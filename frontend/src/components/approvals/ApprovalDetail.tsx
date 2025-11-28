import { ApprovalRequest } from '@/types/approval'
import { RoutingApproval } from './RoutingApproval'
import { PlanApproval } from './PlanApproval'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { StatusBadge } from '../ui/StatusBadge'
import { formatDate } from '@/lib/utils'

interface ApprovalDetailProps {
  approval: ApprovalRequest
  onUpdate: () => void
}

export function ApprovalDetail({ approval, onUpdate }: ApprovalDetailProps) {
  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <Card variant="bordered">
        <CardHeader>
          <CardTitle>Approval Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Status</p>
              <div className="mt-1">
                <StatusBadge status={approval.status} />
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500">Type</p>
              <p className="mt-1 font-medium capitalize">
                {approval.approval_type.replace('_', ' ')}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Created At</p>
              <p className="mt-1 font-medium">{formatDate(approval.created_at)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Timeout At</p>
              <p className="mt-1 font-medium">{formatDate(approval.timeout_at)}</p>
            </div>
            {approval.incident_id && (
              <div>
                <p className="text-sm text-gray-500">Related Incident</p>
                <p className="mt-1 font-medium font-mono">{approval.incident_id}</p>
              </div>
            )}
            {approval.approved_by && (
              <div>
                <p className="text-sm text-gray-500">Approved By</p>
                <p className="mt-1 font-medium">{approval.approved_by}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Type-Specific Content */}
      {approval.approval_type === 'routing_override' && approval.routing_decision && (
        <RoutingApproval
          approval={approval}
          onApprove={onUpdate}
        />
      )}

      {approval.approval_type === 'plan_approval' && approval.execution_plan && (
        <PlanApproval
          approval={approval}
          onApprove={onUpdate}
          onReject={onUpdate}
        />
      )}
    </div>
  )
}
