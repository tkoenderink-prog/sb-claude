'use client'

import { useState } from 'react'
import { useProposal, useApproveProposal, useRejectProposal } from '@/hooks/useProposals'
import { DiffViewer } from './DiffViewer'

interface ProposalCardProps {
  proposalId: string
  description: string
  files: Array<{
    path: string
    operation: 'create' | 'modify' | 'delete'
    diff_preview?: string
    lines_added?: number
    lines_removed?: number
  }>
  status: 'pending' | 'approved' | 'rejected' | 'applied'
  autoApplied: boolean
  onStatusChange?: (proposalId: string, newStatus: 'applied' | 'rejected') => void
}

function FileIcon({ operation }: { operation: 'create' | 'modify' | 'delete' }) {
  if (operation === 'create') {
    return (
      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
      </svg>
    )
  }
  if (operation === 'delete') {
    return (
      <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
      </svg>
    )
  }
  return (
    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
    </svg>
  )
}

function OperationBadge({ operation }: { operation: 'create' | 'modify' | 'delete' }) {
  const styles = {
    create: 'bg-green-100 text-green-800',
    modify: 'bg-blue-100 text-blue-800',
    delete: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${styles[operation]}`}>
      {operation}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-800',
    approved: 'bg-green-100 text-green-800',
    rejected: 'bg-gray-100 text-gray-800',
    applied: 'bg-green-100 text-green-800',
  }
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded ${styles[status] || 'bg-gray-100'}`}>
      {status}
    </span>
  )
}

export function ProposalCard({ proposalId, description, files, status, autoApplied, onStatusChange }: ProposalCardProps) {
  const [showDiff, setShowDiff] = useState(false)
  const [selectedFileIndex, setSelectedFileIndex] = useState(0)
  const { data: fullProposal } = useProposal(showDiff ? proposalId : null)
  const approveMutation = useApproveProposal()
  const rejectMutation = useRejectProposal()

  const isPending = status === 'pending'
  const isLoading = approveMutation.isPending || rejectMutation.isPending

  const handleViewDiff = (index: number) => {
    setSelectedFileIndex(index)
    setShowDiff(true)
  }

  const handleApprove = () => {
    approveMutation.mutate(proposalId, {
      onSuccess: () => {
        onStatusChange?.(proposalId, 'applied')
      }
    })
  }

  const handleReject = () => {
    rejectMutation.mutate(proposalId, {
      onSuccess: () => {
        onStatusChange?.(proposalId, 'rejected')
      }
    })
  }

  const bgColor = status === 'pending' ? 'bg-amber-50 border-amber-200' :
                  status === 'applied' ? 'bg-green-50 border-green-200' :
                  status === 'rejected' ? 'bg-gray-50 border-gray-200' :
                  'bg-white border-gray-200'

  return (
    <>
      <div className={`border rounded-lg p-4 ${bgColor}`}>
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="font-medium text-gray-900">File Proposal</span>
            <StatusBadge status={status} />
            {autoApplied && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-purple-100 text-purple-800">
                auto-applied
              </span>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 mb-3">{description}</p>

        {/* Files List */}
        <div className="space-y-2 mb-3">
          {files.map((file, index) => (
            <div key={file.path} className="flex items-center justify-between bg-white/60 rounded px-3 py-2">
              <div className="flex items-center gap-2">
                <FileIcon operation={file.operation} />
                <span className="text-sm font-mono text-gray-800">{file.path}</span>
                <OperationBadge operation={file.operation} />
              </div>
              <div className="flex items-center gap-3">
                {file.lines_added !== undefined && file.lines_removed !== undefined && (
                  <span className="text-xs text-gray-500">
                    <span className="text-green-600">+{file.lines_added}</span>
                    {' / '}
                    <span className="text-red-600">-{file.lines_removed}</span>
                  </span>
                )}
                {file.operation !== 'delete' && (
                  <button
                    onClick={() => handleViewDiff(index)}
                    className="text-xs text-blue-600 hover:text-blue-800"
                  >
                    View Diff
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        {isPending && (
          <div className="flex gap-2">
            <button
              onClick={handleApprove}
              disabled={isLoading}
              className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded hover:bg-green-700 disabled:opacity-50"
            >
              {approveMutation.isPending ? 'Applying...' : 'Approve & Apply'}
            </button>
            <button
              onClick={handleReject}
              disabled={isLoading}
              className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
            >
              {rejectMutation.isPending ? 'Rejecting...' : 'Reject'}
            </button>
          </div>
        )}
      </div>

      {/* Diff Viewer Modal */}
      {showDiff && fullProposal && fullProposal.files[selectedFileIndex] && (
        <DiffViewer
          originalContent={fullProposal.files[selectedFileIndex].original_content || ''}
          newContent={fullProposal.files[selectedFileIndex].proposed_content || ''}
          fileName={fullProposal.files[selectedFileIndex].file_path}
          onClose={() => setShowDiff(false)}
        />
      )}
    </>
  )
}
