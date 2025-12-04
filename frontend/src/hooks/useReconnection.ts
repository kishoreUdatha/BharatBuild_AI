/**
 * useReconnection - Handle network disconnection and resume
 *
 * Features:
 * - Detect connection loss
 * - Auto-reconnect with exponential backoff
 * - Resume interrupted workflows
 * - Heartbeat to keep connection alive
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiConfig, reconnectionConfig, getReconnectionDelay, getHealthUrl } from '@/config'

const API_BASE = apiConfig.baseUrl

interface ReconnectionState {
  isOnline: boolean
  isReconnecting: boolean
  reconnectAttempt: number
  lastDisconnect: Date | null
  canResume: boolean
  resumeInfo: ResumeInfo | null
}

interface ResumeInfo {
  project_id: string
  next_step: string
  completed_steps: string[]
  remaining_files: Array<{ path: string; type: string }>
  generated_files_count: number
  retry_count: number
}

interface CheckpointStatus {
  status: string
  current_step: string | null
  completed_steps: string[]
  generated_files_count: number
  pending_files_count: number
  error_message: string | null
  retry_count: number
  max_retries: number
}

interface UseReconnectionOptions {
  projectId?: string
  onReconnect?: () => void
  onDisconnect?: () => void
  onResumeAvailable?: (info: ResumeInfo) => void
  maxRetries?: number
  baseDelay?: number
  heartbeatInterval?: number
}

export function useReconnection(options: UseReconnectionOptions = {}) {
  const {
    projectId,
    onReconnect,
    onDisconnect,
    onResumeAvailable,
    maxRetries = reconnectionConfig.maxRetries,
    baseDelay = reconnectionConfig.baseDelay,
    heartbeatInterval = reconnectionConfig.heartbeatInterval
  } = options

  const [state, setState] = useState<ReconnectionState>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isReconnecting: false,
    reconnectAttempt: 0,
    lastDisconnect: null,
    canResume: false,
    resumeInfo: null
  })

  const heartbeatRef = useRef<NodeJS.Timeout | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const checkedProjectsRef = useRef<Set<string>>(new Set())

  // Get auth token
  const getAuthToken = useCallback(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token') || ''
    }
    return ''
  }, [])

  // Check if project can be resumed
  const checkResumeStatus = useCallback(async (pid: string): Promise<{
    canResume: boolean
    checkpoint: CheckpointStatus | null
    resumeInfo: ResumeInfo | null
  }> => {
    // Skip if no auth token available
    const token = getAuthToken()
    if (!token) {
      return { canResume: false, checkpoint: null, resumeInfo: null }
    }

    try {
      const response = await fetch(`${API_BASE}/resume/status/${pid}`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`
        }
      })

      if (!response.ok) {
        // Log auth errors - don't retry these
        if (response.status === 401 || response.status === 403) {
          console.warn(`Auth error ${response.status} checking resume status - not retrying`)
        }
        return { canResume: false, checkpoint: null, resumeInfo: null }
      }

      const data = await response.json()
      return {
        canResume: data.can_resume,
        checkpoint: data.checkpoint,
        resumeInfo: data.resume_info
      }
    } catch (error) {
      console.error('Failed to check resume status:', error)
      return { canResume: false, checkpoint: null, resumeInfo: null }
    }
  }, [getAuthToken])

  // Resume project generation
  const resumeProject = useCallback(async (pid: string): Promise<ReadableStream | null> => {
    try {
      abortControllerRef.current = new AbortController()

      const response = await fetch(`${API_BASE}/resume/${pid}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`,
          'Content-Type': 'application/json'
        },
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) {
        throw new Error(`Resume failed: ${response.status}`)
      }

      return response.body
    } catch (error) {
      console.error('Failed to resume project:', error)
      return null
    }
  }, [getAuthToken])

  // Send heartbeat
  const sendHeartbeat = useCallback(async (pid: string) => {
    try {
      await fetch(`${API_BASE}/resume/heartbeat/${pid}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`
        }
      })
    } catch (error) {
      // Heartbeat failed - connection might be lost
      console.warn('Heartbeat failed:', error)
    }
  }, [getAuthToken])

  // Start heartbeat
  const startHeartbeat = useCallback((pid: string) => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
    }

    heartbeatRef.current = setInterval(() => {
      sendHeartbeat(pid)
    }, heartbeatInterval)
  }, [heartbeatInterval, sendHeartbeat])

  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current)
      heartbeatRef.current = null
    }
  }, [])

  // Exponential backoff delay
  const getBackoffDelay = useCallback((attempt: number) => {
    return getReconnectionDelay(attempt)
  }, [])

  // Attempt reconnection
  const attemptReconnect = useCallback(async () => {
    if (state.reconnectAttempt >= maxRetries) {
      setState(prev => ({ ...prev, isReconnecting: false }))
      return false
    }

    setState(prev => ({
      ...prev,
      isReconnecting: true,
      reconnectAttempt: prev.reconnectAttempt + 1
    }))

    try {
      // Try to reach the backend
      const response = await fetch(getHealthUrl(), {
        method: 'GET',
        signal: AbortSignal.timeout(reconnectionConfig.healthCheckTimeout)
      })

      if (response.ok) {
        setState(prev => ({
          ...prev,
          isOnline: true,
          isReconnecting: false,
          reconnectAttempt: 0
        }))

        // Check if we can resume
        if (projectId) {
          const { canResume, resumeInfo } = await checkResumeStatus(projectId)
          setState(prev => ({ ...prev, canResume, resumeInfo }))

          if (canResume && resumeInfo && onResumeAvailable) {
            onResumeAvailable(resumeInfo)
          }
        }

        onReconnect?.()
        return true
      }
    } catch (error) {
      console.warn(`Reconnect attempt ${state.reconnectAttempt + 1} failed:`, error)
    }

    // Schedule next attempt
    const delay = getBackoffDelay(state.reconnectAttempt)
    reconnectTimeoutRef.current = setTimeout(() => {
      attemptReconnect()
    }, delay)

    return false
  }, [state.reconnectAttempt, maxRetries, projectId, checkResumeStatus, onReconnect, onResumeAvailable, getBackoffDelay])

  // Handle online event
  const handleOnline = useCallback(() => {
    console.log('Network online detected')
    setState(prev => ({ ...prev, isOnline: true }))
    attemptReconnect()
  }, [attemptReconnect])

  // Handle offline event
  const handleOffline = useCallback(() => {
    console.log('Network offline detected')
    setState(prev => ({
      ...prev,
      isOnline: false,
      lastDisconnect: new Date()
    }))
    stopHeartbeat()
    onDisconnect?.()
  }, [stopHeartbeat, onDisconnect])

  // Cancel ongoing operations
  const cancelOperations = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    stopHeartbeat()
  }, [stopHeartbeat])

  // List resumable projects
  const listResumableProjects = useCallback(async (): Promise<ResumeInfo[]> => {
    try {
      const response = await fetch(`${API_BASE}/resume/list`, {
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`
        }
      })

      if (!response.ok) {
        return []
      }

      const data = await response.json()
      return data.resumable_projects || []
    } catch (error) {
      console.error('Failed to list resumable projects:', error)
      return []
    }
  }, [getAuthToken])

  // Cancel checkpoint
  const cancelCheckpoint = useCallback(async (pid: string): Promise<boolean> => {
    try {
      const response = await fetch(`${API_BASE}/resume/${pid}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${getAuthToken()}`
        }
      })

      return response.ok
    } catch (error) {
      console.error('Failed to cancel checkpoint:', error)
      return false
    }
  }, [getAuthToken])

  // Setup event listeners
  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', handleOnline)
      window.addEventListener('offline', handleOffline)

      // Check initial status - only once per projectId
      if (projectId && !checkedProjectsRef.current.has(projectId)) {
        checkedProjectsRef.current.add(projectId)
        checkResumeStatus(projectId).then(({ canResume, resumeInfo }) => {
          setState(prev => ({ ...prev, canResume, resumeInfo }))
        })
      }

      return () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
        cancelOperations()
      }
    }
  }, [projectId, handleOnline, handleOffline, checkResumeStatus, cancelOperations])

  return {
    // State
    isOnline: state.isOnline,
    isReconnecting: state.isReconnecting,
    reconnectAttempt: state.reconnectAttempt,
    lastDisconnect: state.lastDisconnect,
    canResume: state.canResume,
    resumeInfo: state.resumeInfo,

    // Actions
    checkResumeStatus,
    resumeProject,
    attemptReconnect,
    startHeartbeat,
    stopHeartbeat,
    cancelOperations,
    listResumableProjects,
    cancelCheckpoint
  }
}

export type { ReconnectionState, ResumeInfo, CheckpointStatus }
