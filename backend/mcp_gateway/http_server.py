#!/usr/bin/env python3
"""
MCP HTTP Gateway Server
Exposes MCP server functionality as HTTP REST APIs
Port: 8001
"""

import os
import sys
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx
import structlog

# Add parent paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = structlog.get_logger()

app = FastAPI(
    title="MCP HTTP Gateway",
    description="HTTP REST API gateway for MCP servers (ServiceNow, GCP, GitHub, Jira)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Models
# ============================================================================

class ToolCall(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class MCPServerStatus(BaseModel):
    name: str
    status: str
    tools: List[str]
    last_call: Optional[str] = None

# ============================================================================
# ServiceNow MCP Tools
# ============================================================================

class ServiceNowClient:
    """HTTP client for ServiceNow operations"""

    def __init__(self):
        self.instance_url = os.getenv("SNOW_INSTANCE_URL", "")
        self.username = os.getenv("SNOW_USERNAME", "")
        self.password = os.getenv("SNOW_PASSWORD", "")
        self.last_call = None

    @property
    def is_configured(self) -> bool:
        return all([self.instance_url, self.username, self.password])

    async def get_incident(self, incident_id: str) -> Dict:
        """Get incident by ID"""
        self.last_call = datetime.now().isoformat()
        async with httpx.AsyncClient(auth=(self.username, self.password), timeout=30) as client:
            url = f"{self.instance_url}/api/now/table/incident"
            response = await client.get(url, params={"sysparm_query": f"number={incident_id}", "sysparm_limit": 1})
            response.raise_for_status()
            data = response.json()
            results = data.get("result", [])
            return results[0] if results else {"error": f"Incident {incident_id} not found"}

    async def create_incident(self, short_description: str, description: str, priority: str = "3") -> Dict:
        """Create new incident"""
        self.last_call = datetime.now().isoformat()
        async with httpx.AsyncClient(auth=(self.username, self.password), timeout=30) as client:
            url = f"{self.instance_url}/api/now/table/incident"
            payload = {
                "short_description": short_description,
                "description": description,
                "priority": priority,
                "state": "1"
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("result", {})

    async def update_incident(self, incident_id: str, updates: Dict) -> Dict:
        """Update incident"""
        self.last_call = datetime.now().isoformat()
        # First get sys_id
        incident = await self.get_incident(incident_id)
        if "error" in incident:
            return incident

        sys_id = incident.get("sys_id")
        async with httpx.AsyncClient(auth=(self.username, self.password), timeout=30) as client:
            url = f"{self.instance_url}/api/now/table/incident/{sys_id}"
            response = await client.patch(url, json=updates)
            response.raise_for_status()
            return {"status": "updated", "incident_id": incident_id, "fields": list(updates.keys())}

    async def search_incidents(self, query: str, limit: int = 10) -> List[Dict]:
        """Search incidents"""
        self.last_call = datetime.now().isoformat()
        async with httpx.AsyncClient(auth=(self.username, self.password), timeout=30) as client:
            url = f"{self.instance_url}/api/now/table/incident"
            response = await client.get(url, params={"sysparm_query": query, "sysparm_limit": limit})
            response.raise_for_status()
            return response.json().get("result", [])

# ============================================================================
# GCP MCP Tools
# ============================================================================

class GCPClient:
    """Client for GCP operations"""

    def __init__(self):
        self.project = os.getenv("GCP_PROJECT_ID", "agent-ai-test-461120")
        self.last_call = None

    @property
    def is_configured(self) -> bool:
        return os.path.exists(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))

    async def list_instances(self, zone: str = "us-central1-a") -> List[Dict]:
        """List GCP VM instances"""
        self.last_call = datetime.now().isoformat()
        import subprocess
        import json
        try:
            result = subprocess.run(
                ["gcloud", "compute", "instances", "list", "--format=json"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                instances = json.loads(result.stdout)
                return [{"name": i.get("name"), "zone": i.get("zone", "").split("/")[-1],
                        "status": i.get("status"), "machineType": i.get("machineType", "").split("/")[-1]}
                       for i in instances]
        except Exception as e:
            logger.error(f"GCP list instances failed: {e}")
        return []

    async def start_instance(self, instance_name: str, zone: str) -> Dict:
        """Start a GCP VM instance"""
        self.last_call = datetime.now().isoformat()
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "compute", "instances", "start", instance_name, f"--zone={zone}"],
                capture_output=True, text=True, timeout=120
            )
            return {"status": "started" if result.returncode == 0 else "failed",
                   "instance": instance_name, "zone": zone, "output": result.stdout or result.stderr}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def stop_instance(self, instance_name: str, zone: str) -> Dict:
        """Stop a GCP VM instance"""
        self.last_call = datetime.now().isoformat()
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "compute", "instances", "stop", instance_name, f"--zone={zone}"],
                capture_output=True, text=True, timeout=120
            )
            return {"status": "stopped" if result.returncode == 0 else "failed",
                   "instance": instance_name, "zone": zone}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_instance_status(self, instance_name: str, zone: str) -> Dict:
        """Get VM instance status"""
        self.last_call = datetime.now().isoformat()
        instances = await self.list_instances(zone)
        for inst in instances:
            if inst["name"] == instance_name:
                return inst
        return {"error": f"Instance {instance_name} not found"}

# ============================================================================
# GitHub MCP Tools
# ============================================================================

class GitHubClient:
    """Client for GitHub operations"""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.last_call = None

    @property
    def is_configured(self) -> bool:
        return bool(self.token)

    async def list_repos(self, org: str = None) -> List[Dict]:
        """List repositories"""
        self.last_call = datetime.now().isoformat()
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"token {self.token}"}
            url = f"https://api.github.com/user/repos" if not org else f"https://api.github.com/orgs/{org}/repos"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            repos = response.json()
            return [{"name": r["name"], "full_name": r["full_name"], "url": r["html_url"]} for r in repos[:20]]

    async def get_file(self, owner: str, repo: str, path: str) -> Dict:
        """Get file content from repo"""
        self.last_call = datetime.now().isoformat()
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"token {self.token}"}
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def create_issue(self, owner: str, repo: str, title: str, body: str) -> Dict:
        """Create GitHub issue"""
        self.last_call = datetime.now().isoformat()
        async with httpx.AsyncClient(timeout=30) as client:
            headers = {"Authorization": f"token {self.token}"}
            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            response = await client.post(url, headers=headers, json={"title": title, "body": body})
            response.raise_for_status()
            return response.json()

# ============================================================================
# Jira MCP Tools
# ============================================================================

class JiraClient:
    """Client for Jira operations"""

    def __init__(self):
        self.url = os.getenv("JIRA_URL", "")
        self.username = os.getenv("JIRA_USERNAME", "")
        self.token = os.getenv("JIRA_API_TOKEN", "")
        self.last_call = None

    @property
    def is_configured(self) -> bool:
        return all([self.url, self.username, self.token])

    async def get_issue(self, issue_key: str) -> Dict:
        """Get Jira issue"""
        self.last_call = datetime.now().isoformat()
        if not self.is_configured:
            return {"error": "Jira not configured"}
        async with httpx.AsyncClient(auth=(self.username, self.token), timeout=30) as client:
            url = f"{self.url}/rest/api/3/issue/{issue_key}"
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    async def create_issue(self, project: str, summary: str, description: str, issue_type: str = "Task") -> Dict:
        """Create Jira issue"""
        self.last_call = datetime.now().isoformat()
        if not self.is_configured:
            return {"error": "Jira not configured"}
        async with httpx.AsyncClient(auth=(self.username, self.token), timeout=30) as client:
            url = f"{self.url}/rest/api/3/issue"
            payload = {
                "fields": {
                    "project": {"key": project},
                    "summary": summary,
                    "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]},
                    "issuetype": {"name": issue_type}
                }
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

# ============================================================================
# Initialize Clients
# ============================================================================

servicenow_client = ServiceNowClient()
gcp_client = GCPClient()
github_client = GitHubClient()
jira_client = JiraClient()

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "mcp-gateway", "port": 8001}

@app.get("/api/mcp/servers")
async def list_mcp_servers():
    """List all MCP servers and their status"""
    return {
        "servers": [
            {
                "name": "servicenow-mcp",
                "display_name": "ServiceNow",
                "status": "active" if servicenow_client.is_configured else "not_configured",
                "tools": ["get_incident", "create_incident", "update_incident", "search_incidents"],
                "last_call": servicenow_client.last_call,
                "icon": "🎫"
            },
            {
                "name": "gcp-mcp",
                "display_name": "GCP",
                "status": "active" if gcp_client.is_configured else "not_configured",
                "tools": ["list_instances", "start_instance", "stop_instance", "get_instance_status"],
                "last_call": gcp_client.last_call,
                "icon": "☁️"
            },
            {
                "name": "github-mcp",
                "display_name": "GitHub",
                "status": "active" if github_client.is_configured else "not_configured",
                "tools": ["list_repos", "get_file", "create_issue"],
                "last_call": github_client.last_call,
                "icon": "🐙"
            },
            {
                "name": "jira-mcp",
                "display_name": "Jira",
                "status": "active" if jira_client.is_configured else "not_configured",
                "tools": ["get_issue", "create_issue"],
                "last_call": jira_client.last_call,
                "icon": "📋"
            }
        ]
    }

# ServiceNow Endpoints
@app.get("/api/mcp/servicenow/incident/{incident_id}")
async def get_servicenow_incident(incident_id: str):
    try:
        return await servicenow_client.get_incident(incident_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/servicenow/incident")
async def create_servicenow_incident(short_description: str, description: str, priority: str = "3"):
    try:
        return await servicenow_client.create_incident(short_description, description, priority)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/servicenow/search")
async def search_servicenow_incidents(query: str, limit: int = 10):
    try:
        return await servicenow_client.search_incidents(query, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GCP Endpoints
@app.get("/api/mcp/gcp/instances")
async def list_gcp_instances(zone: str = "us-central1-a"):
    try:
        return await gcp_client.list_instances(zone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/gcp/instances/{instance_name}/start")
async def start_gcp_instance(instance_name: str, zone: str = "us-central1-a"):
    try:
        return await gcp_client.start_instance(instance_name, zone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/gcp/instances/{instance_name}/stop")
async def stop_gcp_instance(instance_name: str, zone: str = "us-central1-a"):
    try:
        return await gcp_client.stop_instance(instance_name, zone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/gcp/instances/{instance_name}")
async def get_gcp_instance(instance_name: str, zone: str = "us-central1-a"):
    try:
        return await gcp_client.get_instance_status(instance_name, zone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# GitHub Endpoints
@app.get("/api/mcp/github/repos")
async def list_github_repos(org: str = None):
    try:
        return await github_client.list_repos(org)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/github/file")
async def get_github_file(owner: str, repo: str, path: str):
    try:
        return await github_client.get_file(owner, repo, path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/github/issue")
async def create_github_issue(owner: str, repo: str, title: str, body: str):
    try:
        return await github_client.create_issue(owner, repo, title, body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Jira Endpoints
@app.get("/api/mcp/jira/issue/{issue_key}")
async def get_jira_issue(issue_key: str):
    try:
        return await jira_client.get_issue(issue_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generic Tool Call Endpoint
@app.post("/api/mcp/call")
async def call_mcp_tool(server: str, tool: ToolCall):
    """Generic endpoint to call any MCP tool"""
    try:
        if server == "servicenow":
            if tool.tool_name == "get_incident":
                return await servicenow_client.get_incident(tool.arguments["incident_id"])
            elif tool.tool_name == "search_incidents":
                return await servicenow_client.search_incidents(tool.arguments["query"], tool.arguments.get("limit", 10))
        elif server == "gcp":
            if tool.tool_name == "list_instances":
                return await gcp_client.list_instances(tool.arguments.get("zone", "us-central1-a"))
            elif tool.tool_name == "start_instance":
                return await gcp_client.start_instance(tool.arguments["instance_name"], tool.arguments["zone"])
            elif tool.tool_name == "stop_instance":
                return await gcp_client.stop_instance(tool.arguments["instance_name"], tool.arguments["zone"])
        elif server == "github":
            if tool.tool_name == "list_repos":
                return await github_client.list_repos(tool.arguments.get("org"))
        elif server == "jira":
            if tool.tool_name == "get_issue":
                return await jira_client.get_issue(tool.arguments["issue_key"])

        raise HTTPException(status_code=400, detail=f"Unknown server/tool: {server}/{tool.tool_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    print("Starting MCP HTTP Gateway on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
