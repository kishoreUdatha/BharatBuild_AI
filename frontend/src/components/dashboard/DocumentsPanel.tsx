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
  AlertCircle
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'

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

const documentIcons: Record<string, any> = {
  project_report: FileText,
  srs: FileSpreadsheet,
  sds: FileSpreadsheet,
  ppt: Presentation,
  viva_qa: FileText,
  documents: FileText,
  presentations: Presentation
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

export function DocumentsPanel({ selectedProject, onClose }: DocumentsPanelProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

    setIsDownloading(true)
    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/documents/download-all/${selectedProject.id}`,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
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
    const token = localStorage.getItem('access_token')
    const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1${doc.download_url}`

    try {
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`
        }
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
    }
  }

  if (!selectedProject) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-500 p-6">
        <FolderOpen className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-center">Select a project to view its documents</p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-[#1a1a1a] rounded-xl border border-[#333]">
      {/* Header */}
      <div className="p-4 border-b border-[#333]">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-white">Documents</h3>
          {documents.length > 0 && (
            <span className="text-xs text-gray-400 bg-[#333] px-2 py-0.5 rounded">
              {documents.length} files
            </span>
          )}
        </div>
        <p className="text-sm text-gray-400 truncate">{selectedProject.title}</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-400" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-8 text-red-400">
            <AlertCircle className="h-8 w-8 mb-2" />
            <p className="text-sm text-center">{error}</p>
            <button
              onClick={fetchDocuments}
              className="mt-3 text-sm text-blue-400 hover:underline"
            >
              Retry
            </button>
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-gray-500">
            <PackageOpen className="h-10 w-10 mb-3 opacity-50" />
            <p className="text-sm">No documents generated yet</p>
            <p className="text-xs mt-1 text-gray-600">
              Documents are generated for student projects
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {documents.map((doc, index) => {
              const Icon = documentIcons[doc.type] || FileText
              return (
                <div
                  key={doc.id || index}
                  className="flex items-center justify-between p-3 rounded-lg bg-[#252525] hover:bg-[#2a2a2a] transition-colors group"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <div className="p-2 rounded-lg bg-blue-500/20">
                      <Icon className="h-4 w-4 text-blue-400" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white truncate">{doc.name}</p>
                      <p className="text-xs text-gray-500">{formatBytes(doc.size_bytes)}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownloadSingle(doc)}
                    className="p-2 rounded-lg hover:bg-[#333] text-gray-400 hover:text-white opacity-0 group-hover:opacity-100 transition-all"
                    title="Download"
                  >
                    <Download className="h-4 w-4" />
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Download All Button */}
      {documents.length > 0 && (
        <div className="p-4 border-t border-[#333]">
          <button
            onClick={handleDownloadAll}
            disabled={isDownloading}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDownloading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Downloading...
              </>
            ) : (
              <>
                <Download className="h-5 w-5" />
                Download All as ZIP
              </>
            )}
          </button>
        </div>
      )}
    </div>
  )
}
