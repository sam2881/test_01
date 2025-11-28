'use client'

import { useState, useEffect } from 'react'
import { PageLayout } from '@/components/layout/PageLayout'
import { EventStream } from '@/components/events/EventStream'
import { EventFilter } from '@/components/events/EventFilter'
import { wsClient } from '@/lib/websocket'
import { WEBSOCKET_EVENTS } from '@/lib/constants'

interface Event {
  id: string
  type: string
  timestamp: string
  data: any
}

export default function EventsPage() {
  const [events, setEvents] = useState<Event[]>([])
  const [filters, setFilters] = useState({
    types: [] as string[],
    search: '',
  })

  useEffect(() => {
    // Subscribe to all WebSocket events
    const unsubscribers = Object.values(WEBSOCKET_EVENTS).map((eventType) =>
      wsClient.on(eventType, (data: any) => {
        const newEvent: Event = {
          id: `${eventType}-${Date.now()}-${Math.random()}`,
          type: eventType,
          timestamp: new Date().toISOString(),
          data,
        }
        setEvents((prev) => [newEvent, ...prev].slice(0, 100)) // Keep last 100 events
      })
    )

    return () => {
      unsubscribers.forEach((unsub) => unsub())
    }
  }, [])

  const filteredEvents = events.filter((event) => {
    if (filters.types.length > 0 && !filters.types.includes(event.type)) {
      return false
    }
    if (filters.search) {
      const searchLower = filters.search.toLowerCase()
      return (
        event.type.toLowerCase().includes(searchLower) ||
        JSON.stringify(event.data).toLowerCase().includes(searchLower)
      )
    }
    return true
  })

  return (
    <PageLayout
      title="Real-Time Events"
      subtitle={`${filteredEvents.length} events (${events.length} total)`}
    >
      <div className="space-y-6">
        <EventFilter filters={filters} onFiltersChange={setFilters} />
        <EventStream events={filteredEvents} />
      </div>
    </PageLayout>
  )
}
