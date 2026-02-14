'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import useSWR, { mutate } from 'swr'
import { apiClient } from '@/lib/api-client'
import type {
  Team,
  TeamMember,
  TeamTask,
  TeamInvitation,
  TaskComment,
  TeamActivity,
  TeamChatMessage,
  CodeReview,
  TaskTimeLog,
  TeamMilestone,
  TeamNotification,
  TeamAnalytics,
  TeamPresenceInfo,
  TeamWebSocketMessage,
  FileLock,
  CreateTeamRequest,
  UpdateTeamRequest,
  InviteMemberRequest,
  CreateTaskRequest,
  UpdateTaskRequest,
  TaskSplitRequest,
  TaskSplitResponse,
  ApplyTaskSplitRequest,
  CreateCommentRequest,
  CreateMilestoneRequest,
  UpdateMilestoneRequest,
  SendChatMessageRequest,
  CreateCodeReviewRequest,
  SubmitReviewRequest,
  AddSkillRequest,
  TaskStatus,
} from '@/types/team'

const API_BASE = '/teams'

// SWR fetcher
const fetcher = async (url: string) => {
  const data = await apiClient.get(url)
  return data
}

// ============ Team Hooks ============

/**
 * Hook to get team for a project
 */
export function useTeamForProject(projectId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Team>(
    projectId ? `${API_BASE}/project/${projectId}` : null,
    fetcher,
    { revalidateOnFocus: false }
  )

  return {
    team: data,
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team by ID
 */
export function useTeam(teamId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<Team>(
    teamId ? `${API_BASE}/${teamId}` : null,
    fetcher,
    { revalidateOnFocus: false }
  )

  return {
    team: data,
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team members
 */
export function useTeamMembers(teamId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TeamMember[]>(
    teamId ? `${API_BASE}/${teamId}/members` : null,
    fetcher
  )

  return {
    members: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team tasks with optional filters
 */
export function useTeamTasks(
  teamId: string | null,
  filters?: {
    status?: TaskStatus
    assignee_id?: string
    milestone_id?: string
  }
) {
  const params = new URLSearchParams()
  if (filters?.status) params.set('status', filters.status)
  if (filters?.assignee_id) params.set('assignee_id', filters.assignee_id)
  if (filters?.milestone_id) params.set('milestone_id', filters.milestone_id)

  const queryString = params.toString()
  const url = teamId
    ? `${API_BASE}/${teamId}/tasks${queryString ? `?${queryString}` : ''}`
    : null

  const { data, error, isLoading, mutate } = useSWR<TeamTask[]>(url, fetcher)

  return {
    tasks: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get pending invitations for current user
 */
export function useMyInvitations() {
  const { data, error, isLoading, mutate } = useSWR<TeamInvitation[]>(
    `${API_BASE}/invitations/my`,
    fetcher
  )

  return {
    invitations: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team chat messages
 */
export function useTeamChat(
  teamId: string | null,
  options?: { limit?: number; before?: string }
) {
  const params = new URLSearchParams()
  if (options?.limit) params.set('limit', String(options.limit))
  if (options?.before) params.set('before', options.before)

  const queryString = params.toString()
  const url = teamId
    ? `${API_BASE}/${teamId}/chat${queryString ? `?${queryString}` : ''}`
    : null

  const { data, error, isLoading, mutate } = useSWR<TeamChatMessage[]>(
    url,
    fetcher
  )

  return {
    messages: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team activity feed
 */
export function useTeamActivities(
  teamId: string | null,
  options?: { limit?: number; activity_type?: string }
) {
  const params = new URLSearchParams()
  if (options?.limit) params.set('limit', String(options.limit))
  if (options?.activity_type) params.set('activity_type', options.activity_type)

  const queryString = params.toString()
  const url = teamId
    ? `${API_BASE}/${teamId}/activities${queryString ? `?${queryString}` : ''}`
    : null

  const { data, error, isLoading, mutate } = useSWR<TeamActivity[]>(
    url,
    fetcher
  )

  return {
    activities: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team milestones
 */
export function useTeamMilestones(teamId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TeamMilestone[]>(
    teamId ? `${API_BASE}/${teamId}/milestones` : null,
    fetcher
  )

  return {
    milestones: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team notifications for current user
 */
export function useTeamNotifications(
  teamId: string | null,
  options?: { unread_only?: boolean }
) {
  const params = new URLSearchParams()
  if (options?.unread_only) params.set('unread_only', 'true')

  const queryString = params.toString()
  const url = teamId
    ? `${API_BASE}/${teamId}/notifications${queryString ? `?${queryString}` : ''}`
    : null

  const { data, error, isLoading, mutate } = useSWR<TeamNotification[]>(
    url,
    fetcher
  )

  return {
    notifications: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get team analytics
 */
export function useTeamAnalytics(teamId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TeamAnalytics>(
    teamId ? `${API_BASE}/${teamId}/analytics` : null,
    fetcher,
    { revalidateOnFocus: false, revalidateOnReconnect: false }
  )

  return {
    analytics: data,
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get task comments
 */
export function useTaskComments(teamId: string | null, taskId: string | null) {
  const { data, error, isLoading, mutate } = useSWR<TaskComment[]>(
    teamId && taskId ? `${API_BASE}/${teamId}/tasks/${taskId}/comments` : null,
    fetcher
  )

  return {
    comments: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

/**
 * Hook to get code reviews
 */
export function useCodeReviews(
  teamId: string | null,
  options?: { status?: string; my_reviews?: boolean }
) {
  const params = new URLSearchParams()
  if (options?.status) params.set('status', options.status)
  if (options?.my_reviews) params.set('my_reviews', 'true')

  const queryString = params.toString()
  const url = teamId
    ? `${API_BASE}/${teamId}/reviews${queryString ? `?${queryString}` : ''}`
    : null

  const { data, error, isLoading, mutate } = useSWR<CodeReview[]>(url, fetcher)

  return {
    reviews: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

// ============ Team Actions Hook ============

/**
 * Hook providing all team mutation actions
 */
export function useTeamActions() {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleError = (err: any) => {
    const message = err.response?.data?.detail || err.message || 'An error occurred'
    setError(message)
    throw new Error(message)
  }

  // Team CRUD
  const createTeam = useCallback(async (data: CreateTeamRequest): Promise<Team> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<Team>(API_BASE, data)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateTeam = useCallback(async (teamId: string, data: UpdateTeamRequest): Promise<Team> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.put<Team>(`${API_BASE}/${teamId}`, data)
      mutate(`${API_BASE}/${teamId}`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Invitations
  const inviteMember = useCallback(async (teamId: string, data: InviteMemberRequest): Promise<TeamInvitation> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TeamInvitation>(`${API_BASE}/${teamId}/invite`, data)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const acceptInvitation = useCallback(async (token: string): Promise<TeamMember> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TeamMember>(`${API_BASE}/invitations/accept`, { token })
      mutate(`${API_BASE}/invitations/my`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const declineInvitation = useCallback(async (token: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.post(`${API_BASE}/invitations/decline`, { token })
      mutate(`${API_BASE}/invitations/my`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const removeMember = useCallback(async (teamId: string, memberId: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.delete(`${API_BASE}/${teamId}/members/${memberId}`)
      mutate(`${API_BASE}/${teamId}/members`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const leaveTeam = useCallback(async (teamId: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.post(`${API_BASE}/${teamId}/leave`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Tasks
  const createTask = useCallback(async (teamId: string, data: CreateTaskRequest): Promise<TeamTask> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TeamTask>(`${API_BASE}/${teamId}/tasks`, data)
      mutate(`${API_BASE}/${teamId}/tasks`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateTask = useCallback(async (teamId: string, taskId: string, data: UpdateTaskRequest): Promise<TeamTask> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.put<TeamTask>(`${API_BASE}/${teamId}/tasks/${taskId}`, data)
      mutate(`${API_BASE}/${teamId}/tasks`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const deleteTask = useCallback(async (teamId: string, taskId: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.delete(`${API_BASE}/${teamId}/tasks/${taskId}`)
      mutate(`${API_BASE}/${teamId}/tasks`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // AI Task Split
  const splitTasks = useCallback(async (teamId: string, data?: TaskSplitRequest): Promise<TaskSplitResponse> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TaskSplitResponse>(`${API_BASE}/${teamId}/tasks/split`, data || {})
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const applyTaskSplit = useCallback(async (teamId: string, data: ApplyTaskSplitRequest): Promise<TeamTask[]> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TeamTask[]>(`${API_BASE}/${teamId}/tasks/apply-split`, data)
      mutate(`${API_BASE}/${teamId}/tasks`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Comments
  const addComment = useCallback(async (teamId: string, taskId: string, data: CreateCommentRequest): Promise<TaskComment> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TaskComment>(`${API_BASE}/${teamId}/tasks/${taskId}/comments`, data)
      mutate(`${API_BASE}/${teamId}/tasks/${taskId}/comments`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Chat
  const sendChatMessage = useCallback(async (teamId: string, data: SendChatMessageRequest): Promise<TeamChatMessage> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TeamChatMessage>(`${API_BASE}/${teamId}/chat`, data)
      mutate(`${API_BASE}/${teamId}/chat`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Milestones
  const createMilestone = useCallback(async (teamId: string, data: CreateMilestoneRequest): Promise<TeamMilestone> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TeamMilestone>(`${API_BASE}/${teamId}/milestones`, data)
      mutate(`${API_BASE}/${teamId}/milestones`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateMilestone = useCallback(async (teamId: string, milestoneId: string, data: UpdateMilestoneRequest): Promise<TeamMilestone> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.put<TeamMilestone>(`${API_BASE}/${teamId}/milestones/${milestoneId}`, data)
      mutate(`${API_BASE}/${teamId}/milestones`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Code Reviews
  const createCodeReview = useCallback(async (teamId: string, data: CreateCodeReviewRequest): Promise<CodeReview> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<CodeReview>(`${API_BASE}/${teamId}/reviews`, data)
      mutate(`${API_BASE}/${teamId}/reviews`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const submitReview = useCallback(async (teamId: string, reviewId: string, data: SubmitReviewRequest): Promise<CodeReview> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<CodeReview>(`${API_BASE}/${teamId}/reviews/${reviewId}/submit`, data)
      mutate(`${API_BASE}/${teamId}/reviews`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Time Tracking
  const startTimeLog = useCallback(async (teamId: string, taskId: string, description?: string): Promise<TaskTimeLog> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TaskTimeLog>(`${API_BASE}/${teamId}/tasks/${taskId}/time/start`, { description })
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const stopTimeLog = useCallback(async (teamId: string, taskId: string, timeLogId: string): Promise<TaskTimeLog> => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await apiClient.post<TaskTimeLog>(`${API_BASE}/${teamId}/tasks/${taskId}/time/${timeLogId}/stop`)
      return result
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Skills
  const addSkill = useCallback(async (teamId: string, memberId: string, data: AddSkillRequest): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.post(`${API_BASE}/${teamId}/members/${memberId}/skills`, data)
      mutate(`${API_BASE}/${teamId}/members`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Notifications
  const markNotificationRead = useCallback(async (teamId: string, notificationId: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.post(`${API_BASE}/${teamId}/notifications/${notificationId}/read`)
      mutate(`${API_BASE}/${teamId}/notifications`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const markAllNotificationsRead = useCallback(async (teamId: string): Promise<void> => {
    setIsLoading(true)
    setError(null)
    try {
      await apiClient.post(`${API_BASE}/${teamId}/notifications/read-all`)
      mutate(`${API_BASE}/${teamId}/notifications`)
    } catch (err) {
      handleError(err)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  return {
    isLoading,
    error,
    // Team
    createTeam,
    updateTeam,
    // Members
    inviteMember,
    acceptInvitation,
    declineInvitation,
    removeMember,
    leaveTeam,
    // Tasks
    createTask,
    updateTask,
    deleteTask,
    splitTasks,
    applyTaskSplit,
    // Comments
    addComment,
    // Chat
    sendChatMessage,
    // Milestones
    createMilestone,
    updateMilestone,
    // Code Reviews
    createCodeReview,
    submitReview,
    // Time Tracking
    startTimeLog,
    stopTimeLog,
    // Skills
    addSkill,
    // Notifications
    markNotificationRead,
    markAllNotificationsRead,
  }
}

// ============ WebSocket Hook ============

interface UseTeamWebSocketOptions {
  onPresenceUpdate?: (presence: TeamPresenceInfo[]) => void
  onMessage?: (message: TeamWebSocketMessage) => void
  onFileLock?: (lock: FileLock) => void
  onFileUnlock?: (filePath: string) => void
}

/**
 * Hook for team real-time collaboration via WebSocket
 */
export function useTeamWebSocket(
  teamId: string | null,
  options: UseTeamWebSocketOptions = {}
) {
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [presence, setPresence] = useState<TeamPresenceInfo[]>([])
  const [fileLocks, setFileLocks] = useState<FileLock[]>([])
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const connect = useCallback(() => {
    if (!teamId || wsRef.current?.readyState === WebSocket.OPEN) return

    const token = localStorage.getItem('access_token')
    if (!token) return

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/v1/teams/ws/${teamId}?token=${token}`

    try {
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('[TeamWS] Connected to team:', teamId)
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const message: TeamWebSocketMessage = JSON.parse(event.data)

          switch (message.type) {
            case 'presence_update':
              const presenceList = message.payload.members || []
              setPresence(presenceList)
              options.onPresenceUpdate?.(presenceList)
              break

            case 'file_locked':
              const lock = message.payload as FileLock
              setFileLocks((prev) => [...prev.filter((l) => l.file_path !== lock.file_path), lock])
              options.onFileLock?.(lock)
              break

            case 'file_unlocked':
              const unlockedPath = message.payload.file_path
              setFileLocks((prev) => prev.filter((l) => l.file_path !== unlockedPath))
              options.onFileUnlock?.(unlockedPath)
              break

            case 'chat_message':
              // Trigger SWR revalidation for chat
              mutate(`${API_BASE}/${teamId}/chat`)
              options.onMessage?.(message)
              break

            case 'task_updated':
              // Trigger SWR revalidation for tasks
              mutate(`${API_BASE}/${teamId}/tasks`)
              options.onMessage?.(message)
              break

            default:
              options.onMessage?.(message)
          }
        } catch (err) {
          console.error('[TeamWS] Failed to parse message:', err)
        }
      }

      ws.onclose = () => {
        console.log('[TeamWS] Disconnected from team:', teamId)
        setIsConnected(false)
        wsRef.current = null

        // Auto-reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 3000)
      }

      ws.onerror = (error) => {
        console.error('[TeamWS] Error:', error)
      }
    } catch (err) {
      console.error('[TeamWS] Failed to connect:', err)
    }
  }, [teamId, options])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
    setPresence([])
    setFileLocks([])
  }, [])

  const send = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }))
    }
  }, [])

  const lockFile = useCallback((filePath: string) => {
    send('lock_file', { file_path: filePath })
  }, [send])

  const unlockFile = useCallback((filePath: string) => {
    send('unlock_file', { file_path: filePath })
  }, [send])

  const updateCursor = useCallback((filePath: string, line: number, column: number) => {
    send('cursor_update', { file_path: filePath, line, column })
  }, [send])

  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    send('typing', { is_typing: isTyping })
  }, [send])

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect()
    return () => disconnect()
  }, [connect, disconnect])

  return {
    isConnected,
    presence,
    fileLocks,
    connect,
    disconnect,
    send,
    lockFile,
    unlockFile,
    updateCursor,
    sendTypingIndicator,
  }
}
