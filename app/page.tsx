"use client"

import type React from "react"

import { useState, useEffect } from "react"
import { Sidebar } from "@/components/sidebar"
import { ChatMessage } from "@/components/chat-message"
import { ModelSelector } from "@/components/model-selector"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { useChatSSE } from "@/hooks/use-chat-sse"
import { getTokenUsage, getSubscription } from "@/lib/api"
import { Zap, Send, AlertCircle, Sparkles } from "lucide-react"

const DEMO_USER_ID = process.env.NEXT_PUBLIC_DEFAULT_USER_ID || "demo-user-1"

export default function ChatPage() {
  const [selectedModel, setSelectedModel] = useState("")
  const [inputValue, setInputValue] = useState("")
  const [usage, setUsage] = useState<any>(null)
  const [subscription, setSubscription] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [loadingUsage, setLoadingUsage] = useState(false)

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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming) return

    const message = inputValue
    setInputValue("")
    setLoadingUsage(true)

    await sendMessage(message, selectedModel || "gemini-2.5-flash", (delta) => {
      setUsage((prev) =>
        prev
          ? {
              ...prev,
              tokens_remaining: delta.tokens_remaining,
              credits_remaining: delta.credits_remaining,
            }
          : null,
      )
    })

    setLoadingUsage(false)
  }

  const handleNewChat = () => {
    // In a real app, this would reset the conversation
    setInputValue("")
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar onNewChat={handleNewChat} />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="border-b border-border bg-card/50 backdrop-blur-sm p-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="font-semibold flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                AI Fiesta
              </h1>
              <p className="text-xs text-muted-foreground">Multi-Model AI Chat</p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            {usage && (
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Tokens</p>
                  <p className="font-semibold text-sm">
                    {usage.tokens_remaining}/{usage.tokens_limit}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted-foreground">Credits</p>
                  <p className="font-semibold text-sm">
                    {usage.credits_remaining}/{usage.credits_limit}
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-6 no-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-6">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center mx-auto mb-3">
                  <Sparkles className="w-8 h-8 text-primary" />
                </div>
                <h2 className="text-xl font-semibold mb-2">Start a conversation</h2>
                <p className="text-muted-foreground text-sm">
                  Pick a model, type a prompt, and we’ll stream the response in real-time.
                </p>
              </div>

              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {[
                  "Summarize this article into 3 bullets",
                  "Explain transformers like I’m 12",
                  "Draft a welcome email for new users",
                  "Brainstorm product taglines",
                ].map((prompt) => (
                  <Button
                    key={prompt}
                    variant="outline"
                    size="sm"
                    onClick={() => setInputValue(prompt)}
                    className="whitespace-nowrap"
                  >
                    {prompt}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto">
              {messages.map((msg, idx) => (
                <ChatMessage key={msg.id} message={msg} isStreaming={isStreaming && idx === messages.length - 1} />
              ))}
            </div>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="px-6 py-3 bg-destructive/10 border border-destructive/20 rounded-lg mx-6 flex items-gap-2 gap-2">
            <AlertCircle className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
            <p className="text-sm text-destructive">{error}</p>
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-border bg-card/50 backdrop-blur-sm p-6">
          <div className="max-w-3xl mx-auto space-y-4">
            {/* Model Selector and Options */}
            <div className="flex flex-col md:flex-row items-center gap-3">
              <ModelSelector value={selectedModel} onChange={setSelectedModel} userTier={subscription?.tier_id} />

              <div className="flex items-center gap-2">
                <Badge variant="secondary" className="gap-1 hidden md:flex">
                  <Zap className="w-3 h-3" />
                  Super Fiesta
                </Badge>
              </div>
            </div>

            {/* Chat Input */}
            <form onSubmit={handleSendMessage} className="flex gap-3">
              <Input
                placeholder="Ask me anything..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isStreaming}
                className="flex-1"
              />
              <Button type="submit" disabled={isStreaming || !inputValue.trim()} size="icon" className="rounded-full">
                <Send className="w-4 h-4" />
              </Button>
            </form>

          </div>
        </div>
      </div>
    </div>
  )
}

