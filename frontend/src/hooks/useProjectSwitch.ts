'use client'

/**
 * Bolt.new-style Project Switching Hook
 *
 * When switching projects, this hook performs COMPLETE teardown:
 *
 * 1. CLEAR OLD PROJECT STATE
 *    - File tree
 *    - Open tabs
 *    - Selected file
 *    - Pending saves
 *
 * 2. CLEAR TERMINAL
 *    - All logs
 *    - End active session
 *    - Reset execution state
 *
 * 3. CLEAR ERRORS
 *    - All collected errors
 *    - Reset fixing state
 *
 * 4. DESTROY OLD SANDBOX
 *    - DELETE /sync/sandbox/{oldProjectId}
 *    - Frees server resources
 *
 * 5. LOAD NEW PROJECT
 *    - GET /sync/files/{newProjectId}
 *    - Fresh file tree from server
 *    - Set as current project
 *
 * This ensures NO state mixing between projects - exactly like Bolt.new!
 */

import { useCallback, useState } from 'react'
import { useProjectStore } from '@/store/projectStore'
import { useTerminalStore } from '@/store/terminalStore'
import { useErrorStore } from '@/store/errorStore'
import { useChatStore } from '@/store/chatStore'
import { apiClient } from '@/lib/api-client'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Type for ProjectFile (matches projectStore)
interface ProjectFile {
  path: string
  content: string
  language: string
  type: 'file' | 'folder'
  children?: ProjectFile[]
}

/**
 * Convert flat file list to hierarchical tree structure
 *
 * Input: [{ path: 'src/App.tsx', content: '...' }, { path: 'package.json', content: '...' }]
 * Output: [
 *   { path: 'package.json', type: 'file', ... },
 *   { path: 'src', type: 'folder', children: [{ path: 'src/App.tsx', type: 'file', ... }] }
 * ]
 */
function buildFileTree(flatFiles: Array<{ path: string; content: string; language?: string }>): ProjectFile[] {
  const root: ProjectFile[] = []

  for (const file of flatFiles) {
    const parts = file.path.split('/')
    let currentLevel = root
    let currentPath = ''

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      currentPath = currentPath ? `${currentPath}/${part}` : part
      const isLastPart = i === parts.length - 1

      if (isLastPart) {
        // It's a file - add it to current level
        currentLevel.push({
          path: file.path,  // Full path for files
          content: file.content || '',
          language: file.language || 'plaintext',
          type: 'file'
        })
      } else {
        // It's a folder - find or create it
        let folder = currentLevel.find(f => f.type === 'folder' && f.path === currentPath)
        if (!folder) {
          folder = {
            path: currentPath,
            content: '',
            language: '',
            type: 'folder',
            children: []
          }
          currentLevel.push(folder)
        }
        currentLevel = folder.children!
      }
    }
  }

  // Sort: folders first, then files, alphabetically
  const sortTree = (items: ProjectFile[]): ProjectFile[] => {
    return items
      .map(item => ({
        ...item,
        children: item.children ? sortTree(item.children) : undefined
      }))
      .sort((a, b) => {
        if (a.type === 'folder' && b.type === 'file') return -1
        if (a.type === 'file' && b.type === 'folder') return 1
        return a.path.localeCompare(b.path)
      })
  }

  return sortTree(root)
}

interface SwitchOptions {
  loadFiles?: boolean      // Load files from backend (default: true)
  loadMessages?: boolean   // Load chat history from backend (default: true)
  clearTerminal?: boolean  // Clear terminal logs (default: true)
  clearErrors?: boolean    // Clear error logs (default: true)
  clearChat?: boolean      // Clear chat messages before loading history (default: true)
  destroyOldSandbox?: boolean  // Delete old sandbox from server (default: true)
  projectName?: string     // Project name/title to use (default: "Project {id}")
  projectDescription?: string  // Project description
}

interface SwitchResult {
  success: boolean
  projectId: string
  fileCount: number
  messageCount: number  // Number of chat messages loaded
  layer: string  // 'sandbox' | 's3' | 'none'
  error?: string
}

export function useProjectSwitch() {
  const [isSwitching, setIsSwitching] = useState(false)
  const [lastSwitchResult, setLastSwitchResult] = useState<SwitchResult | null>(null)

  // Get store actions
  const projectStore = useProjectStore()
  const terminalStore = useTerminalStore()
  const errorStore = useErrorStore()
  const chatStore = useChatStore()

  /**
   * Switch to a different project with FULL ISOLATION
   *
   * This is the Bolt.new-style switch that:
   * - Unmounts old workspace completely
   * - Destroys old sandbox
   * - Clears ALL state (terminal, errors, chat)
   * - Loads fresh file tree from server
   */
  const switchProject = useCallback(async (
    newProjectId: string,
    options: SwitchOptions = {}
  ): Promise<SwitchResult> => {
    const {
      loadFiles = true,
      loadMessages = true,
      clearTerminal = true,
      clearErrors = true,
      clearChat = true,
      destroyOldSandbox = true,
      projectName,
      projectDescription
    } = options

    const oldProjectId = projectStore.currentProject?.id

    console.log(`[ProjectSwitch] Starting switch from "${oldProjectId}" to "${newProjectId}"`)
    setIsSwitching(true)

    try {
      // ============================================================
      // STEP 1: CLEAR ALL OLD STATE (Bolt.new Complete Teardown)
      // ============================================================

      // 1a. Clear project state (file tree, tabs, selected file)
      projectStore.resetProject()
      console.log('[ProjectSwitch] ✓ Cleared project state')

      // 1b. Clear terminal logs and end session
      if (clearTerminal) {
        terminalStore.clearLogs()
        terminalStore.endSession()
        console.log('[ProjectSwitch] ✓ Cleared terminal')
      }

      // 1c. Clear collected errors
      if (clearErrors) {
        errorStore.clearErrors()
        console.log('[ProjectSwitch] ✓ Cleared errors')
      }

      // 1d. Clear chat messages (optional - user might want to keep history)
      if (clearChat) {
        chatStore.clearMessages()
        console.log('[ProjectSwitch] ✓ Cleared chat')
      }

      // ============================================================
      // STEP 2: DESTROY OLD SANDBOX ON SERVER (Free Resources)
      // ============================================================

      if (destroyOldSandbox && oldProjectId && oldProjectId !== newProjectId) {
        try {
          const token = localStorage.getItem('access_token')
          if (token) {
            // Fire and forget - don't block UI
            fetch(`${API_BASE_URL}/sync/sandbox/${oldProjectId}`, {
              method: 'DELETE',
              headers: { 'Authorization': `Bearer ${token}` }
            }).then(res => {
              if (res.ok) {
                console.log(`[ProjectSwitch] ✓ Destroyed old sandbox: ${oldProjectId}`)
              }
            }).catch(err => {
              console.warn('[ProjectSwitch] Failed to destroy old sandbox:', err)
            })
          }
        } catch (err) {
          console.warn('[ProjectSwitch] Error destroying old sandbox:', err)
        }
      }

      // ============================================================
      // STEP 3: LOAD NEW PROJECT FROM SERVER (Fresh File Tree)
      // ============================================================

      let result: SwitchResult = {
        success: false,
        projectId: newProjectId,
        fileCount: 0,
        messageCount: 0,
        layer: 'none'
      }

      if (loadFiles) {
        try {
          // BOLT.NEW STYLE: Use /projects/{id}/metadata endpoint
          // This returns ONLY file tree (no content) for fast loading
          // Content is lazy-loaded when user clicks a file
          console.log(`[ProjectSwitch] Loading project metadata via /projects/${newProjectId}/metadata`)

          let data: any = null
          let useMetadataEndpoint = true

          // Try the new /metadata endpoint first
          try {
            data = await apiClient.get(`/projects/${newProjectId}/metadata`)
            console.log(`[ProjectSwitch] Metadata response:`, data)
          } catch (metadataErr: any) {
            console.warn(`[ProjectSwitch] /metadata endpoint failed, falling back to /sync/files:`, metadataErr)
            useMetadataEndpoint = false

            // Fallback to old /sync/files endpoint (loads content too, but works)
            data = await apiClient.get(`/sync/files/${newProjectId}`)
            console.log(`[ProjectSwitch] Fallback /sync/files response:`, data)
          }

          // Handle response from either endpoint
          // /metadata returns: { success, project_id, project_title, file_tree, total_files, messages_count }
          // /sync/files returns: { success, project_id, tree, total, layer, project_title? }
          const fileTreeData = data.file_tree || data.tree || []
          const totalFiles = data.total_files || data.total || 0
          const projectTitle = data.project_title || projectName || `Project ${newProjectId}`
          const projectDesc = data.project_description || projectDescription

          console.log(`[ProjectSwitch] Processing file data:`, {
            success: data.success,
            fileTreeLength: fileTreeData.length,
            totalFiles,
            projectTitle,
            useMetadataEndpoint,
            layer: data.layer
          })

          if (data.success && fileTreeData.length > 0) {
            // Convert backend tree format to frontend ProjectFile format
            const convertTree = (items: any[]): ProjectFile[] => {
              return items.map((item: any) => ({
                path: item.path,
                // If using /sync/files (fallback), content is included
                // If using /metadata, content is undefined (lazy load)
                content: useMetadataEndpoint ? undefined : (item.content || ''),
                language: item.language || 'plaintext',
                type: item.type === 'folder' ? 'folder' : 'file',
                hash: item.hash,  // For change detection
                size_bytes: item.size_bytes,
                isLoading: false,
                isLoaded: !useMetadataEndpoint,  // Already loaded if from /sync/files
                children: item.children ? convertTree(item.children) : undefined
              }))
            }

            const fileTree = convertTree(fileTreeData)

            console.log(`[ProjectSwitch] Loaded file tree: ${fileTree.length} root items, ${totalFiles} total files`)
            console.log(`[ProjectSwitch] Project: "${projectTitle}" (${data.messages_count || 0} messages)`)

            // Set new project in store with hierarchical tree
            const newProject = {
              id: newProjectId,
              name: projectTitle,
              description: projectDesc,
              files: fileTree,
              createdAt: new Date(data.created_at || Date.now()),
              updatedAt: new Date(data.updated_at || Date.now()),
              isSynced: true
            }

            console.log(`[ProjectSwitch] Setting project in store:`, {
              id: newProject.id,
              name: newProject.name,
              filesCount: newProject.files.length,
              firstFile: newProject.files[0] ? { path: newProject.files[0].path, type: newProject.files[0].type } : null
            })

            projectStore.setCurrentProject(newProject)

            // Verify the store was updated
            const verifyProject = projectStore.currentProject
            console.log(`[ProjectSwitch] Verified store project:`, {
              id: verifyProject?.id,
              name: verifyProject?.name,
              filesCount: verifyProject?.files?.length || 0
            })

            result = {
              success: true,
              projectId: newProjectId,
              fileCount: totalFiles || fileTree.length,
              messageCount: data.messages_count || 0,
              layer: data.layer || 'database'
            }

            console.log(`[ProjectSwitch] ✓ Loaded ${result.fileCount} files from ${result.layer}`)
          } else {
            // No files found - create empty project
            projectStore.setCurrentProject({
              id: newProjectId,
              name: projectTitle,
              description: projectDesc,
              files: [],
              createdAt: new Date(),
              updatedAt: new Date(),
              isSynced: false
            })

            result = {
              success: true,
              projectId: newProjectId,
              fileCount: 0,
              messageCount: 0,
              layer: 'none'
            }

            console.log('[ProjectSwitch] ✓ Project loaded but no files found')
          }
        } catch (err: any) {
          console.warn('[ProjectSwitch] Failed to load project metadata:', err)

          // Fallback: create empty project
          projectStore.setCurrentProject({
            id: newProjectId,
            name: projectName || `Project ${newProjectId}`,
            description: projectDescription,
            files: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            isSynced: false
          })

          result = {
            success: true,  // Still "success" - we have a project, just no files
            projectId: newProjectId,
            fileCount: 0,
            messageCount: 0,
            layer: 'none',
            error: err.message
          }
        }
      } else {
        // loadFiles = false - just create empty project
        projectStore.setCurrentProject({
          id: newProjectId,
          name: projectName || `Project ${newProjectId}`,
          description: projectDescription,
          files: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          isSynced: false
        })

        result = {
          success: true,
          projectId: newProjectId,
          fileCount: 0,
          messageCount: 0,
          layer: 'none'
        }

        console.log('[ProjectSwitch] ✓ Created empty project (loadFiles=false)')
      }

      // ============================================================
      // STEP 4: LOAD CHAT HISTORY FROM SERVER (User prompts + Claude responses)
      // ============================================================

      if (loadMessages) {
        try {
          console.log(`[ProjectSwitch] Loading chat history for project ${newProjectId}`)
          const messagesData = await apiClient.get(`/projects/${newProjectId}/messages`)
          console.log(`[ProjectSwitch] Messages API response:`, messagesData)

          if (messagesData.success && messagesData.messages && messagesData.messages.length > 0) {
            // Convert backend message format to frontend chat format
            // Backend returns: { id, role (user/planner/writer/fixer/assistant), content, created_at }
            // Frontend expects: { id, type (user/assistant), content, timestamp }

            // Helper: Check if content is internal JSON (not displayable)
            const isInternalJson = (content: string): boolean => {
              if (!content) return false
              const trimmed = content.trim()
              // Check if it starts with { and contains internal workflow keys
              if (trimmed.startsWith('{')) {
                try {
                  const parsed = JSON.parse(trimmed)
                  // Internal workflow messages have these keys
                  if (parsed.tasks || parsed.plan || parsed.files || parsed.raw) {
                    return true
                  }
                } catch {
                  // Not valid JSON, might be displayable
                }
              }
              return false
            }

            // Helper: Extract human-readable summary from internal JSON
            const extractSummary = (content: string, role: string): string | null => {
              if (!content) return null
              const trimmed = content.trim()

              try {
                if (trimmed.startsWith('{')) {
                  const parsed = JSON.parse(trimmed)

                  // Plan message - extract project description
                  if (parsed.plan?.raw) {
                    // Try to extract project_description from XML
                    const descMatch = parsed.plan.raw.match(/<project_description>([\s\S]*?)<\/project_description>/)
                    if (descMatch) {
                      return `**Project Plan Created**\n\n${descMatch[1].trim()}`
                    }
                    // Try to extract project_name
                    const nameMatch = parsed.plan.raw.match(/<project_name>([\s\S]*?)<\/project_name>/)
                    if (nameMatch) {
                      return `**Planning: ${nameMatch[1].trim()}**\n\nI've created a plan for your project. The files are being generated...`
                    }
                  }

                  // Tasks message - just note that tasks were created
                  if (parsed.tasks && Array.isArray(parsed.tasks)) {
                    return null  // Skip tasks messages entirely
                  }
                }
              } catch {
                // Not JSON, return as-is
              }

              return null
            }

            const chatMessages = messagesData.messages
              .map((msg: any, index: number) => {
                const content = msg.content || ''

                // Skip internal workflow messages entirely
                if (msg.role !== 'user' && isInternalJson(content)) {
                  const summary = extractSummary(content, msg.role)
                  if (!summary) {
                    return null  // Skip this message
                  }
                  // Use extracted summary instead of raw JSON
                  return {
                    id: msg.id || `loaded-${index}-${Date.now()}`,
                    content: summary,
                    timestamp: new Date(msg.created_at || Date.now()),
                    type: 'assistant' as const,
                    isStreaming: false,
                    status: 'complete' as const
                  }
                }

                const baseMessage = {
                  id: msg.id || `loaded-${index}-${Date.now()}`,
                  content: content,
                  timestamp: new Date(msg.created_at || Date.now())
                }

                // Map backend 'role' to frontend 'type'
                // Only 'user' stays as 'user', all agent roles become 'assistant'
                if (msg.role === 'user') {
                  return {
                    ...baseMessage,
                    type: 'user' as const
                  }
                } else {
                  // All other roles (planner, writer, fixer, assistant, etc.) -> 'assistant'
                  return {
                    ...baseMessage,
                    type: 'assistant' as const,
                    isStreaming: false,
                    status: 'complete' as const
                  }
                }
              })
              .filter((msg): msg is NonNullable<typeof msg> => msg !== null)  // Filter out skipped messages

            // Add messages to chat store
            console.log(`[ProjectSwitch] Setting ${chatMessages.length} messages to chatStore`)
            chatStore.setMessages(chatMessages)
            result.messageCount = chatMessages.length

            console.log(`[ProjectSwitch] ✓ Loaded ${chatMessages.length} chat messages`)
          } else {
            console.log('[ProjectSwitch] No chat history found for project (success:', messagesData.success, ', messages:', messagesData.messages?.length || 0, ')')
          }
        } catch (err: any) {
          console.warn('[ProjectSwitch] Failed to load chat history:', err.message || err)
          // Don't fail the switch - messages are optional
        }
      }

      setLastSwitchResult(result)
      console.log('[ProjectSwitch] Switch complete:', result)
      return result

    } catch (err: any) {
      console.error('[ProjectSwitch] Switch failed:', err)

      const result: SwitchResult = {
        success: false,
        projectId: newProjectId,
        fileCount: 0,
        messageCount: 0,
        layer: 'none',
        error: err.message
      }

      setLastSwitchResult(result)
      return result

    } finally {
      setIsSwitching(false)
    }
  }, [projectStore, terminalStore, errorStore, chatStore])

  /**
   * Create a new empty project (like clicking "New Project" in Bolt.new)
   *
   * Generates a unique project ID and switches to it with empty state
   */
  const createNewProject = useCallback(async (name?: string): Promise<SwitchResult> => {
    const projectId = `project-${Date.now()}`

    const result = await switchProject(projectId, {
      loadFiles: false,  // Don't try to load - it's new
      clearTerminal: true,
      clearErrors: true,
      clearChat: true,
      destroyOldSandbox: true
    })

    // Update project name if provided
    if (name && result.success) {
      projectStore.updateProject({ name })
    }

    console.log(`[ProjectSwitch] Created new project: ${projectId}`)
    return result
  }, [switchProject, projectStore])

  return {
    // State
    isSwitching,
    lastSwitchResult,

    // Actions
    switchProject,
    createNewProject
  }
}
