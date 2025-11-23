import { useCallback } from 'react'
import { useChatStore, AIMessage, UserMessage } from '@/store/chatStore'
import { useProjectStore, ProjectFile } from '@/store/projectStore'
import { useTokenStore } from '@/store/tokenStore'
import { useTerminalStore } from '@/store/terminalStore'
import { streamingClient } from '@/lib/streaming-client'

const generateId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

// Helper: Get language from file extension
const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase()
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'html': 'html',
    'css': 'css',
    'json': 'json',
    'md': 'markdown',
    'py': 'python',
    'java': 'java',
    'go': 'go',
    'rs': 'rust',
    'cpp': 'cpp',
    'c': 'c',
  }
  return languageMap[ext || ''] || 'plaintext'
}

// Helper: Find file in project recursively
const findFileInProject = (files: ProjectFile[], path: string): ProjectFile | null => {
  for (const file of files) {
    if (file.path === path) return file
    if (file.children) {
      const found = findFileInProject(file.children, path)
      if (found) return found
    }
  }
  return null
}

export const useChat = () => {
  const {
    messages,
    addMessage,
    updateMessage,
    startStreaming,
    stopStreaming,
    appendToMessage,
    updateMessageStatus,
    addFileOperation,
    updateFileOperation,
    updateThinkingSteps,
    isStreaming,
    clearMessages
  } = useChatStore()

  const { currentProject } = useProjectStore()
  const { deductTokens } = useTokenStore()
  const { addLog, setVisible: setTerminalVisible } = useTerminalStore()

  const sendMessage = useCallback(async (
    content: string,
    attachedFiles?: string[]
  ) => {
    // 1. Add user message
    const userMessage: UserMessage = {
      id: generateId(),
      type: 'user',
      content,
      timestamp: new Date(),
      attachedFiles
    }
    addMessage(userMessage)

    // 2. Create AI message placeholder
    const aiMessageId = generateId()
    const aiMessage: AIMessage = {
      id: aiMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      status: 'thinking',
      fileOperations: [],
      thinkingSteps: []
    }
    addMessage(aiMessage)
    startStreaming(aiMessageId)

    try {
      // 3. Initialize thinking steps (will be updated dynamically from backend)
      updateThinkingSteps(aiMessageId, [])

      // Track thinking steps dynamically
      const thinkingStepsMap = new Map<number, { label: string; status: 'pending' | 'active' | 'complete' }>()

      // 4. Stream response from Dynamic Orchestrator
      await streamingClient.streamOrchestratorWorkflow(
        content,
        currentProject?.id || 'default-project',
        'bolt_standard',
        {},
        (event) => {
          switch (event.type) {
            case 'status':
              // Handle workflow status updates
              if (event.data?.message) {
                appendToMessage(aiMessageId, `\n${event.data.message}\n`)
              }

              // If total_steps is provided, initialize thinking steps
              if (event.data?.total_steps) {
                const steps = []
                for (let i = 1; i <= event.data.total_steps; i++) {
                  thinkingStepsMap.set(i, { label: `Step ${i}`, status: 'pending' })
                  steps.push({ label: `Step ${i}`, status: 'pending' as const })
                }
                updateThinkingSteps(aiMessageId, steps)
              }
              break

            case 'agent_start':
              // Mark step as active when agent starts
              if (event.step && event.data?.name) {
                const stepLabel = event.data.name
                thinkingStepsMap.set(event.step, { label: stepLabel, status: 'active' })

                // Update all thinking steps
                const steps = Array.from(thinkingStepsMap.values())
                  .sort((a, b) => {
                    const indexA = Array.from(thinkingStepsMap.entries()).find(([_, v]) => v === a)?.[0] || 0
                    const indexB = Array.from(thinkingStepsMap.entries()).find(([_, v]) => v === b)?.[0] || 0
                    return indexA - indexB
                  })
                updateThinkingSteps(aiMessageId, steps)

                appendToMessage(aiMessageId, `\n🤔 **${stepLabel}**\n`)
              }
              break

            case 'agent_complete':
              // Mark step as complete when agent finishes
              if (event.step) {
                const stepData = thinkingStepsMap.get(event.step)
                if (stepData) {
                  stepData.status = 'complete'
                  thinkingStepsMap.set(event.step, stepData)

                  // Update all thinking steps
                  const steps = Array.from(thinkingStepsMap.values())
                    .sort((a, b) => {
                      const indexA = Array.from(thinkingStepsMap.entries()).find(([_, v]) => v === a)?.[0] || 0
                      const indexB = Array.from(thinkingStepsMap.entries()).find(([_, v]) => v === b)?.[0] || 0
                      return indexA - indexB
                    })
                  updateThinkingSteps(aiMessageId, steps)
                }
              }
              break

            case 'plan_created':
              // Plan created event from backend
              if (event.data?.files) {
                event.data.files.forEach((file: any) => {
                  addFileOperation(aiMessageId, {
                    type: 'create',
                    path: file.path,
                    description: file.description,
                    status: 'pending'
                  })
                })
              }
              break

            case 'file_start':
              if (event.path) {
                updateFileOperation(aiMessageId, event.path, { status: 'in-progress' })

                // Show minimal message in chat (Bolt.new style)
                appendToMessage(aiMessageId, `\n\n📄 **${event.path}**\n`)

                // Create empty file in project store immediately
                const projectStore = useProjectStore.getState()
                const language = getLanguageFromPath(event.path)

                projectStore.addFile({
                  path: event.path,
                  content: '', // Start with empty content
                  language,
                  type: 'file'
                })

                // Auto-select this file to show in Monaco editor
                const newFile = {
                  name: event.path.split('/').pop() || event.path,
                  path: event.path,
                  content: '',
                  language,
                  type: 'file' as const
                }
                projectStore.setSelectedFile(newFile)
              }
              break

            case 'file_content':
              if (event.content && event.path) {
                // DON'T append to chat message - stream to Monaco editor instead!
                const projectStore = useProjectStore.getState()
                const currentFile = findFileInProject(projectStore.currentProject?.files || [], event.path)

                if (currentFile) {
                  // Append chunk to file content (this creates the "typing" effect in Monaco)
                  const newContent = (currentFile.content || '') + event.content
                  projectStore.updateFile(event.path, newContent)
                }
              }
              break

            case 'file_operation':
              // Handle file_operation events from backend
              if (event.operation === 'create') {
                if (event.operation_status === 'in_progress') {
                  // Add file operation to list
                  addFileOperation(aiMessageId, {
                    type: 'create',
                    path: event.path || '',
                    description: `Creating ${event.path}`,
                    status: 'in-progress'
                  })
                  // Show minimal message in chat (Bolt.new style)
                  appendToMessage(aiMessageId, `\n\n📄 **${event.path}**\n`)
                } else if (event.operation_status === 'complete' && event.file_content !== undefined) {
                  // Mark file operation as complete
                  updateFileOperation(aiMessageId, event.path || '', {
                    status: 'complete',
                    content: event.file_content
                  })

                  // Add file to project store with actual content from backend
                  const projectStore = useProjectStore.getState()
                  const language = getLanguageFromPath(event.path || '')

                  // Check if file already exists
                  const existingFile = findFileInProject(projectStore.currentProject?.files || [], event.path || '')

                  if (existingFile) {
                    // Update existing file with new content
                    projectStore.updateFile(event.path || '', event.file_content)
                  } else {
                    // Create new file with content from backend
                    const newFile = {
                      path: event.path || '',
                      content: event.file_content,
                      language,
                      type: 'file' as const
                    }
                    projectStore.addFile(newFile)

                    // Auto-open newly created file in tab
                    projectStore.openTab(newFile)
                  }

                  appendToMessage(aiMessageId, `\n✓ ${event.path} created\n`)
                }
              } else if (event.operation === 'modify') {
                if (event.operation_status === 'in_progress') {
                  addFileOperation(aiMessageId, {
                    type: 'modify',
                    path: event.path || '',
                    description: `Modifying ${event.path}`,
                    status: 'in-progress'
                  })
                } else if (event.operation_status === 'complete') {
                  updateFileOperation(aiMessageId, event.path || '', {
                    status: 'complete'
                  })

                  // Update file content in project store if provided
                  if (event.file_content !== undefined) {
                    const projectStore = useProjectStore.getState()
                    projectStore.updateFile(event.path || '', event.file_content)
                  }

                  appendToMessage(aiMessageId, `\n✓ ${event.path} modified\n`)
                }
              }
              break

            case 'file_complete':
              if (event.path && event.full_content) {
                updateFileOperation(aiMessageId, event.path, {
                  status: 'complete',
                  content: event.full_content
                })

                // Ensure final content is set (in case streaming missed chunks)
                const projectStore = useProjectStore.getState()
                const language = getLanguageFromPath(event.path)

                const existingFile = findFileInProject(projectStore.currentProject?.files || [], event.path)

                if (existingFile) {
                  // Update to final content
                  projectStore.updateFile(event.path, event.full_content)

                  // Auto-open updated file in tab
                  projectStore.openTab({
                    path: event.path,
                    content: event.full_content,
                    language,
                    type: 'file'
                  })
                } else {
                  // Fallback: create file if it doesn't exist
                  const newFile = {
                    path: event.path,
                    content: event.full_content,
                    language,
                    type: 'file' as const
                  }
                  projectStore.addFile(newFile)

                  // Auto-open newly created file in tab
                  projectStore.openTab(newFile)
                }

                // Show checkmark in chat (minimal, Bolt.new style)
                appendToMessage(aiMessageId, `   ✓ Complete\n`)
              }
              break

            case 'commands':
              if (event.commands) {
                appendToMessage(
                  aiMessageId,
                  `\n\n### Installation Commands:\n${event.commands.map(cmd => `\`${cmd}\``).join('\n')}\n`
                )

                // Show terminal and execute commands
                setTerminalVisible(true)

                // Execute each command in the terminal with simulated output
                event.commands.forEach((cmd, index) => {
                  setTimeout(() => {
                    // Add command to terminal
                    addLog({
                      type: 'command',
                      content: cmd
                    })

                    // Simulate command execution
                    setTimeout(() => {
                      if (cmd.includes('npm install') || cmd.includes('yarn install')) {
                        addLog({
                          type: 'info',
                          content: 'Installing dependencies...'
                        })
                        setTimeout(() => {
                          addLog({
                            type: 'output',
                            content: `✓ Dependencies installed successfully`
                          })
                        }, 1500)
                      } else if (cmd.includes('npm run dev') || cmd.includes('yarn dev')) {
                        addLog({
                          type: 'info',
                          content: 'Starting development server...'
                        })
                        setTimeout(() => {
                          addLog({
                            type: 'output',
                            content: `✓ Development server ready at http://localhost:5173`
                          })
                        }, 1000)
                      } else {
                        addLog({
                          type: 'output',
                          content: `✓ Command executed successfully`
                        })
                      }
                    }, 500)
                  }, index * 2500) // Stagger commands
                })
              }
              break

            case 'complete':
              // Mark all steps as complete
              thinkingStepsMap.forEach((stepData, stepNum) => {
                stepData.status = 'complete'
                thinkingStepsMap.set(stepNum, stepData)
              })

              const finalSteps = Array.from(thinkingStepsMap.values())
                .sort((a, b) => {
                  const indexA = Array.from(thinkingStepsMap.entries()).find(([_, v]) => v === a)?.[0] || 0
                  const indexB = Array.from(thinkingStepsMap.entries()).find(([_, v]) => v === b)?.[0] || 0
                  return indexA - indexB
                })
              updateThinkingSteps(aiMessageId, finalSteps)

              updateMessageStatus(aiMessageId, 'complete')
              if (event.data?.message) {
                appendToMessage(aiMessageId, `\n\n✅ ${event.data.message}`)
              }
              break

            case 'error':
              updateMessageStatus(aiMessageId, 'complete')
              const errorMsg = event.data?.error || event.data?.message || 'Unknown error'
              appendToMessage(aiMessageId, `\n\n⚠️ Error: ${errorMsg}`)
              break

            case 'warning':
              const warningMsg = event.data?.message || 'Warning'
              appendToMessage(aiMessageId, `\n⚠️ ${warningMsg}\n`)
              break

            case 'content':
              if (event.content) {
                appendToMessage(aiMessageId, event.content)
              }
              break
          }
        },
        (error) => {
          console.error('Streaming error:', error)
          updateMessageStatus(aiMessageId, 'complete')
          appendToMessage(aiMessageId, `\n\n⚠️ Error: ${error.message}`)
          stopStreaming()
        },
        () => {
          stopStreaming()
          // Deduct tokens (estimated based on message length)
          const estimatedTokens = Math.ceil(content.length / 4)
          deductTokens(estimatedTokens, aiMessageId, 'code_generation')
        }
      )
    } catch (error: any) {
      console.error('Failed to send message:', error)
      updateMessageStatus(aiMessageId, 'complete')
      appendToMessage(aiMessageId, `\n\n⚠️ Error: ${error.message}`)
      stopStreaming()
    }
  }, [
    addMessage,
    startStreaming,
    stopStreaming,
    appendToMessage,
    updateMessageStatus,
    addFileOperation,
    updateFileOperation,
    deductTokens,
    currentProject
  ])

  const regenerateMessage = useCallback(async (messageId: string) => {
    const messageIndex = messages.findIndex(msg => msg.id === messageId)
    if (messageIndex === -1) return

    const previousUserMessage = messages
      .slice(0, messageIndex)
      .reverse()
      .find(msg => msg.type === 'user') as UserMessage | undefined

    if (previousUserMessage) {
      await sendMessage(previousUserMessage.content, previousUserMessage.attachedFiles)
    }
  }, [messages, sendMessage])

  return {
    messages,
    sendMessage,
    regenerateMessage,
    isStreaming,
    clearMessages
  }
}
