import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface ProjectFile {
  path: string
  content: string
  language: string
  type: 'file' | 'folder'
  children?: ProjectFile[]
}

export interface Project {
  id: string
  name: string
  description?: string
  workspaceId?: string
  files: ProjectFile[]
  createdAt: Date
  updatedAt: Date
  isSynced?: boolean  // Track if synced with backend
}

interface ProjectState {
  currentProject: Project | null
  projects: Project[]
  selectedFile: ProjectFile | null
  openTabs: ProjectFile[]
  activeTabPath: string | null
  pendingSaves: Set<string>  // Track files pending save to backend

  // Ephemeral storage (like Bolt.new) - session-based, auto-cleanup
  sessionId: string | null  // Temp session for current generation
  downloadUrl: string | null  // URL to download ZIP

  // Actions
  setCurrentProject: (project: Project) => void
  updateProject: (updates: Partial<Project>) => void
  addFile: (file: ProjectFile) => void
  updateFile: (path: string, content: string) => void
  deleteFile: (path: string) => void
  setSelectedFile: (file: ProjectFile | null) => void
  loadProjects: (projects: Project[]) => void
  openTab: (file: ProjectFile) => void
  closeTab: (path: string) => void
  setActiveTab: (path: string) => void
  closeAllTabs: () => void

  // Sync actions
  markFilePendingSave: (path: string) => void
  markFileSaved: (path: string) => void
  loadFromBackend: (projectData: any) => void

  // Ephemeral storage actions
  setSessionId: (sessionId: string | null) => void
  setDownloadUrl: (url: string | null) => void
  clearSession: () => void

  // Reset everything for new project
  resetProject: () => void

  // Bolt.new-style project switching with isolation
  switchProject: (newProjectId: string, loadFiles?: boolean) => Promise<void>
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
  currentProject: null,
  projects: [],
  selectedFile: null,
  openTabs: [],
  activeTabPath: null,
  pendingSaves: new Set<string>(),

  // Ephemeral storage state
  sessionId: null,
  downloadUrl: null,

  setCurrentProject: (project) => {
    set({ currentProject: project })
  },

  updateProject: (updates) => {
    set((state) => ({
      currentProject: state.currentProject
        ? { ...state.currentProject, ...updates }
        : null
    }))
  },

  addFile: (file) => {
    set((state) => {
      if (!state.currentProject) return state

      // Build hierarchical tree structure from file path
      // Keeps FULL paths for proper identification
      const addFileToTree = (files: ProjectFile[], newFile: ProjectFile, basePath: string = ''): ProjectFile[] => {
        const pathParts = newFile.path.split('/')

        // If it's a root-level file (single part), add it directly
        if (pathParts.length === 1) {
          const fullPath = basePath ? `${basePath}/${newFile.path}` : newFile.path
          // Check if file already exists
          const existingIndex = files.findIndex(f => f.path === fullPath)
          if (existingIndex >= 0) {
            // Replace existing file
            const newFiles = [...files]
            newFiles[existingIndex] = { ...newFile, path: fullPath }
            return newFiles
          }
          return [...files, { ...newFile, path: fullPath }]
        }

        // Need to create folder structure
        const folderName = pathParts[0]
        const remainingPath = pathParts.slice(1).join('/')
        const fullFolderPath = basePath ? `${basePath}/${folderName}` : folderName

        // Find or create the folder (match by full path)
        const folderIndex = files.findIndex(f => f.type === 'folder' && f.path === fullFolderPath)

        if (folderIndex >= 0) {
          // Folder exists, add file to its children
          const folder = files[folderIndex]
          const newFiles = [...files]
          newFiles[folderIndex] = {
            ...folder,
            children: addFileToTree(folder.children || [], {
              ...newFile,
              path: remainingPath
            }, fullFolderPath)
          }
          return newFiles
        } else {
          // Create new folder with FULL path
          const newFolder: ProjectFile = {
            path: fullFolderPath,
            content: '',
            language: '',
            type: 'folder',
            children: addFileToTree([], {
              ...newFile,
              path: remainingPath
            }, fullFolderPath)
          }
          return [...files, newFolder]
        }
      }

      return {
        currentProject: {
          ...state.currentProject,
          files: addFileToTree(state.currentProject.files, file)
        }
      }
    })
  },

  updateFile: (path, content) => {
    set((state) => {
      if (!state.currentProject) return state

      const updateFileContent = (files: ProjectFile[]): ProjectFile[] => {
        return files.map((file) => {
          if (file.path === path) {
            return { ...file, content }
          }
          if (file.children) {
            return { ...file, children: updateFileContent(file.children) }
          }
          return file
        })
      }

      // Also update the open tabs and selected file if they match this path
      const updatedTabs = state.openTabs.map(tab =>
        tab.path === path ? { ...tab, content } : tab
      )

      const updatedSelectedFile = state.selectedFile?.path === path
        ? { ...state.selectedFile, content }
        : state.selectedFile

      return {
        currentProject: {
          ...state.currentProject,
          files: updateFileContent(state.currentProject.files)
        },
        openTabs: updatedTabs,
        selectedFile: updatedSelectedFile
      }
    })
  },

  deleteFile: (path) => {
    set((state) => {
      if (!state.currentProject) return state

      const removeFile = (files: ProjectFile[]): ProjectFile[] => {
        return files.filter((file) => {
          if (file.path === path) return false
          if (file.children) {
            file.children = removeFile(file.children)
          }
          return true
        })
      }

      return {
        currentProject: {
          ...state.currentProject,
          files: removeFile(state.currentProject.files)
        }
      }
    })
  },

  setSelectedFile: (file) => {
    set({ selectedFile: file })
  },

  loadProjects: (projects) => {
    set({ projects })
  },

  openTab: (file) => {
    set((state) => {
      // Check if tab is already open
      const existingTabIndex = state.openTabs.findIndex(tab => tab.path === file.path)

      if (existingTabIndex >= 0) {
        // Tab already open - update the tab's content and set as active
        // This ensures the tab always has the latest content
        const newTabs = [...state.openTabs]
        newTabs[existingTabIndex] = { ...newTabs[existingTabIndex], ...file }
        return {
          openTabs: newTabs,
          activeTabPath: file.path,
          selectedFile: file
        }
      }

      // Add new tab
      return {
        openTabs: [...state.openTabs, file],
        activeTabPath: file.path,
        selectedFile: file
      }
    })
  },

  closeTab: (path) => {
    set((state) => {
      const newTabs = state.openTabs.filter(tab => tab.path !== path)

      // If closing active tab, switch to another tab
      let newActiveTabPath = state.activeTabPath
      let newSelectedFile = state.selectedFile

      if (state.activeTabPath === path) {
        if (newTabs.length > 0) {
          // Switch to the last tab
          const lastTab = newTabs[newTabs.length - 1]
          newActiveTabPath = lastTab.path
          newSelectedFile = lastTab
        } else {
          newActiveTabPath = null
          newSelectedFile = null
        }
      }

      return {
        openTabs: newTabs,
        activeTabPath: newActiveTabPath,
        selectedFile: newSelectedFile
      }
    })
  },

  setActiveTab: (path) => {
    set((state) => {
      const file = state.openTabs.find(tab => tab.path === path)

      return {
        activeTabPath: path,
        selectedFile: file || state.selectedFile
      }
    })
  },

  closeAllTabs: () => {
    set({
      openTabs: [],
      activeTabPath: null,
      selectedFile: null
    })
  },

  // Sync actions
  markFilePendingSave: (path) => {
    set((state) => {
      const newPending = new Set(state.pendingSaves)
      newPending.add(path)
      return { pendingSaves: newPending }
    })
  },

  markFileSaved: (path) => {
    set((state) => {
      const newPending = new Set(state.pendingSaves)
      newPending.delete(path)
      return { pendingSaves: newPending }
    })
  },

  loadFromBackend: (projectData) => {
    // Convert backend tree format to frontend ProjectFile format
    // Backend returns hierarchical tree with: path, name, type ('file'|'folder'), content, language, children
    const convertTree = (items: any[]): ProjectFile[] => {
      return items.map((item: any) => ({
        path: item.path,
        content: item.content || '',
        language: item.language || 'plaintext',
        type: item.type === 'folder' ? 'folder' : 'file',
        children: item.children ? convertTree(item.children) : undefined
      }))
    }

    // Backend now returns `tree` (hierarchical) instead of `files` (flat)
    const tree = projectData.tree || projectData.files || []
    const files = convertTree(tree)

    console.log('[ProjectStore] Received tree from backend:', tree.length, 'root items')
    console.log('[ProjectStore] Tree structure:', JSON.stringify(files.map((f: any) => ({
      path: f.path,
      type: f.type,
      childrenCount: f.children?.length || 0
    })), null, 2))

    set({
      currentProject: {
        id: projectData.project?.id || projectData.id,
        name: projectData.project?.title || projectData.name || 'Project',
        description: projectData.project?.description,
        files: files,
        createdAt: new Date(projectData.project?.created_at || Date.now()),
        updatedAt: new Date(projectData.project?.updated_at || Date.now()),
        isSynced: true
      }
    })

    console.log('[ProjectStore] Loaded project from backend:', projectData.project?.id)
  },

  // Ephemeral storage actions (like Bolt.new)
  setSessionId: (sessionId) => {
    set({ sessionId })
    console.log('[ProjectStore] Session ID set:', sessionId)
  },

  setDownloadUrl: (url) => {
    set({ downloadUrl: url })
    console.log('[ProjectStore] Download URL set:', url)
  },

  clearSession: () => {
    set({
      sessionId: null,
      downloadUrl: null
    })
    console.log('[ProjectStore] Session cleared')
  },

  resetProject: () => {
    set({
      currentProject: null,
      selectedFile: null,
      openTabs: [],
      activeTabPath: null,
      pendingSaves: new Set<string>(),
      sessionId: null,
      downloadUrl: null
    })
    console.log('[ProjectStore] Project reset for new project')
  },

  /**
   * Bolt.new-style project switching with full isolation
   *
   * When switching projects:
   * 1. Clear current project state (tabs, files, selected file)
   * 2. Optionally destroy old sandbox (free memory)
   * 3. Load new project files from sandbox/database
   * 4. Set new project as current
   *
   * This ensures NO file mixing between projects!
   */
  switchProject: async (newProjectId: string, loadFiles: boolean = true) => {
    const state = get()
    const oldProjectId = state.currentProject?.id

    console.log(`[ProjectStore] Switching from ${oldProjectId} to ${newProjectId}`)

    // Step 1: Clear ALL current project state (Bolt.new style)
    set({
      currentProject: null,
      selectedFile: null,
      openTabs: [],
      activeTabPath: null,
      pendingSaves: new Set<string>(),
      sessionId: null,
      downloadUrl: null
    })
    console.log('[ProjectStore] Cleared old project state')

    // Step 2: Optionally destroy old sandbox on backend (free resources)
    if (oldProjectId && oldProjectId !== newProjectId) {
      try {
        const token = localStorage.getItem('access_token')
        if (token) {
          // Don't await - fire and forget to not block UI
          fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/sync/sandbox/${oldProjectId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
          }).catch(err => console.warn('[ProjectStore] Failed to cleanup old sandbox:', err))
          console.log('[ProjectStore] Requested cleanup of old sandbox:', oldProjectId)
        }
      } catch (err) {
        console.warn('[ProjectStore] Error cleaning up old sandbox:', err)
      }
    }

    // Step 3: Load new project files from backend
    if (loadFiles) {
      try {
        const token = localStorage.getItem('access_token')
        if (token) {
          const response = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/sync/files/${newProjectId}`,
            {
              headers: { 'Authorization': `Bearer ${token}` }
            }
          )

          if (response.ok) {
            const data = await response.json()
            if (data.success && data.tree) {
              // Convert backend tree to ProjectFile format
              const convertTree = (items: any[]): ProjectFile[] => {
                return items.map((item: any) => ({
                  path: item.path,
                  content: item.content || '',
                  language: item.language || 'plaintext',
                  type: item.type === 'folder' ? 'folder' : 'file',
                  children: item.children ? convertTree(item.children) : undefined
                }))
              }

              const files = convertTree(data.tree)

              set({
                currentProject: {
                  id: newProjectId,
                  name: data.project?.title || `Project ${newProjectId}`,
                  description: data.project?.description,
                  files: files,
                  createdAt: new Date(),
                  updatedAt: new Date(),
                  isSynced: true
                }
              })
              console.log(`[ProjectStore] Loaded ${files.length} files for project ${newProjectId} from layer: ${data.layer}`)
              return
            }
          }
        }
      } catch (err) {
        console.warn('[ProjectStore] Failed to load project files:', err)
      }
    }

    // Fallback: Create empty project
    set({
      currentProject: {
        id: newProjectId,
        name: `Project ${newProjectId}`,
        files: [],
        createdAt: new Date(),
        updatedAt: new Date(),
        isSynced: false
      }
    })
    console.log(`[ProjectStore] Created empty project: ${newProjectId}`)
  }
}),
    {
      name: 'bharatbuild-project-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist essential data for recovery
        currentProject: state.currentProject,
        openTabs: state.openTabs,
        activeTabPath: state.activeTabPath
      }),
      // Custom serialization to handle Set
      serialize: (state) => JSON.stringify(state),
      deserialize: (str) => JSON.parse(str)
    }
  )
)
