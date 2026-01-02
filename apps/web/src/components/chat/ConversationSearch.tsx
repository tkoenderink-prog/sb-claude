'use client'

import { useState, useEffect, useCallback } from 'react'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/react/24/outline'
import { API_BASE } from '@/lib/api'

interface SearchResult {
  session_id: string
  title: string | null
  created_at: string
  snippet: string
  message_count: number
  rank: number
}

interface ConversationSearchProps {
  onSelectSession: (sessionId: string) => void
  onSearchModeChange?: (isSearching: boolean) => void
}

export function ConversationSearch({ onSelectSession, onSearchModeChange }: ConversationSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      setIsSearching(false)
      onSearchModeChange?.(false)
      return
    }

    setIsSearching(true)
    onSearchModeChange?.(true)

    const timer = setTimeout(async () => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await fetch(
          `${API_BASE}/search/conversations?query=${encodeURIComponent(query)}&limit=20`
        )
        if (!response.ok) {
          throw new Error('Search failed')
        }
        const data = await response.json()
        setResults(data.results || [])
      } catch (err) {
        console.error('Search error:', err)
        setError('Search failed')
        setResults([])
      } finally {
        setIsLoading(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query, onSearchModeChange])

  const clearSearch = useCallback(() => {
    setQuery('')
    setResults([])
    setIsSearching(false)
    onSearchModeChange?.(false)
  }, [onSearchModeChange])

  const handleSelectResult = useCallback(
    (sessionId: string) => {
      onSelectSession(sessionId)
      clearSearch()
    },
    [onSelectSession, clearSearch]
  )

  return (
    <div className="relative">
      {/* Search Input */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search conversations..."
          className="w-full pl-9 pr-8 py-2 text-sm border border-gray-200 rounded-lg
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                     bg-white"
        />
        {query && (
          <button
            onClick={clearSearch}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-100 rounded"
          >
            <XMarkIcon className="w-4 h-4 text-gray-400" />
          </button>
        )}
      </div>

      {/* Search Results */}
      {isSearching && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-80 overflow-y-auto">
          {isLoading && (
            <div className="p-4 text-center text-sm text-gray-500">
              Searching...
            </div>
          )}

          {error && (
            <div className="p-4 text-center text-sm text-red-500">
              {error}
            </div>
          )}

          {!isLoading && !error && results.length === 0 && query.trim() && (
            <div className="p-4 text-center text-sm text-gray-500">
              No conversations found
            </div>
          )}

          {!isLoading && results.length > 0 && (
            <ul className="divide-y divide-gray-100">
              {results.map((result) => (
                <li key={result.session_id}>
                  <button
                    onClick={() => handleSelectResult(result.session_id)}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {result.title || 'Untitled Chat'}
                        </h4>
                        <p
                          className="text-xs text-gray-600 mt-1 line-clamp-2"
                          dangerouslySetInnerHTML={{ __html: result.snippet }}
                        />
                      </div>
                      <div className="text-xs text-gray-400 whitespace-nowrap">
                        {new Date(result.created_at).toLocaleDateString()}
                      </div>
                    </div>
                    <div className="mt-1 text-xs text-gray-400">
                      {result.message_count} messages
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
