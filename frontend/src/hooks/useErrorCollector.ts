import { useEffect, useCallback } from 'react'
import { useErrorStore, CollectedError } from '@/store/errorStore'
import { useTerminalStore } from '@/store/terminalStore'
import { apiClient } from '@/lib/api-client'

interface UseErrorCollectorOptions {
  projectId?: string
  autoCapture?: boolean
}

interface FixErrorResponse {
  success: boolean
  fixes?: {
    file: string
    patch: string
    description: string
  }[]
  message?: string
}

export function useErrorCollector(options: UseErrorCollectorOptions = {}) {
  const { projectId, autoCapture = true } = options

  const {
    errors,
    addBuildError,
    addRuntimeError,
    addTerminalError,
    addNetworkError,
    markResolved,
    markAllResolved,
    clearErrors,
    getUnresolvedErrors,
    getErrorCount,
    isFixing,
    setFixing,
    selectedErrorId,
    selectError
  } = useErrorStore()

  const { logs } = useTerminalStore()

  // Watch terminal logs for errors
  useEffect(() => {
    if (!autoCapture) return

    const latestLogs = logs.slice(-10) // Check last 10 logs
    latestLogs.forEach(log => {
      if (log.type === 'error') {
        // Check if it's a build/runtime error pattern
        const content = log.content

        // Build error patterns
        const buildPatterns = [
          /error\s+TS\d+:/i,  // TypeScript
          /SyntaxError:/i,
          /Failed to compile/i,
          /Build failed/i,
          /Module not found/i,
          /Cannot find module/i,
          /Error: Command failed/i,
          /npm ERR!/i,
          /error\[E\d+\]/i,  // Rust
          /error: /i
        ]

        const isBuildError = buildPatterns.some(pattern => pattern.test(content))

        if (isBuildError) {
          addBuildError(content)
        } else if (content.includes('Error:') || content.includes('error:')) {
          addTerminalError(content)
        }
      }
    })
  }, [logs, autoCapture, addBuildError, addTerminalError])

  // Fix a single error using Fixer Agent
  const fixError = useCallback(async (error: CollectedError): Promise<FixErrorResponse> => {
    if (!projectId) {
      return { success: false, message: 'No project selected' }
    }

    setFixing(true)
    selectError(error.id)

    try {
      const response = await apiClient.post<FixErrorResponse>(`/projects/${projectId}/fix-error`, {
        error: {
          message: error.message,
          file: error.file,
          line: error.line,
          column: error.column,
          stack: error.stack,
          source: error.source,
          severity: error.severity,
          // Network error specific fields
          url: error.url,
          status: error.status,
          method: error.method
        }
      })

      if (response.success) {
        markResolved(error.id)
      }

      return response
    } catch (err: any) {
      console.error('[useErrorCollector] Fix error failed:', err)
      return {
        success: false,
        message: err.message || 'Failed to fix error'
      }
    } finally {
      setFixing(false)
      selectError(null)
    }
  }, [projectId, setFixing, selectError, markResolved])

  // Fix all unresolved errors
  const fixAllErrors = useCallback(async (): Promise<FixErrorResponse> => {
    if (!projectId) {
      return { success: false, message: 'No project selected' }
    }

    const unresolvedErrors = getUnresolvedErrors()
    if (unresolvedErrors.length === 0) {
      return { success: true, message: 'No errors to fix' }
    }

    setFixing(true)

    try {
      const response = await apiClient.post<FixErrorResponse>(`/projects/${projectId}/fix-errors`, {
        errors: unresolvedErrors.map(err => ({
          message: err.message,
          file: err.file,
          line: err.line,
          column: err.column,
          stack: err.stack,
          source: err.source,
          severity: err.severity,
          // Network error specific fields
          url: err.url,
          status: err.status,
          method: err.method
        }))
      })

      if (response.success) {
        markAllResolved()
      }

      return response
    } catch (err: any) {
      console.error('[useErrorCollector] Fix all errors failed:', err)
      return {
        success: false,
        message: err.message || 'Failed to fix errors'
      }
    } finally {
      setFixing(false)
    }
  }, [projectId, setFixing, getUnresolvedErrors, markAllResolved])

  // Format error for display
  const formatError = useCallback((error: CollectedError): string => {
    let formatted = error.message
    if (error.file) {
      formatted += `\n  at ${error.file}`
      if (error.line) {
        formatted += `:${error.line}`
        if (error.column) {
          formatted += `:${error.column}`
        }
      }
    }
    return formatted
  }, [])

  // Get error context for AI (includes surrounding code if available)
  const getErrorContext = useCallback(async (error: CollectedError): Promise<string> => {
    let context = `Error: ${error.message}\n`
    context += `Source: ${error.source}\n`
    context += `Severity: ${error.severity}\n`

    if (error.file) {
      context += `File: ${error.file}\n`
      if (error.line) {
        context += `Line: ${error.line}\n`
      }
    }

    // Network error specific context
    if (error.source === 'network') {
      if (error.url) {
        context += `URL: ${error.url}\n`
      }
      if (error.method) {
        context += `HTTP Method: ${error.method}\n`
      }
      if (error.status) {
        context += `HTTP Status: ${error.status}\n`
      }
    }

    if (error.stack) {
      context += `\nStack trace:\n${error.stack}\n`
    }

    return context
  }, [])

  return {
    // State
    errors,
    unresolvedErrors: getUnresolvedErrors(),
    errorCount: getErrorCount(),
    isFixing,
    selectedErrorId,

    // Actions
    fixError,
    fixAllErrors,
    markResolved,
    markAllResolved,
    clearErrors,
    selectError,
    addNetworkError,

    // Utilities
    formatError,
    getErrorContext
  }
}

export default useErrorCollector
