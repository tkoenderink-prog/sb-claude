'use client'

import { useEffect, useRef } from 'react'
import { type ChatMessage, type ChatProposal, type CouncilEventData } from '@/lib/chat-api'
import { MessageBubble } from './MessageBubble'
import { ProposalCard } from '../proposal/ProposalCard'

interface MessageListProps {
  messages: ChatMessage[]
  currentAssistantMessage?: string
  currentToolCalls?: any[]
  currentToolResults?: any[]
  currentFileRefs?: any[]
  currentSubagents?: any[]
  currentProposals?: ChatProposal[]
  currentCouncils?: CouncilEventData[]
  isStreaming?: boolean
  onProposalStatusChange?: (proposalId: string, newStatus: 'applied' | 'rejected') => void
}

export function MessageList({
  messages,
  currentAssistantMessage,
  currentToolCalls,
  currentToolResults,
  currentFileRefs,
  currentSubagents,
  currentProposals,
  currentCouncils,
  isStreaming = false,
  onProposalStatusChange,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [messages, currentAssistantMessage])

  // Create temporary message for streaming content
  // Show streaming message if there's text OR tool calls (tool calls can come before text)
  const hasStreamingContent = currentAssistantMessage ||
    (currentToolCalls && currentToolCalls.length > 0) ||
    (currentSubagents && currentSubagents.length > 0) ||
    (currentCouncils && currentCouncils.length > 0)

  const streamingMessage: ChatMessage | null =
    isStreaming && hasStreamingContent
      ? {
          role: 'assistant',
          content: currentAssistantMessage || '',
          timestamp: new Date().toISOString(),
          tool_calls: currentToolCalls,
          tool_results: currentToolResults,
          file_refs: currentFileRefs,
          subagents: currentSubagents,
          councils: currentCouncils,
        }
      : null

  const allMessages = streamingMessage ? [...messages, streamingMessage] : messages

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto p-4 bg-white"
    >
      {allMessages.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <p className="text-lg font-medium mb-2">Start a conversation</p>
            <p className="text-sm">Ask about your calendar, tasks, or vault content</p>
          </div>
        </div>
      ) : (
        <div>
          {allMessages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              isStreaming={index === allMessages.length - 1 && isStreaming}
            />
          ))}

          {/* Render current proposals */}
          {currentProposals && currentProposals.length > 0 && (
            <div className="mt-4 space-y-3">
              {currentProposals.map((proposal) => (
                <ProposalCard
                  key={proposal.id}
                  proposalId={proposal.id}
                  description={proposal.description}
                  files={proposal.files.map((f) => ({
                    path: f.path,
                    operation: f.operation,
                    diff_preview: f.diff_preview,
                    lines_added: f.lines_added,
                    lines_removed: f.lines_removed,
                  }))}
                  status={proposal.status}
                  autoApplied={proposal.auto_applied}
                  onStatusChange={onProposalStatusChange}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
