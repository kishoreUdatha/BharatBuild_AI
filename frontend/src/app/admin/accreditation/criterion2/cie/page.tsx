'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ClipboardCheck,
  ChevronRight,
  Loader2,
  Plus,
  Search,
  Filter,
  X,
  Save,
  Brain,
  BarChart3,
  Calendar,
  FileText
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface CIERecord {
  id: string
  student_id: string
  student_name: string
  department: string
  course_code: string
  course_name: string
  academic_year: string
  assessment_type: string
  assessment_name: string
  assessment_date: string
  max_marks: number
  marks_obtained: number | null
  percentage: number | null
  grade: string | null
  blooms_level: string | null
  course_outcomes_assessed: string[] | null
  created_at: string
}

const ASSESSMENT_TYPES = [
  { value: 'quiz', label: 'Quiz' },
  { value: 'assignment', label: 'Assignment' },
  { value: 'mid_term', label: 'Mid-Term' },
  { value: 'end_term', label: 'End-Term' },
  { value: 'project', label: 'Project' },
  { value: 'presentation', label: 'Presentation' },
  { value: 'lab', label: 'Lab' },
  { value: 'viva', label: 'Viva' },
  { value: 'seminar', label: 'Seminar' }
]

const BLOOMS_LEVELS = [
  { value: 'L1_remember', label: 'L1: Remember' },
  { value: 'L2_understand', label: 'L2: Understand' },
  { value: 'L3_apply', label: 'L3: Apply' },
  { value: 'L4_analyze', label: 'L4: Analyze' },
  { value: 'L5_evaluate', label: 'L5: Evaluate' },
  { value: 'L6_create', label: 'L6: Create' }
]

export default function CIEPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [records, setRecords] = useState<CIERecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [assessmentTypeFilter, setAssessmentTypeFilter] = useState('')
  const [academicYearFilter, setAcademicYearFilter] = useState('2024-25')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [byType, setByType] = useState<Record<string, number>>({})
  const pageSize = 20

  const [formData, setFormData] = useState({
    student_id: '',
    student_name: '',
    department: '',
    course_code: '',
    course_name: '',
    academic_year: '2024-25',
    assessment_type: 'quiz',
    assessment_name: '',
    assessment_date: new Date().toISOString().split('T')[0],
    max_marks: 20,
    marks_obtained: '',
    blooms_level: 'L3_apply',
    course_outcomes_assessed: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchRecords()
    }
  }, [authLoading, isAuthenticated, page, assessmentTypeFilter, academicYearFilter])

  const fetchRecords = async () => {
    setIsLoading(true)
    try {
      let url = `/accreditation/criterion2/cie?page=${page}&page_size=${pageSize}&academic_year=${academicYearFilter}`
      if (assessmentTypeFilter) url += `&assessment_type=${assessmentTypeFilter}`

      const response = await apiClient.get(url)
      setRecords(response.items || [])
      setTotal(response.total || 0)
      setByType(response.by_assessment_type || {})
    } catch (err: any) {
      console.error('Failed to fetch CIE records:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      const submitData = {
        ...formData,
        marks_obtained: formData.marks_obtained ? parseFloat(formData.marks_obtained) : null,
        course_outcomes_assessed: formData.course_outcomes_assessed ? formData.course_outcomes_assessed.split(',').map(s => s.trim()) : null
      }
      await apiClient.post('/accreditation/criterion2/cie', submitData)
      setShowAddModal(false)
      setFormData({
        student_id: '',
        student_name: '',
        department: '',
        course_code: '',
        course_name: '',
        academic_year: '2024-25',
        assessment_type: 'quiz',
        assessment_name: '',
        assessment_date: new Date().toISOString().split('T')[0],
        max_marks: 20,
        marks_obtained: '',
        blooms_level: 'L3_apply',
        course_outcomes_assessed: ''
      })
      fetchRecords()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredRecords = records.filter(r =>
    r.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.student_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.course_code.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getTypeBadge = (type: string) => {
    const colors: Record<string, string> = {
      quiz: 'bg-blue-500/20 text-blue-400',
      assignment: 'bg-green-500/20 text-green-400',
      mid_term: 'bg-purple-500/20 text-purple-400',
      end_term: 'bg-red-500/20 text-red-400',
      project: 'bg-orange-500/20 text-orange-400',
      presentation: 'bg-teal-500/20 text-teal-400',
      lab: 'bg-yellow-500/20 text-yellow-400',
      viva: 'bg-pink-500/20 text-pink-400',
      seminar: 'bg-indigo-500/20 text-indigo-400'
    }
    return colors[type] || 'bg-slate-500/20 text-slate-400'
  }

  const getBloomsBadge = (level: string | null) => {
    if (!level) return 'bg-slate-500/20 text-slate-400'
    const colors: Record<string, string> = {
      'L1_remember': 'bg-red-500/20 text-red-400',
      'L2_understand': 'bg-orange-500/20 text-orange-400',
      'L3_apply': 'bg-yellow-500/20 text-yellow-400',
      'L4_analyze': 'bg-green-500/20 text-green-400',
      'L5_evaluate': 'bg-cyan-500/20 text-cyan-400',
      'L6_create': 'bg-purple-500/20 text-purple-400'
    }
    return colors[level] || 'bg-slate-500/20 text-slate-400'
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
            <span className="text-white">CIE Records</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Continuous Internal Evaluation</h1>
              <p className="text-slate-400 mt-1">Key Indicator 2.5 - Evaluation process and reforms</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add CIE Record
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <ClipboardCheck className="w-5 h-5 text-blue-400 mb-2" />
            <p className="text-2xl font-bold">{total}</p>
            <p className="text-sm text-slate-400">Total Records</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <FileText className="w-5 h-5 text-purple-400 mb-2" />
            <p className="text-2xl font-bold">{byType['quiz'] || 0}</p>
            <p className="text-sm text-slate-400">Quizzes</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <Calendar className="w-5 h-5 text-green-400 mb-2" />
            <p className="text-2xl font-bold">{byType['mid_term'] || 0}</p>
            <p className="text-sm text-slate-400">Mid-Terms</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <Brain className="w-5 h-5 text-orange-400 mb-2" />
            <p className="text-2xl font-bold">{byType['project'] || 0}</p>
            <p className="text-sm text-slate-400">Projects</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by student or course..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
            />
          </div>
          <select
            value={academicYearFilter}
            onChange={(e) => setAcademicYearFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="2024-25">2024-25</option>
            <option value="2023-24">2023-24</option>
            <option value="2022-23">2022-23</option>
          </select>
          <select
            value={assessmentTypeFilter}
            onChange={(e) => setAssessmentTypeFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="">All Types</option>
            {ASSESSMENT_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>

        {/* Records Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-800">
                <tr>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Student</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Course</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Assessment</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Date</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Marks</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Bloom's</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">COs</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filteredRecords.map((record) => (
                  <tr key={record.id} className="hover:bg-slate-800/50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium">{record.student_name}</p>
                        <p className="text-sm text-slate-400">{record.student_id}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium">{record.course_code}</p>
                        <p className="text-sm text-slate-400">{record.course_name}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <span className={`text-xs px-2 py-1 rounded-full ${getTypeBadge(record.assessment_type)}`}>
                          {record.assessment_type.replace(/_/g, ' ')}
                        </span>
                        <p className="text-sm text-slate-400 mt-1">{record.assessment_name}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {new Date(record.assessment_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="font-medium">
                          {record.marks_obtained !== null ? record.marks_obtained : '-'} / {record.max_marks}
                        </p>
                        {record.percentage !== null && (
                          <p className="text-sm text-slate-400">{record.percentage}%</p>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {record.blooms_level && (
                        <span className={`text-xs px-2 py-1 rounded-full ${getBloomsBadge(record.blooms_level)}`}>
                          {record.blooms_level.replace('_', ': ')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {record.course_outcomes_assessed?.map((co, i) => (
                          <span key={i} className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                            {co}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {filteredRecords.length === 0 && !isLoading && (
          <div className="text-center py-12 text-slate-400">
            <ClipboardCheck className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No CIE records found. Add your first assessment record.</p>
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
              <h2 className="text-lg font-semibold">Add CIE Record</h2>
              <button onClick={() => setShowAddModal(false)} className="p-1 hover:bg-slate-800 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Student ID *</label>
                  <input
                    type="text"
                    required
                    value={formData.student_id}
                    onChange={(e) => setFormData({ ...formData, student_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Student Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.student_name}
                    onChange={(e) => setFormData({ ...formData, student_name: e.target.value })}
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
                  <label className="block text-sm text-slate-400 mb-1">Academic Year *</label>
                  <select
                    value={formData.academic_year}
                    onChange={(e) => setFormData({ ...formData, academic_year: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  >
                    <option value="2024-25">2024-25</option>
                    <option value="2023-24">2023-24</option>
                    <option value="2022-23">2022-23</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Course Code *</label>
                  <input
                    type="text"
                    required
                    value={formData.course_code}
                    onChange={(e) => setFormData({ ...formData, course_code: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Course Name *</label>
                  <input
                    type="text"
                    required
                    value={formData.course_name}
                    onChange={(e) => setFormData({ ...formData, course_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Assessment Type *</label>
                  <select
                    value={formData.assessment_type}
                    onChange={(e) => setFormData({ ...formData, assessment_type: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  >
                    {ASSESSMENT_TYPES.map(t => (
                      <option key={t.value} value={t.value}>{t.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Assessment Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Quiz 1, Mid-Term 1"
                    value={formData.assessment_name}
                    onChange={(e) => setFormData({ ...formData, assessment_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Assessment Date *</label>
                  <input
                    type="date"
                    required
                    value={formData.assessment_date}
                    onChange={(e) => setFormData({ ...formData, assessment_date: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Max Marks *</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={formData.max_marks}
                    onChange={(e) => setFormData({ ...formData, max_marks: parseInt(e.target.value) || 0 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Marks Obtained</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={formData.marks_obtained}
                    onChange={(e) => setFormData({ ...formData, marks_obtained: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Bloom's Level</label>
                  <select
                    value={formData.blooms_level}
                    onChange={(e) => setFormData({ ...formData, blooms_level: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  >
                    {BLOOMS_LEVELS.map(l => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm text-slate-400 mb-1">Course Outcomes Assessed (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="e.g., CO1, CO2, CO3"
                    value={formData.course_outcomes_assessed}
                    onChange={(e) => setFormData({ ...formData, course_outcomes_assessed: e.target.value })}
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
                  Save Record
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
