'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import {
  ChevronDown,
  ChevronRight,
  FolderOpen,
  Plus,
  Check,
  Loader2,
  Clock,
  History,
  Pencil,
  Copy,
  Download,
  FileDown,
  Github,
  Search,
  FileText,
  File,
  Presentation
} from 'lucide-react'
import { useProjects, Project } from '@/hooks/useProjects'
import { useProjectStore } from '@/store/projectStore'
import { useProjectSwitch } from '@/hooks/useProjectSwitch'
import { apiClient } from '@/lib/api-client'

interface DocumentItem {
  id: string | null
  name: string
  type: string
  status: string
  size_bytes: number
  created_at: string | null
  download_url: string
}

interface ProjectSelectorProps {
  onProjectSelect?: (project: Project) => void
  onNewProject?: () => void
}

export function ProjectSelector({ onProjectSelect, onNewProject }: ProjectSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [showRecentProjects, setShowRecentProjects] = useState(false)
  const [showExportOptions, setShowExportOptions] = useState(false)
  const [showDocuments, setShowDocuments] = useState(false)
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [documentsLoading, setDocumentsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  const { projects, loading, error, refresh } = useProjects(1, 50)
  const { currentProject } = useProjectStore()

  const { isSwitching, switchProject, createNewProject } = useProjectSwitch()

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
        setShowRecentProjects(false)
        setShowExportOptions(false)
        setShowDocuments(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Fetch documents for current project
  const fetchDocuments = async () => {
    if (!currentProject?.id) return
    setDocumentsLoading(true)
    try {
      const response = await apiClient.get(`/documents/list/${currentProject.id}`)
      setDocuments(response.items || [])
    } catch (err) {
      console.error('Failed to fetch documents:', err)
      setDocuments([])
    } finally {
      setDocumentsLoading(false)
    }
  }

  // Download document
  const handleDownloadDocument = async (doc: DocumentItem) => {
    if (!currentProject?.id) return
    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
      const token = localStorage.getItem('access_token')

      // If download_url is an S3 presigned URL (starts with http), use it directly
      if (doc.download_url && (doc.download_url.startsWith('http://') || doc.download_url.startsWith('https://'))) {
        window.open(doc.download_url, '_blank')
      } else if (doc.id) {
        // Use document ID endpoint for reliable download
        const downloadUrl = `${baseUrl}/documents/download-by-id/${doc.id}`
        const response = await fetch(downloadUrl, {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = doc.name
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          document.body.removeChild(a)
        }
      } else {
        // Fallback to legacy endpoint
        const downloadUrl = `${baseUrl}${doc.download_url}`
        const response = await fetch(downloadUrl, {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if (response.ok) {
          const blob = await response.blob()
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = doc.name
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          document.body.removeChild(a)
        }
      }
    } catch (err) {
      console.error('Failed to download document:', err)
    }
    setIsOpen(false)
    setShowDocuments(false)
  }

  // Get icon for document type
  const getDocIcon = (name: string) => {
    if (name.toLowerCase().includes('ppt') || name.endsWith('.pptx')) {
      return <Presentation className="w-4 h-4 text-orange-400" />
    }
    if (name.toLowerCase().includes('srs')) {
      return <FileText className="w-4 h-4 text-blue-400" />
    }
    if (name.toLowerCase().includes('viva') || name.toLowerCase().includes('q&a')) {
      return <FileText className="w-4 h-4 text-green-400" />
    }
    return <File className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
  }

  // Get latest project name to show
  const latestProjectName = currentProject?.name || (projects.length > 0 ? projects[0].title : 'New Project')

  const handleSelectProject = async (project: Project) => {
    const hasNoFiles = !currentProject?.files || currentProject.files.length === 0
    if (currentProject?.id === project.id && !hasNoFiles) {
      setIsOpen(false)
      setShowRecentProjects(false)
      return
    }

    try {
      const result = await switchProject(project.id, {
        loadFiles: true,
        loadMessages: true,
        clearTerminal: true,
        clearErrors: true,
        clearChat: true,
        destroyOldSandbox: true,
        projectName: project.title,
        projectDescription: project.description || undefined
      })

      if (result.success) {
        onProjectSelect?.(project)
      }

      setIsOpen(false)
      setShowRecentProjects(false)
    } catch (error) {
      console.error('[ProjectSelector] Failed to switch project:', error)
    }
  }

  const handleNewProject = async () => {
    setIsOpen(false)
    setShowRecentProjects(false)

    if (onNewProject) {
      onNewProject()
      return
    }

    try {
      await createNewProject()
    } catch (error) {
      console.error('[ProjectSelector] Failed to create new project:', error)
    }
  }

  const handleExportZip = () => {
    // Trigger export
    const exportBtn = document.querySelector('[title="Download Project as ZIP"]') as HTMLButtonElement
    if (exportBtn) exportBtn.click()
    setIsOpen(false)
    setShowExportOptions(false)
  }

  const handleExportGithub = () => {
    // TODO: Implement GitHub export
    console.log('Export to GitHub')
    setIsOpen(false)
    setShowExportOptions(false)
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

  const getMonthYear = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })
  }

  // Filter and group projects by month
  const filteredProjects = useMemo(() => {
    return projects.filter(project =>
      project.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      project.description?.toLowerCase().includes(searchQuery.toLowerCase())
    )
  }, [projects, searchQuery])

  const groupedProjects = useMemo(() => {
    const groups: { [key: string]: Project[] } = {}
    filteredProjects.forEach(project => {
      const monthYear = getMonthYear(project.updated_at)
      if (!groups[monthYear]) {
        groups[monthYear] = []
      }
      groups[monthYear].push(project)
    })
    return groups
  }, [filteredProjects])

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button - Shows latest project name */}
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
          {latestProjectName}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-[240px] z-50
          bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]
          rounded-lg shadow-xl">

          {/* Open Recent Projects - with submenu on click */}
          <div className="relative">
            <button
              onClick={() => {
                setShowRecentProjects(!showRecentProjects)
                setShowExportOptions(false)
                setShowDocuments(false)
                if (!showRecentProjects) refresh()
              }}
              className="w-full flex items-center justify-between px-3 py-2.5 text-sm
                text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
                border-b border-[hsl(var(--bolt-border))]"
            >
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                <span>Open Recent Project</span>
              </div>
              <ChevronRight className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] transition-transform ${showRecentProjects ? 'rotate-90' : ''}`} />
            </button>

            {/* Recent Projects Submenu - appears on click */}
            {showRecentProjects && (
              <div
                className="absolute left-full top-0 w-[320px]
                  bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]
                  rounded-lg shadow-xl overflow-hidden z-50"
                style={{ marginLeft: '4px' }}
              >
                {/* Search Input */}
                <div className="p-2 border-b border-[hsl(var(--bolt-border))]">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[hsl(var(--bolt-text-tertiary))]" />
                    <input
                      type="text"
                      placeholder="Search projects..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-2 text-sm rounded-md
                        bg-[hsl(var(--bolt-bg-primary))] border border-[hsl(var(--bolt-border))]
                        text-[hsl(var(--bolt-text-primary))] placeholder-[hsl(var(--bolt-text-tertiary))]
                        focus:outline-none focus:ring-1 focus:ring-[hsl(var(--bolt-accent))]"
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                </div>

                {/* Projects List */}
                <div className="max-h-[300px] overflow-y-auto">
                  {loading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--bolt-accent))]" />
                    </div>
                  ) : error ? (
                    <div className="py-6 text-center text-sm text-red-400">
                      {error}
                    </div>
                  ) : filteredProjects.length === 0 ? (
                    <div className="py-6 text-center text-sm text-[hsl(var(--bolt-text-tertiary))]">
                      {searchQuery ? 'No matching projects' : 'No projects yet'}
                    </div>
                  ) : (
                    <>
                      {/* Last 30 Days Header */}
                      <div className="px-3 py-1.5 text-xs font-semibold
                        text-[hsl(var(--bolt-text-tertiary))] bg-[hsl(var(--bolt-bg-primary))]
                        border-b border-[hsl(var(--bolt-border))]">
                        Last 30 Days
                      </div>
                      {/* Project List */}
                      {filteredProjects.map((project) => (
                        <button
                          key={project.id}
                          onClick={() => handleSelectProject(project)}
                          className={`w-full flex items-center justify-between px-3 py-2 text-left
                            hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors
                            ${currentProject?.id === project.id ? 'bg-[hsl(var(--bolt-accent)/0.1)]' : ''}`}
                        >
                          <span className="text-sm text-[hsl(var(--bolt-text-primary))] truncate">
                            {project.title}
                          </span>
                          {currentProject?.id === project.id && (
                            <Check className="w-3.5 h-3.5 text-[hsl(var(--bolt-accent))] flex-shrink-0 ml-2" />
                          )}
                        </button>
                      ))}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Version History */}
          <button
            className="w-full flex items-center gap-2 px-3 py-2.5 text-sm
              text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
              border-b border-[hsl(var(--bolt-border))]"
            onClick={() => {
              // TODO: Implement version history
              console.log('Version History')
              setIsOpen(false)
            }}
          >
            <History className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
            <span>Version History</span>
          </button>

          {/* Documents - with submenu on click */}
          <div className="relative">
            <button
              onClick={() => {
                setShowDocuments(!showDocuments)
                setShowRecentProjects(false)
                setShowExportOptions(false)
                if (!showDocuments) fetchDocuments()
              }}
              className="w-full flex items-center justify-between px-3 py-2.5 text-sm
                text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
                border-b border-[hsl(var(--bolt-border))]"
            >
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                <span>Documents</span>
              </div>
              <ChevronRight className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] transition-transform ${showDocuments ? 'rotate-90' : ''}`} />
            </button>

            {/* Documents Submenu */}
            {showDocuments && (
              <div
                className="absolute left-full top-0 w-[280px]
                  bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]
                  rounded-lg shadow-xl overflow-hidden z-50"
                style={{ marginLeft: '4px' }}
              >
                {/* Header */}
                <div className="px-3 py-2 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-primary))]">
                  <span className="text-xs font-semibold text-[hsl(var(--bolt-text-tertiary))] uppercase">
                    Project Documents
                  </span>
                </div>

                {/* Documents List */}
                <div className="max-h-[300px] overflow-y-auto">
                  {documentsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-5 h-5 animate-spin text-[hsl(var(--bolt-accent))]" />
                    </div>
                  ) : documents.length === 0 ? (
                    <div className="py-6 text-center text-sm text-[hsl(var(--bolt-text-tertiary))]">
                      No documents generated yet
                    </div>
                  ) : (
                    documents.map((doc, index) => (
                      <button
                        key={doc.id || index}
                        onClick={() => handleDownloadDocument(doc)}
                        className="w-full flex items-center gap-3 px-3 py-2.5 text-left
                          hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors"
                      >
                        {getDocIcon(doc.name)}
                        <div className="flex-1 min-w-0">
                          <span className="text-sm text-[hsl(var(--bolt-text-primary))] truncate block">
                            {doc.name}
                          </span>
                          <span className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
                            {doc.size_bytes ? `${(doc.size_bytes / 1024).toFixed(1)} KB` : 'Click to download'}
                          </span>
                        </div>
                        <Download className="w-3.5 h-3.5 text-[hsl(var(--bolt-text-tertiary))]" />
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Rename */}
          <button
            className="w-full flex items-center gap-2 px-3 py-2.5 text-sm
              text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
              border-b border-[hsl(var(--bolt-border))]"
            onClick={() => {
              // TODO: Implement rename
              console.log('Rename')
              setIsOpen(false)
            }}
          >
            <Pencil className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
            <span>Rename</span>
          </button>

          {/* Duplicate */}
          <button
            className="w-full flex items-center gap-2 px-3 py-2.5 text-sm
              text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
              border-b border-[hsl(var(--bolt-border))]"
            onClick={() => {
              // TODO: Implement duplicate
              console.log('Duplicate')
              setIsOpen(false)
            }}
          >
            <Copy className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
            <span>Duplicate</span>
          </button>

          {/* Export - with submenu on click */}
          <div className="relative">
            <button
              onClick={() => {
                setShowExportOptions(!showExportOptions)
                setShowRecentProjects(false)
                setShowDocuments(false)
              }}
              className="w-full flex items-center justify-between px-3 py-2.5 text-sm
                text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]"
            >
              <div className="flex items-center gap-2">
                <Download className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                <span>Export</span>
              </div>
              <ChevronRight className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] transition-transform ${showExportOptions ? 'rotate-90' : ''}`} />
            </button>

            {/* Export Submenu */}
            {showExportOptions && (
              <div
                className="absolute left-full top-0 w-[180px]
                  bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))]
                  rounded-lg shadow-xl overflow-hidden z-50"
                style={{ marginLeft: '4px' }}
              >
                <button
                  onClick={handleExportZip}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-sm
                    text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]
                    border-b border-[hsl(var(--bolt-border))]"
                >
                  <FileDown className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                  <span>Download ZIP</span>
                </button>
                <button
                  onClick={handleExportGithub}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-sm
                    text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))]"
                >
                  <Github className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))]" />
                  <span>Push to GitHub</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
