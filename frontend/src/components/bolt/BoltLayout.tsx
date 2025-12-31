'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import Image from 'next/image'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { FileExplorer } from './FileExplorer'
import { CodeEditor } from './CodeEditor'
import { PlanView } from './PlanView'
import { ProjectSelector } from './ProjectSelector'
import { ProjectRunControls } from './ProjectRunControls'
import { BuildDocumentsPanel } from './BuildDocumentsPanel'
import { ProjectStagesPanel } from './ProjectStagesPanel'
// WelcomeScreen and QuickActions removed - now showing clean empty state

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
  ChevronRight,
  ListTodo,
  Home,
  Layers,
  Crown,
  RefreshCw,
  AlertCircle,
  LogOut,
  User,
  HelpCircle,
  CreditCard,
  Sun,
  Moon,
  Monitor,
  Check,
  FileText,
  Lock,
} from 'lucide-react'
import { useRouter } from 'next/navigation'
import { useTerminal } from '@/hooks/useTerminal'
import { Message, AIMessage, ThinkingStep, useChatStore } from '@/store/chatStore'
import { useVersionControl } from '@/services/versionControl/historyManager'
import { exportProjectAsZip } from '@/services/project/exportService'
import { useProject } from '@/hooks/useProject'
import { useAuth } from '@/hooks/useAuth'
import { useProjectStore } from '@/store/projectStore'
import { usePlanStatus } from '@/hooks/usePlanStatus'
// import { useConnectionHealth } from '@/hooks/useConnectionHealth' // Disabled - was causing header blinking
import { ReconnectionBanner } from '@/components/ReconnectionBanner'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
  hash?: string  // MD5 hash for change detection (Bolt.new style)
  isLoading?: boolean  // True while content is being fetched
  isLoaded?: boolean  // True if content has been fetched
}

interface BoltLayoutProps {
  onSendMessage: (message: string) => void
  onStopGeneration?: () => void
  messages: Message[]
  files: FileNode[]
  isLoading?: boolean
  tokenBalance?: number
  livePreview?: React.ReactNode
  onServerStart?: (url: string) => void
  onServerStop?: () => void
  onGenerateProject?: () => void
}

export function BoltLayout({
  onSendMessage,
  onStopGeneration,
  messages,
  files,
  isLoading = false,
  tokenBalance = 0,
  livePreview,
  onServerStart,
  onServerStop,
  onGenerateProject,
}: BoltLayoutProps) {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false)
  const [isThemeMenuOpen, setIsThemeMenuOpen] = useState(false)
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>('dark')
  const userMenuRef = useRef<HTMLDivElement>(null)
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null)
  const [activeTab, setActiveTab] = useState<'preview' | 'code' | 'docs'>('preview')
  const [isPlanViewVisible, setIsPlanViewVisible] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)

  // Mobile responsiveness
  const [isMobile, setIsMobile] = useState(false)
  const [mobilePanel, setMobilePanel] = useState<'chat' | 'code' | 'preview'>('chat')

  // Detect mobile screen
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (mobile) {
        setIsSidebarOpen(false) // Close sidebar on mobile by default
      }
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setIsUserMenuOpen(false)
        setIsThemeMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Handle theme change
  const handleThemeChange = (newTheme: 'dark' | 'light' | 'system') => {
    setTheme(newTheme)
    // Apply theme to document
    if (newTheme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
      document.documentElement.classList.toggle('dark', systemTheme === 'dark')
    } else {
      document.documentElement.classList.toggle('dark', newTheme === 'dark')
    }
    localStorage.setItem('theme', newTheme)
  }

  // Initialize theme on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'dark' | 'light' | 'system' | null
    if (savedTheme) {
      setTheme(savedTheme)
      if (savedTheme === 'system') {
        const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
        document.documentElement.classList.toggle('dark', systemTheme === 'dark')
      } else {
        document.documentElement.classList.toggle('dark', savedTheme === 'dark')
      }
    } else {
      // Default to dark theme
      document.documentElement.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    }
  }, [])

  // Resizable panel states - thin like border lines
  const [leftPanelWidth, setLeftPanelWidth] = useState(22) // percentage (narrower chat panel)
  const [fileExplorerWidth, setFileExplorerWidth] = useState(260) // pixels (wider for readable file names)
  const [isResizingMain, setIsResizingMain] = useState(false)
  const [isResizingExplorer, setIsResizingExplorer] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  // Import project store for file operations
  const { openTab } = useProject()

  // Import terminal hooks
  const { isVisible: showTerminal, height: terminalHeight, toggleTerminal, openTerminal, setHeight: setTerminalHeight, logs: terminalLogs, addLog, startSession, endSession } = useTerminal()

  // Memoized terminal command handler to prevent XTerminal re-renders
  const handleTerminalCommand = useCallback((cmd: string) => {
    addLog({ type: 'command', content: cmd })
    addLog({ type: 'output', content: `Command received: ${cmd}` })
  }, [addLog])

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

  // Get chat store for clearing messages and updating message state
  const { clearMessages, addMessage, addFileOperation, updateFileOperation, updateMessageStatus, appendToMessage, addThinkingStep, updateThinkingStep } = useChatStore()

  // Get plan status for project limits
  const { projectsCreated, projectLimit, isPremium, isFree, needsUpgrade, features } = usePlanStatus()

  // Resume generation state
  const [canResume, setCanResume] = useState(false)
  const [isResuming, setIsResuming] = useState(false)
  const [resumeMessage, setResumeMessage] = useState<string | null>(null)

  // Check if project generation was interrupted
  useEffect(() => {
    const checkResumeStatus = async () => {
      if (!currentProject?.id || currentProject.id === 'default-project') return

      try {
        const token = localStorage.getItem('access_token')
        if (!token) return

        const response = await fetch(`${API_BASE_URL}/orchestrator/project/${currentProject.id}/status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if (response.ok) {
          const data = await response.json()
          setCanResume(data.can_resume)
          if (data.can_resume) {
            setResumeMessage(`Generation interrupted. ${data.files_generated} files generated.`)
          }
        }
      } catch (error) {
        console.warn('[BoltLayout] Failed to check resume status:', error)
      }
    }

    checkResumeStatus()
  }, [currentProject?.id])

  // Resume generation handler
  const handleResumeGeneration = async () => {
    if (!currentProject?.id || isResuming) return

    setIsResuming(true)
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        alert('Please log in to resume generation')
        return
      }

      // Use SSE to stream resume events
      const response = await fetch(`${API_BASE_URL}/orchestrator/resume`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          project_id: currentProject.id,
          continue_message: 'Continue generating the remaining files'
        })
      })

      if (!response.ok) {
        const error = await response.json()
        if (error.detail?.error === 'file_limit_reached') {
          alert('FREE plan limit reached. Please upgrade to continue.')
          window.open('/pricing', '_blank')
        } else {
          alert(`Failed to resume: ${error.detail || 'Unknown error'}`)
        }
        return
      }

      // Stream the response (similar to normal generation)
      const reader = response.body?.getReader()
      if (!reader) return

      // Create a resume message to track file operations
      const resumeMessageId = `resume-${Date.now()}`
      const resumeMessage = {
        id: resumeMessageId,
        type: 'assistant' as const,
        content: 'Resuming generation...',
        isStreaming: true,
        timestamp: new Date(),
        fileOperations: [] as Array<{ type: 'create' | 'modify' | 'delete'; path: string; description: string; status: 'pending' | 'in-progress' | 'complete' | 'error' }>,
        thinkingSteps: [] as Array<{ label: string; status: 'pending' | 'active' | 'complete'; category: string }>
      }
      addMessage(resumeMessage)

      const decoder = new TextDecoder()

      // Track which files have been added to avoid duplicates (persists across all events)
      const addedFiles = new Set<string>()

      // Helper to add file operation if not exists, then update
      const addOrUpdateFileOp = (path: string, status: 'pending' | 'in-progress' | 'complete', description?: string) => {
        if (!addedFiles.has(path)) {
          addFileOperation(resumeMessageId, {
            type: 'create',
            path,
            description: description || `Creating ${path}`,
            status
          })
          addedFiles.add(path)
        } else {
          updateFileOperation(resumeMessageId, path, { status, description })
        }
      }

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              console.log('[Resume] Event:', event.type, event.data)

              // Handle plan_created to show planned files FIRST (this should come early in the stream)
              // Backend sends files in event.data.files (direct) or event.data.plan.files (nested)
              if (event.type === 'plan_created') {
                const files = event.data?.files || event.data?.plan?.files || []
                console.log('[Resume] plan_created received with', files.length, 'files')
                for (const file of files) {
                  const filePath = typeof file === 'string' ? file : file.path
                  if (filePath) {
                    addOrUpdateFileOp(filePath, 'pending', `Planned: ${filePath}`)
                  }
                }
              }

              // Handle file_operation events to show progress in UI
              if (event.type === 'file_operation') {
                const fileOp = event.data || event
                const opPath = fileOp.path || ''
                const opStatus = fileOp.operation_status || fileOp.status || 'pending'

                if (opPath) {
                  const mappedStatus = opStatus === 'complete' ? 'complete' : opStatus === 'in_progress' ? 'in-progress' : 'pending'
                  addOrUpdateFileOp(opPath, mappedStatus, opStatus === 'in_progress' ? `Creating ${opPath}` : undefined)
                }
              }

              // Handle file_start events (file generation starting)
              if (event.type === 'file_start' && event.data?.path) {
                const filePath = event.data.path
                addOrUpdateFileOp(filePath, 'in-progress', `Creating ${filePath}`)
              }

              // Handle file_content events (file completed)
              if (event.type === 'file_content' && event.data?.path) {
                const projectStore = useProjectStore.getState()
                const filePath = event.data.path
                const ext = filePath.split('.').pop()?.toLowerCase() || ''
                const langMap: Record<string, string> = {
                  'ts': 'typescript', 'tsx': 'typescript', 'js': 'javascript', 'jsx': 'javascript',
                  'py': 'python', 'css': 'css', 'html': 'html', 'json': 'json', 'md': 'markdown'
                }
                projectStore.addFile({
                  path: filePath,
                  content: event.data.content || '',
                  type: 'file',
                  language: langMap[ext] || ext || 'text'
                })
                // Mark file as complete
                addOrUpdateFileOp(filePath, 'complete')
              }

              // Handle file_complete events (legacy format)
              if (event.type === 'file_complete' && event.data?.path) {
                const projectStore = useProjectStore.getState()
                const filePath = event.data.path
                const ext = filePath.split('.').pop()?.toLowerCase() || ''
                const langMap: Record<string, string> = {
                  'ts': 'typescript', 'tsx': 'typescript', 'js': 'javascript', 'jsx': 'javascript',
                  'py': 'python', 'css': 'css', 'html': 'html', 'json': 'json', 'md': 'markdown'
                }
                projectStore.addFile({
                  path: filePath,
                  content: event.data.full_content || '',
                  type: 'file',
                  language: langMap[ext] || ext || 'text'
                })
                // Mark file as complete
                addOrUpdateFileOp(filePath, 'complete')
              }

              // Handle thinking_step events to show progress stages
              if (event.type === 'thinking_step') {
                const stepData = event.data || event
                const label = stepData.label || stepData.step || 'Processing'
                const status = stepData.status || 'active'
                const category = stepData.category || 'general'

                // Map backend status to frontend status
                const mappedStatus = status === 'complete' ? 'complete' : status === 'active' ? 'active' : 'pending'

                // Check if step already exists
                const foundMessage = useChatStore.getState().messages
                  .find(m => m.id === resumeMessageId)
                const existingStep = foundMessage?.type === 'assistant'
                  ? (foundMessage as AIMessage).thinkingSteps?.find((s: ThinkingStep) => s.label === label)
                  : undefined

                if (existingStep) {
                  updateThinkingStep(resumeMessageId, label, { status: mappedStatus })
                } else {
                  addThinkingStep(resumeMessageId, { label, status: mappedStatus, category })
                }
              }

              // Handle status events for general progress updates
              if (event.type === 'status') {
                const message = event.data?.message || event.message
                if (message) {
                  appendToMessage(resumeMessageId, `\n${message}`)
                }
              }

              if (event.type === 'complete') {
                setCanResume(false)
                setResumeMessage(null)
                updateMessageStatus(resumeMessageId, 'complete')
                appendToMessage(resumeMessageId, '\n\nResume complete!')
              }

              if (event.type === 'upgrade_required') {
                alert(event.data?.message || 'Upgrade required to continue')
                window.open('/pricing', '_blank')
              }
            } catch (e) {
              // Ignore parse errors for partial chunks
            }
          }
        }
      }

      // Mark resume message as complete
      updateMessageStatus(resumeMessageId, 'complete')

    } catch (error) {
      console.error('[Resume] Error:', error)
      alert('Failed to resume generation. Please try again.')
    } finally {
      setIsResuming(false)
    }
  }

  // Handle new project - clears everything for a fresh start
  const handleNewProject = useCallback(() => {
    resetProject()  // Clears project, files, tabs, session
    clearMessages()  // Clears chat messages
    setSelectedFile(null)
    setActiveTab('preview')
    console.log('[BoltLayout] New project started')
  }, [resetProject, clearMessages])

  // Export project handler - downloads entire project as ZIP
  const handleExportProject = async () => {
    if (!currentProject) {
      console.error("No project to export")
      return
    }

    // Double-check if user has download_files feature enabled (UI should already block this)
    if (features && !features.download_files) {
      console.warn("[Export] User doesn't have download_files feature")
      return
    }

    // First try: Backend export (PREFERRED - has access to ALL files in sandbox/storage)
    // This is the most reliable method as it exports directly from the server filesystem
    if (currentProject.id) {
      try {
        const token = localStorage.getItem('access_token')
        console.log(`[Export] Attempting backend export for project: ${currentProject.id}`)
        const response = await fetch(`${API_BASE_URL}/execution/export/${currentProject.id}`, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
        if (response.ok) {
          const blob = await response.blob()
          // Verify it's actually a ZIP with content
          if (blob.size > 100) {  // Minimum valid ZIP size
            const url = URL.createObjectURL(blob)
            const link = document.createElement("a")
            link.href = url
            link.download = (currentProject.name || currentProject.id) + ".zip"
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
            console.log(`[Export] Successfully exported ${blob.size} bytes from backend`)
            return
          } else {
            console.warn("[Export] Backend returned empty/tiny ZIP, trying fallback")
          }
        } else {
          console.warn(`[Export] Backend export failed: ${response.status} ${response.statusText}`)
        }
      } catch (error) {
        console.warn("[Export] Backend export error, trying fallback:", error)
      }
    }

    // Second try: Session download URL (if available from recent generation)
    if (sessionId && downloadUrl) {
      try {
        console.log("[Export] Attempting session download")
        const response = await fetch(`${API_BASE_URL}${downloadUrl.replace('/api/v1', '')}`)
        if (response.ok) {
          const blob = await response.blob()
          if (blob.size > 100) {
            const url = URL.createObjectURL(blob)
            const link = document.createElement("a")
            link.href = url
            link.download = (currentProject.name || "project") + ".zip"
            document.body.appendChild(link)
            link.click()
            document.body.removeChild(link)
            URL.revokeObjectURL(url)
            console.log("[Export] Project downloaded from session storage")
            return
          }
        }
      } catch (error) {
        console.warn("[Export] Session download failed:", error)
      }
    }

    // Third try: Client-side ZIP generation (works offline, but only includes loaded files)
    if (currentProject.files.length > 0) {
      try {
        console.log("[Export] Attempting client-side ZIP generation")
        await exportProjectAsZip(currentProject.name, currentProject.files)
        console.log("[Export] Project exported via client-side ZIP")
        return
      } catch (error) {
        console.error("[Export] Client-side export failed:", error)
      }
    }

    console.error("[Export] All export methods failed")
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

  // Mouse move handler for resizing with requestAnimationFrame throttling
  useEffect(() => {
    let rafId: number | null = null
    let lastX = 0

    const handleMouseMove = (e: MouseEvent) => {
      lastX = e.clientX

      // Use requestAnimationFrame to throttle updates (smoother than debounce for resize)
      if (rafId === null) {
        rafId = requestAnimationFrame(() => {
          if (isResizingMain && containerRef.current) {
            const containerRect = containerRef.current.getBoundingClientRect()
            const newWidth = ((lastX - containerRect.left) / containerRect.width) * 100
            // Clamp between 10% and 30%
            setLeftPanelWidth(Math.max(10, Math.min(30, newWidth)))
          }
          if (isResizingExplorer && containerRef.current) {
            const containerRect = containerRef.current.getBoundingClientRect()
            const rightPanelStart = containerRect.left + (containerRect.width * leftPanelWidth / 100)
            const newWidth = lastX - rightPanelStart
            // Clamp between 50px and 180px
            setFileExplorerWidth(Math.max(50, Math.min(180, newWidth)))
          }
          rafId = null
        })
      }
    }

    const handleMouseUp = () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId)
        rafId = null
      }
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
      if (rafId !== null) {
        cancelAnimationFrame(rafId)
      }
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

  // Track thinkingSteps and fileOperations for auto-scroll during generation
  const lastMessageThinkingSteps = (lastMessage as any)?.thinkingSteps?.length || 0
  const lastMessageFileOperations = (lastMessage as any)?.fileOperations?.length || 0

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

  // Auto-scroll when thinkingSteps or fileOperations update (PlanView content)
  useEffect(() => {
    if (lastMessageThinkingSteps > 0 || lastMessageFileOperations > 0) {
      requestAnimationFrame(() => {
        scrollToBottom(true)
      })
    }
  }, [lastMessageThinkingSteps, lastMessageFileOperations, scrollToBottom])

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
    <div className="h-screen w-screen flex flex-col bg-[hsl(var(--bolt-bg-primary))] overflow-hidden">
      {/* Reconnection Banner */}
      <ReconnectionBanner
        projectId={currentProject?.id}
        onResume={(stream) => {
          console.log('Resuming project generation...')
          // Handle resume stream
        }}
      />

      {/* Top Header - Responsive */}
      <div className="relative z-50 flex items-center justify-between px-3 md:px-6 py-2 md:py-3 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] flex-shrink-0 overflow-visible">
        <div className="flex items-center gap-2 md:gap-3">
          {/* BharatBuild Logo */}
          <a
            href="/"
            className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
            title="BharatBuild AI - Go to Home"
          >
            <Image
              src="/logo.png"
              alt="BharatBuild"
              width={32}
              height={32}
              className="rounded"
            />
            <span className="hidden md:block text-sm font-semibold bg-gradient-to-r from-blue-400 to-cyan-400 bg-clip-text text-transparent">
              BharatBuild
            </span>
          </a>

          {/* Project Selector - Hidden on very small screens */}
          <div className="hidden sm:block">
            <ProjectSelector onNewProject={handleNewProject} />
          </div>
        </div>

        {/* Mobile Panel Switcher */}
        {isMobile && (
          <div className="flex items-center gap-1 bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg p-1">
            <button
              onClick={() => setMobilePanel('chat')}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mobilePanel === 'chat'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))]'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => {
                setMobilePanel('code')
                setActiveTab('code')
              }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mobilePanel === 'code'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))]'
              }`}
            >
              Code
            </button>
            <button
              onClick={() => {
                setMobilePanel('preview')
                setActiveTab('preview')
              }}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                mobilePanel === 'preview'
                  ? 'bg-[hsl(var(--bolt-accent))] text-white'
                  : 'text-[hsl(var(--bolt-text-secondary))]'
              }`}
            >
              Preview
            </button>
          </div>
        )}

        <div className="flex items-center gap-2">
          {/* Code & Preview Buttons - Hidden on mobile (use mobile switcher instead) */}
          <div className="hidden md:flex items-center gap-1 mr-32">
            <button
              onClick={() => {
                setActiveTab('code')
                if (terminalLogs.length > 0) {
                  openTerminal()
                }
              }}
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
              // Add output to terminal buffer (terminal is already opened by onStartSession)
              addLog({
                type: 'output',
                content: line
              })
            }}
            onStartSession={() => {
              // Start session - keeps terminal open during and after execution
              startSession()
              // Stay on Code tab to see terminal logs - will switch to Preview when server starts
              setActiveTab('code')
              openTerminal()
            }}
            onEndSession={() => {
              // End session but keep terminal open for user to review output
              endSession()
            }}
          />

          {/* Resume Generation - Show when generation was interrupted */}
          {canResume && (
            <button
              onClick={handleResumeGeneration}
              disabled={isResuming}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 transition-colors disabled:opacity-50"
              title={resumeMessage || "Resume interrupted generation"}
            >
              {isResuming ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
              {isResuming ? 'Resuming...' : 'Resume'}
            </button>
          )}

          {/* Export Project */}
          {features && !features.download_files ? (
            // Show locked button for non-premium users
            <a
              href="/pricing"
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium bg-amber-500/10 border border-amber-500/30 text-amber-400 hover:bg-amber-500/20 transition-colors"
              title="Upgrade to Premium to download projects"
            >
              <Lock className="w-4 h-4" />
              Export (Premium)
            </a>
          ) : (
            <button
              onClick={handleExportProject}
              disabled={!currentProject || currentProject.files.length === 0}
              className="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Download Project as ZIP"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          )}

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

          {/* Projects Counter */}
          <div
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg border ${
              isPremium
                ? 'bg-gradient-to-r from-amber-500/10 to-yellow-500/10 border-amber-500/30'
                : 'bg-[hsl(var(--bolt-bg-tertiary))] border-[hsl(var(--bolt-border))]'
            }`}
            title={projectLimit !== null ? `${projectsCreated} of ${projectLimit} projects used` : 'Unlimited projects'}
          >
            {isPremium ? (
              <Crown className="w-4 h-4 text-amber-500" />
            ) : (
              <Layers className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
            )}
            <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
              {projectLimit !== null ? (
                <>
                  {projectsCreated}/{projectLimit} Projects
                </>
              ) : (
                'Unlimited'
              )}
            </span>
            {needsUpgrade && isFree && (
              <a
                href="/pricing"
                className="ml-1 px-2 py-0.5 text-xs font-medium rounded-full bg-gradient-to-r from-blue-500 to-cyan-500 text-white hover:from-blue-600 hover:to-cyan-600 transition-colors"
              >
                Upgrade
              </a>
            )}
          </div>

          {/* User Menu Dropdown */}
          {user && (
            <div className="relative" ref={userMenuRef}>
              {/* User Avatar/Name - Click to open dropdown */}
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-xs font-bold">
                  {(user.full_name || user.name || user.email || 'U').charAt(0).toUpperCase()}
                </div>
                <span className="hidden sm:block text-xs font-medium text-[hsl(var(--bolt-text-primary))] max-w-[100px] truncate">
                  {user.full_name || user.name || user.email?.split('@')[0] || 'User'}
                </span>
                <ChevronDown className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Menu - Fixed position to avoid overflow clipping */}
              {isUserMenuOpen && (
                <div
                  className="fixed w-48 rounded-xl bg-[#1a1a2e] border border-[#2a2a3e] shadow-2xl shadow-black/40 py-1"
                  style={{
                    top: (userMenuRef.current?.getBoundingClientRect().bottom || 0) + 8,
                    right: window.innerWidth - (userMenuRef.current?.getBoundingClientRect().right || 0),
                    zIndex: 9999
                  }}
                >
                  {/* Menu Items */}
                  <a
                    href="/profile"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-colors"
                    onClick={() => setIsUserMenuOpen(false)}
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </a>
                  <a
                    href="/help"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-colors"
                    onClick={() => setIsUserMenuOpen(false)}
                  >
                    <HelpCircle className="w-4 h-4" />
                    Help
                  </a>
                  <a
                    href="/pricing"
                    className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-colors"
                    onClick={() => setIsUserMenuOpen(false)}
                  >
                    <CreditCard className="w-4 h-4" />
                    Subscription
                  </a>

                  {/* Theme with Submenu */}
                  <div className="relative">
                    <button
                      onClick={() => setIsThemeMenuOpen(!isThemeMenuOpen)}
                      className="flex items-center justify-between w-full px-4 py-2.5 text-sm text-gray-300 hover:text-white hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        {theme === 'dark' ? <Moon className="w-4 h-4" /> : theme === 'light' ? <Sun className="w-4 h-4" /> : <Monitor className="w-4 h-4" />}
                        Theme
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 capitalize">{theme}</span>
                        <ChevronRight className="w-4 h-4 text-gray-500 rotate-180" />
                      </div>
                    </button>

                    {/* Theme Submenu */}
                    {isThemeMenuOpen && (
                      <div
                        className="absolute right-full top-0 mr-1 w-36 rounded-lg bg-[#1a1a2e] border border-[#2a2a3e] shadow-xl py-1"
                      >
                        <button
                          onClick={() => {
                            handleThemeChange('dark')
                            setIsThemeMenuOpen(false)
                          }}
                          className={`flex items-center gap-3 w-full px-4 py-2 text-sm transition-colors ${
                            theme === 'dark' ? 'text-blue-400 bg-blue-500/10' : 'text-gray-300 hover:text-white hover:bg-white/5'
                          }`}
                        >
                          <Moon className="w-4 h-4" />
                          Dark
                          {theme === 'dark' && <Check className="w-4 h-4 ml-auto" />}
                        </button>
                        <button
                          onClick={() => {
                            handleThemeChange('light')
                            setIsThemeMenuOpen(false)
                          }}
                          className={`flex items-center gap-3 w-full px-4 py-2 text-sm transition-colors ${
                            theme === 'light' ? 'text-blue-400 bg-blue-500/10' : 'text-gray-300 hover:text-white hover:bg-white/5'
                          }`}
                        >
                          <Sun className="w-4 h-4" />
                          Light
                          {theme === 'light' && <Check className="w-4 h-4 ml-auto" />}
                        </button>
                        <button
                          onClick={() => {
                            handleThemeChange('system')
                            setIsThemeMenuOpen(false)
                          }}
                          className={`flex items-center gap-3 w-full px-4 py-2 text-sm transition-colors ${
                            theme === 'system' ? 'text-blue-400 bg-blue-500/10' : 'text-gray-300 hover:text-white hover:bg-white/5'
                          }`}
                        >
                          <Monitor className="w-4 h-4" />
                          System
                          {theme === 'system' && <Check className="w-4 h-4 ml-auto" />}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Divider */}
                  <div className="my-1 border-t border-[#2a2a3e]" />

                  {/* Sign Out */}
                  <button
                    onClick={() => {
                      setIsUserMenuOpen(false)
                      setIsThemeMenuOpen(false)
                      logout()
                    }}
                    className="flex items-center gap-3 w-full px-4 py-2.5 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <LogOut className="w-4 h-4" />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div ref={containerRef} className="flex-1 flex overflow-hidden">
        {/* Left Panel - AI Chat Interaction */}
        <div
          className={`flex flex-col border-r border-[hsl(var(--bolt-border))] flex-shrink-0 min-w-0 ${
            isMobile
              ? mobilePanel === 'chat' ? 'w-full' : 'hidden'
              : ''
          }`}
          style={!isMobile ? { width: isSidebarOpen ? `${leftPanelWidth}%` : '100%' } : undefined}
        >
          {/* Project Stages Panel - Timeline View */}
          <div ref={messagesContainerRef} className="flex-1 overflow-y-auto scrollbar-thin bg-[hsl(var(--bolt-bg-primary))]">
            <ProjectStagesPanel />
            <div ref={messagesEndRef} />
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
        {(isSidebarOpen || isMobile) && (
          <div
            className={`flex-1 flex flex-col border-l border-[hsl(var(--bolt-border))] min-w-0 ${
              isMobile
                ? (mobilePanel === 'code' || mobilePanel === 'preview') ? 'w-full' : 'hidden'
                : ''
            }`}
          >
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
                        onFileSelect={async (file) => {
                          // Bolt.new-style lazy loading: content is loaded on-demand
                          const filePath = file.path || file.name

                          // Check if content already loaded
                          if (file.content !== undefined && file.content !== null) {
                            // Content already available, open tab immediately
                            openTab({
                              path: filePath,
                              content: file.content,
                              language: '',
                              type: 'file'
                            })
                          } else {
                            // Content not loaded yet - lazy load from backend
                            console.log(`[BoltLayout] Lazy loading file: ${filePath}`)

                            // Open tab with loading state
                            openTab({
                              path: filePath,
                              content: '// Loading...',
                              language: '',
                              type: 'file',
                              isLoading: true
                            })

                            // Load content from store (which fetches from backend)
                            const { loadFileContent } = useProjectStore.getState()
                            const content = await loadFileContent(filePath)

                            if (content !== null) {
                              // Update the tab with loaded content
                              openTab({
                                path: filePath,
                                content: content,
                                language: '',
                                type: 'file',
                                isLoaded: true
                              })
                            }
                          }
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
                <div className="flex-1 flex flex-col bg-white h-full">
                  {/* Preview Content - Full height, no terminal in preview mode */}
                  <div className="flex-1 h-full">
                    {livePreview || <div className="h-full w-full" />}
                  </div>
                </div>
              )}

              {activeTab === 'docs' && (
                <div className="flex-1 flex flex-col h-full">
                  <BuildDocumentsPanel />
                </div>
              )}

              {/* Terminal Panel - Only visible in Code mode */}
              <div
                className={`border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] flex flex-col flex-shrink-0 ${showTerminal && activeTab === 'code' ? '' : 'hidden'}`}
                style={{ height: `${terminalHeight}px` }}
              >
                {/* Draggable Resize Handle */}
                <div
                  className="h-1.5 bg-[hsl(var(--bolt-border))] cursor-ns-resize hover:bg-blue-500/50 active:bg-blue-500 transition-colors group flex items-center justify-center"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    const startY = e.clientY
                    const startHeight = terminalHeight

                    const handleMouseMove = (moveEvent: MouseEvent) => {
                      const delta = startY - moveEvent.clientY
                      const newHeight = Math.min(600, Math.max(100, startHeight + delta))
                      setTerminalHeight(newHeight)
                    }

                    const handleMouseUp = () => {
                      document.removeEventListener('mousemove', handleMouseMove)
                      document.removeEventListener('mouseup', handleMouseUp)
                      document.body.style.cursor = ''
                      document.body.style.userSelect = ''
                    }

                    document.addEventListener('mousemove', handleMouseMove)
                    document.addEventListener('mouseup', handleMouseUp)
                    document.body.style.cursor = 'ns-resize'
                    document.body.style.userSelect = 'none'
                  }}
                >
                  {/* Drag indicator */}
                  <div className="w-10 h-0.5 rounded-full bg-gray-500 group-hover:bg-blue-400 transition-colors" />
                </div>

                {/* Terminal Header */}
                <div className="flex items-center justify-between px-3 py-2 border-b border-[hsl(var(--bolt-border))]">
                  <div className="flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                    <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
                      Terminal
                    </span>
                    <span className="text-xs text-gray-500">({terminalHeight}px)</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setTerminalHeight(Math.max(100, terminalHeight - 50))}
                      className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
                      title="Decrease height"
                    >
                      <Minus className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))]" />
                    </button>
                    <button
                      onClick={() => setTerminalHeight(Math.min(600, terminalHeight + 50))}
                      className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
                      title="Increase height"
                    >
                      <Maximize2 className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))]" />
                    </button>
                    <button
                      onClick={() => toggleTerminal()}
                      className="p-1 hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded"
                      title="Close terminal"
                    >
                      <X className="w-3 h-3 text-[hsl(var(--bolt-text-secondary))]" />
                    </button>
                  </div>
                </div>

                {/* Terminal Content - xterm.js - Single instance */}
                <div className="flex-1 overflow-auto bg-[hsl(var(--bolt-bg-primary))]">
                  <XTerminal
                    logs={terminalLogs}
                    onCommand={handleTerminalCommand}
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
    </div>
  )
}
