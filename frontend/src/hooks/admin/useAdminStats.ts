'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export interface DashboardStats {
  total_users: number
  active_users: number
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
  total_projects: number
  active_projects: number
  total_revenue: number
  revenue_this_month: number
  total_subscriptions: number
  active_subscriptions: number
  total_tokens_used: number
  tokens_used_today: number
  total_api_calls: number
  api_calls_today: number
}

export interface ActivityItem {
  id: string
  type: string
  title: string
  description: string
  user_email?: string
  user_name?: string
  timestamp: string
  metadata?: Record<string, any>
}

export function useAdminStats() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)
  const [activityLoading, setActivityLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStats = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await apiClient.get<DashboardStats>('/admin/dashboard/stats')
      setStats(data)
    } catch (err: any) {
      console.error('Failed to fetch admin stats:', err)
      setError(err.message || 'Failed to fetch statistics')
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchActivity = useCallback(async (limit: number = 20) => {
    setActivityLoading(true)
    try {
      const data = await apiClient.get<{ items: ActivityItem[]; total: number }>(
        `/admin/dashboard/activity?limit=${limit}`
      )
      setActivity(data.items || [])
    } catch (err: any) {
      console.error('Failed to fetch activity:', err)
    } finally {
      setActivityLoading(false)
    }
  }, [])

  const refresh = useCallback(() => {
    fetchStats()
    fetchActivity()
  }, [fetchStats, fetchActivity])

  useEffect(() => {
    fetchStats()
    fetchActivity()
  }, [fetchStats, fetchActivity])

  return {
    stats,
    activity,
    loading,
    activityLoading,
    error,
    refresh,
    fetchStats,
    fetchActivity,
  }
}
