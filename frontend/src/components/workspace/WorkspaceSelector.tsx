'use client'

import { useState } from 'react'
import { ChevronDown, Plus, FolderOpen, Check, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useWorkspaceStore, Workspace } from '@/store/workspaceStore'

interface WorkspaceSelectorProps {
  onNewProject?: () => void
}

export function WorkspaceSelector({ onNewProject }: WorkspaceSelectorProps) {
  const {
    workspaces,
    currentWorkspace,
    currentProjectId,
    setCurrentWorkspace,
    setCurrentProject,
    createWorkspace,
    addProjectToWorkspace
  } = useWorkspaceStore()

  const [isOpen, setIsOpen] = useState(false)
  const [showNewWorkspaceInput, setShowNewWorkspaceInput] = useState(false)
  const [showNewProjectInput, setShowNewProjectInput] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [newProjectName, setNewProjectName] = useState('')

  const currentProject = currentWorkspace?.projects.find(p => p.id === currentProjectId)

  const handleCreateWorkspace = () => {
    if (newWorkspaceName.trim()) {
      const workspace = createWorkspace(newWorkspaceName.trim())
      setCurrentWorkspace(workspace)
      setNewWorkspaceName('')
      setShowNewWorkspaceInput(false)
    }
  }

  const handleCreateProject = () => {
    if (newProjectName.trim() && currentWorkspace) {
      const newProject = {
        id: `proj-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        name: newProjectName.trim(),
        createdAt: new Date(),
        updatedAt: new Date()
      }
      addProjectToWorkspace(currentWorkspace.id, newProject)
      setCurrentProject(newProject.id)
      setNewProjectName('')
      setShowNewProjectInput(false)
      setIsOpen(false)
      onNewProject?.()
    }
  }

  const handleSelectWorkspace = (workspace: Workspace) => {
    setCurrentWorkspace(workspace)
    // Auto-select first project
    if (workspace.projects.length > 0) {
      setCurrentProject(workspace.projects[0].id)
    }
  }

  const handleSelectProject = (projectId: string) => {
    setCurrentProject(projectId)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      {/* Current Selection Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] hover:border-[hsl(var(--bolt-accent))] transition-colors"
      >
        <FolderOpen className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
        <div className="text-left">
          <div className="text-xs text-[hsl(var(--bolt-text-secondary))]">
            {currentWorkspace?.name || 'No Workspace'}
          </div>
          <div className="text-sm font-medium text-[hsl(var(--bolt-text-primary))] max-w-[150px] truncate">
            {currentProject?.name || 'Select Project'}
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown Menu */}
          <div className="absolute top-full left-0 mt-2 w-72 bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-lg shadow-xl z-50 overflow-hidden">
            {/* Workspaces Section */}
            <div className="p-2 border-b border-[hsl(var(--bolt-border))]">
              <div className="text-xs font-semibold text-[hsl(var(--bolt-text-secondary))] px-2 py-1 mb-1">
                WORKSPACES
              </div>
              {workspaces.map((workspace) => (
                <button
                  key={workspace.id}
                  onClick={() => handleSelectWorkspace(workspace)}
                  className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors ${
                    currentWorkspace?.id === workspace.id
                      ? 'bg-[hsl(var(--bolt-accent))]/10 text-[hsl(var(--bolt-accent))]'
                      : 'hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-primary))]'
                  }`}
                >
                  <FolderOpen className="w-4 h-4" />
                  <span className="flex-1 truncate text-sm">{workspace.name}</span>
                  <span className="text-xs text-[hsl(var(--bolt-text-secondary))]">
                    {workspace.projects.length} projects
                  </span>
                  {currentWorkspace?.id === workspace.id && (
                    <Check className="w-4 h-4" />
                  )}
                </button>
              ))}

              {/* New Workspace Input */}
              {showNewWorkspaceInput ? (
                <div className="flex items-center gap-2 mt-2 px-2">
                  <input
                    type="text"
                    value={newWorkspaceName}
                    onChange={(e) => setNewWorkspaceName(e.target.value)}
                    placeholder="Workspace name"
                    className="flex-1 px-2 py-1 text-sm bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] rounded focus:border-[hsl(var(--bolt-accent))] outline-none"
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreateWorkspace()
                      if (e.key === 'Escape') setShowNewWorkspaceInput(false)
                    }}
                  />
                  <Button size="sm" onClick={handleCreateWorkspace} className="h-7 px-2">
                    Add
                  </Button>
                </div>
              ) : (
                <button
                  onClick={() => setShowNewWorkspaceInput(true)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors mt-1"
                >
                  <Plus className="w-4 h-4" />
                  <span className="text-sm">New Workspace</span>
                </button>
              )}
            </div>

            {/* Projects Section (for current workspace) */}
            {currentWorkspace && (
              <div className="p-2">
                <div className="text-xs font-semibold text-[hsl(var(--bolt-text-secondary))] px-2 py-1 mb-1">
                  PROJECTS IN {currentWorkspace.name.toUpperCase()}
                </div>
                {currentWorkspace.projects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => handleSelectProject(project.id)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors ${
                      currentProjectId === project.id
                        ? 'bg-[hsl(var(--bolt-accent))]/10 text-[hsl(var(--bolt-accent))]'
                        : 'hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-primary))]'
                    }`}
                  >
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="flex-1 truncate text-sm">{project.name}</span>
                    {currentProjectId === project.id && (
                      <Check className="w-4 h-4" />
                    )}
                  </button>
                ))}

                {/* New Project Input */}
                {showNewProjectInput ? (
                  <div className="flex items-center gap-2 mt-2 px-2">
                    <input
                      type="text"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      placeholder="Project name"
                      className="flex-1 px-2 py-1 text-sm bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] rounded focus:border-[hsl(var(--bolt-accent))] outline-none"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateProject()
                        if (e.key === 'Escape') setShowNewProjectInput(false)
                      }}
                    />
                    <Button size="sm" onClick={handleCreateProject} className="h-7 px-2">
                      Add
                    </Button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowNewProjectInput(true)}
                    className="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors mt-1"
                  >
                    <Plus className="w-4 h-4" />
                    <span className="text-sm">New Project</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
