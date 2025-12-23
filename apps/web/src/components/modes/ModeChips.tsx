'use client'

import { type Mode } from '@/hooks/useModes'

interface ModeChipsProps {
  modes: Mode[]
  selectedId: string | null
  onSelect: (mode: Mode) => void
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function ModeChips({ modes, selectedId, onSelect }: ModeChipsProps) {
  if (!modes.length) return null

  return (
    <div className="flex flex-wrap gap-2">
      {modes.map(mode => (
        <button
          key={mode.id}
          onClick={() => onSelect(mode)}
          className={cn(
            'px-3 py-1.5 rounded-full text-sm flex items-center gap-1.5 transition-colors border',
            selectedId === mode.id
              ? 'bg-blue-100 text-blue-800 border-blue-300 ring-2 ring-blue-500 ring-offset-1'
              : 'bg-gray-100 text-gray-700 border-gray-200 hover:bg-gray-200 hover:border-gray-300'
          )}
        >
          <span>{mode.icon}</span>
          <span>{mode.name}</span>
        </button>
      ))}
    </div>
  )
}
