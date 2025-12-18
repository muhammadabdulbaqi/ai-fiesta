"use client"

import { useState, useEffect } from "react"
import type { Model } from "@/lib/api"
import { getAvailableModels } from "@/lib/api"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Sparkles } from "lucide-react"

interface SuperFiestaSelectorProps {
  value: string
  onChange: (model: string) => void
  userTier?: string
}

export function SuperFiestaSelector({ value, onChange, userTier = "free" }: SuperFiestaSelectorProps) {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getAvailableModels()
        setModels(data)
        if (data.length > 0 && !value) {
          onChange(data[0].value)
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
    const iconPaths: Record<string, string> = {
      openai: "/icons/openai.png",
      anthropic: "/icons/anthropic-1.svg",
      gemini: "/icons/Google_Gemini_icon_2025.svg.png",
      grok: "/icons/Grok-icon.svg.png",
      perplexity: "/icons/perplexity-e6a4e1t06hd6dhczot580o.webp",
    }
    
    const iconPath = iconPaths[provider]
    if (iconPath) {
      return (
        <img
          src={iconPath}
          alt={provider}
          className="w-4 h-4 object-contain"
        />
      )
    }
    return <Sparkles className="w-4 h-4" />
  }

  const groupedModels = models.reduce(
    (acc, model) => {
      const provider = model.provider
      if (!acc[provider]) acc[provider] = []
      acc[provider].push(model)
      return acc
    },
    {} as Record<string, Model[]>,
  )

  if (loading) {
    return <div className="h-10 bg-muted rounded-lg animate-pulse w-full max-w-xs" />
  }

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-full md:w-64 gap-2">
        <div className="flex items-center gap-2">
          {value && models.find(m => m.value === value) && (
            getProviderIcon(models.find(m => m.value === value)!.provider)
          )}
          <SelectValue />
        </div>
      </SelectTrigger>
      <SelectContent className="max-h-64">
        {Object.entries(groupedModels).map(([provider, providerModels]) => (
          <div key={provider}>
            <div className="px-2 py-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {provider}
            </div>
            {providerModels.map((model) => (
              <SelectItem key={model.value} value={model.value} disabled={userTier === "free" && model.tier !== "free"}>
                <div className="flex items-center gap-2">
                  {model.label}
                  {model.tier !== "free" && (
                    <Badge variant="outline" className="text-xs">
                      {model.tier}
                    </Badge>
                  )}
                </div>
              </SelectItem>
            ))}
          </div>
        ))}
      </SelectContent>
    </Select>
  )
}

