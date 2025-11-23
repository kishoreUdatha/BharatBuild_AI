'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { FileExplorer } from './FileExplorer'
import { CodeEditor } from './CodeEditor'
import { PlanView } from './PlanView'
import { XTerminal } from './XTerminal'
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
  Undo2,
  Redo2,
  History,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useTerminal } from '@/hooks/useTerminal'
import { Message } from '@/store/chatStore'
import { useVersionControl } from '@/services/versionControl/historyManager'
import { exportProjectAsZip } from '@/services/project/exportService'
import { useProject } from '@/hooks/useProject'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

interface BoltLayoutProps {
  onSendMessage: (message: string) => void
  messages: Message[]
  files: FileNode[]
  isLoading?: boolean
  tokenBalance?: number
  livePreview?: React.ReactNode
  onGenerateProject?: () => void
}

export function BoltLayout({
  onSendMessage,
  messages,
  onGenerateProject,
  files,
  isLoading = false,
  tokenBalance = 0,
  livePreview,
}: BoltLayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [selectedFile, setSelectedFile] = useState<FileNode | null>(null)
  const [activeTab, setActiveTab] = useState<'preview' | 'code'>('preview')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Import project store for file operations
  const { openTab } = useProject()

  // Import terminal hooks
  const { isVisible: showTerminal, height: terminalHeight, toggleTerminal, setHeight: setTerminalHeight, logs: terminalLogs, addLog } = useTerminal()

  // Version control hooks
  const { canUndo, canRedo, undo, redo, history } = useVersionControl()

  // Project hooks
  const { currentProject, updateFile } = useProject()

  // Export project handler
  const handleExportProject = async () => {
    if (currentProject) {
      try {
        await exportProjectAsZip(currentProject.name, currentProject.files)
      } catch (error) {
        console.error('Failed to export project:', error)
      }
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

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
      {/* Top Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg bolt-gradient-text">BharatBuild AI</span>
          </div>
          <Badge variant="secondary" className="text-xs">
            <Sparkles className="w-3 h-3 mr-1" />
            Powered by Claude 3.5
          </Badge>

          {/* Preview/Code Tabs in Header */}
          <div className="flex items-center gap-1 ml-8">
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
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Terminal Toggle - Only show in Code tab */}
          {activeTab === 'code' && !showTerminal && (
            <button
              onClick={() => toggleTerminal()}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors border border-[hsl(var(--bolt-border))]"
            >
              <Terminal className="w-4 h-4" />
              <span>Show Terminal</span>
            </button>
          )}

          {/* Version Control Actions */}
          <div className="flex items-center gap-1 px-2 py-1 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))]">
            <Button
              variant="ghost"
              size="sm"
              disabled={!canUndo}
              onClick={handleUndo}
              className="h-7 w-7 p-0 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] disabled:opacity-30"
              title="Undo (Ctrl+Z)"
            >
              <Undo2 className="w-3.5 h-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              disabled={!canRedo}
              onClick={handleRedo}
              className="h-7 w-7 p-0 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] disabled:opacity-30"
              title="Redo (Ctrl+Y)"
            >
              <Redo2 className="w-3.5 h-3.5" />
            </Button>
            <div className="w-px h-4 bg-[hsl(var(--bolt-border))] mx-1" />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
              title={`Version History (${history.length} commits)`}
            >
              <History className="w-3.5 h-3.5" />
            </Button>
          </div>

          {/* Generate Project */}
          {onGenerateProject && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onGenerateProject}
              className="h-8 px-3 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]  bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-700 hover:to-purple-700"
              title="Generate Complete Project"
            >
              <Sparkles className="w-4 h-4 mr-1.5" />
              <span className="text-sm font-semibold">Generate Project</span>
            </Button>
          )}

          {/* Export Project */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleExportProject}
            disabled={!currentProject || currentProject.files.length === 0}
            className="h-8 px-3 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] disabled:opacity-30"
            title="Download Project as ZIP"
          >
            <Download className="w-4 h-4 mr-1.5" />
            <span className="text-sm">Export</span>
          </Button>

          {/* Token Balance */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))]">
            <Sparkles className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
            <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
              {tokenBalance.toLocaleString()} tokens
            </span>
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
          >
            <Settings className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - AI Chat Interaction */}
        <div className={`flex flex-col ${isSidebarOpen ? 'w-[30%]' : 'w-full'} transition-all border-r border-[hsl(var(--bolt-border))]`}>
          {/* Messages */}
          <div className="flex-1 overflow-y-auto scrollbar-thin">
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
                    thinkingSteps={message.type === 'assistant' ? message.thinkingSteps : undefined}
                    fileOperations={message.type === 'assistant' ? message.fileOperations : undefined}
                  />
                ))}

                {/* PlanView - Show current tasks and thinking steps */}
                <PlanView />

                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Input */}
          <div className="border-t border-[hsl(var(--bolt-border))]">
            <ChatInput onSend={onSendMessage} isLoading={isLoading} />
          </div>
        </div>

        {/* Right Panel - Monaco Code Editor & Preview */}
        {isSidebarOpen && (
          <div className="w-[70%] flex flex-col border-l border-[hsl(var(--bolt-border))]">
            {/* Tab Content */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {activeTab === 'code' && (
                <>
                  {/* Code Editor Area */}
                  <div className={`flex ${showTerminal ? 'flex-1' : 'h-full'} overflow-hidden`}>
                    {/* File Explorer */}
                    <div className="w-64 flex-shrink-0">
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

                    {/* Code Editor - Simplified (no props needed) */}
                    <div className="flex-1">
                      <CodeEditor />
                    </div>
                  </div>

                  {/* Terminal Panel - Below Code Editor */}
                  {showTerminal && (
                    <div
                      className="border-t border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] flex flex-col"
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

                      {/* Terminal Content - xterm.js */}
                      <div className="flex-1 overflow-hidden bg-[hsl(var(--bolt-bg-primary))]">
                        <XTerminal
                          logs={terminalLogs}
                          onCommand={(cmd) => {
                            // Add command to terminal logs
                            addLog({
                              type: 'command',
                              content: cmd
                            })
                            // Execute command (can be extended to call backend)
                            addLog({
                              type: 'output',
                              content: `Command received: ${cmd}`
                            })
                          }}
                        />
                      </div>
                    </div>
                  )}
                </>
              )}

              {activeTab === 'preview' && (
                <div className="flex-1">
                  {livePreview ? (
                    livePreview
                  ) : (
                    <div className="h-full flex items-center justify-center text-[hsl(var(--bolt-text-secondary))]">
                      <div className="text-center">
                        <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p className="text-sm">Start building to see live preview</p>
                      </div>
                    </div>
                  )}
                </div>
              )}
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
    </div>
  )
}
