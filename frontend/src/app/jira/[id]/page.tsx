'use client'

import { useState } from 'react'
import { useParams } from 'next/navigation'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { PageLayout } from '@/components/layout/PageLayout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { api, QUERY_KEYS } from '@/lib/api'
import Link from 'next/link'
import {
  Code, GitPullRequest, Clock, User, Tag, ExternalLink, Play,
  CheckCircle, AlertCircle, FileCode, ArrowLeft, BookOpen, Bug, FileText, GitBranch
} from 'lucide-react'

interface JiraTicket {
  ticket_id: string
  summary: string
  description: string
  status: string
  priority: string
  issue_type: string
  assignee: { name: string } | null
  reporter: { name: string } | null
  labels: string[]
  created: string
  updated: string
  url: string
}

interface ProcessResult {
  ticket_id: string
  status: string
  pr_url?: string
  pr_number?: number
  steps: Array<{ step: string; status: string; branch?: string; file?: string; chars?: number }>
  error?: string
}

const statusColors: Record<string, string> = { 'To Do': 'bg-gray-500', 'In Progress': 'bg-blue-500', 'Done': 'bg-green-500' }
const priorityColors: Record<string, string> = { 'Critical': 'bg-red-500', 'High': 'bg-orange-500', 'Medium': 'bg-yellow-500', 'Low': 'bg-green-500' }

export default function JiraTicketDetailPage() {
  const params = useParams()
  const ticketId = params.id as string
  const queryClient = useQueryClient()
  const [isProcessing, setIsProcessing] = useState(false)
  const [processResult, setProcessResult] = useState<ProcessResult | null>(null)

  const { data: ticket, isLoading } = useQuery<JiraTicket>({
    queryKey: [QUERY_KEYS.JIRA_TICKETS, ticketId],
    queryFn: () => api.getJiraTicket(ticketId),
    enabled: !!ticketId,
  })

  const processTicketMutation = useMutation({
    mutationFn: () => api.processJiraTicket(ticketId),
    onSuccess: (data) => { setProcessResult(data); setIsProcessing(false); queryClient.invalidateQueries({ queryKey: ['github-prs'] }) },
    onError: (error: any) => { setIsProcessing(false); setProcessResult({ ticket_id: ticketId, status: 'failed', error: error.message, steps: [] }) }
  })

  const handleProcess = () => { setIsProcessing(true); setProcessResult(null); processTicketMutation.mutate() }

  if (isLoading) return <PageLayout title="Loading..."><div className="flex justify-center py-12"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full" /></div></PageLayout>

  if (!ticket) return (
    <PageLayout title="Not Found">
      <Card className="bg-gray-800 border-gray-700">
        <CardContent className="py-12 text-center">
          <AlertCircle className="h-12 w-12 mx-auto text-red-500 mb-4" />
          <p className="text-gray-400">Ticket {ticketId} not found</p>
          <Link href="/jira"><Button className="mt-4 border-gray-500 bg-transparent text-gray-300"><ArrowLeft className="h-4 w-4 mr-2" />Back</Button></Link>
        </CardContent>
      </Card>
    </PageLayout>
  )

  const Icon = ticket.issue_type === 'Story' ? BookOpen : ticket.issue_type === 'Bug' ? Bug : FileCode

  return (
    <PageLayout title={ticket.ticket_id} subtitle={ticket.summary}>
      <Link href="/jira"><Button variant="ghost" size="sm" className="mb-4"><ArrowLeft className="h-4 w-4 mr-2" />Back</Button></Link>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <Card className="bg-gray-800 border-gray-700">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/20 rounded-lg"><Icon className="h-5 w-5" /></div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400 font-mono">{ticket.ticket_id}</span>
                      <Badge className={statusColors[ticket.status] || 'bg-gray-500'}>{ticket.status}</Badge>
                    </div>
                    <span className="text-sm text-gray-500">{ticket.issue_type}</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={priorityColors[ticket.priority] || 'bg-gray-500'}>{ticket.priority}</Badge>
                  <a href={ticket.url} target="_blank" rel="noopener noreferrer"><Button className="border-gray-500 bg-transparent text-gray-300" size="sm"><ExternalLink className="h-4 w-4 mr-2" />Jira</Button></a>
                </div>
              </div>
              <h1 className="text-2xl font-bold text-white mb-4">{ticket.summary}</h1>
              <Button onClick={handleProcess} disabled={isProcessing} className="bg-green-600 hover:bg-green-700">
                {isProcessing ? <><div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full mr-2" />Processing...</> : <><Play className="h-4 w-4 mr-2" />Generate Code & Create PR</>}
              </Button>
            </CardContent>
          </Card>

          {/* Result */}
          {processResult && (
            <Card className={processResult.status === 'completed' ? 'bg-green-900/20 border-green-700' : 'bg-red-900/20 border-red-700'}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {processResult.status === 'completed' ? <><CheckCircle className="h-5 w-5 text-green-500" /><span className="text-green-400">Complete</span></> : <><AlertCircle className="h-5 w-5 text-red-500" /><span className="text-red-400">Failed</span></>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 mb-4">
                  {processResult.steps.map((step, i) => (
                    <div key={i} className="flex items-center gap-2 p-2 bg-gray-800/50 rounded">
                      {step.status === 'done' ? <CheckCircle className="h-4 w-4 text-green-500" /> : <AlertCircle className="h-4 w-4 text-red-500" />}
                      <span className="text-white capitalize">{step.step}</span>
                      {step.branch && <span className="text-gray-400 text-sm"><GitBranch className="h-3 w-3 inline mr-1" />{step.branch}</span>}
                      {step.file && <span className="text-gray-400 text-sm"><FileText className="h-3 w-3 inline mr-1" />{step.file}</span>}
                    </div>
                  ))}
                </div>
                {processResult.pr_url && (
                  <div className="p-4 bg-green-900/30 rounded border border-green-700 flex items-center justify-between">
                    <div className="flex items-center gap-3"><GitPullRequest className="h-6 w-6 text-green-500" /><span className="text-white">PR #{processResult.pr_number}</span></div>
                    <a href={processResult.pr_url} target="_blank" rel="noopener noreferrer"><Button className="bg-green-600"><ExternalLink className="h-4 w-4 mr-2" />View PR</Button></a>
                  </div>
                )}
                {processResult.error && <p className="text-red-400 p-4 bg-red-900/30 rounded">{processResult.error}</p>}
              </CardContent>
            </Card>
          )}

          {/* Description */}
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader><CardTitle><FileText className="h-5 w-5 inline mr-2" />Description</CardTitle></CardHeader>
            <CardContent><pre className="whitespace-pre-wrap text-gray-300 text-sm">{ticket.description || 'No description'}</pre></CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="bg-gray-800 border-gray-700">
            <CardHeader><CardTitle className="text-sm text-gray-400">Details</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div><p className="text-xs text-gray-500 mb-1">Status</p><Badge className={statusColors[ticket.status] || 'bg-gray-500'}>{ticket.status}</Badge></div>
              <div><p className="text-xs text-gray-500 mb-1">Priority</p><Badge className={priorityColors[ticket.priority] || 'bg-gray-500'}>{ticket.priority}</Badge></div>
              <div><p className="text-xs text-gray-500 mb-1">Type</p><span className="text-gray-300 flex items-center gap-2"><Icon className="h-4 w-4" />{ticket.issue_type}</span></div>
              {ticket.assignee && <div><p className="text-xs text-gray-500 mb-1">Assignee</p><span className="text-gray-300 flex items-center gap-2"><User className="h-4 w-4" />{ticket.assignee.name}</span></div>}
              <div><p className="text-xs text-gray-500 mb-1">Created</p><span className="text-gray-300 flex items-center gap-2"><Clock className="h-4 w-4" />{new Date(ticket.created).toLocaleDateString()}</span></div>
            </CardContent>
          </Card>

          {ticket.labels.length > 0 && (
            <Card className="bg-gray-800 border-gray-700">
              <CardHeader><CardTitle className="text-sm text-gray-400"><Tag className="h-4 w-4 inline mr-2" />Labels</CardTitle></CardHeader>
              <CardContent><div className="flex flex-wrap gap-2">{ticket.labels.map(l => <Badge key={l} className="border-gray-500 bg-transparent text-gray-300">{l}</Badge>)}</div></CardContent>
            </Card>
          )}

          <Card className="bg-gray-800 border-gray-700">
            <CardHeader><CardTitle className="text-sm text-gray-400"><Code className="h-4 w-4 inline mr-2" />Code Agent</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-gray-400">
                <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500" />Analyze requirements</li>
                <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500" />Read GitHub source</li>
                <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500" />Generate code with LLM</li>
                <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500" />Create pull request</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </PageLayout>
  )
}
