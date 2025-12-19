/**
 * useSDKFixer Hook
 *
 * Custom React hook for SDK-based error fixing.
 * Provides state management and easy integration with UI components.
 */

import { useState, useCallback } from 'react'
import { useProjectStore } from '@/store/projectStore'
import { useErrorStore } from '@/store/errorStore'
import { useTerminalStore } from '@/store/terminalStore'
import { sdkService, FixErrorResponse, StreamEvent } from '@/services/sdkService'

export interface UseSDKFixerOptions {
  buildCommand?: string
  maxRetries?: number
  onFixStart?: () => void
  onFixComplete?: (result: FixErrorResponse) => void
  onFixError?: (error: Error) => void
  onFileModified?: (filePath: string) => void
}

export interface UseSDKFixerReturn {
  // State
  isFixing: boolean
  lastResult: FixErrorResponse | null
  error: string | null

  // Actions
  fixError: (errorMessage: string, stackTrace?: string) => Promise<FixErrorResponse | null>
  fixCurrentErrors: () => Promise<FixErrorResponse | null>
  fixWithStreaming: (errorMessage: string, onProgress?: (event: StreamEvent) => void) => Promise<void>
  reset: () => void

  // Tool shortcuts
  runCommand: (command: string) => Promise<string>
  viewFile: (path: string) => Promise<string>
  searchFiles: (pattern: string) => Promise<string>
}

export function useSDKFixer(options: UseSDKFixerOptions = {}): UseSDKFixerReturn {
  const {
    buildCommand = 'npm run build',
    maxRetries = 3,
    onFixStart,
    onFixComplete,
    onFixError,
    onFileModified
  } = options

  // State
  const [isFixing, setIsFixing] = useState(false)
  const [lastResult, setLastResult] = useState<FixErrorResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Stores
  const projectStore = useProjectStore()
  const errorStore = useErrorStore()
  const terminalStore = useTerminalStore()

  /**
   * Fix a specific error
   */
  const fixError = useCallback(async (
    errorMessage: string,
    stackTrace?: string
  ): Promise<FixErrorResponse | null> => {
    const projectId = projectStore.currentProject?.id
    if (!projectId) {
      setError('No project selected')
      return null
    }

    setIsFixing(true)
    setError(null)
    onFixStart?.()

    // Log to terminal
    terminalStore.addLog({
      type: 'info',
      content: '🔧 SDK Fixer: Starting auto-fix...'
    })

    try {
      const result = await sdkService.fixError({
        project_id: projectId,
        error_message: errorMessage,
        stack_trace: stackTrace,
        build_command: buildCommand,
        max_retries: maxRetries
      })

      setLastResult(result)

      // Log result to terminal
      if (result.success && result.error_fixed) {
        terminalStore.addLog({
          type: 'info',
          content: `✅ SDK Fixer: Fixed in ${result.attempts} attempt(s)`
        })

        // Notify about modified files
        result.files_modified.forEach(filePath => {
          terminalStore.addLog({
            type: 'info',
            content: `   Modified: ${filePath}`
          })
          onFileModified?.(filePath)
        })

        // Mark errors as resolved in error store
        errorStore.clearErrors()
      } else {
        terminalStore.addLog({
          type: 'info',
          content: `⚠️ SDK Fixer: Could not fix automatically - ${result.message}`
        })
      }

      onFixComplete?.(result)
      return result

    } catch (err: any) {
      const errorMsg = err.message || 'Unknown error'
      setError(errorMsg)
      terminalStore.addLog({
        type: 'error',
        content: `❌ SDK Fixer Error: ${errorMsg}`
      })
      onFixError?.(err)
      return null

    } finally {
      setIsFixing(false)
    }
  }, [projectStore.currentProject?.id, buildCommand, maxRetries, terminalStore, errorStore, onFixStart, onFixComplete, onFixError, onFileModified])

  /**
   * Fix all current unresolved errors
   */
  const fixCurrentErrors = useCallback(async (): Promise<FixErrorResponse | null> => {
    const unresolvedErrors = errorStore.getUnresolvedErrors()

    if (unresolvedErrors.length === 0) {
      terminalStore.addLog({
        type: 'info',
        content: '✅ No errors to fix'
      })
      return null
    }

    // Combine all errors into one message
    const combinedError = unresolvedErrors
      .map(err => `${err.source}: ${err.message}${err.file ? ` (${err.file}:${err.line})` : ''}`)
      .join('\n')

    const combinedStack = unresolvedErrors
      .filter(err => err.stack)
      .map(err => err.stack)
      .join('\n---\n')

    return fixError(combinedError, combinedStack)
  }, [errorStore, terminalStore, fixError])

  /**
   * Fix with streaming progress updates
   */
  const fixWithStreaming = useCallback(async (
    errorMessage: string,
    onProgress?: (event: StreamEvent) => void
  ): Promise<void> => {
    const projectId = projectStore.currentProject?.id
    if (!projectId) {
      setError('No project selected')
      return
    }

    setIsFixing(true)
    setError(null)
    onFixStart?.()

    terminalStore.addLog({
      type: 'info',
      content: '🔧 SDK Fixer: Starting auto-fix (streaming)...'
    })

    try {
      await sdkService.fixErrorStream(
        {
          project_id: projectId,
          error_message: errorMessage,
          build_command: buildCommand,
          max_retries: maxRetries
        },
        (event) => {
          // Handle events
          if (event.type === 'start') {
            terminalStore.addLog({
              type: 'info',
              content: `   ${event.message}`
            })
          } else if (event.type === 'complete' && event.result) {
            setLastResult(event.result)
            onFixComplete?.(event.result)
          } else if (event.type === 'error') {
            setError(event.message || 'Unknown error')
            terminalStore.addLog({
              type: 'error',
              content: `❌ ${event.message}`
            })
          }

          onProgress?.(event)
        }
      )

    } catch (err: any) {
      setError(err.message)
      terminalStore.addLog({
        type: 'error',
        content: `❌ SDK Fixer Error: ${err.message}`
      })
      onFixError?.(err)

    } finally {
      setIsFixing(false)
    }
  }, [projectStore.currentProject?.id, buildCommand, maxRetries, terminalStore, onFixStart, onFixComplete, onFixError])

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    setIsFixing(false)
    setLastResult(null)
    setError(null)
  }, [])

  // ============================================
  // Tool Shortcuts
  // ============================================

  const runCommand = useCallback(async (command: string): Promise<string> => {
    const projectId = projectStore.currentProject?.id
    if (!projectId) throw new Error('No project selected')

    terminalStore.addLog({ type: 'command', content: command })
    const result = await sdkService.runBash(projectId, command)
    terminalStore.addLog({ type: 'output', content: result })
    return result
  }, [projectStore.currentProject?.id, terminalStore])

  const viewFile = useCallback(async (path: string): Promise<string> => {
    const projectId = projectStore.currentProject?.id
    if (!projectId) throw new Error('No project selected')
    return sdkService.viewFile(projectId, path)
  }, [projectStore.currentProject?.id])

  const searchFiles = useCallback(async (pattern: string): Promise<string> => {
    const projectId = projectStore.currentProject?.id
    if (!projectId) throw new Error('No project selected')
    return sdkService.grep(projectId, pattern)
  }, [projectStore.currentProject?.id])

  return {
    // State
    isFixing,
    lastResult,
    error,

    // Actions
    fixError,
    fixCurrentErrors,
    fixWithStreaming,
    reset,

    // Tool shortcuts
    runCommand,
    viewFile,
    searchFiles
  }
}

export default useSDKFixer
