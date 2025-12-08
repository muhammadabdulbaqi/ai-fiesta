"use client"

import Link from "next/link"
import { Plus, MessageCircle, Users, Gamepad2, Settings } from "lucide-react"
import { Button } from "@/components/ui/button"

interface SidebarProps {
  onNewChat: () => void
}

export function Sidebar({ onNewChat }: SidebarProps) {
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
      <nav className="space-y-2 flex-1">
        <Link href="/admin" className="block">
          <Button
            variant="ghost"
            className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent"
          >
            <Users className="w-4 h-4" />
            Admin
          </Button>
        </Link>

        <button className="w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors flex items-center gap-2 text-sidebar-foreground">
          <MessageCircle className="w-4 h-4" />
          <span className="text-sm">Avatars</span>
        </button>

        <button className="w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors flex items-center gap-2 text-sidebar-foreground">
          <Gamepad2 className="w-4 h-4" />
          <span className="text-sm">Projects</span>
        </button>

        <button className="w-full text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors flex items-center gap-2 text-sidebar-foreground">
          <Gamepad2 className="w-4 h-4" />
          <span className="text-sm">Games</span>
        </button>
      </nav>

      {/* History Section */}
      <div className="border-t border-sidebar-border pt-4 mb-4">
        <p className="text-xs uppercase tracking-wide text-sidebar-foreground/60 font-semibold mb-3">Yesterday</p>
        <button className="w-full text-left p-2 rounded hover:bg-sidebar-accent transition-colors text-sm text-sidebar-foreground">
          what is vercel
        </button>
      </div>

      {/* Footer */}
      <div className="border-t border-sidebar-border pt-4 space-y-3">
        <div className="bg-sidebar-accent rounded-lg p-3">
          <p className="font-semibold text-sm mb-2">Free Plan</p>
          <p className="text-xs text-sidebar-foreground/70 mb-2">2 / 3 messages used</p>
          <div className="w-full h-2 bg-sidebar-border rounded-full overflow-hidden">
            <div className="h-full w-2/3 bg-primary" />
          </div>
        </div>
        <Button variant="ghost" className="w-full justify-start gap-2 text-sidebar-foreground hover:bg-sidebar-accent">
          <Settings className="w-4 h-4" />
          Settings
        </Button>
      </div>
    </div>
  )
}

