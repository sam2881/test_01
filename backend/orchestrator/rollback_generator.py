"""
Automatic Rollback Plan Generator

Generates rollback plans for remediation actions:
- Analyzes action type and generates reverse action
- Creates checkpoint before execution
- Provides automatic rollback on failure

Supported Actions:
- VM operations (start/stop/restart)
- Service operations (start/stop/restart)
- File operations (create/delete/modify)
- Configuration changes
- Kubernetes operations
"""

import os
import json
import re
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import structlog

logger = structlog.get_logger()


class ActionType(Enum):
    """Types of actions that can have rollback"""
    VM_START = "vm_start"
    VM_STOP = "vm_stop"
    VM_RESTART = "vm_restart"
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    SERVICE_RESTART = "service_restart"
    FILE_CREATE = "file_create"
    FILE_DELETE = "file_delete"
    FILE_MODIFY = "file_modify"
    CONFIG_CHANGE = "config_change"
    K8S_SCALE_UP = "k8s_scale_up"
    K8S_SCALE_DOWN = "k8s_scale_down"
    K8S_RESTART = "k8s_restart"
    DISK_CLEANUP = "disk_cleanup"
    CACHE_CLEAR = "cache_clear"
    DB_QUERY = "db_query"
    CUSTOM = "custom"


@dataclass
class RollbackStep:
    """A single step in a rollback plan"""
    step_number: int
    description: str
    action_type: str
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    estimated_time_seconds: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RollbackPlan:
    """Complete rollback plan for an action"""
    plan_id: str
    original_action: str
    original_script_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Checkpoint info
    checkpoint_created: bool = False
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)

    # Rollback steps
    steps: List[RollbackStep] = field(default_factory=list)

    # Metadata
    risk_level: str = "medium"  # low, medium, high
    requires_approval: bool = False
    estimated_total_time_seconds: int = 60
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result["steps"] = [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.steps]
        return result


class RollbackGenerator:
    """
    Generates automatic rollback plans for remediation actions.

    Features:
    - Detects action type from script/command
    - Generates appropriate reverse actions
    - Creates checkpoints for stateful operations
    - Estimates rollback time and risk
    """

    def __init__(self):
        # Action patterns for detection
        self._action_patterns = {
            ActionType.VM_START: [
                r'start.*instance', r'gcloud.*start', r'aws.*start-instances',
                r'start_gcp_instance', r'vm.*start'
            ],
            ActionType.VM_STOP: [
                r'stop.*instance', r'gcloud.*stop', r'aws.*stop-instances',
                r'stop_gcp_instance', r'vm.*stop'
            ],
            ActionType.VM_RESTART: [
                r'restart.*instance', r'reboot', r'gcloud.*reset',
                r'restart_gcp_instance'
            ],
            ActionType.SERVICE_START: [
                r'systemctl\s+start', r'service\s+\w+\s+start',
                r'start.*service'
            ],
            ActionType.SERVICE_STOP: [
                r'systemctl\s+stop', r'service\s+\w+\s+stop',
                r'stop.*service'
            ],
            ActionType.SERVICE_RESTART: [
                r'systemctl\s+restart', r'service\s+\w+\s+restart',
                r'restart.*service'
            ],
            ActionType.DISK_CLEANUP: [
                r'clean.*disk', r'clear.*log', r'rm\s+-rf', r'delete.*old',
                r'disk.*cleanup', r'clear.*cache'
            ],
            ActionType.K8S_SCALE_UP: [
                r'kubectl.*scale.*replicas=\d+', r'scale.*up',
                r'increase.*replicas'
            ],
            ActionType.K8S_SCALE_DOWN: [
                r'kubectl.*scale.*replicas=0', r'scale.*down',
                r'decrease.*replicas'
            ],
            ActionType.K8S_RESTART: [
                r'kubectl.*rollout\s+restart', r'kubectl.*delete\s+pod'
            ],
            ActionType.CONFIG_CHANGE: [
                r'sed\s+-i', r'echo.*>>', r'modify.*config',
                r'update.*setting'
            ],
            ActionType.FILE_CREATE: [
                r'touch\s+', r'mkdir\s+', r'create.*file'
            ],
            ActionType.FILE_DELETE: [
                r'rm\s+', r'rmdir\s+', r'delete.*file'
            ],
        }

        # Reverse action mappings
        self._reverse_actions = {
            ActionType.VM_START: ActionType.VM_STOP,
            ActionType.VM_STOP: ActionType.VM_START,
            ActionType.VM_RESTART: None,  # No reverse needed
            ActionType.SERVICE_START: ActionType.SERVICE_STOP,
            ActionType.SERVICE_STOP: ActionType.SERVICE_START,
            ActionType.SERVICE_RESTART: None,
            ActionType.K8S_SCALE_UP: ActionType.K8S_SCALE_DOWN,
            ActionType.K8S_SCALE_DOWN: ActionType.K8S_SCALE_UP,
            ActionType.K8S_RESTART: None,
            ActionType.DISK_CLEANUP: None,  # Can't restore deleted files
            ActionType.CACHE_CLEAR: None,  # Can't restore cleared cache
            ActionType.CONFIG_CHANGE: ActionType.CONFIG_CHANGE,  # Restore backup
            ActionType.FILE_CREATE: ActionType.FILE_DELETE,
            ActionType.FILE_DELETE: ActionType.FILE_CREATE,  # Restore from backup
        }

        logger.info("rollback_generator_initialized")

    def generate_rollback_plan(
        self,
        script_id: str,
        script_content: str,
        script_metadata: Dict[str, Any],
        execution_parameters: Dict[str, Any]
    ) -> RollbackPlan:
        """
        Generate a rollback plan for a script execution.

        Args:
            script_id: ID of the script being executed
            script_content: Content/command of the script
            script_metadata: Metadata about the script
            execution_parameters: Parameters for the execution

        Returns:
            RollbackPlan with steps to reverse the action
        """
        plan_id = f"rollback_{script_id}_{int(datetime.now().timestamp())}"

        # Detect action type
        action_type = self._detect_action_type(script_content, script_metadata)

        # Generate rollback steps based on action type
        steps, checkpoint_data = self._generate_rollback_steps(
            action_type,
            script_content,
            script_metadata,
            execution_parameters
        )

        # Calculate risk level
        risk_level = self._assess_risk_level(action_type, script_metadata)

        # Determine if approval needed
        requires_approval = risk_level in ["high", "critical"] or action_type in [
            ActionType.FILE_DELETE,
            ActionType.CONFIG_CHANGE,
            ActionType.DB_QUERY
        ]

        # Calculate total time
        total_time = sum(s.estimated_time_seconds for s in steps)

        plan = RollbackPlan(
            plan_id=plan_id,
            original_action=str(action_type.value if action_type else "unknown"),
            original_script_id=script_id,
            checkpoint_created=bool(checkpoint_data),
            checkpoint_data=checkpoint_data,
            steps=steps,
            risk_level=risk_level,
            requires_approval=requires_approval,
            estimated_total_time_seconds=total_time,
            notes=self._generate_notes(action_type, script_metadata)
        )

        logger.info(
            "rollback_plan_generated",
            plan_id=plan_id,
            action_type=action_type.value if action_type else "unknown",
            steps=len(steps),
            risk_level=risk_level
        )

        return plan

    def _detect_action_type(
        self,
        script_content: str,
        script_metadata: Dict[str, Any]
    ) -> Optional[ActionType]:
        """Detect the type of action from script content"""
        content_lower = script_content.lower()

        for action_type, patterns in self._action_patterns.items():
            for pattern in patterns:
                if re.search(pattern, content_lower):
                    return action_type

        # Check metadata
        action = script_metadata.get("action", "").lower()
        if "start" in action:
            if "vm" in action or "instance" in action:
                return ActionType.VM_START
            return ActionType.SERVICE_START
        elif "stop" in action:
            if "vm" in action or "instance" in action:
                return ActionType.VM_STOP
            return ActionType.SERVICE_STOP
        elif "restart" in action:
            return ActionType.SERVICE_RESTART

        return ActionType.CUSTOM

    def _generate_rollback_steps(
        self,
        action_type: Optional[ActionType],
        script_content: str,
        script_metadata: Dict[str, Any],
        execution_parameters: Dict[str, Any]
    ) -> Tuple[List[RollbackStep], Dict[str, Any]]:
        """Generate rollback steps for the action type"""
        steps = []
        checkpoint_data = {}

        if action_type == ActionType.VM_START:
            steps = self._generate_vm_stop_rollback(execution_parameters)

        elif action_type == ActionType.VM_STOP:
            steps = self._generate_vm_start_rollback(execution_parameters)

        elif action_type == ActionType.SERVICE_START:
            steps = self._generate_service_stop_rollback(script_content, execution_parameters)

        elif action_type == ActionType.SERVICE_STOP:
            steps = self._generate_service_start_rollback(script_content, execution_parameters)

        elif action_type == ActionType.SERVICE_RESTART:
            # For restart, rollback is just noting the service was restarted
            steps.append(RollbackStep(
                step_number=1,
                description="Service was restarted - no rollback needed unless issues persist",
                action_type="note",
                command="# Monitor service status",
                parameters={}
            ))

        elif action_type == ActionType.DISK_CLEANUP:
            steps, checkpoint_data = self._generate_disk_cleanup_rollback(execution_parameters)

        elif action_type == ActionType.K8S_SCALE_UP:
            steps = self._generate_k8s_scale_rollback(execution_parameters, "down")

        elif action_type == ActionType.K8S_SCALE_DOWN:
            steps = self._generate_k8s_scale_rollback(execution_parameters, "up")

        elif action_type == ActionType.CONFIG_CHANGE:
            steps, checkpoint_data = self._generate_config_rollback(execution_parameters)

        else:
            # Generic rollback
            steps.append(RollbackStep(
                step_number=1,
                description="Manual rollback may be required - review execution logs",
                action_type="manual",
                command="# Review and manually reverse if needed",
                parameters={"original_script": script_metadata.get("name", "unknown")}
            ))

        return steps, checkpoint_data

    def _generate_vm_stop_rollback(self, params: Dict[str, Any]) -> List[RollbackStep]:
        """Generate rollback to stop a VM that was started"""
        instance = params.get("instance_name", params.get("instance", "unknown"))
        zone = params.get("zone", "us-central1-a")
        project = params.get("project", os.getenv("GCP_PROJECT", ""))

        return [
            RollbackStep(
                step_number=1,
                description=f"Stop the VM instance {instance}",
                action_type="vm_stop",
                command=f"gcloud compute instances stop {instance} --zone={zone} --project={project}",
                parameters={"instance": instance, "zone": zone, "project": project},
                requires_approval=True,
                estimated_time_seconds=60
            )
        ]

    def _generate_vm_start_rollback(self, params: Dict[str, Any]) -> List[RollbackStep]:
        """Generate rollback to start a VM that was stopped"""
        instance = params.get("instance_name", params.get("instance", "unknown"))
        zone = params.get("zone", "us-central1-a")
        project = params.get("project", os.getenv("GCP_PROJECT", ""))

        return [
            RollbackStep(
                step_number=1,
                description=f"Start the VM instance {instance}",
                action_type="vm_start",
                command=f"gcloud compute instances start {instance} --zone={zone} --project={project}",
                parameters={"instance": instance, "zone": zone, "project": project},
                requires_approval=True,
                estimated_time_seconds=90
            )
        ]

    def _generate_service_stop_rollback(
        self,
        script_content: str,
        params: Dict[str, Any]
    ) -> List[RollbackStep]:
        """Generate rollback to stop a service that was started"""
        # Try to extract service name
        service_match = re.search(r'(?:systemctl|service)\s+(?:start|restart)\s+(\S+)', script_content)
        service_name = service_match.group(1) if service_match else params.get("service", "unknown")

        return [
            RollbackStep(
                step_number=1,
                description=f"Stop service {service_name}",
                action_type="service_stop",
                command=f"sudo systemctl stop {service_name}",
                parameters={"service": service_name},
                requires_approval=False,
                estimated_time_seconds=30
            )
        ]

    def _generate_service_start_rollback(
        self,
        script_content: str,
        params: Dict[str, Any]
    ) -> List[RollbackStep]:
        """Generate rollback to start a service that was stopped"""
        service_match = re.search(r'(?:systemctl|service)\s+stop\s+(\S+)', script_content)
        service_name = service_match.group(1) if service_match else params.get("service", "unknown")

        return [
            RollbackStep(
                step_number=1,
                description=f"Start service {service_name}",
                action_type="service_start",
                command=f"sudo systemctl start {service_name}",
                parameters={"service": service_name},
                requires_approval=False,
                estimated_time_seconds=30
            )
        ]

    def _generate_disk_cleanup_rollback(
        self,
        params: Dict[str, Any]
    ) -> Tuple[List[RollbackStep], Dict[str, Any]]:
        """Generate rollback for disk cleanup (restore from backup if available)"""
        steps = [
            RollbackStep(
                step_number=1,
                description="Check if backup was created before cleanup",
                action_type="check",
                command="ls -la /var/backup/cleanup_*",
                parameters={},
                estimated_time_seconds=10
            ),
            RollbackStep(
                step_number=2,
                description="Restore files from backup if available",
                action_type="restore",
                command="# Manual restore: cp -r /var/backup/cleanup_TIMESTAMP/* /original/path/",
                parameters={},
                requires_approval=True,
                estimated_time_seconds=120
            )
        ]

        checkpoint_data = {
            "backup_recommended": True,
            "backup_command": "tar -czf /var/backup/cleanup_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/cleanup"
        }

        return steps, checkpoint_data

    def _generate_k8s_scale_rollback(
        self,
        params: Dict[str, Any],
        direction: str
    ) -> List[RollbackStep]:
        """Generate rollback for Kubernetes scaling"""
        deployment = params.get("deployment", "unknown")
        namespace = params.get("namespace", "default")
        original_replicas = params.get("original_replicas", 1)

        return [
            RollbackStep(
                step_number=1,
                description=f"Scale {direction} deployment {deployment}",
                action_type=f"k8s_scale_{direction}",
                command=f"kubectl scale deployment {deployment} --replicas={original_replicas} -n {namespace}",
                parameters={
                    "deployment": deployment,
                    "namespace": namespace,
                    "replicas": original_replicas
                },
                requires_approval=True,
                estimated_time_seconds=60
            )
        ]

    def _generate_config_rollback(
        self,
        params: Dict[str, Any]
    ) -> Tuple[List[RollbackStep], Dict[str, Any]]:
        """Generate rollback for config changes"""
        config_file = params.get("config_file", "/etc/app/config")

        steps = [
            RollbackStep(
                step_number=1,
                description="Restore config from backup",
                action_type="config_restore",
                command=f"cp {config_file}.bak {config_file}",
                parameters={"config_file": config_file},
                requires_approval=True,
                estimated_time_seconds=10
            ),
            RollbackStep(
                step_number=2,
                description="Restart service to apply restored config",
                action_type="service_restart",
                command="sudo systemctl restart app-service",
                parameters={},
                estimated_time_seconds=30
            )
        ]

        checkpoint_data = {
            "backup_command": f"cp {config_file} {config_file}.bak",
            "backup_file": f"{config_file}.bak"
        }

        return steps, checkpoint_data

    def _assess_risk_level(
        self,
        action_type: Optional[ActionType],
        script_metadata: Dict[str, Any]
    ) -> str:
        """Assess the risk level of the rollback"""
        high_risk_actions = [
            ActionType.FILE_DELETE,
            ActionType.CONFIG_CHANGE,
            ActionType.DB_QUERY,
            ActionType.DISK_CLEANUP
        ]

        medium_risk_actions = [
            ActionType.VM_STOP,
            ActionType.SERVICE_STOP,
            ActionType.K8S_SCALE_DOWN
        ]

        if action_type in high_risk_actions:
            return "high"
        elif action_type in medium_risk_actions:
            return "medium"

        # Check metadata
        if script_metadata.get("risk_level", "").lower() in ["high", "critical"]:
            return "high"
        if script_metadata.get("environment", "").lower() == "production":
            return "high"

        return "low"

    def _generate_notes(
        self,
        action_type: Optional[ActionType],
        script_metadata: Dict[str, Any]
    ) -> List[str]:
        """Generate helpful notes for the rollback"""
        notes = []

        if action_type == ActionType.DISK_CLEANUP:
            notes.append("WARNING: Deleted files cannot be automatically restored")
            notes.append("Ensure backups exist before cleanup operations")

        if action_type in [ActionType.VM_STOP, ActionType.SERVICE_STOP]:
            notes.append("Stopping may cause service disruption")
            notes.append("Verify dependent services before proceeding")

        if script_metadata.get("environment", "").lower() == "production":
            notes.append("PRODUCTION environment - extra caution required")

        return notes


# Global instance
rollback_generator = RollbackGenerator()
