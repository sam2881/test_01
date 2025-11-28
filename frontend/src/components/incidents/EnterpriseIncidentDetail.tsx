'use client'

import { useQuery } from '@tanstack/react-query'
import { RAGPanel, SimilarIncident } from './RAGPanel'
import { RemediationPanel } from './RemediationPanel'
import { Tabs } from '../ui/Tabs'
import { Badge } from '../ui/Badge'
import {
  Zap,
  FileText,
  Activity,
  Clock,
  AlertCircle
} from 'lucide-react'

interface EnterpriseIncidentDetailProps {
  incident: any
}

export function EnterpriseIncidentDetail({ incident }: EnterpriseIncidentDetailProps) {
  // Fetch workflow context (RAG + Graph DB)
  const { data: context, isLoading: contextLoading } = useQuery({
    queryKey: ['workflow-context', incident.incident_id || incident.number],
    queryFn: () =>
      fetch(
        `http://localhost:8000/api/workflow/${incident.incident_id || incident.number}/context`
      ).then((res) => res.json()),
    refetchInterval: 10000
  })

  // Extract RAG similar incidents from context
  const similarIncidents: SimilarIncident[] = context?.rag_context || []

  const tabs = [
    {
      id: 'remediation',
      label: 'AI Remediation',
      icon: <Zap className="w-4 h-4" />,
      content: (
        <RemediationPanel
          incidentId={incident.incident_id || incident.number}
          incidentDescription={incident.short_description}
        />
      )
    },
    {
      id: 'details',
      label: 'Incident Details',
      icon: <FileText className="w-4 h-4" />,
      content: (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Incident Information</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Incident ID</p>
                <p className="mt-1 font-medium">{incident.number || incident.incident_id}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Priority</p>
                <Badge
                  className={
                    incident.priority === '1'
                      ? 'bg-red-100 text-red-800'
                      : incident.priority === '2'
                      ? 'bg-orange-100 text-orange-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }
                >
                  {incident.priority === '1'
                    ? 'Critical'
                    : incident.priority === '2'
                    ? 'High'
                    : incident.priority === '3'
                    ? 'Medium'
                    : 'Low'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500">State</p>
                <Badge
                  className={
                    incident.state === '6'
                      ? 'bg-green-100 text-green-800'
                      : incident.state === '1'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-blue-100 text-blue-800'
                  }
                >
                  {incident.state === '6' ? 'Resolved' : incident.state === '1' ? 'New' : 'In Progress'}
                </Badge>
              </div>
              <div>
                <p className="text-sm text-gray-500">Category</p>
                <p className="mt-1 font-medium">{incident.category || 'N/A'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Created On</p>
                <p className="mt-1 font-medium">
                  {incident.created_on || incident.sys_created_on
                    ? new Date(incident.created_on || incident.sys_created_on).toLocaleString()
                    : 'N/A'}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Updated On</p>
                <p className="mt-1 font-medium">
                  {incident.updated_on || incident.sys_updated_on
                    ? new Date(incident.updated_on || incident.sys_updated_on).toLocaleString()
                    : 'N/A'}
                </p>
              </div>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Short Description</h4>
            <p className="text-gray-700">{incident.short_description}</p>
          </div>

          <div>
            <h4 className="text-sm font-semibold text-gray-900 mb-2">Full Description</h4>
            <div className="bg-gray-50 rounded-lg p-4">
              <p className="text-gray-700 whitespace-pre-wrap">{incident.description}</p>
            </div>
          </div>
        </div>
      )
    },
    {
      id: 'activity',
      label: 'Activity',
      icon: <Activity className="w-4 h-4" />,
      content: (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="space-y-4">
            <div className="flex gap-4 pb-4 border-b border-gray-200">
              <div className="flex-shrink-0">
                <Clock className="w-5 h-5 text-gray-400" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900">Incident Created</p>
                <p className="text-sm text-gray-600">
                  {incident.created_on || incident.sys_created_on
                    ? new Date(incident.created_on || incident.sys_created_on).toLocaleString()
                    : 'N/A'}
                </p>
              </div>
            </div>
            {incident.updated_on && incident.updated_on !== incident.created_on && (
              <div className="flex gap-4 pb-4 border-b border-gray-200">
                <div className="flex-shrink-0">
                  <AlertCircle className="w-5 h-5 text-blue-400" />
                </div>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">Last Updated</p>
                  <p className="text-sm text-gray-600">
                    {new Date(incident.updated_on).toLocaleString()}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )
    }
  ]

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Main Content - 2 columns */}
      <div className="lg:col-span-2 space-y-6">
        <Tabs tabs={tabs} defaultTab="remediation" />
      </div>

      {/* Right Sidebar - 1 column */}
      <div className="space-y-6">
        {/* RAG Panel - Similar Incidents */}
        <RAGPanel similarIncidents={similarIncidents} isLoading={contextLoading} />

        {/* Quick Info Card */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h4 className="font-medium text-gray-900 mb-3">Quick Actions</h4>
          <div className="space-y-2 text-sm">
            <p className="text-gray-600">
              <span className="font-medium">Tip:</span> Use the floating chat (bottom right) to ask questions about this incident.
            </p>
            <p className="text-gray-600">
              <span className="font-medium">AI Remediation:</span> Click "Start Analysis" in the AI Remediation tab to find matching runbooks.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
