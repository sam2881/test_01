'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ApprovalRequest } from '@/types/approval'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { Select } from '../ui/Select'
import { api } from '@/lib/api'
import { AGENT_DISPLAY_NAMES } from '@/types/agent'
import { CheckCircle, AlertCircle } from 'lucide-react'

interface RoutingApprovalProps {
  approval: ApprovalRequest
  onApprove: () => void
}

export function RoutingApproval({ approval, onApprove }: RoutingApprovalProps) {
  const [selectedAgent, setSelectedAgent] = useState(
    approval.routing_decision?.selected_agent || ''
  )
  const [overrideReason, setOverrideReason] = useState('')

  const isPending = approval.status === 'pending'
  const decision = approval.routing_decision!

  const approveMutation = useMutation({
    mutationFn: () =>
      api.approveRouting(approval.approval_id, {
        approved_by: 'Admin', // In production, get from auth context
        selected_agent: selectedAgent,
        override_reason: selectedAgent !== decision.selected_agent ? overrideReason : undefined,
      }),
    onSuccess: () => {
      toast.success('Routing approved successfully')
      onApprove()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to approve routing')
    },
  })

  const handleApprove = () => {
    if (selectedAgent !== decision.selected_agent && !overrideReason) {
      toast.error('Please provide a reason for overriding the suggested agent')
      return
    }
    approveMutation.mutate()
  }

  const agentOptions = [
    { value: decision.selected_agent, label: AGENT_DISPLAY_NAMES[decision.selected_agent] || decision.selected_agent },
    ...(decision.alternative_agents || []).map((alt) => ({
      value: alt.agent_name,
      label: `${AGENT_DISPLAY_NAMES[alt.agent_name] || alt.agent_name} (${(alt.confidence * 100).toFixed(1)}%)`,
    })),
  ]

  return (
    <div className="space-y-6">
      {/* AI Suggestion */}
      <Card variant="bordered">
        <CardHeader>
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-blue-600" />
            <CardTitle>AI Routing Suggestion</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-gray-500 mb-2">Suggested Agent</p>
            <div className="flex items-center gap-3">
              <Badge variant="info" className="text-base px-4 py-2">
                {AGENT_DISPLAY_NAMES[decision.selected_agent] || decision.selected_agent}
              </Badge>
              <span className="text-sm text-gray-600">
                {(decision.confidence * 100).toFixed(1)}% confidence
              </span>
            </div>
          </div>

          <div>
            <p className="text-sm text-gray-500 mb-2">Reasoning</p>
            <p className="text-gray-900">{decision.reasoning}</p>
          </div>

          {decision.alternative_agents && decision.alternative_agents.length > 0 && (
            <div>
              <p className="text-sm text-gray-500 mb-2">Alternative Agents</p>
              <div className="space-y-2">
                {decision.alternative_agents.map((alt) => (
                  <div
                    key={alt.agent_name}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <span className="font-medium">
                      {AGENT_DISPLAY_NAMES[alt.agent_name] || alt.agent_name}
                    </span>
                    <Badge variant="default">{(alt.confidence * 100).toFixed(1)}%</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Similar Incidents */}
      {decision.similar_incidents && decision.similar_incidents.length > 0 && (
        <Card variant="bordered">
          <CardHeader>
            <CardTitle>Similar Incidents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {decision.similar_incidents.map((incident) => (
                <div
                  key={incident.incident_id}
                  className="p-4 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-medium">{incident.incident_id}</p>
                      <p className="text-sm text-gray-600 mt-1">{incident.short_description}</p>
                    </div>
                    <Badge variant="info">{(incident.similarity_score * 100).toFixed(0)}% match</Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-2 text-sm">
                    <span className="text-gray-500">Assigned to:</span>
                    <Badge variant="default">{incident.assigned_agent}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Approval Section */}
      {isPending && (
        <Card variant="bordered">
          <CardHeader>
            <CardTitle>Approval Decision</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Select
              label="Select Agent"
              options={agentOptions}
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
            />

            {selectedAgent !== decision.selected_agent && (
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Override Reason *
                </label>
                <textarea
                  className="flex min-h-[100px] w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  placeholder="Explain why you're overriding the AI suggestion..."
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                />
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <Button
                onClick={handleApprove}
                isLoading={approveMutation.isPending}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Approve & Route
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
