"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatMessage } from "@/components/chat-message"
import { MultiChatModelSelectors } from "@/components/multi-chat-model-selectors"
import { SuperFiestaSelector } from "@/components/super-fiesta-selector"
import { ModeToggle } from "@/components/mode-toggle"
import { ModelResponseColumn } from "@/components/model-response-column"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useChatSSE } from "@/hooks/use-chat-sse"
import { getTokenUsage, getSubscription, getAuthToken, getAvailableModels, type ModelRichInfo } from "@/lib/api"
import { useRouter } from "next/navigation"
import { Send, AlertCircle, Sparkles, User } from "lucide-react"

type Mode = "multi-chat" | "super-fiesta"

export default function ChatPage() {
  const router = useRouter()
  const [mode, setMode] = useState<Mode>("multi-chat")
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [inputValue, setInputValue] = useState("")
  const [usage, setUsage] = useState<any>(null)
  const [subscription, setSubscription] = useState<any>(null)
  const [availableModels, setAvailableModels] = useState<ModelRichInfo[]>([])
  const [loading, setLoading] = useState(true)

  // Auto-scroll ref
  const bottomRef = useRef<HTMLDivElement>(null)

  const { messages, sendMessage, isStreaming, error, loadConversation, clearMessages, currentConversationId } = useChatSSE()

  useEffect(() => {
    const fetchInitialData = async () => {
      // Check authentication first
      const token = getAuthToken()
      if (!token) {
        router.push("/login")
        setLoading(false)
        return
      }

      try {
        const [usageData, subData, modelsData] = await Promise.all([
          getTokenUsage(), 
          getSubscription(),
          getAvailableModels()
        ])
        setUsage(usageData)
        setSubscription(subData)
        setAvailableModels(modelsData)
      } catch (err: any) {
        console.error("Failed to fetch initial data:", err)
        // If 401 or 403, redirect to login
        const errorMessage = err?.message || ""
        if (errorMessage.includes("401") || errorMessage.includes("403") || errorMessage.includes("Unauthorized") || errorMessage.includes("Failed to fetch")) {
          // Check if it's actually an auth error by checking response status
          if (err instanceof Response || errorMessage.includes("401") || errorMessage.includes("403")) {
            router.push("/login")
            return
          }
        }
      } finally {
        setLoading(false)
      }
    }
    fetchInitialData()
  }, [router])

  // Auto-scroll effect
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    // For multi-chat, use all selected models (they're already filtered by enabled state in the component)
    const modelsToUse = mode === "multi-chat" ? selectedModels : (selectedModel ? [selectedModel] : [])
    if (!inputValue.trim() || isStreaming || modelsToUse.length === 0) return

    const message = inputValue
    setInputValue("")

    await sendMessage(message, modelsToUse, (delta) => {
      setUsage((prev: any) =>
        prev
          ? {
              ...prev,
              tokens_remaining: delta.tokens_remaining,
              credits_remaining: delta.credits_remaining,
            }
          : null,
      )
    }, currentConversationId) // Pass current conversation_id to maintain conversation continuity
  }

  const handleNewChat = () => {
    setInputValue("")
    clearMessages()
  }

  const handleConversationSelect = async (conversationId: string) => {
    await loadConversation(conversationId)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background font-sans">
      <Sidebar 
        onNewChat={handleNewChat} 
        onConversationSelect={handleConversationSelect}
      />

      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header */}
        <div className="border-b border-border bg-card/50 backdrop-blur-sm p-4 z-10 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <h1 className="font-semibold flex items-center gap-2 text-lg">
                <Sparkles className="w-5 h-5 text-primary" />
                AI Fiesta
              </h1>
            </div>
            <div className="flex items-center gap-6 text-sm">
              {usage && (
                <>
                  <div className="text-right">
                    <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Tokens</p>
                    <p className="font-mono font-medium">{usage.tokens_remaining}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase text-muted-foreground font-bold tracking-wider">Credits</p>
                    <p className="font-mono font-medium text-primary">{usage.credits_remaining}</p>
                  </div>
                </>
              )}
            </div>
          </div>
          {/* Model Selection at Top */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3 overflow-x-auto pb-2">
              {mode === "multi-chat" ? (
                // Multi-Chat: Show multiple model selectors with toggles
                <MultiChatModelSelectors
                  selectedModels={selectedModels}
                  onModelsChange={setSelectedModels}
                  userTier={subscription?.tier_id}
                />
              ) : (
                // Super Fiesta: Show single model selector
                <SuperFiestaSelector
                  value={selectedModel}
                  onChange={setSelectedModel}
                  userTier={subscription?.tier_id}
                />
              )}
            </div>
            
            {/* Model Response Columns - Directly below model selectors (only in multi-chat mode) */}
            {mode === "multi-chat" && selectedModels.length > 0 && (
              <div className="flex flex-col gap-2 flex-1 overflow-hidden bg-background/50 min-h-[400px] max-h-[600px]">
                {/* Shared User Messages Area - Show once above all columns */}
                <div className="flex-shrink-0 overflow-y-auto max-h-[150px] px-4 py-2 space-y-2 border-b border-border">
                  {messages.filter(m => m.role === "user").map((msg) => (
                    <div key={msg.id} className="flex justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
                      <div className="flex gap-2 flex-row-reverse max-w-[85%]">
                        <div className="w-6 h-6 rounded-full bg-primary/20 text-primary flex items-center justify-center flex-shrink-0 mt-1">
                          <User className="w-3 h-3" />
                        </div>
                        <div className="rounded-lg rounded-br-none px-3 py-2 bg-primary text-primary-foreground text-sm">
                          <p className="whitespace-pre-wrap break-words">{msg.content}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                
                {/* Model Response Columns */}
                <div className="flex h-full overflow-x-auto">
                  {selectedModels.map((modelId) => {
                    // Find model info from availableModels
                    const modelInfo = availableModels.find((m) => m.value === modelId) || 
                      { value: modelId, label: modelId, provider: "unknown" }
                    const providerIcon = modelInfo.provider === "openai" ? "/icons/openai.png" :
                      modelInfo.provider === "anthropic" ? "/icons/anthropic-1.svg" :
                      modelInfo.provider === "gemini" ? "/icons/Google_Gemini_icon_2025.svg.png" :
                      modelInfo.provider === "grok" ? "/icons/Grok-icon.svg.png" :
                      modelInfo.provider === "perplexity" ? "/icons/perplexity-e6a4e1t06hd6dhczot580o.webp" :
                      undefined
                    
                    return (
                      <ModelResponseColumn
                        key={modelId}
                        modelId={modelId}
                        modelLabel={modelInfo.label || modelId}
                        providerIcon={providerIcon}
                        isEnabled={true}
                        messages={messages}
                        isStreaming={isStreaming}
                      />
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Chat Area - Standard view for Super Fiesta or when no models selected */}
        {!(mode === "multi-chat" && selectedModels.length > 0) && (
          /* Standard Chat View for Super Fiesta mode or when no models selected */
          <div className="flex-1 overflow-y-auto no-scrollbar bg-background/50">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center gap-6 opacity-40">
                <div className="bg-muted rounded-full p-6">
                  <Sparkles className="w-12 h-12 text-muted-foreground" />
                </div>
                <p className="text-lg font-medium">Select models below and start the arena</p>
              </div>
            ) : (
              <div className="w-full h-full p-6">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                <div ref={bottomRef} className="h-4" />
              </div>
            )}
          </div>
        )}

        {/* Floating Controls Area */}
        <div className="p-6 bg-gradient-to-t from-background via-background to-transparent z-20">
            <div className="max-w-[95%] mx-auto space-y-4">
                
                {/* Error Banner */}
                {error && (
                    <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-lg flex items-center gap-2 animate-in slide-in-from-bottom-2">
                        <AlertCircle className="w-4 h-4 text-destructive" />
                        <p className="text-sm text-destructive font-medium">{error}</p>
                    </div>
                )}

                {/* Mode Toggle Buttons - Above Input */}
                <div className="flex items-center justify-center gap-3">
                  <ModeToggle mode={mode} onModeChange={setMode} />
                </div>

                {/* Input Container */}
                <div className="bg-card border border-border rounded-xl shadow-lg p-4">
                    <form onSubmit={handleSendMessage} className="flex gap-3 relative">
                        <Input
                            placeholder={
                              mode === "multi-chat" 
                                ? (selectedModels.length === 0 ? "Select at least one model..." : `Ask ${selectedModels.length} models...`)
                                : (selectedModel ? `Ask ${selectedModel}...` : "Select a model...")
                            }
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            disabled={isStreaming || (mode === "multi-chat" ? selectedModels.length === 0 : !selectedModel)}
                            className="flex-1 pr-12 py-6 text-base shadow-inner bg-muted/20 border-muted-foreground/20"
                        />
                        <Button 
                            type="submit" 
                            disabled={
                              isStreaming || 
                              !inputValue.trim() || 
                              (mode === "multi-chat" ? selectedModels.length === 0 : !selectedModel)
                            } 
                            size="icon" 
                            className="absolute right-1.5 top-1.5 h-9 w-9 rounded-lg transition-all shadow-sm"
                        >
                            <Send className="w-4 h-4" />
                        </Button>
                    </form>
                </div>
            </div>
        </div>
      </div>
    </div>
  )
}