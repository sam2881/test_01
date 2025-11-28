import { Card, CardContent } from '../ui/Card'
import { Input } from '../ui/Input'
import { Button } from '../ui/Button'
import { X } from 'lucide-react'
import { WEBSOCKET_EVENTS } from '@/lib/constants'

interface EventFilterProps {
  filters: {
    types: string[]
    search: string
  }
  onFiltersChange: (filters: any) => void
}

export function EventFilter({ filters, onFiltersChange }: EventFilterProps) {
  const eventTypes = Object.values(WEBSOCKET_EVENTS)

  const toggleType = (type: string) => {
    const newTypes = filters.types.includes(type)
      ? filters.types.filter((t) => t !== type)
      : [...filters.types, type]
    onFiltersChange({ ...filters, types: newTypes })
  }

  const clearFilters = () => {
    onFiltersChange({ types: [], search: '' })
  }

  const hasActiveFilters = filters.types.length > 0 || filters.search

  return (
    <Card variant="bordered">
      <CardContent className="p-4">
        <div className="space-y-4">
          <div className="flex gap-2">
            <Input
              placeholder="Search events..."
              value={filters.search}
              onChange={(e) =>
                onFiltersChange({ ...filters, search: e.target.value })
              }
              className="flex-1"
            />
            {hasActiveFilters && (
              <Button variant="outline" onClick={clearFilters}>
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>

          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Event Types</p>
            <div className="flex flex-wrap gap-2">
              {eventTypes.map((type) => (
                <button
                  key={type}
                  onClick={() => toggleType(type)}
                  className={`px-3 py-1 text-sm rounded-full border transition-colors ${
                    filters.types.includes(type)
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-blue-600'
                  }`}
                >
                  {type.replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
