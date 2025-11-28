"""Infrastructure Agent for Terraform/Ansible automation"""
import os
import sys
from typing import Any, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from python_terraform import Terraform
import ansible_runner

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.base_agent import BaseAgent
import structlog

logger = structlog.get_logger()

app = FastAPI(title="Infrastructure Agent")


class InfraTask(BaseModel):
    """Infrastructure task schema"""
    task_id: str
    task_type: str  # "terraform" or "ansible"
    action: str  # "plan", "apply", "destroy" for terraform; "run" for ansible
    config_path: str
    variables: Dict[str, Any] = {}


class InfraAgent(BaseAgent):
    """Agent for infrastructure automation"""

    def __init__(self):
        super().__init__(agent_name="InfraAgent", agent_type="infrastructure")
        self.terraform = Terraform(working_dir="/tmp/terraform")

    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate task input"""
        return all(k in task for k in ["task_id", "task_type", "action"])

    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process infrastructure task"""
        task_type = task["task_type"]
        action = task["action"]

        logger.info("processing_infra_task", type=task_type, action=action)

        if task_type == "terraform":
            return self._handle_terraform(action, task)
        elif task_type == "ansible":
            return self._handle_ansible(action, task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    def _handle_terraform(self, action: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Terraform operations"""
        variables = task.get("variables", {})

        if action == "plan":
            return_code, stdout, stderr = self.terraform.plan(var=variables)
        elif action == "apply":
            # HITL approval required for apply
            logger.warning("terraform_apply_requires_approval", task_id=task["task_id"])
            return {
                "status": "pending_approval",
                "message": "Terraform apply requires human approval",
                "plan": "Terraform plan output here"
            }
        elif action == "destroy":
            logger.warning("terraform_destroy_blocked", task_id=task["task_id"])
            return {
                "status": "blocked",
                "message": "Terraform destroy requires explicit approval"
            }
        else:
            raise ValueError(f"Unknown action: {action}")

        return {
            "action": action,
            "return_code": return_code,
            "output": stdout,
            "errors": stderr
        }

    def _handle_ansible(self, action: str, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Ansible operations"""
        playbook_path = task.get("config_path", "")

        if action == "run":
            result = ansible_runner.run(
                private_data_dir="/tmp/ansible",
                playbook=playbook_path,
                extravars=task.get("variables", {})
            )

            return {
                "status": result.status,
                "rc": result.rc,
                "stats": result.stats
            }
        else:
            raise ValueError(f"Unknown action: {action}")


agent = InfraAgent()


@app.post("/process")
async def process_infra_task(task: InfraTask):
    """Process infrastructure task"""
    try:
        result = agent.run(task.dict())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agent": "InfraAgent"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8013)
