import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Command {
  id: string
  mode_id: string | null
  name: string
  description: string | null
  prompt: string
  icon: string | null
  sort_order: number
}

export interface CreateCommandRequest {
  mode_id?: string
  name: string
  description?: string
  prompt: string
  icon?: string
  sort_order?: number
}

export interface UpdateCommandRequest {
  name?: string
  description?: string
  prompt?: string
  icon?: string
  sort_order?: number
}

async function getCommands(modeId?: string, globalOnly?: boolean): Promise<Command[]> {
  const params = new URLSearchParams()
  if (modeId) params.set('mode_id', modeId)
  if (globalOnly) params.set('global_only', 'true')

  const res = await fetch(`${API_BASE}/commands?${params.toString()}`)
  if (!res.ok) throw new Error('Failed to fetch commands')
  return res.json()
}

async function createCommand(data: CreateCommandRequest): Promise<Command> {
  const res = await fetch(`${API_BASE}/commands`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create command')
  return res.json()
}

async function updateCommand({ id, ...data }: UpdateCommandRequest & { id: string }): Promise<Command> {
  const res = await fetch(`${API_BASE}/commands/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update command')
  return res.json()
}

async function deleteCommand(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/commands/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete command')
}

export function useCommands(modeId?: string, globalOnly?: boolean) {
  return useQuery({
    queryKey: ['commands', modeId, globalOnly],
    queryFn: () => getCommands(modeId, globalOnly),
    staleTime: 60000,
  })
}

export function useGlobalCommands() {
  return useCommands(undefined, true)
}

export function useCreateCommand() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createCommand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commands'] })
      queryClient.invalidateQueries({ queryKey: ['modes'] })
    },
  })
}

export function useUpdateCommand() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateCommand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commands'] })
      queryClient.invalidateQueries({ queryKey: ['modes'] })
    },
  })
}

export function useDeleteCommand() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteCommand,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['commands'] })
      queryClient.invalidateQueries({ queryKey: ['modes'] })
    },
  })
}
