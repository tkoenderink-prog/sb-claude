import axios from 'axios'

// API base URL - uses environment variable for Tailscale/remote access
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface HealthResponse {
  status: string
  version: string
  service: string
}

export interface CalendarStatus {
  available: boolean
  version: string
  generated_at: string
  timezone: string
  calendars: string[]
  event_count: number
}

export interface TasksStatus {
  available: boolean
  last_updated: string
  task_count: number
  stats: {
    total_tasks: number
    by_status: Record<string, number>
    by_priority: Record<string, number>
    with_due_date: number
    overdue: number
  }
}

export interface SkillsStats {
  total_skills: number
  by_source: Record<string, number>
  with_checklist: number
  skill_roots: string[]
}

export interface SystemStatus {
  health: HealthResponse
  calendar: CalendarStatus | null
  tasks: TasksStatus | null
  skills: SkillsStats | null
}

export interface JobRun {
  id: string
  type: 'processor' | 'index' | 'agent' | 'chat'
  status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'
  started_at: string
  ended_at?: string
  command: string
  args?: Record<string, any>
  artifacts?: any[]
  metrics?: Record<string, any>
}

export interface RunJobRequest {
  type: string
  command: string
  args?: Record<string, any>
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await api.get<HealthResponse>('/health')
  return response.data
}

export async function getCalendarStatus(): Promise<CalendarStatus> {
  const response = await api.get<CalendarStatus>('/calendar/status')
  return response.data
}

export async function getTasksStatus(): Promise<TasksStatus> {
  const response = await api.get<TasksStatus>('/tasks/status')
  return response.data
}

export async function getSkillsStats(): Promise<SkillsStats> {
  const response = await api.get<SkillsStats>('/skills/stats')
  return response.data
}

export async function getJobs(): Promise<JobRun[]> {
  const response = await api.get<JobRun[]>('/jobs')
  return response.data
}

export async function runJob(request: RunJobRequest): Promise<JobRun> {
  const response = await api.post<JobRun>('/jobs/run', request)
  return response.data
}

// SSE Types
export interface JobLogEvent {
  type: 'log'
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  timestamp: string
}

export interface JobStatusEvent {
  status: 'started' | 'completed' | 'failed'
  job_id: string
}

export type SSEEvent =
  | { event: 'log'; data: JobLogEvent }
  | { event: 'status'; data: JobStatusEvent }
  | { event: 'error'; data: { message: string } }

// SSE Stream helper
export function streamJobLogs(
  jobId: string,
  onLog: (log: JobLogEvent) => void,
  onStatus: (status: JobStatusEvent) => void,
  onError: (error: Error) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE}/jobs/${jobId}/stream`)

  eventSource.addEventListener('log', (event) => {
    try {
      const data = JSON.parse(event.data) as JobLogEvent
      onLog(data)
    } catch (e) {
      console.error('Failed to parse log event:', e)
    }
  })

  eventSource.addEventListener('status', (event) => {
    try {
      const data = JSON.parse(event.data) as JobStatusEvent
      onStatus(data)
      if (data.status === 'completed' || data.status === 'failed') {
        eventSource.close()
      }
    } catch (e) {
      console.error('Failed to parse status event:', e)
    }
  })

  eventSource.addEventListener('error', (event) => {
    onError(new Error('SSE connection error'))
    eventSource.close()
  })

  eventSource.onerror = () => {
    onError(new Error('SSE connection failed'))
    eventSource.close()
  }

  // Return cleanup function
  return () => {
    eventSource.close()
  }
}
