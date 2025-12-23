'use client'

import { useCommands, type Command } from '@/hooks/useCommands'

interface CommandChipsProps {
  selectedModeId?: string | null
  onCommandClick: (prompt: string) => void
}

export function CommandChips({ selectedModeId, onCommandClick }: CommandChipsProps) {
  // Fetch all commands - we filter client-side
  const { data: allCommands = [], isLoading } = useCommands()

  if (isLoading) {
    return null
  }

  // Filter to show global commands + commands for the selected mode
  const visibleCommands = allCommands.filter(
    (cmd) => cmd.mode_id === null || cmd.mode_id === selectedModeId
  )

  if (visibleCommands.length === 0) {
    return null
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {visibleCommands.map((command) => (
        <button
          key={command.id}
          onClick={() => onCommandClick(command.prompt)}
          className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium
                     bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-full
                     border border-gray-200 hover:border-gray-300 transition-colors"
          title={command.description || command.prompt}
        >
          {command.icon && <span className="text-sm">{command.icon}</span>}
          <span>{command.name}</span>
        </button>
      ))}
    </div>
  )
}
