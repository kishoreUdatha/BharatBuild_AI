'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Play,
  Square,
  RefreshCw,
  Loader2,
  Wrench,
  Zap,
  RotateCcw,
  AlertTriangle,
  Lock
} from 'lucide-react'
import { useProjectStore } from '@/store/projectStore'
import { useErrorCollector } from '@/hooks/useErrorCollector'
import { usePlanStatus } from '@/hooks/usePlanStatus'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
// Sandbox preview URL base (for local development, production uses domain-based URLs from backend)
const SANDBOX_PREVIEW_BASE = process.env.NEXT_PUBLIC_SANDBOX_URL || 'http://localhost'
const FRONTEND_URL = process.env.NEXT_PUBLIC_FRONTEND_URL || (typeof window !== 'undefined' ? window.location.origin : '')

// Check if we're in production (not localhost)
const isProduction = (): boolean => {
  if (typeof window === 'undefined') return false
  const hostname = window.location.hostname
  return hostname !== 'localhost' && hostname !== '127.0.0.1'
}

// Helper to construct preview URL with correct base
// In production: uses path-based URL through API proxy
// In development: uses localhost:port
const getPreviewUrl = (port: number | string, projectId?: string): string => {
  if (isProduction() && projectId) {
    // Production: Use path-based preview URL through API proxy
    // Subdomain-based URLs require wildcard DNS which isn't configured
    return `https://app.bharatbuild.ai/api/v1/preview/${projectId}/`
  }
  // Development: Use localhost
  const base = SANDBOX_PREVIEW_BASE.replace(/:\d+$/, '').replace(/\/$/, '')
  return `${base}:${port}`
}

// Parse _PREVIEW_URL_ marker from backend output (production uses domain-based URLs)
const parsePreviewUrl = (output: string): string | null => {
  // Match _PREVIEW_URL_:URL pattern (new format)
  const previewMatch = output.match(/_PREVIEW_URL_:(.+)/)
  if (previewMatch && previewMatch[1]) {
    return previewMatch[1].trim()
  }
  // Legacy format: __SERVER_STARTED__:URL
  const legacyMatch = output.match(/__SERVER_STARTED__:(.+)/)
  if (legacyMatch && legacyMatch[1]) {
    return legacyMatch[1].trim()
  }
  return null
}

// Parse __PREVIEW_READY__ marker - only navigate to preview when this is received
// This ensures the server has passed health checks and is ready to serve content
const parsePreviewReady = (output: string): string | null => {
  const readyMatch = output.match(/__PREVIEW_READY__:(.+)/)
  if (readyMatch && readyMatch[1]) {
    return readyMatch[1].trim()
  }
  return null
}

// Parse __MOBILE_QR__ marker - QR code data for React Native/Expo mobile preview
const parseMobileQR = (output: string): string | null => {
  const qrMatch = output.match(/__MOBILE_QR__:(.+)/)
  if (qrMatch && qrMatch[1]) {
    return qrMatch[1].trim()
  }
  return null
}

// Parse __EXPO_URL__ marker - Expo URL for mobile preview
const parseExpoUrl = (output: string): string | null => {
  const urlMatch = output.match(/__EXPO_URL__:(.+)/)
  if (urlMatch && urlMatch[1]) {
    return urlMatch[1].trim()
  }
  return null
}

// COST OPTIMIZATION: Increased to 6 for Java/Spring Boot projects with complex multi-file dependencies
// Java projects often need more attempts due to Entity/DTO/Service/Controller consistency requirements
const MAX_AUTO_FIX_ATTEMPTS = 6
const DEFAULT_RETRY_DELAY = 1500  // Base delay between retries (ms)
const MAX_RETRY_DELAY = 10000     // Max delay with exponential backoff (ms)
const MAX_ERROR_BUFFER_SIZE = 50  // Max lines in error buffer to prevent memory leaks
const MAX_OUTPUT_BUFFER_SIZE = 100 // Max lines in output buffer

// Error severity classification
type ErrorSeverity = 'warning' | 'build_error' | 'runtime_error' | 'fatal'
type ExecutionMode = 'docker' | 'direct'
type RunStatus = 'idle' | 'creating' | 'starting' | 'running' | 'stopping' | 'stopped' | 'error' | 'fixing'

interface ErrorInfo {
  message: string
  stackTrace: string
  detectedAt: Date
  severity: ErrorSeverity
  phase: 'install' | 'build' | 'runtime' | 'unknown'
}

interface MobilePreviewInfo {
  expoUrl: string
  qrBase64: string
}

interface ProjectRunControlsProps {
  onOpenTerminal?: () => void
  onPreviewUrlChange?: (url: string | null) => void
  onMobilePreviewChange?: (mobilePreview: MobilePreviewInfo | null) => void  // For React Native QR code
  onOutput?: (line: string) => void
  autoFix?: boolean // Enable automatic error fixing
  onStartSession?: () => void  // Called when run starts to keep terminal open
  onEndSession?: () => void    // Called when run ends (terminal stays open)
  onClearLogs?: () => void     // Called to clear terminal logs for fresh run
}

export function ProjectRunControls({ onOpenTerminal, onPreviewUrlChange, onMobilePreviewChange, onOutput, autoFix = true, onStartSession, onEndSession, onClearLogs }: ProjectRunControlsProps) {
  const { currentProject, loadFromBackend } = useProjectStore()
  const [status, setStatus] = useState<RunStatus>('idle')

  // Check if user has code execution feature (Premium only)
  const { features, isPremium, isLoading: planLoading } = usePlanStatus()
  const canRunCode = isPremium || features?.code_execution === true
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [executionMode, setExecutionMode] = useState<ExecutionMode>('docker')
  const [dockerAvailable, setDockerAvailable] = useState<boolean | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Mobile preview state for React Native/Expo projects
  const [mobilePreview, setMobilePreview] = useState<MobilePreviewInfo | null>(null)
  const pendingQRRef = useRef<string | null>(null)  // Buffer for QR data before URL arrives

  // Auto-fix state with synchronized refs and state
  const [lastError, setLastError] = useState<ErrorInfo | null>(null)
  const [fixAttempts, setFixAttempts] = useState(0)
  const fixAttemptsRef = useRef(0) // Ref for synchronous access (React state updates are async!)
  const [isFixing, setIsFixing] = useState(false)
  const isFixingRef = useRef(false) // Ref for synchronous fix lock (Gap #9: prevent concurrent fixes)
  const fixLockTimeRef = useRef<number>(0) // High #5: Timestamp when fix lock acquired
  const FIX_LOCK_TIMEOUT_MS = 180000 // High #5: 180 second timeout for fix lock (increased from 60s for slow API)
  const [maxAttemptsReached, setMaxAttemptsReached] = useState(false)
  const errorBufferRef = useRef<string[]>([]) // Collect error lines
  const outputBufferRef = useRef<string[]>([]) // Collect ALL recent output for context
  const pendingRestartRef = useRef<boolean>(false) // Flag for auto-restart after fix
  const consecutiveFailuresRef = useRef<number>(0) // Track consecutive failures for backoff
  const isRetryingRef = useRef<boolean>(false) // Prevent duplicate retries
  const forwardDebounceRef = useRef<NodeJS.Timeout | null>(null) // Debounce error forwarding
  const fixRequestIdRef = useRef<number>(0) // Unique ID for fix requests (deduplication)
  const serverStartedRef = useRef<boolean>(false) // Track if server has started (Gap #3)
  const buildFailedRef = useRef<boolean>(false) // Track if build actually failed (prevents false SUCCESS)

  // Calculate exponential backoff delay
  const getRetryDelay = useCallback((failureCount: number): number => {
    // Exponential backoff: 1.5s, 3s, 6s, 10s (capped)
    const delay = Math.min(
      DEFAULT_RETRY_DELAY * Math.pow(2, failureCount),
      MAX_RETRY_DELAY
    )
    return delay
  }, [])

  // ============= CENTRALIZED ERROR HANDLING FOR AUTO-FIX =============
  // Single entry point for all error collection and auto-fix
  const {
    reportError,
    detectAndReport,
    addOutput: addErrorOutput,
    setCurrentCommand: setErrorCommand,
    forwardNow,
    clearBuffers,
    isConnected: errorCollectorConnected,
    setServerRunning  // Prevents auto-fix when preview is working
  } = useErrorCollector({
    projectId: currentProject?.id,
    enabled: !!currentProject?.id && autoFix,
    debounceMs: 800,
    onFixStarted: (reason) => {
      console.log('[ProjectRunControls] Auto-fix started:', reason)
      setStatus('fixing')
      onOutput?.(`\n🔧 Auto-fix started: ${reason}`)
    },
    onFixCompleted: (patchesApplied, filesModified) => {
      console.log('[ProjectRunControls] Auto-fix completed:', patchesApplied, 'patches')
      onOutput?.(`✅ Auto-fix completed! ${patchesApplied} patches applied`)
      if (filesModified.length > 0) {
        onOutput?.(`📄 Files modified: ${filesModified.join(', ')}`)
      }

      // Only restart if server is NOT already running
      // If server is running, HMR will pick up the changes automatically
      if (!serverStartedRef.current) {
        pendingRestartRef.current = true
        onOutput?.('\n🚀 Restarting project with fixes...\n')
      } else {
        onOutput?.('\n✨ Fix applied! HMR will reload automatically.\n')
        setStatus('running')  // Keep status as running
      }

      setFixAttempts(0)
      setLastError(null)
      setMaxAttemptsReached(false)
      errorBufferRef.current = []
      outputBufferRef.current = []
      // Clear any pending debounce timer
      if (forwardDebounceRef.current) {
        clearTimeout(forwardDebounceRef.current)
        forwardDebounceRef.current = null
      }
    },
    onFixFailed: (error) => {
      console.log('[ProjectRunControls] Auto-fix failed:', error)
      onOutput?.(`❌ Auto-fix failed: ${error}`)
      setStatus('error')
    }
  })

  // Check if Docker is available on mount
  // On Windows, default to direct execution since Docker Desktop is often not installed
  useEffect(() => {
    // Check if running on Windows - default to direct execution
    const isWindows = typeof window !== 'undefined' && navigator.platform.toLowerCase().includes('win')
    if (isWindows) {
      console.log('[Docker] Windows detected, defaulting to direct execution')
      setDockerAvailable(false)
      setExecutionMode('direct')
      return
    }
    checkDockerAvailability()
  }, [])

  const checkDockerAvailability = async () => {
    try {
      // Use AbortController for timeout (2 seconds max - faster timeout)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 2000)

      // Try to check container status - if it fails with 503/500, Docker is not available
      const response = await fetch(`${API_BASE_URL}/containers/test-docker/status`, {
        method: 'GET',
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      // If we get 404, that's fine - Docker is available but no container exists
      // If we get 503 (Service Unavailable) or 500 with "Docker", Docker is not installed
      if (response.status === 503 || response.status === 500) {
        const error = await response.json()
        if (error.detail?.toLowerCase().includes('docker')) {
          console.log('[Docker] Not available, falling back to direct execution')
          setDockerAvailable(false)
          setExecutionMode('direct')
          return
        }
      }
      setDockerAvailable(true)
      console.log('[Docker] Available')
    } catch (e: any) {
      // Network error, timeout, or backend down - assume Docker is NOT available to be safe
      if (e.name === 'AbortError') {
        console.log('[Docker] Check timed out, assuming unavailable')
      } else {
        console.log('[Docker] Check failed, assuming unavailable:', e)
      }
      setDockerAvailable(false)
      setExecutionMode('direct')
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
  // Gap #3: Track server start state to avoid race condition with error detection
  const detectServerStart = useCallback((output: string) => {
    // Strip ANSI escape codes for pattern matching (Vite uses colored output)
    const stripAnsi = (str: string) => str.replace(/\x1b\[[0-9;]*[a-zA-Z]|\x1b\].*?\x07|\r/g, '')
    const cleanOutput = stripAnsi(output)

    console.log('[DetectServer] Checking output:', cleanOutput.substring(0, 100))

    // FIRST: Check for __PREVIEW_READY__ marker - this means health check passed
    const readyUrl = parsePreviewReady(cleanOutput)
    if (readyUrl) {
      console.log('[DetectServer] Found __PREVIEW_READY__ marker - server is ready:', readyUrl)
      serverStartedRef.current = true
      setPreviewUrl(readyUrl)
      setStatus('running')
      onPreviewUrlChange?.(readyUrl)
      // IMPORTANT: Tell error collector server is running - stops auto-fix
      setServerRunning(true)
      return true
    }

    // MOBILE PREVIEW: Check for __MOBILE_QR__ marker (React Native/Expo)
    const qrData = parseMobileQR(cleanOutput)
    if (qrData) {
      console.log('[DetectServer] Found __MOBILE_QR__ marker')
      pendingQRRef.current = qrData
    }

    // MOBILE PREVIEW: Check for __EXPO_URL__ marker and combine with QR data
    const expoUrl = parseExpoUrl(cleanOutput)
    if (expoUrl && pendingQRRef.current) {
      console.log('[DetectServer] Found __EXPO_URL__ marker, activating mobile preview:', expoUrl)
      const mobilePreviewData = { expoUrl, qrBase64: pendingQRRef.current }
      setMobilePreview(mobilePreviewData)
      onMobilePreviewChange?.(mobilePreviewData)
      pendingQRRef.current = null  // Clear pending QR after using
      serverStartedRef.current = true
      setStatus('running')
      // IMPORTANT: Tell error collector server is running - stops auto-fix
      setServerRunning(true)
      return true
    }

    // SECOND: Check for _PREVIEW_URL_ marker - just set the URL but don't mark as fully ready yet
    const backendUrl = parsePreviewUrl(cleanOutput)
    if (backendUrl && !serverStartedRef.current) {
      console.log('[DetectServer] Found _PREVIEW_URL_ marker (waiting for ready):', backendUrl)
      setPreviewUrl(backendUrl)  // Set URL for display
      setStatus('starting')      // Keep status as starting until ready
      // Don't call onPreviewUrlChange yet - wait for __PREVIEW_READY__
      return false  // Return false - server not fully ready yet
    }

    // Patterns to detect server URL and extract port (fallback for local development)
    const serverPatterns = [
      /https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)/i,
      /running\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /server\s+(?:started|listening|running)\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /listening\s+(?:on|at)\s+(?:port\s+)?(\d+)/i,
      /(?:localhost|127\.0\.0\.1|0\.0\.0\.0):(\d+)/i,
      /local:\s*https?:\/\/.*:(\d+)/i,
    ]

    // Patterns that indicate server is ready (without needing to extract port)
    const readyPatterns = [
      /vite.*ready/i,                   // "VITE v5.4.6  ready in 234 ms" (flexible spacing)
      /ready\s+in\s+\d+/i,              // "ready in 234 ms" without VITE prefix
      /webpack.*compiled/i,             // "webpack compiled successfully"
      /compiled\s+successfully/i,       // Generic compile success
      /development\s+server\s+running/i, // Next.js style
      /ready\s+on/i,                    // "ready on http://localhost:3000"
      /Local:\s*http/i,                 // Vite "Local: http://localhost:3000/"
      /➜\s+Local:/i,                    // Vite arrow format
    ]

    // Try to extract port from output
    // In production: DON'T set preview URL from these patterns - wait for __PREVIEW_READY__
    // In development: OK to set preview URL directly (no health check markers)
    for (const pattern of serverPatterns) {
      const match = cleanOutput.match(pattern)
      if (match && match[1]) {
        const port = match[1]
        // Pass project ID to get correct production URL
        const url = getPreviewUrl(port, currentProject?.id)
        console.log('[DetectServer] MATCHED serverPattern:', pattern, '-> port:', port, '-> url:', url)
        serverStartedRef.current = true // Gap #3: Mark server as started
        setStatus('running')

        // IMPORTANT: Only call onPreviewUrlChange in DEVELOPMENT mode
        // In production, wait for __PREVIEW_READY__ health check marker
        if (!isProduction()) {
          setPreviewUrl(url)
          onPreviewUrlChange?.(url)
          console.log('[DetectServer] Development mode - showing preview immediately')
        } else {
          // Production: Just mark server as started, preview URL will be set by __PREVIEW_READY__
          console.log('[DetectServer] Production mode - waiting for __PREVIEW_READY__ marker')
        }
        return true
      }
    }

    // Fall back to readyPatterns (when port can't be extracted)
    for (const pattern of readyPatterns) {
      if (pattern.test(cleanOutput)) {
        console.log('[DetectServer] MATCHED readyPattern:', pattern)
        serverStartedRef.current = true // Gap #3: Mark server as started
        // Server is ready, set status to running
        // Port will be fetched from preview endpoint
        setStatus('running')
        return true
      }
    }
    return false
  }, [onPreviewUrlChange, currentProject?.id])

  // ============= BOLT.NEW STYLE ERROR DETECTION =============
  // Track current command for fixer agent
  const currentCommandRef = useRef<string>('')

  // Gap #11: Classify error type for better auto-fix strategy
  const classifyError = useCallback((output: string): { severity: ErrorSeverity; phase: 'install' | 'build' | 'runtime' | 'unknown' } => {
    const lowerOutput = output.toLowerCase()

    // Install phase errors (npm/yarn/pip)
    if (/npm err!|yarn error|pip.*error|could not resolve|enoent.*package/i.test(output)) {
      return { severity: 'build_error', phase: 'install' }
    }

    // Build/compile errors
    if (/failed to compile|syntaxerror|typeerror.*at build|webpack.*error|vite.*error|tsc.*error/i.test(output)) {
      return { severity: 'build_error', phase: 'build' }
    }

    // Runtime errors (after server starts)
    if (serverStartedRef.current && /typeerror|referenceerror|unhandled.*rejection|uncaught.*exception/i.test(output)) {
      return { severity: 'runtime_error', phase: 'runtime' }
    }

    // Fatal errors
    if (/segmentation fault|out of memory|killed|fatal error/i.test(output)) {
      return { severity: 'fatal', phase: 'unknown' }
    }

    // Warnings (non-fatal)
    if (/warn|warning|deprecated/i.test(output) && !/error/i.test(output)) {
      return { severity: 'warning', phase: 'unknown' }
    }

    return { severity: 'build_error', phase: 'unknown' }
  }, [])

  const detectError = useCallback((output: string): boolean => {
    // Gap #2: Expanded ignore patterns to reduce false positives
    const ignoredPatterns = [
      /spawn xdg-open ENOENT/i,      // Vite trying to open browser on Windows
      /spawn open ENOENT/i,          // Same for macOS fallback
      /npm WARN/i,                   // npm warnings are not errors
      /npm notice/i,                 // npm notices
      /npm timing/i,                 // npm timing info
      /deprecation warning/i,        // Deprecation warnings
      /DeprecationWarning/i,         // Node deprecation warnings
      /ExperimentalWarning/i,        // Node experimental features
      /PendingDeprecationWarning/i,  // Pending deprecations
      /warning:.*deprecated/i,       // Generic deprecation warnings
      /punycode.*deprecated/i,       // Common punycode warning
      /\[DEP\d+\]/i,                 // Node deprecation codes
      /peer dep/i,                   // Peer dependency warnings
      /optional dependency/i,        // Optional deps that failed (OK)
      /SKIPPING OPTIONAL/i,          // Skipped optional deps
      /gyp WARN/i,                   // Node-gyp warnings
      /fsevents.*skip/i,             // fsevents on non-Mac
      /enoent.*optional/i,           // Optional file not found
      /warn.*@/i,                    // Package version warnings (@types/node@...)
    ]

    // Check if this is an ignorable warning first
    for (const pattern of ignoredPatterns) {
      if (pattern.test(output)) {
        console.log('[ErrorDetect] ⚪ Ignored (false positive):', output.slice(0, 50))
        return false // Not a real error
      }
    }

    // Terminal/Build errors
    const terminalErrorPatterns = [
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
      /npm ERR!/i,
      /ENOENT/i,
      /EACCES/i,
    ]

    // Docker-specific errors
    const dockerErrorPatterns = [
      /port.*already.*in.*use/i,
      /invalid.*dockerfile/i,
      /missing.*dependencies/i,
      /incorrect.*base.*image/i,
      /build.*failure/i,
      /health.*check.*failing/i,
      /container.*exit.*code.*[1-9]/i,
      /compose.*file.*syntax/i,
      /docker.*daemon/i,
      /no.*such.*image/i,
      /cannot.*connect.*to.*docker/i,
      /failed.*to.*pull/i,
      /EXPOSE.*invalid/i,
    ]

    // Vite/Next/Webpack errors
    const bundlerErrorPatterns = [
      /\[vite\].*error/i,
      /\[webpack\].*error/i,
      /\[next\].*error/i,
      /failed.*to.*resolve.*import/i,
      /transform.*failed/i,
      /internal.*server.*error/i,
      /pre-transform.*error/i,
    ]

    // Python errors
    const pythonErrorPatterns = [
      /file.*not.*found/i,
      /no.*module.*named/i,
      /attributeerror/i,
      /valueerror/i,
      /keyerror/i,
      /indentationerror/i,
      /taberror/i,
      /nameerror/i,
      /zerodivisionerror/i,
      /runtimeerror/i,
      /assertionerror/i,
      /pip.*error/i,
      /poetry.*error/i,
      /django\..*error/i,
      /flask\..*error/i,
      /fastapi.*error/i,
      /pydantic.*error/i,
      /memoryerror/i,  // Medium #15: Python OOM
    ]

    // Medium #15: OOM (Out of Memory) errors
    const oomErrorPatterns = [
      /JavaScript heap out of memory/i,
      /FATAL ERROR.*allocation failed/i,
      /Killed/i,  // Linux OOM killer
      /out of memory/i,
      /Cannot allocate memory/i,
      /ENOMEM/i,  // Node.js memory error
      /java\.lang\.OutOfMemoryError/i,  // Java OOM
    ]

    // Java/Maven/Gradle/Kotlin errors
    const javaErrorPatterns = [
      /BUILD FAILURE/i,              // Maven
      /FAILURE: Build failed/i,      // Gradle
      /compilation failure/i,
      /cannot find symbol/i,
      /package does not exist/i,
      /java\.lang\.\w+Exception/i,
      /ClassNotFoundException/i,
      /NoClassDefFoundError/i,
      /NullPointerException/i,
      /ArrayIndexOutOfBoundsException/i,
      /IllegalArgumentException/i,
      /mvn.*error/i,
      /gradle.*error/i,
      /kotlin.*error/i,
      /spring.*error/i,
    ]

    // Go errors
    const goErrorPatterns = [
      /go:.*error/i,
      /cannot find package/i,
      /undefined:/i,
      /imported and not used/i,
      /declared and not used/i,
      /no required module provides/i,
      /go mod.*error/i,
      /panic:/i,
      /fatal error:/i,
      /build constraints exclude/i,
    ]

    // Rust/Cargo errors
    const rustErrorPatterns = [
      /error\[E\d+\]/i,              // Rust error codes (E0433, etc.)
      /cargo.*error/i,
      /cannot find.*in this scope/i,
      /unresolved import/i,
      /no method named/i,
      /mismatched types/i,
      /borrow.*moved value/i,
      /lifetime.*not live long enough/i,
      /thread.*panicked/i,
    ]

    // Ruby/Rails errors
    const rubyErrorPatterns = [
      /loaderror/i,
      /nameerror.*uninitialized constant/i,
      /nomethoderror/i,
      /argumenterror/i,
      /bundler.*error/i,
      /gem.*error/i,
      /rails.*error/i,
      /activerecord.*error/i,
      /actioncontroller.*error/i,
      /rake.*aborted/i,
    ]

    // PHP/Laravel/Composer errors
    const phpErrorPatterns = [
      /fatal error:/i,
      /parse error:/i,
      /php.*error/i,
      /composer.*error/i,
      /laravel.*error/i,
      /symfony.*error/i,
      /artisan.*error/i,
      /class.*not found/i,
      /call to undefined/i,
    ]

    // C#/.NET errors
    const dotnetErrorPatterns = [
      /error CS\d+/i,                // C# error codes
      /build FAILED/i,
      /dotnet.*error/i,
      /nuget.*error/i,
      /System\..*Exception/i,
      /NullReferenceException/i,
      /InvalidOperationException/i,
      /aspnet.*error/i,
    ]

    // C/C++ errors
    const cppErrorPatterns = [
      /undefined reference/i,
      /fatal error:.*no such file/i,
      /error:.*expected/i,
      /linker error/i,
      /make.*error/i,
      /cmake.*error/i,
      /gcc.*error/i,
      /g\+\+.*error/i,
      /clang.*error/i,
      /segmentation fault/i,
    ]

    // Flutter/Dart errors
    const flutterErrorPatterns = [
      /flutter.*error/i,
      /dart.*error/i,
      /pub.*error/i,
      /analysis_options.*error/i,
      /the.*getter.*isn't defined/i,
      /undefined.*class/i,
      /a value of type.*can't be assigned/i,
    ]

    // Database errors
    const databaseErrorPatterns = [
      /sqlite.*error/i,
      /postgresql.*error/i,
      /mysql.*error/i,
      /mongodb.*error/i,
      /redis.*error/i,
      /connection refused/i,
      /authentication failed/i,
      /relation.*does not exist/i,
      /duplicate key/i,
      /foreign key constraint/i,
    ]

    const allPatterns = [
      ...terminalErrorPatterns,
      ...dockerErrorPatterns,
      ...bundlerErrorPatterns,
      ...pythonErrorPatterns,
      ...javaErrorPatterns,
      ...goErrorPatterns,
      ...rustErrorPatterns,
      ...rubyErrorPatterns,
      ...phpErrorPatterns,
      ...dotnetErrorPatterns,
      ...cppErrorPatterns,
      ...flutterErrorPatterns,
      ...databaseErrorPatterns,
      ...oomErrorPatterns,  // Medium #15: OOM detection
    ]

    // Gap #19: Add ALL output lines to buffer with overflow protection
    outputBufferRef.current.push(output)
    // Keep last N lines to prevent memory leaks on long error sequences
    while (outputBufferRef.current.length > MAX_OUTPUT_BUFFER_SIZE) {
      outputBufferRef.current.shift()
    }

    for (const pattern of allPatterns) {
      if (pattern.test(output)) {
        // Add to local error buffer for UI display with overflow protection
        errorBufferRef.current.push(output)
        while (errorBufferRef.current.length > MAX_ERROR_BUFFER_SIZE) {
          errorBufferRef.current.shift()
        }

        console.log('[ErrorDetect] 🔴 TERMINAL ERROR matched pattern:', pattern.toString())
        console.log('[ErrorDetect]    Output:', output.slice(0, 150))
        console.log('[ErrorDetect]    Command:', currentCommandRef.current)

        // ========== CENTRALIZED ERROR HANDLING ==========
        // The detectAndReport function handles all buffering, debouncing, and forwarding
        // This is the SINGLE ENTRY POINT for error handling
        if (detectAndReport) {
          detectAndReport(output, 'build')
          console.log('[ErrorDetect] ✅ Error sent to centralized ErrorCollector')
        } else {
          console.warn('[ErrorDetect] ⚠️ detectAndReport not available!')
        }

        return true
      }
    }
    return false
  }, [detectAndReport])

  // Reset fix state - synchronizes all refs and state (Gap #1)
  const resetFixState = useCallback(() => {
    // Sync state and refs together
    setFixAttempts(0)
    fixAttemptsRef.current = 0
    setIsFixing(false)
    isFixingRef.current = false
    setLastError(null)
    setMaxAttemptsReached(false)
    errorBufferRef.current = []
    outputBufferRef.current = []
    consecutiveFailuresRef.current = 0
    isRetryingRef.current = false
    serverStartedRef.current = false
    buildFailedRef.current = false // Reset build failure flag
    fixRequestIdRef.current = 0
    // Reset server running state in error collector
    setServerRunning(false)
    // Clear any pending debounce timer
    if (forwardDebounceRef.current) {
      clearTimeout(forwardDebounceRef.current)
      forwardDebounceRef.current = null
    }
    // Clear centralized error collector buffers
    clearBuffers?.()
    console.log('[ResetFixState] All refs and state synchronized')
  }, [clearBuffers, setServerRunning])

  // ============= BOLT.NEW STYLE AUTO-FIX HANDLER =============
  const attemptAutoFix = useCallback(async (errorMessage: string, stackTrace: string) => {
    if (!currentProject?.id || !autoFix) {
      return false
    }

    // Gap #9 + High #5: Prevent concurrent fix attempts with lock + timeout
    if (isFixingRef.current) {
      // High #5: Check if lock is stale (older than timeout)
      const lockAge = Date.now() - fixLockTimeRef.current
      if (lockAge > FIX_LOCK_TIMEOUT_MS) {
        console.log(`[AutoFix] Lock stale (${lockAge}ms), releasing and proceeding`)
        isFixingRef.current = false
        fixLockTimeRef.current = 0
      } else {
        console.log('[AutoFix] Fix already in progress, skipping duplicate request')
        return false
      }
    }

    // Use ref for synchronous check (React state updates are async!)
    if (fixAttemptsRef.current >= MAX_AUTO_FIX_ATTEMPTS) {
      setMaxAttemptsReached(true)
      onOutput?.('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
      onOutput?.(`❌ Max auto-fix attempts (${MAX_AUTO_FIX_ATTEMPTS}) reached.`)
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

    // Gap #9 + High #5: Acquire fix lock with timestamp and generate unique request ID
    isFixingRef.current = true
    fixLockTimeRef.current = Date.now() // High #5: Record when lock acquired
    fixRequestIdRef.current += 1
    const thisRequestId = fixRequestIdRef.current

    // Increment ref FIRST (synchronous), then state (for UI)
    fixAttemptsRef.current += 1
    const currentAttempt = fixAttemptsRef.current

    setIsFixing(true)
    setStatus('fixing')
    setFixAttempts(currentAttempt) // Sync state with ref
    onOutput?.('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    onOutput?.(`🔧 AUTO-FIX ATTEMPT ${currentAttempt}/${MAX_AUTO_FIX_ATTEMPTS}`)
    onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
    onOutput?.('🤖 Fixer Agent analyzing error...')
    onOutput?.(`📋 Command: ${currentCommandRef.current || 'unknown'}`)

    try {
      const token = localStorage.getItem('access_token')

      // Send Bolt.new style payload with command and error logs
      const response = await fetch(`${API_BASE_URL}/execution/fix/${currentProject.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          error_message: errorMessage,
          stack_trace: stackTrace,
          command: currentCommandRef.current || 'unknown',  // Bolt.new style: include command
          error_logs: errorBufferRef.current.slice(-20),    // Bolt.new style: include recent error logs
        })
      })

      if (!response.ok) {
        const error = await response.json()
        onOutput?.(`❌ Fix failed: ${error.detail || 'Unknown error'}`)
        setIsFixing(false)
        isFixingRef.current = false // Release lock
        setStatus('error')
        return false
      }

      // Gap #9: Check if this request is still valid (not superseded)
      if (thisRequestId !== fixRequestIdRef.current) {
        console.log('[AutoFix] Request superseded, ignoring result')
        isFixingRef.current = false
        return false
      }

      const result = await response.json()

      if (!result.success) {
        onOutput?.(`❌ Fixer Agent: ${result.error || 'Could not generate fix'}`)
        if (result.suggestion) {
          onOutput?.(`💡 Suggestion: ${result.suggestion}`)
        }
        setIsFixing(false)
        isFixingRef.current = false // Release lock
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

      // Reload project files to reflect changes (use /load endpoint to get files with content)
      try {
        const { apiClient } = await import('@/lib/api-client')
        const projectData = await apiClient.loadProjectWithFiles(currentProject.id)
        loadFromBackend(projectData)
        onOutput?.('🔄 Project files reloaded')
      } catch (e) {
        onOutput?.('⚠️ Could not reload project files')
      }

      setIsFixing(false)
      isFixingRef.current = false // Release lock
      setLastError(null)
      errorBufferRef.current = []

      // Auto-restart after fix
      onOutput?.('\n🚀 Restarting project with fixes...\n')
      return true

    } catch (error: any) {
      onOutput?.(`❌ Auto-fix error: ${error.message}`)
      setIsFixing(false)
      isFixingRef.current = false // Release lock
      setStatus('error')
      return false
    }
  }, [currentProject?.id, autoFix, fixAttempts, onOutput, loadFromBackend])

  // ============= LOAD FILES FROM BACKEND =============
  const loadFilesFromBackend = async (): Promise<boolean> => {
    if (!currentProject?.id) return false

    onOutput?.('📥 Loading project files from backend...')

    try {
      const { apiClient } = await import('@/lib/api-client')
      // Use loadProjectWithFiles which calls /projects/{id}/load - returns project + all files with content
      const projectData = await apiClient.loadProjectWithFiles(currentProject.id)

      if (projectData?.files && projectData.files.length > 0) {
        loadFromBackend(projectData)
        onOutput?.(`✅ Loaded ${projectData.files.length} files from backend`)
        return true
      } else {
        onOutput?.('⚠️ No files found in backend')
        return false
      }
    } catch (error: any) {
      onOutput?.(`⚠️ Could not load files from backend: ${error.message}`)
      return false
    }
  }

  // ============= SYNC FILES TO WORKSPACE =============
  const syncFilesToWorkspace = async (): Promise<boolean> => {
    // First check if we have files in memory
    if (!currentProject?.files || currentProject.files.length === 0) {
      onOutput?.('⚠️ No files in memory, trying to load from backend...')
      // Try to load files from backend
      const loaded = await loadFilesFromBackend()
      if (!loaded) {
        onOutput?.('❌ No files available to sync')
        return false
      }
    }

    // Re-check after potential load (need to get fresh data from store)
    const { currentProject: freshProject } = useProjectStore.getState()
    if (!freshProject?.files || freshProject.files.length === 0) {
      onOutput?.('❌ Still no files after backend load')
      return false
    }

    const token = localStorage.getItem('access_token')
    onOutput?.(`📁 Syncing ${freshProject.files.length} files to workspace...`)

    try {
      // Use batch write endpoint for efficiency
      const response = await fetch(`${API_BASE_URL}/containers/${freshProject.id}/files/batch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          files: freshProject.files.map(f => ({
            path: f.path,
            content: f.content || ''
          }))
        })
      })

      if (!response.ok) {
        const error = await response.json()
        onOutput?.(`⚠️ Sync failed: ${error.detail || 'Unknown error'}`)
        return false
      }

      const result = await response.json()
      onOutput?.(`✅ Synced ${result.success}/${result.total} files`)

      // HIGH #8: Verify all files were written and wait for filesystem consistency
      if (result.success !== result.total) {
        onOutput?.(`⚠️ Warning: Only ${result.success}/${result.total} files synced`)
      }

      // HIGH #2: Verify critical files exist in container (package.json for Node projects)
      const criticalFiles = freshProject.files.filter(f =>
        f.path === 'package.json' ||
        f.path === 'requirements.txt' ||
        f.path === 'pom.xml' ||
        f.path === 'build.gradle'
      )

      if (criticalFiles.length > 0 && result.success > 0) {
        onOutput?.('  Verifying file sync...')
        await new Promise(resolve => setTimeout(resolve, 300))

        // HIGH #2: Quick verification - check if package.json exists
        try {
          const verifyResponse = await fetch(`${API_BASE_URL}/containers/${freshProject.id}/files/verify`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              ...(token && { 'Authorization': `Bearer ${token}` })
            },
            body: JSON.stringify({
              paths: criticalFiles.map(f => f.path)
            })
          })

          if (verifyResponse.ok) {
            const verifyResult = await verifyResponse.json()
            if (verifyResult.all_exist) {
              onOutput?.('  ✓ Critical files verified')
            } else {
              onOutput?.(`  ⚠️ Some files not found: ${verifyResult.missing?.join(', ')}`)
              // Retry sync for missing files
              if (verifyResult.missing?.length > 0) {
                onOutput?.('  Retrying sync for missing files...')
                await new Promise(resolve => setTimeout(resolve, 500))
              }
            }
          }
        } catch {
          // Verification endpoint may not exist, continue anyway
          onOutput?.('  Waiting for filesystem sync...')
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      } else {
        // HIGH #8: Wait for filesystem to stabilize before npm install
        // This prevents race conditions where npm install starts before files are fully written
        if (result.success > 0) {
          onOutput?.('  Waiting for filesystem sync...')
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      }

      return result.success > 0
    } catch (error: any) {
      onOutput?.(`⚠️ Sync error: ${error.message}`)
      return false
    }
  }

  // ============= DOCKER EXECUTION =============
  const runWithDocker = async (): Promise<{ success: boolean; error?: string }> => {
    if (!currentProject?.id) return { success: false, error: 'No project' }

    // Reset error buffer for this execution
    errorBufferRef.current = []
    let containerPreviewUrl: string | null = null

    onOutput?.('🐳 Starting Docker container...')

    const token = localStorage.getItem('access_token')

    try {
      // Step 1: Create container
      const createResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
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

      // CRITICAL #4: Validate preview_urls before accessing
      if (!container.preview_urls || Object.keys(container.preview_urls).length === 0) {
        console.warn('[RunWithDocker] Container created but no preview_urls returned')
        onOutput?.('⚠️ Warning: No preview URLs available from container')
      }

      // CRITICAL #4: Extract and validate preview URL
      const candidateUrls = [
        container.preview_urls?.primary,
        container.preview_urls?.['3000'],
        container.preview_urls?.['5173'],
        container.preview_urls?.['5174'],
        container.preview_urls?.['8080'],
        container.preview_urls?.reverse_proxy,
        ...Object.values(container.preview_urls || {}).filter((url: any) => typeof url === 'string')
      ].filter(Boolean) as string[]

      // CRITICAL #4: Find first valid URL (must be http/https or start with /)
      containerPreviewUrl = candidateUrls.find(url => {
        if (!url || typeof url !== 'string') return false
        return url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')
      }) || null

      if (containerPreviewUrl) {
        // NOTE: Do NOT set preview URL or call onPreviewUrlChange here!
        // Preview should only be shown AFTER health check passes (__PREVIEW_READY__ marker)
        // Setting URL here causes iframe to refresh multiple times
        console.log('[RunWithDocker] Preview URL prepared (will show after health check):', containerPreviewUrl)
        onOutput?.(`📍 Preview URL: ${containerPreviewUrl} (waiting for server...)`)
      } else {
        console.warn('[RunWithDocker] No valid preview URL found in:', container.preview_urls)
        onOutput?.('⚠️ Warning: Could not determine preview URL')
      }

      // HIGH #4: Verify container is ready before syncing files
      onOutput?.('📡 Checking container status...')
      let containerReady = false
      const maxHealthChecks = 5

      for (let i = 0; i < maxHealthChecks && !containerReady; i++) {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/status`, {
            headers: { ...(token && { 'Authorization': `Bearer ${token}` }) },
          })
          if (statusResponse.ok) {
            const status = await statusResponse.json()
            if (status.status === 'running' || status.status === 'ready') {
              containerReady = true
              onOutput?.('  ✓ Container is ready')
              break
            }
          }
        } catch {
          // Ignore errors, keep trying
        }
        if (!containerReady && i < maxHealthChecks - 1) {
          await new Promise(resolve => setTimeout(resolve, 500))
        }
      }

      if (!containerReady) {
        onOutput?.('  ⚠️ Container health check failed, proceeding anyway...')
      }

      // Step 2: Sync files
      const fileSynced = await syncFilesToWorkspace()
      if (!fileSynced && currentProject?.files?.length > 0) {
        throw new Error('Failed to sync project files')
      }

      setStatus('starting')

      // Step 3: Execute commands
      const commands = detectProjectType() === 'node'
        ? ['npm install', 'npm run dev']
        : detectProjectType() === 'python'
        ? ['pip install -r requirements.txt', 'python main.py']
        : ['python -m http.server 3000']

      const isDevServerCommand = (cmd: string) => {
        return ['npm run dev', 'npm start', 'yarn dev', 'pnpm dev', 'python -m http.server', 'python main.py'].some(p => cmd.includes(p))
      }

      for (const command of commands) {
        currentCommandRef.current = command
        // Also set command in centralized error collector for context
        setErrorCommand?.(command)
        onOutput?.(`$ ${command}`)

        const isDevServer = isDevServerCommand(command)
        // Critical #4: Detect install commands that MUST complete before proceeding
        const isInstallCommand = command.includes('npm install') ||
                                 command.includes('yarn install') ||
                                 command.includes('pnpm install') ||
                                 command.includes('pip install') ||
                                 command.includes('mvn install') ||
                                 command.includes('gradle build')

        const execResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/exec`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
          },
          body: JSON.stringify({ command, timeout: 600 }),
          signal: abortControllerRef.current?.signal,
        })

        if (!execResponse.ok) {
          throw new Error('Failed to execute command')
        }

        const reader = execResponse.body?.getReader()
        if (!reader) continue

        // Execute command with proper timeout handling
        // Critical #4: Install commands wait for completion to prevent race condition
        const result = await executeCommandWithTimeout(
          reader,
          isDevServer,
          isDevServer ? 10000 : 120000, // 10s for dev server, 2min timeout (but install waits for completion)
          containerPreviewUrl,
          onOutput,
          isInstallCommand // Critical #4: Wait for install commands to fully complete
        )

        // Check for real errors FIRST (applies to both dev servers and short commands)
        if (result.hasRealError && !result.serverStarted) {
          setLastError({
            message: result.errorOutput.slice(0, 500),
            stackTrace: result.errorOutput,
            detectedAt: new Date(),
            severity: isInstallCommand ? 'build_error' : 'runtime_error',
            phase: isInstallCommand ? 'install' : 'runtime'
          })
          onOutput?.(`\n❌ Error detected during: ${command}`)
          onOutput?.(`📋 Error: ${result.errorOutput.slice(0, 200)}...`)
          return { success: false, error: result.errorOutput }
        }

        // For dev servers: mark as running after timeout if no errors
        // NOTE: Preview URL is only set when __PREVIEW_READY__ marker is received
        // This prevents iframe from refreshing before server is confirmed ready
        if (isDevServer) {
          setStatus('running')
          // Don't set preview URL here - wait for __PREVIEW_READY__ health check marker
          // The URL will be set by detectServerStart() when __PREVIEW_READY__ is received
          if (!serverStartedRef.current && containerPreviewUrl) {
            // Server didn't confirm ready via marker, but timeout passed without errors
            // This is a fallback - give the user a hint but don't force preview
            onOutput?.(`⏳ Waiting for server health check... (preview at ${containerPreviewUrl})`)
          } else if (serverStartedRef.current) {
            onOutput?.(`✅ Server is running!`)
          }
          return { success: true }
        }
      }

      setStatus('running')
      return { success: true }

    } catch (error: any) {
      if (error.name === 'AbortError') return { success: false }

      if (error.message?.includes('Docker') || error.message?.includes('container')) {
        onOutput?.(`⚠️ Docker error: ${error.message}`)
        setDockerAvailable(false)
        setExecutionMode('direct')
        return { success: false, error: error.message }
      }

      throw error
    }
  }

  // Helper: Execute command with timeout and proper SSE handling
  // Critical #4: For install commands, wait for completion (done event) not timeout
  const executeCommandWithTimeout = async (
    reader: ReadableStreamDefaultReader<Uint8Array>,
    isDevServer: boolean,
    timeoutMs: number,
    previewUrl: string | null,
    output?: (line: string) => void,
    waitForCompletion: boolean = false // Critical #4: Wait for done event, not timeout
  ): Promise<{ hasRealError: boolean; errorOutput: string; serverStarted: boolean; completed: boolean }> => {
    const decoder = new TextDecoder()
    let buffer = ''
    let hasRealError = false
    let errorOutput = ''
    let serverStarted = false
    let timedOut = false
    let commandCompleted = false // Critical #4: Track if command actually finished

    // Create timeout promise
    const timeoutPromise = new Promise<void>((resolve) => {
      setTimeout(() => {
        timedOut = true
        resolve()
      }, timeoutMs)
    })

    // Process SSE stream
    const processStream = async () => {
      try {
        // Critical #4: For install commands (waitForCompletion=true), don't check timedOut
        // This ensures we wait for npm install to fully complete
        while (waitForCompletion ? !commandCompleted : !timedOut) {
          // CRITICAL #5: Check if abort signal was triggered before reading
          if (abortControllerRef.current?.signal.aborted) {
            console.log('[ExecuteCommand] Abort signal detected, stopping stream')
            break
          }

          // Race between read and a short timeout to check flags
          const readWithTimeout = Promise.race([
            reader.read(),
            new Promise<{ done: true; value: undefined }>((resolve) =>
              setTimeout(() => resolve({ done: true, value: undefined }), 500)
            )
          ])

          let result: ReadableStreamReadResult<Uint8Array>
          try {
            result = await readWithTimeout
          } catch (readErr) {
            // CRITICAL #5: Handle abort error gracefully
            if (readErr instanceof DOMException && readErr.name === 'AbortError') {
              console.log('[ExecuteCommand] Stream aborted by user')
              break
            }
            throw readErr
          }

          const { done, value } = result

          // Critical #4: Only break on timedOut if not waiting for completion
          if (!waitForCompletion && timedOut) break
          if (done && value === undefined && !timedOut) continue // Short timeout, retry
          if (done) {
            // Stream ended - mark as completed
            commandCompleted = true
            break
          }

          if (value) {
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop() || ''

            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const event = JSON.parse(line.slice(6))
                  const text = event.data ? String(event.data) : ''

                  if (event.type === 'stdout' || event.type === 'stderr') {
                    output?.(text)

                    // Check for real errors (not false positives)
                    if (detectError(text)) {
                      hasRealError = true
                      errorOutput += text + '\n'
                      errorBufferRef.current.push(text)
                    }

                    // Server started - but DON'T clear errors
                    // Vite/webpack dev servers continue running even with compile errors
                    // We still need to trigger auto-fix for those errors
                    if (isDevServer && detectServerStart(text)) {
                      serverStarted = true
                      // NOTE: Don't clear hasRealError or errorOutput here
                      // Errors detected before server start should still trigger fix
                    }
                  }

                  if (event.type === 'error') {
                    output?.(`❌ ${text}`)
                    hasRealError = true
                    errorOutput += text + '\n'
                  }

                  if (event.type === 'done') {
                    // Critical #4: Mark command as completed
                    commandCompleted = true

                    // Check exit code for non-zero (error)
                    const exitCode = event.exit_code || event.exitCode || 0
                    if (exitCode !== 0) {
                      hasRealError = true
                      buildFailedRef.current = true // Mark build as failed (prevents false SUCCESS)
                      // CRITICAL #2: Reset serverStarted if command failed
                      // This ensures we don't show "server running" when it actually crashed
                      if (serverStarted) {
                        console.log('[ExecuteCommand] ⚠️ Server was marked as started but command failed - resetting')
                        serverStarted = false
                      }
                      const exitMsg = `Command exited with code ${exitCode}`
                      errorOutput += exitMsg + '\n'
                      console.log('[ExecuteCommand] 🔴 NON-ZERO EXIT CODE:', exitCode)
                      console.log('[ExecuteCommand]    Command:', currentCommandRef.current)

                      // ========== CENTRALIZED ERROR HANDLING ==========
                      // Forward full output context to the error collector
                      const fullContext = outputBufferRef.current.join('\n') + '\n' + exitMsg
                      console.log('[ExecuteCommand] 📤 Forwarding error to centralized ErrorCollector...')
                      console.log('[ExecuteCommand]    Output buffer size:', outputBufferRef.current.length, 'lines')

                      // Clear any pending debounce and forward immediately
                      if (forwardDebounceRef.current) {
                        clearTimeout(forwardDebounceRef.current)
                        forwardDebounceRef.current = null
                      }

                      // Report through centralized error collector
                      if (reportError) {
                        reportError('build', fullContext, { severity: 'error' })
                        // Force immediate forward
                        forwardNow?.()
                      }
                    } else {
                      console.log('[ExecuteCommand] ✅ Command completed successfully (exit code 0)')
                    }
                    return // Command completed
                  }
                } catch {}
              }
            }

            // Early exit if server started
            if (serverStarted) return
          }
        }
      } catch (e) {
        // Stream error, exit gracefully
        console.log('[ExecuteCommand] Stream error:', e)
      }
    }

    // Critical #4: For install commands, wait for completion without timeout race
    // This prevents starting dev server before npm install finishes
    if (waitForCompletion) {
      // Wait for stream to complete (or until a maximum safety timeout of 5 minutes)
      const safetyTimeout = new Promise<void>((resolve) => {
        setTimeout(() => {
          console.log('[ExecuteCommand] ⚠️ Safety timeout reached for install command')
          timedOut = true
          resolve()
        }, 300000) // 5 minute safety timeout
      })
      await Promise.race([processStream(), safetyTimeout])
    } else {
      // Race between stream processing and timeout
      await Promise.race([processStream(), timeoutPromise])
    }

    // For dev servers:
    // - If timeout WITH errors, keep the errors (trigger auto-fix) regardless of server status
    // - If timeout but NO errors detected, assume server is running
    // NOTE: Don't clear errors when server starts - Vite/webpack continue running even with compile errors
    if (isDevServer && timedOut) {
      if (!hasRealError) {
        // No errors detected, assume server is running
        serverStarted = true
      }
      // If hasRealError is true, keep the errors - don't clear them!
      // This allows auto-fix to trigger for compile errors even if dev server is running
    }

    return { hasRealError, errorOutput, serverStarted, completed: commandCompleted }
  }

  // ============= DIRECT EXECUTION (FALLBACK) =============
  const runDirect = async (): Promise<{ success: boolean; error?: string }> => {
    if (!currentProject?.id) return { success: false, error: 'No project' }

    console.log('[ProjectRunControls] runDirect called for project:', currentProject.id)
    onOutput?.('🖥️ Running directly on server...')
    onOutput?.(`📂 Project ID: ${currentProject.id}`)
    errorBufferRef.current = [] // Reset error buffer

    try {
      const token = localStorage.getItem('access_token')
      console.log('[ProjectRunControls] Making API call to:', `${API_BASE_URL}/execution/run/${currentProject.id}`)
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
      if (!reader) return { success: false, error: 'No response body' }

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
              console.log('[ProjectRunControls] SSE event received:', data.type, data)
              if (data.type === 'output') {
                const content = data.data?.output || data.content || ''
                console.log('[ProjectRunControls] Output:', content)
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
                // Also add to output buffer for full context
                outputBufferRef.current.push(content)
                if (outputBufferRef.current.length > 50) {
                  outputBufferRef.current.shift()
                }
                // Forward to centralized error collector
                if (reportError) {
                  reportError('build', content, { severity: 'error' })
                }
              } else if (data.type === 'server_started') {
                // Use preview_url from Docker if available, otherwise construct from port
                // Pass project ID for production URL construction
                const url = data.preview_url || getPreviewUrl(data.port || 3000, currentProject?.id)
                console.log('[ProjectRunControls] SERVER STARTED! preview_url:', data.preview_url, 'port:', data.port, 'final URL:', url)
                setPreviewUrl(url)
                onPreviewUrlChange?.(url)
                // NOTE: Don't reset hasError here - errors detected before server start should still trigger fix
                // Vite/webpack dev servers continue running even with compile errors
                onOutput?.(`🚀 Server running at: ${url}`)
              } else if (data.type === 'command_complete' && data.data?.success === false) {
                hasError = true
                buildFailedRef.current = true // Mark build as failed (prevents false SUCCESS)
                const errorMsg = `Command failed with exit code ${data.data?.exit_code}`
                onOutput?.(`❌ ${errorMsg}`)
                // Forward full context to centralized error collector
                const fullContext = outputBufferRef.current.join('\n') + '\n' + errorMsg
                if (reportError) {
                  reportError('build', fullContext, { severity: 'error' })
                  forwardNow?.()
                }
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
          detectedAt: new Date(),
          severity: 'build_error',
          phase: 'build'
        })

        // Return error for auto-fix
        return { success: false, error: fullError }
      }

      return { success: true }

    } catch (error: any) {
      if (error.name === 'AbortError') return { success: false }
      throw error
    }
  }

  // ============= CHECK IF SERVER IS ALREADY RUNNING =============
  // Track if we started from existing server (for Stop button handling)
  const startedFromExistingServerRef = useRef<boolean>(false)

  const checkExistingServer = useCallback(async (): Promise<string | null> => {
    // DISABLED: This was detecting BharatBuild itself and other apps
    // Always let the backend start the project on a dynamic port
    console.log('[ProjectRunControls] checkExistingServer DISABLED - always use backend execution')
    return null
  }, [])

  // ============= MAIN RUN HANDLER =============
  const handleRun = useCallback(async () => {
    // Check if project exists
    if (!currentProject?.id) {
      onOutput?.('❌ No project selected. Generate a project first!')
      onStartSession?.()
      return
    }

    // Check if user is authenticated
    const token = localStorage.getItem('access_token')
    if (!token) {
      onOutput?.('❌ Please log in to run projects.')
      onStartSession?.()
      return
    }

    abortControllerRef.current?.abort()
    abortControllerRef.current = new AbortController()

    // Clear terminal logs for fresh run - new terminal for each run
    onClearLogs?.()

    setStatus('creating')
    setPreviewUrl(null)
    setMobilePreview(null)  // Reset mobile preview for fresh run
    onMobilePreviewChange?.(null)
    pendingQRRef.current = null

    onStartSession?.()
    // NOTE: Terminal is NOT auto-opened here. User must click "Code" tab to see terminal.

    // First, check if a server is already running
    const existingServerUrl = await checkExistingServer()
    if (existingServerUrl) {
      onOutput?.(`✅ Found existing server at ${existingServerUrl}`)
      setPreviewUrl(existingServerUrl)
      onPreviewUrlChange?.(existingServerUrl)
      setStatus('running')
      startedFromExistingServerRef.current = true  // Track that we detected existing server
      return
    }
    startedFromExistingServerRef.current = false  // Reset for fresh starts

    try {
      let result: { success: boolean; error?: string } = { success: false }

      // Try Docker first (if available)
      if (executionMode === 'docker' && dockerAvailable !== false) {
        try {
          result = await runWithDocker()
        } catch (error: any) {
          onOutput?.(`⚠️ Docker failed: ${error.message}`)
          onOutput?.('🔄 Switching to direct execution...')
          setExecutionMode('direct')
          setDockerAvailable(false)
        }
      }

      // Fallback to direct execution
      if (!result.success && (executionMode === 'direct' || dockerAvailable === false)) {
        setStatus('starting')
        result = await runDirect()
      }

      if (result.success) {
        // Already set to running by runWithDocker/runDirect
        console.log('[AutoFix] Project started successfully, no fix needed')
        if (fixAttempts > 0) {
          onOutput?.(`\n✨ SUCCESS after ${fixAttempts} fix attempt(s)!`)
          onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        }
        resetFixState()
        isRetryingRef.current = false
      } else if (result.error || lastError) {
        // ============= FIX → VERIFY → RE-RUN LOOP (Bolt.new style!) =============
        // This loop continues UNTIL SUCCESS or max attempts reached

        // IMPORTANT: If server is already running AND build didn't fail, treat as success (error might be from earlier in stream)
        if (serverStartedRef.current && !buildFailedRef.current) {
          console.log('[AutoFix] Server is running - skipping auto-fix despite error in stream')
          if (fixAttemptsRef.current > 0) {
            onOutput?.(`\n✨ SUCCESS after ${fixAttemptsRef.current} fix attempt(s)!`)
            onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          }
          resetFixState()
          onEndSession?.()
          return
        }

        const errorToFix = result.error || lastError?.stackTrace || 'Unknown error'
        console.log('[AutoFix] Error detected, triggering auto-fix:', errorToFix.slice(0, 100))

        // Prevent duplicate retries (e.g., from multiple error detections)
        if (isRetryingRef.current) {
          console.log('[AutoFix] Already retrying, skipping duplicate trigger')
          return
        }

        // Use ref for synchronous check (React state updates are async!)
        const currentAttempts = fixAttemptsRef.current

        if (autoFix && currentAttempts < MAX_AUTO_FIX_ATTEMPTS) {
          isRetryingRef.current = true

          onOutput?.('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          onOutput?.(`🔄 AUTO-RETRY LOOP [${currentAttempts + 1}/${MAX_AUTO_FIX_ATTEMPTS}]`)
          onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          console.log(`[AutoFix] Fix loop iteration ${currentAttempts + 1}/${MAX_AUTO_FIX_ATTEMPTS}`)

          setStatus('fixing')
          const fixSuccess = await attemptAutoFix(
            errorToFix.slice(0, 500),
            errorToFix
          )

          // After attemptAutoFix, the ref has been incremented
          const attemptsAfterFix = fixAttemptsRef.current

          if (fixSuccess) {
            // ✅ FIX APPLIED → RE-RUN TO VERIFY
            consecutiveFailuresRef.current = 0 // Reset on successful fix
            const delay = DEFAULT_RETRY_DELAY
            onOutput?.(`\n🚀 Fix applied! Re-running to verify in ${delay/1000}s... (attempt ${attemptsAfterFix}/${MAX_AUTO_FIX_ATTEMPTS})`)
            isRetryingRef.current = false
            setTimeout(() => handleRun(), delay)
            return
          } else {
            // ❌ FIX FAILED → Check if we can retry
            consecutiveFailuresRef.current += 1
            const backoffDelay = getRetryDelay(consecutiveFailuresRef.current)

            // Use ref value AFTER increment to check if we can retry
            if (attemptsAfterFix < MAX_AUTO_FIX_ATTEMPTS) {
              onOutput?.(`\n⚠️ Fix attempt ${attemptsAfterFix} failed.`)
              onOutput?.(`⏳ Retrying in ${(backoffDelay/1000).toFixed(1)}s with different approach...`)
              isRetryingRef.current = false
              // Continue retry loop - try fixing again
              setTimeout(() => handleRun(), backoffDelay)
              return
            }
          }
        }

        // Max attempts reached or autoFix disabled
        // BUT: Check if server is actually running AND build didn't fail (it might have succeeded after fixes!)
        if (serverStartedRef.current && !buildFailedRef.current) {
          console.log('[AutoFix] Server is running despite hitting max attempts - treating as success')
          if (fixAttemptsRef.current > 0) {
            onOutput?.(`\n✨ SUCCESS after ${fixAttemptsRef.current} fix attempt(s)!`)
            onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          }
          resetFixState()
          isRetryingRef.current = false
          // Don't change status - it's already 'running'
        } else if (fixAttemptsRef.current >= MAX_AUTO_FIX_ATTEMPTS) {
          // CRITICAL: Final check - if server actually started (preview URL set) AND build didn't fail, don't show error
          // This catches cases where server started but errors were detected earlier in stream
          if ((previewUrl || serverStartedRef.current) && !buildFailedRef.current) {
            console.log('[AutoFix] Server is running (previewUrl or ref set) - suppressing MAX ATTEMPTS message')
            resetFixState()
            isRetryingRef.current = false
            // Don't change status - it's already 'running'
            return
          }
          onOutput?.('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          onOutput?.(`🛑 MAX ATTEMPTS (${MAX_AUTO_FIX_ATTEMPTS}) REACHED`)
          onOutput?.('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
          onOutput?.('\n💡 The auto-fixer tried multiple approaches but couldn\'t resolve the issue.')
          onOutput?.('   Options:')
          onOutput?.('   1. Check the error message above for clues')
          onOutput?.('   2. Manually edit the file in Code Editor')
          onOutput?.('   3. Click "Retry Fix" to reset and try again')
          onOutput?.('   4. Ask the AI in chat for specific guidance')
          setMaxAttemptsReached(true)
          isRetryingRef.current = false
          setStatus('error')
          onOutput?.('\n❌ Execution failed. See errors above.')
        } else {
          isRetryingRef.current = false
          setStatus('error')
          onOutput?.('\n❌ Execution failed. See errors above.')
        }
      }

      onEndSession?.()

    } catch (error: any) {
      console.error('Run error:', error)
      onOutput?.(`❌ Error: ${error.message}`)
      setStatus('error')
      onEndSession?.()
    }
  }, [currentProject?.id, executionMode, dockerAvailable, onOutput, autoFix, fixAttempts, lastError, attemptAutoFix, onStartSession, onEndSession, resetFixState, getRetryDelay])

  // ============= BOLT.NEW: AUTO-RESTART AFTER LOGBUS FIX =============
  // Check if LogBus auto-fix completed and restart is pending
  // Added safeguard: only restart if we haven't exceeded max attempts
  useEffect(() => {
    if (pendingRestartRef.current && status !== 'fixing') {
      pendingRestartRef.current = false

      // Safety check: don't restart if max attempts reached (use ref for synchronous check)
      if (fixAttemptsRef.current >= MAX_AUTO_FIX_ATTEMPTS) {
        console.log('[AutoRestart] Skipping restart - max attempts reached')
        onOutput?.(`⚠️ Auto-restart skipped: max fix attempts (${MAX_AUTO_FIX_ATTEMPTS}) reached`)
        return
      }

      // Delay restart to let files sync
      setTimeout(() => {
        handleRun()
      }, 1000)
    }
  }, [status, handleRun, onOutput]) // Removed fixAttempts - using ref now

  // ============= STOP HANDLER =============
  // High #9: Actually stops container and propagates abort signal
  const handleStop = useCallback(async () => {
    setStatus('stopping')
    onOutput?.('🛑 Stopping project...')

    // Abort current fetch requests
    abortControllerRef.current?.abort()
    abortControllerRef.current = null

    // Reset fix state to prevent stuck fixes
    isFixingRef.current = false
    fixLockTimeRef.current = 0
    isRetryingRef.current = false
    serverStartedRef.current = false
    // Tell error collector server stopped - allows auto-fix on next run
    setServerRunning(false)

    // If we detected an existing server (not started by us), just close the preview
    if (startedFromExistingServerRef.current) {
      setStatus('stopped')
      setPreviewUrl(null)
      setMobilePreview(null)
      onPreviewUrlChange?.(null)
      onMobilePreviewChange?.(null)
      onOutput?.('🛑 Preview closed (external server still running)')
      startedFromExistingServerRef.current = false
      return
    }

    const token = localStorage.getItem('access_token')
    let stopSuccess = false

    try {
      // HIGH #9: Stop container with proper error handling and verification wait
      if (executionMode === 'docker' && currentProject?.id) {
        const containerResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/stop`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        })
        if (containerResponse.ok) {
          const result = await containerResponse.json()
          stopSuccess = result.verified === true

          // HIGH #9: If not verified, wait and retry verification
          if (!stopSuccess) {
            onOutput?.('  ⏳ Waiting for container to stop...')
            const maxRetries = 5
            for (let i = 0; i < maxRetries && !stopSuccess; i++) {
              await new Promise(resolve => setTimeout(resolve, 1000))
              try {
                const statusResponse = await fetch(`${API_BASE_URL}/containers/${currentProject.id}/status`, {
                  headers: { 'Authorization': `Bearer ${token}` },
                })
                if (statusResponse.ok) {
                  const status = await statusResponse.json()
                  if (status.status === 'stopped' || status.status === 'not_found' || status.status === 'exited') {
                    stopSuccess = true
                    break
                  }
                } else if (statusResponse.status === 404) {
                  // Container not found = stopped
                  stopSuccess = true
                  break
                }
              } catch {
                // Ignore check errors, keep retrying
              }
            }
          }

          if (stopSuccess) {
            onOutput?.('  ✓ Container stopped and verified')
          } else {
            onOutput?.('  ⚠️ Container stop requested (may still be shutting down)')
          }
        }
      }

      // Also try direct stop endpoint for non-Docker executions
      if (currentProject?.id) {
        await fetch(`${API_BASE_URL}/execution/stop/${currentProject.id}`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        }).catch(() => {}) // This one can fail silently
      }

    } catch (stopErr) {
      console.warn('[Stop] Error stopping container:', stopErr)
      onOutput?.(`  ⚠️ Stop error: ${stopErr}`)
    }

    setStatus('stopped')
    setPreviewUrl(null)
    setMobilePreview(null)  // Clear mobile preview on stop
    onPreviewUrlChange?.(null)
    onMobilePreviewChange?.(null)
    onOutput?.('🛑 Project stopped')
  }, [currentProject?.id, executionMode, onPreviewUrlChange, onMobilePreviewChange, onOutput])

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
  const isRunning = status === 'running'
  const isLoading = status === 'creating' || status === 'starting' || status === 'stopping' || status === 'fixing'
  const canRun = !isLoading && !isRunning && currentProject && canRunCode
  const hasFixableError = status === 'error' && lastError && fixAttempts < MAX_AUTO_FIX_ATTEMPTS

  return (
    <div className="flex items-center gap-2">

      {/* Run/Stop Buttons */}
      {!isRunning && !isLoading ? (
        // Show locked button for non-premium users
        !canRunCode && !planLoading ? (
          <a
            href="/pricing"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
              bg-amber-600/20 border border-amber-500/30 hover:bg-amber-600/30
              text-amber-400 text-sm font-medium transition-colors"
            title="Upgrade to Premium to run projects"
          >
            <Lock className="w-3.5 h-3.5" />
            <span>Run (Premium)</span>
          </a>
        ) : (
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
        )
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
             status === 'fixing' ? `Fixing (${fixAttempts + 1}/${MAX_AUTO_FIX_ATTEMPTS})...` :
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
    </div>
  )
}
