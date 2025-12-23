'use client'

import { useState } from 'react'

interface GitSettings {
  auto_commit_on_edit: boolean
  auto_push: boolean
  commit_message_template: string
}

export function GitSettingsPanel() {
  const [settings, setSettings] = useState<GitSettings>({
    auto_commit_on_edit: true,
    auto_push: false,
    commit_message_template: '[Second Brain] {action}',
  })
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle')

  const handleSave = async () => {
    setIsSaving(true)
    setSaveStatus('idle')
    
    try {
      const res = await fetch('http://localhost:8000/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ git_settings: settings }),
      })
      
      if (!res.ok) throw new Error('Failed to save settings')
      
      setSaveStatus('success')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch (error) {
      console.error('Error saving settings:', error)
      setSaveStatus('error')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-gray-900">Vault Git Settings</h3>
        <p className="mt-1 text-sm text-gray-600">
          Configure automatic git commits and syncing for your Obsidian vault
        </p>
      </div>

      <div className="space-y-4">
        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={settings.auto_commit_on_edit}
            onChange={(e) =>
              setSettings({ ...settings, auto_commit_on_edit: e.target.checked })
            }
            className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-900">
              Auto-commit on proposal apply
            </div>
            <div className="text-sm text-gray-600">
              Automatically commit changes before and after applying proposals
            </div>
          </div>
        </label>

        <label className="flex items-start gap-3">
          <input
            type="checkbox"
            checked={settings.auto_push}
            onChange={(e) =>
              setSettings({ ...settings, auto_push: e.target.checked })
            }
            className="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            disabled={!settings.auto_commit_on_edit}
          />
          <div className="flex-1">
            <div className="text-sm font-medium text-gray-900">
              Auto-push after commit
            </div>
            <div className="text-sm text-gray-600">
              Push to remote after committing
            </div>
          </div>
        </label>

        <div>
          <label className="block text-sm font-medium text-gray-900">
            Commit message template
          </label>
          <div className="mt-1">
            <input
              type="text"
              value={settings.commit_message_template}
              onChange={(e) =>
                setSettings({ ...settings, commit_message_template: e.target.value })
              }
              placeholder="[Second Brain] {action}"
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
            />
          </div>
          <p className="mt-1 text-sm text-gray-600">
            Use {'{action}'} as placeholder
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-gray-400"
        >
          {isSaving ? 'Saving...' : 'Save Git Settings'}
        </button>
        {saveStatus === 'success' && (
          <span className="text-sm text-green-600">✓ Saved</span>
        )}
        {saveStatus === 'error' && (
          <span className="text-sm text-red-600">Error saving</span>
        )}
      </div>
    </div>
  )
}
