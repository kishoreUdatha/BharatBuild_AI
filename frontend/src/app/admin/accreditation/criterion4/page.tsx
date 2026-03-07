'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Building2,
  Monitor,
  Server,
  BookOpen,
  Wrench,
  Wifi,
  ChevronRight,
  Loader2,
  AlertCircle,
  Download,
  RefreshCw,
  Laptop,
  Library,
  HardDrive,
  Clock,
  Activity,
  Settings
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'

interface DashboardStats {
  total_infrastructure: number
  smart_classrooms: number
  computer_labs: number
  total_lab_equipment: number
  working_equipment: number
  equipment_utilization: number
  total_software_licenses: number
  active_licenses: number
  expired_licenses: number
  total_library_resources: number
  e_resources: number
  physical_books: number
  total_maintenance_records: number
  pending_maintenance: number
  completed_maintenance: number
  avg_lab_utilization: number
  total_e_resource_access: number
  monthly_access_count: number
}

const KEY_INDICATORS = [
  {
    id: '4.1',
    name: 'Physical Facilities',
    description: 'Classrooms, laboratories, computing equipment, and infrastructure',
    icon: Building2,
    links: [
      { name: 'Infrastructure', href: '/admin/accreditation/criterion4/infrastructure' },
      { name: 'Labs & Classrooms', href: '/admin/accreditation/criterion4/labs' }
    ],
    color: 'blue'
  },
  {
    id: '4.2',
    name: 'Library as Learning Resource',
    description: 'Library resources, e-journals, digital library, OPAC',
    icon: Library,
    links: [
      { name: 'Library Resources', href: '/admin/accreditation/criterion4/library' },
      { name: 'E-Resources', href: '/admin/accreditation/criterion4/e-resources' }
    ],
    color: 'purple'
  },
  {
    id: '4.3',
    name: 'IT Infrastructure',
    description: 'Computing facilities, internet bandwidth, software, LMS',
    icon: Server,
    links: [
      { name: 'Lab Equipment', href: '/admin/accreditation/criterion4/equipment' },
      { name: 'Software Licenses', href: '/admin/accreditation/criterion4/software' }
    ],
    color: 'green'
  },
  {
    id: '4.4',
    name: 'Maintenance of Infrastructure',
    description: 'Maintenance systems, budget allocation, AMC coverage',
    icon: Wrench,
    links: [
      { name: 'Maintenance Records', href: '/admin/accreditation/criterion4/maintenance' },
      { name: 'Utilization Reports', href: '/admin/accreditation/criterion4/utilization' }
    ],
    color: 'orange'
  }
]

const QUICK_ACTIONS = [
  { name: 'Add Infrastructure', icon: Building2, href: '/admin/accreditation/criterion4/infrastructure', color: 'blue' },
  { name: 'Add Equipment', icon: HardDrive, href: '/admin/accreditation/criterion4/equipment', color: 'green' },
  { name: 'Add Software', icon: Laptop, href: '/admin/accreditation/criterion4/software', color: 'purple' },
  { name: 'Add Library Resource', icon: BookOpen, href: '/admin/accreditation/criterion4/library', color: 'teal' },
  { name: 'Log Maintenance', icon: Wrench, href: '/admin/accreditation/criterion4/maintenance', color: 'orange' },
  { name: 'Lab Utilization', icon: Activity, href: '/admin/accreditation/criterion4/utilization', color: 'yellow' }
]

export default function Criterion4DashboardPage() {
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
      const response = await apiClient.get(`/accreditation/criterion4/dashboard?academic_year=${academicYear}`)
      setStats(response)
    } catch (err: any) {
      console.error('Failed to fetch dashboard stats:', err)
      setError(err.message || 'Failed to load dashboard')
      setStats({
        total_infrastructure: 0,
        smart_classrooms: 0,
        computer_labs: 0,
        total_lab_equipment: 0,
        working_equipment: 0,
        equipment_utilization: 0,
        total_software_licenses: 0,
        active_licenses: 0,
        expired_licenses: 0,
        total_library_resources: 0,
        e_resources: 0,
        physical_books: 0,
        total_maintenance_records: 0,
        pending_maintenance: 0,
        completed_maintenance: 0,
        avg_lab_utilization: 0,
        total_e_resource_access: 0,
        monthly_access_count: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    try {
      const response = await apiClient.post('/accreditation/criterion4/generate-report', {
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
                <span className="text-white">Criterion 4</span>
              </div>
              <h1 className="text-2xl font-bold">Criterion 4: Infrastructure and Learning Resources</h1>
              <p className="text-slate-400 mt-1">150 Marks - Physical facilities, IT infrastructure, library resources, and maintenance</p>
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
            icon={Building2}
            label="Infrastructure"
            value={stats?.total_infrastructure || 0}
            subValue={`${stats?.smart_classrooms || 0} smart rooms`}
            color="blue"
          />
          <StatCard
            icon={HardDrive}
            label="Lab Equipment"
            value={stats?.total_lab_equipment || 0}
            subValue={`${stats?.working_equipment || 0} working`}
            color="green"
          />
          <StatCard
            icon={Laptop}
            label="Software Licenses"
            value={stats?.total_software_licenses || 0}
            subValue={`${stats?.active_licenses || 0} active`}
            color="purple"
          />
          <StatCard
            icon={Library}
            label="Library Resources"
            value={stats?.total_library_resources || 0}
            subValue={`${stats?.e_resources || 0} e-resources`}
            color="teal"
          />
          <StatCard
            icon={Wrench}
            label="Maintenance"
            value={stats?.total_maintenance_records || 0}
            subValue={`${stats?.pending_maintenance || 0} pending`}
            color="orange"
          />
          <StatCard
            icon={Activity}
            label="Lab Utilization"
            value={`${stats?.avg_lab_utilization || 0}%`}
            subValue="Average"
            color="yellow"
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

        {/* Quick Actions & Infrastructure Summary */}
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

          {/* Infrastructure Summary */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Infrastructure Summary</h2>
            <div className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Monitor className="w-5 h-5 text-blue-400" />
                  <span>Smart Classrooms</span>
                </div>
                <span className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg font-semibold">
                  {stats?.smart_classrooms || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Server className="w-5 h-5 text-green-400" />
                  <span>Computer Labs</span>
                </div>
                <span className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg font-semibold">
                  {stats?.computer_labs || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Wifi className="w-5 h-5 text-purple-400" />
                  <span>E-Resource Access</span>
                </div>
                <span className="px-3 py-1 bg-purple-500/20 text-purple-400 rounded-lg font-semibold">
                  {stats?.total_e_resource_access || 0}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <Clock className="w-5 h-5 text-orange-400" />
                  <span>Monthly Access</span>
                </div>
                <span className="px-3 py-1 bg-orange-500/20 text-orange-400 rounded-lg font-semibold">
                  {stats?.monthly_access_count || 0}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Equipment & License Status */}
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Equipment Status */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Equipment Status</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg text-center">
                <HardDrive className="w-6 h-6 text-green-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.working_equipment || 0}</p>
                <p className="text-sm text-slate-400">Working</p>
              </div>
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-center">
                <Settings className="w-6 h-6 text-red-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{(stats?.total_lab_equipment || 0) - (stats?.working_equipment || 0)}</p>
                <p className="text-sm text-slate-400">Under Repair</p>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg text-center">
                <Activity className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.equipment_utilization || 0}%</p>
                <p className="text-sm text-slate-400">Utilization</p>
              </div>
              <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg text-center">
                <Wrench className="w-6 h-6 text-orange-400 mx-auto mb-2" />
                <p className="text-2xl font-bold">{stats?.pending_maintenance || 0}</p>
                <p className="text-sm text-slate-400">Pending Maint.</p>
              </div>
            </div>
          </div>

          {/* License Status */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h2 className="text-lg font-semibold mb-4">Software License Status</h2>
            <div className="space-y-4">
              <div className="p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Active Licenses</span>
                  <span className="text-2xl font-bold text-green-400">{stats?.active_licenses || 0}</span>
                </div>
                <div className="w-full bg-slate-700 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${stats?.total_software_licenses ? (stats.active_licenses / stats.total_software_licenses) * 100 : 0}%` }}
                  />
                </div>
              </div>
              <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium">Expired Licenses</span>
                  <span className="text-2xl font-bold text-red-400">{stats?.expired_licenses || 0}</span>
                </div>
                <p className="text-sm text-slate-400">
                  Requires immediate renewal attention
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
