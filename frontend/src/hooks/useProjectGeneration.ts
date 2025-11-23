import { useState, useCallback } from 'react'
import { streamingClient, StreamEvent } from '@/lib/streaming-client'
import { useProjectStore } from '@/store/projectStore'

export interface ProjectGenerationProgress {
  percent: number
  message: string
  currentStep?: string
  filesCreated: number
  commandsExecuted: number
}

export const useProjectGeneration = () => {
  const [isGenerating, setIsGenerating] = useState(false)
  const [progress, setProgress] = useState<ProjectGenerationProgress>({
    percent: 0,
    message: '',
    filesCreated: 0,
    commandsExecuted: 0,
  })
  const [error, setError] = useState<string | null>(null)

  const { addFile, setCurrentProject, currentProject } = useProjectStore()

  const generateProject = useCallback(
    async (description: string, projectName?: string) => {
      setIsGenerating(true)
      setError(null)
      setProgress({
        percent: 0,
        message: 'Starting project generation...',
        filesCreated: 0,
        commandsExecuted: 0,
      })

      try {
        // Ensure a current project exists BEFORE starting generation
        const store = useProjectStore.getState()
        if (!store.currentProject) {
          const newProject = {
            id: projectName || `project-${Date.now()}`,
            name: projectName || 'Generated Project',
            description,
            files: [],
            createdAt: new Date(),
            updatedAt: new Date(),
          }
          setCurrentProject(newProject)
          // Wait a tick for store to update
          await new Promise(resolve => setTimeout(resolve, 0))
        }

        await streamingClient.streamProjectGeneration(
          description,
          projectName,
          // onEvent callback
          (event: StreamEvent) => {
            handleGenerationEvent(event)
          },
          // onError callback
          (err: Error) => {
            console.error('Project generation error:', err)
            setError(err.message)
            setIsGenerating(false)
          },
          // onComplete callback
          () => {
            setProgress((prev) => ({
              ...prev,
              percent: 100,
              message: 'Project generation complete!',
            }))
            setIsGenerating(false)
          }
        )
      } catch (err: any) {
        console.error('Failed to start project generation:', err)
        setError(err.message || 'Failed to start project generation')
        setIsGenerating(false)
      }
    },
    [setCurrentProject]
  )

  const handleGenerationEvent = useCallback(
    (event: StreamEvent) => {
      switch (event.type) {
        case 'progress':
          setProgress((prev) => ({
            ...prev,
            percent: event.percent || prev.percent,
            message: event.message || prev.message,
          }))
          break

        case 'step_start':
          setProgress((prev) => ({
            ...prev,
            currentStep: event.step,
            message: event.message || `Starting ${event.step}`,
          }))
          break

        case 'step_complete':
          setProgress((prev) => ({
            ...prev,
            message: event.message || `Completed ${event.step}`,
          }))
          break

        case 'file_created':
          if (event.path && event.content) {
            // Add file to project store
            addFile({
              path: event.path,
              content: event.content,
              type: 'file',
              language: getLanguageFromPath(event.path),
            })

            setProgress((prev) => ({
              ...prev,
              filesCreated: prev.filesCreated + 1,
              message: `Created ${event.path}`,
            }))
          }
          break

        case 'command_executed':
          setProgress((prev) => ({
            ...prev,
            commandsExecuted: prev.commandsExecuted + 1,
            message: event.message || 'Executed command',
          }))
          break

        case 'done':
          setProgress((prev) => ({
            ...prev,
            percent: 100,
            message: 'Project generated successfully!',
            filesCreated: event.total_files_created || prev.filesCreated,
            commandsExecuted: event.total_commands_executed || prev.commandsExecuted,
          }))
          break

        case 'error':
          setError(event.message || 'An error occurred')
          setIsGenerating(false)
          break
      }
    },
    [addFile]
  )

  const resetProgress = useCallback(() => {
    setProgress({
      percent: 0,
      message: '',
      filesCreated: 0,
      commandsExecuted: 0,
    })
    setError(null)
  }, [])

  return {
    generateProject,
    isGenerating,
    progress,
    error,
    resetProgress,
  }
}

// Helper: Get language from file extension
const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase()
  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    html: 'html',
    css: 'css',
    json: 'json',
    md: 'markdown',
    py: 'python',
    java: 'java',
    go: 'go',
    rs: 'rust',
    cpp: 'cpp',
    c: 'c',
  }
  return languageMap[ext || ''] || 'plaintext'
}
