import { Card, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { formatRelativeTime } from '@/lib/utils'
import { Activity, AlertCircle, CheckCircle, GitBranch, FileCode, Bot } from 'lucide-react'

interface EventCardProps {
  event: {
    id: string
    type: string
    timestamp: string
    data: any
  }
}

export function EventCard({ event }: EventCardProps) {
  const getEventIcon = (type: string) => {
    if (type.includes('incident')) return <AlertCircle className="h-5 w-5" />
    if (type.includes('approval')) return <CheckCircle className="h-5 w-5" />
    if (type.includes('agent')) return <Bot className="h-5 w-5" />
    if (type.includes('ticket')) return <FileCode className="h-5 w-5" />
    return <Activity className="h-5 w-5" />
  }

  const getEventColor = (type: string) => {
    if (type.includes('incident')) return 'text-red-600 bg-red-100'
    if (type.includes('approval')) return 'text-green-600 bg-green-100'
    if (type.includes('agent')) return 'text-blue-600 bg-blue-100'
    if (type.includes('ticket')) return 'text-purple-600 bg-purple-100'
    return 'text-gray-600 bg-gray-100'
  }

  return (
    <Card variant="bordered" className="hover:shadow-sm transition-shadow">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${getEventColor(event.type)}`}>
            {getEventIcon(event.type)}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Badge variant="default">{event.type}</Badge>
              <span className="text-xs text-gray-500">{formatRelativeTime(event.timestamp)}</span>
            </div>

            <div className="text-sm text-gray-900 mb-2">
              {event.data.message || event.data.description || 'Event triggered'}
            </div>

            <details className="mt-2">
              <summary className="cursor-pointer text-xs text-gray-500 hover:text-gray-700">
                View details
              </summary>
              <div className="mt-2 p-3 bg-gray-50 rounded text-xs font-mono overflow-x-auto">
                <pre>{JSON.stringify(event.data, null, 2)}</pre>
              </div>
            </details>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
