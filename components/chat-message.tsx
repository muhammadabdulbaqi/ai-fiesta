import type { Message } from "@/lib/api"
import { Sparkles } from "lucide-react"

interface ChatMessageProps {
  message: Message
  isStreaming?: boolean
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user"

  return (
    <div
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"} mb-6 animate-in fade-in slide-in-from-bottom-2 duration-300`}
    >
      <div className={`flex gap-3 max-w-2xl ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0 mt-1">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
        )}

        <div
          className={`rounded-xl px-4 py-3 ${
            isUser
              ? "bg-primary text-primary-foreground rounded-br-none"
              : "bg-muted text-muted-foreground rounded-bl-none"
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message.content}
            {isStreaming && <span className="animate-pulse">▌</span>}
          </p>

          {!isUser && message.model && (
            <div className="text-xs opacity-60 mt-2 pt-2 border-t border-current/20">
              <p>{message.model}</p>
              {message.tokens_used && <p>Tokens: {message.tokens_used}</p>}
              {message.credits_used && <p>Credits: {message.credits_used}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

