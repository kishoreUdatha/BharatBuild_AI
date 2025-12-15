'use client'

import { useState, useEffect } from 'react'
import {
  FileText,
  Presentation,
  Download,
  Loader2,
  ChevronRight,
  ChevronDown,
  FolderOpen,
  Image as ImageIcon,
  File,
  RefreshCw
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useProject } from '@/hooks/useProject'

interface Document {
  id: string | null
  name: string
  title: string
  type: string
  status: string
  size_bytes: number
  created_at: string
  download_url: string
  source: string
}

interface Project {
  id: string
  title: string
  status: string
}

const getDocumentIcon = (type: string, name: string) => {
  const ext = name.split('.').pop()?.toLowerCase()

  if (ext === 'pptx' || ext === 'ppt' || type === 'ppt' || type === 'PPT') {
    return { icon: Presentation, color: 'text-orange-400', bg: 'bg-orange-500/20' }
  }
  if (ext === 'docx' || ext === 'doc' || type === 'REPORT' || type === 'SRS' || type === 'VIVA_QA') {
    return { icon: FileText, color: 'text-blue-400', bg: 'bg-blue-500/20' }
  }
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || type === 'UML') {
    return { icon: ImageIcon, color: 'text-purple-400', bg: 'bg-purple-500/20' }
  }
  if (ext === 'pdf') {
    return { icon: File, color: 'text-red-400', bg: 'bg-red-500/20' }
  }

  return { icon: FileText, color: 'text-gray-400', bg: 'bg-gray-500/20' }
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const formatDocType = (type: string) => {
  switch (type.toUpperCase()) {
    case 'REPORT': return 'Report'
    case 'SRS': return 'SRS'
    case 'SDS': return 'Design'
    case 'PPT': return 'PPT'
    case 'VIVA_QA': return 'Q&A'
    case 'UML': return 'UML'
    default: return type
  }
}

export function BuildDocumentsPanel() {
  const { currentProject } = useProject()
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [isLoadingDocs, setIsLoadingDocs] = useState(false)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(new Set(['REPORT', 'SRS', 'PPT', 'VIVA_QA']))

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects()
  }, [])

  // Auto-select current project if available
  useEffect(() => {
    if (currentProject?.id && currentProject.id !== 'default-project') {
      setSelectedProjectId(currentProject.id)
    }
  }, [currentProject?.id])

  // Fetch documents when project is selected
  useEffect(() => {
    if (selectedProjectId) {
      fetchDocuments(selectedProjectId)
    } else {
      setDocuments([])
    }
  }, [selectedProjectId])

  const fetchProjects = async () => {
    setIsLoadingProjects(true)
    try {
      const response = await apiClient.get<{
        items: Project[]
        total: number
      }>('/projects/list?limit=50&sort_by=created_at&sort_order=desc')
      setProjects(response.items || [])
    } catch (error) {
      console.error('Failed to fetch projects:', error)
    } finally {
      setIsLoadingProjects(false)
    }
  }

  const fetchDocuments = async (projectId: string) => {
    setIsLoadingDocs(true)
    try {
      const response = await apiClient.get<{
        items: Document[]
        total: number
      }>(`/documents/list/${projectId}`)
      setDocuments(response.items || [])
    } catch (error) {
      console.error('Failed to fetch documents:', error)
      setDocuments([])
    } finally {
      setIsLoadingDocs(false)
    }
  }

  const handleDownload = async (doc: Document) => {
    const token = localStorage.getItem('access_token')
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

    setDownloadingId(doc.id)

    try {
      // If download_url is a presigned S3 URL, use it directly
      const url = doc.download_url.startsWith('http')
        ? doc.download_url
        : `${apiBase}${doc.download_url.startsWith('/') ? '' : '/'}${doc.download_url}`

      const response = await fetch(url, {
        headers: doc.download_url.startsWith('http') ? {} : { Authorization: `Bearer ${token}` }
      })

      if (!response.ok) throw new Error('Download failed')

      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = doc.name
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(downloadUrl)
      document.body.removeChild(a)
    } catch (error) {
      console.error('Download failed:', error)
    } finally {
      setDownloadingId(null)
    }
  }

  const toggleType = (type: string) => {
    const newExpanded = new Set(expandedTypes)
    if (newExpanded.has(type)) {
      newExpanded.delete(type)
    } else {
      newExpanded.add(type)
    }
    setExpandedTypes(newExpanded)
  }

  // Group documents by type
  const groupedDocs = documents.reduce((acc, doc) => {
    const type = doc.type.toUpperCase()
    if (!acc[type]) acc[type] = []
    acc[type].push(doc)
    return acc
  }, {} as Record<string, Document[]>)

  const selectedProject = projects.find(p => p.id === selectedProjectId)

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Project Selector Dropdown */}
      <div className="p-3 border-b border-[hsl(var(--bolt-border))]">
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] hover:bg-[hsl(var(--bolt-bg-secondary))] transition-colors"
          >
            <div className="flex items-center gap-2 min-w-0">
              <FolderOpen className="w-4 h-4 text-[hsl(var(--bolt-text-secondary))] flex-shrink-0" />
              <span className="text-sm text-[hsl(var(--bolt-text-primary))] truncate">
                {selectedProject ? selectedProject.title : 'Select Project'}
              </span>
            </div>
            <ChevronDown className={`w-4 h-4 text-[hsl(var(--bolt-text-secondary))] transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
          </button>

          {/* Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute top-full left-0 right-0 mt-1 max-h-60 overflow-y-auto rounded-lg bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] shadow-xl z-50">
              {isLoadingProjects ? (
                <div className="p-3 flex items-center justify-center">
                  <Loader2 className="w-4 h-4 animate-spin text-[hsl(var(--bolt-text-secondary))]" />
                </div>
              ) : projects.length === 0 ? (
                <div className="p-3 text-sm text-[hsl(var(--bolt-text-secondary))] text-center">
                  No projects found
                </div>
              ) : (
                projects.map(project => (
                  <button
                    key={project.id}
                    onClick={() => {
                      setSelectedProjectId(project.id)
                      setIsDropdownOpen(false)
                    }}
                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[hsl(var(--bolt-bg-tertiary))] transition-colors ${
                      selectedProjectId === project.id ? 'bg-[hsl(var(--bolt-accent))]/10 text-[hsl(var(--bolt-accent))]' : 'text-[hsl(var(--bolt-text-primary))]'
                    }`}
                  >
                    <FolderOpen className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{project.title}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        {/* Refresh Button */}
        {selectedProjectId && (
          <button
            onClick={() => fetchDocuments(selectedProjectId)}
            disabled={isLoadingDocs}
            className="mt-2 w-full flex items-center justify-center gap-2 px-3 py-1.5 text-xs text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded-lg transition-colors"
          >
            <RefreshCw className={`w-3 h-3 ${isLoadingDocs ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        )}
      </div>

      {/* Documents List */}
      <div className="flex-1 overflow-y-auto">
        {!selectedProjectId ? (
          <div className="p-6 flex flex-col items-center justify-center text-center">
            <FolderOpen className="w-10 h-10 text-[hsl(var(--bolt-text-secondary))] mb-3 opacity-50" />
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              Select a project to view documents
            </p>
          </div>
        ) : isLoadingDocs ? (
          <div className="p-6 flex flex-col items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-[hsl(var(--bolt-accent))] mb-2" />
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">Loading documents...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className="p-6 flex flex-col items-center justify-center text-center">
            <FileText className="w-10 h-10 text-[hsl(var(--bolt-text-secondary))] mb-3 opacity-50" />
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">
              No documents generated yet
            </p>
            <p className="text-xs text-[hsl(var(--bolt-text-secondary))] mt-1 opacity-70">
              Documents will appear after generation
            </p>
          </div>
        ) : (
          <div className="p-2">
            {Object.entries(groupedDocs).map(([type, docs]) => (
              <div key={type} className="mb-2">
                {/* Type Header */}
                <button
                  onClick={() => toggleType(type)}
                  className="w-full flex items-center gap-2 px-2 py-1.5 text-xs font-medium text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] hover:bg-[hsl(var(--bolt-bg-tertiary))] rounded transition-colors"
                >
                  <ChevronRight className={`w-3 h-3 transition-transform ${expandedTypes.has(type) ? 'rotate-90' : ''}`} />
                  <span>{formatDocType(type)}</span>
                  <span className="ml-auto text-[hsl(var(--bolt-text-secondary))] opacity-60">
                    {docs.length}
                  </span>
                </button>

                {/* Documents under this type */}
                {expandedTypes.has(type) && (
                  <div className="ml-4 mt-1 space-y-1">
                    {docs.map((doc, index) => {
                      const { icon: Icon, color, bg } = getDocumentIcon(doc.type, doc.name)
                      const isDownloading = downloadingId === doc.id

                      return (
                        <div
                          key={doc.id || index}
                          className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[hsl(var(--bolt-bg-tertiary))] group transition-colors"
                        >
                          <div className={`w-7 h-7 rounded-lg ${bg} flex items-center justify-center flex-shrink-0`}>
                            <Icon className={`w-3.5 h-3.5 ${color}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-[hsl(var(--bolt-text-primary))] truncate">
                              {doc.name}
                            </p>
                            <p className="text-[10px] text-[hsl(var(--bolt-text-secondary))]">
                              {formatBytes(doc.size_bytes)}
                            </p>
                          </div>
                          <button
                            onClick={() => handleDownload(doc)}
                            disabled={isDownloading}
                            className="p-1.5 rounded-lg text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-accent))] hover:bg-[hsl(var(--bolt-accent))]/10 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
                            title="Download"
                          >
                            {isDownloading ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <Download className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Download All Button */}
      {documents.length > 0 && (
        <div className="p-3 border-t border-[hsl(var(--bolt-border))]">
          <button
            onClick={async () => {
              if (!selectedProjectId) return
              const token = localStorage.getItem('access_token')
              const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

              try {
                const response = await fetch(
                  `${apiBase}/documents/download-all/${selectedProjectId}`,
                  { headers: { Authorization: `Bearer ${token}` } }
                )

                if (!response.ok) throw new Error('Download failed')

                const blob = await response.blob()
                const url = window.URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `${selectedProject?.title.replace(/\s+/g, '_') || 'project'}_documents.zip`
                document.body.appendChild(a)
                a.click()
                window.URL.revokeObjectURL(url)
                document.body.removeChild(a)
              } catch (error) {
                console.error('Download all failed:', error)
              }
            }}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-[hsl(var(--bolt-accent))] hover:bg-[hsl(var(--bolt-accent))]/80 rounded-lg text-white text-sm font-medium transition-colors"
          >
            <Download className="w-4 h-4" />
            Download All ({documents.length})
          </button>
        </div>
      )}
    </div>
  )
}
