"use client"

import type React from "react"
import { useState, useEffect, useRef } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatMessage } from "@/components/chat-message"
import { ModelToggleGroup } from "@/components/model-toggle-group"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useChatSSE } from "@/hooks/use-chat-sse"
import { getTokenUsage, getSubscription } from "@/lib/api"
import { Send, AlertCircle, Sparkles } from "lucide-react"

const DEMO_USER_ID = process.env.NEXT_PUBLIC_DEFAULT_USER_ID || "demo-user-1"

export default function ChatPage() {
  const [selectedModels, setSelectedModels] = useState<string[]>([])
  const [inputValue, setInputValue] = useState("")
  const [usage, setUsage] = useState<any>(null)
  const [subscription, setSubscription] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // Auto-scroll ref
  const bottomRef = useRef<HTMLDivElement>(null)

  const { messages, sendMessage, isStreaming, error } = useChatSSE(DEMO_USER_ID)

  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        const [usageData, subData] = await Promise.all([getTokenUsage(DEMO_USER_ID), getSubscription(DEMO_USER_ID)])
        setUsage(usageData)
        setSubscription(subData)
      } catch (err) {
        console.error("Failed to fetch initial data:", err)
      } finally {
        setLoading(false)
      }
    }
    fetchInitialData()
  }, [])

  // Auto-scroll effect
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming || selectedModels.length === 0) return

    const message = inputValue
    setInputValue("")

    await sendMessage(message, selectedModels, (delta) => {
      setUsage((prev: any) =>
        prev
          ? {
              ...prev,
              tokens_remaining: delta.tokens_remaining,
              credits_remaining: delta.credits_remaining,
            }
          : null,
      )
    })
  }

  const handleNewChat = () => {
    setInputValue("")
    // Ideally clear messages via hook logic here
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
      <Sidebar onNewChat={handleNewChat} />

      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Header */}
        <div className="border-b border-border bg-card/50 backdrop-blur-sm p-4 flex items-center justify-between z-10 h-16 shrink-0">
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

        {/* Chat Area - Scrollable */}
        <div className="flex-1 overflow-y-auto no-scrollbar bg-background/50">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-6 opacity-40">
              <div className="bg-muted rounded-full p-6">
                 <Sparkles className="w-12 h-12 text-muted-foreground" />
              </div>
              <p className="text-lg font-medium">Select models below and start the arena</p>
            </div>
          ) : (
            // REMOVED max-w constraints here to allow full width for columns
            <div className="w-full h-full p-6">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} className="h-4" />
            </div>
          )}
        </div>

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

                {/* Input Container */}
                <div className="bg-card border border-border rounded-xl shadow-lg p-4 space-y-4">
                    <ModelToggleGroup 
                        selectedModels={selectedModels} 
                        onSelectionChange={setSelectedModels}
                        userTier={subscription?.tier_id}
                    />

                    <form onSubmit={handleSendMessage} className="flex gap-3 relative">
                        <Input
                            placeholder={selectedModels.length === 0 ? "Select at least one model..." : `Ask ${selectedModels.length} models...`}
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            disabled={isStreaming || selectedModels.length === 0}
                            className="flex-1 pr-12 py-6 text-base shadow-inner bg-muted/20 border-muted-foreground/20"
                        />
                        <Button 
                            type="submit" 
                            disabled={isStreaming || !inputValue.trim() || selectedModels.length === 0} 
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