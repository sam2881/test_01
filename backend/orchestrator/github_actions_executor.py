"""
GitHub Actions Executor
Triggers GitHub Actions workflows for safe script execution
"""
import os
import sys
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import structlog
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

logger = structlog.get_logger()


class GitHubActionsExecutor:
    """
    Execute scripts via GitHub Actions for safety and auditability

    Instead of running scripts locally, this:
    1. Triggers GitHub Actions workflow
    2. Monitors execution status
    3. Retrieves results
    4. Updates incident with outcome
    """

    def __init__(self):
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_org = os.getenv("GITHUB_ORG", "sam2881")
        self.github_repo = os.getenv("GITHUB_REPO", "test_01")
        self.base_url = f"https://api.github.com/repos/{self.github_org}/{self.github_repo}"
        self.headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

    async def trigger_terraform_execution(
        self,
        incident_id: str,
        script_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger Terraform execution via GitHub Actions

        Args:
            incident_id: ServiceNow incident ID
            script_name: Terraform script to run (e.g., "gcp_vm_start.tf")
            parameters: Script parameters (e.g., {vm_name, zone, project_id})

        Returns:
            {
                "workflow_run_id": "...",
                "workflow_url": "https://github.com/.../actions/runs/...",
                "status": "triggered"
            }
        """
        logger.info("triggering_terraform_workflow",
                   incident=incident_id,
                   script=script_name)

        # Prepare payload
        payload = {
            "event_type": "terraform_execution",
            "client_payload": {
                "incident_id": incident_id,
                "script_name": script_name,
                "parameters_json": json.dumps(parameters)
            }
        }

        # Trigger via repository_dispatch
        response = requests.post(
            f"{self.base_url}/dispatches",
            headers=self.headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 204:
            logger.info("terraform_workflow_triggered",
                       incident=incident_id)

            # Wait a bit for workflow to start
            await asyncio.sleep(5)

            # Get the workflow run ID
            workflow_run = await self._get_latest_workflow_run(incident_id)

            if workflow_run:
                return {
                    "success": True,
                    "workflow_run_id": workflow_run["id"],
                    "workflow_url": workflow_run["html_url"],
                    "status": workflow_run["status"],
                    "created_at": workflow_run["created_at"]
                }
            else:
                return {
                    "success": True,
                    "workflow_triggered": True,
                    "message": "Workflow triggered but run not found yet"
                }
        else:
            logger.error("terraform_workflow_trigger_failed",
                        status=response.status_code,
                        error=response.text)
            return {
                "success": False,
                "error": f"Failed to trigger workflow: {response.status_code}",
                "details": response.text
            }

    async def trigger_ansible_execution(
        self,
        incident_id: str,
        playbook_name: str,
        inventory: Dict[str, Any],
        extra_vars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger Ansible execution via GitHub Actions

        Args:
            incident_id: ServiceNow incident ID
            playbook_name: Ansible playbook to run
            inventory: Inventory configuration
            extra_vars: Extra variables for playbook

        Returns:
            Workflow run details
        """
        logger.info("triggering_ansible_workflow",
                   incident=incident_id,
                   playbook=playbook_name)

        # Prepare payload
        payload = {
            "event_type": "ansible_execution",
            "client_payload": {
                "incident_id": incident_id,
                "playbook_name": playbook_name,
                "inventory_json": json.dumps(inventory),
                "extra_vars_json": json.dumps(extra_vars)
            }
        }

        # Trigger via repository_dispatch
        response = requests.post(
            f"{self.base_url}/dispatches",
            headers=self.headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 204:
            logger.info("ansible_workflow_triggered",
                       incident=incident_id)

            # Wait for workflow to start
            await asyncio.sleep(5)

            workflow_run = await self._get_latest_workflow_run(incident_id)

            if workflow_run:
                return {
                    "success": True,
                    "workflow_run_id": workflow_run["id"],
                    "workflow_url": workflow_run["html_url"],
                    "status": workflow_run["status"]
                }
            else:
                return {
                    "success": True,
                    "workflow_triggered": True
                }
        else:
            logger.error("ansible_workflow_trigger_failed",
                        status=response.status_code)
            return {
                "success": False,
                "error": f"Failed to trigger workflow: {response.status_code}"
            }

    async def _get_latest_workflow_run(
        self,
        incident_id: str
    ) -> Optional[Dict]:
        """Get the latest workflow run for an incident"""

        try:
            response = requests.get(
                f"{self.base_url}/actions/runs",
                headers=self.headers,
                params={"per_page": 10},
                timeout=30
            )

            if response.status_code == 200:
                runs = response.json().get("workflow_runs", [])

                # Find run matching incident (by checking name or created time)
                for run in runs:
                    # Check if run was created recently (last 2 minutes)
                    created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                    age = (datetime.now(created.tzinfo) - created).total_seconds()

                    if age < 120:  # Last 2 minutes
                        return run

        except Exception as e:
            logger.error("get_workflow_run_failed", error=str(e))

        return None

    async def get_workflow_status(
        self,
        workflow_run_id: str
    ) -> Dict[str, Any]:
        """
        Get status of a workflow run

        Returns:
            {
                "id": "...",
                "status": "queued|in_progress|completed",
                "conclusion": "success|failure|cancelled|null",
                "html_url": "...",
                "logs_url": "..."
            }
        """
        try:
            response = requests.get(
                f"{self.base_url}/actions/runs/{workflow_run_id}",
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                run = response.json()
                return {
                    "id": run["id"],
                    "status": run["status"],
                    "conclusion": run.get("conclusion"),
                    "html_url": run["html_url"],
                    "logs_url": run.get("logs_url"),
                    "created_at": run["created_at"],
                    "updated_at": run["updated_at"]
                }
            else:
                logger.error("get_workflow_status_failed",
                            run_id=workflow_run_id,
                            status=response.status_code)
                return {
                    "error": f"Failed to get status: {response.status_code}"
                }

        except Exception as e:
            logger.error("get_workflow_status_exception", error=str(e))
            return {"error": str(e)}

    async def wait_for_completion(
        self,
        workflow_run_id: str,
        timeout_seconds: int = 1800  # 30 minutes
    ) -> Dict[str, Any]:
        """
        Wait for workflow to complete

        Args:
            workflow_run_id: GitHub Actions run ID
            timeout_seconds: Max time to wait

        Returns:
            Final workflow status
        """
        logger.info("waiting_for_workflow",
                   run_id=workflow_run_id,
                   timeout=timeout_seconds)

        start_time = datetime.now()
        poll_interval = 10  # seconds

        while True:
            # Check timeout
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                logger.warning("workflow_wait_timeout",
                             run_id=workflow_run_id,
                             elapsed=elapsed)
                return {
                    "status": "timeout",
                    "elapsed_seconds": elapsed
                }

            # Get status
            status = await self.get_workflow_status(workflow_run_id)

            if "error" in status:
                return status

            # Check if completed
            if status["status"] == "completed":
                logger.info("workflow_completed",
                           run_id=workflow_run_id,
                           conclusion=status["conclusion"],
                           elapsed=elapsed)
                return status

            # Still running, wait
            logger.debug("workflow_in_progress",
                        run_id=workflow_run_id,
                        status=status["status"])

            await asyncio.sleep(poll_interval)

    async def get_workflow_logs(
        self,
        workflow_run_id: str
    ) -> Optional[str]:
        """
        Download workflow logs

        Returns log content or None if failed
        """
        try:
            # Get logs URL
            response = requests.get(
                f"{self.base_url}/actions/runs/{workflow_run_id}/logs",
                headers=self.headers,
                timeout=60,
                allow_redirects=True
            )

            if response.status_code == 200:
                return response.text
            else:
                logger.error("get_workflow_logs_failed",
                            run_id=workflow_run_id,
                            status=response.status_code)
                return None

        except Exception as e:
            logger.error("get_workflow_logs_exception", error=str(e))
            return None


# Global instance
github_actions = GitHubActionsExecutor()
