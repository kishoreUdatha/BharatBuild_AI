'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import { Key, User, Clock, Ban, CheckCircle, XCircle, MoreVertical } from 'lucide-react'

export default function AdminApiKeysPage() {
  const { theme } = useAdminTheme()
  const [apiKeys, setApiKeys] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [actionMenu, setActionMenu] = useState<string | null>(null)

  const isDark = theme === 'dark'

  const fetchApiKeys = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      })
      if (statusFilter) params.append('status', statusFilter)

      const data = await apiClient.get<any>(`/admin/api-keys?${params.toString()}`)
      setApiKeys(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch API keys:', err)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter])

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient.get<any>('/admin/api-keys/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  useEffect(() => {
    fetchApiKeys()
    fetchStats()
  }, [fetchApiKeys, fetchStats])

  const handleRevoke = async (keyId: string) => {
    try {
      await apiClient.post(`/admin/api-keys/${keyId}/revoke`)
      fetchApiKeys()
    } catch (err) {
      console.error('Failed to revoke key:', err)
    }
  }

  const handleActivate = async (keyId: string) => {
    try {
      await apiClient.post(`/admin/api-keys/${keyId}/activate`)
      fetchApiKeys()
    } catch (err) {
      console.error('Failed to activate key:', err)
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
      active: 'bg-green-500/20 text-green-400',
      inactive: 'bg-gray-500/20 text-gray-400',
      revoked: 'bg-red-500/20 text-red-400',
    }
    return colors[status] || colors.inactive
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="API Keys"
        subtitle="Manage API keys across all users"
        onRefresh={() => { fetchApiKeys(); fetchStats(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_keys}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Keys</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.keys_by_status?.active || 0}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Active Keys</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_requests?.toLocaleString() || 0}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Requests</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_tokens_used?.toLocaleString() || 0}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Tokens Used</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className={`flex items-center gap-4 mb-6 p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            }`}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="revoked">Revoked</option>
          </select>
        </div>

        {/* Table */}
        <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    API Key
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    User
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Status
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Requests
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Last Used
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
                        <div className="animate-pulse h-6 rounded bg-gray-700" />
                      </td>
                    </tr>
                  ))
                ) : apiKeys.length === 0 ? (
                  <tr>
                    <td colSpan={6} className={`px-4 py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No API keys found
                    </td>
                  </tr>
                ) : (
                  apiKeys.map((key) => (
                    <tr key={key.id} className={isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'}>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                            isDark ? 'bg-[#252525]' : 'bg-gray-100'
                          }`}>
                            <Key className="w-4 h-4 text-blue-400" />
                          </div>
                          <div>
                            <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {key.name}
                            </div>
                            <div className={`text-xs font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                              {key.key_prefix}...
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className={`px-4 py-4 text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {key.user_email}
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(key.status)}`}>
                          {key.status}
                        </span>
                      </td>
                      <td className={`px-4 py-4 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {key.requests_count?.toLocaleString() || 0}
                      </td>
                      <td className={`px-4 py-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {formatDate(key.last_used_at)}
                      </td>
                      <td className="px-4 py-4">
                        <div className="relative">
                          <button
                            onClick={() => setActionMenu(actionMenu === key.id ? null : key.id)}
                            className={`p-2 rounded-lg ${isDark ? 'hover:bg-[#333]' : 'hover:bg-gray-100'}`}
                          >
                            <MoreVertical className="w-4 h-4" />
                          </button>

                          {actionMenu === key.id && (
                            <>
                              <div className="fixed inset-0 z-40" onClick={() => setActionMenu(null)} />
                              <div className={`absolute right-0 mt-1 w-36 rounded-lg shadow-lg border z-50 ${
                                isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
                              }`}>
                                {key.status === 'active' ? (
                                  <button
                                    onClick={() => { setActionMenu(null); handleRevoke(key.id); }}
                                    className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                      isDark ? 'text-red-400 hover:bg-[#252525]' : 'text-red-600 hover:bg-gray-100'
                                    }`}
                                  >
                                    <Ban className="w-4 h-4" />
                                    Revoke
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => { setActionMenu(null); handleActivate(key.id); }}
                                    className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                      isDark ? 'text-green-400 hover:bg-[#252525]' : 'text-green-600 hover:bg-gray-100'
                                    }`}
                                  >
                                    <CheckCircle className="w-4 h-4" />
                                    Activate
                                  </button>
                                )}
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
    </div>
  )
}
