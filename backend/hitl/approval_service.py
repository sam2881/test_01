#!/usr/bin/env python3
"""
Human-in-the-Loop Approval Service
Implements STEP 3 (Human Override) and STEP 5 (Human Approval)
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import structlog
import httpx
from backend.hitl.models import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalLog,
    ApprovalStatus,
    ApprovalType,
    RoutingDecision,
    ExecutionPlan,
    RoutingOverride
)
from backend.utils.postgres_client import PostgreSQLClient

logger = structlog.get_logger()


class ApprovalService:
    """
    Manages human approval workflows
    - STEP 3: Routing override (human can change agent selection)
    - STEP 5: Plan approval (human approves execution plan)
    """

    def __init__(
        self,
        postgres_client: PostgreSQLClient,
        slack_webhook_url: Optional[str] = None,
        default_timeout_minutes: int = 30
    ):
        self.db = postgres_client
        self.slack_webhook_url = slack_webhook_url
        self.default_timeout_minutes = default_timeout_minutes

        # In-memory cache of pending approvals (could use Redis in production)
        self.pending_approvals: Dict[str, ApprovalRequest] = {}

        self._ensure_tables()

    def _ensure_tables(self):
        """Create database tables if they don't exist"""
        from backend.hitl.models import (
            CREATE_APPROVAL_LOGS_TABLE,
            CREATE_ROUTING_OVERRIDES_TABLE,
            CREATE_EXECUTION_PLANS_TABLE
        )

        try:
            self.db.execute(CREATE_APPROVAL_LOGS_TABLE)
            self.db.execute(CREATE_ROUTING_OVERRIDES_TABLE)
            self.db.execute(CREATE_EXECUTION_PLANS_TABLE)
            logger.info("approval_tables_ensured")
        except Exception as e:
            logger.error("table_creation_failed", error=str(e))

    # ===========================
    # STEP 3: Routing Override
    # ===========================

    async def request_routing_approval(
        self,
        routing_decision: RoutingDecision,
        timeout_minutes: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Request human review of routing decision (STEP 3)
        Returns: ApprovalRequest that can be approved/rejected
        """
        approval_id = f"routing_{routing_decision.ticket_id}_{uuid.uuid4().hex[:8]}"

        approval_request = ApprovalRequest(
            approval_id=approval_id,
            approval_type=ApprovalType.ROUTING_OVERRIDE,
            ticket_id=routing_decision.ticket_id,
            requested_by="orchestrator",
            request_data={
                "selected_agent": routing_decision.selected_agent,
                "confidence": routing_decision.confidence,
                "reasoning": routing_decision.reasoning
            },
            routing_decision=routing_decision,
            timeout_minutes=timeout_minutes or self.default_timeout_minutes
        )

        # Store in database
        self._save_approval_request(approval_request)

        # Store in memory cache
        self.pending_approvals[approval_id] = approval_request

        # Send notification
        await self._send_approval_notification(approval_request)

        logger.info(
            "routing_approval_requested",
            approval_id=approval_id,
            ticket_id=routing_decision.ticket_id,
            selected_agent=routing_decision.selected_agent
        )

        return approval_request

    async def wait_for_routing_approval(
        self,
        approval_id: str,
        poll_interval_seconds: int = 5
    ) -> Optional[ApprovalResponse]:
        """
        Wait for human approval of routing decision
        Returns None if timeout
        """
        import asyncio

        approval_request = self.pending_approvals.get(approval_id)
        if not approval_request:
            logger.error("approval_not_found", approval_id=approval_id)
            return None

        timeout_at = approval_request.created_at + timedelta(minutes=approval_request.timeout_minutes)

        while datetime.utcnow() < timeout_at:
            # Check if approval received
            response = self._get_approval_response(approval_id)
            if response:
                logger.info(
                    "routing_approval_received",
                    approval_id=approval_id,
                    status=response.status
                )
                return response

            # Wait before next check
            await asyncio.sleep(poll_interval_seconds)

        # Timeout
        logger.warning("routing_approval_timeout", approval_id=approval_id)
        self._mark_approval_timeout(approval_id)
        return None

    def get_routing_with_override(
        self,
        routing_decision: RoutingDecision,
        approval_response: Optional[ApprovalResponse]
    ) -> str:
        """
        Get final agent selection (original or overridden)
        """
        if approval_response and approval_response.selected_agent:
            # Human override
            logger.info(
                "routing_overridden",
                ticket_id=routing_decision.ticket_id,
                original=routing_decision.selected_agent,
                overridden=approval_response.selected_agent,
                by=approval_response.approved_by
            )
            return approval_response.selected_agent
        else:
            # Use original LLM decision
            return routing_decision.selected_agent

    # ===========================
    # STEP 5: Plan Approval
    # ===========================

    async def request_plan_approval(
        self,
        execution_plan: ExecutionPlan,
        timeout_minutes: Optional[int] = None
    ) -> ApprovalRequest:
        """
        Request human approval of execution plan (STEP 5)
        Returns: ApprovalRequest that can be approved/rejected/modified
        """
        approval_id = f"plan_{execution_plan.ticket_id}_{uuid.uuid4().hex[:8]}"

        approval_request = ApprovalRequest(
            approval_id=approval_id,
            approval_type=ApprovalType.PLAN_APPROVAL,
            ticket_id=execution_plan.ticket_id,
            requested_by=execution_plan.agent_name,
            request_data={
                "risk_level": execution_plan.risk_level,
                "steps_count": len(execution_plan.steps),
                "commands_count": len(execution_plan.commands)
            },
            execution_plan=execution_plan,
            timeout_minutes=timeout_minutes or self.default_timeout_minutes
        )

        # Store in database
        self._save_approval_request(approval_request)

        # Store in memory cache
        self.pending_approvals[approval_id] = approval_request

        # Send notification
        await self._send_approval_notification(approval_request)

        logger.info(
            "plan_approval_requested",
            approval_id=approval_id,
            ticket_id=execution_plan.ticket_id,
            agent=execution_plan.agent_name,
            risk=execution_plan.risk_level
        )

        return approval_request

    async def wait_for_plan_approval(
        self,
        approval_id: str,
        poll_interval_seconds: int = 5
    ) -> Optional[ApprovalResponse]:
        """
        Wait for human approval of execution plan
        Returns None if timeout
        """
        import asyncio

        approval_request = self.pending_approvals.get(approval_id)
        if not approval_request:
            logger.error("approval_not_found", approval_id=approval_id)
            return None

        timeout_at = approval_request.created_at + timedelta(minutes=approval_request.timeout_minutes)

        while datetime.utcnow() < timeout_at:
            # Check if approval received
            response = self._get_approval_response(approval_id)
            if response:
                logger.info(
                    "plan_approval_received",
                    approval_id=approval_id,
                    status=response.status
                )
                return response

            # Wait before next check
            await asyncio.sleep(poll_interval_seconds)

        # Timeout
        logger.warning("plan_approval_timeout", approval_id=approval_id)
        self._mark_approval_timeout(approval_id)
        return None

    def get_approved_plan(
        self,
        execution_plan: ExecutionPlan,
        approval_response: Optional[ApprovalResponse]
    ) -> Optional[ExecutionPlan]:
        """
        Get final execution plan (original, modified, or None if rejected)
        """
        if not approval_response:
            logger.warning("no_approval_response", plan_id=execution_plan.plan_id)
            return None

        if approval_response.status == ApprovalStatus.REJECTED:
            logger.info("plan_rejected", plan_id=execution_plan.plan_id)
            return None

        if approval_response.modified_plan:
            # Human modified the plan
            logger.info("plan_modified", plan_id=execution_plan.plan_id)
            return approval_response.modified_plan

        # Approved as-is
        logger.info("plan_approved", plan_id=execution_plan.plan_id)
        return execution_plan

    # ===========================
    # API Methods (for UI/Slack)
    # ===========================

    def approve_request(
        self,
        approval_id: str,
        approved_by: str,
        selected_agent: Optional[str] = None,
        modified_plan: Optional[ExecutionPlan] = None,
        comments: Optional[str] = None
    ) -> ApprovalResponse:
        """
        Approve a pending request (called by human via API/Slack)
        """
        approval_request = self.pending_approvals.get(approval_id)
        if not approval_request:
            raise ValueError(f"Approval {approval_id} not found")

        response = ApprovalResponse(
            approval_id=approval_id,
            status=ApprovalStatus.APPROVED,
            approved_by=approved_by,
            selected_agent=selected_agent,
            modified_plan=modified_plan,
            comments=comments
        )

        self._save_approval_response(response)

        # Remove from pending
        self.pending_approvals.pop(approval_id, None)

        logger.info(
            "request_approved",
            approval_id=approval_id,
            approved_by=approved_by
        )

        return response

    def reject_request(
        self,
        approval_id: str,
        rejected_by: str,
        rejection_reason: str,
        alternative_suggestion: Optional[Dict] = None
    ) -> ApprovalResponse:
        """
        Reject a pending request
        """
        approval_request = self.pending_approvals.get(approval_id)
        if not approval_request:
            raise ValueError(f"Approval {approval_id} not found")

        response = ApprovalResponse(
            approval_id=approval_id,
            status=ApprovalStatus.REJECTED,
            approved_by=rejected_by,
            rejection_reason=rejection_reason,
            alternative_suggestion=alternative_suggestion
        )

        self._save_approval_response(response)

        # Remove from pending
        self.pending_approvals.pop(approval_id, None)

        logger.info(
            "request_rejected",
            approval_id=approval_id,
            rejected_by=rejected_by,
            reason=rejection_reason
        )

        return response

    # ===========================
    # Database Operations
    # ===========================

    def _save_approval_request(self, request: ApprovalRequest):
        """Save approval request to database"""
        query = """
        INSERT INTO approval_logs (
            log_id, approval_id, approval_type, ticket_id,
            routing_decision, execution_plan,
            status, requested_by, created_at, timeout_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """
        import json

        timeout_at = request.created_at + timedelta(minutes=request.timeout_minutes)

        self.db.execute(
            query,
            f"log_{request.approval_id}",
            request.approval_id,
            request.approval_type.value,
            request.ticket_id,
            json.dumps(request.routing_decision.dict()) if request.routing_decision else None,
            json.dumps(request.execution_plan.dict()) if request.execution_plan else None,
            request.status.value,
            request.requested_by,
            request.created_at,
            timeout_at
        )

    def _save_approval_response(self, response: ApprovalResponse):
        """Save approval response to database"""
        query = """
        UPDATE approval_logs SET
            status = $1,
            approved_by = $2,
            approved_at = $3,
            rejection_reason = $4,
            alternative_suggestion = $5,
            modified_plan = $6,
            comments = $7,
            updated_at = $8
        WHERE approval_id = $9
        """
        import json

        self.db.execute(
            query,
            response.status.value,
            response.approved_by,
            response.approved_at,
            response.rejection_reason,
            json.dumps(response.alternative_suggestion) if response.alternative_suggestion else None,
            json.dumps(response.modified_plan.dict()) if response.modified_plan else None,
            response.comments,
            datetime.utcnow(),
            response.approval_id
        )

    def _get_approval_response(self, approval_id: str) -> Optional[ApprovalResponse]:
        """Get approval response from database"""
        query = """
        SELECT status, approved_by, approved_at, rejection_reason,
               alternative_suggestion, modified_plan, comments
        FROM approval_logs
        WHERE approval_id = $1 AND status != 'pending'
        """
        result = self.db.fetch_one(query, approval_id)

        if result:
            return ApprovalResponse(
                approval_id=approval_id,
                status=ApprovalStatus(result['status']),
                approved_by=result['approved_by'],
                approved_at=result['approved_at'],
                rejection_reason=result['rejection_reason'],
                alternative_suggestion=result['alternative_suggestion'],
                comments=result['comments']
            )
        return None

    def _mark_approval_timeout(self, approval_id: str):
        """Mark approval as timed out"""
        query = """
        UPDATE approval_logs SET
            status = 'timeout',
            updated_at = $1
        WHERE approval_id = $2
        """
        self.db.execute(query, datetime.utcnow(), approval_id)

        # Remove from pending
        self.pending_approvals.pop(approval_id, None)

    # ===========================
    # Notifications
    # ===========================

    async def _send_approval_notification(self, request: ApprovalRequest):
        """Send approval notification to Slack"""
        if not self.slack_webhook_url:
            logger.warning("slack_webhook_not_configured")
            return

        if request.approval_type == ApprovalType.ROUTING_OVERRIDE:
            message = self._format_routing_notification(request)
        else:
            message = self._format_plan_notification(request)

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.slack_webhook_url,
                    json=message,
                    timeout=10.0
                )
            logger.info("slack_notification_sent", approval_id=request.approval_id)
        except Exception as e:
            logger.error("slack_notification_failed", error=str(e))

    def _format_routing_notification(self, request: ApprovalRequest) -> Dict:
        """Format Slack message for routing approval"""
        routing = request.routing_decision

        return {
            "text": f"🤖 Routing Approval Required: {request.ticket_id}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Routing Approval Required*\n\n"
                                f"*Ticket:* {request.ticket_id}\n"
                                f"*Selected Agent:* {routing.selected_agent}\n"
                                f"*Confidence:* {routing.confidence:.2%}\n\n"
                                f"*Reasoning:* {routing.reasoning}\n\n"
                                f"Approve at: http://localhost:8000/api/approvals/{request.approval_id}"
                    }
                }
            ]
        }

    def _format_plan_notification(self, request: ApprovalRequest) -> Dict:
        """Format Slack message for plan approval"""
        plan = request.execution_plan

        return {
            "text": f"⚠️  Execution Plan Approval Required: {request.ticket_id}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Execution Plan Approval Required*\n\n"
                                f"*Ticket:* {request.ticket_id}\n"
                                f"*Agent:* {plan.agent_name}\n"
                                f"*Risk Level:* {plan.risk_level.value.upper()}\n"
                                f"*Steps:* {len(plan.steps)}\n"
                                f"*Commands:* {len(plan.commands)}\n\n"
                                f"Approve at: http://localhost:8000/api/approvals/{request.approval_id}"
                    }
                }
            ]
        }

    # ===========================
    # Statistics
    # ===========================

    def get_approval_stats(self, days: int = 30) -> Dict:
        """Get approval statistics"""
        query = """
        SELECT
            approval_type,
            status,
            COUNT(*) as count
        FROM approval_logs
        WHERE created_at >= NOW() - INTERVAL '{} days'
        GROUP BY approval_type, status
        """.format(days)

        results = self.db.fetch_all(query)

        stats = {
            "total": 0,
            "by_type": {},
            "by_status": {}
        }

        for row in results:
            stats["total"] += row["count"]
            stats["by_type"][row["approval_type"]] = stats["by_type"].get(row["approval_type"], 0) + row["count"]
            stats["by_status"][row["status"]] = stats["by_status"].get(row["status"], 0) + row["count"]

        return stats
