'use client'

import { useState } from 'react'
import { Card, CardContent } from '../ui/Card'
import { Select } from '../ui/Select'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { X } from 'lucide-react'
import type { IncidentFilters as IIncidentFilters } from '@/types/incident'
import { INCIDENT_PRIORITIES, INCIDENT_STATUSES } from '@/lib/constants'

interface IncidentFiltersProps {
  filters: IIncidentFilters
  onFiltersChange: (filters: IIncidentFilters) => void
}

export function IncidentFilters({ filters, onFiltersChange }: IncidentFiltersProps) {
  const [localFilters, setLocalFilters] = useState<IIncidentFilters>(filters)

  const handleApply = () => {
    onFiltersChange(localFilters)
  }

  const handleClear = () => {
    setLocalFilters({})
    onFiltersChange({})
  }

  const hasActiveFilters = Object.keys(localFilters).length > 0

  return (
    <Card variant="bordered">
      <CardContent className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Input
            label="Search"
            placeholder="Search incidents..."
            value={localFilters.search || ''}
            onChange={(e) =>
              setLocalFilters({ ...localFilters, search: e.target.value })
            }
          />

          <Select
            label="Priority"
            options={[
              { value: '', label: 'All Priorities' },
              ...INCIDENT_PRIORITIES.map((p) => ({ value: p, label: p })),
            ]}
            value={localFilters.priority?.[0] || ''}
            onChange={(e) =>
              setLocalFilters({
                ...localFilters,
                priority: e.target.value ? [e.target.value as any] : undefined,
              })
            }
          />

          <Select
            label="Status"
            options={[
              { value: '', label: 'All Statuses' },
              ...INCIDENT_STATUSES.map((s) => ({ value: s, label: s })),
            ]}
            value={localFilters.status?.[0] || ''}
            onChange={(e) =>
              setLocalFilters({
                ...localFilters,
                status: e.target.value ? [e.target.value as any] : undefined,
              })
            }
          />

          <div className="flex items-end gap-2">
            <Button onClick={handleApply} className="flex-1">
              Apply
            </Button>
            {hasActiveFilters && (
              <Button variant="outline" onClick={handleClear}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
