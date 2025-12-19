const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface StreamEvent {
  type: string
  percent?: number
  message?: string
  step?: string
  path?: string
  content?: string
  project_id?: string
  data?: Record<string, any>
  total_files_created?: number
  total_commands_executed?: number
  text?: string
  agent?: string
  status?: string
  operation?: string
  operation_status?: string
  file_path?: string
  language?: string
  title?: string
  description?: string
  filename?: string
  file_content?: string
  command?: string
  output?: string
  exit_code?: number
  error?: string
  chunk?: string
  token?: string
  delta?: string
  commands?: string[]
  files?: any[]
  [key: string]: any // Allow additional properties
}

type OnEventCallback = (event: StreamEvent) => void
type OnErrorCallback = (error: Error) => void
type OnCompleteCallback = () => void
type OnDisconnectCallback = (projectId: string) => void  // Called when SSE disconnects unexpectedly

class StreamingClient {
  private abortController: AbortController | null = null
  private currentProjectId: string | null = null

  private getAuthHeaders(): Record<string, string> {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }

  /**
   * Abort current streaming request AND notify backend to stop generation
   */
  abort(): void {
    // Abort the fetch request
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }

    // CRITICAL: Also notify backend to stop generating files
    // Without this, backend continues processing even after frontend disconnects
    if (this.currentProjectId) {
      this.cancelBackendGeneration(this.currentProjectId)
      this.currentProjectId = null
    }
  }

  /**
   * Notify backend to cancel ongoing generation for a project
   */
  private async cancelBackendGeneration(projectId: string): Promise<void> {
    try {
      console.log('[StreamingClient] Sending cancel request to backend for project:', projectId)
      const response = await fetch(`${API_BASE_URL}/orchestrator/cancel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        body: JSON.stringify({ project_id: projectId }),
      })

      if (response.ok) {
        console.log('[StreamingClient] Backend generation cancelled successfully')
      } else {
        console.warn('[StreamingClient] Failed to cancel backend generation:', response.status)
      }
    } catch (error) {
      // Don't throw - this is a best-effort cancellation
      console.warn('[StreamingClient] Error sending cancel request:', error)
    }
  }

  /**
   * Stream project generation events from backend
   */
  async streamProjectGeneration(
    description: string,
    projectName?: string,
    onEvent?: OnEventCallback,
    onError?: OnErrorCallback,
    onComplete?: OnCompleteCallback
  ): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/bolt/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        body: JSON.stringify({
          prompt: description,
          project_name: projectName,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      await this.processStream(response, onEvent, onError, onComplete)
    } catch (error: any) {
      onError?.(error)
    }
  }

  /**
   * Stream chat messages from backend
   */
  async streamChat(
    projectId: string,
    message: string,
    onEvent?: OnEventCallback,
    onError?: OnErrorCallback,
    onComplete?: OnCompleteCallback
  ): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/bolt/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        body: JSON.stringify({
          project_id: projectId,
          message,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      await this.processStream(response, onEvent, onError, onComplete)
    } catch (error: any) {
      onError?.(error)
    }
  }

  /**
   * Stream orchestrator events from backend
   */
  async streamOrchestrator(
    projectId: string,
    prompt: string,
    onEvent?: OnEventCallback,
    onError?: OnErrorCallback,
    onComplete?: OnCompleteCallback
  ): Promise<void> {
    // Track current project ID for cancellation support
    this.currentProjectId = projectId

    // Create abort controller for this request
    this.abortController = new AbortController()

    try {
      const response = await fetch(`${API_BASE_URL}/orchestrator/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        body: JSON.stringify({
          project_id: projectId,
          user_request: prompt,
        }),
        signal: this.abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      await this.processStream(response, onEvent, onError, onComplete)
    } catch (error: any) {
      // Don't report abort errors as actual errors
      if (error.name === 'AbortError') {
        console.log('[StreamingClient] Request aborted by user')
        onComplete?.()
        return
      }
      onError?.(error)
    }
  }

  /**
   * Stream orchestrator workflow with metadata
   */
  async streamOrchestratorWorkflow(
    prompt: string,
    projectId: string,
    workflow: string,
    metadata?: Record<string, any>,
    onEvent?: OnEventCallback,
    onError?: OnErrorCallback,
    onComplete?: OnCompleteCallback
  ): Promise<void> {
    // Track current project ID for cancellation support
    this.currentProjectId = projectId

    // Create abort controller for this request
    this.abortController = new AbortController()

    try {
      const response = await fetch(`${API_BASE_URL}/orchestrator/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...this.getAuthHeaders(),
        },
        body: JSON.stringify({
          project_id: projectId,
          user_request: prompt,
          workflow_name: workflow,
          metadata,
        }),
        signal: this.abortController.signal,
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      await this.processStream(response, onEvent, onError, onComplete)
    } catch (error: any) {
      // Don't report abort errors as actual errors
      if (error.name === 'AbortError') {
        console.log('[StreamingClient] Request aborted by user')
        onComplete?.()
        return
      }
      onError?.(error)
    }
  }

  /**
   * Process SSE stream from response
   */
  private async processStream(
    response: Response,
    onEvent?: OnEventCallback,
    onError?: OnErrorCallback,
    onComplete?: OnCompleteCallback
  ): Promise<void> {
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''

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
              const data = line.slice(6).trim()
              if (data === '[DONE]') {
                onComplete?.()
                return
              }
              const event: StreamEvent = JSON.parse(data)

              // Update project ID if backend sends a new one
              // This happens when frontend uses temporary ID and backend assigns real DB UUID
              if (event.type === 'project_id_updated' && event.data?.project_id) {
                this.currentProjectId = event.data.project_id
                console.log('[StreamingClient] Updated project ID to:', this.currentProjectId)
              }

              onEvent?.(event)

              if (event.type === 'done' || event.type === 'complete') {
                this.currentProjectId = null  // Clear on completion
                onComplete?.()
                return
              }

              if (event.type === 'cancelled') {
                this.currentProjectId = null  // Clear on cancellation
                onComplete?.()
                return
              }
              if (event.type === 'error') {
                // Extract error message from various nested locations
                // Backend may send: event.message, event.data.message, event.error, event.data.error
                const errorMessage =
                  event.message ||
                  event.data?.message ||
                  event.data?.error ||
                  event.error ||
                  'Stream error'
                console.error('[StreamingClient] Error event received:', event)
                onError?.(new Error(errorMessage))
                return
              }
            } catch (parseError) {
              // Skip invalid JSON
              console.warn('Failed to parse SSE event:', line)
            }
          }
        }
      }
      onComplete?.()
    } catch (error: any) {
      // Check if it's a network disconnection
      const isNetworkError = error.name === 'TypeError' ||
                             error.message?.includes('network') ||
                             error.message?.includes('Failed to fetch') ||
                             error.message?.includes('aborted')

      if (isNetworkError && this.currentProjectId && this.onDisconnectCallback) {
        console.log('[StreamingClient] Network disconnected, triggering polling fallback')
        this.onDisconnectCallback(this.currentProjectId)
      }

      onError?.(error)
    } finally {
      reader.releaseLock()
    }
  }

  // Disconnect callback for polling fallback
  private onDisconnectCallback: OnDisconnectCallback | null = null

  /**
   * Set callback for when SSE disconnects unexpectedly
   * Use this to start polling for progress updates
   */
  setOnDisconnect(callback: OnDisconnectCallback | null): void {
    this.onDisconnectCallback = callback
  }

  /**
   * Get current project ID being generated
   */
  getCurrentProjectId(): string | null {
    return this.currentProjectId
  }
}

export const streamingClient = new StreamingClient()
export default streamingClient
