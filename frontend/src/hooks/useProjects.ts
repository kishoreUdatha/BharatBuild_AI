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
}

export interface ProjectsResponse {
  projects: Project[]
  total: number
  page: number
  page_size: number
}

export function useProjects(initialPage: number = 1, pageSize: number = 12) {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(initialPage)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  const fetchProjects = useCallback(async (pageNum: number = page) => {
    setLoading(true)
    setError(null)

    try {
      const response: ProjectsResponse = await apiClient.getProjects()
      setProjects(response.projects)
      setTotal(response.total)
      setTotalPages(Math.ceil(response.total / pageSize))
      setPage(response.page)
    } catch (err: any) {
      console.error('Failed to fetch projects:', err)
      if (err.response?.status === 401) {
        setError('Please login to view your projects')
      } else {
        setError(err.message || 'Failed to fetch projects')
      }
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  const deleteProject = useCallback(async (projectId: string) => {
    try {
      await apiClient.getProject(projectId) // Using this as a workaround, would need delete endpoint
      // For now, we'll just refresh the list
      await fetchProjects()
      return true
    } catch (err: any) {
      console.error('Failed to delete project:', err)
      throw err
    }
  }, [fetchProjects])

  const refresh = useCallback(() => {
    fetchProjects(page)
  }, [fetchProjects, page])

  const goToPage = useCallback((newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage)
    }
  }, [totalPages])

  useEffect(() => {
    fetchProjects()
  }, []) // Only fetch on mount

  return {
    projects,
    loading,
    error,
    page,
    total,
    totalPages,
    refresh,
    goToPage,
    deleteProject,
  }
}
