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

export interface Mode {
  id: string
  name: string
  description: string | null
  icon: string
  color: string
  system_prompt_addition: string | null
  default_model: string | null
  sort_order: number
  is_default: boolean
  is_system: boolean
  commands?: Command[]
}

export interface CreateModeRequest {
  name: string
  description?: string
  icon?: string
  color?: string
  system_prompt_addition?: string
  default_model?: string
  sort_order?: number
  is_default?: boolean
}

export interface UpdateModeRequest {
  name?: string
  description?: string
  icon?: string
  color?: string
  system_prompt_addition?: string
  default_model?: string
  sort_order?: number
  is_default?: boolean
}

async function getModes(): Promise<Mode[]> {
  const res = await fetch(`${API_BASE}/modes`)
  if (!res.ok) throw new Error('Failed to fetch modes')
  return res.json()
}

async function createMode(data: CreateModeRequest): Promise<Mode> {
  const res = await fetch(`${API_BASE}/modes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to create mode')
  return res.json()
}

async function updateMode({ id, ...data }: UpdateModeRequest & { id: string }): Promise<Mode> {
  const res = await fetch(`${API_BASE}/modes/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error('Failed to update mode')
  return res.json()
}

async function deleteMode(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/modes/${id}`, {
    method: 'DELETE',
  })
  if (!res.ok) throw new Error('Failed to delete mode')
}

export function useModes() {
  return useQuery({
    queryKey: ['modes'],
    queryFn: getModes,
    staleTime: 60000,
  })
}

export function useCreateMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: createMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modes'] })
    },
  })
}

export function useUpdateMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modes'] })
    },
  })
}

export function useDeleteMode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteMode,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['modes'] })
    },
  })
}
