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

// Export singleton manager for easy use
export const webContainerManager = new WebContainerManager()
