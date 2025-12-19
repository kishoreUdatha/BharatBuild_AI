'use client'

import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import {
  Terminal as TerminalIcon,
  X,
  Minimize2,
  Maximize2,
  Copy,
  Trash2,
  Search,
  ChevronUp,
  ChevronDown,
  ArrowDown,
  CheckCircle,
  XCircle,
  AlertCircle,
  Wrench,
  Loader2
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/store/projectStore'
import { useErrorStore } from '@/store/errorStore'
import { sdkService } from '@/services/sdkService'

interface TerminalLine {
  id: string
  content: string
  type: 'command' | 'output' | 'error' | 'success' | 'info' | 'warning'
  timestamp?: Date
}

interface TerminalProps {
  commands?: string[]
  output?: string[]
  onClose?: () => void
  isOpen?: boolean
  title?: string
  showTimestamps?: boolean
  onAutoFix?: (result: { success: boolean; files_modified: string[]; message: string }) => void
}

// ANSI color codes to CSS classes
const ansiToClass: Record<string, string> = {
  '30': 'text-gray-800',
  '31': 'text-red-500',
  '32': 'text-green-500',
  '33': 'text-yellow-500',
  '34': 'text-blue-500',
  '35': 'text-purple-500',
  '36': 'text-cyan-500',
  '37': 'text-white',
  '90': 'text-gray-500',
  '91': 'text-red-400',
  '92': 'text-green-400',
  '93': 'text-yellow-400',
  '94': 'text-blue-400',
  '95': 'text-purple-400',
  '96': 'text-cyan-400',
  '97': 'text-gray-100',
  '1': 'font-bold',
  '0': '',
}

// Parse ANSI escape codes and convert to styled spans
function parseAnsiToReact(text: string): React.ReactNode[] {
  const ansiRegex = /\x1b\[([0-9;]+)m/g
  const parts: React.ReactNode[] = []
  let lastIndex = 0
  let currentClasses: string[] = []
  let match

  while ((match = ansiRegex.exec(text)) !== null) {
    // Add text before this escape code
    if (match.index > lastIndex) {
      const textContent = text.slice(lastIndex, match.index)
      if (textContent) {
        parts.push(
          <span key={parts.length} className={currentClasses.join(' ')}>
            {textContent}
          </span>
        )
      }
    }

    // Parse the codes
    const codes = match[1].split(';')
    codes.forEach(code => {
      if (code === '0') {
        currentClasses = []
      } else if (ansiToClass[code]) {
        currentClasses.push(ansiToClass[code])
      }
    })

    lastIndex = match.index + match[0].length
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(
      <span key={parts.length} className={currentClasses.join(' ')}>
        {text.slice(lastIndex)}
      </span>
    )
  }

  return parts.length > 0 ? parts : [text]
}

// Detect line type based on content
function detectLineType(content: string): TerminalLine['type'] {
  const lowerContent = content.toLowerCase()

  // Error patterns
  if (
    lowerContent.includes('error') ||
    lowerContent.includes('failed') ||
    lowerContent.includes('exception') ||
    lowerContent.includes('traceback') ||
    content.includes('ERR!') ||
    content.includes('ENOENT') ||
    content.includes('EACCES')
  ) {
    return 'error'
  }

  // Success patterns
  if (
    lowerContent.includes('success') ||
    lowerContent.includes('done') ||
    lowerContent.includes('completed') ||
    lowerContent.includes('ready') ||
    content.includes('[OK]') ||
    content.includes('✓') ||
    content.includes('✔')
  ) {
    return 'success'
  }

  // Warning patterns
  if (
    lowerContent.includes('warning') ||
    lowerContent.includes('warn') ||
    lowerContent.includes('deprecated')
  ) {
    return 'warning'
  }

  // Command patterns (starts with $)
  if (content.trim().startsWith('$')) {
    return 'command'
  }

  // Info patterns
  if (
    lowerContent.includes('info') ||
    lowerContent.includes('installing') ||
    lowerContent.includes('building') ||
    lowerContent.includes('compiling')
  ) {
    return 'info'
  }

  return 'output'
}

export function Terminal({
  commands = [],
  output = [],
  onClose,
  isOpen = true,
  title = 'Terminal',
  showTimestamps = false,
  onAutoFix
}: TerminalProps) {
  const [isMinimized, setIsMinimized] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showSearch, setShowSearch] = useState(false)
  const [autoScroll, setAutoScroll] = useState(true)
  const [copied, setCopied] = useState(false)
  const [height, setHeight] = useState(300)
  const [isResizing, setIsResizing] = useState(false)
  const [isFixing, setIsFixing] = useState(false)

  const terminalRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)
  const resizeStartY = useRef(0)
  const resizeStartHeight = useRef(0)

  // Stores for Auto Fix
  const projectStore = useProjectStore()
  const errorStore = useErrorStore()

  // Convert output array to terminal lines with types
  const lines = useMemo<TerminalLine[]>(() => {
    const allLines: TerminalLine[] = []

    // Add commands first
    commands.forEach((cmd, index) => {
      allLines.push({
        id: `cmd-${index}`,
        content: `$ ${cmd}`,
        type: 'command',
        timestamp: new Date()
      })
    })

    // Add output lines
    output.forEach((line, index) => {
      allLines.push({
        id: `out-${index}`,
        content: line,
        type: detectLineType(line),
        timestamp: new Date()
      })
    })

    return allLines
  }, [commands, output])

  // Filter lines based on search
  const filteredLines = useMemo(() => {
    if (!searchQuery.trim()) return lines
    return lines.filter(line =>
      line.content.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [lines, searchQuery])

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && terminalRef.current && !isMinimized) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
    }
  }, [lines, autoScroll, isMinimized])

  // Handle scroll - disable auto-scroll when user scrolls up
  const handleScroll = useCallback(() => {
    if (!terminalRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = terminalRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    setAutoScroll(isAtBottom)
  }, [])

  // Copy all content to clipboard
  const copyToClipboard = useCallback(async () => {
    const text = lines.map(l => l.content).join('\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [lines])

  // Clear terminal
  const clearTerminal = useCallback(() => {
    // This would need to be handled by parent component
    console.log('[Terminal] Clear requested')
  }, [])

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight
      setAutoScroll(true)
    }
  }, [])

  // Toggle search
  const toggleSearch = useCallback(() => {
    setShowSearch(prev => !prev)
    if (!showSearch) {
      setTimeout(() => searchInputRef.current?.focus(), 100)
    }
  }, [showSearch])

  // Auto Fix - Uses SDK Fixer to automatically fix errors
  const handleAutoFix = useCallback(async () => {
    const projectId = projectStore.currentProject?.id
    if (!projectId) {
      console.warn('[Terminal] No project selected for auto-fix')
      return
    }

    setIsFixing(true)

    try {
      // Collect errors from error store
      const unresolvedErrors = errorStore.getUnresolvedErrors()

      // Build error message from terminal output and error store
      const errorLines = lines
        .filter(l => l.type === 'error')
        .map(l => l.content)
        .join('\n')

      const errorStoreErrors = unresolvedErrors
        .map(e => `${e.source}: ${e.message}${e.file ? ` (${e.file}:${e.line})` : ''}`)
        .join('\n')

      const combinedErrors = [errorLines, errorStoreErrors].filter(Boolean).join('\n\n')

      if (!combinedErrors.trim()) {
        console.log('[Terminal] No errors to fix')
        setIsFixing(false)
        return
      }

      // Get stack traces
      const stackTrace = unresolvedErrors
        .filter(e => e.stack)
        .map(e => e.stack)
        .join('\n---\n')

      // Call SDK Fixer
      const result = await sdkService.fixError({
        project_id: projectId,
        error_message: combinedErrors,
        stack_trace: stackTrace,
        build_command: 'npm run build',
        max_retries: 3
      })

      console.log('[Terminal] Auto-fix result:', result)

      // Callback to parent
      onAutoFix?.({
        success: result.success && result.error_fixed,
        files_modified: result.files_modified,
        message: result.message
      })

      // Clear errors if fixed
      if (result.success && result.error_fixed) {
        errorStore.clearErrors()
      }

    } catch (error: any) {
      console.error('[Terminal] Auto-fix error:', error)
      onAutoFix?.({
        success: false,
        files_modified: [],
        message: error.message || 'Auto-fix failed'
      })
    } finally {
      setIsFixing(false)
    }
  }, [projectStore.currentProject?.id, errorStore, lines, onAutoFix])

  // Check if there are errors to fix
  const hasErrors = useMemo(() => {
    return lines.some(l => l.type === 'error') || errorStore.getUnresolvedErrors().length > 0
  }, [lines, errorStore])

  // Handle resize
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
    resizeStartY.current = e.clientY
    resizeStartHeight.current = height
  }, [height])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const delta = resizeStartY.current - e.clientY
      const newHeight = Math.max(150, Math.min(600, resizeStartHeight.current + delta))
      setHeight(newHeight)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+F to search
      if (e.ctrlKey && e.key === 'f') {
        e.preventDefault()
        toggleSearch()
      }
      // Escape to close search
      if (e.key === 'Escape' && showSearch) {
        setShowSearch(false)
        setSearchQuery('')
      }
      // Ctrl+L to clear
      if (e.ctrlKey && e.key === 'l') {
        e.preventDefault()
        clearTerminal()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggleSearch, showSearch, clearTerminal])

  // Get line icon and color
  const getLineStyle = (type: TerminalLine['type']) => {
    switch (type) {
      case 'command':
        return { color: 'text-green-400', icon: null, bg: 'bg-green-500/5' }
      case 'error':
        return { color: 'text-red-400', icon: <XCircle className="w-3 h-3" />, bg: 'bg-red-500/10' }
      case 'success':
        return { color: 'text-green-400', icon: <CheckCircle className="w-3 h-3" />, bg: 'bg-green-500/10' }
      case 'warning':
        return { color: 'text-yellow-400', icon: <AlertCircle className="w-3 h-3" />, bg: 'bg-yellow-500/10' }
      case 'info':
        return { color: 'text-blue-400', icon: null, bg: '' }
      default:
        return { color: 'text-gray-300', icon: null, bg: '' }
    }
  }

  if (!isOpen || (commands.length === 0 && output.length === 0)) {
    return null
  }

  const terminalHeight = isFullscreen ? '100vh' : isMinimized ? '48px' : `${height}px`

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 bg-[#1a1d23] border-t border-gray-800 transition-all duration-200 ${
        isFullscreen ? 'z-[100]' : 'z-50'
      }`}
      style={{
        height: terminalHeight,
        boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.5)'
      }}
    >
      {/* Resize Handle */}
      {!isMinimized && !isFullscreen && (
        <div
          className="absolute top-0 left-0 right-0 h-1 cursor-ns-resize bg-transparent hover:bg-blue-500/50 transition-colors"
          onMouseDown={handleResizeStart}
        />
      )}

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800 bg-[#1e2128] select-none">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <TerminalIcon className="w-4 h-4 text-green-400" />
            <span className="text-sm font-medium text-gray-200">{title}</span>
          </div>

          {/* Status indicator */}
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-xs text-gray-500">{lines.length} lines</span>
          </div>

          {/* Auto-scroll indicator */}
          {!autoScroll && (
            <Button
              variant="ghost"
              size="sm"
              onClick={scrollToBottom}
              className="h-6 px-2 text-xs bg-blue-500/20 hover:bg-blue-500/30 text-blue-400"
            >
              <ArrowDown className="w-3 h-3 mr-1" />
              Scroll to bottom
            </Button>
          )}
        </div>

        <div className="flex items-center gap-1">
          {/* Auto Fix Button - Only show when there are errors */}
          {hasErrors && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleAutoFix}
              disabled={isFixing}
              className={`h-7 px-2 text-xs ${
                isFixing
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300'
              }`}
              title="Auto-fix errors using SDK"
            >
              {isFixing ? (
                <>
                  <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  Fixing...
                </>
              ) : (
                <>
                  <Wrench className="w-3 h-3 mr-1" />
                  Auto Fix
                </>
              )}
            </Button>
          )}

          {/* Search */}
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleSearch}
            className={`h-7 w-7 p-0 ${showSearch ? 'bg-blue-500/20 text-blue-400' : 'text-gray-400 hover:text-gray-200'}`}
            title="Search (Ctrl+F)"
          >
            <Search className="w-3.5 h-3.5" />
          </Button>

          {/* Copy */}
          <Button
            variant="ghost"
            size="sm"
            onClick={copyToClipboard}
            className={`h-7 w-7 p-0 ${copied ? 'text-green-400' : 'text-gray-400 hover:text-gray-200'}`}
            title="Copy all"
          >
            {copied ? <CheckCircle className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          </Button>

          {/* Clear */}
          <Button
            variant="ghost"
            size="sm"
            onClick={clearTerminal}
            className="h-7 w-7 p-0 text-gray-400 hover:text-gray-200"
            title="Clear (Ctrl+L)"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>

          {/* Divider */}
          <div className="w-px h-4 bg-gray-700 mx-1" />

          {/* Minimize */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsMinimized(!isMinimized)}
            className="h-7 w-7 p-0 text-gray-400 hover:text-gray-200"
            title={isMinimized ? 'Expand' : 'Minimize'}
          >
            {isMinimized ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </Button>

          {/* Fullscreen */}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="h-7 w-7 p-0 text-gray-400 hover:text-gray-200"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </Button>

          {/* Close */}
          {onClose && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 w-7 p-0 text-gray-400 hover:text-red-400"
              title="Close"
            >
              <X className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      {/* Search Bar */}
      {showSearch && !isMinimized && (
        <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-800 bg-[#1e2128]">
          <Search className="w-4 h-4 text-gray-500" />
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search terminal output..."
            className="flex-1 bg-transparent text-sm text-gray-200 placeholder-gray-500 outline-none"
          />
          <span className="text-xs text-gray-500">
            {searchQuery ? `${filteredLines.length} matches` : ''}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => { setShowSearch(false); setSearchQuery('') }}
            className="h-6 w-6 p-0 text-gray-400 hover:text-gray-200"
          >
            <X className="w-3 h-3" />
          </Button>
        </div>
      )}

      {/* Terminal Content */}
      {!isMinimized && (
        <div
          ref={terminalRef}
          onScroll={handleScroll}
          className="h-[calc(100%-48px)] overflow-y-auto overflow-x-hidden font-mono text-sm"
          style={{
            background: 'linear-gradient(to bottom, #1a1d23 0%, #16181d 100%)',
            scrollBehavior: 'smooth'
          }}
        >
          <div className="p-4 space-y-0.5">
            {filteredLines.map((line) => {
              const style = getLineStyle(line.type)
              return (
                <div
                  key={line.id}
                  className={`flex items-start gap-2 py-0.5 px-2 -mx-2 rounded ${style.bg} hover:bg-white/5 transition-colors group`}
                >
                  {/* Line icon */}
                  {style.icon && (
                    <span className={`mt-0.5 flex-shrink-0 ${style.color}`}>
                      {style.icon}
                    </span>
                  )}

                  {/* Command prompt */}
                  {line.type === 'command' && (
                    <span className="text-green-400 flex-shrink-0">$</span>
                  )}

                  {/* Content */}
                  <span className={`${style.color} break-all whitespace-pre-wrap`}>
                    {line.type === 'command'
                      ? line.content.slice(2) // Remove "$ " prefix
                      : parseAnsiToReact(line.content)
                    }
                  </span>

                  {/* Timestamp on hover */}
                  {showTimestamps && line.timestamp && (
                    <span className="ml-auto text-xs text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                      {line.timestamp.toLocaleTimeString()}
                    </span>
                  )}
                </div>
              )
            })}

            {/* Cursor */}
            <div className="flex items-center gap-2 pt-2">
              <span className="text-green-400">$</span>
              <span className="inline-block w-2 h-4 bg-green-400 animate-pulse" />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Terminal
