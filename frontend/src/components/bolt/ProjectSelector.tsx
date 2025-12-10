'use client'

import { useState, useEffect, useRef } from 'react'
import {
  ChevronDown,
  FolderOpen,
  Plus,
  Check,
  Loader2,
  Search,
  Clock,
  Zap
} from 'lucide-react'
import { useProjects, Project } from '@/hooks/useProjects'
import { useProjectStore } from '@/store/projectStore'
import { useProjectSwitch } from '@/hooks/useProjectSwitch'
import { apiClient } from '@/lib/api-client'

interface ProjectSelectorProps {
  onProjectSelect?: (project: Project) => void
  onNewProject?: () => void
}

export function ProjectSelector({ onProjectSelect, onNewProject }: ProjectSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { projects, loading, refresh } = useProjects()
  const { currentProject } = useProjectStore()

  // Bolt.new-style project switching with complete isolation
  const { isSwitching, switchProject, createNewProject } = useProjectSwitch()

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Filter projects based on search query
  const filteredProjects = projects.filter(project =>
    project.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  /**
   * Bolt.new-style project switching with COMPLETE ISOLATION
   *
   * When switching to a different project:
   * 1. Clear ALL old state (file tree, tabs, terminal, errors, chat)
   * 2. Destroy old sandbox on server (free resources)
   * 3. Load fresh file tree from server
   * 4. NO file mixing between projects!
   */
  const handleSelectProject = async (project: Project) => {
    // Allow re-selection if current project has no files (force reload)
    const hasNoFiles = !currentProject?.files || currentProject.files.length === 0
    if (currentProject?.id === project.id && !hasNoFiles) {
      setIsOpen(false)
      return
    }

    console.log(`[ProjectSelector] Switching to project: ${project.id} (${project.title}), hasNoFiles: ${hasNoFiles}`)

    try {
      // Use Bolt.new-style project switching with complete teardown
      const result = await switchProject(project.id, {
        loadFiles: true,       // Load files from server
        loadMessages: true,    // Load chat history from server
        clearTerminal: true,   // Clear terminal logs
        clearErrors: true,     // Clear error logs
        clearChat: true,       // Clear chat before loading history from server
        destroyOldSandbox: true, // Delete old sandbox from server
        projectName: project.title,  // Pass actual project title
        projectDescription: project.description || undefined
      })

      if (result.success) {
        console.log(`[ProjectSelector] Switch complete: ${result.fileCount} files loaded from ${result.layer}`)
        onProjectSelect?.(project)
      } else {
        console.warn(`[ProjectSelector] Switch failed:`, result.error)
      }

      setIsOpen(false)
      setSearchQuery('')
    } catch (error) {
      console.error('[ProjectSelector] Failed to switch project:', error)
    }
  }

  /**
   * Create a new project with complete teardown of current state
   * (Like clicking "New Project" in Bolt.new)
   */
  const handleNewProject = async () => {
    setIsOpen(false)

    // If there's a callback, let the parent handle it
    if (onNewProject) {
      onNewProject()
      return
    }

    // Otherwise, use Bolt.new-style new project creation
    console.log('[ProjectSelector] Creating new project with complete teardown')
    try {
      const result = await createNewProject()
      console.log(`[ProjectSelector] New project created: ${result.projectId}`)
    } catch (error) {
      console.error('[ProjectSelector] Failed to create new project:', error)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return 'bg-green-500'
      case 'IN_PROGRESS':
      case 'PROCESSING':
        return 'bg-yellow-500'
      case 'FAILED':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return <Check className="w-3 h-3" />
      case 'IN_PROGRESS':
      case 'PROCESSING':
        return <Loader2 className="w-3 h-3 animate-spin" />
      default:
        return null
    }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => {
          setIsOpen(!isOpen)
          if (!isOpen) refresh()
        }}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg
          bg-[hsl(var(--bolt-bg-secondary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
          border border-[hsl(var(--bolt-border))]
          text-[hsl(var(--bolt-text-primary))] text-sm font-medium
          transition-colors min-w-[180px] max-w-[280px]"
        disabled={isSwitching}
      >
        {isSwitching ? (
          <Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--bolt-accent))]" />
        ) : (
          <FolderOpen className="w-4 h-4 text-[hsl(var(--bolt-accent))]" />
        )}
        <span className="flex-1 text-left truncate">
          {currentProject?.name || 'Select Project'}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-[320px] z-50
          bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]
          rounded-lg shadow-xl overflow-hidden">

          {/* Search Input */}
          <div className="p-2 border-b border-[hsl(var(--bolt-border))]">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--bolt-text-tertiary))]" />
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-sm rounded-md
                  bg-[hsl(var(--bolt-bg-primary))] border border-[hsl(var(--bolt-border))]
                  text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))]
                  focus:outline-none focus:border-[hsl(var(--bolt-accent))]"
                autoFocus
              />
            </div>
          </div>

          {/* New Project Button */}
          <button
            onClick={handleNewProject}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm
              text-[hsl(var(--bolt-accent))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
              border-b border-[hsl(var(--bolt-border))]"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
            <kbd className="ml-auto text-xs px-1.5 py-0.5 rounded bg-[hsl(var(--bolt-bg-primary))] text-[hsl(var(--bolt-text-tertiary))]">
              Ctrl+N
            </kbd>
          </button>

          {/* Projects List */}
          <div className="max-h-[300px] overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--bolt-accent))]" />
              </div>
            ) : filteredProjects.length === 0 ? (
              <div className="py-8 text-center text-sm text-[hsl(var(--bolt-text-tertiary))]">
                {searchQuery ? 'No projects found' : 'No projects yet'}
              </div>
            ) : (
              filteredProjects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => handleSelectProject(project)}
                  className={`w-full flex items-start gap-3 px-3 py-2.5 text-left
                    hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors
                    ${currentProject?.id === project.id ? 'bg-[hsl(var(--bolt-accent)/0.1)]' : ''}`}
                >
                  {/* Status Indicator */}
                  <div className={`mt-1.5 w-2 h-2 rounded-full ${getStatusColor(project.status)}`} />

                  {/* Project Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-[hsl(var(--bolt-text-primary))] truncate">
                        {project.title}
                      </span>
                      {currentProject?.id === project.id && (
                        <Check className="w-3.5 h-3.5 text-[hsl(var(--bolt-accent))]" />
                      )}
                    </div>
                    {project.description && (
                      <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] truncate mt-0.5">
                        {project.description}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-1 text-xs text-[hsl(var(--bolt-text-tertiary))]">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatDate(project.updated_at)}
                      </span>
                      {project.total_tokens > 0 && (
                        <span className="flex items-center gap-1">
                          <Zap className="w-3 h-3" />
                          {project.total_tokens.toLocaleString()} tokens
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
