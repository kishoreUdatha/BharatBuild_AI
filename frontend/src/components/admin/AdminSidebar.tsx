'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useAdminStore } from '@/store/adminStore'
import { useAdminTheme } from '@/contexts/AdminThemeContext'
import {
  LayoutDashboard,
  Users,
  FolderKanban,
  CreditCard,
  BarChart3,
  Layers,
  Key,
  FileText,
  Settings,
  MessageSquare,
  ChevronLeft,
  ChevronRight,
  Moon,
  Sun,
  Shield,
  Server,
  GraduationCap,
  FileSpreadsheet,
  Trophy,
  Ticket
} from 'lucide-react'

const navItems = [
  { href: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/admin/users', label: 'Users', icon: Users },
  { href: '/admin/enrollments', label: 'Enrollments', icon: GraduationCap },
  { href: '/admin/campus-drive', label: 'Campus Drive', icon: Trophy },
  { href: '/admin/projects', label: 'Projects', icon: FolderKanban },
  { href: '/admin/documents', label: 'Documents', icon: FileSpreadsheet },
  { href: '/admin/sandboxes', label: 'Sandboxes', icon: Server },
  { href: '/admin/billing', label: 'Billing', icon: CreditCard },
  { href: '/admin/coupons', label: 'Coupons', icon: Ticket },
  { href: '/admin/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/admin/plans', label: 'Plans', icon: Layers },
  { href: '/admin/api-keys', label: 'API Keys', icon: Key },
  { href: '/admin/audit-logs', label: 'Audit Logs', icon: FileText },
  { href: '/admin/settings', label: 'Settings', icon: Settings },
  { href: '/admin/feedback', label: 'Feedback', icon: MessageSquare },
]

export default function AdminSidebar() {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebar } = useAdminStore()
  const { theme, toggleTheme } = useAdminTheme()

  const isDark = theme === 'dark'

  return (
    <aside
      className={`fixed left-0 top-0 h-screen transition-all duration-300 z-40 ${
        sidebarCollapsed ? 'w-16' : 'w-64'
      } ${
        isDark
          ? 'bg-[#1a1a1a] border-r border-[#333]'
          : 'bg-white border-r border-gray-200'
      }`}
    >
      {/* Logo */}
      <div className={`h-16 flex items-center px-4 border-b ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Shield className="w-5 h-5 text-white" />
          </div>
          {!sidebarCollapsed && (
            <span className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
              Admin Panel
            </span>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto" style={{ height: 'calc(100vh - 128px)' }}>
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const isActive = pathname === item.href ||
              (item.href !== '/admin' && pathname?.startsWith(item.href))
            const Icon = item.icon

            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${
                    isActive
                      ? isDark
                        ? 'bg-blue-600/20 text-blue-400'
                        : 'bg-blue-50 text-blue-600'
                      : isDark
                        ? 'text-gray-400 hover:text-white hover:bg-[#252525]'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                  } ${sidebarCollapsed ? 'justify-center' : ''}`}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" />
                  {!sidebarCollapsed && (
                    <span className="text-sm font-medium">{item.label}</span>
                  )}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Bottom Actions */}
      <div className={`h-16 flex items-center justify-between px-3 border-t ${isDark ? 'border-[#333]' : 'border-gray-200'}`}>
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-lg transition-colors ${
            isDark
              ? 'text-gray-400 hover:text-white hover:bg-[#252525]'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </button>

        {/* Collapse Toggle */}
        <button
          onClick={toggleSidebar}
          className={`p-2 rounded-lg transition-colors ${
            isDark
              ? 'text-gray-400 hover:text-white hover:bg-[#252525]'
              : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }`}
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-5 h-5" />
          ) : (
            <ChevronLeft className="w-5 h-5" />
          )}
        </button>
      </div>
    </aside>
  )
}
