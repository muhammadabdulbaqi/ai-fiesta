"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { Plus, Users, Receipt, Trash2, Moon, Sun, LogOut } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { getConversations, deleteConversation, getCurrentUser, logout, getAdminToken, type ConversationSummary, type User } from "@/lib/api"
import { cn } from "@/lib/utils"

interface SidebarProps {
  onNewChat: () => void
  onConversationSelect?: (conversationId: string) => void
  refreshTrigger?: number // When this changes, refresh the conversation list
}

export function Sidebar({ onNewChat, onConversationSelect, refreshTrigger }: SidebarProps) {
  const router = useRouter()
  const { theme, setTheme } = useTheme()
  const [history, setHistory] = useState<ConversationSummary[]>([])
  const [user, setUser] = useState<User | null>(null)
  const [selectedConv, setSelectedConv] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      const [conversations, currentUser] = await Promise.all([
        getConversations(), // Uses JWT from headers
        getCurrentUser().catch(() => null)
      ])
      setHistory(conversations)
      setUser(currentUser)
    } catch (err: any) {
      console.error("Sidebar fetch error:", err)
      // Only redirect on authentication errors, not on network errors
      const errorMessage = err?.message || ""
      if (errorMessage.includes("401") || errorMessage.includes("403") || errorMessage.includes("Unauthorized")) {
        // Don't redirect if we're already on login page
        if (window.location.pathname !== "/login") {
          router.push("/login")
        }
      }
    }
  }

  useEffect(() => {
    fetchData()
  }, [router, refreshTrigger])

  const handleDelete = async (e: React.MouseEvent, conversationId: string) => {
    e.stopPropagation()
    if (!confirm("Delete this conversation?")) return
    
    try {
      await deleteConversation(conversationId)
      setHistory(history.filter(c => c.id !== conversationId))
    } catch (err) {
      console.error("Failed to delete conversation:", err)
    }
  }

  const handleLogout = async () => {
    try {
      logout()
      // Clear any additional state if needed
      router.push("/login")
    } catch (err) {
      console.error("Logout error:", err)
      // Force redirect even if logout fails
      router.push("/login")
    }
  }

  const getProviderIconPath = (modelId: string): string | null => {
    if (!modelId) return null
    const lowerModel = modelId.toLowerCase()
    if (lowerModel.includes("gpt") || lowerModel.includes("openai") || lowerModel.includes("o1")) {
      return "/icons/openai.png"
    } else if (lowerModel.includes("claude") || lowerModel.includes("anthropic")) {
      return "/icons/anthropic-1.svg"
    } else if (lowerModel.includes("gemini")) {
      return "/icons/Google_Gemini_icon_2025.svg.png"
    } else if (lowerModel.includes("grok")) {
      return "/icons/Grok-icon.svg.png"
    } else if (lowerModel.includes("perplexity") || lowerModel.includes("sonar")) {
      return "/icons/perplexity-e6a4e1t06hd6dhczot580o.webp"
    }
    return null
  }

  return (
    <div className="w-64 h-screen bg-sidebar border-r border-sidebar-border flex flex-col p-4 overflow-hidden">
      {/* Logo */}
      <div className="flex items-center gap-2 mb-8">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
          <span className="text-white font-bold text-lg">🎉</span>
        </div>
        <span className="font-bold text-lg">AI Fiesta</span>
      </div>

      {/* New Chat */}
      <Button onClick={onNewChat} variant="outline" className="w-full justify-start gap-2 mb-8 bg-transparent">
        <Plus className="w-4 h-4" />
        New chat
      </Button>

      {/* Navigation */}
      <nav className="space-y-1 mb-6">
        <Link href="/pricing" className="block">
          <Button variant="ghost" className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent">
            <Receipt className="w-4 h-4" />
            Pricing & Models
          </Button>
        </Link>
        {/* Show Admin Dashboard link only if admin token exists */}
        {getAdminToken() && (
          <Link href="/admin" className="block">
            <Button variant="ghost" className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent">
              <Users className="w-4 h-4" />
              Admin Dashboard
            </Button>
          </Link>
        )}
      </nav>

      {/* History Section */}
      <div className="flex-1 overflow-y-auto no-scrollbar">
        <p className="text-xs uppercase tracking-wide text-sidebar-foreground/60 font-semibold mb-3 px-2">
          History
        </p>
        <div className="space-y-1">
          {history.length === 0 ? (
            <p className="text-xs text-muted-foreground px-2">No history yet.</p>
          ) : (
            history.map((conv) => (
              <Link
                key={conv.id}
                href={`/?id=${conv.id}`}
                onClick={() => {
                  setSelectedConv(conv.id)
                  onConversationSelect?.(conv.id)
                }}
                className={cn(
                  "group flex items-center justify-between p-2 rounded-lg hover:bg-sidebar-accent transition-colors cursor-pointer block",
                  selectedConv === conv.id && "bg-sidebar-accent"
                )}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium truncate" title={conv.title || "Untitled"}>
                      {conv.title || "New Chat"}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0"
                      onClick={(e) => handleDelete(e, conv.id)}
                    >
                      <Trash2 className="w-3 h-3 text-destructive" />
                    </Button>
                  </div>
                  <div className="text-[10px] text-muted-foreground/70 mt-1">
                    {new Date(conv.created_at).toLocaleDateString()} • ${conv.total_cost_usd?.toFixed(4)}
                  </div>
                  {conv.models_used && conv.models_used.length > 0 && (
                    <div className="flex items-center gap-1 mt-1.5 flex-wrap">
                      {conv.models_used.slice(0, 3).map((modelId) => {
                        const iconPath = getProviderIconPath(modelId)
                        return iconPath ? (
                          <img
                            key={modelId}
                            src={iconPath}
                            alt={modelId}
                            className="w-3 h-3 object-contain opacity-70"
                            title={modelId}
                          />
                        ) : null
                      })}
                      {conv.models_used.length > 3 && (
                        <span className="text-[9px] text-muted-foreground/60">+{conv.models_used.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
      
      {/* Footer */}
      <div className="border-t border-sidebar-border pt-4 mt-2 space-y-2">
        <div className="flex items-center justify-between px-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="w-full justify-start gap-2"
          >
            {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </Button>
        </div>
        {user && (
          <div className="px-2">
            <div className="text-xs text-muted-foreground mb-1">{user.username}</div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="w-full justify-start gap-2 text-destructive hover:text-destructive"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
          </div>
        )}
        <div className="text-xs text-center text-muted-foreground">
          v0.1.0-beta
        </div>
      </div>
    </div>
  )
}