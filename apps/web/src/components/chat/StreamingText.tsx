'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface StreamingTextProps {
  text: string
  isStreaming?: boolean
}

export function StreamingText({ text, isStreaming = false }: StreamingTextProps) {
  return (
    <div className="prose prose-sm max-w-none prose-headings:mt-3 prose-headings:mb-2 prose-p:my-1 prose-ul:my-1 prose-li:my-0">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      {isStreaming && (
        <span className="inline-block w-2 h-4 ml-1 bg-blue-600 animate-pulse" />
      )}
    </div>
  )
}
