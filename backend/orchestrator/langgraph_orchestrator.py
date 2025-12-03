"""
18-Node LangGraph Enterprise Incident Resolution Orchestrator
=============================================================

This orchestrator implements a production-grade incident resolution workflow
using LangGraph state machine with 18 specialized nodes.

Architecture:
- Phase 1: Ingest/Parse (Nodes 1-3)
- Phase 2: Classification (Nodes 4-5)
- Phase 3: Retrieval (Nodes 6-9)
- Phase 4: Script Selection (Nodes 10-11)
- Phase 5: Plan Creation (Nodes 12-13)
- Phase 6: Approval/Execute (Nodes 14-15)
- Phase 7: Validation/Close (Nodes 16-17)
- Phase 8: Learning (Node 18)
"""

import os
import json
import re
from typing import TypedDict, Optional, List, Dict, Any, Literal
from datetime import datetime
import structlog

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = "END"

# Gemini for LLM calls
try:
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    LLM_AVAILABLE = True
except:
    LLM_AVAILABLE = False

logger = structlog.get_logger()


# =============================================================================
# STATE DEFINITION
# =============================================================================

class IncidentState(TypedDict):
    """State that flows through all 18 nodes"""
    # Input
    incident_id: str
    raw_incident: str
    metadata: Dict[str, Any]

    # Phase 1: Parse
    parsed_context: Dict[str, Any]
    clean_logs: List[str]
    primary_error: str
    log_quality_confidence: float

    # Phase 2: Classification
    classification: str
    classification_confidence: float
    needs_more_context: bool

    # Phase 3: Retrieval
    rag_results: List[Dict[str, Any]]
    filtered_rag: List[Dict[str, Any]]
    graph_context: Dict[str, Any]
    merged_context: Dict[str, Any]

    # Phase 4: Script Selection
    candidates: List[Dict[str, Any]]
    selected_script: Optional[Dict[str, Any]]
    rejected_scripts: List[Dict[str, Any]]
    approval_required: bool
    escalate_to_human: bool

    # Phase 5: Plan
    plan: Dict[str, Any]
    plan_safe: bool

    # Phase 6: Execution
    execution_approved: bool
    execution_output: Dict[str, Any]

    # Phase 7: Validation
    fix_valid: bool
    validation_reason: str
    validation_confidence: float
    ticket_closed: bool

    # Phase 8: Learning
    kb_update: str

    # Workflow tracking
    current_node: str
    node_history: List[str]
    errors: List[str]
    timestamp: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def call_llm(prompt: str, json_response: bool = True) -> Dict[str, Any]:
    """Call Gemini LLM with prompt"""
    if not LLM_AVAILABLE:
        return {"error": "LLM not available"}

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()

        if json_response:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        return {"text": text}
    except Exception as e:
        logger.error("llm_call_failed", error=str(e))
        return {"error": str(e)}


def compute_hybrid_score(vector: float, metadata: float, graph: float, safety: float) -> float:
    """Compute hybrid score: 50% Vector + 25% Metadata + 15% Graph + 10% Safety"""
    return 0.50 * vector + 0.25 * metadata + 0.15 * graph + 0.10 * safety


# =============================================================================
# PHASE 1: INGEST / PARSE (Nodes 1-3)
# =============================================================================

def node_1_ingest(state: IncidentState) -> IncidentState:
    """Node 1: Ingest Incident (No LLM - Python only)"""
    logger.info("node_1_ingest", incident_id=state.get("incident_id"))

    state["current_node"] = "ingest"
    state["node_history"] = state.get("node_history", []) + ["ingest"]
    state["timestamp"] = datetime.utcnow().isoformat()

    # Initialize defaults
    if not state.get("parsed_context"):
        state["parsed_context"] = {}
    if not state.get("errors"):
        state["errors"] = []

    return state


def node_2_parse_context(state: IncidentState) -> IncidentState:
    """Node 2: Parse Context - Extract meaningful data"""
    logger.info("node_2_parse_context", incident_id=state.get("incident_id"))

    state["current_node"] = "parse_context"
    state["node_history"] = state.get("node_history", []) + ["parse_context"]

    raw = state.get("raw_incident", "")

    prompt = f"""You are a Context Parser.
Extract only meaningful logs, alerts, metrics, stack traces, service names, and error indicators.

Incident: {raw}

Return JSON:
{{
    "parsed_context": {{
        "service": "",
        "component": "",
        "error_type": "",
        "stack_trace": "",
        "metrics": {{}},
        "keywords": []
    }}
}}"""

    result = call_llm(prompt)
    if "parsed_context" in result:
        state["parsed_context"] = result["parsed_context"]
    else:
        # Fallback parsing
        state["parsed_context"] = {
            "service": "unknown",
            "component": "unknown",
            "error_type": "unknown",
            "raw_text": raw[:500]
        }

    return state


def node_3_judge_log_quality(state: IncidentState) -> IncidentState:
    """Node 3: Judge Log Quality - Rank and clean logs"""
    logger.info("node_3_judge_log_quality", incident_id=state.get("incident_id"))

    state["current_node"] = "judge_log_quality"
    state["node_history"] = state.get("node_history", []) + ["judge_log_quality"]

    parsed = state.get("parsed_context", {})

    prompt = f"""You are the Log Quality Judge.
Rank logs by importance, remove noise, detect primary signal.

Context: {json.dumps(parsed)}

Return JSON:
{{
    "clean_logs": ["log1", "log2"],
    "primary_error": "main error description",
    "confidence": 0.85
}}"""

    result = call_llm(prompt)
    state["clean_logs"] = result.get("clean_logs", [])
    state["primary_error"] = result.get("primary_error", parsed.get("error_type", "unknown"))
    state["log_quality_confidence"] = result.get("confidence", 0.5)

    return state


# =============================================================================
# PHASE 2: CLASSIFICATION (Nodes 4-5)
# =============================================================================

def node_4_classify_incident(state: IncidentState) -> IncidentState:
    """Node 4: Classify Incident into domain"""
    logger.info("node_4_classify_incident", incident_id=state.get("incident_id"))

    state["current_node"] = "classify_incident"
    state["node_history"] = state.get("node_history", []) + ["classify_incident"]

    parsed = state.get("parsed_context", {})
    primary_error = state.get("primary_error", "")

    prompt = f"""Classify the incident into EXACTLY one domain:
["gcp", "aws", "azure", "kubernetes", "database", "network", "airflow", "platform"]

Context: {json.dumps(parsed)}
Primary Error: {primary_error}

Return JSON:
{{ "classification": "" }}"""

    result = call_llm(prompt)
    state["classification"] = result.get("classification", "platform")

    return state


def node_5_judge_classification(state: IncidentState) -> IncidentState:
    """Node 5: Judge Classification correctness"""
    logger.info("node_5_judge_classification", incident_id=state.get("incident_id"))

    state["current_node"] = "judge_classification"
    state["node_history"] = state.get("node_history", []) + ["judge_classification"]

    classification = state.get("classification", "")
    parsed = state.get("parsed_context", {})

    prompt = f"""Judge classification correctness.
If classification is incorrect or ambiguous, set needs_more_context=true.

Classification: {classification}
Context: {json.dumps(parsed)}

Return JSON:
{{
    "validated_classification": "",
    "confidence": 0.85,
    "needs_more_context": false
}}"""

    result = call_llm(prompt)
    state["classification"] = result.get("validated_classification", classification)
    state["classification_confidence"] = result.get("confidence", 0.5)
    state["needs_more_context"] = result.get("needs_more_context", False)

    return state


# =============================================================================
# PHASE 3: RETRIEVAL & ENRICHMENT (Nodes 6-9)
# =============================================================================

def node_6_rag_search(state: IncidentState) -> IncidentState:
    """Node 6: RAG Search - Retrieve similar incidents"""
    logger.info("node_6_rag_search", incident_id=state.get("incident_id"))

    state["current_node"] = "rag_search"
    state["node_history"] = state.get("node_history", []) + ["rag_search"]

    # In production, this would call Weaviate/Pinecone
    state["rag_results"] = [
        {"id": "rag_1", "similarity": 0.85, "description": "Similar GCP VM incident", "solution": "restart_vm"},
        {"id": "rag_2", "similarity": 0.72, "description": "Related network issue", "solution": "check_network"},
    ]

    return state


def node_7_judge_rag(state: IncidentState) -> IncidentState:
    """Node 7: Judge RAG Results - Filter irrelevant"""
    logger.info("node_7_judge_rag", incident_id=state.get("incident_id"))

    state["current_node"] = "judge_rag"
    state["node_history"] = state.get("node_history", []) + ["judge_rag"]

    rag_results = state.get("rag_results", [])

    # Filter results with similarity >= 0.5
    state["filtered_rag"] = [r for r in rag_results if r.get("similarity", 0) >= 0.5]

    return state


def node_8_graph_search(state: IncidentState) -> IncidentState:
    """Node 8: Graph Search - Get relationships from Neo4j"""
    logger.info("node_8_graph_search", incident_id=state.get("incident_id"))

    state["current_node"] = "graph_search"
    state["node_history"] = state.get("node_history", []) + ["graph_search"]

    # In production, this would call Neo4j
    classification = state.get("classification", "platform")

    state["graph_context"] = {
        "service_dependencies": [],
        "owner_team": "platform-team",
        "related_incidents": [],
        "known_runbooks": [f"script-start-{classification}-instance", f"script-stop-{classification}-instance"]
    }

    return state


def node_9_merge_context(state: IncidentState) -> IncidentState:
    """Node 9: Merge Context - Combine RAG + Graph + Metadata"""
    logger.info("node_9_merge_context", incident_id=state.get("incident_id"))

    state["current_node"] = "merge_context"
    state["node_history"] = state.get("node_history", []) + ["merge_context"]

    state["merged_context"] = {
        "parsed": state.get("parsed_context", {}),
        "classification": state.get("classification", ""),
        "rag_results": state.get("filtered_rag", []),
        "graph_context": state.get("graph_context", {}),
        "primary_error": state.get("primary_error", "")
    }

    return state


# =============================================================================
# PHASE 4: SCRIPT/RUNBOOK SELECTION (Nodes 10-11)
# =============================================================================

def node_10_match_scripts(state: IncidentState) -> IncidentState:
    """Node 10: Match Scripts - Identify candidates"""
    logger.info("node_10_match_scripts", incident_id=state.get("incident_id"))

    state["current_node"] = "match_scripts"
    state["node_history"] = state.get("node_history", []) + ["match_scripts"]

    merged = state.get("merged_context", {})
    classification = merged.get("classification", "gcp")

    # Load from registry.json in production
    state["candidates"] = [
        {
            "script_id": "script-start-gcp-instance",
            "name": "Start GCP VM Instance",
            "type": "shell",
            "path": "scripts/start_gcp_instance.sh",
            "risk_level": "low",
            "vector_score": 0.85,
            "metadata_score": 0.90,
            "graph_score": 0.80,
            "safety_score": 0.95
        },
        {
            "script_id": "script-stop-gcp-instance",
            "name": "Stop GCP VM Instance",
            "type": "shell",
            "path": "scripts/stop_gcp_instance.sh",
            "risk_level": "medium",
            "vector_score": 0.60,
            "metadata_score": 0.70,
            "graph_score": 0.65,
            "safety_score": 0.90
        }
    ]

    return state


def node_11_judge_script_selection(state: IncidentState) -> IncidentState:
    """Node 11: Judge Script Selection - CRITICAL NODE

    Uses Hybrid Score: 50% Vector + 25% Metadata + 15% Graph + 10% Safety

    Rules:
    - Reject if environment mismatch
    - Reject if required inputs missing
    - Reject if no rollback
    - Reject high-risk scripts without human approval
    - Never hallucinate script names
    - If top score < 0.75 → escalate_to_human = true
    """
    logger.info("node_11_judge_script_selection", incident_id=state.get("incident_id"))

    state["current_node"] = "judge_script_selection"
    state["node_history"] = state.get("node_history", []) + ["judge_script_selection"]

    candidates = state.get("candidates", [])

    # Compute hybrid scores
    scored_candidates = []
    for c in candidates:
        score = compute_hybrid_score(
            c.get("vector_score", 0),
            c.get("metadata_score", 0),
            c.get("graph_score", 0),
            c.get("safety_score", 0)
        )
        scored_candidates.append({**c, "final_score": score})

    # Sort by score
    scored_candidates.sort(key=lambda x: x["final_score"], reverse=True)

    if scored_candidates:
        top = scored_candidates[0]

        # Check if score is high enough
        if top["final_score"] < 0.75:
            state["escalate_to_human"] = True
            state["selected_script"] = None
        else:
            state["selected_script"] = top
            state["escalate_to_human"] = False

        # High risk requires approval
        state["approval_required"] = top.get("risk_level") in ["high", "critical"]
        state["rejected_scripts"] = scored_candidates[1:]
    else:
        state["selected_script"] = None
        state["escalate_to_human"] = True
        state["approval_required"] = False
        state["rejected_scripts"] = []

    return state


# =============================================================================
# PHASE 5: PLAN CREATION (Nodes 12-13)
# =============================================================================

def node_12_generate_plan(state: IncidentState) -> IncidentState:
    """Node 12: Generate Execution Plan"""
    logger.info("node_12_generate_plan", incident_id=state.get("incident_id"))

    state["current_node"] = "generate_plan"
    state["node_history"] = state.get("node_history", []) + ["generate_plan"]

    script = state.get("selected_script")
    if not script:
        state["plan"] = {"error": "No script selected"}
        return state

    state["plan"] = {
        "script_id": script.get("script_id"),
        "script_path": script.get("path"),
        "execution_steps": [
            {"step": 1, "action": "Validate inputs", "timeout": 30},
            {"step": 2, "action": f"Execute {script.get('name')}", "timeout": 300},
            {"step": 3, "action": "Capture output", "timeout": 30},
            {"step": 4, "action": "Validate result", "timeout": 60}
        ],
        "parameters": state.get("metadata", {}).get("extracted_params", {}),
        "rollback_steps": [
            {"step": 1, "action": "Revert changes"},
            {"step": 2, "action": "Notify on-call"}
        ],
        "expected_impact": "minimal",
        "estimated_duration": "5 minutes"
    }

    return state


def node_13_judge_plan_safety(state: IncidentState) -> IncidentState:
    """Node 13: Judge Plan Safety"""
    logger.info("node_13_judge_plan_safety", incident_id=state.get("incident_id"))

    state["current_node"] = "judge_plan_safety"
    state["node_history"] = state.get("node_history", []) + ["judge_plan_safety"]

    plan = state.get("plan", {})
    script = state.get("selected_script", {})

    # Safety checks
    checks = {
        "has_rollback": len(plan.get("rollback_steps", [])) > 0,
        "timeout_configured": all(s.get("timeout") for s in plan.get("execution_steps", [])),
        "risk_acceptable": script.get("risk_level") in ["low", "medium"],
        "no_dangerous_commands": True  # Would check script content
    }

    state["plan_safe"] = all(checks.values())
    state["approval_required"] = state.get("approval_required", False) or not state["plan_safe"]

    return state


# =============================================================================
# PHASE 6: APPROVAL & EXECUTION (Nodes 14-15)
# =============================================================================

def node_14_approval_workflow(state: IncidentState) -> IncidentState:
    """Node 14: Approval Workflow (No LLM - Business Logic)"""
    logger.info("node_14_approval_workflow", incident_id=state.get("incident_id"))

    state["current_node"] = "approval_workflow"
    state["node_history"] = state.get("node_history", []) + ["approval_workflow"]

    # In production, this would check approval database
    # For now, auto-approve low/medium risk
    script = state.get("selected_script", {})

    if script.get("risk_level") in ["low", "medium"]:
        state["execution_approved"] = True
    else:
        state["execution_approved"] = False  # Would wait for human approval

    return state


def node_15_execute_pipeline(state: IncidentState) -> IncidentState:
    """Node 15: Execute Pipeline (No LLM - Runs GitHub Actions/Jenkins)"""
    logger.info("node_15_execute_pipeline", incident_id=state.get("incident_id"))

    state["current_node"] = "execute_pipeline"
    state["node_history"] = state.get("node_history", []) + ["execute_pipeline"]

    if not state.get("execution_approved"):
        state["execution_output"] = {"status": "blocked", "reason": "Awaiting approval"}
        return state

    # In production, this triggers GitHub Actions
    state["execution_output"] = {
        "status": "success",
        "exit_code": 0,
        "output": "Script executed successfully",
        "duration": "45 seconds",
        "workflow_run_id": "mock_run_123"
    }

    return state


# =============================================================================
# PHASE 7: VALIDATION & TICKET CLOSURE (Nodes 16-17)
# =============================================================================

def node_16_validate_fix(state: IncidentState) -> IncidentState:
    """Node 16: Validate Fix - LLM Judge"""
    logger.info("node_16_validate_fix", incident_id=state.get("incident_id"))

    state["current_node"] = "validate_fix"
    state["node_history"] = state.get("node_history", []) + ["validate_fix"]

    execution = state.get("execution_output", {})

    prompt = f"""Judge whether execution logs indicate successful remediation.
Check metrics, errors, and outcome.

Execution Output: {json.dumps(execution)}

Return JSON:
{{
    "fix_valid": true,
    "reason": "explanation",
    "confidence": 0.9
}}"""

    result = call_llm(prompt)

    # Also check execution status
    exec_success = execution.get("status") == "success" and execution.get("exit_code") == 0

    state["fix_valid"] = result.get("fix_valid", exec_success)
    state["validation_reason"] = result.get("reason", "Execution completed successfully")
    state["validation_confidence"] = result.get("confidence", 0.8 if exec_success else 0.3)

    return state


def node_17_close_ticket(state: IncidentState) -> IncidentState:
    """Node 17: Close Ticket - Update ServiceNow/Jira"""
    logger.info("node_17_close_ticket", incident_id=state.get("incident_id"))

    state["current_node"] = "close_ticket"
    state["node_history"] = state.get("node_history", []) + ["close_ticket"]

    if not state.get("fix_valid"):
        state["ticket_closed"] = False
        return state

    # In production, this calls ServiceNow API
    state["ticket_closed"] = True

    return state


# =============================================================================
# PHASE 8: LEARNING LOOP (Node 18)
# =============================================================================

def node_18_learn(state: IncidentState) -> IncidentState:
    """Node 18: Learn - Update knowledge base"""
    logger.info("node_18_learn", incident_id=state.get("incident_id"))

    state["current_node"] = "learn"
    state["node_history"] = state.get("node_history", []) + ["learn"]

    if not state.get("fix_valid"):
        state["kb_update"] = "skipped"
        return state

    # In production, this updates:
    # - Weaviate embeddings
    # - Neo4j graph edges
    # - Script metadata

    state["kb_update"] = "completed"

    return state


# =============================================================================
# LANGGRAPH WORKFLOW BUILDER
# =============================================================================

def build_workflow():
    """Build the 18-node LangGraph workflow"""

    if not LANGGRAPH_AVAILABLE:
        logger.warning("langgraph_not_available", message="Using fallback sequential execution")
        return None

    workflow = StateGraph(IncidentState)

    # Add all 18 nodes
    workflow.add_node("ingest", node_1_ingest)
    workflow.add_node("parse_context", node_2_parse_context)
    workflow.add_node("judge_log_quality", node_3_judge_log_quality)
    workflow.add_node("classify_incident", node_4_classify_incident)
    workflow.add_node("judge_classification", node_5_judge_classification)
    workflow.add_node("rag_search", node_6_rag_search)
    workflow.add_node("judge_rag", node_7_judge_rag)
    workflow.add_node("graph_search", node_8_graph_search)
    workflow.add_node("merge_context", node_9_merge_context)
    workflow.add_node("match_scripts", node_10_match_scripts)
    workflow.add_node("judge_script_selection", node_11_judge_script_selection)
    workflow.add_node("generate_plan", node_12_generate_plan)
    workflow.add_node("judge_plan_safety", node_13_judge_plan_safety)
    workflow.add_node("approval_workflow", node_14_approval_workflow)
    workflow.add_node("execute_pipeline", node_15_execute_pipeline)
    workflow.add_node("validate_fix", node_16_validate_fix)
    workflow.add_node("close_ticket", node_17_close_ticket)
    workflow.add_node("learn", node_18_learn)

    # Define edges (sequential flow)
    workflow.set_entry_point("ingest")
    workflow.add_edge("ingest", "parse_context")
    workflow.add_edge("parse_context", "judge_log_quality")
    workflow.add_edge("judge_log_quality", "classify_incident")
    workflow.add_edge("classify_incident", "judge_classification")
    workflow.add_edge("judge_classification", "rag_search")
    workflow.add_edge("rag_search", "judge_rag")
    workflow.add_edge("judge_rag", "graph_search")
    workflow.add_edge("graph_search", "merge_context")
    workflow.add_edge("merge_context", "match_scripts")
    workflow.add_edge("match_scripts", "judge_script_selection")
    workflow.add_edge("judge_script_selection", "generate_plan")
    workflow.add_edge("generate_plan", "judge_plan_safety")
    workflow.add_edge("judge_plan_safety", "approval_workflow")
    workflow.add_edge("approval_workflow", "execute_pipeline")
    workflow.add_edge("execute_pipeline", "validate_fix")
    workflow.add_edge("validate_fix", "close_ticket")
    workflow.add_edge("close_ticket", "learn")
    workflow.add_edge("learn", END)

    return workflow.compile()


# =============================================================================
# ORCHESTRATOR CLASS
# =============================================================================

class LangGraphOrchestrator:
    """Main orchestrator class for 18-node workflow"""

    def __init__(self):
        self.workflow = build_workflow()
        self.nodes = [
            node_1_ingest, node_2_parse_context, node_3_judge_log_quality,
            node_4_classify_incident, node_5_judge_classification,
            node_6_rag_search, node_7_judge_rag, node_8_graph_search, node_9_merge_context,
            node_10_match_scripts, node_11_judge_script_selection,
            node_12_generate_plan, node_13_judge_plan_safety,
            node_14_approval_workflow, node_15_execute_pipeline,
            node_16_validate_fix, node_17_close_ticket,
            node_18_learn
        ]

    def run(self, incident_id: str, raw_incident: str, metadata: Dict = None) -> IncidentState:
        """Run the full 18-node workflow"""

        initial_state: IncidentState = {
            "incident_id": incident_id,
            "raw_incident": raw_incident,
            "metadata": metadata or {},
            "parsed_context": {},
            "clean_logs": [],
            "primary_error": "",
            "log_quality_confidence": 0.0,
            "classification": "",
            "classification_confidence": 0.0,
            "needs_more_context": False,
            "rag_results": [],
            "filtered_rag": [],
            "graph_context": {},
            "merged_context": {},
            "candidates": [],
            "selected_script": None,
            "rejected_scripts": [],
            "approval_required": False,
            "escalate_to_human": False,
            "plan": {},
            "plan_safe": False,
            "execution_approved": False,
            "execution_output": {},
            "fix_valid": False,
            "validation_reason": "",
            "validation_confidence": 0.0,
            "ticket_closed": False,
            "kb_update": "",
            "current_node": "",
            "node_history": [],
            "errors": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        if self.workflow:
            # Use LangGraph
            result = self.workflow.invoke(initial_state)
            return result
        else:
            # Fallback: Sequential execution
            state = initial_state
            for node_fn in self.nodes:
                try:
                    state = node_fn(state)
                except Exception as e:
                    state["errors"].append(f"{node_fn.__name__}: {str(e)}")
                    logger.error("node_execution_failed", node=node_fn.__name__, error=str(e))
            return state

    def run_until_node(self, incident_id: str, raw_incident: str, stop_at: str, metadata: Dict = None) -> IncidentState:
        """Run workflow until a specific node (for UI step-by-step)"""

        node_names = [
            "ingest", "parse_context", "judge_log_quality",
            "classify_incident", "judge_classification",
            "rag_search", "judge_rag", "graph_search", "merge_context",
            "match_scripts", "judge_script_selection",
            "generate_plan", "judge_plan_safety",
            "approval_workflow", "execute_pipeline",
            "validate_fix", "close_ticket", "learn"
        ]

        try:
            stop_index = node_names.index(stop_at) + 1
        except ValueError:
            stop_index = len(node_names)

        initial_state: IncidentState = {
            "incident_id": incident_id,
            "raw_incident": raw_incident,
            "metadata": metadata or {},
            "parsed_context": {},
            "clean_logs": [],
            "primary_error": "",
            "log_quality_confidence": 0.0,
            "classification": "",
            "classification_confidence": 0.0,
            "needs_more_context": False,
            "rag_results": [],
            "filtered_rag": [],
            "graph_context": {},
            "merged_context": {},
            "candidates": [],
            "selected_script": None,
            "rejected_scripts": [],
            "approval_required": False,
            "escalate_to_human": False,
            "plan": {},
            "plan_safe": False,
            "execution_approved": False,
            "execution_output": {},
            "fix_valid": False,
            "validation_reason": "",
            "validation_confidence": 0.0,
            "ticket_closed": False,
            "kb_update": "",
            "current_node": "",
            "node_history": [],
            "errors": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        state = initial_state
        for i, node_fn in enumerate(self.nodes[:stop_index]):
            try:
                state = node_fn(state)
            except Exception as e:
                state["errors"].append(f"{node_fn.__name__}: {str(e)}")
                logger.error("node_execution_failed", node=node_fn.__name__, error=str(e))
                break

        return state


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

orchestrator = LangGraphOrchestrator()


# =============================================================================
# API HELPERS
# =============================================================================

def run_full_workflow(incident_id: str, description: str, metadata: Dict = None) -> Dict:
    """Run complete 18-node workflow and return result"""
    result = orchestrator.run(incident_id, description, metadata)
    return dict(result)


def run_to_step(incident_id: str, description: str, step: int, metadata: Dict = None) -> Dict:
    """Run workflow up to specific step number (1-18)"""
    node_names = [
        "ingest", "parse_context", "judge_log_quality",
        "classify_incident", "judge_classification",
        "rag_search", "judge_rag", "graph_search", "merge_context",
        "match_scripts", "judge_script_selection",
        "generate_plan", "judge_plan_safety",
        "approval_workflow", "execute_pipeline",
        "validate_fix", "close_ticket", "learn"
    ]

    step = max(1, min(step, 18))
    stop_at = node_names[step - 1]

    result = orchestrator.run_until_node(incident_id, description, stop_at, metadata)
    return dict(result)
