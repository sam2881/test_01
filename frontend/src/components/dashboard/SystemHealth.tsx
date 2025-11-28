import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { cn } from '@/lib/utils'
import { CheckCircle, AlertCircle, XCircle, Clock } from 'lucide-react'

interface Service {
  name: string
  status: 'healthy' | 'degraded' | 'down' | 'unknown'
  latency?: number
  message?: string
}

interface SystemHealthProps {
  services: Service[]
}

export function SystemHealth({ services }: SystemHealthProps) {
  // Ensure services is always an array
  const servicesList = Array.isArray(services) ? services : []

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-600" />
      case 'down':
        return <XCircle className="h-5 w-5 text-red-600" />
      default:
        return <Clock className="h-5 w-5 text-gray-600" />
    }
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'degraded':
        return 'warning'
      case 'down':
        return 'error'
      default:
        return 'default'
    }
  }

  const healthyCount = servicesList.filter((s) => s.status === 'healthy').length
  const totalCount = servicesList.length

  return (
    <Card variant="bordered">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>System Health</CardTitle>
          <div className="text-sm">
            <span className="font-semibold text-green-600">{healthyCount}</span>
            <span className="text-gray-500">/{totalCount} services healthy</span>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {servicesList.map((service) => (
            <div
              key={service.name}
              className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
            >
              <div className="flex items-center gap-3">
                {getStatusIcon(service.status)}
                <div>
                  <p className="font-medium text-gray-900">{service.name}</p>
                  {service.message && (
                    <p className="text-sm text-gray-500">{service.message}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-3">
                {service.latency && (
                  <span className="text-sm text-gray-600">{service.latency}ms</span>
                )}
                <Badge variant={getStatusVariant(service.status)}>
                  {service.status}
                </Badge>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
