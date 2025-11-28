import { ApprovalRequest } from '@/types/approval'
import { Card, CardContent } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { StatusBadge } from '../ui/StatusBadge'
import { formatRelativeTime } from '@/lib/utils'
import { Clock, GitBranch, FileCode } from 'lucide-react'

interface ApprovalCardProps {
  approval: ApprovalRequest
  onUpdate: () => void
  showActions?: boolean
}

export function ApprovalCard({ approval, onUpdate, showActions = true }: ApprovalCardProps) {
  const getTypeIcon = () => {
    if (approval.approval_type === 'routing_override') {
      return <GitBranch className="h-5 w-5" />
    }
    return <FileCode className="h-5 w-5" />
  }

  const getTypeLabel = () => {
    return approval.approval_type === 'routing_override'
      ? 'Routing Override'
      : 'Plan Approval'
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success'
      case 'rejected':
        return 'error'
      case 'timeout':
        return 'warning'
      default:
        return 'info'
    }
  }

  return (
    <Card variant="bordered" className="hover:shadow-md transition-shadow cursor-pointer">
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4 flex-1">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-600">
              {getTypeIcon()}
            </div>

            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <h4 className="font-semibold text-gray-900">{getTypeLabel()}</h4>
                <Badge variant={getStatusVariant(approval.status)}>
                  {approval.status}
                </Badge>
              </div>

              <div className="space-y-1 text-sm text-gray-600">
                <div className="flex items-center gap-2">
                  <span className="font-medium">ID:</span>
                  <span className="font-mono">{approval.approval_id}</span>
                </div>

                {approval.incident_id && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Incident:</span>
                    <span className="font-mono">{approval.incident_id}</span>
                  </div>
                )}

                {approval.routing_decision && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Suggested Agent:</span>
                    <Badge variant="info">{approval.routing_decision.selected_agent}</Badge>
                    <span className="text-xs">
                      ({(approval.routing_decision.confidence * 100).toFixed(1)}% confidence)
                    </span>
                  </div>
                )}

                {approval.execution_plan && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium">Risk Level:</span>
                    <Badge
                      variant={
                        approval.execution_plan.risk_level === 'Critical' || approval.execution_plan.risk_level === 'High'
                          ? 'error'
                          : approval.execution_plan.risk_level === 'Medium'
                          ? 'warning'
                          : 'success'
                      }
                    >
                      {approval.execution_plan.risk_level}
                    </Badge>
                  </div>
                )}

                <div className="flex items-center gap-2 text-xs">
                  <Clock className="h-3 w-3" />
                  <span>Created {formatRelativeTime(approval.created_at)}</span>
                  {approval.status === 'pending' && (
                    <>
                      <span>•</span>
                      <span className="text-orange-600 font-medium">
                        Timeout in {formatRelativeTime(approval.timeout_at)}
                      </span>
                    </>
                  )}
                </div>

                {approval.approved_by && (
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-medium">By:</span>
                    <span>{approval.approved_by}</span>
                    {approval.approved_at && (
                      <span className="text-gray-500">
                        @ {formatRelativeTime(approval.approved_at)}
                      </span>
                    )}
                  </div>
                )}

                {approval.rejection_reason && (
                  <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">
                    <span className="font-medium">Rejection reason:</span> {approval.rejection_reason}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
