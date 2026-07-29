'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  LayoutDashboard,
  Plus,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileText,
  Users,
  Calendar,
  Star,
  Eye,
  ChevronRight,
  GraduationCap,
  Target,
  Loader2,
  LogOut,
  ArrowLeft,
  BookOpen,
  Code2,
  Award
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Types
interface ReviewProject {
  id: string
  title: string
  description: string
  project_type: string
  technology_stack: string
  domain: string
  team_name: string
  team_size: number
  semester: number
  batch: string
  department: string
  guide_name: string
  github_url: string
  demo_url: string
  current_review: number
  total_score: number
  average_score: number
  is_approved: boolean
  is_completed: boolean
  created_at: string
  reviews: ProjectReview[]
  team_members: TeamMember[]
}

interface ProjectReview {
  id: string
  review_type: string
  review_number: number
  scheduled_date: string
  scheduled_time: string
  venue: string
  status: string
  total_score: number
  overall_feedback: string
  strengths: string
  weaknesses: string
  suggestions: string
}

interface TeamMember {
  id: string
  name: string
  roll_number: string
  email: string
  role: string
}

interface ReviewCriteria {
  innovation: { max_score: number; description: string }
  technical: { max_score: number; description: string }
  implementation: { max_score: number; description: string }
  documentation: { max_score: number; description: string }
  presentation: { max_score: number; description: string }
}

export default function StudentProjectReviews() {
  const router = useRouter()
  const [projects, setProjects] = useState<ReviewProject[]>([])
  const [selectedProject, setSelectedProject] = useState<ReviewProject | null>(null)
  const [loading, setLoading] = useState(true)
  const [showRegisterModal, setShowRegisterModal] = useState(false)
  const [criteria, setCriteria] = useState<ReviewCriteria | null>(null)

  // New project form state
  const [newProject, setNewProject] = useState({
    title: '',
    description: '',
    project_type: 'mini_project',
    technology_stack: '',
    domain: '',
    team_name: '',
    semester: 5,
    batch: '2021-2025',
    department: 'Computer Science',
    guide_name: '',
    github_url: '',
    team_members: [{ name: '', roll_number: '', email: '', role: 'Team Lead' }]
  })

  useEffect(() => {
    fetchProjects()
    fetchCriteria()
  }, [])

  const fetchProjects = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/project-reviews/projects`)
      if (res.ok) {
        const data = await res.json()
        // Backend returns array directly, not { projects: [] }
        setProjects(Array.isArray(data) ? data : (data.projects || []))
      }
    } catch (error) {
      console.error('Error fetching projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchCriteria = async () => {
    try {
      const res = await fetch(`${API_BASE}/project-reviews/criteria`)
      if (res.ok) {
        const data = await res.json()
        setCriteria(data.scoring_criteria)
      }
    } catch (error) {
      console.error('Error fetching criteria:', error)
    }
  }

  const fetchProjectDetails = async (projectId: string) => {
    try {
      const res = await fetch(`${API_BASE}/project-reviews/projects/${projectId}`)
      if (res.ok) {
        const data = await res.json()
        setSelectedProject(data)
      }
    } catch (error) {
      console.error('Error fetching project details:', error)
    }
  }

  const handleRegisterProject = async () => {
    try {
      const res = await fetch(`${API_BASE}/project-reviews/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newProject)
      })
      if (res.ok) {
        setShowRegisterModal(false)
        fetchProjects()
        setNewProject({
          title: '',
          description: '',
          project_type: 'mini_project',
          technology_stack: '',
          domain: '',
          team_name: '',
          semester: 5,
          batch: '2021-2025',
          department: 'Computer Science',
          guide_name: '',
          github_url: '',
          team_members: [{ name: '', roll_number: '', email: '', role: 'Team Lead' }]
        })
      }
    } catch (error) {
      console.error('Error registering project:', error)
    }
  }

  const addTeamMember = () => {
    setNewProject({
      ...newProject,
      team_members: [...newProject.team_members, { name: '', roll_number: '', email: '', role: 'Member' }]
    })
  }

  const updateTeamMember = (index: number, field: string, value: string) => {
    const members = [...newProject.team_members]
    members[index] = { ...members[index], [field]: value }
    setNewProject({ ...newProject, team_members: members })
  }

  const getReviewStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'scheduled': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'in_progress': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'cancelled': return 'bg-red-500/20 text-red-400 border-red-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getReviewTypeName = (type: string) => {
    switch (type) {
      case 'review_1': return 'Review 1 - Problem Definition'
      case 'review_2': return 'Review 2 - System Design'
      case 'review_3': return 'Review 3 - Implementation'
      case 'final_review': return 'Final Review'
      default: return type
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    router.push('/login')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Header */}
      <header className="bg-gray-900/80 backdrop-blur-xl border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/lab" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors">
                <ArrowLeft className="w-5 h-5" />
                <span>Back to Dashboard</span>
              </Link>
            </div>
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Project Reviews
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="text-gray-400 hover:text-white"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card className="bg-gray-900/50 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <FileText className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{projects.length}</p>
                  <p className="text-sm text-gray-400">My Projects</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <CheckCircle2 className="w-5 h-5 text-green-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {projects.filter(p => p.is_completed).length}
                  </p>
                  <p className="text-sm text-gray-400">Completed</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Clock className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {projects.filter(p => !p.is_completed).length}
                  </p>
                  <p className="text-sm text-gray-400">In Progress</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gray-900/50 border-gray-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/20 rounded-lg">
                  <Star className="w-5 h-5 text-yellow-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">
                    {projects.length > 0 ? (projects.reduce((sum, p) => sum + p.average_score, 0) / projects.length).toFixed(1) : '0'}
                  </p>
                  <p className="text-sm text-gray-400">Avg Score</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Action Bar */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-white">My Projects</h2>
          <Button
            onClick={() => setShowRegisterModal(true)}
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
          >
            <Plus className="w-4 h-4 mr-2" />
            Register New Project
          </Button>
        </div>

        {/* Projects Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-purple-500" />
          </div>
        ) : projects.length === 0 ? (
          <Card className="bg-gray-900/50 border-gray-800">
            <CardContent className="py-20 text-center">
              <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No Projects Yet</h3>
              <p className="text-gray-400 mb-6">Register your first project to start the review process</p>
              <Button
                onClick={() => setShowRegisterModal(true)}
                className="bg-gradient-to-r from-purple-600 to-pink-600"
              >
                <Plus className="w-4 h-4 mr-2" />
                Register Project
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {projects.map((project) => (
              <Card
                key={project.id}
                className="bg-gray-900/50 border-gray-800 hover:border-purple-500/50 transition-all cursor-pointer"
                onClick={() => fetchProjectDetails(project.id)}
              >
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-white">{project.title}</h3>
                        <Badge className={project.project_type === 'major_project' ? 'bg-orange-500/20 text-orange-400' : 'bg-blue-500/20 text-blue-400'}>
                          {project.project_type === 'major_project' ? 'Major Project' : 'Mini Project'}
                        </Badge>
                        {project.is_completed && (
                          <Badge className="bg-green-500/20 text-green-400">Completed</Badge>
                        )}
                        {project.is_approved && (
                          <Badge className="bg-purple-500/20 text-purple-400">Approved</Badge>
                        )}
                      </div>
                      <p className="text-gray-400 text-sm mb-4 line-clamp-2">{project.description}</p>

                      <div className="flex flex-wrap gap-4 text-sm">
                        <div className="flex items-center gap-1 text-gray-400">
                          <Code2 className="w-4 h-4" />
                          <span>{project.technology_stack || 'Not specified'}</span>
                        </div>
                        <div className="flex items-center gap-1 text-gray-400">
                          <Users className="w-4 h-4" />
                          <span>{project.team_size} members</span>
                        </div>
                        <div className="flex items-center gap-1 text-gray-400">
                          <GraduationCap className="w-4 h-4" />
                          <span>Semester {project.semester}</span>
                        </div>
                        <div className="flex items-center gap-1 text-gray-400">
                          <BookOpen className="w-4 h-4" />
                          <span>{project.guide_name || 'No guide assigned'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="text-right ml-6">
                      <div className="mb-2">
                        <p className="text-sm text-gray-400">Review Progress</p>
                        <p className="text-2xl font-bold text-white">{project.current_review}/4</p>
                      </div>
                      <Progress value={(project.current_review / 4) * 100} className="w-24 h-2" />
                      {project.average_score > 0 && (
                        <div className="mt-3">
                          <p className="text-sm text-gray-400">Avg Score</p>
                          <p className="text-xl font-bold text-yellow-400">{project.average_score.toFixed(1)}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Project Details Modal */}
        {selectedProject && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-800 flex items-center justify-between sticky top-0 bg-gray-900">
                <h2 className="text-xl font-bold text-white">{selectedProject.title}</h2>
                <Button variant="ghost" onClick={() => setSelectedProject(null)}>
                  Close
                </Button>
              </div>

              <div className="p-6 space-y-6">
                {/* Project Info */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-400">Project Type</p>
                    <p className="text-white">{selectedProject.project_type === 'major_project' ? 'Major Project' : 'Mini Project'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Domain</p>
                    <p className="text-white">{selectedProject.domain || 'Not specified'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Technology Stack</p>
                    <p className="text-white">{selectedProject.technology_stack || 'Not specified'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Guide</p>
                    <p className="text-white">{selectedProject.guide_name || 'Not assigned'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Semester</p>
                    <p className="text-white">{selectedProject.semester}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-400">Batch</p>
                    <p className="text-white">{selectedProject.batch}</p>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <p className="text-sm text-gray-400 mb-2">Description</p>
                  <p className="text-gray-300">{selectedProject.description || 'No description provided'}</p>
                </div>

                {/* Team Members */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">Team Members</h3>
                  <div className="grid gap-2">
                    {selectedProject.team_members?.map((member, index) => (
                      <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 rounded-lg">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-purple-500/20 rounded-full flex items-center justify-center">
                            <span className="text-purple-400 font-medium">{member.name?.[0] || '?'}</span>
                          </div>
                          <div>
                            <p className="text-white font-medium">{member.name}</p>
                            <p className="text-sm text-gray-400">{member.roll_number}</p>
                          </div>
                        </div>
                        <Badge variant="outline">{member.role}</Badge>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Reviews */}
                <div>
                  <h3 className="text-lg font-semibold text-white mb-3">Reviews</h3>
                  {selectedProject.reviews?.length === 0 ? (
                    <p className="text-gray-400">No reviews scheduled yet</p>
                  ) : (
                    <div className="space-y-3">
                      {selectedProject.reviews?.map((review, index) => (
                        <Card key={index} className="bg-gray-800/50 border-gray-700">
                          <CardContent className="p-4">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-3">
                                <span className="text-white font-medium">{getReviewTypeName(review.review_type)}</span>
                                <Badge className={getReviewStatusColor(review.status)}>
                                  {review.status}
                                </Badge>
                              </div>
                              {review.total_score > 0 && (
                                <span className="text-xl font-bold text-yellow-400">{review.total_score}/100</span>
                              )}
                            </div>
                            <div className="flex items-center gap-4 text-sm text-gray-400">
                              <div className="flex items-center gap-1">
                                <Calendar className="w-4 h-4" />
                                <span>{new Date(review.scheduled_date).toLocaleDateString()}</span>
                              </div>
                              {review.scheduled_time && (
                                <span>{review.scheduled_time}</span>
                              )}
                              {review.venue && (
                                <span>@ {review.venue}</span>
                              )}
                            </div>
                            {review.overall_feedback && (
                              <div className="mt-3 p-3 bg-gray-900/50 rounded-lg">
                                <p className="text-sm text-gray-400 mb-1">Feedback</p>
                                <p className="text-gray-300">{review.overall_feedback}</p>
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>

                {/* Scoring Criteria Reference */}
                {criteria && (
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Scoring Criteria</h3>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                      {Object.entries(criteria).map(([key, value]) => (
                        <div key={key} className="p-3 bg-gray-800/50 rounded-lg text-center">
                          <p className="text-2xl font-bold text-purple-400">{value.max_score}</p>
                          <p className="text-xs text-gray-400 capitalize">{key}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Register Project Modal */}
        {showRegisterModal && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 border border-gray-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6 border-b border-gray-800 flex items-center justify-between sticky top-0 bg-gray-900">
                <h2 className="text-xl font-bold text-white">Register New Project</h2>
                <Button variant="ghost" onClick={() => setShowRegisterModal(false)}>
                  Close
                </Button>
              </div>

              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-1">Project Title *</label>
                  <input
                    type="text"
                    value={newProject.title}
                    onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="e.g., Hospital Management System"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">Description</label>
                  <textarea
                    value={newProject.description}
                    onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                    rows={3}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="Brief description of your project..."
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Project Type</label>
                    <select
                      value={newProject.project_type}
                      onChange={(e) => setNewProject({ ...newProject, project_type: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    >
                      <option value="mini_project">Mini Project</option>
                      <option value="major_project">Major Project</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Semester</label>
                    <select
                      value={newProject.semester}
                      onChange={(e) => setNewProject({ ...newProject, semester: parseInt(e.target.value) })}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    >
                      <option value={5}>5th Semester</option>
                      <option value={6}>6th Semester</option>
                      <option value={7}>7th Semester</option>
                      <option value={8}>8th Semester</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Technology Stack</label>
                    <input
                      type="text"
                      value={newProject.technology_stack}
                      onChange={(e) => setNewProject({ ...newProject, technology_stack: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      placeholder="e.g., React, Node.js, MongoDB"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Domain</label>
                    <input
                      type="text"
                      value={newProject.domain}
                      onChange={(e) => setNewProject({ ...newProject, domain: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      placeholder="e.g., Healthcare, Education"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Team Name</label>
                    <input
                      type="text"
                      value={newProject.team_name}
                      onChange={(e) => setNewProject({ ...newProject, team_name: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      placeholder="e.g., Tech Innovators"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Guide Name</label>
                    <input
                      type="text"
                      value={newProject.guide_name}
                      onChange={(e) => setNewProject({ ...newProject, guide_name: e.target.value })}
                      className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      placeholder="e.g., Dr. Smith"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-1">GitHub URL (Optional)</label>
                  <input
                    type="url"
                    value={newProject.github_url}
                    onChange={(e) => setNewProject({ ...newProject, github_url: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    placeholder="https://github.com/..."
                  />
                </div>

                {/* Team Members */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm text-gray-400">Team Members</label>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={addTeamMember}
                      className="text-purple-400"
                    >
                      <Plus className="w-4 h-4 mr-1" /> Add Member
                    </Button>
                  </div>
                  <div className="space-y-3">
                    {newProject.team_members.map((member, index) => (
                      <div key={index} className="grid grid-cols-4 gap-2 p-3 bg-gray-800/50 rounded-lg">
                        <input
                          type="text"
                          value={member.name}
                          onChange={(e) => updateTeamMember(index, 'name', e.target.value)}
                          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-purple-500"
                          placeholder="Name"
                        />
                        <input
                          type="text"
                          value={member.roll_number}
                          onChange={(e) => updateTeamMember(index, 'roll_number', e.target.value)}
                          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-purple-500"
                          placeholder="Roll No."
                        />
                        <input
                          type="email"
                          value={member.email}
                          onChange={(e) => updateTeamMember(index, 'email', e.target.value)}
                          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-purple-500"
                          placeholder="Email"
                        />
                        <select
                          value={member.role}
                          onChange={(e) => updateTeamMember(index, 'role', e.target.value)}
                          className="px-3 py-1.5 bg-gray-800 border border-gray-700 rounded text-white text-sm focus:outline-none focus:border-purple-500"
                        >
                          <option value="Team Lead">Team Lead</option>
                          <option value="Developer">Developer</option>
                          <option value="Designer">Designer</option>
                          <option value="Tester">Tester</option>
                          <option value="Member">Member</option>
                        </select>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end gap-3 pt-4">
                  <Button variant="ghost" onClick={() => setShowRegisterModal(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={handleRegisterProject}
                    className="bg-gradient-to-r from-purple-600 to-pink-600"
                    disabled={!newProject.title}
                  >
                    Register Project
                  </Button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
