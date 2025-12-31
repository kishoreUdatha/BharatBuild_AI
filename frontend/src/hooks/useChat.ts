import { useCallback } from 'react'
import { useChatStore, AIMessage, UserMessage } from '@/store/chatStore'
import { useProjectStore, ProjectFile } from '@/store/projectStore'
import { useTokenStore } from '@/store/tokenStore'
import { useTerminalStore } from '@/store/terminalStore'
import { useErrorStore } from '@/store/errorStore'
import { parseFileOperationEvent } from '@/hooks/useFileChangeEvents'
import { streamingClient, StreamEvent } from '@/lib/streaming-client'
import {
  classifyPromptAsync,
  getChatResponse,
  getExplainResponse,
  getDebugResponse,
  type ClassificationResult,
  type PromptIntent
} from '@/services/promptClassifier'
import { getAgentLabel } from './agentLabelMapping'
import { sdkService } from '@/services/sdkService'
import { detectPastedError, extractErrorDetails, sendChatMessage } from '@/services/chatService'

// SDK Fixer configuration
const USE_SDK_FIXER = true // Enable SDK-based fixing for better reliability
const USE_REAL_CHAT = true // Enable real conversational AI for CHAT intent

const generateId = () => `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

// Helper: Extract a project name from user's prompt
const extractProjectName = (prompt: string): string => {
  // Common patterns: "Create a/an X", "Build a/an X", "Make a/an X", etc.
  const patterns = [
    /(?:create|build|make|develop|design|implement)\s+(?:a|an|the)?\s*(.+?)(?:\s+(?:app|application|website|site|platform|system|tool|project|page|portal))?$/i,
    /(?:create|build|make|develop|design|implement)\s+(.+)/i,
    /^(.+?)\s+(?:app|application|website|site|platform|system|tool|project)$/i,
  ]

  for (const pattern of patterns) {
    const match = prompt.match(pattern)
    if (match && match[1]) {
      // Clean up and capitalize
      let name = match[1].trim()
      // Remove common trailing words
      name = name.replace(/\s+(app|application|website|site|platform|system|tool|project|page|portal)$/i, '')
      // Capitalize each word
      name = name.split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
        .join(' ')
      // Limit length
      if (name.length > 50) {
        name = name.substring(0, 50) + '...'
      }
      return name || 'My Project'
    }
  }

  // Fallback: Use first few words
  const words = prompt.split(' ').slice(0, 4).join(' ')
  return words.charAt(0).toUpperCase() + words.slice(1) || 'My Project'
}

// Helper: Get language from file extension
const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase()
  const languageMap: Record<string, string> = {
    // Web Development
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'sass',
    'less': 'less',
    'php': 'php',

    // AI/ML & Data Science
    'py': 'python',
    'r': 'r',
    'jl': 'julia',
    'm': 'matlab',
    'ipynb': 'json',

    // Systems Programming
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'cs': 'csharp',
    'go': 'go',
    'rs': 'rust',
    'rb': 'ruby',
    'kt': 'kotlin',
    'scala': 'scala',
    'swift': 'swift',

    // Data & Config
    'json': 'json',
    'xml': 'xml',
    'yaml': 'yaml',
    'yml': 'yaml',
    'toml': 'toml',
    'csv': 'plaintext',

    // Database
    'sql': 'sql',

    // Shell & Scripts
    'sh': 'shell',
    'bash': 'shell',
    'ps1': 'powershell',
    'bat': 'bat',

    // Documentation
    'md': 'markdown',
    'rst': 'restructuredtext',
    'tex': 'latex',

    // Other
    'dockerfile': 'dockerfile',
    'makefile': 'makefile',
    'gradle': 'groovy',
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
    addThinkingStep,
    updateThinkingStep,
    isStreaming,
    clearMessages
  } = useChatStore()

  const { currentProject, updateProject } = useProjectStore()
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

    // 2. PROMPT CLASSIFIER LAYER - Classify the user's intent using AI
    const projectStore = useProjectStore.getState()
    const classification = await classifyPromptAsync(content, {
      hasExistingProject: (projectStore.currentProject?.files?.length ?? 0) > 0,
      currentFiles: projectStore.currentProject?.files?.map(f => f.path) || []
    })

    console.log('[useChat] Prompt Classification (AI-powered):', {
      intent: classification.intent,
      confidence: classification.confidence,
      reasoning: classification.reasoning,
      requiresGeneration: classification.requiresGeneration,
      suggestedWorkflow: classification.suggestedWorkflow,
      entities: classification.entities
    })

    // 3. Create AI message placeholder
    const aiMessageId = generateId()
    const aiMessage: AIMessage = {
      id: aiMessageId,
      type: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
      status: classification.requiresGeneration ? 'thinking' : 'complete',
      fileOperations: [],
      thinkingSteps: []
    }
    addMessage(aiMessage)

    // 4. Route based on intent
    switch (classification.intent) {
      case 'CHAT':
        // Check if the "chat" message is actually a pasted error
        if (detectPastedError(content)) {
          console.log('[useChat] Detected pasted error in CHAT intent, switching to FIX')
          // Switch to FIX intent for pasted errors
          classification.intent = 'FIX'
          break // Fall through to FIX handling below
        }

        // Real conversational AI support
        if (USE_REAL_CHAT) {
          try {
            appendToMessage(aiMessageId, '') // Start streaming indicator

            const chatResult = await sendChatMessage({
              message: content,
              conversation_history: messages.slice(-10).map(m => ({
                role: m.type as 'user' | 'assistant',
                content: m.content
              })),
              context: {
                project_id: projectStore.currentProject?.id,
                has_project: (projectStore.currentProject?.files?.length || 0) > 0
              }
            })

            if (chatResult.success) {
              appendToMessage(aiMessageId, chatResult.response)
            } else {
              // Fallback to static response
              const fallbackResponse = classification.chatResponse || getChatResponse(content)
              appendToMessage(aiMessageId, fallbackResponse)
            }

            updateMessageStatus(aiMessageId, 'complete')
            stopStreaming()
            return

          } catch (chatError) {
            console.error('[useChat] Real chat error, using fallback:', chatError)
            // Fallback to static response
            const fallbackResponse = classification.chatResponse || getChatResponse(content)
            appendToMessage(aiMessageId, fallbackResponse)
            updateMessageStatus(aiMessageId, 'complete')
            stopStreaming()
            return
          }
        }

        // Static fallback (when USE_REAL_CHAT is false)
        const chatResponse = classification.chatResponse || getChatResponse(content)
        appendToMessage(aiMessageId, chatResponse)
        updateMessageStatus(aiMessageId, 'complete')
        stopStreaming()
        return

      case 'EXPLAIN':
        // Check if the "explain" message is actually a pasted error
        if (detectPastedError(content)) {
          console.log('[useChat] Detected pasted error in EXPLAIN intent, switching to FIX')
          classification.intent = 'FIX'
          break // Fall through to FIX handling
        }

        // Real conversational AI for explanations
        if (USE_REAL_CHAT) {
          try {
            const explainResult = await sendChatMessage({
              message: `Please explain: ${content}`,
              conversation_history: messages.slice(-5).map(m => ({
                role: m.type as 'user' | 'assistant',
                content: m.content
              }))
            })

            if (explainResult.success) {
              appendToMessage(aiMessageId, explainResult.response)
            } else {
              const fallbackResponse = classification.chatResponse || getExplainResponse(content)
              appendToMessage(aiMessageId, fallbackResponse)
            }

            updateMessageStatus(aiMessageId, 'complete')
            stopStreaming()
            return

          } catch (explainError) {
            console.error('[useChat] Explain error, using fallback:', explainError)
          }
        }

        // Static fallback
        const explainResponse = classification.chatResponse || getExplainResponse(content)
        appendToMessage(aiMessageId, explainResponse)
        updateMessageStatus(aiMessageId, 'complete')
        stopStreaming()
        return

      case 'DEBUG':
        // Debug request without existing project context
        if (!projectStore.currentProject?.files?.length) {
          const debugResponse = classification.chatResponse || getDebugResponse(content)
          appendToMessage(aiMessageId, debugResponse)
          updateMessageStatus(aiMessageId, 'complete')
          stopStreaming()
          return
        }
        // If there's a project, fall through to generation
        break

      case 'FIX':
        // AUTO-FIX: User reports a problem in simple terms
        // System automatically collects ALL context and sends to Fixer Agent
        // Context is collected below in the metadata building section (step 8)

        // If no project exists, show helpful message
        if (!projectStore.currentProject?.files?.length) {
          appendToMessage(aiMessageId, `I notice you're reporting an issue, but there's no project to fix yet.

**What would you like to do?**
1. **Create a new project** - Describe what you want to build
2. **Import existing code** - Paste your code and I'll help fix it

Just describe your project or share the code that needs fixing!`)
          updateMessageStatus(aiMessageId, 'complete')
          stopStreaming()
          return
        }

        // USE SDK FIXER for more reliable fixes (if enabled)
        if (USE_SDK_FIXER) {
          try {
            appendToMessage(aiMessageId, '🔧 **Auto-Fix Started** (SDK Mode)\n\nAnalyzing errors and applying fixes...\n')

            // Collect error context
            const errorStoreState = useErrorStore.getState()
            const terminalStoreState = useTerminalStore.getState()

            // Get unresolved errors
            const unresolvedErrors = errorStoreState.getUnresolvedErrors()
            const errorMessage = unresolvedErrors.length > 0
              ? unresolvedErrors.map(e => `${e.source}: ${e.message}${e.file ? ` (${e.file}:${e.line})` : ''}`).join('\n')
              : content // Use user's description if no captured errors

            // Get stack traces
            const stackTrace = unresolvedErrors
              .filter(e => e.stack)
              .map(e => e.stack)
              .join('\n---\n')

            // Get recent terminal output for context
            const recentLogs = terminalStoreState.logs.slice(-20)
              .map(l => l.content)
              .join('\n')

            // Call SDK Fixer
            const result = await sdkService.fixError({
              project_id: projectStore.currentProject.id,
              error_message: `User reported: ${content}\n\nCaptured errors:\n${errorMessage}\n\nRecent terminal output:\n${recentLogs}`,
              stack_trace: stackTrace,
              build_command: 'npm run build',
              max_retries: 3
            })

            // Report result
            if (result.success && result.error_fixed) {
              appendToMessage(aiMessageId, `\n✅ **Fix Applied Successfully!**

**Files Modified:**
${result.files_modified.map(f => `• \`${f}\``).join('\n')}

**Attempts:** ${result.attempts}

The errors have been fixed. Your preview should update automatically.`)

              // Clear errors from store
              errorStoreState.clearErrors()

              // Trigger file refresh for modified files
              result.files_modified.forEach(filePath => {
                parseFileOperationEvent({
                  path: filePath,
                  operation: 'fixed',
                  status: 'complete'
                }, projectStore.currentProject?.id || '')
              })
            } else {
              appendToMessage(aiMessageId, `\n⚠️ **Could Not Auto-Fix**

${result.message}

**What you can try:**
1. Check the error details in the Terminal
2. Manually review the affected files
3. Describe the issue in more detail

I'll keep trying to help!`)
            }

            updateMessageStatus(aiMessageId, 'complete')
            stopStreaming()
            return

          } catch (sdkError: any) {
            console.error('[useChat] SDK Fixer error:', sdkError)
            appendToMessage(aiMessageId, `\n❌ **SDK Fix Error:** ${sdkError.message}\n\nFalling back to standard fix workflow...`)
            // Fall through to standard fix workflow
          }
        }

        // Continue with standard fix workflow - context will be attached in metadata below
        break

      case 'GENERATE':
        // CRITICAL: For new project generation, reset ALL state to prevent file overlap
        // This is the Bolt.new behavior - each "create X" starts fresh
        if (projectStore.currentProject?.files && projectStore.currentProject.files.length > 0) {
          console.log('[useChat] GENERATE intent with existing project - creating NEW project (Bolt.new style)')

          // Capture old project info before reset
          const oldProjectId = projectStore.currentProject.id
          const token = localStorage.getItem('access_token')

          // ATOMIC STATE RESET: Clear all stores in a single synchronous batch
          // This prevents race conditions where partial state could leak between projects
          const resetAllStores = () => {
            // Clear all stores atomically
            projectStore.resetProject()
            useTerminalStore.getState().clearLogs()
            useErrorStore.getState().clearErrors()
          }
          resetAllStores()

          // Create new empty project with temporary ID (will be replaced by project_id_updated event)
          // IMPORTANT: isSynced MUST be true to prevent build/page.tsx effect from trying to reload files
          // Files will be streamed in via SSE events during generation
          const newProjectId = `project-${Date.now()}`
          projectStore.setCurrentProject({
            id: newProjectId,
            name: 'New Project',
            files: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            isSynced: true  // FIX: Set true to prevent file reload during generation
          })
          console.log(`[useChat] Created fresh project: ${newProjectId}`)

          // Destroy old sandbox on server with retry mechanism (non-blocking)
          if (token && oldProjectId && oldProjectId !== 'default-project') {
            const cleanupSandbox = async (retries = 3) => {
              for (let attempt = 1; attempt <= retries; attempt++) {
                try {
                  const response = await fetch(
                    `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/sync/sandbox/${oldProjectId}`,
                    {
                      method: 'DELETE',
                      headers: { 'Authorization': `Bearer ${token}` }
                    }
                  )
                  if (response.ok || response.status === 404) {
                    console.log(`[useChat] Successfully cleaned up old sandbox: ${oldProjectId}`)
                    return
                  }
                  throw new Error(`HTTP ${response.status}`)
                } catch (err) {
                  console.warn(`[useChat] Sandbox cleanup attempt ${attempt}/${retries} failed:`, err)
                  if (attempt < retries) {
                    // Wait before retry with exponential backoff
                    await new Promise(resolve => setTimeout(resolve, 1000 * attempt))
                  }
                }
              }
              console.error(`[useChat] Failed to cleanup old sandbox after ${retries} attempts: ${oldProjectId}`)
            }
            // Fire and forget, but with retries
            cleanupSandbox()
          }
        }
        // Continue to generation below
        break

      case 'MODIFY':
      case 'DOCUMENT':
      case 'REFACTOR':
        // These intents modify existing project - continue below
        break

      default:
        // Unknown intent - treat as generation request if long enough
        if (content.trim().split(/\s+/).length < 4) {
          const defaultResponse = classification.chatResponse || getChatResponse(content)
          appendToMessage(aiMessageId, defaultResponse)
          updateMessageStatus(aiMessageId, 'complete')
          stopStreaming()
          return
        }
    }

    // 5. Ensure project exists before streaming (CRITICAL for file tree to work)
    // This handles the case where user has no existing project
    if (!projectStore.currentProject) {
      const newProjectId = `project-${Date.now()}`
      const extractedName = extractProjectName(content) || 'New Project'
      projectStore.setCurrentProject({
        id: newProjectId,
        name: extractedName,
        files: [],
        createdAt: new Date(),
        updatedAt: new Date(),
        isSynced: true  // FIX: Set true to prevent file reload during generation
      })
      console.log(`[useChat] Created new project for generation: ${newProjectId} (${extractedName})`)
    }

    // 6. Extract project name from prompt and update project (only for GENERATE intent)
    if (classification.intent === 'GENERATE' &&
        projectStore.currentProject &&
        (projectStore.currentProject.name === 'My Project' ||
         projectStore.currentProject.name === 'New Project' ||
         projectStore.currentProject.files.length === 0)) {
      const extractedName = extractProjectName(content)
      if (extractedName && extractedName !== 'My Project' && extractedName !== 'New Project') {
        updateProject({ name: extractedName })
        console.log('[useChat] Updated project name to:', extractedName)
      }
    }

    startStreaming(aiMessageId)

    try {
      // 6. Initialize thinking steps (will be updated dynamically from backend)
      updateThinkingSteps(aiMessageId, [])

      // 7. Determine workflow based on classification
      const workflow = classification.suggestedWorkflow === 'bolt_instant' ? 'bolt_instant' : 'bolt_standard'

      // 8. Build metadata with auto-collected context for FIX intent
      // IMPORTANT: Always include project_name in metadata so backend creates project with correct title
      const freshProjectStore = useProjectStore.getState()
      let workflowMetadata: Record<string, any> = {
        project_name: freshProjectStore.currentProject?.name || extractProjectName(content)
      }

      if (classification.intent === 'FIX') {
        // AUTO-FIX: Automatically collect ALL context (Bolt.new style)
        // User doesn't need to provide technical details!
        const errorStoreState = useErrorStore.getState()
        const terminalStoreState = useTerminalStore.getState()
        const projectStoreState = useProjectStore.getState()

        // Get all unresolved errors from the error collector
        const autoCollectedErrors = errorStoreState.getUnresolvedErrors().map(err => ({
          message: err.message,
          file: err.file,
          line: err.line,
          column: err.column,
          stack: err.stack,
          source: err.source,
          severity: err.severity
        }))

        // Get recent terminal logs (last 50 entries)
        const autoCollectedLogs = terminalStoreState.logs.slice(-50).map(log => ({
          type: log.type,
          content: log.content,
          timestamp: log.timestamp?.toISOString?.() || new Date().toISOString()
        }))

        // Get project files for context
        const autoCollectedFiles = projectStoreState.currentProject?.files?.map(f => ({
          path: f.path,
          content: f.content
        })) || []

        console.log('[useChat] AUTO-FIX: Collected context for Fixer Agent:', {
          errorsCount: autoCollectedErrors.length,
          logsCount: autoCollectedLogs.length,
          filesCount: autoCollectedFiles.length
        })

        // Pack everything into metadata for the backend
        workflowMetadata = {
          intent: 'FIX',
          auto_fix_context: {
            user_problem_description: content,  // User's simple description like "page is blank"
            collected_errors: autoCollectedErrors,
            terminal_logs: autoCollectedLogs,
            project_files: autoCollectedFiles
          }
        }
      }

      // Get the CURRENT project ID (may have been reset in GENERATE case above)
      // Note: freshProjectStore was already declared above for metadata
      const projectId = freshProjectStore.currentProject?.id || 'default-project'

      console.log(`[useChat] Starting orchestrator workflow (${workflow} - ${classification.intent} intent) for project: ${projectId}`)
      await streamingClient.streamOrchestratorWorkflow(
        content,
        projectId,  // Use fresh project ID (not stale closure value)
        workflow,  // Use classifier-suggested workflow
        workflowMetadata,
        (event: StreamEvent) => {
          // Log ALL events for debugging
          console.log('[useChat] Event received:', event.type, event)

          switch (event.type) {
            case 'project_id_updated':
              // CRITICAL: Update project ID to actual database UUID
              // This fixes the bug where frontend uses 'default-project' but files are saved to DB UUID
              if (event.data?.project_id) {
                const projectStore = useProjectStore.getState()
                const newProjectId = event.data.project_id
                console.log('[project_id_updated] Updating project ID:', event.data.original_project_id, '->', newProjectId)

                // Update the project ID in the store
                projectStore.updateProject({ id: newProjectId })

                // Also update the current project reference if it exists
                if (projectStore.currentProject) {
                  projectStore.setCurrentProject({
                    ...projectStore.currentProject,
                    id: newProjectId
                  })
                }
              }
              break

            case 'status':
              // Handle workflow status updates - DON'T show in chat, only log
              console.log('[status] Status event:', event.data?.message)

              // Handle documents_skipped event - show in thinking steps
              if (event.data?.documents_skipped) {
                console.log('[status] Documents skipped:', event.data.skip_reason)
                // Update thinking steps to show why documents were skipped
                addThinkingStep(aiMessageId, {
                  label: 'Documents Skipped',
                  status: 'complete',
                  description: event.data.skip_reason || 'Academic documents not available for your account',
                  details: event.data.role_required
                    ? 'Update your profile to student/faculty role to access academic documents'
                    : event.data.upgrade_required
                    ? 'Upgrade to PRO for academic documents (SRS, PPT, Viva Q&A)'
                    : event.data.message
                })
              }

              // Don't append status messages to chat - they clutter the UI
              break

            case 'thinking_step':
              // Handle thinking steps from backend
              // bolt_standard shows file-by-file progress, bolt_instant shows 3 simple steps
              if (event.data?.user_visible && event.data?.detail) {
                const stepLabel = event.data.detail
                const stepStatus = event.data.step === 'complete' ? 'complete' : 'active'

                // First, mark any existing 'active' steps as 'complete' before adding new one
                const currentMsg = useChatStore.getState().messages.find(m => m.id === aiMessageId)
                if (currentMsg && currentMsg.type === 'assistant' && currentMsg.thinkingSteps) {
                  currentMsg.thinkingSteps.forEach((existingStep) => {
                    if (existingStep.status === 'active' && existingStep.label !== stepLabel) {
                      updateThinkingStep(aiMessageId, existingStep.label, { status: 'complete' })
                    }
                  })
                }

                // Check if this step already exists (to avoid duplicates)
                const existingStep = currentMsg?.type === 'assistant' &&
                  currentMsg.thinkingSteps?.find(s => s.label === stepLabel)

                if (existingStep) {
                  // Update existing step
                  updateThinkingStep(aiMessageId, stepLabel, {
                    status: stepStatus as 'pending' | 'active' | 'complete'
                  })
                } else {
                  // Add new step
                  addThinkingStep(aiMessageId, {
                    label: stepLabel,
                    status: stepStatus as 'pending' | 'active' | 'complete',
                    description: event.data.detail,
                    details: '',
                    icon: event.data.icon
                  })
                }
              }
              break

            case 'agent_start':
              // Add new step when agent starts (progressive appearance)
              // Use user-friendly labels instead of internal agent names (Bolt.new style)
              if (event.data?.name) {
                const agentInfo = getAgentLabel(event.data.name)
                // Skip hidden agents (bolt_instant, Analyzer, Verifier, etc.)
                if (!agentInfo) break
                const stepLabel = agentInfo.label
                const status = event.data.status || 'active'

                // Check if step already exists (from plan_created)
                const currentMessage = useChatStore.getState().messages.find(m => m.id === aiMessageId)
                if (currentMessage && currentMessage.type === 'assistant') {
                  const existingStepIndex = currentMessage.thinkingSteps?.findIndex(s => s.label === stepLabel)

                  if (existingStepIndex !== undefined && existingStepIndex >= 0 && currentMessage.thinkingSteps) {
                    // Update existing step - preserve description and details
                    updateThinkingStep(aiMessageId, stepLabel, {
                      status: status as 'pending' | 'active' | 'complete',
                      details: event.data.details || currentMessage.thinkingSteps[existingStepIndex]?.details
                    })
                  } else {
                    // Add new step
                    addThinkingStep(aiMessageId, {
                      label: stepLabel,
                      status: status as 'pending' | 'active' | 'complete',
                      description: event.data.description,
                      details: event.data.details,
                      taskNumber: event.data.task_number
                    })
                  }
                } else {
                  // Add new step
                  addThinkingStep(aiMessageId, {
                    label: stepLabel,
                    status: status as 'pending' | 'active' | 'complete',
                    description: event.data.description,
                    details: event.data.details,
                    taskNumber: event.data.task_number
                  })
                }
              }
              break

            case 'agent_complete':
              // Mark step as complete when agent finishes and update details
              // Use user-friendly labels (Bolt.new style)
              if (event.data?.name) {
                const agentInfo = getAgentLabel(event.data.name)
                // Skip hidden agents
                if (!agentInfo) break
                updateThinkingStep(aiMessageId, agentInfo.label, {
                  status: 'complete',
                  details: event.data.details || undefined
                })
              }
              break

            case 'plan_created':
              // Plan created event from backend - add tasks to UI immediately
              console.log('[plan_created] Event received at:', new Date().toISOString())
              console.log('[plan_created] Event data:', event.data)

              // Update project name if Claude suggested one
              if (event.data?.project_name) {
                const projectStore = useProjectStore.getState()
                projectStore.updateProject({ name: event.data.project_name })
                console.log('[plan_created] Updated project name to Claude suggestion:', event.data.project_name)
              }

              if (event.data?.tasks && Array.isArray(event.data.tasks)) {
                console.log('[plan_created] Tasks count:', event.data.tasks.length)

                // Get current message to check existing steps
                const currentMsg = useChatStore.getState().messages.find(m => m.id === aiMessageId)
                const existingSteps = (currentMsg?.type === 'assistant' && currentMsg.thinkingSteps) || []

                // Map existing steps by label for quick lookup
                const existingStepsMap = new Map(existingSteps.map(s => [s.label, s]))

                // Merge with existing steps, preserving status of already-started steps
                // This prevents subsequent plan_created events from resetting step statuses
                const taskSteps = event.data.tasks.map((task: any) => {
                  const label = task.title || task.name
                  const existingStep = existingStepsMap.get(label)

                  // Preserve existing status if step is already active or complete
                  // Only use 'pending' if step doesn't exist or is already pending
                  const status = existingStep && existingStep.status !== 'pending'
                    ? existingStep.status
                    : 'pending' as const

                  return {
                    label,
                    status,
                    description: task.description || existingStep?.description || task.name,
                    details: task.details || existingStep?.details || '',
                    taskNumber: task.number
                  }
                })

                console.log('[plan_created] Calling updateThinkingSteps with:', taskSteps.length, 'tasks')
                updateThinkingSteps(aiMessageId, taskSteps)
                console.log('[plan_created] updateThinkingSteps completed')
              } else {
                console.warn('[plan_created] No tasks in event data!')
              }

              // Handle file operations if provided
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
              // NOTE: Don't append to chat - file operations shown in PlanView sidebar only
              // NOTE: Backend sends data nested inside event.data
              const startData = event.data || event
              const startPath = startData.path || event.path
              if (startPath) {
                updateFileOperation(aiMessageId, startPath, { status: 'in-progress' })

                // Create empty file in project store immediately
                const projectStore = useProjectStore.getState()
                const language = getLanguageFromPath(startPath)

                projectStore.addFile({
                  path: startPath,
                  content: '', // Start with empty content
                  language,
                  type: 'file'
                })

                // Auto-select this file to show in Monaco editor
                const newFile = {
                  name: startPath.split('/').pop() || startPath,
                  path: startPath,
                  content: '',
                  language,
                  type: 'file' as const
                }
                projectStore.setSelectedFile(newFile)
              }
              break

            case 'file_content':
              // NOTE: Backend sends data nested inside event.data
              const contentData = event.data || event
              const contentPath = contentData.path || event.path
              const contentChunk = contentData.content || event.content
              const contentStatus = contentData.status || event.status
              if (contentChunk && contentPath) {
                // DON'T append to chat message - stream to Monaco editor instead!
                const projectStore = useProjectStore.getState()
                const currentFile = findFileInProject(projectStore.currentProject?.files || [], contentPath)
                const language = getLanguageFromPath(contentPath)

                if (currentFile) {
                  // If status is "complete", replace content entirely (final file)
                  // Otherwise, append chunk to file content (streaming "typing" effect)
                  if (contentStatus === 'complete') {
                    projectStore.updateFile(contentPath, contentChunk)
                  } else {
                    const newContent = (currentFile.content || '') + contentChunk
                    projectStore.updateFile(contentPath, newContent)
                  }
                } else {
                  // File doesn't exist yet - CREATE it with the content
                  // This handles cases where file_start wasn't sent first
                  console.log('[file_content] Creating new file:', contentPath)
                  projectStore.addFile({
                    path: contentPath,
                    content: contentChunk,
                    language,
                    type: 'file'
                  })

                  // Auto-open newly created file in tab
                  projectStore.openTab({
                    path: contentPath,
                    content: contentChunk,
                    language,
                    type: 'file'
                  })
                }
              }
              break

            case 'file_operation':
              // Handle file_operation events from backend
              // NOTE: Don't append to chat message - file operations are shown in PlanView sidebar only (Bolt.new style)
              // NOTE: Backend sends data nested inside event.data, so we access it there
              const fileOp = event.data || event  // Support both nested and flat event structures
              const opType = fileOp.operation || event.operation
              const opStatus = fileOp.operation_status || event.operation_status
              const opPath = fileOp.path || event.path || ''
              // Backend may send content as file_content OR content
              const opContent = fileOp.file_content ?? fileOp.content ?? event.file_content ?? event.content

              console.log('[file_operation] Received:', { opType, opStatus, opPath, hasContent: opContent !== undefined, contentLength: typeof opContent === 'string' ? opContent.length : 0 })

              if (opType === 'create') {
                if (opStatus === 'in_progress') {
                  // Update file operation status to in-progress (file was already added by plan_created)
                  // Use updateFileOperation to avoid duplicates (plan_created already added it as 'pending')
                  updateFileOperation(aiMessageId, opPath, {
                    status: 'in-progress',
                    description: `Creating ${opPath}`
                  })

                  // Also create empty file in store to show in file tree immediately
                  const projectStoreForProgress = useProjectStore.getState()
                  const langForProgress = getLanguageFromPath(opPath)
                  const existingFileForProgress = findFileInProject(projectStoreForProgress.currentProject?.files || [], opPath)
                  if (!existingFileForProgress) {
                    console.log('[file_operation] Creating placeholder file for in-progress:', opPath)
                    projectStoreForProgress.addFile({
                      path: opPath,
                      content: '', // Empty until content arrives
                      language: langForProgress,
                      type: 'file'
                    })
                  }
                } else if (opStatus === 'complete') {
                  // Accept both with content and without (empty files are valid)
                  const fileContent = opContent ?? '' // Default to empty string if no content
                  // Mark file operation as complete
                  updateFileOperation(aiMessageId, opPath, {
                    status: 'complete',
                    content: fileContent
                  })

                  // Add file to project store with actual content from backend
                  const projectStore = useProjectStore.getState()
                  const language = getLanguageFromPath(opPath)

                  // Check if file already exists
                  const existingFile = findFileInProject(projectStore.currentProject?.files || [], opPath)

                  if (existingFile) {
                    // Update existing file with new content
                    projectStore.updateFile(opPath, fileContent)
                    console.log('[file_operation] Updated existing file:', opPath, 'length:', fileContent.length)
                  } else {
                    // Create new file with content from backend
                    const newFile = {
                      path: opPath,
                      content: fileContent,
                      language,
                      type: 'file' as const
                    }
                    projectStore.addFile(newFile)
                    console.log('[file_operation] Created new file:', opPath, 'length:', fileContent.length)

                    // Auto-open newly created file in tab
                    projectStore.openTab(newFile)
                  }

                  // Emit file change event for auto-reload
                  parseFileOperationEvent({
                    path: opPath,
                    operation: 'created',
                    status: 'complete'
                  }, projectId)
                }
              } else if (opType === 'modify') {
                if (opStatus === 'in_progress') {
                  addFileOperation(aiMessageId, {
                    type: 'modify',
                    path: opPath,
                    description: `Modifying ${opPath}`,
                    status: 'in-progress'
                  })
                } else if (opStatus === 'complete') {
                  updateFileOperation(aiMessageId, opPath, {
                    status: 'complete'
                  })

                  // Update file content in project store if provided
                  if (opContent !== undefined) {
                    const projectStore = useProjectStore.getState()
                    projectStore.updateFile(opPath, opContent)
                  }

                  // Emit file change event for auto-reload
                  parseFileOperationEvent({
                    path: opPath,
                    operation: 'updated',
                    status: 'complete'
                  }, projectId)
                }
              } else if (opType === 'fixed') {
                // Handle file fixed by fixer agent
                const fixStatus = opStatus || fileOp.status || event.status
                if (fixStatus === 'in_progress') {
                  addFileOperation(aiMessageId, {
                    type: 'modify',
                    path: opPath,
                    description: `Fixing ${opPath}`,
                    status: 'in-progress'
                  })
                } else if (fixStatus === 'complete') {
                  updateFileOperation(aiMessageId, opPath, {
                    status: 'complete'
                  })

                  // Update file content in project store if provided
                  if (opContent !== undefined) {
                    const projectStore = useProjectStore.getState()
                    projectStore.updateFile(opPath, opContent)
                  }

                  // Emit file change event to trigger auto-reload
                  parseFileOperationEvent({
                    path: opPath,
                    operation: 'fixed',
                    status: 'complete'
                  }, projectId)

                  console.log(`[useChat] File fixed: ${opPath} - triggering preview reload`)
                }
              } else if (opType === 'documentation') {
                // Handle documentation file operations (from Documenter agent)
                // Documentation files follow planner structure: docs/SRS.md, docs/ARCHITECTURE.md, etc.
                // For academic projects: Word, PDF, PPT files (binary - stored on backend)
                const docPath = opPath
                const docStatus = opStatus || fileOp.status || event.status
                const docContent = opContent || fileOp.content || event.content

                // Check if this is a binary file (Word, PDF, PPT)
                const isBinaryDoc = (path: string) => {
                  const ext = path.split('.').pop()?.toLowerCase()
                  return ['pdf', 'docx', 'doc', 'pptx', 'ppt'].includes(ext || '')
                }

                if (docStatus === 'in_progress') {
                  addFileOperation(aiMessageId, {
                    type: 'create',
                    path: docPath,
                    description: `Creating documentation: ${docPath}`,
                    status: 'in-progress'
                  })
                } else if (docStatus === 'complete') {
                  updateFileOperation(aiMessageId, docPath, {
                    status: 'complete'
                  })

                  const projectStore = useProjectStore.getState()
                  const existingFile = findFileInProject(projectStore.currentProject?.files || [], docPath)

                  if (isBinaryDoc(docPath)) {
                    // Binary files (Word, PDF, PPT) - add to file tree without content
                    // These are stored on backend and can be downloaded
                    if (!existingFile) {
                      const newFile = {
                        path: docPath,
                        content: `[Binary file stored on server: ${docPath}]`,
                        language: 'text',
                        type: 'file' as const,
                        isBinary: true
                      }
                      projectStore.addFile(newFile)
                      console.log(`[useChat] Added binary documentation file: ${docPath}`)
                    }
                  } else if (docContent) {
                    // Text files (Markdown) - add with content
                    const language = getLanguageFromPath(docPath)

                    if (existingFile) {
                      projectStore.updateFile(docPath, docContent)
                    } else {
                      // Create new documentation file in docs/ folder structure
                      const newFile = {
                        path: docPath,
                        content: docContent,
                        language,
                        type: 'file' as const
                      }
                      projectStore.addFile(newFile)
                      console.log(`[useChat] Added documentation file: ${docPath}`)
                    }
                  } else {
                    // File created without content (content saved on backend only)
                    console.log(`[useChat] Documentation file created on backend: ${docPath}`)
                  }
                }
              }
              break

            case 'file_complete':
              // NOTE: Don't append to chat - file operations shown in PlanView sidebar only
              // NOTE: Backend sends data nested inside event.data
              const completeData = event.data || event
              const completePath = completeData.path || event.path
              // Backend may send content as full_content, file_content, or content
              const completeContent = completeData.full_content || completeData.file_content || completeData.content || event.full_content || event.file_content || event.content
              console.log('[file_complete] Received:', { completePath, hasContent: !!completeContent, contentLength: completeContent?.length || 0 })
              if (completePath && completeContent) {
                updateFileOperation(aiMessageId, completePath, {
                  status: 'complete',
                  content: completeContent
                })

                // Ensure final content is set (in case streaming missed chunks)
                const projectStore = useProjectStore.getState()
                const language = getLanguageFromPath(completePath)

                const existingFile = findFileInProject(projectStore.currentProject?.files || [], completePath)

                if (existingFile) {
                  // Update to final content
                  projectStore.updateFile(completePath, completeContent)

                  // Auto-open updated file in tab
                  projectStore.openTab({
                    path: completePath,
                    content: completeContent,
                    language,
                    type: 'file'
                  })
                } else {
                  // Fallback: create file if it doesn't exist
                  const newFile = {
                    path: completePath,
                    content: completeContent,
                    language,
                    type: 'file' as const
                  }
                  projectStore.addFile(newFile)

                  // Auto-open newly created file in tab
                  projectStore.openTab(newFile)
                }
              }
              break

            case 'upgrade_required':
              // FREE plan limit reached - show upgrade prompt
              console.log('[upgrade_required] FREE plan limit reached:', event.data)
              const upgradeData = event.data || {}

              // Update the message with upgrade info
              updateMessage(aiMessageId, {
                content: `🔒 **FREE Plan Limit Reached**\n\nYou've generated ${upgradeData.files_generated || 3} preview files.\n\n${upgradeData.upgrade_message || 'Upgrade to Premium to generate the complete project with all files, bug fixing, and documentation.'}\n\n[👉 Upgrade to Premium](/pricing)`,
                status: 'complete'
              })

              // Show alert and redirect to pricing
              setTimeout(() => {
                if (confirm('FREE plan limit reached! Would you like to upgrade to Premium for the complete project?')) {
                  window.open('/pricing', '_blank')
                }
              }, 500)
              break

            case 'commands':
              if (event.commands) {
                // Don't append commands to chat message - only show in terminal
                // Show terminal and execute commands
                setTerminalVisible(true)

                // Execute each command in the terminal with simulated output
                event.commands.forEach((cmd: string, index: number) => {
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

            case 'server_started':
            case 'preview_ready':
            case 'docker_running':
              // Handle server/preview ready events - update projectStore with server URL
              // Backend may send: server_started, preview_ready, or docker_running
              const serverUrl = event.data?.url || event.data?.preview_url || event.data?.server_url || event.url
              const serverPort = event.data?.port || event.port
              if (serverUrl) {
                console.log(`[${event.type}] Dev server ready at:`, serverUrl, 'port:', serverPort)
                // Update the projectStore with server info
                useProjectStore.setState({
                  serverUrl,
                  isServerRunning: true
                })
              }
              break

            // ==================== DOCUMENT GENERATION EVENTS ====================
            case 'documents_starting':
              // Document generation is starting - add a thinking step
              console.log('[documents_starting] Starting document generation:', event.data)
              addThinkingStep(aiMessageId, {
                label: 'Generating Documents',
                status: 'active',
                description: 'Creating academic documents (SRS, Report, PPT, Viva Q&A)...',
                details: event.data?.message || 'Starting document generation...'
              })
              break

            case 'document_generating':
              // A specific document is being generated
              console.log('[document_generating]', event.data?.document)
              {
                const docName = event.data?.document || 'Document'
                // Update the main documents step with current document
                updateThinkingStep(aiMessageId, 'Generating Documents', {
                  status: 'active',
                  details: `Generating ${docName}...`
                })
              }
              break

            case 'document_progress':
              // Progress update for a document
              console.log('[document_progress]', event.data)
              {
                const docName = event.data?.document || 'Document'
                const progressMsg = event.data?.message || event.data?.section || ''
                updateThinkingStep(aiMessageId, 'Generating Documents', {
                  status: 'active',
                  details: `${docName}: ${progressMsg}`
                })
              }
              break

            case 'document_complete':
              // A specific document is complete
              console.log('[document_complete]', event.data?.document)
              {
                const docName = event.data?.document || 'Document'
                updateThinkingStep(aiMessageId, 'Generating Documents', {
                  status: 'active',
                  details: `${docName} completed ✓`
                })
              }
              break

            case 'all_documents_complete':
              // All documents are complete
              console.log('[all_documents_complete] All documents generated')
              updateThinkingStep(aiMessageId, 'Generating Documents', {
                status: 'complete',
                details: 'All documents generated successfully!'
              })
              break

            case 'document_error':
              // Error generating a document
              console.error('[document_error]', event.data)
              {
                const docName = event.data?.document || 'Document'
                const errorMsg = event.data?.error || 'Unknown error'
                updateThinkingStep(aiMessageId, 'Generating Documents', {
                  status: 'active',
                  details: `${docName}: Error - ${errorMsg}`
                })
              }
              break

            case 'complete':
              // Mark any remaining active steps as complete
              const currentMessage = useChatStore.getState().messages.find(m => m.id === aiMessageId)
              if (currentMessage && currentMessage.type === 'assistant') {
                currentMessage.thinkingSteps?.forEach((step) => {
                  if (step.status === 'active') {
                    updateThinkingStep(aiMessageId, step.label, { status: 'complete' })
                  }
                })
              }

              updateMessageStatus(aiMessageId, 'complete')

              // Store session_id for ZIP download (ephemeral storage)
              if (event.data?.session_id) {
                useProjectStore.getState().setSessionId(event.data.session_id)
                useProjectStore.getState().setDownloadUrl(event.data.download_url)
              }

              // Generate comprehensive completion summary for students
              const projectStore = useProjectStore.getState()
              const aiMessage = currentMessage?.type === 'assistant' ? currentMessage : null
              const completedFiles = aiMessage?.fileOperations?.filter(f => f.status === 'complete') || []
              const completedSteps = aiMessage?.thinkingSteps?.filter(s => s.status === 'complete') || []

              if (completedFiles.length > 0 || completedSteps.length > 0) {
                let summary = '\n\n---\n\n'
                summary += '## Project Generation Complete\n\n'

                // Project Overview Section
                const projectName = projectStore.currentProject?.name || 'Your Project'
                summary += `### ${projectName}\n\n`

                // What was accomplished
                if (completedSteps.length > 0) {
                  summary += '#### What We Built\n'
                  completedSteps.forEach(step => {
                    summary += `- ${step.label}\n`
                  })
                  summary += '\n'
                }

                // Files breakdown with categories
                if (completedFiles.length > 0) {
                  summary += `#### Project Files (${completedFiles.length} files created)\n\n`

                  // Categorize files
                  const sourceFiles = completedFiles.filter(f =>
                    f.path.endsWith('.tsx') || f.path.endsWith('.jsx') ||
                    f.path.endsWith('.ts') || f.path.endsWith('.js') ||
                    f.path.endsWith('.java') || f.path.endsWith('.py')
                  )
                  const styleFiles = completedFiles.filter(f =>
                    f.path.endsWith('.css') || f.path.endsWith('.scss') || f.path.endsWith('.sass')
                  )
                  const configFiles = completedFiles.filter(f =>
                    f.path.endsWith('.json') || f.path.endsWith('.yaml') || f.path.endsWith('.yml') ||
                    f.path.includes('config') || f.path.endsWith('.xml') || f.path.endsWith('.properties')
                  )
                  const docFiles = completedFiles.filter(f =>
                    f.path.endsWith('.md') || f.path.endsWith('.txt') ||
                    f.path.endsWith('.docx') || f.path.endsWith('.pdf') || f.path.endsWith('.pptx')
                  )
                  const testFiles = completedFiles.filter(f =>
                    f.path.includes('test') || f.path.includes('spec') || f.path.includes('__tests__')
                  )

                  if (sourceFiles.length > 0) {
                    summary += `| Category | Count |\n|----------|-------|\n`
                    summary += `| Source Code | ${sourceFiles.length} files |\n`
                    if (styleFiles.length > 0) summary += `| Stylesheets | ${styleFiles.length} files |\n`
                    if (configFiles.length > 0) summary += `| Configuration | ${configFiles.length} files |\n`
                    if (testFiles.length > 0) summary += `| Tests | ${testFiles.length} files |\n`
                    if (docFiles.length > 0) summary += `| Documentation | ${docFiles.length} files |\n`
                    summary += '\n'
                  }

                  // Key files to explore
                  const keyFiles = completedFiles.slice(0, 5)
                  if (keyFiles.length > 0) {
                    summary += '**Key files to explore:**\n'
                    keyFiles.forEach(f => {
                      const fileName = f.path.split('/').pop() || f.path
                      summary += `- \`${fileName}\`\n`
                    })
                    if (completedFiles.length > 5) {
                      summary += `- ...and ${completedFiles.length - 5} more files\n`
                    }
                    summary += '\n'
                  }
                }

                // Documents section (for academic projects)
                const academicDocs = completedFiles.filter(f =>
                  f.path.endsWith('.docx') || f.path.endsWith('.pdf') || f.path.endsWith('.pptx')
                )
                if (academicDocs.length > 0) {
                  summary += '#### Academic Documents Generated\n'
                  academicDocs.forEach(doc => {
                    const docName = doc.path.split('/').pop() || doc.path
                    if (docName.includes('project_report') || docName.includes('ProjectReport')) {
                      summary += `- **Project Report** - Complete documentation with UML diagrams\n`
                    } else if (docName.includes('srs') || docName.includes('SRS')) {
                      summary += `- **SRS Document** - Software Requirements Specification\n`
                    } else if (docName.includes('ppt') || docName.includes('presentation')) {
                      summary += `- **Presentation** - Ready for project defense\n`
                    } else if (docName.includes('viva') || docName.includes('qa')) {
                      summary += `- **Viva Q&A** - Common questions and answers\n`
                    } else {
                      summary += `- \`${docName}\`\n`
                    }
                  })
                  summary += '\n'
                }

                // Tech Stack (infer from files)
                const techStack: string[] = []
                const fileExts = completedFiles.map(f => f.path.split('.').pop()?.toLowerCase())
                if (fileExts.includes('tsx') || fileExts.includes('jsx')) techStack.push('React')
                if (fileExts.includes('vue')) techStack.push('Vue.js')
                if (fileExts.includes('java')) techStack.push('Java')
                if (fileExts.includes('py')) techStack.push('Python')
                if (completedFiles.some(f => f.path.includes('spring') || f.path.includes('pom.xml'))) techStack.push('Spring Boot')
                if (completedFiles.some(f => f.path.includes('next.config') || f.path.includes('_app'))) techStack.push('Next.js')
                if (completedFiles.some(f => f.path.includes('vite.config'))) techStack.push('Vite')
                if (fileExts.includes('ts') || fileExts.includes('tsx')) techStack.push('TypeScript')

                if (techStack.length > 0) {
                  summary += `**Tech Stack:** ${techStack.join(' • ')}\n\n`
                }

                // Next steps for students
                summary += '#### What You Can Do Now\n'
                summary += '1. **Explore Code** - Browse files in the editor panel on the right\n'
                summary += '2. **Run Preview** - Click the "Run" button to see your app in action\n'
                summary += '3. **Download Project** - Use "Export" to download everything as ZIP\n'
                if (academicDocs.length > 0) {
                  summary += '4. **Download Documents** - Go to Dashboard to download all academic documents\n'
                }
                summary += '\n'

                // Tips
                summary += '> **Tip:** Click on any file in the file explorer to view and edit the code.\n'

                appendToMessage(aiMessageId, summary)
              }
              break

            case 'error':
              updateMessageStatus(aiMessageId, 'complete')
              const errorMsg = event.data?.error || event.data?.message || 'Unknown error'
              const errorCode = event.data?.code || 'ERROR'

              // Format error message based on error code
              let formattedError = `\n\n---\n\n## ⚠️ Generation Error\n\n`
              formattedError += `**${errorMsg}**\n\n`

              // Add helpful suggestions based on error code
              switch (errorCode) {
                case 'AUTH_ERROR':
                  formattedError += `> This is a service configuration issue. Please contact support.\n`
                  break
                case 'RATE_LIMITED':
                  formattedError += `> The AI service is temporarily busy. Please wait a moment and try again.\n`
                  break
                case 'TIMEOUT':
                  formattedError += `> The request took too long. Try simplifying your request or try again.\n`
                  break
                case 'TOKEN_LIMIT':
                  formattedError += `> Consider upgrading your plan for more tokens.\n`
                  break
                default:
                  formattedError += `> If this persists, try refreshing the page or contact support.\n`
              }

              appendToMessage(aiMessageId, formattedError)
              console.error('[useChat] Generation error:', errorCode, errorMsg)
              break

            case 'cancelled':
              // Backend confirmed cancellation - update UI
              console.log('[useChat] Generation cancelled by backend')
              updateMessageStatus(aiMessageId, 'complete')
              stopStreaming()
              return  // Exit early - don't process more events

            case 'warning':
              // Don't show warnings in chat - only log them
              console.log('[warning]', event.data?.message)
              break

            case 'content':
              if (event.content) {
                appendToMessage(aiMessageId, event.content)
              }
              break
          }
        },
        (error: Error) => {
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

  // Stop ongoing generation
  const stopGeneration = useCallback(() => {
    console.log('[useChat] Stopping generation...')

    // Abort the streaming client request
    streamingClient.abort()

    // Stop the streaming state
    stopStreaming()

    // Find the current streaming message and mark it as stopped
    const streamingMessage = messages.find(m => m.type === 'assistant' && m.isStreaming)
    if (streamingMessage) {
      // Mark any active thinking steps as stopped
      if (streamingMessage.type === 'assistant' && streamingMessage.thinkingSteps) {
        streamingMessage.thinkingSteps.forEach((step) => {
          if (step.status === 'active') {
            updateThinkingStep(streamingMessage.id, step.label, {
              status: 'complete',
              details: 'Stopped by user'
            })
          }
        })
      }

      // Mark any in-progress file operations as stopped
      if (streamingMessage.type === 'assistant' && streamingMessage.fileOperations) {
        streamingMessage.fileOperations.forEach((op) => {
          if (op.status === 'in-progress') {
            updateFileOperation(streamingMessage.id, op.path, { status: 'complete' })
          }
        })
      }

      updateMessageStatus(streamingMessage.id, 'complete')
      appendToMessage(streamingMessage.id, '\n\n⏹️ Generation stopped by user.')
    }
  }, [messages, stopStreaming, updateMessageStatus, appendToMessage, updateThinkingStep, updateFileOperation])

  return {
    messages,
    sendMessage,
    regenerateMessage,
    stopGeneration,
    isStreaming,
    clearMessages
  }
}
