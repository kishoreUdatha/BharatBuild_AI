'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export interface PlanStatus {
  plan: {
    name: string
    type: string
    is_free: boolean
    is_premium: boolean
  }
  projects: {
    created: number
    limit: number | null
    remaining: number | null
    can_create: boolean
  }
  features: {
    project_generation: boolean
    bug_fixing: boolean
    srs_document: boolean
    sds_document: boolean
    project_report: boolean
    ppt_generation: boolean
    viva_questions: boolean
    plagiarism_check: boolean
    code_execution: boolean
    download_files: boolean
  }
  needs_upgrade: boolean
  upgrade_message: string | null
}

export function usePlanStatus() {
  const [status, setStatus] = useState<PlanStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const data = await apiClient.getPlanStatus()
      if (data.success) {
        setStatus(data)
      }
    } catch (err: any) {
      // Don't set error for 401 (not logged in)
      if (err?.response?.status !== 401) {
        setError(err?.message || 'Failed to fetch plan status')
      }
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    // Only fetch if user is logged in
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    if (token) {
      fetchStatus()
    } else {
      setIsLoading(false)
    }
  }, [fetchStatus])

  return {
    status,
    isLoading,
    error,
    refetch: fetchStatus,
    // Convenience getters
    canCreateProject: status?.projects.can_create ?? false,
    projectsRemaining: status?.projects.remaining,
    projectsCreated: status?.projects.created ?? 0,
    projectLimit: status?.projects.limit,
    planName: status?.plan.name ?? 'Free',
    isPremium: status?.plan.is_premium ?? false,
    isFree: status?.plan.is_free ?? true,
    needsUpgrade: status?.needs_upgrade ?? true,
    upgradeMessage: status?.upgrade_message,
    features: status?.features
  }
}
