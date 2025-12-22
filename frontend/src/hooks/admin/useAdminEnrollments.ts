'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export interface WorkshopEnrollment {
  id: string
  full_name: string
  email: string
  phone: string
  college_name: string
  department: string
  year_of_study: string
  roll_number: string | null
  workshop_name: string
  is_confirmed: boolean
  created_at: string
}

export interface UseAdminEnrollmentsParams {
  initialPageSize?: number
}

export function useAdminEnrollments({
  initialPageSize = 10,
}: UseAdminEnrollmentsParams = {}) {
  const [enrollments, setEnrollments] = useState<WorkshopEnrollment[]>([])
  const [filteredEnrollments, setFilteredEnrollments] = useState<WorkshopEnrollment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const [search, setSearch] = useState('')
  const [workshopFilter, setWorkshopFilter] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  const fetchEnrollments = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams()
      if (workshopFilter) params.append('workshop_name', workshopFilter)

      const url = `/workshop/enrollments${params.toString() ? `?${params.toString()}` : ''}`
      const data = await apiClient.get<WorkshopEnrollment[]>(url)

      setEnrollments(data || [])
      setTotal(data?.length || 0)
    } catch (err: any) {
      console.error('Failed to fetch enrollments:', err)
      setError(err.message || 'Failed to fetch enrollments')
      setEnrollments([])
    } finally {
      setLoading(false)
    }
  }, [workshopFilter])

  // Apply client-side filtering, sorting, and pagination
  useEffect(() => {
    let result = [...enrollments]

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase()
      result = result.filter(
        (e) =>
          e.full_name.toLowerCase().includes(searchLower) ||
          e.email.toLowerCase().includes(searchLower) ||
          e.college_name.toLowerCase().includes(searchLower) ||
          e.department.toLowerCase().includes(searchLower) ||
          e.phone.includes(search)
      )
    }

    // Sorting
    result.sort((a, b) => {
      let aVal: any = a[sortBy as keyof WorkshopEnrollment]
      let bVal: any = b[sortBy as keyof WorkshopEnrollment]

      if (sortBy === 'created_at') {
        aVal = new Date(aVal).getTime()
        bVal = new Date(bVal).getTime()
      } else if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase()
        bVal = bVal?.toLowerCase() || ''
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : -1
      }
      return aVal < bVal ? 1 : -1
    })

    setTotal(result.length)
    setTotalPages(Math.ceil(result.length / pageSize))

    // Pagination
    const start = (page - 1) * pageSize
    const end = start + pageSize
    setFilteredEnrollments(result.slice(start, end))
  }, [enrollments, search, sortBy, sortOrder, page, pageSize])

  useEffect(() => {
    fetchEnrollments()
  }, [fetchEnrollments])

  const refresh = useCallback(() => {
    fetchEnrollments()
  }, [fetchEnrollments])

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

  const handleWorkshopFilter = useCallback((workshop: string) => {
    setWorkshopFilter(workshop)
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

  const exportEnrollments = useCallback(async () => {
    try {
      // Get all enrollments for export
      const dataToExport = search ? filteredEnrollments : enrollments

      // Create CSV content
      const headers = [
        'Full Name',
        'Email',
        'Phone',
        'College',
        'Department',
        'Year of Study',
        'Roll Number',
        'Workshop',
        'Confirmed',
        'Registered At'
      ]

      const rows = dataToExport.map((e) => [
        e.full_name,
        e.email,
        e.phone,
        e.college_name,
        e.department,
        e.year_of_study,
        e.roll_number || '',
        e.workshop_name,
        e.is_confirmed ? 'Yes' : 'No',
        new Date(e.created_at).toLocaleString()
      ])

      const csvContent = [
        headers.join(','),
        ...rows.map((row) =>
          row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
        )
      ].join('\n')

      // Download the file
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `workshop_enrollments_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      console.error('Failed to export enrollments:', err)
      throw err
    }
  }, [enrollments, filteredEnrollments, search])

  // Get unique workshop names for filter dropdown
  const workshopNames = useCallback(() => {
    const names = new Set(enrollments.map((e) => e.workshop_name))
    return Array.from(names)
  }, [enrollments])

  return {
    enrollments: filteredEnrollments,
    allEnrollments: enrollments,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    search,
    workshopFilter,
    sortBy,
    sortOrder,
    refresh,
    goToPage,
    changePageSize,
    handleSearch,
    handleWorkshopFilter,
    handleSort,
    exportEnrollments,
    workshopNames,
  }
}
