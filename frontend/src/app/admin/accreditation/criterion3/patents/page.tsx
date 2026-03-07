'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Award,
  Plus,
  Search,
  ChevronRight,
  Loader2,
  Edit,
  Trash2,
  Calendar,
  User,
  Building2,
  XCircle,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface Patent {
  id: string
  title: string
  patent_type: string
  status: string
  application_number: string
  patent_number: string
  filing_date: string
  filing_year: number
  grant_date: string
  inventors: any[]
  applicant: string
  department: string
  technology_area: string
  is_commercialized: boolean
  created_at: string
}

const PATENT_TYPES = [
  { value: 'indian', label: 'Indian Patent' },
  { value: 'international', label: 'International' },
  { value: 'us', label: 'US Patent' },
  { value: 'european', label: 'European Patent' },
  { value: 'pct', label: 'PCT' }
]

const PATENT_STATUS = [
  { value: 'filed', label: 'Filed', color: 'blue', icon: FileText },
  { value: 'published', label: 'Published', color: 'purple', icon: Clock },
  { value: 'granted', label: 'Granted', color: 'green', icon: CheckCircle },
  { value: 'rejected', label: 'Rejected', color: 'red', icon: XCircle },
  { value: 'abandoned', label: 'Abandoned', color: 'gray', icon: XCircle }
]

export default function PatentsPage() {
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [patents, setPatents] = useState<Patent[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [formData, setFormData] = useState({
    title: '',
    patent_type: 'indian',
    status: 'filed',
    description: '',
    application_number: '',
    filing_date: '',
    filing_year: new Date().getFullYear(),
    inventors: [{ name: '', designation: '', department: '' }],
    applicant: '',
    department: '',
    ipc_class: '',
    technology_area: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchPatents()
    }
  }, [authLoading, isAuthenticated, filterType, filterStatus])

  const fetchPatents = async () => {
    setIsLoading(true)
    try {
      let url = '/accreditation/criterion3/patents?limit=100'
      if (filterType) url += `&patent_type=${filterType}`
      if (filterStatus) url += `&status=${filterStatus}`

      const response = await apiClient.get(url)
      setPatents(response.patents || [])
    } catch (err: any) {
      console.error('Failed to fetch patents:', err)
      setError(err.message || 'Failed to load patents')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion3/patents', formData)
      setShowAddModal(false)
      resetForm()
      fetchPatents()
    } catch (err: any) {
      setError(err.message || 'Failed to save patent')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this patent?')) return
    try {
      await apiClient.delete(`/accreditation/criterion3/patents/${id}`)
      fetchPatents()
    } catch (err: any) {
      setError(err.message || 'Failed to delete patent')
    }
  }

  const resetForm = () => {
    setFormData({
      title: '',
      patent_type: 'indian',
      status: 'filed',
      description: '',
      application_number: '',
      filing_date: '',
      filing_year: new Date().getFullYear(),
      inventors: [{ name: '', designation: '', department: '' }],
      applicant: '',
      department: '',
      ipc_class: '',
      technology_area: ''
    })
  }

  const getStatusColor = (status: string) => {
    const info = PATENT_STATUS.find(s => s.value === status)
    const colors: Record<string, string> = {
      blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      green: 'bg-green-500/20 text-green-400 border-green-500/30',
      red: 'bg-red-500/20 text-red-400 border-red-500/30',
      gray: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
    return colors[info?.color || 'gray']
  }

  const addInventor = () => {
    setFormData({
      ...formData,
      inventors: [...formData.inventors, { name: '', designation: '', department: '' }]
    })
  }

  const filteredPatents = patents.filter(p =>
    p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
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
                <span className="text-white">Patents</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <Award className="w-7 h-7 text-purple-500" />
                Patents
              </h1>
              <p className="text-slate-400 mt-1">Track patent filings and grants</p>
            </div>
            <button
              onClick={() => { resetForm(); setShowAddModal(true) }}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add Patent
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-500" />
            <span className="text-red-400">{error}</span>
            <button onClick={() => setError(null)} className="ml-auto">
              <XCircle className="w-5 h-5 text-red-400" />
            </button>
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex-1 min-w-64 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search patents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Types</option>
            {PATENT_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
          >
            <option value="">All Status</option>
            {PATENT_STATUS.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>

        {/* Patents Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPatents.map((patent) => (
            <div key={patent.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <span className={`px-2 py-1 text-xs rounded border ${getStatusColor(patent.status)}`}>
                  {PATENT_STATUS.find(s => s.value === patent.status)?.label}
                </span>
                <button onClick={() => handleDelete(patent.id)} className="p-1.5 hover:bg-slate-800 rounded">
                  <Trash2 className="w-4 h-4 text-red-400" />
                </button>
              </div>

              <h3 className="font-semibold mb-2 line-clamp-2">{patent.title}</h3>

              <div className="space-y-2 text-sm text-slate-400">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  <span>{patent.application_number || 'No application #'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  <span>{patent.department}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  <span>Filed: {patent.filing_date}</span>
                </div>
                {patent.is_commercialized && (
                  <div className="flex items-center gap-2 text-green-400">
                    <CheckCircle className="w-4 h-4" />
                    <span>Commercialized</span>
                  </div>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-slate-800">
                <span className="text-xs px-2 py-1 bg-slate-800 rounded">
                  {PATENT_TYPES.find(t => t.value === patent.patent_type)?.label}
                </span>
              </div>
            </div>
          ))}
        </div>

        {filteredPatents.length === 0 && (
          <div className="text-center py-12 text-slate-400">
            <Award className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No patents found</p>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800">
              <h2 className="text-xl font-semibold">Add Patent</h2>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Patent Title *</label>
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
                  <label className="block text-sm font-medium mb-1">Type *</label>
                  <select
                    required
                    value={formData.patent_type}
                    onChange={(e) => setFormData({ ...formData, patent_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  >
                    {PATENT_TYPES.map(t => (
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
                    {PATENT_STATUS.map(s => (
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
                  <label className="block text-sm font-medium mb-1">Technology Area</label>
                  <input
                    type="text"
                    value={formData.technology_area}
                    onChange={(e) => setFormData({ ...formData, technology_area: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Application Number</label>
                  <input
                    type="text"
                    value={formData.application_number}
                    onChange={(e) => setFormData({ ...formData, application_number: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium mb-1">Filing Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.filing_date}
                    onChange={(e) => setFormData({ ...formData, filing_date: e.target.value, filing_year: new Date(e.target.value).getFullYear() })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Applicant/Institution</label>
                <input
                  type="text"
                  value={formData.applicant}
                  onChange={(e) => setFormData({ ...formData, applicant: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg"
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
