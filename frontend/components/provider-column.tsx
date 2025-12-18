"use client"

import { useState } from "react"
import { ExtendedMessage } from "@/hooks/use-chat-sse"
import { Sparkles, AlertTriangle, Bot, ThumbsUp, ThumbsDown, Download } from "lucide-react"
import { cn } from "@/lib/utils"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import type { ModelRichInfo } from "@/lib/api"

interface ProviderColumnProps {
  provider: string
  providerIcon?: string
  models: ModelRichInfo[]
  selectedModelId: string
  isEnabled: boolean
  messages: ExtendedMessage[]
  isStreaming: boolean
  onToggle: (enabled: boolean) => void
  onModelChange: (modelId: string) => void
}

export function ProviderColumn({
  provider,
  providerIcon,
  models,
  selectedModelId,
  isEnabled,
  messages,
  isStreaming,
  onToggle,
  onModelChange,
}: ProviderColumnProps) {
  const isCollapsed = !isEnabled
  const selectedModel = models.find(m => m.value === selectedModelId) || models[0]

  // Filter messages to show only assistant responses from the selected model
  const relevantMessages = messages.filter((msg) => {
    if (msg.role === "assistant" && msg.variations && msg.variations[selectedModelId]) return true
    return false
  })

  return (
    <div 
      data-model-column
      className={cn(
        "flex flex-col h-full border-r border-border bg-background transition-all duration-300",
        isCollapsed ? "min-w-[60px] max-w-[60px]" : "min-w-[400px] max-w-[500px]"
      )}
    >
      {/* Provider Header - Fixed at top with Toggle and Dropdown */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm border-b border-border p-3">
        <div className="flex items-center gap-2">
          {providerIcon ? (
            <img
              src={providerIcon}
              alt={provider}
              className="w-5 h-5 object-contain flex-shrink-0"
            />
          ) : (
            <Sparkles className="w-5 h-5 text-primary flex-shrink-0" />
          )}
          {!isCollapsed && (
            <>
              <span className="font-semibold text-sm capitalize truncate">{provider}</span>
              <Select value={selectedModelId} onValueChange={onModelChange}>
                <SelectTrigger className="h-7 text-xs border-0 shadow-none focus:ring-0 w-auto min-w-[140px]">
                  <SelectValue>{selectedModel?.label || selectedModelId}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model.value} value={model.value}>
                      {model.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {isStreaming && (
                <span className="relative flex h-2 w-2 ml-auto">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
                </span>
              )}
            </>
          )}
          <Switch 
            checked={isEnabled} 
            onCheckedChange={onToggle}
            className="ml-auto"
          />
        </div>
      </div>

      {/* Messages - Scrollable (only assistant responses from selected model) */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {relevantMessages.length === 0 ? (
            <div className="text-center text-sm text-muted-foreground py-8">
              No response yet
            </div>
          ) : (
            relevantMessages.map((msg) => {
              const variation = msg.variations?.[selectedModelId]
              if (!variation) return null

              return (
                <div key={`${msg.id}-${selectedModelId}`} className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex gap-2 max-w-[85%]">
                    <div className="w-6 h-6 rounded-full bg-muted text-muted-foreground flex items-center justify-center flex-shrink-0 mt-1">
                      <Bot className="w-3 h-3" />
                    </div>
                    <div className="rounded-lg rounded-bl-none px-3 py-2 bg-muted/50 border border-border text-sm flex-1">
                      {variation.error ? (
                        <div className="text-destructive text-sm flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4" />
                          <span>{variation.error}</span>
                        </div>
                      ) : (
                        <div className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                          {variation.content}
                          {variation.isStreaming && (
                            <span className="inline-block w-1.5 h-4 bg-primary/50 ml-1 animate-pulse align-middle" />
                          )}
                        </div>
                      )}
                      {!variation.isStreaming && !variation.error && (
                        <>
                          <div className="mt-2 pt-2 border-t border-border/50 text-[10px] text-muted-foreground flex justify-between">
                            <span>Tokens: {variation.tokens_used || 0}</span>
                            <span>Credits: {variation.credits_used || 0}</span>
                          </div>
                          <div className="mt-2 flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs"
                              onClick={async () => {
                                try {
                                  const { submitFeedback } = await import("@/lib/api")
                                  await submitFeedback(msg.id, "upvote")
                                } catch (err) {
                                  console.error("Failed to submit upvote:", err)
                                }
                              }}
                            >
                              <ThumbsUp className="w-3 h-3 mr-1" />
                              Upvote
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs"
                              onClick={async () => {
                                try {
                                  const { submitFeedback } = await import("@/lib/api")
                                  await submitFeedback(msg.id, "downvote")
                                } catch (err) {
                                  console.error("Failed to submit downvote:", err)
                                }
                              }}
                            >
                              <ThumbsDown className="w-3 h-3 mr-1" />
                              Downvote
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 px-2 text-xs"
                              onClick={async () => {
                                try {
                                  const { submitFeedback } = await import("@/lib/api")
                                  await submitFeedback(msg.id, "download")
                                  // Also trigger actual download
                                  const blob = new Blob([variation.content], { type: "text/plain" })
                                  const url = URL.createObjectURL(blob)
                                  const a = document.createElement("a")
                                  a.href = url
                                  a.download = `response-${selectedModelId}-${msg.id}.txt`
                                  document.body.appendChild(a)
                                  a.click()
                                  document.body.removeChild(a)
                                  URL.revokeObjectURL(url)
                                } catch (err) {
                                  console.error("Failed to download:", err)
                                }
                              }}
                            >
                              <Download className="w-3 h-3 mr-1" />
                              Download
                            </Button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

