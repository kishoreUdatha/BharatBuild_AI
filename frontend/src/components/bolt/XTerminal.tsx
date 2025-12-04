'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import '@xterm/xterm/css/xterm.css'

interface XTerminalProps {
  logs?: Array<{
    id: string
    type: 'command' | 'output' | 'error' | 'info'
    content: string
  }>
  onCommand?: (command: string) => void
}

export function XTerminal({ logs = [], onCommand }: XTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const currentLineRef = useRef<string>('')
  const lastLogCountRef = useRef<number>(0)
  const onCommandRef = useRef(onCommand)
  const isInitializedRef = useRef(false)
  const fitTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Context menu state for copy
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number } | null>(null)

  // Copy selected text to clipboard
  const copyToClipboard = useCallback(async () => {
    if (!xtermRef.current) return

    const selection = xtermRef.current.getSelection()
    if (selection) {
      try {
        await navigator.clipboard.writeText(selection)
        // Visual feedback - briefly show copied message
        console.log('[XTerminal] Copied to clipboard:', selection.substring(0, 50) + '...')
      } catch (err) {
        console.error('[XTerminal] Failed to copy:', err)
      }
    }
    setContextMenu(null)
  }, [])

  // Handle right-click context menu
  const handleContextMenu = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const selection = xtermRef.current?.getSelection()
    if (selection) {
      setContextMenu({ x: e.clientX, y: e.clientY })
    }
  }, [])

  // Close context menu on click outside
  useEffect(() => {
    const handleClick = () => setContextMenu(null)
    if (contextMenu) {
      document.addEventListener('click', handleClick)
      return () => document.removeEventListener('click', handleClick)
    }
  }, [contextMenu])

  // Keep onCommand ref updated without causing re-render
  useEffect(() => {
    onCommandRef.current = onCommand
  }, [onCommand])

  // Debounced fit function to prevent blinking
  const debouncedFit = useCallback(() => {
    if (fitTimeoutRef.current) {
      clearTimeout(fitTimeoutRef.current)
    }
    fitTimeoutRef.current = setTimeout(() => {
      try {
        if (fitAddonRef.current && xtermRef.current) {
          fitAddonRef.current.fit()
        }
      } catch (error) {
        // Silently ignore fit errors
      }
    }, 100)
  }, [])

  // Initialize terminal only once
  useEffect(() => {
    // Guard: Don't initialize if ref is missing or already initialized
    if (!terminalRef.current) {
      console.log('[XTerminal] Container ref not ready')
      return
    }

    if (isInitializedRef.current && xtermRef.current) {
      console.log('[XTerminal] Already initialized, skipping')
      return
    }

    console.log('[XTerminal] Initializing terminal...')
    isInitializedRef.current = true

    // Initialize xterm.js
    const terminal = new Terminal({
      cursorBlink: true,
      cursorStyle: 'block',
      fontSize: 14,
      fontFamily: '"Fira Code", "Consolas", "Monaco", "Courier New", monospace',
      theme: {
        background: '#1a1d23',
        foreground: '#e4e6eb',
        cursor: '#0099ff',
        cursorAccent: '#ffffff',
        selectionBackground: 'rgba(0, 153, 255, 0.3)',
        black: '#1a1d23',
        red: '#f87171',
        green: '#4ade80',
        yellow: '#facc15',
        blue: '#60a5fa',
        magenta: '#c084fc',
        cyan: '#22d3ee',
        white: '#e4e6eb',
        brightBlack: '#6b7280',
        brightRed: '#fca5a5',
        brightGreen: '#86efac',
        brightYellow: '#fde047',
        brightBlue: '#93c5fd',
        brightMagenta: '#d8b4fe',
        brightCyan: '#67e8f9',
        brightWhite: '#f3f4f6',
      },
      scrollback: 1000,
      convertEol: true,
      allowProposedApi: true,
    })

    // Add addons
    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()

    terminal.loadAddon(fitAddon)
    terminal.loadAddon(webLinksAddon)

    // Open terminal
    terminal.open(terminalRef.current)

    // Store refs
    xtermRef.current = terminal
    fitAddonRef.current = fitAddon

    // Fit after a small delay to ensure DOM is ready
    setTimeout(() => {
      try {
        fitAddon.fit()
      } catch (error) {
        // Silently ignore
      }
    }, 50)

    // Welcome message
    terminal.writeln('\x1b[1;36m╔═══════════════════════════════════════════════════╗\x1b[0m')
    terminal.writeln('\x1b[1;36m║\x1b[0m  \x1b[1;33mBharatBuild AI Terminal\x1b[0m                        \x1b[1;36m║\x1b[0m')
    terminal.writeln('\x1b[1;36m║\x1b[0m  Real-time command execution and output          \x1b[1;36m║\x1b[0m')
    terminal.writeln('\x1b[1;36m╚═══════════════════════════════════════════════════╝\x1b[0m')
    terminal.writeln('')
    terminal.write('\x1b[1;32m$\x1b[0m ')

    // Handle input - use ref for onCommand to avoid re-initialization
    terminal.onData((data) => {
      const code = data.charCodeAt(0)

      // Enter key
      if (code === 13) {
        terminal.writeln('')
        if (currentLineRef.current.trim()) {
          onCommandRef.current?.(currentLineRef.current)
        }
        currentLineRef.current = ''
        terminal.write('\x1b[1;32m$\x1b[0m ')
      }
      // Backspace
      else if (code === 127) {
        if (currentLineRef.current.length > 0) {
          currentLineRef.current = currentLineRef.current.slice(0, -1)
          terminal.write('\b \b')
        }
      }
      // Ctrl+C - If there's a selection, copy it; otherwise send interrupt
      else if (code === 3) {
        const selection = terminal.getSelection()
        if (selection) {
          navigator.clipboard.writeText(selection).then(() => {
            console.log('[XTerminal] Copied with Ctrl+C')
          }).catch(err => {
            console.error('[XTerminal] Copy failed:', err)
          })
        } else {
          terminal.writeln('^C')
          currentLineRef.current = ''
          terminal.write('\x1b[1;32m$\x1b[0m ')
        }
      }
      // Ctrl+L (clear)
      else if (code === 12) {
        terminal.clear()
        terminal.write('\x1b[1;32m$\x1b[0m ')
      }
      // Printable characters
      else if (code >= 32) {
        currentLineRef.current += data
        terminal.write(data)
      }
    })

    // Add keyboard handler for Ctrl+Shift+C (copy)
    terminal.attachCustomKeyEventHandler((event) => {
      // Ctrl+Shift+C to copy
      if (event.ctrlKey && event.shiftKey && event.key === 'C') {
        const selection = terminal.getSelection()
        if (selection) {
          navigator.clipboard.writeText(selection).then(() => {
            console.log('[XTerminal] Copied with Ctrl+Shift+C')
          }).catch(err => {
            console.error('[XTerminal] Copy failed:', err)
          })
        }
        return false // Prevent default
      }
      // Ctrl+Shift+V to paste
      if (event.ctrlKey && event.shiftKey && event.key === 'V') {
        navigator.clipboard.readText().then(text => {
          terminal.write(text)
          currentLineRef.current += text
        }).catch(err => {
          console.error('[XTerminal] Paste failed:', err)
        })
        return false // Prevent default
      }
      return true // Allow other keys
    })

    // Cleanup
    return () => {
      console.log('[XTerminal] Cleanup - disposing terminal')
      if (fitTimeoutRef.current) {
        clearTimeout(fitTimeoutRef.current)
      }
      try {
        terminal.dispose()
      } catch (e) {
        console.log('[XTerminal] Error disposing terminal:', e)
      }
      xtermRef.current = null
      fitAddonRef.current = null
      isInitializedRef.current = false
    }
  }, []) // Empty dependency - initialize only once

  // Handle new logs
  useEffect(() => {
    if (!xtermRef.current || logs.length === 0) return

    // Only process new logs
    const newLogs = logs.slice(lastLogCountRef.current)
    lastLogCountRef.current = logs.length

    newLogs.forEach((log) => {
      const terminal = xtermRef.current!

      switch (log.type) {
        case 'command':
          // Show command in green with $ prompt
          terminal.writeln(`\x1b[1;32m$ ${log.content}\x1b[0m`)
          break

        case 'error':
          // Show errors in red
          terminal.writeln(`\x1b[1;31m${log.content}\x1b[0m`)
          break

        case 'info':
          // Show info in cyan
          terminal.writeln(`\x1b[1;36m${log.content}\x1b[0m`)
          break

        case 'output':
          // Show output in default color
          terminal.writeln(log.content)
          break

        default:
          terminal.writeln(log.content)
      }
    })

    // Add prompt after logs
    if (newLogs.length > 0) {
      xtermRef.current.write('\x1b[1;32m$\x1b[0m ')
    }
  }, [logs])

  // Re-fit on container size changes with debouncing
  useEffect(() => {
    const resizeObserver = new ResizeObserver(() => {
      debouncedFit()
    })

    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current)
    }

    // Also handle window resize with debounce
    const handleWindowResize = () => {
      debouncedFit()
    }
    window.addEventListener('resize', handleWindowResize)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', handleWindowResize)
    }
  }, [debouncedFit])

  return (
    <div className="relative h-full w-full">
      <div
        ref={terminalRef}
        className="h-full w-full"
        style={{ padding: '8px' }}
        onContextMenu={handleContextMenu}
      />

      {/* Context Menu for Copy */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-[#2d2d2d] border border-[#555] rounded shadow-lg py-1 min-w-[120px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={copyToClipboard}
            className="w-full px-3 py-1.5 text-left text-sm text-white hover:bg-[#3d3d3d] flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Copy
          </button>
        </div>
      )}
    </div>
  )
}

export default XTerminal
