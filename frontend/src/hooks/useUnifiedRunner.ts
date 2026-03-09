/**
 * Unified Runner Hook
 * ====================
 * Automatically chooses between WebContainer (browser) and Docker (server)
 * based on project type. Includes auto-fix capability for both.
 *
 * For Node.js projects: Uses WebContainer (zero server cost)
 * For Python/Java/etc: Uses Docker sandbox (server-side)
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import { useWebContainer } from './useWebContainer'
import { useProjectStore } from '@/store/projectStore'
import { isWebContainerSupported } from '@/lib/webcontainer'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const MAX_AUTO_FIX_ATTEMPTS = 6

export type RunnerType = 'webcontainer' | 'docker' | 'detecting'
export type RunnerStatus = 'idle' | 'detecting' | 'booting' | 'installing' | 'starting' | 'running' | 'fixing' | 'error' | 'stopped'

interface ErrorInfo {
  message: string
  stackTrace: string
  timestamp: Date
}

interface UseUnifiedRunnerOptions {
  onOutput?: (line: string) => void
  onPreviewReady?: (url: string) => void
  onError?: (error: string) => void
  autoFix?: boolean
}

interface UseUnifiedRunnerReturn {
  // State
  status: RunnerStatus
  runnerType: RunnerType
  previewUrl: string | null
  output: string[]
  isRunning: boolean
  isLoading: boolean
  fixAttempts: number
  maxAttemptsReached: boolean

  // Actions
  run: () => Promise<void>
  stop: () => Promise<void>
  restart: () => Promise<void>
  clearOutput: () => void
}

export function useUnifiedRunner(options: UseUnifiedRunnerOptions = {}): UseUnifiedRunnerReturn {
  const { onOutput, onPreviewReady, onError, autoFix = true } = options

  const { currentProject, loadFromBackend } = useProjectStore()

  // State
  const [status, setStatus] = useState<RunnerStatus>('idle')
  const [runnerType, setRunnerType] = useState<RunnerType>('detecting')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [output, setOutput] = useState<string[]>([])
  const [fixAttempts, setFixAttempts] = useState(0)
  const [maxAttemptsReached, setMaxAttemptsReached] = useState(false)
  const [lastError, setLastError] = useState<ErrorInfo | null>(null)

  // Refs
  const fixAttemptsRef = useRef(0)
  const isFixingRef = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)
  const errorBufferRef = useRef<string[]>([])

  // WebContainer hook
  const webContainer = useWebContainer()

  // Add output line
  const addOutput = useCallback((line: string) => {
    setOutput(prev => [...prev, line])
    onOutput?.(line)
  }, [onOutput])

  // Clear output
  const clearOutput = useCallback(() => {
    setOutput([])
    errorBufferRef.current = []
  }, [])

  // Detect if project can use WebContainer
  const canUseWebContainer = useCallback((): boolean => {
    if (!isWebContainerSupported()) {
      addOutput('⚠️ WebContainer not supported in this browser')
      return false
    }

    if (!currentProject?.files) return false

    // Check for Node.js project indicators
    const hasPackageJson = currentProject.files.some(f => f.path === 'package.json')
    const hasPythonFiles = currentProject.files.some(f => f.path.endsWith('.py'))
    const hasJavaFiles = currentProject.files.some(f => f.path.endsWith('.java'))
    const hasGoFiles = currentProject.files.some(f => f.path.endsWith('.go'))
    const hasRustFiles = currentProject.files.some(f => f.path.endsWith('.rs'))
    const hasFlutterFiles = currentProject.files.some(f => f.path === 'pubspec.yaml')

    // WebContainer only supports Node.js
    if (hasPackageJson && !hasPythonFiles && !hasJavaFiles && !hasGoFiles && !hasRustFiles && !hasFlutterFiles) {
      return true
    }

    return false
  }, [currentProject?.files, addOutput])

  // Detect errors in output
  const detectError = useCallback((text: string): boolean => {
    const errorPatterns = [
      /error:/i,
      /failed to compile/i,
      /syntaxerror/i,
      /typeerror/i,
      /referenceerror/i,
      /cannot find module/i,
      /module not found/i,
      /unexpected token/i,
      /npm ERR!/i,
      /ENOENT/i,
    ]

    // Ignore patterns (false positives)
    const ignorePatterns = [
      /npm WARN/i,
      /deprecation/i,
      /ExperimentalWarning/i,
    ]

    for (const ignore of ignorePatterns) {
      if (ignore.test(text)) return false
    }

    for (const pattern of errorPatterns) {
      if (pattern.test(text)) {
        errorBufferRef.current.push(text)
        return true
      }
    }
    return false
  }, [])

  // Auto-fix errors (works for both WebContainer and Docker)
  const attemptAutoFix = useCallback(async (errorMessage: string): Promise<boolean> => {
    if (!currentProject?.id || !autoFix || isFixingRef.current) {
      return false
    }

    if (fixAttemptsRef.current >= MAX_AUTO_FIX_ATTEMPTS) {
      setMaxAttemptsReached(true)
      addOutput(`\n❌ Max auto-fix attempts (${MAX_AUTO_FIX_ATTEMPTS}) reached.`)
      return false
    }

    isFixingRef.current = true
    fixAttemptsRef.current += 1
    setFixAttempts(fixAttemptsRef.current)
    setStatus('fixing')

    addOutput('\n🔧 Fixing issue...')

    try {
      const token = localStorage.getItem('access_token')

      const response = await fetch(`${API_BASE_URL}/execution/fix/${currentProject.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          error_message: errorMessage.slice(0, 500),
          stack_trace: errorMessage,
          error_logs: errorBufferRef.current.slice(-20),
        })
      })

      if (!response.ok) {
        const error = await response.json()
        addOutput(`❌ Fix failed: ${error.detail || 'Unknown error'}`)
        isFixingRef.current = false
        return false
      }

      const result = await response.json()

      if (!result.success) {
        addOutput(`❌ AI could not generate fix: ${result.error || 'Unknown error'}`)
        isFixingRef.current = false
        return false
      }

      // Apply fixes
      const fixedFiles = result.fixed_files || []

      for (const file of fixedFiles) {

        // Apply fix based on runner type
        if (runnerType === 'webcontainer' && webContainer.isReady) {
          // Write to WebContainer virtual filesystem
          await webContainer.writeFile(file.path, file.content)
        }
        // For Docker, files are already updated on server by the fix endpoint
      }

      // Reload project files in store
      try {
        const { apiClient } = await import('@/lib/api-client')
        const projectData = await apiClient.loadProjectWithFiles(currentProject.id)
        loadFromBackend(projectData)
      } catch (e) {
        // Silently continue
      }

      isFixingRef.current = false
      setLastError(null)
      errorBufferRef.current = []

      addOutput('✅ Fixed! Restarting...')
      return true

    } catch (error: any) {
      addOutput(`❌ Auto-fix error: ${error.message}`)
      isFixingRef.current = false
      return false
    }
  }, [currentProject?.id, autoFix, runnerType, webContainer, addOutput, loadFromBackend])

  // Get files as flat object for WebContainer
  const getFilesForWebContainer = useCallback(async (): Promise<Record<string, string>> => {
    if (!currentProject?.id) return {}

    try {
      const { apiClient } = await import('@/lib/api-client')
      const projectData = await apiClient.loadProjectWithFiles(currentProject.id)

      const files: Record<string, string> = {}
      if (projectData?.files) {
        for (const file of projectData.files) {
          if (!file.is_folder && file.content !== undefined) {
            files[file.path] = file.content
          }
        }
      }
      return files
    } catch (error) {
      addOutput(`⚠️ Could not load files: ${error}`)
      return {}
    }
  }, [currentProject?.id, addOutput])

  // Run with WebContainer
  const runWithWebContainer = useCallback(async (): Promise<boolean> => {
    addOutput('🚀 Starting project...')
    setStatus('booting')

    try {
      // Check if SharedArrayBuffer is available (required for WebContainer)
      if (typeof SharedArrayBuffer === 'undefined') {
        addOutput('⚠️ WebContainer requires special browser headers.')
        addOutput('💡 Please refresh the page or try a different browser.')
        addOutput('')
        addOutput('📋 Technical details:')
        addOutput('   - SharedArrayBuffer is not available')
        addOutput('   - COOP/COEP headers may not be configured')
        setStatus('error')
        return false
      }

      // Initialize if needed
      if (!webContainer.isReady) {
        addOutput('⏳ Initializing WebContainer...')
        const initialized = await webContainer.init()
        if (!initialized) {
          addOutput('❌ WebContainer initialization failed')
          addOutput('💡 Try refreshing the page or check browser console for errors')
          setStatus('error')
          return false
        }
      }

      // Load and mount files
      const files = await getFilesForWebContainer()

      if (Object.keys(files).length === 0) {
        addOutput('❌ No files found')
        return false
      }

      addOutput(`📁 Loading ${Object.keys(files).length} files...`)
      setStatus('installing')

      // Run the project (mount + install + start)
      const serverUrl = await webContainer.runProject(files)

      if (serverUrl) {
        setPreviewUrl(serverUrl)
        setStatus('running')
        addOutput(`\n🚀 Server running at: ${serverUrl}`)
        onPreviewReady?.(serverUrl)
        return true
      }

      // Check for errors in output
      const hasErrors = webContainer.output.some(line => detectError(line))
      if (hasErrors) {
        const errorText = errorBufferRef.current.join('\n')
        setLastError({
          message: errorText.slice(0, 500),
          stackTrace: errorText,
          timestamp: new Date()
        })
        return false
      }

      return false

    } catch (error: any) {
      addOutput(`❌ WebContainer error: ${error.message}`)
      return false
    }
  }, [webContainer, getFilesForWebContainer, addOutput, onPreviewReady, detectError])

  // Run with Docker (fallback)
  const runWithDocker = useCallback(async (): Promise<boolean> => {
    if (!currentProject?.id) return false

    addOutput('🚀 Starting project...')
    setStatus('booting')

    const token = localStorage.getItem('access_token')

    try {
      // Create container
      const createResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          project_type: 'node',
          memory_limit: '512m',
          cpu_limit: 0.5,
        }),
        signal: abortControllerRef.current?.signal,
      })

      if (!createResponse.ok) {
        const error = await createResponse.json()
        addOutput(`❌ Failed to create container: ${error.detail}`)
        return false
      }

      const container = await createResponse.json()

      // Sync files silently
      const syncResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/files/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          files: currentProject.files?.map(f => ({
            path: f.path,
            content: f.content || ''
          })) || []
        })
      })

      if (!syncResponse.ok) {
        addOutput('⚠️ File sync failed, continuing...')
      }

      // Run npm install
      setStatus('installing')
      addOutput('📦 Installing dependencies...')

      const installResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/exec`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({ command: 'npm install', timeout: 120 }),
        signal: abortControllerRef.current?.signal,
      })

      if (installResponse.ok) {
        await processSSEStream(installResponse)
      }

      // Run dev server
      setStatus('starting')
      addOutput('🔄 Starting server...')

      const devResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/exec`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({ command: 'npm run dev', timeout: 600 }),
        signal: abortControllerRef.current?.signal,
      })

      if (devResponse.ok) {
        const serverStarted = await processSSEStream(devResponse, true)
        if (serverStarted) {
          setStatus('running')
          return true
        }
      }

      return false

    } catch (error: any) {
      if (error.name === 'AbortError') return false
      addOutput(`❌ Docker error: ${error.message}`)
      return false
    }
  }, [currentProject, addOutput])

  // Process SSE stream from Docker
  const processSSEStream = useCallback(async (response: Response, detectServer = false): Promise<boolean> => {
    const reader = response.body?.getReader()
    if (!reader) return false

    const decoder = new TextDecoder()
    let buffer = ''
    let serverStarted = false
    let hasError = false

    try {
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
              const text = event.data ? String(event.data) : ''

              if (event.type === 'stdout' || event.type === 'stderr') {
                addOutput(text)

                if (detectError(text)) {
                  hasError = true
                  errorBufferRef.current.push(text)
                }

                // Detect server start
                if (detectServer) {
                  const serverPatterns = [
                    /Local:\s*https?:\/\/.*:(\d+)/i,
                    /ready in \d+/i,
                    /listening on.*:(\d+)/i,
                  ]
                  for (const pattern of serverPatterns) {
                    if (pattern.test(text)) {
                      serverStarted = true
                    }
                  }
                }
              }

              if (event.type === 'error') {
                addOutput(`❌ ${text}`)
                hasError = true
              }

              if (event.type === 'done' && event.exit_code !== 0) {
                hasError = true
              }
            } catch {}
          }
        }

        if (serverStarted) break
      }
    } catch (e) {
      // Stream ended
    }

    if (hasError && !serverStarted) {
      setLastError({
        message: errorBufferRef.current.slice(-5).join('\n'),
        stackTrace: errorBufferRef.current.join('\n'),
        timestamp: new Date()
      })
    }

    return serverStarted
  }, [addOutput, detectError])

  // Main run function
  const run = useCallback(async () => {
    if (!currentProject?.id) {
      addOutput('❌ No project selected')
      return
    }

    // Reset state
    clearOutput()
    setStatus('detecting')
    setPreviewUrl(null)
    setLastError(null)
    fixAttemptsRef.current = 0
    setFixAttempts(0)
    setMaxAttemptsReached(false)
    errorBufferRef.current = []

    abortControllerRef.current = new AbortController()

    // Determine runner type silently - no technical details for user
    const useWebContainer = canUseWebContainer()
    setRunnerType(useWebContainer ? 'webcontainer' : 'docker')

    let success = false
    let attempts = 0

    // Run with auto-fix loop
    while (!success && attempts <= MAX_AUTO_FIX_ATTEMPTS) {

      // Run project - try WebContainer first, fallback to Docker if it fails
      if (useWebContainer) {
        success = await runWithWebContainer()

        // If WebContainer failed to initialize, try Docker as fallback
        if (!success && status === 'error') {
          addOutput('\n🔄 Falling back to Docker...\n')
          setRunnerType('docker')
          success = await runWithDocker()
        }
      } else {
        success = await runWithDocker()
      }

      if (success) {
        addOutput('\n✅ Running!')
        break
      }

      // Check for errors and try to fix
      if (lastError && autoFix && fixAttemptsRef.current < MAX_AUTO_FIX_ATTEMPTS) {
        const fixed = await attemptAutoFix(lastError.stackTrace)

        if (fixed) {
          attempts++
          // Small delay before retry
          await new Promise(resolve => setTimeout(resolve, 1500))
          continue
        }
      }

      // No error to fix or fix failed
      break
    }

    if (!success) {
      setStatus('error')
      if (maxAttemptsReached) {
        addOutput('\n❌ Could not fix automatically. Please check the errors above.')
      }
    }

  }, [currentProject?.id, canUseWebContainer, runWithWebContainer, runWithDocker, attemptAutoFix, autoFix, lastError, maxAttemptsReached, addOutput, clearOutput])

  // Stop
  const stop = useCallback(async () => {
    addOutput('🛑 Stopping...')

    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    if (runnerType === 'webcontainer') {
      await webContainer.stopServer()
    } else if (currentProject?.id) {
      const token = localStorage.getItem('access_token')
      try {
        await fetch(`${API_BASE_URL}/containers/${currentProject.id}/stop`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        })
      } catch {}
    }

    setStatus('stopped')
    setPreviewUrl(null)
    addOutput('🛑 Stopped')
  }, [runnerType, webContainer, currentProject?.id, addOutput])

  // Restart
  const restart = useCallback(async () => {
    await stop()
    await new Promise(resolve => setTimeout(resolve, 500))
    await run()
  }, [stop, run])

  // Sync WebContainer output to our output state
  useEffect(() => {
    if (runnerType === 'webcontainer' && webContainer.output.length > 0) {
      const lastLine = webContainer.output[webContainer.output.length - 1]
      if (!output.includes(lastLine)) {
        setOutput(prev => [...prev, lastLine])
      }
    }
  }, [runnerType, webContainer.output, output])

  // Sync WebContainer server URL
  useEffect(() => {
    if (runnerType === 'webcontainer' && webContainer.serverUrl && !previewUrl) {
      setPreviewUrl(webContainer.serverUrl)
      setStatus('running')
      onPreviewReady?.(webContainer.serverUrl)
    }
  }, [runnerType, webContainer.serverUrl, previewUrl, onPreviewReady])

  return {
    // State
    status,
    runnerType,
    previewUrl,
    output,
    isRunning: status === 'running',
    isLoading: ['detecting', 'booting', 'installing', 'starting', 'fixing'].includes(status),
    fixAttempts,
    maxAttemptsReached,

    // Actions
    run,
    stop,
    restart,
    clearOutput,
  }
}

export default useUnifiedRunner
