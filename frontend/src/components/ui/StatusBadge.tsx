import { Badge } from './Badge'
import { cn, getStatusColor, getPriorityColor, getRiskLevelColor } from '@/lib/utils'

interface StatusBadgeProps {
  status: string
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge className={cn(getStatusColor(status), className)}>
      {status}
    </Badge>
  )
}

interface PriorityBadgeProps {
  priority: string
  className?: string
}

export function PriorityBadge({ priority, className }: PriorityBadgeProps) {
  return (
    <Badge className={cn(getPriorityColor(priority), className)}>
      {priority}
    </Badge>
  )
}

interface RiskBadgeProps {
  risk: string
  className?: string
}

export function RiskBadge({ risk, className }: RiskBadgeProps) {
  return (
    <Badge className={cn(getRiskLevelColor(risk), className)}>
      {risk}
    </Badge>
  )
}
