/**
 * SDK Service - Frontend API client for Claude Agent SDK endpoints
 *
 * This service provides methods to interact with the backend SDK agents:
 * - SDKFixerAgent: Auto-fix errors using Claude's tool use API
 * - SDK Tools: Execute individual tools (bash, view_file, etc.)
 *
 * All methods are non-blocking and return promises.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// ============================================
// Types
// ============================================

export interface FixErrorRequest {
  project_id: string
  error_message: string
  stack_trace?: string
  command?: string
  build_command?: string
  max_retries?: number
}

export interface FixErrorResponse {
  success: boolean
  error_fixed: boolean
  files_modified: string[]
  message: string
  attempts: number
}

export interface ToolExecuteRequest {
  project_id: string
  tool_name: string
  tool_input: Record<string, any>
}

export interface ToolExecuteResponse {
  success: boolean
  tool: string
  result: string
}

export interface SDKTool {
  name: string
  description: string
  input_schema: {
    type: string
    properties: Record<string, any>
    required: string[]
  }
}

export interface SDKHealthResponse {
  status: string
  sdk_fixer: string
  sdk_orchestrator: string
  tools_available: number
}

export interface StreamEvent {
  type: string
  message?: string
  result?: FixErrorResponse
  error?: string
}

// ============================================
// Helper Functions
// ============================================

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('access_token')
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  }
}

// ============================================
// SDK Service
// ============================================

export const sdkService = {
  /**
   * Fix an error using SDK Fixer Agent
   *
   * @param request - Fix error request parameters
   * @returns Promise with fix result
   */
  async fixError(request: FixErrorRequest): Promise<FixErrorResponse> {
    const response = await fetch(`${API_URL}/sdk/fix`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  },

  /**
   * Fix an error with streaming progress updates
   *
   * @param request - Fix error request parameters
   * @param onEvent - Callback for each SSE event
   * @returns Promise that resolves when stream completes
   */
  async fixErrorStream(
    request: FixErrorRequest,
    onEvent: (event: StreamEvent) => void
  ): Promise<void> {
    const response = await fetch(`${API_URL}/sdk/fix/stream`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

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
            const data = JSON.parse(line.slice(6))
            onEvent(data)
          } catch (e) {
            console.warn('[SDK] Failed to parse SSE event:', line)
          }
        }
      }
    }
  },

  /**
   * Execute a single SDK tool
   *
   * @param request - Tool execution request
   * @returns Promise with tool result
   */
  async executeTool(request: ToolExecuteRequest): Promise<ToolExecuteResponse> {
    const response = await fetch(`${API_URL}/sdk/tool/execute`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(request)
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
  },

  /**
   * Get list of available SDK tools
   *
   * @returns Promise with tools list
   */
  async getTools(): Promise<{ tools: SDKTool[], count: number }> {
    const response = await fetch(`${API_URL}/sdk/tools`, {
      method: 'GET',
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    return response.json()
  },

  /**
   * Check SDK health status
   *
   * @returns Promise with health status
   */
  async checkHealth(): Promise<SDKHealthResponse> {
    const response = await fetch(`${API_URL}/sdk/health`, {
      method: 'GET',
      headers: getAuthHeaders()
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    return response.json()
  },

  // ============================================
  // Convenience Methods for Common Tools
  // ============================================

  /**
   * Run a bash command in the project sandbox
   */
  async runBash(projectId: string, command: string, timeout = 120): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'bash',
      tool_input: { command, timeout }
    })
    return result.result
  },

  /**
   * View a file's contents
   */
  async viewFile(projectId: string, path: string): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'view_file',
      tool_input: { path }
    })
    return result.result
  },

  /**
   * Replace text in a file
   */
  async replaceInFile(
    projectId: string,
    path: string,
    oldStr: string,
    newStr: string
  ): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'str_replace',
      tool_input: { path, old_str: oldStr, new_str: newStr }
    })
    return result.result
  },

  /**
   * Create a new file
   */
  async createFile(projectId: string, path: string, content: string): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'create_file',
      tool_input: { path, content }
    })
    return result.result
  },

  /**
   * Search for files by pattern
   */
  async glob(projectId: string, pattern: string): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'glob',
      tool_input: { pattern }
    })
    return result.result
  },

  /**
   * Search for text in files
   */
  async grep(projectId: string, pattern: string, path = '.'): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'grep',
      tool_input: { pattern, path }
    })
    return result.result
  },

  /**
   * List directory contents
   */
  async listDirectory(projectId: string, path = '.', recursive = false): Promise<string> {
    const result = await this.executeTool({
      project_id: projectId,
      tool_name: 'list_directory',
      tool_input: { path, recursive }
    })
    return result.result
  }
}

export default sdkService
