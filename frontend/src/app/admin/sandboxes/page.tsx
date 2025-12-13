'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { Pagination } from '@/components/ui/Pagination'
import { apiClient } from '@/lib/api-client'
import {
  Server,
  Activity,
  Cpu,
  HardDrive,
  RefreshCw,
  Play,
  Square,
  Trash2,
  MoreVertical,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  User,
  ExternalLink,
  Zap,
  ChevronUp,
  ChevronDown
} from 'lucide-react'

interface SandboxStats {
  total_sandboxes: number
  by_status: {
    running: number
    stopped: number
    error: number
  }
  by_health: {
    healthy: number
    unhealthy: number
    unknown: number
  }
  resource_usage: {
    total_cpu_percent: number
    total_memory_mb: number
    avg_cpu_percent: number
    avg_memory_mb: number
  }
  ports: {
    total_allocated: number
    available: number
  }
  unhealthy_containers: string[]
}

interface Sandbox {
  project_id: string
  project_name: string
  container_id: string
  user_id: string
  user_email: string
  user_name: string | null
  status: string
  health_status: string
  consecutive_failures: number
  restart_count: number
  last_health_check: string | null
  created_at: string
  last_activity: string
  idle_time_minutes: number
  port_mappings: Record<number, number>
  active_port: number | null
  resource_usage: {
    cpu_percent: number
    memory_usage_mb: number
    memory_limit_mb: number
    memory_percent: number
    status: string
  }
}

export default function AdminSandboxesPage() {
  const { theme } = useAdminTheme()
  const [sandboxes, setSandboxes] = useState<Sandbox[]>([])
  const [stats, setStats] = useState<SandboxStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')
  const [sortBy, setSortBy] = useState('last_activity')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [actionMenu, setActionMenu] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const isDark = theme === 'dark'

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

  const fetchSandboxes = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })
      if (statusFilter) params.append('status', statusFilter)

      const data = await apiClient.get<any>(`/admin/sandboxes?${params.toString()}`)
      setSandboxes(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err) {
      console.error('Failed to fetch sandboxes:', err)
      setSandboxes([])
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, statusFilter, sortBy, sortOrder])

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiClient.get<SandboxStats>('/admin/sandboxes/stats')
      setStats(data)
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }, [])

  useEffect(() => {
    fetchSandboxes()
    fetchStats()
  }, [fetchSandboxes, fetchStats])

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchSandboxes()
      fetchStats()
    }, 30000)
    return () => clearInterval(interval)
  }, [fetchSandboxes, fetchStats])

  const handleRestart = async (projectId: string) => {
    setActionLoading(projectId)
    try {
      await apiClient.post(`/admin/sandboxes/${projectId}/restart`)
      fetchSandboxes()
      fetchStats()
    } catch (err) {
      console.error('Failed to restart sandbox:', err)
    } finally {
      setActionLoading(null)
      setActionMenu(null)
    }
  }

  const handleStop = async (projectId: string) => {
    setActionLoading(projectId)
    try {
      await apiClient.post(`/admin/sandboxes/${projectId}/stop`)
      fetchSandboxes()
      fetchStats()
    } catch (err) {
      console.error('Failed to stop sandbox:', err)
    } finally {
      setActionLoading(null)
      setActionMenu(null)
    }
  }

  const handleDelete = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this sandbox?')) return
    setActionLoading(projectId)
    try {
      await apiClient.delete(`/admin/sandboxes/${projectId}`)
      fetchSandboxes()
      fetchStats()
    } catch (err) {
      console.error('Failed to delete sandbox:', err)
    } finally {
      setActionLoading(null)
      setActionMenu(null)
    }
  }

  const handleCleanupExpired = async () => {
    try {
      const result = await apiClient.post<any>('/admin/sandboxes/cleanup-expired')
      alert(`Cleaned up ${result.cleaned_count} expired sandboxes`)
      fetchSandboxes()
      fetchStats()
    } catch (err) {
      console.error('Failed to cleanup:', err)
    }
  }

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case 'unhealthy':
        return <XCircle className="w-4 h-4 text-red-400" />
      case 'starting':
        return <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
      case 'dead':
        return <XCircle className="w-4 h-4 text-gray-400" />
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      running: 'bg-green-500/20 text-green-400',
      stopped: 'bg-gray-500/20 text-gray-400',
      error: 'bg-red-500/20 text-red-400',
      creating: 'bg-blue-500/20 text-blue-400',
    }
    return colors[status] || colors.stopped
  }

  const formatUptime = (minutes: number) => {
    if (minutes < 60) return `${minutes}m`
    if (minutes < 1440) return `${Math.floor(minutes / 60)}h ${minutes % 60}m`
    return `${Math.floor(minutes / 1440)}d ${Math.floor((minutes % 1440) / 60)}h`
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Sandbox Health"
        subtitle="Monitor and manage user sandboxes"
        onRefresh={() => { fetchSandboxes(); fetchStats(); }}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Server className="w-4 h-4 text-blue-400" />
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total</span>
              </div>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.total_sandboxes}
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-green-400" />
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Running</span>
              </div>
              <div className="text-2xl font-bold text-green-400">
                {stats.by_status.running}
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Healthy</span>
              </div>
              <div className="text-2xl font-bold text-green-400">
                {stats.by_health.healthy}
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-4 h-4 text-red-400" />
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Unhealthy</span>
              </div>
              <div className="text-2xl font-bold text-red-400">
                {stats.by_health.unhealthy}
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Avg CPU</span>
              </div>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {stats.resource_usage?.avg_cpu_percent ?? 0}%
              </div>
            </div>

            <div className={`p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
              <div className="flex items-center gap-2 mb-2">
                <HardDrive className="w-4 h-4 text-orange-400" />
                <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Avg Memory</span>
              </div>
              <div className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {(stats.resource_usage?.avg_memory_mb ?? 0).toFixed(0)}MB
              </div>
            </div>
          </div>
        )}

        {/* Filters & Actions */}
        <div className={`flex items-center justify-between gap-4 mb-6 p-4 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
          <div className="flex items-center gap-4">
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
              <option value="running">Running</option>
              <option value="stopped">Stopped</option>
              <option value="error">Error</option>
            </select>
          </div>

          <button
            onClick={handleCleanupExpired}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium ${
              isDark
                ? 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30'
                : 'bg-orange-100 text-orange-600 hover:bg-orange-200'
            }`}
          >
            <Trash2 className="w-4 h-4" />
            Cleanup Expired
          </button>
        </div>

        {/* Sandboxes Table */}
        <div className={`rounded-xl border overflow-hidden ${isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'}`}>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={isDark ? 'bg-[#252525]' : 'bg-gray-50'}>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('project_name')}
                  >
                    <div className="flex items-center gap-1">
                      Project
                      <SortIcon field="project_name" />
                    </div>
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    User
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Status
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Health
                  </th>
                  <th className={`px-4 py-3 text-left text-xs font-medium uppercase ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Resources
                  </th>
                  <th
                    className={`px-4 py-3 text-left text-xs font-medium uppercase cursor-pointer ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                    onClick={() => handleSort('idle_time_minutes')}
                  >
                    <div className="flex items-center gap-1">
                      Idle Time
                      <SortIcon field="idle_time_minutes" />
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
                        <div className={`animate-pulse h-6 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                      </td>
                    </tr>
                  ))
                ) : sandboxes.length === 0 ? (
                  <tr>
                    <td colSpan={7} className={`px-4 py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      <Server className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p>No sandboxes found</p>
                    </td>
                  </tr>
                ) : (
                  sandboxes.map((sandbox) => (
                    <tr key={sandbox.project_id} className={isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'}>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                            isDark ? 'bg-[#252525]' : 'bg-gray-100'
                          }`}>
                            <Server className="w-4 h-4 text-blue-400" />
                          </div>
                          <div>
                            <div className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {sandbox.project_name}
                            </div>
                            <div className={`text-xs font-mono ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                              {sandbox.container_id}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          <User className="w-4 h-4 text-gray-400" />
                          <div>
                            <div className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                              {sandbox.user_name || sandbox.user_email}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge(sandbox.status)}`}>
                          {sandbox.status}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-2">
                          {getHealthIcon(sandbox.health_status)}
                          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                            {sandbox.health_status}
                          </span>
                          {sandbox.restart_count > 0 && (
                            <span className="text-xs text-orange-400">
                              ({sandbox.restart_count} restarts)
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-xs">
                            <Cpu className="w-3 h-3 text-purple-400" />
                            <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>
                              {sandbox.resource_usage.cpu_percent}%
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-xs">
                            <HardDrive className="w-3 h-3 text-orange-400" />
                            <span className={isDark ? 'text-gray-300' : 'text-gray-600'}>
                              {sandbox.resource_usage.memory_usage_mb.toFixed(0)}MB / {sandbox.resource_usage.memory_limit_mb}MB
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center gap-1 text-sm">
                          <Clock className="w-4 h-4 text-gray-400" />
                          <span className={sandbox.idle_time_minutes > 30 ? 'text-orange-400' : isDark ? 'text-gray-300' : 'text-gray-600'}>
                            {formatUptime(sandbox.idle_time_minutes)}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="relative">
                          <button
                            onClick={() => setActionMenu(actionMenu === sandbox.project_id ? null : sandbox.project_id)}
                            disabled={actionLoading === sandbox.project_id}
                            className={`p-2 rounded-lg ${isDark ? 'hover:bg-[#333]' : 'hover:bg-gray-100'}`}
                          >
                            {actionLoading === sandbox.project_id ? (
                              <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                              <MoreVertical className="w-4 h-4" />
                            )}
                          </button>

                          {actionMenu === sandbox.project_id && (
                            <>
                              <div className="fixed inset-0 z-40" onClick={() => setActionMenu(null)} />
                              <div className={`absolute right-0 mt-1 w-40 rounded-lg shadow-lg border z-50 ${
                                isDark ? 'bg-[#1a1a1a] border-[#333]' : 'bg-white border-gray-200'
                              }`}>
                                {sandbox.active_port && (
                                  <a
                                    href={`http://localhost:${sandbox.port_mappings[sandbox.active_port]}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                      isDark ? 'text-blue-400 hover:bg-[#252525]' : 'text-blue-600 hover:bg-gray-100'
                                    }`}
                                  >
                                    <ExternalLink className="w-4 h-4" />
                                    Open Preview
                                  </a>
                                )}
                                <button
                                  onClick={() => handleRestart(sandbox.project_id)}
                                  className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                    isDark ? 'text-green-400 hover:bg-[#252525]' : 'text-green-600 hover:bg-gray-100'
                                  }`}
                                >
                                  <RefreshCw className="w-4 h-4" />
                                  Restart
                                </button>
                                <button
                                  onClick={() => handleStop(sandbox.project_id)}
                                  className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                    isDark ? 'text-yellow-400 hover:bg-[#252525]' : 'text-yellow-600 hover:bg-gray-100'
                                  }`}
                                >
                                  <Square className="w-4 h-4" />
                                  Stop
                                </button>
                                <button
                                  onClick={() => handleDelete(sandbox.project_id)}
                                  className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                                    isDark ? 'text-red-400 hover:bg-[#252525]' : 'text-red-600 hover:bg-gray-100'
                                  }`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                  Delete
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
                totalItems={total}
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
