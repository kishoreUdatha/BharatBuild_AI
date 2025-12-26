import { create } from 'zustand'
import { useProjectStore } from './projectStore'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface TerminalLog {
  id: string
  type: 'command' | 'output' | 'error' | 'info'
  content: string
  timestamp: Date
}

interface TerminalState {
  logs: TerminalLog[]
  isVisible: boolean
  height: number
  activeTab: 'terminal' | 'problems' | 'output'
  isExecuting: boolean
  sessionActive: boolean  // Keep terminal open after execution
  lastVisibilityChange: number  // Timestamp of last visibility change (for debouncing)

  // Actions
  addLog: (log: Omit<TerminalLog, 'id' | 'timestamp'>) => void
  clearLogs: () => void
  setVisible: (visible: boolean) => void
  setHeight: (height: number) => void
  setActiveTab: (tab: 'terminal' | 'problems' | 'output') => void
  executeCommand: (command: string) => Promise<void>
  startSession: () => void  // Called when run starts
  endSession: () => void    // Called when run ends (keeps terminal open)
}

export const useTerminalStore = create<TerminalState>((set, get) => ({
  logs: [],
  isVisible: false,
  height: 200,
  activeTab: 'terminal',
  isExecuting: false,
  sessionActive: false,
  lastVisibilityChange: 0,

  startSession: () => {
    // Mark session as active AND open terminal to show logs
    console.log('[Terminal] Starting session - opening terminal for logs')
    set({
      sessionActive: true,
      isVisible: true,
      lastVisibilityChange: Date.now()
    })
  },

  endSession: () => {
    // Keep terminal open but mark session as ended
    // IMPORTANT: Do NOT set isVisible to false here
    console.log('[Terminal] Ending session - keeping terminal visible')
    set({ sessionActive: false, isExecuting: false })
  },

  addLog: (log) => {
    const newLog: TerminalLog = {
      ...log,
      id: `log-${Date.now()}-${Math.random()}`,
      timestamp: new Date()
    }
    set((state) => ({
      logs: [...state.logs, newLog]
    }))
  },

  clearLogs: () => {
    set({ logs: [] })
  },

  setVisible: (visible) => {
    const state = get()
    const now = Date.now()

    // Debounce: Prevent closing terminal within 500ms of opening
    // This prevents race conditions during rapid state changes
    if (!visible && state.isVisible) {
      const timeSinceOpen = now - state.lastVisibilityChange
      if (timeSinceOpen < 500) {
        console.log('[Terminal] Ignoring close request - too soon after open:', timeSinceOpen, 'ms')
        return
      }

      // Don't close if session is active (running something)
      if (state.sessionActive) {
        console.log('[Terminal] Ignoring close request - session is active')
        return
      }
    }

    console.log('[Terminal] setVisible:', visible)
    set({ isVisible: visible, lastVisibilityChange: now })
  },

  setHeight: (height) => {
    set({ height: Math.max(150, Math.min(600, height)) })
  },

  setActiveTab: (tab) => {
    set({ activeTab: tab })
  },

  // ============= REAL CONTAINER EXECUTION (Like Bolt.new) =============
  executeCommand: async (command: string) => {
    const { addLog } = get()
    const projectId = useProjectStore.getState().currentProject?.id

    // Add command to logs
    addLog({
      type: 'command',
      content: command
    })

    if (!projectId) {
      addLog({
        type: 'error',
        content: 'No project selected. Please generate a project first.'
      })
      return
    }

    set({ isExecuting: true })

    try {
      const token = localStorage.getItem('access_token')

      // Call container execution API with streaming
      const response = await fetch(`${API_BASE_URL}/containers/${projectId}/exec`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          command,
          timeout: 120
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Command failed: ${response.status}`)
      }

      // Stream the output
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('No response body')
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'stdout') {
                addLog({
                  type: 'output',
                  content: event.data
                })
              } else if (event.type === 'stderr') {
                addLog({
                  type: 'error',
                  content: event.data
                })
              } else if (event.type === 'exit') {
                addLog({
                  type: 'info',
                  content: `Process exited with code ${event.code}`
                })
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }

      // Process remaining buffer
      if (buffer && buffer.startsWith('data: ')) {
        try {
          const event = JSON.parse(buffer.slice(6))
          if (event.type === 'stdout') {
            addLog({ type: 'output', content: event.data })
          } else if (event.type === 'stderr') {
            addLog({ type: 'error', content: event.data })
          }
        } catch {}
      }

    } catch (error: any) {
      addLog({
        type: 'error',
        content: error.message || 'Command execution failed'
      })
    } finally {
      set({ isExecuting: false })
    }
  }
}))
