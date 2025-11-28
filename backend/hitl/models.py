#!/usr/bin/env python3
"""
Human-in-the-Loop (HITL) Data Models
Implements STEP 3 (Human Override) and STEP 5 (Human Approval) workflows
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Approval status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ApprovalType(str, Enum):
    """Type of approval required"""
    ROUTING_OVERRIDE = "routing_override"  # STEP 3: Human override of agent selection
    PLAN_APPROVAL = "plan_approval"        # STEP 5: Approve execution plan


class RiskLevel(str, Enum):
    """Risk level for execution plans"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ExecutionPlan(BaseModel):
    """
    Standardized execution plan schema
    Used by all agents for STEP 4 (Sub-Agent Planning)
    """
    plan_id: str = Field(..., description="Unique plan ID")
    agent_name: str = Field(..., description="Agent that created the plan")
    ticket_id: str = Field(..., description="Associated ticket/incident ID")

    # Plan steps
    steps: List[Dict[str, str]] = Field(..., description="Sequential steps")
    commands: List[str] = Field(default_factory=list, description="Commands to execute")
    files_to_edit: List[str] = Field(default_factory=list, description="Files that will be modified")
    apis_to_call: List[str] = Field(default_factory=list, description="External APIs to call")

    # Risk assessment
    risk_level: RiskLevel = Field(..., description="Overall risk level")
    risk_reasons: List[str] = Field(default_factory=list, description="Why this risk level")

    # Metadata
    estimated_duration_minutes: int = Field(default=5, description="Estimated execution time")
    rollback_available: bool = Field(default=False, description="Can this be rolled back?")
    requires_approval: bool = Field(default=True, description="Does this need HITL approval?")

    # Context
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoutingDecision(BaseModel):
    """
    Routing decision from orchestrator (STEP 2 output)
    """
    ticket_id: str
    ticket_text: str

    # LLM routing decision
    selected_agent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str

    # Supporting evidence
    similar_tickets: List[Dict] = Field(default_factory=list, description="From vector DB")
    graph_context: Dict = Field(default_factory=dict, description="From Neo4j")
    cluster_info: Optional[Dict] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoutingOverride(BaseModel):
    """
    Human override for routing decision (STEP 3)
    """
    ticket_id: str
    original_agent: str
    overridden_agent: str
    override_reason: str
    override_by: str = Field(..., description="User who made override")
    override_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalRequest(BaseModel):
    """
    Request for human approval
    Used for both STEP 3 (routing) and STEP 5 (plan execution)
    """
    approval_id: str = Field(..., description="Unique approval ID")
    approval_type: ApprovalType

    # Request details
    ticket_id: str
    requested_by: str = Field(default="system", description="Agent or system component")
    request_data: Dict[str, Any] = Field(..., description="Data to approve")

    # For routing override (STEP 3)
    routing_decision: Optional[RoutingDecision] = None

    # For plan approval (STEP 5)
    execution_plan: Optional[ExecutionPlan] = None

    # Approval settings
    timeout_minutes: int = Field(default=30, description="Approval timeout")
    approvers: List[str] = Field(default_factory=list, description="Who can approve")

    # Status
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class ApprovalResponse(BaseModel):
    """
    Response to approval request
    """
    approval_id: str
    status: ApprovalStatus
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    alternative_suggestion: Optional[Dict] = None

    # For routing override
    selected_agent: Optional[str] = None

    # For plan approval
    modified_plan: Optional[ExecutionPlan] = None

    comments: Optional[str] = None
    approved_at: datetime = Field(default_factory=datetime.utcnow)


class ApprovalLog(BaseModel):
    """
    Complete log of approval workflow
    Stored in PostgreSQL for audit trail
    """
    log_id: str
    approval_request: ApprovalRequest
    approval_response: Optional[ApprovalResponse] = None

    # Workflow tracking
    request_sent_at: datetime
    response_received_at: Optional[datetime] = None
    notification_sent: bool = False
    notification_channel: Optional[str] = None  # "slack", "email", etc.

    # Outcome
    final_status: ApprovalStatus
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None
    execution_result: Optional[Dict] = None


# Database schemas (for PostgreSQL)

CREATE_APPROVAL_LOGS_TABLE = """
CREATE TABLE IF NOT EXISTS approval_logs (
    log_id VARCHAR(255) PRIMARY KEY,
    approval_id VARCHAR(255) UNIQUE NOT NULL,
    approval_type VARCHAR(50) NOT NULL,
    ticket_id VARCHAR(255) NOT NULL,

    -- Request data (JSON)
    routing_decision JSONB,
    execution_plan JSONB,

    -- Status tracking
    status VARCHAR(50) NOT NULL,
    requested_by VARCHAR(255),
    approved_by VARCHAR(255),

    -- Timestamps
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP,
    timeout_at TIMESTAMP,
    approved_at TIMESTAMP,

    -- Outcome
    rejection_reason TEXT,
    alternative_suggestion JSONB,
    modified_plan JSONB,
    comments TEXT,

    -- Execution tracking
    execution_started_at TIMESTAMP,
    execution_completed_at TIMESTAMP,
    execution_result JSONB,

    -- Notification
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_channel VARCHAR(50),

    -- Indexes
    INDEX idx_ticket_id (ticket_id),
    INDEX idx_status (status),
    INDEX idx_approval_type (approval_type),
    INDEX idx_created_at (created_at)
);
"""

CREATE_ROUTING_OVERRIDES_TABLE = """
CREATE TABLE IF NOT EXISTS routing_overrides (
    override_id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL,
    original_agent VARCHAR(100) NOT NULL,
    overridden_agent VARCHAR(100) NOT NULL,
    override_reason TEXT,
    override_by VARCHAR(255) NOT NULL,
    override_at TIMESTAMP NOT NULL,
    confidence_score FLOAT,

    INDEX idx_ticket_id (ticket_id),
    INDEX idx_override_at (override_at)
);
"""

CREATE_EXECUTION_PLANS_TABLE = """
CREATE TABLE IF NOT EXISTS execution_plans (
    plan_id VARCHAR(255) PRIMARY KEY,
    ticket_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,

    -- Plan details (JSON)
    steps JSONB NOT NULL,
    commands JSONB,
    files_to_edit JSONB,
    apis_to_call JSONB,

    -- Risk
    risk_level VARCHAR(50) NOT NULL,
    risk_reasons JSONB,

    -- Metadata
    estimated_duration_minutes INTEGER,
    rollback_available BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT TRUE,

    -- Context
    context JSONB,

    -- Status
    plan_status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP NOT NULL,
    approved_at TIMESTAMP,
    executed_at TIMESTAMP,

    INDEX idx_ticket_id (ticket_id),
    INDEX idx_plan_status (plan_status),
    INDEX idx_risk_level (risk_level)
);
"""
