"""
Enterprise Script Executor - Safe Automation via GitHub Actions

This module provides enterprise-grade script execution that:
1. NEVER executes scripts directly on the system
2. Always triggers GitHub Actions workflows for safe, audited execution
3. Validates inputs against the script registry
4. Enforces approval workflows based on risk levels
5. Tracks execution status and results
"""

import os
import json
import logging
import httpx
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "sam2881")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "test_01")
REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "../../registry.json")


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    VALIDATION_FAILED = "validation_failed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    TRIGGERED = "triggered"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EnterpriseExecutor:
    """
    Enterprise Script Executor that uses GitHub Actions for safe execution.

    Key Principles:
    - Scripts are NEVER executed directly
    - All execution goes through GitHub Actions workflows
    - Full audit trail and approval workflows
    - Risk-based execution controls
    """

    def __init__(self):
        self.registry = self._load_registry()
        self.execution_history: List[Dict] = []
        self.github_api_base = "https://api.github.com"

    def _load_registry(self) -> Dict:
        """Load the script registry from disk."""
        try:
            # Try multiple paths
            paths_to_try = [
                REGISTRY_PATH,
                "/home/samrattidke600/ai_agent_app/registry.json",
                os.path.join(os.path.dirname(__file__), "../../../registry.json"),
            ]

            for path in paths_to_try:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        registry = json.load(f)
                        logger.info(f"Loaded registry v{registry.get('version', 'unknown')} from {path}")
                        return registry

            logger.warning("Registry not found, using empty registry")
            return {"scripts": [], "safety_rules": {}, "risk_levels": {}}

        except Exception as e:
            logger.error(f"Failed to load registry: {e}")
            return {"scripts": [], "safety_rules": {}, "risk_levels": {}}

    def reload_registry(self) -> Dict:
        """Reload the registry from disk."""
        self.registry = self._load_registry()
        return self.registry

    def get_script_by_id(self, script_id: str) -> Optional[Dict]:
        """Get a script configuration by its ID."""
        for script in self.registry.get("scripts", []):
            if script.get("id") == script_id:
                return script
        return None

    def search_scripts(self, query: str) -> List[Dict]:
        """Search scripts by keyword, name, or error pattern."""
        query_lower = query.lower()
        results = []

        for script in self.registry.get("scripts", []):
            score = 0

            # Check keywords
            keywords = script.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in query_lower or query_lower in keyword.lower():
                    score += 10

            # Check error patterns
            error_patterns = script.get("error_patterns", [])
            for pattern in error_patterns:
                if pattern.lower() in query_lower:
                    score += 15

            # Check name and description
            if query_lower in script.get("name", "").lower():
                score += 20
            if query_lower in script.get("description", "").lower():
                score += 5

            # Check service, component, action
            if query_lower in script.get("service", "").lower():
                score += 8
            if query_lower in script.get("component", "").lower():
                score += 8
            if query_lower in script.get("action", "").lower():
                score += 8

            if score > 0:
                results.append({**script, "_match_score": score})

        # Sort by score
        results.sort(key=lambda x: x.get("_match_score", 0), reverse=True)
        return results

    def validate_inputs(self, script: Dict, inputs: Dict) -> Dict:
        """
        Validate that all required inputs are provided and valid.

        Returns:
            Dict with 'valid' boolean and 'errors' list
        """
        errors = []
        warnings = []

        required_inputs = script.get("required_inputs", [])
        optional_inputs = script.get("optional_inputs", [])

        # Check required inputs
        for required in required_inputs:
            if required not in inputs or not inputs[required]:
                errors.append(f"Missing required input: {required}")

        # Check for unknown inputs
        all_known = set(required_inputs + optional_inputs)
        for key in inputs.keys():
            if key not in all_known:
                warnings.append(f"Unknown input provided: {key}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def validate_environment(self, script: Dict, environment: str) -> Dict:
        """
        Validate that the script is allowed in the specified environment.

        Returns:
            Dict with 'valid' boolean and 'error' message
        """
        allowed_envs = script.get("environment_allowed", [])

        if environment not in allowed_envs:
            return {
                "valid": False,
                "error": f"Script '{script.get('id')}' is not allowed in '{environment}' environment. Allowed: {allowed_envs}"
            }

        return {"valid": True, "error": None}

    def check_auto_approve(self, script: Dict, environment: str) -> Dict:
        """
        Check if the script can be auto-approved based on risk level and environment.

        Returns:
            Dict with 'auto_approve' boolean and 'reason'
        """
        risk_level = script.get("risk_level", "medium")
        auto_approve = script.get("auto_approve", False)

        risk_config = self.registry.get("risk_levels", {}).get(risk_level, {})

        # Critical and high-risk scripts never auto-approve in production
        if environment == "production" and risk_level in ["high", "critical"]:
            return {
                "auto_approve": False,
                "reason": f"High/critical risk scripts require manual approval in production"
            }

        # Check if auto-approve is allowed for this risk level
        if not risk_config.get("auto_approve_allowed", False):
            return {
                "auto_approve": False,
                "reason": f"Risk level '{risk_level}' does not allow auto-approval"
            }

        # Check script-level auto_approve flag
        if not auto_approve:
            return {
                "auto_approve": False,
                "reason": "Script is configured to require manual approval"
            }

        return {
            "auto_approve": True,
            "reason": "Script meets auto-approval criteria"
        }

    def get_required_approvals(self, script: Dict, environment: str) -> Dict:
        """
        Determine the number and type of approvals required.

        Returns:
            Dict with approval requirements
        """
        risk_level = script.get("risk_level", "medium")
        risk_config = self.registry.get("risk_levels", {}).get(risk_level, {})

        approval_count = risk_config.get("approval_count", 1)
        requires_manager = risk_config.get("requires_manager_approval", False)

        # Production may require additional approvals
        if environment == "production" and risk_level in ["medium", "high", "critical"]:
            approval_count = max(approval_count, 1)

        return {
            "approval_count": approval_count,
            "requires_manager_approval": requires_manager,
            "risk_level": risk_level
        }

    async def trigger_github_workflow(
        self,
        script: Dict,
        inputs: Dict,
        incident_id: str,
        environment: str = "development",
        dry_run: bool = False
    ) -> Dict:
        """
        Trigger a GitHub Actions workflow for the specified script.

        This is the ONLY way scripts are executed - through GitHub Actions.
        Direct execution is NEVER performed.

        Args:
            script: The script configuration from registry
            inputs: The input parameters for the script
            incident_id: The ServiceNow incident ID
            environment: Target environment (development, staging, production)
            dry_run: If True, validates without actually triggering

        Returns:
            Dict with execution status and details
        """
        script_id = script.get("id")
        workflow_file = script.get("workflow")
        script_type = script.get("type", "shell")

        logger.info(f"Preparing to trigger workflow for script: {script_id}")

        # Step 1: Validate inputs
        input_validation = self.validate_inputs(script, inputs)
        if not input_validation["valid"]:
            return {
                "status": ExecutionStatus.VALIDATION_FAILED,
                "script_id": script_id,
                "errors": input_validation["errors"],
                "message": "Input validation failed"
            }

        # Step 2: Validate environment
        env_validation = self.validate_environment(script, environment)
        if not env_validation["valid"]:
            return {
                "status": ExecutionStatus.VALIDATION_FAILED,
                "script_id": script_id,
                "errors": [env_validation["error"]],
                "message": "Environment validation failed"
            }

        # Step 3: Check auto-approval
        approval_check = self.check_auto_approve(script, environment)
        if not approval_check["auto_approve"]:
            approval_reqs = self.get_required_approvals(script, environment)
            return {
                "status": ExecutionStatus.AWAITING_APPROVAL,
                "script_id": script_id,
                "reason": approval_check["reason"],
                "approval_requirements": approval_reqs,
                "message": f"Script requires {approval_reqs['approval_count']} approval(s)"
            }

        # Step 4: Prepare workflow inputs based on script type
        workflow_inputs = self._prepare_workflow_inputs(script, inputs, incident_id, environment, dry_run)

        # Step 5: If dry run, return validation success without triggering
        if dry_run:
            return {
                "status": "dry_run_validated",
                "script_id": script_id,
                "workflow": workflow_file,
                "inputs": workflow_inputs,
                "message": "Dry run validation successful - workflow not triggered"
            }

        # Step 6: Trigger the GitHub Actions workflow
        try:
            result = await self._dispatch_workflow(workflow_file, workflow_inputs)

            # Record execution in history
            execution_record = {
                "execution_id": result.get("run_id", f"exec_{datetime.utcnow().timestamp()}"),
                "script_id": script_id,
                "incident_id": incident_id,
                "environment": environment,
                "inputs": inputs,
                "triggered_at": datetime.utcnow().isoformat(),
                "status": ExecutionStatus.TRIGGERED,
                "workflow_file": workflow_file
            }
            self.execution_history.append(execution_record)

            return {
                "status": ExecutionStatus.TRIGGERED,
                "script_id": script_id,
                "workflow": workflow_file,
                "run_id": result.get("run_id"),
                "run_url": result.get("run_url"),
                "message": f"Workflow triggered successfully",
                "execution_record": execution_record
            }

        except Exception as e:
            logger.error(f"Failed to trigger workflow: {e}")
            return {
                "status": ExecutionStatus.FAILED,
                "script_id": script_id,
                "error": str(e),
                "message": "Failed to trigger GitHub Actions workflow"
            }

    def _prepare_workflow_inputs(
        self,
        script: Dict,
        inputs: Dict,
        incident_id: str,
        environment: str,
        dry_run: bool
    ) -> Dict:
        """Prepare inputs for the specific workflow type."""
        script_type = script.get("type", "shell")

        base_inputs = {
            "incident_id": incident_id,
            "environment": environment,
            "dry_run": str(dry_run).lower()
        }

        if script_type == "ansible":
            return {
                **base_inputs,
                "playbook_name": script.get("path", "").replace("ansible/", ""),
                "inventory": inputs.get("inventory", environment),
                "extra_vars": json.dumps({k: v for k, v in inputs.items() if k != "inventory"})
            }

        elif script_type == "terraform":
            return {
                **base_inputs,
                "terraform_dir": script.get("path", "").rsplit("/", 1)[0] if "/" in script.get("path", "") else "terraform",
                "action": inputs.get("action", "plan"),
                "tf_vars": json.dumps(inputs)
            }

        elif script_type == "kubernetes":
            return {
                **base_inputs,
                "manifest": script.get("path", ""),
                "namespace": inputs.get("namespace", "default"),
                "action": script.get("action", "apply"),
                **inputs
            }

        elif script_type == "shell":
            return {
                **base_inputs,
                "script_path": script.get("path", ""),
                "script_args": json.dumps(inputs)
            }

        return {**base_inputs, **inputs}

    async def _dispatch_workflow(self, workflow_file: str, inputs: Dict) -> Dict:
        """
        Dispatch a GitHub Actions workflow via the GitHub API.

        Uses the workflow_dispatch event to trigger the workflow.
        """
        if not GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN environment variable is not set")

        url = f"{self.github_api_base}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/workflows/{workflow_file}/dispatches"

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

        payload = {
            "ref": "master",  # or main, depending on your default branch
            "inputs": {k: str(v) for k, v in inputs.items()}  # GitHub requires string inputs
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 204:
                # Workflow dispatch successful - get the run ID
                # Need to wait briefly and fetch the latest run
                await asyncio.sleep(2)

                runs_url = f"{self.github_api_base}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/runs?per_page=1"
                runs_response = await client.get(runs_url, headers=headers)

                if runs_response.status_code == 200:
                    runs_data = runs_response.json()
                    if runs_data.get("workflow_runs"):
                        latest_run = runs_data["workflow_runs"][0]
                        return {
                            "run_id": latest_run.get("id"),
                            "run_url": latest_run.get("html_url"),
                            "status": latest_run.get("status")
                        }

                return {"run_id": None, "run_url": None, "status": "triggered"}

            elif response.status_code == 401:
                raise ValueError("GitHub authentication failed - check GITHUB_TOKEN")

            elif response.status_code == 404:
                raise ValueError(f"Workflow '{workflow_file}' not found in repository")

            else:
                raise ValueError(f"GitHub API error: {response.status_code} - {response.text}")

    async def get_workflow_status(self, run_id: int) -> Dict:
        """Get the status of a workflow run."""
        if not GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN environment variable is not set")

        url = f"{self.github_api_base}/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/actions/runs/{run_id}"

        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                return {
                    "run_id": data.get("id"),
                    "status": data.get("status"),
                    "conclusion": data.get("conclusion"),
                    "html_url": data.get("html_url"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at")
                }
            else:
                raise ValueError(f"Failed to get workflow status: {response.status_code}")

    async def wait_for_workflow_completion(
        self,
        run_id: int,
        timeout_seconds: int = 600,
        poll_interval: int = 10
    ) -> Dict:
        """Wait for a workflow run to complete."""
        start_time = datetime.utcnow()

        while True:
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            if elapsed > timeout_seconds:
                return {
                    "status": "timeout",
                    "message": f"Workflow did not complete within {timeout_seconds} seconds"
                }

            status = await self.get_workflow_status(run_id)

            if status.get("status") == "completed":
                conclusion = status.get("conclusion")
                return {
                    "status": "completed",
                    "conclusion": conclusion,
                    "success": conclusion == "success",
                    "run_url": status.get("html_url")
                }

            await asyncio.sleep(poll_interval)

    def get_execution_history(
        self,
        incident_id: Optional[str] = None,
        script_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Get execution history, optionally filtered."""
        history = self.execution_history

        if incident_id:
            history = [h for h in history if h.get("incident_id") == incident_id]

        if script_id:
            history = [h for h in history if h.get("script_id") == script_id]

        return history[-limit:]


# Singleton instance
_executor_instance: Optional[EnterpriseExecutor] = None


def get_executor() -> EnterpriseExecutor:
    """Get the singleton executor instance."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = EnterpriseExecutor()
    return _executor_instance
