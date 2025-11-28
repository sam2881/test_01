import { AgentMetrics as IAgentMetrics } from '@/types/agent'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { CheckCircle, XCircle, Clock, Activity, TrendingUp } from 'lucide-react'

interface AgentMetricsProps {
  agentName: string
  metrics: IAgentMetrics
}

export function AgentMetrics({ agentName, metrics }: AgentMetricsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <Card variant="bordered">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Tasks</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">{metrics.total_tasks}</p>
            </div>
            <Activity className="h-8 w-8 text-blue-600" />
          </div>
        </CardContent>
      </Card>

      <Card variant="bordered">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Success Rate</p>
              <p className="text-2xl font-semibold text-green-600 mt-1">
                {metrics.success_rate.toFixed(1)}%
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {metrics.successful_tasks}/{metrics.total_tasks}
              </p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
        </CardContent>
      </Card>

      <Card variant="bordered">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Failed Tasks</p>
              <p className="text-2xl font-semibold text-red-600 mt-1">{metrics.failed_tasks}</p>
            </div>
            <XCircle className="h-8 w-8 text-red-600" />
          </div>
        </CardContent>
      </Card>

      <Card variant="bordered">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Avg Response Time</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {metrics.average_response_time_ms}ms
              </p>
            </div>
            <Clock className="h-8 w-8 text-purple-600" />
          </div>
        </CardContent>
      </Card>

      <Card variant="bordered">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Tasks (24h)</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">{metrics.tasks_last_24h}</p>
            </div>
            <TrendingUp className="h-8 w-8 text-blue-600" />
          </div>
        </CardContent>
      </Card>

      <Card variant="bordered">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Current Load</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {metrics.current_load}%
              </p>
            </div>
            <div className="relative h-8 w-8">
              <svg className="h-8 w-8 transform -rotate-90">
                <circle
                  cx="16"
                  cy="16"
                  r="14"
                  stroke="#e5e7eb"
                  strokeWidth="4"
                  fill="none"
                />
                <circle
                  cx="16"
                  cy="16"
                  r="14"
                  stroke="#3b82f6"
                  strokeWidth="4"
                  fill="none"
                  strokeDasharray={`${(metrics.current_load / 100) * 88} 88`}
                />
              </svg>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
