"""
HITL (Human-in-the-Loop) API Endpoints
Handles approval requests and frontend integration
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import structlog
from datetime import datetime
import uuid

from gcp_issue_resolver import resolver, ApprovalStatus

logger = structlog.get_logger()

app = FastAPI(title="HITL Approval API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3002",
        "http://localhost:3000",
        "http://34.171.221.200:3002",
        "http://136.119.70.195:3002"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo incidents (replace with database in production)
mock_incidents = {}


class IncidentRequest(BaseModel):
    """Incident resolution request"""
    incident_id: str
    description: str
    gcp_context: dict = {}


class RoutingApprovalRequest(BaseModel):
    """Routing approval"""
    approval_id: str
    approved_agent: str
    comment: Optional[str] = None


class ExecutionApprovalRequest(BaseModel):
    """Execution approval"""
    approval_id: str
    approved: bool
    comment: Optional[str] = None


class ApprovalResponse(BaseModel):
    """Approval details for frontend"""
    approval_id: str
    type: str
    incident_id: str
    status: str
    data: dict
    created_at: str


@app.post("/api/incidents/resolve")
async def resolve_incident(request: IncidentRequest):
    """
    Start incident resolution workflow
    Returns immediately with approval_id for HITL Step 1
    """
    try:
        logger.info("incident_resolution_requested",
                   incident_id=request.incident_id)

        result = await resolver.resolve_issue(
            incident_id=request.incident_id,
            incident_description=request.description,
            gcp_context=request.gcp_context
        )

        return result

    except Exception as e:
        logger.error("resolve_incident_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/approvals/pending")
async def get_pending_approvals():
    """
    Get all pending HITL approvals for frontend
    """
    try:
        pending = [
            approval for approval in resolver.pending_approvals.values()
            if approval["status"] == ApprovalStatus.PENDING.value
        ]

        return {
            "count": len(pending),
            "approvals": pending
        }

    except Exception as e:
        logger.error("get_pending_approvals_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/approvals/{approval_id}")
async def get_approval(approval_id: str):
    """
    Get specific approval details
    """
    approval = resolver.pending_approvals.get(approval_id)

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    return approval


@app.post("/api/approvals/routing/approve")
async def approve_routing(request: RoutingApprovalRequest):
    """
    HITL Step 1: Approve agent routing (or override)
    """
    try:
        logger.info("routing_approved",
                   approval_id=request.approval_id,
                   agent=request.approved_agent)

        # Update approval status
        approval = resolver.pending_approvals.get(request.approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        approval["status"] = ApprovalStatus.APPROVED.value
        approval["comment"] = request.comment
        approval["approved_agent"] = request.approved_agent

        # Continue workflow
        result = await resolver.continue_after_routing_approval(
            approval_id=request.approval_id,
            approved_agent=request.approved_agent,
            incident_id=approval["incident_id"]
        )

        return result

    except Exception as e:
        logger.error("approve_routing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approvals/routing/reject")
async def reject_routing(approval_id: str, comment: str = ""):
    """
    HITL Step 1: Reject - requires manual intervention
    """
    try:
        logger.info("routing_rejected", approval_id=approval_id)

        approval = resolver.pending_approvals.get(approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        approval["status"] = ApprovalStatus.REJECTED.value
        approval["comment"] = comment

        return {
            "status": "rejected",
            "message": "Routing rejected. Manual intervention required.",
            "incident_id": approval["incident_id"]
        }

    except Exception as e:
        logger.error("reject_routing_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/approvals/execution/approve")
async def approve_execution(request: ExecutionApprovalRequest):
    """
    HITL Step 2: Approve execution plan
    """
    try:
        logger.info("execution_approved", approval_id=request.approval_id)

        approval = resolver.pending_approvals.get(request.approval_id)
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")

        if not request.approved:
            approval["status"] = ApprovalStatus.REJECTED.value
            approval["comment"] = request.comment
            return {
                "status": "rejected",
                "message": "Execution rejected",
                "incident_id": approval["incident_id"]
            }

        approval["status"] = ApprovalStatus.APPROVED.value
        approval["comment"] = request.comment

        # Execute plan
        result = await resolver.continue_after_execution_approval(
            approval_id=request.approval_id,
            incident_id=approval["incident_id"]
        )

        return result

    except Exception as e:
        logger.error("approve_execution_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/incidents/{incident_id}/workflow")
async def get_incident_workflow(incident_id: str):
    """
    Get workflow history for incident
    """
    # In production, fetch from database
    # For now, return from memory
    approvals = [
        a for a in resolver.pending_approvals.values()
        if a["incident_id"] == incident_id
    ]

    return {
        "incident_id": incident_id,
        "approvals": approvals,
        "count": len(approvals)
    }


@app.get("/api/incidents")
async def get_incidents(status: Optional[str] = None, limit: int = 50):
    """
    Get all incidents with optional status filter
    """
    incidents = list(mock_incidents.values())

    # Filter by status if provided
    if status:
        incidents = [i for i in incidents if i["status"] == status]

    # Sort by created date (newest first)
    incidents.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "total": len(incidents),
        "incidents": incidents[:limit]
    }


@app.post("/api/incidents/create")
async def create_incident(
    short_description: str,
    description: str,
    priority: str = "3",
    category: str = "Infrastructure",
    severity: str = "medium"
):
    """
    Create a new mock incident for testing
    """
    incident_id = f"INC{str(uuid.uuid4())[:8]}"

    incident = {
        "incident_id": incident_id,
        "number": incident_id,
        "short_description": short_description,
        "description": description,
        "priority": priority,
        "severity": severity,
        "status": "new",
        "state": "1",
        "category": category,
        "assignment_group": "Infrastructure",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    mock_incidents[incident_id] = incident

    logger.info("incident_created", incident_id=incident_id)

    return incident


@app.post("/api/incidents/import-from-servicenow")
async def import_from_servicenow(incidents: List[dict]):
    """
    Import incidents from ServiceNow (bulk import)
    Accepts array of ServiceNow incident objects
    """
    created = []

    for snow_inc in incidents:
        # Map ServiceNow fields to our format
        incident_id = f"INC{str(uuid.uuid4())[:8]}"

        # Map priority
        priority_map = {"1": "critical", "2": "high", "3": "medium", "4": "low", "5": "low"}
        priority = snow_inc.get('priority', '3')
        severity = priority_map.get(str(priority), "medium")

        incident = {
            "incident_id": incident_id,
            "number": snow_inc.get('number', incident_id),
            "short_description": snow_inc.get('short_description', 'No description'),
            "description": snow_inc.get('description', snow_inc.get('short_description', 'No description')),
            "priority": str(priority),
            "severity": severity,
            "status": "new",
            "state": snow_inc.get('state', '1'),
            "category": snow_inc.get('category', 'General'),
            "assignment_group": snow_inc.get('assignment_group', 'Infrastructure'),
            "created_at": snow_inc.get('sys_created_on', datetime.utcnow().isoformat()),
            "updated_at": datetime.utcnow().isoformat(),
            "servicenow_sys_id": snow_inc.get('sys_id'),
            "servicenow_number": snow_inc.get('number'),
        }

        mock_incidents[incident_id] = incident
        created.append(incident)

    logger.info("servicenow_incidents_imported", count=len(created))

    return {
        "message": f"Imported {len(created)} incidents from ServiceNow",
        "incidents": created
    }


@app.post("/api/incidents/create-samples")
async def create_sample_incidents():
    """
    Create sample incidents for testing
    """
    samples = [
        {
            "short_description": "GCP VM instance prod-web-01 is stopped",
            "description": "Production VM instance prod-web-01 in us-central1-a is stopped and not responding to health checks. Impact: 500 users affected.",
            "priority": "1",
            "severity": "critical",
            "category": "Infrastructure"
        },
        {
            "short_description": "Disk space critical on database server",
            "description": "PostgreSQL server disk usage at 95%. Need immediate cleanup or disk expansion.",
            "priority": "1",
            "severity": "high",
            "category": "Database"
        },
        {
            "short_description": "Application service crashed",
            "description": "Nginx service on web-server-03 has crashed. Application is unavailable.",
            "priority": "2",
            "severity": "high",
            "category": "Application"
        },
        {
            "short_description": "Network connectivity issues",
            "description": "Intermittent network connectivity between frontend and backend services.",
            "priority": "2",
            "severity": "medium",
            "category": "Network"
        },
        {
            "short_description": "Redis cache high memory usage",
            "description": "Redis instance consuming 90% memory. Need to implement TTL policies.",
            "priority": "3",
            "severity": "medium",
            "category": "Infrastructure"
        },
    ]

    created = []
    for sample in samples:
        incident_id = f"INC{str(uuid.uuid4())[:8]}"
        incident = {
            "incident_id": incident_id,
            "number": incident_id,
            "short_description": sample["short_description"],
            "description": sample["description"],
            "priority": sample["priority"],
            "severity": sample["severity"],
            "status": "new",
            "state": "1",
            "category": sample["category"],
            "assignment_group": "Infrastructure",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        mock_incidents[incident_id] = incident
        created.append(incident)

    logger.info("sample_incidents_created", count=len(created))

    return {
        "message": f"Created {len(created)} sample incidents",
        "incidents": created
    }


@app.get("/api/stats")
async def get_stats():
    """
    Get dashboard statistics
    """
    all_incidents = list(mock_incidents.values())

    return {
        "active_incidents": len([i for i in all_incidents if i["status"] in ["new", "in_progress"]]),
        "pending_approvals": len([
            a for a in resolver.pending_approvals.values()
            if a["status"] == ApprovalStatus.PENDING.value
        ]),
        "total_incidents": len(all_incidents),
        "success_rate": 95,  # Mock data
        "incidents_by_severity": {
            "critical": len([i for i in all_incidents if i["severity"] == "critical"]),
            "high": len([i for i in all_incidents if i["severity"] == "high"]),
            "medium": len([i for i in all_incidents if i["severity"] == "medium"]),
            "low": len([i for i in all_incidents if i["severity"] == "low"]),
        }
    }


@app.get("/api/agents")
async def get_agents():
    """
    Get agent status information
    """
    agents = [
        {
            "name": "Incident Analyzer",
            "status": "active",
            "tasks_completed": 145,
            "success_rate": 98,
            "last_active": datetime.utcnow().isoformat()
        },
        {
            "name": "Script Selector",
            "status": "active",
            "tasks_completed": 132,
            "success_rate": 100,
            "last_active": datetime.utcnow().isoformat()
        },
        {
            "name": "Executor",
            "status": "active",
            "tasks_completed": 128,
            "success_rate": 96,
            "last_active": datetime.utcnow().isoformat()
        },
        {
            "name": "Verification Agent",
            "status": "active",
            "tasks_completed": 128,
            "success_rate": 97,
            "last_active": datetime.utcnow().isoformat()
        },
        {
            "name": "Learning Agent",
            "status": "active",
            "tasks_completed": 89,
            "success_rate": 100,
            "last_active": datetime.utcnow().isoformat()
        },
        {
            "name": "Monitoring Agent",
            "status": "active",
            "tasks_completed": 1203,
            "success_rate": 99,
            "last_active": datetime.utcnow().isoformat()
        },
        {
            "name": "Notification Agent",
            "status": "active",
            "tasks_completed": 456,
            "success_rate": 100,
            "last_active": datetime.utcnow().isoformat()
        },
    ]

    return agents


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "HITL Approval API",
        "pending_approvals": len([
            a for a in resolver.pending_approvals.values()
            if a["status"] == ApprovalStatus.PENDING.value
        ])
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
