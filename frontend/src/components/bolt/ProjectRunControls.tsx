'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Play,
  Square,
  RefreshCw,
  ExternalLink,
  Loader2,
  Terminal,
  Circle,
  CheckCircle2,
  XCircle,
  Container,
  Server,
  Wrench,
  Zap,
  RotateCcw,
  AlertTriangle
} from 'lucide-react'
import { useProjectStore } from '@/store/projectStore'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
const MAX_AUTO_FIX_ATTEMPTS = 3

type ExecutionMode = 'docker' | 'direct'
type RunStatus = 'idle' | 'creating' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error' | 'fixing'

interface ErrorInfo {
  message: string
  stackTrace: string
  detectedAt: Date
}

interface ProjectRunControlsProps {
  onOpenTerminal?: () => void
  onPreviewUrlChange?: (url: string | null) => void
  onOutput?: (line: string) => void
  autoFix?: boolean // Enable automatic error fixing
  onStartSession?: () => void  // Called when run starts to keep terminal open
  onEndSession?: () => void    // Called when run ends (terminal stays open)
}

export function ProjectRunControls({ onOpenTerminal, onPreviewUrlChange, onOutput, autoFix = true, onStartSession, onEndSession }: ProjectRunControlsProps) {
  const { currentProject, loadFromBackend } = useProjectStore()
  const [status, setStatus] = useState<RunStatus>('idle')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [executionMode, setExecutionMode] = useState<ExecutionMode>('docker')
  const [dockerAvailable, setDockerAvailable] = useState<boolean | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Auto-fix state
  const [lastError, setLastError] = useState<ErrorInfo | null>(null)
  const [fixAttempts, setFixAttempts] = useState(0)
  const [isFixing, setIsFixing] = useState(false)
  const [maxAttemptsReached, setMaxAttemptsReached] = useState(false)
  const errorBufferRef = useRef<string[]>([]) // Collect error lines

  // Check if Docker is available on mount
  useEffect(() => {
    checkDockerAvailability()
  }, [])

  const checkDockerAvailability = async () => {
    try {
      // Try to create a test container - if it fails, Docker is not available
      const response = await fetch(`${API_BASE_URL}/containers/test-docker/status`, {
        method: 'GET',
      })
      // If we get 404, that's fine - Docker is available but no container exists
      // If we get 500 with "Docker not available", Docker is not installed
      if (response.status === 500) {
        const error = await response.json()
        if (error.detail?.includes('Docker')) {
          setDockerAvailable(false)
          setExecutionMode('direct')
          return
        }
      }
      setDockerAvailable(true)
    } catch (e) {
      // Network error or backend down - assume Docker might be available
      setDockerAvailable(true)
    }
  }

  // Detect project type from files
  const detectProjectType = useCallback((): 'node' | 'python' | 'static' => {
    if (!currentProject?.files) return 'node'

    const hasPackageJson = currentProject.files.some(f => f.path === 'package.json')
    const hasRequirements = currentProject.files.some(f => f.path === 'requirements.txt')
    const hasIndexHtml = currentProject.files.some(f => f.path === 'index.html')

    if (hasPackageJson) return 'node'
    if (hasRequirements) return 'python'
    if (hasIndexHtml) return 'static'
    return 'node'
  }, [currentProject?.files])

  // Detect server start from output
  const detectServerStart = useCallback((output: string) => {
    const serverPatterns = [
      /https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)/i,
      /running\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /server\s+(?:started|listening|running)\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /listening\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)/i,
      /local:\s*https?:\/\/.*:(\d+)/i,
    ]

    for (const pattern of serverPatterns) {
      const match = output.match(pattern)
      if (match && match[1]) {
        const port = match[1]
        const url = `http://localhost:${port}`
        setPreviewUrl(url)
        setStatus('running')
        onPreviewUrlChange?.(url)
        return true
      }
    }
    return false
  }, [onPreviewUrlChange])

  // ============= ERROR DETECTION =============
  const detectError = useCallback((output: string): boolean => {
    const errorPatterns = [
      /error:/i,
      /exception:/i,
      /traceback/i,
      /syntaxerror/i,
      /typeerror/i,
      /referenceerror/i,
      /modulenotfound/i,
      /importerror/i,
      /failed to compile/i,
      /build failed/i,
      /cannot find module/i,
      /unexpected token/i,
      /command failed/i,
      /exited with code [1-9]/i,
    ]

    for (const pattern of errorPatterns) {
      if (pattern.test(output)) {
        // Add to error buffer
        errorBufferRef.current.push(output)
        // Keep last 20 lines for context
        if (errorBufferRef.current.length > 20) {
          errorBufferRef.current.shift()
        }
        return true
      }
    }
    return false
  }, [])

  // Reset fix state
  const resetFixState = useCallback(() => {
    setFixAttempts(0)
    setLastError(null)
    setMaxAttemptsReached(false)
    errorBufferRef.current = []
  }, [])

  // ============= AUTO-FIX HANDLER =============
  const attemptAutoFix = useCallback(async (errorMessage: string, stackTrace: string) => {
    if (!currentProject?.id || !autoFix) {
      return false
    }

    if (fixAttempts >= MAX_AUTO_FIX_ATTEMPTS) {
      setMaxAttemptsReached(true)
      onOutput?.(`\n❌ Max auto-fix attempts (${MAX_AUTO_FIX_ATTEMPTS}) reached.`)
      onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      onOutput?.('🔴 AUTO-FIX FAILED - Manual intervention required')
      onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      onOutput?.('\n💡 Options:')
      onOutput?.('   1. Review the error message above')
      onOutput?.('   2. Edit the file manually in the Code Editor')
      onOutput?.('   3. Click "Retry Fix" to reset and try again')
      onOutput?.('   4. Ask AI in chat to help fix this error')
      onOutput?.('\n📋 Error Summary:')
      onOutput?.(`   ${errorMessage.slice(0, 200)}...`)
      return false
    }

    setIsFixing(true)
    setStatus('fixing')
    setFixAttempts(prev => prev + 1)
    onOutput?.(`\n🔧 Auto-Fix Attempt ${fixAttempts + 1}/${MAX_AUTO_FIX_ATTEMPTS}...`)
    onOutput?.('🤖 AI Fixer Agent analyzing error...')

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${API_BASE_URL}/execution/fix/${currentProject.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          error_message: errorMessage,
          stack_trace: stackTrace,
        })
      })

      if (!response.ok) {
        const error = await response.json()
        onOutput?.(`❌ Fix failed: ${error.detail || 'Unknown error'}`)
        setIsFixing(false)
        setStatus('error')
        return false
      }

      const result = await response.json()

      if (!result.success) {
        onOutput?.(`❌ Fixer Agent: ${result.error || 'Could not generate fix'}`)
        if (result.suggestion) {
          onOutput?.(`💡 Suggestion: ${result.suggestion}`)
        }
        setIsFixing(false)
        setStatus('error')
        return false
      }

      // Log fixed files
      const fixedFiles = result.fixed_files || []
      onOutput?.(`✅ Fixed ${fixedFiles.length} file(s):`)
      for (const file of fixedFiles) {
        onOutput?.(`   📄 ${file.path}`)
      }

      // Run instructions if any
      if (result.instructions) {
        onOutput?.(`📋 Running: ${result.instructions}`)
      }

      // Reload project files to reflect changes
      try {
        const { apiClient } = await import('@/lib/api-client')
        const projectData = await apiClient.getProject(currentProject.id)
        loadFromBackend(projectData)
        onOutput?.('🔄 Project files reloaded')
      } catch (e) {
        onOutput?.('⚠️ Could not reload project files')
      }

      setIsFixing(false)
      setLastError(null)
      errorBufferRef.current = []

      // Auto-restart after fix
      onOutput?.('\n🚀 Restarting project with fixes...\n')
      return true

    } catch (error: any) {
      onOutput?.(`❌ Auto-fix error: ${error.message}`)
      setIsFixing(false)
      setStatus('error')
      return false
    }
  }, [currentProject?.id, autoFix, fixAttempts, onOutput, loadFromBackend])

  // ============= DOCKER EXECUTION =============
  const runWithDocker = async (): Promise<boolean> => {
    if (!currentProject?.id) return false

    onOutput?.('🐳 Starting Docker container...')

    try {
      // Step 1: Create container
      const createResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_type: detectProjectType(),
          memory_limit: '512m',
          cpu_limit: 0.5,
        }),
      })

      if (!createResponse.ok) {
        const error = await createResponse.json()
        throw new Error(error.detail || 'Failed to create container')
      }

      const container = await createResponse.json()
      onOutput?.(`✅ Container created: ${container.container_id}`)
      setStatus('starting')

      // Step 2: Execute commands
      const commands = detectProjectType() === 'node'
        ? ['npm install', 'npm run dev']
        : detectProjectType() === 'python'
        ? ['pip install -r requirements.txt', 'python main.py']
        : ['python -m http.server 3000']

      for (const command of commands) {
        onOutput?.(`$ ${command}`)

        const execResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/exec`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command, timeout: 600 }),
          signal: abortControllerRef.current?.signal,
        })

        if (!execResponse.ok) {
          throw new Error('Failed to execute command')
        }

        // Stream output
        const reader = execResponse.body?.getReader()
        if (!reader) continue

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
                if (event.type === 'stdout' || event.type === 'stderr') {
                  const text = String(event.data)
                  onOutput?.(text)
                  detectServerStart(text)
                }
              } catch {}
            }
          }
        }
      }

      // Get preview URL
      const previewResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/preview?port=3000`)
      if (previewResponse.ok) {
        const { url } = await previewResponse.json()
        setPreviewUrl(url)
        onPreviewUrlChange?.(url)
      }

      setStatus('running')
      return true

    } catch (error: any) {
      if (error.name === 'AbortError') return false

      // Check if Docker-specific error
      const errorMsg = error.message || ''
      if (errorMsg.includes('Docker') || errorMsg.includes('container') || errorMsg.includes('daemon')) {
        onOutput?.(`⚠️ Docker error: ${errorMsg}`)
        onOutput?.('🔄 Falling back to direct execution...')
        setDockerAvailable(false)
        setExecutionMode('direct')
        return false // Signal to try direct execution
      }

      throw error
    }
  }

  // ============= DIRECT EXECUTION (FALLBACK) =============
  const runDirect = async (): Promise<boolean> => {
    if (!currentProject?.id) return false

    onOutput?.('🖥️ Running directly on server...')
    onOutput?.(`📂 Project ID: ${currentProject.id}`)
    errorBufferRef.current = [] // Reset error buffer

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(`${API_BASE_URL}/execution/run/${currentProject.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ project_id: currentProject.id }),
        signal: abortControllerRef.current?.signal,
      })

      if (!response.ok) {
        const errorText = await response.text()
        onOutput?.(`❌ Server error: ${response.status}`)
        if (response.status === 404) {
          onOutput?.('📁 Project files not found on server.')
          onOutput?.('💡 The project may have been cleaned up. Try regenerating it.')
        } else {
          onOutput?.(`Details: ${errorText}`)
        }
        throw new Error(`Failed to start project: ${response.status}`)
      }

      setStatus('running')

      // Stream output
      const reader = response.body?.getReader()
      if (!reader) return false

      const decoder = new TextDecoder()
      let buffer = ''
      let hasError = false
      let errorOutput = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.type === 'output') {
                const content = data.data?.output || data.content || ''
                onOutput?.(content)
                detectServerStart(content)

                // Check for errors
                if (detectError(content)) {
                  hasError = true
                  errorOutput += content + '\n'
                }
              } else if (data.type === 'error') {
                const content = data.data?.error || data.content || ''
                onOutput?.(`❌ ${content}`)
                hasError = true
                errorOutput += content + '\n'
                errorBufferRef.current.push(content)
              } else if (data.type === 'server_started') {
                // Use preview_url from Docker if available, otherwise construct from port
                const url = data.preview_url || `http://localhost:${data.port || 3000}`
                setPreviewUrl(url)
                onPreviewUrlChange?.(url)
                hasError = false // Server started successfully
                onOutput?.(`🚀 Server running at: ${url}`)
              } else if (data.type === 'command_complete' && data.data?.success === false) {
                hasError = true
                onOutput?.(`❌ Command failed with exit code ${data.data?.exit_code}`)
              }
            } catch {}
          }
        }
      }

      // If errors detected, save for potential fix
      if (hasError) {
        const fullError = errorOutput || errorBufferRef.current.join('\n')
        setLastError({
          message: fullError.slice(0, 500),
          stackTrace: fullError,
          detectedAt: new Date()
        })

        // Return 'needs_fix' indicator for main handler to process
        return false
      }

      return true

    } catch (error: any) {
      if (error.name === 'AbortError') return false
      throw error
    }
  }

  // ============= MAIN RUN HANDLER =============
  const handleRun = useCallback(async () => {
    // Check if project exists
    if (!currentProject?.id) {
      onOutput?.('❌ No project selected. Generate a project first!')
      onOpenTerminal?.()
      onStartSession?.()  // Keep terminal open even for error
      return
    }

    // Check if user is authenticated
    const token = localStorage.getItem('access_token')
    if (!token) {
      onOutput?.('❌ Please log in to run projects.')
      onOpenTerminal?.()
      onStartSession?.()  // Keep terminal open even for error
      return
    }

    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    setStatus('creating')
    setPreviewUrl(null)

    // Start session - opens terminal and keeps it open
    onStartSession?.()
    onOpenTerminal?.()

    try {
      let success = false

      // Try Docker first (if available)
      if (executionMode === 'docker' && dockerAvailable !== false) {
        try {
          success = await runWithDocker()
        } catch (error: any) {
          onOutput?.(`⚠️ Docker failed: ${error.message}`)
          onOutput?.('🔄 Switching to direct execution...')
          setExecutionMode('direct')
          setDockerAvailable(false)
        }
      }

      // Fallback to direct execution
      if (!success && (executionMode === 'direct' || dockerAvailable === false)) {
        setStatus('starting')
        success = await runDirect()
      }

      if (success) {
        setStatus('running')
        // Reset fix state on success
        resetFixState()
        onOutput?.('\n✅ Project is running successfully!')
      } else {
        // Execution failed - try auto-fix if enabled
        if (autoFix && fixAttempts < MAX_AUTO_FIX_ATTEMPTS && lastError) {
          onOutput?.('\n🤖 Attempting auto-fix...')
          const fixSuccess = await attemptAutoFix(lastError.message, lastError.stackTrace)

          if (fixSuccess) {
            // Recursively try running again after fix
            setTimeout(() => {
              handleRun()
            }, 1000)
            return
          }
        }
        setStatus('error')
        onOutput?.('\n❌ Execution completed with errors. Check the output above.')
      }

      // End session but keep terminal open
      onEndSession?.()

    } catch (error: any) {
      console.error('Run error:', error)
      onOutput?.(`❌ Error: ${error.message}`)
      onOutput?.('\n💡 Tips:')
      onOutput?.('   - Make sure the project was generated successfully')
      onOutput?.('   - Check that all files are present')
      onOutput?.('   - Try regenerating the project')
      setStatus('error')
      onEndSession?.()  // Keep terminal open to show error
    }
  }, [currentProject?.id, executionMode, dockerAvailable, detectProjectType, onOutput, onPreviewUrlChange, detectServerStart, autoFix, fixAttempts, lastError, attemptAutoFix, onStartSession, onEndSession])

  // ============= STOP HANDLER =============
  const handleStop = useCallback(async () => {
    setStatus('stopping')

    // Abort current execution
    abortControllerRef.current?.abort()

    try {
      const token = localStorage.getItem('access_token')

      // Try to stop container (if Docker mode)
      if (executionMode === 'docker') {
        await fetch(`${API_BASE_URL}/containers/${currentProject?.id}/stop`, {
          method: 'POST',
        }).catch(() => {})
      }

      // Also try direct stop endpoint
      await fetch(`${API_BASE_URL}/execution/stop/${currentProject?.id}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      }).catch(() => {})

    } catch {}

    setStatus('stopped')
    setPreviewUrl(null)
    onPreviewUrlChange?.(null)
    onOutput?.('🛑 Project stopped')
  }, [currentProject?.id, executionMode, onPreviewUrlChange, onOutput])

  // Restart
  const handleRestart = useCallback(async () => {
    await handleStop()
    setTimeout(() => handleRun(), 500)
  }, [handleStop, handleRun])

  // Manual fix handler
  const handleManualFix = useCallback(async () => {
    if (!lastError) {
      onOutput?.('⚠️ No error to fix. Run the project first to detect errors.')
      return
    }
    await attemptAutoFix(lastError.message, lastError.stackTrace)
  }, [lastError, attemptAutoFix, onOutput])

  // Get status info
  const getStatusInfo = (status: RunStatus) => {
    switch (status) {
      case 'idle':
        return { icon: Circle, color: 'text-gray-400', label: 'Idle', bgColor: 'bg-gray-400' }
      case 'creating':
        return { icon: Container, color: 'text-blue-500', label: 'Creating...', bgColor: 'bg-blue-500' }
      case 'starting':
        return { icon: Loader2, color: 'text-yellow-500', label: 'Starting...', bgColor: 'bg-yellow-500' }
      case 'running':
        return { icon: CheckCircle2, color: 'text-green-500', label: 'Running', bgColor: 'bg-green-500' }
      case 'stopping':
        return { icon: Loader2, color: 'text-orange-500', label: 'Stopping...', bgColor: 'bg-orange-500' }
      case 'stopped':
        return { icon: Circle, color: 'text-gray-400', label: 'Stopped', bgColor: 'bg-gray-400' }
      case 'fixing':
        return { icon: Wrench, color: 'text-purple-500', label: 'Fixing...', bgColor: 'bg-purple-500' }
      case 'error':
        return { icon: XCircle, color: 'text-red-500', label: 'Error', bgColor: 'bg-red-500' }
      default:
        return { icon: Circle, color: 'text-gray-400', label: 'Unknown', bgColor: 'bg-gray-400' }
    }
  }

  const statusInfo = getStatusInfo(status)
  const isRunning = status === 'running'
  const isLoading = status === 'creating' || status === 'starting' || status === 'stopping' || status === 'fixing'
  const canRun = !isLoading && !isRunning && currentProject
  const hasFixableError = status === 'error' && lastError && fixAttempts < MAX_AUTO_FIX_ATTEMPTS

  return (
    <div className="flex items-center gap-2">
      {/* Execution Mode Indicator */}
      <div
        className={`flex items-center gap-1 px-2 py-1 rounded-md ${
          executionMode === 'docker' ? 'bg-blue-500/10 text-blue-400' : 'bg-orange-500/10 text-orange-400'
        }`}
        title={executionMode === 'docker'
          ? 'Running in Docker container (isolated & secure)'
          : 'Running directly on server (Docker unavailable)'
        }
      >
        {executionMode === 'docker' ? <Container className="w-3 h-3" /> : <Server className="w-3 h-3" />}
        <span className="text-xs font-medium">{executionMode === 'docker' ? 'Docker' : 'Direct'}</span>
      </div>

      {/* Status Indicator */}
      <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-[hsl(var(--bolt-bg-secondary))]">
        <div className={`w-2 h-2 rounded-full ${statusInfo.bgColor} ${isRunning ? 'animate-pulse' : ''}`} />
        <span className={`text-xs font-medium ${statusInfo.color}`}>
          {statusInfo.label}
        </span>
      </div>

      {/* Run/Stop Buttons */}
      {!isRunning && !isLoading ? (
        <button
          onClick={handleRun}
          disabled={!canRun}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
            bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:opacity-50
            text-white text-sm font-medium transition-colors"
          title="Run Project"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run</span>
        </button>
      ) : isLoading ? (
        <button
          disabled
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md
            ${status === 'fixing' ? 'bg-purple-600' : 'bg-yellow-600'} text-white text-sm font-medium opacity-75`}
        >
          {status === 'fixing' ? <Wrench className="w-3.5 h-3.5 animate-spin" /> : <Loader2 className="w-3.5 h-3.5 animate-spin" />}
          <span>
            {status === 'creating' ? 'Creating...' :
             status === 'starting' ? 'Starting...' :
             status === 'fixing' ? 'Fixing...' :
             'Stopping...'}
          </span>
        </button>
      ) : (
        <button
          onClick={handleStop}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
            bg-red-600 hover:bg-red-700 text-white text-sm font-medium transition-colors"
          title="Stop Project"
        >
          <Square className="w-3.5 h-3.5" />
          <span>Stop</span>
        </button>
      )}

      {/* Fix Button - Shows when there's a fixable error */}
      {hasFixableError && !maxAttemptsReached && (
        <button
          onClick={handleManualFix}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
            bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium transition-colors"
          title={`Auto-fix error (${fixAttempts}/${MAX_AUTO_FIX_ATTEMPTS} attempts)`}
        >
          <Zap className="w-3.5 h-3.5" />
          <span>Fix ({fixAttempts}/{MAX_AUTO_FIX_ATTEMPTS})</span>
        </button>
      )}

      {/* Max Attempts Reached - Show warning and retry option */}
      {maxAttemptsReached && (
        <>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-red-500/10 text-red-400">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Fix Failed</span>
          </div>
          <button
            onClick={() => {
              resetFixState()
              onOutput?.('\n🔄 Fix attempts reset. You can try again or edit manually.')
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
              bg-orange-600 hover:bg-orange-700 text-white text-sm font-medium transition-colors"
            title="Reset fix attempts and try again"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Fix</span>
          </button>
        </>
      )}

      {/* Restart Button */}
      {isRunning && (
        <button
          onClick={handleRestart}
          className="flex items-center justify-center w-8 h-8 rounded-md
            bg-[hsl(var(--bolt-bg-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
            text-[hsl(var(--bolt-text-secondary))] transition-colors"
          title="Restart"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      )}

      {/* Preview URL */}
      {previewUrl && (
        <a
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-md
            bg-[hsl(var(--bolt-accent)/0.1)] text-[hsl(var(--bolt-accent))]
            text-xs font-medium hover:bg-[hsl(var(--bolt-accent)/0.2)] transition-colors"
          title={`Open ${previewUrl}`}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>Preview</span>
        </a>
      )}

      {/* Terminal Toggle */}
      <button
        onClick={onOpenTerminal}
        className="flex items-center justify-center w-8 h-8 rounded-md
          bg-[hsl(var(--bolt-bg-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
          text-[hsl(var(--bolt-text-secondary))] transition-colors"
        title="Toggle Terminal"
      >
        <Terminal className="w-4 h-4" />
      </button>
    </div>
  )
}
