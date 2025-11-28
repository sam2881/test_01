'use client'

import { useQuery } from '@tanstack/react-query'
import { AlertCircle, Bot, CheckCircle, TrendingUp } from 'lucide-react'
import { PageLayout } from '@/components/layout/PageLayout'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { AgentStatus } from '@/components/dashboard/AgentStatus'
import { RecentIncidents } from '@/components/dashboard/RecentIncidents'
import { ActivityChart } from '@/components/dashboard/ActivityChart'
import { SystemHealth } from '@/components/dashboard/SystemHealth'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { api } from '@/lib/api'
import { QUERY_KEYS } from '@/lib/constants'

export default function DashboardPage() {
  // Fetch dashboard stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: [QUERY_KEYS.STATS],
    queryFn: () => api.getDashboardStats(),
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  // Fetch agents status
  const { data: agents = [], isLoading: agentsLoading } = useQuery({
    queryKey: [QUERY_KEYS.AGENTS],
    queryFn: () => api.getAgents(),
    refetchInterval: 10000, // Refetch every 10 seconds
  })

  // Fetch recent incidents
  const { data: incidents = [], isLoading: incidentsLoading } = useQuery({
    queryKey: [QUERY_KEYS.INCIDENTS],
    queryFn: () => api.getIncidents({ limit: 10 }),
    refetchInterval: 15000, // Refetch every 15 seconds
  })

  // Fetch activity data
  const { data: activityData = [], isLoading: activityLoading } = useQuery({
    queryKey: ['activity'],
    queryFn: () => api.getActivityData(24),
    refetchInterval: 60000, // Refetch every minute
  })

  // Fetch system health
  const { data: systemHealth = [], isLoading: healthLoading } = useQuery({
    queryKey: ['system-health'],
    queryFn: () => api.getSystemHealth(),
    refetchInterval: 30000, // Refetch every 30 seconds
  })

  if (statsLoading || agentsLoading || incidentsLoading) {
    return (
      <PageLayout title="Dashboard">
        <div className="flex items-center justify-center h-96">
          <LoadingSpinner size="lg" text="Loading dashboard..." />
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout title="Dashboard" subtitle="Real-time system overview">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <StatsCard
          title="Active Incidents"
          value={stats?.active_incidents || 0}
          icon={AlertCircle}
          description="Currently unresolved"
          color="red"
          trend={stats?.incidents_trend}
        />
        <StatsCard
          title="Agents Running"
          value={`${agents.filter((a: any) => a.status === 'active').length}/${agents.length}`}
          icon={Bot}
          description="Healthy agents"
          color="green"
        />
        <StatsCard
          title="Pending Approvals"
          value={stats?.pending_approvals || 0}
          icon={CheckCircle}
          description="Awaiting human review"
          color="yellow"
        />
        <StatsCard
          title="Success Rate"
          value={`${stats?.success_rate || 0}%`}
          icon={TrendingUp}
          description="Last 7 days"
          color="blue"
          trend={stats?.success_rate_trend}
        />
      </div>

      {/* Agent Status Grid */}
      <div className="mb-6">
        <AgentStatus agents={agents} />
      </div>

      {/* Charts and Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ActivityChart data={activityData} />
        <SystemHealth services={systemHealth} />
      </div>

      {/* Recent Incidents Table */}
      <div>
        <RecentIncidents incidents={incidents} />
      </div>
    </PageLayout>
  )
}
