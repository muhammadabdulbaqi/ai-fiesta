"use client"

import { useState, useRef, useCallback } from "react"
import type { Message } from "@/lib/api"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// Extended types for internal hook usage
export interface ModelResponseVariation {
  modelId: string
  content: string
  isStreaming: boolean
  tokens_used?: number
  credits_used?: number
  error?: string
}

// Extend the base Message type to support variations
export interface ExtendedMessage extends Omit<Message, 'content'> {
  content?: string // specific to user messages
  variations?: Record<string, ModelResponseVariation> // specific to assistant messages
}

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

// Helper to get auth headers
function getAuthHeaders(): HeadersInit {
  const TOKEN_KEY = "fiesta_auth_token"
  const token = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  return headers
}

export function useChatSSE() {
  const [messages, setMessages] = useState<ExtendedMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [usage, setUsage] = useState<UsageDelta | null>(null)
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Helper to stream a single model
  const streamSingleModel = async (
    prompt: string, 
    modelId: string, 
    assistantMsgId: string, 
    conversationId: string | null,
    signal: AbortSignal,
    onUsageUpdate?: (delta: UsageDelta) => void
  ) => {
    try {
      const response = await fetch(`${API_URL}/stream/chat`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          prompt,
          model: modelId,
          conversation_id: conversationId, // Use shared conversation_id for all models
          max_tokens: 1000,
          temperature: 0.7,
        }),
        signal,
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      if (!response.body) throw new Error("No response body")

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
              try {
                const data: SSEMessage = JSON.parse(line.slice(6))

                setMessages((prev) => {
                  const updatedMessages = [...prev]
                  const msgIndex = updatedMessages.findIndex(m => m.id === assistantMsgId)
                  if (msgIndex === -1) return prev

                  const currentMsg = updatedMessages[msgIndex]
                  // Deep copy variations to ensure immutability
                  const newVariations = { ...currentMsg.variations }
                  
                  if (!newVariations[modelId]) return prev // Should exist

                  // Update the specific model's variation
                  if (data.type === "chunk" && data.content) {
                    newVariations[modelId] = {
                      ...newVariations[modelId],
                      content: newVariations[modelId].content + data.content
                    }
                  } else if (data.type === "done") {
                     newVariations[modelId] = {
                      ...newVariations[modelId],
                      isStreaming: false,
                      tokens_used: data.tokens_used,
                      credits_used: data.credits_used
                    }
                    
                    if (data.tokens_remaining !== undefined) {
                      onUsageUpdate?.({
                        tokens_remaining: data.tokens_remaining,
                        credits_remaining: data.credits_remaining || 0
                      })
                    }
                  } else if (data.type === "error") {
                     newVariations[modelId] = {
                      ...newVariations[modelId],
                      isStreaming: false,
                      error: data.message || data.error
                    }
                  }

                  updatedMessages[msgIndex] = {
                    ...currentMsg,
                    variations: newVariations
                  }
                  
                  return updatedMessages
                })
              } catch (e) {
                console.error("Parse error", e)
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === "AbortError") return

      // Update UI to show error for this specific model
      setMessages((prev) => {
        const updatedMessages = [...prev]
        const msgIndex = updatedMessages.findIndex(m => m.id === assistantMsgId)
        if (msgIndex === -1) return prev
        
        const currentMsg = updatedMessages[msgIndex]
        const newVariations = { ...currentMsg.variations }
        
        if (newVariations[modelId]) {
            newVariations[modelId] = {
                ...newVariations[modelId],
                isStreaming: false,
                error: err.message || "Network error"
            }
        }

        updatedMessages[msgIndex] = { ...currentMsg, variations: newVariations }
        return updatedMessages
      })
    }
  }

  const sendMessage = useCallback(
    async (prompt: string, models: string[], onUsageUpdate?: (usage: UsageDelta) => void, conversationId?: string | null) => {
      setError(null)
      setUsage(null)

      if (models.length === 0) {
        setError("Please select at least one model")
        return
      }

      // Generate or use provided conversation_id - shared across all models
      const sharedConversationId = conversationId || crypto.randomUUID()
      setCurrentConversationId(sharedConversationId)

      // 1. Add User Message
      const userMessage: ExtendedMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: prompt,
        timestamp: new Date(),
      }
      
      // 2. Initialize Assistant Message with slots for each model
      const assistantMsgId = crypto.randomUUID()
      const initialVariations: Record<string, ModelResponseVariation> = {}
      
      models.forEach(modelId => {
        initialVariations[modelId] = {
          modelId,
          content: "",
          isStreaming: true
        }
      })

      const assistantMessage: ExtendedMessage = {
        id: assistantMsgId,
        role: "assistant",
        variations: initialVariations,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMessage, assistantMessage])
      setIsStreaming(true)
      
      abortControllerRef.current = new AbortController()

      // 3. Fire requests in parallel - all use the same conversation_id
      const promises = models.map(modelId => 
        streamSingleModel(
            prompt, 
            modelId, 
            assistantMsgId, 
            sharedConversationId,
            abortControllerRef.current!.signal,
            onUsageUpdate
        )
      )

      await Promise.all(promises)
      setIsStreaming(false)
    },
    [],
  )

  const stopGeneration = useCallback(() => {
    abortControllerRef.current?.abort()
    setIsStreaming(false)
  }, [])

  const loadConversation = useCallback(async (conversationId: string) => {
    try {
      setError(null)
      setIsStreaming(false)
      // Import the API function
      const { getConversationMessages } = await import("@/lib/api")
      const conversationMessages = await getConversationMessages(conversationId)
      
      // Transform conversation messages to ExtendedMessage format
      // Group assistant messages that follow the same user message as variations
      const transformedMessages: ExtendedMessage[] = []
      
      for (let i = 0; i < conversationMessages.length; i++) {
        const msg = conversationMessages[i]
        
        if (msg.role === "user") {
          transformedMessages.push({
            id: msg.id,
            role: "user",
            content: msg.content,
            timestamp: msg.timestamp,
          })
        } else if (msg.role === "assistant") {
          const modelId = msg.model || "unknown"
          
          // Find the last user message (should be the one right before this assistant message)
          // Then find the assistant message that follows that user message
          let lastUserIndex = -1
          for (let j = transformedMessages.length - 1; j >= 0; j--) {
            if (transformedMessages[j].role === "user") {
              lastUserIndex = j
              break
            }
          }
          
          // If there's a user message, check if there's already an assistant message right after it
          if (lastUserIndex !== -1) {
            // Check if the next message after the user message is an assistant message
            const nextIndex = lastUserIndex + 1
            if (nextIndex < transformedMessages.length && transformedMessages[nextIndex].role === "assistant") {
              // Add as variation to existing assistant message
              const existingAssistant = transformedMessages[nextIndex]
              transformedMessages[nextIndex] = {
                ...existingAssistant,
                variations: {
                  ...existingAssistant.variations,
                  [modelId]: {
                    modelId,
                    content: msg.content,
                    isStreaming: false,
                    tokens_used: msg.tokens_used,
                  }
                }
              }
            } else {
              // Create new assistant message after the user message
              const assistantMessage: ExtendedMessage = {
                id: msg.id,
                role: "assistant",
                variations: {
                  [modelId]: {
                    modelId,
                    content: msg.content,
                    isStreaming: false,
                    tokens_used: msg.tokens_used,
                  }
                },
                timestamp: msg.timestamp,
              }
              transformedMessages.push(assistantMessage)
            }
          } else {
            // No user message found, create standalone assistant message
            transformedMessages.push({
              id: msg.id,
              role: "assistant",
              variations: {
                [modelId]: {
                  modelId,
                  content: msg.content,
                  isStreaming: false,
                  tokens_used: msg.tokens_used,
                }
              },
              timestamp: msg.timestamp,
            })
          }
        }
      }
      
      setMessages(transformedMessages)
      // Set the conversation ID so new messages continue in the same conversation
      setCurrentConversationId(conversationId)
    } catch (err: any) {
      setError(err.message || "Failed to load conversation")
      console.error("Failed to load conversation:", err)
    }
  }, [])

  return {
    messages,
    sendMessage,
    isStreaming,
    error,
    usage,
    stopGeneration,
    clearMessages: () => {
      setMessages([])
      setCurrentConversationId(null)
    },
    loadConversation,
    currentConversationId,
  }
}