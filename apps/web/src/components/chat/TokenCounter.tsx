'use client'

import { useState, useEffect, useMemo } from 'react'

interface TokenCounterProps {
  sessionTokens: {
    input: number
    output: number
    cacheRead?: number
    cacheCreation?: number
  }
  currentDraft: string
  model: string
}

// Model pricing per 1M tokens (input, output, cacheRead, cacheCreation)
const MODEL_PRICING: Record<string, { input: number; output: number; cacheRead: number; cacheCreation: number }> = {
  'claude-opus-4-5-20251101': { input: 15.0, output: 75.0, cacheRead: 1.5, cacheCreation: 18.75 },
  'claude-sonnet-4-5-20250929': { input: 3.0, output: 15.0, cacheRead: 0.30, cacheCreation: 3.75 },
  'claude-haiku-4-5-20251001': { input: 1.0, output: 5.0, cacheRead: 0.10, cacheCreation: 1.25 },
  'claude-3-5-haiku-20241022': { input: 0.80, output: 4.0, cacheRead: 0.08, cacheCreation: 1.0 },
  'claude-sonnet-4-20250514': { input: 3.0, output: 15.0, cacheRead: 0.30, cacheCreation: 3.75 },
}

// Context window sizes per model
const MODEL_CONTEXT_WINDOWS: Record<string, number> = {
  'claude-opus-4-5-20251101': 200_000,
  'claude-sonnet-4-5-20250929': 200_000,
  'claude-haiku-4-5-20251001': 200_000,
  'claude-3-5-haiku-20241022': 200_000,
  'claude-sonnet-4-20250514': 200_000,
}

// Simple token estimation (approximation)
function estimateTokens(text: string): number {
  if (!text) return 0
  // Rough approximation: ~4 characters per token for English text
  return Math.ceil(text.length / 4)
}

function formatTokens(count: number): string {
  if (count >= 1_000_000) {
    return `${(count / 1_000_000).toFixed(1)}M`
  } else if (count >= 1_000) {
    return `${(count / 1_000).toFixed(1)}K`
  }
  return count.toString()
}

function formatCost(cost: number): string {
  if (cost < 0.01) {
    return `$${cost.toFixed(4)}`
  } else if (cost < 1) {
    return `$${cost.toFixed(2)}`
  }
  return `$${cost.toFixed(2)}`
}

function calculateCost(
  model: string,
  inputTokens: number,
  outputTokens: number,
  cacheReadTokens: number = 0,
  cacheCreationTokens: number = 0
): number {
  const pricing = MODEL_PRICING[model] || { input: 3.0, output: 15.0, cacheRead: 0.3, cacheCreation: 3.75 }
  const inputCost = (inputTokens / 1_000_000) * pricing.input
  const outputCost = (outputTokens / 1_000_000) * pricing.output
  const cacheReadCost = (cacheReadTokens / 1_000_000) * pricing.cacheRead
  const cacheCreationCost = (cacheCreationTokens / 1_000_000) * pricing.cacheCreation
  return inputCost + outputCost + cacheReadCost + cacheCreationCost
}

export function TokenCounter({ sessionTokens, currentDraft, model }: TokenCounterProps) {
  const [expanded, setExpanded] = useState(false)
  const [draftTokens, setDraftTokens] = useState(0)

  // Debounced token estimation for current draft
  useEffect(() => {
    const timer = setTimeout(() => {
      setDraftTokens(estimateTokens(currentDraft))
    }, 300)
    return () => clearTimeout(timer)
  }, [currentDraft])

  const totalTokens = sessionTokens.input + sessionTokens.output
  const cacheReadTokens = sessionTokens.cacheRead || 0
  const cacheCreationTokens = sessionTokens.cacheCreation || 0
  const contextWindowSize = MODEL_CONTEXT_WINDOWS[model] || 200_000
  const contextUsed = totalTokens + draftTokens
  const contextPercent = (contextUsed / contextWindowSize) * 100

  // Calculate session cost dynamically
  const sessionCost = useMemo(
    () => calculateCost(model, sessionTokens.input, sessionTokens.output, cacheReadTokens, cacheCreationTokens),
    [model, sessionTokens.input, sessionTokens.output, cacheReadTokens, cacheCreationTokens]
  )

  // Determine color based on usage
  const usageColor = useMemo(() => {
    if (contextPercent > 80) return 'text-red-600'
    if (contextPercent > 50) return 'text-yellow-600'
    return 'text-gray-500'
  }, [contextPercent])

  if (totalTokens === 0 && draftTokens === 0) {
    return null // Don't show until there's something to display
  }

  return (
    <div className="relative">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`text-xs ${usageColor} hover:text-gray-700 transition-colors flex items-center gap-1`}
        title="Click for detailed token usage"
      >
        <span>{formatTokens(totalTokens)} tokens</span>
        <span className="text-gray-400">|</span>
        <span>{formatCost(sessionCost)}</span>
      </button>

      {expanded && (
        <div className="absolute bottom-full right-0 mb-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs z-10">
          <h4 className="font-medium text-gray-900 mb-2">Session Usage</h4>
          <div className="space-y-1">
            <div className="flex justify-between">
              <span className="text-gray-600">Input:</span>
              <span className="font-mono">{formatTokens(sessionTokens.input)} tokens</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Output:</span>
              <span className="font-mono">{formatTokens(sessionTokens.output)} tokens</span>
            </div>
            <div className="flex justify-between border-t pt-1 mt-1">
              <span className="text-gray-600">Total:</span>
              <span className="font-mono font-medium">{formatTokens(totalTokens)} tokens</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Cost:</span>
              <span className="font-mono font-medium">{formatCost(sessionCost)}</span>
            </div>
            {(cacheReadTokens > 0 || cacheCreationTokens > 0) && (
              <div className="flex justify-between text-green-600">
                <span>Cache:</span>
                <span className="font-mono">{formatTokens(cacheReadTokens)} read / {formatTokens(cacheCreationTokens)} write</span>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t">
            <div className="flex justify-between text-gray-600 mb-1">
              <span>Current message:</span>
              <span className="font-mono">~{formatTokens(draftTokens)} tokens</span>
            </div>
            <div className="flex justify-between text-gray-600">
              <span>Context window:</span>
              <span className={`font-mono ${usageColor}`}>
                {formatTokens(contextUsed)} / {formatTokens(contextWindowSize)} ({contextPercent.toFixed(1)}%)
              </span>
            </div>
            <div className="mt-2 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  contextPercent > 80
                    ? 'bg-red-500'
                    : contextPercent > 50
                    ? 'bg-yellow-500'
                    : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(contextPercent, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
