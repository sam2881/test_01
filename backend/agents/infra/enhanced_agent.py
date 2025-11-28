"""
Enhanced Infrastructure Agent with Autonomous VM Recovery
Integrates with ServiceNow incidents and uses LLM to decide remediation
"""
import os
import sys
from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import httpx
import structlog

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent
from agents.infra.autonomous_vm_recovery import AutonomousVMRecovery
from backend.rag.hybrid_search import hybrid_rag

logger = structlog.get_logger()

app = FastAPI(title="Enhanced Infrastructure Agent")


class VMRecoveryTask(BaseModel):
    """VM Recovery task schema"""
    task_id: str
    incident_id: Optional[str] = None
    vm_name: str
    zone: str = "us-central1-a"
    restart_services: bool = True
    description: Optional[str] = None


class IncidentAnalysis(BaseModel):
    """Incident analysis result"""
    incident_id: str
    description: str
    requires_vm_recovery: bool
    vm_name: Optional[str] = None
    zone: Optional[str] = None
    confidence: float


class EnhancedInfraAgent(BaseAgent):
    """Enhanced Infrastructure Agent with autonomous capabilities"""

    def __init__(self):
        super().__init__(agent_name="EnhancedInfraAgent", agent_type="infrastructure_autonomous")

        # Initialize autonomous recovery
        self.vm_recovery = AutonomousVMRecovery()

        # Initialize RAG for context
        self.rag = hybrid_rag

        # ServiceNow agent URL
        self.servicenow_agent_url = os.getenv(
            "SERVICENOW_AGENT_URL",
            "http://servicenow_agent:8010/process"
        )

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate task input"""
        return "vm_name" in task or "incident_id" in task

    def analyze_incident_with_llm(self, incident_description: str) -> Dict[str, Any]:
        """
        Use LLM to analyze incident and determine if VM recovery is needed
        """
        from langchain_openai import ChatOpenAI
        from langchain_core.prompts import ChatPromptTemplate

        logger.info("analyzing_incident_with_llm", description=incident_description[:100])

        # Get similar incidents from RAG
        context = self.rag.retrieve_context_for_incident(
            incident_description=incident_description,
            service="compute",
            limit=3
        )

        similar_incidents = "\n".join([
            f"- {inc.get('title', '')}: {inc.get('resolution', '')}"
            for inc in context.get("similar_incidents", [])[:3]
        ])

        # LLM Prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert DevOps engineer analyzing infrastructure incidents.
Analyze the incident description and determine if it requires VM recovery.

Your task:
1. Determine if this is a VM/compute instance down issue
2. Extract the VM name if mentioned (usually in format: vm-name, instance-name, or server-name)
3. Extract the GCP zone if mentioned (like us-central1-a)
4. Decide if services need to be restarted after VM starts
5. Provide confidence score (0.0 to 1.0)

Similar incidents from history:
{similar_incidents}

Respond in JSON format:
{{
    "requires_vm_recovery": true/false,
    "vm_name": "extracted-vm-name or null",
    "zone": "extracted-zone or us-central1-a",
    "restart_services": true/false,
    "reasoning": "brief explanation",
    "confidence": 0.0-1.0
}}"""),
            ("human", "Incident Description: {description}")
        ])

        llm = ChatOpenAI(model="gpt-4", temperature=0.3)
        chain = prompt | llm

        try:
            response = chain.invoke({
                "description": incident_description,
                "similar_incidents": similar_incidents or "No similar incidents found"
            })

            # Parse JSON response
            import json
            result = json.loads(response.content)

            logger.info("llm_analysis_complete",
                       requires_recovery=result.get("requires_vm_recovery"),
                       vm_name=result.get("vm_name"),
                       confidence=result.get("confidence"))

            return result

        except Exception as e:
            logger.error("llm_analysis_error", error=str(e))
            return {
                "requires_vm_recovery": False,
                "error": str(e),
                "confidence": 0.0
            }

    async def update_servicenow_incident(
        self,
        incident_id: str,
        work_notes: str,
        state: str = "2"  # In Progress
    ):
        """Update ServiceNow incident with progress"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.servicenow_agent_url,
                    json={
                        "task_id": f"infra-update-{incident_id}",
                        "task_type": "update",
                        "incident_id": incident_id,
                        "updates": {
                            "work_notes": work_notes,
                            "state": state
                        }
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info("servicenow_updated", incident_id=incident_id)
                else:
                    logger.error("servicenow_update_failed", status=response.status_code)

        except Exception as e:
            logger.error("update_incident_error", error=str(e))

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process infrastructure task with autonomous decision making"""
        task_id = task.get("task_id")
        incident_id = task.get("incident_id")
        description = task.get("description", "")

        logger.info("processing_infra_task", task_id=task_id, has_incident=bool(incident_id))

        # If incident_id is provided, analyze it with LLM
        if incident_id and description:
            analysis = self.analyze_incident_with_llm(description)

            if not analysis.get("requires_vm_recovery"):
                return {
                    "status": "no_action_required",
                    "message": "LLM determined VM recovery not needed",
                    "analysis": analysis
                }

            if analysis.get("confidence", 0) < 0.7:
                return {
                    "status": "low_confidence",
                    "message": "LLM confidence too low for autonomous action",
                    "analysis": analysis,
                    "recommendation": "Manual review recommended"
                }

            # Extract VM details from LLM analysis
            vm_name = analysis.get("vm_name") or task.get("vm_name")
            zone = analysis.get("zone", "us-central1-a")
            restart_services = analysis.get("restart_services", True)

        else:
            # Direct VM recovery request
            vm_name = task.get("vm_name")
            zone = task.get("zone", "us-central1-a")
            restart_services = task.get("restart_services", True)
            analysis = None

        if not vm_name:
            return {
                "status": "error",
                "message": "VM name not provided and could not be extracted from incident"
            }

        # Execute autonomous recovery
        logger.info("executing_autonomous_recovery", vm=vm_name, zone=zone)

        recovery_result = self.vm_recovery.run({
            "vm_name": vm_name,
            "zone": zone,
            "restart_services": restart_services
        })

        # Prepare detailed result
        result = {
            "status": "success" if recovery_result.get("success") else "failed",
            "vm_name": vm_name,
            "zone": zone,
            "llm_analysis": analysis,
            "recovery_result": recovery_result
        }

        return result


# Global agent instance
agent = EnhancedInfraAgent()


@app.post("/recover")
async def recover_vm(task: VMRecoveryTask, background_tasks: BackgroundTasks):
    """Recover a VM and restart services"""
    try:
        logger.info("vm_recovery_requested", vm=task.vm_name, incident=task.incident_id)

        # Run recovery
        result = agent.run({
            "task_id": task.task_id,
            "incident_id": task.incident_id,
            "vm_name": task.vm_name,
            "zone": task.zone,
            "restart_services": task.restart_services,
            "description": task.description
        })

        # Update ServiceNow in background if incident provided
        if task.incident_id and result.get("status") == "success":
            recovery_notes = f"""Autonomous VM Recovery Completed:
VM Name: {task.vm_name}
Zone: {task.zone}
Status: SUCCESS
External IP: {result.get('recovery_result', {}).get('vm_ip', 'N/A')}

Workflow Steps:
"""
            for step in result.get("recovery_result", {}).get("workflow_steps", []):
                recovery_notes += f"\n- {step['step']}: {step['status']}"

            background_tasks.add_task(
                agent.update_servicenow_incident,
                task.incident_id,
                recovery_notes,
                "6"  # Resolved
            )

        return result

    except Exception as e:
        logger.error("recovery_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_incident(analysis: IncidentAnalysis):
    """Analyze incident to determine if VM recovery is needed"""
    try:
        result = agent.analyze_incident_with_llm(analysis.description)

        return {
            "incident_id": analysis.incident_id,
            "analysis": result,
            "recommended_action": "vm_recovery" if result.get("requires_vm_recovery") else "manual_review"
        }

    except Exception as e:
        logger.error("analysis_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "EnhancedInfraAgent",
        "capabilities": [
            "autonomous_vm_recovery",
            "llm_incident_analysis",
            "terraform_execution",
            "ansible_execution",
            "servicenow_integration"
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8013)
