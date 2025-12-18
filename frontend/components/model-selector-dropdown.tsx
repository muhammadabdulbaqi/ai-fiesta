"use client"

import { useState, useEffect } from "react"
import type { ModelRichInfo } from "@/lib/api"
import { getAvailableModels } from "@/lib/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Sparkles, Bot, Zap, Brain, Search } from "lucide-react"
import { cn } from "@/lib/utils"

interface ModelSelectorDropdownProps {
  modelId: string
  isEnabled: boolean
  onModelChange: (modelId: string) => void
  onToggle: (enabled: boolean) => void
  userTier?: string
}

export function ModelSelectorDropdown({ 
  modelId, 
  isEnabled, 
  onModelChange, 
  onToggle,
  userTier = "free" 
}: ModelSelectorDropdownProps) {
  const [models, setModels] = useState<ModelRichInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getAvailableModels()
        setModels(data)
        if (!modelId && data.length > 0) {
          onModelChange(data[0].value)
        }
      } catch (err) {
        console.error("Failed to fetch models:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchModels()
  }, [])

  const getProviderIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case "openai": return <Zap className="w-4 h-4" />
      case "anthropic": return <Bot className="w-4 h-4" />
      case "gemini": return <Sparkles className="w-4 h-4" />
      case "grok": return <Brain className="w-4 h-4" />
      case "perplexity": return <Search className="w-4 h-4" />
      default: return <Bot className="w-4 h-4" />
    }
  }

  const selectedModel = models.find(m => m.value === modelId)
  const provider = selectedModel?.provider || ""

  if (loading) {
    return <div className="h-10 w-48 bg-muted/50 rounded-lg animate-pulse" />
  }

  return (
    <div className="flex items-center gap-3 bg-card border border-border rounded-lg px-3 py-2 min-w-[200px]">
      <div className="flex items-center gap-2 flex-1">
        {selectedModel && getProviderIcon(provider)}
        <Select value={modelId} onValueChange={onModelChange}>
          <SelectTrigger className="border-0 shadow-none focus:ring-0 h-auto p-0 w-auto min-w-[120px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {models
              .filter(m => userTier !== "free" || m.tier === "free")
              .map((model) => (
                <SelectItem key={model.value} value={model.value}>
                  <div className="flex items-center gap-2">
                    {getProviderIcon(model.provider)}
                    <span>{model.label}</span>
                  </div>
                </SelectItem>
              ))}
          </SelectContent>
        </Select>
      </div>
      <Switch checked={isEnabled} onCheckedChange={onToggle} />
    </div>
  )
}

