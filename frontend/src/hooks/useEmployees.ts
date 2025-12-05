'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export interface Employee {
  id: string
  email: string
  full_name: string | null
  username: string | null
  role: string
  organization: string | null
  is_active: boolean
  is_verified: boolean
  avatar_url: string | null
  oauth_provider: string | null
  created_at: string
  last_login: string | null
}

export interface EmployeesResponse {
  items: Employee[]
  total: number
  page: number
  page_size: number
  total_pages: number
  has_next: boolean
  has_previous: boolean
}

export interface EmployeeStats {
  total_users: number
  active_users: number
  verified_users: number
  users_by_role: Record<string, number>
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
}

export interface UseEmployeesParams {
  initialPage?: number
  initialPageSize?: number
  initialSortBy?: string
  initialSortOrder?: 'asc' | 'desc'
}

export function useEmployees({
  initialPage = 1,
  initialPageSize = 10,
  initialSortBy = 'created_at',
  initialSortOrder = 'desc'
}: UseEmployeesParams = {}) {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('')
  const [activeFilter, setActiveFilter] = useState<boolean | null>(null)
  const [sortBy, setSortBy] = useState(initialSortBy)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(initialSortOrder)
  const [stats, setStats] = useState<EmployeeStats | null>(null)

  const fetchEmployees = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      })

      if (search) {
        params.append('search', search)
      }
      if (roleFilter) {
        params.append('role', roleFilter)
      }
      if (activeFilter !== null) {
        params.append('is_active', activeFilter.toString())
      }

      const response: EmployeesResponse = await apiClient.get(`/users/?${params.toString()}`)

      setEmployees(response.items || [])
      setTotal(response.total || 0)
      setTotalPages(response.total_pages || 1)
    } catch (err: any) {
      console.error('Failed to fetch employees:', err)
      if (err.response?.status === 401) {
        setError('Please login to view employees')
      } else if (err.response?.status === 403) {
        setError('You do not have permission to view employees')
      } else {
        setError(err.message || 'Failed to fetch employees')
      }
      setEmployees([])
      setTotal(0)
      setTotalPages(0)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, roleFilter, activeFilter, sortBy, sortOrder])

  const fetchStats = useCallback(async () => {
    try {
      const response: EmployeeStats = await apiClient.get('/users/stats')
      setStats(response)
    } catch (err) {
      console.error('Failed to fetch employee stats:', err)
    }
  }, [])

  const updateEmployee = useCallback(async (userId: string, data: Partial<Employee>) => {
    try {
      await apiClient.put(`/users/${userId}`, data)
      await fetchEmployees()
      return true
    } catch (err: any) {
      console.error('Failed to update employee:', err)
      throw err
    }
  }, [fetchEmployees])

  const deleteEmployee = useCallback(async (userId: string) => {
    try {
      await apiClient.delete(`/users/${userId}`)
      await fetchEmployees()
      return true
    } catch (err: any) {
      console.error('Failed to delete employee:', err)
      throw err
    }
  }, [fetchEmployees])

  const refresh = useCallback(() => {
    fetchEmployees()
    fetchStats()
  }, [fetchEmployees, fetchStats])

  const goToPage = useCallback((newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage)
    }
  }, [totalPages])

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

  const handleSort = useCallback((field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
    setPage(1)
  }, [sortBy, sortOrder])

  // Fetch employees when filters change
  useEffect(() => {
    fetchEmployees()
  }, [fetchEmployees])

  // Fetch stats on mount
  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  return {
    employees,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    search,
    roleFilter,
    activeFilter,
    sortBy,
    sortOrder,
    stats,
    refresh,
    goToPage,
    changePageSize,
    handleSearch,
    handleRoleFilter,
    handleActiveFilter,
    handleSort,
    updateEmployee,
    deleteEmployee,
  }
}
