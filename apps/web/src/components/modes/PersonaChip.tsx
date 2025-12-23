'use client'

import { type Persona } from '@/hooks/usePersonas'

interface PersonaChipProps {
  persona: Persona
  selected: boolean
  onClick: () => void
  variant?: 'default' | 'outline'
  size?: 'default' | 'compact'
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

export function PersonaChip({
  persona,
  selected,
  onClick,
  variant = 'default',
  size = 'default'
}: PersonaChipProps) {
  const isCompact = size === 'compact'

  return (
    <button
      onClick={onClick}
      className={cn(
        'rounded-lg flex items-center gap-2 transition-all',
        isCompact ? 'px-2 py-1.5' : 'px-3 py-2',
        variant === 'default' && selected && 'ring-2 ring-offset-2',
        variant === 'outline' && !selected && 'border border-dashed border-gray-300 hover:border-gray-400',
        variant === 'outline' && selected && 'border-2 border-solid',
        !selected && 'hover:shadow-sm'
      )}
      style={{
        backgroundColor: selected ? `${persona.color}20` : variant === 'outline' ? 'transparent' : '#f9fafb',
        borderColor: selected ? persona.color : undefined,
        ...(selected && { '--tw-ring-color': persona.color } as React.CSSProperties),
      }}
      title={persona.description || persona.name}
    >
      <span className={isCompact ? 'text-base' : 'text-lg'}>{persona.icon}</span>
      <div className="text-left">
        <div className={cn('font-medium', isCompact ? 'text-xs' : 'text-sm')}>
          {persona.name}
        </div>
        {!isCompact && persona.description && (
          <div className="text-xs text-gray-500 max-w-[150px] truncate">
            {persona.description}
          </div>
        )}
      </div>
    </button>
  )
}
