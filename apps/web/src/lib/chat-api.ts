import axios from 'axios'

// API base URL - uses environment variable for Tailscale/remote access
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Chat Types
export interface Subagent {
  id: string
  type: string
  task: string
  status: 'running' | 'completed' | 'failed'
  result?: string
  error?: string
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  tool_calls?: ToolCall[]
  tool_results?: ToolResult[]
  file_refs?: FileReference[]
  artifacts?: Artifact[]
  subagents?: Subagent[]
  councils?: CouncilEventData[]  // Phase 10: Council responses
}

export interface ToolCall {
  id: string
  tool: string  // Backend field name
  arguments: Record<string, any>  // Backend field name
  status?: 'pending' | 'running' | 'completed' | 'failed'
}

export interface ToolResult {
  tool_call_id: string
  result: any
  error?: string
}

export interface FileReference {
  path: string
  line?: number
  heading?: string
}

export interface Artifact {
  id: string
  name: string
  type: 'report' | 'analysis' | 'export' | 'code' | 'other'
  mime_type: string
  size_bytes: number
  download_url: string
  created_at: string
}

export type ChatMode = 'tools' | 'agent'

export interface ChatRequest {
  mode: ChatMode
  provider: string
  model: string
  messages: ChatMessage[]
  session_id?: string
  attached_skills?: string[]
  mode_id?: string  // Phase 9: Database mode reference
  lead_persona_id?: string  // Phase 10: Persona system
  council_member_ids?: string[]  // Phase 10: Council members
}

export interface ChatSession {
  id: string
  created_at: string
  updated_at: string
  mode: ChatMode
  provider: string
  model: string
  message_count: number
  attached_skills: string[]
  lead_persona_id?: string  // Phase 10: Persona system
  council_member_ids?: string[]  // Phase 10: Council members
}

export interface ProviderInfo {
  name: string
  display_name: string
  models: ModelInfo[]
  supports_tools: boolean
  supports_agent: boolean
}

export interface ModelInfo {
  id: string
  display_name: string
  context_window: number
  supports_streaming: boolean
}

// SSE Event Types for Chat
export interface ChatTextEvent {
  type: 'text'
  content: string
}

export interface ChatToolCallEvent {
  type: 'tool_call'
  tool_call: ToolCall
}

export interface ChatToolResultEvent {
  type: 'tool_result'
  tool_result: ToolResult
}

export interface ChatFileRefEvent {
  type: 'file_ref'
  file_ref: FileReference
}

export interface ChatArtifactEvent {
  type: 'artifact'
  artifact: Artifact
}

export interface ChatStatusEvent {
  type: 'status'
  status: 'started' | 'completed' | 'failed'
}

export interface ChatErrorEvent {
  type: 'error'
  message: string
}

export interface ChatSubagentEvent {
  type: 'subagent'
  subagent: Subagent
}

export interface ProposalFileInfo {
  path: string
  operation: 'create' | 'modify' | 'delete'
  diff_preview?: string
  lines_added: number
  lines_removed: number
}

export interface ChatProposal {
  id: string
  description: string
  files: ProposalFileInfo[]
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  auto_applied: boolean
  requires_approval: boolean
}

export interface ChatProposalEvent {
  type: 'proposal'
  proposal: ChatProposal
}

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  cache_read_tokens?: number
  cache_creation_tokens?: number
}

export interface ChatUsageEvent {
  type: 'usage'
  usage: TokenUsage
}

// Phase 10: Council event types
export interface CouncilMember {
  name: string
  icon: string
  response: string
}

export interface CouncilEventData {
  council_name: string
  members: CouncilMember[]
  synthesis: string
  orchestrator?: string
}

export interface ChatCouncilEvent {
  type: 'council'
  council: CouncilEventData
}

export type ChatEvent =
  | ChatTextEvent
  | ChatToolCallEvent
  | ChatToolResultEvent
  | ChatFileRefEvent
  | ChatArtifactEvent
  | ChatStatusEvent
  | ChatErrorEvent
  | ChatSubagentEvent
  | ChatProposalEvent
  | ChatUsageEvent
  | ChatCouncilEvent

// API Functions
export async function getSessions(): Promise<ChatSession[]> {
  const response = await api.get<ChatSession[]>('/chat/sessions')
  return response.data
}

export async function getSession(sessionId: string): Promise<ChatSession & { messages: ChatMessage[] }> {
  const response = await api.get(`/chat/sessions/${sessionId}`)
  return response.data
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/chat/sessions/${sessionId}`)
}

interface ApiProviderResponse {
  id: string
  name: string
  models: Array<{
    id: string
    name: string
    capabilities: string[]
    context_window: number
    max_output: number
  }>
}

export async function getProviders(): Promise<ProviderInfo[]> {
  const response = await api.get<ApiProviderResponse[]>('/chat/providers')
  // Transform API response to match frontend interface
  return response.data.map((p) => ({
    name: p.id,
    display_name: p.name,
    models: p.models.map((m) => ({
      id: m.id,
      display_name: m.name,
      context_window: m.context_window,
      supports_streaming: m.capabilities.includes('streaming'),
    })),
    supports_tools: p.models.some((m) => m.capabilities.includes('tools')),
    supports_agent: p.id === 'anthropic', // Only Anthropic supports agent mode
  }))
}

export async function generateSessionTitle(sessionId: string): Promise<{ title: string; session_id: string }> {
  const response = await api.post(`/chat/sessions/${sessionId}/title`)
  return response.data
}

// SSE Stream helper using fetch (POST with body support)
export function streamChatResponse(
  request: ChatRequest,
  onText: (text: string) => void,
  onToolCall: (toolCall: ToolCall) => void,
  onToolResult: (toolResult: ToolResult) => void,
  onFileRef: (fileRef: FileReference) => void,
  onArtifact: (artifact: Artifact) => void,
  onSubagent: (subagent: Subagent) => void,
  onProposal: (proposal: ChatProposal) => void,
  onCouncil: (council: CouncilEventData) => void,
  onStatus: (status: 'started' | 'completed' | 'failed', sessionId?: string) => void,
  onError: (error: Error) => void,
  onUsage?: (usage: TokenUsage) => void
): () => void {
  const abortController = new AbortController()

  // Build request body matching backend ChatRequest model
  const body = {
    mode: request.mode,
    provider: request.provider,
    model: request.model,
    messages: request.messages,
    session_id: request.session_id,
    attached_skills: request.attached_skills || [],
    lead_persona_id: request.lead_persona_id,
    council_member_ids: request.council_member_ids || [],
  }

  fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal: abortController.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events from buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        let currentEvent = ''
        let currentData = ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7)
          } else if (line.startsWith('data: ')) {
            currentData = line.slice(6)
          } else if (line === '' && currentEvent && currentData) {
            // End of event, process it
            try {
              const parsed = JSON.parse(currentData)

              switch (currentEvent) {
                case 'text':
                  onText(parsed.data?.text || '')
                  break
                case 'tool_call':
                  onToolCall({
                    id: parsed.data?.id,
                    tool: parsed.data?.tool,
                    arguments: parsed.data?.arguments || {},
                    status: parsed.data?.status,
                  })
                  break
                case 'tool_result':
                  onToolResult({
                    tool_call_id: parsed.data?.tool_call_id,
                    result: parsed.data?.result,
                    error: parsed.data?.error,
                  })
                  break
                case 'file_ref':
                  onFileRef(parsed.data)
                  break
                case 'artifact':
                  onArtifact(parsed.data)
                  break
                case 'subagent':
                  onSubagent(parsed.data)
                  break
                case 'proposal':
                  onProposal(parsed.data)
                  break
                case 'council':
                  onCouncil(parsed.data)
                  break
                case 'usage':
                  if (onUsage) {
                    onUsage({
                      input_tokens: parsed.data?.input_tokens || 0,
                      output_tokens: parsed.data?.output_tokens || 0,
                      cache_read_tokens: parsed.data?.cache_read_tokens,
                      cache_creation_tokens: parsed.data?.cache_creation_tokens,
                    })
                  }
                  break
                case 'status':
                  onStatus(parsed.status || parsed.data?.status, parsed.data?.session_id)
                  break
                case 'done':
                  onStatus('completed', parsed.data?.session_id)
                  break
                case 'error':
                  onError(new Error(parsed.data?.error || 'Unknown error'))
                  break
              }
            } catch (e) {
              console.error('Failed to parse SSE event:', currentEvent, currentData, e)
            }

            currentEvent = ''
            currentData = ''
          }
        }
      }

      // Stream ended normally
      onStatus('completed')
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        onError(error)
      }
    })

  // Return cleanup function
  return () => {
    abortController.abort()
  }
}
