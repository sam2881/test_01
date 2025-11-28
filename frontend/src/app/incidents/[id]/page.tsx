'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams } from 'next/navigation'
import { PageLayout } from '@/components/layout/PageLayout'
import { EnterpriseIncidentDetail } from '@/components/incidents/EnterpriseIncidentDetail'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'
import { useChatContext } from '@/contexts/ChatContext'

export default function IncidentDetailPage() {
  const params = useParams()
  const incidentId = params.id as string
  const { setCurrentIncident } = useChatContext()

  const { data: incident, isLoading } = useQuery({
    queryKey: [QUERY_KEYS.INCIDENT, incidentId],
    queryFn: () => api.getIncidentById(incidentId),
    enabled: !!incidentId,
  })

  // Set current incident in chat context when incident data loads
  useEffect(() => {
    if (incident) {
      setCurrentIncident({
        incident_id: incident.incident_id,
        short_description: incident.short_description,
        description: incident.description,
        category: incident.category,
        priority: incident.priority,
        state: incident.status,
      })
    }

    // Clear when leaving the page
    return () => {
      setCurrentIncident(null)
    }
  }, [incident, setCurrentIncident])

  if (isLoading) {
    return (
      <PageLayout title="Incident Details">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading incident..." />
        </div>
      </PageLayout>
    )
  }

  if (!incident) {
    return (
      <PageLayout title="Incident Not Found">
        <div className="text-center py-12">
          <p className="text-gray-500">Incident {incidentId} not found</p>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout
      title={`Incident ${incident.incident_id}`}
      subtitle={incident.short_description}
    >
      <EnterpriseIncidentDetail incident={incident} />
    </PageLayout>
  )
}
