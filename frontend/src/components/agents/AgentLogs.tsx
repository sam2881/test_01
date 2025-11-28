import { AgentLog } from '@/types/agent'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { formatRelativeTime } from '@/lib/utils'
import { AlertCircle, Info, AlertTriangle } from 'lucide-react'

interface AgentLogsProps {
  logs: AgentLog[]
}

export function AgentLogs({ logs }: AgentLogsProps) {
  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-600" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />
      default:
        return <Info className="h-4 w-4 text-blue-600" />
    }
  }

  const getLevelVariant = (level: string) => {
    switch (level) {
      case 'error':
        return 'error'
      case 'warning':
        return 'warning'
      default:
        return 'info'
    }
  }

  return (
    <Card variant="bordered">
      <CardHeader>
        <CardTitle>Recent Logs ({logs.length})</CardTitle>
      </CardHeader>
      <CardContent>
        {logs.length === 0 ? (
          <div className="text-center py-8 text-gray-500">No logs available</div>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto">
            {logs.map((log, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                <div className="mt-0.5">{getLevelIcon(log.level)}</div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={getLevelVariant(log.level)} className="text-xs">
                      {log.level}
                    </Badge>
                    <span className="text-xs text-gray-500">
                      {formatRelativeTime(log.timestamp)}
                    </span>
                    {log.task_id && (
                      <span className="text-xs text-gray-500 font-mono">
                        Task: {log.task_id}
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-gray-900">{log.message}</p>

                  {log.metadata && Object.keys(log.metadata).length > 0 && (
                    <div className="mt-2 p-2 bg-gray-100 rounded text-xs font-mono overflow-x-auto">
                      {JSON.stringify(log.metadata, null, 2)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
