'use client'

import { type ChatMessage } from '@/lib/chat-api'
import { FileChip } from './FileChip'
import { ToolCallCard } from './ToolCallCard'
import { ToolResultCard } from './ToolResultCard'
import { StreamingText } from './StreamingText'
import { ArtifactCard } from './ArtifactCard'
import { SubagentCard } from './SubagentCard'
import { CouncilResponse } from './CouncilResponse'
import { useClientTime } from '@/hooks/useClientDate'

interface MessageBubbleProps {
  message: ChatMessage
  isStreaming?: boolean
}

export function MessageBubble({ message, isStreaming = false }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const formattedTime = useClientTime(message.timestamp)

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-3xl ${isUser ? 'ml-12' : 'mr-12'}`}>
        {/* Message header */}
        <div className={`flex items-center gap-2 mb-1 ${isUser ? 'justify-end' : 'justify-start'}`}>
          <span className="text-xs text-gray-500">
            {message.role === 'user' ? 'You' : 'Assistant'}
          </span>
          <span className="text-xs text-gray-400">
            {formattedTime}
          </span>
        </div>

        {/* Message content */}
        <div
          className={`px-4 py-3 rounded-lg ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 text-gray-900 border border-gray-200'
          }`}
        >
          {isUser ? (
            <div className="whitespace-pre-wrap">{message.content}</div>
          ) : (
            <StreamingText text={message.content} isStreaming={isStreaming} />
          )}
        </div>

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.tool_calls.map((toolCall) => (
              <ToolCallCard key={toolCall.id} toolCall={toolCall} />
            ))}
          </div>
        )}

        {/* Tool results */}
        {message.tool_results && message.tool_results.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.tool_results.map((toolResult) => (
              <ToolResultCard key={toolResult.tool_call_id} toolResult={toolResult} />
            ))}
          </div>
        )}

        {/* File references */}
        {message.file_refs && message.file_refs.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {message.file_refs.map((fileRef, index) => (
              <FileChip key={index} fileRef={fileRef} />
            ))}
          </div>
        )}

        {/* Artifacts */}
        {message.artifacts && message.artifacts.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.artifacts.map((artifact) => (
              <ArtifactCard key={artifact.id} artifact={artifact} />
            ))}
          </div>
        )}

        {/* Subagents */}
        {message.subagents && message.subagents.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.subagents.map((subagent) => (
              <SubagentCard key={subagent.id} subagent={subagent} />
            ))}
          </div>
        )}

        {/* Councils */}
        {message.councils && message.councils.length > 0 && (
          <div className="mt-2 space-y-2">
            {message.councils.map((council, index) => (
              <CouncilResponse
                key={index}
                response={{
                  councilName: council.council_name,
                  members: council.members,
                  synthesis: council.synthesis,
                  orchestrator: council.orchestrator,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
