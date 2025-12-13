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
import { Users, Zap, Activity, TrendingUp } from 'lucide-react'

const COLORS = ['#3b82f6', '#8b5cf6', '#f97316', '#22c55e', '#ef4444']

export default function AdminAnalyticsPage() {
  const { theme } = useAdminTheme()
  const [userGrowth, setUserGrowth] = useState<any>(null)
  const [tokenUsage, setTokenUsage] = useState<any>(null)
  const [apiCalls, setApiCalls] = useState<any>(null)
  const [modelUsage, setModelUsage] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

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

  useEffect(() => {
    fetchAnalytics()
  }, [fetchAnalytics])

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
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
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
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
      </div>
    </div>
  )
}
