'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { useChat } from '@/hooks/useChat'
import { useModes, type Mode } from '@/hooks/useModes'
import { type ChatMode } from '@/lib/chat-api'
import { ModeSelector } from './ModeSelector'
import { ProviderSelector } from './ProviderSelector'
import { MessageList } from './MessageList'
import { MessageInput, type MessageInputHandle } from './MessageInput'
import { TokenCounter } from './TokenCounter'
import { ContextFileSelector, type PendingContextFile } from './ContextFileSelector'
import { ModeChips } from '../modes/ModeChips'
import { CommandChips } from './CommandChips'
import { NewChatModal, type ChatConfig } from '../modes/NewChatModal'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ChatContainerProps {
  sessionId?: string | null
  onSessionCreated?: (sessionId: string) => void
}

export function ChatContainer({ sessionId: propSessionId, onSessionCreated }: ChatContainerProps) {
  const [mode, setMode] = useState<ChatMode>('tools')
  const [provider, setProvider] = useState('anthropic')
  const [model, setModel] = useState('claude-sonnet-4-5-20250929')
  const [currentDraft, setCurrentDraft] = useState('')
  const [isContextSelectorOpen, setIsContextSelectorOpen] = useState(false)
  const [selectedDbMode, setSelectedDbMode] = useState<Mode | null>(null)
  const [pendingContextFiles, setPendingContextFiles] = useState<PendingContextFile[]>([])
  const [isPersonaModalOpen, setIsPersonaModalOpen] = useState(false)
  const [leadPersonaId, setLeadPersonaId] = useState<string | null>(null)
  const [councilMemberIds, setCouncilMemberIds] = useState<string[]>([])
  const messageInputRef = useRef<MessageInputHandle>(null)

  // Helper function to reset ALL component state (not just hook state)
  const resetComponentState = () => {
    setMode('tools')
    setProvider('anthropic')
    setModel('claude-sonnet-4-5-20250929')
    setCurrentDraft('')
    setSelectedDbMode(null)
    setPendingContextFiles([])
    setLeadPersonaId(null)
    setCouncilMemberIds([])
  }

  // Fetch database modes
  const { data: dbModes } = useModes()

  const {
    messages,
    sessionId,
    sessionTitle,
    isStreaming,
    error,
    currentAssistantMessage,
    currentToolCalls,
    currentToolResults,
    currentFileRefs,
    currentSubagents,
    currentProposals,
    currentCouncils,
    sessionUsage,
    sendMessage,
    loadSession,
    clearSession,
    cancelStreaming,
    updateProposalStatus,
  } = useChat()

  // Track whether we're currently loading a session (to prevent notify loop)
  const isLoadingSessionRef = useRef(false)
  const prevPropSessionIdRef = useRef<string | null | undefined>(propSessionId)

  // Load session when propSessionId changes to a specific session
  useEffect(() => {
    if (propSessionId && propSessionId !== sessionId) {
      isLoadingSessionRef.current = true
      loadSession(propSessionId)
        .catch(console.error)
        .finally(() => {
          isLoadingSessionRef.current = false
        })
    }
  }, [propSessionId, sessionId, loadSession])

  // Handle New Chat - clear session when propSessionId changes to null
  useEffect(() => {
    // If propSessionId changed to null (New Chat clicked)
    if (propSessionId === null && prevPropSessionIdRef.current !== null) {
      clearSession()  // Clear hook state (messages, sessionId, etc.)
      resetComponentState()  // Clear component state (mode, persona, etc.)
      setTimeout(() => messageInputRef.current?.focus(), 0)
    }
    prevPropSessionIdRef.current = propSessionId
  }, [propSessionId, clearSession])

  // Notify parent only when a NEW session is created (not when loading existing)
  useEffect(() => {
    // Only notify if:
    // 1. We have a sessionId
    // 2. It differs from propSessionId (new session created)
    // 3. We're not currently loading a session
    // 4. propSessionId was null (meaning we started fresh, not switching sessions)
    if (sessionId && onSessionCreated && sessionId !== propSessionId &&
        !isLoadingSessionRef.current && prevPropSessionIdRef.current === null) {
      onSessionCreated(sessionId)
    }
  }, [sessionId, propSessionId, onSessionCreated])

  // Attach pending context files when session is created
  useEffect(() => {
    if (sessionId && pendingContextFiles.length > 0) {
      // Attach all pending files to the new session
      const attachFiles = async () => {
        for (const file of pendingContextFiles) {
          try {
            await fetch(`${API_BASE}/chat/sessions/${sessionId}/context`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ file_path: file.path }),
            })
          } catch (err) {
            console.error('Failed to attach context file:', file.path, err)
          }
        }
        // Clear pending files after attaching
        setPendingContextFiles([])
      }
      attachFiles()
    }
  }, [sessionId, pendingContextFiles])

  // Select default mode when modes are loaded
  useEffect(() => {
    if (dbModes && dbModes.length > 0 && !selectedDbMode && !sessionId) {
      const defaultMode = dbModes.find(m => m.is_default) || dbModes[0]
      setSelectedDbMode(defaultMode)
      // Use mode's default model if set
      if (defaultMode.default_model) {
        setModel(defaultMode.default_model)
      }
    }
  }, [dbModes, selectedDbMode, sessionId])

  // Handle mode selection
  const handleModeSelect = (dbMode: Mode) => {
    setSelectedDbMode(dbMode)
    if (dbMode.default_model) {
      setModel(dbMode.default_model)
    }
  }

  const handlePersonaChatStart = (config: ChatConfig) => {
    // Clear everything first
    clearSession()  // Clear hook state (messages, sessionId, etc.)
    resetComponentState()  // Reset to defaults

    // Then apply persona configuration
    setLeadPersonaId(config.leadPersonaId)
    setCouncilMemberIds(config.councilMemberIds)
    if (config.modelOverride) {
      setModel(config.modelOverride)
    }

    // Focus input so user can start typing
    setTimeout(() => messageInputRef.current?.focus(), 0)
  }

  const handleSendMessage = (message: string) => {
    sendMessage({
      mode,
      provider,
      model,
      messages: [{ role: 'user', content: message, timestamp: new Date().toISOString() }],
      session_id: sessionId || undefined,
      attached_skills: [],
      mode_id: selectedDbMode?.id || undefined,
      lead_persona_id: leadPersonaId || undefined,
      council_member_ids: councilMemberIds,
    })
  }

  // Get chat title - prefer AI-generated title, fallback to first message
  const chatTitle = useMemo(() => {
    if (sessionTitle) return sessionTitle
    const firstUserMessage = messages.find(m => m.role === 'user')
    if (!firstUserMessage) return 'New Chat'
    const content = firstUserMessage.content
    return content.length > 50 ? content.slice(0, 50) + '...' : content
  }, [sessionTitle, messages])

  return (
    <div className="flex h-full">
      {/* Main chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="border-b bg-white">
          <div className="px-4 py-3 md:px-4 pl-14 md:pl-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex-1 min-w-0">
                <h1 className="text-lg md:text-xl font-bold text-gray-900 truncate">
                  {chatTitle}
                  <span className="hidden md:inline ml-2 text-sm font-normal text-gray-400">
                    {sessionId && `(${sessionId.slice(0, 8)})`}
                  </span>
                </h1>
              </div>
              {isStreaming && (
                <button
                  onClick={cancelStreaming}
                  className="px-3 py-1.5 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors ml-2 flex-shrink-0"
                >
                  Cancel
                </button>
              )}
            </div>
            <ModeSelector mode={mode} onChange={setMode} />
          </div>
          <div className="px-4 pb-3 border-t hidden md:block">
            <ProviderSelector
              provider={provider}
              model={model}
              onProviderChange={setProvider}
              onModelChange={setModel}
            />
          </div>
        </div>

        {/* Messages */}
        <MessageList
          messages={messages}
          currentAssistantMessage={currentAssistantMessage}
          currentToolCalls={currentToolCalls}
          currentToolResults={currentToolResults}
          currentFileRefs={currentFileRefs}
          currentSubagents={currentSubagents}
          currentProposals={currentProposals}
          currentCouncils={currentCouncils}
          isStreaming={isStreaming}
          onProposalStatusChange={updateProposalStatus}
        />

        {/* Error display */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-red-700 text-sm">
            Error: {error.message}
          </div>
        )}

        {/* Mode selection for new conversations */}
        {!sessionId && messages.length === 0 && dbModes && dbModes.length > 0 && (
          <div className="px-4 py-3 border-t bg-gray-50">
            <p className="text-sm text-gray-500 mb-2">Select a mode:</p>
            <ModeChips
              modes={dbModes}
              selectedId={selectedDbMode?.id || null}
              onSelect={handleModeSelect}
            />
          </div>
        )}

        {/* Input */}
        <div className="border-t bg-white p-3 md:p-4 pb-[calc(0.75rem+var(--safe-area-inset-bottom))] md:pb-4">
          {/* Command chips */}
          {messages.length === 0 && (
            <div className="mb-3">
              <CommandChips
                selectedModeId={selectedDbMode?.id}
                onCommandClick={(prompt) => {
                  handleSendMessage(prompt)
                }}
              />
            </div>
          )}
          <div className="flex items-end justify-between gap-2 mb-2">
            <div className="flex gap-2">
              <button
                onClick={() => setIsPersonaModalOpen(true)}
                className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Configure persona and council"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                </svg>
              </button>
              <button
                onClick={() => setIsContextSelectorOpen(true)}
                className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                title="Add context files"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
                {pendingContextFiles.length > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-white text-xs rounded-full flex items-center justify-center">
                    {pendingContextFiles.length}
                  </span>
                )}
              </button>
            </div>
            {/* Pending files indicator */}
            {!sessionId && pendingContextFiles.length > 0 && (
              <div className="flex flex-wrap gap-1 items-center">
                {pendingContextFiles.map((file) => (
                  <span
                    key={file.path}
                    className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-800 rounded text-xs"
                  >
                    <span className="truncate max-w-24">{file.name}</span>
                    <button
                      onClick={() => setPendingContextFiles(pendingContextFiles.filter(f => f.path !== file.path))}
                      className="hover:bg-amber-200 rounded p-0.5"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="flex-1" />
            <div className="hidden md:block">
              <TokenCounter
                sessionTokens={{
                  input: sessionUsage.input,
                  output: sessionUsage.output,
                  cacheRead: sessionUsage.cacheRead,
                  cacheCreation: sessionUsage.cacheCreation,
                }}
                currentDraft={currentDraft}
                model={model}
              />
            </div>
          </div>
          <MessageInput
            ref={messageInputRef}
            onSend={(msg) => {
              handleSendMessage(msg)
              setCurrentDraft('')
            }}
            onChange={setCurrentDraft}
            disabled={isStreaming}
            autoFocus={true}
            placeholder={
              mode === 'tools'
                ? 'Ask about your calendar, tasks, or vault...'
                : 'Describe a task for the agent to complete...'
            }
          />
        </div>
      </div>

      {/* Context file selector modal */}
      <ContextFileSelector
        sessionId={sessionId}
        isOpen={isContextSelectorOpen}
        onClose={() => setIsContextSelectorOpen(false)}
        pendingFiles={pendingContextFiles}
        onPendingFilesChange={setPendingContextFiles}
      />

      {/* Persona selection modal */}
      <NewChatModal
        open={isPersonaModalOpen}
        onClose={() => setIsPersonaModalOpen(false)}
        onStartChat={handlePersonaChatStart}
      />
    </div>
  )
}
