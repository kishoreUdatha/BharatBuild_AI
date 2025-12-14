'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import { MessageSquare, Star, User, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

export default function AdminFeedbackPage() {
  const { theme } = useAdminTheme()
  const [feedback, setFeedback] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const isDark = theme === 'dark'

  const fetchFeedback = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      })
      if (statusFilter) params.append('status', statusFilter)
      if (typeFilter) params.append('type', typeFilter)

      const data = await apiClient.get<any>(`/admin/feedback?${params.toString()}`)
      setFeedback(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch feedback:', err)
      setFeedback([])
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter, typeFilter])

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient.get<any>('/admin/feedback/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  useEffect(() => {
    fetchFeedback()
    fetchStats()
  }, [fetchFeedback, fetchStats])

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'resolved':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'reviewed':
        return <AlertCircle className="w-4 h-4 text-blue-400" />
      case 'dismissed':
        return <XCircle className="w-4 h-4 text-gray-400" />
      default:
        return <Clock className="w-4 h-4 text-yellow-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-500/20 text-yellow-400',
      reviewed: 'bg-blue-500/20 text-blue-400',
      resolved: 'bg-green-500/20 text-green-400',
      dismissed: 'bg-gray-500/20 text-gray-400',
    }
    return colors[status] || colors.pending
  }

  const getTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      bug: 'bg-red-500/20 text-red-400',
      feature: 'bg-purple-500/20 text-purple-400',
      general: 'bg-blue-500/20 text-blue-400',
      praise: 'bg-green-500/20 text-green-400',
    }
    return colors[type] || colors.general
  }

  const renderStars = (rating: number | null) => {
    if (!rating) return null
    return (
      <div className="flex items-center gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            className={`w-3 h-3 ${star <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-600'}`}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Feedback"
        subtitle="User feedback and suggestions"
        onRefresh={() => { fetchFeedback(); fetchStats(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_feedback}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Feedback</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold text-yellow-400`}>
                {stats.pending_count}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Pending</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2">
                <span className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  {stats.average_rating?.toFixed(1) || '-'}
                </span>
                <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Avg Rating</div>
            </div>
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.feedback_in_period}
              </div>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Last 30 Days</div>
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
            <option value="pending">Pending</option>
            <option value="reviewed">Reviewed</option>
            <option value="resolved">Resolved</option>
            <option value="dismissed">Dismissed</option>
          </select>

          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-gray-50 border-gray-200 text-gray-900'
            }`}
          >
            <option value="">All Types</option>
            <option value="bug">Bug Report</option>
            <option value="feature">Feature Request</option>
            <option value="general">General</option>
            <option value="praise">Praise</option>
          </select>
        </div>

        {/* Feedback List */}
        <div className={`rounded-xl border ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
          <div className={`divide-y ${isDark ? 'divide-[#333]' : 'divide-gray-200'}`}>
            {loading ? (
              [...Array(3)].map((_, i) => (
                <div key={i} className="p-6 animate-pulse">
                  <div className="flex items-start gap-4">
                    <div className={`w-10 h-10 rounded-full ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                    <div className="flex-1 space-y-3">
                      <div className={`h-4 w-48 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                      <div className={`h-3 w-full rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                      <div className={`h-3 w-2/3 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                    </div>
                  </div>
                </div>
              ))
            ) : feedback.length === 0 ? (
              <div className={`p-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No feedback found</p>
              </div>
            ) : (
              feedback.map((item) => (
                <div key={item.id} className={`p-6 ${isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'}`}>
                  <div className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium">
                      {(item.user_name || item.user_email)?.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-2">
                        <span className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                          {item.user_name || item.user_email}
                        </span>
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getTypeBadge(item.type)}`}>
                          {item.type}
                        </span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${getStatusBadge(item.status)}`}>
                          {getStatusIcon(item.status)}
                          {item.status}
                        </span>
                        {item.rating && renderStars(item.rating)}
                      </div>
                      <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {item.message}
                      </p>
                      {item.admin_response && (
                        <div className={`mt-3 p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                          <div className={`text-xs font-medium mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            Admin Response:
                          </div>
                          <p className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                            {item.admin_response}
                          </p>
                        </div>
                      )}
                      <div className={`mt-2 text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        {formatDate(item.created_at)}
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {totalPages > 1 && (
            <div className={`px-6 py-3 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
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
