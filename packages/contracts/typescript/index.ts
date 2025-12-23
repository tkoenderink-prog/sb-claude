// Second Brain Contracts - TypeScript Types
// Generated from JSON Schema definitions

export type JobType = 'processor' | 'index' | 'agent' | 'chat';
export type JobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
export type TaskStatus = 'todo' | 'done' | 'in_progress' | 'cancelled';
export type TaskPriority = 'highest' | 'high' | 'medium' | 'low' | 'lowest';
export type CalendarProvider = 'google' | 'm365';
export type Visibility = 'private' | 'public';

export interface ArtifactRef {
  id: string;
  name: string;
  path: string;
  mime_type?: string;
  size_bytes?: number;
}

export interface JobRunV1 {
  id: string;
  type: JobType;
  status: JobStatus;
  command: string;
  args?: Record<string, unknown>;
  started_at: string;
  ended_at?: string | null;
  artifacts: ArtifactRef[];
  metrics?: Record<string, unknown>;
}

export interface Attendee {
  email: string;
  name?: string;
  status?: string;
}

export interface SourceProvenance {
  raw_hash: string;
  fetched_at: string;
}

export interface NormalizedEventV1 {
  event_id: string;
  provider: CalendarProvider;
  calendar_id?: string;
  start: string;
  end: string;
  timezone?: string;
  title: string;
  description?: string | null;
  location?: string | null;
  all_day: boolean;
  attendees: Attendee[];
  visibility: Visibility;
  source_provenance?: SourceProvenance;
}

export interface TaskItemV1 {
  task_id: string;
  file_path: string;
  line_number: number;
  text: string;
  text_clean: string;
  status: TaskStatus;
  due_date?: string | null;
  scheduled_date?: string | null;
  priority?: TaskPriority | null;
  tags: string[];
  estimate_min?: number | null;
  actual_min?: number | null;
  obsidian_uri: string;
}

export interface ChunkV1 {
  chunk_id: string;
  text: string;
  file_path: string;
  heading_path?: string;
  tags: string[];
  links: string[];
  start_line: number;
  end_line: number;
  token_count: number;
}

// SSE Event types
export type SSEEventType = 'log' | 'assistant' | 'tool_call' | 'tool_result' | 'artifact' | 'status';

export interface SSELogEvent {
  type: 'log';
  data: string;
}

export interface SSEAssistantEvent {
  type: 'assistant';
  data: string;
}

export interface SSEToolCallEvent {
  type: 'tool_call';
  data: {
    tool_name: string;
    arguments: Record<string, unknown>;
  };
}

export interface SSEToolResultEvent {
  type: 'tool_result';
  data: {
    tool_name: string;
    result: unknown;
  };
}

export interface SSEArtifactEvent {
  type: 'artifact';
  data: ArtifactRef;
}

export interface SSEStatusEvent {
  type: 'status';
  data: 'started' | 'completed' | 'failed';
}

export type SSEEvent =
  | SSELogEvent
  | SSEAssistantEvent
  | SSEToolCallEvent
  | SSEToolResultEvent
  | SSEArtifactEvent
  | SSEStatusEvent;

// API Response types
export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  version: string;
  timestamp?: string;
}

export interface JobListResponse {
  jobs: JobRunV1[];
  total: number;
}

export interface RunJobRequest {
  type: JobType;
  command: string;
  args?: Record<string, unknown>;
}
