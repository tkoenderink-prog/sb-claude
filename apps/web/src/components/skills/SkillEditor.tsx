'use client'

import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

interface SkillDetail {
  id: string
  name: string
  description: string
  when_to_use: string
  category: string
  tags: string[]
  content: string
  source: string
  path?: string
}

// Strip YAML frontmatter from content
function stripFrontmatter(content: string): string {
  if (!content.startsWith('---')) return content
  const endIndex = content.indexOf('---', 3)
  if (endIndex === -1) return content
  return content.slice(endIndex + 3).trim()
}

interface SkillEditorProps {
  skillId: string | null
  onClose: () => void
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const CATEGORIES = [
  'knowledge', 'workflow', 'analysis', 'creation',
  'integration', 'training', 'productivity', 'uncategorized'
]

export function SkillEditor({ skillId, onClose }: SkillEditorProps) {
  const queryClient = useQueryClient()
  const isNew = skillId === null

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    when_to_use: '',
    category: 'uncategorized',
    tags: [] as string[],
    content: '',
  })
  const [tagInput, setTagInput] = useState('')

  // Load existing skill
  const { data: skill, isLoading } = useQuery<SkillDetail>({
    queryKey: ['skill', skillId],
    queryFn: async () => {
      const res = await fetch(`${API_BASE}/skills/${skillId}`)
      if (!res.ok) throw new Error('Failed to load skill')
      return res.json()
    },
    enabled: !!skillId,
  })

  // Update form when skill loads
  useEffect(() => {
    if (skill) {
      setFormData({
        name: skill.name,
        description: skill.description,
        when_to_use: skill.when_to_use,
        category: skill.category,
        tags: skill.tags || [],
        content: stripFrontmatter(skill.content),
      })
    }
  }, [skill])

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const res = await fetch(`${API_BASE}/skills`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to create skill')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      onClose()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: async (data: typeof formData) => {
      const res = await fetch(`${API_BASE}/skills/${skillId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      if (!res.ok) throw new Error('Failed to update skill')
      return res.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      queryClient.invalidateQueries({ queryKey: ['skill', skillId] })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`${API_BASE}/skills/${skillId}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error('Failed to delete skill')
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['skills'] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isNew) {
      createMutation.mutate(formData)
    } else {
      updateMutation.mutate(formData)
    }
  }

  const handleAddTag = () => {
    if (tagInput && !formData.tags.includes(tagInput)) {
      setFormData({ ...formData, tags: [...formData.tags, tagInput] })
      setTagInput('')
    }
  }

  const handleRemoveTag = (tag: string) => {
    setFormData({ ...formData, tags: formData.tags.filter((t) => t !== tag) })
  }

  // All skills are now editable (filesystem skills update the SKILL.md file)
  const isReadOnly = false

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          {isNew ? 'Create Skill' : isReadOnly ? 'View Skill' : 'Edit Skill'}
        </h2>
        <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {skill?.path && (
        <div className="mb-4 p-3 bg-blue-50 text-blue-800 text-sm rounded border border-blue-200">
          <p className="font-medium mb-1">Filesystem Skill</p>
          <p className="text-xs mb-2">Changes will be saved to:</p>
          <code className="block bg-blue-100 px-2 py-1 rounded text-xs break-all">
            {skill.path}/SKILL.md
          </code>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Name</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
            disabled={isReadOnly}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full px-3 py-2 border rounded-md h-20"
            disabled={isReadOnly}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">When to Use</label>
          <textarea
            value={formData.when_to_use}
            onChange={(e) => setFormData({ ...formData, when_to_use: e.target.value })}
            className="w-full px-3 py-2 border rounded-md h-20"
            disabled={isReadOnly}
            placeholder="Describe when this skill should be triggered..."
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Category</label>
          <select
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            className="w-full px-3 py-2 border rounded-md"
            disabled={isReadOnly}
          >
            {CATEGORIES.map((cat) => (
              <option key={cat} value={cat}>
                {cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Tags</label>
          <div className="flex gap-2 mb-2 flex-wrap">
            {formData.tags.map((tag) => (
              <span key={tag} className="flex items-center gap-1 px-2 py-1 bg-gray-100 rounded text-sm">
                {tag}
                {!isReadOnly && (
                  <button
                    type="button"
                    onClick={() => handleRemoveTag(tag)}
                    className="text-gray-500 hover:text-gray-700"
                  >
                    ×
                  </button>
                )}
              </span>
            ))}
          </div>
          {!isReadOnly && (
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                className="flex-1 px-3 py-2 border rounded-md"
                placeholder="Add tag..."
              />
              <button
                type="button"
                onClick={handleAddTag}
                className="px-3 py-2 border rounded-md hover:bg-gray-50"
              >
                Add
              </button>
            </div>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Content (Markdown)</label>
          <textarea
            value={formData.content}
            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
            className="w-full px-3 py-2 border rounded-md h-64 font-mono text-sm"
            disabled={isReadOnly}
            required
          />
        </div>

        {!isReadOnly && (
          <div className="flex justify-between pt-4">
            {!isNew && (
              <button
                type="button"
                onClick={() => {
                  if (confirm('Are you sure you want to delete this skill?')) {
                    deleteMutation.mutate()
                  }
                }}
                className="px-4 py-2 text-red-600 hover:bg-red-50 rounded-md"
              >
                Delete
              </button>
            )}
            <div className="flex gap-2 ml-auto">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border rounded-md hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {isNew ? 'Create' : 'Save'}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  )
}
