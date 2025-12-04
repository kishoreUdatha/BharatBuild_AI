/**
 * Project Sync Hook - Handles syncing project files with backend
 * - Auto-saves files to PostgreSQL/S3 when modified
 * - Loads project on page refresh
 * - Debounced saves to reduce API calls
 * - Falls back to offline queue when connection is lost
 */

import { useEffect, useRef, useCallback, useState } from 'react'
import { useProjectStore } from '@/store/projectStore'
import { apiClient } from '@/lib/api-client'
import { offlineQueue } from '@/lib/offline-queue'

// Debounce delay for auto-save (2 seconds)
const SAVE_DEBOUNCE_MS = 2000

// Store project ID in localStorage for refresh recovery
const PROJECT_ID_KEY = 'bharatbuild_current_project_id'

export function useProjectSync() {
  const {
    currentProject,
    pendingSaves,
    markFilePendingSave,
    markFileSaved,
    loadFromBackend,
    updateFile
  } = useProjectStore()

  const saveTimeouts = useRef<Map<string, NodeJS.Timeout>>(new Map())
  const isSaving = useRef(false)
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)

  // Track online/offline status
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  // Save project ID to localStorage when project changes
  useEffect(() => {
    if (currentProject?.id) {
      localStorage.setItem(PROJECT_ID_KEY, currentProject.id)
    }
  }, [currentProject?.id])

  // Load project from backend on mount (page refresh recovery)
  useEffect(() => {
    const loadProjectFromBackend = async () => {
      const savedProjectId = localStorage.getItem(PROJECT_ID_KEY)

      if (savedProjectId && !currentProject) {
        try {
          console.log('[useProjectSync] Loading project from backend:', savedProjectId)
          const projectData = await apiClient.loadProjectWithFiles(savedProjectId)

          if (projectData) {
            loadFromBackend(projectData)
            console.log('[useProjectSync] Project loaded successfully')
          }
        } catch (error) {
          console.error('[useProjectSync] Failed to load project:', error)
          // Project might not exist in backend, clear localStorage
          localStorage.removeItem(PROJECT_ID_KEY)
        }
      }
    }

    loadProjectFromBackend()
  }, []) // Only run once on mount

  // Debounced save function - with offline queue fallback
  const saveFileToBackend = useCallback(async (path: string, content: string) => {
    if (!currentProject?.id) return

    try {
      isSaving.current = true
      markFilePendingSave(path)

      // Check if we're online
      if (!navigator.onLine) {
        // Queue for later sync
        offlineQueue.queueSaveFile(currentProject.id, path, content)
        console.log('[useProjectSync] Queued file for offline sync:', path)
        return
      }

      await apiClient.saveFile(currentProject.id, {
        path,
        content
      })

      markFileSaved(path)
      console.log('[useProjectSync] Saved file:', path)
    } catch (error: any) {
      console.error('[useProjectSync] Failed to save file:', path, error)

      // If network error, queue for later
      if (!error.response) {
        offlineQueue.queueSaveFile(currentProject.id, path, content)
        console.log('[useProjectSync] Network error, queued file for later:', path)
      }
      // Keep in pending state so user knows save failed
    } finally {
      isSaving.current = false
    }
  }, [currentProject?.id, markFilePendingSave, markFileSaved])

  // Schedule debounced save when file content changes
  const scheduleFileSave = useCallback((path: string, content: string) => {
    // Clear existing timeout for this file
    const existingTimeout = saveTimeouts.current.get(path)
    if (existingTimeout) {
      clearTimeout(existingTimeout)
    }

    // Schedule new save
    const timeout = setTimeout(() => {
      saveFileToBackend(path, content)
      saveTimeouts.current.delete(path)
    }, SAVE_DEBOUNCE_MS)

    saveTimeouts.current.set(path, timeout)
    markFilePendingSave(path)
  }, [saveFileToBackend, markFilePendingSave])

  // Bulk save all pending files (for manual save or before navigation)
  const saveAllPending = useCallback(async () => {
    if (!currentProject?.id || pendingSaves.size === 0) return

    const filesToSave: Array<{ path: string; content: string }> = []

    // Get content for all pending files
    const getAllFiles = (files: typeof currentProject.files): void => {
      for (const file of files) {
        if (file.type === 'file' && pendingSaves.has(file.path)) {
          filesToSave.push({
            path: file.path,
            content: file.content
          })
        }
        if (file.children) {
          getAllFiles(file.children)
        }
      }
    }

    getAllFiles(currentProject.files)

    if (filesToSave.length === 0) return

    try {
      // Check if we're online
      if (!navigator.onLine) {
        // Queue for later sync
        offlineQueue.queueSaveFilesBulk(currentProject.id, filesToSave)
        console.log('[useProjectSync] Queued', filesToSave.length, 'files for offline sync')
        return
      }

      await apiClient.saveFilesBulk(currentProject.id, filesToSave)
      filesToSave.forEach(f => markFileSaved(f.path))
      console.log('[useProjectSync] Bulk saved', filesToSave.length, 'files')
    } catch (error: any) {
      console.error('[useProjectSync] Bulk save failed:', error)

      // If network error, queue for later
      if (!error.response) {
        offlineQueue.queueSaveFilesBulk(currentProject.id, filesToSave)
        console.log('[useProjectSync] Network error, queued files for later')
      }
    }
  }, [currentProject, pendingSaves, markFileSaved])

  // Save all pending on unmount or page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      // Clear all pending timeouts
      saveTimeouts.current.forEach(timeout => clearTimeout(timeout))
      // Note: Can't await async in beforeunload, but we've been saving continuously
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      // Save all pending on unmount
      saveAllPending()
    }
  }, [saveAllPending])

  // Refresh project from backend
  const refreshFromBackend = useCallback(async () => {
    if (!currentProject?.id) return

    try {
      const projectData = await apiClient.loadProjectWithFiles(currentProject.id)
      if (projectData) {
        loadFromBackend(projectData)
      }
    } catch (error) {
      console.error('[useProjectSync] Failed to refresh project:', error)
    }
  }, [currentProject?.id, loadFromBackend])

  return {
    scheduleFileSave,
    saveAllPending,
    refreshFromBackend,
    hasPendingSaves: pendingSaves.size > 0,
    pendingSavesCount: pendingSaves.size,
    isOnline
  }
}
