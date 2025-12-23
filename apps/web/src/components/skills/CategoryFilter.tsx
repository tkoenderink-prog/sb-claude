'use client'

interface CategoryFilterProps {
  categories: Record<string, number>
  selected: string | null
  onSelect: (category: string | null) => void
}

const CATEGORY_ICONS: Record<string, string> = {
  knowledge: '📚',
  workflow: '⚙️',
  analysis: '🔍',
  creation: '✏️',
  integration: '🔗',
  training: '💪',
  productivity: '⏱️',
  uncategorized: '📁',
}

export function CategoryFilter({ categories, selected, onSelect }: CategoryFilterProps) {
  const total = Object.values(categories).reduce((sum, n) => sum + n, 0)

  return (
    <ul className="space-y-1">
      <li>
        <button
          onClick={() => onSelect(null)}
          className={`w-full text-left px-2 py-1.5 rounded-md text-sm flex items-center justify-between ${
            selected === null ? 'bg-gray-200 font-medium' : 'hover:bg-gray-100'
          }`}
        >
          <span>All Skills</span>
          <span className="text-gray-500">{total}</span>
        </button>
      </li>
      {Object.entries(categories)
        .filter(([, count]) => count > 0)
        .sort((a, b) => b[1] - a[1])
        .map(([category, count]) => (
          <li key={category}>
            <button
              onClick={() => onSelect(category)}
              className={`w-full text-left px-2 py-1.5 rounded-md text-sm flex items-center justify-between ${
                selected === category ? 'bg-gray-200 font-medium' : 'hover:bg-gray-100'
              }`}
            >
              <span className="flex items-center gap-2">
                <span>{CATEGORY_ICONS[category] || '📁'}</span>
                <span className="capitalize">{category}</span>
              </span>
              <span className="text-gray-500">{count}</span>
            </button>
          </li>
        ))}
    </ul>
  )
}
