'use client'

import { useEffect, useState } from 'react'
import { BoltLayout } from '@/components/bolt/BoltLayout'
import { LivePreview } from '@/components/bolt/LivePreview'
import { ProjectGenerationModal } from '@/components/bolt/ProjectGenerationModal'
import { useChat } from '@/hooks/useChat'
import { useTokenBalance } from '@/hooks/useTokenBalance'
import { useProject } from '@/hooks/useProject'
import { apiClient } from '@/lib/api-client'

interface FileNode {
  name: string
  path?: string
  type: 'file' | 'folder'
  children?: FileNode[]
  content?: string
}

export default function BoltPage() {
  const { messages, sendMessage, isStreaming } = useChat()
  const { balance, setBalance } = useTokenBalance()
  const { currentProject, createNewProject } = useProject()
  const [isGenerationModalOpen, setIsGenerationModalOpen] = useState(false)

  // Convert project files to FileNode format for BoltLayout
  const convertToFileNode = (file: NonNullable<typeof currentProject>['files'][0], parentPath = ''): FileNode => {
    const fullPath = parentPath ? `${parentPath}/${file.path}` : file.path
    return {
      name: file.path.split('/').pop() || file.path,
      path: fullPath,
      type: file.type,
      children: file.children?.map(child => convertToFileNode(child, fullPath)),
      content: file.content
    }
  }

  const files: FileNode[] = currentProject?.files.map(f => convertToFileNode(f)) || []

  // Build file contents object for LivePreview
  const fileContents: Record<string, string> = {}
  const extractFileContents = (files: NonNullable<typeof currentProject>['files'] | undefined) => {
    files?.forEach(file => {
      if (file.type === 'file' && file.content) {
        fileContents[file.path] = file.content
      }
      if (file.children) {
        extractFileContents(file.children)
      }
    })
  }
  if (currentProject?.files) {
    extractFileContents(currentProject.files)
  }

  // Load token balance and check for initial prompt on mount
  useEffect(() => {
    loadTokenBalance()

    // Create default project if none exists
    if (!currentProject) {
      createNewProject('My Project', 'AI-generated application')
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
  }, []) // Run only once on mount

  const loadTokenBalance = async () => {
    try {
      const balance = await apiClient.getTokenBalance()
      setBalance(balance.remaining_tokens)
    } catch (error) {
      console.error('Failed to load token balance:', error)
    }
  }

  return (
    <>
      <BoltLayout
        onSendMessage={sendMessage}
        messages={messages}
        files={files}
        isLoading={isStreaming}
        tokenBalance={balance}
        livePreview={<LivePreview files={fileContents} />}
        onGenerateProject={() => setIsGenerationModalOpen(true)}
      />

      <ProjectGenerationModal
        isOpen={isGenerationModalOpen}
        onClose={() => setIsGenerationModalOpen(false)}
      />
    </>
  )
}
