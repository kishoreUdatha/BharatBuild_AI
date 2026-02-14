'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, Loader2 } from 'lucide-react'
import { TeamProjectDashboard } from '@/components/team'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api-client'

interface ProjectData {
  id: string
  title: string
  description: string
  status: string
}

export default function TeamPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.id as string

  const { isAuthenticated, isLoading: authLoading } = useAuth()
  const [project, setProject] = useState<ProjectData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  // Fetch project data
  useEffect(() => {
    const fetchProject = async () => {
      if (!projectId) return

      try {
        const data = await apiClient.getProject(projectId)
        setProject({
          id: data.id,
          title: data.title || data.name || 'Untitled Project',
          description: data.description || '',
          status: data.status
        })
      } catch (err: any) {
        console.error('Failed to fetch project:', err)
        setError(err.message || 'Failed to load project')
      } finally {
        setIsLoading(false)
      }
    }

    if (isAuthenticated) {
      fetchProject()
    }
  }, [projectId, isAuthenticated])

  // Loading state
  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--bolt-accent))]" />
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="text-[hsl(var(--bolt-accent))] hover:underline"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  // Not found
  if (!project) {
    return (
      <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[hsl(var(--bolt-text-secondary))] mb-4">Project not found</p>
          <button
            onClick={() => router.push('/dashboard')}
            className="text-[hsl(var(--bolt-accent))] hover:underline"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex flex-col">
      {/* Navigation Header */}
      <div className="flex-shrink-0 h-14 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))] flex items-center px-4">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Project</span>
        </button>
      </div>

      {/* Team Dashboard */}
      <div className="flex-1 overflow-hidden">
        <TeamProjectDashboard
          projectId={projectId}
          projectName={project.title}
          projectDescription={project.description}
        />
      </div>
    </div>
  )
}
