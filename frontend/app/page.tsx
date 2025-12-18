"use client"

import type React from "react"
import { useState, useEffect, useRef, Suspense } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatMessage } from "@/components/chat-message"
import { MultiChatModelSelectors } from "@/components/multi-chat-model-selectors"
import { SuperFiestaSelector } from "@/components/super-fiesta-selector"
import { ModeToggle } from "@/components/mode-toggle"
import { ProviderColumn } from "@/components/provider-column"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useChatSSE } from "@/hooks/use-chat-sse"
import { getTokenUsage, getSubscription, getAuthToken, getAvailableModels, type ModelRichInfo } from "@/lib/api"
import { useRouter, useSearchParams } from "next/navigation"
import { Send, AlertCircle, Sparkles, User } from "lucide-react"

type Mode = "multi-chat" | "super-fiesta"

function ChatPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const conversationIdFromUrl = searchParams.get("id")
  const [mode, setMode] = useState<Mode>("multi-chat")
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState<string>("")
  const [inputValue, setInputValue] = useState("")
  const [usage, setUsage] = useState<any>(null)
  const [subscription, setSubscription] = useState<any>(null)
  const [availableModels, setAvailableModels] = useState<ModelRichInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [sidebarRefreshTrigger, setSidebarRefreshTrigger] = useState(0)
  const [isViewingConversation, setIsViewingConversation] = useState(false)
  const [conversationMode, setConversationMode] = useState<Mode | null>(null)
  // Provider-based selection for multi-chat mode
  const [providerModelMap, setProviderModelMap] = useState<Record<string, string>>({}) // provider -> modelId
  const [enabledProviders, setEnabledProviders] = useState<string[]>([]) // List of enabled providers

  // Auto-scroll refs
  const bottomRef = useRef<HTMLDivElement>(null)
  const columnsContainerRef = useRef<HTMLDivElement>(null)

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
        
        // Initialize provider-based selection if empty and not viewing a conversation
        if (!conversationIdFromUrl && enabledProviders.length === 0 && modelsData.length > 0) {
          // Group by provider and select first model from each
          const grouped: Record<string, ModelRichInfo[]> = {}
          modelsData
            .filter(m => subData?.tier_id === "free" ? m.tier === "free" : true)
            .forEach(model => {
              if (!grouped[model.provider]) grouped[model.provider] = []
              grouped[model.provider].push(model)
            })
          
          const initialProviders = Object.keys(grouped).slice(0, 3) // Enable first 3 providers
          const initialProviderModelMap: Record<string, string> = {}
          initialProviders.forEach(provider => {
            if (grouped[provider].length > 0) {
              initialProviderModelMap[provider] = grouped[provider][0].value
            }
          })
          
          setProviderModelMap(initialProviderModelMap)
          setEnabledProviders(initialProviders)
          setSelectedModels(initialProviders.map(p => initialProviderModelMap[p]).filter(Boolean))
        }
        
        // If there's a conversation ID in URL, load it
        if (conversationIdFromUrl) {
          const loadedMode = await loadConversation(conversationIdFromUrl)
          if (loadedMode === "multi-chat" || loadedMode === "super-fiesta") {
            setMode(loadedMode)
            setConversationMode(loadedMode)
            setIsViewingConversation(true)
          }
        }
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
  }, [router, conversationIdFromUrl, loadConversation])

  // Auto-scroll effect for super-fiesta mode
  useEffect(() => {
    if (mode === "super-fiesta" || (mode === "multi-chat" && selectedModels.length === 0)) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages, mode, selectedModels.length])

  // Auto-scroll effect for multi-chat mode columns
  useEffect(() => {
    if (mode === "multi-chat" && selectedModels.length > 0 && columnsContainerRef.current) {
      // Scroll each column container to bottom when new messages arrive
      const columns = columnsContainerRef.current.querySelectorAll('[data-model-column]')
      columns.forEach((column) => {
        column.scrollTo({ top: column.scrollHeight, behavior: "smooth" })
      })
    }
  }, [messages, isStreaming, mode, selectedModels.length])

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
    }, currentConversationId, mode) // Pass current conversation_id and mode to maintain conversation continuity
    
    // Refresh sidebar after message is sent (with a small delay to ensure backend has saved)
    setTimeout(() => {
      setSidebarRefreshTrigger(prev => prev + 1)
    }, 1000)
  }


  const handleConversationSelect = async (conversationId: string) => {
    const loadedMode = await loadConversation(conversationId)
    // Set mode if conversation has one and lock it
    if (loadedMode === "multi-chat" || loadedMode === "super-fiesta") {
      setMode(loadedMode)
      setConversationMode(loadedMode)
      setIsViewingConversation(true)
      // Navigate to conversation URL
      router.push(`/?id=${conversationId}`)
    }
  }

  const handleNewChat = () => {
    setInputValue("")
    clearMessages()
    setIsViewingConversation(false)
    setConversationMode(null)
    router.push("/")
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
        refreshTrigger={sidebarRefreshTrigger}
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
          {/* Model Selection at Top - Only show in Super Fiesta mode */}
          {mode === "super-fiesta" && (
            <div className="flex items-center gap-3 overflow-x-auto pb-2">
              <SuperFiestaSelector
                value={selectedModel}
                onChange={setSelectedModel}
                userTier={subscription?.tier_id}
              />
            </div>
          )}
        </div>

        {/* Main Content Area */}
        {mode === "multi-chat" ? (
          /* Multi-Chat Mode: Separate full-height containers with horizontal scrolling */
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Shared User Messages Area - Show once at the top */}
            {messages.filter(m => m.role === "user").length > 0 && (
              <div className="flex-shrink-0 border-b border-border bg-background/50 px-4 py-3">
                <div className="space-y-2">
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
              </div>
            )}
            
            {/* Provider Columns - Full height, horizontal scrolling - Show providers, not individual models */}
            <div ref={columnsContainerRef} className="flex-1 flex overflow-x-auto overflow-y-hidden">
              {(() => {
                // Group models by provider
                const grouped: Record<string, ModelRichInfo[]> = {}
                availableModels
                  .filter(m => subscription?.tier_id !== "free" || m.tier === "free")
                  .forEach(model => {
                    if (!grouped[model.provider]) grouped[model.provider] = []
                    grouped[model.provider].push(model)
                  })
                
                const providers = Object.keys(grouped).sort()
                
                return providers.map((provider) => {
                  const models = grouped[provider]
                  const selectedModelId = providerModelMap[provider] || models[0]?.value
                  const isEnabled = enabledProviders.includes(provider)
                  const providerIcon = provider === "openai" ? "/icons/openai.png" :
                    provider === "anthropic" ? "/icons/anthropic-1.svg" :
                    provider === "gemini" ? "/icons/Google_Gemini_icon_2025.svg.png" :
                    provider === "grok" ? "/icons/Grok-icon.svg.png" :
                    provider === "perplexity" ? "/icons/perplexity-e6a4e1t06hd6dhczot580o.webp" :
                    undefined
                  
                  return (
                    <ProviderColumn
                      key={provider}
                      provider={provider}
                      providerIcon={providerIcon}
                      models={models}
                      selectedModelId={selectedModelId}
                      isEnabled={isEnabled}
                      messages={messages}
                      isStreaming={isStreaming}
                      onToggle={(enabled) => {
                        if (enabled) {
                          if (!enabledProviders.includes(provider)) {
                            setEnabledProviders([...enabledProviders, provider])
                            if (!providerModelMap[provider] && models.length > 0) {
                              setProviderModelMap({ ...providerModelMap, [provider]: models[0].value })
                              setSelectedModels([...selectedModels, models[0].value])
                            }
                          }
                        } else {
                          // Don't allow disabling if it's the last enabled provider
                          if (enabledProviders.length > 1) {
                            const modelToRemove = providerModelMap[provider]
                            setEnabledProviders(enabledProviders.filter(p => p !== provider))
                            setSelectedModels(selectedModels.filter(m => m !== modelToRemove))
                          }
                        }
                      }}
                      onModelChange={(modelId) => {
                        // Update the selected model for this provider
                        const oldModelId = providerModelMap[provider]
                        setProviderModelMap({ ...providerModelMap, [provider]: modelId })
                        // Update selectedModels array
                        setSelectedModels(selectedModels.map(m => m === oldModelId ? modelId : m))
                      }}
                    />
                  )
                })
              })()}
            </div>
          </div>
        ) : (
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

                {/* Mode Toggle Buttons - Above Input - Disabled when viewing conversation */}
                {!isViewingConversation && (
                  <div className="flex items-center justify-center gap-3">
                    <ModeToggle mode={mode} onModeChange={setMode} />
                  </div>
                )}

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

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    }>
      <ChatPageContent />
    </Suspense>
  )
}