'use client'

import { useState, useCallback, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { SessionSidebar } from '@/components/chat/SessionSidebar'
import { ChatContainer } from '@/components/chat/ChatContainer'
import { HealthChip } from '@/components/chat/HealthChip'

export default function ChatPage() {
  // Always start with a fresh chat - don't restore from localStorage
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const queryClient = useQueryClient()

  // Detect mobile viewport
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 768)
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Listen for sidebar close event from mobile
  useEffect(() => {
    const handleCloseSidebar = () => setIsMobileSidebarOpen(false)
    window.addEventListener('closeMobileSidebar', handleCloseSidebar)
    return () => window.removeEventListener('closeMobileSidebar', handleCloseSidebar)
  }, [])

  const handleSelectSession = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    localStorage.setItem('chat_session_id', sessionId)
    // Close sidebar on mobile after selection
    setIsMobileSidebarOpen(false)
  }, [])

  const handleNewSession = useCallback(() => {
    setCurrentSessionId(null)
    localStorage.removeItem('chat_session_id')
    // Close sidebar on mobile after new session
    setIsMobileSidebarOpen(false)
  }, [])

  const handleSessionCreated = useCallback((sessionId: string) => {
    setCurrentSessionId(sessionId)
    // Note: localStorage is already updated by useChat hook when session is created
    // Defer sidebar refresh to avoid race condition during session creation
    // This prevents the flicker and wrongly reopening previous sessions
    setTimeout(() => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    }, 1500)
  }, [queryClient])

  return (
    <div className="flex h-screen h-[100dvh] overflow-hidden">
      {/* Health indicator */}
      <HealthChip />

      {/* Mobile sidebar toggle */}
      {isMobile && (
        <button
          onClick={() => setIsMobileSidebarOpen(true)}
          className="fixed top-3 left-3 z-40 p-2 bg-white border border-gray-200 rounded-lg shadow-sm md:hidden"
          aria-label="Open menu"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      )}

      {/* Mobile sidebar overlay */}
      {isMobile && isMobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsMobileSidebarOpen(false)}
        />
      )}

      {/* Left sidebar - Session list */}
      <div className={`
        ${isMobile ? 'fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-in-out' : ''}
        ${isMobile && !isMobileSidebarOpen ? '-translate-x-full' : 'translate-x-0'}
        ${!isMobile ? '' : ''}
      `}>
        <SessionSidebar
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
        />
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        <ChatContainer
          sessionId={currentSessionId}
          onSessionCreated={handleSessionCreated}
        />
      </div>
    </div>
  )
}
