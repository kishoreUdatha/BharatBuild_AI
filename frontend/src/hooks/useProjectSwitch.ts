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
  clearTerminal?: boolean  // Clear terminal logs (default: true)
  clearErrors?: boolean    // Clear error logs (default: true)
  clearChat?: boolean      // Clear chat messages (default: true)
  destroyOldSandbox?: boolean  // Delete old sandbox from server (default: true)
  projectName?: string     // Project name/title to use (default: "Project {id}")
  projectDescription?: string  // Project description
}

interface SwitchResult {
  success: boolean
  projectId: string
  fileCount: number
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
        layer: 'none'
      }

      if (loadFiles) {
        try {
          // Use /sync/files endpoint which returns hierarchical tree and works reliably
          // The /projects/{id}/load endpoint has auth issues
          console.log(`[ProjectSwitch] Loading project files via /sync/files/${newProjectId}`)
          const data = await apiClient.get(`/sync/files/${newProjectId}`)

          // The /sync/files endpoint returns { success, project_id, tree, layer, total }
          // tree is already hierarchical with folders/children structure
          if (data.success && data.tree && data.tree.length > 0) {
            // Convert backend tree format to frontend ProjectFile format
            const convertTree = (items: any[]): ProjectFile[] => {
              return items.map((item: any) => ({
                path: item.path,
                content: item.content || '',
                language: item.language || 'plaintext',
                type: item.type === 'folder' ? 'folder' : 'file',
                children: item.children ? convertTree(item.children) : undefined
              }))
            }

            const fileTree = convertTree(data.tree)

            console.log(`[ProjectSwitch] Loaded file tree: ${fileTree.length} root items, ${data.total} total files from layer: ${data.layer}`)
            console.log('[ProjectSwitch] Tree structure:', JSON.stringify(fileTree.map(f => ({
              path: f.path,
              type: f.type,
              childrenCount: f.children?.length || 0
            })), null, 2))

            // Set new project in store with hierarchical tree
            projectStore.setCurrentProject({
              id: newProjectId,
              name: projectName || `Project ${newProjectId}`,
              description: projectDescription,
              files: fileTree,
              createdAt: new Date(),
              updatedAt: new Date(),
              isSynced: true
            })

            result = {
              success: true,
              projectId: newProjectId,
              fileCount: data.total || fileTree.length,
              layer: data.layer || 'unknown'
            }

            console.log(`[ProjectSwitch] ✓ Loaded ${result.fileCount} files from ${result.layer}`)
          } else {
            // No files found - create empty project
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
              layer: 'none'
            }

            console.log('[ProjectSwitch] ✓ Project loaded but no files found')
          }
        } catch (err: any) {
          console.warn('[ProjectSwitch] Failed to load project files:', err)

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
          layer: 'none'
        }

        console.log('[ProjectSwitch] ✓ Created empty project (loadFiles=false)')
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
