/**
 * useConnectionHealth - Monitor backend connection health
 *
 * Features:
 * - Periodic health checks
 * - Connection status tracking
 * - Auto-reconnect on connection loss
 * - Latency monitoring
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api-client'

export interface ConnectionStatus {
  isOnline: boolean
  isBackendAvailable: boolean
  lastCheck: Date | null
  latency: number | null
  consecutiveFailures: number
  status: 'connected' | 'disconnected' | 'checking' | 'reconnecting'
}

interface UseConnectionHealthOptions {
  // Check interval in milliseconds (default: 30 seconds)
  checkInterval?: number
  // Enable automatic health checks (default: true)
  autoCheck?: boolean
  // Callback when connection is lost
  onDisconnect?: () => void
  // Callback when connection is restored
  onReconnect?: () => void
  // Number of consecutive failures before marking as disconnected (default: 2)
  failureThreshold?: number
}

export function useConnectionHealth(options: UseConnectionHealthOptions = {}) {
  const {
    checkInterval = 30000,
    autoCheck = true,
    onDisconnect,
    onReconnect,
    failureThreshold = 2
  } = options

  const [status, setStatus] = useState<ConnectionStatus>({
    isOnline: typeof navigator !== 'undefined' ? navigator.onLine : true,
    isBackendAvailable: true,
    lastCheck: null,
    latency: null,
    consecutiveFailures: 0,
    status: 'connected'
  })

  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const wasConnectedRef = useRef(true)

  // Check backend health
  const checkHealth = useCallback(async () => {
    setStatus(prev => ({ ...prev, status: 'checking' }))

    const startTime = Date.now()

    try {
      const isHealthy = await apiClient.healthCheck()
      const latency = Date.now() - startTime

      if (isHealthy) {
        const wasDisconnected = !wasConnectedRef.current

        setStatus({
          isOnline: navigator.onLine,
          isBackendAvailable: true,
          lastCheck: new Date(),
          latency,
          consecutiveFailures: 0,
          status: 'connected'
        })

        wasConnectedRef.current = true

        // Trigger reconnect callback if we were disconnected
        if (wasDisconnected) {
          onReconnect?.()
        }
      } else {
        handleFailure()
      }
    } catch {
      handleFailure()
    }
  }, [onReconnect])

  const handleFailure = useCallback(() => {
    setStatus(prev => {
      const newFailures = prev.consecutiveFailures + 1
      const isDisconnected = newFailures >= failureThreshold

      if (isDisconnected && wasConnectedRef.current) {
        wasConnectedRef.current = false
        onDisconnect?.()
      }

      return {
        ...prev,
        isBackendAvailable: !isDisconnected,
        lastCheck: new Date(),
        latency: null,
        consecutiveFailures: newFailures,
        status: isDisconnected ? 'disconnected' : 'reconnecting'
      }
    })
  }, [failureThreshold, onDisconnect])

  // Handle browser online/offline events
  const handleOnline = useCallback(() => {
    setStatus(prev => ({ ...prev, isOnline: true }))
    // Immediately check backend when coming online
    checkHealth()
  }, [checkHealth])

  const handleOffline = useCallback(() => {
    setStatus(prev => ({
      ...prev,
      isOnline: false,
      status: 'disconnected'
    }))

    if (wasConnectedRef.current) {
      wasConnectedRef.current = false
      onDisconnect?.()
    }
  }, [onDisconnect])

  // Force a health check
  const forceCheck = useCallback(() => {
    return checkHealth()
  }, [checkHealth])

  // Start periodic health checks
  const startHealthChecks = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }

    intervalRef.current = setInterval(() => {
      checkHealth()
    }, checkInterval)

    // Do an immediate check
    checkHealth()
  }, [checkHealth, checkInterval])

  // Stop periodic health checks
  const stopHealthChecks = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Setup event listeners and auto-check
  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', handleOnline)
      window.addEventListener('offline', handleOffline)

      if (autoCheck) {
        startHealthChecks()
      }

      return () => {
        window.removeEventListener('online', handleOnline)
        window.removeEventListener('offline', handleOffline)
        stopHealthChecks()
      }
    }
  }, [handleOnline, handleOffline, autoCheck, startHealthChecks, stopHealthChecks])

  return {
    // Status
    ...status,
    isConnected: status.isOnline && status.isBackendAvailable,

    // Actions
    checkHealth: forceCheck,
    startHealthChecks,
    stopHealthChecks
  }
}

export type { UseConnectionHealthOptions }
