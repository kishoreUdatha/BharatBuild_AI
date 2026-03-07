'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Leaf,
  Heart,
  Users,
  Shield,
  Award,
  Star,
  ChevronRight,
  Loader2,
  AlertCircle,
  Download,
  RefreshCw,
  Recycle,
  Droplets,
  Sun,
  TreePine,
  Scale,
  Globe,
  Trophy,
  Sparkles
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  total_gender_equity_programs: number
  participants_gender_equity: number
  total_green_initiatives: number
  solar_initiatives: number
  water_conservation: number
  trees_planted: number
  carbon_reduced_kg: number
  total_inclusivity_programs: number
  beneficiaries_inclusivity: number
  total_ethics_programs: number
  participants_ethics: number
  cases_resolved: number
  total_best_practices: number
  featured_practices: number
  total_distinctiveness: number
  total_awards: number
  national_awards: number
  state_awards: number
}

const KEY_INDICATORS = [
  {
    id: '7.1',
    name: 'Institutional Values & Social Responsibilities',
    description: 'Gender equity, environment consciousness, inclusivity, and ethics',
    icon: Heart,
    links: [
      { name: 'Gender Equity', href: '/admin/accreditation/criterion7/gender-equity' },
      { name: 'Green Initiatives', href: '/admin/accreditation/criterion7/green-initiatives' },
      { name: 'Inclusivity', href: '/admin/accreditation/criterion7/inclusivity' },
      { name: 'Ethics', href: '/admin/accreditation/criterion7/ethics' }
    ],
    color: 'green'
  },
  {
    id: '7.2',
    name: 'Best Practices',
    description: 'Two best practices demonstrating institutional excellence',
    icon: Star,
    links: [
      { name: 'Best Practices', href: '/admin/accreditation/criterion7/best-practices' }
    ],
    color: 'purple'
  },
  {
    id: '7.3',
    name: 'Institutional Distinctiveness',
    description: 'Unique features that distinguish the institution',
    icon: Sparkles,
    links: [
      { name: 'Distinctiveness', href: '/admin/accreditation/criterion7/distinctiveness' }
    ],
    color: 'blue'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Gender Program', icon: Users, href: '/admin/accreditation/criterion7/gender-equity', color: 'pink' },
  { name: 'Add Green Initiative', icon: Leaf, href: '/admin/accreditation/criterion7/green-initiatives', color: 'green' },
  { name: 'Add Inclusivity', icon: Heart, href: '/admin/accreditation/criterion7/inclusivity', color: 'purple' },
  { name: 'Add Ethics Program', icon: Shield, href: '/admin/accreditation/criterion7/ethics', color: 'blue' },
  { name: 'Add Best Practice', icon: Star, href: '/admin/accreditation/criterion7/best-practices', color: 'yellow' },
  { name: 'Add Award', icon: Trophy, href: '/admin/accreditation/criterion7/awards', color: 'orange' }
]

export default function Criterion7DashboardPage() {
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
      const response = await apiClient.get(`/accreditation/criterion7/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      setStats({
        total_gender_equity_programs: 0,
        participants_gender_equity: 0,
        total_green_initiatives: 0,
        solar_initiatives: 0,
        water_conservation: 0,
        trees_planted: 0,
        carbon_reduced_kg: 0,
        total_inclusivity_programs: 0,
        beneficiaries_inclusivity: 0,
        total_ethics_programs: 0,
        participants_ethics: 0,
        cases_resolved: 0,
        total_best_practices: 0,
        featured_practices: 0,
        total_distinctiveness: 0,
        total_awards: 0,
        national_awards: 0,
        state_awards: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await apiClient.post('/accreditation/criterion7/generate-report', {
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
      teal: { bg: 'bg-teal-500/10', border: 'border-teal-500/30', text: 'text-teal-400', icon: 'text-teal-500' },
      pink: { bg: 'bg-pink-500/10', border: 'border-pink-500/30', text: 'text-pink-400', icon: 'text-pink-500' }
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
                <span className="text-white">Criterion 7</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 7: Institutional Values and Best Practices</h1>
              <p className="text-slate-400 mt-1">100 Marks - Values, environment, inclusivity, best practices, and distinctiveness</p>
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
            icon={Users}
            label="Gender Equity"
            value={stats?.total_gender_equity_programs || 0}
            subValue={`${stats?.participants_gender_equity || 0} participants`}
            color="pink"
          />
          <StatCard
            icon={Leaf}
            label="Green Initiatives"
            value={stats?.total_green_initiatives || 0}
            subValue={`${stats?.trees_planted || 0} trees planted`}
            color="green"
          />
          <StatCard
            icon={Heart}
            label="Inclusivity"
            value={stats?.total_inclusivity_programs || 0}
            subValue={`${stats?.beneficiaries_inclusivity || 0} beneficiaries`}
            color="purple"
          />
          <StatCard
            icon={Shield}
            label="Ethics Programs"
            value={stats?.total_ethics_programs || 0}
            subValue={`${stats?.cases_resolved || 0} cases resolved`}
            color="blue"
          />
          <StatCard
            icon={Star}
            label="Best Practices"
            value={stats?.total_best_practices || 0}
            subValue={`${stats?.featured_practices || 0} featured`}
            color="yellow"
          />
          <StatCard
            icon={Trophy}
            label="Awards"
            value={stats?.total_awards || 0}
            subValue={`${stats?.national_awards || 0} national`}
            color="orange"
          />
        </div>

        {/* Key Indicators */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">Key Indicators (100 Marks)</h2>
          <div className="grid md:grid-cols-3 gap-4">
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

        {/* Quick Actions & Green Initiatives Summary */}
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

          {/* Green Initiatives Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Environmental Sustainability</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Sun className="w-5 h-5 text-yellow-400" />
                  <span>Solar Initiatives</span>
                </div>
                <span className="px-3 py-1 bg-yellow-500/20 text-yellow-400 rounded-lg font-semibold">
                  {stats?.solar_initiatives || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Droplets className="w-5 h-5 text-blue-400" />
                  <span>Water Conservation</span>
                </div>
                <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg font-semibold">
                  {stats?.water_conservation || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <TreePine className="w-5 h-5 text-green-400" />
                  <span>Trees Planted</span>
                </div>
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg font-semibold">
                  {stats?.trees_planted || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Recycle className="w-5 h-5 text-teal-400" />
                  <span>Carbon Reduced</span>
                </div>
                <span className="px-3 py-1 bg-teal-500/20 text-teal-400 rounded-lg font-semibold">
                  {stats?.carbon_reduced_kg || 0} kg
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Values & Awards */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Institutional Values */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Institutional Values</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-pink-500/10 border border-pink-500/30 rounded-lg text-center">
                <Users className="w-6 h-6 text-pink-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_gender_equity_programs || 0}</p>
                <p className="text-sm text-slate-400">Gender Programs</p>
              </div>
              <div className="p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg text-center">
                <Heart className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_inclusivity_programs || 0}</p>
                <p className="text-sm text-slate-400">Inclusivity</p>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center">
                <Shield className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_ethics_programs || 0}</p>
                <p className="text-sm text-slate-400">Ethics</p>
              </div>
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                <Leaf className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.total_green_initiatives || 0}</p>
                <p className="text-sm text-slate-400">Green Initiatives</p>
              </div>
            </div>
          </div>

          {/* Awards & Recognition */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Awards & Recognition</h2>
            <div className="space-y-4">
              <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">National Awards</span>
                  <span className="text-2xl font-bold text-orange-400">{stats?.national_awards || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  Recognition at national level
                </p>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">State Awards</span>
                  <span className="text-2xl font-bold text-blue-400">{stats?.state_awards || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  Recognition at state level
                </p>
              </div>
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Best Practices</span>
                  <span className="text-2xl font-bold text-yellow-400">{stats?.featured_practices || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  Featured institutional practices
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
    teal: 'text-teal-400',
    pink: 'text-pink-400'
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
