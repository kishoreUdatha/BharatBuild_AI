'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAdminStore } from '@/store/adminStore'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import { useAuth } from '@/hooks/useAuth'
import {
  Search,
  Bell,
  Menu,
  User,
  LogOut,
  Settings,
  ChevronDown,
  RefreshCw
} from 'lucide-react'

interface AdminHeaderProps {
  title?: string
  subtitle?: string
  onRefresh?: () => void
  isLoading?: boolean
}

export default function AdminHeader({ title, subtitle, onRefresh, isLoading }: AdminHeaderProps) {
  const router = useRouter()
  const { sidebarCollapsed, setSidebarCollapsed, isConnected, lastUpdate, notifications, clearNotifications } = useAdminStore()
  const { theme } = useAdminTheme()
  const { user, logout } = useAuth()
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  const unreadCount = notifications.length

  const isDark = theme === 'dark'

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      router.push(`/admin/users?search=${encodeURIComponent(searchQuery)}`)
    }
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  return (
    <header
      className={`h-16 flex items-center justify-between px-6 border-b ${
        isDark
          ? 'bg-[#121212] border-[#333]'
          : 'bg-white border-gray-200'
      }`}
    >
      {/* Left Side */}
      <div className="flex items-center gap-4">
        {/* Mobile Menu Toggle */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className={`lg:hidden p-2 rounded-lg ${
            isDark
              ? 'text-gray-400 hover:text-white hover:bg-[#252525]'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Title */}
        {title && (
          <div>
            <h1 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {title}
            </h1>
            {subtitle && (
              <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                {subtitle}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-4">
        {/* Search */}
        <form onSubmit={handleSearch} className="hidden md:block">
          <div className="relative">
            <Search className={`absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 ${
              isDark ? 'text-gray-500' : 'text-gray-400'
            }`} />
            <input
              type="text"
              placeholder="Search users, projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={`w-64 pl-9 pr-4 py-2 rounded-lg border text-sm ${
                isDark
                  ? 'bg-[#252525] border-[#333] text-white placeholder-gray-500 focus:border-blue-500'
                  : 'bg-gray-50 border-gray-200 text-gray-900 placeholder-gray-400 focus:border-blue-500'
              } outline-none transition-colors`}
            />
          </div>
        </form>

        {/* Refresh Button */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className={`p-2 rounded-lg transition-colors ${
              isDark
                ? 'text-gray-400 hover:text-white hover:bg-[#252525]'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            } ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
            title="Refresh data"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        )}

        {/* Connection Status */}
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-500'
            }`}
            title={isConnected ? 'Real-time connected' : 'Real-time disconnected'}
          />
          {lastUpdate && (
            <span className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
              {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className={`relative p-2 rounded-lg transition-colors ${
              isDark
                ? 'text-gray-400 hover:text-white hover:bg-[#252525]'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setShowNotifications(false)}
              />
              <div
                className={`absolute right-0 mt-2 w-80 rounded-lg shadow-lg border z-50 ${
                  isDark
                    ? 'bg-[#1a1a1a] border-[#333]'
                    : 'bg-white border-gray-200'
                }`}
              >
                <div className={`px-4 py-3 border-b flex items-center justify-between ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                  <span className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    Notifications
                  </span>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => clearNotifications()}
                      className="text-xs text-blue-500 hover:text-blue-400"
                    >
                      Clear all
                    </button>
                  )}
                </div>
                <div className="max-h-64 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className={`px-4 py-8 text-center text-sm ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                      No notifications
                    </div>
                  ) : (
                    notifications.slice(0, 10).map((notification, i) => (
                      <div
                        key={i}
                        className={`px-4 py-3 border-b last:border-0 ${
                          isDark ? 'border-[#333] hover:bg-[#252525]' : 'border-gray-100 hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-start gap-2">
                          <div className={`w-2 h-2 mt-1.5 rounded-full ${
                            notification.level === 'success' ? 'bg-green-500' :
                            notification.level === 'warning' ? 'bg-yellow-500' :
                            notification.level === 'error' ? 'bg-red-500' : 'bg-blue-500'
                          }`} />
                          <div className="flex-1 min-w-0">
                            <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {notification.title}
                            </p>
                            <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                              {notification.message}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* User Menu */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
              isDark
                ? 'hover:bg-[#252525]'
                : 'hover:bg-gray-100'
            }`}
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <User className="w-4 h-4 text-white" />
            </div>
            <span className={`hidden sm:block text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {user?.full_name || user?.email || 'Admin'}
            </span>
            <ChevronDown className={`w-4 h-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`} />
          </button>

          {/* Dropdown Menu */}
          {showUserMenu && (
            <>
              <div
                className="fixed inset-0 z-40"
                onClick={() => setShowUserMenu(false)}
              />
              <div
                className={`absolute right-0 mt-2 w-48 rounded-lg shadow-lg border z-50 ${
                  isDark
                    ? 'bg-[#1a1a1a] border-[#333]'
                    : 'bg-white border-gray-200'
                }`}
              >
                <div className={`px-4 py-3 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
                  <p className={`text-sm font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {user?.full_name || 'Admin User'}
                  </p>
                  <p className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                    {user?.email}
                  </p>
                </div>
                <div className="py-1">
                  <button
                    onClick={() => {
                      setShowUserMenu(false)
                      router.push('/admin/settings')
                    }}
                    className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                      isDark
                        ? 'text-gray-300 hover:bg-[#252525]'
                        : 'text-gray-700 hover:bg-gray-100'
                    }`}
                  >
                    <Settings className="w-4 h-4" />
                    Settings
                  </button>
                  <button
                    onClick={handleLogout}
                    className={`w-full flex items-center gap-2 px-4 py-2 text-sm ${
                      isDark
                        ? 'text-red-400 hover:bg-[#252525]'
                        : 'text-red-600 hover:bg-gray-100'
                    }`}
                  >
                    <LogOut className="w-4 h-4" />
                    Logout
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
