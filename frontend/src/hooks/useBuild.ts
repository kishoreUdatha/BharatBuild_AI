import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import { useBuildStore, BuildPlatform, Build, BuildQuota, BuildHistory } from '@/store/buildStore'

interface BuildConfig {
  app_name?: string
  version?: string
  build_number?: number
  bundle_id?: string
}

interface UseBuildOptions {
  projectId: string
  autoRefreshStatus?: boolean
  pollInterval?: number
}

export function useBuild(options: UseBuildOptions) {
  const {
    projectId,
    autoRefreshStatus = true,
    pollInterval = 5000,
  } = options

  const {
    currentBuild,
    buildHistory,
    isBuilding,
    error,
    quota,
    setCurrentBuild,
    updateCurrentBuild,
    setIsBuilding,
    setError,
    setQuota,
    setBuildHistory,
    clearBuild,
    reset,
  } = useBuildStore()

  const [isLoading, setIsLoading] = useState(false)

  // Fetch quota on mount
  useEffect(() => {
    if (projectId) {
      fetchQuota()
    }
  }, [projectId])

  // Poll for build status when building
  useEffect(() => {
    if (!autoRefreshStatus || !isBuilding || !currentBuild?.id) return

    const interval = setInterval(() => {
      fetchBuildStatus(currentBuild.id)
    }, pollInterval)

    return () => clearInterval(interval)
  }, [autoRefreshStatus, isBuilding, currentBuild?.id, pollInterval])

  const fetchQuota = useCallback(async () => {
    try {
      const data = await apiClient.get<BuildQuota>('/builds/quota')
      setQuota(data)
      return data
    } catch (err) {
      console.error('Failed to fetch build quota:', err)
      return null
    }
  }, [])

  const fetchBuildStatus = useCallback(async (buildId?: string) => {
    if (!projectId) return null

    try {
      const url = buildId
        ? `/builds/${projectId}/status?build_id=${buildId}`
        : `/builds/${projectId}/status`
      const data = await apiClient.get<Build>(url)

      if (currentBuild?.id === data.id || !buildId) {
        updateCurrentBuild(data)

        // Stop polling if build is complete
        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          setIsBuilding(false)
          fetchQuota() // Refresh quota after build completes
        }
      }

      return data
    } catch (err: any) {
      if (err.response?.status !== 404) {
        console.error('Failed to fetch build status:', err)
      }
      return null
    }
  }, [projectId, currentBuild?.id])

  const fetchBuildHistory = useCallback(async (platform?: BuildPlatform, limit = 10) => {
    if (!projectId) return null

    try {
      setIsLoading(true)
      let url = `/builds/${projectId}/history?limit=${limit}`
      if (platform) {
        url += `&platform=${platform}`
      }
      const data = await apiClient.get<BuildHistory>(url)
      setBuildHistory(data)
      return data
    } catch (err) {
      console.error('Failed to fetch build history:', err)
      return null
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  const startBuild = useCallback(async (platform: BuildPlatform, config: BuildConfig) => {
    if (!projectId || isBuilding) return null

    // Check quota
    if (quota && !quota.can_build) {
      setError(`Build limit reached (${quota.builds_limit}/month). Upgrade to premium for more builds.`)
      return null
    }

    try {
      setError(null)
      setIsLoading(true)
      setIsBuilding(true)

      const endpoint = platform === 'android' ? 'apk' : 'ipa'
      const data = await apiClient.post<{ build_id: string; message: string; status: string }>(
        `/builds/${projectId}/${endpoint}`,
        config
      )

      const build: Build = {
        id: data.build_id,
        project_id: projectId,
        platform,
        status: 'pending',
        progress: 0,
        phase: 'Preparing build...',
      }

      setCurrentBuild(build)
      return build
    } catch (err: any) {
      setIsBuilding(false)
      const errorDetail = err.response?.data?.detail
      if (typeof errorDetail === 'object') {
        setError(errorDetail.message || 'Failed to start build')
      } else {
        setError(errorDetail || 'Failed to start build')
      }
      return null
    } finally {
      setIsLoading(false)
    }
  }, [projectId, isBuilding, quota])

  const cancelBuild = useCallback(async (reason?: string) => {
    if (!projectId || !isBuilding) return false

    try {
      await apiClient.delete(`/builds/${projectId}/cancel`, {
        data: reason ? { reason } : undefined,
      })

      setIsBuilding(false)
      if (currentBuild) {
        updateCurrentBuild({ status: 'cancelled' })
      }
      return true
    } catch (err: any) {
      console.error('Failed to cancel build:', err)
      return false
    }
  }, [projectId, isBuilding, currentBuild])

  const getDownloadUrl = useCallback(async (buildId?: string) => {
    if (!projectId) return null

    try {
      const url = buildId
        ? `/builds/${projectId}/download?build_id=${buildId}`
        : `/builds/${projectId}/download`
      const data = await apiClient.get<{
        download_url: string
        filename: string
        size_bytes?: number
        expires_at?: string
      }>(url)
      return data
    } catch (err: any) {
      console.error('Failed to get download URL:', err)
      setError('Failed to get download URL')
      return null
    }
  }, [projectId])

  const downloadBuild = useCallback(async (buildId?: string) => {
    const data = await getDownloadUrl(buildId)
    if (data?.download_url) {
      window.open(data.download_url, '_blank')
      return true
    }
    return false
  }, [getDownloadUrl])

  return {
    // State
    currentBuild,
    buildHistory,
    isBuilding,
    isLoading,
    error,
    quota,

    // Actions
    startBuild,
    cancelBuild,
    fetchBuildStatus,
    fetchBuildHistory,
    fetchQuota,
    getDownloadUrl,
    downloadBuild,
    clearBuild,
    reset,
    setError,
  }
}
