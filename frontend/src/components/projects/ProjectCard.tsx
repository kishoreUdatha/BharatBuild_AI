'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Project } from '@/hooks/useProjects'
import { apiClient } from '@/lib/api-client'

interface ProjectCardProps {
  project: Project
  onDelete?: (projectId: string) => void
}

// Check if tech_stack indicates a Flutter project
const isFlutterProject = (techStack?: string | null): boolean => {
  if (!techStack) return false
  const stack = techStack.toLowerCase()
  return stack.includes('flutter') || stack.includes('dart')
}

const statusColors: Record<string, { bg: string; text: string; dot: string }> = {
  draft: { bg: 'bg-gray-500/10', text: 'text-gray-400', dot: 'bg-gray-400' },
  in_progress: { bg: 'bg-blue-500/10', text: 'text-blue-400', dot: 'bg-blue-400' },
  processing: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', dot: 'bg-yellow-400' },
  completed: { bg: 'bg-green-500/10', text: 'text-green-400', dot: 'bg-green-400' },
  failed: { bg: 'bg-red-500/10', text: 'text-red-400', dot: 'bg-red-400' },
}

const modeIcons: Record<string, string> = {
  student: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25',
  developer: 'M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5',
  founder: 'M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z',
  college: 'M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5',
}

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const router = useRouter()
  const [isDownloading, setIsDownloading] = useState(false)
  const [isDownloadingApk, setIsDownloadingApk] = useState(false)
  const [showMenu, setShowMenu] = useState(false)
  const [apkAvailable, setApkAvailable] = useState(false)

  const status = statusColors[project.status] || statusColors.draft
  const modeIcon = modeIcons[project.mode] || modeIcons.developer
  const isFlutter = isFlutterProject(project.tech_stack)

  // Check APK availability for Flutter projects
  useEffect(() => {
    if (!isFlutter) {
      setApkAvailable(false)
      return
    }

    const checkApk = async () => {
      try {
        const response = await apiClient.get(`/projects/${project.id}/download/apk/info`)
        setApkAvailable(response.apk_available || false)
      } catch {
        setApkAvailable(false)
      }
    }
    checkApk()
  }, [project.id, isFlutter])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  const formatTime = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const handleOpen = () => {
    router.push(`/build?project=${project.id}`)
  }

  const handleDownload = async () => {
    setIsDownloading(true)
    try {
      // Get files and create a client-side ZIP
      const filesResponse = await apiClient.getProjectFiles(project.id)

      if (!filesResponse.files || filesResponse.files.length === 0) {
        alert('No files found in this project')
        return
      }

      // Import JSZip dynamically
      const JSZip = (await import('jszip')).default
      const zip = new JSZip()

      // Fetch content for each file and add to ZIP
      for (const file of filesResponse.files) {
        if (!file.is_folder) {
          try {
            const contentResponse = await apiClient.getFileContent(project.id, file.path)
            zip.file(file.path, contentResponse.content || '')
          } catch (err) {
            console.warn(`Failed to fetch file: ${file.path}`)
          }
        }
      }

      // Generate and download ZIP
      const blob = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${project.title.replace(/[^a-z0-9]/gi, '_')}.zip`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download failed:', err)
      alert('Failed to download project')
    } finally {
      setIsDownloading(false)
    }
  }

  const handleDelete = () => {
    if (confirm('Are you sure you want to delete this project?')) {
      onDelete?.(project.id)
    }
    setShowMenu(false)
  }

  const handleDownloadApk = async () => {
    if (!isFlutter) return
    setIsDownloadingApk(true)
    try {
      const blob = await apiClient.downloadApk(project.id, 'release')
      if (blob && blob.size > 0) {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${project.title.replace(/[^a-z0-9]/gi, '_')}.apk`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } else {
        alert('APK not available. Run the project first to build the APK.')
      }
    } catch (err) {
      console.error('APK download failed:', err)
      alert('Failed to download APK. Make sure the project has been built.')
    } finally {
      setIsDownloadingApk(false)
    }
  }

  return (
    <div className="relative bg-[#1e1e1e] border border-[#333] rounded-lg overflow-hidden hover:border-[#555] transition-all duration-200 group">
      {/* Header with gradient */}
      <div className="h-24 bg-gradient-to-br from-blue-600/20 to-purple-600/20 relative">
        {/* Mode icon */}
        <div className="absolute top-3 left-3 w-10 h-10 rounded-lg bg-[#252525] flex items-center justify-center">
          <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d={modeIcon} />
          </svg>
        </div>

        {/* Status badge */}
        <div className={`absolute top-3 right-3 px-2 py-1 rounded-full flex items-center gap-1.5 ${status.bg}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`}></span>
          <span className={`text-xs font-medium capitalize ${status.text}`}>
            {project.status.replace('_', ' ')}
          </span>
        </div>

        {/* Progress bar for in-progress projects */}
        {(project.status === 'processing' || project.status === 'in_progress') && project.progress > 0 && (
          <div className="absolute bottom-0 left-0 right-0 h-1 bg-[#333]">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${project.progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="text-white font-semibold text-lg mb-1 truncate" title={project.title}>
          {project.title}
        </h3>

        {project.description && (
          <p className="text-gray-400 text-sm mb-3 line-clamp-2" title={project.description}>
            {project.description}
          </p>
        )}

        {/* Meta info */}
        <div className="flex items-center gap-3 text-xs text-gray-500 mb-4">
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
            </svg>
            {formatDate(project.created_at)}
          </span>
          <span className="flex items-center gap-1">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {formatTime(project.created_at)}
          </span>
        </div>

        {/* Token usage */}
        {project.total_tokens > 0 && (
          <div className="flex items-center gap-2 text-xs text-gray-500 mb-4">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
            </svg>
            <span>{project.total_tokens.toLocaleString()} tokens used</span>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleOpen}
            className="flex-1 py-2 px-3 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
            Open
          </button>

          <button
            onClick={handleDownload}
            disabled={isDownloading}
            className="py-2 px-3 bg-[#333] hover:bg-[#444] text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            title="Download as ZIP"
          >
            {isDownloading ? (
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
            )}
          </button>

          {/* APK Download Button - Only for Flutter projects */}
          {isFlutter && (
            <button
              onClick={handleDownloadApk}
              disabled={isDownloadingApk}
              className={`py-2 px-3 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50 ${
                apkAvailable
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-[#333] hover:bg-[#444] text-gray-400'
              }`}
              title={apkAvailable ? 'Download APK' : 'APK not built yet - Run project first'}
            >
              {isDownloadingApk ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 1.5H8.25A2.25 2.25 0 006 3.75v16.5a2.25 2.25 0 002.25 2.25h7.5A2.25 2.25 0 0018 20.25V3.75a2.25 2.25 0 00-2.25-2.25H13.5m-3 0V3h3V1.5m-3 0h3m-3 18.75h3" />
                </svg>
              )}
            </button>
          )}

          {/* More menu */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="py-2 px-2 bg-[#333] hover:bg-[#444] text-white text-sm font-medium rounded-lg transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 12.75a.75.75 0 110-1.5.75.75 0 010 1.5zM12 18.75a.75.75 0 110-1.5.75.75 0 010 1.5z" />
              </svg>
            </button>

            {showMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowMenu(false)}
                />
                <div className="absolute right-0 bottom-full mb-1 w-36 bg-[#2a2a2a] border border-[#444] rounded-lg shadow-lg z-20 overflow-hidden">
                  <button
                    onClick={handleDelete}
                    className="w-full px-3 py-2 text-left text-sm text-red-400 hover:bg-red-500/10 flex items-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
