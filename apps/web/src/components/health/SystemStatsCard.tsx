'use client'

import { useQuery } from '@tanstack/react-query'
import { API_BASE } from '@/lib/api'

interface SystemStats {
  sessions_24h: number
  proposals_24h: number
  skills_used_24h: number
  councils_24h: number
}

export function SystemStatsCard() {
  const { data: stats, isLoading } = useQuery<SystemStats>({
    queryKey: ['system-stats'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/health`)
      if (!res.ok) throw new Error('Failed to fetch stats')
      const health = await res.json()
      return {
        sessions_24h: health.sessions_24h || 0,
        proposals_24h: health.proposals_24h || 0,
        skills_used_24h: health.skills_used_24h || 0,
        councils_24h: health.councils_24h || 0,
      }
    },
    refetchInterval: 60000,
  })

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          📊 System Stats (24h)
        </div>
        <div className="mt-4 text-sm text-gray-500">Loading...</div>
      </div>
    )
  }

  const StatRow = ({ label, value }: { label: string; value: number }) => (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-600">{label}</span>
      <span className="text-lg font-semibold text-gray-900">{value}</span>
    </div>
  )

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
        📊 System Stats (24h)
      </div>
      <div className="mt-4 divide-y divide-gray-100">
        <StatRow label="Chat Sessions" value={stats?.sessions_24h || 0} />
        <StatRow label="Proposals Created" value={stats?.proposals_24h || 0} />
        <StatRow label="Skills Used" value={stats?.skills_used_24h || 0} />
        <StatRow label="Council Invocations" value={stats?.councils_24h || 0} />
      </div>
    </div>
  )
}
