'use client'

import { useState, useEffect } from 'react'
import { usePersonas, type Persona } from '@/hooks/usePersonas'
import { PersonaChip } from './PersonaChip'

interface NewChatModalProps {
  open: boolean
  onClose: () => void
  onStartChat: (config: ChatConfig) => void
}

export interface ChatConfig {
  leadPersonaId: string | null
  councilMemberIds: string[]
  modelOverride?: string
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function NewChatModal({ open, onClose, onStartChat }: NewChatModalProps) {
  const { data: personas, isLoading } = usePersonas()
  const [leadPersona, setLeadPersona] = useState<string | null>(null)
  const [councilMembers, setCouncilMembers] = useState<string[]>([])
  const [model, setModel] = useState<string>('claude-sonnet-4-5-20250929')

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setLeadPersona(null)
      setCouncilMembers([])
      setModel('claude-sonnet-4-5-20250929')
    }
  }, [open])

  const handleStart = () => {
    onStartChat({
      leadPersonaId: leadPersona,
      councilMemberIds: councilMembers,
      modelOverride: model,
    })
    onClose()
  }

  const handleSkip = () => {
    onStartChat({
      leadPersonaId: null,
      councilMemberIds: [],
      modelOverride: model,
    })
    onClose()
  }

  const toggleCouncilMember = (personaId: string) => {
    setCouncilMembers(prev =>
      prev.includes(personaId)
        ? prev.filter(id => id !== personaId)
        : [...prev, personaId]
    )
  }

  if (!open) return null

  const orchestratorPersonas = personas?.filter(p => p.can_orchestrate) || []
  const availableMembers = personas?.filter(p => p.id !== leadPersona) || []

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b">
          <h2 className="text-xl font-semibold">New Conversation</h2>
          <p className="text-sm text-gray-500 mt-1">
            Choose a coaching persona to guide your conversation
          </p>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-6">
          {/* Lead Persona Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Lead Persona (Orchestrator)
            </label>
            <p className="text-xs text-gray-500 mb-3">
              This persona shapes how responses are framed and synthesized
            </p>
            {isLoading ? (
              <div className="text-sm text-gray-500">Loading personas...</div>
            ) : orchestratorPersonas.length === 0 ? (
              <div className="text-sm text-gray-500">No personas available</div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {orchestratorPersonas.map(persona => (
                  <PersonaChip
                    key={persona.id}
                    persona={persona}
                    selected={leadPersona === persona.id}
                    onClick={() => setLeadPersona(persona.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Council Members (optional) */}
          {leadPersona && (
            <div>
              <label className="block text-sm font-medium mb-2">
                Council Members (Optional)
              </label>
              <p className="text-xs text-gray-500 mb-3">
                Select personas to be available for council consultations
              </p>
              {availableMembers.length === 0 ? (
                <div className="text-sm text-gray-500">No other personas available</div>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {availableMembers.map(persona => (
                    <PersonaChip
                      key={persona.id}
                      persona={persona}
                      selected={councilMembers.includes(persona.id)}
                      onClick={() => toggleCouncilMember(persona.id)}
                      variant="outline"
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="claude-sonnet-4-5-20250929">Sonnet 4.5</option>
              <option value="claude-opus-4-5-20251101">Opus 4.5</option>
              <option value="claude-haiku-4-5-20251001">Haiku 4.5</option>
            </select>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex justify-between">
          <button
            onClick={handleSkip}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Skip (Use Default)
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 hover:bg-gray-50 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleStart}
              disabled={!leadPersona}
              className={cn(
                'px-4 py-2 text-sm font-medium text-white rounded-lg transition-colors',
                leadPersona
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-gray-300 cursor-not-allowed'
              )}
            >
              Start Chat
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
