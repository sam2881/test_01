"""ServiceNow Agent for incident triage, diagnosis, and resolution"""
import os
import sys
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent
from rag.hybrid_search import hybrid_rag
from agents.servicenow.dspy_modules import ServiceNowModule
import pysnow
import structlog

logger = structlog.get_logger()

app = FastAPI(title="ServiceNow Agent")


class IncidentTask(BaseModel):
    """Incident task schema"""
    task_id: str
    task_type: str
    incident_id: Optional[str] = None
    description: str
    service: Optional[str] = None
    priority: Optional[str] = None


class ServiceNowAgent(BaseAgent):
    """Agent for handling ServiceNow incidents"""

    def __init__(self):
        super().__init__(agent_name="ServiceNowAgent", agent_type="incident_management")

        # Initialize ServiceNow client
        self.snow_instance = os.getenv("SNOW_INSTANCE_URL", "").replace("https://", "")
        self.snow_user = os.getenv("SNOW_USERNAME", "admin")
        self.snow_password = os.getenv("SNOW_PASSWORD", "")

        try:
            self.snow_client = pysnow.Client(
                instance=self.snow_instance,
                user=self.snow_user,
                password=self.snow_password
            )
            self.incident_table = self.snow_client.resource(api_path='/table/incident')
            logger.info("servicenow_client_initialized", instance=self.snow_instance)
        except Exception as e:
            logger.warning("servicenow_client_init_failed", error=str(e))
            self.snow_client = None

        # Initialize DSPy module
        self.dspy_module = ServiceNowModule()

        # Initialize RAG
        self.rag = hybrid_rag

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate incident task input"""
        required_fields = ["task_id", "description"]
        return all(field in task for field in required_fields)

    def get_incident_from_snow(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Fetch incident from ServiceNow"""
        if not self.snow_client:
            logger.warning("snow_client_not_configured")
            return None

        try:
            response = self.incident_table.get(
                query={'number': incident_id},
                limit=1
            )
            incident = response.one()
            return dict(incident)
        except Exception as e:
            logger.error("snow_get_incident_error", error=str(e), incident_id=incident_id)
            return None

    def update_incident_in_snow(self, incident_id: str, updates: Dict[str, Any]):
        """Update incident in ServiceNow"""
        if not self.snow_client:
            logger.warning("snow_client_not_configured")
            return

        try:
            self.incident_table.update(
                query={'number': incident_id},
                payload=updates
            )
            logger.info("snow_incident_updated", incident_id=incident_id)
        except Exception as e:
            logger.error("snow_update_error", error=str(e), incident_id=incident_id)

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process ServiceNow incident task"""
        task_id = task["task_id"]
        description = task["description"]
        service = task.get("service", "unknown")
        incident_id = task.get("incident_id")

        logger.info("processing_incident", task_id=task_id, service=service)

        # Step 1: Retrieve context from RAG
        context = self.rag.retrieve_context_for_incident(
            incident_description=description,
            service=service,
            limit=5
        )

        # Format context for DSPy
        historical_context = "\n".join([
            f"- {inc.get('title', '')}: {inc.get('resolution', '')}"
            for inc in context.get("similar_incidents", [])[:3]
        ])

        service_context = f"Service: {service}\n"
        if context.get("service_history"):
            service_context += "Recent incidents:\n" + "\n".join([
                f"- {inc.get('title', '')}"
                for inc in context["service_history"][:3]
            ])

        runbooks = "\n\n".join([
            f"Runbook: {rb.get('title', '')}\n{rb.get('content', '')}"
            for rb in context.get("runbooks", [])
        ])

        # Step 2: Run DSPy reasoning
        try:
            result = self.dspy_module(
                incident_description=description,
                historical_context=historical_context or "No historical context available",
                service_context=service_context,
                runbooks=runbooks or "No runbooks available"
            )

            # Step 3: Update ServiceNow if incident_id provided
            if incident_id:
                self.update_incident_in_snow(
                    incident_id=incident_id,
                    updates={
                        "work_notes": f"AI Analysis:\n"
                                     f"Severity: {result.severity}\n"
                                     f"Category: {result.category}\n"
                                     f"Root Cause: {result.root_cause}\n"
                                     f"Confidence: {result.confidence_score}%\n\n"
                                     f"Resolution Steps:\n{result.resolution_steps}",
                        "state": "2",  # In Progress
                        "priority": self._map_severity_to_priority(result.severity)
                    }
                )

            # Step 4: Store in knowledge graph for future retrieval
            if incident_id:
                self.rag.store_incident_with_graph(
                    incident_id=incident_id,
                    incident_data={
                        "incident_id": incident_id,
                        "title": description[:100],
                        "description": description,
                        "resolution": result.resolution_steps,
                        "severity": result.severity,
                        "service": service
                    },
                    service=service,
                    topic=result.category
                )

            return {
                "classification": {
                    "severity": result.severity,
                    "category": result.category,
                    "urgency": result.urgency,
                    "reasoning": result.classification_reasoning
                },
                "root_cause_analysis": {
                    "root_cause": result.root_cause,
                    "confidence": result.confidence_score,
                    "evidence": result.supporting_evidence,
                    "alternatives": result.alternative_causes
                },
                "resolution": {
                    "steps": result.resolution_steps,
                    "estimated_time": result.estimated_time,
                    "risk_level": result.risk_level,
                    "rollback_plan": result.rollback_plan
                },
                "context_used": {
                    "similar_incidents": len(context.get("similar_incidents", [])),
                    "runbooks": len(context.get("runbooks", [])),
                    "service_history": len(context.get("service_history", []))
                }
            }

        except Exception as e:
            logger.error("dspy_processing_error", error=str(e))
            raise

    def _map_severity_to_priority(self, severity: str) -> str:
        """Map severity to ServiceNow priority"""
        mapping = {
            "P1": "1",
            "P2": "2",
            "P3": "3",
            "P4": "4"
        }
        return mapping.get(severity, "3")


# Global agent instance
agent = ServiceNowAgent()


@app.post("/process")
async def process_incident(task: IncidentTask):
    """Process incident task"""
    try:
        result = agent.run(task.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "ServiceNowAgent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
