'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  FlaskConical,
  Plus,
  Search,
  Filter,
  ChevronRight,
  Loader2,
  Edit,
  Trash2,
  Eye,
  Calendar,
  User,
  Building2,
  DollarSign,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface ResearchProject {
  id: string
  title: string
  project_type: string
  description: string
  department: string
  domain: string
  start_date: string
  end_date: string
  academic_year: string
  status: string
  principal_investigator: string
  pi_email: string
  funding_agency: string
  funding_agency_name: string
  sanctioned_amount: number
  received_amount: number
  grant_number: string
  created_at: string
}

const PROJECT_TYPES = [
  { value: 'student', label: 'Student Project' },
  { value: 'faculty', label: 'Faculty Project' },
  { value: 'collaborative', label: 'Collaborative' },
  { value: 'sponsored', label: 'Sponsored' },
  { value: 'consultancy', label: 'Consultancy' }
]

const PROJECT_STATUS = [
  { value: 'proposed', label: 'Proposed', color: 'gray' },
  { value: 'ongoing', label: 'Ongoing', color: 'blue' },
  { value: 'completed', label: 'Completed', color: 'green' },
  { value: 'extended', label: 'Extended', color: 'orange' },
  { value: 'terminated', label: 'Terminated', color: 'red' }
]

const FUNDING_AGENCIES = [
  { value: 'dst', label: 'DST' },
  { value: 'dbt', label: 'DBT' },
  { value: 'serb', label: 'SERB' },
  { value: 'csir', label: 'CSIR' },
  { value: 'ugc', label: 'UGC' },
  { value: 'aicte', label: 'AICTE' },
  { value: 'icmr', label: 'ICMR' },
  { value: 'drdo', label: 'DRDO' },
  { value: 'isro', label: 'ISRO' },
  { value: 'industry', label: 'Industry' },
  { value: 'international', label: 'International' },
  { value: 'other', label: 'Other' }
]

export default function ResearchProjectsPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [projects, setProjects] = useState<ResearchProject[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterDepartment, setFilterDepartment] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingProject, setEditingProject] = useState<ResearchProject | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    project_type: 'faculty',
    description: '',
    department: '',
    domain: '',
    start_date: '',
    end_date: '',
    academic_year: '2024-25',
    status: 'proposed',
    principal_investigator: '',
    pi_designation: '',
    pi_email: '',
    funding_agency: '',
    funding_agency_name: '',
    sanctioned_amount: 0,
    received_amount: 0,
    grant_number: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchProjects()
    }
  }, [authLoading, isAuthenticated, filterType, filterStatus, filterDepartment])

  const fetchProjects = async () => {
    setIsLoading(true)
    try {
      let url = '/accreditation/criterion3/research-projects?limit=100'
      if (filterType) url += `&project_type=${filterType}`
      if (filterStatus) url += `&status=${filterStatus}`
      if (filterDepartment) url += `&department=${filterDepartment}`

      const response = await apiClient.get(url)
      setProjects(response.projects || [])
    } catch (err: any) {
      console.error('Failed to fetch projects:', err)
      setError(err.message || 'Failed to load projects')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      if (editingProject) {
        await apiClient.put(`/accreditation/criterion3/research-projects/${editingProject.id}`, formData)
      } else {
        await apiClient.post('/accreditation/criterion3/research-projects', formData)
      }
      setShowAddModal(false)
      setEditingProject(null)
      resetForm()
      fetchProjects()
    } catch (err: any) {
      setError(err.message || 'Failed to save project')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this project?')) return
    try {
      await apiClient.delete(`/accreditation/criterion3/research-projects/${id}`)
      fetchProjects()
    } catch (err: any) {
      setError(err.message || 'Failed to delete project')
    }
  }

  const handleEdit = (project: ResearchProject) => {
    setEditingProject(project)
    setFormData({
      title: project.title,
      project_type: project.project_type,
      description: project.description || '',
      department: project.department,
      domain: project.domain || '',
      start_date: project.start_date,
      end_date: project.end_date || '',
      academic_year: project.academic_year,
      status: project.status,
      principal_investigator: project.principal_investigator,
      pi_designation: '',
      pi_email: project.pi_email || '',
      funding_agency: project.funding_agency || '',
      funding_agency_name: project.funding_agency_name || '',
      sanctioned_amount: project.sanctioned_amount || 0,
      received_amount: project.received_amount || 0,
      grant_number: project.grant_number || ''
    })
    setShowAddModal(true)
  }

  const resetForm = () => {
    setFormData({
      title: '',
      project_type: 'faculty',
      description: '',
      department: '',
      domain: '',
      start_date: '',
      end_date: '',
      academic_year: '2024-25',
      status: 'proposed',
      principal_investigator: '',
      pi_designation: '',
      pi_email: '',
      funding_agency: '',
      funding_agency_name: '',
      sanctioned_amount: 0,
      received_amount: 0,
      grant_number: ''
    })
  }

  const getStatusColor = (status: string) => {
    const statusInfo = PROJECT_STATUS.find(s => s.value === status)
    const colors: Record<string, string> = {
      gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30',
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      green: 'bg-green-500/20 text-green-400 border-green-500/30',
      orange: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      red: 'bg-red-500/20 text-red-400 border-red-500/30'
    }
    return colors[statusInfo?.color || 'gray']
  }

  const formatCurrency = (amount: number) => {
    if (amount >= 10000000) return `${(amount / 10000000).toFixed(2)} Cr`
    if (amount >= 100000) return `${(amount / 100000).toFixed(2)} L`
    return `${amount.toLocaleString()}`
  }

  const filteredProjects = projects.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.principal_investigator.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.department.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                <Link href="/admin/accreditation" className="hover:text-white">Accreditation</Link>
                <ChevronRight className="w-4 h-4" />
                <Link href="/admin/accreditation/criterion3" className="hover:text-white">Criterion 3</Link>
                <ChevronRight className="w-4 h-4" />
                <span className="text-white">Research Projects</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <FlaskConical className="w-7 h-7 text-green-500" />
                Research Projects
              </h1>
              <p className="text-slate-400 mt-1">Manage student and faculty research projects</p>
            </div>
            <button
              onClick={() => { resetForm(); setEditingProject(null); setShowAddModal(true) }}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add Project
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-400">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex-1 min-w-64 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-slate-400"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Types</option>
            {PROJECT_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Status</option>
            {PROJECT_STATUS.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* Projects Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <div key={project.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <span className={`px-2 py-1 text-xs rounded border ${getStatusColor(project.status)}`}>
                  {PROJECT_STATUS.find(s => s.value === project.status)?.label}
                </span>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleEdit(project)}
                    className="p-1.5 hover:bg-slate-800 rounded"
                  >
                    <Edit className="w-4 h-4 text-slate-400" />
                  </button>
                  <button
                    onClick={() => handleDelete(project.id)}
                    className="p-1.5 hover:bg-slate-800 rounded"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>

              <h3 className="font-semibold mb-2 line-clamp-2">{project.title}</h3>

              <div className="space-y-2 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4" />
                  <span>{project.principal_investigator}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  <span>{project.department}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span>{project.start_date} - {project.end_date || 'Ongoing'}</span>
                </div>
                {project.sanctioned_amount > 0 && (
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-green-400" />
                    <span className="text-green-400">{formatCurrency(project.sanctioned_amount)}</span>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-slate-800 flex items-center justify-between">
                <span className="text-xs px-2 py-1 bg-slate-800 rounded">
                  {PROJECT_TYPES.find(t => t.value === project.project_type)?.label}
                </span>
                {project.funding_agency && (
                  <span className="text-xs text-blue-400">
                    {FUNDING_AGENCIES.find(a => a.value === project.funding_agency)?.label || project.funding_agency_name}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {filteredProjects.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <FlaskConical className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No research projects found</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-4 text-green-400 hover:text-green-300"
            >
              Add your first project
            </button>
          </div>
        )}
      </div>

      {/* Add/Edit Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-xl font-semibold">
                {editingProject ? 'Edit Research Project' : 'Add Research Project'}
              </h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Project Title *</label>
                <input
                  type="text"
                  required
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Project Type *</label>
                  <select
                    required
                    value={formData.project_type}
                    onChange={(e) => setFormData({ ...formData, project_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    {PROJECT_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Status *</label>
                  <select
                    required
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    {PROJECT_STATUS.map(s => (
                      <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Department *</label>
                  <input
                    type="text"
                    required
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Domain</label>
                  <input
                    type="text"
                    value={formData.domain}
                    onChange={(e) => setFormData({ ...formData, domain: e.target.value })}
                    placeholder="AI, IoT, Healthcare..."
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Start Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.start_date}
                    onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">End Date</label>
                  <input
                    type="date"
                    value={formData.end_date}
                    onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Academic Year *</label>
                  <input
                    type="text"
                    required
                    value={formData.academic_year}
                    onChange={(e) => setFormData({ ...formData, academic_year: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Principal Investigator *</label>
                  <input
                    type="text"
                    required
                    value={formData.principal_investigator}
                    onChange={(e) => setFormData({ ...formData, principal_investigator: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">PI Email</label>
                  <input
                    type="email"
                    value={formData.pi_email}
                    onChange={(e) => setFormData({ ...formData, pi_email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Funding Agency</label>
                  <select
                    value={formData.funding_agency}
                    onChange={(e) => setFormData({ ...formData, funding_agency: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    <option value="">Select Agency</option>
                    {FUNDING_AGENCIES.map(a => (
                      <option key={a.value} value={a.value}>{a.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Grant Number</label>
                  <input
                    type="text"
                    value={formData.grant_number}
                    onChange={(e) => setFormData({ ...formData, grant_number: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Sanctioned Amount</label>
                  <input
                    type="number"
                    value={formData.sanctioned_amount}
                    onChange={(e) => setFormData({ ...formData, sanctioned_amount: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Received Amount</label>
                  <input
                    type="number"
                    value={formData.received_amount}
                    onChange={(e) => setFormData({ ...formData, received_amount: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => { setShowAddModal(false); setEditingProject(null) }}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : (editingProject ? 'Update' : 'Create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
