/**
 * Unified Agent Client — Frontend service for Kiro-style agent interaction
 * 
 * Connects to POST /api/v1/agent/execute and processes SSE events.
 * Use this for MODIFY/FIX intents instead of the old orchestrator.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface AgentExecuteRequest {
  message: string
  project_id: string
  user_id?: string
  project_files?: Record<string, string>
  conversation_history?: Array<{ role: string; content: string }>
  model_preference?: string
  user_plan?: string
}

export interface AgentEvent {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'file_created' | 'file_modified' | 'file_read' | 'command_run' | 'command_output' | 'message' | 'error' | 'done'
  data: Record<string, any>
  timestamp: string
}

export type OnAgentEvent = (event: AgentEvent) => void

/**
 * Execute the unified agent with SSE streaming.
 * 
 * Usage:
 *   await executeUnifiedAgent(
 *     { message: "Add dark mode", project_id: "proj-123", project_files: {...} },
 *     (event) => {
 *       if (event.type === 'thinking') showThinking(event.data.message)
 *       if (event.type === 'file_created') addFileToTree(event.data.path)
 *       if (event.type === 'file_modified') refreshFile(event.data.path)
 *       if (event.type === 'message') showResponse(event.data.content)
 *       if (event.type === 'done') showSummary(event.data)
 *     }
 *   )
 */
export async function executeUnifiedAgent(
  request: AgentExecuteRequest,
  onEvent: OnAgentEvent,
  signal?: AbortSignal
): Promise<void> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null

  const response = await fetch(`${API_BASE_URL}/agent/execute`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(request),
    signal,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  const reader = response.body?.getReader()
  if (!reader) throw new Error('No response body')

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
        const data = line.slice(6).trim()
        if (data === '[DONE]') return

        try {
          const event: AgentEvent = JSON.parse(data)
          onEvent(event)
        } catch (e) {
          console.warn('[UnifiedAgent] Failed to parse event:', line)
        }
      }
    }
  }
}

/**
 * Check if we should use the Unified Agent for this intent.
 * Returns true for MODIFY, FIX, REFACTOR intents when project exists.
 */
export function shouldUseUnifiedAgent(
  intent: string,
  hasExistingProject: boolean
): boolean {
  const unifiedIntents = ['MODIFY', 'FIX', 'REFACTOR']
  return hasExistingProject && unifiedIntents.includes(intent)
}

/**
 * Build project_files dict from the project file tree.
 * Only includes files that have content loaded.
 */
export function buildProjectFilesDict(
  files: Array<{ path: string; content?: string; type?: string; children?: any[] }>
): Record<string, string> {
  const dict: Record<string, string> = {}

  function collect(fileList: typeof files) {
    for (const file of fileList) {
      if (file.type === 'file' && file.content) {
        dict[file.path] = file.content
      }
      if (file.children) {
        collect(file.children)
      }
    }
  }

  collect(files)
  return dict
}

export default executeUnifiedAgent
