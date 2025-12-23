import { useQuery } from '@tanstack/react-query'
import { getProviders } from '@/lib/chat-api'

export function useProviders() {
  return useQuery({
    queryKey: ['providers'],
    queryFn: getProviders,
    staleTime: 60000, // Cache for 1 minute
  })
}
