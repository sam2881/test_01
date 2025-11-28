import Link from 'next/link'
import { ApprovalRequest } from '@/types/approval'
import { Card, CardContent } from '../ui/Card'
import { ApprovalCard } from './ApprovalCard'

interface ApprovalListProps {
  approvals: ApprovalRequest[]
  onUpdate: () => void
}

export function ApprovalList({ approvals, onUpdate }: ApprovalListProps) {
  if (approvals.length === 0) {
    return (
      <Card variant="bordered">
        <CardContent className="p-12 text-center text-gray-500">
          No pending approvals
        </CardContent>
      </Card>
    )
  }

  const pendingApprovals = approvals.filter((a) => a.status === 'pending')
  const completedApprovals = approvals.filter((a) => a.status !== 'pending')

  return (
    <div className="space-y-6">
      {/* Pending Approvals */}
      {pendingApprovals.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Pending Approvals ({pendingApprovals.length})
          </h3>
          <div className="space-y-4">
            {pendingApprovals.map((approval) => (
              <Link key={approval.approval_id} href={`/approvals/${approval.approval_id}`}>
                <ApprovalCard approval={approval} onUpdate={onUpdate} showActions={false} />
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Completed Approvals */}
      {completedApprovals.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recent History ({completedApprovals.length})
          </h3>
          <div className="space-y-4">
            {completedApprovals.map((approval) => (
              <Link key={approval.approval_id} href={`/approvals/${approval.approval_id}`}>
                <ApprovalCard approval={approval} onUpdate={onUpdate} showActions={false} />
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
