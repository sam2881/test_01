'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { PageLayout } from '@/components/layout/PageLayout'
import { AgentMetrics } from '@/components/agents/AgentMetrics'
import { AgentLogs } from '@/components/agents/AgentLogs'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'
import { AGENT_DISPLAY_NAMES } from '@/types/agent'

export default function AgentDetailPage() {
  const params = useParams()
  const agentName = params.name as string

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: [QUERY_KEYS.AGENT_METRICS, agentName],
    queryFn: () => api.getAgentMetrics(agentName),
    enabled: !!agentName,
    refetchInterval: 10000,
  })

  const { data: logs = [], isLoading: logsLoading } = useQuery({
    queryKey: [QUERY_KEYS.AGENT_LOGS, agentName],
    queryFn: () => api.getAgentLogs(agentName, 100),
    enabled: !!agentName,
    refetchInterval: 5000,
  })

  if (metricsLoading || logsLoading) {
    return (
      <PageLayout title="Agent Details">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading agent details..." />
        </div>
      </PageLayout>
    )
  }

  const displayName = AGENT_DISPLAY_NAMES[agentName] || agentName

  return (
    <PageLayout title={displayName} subtitle={`Agent: ${agentName}`}>
      <div className="space-y-6">
        {metrics && <AgentMetrics agentName={agentName} metrics={metrics} />}
        <AgentLogs logs={logs} />
      </div>
    </PageLayout>
  )
}
