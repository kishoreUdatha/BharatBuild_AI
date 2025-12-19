'use client'

import { useRouter } from 'next/navigation'
import {
  FolderOpen,
  FileText,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  ExternalLink
} from 'lucide-react'

interface Project {
  id: string
  title: string
  description?: string
  status: 'draft' | 'in_progress' | 'processing' | 'completed' | 'failed'
  progress?: number
  created_at: string
  documents_count?: number
}

interface DashboardProjectCardProps {
  project: Project
  onSelectForDocuments: (project: Project) => void
  isSelected?: boolean
}

const statusConfig = {
  draft: { icon: FileText, color: 'text-gray-400', bg: 'bg-gray-500/20', label: 'Draft' },
  in_progress: { icon: Loader2, color: 'text-blue-400', bg: 'bg-blue-500/20', label: 'In Progress' },
  processing: { icon: Loader2, color: 'text-yellow-400', bg: 'bg-yellow-500/20', label: 'Processing' },
  completed: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-500/20', label: 'Completed' },
  failed: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/20', label: 'Failed' }
}

export function DashboardProjectCard({ project, onSelectForDocuments, isSelected }: DashboardProjectCardProps) {
  const router = useRouter()
  const status = statusConfig[project.status] || statusConfig.draft
  const StatusIcon = status.icon

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  const handleOpen = () => {
    router.push(`/build?project=${project.id}`)
  }

  return (
    <div
      className={`group relative rounded-xl border transition-all duration-200 ${
        isSelected
          ? 'border-blue-500 bg-blue-500/10'
          : 'border-[#333] bg-[#1a1a1a] hover:border-[#444] hover:bg-[#222]'
      }`}
    >
      <div className="p-4 space-y-3">
        {/* Header with status */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-white truncate">{project.title}</h3>
            {project.description && (
              <p className="text-sm text-gray-400 line-clamp-1 mt-1">{project.description}</p>
            )}
          </div>
          <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full text-xs ${status.bg} ${status.color}`}>
            <StatusIcon className={`h-3 w-3 ${project.status === 'processing' || project.status === 'in_progress' ? 'animate-spin' : ''}`} />
            <span>{status.label}</span>
          </div>
        </div>

        {/* Progress bar for in-progress projects */}
        {(project.status === 'in_progress' || project.status === 'processing') && project.progress !== undefined && (
          <div className="w-full bg-[#333] rounded-full h-1.5">
            <div
              className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${project.progress}%` }}
            />
          </div>
        )}

        {/* Meta info */}
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{formatDate(project.created_at)}</span>
          </div>
          {project.documents_count !== undefined && project.documents_count > 0 && (
            <div className="flex items-center gap-1 text-blue-400">
              <FileText className="h-3 w-3" />
              <span>{project.documents_count} docs</span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t border-[#333]">
          <button
            onClick={handleOpen}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open
          </button>
          <button
            onClick={() => onSelectForDocuments(project)}
            className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              isSelected
                ? 'bg-blue-500 text-white'
                : 'bg-[#333] hover:bg-[#444] text-gray-300'
            }`}
          >
            <FolderOpen className="h-3.5 w-3.5" />
            Documents
          </button>
        </div>
      </div>
    </div>
  )
}
