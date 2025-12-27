'use client'

import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { AlertCircle, RefreshCw, ExternalLink, Play, AlertTriangle } from 'lucide-react'
import { useErrorStore } from '@/store/errorStore'
import { useFileChangeEvents } from '@/hooks/useFileChangeEvents'
import { useErrorCollector } from '@/hooks/useErrorCollector'

interface LivePreviewProps {
  files: Record<string, string>
  entryPoint?: string
  serverUrl?: string  // URL of running server (e.g., http://localhost:3001)
  isServerRunning?: boolean
  projectId?: string  // Project ID for file change events
  autoReloadOnFix?: boolean  // Auto-reload when files are fixed (default: true)
  onError?: (error: { message: string; file?: string; line?: number; column?: number; stack?: string }) => void
  onReload?: () => void  // Callback when preview is reloaded
}

export function LivePreview({
  files,
  entryPoint = 'index.html',
  serverUrl,
  isServerRunning = false,
  projectId,
  autoReloadOnFix = true,
  onError,
  onReload
}: LivePreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [previewMode, setPreviewMode] = useState<'static' | 'server'>('static')
  const [refreshKey, setRefreshKey] = useState(0)
  const [autoReloadIndicator, setAutoReloadIndicator] = useState(false)
  const [autoFixStatus, setAutoFixStatus] = useState<'idle' | 'fixing' | 'completed' | 'failed'>('idle')
  const [autoFixMessage, setAutoFixMessage] = useState<string | null>(null)

  // Retry state for dev server startup
  const [retryCount, setRetryCount] = useState(0)
  const [retryStatus, setRetryStatus] = useState<'idle' | 'waiting' | 'retrying'>('idle')
  const maxRetries = 15 // Max retries (~30 seconds total)
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const { addBrowserError, addNetworkError, getErrorCount, clearErrors } = useErrorStore()
  const errorCount = getErrorCount()

  // Connect to centralized error collector for auto-fix (Bolt.new style!)
  const {
    reportError,
    isConnected: errorCollectorConnected,
    isFixing
  } = useErrorCollector({
    projectId,
    enabled: !!projectId,
    onFixStarted: (reason) => {
      console.log('[LivePreview] Auto-fix started:', reason)
      setAutoFixStatus('fixing')
      setAutoFixMessage(reason || 'Fixing errors...')
    },
    onFixCompleted: (patchesApplied, filesModified) => {
      console.log('[LivePreview] Auto-fix completed!', patchesApplied, 'patches')
      setAutoFixStatus('completed')
      setAutoFixMessage(`Fixed! ${patchesApplied || 0} patches applied`)
      clearErrors()
      // Auto-reload preview after fix
      setTimeout(() => {
        setIsLoading(true)
        setRefreshKey(prev => prev + 1)
        onReload?.()
        setTimeout(() => {
          setAutoFixStatus('idle')
          setAutoFixMessage(null)
        }, 2000)
      }, 500)
    },
    onFixFailed: (error) => {
      console.log('[LivePreview] Auto-fix failed:', error)
      setAutoFixStatus('failed')
      setAutoFixMessage(error || 'Fix failed')
      setTimeout(() => {
        setAutoFixStatus('idle')
        setAutoFixMessage(null)
      }, 5000)
    }
  })

  // Wrapper functions for backward compatibility with iframe message handling
  const forwardBrowserError = useCallback((message: string, file?: string, line?: number, column?: number, stack?: string) => {
    reportError('browser', message, { file, line, column, stack })
  }, [reportError])

  const forwardNetworkError = useCallback((message: string, url?: string, status?: number, method?: string) => {
    reportError('network', message, { file: url })
  }, [reportError])

  // File change events for auto-reload
  const { hasRecentFix, setReloadCallback, lastChange } = useFileChangeEvents({
    projectId,
    autoReloadPreview: autoReloadOnFix,
    reloadDelay: 800, // Wait 800ms after last change before reloading
    onFileChange: (event) => {
      if (['fixed', 'patched', 'updated'].includes(event.type)) {
        console.log('[LivePreview] File change detected, will auto-reload:', event.path)
      }
    }
  })

  // Register the reload callback
  useEffect(() => {
    setReloadCallback(() => {
      console.log('[LivePreview] Auto-reloading preview after file change')
      setAutoReloadIndicator(true)
      handleRefresh()
      onReload?.()

      // Hide indicator after 2 seconds
      setTimeout(() => setAutoReloadIndicator(false), 2000)
    })
  }, [setReloadCallback, onReload])

  // Switch to server mode when server is running
  useEffect(() => {
    console.log('[LivePreview] State update:', { isServerRunning, serverUrl, previewMode })
    if (isServerRunning && serverUrl) {
      console.log('[LivePreview] Switching to server mode with URL:', serverUrl)
      setPreviewMode('server')
      setIsLoading(true) // Reset loading state when switching to server mode
      setRetryCount(0) // Reset retry count
      setRetryStatus('waiting') // Start in waiting mode for dev server
      setError(null)
    } else {
      console.log('[LivePreview] Switching to static mode')
      setPreviewMode('static')
      setRetryStatus('idle')
    }
  }, [isServerRunning, serverUrl])

  // Cleanup retry timeout on unmount
  useEffect(() => {
    return () => {
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current)
      }
    }
  }, [])

  // Retry loading the preview with exponential backoff
  const retryPreview = useCallback(() => {
    if (retryCount >= maxRetries) {
      console.log('[LivePreview] Max retries reached, giving up')
      setRetryStatus('idle')
      setError('Dev server is taking too long to start. Try clicking Refresh.')
      return
    }

    const delay = Math.min(1000 * Math.pow(1.5, Math.min(retryCount, 5)), 5000) // 1s, 1.5s, 2.25s, 3.4s, 5s, 5s...
    console.log(`[LivePreview] Scheduling retry ${retryCount + 1}/${maxRetries} in ${delay}ms`)

    setRetryStatus('waiting')

    retryTimeoutRef.current = setTimeout(() => {
      setRetryCount(prev => prev + 1)
      setRetryStatus('retrying')

      if (iframeRef.current && serverUrl) {
        // Force reload the iframe with a cache-busting parameter
        const newUrl = serverUrl + (serverUrl.includes('?') ? '&' : '?') + '_retry=' + Date.now()
        console.log(`[LivePreview] Retry ${retryCount + 1}: Loading ${newUrl}`)
        iframeRef.current.src = newUrl
      }
    }, delay)
  }, [retryCount, maxRetries, serverUrl])

  // Listen for error messages from iframe via postMessage
  const handleIframeMessage = useCallback((event: MessageEvent) => {
    // Validate message origin and structure
    if (event.data && event.data.type === 'bharatbuild-error') {
      const { message, filename, lineno, colno, stack } = event.data
      console.log('[LivePreview] 🔴 CAPTURED BROWSER ERROR from iframe:', {
        message: message?.substring(0, 150),
        filename,
        lineno,
        colno,
        hasStack: !!stack,
        projectId,
        errorCollectorConnected
      })

      // Add to error store (local)
      addBrowserError(message, filename, lineno, colno, stack)

      // Forward to backend for auto-fix! (This is the key fix)
      console.log('[LivePreview] 📤 Forwarding to backend via forwardBrowserError...')
      forwardBrowserError(message, filename, lineno, colno, stack)

      // Call optional callback
      onError?.({ message, file: filename, line: lineno, column: colno, stack })
    } else if (event.data && event.data.type === 'bharatbuild-console') {
      // Also capture console.error calls
      if (event.data.level === 'error') {
        const message = event.data.args?.join(' ') || 'Unknown error'
        console.log('[LivePreview] 🔴 CAPTURED console.error from iframe:', message?.substring(0, 100))
        addBrowserError(message)

        // Forward to backend for auto-fix!
        console.log('[LivePreview] 📤 Forwarding console.error to backend...')
        forwardBrowserError(message)

        onError?.({ message })
      }
    } else if (event.data && event.data.type === 'bharatbuild-network') {
      // Network errors (fetch/XHR failures, CORS, timeouts, HTTP errors)
      const { url, method, status, message } = event.data
      console.log('[LivePreview] 🌐 CAPTURED NETWORK ERROR from iframe:', {
        message,
        url,
        status,
        method,
        projectId,
        errorCollectorConnected
      })

      // Add to error store with network-specific info
      addNetworkError(message, url, status, method)

      // Forward to backend for auto-fix!
      console.log('[LivePreview] 📤 Forwarding network error to backend...')
      forwardNetworkError(message, url, status, method)

      // Call optional callback
      onError?.({ message, file: url })
    }
    // ===== RESOURCE ERRORS =====
    else if (event.data && event.data.type === 'bharatbuild-resource-error') {
      console.log('[LivePreview] 📦 CAPTURED RESOURCE ERROR:', event.data)
      const { tagName, src, message } = event.data
      addBrowserError(`Resource load failed: ${tagName} - ${src}`, src)
      forwardBrowserError(message || `Failed to load ${tagName}: ${src}`, src)
    }
    // ===== HMR ERRORS =====
    else if (event.data && event.data.type === 'bharatbuild-hmr-error') {
      console.log('[LivePreview] 🔥 CAPTURED HMR ERROR:', event.data)
      const { message, file, line, column, stack } = event.data
      addBrowserError(`HMR Error: ${message}`, file, line, column, stack)
      forwardBrowserError(message, file, line, column, stack)
    }
    // ===== HMR UPDATES =====
    else if (event.data && event.data.type === 'bharatbuild-hmr-update') {
      console.log('[LivePreview] 🔄 HMR update detected, preview will refresh')
      // Optionally trigger a visual indicator
      setAutoReloadIndicator(true)
      setTimeout(() => setAutoReloadIndicator(false), 1500)
    }
    // ===== REACT RENDER ERRORS =====
    else if (event.data && event.data.type === 'bharatbuild-react-error') {
      console.log('[LivePreview] ⚛️ CAPTURED REACT ERROR:', event.data)
      const { message, stack, componentStack } = event.data
      const fullStack = stack + (componentStack ? '\n\nComponent Stack:' + componentStack : '')
      addBrowserError(`React Error: ${message}`, undefined, undefined, undefined, fullStack)
      forwardBrowserError(message, undefined, undefined, undefined, fullStack)
    }
    // ===== CSP VIOLATIONS =====
    else if (event.data && event.data.type === 'bharatbuild-csp-error') {
      console.log('[LivePreview] 🔒 CAPTURED CSP VIOLATION:', event.data)
      const { blockedURI, violatedDirective, sourceFile, lineNumber } = event.data
      const message = `CSP Violation: ${violatedDirective} blocked ${blockedURI}`
      addBrowserError(message, sourceFile, lineNumber)
      forwardBrowserError(message, sourceFile, lineNumber)
    }
    // ===== PROMISE REJECTIONS =====
    else if (event.data && event.data.type === 'bharatbuild-promise-rejection') {
      console.log('[LivePreview] 💥 CAPTURED PROMISE REJECTION:', event.data)
      const { message, stack } = event.data
      addBrowserError(`Unhandled Promise: ${message}`, undefined, undefined, undefined, stack)
      forwardBrowserError(message, undefined, undefined, undefined, stack)
    }
    // ===== MODULE LOADER ERRORS (Bolt-style) =====
    else if (event.data && event.data.type === 'bharatbuild-module-error') {
      console.log('[LivePreview] 📦 CAPTURED MODULE ERROR:', event.data)
      const { message, file, line, column, stack } = event.data
      addBrowserError(`Module Error: ${message}`, file, line, column, stack)
      forwardBrowserError(message, file, line, column, stack)
    }
    // ===== RUNTIME ERRORS =====
    else if (event.data && event.data.type === 'bharatbuild-runtime-error') {
      console.log('[LivePreview] 🔴 CAPTURED RUNTIME ERROR:', event.data)
      const { message, file, line, column, stack } = event.data
      addBrowserError(message, file, line, column, stack)
      forwardBrowserError(message, file, line, column, stack)
      onError?.({ message, file, line, column, stack })
    }
    // Also handle other bharatbuild message types for logging
    else if (event.data && event.data.type?.startsWith('bharatbuild-')) {
      console.log('[LivePreview] 📨 Received iframe message:', event.data.type, event.data)
    }
    // ===== AUTO-FIX EVENTS (Bolt.new Magic!) =====
    else if (event.data && event.data.type === 'bharatbuild-fix-started') {
      console.log('[LivePreview] Auto-fix started:', event.data.reason)
      setAutoFixStatus('fixing')
      setAutoFixMessage(event.data.reason || 'Fixing errors...')
    }
    else if (event.data && event.data.type === 'bharatbuild-fix-completed') {
      console.log('[LivePreview] Auto-fix completed!', event.data.patchesApplied, 'patches')
      setAutoFixStatus('completed')
      setAutoFixMessage(`Fixed! ${event.data.patchesApplied || 0} patches applied`)
      // Clear errors since they're fixed
      clearErrors()
      // Auto-reload preview after fix
      setTimeout(() => {
        // Inline refresh logic (can't use handleRefresh due to closure timing)
        setIsLoading(true)
        setRefreshKey(prev => prev + 1)
        onReload?.()
        // Reset status after showing completion
        setTimeout(() => {
          setAutoFixStatus('idle')
          setAutoFixMessage(null)
        }, 2000)
      }, 500)
    }
    else if (event.data && event.data.type === 'bharatbuild-fix-failed') {
      console.log('[LivePreview] Auto-fix failed:', event.data.error)
      setAutoFixStatus('failed')
      setAutoFixMessage(event.data.error || 'Fix failed')
      // Reset status after showing error
      setTimeout(() => {
        setAutoFixStatus('idle')
        setAutoFixMessage(null)
      }, 5000)
    }
  }, [addBrowserError, addNetworkError, onError, clearErrors, onReload, forwardBrowserError, forwardNetworkError])

  // Set up message listener
  useEffect(() => {
    window.addEventListener('message', handleIframeMessage)
    return () => {
      window.removeEventListener('message', handleIframeMessage)
    }
  }, [handleIframeMessage])

  // Generate preview HTML using srcdoc (avoids cross-origin issues)
  const previewHTML = useMemo(() => {
    if (previewMode !== 'static' || Object.keys(files).length === 0) {
      return ''
    }
    try {
      setError(null)
      return generatePreviewHTML(files, entryPoint, projectId)
    } catch (err: any) {
      setError(err.message)
      return ''
    }
  }, [files, entryPoint, previewMode, refreshKey, projectId])

  // Handle iframe load - don't stop retrying immediately, error pages also fire onLoad
  const handleIframeLoad = useCallback(() => {
    console.log('[LivePreview] Iframe loaded, retryCount:', retryCount, 'retryStatus:', retryStatus)

    // In early retries (< 8), don't stop - error pages (502, connection refused) also trigger onLoad
    // Keep retrying until we get more attempts or hit retry limit
    if (previewMode === 'server' && retryCount < 8 && retryStatus !== 'idle') {
      console.log('[LivePreview] Still in retry phase, scheduling next retry in 2s...')
      setTimeout(() => {
        if (retryCount < maxRetries) {
          retryPreview()
        }
      }, 2000)
      return
    }

    // After 8 retries, assume loaded successfully
    console.log('[LivePreview] Assuming app loaded after retries')
    setIsLoading(false)
    setRetryStatus('idle')
    setError(null)
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
  }, [previewMode, retryCount, retryStatus, maxRetries, retryPreview])

  // Handle iframe crash/sandbox errors (Bolt.new style - Layer 12)
  const handleIframeError = useCallback((event: React.SyntheticEvent<HTMLIFrameElement, Event>) => {
    console.log('[LivePreview] 💀 IFRAME CRASH/ERROR detected:', event)

    // In server mode, trigger retry instead of showing error immediately
    if (previewMode === 'server' && retryCount < maxRetries) {
      console.log(`[LivePreview] Server mode error, triggering retry (${retryCount + 1}/${maxRetries})`)
      retryPreview()
      return
    }

    const message = 'Preview iframe crashed or failed to load'
    setError(message)
    addBrowserError(message)
    forwardBrowserError(message)
  }, [addBrowserError, forwardBrowserError, previewMode, retryCount, maxRetries, retryPreview])

  // Monitor iframe for unresponsive state
  useEffect(() => {
    if (!iframeRef.current || previewMode !== 'server') return

    const iframe = iframeRef.current
    let checkInterval: NodeJS.Timeout | null = null

    // Check if iframe is responsive by trying to access contentWindow
    const checkIframeHealth = () => {
      try {
        // This will throw if iframe crashed or has security issues
        const doc = iframe.contentDocument || iframe.contentWindow?.document
        if (!doc && isServerRunning) {
          console.log('[LivePreview] Iframe may be unresponsive')
        }
      } catch (e) {
        // Cross-origin is expected for server mode, ignore
      }
    }

    // Check every 10 seconds
    checkInterval = setInterval(checkIframeHealth, 10000)

    return () => {
      if (checkInterval) clearInterval(checkInterval)
    }
  }, [previewMode, isServerRunning])

  // Timeout to trigger retry if iframe doesn't fire onLoad (connection refused, CORS, etc.)
  useEffect(() => {
    if (previewMode === 'server' && isLoading && retryStatus !== 'idle') {
      const timeout = setTimeout(() => {
        console.log('[LivePreview] Loading timeout - triggering retry')
        // Don't hide loading, trigger retry instead
        if (retryCount < maxRetries) {
          retryPreview()
        } else {
          setIsLoading(false)
          setRetryStatus('idle')
          console.log('[LivePreview] Max retries reached after timeout')
        }
      }, 3000) // 3 second timeout per attempt
      return () => clearTimeout(timeout)
    }
  }, [previewMode, isLoading, serverUrl, retryStatus, retryCount, maxRetries, retryPreview])

  const handleRefresh = () => {
    setIsLoading(true)
    setError(null)
    setRetryCount(0)
    setRetryStatus('waiting')
    // Clear any pending retry timeout
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current)
      retryTimeoutRef.current = null
    }
    if (previewMode === 'server' && serverUrl && iframeRef.current) {
      // Force reload server iframe
      iframeRef.current.src = serverUrl + '?t=' + Date.now()
    } else {
      // Trigger re-render of static preview
      setRefreshKey(prev => prev + 1)
    }
  }

  const handleOpenExternal = () => {
    if (previewMode === 'server' && serverUrl) {
      window.open(serverUrl, '_blank')
    } else {
      // Open static preview in new tab using blob URL
      const blob = new Blob([previewHTML], { type: 'text/html' })
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
    }
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Preview Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center gap-2">
          {/* Status indicator */}
          <div className={`w-2 h-2 rounded-full ${isServerRunning ? 'bg-green-500 animate-pulse' : 'bg-gray-400'}`} />
          <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
            {isServerRunning ? 'Server Running' : 'Static Preview'}
          </span>
          {serverUrl && isServerRunning && (
            <span className="text-xs text-[hsl(var(--bolt-text-tertiary))] font-mono">
              {serverUrl}
            </span>
          )}
          {/* Auto-reload indicator */}
          {autoReloadIndicator && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 text-xs animate-pulse">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Reloading...
            </span>
          )}
          {/* Recent fix indicator */}
          {hasRecentFix && !autoReloadIndicator && autoFixStatus === 'idle' && (
            <span className="px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">
              Fixed
            </span>
          )}
          {/* Auto-fix status indicator (Bolt.new style!) */}
          {autoFixStatus === 'fixing' && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400 text-xs animate-pulse">
              <svg className="w-3 h-3 animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
              </svg>
              Auto-fixing...
            </span>
          )}
          {autoFixStatus === 'completed' && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">
              <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
              </svg>
              {autoFixMessage || 'Fixed!'}
            </span>
          )}
          {autoFixStatus === 'failed' && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-xs">
              <AlertTriangle className="w-3 h-3" />
              Fix failed
            </span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Error count badge */}
          {errorCount.total > 0 && (
            <div
              className="flex items-center gap-1 px-2 py-1 rounded bg-red-500/20 text-red-400 text-xs font-medium cursor-pointer hover:bg-red-500/30 transition-colors"
              title={`${errorCount.errors} errors, ${errorCount.warnings} warnings`}
            >
              <AlertTriangle className="w-3 h-3" />
              <span>{errorCount.total}</span>
            </div>
          )}
          <button
            onClick={handleRefresh}
            className="p-1.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleOpenExternal}
            className="p-1.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors"
            title="Open in new tab"
          >
            <ExternalLink className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Preview Content */}
      <div className="flex-1 relative bg-white">
        {error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-6">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p className="text-sm text-gray-600 mb-2">Preview Error</p>
              <p className="text-xs text-gray-500">{error}</p>
            </div>
          </div>
        ) : previewMode === 'server' && serverUrl ? (
          // Server mode - point to running server
          // Note: Cross-origin issues may occur. User can click "Open in new tab" to view
          <>
            {/* Loading overlay with retry status */}
            {isLoading && (
              <div className="absolute inset-0 bg-[hsl(var(--bolt-bg-primary))] flex items-center justify-center z-10">
                <div className="text-center max-w-sm px-4">
                  <div className="w-12 h-12 border-4 border-[hsl(var(--bolt-accent))] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                  <p className="text-[hsl(var(--bolt-text-secondary))] text-sm font-medium">
                    {retryCount === 0 ? 'Starting dev server...' : `Waiting for dev server... (${retryCount}/${maxRetries})`}
                  </p>
                  <p className="text-[hsl(var(--bolt-text-tertiary))] text-xs mt-2">{serverUrl}</p>

                  {/* Progress bar */}
                  {retryCount > 0 && (
                    <div className="mt-4 w-full bg-[hsl(var(--bolt-bg-tertiary))] rounded-full h-1.5">
                      <div
                        className="bg-[hsl(var(--bolt-accent))] h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min((retryCount / maxRetries) * 100, 100)}%` }}
                      />
                    </div>
                  )}

                  <p className="text-[hsl(var(--bolt-text-tertiary))] text-xs mt-3">
                    {retryStatus === 'waiting' && retryCount === 0 && 'Vite dev server is initializing...'}
                    {retryStatus === 'waiting' && retryCount > 0 && 'Dev server is starting up, please wait...'}
                    {retryStatus === 'retrying' && 'Connecting to dev server...'}
                  </p>
                </div>
              </div>
            )}
            <iframe
              ref={iframeRef}
              src={serverUrl}
              className="w-full h-full border-0"
              sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
              title="Live Preview"
              onLoad={handleIframeLoad}
              onError={handleIframeError}
            />
          </>
        ) : Object.keys(files).length === 0 ? (
          // No files yet
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-6">
              <Play className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-sm text-gray-500">No preview available</p>
              <p className="text-xs text-gray-400 mt-2">Generate code to see preview</p>
            </div>
          </div>
        ) : (
          // Static file preview using srcdoc (no cross-origin issues!)
          <iframe
            ref={iframeRef}
            srcDoc={previewHTML}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-forms allow-modals allow-popups"
            title="Static Preview"
            onLoad={handleIframeLoad}
            onError={handleIframeError}
          />
        )}
      </div>
    </div>
  )
}

// Error capture script to inject into preview iframe (Bolt.new style - ALL 11 LAYERS)
// Captures: JS errors, Promise rejections, Console errors, Network errors, React errors,
// Vite HMR errors, Resource load errors, and more
// NOTE: WebSocket is disabled in srcdoc iframes (origin is null) - using postMessage only
const ERROR_CAPTURE_SCRIPT = `
<script>
(function() {
  // ===== WEBSOCKET LOG STREAM - DISABLED FOR SRCDOC =====
  // srcdoc iframes have origin 'null' which breaks WebSocket URLs
  // We use postMessage to communicate with parent instead
  const projectId = window.__BHARATBUILD_PROJECT_ID__ || 'unknown';

  // Track captured errors to avoid duplicates
  const capturedErrors = new Set();

  // Skip WebSocket connection in srcdoc (origin is null)
  // Parent window handles the WebSocket connection instead
  const isSrcdoc = window.location.protocol === 'about:';

  let socket = null;
  let messageQueue = [];
  let reconnectAttempts = 0;
  const maxReconnectAttempts = 3;

  function connectWebSocket() {
    // Don't attempt WebSocket in srcdoc iframes - it will always fail
    if (isSrcdoc) {
      console.log('[BharatBuild] Skipping WebSocket in srcdoc iframe, using postMessage');
      return;
    }

    try {
      // Build WebSocket URL from parent's origin
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.hostname + ':8000';
      const wsUrl = wsProtocol + '//' + wsHost + '/api/v1/log-stream/stream/' + projectId;

      socket = new WebSocket(wsUrl);

      socket.onopen = function() {
        console.log('[BharatBuild] Log stream connected');
        reconnectAttempts = 0;
        // Send queued messages
        while (messageQueue.length > 0) {
          const msg = messageQueue.shift();
          socket.send(JSON.stringify(msg));
        }
      };

      // ===== HANDLE AUTO-FIX MESSAGES FROM SERVER =====
      socket.onmessage = function(event) {
        try {
          const msg = JSON.parse(event.data);

          if (msg.type === 'fix_started') {
            console.log('[BharatBuild] Auto-fix started:', msg.reason);
            // Notify parent about fix starting
            window.parent.postMessage({
              type: 'bharatbuild-fix-started',
              reason: msg.reason,
              timestamp: msg.timestamp
            }, '*');
          }
          else if (msg.type === 'fix_completed') {
            console.log('[BharatBuild] Auto-fix completed!', msg.patches_applied, 'patches applied');
            // Notify parent about fix completion
            window.parent.postMessage({
              type: 'bharatbuild-fix-completed',
              patchesApplied: msg.patches_applied,
              filesModified: msg.files_modified,
              timestamp: msg.timestamp
            }, '*');
            // Trigger reload after short delay
            setTimeout(function() {
              window.location.reload();
            }, 500);
          }
          else if (msg.type === 'fix_failed') {
            console.log('[BharatBuild] Auto-fix failed:', msg.error);
            window.parent.postMessage({
              type: 'bharatbuild-fix-failed',
              error: msg.error,
              timestamp: msg.timestamp
            }, '*');
          }
          else if (msg.type === 'project_restarted') {
            console.log('[BharatBuild] Project restarted, reloading preview');
            window.parent.postMessage({
              type: 'bharatbuild-project-restarted',
              timestamp: msg.timestamp
            }, '*');
            // Auto-reload on project restart
            setTimeout(function() {
              window.location.reload();
            }, 1000);
          }
        } catch (e) {
          // Ignore non-JSON messages
        }
      };

      socket.onclose = function() {
        if (reconnectAttempts < maxReconnectAttempts) {
          reconnectAttempts++;
          setTimeout(connectWebSocket, 2000 * reconnectAttempts);
        }
      };

      socket.onerror = function() {
        // Silent fail, will use postMessage fallback
      };
    } catch (e) {
      // WebSocket not available, use postMessage fallback
    }
  }

  // Only connect WebSocket if not in srcdoc
  if (!isSrcdoc) {
    connectWebSocket();
  }

  // Send log to WebSocket (with postMessage fallback)
  function sendLog(eventType, payload) {
    const logEntry = {
      source: 'browser',
      type: eventType,
      data: payload,
      timestamp: Date.now()
    };

    // Try WebSocket first
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(logEntry));
    } else {
      // Queue for later if socket is connecting
      if (socket && socket.readyState === WebSocket.CONNECTING) {
        messageQueue.push(logEntry);
      }
    }

    // Always also send via postMessage for iframe communication
    window.parent.postMessage({
      type: 'bharatbuild-' + eventType.replace('_', '-'),
      ...payload
    }, '*');
  }

  // ===== 1. GLOBAL JS ERRORS =====
  window.onerror = function(message, filename, lineno, colno, error) {
    const msgStr = String(message);

    // ===== 1b. MODULE LOADER ERROR DETECTION (Bolt-style) =====
    // Specific detection for dynamic import failures
    if (msgStr.includes('Failed to fetch dynamically imported module') ||
        msgStr.includes('Failed to load module script') ||
        msgStr.includes('Loading module') ||
        msgStr.includes('Cannot find module') ||
        msgStr.includes('Module not found')) {
      sendLog('module_error', {
        source: 'module-loader',
        message: msgStr,
        file: filename,
        line: lineno,
        column: colno,
        stack: error ? error.stack : null,
        errorType: 'module_resolution'
      });
      return false;
    }

    // Regular runtime error
    sendLog('runtime_error', {
      source: 'runtime',
      message: msgStr,
      file: filename,
      line: lineno,
      column: colno,
      stack: error ? error.stack : null
    });
    return false;
  };

  // ===== 2. UNHANDLED PROMISE REJECTIONS =====
  window.addEventListener('unhandledrejection', function(event) {
    sendLog('promise_rejection', {
      message: event.reason?.message || String(event.reason),
      stack: event.reason?.stack || null
    });
  });

  // ===== 3. CONSOLE.ERROR INTERCEPTOR =====
  const originalConsoleError = console.error;
  console.error = function(...args) {
    sendLog('console_error', {
      args: args.map(arg => {
        try {
          return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
        } catch { return String(arg); }
      })
    });
    originalConsoleError.apply(console, args);
  };

  // ===== 4. CONSOLE.WARN INTERCEPTOR =====
  const originalConsoleWarn = console.warn;
  console.warn = function(...args) {
    sendLog('console_warn', {
      args: args.map(arg => {
        try {
          return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
        } catch { return String(arg); }
      })
    });
    originalConsoleWarn.apply(console, args);
  };

  // ===== 5. FETCH INTERCEPTOR =====
  const originalFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const method = (init && init.method) || 'GET';
    const startTime = Date.now();

    try {
      const response = await originalFetch.apply(this, arguments);
      const duration = Date.now() - startTime;

      if (!response.ok) {
        let errorMessage = 'HTTP ' + response.status + ' ' + response.statusText;
        try {
          const clonedResponse = response.clone();
          const contentType = clonedResponse.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = await clonedResponse.json();
            if (errorData.message || errorData.error) {
              errorMessage += ': ' + (errorData.message || errorData.error);
            }
          }
        } catch (e) {}

        sendLog('fetch_error', {
          url: url,
          method: method,
          status: response.status,
          statusText: response.statusText,
          message: errorMessage,
          duration: duration
        });
      }
      return response;
    } catch (error) {
      const duration = Date.now() - startTime;
      let errorType = 'network_error';
      let message = error.message || 'Network request failed';

      if (message.includes('CORS') || message.includes('cross-origin') ||
          message.includes('Failed to fetch') || message.includes('NetworkError')) {
        errorType = 'cors_error';
        message = 'CORS Error: ' + message;
      }

      sendLog('fetch_exception', {
        url: url,
        method: method,
        error: message,
        stack: error.stack,
        errorType: errorType,
        duration: duration
      });
      throw error;
    }
  };

  // ===== 6. XHR INTERCEPTOR =====
  const originalXHROpen = XMLHttpRequest.prototype.open;
  const originalXHRSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
    this._bharatbuild_method = method;
    this._bharatbuild_url = url;
    this._bharatbuild_startTime = null;
    return originalXHROpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function(body) {
    this._bharatbuild_startTime = Date.now();
    const xhr = this;

    xhr.addEventListener('load', function() {
      const duration = Date.now() - (xhr._bharatbuild_startTime || Date.now());

      if (xhr.status >= 400) {
        let errorMessage = 'HTTP ' + xhr.status + ' ' + xhr.statusText;
        try {
          const contentType = xhr.getResponseHeader('content-type');
          if (contentType && contentType.includes('application/json')) {
            const errorData = JSON.parse(xhr.responseText);
            if (errorData.message || errorData.error) {
              errorMessage += ': ' + (errorData.message || errorData.error);
            }
          }
        } catch (e) {}

        sendLog('xhr_error', {
          url: xhr._bharatbuild_url,
          method: xhr._bharatbuild_method,
          status: xhr.status,
          message: errorMessage,
          duration: duration
        });
      }
    });

    xhr.addEventListener('error', function() {
      const duration = Date.now() - (xhr._bharatbuild_startTime || Date.now());
      sendLog('xhr_error', {
        url: xhr._bharatbuild_url,
        method: xhr._bharatbuild_method,
        status: 0,
        message: 'Network request failed (XHR)',
        duration: duration
      });
    });

    xhr.addEventListener('timeout', function() {
      const duration = Date.now() - (xhr._bharatbuild_startTime || Date.now());
      sendLog('xhr_error', {
        url: xhr._bharatbuild_url,
        method: xhr._bharatbuild_method,
        status: 0,
        message: 'Request timeout',
        duration: duration
      });
    });

    return originalXHRSend.apply(this, arguments);
  };

  // ===== 7. RESOURCE LOAD ERRORS (images, scripts, stylesheets) =====
  window.addEventListener('error', function(event) {
    // Only handle resource errors (not JS errors - those go through window.onerror)
    if (event.target && event.target !== window) {
      const target = event.target;
      const tagName = target.tagName ? target.tagName.toLowerCase() : '';

      if (['img', 'script', 'link', 'video', 'audio', 'source', 'iframe'].includes(tagName)) {
        const src = target.src || target.href || 'unknown';
        const errorKey = 'resource:' + src;

        // Deduplicate
        if (capturedErrors.has(errorKey)) return;
        capturedErrors.add(errorKey);

        sendLog('resource_error', {
          tagName: tagName,
          src: src,
          message: 'Failed to load ' + tagName + ': ' + src
        });
      }
    }
  }, true); // Use capture phase to catch before bubbling

  // ===== 8. VITE HMR ERROR CAPTURE =====
  // Vite sends custom events for HMR errors
  if (typeof window !== 'undefined') {
    // Vite error overlay events
    window.addEventListener('vite:error', function(event) {
      const err = event.detail?.err || event.detail || event;
      sendLog('hmr_error', {
        source: 'vite',
        message: err.message || 'Vite HMR Error',
        stack: err.stack,
        file: err.loc?.file || err.id,
        line: err.loc?.line,
        column: err.loc?.column,
        plugin: err.plugin,
        frame: err.frame
      });
    });

    // Vite beforeUpdate - track HMR updates
    window.addEventListener('vite:beforeUpdate', function(event) {
      console.log('[BharatBuild] HMR update incoming:', event.detail);
    });

    // Vite afterUpdate - HMR completed
    window.addEventListener('vite:afterUpdate', function(event) {
      console.log('[BharatBuild] HMR update completed');
      // Notify parent that code was hot-reloaded
      window.parent.postMessage({
        type: 'bharatbuild-hmr-update',
        timestamp: Date.now()
      }, '*');
    });

    // Webpack HMR errors (for projects using webpack)
    if (typeof module !== 'undefined' && module.hot) {
      module.hot.addStatusHandler(function(status) {
        if (status === 'fail' || status === 'abort') {
          sendLog('hmr_error', {
            source: 'webpack',
            message: 'Webpack HMR ' + status,
            status: status
          });
        }
      });
    }

    // ===== VITE ERROR OVERLAY OBSERVER =====
    // Vite's "Failed to resolve import" errors appear in a custom web component
    // called "vite-error-overlay" BEFORE HMR is established. We need to observe
    // the DOM for this element and extract the error message.
    (function observeViteErrorOverlay() {
      const capturedViteErrors = new Set();

      function extractViteErrorFromOverlay(overlay) {
        try {
          // Vite error overlay uses shadow DOM
          const shadowRoot = overlay.shadowRoot;
          if (!shadowRoot) return null;

          // Try to find error message in shadow DOM
          const messageEl = shadowRoot.querySelector('.message') ||
                           shadowRoot.querySelector('.error') ||
                           shadowRoot.querySelector('[class*="message"]') ||
                           shadowRoot.querySelector('pre');

          if (messageEl) {
            return messageEl.textContent || messageEl.innerText;
          }

          // Fallback: get all text content
          return shadowRoot.textContent || overlay.textContent;
        } catch (e) {
          console.log('[BharatBuild] Error extracting Vite error:', e);
          return overlay.textContent || overlay.innerText;
        }
      }

      function handleViteOverlay(overlay) {
        const errorText = extractViteErrorFromOverlay(overlay);
        if (!errorText) return;

        // Extract relevant error info
        const errorKey = errorText.substring(0, 200);
        if (capturedViteErrors.has(errorKey)) return;
        capturedViteErrors.add(errorKey);

        console.log('[BharatBuild] 🔴 CAPTURED VITE ERROR OVERLAY:', errorText.substring(0, 200));

        // Parse error message to extract file and line info
        let file = null;
        let line = null;
        let column = null;

        // Pattern: Failed to resolve import "./pages/LoginPage" from "src/App.tsx"
        const importMatch = errorText.match(/Failed to resolve import [\"']([^\"']+)[\"'] from [\"']([^\"']+)[\"']/);
        if (importMatch) {
          file = importMatch[2]; // The file trying to import
        }

        // Pattern: file:line:column
        const locMatch = errorText.match(/([\\w/.]+\\.tsx?):(\\d+):(\\d+)/);
        if (locMatch) {
          file = file || locMatch[1];
          line = parseInt(locMatch[2]);
          column = parseInt(locMatch[3]);
        }

        sendLog('hmr_error', {
          source: 'vite-overlay',
          message: errorText.substring(0, 2000),
          file: file,
          line: line,
          column: column,
          errorType: 'import_resolution'
        });
      }

      // Observer callback
      function observerCallback(mutations) {
        mutations.forEach(function(mutation) {
          mutation.addedNodes.forEach(function(node) {
            if (node.nodeType === 1) {
              // Check if it's a Vite error overlay
              if (node.tagName && node.tagName.toLowerCase() === 'vite-error-overlay') {
                console.log('[BharatBuild] Vite error overlay detected!');
                // Wait a tick for shadow DOM to be populated
                setTimeout(function() { handleViteOverlay(node); }, 100);
              }
              // Also check for id-based overlays
              if (node.id === 'vite-error-overlay') {
                setTimeout(function() { handleViteOverlay(node); }, 100);
              }
            }
          });
        });
      }

      // Create observer
      const viteErrorObserver = new MutationObserver(observerCallback);

      // Start observing when DOM is ready
      function startObserving() {
        if (document.body) {
          viteErrorObserver.observe(document.body, { childList: true, subtree: true });
          console.log('[BharatBuild] Vite error overlay observer started');

          // Also check for existing overlay (in case it appeared before observer started)
          const existingOverlay = document.querySelector('vite-error-overlay');
          if (existingOverlay) {
            handleViteOverlay(existingOverlay);
          }
        } else {
          document.addEventListener('DOMContentLoaded', function() {
            viteErrorObserver.observe(document.body, { childList: true, subtree: true });
          });
        }
      }

      startObserving();
    })();

    // ===== NEXT.JS FAST REFRESH ERROR CAPTURE =====
    // Next.js uses a special global function for dev hot messages
    window.__NEXT_HMR_CB = window.__NEXT_HMR_CB || [];
    window.__NEXTDevHotMessage = function(msg) {
      sendLog('hmr_error', {
        source: 'nextjs',
        message: typeof msg === 'string' ? msg : JSON.stringify(msg),
        errorType: 'fast_refresh'
      });
    };

    // Next.js also uses custom events
    window.addEventListener('next-route-announcer', function() {
      console.log('[BharatBuild] Next.js route change detected');
    });

    // Capture Next.js hydration errors via MutationObserver on error overlay
    const nextErrorObserver = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
          if (node.nodeType === 1) {
            // Check for Next.js error overlay
            if (node.id === '__next-build-watcher' ||
                node.id === 'nextjs__container_errors_label' ||
                node.className?.includes('nextjs-toast') ||
                node.getAttribute?.('data-nextjs-dialog')) {
              const errorText = node.textContent || node.innerText || '';
              if (errorText) {
                sendLog('hmr_error', {
                  source: 'nextjs-overlay',
                  message: errorText.substring(0, 1000),
                  errorType: 'build_error'
                });
              }
            }
          }
        });
      });
    });

    // Start observing when DOM is ready
    if (document.body) {
      nextErrorObserver.observe(document.body, { childList: true, subtree: true });
    } else {
      document.addEventListener('DOMContentLoaded', function() {
        nextErrorObserver.observe(document.body, { childList: true, subtree: true });
      });
    }
  }

  // ===== 9. REACT ERROR BOUNDARY INJECTION =====
  // Wrap React's createElement to catch render errors
  // This catches errors that window.onerror cannot
  (function injectReactErrorCapture() {
    // Wait for React to be available
    function tryInjectReact() {
      if (typeof React !== 'undefined' && React.createElement) {
        const originalCreateElement = React.createElement;

        // Create a global error boundary component
        window.__BharatBuildErrorBoundary = class extends React.Component {
          constructor(props) {
            super(props);
            this.state = { hasError: false, error: null };
          }

          static getDerivedStateFromError(error) {
            return { hasError: true, error: error };
          }

          componentDidCatch(error, errorInfo) {
            sendLog('react_error', {
              message: error.message || String(error),
              stack: error.stack,
              componentStack: errorInfo.componentStack,
              errorType: 'render_error'
            });
          }

          render() {
            if (this.state.hasError) {
              return React.createElement('div', {
                style: {
                  padding: '20px',
                  background: '#fee2e2',
                  border: '1px solid #ef4444',
                  borderRadius: '8px',
                  margin: '10px',
                  fontFamily: 'monospace'
                }
              }, [
                React.createElement('h3', {
                  key: 'title',
                  style: { color: '#dc2626', marginBottom: '10px' }
                }, '⚠️ React Component Error'),
                React.createElement('pre', {
                  key: 'error',
                  style: {
                    whiteSpace: 'pre-wrap',
                    fontSize: '12px',
                    color: '#7f1d1d'
                  }
                }, this.state.error?.message || 'Unknown error')
              ]);
            }
            return this.props.children;
          }
        };

        console.log('[BharatBuild] React error boundary injected');
        return true;
      }
      return false;
    }

    // Try immediately, then retry after DOM is ready
    if (!tryInjectReact()) {
      document.addEventListener('DOMContentLoaded', function() {
        setTimeout(tryInjectReact, 100);
      });
      // Also try after a delay for async React loading
      setTimeout(tryInjectReact, 500);
      setTimeout(tryInjectReact, 1500);
    }
  })();

  // ===== 10. NAVIGATION/HISTORY ERRORS =====
  window.addEventListener('popstate', function(event) {
    // Track navigation for debugging
    console.log('[BharatBuild] Navigation:', window.location.href);
  });

  // Catch navigation errors
  window.addEventListener('pagehide', function(event) {
    if (!event.persisted) {
      // Page is being unloaded (not bfcache)
      console.log('[BharatBuild] Page unloading');
    }
  });

  // ===== 11. SECURITY/CSP ERRORS =====
  document.addEventListener('securitypolicyviolation', function(event) {
    sendLog('csp_error', {
      message: 'Content Security Policy violation',
      blockedURI: event.blockedURI,
      violatedDirective: event.violatedDirective,
      originalPolicy: event.originalPolicy,
      sourceFile: event.sourceFile,
      lineNumber: event.lineNumber,
      columnNumber: event.columnNumber
    });
  });

  console.log('[BharatBuild] Error capture initialized (11 layers active)');
})();
</script>
`;

function generatePreviewHTML(files: Record<string, string>, entryPoint: string, projectId?: string): string {
  // Debug: Log available files
  console.log('[LivePreview] Available files:', Object.keys(files))

  // Generate project ID injection script
  const PROJECT_ID_SCRIPT = `<script>window.__BHARATBUILD_PROJECT_ID__ = '${projectId || 'unknown'}';</script>`

  // Check if this is a React/TypeScript/bundled project that needs a dev server
  const needsBundling = Object.keys(files).some(path => {
    const content = files[path] || ''
    const isReactFile = path.endsWith('.tsx') || path.endsWith('.jsx')
    const hasReactImport = content.includes('from \'react\'') || content.includes('from "react"')
    const hasJSXImport = content.includes('import React') || content.includes('createRoot')
    const isViteProject = path === 'vite.config.ts' || path === 'vite.config.js'
    return isReactFile || hasReactImport || hasJSXImport || isViteProject
  })

  // If project needs bundling, show helpful message
  if (needsBundling) {
    console.log('[LivePreview] Detected React/TS project that needs bundling')
    return `<!DOCTYPE html>
<html lang="en">
<head>
  ${PROJECT_ID_SCRIPT}
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview - Bundling Required</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #e4e4e7;
    }
    .container {
      text-align: center;
      padding: 40px;
      max-width: 500px;
    }
    .icon {
      width: 80px;
      height: 80px;
      margin: 0 auto 24px;
      background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 40px;
    }
    h2 {
      font-size: 24px;
      font-weight: 600;
      margin-bottom: 12px;
      color: #fff;
    }
    p {
      color: #a1a1aa;
      line-height: 1.6;
      margin-bottom: 24px;
    }
    .tech-badge {
      display: inline-block;
      padding: 4px 12px;
      background: rgba(59, 130, 246, 0.2);
      border: 1px solid rgba(59, 130, 246, 0.3);
      border-radius: 20px;
      font-size: 12px;
      color: #60a5fa;
      margin: 4px;
    }
    .steps {
      text-align: left;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 12px;
      padding: 20px;
      margin-top: 24px;
    }
    .steps h3 {
      font-size: 14px;
      color: #a1a1aa;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .step {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 8px 0;
    }
    .step-num {
      width: 24px;
      height: 24px;
      background: rgba(59, 130, 246, 0.2);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 600;
      color: #60a5fa;
      flex-shrink: 0;
    }
    .step code {
      background: rgba(0, 0, 0, 0.3);
      padding: 2px 8px;
      border-radius: 4px;
      font-family: 'Monaco', 'Consolas', monospace;
      font-size: 13px;
      color: #fbbf24;
    }
    .export-hint {
      margin-top: 20px;
      padding: 12px;
      background: rgba(34, 197, 94, 0.1);
      border: 1px solid rgba(34, 197, 94, 0.2);
      border-radius: 8px;
      font-size: 13px;
      color: #4ade80;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">⚛️</div>
    <h2>React/TypeScript Project</h2>
    <p>This project uses modern frameworks that need compilation before running in the browser.</p>

    <div>
      <span class="tech-badge">React</span>
      <span class="tech-badge">TypeScript</span>
      <span class="tech-badge">Vite</span>
    </div>

    <div class="steps">
      <h3>To run locally:</h3>
      <div class="step">
        <span class="step-num">1</span>
        <span>Click <strong>Export</strong> to download the project</span>
      </div>
      <div class="step">
        <span class="step-num">2</span>
        <span>Extract and run <code>npm install</code></span>
      </div>
      <div class="step">
        <span class="step-num">3</span>
        <span>Start dev server: <code>npm run dev</code></span>
      </div>
      <div class="step">
        <span class="step-num">4</span>
        <span>Open <code>http://localhost:5173</code></span>
      </div>
    </div>

    <div class="export-hint">
      💡 Your code is ready! Use the <strong>Export</strong> button to download and run locally.
    </div>
  </div>
</body>
</html>`
  }

  // Find HTML file - check multiple possible paths
  let htmlFile: string | undefined
  let htmlFilePath: string | undefined

  // Priority order for finding HTML files
  const htmlSearchPaths = [
    entryPoint,
    'index.html',
    'src/index.html',
    'public/index.html',
    // Also search by filename in any directory
    ...Object.keys(files).filter(path => path.endsWith('.html'))
  ]

  for (const path of htmlSearchPaths) {
    if (files[path]) {
      htmlFile = files[path]
      htmlFilePath = path
      console.log('[LivePreview] Found HTML file at:', path)
      break
    }
  }

  if (htmlFile) {
    // If HTML exists, inject other files
    let html = htmlFile

    // Inject CSS - collect all CSS files
    const cssFiles = Object.entries(files).filter(([path]) => path.endsWith('.css'))
    console.log('[LivePreview] Found CSS files:', cssFiles.map(([p]) => p))

    const cssContent = cssFiles.map(([_, content]) => content).join('\n')
    if (cssContent) {
      // Try to inject before </head>, or append to end if no </head>
      if (html.includes('</head>')) {
        html = html.replace('</head>', `<style>\n${cssContent}\n</style>\n</head>`)
      } else if (html.includes('<head>')) {
        html = html.replace('<head>', `<head>\n<style>\n${cssContent}\n</style>`)
      } else {
        // No head tag - wrap in basic structure
        html = `<!DOCTYPE html><html><head><style>${cssContent}</style></head><body>${html}</body></html>`
      }
    }

    // Inject JS (as modules) - collect all JS files
    const jsFiles = Object.entries(files).filter(([path]) =>
      path.endsWith('.js') || path.endsWith('.jsx') || path.endsWith('.ts') || path.endsWith('.tsx')
    )
    console.log('[LivePreview] Found JS files:', jsFiles.map(([p]) => p))

    // Only inject simple JS files (not React/complex frameworks)
    const simpleJsFiles = jsFiles.filter(([path, content]) => {
      // Skip files that look like React components or require bundling
      const hasJSX = content.includes('React') || content.includes('jsx') || content.includes('</')
      const hasImports = content.includes('import ') || content.includes('require(')
      return !hasJSX && !hasImports
    })

    const jsContent = simpleJsFiles.map(([_, content]) => content).join('\n')
    if (jsContent) {
      if (html.includes('</body>')) {
        html = html.replace('</body>', `<script>\n${jsContent}\n</script>\n</body>`)
      } else {
        html += `<script>\n${jsContent}\n</script>`
      }
    }

    // Inject project ID and error capture script before </head> or at the start
    // PROJECT_ID_SCRIPT must come first so ERROR_CAPTURE_SCRIPT can use it
    if (html.includes('<head>')) {
      html = html.replace('<head>', `<head>${PROJECT_ID_SCRIPT}${ERROR_CAPTURE_SCRIPT}`)
    } else if (html.includes('<html>')) {
      html = html.replace('<html>', `<html><head>${PROJECT_ID_SCRIPT}${ERROR_CAPTURE_SCRIPT}</head>`)
    } else {
      html = `${PROJECT_ID_SCRIPT}${ERROR_CAPTURE_SCRIPT}${html}`
    }

    console.log('[LivePreview] Generated HTML preview (length:', html.length, ')')
    return html
  }

  // No HTML file found - check if we have any files at all
  console.log('[LivePreview] No HTML file found, generating fallback')

  // Generate HTML from scratch using CSS and JS files
  const jsFiles = Object.entries(files).filter(([path]) =>
    path.endsWith('.js') || path.endsWith('.jsx')
  )
  const cssFiles = Object.entries(files).filter(([path]) => path.endsWith('.css'))

  const css = cssFiles.map(([_, content]) => content).join('\n')
  const js = jsFiles.map(([_, content]) => content).join('\n')

  // If we have no files at all, return a helpful message
  if (Object.keys(files).length === 0) {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  ${PROJECT_ID_SCRIPT}
  ${ERROR_CAPTURE_SCRIPT}
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
      background: #f5f5f5;
      color: #666;
    }
    .message { text-align: center; }
    h2 { color: #333; margin-bottom: 10px; }
  </style>
</head>
<body>
  <div class="message">
    <h2>No files to preview</h2>
    <p>Generate a project to see the preview here.</p>
  </div>
</body>
</html>`
  }

  return `<!DOCTYPE html>
<html lang="en">
<head>
  ${PROJECT_ID_SCRIPT}
  ${ERROR_CAPTURE_SCRIPT}
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    ${css}
  </style>
</head>
<body>
  <div id="root"></div>
  <div id="app"></div>

  <script type="module">
    ${js}
  </script>
</body>
</html>`
}
