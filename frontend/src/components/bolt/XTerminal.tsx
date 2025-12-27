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

    // Initialize xterm.js with improved styling
    const terminal = new Terminal({
      cursorBlink: true,
      cursorStyle: 'bar',
      fontSize: 13,
      fontFamily: '"JetBrains Mono", "Fira Code", "Cascadia Code", "Consolas", monospace',
      fontWeight: '400',
      fontWeightBold: '600',
      letterSpacing: 0.5,
      lineHeight: 1.4,
      theme: {
        background: '#0d1117',
        foreground: '#c9d1d9',
        cursor: '#58a6ff',
        cursorAccent: '#0d1117',
        selectionBackground: 'rgba(56, 139, 253, 0.4)',
        selectionForeground: '#ffffff',
        black: '#484f58',
        red: '#ff7b72',
        green: '#7ee787',
        yellow: '#d29922',
        blue: '#58a6ff',
        magenta: '#bc8cff',
        cyan: '#39c5cf',
        white: '#b1bac4',
        brightBlack: '#6e7681',
        brightRed: '#ffa198',
        brightGreen: '#a5d6a7',
        brightYellow: '#e3b341',
        brightBlue: '#79c0ff',
        brightMagenta: '#d2a8ff',
        brightCyan: '#56d4dd',
        brightWhite: '#f0f6fc',
      },
      scrollback: 5000,
      convertEol: true,
      allowProposedApi: true,
      smoothScrollDuration: 150,
      fastScrollModifier: 'alt',
      scrollSensitivity: 3,
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

    // Welcome message - Clean and modern
    terminal.writeln('')
    terminal.writeln('\x1b[38;5;39m  ██████╗ ██╗  ██╗ █████╗ ██████╗  █████╗ ████████╗\x1b[0m')
    terminal.writeln('\x1b[38;5;39m  ██╔══██╗██║  ██║██╔══██╗██╔══██╗██╔══██╗╚══██╔══╝\x1b[0m')
    terminal.writeln('\x1b[38;5;45m  ██████╔╝███████║███████║██████╔╝███████║   ██║\x1b[0m')
    terminal.writeln('\x1b[38;5;45m  ██╔══██╗██╔══██║██╔══██║██╔══██╗██╔══██║   ██║\x1b[0m')
    terminal.writeln('\x1b[38;5;51m  ██████╔╝██║  ██║██║  ██║██║  ██║██║  ██║   ██║\x1b[0m')
    terminal.writeln('\x1b[38;5;51m  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝\x1b[0m')
    terminal.writeln('')
    terminal.writeln('\x1b[38;5;245m  ─────────────────────────────────────────────────\x1b[0m')
    terminal.writeln('\x1b[38;5;250m  BharatBuild AI Terminal\x1b[0m \x1b[38;5;239m│\x1b[0m \x1b[38;5;114mReady\x1b[0m')
    terminal.writeln('\x1b[38;5;245m  ─────────────────────────────────────────────────\x1b[0m')
    terminal.writeln('')
    terminal.writeln('\x1b[38;5;239m  Tips: \x1b[38;5;250mCtrl+C\x1b[38;5;239m copy • \x1b[38;5;250mCtrl+L\x1b[38;5;239m clear • \x1b[38;5;250mRight-click\x1b[38;5;239m menu\x1b[0m')
    terminal.writeln('')
    terminal.write('\x1b[38;5;114m❯\x1b[0m ')

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
        terminal.write('\x1b[38;5;114m❯\x1b[0m ')
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
          terminal.writeln('\x1b[38;5;245m^C\x1b[0m')
          currentLineRef.current = ''
          terminal.write('\x1b[38;5;114m❯\x1b[0m ')
        }
      }
      // Ctrl+L (clear)
      else if (code === 12) {
        terminal.clear()
        terminal.write('\x1b[38;5;114m❯\x1b[0m ')
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

  // Handle new logs with improved formatting
  useEffect(() => {
    if (!xtermRef.current || logs.length === 0) return

    // Only process new logs
    const newLogs = logs.slice(lastLogCountRef.current)
    lastLogCountRef.current = logs.length

    newLogs.forEach((log) => {
      const terminal = xtermRef.current!
      const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })

      switch (log.type) {
        case 'command':
          // Show command with styled prompt and timestamp
          terminal.writeln(`\x1b[38;5;239m${timestamp}\x1b[0m \x1b[38;5;114m❯\x1b[0m \x1b[38;5;79m${log.content}\x1b[0m`)
          break

        case 'error':
          // Show errors with red icon and styled text
          terminal.writeln(`\x1b[38;5;239m${timestamp}\x1b[0m \x1b[38;5;196m✖\x1b[0m \x1b[38;5;210m${log.content}\x1b[0m`)
          break

        case 'info':
          // Show info with blue icon
          terminal.writeln(`\x1b[38;5;239m${timestamp}\x1b[0m \x1b[38;5;39mℹ\x1b[0m \x1b[38;5;153m${log.content}\x1b[0m`)
          break

        case 'output':
          // Show output with subtle styling
          const lines = log.content.split('\n')
          lines.forEach(line => {
            if (line.trim()) {
              // Detect success patterns
              if (line.includes('✓') || line.toLowerCase().includes('success') || line.toLowerCase().includes('completed')) {
                terminal.writeln(`  \x1b[38;5;114m${line}\x1b[0m`)
              }
              // Detect warning patterns
              else if (line.toLowerCase().includes('warn') || line.includes('⚠')) {
                terminal.writeln(`  \x1b[38;5;220m${line}\x1b[0m`)
              }
              // Detect error patterns in output
              else if (line.toLowerCase().includes('error') || line.toLowerCase().includes('fail')) {
                terminal.writeln(`  \x1b[38;5;210m${line}\x1b[0m`)
              }
              // URLs
              else if (line.includes('http://') || line.includes('https://')) {
                terminal.writeln(`  \x1b[38;5;75m${line}\x1b[0m`)
              }
              // Default output
              else {
                terminal.writeln(`  \x1b[38;5;250m${line}\x1b[0m`)
              }
            }
          })
          break

        default:
          terminal.writeln(`  \x1b[38;5;245m${log.content}\x1b[0m`)
      }
    })

    // Add prompt after logs and scroll to bottom
    if (newLogs.length > 0 && xtermRef.current) {
      xtermRef.current.writeln('')
      xtermRef.current.write('\x1b[38;5;114m❯\x1b[0m ')
      // Auto-scroll to bottom after new logs
      xtermRef.current.scrollToBottom()
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

  // Handle wheel events for scrolling
  const handleWheel = useCallback((e: React.WheelEvent) => {
    if (xtermRef.current) {
      // Let xterm handle the scroll
      const scrollAmount = e.deltaY > 0 ? 3 : -3
      xtermRef.current.scrollLines(scrollAmount)
    }
  }, [])

  return (
    <div className="relative h-full w-full bg-[#0d1117]" onWheel={handleWheel}>
      <div
        ref={terminalRef}
        className="h-full w-full"
        style={{ padding: '12px 16px' }}
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
