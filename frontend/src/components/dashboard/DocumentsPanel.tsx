'use client'

import { useState, useEffect } from 'react'
import {
  FileText,
  FileSpreadsheet,
  Presentation,
  Download,
  Loader2,
  FolderOpen,
  PackageOpen,
  AlertCircle,
  File,
  FileCode,
  Image as ImageIcon,
  Lock
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { usePlanStatus } from '@/hooks/usePlanStatus'

interface Document {
  id: string | null
  name: string
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
}

interface DocumentsPanelProps {
  selectedProject: Project | null
  onClose?: () => void
}

const getDocumentIcon = (type: string, name: string) => {
  const ext = name.split('.').pop()?.toLowerCase()

  if (ext === 'pptx' || ext === 'ppt' || type === 'ppt' || type === 'presentations') {
    return { icon: Presentation, color: 'text-orange-600', bg: 'bg-orange-50' }
  }
  if (ext === 'docx' || ext === 'doc' || type === 'project_report' || type === 'srs' || type === 'documents') {
    return { icon: FileText, color: 'text-blue-600', bg: 'bg-blue-50' }
  }
  if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') {
    return { icon: FileSpreadsheet, color: 'text-green-600', bg: 'bg-green-50' }
  }
  if (ext === 'pdf') {
    return { icon: File, color: 'text-red-600', bg: 'bg-red-50' }
  }
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'svg') {
    return { icon: ImageIcon, color: 'text-purple-600', bg: 'bg-purple-50' }
  }
  if (type === 'viva_qa') {
    return { icon: FileCode, color: 'text-cyan-600', bg: 'bg-cyan-50' }
  }

  return { icon: FileText, color: 'text-gray-600', bg: 'bg-gray-100' }
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const formatDocType = (type: string) => {
  switch (type) {
    case 'project_report': return 'Report'
    case 'srs': return 'SRS'
    case 'sds': return 'Design'
    case 'ppt': return 'PPT'
    case 'viva_qa': return 'Q&A'
    case 'documents': return 'Doc'
    case 'presentations': return 'PPT'
    default: return type
  }
}

export function DocumentsPanel({ selectedProject, onClose }: DocumentsPanelProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Check if user has download feature (Premium only)
  const { features, isPremium, isLoading: planLoading } = usePlanStatus()
  const canDownload = isPremium || features?.download_files === true

  useEffect(() => {
    if (selectedProject) {
      fetchDocuments()
    } else {
      setDocuments([])
    }
  }, [selectedProject])

  const fetchDocuments = async () => {
    if (!selectedProject) return

    setIsLoading(true)
    setError(null)
    try {
      const response = await apiClient.get<{
        items: Document[]
        total: number
      }>(`/documents/list/${selectedProject.id}`)
      setDocuments(response.items || [])
    } catch (err: any) {
      setError(err.message || 'Failed to load documents')
      setDocuments([])
    } finally {
      setIsLoading(false)
    }
  }

  const handleDownloadAll = async () => {
    if (!selectedProject) return

    // Check if user can download (Premium feature)
    if (!canDownload) {
      console.warn('[DocumentsPanel] Download blocked - Premium feature required')
      return
    }

    setIsDownloading(true)
    try {
      const token = localStorage.getItem('access_token')
      const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(
        `${apiBase}/api/v1/documents/download-all/${selectedProject.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Download failed')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedProject.title.replace(/\s+/g, '_')}_documents.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      setError(err.message || 'Download failed')
    } finally {
      setIsDownloading(false)
    }
  }

  const handleDownloadSingle = async (doc: Document) => {
    // Check if user can download (Premium feature)
    if (!canDownload) {
      console.warn('[DocumentsPanel] Download blocked - Premium feature required')
      return
    }

    const token = localStorage.getItem('access_token')
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const url = `${apiBase}/api/v1${doc.download_url}`

    setDownloadingId(doc.id)

    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` }
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
    } catch (err: any) {
      setError(err.message || 'Download failed')
    } finally {
      setDownloadingId(null)
    }
  }

  if (!selectedProject) {
    return (
      <div className="p-8 flex flex-col items-center justify-center text-center">
        <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
          <FolderOpen className="w-6 h-6 text-gray-400" />
        </div>
        <p className="text-gray-500 text-sm">Select a project to view documents</p>
      </div>
    )
  }

  return (
    <div>
      {isLoading ? (
        <div className="p-8 flex flex-col items-center justify-center">
          <Loader2 className="w-6 h-6 text-indigo-600 animate-spin mb-2" />
          <p className="text-gray-500 text-sm">Loading documents...</p>
        </div>
      ) : error ? (
        <div className="p-8 flex flex-col items-center justify-center">
          <div className="w-10 h-10 rounded-full bg-red-50 flex items-center justify-center mb-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-red-600 text-sm mb-2">{error}</p>
          <button
            onClick={fetchDocuments}
            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
          >
            Try again
          </button>
        </div>
      ) : documents.length === 0 ? (
        <div className="p-8 flex flex-col items-center justify-center text-center">
          <div className="w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mb-3">
            <PackageOpen className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-gray-600 text-sm font-medium mb-1">No documents</p>
          <p className="text-gray-400 text-xs">Documents will appear after generation</p>
        </div>
      ) : (
        <>
          <div className="divide-y divide-gray-100">
            {documents.map((doc, index) => {
              const { icon: Icon, color, bg } = getDocumentIcon(doc.type, doc.name)
              const isDownloadingThis = downloadingId === doc.id

              return (
                <div
                  key={doc.id || index}
                  className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors group"
                >
                  <div className={`w-9 h-9 rounded-lg ${bg} flex items-center justify-center flex-shrink-0`}>
                    <Icon className={`w-4 h-4 ${color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{doc.name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-xs text-gray-400">{formatBytes(doc.size_bytes)}</span>
                      <span className="text-gray-300">·</span>
                      <span className="text-xs text-gray-400">{formatDocType(doc.type)}</span>
                    </div>
                  </div>
                  {canDownload ? (
                    <button
                      onClick={() => handleDownloadSingle(doc)}
                      disabled={isDownloadingThis}
                      className="p-2 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 opacity-0 group-hover:opacity-100 transition-all disabled:opacity-50"
                      title="Download"
                    >
                      {isDownloadingThis ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                    </button>
                  ) : (
                    <a
                      href="/pricing"
                      className="p-2 rounded-lg text-amber-500 hover:bg-amber-50 opacity-0 group-hover:opacity-100 transition-all"
                      title="Upgrade to Premium to download"
                    >
                      <Lock className="w-4 h-4" />
                    </a>
                  )}
                </div>
              )
            })}
          </div>

          <div className="p-4 border-t border-gray-100">
            {canDownload ? (
              <button
                onClick={handleDownloadAll}
                disabled={isDownloading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-400 rounded-lg text-white text-sm font-medium transition-colors"
              >
                {isDownloading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Preparing...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Download All ({documents.length})
                  </>
                )}
              </button>
            ) : (
              <a
                href="/pricing"
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-amber-500/20 border border-amber-400 hover:bg-amber-500/30 rounded-lg text-amber-600 text-sm font-medium transition-colors"
              >
                <Lock className="w-4 h-4" />
                Download All (Premium)
              </a>
            )}
          </div>
        </>
      )}
    </div>
  )
}
