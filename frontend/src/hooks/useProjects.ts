'use client'

import { useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

export interface Project {
  id: string
  user_id: string
  title: string
  description: string | null
  mode: string
  status: string
  progress: number
  current_agent: string | null
  total_tokens: number
  total_cost: number
  created_at: string
  updated_at: string
  completed_at: string | null
  tech_stack?: string | null  // Technology stack (e.g., "Flutter, Dart, Firebase")
}

export interface ProjectsResponse {
  projects: Project[]
  total: number
  page: number
  page_size: number
  total_pages?: number
}

export function useProjects(initialPage: number = 1, initialPageSize: number = 12) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  const fetchProjects = useCallback(async (pageNum: number, size: number) => {
    setLoading(true)
    setError(null)

    try {
      const response: ProjectsResponse = await apiClient.getProjects({ page: pageNum, limit: size })
      setProjects(response.projects || [])
      setTotal(response.total || 0)

      // Calculate total pages
      const calculatedTotalPages = response.total_pages || Math.ceil((response.total || 0) / size)
      setTotalPages(calculatedTotalPages)
      setPage(response.page || pageNum)
    } catch (err: any) {
      console.error('Failed to fetch projects:', err)
      if (err.response?.status === 401) {
        setError('Please login to view your projects')
      } else {
        setError(err.message || 'Failed to fetch projects')
      }
      setProjects([])
      setTotal(0)
      setTotalPages(0)
    } finally {
      setLoading(false)
    }
  }, [])

  const deleteProject = useCallback(async (projectId: string) => {
    try {
      await apiClient.delete(`/projects/${projectId}`)
      // Refresh the list after deletion
      await fetchProjects(page, pageSize)
      return true
    } catch (err: any) {
      console.error('Failed to delete project:', err)
      throw err
    }
  }, [fetchProjects, page, pageSize])

  const refresh = useCallback(() => {
    fetchProjects(page, pageSize)
  }, [fetchProjects, page, pageSize])

  const goToPage = useCallback((newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage)
    }
  }, [totalPages])

  const changePageSize = useCallback((newSize: number) => {
    setPageSize(newSize)
    setPage(1) // Reset to first page when changing page size
  }, [])

  // Fetch projects when page or pageSize changes
  useEffect(() => {
    fetchProjects(page, pageSize)
  }, [page, pageSize, fetchProjects])

  return {
    projects,
    loading,
    error,
    page,
    pageSize,
    total,
    totalPages,
    refresh,
    goToPage,
    changePageSize,
    deleteProject,
  }
}
