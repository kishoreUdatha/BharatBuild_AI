import { create } from 'zustand'

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
  files: ProjectFile[]
  createdAt: Date
  updatedAt: Date
}

interface ProjectState {
  currentProject: Project | null
  projects: Project[]
  selectedFile: ProjectFile | null
  openTabs: ProjectFile[]
  activeTabPath: string | null

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
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProject: null,
  projects: [],
  selectedFile: null,
  openTabs: [],
  activeTabPath: null,

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
      const addFileToTree = (files: ProjectFile[], newFile: ProjectFile): ProjectFile[] => {
        const pathParts = newFile.path.split('/')

        // If it's a root-level file, just add it
        if (pathParts.length === 1) {
          // Check if file already exists
          const existingIndex = files.findIndex(f => f.path === newFile.path)
          if (existingIndex >= 0) {
            // Replace existing file
            const newFiles = [...files]
            newFiles[existingIndex] = newFile
            return newFiles
          }
          return [...files, newFile]
        }

        // Need to create folder structure
        const folderName = pathParts[0]
        const remainingPath = pathParts.slice(1).join('/')

        // Find or create the folder
        const folderIndex = files.findIndex(f => f.type === 'folder' && f.path === folderName)

        if (folderIndex >= 0) {
          // Folder exists, add file to its children
          const folder = files[folderIndex]
          const newFiles = [...files]
          newFiles[folderIndex] = {
            ...folder,
            children: addFileToTree(folder.children || [], {
              ...newFile,
              path: remainingPath
            })
          }
          return newFiles
        } else {
          // Create new folder
          const newFolder: ProjectFile = {
            path: folderName,
            content: '',
            language: '',
            type: 'folder',
            children: addFileToTree([], {
              ...newFile,
              path: remainingPath
            })
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

      return {
        currentProject: {
          ...state.currentProject,
          files: updateFileContent(state.currentProject.files)
        }
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
      const existingTab = state.openTabs.find(tab => tab.path === file.path)

      if (existingTab) {
        // Tab already open, just set it as active
        return {
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
  }
}))
