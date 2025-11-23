import { useCallback } from 'react'
import { useProjectStore, ProjectFile, Project } from '@/store/projectStore'

export const useProject = () => {
  const {
    currentProject,
    projects,
    selectedFile,
    openTabs,
    activeTabPath,
    setCurrentProject,
    updateProject,
    addFile,
    updateFile,
    deleteFile,
    setSelectedFile,
    loadProjects,
    openTab,
    closeTab,
    setActiveTab,
    closeAllTabs
  } = useProjectStore()

  const createNewProject = useCallback((name: string, description?: string) => {
    const newProject: Project = {
      id: `project-${Date.now()}`,
      name,
      description,
      files: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }
    setCurrentProject(newProject)
  }, [setCurrentProject])

  const findFile = useCallback((path: string): ProjectFile | undefined => {
    if (!currentProject) return undefined

    const searchFiles = (files: ProjectFile[]): ProjectFile | undefined => {
      for (const file of files) {
        if (file.path === path) return file
        if (file.children) {
          const found = searchFiles(file.children)
          if (found) return found
        }
      }
      return undefined
    }

    return searchFiles(currentProject.files)
  }, [currentProject])

  const getFileCount = useCallback((): number => {
    if (!currentProject) return 0

    const countFiles = (files: ProjectFile[]): number => {
      return files.reduce((count, file) => {
        if (file.type === 'file') {
          return count + 1
        }
        if (file.children) {
          return count + countFiles(file.children)
        }
        return count
      }, 0)
    }

    return countFiles(currentProject.files)
  }, [currentProject])

  return {
    currentProject,
    projects,
    selectedFile,
    openTabs,
    activeTabPath,
    setCurrentProject,
    updateProject,
    addFile,
    updateFile,
    deleteFile,
    setSelectedFile,
    loadProjects,
    createNewProject,
    findFile,
    getFileCount,
    openTab,
    closeTab,
    setActiveTab,
    closeAllTabs
  }
}
