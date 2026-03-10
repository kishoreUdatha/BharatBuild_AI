/**
 * WebContainer Service for BharatBuild AI
 * ========================================
 * Runs Node.js projects entirely in the browser using StackBlitz WebContainer API.
 * No backend server needed for code execution - saves 80-95% server costs!
 *
 * Supports: React, Vue, Next.js, Express, and any Node.js project
 */

import { WebContainer, FileSystemTree } from '@webcontainer/api'

// Singleton instance
let webcontainerInstance: WebContainer | null = null
let bootPromise: Promise<WebContainer> | null = null

// Event types for status updates
export type WebContainerStatus =
  | 'idle'
  | 'booting'
  | 'ready'
  | 'installing'
  | 'starting'
  | 'running'
  | 'error'

export interface WebContainerEvents {
  onStatusChange?: (status: WebContainerStatus, message?: string) => void
  onOutput?: (data: string) => void
  onError?: (error: string) => void
  onServerReady?: (url: string, port: number) => void
}

/**
 * Check if WebContainer is supported in this browser
 */
export function isWebContainerSupported(): boolean {
  if (typeof window === 'undefined') return false

  // Check for SharedArrayBuffer (required for WebContainer)
  if (typeof SharedArrayBuffer === 'undefined') {
    console.warn('[WebContainer] SharedArrayBuffer not available. Headers may not be configured.')
    return false
  }

  return true
}

/**
 * Boot the WebContainer instance (singleton)
 */
export async function bootWebContainer(): Promise<WebContainer> {
  if (webcontainerInstance) {
    return webcontainerInstance
  }

  if (bootPromise) {
    return bootPromise
  }

  bootPromise = (async () => {
    try {
      console.log('[WebContainer] Booting...')
      webcontainerInstance = await WebContainer.boot()
      console.log('[WebContainer] Boot complete!')
      return webcontainerInstance
    } catch (error) {
      console.error('[WebContainer] Boot failed:', error)
      bootPromise = null
      throw error
    }
  })()

  return bootPromise
}

/**
 * Get the current WebContainer instance
 */
export function getWebContainer(): WebContainer | null {
  return webcontainerInstance
}

/**
 * Convert project files to WebContainer FileSystemTree format
 */
export function convertToFileSystemTree(files: Record<string, string>): FileSystemTree {
  const tree: FileSystemTree = {}

  for (const [path, content] of Object.entries(files)) {
    const parts = path.split('/').filter(Boolean)
    let current = tree

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1

      if (isFile) {
        current[part] = {
          file: {
            contents: content
          }
        }
      } else {
        if (!current[part]) {
          current[part] = {
            directory: {}
          }
        }
        const dir = current[part]
        if ('directory' in dir) {
          current = dir.directory
        }
      }
    }
  }

  return tree
}

/**
 * Main class to manage WebContainer lifecycle
 */
export class WebContainerManager {
  private container: WebContainer | null = null
  private events: WebContainerEvents = {}
  private serverProcess: any = null
  private currentUrl: string | null = null

  constructor(events?: WebContainerEvents) {
    this.events = events || {}
  }

  /**
   * Update event handlers
   */
  setEvents(events: WebContainerEvents) {
    this.events = { ...this.events, ...events }
  }

  /**
   * Emit status change
   */
  private emitStatus(status: WebContainerStatus, message?: string) {
    this.events.onStatusChange?.(status, message)
  }

  /**
   * Emit output
   */
  private emitOutput(data: string) {
    this.events.onOutput?.(data)
  }

  /**
   * Emit error
   */
  private emitError(error: string) {
    this.events.onError?.(error)
  }

  /**
   * Initialize WebContainer
   */
  async init(): Promise<boolean> {
    if (!isWebContainerSupported()) {
      this.emitError('WebContainer is not supported in this browser. Make sure COOP/COEP headers are configured.')
      return false
    }

    try {
      this.emitStatus('booting', 'Starting WebContainer...')
      this.container = await bootWebContainer()
      this.emitStatus('ready', 'WebContainer ready')
      return true
    } catch (error: any) {
      this.emitError(`Failed to boot WebContainer: ${error.message}`)
      this.emitStatus('error', error.message)
      return false
    }
  }

  /**
   * Mount files to WebContainer
   */
  async mountFiles(files: Record<string, string>): Promise<boolean> {
    if (!this.container) {
      const success = await this.init()
      if (!success) return false
    }

    try {
      const tree = convertToFileSystemTree(files)
      await this.container!.mount(tree)
      this.emitOutput('Files mounted successfully\n')
      return true
    } catch (error: any) {
      this.emitError(`Failed to mount files: ${error.message}`)
      return false
    }
  }

  /**
   * Run npm install
   */
  async installDependencies(): Promise<boolean> {
    if (!this.container) return false

    try {
      this.emitStatus('installing', 'Installing dependencies...')
      this.emitOutput('$ npm install\n')

      const installProcess = await this.container.spawn('npm', ['install'])

      // Stream output
      installProcess.output.pipeTo(
        new WritableStream({
          write: (data) => {
            this.emitOutput(data)
          }
        })
      )

      const exitCode = await installProcess.exit

      if (exitCode !== 0) {
        this.emitError(`npm install failed with exit code ${exitCode}`)
        return false
      }

      this.emitOutput('\nDependencies installed successfully!\n')
      return true
    } catch (error: any) {
      this.emitError(`Install failed: ${error.message}`)
      return false
    }
  }

  /**
   * Start the dev server
   */
  async startDevServer(command: string = 'npm run dev'): Promise<string | null> {
    if (!this.container) return null

    try {
      this.emitStatus('starting', 'Starting development server...')

      const [cmd, ...args] = command.split(' ')
      this.emitOutput(`$ ${command}\n`)

      this.serverProcess = await this.container.spawn(cmd, args)

      // Stream output
      this.serverProcess.output.pipeTo(
        new WritableStream({
          write: (data) => {
            this.emitOutput(data)
          }
        })
      )

      // Listen for server-ready event
      return new Promise((resolve) => {
        this.container!.on('server-ready', (port, url) => {
          console.log(`[WebContainer] Server ready on port ${port}: ${url}`)
          this.currentUrl = url
          this.emitStatus('running', `Server running on port ${port}`)
          this.events.onServerReady?.(url, port)
          resolve(url)
        })

        // Timeout after 60 seconds
        setTimeout(() => {
          if (!this.currentUrl) {
            this.emitError('Server startup timed out')
            resolve(null)
          }
        }, 60000)
      })
    } catch (error: any) {
      this.emitError(`Failed to start server: ${error.message}`)
      return null
    }
  }

  /**
   * Run a complete project (mount, install, start)
   */
  async runProject(files: Record<string, string>): Promise<string | null> {
    // Add missing config files for Vite/TypeScript projects
    const filesToMount = { ...files }

    // Inject error capture script into HTML files for auto-fix support
    const htmlFiles = ['index.html', 'public/index.html', 'src/index.html']
    for (const htmlPath of htmlFiles) {
      if (filesToMount[htmlPath]) {
        console.log('[WebContainer] Injecting error capture script into', htmlPath)
        filesToMount[htmlPath] = injectErrorCaptureScript(filesToMount[htmlPath])
      }
    }

    // Check if this is a Vite project
    const isViteProject = files['vite.config.ts'] || files['vite.config.js'] ||
      (files['package.json'] && files['package.json'].includes('vite'))

    // Add tsconfig.node.json if missing (required by Vite)
    if (isViteProject && !files['tsconfig.node.json']) {
      console.log('[WebContainer] Adding missing tsconfig.node.json')
      filesToMount['tsconfig.node.json'] = JSON.stringify({
        "compilerOptions": {
          "composite": true,
          "skipLibCheck": true,
          "module": "ESNext",
          "moduleResolution": "bundler",
          "allowSyntheticDefaultImports": true,
          "strict": true
        },
        "include": ["vite.config.ts"]
      }, null, 2)
    }

    // Add tsconfig.json if missing
    if (isViteProject && !files['tsconfig.json']) {
      console.log('[WebContainer] Adding missing tsconfig.json')
      filesToMount['tsconfig.json'] = JSON.stringify({
        "compilerOptions": {
          "target": "ES2020",
          "useDefineForClassFields": true,
          "lib": ["ES2020", "DOM", "DOM.Iterable"],
          "module": "ESNext",
          "skipLibCheck": true,
          "moduleResolution": "bundler",
          "allowImportingTsExtensions": true,
          "resolveJsonModule": true,
          "isolatedModules": true,
          "noEmit": true,
          "jsx": "react-jsx",
          "strict": true,
          "noUnusedLocals": false,
          "noUnusedParameters": false,
          "noFallthroughCasesInSwitch": true
        },
        "include": ["src"],
        "references": [{ "path": "./tsconfig.node.json" }]
      }, null, 2)
    }

    // Mount files
    const mounted = await this.mountFiles(filesToMount)
    if (!mounted) return null

    // Check if package.json exists
    if (!filesToMount['package.json']) {
      this.emitError('No package.json found in project')
      return null
    }

    // Install dependencies
    const installed = await this.installDependencies()
    if (!installed) return null

    // Detect the right start command
    const packageJson = JSON.parse(filesToMount['package.json'])
    const scripts = packageJson.scripts || {}

    let startCommand = 'npm run dev'
    if (scripts.dev) {
      startCommand = 'npm run dev'
    } else if (scripts.start) {
      startCommand = 'npm start'
    }

    // Start dev server
    return await this.startDevServer(startCommand)
  }

  /**
   * Write a single file
   */
  async writeFile(path: string, content: string): Promise<boolean> {
    if (!this.container) return false

    try {
      await this.container.fs.writeFile(path, content)
      return true
    } catch (error: any) {
      this.emitError(`Failed to write file ${path}: ${error.message}`)
      return false
    }
  }

  /**
   * Read a file
   */
  async readFile(path: string): Promise<string | null> {
    if (!this.container) return null

    try {
      const content = await this.container.fs.readFile(path, 'utf-8')
      return content
    } catch (error: any) {
      this.emitError(`Failed to read file ${path}: ${error.message}`)
      return null
    }
  }

  /**
   * Kill the running server
   */
  async killServer(): Promise<void> {
    if (this.serverProcess) {
      this.serverProcess.kill()
      this.serverProcess = null
      this.currentUrl = null
      this.emitStatus('ready', 'Server stopped')
    }
  }

  /**
   * Get current server URL
   */
  getServerUrl(): string | null {
    return this.currentUrl
  }

  /**
   * Teardown WebContainer
   */
  async teardown(): Promise<void> {
    await this.killServer()
    this.container = null
    webcontainerInstance = null
    bootPromise = null
    this.emitStatus('idle')
  }
}

/**
 * Error capture script to inject into WebContainer projects
 * This enables auto-fix by capturing runtime errors and sending them to parent
 */
const WEBCONTAINER_ERROR_CAPTURE_SCRIPT = `
<script>
(function() {
  // BharatBuild WebContainer Error Capture
  // Captures runtime errors and sends to parent for auto-fix

  const capturedErrors = new Set();

  // Send error to parent window
  function sendError(type, payload) {
    try {
      window.parent.postMessage({
        type: 'bharatbuild-' + type,
        ...payload,
        source: 'webcontainer'
      }, '*');
    } catch (e) {
      // Parent may not be accessible
    }
  }

  // 1. Global JS errors
  window.onerror = function(message, filename, lineno, colno, error) {
    const msgStr = String(message);
    const errorKey = msgStr.substring(0, 100);
    if (capturedErrors.has(errorKey)) return false;
    capturedErrors.add(errorKey);

    sendError('error', {
      message: msgStr,
      filename: filename,
      lineno: lineno,
      colno: colno,
      stack: error ? error.stack : null
    });
    return false;
  };

  // 2. Unhandled promise rejections
  window.addEventListener('unhandledrejection', function(event) {
    var message = event.reason ? (event.reason.message || String(event.reason)) : 'Unknown rejection';
    console.log('[BharatBuild] Captured unhandled rejection:', message.substring(0, 100));
    sendError('error', {
      message: message,
      filename: null,
      lineno: null,
      colno: null,
      stack: event.reason ? event.reason.stack : null
    });
  });

  // 2b. Error event listener (catches more errors than onerror)
  window.addEventListener('error', function(event) {
    var message = event.message || (event.error ? event.error.message : 'Unknown error');
    var errorKey = String(message).substring(0, 100);
    if (capturedErrors.has(errorKey)) return;
    capturedErrors.add(errorKey);

    console.log('[BharatBuild] Captured error event:', message.substring(0, 100));
    sendError('error', {
      message: message,
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      stack: event.error ? event.error.stack : null
    });
  }, true); // Use capture phase to catch before other handlers

  // 3. Console.error interceptor - CRITICAL for React errors
  // React logs errors to console before showing overlay
  var originalConsoleError = console.error;
  console.error = function() {
    var args = Array.prototype.slice.call(arguments);
    var message = args.map(function(arg) {
      if (arg instanceof Error) {
        return arg.message + (arg.stack ? '\\n' + arg.stack : '');
      }
      try {
        return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
      } catch(e) {
        return String(arg);
      }
    }).join(' ');

    // Check for React/Router specific errors
    var isReactError = message.includes('React') ||
                       message.includes('Router') ||
                       message.includes('render') ||
                       message.includes('component') ||
                       message.includes('Cannot') ||
                       message.includes('Uncaught') ||
                       message.includes('Error:');

    if (isReactError && message.length > 20) {
      console.log('[BharatBuild] Captured console.error (React):', message.substring(0, 100));
      sendError('error', {
        message: message.substring(0, 3000),
        filename: null,
        lineno: null,
        colno: null,
        stack: message,
        source: 'console.error'
      });
    }

    originalConsoleError.apply(console, args);
  };

  // Also intercept console.warn for warnings that might be errors
  var originalConsoleWarn = console.warn;
  console.warn = function() {
    var args = Array.prototype.slice.call(arguments);
    var message = args.join(' ');

    // Check for React warnings that indicate errors
    if (message.includes('Warning:') &&
        (message.includes('Router') || message.includes('cannot') || message.includes('Invalid'))) {
      console.log('[BharatBuild] Captured React warning:', message.substring(0, 100));
      sendError('error', {
        message: message.substring(0, 3000),
        filename: null,
        lineno: null,
        colno: null,
        stack: null,
        source: 'console.warn'
      });
    }

    originalConsoleWarn.apply(console, args);
  };

  // 4. React/Vite Error Overlay detection - CRITICAL for catching React errors
  // React catches errors internally, so window.onerror doesn't fire
  // We need to watch for error overlay elements

  var overlayChecked = false;

  function checkForErrorOverlay() {
    if (overlayChecked) return;

    // 1. Check for Vite error overlay (custom element with shadow DOM)
    var viteOverlay = document.querySelector('vite-error-overlay');
    if (viteOverlay) {
      var text = '';
      var shadowRoot = viteOverlay.shadowRoot;
      if (shadowRoot) {
        // Vite 5 structure - try multiple selectors
        var selectors = [
          '.message-body',
          '.message',
          '.error-message',
          'pre',
          '[class*="message"]',
          '[class*="error"]'
        ];
        for (var i = 0; i < selectors.length; i++) {
          var el = shadowRoot.querySelector(selectors[i]);
          if (el && el.textContent && el.textContent.length > 20) {
            text = el.textContent;
            break;
          }
        }
        if (!text) {
          text = shadowRoot.textContent || '';
        }
      } else {
        text = viteOverlay.textContent || '';
      }

      if (text && text.length > 20) {
        overlayChecked = true;
        console.log('[BharatBuild] Captured Vite error overlay:', text.substring(0, 100));
        sendError('error', {
          message: text.substring(0, 3000),
          filename: null,
          lineno: null,
          colno: null,
          stack: text,
          source: 'vite-overlay'
        });
        return;
      }
    }

    // 2. Check for React error boundary / overlay
    var reactOverlays = document.querySelectorAll(
      '#react-error-overlay, ' +
      '[class*="error-overlay"], ' +
      '[class*="ErrorBoundary"], ' +
      '[class*="react-error"], ' +
      '[data-reactroot] [class*="error"]'
    );
    for (var j = 0; j < reactOverlays.length; j++) {
      var overlay = reactOverlays[j];
      var text = overlay.textContent || '';
      if (text.length > 50 && (text.includes('Error') || text.includes('Cannot'))) {
        overlayChecked = true;
        console.log('[BharatBuild] Captured React error overlay:', text.substring(0, 100));
        sendError('error', {
          message: text.substring(0, 3000),
          filename: null,
          lineno: null,
          colno: null,
          stack: text,
          source: 'react-overlay'
        });
        return;
      }
    }

    // 3. Check full document body for error patterns (last resort)
    var bodyText = document.body ? document.body.innerText : '';
    var errorPatterns = [
      /Error:.*Router.*inside.*Router/i,
      /Cannot.*render.*Router/i,
      /Uncaught Error:/i,
      /Invariant Violation:/i,
      /React error/i
    ];
    for (var k = 0; k < errorPatterns.length; k++) {
      var match = bodyText.match(errorPatterns[k]);
      if (match) {
        // Extract context around the match
        var idx = bodyText.indexOf(match[0]);
        var context = bodyText.substring(Math.max(0, idx - 50), Math.min(bodyText.length, idx + 500));
        if (context.length > 30) {
          overlayChecked = true;
          console.log('[BharatBuild] Captured error from body text:', context.substring(0, 100));
          sendError('error', {
            message: context.substring(0, 3000),
            filename: null,
            lineno: null,
            colno: null,
            stack: context,
            source: 'body-scan'
          });
          return;
        }
      }
    }
  }

  // Poll for error overlays (they may appear after a delay)
  setInterval(checkForErrorOverlay, 500);

  var observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
      mutation.addedNodes.forEach(function(node) {
        if (node.nodeType === 1) {
          // Vite error overlay
          if (node.tagName && node.tagName.toLowerCase() === 'vite-error-overlay') {
            setTimeout(function() {
              var shadowRoot = node.shadowRoot;
              var text = '';
              if (shadowRoot) {
                var messageEl = shadowRoot.querySelector('.message-body') || shadowRoot.querySelector('.message');
                text = messageEl ? messageEl.textContent : (shadowRoot.textContent || '');
              } else {
                text = node.textContent || '';
              }
              if (text && !overlayChecked) {
                overlayChecked = true;
                console.log('[BharatBuild] Captured Vite error overlay (mutation):', text.substring(0, 100));
                sendError('error', {
                  message: text.substring(0, 2000),
                  filename: null,
                  lineno: null,
                  colno: null,
                  stack: text,
                  source: 'vite-overlay'
                });
              }
            }, 200);
          }
          // React error overlay
          if (node.id === 'webpack-dev-server-client-overlay' ||
              node.id === 'react-error-overlay' ||
              (node.className && node.className.includes && node.className.includes('error-overlay'))) {
            var text = node.textContent || node.innerText || '';
            if (text && !overlayChecked) {
              overlayChecked = true;
              console.log('[BharatBuild] Captured React error overlay:', text.substring(0, 100));
              sendError('error', {
                message: text.substring(0, 2000),
                filename: null,
                lineno: null,
                colno: null,
                stack: text,
                source: 'react-overlay'
              });
            }
          }
        }
      });
    });
  });

  // Start observing when DOM is ready
  if (document.body) {
    observer.observe(document.body, { childList: true, subtree: true });
  } else {
    document.addEventListener('DOMContentLoaded', function() {
      observer.observe(document.body, { childList: true, subtree: true });
    });
  }

  // 5. Network error capture (fetch)
  const originalFetch = window.fetch;
  window.fetch = async function(input, init) {
    const url = typeof input === 'string' ? input : input.url;
    const method = (init && init.method) || 'GET';

    try {
      const response = await originalFetch.apply(this, arguments);
      if (!response.ok && response.status >= 400) {
        sendError('network', {
          url: url,
          method: method,
          status: response.status,
          message: 'HTTP ' + response.status + ' ' + response.statusText
        });
      }
      return response;
    } catch (error) {
      sendError('network', {
        url: url,
        method: method,
        status: 0,
        message: error.message || 'Network request failed'
      });
      throw error;
    }
  };

  console.log('[BharatBuild] WebContainer error capture active');
})();
</script>
`;

/**
 * Inject error capture script into HTML content
 */
function injectErrorCaptureScript(html: string): string {
  // Try to inject after <head> tag
  if (html.includes('<head>')) {
    return html.replace('<head>', '<head>' + WEBCONTAINER_ERROR_CAPTURE_SCRIPT)
  }
  // Try to inject after <html> tag
  if (html.includes('<html>')) {
    return html.replace('<html>', '<html><head>' + WEBCONTAINER_ERROR_CAPTURE_SCRIPT + '</head>')
  }
  // Prepend if no head/html found
  return WEBCONTAINER_ERROR_CAPTURE_SCRIPT + html
}

// Export singleton manager for easy use
export const webContainerManager = new WebContainerManager()
