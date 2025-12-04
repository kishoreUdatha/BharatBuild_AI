'use client'

import { useCallback, useRef, useEffect, useState } from 'react'
import { useProjectStore } from '@/store/projectStore'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface AutoSaveOptions {
  debounceMs?: number  // Debounce delay in milliseconds (default: 1500)
  enabled?: boolean    // Enable/disable auto-save (default: true)
}

interface AutoSaveState {
  isSaving: boolean
  lastSaved: Date | null
  error: string | null
  pendingPaths: Set<string>
}

export function useAutoSave(options: AutoSaveOptions = {}) {
  const { debounceMs = 1500, enabled = true } = options

  const {
    currentProject,
    markFilePendingSave,
    markFileSaved,
    pendingSaves
  } = useProjectStore()

  const [state, setState] = useState<AutoSaveState>({
    isSaving: false,
    lastSaved: null,
    error: null,
    pendingPaths: new Set()
  })

  // Track debounce timers for each file
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map())

  // Get auth token from localStorage
  const getAuthToken = useCallback(() => {
    if (typeof window === 'undefined') return null
    const authData = localStorage.getItem('bharatbuild-auth')
    if (authData) {
      try {
        const parsed = JSON.parse(authData)
        return parsed.state?.token || parsed.token
      } catch {
        return null
      }
    }
    return null
  }, [])

  // Sync a single file to backend
  const syncFile = useCallback(async (path: string, content: string) => {
    if (!currentProject?.id) {
      console.warn('[AutoSave] No project ID, skipping sync')
      return false
    }

    const token = getAuthToken()
    if (!token) {
      console.warn('[AutoSave] No auth token, skipping sync')
      return false
    }

    setState(prev => ({ ...prev, isSaving: true, error: null }))

    try {
      const response = await fetch(`${API_BASE_URL}/sync/file`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: currentProject.id,
          path,
          content,
          language: getLanguageFromPath(path)
        })
      })

      if (!response.ok) {
        throw new Error(`Sync failed: ${response.status}`)
      }

      const result = await response.json()

      if (result.success) {
        markFileSaved(path)
        setState(prev => ({
          ...prev,
          isSaving: false,
          lastSaved: new Date(),
          pendingPaths: new Set(Array.from(prev.pendingPaths).filter(p => p !== path))
        }))
        console.log(`[AutoSave] Saved: ${path}`)
        return true
      } else {
        throw new Error(result.message || 'Sync failed')
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      setState(prev => ({ ...prev, isSaving: false, error: errorMsg }))
      console.error(`[AutoSave] Error saving ${path}:`, error)
      return false
    }
  }, [currentProject?.id, getAuthToken, markFileSaved])

  // Schedule a debounced save for a file
  const scheduleSync = useCallback((path: string, content: string) => {
    if (!enabled) return

    // Mark file as pending
    markFilePendingSave(path)
    setState(prev => ({
      ...prev,
      pendingPaths: new Set([...Array.from(prev.pendingPaths), path])
    }))

    // Clear existing timer for this file
    const existingTimer = timersRef.current.get(path)
    if (existingTimer) {
      clearTimeout(existingTimer)
    }

    // Set new debounced timer
    const timer = setTimeout(() => {
      syncFile(path, content)
      timersRef.current.delete(path)
    }, debounceMs)

    timersRef.current.set(path, timer)
  }, [enabled, debounceMs, markFilePendingSave, syncFile])

  // Force immediate sync for a file
  const syncNow = useCallback(async (path: string, content: string) => {
    // Clear any pending timer
    const existingTimer = timersRef.current.get(path)
    if (existingTimer) {
      clearTimeout(existingTimer)
      timersRef.current.delete(path)
    }

    return syncFile(path, content)
  }, [syncFile])

  // Sync all pending files immediately
  const syncAllPending = useCallback(async () => {
    const pendingPaths = Array.from(state.pendingPaths)
    if (pendingPaths.length === 0) return

    console.log(`[AutoSave] Syncing ${pendingPaths.length} pending files...`)

    // Clear all timers
    timersRef.current.forEach((timer) => clearTimeout(timer))
    timersRef.current.clear()

    // Note: We'd need access to file contents here
    // This is a simplified version - in practice, we'd need to track content too
  }, [state.pendingPaths])

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer))
      timersRef.current.clear()
    }
  }, [])

  return {
    // State
    isSaving: state.isSaving,
    lastSaved: state.lastSaved,
    error: state.error,
    hasPendingChanges: state.pendingPaths.size > 0 || pendingSaves.size > 0,
    pendingCount: Math.max(state.pendingPaths.size, pendingSaves.size),

    // Actions
    scheduleSync,
    syncNow,
    syncAllPending
  }
}

// Helper to detect language from file path
function getLanguageFromPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase()
  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    html: 'html',
    css: 'css',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
    sh: 'shell',
    sql: 'sql',
    java: 'java',
    go: 'go',
    rs: 'rust',
    cpp: 'cpp',
    c: 'c',
  }
  return languageMap[ext || ''] || 'plaintext'
}
