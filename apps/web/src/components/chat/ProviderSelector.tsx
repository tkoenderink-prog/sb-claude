'use client'

import { useProviders } from '@/hooks/useProviders'
import { type ProviderInfo, type ModelInfo } from '@/lib/chat-api'

interface ProviderSelectorProps {
  provider: string
  model: string
  onProviderChange: (provider: string) => void
  onModelChange: (model: string) => void
}

export function ProviderSelector({
  provider,
  model,
  onProviderChange,
  onModelChange,
}: ProviderSelectorProps) {
  const { data: providers, isLoading } = useProviders()

  if (isLoading) {
    return (
      <div className="flex gap-2 items-center text-sm text-gray-500">
        <div className="animate-pulse">Loading providers...</div>
      </div>
    )
  }

  const currentProvider = providers?.find((p) => p.name === provider)
  const availableModels = currentProvider?.models || []

  // Get model info to show context window and pricing tier
  const currentModel = availableModels.find((m) => m.id === model)
  const getModelTier = (modelId: string): string | null => {
    if (modelId.includes('opus')) return 'Premium'
    if (modelId.includes('sonnet')) return 'Balanced'
    if (modelId.includes('haiku')) return 'Fast'
    if (modelId.includes('gpt-4o-mini')) return 'Fast'
    if (modelId.includes('gpt-4o')) return 'Balanced'
    if (modelId.includes('gpt-4-turbo')) return 'Premium'
    return null
  }

  return (
    <div className="flex gap-3 items-center">
      <div className="flex items-center gap-2">
        <label htmlFor="provider" className="text-sm font-medium text-gray-700">
          Provider:
        </label>
        <select
          id="provider"
          value={provider}
          onChange={(e) => {
            onProviderChange(e.target.value)
            // Auto-select first model of new provider
            const newProvider = providers?.find((p) => p.name === e.target.value)
            if (newProvider && newProvider.models.length > 0) {
              onModelChange(newProvider.models[0].id)
            }
          }}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {providers?.map((p) => (
            <option key={p.name} value={p.name}>
              {p.display_name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex items-center gap-2">
        <label htmlFor="model" className="text-sm font-medium text-gray-700">
          Model:
        </label>
        <select
          id="model"
          value={model}
          onChange={(e) => onModelChange(e.target.value)}
          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {availableModels.map((m) => (
            <option key={m.id} value={m.id}>
              {m.display_name}
            </option>
          ))}
        </select>
      </div>

      {currentProvider && (
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <div className="flex items-center gap-1">
            {currentProvider.supports_tools && <span title="Supports tools">🔧</span>}
            {currentProvider.supports_agent && <span title="Supports agent mode">🤖</span>}
          </div>
          {currentModel && (
            <div className="flex items-center gap-2">
              {getModelTier(model) && (
                <span className="px-2 py-0.5 bg-gray-100 rounded text-xs font-medium">
                  {getModelTier(model)}
                </span>
              )}
              <span className="text-xs text-gray-400">
                {(currentModel.context_window / 1000).toFixed(0)}K ctx
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
