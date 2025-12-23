import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getHealth, getJobs, runJob, type RunJobRequest } from '@/lib/api'

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 10000, // Poll every 10 seconds
  })
}

export function useJobs() {
  return useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
    refetchInterval: 5000, // Poll every 5 seconds
  })
}

export function useRunJob() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: runJob,
    onSuccess: () => {
      // Invalidate jobs query to refetch the list
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
}
