export type AgentStatus = 'active' | 'idle' | 'error' | 'offline'

export interface Agent {
  name: string
  display_name: string
  description: string
  status: AgentStatus
  health_check?: {
    last_check: string
    status: 'healthy' | 'degraded' | 'unhealthy'
    response_time_ms?: number
  }
  capabilities: string[]
  metrics?: AgentMetrics
}

export interface AgentMetrics {
  total_tasks: number
  successful_tasks: number
  failed_tasks: number
  success_rate: number
  average_response_time_ms: number
  tasks_last_24h: number
  current_load: number
  last_active?: string
}

export interface AgentLog {
  timestamp: string
  level: 'info' | 'warning' | 'error'
  message: string
  task_id?: string
  metadata?: Record<string, any>
}

export const AGENT_NAMES = {
  SERVICENOW: 'servicenow',
  JIRA: 'jira',
  GITHUB: 'github',
  INFRASTRUCTURE: 'infrastructure',
  DATA: 'data',
  GCP_MONITOR: 'gcp_monitor',
  DSPY_OPTIMIZER: 'dspy_optimizer',
} as const

export const AGENT_DISPLAY_NAMES: Record<string, string> = {
  servicenow: 'ServiceNow Agent',
  jira: 'Jira Agent',
  github: 'GitHub Agent',
  infrastructure: 'Infrastructure Agent',
  data: 'Data Agent',
  gcp_monitor: 'GCP Monitor Agent',
  dspy_optimizer: 'DSPy Optimizer',
}
