import { create } from 'zustand'

export type ErrorSource = 'browser' | 'build' | 'runtime' | 'terminal' | 'network'
export type ErrorSeverity = 'error' | 'warning' | 'info'

export interface CollectedError {
  id: string
  source: ErrorSource
  severity: ErrorSeverity
  message: string
  file?: string
  line?: number
  column?: number
  stack?: string
  timestamp: Date
  resolved: boolean
  // Network error specific fields
  url?: string
  status?: number
  method?: string
}

interface ErrorState {
  errors: CollectedError[]
  isFixing: boolean
  selectedErrorId: string | null

  // Actions
  addError: (error: Omit<CollectedError, 'id' | 'timestamp' | 'resolved'>) => void
  addBrowserError: (message: string, file?: string, line?: number, column?: number, stack?: string) => void
  addBuildError: (message: string, file?: string, line?: number) => void
  addRuntimeError: (message: string, stack?: string) => void
  addTerminalError: (message: string) => void
  addNetworkError: (message: string, url: string, status?: number, method?: string) => void
  markResolved: (id: string) => void
  markAllResolved: () => void
  clearErrors: () => void
  clearResolvedErrors: () => void
  selectError: (id: string | null) => void
  setFixing: (fixing: boolean) => void
  getUnresolvedErrors: () => CollectedError[]
  getErrorsBySource: (source: ErrorSource) => CollectedError[]
  getErrorCount: () => { total: number; errors: number; warnings: number }
}

export const useErrorStore = create<ErrorState>((set, get) => ({
  errors: [],
  isFixing: false,
  selectedErrorId: null,

  addError: (error) => {
    const newError: CollectedError = {
      ...error,
      id: `err-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date(),
      resolved: false
    }

    // Deduplicate - don't add if same message already exists recently (within 5 seconds)
    const recentThreshold = Date.now() - 5000
    const isDuplicate = get().errors.some(
      e => e.message === error.message &&
           e.source === error.source &&
           e.timestamp.getTime() > recentThreshold
    )

    if (!isDuplicate) {
      set((state) => ({
        errors: [...state.errors, newError].slice(-100) // Keep last 100 errors
      }))
      console.log(`[ErrorStore] Collected ${error.source} ${error.severity}:`, error.message)
    }
  },

  addBrowserError: (message, file, line, column, stack) => {
    // Try to extract file:line from message or stack if not provided
    let extractedFile = file
    let extractedLine = line
    let extractedColumn = column

    if (!extractedFile || !extractedLine) {
      // Patterns to extract file:line from error messages
      const patterns = [
        // React/JS errors: "at Component (file.jsx:10:5)"
        /at\s+\w+\s+\(([^:)]+):(\d+):?(\d+)?\)/,
        // Direct file reference: "file.jsx:10:5"
        /([^\s:(]+\.[jt]sx?):(\d+)(?::(\d+))?/,
        // Webpack/Vite errors: "in ./src/file.jsx (line 10)"
        /in\s+\.?\/([^\s]+)\s+\(line\s+(\d+)\)/i,
        // Stack trace first line
        /^\s+at\s+(?:\w+\s+)?\(?([^:)]+):(\d+):?(\d+)?\)?/m,
      ]

      // Try message first
      for (const pattern of patterns) {
        const match = message.match(pattern)
        if (match) {
          extractedFile = extractedFile || match[1]
          extractedLine = extractedLine || (match[2] ? parseInt(match[2]) : undefined)
          extractedColumn = extractedColumn || (match[3] ? parseInt(match[3]) : undefined)
          break
        }
      }

      // Try stack trace if still no file
      if ((!extractedFile || !extractedLine) && stack) {
        for (const pattern of patterns) {
          const match = stack.match(pattern)
          if (match) {
            extractedFile = extractedFile || match[1]
            extractedLine = extractedLine || (match[2] ? parseInt(match[2]) : undefined)
            extractedColumn = extractedColumn || (match[3] ? parseInt(match[3]) : undefined)
            break
          }
        }
      }
    }

    // Normalize file path (remove leading ./ or webpack prefixes)
    if (extractedFile) {
      extractedFile = extractedFile.replace(/^\.\//, '').replace(/^\(webpack\)\//, '')
    }

    get().addError({
      source: 'browser',
      severity: 'error',
      message,
      file: extractedFile,
      line: extractedLine,
      column: extractedColumn,
      stack
    })
  },

  addBuildError: (message, file, line) => {
    get().addError({
      source: 'build',
      severity: 'error',
      message,
      file,
      line
    })
  },

  addRuntimeError: (message, stack) => {
    get().addError({
      source: 'runtime',
      severity: 'error',
      message,
      stack
    })
  },

  addTerminalError: (message) => {
    // Parse terminal errors to extract file/line info
    const fileMatch = message.match(/(?:at\s+)?([^\s:]+):(\d+)(?::(\d+))?/)
    get().addError({
      source: 'terminal',
      severity: 'error',
      message,
      file: fileMatch?.[1],
      line: fileMatch?.[2] ? parseInt(fileMatch[2]) : undefined,
      column: fileMatch?.[3] ? parseInt(fileMatch[3]) : undefined
    })
  },

  addNetworkError: (message, url, status, method) => {
    // Determine severity based on status code
    let severity: ErrorSeverity = 'error'
    if (status && status >= 400 && status < 500) {
      severity = status === 404 ? 'warning' : 'error'
    }

    get().addError({
      source: 'network',
      severity,
      message,
      url,
      status,
      method
    })
  },

  markResolved: (id) => {
    set((state) => ({
      errors: state.errors.map((e) =>
        e.id === id ? { ...e, resolved: true } : e
      )
    }))
  },

  markAllResolved: () => {
    set((state) => ({
      errors: state.errors.map((e) => ({ ...e, resolved: true }))
    }))
  },

  clearErrors: () => {
    set({ errors: [], selectedErrorId: null })
  },

  clearResolvedErrors: () => {
    set((state) => ({
      errors: state.errors.filter((e) => !e.resolved)
    }))
  },

  selectError: (id) => {
    set({ selectedErrorId: id })
  },

  setFixing: (fixing) => {
    set({ isFixing: fixing })
  },

  getUnresolvedErrors: () => {
    return get().errors.filter((e) => !e.resolved)
  },

  getErrorsBySource: (source) => {
    return get().errors.filter((e) => e.source === source)
  },

  getErrorCount: () => {
    const errors = get().errors.filter(e => !e.resolved)
    return {
      total: errors.length,
      errors: errors.filter(e => e.severity === 'error').length,
      warnings: errors.filter(e => e.severity === 'warning').length
    }
  }
}))
