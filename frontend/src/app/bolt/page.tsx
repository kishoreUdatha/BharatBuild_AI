'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { BoltLayout } from '@/components/bolt/BoltLayout'
import { LivePreview } from '@/components/bolt/LivePreview'
import { ProjectGenerationModal } from '@/components/bolt/ProjectGenerationModal'
import { useChat } from '@/hooks/useChat'
import { useTokenBalance } from '@/hooks/useTokenBalance'
import { useProject } from '@/hooks/useProject'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api-client'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

export default function BoltPage() {
  const { messages, sendMessage, stopGeneration, isStreaming } = useChat()
  const { balance, setBalance } = useTokenBalance()
  const { currentProject, createNewProject } = useProject()
  const { currentWorkspace, setCurrentWorkspace, setCurrentProject, getWorkspace } = useWorkspaceStore()
  const { isAuthenticated, isLoading: authLoading, checkAuth } = useAuth()
  const router = useRouter()
  const [isGenerationModalOpen, setIsGenerationModalOpen] = useState(false)
  const [isServerRunning, setIsServerRunning] = useState(false)
  const [serverUrl, setServerUrl] = useState<string | undefined>(undefined)
  const [isMounted, setIsMounted] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)

  // Convert project files to FileNode format for BoltLayout
  // Files already have full paths from projectStore, just extract the name for display
  const convertToFileNode = (file: NonNullable<typeof currentProject>['files'][0]): FileNode => {
    return {
      name: file.path.split('/').pop() || file.path,  // Display name is last part of path
      path: file.path,  // Full path already stored
      type: file.type,
      children: file.children?.map(child => convertToFileNode(child)),
      content: file.content
    }
  }

  // Wrap files in a project root folder for proper display
  const projectName = currentProject?.name || 'Project'
  const projectFiles = currentProject?.files || []

  const files: FileNode[] = projectFiles.length > 0
    ? [{
        name: projectName,
        path: projectName,
        type: 'folder' as const,
        children: projectFiles.map(f => convertToFileNode(f))
      }]
    : []

  // Build file contents object for LivePreview
  const fileContents: Record<string, string> = {}
  const extractFileContents = (files: NonNullable<typeof currentProject>['files'] | undefined) => {
    files?.forEach(file => {
      if (file.type === 'file' && file.content) {
        fileContents[file.path] = file.content
        console.log('[BoltPage] Extracted file for preview:', file.path, '(', file.content.length, 'chars)')
      }
      if (file.children) {
        extractFileContents(file.children)
      }
    })
  }
  if (currentProject?.files) {
    console.log('[BoltPage] Current project files count:', currentProject.files.length)
    extractFileContents(currentProject.files)
    console.log('[BoltPage] Total files for preview:', Object.keys(fileContents).length)
  }

  // Set mounted state on client side
  useEffect(() => {
    setIsMounted(true)
  }, [])

  // Check authentication on mount
  useEffect(() => {
    if (!isMounted) return

    // Check if user is authenticated
    if (!checkAuth()) {
      // Not authenticated - redirect to login
      sessionStorage.setItem('redirectAfterLogin', '/bolt')
      router.push('/login')
      return
    }
    setAuthChecked(true)
  }, [isMounted, checkAuth, router])

  // Load token balance, workspace, and check for initial prompt on mount
  useEffect(() => {
    if (!isMounted || !authChecked) return

    loadTokenBalance()

    // Check for workspace/project from session storage (from landing page)
    const storedWorkspaceId = sessionStorage.getItem('workspaceId')
    const storedProjectId = sessionStorage.getItem('projectId')

    if (storedWorkspaceId && storedProjectId) {
      // Load workspace from store
      const workspace = getWorkspace(storedWorkspaceId)
      if (workspace) {
        setCurrentWorkspace(workspace)
        setCurrentProject(storedProjectId)
      }
      // Clear session storage after loading
      sessionStorage.removeItem('workspaceId')
      sessionStorage.removeItem('projectId')
    }

    // Create default project if none exists
    if (!currentProject) {
      const projectName = currentWorkspace?.projects[0]?.name || 'My Project'
      const projectDesc = currentWorkspace?.projects[0]?.description || 'AI-generated application'
      createNewProject(projectName, projectDesc)
    }

    // Check if there's an initial prompt from landing page
    const initialPrompt = sessionStorage.getItem('initialPrompt')
    if (initialPrompt) {
      sessionStorage.removeItem('initialPrompt') // Clear it so it doesn't run again
      // Wait a bit for the component to fully render
      setTimeout(() => {
        sendMessage(initialPrompt)
      }, 500)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isMounted, authChecked]) // Run after mount and auth check

  const loadTokenBalance = async () => {
    try {
      const balance = await apiClient.getTokenBalance()
      setBalance(balance.remaining_tokens)
    } catch (error) {
      console.error('Failed to load token balance:', error)
    }
  }

  // Prevent hydration mismatch by not rendering until mounted and auth checked
  if (!isMounted || !authChecked) {
    return (
      <div className="h-screen flex items-center justify-center bg-[hsl(var(--bolt-bg-primary))]">
        <div className="animate-pulse text-[hsl(var(--bolt-text-secondary))]">Loading...</div>
      </div>
    )
  }

  return (
    <>
      <BoltLayout
        onSendMessage={sendMessage}
        onStopGeneration={stopGeneration}
        messages={messages}
        files={files}
        isLoading={isStreaming}
        tokenBalance={balance}
        livePreview={
          <LivePreview
            files={fileContents}
            isServerRunning={isServerRunning}
            serverUrl={serverUrl}
          />
        }
        onGenerateProject={() => setIsGenerationModalOpen(true)}
        onServerStart={(url) => {
          setServerUrl(url)
          setIsServerRunning(true)
        }}
        onServerStop={() => {
          setServerUrl(undefined)
          setIsServerRunning(false)
        }}
      />

      <ProjectGenerationModal
        isOpen={isGenerationModalOpen}
        onClose={() => setIsGenerationModalOpen(false)}
        onServerStart={(url) => {
          // Auto-run started the server - update preview!
          console.log('[BoltPage] Server started via auto-run:', url)
          setServerUrl(url)
          setIsServerRunning(true)
        }}
      />
    </>
  )
}
