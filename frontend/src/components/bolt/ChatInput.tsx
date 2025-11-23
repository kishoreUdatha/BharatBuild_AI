'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatInputProps {
  onSend: (message: string) => void
  isLoading?: boolean
  placeholder?: string
}

export function ChatInput({ onSend, isLoading = false, placeholder }: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !isLoading) {
      onSend(message.trim())
      setMessage('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [message])

  return (
    <div className="border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-primary))] p-4">
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
        <div className="relative flex items-end gap-3 bg-[hsl(var(--bolt-bg-tertiary))] rounded-xl border border-[hsl(var(--bolt-border))] p-3 focus-within:border-[hsl(var(--bolt-accent))] transition-colors">
          {/* Sparkles Icon */}
          <div className="flex-shrink-0 self-center mb-1">
            <Sparkles className="w-5 h-5 text-[hsl(var(--bolt-accent))]" />
          </div>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder || "Describe your project... (e.g., 'Build a task management app')"}
            disabled={isLoading}
            rows={1}
            className="flex-1 bg-transparent text-[hsl(var(--bolt-text-primary))] placeholder:text-[hsl(var(--bolt-text-secondary))] resize-none focus:outline-none max-h-[200px] scrollbar-thin"
            style={{ minHeight: '24px' }}
          />

          {/* Send Button */}
          <Button
            type="submit"
            disabled={!message.trim() || isLoading}
            size="sm"
            className="flex-shrink-0 bg-[hsl(var(--bolt-accent))] hover:bg-[hsl(var(--bolt-accent-hover))] text-white rounded-lg px-4 h-9 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>

        {/* Helper Text */}
        <div className="mt-2 flex items-center justify-between text-xs text-[hsl(var(--bolt-text-secondary))]">
          <span>Press Enter to send, Shift+Enter for new line</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
            Ready
          </span>
        </div>
      </form>
    </div>
  )
}
