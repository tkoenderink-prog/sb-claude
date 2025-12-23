'use client'

import { useState } from 'react'
import { type ToolCall } from '@/lib/chat-api'

interface ToolCallCardProps {
  toolCall: ToolCall
}

export function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const statusColors = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    running: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    failed: 'bg-red-100 text-red-800 border-red-200',
  }

  const statusIcons = {
    pending: '⏳',
    running: '⚙️',
    completed: '✓',
    failed: '✗',
  }

  const status = toolCall.status || 'pending'

  return (
    <div className={`border rounded-lg overflow-hidden ${statusColors[status]}`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:opacity-80 transition-opacity"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">{statusIcons[status]}</span>
          <span className="font-medium text-sm">{toolCall.tool}</span>
          <span className="text-xs opacity-70">{status}</span>
        </div>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 border-t border-current border-opacity-20">
          <div className="mt-2">
            <div className="text-xs font-semibold mb-1">Arguments:</div>
            <pre className="text-xs bg-white bg-opacity-50 p-2 rounded overflow-x-auto">
              {JSON.stringify(toolCall.arguments, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}
