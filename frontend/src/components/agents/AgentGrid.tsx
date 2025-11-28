import Link from 'next/link'
import { Agent } from '@/types/agent'
import { Card, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { AGENT_DISPLAY_NAMES } from '@/types/agent'
import { cn } from '@/lib/utils'
import { Bot, Activity, CheckCircle, TrendingUp } from 'lucide-react'

interface AgentGridProps {
  agents: Agent[]
}

export function AgentGrid({ agents }: AgentGridProps) {
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {agents.map((agent) => (
        <Link key={agent.name} href={`/agents/${agent.name}`}>
          <Card variant="bordered" className="hover:shadow-lg transition-shadow h-full">
            <CardContent className="p-6">
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
                    <Bot className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {AGENT_DISPLAY_NAMES[agent.name] || agent.name}
                    </h3>
                    <p className="text-xs text-gray-500 font-mono">{agent.name}</p>
                  </div>
                </div>
                <Badge variant={getStatusVariant(agent.status)}>{agent.status}</Badge>
              </div>

              {/* Description */}
              {agent.description && (
                <p className="text-sm text-gray-600 mb-4">{agent.description}</p>
              )}

              {/* Metrics */}
              {agent.metrics && (
                <div className="space-y-3 mb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 flex items-center gap-1">
                      <CheckCircle className="h-4 w-4" />
                      Success Rate
                    </span>
                    <span className="font-semibold text-green-600">
                      {agent.metrics.success_rate.toFixed(1)}%
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 flex items-center gap-1">
                      <Activity className="h-4 w-4" />
                      Tasks (24h)
                    </span>
                    <span className="font-semibold text-gray-900">
                      {agent.metrics.tasks_last_24h}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 flex items-center gap-1">
                      <TrendingUp className="h-4 w-4" />
                      Total Tasks
                    </span>
                    <span className="font-semibold text-gray-900">
                      {agent.metrics.total_tasks}
                    </span>
                  </div>
                </div>
              )}

              {/* Health Status */}
              {agent.health_check && (
                <div className="pt-4 border-t border-gray-200">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div
                        className={cn(
                          'h-2 w-2 rounded-full',
                          agent.health_check.status === 'healthy' && 'bg-green-500',
                          agent.health_check.status === 'degraded' && 'bg-yellow-500',
                          agent.health_check.status === 'unhealthy' && 'bg-red-500'
                        )}
                      />
                      <span className="text-gray-600 capitalize">{agent.health_check.status}</span>
                    </div>
                    {agent.health_check.response_time_ms && (
                      <span className="text-gray-500">{agent.health_check.response_time_ms}ms</span>
                    )}
                  </div>
                </div>
              )}

              {/* Capabilities */}
              {agent.capabilities && agent.capabilities.length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <p className="text-xs text-gray-500 mb-2">Capabilities</p>
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 3).map((cap, idx) => (
                      <Badge key={idx} variant="default" className="text-xs">
                        {cap}
                      </Badge>
                    ))}
                    {agent.capabilities.length > 3 && (
                      <Badge variant="default" className="text-xs">
                        +{agent.capabilities.length - 3}
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  )
}
