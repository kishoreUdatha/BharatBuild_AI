'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  BookOpen,
  Users,
  GraduationCap,
  Award,
  ClipboardCheck,
  BarChart3,
  ChevronRight,
  Loader2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Calendar,
  Download,
  RefreshCw,
  Target,
  MonitorPlay,
  FileText,
  Clock,
  Brain,
  Laptop
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  total_students: number
  student_diversity: Record<string, number>
  total_teachers: number
  student_teacher_ratio: number
  teachers_with_phd: number
  phd_percentage: number
  lms_adoption_rate: number
  total_digital_content: number
  blended_learning_sessions: number
  lesson_plans_created: number
  teaching_methods_used: Record<string, number>
  teachers_with_awards: number
  average_experience_years: number
  fdp_participation_rate: number
  average_feedback_rating: number
  rubrics_created: number
  cie_assessments: number
  blooms_coverage: Record<string, number>
  average_pass_percentage: number
  students_with_distinction: number
  average_co_attainment: number
  average_po_attainment: number
  completion_percentage: number
  pending_items: Array<{ item: string; status: string; action: string }>
}

const KEY_INDICATORS = [
  {
    id: '2.1',
    name: 'Student Enrollment and Profile',
    description: 'Student enrollment data, diversity, and progression',
    icon: Users,
    link: null,
    color: 'blue'
  },
  {
    id: '2.2',
    name: 'Student-Teacher Ratio',
    description: 'Full-time teachers, qualifications, experience',
    icon: GraduationCap,
    links: [
      { name: 'Teacher Profiles', href: '/admin/accreditation/criterion2/teachers' }
    ],
    color: 'purple'
  },
  {
    id: '2.3',
    name: 'Teaching-Learning Process',
    description: 'LMS, ICT, experiential learning, blended mode',
    icon: Laptop,
    links: [
      { name: 'LMS Adoption', href: '/admin/accreditation/criterion2/lms' },
      { name: 'Lesson Plans', href: '/admin/accreditation/criterion2/lesson-plans' },
      { name: 'Digital Content', href: '/admin/accreditation/criterion2/digital-content' },
      { name: 'Blended Learning', href: '/admin/accreditation/criterion2/blended-learning' }
    ],
    color: 'green'
  },
  {
    id: '2.4',
    name: 'Teacher Quality',
    description: 'Awards, FDPs, research, API scores',
    icon: Award,
    links: [
      { name: 'Teacher Profiles', href: '/admin/accreditation/criterion2/teachers' }
    ],
    color: 'orange'
  },
  {
    id: '2.5',
    name: 'Evaluation Process and Reforms',
    description: 'CIE, rubrics-based evaluation, Bloom\'s taxonomy',
    icon: ClipboardCheck,
    links: [
      { name: 'CIE Records', href: '/admin/accreditation/criterion2/cie' },
      { name: 'Rubrics', href: '/admin/accreditation/criterion2/rubrics' }
    ],
    color: 'red'
  },
  {
    id: '2.6',
    name: 'Student Performance & Learning Outcomes',
    description: 'Pass percentage, CO/PO attainment, analytics',
    icon: BarChart3,
    links: [
      { name: 'Performance Analytics', href: '/admin/accreditation/criterion2/performance' },
      { name: 'LO Attainment', href: '/admin/accreditation/criterion2/lo-attainment' }
    ],
    color: 'teal'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Teacher', icon: GraduationCap, href: '/admin/accreditation/criterion2/teachers', color: 'purple' },
  { name: 'Create Lesson Plan', icon: BookOpen, href: '/admin/accreditation/criterion2/lesson-plans', color: 'blue' },
  { name: 'Add CIE Record', icon: ClipboardCheck, href: '/admin/accreditation/criterion2/cie', color: 'red' },
  { name: 'Create Rubric', icon: FileText, href: '/admin/accreditation/criterion2/rubrics', color: 'orange' },
  { name: 'Record Performance', icon: BarChart3, href: '/admin/accreditation/criterion2/performance', color: 'green' }
]

const BLOOMS_LEVELS = [
  { id: 'L1_remember', label: 'L1: Remember', color: '#f87171' },
  { id: 'L2_understand', label: 'L2: Understand', color: '#fb923c' },
  { id: 'L3_apply', label: 'L3: Apply', color: '#facc15' },
  { id: 'L4_analyze', label: 'L4: Analyze', color: '#4ade80' },
  { id: 'L5_evaluate', label: 'L5: Evaluate', color: '#22d3ee' },
  { id: 'L6_create', label: 'L6: Create', color: '#a78bfa' }
]

export default function Criterion2DashboardPage() {
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
      const response = await apiClient.get(`/accreditation/criterion2/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      // Set default stats for demo
      setStats({
        total_students: 0,
        student_diversity: {},
        total_teachers: 0,
        student_teacher_ratio: 0,
        teachers_with_phd: 0,
        phd_percentage: 0,
        lms_adoption_rate: 0,
        total_digital_content: 0,
        blended_learning_sessions: 0,
        lesson_plans_created: 0,
        teaching_methods_used: {},
        teachers_with_awards: 0,
        average_experience_years: 0,
        fdp_participation_rate: 0,
        average_feedback_rating: 0,
        rubrics_created: 0,
        cie_assessments: 0,
        blooms_coverage: {},
        average_pass_percentage: 0,
        students_with_distinction: 0,
        average_co_attainment: 0,
        average_po_attainment: 0,
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
      const response = await apiClient.post('/accreditation/criterion2/generate-report', {
        institution_name: 'Institution Name',
        academic_year: academicYear,
        format: 'docx',
        include_analytics: true,
        include_evidence_list: true
      })
      if (response.success && response.report_path) {
        window.open(`/api/v1/files/${response.report_path}`, '_blank')
      }
    } catch (err: any) {
      console.error('Failed to generate report:', err)
      setError(err.message || 'Failed to generate report')
    } finally {
      setIsGeneratingReport(false)
    }
  }

  const getColorClasses = (color: string) => {
    const colors: Record<string, { bg: string; border: string; text: string; icon: string }> = {
      blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: 'text-blue-500' },
      purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-400', icon: 'text-purple-500' },
      green: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', icon: 'text-green-500' },
      orange: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', icon: 'text-orange-500' },
      red: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', icon: 'text-red-500' },
      teal: { bg: 'bg-teal-500/10', border: 'border-teal-500/30', text: 'text-teal-400', icon: 'text-teal-500' }
    }
    return colors[color] || colors.blue
  }

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
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
                <span className="text-white">Criterion 2</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 2: Teaching-Learning and Evaluation</h1>
              <p className="text-slate-400 mt-1">200 Marks - Student-centric methods, ICT, and outcome-based education</p>
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
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
              >
                {isGeneratingReport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Generate Report
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-400">{error}</span>
          </div>
        )}

        {/* Completion Progress */}
        <div className="mb-8 p-6 bg-slate-900 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold">Criterion 2 Readiness</h2>
              <p className="text-sm text-slate-400">Overall completion for NAAC submission</p>
            </div>
            <div className="text-3xl font-bold text-blue-400">{stats?.completion_percentage || 0}%</div>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-blue-500 to-purple-500 h-3 rounded-full transition-all duration-500"
              style={{ width: `${stats?.completion_percentage || 0}%` }}
            />
          </div>
        </div>

        {/* Key Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <StatCard
            icon={Users}
            label="Total Students"
            value={stats?.total_students || 0}
            color="blue"
          />
          <StatCard
            icon={GraduationCap}
            label="Total Teachers"
            value={stats?.total_teachers || 0}
            subValue={`${stats?.phd_percentage || 0}% Ph.D.`}
            color="purple"
          />
          <StatCard
            icon={Target}
            label="Student:Teacher"
            value={`${stats?.student_teacher_ratio || 0}:1`}
            color="green"
          />
          <StatCard
            icon={Laptop}
            label="LMS Adoption"
            value={`${stats?.lms_adoption_rate || 0}%`}
            color="teal"
          />
          <StatCard
            icon={BarChart3}
            label="Pass %"
            value={`${stats?.average_pass_percentage || 0}%`}
            color="orange"
          />
          <StatCard
            icon={Brain}
            label="Avg CO Attainment"
            value={stats?.average_co_attainment?.toFixed(2) || '0'}
            color="red"
          />
        </div>

        {/* Key Indicators */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Key Indicators (200 Marks)</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {KEY_INDICATORS.map((indicator) => {
              const colorClasses = getColorClasses(indicator.color)
              const Icon = indicator.icon
              return (
                <div
                  key={indicator.id}
                  className={`p-5 ${colorClasses.bg} border ${colorClasses.border} rounded-xl`}
                >
                  <div className="flex items-start gap-3 mb-3">
                    <div className={`p-2 rounded-lg ${colorClasses.bg}`}>
                      <Icon className={`w-5 h-5 ${colorClasses.icon}`} />
                    </div>
                    <div>
                      <div className={`text-sm font-medium ${colorClasses.text}`}>{indicator.id}</div>
                      <h3 className="font-semibold">{indicator.name}</h3>
                    </div>
                  </div>
                  <p className="text-sm text-slate-400 mb-3">{indicator.description}</p>
                  {indicator.links && (
                    <div className="flex flex-wrap gap-2">
                      {indicator.links.map((link) => (
                        <Link
                          key={link.href}
                          href={link.href}
                          className={`text-xs px-3 py-1.5 ${colorClasses.bg} ${colorClasses.text} rounded-full hover:opacity-80 transition-opacity`}
                        >
                          {link.name}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Quick Actions & Bloom's Coverage */}
        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Quick Actions */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {QUICK_ACTIONS.map((action) => {
                const colorClasses = getColorClasses(action.color)
                const Icon = action.icon
                return (
                  <Link
                    key={action.name}
                    href={action.href}
                    className={`flex flex-col items-center gap-2 p-4 ${colorClasses.bg} border ${colorClasses.border} rounded-xl hover:opacity-80 transition-opacity`}
                  >
                    <Icon className={`w-6 h-6 ${colorClasses.icon}`} />
                    <span className="text-sm text-center">{action.name}</span>
                  </Link>
                )
              })}
            </div>
          </div>

          {/* Bloom's Taxonomy Coverage */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Bloom's Taxonomy Coverage</h2>
            <div className="space-y-3">
              {BLOOMS_LEVELS.map((level) => {
                const count = stats?.blooms_coverage?.[level.id] || 0
                const total = Object.values(stats?.blooms_coverage || {}).reduce((a, b) => a + b, 0) || 1
                const percentage = Math.round((count / total) * 100)
                return (
                  <div key={level.id}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{level.label}</span>
                      <span className="text-slate-400">{count} ({percentage}%)</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <div
                        className="h-2 rounded-full transition-all duration-300"
                        style={{ width: `${percentage}%`, backgroundColor: level.color }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        {/* Teaching Methods & Pending Items */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Teaching Methods Used */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Teaching Methods Distribution</h2>
            <div className="space-y-2">
              {Object.entries(stats?.teaching_methods_used || {}).slice(0, 6).map(([method, count]) => (
                <div key={method} className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                  <span className="capitalize">{method.replace(/_/g, ' ')}</span>
                  <span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-sm rounded">{count}</span>
                </div>
              ))}
              {Object.keys(stats?.teaching_methods_used || {}).length === 0 && (
                <p className="text-slate-400 text-sm text-center py-4">No teaching methods recorded yet</p>
              )}
            </div>
          </div>

          {/* Pending Items */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Pending Items</h2>
            <div className="space-y-3">
              {stats?.pending_items?.map((item, index) => (
                <div key={index} className="p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-yellow-500 mt-0.5" />
                    <div>
                      <p className="font-medium text-yellow-400">{item.item}</p>
                      <p className="text-sm text-slate-400">{item.status}</p>
                      <p className="text-sm text-slate-300 mt-1">{item.action}</p>
                    </div>
                  </div>
                </div>
              ))}
              {(!stats?.pending_items || stats.pending_items.length === 0) && (
                <div className="flex items-center justify-center gap-2 p-4 text-green-400">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>All items completed!</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color
}: {
  icon: any
  label: string
  value: string | number
  subValue?: string
  color: string
}) {
  const colorClasses: Record<string, string> = {
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    green: 'text-green-400',
    orange: 'text-orange-400',
    red: 'text-red-400',
    teal: 'text-teal-400'
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <Icon className={`w-5 h-5 ${colorClasses[color]} mb-2`} />
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm text-slate-400">{label}</p>
      {subValue && <p className={`text-xs ${colorClasses[color]} mt-1`}>{subValue}</p>}
    </div>
  )
}
