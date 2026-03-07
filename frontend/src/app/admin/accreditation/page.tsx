'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Award,
  FileText,
  Users,
  ClipboardCheck,
  Settings,
  FolderOpen,
  CheckSquare,
  Shield,
  ChevronRight,
  BarChart3,
  BookOpen,
  GraduationCap,
  Building2,
  Leaf,
  TrendingUp,
  Sparkles,
  PieChart,
  Building,
  Eye,
  Clock,
  CheckCircle2
} from 'lucide-react'
import {
  SAMPLE_APPLICATIONS,
  SAMPLE_INSTITUTIONS,
  DASHBOARD_STATS,
  getInstitutionById,
  getBinaryStatusLabel,
  getMBGLLevelLabel,
  getPhaseLabel
} from '@/data/sampleAccreditationData'
import { useAuth } from '@/hooks/useAuth'
import { useNAACRole } from '@/contexts/NAACRoleContext'

const CRITERIA_ICONS = [BookOpen, GraduationCap, FileText, Building2, Users, Shield, Leaf]

export default function AccreditationLandingPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const { roles, highestRole } = useNAACRole()

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  // Quick stats from sample data
  const stats = {
    criteriaCompleted: 7,
    documentsGenerated: DASHBOARD_STATS.totalApplications,
    pendingTasks: DASHBOARD_STATS.underReview,
    pendingApprovals: DASHBOARD_STATS.applied
  }

  // Get recent applications for display
  const recentApplications = SAMPLE_APPLICATIONS.slice(0, 3)

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      accredited: 'bg-green-500/20 text-green-400 border-green-500/30',
      under_review: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      applied: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      not_applied: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
    }
    return colors[status] || colors.not_applied
  }

  const getLevelBadge = (level: string) => {
    const colors: Record<string, string> = {
      level_5: 'bg-green-500',
      level_4: 'bg-blue-500',
      level_3: 'bg-yellow-500',
      level_2: 'bg-orange-500',
      level_1: 'bg-red-500',
      not_assessed: 'bg-slate-500',
    }
    return colors[level] || colors.not_assessed
  }

  return (
    <div className="p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-orange-500/20 rounded-xl">
              <Award className="w-10 h-10 text-orange-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">NAAC Accreditation</h1>
              <p className="text-slate-400">
                {highestRole ? `Welcome, ${highestRole.role_display_name}` : 'Manage accreditation process'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="bg-green-500/20 text-green-400 px-4 py-2 rounded-full text-sm font-medium">
              700 Total Marks
            </span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-2">
              <ClipboardCheck className="w-5 h-5 text-blue-400" />
              <span className="text-slate-400 text-sm">Criteria</span>
            </div>
            <div className="text-2xl font-bold">{stats.criteriaCompleted}/7</div>
            <div className="text-sm text-slate-500">Completed</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-2">
              <FolderOpen className="w-5 h-5 text-green-400" />
              <span className="text-slate-400 text-sm">Documents</span>
            </div>
            <div className="text-2xl font-bold">{stats.documentsGenerated}</div>
            <div className="text-sm text-slate-500">Generated</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-2">
              <CheckSquare className="w-5 h-5 text-yellow-400" />
              <span className="text-slate-400 text-sm">Tasks</span>
            </div>
            <div className="text-2xl font-bold">{stats.pendingTasks}</div>
            <div className="text-sm text-slate-500">Pending</div>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-5 h-5 text-purple-400" />
              <span className="text-slate-400 text-sm">Approvals</span>
            </div>
            <div className="text-2xl font-bold">{stats.pendingApprovals}</div>
            <div className="text-sm text-slate-500">Awaiting</div>
          </div>
        </div>

        {/* Main Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <a
            href="/admin/accreditation/dashboard"
            className="bg-gradient-to-br from-orange-500 to-red-600 p-6 rounded-xl hover:from-orange-400 hover:to-red-500 transition-all group"
          >
            <BarChart3 className="w-8 h-8 mb-4" />
            <h3 className="text-lg font-semibold mb-1">My Dashboard</h3>
            <p className="text-sm text-orange-100">Role-based dashboard with your tasks and approvals</p>
            <ChevronRight className="w-5 h-5 mt-4 group-hover:translate-x-1 transition-transform" />
          </a>

          <a
            href="/admin/accreditation/ssr"
            className="bg-gradient-to-br from-blue-500 to-cyan-600 p-6 rounded-xl hover:from-blue-400 hover:to-cyan-500 transition-all group"
          >
            <FileText className="w-8 h-8 mb-4" />
            <h3 className="text-lg font-semibold mb-1">Generate SSR</h3>
            <p className="text-sm text-blue-100">Complete Self Study Report for all 7 criteria</p>
            <ChevronRight className="w-5 h-5 mt-4 group-hover:translate-x-1 transition-transform" />
          </a>

          <a
            href="/admin/accreditation/tasks"
            className="bg-gradient-to-br from-green-500 to-emerald-600 p-6 rounded-xl hover:from-green-400 hover:to-emerald-500 transition-all group"
          >
            <CheckSquare className="w-8 h-8 mb-4" />
            <h3 className="text-lg font-semibold mb-1">Task Management</h3>
            <p className="text-sm text-green-100">View and manage accreditation tasks</p>
            <ChevronRight className="w-5 h-5 mt-4 group-hover:translate-x-1 transition-transform" />
          </a>
        </div>

        {/* IQAC & Documentation Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <Shield className="w-5 h-5 text-purple-500" />
              IQAC Documents
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              Organizational structure, committee orders, role allocation circulars.
            </p>
            <a
              href="/admin/accreditation/iqac"
              className="inline-flex items-center gap-2 bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-sm"
            >
              Generate Documents <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <ClipboardCheck className="w-5 h-5 text-green-500" />
              Evidence Mapping
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              Track all metrics and evidence across criteria. Export to CSV.
            </p>
            <a
              href="/admin/accreditation/evidence"
              className="inline-flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg text-sm"
            >
              Manage Evidence <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-500" />
              AQAR Generator
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              Annual Quality Assurance Report with all criteria and SWOT analysis.
            </p>
            <a
              href="/admin/accreditation/aqar"
              className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg text-sm"
            >
              Create AQAR <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <ClipboardCheck className="w-5 h-5 text-teal-500" />
              DVV Clarifications
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              Prepare Data Validation & Verification responses with AI assistance.
            </p>
            <a
              href="/admin/accreditation/dvv"
              className="inline-flex items-center gap-2 bg-teal-500 hover:bg-teal-600 text-white px-4 py-2 rounded-lg text-sm"
            >
              Manage DVV <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-3 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-yellow-500" />
              Document Repository
            </h3>
            <p className="text-slate-400 text-sm mb-4">
              View and manage all generated NAAC documents.
            </p>
            <a
              href="/admin/accreditation/documents"
              className="inline-flex items-center gap-2 bg-yellow-500 hover:bg-yellow-600 text-black px-4 py-2 rounded-lg text-sm"
            >
              View Documents <ChevronRight className="w-4 h-4" />
            </a>
          </div>
        </div>

        {/* Criteria Grid */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <ClipboardCheck className="w-5 h-5 text-orange-500" />
            NAAC Criteria (700 Marks)
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {[
              { num: 1, name: 'Curricular Aspects', marks: 150 },
              { num: 2, name: 'Teaching-Learning', marks: 200 },
              { num: 3, name: 'Research & Extension', marks: 150 },
              { num: 4, name: 'Infrastructure', marks: 100 },
              { num: 5, name: 'Student Support', marks: 100 },
              { num: 6, name: 'Governance', marks: 100 },
              { num: 7, name: 'Best Practices', marks: 100 },
            ].map((criterion) => {
              const Icon = CRITERIA_ICONS[criterion.num - 1]
              return (
                <a
                  key={criterion.num}
                  href={`/admin/accreditation/criterion${criterion.num}`}
                  className="bg-slate-800 hover:bg-slate-700 border border-slate-700 hover:border-orange-500/50 rounded-xl p-4 text-center transition-all"
                >
                  <Icon className="w-6 h-6 text-orange-400 mx-auto mb-2" />
                  <div className="text-sm font-medium">Criterion {criterion.num}</div>
                  <div className="text-xs text-slate-400 mt-1">{criterion.marks} marks</div>
                </a>
              )
            })}
          </div>

          {/* NBA Link */}
          <div className="mt-4 pt-4 border-t border-slate-800">
            <a
              href="/admin/accreditation/nba"
              className="flex items-center justify-between p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-xl hover:bg-indigo-500/20 transition-all"
            >
              <div className="flex items-center gap-3">
                <Award className="w-6 h-6 text-indigo-400" />
                <div>
                  <div className="font-medium">NBA Accreditation</div>
                  <div className="text-sm text-slate-400">Program-level OBE accreditation</div>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-indigo-400" />
            </a>
          </div>
        </div>

        {/* NAAC 2025 Framework - Binary + MBGL */}
        <div className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-xl p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <Sparkles className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">NAAC 2025 Framework</h2>
              <p className="text-sm text-slate-400">Binary Accreditation + MBGL (Maturity-Based Graded Levels)</p>
            </div>
            <span className="ml-auto px-3 py-1 bg-green-500/20 text-green-400 text-xs font-medium rounded-full">NEW</span>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Binary Accreditation */}
            <a
              href="/admin/accreditation/settings"
              className="p-4 bg-slate-900/50 border border-slate-700 rounded-xl hover:border-blue-500/50 transition-all group"
            >
              <div className="flex items-center gap-3 mb-2">
                <Shield className="w-5 h-5 text-blue-400" />
                <span className="font-medium">Binary Accreditation</span>
              </div>
              <p className="text-sm text-slate-400 mb-3">
                Simple status: Accredited or Not Accredited. Replaces old CGPA grading.
              </p>
              <div className="flex items-center gap-2 text-blue-400 text-sm group-hover:gap-3 transition-all">
                Configure Status <ChevronRight className="w-4 h-4" />
              </div>
            </a>

            {/* MBGL Assessment */}
            <a
              href="/admin/accreditation/mbgl"
              className="p-4 bg-slate-900/50 border border-slate-700 rounded-xl hover:border-green-500/50 transition-all group"
            >
              <div className="flex items-center gap-3 mb-2">
                <TrendingUp className="w-5 h-5 text-green-400" />
                <span className="font-medium">MBGL Assessment</span>
              </div>
              <p className="text-sm text-slate-400 mb-3">
                Maturity Levels 1-5 across 8 dimensions. For accredited institutions only.
              </p>
              <div className="flex items-center gap-2 text-green-400 text-sm group-hover:gap-3 transition-all">
                Start Assessment <ChevronRight className="w-4 h-4" />
              </div>
            </a>
          </div>

          {/* Key Changes Info */}
          <div className="mt-4 p-3 bg-slate-800/50 rounded-lg">
            <p className="text-xs text-slate-400">
              <span className="text-green-400 font-medium">Key Changes:</span> 3-year validity (vs 5), 10 attributes (vs 7 criteria), AI-driven assessment, Digital document verification
            </p>
          </div>
        </div>

        {/* Sample Data Section */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Building className="w-5 h-5 text-blue-500" />
              Recent Applications (Sample Data)
            </h2>
            <a
              href="/admin/accreditation/analytics"
              className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300"
            >
              <PieChart className="w-4 h-4" />
              View All Analytics
              <ChevronRight className="w-4 h-4" />
            </a>
          </div>

          {/* Summary Stats */}
          <div className="grid grid-cols-4 gap-3 mb-6">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-green-400">{DASHBOARD_STATS.accredited}</p>
              <p className="text-xs text-slate-400">Accredited</p>
            </div>
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-yellow-400">{DASHBOARD_STATS.underReview}</p>
              <p className="text-xs text-slate-400">Under Review</p>
            </div>
            <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-purple-400">{DASHBOARD_STATS.averageMaturityScore.toFixed(2)}</p>
              <p className="text-xs text-slate-400">Avg Maturity</p>
            </div>
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-blue-400">{DASHBOARD_STATS.completionRate}%</p>
              <p className="text-xs text-slate-400">Completion</p>
            </div>
          </div>

          {/* Recent Applications List */}
          <div className="space-y-3">
            {recentApplications.map(app => {
              const institution = getInstitutionById(app.institutionId)
              const levelNum = app.mbglLevel.replace('level_', 'L').replace('not_assessed', 'N/A')
              return (
                <div key={app.id} className="flex items-center gap-4 p-4 bg-slate-800 rounded-xl hover:bg-slate-700 transition-colors">
                  <div className={`w-12 h-12 ${getLevelBadge(app.mbglLevel)} rounded-xl flex items-center justify-center text-white font-bold`}>
                    {levelNum}
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium">{institution?.name}</h4>
                    <p className="text-sm text-slate-400">{institution?.location} | {app.cycle} cycle</p>
                  </div>
                  <div className="text-right">
                    <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(app.binaryStatus)}`}>
                      {getBinaryStatusLabel(app.binaryStatus)}
                    </span>
                    <p className="text-sm text-slate-500 mt-1">
                      {app.currentPhase === 'completed' ? (
                        <span className="flex items-center gap-1 text-green-400 justify-end">
                          <CheckCircle2 className="w-3 h-3" /> Completed
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 justify-end">
                          <Clock className="w-3 h-3" /> {getPhaseLabel(app.currentPhase)}
                        </span>
                      )}
                    </p>
                  </div>
                  <a
                    href="/admin/accreditation/mbgl"
                    className="p-2 hover:bg-slate-600 rounded-lg"
                  >
                    <Eye className="w-4 h-4 text-slate-400" />
                  </a>
                </div>
              )
            })}
          </div>

          <div className="mt-4 flex justify-center">
            <a
              href="/admin/accreditation/analytics"
              className="px-6 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg text-sm font-medium transition-colors"
            >
              View All {DASHBOARD_STATS.totalApplications} Applications
            </a>
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <a
            href="/admin/accreditation/documents"
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors flex items-center gap-4"
          >
            <FolderOpen className="w-6 h-6 text-blue-400" />
            <div>
              <div className="font-medium">Documents</div>
              <div className="text-sm text-slate-400">View generated docs</div>
            </div>
          </a>

          <a
            href="/admin/accreditation/approvals"
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors flex items-center gap-4"
          >
            <Shield className="w-6 h-6 text-purple-400" />
            <div>
              <div className="font-medium">Approvals</div>
              <div className="text-sm text-slate-400">Review submissions</div>
            </div>
          </a>

          <a
            href="/admin/accreditation/roles/manage"
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors flex items-center gap-4"
          >
            <Users className="w-6 h-6 text-green-400" />
            <div>
              <div className="font-medium">Role Management</div>
              <div className="text-sm text-slate-400">Assign NAAC roles</div>
            </div>
          </a>

          <a
            href="/admin/accreditation/settings"
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors flex items-center gap-4"
          >
            <Settings className="w-6 h-6 text-yellow-400" />
            <div>
              <div className="font-medium">Settings</div>
              <div className="text-sm text-slate-400">Institution profile</div>
            </div>
          </a>
        </div>
      </div>
    </div>
  )
}
