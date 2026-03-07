'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import apiClient from '@/lib/api-client'

// Types
export interface UserNAACRole {
  id: string
  user_id: string
  role_id: string
  role_type: string
  role_display_name: string
  criterion_number: number | null
  department: string | null
  assigned_by: string | null
  assigned_by_name: string | null
  assigned_at: string
  valid_from: string
  valid_until: string | null
  is_active: boolean
  assignment_notes: string | null
  hierarchy_level: number
  can_access_all_criteria: boolean
  can_access_all_departments: boolean
  allowed_criteria: number[] | null
  can_approve_level: number | null
}

export interface NAACNotification {
  id: string
  notification_type: string
  title: string
  message: string
  related_entity_type: string | null
  related_entity_id: string | null
  action_url: string | null
  is_read: boolean
  read_at: string | null
  is_important: boolean
  created_at: string
}

export interface TaskSummary {
  pending: number
  assigned: number
  in_progress: number
  submitted: number
  completed: number
  overdue: number
}

export interface ApprovalSummary {
  pending_department: number
  pending_criterion: number
  pending_iqac: number
  pending_head: number
  approved: number
  rejected: number
  revision_requested: number
}

interface NAACRoleContextType {
  // Role data
  roles: UserNAACRole[]
  isLoading: boolean
  error: string | null

  // Role checks
  hasRole: (roleType: string) => boolean
  hasAnyRole: (roleTypes: string[]) => boolean
  hasCriterionAccess: (criterion: number) => boolean
  hasDepartmentAccess: (department: string) => boolean
  canApprove: (level: 'department' | 'criterion' | 'iqac' | 'head') => boolean
  highestRole: UserNAACRole | null

  // Accessible scope
  accessibleCriteria: number[]
  accessibleDepartments: string[]
  canAccessAllCriteria: boolean
  canAccessAllDepartments: boolean

  // Dashboard data
  taskSummary: TaskSummary | null
  approvalSummary: ApprovalSummary | null
  notifications: NAACNotification[]
  unreadNotificationCount: number

  // Actions
  refreshRoles: () => Promise<void>
  refreshDashboard: () => Promise<void>
  markNotificationsRead: (ids: string[]) => Promise<void>
  markAllNotificationsRead: () => Promise<void>
}

const NAACRoleContext = createContext<NAACRoleContextType | undefined>(undefined)

const ROLE_HIERARCHY: Record<string, number> = {
  head_of_institution: 1,
  iqac_coordinator: 2,
  criterion_coordinator: 3,
  department_coordinator: 4,
  documentation_team: 5,
  it_data_analytics: 5,
  ssr_drafting_committee: 5,
  administrative_officer: 5,
  alumni_coordinator: 5,
  placement_officer: 5,
  student_representative: 6,
}

const APPROVAL_LEVELS: Record<string, number> = {
  department: 1,
  criterion: 2,
  iqac: 3,
  head: 4,
}

export function NAACRoleProvider({ children }: { children: React.ReactNode }) {
  const [roles, setRoles] = useState<UserNAACRole[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [taskSummary, setTaskSummary] = useState<TaskSummary | null>(null)
  const [approvalSummary, setApprovalSummary] = useState<ApprovalSummary | null>(null)
  const [notifications, setNotifications] = useState<NAACNotification[]>([])
  const [unreadNotificationCount, setUnreadNotificationCount] = useState(0)

  // Fetch user's NAAC roles
  const refreshRoles = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await apiClient.get<UserNAACRole[]>('/naac/rbac/my-roles')
      setRoles(data)
    } catch (err: any) {
      console.error('Failed to fetch NAAC roles:', err)
      setError(err.response?.data?.detail || 'Failed to load roles')
      setRoles([])
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Fetch dashboard data
  const refreshDashboard = useCallback(async () => {
    try {
      const data = await apiClient.get('/naac/rbac/dashboard')
      setTaskSummary(data.task_summary)
      setApprovalSummary(data.approval_summary)
      setNotifications(data.recent_notifications || [])
      setUnreadNotificationCount(data.unread_notifications || 0)
    } catch (err) {
      console.error('Failed to fetch NAAC dashboard:', err)
    }
  }, [])

  // Mark notifications as read
  const markNotificationsRead = useCallback(async (ids: string[]) => {
    try {
      await apiClient.post('/naac/rbac/notifications/mark-read', { notification_ids: ids })
      setNotifications(prev =>
        prev.map(n => ids.includes(n.id) ? { ...n, is_read: true } : n)
      )
      setUnreadNotificationCount(prev => Math.max(0, prev - ids.length))
    } catch (err) {
      console.error('Failed to mark notifications as read:', err)
    }
  }, [])

  const markAllNotificationsRead = useCallback(async () => {
    try {
      await apiClient.post('/naac/rbac/notifications/mark-all-read')
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadNotificationCount(0)
    } catch (err) {
      console.error('Failed to mark all notifications as read:', err)
    }
  }, [])

  // Load roles on mount
  useEffect(() => {
    refreshRoles()
  }, [refreshRoles])

  // Load dashboard when roles are loaded
  useEffect(() => {
    if (roles.length > 0) {
      refreshDashboard()
    }
  }, [roles.length, refreshDashboard])

  // Role check functions
  const hasRole = useCallback((roleType: string): boolean => {
    return roles.some(r => r.role_type === roleType && r.is_active)
  }, [roles])

  const hasAnyRole = useCallback((roleTypes: string[]): boolean => {
    return roles.some(r => roleTypes.includes(r.role_type) && r.is_active)
  }, [roles])

  const hasCriterionAccess = useCallback((criterion: number): boolean => {
    return roles.some(r => {
      if (!r.is_active) return false
      if (r.can_access_all_criteria) return true
      if (r.criterion_number === criterion) return true
      if (r.allowed_criteria && r.allowed_criteria.includes(criterion)) return true
      return false
    })
  }, [roles])

  const hasDepartmentAccess = useCallback((department: string): boolean => {
    return roles.some(r => {
      if (!r.is_active) return false
      if (r.can_access_all_departments) return true
      if (r.department === department) return true
      return false
    })
  }, [roles])

  const canApprove = useCallback((level: 'department' | 'criterion' | 'iqac' | 'head'): boolean => {
    const requiredLevel = APPROVAL_LEVELS[level]
    return roles.some(r =>
      r.is_active && r.can_approve_level && r.can_approve_level >= requiredLevel
    )
  }, [roles])

  // Get highest role
  const highestRole = roles.length > 0
    ? roles.reduce((highest, current) =>
        !highest || current.hierarchy_level < highest.hierarchy_level ? current : highest
      , roles[0])
    : null

  // Calculate accessible scope
  const accessibleCriteria = roles.reduce((acc, r) => {
    if (!r.is_active) return acc
    if (r.can_access_all_criteria) return [1, 2, 3, 4, 5, 6, 7]
    if (r.criterion_number && !acc.includes(r.criterion_number)) {
      acc.push(r.criterion_number)
    }
    if (r.allowed_criteria) {
      r.allowed_criteria.forEach(c => {
        if (!acc.includes(c)) acc.push(c)
      })
    }
    return acc
  }, [] as number[]).sort((a, b) => a - b)

  const accessibleDepartments = roles.reduce((acc, r) => {
    if (!r.is_active) return acc
    if (r.can_access_all_departments) return ['*']
    if (r.department && !acc.includes(r.department)) {
      acc.push(r.department)
    }
    return acc
  }, [] as string[])

  const canAccessAllCriteria = accessibleCriteria.length === 7 ||
    roles.some(r => r.is_active && r.can_access_all_criteria)

  const canAccessAllDepartments = accessibleDepartments.includes('*') ||
    roles.some(r => r.is_active && r.can_access_all_departments)

  const value: NAACRoleContextType = {
    roles,
    isLoading,
    error,
    hasRole,
    hasAnyRole,
    hasCriterionAccess,
    hasDepartmentAccess,
    canApprove,
    highestRole,
    accessibleCriteria,
    accessibleDepartments,
    canAccessAllCriteria,
    canAccessAllDepartments,
    taskSummary,
    approvalSummary,
    notifications,
    unreadNotificationCount,
    refreshRoles,
    refreshDashboard,
    markNotificationsRead,
    markAllNotificationsRead,
  }

  return (
    <NAACRoleContext.Provider value={value}>
      {children}
    </NAACRoleContext.Provider>
  )
}

export function useNAACRole() {
  const context = useContext(NAACRoleContext)
  if (context === undefined) {
    throw new Error('useNAACRole must be used within a NAACRoleProvider')
  }
  return context
}

// Hook for checking specific permissions
export function useNAACPermission(
  criterion?: number,
  department?: string
) {
  const { hasCriterionAccess, hasDepartmentAccess, canAccessAllCriteria, canAccessAllDepartments } = useNAACRole()

  const hasAccess = () => {
    if (criterion && !hasCriterionAccess(criterion)) return false
    if (department && !hasDepartmentAccess(department)) return false
    return true
  }

  return {
    hasAccess: hasAccess(),
    canAccessAllCriteria,
    canAccessAllDepartments,
  }
}

export default NAACRoleContext
