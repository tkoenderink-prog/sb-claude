'use client'

import { useJobs } from '@/hooks/useJobs'
import { useClientDateTime } from '@/hooks/useClientDate'
import type { JobRun } from '@/lib/api'

function JobStatusBadge({ status }: { status: JobRun['status'] }) {
  const styles = {
    queued: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    succeeded: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
    cancelled: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
      {status}
    </span>
  )
}

function JobRow({ job }: { job: JobRun }) {
  const startedAt = useClientDateTime(job.started_at)
  const endedAt = useClientDateTime(job.ended_at)

  return (
    <div className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-mono text-sm font-medium">{job.id}</h3>
            <JobStatusBadge status={job.status} />
          </div>
          <div className="text-sm text-gray-600 space-y-1">
            <p>Type: <span className="font-medium">{job.type}</span></p>
            <p>Command: <span className="font-mono">{job.command}</span></p>
            <p>Started: <span className="font-medium">{startedAt}</span></p>
            {job.ended_at && (
              <p>Ended: <span className="font-medium">{endedAt}</span></p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function JobList() {
  const { data: jobs, isLoading, isError, error } = useJobs()

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border rounded-lg p-4 animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="border border-red-200 rounded-lg p-4 bg-red-50">
        <p className="text-red-600 text-sm">
          Error loading jobs: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  if (!jobs || jobs.length === 0) {
    return (
      <div className="border border-gray-200 rounded-lg p-8 text-center text-gray-500">
        <p>No jobs found</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {jobs.map((job) => (
        <JobRow key={job.id} job={job} />
      ))}
    </div>
  )
}
