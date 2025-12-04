'use client'

import { useState } from 'react'
import { User, Bot, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

/**
 * Clean, simple chat message component.
 * Only shows the conversation - no duplicate task displays.
 * Task progress is shown in the PlanView component below.
 */
export function ChatMessage({ role, content, isStreaming = false }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Don't render empty assistant messages (placeholder during generation)
  if (role === 'assistant' && !content && !isStreaming) {
    return null
  }

  return (
    <div
      className={`group flex gap-4 px-6 py-4 ${
        role === 'user' ? 'flex-row-reverse' : ''
      } ${
        role === 'assistant' ? 'bg-[hsl(var(--bolt-bg-secondary))]' : ''
      }`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0">
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            role === 'user'
              ? 'bg-gradient-to-br from-blue-500 to-cyan-500'
              : 'bg-gradient-to-br from-purple-500 to-pink-500'
          }`}
        >
          {role === 'user' ? (
            <User className="w-5 h-5 text-white" />
          ) : (
            <Bot className="w-5 h-5 text-white" />
          )}
        </div>
      </div>

      {/* Content */}
      <div className={`flex-1 min-w-0 ${role === 'user' ? 'text-right' : ''}`}>
        <div className={`flex items-center gap-2 mb-2 ${role === 'user' ? 'justify-end' : ''}`}>
          <span className="font-semibold text-sm text-[hsl(var(--bolt-text-primary))]">
            {role === 'user' ? 'You' : 'BharatBuild AI'}
          </span>
          {isStreaming && (
            <div className="flex gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse delay-75" />
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse delay-150" />
            </div>
          )}
        </div>

        <div className="prose prose-invert max-w-none">
          <div className="text-[hsl(var(--bolt-text-primary))] text-sm leading-relaxed">
            {content.split('\n').map((line, i) => {
              // Render bold text (wrapped in **)
              if (line.includes('**')) {
                const parts = line.split('**')
                return (
                  <div key={i} className="mb-2">
                    {parts.map((part, j) =>
                      j % 2 === 1 ? (
                        <strong key={j} className="font-semibold text-[hsl(var(--bolt-accent))]">
                          {part}
                        </strong>
                      ) : (
                        <span key={j}>{part}</span>
                      )
                    )}
                  </div>
                )
              }
              // Render code blocks (wrapped in `)
              if (line.includes('`')) {
                const parts = line.split('`')
                return (
                  <div key={i} className="mb-2">
                    {parts.map((part, j) =>
                      j % 2 === 1 ? (
                        <code
                          key={j}
                          className="px-1.5 py-0.5 rounded bg-[hsl(var(--bolt-bg-tertiary))] text-cyan-400 font-mono text-xs"
                        >
                          {part}
                        </code>
                      ) : (
                        <span key={j}>{part}</span>
                      )
                    )}
                  </div>
                )
              }
              // Regular line
              return line ? (
                <div key={i} className="mb-2">
                  {line}
                </div>
              ) : (
                <div key={i} className="mb-2" />
              )
            })}
            {isStreaming && <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-0.5" />}
          </div>
        </div>

        {/* Action Buttons - Only show for messages with content */}
        {role === 'assistant' && !isStreaming && content && (
          <div className="mt-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity justify-start">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="h-7 px-2 text-xs text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 mr-1" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3 mr-1" />
                  Copy
                </>
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
