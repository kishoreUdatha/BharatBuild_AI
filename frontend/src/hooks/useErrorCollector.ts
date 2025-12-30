/**
 * @deprecated This hook is DEPRECATED - use useLogViewer instead.
 *
 * ============================================================================
 * DEPRECATION NOTICE - DO NOT USE FOR NEW CODE
 * ============================================================================
 *
 * This hook implements the WRONG architecture where:
 * - Frontend parses terminal output for errors
 * - Frontend sends errors to backend for fixing
 *
 * This approach has problems:
 * - Logs get fragmented (multi-line errors break)
 * - Race conditions (UI may render before error completes)
 * - Security risk (client can tamper logs)
 * - Latency (auto-fix starts late)
 *
 * CORRECT ARCHITECTURE (use useLogViewer instead):
 * - Backend captures stdout/stderr directly from container
 * - Backend triggers auto-fixer immediately on exit code != 0
 * - Frontend is READ-ONLY (just displays logs and fix status)
 *
 * See: backend/app/services/execution_context.py
 * See: frontend/src/hooks/useLogViewer.ts
 * ============================================================================
 *
 * OLD DESCRIPTION (kept for reference):
 * useErrorCollector Hook - Centralized Error Collection & Auto-Fix
 *
 * SINGLE ENTRY POINT for all error handling in the frontend.
 * This hook integrates with the ErrorCollector service and the unified
 * backend error endpoint for automatic error detection and fixing.
 *
 * Usage:
 * ```tsx
 * const {
 *   reportError,           // Report any error
 *   detectAndReport,       // Detect errors in terminal output
 *   forwardErrorToBackend, // Forward for auto-fix
 *   fixAllErrors           // Manually trigger fix
 * } = useErrorCollector({ projectId: 'xxx' })
 * ```
 */

import { useEffect, useCallback, useRef, useState } from 'react'
import { useErrorStore, CollectedError } from '@/store/errorStore'
import { useTerminalStore } from '@/store/terminalStore'
import { useProjectStore } from '@/store/projectStore'
import { apiClient } from '@/lib/api-client'

// Error source types (expanded for Bolt.new-style capture)
export type ErrorSource =
  | 'browser'      // JS runtime errors
  | 'build'        // Build/compile errors
  | 'docker'       // Container errors
  | 'network'      // Fetch/XHR errors
  | 'backend'      // Backend API errors
  | 'terminal'     // Terminal output errors
  | 'react'        // React component errors
  | 'hmr'          // Hot Module Replacement errors
  | 'resource'     // Resource load errors (img/script/css)
  | 'csp'          // Content Security Policy violations

// Error severity levels
export type ErrorSeverity = 'error' | 'warning' | 'info'

interface UseErrorCollectorOptions {
  projectId?: string
  autoCapture?: boolean
  enabled?: boolean
  debounceMs?: number
  onFixStarted?: (reason: string) => void
  onFixCompleted?: (patchesApplied: number, filesModified: string[]) => void
  onFixFailed?: (error: string) => void
}

interface FixErrorResponse {
  success: boolean
  fixes?: {
    file: string
    patch: string
    description: string
  }[]
  message?: string
  patches_applied?: number
  files_modified?: string[]
}

// Error patterns for auto-detection - ALL TECHNOLOGIES
// Comprehensive patterns for build errors + runtime errors
const ERROR_PATTERNS: { pattern: RegExp; severity: ErrorSeverity }[] = [
  // ===== JAVASCRIPT/TYPESCRIPT =====
  { pattern: /error\s+TS\d+:/i, severity: 'error' },
  { pattern: /SyntaxError:/i, severity: 'error' },
  { pattern: /TypeError:/i, severity: 'error' },
  { pattern: /ReferenceError:/i, severity: 'error' },
  { pattern: /RangeError:/i, severity: 'error' },
  { pattern: /EvalError:/i, severity: 'error' },
  { pattern: /URIError:/i, severity: 'error' },
  { pattern: /AggregateError:/i, severity: 'error' },
  { pattern: /Uncaught.*Error/i, severity: 'error' },
  { pattern: /Unhandled.*rejection/i, severity: 'error' },
  { pattern: /Unhandled.*promise/i, severity: 'error' },

  // ===== BUILD TOOLS (Vite, Webpack, Rollup, esbuild) =====
  { pattern: /Failed to compile/i, severity: 'error' },
  { pattern: /Build failed/i, severity: 'error' },
  { pattern: /Compilation failed/i, severity: 'error' },
  { pattern: /Module not found/i, severity: 'error' },
  { pattern: /Cannot find module/i, severity: 'error' },
  { pattern: /Cannot resolve/i, severity: 'error' },
  { pattern: /Failed to resolve/i, severity: 'error' },
  { pattern: /\[ERROR\]/i, severity: 'error' },
  { pattern: /No matching export/i, severity: 'error' },
  { pattern: /does not provide an export/i, severity: 'error' },
  { pattern: /Pre-transform error/i, severity: 'error' },
  { pattern: /\[vite\].*error/i, severity: 'error' },
  { pattern: /\[webpack\].*error/i, severity: 'error' },
  { pattern: /\[rollup\].*error/i, severity: 'error' },
  { pattern: /\[esbuild\].*error/i, severity: 'error' },

  // ===== NPM/YARN/PNPM =====
  { pattern: /npm ERR!/i, severity: 'error' },
  { pattern: /yarn error/i, severity: 'error' },
  { pattern: /pnpm ERR!/i, severity: 'error' },
  { pattern: /ERESOLVE/i, severity: 'error' },
  { pattern: /peer dep/i, severity: 'error' },
  { pattern: /Could not resolve dependency/i, severity: 'error' },

  // ===== REACT =====
  { pattern: /Invalid hook call/i, severity: 'error' },
  { pattern: /Maximum update depth exceeded/i, severity: 'error' },
  { pattern: /Cannot update.*unmounted/i, severity: 'error' },
  { pattern: /React.*error/i, severity: 'error' },
  { pattern: /Component.*threw/i, severity: 'error' },
  { pattern: /Error boundary/i, severity: 'error' },
  { pattern: /Minified React error/i, severity: 'error' },
  { pattern: /Each child.*should have.*key/i, severity: 'error' },
  { pattern: /Invalid prop/i, severity: 'error' },
  { pattern: /Failed prop type/i, severity: 'error' },

  // ===== VUE =====
  { pattern: /\[Vue warn\]/i, severity: 'error' },
  { pattern: /\[Vue error\]/i, severity: 'error' },
  { pattern: /Vue.*error/i, severity: 'error' },
  { pattern: /Property.*was accessed.*not defined/i, severity: 'error' },
  { pattern: /Unknown custom element/i, severity: 'error' },
  { pattern: /Failed to resolve component/i, severity: 'error' },

  // ===== ANGULAR =====
  { pattern: /\[Angular\].*error/i, severity: 'error' },
  { pattern: /NG\d+:/i, severity: 'error' },
  { pattern: /NullInjectorError/i, severity: 'error' },
  { pattern: /ExpressionChangedAfterItHasBeenCheckedError/i, severity: 'error' },
  { pattern: /Can't bind to/i, severity: 'error' },
  { pattern: /No provider for/i, severity: 'error' },

  // ===== SVELTE =====
  { pattern: /\[Svelte\].*error/i, severity: 'error' },
  { pattern: /svelte.*error/i, severity: 'error' },

  // ===== NEXT.JS =====
  { pattern: /\[next\].*error/i, severity: 'error' },
  { pattern: /Server Error/i, severity: 'error' },
  { pattern: /Application error/i, severity: 'error' },
  { pattern: /getServerSideProps.*error/i, severity: 'error' },
  { pattern: /getStaticProps.*error/i, severity: 'error' },

  // ===== NODE.JS/EXPRESS =====
  { pattern: /node:.*error/i, severity: 'error' },
  { pattern: /ENOENT/i, severity: 'error' },
  { pattern: /EACCES/i, severity: 'error' },
  { pattern: /EADDRINUSE/i, severity: 'error' },
  { pattern: /ECONNREFUSED/i, severity: 'error' },
  { pattern: /ENOTFOUND/i, severity: 'error' },
  { pattern: /ETIMEDOUT/i, severity: 'error' },
  { pattern: /UnhandledPromiseRejection/i, severity: 'error' },
  { pattern: /express.*error/i, severity: 'error' },

  // ===== PYTHON =====
  { pattern: /Traceback \(most recent call last\)/i, severity: 'error' },
  { pattern: /^\s*File ".*", line \d+/i, severity: 'error' },
  { pattern: /IndentationError/i, severity: 'error' },
  { pattern: /ImportError/i, severity: 'error' },
  { pattern: /ModuleNotFoundError/i, severity: 'error' },
  { pattern: /NameError/i, severity: 'error' },
  { pattern: /AttributeError/i, severity: 'error' },
  { pattern: /KeyError/i, severity: 'error' },
  { pattern: /ValueError/i, severity: 'error' },
  { pattern: /IndexError/i, severity: 'error' },
  { pattern: /ZeroDivisionError/i, severity: 'error' },
  { pattern: /FileNotFoundError/i, severity: 'error' },
  { pattern: /PermissionError/i, severity: 'error' },
  { pattern: /ConnectionError/i, severity: 'error' },
  { pattern: /TimeoutError/i, severity: 'error' },

  // ===== DJANGO =====
  { pattern: /django.*error/i, severity: 'error' },
  { pattern: /DoesNotExist/i, severity: 'error' },
  { pattern: /MultipleObjectsReturned/i, severity: 'error' },
  { pattern: /OperationalError/i, severity: 'error' },
  { pattern: /IntegrityError/i, severity: 'error' },
  { pattern: /ValidationError/i, severity: 'error' },
  { pattern: /ImproperlyConfigured/i, severity: 'error' },
  { pattern: /TemplateDoesNotExist/i, severity: 'error' },

  // ===== FLASK/FASTAPI =====
  { pattern: /flask.*error/i, severity: 'error' },
  { pattern: /fastapi.*error/i, severity: 'error' },
  { pattern: /RequestValidationError/i, severity: 'error' },
  { pattern: /HTTPException/i, severity: 'error' },
  { pattern: /pydantic.*error/i, severity: 'error' },

  // ===== JAVA/SPRING =====
  { pattern: /Exception in thread/i, severity: 'error' },
  { pattern: /java\.lang\.\w+Exception/i, severity: 'error' },
  { pattern: /NullPointerException/i, severity: 'error' },
  { pattern: /ClassNotFoundException/i, severity: 'error' },
  { pattern: /NoSuchMethodException/i, severity: 'error' },
  { pattern: /IllegalArgumentException/i, severity: 'error' },
  { pattern: /IllegalStateException/i, severity: 'error' },
  { pattern: /ArrayIndexOutOfBoundsException/i, severity: 'error' },
  { pattern: /NumberFormatException/i, severity: 'error' },
  { pattern: /IOException/i, severity: 'error' },
  { pattern: /SQLException/i, severity: 'error' },
  { pattern: /Spring.*error/i, severity: 'error' },
  { pattern: /BeanCreationException/i, severity: 'error' },
  { pattern: /NoSuchBeanDefinitionException/i, severity: 'error' },
  { pattern: /DataAccessException/i, severity: 'error' },

  // ===== GO =====
  { pattern: /^panic:/i, severity: 'error' },
  { pattern: /^fatal error:/i, severity: 'error' },
  { pattern: /runtime error:/i, severity: 'error' },
  { pattern: /undefined:.*not declared/i, severity: 'error' },
  { pattern: /cannot find package/i, severity: 'error' },
  { pattern: /build.*failed/i, severity: 'error' },

  // ===== RUST =====
  { pattern: /error\[E\d+\]/i, severity: 'error' },
  { pattern: /panicked at/i, severity: 'error' },
  { pattern: /thread.*panicked/i, severity: 'error' },
  { pattern: /cannot find.*in this scope/i, severity: 'error' },
  { pattern: /mismatched types/i, severity: 'error' },
  { pattern: /borrow checker/i, severity: 'error' },

  // ===== RUBY/RAILS =====
  { pattern: /NoMethodError/i, severity: 'error' },
  { pattern: /ArgumentError/i, severity: 'error' },
  { pattern: /NameError.*undefined/i, severity: 'error' },
  { pattern: /LoadError/i, severity: 'error' },
  { pattern: /ActiveRecord.*Error/i, severity: 'error' },
  { pattern: /ActionController.*Error/i, severity: 'error' },
  { pattern: /RoutingError/i, severity: 'error' },

  // ===== PHP/LARAVEL =====
  { pattern: /PHP Fatal error/i, severity: 'error' },
  { pattern: /PHP Parse error/i, severity: 'error' },
  { pattern: /PHP Warning/i, severity: 'error' },
  { pattern: /Undefined variable/i, severity: 'error' },
  { pattern: /Call to undefined/i, severity: 'error' },
  { pattern: /Class.*not found/i, severity: 'error' },
  { pattern: /Laravel.*error/i, severity: 'error' },
  { pattern: /Illuminate\\.*Exception/i, severity: 'error' },

  // ===== DATABASE ERRORS =====
  { pattern: /SQLSTATE/i, severity: 'error' },
  { pattern: /syntax error.*SQL/i, severity: 'error' },
  { pattern: /duplicate key/i, severity: 'error' },
  { pattern: /foreign key constraint/i, severity: 'error' },
  { pattern: /deadlock/i, severity: 'error' },
  { pattern: /connection.*refused/i, severity: 'error' },
  { pattern: /authentication failed/i, severity: 'error' },
  { pattern: /MongoError/i, severity: 'error' },
  { pattern: /MongoServerError/i, severity: 'error' },
  { pattern: /Redis.*error/i, severity: 'error' },
  { pattern: /PostgreSQL.*error/i, severity: 'error' },
  { pattern: /MySQL.*error/i, severity: 'error' },

  // ===== GRAPHQL =====
  { pattern: /GraphQL.*error/i, severity: 'error' },
  { pattern: /Cannot query field/i, severity: 'error' },
  { pattern: /Unknown argument/i, severity: 'error' },
  { pattern: /Variable.*required/i, severity: 'error' },

  // ===== API/HTTP ERRORS =====
  { pattern: /Failed to fetch/i, severity: 'error' },
  { pattern: /NetworkError/i, severity: 'error' },
  { pattern: /net::ERR_/i, severity: 'error' },
  { pattern: /CORS.*blocked/i, severity: 'error' },
  { pattern: /Access-Control-Allow-Origin/i, severity: 'error' },
  { pattern: /ERR_CONNECTION_REFUSED/i, severity: 'error' },
  { pattern: /fetch.*failed/i, severity: 'error' },
  { pattern: /AxiosError/i, severity: 'error' },
  { pattern: /\b404\b.*not found/i, severity: 'error' },
  { pattern: /\b500\b.*internal server/i, severity: 'error' },
  { pattern: /\b401\b.*unauthorized/i, severity: 'error' },
  { pattern: /\b403\b.*forbidden/i, severity: 'error' },
  { pattern: /\b400\b.*bad request/i, severity: 'error' },
  { pattern: /\b502\b.*bad gateway/i, severity: 'error' },
  { pattern: /\b503\b.*service unavailable/i, severity: 'error' },
  { pattern: /\b504\b.*gateway timeout/i, severity: 'error' },
  { pattern: /\b422\b.*unprocessable/i, severity: 'error' },
  { pattern: /\b429\b.*too many requests/i, severity: 'error' },
  { pattern: /status\s*(?:code\s*)?[:=]?\s*[45]\d{2}/i, severity: 'error' },
  { pattern: /Request failed with status/i, severity: 'error' },
  { pattern: /HTTP\s*[45]\d{2}/i, severity: 'error' },
  { pattern: /Error\s*[45]\d{2}/i, severity: 'error' },

  // ===== WEBSOCKET =====
  { pattern: /WebSocket.*error/i, severity: 'error' },
  { pattern: /WebSocket.*failed/i, severity: 'error' },
  { pattern: /socket.*disconnected/i, severity: 'error' },
  { pattern: /socket.*error/i, severity: 'error' },

  // ===== AUTH/JWT =====
  { pattern: /JWT.*error/i, severity: 'error' },
  { pattern: /Token.*expired/i, severity: 'error' },
  { pattern: /Token.*invalid/i, severity: 'error' },
  { pattern: /Unauthorized/i, severity: 'error' },
  { pattern: /Authentication failed/i, severity: 'error' },
  { pattern: /Invalid credentials/i, severity: 'error' },
  { pattern: /Session expired/i, severity: 'error' },

  // ===== JSON/DATA =====
  { pattern: /Unexpected token.*JSON/i, severity: 'error' },
  { pattern: /JSON\.parse/i, severity: 'error' },
  { pattern: /is not valid JSON/i, severity: 'error' },
  { pattern: /undefined is not an object/i, severity: 'error' },
  { pattern: /null is not an object/i, severity: 'error' },
  { pattern: /Cannot read propert/i, severity: 'error' },
  { pattern: /Cannot set propert/i, severity: 'error' },

  // ===== DOCKER/CONTAINER =====
  { pattern: /exited with code [1-9]/i, severity: 'error' },
  { pattern: /container.*error/i, severity: 'error' },
  { pattern: /docker.*error/i, severity: 'error' },
  { pattern: /OOMKilled/i, severity: 'error' },
  { pattern: /ContainerCannotRun/i, severity: 'error' },

  // ===== GENERAL PATTERNS =====
  { pattern: /\[error\]/i, severity: 'error' },
  { pattern: /Error:.*at\s+/i, severity: 'error' },
  { pattern: /FATAL/i, severity: 'error' },
  { pattern: /CRITICAL/i, severity: 'error' },
  { pattern: /Exception:/i, severity: 'error' },
  { pattern: /failed with error/i, severity: 'error' },
  { pattern: /error occurred/i, severity: 'error' },
]

// Patterns to ignore (false positives) - EXPANDED LIST
// Be careful not to ignore legitimate errors!
const IGNORE_PATTERNS: RegExp[] = [
  /spawn xdg-open ENOENT/i,
  /spawn open ENOENT/i,
  /npm WARN/i,
  /deprecation warning/i,
  /ExperimentalWarning/i,
  // Vite/dev server normal output
  /VITE.*ready in/i,
  /Local:.*http/i,
  /Network:.*http/i,
  /press h to show help/i,
  /watching for file changes/i,
  /\[vite\] connected/i,
  /\[vite\] hmr update/i,
  /\[vite\] page reload/i,
  // React DevTools (not actual errors)
  /Download the React DevTools/i,
  // Browser console noise
  /favicon\.ico.*404/i,  // Favicon 404 is not a code error
  /DevTools failed to load/i,
  // Successful messages that contain "error" word
  /error handling/i,
  /error handler/i,
  /no errors/i,
  /0 errors/i,
  /fixed.*error/i,
  /errors fixed/i,
  // Logging/debug messages
  /\[debug\]/i,
  /\[info\]/i,
  /\[log\]/i,
]

export function useErrorCollector(options: UseErrorCollectorOptions = {}) {
  const {
    projectId,
    autoCapture = true,
    enabled = true,
    debounceMs = 3000,
    onFixStarted,
    onFixCompleted,
    onFixFailed
  } = options

  const {
    errors,
    addBuildError,
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

  // Get file tree and recently modified files from project store (Bolt.new-style fixer context)
  const { getFileTree, getRecentlyModifiedFiles } = useProjectStore()

  // Buffers for error context
  const outputBufferRef = useRef<string[]>([])
  const errorBufferRef = useRef<{ source: ErrorSource; message: string; timestamp: number }[]>([])
  const currentCommandRef = useRef<string>('')
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null)
  const recentErrorsRef = useRef<Set<string>>(new Set())
  const [isConnected, setIsConnected] = useState(false)

  // Retry limit tracking - max 3 auto-fix attempts per error session
  const MAX_FIX_ATTEMPTS = 3
  const fixAttemptCountRef = useRef(0)
  const [maxRetriesReached, setMaxRetriesReached] = useState(false)

  // Success timer - reset counter only after 10s of no errors
  const successTimerRef = useRef<NodeJS.Timeout | null>(null)
  const SUCCESS_DELAY_MS = 10000 // 10 seconds of no errors = success

  // Server running flag - when true, DON'T trigger auto-fix
  // This prevents fixing when preview is already working
  const serverRunningRef = useRef(false)

  // WebSocket connection for real-time fix notifications
  const wsRef = useRef<WebSocket | null>(null)
  const wsReconnectAttemptsRef = useRef(0)
  const wsReconnectTimerRef = useRef<NodeJS.Timeout | null>(null)

  // Cleanup recent errors periodically
  useEffect(() => {
    const interval = setInterval(() => {
      recentErrorsRef.current.clear()
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  // Store callbacks in refs to avoid dependency issues causing reconnections
  const onFixStartedRef = useRef(onFixStarted)
  const onFixCompletedRef = useRef(onFixCompleted)
  const onFixFailedRef = useRef(onFixFailed)

  // Update refs when callbacks change (without triggering reconnection)
  useEffect(() => {
    onFixStartedRef.current = onFixStarted
    onFixCompletedRef.current = onFixCompleted
    onFixFailedRef.current = onFixFailed
  }, [onFixStarted, onFixCompleted, onFixFailed])

  // WebSocket connection for real-time fix notifications from backend
  // IMPORTANT: Only reconnect when projectId or enabled changes, NOT on callback changes
  useEffect(() => {
    if (!projectId || !enabled) return

    // Prevent duplicate connections
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('[useErrorCollector] WebSocket already connected, skipping')
      return
    }

    const connectWebSocket = () => {
      // Extra guard: don't create new connection if one exists and is connecting/open
      if (wsRef.current && (wsRef.current.readyState === WebSocket.CONNECTING || wsRef.current.readyState === WebSocket.OPEN)) {
        console.log('[useErrorCollector] WebSocket connection in progress or open, skipping')
        return
      }

      try {
        // Build WebSocket URL
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
        const wsHost = apiUrl
          .replace(/^https?:\/\//, '')
          .replace(/\/api\/v1\/?$/, '')
        const wsUrl = `${wsProtocol}//${wsHost}/api/v1/errors/ws/${projectId}`

        console.log('[useErrorCollector] Connecting WebSocket:', wsUrl)

        const ws = new WebSocket(wsUrl)
        wsRef.current = ws

        ws.onopen = () => {
          console.log('[useErrorCollector] WebSocket connected for project:', projectId)
          setIsConnected(true)
          wsReconnectAttemptsRef.current = 0
        }

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data)
            console.log('[useErrorCollector] WebSocket message:', msg)

            // Handle fix notifications from backend (use refs to get latest callbacks)
            if (msg.type === 'fix_started') {
              // Increment fix attempt counter
              fixAttemptCountRef.current++
              console.log('[useErrorCollector] Fix started (attempt', fixAttemptCountRef.current, '/', MAX_FIX_ATTEMPTS, '):', msg.reason)
              setFixing(true)
              onFixStartedRef.current?.(msg.reason || 'Auto-fix started')
            } else if (msg.type === 'fix_completed') {
              console.log('[useErrorCollector] Fix completed (attempt', fixAttemptCountRef.current, '):', msg.patches_applied, 'patches')
              setFixing(false)
              markAllResolved()
              // Clear deduplication cache so same error can trigger another fix if it persists
              recentErrorsRef.current.clear()
              errorBufferRef.current = []
              // Check if max retries reached after this fix
              if (fixAttemptCountRef.current >= MAX_FIX_ATTEMPTS) {
                console.log('[useErrorCollector] Max fix attempts reached, stopping auto-fix')
                setMaxRetriesReached(true)
              }
              onFixCompletedRef.current?.(msg.patches_applied || 0, msg.files_modified || [])
            } else if (msg.type === 'fix_failed') {
              console.log('[useErrorCollector] Fix failed (attempt', fixAttemptCountRef.current, '):', msg.error)
              setFixing(false)
              // Clear deduplication cache so same error can trigger another fix attempt
              recentErrorsRef.current.clear()
              errorBufferRef.current = []
              // Check if max retries reached
              if (fixAttemptCountRef.current >= MAX_FIX_ATTEMPTS) {
                console.log('[useErrorCollector] Max fix attempts reached, stopping auto-fix')
                setMaxRetriesReached(true)
              }
              onFixFailedRef.current?.(msg.error || 'Fix failed')
            } else if (msg.type === 'rebuild_completed') {
              // App rebuilt - start success timer instead of immediate reset
              // Only reset counter if NO errors occur for 10 seconds
              // This prevents infinite loops where same error triggers fix forever
              console.log('[useErrorCollector] Rebuild completed, starting success timer (10s)')

              // Cancel any existing success timer
              if (successTimerRef.current) {
                clearTimeout(successTimerRef.current)
              }

              // Start new success timer - reset counter only if no errors for 10s
              successTimerRef.current = setTimeout(() => {
                console.log('[useErrorCollector] SUCCESS: No errors for 10s, resetting fix counter')
                fixAttemptCountRef.current = 0
                setMaxRetriesReached(false)
                successTimerRef.current = null
              }, SUCCESS_DELAY_MS)
            }
          } catch (e) {
            console.error('[useErrorCollector] Failed to parse WebSocket message:', e)
          }
        }

        ws.onclose = () => {
          console.log('[useErrorCollector] WebSocket disconnected')
          setIsConnected(false)
          wsRef.current = null

          // Reconnect with exponential backoff (max 5 attempts)
          if (wsReconnectAttemptsRef.current < 5) {
            const delay = 2000 * Math.pow(2, wsReconnectAttemptsRef.current)
            wsReconnectAttemptsRef.current++
            console.log(`[useErrorCollector] Reconnecting in ${delay}ms (attempt ${wsReconnectAttemptsRef.current})`)
            wsReconnectTimerRef.current = setTimeout(connectWebSocket, delay)
          }
        }

        ws.onerror = (error) => {
          console.error('[useErrorCollector] WebSocket error:', error)
        }
      } catch (error) {
        console.error('[useErrorCollector] Failed to connect WebSocket:', error)
      }
    }

    // Initial connection
    connectWebSocket()

    // Cleanup on unmount or projectId change
    return () => {
      if (wsReconnectTimerRef.current) {
        clearTimeout(wsReconnectTimerRef.current)
        wsReconnectTimerRef.current = null
      }
      if (successTimerRef.current) {
        clearTimeout(successTimerRef.current)
        successTimerRef.current = null
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsConnected(false)
    }
  }, [projectId, enabled, setFixing, markAllResolved]) // Removed callback dependencies - use refs instead

  // Watch terminal logs for errors AND capture output buffer (legacy support)
  useEffect(() => {
    if (!autoCapture || !enabled) return

    const latestLogs = logs.slice(-20)  // Check last 20 logs
    latestLogs.forEach(log => {
      const content = log.content

      // Add ALL logs to output buffer for context (not just errors)
      if (content && !outputBufferRef.current.includes(content)) {
        outputBufferRef.current.push(content)
        if (outputBufferRef.current.length > 200) {
          outputBufferRef.current.shift()
        }
      }

      // Detect errors
      if (log.type === 'error' || log.type === 'output') {
        const isBuildError = ERROR_PATTERNS.some(({ pattern }) => pattern.test(content))

        if (isBuildError) {
          addBuildError(content)
        } else if (content.includes('Error:') || content.includes('error:') || content.includes('[ERROR]') || content.includes('No matching export')) {
          addTerminalError(content)
        }
      }
    })
  }, [logs, autoCapture, enabled, addBuildError, addTerminalError])

  /**
   * Set current command being executed (for context)
   */
  const setCurrentCommand = useCallback((command: string) => {
    currentCommandRef.current = command
  }, [])

  /**
   * Add output to buffer (for context)
   */
  const addOutput = useCallback((output: string) => {
    if (!enabled || !output) return

    outputBufferRef.current.push(output)
    if (outputBufferRef.current.length > 200) {
      outputBufferRef.current.shift()
    }
  }, [enabled])

  /**
   * Check if output should be ignored
   */
  const shouldIgnore = useCallback((message: string): boolean => {
    return IGNORE_PATTERNS.some(pattern => pattern.test(message))
  }, [])

  /**
   * Detect error severity from message
   */
  const detectSeverity = useCallback((message: string): ErrorSeverity => {
    for (const { pattern, severity } of ERROR_PATTERNS) {
      if (pattern.test(message)) {
        return severity
      }
    }
    return 'info'
  }, [])

  /**
   * SINGLE ENTRY POINT: Report an error from any source
   * This is the main method for reporting errors
   */
  const reportError = useCallback((
    source: ErrorSource,
    message: string,
    opts?: {
      file?: string
      line?: number
      column?: number
      stack?: string
      severity?: ErrorSeverity
    }
  ) => {
    if (!enabled || !message) return
    if (shouldIgnore(message)) return

    // Deduplicate
    const errorKey = `${source}:${message.slice(0, 100)}`
    if (recentErrorsRef.current.has(errorKey)) return
    recentErrorsRef.current.add(errorKey)

    // Cancel success timer - error occurred so build is NOT successful
    if (successTimerRef.current) {
      console.log('[useErrorCollector] Error detected, cancelling success timer')
      clearTimeout(successTimerRef.current)
      successTimerRef.current = null
    }

    const severity = opts?.severity ?? detectSeverity(message)

    console.log('[useErrorCollector] Error reported:', { source, message: message.slice(0, 100), severity })

    // Add to error buffer
    errorBufferRef.current.push({
      source,
      message,
      timestamp: Date.now()
    })
    if (errorBufferRef.current.length > 20) {
      errorBufferRef.current.shift()
    }

    // Also add to output buffer
    outputBufferRef.current.push(message)
    if (outputBufferRef.current.length > 200) {
      outputBufferRef.current.shift()
    }

    // Add to error store based on source
    if (source === 'build' || source === 'docker') {
      addBuildError(message, opts?.file, opts?.line)
    } else if (source === 'browser') {
      // Browser errors use addBrowserError which accepts file/line/column/stack
      const { addBrowserError } = useErrorStore.getState()
      addBrowserError(message, opts?.file, opts?.line, opts?.column, opts?.stack)
    } else if (source === 'network') {
      // Network errors require a URL - use file field if available, otherwise empty string
      addNetworkError(message, opts?.file || '', undefined, undefined)
    } else {
      addTerminalError(message)
    }

    // Schedule debounced forward to backend
    scheduleForwardToBackend()
  }, [enabled, shouldIgnore, detectSeverity, addBuildError, addNetworkError, addTerminalError])

  /**
   * Detect and report errors in terminal output
   * Returns true if error was detected
   */
  const detectAndReport = useCallback((output: string, source: ErrorSource = 'build'): boolean => {
    if (!enabled || !output) return false

    // Add to output buffer regardless
    addOutput(output)

    if (shouldIgnore(output)) return false

    // Check for error patterns
    for (const { pattern, severity } of ERROR_PATTERNS) {
      if (pattern.test(output)) {
        reportError(source, output, { severity })
        return true
      }
    }

    return false
  }, [enabled, addOutput, shouldIgnore, reportError])

  /**
   * Schedule debounced forward to backend
   */
  const scheduleForwardToBackend = useCallback(() => {
    if (!projectId) return

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    debounceTimerRef.current = setTimeout(() => {
      forwardErrorToBackend()
      debounceTimerRef.current = null
    }, debounceMs)
  }, [projectId, debounceMs])

  /**
   * Forward errors to backend for auto-fix
   * Uses the unified /errors/report endpoint
   * Includes file tree and recently modified files for Bolt.new-style fixer context
   */
  const forwardErrorToBackend = useCallback(async () => {
    if (!projectId || errorBufferRef.current.length === 0) return

    // NOTE: We allow auto-fix even when server is running!
    // Runtime errors (API errors, TypeError, etc.) should still be fixed
    // The fix will be applied via HMR without full restart

    // Check if max retries reached - stop auto-fix
    if (fixAttemptCountRef.current >= MAX_FIX_ATTEMPTS) {
      console.log('[useErrorCollector] Skipping auto-fix: max retries reached (', fixAttemptCountRef.current, '/', MAX_FIX_ATTEMPTS, ')')
      return
    }

    const fullContext = outputBufferRef.current.join('\n')
    const errors = errorBufferRef.current.map(e => ({
      source: e.source,
      type: 'auto_detected',
      message: e.message,
      severity: detectSeverity(e.message),
      timestamp: e.timestamp
    }))

    // Get file tree and recently modified files for fixer context (Bolt.new style!)
    const fileTree = getFileTree()
    const recentlyModified = getRecentlyModifiedFiles(5 * 60 * 1000) // Last 5 minutes

    console.log('[useErrorCollector] Forwarding to backend:', {
      projectId,
      errorCount: errors.length,
      contextLines: outputBufferRef.current.length,
      fileTreeCount: fileTree.length,
      recentlyModifiedCount: recentlyModified.length
    })

    try {
      onFixStarted?.(errors[errors.length - 1]?.message?.slice(0, 100) || 'Auto-fix started')

      const response = await apiClient.post<{
        success: boolean
        fix_triggered: boolean
        fix_status?: string
        message: string
      }>(`/errors/report/${projectId}`, {
        errors,
        context: fullContext,
        command: currentCommandRef.current,
        timestamp: Date.now(),
        // Bolt.new-style fixer context
        file_tree: fileTree,
        recently_modified: recentlyModified.map(f => ({
          path: f.path,
          action: f.action,
          timestamp: f.timestamp
        }))
      })

      console.log('[useErrorCollector] Backend response:', response)

      // Clear error buffer after successful forward
      errorBufferRef.current = []

      return response
    } catch (error) {
      console.error('[useErrorCollector] Failed to forward errors:', error)
      onFixFailed?.(String(error))
    }
  }, [projectId, detectSeverity, onFixStarted, onFixFailed, getFileTree, getRecentlyModifiedFiles])

  /**
   * Force immediate forward (use when command completes)
   */
  const forwardNow = useCallback(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
    forwardErrorToBackend()
  }, [forwardErrorToBackend])

  /**
   * Clear all buffers
   */
  const clearBuffers = useCallback(() => {
    outputBufferRef.current = []
    errorBufferRef.current = []
    recentErrorsRef.current.clear()
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
      debounceTimerRef.current = null
    }
    clearErrors()
  }, [clearErrors])

  // Fix a single error using Fixer Agent (legacy support)
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
    onFixStarted?.(`Fixing ${unresolvedErrors.length} errors`)

    try {
      // Use unified error endpoint
      const response = await apiClient.post<FixErrorResponse>(`/errors/report/${projectId}`, {
        errors: unresolvedErrors.map(err => ({
          source: err.source || 'build',
          type: 'manual_fix',
          message: err.message,
          file: err.file,
          line: err.line,
          column: err.column,
          stack: err.stack,
          severity: err.severity || 'error'
        })),
        context: unresolvedErrors.map(e => e.message).join('\n'),
        timestamp: Date.now()
      })

      if (response.success) {
        markAllResolved()
        onFixCompleted?.(response.patches_applied || 0, response.files_modified || [])
      } else {
        onFixFailed?.(response.message || 'Fix failed')
      }

      return response
    } catch (err: any) {
      console.error('[useErrorCollector] Fix all errors failed:', err)
      onFixFailed?.(err.message || 'Failed to fix errors')
      return {
        success: false,
        message: err.message || 'Failed to fix errors'
      }
    } finally {
      setFixing(false)
    }
  }, [projectId, setFixing, getUnresolvedErrors, markAllResolved, onFixStarted, onFixCompleted, onFixFailed])

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

  // Get error context for AI
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

    if (error.source === 'network') {
      if (error.url) context += `URL: ${error.url}\n`
      if (error.method) context += `HTTP Method: ${error.method}\n`
      if (error.status) context += `HTTP Status: ${error.status}\n`
    }

    if (error.stack) {
      context += `\nStack trace:\n${error.stack}\n`
    }

    return context
  }, [])

  /**
   * Reset the retry counter - allows auto-fix to run again
   * Call this when user manually intervenes or wants to retry
   */
  const resetRetryCount = useCallback(() => {
    console.log('[useErrorCollector] Resetting fix attempt counter')
    fixAttemptCountRef.current = 0
    setMaxRetriesReached(false)
  }, [])

  return {
    // State
    errors,
    unresolvedErrors: getUnresolvedErrors(),
    errorCount: getErrorCount(),
    isFixing,
    selectedErrorId,
    isConnected,
    maxRetriesReached, // True when auto-fix has given up
    fixAttemptCount: fixAttemptCountRef.current,

    // SINGLE ENTRY POINT - Primary methods
    reportError,          // Report any error
    detectAndReport,      // Auto-detect and report
    forwardErrorToBackend, // Manual forward to backend
    forwardNow,           // Force immediate forward

    // Buffer management
    addOutput,
    setCurrentCommand,
    clearBuffers,
    getOutputBuffer: () => [...outputBufferRef.current],
    getErrorBuffer: () => [...errorBufferRef.current],

    // Actions (legacy support)
    fixError,
    fixAllErrors,
    markResolved,
    markAllResolved,
    clearErrors,
    selectError,
    addNetworkError,

    // Utilities
    formatError,
    getErrorContext,

    // Retry management
    resetRetryCount,  // Reset retry counter to allow auto-fix again

    // Server state management - prevents auto-fix when preview is working
    setServerRunning: (running: boolean) => {
      console.log('[useErrorCollector] Server running:', running)
      serverRunningRef.current = running
      // If server starts running, also start success timer
      if (running && !successTimerRef.current) {
        successTimerRef.current = setTimeout(() => {
          console.log('[useErrorCollector] SUCCESS: Server stable for 10s, resetting counter')
          fixAttemptCountRef.current = 0
          setMaxRetriesReached(false)
          successTimerRef.current = null
        }, SUCCESS_DELAY_MS)
      }
    },
    isServerRunning: () => serverRunningRef.current
  }
}

export default useErrorCollector
