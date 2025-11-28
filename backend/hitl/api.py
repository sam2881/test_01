#!/usr/bin/env python3
"""
HITL API Endpoints
Provides REST API for human approval workflows
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import structlog

from backend.hitl.models import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ExecutionPlan,
    RiskLevel
)
from backend.hitl.approval_service import ApprovalService

logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/hitl", tags=["hitl"])

# Global approval service (initialized by main app)
approval_service: Optional[ApprovalService] = None


def init_hitl_api(service: ApprovalService):
    """Initialize HITL API with approval service"""
    global approval_service
    approval_service = service
    logger.info("hitl_api_initialized")


# ===========================
# Request Models
# ===========================

class ApproveRoutingRequest(BaseModel):
    """Request to approve/override routing"""
    approved_by: str
    selected_agent: Optional[str] = None  # If None, uses original agent
    comments: Optional[str] = None


class RejectRoutingRequest(BaseModel):
    """Request to reject routing"""
    rejected_by: str
    rejection_reason: str
    alternative_agent: Optional[str] = None


class ApprovePlanRequest(BaseModel):
    """Request to approve execution plan"""
    approved_by: str
    modified_plan: Optional[ExecutionPlan] = None  # If None, uses original plan
    comments: Optional[str] = None


class RejectPlanRequest(BaseModel):
    """Request to reject execution plan"""
    rejected_by: str
    rejection_reason: str
    alternative_steps: Optional[List[str]] = None


# ===========================
# Endpoints
# ===========================

@router.get("/approvals/pending", response_model=List[ApprovalRequest])
async def get_pending_approvals():
    """Get all pending approval requests"""
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    pending = list(approval_service.pending_approvals.values())

    logger.info("pending_approvals_fetched", count=len(pending))
    return pending


@router.get("/approvals/{approval_id}", response_model=ApprovalRequest)
async def get_approval(approval_id: str):
    """Get specific approval request"""
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    approval = approval_service.pending_approvals.get(approval_id)
    if not approval:
        # Try database
        raise HTTPException(404, f"Approval {approval_id} not found")

    return approval


@router.post("/approvals/{approval_id}/approve-routing", response_model=ApprovalResponse)
async def approve_routing(
    approval_id: str,
    request: ApproveRoutingRequest
):
    """
    Approve routing decision (STEP 3)
    - If selected_agent is provided, overrides LLM decision
    - If not provided, uses original LLM decision
    """
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    try:
        response = approval_service.approve_request(
            approval_id=approval_id,
            approved_by=request.approved_by,
            selected_agent=request.selected_agent,
            comments=request.comments
        )

        logger.info(
            "routing_approved_via_api",
            approval_id=approval_id,
            approved_by=request.approved_by,
            overridden=request.selected_agent is not None
        )

        return response

    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/approvals/{approval_id}/reject-routing", response_model=ApprovalResponse)
async def reject_routing(
    approval_id: str,
    request: RejectRoutingRequest
):
    """Reject routing decision (STEP 3)"""
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    try:
        alternative = {"suggested_agent": request.alternative_agent} if request.alternative_agent else None

        response = approval_service.reject_request(
            approval_id=approval_id,
            rejected_by=request.rejected_by,
            rejection_reason=request.rejection_reason,
            alternative_suggestion=alternative
        )

        logger.info(
            "routing_rejected_via_api",
            approval_id=approval_id,
            rejected_by=request.rejected_by
        )

        return response

    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/approvals/{approval_id}/approve-plan", response_model=ApprovalResponse)
async def approve_plan(
    approval_id: str,
    request: ApprovePlanRequest
):
    """
    Approve execution plan (STEP 5)
    - If modified_plan is provided, uses modified version
    - If not provided, uses original plan
    """
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    try:
        response = approval_service.approve_request(
            approval_id=approval_id,
            approved_by=request.approved_by,
            modified_plan=request.modified_plan,
            comments=request.comments
        )

        logger.info(
            "plan_approved_via_api",
            approval_id=approval_id,
            approved_by=request.approved_by,
            modified=request.modified_plan is not None
        )

        return response

    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/approvals/{approval_id}/reject-plan", response_model=ApprovalResponse)
async def reject_plan(
    approval_id: str,
    request: RejectPlanRequest
):
    """Reject execution plan (STEP 5)"""
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    try:
        alternative = {"suggested_steps": request.alternative_steps} if request.alternative_steps else None

        response = approval_service.reject_request(
            approval_id=approval_id,
            rejected_by=request.rejected_by,
            rejection_reason=request.rejection_reason,
            alternative_suggestion=alternative
        )

        logger.info(
            "plan_rejected_via_api",
            approval_id=approval_id,
            rejected_by=request.rejected_by
        )

        return response

    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/stats")
async def get_approval_stats(days: int = 30):
    """Get approval statistics"""
    if not approval_service:
        raise HTTPException(500, "Approval service not initialized")

    stats = approval_service.get_approval_stats(days=days)

    return {
        "period_days": days,
        **stats
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "hitl_api",
        "approval_service_initialized": approval_service is not None,
        "pending_approvals": len(approval_service.pending_approvals) if approval_service else 0
    }
