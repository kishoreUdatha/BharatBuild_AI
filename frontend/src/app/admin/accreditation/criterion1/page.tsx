'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  BookOpen,
  MessageSquare,
  FileText,
  Building2,
  GraduationCap,
  Briefcase,
  ChevronRight,
  Loader2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Users,
  Award,
  Calendar,
  Download,
  RefreshCw,
  BarChart3,
  Target,
  Clock
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  curriculum_revisions: number
  board_meetings: number
  industry_expert_inputs: number
  elective_courses: number
  interdisciplinary_programs: number
  value_added_courses: number
  total_enrollments: number
  certifications_issued: number
  internships_total: number
  internships_ongoing: number
  total_feedback: number
  feedback_by_type: Record<string, number>
  action_taken_percentage: number
  total_evidence: number
  verified_evidence: number
  evidence_by_indicator: Record<string, number>
  active_mous: number
  total_partners: number
  students_benefited: number
  completion_percentage: number
  pending_items: Array<{ item: string; status: string }>
}

const KEY_INDICATORS = [
  {
    id: '1.1',
    name: 'Curriculum Planning and Implementation',
    description: 'Curriculum design with stakeholder involvement',
    icon: BookOpen,
    link: null,
    color: 'blue'
  },
  {
    id: '1.2',
    name: 'Academic Flexibility',
    description: 'Choice-based credit system, electives',
    icon: Target,
    link: null,
    color: 'purple'
  },
  {
    id: '1.3',
    name: 'Curriculum Enrichment',
    description: 'Value-added courses, internships, industry integration',
    icon: GraduationCap,
    links: [
      { name: 'Value-Added Courses', href: '/admin/accreditation/criterion1/value-added-courses' },
      { name: 'Internships', href: '/admin/accreditation/criterion1/internships' }
    ],
    color: 'green'
  },
  {
    id: '1.4',
    name: 'Feedback System',
    description: 'Structured feedback from stakeholders with action taken',
    icon: MessageSquare,
    links: [
      { name: 'Manage Feedback', href: '/admin/accreditation/criterion1/feedback' }
    ],
    color: 'orange'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Feedback', icon: MessageSquare, href: '/admin/accreditation/criterion1/feedback', color: 'orange' },
  { name: 'Upload Evidence', icon: FileText, href: '/admin/accreditation/criterion1/evidence', color: 'blue' },
  { name: 'Add Partner', icon: Building2, href: '/admin/accreditation/criterion1/industry-partners', color: 'purple' },
  { name: 'Add Course', icon: GraduationCap, href: '/admin/accreditation/criterion1/value-added-courses', color: 'green' },
  { name: 'Record Internship', icon: Briefcase, href: '/admin/accreditation/criterion1/internships', color: 'teal' }
]

export default function Criterion1DashboardPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [academicYear, setAcademicYear] = useState('2024-25')
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      if (user?.role !== 'admin' && user?.role !== 'faculty') {
        router.push('/accreditation')
        return
      }
      fetchDashboardStats()
    }
  }, [authLoading, isAuthenticated, user, academicYear])

  const fetchDashboardStats = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await apiClient.get(`/accreditation/criterion1/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      // Set default stats for demo
      setStats({
        curriculum_revisions: 0,
        board_meetings: 0,
        industry_expert_inputs: 0,
        elective_courses: 0,
        interdisciplinary_programs: 0,
        value_added_courses: 0,
        total_enrollments: 0,
        certifications_issued: 0,
        internships_total: 0,
        internships_ongoing: 0,
        total_feedback: 0,
        feedback_by_type: {},
        action_taken_percentage: 0,
        total_evidence: 0,
        verified_evidence: 0,
        evidence_by_indicator: {},
        active_mous: 0,
        total_partners: 0,
        students_benefited: 0,
        completion_percentage: 0,
        pending_items: []
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await apiClient.post('/accreditation/criterion1/generate-report', {
        institution_name: 'Institution Name', // TODO: Get from profile
        academic_year: academicYear,
        format: 'docx',
        include_evidence_list: true,
        include_analytics: true
      })
      if (response.success && response.report_path) {
        alert('Report generated successfully!')
      }
    } catch (err: any) {
      console.error('Failed to generate report:', err)
      alert('Failed to generate report: ' + err.message)
    } finally {
      setIsGeneratingReport(false)
    }
  }

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Navigation */}
      <AccreditationNav />

      {/* Header */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                <Link href="/admin/accreditation" className="hover:text-white">Accreditation</Link>
                <ChevronRight className="w-4 h-4" />
                <span className="text-white">Criterion 1</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 1: Curricular Aspects</h1>
              <p className="text-slate-400 mt-1">150 Marks - Curriculum design, academic flexibility, and feedback system</p>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="2024-25">2024-25</option>
                <option value="2023-24">2023-24</option>
                <option value="2022-23">2022-23</option>
              </select>
              <button
                onClick={fetchDashboardStats}
                className="p-2 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
              <button
                onClick={handleGenerateReport}
                disabled={isGeneratingReport}
                className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg disabled:opacity-50"
              >
                {isGeneratingReport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Generate Report
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Completion Progress */}
        {stats && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-green-500" />
                Overall Completion
              </h2>
              <button
                onClick={fetchDashboardStats}
                className="text-slate-400 hover:text-white transition-colors"
              >
                <RefreshCw className="w-5 h-5" />
              </button>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex-1 bg-slate-800 rounded-full h-4 overflow-hidden">
                <div
                  className="bg-gradient-to-r from-orange-500 to-orange-400 h-full rounded-full transition-all duration-500"
                  style={{ width: `${stats.completion_percentage}%` }}
                />
              </div>
              <span className="text-2xl font-bold text-orange-500">{stats.completion_percentage}%</span>
            </div>
            {stats.pending_items.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {stats.pending_items.map((item, idx) => (
                  <span key={idx} className="bg-yellow-500/10 text-yellow-400 px-3 py-1 rounded-full text-sm flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {item.item}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Quick Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <MessageSquare className="w-8 h-8 text-orange-500" />
                <span className="text-2xl font-bold">{stats.total_feedback}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Total Feedback</p>
              <p className="text-green-400 text-xs">{stats.action_taken_percentage}% action taken</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <FileText className="w-8 h-8 text-blue-500" />
                <span className="text-2xl font-bold">{stats.total_evidence}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Evidence Docs</p>
              <p className="text-green-400 text-xs">{stats.verified_evidence} verified</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <Building2 className="w-8 h-8 text-purple-500" />
                <span className="text-2xl font-bold">{stats.total_partners}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Industry Partners</p>
              <p className="text-green-400 text-xs">{stats.active_mous} active MoUs</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <GraduationCap className="w-8 h-8 text-green-500" />
                <span className="text-2xl font-bold">{stats.value_added_courses}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Value-Added Courses</p>
              <p className="text-green-400 text-xs">{stats.total_enrollments} enrollments</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <Briefcase className="w-8 h-8 text-teal-500" />
                <span className="text-2xl font-bold">{stats.internships_total}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Internships</p>
              <p className="text-green-400 text-xs">{stats.internships_ongoing} ongoing</p>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <Users className="w-8 h-8 text-pink-500" />
                <span className="text-2xl font-bold">{stats.students_benefited}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Students Benefited</p>
              <p className="text-green-400 text-xs">From partnerships</p>
            </div>
          </div>
        )}

        {/* Quick Actions */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon
              return (
                <Link
                  key={action.name}
                  href={action.href}
                  className={`bg-slate-900 border border-slate-800 rounded-xl p-4 hover:border-${action.color}-500 transition-colors group`}
                >
                  <Icon className={`w-8 h-8 text-${action.color}-500 mb-2 group-hover:scale-110 transition-transform`} />
                  <p className="font-medium">{action.name}</p>
                </Link>
              )
            })}
          </div>
        </div>

        {/* Key Indicators */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Key Indicators</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {KEY_INDICATORS.map((indicator) => {
              const Icon = indicator.icon
              const evidenceCount = stats?.evidence_by_indicator[indicator.id] || 0

              return (
                <div
                  key={indicator.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-3 rounded-lg bg-${indicator.color}-500/10`}>
                        <Icon className={`w-6 h-6 text-${indicator.color}-500`} />
                      </div>
                      <div>
                        <h3 className="font-semibold">{indicator.id} {indicator.name}</h3>
                        <p className="text-slate-400 text-sm">{indicator.description}</p>
                      </div>
                    </div>
                    <span className="bg-slate-800 text-slate-300 px-2 py-1 rounded text-sm">
                      {evidenceCount} docs
                    </span>
                  </div>

                  {'links' in indicator && indicator.links && (
                    <div className="flex flex-wrap gap-2 mt-4">
                      {indicator.links.map((link) => (
                        <Link
                          key={link.href}
                          href={link.href}
                          className="bg-slate-800 hover:bg-slate-700 text-white px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 transition-colors"
                        >
                          {link.name}
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Feedback by Type */}
        {stats && Object.keys(stats.feedback_by_type).length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-orange-500" />
              Feedback Distribution
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Object.entries(stats.feedback_by_type).map(([type, count]) => (
                <div key={type} className="bg-slate-800 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-orange-500">{count}</p>
                  <p className="text-slate-400 text-sm capitalize">{type.replace('_', ' ')}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Navigation Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Link
            href="/admin/accreditation/criterion1/feedback"
            className="bg-gradient-to-br from-orange-500/20 to-orange-600/20 border border-orange-500/30 rounded-xl p-6 hover:border-orange-500/50 transition-colors group"
          >
            <MessageSquare className="w-10 h-10 text-orange-500 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Feedback Management</h3>
            <p className="text-slate-400 text-sm mb-4">
              Collect and track feedback from students, alumni, employers, and teachers with action-taken reports.
            </p>
            <span className="text-orange-500 font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Manage Feedback <ChevronRight className="w-4 h-4" />
            </span>
          </Link>

          <Link
            href="/admin/accreditation/criterion1/evidence"
            className="bg-gradient-to-br from-blue-500/20 to-blue-600/20 border border-blue-500/30 rounded-xl p-6 hover:border-blue-500/50 transition-colors group"
          >
            <FileText className="w-10 h-10 text-blue-500 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Evidence Repository</h3>
            <p className="text-slate-400 text-sm mb-4">
              Upload and organize evidence documents categorized by key indicators with verification workflow.
            </p>
            <span className="text-blue-500 font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Manage Evidence <ChevronRight className="w-4 h-4" />
            </span>
          </Link>

          <Link
            href="/admin/accreditation/criterion1/industry-partners"
            className="bg-gradient-to-br from-purple-500/20 to-purple-600/20 border border-purple-500/30 rounded-xl p-6 hover:border-purple-500/50 transition-colors group"
          >
            <Building2 className="w-10 h-10 text-purple-500 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Industry Partners</h3>
            <p className="text-slate-400 text-sm mb-4">
              Track MoUs, collaborations, and advisory board meetings with industry experts.
            </p>
            <span className="text-purple-500 font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Manage Partners <ChevronRight className="w-4 h-4" />
            </span>
          </Link>

          <Link
            href="/admin/accreditation/criterion1/value-added-courses"
            className="bg-gradient-to-br from-green-500/20 to-green-600/20 border border-green-500/30 rounded-xl p-6 hover:border-green-500/50 transition-colors group"
          >
            <GraduationCap className="w-10 h-10 text-green-500 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Value-Added Courses</h3>
            <p className="text-slate-400 text-sm mb-4">
              Manage skill development programs, certifications, and student enrollments.
            </p>
            <span className="text-green-500 font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Manage Courses <ChevronRight className="w-4 h-4" />
            </span>
          </Link>

          <Link
            href="/admin/accreditation/criterion1/internships"
            className="bg-gradient-to-br from-teal-500/20 to-teal-600/20 border border-teal-500/30 rounded-xl p-6 hover:border-teal-500/50 transition-colors group"
          >
            <Briefcase className="w-10 h-10 text-teal-500 mb-4" />
            <h3 className="text-xl font-semibold mb-2">Internship Tracking</h3>
            <p className="text-slate-400 text-sm mb-4">
              Record and analyze student internships with company details and outcomes.
            </p>
            <span className="text-teal-500 font-medium flex items-center gap-1 group-hover:gap-2 transition-all">
              Manage Internships <ChevronRight className="w-4 h-4" />
            </span>
          </Link>
        </div>
      </div>
    </div>
  )
}
