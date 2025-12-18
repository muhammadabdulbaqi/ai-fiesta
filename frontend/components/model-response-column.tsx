"use client"

import { useState } from "react"
import { ExtendedMessage, ModelResponseVariation } from "@/hooks/use-chat-sse"
import { Sparkles, AlertTriangle, Bot, User } from "lucide-react"
import { cn } from "@/lib/utils"

interface ModelResponseColumnProps {
  modelId: string
  modelLabel: string
  providerIcon?: string
  isEnabled: boolean
  messages: ExtendedMessage[]
  isStreaming: boolean
}

export function ModelResponseColumn({
  modelId,
  modelLabel,
  providerIcon,
  isEnabled,
  messages,
  isStreaming,
}: ModelResponseColumnProps) {
  // Filter messages to show only assistant responses from this model
  // User messages are shown separately in a shared area, not in each column
  const relevantMessages = messages.filter((msg) => {
    if (msg.role === "assistant" && msg.variations && msg.variations[modelId]) return true
    return false
  })

  return (
    <div className={cn(
      "flex flex-col h-full min-w-[300px] max-w-[400px]",
      !isEnabled && "opacity-50"
    )}>
      {/* Model Header - Fixed at top */}
      <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm border-b border-border p-3">
        <div className="flex items-center gap-2">
          {providerIcon ? (
            <img
              src={providerIcon}
              alt={modelId}
              className="w-5 h-5 object-contain"
            />
          ) : (
            <Sparkles className="w-5 h-5 text-primary" />
          )}
          <span className="font-semibold text-sm">{modelLabel}</span>
          {isStreaming && (
            <span className="relative flex h-2 w-2 ml-auto">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-primary"></span>
            </span>
          )}
        </div>
      </div>

      {/* Messages - Scrollable (only assistant responses, no user messages) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {relevantMessages.length === 0 ? (
          <div className="text-center text-sm text-muted-foreground py-8">
            No response yet
          </div>
        ) : (
          relevantMessages.map((msg) => {
            // Assistant message for this model
            const variation = msg.variations?.[modelId]
            if (!variation) return null

            return (
              <div key={`${msg.id}-${modelId}`} className="flex justify-start animate-in fade-in slide-in-from-bottom-2 duration-300">
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
                      <div className="mt-2 pt-2 border-t border-border/50 text-[10px] text-muted-foreground flex justify-between">
                        <span>Tokens: {variation.tokens_used || 0}</span>
                        <span>Credits: {variation.credits_used || 0}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

