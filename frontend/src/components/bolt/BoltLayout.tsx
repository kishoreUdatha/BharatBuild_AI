'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { FileExplorer } from './FileExplorer'
import { CodeEditor } from './CodeEditor'
import { PlanView } from './PlanView'
import { ProjectSelector } from './ProjectSelector'
import { ProjectRunControls } from './ProjectRunControls'

// Dynamically import XTerminal to avoid SSR issues
const XTerminal = dynamic(() => import('./XTerminal'), {
  ssr: false,
  loading: () => <div className="h-full flex items-center justify-center text-muted-foreground">Loading terminal...</div>
})
import {
  PanelLeftClose,
  PanelLeftOpen,
  Zap,
  Settings,
  Download,
  Sparkles,
  Eye,
  Code2,
  Terminal,
  X,
  Minus,
  Maximize2,
  ChevronDown,
  ChevronUp,
  ListTodo,
  FolderKanban,
  MessageSquare,
} from 'lucide-react'
import { FeedbackModal } from '@/components/feedback/FeedbackModal'
import { useRouter } from 'next/navigation'
import { useTerminal } from '@/hooks/useTerminal'
import { Message, useChatStore } from '@/store/chatStore'
import { useVersionControl } from '@/services/versionControl/historyManager'
import { exportProjectAsZip } from '@/services/project/exportService'
import { useProject } from '@/hooks/useProject'
import { useProjectStore } from '@/store/projectStore'
// import { useConnectionHealth } from '@/hooks/useConnectionHealth' // Disabled - was causing header blinking
import { ReconnectionBanner } from '@/components/ReconnectionBanner'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

interface BoltLayoutProps {
  onSendMessage: (message: string) => void
  onStopGeneration?: () => void
  messages: Message[]
  files: FileNode[]
  isLoading?: boolean
  tokenBalance?: number
  livePreview?: React.ReactNode
  onGenerateProject?: () => void
  onServerStart?: (url: string) => void
  onServerStop?: () => void
}

export function BoltLayout({
  onSendMessage,
  onStopGeneration,
  messages,
  onGenerateProject,
  files,
  isLoading = false,
  tokenBalance = 0,
  livePreview,
  onServerStart,
  onServerStop,
}: BoltLayoutProps) {
  const router = useRouter()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null)
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview')
  const [isPlanViewVisible, setIsPlanViewVisible] = useState(true)
  const [showFeedback, setShowFeedback] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // Resizable panel states - thin like border lines
  const [leftPanelWidth, setLeftPanelWidth] = useState(28) // percentage (balanced chat panel)
  const [fileExplorerWidth, setFileExplorerWidth] = useState(180) // pixels (balanced file explorer)
  const [isResizingMain, setIsResizingMain] = useState(false)
  const [isResizingExplorer, setIsResizingExplorer] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Import project store for file operations
  const { openTab } = useProject()

  // Import terminal hooks
  const { isVisible: showTerminal, height: terminalHeight, toggleTerminal, openTerminal, setHeight: setTerminalHeight, logs: terminalLogs, addLog, startSession, endSession } = useTerminal()

  // Version control hooks
  const { canUndo, canRedo, undo, redo, history } = useVersionControl()

  // Connection health monitoring - DISABLED to prevent header blinking
  // The health check was causing re-renders every 30 seconds
  // Uncomment if you need connection monitoring in the future
  /*
  const { isConnected, status: connectionStatus, latency } = useConnectionHealth({
    checkInterval: 30000,
    autoCheck: false, // Disable auto-check
    onDisconnect: () => {
      addLog({
        type: 'error',
        content: '⚠️ Connection lost. Your work will be saved locally.'
      })
    },
    onReconnect: () => {
      addLog({
        type: 'info',
        content: '✅ Connection restored!'
      })
    }
  })
  */
  // Use static values instead
  const connectionStatus = 'connected'
  const latency = null

  // Project hooks
  const { currentProject, updateFile } = useProject()

  // Get session info for ephemeral storage download
  const { sessionId, downloadUrl, resetProject } = useProjectStore()

  // Get chat store for clearing messages
  const { clearMessages } = useChatStore()

  // Handle new project - clears everything for a fresh start
  const handleNewProject = useCallback(() => {
    resetProject()  // Clears project, files, tabs, session
    clearMessages()  // Clears chat messages
    setSelectedFile(null)
    setActiveTab('preview')
    console.log('[BoltLayout] New project started')
  }, [resetProject, clearMessages])

  // Export project handler - uses ephemeral session storage (like Bolt.new)
  const handleExportProject = async () => {
    // First try: Use ephemeral session download (preferred - like Bolt.new)
    if (sessionId && downloadUrl) {
      try {
        const response = await fetch(`${API_BASE_URL}${downloadUrl.replace('/api/v1', '')}`)
        if (!response.ok) {
          throw new Error("Failed to download: " + response.statusText)
        }
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.href = url
        link.download = (currentProject?.name || "project") + ".zip"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        console.log("Project downloaded from session storage")
        return
      } catch (error) {
        console.warn("Session download failed, trying fallback:", error)
      }
    }

    // Second try: Client-side ZIP generation (works offline)
    if (currentProject && currentProject.files.length > 0) {
      try {
        await exportProjectAsZip(currentProject.name, currentProject.files)
        console.log("Project exported via client-side ZIP")
        return
      } catch (error) {
        console.error("Client-side export failed:", error)
      }
    }

    // Third try: Legacy backend export (if project saved permanently)
    if (currentProject?.id) {
      try {
        const response = await fetch(`${API_BASE_URL}/execution/export/${currentProject.id}`)
        if (!response.ok) {
          throw new Error("Failed to export: " + response.statusText)
        }
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const link = document.createElement("a")
        link.href = url
        link.download = (currentProject.name || currentProject.id) + ".zip"
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        console.log("Project exported from backend")
      } catch (error) {
        console.error("All export methods failed:", error)
      }
    } else {
      console.error("No project to export")
    }
  }


  // Handle undo - restore files from previous commit
  const handleUndo = () => {
    const commit = undo()
    if (commit && updateFile) {
      // Restore all file changes from this commit
      commit.fileChanges.forEach(change => {
        if (change.changeType === 'modify' || change.changeType === 'create') {
          updateFile(change.path, change.content)
        }
      })
    }
  }

  // Handle redo - restore files from next commit
  const handleRedo = () => {
    const commit = redo()
    if (commit && updateFile) {
      // Restore all file changes from this commit
      commit.fileChanges.forEach(change => {
        if (change.changeType === 'modify' || change.changeType === 'create') {
          updateFile(change.path, change.content)
        }
      })
    }
  }

  // Main splitter resize handler (between left chat panel and right panel)
  const handleMainSplitterMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingMain(true)
  }, [])

  // File explorer splitter resize handler (between file explorer and code editor)
  const handleExplorerSplitterMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizingExplorer(true)
  }, [])

  // Mouse move handler for resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isResizingMain && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect()
        const newWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100
        // Clamp between 10% and 30%
        setLeftPanelWidth(Math.max(10, Math.min(30, newWidth)))
      }
      if (isResizingExplorer && containerRef.current) {
        const containerRect = containerRef.current.getBoundingClientRect()
        const rightPanelStart = containerRect.left + (containerRect.width * leftPanelWidth / 100)
        const newWidth = e.clientX - rightPanelStart
        // Clamp between 50px and 180px
        setFileExplorerWidth(Math.max(50, Math.min(180, newWidth)))
      }
    }

    const handleMouseUp = () => {
      setIsResizingMain(false)
      setIsResizingExplorer(false)
    }

    if (isResizingMain || isResizingExplorer) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizingMain, isResizingExplorer, leftPanelWidth])

  // Helper function to scroll to bottom
  const scrollToBottom = useCallback((smooth: boolean = true) => {
    if (messagesContainerRef.current) {
      const container = messagesContainerRef.current
      if (smooth) {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: 'smooth'
        })
      } else {
        container.scrollTop = container.scrollHeight
      }
    }
    // Fallback to scrollIntoView
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' })
  }, [])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom(true)
  }, [messages, scrollToBottom])

  // Also scroll when streaming content updates (check last message content length)
  const lastMessage = messages[messages.length - 1]
  const lastMessageContent = lastMessage?.content || ''
  const lastMessageIsStreaming = lastMessage?.type === 'assistant' && (lastMessage as any).isStreaming || false

  useEffect(() => {
    if (lastMessageIsStreaming) {
      // Use requestAnimationFrame for smoother scroll during streaming
      requestAnimationFrame(() => {
        scrollToBottom(true)
      })
    }
  }, [lastMessageContent, lastMessageIsStreaming, scrollToBottom])

  // Scroll when loading state changes (new message being generated)
  useEffect(() => {
    if (isLoading) {
      scrollToBottom(true)
    }
  }, [isLoading, scrollToBottom])

  // Auto-switch to Code tab when files are generated
  useEffect(() => {
    if (files.length > 0 && activeTab === 'preview') {
      setActiveTab('code')
      // Auto-select first file if none selected
      if (!selectedFile && files[0]?.type === 'file') {
        setSelectedFile(files[0])
      }
    }
  }, [files.length])

  // Auto-switch to code tab when files are created
  useEffect(() => {
    if (files.length > 0) {
      setActiveTab('code')
    }
  }, [files.length])

  return (
    <div className="h-screen flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Reconnection Banner */}
      <ReconnectionBanner
        projectId={currentProject?.id}
        onResume={(stream) => {
          console.log('Resuming project generation...')
          // Handle resume stream
        }}
      />

      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg bolt-gradient-text">BharatBuild AI</span>
          </div>

          {/* Code & Preview Buttons */}
          <div className="flex items-center gap-1 ml-4">
            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'code'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
              }`}
            >
              <Code2 className="w-4 h-4" />
              Code
            </button>
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeTab === 'preview'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]'
              }`}
            >
              <Eye className="w-4 h-4" />
              Preview
            </button>
          </div>

          {/* Project Selector */}
          <ProjectSelector onNewProject={handleNewProject} />
        </div>

        <div className="flex items-center gap-2">
          {/* Generate Project */}
          {onGenerateProject && (
            <button
              onClick={onGenerateProject}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700 transition-colors"
              title="Generate Complete Project"
            >
              <Sparkles className="w-4 h-4" />
              Generate
            </button>
          )}

          {/* Project Run Controls (Docker) */}
          <ProjectRunControls
            onOpenTerminal={() => {
              openTerminal()
            }}
            onPreviewUrlChange={(url) => {
              if (url && onServerStart) {
                onServerStart(url)
                setActiveTab('preview')
              } else if (!url && onServerStop) {
                onServerStop()
              }
            }}
            onOutput={(line) => {
              // Show terminal (use openTerminal to avoid race conditions with toggle)
              openTerminal()
              // Add output to terminal
              addLog({
                type: 'output',
                content: line
              })
            }}
            onStartSession={() => {
              // Start session - keeps terminal open during and after execution
              startSession()
            }}
            onEndSession={() => {
              // End session but keep terminal open for user to review output
              endSession()
            }}
          />

          {/* Export Project */}
          <button
            onClick={handleExportProject}
            disabled={!currentProject || currentProject.files.length === 0}
            className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            title="Download Project as ZIP"
          >
            <Download className="w-4 h-4" />
            Export
          </button>

          {/* Connection Status Indicator - Only show when disconnected or reconnecting */}
          {connectionStatus !== 'connected' && connectionStatus !== 'checking' && (
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium ${
                connectionStatus === 'reconnecting'
                  ? 'bg-yellow-500/10 text-yellow-500'
                  : 'bg-red-500/10 text-red-500'
              }`}
              title={latency ? `Latency: ${latency}ms` : 'Connection status'}
            >
              <div
                className={`w-2 h-2 rounded-full ${
                  connectionStatus === 'reconnecting'
                    ? 'bg-yellow-500 animate-pulse'
                    : 'bg-red-500'
                }`}
              />
              {connectionStatus === 'reconnecting' ? 'Reconnecting...' : 'Offline'}
            </div>
          )}

          {/* Token Balance */}
          <div className="flex items-center gap-2 px-4 py-1.5 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))]">
            <Sparkles className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
            <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
              {tokenBalance.toLocaleString()} tokens
            </span>
          </div>

          {/* My Projects */}
          <button
            onClick={() => router.push('/projects')}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
            title="My Projects"
          >
            <FolderKanban className="w-4 h-4" />
            <span className="text-sm hidden sm:inline">Projects</span>
          </button>

          {/* Feedback */}
          <button
            onClick={() => setShowFeedback(true)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
            title="Send Feedback"
          >
            <MessageSquare className="w-4 h-4" />
            <span className="text-sm hidden sm:inline">Feedback</span>
          </button>

          {/* Settings */}
          <button
            className="flex items-center justify-center w-8 h-8 rounded-lg text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div ref={containerRef} className="flex-1 flex overflow-hidden">
        {/* Left Panel - AI Chat Interaction */}
        <div
          className="flex flex-col border-r border-[hsl(var(--bolt-border))] flex-shrink-0 min-w-0"
          style={{ width: isSidebarOpen ? `${leftPanelWidth}%` : '100%' }}
        >
          {/* Messages */}
          <div ref={messagesContainerRef} className="flex-1 overflow-y-auto scrollbar-thin">
            {messages.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center max-w-2xl px-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center mx-auto mb-6">
                    <Zap className="w-8 h-8 text-white" />
                  </div>
                  <h2 className="text-2xl font-bold mb-3 text-[hsl(var(--bolt-text-primary))]">
                    Welcome to BharatBuild AI
                  </h2>
                  <p className="text-[hsl(var(--bolt-text-secondary))] mb-8">
                    Describe your project and watch as AI agents build it in real-time.
                    Generate complete academic projects, production-ready code, and more.
                  </p>

                  <div className="grid grid-cols-2 gap-3 text-left">
                    {[
                      'Build a task management app with React',
                      'Create an e-commerce platform',
                      'Generate SRS for student project',
                      'Build a REST API with FastAPI',
                    ].map((example, index) => (
                      <button
                        key={index}
                        onClick={() => onSendMessage(example)}
                        className="p-3 rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))] transition-colors text-left"
                      >
                        <p className="text-sm text-[hsl(var(--bolt-text-primary))]">{example}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {messages.map((message, index) => (
                  <ChatMessage
                    key={index}
                    role={message.type}
                    content={message.content}
                    isStreaming={message.type === 'assistant' && message.isStreaming}
                  />
                ))}

                {/* Task Progress Panel - Only show when generating project */}
                {messages.some(m => m.type === 'assistant' && ((m.thinkingSteps?.length ?? 0) > 0 || (m.fileOperations?.length ?? 0) > 0)) && (
                  <div className="border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
                    <button
                      onClick={() => setIsPlanViewVisible(!isPlanViewVisible)}
                      className="w-full flex items-center justify-between px-4 py-2 hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <ListTodo className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
                        <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                          Generation Progress
                        </span>
                      </div>
                      {isPlanViewVisible ? (
                        <ChevronUp className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                      )}
                    </button>

                    {isPlanViewVisible && (
                      <div className="border-t border-[hsl(var(--bolt-border))] max-h-[300px] overflow-y-auto">
                        <PlanView />
                      </div>
                    )}
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-[hsl(var(--bolt-border))]">
            <ChatInput onSend={onSendMessage} onStop={onStopGeneration} isLoading={isLoading} />
          </div>
        </div>

        {/* Main Vertical Splitter - Thin border line */}
        {isSidebarOpen && (
          <div
            onMouseDown={handleMainSplitterMouseDown}
            className={`w-px cursor-col-resize transition-colors flex-shrink-0 ${
              isResizingMain ? 'bg-[hsl(var(--bolt-accent))]' : 'bg-[hsl(var(--bolt-border))] hover:bg-[hsl(var(--bolt-accent))]'
            }`}
            title="Drag to resize"
          />
        )}

        {/* Right Panel - Monaco Code Editor & Preview */}
        {isSidebarOpen && (
          <div className="flex-1 flex flex-col border-l border-[hsl(var(--bolt-border))] min-w-0">
            {/* Tab Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {activeTab === 'code' && (
                <>
                  {/* Code Editor Area */}
                  <div className={`flex ${showTerminal ? 'flex-1' : 'h-full'} overflow-hidden`}>
                    {/* File Explorer */}
                    <div
                      className="flex-shrink-0 border-r border-[hsl(var(--bolt-border))]"
                      style={{ width: `${fileExplorerWidth}px` }}
                    >
                      <FileExplorer
                        files={files}
                        onFileSelect={(file) => {
                          // Convert FileNode to ProjectFile and open in tab
                          openTab({
                            path: file.path || file.name,
                            content: file.content || '',
                            language: '',
                            type: 'file'
                          })
                        }}
                        selectedFile={selectedFile?.name}
                      />
                    </div>

                    {/* File Explorer Splitter - Thin border line */}
                    <div
                      onMouseDown={handleExplorerSplitterMouseDown}
                      className={`w-px cursor-col-resize transition-colors flex-shrink-0 ${
                        isResizingExplorer ? 'bg-[hsl(var(--bolt-accent))]' : 'bg-[hsl(var(--bolt-border))] hover:bg-[hsl(var(--bolt-accent))]'
                      }`}
                      title="Drag to resize"
                    />

                    {/* Code Editor - Simplified (no props needed) */}
                    <div className="flex-1 min-w-0">
                      <CodeEditor />
                    </div>
                  </div>

                </>
              )}

              {activeTab === 'preview' && (
                <div className={`flex-1 flex flex-col bg-white ${showTerminal ? '' : 'h-full'}`}>
                  {/* Preview Content */}
                  <div className="flex-1 h-full">
                    {livePreview || <div className="h-full w-full" />}
                  </div>
                </div>
              )}

              {/* Shared Terminal Panel - Single instance, persists across tab switches */}
              <div
                className={`border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] flex flex-col flex-shrink-0 ${showTerminal ? '' : 'hidden'}`}
                style={{ height: `${terminalHeight}px` }}
              >
                {/* Terminal Header */}
                <div className="flex items-center justify-between px-3 py-2 border-b border-[hsl(var(--bolt-border))]">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                    <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                      Terminal
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setTerminalHeight(Math.max(150, terminalHeight - 50))}
                      className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
                    >
                      <Minus className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))]" />
                    </button>
                    <button
                      onClick={() => setTerminalHeight(Math.min(400, terminalHeight + 50))}
                      className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
                    >
                      <Maximize2 className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))]" />
                    </button>
                    <button
                      onClick={() => toggleTerminal()}
                      className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
                    >
                      <X className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))]" />
                    </button>
                  </div>
                </div>

                {/* Terminal Content - xterm.js - Single instance */}
                <div className="flex-1 overflow-hidden bg-[hsl(var(--bolt-bg-primary))]">
                  <XTerminal
                    logs={terminalLogs}
                    onCommand={(cmd) => {
                      addLog({
                        type: 'command',
                        content: cmd
                      })
                      addLog({
                        type: 'output',
                        content: `Command received: ${cmd}`
                      })
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Toggle Sidebar Button */}
        <button
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          className="absolute right-0 top-1/2 -translate-y-1/2 p-2 bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-l-lg hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
        >
          {isSidebarOpen ? (
            <PanelLeftClose className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
          ) : (
            <PanelLeftOpen className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
          )}
        </button>
      </div>

      {/* Feedback Modal */}
      <FeedbackModal isOpen={showFeedback} onClose={() => setShowFeedback(false)} />
    </div>
  )
}
