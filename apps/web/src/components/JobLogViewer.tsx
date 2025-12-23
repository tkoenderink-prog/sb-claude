'use client'

import { useEffect, useState, useRef } from 'react'
import { streamJobLogs, type JobLogEvent, type JobStatusEvent } from '@/lib/api'

interface JobLogViewerProps {
  jobId: string
  onComplete?: () => void
}

export function JobLogViewer({ jobId, onComplete }: JobLogViewerProps) {
  const [logs, setLogs] = useState<JobLogEvent[]>([])
  const [status, setStatus] = useState<'connecting' | 'streaming' | 'completed' | 'failed' | 'error'>('connecting')
  const [error, setError] = useState<string | null>(null)
  const logContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const cleanup = streamJobLogs(
      jobId,
      (log) => {
        setLogs((prev) => [...prev, log])
        setStatus('streaming')
      },
      (statusEvent) => {
        if (statusEvent.status === 'completed') {
          setStatus('completed')
          onComplete?.()
        } else if (statusEvent.status === 'failed') {
          setStatus('failed')
        } else if (statusEvent.status === 'started') {
          setStatus('streaming')
        }
      },
      (err) => {
        setError(err.message)
        setStatus('error')
      }
    )

    return cleanup
  }, [jobId, onComplete])

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight
    }
  }, [logs])

  const levelColors = {
    info: 'text-blue-600',
    warn: 'text-yellow-600',
    error: 'text-red-600',
    debug: 'text-gray-500',
  }

  const statusColors = {
    connecting: 'bg-yellow-100 text-yellow-800',
    streaming: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    error: 'bg-red-100 text-red-800',
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-100 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">Job Logs</span>
          <span className="font-mono text-xs text-gray-500">{jobId.substring(0, 8)}...</span>
        </div>
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[status]}`}>
          {status}
        </span>
      </div>

      {/* Log content */}
      <div
        ref={logContainerRef}
        className="bg-gray-900 text-gray-100 p-4 font-mono text-sm max-h-64 overflow-y-auto"
      >
        {logs.length === 0 && status === 'connecting' && (
          <div className="text-gray-400 animate-pulse">Connecting to log stream...</div>
        )}

        {logs.map((log, index) => (
          <div key={index} className="flex gap-2 mb-1">
            <span className="text-gray-500 text-xs">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            <span className={`uppercase text-xs font-bold ${levelColors[log.level]}`}>
              [{log.level}]
            </span>
            <span>{log.message}</span>
          </div>
        ))}

        {error && (
          <div className="text-red-400 mt-2">Error: {error}</div>
        )}

        {status === 'completed' && (
          <div className="text-green-400 mt-2">Job completed successfully</div>
        )}

        {status === 'failed' && (
          <div className="text-red-400 mt-2">Job failed</div>
        )}
      </div>
    </div>
  )
}
