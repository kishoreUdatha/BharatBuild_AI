/**
 * useLogViewer Hook - READ-ONLY Log Viewer
 *
 * PRODUCTION-GRADE ARCHITECTURE:
 * - Terminal logs are captured in BACKEND (ExecutionContext)
 * - Auto-fixer is triggered in BACKEND (container_executor.py)
 * - This hook is READ-ONLY - only displays logs and fix status
 *
 * This is the CORRECT approach used by Bolt.new and similar platforms:
 * - UI is a "CCTV camera" - only shows what's happening
 * - Backend is the "police station" - makes decisions and fixes
 *
 * DO NOT:
 * - Parse errors in this hook
 * - Send errors to backend from here
 * - Make fix decisions here
 *
 * The old useErrorCollector.ts is DEPRECATED in favor of this approach.
 */

import { useEffect, useCallback, useRef, useState } from 'react'

// Fix status from backend (read-only)
export type FixStatus =
  | 'idle'           // No fix in progress
  | 'fixing'         // Fix attempt in progress
  | 'success'        // Fix applied successfully
  | 'failed'         // Fix failed
  | 'exhausted'      // Max attempts reached

// Execution state from backend (read-only)
export type ExecutionState =
  | 'pending'
  | 'running'
  | 'success'
  | 'failed'
  | 'fixing'
  | 'fixed'
  | 'exhausted'

interface LogEntry {
  timestamp: number
  content: string
  type: 'stdout' | 'stderr' | 'system' | 'fix'
}

interface UseLogViewerOptions {
  projectId?: string
  enabled?: boolean
  maxLogLines?: number
  onServerStarted?: (previewUrl: string) => void
  onFixStarted?: () => void
  onFixCompleted?: (filesModified: string[]) => void
  onFixFailed?: (error: string) => void
}

interface LogViewerState {
  logs: LogEntry[]
  fixStatus: FixStatus
  executionState: ExecutionState
  serverStarted: boolean
  previewUrl: string | null
  fixAttempt: number
  maxFixAttempts: number
  isConnected: boolean
}

/**
 * Read-only log viewer hook.
 *
 * This hook only DISPLAYS information from the backend.
 * It does NOT send errors or make fix decisions.
 */
export function useLogViewer(options: UseLogViewerOptions = {}) {
  const {
    projectId,
    enabled = true,
    maxLogLines = 500,
    onServerStarted,
    onFixStarted,
    onFixCompleted,
    onFixFailed
  } = options

  const [state, setState] = useState<LogViewerState>({
    logs: [],
    fixStatus: 'idle',
    executionState: 'pending',
    serverStarted: false,
    previewUrl: null,
    fixAttempt: 0,
    maxFixAttempts: 3,
    isConnected: false
  })

  // Store callbacks in refs to avoid reconnection on callback changes
  const callbacksRef = useRef({ onServerStarted, onFixStarted, onFixCompleted, onFixFailed })
  useEffect(() => {
    callbacksRef.current = { onServerStarted, onFixStarted, onFixCompleted, onFixFailed }
  }, [onServerStarted, onFixStarted, onFixCompleted, onFixFailed])

  // WebSocket connection
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null)

  /**
   * Add a log entry (internal use only)
   */
  const addLog = useCallback((content: string, type: LogEntry['type'] = 'stdout') => {
    setState(prev => {
      const newLogs = [...prev.logs, { timestamp: Date.now(), content, type }]
      // Trim logs if exceeding max
      if (newLogs.length > maxLogLines) {
        return { ...prev, logs: newLogs.slice(-maxLogLines) }
      }
      return { ...prev, logs: newLogs }
    })
  }, [maxLogLines])

  /**
   * Parse special markers from log output.
   * These markers are emitted by container_executor.py.
   */
  const parseLogMarkers = useCallback((line: string) => {
    // Preview READY marker - server has passed health check and is ready for navigation
    if (line.startsWith('__PREVIEW_READY__:')) {
      const url = line.replace('__PREVIEW_READY__:', '').trim()
      setState(prev => ({
        ...prev,
        serverStarted: true,
        previewUrl: url,
        executionState: 'success'
      }))
      callbacksRef.current.onServerStarted?.(url)
      return true
    }

    // Server started marker (legacy - keep for backwards compatibility but don't trigger navigation)
    if (line.startsWith('__SERVER_STARTED__:')) {
      const url = line.replace('__SERVER_STARTED__:', '').trim()
      // Only set URL, wait for __PREVIEW_READY__ to actually navigate
      setState(prev => ({
        ...prev,
        previewUrl: url
      }))
      return true
    }

    // Preview URL marker - just store URL, don't navigate yet
    if (line.startsWith('_PREVIEW_URL_:')) {
      const url = line.replace('_PREVIEW_URL_:', '').trim()
      setState(prev => ({ ...prev, previewUrl: url }))
      return true
    }

    // Fix starting marker
    if (line === '__FIX_STARTING__') {
      setState(prev => ({
        ...prev,
        fixStatus: 'fixing',
        executionState: 'fixing',
        fixAttempt: prev.fixAttempt + 1
      }))
      callbacksRef.current.onFixStarted?.()
      return true
    }

    // Fix success marker
    if (line === '__FIX_SUCCESS__') {
      setState(prev => ({
        ...prev,
        fixStatus: 'success',
        executionState: 'fixed'
      }))
      // Files modified will be in subsequent log lines
      callbacksRef.current.onFixCompleted?.([])
      return true
    }

    // Fix failed marker
    if (line.startsWith('__FIX_FAILED__:')) {
      const error = line.replace('__FIX_FAILED__:', '').trim()
      setState(prev => ({
        ...prev,
        fixStatus: 'failed',
        executionState: prev.fixAttempt >= prev.maxFixAttempts ? 'exhausted' : 'failed'
      }))
      callbacksRef.current.onFixFailed?.(error)
      return true
    }

    // Error marker
    if (line.startsWith('__ERROR__:')) {
      setState(prev => ({ ...prev, executionState: 'failed' }))
      return false // Still show this log
    }

    // Validation failed marker (pre-run check)
    if (line.startsWith('__VALIDATION_FAILED__:')) {
      const missingFiles = line.replace('__VALIDATION_FAILED__:', '').trim()
      setState(prev => ({
        ...prev,
        executionState: 'failed',
        fixStatus: 'failed'
      }))
      callbacksRef.current.onFixFailed?.(`Workspace validation failed. Missing: ${missingFiles}`)
      return true
    }

    // Health check failed marker
    if (line.startsWith('__HEALTH_CHECK_FAILED__:')) {
      const reason = line.replace('__HEALTH_CHECK_FAILED__:', '').trim()
      // Don't fail completely - just log warning
      console.warn('[useLogViewer] Container health check failed:', reason)
      return true
    }

    // Fix exhausted marker (max attempts reached)
    if (line === '__FIX_EXHAUSTED__') {
      setState(prev => ({
        ...prev,
        fixStatus: 'exhausted',
        executionState: 'exhausted'
      }))
      callbacksRef.current.onFixFailed?.('Maximum fix attempts reached')
      return true
    }

    return false
  }, [])

  /**
   * Process incoming log line from SSE stream.
   */
  const processLogLine = useCallback((line: string) => {
    if (!line.trim()) return

    // Check for special markers (these control state, may not be displayed)
    const isMarker = parseLogMarkers(line)

    // Determine log type based on content
    let logType: LogEntry['type'] = 'stdout'
    if (line.startsWith('🔴') || line.includes('ERROR') || line.includes('error')) {
      logType = 'stderr'
    } else if (line.startsWith('🔧') || line.startsWith('✅') || line.startsWith('❌')) {
      logType = 'fix'
    } else if (line.startsWith('📍') || line.startsWith('🐳') || line.startsWith('🚀')) {
      logType = 'system'
    }

    // Add to logs unless it's a pure marker (starts with __)
    if (!line.startsWith('__')) {
      addLog(line, logType)
    }
  }, [parseLogMarkers, addLog])

  /**
   * Connect to WebSocket for real-time log streaming.
   */
  useEffect(() => {
    if (!projectId || !enabled) return

    // Prevent duplicate connections
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const connectWebSocket = () => {
      if (wsRef.current?.readyState === WebSocket.CONNECTING ||
          wsRef.current?.readyState === WebSocket.OPEN) {
        return
      }

      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
        const wsHost = apiUrl
          .replace(/^https?:\/\//, '')
          .replace(/\/api\/v1\/?$/, '')
        const wsUrl = `${wsProtocol}//${wsHost}/api/v1/log_stream/stream/${projectId}`

        console.log('[useLogViewer] Connecting WebSocket:', wsUrl)

        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('[useLogViewer] WebSocket connected')
          setState(prev => ({ ...prev, isConnected: true }))
          reconnectAttemptsRef.current = 0
        }

        ws.onmessage = (event) => {
          try {
            // Handle both JSON and plain text messages
            if (event.data.startsWith('{')) {
              const msg = JSON.parse(event.data)
              if (msg.type === 'log' && msg.content) {
                processLogLine(msg.content)
              }
            } else {
              // Plain text log line
              processLogLine(event.data)
            }
          } catch (e) {
            // If JSON parse fails, treat as plain text
            processLogLine(event.data)
          }
        }

        ws.onclose = () => {
          console.log('[useLogViewer] WebSocket disconnected')
          setState(prev => ({ ...prev, isConnected: false }))
          wsRef.current = null

          // Reconnect with exponential backoff
          if (reconnectAttemptsRef.current < 5) {
            const delay = 2000 * Math.pow(2, reconnectAttemptsRef.current)
            reconnectAttemptsRef.current++
            console.log(`[useLogViewer] Reconnecting in ${delay}ms`)
            reconnectTimerRef.current = setTimeout(connectWebSocket, delay)
          }
        }

        ws.onerror = (error) => {
          console.error('[useLogViewer] WebSocket error:', error)
        }
      } catch (error) {
        console.error('[useLogViewer] Failed to connect WebSocket:', error)
      }
    }

    connectWebSocket()

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current)
        reconnectTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setState(prev => ({ ...prev, isConnected: false }))
    }
  }, [projectId, enabled, processLogLine])

  /**
   * Clear all logs (for UI reset)
   */
  const clearLogs = useCallback(() => {
    setState(prev => ({ ...prev, logs: [] }))
  }, [])

  /**
   * Reset state (for new execution)
   */
  const reset = useCallback(() => {
    setState({
      logs: [],
      fixStatus: 'idle',
      executionState: 'pending',
      serverStarted: false,
      previewUrl: null,
      fixAttempt: 0,
      maxFixAttempts: 3,
      isConnected: state.isConnected
    })
  }, [state.isConnected])

  return {
    // State (read-only)
    logs: state.logs,
    fixStatus: state.fixStatus,
    executionState: state.executionState,
    serverStarted: state.serverStarted,
    previewUrl: state.previewUrl,
    fixAttempt: state.fixAttempt,
    maxFixAttempts: state.maxFixAttempts,
    isConnected: state.isConnected,

    // Derived state
    isFixing: state.fixStatus === 'fixing',
    hasFailed: state.executionState === 'failed' || state.executionState === 'exhausted',
    isExhausted: state.executionState === 'exhausted',

    // Actions (UI only - no backend interaction)
    clearLogs,
    reset,

    // For manual log processing (SSE streams)
    processLogLine
  }
}

export default useLogViewer
