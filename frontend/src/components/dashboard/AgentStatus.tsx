import { Agent } from '@/types/agent'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { cn, getAgentStatusColor } from '@/lib/utils'
import { AGENT_DISPLAY_NAMES } from '@/types/agent'
import Link from 'next/link'

interface AgentStatusProps {
  agents: Agent[]
}

export function AgentStatus({ agents }: AgentStatusProps) {
  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'success'
      case 'idle':
        return 'info'
      case 'error':
        return 'error'
      default:
        return 'default'
    }
  }

  return (
    <Card variant="bordered">
      <CardHeader>
        <CardTitle>Agent Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {agents.map((agent) => (
            <Link
              key={agent.name}
              href={`/agents/${agent.name}`}
              className="block p-4 border border-gray-200 rounded-lg hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="flex items-start justify-between mb-2">
                <h4 className="font-medium text-gray-900">{AGENT_DISPLAY_NAMES[agent.name] || agent.name}</h4>
                <Badge variant={getStatusVariant(agent.status)}>
                  {agent.status}
                </Badge>
              </div>

              {agent.metrics && (
                <div className="space-y-1 text-sm text-gray-600">
                  <div className="flex justify-between">
                    <span>Success Rate:</span>
                    <span className="font-medium">{agent.metrics.success_rate.toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Tasks (24h):</span>
                    <span className="font-medium">{agent.metrics.tasks_last_24h}</span>
                  </div>
                  {agent.metrics.average_response_time_ms && (
                    <div className="flex justify-between">
                      <span>Avg. Time:</span>
                      <span className="font-medium">{agent.metrics.average_response_time_ms}ms</span>
                    </div>
                  )}
                </div>
              )}

              {agent.health_check && (
                <div className="mt-2 pt-2 border-t border-gray-100">
                  <div className="flex items-center gap-2">
                    <div className={cn(
                      'h-2 w-2 rounded-full',
                      agent.health_check.status === 'healthy' && 'bg-green-500',
                      agent.health_check.status === 'degraded' && 'bg-yellow-500',
                      agent.health_check.status === 'unhealthy' && 'bg-red-500'
                    )} />
                    <span className="text-xs text-gray-500 capitalize">{agent.health_check.status}</span>
                  </div>
                </div>
              )}
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
