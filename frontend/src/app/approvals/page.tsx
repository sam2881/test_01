'use client'

import { useQuery } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { ApprovalList } from '@/components/approvals/ApprovalList'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'
import { CheckCircle, Clock, XCircle } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/Card'

export default function ApprovalsPage() {
  const { data: approvals = [], isLoading, refetch } = useQuery({
    queryKey: [QUERY_KEYS.APPROVALS],
    queryFn: () => api.getPendingApprovals(),
    refetchInterval: 5000, // Refetch every 5 seconds for critical approvals
  })

  const pendingCount = approvals.filter((a: any) => a.status === 'pending').length
  const approvedCount = approvals.filter((a: any) => a.status === 'approved').length
  const rejectedCount = approvals.filter((a: any) => a.status === 'rejected').length

  return (
    <PageLayout
      title="HITL Approvals"
      subtitle="Human-in-the-loop approval workflows"
    >
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <Card variant="bordered">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Pending</p>
                <p className="text-2xl font-semibold text-orange-600">{pendingCount}</p>
              </div>
              <Clock className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>

        <Card variant="bordered">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Approved</p>
                <p className="text-2xl font-semibold text-green-600">{approvedCount}</p>
              </div>
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card variant="bordered">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Rejected</p>
                <p className="text-2xl font-semibold text-red-600">{rejectedCount}</p>
              </div>
              <XCircle className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Approvals List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading approvals..." />
        </div>
      ) : (
        <ApprovalList approvals={approvals} onUpdate={refetch} />
      )}
    </PageLayout>
  )
}
