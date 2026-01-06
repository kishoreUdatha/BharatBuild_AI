import { useState, useCallback, useRef } from 'react'
import { streamingClient, StreamEvent } from '@/lib/streaming-client'
import { useProjectStore } from '@/store/projectStore'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// ============= AUTO-RUN SYSTEM (Like Bolt.new) =============
// After generation completes, automatically:
// 1. Create container
// 2. Run npm install && npm run dev
// 3. Detect server port from output
// 4. Update preview URL

interface AutoRunCallbacks {
  onServerStart?: (url: string) => void
  onOutput?: (line: string) => void
  onError?: (error: string) => void
}

const autoRunProject = async (
  projectId: string,
  callbacks: AutoRunCallbacks
): Promise<boolean> => {
  const { onServerStart, onOutput, onError } = callbacks
  const token = localStorage.getItem('access_token')

  try {
    onOutput?.('🚀 Auto-starting project...')

    // Step 1: Create container
    onOutput?.('📦 Creating container...')
    const createResponse = await fetch(`${API_BASE_URL}/containers/${projectId}/create`, {
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
    })

    if (!createResponse.ok) {
      // Container might already exist, try to proceed
      console.warn('Container create failed, might already exist')
    } else {
      onOutput?.('✅ Container created')
    }

    // Step 2: Run npm install && npm run dev
    onOutput?.('📥 Installing dependencies...')
    const execResponse = await fetch(`${API_BASE_URL}/containers/${projectId}/exec`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify({
        command: 'npm install && npm run dev',
        timeout: 300,
      }),
    })

    if (!execResponse.ok) {
      throw new Error('Failed to start dev server')
    }

    // Step 3: Stream output and detect server start
    const reader = execResponse.body?.getReader()
    if (!reader) throw new Error('No response body')

    const decoder = new TextDecoder()
    let buffer = ''
    let serverDetected = false

    // Port detection patterns
    const portPatterns = [
      /https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)/i,
      /Local:\s*https?:\/\/[^:]+:(\d+)/i,
      /running\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /listening\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /VITE.*ready.*localhost:(\d+)/i,
      /Next.*ready.*localhost:(\d+)/i,
    ]

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

              // Check for server start
              if (!serverDetected) {
                for (const pattern of portPatterns) {
                  const match = text.match(pattern)
                  if (match && match[1]) {
                    const port = match[1]
                    const url = `http://localhost:${port}`
                    onOutput?.(`🎉 Server running at ${url}`)
                    onServerStart?.(url)
                    serverDetected = true
                    break
                  }
                }
              }
            }
          } catch {}
        }
      }
    }

    return serverDetected

  } catch (error: any) {
    onError?.(error.message || 'Auto-run failed')
    return false
  }
}

// Sync a file to backend filesystem
const syncFileToBackend = async (projectId: string, path: string, content: string, language?: string) => {
  try {
    const token = localStorage.getItem('access_token')
    const response = await fetch(`${API_BASE_URL}/sync/file`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
      },
      body: JSON.stringify({
        project_id: projectId,
        path,
        content,
        language
      })
    })

    if (!response.ok) {
      console.warn('Failed to sync file to backend:', path)
    }
  } catch (err) {
    console.warn('File sync error:', err)
  }
}

export interface ProjectGenerationProgress {
  percent: number
  message: string
  currentStep?: string
  filesCreated: number
  commandsExecuted: number
}

// Options for the hook (like Bolt.new auto-run behavior)
export interface UseProjectGenerationOptions {
  autoRun?: boolean  // Automatically run project after generation (default: true)
  onServerStart?: (url: string) => void  // Called when dev server starts
  onAutoRunOutput?: (line: string) => void  // Terminal output during auto-run
}

export const useProjectGeneration = (options: UseProjectGenerationOptions = {}) => {
  const { autoRun = true, onServerStart, onAutoRunOutput } = options

  const [isGenerating, setIsGenerating] = useState(false)
  const [isAutoRunning, setIsAutoRunning] = useState(false)
  const [progress, setProgress] = useState<ProjectGenerationProgress>({
    percent: 0,
    message: '',
    filesCreated: 0,
    commandsExecuted: 0,
  })
  const [error, setError] = useState<string | null>(null)
  const [serverUrl, setServerUrl] = useState<string | null>(null)

  // Store the project ID for auto-run
  const projectIdRef = useRef<string | null>(null)

  // Queue files until we have the real project ID from backend
  const pendingFileSyncsRef = useRef<Array<{path: string, content: string, language: string}>>([])
  const hasRealProjectIdRef = useRef<boolean>(false)

  // Track pending sync promises to ensure all files are synced before auto-run
  const pendingSyncPromisesRef = useRef<Promise<void>[]>([])

  const { addFile, setCurrentProject, currentProject } = useProjectStore()

  const generateProject = useCallback(
    async (description: string, projectName?: string) => {
      // CRITICAL: Reset all refs for new project to prevent file overlap
      projectIdRef.current = null
      pendingFileSyncsRef.current = []
      hasRealProjectIdRef.current = false
      pendingSyncPromisesRef.current = [] // Reset pending sync promises

      // Reset project store for clean slate
      useProjectStore.getState().resetProject()

      setIsGenerating(true)
      setError(null)
      setServerUrl(null)
      setProgress({
        percent: 0,
        message: 'Starting project generation...',
        filesCreated: 0,
        commandsExecuted: 0,
      })

      try {
        // Ensure a current project exists BEFORE starting generation
        const store = useProjectStore.getState()
        if (!store.currentProject) {
          const newProject = {
            id: projectName || `project-${Date.now()}`,
            name: projectName || 'Generated Project',
            description,
            files: [],
            createdAt: new Date(),
            updatedAt: new Date(),
          }
          setCurrentProject(newProject)
          // Wait a tick for store to update
          await new Promise(resolve => setTimeout(resolve, 0))
        }

        await streamingClient.streamProjectGeneration(
          description,
          projectName,
          // onEvent callback
          (event: StreamEvent) => {
            handleGenerationEvent(event)
          },
          // onError callback
          (err: Error) => {
            console.error('Project generation error:', err)
            setError(err.message)
            setIsGenerating(false)
          },
          // onComplete callback
          () => {
            setProgress((prev) => ({
              ...prev,
              percent: 100,
              message: 'Project generation complete!',
            }))
            setIsGenerating(false)
          }
        )
      } catch (err: any) {
        console.error('Failed to start project generation:', err)
        setError(err.message || 'Failed to start project generation')
        setIsGenerating(false)
      }
    },
    [setCurrentProject]
  )

  const handleGenerationEvent = useCallback(
    (event: StreamEvent) => {
      switch (event.type) {
        case 'progress':
          setProgress((prev) => ({
            ...prev,
            percent: event.percent || prev.percent,
            message: event.message || prev.message,
          }))
          break

        case 'step_start':
          setProgress((prev) => ({
            ...prev,
            currentStep: event.step?.toString(),
            message: event.message || `Starting ${event.step}`,
          }))
          break

        case 'step_complete':
          setProgress((prev) => ({
            ...prev,
            message: event.message || `Completed ${event.step}`,
          }))
          break

        case 'file_created':
          if (event.path && event.content) {
            const language = getLanguageFromPath(event.path)

            // Add file to project store
            addFile({
              path: event.path,
              content: event.content,
              type: 'file',
              language,
            })

            // Sync file to backend filesystem
            // If we have the real project ID, sync immediately
            // Otherwise, queue for syncing after project_id_updated
            if (hasRealProjectIdRef.current && projectIdRef.current) {
              // Track sync promise to ensure completion before auto-run
              const syncPromise = syncFileToBackend(projectIdRef.current, event.path, event.content, language)
              pendingSyncPromisesRef.current.push(syncPromise)
            } else if (event.project_id) {
              // Backend provided project_id in the event
              const syncPromise = syncFileToBackend(event.project_id, event.path, event.content, language)
              pendingSyncPromisesRef.current.push(syncPromise)
            } else {
              // Queue for later sync - prevents file overlap with temp IDs
              pendingFileSyncsRef.current.push({ path: event.path, content: event.content, language })
              console.log(`[ProjectGeneration] Queued file for sync: ${event.path}`)
            }

            setProgress((prev) => ({
              ...prev,
              filesCreated: prev.filesCreated + 1,
              message: `Created ${event.path}`,
            }))
          }
          break

        case 'command_executed':
          setProgress((prev) => ({
            ...prev,
            commandsExecuted: prev.commandsExecuted + 1,
            message: event.message || 'Executed command',
          }))
          break

        case 'project_id_updated':
          // CRITICAL: Update project with real database ID from backend
          // This is required for Run/Preview to work and prevents file overlap
          // Backend sends project_id inside event.data, so check both locations
          const newProjectId = event.data?.project_id || event.project_id
          if (newProjectId) {
            const store = useProjectStore.getState()
            const currentProject = store.currentProject
            if (currentProject) {
              console.log(`[ProjectGeneration] Updating project ID: ${currentProject.id} -> ${newProjectId}`)
              setCurrentProject({
                ...currentProject,
                id: newProjectId,
              })
              // Store for auto-run
              projectIdRef.current = newProjectId
              hasRealProjectIdRef.current = true

              // CRITICAL: Flush all queued file syncs with the REAL project ID
              // This prevents files from being synced to wrong directories
              if (pendingFileSyncsRef.current.length > 0) {
                console.log(`[ProjectGeneration] Flushing ${pendingFileSyncsRef.current.length} queued files to project: ${newProjectId}`)
                for (const file of pendingFileSyncsRef.current) {
                  // Track sync promise to ensure completion before auto-run
                  const syncPromise = syncFileToBackend(newProjectId, file.path, file.content, file.language)
                  pendingSyncPromisesRef.current.push(syncPromise)
                }
                pendingFileSyncsRef.current = [] // Clear the queue
              }
            }
          }
          break

        case 'done':
          setProgress((prev) => ({
            ...prev,
            percent: 100,
            message: 'Project generated successfully!',
            filesCreated: event.total_files_created || prev.filesCreated,
            commandsExecuted: event.total_commands_executed || prev.commandsExecuted,
          }))
          // Mark generation as complete
          setIsGenerating(false)

          // ============= AUTO-RUN (Like Bolt.new) =============
          // Automatically start the project after generation
          // CRITICAL: Wait for all file syncs to complete before starting auto-run
          // This prevents "build complete but files still creating" race condition
          if (autoRun && projectIdRef.current) {
            console.log('[ProjectGeneration] 🚀 Waiting for file syncs to complete...')
            setProgress((prev) => ({
              ...prev,
              message: '📁 Syncing files to server...',
            }))

            // Wait for all pending file syncs to complete
            const pendingSyncs = pendingSyncPromisesRef.current
            if (pendingSyncs.length > 0) {
              console.log(`[ProjectGeneration] Waiting for ${pendingSyncs.length} file syncs to complete`)
              await Promise.all(pendingSyncs)
              console.log(`[ProjectGeneration] All ${pendingSyncs.length} file syncs completed`)
              pendingSyncPromisesRef.current = [] // Clear completed promises
            }

            console.log('[ProjectGeneration] 🚀 Starting auto-run...')
            setIsAutoRunning(true)
            setProgress((prev) => ({
              ...prev,
              message: '🚀 Starting project...',
            }))

            autoRunProject(projectIdRef.current, {
              onServerStart: (url) => {
                setServerUrl(url)
                setIsAutoRunning(false)
                setProgress((prev) => ({
                  ...prev,
                  message: `🎉 Server running at ${url}`,
                }))
                onServerStart?.(url)
              },
              onOutput: (line) => {
                console.log('[AutoRun]', line)
                onAutoRunOutput?.(line)
              },
              onError: (err) => {
                console.error('[AutoRun Error]', err)
                setIsAutoRunning(false)
                setProgress((prev) => ({
                  ...prev,
                  message: `Auto-run failed: ${err}`,
                }))
              },
            })
          }
          break

        case 'error':
          setError(event.message || 'An error occurred')
          setIsGenerating(false)
          break
      }
    },
    [addFile]
  )

  const resetProgress = useCallback(() => {
    setProgress({
      percent: 0,
      message: '',
      filesCreated: 0,
      commandsExecuted: 0,
    })
    setError(null)
  }, [])

  return {
    generateProject,
    isGenerating,
    isAutoRunning,
    progress,
    error,
    serverUrl,
    resetProgress,
  }
}

// Helper: Get language from file extension
const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase()
  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    html: 'html',
    css: 'css',
    json: 'json',
    md: 'markdown',
    py: 'python',
    java: 'java',
    go: 'go',
    rs: 'rust',
    cpp: 'cpp',
    c: 'c',
  }
  return languageMap[ext || ''] || 'plaintext'
}
