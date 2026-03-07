'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Briefcase,
  ChevronRight,
  Loader2,
  Plus,
  Search,
  X,
  Building2,
  Calendar,
  MapPin,
  Clock,
  DollarSign,
  Users,
  TrendingUp,
  Award,
  CheckCircle2,
  BarChart3
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface Internship {
  id: string
  student_id: string
  student_name: string
  student_email: string | null
  department: string
  batch: string | null
  semester: number | null
  academic_year: string
  internship_type: string
  company_name: string
  company_website: string | null
  industry_sector: string | null
  location: string | null
  is_remote: boolean
  start_date: string
  end_date: string | null
  duration_weeks: number | null
  role_title: string | null
  project_title: string | null
  skills_used: string[] | null
  is_paid: boolean
  stipend_amount: number | null
  status: string
  ppo_offered: boolean
  converted_to_job: boolean
  created_at: string
}

interface Analytics {
  total_internships: number
  ongoing: number
  completed: number
  by_type: Record<string, number>
  by_department: Record<string, number>
  paid_internships: number
  ppo_offered: number
  converted_to_jobs: number
  average_duration_weeks: number
  average_stipend: number | null
  top_companies: Array<{ company: string; count: number }>
}

const INTERNSHIP_TYPES = [
  { value: 'industry', label: 'Industry', color: 'blue' },
  { value: 'research', label: 'Research', color: 'purple' },
  { value: 'government', label: 'Government', color: 'orange' },
  { value: 'ngo', label: 'NGO', color: 'green' },
  { value: 'startup', label: 'Startup', color: 'pink' },
  { value: 'international', label: 'International', color: 'teal' }
]

const STATUS_COLORS = {
  ongoing: 'bg-blue-500/10 text-blue-400',
  completed: 'bg-green-500/10 text-green-400',
  withdrawn: 'bg-red-500/10 text-red-400'
}

export default function InternshipsPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [internships, setInternships] = useState<Internship[]>([])
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [newInternship, setNewInternship] = useState({
    student_id: '',
    student_name: '',
    student_email: '',
    department: '',
    batch: '',
    semester: '',
    academic_year: '2024-25',
    internship_type: 'industry',
    company_name: '',
    company_website: '',
    industry_sector: '',
    location: '',
    is_remote: false,
    start_date: '',
    end_date: '',
    duration_weeks: '',
    role_title: '',
    project_title: '',
    project_description: '',
    skills_used: '',
    company_mentor: '',
    faculty_mentor: '',
    is_paid: false,
    stipend_amount: '',
    stipend_currency: 'INR'
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchInternships()
      fetchAnalytics()
    }
  }, [authLoading, isAuthenticated, typeFilter, statusFilter, departmentFilter])

  const fetchInternships = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (typeFilter) params.append('internship_type', typeFilter)
      if (statusFilter) params.append('status', statusFilter)
      if (departmentFilter) params.append('department', departmentFilter)
      params.append('page_size', '50')

      const response = await apiClient.get(`/accreditation/criterion1/internships?${params.toString()}`)
      setInternships(response.items || [])
    } catch (err: any) {
      console.error('Failed to fetch internships:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const fetchAnalytics = async () => {
    try {
      const response = await apiClient.get('/accreditation/criterion1/internships/analytics')
      setAnalytics(response)
    } catch (err: any) {
      console.error('Failed to fetch analytics:', err)
    }
  }

  const handleAddInternship = async () => {
    if (!newInternship.student_name || !newInternship.company_name || !newInternship.department || !newInternship.start_date) {
      setError('Please fill in required fields')
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion1/internships', {
        ...newInternship,
        semester: newInternship.semester ? parseInt(newInternship.semester) : null,
        duration_weeks: newInternship.duration_weeks ? parseInt(newInternship.duration_weeks) : null,
        stipend_amount: newInternship.stipend_amount ? parseFloat(newInternship.stipend_amount) : null,
        skills_used: newInternship.skills_used ? newInternship.skills_used.split(',').map(s => s.trim()) : null,
        end_date: newInternship.end_date || null
      })
      setShowAddModal(false)
      setNewInternship({
        student_id: '',
        student_name: '',
        student_email: '',
        department: '',
        batch: '',
        semester: '',
        academic_year: '2024-25',
        internship_type: 'industry',
        company_name: '',
        company_website: '',
        industry_sector: '',
        location: '',
        is_remote: false,
        start_date: '',
        end_date: '',
        duration_weeks: '',
        role_title: '',
        project_title: '',
        project_description: '',
        skills_used: '',
        company_mentor: '',
        faculty_mentor: '',
        is_paid: false,
        stipend_amount: '',
        stipend_currency: 'INR'
      })
      fetchInternships()
      fetchAnalytics()
    } catch (err: any) {
      console.error('Failed to add internship:', err)
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredInternships = internships.filter(i =>
    i.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    i.company_name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const departments = [...new Set(internships.map(i => i.department))]

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-600 to-teal-500 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 text-teal-100 mb-2">
            <Link href="/admin/accreditation" className="hover:text-white">NAAC</Link>
            <ChevronRight className="w-4 h-4" />
            <Link href="/admin/accreditation/criterion1" className="hover:text-white">Criterion 1</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white">Internships</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <Briefcase className="w-6 h-6" />
                Internship Tracking
              </h1>
              <p className="text-teal-100">Key Indicator 1.3 - Curriculum Enrichment</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowAnalytics(!showAnalytics)}
                className="bg-teal-700 hover:bg-teal-800 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
              >
                <BarChart3 className="w-4 h-4" />
                Analytics
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-white text-teal-600 px-4 py-2 rounded-lg font-medium hover:bg-teal-50 transition-colors flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Internship
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Analytics Panel */}
        {showAnalytics && analytics && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-teal-500" />
              Internship Analytics
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
              <div className="bg-slate-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-teal-400">{analytics.total_internships}</p>
                <p className="text-sm text-slate-400">Total</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-blue-400">{analytics.ongoing}</p>
                <p className="text-sm text-slate-400">Ongoing</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-green-400">{analytics.completed}</p>
                <p className="text-sm text-slate-400">Completed</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-yellow-400">{analytics.paid_internships}</p>
                <p className="text-sm text-slate-400">Paid</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-purple-400">{analytics.ppo_offered}</p>
                <p className="text-sm text-slate-400">PPO Offered</p>
              </div>
              <div className="bg-slate-800 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-orange-400">{analytics.converted_to_jobs}</p>
                <p className="text-sm text-slate-400">Converted</p>
              </div>
            </div>
            {analytics.top_companies.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-2">Top Companies</h3>
                <div className="flex flex-wrap gap-2">
                  {analytics.top_companies.map((company, idx) => (
                    <span key={idx} className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-sm">
                      {company.company} ({company.count})
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Stats Cards */}
        {analytics && !showAnalytics && (
          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <Briefcase className="w-8 h-8 text-teal-500" />
                <span className="text-2xl font-bold">{analytics.total_internships}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Total Internships</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <Clock className="w-8 h-8 text-blue-500" />
                <span className="text-2xl font-bold">{analytics.ongoing}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Ongoing</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <CheckCircle2 className="w-8 h-8 text-green-500" />
                <span className="text-2xl font-bold">{analytics.completed}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">Completed</p>
            </div>
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <Award className="w-8 h-8 text-purple-500" />
                <span className="text-2xl font-bold">{analytics.ppo_offered}</span>
              </div>
              <p className="text-slate-400 text-sm mt-2">PPO Offered</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by student or company..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-teal-500"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
          >
            <option value="">All Types</option>
            {INTERNSHIP_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
          >
            <option value="">All Status</option>
            <option value="ongoing">Ongoing</option>
            <option value="completed">Completed</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
          >
            <option value="">All Departments</option>
            {departments.map(dept => (
              <option key={dept} value={dept}>{dept}</option>
            ))}
          </select>
        </div>

        {/* Internships Table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-teal-500" />
          </div>
        ) : filteredInternships.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-xl">
            <Briefcase className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400">No internships found</h3>
            <p className="text-slate-500 mb-4">Start tracking student internships</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-teal-500 hover:bg-teal-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Add First Internship
            </button>
          </div>
        ) : (
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-800">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Student</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Company</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Type</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Duration</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Status</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-slate-400">Outcomes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredInternships.map((internship) => {
                  const typeInfo = INTERNSHIP_TYPES.find(t => t.value === internship.internship_type)

                  return (
                    <tr key={internship.id} className="hover:bg-slate-800/50">
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium">{internship.student_name}</p>
                          <p className="text-sm text-slate-400">{internship.department}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium">{internship.company_name}</p>
                          <p className="text-sm text-slate-400">{internship.role_title || internship.industry_sector}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`bg-${typeInfo?.color || 'slate'}-500/10 text-${typeInfo?.color || 'slate'}-400 px-2 py-1 rounded text-sm`}>
                          {typeInfo?.label || internship.internship_type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-400">
                        {internship.duration_weeks ? `${internship.duration_weeks} weeks` : 'Ongoing'}
                        {internship.is_paid && (
                          <span className="ml-2 text-green-400">Paid</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded text-sm ${STATUS_COLORS[internship.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.ongoing}`}>
                          {internship.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {internship.ppo_offered && (
                            <span className="bg-purple-500/10 text-purple-400 px-2 py-0.5 rounded text-xs">PPO</span>
                          )}
                          {internship.converted_to_job && (
                            <span className="bg-green-500/10 text-green-400 px-2 py-0.5 rounded text-xs">Hired</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Internship Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Record Internship</h2>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Student Name *</label>
                  <input
                    type="text"
                    value={newInternship.student_name}
                    onChange={(e) => setNewInternship({ ...newInternship, student_name: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Student ID</label>
                  <input
                    type="text"
                    value={newInternship.student_id}
                    onChange={(e) => setNewInternship({ ...newInternship, student_id: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                    placeholder="Roll number"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Department *</label>
                  <input
                    type="text"
                    value={newInternship.department}
                    onChange={(e) => setNewInternship({ ...newInternship, department: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Internship Type *</label>
                  <select
                    value={newInternship.internship_type}
                    onChange={(e) => setNewInternship({ ...newInternship, internship_type: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                  >
                    {INTERNSHIP_TYPES.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Company Name *</label>
                  <input
                    type="text"
                    value={newInternship.company_name}
                    onChange={(e) => setNewInternship({ ...newInternship, company_name: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Industry Sector</label>
                  <input
                    type="text"
                    value={newInternship.industry_sector}
                    onChange={(e) => setNewInternship({ ...newInternship, industry_sector: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                    placeholder="e.g., IT, Finance"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Start Date *</label>
                  <input
                    type="date"
                    value={newInternship.start_date}
                    onChange={(e) => setNewInternship({ ...newInternship, start_date: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">End Date</label>
                  <input
                    type="date"
                    value={newInternship.end_date}
                    onChange={(e) => setNewInternship({ ...newInternship, end_date: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Role Title</label>
                  <input
                    type="text"
                    value={newInternship.role_title}
                    onChange={(e) => setNewInternship({ ...newInternship, role_title: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                    placeholder="e.g., Software Developer Intern"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Location</label>
                  <input
                    type="text"
                    value={newInternship.location}
                    onChange={(e) => setNewInternship({ ...newInternship, location: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                    placeholder="City"
                  />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newInternship.is_remote}
                    onChange={(e) => setNewInternship({ ...newInternship, is_remote: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-teal-500"
                  />
                  <span className="text-sm text-slate-300">Remote</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newInternship.is_paid}
                    onChange={(e) => setNewInternship({ ...newInternship, is_paid: e.target.checked })}
                    className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-teal-500"
                  />
                  <span className="text-sm text-slate-300">Paid Internship</span>
                </label>
              </div>

              {newInternship.is_paid && (
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Stipend Amount (INR/month)</label>
                  <input
                    type="number"
                    value={newInternship.stipend_amount}
                    onChange={(e) => setNewInternship({ ...newInternship, stipend_amount: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-500"
                    min="0"
                  />
                </div>
              )}

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400">
                  {error}
                </div>
              )}
            </div>
            <div className="p-6 border-t border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAddInternship}
                disabled={isSubmitting}
                className="px-4 py-2 bg-teal-500 hover:bg-teal-600 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Record Internship
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
