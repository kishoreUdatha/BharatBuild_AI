'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Award,
  Building2,
  Users,
  FileText,
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronRight,
  GraduationCap,
  BookOpen,
  Shield,
  Leaf,
  TrendingUp,
  Calendar,
  Settings,
  Plus,
  Download,
  Bell,
  User,
  LogOut,
  BarChart3,
  Target,
  Loader2
} from 'lucide-react'

interface CollegeProfile {
  id: string
  name: string
  short_name: string
  city: string
  state: string
  principal_name: string
  subscription_plan: string
  total_departments: number
  total_programs: number
  total_faculty: number
  total_students: number
}

interface CriterionProgress {
  number: number
  name: string
  marks: number
  progress: number
  status: 'not_started' | 'in_progress' | 'submitted' | 'approved'
  last_updated?: string
}

interface TeamMember {
  id: string
  name: string
  email: string
  role: string
  criterion?: number
  status: 'active' | 'pending'
}

const CRITERIA = [
  { number: 1, name: 'Curricular Aspects', marks: 150, icon: BookOpen },
  { number: 2, name: 'Teaching-Learning & Evaluation', marks: 200, icon: GraduationCap },
  { number: 3, name: 'Research, Innovations & Extension', marks: 150, icon: FileText },
  { number: 4, name: 'Infrastructure & Learning Resources', marks: 100, icon: Building2 },
  { number: 5, name: 'Student Support & Progression', marks: 50, icon: Users },
  { number: 6, name: 'Governance, Leadership & Management', marks: 50, icon: Shield },
  { number: 7, name: 'Institutional Values & Best Practices', marks: 50, icon: Leaf },
]

export default function CollegeDashboard() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [college, setCollege] = useState<CollegeProfile | null>(null)
  const [criteriaProgress, setCriteriaProgress] = useState<CriterionProgress[]>([])
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([])
  const [notifications, setNotifications] = useState<any[]>([])

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setIsLoading(true)
    try {
      // TODO: Replace with actual API calls
      // For now, using mock data
      setCollege({
        id: '1',
        name: 'ABC College of Engineering',
        short_name: 'ABCCE',
        city: 'Hyderabad',
        state: 'Telangana',
        principal_name: 'Dr. Rajesh Kumar',
        subscription_plan: 'PRO',
        total_departments: 8,
        total_programs: 15,
        total_faculty: 120,
        total_students: 2500
      })

      setCriteriaProgress(CRITERIA.map(c => ({
        number: c.number,
        name: c.name,
        marks: c.marks,
        progress: Math.floor(Math.random() * 40),
        status: 'in_progress' as const,
        last_updated: '2 days ago'
      })))

      setTeamMembers([
        { id: '1', name: 'Dr. Priya Sharma', email: 'priya@college.edu', role: 'IQAC Coordinator', status: 'active' },
        { id: '2', name: 'Prof. Anil Reddy', email: 'anil@college.edu', role: 'Criterion 1 Head', criterion: 1, status: 'active' },
        { id: '3', name: 'Dr. Sunita Rao', email: 'sunita@college.edu', role: 'Criterion 2 Head', criterion: 2, status: 'active' },
        { id: '4', name: 'Mr. Venkat', email: 'venkat@college.edu', role: 'Data Entry', status: 'pending' },
      ])

      setNotifications([
        { id: '1', message: 'Criterion 1 data pending review', type: 'warning' },
        { id: '2', message: 'New team member invitation accepted', type: 'success' },
      ])
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const totalProgress = criteriaProgress.length > 0
    ? Math.round(criteriaProgress.reduce((sum, c) => sum + c.progress, 0) / criteriaProgress.length)
    : 0

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved': return 'bg-green-500'
      case 'submitted': return 'bg-blue-500'
      case 'in_progress': return 'bg-yellow-500'
      default: return 'bg-slate-500'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'approved': return 'Approved'
      case 'submitted': return 'Submitted'
      case 'in_progress': return 'In Progress'
      default: return 'Not Started'
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-amber-500 rounded-xl flex items-center justify-center">
                <Award className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-lg">{college?.short_name || 'College'} - NAAC Dashboard</h1>
                <p className="text-xs text-slate-400">{college?.name}</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Notifications */}
              <button className="relative p-2 hover:bg-slate-800 rounded-lg">
                <Bell className="w-5 h-5 text-slate-400" />
                {notifications.length > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
                )}
              </button>

              {/* Settings */}
              <button
                onClick={() => router.push('/accreditation/settings')}
                className="p-2 hover:bg-slate-800 rounded-lg"
              >
                <Settings className="w-5 h-5 text-slate-400" />
              </button>

              {/* Profile */}
              <div className="flex items-center gap-2 pl-4 border-l border-slate-700">
                <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4" />
                </div>
                <span className="text-sm">{college?.principal_name?.split(' ')[0]}</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <Target className="w-8 h-8 text-orange-500" />
              <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-1 rounded-full">Overall</span>
            </div>
            <div className="text-3xl font-bold mb-1">{totalProgress}%</div>
            <div className="text-sm text-slate-400">Completion Progress</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <Building2 className="w-8 h-8 text-blue-500" />
              <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full">Depts</span>
            </div>
            <div className="text-3xl font-bold mb-1">{college?.total_departments}</div>
            <div className="text-sm text-slate-400">Departments</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <Users className="w-8 h-8 text-green-500" />
              <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">Team</span>
            </div>
            <div className="text-3xl font-bold mb-1">{teamMembers.filter(t => t.status === 'active').length}</div>
            <div className="text-sm text-slate-400">Active Members</div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <FileText className="w-8 h-8 text-purple-500" />
              <span className="text-xs bg-purple-500/20 text-purple-400 px-2 py-1 rounded-full">SSR</span>
            </div>
            <div className="text-3xl font-bold mb-1">0</div>
            <div className="text-sm text-slate-400">Documents Ready</div>
          </div>
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Criteria Progress - 2 columns */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-orange-500" />
                Criteria Progress
              </h2>
              <Link
                href="/accreditation/criteria"
                className="text-sm text-orange-500 hover:text-orange-400 flex items-center gap-1"
              >
                View All <ChevronRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="space-y-3">
              {criteriaProgress.map((criterion) => {
                const CriterionIcon = CRITERIA.find(c => c.number === criterion.number)?.icon || FileText
                return (
                  <Link
                    key={criterion.number}
                    href={`/accreditation/criterion/${criterion.number}`}
                    className="block bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-orange-500/50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-slate-800 rounded-lg">
                        <CriterionIcon className="w-5 h-5 text-orange-500" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="font-medium">Criterion {criterion.number}</span>
                          <span className="text-sm text-slate-400">{criterion.marks} marks</span>
                        </div>
                        <div className="text-sm text-slate-400 mb-2">{criterion.name}</div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all"
                              style={{ width: `${criterion.progress}%` }}
                            />
                          </div>
                          <span className="text-sm font-medium w-12 text-right">{criterion.progress}%</span>
                        </div>
                      </div>
                      <div className={`px-2 py-1 rounded-full text-xs ${getStatusColor(criterion.status)} bg-opacity-20`}>
                        {getStatusText(criterion.status)}
                      </div>
                      <ChevronRight className="w-5 h-5 text-slate-500" />
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            {/* Quick Actions */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-orange-500" />
                Quick Actions
              </h3>
              <div className="space-y-2">
                <button
                  onClick={() => router.push('/accreditation/ssr/generate')}
                  className="w-full flex items-center gap-3 p-3 bg-gradient-to-r from-orange-500/20 to-amber-500/20 border border-orange-500/30 rounded-lg hover:border-orange-500 transition-colors text-left"
                >
                  <FileText className="w-5 h-5 text-orange-500" />
                  <div>
                    <div className="font-medium">Generate SSR</div>
                    <div className="text-xs text-slate-400">Auto-generate Self Study Report</div>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/accreditation/team/invite')}
                  className="w-full flex items-center gap-3 p-3 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors text-left"
                >
                  <Plus className="w-5 h-5 text-blue-500" />
                  <div>
                    <div className="font-medium">Invite Team Member</div>
                    <div className="text-xs text-slate-400">Add faculty to criteria</div>
                  </div>
                </button>
                <button
                  onClick={() => router.push('/accreditation/evidence/upload')}
                  className="w-full flex items-center gap-3 p-3 bg-slate-800 rounded-lg hover:bg-slate-700 transition-colors text-left"
                >
                  <Download className="w-5 h-5 text-green-500 rotate-180" />
                  <div>
                    <div className="font-medium">Upload Evidence</div>
                    <div className="text-xs text-slate-400">Add supporting documents</div>
                  </div>
                </button>
              </div>
            </div>

            {/* Team Members */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold flex items-center gap-2">
                  <Users className="w-5 h-5 text-orange-500" />
                  Team
                </h3>
                <Link
                  href="/accreditation/team"
                  className="text-xs text-orange-500 hover:text-orange-400"
                >
                  Manage
                </Link>
              </div>
              <div className="space-y-3">
                {teamMembers.slice(0, 4).map((member) => (
                  <div key={member.id} className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-slate-700 rounded-full flex items-center justify-center text-sm font-medium">
                      {member.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">{member.name}</div>
                      <div className="text-xs text-slate-400">{member.role}</div>
                    </div>
                    <div className={`w-2 h-2 rounded-full ${member.status === 'active' ? 'bg-green-500' : 'bg-yellow-500'}`} />
                  </div>
                ))}
              </div>
            </div>

            {/* Notifications */}
            {notifications.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Bell className="w-5 h-5 text-orange-500" />
                  Recent Activity
                </h3>
                <div className="space-y-3">
                  {notifications.map((notif) => (
                    <div key={notif.id} className="flex items-start gap-3 text-sm">
                      <div className={`w-2 h-2 rounded-full mt-1.5 ${
                        notif.type === 'warning' ? 'bg-yellow-500' : 'bg-green-500'
                      }`} />
                      <span className="text-slate-300">{notif.message}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Subscription Info */}
            <div className="bg-gradient-to-br from-orange-500/20 to-amber-500/20 border border-orange-500/30 rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold">Plan: {college?.subscription_plan}</span>
                <Award className="w-5 h-5 text-orange-500" />
              </div>
              <p className="text-sm text-slate-400 mb-3">
                Full access to all 7 criteria and SSR generation
              </p>
              <button className="text-sm text-orange-500 hover:text-orange-400">
                View plan details →
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
