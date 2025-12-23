'use client'

import { useQuery } from '@tanstack/react-query'

interface Skill {
  id: string
  name: string
  description: string
  category: string
  source: string
  tags: string[]
}

interface SkillsListProps {
  category: string | null
  search: string
  selectedId: string | null
  onSelect: (id: string) => void
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const CATEGORY_COLORS: Record<string, string> = {
  knowledge: 'bg-blue-100 text-blue-800',
  workflow: 'bg-green-100 text-green-800',
  analysis: 'bg-purple-100 text-purple-800',
  creation: 'bg-yellow-100 text-yellow-800',
  integration: 'bg-orange-100 text-orange-800',
  training: 'bg-red-100 text-red-800',
  productivity: 'bg-teal-100 text-teal-800',
  uncategorized: 'bg-gray-100 text-gray-800',
}

interface SkillsResponse {
  skills: Skill[]
}

export function SkillsList({ category, search, selectedId, onSelect }: SkillsListProps) {
  const { data: skills, isLoading } = useQuery<Skill[]>({
    queryKey: ['skills', category, search],
    queryFn: async () => {
      const params = new URLSearchParams()
      if (category) params.set('category', category)
      if (search) params.set('search', search)

      const res = await fetch(`${API_BASE}/skills?${params}`)
      const data: SkillsResponse = await res.json()
      return data.skills || []
    },
  })

  if (isLoading) {
    return <div className="text-gray-500">Loading skills...</div>
  }

  if (!skills?.length) {
    return <div className="text-gray-500">No skills found</div>
  }

  // Group by category
  const grouped = skills.reduce((acc, skill) => {
    const cat = skill.category
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(skill)
    return acc
  }, {} as Record<string, Skill[]>)

  return (
    <div className="space-y-6">
      {Object.entries(grouped).map(([cat, catSkills]) => (
        <div key={cat}>
          <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wider mb-2">
            {cat}
          </h3>
          <div className="grid gap-3">
            {catSkills.map((skill) => (
              <button
                key={skill.id}
                onClick={() => onSelect(skill.id)}
                className={`text-left p-3 rounded-lg border transition-colors ${
                  selectedId === skill.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-medium">{skill.name}</h4>
                    <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                      {skill.description}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${CATEGORY_COLORS[skill.category] || CATEGORY_COLORS.uncategorized}`}>
                    {skill.category}
                  </span>
                </div>
                {skill.tags.length > 0 && (
                  <div className="flex gap-1 mt-2 flex-wrap">
                    {skill.tags.slice(0, 3).map((tag) => (
                      <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                        {tag}
                      </span>
                    ))}
                    {skill.tags.length > 3 && (
                      <span className="text-xs text-gray-400">+{skill.tags.length - 3}</span>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
