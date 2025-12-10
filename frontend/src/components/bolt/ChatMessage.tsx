'use client'

import { useState } from 'react'
import { Copy, Check, Sparkles, RotateCcw, ThumbsUp, ThumbsDown, User } from 'lucide-react'
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
 * Modern chat message component
 * - User messages: Right aligned with bubble
 * - AI messages: Left aligned with rich formatting
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

  // User Message - Right aligned bubble
  if (role === 'user') {
    return (
      <div className="px-4 py-3">
        <div className="max-w-3xl mx-auto flex justify-end">
          <div className="flex items-start gap-3 max-w-[85%]">
            {/* Message Bubble */}
            <div className="bg-gradient-to-br from-violet-600 to-purple-700 rounded-2xl rounded-tr-sm px-4 py-3 shadow-lg shadow-violet-500/20">
              <p className="text-[15px] leading-relaxed text-white whitespace-pre-wrap">
                {content}
              </p>
            </div>
            {/* User Avatar */}
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
              <User className="w-4 h-4 text-white/70" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Assistant Message - Left aligned with rich formatting
  return (
    <div className="group px-4 py-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          {/* AI Avatar */}
          <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shadow-lg shadow-violet-500/25">
            <Sparkles className="w-4.5 h-4.5 text-white" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white">BharatBuild AI</span>
            {isStreaming && (
              <span className="flex items-center gap-1 text-xs text-violet-400">
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse delay-75" />
                <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse delay-150" />
              </span>
            )}
          </div>
        </div>

        {/* Message Content */}
        <div className="pl-12">
          <div className="bg-[#12121a] rounded-2xl rounded-tl-sm px-5 py-4 border border-white/5">
            <MarkdownContent content={content} isStreaming={isStreaming} />
          </div>

          {/* Action Buttons */}
          {!isStreaming && content && (
            <div className="flex items-center gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors"
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
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors"
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
    </div>
  )
}

/**
 * Enhanced Markdown renderer with beautiful formatting
 */
function MarkdownContent({ content, isStreaming }: { content: string; isStreaming: boolean }) {
  return (
    <div className="text-[15px] leading-relaxed text-white/85">
      <ReactMarkdown
        components={{
          // Paragraphs - Good spacing
          p: ({ children }) => (
            <p className="mb-4 last:mb-0 text-white/85">{children}</p>
          ),

          // Headings - Bold and distinct
          h1: ({ children }) => (
            <h1 className="text-xl font-bold mb-4 mt-6 first:mt-0 text-white flex items-center gap-2">
              <span className="w-1 h-6 bg-gradient-to-b from-violet-500 to-purple-500 rounded-full" />
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-lg font-bold mb-3 mt-5 first:mt-0 text-white flex items-center gap-2">
              <span className="w-1 h-5 bg-gradient-to-b from-violet-500 to-purple-500 rounded-full" />
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-base font-semibold mb-2 mt-4 first:mt-0 text-white/95">{children}</h3>
          ),

          // Lists - Clean bullet points
          ul: ({ children }) => (
            <ul className="mb-4 space-y-2 last:mb-0">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-4 space-y-2 list-decimal list-inside last:mb-0">{children}</ol>
          ),
          li: ({ children }) => (
            <li className="flex items-start gap-2 text-white/80">
              <span className="flex-shrink-0 w-1.5 h-1.5 rounded-full bg-violet-400 mt-2" />
              <span className="flex-1">{children}</span>
            </li>
          ),

          // Inline code
          code: ({ className, children, ...props }: any) => {
            const match = /language-(\w+)/.exec(className || '')
            const isInline = !match

            if (isInline) {
              return (
                <code className="px-1.5 py-0.5 rounded-md bg-violet-500/20 text-violet-300 font-mono text-sm border border-violet-500/20">
                  {children}
                </code>
              )
            }

            // Code block with syntax highlighting
            return (
              <div className="relative group/code my-4">
                <div className="absolute top-3 right-3 opacity-0 group-hover/code:opacity-100 transition-opacity">
                  <button
                    onClick={() => navigator.clipboard.writeText(String(children))}
                    className="p-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/60 hover:text-white transition-colors"
                  >
                    <Copy className="w-3.5 h-3.5" />
                  </button>
                </div>
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                  className="rounded-xl !bg-[#0d0d12] !mt-0 !mb-0 text-sm border border-white/5"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              </div>
            )
          },

          // Blockquotes - Styled nicely
          blockquote: ({ children }) => (
            <blockquote className="border-l-3 border-violet-500 pl-4 my-4 py-2 bg-violet-500/5 rounded-r-lg text-white/70 italic">
              {children}
            </blockquote>
          ),

          // Links
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="text-violet-400 hover:text-violet-300 underline underline-offset-2 decoration-violet-400/50 hover:decoration-violet-300"
            >
              {children}
            </a>
          ),

          // Strong/Bold
          strong: ({ children }) => (
            <strong className="font-semibold text-white">{children}</strong>
          ),

          // Emphasis/Italic
          em: ({ children }) => (
            <em className="italic text-white/70">{children}</em>
          ),

          // Horizontal rule
          hr: () => (
            <hr className="my-6 border-white/10" />
          ),

          // Tables
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="w-full border-collapse border border-white/10 rounded-lg overflow-hidden">
                {children}
              </table>
            </div>
          ),
          th: ({ children }) => (
            <th className="px-4 py-2 bg-white/5 border border-white/10 text-left font-semibold text-white">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2 border border-white/10 text-white/80">
              {children}
            </td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>

      {/* Streaming cursor */}
      {isStreaming && (
        <span className="inline-block w-2 h-5 bg-violet-500 animate-pulse ml-0.5 align-middle rounded-sm" />
      )}
    </div>
  )
}

export default ChatMessage
