'use client'

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

interface GitCommit {
  message: string
  author: string
  date: string
  sha: string
}

interface GitStatus {
  is_git_repo: boolean
  last_commit: GitCommit | null
  uncommitted_files: string[]
  is_dirty: boolean
  remote_ahead: number
  remote_behind: number
}

export function VaultGitCard() {
  const queryClient = useQueryClient()
  const [isExpanded, setIsExpanded] = useState(false)

  const { data: gitStatus, isLoading } = useQuery<GitStatus>({
    queryKey: ['vault-git-status'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/vault/git/status')
      if (!res.ok) throw new Error('Failed to fetch git status')
      return res.json()
    },
    refetchInterval: 30000,
  })

  const syncMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('http://localhost:8000/vault/git/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.detail || 'Sync failed')
      }
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['vault-git-status'] })
    },
  })

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          📦 Vault Git Status
        </div>
        <div className="mt-4 text-sm text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!gitStatus?.is_git_repo) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          📦 Vault Git Status
        </div>
        <div className="mt-4 text-sm text-gray-500">
          Vault is not a git repository
        </div>
      </div>
    )
  }

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`
    return `${Math.floor(seconds / 86400)} days ago`
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          📦 Vault Git Status
        </div>
        {gitStatus.is_dirty && (
          <span className="rounded-full bg-yellow-100 px-2 py-1 text-xs font-medium text-yellow-800">
            {gitStatus.uncommitted_files.length} uncommitted
          </span>
        )}
      </div>

      <div className="mt-4 space-y-4">
        {gitStatus.last_commit && (
          <div>
            <div className="text-sm font-medium text-gray-700">Last Commit:</div>
            <div className="mt-1 text-sm text-gray-600">
              {gitStatus.last_commit.message}
            </div>
            <div className="mt-1 text-xs text-gray-500">
              by {gitStatus.last_commit.author} • {getRelativeTime(gitStatus.last_commit.date)} • <span className="font-mono">{gitStatus.last_commit.sha}</span>
            </div>
          </div>
        )}

        {gitStatus.is_dirty && (
          <div>
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-yellow-700">
                Uncommitted Changes: {gitStatus.uncommitted_files.length} files
              </div>
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                {isExpanded ? 'Hide' : 'Show'}
              </button>
            </div>
            {isExpanded && (
              <div className="mt-2 space-y-1">
                {gitStatus.uncommitted_files.slice(0, 10).map((file, i) => (
                  <div key={i} className="truncate text-xs text-gray-600">
                    • {file}
                  </div>
                ))}
                {gitStatus.uncommitted_files.length > 10 && (
                  <div className="text-xs text-gray-500">
                    +{gitStatus.uncommitted_files.length - 10} more...
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-700">Remote:</span>
          {gitStatus.remote_ahead > 0 && (
            <span className="text-blue-600">↑ {gitStatus.remote_ahead} ahead</span>
          )}
          {gitStatus.remote_behind > 0 && (
            <span className="text-orange-600">↓ {gitStatus.remote_behind} behind</span>
          )}
          {gitStatus.remote_ahead === 0 && gitStatus.remote_behind === 0 && (
            <span className="text-green-600">✓ In sync</span>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {syncMutation.isPending ? 'Syncing...' : 'Commit & Push'}
          </button>
          {syncMutation.isError && (
            <span className="text-sm text-red-600">
              {(syncMutation.error as Error).message}
            </span>
          )}
          {syncMutation.isSuccess && (
            <span className="text-sm text-green-600">✓ Synced successfully</span>
          )}
        </div>
      </div>
    </div>
  )
}
