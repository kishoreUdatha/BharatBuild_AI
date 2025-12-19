'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AdminThemeProvider, useAdminTheme } from '@/contexts/AdminThemeContext'
import { useAdminStore } from '@/store/adminStore'
import AdminSidebar from '@/components/admin/AdminSidebar'
import { useAuth } from '@/hooks/useAuth'

function AdminLayoutContent({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, isLoading, isAuthenticated } = useAuth()
  const { sidebarCollapsed } = useAdminStore()
  const { theme } = useAdminTheme()
  const [mounted, setMounted] = useState(false)

  const isDark = theme === 'dark'

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login?redirect=/admin')
    }
  }, [isLoading, isAuthenticated, router])

  useEffect(() => {
    // Check if user is admin
    if (!isLoading && user && user.role !== 'admin' && !user.is_superuser) {
      router.push('/build')
    }
  }, [isLoading, user, router])

  if (!mounted) {
    return null
  }

  if (isLoading) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDark ? 'bg-[#121212]' : 'bg-gray-50'}`}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>Loading admin panel...</p>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  // Check admin role
  if (user && user.role !== 'admin' && !user.is_superuser) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDark ? 'bg-[#121212]' : 'bg-gray-50'}`}>
        <div className={`text-center p-8 rounded-xl ${isDark ? 'bg-[#1a1a1a]' : 'bg-white'}`}>
          <h1 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
            Access Denied
          </h1>
          <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
            You don't have permission to access the admin panel.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`min-h-screen ${isDark ? 'bg-[#121212]' : 'bg-gray-50'}`}>
      <AdminSidebar />
      <main
        className={`transition-all duration-300 ${
          sidebarCollapsed ? 'ml-16' : 'ml-64'
        }`}
      >
        {children}
      </main>
    </div>
  )
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminThemeProvider>
      <AdminLayoutContent>{children}</AdminLayoutContent>
    </AdminThemeProvider>
  )
}
