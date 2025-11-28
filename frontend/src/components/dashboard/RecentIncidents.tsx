import { Incident } from '@/types/incident'
import { Card, CardHeader, CardTitle, CardContent } from '../ui/Card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../ui/Table'
import { PriorityBadge, StatusBadge } from '../ui/StatusBadge'
import { formatRelativeTime } from '@/lib/utils'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'

interface RecentIncidentsProps {
  incidents: Incident[]
}

export function RecentIncidents({ incidents }: RecentIncidentsProps) {
  return (
    <Card variant="bordered">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Recent Incidents</CardTitle>
        <Link
          href="/incidents"
          className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
        >
          View all <ArrowRight className="h-4 w-4" />
        </Link>
      </CardHeader>
      <CardContent>
        {incidents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No recent incidents
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Assigned To</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {incidents.map((incident) => (
                <TableRow key={incident.incident_id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/incidents/${incident.incident_id}`}
                      className="text-blue-600 hover:text-blue-700 hover:underline"
                    >
                      {incident.incident_id}
                    </Link>
                  </TableCell>
                  <TableCell className="max-w-md truncate">
                    {incident.short_description}
                  </TableCell>
                  <TableCell>
                    <PriorityBadge priority={incident.priority} />
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={incident.status} />
                  </TableCell>
                  <TableCell className="text-sm text-gray-500">
                    {formatRelativeTime(incident.created_at)}
                  </TableCell>
                  <TableCell>
                    {incident.assigned_to || (
                      <span className="text-gray-400 italic">Unassigned</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  )
}
