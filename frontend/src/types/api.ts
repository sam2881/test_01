export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TaskRequest {
  description: string
  priority?: 'P1' | 'P2' | 'P3' | 'P4'
  metadata?: Record<string, any>
}

export interface TaskResponse {
  task_id: string
  status: string
  message: string
}
