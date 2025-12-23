import { useQuery } from '@tanstack/react-query'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Persona {
  id: string
  name: string
  description: string | null
  icon: string
  color: string
  is_persona: boolean
  can_orchestrate: boolean
  persona_config: {
    reasoning_style?: string
    synthesis_behavior?: string
    default_temperature?: number
  }
  system_prompt_addition: string | null
}

export interface PersonaSkill {
  id: string
  name: string
  description: string
  category: string
  when_to_use: string
}

async function getPersonas(): Promise<Persona[]> {
  const res = await fetch(`${API_BASE}/personas`)
  if (!res.ok) throw new Error('Failed to fetch personas')
  return res.json()
}

async function getPersonaSkills(personaId: string): Promise<PersonaSkill[]> {
  const res = await fetch(`${API_BASE}/personas/${personaId}/skills`)
  if (!res.ok) throw new Error('Failed to fetch persona skills')
  return res.json()
}

export function usePersonas() {
  return useQuery({
    queryKey: ['personas'],
    queryFn: getPersonas,
    staleTime: 60000, // Cache for 1 minute
  })
}

export function usePersonaSkills(personaId: string | null) {
  return useQuery({
    queryKey: ['persona-skills', personaId],
    queryFn: () => personaId ? getPersonaSkills(personaId) : Promise.resolve([]),
    enabled: !!personaId,
    staleTime: 60000,
  })
}
