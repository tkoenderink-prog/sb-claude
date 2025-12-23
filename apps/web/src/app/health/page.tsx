import { VaultGitCard } from '@/components/health/VaultGitCard'
import { SystemStatsCard } from '@/components/health/SystemStatsCard'
import { RecentActivityCard } from '@/components/health/RecentActivityCard'

export default function HealthDashboard() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">System Health</h1>
          <p className="mt-2 text-sm text-gray-600">
            Monitor your Second Brain system status and activity
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <VaultGitCard />
          <SystemStatsCard />
          <div className="md:col-span-2">
            <RecentActivityCard />
          </div>
        </div>
      </div>
    </div>
  )
}
