'use client'

import { HealthIndicator } from '@/components/HealthIndicator'
import { JobList } from '@/components/JobList'
import { JobLogViewer } from '@/components/JobLogViewer'
import { useRunJob } from '@/hooks/useJobs'
import { useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import Link from 'next/link'

export default function DashboardPage() {
  const runJobMutation = useRunJob()
  const queryClient = useQueryClient()
  const [activeJobId, setActiveJobId] = useState<string | null>(null)

  const handleRunJob = async () => {
    try {
      const job = await runJobMutation.mutateAsync({
        type: 'processor',
        command: 'test',
      })
      // Start streaming logs for the new job
      setActiveJobId(job.id)
    } catch (error) {
      console.error('Failed to run job:', error)
    }
  }

  const handleJobComplete = useCallback(() => {
    // Refresh job list when job completes
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
    // Clear active job after a short delay
    setTimeout(() => setActiveJobId(null), 2000)
  }, [queryClient])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-3xl font-bold text-gray-900">Second Brain Dashboard</h1>
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                Back to Chat
              </Link>
              <HealthIndicator />
            </div>
          </div>
          <p className="text-gray-600">
            Monitor and manage your AI second brain processors and jobs
          </p>
        </div>

        {/* Actions */}
        <div className="mb-8">
          <button
            onClick={handleRunJob}
            disabled={activeJobId !== null || runJobMutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {activeJobId !== null || runJobMutation.isPending ? 'Running...' : 'Run Job'}
          </button>
          {runJobMutation.isError && (
            <p className="mt-2 text-sm text-red-600">
              Error: {runJobMutation.error instanceof Error ? runJobMutation.error.message : 'Failed to run job'}
            </p>
          )}
        </div>

        {/* Live Job Logs */}
        {activeJobId && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Live Job Logs</h2>
            <JobLogViewer jobId={activeJobId} onComplete={handleJobComplete} />
          </div>
        )}

        {/* Recent Jobs */}
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Jobs</h2>
          <JobList />
        </div>
      </div>
    </div>
  )
}
