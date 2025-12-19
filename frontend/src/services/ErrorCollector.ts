/**
 * ErrorCollector - Centralized Error Handling Service
 *
 * Single entry point for all error collection, buffering, and forwarding
 * to the backend auto-fixer system.
 *
 * Features:
 * - Collects errors from all sources (browser, build, Docker, network)
 * - Maintains output buffer for full error context
 * - Debounced forwarding to prevent spam
 * - Automatic deduplication
 * - Pattern-based error detection
 */

import { apiClient } from '@/lib/api-client'

// Error source types (expanded for Bolt.new-style capture)
export type ErrorSource =
  | 'browser'      // JS runtime errors
  | 'build'        // Build/compile errors
  | 'docker'       // Container errors
  | 'network'      // Fetch/XHR errors
  | 'backend'      // Backend API errors
  | 'react'        // React component errors
  | 'hmr'          // Hot Module Replacement errors
  | 'resource'     // Resource load errors (img/script/css)
  | 'csp'          // Content Security Policy violations

// Error severity levels
export type ErrorSeverity = 'error' | 'warning' | 'info'

// Error entry structure
export interface ErrorEntry {
  source: ErrorSource
  type: string
  message: string
  file?: string
  line?: number
  column?: number
  stack?: string
  command?: string
  timestamp: number
  severity: ErrorSeverity
}

// Callback types
export type OnFixStarted = (reason: string) => void
export type OnFixCompleted = (patchesApplied: number, filesModified: string[]) => void
export type OnFixFailed = (error: string) => void
export type OnErrorDetected = (error: ErrorEntry) => void

// Configuration options
export interface ErrorCollectorConfig {
  projectId: string
  enabled?: boolean
  debounceMs?: number
  maxBufferSize?: number
  onFixStarted?: OnFixStarted
  onFixCompleted?: OnFixCompleted
  onFixFailed?: OnFixFailed
  onErrorDetected?: OnErrorDetected
}

// Error patterns for detection (expanded for Bolt.new-style capture)
const ERROR_PATTERNS: { pattern: RegExp; severity: ErrorSeverity }[] = [
  // Terminal/Build errors
  { pattern: /error:/i, severity: 'error' },
  { pattern: /exception:/i, severity: 'error' },
  { pattern: /traceback/i, severity: 'error' },
  { pattern: /syntaxerror/i, severity: 'error' },
  { pattern: /typeerror/i, severity: 'error' },
  { pattern: /referenceerror/i, severity: 'error' },
  { pattern: /modulenotfound/i, severity: 'error' },
  { pattern: /importerror/i, severity: 'error' },
  { pattern: /failed to compile/i, severity: 'error' },
  { pattern: /build failed/i, severity: 'error' },
  { pattern: /cannot find module/i, severity: 'error' },
  { pattern: /unexpected token/i, severity: 'error' },
  { pattern: /command failed/i, severity: 'error' },
  { pattern: /exited with code [1-9]/i, severity: 'error' },
  { pattern: /npm ERR!/i, severity: 'error' },
  { pattern: /ENOENT/i, severity: 'error' },
  { pattern: /EACCES/i, severity: 'error' },
  // Docker errors
  { pattern: /port.*already.*in.*use/i, severity: 'error' },
  { pattern: /invalid.*dockerfile/i, severity: 'error' },
  { pattern: /container.*exit.*code.*[1-9]/i, severity: 'error' },
  { pattern: /no.*such.*image/i, severity: 'error' },
  // Python errors
  { pattern: /no.*module.*named/i, severity: 'error' },
  { pattern: /attributeerror/i, severity: 'error' },
  { pattern: /valueerror/i, severity: 'error' },
  { pattern: /keyerror/i, severity: 'error' },
  { pattern: /indentationerror/i, severity: 'error' },
  // Java errors
  { pattern: /BUILD FAILURE/i, severity: 'error' },
  { pattern: /compilation failure/i, severity: 'error' },
  { pattern: /NullPointerException/i, severity: 'error' },
  // Rust errors
  { pattern: /error\[E\d+\]/i, severity: 'error' },
  { pattern: /thread.*panicked/i, severity: 'error' },
  // Go errors
  { pattern: /panic:/i, severity: 'error' },
  { pattern: /fatal error:/i, severity: 'error' },
  // ===== NEW: React errors =====
  { pattern: /react.*error/i, severity: 'error' },
  { pattern: /component.*error/i, severity: 'error' },
  { pattern: /render.*error/i, severity: 'error' },
  { pattern: /invalid.*hook.*call/i, severity: 'error' },
  { pattern: /maximum.*update.*depth/i, severity: 'error' },
  { pattern: /cannot read.*undefined/i, severity: 'error' },
  { pattern: /cannot read.*null/i, severity: 'error' },
  { pattern: /minified react error/i, severity: 'error' },
  // ===== NEW: HMR/Vite errors =====
  { pattern: /hmr.*error/i, severity: 'error' },
  { pattern: /hot.*update.*failed/i, severity: 'error' },
  { pattern: /vite.*error/i, severity: 'error' },
  { pattern: /\[vite\].*error/i, severity: 'error' },
  { pattern: /pre-transform.*error/i, severity: 'error' },
  // ===== NEW: Resource load errors =====
  { pattern: /failed to load/i, severity: 'error' },
  { pattern: /resource.*load.*error/i, severity: 'error' },
  { pattern: /failed to fetch/i, severity: 'error' },
  { pattern: /loading.*chunk.*failed/i, severity: 'error' },
  { pattern: /dynamic import/i, severity: 'error' },
  // ===== NEW: CSP errors =====
  { pattern: /content.*security.*policy/i, severity: 'error' },
  { pattern: /csp.*violation/i, severity: 'error' },
  { pattern: /blocked.*by.*csp/i, severity: 'error' },
  // ===== NEW: CORS errors =====
  { pattern: /cors.*error/i, severity: 'error' },
  { pattern: /cross-origin/i, severity: 'warning' },
  { pattern: /access.*control.*allow/i, severity: 'warning' },
  // Warnings
  { pattern: /warning:/i, severity: 'warning' },
  { pattern: /deprecated/i, severity: 'warning' },
]

// Patterns to ignore (false positives)
const IGNORE_PATTERNS: RegExp[] = [
  /spawn xdg-open ENOENT/i,
  /spawn open ENOENT/i,
  /npm WARN/i,
  /deprecation warning/i,
  /ExperimentalWarning/i,
]

/**
 * ErrorCollector - Singleton service for centralized error handling
 */
class ErrorCollectorService {
  private static instances: Map<string, ErrorCollectorService> = new Map()

  private projectId: string
  private enabled: boolean
  private debounceMs: number
  private maxBufferSize: number

  // Buffers
  private outputBuffer: string[] = []
  private errorBuffer: ErrorEntry[] = []
  private currentCommand: string = ''

  // Debounce timer
  private debounceTimer: NodeJS.Timeout | null = null

  // Callbacks
  private onFixStarted?: OnFixStarted
  private onFixCompleted?: OnFixCompleted
  private onFixFailed?: OnFixFailed
  private onErrorDetected?: OnErrorDetected

  // WebSocket connection
  private ws: WebSocket | null = null
  private wsReconnectAttempts = 0
  private wsReconnectTimer: NodeJS.Timeout | null = null

  // Deduplication
  private recentErrors: Set<string> = new Set()
  private dedupeTimer: NodeJS.Timeout | null = null

  private constructor(config: ErrorCollectorConfig) {
    this.projectId = config.projectId
    this.enabled = config.enabled ?? true
    this.debounceMs = config.debounceMs ?? 800
    this.maxBufferSize = config.maxBufferSize ?? 50
    this.onFixStarted = config.onFixStarted
    this.onFixCompleted = config.onFixCompleted
    this.onFixFailed = config.onFixFailed
    this.onErrorDetected = config.onErrorDetected

    // Start deduplication cleanup
    this.startDedupeCleanup()
  }

  /**
   * Get or create an ErrorCollector instance for a project
   */
  static getInstance(config: ErrorCollectorConfig): ErrorCollectorService {
    const existing = this.instances.get(config.projectId)
    if (existing) {
      existing.updateConfig(config)
      return existing
    }

    const instance = new ErrorCollectorService(config)
    this.instances.set(config.projectId, instance)
    return instance
  }

  /**
   * Destroy instance for a project
   */
  static destroyInstance(projectId: string): void {
    const instance = this.instances.get(projectId)
    if (instance) {
      instance.destroy()
      this.instances.delete(projectId)
    }
  }

  /**
   * Update configuration
   */
  updateConfig(config: Partial<ErrorCollectorConfig>): void {
    if (config.enabled !== undefined) this.enabled = config.enabled
    if (config.debounceMs !== undefined) this.debounceMs = config.debounceMs
    if (config.maxBufferSize !== undefined) this.maxBufferSize = config.maxBufferSize
    if (config.onFixStarted) this.onFixStarted = config.onFixStarted
    if (config.onFixCompleted) this.onFixCompleted = config.onFixCompleted
    if (config.onFixFailed) this.onFixFailed = config.onFixFailed
    if (config.onErrorDetected) this.onErrorDetected = config.onErrorDetected
  }

  /**
   * Set current command being executed
   */
  setCurrentCommand(command: string): void {
    this.currentCommand = command
  }

  /**
   * Add output line to buffer (for context)
   * Call this for ALL output, not just errors
   */
  addOutput(output: string): void {
    if (!this.enabled || !output) return

    this.outputBuffer.push(output)
    if (this.outputBuffer.length > this.maxBufferSize) {
      this.outputBuffer.shift()
    }
  }

  /**
   * SINGLE ENTRY POINT: Report an error from any source
   * This is the main method to use for reporting errors
   */
  reportError(
    source: ErrorSource,
    message: string,
    options: {
      type?: string
      file?: string
      line?: number
      column?: number
      stack?: string
      severity?: ErrorSeverity
    } = {}
  ): void {
    if (!this.enabled || !message) return

    // Check if this should be ignored
    if (this.shouldIgnore(message)) {
      console.log('[ErrorCollector] Ignoring false positive:', message.slice(0, 50))
      return
    }

    // Deduplicate
    const errorKey = `${source}:${message.slice(0, 100)}`
    if (this.recentErrors.has(errorKey)) {
      console.log('[ErrorCollector] Deduplicating error:', message.slice(0, 50))
      return
    }
    this.recentErrors.add(errorKey)

    // Determine severity if not provided
    const severity = options.severity ?? this.detectSeverity(message)

    // Create error entry
    const entry: ErrorEntry = {
      source,
      type: options.type ?? this.inferErrorType(source, message),
      message,
      file: options.file,
      line: options.line,
      column: options.column,
      stack: options.stack,
      command: this.currentCommand,
      timestamp: Date.now(),
      severity
    }

    // Add to error buffer
    this.errorBuffer.push(entry)
    if (this.errorBuffer.length > 20) {
      this.errorBuffer.shift()
    }

    // Also add to output buffer for context
    this.outputBuffer.push(message)
    if (this.outputBuffer.length > this.maxBufferSize) {
      this.outputBuffer.shift()
    }

    console.log('[ErrorCollector] Error reported:', {
      source,
      type: entry.type,
      message: message.slice(0, 100),
      severity
    })

    // Notify listener
    this.onErrorDetected?.(entry)

    // Schedule debounced forwarding
    this.scheduleForward()
  }

  /**
   * Detect error in output and report if found
   * Returns true if error was detected
   */
  detectAndReport(output: string, source: ErrorSource = 'build'): boolean {
    if (!this.enabled || !output) return false

    // Add to output buffer regardless
    this.addOutput(output)

    // Check if this should be ignored
    if (this.shouldIgnore(output)) {
      return false
    }

    // Check for error patterns
    for (const { pattern, severity } of ERROR_PATTERNS) {
      if (pattern.test(output)) {
        this.reportError(source, output, { severity })
        return true
      }
    }

    return false
  }

  /**
   * Report browser runtime error
   */
  reportBrowserError(
    message: string,
    file?: string,
    line?: number,
    column?: number,
    stack?: string
  ): void {
    this.reportError('browser', message, {
      type: 'runtime_error',
      file,
      line,
      column,
      stack,
      severity: 'error'
    })
  }

  /**
   * Report build/compile error
   */
  reportBuildError(message: string, file?: string): void {
    this.reportError('build', message, {
      type: 'build_error',
      file,
      severity: 'error'
    })
  }

  /**
   * Report Docker container error
   */
  reportDockerError(message: string, exitCode?: number): void {
    this.reportError('docker', message, {
      type: exitCode ? 'container_exit' : 'docker_error',
      severity: 'error'
    })
  }

  /**
   * Report network/API error
   */
  reportNetworkError(
    message: string,
    url: string,
    status?: number,
    method: string = 'GET'
  ): void {
    this.reportError('network', `${method} ${url}: ${message}`, {
      type: 'network_error',
      severity: status && status < 500 ? 'warning' : 'error'
    })
  }

  /**
   * Report React component error (Bolt.new style)
   */
  reportReactError(
    message: string,
    componentStack?: string,
    stack?: string
  ): void {
    this.reportError('react', message, {
      type: 'react_error',
      stack: stack ? `${stack}\n\nComponent Stack:\n${componentStack || ''}` : componentStack,
      severity: 'error'
    })
  }

  /**
   * Report HMR/Hot reload error
   */
  reportHMRError(
    message: string,
    file?: string,
    line?: number,
    column?: number
  ): void {
    this.reportError('hmr', message, {
      type: 'hmr_error',
      file,
      line,
      column,
      severity: 'error'
    })
  }

  /**
   * Report resource load error (img/script/css)
   */
  reportResourceError(
    tagName: string,
    src: string
  ): void {
    this.reportError('resource', `Failed to load ${tagName}: ${src}`, {
      type: 'resource_load_error',
      file: src,
      severity: 'error'
    })
  }

  /**
   * Report CSP violation
   */
  reportCSPError(
    violatedDirective: string,
    blockedURI: string,
    sourceFile?: string,
    lineNumber?: number
  ): void {
    this.reportError('csp', `CSP Violation: ${violatedDirective} blocked ${blockedURI}`, {
      type: 'csp_violation',
      file: sourceFile,
      line: lineNumber,
      severity: 'error'
    })
  }

  /**
   * Force immediate forward (use when command completes)
   */
  forwardNow(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer)
      this.debounceTimer = null
    }
    this.forwardToBackend()
  }

  /**
   * Clear all buffers
   */
  clearBuffers(): void {
    this.outputBuffer = []
    this.errorBuffer = []
    this.recentErrors.clear()
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer)
      this.debounceTimer = null
    }
  }

  /**
   * Get current output buffer (for display purposes)
   */
  getOutputBuffer(): string[] {
    return [...this.outputBuffer]
  }

  /**
   * Get current error buffer
   */
  getErrorBuffer(): ErrorEntry[] {
    return [...this.errorBuffer]
  }

  /**
   * Connect to WebSocket for real-time fix notifications
   */
  connectWebSocket(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return

    try {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = process.env.NEXT_PUBLIC_API_URL
        ?.replace(/^https?:\/\//, '')
        .replace(/\/api\/v1\/?$/, '') || 'localhost:8000'
      const wsUrl = `${wsProtocol}//${wsHost}/api/v1/errors/ws/${this.projectId}`

      console.log('[ErrorCollector] Connecting WebSocket:', wsUrl)

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('[ErrorCollector] WebSocket connected')
        this.wsReconnectAttempts = 0
      }

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'fix_started') {
            this.onFixStarted?.(msg.reason)
          } else if (msg.type === 'fix_completed') {
            this.onFixCompleted?.(msg.patches_applied || 0, msg.files_modified || [])
          } else if (msg.type === 'fix_failed') {
            this.onFixFailed?.(msg.error)
          }
        } catch {}
      }

      this.ws.onclose = () => {
        console.log('[ErrorCollector] WebSocket disconnected')
        this.ws = null
        this.scheduleReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('[ErrorCollector] WebSocket error:', error)
      }
    } catch (error) {
      console.error('[ErrorCollector] Failed to connect WebSocket:', error)
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnectWebSocket(): void {
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer)
      this.wsReconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * Clean up and destroy instance
   */
  destroy(): void {
    this.clearBuffers()
    this.disconnectWebSocket()
    if (this.dedupeTimer) {
      clearInterval(this.dedupeTimer)
      this.dedupeTimer = null
    }
  }

  // ==================== Private Methods ====================

  private shouldIgnore(message: string): boolean {
    return IGNORE_PATTERNS.some(pattern => pattern.test(message))
  }

  private detectSeverity(message: string): ErrorSeverity {
    for (const { pattern, severity } of ERROR_PATTERNS) {
      if (pattern.test(message)) {
        return severity
      }
    }
    return 'info'
  }

  private inferErrorType(source: ErrorSource, message: string): string {
    const lowerMsg = message.toLowerCase()

    if (source === 'browser') {
      if (lowerMsg.includes('typeerror')) return 'type_error'
      if (lowerMsg.includes('referenceerror')) return 'reference_error'
      if (lowerMsg.includes('syntaxerror')) return 'syntax_error'
      if (lowerMsg.includes('promise')) return 'promise_rejection'
      return 'runtime_error'
    }

    if (source === 'build') {
      if (lowerMsg.includes('compile') || lowerMsg.includes('compilation')) return 'compile_error'
      if (lowerMsg.includes('module') || lowerMsg.includes('import')) return 'module_error'
      if (lowerMsg.includes('syntax')) return 'syntax_error'
      return 'build_error'
    }

    if (source === 'docker') {
      if (lowerMsg.includes('port')) return 'port_error'
      if (lowerMsg.includes('exit')) return 'container_exit'
      return 'docker_error'
    }

    if (source === 'network') {
      if (lowerMsg.includes('cors')) return 'cors_error'
      if (lowerMsg.includes('timeout')) return 'timeout_error'
      if (lowerMsg.includes('fetch')) return 'fetch_error'
      return 'network_error'
    }

    // ===== NEW: React errors =====
    if (source === 'react') {
      if (lowerMsg.includes('render')) return 'render_error'
      if (lowerMsg.includes('hook')) return 'hook_error'
      if (lowerMsg.includes('state')) return 'state_error'
      if (lowerMsg.includes('component')) return 'component_error'
      return 'react_error'
    }

    // ===== NEW: HMR errors =====
    if (source === 'hmr') {
      if (lowerMsg.includes('vite')) return 'vite_hmr_error'
      if (lowerMsg.includes('webpack')) return 'webpack_hmr_error'
      return 'hmr_error'
    }

    // ===== NEW: Resource errors =====
    if (source === 'resource') {
      if (lowerMsg.includes('script')) return 'script_load_error'
      if (lowerMsg.includes('style') || lowerMsg.includes('css')) return 'style_load_error'
      if (lowerMsg.includes('image') || lowerMsg.includes('img')) return 'image_load_error'
      if (lowerMsg.includes('chunk')) return 'chunk_load_error'
      return 'resource_load_error'
    }

    // ===== NEW: CSP errors =====
    if (source === 'csp') {
      return 'csp_violation'
    }

    return 'unknown_error'
  }

  private scheduleForward(): void {
    // Clear existing timer
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer)
    }

    // Set new timer
    this.debounceTimer = setTimeout(() => {
      this.forwardToBackend()
      this.debounceTimer = null
    }, this.debounceMs)

    console.log('[ErrorCollector] Scheduled forward in', this.debounceMs, 'ms')
  }

  private async forwardToBackend(): Promise<void> {
    if (!this.enabled || this.errorBuffer.length === 0) return

    // Compile full error context
    const fullContext = this.outputBuffer.join('\n')
    const errors = [...this.errorBuffer]
    const primaryError = errors[errors.length - 1]

    console.log('[ErrorCollector] Forwarding to backend:', {
      projectId: this.projectId,
      errorCount: errors.length,
      contextLines: this.outputBuffer.length,
      primaryError: primaryError?.message?.slice(0, 100)
    })

    try {
      // Use unified error endpoint
      const response = await apiClient.post(`/errors/report/${this.projectId}`, {
        errors: errors.map(e => ({
          source: e.source,
          type: e.type,
          message: e.message,
          file: e.file,
          line: e.line,
          column: e.column,
          stack: e.stack,
          severity: e.severity,
          timestamp: e.timestamp
        })),
        context: fullContext,
        command: this.currentCommand,
        timestamp: Date.now()
      })

      console.log('[ErrorCollector] Backend response:', response.data)

      // Clear error buffer after successful forward
      this.errorBuffer = []

    } catch (error) {
      console.error('[ErrorCollector] Failed to forward errors:', error)
      // Keep errors in buffer for retry
    }
  }

  private scheduleReconnect(): void {
    if (this.wsReconnectAttempts >= 5) {
      console.log('[ErrorCollector] Max reconnect attempts reached')
      return
    }

    const delay = 2000 * Math.pow(2, this.wsReconnectAttempts)
    this.wsReconnectAttempts++

    console.log(`[ErrorCollector] Reconnecting in ${delay}ms (attempt ${this.wsReconnectAttempts})`)

    this.wsReconnectTimer = setTimeout(() => {
      this.connectWebSocket()
    }, delay)
  }

  private startDedupeCleanup(): void {
    // Clear recent errors every 5 seconds
    this.dedupeTimer = setInterval(() => {
      this.recentErrors.clear()
    }, 5000)
  }
}

// Export singleton accessor
export const ErrorCollector = ErrorCollectorService

// Export convenience hook
export function useErrorCollector(config: ErrorCollectorConfig) {
  return ErrorCollector.getInstance(config)
}

export default ErrorCollector
