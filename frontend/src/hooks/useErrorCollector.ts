/**
 * useErrorCollector Hook - Centralized Error Collection & Auto-Fix
 *
 * SINGLE ENTRY POINT for all error handling in the frontend.
 * This hook integrates with the ErrorCollector service and the unified
 * backend error endpoint for automatic error detection and fixing.
 *
 * Usage:
 * ```tsx
 * const {
 *   reportError,           // Report any error
 *   detectAndReport,       // Detect errors in terminal output
 *   forwardErrorToBackend, // Forward for auto-fix
 *   fixAllErrors           // Manually trigger fix
 * } = useErrorCollector({ projectId: 'xxx' })
 * ```
 */

import { useEffect, useCallback, useRef, useState } from 'react'
import { useErrorStore, CollectedError } from '@/store/errorStore'
import { useTerminalStore } from '@/store/terminalStore'
import { useProjectStore } from '@/store/projectStore'
import { apiClient } from '@/lib/api-client'

// Error source types (expanded for Bolt.new-style capture)
export type ErrorSource =
  | 'browser'      // JS runtime errors
  | 'build'        // Build/compile errors
  | 'docker'       // Container errors
  | 'network'      // Fetch/XHR errors
  | 'backend'      // Backend API errors
  | 'terminal'     // Terminal output errors
  | 'react'        // React component errors
  | 'hmr'          // Hot Module Replacement errors
  | 'resource'     // Resource load errors (img/script/css)
  | 'csp'          // Content Security Policy violations

// Error severity levels
export type ErrorSeverity = 'error' | 'warning' | 'info'

interface UseErrorCollectorOptions {
  projectId?: string
  autoCapture?: boolean
  enabled?: boolean
  debounceMs?: number
  onFixStarted?: (reason: string) => void
  onFixCompleted?: (patchesApplied: number, filesModified: string[]) => void
  onFixFailed?: (error: string) => void
}

interface FixErrorResponse {
  success: boolean
  fixes?: {
    file: string
    patch: string
    description: string
  }[]
  message?: string
  patches_applied?: number
  files_modified?: string[]
}

// Error patterns for auto-detection (Bolt.new-style comprehensive patterns)
const ERROR_PATTERNS: { pattern: RegExp; severity: ErrorSeverity }[] = [
  // TypeScript/JavaScript errors
  { pattern: /error\s+TS\d+:/i, severity: 'error' },
  { pattern: /SyntaxError:/i, severity: 'error' },
  { pattern: /TypeError:/i, severity: 'error' },
  { pattern: /ReferenceError:/i, severity: 'error' },
  // Build errors
  { pattern: /Failed to compile/i, severity: 'error' },
  { pattern: /Build failed/i, severity: 'error' },
  { pattern: /Module not found/i, severity: 'error' },
  { pattern: /Cannot find module/i, severity: 'error' },
  // ===== NEW: Vite import resolution errors =====
  { pattern: /Failed to resolve import/i, severity: 'error' },
  { pattern: /does not provide an export named/i, severity: 'error' },
  { pattern: /Pre-transform error/i, severity: 'error' },
  { pattern: /Error: Command failed/i, severity: 'error' },
  { pattern: /npm ERR!/i, severity: 'error' },
  { pattern: /error\[E\d+\]/i, severity: 'error' },
  { pattern: /error:/i, severity: 'error' },
  { pattern: /exception:/i, severity: 'error' },
  { pattern: /traceback/i, severity: 'error' },
  { pattern: /panic:/i, severity: 'error' },
  { pattern: /fatal error:/i, severity: 'error' },
  { pattern: /exited with code [1-9]/i, severity: 'error' },
  { pattern: /container.*exit.*code.*[1-9]/i, severity: 'error' },
  // ===== NEW: React errors =====
  { pattern: /react.*error/i, severity: 'error' },
  { pattern: /component.*error/i, severity: 'error' },
  { pattern: /render.*error/i, severity: 'error' },
  { pattern: /invalid.*hook.*call/i, severity: 'error' },
  { pattern: /maximum.*update.*depth/i, severity: 'error' },
  { pattern: /minified react error/i, severity: 'error' },
  // ===== NEW: HMR/Vite errors =====
  { pattern: /hmr.*error/i, severity: 'error' },
  { pattern: /\[vite\].*error/i, severity: 'error' },
  { pattern: /hot.*update.*failed/i, severity: 'error' },
  // ===== NEW: Resource load errors =====
  { pattern: /failed to load/i, severity: 'error' },
  { pattern: /loading.*chunk.*failed/i, severity: 'error' },
  // ===== NEW: Network/CORS errors =====
  { pattern: /cors.*error/i, severity: 'error' },
  { pattern: /failed to fetch/i, severity: 'error' },
]

// Patterns to ignore (false positives)
const IGNORE_PATTERNS: RegExp[] = [
  /spawn xdg-open ENOENT/i,
  /spawn open ENOENT/i,
  /npm WARN/i,
  /deprecation warning/i,
  /ExperimentalWarning/i,
]

export function useErrorCollector(options: UseErrorCollectorOptions = {}) {
  const {
    projectId,
    autoCapture = true,
    enabled = true,
    debounceMs = 800,
    onFixStarted,
    onFixCompleted,
    onFixFailed
  } = options

  const {
    errors,
    addBuildError,
    addTerminalError,
    addNetworkError,
    markResolved,
    markAllResolved,
    clearErrors,
    getUnresolvedErrors,
    getErrorCount,
    isFixing,
    setFixing,
    selectedErrorId,
    selectError
  } = useErrorStore()

  const { logs } = useTerminalStore()

  // Get file tree and recently modified files from project store (Bolt.new-style fixer context)
  const { getFileTree, getRecentlyModifiedFiles } = useProjectStore()

  // Buffers for error context
  const outputBufferRef = useRef<string[]>([])
  const errorBufferRef = useRef<{ source: ErrorSource; message: string; timestamp: number }[]>([])
  const currentCommandRef = useRef<string>('')
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)
  const recentErrorsRef = useRef<Set<string>>(new Set())
  const [isConnected, setIsConnected] = useState(false)

  // WebSocket connection for real-time fix notifications
  const wsRef = useRef<WebSocket | null>(null)
  const wsReconnectAttemptsRef = useRef(0)
  const wsReconnectTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Cleanup recent errors periodically
  useEffect(() => {
    const interval = setInterval(() => {
      recentErrorsRef.current.clear()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  // Store callbacks in refs to avoid dependency issues causing reconnections
  const onFixStartedRef = useRef(onFixStarted)
  const onFixCompletedRef = useRef(onFixCompleted)
  const onFixFailedRef = useRef(onFixFailed)

  // Update refs when callbacks change (without triggering reconnection)
  useEffect(() => {
    onFixStartedRef.current = onFixStarted
    onFixCompletedRef.current = onFixCompleted
    onFixFailedRef.current = onFixFailed
  }, [onFixStarted, onFixCompleted, onFixFailed])

  // WebSocket connection for real-time fix notifications from backend
  // IMPORTANT: Only reconnect when projectId or enabled changes, NOT on callback changes
  useEffect(() => {
    if (!projectId || !enabled) return

    // Prevent duplicate connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('[useErrorCollector] WebSocket already connected, skipping')
      return
    }

    const connectWebSocket = () => {
      // Extra guard: don't create new connection if one exists and is connecting/open
      if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
        console.log('[useErrorCollector] WebSocket connection in progress or open, skipping')
        return
      }

      try {
        // Build WebSocket URL
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
        const wsHost = apiUrl
          .replace(/^https?:\/\//, '')
          .replace(/\/api\/v1\/?$/, '')
        const wsUrl = `${wsProtocol}//${wsHost}/api/v1/errors/ws/${projectId}`

        console.log('[useErrorCollector] Connecting WebSocket:', wsUrl)

        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('[useErrorCollector] WebSocket connected for project:', projectId)
          setIsConnected(true)
          wsReconnectAttemptsRef.current = 0
        }

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            console.log('[useErrorCollector] WebSocket message:', msg)

            // Handle fix notifications from backend (use refs to get latest callbacks)
            if (msg.type === 'fix_started') {
              console.log('[useErrorCollector] Fix started:', msg.reason)
              setFixing(true)
              onFixStartedRef.current?.(msg.reason || 'Auto-fix started')
            } else if (msg.type === 'fix_completed') {
              console.log('[useErrorCollector] Fix completed:', msg.patches_applied, 'patches')
              setFixing(false)
              markAllResolved()
              onFixCompletedRef.current?.(msg.patches_applied || 0, msg.files_modified || [])
            } else if (msg.type === 'fix_failed') {
              console.log('[useErrorCollector] Fix failed:', msg.error)
              setFixing(false)
              onFixFailedRef.current?.(msg.error || 'Fix failed')
            }
          } catch (e) {
            console.error('[useErrorCollector] Failed to parse WebSocket message:', e)
          }
        }

        ws.onclose = () => {
          console.log('[useErrorCollector] WebSocket disconnected')
          setIsConnected(false)
          wsRef.current = null

          // Reconnect with exponential backoff (max 5 attempts)
          if (wsReconnectAttemptsRef.current < 5) {
            const delay = 2000 * Math.pow(2, wsReconnectAttemptsRef.current)
            wsReconnectAttemptsRef.current++
            console.log(`[useErrorCollector] Reconnecting in ${delay}ms (attempt ${wsReconnectAttemptsRef.current})`)
            wsReconnectTimerRef.current = setTimeout(connectWebSocket, delay)
          }
        }

        ws.onerror = (error) => {
          console.error('[useErrorCollector] WebSocket error:', error)
        }
      } catch (error) {
        console.error('[useErrorCollector] Failed to connect WebSocket:', error)
      }
    }

    // Initial connection
    connectWebSocket()

    // Cleanup on unmount or projectId change
    return () => {
      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current)
        wsReconnectTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsConnected(false)
    }
  }, [projectId, enabled, setFixing, markAllResolved]) // Removed callback dependencies - use refs instead

  // Watch terminal logs for errors (legacy support)
  useEffect(() => {
    if (!autoCapture || !enabled) return

    const latestLogs = logs.slice(-10)
    latestLogs.forEach(log => {
      if (log.type === 'error') {
        const content = log.content
        const isBuildError = ERROR_PATTERNS.some(({ pattern }) => pattern.test(content))

        if (isBuildError) {
          addBuildError(content)
        } else if (content.includes('Error:') || content.includes('error:')) {
          addTerminalError(content)
        }
      }
    })
  }, [logs, autoCapture, enabled, addBuildError, addTerminalError])

  /**
   * Set current command being executed (for context)
   */
  const setCurrentCommand = useCallback((command: string) => {
    currentCommandRef.current = command
  }, [])

  /**
   * Add output to buffer (for context)
   */
  const addOutput = useCallback((output: string) => {
    if (!enabled || !output) return

    outputBufferRef.current.push(output)
    if (outputBufferRef.current.length > 50) {
      outputBufferRef.current.shift()
    }
  }, [enabled])

  /**
   * Check if output should be ignored
   */
  const shouldIgnore = useCallback((message: string): boolean => {
    return IGNORE_PATTERNS.some(pattern => pattern.test(message))
  }, [])

  /**
   * Detect error severity from message
   */
  const detectSeverity = useCallback((message: string): ErrorSeverity => {
    for (const { pattern, severity } of ERROR_PATTERNS) {
      if (pattern.test(message)) {
        return severity
      }
    }
    return 'info'
  }, [])

  /**
   * SINGLE ENTRY POINT: Report an error from any source
   * This is the main method for reporting errors
   */
  const reportError = useCallback((
    source: ErrorSource,
    message: string,
    opts?: {
      file?: string
      line?: number
      column?: number
      stack?: string
      severity?: ErrorSeverity
    }
  ) => {
    if (!enabled || !message) return
    if (shouldIgnore(message)) return

    // Deduplicate
    const errorKey = `${source}:${message.slice(0, 100)}`
    if (recentErrorsRef.current.has(errorKey)) return
    recentErrorsRef.current.add(errorKey)

    const severity = opts?.severity ?? detectSeverity(message)

    console.log('[useErrorCollector] Error reported:', { source, message: message.slice(0, 100), severity })

    // Add to error buffer
    errorBufferRef.current.push({
      source,
      message,
      timestamp: Date.now()
    })
    if (errorBufferRef.current.length > 20) {
      errorBufferRef.current.shift()
    }

    // Also add to output buffer
    outputBufferRef.current.push(message)
    if (outputBufferRef.current.length > 50) {
      outputBufferRef.current.shift()
    }

    // Add to error store based on source
    if (source === 'build' || source === 'docker') {
      addBuildError(message, opts?.file, opts?.line)
    } else if (source === 'browser') {
      // Browser errors use addBrowserError which accepts file/line/column/stack
      const { addBrowserError } = useErrorStore.getState()
      addBrowserError(message, opts?.file, opts?.line, opts?.column, opts?.stack)
    } else if (source === 'network') {
      // Network errors require a URL - use file field if available, otherwise empty string
      addNetworkError(message, opts?.file || '', undefined, undefined)
    } else {
      addTerminalError(message)
    }

    // Schedule debounced forward to backend
    scheduleForwardToBackend()
  }, [enabled, shouldIgnore, detectSeverity, addBuildError, addNetworkError, addTerminalError])

  /**
   * Detect and report errors in terminal output
   * Returns true if error was detected
   */
  const detectAndReport = useCallback((output: string, source: ErrorSource = 'build'): boolean => {
    if (!enabled || !output) return false

    // Add to output buffer regardless
    addOutput(output)

    if (shouldIgnore(output)) return false

    // Check for error patterns
    for (const { pattern, severity } of ERROR_PATTERNS) {
      if (pattern.test(output)) {
        reportError(source, output, { severity })
        return true
      }
    }

    return false
  }, [enabled, addOutput, shouldIgnore, reportError])

  /**
   * Schedule debounced forward to backend
   */
  const scheduleForwardToBackend = useCallback(() => {
    if (!projectId) return

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      forwardErrorToBackend()
      debounceTimerRef.current = null
    }, debounceMs)
  }, [projectId, debounceMs])

  /**
   * Forward errors to backend for auto-fix
   * Uses the unified /errors/report endpoint
   * Includes file tree and recently modified files for Bolt.new-style fixer context
   */
  const forwardErrorToBackend = useCallback(async () => {
    if (!projectId || errorBufferRef.current.length === 0) return

    const fullContext = outputBufferRef.current.join('\n')
    const errors = errorBufferRef.current.map(e => ({
      source: e.source,
      type: 'auto_detected',
      message: e.message,
      severity: detectSeverity(e.message),
      timestamp: e.timestamp
    }))

    // Get file tree and recently modified files for fixer context (Bolt.new style!)
    const fileTree = getFileTree()
    const recentlyModified = getRecentlyModifiedFiles(5 * 60 * 1000) // Last 5 minutes

    console.log('[useErrorCollector] Forwarding to backend:', {
      projectId,
      errorCount: errors.length,
      contextLines: outputBufferRef.current.length,
      fileTreeCount: fileTree.length,
      recentlyModifiedCount: recentlyModified.length
    })

    try {
      onFixStarted?.(errors[errors.length - 1]?.message?.slice(0, 100) || 'Auto-fix started')

      const response = await apiClient.post<{
        success: boolean
        fix_triggered: boolean
        fix_status?: string
        message: string
      }>(`/errors/report/${projectId}`, {
        errors,
        context: fullContext,
        command: currentCommandRef.current,
        timestamp: Date.now(),
        // Bolt.new-style fixer context
        file_tree: fileTree,
        recently_modified: recentlyModified.map(f => ({
          path: f.path,
          action: f.action,
          timestamp: f.timestamp
        }))
      })

      console.log('[useErrorCollector] Backend response:', response)

      // Clear error buffer after successful forward
      errorBufferRef.current = []

      return response
    } catch (error) {
      console.error('[useErrorCollector] Failed to forward errors:', error)
      onFixFailed?.(String(error))
    }
  }, [projectId, detectSeverity, onFixStarted, onFixFailed, getFileTree, getRecentlyModifiedFiles])

  /**
   * Force immediate forward (use when command completes)
   */
  const forwardNow = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
    forwardErrorToBackend()
  }, [forwardErrorToBackend])

  /**
   * Clear all buffers
   */
  const clearBuffers = useCallback(() => {
    outputBufferRef.current = []
    errorBufferRef.current = []
    recentErrorsRef.current.clear()
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
    clearErrors()
  }, [clearErrors])

  // Fix a single error using Fixer Agent (legacy support)
  const fixError = useCallback(async (error: CollectedError): Promise<FixErrorResponse> => {
    if (!projectId) {
      return { success: false, message: 'No project selected' }
    }

    setFixing(true)
    selectError(error.id)

    try {
      const response = await apiClient.post<FixErrorResponse>(`/projects/${projectId}/fix-error`, {
        error: {
          message: error.message,
          file: error.file,
          line: error.line,
          column: error.column,
          stack: error.stack,
          source: error.source,
          severity: error.severity,
          url: error.url,
          status: error.status,
          method: error.method
        }
      })

      if (response.success) {
        markResolved(error.id)
      }

      return response
    } catch (err: any) {
      console.error('[useErrorCollector] Fix error failed:', err)
      return {
        success: false,
        message: err.message || 'Failed to fix error'
      }
    } finally {
      setFixing(false)
      selectError(null)
    }
  }, [projectId, setFixing, selectError, markResolved])

  // Fix all unresolved errors
  const fixAllErrors = useCallback(async (): Promise<FixErrorResponse> => {
    if (!projectId) {
      return { success: false, message: 'No project selected' }
    }

    const unresolvedErrors = getUnresolvedErrors()
    if (unresolvedErrors.length === 0) {
      return { success: true, message: 'No errors to fix' }
    }

    setFixing(true)
    onFixStarted?.(`Fixing ${unresolvedErrors.length} errors`)

    try {
      // Use unified error endpoint
      const response = await apiClient.post<FixErrorResponse>(`/errors/report/${projectId}`, {
        errors: unresolvedErrors.map(err => ({
          source: err.source || 'build',
          type: 'manual_fix',
          message: err.message,
          file: err.file,
          line: err.line,
          column: err.column,
          stack: err.stack,
          severity: err.severity || 'error'
        })),
        context: unresolvedErrors.map(e => e.message).join('\n'),
        timestamp: Date.now()
      })

      if (response.success) {
        markAllResolved()
        onFixCompleted?.(response.patches_applied || 0, response.files_modified || [])
      } else {
        onFixFailed?.(response.message || 'Fix failed')
      }

      return response
    } catch (err: any) {
      console.error('[useErrorCollector] Fix all errors failed:', err)
      onFixFailed?.(err.message || 'Failed to fix errors')
      return {
        success: false,
        message: err.message || 'Failed to fix errors'
      }
    } finally {
      setFixing(false)
    }
  }, [projectId, setFixing, getUnresolvedErrors, markAllResolved, onFixStarted, onFixCompleted, onFixFailed])

  // Format error for display
  const formatError = useCallback((error: CollectedError): string => {
    let formatted = error.message
    if (error.file) {
      formatted += `\n  at ${error.file}`
      if (error.line) {
        formatted += `:${error.line}`
        if (error.column) {
          formatted += `:${error.column}`
        }
      }
    }
    return formatted
  }, [])

  // Get error context for AI
  const getErrorContext = useCallback(async (error: CollectedError): Promise<string> => {
    let context = `Error: ${error.message}\n`
    context += `Source: ${error.source}\n`
    context += `Severity: ${error.severity}\n`

    if (error.file) {
      context += `File: ${error.file}\n`
      if (error.line) {
        context += `Line: ${error.line}\n`
      }
    }

    if (error.source === 'network') {
      if (error.url) context += `URL: ${error.url}\n`
      if (error.method) context += `HTTP Method: ${error.method}\n`
      if (error.status) context += `HTTP Status: ${error.status}\n`
    }

    if (error.stack) {
      context += `\nStack trace:\n${error.stack}\n`
    }

    return context
  }, [])

  return {
    // State
    errors,
    unresolvedErrors: getUnresolvedErrors(),
    errorCount: getErrorCount(),
    isFixing,
    selectedErrorId,
    isConnected,

    // SINGLE ENTRY POINT - Primary methods
    reportError,          // Report any error
    detectAndReport,      // Auto-detect and report
    forwardErrorToBackend, // Manual forward to backend
    forwardNow,           // Force immediate forward

    // Buffer management
    addOutput,
    setCurrentCommand,
    clearBuffers,
    getOutputBuffer: () => [...outputBufferRef.current],
    getErrorBuffer: () => [...errorBufferRef.current],

    // Actions (legacy support)
    fixError,
    fixAllErrors,
    markResolved,
    markAllResolved,
    clearErrors,
    selectError,
    addNetworkError,

    // Utilities
    formatError,
    getErrorContext
  }
}

export default useErrorCollector
