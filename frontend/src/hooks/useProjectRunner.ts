'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { useProjectStore } from '@/store/projectStore'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// =========== OUTPUT BUFFER + ERROR ACCUMULATOR (Bolt.new style!) ===========
// Key insight: We need to capture ALL output lines for context, not just error lines.
// When an error is detected, we include the previous lines for context.
// This gives Claude much better information for fixing errors!

interface OutputBuffer {
  // Rolling buffer of ALL output lines (for context)
  allLines: string[]
  // Error lines to be sent (with context)
  errorLines: string[]
  // Whether we're in "error state" (after first error detected)
  inErrorState: boolean
  // Timer for debounced sending
  timer: NodeJS.Timeout | null
}

const outputBuffers: Record<string, OutputBuffer> = {}

// Debounce delay - wait this long for more lines before sending
const ERROR_ACCUMULATE_DELAY_MS = 1200 // Increased to capture more context

// Maximum lines to keep in rolling buffer
const MAX_CONTEXT_LINES = 30

// Maximum error lines to accumulate
const MAX_ERROR_LINES = 50

async function sendAccumulatedErrors(projectId: string) {
  // ============= DISABLED =============
  // Backend now handles build error collection with full context directly in docker_executor.py
  // When command completes with errors, backend sends FULL output context (40 lines) to LogBus
  // This frontend forwarding was causing early/incomplete "ERROR:" messages to trigger auto-fix
  // Browser runtime errors are still forwarded via useErrorCollector (different path)
  // =====================================

  const buffer = outputBuffers[projectId]
  if (!buffer || buffer.errorLines.length === 0) return

  // Just clear the buffer without forwarding - backend handles it
  buffer.errorLines = []
  buffer.inErrorState = false
  if (buffer.timer) {
    clearTimeout(buffer.timer)
    buffer.timer = null
  }

  console.log('[useProjectRunner] Error accumulation cleared - backend handles with full context')
}

// Add ANY output line to the rolling buffer (for context)
function addOutputLine(projectId: string, line: string) {
  if (!line || !line.trim()) return

  // Initialize buffer if needed
  if (!outputBuffers[projectId]) {
    outputBuffers[projectId] = { allLines: [], errorLines: [], inErrorState: false, timer: null }
  }

  const buffer = outputBuffers[projectId]

  // Add to rolling context buffer
  buffer.allLines.push(line)
  if (buffer.allLines.length > MAX_CONTEXT_LINES) {
    buffer.allLines.shift()
  }

  // If we're in error state, also add to error lines
  if (buffer.inErrorState) {
    buffer.errorLines.push(line)
    if (buffer.errorLines.length > MAX_ERROR_LINES) {
      buffer.errorLines.shift()
    }
    // Reset the timer to wait for more lines
    if (buffer.timer) {
      clearTimeout(buffer.timer)
    }
    buffer.timer = setTimeout(() => {
      sendAccumulatedErrors(projectId)
    }, ERROR_ACCUMULATE_DELAY_MS)
  }
}

// Trigger error state - start accumulating all subsequent lines
function accumulateError(projectId: string, errorLine: string) {
  // Initialize buffer if needed
  if (!outputBuffers[projectId]) {
    outputBuffers[projectId] = { allLines: [], errorLines: [], inErrorState: false, timer: null }
  }

  const buffer = outputBuffers[projectId]

  // Enter error state
  buffer.inErrorState = true

  // Add the error line itself
  buffer.errorLines.push(errorLine)
  if (buffer.errorLines.length > MAX_ERROR_LINES) {
    buffer.errorLines.shift()
  }

  // Clear existing timer and set new one
  if (buffer.timer) {
    clearTimeout(buffer.timer)
  }

  // Schedule send after delay (allows more lines to accumulate)
  buffer.timer = setTimeout(() => {
    sendAccumulatedErrors(projectId)
  }, ERROR_ACCUMULATE_DELAY_MS)
}

// Force send accumulated errors immediately (e.g., on command completion)
function flushErrorBuffer(projectId: string) {
  const buffer = outputBuffers[projectId]
  if (buffer?.timer) {
    clearTimeout(buffer.timer)
    buffer.timer = null
  }
  if (buffer?.errorLines.length > 0) {
    sendAccumulatedErrors(projectId)
  }
}

// Reset error state (e.g., when server starts successfully)
function resetErrorState(projectId: string) {
  const buffer = outputBuffers[projectId]
  if (buffer) {
    buffer.inErrorState = false
    // Don't clear errorLines - they might still need to be sent
  }
}

export type ProjectRunStatus = 'idle' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error'

export interface RunLog {
  id: string
  timestamp: Date
  type: 'info' | 'error' | 'success' | 'command'
  content: string
}

export interface ProjectRunner {
  projectId: string
  status: ProjectRunStatus
  port: number | null
  previewUrl: string | null
  logs: RunLog[]
}

export function useProjectRunner() {
  const [runners, setRunners] = useState<Record<string, ProjectRunner>>({})
  const abortControllers = useRef<Record<string, AbortController>>({})
  const { currentProject } = useProjectStore()

  // Get runner for current project
  const currentRunner = currentProject?.id ? runners[currentProject.id] : null

  // Initialize runner for a project
  const initRunner = useCallback((projectId: string): ProjectRunner => {
    return {
      projectId,
      status: 'idle',
      port: null,
      previewUrl: null,
      logs: []
    }
  }, [])

  // Add log entry
  const addLog = useCallback((projectId: string, type: RunLog['type'], content: string) => {
    const log: RunLog = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      type,
      content
    }

    setRunners(prev => ({
      ...prev,
      [projectId]: {
        ...(prev[projectId] || initRunner(projectId)),
        logs: [...(prev[projectId]?.logs || []), log].slice(-100) // Keep last 100 logs
      }
    }))
  }, [initRunner])

  // Update runner status
  const updateStatus = useCallback((projectId: string, status: ProjectRunStatus, updates?: Partial<ProjectRunner>) => {
    setRunners(prev => ({
      ...prev,
      [projectId]: {
        ...(prev[projectId] || initRunner(projectId)),
        status,
        ...updates
      }
    }))
  }, [initRunner])

  // Run project
  const runProject = useCallback(async (projectId: string, commands?: string[]) => {
    // Cancel any existing run
    if (abortControllers.current[projectId]) {
      abortControllers.current[projectId].abort()
    }

    const controller = new AbortController()
    abortControllers.current[projectId] = controller

    updateStatus(projectId, 'starting')
    addLog(projectId, 'info', 'Starting project...')

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${API_BASE_URL}/execution/run/${projectId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ project_id: projectId, commands }),
        signal: controller.signal
      })

      if (!response.ok) {
        throw new Error(`Failed to start project: ${response.statusText}`)
      }

      // Handle SSE stream
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('No response body')
      }

      updateStatus(projectId, 'running')
      addLog(projectId, 'success', 'Project started!')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = decoder.decode(value, { stream: true })
        const lines = text.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))

              if (data.type === 'output') {
                addLog(projectId, 'info', data.content)
                // Add ALL output to context buffer (for error context)
                if (data.content) {
                  addOutputLine(projectId, data.content)
                }
                // Check if output contains build errors - trigger error state
                if (data.content && (
                  data.content.includes('error') ||
                  data.content.includes('Error') ||
                  data.content.includes('ERROR') ||
                  data.content.includes('Failed') ||
                  data.content.includes('Cannot find') ||
                  data.content.includes('Module not found') ||
                  data.content.includes('npm ERR') ||
                  data.content.includes('ENOENT') ||
                  data.content.includes('ELIFECYCLE')
                )) {
                  accumulateError(projectId, data.content)
                }
              } else if (data.type === 'error') {
                addLog(projectId, 'error', data.content)
                // Add to context and trigger error state
                if (data.content) {
                  addOutputLine(projectId, data.content)
                  accumulateError(projectId, data.content)
                }
              } else if (data.type === 'server_started') {
                const port = data.port || 3000
                const previewUrl = `http://localhost:${port}`
                updateStatus(projectId, 'running', { port, previewUrl })
                addLog(projectId, 'success', `Server running at ${previewUrl}`)
                // Server started successfully - reset error state
                resetErrorState(projectId)
              } else if (data.type === 'command') {
                addLog(projectId, 'command', `$ ${data.content}`)
              }
            } catch {
              // Not JSON, just log as text
              if (line.slice(6).trim()) {
                addLog(projectId, 'info', line.slice(6))
              }
            }
          }
        }
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        addLog(projectId, 'info', 'Project execution cancelled')
        updateStatus(projectId, 'stopped')
      } else {
        console.error('Run project error:', error)
        const errorMsg = error.message || 'Failed to run project'
        addLog(projectId, 'error', errorMsg)
        // Forward error to backend LogBus for auto-fix (accumulated)
        accumulateError(projectId, errorMsg)
        flushErrorBuffer(projectId) // Flush immediately on command failure
        updateStatus(projectId, 'error')
      }
    }
  }, [updateStatus, addLog])

  // Stop project
  const stopProject = useCallback(async (projectId: string) => {
    updateStatus(projectId, 'stopping')
    addLog(projectId, 'info', 'Stopping project...')

    // Abort the current stream
    if (abortControllers.current[projectId]) {
      abortControllers.current[projectId].abort()
      delete abortControllers.current[projectId]
    }

    try {
      const token = localStorage.getItem('access_token')
      await fetch(`${API_BASE_URL}/execution/stop/${projectId}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      updateStatus(projectId, 'stopped', { port: null, previewUrl: null })
      addLog(projectId, 'success', 'Project stopped')
    } catch (error: any) {
      console.error('Stop project error:', error)
      addLog(projectId, 'error', 'Failed to stop project gracefully')
      updateStatus(projectId, 'stopped', { port: null, previewUrl: null })
    }
  }, [updateStatus, addLog])

  // Clear logs for a project
  const clearLogs = useCallback((projectId: string) => {
    setRunners(prev => ({
      ...prev,
      [projectId]: {
        ...(prev[projectId] || initRunner(projectId)),
        logs: []
      }
    }))
  }, [initRunner])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      Object.values(abortControllers.current).forEach(controller => {
        controller.abort()
      })
    }
  }, [])

  return {
    runners,
    currentRunner,
    runProject,
    stopProject,
    clearLogs,
    addLog
  }
}

// Create a global instance for sharing across components
import { create } from 'zustand'

interface ProjectRunnerStore {
  runners: Record<string, ProjectRunner>
  setRunner: (projectId: string, runner: Partial<ProjectRunner>) => void
  addLog: (projectId: string, type: RunLog['type'], content: string) => void
  clearLogs: (projectId: string) => void
}

export const useProjectRunnerStore = create<ProjectRunnerStore>((set) => ({
  runners: {},

  setRunner: (projectId, updates) => set((state) => {
    const existing = state.runners[projectId] || {
      projectId,
      status: 'idle' as ProjectRunStatus,
      port: null,
      previewUrl: null,
      logs: []
    }
    return {
      runners: {
        ...state.runners,
        [projectId]: {
          ...existing,
          ...updates
        }
      }
    }
  }),

  addLog: (projectId, type, content) => set((state) => {
    const runner = state.runners[projectId] || {
      projectId,
      status: 'idle',
      port: null,
      previewUrl: null,
      logs: []
    }

    const log: RunLog = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      type,
      content
    }

    return {
      runners: {
        ...state.runners,
        [projectId]: {
          ...runner,
          logs: [...runner.logs, log].slice(-100)
        }
      }
    }
  }),

  clearLogs: (projectId) => set((state) => ({
    runners: {
      ...state.runners,
      [projectId]: {
        ...state.runners[projectId],
        logs: []
      }
    }
  }))
}))
