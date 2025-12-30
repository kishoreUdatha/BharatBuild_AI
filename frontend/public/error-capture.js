/**
 * Browser Error Capture Script
 *
 * ARCHITECTURE:
 * Browser = Reporter (captures errors)
 * Backend = Doctor (fixes errors)
 *
 * This script is injected into preview iframes to capture:
 * - JavaScript runtime errors (window.onerror)
 * - Promise rejections (unhandledrejection)
 * - Console errors (console.error patch)
 * - Network errors (fetch patch)
 * - Resource load errors (error event on window)
 *
 * Errors are sent to backend for normalization and auto-fixing.
 * The browser itself does NOT fix errors - it only reports them.
 */

(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    // Backend endpoint for error reporting
    endpoint: window.__ERROR_ENDPOINT__ || '/api/v1/errors/browser',
    // Project ID (injected by parent)
    projectId: window.__PROJECT_ID__ || null,
    // Debounce time in ms
    debounceMs: 1000,
    // Max errors to buffer before force send
    maxBufferSize: 10,
    // Ignore patterns (false positives)
    ignorePatterns: [
      /ResizeObserver loop/i,
      /Loading chunk.*failed/i, // Handled separately
      /Script error\./i, // Cross-origin scripts
      /Extension context invalidated/i,
      /chrome-extension/i,
      /moz-extension/i,
    ],
    // Error deduplication window (ms)
    dedupeWindowMs: 5000,
  };

  // State
  let errorBuffer = [];
  let debounceTimer = null;
  let recentErrors = new Map(); // For deduplication
  let isCapturing = true;

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  /**
   * Generate unique error key for deduplication
   */
  function getErrorKey(error) {
    return `${error.type}:${error.message}:${error.file || ''}:${error.line || ''}`;
  }

  /**
   * Check if error should be ignored
   */
  function shouldIgnore(message) {
    if (!message) return true;
    return CONFIG.ignorePatterns.some(pattern => pattern.test(message));
  }

  /**
   * Check if error is duplicate (within dedupe window)
   */
  function isDuplicate(error) {
    const key = getErrorKey(error);
    const now = Date.now();

    if (recentErrors.has(key)) {
      const lastSeen = recentErrors.get(key);
      if (now - lastSeen < CONFIG.dedupeWindowMs) {
        return true;
      }
    }

    recentErrors.set(key, now);

    // Cleanup old entries
    if (recentErrors.size > 100) {
      const cutoff = now - CONFIG.dedupeWindowMs;
      for (const [k, v] of recentErrors) {
        if (v < cutoff) recentErrors.delete(k);
      }
    }

    return false;
  }

  /**
   * Extract file info from stack trace
   */
  function parseStack(stack) {
    if (!stack) return { file: null, line: null, column: null };

    // Match patterns like:
    // at Component (http://localhost:3000/src/App.tsx:42:15)
    // at http://localhost:3000/src/App.tsx:42:15
    const match = stack.match(/(?:at\s+)?(?:\S+\s+)?\(?([^():]+):(\d+):(\d+)\)?/);

    if (match) {
      let file = match[1];
      // Clean up file path
      file = file.replace(/^https?:\/\/[^/]+/, '');
      file = file.replace(/\?.*$/, '');

      return {
        file,
        line: parseInt(match[2], 10),
        column: parseInt(match[3], 10),
      };
    }

    return { file: null, line: null, column: null };
  }

  /**
   * Detect framework from error or stack
   */
  function detectFramework(error, stack) {
    const combined = `${error} ${stack || ''}`.toLowerCase();

    if (combined.includes('react') || combined.includes('jsx')) return 'react';
    if (combined.includes('vue') || combined.includes('.vue')) return 'vue';
    if (combined.includes('angular') || combined.includes('@angular')) return 'angular';
    if (combined.includes('svelte')) return 'svelte';
    if (combined.includes('next')) return 'nextjs';
    if (combined.includes('nuxt')) return 'nuxt';
    if (combined.includes('vite')) return 'vite';

    return 'unknown';
  }

  /**
   * Classify error type
   */
  function classifyError(message, stack) {
    const msg = (message || '').toLowerCase();

    if (msg.includes('is not defined') || msg.includes('is not a function')) {
      return 'REFERENCE_ERROR';
    }
    if (msg.includes('cannot read') || msg.includes('undefined is not')) {
      return 'TYPE_ERROR';
    }
    if (msg.includes('syntax') || msg.includes('unexpected token')) {
      return 'SYNTAX_ERROR';
    }
    if (msg.includes('cors') || msg.includes('cross-origin')) {
      return 'CORS_ERROR';
    }
    if (msg.includes('network') || msg.includes('failed to fetch')) {
      return 'NETWORK_ERROR';
    }
    if (msg.includes('chunk') || msg.includes('loading')) {
      return 'CHUNK_LOAD_ERROR';
    }
    if (msg.includes('hydration') || msg.includes('hydrat')) {
      return 'HYDRATION_ERROR';
    }
    if (msg.includes('hook') || msg.includes('usestate') || msg.includes('useeffect')) {
      return 'HOOK_ERROR';
    }
    if (msg.includes('module') || msg.includes('import') || msg.includes('export')) {
      return 'MODULE_ERROR';
    }

    return 'RUNTIME_ERROR';
  }

  // =========================================================================
  // ERROR SENDING
  // =========================================================================

  /**
   * Send errors to backend
   */
  function sendErrors() {
    if (errorBuffer.length === 0) return;
    if (!CONFIG.projectId) {
      console.warn('[ErrorCapture] No project ID configured');
      return;
    }

    const errors = [...errorBuffer];
    errorBuffer = [];

    // Build payload
    const payload = {
      project_id: CONFIG.projectId,
      source: 'browser',
      errors: errors,
      timestamp: Date.now(),
      url: window.location.href,
      userAgent: navigator.userAgent,
    };

    // Send to backend (fire-and-forget)
    fetch(CONFIG.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true, // Ensure request completes even if page unloads
    }).catch(err => {
      // Don't report fetch errors to avoid infinite loop
      console.debug('[ErrorCapture] Failed to send errors:', err);
    });
  }

  /**
   * Queue error for sending (with debounce)
   */
  function queueError(error) {
    if (!isCapturing) return;
    if (shouldIgnore(error.message)) return;
    if (isDuplicate(error)) return;

    errorBuffer.push(error);

    // Force send if buffer is full
    if (errorBuffer.length >= CONFIG.maxBufferSize) {
      clearTimeout(debounceTimer);
      sendErrors();
      return;
    }

    // Debounced send
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(sendErrors, CONFIG.debounceMs);
  }

  // =========================================================================
  // ERROR CAPTURE HOOKS
  // =========================================================================

  /**
   * A. JavaScript Runtime Errors
   */
  window.onerror = function(message, source, line, column, error) {
    const stackInfo = parseStack(error?.stack);

    queueError({
      type: 'JS_RUNTIME',
      category: classifyError(message, error?.stack),
      message: String(message),
      source: source || stackInfo.file,
      file: stackInfo.file || source,
      line: line || stackInfo.line,
      column: column || stackInfo.column,
      stack: error?.stack || null,
      framework: detectFramework(message, error?.stack),
      timestamp: Date.now(),
    });

    // Don't prevent default error handling
    return false;
  };

  /**
   * B. Unhandled Promise Rejections
   */
  window.onunhandledrejection = function(event) {
    const reason = event.reason;
    const message = reason?.message || String(reason);
    const stack = reason?.stack || null;
    const stackInfo = parseStack(stack);

    queueError({
      type: 'PROMISE_REJECTION',
      category: classifyError(message, stack),
      message: message,
      file: stackInfo.file,
      line: stackInfo.line,
      column: stackInfo.column,
      stack: stack,
      framework: detectFramework(message, stack),
      timestamp: Date.now(),
    });
  };

  /**
   * C. Console Errors (patched)
   */
  const originalConsoleError = console.error;
  console.error = function(...args) {
    // Call original first
    originalConsoleError.apply(console, args);

    // Extract message
    const message = args.map(arg => {
      if (arg instanceof Error) return arg.message;
      if (typeof arg === 'object') {
        try { return JSON.stringify(arg); } catch { return String(arg); }
      }
      return String(arg);
    }).join(' ');

    // Extract stack if first arg is Error
    const stack = args[0] instanceof Error ? args[0].stack : null;
    const stackInfo = parseStack(stack);

    queueError({
      type: 'CONSOLE_ERROR',
      category: classifyError(message, stack),
      message: message,
      file: stackInfo.file,
      line: stackInfo.line,
      column: stackInfo.column,
      stack: stack,
      framework: detectFramework(message, stack),
      timestamp: Date.now(),
    });
  };

  /**
   * D. Network Errors (fetch patch)
   */
  const originalFetch = window.fetch;
  window.fetch = function(input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const method = init?.method || 'GET';

    return originalFetch.apply(this, arguments)
      .then(response => {
        // Report non-OK responses (4xx, 5xx)
        if (!response.ok) {
          queueError({
            type: 'NETWORK_ERROR',
            category: response.status >= 500 ? 'SERVER_ERROR' : 'CLIENT_ERROR',
            message: `HTTP ${response.status}: ${response.statusText}`,
            url: url,
            method: method,
            status: response.status,
            statusText: response.statusText,
            timestamp: Date.now(),
          });
        }
        return response;
      })
      .catch(error => {
        queueError({
          type: 'NETWORK_ERROR',
          category: 'FETCH_FAILED',
          message: error.message || 'Network request failed',
          url: url,
          method: method,
          stack: error.stack,
          timestamp: Date.now(),
        });
        throw error; // Re-throw to preserve original behavior
      });
  };

  /**
   * E. Resource Load Errors (images, scripts, stylesheets)
   */
  window.addEventListener('error', function(event) {
    // Only handle resource errors (not JS errors)
    if (event.target && event.target !== window) {
      const target = event.target;
      const tagName = target.tagName?.toLowerCase();

      if (['img', 'script', 'link', 'video', 'audio', 'source'].includes(tagName)) {
        queueError({
          type: 'RESOURCE_ERROR',
          category: 'LOAD_FAILED',
          message: `Failed to load ${tagName}: ${target.src || target.href}`,
          resource: target.src || target.href,
          tagName: tagName,
          timestamp: Date.now(),
        });
      }
    }
  }, true); // Capture phase

  /**
   * F. React Error Boundary (if React is available)
   */
  if (typeof window.__REACT_ERROR_OVERLAY_GLOBAL_HOOK__ !== 'undefined') {
    // React dev overlay hook
    const originalHandleError = window.__REACT_ERROR_OVERLAY_GLOBAL_HOOK__?.handleRuntimeError;
    if (originalHandleError) {
      window.__REACT_ERROR_OVERLAY_GLOBAL_HOOK__.handleRuntimeError = function(error) {
        queueError({
          type: 'REACT_ERROR',
          category: 'COMPONENT_ERROR',
          message: error.message,
          stack: error.stack,
          framework: 'react',
          timestamp: Date.now(),
        });
        return originalHandleError.apply(this, arguments);
      };
    }
  }

  // =========================================================================
  // LIFECYCLE
  // =========================================================================

  /**
   * Send any remaining errors before page unload
   */
  window.addEventListener('beforeunload', function() {
    if (errorBuffer.length > 0) {
      sendErrors();
    }
  });

  /**
   * Pause/resume capture (for debugging)
   */
  window.__errorCapture = {
    pause: function() { isCapturing = false; },
    resume: function() { isCapturing = true; },
    flush: function() { sendErrors(); },
    getBuffer: function() { return [...errorBuffer]; },
    setProjectId: function(id) { CONFIG.projectId = id; },
    setEndpoint: function(url) { CONFIG.endpoint = url; },
  };

  // Log initialization
  console.debug('[ErrorCapture] Browser error capture initialized', {
    projectId: CONFIG.projectId,
    endpoint: CONFIG.endpoint,
  });

})();
