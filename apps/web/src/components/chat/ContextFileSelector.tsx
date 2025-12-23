'use client'

import { useState, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface VaultFile {
  name: string
  path: string
  is_directory: boolean
  size?: number
}

interface ContextFile {
  id: string
  file_path: string
  display_name: string
  token_count: number
}

// Pending file for pre-session selection
export interface PendingContextFile {
  path: string
  name: string
}

interface ContextFileSelectorProps {
  sessionId: string | null
  isOpen: boolean
  onClose: () => void
  // For pre-session file selection
  pendingFiles?: PendingContextFile[]
  onPendingFilesChange?: (files: PendingContextFile[]) => void
}

export function ContextFileSelector({
  sessionId,
  isOpen,
  onClose,
  pendingFiles = [],
  onPendingFilesChange,
}: ContextFileSelectorProps) {
  const [currentPath, setCurrentPath] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const queryClient = useQueryClient()

  // Are we in pending mode (no session yet)?
  const isPendingMode = !sessionId && onPendingFilesChange !== undefined

  // Fetch current directory contents
  const { data: browseData, isLoading: isBrowsing } = useQuery({
    queryKey: ['vault-browse', currentPath],
    queryFn: async () => {
      const params = currentPath ? `?path=${encodeURIComponent(currentPath)}` : ''
      const res = await fetch(`${API_BASE}/vault/browse${params}`)
      if (!res.ok) throw new Error('Failed to browse vault')
      return res.json()
    },
    enabled: isOpen && !isSearching,
  })

  // Search vault files
  const { data: searchData, isLoading: isSearchLoading } = useQuery({
    queryKey: ['vault-search', searchQuery],
    queryFn: async () => {
      const res = await fetch(
        `${API_BASE}/vault/search-files?query=${encodeURIComponent(searchQuery)}`
      )
      if (!res.ok) throw new Error('Failed to search vault')
      return res.json()
    },
    enabled: isOpen && isSearching && searchQuery.length > 0,
  })

  // Fetch context files for current session
  const { data: contextFiles } = useQuery({
    queryKey: ['context-files', sessionId],
    queryFn: async () => {
      if (!sessionId) return { files: [], total_tokens: 0 }
      const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/context`)
      if (!res.ok) throw new Error('Failed to load context files')
      return res.json()
    },
    enabled: isOpen && !!sessionId,
  })

  // Add file to context (when session exists)
  const addFile = useMutation({
    mutationFn: async (filePath: string) => {
      if (!sessionId) throw new Error('No session')
      const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/context`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: filePath }),
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Failed to add file')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['context-files', sessionId] })
    },
  })

  // Remove file from context (when session exists)
  const removeFile = useMutation({
    mutationFn: async (fileId: string) => {
      if (!sessionId) throw new Error('No session')
      const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/context/${fileId}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to remove file')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['context-files', sessionId] })
    },
  })

  // Handle adding file (either pending or to session)
  const handleAddFile = useCallback(
    (file: VaultFile) => {
      if (file.is_directory) {
        setCurrentPath(file.path)
        setIsSearching(false)
        setSearchQuery('')
        return
      }

      if (isPendingMode) {
        // Add to pending files
        if (!pendingFiles.some((f) => f.path === file.path)) {
          onPendingFilesChange?.([...pendingFiles, { path: file.path, name: file.name }])
        }
      } else if (sessionId) {
        // Add to session context
        addFile.mutate(file.path)
      }
    },
    [isPendingMode, pendingFiles, onPendingFilesChange, sessionId, addFile]
  )

  // Handle removing file
  const handleRemoveFile = useCallback(
    (filePathOrId: string, isPending: boolean) => {
      if (isPending) {
        onPendingFilesChange?.(pendingFiles.filter((f) => f.path !== filePathOrId))
      } else {
        removeFile.mutate(filePathOrId)
      }
    },
    [pendingFiles, onPendingFilesChange, removeFile]
  )

  // Check if file is already attached
  const isAttached = useCallback(
    (filePath: string) => {
      if (isPendingMode) {
        return pendingFiles.some((f) => f.path === filePath)
      }
      return contextFiles?.files?.some((f: ContextFile) => f.file_path === filePath)
    },
    [isPendingMode, pendingFiles, contextFiles]
  )

  // Handle search input
  const handleSearchChange = useCallback((value: string) => {
    setSearchQuery(value)
    setIsSearching(value.length > 0)
  }, [])

  // Navigate to directory
  const navigateTo = useCallback((path: string) => {
    setCurrentPath(path)
    setIsSearching(false)
    setSearchQuery('')
  }, [])

  // Navigate up
  const navigateUp = useCallback(() => {
    if (browseData?.parent_path !== null) {
      setCurrentPath(browseData?.parent_path || '')
    }
  }, [browseData?.parent_path])

  if (!isOpen) return null

  const files = isSearching ? searchData?.results : browseData?.items
  const loading = isBrowsing || isSearchLoading

  // Combined attached files (pending + session)
  const allAttachedFiles = isPendingMode
    ? pendingFiles.map((f) => ({
        id: f.path,
        file_path: f.path,
        display_name: f.name,
        isPending: true,
      }))
    : (contextFiles?.files || []).map((f: ContextFile) => ({
        ...f,
        isPending: false,
      }))

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">Add Context Files</h2>
            {isPendingMode && (
              <p className="text-xs text-amber-600 mt-1">
                Files will be attached when you send your first message
              </p>
            )}
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Search */}
        <div className="p-3 border-b">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search files..."
            className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Breadcrumb */}
        {!isSearching && (
          <div className="px-3 py-2 border-b flex items-center gap-2 text-sm text-gray-600 overflow-x-auto">
            <button onClick={() => navigateTo('')} className="hover:text-blue-600">
              Vault
            </button>
            {currentPath &&
              currentPath.split('/').map((part, i, arr) => (
                <span key={i} className="flex items-center gap-2">
                  <span>/</span>
                  <button
                    onClick={() => navigateTo(arr.slice(0, i + 1).join('/'))}
                    className="hover:text-blue-600 truncate max-w-32"
                  >
                    {part}
                  </button>
                </span>
              ))}
          </div>
        )}

        {/* File list */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-center text-gray-500">Loading...</div>
          ) : !files?.length ? (
            <div className="p-4 text-center text-gray-500">
              {isSearching ? 'No files found' : 'Empty directory'}
            </div>
          ) : (
            <ul className="divide-y">
              {/* Go up button */}
              {!isSearching && browseData?.parent_path !== null && (
                <li>
                  <button
                    onClick={navigateUp}
                    className="w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 text-left"
                  >
                    <svg
                      className="w-5 h-5 text-gray-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M11 17l-5-5m0 0l5-5m-5 5h12"
                      />
                    </svg>
                    <span className="text-gray-600">..</span>
                  </button>
                </li>
              )}
              {files.map((file: VaultFile) => (
                <li key={file.path}>
                  <button
                    onClick={() => handleAddFile(file)}
                    disabled={!file.is_directory && isAttached(file.path)}
                    className={`w-full px-4 py-3 flex items-center gap-3 hover:bg-gray-50 text-left ${
                      isAttached(file.path) ? 'opacity-50' : ''
                    }`}
                  >
                    {file.is_directory ? (
                      <svg className="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                      </svg>
                    ) : (
                      <svg
                        className="w-5 h-5 text-gray-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                        />
                      </svg>
                    )}
                    <span className="flex-1 truncate">{file.name}</span>
                    {!file.is_directory &&
                      (isAttached(file.path) ? (
                        <span className="text-xs text-green-600">Added</span>
                      ) : (
                        <svg
                          className="w-4 h-4 text-gray-400"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 4v16m8-8H4"
                          />
                        </svg>
                      ))}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Attached files */}
        {allAttachedFiles.length > 0 && (
          <div className="border-t p-3">
            <div className="text-xs text-gray-500 mb-2">
              {isPendingMode ? (
                <>Pending ({allAttachedFiles.length} files)</>
              ) : (
                <>
                  Attached ({contextFiles.files.length} files, ~
                  {contextFiles.total_tokens.toLocaleString()} tokens)
                </>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              {allAttachedFiles.map(
                (file: { id: string; file_path: string; display_name: string; isPending?: boolean }) => (
                  <span
                    key={file.id}
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded text-sm ${
                      file.isPending
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    <span className="truncate max-w-32">{file.display_name}</span>
                    <button
                      onClick={() => handleRemoveFile(file.isPending ? file.file_path : file.id, !!file.isPending)}
                      className={`rounded p-0.5 ${
                        file.isPending ? 'hover:bg-amber-200' : 'hover:bg-blue-200'
                      }`}
                    >
                      <svg
                        className="w-3 h-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </button>
                  </span>
                )
              )}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="p-3 border-t flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
