'use client'

import { useEffect, useRef } from 'react'
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

  useEffect(() => {
    if (!terminalRef.current) return

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
        selection: 'rgba(0, 153, 255, 0.3)',
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
    fitAddon.fit()

    // Store refs
    xtermRef.current = terminal
    fitAddonRef.current = fitAddon

    // Welcome message
    terminal.writeln('\x1b[1;36m╔═══════════════════════════════════════════════════╗\x1b[0m')
    terminal.writeln('\x1b[1;36m║\x1b[0m  \x1b[1;33mBharatBuild AI Terminal\x1b[0m                        \x1b[1;36m║\x1b[0m')
    terminal.writeln('\x1b[1;36m║\x1b[0m  Real-time command execution and output          \x1b[1;36m║\x1b[0m')
    terminal.writeln('\x1b[1;36m╚═══════════════════════════════════════════════════╝\x1b[0m')
    terminal.writeln('')
    terminal.write('\x1b[1;32m$\x1b[0m ')

    // Handle input
    let currentLine = ''
    terminal.onData((data) => {
      const code = data.charCodeAt(0)

      // Enter key
      if (code === 13) {
        terminal.writeln('')
        if (currentLine.trim()) {
          onCommand?.(currentLine)
        }
        currentLine = ''
        terminal.write('\x1b[1;32m$\x1b[0m ')
      }
      // Backspace
      else if (code === 127) {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1)
          terminal.write('\b \b')
        }
      }
      // Ctrl+C
      else if (code === 3) {
        terminal.writeln('^C')
        currentLine = ''
        terminal.write('\x1b[1;32m$\x1b[0m ')
      }
      // Ctrl+L (clear)
      else if (code === 12) {
        terminal.clear()
        terminal.write('\x1b[1;32m$\x1b[0m ')
      }
      // Printable characters
      else if (code >= 32) {
        currentLine += data
        terminal.write(data)
      }
    })

    // Handle resize
    const handleResize = () => {
      fitAddon.fit()
    }
    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      terminal.dispose()
    }
  }, [onCommand])

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

  // Re-fit on mount and when container size changes
  useEffect(() => {
    const resizeObserver = new ResizeObserver(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
      }
    })

    if (terminalRef.current) {
      resizeObserver.observe(terminalRef.current)
    }

    return () => {
      resizeObserver.disconnect()
    }
  }, [])

  return (
    <div
      ref={terminalRef}
      className="h-full w-full"
      style={{ padding: '8px' }}
    />
  )
}
