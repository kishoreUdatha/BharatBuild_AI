'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import {
  Send,
  Sparkles,
  Square,
  Paperclip,
  Image as ImageIcon,
  Mic,
  ArrowUp
} from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  onStop?: () => void
  isLoading?: boolean
  placeholder?: string
  disabled?: boolean
}

/**
 * Bolt.new-style chat input component
 * Modern, floating design with smooth animations
 */
export function ChatInput({
  onSend,
  onStop,
  isLoading = false,
  placeholder,
  disabled = false
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const [isFocused, setIsFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = () => {
    if (message.trim() && !isLoading && !disabled) {
      onSend(message.trim())
      setMessage('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [message])

  // Focus textarea on mount
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  const canSubmit = message.trim().length > 0 && !isLoading && !disabled

  return (
    <div className="p-4 bg-gradient-to-t from-[hsl(var(--bolt-bg-primary))] via-[hsl(var(--bolt-bg-primary))] to-transparent">
      <div className="max-w-3xl mx-auto">
        {/* Main Input Container */}
        <div
          className={`relative flex items-end gap-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-2xl border transition-all duration-200 ${
            isFocused
              ? 'border-violet-500/50 shadow-lg shadow-violet-500/10'
              : 'border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-text-secondary))]/30'
          }`}
        >
          {/* Left Icon */}
          <div className="flex-shrink-0 p-3 pb-3.5">
            <Sparkles className={`w-5 h-5 transition-colors ${
              isFocused ? 'text-violet-400' : 'text-[hsl(var(--bolt-text-secondary))]'
            }`} />
          </div>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder || "Describe what you want to build..."}
            disabled={isLoading || disabled}
            rows={1}
            className="flex-1 bg-transparent text-[hsl(var(--bolt-text-primary))] text-[15px] placeholder:text-[hsl(var(--bolt-text-secondary))] resize-none focus:outline-none py-3.5 pr-2 max-h-[200px] scrollbar-thin disabled:opacity-50"
            style={{ minHeight: '24px' }}
          />

          {/* Right Actions */}
          <div className="flex items-center gap-1 p-2 flex-shrink-0">
            {/* Attachment Button (optional) */}
            {/*
            <button
              type="button"
              className="p-2 rounded-xl text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              title="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            */}

            {/* Send/Stop Button */}
            {isLoading ? (
              <button
                type="button"
                onClick={onStop}
                className="p-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-colors"
                title="Stop generating"
              >
                <Square className="w-4 h-4 fill-current" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!canSubmit}
                className={`p-2.5 rounded-xl transition-all duration-200 ${
                  canSubmit
                    ? 'bg-violet-500 hover:bg-violet-600 text-white shadow-lg shadow-violet-500/25'
                    : 'bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-secondary))]/50 cursor-not-allowed'
                }`}
                title="Send message"
              >
                <ArrowUp className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Helper Text */}
        <div className="flex items-center justify-between mt-2 px-1">
          <p className="text-xs text-[hsl(var(--bolt-text-secondary))]">
            {isLoading ? (
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-500 animate-pulse" />
                Generating... Press stop to cancel
              </span>
            ) : (
              <span>
                Press <kbd className="px-1.5 py-0.5 rounded bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] font-mono text-[10px]">Enter</kbd> to send, <kbd className="px-1.5 py-0.5 rounded bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] font-mono text-[10px]">Shift+Enter</kbd> for new line
              </span>
            )}
          </p>

          {/* Character count (optional) */}
          {message.length > 100 && (
            <span className={`text-xs ${
              message.length > 4000 ? 'text-red-400' : 'text-[hsl(var(--bolt-text-secondary))]'
            }`}>
              {message.length} / 4000
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChatInput
