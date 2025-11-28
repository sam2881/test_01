import Link from 'next/link'
import { Incident } from '@/types/incident'
import { Card, CardContent } from '../ui/Card'
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../ui/Table'
import { PriorityBadge, StatusBadge } from '../ui/StatusBadge'
import { formatRelativeTime } from '@/lib/utils'

interface IncidentTableProps {
  incidents: Incident[]
}

export function IncidentTable({ incidents }: IncidentTableProps) {
  if (incidents.length === 0) {
    return (
      <Card variant="bordered">
        <CardContent className="p-12 text-center text-gray-500">
          No incidents found
        </CardContent>
      </Card>
    )
  }

  return (
    <Card variant="bordered">
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Service</TableHead>
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
                <TableCell className="max-w-md">
                  <div className="truncate">{incident.short_description}</div>
                  {incident.affected_users && (
                    <div className="text-xs text-gray-500 mt-1">
                      {incident.affected_users} users affected
                    </div>
                  )}
                </TableCell>
                <TableCell>
                  <PriorityBadge priority={incident.priority} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={incident.status} />
                </TableCell>
                <TableCell className="text-sm text-gray-600">
                  {incident.category || '-'}
                </TableCell>
                <TableCell className="text-sm text-gray-600">
                  {incident.affected_service || '-'}
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
      </CardContent>
    </Card>
  )
}
