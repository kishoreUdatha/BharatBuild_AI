'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import {
  Search,
  FileText,
  User,
  FolderKanban,
  Download,
  ChevronUp,
  ChevronDown,
  Loader2,
  X,
  FileSpreadsheet,
  Presentation,
  FileQuestion,
  File
} from 'lucide-react'

interface AdminDocument {
  id: string
  title: string
  doc_type: string | null
  file_name: string | null
  file_size: number | null
  mime_type: string | null
  created_at: string | null
  project_id: string
  project_title: string
  user_id: string
  user_email: string
  user_name: string | null
}

interface DocumentStats {
  total_documents: number
  documents_by_type: Record<string, number>
  documents_today: number
  documents_this_week: number
  documents_this_month: number
  total_storage_mb: number
}

const DOC_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'srs', label: 'SRS' },
  { value: 'report', label: 'Report' },
  { value: 'ppt', label: 'PPT' },
  { value: 'viva_qa', label: 'Viva Q&A' },
  { value: 'uml', label: 'UML' },
  { value: 'prd', label: 'PRD' },
  { value: 'business_plan', label: 'Business Plan' },
]

const getDocTypeIcon = (docType: string | null) => {
  switch (docType) {
    case 'srs':
      return <FileSpreadsheet className="w-5 h-5 text-blue-400" />
    case 'report':
      return <FileText className="w-5 h-5 text-green-400" />
    case 'ppt':
      return <Presentation className="w-5 h-5 text-orange-400" />
    case 'viva_qa':
      return <FileQuestion className="w-5 h-5 text-purple-400" />
    default:
      return <File className="w-5 h-5 text-gray-400" />
  }
}

const formatFileSize = (bytes: number | null) => {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function AdminDocumentsPage() {
  const { theme } = useAdminTheme()
  const [documents, setDocuments] = useState<AdminDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [searchInput, setSearchInput] = useState('')
  const [docTypeFilter, setDocTypeFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [stats, setStats] = useState<DocumentStats | null>(null)
  const [downloadingId, setDownloadingId] = useState<string | null>(null)

  // User filter states
  const [users, setUsers] = useState<Array<{ id: string; email: string; full_name: string | null }>>([])
  const [userFilter, setUserFilter] = useState('')
  const [userSearchInput, setUserSearchInput] = useState('')
  const [showUserSuggestions, setShowUserSuggestions] = useState(false)
  const [selectedUserName, setSelectedUserName] = useState('')

  const isDark = theme === 'dark'

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      if (searchInput) params.append('search', searchInput)
      if (docTypeFilter) params.append('doc_type', docTypeFilter)
      if (userFilter) params.append('user_id', userFilter)

      const data = await apiClient.get<any>(`/admin/documents?${params.toString()}`)
      setDocuments(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch documents:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchInput, docTypeFilter, userFilter, sortBy, sortOrder])

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient.get<DocumentStats>('/admin/documents/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  const fetchUsers = useCallback(async () => {
    try {
      const data = await apiClient.get<any>('/admin/users?page_size=1000')
      setUsers(data.items || [])
    } catch (err) {
      console.error('Failed to fetch users:', err)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  useEffect(() => {
    fetchStats()
    fetchUsers()
  }, [fetchStats, fetchUsers])

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

  const handleDownload = async (docId: string, fileName: string | null) => {
    setDownloadingId(docId)
    try {
      // Use apiClient.get with responseType: 'blob' for automatic token refresh support
      const blob = await apiClient.get<Blob>(`/admin/documents/${docId}/download`, {
        responseType: 'blob'
      })

      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = fileName || 'document'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Download failed:', err)
      alert('Failed to download document')
    } finally {
      setDownloadingId(null)
    }
  }

  // User filter functions
  const filteredUsers = userSearchInput.trim()
    ? users.filter(user => {
        const searchLower = userSearchInput.toLowerCase()
        return (
          user.email.toLowerCase().includes(searchLower) ||
          (user.full_name && user.full_name.toLowerCase().includes(searchLower))
        )
      }).slice(0, 10)
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

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getDocTypeBadge = (docType: string | null) => {
    const colors: Record<string, string> = {
      srs: 'bg-blue-500/20 text-blue-400',
      report: 'bg-green-500/20 text-green-400',
      ppt: 'bg-orange-500/20 text-orange-400',
      viva_qa: 'bg-purple-500/20 text-purple-400',
      uml: 'bg-cyan-500/20 text-cyan-400',
      prd: 'bg-pink-500/20 text-pink-400',
      business_plan: 'bg-yellow-500/20 text-yellow-400',
    }
    return colors[docType || ''] || 'bg-gray-500/20 text-gray-400'
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Document Management"
        subtitle={`${total} documents total`}
        onRefresh={() => { fetchDocuments(); fetchStats(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_documents}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Documents</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.documents_today}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Today</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.documents_this_week}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>This Week</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.documents_this_month}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>This Month</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_storage_mb} MB
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Storage Used</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold text-blue-400`}>
                {stats.documents_by_type?.srs || 0}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>SRS Documents</div>
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
              placeholder="Search documents..."
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
            value={docTypeFilter}
            onChange={(e) => { setDocTypeFilter(e.target.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            } outline-none focus:border-blue-500`}
          >
            {DOC_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>

          {/* User Search/Filter */}
          <div className="relative min-w-[220px]">
            {selectedUserName ? (
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
                      Document
                      <SortIcon field="title" />
                    </div>
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('doc_type')}
                  >
                    <div className="flex items-center gap-1">
                      Type
                      <SortIcon field="doc_type" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Project
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    User
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('file_size')}
                  >
                    <div className="flex items-center gap-1">
                      Size
                      <SortIcon field="file_size" />
                    </div>
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
                      <td colSpan={7} className="px-4 py-4">
                        <div className="animate-pulse h-8 rounded bg-gray-700" />
                      </td>
                    </tr>
                  ))
                ) : documents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className={`px-4 py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No documents found
                    </td>
                  </tr>
                ) : (
                  documents.map((doc) => (
                    <tr key={doc.id} className={`${isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'}`}>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                            isDark ? 'bg-[#252525]' : 'bg-gray-100'
                          }`}>
                            {getDocTypeIcon(doc.doc_type)}
                          </div>
                          <div>
                            <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {doc.title}
                            </div>
                            <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                              {doc.file_name || '-'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getDocTypeBadge(doc.doc_type)}`}>
                          {doc.doc_type?.toUpperCase().replace('_', ' ') || 'OTHER'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <FolderKanban className="w-4 h-4 text-gray-400" />
                          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                            {doc.project_title}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                          {doc.user_name || doc.user_email}
                        </div>
                      </td>
                      <td className={`px-4 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatFileSize(doc.file_size)}
                      </td>
                      <td className={`px-4 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(doc.created_at)}
                      </td>
                      <td className="px-4 py-4">
                        <button
                          onClick={() => handleDownload(doc.id, doc.file_name)}
                          disabled={downloadingId === doc.id}
                          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            downloadingId === doc.id
                              ? 'bg-gray-500/20 text-gray-400 cursor-not-allowed'
                              : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'
                          }`}
                        >
                          {downloadingId === doc.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Download className="w-4 h-4" />
                          )}
                          {downloadingId === doc.id ? 'Downloading...' : 'Download'}
                        </button>
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
    </div>
  )
}
