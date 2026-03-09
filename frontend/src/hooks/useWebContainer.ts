/**
 * React Hook for WebContainer
 * ===========================
 * Easy-to-use hook for running Node.js projects in the browser
 */

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  WebContainerManager,
  WebContainerStatus,
  isWebContainerSupported
} from '@/lib/webcontainer'

export interface UseWebContainerOptions {
  autoInit?: boolean
}

export interface UseWebContainerReturn {
  // State
  status: WebContainerStatus
  message: string
  output: string[]
  serverUrl: string | null
  isSupported: boolean
  isReady: boolean
  isRunning: boolean

  // Actions
  init: () => Promise<boolean>
  runProject: (files: Record<string, string>) => Promise<string | null>
  mountFiles: (files: Record<string, string>) => Promise<boolean>
  installDependencies: () => Promise<boolean>
  startDevServer: (command?: string) => Promise<string | null>
  writeFile: (path: string, content: string) => Promise<boolean>
  stopServer: () => Promise<void>
  clearOutput: () => void
  teardown: () => Promise<void>
}

export function useWebContainer(options: UseWebContainerOptions = {}): UseWebContainerReturn {
  const { autoInit = false } = options

  const [status, setStatus] = useState<WebContainerStatus>('idle')
  const [message, setMessage] = useState('')
  const [output, setOutput] = useState<string[]>([])
  const [serverUrl, setServerUrl] = useState<string | null>(null)
  const [isSupported] = useState(() => isWebContainerSupported())

  const managerRef = useRef<WebContainerManager | null>(null)

  // Initialize manager with event handlers
  useEffect(() => {
    managerRef.current = new WebContainerManager({
      onStatusChange: (newStatus, msg) => {
        setStatus(newStatus)
        if (msg) setMessage(msg)
      },
      onOutput: (data) => {
        setOutput((prev) => [...prev, data])
      },
      onError: (error) => {
        setOutput((prev) => [...prev, `ERROR: ${error}\n`])
      },
      onServerReady: (url) => {
        setServerUrl(url)
      }
    })

    // Auto-init if requested
    if (autoInit && isSupported) {
      managerRef.current.init()
    }

    return () => {
      managerRef.current?.teardown()
    }
  }, [autoInit, isSupported])

  // Init WebContainer
  const init = useCallback(async (): Promise<boolean> => {
    if (!managerRef.current) return false
    return managerRef.current.init()
  }, [])

  // Run complete project
  const runProject = useCallback(async (files: Record<string, string>): Promise<string | null> => {
    if (!managerRef.current) return null
    setOutput([]) // Clear previous output
    return managerRef.current.runProject(files)
  }, [])

  // Mount files only
  const mountFiles = useCallback(async (files: Record<string, string>): Promise<boolean> => {
    if (!managerRef.current) return false
    return managerRef.current.mountFiles(files)
  }, [])

  // Install dependencies
  const installDependencies = useCallback(async (): Promise<boolean> => {
    if (!managerRef.current) return false
    return managerRef.current.installDependencies()
  }, [])

  // Start dev server
  const startDevServer = useCallback(async (command?: string): Promise<string | null> => {
    if (!managerRef.current) return null
    return managerRef.current.startDevServer(command)
  }, [])

  // Write single file
  const writeFile = useCallback(async (path: string, content: string): Promise<boolean> => {
    if (!managerRef.current) return false
    return managerRef.current.writeFile(path, content)
  }, [])

  // Stop server
  const stopServer = useCallback(async (): Promise<void> => {
    if (!managerRef.current) return
    await managerRef.current.killServer()
    setServerUrl(null)
  }, [])

  // Clear output
  const clearOutput = useCallback(() => {
    setOutput([])
  }, [])

  // Teardown
  const teardown = useCallback(async (): Promise<void> => {
    if (!managerRef.current) return
    await managerRef.current.teardown()
    setServerUrl(null)
    setStatus('idle')
    setMessage('')
  }, [])

  return {
    // State
    status,
    message,
    output,
    serverUrl,
    isSupported,
    isReady: status === 'ready' || status === 'running',
    isRunning: status === 'running',

    // Actions
    init,
    runProject,
    mountFiles,
    installDependencies,
    startDevServer,
    writeFile,
    stopServer,
    clearOutput,
    teardown
  }
}

export default useWebContainer
