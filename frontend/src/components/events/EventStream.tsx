import { Card, CardContent } from '../ui/Card'
import { EventCard } from './EventCard'

interface Event {
  id: string
  type: string
  timestamp: string
  data: any
}

interface EventStreamProps {
  events: Event[]
}

export function EventStream({ events }: EventStreamProps) {
  if (events.length === 0) {
    return (
      <Card variant="bordered">
        <CardContent className="p-12 text-center text-gray-500">
          No events yet. Waiting for real-time updates...
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-3">
      {events.map((event) => (
        <EventCard key={event.id} event={event} />
      ))}
    </div>
  )
}
