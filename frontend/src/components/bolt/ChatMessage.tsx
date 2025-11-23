'use client'

import { useState } from 'react'
import { User, Bot, Copy, Check, CheckCircle2, Loader2, FileText, FilePlus, FileEdit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ThinkingStep, FileOperation } from '@/store/chatStore'
import { TaskDetailModal } from './TaskDetailModal'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  thinkingSteps?: ThinkingStep[]
  fileOperations?: FileOperation[]
}

export function ChatMessage({ role, content, isStreaming = false, thinkingSteps = [], fileOperations = [] }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const [selectedTask, setSelectedTask] = useState<FileOperation | null>(null)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleTaskClick = (task: FileOperation) => {
    setSelectedTask(task)
  }

  return (
    <div
      className={`group flex gap-4 px-6 py-4 ${
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
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-semibold text-sm">
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

        {/* Thinking Steps - Bolt.new style */}
        {role === 'assistant' && thinkingSteps.length > 0 && (
          <div className="mb-4 space-y-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg p-3 border border-[hsl(var(--bolt-border))]">
            <div className="text-xs font-semibold text-[hsl(var(--bolt-text-secondary))] mb-2">🤔 Thinking</div>
            {thinkingSteps.map((step, index) => (
              <div key={index} className="flex items-center gap-2">
                {step.status === 'complete' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                ) : step.status === 'active' ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border-2 border-[hsl(var(--bolt-border))] flex-shrink-0" />
                )}
                <span
                  className={`text-sm ${
                    step.status === 'complete'
                      ? 'text-green-500'
                      : step.status === 'active'
                      ? 'text-blue-500 font-medium'
                      : 'text-[hsl(var(--bolt-text-secondary))]'
                  }`}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* File Operations - Tasks */}
        {role === 'assistant' && fileOperations.length > 0 && (
          <div className="mb-4 space-y-2 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg p-3 border border-[hsl(var(--bolt-border))]">
            <div className="text-xs font-semibold text-[hsl(var(--bolt-text-secondary))] mb-2">⚙️ Tasks</div>
            {fileOperations.map((op, index) => (
              <div
                key={index}
                className="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors hover:bg-[hsl(var(--bolt-bg-primary))]"
                onClick={() => handleTaskClick(op)}
                title="Click to view task details"
              >
                {op.status === 'complete' ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                ) : op.status === 'in-progress' ? (
                  <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
                ) : op.status === 'error' ? (
                  <div className="w-4 h-4 rounded-full bg-red-500 flex-shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border-2 border-[hsl(var(--bolt-border))] flex-shrink-0" />
                )}
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {op.type === 'create' ? (
                    <FilePlus className="w-3.5 h-3.5 text-[hsl(var(--bolt-text-secondary))] flex-shrink-0" />
                  ) : op.type === 'modify' ? (
                    <FileEdit className="w-3.5 h-3.5 text-[hsl(var(--bolt-text-secondary))] flex-shrink-0" />
                  ) : (
                    <FileText className="w-3.5 h-3.5 text-[hsl(var(--bolt-text-secondary))] flex-shrink-0" />
                  )}
                  <span
                    className={`text-sm truncate ${
                      op.status === 'complete'
                        ? 'text-green-500'
                        : op.status === 'in-progress'
                        ? 'text-blue-500 font-medium'
                        : op.status === 'error'
                        ? 'text-red-500'
                        : 'text-[hsl(var(--bolt-text-secondary))]'
                    }`}
                  >
                    {op.path}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

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

        {/* Action Buttons */}
        {role === 'assistant' && !isStreaming && (
          <div className="mt-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
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

      {/* Task Detail Modal */}
      <TaskDetailModal
        isOpen={selectedTask !== null}
        task={selectedTask}
        onClose={() => setSelectedTask(null)}
      />
    </div>
  )
}
