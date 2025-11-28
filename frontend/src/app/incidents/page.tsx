'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { PageLayout } from '@/components/layout/PageLayout'
import { IncidentTable } from '@/components/incidents/IncidentTable'
import { CreateIncidentModal } from '@/components/incidents/CreateIncidentModal'
import { IncidentFilters } from '@/components/incidents/IncidentFilters'
import { Button } from '@/components/ui/Button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'
import type { IncidentFilters as IIncidentFilters } from '@/types/incident'

export default function IncidentsPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [filters, setFilters] = useState<IIncidentFilters>({})

  const { data: incidents = [], isLoading, refetch } = useQuery({
    queryKey: [QUERY_KEYS.INCIDENTS, filters],
    queryFn: () => api.getIncidents(filters),
    refetchInterval: 15000,
  })

  return (
    <PageLayout
      title="Incidents"
      subtitle={`${incidents.length} total incidents`}
      actions={
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="h-4 w-4 mr-2" />
          Create Incident
        </Button>
      }
    >
      {/* Filters */}
      <div className="mb-6">
        <IncidentFilters filters={filters} onFiltersChange={setFilters} />
      </div>

      {/* Incidents Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading incidents..." />
        </div>
      ) : (
        <IncidentTable incidents={incidents} />
      )}

      {/* Create Modal */}
      <CreateIncidentModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSuccess={() => {
          refetch()
          setIsCreateModalOpen(false)
        }}
      />
    </PageLayout>
  )
}
