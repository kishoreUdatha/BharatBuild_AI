'use client'

/**
 * ReconnectionBanner - Shows connection status and resume options
 *
 * Displays:
 * - Offline warning banner
 * - Reconnecting status with progress
 * - Resume prompt when connection restored
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useReconnection, ResumeInfo } from '@/hooks/useReconnection'
import { Wifi, WifiOff, RefreshCw, Play, X, AlertCircle } from 'lucide-react'

interface ReconnectionBannerProps {
  projectId?: string
  onResume?: (stream: ReadableStream) => void
  onDismiss?: () => void
}

export function ReconnectionBanner({
  projectId,
  onResume,
  onDismiss
}: ReconnectionBannerProps) {
  const [showResumePrompt, setShowResumePrompt] = useState(false)
  const [isResuming, setIsResuming] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  const {
    isOnline,
    isReconnecting,
    reconnectAttempt,
    canResume,
    resumeInfo,
    resumeProject,
    attemptReconnect,
    cancelCheckpoint
  } = useReconnection({
    projectId,
    onReconnect: () => {
      console.log('Reconnected!')
    },
    onDisconnect: () => {
      console.log('Disconnected!')
      setDismissed(false)
    },
    onResumeAvailable: (info) => {
      console.log('Resume available:', info)
      setShowResumePrompt(true)
    }
  })

  // Handle resume click
  const handleResume = async () => {
    if (!projectId) return

    setIsResuming(true)
    try {
      const stream = await resumeProject(projectId)
      if (stream && onResume) {
        onResume(stream)
        setShowResumePrompt(false)
      }
    } catch (error) {
      console.error('Resume failed:', error)
    } finally {
      setIsResuming(false)
    }
  }

  // Handle dismiss
  const handleDismiss = () => {
    setShowResumePrompt(false)
    setDismissed(true)
    onDismiss?.()
  }

  // Handle cancel checkpoint
  const handleCancelCheckpoint = async () => {
    if (!projectId) return

    const confirmed = window.confirm(
      'Are you sure you want to cancel? You won\'t be able to resume this project.'
    )

    if (confirmed) {
      await cancelCheckpoint(projectId)
      setShowResumePrompt(false)
      setDismissed(true)
    }
  }

  // Don't show if dismissed or online with nothing to resume
  if (dismissed && isOnline && !canResume) return null

  return (
    <AnimatePresence>
      {/* Offline Banner */}
      {!isOnline && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-50 bg-red-600 text-white px-4 py-3 shadow-lg"
        >
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-3">
              <WifiOff className="w-5 h-5" />
              <div>
                <p className="font-medium">You're offline</p>
                <p className="text-sm text-red-200">
                  Your progress is saved. We'll resume when you're back online.
                </p>
              </div>
            </div>

            {isReconnecting && (
              <div className="flex items-center gap-2 text-sm">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Reconnecting... (attempt {reconnectAttempt})</span>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Reconnecting Banner */}
      {isOnline && isReconnecting && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-50 bg-yellow-500 text-yellow-900 px-4 py-3 shadow-lg"
        >
          <div className="max-w-6xl mx-auto flex items-center gap-3">
            <RefreshCw className="w-5 h-5 animate-spin" />
            <p className="font-medium">Reconnecting to server...</p>
          </div>
        </motion.div>
      )}

      {/* Resume Prompt */}
      {isOnline && canResume && showResumePrompt && resumeInfo && (
        <motion.div
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-4 py-4 shadow-lg"
        >
          <div className="max-w-6xl mx-auto">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="bg-white/20 rounded-full p-2">
                  <AlertCircle className="w-6 h-6" />
                </div>
                <div>
                  <p className="font-bold text-lg">Resume Your Project?</p>
                  <p className="text-blue-100 text-sm">
                    Your previous generation was interrupted.
                    {resumeInfo.generated_files_count > 0 && (
                      <span> {resumeInfo.generated_files_count} files already generated.</span>
                    )}
                    {resumeInfo.remaining_files.length > 0 && (
                      <span> {resumeInfo.remaining_files.length} files remaining.</span>
                    )}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Resume Button */}
                <button
                  onClick={handleResume}
                  disabled={isResuming}
                  className="flex items-center gap-2 bg-white text-blue-600 px-4 py-2 rounded-lg font-bold hover:bg-blue-50 transition-colors disabled:opacity-50"
                >
                  {isResuming ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Resuming...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Resume
                    </>
                  )}
                </button>

                {/* Start Fresh Button */}
                <button
                  onClick={handleCancelCheckpoint}
                  className="flex items-center gap-2 bg-white/20 text-white px-4 py-2 rounded-lg font-medium hover:bg-white/30 transition-colors"
                >
                  Start Fresh
                </button>

                {/* Dismiss Button */}
                <button
                  onClick={handleDismiss}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Progress Details */}
            {resumeInfo.completed_steps.length > 0 && (
              <div className="mt-3 flex items-center gap-2 text-sm text-blue-100">
                <span>Completed:</span>
                {resumeInfo.completed_steps.map((step, idx) => (
                  <span
                    key={step}
                    className="bg-white/20 px-2 py-0.5 rounded text-xs"
                  >
                    {step.replace('_', ' ')}
                  </span>
                ))}
                {resumeInfo.next_step && (
                  <>
                    <span className="mx-2">→</span>
                    <span className="bg-green-500/30 px-2 py-0.5 rounded text-xs">
                      Next: {resumeInfo.next_step.replace('_', ' ')}
                    </span>
                  </>
                )}
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Connection Restored Toast - Only show after a disconnection event, not on initial load */}
      {/* Removed: This was causing blinking on every health check. Connection status is shown in header only when offline. */}
    </AnimatePresence>
  )
}

export default ReconnectionBanner
