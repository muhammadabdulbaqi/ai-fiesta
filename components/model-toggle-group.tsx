"use client"

import { useState, useEffect } from "react"
import type { Model } from "@/lib/api"
import { getAvailableModels } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sparkles, Bot, Zap } from "lucide-react"
import { cn } from "@/lib/utils"

interface ModelToggleGroupProps {
  selectedModels: string[]
  onSelectionChange: (models: string[]) => void
  userTier?: string
}

export function ModelToggleGroup({ selectedModels, onSelectionChange, userTier = "free" }: ModelToggleGroupProps) {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getAvailableModels()
        setModels(data)
        // Default to first model if nothing selected
        if (selectedModels.length === 0 && data.length > 0) {
          onSelectionChange([data[0].value])
        }
      } catch (err) {
        console.error("Failed to fetch models:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchModels()
  }, [])

  const handleToggle = (modelId: string) => {
    if (selectedModels.includes(modelId)) {
      // Don't allow deselecting the last one
      if (selectedModels.length > 1) {
        onSelectionChange(selectedModels.filter(m => m !== modelId))
      }
    } else {
      onSelectionChange([...selectedModels, modelId])
    }
  }

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case "openai": return <Zap className="w-4 h-4" />
      case "anthropic": return <Bot className="w-4 h-4" />
      case "gemini": return <Sparkles className="w-4 h-4" />
      default: return <Bot className="w-4 h-4" />
    }
  }

  if (loading) {
    return <div className="h-10 bg-muted/50 rounded-lg animate-pulse w-full max-w-lg" />
  }

  // Group models by provider for cleaner UI
  const groupedModels = models.reduce((acc, model) => {
    if (!acc[model.provider]) acc[model.provider] = []
    acc[model.provider].push(model)
    return acc
  }, {} as Record<string, Model[]>)

  return (
    <div className="flex flex-wrap gap-4">
      {Object.entries(groupedModels).map(([provider, providerModels]) => (
        <div key={provider} className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase text-muted-foreground ml-1">
                {provider}
            </span>
            <div className="flex flex-wrap gap-2">
                {providerModels.map(model => {
                    const isSelected = selectedModels.includes(model.value)
                    const isDisabled = userTier === "free" && model.tier !== "free"
                    
                    return (
                        <Button
                            key={model.value}
                            variant={isSelected ? "default" : "outline"}
                            size="sm"
                            onClick={() => handleToggle(model.value)}
                            disabled={isDisabled}
                            className={cn(
                                "h-9 transition-all",
                                isSelected ? "ring-2 ring-primary/20" : "opacity-80 hover:opacity-100"
                            )}
                        >
                            {getProviderIcon(provider)}
                            <span className="ml-2">{model.label}</span>
                            {model.tier !== "free" && (
                                <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-[10px]">
                                    {model.tier}
                                </Badge>
                            )}
                        </Button>
                    )
                })}
            </div>
        </div>
      ))}
    </div>
  )
}