export type ApprovalType = 'routing_override' | 'plan_approval'
export type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'timeout'
export type RiskLevel = 'Low' | 'Medium' | 'High' | 'Critical'

export interface ApprovalRequest {
  approval_id: string
  approval_type: ApprovalType
  status: ApprovalStatus
  created_at: string
  timeout_at: string
  incident_id?: string
  routing_decision?: RoutingDecision
  execution_plan?: ExecutionPlan
  approved_by?: string
  approved_at?: string
  rejection_reason?: string
}

export interface RoutingDecision {
  selected_agent: string
  confidence: number
  reasoning: string
  alternative_agents?: {
    agent_name: string
    confidence: number
  }[]
  similar_incidents?: {
    incident_id: string
    short_description: string
    assigned_agent: string
    similarity_score: number
  }[]
}

export interface ExecutionPlan {
  agent_name: string
  steps: {
    step_number: number
    action: string
    description: string
    estimated_time?: string
  }[]
  commands: string[]
  files_to_edit: string[]
  risk_level: RiskLevel
  estimated_duration?: string
  rollback_plan?: string[]
}

export interface ApproveRoutingRequest {
  approved_by: string
  selected_agent: string
  override_reason?: string
}

export interface ApprovePlanRequest {
  approved_by: string
  modifications?: string
}

export interface RejectPlanRequest {
  rejected_by: string
  rejection_reason: string
}
