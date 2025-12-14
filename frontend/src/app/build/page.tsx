'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { BoltLayout } from '@/components/bolt/BoltLayout'
import { LivePreview } from '@/components/bolt/LivePreview'
import { ProjectGenerationModal } from '@/components/bolt/ProjectGenerationModal'
import { useChat } from '@/hooks/useChat'
import { useTokenBalance } from '@/hooks/useTokenBalance'
import { useProject } from '@/hooks/useProject'
import { useProjectSwitch } from '@/hooks/useProjectSwitch'
import { useWorkspaceStore } from '@/store/workspaceStore'
import { useProjectStore } from '@/store/projectStore'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api-client'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

export default function BuildPage() {
  const { messages, sendMessage, stopGeneration, isStreaming } = useChat()
  const { balance, setBalance } = useTokenBalance()
  const { currentProject, createNewProject } = useProject()
  const { switchProject } = useProjectSwitch()
  const { currentWorkspace, setCurrentWorkspace, setCurrentProject, getWorkspace } = useWorkspaceStore()
  const { isAuthenticated, isLoading: authLoading, checkAuth } = useAuth()
  const router = useRouter()
  const [isGenerationModalOpen, setIsGenerationModalOpen] = useState(false)
  const [isServerRunning, setIsServerRunning] = useState(false)
  const [serverUrl, setServerUrl] = useState<string | undefined>(undefined)
  const [isMounted, setIsMounted] = useState(false)
  const [authChecked, setAuthChecked] = useState(false)
  const [projectReloaded, setProjectReloaded] = useState(false)

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
  // Only show files if there's an actual project selected with files
  const projectName = currentProject?.name || 'Project'
  const projectFiles = currentProject?.files || []
  const hasProject = currentProject !== null && currentProject.id !== undefined

  // Only create file tree if we have a project AND it has files
  const files: FileNode[] = (hasProject && projectFiles.length > 0)
    ? [{
        name: projectName,
        path: projectName,
        type: 'folder' as const,
        children: projectFiles.map(f => convertToFileNode(f))
      }]
    : []

  // Build file contents object for LivePreview
  // Only extract if we have a valid project with synced files
  const fileContents: Record<string, string> = {}
  const extractFileContents = (files: NonNullable<typeof currentProject>['files'] | undefined) => {
    files?.forEach(file => {
      if (file.type === 'file' && file.content) {
        fileContents[file.path] = file.content
        console.log('[BuildPage] Extracted file for preview:', file.path, '(', file.content.length, 'chars)')
      }
      if (file.children) {
        extractFileContents(file.children)
      }
    })
  }
  if (hasProject && currentProject?.files && currentProject.files.length > 0) {
    console.log('[BuildPage] Current project files count:', currentProject.files.length)
    extractFileContents(currentProject.files)
    console.log('[BuildPage] Total files for preview:', Object.keys(fileContents).length)
  }

  // Set mounted state on client side
  useEffect(() => {
    setIsMounted(true)
  }, [])

  // Debug: Log when currentProject changes
  useEffect(() => {
    console.log('[BuildPage] currentProject changed:', {
      id: currentProject?.id,
      name: currentProject?.name,
      filesCount: currentProject?.files?.length || 0,
      isSynced: currentProject?.isSynced,
      firstFilePath: currentProject?.files?.[0]?.path || 'NO FILES'
    })
    if (currentProject?.files && currentProject.files.length > 0) {
      console.log('[BuildPage] Files structure:', currentProject.files.map(f => ({
        path: f.path,
        type: f.type,
        childrenCount: f.children?.length || 0
      })))
    }
  }, [currentProject])

  // Debug: Log the files array passed to BoltLayout
  useEffect(() => {
    console.log('[BuildPage] files array for BoltLayout:', files.length, hasProject, projectFiles.length)
  }, [files, hasProject, projectFiles])

  // Check authentication on mount
  useEffect(() => {
    if (!isMounted) return

    // Check if user is authenticated
    if (!checkAuth()) {
      // Not authenticated - redirect to login
      sessionStorage.setItem('redirectAfterLogin', '/build')
      router.push('/login')
      return
    }
    setAuthChecked(true)
  }, [isMounted, checkAuth, router])

  // Reload project files from backend if project exists but isn't synced
  // This handles page refresh where we only persist project ID, not files
  // IMPORTANT: First verify the project exists in the database to avoid loading stale localStorage data
  useEffect(() => {
    if (!isMounted || !authChecked || projectReloaded) return

    const reloadProjectFiles = async () => {
      // If there's a current project that isn't synced and has no files, reload from backend
      if (currentProject && !currentProject.isSynced && currentProject.files.length === 0) {
        console.log('[BuildPage] Verifying project exists in database:', currentProject.id)

        try {
          // FIRST: Verify project exists in database before loading files
          // This prevents loading stale files from sandbox when project was deleted
          const projectExists = await apiClient.get(`/projects/${currentProject.id}/metadata`)
            .then(() => true)
            .catch((err: any) => {
              if (err.response?.status === 404 || err.status === 404) {
                return false
              }
              // For other errors, assume project might exist
              console.warn('[BuildPage] Error checking project existence:', err)
              return true
            })

          if (!projectExists) {
            console.log('[BuildPage] Project not found in database, clearing stale localStorage data')
            // Clear the stale project from localStorage
            const { resetProject } = useProjectStore.getState()
            resetProject()
            setProjectReloaded(true)
            return
          }

          console.log('[BuildPage] Project verified, reloading files from backend:', currentProject.id)
          await switchProject(currentProject.id, {
            loadFiles: true,
            clearTerminal: false,
            clearErrors: false,
            clearChat: false,
            destroyOldSandbox: false,
            projectName: currentProject.name,
            projectDescription: currentProject.description
          })
          console.log('[BuildPage] Project files reloaded successfully')
        } catch (error) {
          console.error('[BuildPage] Failed to reload project files:', error)
          // On error, clear the stale project to avoid showing phantom files
          const { resetProject } = useProjectStore.getState()
          resetProject()
        }
      }
      setProjectReloaded(true)
    }

    reloadProjectFiles()
  }, [isMounted, authChecked, currentProject, projectReloaded, switchProject])

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

    // Don't auto-create a project - let user select from dropdown or create new
    // This prevents showing stale files when no project is explicitly selected

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
          console.log('[BuildPage] onServerStart called with URL:', url)
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
          console.log('[BuildPage] Server started via auto-run:', url)
          setServerUrl(url)
          setIsServerRunning(true)
        }}
      />
    </>
  )
}
