import { useQuery, useMutation } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Council {
  id: string
  name: string
  description: string
  category: string
  when_to_use: string
  content: string
}

export interface CouncilInvokeRequest {
  query: string
  orchestrator_id: string
  member_overrides?: string[]
}

export interface CouncilInvokeResponse {
  synthesis: string
}

async function getCouncils(): Promise<Council[]> {
  const res = await fetch(`${API_BASE}/councils`)
  if (!res.ok) throw new Error('Failed to fetch councils')
  return res.json()
}

async function invokeCouncil(
  councilName: string,
  request: CouncilInvokeRequest
): Promise<CouncilInvokeResponse> {
  const res = await fetch(`${API_BASE}/councils/${councilName}/invoke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!res.ok) throw new Error('Failed to invoke council')
  return res.json()
}

export function useCouncils() {
  return useQuery({
    queryKey: ['councils'],
    queryFn: getCouncils,
    staleTime: 60000, // Cache for 1 minute
  })
}

export function useInvokeCouncil(councilName: string) {
  return useMutation({
    mutationFn: (request: CouncilInvokeRequest) => invokeCouncil(councilName, request),
  })
}
