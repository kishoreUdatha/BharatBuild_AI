'use client'

/**
 * Unified Run Button
 * ==================
 * Single "Run" button that automatically:
 * 1. Detects project type (Node.js vs Python/Java)
 * 2. Uses WebContainer for Node.js (browser-based, free)
 * 3. Uses Docker for other languages (server-based)
 * 4. Auto-fixes errors using AI
 * 5. Shows preview automatically
 *
 * Everything is automatic - user just clicks Run!
 */

import { useEffect, useCallback } from 'react'
import {
  Play,
  Square,
  RefreshCw,
  Loader2,
  Wrench,
  AlertTriangle,
  RotateCcw
} from 'lucide-react'
import { useUnifiedRunner } from '@/hooks/useUnifiedRunner'

interface UnifiedRunButtonProps {
  onPreviewUrlChange?: (url: string | null) => void
  onOutput?: (line: string) => void
  onOpenTerminal?: () => void
}

export function UnifiedRunButton({
  onPreviewUrlChange,
  onOutput,
  onOpenTerminal
}: UnifiedRunButtonProps) {
  const {
    status,
    previewUrl,
    isRunning,
    isLoading,
    fixAttempts,
    maxAttemptsReached,
    run,
    stop,
    restart,
    clearOutput
  } = useUnifiedRunner({
    onOutput,
    onPreviewReady: (url) => {
      onPreviewUrlChange?.(url)
    },
    autoFix: true
  })

  // Notify parent of preview URL changes
  useEffect(() => {
    onPreviewUrlChange?.(previewUrl)
  }, [previewUrl, onPreviewUrlChange])

  // Get status label - simple, no technical details
  const getStatusLabel = () => {
    switch (status) {
      case 'detecting': return 'Starting...'
      case 'booting': return 'Starting...'
      case 'installing': return 'Installing...'
      case 'starting': return 'Starting...'
      case 'fixing': return `Fixing...`
      default: return 'Run'
    }
  }

  const handleRun = useCallback(async () => {
    clearOutput()
    onOpenTerminal?.()
    await run()
  }, [run, clearOutput, onOpenTerminal])

  const handleStop = useCallback(async () => {
    await stop()
    onPreviewUrlChange?.(null)
  }, [stop, onPreviewUrlChange])

  const handleRestart = useCallback(async () => {
    clearOutput()
    await restart()
  }, [restart, clearOutput])

  const handleRetryFix = useCallback(() => {
    clearOutput()
    run()
  }, [run, clearOutput])

  return (
    <div className="flex items-center gap-2">
      {/* Main Run/Stop Button */}
      {!isRunning && !isLoading ? (
        <button
          onClick={handleRun}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
            bg-green-600 hover:bg-green-700
            text-white text-sm font-medium transition-colors"
          title="Run Project"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run</span>
        </button>
      ) : isLoading ? (
        <button
          disabled
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md
            ${status === 'fixing' ? 'bg-purple-600' : 'bg-yellow-600'}
            text-white text-sm font-medium opacity-90`}
        >
          {status === 'fixing' ? (
            <Wrench className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          )}
          <span>{getStatusLabel()}</span>
        </button>
      ) : (
        <button
          onClick={handleStop}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
            bg-red-600 hover:bg-red-700
            text-white text-sm font-medium transition-colors"
          title="Stop Project"
        >
          <Square className="w-3.5 h-3.5" />
          <span>Stop</span>
        </button>
      )}

      {/* Max Attempts Warning - only show when fix completely failed */}
      {maxAttemptsReached && (
        <>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-red-500/10 text-red-400">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Error</span>
          </div>
          <button
            onClick={handleRetryFix}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
              bg-orange-600 hover:bg-orange-700
              text-white text-sm font-medium transition-colors"
            title="Retry"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry</span>
          </button>
        </>
      )}

      {/* Restart Button */}
      {isRunning && (
        <button
          onClick={handleRestart}
          className="flex items-center justify-center w-8 h-8 rounded-md
            bg-[hsl(var(--bolt-bg-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
            text-[hsl(var(--bolt-text-secondary))] transition-colors"
          title="Restart"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

export default UnifiedRunButton
