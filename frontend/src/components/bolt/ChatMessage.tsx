'use client'

import { useState, useMemo } from 'react'
import { Copy, Check, Sparkles, RotateCcw, ThumbsUp, ThumbsDown } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  onRegenerate?: () => void
}

/**
 * Bolt.new-style chat message component
 * Clean, minimal design without avatars
 * Supports markdown rendering and code highlighting
 */
export function ChatMessage({
  role,
  content,
  isStreaming = false,
  onRegenerate
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Don't render empty messages
  if (!content && !isStreaming) {
    return null
  }

  return (
    <div className={`group px-4 py-6 ${
      role === 'assistant'
        ? 'bg-transparent'
        : 'bg-transparent'
    }`}>
      <div className="max-w-3xl mx-auto">
        {/* Role Label */}
        <div className="flex items-center gap-2 mb-3">
          {role === 'assistant' ? (
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
                <Sparkles className="w-3.5 h-3.5 text-white" />
              </div>
              <span className="text-sm font-medium text-white/90">BharatBuild AI</span>
              {isStreaming && (
                <span className="flex items-center gap-1 text-xs text-violet-400">
                  <span className="w-1 h-1 rounded-full bg-violet-400 animate-pulse" />
                  <span className="w-1 h-1 rounded-full bg-violet-400 animate-pulse delay-75" />
                  <span className="w-1 h-1 rounded-full bg-violet-400 animate-pulse delay-150" />
                </span>
              )}
            </div>
          ) : (
            <span className="text-sm font-medium text-white/70">You</span>
          )}
        </div>

        {/* Message Content */}
        <div className={`prose prose-invert max-w-none ${
          role === 'user'
            ? 'text-white/90'
            : 'text-white/80'
        }`}>
          {role === 'assistant' ? (
            <MarkdownContent content={content} isStreaming={isStreaming} />
          ) : (
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap m-0">
              {content}
            </p>
          )}
        </div>

        {/* Action Buttons - Only for assistant messages */}
        {role === 'assistant' && !isStreaming && content && (
          <div className="flex items-center gap-1 mt-4 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors"
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-green-400">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </>
              )}
            </button>

            {onRegenerate && (
              <button
                onClick={onRegenerate}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Regenerate</span>
              </button>
            )}

            <div className="flex items-center gap-0.5 ml-2">
              <button
                onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
                className={`p-1.5 rounded-lg transition-colors ${
                  feedback === 'up'
                    ? 'text-green-400 bg-green-400/10'
                    : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                }`}
              >
                <ThumbsUp className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
                className={`p-1.5 rounded-lg transition-colors ${
                  feedback === 'down'
                    ? 'text-red-400 bg-red-400/10'
                    : 'text-white/50 hover:text-white/80 hover:bg-white/5'
                }`}
              >
                <ThumbsDown className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Markdown content renderer with syntax highlighting
 */
function MarkdownContent({ content, isStreaming }: { content: string; isStreaming: boolean }) {
  return (
    <div className="text-[15px] leading-relaxed">
      <ReactMarkdown
        components={{
          // Paragraphs
          p: ({ children }) => (
            <p className="mb-4 last:mb-0">{children}</p>
          ),

          // Headings
          h1: ({ children }) => (
            <h1 className="text-xl font-bold mb-4 mt-6 first:mt-0 text-white">{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold mb-3 mt-5 first:mt-0 text-white">{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-bold mb-2 mt-4 first:mt-0 text-white">{children}</h3>
          ),

          // Lists
          ul: ({ children }) => (
            <ul className="list-disc list-inside mb-4 space-y-1">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-inside mb-4 space-y-1">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="text-white/80">{children}</li>
          ),

          // Inline code
          code: ({ className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '')
            const isInline = !match

            if (isInline) {
              return (
                <code className="px-1.5 py-0.5 rounded bg-white/10 text-violet-300 font-mono text-sm">
                  {children}
                </code>
              )
            }

            // Code block
            return (
              <SyntaxHighlighter
                style={oneDark}
                language={match[1]}
                PreTag="div"
                className="rounded-lg !bg-[#1e1e2e] !mt-2 !mb-4 text-sm"
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            )
          },

          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-violet-500 pl-4 my-4 text-white/60 italic">
              {children}
            </blockquote>
          ),

          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet-400 hover:text-violet-300 underline underline-offset-2"
            >
              {children}
            </a>
          ),

          // Strong/Bold
          strong: ({ children }) => (
            <strong className="font-semibold text-white">{children}</strong>
          ),

          // Horizontal rule
          hr: () => (
            <hr className="my-6 border-white/10" />
          ),
        }}
      >
        {content}
      </ReactMarkdown>

      {/* Streaming cursor */}
      {isStreaming && (
        <span className="inline-block w-2 h-5 bg-violet-500 animate-pulse ml-0.5 align-middle" />
      )}
    </div>
  )
}

export default ChatMessage
