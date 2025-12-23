'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/chat-api'

interface Skill {
  id: string
  name: string
  description: string
  source: string
}

interface SkillsPanelProps {
  selectedSkills: string[]
  onSkillsChange: (skills: string[]) => void
}

export function SkillsPanel({ selectedSkills, onSkillsChange }: SkillsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const { data: skills, isLoading } = useQuery({
    queryKey: ['skills'],
    queryFn: async () => {
      const response = await api.get<{ skills: Skill[]; count: number }>('/skills')
      return response.data.skills
    },
  })

  const toggleSkill = (skillId: string) => {
    if (selectedSkills.includes(skillId)) {
      onSkillsChange(selectedSkills.filter((id) => id !== skillId))
    } else {
      onSkillsChange([...selectedSkills, skillId])
    }
  }

  const filteredSkills = skills?.filter(
    (skill) =>
      skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="w-80 border-l bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b bg-white">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center justify-between w-full text-left"
        >
          <div>
            <h3 className="font-semibold text-gray-900">Skills</h3>
            <p className="text-xs text-gray-500">
              {selectedSkills.length} selected
            </p>
          </div>
          <svg
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </button>
      </div>

      {/* Content */}
      {isExpanded && (
        <>
          {/* Search */}
          <div className="p-3 border-b bg-white">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search skills..."
              className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Skills list */}
          <div className="flex-1 overflow-y-auto p-3">
            {isLoading ? (
              <div className="text-sm text-gray-500 text-center py-4">
                Loading skills...
              </div>
            ) : filteredSkills && filteredSkills.length > 0 ? (
              <div className="space-y-2">
                {filteredSkills.map((skill) => (
                  <label
                    key={skill.id}
                    className="flex items-start gap-2 p-2 rounded hover:bg-gray-100 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedSkills.includes(skill.id)}
                      onChange={() => toggleSkill(skill.id)}
                      className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {skill.name}
                      </div>
                      <div className="text-xs text-gray-500 line-clamp-2">
                        {skill.description}
                      </div>
                      <div className="text-xs text-gray-400 mt-1">
                        {skill.source}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500 text-center py-4">
                No skills found
              </div>
            )}
          </div>

          {/* Clear button */}
          {selectedSkills.length > 0 && (
            <div className="p-3 border-t bg-white">
              <button
                onClick={() => onSkillsChange([])}
                className="w-full px-3 py-2 text-sm text-red-600 border border-red-300 rounded-lg hover:bg-red-50 transition-colors"
              >
                Clear All
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
