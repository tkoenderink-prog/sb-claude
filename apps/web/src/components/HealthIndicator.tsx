'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getHealth, getCalendarStatus, getTasksStatus, getSkillsStats, API_BASE } from '@/lib/api'
import { useClientDateTime, useClientDate } from '@/hooks/useClientDate'
import type { HealthResponse, CalendarStatus, TasksStatus, SkillsStats } from '@/lib/api'

// Client-side number formatting component to avoid hydration mismatch
function ClientNumber({ value }: { value: number | undefined }) {
  const formatted = useClientDate(
    value ? new Date() : null,
    () => value?.toLocaleString() ?? ''
  )
  return <>{value !== undefined ? (formatted || value) : '-'}</>
}

// Client-side date formatting component
function ClientDateTime({ value }: { value: string | undefined }) {
  const formatted = useClientDateTime(value)
  return <>{formatted || '-'}</>
}

function StatusBadge({ available }: { available: boolean }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
      available ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
    }`}>
      {available ? 'OK' : 'Unavailable'}
    </span>
  )
}

function StatusPanel({ onClose }: { onClose: () => void }) {
  const health = useQuery({ queryKey: ['health'], queryFn: getHealth })
  const calendar = useQuery({ queryKey: ['calendar-status'], queryFn: getCalendarStatus })
  const tasks = useQuery({ queryKey: ['tasks-status'], queryFn: getTasksStatus })
  const skills = useQuery({ queryKey: ['skills-stats'], queryFn: getSkillsStats })

  return (
    <div className="fixed inset-0 bg-black/50 flex items-start justify-center pt-20 z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900">System Status</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            &times;
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Backend Health */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">Backend Service</h3>
            {health.isLoading ? (
              <div className="animate-pulse h-16 bg-gray-100 rounded"></div>
            ) : health.isError ? (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <p className="text-red-700 font-medium">Backend Offline</p>
                <p className="text-red-600 text-sm">Cannot connect to {API_BASE}</p>
              </div>
            ) : (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-green-800 font-medium">{health.data?.service}</p>
                    <p className="text-green-600 text-sm">Version {health.data?.version}</p>
                  </div>
                  <StatusBadge available={health.data?.status === 'ok'} />
                </div>
              </div>
            )}
          </section>

          {/* Calendar */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">Calendar Data</h3>
            {calendar.isLoading ? (
              <div className="animate-pulse h-24 bg-gray-100 rounded"></div>
            ) : calendar.isError ? (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-gray-500">Calendar status unavailable</p>
              </div>
            ) : (
              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-gray-900">Calendar Index</span>
                  <StatusBadge available={calendar.data?.available ?? false} />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Events:</span>
                    <span className="ml-2 font-medium"><ClientNumber value={calendar.data?.event_count} /></span>
                  </div>
                  <div>
                    <span className="text-gray-500">Calendars:</span>
                    <span className="ml-2 font-medium">{calendar.data?.calendars.join(', ')}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Timezone:</span>
                    <span className="ml-2 font-medium">{calendar.data?.timezone}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Generated:</span>
                    <span className="ml-2 font-medium">
                      <ClientDateTime value={calendar.data?.generated_at} />
                    </span>
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Tasks */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">Tasks Data</h3>
            {tasks.isLoading ? (
              <div className="animate-pulse h-32 bg-gray-100 rounded"></div>
            ) : tasks.isError ? (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-gray-500">Tasks status unavailable</p>
              </div>
            ) : (
              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-gray-900">Tasks Index</span>
                  <StatusBadge available={tasks.data?.available ?? false} />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm mb-3">
                  <div>
                    <span className="text-gray-500">Total Tasks:</span>
                    <span className="ml-2 font-medium"><ClientNumber value={tasks.data?.task_count} /></span>
                  </div>
                  <div>
                    <span className="text-gray-500">With Due Date:</span>
                    <span className="ml-2 font-medium">{tasks.data?.stats.with_due_date}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Overdue:</span>
                    <span className={`ml-2 font-medium ${(tasks.data?.stats.overdue ?? 0) > 0 ? 'text-red-600' : ''}`}>
                      {tasks.data?.stats.overdue}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Updated:</span>
                    <span className="ml-2 font-medium">
                      <ClientDateTime value={tasks.data?.last_updated} />
                    </span>
                  </div>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {tasks.data?.stats.by_status && Object.entries(tasks.data.stats.by_status).map(([status, count]) => (
                    <span key={status} className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                      {status}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Skills */}
          <section>
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide mb-3">Skills System</h3>
            {skills.isLoading ? (
              <div className="animate-pulse h-20 bg-gray-100 rounded"></div>
            ) : skills.isError ? (
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <p className="text-gray-500">Skills status unavailable</p>
              </div>
            ) : (
              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-gray-900">Skills Registry</span>
                  <StatusBadge available={(skills.data?.total_skills ?? 0) > 0} />
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Total Skills:</span>
                    <span className="ml-2 font-medium">{skills.data?.total_skills}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">With Checklist:</span>
                    <span className="ml-2 font-medium">{skills.data?.with_checklist}</span>
                  </div>
                </div>
                <div className="mt-2 text-xs text-gray-400 truncate">
                  {skills.data?.skill_roots.join(', ')}
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}

export function HealthIndicator() {
  const [showPanel, setShowPanel] = useState(false)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 10000
  })

  const baseClasses = "flex items-center gap-2 px-3 py-1.5 rounded-lg transition-colors cursor-pointer"

  if (isLoading) {
    return (
      <button className={`${baseClasses} bg-gray-100 hover:bg-gray-200`} disabled>
        <div className="w-3 h-3 rounded-full bg-gray-400 animate-pulse"></div>
        <span className="text-sm text-gray-600">Checking...</span>
      </button>
    )
  }

  if (isError || !data) {
    return (
      <>
        <button
          className={`${baseClasses} bg-red-50 hover:bg-red-100`}
          onClick={() => setShowPanel(true)}
        >
          <div className="w-3 h-3 rounded-full bg-red-500"></div>
          <span className="text-sm text-red-600">Offline</span>
        </button>
        {showPanel && <StatusPanel onClose={() => setShowPanel(false)} />}
      </>
    )
  }

  return (
    <>
      <button
        className={`${baseClasses} bg-green-50 hover:bg-green-100`}
        onClick={() => setShowPanel(true)}
      >
        <div className="w-3 h-3 rounded-full bg-green-500"></div>
        <span className="text-sm text-green-600">Healthy</span>
      </button>
      {showPanel && <StatusPanel onClose={() => setShowPanel(false)} />}
    </>
  )
}
