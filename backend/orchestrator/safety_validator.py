"""
Safety Validation Layer for Enterprise Script Execution

This module enforces all safety rules before script execution:
1. Environment restrictions
2. Risk level validations
3. Approval workflow enforcement
4. Forbidden action detection
5. Input sanitization
6. Rollback requirements
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class SafetyCheck:
    """Result of a single safety check."""
    name: str
    result: ValidationResult
    message: str
    severity: str  # info, warning, error, critical
    recommendation: Optional[str] = None


@dataclass
class SafetyReport:
    """Complete safety validation report."""
    overall_result: ValidationResult
    checks: List[SafetyCheck]
    can_execute: bool
    requires_approval: bool
    approval_level: str  # none, standard, manager, security
    blocking_issues: List[str]
    warnings: List[str]


class SafetyValidator:
    """
    Enterprise Safety Validator for Script Execution.

    Enforces comprehensive safety rules to prevent:
    - Unauthorized execution in production
    - High-risk operations without approval
    - Direct execution bypassing pipelines
    - Dangerous input patterns
    """

    # Dangerous patterns to detect in inputs
    DANGEROUS_INPUT_PATTERNS = [
        (r";\s*rm\s+-rf", "Command injection: rm -rf detected"),
        (r";\s*dd\s+if=", "Command injection: dd detected"),
        (r"&&\s*curl.*\|.*sh", "Remote code execution pattern"),
        (r"\$\(.*\)", "Command substitution detected"),
        (r"`.*`", "Backtick command execution"),
        (r">\s*/dev/sd[a-z]", "Direct disk write attempt"),
        (r"mkfs\.", "Filesystem format attempt"),
        (r":(){ :|:& };:", "Fork bomb detected"),
        (r"wget.*-O\s*-\s*\|", "Remote code execution via wget"),
        (r"base64\s+-d\s*\|", "Encoded payload execution"),
    ]

    # Production-forbidden operations
    PRODUCTION_FORBIDDEN = [
        "terraform_destroy",
        "delete_all",
        "drop_database",
        "truncate_table",
        "rm_rf",
        "format_disk"
    ]

    def __init__(self, registry: Dict):
        self.registry = registry
        self.safety_rules = registry.get("safety_rules", {})
        self.risk_levels = registry.get("risk_levels", {})

    def validate_execution(
        self,
        script: Dict,
        inputs: Dict,
        environment: str,
        user_role: str = "operator"
    ) -> SafetyReport:
        """
        Perform comprehensive safety validation before execution.

        Args:
            script: The script configuration from registry
            inputs: Input parameters for the script
            environment: Target environment (development, staging, production)
            user_role: Role of the user requesting execution

        Returns:
            SafetyReport with all validation results
        """
        checks: List[SafetyCheck] = []
        blocking_issues: List[str] = []
        warnings: List[str] = []

        # 1. Environment validation
        env_check = self._validate_environment(script, environment)
        checks.append(env_check)
        if env_check.result == ValidationResult.FAILED:
            blocking_issues.append(env_check.message)

        # 2. Risk level validation
        risk_check = self._validate_risk_level(script, environment, user_role)
        checks.append(risk_check)
        if risk_check.result == ValidationResult.FAILED:
            blocking_issues.append(risk_check.message)
        elif risk_check.result == ValidationResult.WARNING:
            warnings.append(risk_check.message)

        # 3. Required inputs validation
        input_check = self._validate_required_inputs(script, inputs)
        checks.append(input_check)
        if input_check.result == ValidationResult.FAILED:
            blocking_issues.append(input_check.message)

        # 4. Input sanitization
        sanitize_check = self._validate_input_sanitization(inputs)
        checks.append(sanitize_check)
        if sanitize_check.result == ValidationResult.FAILED:
            blocking_issues.append(sanitize_check.message)

        # 5. Rollback requirement
        rollback_check = self._validate_rollback_requirement(script, environment)
        checks.append(rollback_check)
        if rollback_check.result == ValidationResult.WARNING:
            warnings.append(rollback_check.message)

        # 6. Forbidden actions check
        forbidden_check = self._validate_forbidden_actions(script, environment)
        checks.append(forbidden_check)
        if forbidden_check.result == ValidationResult.FAILED:
            blocking_issues.append(forbidden_check.message)

        # 7. Dependency validation
        dep_check = self._validate_dependencies(script)
        checks.append(dep_check)
        if dep_check.result == ValidationResult.WARNING:
            warnings.append(dep_check.message)

        # 8. Execution mode validation (must be pipeline)
        pipeline_check = self._validate_pipeline_execution()
        checks.append(pipeline_check)
        if pipeline_check.result == ValidationResult.FAILED:
            blocking_issues.append(pipeline_check.message)

        # Determine overall result
        can_execute = len(blocking_issues) == 0
        overall_result = (
            ValidationResult.PASSED if can_execute and len(warnings) == 0
            else ValidationResult.WARNING if can_execute
            else ValidationResult.FAILED
        )

        # Determine approval requirements
        requires_approval, approval_level = self._determine_approval_level(
            script, environment, user_role
        )

        return SafetyReport(
            overall_result=overall_result,
            checks=checks,
            can_execute=can_execute,
            requires_approval=requires_approval,
            approval_level=approval_level,
            blocking_issues=blocking_issues,
            warnings=warnings
        )

    def _validate_environment(self, script: Dict, environment: str) -> SafetyCheck:
        """Validate script is allowed in target environment."""
        allowed_envs = script.get("environment_allowed", [])

        if environment not in allowed_envs:
            return SafetyCheck(
                name="environment_validation",
                result=ValidationResult.FAILED,
                message=f"Script not allowed in '{environment}'. Allowed: {allowed_envs}",
                severity="error",
                recommendation=f"Use one of the allowed environments: {', '.join(allowed_envs)}"
            )

        return SafetyCheck(
            name="environment_validation",
            result=ValidationResult.PASSED,
            message=f"Script allowed in '{environment}'",
            severity="info"
        )

    def _validate_risk_level(
        self,
        script: Dict,
        environment: str,
        user_role: str
    ) -> SafetyCheck:
        """Validate risk level is appropriate for environment and user."""
        risk_level = script.get("risk_level", "medium")
        risk_config = self.risk_levels.get(risk_level, {})

        # Critical risk in production
        if risk_level == "critical" and environment == "production":
            return SafetyCheck(
                name="risk_level_validation",
                result=ValidationResult.FAILED,
                message="Critical risk operations are not allowed in production",
                severity="critical",
                recommendation="Deploy to staging first, then seek security team approval"
            )

        # High risk in production without manager role
        if risk_level == "high" and environment == "production":
            if user_role not in ["manager", "admin", "security"]:
                return SafetyCheck(
                    name="risk_level_validation",
                    result=ValidationResult.WARNING,
                    message="High-risk production operation requires manager approval",
                    severity="warning",
                    recommendation="Request approval from a manager or admin"
                )

        # Medium risk warning
        if risk_level == "medium" and environment == "production":
            return SafetyCheck(
                name="risk_level_validation",
                result=ValidationResult.WARNING,
                message="Medium-risk operation in production - proceed with caution",
                severity="warning"
            )

        return SafetyCheck(
            name="risk_level_validation",
            result=ValidationResult.PASSED,
            message=f"Risk level '{risk_level}' acceptable for '{environment}'",
            severity="info"
        )

    def _validate_required_inputs(self, script: Dict, inputs: Dict) -> SafetyCheck:
        """Validate all required inputs are provided."""
        required = set(script.get("required_inputs", []))
        provided = set(inputs.keys())

        missing = required - provided

        if missing:
            return SafetyCheck(
                name="required_inputs_validation",
                result=ValidationResult.FAILED,
                message=f"Missing required inputs: {', '.join(missing)}",
                severity="error",
                recommendation=f"Provide values for: {', '.join(missing)}"
            )

        # Check for empty values
        empty = [k for k in required if k in inputs and not inputs[k]]
        if empty:
            return SafetyCheck(
                name="required_inputs_validation",
                result=ValidationResult.FAILED,
                message=f"Empty values for required inputs: {', '.join(empty)}",
                severity="error"
            )

        return SafetyCheck(
            name="required_inputs_validation",
            result=ValidationResult.PASSED,
            message="All required inputs provided",
            severity="info"
        )

    def _validate_input_sanitization(self, inputs: Dict) -> SafetyCheck:
        """Check for dangerous patterns in input values."""
        all_values = " ".join(str(v) for v in inputs.values())

        for pattern, description in self.DANGEROUS_INPUT_PATTERNS:
            if re.search(pattern, all_values, re.IGNORECASE):
                return SafetyCheck(
                    name="input_sanitization",
                    result=ValidationResult.FAILED,
                    message=f"Dangerous input detected: {description}",
                    severity="critical",
                    recommendation="Remove potentially dangerous characters/patterns from inputs"
                )

        # Check for SQL injection patterns
        sql_patterns = ["'; DROP", "1=1--", "' OR '", "UNION SELECT"]
        for pattern in sql_patterns:
            if pattern.lower() in all_values.lower():
                return SafetyCheck(
                    name="input_sanitization",
                    result=ValidationResult.FAILED,
                    message="Potential SQL injection detected in inputs",
                    severity="critical"
                )

        return SafetyCheck(
            name="input_sanitization",
            result=ValidationResult.PASSED,
            message="Input values passed sanitization",
            severity="info"
        )

    def _validate_rollback_requirement(
        self,
        script: Dict,
        environment: str
    ) -> SafetyCheck:
        """Validate rollback script exists for high-risk operations."""
        risk_level = script.get("risk_level", "medium")
        rollback = script.get("rollback_script")

        # High/critical risk in prod/staging should have rollback
        if risk_level in ["high", "critical"] and not rollback:
            if environment in ["production", "staging"]:
                return SafetyCheck(
                    name="rollback_validation",
                    result=ValidationResult.WARNING,
                    message=f"No rollback script defined for {risk_level}-risk operation",
                    severity="warning",
                    recommendation="Consider adding a rollback script for safer operations"
                )

        if rollback:
            return SafetyCheck(
                name="rollback_validation",
                result=ValidationResult.PASSED,
                message=f"Rollback script available: {rollback}",
                severity="info"
            )

        return SafetyCheck(
            name="rollback_validation",
            result=ValidationResult.PASSED,
            message="Rollback validation passed (not required for this risk level)",
            severity="info"
        )

    def _validate_forbidden_actions(
        self,
        script: Dict,
        environment: str
    ) -> SafetyCheck:
        """Check if the action is forbidden in this environment."""
        forbidden = self.safety_rules.get("forbidden_actions", [])
        script_id = script.get("id", "").lower()
        action = script.get("action", "").lower()

        # Check against forbidden list
        for forbidden_action in forbidden:
            if forbidden_action.lower() in script_id or forbidden_action.lower() == action:
                return SafetyCheck(
                    name="forbidden_actions_validation",
                    result=ValidationResult.FAILED,
                    message=f"Action '{forbidden_action}' is forbidden by safety rules",
                    severity="critical",
                    recommendation="Use GitHub Actions workflow instead of direct execution"
                )

        # Production-specific forbidden operations
        if environment == "production":
            for prod_forbidden in self.PRODUCTION_FORBIDDEN:
                if prod_forbidden in script_id or prod_forbidden in action:
                    return SafetyCheck(
                        name="forbidden_actions_validation",
                        result=ValidationResult.FAILED,
                        message=f"Action '{prod_forbidden}' is forbidden in production",
                        severity="critical"
                    )

        return SafetyCheck(
            name="forbidden_actions_validation",
            result=ValidationResult.PASSED,
            message="Action is allowed",
            severity="info"
        )

    def _validate_dependencies(self, script: Dict) -> SafetyCheck:
        """Validate script dependencies are documented."""
        dependencies = script.get("dependencies", [])

        if not dependencies:
            return SafetyCheck(
                name="dependency_validation",
                result=ValidationResult.WARNING,
                message="No dependencies documented - ensure required access is available",
                severity="warning"
            )

        return SafetyCheck(
            name="dependency_validation",
            result=ValidationResult.PASSED,
            message=f"Dependencies documented: {', '.join(dependencies)}",
            severity="info"
        )

    def _validate_pipeline_execution(self) -> SafetyCheck:
        """Validate that execution mode is pipeline-only."""
        execution_mode = self.registry.get("execution_mode", "")

        if execution_mode != "pipeline_only":
            return SafetyCheck(
                name="pipeline_execution_validation",
                result=ValidationResult.FAILED,
                message="Direct execution is forbidden. Must use pipeline execution mode.",
                severity="critical",
                recommendation="Configure registry with execution_mode: 'pipeline_only'"
            )

        return SafetyCheck(
            name="pipeline_execution_validation",
            result=ValidationResult.PASSED,
            message="Pipeline execution mode confirmed",
            severity="info"
        )

    def _determine_approval_level(
        self,
        script: Dict,
        environment: str,
        user_role: str
    ) -> Tuple[bool, str]:
        """Determine the approval level required for this execution."""
        risk_level = script.get("risk_level", "medium")
        auto_approve = script.get("auto_approve", False)
        risk_config = self.risk_levels.get(risk_level, {})

        # Low risk with auto_approve = no approval needed
        if risk_level == "low" and auto_approve:
            return False, "none"

        # Critical always needs security approval
        if risk_level == "critical":
            return True, "security"

        # High risk in production needs manager
        if risk_level == "high" and environment == "production":
            if user_role in ["manager", "admin", "security"]:
                return False, "none"
            return True, "manager"

        # Medium/high risk needs standard approval
        if risk_level in ["medium", "high"]:
            if not auto_approve:
                return True, "standard"

        # Production always needs at least standard approval for non-low risk
        if environment == "production" and risk_level != "low":
            return True, "standard"

        return False, "none"

    def generate_safety_summary(self, report: SafetyReport) -> str:
        """Generate a human-readable safety summary."""
        lines = []

        # Header
        if report.can_execute:
            lines.append("✅ SAFETY VALIDATION PASSED")
        else:
            lines.append("❌ SAFETY VALIDATION FAILED")

        lines.append("")

        # Blocking issues
        if report.blocking_issues:
            lines.append("🚫 Blocking Issues:")
            for issue in report.blocking_issues:
                lines.append(f"   • {issue}")
            lines.append("")

        # Warnings
        if report.warnings:
            lines.append("⚠️  Warnings:")
            for warning in report.warnings:
                lines.append(f"   • {warning}")
            lines.append("")

        # Approval requirements
        if report.requires_approval:
            lines.append(f"📋 Approval Required: {report.approval_level}")
        else:
            lines.append("✓ No approval required")

        # Check summary
        passed = sum(1 for c in report.checks if c.result == ValidationResult.PASSED)
        failed = sum(1 for c in report.checks if c.result == ValidationResult.FAILED)
        warned = sum(1 for c in report.checks if c.result == ValidationResult.WARNING)

        lines.append("")
        lines.append(f"Checks: {passed} passed, {warned} warnings, {failed} failed")

        return "\n".join(lines)


def create_validator(registry: Dict) -> SafetyValidator:
    """Factory function to create a SafetyValidator instance."""
    return SafetyValidator(registry)
