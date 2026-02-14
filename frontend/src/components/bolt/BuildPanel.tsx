'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Smartphone,
  Apple,
  Download,
  Loader2,
  XCircle,
  CheckCircle2,
  AlertCircle,
  Copy,
  Check,
  RefreshCw,
  Clock,
  Package
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useProject } from '@/hooks/useProject'
import { useBuildStore, BuildStatus, BuildPlatform } from '@/store/buildStore'

interface BuildConfig {
  app_name: string
  version: string
  build_number: number
  bundle_id?: string
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getStatusIcon = (status: BuildStatus) => {
  switch (status) {
    case 'pending':
    case 'configuring':
    case 'queued':
    case 'in_progress':
      return <Loader2 className="w-5 h-5 animate-spin text-blue-400" />
    case 'completed':
      return <CheckCircle2 className="w-5 h-5 text-green-400" />
    case 'failed':
      return <XCircle className="w-5 h-5 text-red-400" />
    case 'cancelled':
      return <AlertCircle className="w-5 h-5 text-yellow-400" />
    default:
      return <Clock className="w-5 h-5 text-gray-400" />
  }
}

const getStatusText = (status: BuildStatus) => {
  switch (status) {
    case 'pending':
      return 'Preparing build...'
    case 'configuring':
      return 'Configuring project...'
    case 'queued':
      return 'Waiting in build queue...'
    case 'in_progress':
      return 'Building native app...'
    case 'completed':
      return 'Build complete!'
    case 'failed':
      return 'Build failed'
    case 'cancelled':
      return 'Build cancelled'
    default:
      return 'Unknown status'
  }
}

export function BuildPanel() {
  const { currentProject } = useProject()
  const {
    currentBuild,
    isBuilding,
    error,
    quota,
    setCurrentBuild,
    setIsBuilding,
    setError,
    setQuota,
    clearBuild
  } = useBuildStore()

  const [config, setConfig] = useState<BuildConfig>({
    app_name: '',
    version: '1.0.0',
    build_number: 1
  })
  const [selectedPlatform, setSelectedPlatform] = useState<BuildPlatform>('android')
  const [copied, setCopied] = useState(false)
  const [pollInterval, setPollInterval] = useState<NodeJS.Timeout | null>(null)

  // Set default app name from project
  useEffect(() => {
    if (currentProject?.name) {
      setConfig(prev => ({
        ...prev,
        app_name: prev.app_name || currentProject.name
      }))
    }
  }, [currentProject?.name])

  // Fetch quota on mount
  useEffect(() => {
    if (currentProject?.id) {
      fetchQuota()
    }
  }, [currentProject?.id])

  // Poll for build status when building
  useEffect(() => {
    if (isBuilding && currentBuild && currentProject?.id) {
      const interval = setInterval(() => {
        fetchBuildStatus()
      }, 5000) // Poll every 5 seconds
      setPollInterval(interval)
      return () => clearInterval(interval)
    } else if (pollInterval) {
      clearInterval(pollInterval)
      setPollInterval(null)
    }
  }, [isBuilding, currentBuild?.id, currentProject?.id])

  const fetchQuota = async () => {
    try {
      const data = await apiClient.get('/builds/quota')
      setQuota(data)
    } catch (err) {
      console.error('Failed to fetch build quota:', err)
    }
  }

  const fetchBuildStatus = async () => {
    if (!currentProject?.id || !currentBuild?.id) return

    try {
      const data = await apiClient.get(`/builds/${currentProject.id}/status?build_id=${currentBuild.id}`)
      setCurrentBuild({
        ...currentBuild,
        status: data.status,
        progress: data.progress,
        phase: data.phase,
        error_message: data.error_message,
        artifact_url: data.artifact_url,
        artifact_filename: data.artifact_filename,
        artifact_size_mb: data.artifact_size_mb
      })

      // Stop polling if build is complete
      if (['completed', 'failed', 'cancelled'].includes(data.status)) {
        setIsBuilding(false)
        fetchQuota() // Refresh quota after build
      }
    } catch (err) {
      console.error('Failed to fetch build status:', err)
    }
  }

  const handleStartBuild = async () => {
    if (!currentProject?.id || isBuilding) return

    // Check quota
    if (quota && !quota.can_build) {
      setError(`Build limit reached (${quota.builds_limit}/month). Upgrade to premium for more builds.`)
      return
    }

    setError(null)
    setIsBuilding(true)

    try {
      const endpoint = selectedPlatform === 'android' ? 'apk' : 'ipa'
      const data = await apiClient.post(`/builds/${currentProject.id}/${endpoint}`, config)

      setCurrentBuild({
        id: data.build_id,
        project_id: currentProject.id,
        platform: selectedPlatform,
        status: 'pending',
        progress: 0,
        phase: 'Preparing build...'
      })
    } catch (err: any) {
      setIsBuilding(false)
      const errorDetail = err.response?.data?.detail
      if (typeof errorDetail === 'object') {
        setError(errorDetail.message || 'Failed to start build')
      } else {
        setError(errorDetail || 'Failed to start build')
      }
    }
  }

  const handleCancelBuild = async () => {
    if (!currentProject?.id || !isBuilding) return

    try {
      await apiClient.delete(`/builds/${currentProject.id}/cancel`)
      setIsBuilding(false)
      if (currentBuild) {
        setCurrentBuild({
          ...currentBuild,
          status: 'cancelled'
        })
      }
    } catch (err: any) {
      console.error('Failed to cancel build:', err)
    }
  }

  const handleDownload = async () => {
    if (!currentProject?.id || !currentBuild?.id) return

    try {
      const data = await apiClient.get(`/builds/${currentProject.id}/download?build_id=${currentBuild.id}`)
      window.open(data.download_url, '_blank')
    } catch (err: any) {
      console.error('Failed to get download URL:', err)
      setError('Failed to download. Please try again.')
    }
  }

  const handleCopyUrl = async () => {
    if (!currentBuild?.artifact_url) return
    try {
      await navigator.clipboard.writeText(currentBuild.artifact_url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  if (!currentProject?.id) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center">
        <Package className="w-12 h-12 text-[hsl(var(--bolt-text-tertiary))] mb-4" />
        <h3 className="text-lg font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
          No Project Selected
        </h3>
        <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
          Select or create a project to build mobile apps
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bolt-bg-primary))] overflow-auto">
      {/* Header */}
      <div className="p-4 border-b border-[hsl(var(--bolt-border))]">
        <h2 className="text-lg font-semibold text-[hsl(var(--bolt-text-primary))] flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-[hsl(var(--bolt-accent))]" />
          Build Mobile App
        </h2>
        <p className="text-sm text-[hsl(var(--bolt-text-secondary))] mt-1">
          Generate APK (Android) or IPA (iOS) files
        </p>
      </div>

      {/* Quota Display */}
      {quota && (
        <div className="px-4 py-3 bg-[hsl(var(--bolt-bg-secondary))] border-b border-[hsl(var(--bolt-border))]">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[hsl(var(--bolt-text-secondary))]">
              Builds this month:
            </span>
            <span className={`font-medium ${quota.can_build ? 'text-green-400' : 'text-red-400'}`}>
              {quota.builds_this_month} / {quota.builds_limit}
            </span>
          </div>
          {!quota.can_build && (
            <p className="text-xs text-yellow-400 mt-1">
              Upgrade to premium for more builds
            </p>
          )}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 p-4 space-y-6">
        {/* Platform Selection */}
        {!isBuilding && !currentBuild?.status?.includes('completed') && (
          <>
            <div>
              <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-2">
                Platform
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedPlatform('android')}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-colors ${
                    selectedPlatform === 'android'
                      ? 'border-green-500 bg-green-500/10 text-green-400'
                      : 'border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-secondary))] hover:border-[hsl(var(--bolt-text-tertiary))]'
                  }`}
                >
                  <Smartphone className="w-5 h-5" />
                  <span className="font-medium">Android APK</span>
                </button>
                <button
                  onClick={() => setSelectedPlatform('ios')}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border transition-colors ${
                    selectedPlatform === 'ios'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-400'
                      : 'border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] text-[hsl(var(--bolt-text-secondary))] hover:border-[hsl(var(--bolt-text-tertiary))]'
                  }`}
                >
                  <Apple className="w-5 h-5" />
                  <span className="font-medium">iOS IPA</span>
                </button>
              </div>
            </div>

            {/* Build Config */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-1">
                  App Name
                </label>
                <input
                  type="text"
                  value={config.app_name}
                  onChange={(e) => setConfig({ ...config, app_name: e.target.value })}
                  placeholder="My App"
                  className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                />
              </div>

              <div className="flex gap-4">
                <div className="flex-1">
                  <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-1">
                    Version
                  </label>
                  <input
                    type="text"
                    value={config.version}
                    onChange={(e) => setConfig({ ...config, version: e.target.value })}
                    placeholder="1.0.0"
                    className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                  />
                </div>
                <div className="w-24">
                  <label className="block text-sm font-medium text-[hsl(var(--bolt-text-primary))] mb-1">
                    Build #
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={config.build_number}
                    onChange={(e) => setConfig({ ...config, build_number: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))] focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                  />
                </div>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Build Button */}
            <button
              onClick={handleStartBuild}
              disabled={isBuilding || !config.app_name || Boolean(quota && !quota.can_build)}
              className="w-full py-3 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {selectedPlatform === 'android' ? (
                <Smartphone className="w-5 h-5" />
              ) : (
                <Apple className="w-5 h-5" />
              )}
              Start {selectedPlatform === 'android' ? 'APK' : 'IPA'} Build
            </button>
          </>
        )}

        {/* Build Progress */}
        {(isBuilding || currentBuild) && currentBuild && (
          <div className="space-y-4">
            {/* Status Header */}
            <div className="flex items-center gap-3">
              {getStatusIcon(currentBuild.status)}
              <div>
                <h3 className="font-medium text-[hsl(var(--bolt-text-primary))]">
                  {getStatusText(currentBuild.status)}
                </h3>
                {currentBuild.phase && currentBuild.status !== 'completed' && (
                  <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                    {currentBuild.phase}
                  </p>
                )}
              </div>
            </div>

            {/* Progress Bar */}
            {isBuilding && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-[hsl(var(--bolt-text-secondary))]">Progress</span>
                  <span className="text-[hsl(var(--bolt-text-primary))]">{currentBuild.progress}%</span>
                </div>
                <div className="h-2 bg-[hsl(var(--bolt-bg-secondary))] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[hsl(var(--bolt-accent))] transition-all duration-500"
                    style={{ width: `${currentBuild.progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Cancel Button */}
            {isBuilding && (
              <button
                onClick={handleCancelBuild}
                className="w-full py-2 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
              >
                Cancel Build
              </button>
            )}

            {/* Success State */}
            {currentBuild.status === 'completed' && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <CheckCircle2 className="w-5 h-5 text-green-400" />
                    <span className="font-medium text-green-400">Build Successful!</span>
                  </div>
                  {currentBuild.artifact_filename && (
                    <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                      {currentBuild.artifact_filename}
                      {currentBuild.artifact_size_mb && ` (${currentBuild.artifact_size_mb} MB)`}
                    </p>
                  )}
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={handleDownload}
                    className="flex-1 py-3 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                  >
                    <Download className="w-5 h-5" />
                    Download
                  </button>
                  <button
                    onClick={handleCopyUrl}
                    className="px-4 py-3 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
                    title="Copy download link"
                  >
                    {copied ? <Check className="w-5 h-5 text-green-400" /> : <Copy className="w-5 h-5" />}
                  </button>
                </div>

                <button
                  onClick={() => {
                    clearBuild()
                    setError(null)
                  }}
                  className="w-full py-2 rounded-lg border border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-secondary))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  Build Again
                </button>
              </div>
            )}

            {/* Failed State */}
            {currentBuild.status === 'failed' && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
                  <div className="flex items-center gap-2 mb-2">
                    <XCircle className="w-5 h-5 text-red-400" />
                    <span className="font-medium text-red-400">Build Failed</span>
                  </div>
                  {currentBuild.error_message && (
                    <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
                      {currentBuild.error_message}
                    </p>
                  )}
                </div>

                <button
                  onClick={() => {
                    clearBuild()
                    setError(null)
                  }}
                  className="w-full py-3 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-5 h-5" />
                  Try Again
                </button>
              </div>
            )}

            {/* Cancelled State */}
            {currentBuild.status === 'cancelled' && (
              <div className="space-y-4">
                <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-yellow-400" />
                    <span className="font-medium text-yellow-400">Build Cancelled</span>
                  </div>
                </div>

                <button
                  onClick={() => {
                    clearBuild()
                    setError(null)
                  }}
                  className="w-full py-3 rounded-lg bg-[hsl(var(--bolt-accent))] text-white font-medium hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
                >
                  <RefreshCw className="w-5 h-5" />
                  Start New Build
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="p-4 border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <p className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
          Builds are powered by Expo EAS Build service. APK/IPA files are available for download for 7 days.
        </p>
      </div>
    </div>
  )
}
