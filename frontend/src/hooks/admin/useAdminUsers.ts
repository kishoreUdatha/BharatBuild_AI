'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export interface AdminUser {
  id: string
  email: string
  full_name: string | null
  username: string | null
  role: string
  organization: string | null
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  oauth_provider: string | null
  avatar_url: string | null
  created_at: string
  last_login: string | null
  projects_count: number
  tokens_used: number
  subscription_plan: string | null
}

export interface AdminUsersResponse {
  items: AdminUser[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface UseAdminUsersParams {
  initialPage?: number
  initialPageSize?: number
  initialSortBy?: string
  initialSortOrder?: 'asc' | 'desc'
}

export function useAdminUsers({
  initialPage = 1,
  initialPageSize = 10,
  initialSortBy = 'created_at',
  initialSortOrder = 'desc',
}: UseAdminUsersParams = {}) {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState<boolean | null>(null)
  const [verifiedFilter, setVerifiedFilter] = useState<boolean | null>(null)
  const [sortBy, setSortBy] = useState(initialSortBy)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(initialSortOrder)

  const fetchUsers = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      if (search) params.append('search', search)
      if (roleFilter) params.append('role', roleFilter)
      if (activeFilter !== null) params.append('is_active', activeFilter.toString())
      if (verifiedFilter !== null) params.append('is_verified', verifiedFilter.toString())

      const data = await apiClient.get<AdminUsersResponse>(`/admin/users?${params.toString()}`)

      setUsers(data.items || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)
    } catch (err: any) {
      console.error('Failed to fetch users:', err)
      setError(err.message || 'Failed to fetch users')
      setUsers([])
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, roleFilter, activeFilter, verifiedFilter, sortBy, sortOrder])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const refresh = useCallback(() => {
    fetchUsers()
  }, [fetchUsers])

  const goToPage = useCallback((newPage: number) => {
    setPage(newPage)
  }, [])

  const changePageSize = useCallback((newSize: number) => {
    setPageSize(newSize)
    setPage(1)
  }, [])

  const handleSearch = useCallback((query: string) => {
    setSearch(query)
    setPage(1)
  }, [])

  const handleRoleFilter = useCallback((role: string) => {
    setRoleFilter(role)
    setPage(1)
  }, [])

  const handleActiveFilter = useCallback((active: boolean | null) => {
    setActiveFilter(active)
    setPage(1)
  }, [])

  const handleVerifiedFilter = useCallback((verified: boolean | null) => {
    setVerifiedFilter(verified)
    setPage(1)
  }, [])

  const handleSort = useCallback((field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
  }, [sortBy, sortOrder])

  const updateUser = useCallback(async (userId: string, data: Partial<AdminUser>) => {
    try {
      await apiClient.patch(`/admin/users/${userId}`, data)
      await fetchUsers()
      return true
    } catch (err: any) {
      console.error('Failed to update user:', err)
      throw err
    }
  }, [fetchUsers])

  const suspendUser = useCallback(async (userId: string) => {
    try {
      await apiClient.post(`/admin/users/${userId}/suspend`)
      await fetchUsers()
      return true
    } catch (err: any) {
      console.error('Failed to suspend user:', err)
      throw err
    }
  }, [fetchUsers])

  const activateUser = useCallback(async (userId: string) => {
    try {
      await apiClient.post(`/admin/users/${userId}/activate`)
      await fetchUsers()
      return true
    } catch (err: any) {
      console.error('Failed to activate user:', err)
      throw err
    }
  }, [fetchUsers])

  const deleteUser = useCallback(async (userId: string) => {
    try {
      await apiClient.delete(`/admin/users/${userId}`)
      await fetchUsers()
      return true
    } catch (err: any) {
      console.error('Failed to delete user:', err)
      throw err
    }
  }, [fetchUsers])

  const bulkAction = useCallback(async (
    userIds: string[],
    action: 'suspend' | 'activate' | 'delete' | 'change_role',
    role?: string
  ) => {
    try {
      await apiClient.post('/admin/users/bulk', {
        user_ids: userIds,
        action,
        role,
      })
      await fetchUsers()
      return true
    } catch (err: any) {
      console.error('Failed to perform bulk action:', err)
      throw err
    }
  }, [fetchUsers])

  const exportUsers = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/admin/users/export/csv', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      })
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'users_export.csv'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      console.error('Failed to export users:', err)
      throw err
    }
  }, [])

  return {
    users,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    search,
    roleFilter,
    activeFilter,
    verifiedFilter,
    sortBy,
    sortOrder,
    refresh,
    goToPage,
    changePageSize,
    handleSearch,
    handleRoleFilter,
    handleActiveFilter,
    handleVerifiedFilter,
    handleSort,
    updateUser,
    suspendUser,
    activateUser,
    deleteUser,
    bulkAction,
    exportUsers,
  }
}
