'use client'

import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/api'

interface EnvironmentInfo {
  mode: 'local' | 'docker' | 'production'
  port: number
  in_container: boolean
  chroma_host: string
  chroma_port: number
}

interface HealthResponse {
  status: string
  version: string
  service: string
  environment: EnvironmentInfo
}

export function EnvironmentBadge() {
  const { data: health, isLoading, error } = useQuery<HealthResponse>({
    queryKey: ['health-env'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/health`)
      if (!res.ok) throw new Error('Failed to fetch health')
      return res.json()
    },
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 text-gray-500 text-sm">
        <span className="w-2 h-2 rounded-full bg-gray-400 animate-pulse" />
        Loading...
      </div>
    )
  }

  if (error || !health) {
    return (
      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-red-100 text-red-700 text-sm">
        <span className="w-2 h-2 rounded-full bg-red-500" />
        Offline
      </div>
    )
  }

  const env = health.environment
  const isDocker = env.mode === 'docker' || env.in_container
  const isLocal = env.mode === 'local' && !env.in_container

  // Determine badge color and icon based on mode
  const getBadgeStyles = () => {
    if (isDocker) {
      return {
        bg: 'bg-blue-100',
        text: 'text-blue-700',
        dot: 'bg-blue-500',
        label: 'Docker',
        icon: '🐳',
      }
    }
    if (isLocal) {
      return {
        bg: 'bg-green-100',
        text: 'text-green-700',
        dot: 'bg-green-500',
        label: 'Local',
        icon: '💻',
      }
    }
    return {
      bg: 'bg-purple-100',
      text: 'text-purple-700',
      dot: 'bg-purple-500',
      label: 'Production',
      icon: '🚀',
    }
  }

  const styles = getBadgeStyles()

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${styles.bg} ${styles.text} text-sm font-medium`}>
      <span className={`w-2 h-2 rounded-full ${styles.dot}`} />
      <span>{styles.icon}</span>
      <span>{styles.label}</span>
      <span className="text-xs opacity-70">:{env.port}</span>
    </div>
  )
}

export function EnvironmentCard() {
  const { data: health, isLoading, error } = useQuery<HealthResponse>({
    queryKey: ['health-env'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/health`)
      if (!res.ok) throw new Error('Failed to fetch health')
      return res.json()
    },
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          🌍 Environment
        </div>
        <div className="mt-4 text-sm text-gray-500">Loading...</div>
      </div>
    )
  }

  if (error || !health) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold text-red-900">
          🌍 Environment
        </div>
        <div className="mt-4 text-sm text-red-600">
          Backend offline - unable to fetch environment info
        </div>
      </div>
    )
  }

  const env = health.environment
  const isDocker = env.mode === 'docker' || env.in_container

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          🌍 Environment
        </div>
        <EnvironmentBadge />
      </div>

      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">Mode</span>
          <span className="text-sm font-medium text-gray-900 capitalize">{env.mode}</span>
        </div>
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">Backend Port</span>
          <span className="text-sm font-medium text-gray-900">{env.port}</span>
        </div>
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">In Container</span>
          <span className={`text-sm font-medium ${env.in_container ? 'text-blue-600' : 'text-gray-900'}`}>
            {env.in_container ? 'Yes' : 'No'}
          </span>
        </div>
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">ChromaDB</span>
          <span className="text-sm font-medium text-gray-900">{env.chroma_host}:{env.chroma_port}</span>
        </div>
        <div className="flex items-center justify-between py-2">
          <span className="text-sm text-gray-600">API URL</span>
          <span className="text-sm font-mono text-gray-700">{API_BASE}</span>
        </div>
      </div>

      {isDocker && (
        <div className="mt-4 p-3 rounded-md bg-blue-50 text-blue-700 text-xs">
          Running in Docker container. Local dev available on ports 3001/8001.
        </div>
      )}

      {!isDocker && env.mode === 'local' && (
        <div className="mt-4 p-3 rounded-md bg-green-50 text-green-700 text-xs">
          Running locally with hot reload. Docker mode available on ports 3000/8000.
        </div>
      )}
    </div>
  )
}
