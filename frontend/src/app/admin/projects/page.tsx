'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import {
  Search,
  FolderKanban,
  User,
  Calendar,
  MoreVertical,
  Trash2,
  Eye,
  HardDrive,
  FileCode,
  ChevronUp,
  ChevronDown,
  Download,
  Upload,
  X,
  Loader2
} from 'lucide-react'

interface AdminProject {
  id: string
  title: string
  description: string | null
  status: string
  mode: string
  user_id: string
  user_email: string
  user_name: string | null
  files_count: number
  storage_size_mb: number
  created_at: string
  updated_at: string | null
  last_activity: string | null
}

const STATUS_OPTIONS = [
  { value: '', label: 'All Status' },
  { value: 'draft', label: 'Draft' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
]

export default function AdminProjectsPage() {
  const { theme } = useAdminTheme()
  const [projects, setProjects] = useState<AdminProject[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [actionMenuProject, setActionMenuProject] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [stats, setStats] = useState<any>(null)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadUserId, setUploadUserId] = useState('')
  const [uploadProjectName, setUploadProjectName] = useState('')
  const [uploadLoading, setUploadLoading] = useState(false)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)
  const [users, setUsers] = useState<Array<{ id: string; email: string; full_name: string | null }>>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [userFilter, setUserFilter] = useState('')
  const [userSearchInput, setUserSearchInput] = useState('')
  const [showUserSuggestions, setShowUserSuggestions] = useState(false)
  const [selectedUserName, setSelectedUserName] = useState('')

  const isDark = theme === 'dark'

  const fetchProjects = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      if (searchInput) params.append('search', searchInput)
      if (statusFilter) params.append('status', statusFilter)
      if (userFilter) params.append('user_id', userFilter)

      const data = await apiClient.get<any>(`/admin/projects?${params.toString()}`)
      setProjects(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch projects:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchInput, statusFilter, userFilter, sortBy, sortOrder])

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <div className="w-4 h-4" />
    return sortOrder === 'asc' ? (
      <ChevronUp className="w-4 h-4 text-blue-400" />
    ) : (
      <ChevronDown className="w-4 h-4 text-blue-400" />
    )
  }

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient.get<any>('/admin/projects/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true)
    try {
      const data = await apiClient.get<any>('/admin/users?page_size=1000')
      setUsers(data.items || [])
    } catch (err) {
      console.error('Failed to fetch users:', err)
    } finally {
      setUsersLoading(false)
    }
  }, [])

  const handleDownload = async (projectId: string, projectTitle: string) => {
    setDownloadingId(projectId)
    setActionMenuProject(null)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/projects/${projectId}/download`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!response.ok) {
        throw new Error('Download failed')
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const safeTitle = projectTitle.replace(/[^a-zA-Z0-9\s\-_]/g, '').trim() || 'project'
      a.download = `${safeTitle}_${projectId.slice(0, 8)}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Download failed:', err)
      alert('Failed to download project')
    } finally {
      setDownloadingId(null)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile || !uploadUserId) {
      alert('Please select a file and user')
      return
    }

    setUploadLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      formData.append('user_id', uploadUserId)
      if (uploadProjectName) {
        formData.append('project_name', uploadProjectName)
      }

      const token = localStorage.getItem('token')
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/admin/projects/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Upload failed')
      }

      const result = await response.json()
      alert(`Project "${result.project_name}" uploaded successfully!`)
      setShowUploadModal(false)
      setUploadFile(null)
      setUploadUserId('')
      setUploadProjectName('')
      fetchProjects()
    } catch (err: any) {
      console.error('Upload failed:', err)
      alert(err.message || 'Failed to upload project')
    } finally {
      setUploadLoading(false)
    }
  }

  const openUploadModal = () => {
    setShowUploadModal(true)
  }

  // Filter users based on search input
  const filteredUsers = userSearchInput.trim()
    ? users.filter(user => {
        const searchLower = userSearchInput.toLowerCase()
        return (
          user.email.toLowerCase().includes(searchLower) ||
          (user.full_name && user.full_name.toLowerCase().includes(searchLower))
        )
      }).slice(0, 10) // Limit to 10 suggestions
    : []

  const handleUserSelect = (user: { id: string; email: string; full_name: string | null }) => {
    setUserFilter(user.id)
    setSelectedUserName(user.full_name || user.email)
    setUserSearchInput('')
    setShowUserSuggestions(false)
    setPage(1)
  }

  const clearUserFilter = () => {
    setUserFilter('')
    setSelectedUserName('')
    setUserSearchInput('')
    setPage(1)
  }

  const handleDelete = async (projectId: string) => {
    if (deleteConfirm === projectId) {
      try {
        await apiClient.delete(`/admin/projects/${projectId}`)
        fetchProjects()
        setDeleteConfirm(null)
      } catch (err) {
        console.error('Delete failed:', err)
      }
    } else {
      setDeleteConfirm(projectId)
      setTimeout(() => setDeleteConfirm(null), 3000)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      draft: 'bg-gray-500/20 text-gray-400',
      in_progress: 'bg-blue-500/20 text-blue-400',
      processing: 'bg-yellow-500/20 text-yellow-400',
      completed: 'bg-green-500/20 text-green-400',
      failed: 'bg-red-500/20 text-red-400',
    }
    return colors[status] || colors.draft
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Project Management"
        subtitle={`${total} projects total`}
        onRefresh={() => { fetchProjects(); fetchStats(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_projects}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Projects</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.active_projects}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Active (7 days)</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.projects_today}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Created Today</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_files}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Files</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className={`flex flex-wrap items-center gap-4 mb-6 p-4 rounded-xl ${
          isDark ? 'bg-[#1a1a1a]' : 'bg-white'
        }`}>
          <div className="relative flex-1 min-w-[200px]">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${
              isDark ? 'text-gray-500' : 'text-gray-400'
            }`} />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchInput}
              onChange={(e) => { setSearchInput(e.target.value); setPage(1); }}
              className={`w-full pl-10 pr-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                  : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
              } outline-none focus:border-blue-500`}
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {/* User Search/Filter */}
          <div className="relative min-w-[220px]">
            {selectedUserName ? (
              // Show selected user with clear button
              <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white'
                  : 'bg-gray-50 border-gray-200 text-gray-900'
              }`}>
                <User className="w-4 h-4 text-blue-400 flex-shrink-0" />
                <span className="truncate flex-1">{selectedUserName}</span>
                <button
                  onClick={clearUserFilter}
                  className={`p-0.5 rounded hover:bg-gray-600/30 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ) : (
              // Show search input
              <>
                <User className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${
                  isDark ? 'text-gray-500' : 'text-gray-400'
                }`} />
                <input
                  type="text"
                  placeholder="Search by user..."
                  value={userSearchInput}
                  onChange={(e) => {
                    setUserSearchInput(e.target.value)
                    setShowUserSuggestions(true)
                  }}
                  onFocus={() => setShowUserSuggestions(true)}
                  className={`w-full pl-10 pr-4 py-2 rounded-lg border text-sm ${
                    isDark
                      ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                      : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
                  } outline-none focus:border-blue-500`}
                />
              </>
            )}

            {/* User Suggestions Dropdown */}
            {showUserSuggestions && filteredUsers.length > 0 && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowUserSuggestions(false)} />
                <div className={`absolute top-full left-0 right-0 mt-1 rounded-lg shadow-lg border z-50 max-h-60 overflow-y-auto ${
                  isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
                }`}>
                  {filteredUsers.map((user) => (
                    <button
                      key={user.id}
                      onClick={() => handleUserSelect(user)}
                      className={`w-full flex flex-col px-4 py-2 text-left text-sm ${
                        isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-100'
                      }`}
                    >
                      <span className={isDark ? 'text-white' : 'text-gray-900'}>
                        {user.full_name || user.email}
                      </span>
                      {user.full_name && (
                        <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          {user.email}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          <button
            onClick={openUploadModal}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Upload className="w-4 h-4" />
            Upload Project
          </button>
        </div>

        {/* Table */}
        <div className={`rounded-xl border overflow-hidden ${
          isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
        }`}>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('title')}
                  >
                    <div className="flex items-center gap-1">
                      Project
                      <SortIcon field="title" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Owner
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('status')}
                  >
                    <div className="flex items-center gap-1">
                      Status
                      <SortIcon field="status" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Files
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('created_at')}
                  >
                    <div className="flex items-center gap-1">
                      Created
                      <SortIcon field="created_at" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
                {loading ? (
                  [...Array(5)].map((_, i) => (
                    <tr key={i}>
                      <td colSpan={6} className="px-4 py-4">
                        <div className="animate-pulse h-8 rounded bg-gray-700" />
                      </td>
                    </tr>
                  ))
                ) : projects.length === 0 ? (
                  <tr>
                    <td colSpan={6} className={`px-4 py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No projects found
                    </td>
                  </tr>
                ) : (
                  projects.map((project) => (
                    <tr key={project.id} className={`${isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'}`}>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            isDark ? 'bg-[#252525]' : 'bg-gray-100'
                          }`}>
                            <FolderKanban className="w-5 h-5 text-blue-400" />
                          </div>
                          <div>
                            <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {project.title}
                            </div>
                            <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                              {project.mode}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                          {project.user_name || project.user_email}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(project.status)}`}>
                          {project.status}
                        </span>
                      </td>
                      <td className={`px-4 py-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        <div className="flex items-center gap-1">
                          <FileCode className="w-4 h-4" />
                          {project.files_count}
                        </div>
                      </td>
                      <td className={`px-4 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(project.created_at)}
                      </td>
                      <td className="px-4 py-4">
                        <div className="relative">
                          <button
                            onClick={() => setActionMenuProject(actionMenuProject === project.id ? null : project.id)}
                            className={`p-2 rounded-lg ${isDark ? 'hover:bg-[#333]' : 'hover:bg-gray-100'}`}
                          >
                            <MoreVertical className="w-4 h-4" />
                          </button>

                          {actionMenuProject === project.id && (
                            <>
                              <div className="fixed inset-0 z-40" onClick={() => setActionMenuProject(null)} />
                              <div className={`absolute right-0 mt-1 w-40 rounded-lg shadow-lg border z-50 ${
                                isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
                              }`}>
                                <button
                                  onClick={() => handleDownload(project.id, project.title)}
                                  disabled={downloadingId === project.id}
                                  className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                    isDark
                                      ? 'text-gray-300 hover:bg-[#252525]'
                                      : 'text-gray-700 hover:bg-gray-100'
                                  } ${downloadingId === project.id ? 'opacity-50' : ''}`}
                                >
                                  {downloadingId === project.id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Download className="w-4 h-4" />
                                  )}
                                  {downloadingId === project.id ? 'Downloading...' : 'Download ZIP'}
                                </button>
                                <button
                                  onClick={() => {
                                    setActionMenuProject(null)
                                    handleDelete(project.id)
                                  }}
                                  className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                    deleteConfirm === project.id
                                      ? 'bg-red-500/20 text-red-400'
                                      : isDark
                                        ? 'text-red-400 hover:bg-[#252525]'
                                        : 'text-red-600 hover:bg-gray-100'
                                  }`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                  {deleteConfirm === project.id ? 'Confirm?' : 'Delete'}
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className={`px-4 py-3 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
              <Pagination
                currentPage={page}
                totalPages={totalPages}
                pageSize={pageSize}
                total={total}
                onPageChange={setPage}
                onPageSizeChange={(size) => { setPageSize(size); setPage(1); }}
              />
            </div>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className={`w-full max-w-md mx-4 rounded-xl shadow-xl ${
            isDark ? 'bg-[#1a1a1a]' : 'bg-white'
          }`}>
            <div className={`flex items-center justify-between p-4 border-b ${
              isDark ? 'border-[#333]' : 'border-gray-200'
            }`}>
              <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Upload Project
              </h3>
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setUploadFile(null)
                  setUploadUserId('')
                  setUploadProjectName('')
                }}
                className={`p-1 rounded-lg ${isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-100'}`}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* User Selection */}
              <div>
                <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Target User *
                </label>
                <select
                  value={uploadUserId}
                  onChange={(e) => setUploadUserId(e.target.value)}
                  disabled={usersLoading}
                  className={`w-full px-4 py-2 rounded-lg border text-sm ${
                    isDark
                      ? 'bg-[#252525] border-[#333] text-white'
                      : 'bg-gray-50 border-gray-200 text-gray-900'
                  } outline-none focus:border-blue-500`}
                >
                  <option value="">
                    {usersLoading ? 'Loading users...' : 'Select a user'}
                  </option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.full_name ? `${user.full_name} (${user.email})` : user.email}
                    </option>
                  ))}
                </select>
              </div>

              {/* Project Name */}
              <div>
                <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Project Name (optional)
                </label>
                <input
                  type="text"
                  value={uploadProjectName}
                  onChange={(e) => setUploadProjectName(e.target.value)}
                  placeholder="Leave empty to use ZIP filename"
                  className={`w-full px-4 py-2 rounded-lg border text-sm ${
                    isDark
                      ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500'
                      : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400'
                  } outline-none focus:border-blue-500`}
                />
              </div>

              {/* File Upload */}
              <div>
                <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  Project ZIP File *
                </label>
                <div
                  className={`relative border-2 border-dashed rounded-lg p-6 text-center ${
                    isDark ? 'border-[#333] hover:border-[#444]' : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  <input
                    type="file"
                    accept=".zip"
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  {uploadFile ? (
                    <div className={`flex items-center justify-center gap-2 ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                      <FileCode className="w-5 h-5" />
                      <span>{uploadFile.name}</span>
                    </div>
                  ) : (
                    <div className={isDark ? 'text-gray-400' : 'text-gray-500'}>
                      <Upload className="w-8 h-8 mx-auto mb-2" />
                      <p>Click or drag to upload ZIP file</p>
                      <p className="text-xs mt-1">Max 50MB</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className={`flex justify-end gap-3 p-4 border-t ${
              isDark ? 'border-[#333]' : 'border-gray-200'
            }`}>
              <button
                onClick={() => {
                  setShowUploadModal(false)
                  setUploadFile(null)
                  setUploadUserId('')
                  setUploadProjectName('')
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium ${
                  isDark
                    ? 'bg-[#252525] text-gray-300 hover:bg-[#333]'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={uploadLoading || !uploadFile || !uploadUserId}
                className={`px-4 py-2 rounded-lg text-sm font-medium text-white ${
                  uploadLoading || !uploadFile || !uploadUserId
                    ? 'bg-blue-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {uploadLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Uploading...
                  </span>
                ) : (
                  'Upload'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
