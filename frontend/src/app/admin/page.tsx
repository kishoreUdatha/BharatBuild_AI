'use client'

import React, { useEffect } from 'react'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import AdminHeader from '@/components/admin/AdminHeader'
import StatCard from '@/components/admin/StatCard'
import { useAdminStats } from '@/hooks/admin/useAdminStats'
import { useAdminWebSocket } from '@/hooks/admin/useAdminWebSocket'
import { useAdminStore } from '@/store/adminStore'
import {
  Users,
  FolderKanban,
  CreditCard,
  Zap,
  TrendingUp,
  Activity,
  Clock,
  UserPlus,
  Wifi,
  WifiOff,
  Bell
} from 'lucide-react'

export default function AdminDashboard() {
  const { theme } = useAdminTheme()
  const { stats, activity, loading, activityLoading, refresh } = useAdminStats()
  const { liveStats, notifications } = useAdminStore()
  const { isConnected, requestStats } = useAdminWebSocket({
    onNotification: (notification) => {
      // Show toast notification
      console.log('Admin notification:', notification)
    }
  })

  const isDark = theme === 'dark'

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(amount)
  }

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
    return num.toString()
  }

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'user_signup':
        return <UserPlus className="w-4 h-4 text-green-400" />
      case 'project_created':
        return <FolderKanban className="w-4 h-4 text-blue-400" />
      case 'payment':
        return <CreditCard className="w-4 h-4 text-purple-400" />
      default:
        return <Activity className="w-4 h-4 text-gray-400" />
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const now = new Date()
    const then = new Date(timestamp)
    const diff = now.getTime() - then.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(diff / 3600000)
    const days = Math.floor(diff / 86400000)

    if (minutes < 1) return 'Just now'
    if (minutes < 60) return `${minutes}m ago`
    if (hours < 24) return `${hours}h ago`
    return `${days}d ago`
  }

  return (
    <div className="min-h-screen">
      <AdminHeader
        title="Dashboard"
        subtitle="Overview of your platform"
        onRefresh={refresh}
        isLoading={loading}
      />

      <div className="p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Users"
            value={stats?.total_users || 0}
            subtitle={`+${stats?.new_users_today || 0} today`}
            icon={Users}
            color="blue"
            loading={loading}
            trend={{
              value: stats?.new_users_this_week || 0,
              label: 'this week',
              isPositive: true,
            }}
          />
          <StatCard
            title="Active Projects"
            value={stats?.active_projects || 0}
            subtitle={`${stats?.total_projects || 0} total`}
            icon={FolderKanban}
            color="purple"
            loading={loading}
          />
          <StatCard
            title="Revenue This Month"
            value={formatCurrency(stats?.revenue_this_month || 0)}
            subtitle={`${formatCurrency(stats?.total_revenue || 0)} total`}
            icon={CreditCard}
            color="green"
            loading={loading}
          />
          <StatCard
            title="Tokens Used Today"
            value={formatNumber(stats?.tokens_used_today || 0)}
            subtitle={`${formatNumber(stats?.total_tokens_used || 0)} total`}
            icon={Zap}
            color="orange"
            loading={loading}
          />
        </div>

        {/* Second Row Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Active Users"
            value={stats?.active_users || 0}
            subtitle="Accounts enabled"
            icon={TrendingUp}
            color="cyan"
            loading={loading}
          />
          <StatCard
            title="Active Subscriptions"
            value={stats?.active_subscriptions || 0}
            subtitle={`${stats?.total_subscriptions || 0} total`}
            icon={CreditCard}
            color="green"
            loading={loading}
          />
          <StatCard
            title="API Calls Today"
            value={formatNumber(stats?.api_calls_today || 0)}
            subtitle={`${formatNumber(stats?.total_api_calls || 0)} total`}
            icon={Activity}
            color="blue"
            loading={loading}
          />
          <StatCard
            title="New This Month"
            value={stats?.new_users_this_month || 0}
            subtitle="User signups"
            icon={UserPlus}
            color="purple"
            loading={loading}
          />
        </div>

        {/* Activity Feed */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Activity */}
          <div
            className={`rounded-xl border p-6 ${
              isDark
                ? 'bg-[#1a1a1a] border-[#333]'
                : 'bg-white border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                Recent Activity
              </h2>
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                Last 24 hours
              </span>
            </div>

            {activityLoading ? (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center gap-4 animate-pulse">
                    <div className={`w-8 h-8 rounded-full ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                    <div className="flex-1">
                      <div className={`h-4 w-48 rounded ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                      <div className={`h-3 w-32 rounded mt-2 ${isDark ? 'bg-[#333]' : 'bg-gray-200'}`} />
                    </div>
                  </div>
                ))}
              </div>
            ) : activity.length === 0 ? (
              <div className={`text-center py-8 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                No recent activity
              </div>
            ) : (
              <div className="space-y-4">
                {activity.slice(0, 10).map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-start gap-4 p-3 rounded-lg transition-colors ${
                      isDark ? 'hover:bg-[#252525]' : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      isDark ? 'bg-[#252525]' : 'bg-gray-100'
                    }`}>
                      {getActivityIcon(item.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {item.title}
                      </p>
                      <p className={`text-sm truncate ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                        {item.description}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                      <Clock className="w-3 h-3" />
                      {getTimeAgo(item.timestamp)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Quick Stats */}
          <div
            className={`rounded-xl border p-6 ${
              isDark
                ? 'bg-[#1a1a1a] border-[#333]'
                : 'bg-white border-gray-200'
            }`}
          >
            <h2 className={`text-lg font-semibold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Quick Stats
            </h2>

            <div className="space-y-4">
              <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    User Growth Rate
                  </span>
                  <span className="text-sm text-green-400">
                    +{stats?.new_users_this_week || 0} this week
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-green-500 rounded-full h-2 transition-all"
                    style={{
                      width: `${Math.min(((stats?.new_users_this_week || 0) / Math.max(stats?.total_users || 1, 1)) * 100 * 10, 100)}%`,
                    }}
                  />
                </div>
              </div>

              <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Active vs Total Users
                  </span>
                  <span className="text-sm text-blue-400">
                    {stats?.total_users
                      ? Math.round(((stats?.active_users || 0) / stats.total_users) * 100)
                      : 0}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-blue-500 rounded-full h-2 transition-all"
                    style={{
                      width: `${stats?.total_users
                        ? ((stats?.active_users || 0) / stats.total_users) * 100
                        : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Active Projects Ratio
                  </span>
                  <span className="text-sm text-purple-400">
                    {stats?.total_projects
                      ? Math.round(((stats?.active_projects || 0) / stats.total_projects) * 100)
                      : 0}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-purple-500 rounded-full h-2 transition-all"
                    style={{
                      width: `${stats?.total_projects
                        ? ((stats?.active_projects || 0) / stats.total_projects) * 100
                        : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div className={`p-4 rounded-lg ${isDark ? 'bg-[#252525]' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    Subscription Conversion
                  </span>
                  <span className="text-sm text-orange-400">
                    {stats?.total_users
                      ? Math.round(((stats?.active_subscriptions || 0) / stats.total_users) * 100)
                      : 0}%
                  </span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-orange-500 rounded-full h-2 transition-all"
                    style={{
                      width: `${stats?.total_users
                        ? ((stats?.active_subscriptions || 0) / stats.total_users) * 100
                        : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
