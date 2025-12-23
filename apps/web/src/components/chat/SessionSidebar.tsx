'use client'

import { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { SettingsMenu } from './SettingsMenu'
import { ConversationSearch } from './ConversationSearch'

interface SessionPreview {
  id: string
  title: string | null
  preview: string | null
  mode: string
  updated_at: string
}

interface GroupedSessions {
  today: SessionPreview[]
  yesterday: SessionPreview[]
  this_week: SessionPreview[]
  this_month: SessionPreview[]
  older: SessionPreview[]
}

interface SessionSidebarProps {
  currentSessionId: string | null
  onSelectSession: (sessionId: string) => void
  onNewSession: () => void
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function SessionSidebar({
  currentSessionId,
  onSelectSession,
  onNewSession,
}: SessionSidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [yoloMode, setYoloMode] = useState(false)
  const [isSearchMode, setIsSearchMode] = useState(false)
  const queryClient = useQueryClient()

  // Fetch initial settings
  useEffect(() => {
    fetch(`${API_BASE}/settings`)
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data?.yolo_mode !== undefined) {
          setYoloMode(data.yolo_mode)
        }
      })
      .catch(() => {})
  }, [])

  const handleYoloModeChange = async (value: boolean) => {
    // Optimistic update
    setYoloMode(value)
    try {
      const res = await fetch(`${API_BASE}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ yolo_mode: value }),
      })
      if (!res.ok) {
        // Revert on failure
        setYoloMode(!value)
      }
    } catch {
      setYoloMode(!value)
    }
  }

  const { data: groups, isLoading } = useQuery<GroupedSessions>({
    queryKey: ['sessions', 'grouped'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/sessions/grouped`)
      if (!res.ok) throw new Error('Failed to load sessions')
      return res.json()
    },
    refetchInterval: 30000, // Refresh every 30s
  })

  const deleteSession = useMutation({
    mutationFn: async (sessionId: string) => {
      const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to delete session')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  const renderGroup = (title: string, sessions: SessionPreview[]) => {
    if (!sessions.length) return null

    return (
      <div className="mb-4" key={title}>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">
          {title}
        </h3>
        <ul className="space-y-1">
          {sessions.map((session) => (
            <li key={session.id} className="group flex items-center">
              <button
                onClick={() => onSelectSession(session.id)}
                className={`flex-1 text-left px-2 py-1.5 rounded-md text-sm truncate hover:bg-gray-100 ${
                  currentSessionId === session.id
                    ? 'bg-gray-100 font-medium'
                    : ''
                }`}
              >
                {session.title || session.preview || 'New conversation'}
              </button>
              <button
                onClick={() => {
                  if (confirm('Delete this conversation?')) {
                    deleteSession.mutate(session.id)
                  }
                }}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 rounded ml-1"
                title="Delete"
              >
                <svg className="w-3 h-3 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  if (isCollapsed) {
    return (
      <div className="w-12 border-r bg-gray-50 flex flex-col items-center py-4">
        <button
          onClick={() => setIsCollapsed(false)}
          className="p-2 hover:bg-gray-200 rounded-md"
          title="Expand sidebar"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
        <button
          onClick={onNewSession}
          className="p-2 hover:bg-gray-200 rounded-md mt-2"
          title="New conversation"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
        </button>
      </div>
    )
  }

  return (
    <div className="w-64 border-r bg-gray-50 flex flex-col h-full h-[100dvh]">
      {/* Header */}
      <div className="p-3 border-b flex items-center justify-between">
        <button
          onClick={onNewSession}
          className="flex items-center gap-2 px-3 py-1.5 bg-gray-900 text-white rounded-md text-sm hover:bg-gray-800"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>
        <button
          onClick={() => setIsCollapsed(true)}
          className="p-1.5 hover:bg-gray-200 rounded-md hidden md:block"
          title="Collapse sidebar"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        {/* Mobile close button */}
        <button
          onClick={() => {
            // This will be handled by the parent component
            const event = new CustomEvent('closeMobileSidebar')
            window.dispatchEvent(event)
          }}
          className="p-1.5 hover:bg-gray-200 rounded-md md:hidden"
          title="Close sidebar"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Search */}
      <div className="px-2 pt-2">
        <ConversationSearch
          onSelectSession={onSelectSession}
          onSearchModeChange={setIsSearchMode}
        />
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-2">
        {!isSearchMode && (
          <>
            {isLoading ? (
              <div className="text-center text-gray-500 text-sm py-4">Loading...</div>
            ) : groups ? (
              <>
                {renderGroup('Today', groups.today)}
                {renderGroup('Yesterday', groups.yesterday)}
                {renderGroup('This Week', groups.this_week)}
                {renderGroup('This Month', groups.this_month)}
                {renderGroup('Older', groups.older)}
              </>
            ) : (
              <div className="text-center text-gray-500 text-sm py-4">
                No conversations yet
              </div>
            )}
          </>
        )}
      </div>

      {/* Settings Menu */}
      <SettingsMenu yoloMode={yoloMode} onYoloModeChange={handleYoloModeChange} />
    </div>
  )
}
