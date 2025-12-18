"use client"

import { useState, useEffect } from "react"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { getAvailableModels, type ModelRichInfo } from "@/lib/api"
import { cn } from "@/lib/utils"
// Using regular img tag for custom icons that may not be optimized

interface MultiChatModelSelectorsProps {
  selectedModels: string[]
  onModelsChange: (models: string[]) => void
  userTier?: string
}

// Provider icon mapping
const getProviderIcon = (provider: string) => {
  const providerLower = provider.toLowerCase()
  switch (providerLower) {
    case "openai":
      return "/icons/openai.png"
    case "anthropic":
      return "/icons/anthropic-1.svg"
    case "gemini":
      return "/icons/Google_Gemini_icon_2025.svg.png"
    case "grok":
      return "/icons/Grok-icon.svg.png"
    case "perplexity":
      return "/icons/perplexity-e6a4e1t06hd6dhczot580o.webp"
    default:
      return null
  }
}

export function MultiChatModelSelectors({ 
  selectedModels, 
  onModelsChange,
  userTier = "free" 
}: MultiChatModelSelectorsProps) {
  const [availableModels, setAvailableModels] = useState<ModelRichInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [providerModels, setProviderModels] = useState<Record<string, ModelRichInfo[]>>({})
  const [selectedProviderModels, setSelectedProviderModels] = useState<Record<string, string>>({})

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getAvailableModels()
        // Don't filter - show ALL models, we'll handle tier restrictions in UI
        setAvailableModels(data)
        
        // Group by provider - include ALL providers
        const grouped: Record<string, ModelRichInfo[]> = {}
        data.forEach(model => {
          if (!grouped[model.provider]) {
            grouped[model.provider] = []
          }
          grouped[model.provider].push(model)
        })
        setProviderModels(grouped)
        
        // Initialize selected models per provider - for ALL providers
        const initial: Record<string, string> = {}
        Object.keys(grouped).forEach(provider => {
          const models = grouped[provider]
          if (models.length > 0) {
            // Filter by tier for initial selection
            const availableForTier = models.filter(m => userTier !== "free" || m.tier === "free")
            if (availableForTier.length > 0) {
              // Prefer models with "flash", "mini", or "turbo" in the name
              const preferred = availableForTier.find(m => 
                m.value.toLowerCase().includes("flash") || 
                m.value.toLowerCase().includes("mini") || 
                m.value.toLowerCase().includes("turbo")
              ) || availableForTier[0]
              initial[provider] = preferred.value
            } else {
              // If no free tier models, just use first model (will be disabled)
              initial[provider] = models[0].value
            }
          }
        })
        setSelectedProviderModels(initial)
        
        // Initialize selectedModels if empty - only include models available for tier
        if (selectedModels.length === 0) {
          const initialModels = Object.values(initial).filter(modelId => {
            const model = data.find(m => m.value === modelId)
            return model && (userTier !== "free" || model.tier === "free")
          })
          if (initialModels.length > 0) {
            onModelsChange(initialModels)
          }
        } else {
          // Sync selectedProviderModels with selectedModels
          const synced: Record<string, string> = {}
          selectedModels.forEach(modelId => {
            const model = data.find(m => m.value === modelId)
            if (model && !synced[model.provider]) {
              synced[model.provider] = modelId
            }
          })
          setSelectedProviderModels(prev => ({ ...prev, ...synced }))
        }
      } catch (err) {
        console.error("Failed to fetch models:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchModels()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userTier]) // Re-fetch if tier changes

  const handleProviderModelChange = (provider: string, modelId: string) => {
    setSelectedProviderModels(prev => ({ ...prev, [provider]: modelId }))
    
    // Update selectedModels: remove old model from this provider, add new one
    const oldModel = availableModels.find(m => 
      m.provider === provider && selectedModels.includes(m.value)
    )
    const newSelected = oldModel 
      ? selectedModels.map(m => m === oldModel.value ? modelId : m)
      : [...selectedModels, modelId]
    onModelsChange(newSelected)
  }

  const handleToggle = (provider: string, enabled: boolean) => {
    const modelId = selectedProviderModels[provider]
    if (!modelId) return
    
    if (enabled) {
      // Add model if not already selected
      if (!selectedModels.includes(modelId)) {
        onModelsChange([...selectedModels, modelId])
      }
    } else {
      // Remove model if disabled (but keep at least one)
      if (selectedModels.length > 1) {
        onModelsChange(selectedModels.filter(m => m !== modelId))
      }
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-4 overflow-x-auto pb-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-16 w-48 bg-muted/50 rounded-lg animate-pulse flex-shrink-0" />
        ))}
      </div>
    )
  }

  const providers = Object.keys(providerModels).sort()

  if (providers.length === 0) {
    return (
      <div className="text-sm text-muted-foreground">
        No providers available
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
      {providers.map((provider) => {
        const models = providerModels[provider]
        const selectedModelId = selectedProviderModels[provider] || models[0]?.value
        const selectedModel = models.find(m => m.value === selectedModelId) || models[0]
        const isSelected = selectedModel && selectedModels.includes(selectedModel.value)
        const iconSrc = getProviderIcon(provider)
        
        // Check if selected model is available for current tier
        const selectedModelAvailable = selectedModel && (userTier !== "free" || selectedModel.tier === "free")

        return (
          <div
            key={provider}
            className={cn(
              "flex items-center gap-3 bg-card border rounded-lg px-4 py-3 min-w-[220px] max-w-[220px] flex-shrink-0 transition-all",
              isSelected && selectedModelAvailable ? "border-primary shadow-sm" : "border-border opacity-60"
            )}
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              {/* Provider Icon */}
              {iconSrc ? (
                <img
                  src={iconSrc}
                  alt={provider}
                  className="w-6 h-6 flex-shrink-0 object-contain"
                />
              ) : (
                <div className="w-6 h-6 flex-shrink-0 bg-muted rounded" />
              )}
              
              {/* Model Dropdown */}
              <Select
                value={selectedModelId}
                onValueChange={(value) => handleProviderModelChange(provider, value)}
              >
                <SelectTrigger className="border-0 shadow-none focus:ring-0 h-auto p-0 w-auto min-w-[120px] text-sm font-medium">
                  <SelectValue>
                    {selectedModel?.label || models[0]?.label}
                  </SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => {
                    const isAvailable = userTier !== "free" || model.tier === "free"
                    return (
                      <SelectItem 
                        key={model.value} 
                        value={model.value}
                        disabled={!isAvailable}
                        className={!isAvailable ? "opacity-50" : ""}
                      >
                        <div className="flex items-center gap-2">
                          {iconSrc && (
                            <img
                              src={iconSrc}
                              alt={provider}
                              className="w-4 h-4 object-contain"
                            />
                          )}
                          <span>{model.label}</span>
                          {!isAvailable && (
                            <span className="text-xs text-muted-foreground ml-1">({model.tier})</span>
                          )}
                        </div>
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
            </div>
            
            {/* Toggle Switch */}
            <Switch 
              checked={isSelected} 
              onCheckedChange={(enabled) => handleToggle(provider, enabled)}
            />
          </div>
        )
      })}
    </div>
  )
}

