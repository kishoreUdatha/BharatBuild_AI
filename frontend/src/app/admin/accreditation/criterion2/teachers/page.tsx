'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  GraduationCap,
  ChevronRight,
  Loader2,
  Plus,
  Search,
  Filter,
  Award,
  BookOpen,
  Users,
  X,
  Save,
  CheckCircle2,
  AlertCircle
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface TeacherProfile {
  id: string
  employee_id: string
  name: string
  email: string | null
  phone: string | null
  department: string
  designation: string
  highest_qualification: string | null
  specialization: string | null
  teaching_experience_years: number
  industry_experience_years: number
  research_experience_years: number
  publications_count: number
  patents_count: number
  awards: any[] | null
  fdp_attended: any[] | null
  student_feedback_rating: number | null
  uses_lms: boolean
  is_active: boolean
  created_at: string
}

const DESIGNATIONS = [
  { value: 'professor', label: 'Professor' },
  { value: 'associate_professor', label: 'Associate Professor' },
  { value: 'assistant_professor', label: 'Assistant Professor' },
  { value: 'lecturer', label: 'Lecturer' },
  { value: 'guest_faculty', label: 'Guest Faculty' },
  { value: 'adjunct_faculty', label: 'Adjunct Faculty' },
  { value: 'visiting_faculty', label: 'Visiting Faculty' }
]

export default function TeachersPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [teachers, setTeachers] = useState<TeacherProfile[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [designationFilter, setDesignationFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  const [formData, setFormData] = useState({
    employee_id: '',
    name: '',
    email: '',
    phone: '',
    department: '',
    designation: 'assistant_professor',
    highest_qualification: '',
    specialization: '',
    teaching_experience_years: 0,
    industry_experience_years: 0,
    research_experience_years: 0
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchTeachers()
    }
  }, [authLoading, isAuthenticated, page, departmentFilter, designationFilter])

  const fetchTeachers = async () => {
    setIsLoading(true)
    try {
      let url = `/accreditation/criterion2/teachers?page=${page}&page_size=${pageSize}`
      if (departmentFilter) url += `&department=${departmentFilter}`
      if (designationFilter) url += `&designation=${designationFilter}`

      const response = await apiClient.get(url)
      setTeachers(response.items || [])
      setTotal(response.total || 0)
    } catch (err: any) {
      console.error('Failed to fetch teachers:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion2/teachers', formData)
      setShowAddModal(false)
      setFormData({
        employee_id: '',
        name: '',
        email: '',
        phone: '',
        department: '',
        designation: 'assistant_professor',
        highest_qualification: '',
        specialization: '',
        teaching_experience_years: 0,
        industry_experience_years: 0,
        research_experience_years: 0
      })
      fetchTeachers()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredTeachers = teachers.filter(t =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    t.employee_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getDesignationBadge = (designation: string) => {
    const colors: Record<string, string> = {
      professor: 'bg-purple-500/20 text-purple-400',
      associate_professor: 'bg-blue-500/20 text-blue-400',
      assistant_professor: 'bg-green-500/20 text-green-400',
      lecturer: 'bg-orange-500/20 text-orange-400',
      guest_faculty: 'bg-teal-500/20 text-teal-400',
      adjunct_faculty: 'bg-pink-500/20 text-pink-400',
      visiting_faculty: 'bg-yellow-500/20 text-yellow-400'
    }
    return colors[designation] || 'bg-slate-500/20 text-slate-400'
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
      {/* Header */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
            <Link href="/admin/accreditation" className="hover:text-white">Accreditation</Link>
            <ChevronRight className="w-4 h-4" />
            <Link href="/admin/accreditation/criterion2" className="hover:text-white">Criterion 2</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white">Teachers</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Teacher Profiles</h1>
              <p className="text-slate-400 mt-1">Key Indicator 2.2 & 2.4 - Faculty qualifications and quality</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add Teacher
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <GraduationCap className="w-5 h-5 text-blue-400 mb-2" />
            <p className="text-2xl font-bold">{total}</p>
            <p className="text-sm text-slate-400">Total Faculty</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <Award className="w-5 h-5 text-purple-400 mb-2" />
            <p className="text-2xl font-bold">{teachers.filter(t => t.highest_qualification?.toLowerCase().includes('ph.d')).length}</p>
            <p className="text-sm text-slate-400">With Ph.D.</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <BookOpen className="w-5 h-5 text-green-400 mb-2" />
            <p className="text-2xl font-bold">{teachers.reduce((a, t) => a + t.publications_count, 0)}</p>
            <p className="text-sm text-slate-400">Publications</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <Users className="w-5 h-5 text-orange-400 mb-2" />
            <p className="text-2xl font-bold">{teachers.filter(t => t.uses_lms).length}</p>
            <p className="text-sm text-slate-400">Using LMS</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
            />
          </div>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="">All Departments</option>
            <option value="Computer Science">Computer Science</option>
            <option value="Electronics">Electronics</option>
            <option value="Mechanical">Mechanical</option>
            <option value="Civil">Civil</option>
          </select>
          <select
            value={designationFilter}
            onChange={(e) => setDesignationFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="">All Designations</option>
            {DESIGNATIONS.map(d => (
              <option key={d.value} value={d.value}>{d.label}</option>
            ))}
          </select>
        </div>

        {/* Teachers Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTeachers.map((teacher) => (
            <div
              key={teacher.id}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold">{teacher.name}</h3>
                  <p className="text-sm text-slate-400">{teacher.employee_id}</p>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${getDesignationBadge(teacher.designation)}`}>
                  {teacher.designation.replace(/_/g, ' ')}
                </span>
              </div>
              <div className="space-y-2 text-sm">
                <p><span className="text-slate-400">Department:</span> {teacher.department}</p>
                <p><span className="text-slate-400">Qualification:</span> {teacher.highest_qualification || 'N/A'}</p>
                <p><span className="text-slate-400">Experience:</span> {teacher.teaching_experience_years} years</p>
                <div className="flex gap-4 pt-2 border-t border-slate-800">
                  <span className="text-blue-400">{teacher.publications_count} pubs</span>
                  <span className="text-purple-400">{teacher.patents_count} patents</span>
                  {teacher.uses_lms && <span className="text-green-400">LMS</span>}
                </div>
              </div>
            </div>
          ))}
        </div>

        {filteredTeachers.length === 0 && !isLoading && (
          <div className="text-center py-12 text-slate-400">
            <GraduationCap className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No teachers found. Add your first teacher profile.</p>
          </div>
        )}

        {/* Pagination */}
        {total > pageSize && (
          <div className="flex justify-center gap-2 mt-8">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-slate-800 rounded-lg disabled:opacity-50"
            >
              Previous
            </button>
            <span className="px-4 py-2">Page {page} of {Math.ceil(total / pageSize)}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(total / pageSize)}
              className="px-4 py-2 bg-slate-800 rounded-lg disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold">Add Teacher Profile</h2>
              <button onClick={() => setShowAddModal(false)} className="p-1 hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Employee ID *</label>
                  <input
                    type="text"
                    required
                    value={formData.employee_id}
                    onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Phone</label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Department *</label>
                  <input
                    type="text"
                    required
                    value={formData.department}
                    onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Designation *</label>
                  <select
                    value={formData.designation}
                    onChange={(e) => setFormData({ ...formData, designation: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  >
                    {DESIGNATIONS.map(d => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Highest Qualification</label>
                  <input
                    type="text"
                    placeholder="e.g., Ph.D., M.Tech"
                    value={formData.highest_qualification}
                    onChange={(e) => setFormData({ ...formData, highest_qualification: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Specialization</label>
                  <input
                    type="text"
                    value={formData.specialization}
                    onChange={(e) => setFormData({ ...formData, specialization: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Teaching Experience (years)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={formData.teaching_experience_years}
                    onChange={(e) => setFormData({ ...formData, teaching_experience_years: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Industry Experience (years)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={formData.industry_experience_years}
                    onChange={(e) => setFormData({ ...formData, industry_experience_years: parseFloat(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Save Teacher
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
