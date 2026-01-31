import { useEffect, useRef, useState, useCallback } from 'react'
import { useAdminStore } from '@/store/adminStore'

interface WebSocketMessage {
  type: string
  data: any
  timestamp?: string
}

interface StatsUpdate {
  total_users: number
  active_users: number
  total_projects: number
  active_subscriptions: number
  today_revenue: number
  timestamp: string
}

interface ActivityItem {
  id: string
  action: string
  target_type: string
  target_id: string | null
  admin_email: string
  admin_name: string | null
  details: any
  created_at: string
}

interface Notification {
  title: string
  message: string
  level: 'info' | 'success' | 'warning' | 'error'
}

interface UseAdminWebSocketOptions {
  onStatsUpdate?: (stats: StatsUpdate) => void
  onActivityUpdate?: (activities: ActivityItem[]) => void
  onNotification?: (notification: Notification) => void
  autoReconnect?: boolean
  reconnectInterval?: number
}

export function useAdminWebSocket(options: UseAdminWebSocketOptions = {}) {
  const {
    onStatsUpdate,
    onActivityUpdate,
    onNotification,
    autoReconnect = true,
    reconnectInterval = 5000,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastStats, setLastStats] = useState<StatsUpdate | null>(null)
  const [activities, setActivities] = useState<ActivityItem[]>([])
  const [notifications, setNotifications] = useState<Notification[]>([])

  const { setLiveStats, addActivity, addNotification } = useAdminStore()

  const connect = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.warn('No auth token available for WebSocket connection')
      return
    }

    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, '') || window.location.host
    const wsUrl = `${protocol}//${host}/api/v1/admin/ws?token=${token}`

    try {
      wsRef.current = new WebSocket(wsUrl)

      wsRef.current.onopen = () => {
        console.log('Admin WebSocket connected')
        setIsConnected(true)

        // Clear any pending reconnect
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }
      }

      wsRef.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err)
        }
      }

      wsRef.current.onclose = (event) => {
        console.log('Admin WebSocket disconnected:', event.code, event.reason)
        setIsConnected(false)
        wsRef.current = null

        // Attempt reconnection if enabled
        if (autoReconnect && event.code !== 4001 && event.code !== 4003) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting WebSocket reconnection...')
            connect()
          }, reconnectInterval)
        }
      }

      wsRef.current.onerror = (error) => {
        console.error('Admin WebSocket error:', error)
      }
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err)
    }
  }, [autoReconnect, reconnectInterval])

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'stats_update':
        const stats = message.data as StatsUpdate
        setLastStats(stats)
        setLiveStats(stats)
        onStatsUpdate?.(stats)
        break

      case 'activity_update':
        const activityList = message.data as ActivityItem[]
        setActivities(activityList)
        activityList.forEach(activity => addActivity(activity))
        onActivityUpdate?.(activityList)
        break

      case 'notification':
        const notification = message.data as Notification
        setNotifications(prev => [notification, ...prev].slice(0, 50))
        addNotification(notification)
        onNotification?.(notification)
        break

      case 'pong':
        // Heartbeat response
        break

      default:
        console.log('Unknown WebSocket message type:', message.type)
    }
  }, [onStatsUpdate, onActivityUpdate, onNotification, setLiveStats, addActivity, addNotification])

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
  }, [])

  const sendMessage = useCallback((message: object) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  const requestStats = useCallback(() => {
    sendMessage({ type: 'request_stats' })
  }, [sendMessage])

  const requestActivity = useCallback(() => {
    sendMessage({ type: 'request_activity' })
  }, [sendMessage])

  const ping = useCallback(() => {
    sendMessage({ type: 'ping' })
  }, [sendMessage])

  // Connect on mount
  useEffect(() => {
    connect()

    // Cleanup on unmount
    return () => {
      disconnect()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Periodic ping to keep connection alive
  useEffect(() => {
    if (!isConnected) return

    const pingInterval = setInterval(() => {
      ping()
    }, 25000) // Ping every 25 seconds

    return () => clearInterval(pingInterval)
  }, [isConnected, ping])

  return {
    isConnected,
    lastStats,
    activities,
    notifications,
    connect,
    disconnect,
    requestStats,
    requestActivity,
    clearNotifications: () => setNotifications([]),
  }
}

export default useAdminWebSocket
