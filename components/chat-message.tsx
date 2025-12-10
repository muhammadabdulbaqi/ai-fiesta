import type { ExtendedMessage } from "@/hooks/use-chat-sse"
import { Sparkles, Bot, AlertTriangle, User } from "lucide-react"

interface ChatMessageProps {
  message: ExtendedMessage
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user"

  // 1. Render User Message (Right Aligned)
  if (isUser) {
    return (
      <div className="flex justify-end mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300 px-4">
        <div className="flex gap-3 flex-row-reverse max-w-2xl">
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center flex-shrink-0 mt-1">
                <User className="w-4 h-4" />
            </div>
            <div className="rounded-2xl rounded-br-none px-5 py-3.5 bg-primary text-primary-foreground">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            </div>
        </div>
      </div>
    )
  }

  // 2. Render Single Model Response (Standard Chat)
  if (!message.variations && message.content) {
     return (
      <div className="flex justify-start mb-8 px-4">
         <div className="flex gap-3 max-w-2xl">
            <div className="w-8 h-8 rounded-full bg-muted text-muted-foreground flex items-center justify-center flex-shrink-0 mt-1">
                <Bot className="w-4 h-4" />
            </div>
            <div className="rounded-2xl rounded-bl-none px-5 py-3.5 bg-muted/50 border border-border">
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
            </div>
         </div>
      </div>
     )
  }

  // 3. Render Multi-Model Grid (Side-by-Side)
  if (message.variations) {
    const variations = Object.values(message.variations)
    
    // Explicitly calculate width based on number of active models
    const gridStyle = {
        display: 'grid',
        gridTemplateColumns: `repeat(${variations.length}, minmax(300px, 1fr))`,
        gap: '1rem',
        width: '100%'
    }

    return (
      <div className="mb-8 animate-in fade-in slide-in-from-bottom-2 duration-300 px-4 w-full">
        {/* We use inline style for dynamic column count to strictly enforce SxS */}
        <div style={gridStyle}>
            {variations.map((variant) => (
                <div key={variant.modelId} className="flex flex-col border border-border bg-card rounded-xl overflow-hidden shadow-sm h-full">
                    {/* Header */}
                    <div className="bg-muted/30 px-4 py-3 border-b border-border flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-3.5 h-3.5 text-primary" />
                            <span className="font-bold text-xs uppercase tracking-wider">{variant.modelId}</span>
                        </div>
                        {variant.isStreaming && (
                            <span className="relative flex h-2.5 w-2.5">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-primary"></span>
                            </span>
                        )}
                    </div>

                    {/* Content Body */}
                    <div className="p-4 flex-1 bg-card min-h-[200px]">
                        {variant.error ? (
                             <div className="text-destructive text-sm flex items-center gap-2 p-2 bg-destructive/10 rounded-md">
                                <AlertTriangle className="w-4 h-4" />
                                <span>{variant.error}</span>
                             </div>
                        ) : (
                            <div className="text-sm leading-relaxed whitespace-pre-wrap font-normal text-foreground/90">
                                {variant.content}
                                {variant.isStreaming && <span className="inline-block w-1.5 h-4 bg-primary/50 ml-1 animate-pulse align-middle"/>}
                            </div>
                        )}
                    </div>

                    {/* Footer stats */}
                    {!variant.isStreaming && !variant.error && (
                         <div className="px-4 py-2 bg-muted/20 border-t border-border flex justify-between text-[10px] text-muted-foreground uppercase tracking-wide">
                            <span>Tokens: {variant.tokens_used || 0}</span>
                            <span>Credits: {variant.credits_used || 0}</span>
                         </div>
                    )}
                </div>
            ))}
        </div>
      </div>
    )
  }

  return null
}