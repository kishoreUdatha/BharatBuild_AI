'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import {
  BookOpen, Code, Brain, Cpu, Zap, Database, Network,
  GraduationCap, Users, Trophy, Clock, CheckCircle2, ChevronRight,
  Sparkles, Target, BarChart3, ArrowRight, Layers, Globe, Terminal,
  Beaker, CircuitBoard, Play, FileText, Award, TrendingUp,
  Activity, Timer, Home, Calendar, Upload, Lock, Unlock,
  ChevronDown, ChevronUp, AlertCircle, Star, Menu, X, Loader2, LogOut
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Lab Report Modal Component
function LabReportModal({
  isOpen,
  onClose,
  lab,
  onSubmit
}: {
  isOpen: boolean
  onClose: () => void
  lab: Lab | null
  onSubmit: (data: { title: string; description: string }) => Promise<void>
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (lab) {
      setTitle(`${lab.name} - Lab Report`)
      setDescription('')
      setError('')
    }
  }, [lab])

  if (!isOpen || !lab) return null

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) {
      setError('Please enter a title')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await onSubmit({ title, description })
      onClose()
    } catch (err: any) {
      setError(err.message || 'Failed to submit report')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-2xl">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-white"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="w-12 h-12 rounded-xl bg-cyan-500/20 flex items-center justify-center">
            <FileText className="h-6 w-6 text-cyan-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Submit Lab Report</h2>
            <p className="text-sm text-slate-400">{lab.name}</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="title" className="text-slate-300">Report Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Enter report title"
              className="mt-1 bg-slate-800 border-slate-700 text-white"
            />
          </div>

          <div>
            <Label htmlFor="description" className="text-slate-300">Description / Summary</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe what you learned and accomplished in this lab..."
              rows={4}
              className="mt-1 bg-slate-800 border-slate-700 text-white resize-none"
            />
          </div>

          <div className="p-4 bg-slate-800/50 rounded-xl border border-dashed border-slate-600">
            <div className="text-center">
              <Upload className="h-8 w-8 text-slate-500 mx-auto mb-2" />
              <p className="text-sm text-slate-400">
                File upload coming soon
              </p>
              <p className="text-xs text-slate-500 mt-1">
                PDF, DOC, DOCX (Max 10MB)
              </p>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              className="flex-1 border-slate-600 text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              className="flex-1 bg-cyan-500 hover:bg-cyan-600 text-white"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Submitting...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Submit Report
                </>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}

interface Lab {
  id: string
  name: string
  code: string
  description?: string
  branch: string
  semester: string
  technologies?: string[]
  total_topics: number
  total_mcqs: number
  total_coding_problems: number
  is_active: boolean
}

interface SemesterData {
  semester: string
  semesterLabel: string
  labs: Lab[]
  isCompleted: boolean
  isCurrentSemester: boolean
  isLocked: boolean
  reportStatus: 'not_submitted' | 'submitted' | 'approved' | 'rejected'
  progress: number
}

interface StudentProfile {
  name: string
  rollNumber: string
  branch: string
  currentSemester: number
  email: string
  profileImage?: string
}

// Sidebar navigation items
const sidebarItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Home, href: '/lab' },
  { id: 'my-labs', label: 'My Labs', icon: Beaker, href: '/lab#labs' },
  { id: 'progress', label: 'Progress', icon: TrendingUp, href: '/lab#progress' },
  { id: 'reports', label: 'Lab Reports', icon: FileText, href: '/lab#reports' },
  { id: 'analysis', label: 'Content Analysis', icon: Brain, href: '/analysis' },
  { id: 'leaderboard', label: 'Leaderboard', icon: Trophy, href: '/lab/leaderboard' },
  { id: 'schedule', label: 'Schedule', icon: Calendar, href: '/lab/schedule' },
]

const semesterLabels: Record<string, string> = {
  'sem_1': 'Semester 1',
  'sem_2': 'Semester 2',
  'sem_3': 'Semester 3',
  'sem_4': 'Semester 4',
  'sem_5': 'Semester 5',
  'sem_6': 'Semester 6',
  'sem_7': 'Semester 7',
  'sem_8': 'Semester 8',
}

const labIcons: Record<string, React.ReactNode> = {
  'programming': <Code className="h-5 w-5" />,
  'data': <Database className="h-5 w-5" />,
  'network': <Network className="h-5 w-5" />,
  'os': <Cpu className="h-5 w-5" />,
  'web': <Globe className="h-5 w-5" />,
  'algorithm': <Brain className="h-5 w-5" />,
  'electronics': <CircuitBoard className="h-5 w-5" />,
  'default': <Beaker className="h-5 w-5" />
}

function getLabIcon(labName: string): React.ReactNode {
  const name = labName.toLowerCase()
  if (name.includes('programming') || name.includes('c ') || name.includes('python') || name.includes('java')) return labIcons.programming
  if (name.includes('data') || name.includes('database') || name.includes('dbms')) return labIcons.data
  if (name.includes('network') || name.includes('cn')) return labIcons.network
  if (name.includes('operating') || name.includes('os')) return labIcons.os
  if (name.includes('web') || name.includes('html')) return labIcons.web
  if (name.includes('algorithm') || name.includes('dsa')) return labIcons.algorithm
  if (name.includes('electronic') || name.includes('digital')) return labIcons.electronics
  return labIcons.default
}

// Mock student profile - replace with API
const mockStudent: StudentProfile = {
  name: 'Student Name',
  rollNumber: '21CS001',
  branch: 'CSE',
  currentSemester: 5,
  email: 'student@college.edu'
}

export default function LabDashboardPage() {
  const router = useRouter()
  const [labs, setLabs] = useState<Lab[]>([])
  const [loading, setLoading] = useState(true)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [reportModalOpen, setReportModalOpen] = useState(false)
  const [selectedLabForReport, setSelectedLabForReport] = useState<Lab | null>(null)
  const [student, setStudent] = useState<StudentProfile>(mockStudent)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const [expandedSemesters, setExpandedSemesters] = useState<Record<string, boolean>>({})
  const [activeSection, setActiveSection] = useState('dashboard')

  useEffect(() => {
    fetchLabs()
    const token = localStorage.getItem('token') || localStorage.getItem('access_token')
    const name = localStorage.getItem('user_name') || localStorage.getItem('userName')
    setIsLoggedIn(!!token)
    if (name) {
      setStudent(prev => ({ ...prev, name }))
    }
  }, [])

  const handleLogout = () => {
    // Clear all auth data
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    localStorage.removeItem('userRole')
    localStorage.removeItem('userEmail')
    localStorage.removeItem('userName')
    localStorage.removeItem('user_name')
    // Redirect to login
    router.push('/login')
  }

  const fetchLabs = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/lab/public/labs`)
      if (response.ok) {
        const data = await response.json()
        setLabs(data)
        // Auto-expand current semester
        const currentSem = `sem_${mockStudent.currentSemester}`
        setExpandedSemesters({ [currentSem]: true })
      }
    } catch (error) {
      console.error('Error fetching labs:', error)
    } finally {
      setLoading(false)
    }
  }

  // Group labs by semester
  const getSemesterData = (): SemesterData[] => {
    const semesters = ['sem_1', 'sem_2', 'sem_3', 'sem_4', 'sem_5', 'sem_6', 'sem_7', 'sem_8']
    const currentSem = student.currentSemester

    return semesters.map((sem, index) => {
      const semNumber = index + 1
      const semLabs = labs.filter(lab => lab.semester === sem)

      return {
        semester: sem,
        semesterLabel: semesterLabels[sem],
        labs: semLabs,
        isCompleted: semNumber < currentSem,
        isCurrentSemester: semNumber === currentSem,
        isLocked: semNumber > currentSem,
        reportStatus: (semNumber < currentSem ? 'approved' : 'not_submitted') as SemesterData['reportStatus'],
        progress: semNumber < currentSem ? 100 : semNumber === currentSem ? 65 : 0
      }
    }).filter(sem => sem.labs.length > 0 || sem.isCurrentSemester || sem.isCompleted)
  }

  const toggleSemester = (semester: string) => {
    setExpandedSemesters(prev => ({
      ...prev,
      [semester]: !prev[semester]
    }))
  }

  const openReportModal = (lab: Lab) => {
    setSelectedLabForReport(lab)
    setReportModalOpen(true)
  }

  const handleSubmitReport = async (data: { title: string; description: string }) => {
    if (!selectedLabForReport) return

    const token = localStorage.getItem('token')
    if (!token) {
      throw new Error('Please login to submit a report')
    }

    const response = await fetch(`${API_URL}/lab/labs/${selectedLabForReport.id}/reports`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Failed to submit report')
    }

    // Refresh the page data
    alert('Lab report submitted successfully!')
  }

  const getReportStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return <Badge className="bg-green-500/20 text-green-400 border-green-500/30">Approved</Badge>
      case 'submitted':
        return <Badge className="bg-blue-500/20 text-blue-400 border-blue-500/30">Under Review</Badge>
      case 'rejected':
        return <Badge className="bg-red-500/20 text-red-400 border-red-500/30">Resubmit</Badge>
      default:
        return <Badge className="bg-slate-500/20 text-slate-400 border-slate-500/30">Not Submitted</Badge>
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-cyan-500/30 rounded-full animate-spin border-t-cyan-500"></div>
            <Sparkles className="absolute inset-0 m-auto h-8 w-8 text-cyan-400 animate-pulse" />
          </div>
          <p className="mt-4 text-cyan-400 font-medium">Loading Labs...</p>
        </div>
      </div>
    )
  }

  const semesterData = getSemesterData()
  const currentSemesterData = semesterData.find(s => s.isCurrentSemester)
  const completedSemesters = semesterData.filter(s => s.isCompleted).length
  const totalMCQs = labs.reduce((sum, lab) => sum + lab.total_mcqs, 0)
  const totalProblems = labs.reduce((sum, lab) => sum + lab.total_coding_problems, 0)

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Mobile Sidebar Overlay */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Left Sidebar - Fixed position */}
      <aside className={`
        fixed top-0 left-0 z-50 h-screen
        bg-slate-900 border-r border-slate-800
        transition-all duration-300 flex flex-col
        ${mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        ${sidebarOpen ? 'w-64' : 'w-20'}
      `}>
        {/* Student Profile Header */}
        <div className="p-4 border-b border-slate-800">
          <div className="flex items-center justify-between mb-3">
            {sidebarOpen && (
              <h1 className="font-bold text-cyan-400 text-sm uppercase tracking-wider">Lab Portal</h1>
            )}
            <button
              onClick={() => setMobileSidebarOpen(false)}
              className="lg:hidden p-2 text-slate-400 hover:text-white"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
          <div className={`flex items-center gap-3 ${!sidebarOpen && 'justify-center'}`}>
            <div className="w-11 h-11 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
              {student.name.charAt(0)}
            </div>
            {sidebarOpen && (
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-white truncate">{student.name}</p>
                <p className="text-xs text-slate-400">{student.rollNumber} • {student.branch}</p>
                <p className="text-xs text-cyan-400 font-medium">Semester {student.currentSemester}</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
          {sidebarItems.map(item => (
            <Link
              key={item.id}
              href={item.href}
              onClick={() => setActiveSection(item.id)}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all
                ${activeSection === item.id
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'}
                ${!sidebarOpen && 'lg:justify-center lg:px-2'}
              `}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {sidebarOpen && <span className="font-medium">{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* Logout Button */}
        <div className="p-4 border-t border-slate-800">
          <button
            onClick={handleLogout}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-red-400 hover:text-white hover:bg-red-500/20 transition-colors ${!sidebarOpen && 'lg:justify-center lg:px-2'}`}
          >
            <LogOut className="h-5 w-5 flex-shrink-0" />
            {sidebarOpen && <span className="font-medium">Logout</span>}
          </button>
        </div>

        {/* Sidebar Toggle (Desktop) */}
        <div className="hidden lg:block p-4 border-t border-slate-800">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            {sidebarOpen ? (
              <>
                <ChevronDown className="h-4 w-4 rotate-90" />
                <span className="text-sm">Collapse</span>
              </>
            ) : (
              <ChevronDown className="h-4 w-4 -rotate-90" />
            )}
          </button>
        </div>
      </aside>

      {/* Main Content - with left margin for sidebar */}
      <main className={`min-h-screen transition-all duration-300 ${sidebarOpen ? 'lg:ml-64' : 'lg:ml-20'}`}>
        {/* Top Header */}
        <header className="sticky top-0 z-30 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800 px-4 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setMobileSidebarOpen(true)}
                className="lg:hidden p-2 text-slate-400 hover:text-white"
              >
                <Menu className="h-6 w-6" />
              </button>
              <div>
                <h1 className="text-xl lg:text-2xl font-bold text-white">
                  Welcome back, {student.name.split(' ')[0]}!
                </h1>
                <p className="text-sm text-slate-400">
                  Continue your learning journey in Semester {student.currentSemester}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-orange-500/20 to-amber-500/20 border border-orange-500/30">
                <Zap className="h-5 w-5 text-orange-400" />
                <span className="text-orange-400 font-semibold">7 Day Streak</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline font-medium">Logout</span>
              </button>
            </div>
          </div>
        </header>

        <div className="p-4 lg:p-6 space-y-6">
          {/* Stats Overview */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                    <Target className="h-5 w-5 text-cyan-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-cyan-400">{currentSemesterData?.progress || 0}%</p>
                    <p className="text-xs text-slate-400">Current Semester</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-green-500/20 flex items-center justify-center">
                    <CheckCircle2 className="h-5 w-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-green-400">{completedSemesters}</p>
                    <p className="text-xs text-slate-400">Semesters Done</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center">
                    <Brain className="h-5 w-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-purple-400">120</p>
                    <p className="text-xs text-slate-400">MCQs Solved</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center">
                    <Code className="h-5 w-5 text-amber-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-amber-400">45</p>
                    <p className="text-xs text-slate-400">Programs Done</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* My Projects Section */}
          {student.currentSemester >= 5 && (
            <div id="projects" className="mb-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Layers className="h-5 w-5 text-purple-400" />
                My Projects
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Mini Project */}
                {student.currentSemester >= 5 && (
                  <Link href="/build">
                    <Card className="bg-gradient-to-br from-purple-500/10 to-pink-500/10 border-purple-500/30 hover:border-purple-400 transition-all cursor-pointer group">
                      <CardContent className="p-5">
                        <div className="flex items-center gap-4">
                          <div className="w-14 h-14 rounded-xl bg-purple-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                            <Beaker className="h-7 w-7 text-purple-400" />
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-white text-lg group-hover:text-purple-400 transition-colors">Mini Project</h3>
                            <p className="text-sm text-slate-400">Build your 5th/6th semester project with AI</p>
                          </div>
                          <ArrowRight className="h-5 w-5 text-purple-400 group-hover:translate-x-1 transition-transform" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                )}
                {/* Major Project */}
                {student.currentSemester >= 7 && (
                  <Link href="/build">
                    <Card className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border-orange-500/30 hover:border-orange-400 transition-all cursor-pointer group">
                      <CardContent className="p-5">
                        <div className="flex items-center gap-4">
                          <div className="w-14 h-14 rounded-xl bg-orange-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                            <Award className="h-7 w-7 text-orange-400" />
                          </div>
                          <div className="flex-1">
                            <h3 className="font-semibold text-white text-lg group-hover:text-orange-400 transition-colors">Major Project</h3>
                            <p className="text-sm text-slate-400">Build your final year project with AI</p>
                          </div>
                          <ArrowRight className="h-5 w-5 text-orange-400 group-hover:translate-x-1 transition-transform" />
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                )}
                {/* Project Reviews */}
                <Link href="/reviews">
                  <Card className="bg-gradient-to-br from-cyan-500/10 to-blue-500/10 border-cyan-500/30 hover:border-cyan-400 transition-all cursor-pointer group">
                    <CardContent className="p-5">
                      <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-xl bg-cyan-500/20 flex items-center justify-center group-hover:scale-110 transition-transform">
                          <FileText className="h-7 w-7 text-cyan-400" />
                        </div>
                        <div className="flex-1">
                          <h3 className="font-semibold text-white text-lg group-hover:text-cyan-400 transition-colors">Project Reviews</h3>
                          <p className="text-sm text-slate-400">Track your project review progress</p>
                        </div>
                        <ArrowRight className="h-5 w-5 text-cyan-400 group-hover:translate-x-1 transition-transform" />
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              </div>
            </div>
          )}

          {/* Current Semester Labs */}
          <div id="labs">
            <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
              <Layers className="h-5 w-5 text-cyan-400" />
              {currentSemesterData?.semesterLabel || 'Current Semester'} Labs
            </h2>

            {currentSemesterData && (
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800 overflow-hidden ring-2 ring-cyan-500/50">
                {/* Semester Header */}
                <div className="p-4 flex items-center justify-between bg-slate-800/30">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-cyan-500/20 flex items-center justify-center">
                      <GraduationCap className="h-6 w-6 text-cyan-400" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-white">{currentSemesterData.semesterLabel}</h3>
                        <Badge className="bg-cyan-500/20 text-cyan-400 border-cyan-500/30">
                          Current
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-400">
                        {currentSemesterData.labs.length} Labs • {currentSemesterData.progress}% Complete
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="hidden sm:flex items-center gap-2">
                      <FileText className="h-4 w-4 text-slate-400" />
                      {getReportStatusBadge(currentSemesterData.reportStatus)}
                    </div>
                    <div className="hidden sm:block w-32">
                      <Progress value={currentSemesterData.progress} className="h-2 bg-slate-700" />
                    </div>
                  </div>
                </div>

                {/* Labs Content */}
                <div className="border-t border-slate-800 p-4">
                  {/* Lab Report Section */}
                  {currentSemesterData.labs.length > 0 && (
                    <div className="mb-4 p-4 bg-slate-800/50 rounded-xl border border-slate-700">
                      <div className="flex items-center justify-between flex-wrap gap-3">
                        <div className="flex items-center gap-3">
                          <FileText className="h-5 w-5 text-cyan-400" />
                          <div>
                            <p className="font-medium text-white">Lab Reports</p>
                            <p className="text-xs text-slate-400">Submit reports for each lab</p>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {currentSemesterData.labs.map(lab => (
                            <Button
                              key={lab.id}
                              size="sm"
                              variant="outline"
                              onClick={() => openReportModal(lab)}
                              className="border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
                            >
                              <Upload className="h-3 w-3 mr-1" />
                              {lab.code}
                            </Button>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Labs Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {currentSemesterData.labs.map(lab => (
                      <Card
                        key={lab.id}
                        className="bg-slate-800/50 border-slate-700 hover:border-cyan-500/50 transition-all group"
                      >
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3 mb-3">
                            <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
                              {getLabIcon(lab.name)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <h4 className="font-medium text-white truncate group-hover:text-cyan-400 transition-colors">
                                {lab.name}
                              </h4>
                              <p className="text-xs text-slate-400">{lab.code}</p>
                            </div>
                          </div>

                          {/* Lab Stats */}
                          <div className="flex items-center gap-4 mb-3 text-xs text-slate-400">
                            <span className="flex items-center gap-1">
                              <BookOpen className="h-3 w-3" />
                              {lab.total_topics} Topics
                            </span>
                            <span className="flex items-center gap-1">
                              <Brain className="h-3 w-3" />
                              {lab.total_mcqs} MCQs
                            </span>
                            <span className="flex items-center gap-1">
                              <Code className="h-3 w-3" />
                              {lab.total_coding_problems} Problems
                            </span>
                          </div>

                          {/* Progress */}
                          <div className="mb-3">
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-slate-400">Progress</span>
                              <span className="text-cyan-400">0%</span>
                            </div>
                            <Progress value={0} className="h-1.5 bg-slate-700" />
                          </div>

                          {/* Action Button */}
                          <Link href={`/lab/${lab.id}`}>
                            <Button
                              size="sm"
                              className="w-full bg-slate-700 hover:bg-cyan-500 text-white transition-colors"
                            >
                              <Play className="h-4 w-4 mr-2" />
                              Start Lab
                            </Button>
                          </Link>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              </Card>
            )}
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Continue Learning Card */}
            {currentSemesterData && currentSemesterData.labs.length > 0 && (
              <Card className="bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-cyan-500/30">
                <CardContent className="p-5">
                  <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
                    <Play className="h-5 w-5 text-cyan-400" />
                    Continue Learning
                  </h3>
                  <p className="text-sm text-slate-300 mb-4">
                    Pick up where you left off in {currentSemesterData.labs[0].name}
                  </p>
                  <Link href={`/lab/${currentSemesterData.labs[0].id}`}>
                    <Button className="bg-cyan-500 hover:bg-cyan-600 text-white">
                      Continue
                      <ArrowRight className="h-4 w-4 ml-2" />
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}

            {/* Lab Report Reminder */}
            <Card className="bg-gradient-to-br from-amber-500/20 to-orange-500/20 border-amber-500/30">
              <CardContent className="p-5">
                <h3 className="font-semibold text-white mb-2 flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-amber-400" />
                  Lab Report Due
                </h3>
                <p className="text-sm text-slate-300 mb-4">
                  Submit your Semester {student.currentSemester} lab report before the deadline
                </p>
                {currentSemesterData && currentSemesterData.labs.length > 0 && (
                  <Button
                    variant="outline"
                    className="border-amber-500/50 text-amber-400 hover:bg-amber-500/10"
                    onClick={() => openReportModal(currentSemesterData.labs[0])}
                  >
                    <Upload className="h-4 w-4 mr-2" />
                    Submit Report
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Lab Report Submission Modal */}
      <LabReportModal
        isOpen={reportModalOpen}
        onClose={() => {
          setReportModalOpen(false)
          setSelectedLabForReport(null)
        }}
        lab={selectedLabForReport}
        onSubmit={handleSubmitReport}
      />
    </div>
  )
}
