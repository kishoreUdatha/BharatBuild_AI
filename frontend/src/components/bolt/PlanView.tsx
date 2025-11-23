'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, Loader2, Circle, FileText, FileCode, Folder } from 'lucide-react'
import { useChatStore, Message } from '@/store/chatStore'

interface PlanViewProps {
  messageId?: string  // Optional: show plan for specific message, or latest if not provided
}

export function PlanView({ messageId }: PlanViewProps) {
  const messages = useChatStore((state) => state.messages)

  // Find the message to display plan for
  const targetMessage = messageId
    ? messages.find(m => m.id === messageId)
    : messages.filter(m => m.type === 'assistant').slice(-1)[0]

  if (!targetMessage || targetMessage.type !== 'assistant') {
    return null
  }

  const { thinkingSteps = [], fileOperations = [] } = targetMessage

  return (
    <div className="space-y-6 p-4">
      {/* Thinking Steps Section */}
      {thinkingSteps.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[hsl(var(--bolt-text-primary))] flex items-center gap-2">
            <Loader2 className="w-4 h-4 animate-spin text-blue-500" />
            AI Thinking Process
          </h3>

          <AnimatePresence mode="popLayout">
            {thinkingSteps.map((step, idx) => (
              <motion.div
                key={`step-${idx}-${step.label}`}
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{
                  duration: 0.3,
                  delay: idx * 0.05,
                  ease: [0.4, 0, 0.2, 1]
                }}
                className={`p-3 rounded-lg border ${
                  step.status === 'complete'
                    ? 'border-green-500/30 bg-green-500/5'
                    : step.status === 'active'
                    ? 'border-blue-500/30 bg-blue-500/5'
                    : 'border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]'
                }`}
              >
                <div className="flex items-center gap-3">
                  {/* Status Icon */}
                  <motion.div
                    initial={{ scale: 0, rotate: -180 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ delay: idx * 0.05 + 0.1, duration: 0.4 }}
                  >
                    {step.status === 'complete' ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                    ) : step.status === 'active' ? (
                      <Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
                    ) : (
                      <Circle className="w-5 h-5 text-[hsl(var(--bolt-text-tertiary))] flex-shrink-0" />
                    )}
                  </motion.div>

                  {/* Step Label */}
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 + 0.15 }}
                    className={`text-sm font-medium ${
                      step.status === 'complete'
                        ? 'text-green-500'
                        : step.status === 'active'
                        ? 'text-blue-500'
                        : 'text-[hsl(var(--bolt-text-secondary))]'
                    }`}
                  >
                    {step.label}
                  </motion.span>

                  {/* Progress Bar for Active Step */}
                  {step.status === 'active' && (
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                      transition={{ duration: 2, ease: 'linear' }}
                      className="ml-auto h-1 bg-blue-500/20 rounded-full overflow-hidden flex-1 max-w-[100px]"
                    >
                      <motion.div
                        initial={{ x: '-100%' }}
                        animate={{ x: '100%' }}
                        transition={{
                          duration: 1.5,
                          repeat: Infinity,
                          ease: 'linear'
                        }}
                        className="h-full w-1/2 bg-blue-500"
                      />
                    </motion.div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* File Operations Section */}
      {fileOperations.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-[hsl(var(--bolt-text-primary))] flex items-center gap-2">
            <FileCode className="w-4 h-4 text-purple-500" />
            File Operations
          </h3>

          <AnimatePresence mode="popLayout">
            {fileOperations.map((op, idx) => (
              <motion.div
                key={`file-${idx}-${op.path}`}
                initial={{ opacity: 0, x: -20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 20, scale: 0.95 }}
                transition={{
                  duration: 0.3,
                  delay: idx * 0.03,
                  ease: [0.4, 0, 0.2, 1]
                }}
                className={`p-3 rounded-lg border ${
                  op.status === 'complete'
                    ? 'border-green-500/30 bg-green-500/5'
                    : op.status === 'in-progress'
                    ? 'border-blue-500/30 bg-blue-500/5'
                    : op.status === 'error'
                    ? 'border-red-500/30 bg-red-500/5'
                    : 'border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]'
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* File Type Icon */}
                  <motion.div
                    initial={{ scale: 0, rotate: -90 }}
                    animate={{ scale: 1, rotate: 0 }}
                    transition={{ delay: idx * 0.03 + 0.1, duration: 0.3 }}
                  >
                    {op.path.includes('/') ? (
                      <Folder className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))] flex-shrink-0 mt-0.5" />
                    ) : (
                      <FileText className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))] flex-shrink-0 mt-0.5" />
                    )}
                  </motion.div>

                  {/* File Info */}
                  <div className="flex-1 min-w-0">
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: idx * 0.03 + 0.15 }}
                      className="flex items-center gap-2"
                    >
                      <span className="text-sm font-mono text-[hsl(var(--bolt-text-primary))] truncate">
                        {op.path}
                      </span>

                      {/* Status Badge */}
                      <motion.span
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: idx * 0.03 + 0.2 }}
                        className={`text-xs px-2 py-0.5 rounded-full font-medium whitespace-nowrap ${
                          op.status === 'complete'
                            ? 'bg-green-500/20 text-green-500'
                            : op.status === 'in-progress'
                            ? 'bg-blue-500/20 text-blue-500'
                            : op.status === 'error'
                            ? 'bg-red-500/20 text-red-500'
                            : 'bg-gray-500/20 text-gray-500'
                        }`}
                      >
                        {op.status === 'complete' ? '✓' :
                         op.status === 'in-progress' ? '⟳' :
                         op.status === 'error' ? '✗' : '○'}
                      </motion.span>
                    </motion.div>

                    {/* Description */}
                    {op.description && (
                      <motion.p
                        initial={{ opacity: 0, y: -5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.03 + 0.25 }}
                        className="text-xs text-[hsl(var(--bolt-text-secondary))] mt-1"
                      >
                        {op.description}
                      </motion.p>
                    )}
                  </div>

                  {/* Status Icon */}
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: idx * 0.03 + 0.2 }}
                  >
                    {op.status === 'complete' ? (
                      <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                    ) : op.status === 'in-progress' ? (
                      <Loader2 className="w-4 h-4 text-blue-500 animate-spin flex-shrink-0" />
                    ) : op.status === 'error' ? (
                      <Circle className="w-4 h-4 text-red-500 flex-shrink-0" />
                    ) : (
                      <Circle className="w-4 h-4 text-[hsl(var(--bolt-text-tertiary))] flex-shrink-0" />
                    )}
                  </motion.div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Empty State */}
      {thinkingSteps.length === 0 && fileOperations.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-8 text-[hsl(var(--bolt-text-secondary))]"
        >
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No plan or tasks yet</p>
          <p className="text-xs mt-1">Start a conversation to see AI thinking steps</p>
        </motion.div>
      )}
    </div>
  )
}
