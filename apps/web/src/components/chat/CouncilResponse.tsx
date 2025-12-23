'use client'

import { useState } from 'react'

export interface CouncilMember {
  name: string
  icon: string
  response: string
}

export interface CouncilResponseData {
  councilName: string
  members: CouncilMember[]
  synthesis: string
  orchestrator?: string
}

interface CouncilResponseProps {
  response: CouncilResponseData
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function CouncilResponse({ response }: CouncilResponseProps) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-purple-200 rounded-lg overflow-hidden bg-purple-50 bg-opacity-50 mt-3">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 bg-purple-100 bg-opacity-60 flex items-center justify-between hover:bg-purple-200 hover:bg-opacity-60 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">🏛️</span>
          <span className="font-medium text-purple-900">{response.councilName}</span>
          <span className="text-sm text-purple-700">
            ({response.members.length} members consulted)
          </span>
        </div>
        <svg
          className={cn(
            'w-5 h-5 text-purple-700 transition-transform',
            expanded && 'rotate-180'
          )}
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

      {/* Member Responses (collapsible) */}
      {expanded && (
        <div className="border-t border-purple-200 divide-y divide-purple-200">
          {response.members.map((member, idx) => (
            <div key={idx} className="px-4 py-3 bg-white bg-opacity-50">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-base">{member.icon}</span>
                <span className="font-medium text-sm text-purple-900">{member.name}</span>
              </div>
              <div className="text-sm text-gray-700 pl-7 whitespace-pre-wrap">
                {member.response}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Synthesis (always visible) */}
      <div className="px-4 py-3 bg-white border-t border-purple-200">
        {response.orchestrator && (
          <div className="text-xs text-purple-700 font-medium mb-2">
            Synthesis by {response.orchestrator}
          </div>
        )}
        <div className="prose prose-sm max-w-none text-gray-900 whitespace-pre-wrap">
          {response.synthesis}
        </div>
      </div>
    </div>
  )
}
