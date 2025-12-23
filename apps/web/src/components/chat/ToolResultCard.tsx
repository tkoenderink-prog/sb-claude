'use client'

import { useState } from 'react'
import { type ToolResult } from '@/lib/chat-api'

interface ToolResultCardProps {
  toolResult: ToolResult
}

export function ToolResultCard({ toolResult }: ToolResultCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const hasError = !!toolResult.error
  const cardColor = hasError
    ? 'bg-red-50 border-red-200 text-red-900'
    : 'bg-green-50 border-green-200 text-green-900'

  return (
    <div className={`border rounded-lg overflow-hidden ${cardColor}`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:opacity-80 transition-opacity"
      >
        <div className="flex items-center gap-2">
          <span className="text-sm">{hasError ? '✗' : '✓'}</span>
          <span className="font-medium text-sm">
            {hasError ? 'Tool Failed' : 'Tool Result'}
          </span>
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
          {hasError ? (
            <div className="mt-2">
              <div className="text-xs font-semibold mb-1">Error:</div>
              <div className="text-xs bg-white bg-opacity-50 p-2 rounded">
                {toolResult.error}
              </div>
            </div>
          ) : (
            <div className="mt-2">
              <div className="text-xs font-semibold mb-1">Result:</div>
              <pre className="text-xs bg-white bg-opacity-50 p-2 rounded overflow-x-auto max-h-48">
                {typeof toolResult.result === 'string'
                  ? toolResult.result
                  : JSON.stringify(toolResult.result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
