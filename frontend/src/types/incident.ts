export type IncidentPriority = 'P1' | 'P2' | 'P3' | 'P4'
export type IncidentStatus = 'New' | 'In Progress' | 'Resolved' | 'Closed'

export interface Incident {
  incident_id: string
  short_description: string
  description: string
  priority: IncidentPriority
  status: IncidentStatus
  category?: string
  assigned_to?: string
  created_at: string
  updated_at?: string
  resolved_at?: string
  affected_service?: string
  affected_users?: number
  resolution?: string
  similar_incidents?: SimilarIncident[]
  ai_analysis?: {
    confidence: number
    suggested_agent: string
    reasoning: string
    estimated_resolution_time?: string
  }
}

export interface SimilarIncident {
  incident_id: string
  short_description: string
  similarity_score: number
  resolution?: string
}

export interface IncidentFilters {
  priority?: IncidentPriority[]
  status?: IncidentStatus[]
  category?: string[]
  search?: string
  date_from?: string
  date_to?: string
}

export interface CreateIncidentRequest {
  short_description: string
  description: string
  priority?: IncidentPriority
  category?: string
  affected_service?: string
}
