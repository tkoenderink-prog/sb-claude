'use client'

import { useQuery } from '@tanstack/react-query'

interface ChatSession {
  id: string
  title: string
  created_at: string
  mode_id: string
}

export function RecentActivityCard() {
  const { data: sessions, isLoading } = useQuery<ChatSession[]>({
    queryKey: ['recent-sessions'],
    queryFn: async () => {
      const res = await fetch('http://localhost:8000/sessions?limit=5')
      if (!res.ok) throw new Error('Failed to fetch sessions')
      return res.json()
    },
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
          🕐 Recent Activity
        </div>
        <div className="mt-4 text-sm text-gray-500">Loading...</div>
      </div>
    )
  }

  const getRelativeTime = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (seconds < 60) return 'just now'
    if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
    return `${Math.floor(seconds / 86400)}d ago`
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-2 text-lg font-semibold text-gray-900">
        🕐 Recent Activity
      </div>
      <div className="mt-4 space-y-3">
        {sessions && sessions.length > 0 ? (
          sessions.map((session) => (
            <div
              key={session.id}
              className="flex items-start justify-between border-l-2 border-blue-500 pl-3 py-1"
            >
              <div className="flex-1">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {session.title || 'Untitled Chat'}
                </div>
                <div className="text-xs text-gray-500">
                  {getRelativeTime(session.created_at)}
                </div>
              </div>
              <a
                href={`/chat?session=${session.id}`}
                className="text-xs text-blue-600 hover:text-blue-700"
              >
                Open
              </a>
            </div>
          ))
        ) : (
          <div className="text-sm text-gray-500">No recent activity</div>
        )}
      </div>
    </div>
  )
}
