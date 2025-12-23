'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import {
  ArrowLeftIcon,
  CheckIcon,
  XMarkIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline'
import {
  useModes,
  useCreateMode,
  useUpdateMode,
  useDeleteMode,
  type Mode,
  type CreateModeRequest,
} from '@/hooks/useModes'
import {
  useCommands,
  useCreateCommand,
  useUpdateCommand,
  useDeleteCommand,
  type Command,
  type CreateCommandRequest,
} from '@/hooks/useCommands'

interface Settings {
  id: string
  yolo_mode: boolean
  default_model: string
  system_prompt: string | null
  system_prompt_history: Array<{ content: string; saved_at: string }>
}

interface ApiKey {
  provider: string
  key_suffix: string | null
  is_valid: boolean
  last_validated: string | null
  source: string
}

interface SyncStatus {
  sync_type: string
  status: string
  last_sync_start: string | null
  last_sync_end: string | null
  files_processed: number
  chunks_created: number
  error_message: string | null
}

const AVAILABLE_MODELS = [
  { id: 'claude-sonnet-4-5-20250929', name: 'Claude Sonnet 4.5' },
  { id: 'claude-opus-4-5-20251101', name: 'Claude Opus 4.5' },
  { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5' },
  { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku' },
]

const ICON_OPTIONS = ['💬', '📝', '🔍', '💡', '🎯', '📊', '🛠️', '🚀', '⚡', '🔧', '📋', '✨']

// Default system prompt (matches backend)
const DEFAULT_SYSTEM_PROMPT = `You are an AI assistant with access to the user's Second Brain system. You have powerful tools to query their calendar, tasks, and knowledge vault.

# Available Tools

## Calendar Tools
- get_today_events: Get all events for today
- get_week_events: Get events for the next 7 days
- get_events_in_range(start, end): Get events for custom date range
- search_events(query): Search events by title/description

## Task Tools
- get_overdue_tasks: Get tasks past their due date
- get_today_tasks: Get tasks due today
- get_week_tasks: Get tasks due in the next 7 days
- query_tasks(status, priority, project, has_due_date, limit): Flexible task query

## Vault/Knowledge Tools
- semantic_search(query, limit): Find related content by meaning
- text_search(query, limit): Find exact text matches
- hybrid_search(query, limit): Combines semantic + text search
- read_vault_file(path): Read full content of a specific file
- list_vault_directory(path): List files in a vault folder

## Skills Tools
- list_skills(source, category): List available thinking frameworks
- get_skill(skill_id): Get full content of a specific skill
- search_skills(query): Search skills by name or description`
const COLOR_OPTIONS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#8B5CF6', // purple
  '#F59E0B', // amber
  '#EF4444', // red
  '#EC4899', // pink
  '#6366F1', // indigo
  '#14B8A6', // teal
]

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([])
  const [syncStatuses, setSyncStatuses] = useState<SyncStatus[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [newKeyValue, setNewKeyValue] = useState('')
  const [systemPromptDraft, setSystemPromptDraft] = useState('')
  const [showPromptEditor, setShowPromptEditor] = useState(false)

  // Mode/Command state
  const [modesExpanded, setModesExpanded] = useState(false)
  const [commandsExpanded, setCommandsExpanded] = useState(false)
  const [editingMode, setEditingMode] = useState<Mode | null>(null)
  const [creatingMode, setCreatingMode] = useState(false)
  const [editingCommand, setEditingCommand] = useState<Command | null>(null)
  const [creatingCommand, setCreatingCommand] = useState(false)

  // Mode/Command hooks
  const { data: modes = [], isLoading: modesLoading } = useModes()
  const { data: commands = [], isLoading: commandsLoading } = useCommands()
  const createModeMutation = useCreateMode()
  const updateModeMutation = useUpdateMode()
  const deleteModeMutation = useDeleteMode()
  const createCommandMutation = useCreateCommand()
  const updateCommandMutation = useUpdateCommand()
  const deleteCommandMutation = useDeleteCommand()

  // Load settings
  useEffect(() => {
    async function loadData() {
      try {
        const [settingsRes, keysRes, syncRes] = await Promise.all([
          fetch('http://localhost:8000/settings'),
          fetch('http://localhost:8000/settings/api-keys'),
          fetch('http://localhost:8000/sync/status'),
        ])

        if (settingsRes.ok) {
          const data = await settingsRes.json()
          setSettings(data)
          // Use default prompt if no custom one is set
          setSystemPromptDraft(data.system_prompt || DEFAULT_SYSTEM_PROMPT)
        }

        if (keysRes.ok) {
          const data = await keysRes.json()
          setApiKeys(data.keys || [])
        }

        if (syncRes.ok) {
          const data = await syncRes.json()
          setSyncStatuses(data.statuses || [])
        }
      } catch (err) {
        console.error('Failed to load settings:', err)
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [])

  const updateSetting = useCallback(async (key: string, value: any) => {
    setIsSaving(true)
    try {
      const response = await fetch('http://localhost:8000/settings', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [key]: value }),
      })
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (err) {
      console.error('Failed to update setting:', err)
    } finally {
      setIsSaving(false)
    }
  }, [])

  const saveSystemPrompt = useCallback(async () => {
    await updateSetting('system_prompt', systemPromptDraft)
    setShowPromptEditor(false)
  }, [systemPromptDraft, updateSetting])

  const updateApiKey = useCallback(
    async (provider: string) => {
      try {
        const response = await fetch(`http://localhost:8000/settings/api-keys/${provider}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ key: newKeyValue }),
        })
        if (response.ok) {
          const keysRes = await fetch('http://localhost:8000/settings/api-keys')
          if (keysRes.ok) {
            const data = await keysRes.json()
            setApiKeys(data.keys || [])
          }
          setEditingKey(null)
          setNewKeyValue('')
        }
      } catch (err) {
        console.error('Failed to update API key:', err)
      }
    },
    [newKeyValue]
  )

  const testApiKey = useCallback(async (provider: string) => {
    try {
      const response = await fetch(`http://localhost:8000/settings/api-keys/${provider}/test`, {
        method: 'POST',
      })
      if (response.ok) {
        const keysRes = await fetch('http://localhost:8000/settings/api-keys')
        if (keysRes.ok) {
          const data = await keysRes.json()
          setApiKeys(data.keys || [])
        }
      }
    } catch (err) {
      console.error('Failed to test API key:', err)
    }
  }, [])

  const triggerSync = useCallback(async (syncType: string) => {
    try {
      await fetch(`http://localhost:8000/sync/trigger/${syncType}`, {
        method: 'POST',
      })
      const syncRes = await fetch('http://localhost:8000/sync/status')
      if (syncRes.ok) {
        const data = await syncRes.json()
        setSyncStatuses(data.statuses || [])
      }
    } catch (err) {
      console.error('Failed to trigger sync:', err)
    }
  }, [])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-3xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/" className="p-2 hover:bg-gray-200 rounded-lg transition-colors">
            <ArrowLeftIcon className="w-5 h-5 text-gray-600" />
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        </div>

        {/* General Settings */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">General</h2>
          <div className="space-y-4">
            {/* YOLO Mode */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">YOLO Mode</label>
                <p className="text-xs text-gray-500">Auto-apply file changes (except deletes)</p>
              </div>
              <button
                onClick={() => updateSetting('yolo_mode', !settings?.yolo_mode)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings?.yolo_mode ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings?.yolo_mode ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {/* Default Model */}
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">Default Model</label>
                <p className="text-xs text-gray-500">Model used for new conversations</p>
              </div>
              <select
                value={settings?.default_model || 'claude-sonnet-4-5-20250929'}
                onChange={(e) => updateSetting('default_model', e.target.value)}
                className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {AVAILABLE_MODELS.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </section>

        {/* Modes Section */}
        <section className="bg-white rounded-lg border border-gray-200 mb-6">
          <button
            onClick={() => setModesExpanded(!modesExpanded)}
            className="w-full flex items-center justify-between p-6"
          >
            <h2 className="text-lg font-semibold text-gray-900">Modes</h2>
            {modesExpanded ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-500" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-500" />
            )}
          </button>

          {modesExpanded && (
            <div className="px-6 pb-6 border-t border-gray-100 pt-4">
              <p className="text-xs text-gray-500 mb-4">
                Modes customize the AI behavior with custom system prompts and default models.
              </p>

              {modesLoading ? (
                <div className="text-sm text-gray-500">Loading modes...</div>
              ) : (
                <div className="space-y-3">
                  {modes.map((mode) => (
                    <div
                      key={mode.id}
                      className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className="w-8 h-8 rounded-full flex items-center justify-center text-lg"
                          style={{ backgroundColor: mode.color + '20' }}
                        >
                          {mode.icon}
                        </span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-gray-900">{mode.name}</span>
                            {mode.is_default && (
                              <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                Default
                              </span>
                            )}
                            {mode.is_system && (
                              <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                                System
                              </span>
                            )}
                          </div>
                          {mode.description && (
                            <p className="text-xs text-gray-500">{mode.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setEditingMode(mode)}
                          className="p-1.5 hover:bg-gray-200 rounded"
                          title="Edit"
                        >
                          <PencilIcon className="w-4 h-4 text-gray-500" />
                        </button>
                        {!mode.is_system && (
                          <button
                            onClick={() => {
                              if (confirm('Delete this mode?')) {
                                deleteModeMutation.mutate(mode.id)
                              }
                            }}
                            className="p-1.5 hover:bg-red-100 rounded"
                            title="Delete"
                          >
                            <TrashIcon className="w-4 h-4 text-red-500" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}

                  <button
                    onClick={() => setCreatingMode(true)}
                    className="w-full flex items-center justify-center gap-2 py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition-colors"
                  >
                    <PlusIcon className="w-4 h-4" />
                    Add Mode
                  </button>
                </div>
              )}

              {/* Mode Editor Modal */}
              {(editingMode || creatingMode) && (
                <ModeEditor
                  mode={editingMode}
                  onSave={async (data) => {
                    if (editingMode) {
                      await updateModeMutation.mutateAsync({ id: editingMode.id, ...data })
                    } else {
                      await createModeMutation.mutateAsync(data)
                    }
                    setEditingMode(null)
                    setCreatingMode(false)
                  }}
                  onCancel={() => {
                    setEditingMode(null)
                    setCreatingMode(false)
                  }}
                  isSystem={editingMode?.is_system || false}
                />
              )}
            </div>
          )}
        </section>

        {/* Commands Section */}
        <section className="bg-white rounded-lg border border-gray-200 mb-6">
          <button
            onClick={() => setCommandsExpanded(!commandsExpanded)}
            className="w-full flex items-center justify-between p-6"
          >
            <h2 className="text-lg font-semibold text-gray-900">Commands</h2>
            {commandsExpanded ? (
              <ChevronUpIcon className="w-5 h-5 text-gray-500" />
            ) : (
              <ChevronDownIcon className="w-5 h-5 text-gray-500" />
            )}
          </button>

          {commandsExpanded && (
            <div className="px-6 pb-6 border-t border-gray-100 pt-4">
              <p className="text-xs text-gray-500 mb-4">
                Commands are quick actions that inject predefined prompts. They appear as chips in the chat.
              </p>

              {commandsLoading ? (
                <div className="text-sm text-gray-500">Loading commands...</div>
              ) : (
                <div className="space-y-3">
                  {commands.map((command) => (
                    <div
                      key={command.id}
                      className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-lg">
                          {command.icon || '⚡'}
                        </span>
                        <div>
                          <span className="text-sm font-medium text-gray-900">{command.name}</span>
                          {command.description && (
                            <p className="text-xs text-gray-500">{command.description}</p>
                          )}
                          <p className="text-xs text-gray-400 truncate max-w-xs">
                            {command.prompt.slice(0, 60)}...
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => setEditingCommand(command)}
                          className="p-1.5 hover:bg-gray-200 rounded"
                          title="Edit"
                        >
                          <PencilIcon className="w-4 h-4 text-gray-500" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm('Delete this command?')) {
                              deleteCommandMutation.mutate(command.id)
                            }
                          }}
                          className="p-1.5 hover:bg-red-100 rounded"
                          title="Delete"
                        >
                          <TrashIcon className="w-4 h-4 text-red-500" />
                        </button>
                      </div>
                    </div>
                  ))}

                  <button
                    onClick={() => setCreatingCommand(true)}
                    className="w-full flex items-center justify-center gap-2 py-2 border-2 border-dashed border-gray-300 rounded-lg text-sm text-gray-600 hover:border-blue-400 hover:text-blue-600 transition-colors"
                  >
                    <PlusIcon className="w-4 h-4" />
                    Add Command
                  </button>
                </div>
              )}

              {/* Command Editor Modal */}
              {(editingCommand || creatingCommand) && (
                <CommandEditor
                  command={editingCommand}
                  modes={modes}
                  onSave={async (data) => {
                    if (editingCommand) {
                      await updateCommandMutation.mutateAsync({ id: editingCommand.id, ...data })
                    } else {
                      await createCommandMutation.mutateAsync(data)
                    }
                    setEditingCommand(null)
                    setCreatingCommand(false)
                  }}
                  onCancel={() => {
                    setEditingCommand(null)
                    setCreatingCommand(false)
                  }}
                />
              )}
            </div>
          )}
        </section>

        {/* System Prompt */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">System Prompt</h2>
            <button
              onClick={() => setShowPromptEditor(!showPromptEditor)}
              className="text-sm text-blue-600 hover:text-blue-700"
            >
              {showPromptEditor ? 'Cancel' : 'Edit'}
            </button>
          </div>

          {showPromptEditor ? (
            <div className="space-y-4">
              <textarea
                value={systemPromptDraft}
                onChange={(e) => setSystemPromptDraft(e.target.value)}
                rows={10}
                className="w-full border border-gray-300 rounded-lg p-3 text-sm font-mono
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your custom system prompt..."
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-500">
                  Supports variables: {'{{date}}'}, {'{{vault_stats}}'}, {'{{user_name}}'}
                </span>
                <button
                  onClick={saveSystemPrompt}
                  disabled={isSaving}
                  className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
                             hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {isSaving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-600">
              <div className="flex items-center gap-2 mb-2">
                {settings?.system_prompt ? (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">Custom</span>
                ) : (
                  <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">Default</span>
                )}
              </div>
              <pre className="whitespace-pre-wrap font-mono bg-gray-50 p-3 rounded-lg max-h-48 overflow-y-auto text-xs">
                {(settings?.system_prompt || DEFAULT_SYSTEM_PROMPT).slice(0, 500)}
                {(settings?.system_prompt || DEFAULT_SYSTEM_PROMPT).length > 500 && '...'}
              </pre>
            </div>
          )}
        </section>

        {/* API Keys */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">API Keys</h2>
          <div className="space-y-3">
            {apiKeys.map((key) => (
              <div
                key={key.provider}
                className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-gray-900 capitalize w-24">
                    {key.provider}
                  </span>
                  {key.key_suffix ? (
                    <span className="text-sm text-gray-500 font-mono">****{key.key_suffix}</span>
                  ) : (
                    <span className="text-sm text-gray-400 italic">Not set</span>
                  )}
                  {key.source === 'environment' && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                      ENV
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {key.key_suffix && (
                    <>
                      {key.is_valid ? (
                        <CheckIcon className="w-4 h-4 text-green-500" />
                      ) : (
                        <XMarkIcon className="w-4 h-4 text-red-500" />
                      )}
                      <button
                        onClick={() => testApiKey(key.provider)}
                        className="text-xs text-blue-600 hover:text-blue-700"
                      >
                        Test
                      </button>
                    </>
                  )}
                  {editingKey === key.provider ? (
                    <div className="flex items-center gap-2">
                      <input
                        type="password"
                        value={newKeyValue}
                        onChange={(e) => setNewKeyValue(e.target.value)}
                        placeholder="Enter API key..."
                        className="w-48 text-xs border border-gray-300 rounded px-2 py-1"
                      />
                      <button
                        onClick={() => updateApiKey(key.provider)}
                        className="text-xs text-green-600 hover:text-green-700"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => {
                          setEditingKey(null)
                          setNewKeyValue('')
                        }}
                        className="text-xs text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setEditingKey(key.provider)}
                      className="text-xs text-blue-600 hover:text-blue-700"
                    >
                      {key.key_suffix ? 'Edit' : 'Add'}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Knowledge Base / Sync Status */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Knowledge Base</h2>
          <div className="space-y-3">
            {syncStatuses.map((sync) => (
              <div
                key={sync.sync_type}
                className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0"
              >
                <div>
                  <span className="text-sm font-medium text-gray-900 capitalize">
                    {sync.sync_type}
                  </span>
                  <div className="text-xs text-gray-500">
                    {sync.last_sync_end ? (
                      <>Last sync: {new Date(sync.last_sync_end).toLocaleString()}</>
                    ) : (
                      <>Never synced</>
                    )}
                    {sync.sync_type === 'rag' && sync.files_processed > 0 && (
                      <span className="ml-2">
                        ({sync.files_processed} files, {sync.chunks_created} chunks)
                      </span>
                    )}
                  </div>
                  {sync.error_message && (
                    <div className="text-xs text-red-500 mt-1">{sync.error_message}</div>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      sync.status === 'running'
                        ? 'bg-yellow-400 animate-pulse'
                        : sync.status === 'failed'
                          ? 'bg-red-400'
                          : 'bg-green-400'
                    }`}
                  />
                  <button
                    onClick={() => triggerSync(sync.sync_type)}
                    disabled={sync.status === 'running'}
                    className="text-xs text-blue-600 hover:text-blue-700 disabled:text-gray-400"
                  >
                    {sync.status === 'running' ? 'Syncing...' : 'Resync'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Navigation Links */}
        <section className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Links</h2>
          <div className="space-y-2">
            <Link href="/dashboard" className="block text-sm text-blue-600 hover:text-blue-700">
              Dashboard
            </Link>
            <Link href="/" className="block text-sm text-blue-600 hover:text-blue-700">
              Chat
            </Link>
          </div>
        </section>
      </div>
    </div>
  )
}

// Mode Editor Component
function ModeEditor({
  mode,
  onSave,
  onCancel,
  isSystem,
}: {
  mode: Mode | null
  onSave: (data: CreateModeRequest) => Promise<void>
  onCancel: () => void
  isSystem: boolean
}) {
  const [name, setName] = useState(mode?.name || '')
  const [description, setDescription] = useState(mode?.description || '')
  const [icon, setIcon] = useState(mode?.icon || '💬')
  const [color, setColor] = useState(mode?.color || '#3B82F6')
  const [systemPromptAddition, setSystemPromptAddition] = useState(
    mode?.system_prompt_addition || ''
  )
  const [defaultModel, setDefaultModel] = useState(mode?.default_model || '')
  const [isDefault, setIsDefault] = useState(mode?.is_default || false)
  const [isSaving, setIsSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      await onSave({
        name,
        description: description || undefined,
        icon,
        color,
        system_prompt_addition: systemPromptAddition || undefined,
        default_model: defaultModel || undefined,
        is_default: isDefault,
      })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              {mode ? 'Edit Mode' : 'Create Mode'}
            </h3>
          </div>

          <div className="p-6 space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isSystem}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                placeholder="My Custom Mode"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isSystem}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                placeholder="What this mode does..."
              />
            </div>

            {/* Icon */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Icon</label>
              <div className="flex flex-wrap gap-2">
                {ICON_OPTIONS.map((i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => !isSystem && setIcon(i)}
                    disabled={isSystem}
                    className={`w-10 h-10 rounded-lg text-xl flex items-center justify-center border-2 transition-colors ${
                      icon === i
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    } disabled:opacity-50`}
                  >
                    {i}
                  </button>
                ))}
              </div>
            </div>

            {/* Color */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
              <div className="flex flex-wrap gap-2">
                {COLOR_OPTIONS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    onClick={() => !isSystem && setColor(c)}
                    disabled={isSystem}
                    className={`w-8 h-8 rounded-full border-2 transition-transform ${
                      color === c ? 'border-gray-900 scale-110' : 'border-transparent'
                    } disabled:opacity-50`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>

            {/* System Prompt Addition - always editable */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                System Prompt Addition
              </label>
              <textarea
                value={systemPromptAddition}
                onChange={(e) => setSystemPromptAddition(e.target.value)}
                rows={4}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Additional instructions to add to the system prompt..."
              />
            </div>

            {/* Default Model - always editable */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Default Model</label>
              <select
                value={defaultModel}
                onChange={(e) => setDefaultModel(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Use global default</option>
                {AVAILABLE_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Is Default */}
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium text-gray-700">Set as Default</label>
              <button
                type="button"
                onClick={() => setIsDefault(!isDefault)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  isDefault ? 'bg-blue-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    isDefault ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>

          <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !name}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? 'Saving...' : mode ? 'Save Changes' : 'Create Mode'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// Command Editor Component
function CommandEditor({
  command,
  modes,
  onSave,
  onCancel,
}: {
  command: Command | null
  modes: Mode[]
  onSave: (data: CreateCommandRequest) => Promise<void>
  onCancel: () => void
}) {
  const [name, setName] = useState(command?.name || '')
  const [description, setDescription] = useState(command?.description || '')
  const [prompt, setPrompt] = useState(command?.prompt || '')
  const [icon, setIcon] = useState(command?.icon || '⚡')
  const [modeId, setModeId] = useState(command?.mode_id || '')
  const [isSaving, setIsSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSaving(true)
    try {
      await onSave({
        name,
        description: description || undefined,
        prompt,
        icon: icon || undefined,
        mode_id: modeId || undefined,
      })
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              {command ? 'Edit Command' : 'Create Command'}
            </h3>
          </div>

          <div className="p-6 space-y-4">
            {/* Name */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Summarize"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Summarize the current context"
              />
            </div>

            {/* Icon */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Icon</label>
              <div className="flex flex-wrap gap-2">
                {ICON_OPTIONS.map((i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setIcon(i)}
                    className={`w-10 h-10 rounded-lg text-xl flex items-center justify-center border-2 transition-colors ${
                      icon === i
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {i}
                  </button>
                ))}
              </div>
            </div>

            {/* Mode Association */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Associated Mode (Optional)
              </label>
              <select
                value={modeId}
                onChange={(e) => setModeId(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Global (available in all modes)</option>
                {modes.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.icon} {m.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Prompt */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                required
                rows={6}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="The prompt to inject when this command is triggered..."
              />
              <p className="text-xs text-gray-500 mt-1">
                This prompt will be sent as the user message when the command is clicked.
              </p>
            </div>
          </div>

          <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving || !name || !prompt}
              className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isSaving ? 'Saving...' : command ? 'Save Changes' : 'Create Command'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
