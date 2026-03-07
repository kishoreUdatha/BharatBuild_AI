'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  FlaskConical,
  BookOpen,
  Lightbulb,
  Rocket,
  Trophy,
  Heart,
  Users,
  DollarSign,
  ChevronRight,
  Loader2,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Download,
  RefreshCw,
  FileText,
  Award,
  Building2,
  Handshake,
  GraduationCap
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  total_research_projects: number
  ongoing_projects: number
  completed_projects: number
  total_publications: number
  scopus_publications: number
  wos_publications: number
  total_patents: number
  filed_patents: number
  granted_patents: number
  total_startups: number
  dpiit_recognized_startups: number
  funded_startups: number
  total_innovation_cells: number
  total_hackathons: number
  hackathon_participants: number
  total_extension_activities: number
  extension_beneficiaries: number
  total_consultancies: number
  consultancy_revenue: number
  total_funding_grants: number
  total_funding_amount: number
}

const KEY_INDICATORS = [
  {
    id: '3.1',
    name: 'Resource Mobilization for Research',
    description: 'Research projects, grants, and funding from government and industry',
    icon: DollarSign,
    links: [
      { name: 'Research Projects', href: '/admin/accreditation/criterion3/research-projects' },
      { name: 'Research Funding', href: '/admin/accreditation/criterion3/research-funding' }
    ],
    color: 'green'
  },
  {
    id: '3.2',
    name: 'Innovation Ecosystem',
    description: 'Patents, startups, incubation, IIC/EDC activities',
    icon: Lightbulb,
    links: [
      { name: 'Patents', href: '/admin/accreditation/criterion3/patents' },
      { name: 'Startups', href: '/admin/accreditation/criterion3/startups' },
      { name: 'Innovation Cells', href: '/admin/accreditation/criterion3/innovation-cells' },
      { name: 'Hackathons', href: '/admin/accreditation/criterion3/hackathons' }
    ],
    color: 'purple'
  },
  {
    id: '3.3',
    name: 'Research Publications',
    description: 'Journals, conferences, books indexed in Scopus/WoS/UGC CARE',
    icon: BookOpen,
    links: [
      { name: 'Publications', href: '/admin/accreditation/criterion3/publications' }
    ],
    color: 'blue'
  },
  {
    id: '3.4',
    name: 'Extension Activities',
    description: 'NSS, NCC, community outreach, social responsibility',
    icon: Heart,
    links: [
      { name: 'Extension Activities', href: '/admin/accreditation/criterion3/extension-activities' }
    ],
    color: 'red'
  },
  {
    id: '3.5',
    name: 'Collaboration',
    description: 'Industry consultancy, MoUs, collaborative research',
    icon: Handshake,
    links: [
      { name: 'Consultancies', href: '/admin/accreditation/criterion3/consultancies' }
    ],
    color: 'orange'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Project', icon: FlaskConical, href: '/admin/accreditation/criterion3/research-projects', color: 'green' },
  { name: 'Add Publication', icon: BookOpen, href: '/admin/accreditation/criterion3/publications', color: 'blue' },
  { name: 'Add Patent', icon: Award, href: '/admin/accreditation/criterion3/patents', color: 'purple' },
  { name: 'Add Startup', icon: Rocket, href: '/admin/accreditation/criterion3/startups', color: 'orange' },
  { name: 'Add Hackathon', icon: Trophy, href: '/admin/accreditation/criterion3/hackathons', color: 'yellow' },
  { name: 'Add Extension', icon: Heart, href: '/admin/accreditation/criterion3/extension-activities', color: 'red' }
]

const FUNDING_AGENCIES = [
  { id: 'dst', label: 'DST', color: '#22c55e' },
  { id: 'dbt', label: 'DBT', color: '#3b82f6' },
  { id: 'serb', label: 'SERB', color: '#8b5cf6' },
  { id: 'csir', label: 'CSIR', color: '#f59e0b' },
  { id: 'ugc', label: 'UGC', color: '#ef4444' },
  { id: 'aicte', label: 'AICTE', color: '#06b6d4' }
]

export default function Criterion3DashboardPage() {
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
      const response = await apiClient.get(`/accreditation/criterion3/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      // Set default stats for demo
      setStats({
        total_research_projects: 0,
        ongoing_projects: 0,
        completed_projects: 0,
        total_publications: 0,
        scopus_publications: 0,
        wos_publications: 0,
        total_patents: 0,
        filed_patents: 0,
        granted_patents: 0,
        total_startups: 0,
        dpiit_recognized_startups: 0,
        funded_startups: 0,
        total_innovation_cells: 0,
        total_hackathons: 0,
        hackathon_participants: 0,
        total_extension_activities: 0,
        extension_beneficiaries: 0,
        total_consultancies: 0,
        consultancy_revenue: 0,
        total_funding_grants: 0,
        total_funding_amount: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await apiClient.post('/accreditation/criterion3/generate-report', {
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
                <span className="text-white">Criterion 3</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 3: Research, Innovations and Extension</h1>
              <p className="text-slate-400 mt-1">150 Marks - Promoting research culture, innovation ecosystem, and community engagement</p>
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
            icon={FlaskConical}
            label="Research Projects"
            value={stats?.total_research_projects || 0}
            subValue={`${stats?.ongoing_projects || 0} ongoing`}
            color="green"
          />
          <StatCard
            icon={BookOpen}
            label="Publications"
            value={stats?.total_publications || 0}
            subValue={`${stats?.scopus_publications || 0} Scopus`}
            color="blue"
          />
          <StatCard
            icon={Award}
            label="Patents"
            value={stats?.total_patents || 0}
            subValue={`${stats?.granted_patents || 0} granted`}
            color="purple"
          />
          <StatCard
            icon={Rocket}
            label="Startups"
            value={stats?.total_startups || 0}
            subValue={`${stats?.dpiit_recognized_startups || 0} DPIIT`}
            color="orange"
          />
          <StatCard
            icon={Heart}
            label="Extension Activities"
            value={stats?.total_extension_activities || 0}
            subValue={`${stats?.extension_beneficiaries || 0} beneficiaries`}
            color="red"
          />
          <StatCard
            icon={DollarSign}
            label="Research Funding"
            value={formatCurrency(stats?.total_funding_amount || 0)}
            subValue={`${stats?.total_funding_grants || 0} grants`}
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

        {/* Quick Actions & Research Output */}
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

          {/* Research Output Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Research Output Summary</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <BookOpen className="w-5 h-5 text-blue-400" />
                  <span>Scopus Indexed</span>
                </div>
                <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg font-semibold">
                  {stats?.scopus_publications || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <BookOpen className="w-5 h-5 text-purple-400" />
                  <span>Web of Science</span>
                </div>
                <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg font-semibold">
                  {stats?.wos_publications || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Award className="w-5 h-5 text-green-400" />
                  <span>Patents Filed</span>
                </div>
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg font-semibold">
                  {stats?.filed_patents || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Award className="w-5 h-5 text-orange-400" />
                  <span>Patents Granted</span>
                </div>
                <span className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded-lg font-semibold">
                  {stats?.granted_patents || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Innovation & Extension Stats */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Innovation Ecosystem */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Innovation Ecosystem</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg text-center">
                <Lightbulb className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_innovation_cells || 0}</p>
                <p className="text-sm text-slate-400">Innovation Cells</p>
              </div>
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg text-center">
                <Trophy className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_hackathons || 0}</p>
                <p className="text-sm text-slate-400">Hackathons</p>
              </div>
              <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg text-center">
                <Rocket className="w-6 h-6 text-orange-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_startups || 0}</p>
                <p className="text-sm text-slate-400">Startups Incubated</p>
              </div>
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                <Users className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.hackathon_participants || 0}</p>
                <p className="text-sm text-slate-400">Event Participants</p>
              </div>
            </div>
          </div>

          {/* Extension & Consultancy */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Extension & Consultancy</h2>
            <div className="space-y-4">
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Extension Activities</span>
                  <span className="text-2xl font-bold text-red-400">{stats?.total_extension_activities || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  {stats?.extension_beneficiaries || 0} total beneficiaries reached
                </p>
              </div>
              <div className="p-4 bg-teal-500/10 border border-teal-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Consultancy Projects</span>
                  <span className="text-2xl font-bold text-teal-400">{stats?.total_consultancies || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  {formatCurrency(stats?.consultancy_revenue || 0)} total revenue generated
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
