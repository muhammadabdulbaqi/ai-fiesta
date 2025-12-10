"use client"

import { useState, useRef, useCallback } from "react"
import type { Message } from "@/lib/api"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

interface SSEMessage {
  type: "chunk" | "done" | "error"
  content?: string
  tokens_used?: number
  tokens_remaining?: number
  credits_used?: number
  credits_remaining?: number
  model?: string
  error?: string
  message?: string
}

interface UsageDelta {
  tokens_remaining: number
  credits_remaining: number
}

export function useChatSSE(userId: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [usage, setUsage] = useState<UsageDelta | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const sendMessage = useCallback(
    async (prompt: string, model: string, onUsageUpdate?: (usage: UsageDelta) => void) => {
      setError(null)
      setUsage(null)

      // Add user message
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: prompt,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, userMessage])

      // Create assistant message placeholder
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])

      setIsStreaming(true)
      abortControllerRef.current = new AbortController()

      try {
        const response = await fetch(`${API_URL}/stream/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            prompt,
            model,
            user_id: userId,
            max_tokens: 1000,
            temperature: 0.7,
          }),
          signal: abortControllerRef.current.signal,
        })

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        if (!response.body) {
          throw new Error("No response body")
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split("\n\n")
          buffer = events.pop() || ""

          for (const event of events) {
            if (!event.trim()) continue

            const lines = event.split("\n")
            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const jsonStr = line.slice(6)
                try {
                  const data: SSEMessage = JSON.parse(jsonStr)

                                    if (data.type === "chunk" && data.content) {
                    setMessages((prev) => {
                      // 1. Copy the previous array
                      const updatedMessages = [...prev]
                      
                      // 2. Identify the last message index
                      const lastIndex = updatedMessages.length - 1
                      
                      // 3. Create a shallow COPY of the last message object
                      // (Crucial: Don't mutate prev[lastIndex] directly!)
                      const updatedMessage = {
                        ...updatedMessages[lastIndex],
                        content: updatedMessages[lastIndex].content + (data.content || "")
                      }

                      // 4. Replace the message in the new array
                      updatedMessages[lastIndex] = updatedMessage
                      
                      return updatedMessages
                    })
                  } else if (data.type === "done") {
                    setMessages((prev) => {
                      const updatedMessages = [...prev]
                      const lastIndex = updatedMessages.length - 1
                      
                      // Same logic here: Copy before modifying
                      const updatedMessage = {
                        ...updatedMessages[lastIndex],
                        tokens_used: data.tokens_used,
                        credits_used: data.credits_used,
                        model: data.model
                      }
                      
                      updatedMessages[lastIndex] = updatedMessage
                      return updatedMessages
                    })

                    if (data.tokens_remaining !== undefined) {
                      const delta = {
                        tokens_remaining: data.tokens_remaining,
                        credits_remaining: data.credits_remaining || 0,
                      }
                      setUsage(delta)
                      onUsageUpdate?.(delta)
                    }

                    setIsStreaming(false)
                  } else if (data.type === "error") {
                    setError(data.message || data.error || "Stream error")
                    setIsStreaming(false)
                  }
                } catch (e) {
                  console.error("Failed to parse SSE data:", e)
                }
              }
            }
          }
        }
      } catch (err: any) {
        if (err.name !== "AbortError") {
          setError(err.message || "Streaming failed")
          console.error("Streaming failed:", err)
        }
        setIsStreaming(false)
      }
    },
    [userId],
  )

  const stopGeneration = useCallback(() => {
    abortControllerRef.current?.abort()
    setIsStreaming(false)
  }, [])

  return {
    messages,
    sendMessage,
    isStreaming,
    error,
    usage,
    stopGeneration,
    clearMessages: () => setMessages([]),
  }
}

