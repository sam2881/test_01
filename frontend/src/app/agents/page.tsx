'use client'

import { useQuery } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { AgentGrid } from '@/components/agents/AgentGrid'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'

export default function AgentsPage() {
  const { data: agents = [], isLoading } = useQuery({
    queryKey: [QUERY_KEYS.AGENTS],
    queryFn: () => api.getAgents(),
    refetchInterval: 10000,
  })

  const activeCount = agents.filter((a: any) => a.status === 'active').length

  return (
    <PageLayout
      title="Agents"
      subtitle={`${activeCount}/${agents.length} agents active`}
    >
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading agents..." />
        </div>
      ) : (
        <AgentGrid agents={agents} />
      )}
    </PageLayout>
  )
}
