'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Building2,
  Users,
  FileText,
  Award,
  Target,
  DollarSign,
  ChevronRight,
  Loader2,
  AlertCircle,
  Download,
  RefreshCw,
  ClipboardCheck,
  Calendar,
  Settings,
  BookOpen,
  TrendingUp,
  Shield,
  Briefcase,
  GraduationCap
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  total_governance_records: number
  current_year_governance: number
  total_meetings: number
  governing_body_meetings: number
  academic_council_meetings: number
  iqac_meetings: number
  total_policies: number
  active_policies: number
  pending_review_policies: number
  total_iqac_activities: number
  completed_activities: number
  ongoing_activities: number
  total_fdp_programs: number
  faculty_trained: number
  certificates_earned: number
  total_audits: number
  completed_audits: number
  pending_audits: number
  total_strategic_plans: number
  active_strategic_plans: number
}

const KEY_INDICATORS = [
  {
    id: '6.1',
    name: 'Institutional Vision & Leadership',
    description: 'Vision, mission, governance structure, and participative management',
    icon: Target,
    links: [
      { name: 'Governance', href: '/admin/accreditation/criterion6/governance' },
      { name: 'Leadership', href: '/admin/accreditation/criterion6/leadership' }
    ],
    color: 'blue'
  },
  {
    id: '6.2',
    name: 'Strategy Development & Deployment',
    description: 'Strategic planning, perspective plans, and institutional development',
    icon: TrendingUp,
    links: [
      { name: 'Strategic Plans', href: '/admin/accreditation/criterion6/strategic-plans' },
      { name: 'Perspective Plans', href: '/admin/accreditation/criterion6/perspective-plans' }
    ],
    color: 'green'
  },
  {
    id: '6.3',
    name: 'Faculty Empowerment',
    description: 'Professional development, welfare measures, and performance appraisal',
    icon: GraduationCap,
    links: [
      { name: 'Faculty Development', href: '/admin/accreditation/criterion6/faculty-development' },
      { name: 'Welfare Schemes', href: '/admin/accreditation/criterion6/welfare' }
    ],
    color: 'purple'
  },
  {
    id: '6.4',
    name: 'Financial Management & Resource Mobilization',
    description: 'Financial audits, resource mobilization, and utilization',
    icon: DollarSign,
    links: [
      { name: 'Financial Audits', href: '/admin/accreditation/criterion6/financial-audits' },
      { name: 'Resource Mobilization', href: '/admin/accreditation/criterion6/resources' }
    ],
    color: 'yellow'
  },
  {
    id: '6.5',
    name: 'Internal Quality Assurance System',
    description: 'IQAC activities, quality initiatives, and academic audits',
    icon: Shield,
    links: [
      { name: 'IQAC Activities', href: '/admin/accreditation/criterion6/iqac' },
      { name: 'Quality Audits', href: '/admin/accreditation/criterion6/audits' }
    ],
    color: 'teal'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Meeting', icon: Calendar, href: '/admin/accreditation/criterion6/meetings', color: 'blue' },
  { name: 'Add Policy', icon: FileText, href: '/admin/accreditation/criterion6/policies', color: 'green' },
  { name: 'Add IQAC Activity', icon: ClipboardCheck, href: '/admin/accreditation/criterion6/iqac', color: 'purple' },
  { name: 'Add FDP', icon: GraduationCap, href: '/admin/accreditation/criterion6/faculty-development', color: 'orange' },
  { name: 'Add Audit', icon: DollarSign, href: '/admin/accreditation/criterion6/financial-audits', color: 'yellow' },
  { name: 'Add Strategic Plan', icon: Target, href: '/admin/accreditation/criterion6/strategic-plans', color: 'teal' }
]

export default function Criterion6DashboardPage() {
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
      const response = await apiClient.get(`/accreditation/criterion6/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      setStats({
        total_governance_records: 0,
        current_year_governance: 0,
        total_meetings: 0,
        governing_body_meetings: 0,
        academic_council_meetings: 0,
        iqac_meetings: 0,
        total_policies: 0,
        active_policies: 0,
        pending_review_policies: 0,
        total_iqac_activities: 0,
        completed_activities: 0,
        ongoing_activities: 0,
        total_fdp_programs: 0,
        faculty_trained: 0,
        certificates_earned: 0,
        total_audits: 0,
        completed_audits: 0,
        pending_audits: 0,
        total_strategic_plans: 0,
        active_strategic_plans: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await apiClient.post('/accreditation/criterion6/generate-report', {
        institution_name: 'Institution Name',
        academic_year: academicYear,
        format: 'docx',
        include_analytics: true
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
      yellow: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: 'text-yellow-500' },
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
                <span className="text-white">Criterion 6</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 6: Governance, Leadership and Management</h1>
              <p className="text-slate-400 mt-1">150 Marks - Vision, strategic planning, IQAC, and financial management</p>
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

        {/* Key Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <StatCard
            icon={Calendar}
            label="Meetings"
            value={stats?.total_meetings || 0}
            subValue={`${stats?.governing_body_meetings || 0} GB meetings`}
            color="blue"
          />
          <StatCard
            icon={FileText}
            label="Policies"
            value={stats?.total_policies || 0}
            subValue={`${stats?.active_policies || 0} active`}
            color="green"
          />
          <StatCard
            icon={ClipboardCheck}
            label="IQAC Activities"
            value={stats?.total_iqac_activities || 0}
            subValue={`${stats?.completed_activities || 0} completed`}
            color="purple"
          />
          <StatCard
            icon={GraduationCap}
            label="FDP Programs"
            value={stats?.total_fdp_programs || 0}
            subValue={`${stats?.faculty_trained || 0} trained`}
            color="orange"
          />
          <StatCard
            icon={DollarSign}
            label="Financial Audits"
            value={stats?.total_audits || 0}
            subValue={`${stats?.completed_audits || 0} completed`}
            color="yellow"
          />
          <StatCard
            icon={Target}
            label="Strategic Plans"
            value={stats?.total_strategic_plans || 0}
            subValue={`${stats?.active_strategic_plans || 0} active`}
            color="teal"
          />
        </div>

        {/* Key Indicators */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Key Indicators (150 Marks)</h2>
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

        {/* Quick Actions & Meeting Summary */}
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

          {/* Meeting Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Governance Meetings</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Building2 className="w-5 h-5 text-blue-400" />
                  <span>Governing Body</span>
                </div>
                <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg font-semibold">
                  {stats?.governing_body_meetings || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <BookOpen className="w-5 h-5 text-green-400" />
                  <span>Academic Council</span>
                </div>
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg font-semibold">
                  {stats?.academic_council_meetings || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Shield className="w-5 h-5 text-purple-400" />
                  <span>IQAC Meetings</span>
                </div>
                <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg font-semibold">
                  {stats?.iqac_meetings || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* IQAC & FDP Stats */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* IQAC Activities */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">IQAC Activities Status</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                <ClipboardCheck className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.completed_activities || 0}</p>
                <p className="text-sm text-slate-400">Completed</p>
              </div>
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-center">
                <Settings className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.ongoing_activities || 0}</p>
                <p className="text-sm text-slate-400">Ongoing</p>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center col-span-2">
                <Shield className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_iqac_activities || 0}</p>
                <p className="text-sm text-slate-400">Total IQAC Initiatives</p>
              </div>
            </div>
          </div>

          {/* FDP & Audit Stats */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Faculty Development & Audits</h2>
            <div className="space-y-4">
              <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Faculty Trained</span>
                  <span className="text-2xl font-bold text-orange-400">{stats?.faculty_trained || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  {stats?.certificates_earned || 0} certificates earned
                </p>
              </div>
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Financial Audits</span>
                  <span className="text-2xl font-bold text-yellow-400">{stats?.completed_audits || 0}/{stats?.total_audits || 0}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-yellow-500 h-2 rounded-full"
                    style={{ width: `${stats?.total_audits ? (stats.completed_audits / stats.total_audits) * 100 : 0}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-1">{stats?.pending_audits || 0} pending</p>
              </div>
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
    yellow: 'text-yellow-400',
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
