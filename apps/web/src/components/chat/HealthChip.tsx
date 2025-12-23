'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'

type HealthStatus = 'healthy' | 'slow' | 'error'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function HealthChip() {
  const router = useRouter()
  const [status, setStatus] = useState<HealthStatus>('healthy')
  const [lastErrorTime, setLastErrorTime] = useState<number | null>(null)
  const [isHovered, setIsHovered] = useState(false)

  const checkHealth = useCallback(async () => {
    const startTime = Date.now()
    try {
      const res = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        cache: 'no-store',
      })
      const elapsed = Date.now() - startTime

      if (!res.ok) {
        setStatus('error')
        setLastErrorTime(Date.now())
        return
      }

      // Check if we had an error in the last 5 minutes
      const fiveMinutesAgo = Date.now() - 5 * 60 * 1000
      if (lastErrorTime && lastErrorTime > fiveMinutesAgo) {
        setStatus('slow')
        return
      }

      // Check response time
      if (elapsed > 500) {
        setStatus('slow')
      } else {
        setStatus('healthy')
      }
    } catch {
      setStatus('error')
      setLastErrorTime(Date.now())
    }
  }, [lastErrorTime])

  useEffect(() => {
    // Initial check
    checkHealth()

    // Poll every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkHealth])

  const statusConfig = {
    healthy: {
      color: 'bg-green-500',
      text: 'Backend healthy',
    },
    slow: {
      color: 'bg-yellow-500',
      text: 'Backend slow or recovering',
    },
    error: {
      color: 'bg-red-500',
      text: 'Backend unreachable',
    },
  }

  const config = statusConfig[status]

  return (
    <div className="fixed top-4 left-4 z-50">
      <button
        onClick={() => router.push('/dashboard')}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className="flex items-center gap-2 px-2 py-1 bg-white border rounded-full shadow-sm hover:shadow transition-shadow"
        title={config.text}
      >
        <span className={`w-2.5 h-2.5 rounded-full ${config.color}`} />
        {isHovered && (
          <span className="text-xs text-gray-600 pr-1">{config.text}</span>
        )}
      </button>
    </div>
  )
}
