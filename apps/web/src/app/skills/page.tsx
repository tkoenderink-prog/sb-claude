'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { SkillsList } from '@/components/skills/SkillsList'
import { SkillEditor } from '@/components/skills/SkillEditor'
import { CategoryFilter } from '@/components/skills/CategoryFilter'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SkillsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [editingSkillId, setEditingSkillId] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)

  const { data: categories } = useQuery({
    queryKey: ['skills', 'categories'],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/skills/categories`)
      return res.json()
    },
  })

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Left sidebar - Categories */}
      <div className="w-56 border-r bg-gray-50 p-4">
        <h2 className="font-semibold mb-4">Categories</h2>
        <CategoryFilter
          categories={categories || {}}
          selected={selectedCategory}
          onSelect={setSelectedCategory}
        />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold">Skills</h1>
            <input
              type="text"
              placeholder="Search skills..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="px-3 py-1.5 border rounded-md w-64"
            />
          </div>
          <button
            onClick={() => setIsCreating(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Create Skill
          </button>
        </div>

        {/* Skills list or editor */}
        <div className="flex-1 overflow-hidden flex">
          <div className={`${editingSkillId || isCreating ? 'w-1/2' : 'w-full'} overflow-y-auto p-4`}>
            <SkillsList
              category={selectedCategory}
              search={searchQuery}
              selectedId={editingSkillId}
              onSelect={setEditingSkillId}
            />
          </div>

          {(editingSkillId || isCreating) && (
            <div className="w-1/2 border-l overflow-y-auto">
              <SkillEditor
                skillId={isCreating ? null : editingSkillId}
                onClose={() => {
                  setEditingSkillId(null)
                  setIsCreating(false)
                }}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
