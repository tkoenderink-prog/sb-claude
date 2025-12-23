'use client'

import { type ChatMode } from '@/lib/chat-api'

interface ModeSelectorProps {
  mode: ChatMode
  onChange: (mode: ChatMode) => void
}

export function ModeSelector({ mode, onChange }: ModeSelectorProps) {
  const modes: { value: ChatMode; label: string; description: string }[] = [
    {
      value: 'tools',
      label: 'Tool-Enabled',
      description: 'Access calendar, tasks, and vault',
    },
    {
      value: 'agent',
      label: 'Agent Mode',
      description: 'Autonomous multi-step tasks',
    },
  ]

  return (
    <div className="flex gap-2 border-b">
      {modes.map((m) => (
        <button
          key={m.value}
          onClick={() => onChange(m.value)}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            mode === m.value
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300'
          }`}
          title={m.description}
        >
          {m.label}
        </button>
      ))}
    </div>
  )
}
