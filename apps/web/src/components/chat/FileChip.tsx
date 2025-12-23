'use client'

import { type FileReference } from '@/lib/chat-api'

interface FileChipProps {
  fileRef: FileReference
}

export function FileChip({ fileRef }: FileChipProps) {
  const handleClick = () => {
    // Construct obsidian:// URI
    let uri = `obsidian://open?vault=Obsidian-Private&file=${encodeURIComponent(fileRef.path)}`

    if (fileRef.line) {
      uri += `&line=${fileRef.line}`
    }

    if (fileRef.heading) {
      uri += `&heading=${encodeURIComponent(fileRef.heading)}`
    }

    window.location.href = uri
  }

  const fileName = fileRef.path.split('/').pop() || fileRef.path
  const displayText = fileRef.heading
    ? `${fileName}#${fileRef.heading}`
    : fileName

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 rounded transition-colors"
      title={`Open ${fileRef.path}${fileRef.line ? ` (line ${fileRef.line})` : ''}`}
    >
      <svg
        className="w-3 h-3"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      <span className="font-mono">{displayText}</span>
    </button>
  )
}
