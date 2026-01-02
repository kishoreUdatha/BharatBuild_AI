'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import { apiClient } from '@/lib/api-client'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts'
import { Users, Zap, Activity, TrendingUp, DollarSign, FolderOpen, ChevronDown, ChevronUp, Search, Calendar, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, Download, AlertTriangle, BarChart3, PieChart as PieChartIcon, TrendingDown } from 'lucide-react'
import { AreaChart, Area } from 'recharts'

const COLORS = ['#3b82f6', '#8b5cf6', '#f97316', '#22c55e', '#ef4444']

export default function AdminAnalyticsPage() {
  const { theme } = useAdminTheme()
  const [userGrowth, setUserGrowth] = useState<any>(null)
  const [tokenUsage, setTokenUsage] = useState<any>(null)
  const [apiCalls, setApiCalls] = useState<any>(null)
  const [modelUsage, setModelUsage] = useState<any>(null)
  const [projectCosts, setProjectCosts] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)
  const [expandedProject, setExpandedProject] = useState<string | null>(null)
  const [projectDetails, setProjectDetails] = useState<Record<string, any>>({})

  // Search, filter, and sorting state for project costs
  const [searchUser, setSearchUser] = useState('')
  const [searchProject, setSearchProject] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [sortBy, setSortBy] = useState('cost')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [currentPage, setCurrentPage] = useState(0)
  const [costLoading, setCostLoading] = useState(false)
  const pageSize = 20

  // Advanced analytics state
  const [costTrends, setCostTrends] = useState<any>(null)
  const [costsByUser, setCostsByUser] = useState<any>(null)
  const [costStatistics, setCostStatistics] = useState<any>(null)
  const [costsByModel, setCostsByModel] = useState<any>(null)
  const [costAlerts, setCostAlerts] = useState<any>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'trends' | 'users' | 'models' | 'alerts'>('overview')
  const [alertThreshold, setAlertThreshold] = useState(0.5)

  const isDark = theme === 'dark'

  const fetchAnalytics = useCallback(async () => {
    setLoading(true)
    try {
      const [growth, tokens, calls, models] = await Promise.all([
        apiClient.get<any>(`/admin/analytics/user-growth?days=${days}`),
        apiClient.get<any>(`/admin/analytics/token-usage?days=${days}`),
        apiClient.get<any>(`/admin/analytics/api-calls?days=${days}`),
        apiClient.get<any>(`/admin/analytics/model-usage?days=${days}`),
      ])
      setUserGrowth(growth)
      setTokenUsage(tokens)
      setApiCalls(calls)
      setModelUsage(models)
    } catch (err) {
      console.error('Failed to fetch analytics:', err)
    } finally {
      setLoading(false)
    }
  }, [days])

  // Fetch project costs with filters
  const fetchProjectCosts = useCallback(async () => {
    setCostLoading(true)
    try {
      const params = new URLSearchParams({
        days: days.toString(),
        limit: pageSize.toString(),
        offset: (currentPage * pageSize).toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      if (searchUser.trim()) params.append('search_user', searchUser.trim())
      if (searchProject.trim()) params.append('search_project', searchProject.trim())
      if (startDate) params.append('start_date_filter', startDate)
      if (endDate) params.append('end_date_filter', endDate)

      const costs = await apiClient.get<any>(`/admin/analytics/project-costs?${params.toString()}`)
      setProjectCosts(costs)
    } catch (err) {
      console.error('Failed to fetch project costs:', err)
    } finally {
      setCostLoading(false)
    }
  }, [days, currentPage, sortBy, sortOrder, searchUser, searchProject, startDate, endDate])

  const fetchProjectDetails = useCallback(async (projectId: string) => {
    if (projectDetails[projectId]) {
      setExpandedProject(expandedProject === projectId ? null : projectId)
      return
    }
    try {
      const details = await apiClient.get<any>(`/admin/analytics/project-costs/${projectId}`)
      setProjectDetails(prev => ({ ...prev, [projectId]: details }))
      setExpandedProject(projectId)
    } catch (err) {
      console.error('Failed to fetch project details:', err)
    }
  }, [projectDetails, expandedProject])

  // Fetch advanced analytics data
  const fetchAdvancedAnalytics = useCallback(async () => {
    try {
      const [trends, byUser, stats, byModel, alerts] = await Promise.all([
        apiClient.get<any>(`/admin/analytics/project-costs/trends?days=${days}`),
        apiClient.get<any>(`/admin/analytics/project-costs/by-user?days=${days}&limit=10`),
        apiClient.get<any>(`/admin/analytics/project-costs/statistics?days=${days}`),
        apiClient.get<any>(`/admin/analytics/project-costs/by-model?days=${days}`),
        apiClient.get<any>(`/admin/analytics/project-costs/alerts?days=${Math.min(days, 30)}&cost_threshold_usd=${alertThreshold}`),
      ])
      setCostTrends(trends)
      setCostsByUser(byUser)
      setCostStatistics(stats)
      setCostsByModel(byModel)
      setCostAlerts(alerts)
    } catch (err) {
      console.error('Failed to fetch advanced analytics:', err)
    }
  }, [days, alertThreshold])

  // Export costs to CSV
  const exportToCSV = async () => {
    try {
      const params = new URLSearchParams({
        days: days.toString(),
        format: 'csv'
      })
      if (searchUser) params.append('search_user', searchUser)
      if (searchProject) params.append('search_project', searchProject)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/admin/analytics/project-costs/export?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('bharatbuild-auth') ? JSON.parse(localStorage.getItem('bharatbuild-auth')!).state?.token : ''}`
        }
      })

      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `project_costs_${new Date().toISOString().split('T')[0]}.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
        a.remove()
      }
    } catch (err) {
      console.error('Failed to export:', err)
    }
  }

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  useEffect(() => {
    fetchProjectCosts()
  }, [fetchProjectCosts])

  useEffect(() => {
    fetchAdvancedAnalytics()
  }, [fetchAdvancedAnalytics])

  // Handle sort column click
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(column)
      setSortOrder('desc')
    }
    setCurrentPage(0)
  }

  // Get sort icon for column
  const getSortIcon = (column: string) => {
    if (sortBy !== column) {
      return <ArrowUpDown className="w-3 h-3 ml-1 opacity-50" />
    }
    return sortOrder === 'asc'
      ? <ArrowUp className="w-3 h-3 ml-1" />
      : <ArrowDown className="w-3 h-3 ml-1" />
  }

  // Handle search with debounce
  const handleSearchChange = (type: 'user' | 'project', value: string) => {
    if (type === 'user') setSearchUser(value)
    else setSearchProject(value)
    setCurrentPage(0)
  }

  // Clear all filters
  const clearFilters = () => {
    setSearchUser('')
    setSearchProject('')
    setStartDate('')
    setEndDate('')
    setSortBy('cost')
    setSortOrder('desc')
    setCurrentPage(0)
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const formatCurrency = (amount: number, currency: 'USD' | 'INR' = 'USD') => {
    if (currency === 'INR') {
      return `₹${amount.toFixed(2)}`
    }
    return `$${amount.toFixed(4)}`
  }

  const chartTheme = {
    bg: isDark ? '#1a1a1a' : '#ffffff',
    text: isDark ? '#9ca3af' : '#6b7280',
    grid: isDark ? '#333333' : '#e5e7eb',
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Analytics"
        subtitle="Platform usage and growth metrics"
        onRefresh={fetchAnalytics}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Period Selector */}
        <div className="flex justify-end mb-6">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className={`px-4 py-2 rounded-lg border text-sm ${
              isDark
                ? 'bg-[#252525] border-[#333] text-white'
                : 'bg-white border-gray-200 text-gray-900'
            }`}
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-6 mb-8">
          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Users className="w-5 h-5 text-blue-400" />
              </div>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Users</span>
            </div>
            <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {formatNumber(userGrowth?.total_users || 0)}
            </div>
            <div className="text-sm text-green-400">
              +{userGrowth?.growth_rate?.toFixed(1) || 0}% growth
            </div>
          </div>

          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <DollarSign className="w-5 h-5 text-emerald-400" />
              </div>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Cost</span>
            </div>
            <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              ${(projectCosts?.summary?.total_cost_usd || 0).toFixed(2)}
            </div>
            <div className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              {projectCosts?.summary?.total_projects || 0} projects
            </div>
          </div>

          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <Zap className="w-5 h-5 text-purple-400" />
              </div>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Tokens Used</span>
            </div>
            <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {formatNumber(tokenUsage?.total_tokens || 0)}
            </div>
          </div>

          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-orange-500/10 rounded-lg">
                <Activity className="w-5 h-5 text-orange-400" />
              </div>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>API Calls</span>
            </div>
            <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {formatNumber(apiCalls?.total_calls || 0)}
            </div>
            <div className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              Avg {apiCalls?.average_response_time?.toFixed(0) || 0}ms
            </div>
          </div>

          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <TrendingUp className="w-5 h-5 text-green-400" />
              </div>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Growth Rate</span>
            </div>
            <div className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {userGrowth?.growth_rate?.toFixed(1) || 0}%
            </div>
          </div>
        </div>

        {/* Charts Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Growth Chart */}
          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              User Growth
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={userGrowth?.data?.slice(-30) || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                  <XAxis
                    dataKey="date"
                    stroke={chartTheme.text}
                    fontSize={12}
                    tickFormatter={(v) => v.slice(5)}
                  />
                  <YAxis stroke={chartTheme.text} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.bg,
                      border: `1px solid ${chartTheme.grid}`,
                      borderRadius: '8px',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Token Usage Chart */}
          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Token Usage by Model
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={Object.entries(tokenUsage?.tokens_by_model || {}).map(([name, value]) => ({
                      name,
                      value,
                    }))}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {Object.keys(tokenUsage?.tokens_by_model || {}).map((_, index) => (
                      <Cell key={index} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.bg,
                      border: `1px solid ${chartTheme.grid}`,
                      borderRadius: '8px',
                    }}
                  />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* API Calls Chart */}
          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Daily API Calls
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={apiCalls?.daily_calls?.slice(-30) || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke={chartTheme.grid} />
                  <XAxis
                    dataKey="date"
                    stroke={chartTheme.text}
                    fontSize={12}
                    tickFormatter={(v) => v.slice(5)}
                  />
                  <YAxis stroke={chartTheme.text} fontSize={12} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartTheme.bg,
                      border: `1px solid ${chartTheme.grid}`,
                      borderRadius: '8px',
                    }}
                  />
                  <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Top Users */}
          <div className={`p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
            <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Top Users by Token Usage
            </h3>
            <div className="space-y-3">
              {(tokenUsage?.top_users || []).slice(0, 5).map((user: any, i: number) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium ${
                      isDark ? 'bg-[#252525] text-white' : 'bg-gray-100 text-gray-900'
                    }`}>
                      {i + 1}
                    </div>
                    <div>
                      <div className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {user.name || user.email}
                      </div>
                      <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        {user.email}
                      </div>
                    </div>
                  </div>
                  <div className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                    {formatNumber(user.tokens)} tokens
                  </div>
                </div>
              ))}
              {(!tokenUsage?.top_users || tokenUsage.top_users.length === 0) && (
                <div className={`text-center py-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  No data available
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Project Costs Section */}
        <div className={`mt-8 p-6 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-500/10 rounded-lg">
                <DollarSign className="w-5 h-5 text-emerald-400" />
              </div>
              <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Cost Analytics
              </h3>
              {costLoading && (
                <div className="w-4 h-4 border-2 border-emerald-400 border-t-transparent rounded-full animate-spin" />
              )}
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={exportToCSV}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  isDark
                    ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                    : 'bg-emerald-100 text-emerald-600 hover:bg-emerald-200'
                }`}
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
              {costAlerts?.summary?.total_alerts > 0 && (
                <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg ${
                  costAlerts.summary.critical > 0 ? 'bg-red-500/20 text-red-400' :
                  costAlerts.summary.high > 0 ? 'bg-orange-500/20 text-orange-400' :
                  'bg-yellow-500/20 text-yellow-400'
                }`}>
                  <AlertTriangle className="w-4 h-4" />
                  <span className="text-xs font-medium">{costAlerts.summary.total_alerts} Alerts</span>
                </div>
              )}
            </div>
          </div>

          {/* Tab Navigation */}
          <div className={`flex gap-1 mb-6 p-1 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-100'}`}>
            {[
              { id: 'overview', label: 'Overview', icon: FolderOpen },
              { id: 'trends', label: 'Trends', icon: TrendingUp },
              { id: 'users', label: 'By User', icon: Users },
              { id: 'models', label: 'By Model', icon: BarChart3 },
              { id: 'alerts', label: 'Alerts', icon: AlertTriangle },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  activeTab === tab.id
                    ? isDark ? 'bg-[#333] text-white' : 'bg-white text-gray-900 shadow-sm'
                    : isDark ? 'text-gray-400 hover:text-white' : 'text-gray-500 hover:text-gray-900'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Statistics Cards */}
          {costStatistics && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
              <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Total Cost</div>
                <div className={`text-lg font-bold ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                  ${costStatistics.cost_statistics?.total_usd?.toFixed(2) || '0.00'}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Average</div>
                <div className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  ${costStatistics.cost_statistics?.mean_usd?.toFixed(4) || '0.0000'}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Median</div>
                <div className={`text-lg font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                  ${costStatistics.cost_statistics?.median_usd?.toFixed(4) || '0.0000'}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>95th Percentile</div>
                <div className={`text-lg font-bold ${isDark ? 'text-orange-400' : 'text-orange-600'}`}>
                  ${costStatistics.cost_statistics?.percentile_95?.toFixed(4) || '0.0000'}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Max Cost</div>
                <div className={`text-lg font-bold ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                  ${costStatistics.cost_statistics?.max_usd?.toFixed(4) || '0.0000'}
                </div>
              </div>
              <div className={`p-3 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>Outliers</div>
                <div className={`text-lg font-bold ${isDark ? 'text-purple-400' : 'text-purple-600'}`}>
                  {costStatistics.outliers?.count || 0} ({costStatistics.outliers?.percentage || 0}%)
                </div>
              </div>
            </div>
          )}

          {/* Trends Tab Content */}
          {activeTab === 'trends' && costTrends && (
            <div className="mb-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                {/* Cost Trend Chart */}
                <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                  <h4 className={`text-sm font-medium mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Daily Cost Trend
                  </h4>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={costTrends.daily_data || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke={isDark ? '#333' : '#e5e7eb'} />
                        <XAxis
                          dataKey="date"
                          stroke={isDark ? '#9ca3af' : '#6b7280'}
                          fontSize={10}
                          tickFormatter={(v) => v?.slice(5) || ''}
                        />
                        <YAxis stroke={isDark ? '#9ca3af' : '#6b7280'} fontSize={10} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: isDark ? '#1a1a1a' : '#fff',
                            border: `1px solid ${isDark ? '#333' : '#e5e7eb'}`,
                            borderRadius: '8px',
                          }}
                          formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']}
                        />
                        <Area
                          type="monotone"
                          dataKey="cost_usd"
                          stroke="#10b981"
                          fill="#10b98133"
                          strokeWidth={2}
                        />
                        <Line
                          type="monotone"
                          dataKey="moving_avg_7d"
                          stroke="#8b5cf6"
                          strokeWidth={2}
                          dot={false}
                          strokeDasharray="5 5"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs">
                    <div className="flex items-center gap-1.5">
                      <div className="w-3 h-3 rounded bg-emerald-500" />
                      <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>Daily Cost</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <div className="w-3 h-0.5 bg-purple-500" style={{ borderStyle: 'dashed' }} />
                      <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>7-Day Avg</span>
                    </div>
                  </div>
                </div>

                {/* Growth Stats */}
                <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                  <h4 className={`text-sm font-medium mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Period Analysis
                  </h4>
                  <div className="space-y-4">
                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Total Period Cost</span>
                      <span className={`text-lg font-bold ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                        ${costTrends.trends?.total_cost_usd?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Avg Daily Cost</span>
                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        ${costTrends.trends?.avg_daily_cost_usd?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Max Daily Cost</span>
                      <span className={`text-sm font-medium ${isDark ? 'text-red-400' : 'text-red-600'}`}>
                        ${costTrends.trends?.max_daily_cost_usd?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <hr className={isDark ? 'border-[#333]' : 'border-gray-200'} />
                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>First Half Total</span>
                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        ${costTrends.trends?.first_half_cost_usd?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>Second Half Total</span>
                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        ${costTrends.trends?.second_half_cost_usd?.toFixed(4) || '0.0000'}
                      </span>
                    </div>
                    <div className={`flex justify-between items-center p-3 rounded-lg ${
                      (costTrends.trends?.growth_rate_percent || 0) > 0
                        ? 'bg-red-500/10'
                        : 'bg-green-500/10'
                    }`}>
                      <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>Period Growth</span>
                      <div className="flex items-center gap-1.5">
                        {(costTrends.trends?.growth_rate_percent || 0) > 0
                          ? <TrendingUp className="w-4 h-4 text-red-400" />
                          : <TrendingDown className="w-4 h-4 text-green-400" />}
                        <span className={`text-lg font-bold ${
                          (costTrends.trends?.growth_rate_percent || 0) > 0 ? 'text-red-400' : 'text-green-400'
                        }`}>
                          {(costTrends.trends?.growth_rate_percent || 0) > 0 ? '+' : ''}{costTrends.trends?.growth_rate_percent || 0}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Users Tab Content */}
          {activeTab === 'users' && costsByUser && (
            <div className="mb-6">
              <div className={`rounded-lg overflow-hidden ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className={`px-4 py-3 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                  <h4 className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Top Users by Cost
                  </h4>
                </div>
                <div className="divide-y divide-[#333]">
                  {(costsByUser.users || []).map((user: any, idx: number) => (
                    <div key={user.user_id} className="px-4 py-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                          idx === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                          idx === 1 ? 'bg-gray-500/20 text-gray-400' :
                          idx === 2 ? 'bg-orange-500/20 text-orange-400' :
                          isDark ? 'bg-[#333] text-gray-400' : 'bg-gray-200 text-gray-500'
                        }`}>
                          {idx + 1}
                        </div>
                        <div>
                          <div className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                            {user.name || user.email}
                          </div>
                          <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                            {user.project_count} projects • {formatNumber(user.total_tokens)} tokens
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`text-sm font-bold ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                          ${user.cost_usd?.toFixed(4)}
                        </div>
                        <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          ${user.avg_cost_per_project?.toFixed(4)}/project
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Models Tab Content */}
          {activeTab === 'models' && costsByModel && (
            <div className="mb-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Model Cost Chart */}
                <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                  <h4 className={`text-sm font-medium mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Cost by Model
                  </h4>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={(costsByModel.models || []).map((m: any) => ({
                            name: m.model,
                            value: m.cost_usd
                          }))}
                          cx="50%"
                          cy="50%"
                          innerRadius={50}
                          outerRadius={80}
                          paddingAngle={2}
                          dataKey="value"
                        >
                          {(costsByModel.models || []).map((_: any, index: number) => (
                            <Cell key={index} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: number) => [`$${value.toFixed(4)}`, 'Cost']}
                          contentStyle={{
                            backgroundColor: isDark ? '#1a1a1a' : '#fff',
                            border: `1px solid ${isDark ? '#333' : '#e5e7eb'}`,
                            borderRadius: '8px',
                          }}
                        />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Model Details */}
                <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                  <h4 className={`text-sm font-medium mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Model Breakdown
                  </h4>
                  <div className="space-y-3">
                    {(costsByModel.models || []).map((model: any, idx: number) => (
                      <div key={model.model} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div className="w-3 h-3 rounded" style={{ backgroundColor: COLORS[idx % COLORS.length] }} />
                          <span className={`text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{model.model}</span>
                        </div>
                        <div className="text-right">
                          <div className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                            ${model.cost_usd?.toFixed(4)} ({model.percentage_of_total_cost}%)
                          </div>
                          <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                            {formatNumber(model.total_tokens)} tokens • {model.api_calls} calls
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Alerts Tab Content */}
          {activeTab === 'alerts' && (
            <div className="mb-6">
              <div className={`p-4 rounded-lg mb-4 ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      Cost Alert Threshold
                    </h4>
                    <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      Projects exceeding this cost will be flagged
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>$</span>
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={alertThreshold}
                      onChange={(e) => setAlertThreshold(parseFloat(e.target.value) || 0)}
                      className={`w-24 px-3 py-1.5 text-sm rounded-lg border ${
                        isDark
                          ? 'bg-[#1a1a1a] border-[#333] text-white'
                          : 'bg-white border-gray-200 text-gray-900'
                      }`}
                    />
                    <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>USD</span>
                  </div>
                </div>
              </div>

              {costAlerts?.alerts?.length > 0 ? (
                <div className="space-y-3">
                  {costAlerts.alerts.map((alert: any) => (
                    <div
                      key={alert.project_id}
                      className={`p-4 rounded-lg border-l-4 ${
                        alert.severity === 'critical'
                          ? `${isDark ? 'bg-red-500/10' : 'bg-red-50'} border-red-500`
                          : alert.severity === 'high'
                          ? `${isDark ? 'bg-orange-500/10' : 'bg-orange-50'} border-orange-500`
                          : `${isDark ? 'bg-yellow-500/10' : 'bg-yellow-50'} border-yellow-500`
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <AlertTriangle className={`w-4 h-4 ${
                              alert.severity === 'critical' ? 'text-red-400' :
                              alert.severity === 'high' ? 'text-orange-400' : 'text-yellow-400'
                            }`} />
                            <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {alert.project_name}
                            </span>
                            <span className={`text-xs px-2 py-0.5 rounded-full uppercase font-medium ${
                              alert.severity === 'critical'
                                ? 'bg-red-500/20 text-red-400'
                                : alert.severity === 'high'
                                ? 'bg-orange-500/20 text-orange-400'
                                : 'bg-yellow-500/20 text-yellow-400'
                            }`}>
                              {alert.severity}
                            </span>
                          </div>
                          <div className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                            {alert.user_email} • {alert.api_calls} API calls • {formatNumber(alert.total_tokens)} tokens
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={`text-lg font-bold ${
                            alert.severity === 'critical' ? 'text-red-400' :
                            alert.severity === 'high' ? 'text-orange-400' : 'text-yellow-400'
                          }`}>
                            ${alert.cost_usd?.toFixed(4)}
                          </div>
                          <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                            +${alert.threshold_exceeded_by?.toFixed(4)} over threshold
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className={`text-center py-8 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                  No cost alerts for the current threshold
                </div>
              )}
            </div>
          )}

          {/* Overview Tab - Original Project List */}
          {activeTab === 'overview' && (
            <>
              <div className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {projectCosts?.pagination?.total || 0} projects | Avg: ${(projectCosts?.summary?.avg_cost_per_project || 0).toFixed(4)}/project
              </div>

          {/* Search and Filter Controls */}
          <div className={`mb-6 p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Search by User */}
              <div>
                <label className={`block text-xs font-medium mb-1.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Search by User
                </label>
                <div className="relative">
                  <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                  <input
                    type="text"
                    placeholder="Email..."
                    value={searchUser}
                    onChange={(e) => handleSearchChange('user', e.target.value)}
                    className={`w-full pl-9 pr-3 py-2 text-sm rounded-lg border ${
                      isDark
                        ? 'bg-[#1a1a1a] border-[#333] text-white placeholder-gray-500'
                        : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400'
                    } focus:outline-none focus:ring-2 focus:ring-emerald-500/50`}
                  />
                </div>
              </div>

              {/* Search by Project */}
              <div>
                <label className={`block text-xs font-medium mb-1.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Search by Project
                </label>
                <div className="relative">
                  <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                  <input
                    type="text"
                    placeholder="Project name..."
                    value={searchProject}
                    onChange={(e) => handleSearchChange('project', e.target.value)}
                    className={`w-full pl-9 pr-3 py-2 text-sm rounded-lg border ${
                      isDark
                        ? 'bg-[#1a1a1a] border-[#333] text-white placeholder-gray-500'
                        : 'bg-white border-gray-200 text-gray-900 placeholder-gray-400'
                    } focus:outline-none focus:ring-2 focus:ring-emerald-500/50`}
                  />
                </div>
              </div>

              {/* Start Date */}
              <div>
                <label className={`block text-xs font-medium mb-1.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  Start Date
                </label>
                <div className="relative">
                  <Calendar className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => { setStartDate(e.target.value); setCurrentPage(0); }}
                    className={`w-full pl-9 pr-3 py-2 text-sm rounded-lg border ${
                      isDark
                        ? 'bg-[#1a1a1a] border-[#333] text-white'
                        : 'bg-white border-gray-200 text-gray-900'
                    } focus:outline-none focus:ring-2 focus:ring-emerald-500/50`}
                  />
                </div>
              </div>

              {/* End Date */}
              <div>
                <label className={`block text-xs font-medium mb-1.5 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  End Date
                </label>
                <div className="relative">
                  <Calendar className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} />
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => { setEndDate(e.target.value); setCurrentPage(0); }}
                    className={`w-full pl-9 pr-3 py-2 text-sm rounded-lg border ${
                      isDark
                        ? 'bg-[#1a1a1a] border-[#333] text-white'
                        : 'bg-white border-gray-200 text-gray-900'
                    } focus:outline-none focus:ring-2 focus:ring-emerald-500/50`}
                  />
                </div>
              </div>
            </div>

            {/* Clear Filters Button */}
            {(searchUser || searchProject || startDate || endDate) && (
              <div className="mt-3 flex justify-end">
                <button
                  onClick={clearFilters}
                  className={`text-xs px-3 py-1.5 rounded-lg ${
                    isDark
                      ? 'bg-[#333] text-gray-300 hover:bg-[#444]'
                      : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                  } transition-colors`}
                >
                  Clear Filters
                </button>
              </div>
            )}
          </div>

          {/* Cost by Agent Breakdown */}
          {projectCosts?.agent_breakdown && Object.keys(projectCosts.agent_breakdown).length > 0 && (
            <div className="mb-6">
              <h4 className={`text-sm font-medium mb-3 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Cost by Agent Type
              </h4>
              <div className="flex flex-wrap gap-3">
                {Object.entries(projectCosts.agent_breakdown).map(([agent, data]: [string, any]) => (
                  <div
                    key={agent}
                    className={`px-3 py-2 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}
                  >
                    <div className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{agent}</div>
                    <div className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                      ${(data?.cost_usd || 0).toFixed(4)}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Projects Table */}
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className={`border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                  <th
                    onClick={() => handleSort('name')}
                    className={`py-3 px-4 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                  >
                    <div className="flex items-center">
                      Project
                      {getSortIcon('name')}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort('user')}
                    className={`py-3 px-4 text-left text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                  >
                    <div className="flex items-center">
                      User
                      {getSortIcon('user')}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort('cost')}
                    className={`py-3 px-4 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                  >
                    <div className="flex items-center justify-end">
                      Cost (USD)
                      {getSortIcon('cost')}
                    </div>
                  </th>
                  <th className={`py-3 px-4 text-right text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                    Cost (INR)
                  </th>
                  <th
                    onClick={() => handleSort('tokens')}
                    className={`py-3 px-4 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                  >
                    <div className="flex items-center justify-end">
                      Tokens
                      {getSortIcon('tokens')}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort('calls')}
                    className={`py-3 px-4 text-right text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                  >
                    <div className="flex items-center justify-end">
                      API Calls
                      {getSortIcon('calls')}
                    </div>
                  </th>
                  <th
                    onClick={() => handleSort('date')}
                    className={`py-3 px-4 text-center text-xs font-medium uppercase tracking-wider cursor-pointer hover:text-emerald-400 transition-colors ${isDark ? 'text-gray-500' : 'text-gray-400'}`}
                  >
                    <div className="flex items-center justify-center">
                      Date
                      {getSortIcon('date')}
                    </div>
                  </th>
                  <th className={`py-3 px-4 text-center text-xs font-medium uppercase tracking-wider ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                    Details
                  </th>
                </tr>
              </thead>
              <tbody>
                {(projectCosts?.projects || []).map((project: any) => (
                  <React.Fragment key={project.project_id}>
                    <tr
                      className={`border-b cursor-pointer transition-colors ${
                        isDark
                          ? 'border-[#333] hover:bg-[#252525]'
                          : 'border-gray-100 hover:bg-gray-50'
                      } ${expandedProject === project.project_id ? (isDark ? 'bg-[#252525]' : 'bg-gray-50') : ''}`}
                      onClick={() => fetchProjectDetails(project.project_id)}
                    >
                      <td className="py-3 px-4">
                        <div className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                          {project.project_name || 'Untitled Project'}
                        </div>
                      </td>
                      <td className={`py-3 px-4 text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {project.user_email}
                      </td>
                      <td className={`py-3 px-4 text-right text-sm font-medium ${isDark ? 'text-emerald-400' : 'text-emerald-600'}`}>
                        ${project.cost_usd?.toFixed(4) || '0.0000'}
                      </td>
                      <td className={`py-3 px-4 text-right text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        ₹{project.cost_inr.toFixed(2)}
                      </td>
                      <td className={`py-3 px-4 text-right text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {formatNumber(project.total_tokens)}
                      </td>
                      <td className={`py-3 px-4 text-right text-sm ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                        {project.api_calls}
                      </td>
                      <td className={`py-3 px-4 text-center text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {project.created_at ? new Date(project.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td className="py-3 px-4 text-center">
                        {expandedProject === project.project_id ? (
                          <ChevronUp className={`w-4 h-4 inline ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                        ) : (
                          <ChevronDown className={`w-4 h-4 inline ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
                        )}
                      </td>
                    </tr>
                    {expandedProject === project.project_id && projectDetails[project.project_id] && (
                      <tr className={isDark ? 'bg-[#1f1f1f]' : 'bg-gray-25'}>
                        <td colSpan={8} className="p-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Cost by Agent */}
                            <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-white border'}`}>
                              <h5 className={`text-sm font-medium mb-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                                Cost by Agent
                              </h5>
                              <div className="space-y-2">
                                {Object.entries(projectDetails[project.project_id]?.by_agent || {}).map(([agent, data]: [string, any]) => (
                                  <div key={agent} className="flex justify-between items-center">
                                    <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{agent}</span>
                                    <div className="text-right">
                                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                                        ${data.cost_usd.toFixed(4)}
                                      </span>
                                      <span className={`text-xs ml-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                        ({formatNumber(data.tokens)} tokens)
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Cost by Operation */}
                            <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-white border'}`}>
                              <h5 className={`text-sm font-medium mb-3 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                                Cost by Operation
                              </h5>
                              <div className="space-y-2">
                                {Object.entries(projectDetails[project.project_id]?.by_operation || {}).map(([op, data]: [string, any]) => (
                                  <div key={op} className="flex justify-between items-center">
                                    <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{op}</span>
                                    <div className="text-right">
                                      <span className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                                        ${data.cost_usd.toFixed(4)}
                                      </span>
                                      <span className={`text-xs ml-2 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                        ({data.calls} calls)
                                      </span>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
                {(!projectCosts?.projects || projectCosts.projects.length === 0) && (
                  <tr>
                    <td colSpan={8} className={`py-8 text-center ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      {costLoading ? 'Loading...' : 'No project cost data available'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {projectCosts?.pagination && projectCosts.pagination.total > pageSize && (
            <div className={`mt-4 flex items-center justify-between pt-4 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
              <div className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Showing {currentPage * pageSize + 1} to {Math.min((currentPage + 1) * pageSize, projectCosts.pagination.total)} of {projectCosts.pagination.total} projects
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
                  disabled={currentPage === 0}
                  className={`p-2 rounded-lg transition-colors ${
                    currentPage === 0
                      ? 'opacity-50 cursor-not-allowed'
                      : isDark
                        ? 'hover:bg-[#333] text-gray-300'
                        : 'hover:bg-gray-100 text-gray-600'
                  } ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <span className={`text-sm px-3 py-1 rounded-lg ${isDark ? 'bg-[#252525] text-white' : 'bg-gray-100 text-gray-900'}`}>
                  {currentPage + 1} / {Math.ceil(projectCosts.pagination.total / pageSize)}
                </span>
                <button
                  onClick={() => setCurrentPage(prev => prev + 1)}
                  disabled={!projectCosts.pagination.has_more}
                  className={`p-2 rounded-lg transition-colors ${
                    !projectCosts.pagination.has_more
                      ? 'opacity-50 cursor-not-allowed'
                      : isDark
                        ? 'hover:bg-[#333] text-gray-300'
                        : 'hover:bg-gray-100 text-gray-600'
                  } ${isDark ? 'text-gray-400' : 'text-gray-500'}`}
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
