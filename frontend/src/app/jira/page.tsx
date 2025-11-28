'use client'

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { Card, CardContent } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Tabs } from '@/components/ui/Tabs'
import { api, QUERY_KEYS } from '@/lib/api'
import Link from 'next/link'
import {
  Code,
  GitPullRequest,
  Clock,
  User,
  Tag,
  ExternalLink,
  Play,
  CheckCircle,
  AlertCircle,
  FileCode,
  Bug,
  BookOpen
} from 'lucide-react'

interface JiraTicket {
  ticket_id: string
  jira_id: string
  summary: string
  description: string
  status: string
  priority: string
  issue_type: string
  assignee: { name: string; email: string } | null
  labels: string[]
  created: string
  url: string
}

interface ProcessResult {
  ticket_id: string
  status: string
  pr_url?: string
  pr_number?: number
  steps: Array<{ step: string; status: string }>
  error?: string
}

const priorityColors: Record<string, string> = {
  'Critical': 'bg-red-500',
  'High': 'bg-orange-500',
  'Medium': 'bg-yellow-500',
  'Low': 'bg-green-500',
}

const statusColors: Record<string, string> = {
  'To Do': 'bg-gray-500',
  'In Progress': 'bg-blue-500',
  'Done': 'bg-green-500',
}

export default function JiraPage() {
  const queryClient = useQueryClient()
  const [processingTicket, setProcessingTicket] = useState<string | null>(null)
  const [processResult, setProcessResult] = useState<ProcessResult | null>(null)

  const { data: ticketsData, isLoading } = useQuery({
    queryKey: [QUERY_KEYS.JIRA_TICKETS],
    queryFn: () => api.getJiraTickets(),
  })

  const { data: prsData } = useQuery({
    queryKey: ['github-prs'],
    queryFn: () => api.getGitHubPRs(),
  })

  const processTicketMutation = useMutation({
    mutationFn: (ticketId: string) => api.processJiraTicket(ticketId),
    onSuccess: (data) => {
      setProcessResult(data)
      setProcessingTicket(null)
      queryClient.invalidateQueries({ queryKey: ['github-prs'] })
    },
    onError: () => setProcessingTicket(null)
  })

  const handleProcess = (ticketId: string) => {
    setProcessingTicket(ticketId)
    setProcessResult(null)
    processTicketMutation.mutate(ticketId)
  }

  const tickets = ticketsData?.tickets || []
  const prs = prsData?.pull_requests || []
  const todoTickets = tickets.filter((t: JiraTicket) => t.status === 'To Do' || t.status === 'Open')
  const inProgress = tickets.filter((t: JiraTicket) => t.status === 'In Progress')
  const stories = tickets.filter((t: JiraTicket) => t.issue_type === 'Story')

  const tabs = [
    { id: 'all', label: `All (${tickets.length})`, content: <TicketList tickets={tickets} isLoading={isLoading} onProcess={handleProcess} processing={processingTicket} /> },
    { id: 'todo', label: `Ready (${todoTickets.length})`, content: <TicketList tickets={todoTickets} isLoading={isLoading} onProcess={handleProcess} processing={processingTicket} showProcess /> },
    { id: 'progress', label: `In Progress (${inProgress.length})`, content: <TicketList tickets={inProgress} isLoading={isLoading} onProcess={handleProcess} processing={processingTicket} /> },
    { id: 'stories', label: `Stories (${stories.length})`, content: <TicketList tickets={stories} isLoading={isLoading} onProcess={handleProcess} processing={processingTicket} showProcess /> },
    { id: 'prs', label: `PRs (${prs.length})`, content: <PRList prs={prs} /> },
  ]

  return (
    <PageLayout title="Jira Integration" subtitle="Manage tickets and automate code generation">
      {/* Process Result */}
      {processResult && (
        <Card className={`mb-6 ${processResult.status === 'completed' ? 'bg-green-900/20 border-green-700' : 'bg-red-900/20 border-red-700'}`}>
          <CardContent className="pt-4">
            <div className="flex items-start gap-4">
              {processResult.status === 'completed' ? (
                <CheckCircle className="h-6 w-6 text-green-500" />
              ) : (
                <AlertCircle className="h-6 w-6 text-red-500" />
              )}
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-white">
                  {processResult.status === 'completed' ? `Code Generated for ${processResult.ticket_id}` : `Failed: ${processResult.ticket_id}`}
                </h3>
                {processResult.pr_url && (
                  <a href={processResult.pr_url} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 flex items-center gap-2 mt-2">
                    <GitPullRequest className="h-4 w-4" />
                    View Pull Request #{processResult.pr_number}
                  </a>
                )}
                {processResult.steps && (
                  <div className="mt-3 space-y-1">
                    {processResult.steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-gray-400">
                        {step.status === 'done' ? <CheckCircle className="h-3 w-3 text-green-500" /> : <AlertCircle className="h-3 w-3 text-red-500" />}
                        <span className="capitalize">{step.step}</span>
                      </div>
                    ))}
                  </div>
                )}
                {processResult.error && <p className="text-red-400 text-sm mt-2">{processResult.error}</p>}
              </div>
              <Button variant="ghost" size="sm" onClick={() => setProcessResult(null)}>Dismiss</Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs tabs={tabs} defaultTab="all" />
    </PageLayout>
  )
}

function TicketList({ tickets, isLoading, onProcess, processing, showProcess = false }: {
  tickets: JiraTicket[]
  isLoading: boolean
  onProcess: (id: string) => void
  processing: string | null
  showProcess?: boolean
}) {
  if (isLoading) return <div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div>
  if (!tickets.length) return <Card className="bg-gray-800 border-gray-700"><CardContent className="py-12 text-center text-gray-400">No tickets found</CardContent></Card>

  return (
    <div className="space-y-4">
      {tickets.map((ticket) => (
        <Card key={ticket.ticket_id} className="bg-gray-800 border-gray-700 hover:border-gray-600">
          <CardContent className="pt-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-blue-400 font-mono text-sm">{ticket.ticket_id}</span>
                  <Badge className={statusColors[ticket.status] || 'bg-gray-500'}>{ticket.status}</Badge>
                  <Badge className={priorityColors[ticket.priority] || 'bg-gray-500'}>{ticket.priority}</Badge>
                  <span className="text-gray-400 text-xs flex items-center gap-1">
                    {ticket.issue_type === 'Story' ? <BookOpen className="h-3 w-3" /> : ticket.issue_type === 'Bug' ? <Bug className="h-3 w-3" /> : <FileCode className="h-3 w-3" />}
                    {ticket.issue_type}
                  </span>
                </div>
                <Link href={`/jira/${ticket.ticket_id}`}>
                  <h3 className="text-lg font-medium text-white hover:text-blue-400">{ticket.summary}</h3>
                </Link>
                <p className="text-gray-400 text-sm mt-2 line-clamp-2">{ticket.description?.slice(0, 150)}...</p>
                <div className="flex items-center gap-4 mt-3 text-sm text-gray-500">
                  {ticket.assignee && <span className="flex items-center gap-1"><User className="h-4 w-4" />{ticket.assignee.name}</span>}
                  <span className="flex items-center gap-1"><Clock className="h-4 w-4" />{new Date(ticket.created).toLocaleDateString()}</span>
                  {ticket.labels.length > 0 && <span className="flex items-center gap-1"><Tag className="h-4 w-4" />{ticket.labels.slice(0, 2).join(', ')}</span>}
                </div>
              </div>
              <div className="flex flex-col gap-2 ml-4">
                {(showProcess || ticket.status === 'To Do') && (
                  <Button onClick={() => onProcess(ticket.ticket_id)} disabled={processing === ticket.ticket_id} size="sm" className="bg-green-600 hover:bg-green-700">
                    {processing === ticket.ticket_id ? <><div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />Processing...</> : <><Play className="h-4 w-4 mr-2" />Generate Code</>}
                  </Button>
                )}
                <a href={ticket.url} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm" className="w-full"><ExternalLink className="h-4 w-4 mr-2" />Jira</Button>
                </a>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

function PRList({ prs }: { prs: any[] }) {
  if (!prs.length) return (
    <Card className="bg-gray-800 border-gray-700">
      <CardContent className="py-12 text-center">
        <GitPullRequest className="h-12 w-12 mx-auto text-gray-500 mb-4" />
        <p className="text-gray-400">No open pull requests</p>
      </CardContent>
    </Card>
  )

  return (
    <div className="space-y-4">
      {prs.map((pr) => (
        <Card key={pr.number} className="bg-gray-800 border-gray-700">
          <CardContent className="pt-4">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <GitPullRequest className="h-5 w-5 text-green-500" />
                  <span className="text-gray-400">#{pr.number}</span>
                  <Badge className="bg-green-600">{pr.state}</Badge>
                </div>
                <h3 className="text-lg font-medium text-white">{pr.title}</h3>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                  <span><User className="h-4 w-4 inline mr-1" />{pr.user}</span>
                  <span><Clock className="h-4 w-4 inline mr-1" />{new Date(pr.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <a href={pr.url} target="_blank" rel="noopener noreferrer">
                <Button variant="outline" size="sm"><ExternalLink className="h-4 w-4 mr-2" />View</Button>
              </a>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
