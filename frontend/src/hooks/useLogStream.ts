/**
 * useLogStream Hook - Forward errors from frontend to backend LogBus
 *
 * This hook enables auto-fixing for static previews (srcdoc mode) by:
 * 1. Connecting to backend WebSocket log_stream endpoint
 * 2. Forwarding errors received via postMessage to the backend
 * 3. Receiving fix notifications from the backend
 *
 * Without this, errors from static preview iframes never reach the backend
 * because srcdoc iframes cannot connect to WebSocket (origin is null).
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import { apiClient } from '@/lib/api-client'

interface LogStreamOptions {
  projectId?: string
  enabled?: boolean
  onFixStarted?: (reason: string) => void
  onFixCompleted?: (patchesApplied: number, filesModified: string[]) => void
  onFixFailed?: (error: string) => void
  onProjectRestarted?: () => void
}

interface LogEntry {
  source: 'browser' | 'build' | 'backend' | 'docker' | 'network'
  type: string
  data: Record<string, unknown>
  timestamp: number
}

export function useLogStream(options: LogStreamOptions) {
  const {
    projectId,
    enabled = true,
    onFixStarted,
    onFixCompleted,
    onFixFailed,
    onProjectRestarted
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const messageQueueRef = useRef<LogEntry[]>([])

  const MAX_RECONNECT_ATTEMPTS = 5
  const RECONNECT_DELAY_BASE = 2000

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!projectId || !enabled || isConnecting) return

    // Don't reconnect if already connected
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    setIsConnecting(true)

    try {
      // Build WebSocket URL
      // Strip protocol and /api/v1 suffix from API URL to get just host:port
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '').replace(/\/api\/v1\/?$/, '') || 'localhost:8000'
      const wsUrl = `${wsProtocol}//${wsHost}/api/v1/log-stream/stream/${projectId}`

      console.log('[useLogStream] Connecting to:', wsUrl)

      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[useLogStream] Connected to log stream')
        setIsConnected(true)
        setIsConnecting(false)
        reconnectAttemptsRef.current = 0

        // Send queued messages
        while (messageQueueRef.current.length > 0) {
          const msg = messageQueueRef.current.shift()
          if (msg) {
            ws.send(JSON.stringify(msg))
          }
        }
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)

          // Handle fix events from backend
          if (msg.type === 'fix_started') {
            console.log('[useLogStream] Fix started:', msg.reason)
            onFixStarted?.(msg.reason)
          } else if (msg.type === 'fix_completed') {
            console.log('[useLogStream] Fix completed:', msg.patches_applied, 'patches')
            onFixCompleted?.(msg.patches_applied || 0, msg.files_modified || [])
          } else if (msg.type === 'fix_failed') {
            console.log('[useLogStream] Fix failed:', msg.error)
            onFixFailed?.(msg.error)
          } else if (msg.type === 'project_restarted') {
            console.log('[useLogStream] Project restarted')
            onProjectRestarted?.()
          }
        } catch (e) {
          // Ignore non-JSON messages
        }
      }

      ws.onclose = () => {
        console.log('[useLogStream] Disconnected from log stream')
        setIsConnected(false)
        setIsConnecting(false)
        wsRef.current = null

        // Attempt reconnect
        if (enabled && reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = RECONNECT_DELAY_BASE * Math.pow(2, reconnectAttemptsRef.current)
          reconnectAttemptsRef.current++
          console.log(`[useLogStream] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current})`)
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = (error) => {
        console.error('[useLogStream] WebSocket error:', error)
        setIsConnecting(false)
      }

      wsRef.current = ws
    } catch (error) {
      console.error('[useLogStream] Failed to connect:', error)
      setIsConnecting(false)
    }
  }, [projectId, enabled, isConnecting, onFixStarted, onFixCompleted, onFixFailed, onProjectRestarted])

  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    setIsConnected(false)
    setIsConnecting(false)
    reconnectAttemptsRef.current = 0
  }, [])

  // Send log entry to backend
  const sendLog = useCallback((entry: LogEntry) => {
    console.log('[useLogStream] 📤 Sending log entry:', {
      source: entry.source,
      type: entry.type,
      wsState: wsRef.current?.readyState,
      isOpen: wsRef.current?.readyState === WebSocket.OPEN
    })

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(entry))
      console.log('[useLogStream] ✅ Sent via WebSocket')
    } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      // Queue message for when connection is ready
      messageQueueRef.current.push(entry)
      console.log('[useLogStream] ⏳ Queued (WS connecting), queue size:', messageQueueRef.current.length)
    } else {
      // Fallback: Use REST API if WebSocket not available
      console.log('[useLogStream] 🔄 Falling back to REST API')
      sendLogViaRest(projectId!, entry)
    }
  }, [projectId])

  // Forward browser error to backend
  const forwardBrowserError = useCallback((
    message: string,
    file?: string,
    line?: number,
    column?: number,
    stack?: string
  ) => {
    console.log('[useLogStream] 🔴 BROWSER ERROR DETECTED:', {
      projectId,
      message: message?.substring(0, 150),
      file,
      line,
      column,
      hasStack: !!stack
    })

    if (!projectId) {
      console.warn('[useLogStream] ⚠️ No projectId - cannot forward browser error!')
      return
    }

    const entry: LogEntry = {
      source: 'browser',
      type: 'runtime_error',
      data: {
        message,
        file,
        line,
        column,
        stack
      },
      timestamp: Date.now()
    }

    sendLog(entry)
    console.log('[useLogStream] ✅ Forwarded browser error to backend for auto-fix')
  }, [projectId, sendLog])

  // Forward build error to backend
  const forwardBuildError = useCallback((message: string, file?: string) => {
    if (!projectId) return

    const entry: LogEntry = {
      source: 'build',
      type: 'stderr',
      data: {
        message,
        file
      },
      timestamp: Date.now()
    }

    sendLog(entry)
    console.log('[useLogStream] Forwarded build error:', message.substring(0, 100))
  }, [projectId, sendLog])

  // Forward network error to backend
  const forwardNetworkError = useCallback((
    message: string,
    url: string,
    status?: number,
    method?: string
  ) => {
    if (!projectId) return

    const entry: LogEntry = {
      source: 'network',
      type: 'fetch_error',
      data: {
        message,
        url,
        status,
        method
      },
      timestamp: Date.now()
    }

    sendLog(entry)
    console.log('[useLogStream] Forwarded network error:', message)
  }, [projectId, sendLog])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    if (projectId && enabled) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [projectId, enabled, connect, disconnect])

  return {
    isConnected,
    isConnecting,
    forwardBrowserError,
    forwardBuildError,
    forwardNetworkError,
    connect,
    disconnect
  }
}

// Fallback: Send log via REST API if WebSocket is not available
async function sendLogViaRest(projectId: string, entry: LogEntry) {
  try {
    await apiClient.post(`/log-stream/forward/${projectId}`, entry)
  } catch (error) {
    console.warn('[useLogStream] Failed to forward log via REST:', error)
  }
}

export default useLogStream
