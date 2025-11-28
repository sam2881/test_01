'use client'

import { useQuery } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { Card, CardContent } from '@/components/ui/Card'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { WorkflowVisualization, WorkflowData } from '@/components/workflow/WorkflowVisualization'
import { Badge } from '@/components/ui/Badge'
import { Activity, CheckCircle2, XCircle, Clock } from 'lucide-react'

// Mock data - replace with API call
const mockWorkflows: WorkflowData[] = [
  {
    incident_id: 'INC0010002',
    workflow_id: 'wf-2024-001',
    status: 'active',
    current_step: 3,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    steps: [
      {
        id: 'orchestrator',
        name: 'Main Orchestrator',
        description: 'Analyze incident and determine routing strategy',
        status: 'completed',
        timestamp: new Date(Date.now() - 300000).toISOString(),
        duration: '2.3s',
        agent: 'main-orchestrator',
        output: {
          analysis: 'GCP Database incident - High CPU usage',
          recommended_agent: 'Infrastructure Agent',
        },
      },
      {
        id: 'llm_analysis',
        name: 'LLM Analysis',
        description: 'GPT-4 analyzes incident context and retrieves similar cases from RAG',
        status: 'completed',
        timestamp: new Date(Date.now() - 280000).toISOString(),
        duration: '4.5s',
        llm_model: 'gpt-4-turbo',
        confidence: 0.92,
        output: {
          reasoning: 'Database performance degradation pattern detected',
          similar_incidents: 3,
          rag_sources: ['incident-resolution-db-001', 'runbook-gcp-scaling'],
        },
      },
      {
        id: 'hitl_routing',
        name: 'HITL-1: Routing Approval',
        description: 'Human approval required for agent routing decision',
        status: 'completed',
        timestamp: new Date(Date.now() - 240000).toISOString(),
        duration: '45s',
        output: {
          approved_agent: 'Infrastructure Agent',
          approver: 'admin@company.com',
          comment: 'Approved for automated scaling',
        },
      },
      {
        id: 'agent_selection',
        name: 'Sub-Agent Selection',
        description: 'Route to Infrastructure Agent for GCP operations',
        status: 'in_progress',
        timestamp: new Date(Date.now() - 180000).toISOString(),
        agent: 'infrastructure-agent',
      },
      {
        id: 'llm_planning',
        name: 'LLM Execution Planning',
        description: 'Generate detailed execution plan with rollback strategy',
        status: 'pending',
        llm_model: 'gpt-4-turbo',
      },
      {
        id: 'hitl_execution',
        name: 'HITL-2: Execution Approval',
        description: 'Human approval required for execution plan',
        status: 'pending',
      },
      {
        id: 'execution',
        name: 'Execution',
        description: 'Execute approved plan using GCP APIs and Terraform',
        status: 'pending',
      },
      {
        id: 'rag_update',
        name: 'RAG Update',
        description: 'Update Weaviate & Neo4j with resolution knowledge',
        status: 'pending',
      },
      {
        id: 'resolution',
        name: 'Resolution',
        description: 'Mark incident as resolved and notify stakeholders',
        status: 'pending',
      },
    ],
  },
]

export default function WorkflowsPage() {
  // Replace with actual API call
  const { data: workflows, isLoading } = useQuery({
    queryKey: ['workflows'],
    queryFn: async () => {
      // Simulated delay
      await new Promise(resolve => setTimeout(resolve, 1000))
      return mockWorkflows
    },
  })

  if (isLoading) {
    return (
      <PageLayout title="Workflows">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading workflows..." />
        </div>
      </PageLayout>
    )
  }

  const activeWorkflows = workflows?.filter(w => w.status === 'active') || []
  const completedWorkflows = workflows?.filter(w => w.status === 'completed') || []
  const failedWorkflows = workflows?.filter(w => w.status === 'failed') || []

  return (
    <PageLayout
      title="Incident Resolution Workflows"
      subtitle="LangGraph-powered multi-agent orchestration with Human-in-the-Loop"
    >
      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Workflows</p>
                <p className="text-2xl font-bold mt-1">{workflows?.length || 0}</p>
              </div>
              <Activity className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Active</p>
                <p className="text-2xl font-bold mt-1 text-blue-600">{activeWorkflows.length}</p>
              </div>
              <Clock className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Completed</p>
                <p className="text-2xl font-bold mt-1 text-green-600">{completedWorkflows.length}</p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Failed</p>
                <p className="text-2xl font-bold mt-1 text-red-600">{failedWorkflows.length}</p>
              </div>
              <XCircle className="w-8 h-8 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Workflow List */}
      {!workflows || workflows.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No active workflows</p>
            <p className="text-sm text-gray-500 mt-1">
              Workflows will appear here when incidents are processed through the AI agent system
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {workflows.map((workflow) => (
            <div key={workflow.workflow_id}>
              <div className="mb-4 flex items-center gap-3">
                <h2 className="text-xl font-semibold">Incident {workflow.incident_id}</h2>
                <Badge variant={workflow.status === 'completed' ? 'success' : workflow.status === 'failed' ? 'error' : 'info'}>
                  {workflow.status}
                </Badge>
              </div>
              <WorkflowVisualization
                workflow={workflow}
                onApprove={(stepId) => {
                  console.log('Approve step:', stepId)
                  // Handle approval
                }}
                onReject={(stepId) => {
                  console.log('Reject step:', stepId)
                  // Handle rejection
                }}
              />
            </div>
          ))}
        </div>
      )}
    </PageLayout>
  )
}
