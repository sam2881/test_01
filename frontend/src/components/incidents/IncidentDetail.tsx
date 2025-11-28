import { Incident } from '@/types/incident'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { PriorityBadge, StatusBadge } from '../ui/StatusBadge'
import { Badge } from '../ui/Badge'
import { formatDate } from '@/lib/utils'
import { Tabs } from '../ui/Tabs'
import { Clock, User, AlertCircle, Sparkles, GitCompare } from 'lucide-react'

interface IncidentDetailProps {
  incident: Incident
}

export function IncidentDetail({ incident }: IncidentDetailProps) {
  const tabs = [
    {
      id: 'overview',
      label: 'Overview',
      content: (
        <div className="space-y-6">
          {/* Main Info */}
          <Card variant="bordered">
            <CardHeader>
              <CardTitle>Incident Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500">Priority</p>
                  <div className="mt-1">
                    <PriorityBadge priority={incident.priority} />
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Status</p>
                  <div className="mt-1">
                    <StatusBadge status={incident.status} />
                  </div>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Category</p>
                  <p className="mt-1 font-medium">{incident.category || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Affected Service</p>
                  <p className="mt-1 font-medium">{incident.affected_service || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Created At</p>
                  <p className="mt-1 font-medium">{formatDate(incident.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500">Assigned To</p>
                  <p className="mt-1 font-medium">{incident.assigned_to || 'Unassigned'}</p>
                </div>
              </div>

              {incident.affected_users && (
                <div>
                  <p className="text-sm text-gray-500">Affected Users</p>
                  <p className="mt-1 font-medium">{incident.affected_users.toLocaleString()}</p>
                </div>
              )}

              <div>
                <p className="text-sm text-gray-500">Description</p>
                <p className="mt-1 text-gray-900 whitespace-pre-wrap">{incident.description}</p>
              </div>
            </CardContent>
          </Card>

          {/* Resolution */}
          {incident.resolution && (
            <Card variant="bordered">
              <CardHeader>
                <CardTitle>Resolution</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-900 whitespace-pre-wrap">{incident.resolution}</p>
                {incident.resolved_at && (
                  <p className="mt-4 text-sm text-gray-500">
                    Resolved at: {formatDate(incident.resolved_at)}
                  </p>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      ),
    },
    {
      id: 'ai-analysis',
      label: 'AI Analysis',
      content: (
        <div className="space-y-6">
          {incident.ai_analysis ? (
            <Card variant="bordered">
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-purple-600" />
                  <CardTitle>AI-Generated Analysis</CardTitle>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500">Suggested Agent</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant="info">{incident.ai_analysis.suggested_agent}</Badge>
                    <span className="text-sm text-gray-600">
                      ({(incident.ai_analysis.confidence * 100).toFixed(1)}% confidence)
                    </span>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-gray-500">Reasoning</p>
                  <p className="mt-1 text-gray-900">{incident.ai_analysis.reasoning}</p>
                </div>

                {incident.ai_analysis.estimated_resolution_time && (
                  <div>
                    <p className="text-sm text-gray-500">Estimated Resolution Time</p>
                    <p className="mt-1 font-medium">{incident.ai_analysis.estimated_resolution_time}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          ) : (
            <Card variant="bordered">
              <CardContent className="p-12 text-center text-gray-500">
                No AI analysis available yet
              </CardContent>
            </Card>
          )}
        </div>
      ),
    },
    {
      id: 'similar',
      label: 'Similar Incidents',
      content: (
        <div>
          {incident.similar_incidents && incident.similar_incidents.length > 0 ? (
            <div className="space-y-3">
              {incident.similar_incidents.map((similar) => (
                <Card key={similar.incident_id} variant="bordered">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          {similar.incident_id}
                        </p>
                        <p className="mt-1 text-sm text-gray-600">
                          {similar.short_description}
                        </p>
                        {similar.resolution && (
                          <p className="mt-2 text-sm text-gray-500">
                            <span className="font-medium">Resolution:</span> {similar.resolution}
                          </p>
                        )}
                      </div>
                      <Badge variant="info">
                        {(similar.similarity_score * 100).toFixed(0)}% match
                      </Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card variant="bordered">
              <CardContent className="p-12 text-center text-gray-500">
                No similar incidents found
              </CardContent>
            </Card>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <Tabs tabs={tabs} defaultTab="overview" />
    </div>
  )
}
