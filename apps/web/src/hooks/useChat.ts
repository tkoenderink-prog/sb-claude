import { useState, useCallback, useRef, useEffect } from 'react'
import {
  streamChatResponse,
  getSession,
  generateSessionTitle,
  type ChatRequest,
  type ChatMessage,
  type ToolCall,
  type ToolResult,
  type FileReference,
  type Artifact,
  type Subagent,
  type ChatProposal,
  type TokenUsage,
  type CouncilEventData,
} from '@/lib/chat-api'

const SESSION_ID_KEY = 'chat_session_id'

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionTitle, setSessionTitle] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [currentAssistantMessage, setCurrentAssistantMessage] = useState<string>('')
  const [currentToolCalls, setCurrentToolCalls] = useState<ToolCall[]>([])
  const [currentToolResults, setCurrentToolResults] = useState<ToolResult[]>([])
  const [currentFileRefs, setCurrentFileRefs] = useState<FileReference[]>([])
  const [currentArtifacts, setCurrentArtifacts] = useState<Artifact[]>([])
  const [currentSubagents, setCurrentSubagents] = useState<Subagent[]>([])
  const [currentProposals, setCurrentProposals] = useState<ChatProposal[]>([])
  const [currentCouncils, setCurrentCouncils] = useState<CouncilEventData[]>([])
  const [sessionUsage, setSessionUsage] = useState<{ input: number; output: number; cacheRead: number; cacheCreation: number }>({
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheCreation: 0,
  })
  const cleanupRef = useRef<(() => void) | null>(null)
  const titleGeneratingRef = useRef<boolean>(false)

  // Use refs to track accumulated data (avoids closure issues)
  const accumulatedTextRef = useRef<string>('')
  const accumulatedToolCallsRef = useRef<ToolCall[]>([])
  const accumulatedToolResultsRef = useRef<ToolResult[]>([])
  const accumulatedFileRefsRef = useRef<FileReference[]>([])
  const accumulatedArtifactsRef = useRef<Artifact[]>([])
  const accumulatedSubagentsRef = useRef<Subagent[]>([])
  const accumulatedProposalsRef = useRef<ChatProposal[]>([])
  const accumulatedCouncilsRef = useRef<CouncilEventData[]>([])
  const completedRef = useRef<boolean>(false)
  const mountedRef = useRef<boolean>(true)

  // Cleanup on unmount - cancel any active streams
  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (cleanupRef.current) {
        cleanupRef.current()
        cleanupRef.current = null
      }
    }
  }, [])

  // Note: Session loading is controlled by the parent component (ChatPage/ChatContainer)
  // via the loadSession callback. We don't auto-load from localStorage here.

  const loadSession = useCallback(async (id: string) => {
    try {
      const session = await getSession(id)
      // Normalize historical messages: ensure tool calls have proper status
      const normalizedMessages = (session.messages || []).map((msg: ChatMessage) => {
        if (msg.role === 'assistant' && msg.tool_calls && msg.tool_calls.length > 0) {
          // For historical messages, tool calls should be marked as completed
          // (they wouldn't be saved if they hadn't completed)
          const normalizedToolCalls = msg.tool_calls.map((tc: ToolCall) => ({
            ...tc,
            status: tc.status || (msg.tool_results?.some(tr => tr.tool_call_id === tc.id) ? 'completed' : 'completed'),
          }))
          return { ...msg, tool_calls: normalizedToolCalls }
        }
        return msg
      })
      setMessages(normalizedMessages)
      setSessionId(id)
    } catch (err) {
      console.error('Failed to load session:', err)
      throw err
    }
  }, [])

  const sendMessage = useCallback((request: ChatRequest) => {
    // Build full message list for the request
    const newUserMessage: ChatMessage = {
      role: 'user',
      content: request.messages[request.messages.length - 1]?.content || '',
      timestamp: new Date().toISOString(),
    }

    // Get current messages synchronously using a ref pattern
    // This avoids React 18 batching issues with setState
    let currentMessages: ChatMessage[] = []

    // Add user message to UI immediately and capture current state
    setMessages((prev) => {
      currentMessages = [...prev, newUserMessage]
      return currentMessages
    })

    // Ensure we have the new message even if setState batching delays
    if (currentMessages.length === 0) {
      currentMessages = [newUserMessage]
    }

    // Build request with full history including new message
    const fullRequest: ChatRequest = {
      ...request,
      messages: currentMessages,
      session_id: sessionId || undefined,
    }

    // Reset streaming state and refs
    setCurrentAssistantMessage('')
    setCurrentToolCalls([])
    setCurrentToolResults([])
    setCurrentFileRefs([])
    setCurrentArtifacts([])
    setCurrentSubagents([])
    setCurrentProposals([])
    setCurrentCouncils([])
    setIsStreaming(true)
    setError(null)

    accumulatedTextRef.current = ''
    accumulatedToolCallsRef.current = []
    accumulatedToolResultsRef.current = []
    accumulatedFileRefsRef.current = []
    accumulatedArtifactsRef.current = []
    accumulatedSubagentsRef.current = []
    accumulatedProposalsRef.current = []
    accumulatedCouncilsRef.current = []
    completedRef.current = false

    // Start streaming
    const cleanup = streamChatResponse(
      fullRequest,
      // onText
      (text) => {
        if (!mountedRef.current) return
        accumulatedTextRef.current += text
        setCurrentAssistantMessage(accumulatedTextRef.current)
      },
      // onToolCall
      (toolCall) => {
        if (!mountedRef.current) return
        // Ensure tool call has a status (default to 'pending')
        const normalizedToolCall = { ...toolCall, status: toolCall.status || 'pending' }
        accumulatedToolCallsRef.current = [...accumulatedToolCallsRef.current, normalizedToolCall]
        setCurrentToolCalls(accumulatedToolCallsRef.current)
      },
      // onToolResult
      (toolResult) => {
        if (!mountedRef.current) return
        accumulatedToolResultsRef.current = [...accumulatedToolResultsRef.current, toolResult]
        setCurrentToolResults(accumulatedToolResultsRef.current)
        // Update tool call status
        accumulatedToolCallsRef.current = accumulatedToolCallsRef.current.map((tc) =>
          tc.id === toolResult.tool_call_id
            ? { ...tc, status: toolResult.error ? 'failed' : 'completed' }
            : tc
        )
        setCurrentToolCalls(accumulatedToolCallsRef.current)
      },
      // onFileRef
      (fileRef) => {
        if (!mountedRef.current) return
        accumulatedFileRefsRef.current = [...accumulatedFileRefsRef.current, fileRef]
        setCurrentFileRefs(accumulatedFileRefsRef.current)
      },
      // onArtifact
      (artifact) => {
        if (!mountedRef.current) return
        accumulatedArtifactsRef.current = [...accumulatedArtifactsRef.current, artifact]
        setCurrentArtifacts(accumulatedArtifactsRef.current)
      },
      // onSubagent
      (subagent) => {
        if (!mountedRef.current) return
        // Find and update existing subagent or add new one
        const existingIndex = accumulatedSubagentsRef.current.findIndex(s => s.id === subagent.id)
        if (existingIndex >= 0) {
          accumulatedSubagentsRef.current = accumulatedSubagentsRef.current.map((s, i) =>
            i === existingIndex ? subagent : s
          )
        } else {
          accumulatedSubagentsRef.current = [...accumulatedSubagentsRef.current, subagent]
        }
        setCurrentSubagents(accumulatedSubagentsRef.current)
      },
      // onProposal
      (proposal) => {
        if (!mountedRef.current) return
        // Find and update existing proposal or add new one
        const existingIndex = accumulatedProposalsRef.current.findIndex(p => p.id === proposal.id)
        if (existingIndex >= 0) {
          accumulatedProposalsRef.current = accumulatedProposalsRef.current.map((p, i) =>
            i === existingIndex ? proposal : p
          )
        } else {
          accumulatedProposalsRef.current = [...accumulatedProposalsRef.current, proposal]
        }
        setCurrentProposals(accumulatedProposalsRef.current)
      },
      // onCouncil
      (council) => {
        if (!mountedRef.current) return
        accumulatedCouncilsRef.current = [...accumulatedCouncilsRef.current, council]
        setCurrentCouncils(accumulatedCouncilsRef.current)
      },
      // onStatus
      (status, receivedSessionId) => {
        if (!mountedRef.current) return
        // Update session ID if received
        if (receivedSessionId && receivedSessionId !== sessionId) {
          setSessionId(receivedSessionId)
          localStorage.setItem(SESSION_ID_KEY, receivedSessionId)
        }

        if (status === 'completed' && !completedRef.current) {
          completedRef.current = true

          // Only add message if there's content
          if (accumulatedTextRef.current || accumulatedToolCallsRef.current.length > 0) {
            const assistantMessage: ChatMessage = {
              role: 'assistant',
              content: accumulatedTextRef.current,
              timestamp: new Date().toISOString(),
              tool_calls: accumulatedToolCallsRef.current.length > 0 ? accumulatedToolCallsRef.current : undefined,
              tool_results: accumulatedToolResultsRef.current.length > 0 ? accumulatedToolResultsRef.current : undefined,
              file_refs: accumulatedFileRefsRef.current.length > 0 ? accumulatedFileRefsRef.current : undefined,
              artifacts: accumulatedArtifactsRef.current.length > 0 ? accumulatedArtifactsRef.current : undefined,
              subagents: accumulatedSubagentsRef.current.length > 0 ? accumulatedSubagentsRef.current : undefined,
              councils: accumulatedCouncilsRef.current.length > 0 ? accumulatedCouncilsRef.current : undefined,
            }
            setMessages((prev) => [...prev, assistantMessage])
          }

          // Generate title if this is a new session without a title
          const currentSessionId = receivedSessionId || sessionId
          if (currentSessionId && !sessionTitle && !titleGeneratingRef.current) {
            titleGeneratingRef.current = true
            generateSessionTitle(currentSessionId)
              .then((result) => {
                if (mountedRef.current) {
                  setSessionTitle(result.title)
                }
              })
              .catch((err) => {
                console.error('Failed to generate title:', err)
              })
              .finally(() => {
                titleGeneratingRef.current = false
              })
          }

          setIsStreaming(false)
          setCurrentAssistantMessage('')
          setCurrentToolCalls([])
          setCurrentToolResults([])
          setCurrentFileRefs([])
          setCurrentArtifacts([])
          setCurrentSubagents([])
          // NOTE: Don't clear currentProposals here - they need to persist
          // for user to approve/reject after the conversation completes
        } else if (status === 'failed') {
          setIsStreaming(false)
          setError(new Error('Chat request failed'))
        }
      },
      // onError
      (err) => {
        if (!mountedRef.current) return
        setError(err)
        setIsStreaming(false)
      },
      // onUsage
      (usage) => {
        if (!mountedRef.current) return
        setSessionUsage((prev) => ({
          input: prev.input + usage.input_tokens,
          output: prev.output + usage.output_tokens,
          cacheRead: prev.cacheRead + (usage.cache_read_tokens || 0),
          cacheCreation: prev.cacheCreation + (usage.cache_creation_tokens || 0),
        }))
      }
    )

    cleanupRef.current = cleanup
  }, [sessionId, sessionTitle])

  const clearMessages = useCallback(() => {
    setMessages([])
    setCurrentAssistantMessage('')
    setCurrentToolCalls([])
    setCurrentToolResults([])
    setCurrentFileRefs([])
    setCurrentArtifacts([])
    setCurrentSubagents([])
    setCurrentProposals([])
    setCurrentCouncils([])
    setError(null)
  }, [])

  const clearSession = useCallback(() => {
    setMessages([])
    setSessionId(null)
    setSessionTitle(null)
    setCurrentAssistantMessage('')
    setCurrentToolCalls([])
    setCurrentToolResults([])
    setCurrentFileRefs([])
    setCurrentArtifacts([])
    setCurrentSubagents([])
    setCurrentProposals([])
    setCurrentCouncils([])
    setSessionUsage({ input: 0, output: 0, cacheRead: 0, cacheCreation: 0 })
    setError(null)
    titleGeneratingRef.current = false
    localStorage.removeItem(SESSION_ID_KEY)
  }, [])

  const cancelStreaming = useCallback(() => {
    if (cleanupRef.current) {
      cleanupRef.current()
      cleanupRef.current = null
    }
    setIsStreaming(false)
  }, [])

  const updateProposalStatus = useCallback((proposalId: string, newStatus: 'applied' | 'rejected') => {
    setCurrentProposals((prev) =>
      prev.map((p) => (p.id === proposalId ? { ...p, status: newStatus } : p))
    )
  }, [])

  return {
    messages,
    sessionId,
    sessionTitle,
    isStreaming,
    error,
    currentAssistantMessage,
    currentToolCalls,
    currentToolResults,
    currentFileRefs,
    currentArtifacts,
    currentSubagents,
    currentProposals,
    currentCouncils,
    sessionUsage,
    sendMessage,
    loadSession,
    clearMessages,
    clearSession,
    cancelStreaming,
    updateProposalStatus,
  }
}
