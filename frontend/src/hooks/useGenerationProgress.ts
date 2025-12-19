'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useProjectStore } from '@/store/projectStore'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface FileProgress {
  path: string
  name: string
  status: 'planned' | 'generating' | 'completed' | 'failed' | 'skipped'
  order: number | null
  has_content: boolean
  updated_at: string | null
}

interface GenerationProgress {
  project_id: string
  title: string
  project_status: string
  generation: {
    total_files: number
    completed: number
    planned: number
    generating: number
    failed: number
    progress_percent: number
    is_complete: boolean
    is_in_progress: boolean
  }
  files: FileProgress[]
  can_resume: boolean
  last_update: string | null
}

/**
 * Hook for tracking generation progress with auto-polling fallback.
 *
 * When SSE connection is lost (internet drops), this hook polls
 * the server for updates every 3 seconds.
 *
 * Usage:
 * const { progress, isPolling, startPolling, stopPolling } = useGenerationProgress(projectId)
 */
export function useGenerationProgress(projectId: string | null) {
  const [progress, setProgress] = useState<GenerationProgress | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(true)

  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const lastUpdateRef = useRef<string | null>(null)

  // Fetch progress from server
  const fetchProgress = useCallback(async () => {
    if (!projectId || projectId === 'default-project') return null

    try {
      const token = localStorage.getItem('access_token')
      if (!token) return null

      const response = await fetch(`${API_BASE_URL}/orchestrator/project/${projectId}/progress`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch progress')
      }

      const data: GenerationProgress = await response.json()
      setProgress(data)
      setError(null)
      setIsConnected(true)

      // Check if there are new completed files
      if (data.last_update !== lastUpdateRef.current) {
        lastUpdateRef.current = data.last_update

        // Sync completed files to project store
        const projectStore = useProjectStore.getState()
        for (const file of data.files) {
          if (file.status === 'completed' && file.has_content) {
            // Check if file exists in store
            const existingFile = projectStore.currentProject?.files.find(f => f.path === file.path)
            if (!existingFile) {
              // Fetch file content and add to store
              await fetchAndAddFile(projectId, file.path)
            }
          }
        }
      }

      return data
    } catch (err) {
      setError('Connection lost. Retrying...')
      setIsConnected(false)
      return null
    }
  }, [projectId])

  // Fetch individual file content
  const fetchAndAddFile = async (projectId: string, filePath: string) => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return

      const response = await fetch(
        `${API_BASE_URL}/projects/${projectId}/files/${encodeURIComponent(filePath)}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )

      if (response.ok) {
        const fileData = await response.json()
        const projectStore = useProjectStore.getState()
        const ext = filePath.split('.').pop()?.toLowerCase() || ''
        const langMap: Record<string, string> = {
          'ts': 'typescript', 'tsx': 'typescript', 'js': 'javascript', 'jsx': 'javascript',
          'py': 'python', 'css': 'css', 'html': 'html', 'json': 'json', 'md': 'markdown'
        }
        projectStore.addFile({
          path: filePath,
          content: fileData.content || '',
          type: 'file',
          language: langMap[ext] || ext || 'text'
        })
        console.log(`[Progress] Synced file from server: ${filePath}`)
      }
    } catch (err) {
      console.warn(`[Progress] Failed to fetch file: ${filePath}`, err)
    }
  }

  // Start polling
  const startPolling = useCallback((intervalMs: number = 3000) => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
    }

    setIsPolling(true)
    console.log('[Progress] Started polling for updates')

    // Fetch immediately
    fetchProgress()

    // Then poll at interval
    pollingIntervalRef.current = setInterval(() => {
      fetchProgress().then(data => {
        // Stop polling if generation is complete
        if (data?.generation.is_complete) {
          stopPolling()
          console.log('[Progress] Generation complete, stopped polling')
        }
      })
    }, intervalMs)
  }, [fetchProgress])

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
    setIsPolling(false)
    console.log('[Progress] Stopped polling')
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
      }
    }
  }, [])

  // Detect connection loss and auto-start polling
  useEffect(() => {
    const handleOnline = () => {
      console.log('[Progress] Connection restored')
      setIsConnected(true)
      // Fetch latest progress immediately
      fetchProgress()
    }

    const handleOffline = () => {
      console.log('[Progress] Connection lost')
      setIsConnected(false)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [fetchProgress])

  return {
    progress,
    isPolling,
    isConnected,
    error,
    startPolling,
    stopPolling,
    fetchProgress,
    // Convenience getters
    totalFiles: progress?.generation.total_files ?? 0,
    completedFiles: progress?.generation.completed ?? 0,
    pendingFiles: progress?.generation.planned ?? 0,
    progressPercent: progress?.generation.progress_percent ?? 0,
    isComplete: progress?.generation.is_complete ?? false,
    isInProgress: progress?.generation.is_in_progress ?? false,
    canResume: progress?.can_resume ?? false,
    files: progress?.files ?? []
  }
}
