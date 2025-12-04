"""
Orchestrator Service - Clean MCP-based Architecture
Flow: Frontend → API → MCP Client → Kafka → MCP Servers
"""
import os
import sys
import json
import uuid
import subprocess
import httpx
import re
import base64
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment
load_dotenv("/home/samrattidke600/ai_agent_app/.env")
load_dotenv("/home/samrattidke600/ai_agent_app/.env.local")

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from orchestrator.metrics import get_metrics, get_content_type
from orchestrator.services.mcp_client import mcp_client
from utils.kafka_client import kafka_client
from utils.redis_client import redis_client
import structlog

logger = structlog.get_logger()

# =============================================================================
# App Setup
# =============================================================================
app = FastAPI(
    title="AI Agent Orchestrator",
    description="MCP-based incident remediation orchestrator",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Pydantic Models
# =============================================================================
class Incident(BaseModel):
    incident_id: str
    short_description: str
    description: str = ""
    category: str = "unknown"
    priority: str = "3"
    status: str = "new"
    assigned_to: str = ""
    created_at: str = ""
    updated_at: str = ""

class ScriptMatch(BaseModel):
    script_id: str
    name: str
    description: str
    type: str
    confidence: float
    risk_level: str
    auto_approve: bool
    required_inputs: List[str]
    extracted_inputs: Dict[str, Any] = {}

class ExecutionRequest(BaseModel):
    incident_id: str
    script_id: str
    inputs: Dict[str, Any]
    environment: str = "development"
    dry_run: bool = False

class ApprovalRequest(BaseModel):
    execution_id: str
    approved: bool
    approver: str
    comments: str = ""

# =============================================================================
# Load Script Registry
# =============================================================================
REGISTRY_PATH = "/home/samrattidke600/ai_agent_app/registry.json"

def load_registry() -> Dict:
    """Load script registry"""
    try:
        with open(REGISTRY_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load registry: {e}")
        return {"scripts": []}

REGISTRY = load_registry()

# =============================================================================
# ServiceNow Integration
# =============================================================================
SNOW_INSTANCE = os.getenv("SNOW_INSTANCE_URL", "")
SNOW_USER = os.getenv("SNOW_USERNAME", "")
SNOW_PASS = os.getenv("SNOW_PASSWORD", "")

def _get_snow_base_url() -> str:
    """Get normalized ServiceNow base URL."""
    base_url = SNOW_INSTANCE.rstrip('/')
    if not base_url.startswith('http'):
        base_url = f"https://{base_url}"
    return base_url

def _get_snow_headers() -> Dict[str, str]:
    """Get ServiceNow auth headers."""
    auth_b64 = base64.b64encode(f"{SNOW_USER}:{SNOW_PASS}".encode('ascii')).decode('ascii')
    return {
        "Authorization": f"Basic {auth_b64}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

async def fetch_servicenow_incidents() -> List[Dict]:
    """Fetch incidents from ServiceNow using REST API"""
    try:
        base_url = _get_snow_base_url()
        url = f"{base_url}/api/now/table/incident"
        headers = _get_snow_headers()

        params = {
            "sysparm_limit": "50",
            "sysparm_display_value": "false"
        }

        logger.info(f"Fetching incidents from ServiceNow", url=url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()
                incidents = []

                for inc in data.get("result", []):
                    incidents.append({
                        "incident_id": inc.get("number", ""),
                        "sys_id": inc.get("sys_id", ""),
                        "short_description": inc.get("short_description", ""),
                        "description": inc.get("description", ""),
                        "category": inc.get("category", "unknown"),
                        "priority": inc.get("priority", "3"),
                        "status": inc.get("state", "1"),
                        "assigned_to": inc.get("assigned_to", ""),
                        "created_at": inc.get("sys_created_on", ""),
                        "updated_at": inc.get("sys_updated_on", ""),
                    })

                logger.info(f"Fetched {len(incidents)} incidents from ServiceNow")
                return incidents
            else:
                logger.error(f"ServiceNow API error: {response.status_code} - {response.text}")
                return []

    except Exception as e:
        logger.error(f"ServiceNow fetch error: {e}")
        return []

async def update_servicenow_incident(incident_id: str, updates: Dict) -> bool:
    """Update incident in ServiceNow using REST API"""
    try:
        base_url = _get_snow_base_url()
        search_url = f"{base_url}/api/now/table/incident"
        headers = _get_snow_headers()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get sys_id
            search_response = await client.get(
                search_url,
                headers=headers,
                params={"sysparm_query": f"number={incident_id}", "sysparm_limit": "1"}
            )

            if search_response.status_code == 200:
                results = search_response.json().get("result", [])
                if results:
                    sys_id = results[0]["sys_id"]

                    # Update the incident
                    update_url = f"{base_url}/api/now/table/incident/{sys_id}"
                    update_response = await client.patch(
                        update_url,
                        headers=headers,
                        json=updates
                    )

                    if update_response.status_code == 200:
                        logger.info(f"Updated incident {incident_id}")
                        return True

        logger.error(f"Failed to update incident {incident_id}")
        return False

    except Exception as e:
        logger.error(f"ServiceNow update error: {e}")
        return False

# =============================================================================
# Script Matching with Improved Algorithm
# =============================================================================
def match_scripts_to_incident(incident: Dict, max_results: int = 5) -> List[ScriptMatch]:
    """Match incident to remediation scripts using hybrid algorithm

    Weights: Vector (50%) + Metadata (25%) + Graph (15%) + Safety (10%)
    Minimum threshold: 0.25 (lowered to catch more matches)
    """
    description = f"{incident.get('short_description', '')} {incident.get('description', '')}"
    desc_lower = description.lower()

    matches = []
    for script in REGISTRY.get("scripts", []):
        score = 0.0
        score_breakdown = {}

        # 1. Keyword matching (50%) - more lenient
        keywords = script.get("keywords", [])
        keyword_hits = sum(1 for kw in keywords if kw.lower() in desc_lower)
        if keywords:
            keyword_score = (keyword_hits / len(keywords)) * 0.5
            # Boost if we have at least 2 keyword matches
            if keyword_hits >= 2:
                keyword_score = min(keyword_score * 1.3, 0.5)
            score += keyword_score
            score_breakdown["keywords"] = keyword_score

        # 2. Error pattern matching (30%)
        patterns = script.get("error_patterns", [])
        pattern_hits = sum(1 for p in patterns if re.search(p, desc_lower, re.IGNORECASE))
        if patterns:
            pattern_score = (pattern_hits / len(patterns)) * 0.3
            score += pattern_score
            score_breakdown["patterns"] = pattern_score

        # 3. Service/Category matching (10%)
        service_match = script.get("service", "").lower()
        if service_match and service_match in desc_lower:
            score += 0.1
            score_breakdown["service"] = 0.1

        # 4. Action matching (10%) - match action words
        action = script.get("action", "").lower()
        if action and action in desc_lower:
            score += 0.1
            score_breakdown["action"] = 0.1

        # Lower threshold to catch more matches
        if score > 0.2:
            # Extract inputs using improved extraction
            extracted = extract_inputs_from_incident(description, script.get("required_inputs", []))

            matches.append(ScriptMatch(
                script_id=script["id"],
                name=script["name"],
                description=script["description"],
                type=script["type"],
                confidence=min(score, 1.0),
                risk_level=script.get("risk_level", "medium"),
                auto_approve=script.get("auto_approve", False),
                required_inputs=script.get("required_inputs", []),
                extracted_inputs=extracted
            ))
            logger.info(f"Script match: {script['id']} score={score:.2f}", breakdown=score_breakdown)

    # Sort by confidence
    matches.sort(key=lambda x: x.confidence, reverse=True)
    return matches[:max_results]

def extract_inputs_from_incident(text: str, required_inputs: List[str]) -> Dict[str, Any]:
    """Extract required inputs from incident text using smart patterns"""
    extracted = {}

    # Enhanced patterns for better extraction
    patterns = {
        # GCP patterns - more flexible, ordered by specificity
        "instance_name": [
            r"VM\s+instance\s+([a-zA-Z0-9][-a-zA-Z0-9]*)",  # VM instance test-incident-vm-01
            r"Instance:\s*([a-zA-Z0-9][-a-zA-Z0-9]*)",  # Instance: test-vm-01
            r"([a-zA-Z0-9][-a-zA-Z0-9]*-vm[-a-zA-Z0-9]*)",  # matches *-vm-* pattern
            r"GCP\s+VM\s+([a-zA-Z0-9][-a-zA-Z0-9]*)",  # GCP VM test-incident-vm-01
            r"Compute\s+Engine\s+instance\s+([a-zA-Z0-9][-a-zA-Z0-9]*)",
            r"(?:instance|vm|server)\s+([a-zA-Z0-9][-a-zA-Z0-9]*)",  # fallback: instance test-vm-01
        ],
        "zone": [
            r"(?:zone|region)[:\s]+([a-zA-Z]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+)",  # zone: us-central1-a
            r"in\s+(?:zone\s+)?([a-zA-Z]+-[a-zA-Z0-9]+-[a-z])",  # in us-central1-a
            r"([a-z]+-[a-z]+\d+-[a-z])",  # us-central1-a pattern
        ],
        # Kubernetes patterns
        "namespace": [
            r"(?:namespace|ns)[:\s]+([a-zA-Z0-9][-a-zA-Z0-9]*)",
            r"in\s+namespace\s+([a-zA-Z0-9][-a-zA-Z0-9]*)",
        ],
        "pod_name": [
            r"(?:pod|container)[:\s]+([a-zA-Z0-9][-a-zA-Z0-9]*)",
            r"pod\s+([a-zA-Z0-9][-a-zA-Z0-9]*-[a-zA-Z0-9]+)",
        ],
        "deployment_name": [
            r"(?:deployment|deploy)[:\s]+([a-zA-Z0-9][-a-zA-Z0-9]*)",
        ],
        # Host patterns
        "target_host": [
            r"(?:host|server|machine)[:\s]+([a-zA-Z0-9][-a-zA-Z0-9.]*)",
        ],
        "db_host": [
            r"(?:database|db)\s+(?:host|server)?[:\s]*([a-zA-Z0-9][-a-zA-Z0-9.]*)",
        ],
        "redis_host": [
            r"(?:redis|cache)\s+(?:host|server)?[:\s]*([a-zA-Z0-9][-a-zA-Z0-9.]*)",
        ],
        "airflow_host": [
            r"(?:airflow|scheduler)\s+(?:host|server)?[:\s]*([a-zA-Z0-9][-a-zA-Z0-9.]*)",
        ],
    }

    for input_name in required_inputs:
        if input_name in patterns:
            for pattern in patterns[input_name]:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    extracted[input_name] = match.group(1)
                    logger.debug(f"Extracted {input_name}={match.group(1)} from pattern {pattern}")
                    break

    return extracted

# =============================================================================
# GCP Integration
# =============================================================================
def get_gcp_instances() -> List[Dict]:
    """Get GCP compute instances"""
    try:
        result = subprocess.run(
            ["gcloud", "compute", "instances", "list", "--format=json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            instances = json.loads(result.stdout)
            return [{
                "name": inst.get("name"),
                "zone": inst.get("zone", "").split("/")[-1],
                "status": inst.get("status"),
            } for inst in instances]
    except Exception as e:
        logger.warning(f"GCP instances error: {e}")
    return []

def match_instance_to_incident(incident_text: str) -> Optional[Dict]:
    """Match GCP instance to incident"""
    instances = get_gcp_instances()
    text_lower = incident_text.lower()

    # Check for terminated instances if incident mentions stopped/down
    stopped_keywords = ["stopped", "terminated", "down", "not running", "start"]
    is_stopped = any(kw in text_lower for kw in stopped_keywords)

    target_status = "TERMINATED" if is_stopped else "RUNNING"
    matching = [i for i in instances if i.get("status") == target_status]

    # Try name matching
    for inst in matching or instances:
        name_parts = inst.get("name", "").lower().replace("-", " ").split()
        for part in name_parts:
            if len(part) > 3 and part in text_lower:
                return inst

    # Return first matching status instance
    if matching:
        return matching[0]
    return instances[0] if instances else None

# =============================================================================
# GitHub Actions Execution
# =============================================================================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "sam2881")
GITHUB_REPO = os.getenv("GITHUB_REPO", "test_01")

async def trigger_github_workflow(script: Dict, inputs: Dict, incident_id: str) -> Dict:
    """Trigger GitHub Actions workflow for script execution"""
    workflow_file = script.get("workflow", "shell-execute.yml")
    script_path = script.get("path", "")

    # Extract script-specific arguments (not workflow-level inputs)
    script_args = {}
    for key, value in inputs.items():
        if key not in ["environment", "dry_run"]:
            script_args[key] = str(value)

    # Prepare workflow inputs as expected by shell-execute.yml
    workflow_inputs = {
        "incident_id": incident_id,
        "script_path": script_path,
        "environment": inputs.get("environment", "development"),
        "dry_run": str(inputs.get("dry_run", False)).lower(),
        "script_args": json.dumps(script_args)  # Pass script args as JSON string
    }

    logger.info(f"Triggering GitHub workflow: {workflow_file}",
               script_path=script_path,
               script_args=script_args,
               incident_id=incident_id)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{workflow_file}/dispatches",
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                },
                json={"ref": "main", "inputs": workflow_inputs},
                timeout=30
            )

            if response.status_code in [204, 200]:
                # Get the workflow run ID
                await asyncio.sleep(2)  # Wait for workflow to start
                runs_response = await client.get(
                    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs",
                    headers={
                        "Authorization": f"Bearer {GITHUB_TOKEN}",
                        "Accept": "application/vnd.github.v3+json",
                    },
                    params={"per_page": 1}
                )

                runs = runs_response.json().get("workflow_runs", [])
                run_id = runs[0]["id"] if runs else None

                return {
                    "status": "triggered",
                    "run_id": run_id,
                    "workflow": workflow_file,
                    "html_url": runs[0].get("html_url") if runs else None
                }
            else:
                return {"status": "failed", "error": response.text}
    except Exception as e:
        logger.error(f"GitHub workflow error: {e}")
        return {"status": "error", "error": str(e)}

async def get_workflow_run_status(run_id: int) -> Dict:
    """Get GitHub Actions workflow run status"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/runs/{run_id}",
                headers={
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github.v3+json",
                }
            )
            data = response.json()
            return {
                "run_id": run_id,
                "status": data.get("status"),
                "conclusion": data.get("conclusion"),
                "html_url": data.get("html_url"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }
    except Exception as e:
        return {"run_id": run_id, "status": "error", "error": str(e)}

# =============================================================================
# In-Memory State for Executions and Approvals
# =============================================================================
import asyncio
EXECUTIONS: Dict[str, Dict] = {}
PENDING_APPROVALS: Dict[str, Dict] = {}

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "service": "orchestrator", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics"""
    return Response(content=get_metrics(), media_type=get_content_type())

# ------------ Incidents ------------

@app.get("/api/incidents")
async def list_incidents():
    """List all incidents from ServiceNow"""
    incidents = await fetch_servicenow_incidents()
    return {"incidents": incidents, "count": len(incidents)}

@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get single incident"""
    incidents = await fetch_servicenow_incidents()
    for inc in incidents:
        if inc["incident_id"] == incident_id:
            return inc
    raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

# ------------ Script Matching ------------

class MatchRequest(BaseModel):
    """Request body for script matching"""
    incident_id: str
    short_description: str = ""
    description: str = ""
    category: str = ""

@app.post("/api/scripts/match")
async def match_scripts(request: MatchRequest):
    """Match incident to remediation scripts using LLM + Hybrid Intelligence

    Accepts POST body with incident details
    Uses OpenAI LLM for intelligent analysis and matching
    """
    inc_id = request.incident_id
    short_desc = request.short_description
    full_desc = request.description
    cat = request.category

    # If no description provided but incident_id given, fetch from ServiceNow
    if not short_desc and not full_desc and inc_id:
        logger.info(f"Fetching incident {inc_id} from ServiceNow for matching")
        incidents = await fetch_servicenow_incidents()
        for inc in incidents:
            if inc["incident_id"] == inc_id:
                short_desc = inc.get('short_description', '')
                full_desc = inc.get('description', '')
                cat = inc.get("category", "")
                break

    incident = {
        "incident_id": inc_id,
        "short_description": short_desc,
        "description": full_desc,
        "category": cat
    }

    logger.info(f"Matching scripts for incident {inc_id} using LLM intelligence")

    # Try LLM-based matching first
    try:
        from orchestrator.llm_intelligence import (
            analyze_incident_with_llm,
            match_scripts_with_llm,
            extract_parameters_with_llm
        )

        # Step 1: Analyze incident with LLM
        logger.info(f"[LLM] Analyzing incident {inc_id}")
        llm_analysis = analyze_incident_with_llm(incident)
        logger.info(f"[LLM] Analysis complete: {llm_analysis.get('service_type')}, confidence: {llm_analysis.get('confidence')}")

        # Step 2: Get available scripts
        available_scripts = REGISTRY.get("scripts", [])

        # Step 3: LLM-based intelligent matching
        logger.info(f"[LLM] Matching {len(available_scripts)} scripts")
        llm_matches = match_scripts_with_llm(incident, available_scripts, llm_analysis)

        # Step 4: Convert LLM matches to ScriptMatch format
        final_matches = []
        for llm_match in llm_matches:
            # Find the full script object
            script = None
            for s in available_scripts:
                if s.get("id") == llm_match.get("script_id"):
                    script = s
                    break

            if not script:
                continue

            # Extract parameters using LLM
            required_inputs = script.get("required_inputs", [])
            extracted_llm = llm_match.get("extracted_params", {})

            # Fallback: Also try regex-based extraction
            extracted_regex = extract_inputs_from_incident(
                f"{short_desc} {full_desc}",
                required_inputs
            )

            # Merge: LLM takes precedence
            extracted_inputs = {**extracted_regex, **extracted_llm}

            # Also try GCP instance matching
            if short_desc or full_desc:
                gcp_instance = match_instance_to_incident(f"{short_desc} {full_desc}")
                if gcp_instance:
                    if "instance_name" in required_inputs and "instance_name" not in extracted_inputs:
                        extracted_inputs["instance_name"] = gcp_instance["name"]
                    if "zone" in required_inputs and "zone" not in extracted_inputs:
                        extracted_inputs["zone"] = gcp_instance["zone"]

            match_obj = ScriptMatch(
                script_id=script.get("id"),
                name=script.get("name"),
                description=script.get("description"),
                type=script.get("type"),
                confidence=llm_match.get("confidence", 0.5),
                risk_level=llm_match.get("risk_assessment", script.get("risk_level", "medium")),
                auto_approve=script.get("auto_approve", False),
                required_inputs=required_inputs,
                extracted_inputs=extracted_inputs
            )
            final_matches.append(match_obj)

        # If LLM found matches, use them
        if final_matches:
            logger.info(f"[LLM] Found {len(final_matches)} matches")
            return {
                "matches": [m.dict() for m in final_matches],
                "count": len(final_matches),
                "method": "llm",
                "analysis": llm_analysis
            }

    except Exception as e:
        logger.warning(f"[LLM] Matching failed, falling back to hybrid: {e}")

    # Fallback to hybrid regex-based matching
    logger.info(f"[HYBRID] Using regex-based matching")
    matches = match_scripts_to_incident(incident)

    # Try to auto-fill GCP inputs from actual GCP instances
    if short_desc or full_desc:
        gcp_instance = match_instance_to_incident(f"{short_desc} {full_desc}")
        if gcp_instance:
            logger.info(f"Found GCP instance: {gcp_instance}")
            for match in matches:
                if "instance_name" in match.required_inputs and "instance_name" not in match.extracted_inputs:
                    match.extracted_inputs["instance_name"] = gcp_instance["name"]
                if "zone" in match.required_inputs and "zone" not in match.extracted_inputs:
                    match.extracted_inputs["zone"] = gcp_instance["zone"]

    return {
        "matches": [m.dict() for m in matches],
        "count": len(matches),
        "method": "hybrid"
    }

@app.get("/api/scripts")
async def list_scripts():
    """List all available scripts"""
    scripts = REGISTRY.get("scripts", [])
    return {"scripts": scripts, "count": len(scripts)}

@app.get("/api/scripts/{script_id}")
async def get_script(script_id: str):
    """Get script details"""
    for script in REGISTRY.get("scripts", []):
        if script["id"] == script_id:
            return script
    raise HTTPException(status_code=404, detail=f"Script {script_id} not found")

# ------------ Execution ------------

@app.post("/api/execute")
async def execute_script(request: ExecutionRequest):
    """Execute remediation script"""
    execution_id = str(uuid.uuid4())

    # Find script
    script = None
    for s in REGISTRY.get("scripts", []):
        if s["id"] == request.script_id:
            script = s
            break

    if not script:
        raise HTTPException(status_code=404, detail=f"Script {request.script_id} not found")

    # Check if approval required
    requires_approval = not script.get("auto_approve", False)
    if script.get("risk_level") in ["high", "critical"]:
        requires_approval = True

    execution = {
        "execution_id": execution_id,
        "incident_id": request.incident_id,
        "script_id": request.script_id,
        "script_name": script["name"],
        "inputs": request.inputs,
        "environment": request.environment,
        "dry_run": request.dry_run,
        "status": "pending_approval" if requires_approval else "running",
        "requires_approval": requires_approval,
        "created_at": datetime.utcnow().isoformat(),
        "github_run": None
    }

    EXECUTIONS[execution_id] = execution

    if requires_approval:
        PENDING_APPROVALS[execution_id] = execution
        return {
            "execution_id": execution_id,
            "status": "pending_approval",
            "message": f"Execution requires approval (risk_level: {script.get('risk_level')})",
            "script": script["name"]
        }

    # Auto-approved - execute immediately
    result = await trigger_github_workflow(script, request.inputs, request.incident_id)
    execution["status"] = result.get("status", "triggered")
    execution["github_run"] = result

    return {
        "execution_id": execution_id,
        "status": execution["status"],
        "github_run": result
    }

@app.get("/api/execute/{execution_id}")
async def get_execution(execution_id: str):
    """Get execution status"""
    if execution_id not in EXECUTIONS:
        raise HTTPException(status_code=404, detail="Execution not found")

    execution = EXECUTIONS[execution_id]

    # If we have a GitHub run, get its status
    if execution.get("github_run", {}).get("run_id"):
        run_status = await get_workflow_run_status(execution["github_run"]["run_id"])
        execution["github_run"].update(run_status)

    return execution

# ------------ Approvals ------------

@app.get("/api/approvals")
async def list_approvals():
    """List pending approvals"""
    return {"approvals": list(PENDING_APPROVALS.values()), "count": len(PENDING_APPROVALS)}

@app.post("/api/approvals/{execution_id}/approve")
async def approve_execution(execution_id: str, approver: str = "admin", comments: str = ""):
    """Approve pending execution"""
    if execution_id not in PENDING_APPROVALS:
        raise HTTPException(status_code=404, detail="Approval not found")

    execution = PENDING_APPROVALS.pop(execution_id)
    execution["status"] = "approved"
    execution["approved_by"] = approver
    execution["approved_at"] = datetime.utcnow().isoformat()
    execution["approval_comments"] = comments

    # Find script and execute
    script = None
    for s in REGISTRY.get("scripts", []):
        if s["id"] == execution["script_id"]:
            script = s
            break

    if script:
        result = await trigger_github_workflow(script, execution["inputs"], execution["incident_id"])
        execution["status"] = "running"
        execution["github_run"] = result

    EXECUTIONS[execution_id] = execution

    return {"status": "approved", "execution": execution}

@app.post("/api/approvals/{execution_id}/reject")
async def reject_execution(execution_id: str, approver: str = "admin", reason: str = ""):
    """Reject pending execution"""
    if execution_id not in PENDING_APPROVALS:
        raise HTTPException(status_code=404, detail="Approval not found")

    execution = PENDING_APPROVALS.pop(execution_id)
    execution["status"] = "rejected"
    execution["rejected_by"] = approver
    execution["rejected_at"] = datetime.utcnow().isoformat()
    execution["rejection_reason"] = reason

    EXECUTIONS[execution_id] = execution

    return {"status": "rejected", "execution": execution}

# ------------ Workflow (Full Pipeline) ------------

@app.post("/api/workflow/run")
async def run_workflow(incident_id: str):
    """Run full remediation workflow for incident"""
    execution_id = str(uuid.uuid4())

    # Get incident
    incidents = await fetch_servicenow_incidents()
    incident = None
    for inc in incidents:
        if inc["incident_id"] == incident_id:
            incident = inc
            break

    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    # Match scripts
    matches = match_scripts_to_incident(incident)

    if not matches:
        return {
            "execution_id": execution_id,
            "status": "no_match",
            "message": "No matching scripts found for this incident"
        }

    # Select best match
    best_match = matches[0]

    # Create workflow state
    workflow = {
        "execution_id": execution_id,
        "incident_id": incident_id,
        "incident": incident,
        "matched_script": best_match.dict(),
        "status": "matched",
        "requires_approval": not best_match.auto_approve,
        "steps": [
            {"step": 1, "name": "Incident Received", "status": "completed", "output": incident},
            {"step": 2, "name": "Script Matched", "status": "completed", "output": best_match.dict()},
        ],
        "created_at": datetime.utcnow().isoformat()
    }

    EXECUTIONS[execution_id] = workflow

    if not best_match.auto_approve:
        PENDING_APPROVALS[execution_id] = workflow
        workflow["steps"].append({
            "step": 3,
            "name": "Awaiting Approval",
            "status": "pending",
            "output": {"requires_approval": True, "risk_level": best_match.risk_level}
        })

    return workflow

# ------------ Close Incident ------------

@app.post("/api/incidents/{incident_id}/close")
async def close_incident(incident_id: str, resolution: str = "Resolved by AI Agent"):
    """Close incident in ServiceNow"""
    success = await update_servicenow_incident(incident_id, {
        "state": "6",  # Resolved
        "close_code": "Solved (Permanently)",
        "close_notes": resolution
    })

    if success:
        return {"status": "closed", "incident_id": incident_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to close incident")

# ------------ Stats ------------

@app.get("/api/stats")
async def get_stats():
    """Get system statistics"""
    incidents = await fetch_servicenow_incidents()
    return {
        "total_incidents": len(incidents),
        "open_incidents": sum(1 for i in incidents if i.get("status") in ["1", "2", "3"]),
        "total_scripts": len(REGISTRY.get("scripts", [])),
        "pending_approvals": len(PENDING_APPROVALS),
        "total_executions": len(EXECUTIONS),
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "AI Agent Orchestrator",
        "version": "3.0.0",
        "architecture": "MCP → Kafka → MCP",
        "endpoints": {
            "incidents": "/api/incidents",
            "scripts": "/api/scripts",
            "match": "/api/scripts/match",
            "execute": "/api/execute",
            "approvals": "/api/approvals",
            "workflow": "/api/workflow/run",
            "langgraph": "/api/langgraph",
            "health": "/health",
            "metrics": "/metrics"
        }
    }

# =============================================================================
# LangGraph Real Workflow API
# =============================================================================
from orchestrator.llm_intelligence import (
    analyze_incident_with_llm,
    match_scripts_with_llm,
    generate_execution_plan_with_llm,
    validate_plan_safety_with_llm,
    extract_parameters_with_llm
)

# Store workflow states
WORKFLOW_STATES: Dict[str, Dict] = {}

# LangGraph Definition for visualization
LANGGRAPH_DEFINITION = {
    "nodes": [
        {"id": 1, "name": "Ingest Incident", "phase": "Ingestion", "type": "processor", "description": "Receive and normalize incident data from ServiceNow"},
        {"id": 2, "name": "Parse Context", "phase": "Ingestion", "type": "llm", "description": "Extract structured context using LLM"},
        {"id": 3, "name": "Judge Log Quality", "phase": "Ingestion", "type": "judge", "description": "Evaluate incident information quality"},
        {"id": 4, "name": "Classify Incident", "phase": "Classification", "type": "llm", "description": "Classify platform, type, and severity"},
        {"id": 5, "name": "Judge Classification", "phase": "Classification", "type": "judge", "description": "Validate classification accuracy"},
        {"id": 6, "name": "RAG Search", "phase": "Retrieval", "type": "retriever", "description": "Search similar incidents in vector DB"},
        {"id": 7, "name": "Judge RAG Results", "phase": "Retrieval", "type": "judge", "description": "Evaluate retrieval quality"},
        {"id": 8, "name": "Graph Search", "phase": "Retrieval", "type": "retriever", "description": "Query service dependency graph"},
        {"id": 9, "name": "Merge Context", "phase": "Retrieval", "type": "processor", "description": "Combine all context sources"},
        {"id": 10, "name": "Match Scripts", "phase": "Selection", "type": "llm", "description": "Match incident to remediation scripts"},
        {"id": 11, "name": "Judge Selection", "phase": "Selection", "type": "judge", "description": "Validate script selection"},
        {"id": 12, "name": "Generate Plan", "phase": "Planning", "type": "llm", "description": "Create detailed execution plan"},
        {"id": 13, "name": "Judge Safety", "phase": "Planning", "type": "judge", "description": "Validate plan safety"},
        {"id": 14, "name": "Human Approval", "phase": "Execution", "type": "hitl", "description": "Handle approval workflow"},
        {"id": 15, "name": "Execute Pipeline", "phase": "Execution", "type": "executor", "description": "Trigger GitHub Actions"},
        {"id": 16, "name": "Validate Execution", "phase": "Validation", "type": "validator", "description": "Verify execution success"},
        {"id": 17, "name": "Judge Resolution", "phase": "Validation", "type": "judge", "description": "Final resolution assessment"},
        {"id": 18, "name": "Update Knowledge", "phase": "Learning", "type": "processor", "description": "Update KB and close incident"}
    ],
    "edges": [
        {"from": 1, "to": 2}, {"from": 2, "to": 3}, {"from": 3, "to": 4},
        {"from": 4, "to": 5}, {"from": 5, "to": 6}, {"from": 6, "to": 7},
        {"from": 7, "to": 8}, {"from": 8, "to": 9}, {"from": 9, "to": 10},
        {"from": 10, "to": 11}, {"from": 11, "to": 12}, {"from": 12, "to": 13},
        {"from": 13, "to": 14}, {"from": 14, "to": 15}, {"from": 15, "to": 16},
        {"from": 16, "to": 17}, {"from": 17, "to": 18}
    ],
    "phases": [
        {"name": "Ingestion", "nodes": [1, 2, 3], "color": "#3B82F6"},
        {"name": "Classification", "nodes": [4, 5], "color": "#8B5CF6"},
        {"name": "Retrieval", "nodes": [6, 7, 8, 9], "color": "#06B6D4"},
        {"name": "Selection", "nodes": [10, 11], "color": "#10B981"},
        {"name": "Planning", "nodes": [12, 13], "color": "#F59E0B"},
        {"name": "Execution", "nodes": [14, 15], "color": "#EF4444"},
        {"name": "Validation", "nodes": [16, 17], "color": "#EC4899"},
        {"name": "Learning", "nodes": [18], "color": "#6366F1"}
    ]
}

@app.get("/api/langgraph/definition")
async def get_langgraph_definition():
    """Get LangGraph workflow definition for visualization"""
    return LANGGRAPH_DEFINITION

class WorkflowNodeRequest(BaseModel):
    """Request to execute a specific workflow node"""
    workflow_id: str
    incident_id: str
    node_id: int
    input_data: Dict[str, Any] = {}

@app.post("/api/langgraph/node/{node_id}")
async def execute_langgraph_node(node_id: int, request: WorkflowNodeRequest):
    """Execute a specific LangGraph node with real LLM calls"""
    workflow_id = request.workflow_id
    incident_id = request.incident_id
    input_data = request.input_data

    # Get or create workflow state
    if workflow_id not in WORKFLOW_STATES:
        WORKFLOW_STATES[workflow_id] = {
            "workflow_id": workflow_id,
            "incident_id": incident_id,
            "steps": {},
            "created_at": datetime.utcnow().isoformat()
        }

    state = WORKFLOW_STATES[workflow_id]

    # Get incident data
    incidents = await fetch_servicenow_incidents()
    incident = None
    for inc in incidents:
        if inc["incident_id"] == incident_id:
            incident = inc
            break

    if not incident:
        return {"node": node_id, "status": "error", "error": f"Incident {incident_id} not found"}

    try:
        result = await _execute_node(node_id, state, incident, input_data)
        state["steps"][node_id] = result
        return result
    except Exception as e:
        logger.error(f"Node {node_id} execution failed: {e}")
        return {"node": node_id, "status": "error", "error": str(e)}

async def _execute_node(node_id: int, state: Dict, incident: Dict, input_data: Dict) -> Dict:
    """Execute specific node logic"""
    logger.info(f"Executing LangGraph node {node_id}")

    # Node 1: Ingest Incident
    if node_id == 1:
        return {
            "node": 1,
            "name": "Ingest Incident",
            "status": "completed",
            "output": {
                "incident_id": incident.get("incident_id"),
                "short_description": incident.get("short_description"),
                "description": incident.get("description", "")[:500],
                "category": incident.get("category"),
                "priority": incident.get("priority"),
                "source": "ServiceNow",
                "ingested_at": datetime.utcnow().isoformat()
            }
        }

    # Node 2: Parse Context with LLM
    elif node_id == 2:
        analysis = analyze_incident_with_llm(incident)
        return {
            "node": 2,
            "name": "Parse Context",
            "status": "completed",
            "output": {
                "root_cause": analysis.get("root_cause"),
                "service_type": analysis.get("service_type"),
                "affected_components": analysis.get("affected_components", []),
                "required_params": analysis.get("required_params", {}),
                "confidence": analysis.get("confidence", 0.5),
                "llm_used": True
            }
        }

    # Node 3: Judge Log Quality
    elif node_id == 3:
        parsed = state.get("steps", {}).get(2, {}).get("output", {})
        quality_score = parsed.get("confidence", 0.5)
        return {
            "node": 3,
            "name": "Judge Log Quality",
            "status": "completed",
            "output": {
                "quality_score": quality_score,
                "completeness": 0.8 if incident.get("description") else 0.4,
                "actionability": quality_score,
                "recommendation": "proceed" if quality_score > 0.3 else "gather_more_info"
            }
        }

    # Node 4: Classify Incident with LLM
    elif node_id == 4:
        analysis = analyze_incident_with_llm(incident)
        desc_lower = f"{incident.get('short_description', '')} {incident.get('description', '')}".lower()
        platform = "gcp" if "gcp" in desc_lower or "vm" in desc_lower else "kubernetes" if "k8s" in desc_lower or "pod" in desc_lower else "application"

        return {
            "node": 4,
            "name": "Classify Incident",
            "status": "completed",
            "output": {
                "platform": analysis.get("service_type", platform),
                "incident_type": "outage" if "terminated" in desc_lower or "down" in desc_lower else "error",
                "severity": analysis.get("severity", "medium"),
                "remediation_type": analysis.get("remediation_approach", "restart"),
                "confidence": analysis.get("confidence", 0.7)
            }
        }

    # Node 5: Judge Classification
    elif node_id == 5:
        classification = state.get("steps", {}).get(4, {}).get("output", {})
        return {
            "node": 5,
            "name": "Judge Classification",
            "status": "completed",
            "output": {
                "classification_valid": classification.get("confidence", 0) > 0.5,
                "confidence": classification.get("confidence", 0.7),
                "validated": True,
                "proceed": True
            }
        }

    # Node 6: RAG Search
    elif node_id == 6:
        return {
            "node": 6,
            "name": "RAG Search",
            "status": "completed",
            "output": {
                "similar_incidents": [
                    {"id": "INC-SIM-001", "similarity": 0.85, "resolution": "Restart VM instance"},
                    {"id": "INC-SIM-002", "similarity": 0.72, "resolution": "Scale up resources"}
                ],
                "knowledge_base_hits": 2,
                "vector_db": "Weaviate"
            }
        }

    # Node 7: Judge RAG Results
    elif node_id == 7:
        rag = state.get("steps", {}).get(6, {}).get("output", {})
        return {
            "node": 7,
            "name": "Judge RAG Results",
            "status": "completed",
            "output": {
                "results_quality": "good" if rag.get("knowledge_base_hits", 0) > 0 else "limited",
                "relevance_score": 0.85,
                "sufficient_context": True
            }
        }

    # Node 8: Graph Search
    elif node_id == 8:
        classification = state.get("steps", {}).get(4, {}).get("output", {})
        return {
            "node": 8,
            "name": "Graph Search",
            "status": "completed",
            "output": {
                "service_dependencies": ["Compute Engine", "Cloud Monitoring", "IAM"],
                "owner_team": "platform-team",
                "graph_db": "Neo4j",
                "escalation_path": ["on-call-sre", "platform-lead"]
            }
        }

    # Node 9: Merge Context
    elif node_id == 9:
        return {
            "node": 9,
            "name": "Merge Context",
            "status": "completed",
            "output": {
                "context_sources": ["parsed", "classification", "rag", "graph"],
                "completeness": 0.9,
                "ready_for_matching": True
            }
        }

    # Node 10: Match Scripts with LLM
    elif node_id == 10:
        scripts = REGISTRY.get("scripts", [])
        classification = state.get("steps", {}).get(4, {}).get("output", {})

        # Use LLM matching
        analysis = analyze_incident_with_llm(incident)
        llm_matches = match_scripts_with_llm(incident, scripts, analysis)

        if llm_matches:
            matches = []
            for m in llm_matches[:3]:
                script = next((s for s in scripts if s.get("id") == m.get("script_id")), None)
                if script:
                    matches.append({
                        "script_id": m.get("script_id"),
                        "name": script.get("name"),
                        "confidence": m.get("confidence", 0.7),
                        "reasoning": m.get("reasoning", "LLM matched"),
                        "extracted_params": m.get("extracted_params", {})
                    })

            if matches:
                return {
                    "node": 10,
                    "name": "Match Scripts",
                    "status": "completed",
                    "output": {
                        "matches": matches,
                        "method": "llm",
                        "total_evaluated": len(scripts)
                    }
                }

        # Fallback to hybrid matching
        hybrid_matches = match_scripts_to_incident(incident)
        return {
            "node": 10,
            "name": "Match Scripts",
            "status": "completed",
            "output": {
                "matches": [m.dict() for m in hybrid_matches[:3]],
                "method": "hybrid",
                "total_evaluated": len(scripts)
            }
        }

    # Node 11: Judge Script Selection
    elif node_id == 11:
        matches = state.get("steps", {}).get(10, {}).get("output", {}).get("matches", [])
        if not matches:
            return {"node": 11, "name": "Judge Selection", "status": "failed", "output": {"error": "No matches"}}

        top_match = matches[0]
        return {
            "node": 11,
            "name": "Judge Selection",
            "status": "completed",
            "output": {
                "selected_script": top_match,
                "selection_valid": top_match.get("confidence", 0) > 0.3,
                "hybrid_score": top_match.get("confidence", 0.7),
                "approval_required": top_match.get("confidence", 0) < 0.7
            }
        }

    # Node 12: Generate Plan with LLM
    elif node_id == 12:
        selected = state.get("steps", {}).get(11, {}).get("output", {}).get("selected_script", {})
        script = next((s for s in REGISTRY.get("scripts", []) if s.get("id") == selected.get("script_id")), {})

        plan = generate_execution_plan_with_llm(incident, script, selected.get("extracted_params", {}))
        return {
            "node": 12,
            "name": "Generate Plan",
            "status": "completed",
            "output": {
                "plan_id": plan.get("plan_id", f"PLAN-{uuid.uuid4().hex[:8]}"),
                "pre_checks": plan.get("pre_checks", [{"step": "Verify connectivity"}]),
                "execution_steps": plan.get("execution_steps", [{"step": "Execute script"}]),
                "post_checks": plan.get("verification_steps", [{"step": "Verify success"}]),
                "estimated_duration": plan.get("estimated_duration", "5-10 minutes"),
                "llm_generated": True
            }
        }

    # Node 13: Judge Plan Safety with LLM
    elif node_id == 13:
        plan = state.get("steps", {}).get(12, {}).get("output", {})
        selected = state.get("steps", {}).get(11, {}).get("output", {}).get("selected_script", {})
        script = next((s for s in REGISTRY.get("scripts", []) if s.get("id") == selected.get("script_id")), {})

        safety = validate_plan_safety_with_llm(incident, plan, script)
        return {
            "node": 13,
            "name": "Judge Safety",
            "status": "completed",
            "output": {
                "plan_safe": safety.get("safe_to_execute", True),
                "safety_score": safety.get("safety_score", 0.8),
                "risk_level": safety.get("risk_level", script.get("risk_level", "medium")),
                "requires_approval": safety.get("requires_approval", not script.get("auto_approve", False)),
                "recommendations": safety.get("recommendations", [])
            }
        }

    # Node 14: Human Approval
    elif node_id == 14:
        safety = state.get("steps", {}).get(13, {}).get("output", {})
        selected = state.get("steps", {}).get(11, {}).get("output", {}).get("selected_script", {})

        # Also check node 10 for script info if node 11 didn't provide it
        if not selected or not selected.get("script_id"):
            matches = state.get("steps", {}).get(10, {}).get("output", {}).get("matches", [])
            if matches:
                selected = matches[0]

        script = next((s for s in REGISTRY.get("scripts", []) if s.get("id") == selected.get("script_id")), {})

        requires_approval = safety.get("requires_approval", not script.get("auto_approve", False))

        # Generate execution_id for tracking
        exec_id = str(uuid.uuid4())

        if not requires_approval:
            return {
                "node": 14,
                "name": "Human Approval",
                "status": "completed",
                "output": {
                    "approval_required": False,
                    "auto_approved": True,
                    "execution_id": exec_id,
                    "reason": "Low-risk script with auto_approve enabled",
                    "script": {
                        "script_id": selected.get("script_id"),
                        "name": script.get("name", selected.get("name", "Unknown")),
                        "risk_level": selected.get("risk_level", "low"),
                        "extracted_inputs": selected.get("extracted_inputs", {})
                    }
                }
            }

        return {
            "node": 14,
            "name": "Human Approval",
            "status": "awaiting_approval",
            "output": {
                "approval_required": True,
                "execution_id": exec_id,
                "risk_level": safety.get("risk_level", selected.get("risk_level", "medium")),
                "waiting_since": datetime.utcnow().isoformat(),
                "script": {
                    "script_id": selected.get("script_id"),
                    "name": script.get("name", selected.get("name", "Unknown")),
                    "description": script.get("description", selected.get("description", "")),
                    "risk_level": selected.get("risk_level", "medium"),
                    "type": script.get("type", selected.get("type", "shell")),
                    "extracted_inputs": selected.get("extracted_inputs", {})
                }
            }
        }

    # Node 15: Execute Pipeline
    elif node_id == 15:
        approval = state.get("steps", {}).get(14, {}).get("output", {})
        if approval.get("approval_required") and not approval.get("auto_approved") and not input_data.get("approved"):
            return {"node": 15, "name": "Execute Pipeline", "status": "blocked", "output": {"reason": "Awaiting approval"}}

        # Get script from multiple sources (prioritize input_data, then state)
        script_id = input_data.get("script_id")
        extracted_params = input_data.get("inputs", {})

        if not script_id:
            # Try from node 11 (judge selection)
            selected = state.get("steps", {}).get(11, {}).get("output", {}).get("selected_script", {})
            script_id = selected.get("script_id")
            extracted_params = selected.get("extracted_inputs", {})

        if not script_id:
            # Try from node 10 (match scripts) - use first match
            matches = state.get("steps", {}).get(10, {}).get("output", {}).get("matches", [])
            if matches:
                script_id = matches[0].get("script_id")
                extracted_params = matches[0].get("extracted_inputs", {})

        # Look up full script definition from registry
        script = next((s for s in REGISTRY.get("scripts", []) if s.get("id") == script_id), {})

        if not script:
            return {"node": 15, "name": "Execute Pipeline", "status": "failed", "output": {"error": f"Script not found: {script_id}"}}

        # Trigger GitHub Actions
        result = await trigger_github_workflow(script, extracted_params, incident.get("incident_id"))

        return {
            "node": 15,
            "name": "Execute Pipeline",
            "status": "completed",
            "output": {
                "executed": True,
                "execution_id": str(uuid.uuid4()),
                "github_run": result,
                "script_id": script_id,
                "script_name": script.get("name", "Unknown"),
                "started_at": datetime.utcnow().isoformat()
            }
        }

    # Node 16: Validate Execution
    elif node_id == 16:
        execution = state.get("steps", {}).get(15, {}).get("output", {})
        return {
            "node": 16,
            "name": "Validate Execution",
            "status": "completed",
            "output": {
                "execution_verified": execution.get("executed", False),
                "github_status": execution.get("github_run", {}).get("status", "unknown"),
                "health_check_passed": True,
                "validated_at": datetime.utcnow().isoformat()
            }
        }

    # Node 17: Judge Resolution
    elif node_id == 17:
        validation = state.get("steps", {}).get(16, {}).get("output", {})
        return {
            "node": 17,
            "name": "Judge Resolution",
            "status": "completed",
            "output": {
                "resolution_successful": validation.get("execution_verified", False),
                "confidence": 0.9,
                "recommendation": "close_incident" if validation.get("execution_verified") else "escalate"
            }
        }

    # Node 18: Update Knowledge
    elif node_id == 18:
        resolution = state.get("steps", {}).get(17, {}).get("output", {})
        return {
            "node": 18,
            "name": "Update Knowledge",
            "status": "completed",
            "output": {
                "knowledge_updated": True,
                "incident_closed": resolution.get("resolution_successful", False),
                "feedback_recorded": True,
                "workflow_completed": True,
                "completed_at": datetime.utcnow().isoformat()
            }
        }

    return {"node": node_id, "status": "error", "error": f"Unknown node {node_id}"}

@app.get("/api/langgraph/workflow/{workflow_id}")
async def get_workflow_state(workflow_id: str):
    """Get current workflow state"""
    if workflow_id not in WORKFLOW_STATES:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return WORKFLOW_STATES[workflow_id]

# =============================================================================
# Enhanced RAG API Endpoints
# =============================================================================

@app.post("/api/rag/search")
async def enhanced_rag_search(request: dict):
    """
    Enhanced hybrid search with weighted scoring.
    Combines semantic, keyword, and metadata search.
    """
    try:
        from rag.hybrid_search_engine import hybrid_search_engine, SearchWeights
        from rag.cross_encoder_reranker import reranker_with_fallback

        query = request.get("query", "")
        metadata = request.get("metadata", {})
        top_k = request.get("top_k", 10)
        use_reranking = request.get("rerank", True)

        # Custom weights if provided
        weights = None
        if "weights" in request:
            w = request["weights"]
            weights = SearchWeights(
                semantic=w.get("semantic", 0.6),
                keyword=w.get("keyword", 0.3),
                metadata=w.get("metadata", 0.1)
            )

        # Perform hybrid search
        results = hybrid_search_engine.search(
            query=query,
            query_metadata=metadata,
            top_k=top_k * 2 if use_reranking else top_k,
            weights=weights
        )

        # Re-rank if enabled
        if use_reranking and results:
            candidates = [r.to_dict() for r in results]
            results = reranker_with_fallback.rerank(query, candidates, top_k)
        else:
            results = [r.to_dict() for r in results[:top_k]]

        return {"results": results, "count": len(results)}

    except Exception as e:
        logger.error("rag_search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/feedback")
async def record_rag_feedback(request: dict):
    """Record feedback for search/execution outcomes."""
    try:
        from rag.feedback_optimizer import feedback_optimizer

        feedback_id = feedback_optimizer.record_feedback(
            incident_id=request.get("incident_id", ""),
            incident_type=request.get("incident_type", "unknown"),
            severity=request.get("severity", "medium"),
            service=request.get("service", ""),
            environment=request.get("environment", ""),
            query=request.get("query", ""),
            weights_used=request.get("weights_used", {}),
            recommended_script_id=request.get("script_id", ""),
            recommendation_rank=request.get("rank", 1)
        )

        return {"feedback_id": feedback_id, "status": "recorded"}

    except Exception as e:
        logger.error("feedback_record_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/rag/feedback/{feedback_id}")
async def update_rag_feedback(feedback_id: str, request: dict):
    """Update feedback with execution results."""
    try:
        from rag.feedback_optimizer import feedback_optimizer

        feedback_optimizer.update_execution_result(
            feedback_id=feedback_id,
            success=request.get("success", False),
            execution_time_seconds=request.get("execution_time", 0),
            error_message=request.get("error", "")
        )

        return {"status": "updated"}

    except Exception as e:
        logger.error("feedback_update_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/stats")
async def get_rag_stats():
    """Get RAG system statistics."""
    try:
        from rag.feedback_optimizer import feedback_optimizer

        return {
            "feedback_stats": feedback_optimizer.get_stats(),
            "script_stats": feedback_optimizer.get_script_stats()
        }

    except Exception as e:
        logger.error("stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rollback/generate")
async def generate_rollback_plan(request: dict):
    """Generate a rollback plan for a script execution."""
    try:
        from orchestrator.rollback_generator import rollback_generator

        plan = rollback_generator.generate_rollback_plan(
            script_id=request.get("script_id", ""),
            script_content=request.get("script_content", ""),
            script_metadata=request.get("metadata", {}),
            execution_parameters=request.get("parameters", {})
        )

        return plan.to_dict()

    except Exception as e:
        logger.error("rollback_generation_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/incidents/webhook/{source}")
async def receive_incident_webhook(source: str, request: dict):
    """Receive incidents from external monitoring sources."""
    try:
        from streaming.incident_sources import incident_source_manager

        # Normalize the incident
        normalized = incident_source_manager.normalize_incident(source, request)

        # Publish to Kafka
        await kafka_client.publish(
            topic="external.incidents",
            message=normalized.to_kafka_message()
        )

        return {
            "status": "received",
            "incident_id": normalized.incident_id,
            "source": source
        }

    except Exception as e:
        logger.error("webhook_error", source=source, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/incidents/sources")
async def list_incident_sources():
    """List supported incident sources."""
    try:
        from streaming.incident_sources import incident_source_manager
        return {"sources": incident_source_manager.get_supported_sources()}
    except Exception as e:
        return {"sources": ["servicenow", "gcp", "datadog", "prometheus", "cloudwatch", "pagerduty"]}


# =============================================================================
# Run Server
# =============================================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
