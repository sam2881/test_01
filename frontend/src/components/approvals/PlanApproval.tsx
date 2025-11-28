'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ApprovalRequest } from '@/types/approval'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { RiskBadge } from '../ui/StatusBadge'
import { api } from '@/lib/api'
import { CheckCircle, XCircle, AlertTriangle, Code, FileEdit, Clock } from 'lucide-react'

interface PlanApprovalProps {
  approval: ApprovalRequest
  onApprove: () => void
  onReject: () => void
}

export function PlanApproval({ approval, onApprove, onReject }: PlanApprovalProps) {
  const [rejectionReason, setRejectionReason] = useState('')
  const [modifications, setModifications] = useState('')

  const isPending = approval.status === 'pending'
  const plan = approval.execution_plan!

  const approveMutation = useMutation({
    mutationFn: () =>
      api.approvePlan(approval.approval_id, {
        approved_by: 'Admin', // In production, get from auth context
        modifications: modifications || undefined,
      }),
    onSuccess: () => {
      toast.success('Plan approved successfully')
      onApprove()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to approve plan')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: () =>
      api.rejectPlan(approval.approval_id, {
        rejected_by: 'Admin',
        rejection_reason: rejectionReason,
      }),
    onSuccess: () => {
      toast.success('Plan rejected')
      onReject()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to reject plan')
    },
  })

  const handleApprove = () => {
    approveMutation.mutate()
  }

  const handleReject = () => {
    if (!rejectionReason) {
      toast.error('Please provide a rejection reason')
      return
    }
    rejectMutation.mutate()
  }

  return (
    <div className="space-y-6">
      {/* Plan Overview */}
      <Card variant="bordered">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Execution Plan</CardTitle>
            <RiskBadge risk={plan.risk_level} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-gray-500 mb-2">Agent</p>
            <p className="font-medium">{plan.agent_name}</p>
          </div>

          {plan.estimated_duration && (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Clock className="h-4 w-4" />
              <span>Estimated duration: {plan.estimated_duration}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Execution Steps */}
      <Card variant="bordered">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Code className="h-5 w-5 text-blue-600" />
            <CardTitle>Execution Steps</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {plan.steps.map((step) => (
              <div
                key={step.step_number}
                className="flex gap-4 p-4 border border-gray-200 rounded-lg"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-blue-100 text-blue-600 font-semibold shrink-0">
                  {step.step_number}
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{step.action}</p>
                  <p className="text-sm text-gray-600 mt-1">{step.description}</p>
                  {step.estimated_time && (
                    <p className="text-xs text-gray-500 mt-2">
                      Est. time: {step.estimated_time}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Commands */}
      {plan.commands.length > 0 && (
        <Card variant="bordered">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <CardTitle>Commands to Execute</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {plan.commands.map((cmd, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-gray-900 text-gray-100 rounded-lg font-mono text-sm overflow-x-auto"
                >
                  {cmd}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Files to Edit */}
      {plan.files_to_edit.length > 0 && (
        <Card variant="bordered">
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileEdit className="h-5 w-5 text-purple-600" />
              <CardTitle>Files to Modify</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              {plan.files_to_edit.map((file, idx) => (
                <div
                  key={idx}
                  className="p-2 bg-gray-50 rounded text-sm font-mono text-gray-700"
                >
                  {file}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Rollback Plan */}
      {plan.rollback_plan && plan.rollback_plan.length > 0 && (
        <Card variant="bordered">
          <CardHeader>
            <CardTitle>Rollback Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {plan.rollback_plan.map((step, idx) => (
                <div key={idx} className="flex gap-2 text-sm">
                  <span className="font-medium text-gray-600">{idx + 1}.</span>
                  <span className="text-gray-900">{step}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approval Actions */}
      {isPending && (
        <Card variant="bordered">
          <CardHeader>
            <CardTitle>Approval Decision</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Modifications (Optional)
              </label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
                placeholder="Any modifications or notes..."
                value={modifications}
                onChange={(e) => setModifications(e.target.value)}
              />
            </div>

            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">
                Rejection Reason
              </label>
              <textarea
                className="flex min-h-[80px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-red-600"
                placeholder="Reason for rejecting this plan..."
                value={rejectionReason}
                onChange={(e) => setRejectionReason(e.target.value)}
              />
            </div>

            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="danger"
                onClick={handleReject}
                isLoading={rejectMutation.isPending}
              >
                <XCircle className="h-4 w-4 mr-2" />
                Reject Plan
              </Button>
              <Button
                onClick={handleApprove}
                isLoading={approveMutation.isPending}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Approve & Execute
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
