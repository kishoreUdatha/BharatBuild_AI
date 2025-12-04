import { useEffect, useCallback, useRef } from 'react'
import { create } from 'zustand'

/**
 * File change event types
 */
export type FileChangeType = 'created' | 'updated' | 'deleted' | 'fixed' | 'patched'

export interface FileChangeEvent {
  type: FileChangeType
  path: string
  timestamp: Date
  source: 'writer' | 'fixer' | 'user' | 'system'
  projectId?: string
}

/**
 * Store for file change events
 */
interface FileChangeStore {
  events: FileChangeEvent[]
  lastChange: FileChangeEvent | null
  listeners: Set<(event: FileChangeEvent) => void>

  // Actions
  addEvent: (event: Omit<FileChangeEvent, 'timestamp'>) => void
  clearEvents: () => void
  subscribe: (listener: (event: FileChangeEvent) => void) => () => void
}

export const useFileChangeStore = create<FileChangeStore>((set, get) => ({
  events: [],
  lastChange: null,
  listeners: new Set(),

  addEvent: (event) => {
    const newEvent: FileChangeEvent = {
      ...event,
      timestamp: new Date()
    }

    set((state) => ({
      events: [...state.events.slice(-50), newEvent], // Keep last 50 events
      lastChange: newEvent
    }))

    // Notify all listeners
    get().listeners.forEach(listener => {
      try {
        listener(newEvent)
      } catch (e) {
        console.error('[FileChangeStore] Listener error:', e)
      }
    })

    console.log(`[FileChangeStore] File ${event.type}: ${event.path}`)
  },

  clearEvents: () => {
    set({ events: [], lastChange: null })
  },

  subscribe: (listener) => {
    get().listeners.add(listener)
    return () => {
      get().listeners.delete(listener)
    }
  }
}))

/**
 * Hook options
 */
interface UseFileChangeEventsOptions {
  projectId?: string
  onFileChange?: (event: FileChangeEvent) => void
  autoReloadPreview?: boolean
  reloadDelay?: number // ms to wait before triggering reload (debounce)
}

/**
 * Hook to listen for file change events and trigger actions
 *
 * Usage:
 * ```tsx
 * const { lastChange, triggerReload } = useFileChangeEvents({
 *   projectId: 'my-project',
 *   onFileChange: (event) => console.log('File changed:', event),
 *   autoReloadPreview: true
 * })
 * ```
 */
export function useFileChangeEvents(options: UseFileChangeEventsOptions = {}) {
  const {
    projectId,
    onFileChange,
    autoReloadPreview = false,
    reloadDelay = 500
  } = options

  const { events, lastChange, addEvent, subscribe } = useFileChangeStore()
  const reloadTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const reloadCallbackRef = useRef<(() => void) | null>(null)

  // Store the reload callback
  const setReloadCallback = useCallback((callback: () => void) => {
    reloadCallbackRef.current = callback
  }, [])

  // Trigger a reload with debouncing
  const triggerReload = useCallback(() => {
    if (reloadTimeoutRef.current) {
      clearTimeout(reloadTimeoutRef.current)
    }

    reloadTimeoutRef.current = setTimeout(() => {
      if (reloadCallbackRef.current) {
        console.log('[useFileChangeEvents] Triggering preview reload')
        reloadCallbackRef.current()
      }
    }, reloadDelay)
  }, [reloadDelay])

  // Subscribe to file change events
  useEffect(() => {
    const handleFileChange = (event: FileChangeEvent) => {
      // Filter by project ID if specified
      if (projectId && event.projectId && event.projectId !== projectId) {
        return
      }

      // Call custom handler
      onFileChange?.(event)

      // Auto-reload preview if enabled and it's a fix/update
      if (autoReloadPreview && ['fixed', 'patched', 'updated'].includes(event.type)) {
        triggerReload()
      }
    }

    const unsubscribe = subscribe(handleFileChange)

    return () => {
      unsubscribe()
      if (reloadTimeoutRef.current) {
        clearTimeout(reloadTimeoutRef.current)
      }
    }
  }, [projectId, onFileChange, autoReloadPreview, subscribe, triggerReload])

  // Filter events by project ID
  const projectEvents = projectId
    ? events.filter(e => !e.projectId || e.projectId === projectId)
    : events

  // Get recent changes (last 5 seconds)
  const recentChanges = projectEvents.filter(
    e => Date.now() - e.timestamp.getTime() < 5000
  )

  // Check if any file was recently fixed
  const hasRecentFix = recentChanges.some(e => e.type === 'fixed' || e.type === 'patched')

  return {
    // State
    events: projectEvents,
    lastChange,
    recentChanges,
    hasRecentFix,

    // Actions
    addEvent,
    triggerReload,
    setReloadCallback,

    // Utility to emit file change from other components
    emitFileChange: (type: FileChangeType, path: string, source: FileChangeEvent['source'] = 'system') => {
      addEvent({ type, path, source, projectId })
    }
  }
}

/**
 * Parse FILE_OPERATION events from SSE stream and emit file changes
 * Call this when processing orchestrator events
 */
export function parseFileOperationEvent(
  eventData: {
    path?: string
    operation?: string
    status?: string
    type?: string
  },
  projectId?: string
) {
  const store = useFileChangeStore.getState()

  if (!eventData.path) return

  // Map operation to change type
  let changeType: FileChangeType = 'updated'
  const operation = eventData.operation?.toLowerCase() || ''

  if (operation.includes('create') || operation === 'created') {
    changeType = 'created'
  } else if (operation.includes('delete') || operation === 'deleted') {
    changeType = 'deleted'
  } else if (operation.includes('fix') || operation === 'fixed') {
    changeType = 'fixed'
  } else if (operation.includes('patch') || operation === 'patched') {
    changeType = 'patched'
  }

  // Emit the event
  store.addEvent({
    type: changeType,
    path: eventData.path,
    source: operation.includes('fix') ? 'fixer' : 'writer',
    projectId
  })
}

export default useFileChangeEvents
