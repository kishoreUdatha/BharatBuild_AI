'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  GraduationCap,
  FolderKanban,
  CheckCircle2,
  FileText,
  Coins,
  Loader2,
  RefreshCw
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { StatsCard } from '@/components/dashboard/StatsCard'
import { DashboardProjectCard } from '@/components/dashboard/DashboardProjectCard'
import { DocumentsPanel } from '@/components/dashboard/DocumentsPanel'
import { QuickActionsBar } from '@/components/dashboard/QuickActionsBar'

interface Project {
  id: string
  title: string
  description?: string
  status: 'draft' | 'in_progress' | 'processing' | 'completed' | 'failed'
  progress?: number
  created_at: string
  documents_count?: number
}

interface DashboardStats {
  total_projects: number
  completed_projects: number
  total_documents: number
  tokens_used: number
}

export default function StudentDashboard() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [stats, setStats] = useState<DashboardStats>({
    total_projects: 0,
    completed_projects: 0,
    total_documents: 0,
    tokens_used: 0
  })
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [tokenBalance, setTokenBalance] = useState<number>(0)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    setIsLoading(true)
    try {
      // Fetch projects
      const projectsResponse = await apiClient.get<{
        items: Project[]
        total: number
      }>('/projects/list?limit=6&sort_by=created_at&sort_order=desc')

      const projectsList = projectsResponse.items || []
      setProjects(projectsList)

      // Calculate stats from projects
      const completedCount = projectsList.filter(p => p.status === 'completed').length
      const docsCount = projectsList.reduce((sum, p) => sum + (p.documents_count || 0), 0)

      setStats({
        total_projects: projectsResponse.total || projectsList.length,
        completed_projects: completedCount,
        total_documents: docsCount,
        tokens_used: 0
      })

      // Fetch token balance
      try {
        const userResponse = await apiClient.get<{ token_balance: number }>('/users/me')
        setTokenBalance(userResponse.token_balance || 0)
      } catch {
        // Ignore token fetch errors
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSelectForDocuments = (project: Project) => {
    setSelectedProject(selectedProject?.id === project.id ? null : project)
  }

  const handleCreateProject = () => {
    router.push('/bolt')
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <p className="text-gray-400">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Header */}
      <header className="border-b border-[#222] bg-[#0a0a0f]/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500">
                <GraduationCap className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">Student Dashboard</h1>
                <p className="text-sm text-gray-400">Manage your projects and documents</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={fetchDashboardData}
                className="p-2 rounded-lg hover:bg-[#222] text-gray-400 hover:text-white transition-colors"
                title="Refresh"
              >
                <RefreshCw className="h-5 w-5" />
              </button>
              <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#1a1a1a] border border-[#333]">
                <Coins className="h-4 w-4 text-yellow-500" />
                <span className="font-semibold text-white">{tokenBalance.toLocaleString()}</span>
                <span className="text-gray-400 text-sm">tokens</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Stats Cards */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatsCard
            title="Total Projects"
            value={stats.total_projects}
            icon={FolderKanban}
            color="blue"
          />
          <StatsCard
            title="Completed"
            value={stats.completed_projects}
            icon={CheckCircle2}
            color="green"
          />
          <StatsCard
            title="Documents"
            value={stats.total_documents}
            icon={FileText}
            color="purple"
          />
          <StatsCard
            title="Tokens Used"
            value={stats.tokens_used}
            icon={Coins}
            color="orange"
          />
        </section>

        {/* Quick Actions */}
        <section>
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <QuickActionsBar onCreateProject={handleCreateProject} />
        </section>

        {/* Projects and Documents Grid */}
        <section className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Projects Section */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Recent Projects</h2>
              <button
                onClick={() => router.push('/projects')}
                className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                View all
              </button>
            </div>

            {projects.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 bg-[#1a1a1a] rounded-xl border border-[#333]">
                <FolderKanban className="h-12 w-12 text-gray-600 mb-4" />
                <p className="text-gray-400 mb-4">No projects yet</p>
                <button
                  onClick={handleCreateProject}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium transition-colors"
                >
                  Create your first project
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {projects.map((project) => (
                  <DashboardProjectCard
                    key={project.id}
                    project={project}
                    onSelectForDocuments={handleSelectForDocuments}
                    isSelected={selectedProject?.id === project.id}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Documents Panel */}
          <div className="lg:col-span-2">
            <h2 className="text-lg font-semibold text-white mb-4">Project Documents</h2>
            <DocumentsPanel
              selectedProject={selectedProject}
              onClose={() => setSelectedProject(null)}
            />
          </div>
        </section>
      </main>
    </div>
  )
}
