import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface Project {
  id: string
  name: string
  description?: string
  createdAt: Date
  updatedAt: Date
}

export interface Workspace {
  id: string
  name: string
  description?: string
  projects: Project[]
  createdAt: Date
  updatedAt: Date
}

interface WorkspaceState {
  workspaces: Workspace[]
  currentWorkspace: Workspace | null
  currentProjectId: string | null

  // Workspace actions
  createWorkspace: (name: string, description?: string) => Workspace
  setCurrentWorkspace: (workspace: Workspace | null) => void
  updateWorkspace: (id: string, updates: Partial<Workspace>) => void
  deleteWorkspace: (id: string) => void
  getWorkspace: (id: string) => Workspace | undefined

  // Project actions within workspace
  addProjectToWorkspace: (workspaceId: string, project: Project) => void
  removeProjectFromWorkspace: (workspaceId: string, projectId: string) => void
  setCurrentProject: (projectId: string | null) => void
  getCurrentProject: () => Project | null

  // Quick workspace creation from landing page
  createWorkspaceWithProject: (workspaceName: string, projectName: string, description?: string) => { workspace: Workspace, project: Project }
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set, get) => ({
      workspaces: [],
      currentWorkspace: null,
      currentProjectId: null,

      createWorkspace: (name, description) => {
        const newWorkspace: Workspace = {
          id: `ws-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name,
          description,
          projects: [],
          createdAt: new Date(),
          updatedAt: new Date()
        }

        set((state) => ({
          workspaces: [...state.workspaces, newWorkspace],
          currentWorkspace: newWorkspace
        }))

        return newWorkspace
      },

      setCurrentWorkspace: (workspace) => {
        set({ currentWorkspace: workspace, currentProjectId: null })
      },

      updateWorkspace: (id, updates) => {
        set((state) => ({
          workspaces: state.workspaces.map((ws) =>
            ws.id === id ? { ...ws, ...updates, updatedAt: new Date() } : ws
          ),
          currentWorkspace: state.currentWorkspace?.id === id
            ? { ...state.currentWorkspace, ...updates, updatedAt: new Date() }
            : state.currentWorkspace
        }))
      },

      deleteWorkspace: (id) => {
        set((state) => ({
          workspaces: state.workspaces.filter((ws) => ws.id !== id),
          currentWorkspace: state.currentWorkspace?.id === id ? null : state.currentWorkspace,
          currentProjectId: state.currentWorkspace?.id === id ? null : state.currentProjectId
        }))
      },

      getWorkspace: (id) => {
        return get().workspaces.find((ws) => ws.id === id)
      },

      addProjectToWorkspace: (workspaceId, project) => {
        set((state) => ({
          workspaces: state.workspaces.map((ws) =>
            ws.id === workspaceId
              ? { ...ws, projects: [...ws.projects, project], updatedAt: new Date() }
              : ws
          ),
          currentWorkspace: state.currentWorkspace?.id === workspaceId
            ? { ...state.currentWorkspace, projects: [...state.currentWorkspace.projects, project], updatedAt: new Date() }
            : state.currentWorkspace
        }))
      },

      removeProjectFromWorkspace: (workspaceId, projectId) => {
        set((state) => ({
          workspaces: state.workspaces.map((ws) =>
            ws.id === workspaceId
              ? { ...ws, projects: ws.projects.filter((p) => p.id !== projectId), updatedAt: new Date() }
              : ws
          ),
          currentWorkspace: state.currentWorkspace?.id === workspaceId
            ? { ...state.currentWorkspace, projects: state.currentWorkspace.projects.filter((p) => p.id !== projectId), updatedAt: new Date() }
            : state.currentWorkspace,
          currentProjectId: state.currentProjectId === projectId ? null : state.currentProjectId
        }))
      },

      setCurrentProject: (projectId) => {
        set({ currentProjectId: projectId })
      },

      getCurrentProject: () => {
        const state = get()
        if (!state.currentWorkspace || !state.currentProjectId) return null
        return state.currentWorkspace.projects.find((p) => p.id === state.currentProjectId) || null
      },

      createWorkspaceWithProject: (workspaceName, projectName, description) => {
        const projectId = `proj-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        const project: Project = {
          id: projectId,
          name: projectName,
          description,
          createdAt: new Date(),
          updatedAt: new Date()
        }

        const workspace: Workspace = {
          id: `ws-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
          name: workspaceName,
          description: `Workspace for ${projectName}`,
          projects: [project],
          createdAt: new Date(),
          updatedAt: new Date()
        }

        set((state) => ({
          workspaces: [...state.workspaces, workspace],
          currentWorkspace: workspace,
          currentProjectId: projectId
        }))

        return { workspace, project }
      }
    }),
    {
      name: 'bharatbuild-workspaces',
      partialize: (state) => ({
        workspaces: state.workspaces,
        currentWorkspace: state.currentWorkspace,
        currentProjectId: state.currentProjectId
      })
    }
  )
)
