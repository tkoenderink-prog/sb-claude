'use client'

import { useState } from 'react'
import { type Subagent } from '@/lib/chat-api'

interface SubagentCardProps {
  subagent: Subagent
}

export function SubagentCard({ subagent }: SubagentCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const statusColors = {
    running: 'bg-blue-100 text-blue-800 border-blue-200',
    completed: 'bg-green-100 text-green-800 border-green-200',
    failed: 'bg-red-100 text-red-800 border-red-200',
  }

  const statusIcons = {
    running: '⚙️',
    completed: '✓',
    failed: '✗',
  }

  const getTypeBadge = (type: string): string => {
    // Map subagent type to readable badge
    const typeMap: Record<string, string> = {
      calendar_analyst: 'Calendar',
      task_analyst: 'Tasks',
      knowledge_searcher: 'Search',
      journal_analyst: 'Journal',
      general_purpose: 'General',
    }
    return typeMap[type] || type
  }

  const getTypeColor = (type: string): string => {
    const colorMap: Record<string, string> = {
      calendar_analyst: 'bg-purple-50 text-purple-700 border-purple-300',
      task_analyst: 'bg-orange-50 text-orange-700 border-orange-300',
      knowledge_searcher: 'bg-blue-50 text-blue-700 border-blue-300',
      journal_analyst: 'bg-green-50 text-green-700 border-green-300',
      general_purpose: 'bg-gray-50 text-gray-700 border-gray-300',
    }
    return colorMap[type] || 'bg-gray-50 text-gray-700 border-gray-300'
  }

  return (
    <div className={`border rounded-lg overflow-hidden ${statusColors[subagent.status]}`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:opacity-80 transition-opacity"
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-sm flex-shrink-0">
            {statusIcons[subagent.status]}
          </span>
          <span
            className={`px-2 py-0.5 text-xs font-medium rounded border ${getTypeColor(subagent.type)}`}
          >
            {getTypeBadge(subagent.type)}
          </span>
          <span className="text-sm flex-1 min-w-0 truncate" title={subagent.task}>
            {subagent.task}
          </span>
          {subagent.status === 'running' && (
            <div className="flex-shrink-0 flex gap-0.5">
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" style={{ animationDelay: '300ms' }} />
            </div>
          )}
        </div>
        <svg
          className={`w-4 h-4 transition-transform flex-shrink-0 ml-2 ${isExpanded ? 'rotate-180' : ''}`}
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
          <div className="mt-2 space-y-2">
            <div>
              <div className="text-xs font-semibold mb-1">Task:</div>
              <div className="text-xs bg-white bg-opacity-50 p-2 rounded">
                {subagent.task}
              </div>
            </div>

            {subagent.status === 'completed' && subagent.result && (
              <div>
                <div className="text-xs font-semibold mb-1">Result:</div>
                <pre className="text-xs bg-white bg-opacity-50 p-2 rounded overflow-x-auto whitespace-pre-wrap">
                  {subagent.result}
                </pre>
              </div>
            )}

            {subagent.status === 'failed' && subagent.error && (
              <div>
                <div className="text-xs font-semibold mb-1 text-red-700">Error:</div>
                <div className="text-xs bg-white bg-opacity-50 p-2 rounded text-red-700">
                  {subagent.error}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
