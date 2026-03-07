'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Users,
  GraduationCap,
  Briefcase,
  Award,
  Heart,
  MessageSquare,
  ChevronRight,
  Loader2,
  AlertCircle,
  Download,
  RefreshCw,
  Trophy,
  UserCheck,
  Building2,
  TrendingUp,
  DollarSign,
  Target,
  BookOpen,
  Handshake
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  total_scholarships: number
  government_scholarships: number
  institutional_scholarships: number
  total_scholarship_amount: number
  total_placements: number
  placed_students: number
  average_package: number
  highest_package: number
  total_career_sessions: number
  students_counseled: number
  total_grievances: number
  resolved_grievances: number
  pending_grievances: number
  total_alumni: number
  active_alumni: number
  alumni_contributors: number
  total_mentoring_sessions: number
  students_mentored: number
  total_competitive_exams: number
  students_qualified: number
}

const KEY_INDICATORS = [
  {
    id: '5.1',
    name: 'Student Support',
    description: 'Scholarships, fee concessions, and financial assistance',
    icon: DollarSign,
    links: [
      { name: 'Scholarships', href: '/admin/accreditation/criterion5/scholarships' },
      { name: 'Fee Concessions', href: '/admin/accreditation/criterion5/fee-concessions' }
    ],
    color: 'green'
  },
  {
    id: '5.2',
    name: 'Student Progression',
    description: 'Higher education, placements, competitive examinations',
    icon: TrendingUp,
    links: [
      { name: 'Placements', href: '/admin/accreditation/criterion5/placements' },
      { name: 'Competitive Exams', href: '/admin/accreditation/criterion5/competitive-exams' }
    ],
    color: 'blue'
  },
  {
    id: '5.3',
    name: 'Student Participation',
    description: 'Sports, cultural, and technical activities and achievements',
    icon: Trophy,
    links: [
      { name: 'Student Activities', href: '/admin/accreditation/criterion5/activities' },
      { name: 'Awards & Recognition', href: '/admin/accreditation/criterion5/awards' }
    ],
    color: 'purple'
  },
  {
    id: '5.4',
    name: 'Alumni Engagement',
    description: 'Alumni association, contributions, and engagement activities',
    icon: Users,
    links: [
      { name: 'Alumni Records', href: '/admin/accreditation/criterion5/alumni' },
      { name: 'Alumni Contributions', href: '/admin/accreditation/criterion5/alumni-contributions' }
    ],
    color: 'orange'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Scholarship', icon: DollarSign, href: '/admin/accreditation/criterion5/scholarships', color: 'green' },
  { name: 'Add Placement', icon: Briefcase, href: '/admin/accreditation/criterion5/placements', color: 'blue' },
  { name: 'Career Counseling', icon: Target, href: '/admin/accreditation/criterion5/career-counseling', color: 'purple' },
  { name: 'Add Grievance', icon: MessageSquare, href: '/admin/accreditation/criterion5/grievances', color: 'red' },
  { name: 'Add Alumni', icon: Users, href: '/admin/accreditation/criterion5/alumni', color: 'orange' },
  { name: 'Add Mentoring', icon: UserCheck, href: '/admin/accreditation/criterion5/mentoring', color: 'teal' }
]

export default function Criterion5DashboardPage() {
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
      const response = await apiClient.get(`/accreditation/criterion5/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      setStats({
        total_scholarships: 0,
        government_scholarships: 0,
        institutional_scholarships: 0,
        total_scholarship_amount: 0,
        total_placements: 0,
        placed_students: 0,
        average_package: 0,
        highest_package: 0,
        total_career_sessions: 0,
        students_counseled: 0,
        total_grievances: 0,
        resolved_grievances: 0,
        pending_grievances: 0,
        total_alumni: 0,
        active_alumni: 0,
        alumni_contributors: 0,
        total_mentoring_sessions: 0,
        students_mentored: 0,
        total_competitive_exams: 0,
        students_qualified: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await apiClient.post('/accreditation/criterion5/generate-report', {
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

  const formatCurrency = (amount: number) => {
    if (amount >= 10000000) return `${(amount / 10000000).toFixed(2)} Cr`
    if (amount >= 100000) return `${(amount / 100000).toFixed(2)} L`
    if (amount >= 1000) return `${(amount / 1000).toFixed(2)} K`
    return amount.toString()
  }

  const formatLPA = (amount: number) => {
    return `${(amount / 100000).toFixed(2)} LPA`
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
                <span className="text-white">Criterion 5</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 5: Student Support and Progression</h1>
              <p className="text-slate-400 mt-1">150 Marks - Scholarships, placements, career guidance, alumni engagement</p>
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
            icon={DollarSign}
            label="Scholarships"
            value={stats?.total_scholarships || 0}
            subValue={formatCurrency(stats?.total_scholarship_amount || 0)}
            color="green"
          />
          <StatCard
            icon={Briefcase}
            label="Placements"
            value={stats?.placed_students || 0}
            subValue={`Avg: ${formatLPA(stats?.average_package || 0)}`}
            color="blue"
          />
          <StatCard
            icon={Target}
            label="Career Sessions"
            value={stats?.total_career_sessions || 0}
            subValue={`${stats?.students_counseled || 0} counseled`}
            color="purple"
          />
          <StatCard
            icon={MessageSquare}
            label="Grievances"
            value={stats?.total_grievances || 0}
            subValue={`${stats?.resolved_grievances || 0} resolved`}
            color="red"
          />
          <StatCard
            icon={Users}
            label="Alumni"
            value={stats?.total_alumni || 0}
            subValue={`${stats?.active_alumni || 0} active`}
            color="orange"
          />
          <StatCard
            icon={GraduationCap}
            label="Competitive Exams"
            value={stats?.students_qualified || 0}
            subValue="Qualified"
            color="teal"
          />
        </div>

        {/* Key Indicators */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Key Indicators (150 Marks)</h2>
          <div className="grid md:grid-cols-2 gap-4">
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

        {/* Quick Actions & Placement Summary */}
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

          {/* Placement Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Placement Summary</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Briefcase className="w-5 h-5 text-blue-400" />
                  <span>Students Placed</span>
                </div>
                <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg font-semibold">
                  {stats?.placed_students || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <TrendingUp className="w-5 h-5 text-green-400" />
                  <span>Average Package</span>
                </div>
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg font-semibold">
                  {formatLPA(stats?.average_package || 0)}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Award className="w-5 h-5 text-purple-400" />
                  <span>Highest Package</span>
                </div>
                <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg font-semibold">
                  {formatLPA(stats?.highest_package || 0)}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Building2 className="w-5 h-5 text-orange-400" />
                  <span>Total Offers</span>
                </div>
                <span className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded-lg font-semibold">
                  {stats?.total_placements || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Scholarship & Grievance Stats */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Scholarship Distribution */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Scholarship Distribution</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                <DollarSign className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.government_scholarships || 0}</p>
                <p className="text-sm text-slate-400">Government</p>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center">
                <Award className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.institutional_scholarships || 0}</p>
                <p className="text-sm text-slate-400">Institutional</p>
              </div>
              <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg text-center col-span-2">
                <DollarSign className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{formatCurrency(stats?.total_scholarship_amount || 0)}</p>
                <p className="text-sm text-slate-400">Total Amount Disbursed</p>
              </div>
            </div>
          </div>

          {/* Grievance & Alumni Stats */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Support & Engagement</h2>
            <div className="space-y-4">
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Grievances Resolved</span>
                  <span className="text-2xl font-bold text-green-400">{stats?.resolved_grievances || 0}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${stats?.total_grievances ? (stats.resolved_grievances / stats.total_grievances) * 100 : 0}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-1">{stats?.pending_grievances || 0} pending</p>
              </div>
              <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Alumni Contributors</span>
                  <span className="text-2xl font-bold text-orange-400">{stats?.alumni_contributors || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  Out of {stats?.active_alumni || 0} active alumni members
                </p>
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
