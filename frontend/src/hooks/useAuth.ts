'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { setAccessToken, removeAccessToken } from '@/lib/auth-utils'

interface User {
  id: string
  email: string
  name?: string
  full_name?: string
  role?: string
  is_superuser?: boolean
}

interface UseAuthReturn {
  isAuthenticated: boolean
  isLoading: boolean
  user: User | null
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  checkAuth: () => boolean
  requireAuth: (redirectUrl?: string) => boolean
}

export function useAuth(): UseAuthReturn {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const router = useRouter()

  // Check if user is authenticated
  const checkAuth = useCallback((): boolean => {
    if (typeof window === 'undefined') return false
    const token = localStorage.getItem('access_token')
    return !!token
  }, [])

  // Require authentication - redirect to login if not authenticated
  const requireAuth = useCallback((redirectUrl?: string): boolean => {
    const authenticated = checkAuth()
    if (!authenticated) {
      // Store the intended destination
      if (redirectUrl) {
        sessionStorage.setItem('redirectAfterLogin', redirectUrl)
      }
      router.push('/login')
      return false
    }
    return true
  }, [checkAuth, router])

  // Load user data from token
  const loadUser = useCallback(() => {
    if (typeof window === 'undefined') return

    const token = localStorage.getItem('access_token')
    if (token) {
      try {
        // Decode JWT payload (base64)
        const payload = token.split('.')[1]
        const decoded = JSON.parse(atob(payload))

        // Also check localStorage for full user info (stored during login)
        const storedUser = localStorage.getItem('user')
        const userInfo = storedUser ? JSON.parse(storedUser) : null

        setUser({
          id: decoded.sub,
          email: decoded.email || '',
          name: decoded.name || userInfo?.full_name,
          role: decoded.role || userInfo?.role,
          is_superuser: userInfo?.is_superuser || false
        })
        setIsAuthenticated(true)
      } catch (error) {
        console.error('Failed to decode token:', error)
        setIsAuthenticated(false)
        setUser(null)
      }
    } else {
      setIsAuthenticated(false)
      setUser(null)
    }
    setIsLoading(false)
  }, [])

  // Login function
  const login = useCallback(async (email: string, password: string): Promise<boolean> => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      if (response.ok) {
        const data = await response.json()
        // CRITICAL: Clear previous user's project data BEFORE storing new user's tokens
        // This prevents user isolation issues where user B sees user A's projects
        localStorage.removeItem('bharatbuild-project-storage')
        localStorage.removeItem('bharatbuild-chat-storage')
        // Set token in both localStorage and cookie (cookie needed for iframe preview)
        setAccessToken(data.access_token)
        if (data.refresh_token) {
          localStorage.setItem('refresh_token', data.refresh_token)
        }
        loadUser()
        return true
      }
      return false
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }, [loadUser])

  // Logout function - clears ALL user-specific localStorage data
  const logout = useCallback(() => {
    // Auth tokens (removes from both localStorage and cookie)
    removeAccessToken()
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
    // Theme preferences
    localStorage.removeItem('theme')
    localStorage.removeItem('admin-theme')
    // Project & chat stores (Zustand persisted state)
    localStorage.removeItem('bharatbuild-project-storage')
    localStorage.removeItem('bharatbuild-chat-storage')
    // Current project ID
    localStorage.removeItem('bharatbuild_current_project_id')
    // Other user data
    localStorage.removeItem('paper_prompt')
    localStorage.removeItem('offline_queue_bharatbuild')
    setIsAuthenticated(false)
    setUser(null)
    router.push('/')
  }, [router])

  // Check auth on mount
  useEffect(() => {
    loadUser()
  }, [loadUser])

  return {
    isAuthenticated,
    isLoading,
    user,
    login,
    logout,
    checkAuth,
    requireAuth
  }
}
