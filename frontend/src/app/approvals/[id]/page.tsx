'use client'

import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { PageLayout } from '@/components/layout/PageLayout'
import { ApprovalDetail } from '@/components/approvals/ApprovalDetail'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'

export default function ApprovalDetailPage() {
  const params = useParams()
  const approvalId = params.id as string

  const { data: approval, isLoading, refetch } = useQuery({
    queryKey: [QUERY_KEYS.APPROVAL, approvalId],
    queryFn: () => api.getApprovalById(approvalId),
    enabled: !!approvalId,
    refetchInterval: 3000, // Refetch frequently for real-time updates
  })

  if (isLoading) {
    return (
      <PageLayout title="Approval Details">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading approval..." />
        </div>
      </PageLayout>
    )
  }

  if (!approval) {
    return (
      <PageLayout title="Approval Not Found">
        <div className="text-center py-12">
          <p className="text-gray-500">Approval {approvalId} not found</p>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout
      title={`Approval ${approval.approval_id}`}
      subtitle={`${approval.approval_type === 'routing_override' ? 'Routing Override' : 'Plan Approval'}`}
    >
      <ApprovalDetail approval={approval} onUpdate={refetch} />
    </PageLayout>
  )
}
