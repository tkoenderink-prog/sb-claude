'use client'

import { type Artifact } from '@/lib/chat-api'
import { useClientTime, useClientDateTime } from '@/hooks/useClientDate'

interface ArtifactCardProps {
  artifact: Artifact
}

export function ArtifactCard({ artifact }: ArtifactCardProps) {
  const formattedTime = useClientTime(artifact.created_at)
  const formattedDateTime = useClientDateTime(artifact.created_at)

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
  }

  const getTypeIcon = (type: Artifact['type']): string => {
    switch (type) {
      case 'report':
        return '\u{1F4CA}' // Bar chart
      case 'analysis':
        return '\u{1F50D}' // Magnifying glass
      case 'export':
        return '\u{1F4E4}' // Outbox
      case 'code':
        return '\u{1F4BB}' // Computer
      case 'other':
      default:
        return '\u{1F4C4}' // Document
    }
  }

  const getTypeColor = (type: Artifact['type']): string => {
    switch (type) {
      case 'report':
        return 'bg-purple-50 text-purple-700 border-purple-200'
      case 'analysis':
        return 'bg-blue-50 text-blue-700 border-blue-200'
      case 'export':
        return 'bg-green-50 text-green-700 border-green-200'
      case 'code':
        return 'bg-orange-50 text-orange-700 border-orange-200'
      case 'other':
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200'
    }
  }

  return (
    <div className={`border rounded-lg p-3 ${getTypeColor(artifact.type)}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <span className="text-xl flex-shrink-0" aria-label={artifact.type}>
            {getTypeIcon(artifact.type)}
          </span>
          <div className="flex-1 min-w-0">
            <div className="font-medium text-sm truncate" title={artifact.name}>
              {artifact.name}
            </div>
            <div className="flex items-center gap-2 mt-1 text-xs opacity-70">
              <span className="capitalize">{artifact.type}</span>
              <span>•</span>
              <span>{formatBytes(artifact.size_bytes)}</span>
              <span>•</span>
              <span title={formattedDateTime}>
                {formattedTime}
              </span>
            </div>
            {artifact.mime_type && (
              <div className="text-xs opacity-60 mt-1 font-mono">
                {artifact.mime_type}
              </div>
            )}
          </div>
        </div>
        <a
          href={artifact.download_url}
          download={artifact.name}
          className="flex-shrink-0 px-3 py-1.5 text-xs font-medium bg-white hover:bg-opacity-80 border border-current rounded transition-colors"
          title={`Download ${artifact.name}`}
        >
          <svg
            className="w-4 h-4 inline-block mr-1"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
          Download
        </a>
      </div>
    </div>
  )
}
