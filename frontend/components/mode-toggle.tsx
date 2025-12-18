"use client"

import { Button } from "@/components/ui/button"
import { LayoutGrid, Rocket } from "lucide-react"
import { cn } from "@/lib/utils"

type Mode = "multi-chat" | "super-fiesta"

interface ModeToggleProps {
  mode: Mode
  onModeChange: (mode: Mode) => void
}

export function ModeToggle({ mode, onModeChange }: ModeToggleProps) {
  return (
    <div className="flex items-center gap-3">
      <Button
        variant={mode === "multi-chat" ? "default" : "outline"}
        size="lg"
        onClick={() => onModeChange("multi-chat")}
        className={cn(
          "flex items-center gap-2 rounded-full px-6 py-6 h-auto",
          mode === "multi-chat" && "shadow-md"
        )}
      >
        <LayoutGrid className="w-5 h-5" />
        <span className="font-medium">Multi-Chat</span>
      </Button>
      <Button
        variant={mode === "super-fiesta" ? "default" : "outline"}
        size="lg"
        onClick={() => onModeChange("super-fiesta")}
        className={cn(
          "flex items-center gap-2 rounded-full px-6 py-6 h-auto",
          mode === "super-fiesta" && "shadow-md bg-primary text-primary-foreground"
        )}
      >
        <Rocket className="w-5 h-5" />
        <span className="font-medium">Super Fiesta</span>
      </Button>
    </div>
  )
}

