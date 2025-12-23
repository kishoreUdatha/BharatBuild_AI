import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface ProjectFile {
  path: string
  name?: string  // Display name (derived from path if not provided)
  content?: string  // Optional - lazy loaded on click (Bolt.new style)
  language: string
  type: 'file' | 'folder'
  hash?: string  // MD5 hash for change detection (Bolt.new style)
  size_bytes?: number
  isLoading?: boolean  // True while content is being fetched
  isLoaded?: boolean  // True if content has been fetched
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

// Track recently modified files for fixer context
export interface RecentlyModifiedFile {
  path: string
  timestamp: number
  action: 'created' | 'updated' | 'deleted'
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

  // Live preview server state
  serverUrl: string | null  // URL of running dev server
  isServerRunning: boolean  // Whether server is running

  // Recently modified files tracking (for Bolt.new-style fixer context)
  recentlyModifiedFiles: RecentlyModifiedFile[]

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

  // File tree and modification tracking (for Bolt.new-style fixer)
  trackFileModification: (path: string, action: 'created' | 'updated' | 'deleted') => void
  getFileTree: () => string[]
  getRecentlyModifiedFiles: (maxAge?: number) => RecentlyModifiedFile[]
  clearRecentlyModifiedFiles: () => void

  // Bolt.new-style lazy loading
  loadFileContent: (path: string) => Promise<string | null>
  setFileLoading: (path: string, isLoading: boolean) => void
  setFileContent: (path: string, content: string) => void
  findFileByPath: (path: string) => ProjectFile | null
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

  // Live preview server state
  serverUrl: null,
  isServerRunning: false,

  // Recently modified files (for Bolt.new-style fixer context)
  recentlyModifiedFiles: [],

  setCurrentProject: (project) => {
    console.log('[ProjectStore] setCurrentProject called:', {
      id: project.id,
      name: project.name,
      filesCount: project.files?.length || 0,
      firstFile: project.files?.[0]?.path
    })
    set({ currentProject: project })

    // Verify the state was updated
    setTimeout(() => {
      const state = useProjectStore.getState()
      console.log('[ProjectStore] After setCurrentProject - verified state:', {
        id: state.currentProject?.id,
        filesCount: state.currentProject?.files?.length || 0
      })
    }, 0)
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
            name: folderName,
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

      // Track file modification for Bolt.new-style fixer context
      const fullPath = file.path
      setTimeout(() => get().trackFileModification(fullPath, 'created'), 0)

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

      // Track file modification for Bolt.new-style fixer context
      setTimeout(() => get().trackFileModification(path, 'updated'), 0)

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

      // Track file modification for Bolt.new-style fixer context
      setTimeout(() => get().trackFileModification(path, 'deleted'), 0)

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
    // Handle null/undefined projectData
    if (!projectData) {
      console.warn('[ProjectStore] loadFromBackend called with null/undefined projectData')
      return
    }

    // Convert backend tree format to frontend ProjectFile format
    // Backend returns hierarchical tree with: path, name, type ('file'|'folder'), content, language, children
    const convertTree = (items: any[]): ProjectFile[] => {
      // Handle null/undefined items array
      if (!items || !Array.isArray(items)) {
        console.warn('[ProjectStore] convertTree received invalid items:', items)
        return []
      }

      return items
        .filter((item: any) => item != null && typeof item === 'object' && item.path)
        .map((item: any) => ({
          path: item.path || '',
          name: item.name || item.path?.split('/').pop() || item.path || '',
          content: item.content ?? '',
          language: item.language || 'plaintext',
          type: item.type === 'folder' ? 'folder' : 'file',
          children: item.children ? convertTree(item.children) : undefined
        }))
    }

    // Build hierarchical tree from flat file list
    // Input: [{path: 'src/App.tsx', ...}, {path: 'package.json', ...}]
    // Output: [{path: 'src', type: 'folder', children: [...]}, {path: 'package.json', type: 'file'}]
    const buildTreeFromFlat = (flatFiles: any[]): ProjectFile[] => {
      if (!flatFiles || !Array.isArray(flatFiles)) return []

      const root: ProjectFile[] = []

      for (const file of flatFiles) {
        if (!file?.path) continue

        const parts = file.path.split('/')
        let currentLevel = root
        let currentPath = ''

        for (let i = 0; i < parts.length; i++) {
          const part = parts[i]
          currentPath = currentPath ? `${currentPath}/${part}` : part
          const isLastPart = i === parts.length - 1

          if (isLastPart) {
            // It's a file - add to current level
            currentLevel.push({
              path: file.path,
              name: part,
              content: file.content ?? '',
              language: file.language || 'plaintext',
              type: 'file'
            })
          } else {
            // It's a folder - find or create it
            let folder = currentLevel.find(f => f.type === 'folder' && f.path === currentPath)
            if (!folder) {
              folder = {
                path: currentPath,
                name: part,
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
            return (a.name || '').localeCompare(b.name || '')
          })
      }

      return sortTree(root)
    }

    // Backend returns `tree` (hierarchical) or `files` (flat)
    const rawData = projectData.tree || projectData.files || []

    // Check if data is already hierarchical (has children) or flat
    const isHierarchical = rawData.some((item: any) => item.children && item.children.length > 0)

    const files = isHierarchical
      ? convertTree(rawData)  // Already hierarchical, just convert format
      : buildTreeFromFlat(rawData)  // Flat list, build tree structure

    console.log('[ProjectStore] Received from backend:', rawData.length, 'items, isHierarchical:', isHierarchical, '-> built', files.length, 'root items')
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
              // Convert backend tree to ProjectFile format with null safety
              const convertTree = (items: any[]): ProjectFile[] => {
                if (!items || !Array.isArray(items)) {
                  return []
                }
                return items
                  .filter((item: any) => item != null && typeof item === 'object' && item.path)
                  .map((item: any) => ({
                    path: item.path || '',
                    name: item.name || item.path?.split('/').pop() || item.path || '',
                    content: item.content ?? '',
                    language: item.language || 'plaintext',
                    type: item.type === 'folder' ? 'folder' : 'file',
                    children: item.children ? convertTree(item.children) : undefined
                  }))
              }

              const files = convertTree(data.tree)

              // Check if project title is a placeholder (e.g., "New Project", "Project abc123-uuid...")
              const isPlaceholderTitle = (title: string | null | undefined): boolean => {
                if (!title) return true
                const trimmed = title.trim().toLowerCase()
                // Check for common placeholder names
                if (trimmed === 'new project' || trimmed === 'untitled' || trimmed === 'untitled project') {
                  return true
                }
                return /^Project\s+(?:[a-f0-9-]{8,}|project-\d+)/i.test(title)
              }

              const projectTitle = (data.project?.title && !isPlaceholderTitle(data.project.title))
                ? data.project.title
                : `Project ${newProjectId.slice(-8)}`

              set({
                currentProject: {
                  id: newProjectId,
                  name: projectTitle,
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

    // Fallback: Create empty project with short ID display
    set({
      currentProject: {
        id: newProjectId,
        name: `Project ${newProjectId.slice(-8)}`,
        files: [],
        createdAt: new Date(),
        updatedAt: new Date(),
        isSynced: false
      }
    })
    console.log(`[ProjectStore] Created empty project: ${newProjectId}`)
  },

  /**
   * Track a file modification (for Bolt.new-style fixer context)
   * Keeps last 20 modifications, max 5 minutes old
   */
  trackFileModification: (path: string, action: 'created' | 'updated' | 'deleted') => {
    set((state) => {
      const now = Date.now()
      const maxAge = 5 * 60 * 1000 // 5 minutes
      const maxEntries = 20

      // Filter out old entries and add new one
      const filtered = state.recentlyModifiedFiles
        .filter(f => now - f.timestamp < maxAge)
        .filter(f => f.path !== path) // Remove duplicate path

      const newEntry: RecentlyModifiedFile = { path, timestamp: now, action }

      return {
        recentlyModifiedFiles: [...filtered, newEntry].slice(-maxEntries)
      }
    })
  },

  /**
   * Get flat list of all file paths in the project tree
   */
  getFileTree: () => {
    const state = get()
    if (!state.currentProject) return []

    const paths: string[] = []

    const collectPaths = (files: ProjectFile[]) => {
      for (const file of files) {
        paths.push(file.path)
        if (file.children) {
          collectPaths(file.children)
        }
      }
    }

    collectPaths(state.currentProject.files)
    return paths
  },

  /**
   * Get recently modified files (within maxAge ms, default 5 minutes)
   */
  getRecentlyModifiedFiles: (maxAge: number = 5 * 60 * 1000) => {
    const state = get()
    const now = Date.now()
    return state.recentlyModifiedFiles.filter(f => now - f.timestamp < maxAge)
  },

  /**
   * Clear recently modified files tracking
   */
  clearRecentlyModifiedFiles: () => {
    set({ recentlyModifiedFiles: [] })
  },

  /**
   * Find a file by path in the project tree (recursive)
   */
  findFileByPath: (path: string): ProjectFile | null => {
    const state = get()
    if (!state.currentProject) return null

    const findInTree = (files: ProjectFile[]): ProjectFile | null => {
      for (const file of files) {
        if (file.path === path) return file
        if (file.children) {
          const found = findInTree(file.children)
          if (found) return found
        }
      }
      return null
    }

    return findInTree(state.currentProject.files)
  },

  /**
   * Set file loading state (for UI feedback)
   */
  setFileLoading: (path: string, isLoading: boolean) => {
    set((state) => {
      if (!state.currentProject) return state

      const updateLoadingState = (files: ProjectFile[]): ProjectFile[] => {
        return files.map((file) => {
          if (file.path === path) {
            return { ...file, isLoading }
          }
          if (file.children) {
            return { ...file, children: updateLoadingState(file.children) }
          }
          return file
        })
      }

      return {
        currentProject: {
          ...state.currentProject,
          files: updateLoadingState(state.currentProject.files)
        }
      }
    })
  },

  /**
   * Set file content after lazy loading
   */
  setFileContent: (path: string, content: string) => {
    set((state) => {
      if (!state.currentProject) return state

      const updateContent = (files: ProjectFile[]): ProjectFile[] => {
        return files.map((file) => {
          if (file.path === path) {
            return { ...file, content, isLoading: false, isLoaded: true }
          }
          if (file.children) {
            return { ...file, children: updateContent(file.children) }
          }
          return file
        })
      }

      // Also update open tabs if the file is open
      const updatedTabs = state.openTabs.map(tab =>
        tab.path === path ? { ...tab, content, isLoading: false, isLoaded: true } : tab
      )

      const updatedSelectedFile = state.selectedFile?.path === path
        ? { ...state.selectedFile, content, isLoading: false, isLoaded: true }
        : state.selectedFile

      return {
        currentProject: {
          ...state.currentProject,
          files: updateContent(state.currentProject.files)
        },
        openTabs: updatedTabs,
        selectedFile: updatedSelectedFile
      }
    })
  },

  /**
   * Bolt.new-style lazy loading: fetch file content only when user clicks
   *
   * This is the key to Bolt's performance - files are loaded on-demand!
   */
  loadFileContent: async (path: string): Promise<string | null> => {
    const state = get()
    if (!state.currentProject) return null

    // Check if already loaded
    const file = get().findFileByPath(path)
    if (file?.isLoaded && file.content !== undefined) {
      console.log(`[ProjectStore] File already loaded: ${path}`)
      return file.content
    }

    // Set loading state
    get().setFileLoading(path, true)

    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        console.warn('[ProjectStore] No access token for lazy load')
        get().setFileLoading(path, false)
        return null
      }

      const projectId = state.currentProject.id
      const encodedPath = encodeURIComponent(path)

      console.log(`[ProjectStore] Lazy loading file: ${path}`)

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/projects/${projectId}/files/${encodedPath}`,
        {
          headers: { 'Authorization': `Bearer ${token}` }
        }
      )

      if (response.ok) {
        const data = await response.json()
        const content = data.content || ''

        // Update store with loaded content
        get().setFileContent(path, content)

        console.log(`[ProjectStore] Loaded file content: ${path} (${content.length} chars)`)
        return content
      } else {
        console.warn(`[ProjectStore] Failed to load file: ${path}`, response.status)
        get().setFileLoading(path, false)
        return null
      }
    } catch (err) {
      console.error(`[ProjectStore] Error loading file: ${path}`, err)
      get().setFileLoading(path, false)
      return null
    }
  }
}),
    {
      name: 'bharatbuild-project-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist project ID and metadata - NOT files (they come from backend)
        // This prevents stale files from showing when no project is selected
        currentProject: state.currentProject ? {
          id: state.currentProject.id,
          name: state.currentProject.name,
          description: state.currentProject.description,
          files: [],  // Don't persist files - reload from backend
          createdAt: state.currentProject.createdAt,
          updatedAt: state.currentProject.updatedAt,
          isSynced: false  // Mark as not synced so we know to reload
        } : null,
        // Don't persist tabs either - they reference files that aren't persisted
        openTabs: [],
        activeTabPath: null
      }),
      // Custom serialization to handle Set
      serialize: (state) => JSON.stringify(state),
      deserialize: (str) => JSON.parse(str)
    }
  )
)
