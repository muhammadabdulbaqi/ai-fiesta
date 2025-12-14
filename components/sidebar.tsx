"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Plus, Users, LayoutGrid, Receipt } from "lucide-react"
import { Button } from "@/components/ui/button"
import { getConversations, type ConversationSummary } from "@/lib/api"
import { cn } from "@/lib/utils"

interface SidebarProps {
  onNewChat: () => void
}

const DEMO_USER_ID = process.env.NEXT_PUBLIC_DEFAULT_USER_ID || "demo-user-1"

export function Sidebar({ onNewChat }: SidebarProps) {
  const [history, setHistory] = useState<ConversationSummary[]>([])

  useEffect(() => {
    // Poll for history updates occasionally or trigger via context in real app
    const fetchHistory = async () => {
      try {
        const data = await getConversations(DEMO_USER_ID)
        setHistory(data)
      } catch (err) {
        console.error(err)
      }
    }
    fetchHistory()
  }, [])

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
        <Link href="/admin" className="block">
          <Button variant="ghost" className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent">
            <Users className="w-4 h-4" />
            Admin Dashboard
          </Button>
        </Link>
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
              <div 
                key={conv.id}
                className="group flex flex-col p-2 rounded-lg hover:bg-sidebar-accent transition-colors cursor-pointer"
              >
                <div className="flex justify-between items-center">
                    <span className="text-sm font-medium truncate w-32" title={conv.title || "Untitled"}>
                        {conv.title || "New Chat"}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                        ${conv.total_cost_usd?.toFixed(4)}
                    </span>
                </div>
                <div className="text-[10px] text-muted-foreground/70">
                   {new Date(conv.created_at).toLocaleDateString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Footer */}
      <div className="border-t border-sidebar-border pt-4 mt-2">
         {/* Could put user avatar here */}
         <div className="text-xs text-center text-muted-foreground">
            v0.1.0-beta
         </div>
      </div>
    </div>
  )
}