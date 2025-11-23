import { create } from 'zustand'

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

  // Actions
  addLog: (log: Omit<TerminalLog, 'id' | 'timestamp'>) => void
  clearLogs: () => void
  setVisible: (visible: boolean) => void
  setHeight: (height: number) => void
  setActiveTab: (tab: 'terminal' | 'problems' | 'output') => void
  executeCommand: (command: string) => void
}

export const useTerminalStore = create<TerminalState>((set, get) => ({
  logs: [],
  isVisible: false,
  height: 200,
  activeTab: 'terminal',

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
    set({ isVisible: visible })
  },

  setHeight: (height) => {
    set({ height: Math.max(150, Math.min(600, height)) })
  },

  setActiveTab: (tab) => {
    set({ activeTab: tab })
  },

  executeCommand: (command) => {
    const { addLog } = get()

    // Add command to logs
    addLog({
      type: 'command',
      content: `$ ${command}`
    })

    // Simulate command execution (in real app, this would call backend)
    setTimeout(() => {
      addLog({
        type: 'output',
        content: `Executed: ${command}`
      })
    }, 100)
  }
}))
