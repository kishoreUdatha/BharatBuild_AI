'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  BarChart3,
  ChevronRight,
  Loader2,
  Plus,
  Search,
  TrendingUp,
  Users,
  Award,
  AlertTriangle,
  X,
  Save,
  Target
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface StudentPerformance {
  id: string
  student_id: string
  student_name: string
  department: string
  program: string | null
  batch: string | null
  semester: number
  academic_year: string
  sgpa: number | null
  cgpa: number | null
  percentage: number | null
  performance_level: string | null
  overall_attendance_percentage: number | null
  is_passed: boolean | null
  backlogs_count: number
  created_at: string
}

interface PerformanceAnalytics {
  total_students: number
  average_sgpa: number
  average_cgpa: number
  pass_percentage: number
  performance_distribution: Record<string, number>
  top_performers: Array<{ student_id: string; student_name: string; cgpa: number }>
  at_risk_students: number
  average_attendance: number
}

const PERFORMANCE_LEVELS = [
  { value: 'outstanding', label: 'Outstanding', color: 'bg-purple-500/20 text-purple-400' },
  { value: 'excellent', label: 'Excellent', color: 'bg-blue-500/20 text-blue-400' },
  { value: 'good', label: 'Good', color: 'bg-green-500/20 text-green-400' },
  { value: 'average', label: 'Average', color: 'bg-yellow-500/20 text-yellow-400' },
  { value: 'below_average', label: 'Below Average', color: 'bg-orange-500/20 text-orange-400' },
  { value: 'poor', label: 'Poor', color: 'bg-red-500/20 text-red-400' }
]

export default function PerformancePage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [records, setRecords] = useState<StudentPerformance[]>([])
  const [analytics, setAnalytics] = useState<PerformanceAnalytics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')
  const [semesterFilter, setSemesterFilter] = useState('')
  const [academicYearFilter, setAcademicYearFilter] = useState('2024-25')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  const [formData, setFormData] = useState({
    student_id: '',
    student_name: '',
    department: '',
    program: '',
    batch: '',
    semester: 1,
    academic_year: '2024-25',
    sgpa: '',
    cgpa: '',
    percentage: '',
    performance_level: 'good'
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchData()
    }
  }, [authLoading, isAuthenticated, page, departmentFilter, semesterFilter, academicYearFilter])

  const fetchData = async () => {
    setIsLoading(true)
    try {
      let url = `/accreditation/criterion2/performance?page=${page}&page_size=${pageSize}&academic_year=${academicYearFilter}`
      if (departmentFilter) url += `&department=${departmentFilter}`
      if (semesterFilter) url += `&semester=${semesterFilter}`

      const [recordsResponse, analyticsResponse] = await Promise.all([
        apiClient.get(url),
        apiClient.get(`/accreditation/criterion2/performance/analytics?academic_year=${academicYearFilter}${departmentFilter ? `&department=${departmentFilter}` : ''}`)
      ])

      setRecords(recordsResponse.items || [])
      setTotal(recordsResponse.total || 0)
      setAnalytics(analyticsResponse)
    } catch (err: any) {
      console.error('Failed to fetch performance data:', err)
      setError(err.message)
      setAnalytics({
        total_students: 0,
        average_sgpa: 0,
        average_cgpa: 0,
        pass_percentage: 0,
        performance_distribution: {},
        top_performers: [],
        at_risk_students: 0,
        average_attendance: 0
      })
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
        sgpa: formData.sgpa ? parseFloat(formData.sgpa) : null,
        cgpa: formData.cgpa ? parseFloat(formData.cgpa) : null,
        percentage: formData.percentage ? parseFloat(formData.percentage) : null
      }
      await apiClient.post('/accreditation/criterion2/performance', submitData)
      setShowAddModal(false)
      setFormData({
        student_id: '',
        student_name: '',
        department: '',
        program: '',
        batch: '',
        semester: 1,
        academic_year: '2024-25',
        sgpa: '',
        cgpa: '',
        percentage: '',
        performance_level: 'good'
      })
      fetchData()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredRecords = records.filter(r =>
    r.student_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    r.student_id.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const getLevelBadge = (level: string | null) => {
    const found = PERFORMANCE_LEVELS.find(l => l.value === level)
    return found?.color || 'bg-slate-500/20 text-slate-400'
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
            <span className="text-white">Performance Analytics</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Student Performance Analytics</h1>
              <p className="text-slate-400 mt-1">Key Indicator 2.6 - Student performance and learning outcomes</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              <Plus className="w-4 h-4" />
              Add Performance Record
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Analytics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <Users className="w-5 h-5 text-blue-400 mb-2" />
            <p className="text-2xl font-bold">{analytics?.total_students || 0}</p>
            <p className="text-sm text-slate-400">Total Students</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <TrendingUp className="w-5 h-5 text-green-400 mb-2" />
            <p className="text-2xl font-bold">{analytics?.average_cgpa?.toFixed(2) || '0.00'}</p>
            <p className="text-sm text-slate-400">Average CGPA</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <Target className="w-5 h-5 text-purple-400 mb-2" />
            <p className="text-2xl font-bold">{analytics?.pass_percentage?.toFixed(1) || '0'}%</p>
            <p className="text-sm text-slate-400">Pass Percentage</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <AlertTriangle className="w-5 h-5 text-orange-400 mb-2" />
            <p className="text-2xl font-bold">{analytics?.at_risk_students || 0}</p>
            <p className="text-sm text-slate-400">At-Risk Students</p>
          </div>
        </div>

        {/* Performance Distribution & Top Performers */}
        <div className="grid lg:grid-cols-2 gap-6 mb-6">
          {/* Performance Distribution */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Performance Distribution</h3>
            <div className="space-y-3">
              {PERFORMANCE_LEVELS.map(level => {
                const count = analytics?.performance_distribution?.[level.value] || 0
                const percentage = analytics?.total_students ? Math.round(count / analytics.total_students * 100) : 0
                return (
                  <div key={level.value}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{level.label}</span>
                      <span className="text-slate-400">{count} ({percentage}%)</span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${level.color.replace('/20', '').replace('text-', 'bg-')}`}
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Top Performers */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-4">Top Performers</h3>
            <div className="space-y-3">
              {analytics?.top_performers?.slice(0, 5).map((student, index) => (
                <div key={student.student_id} className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    index === 0 ? 'bg-yellow-500/20 text-yellow-400' :
                    index === 1 ? 'bg-slate-400/20 text-slate-300' :
                    index === 2 ? 'bg-orange-500/20 text-orange-400' :
                    'bg-slate-700 text-slate-400'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium">{student.student_name}</p>
                    <p className="text-sm text-slate-400">{student.student_id}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-green-400">{student.cgpa?.toFixed(2)}</p>
                    <p className="text-xs text-slate-400">CGPA</p>
                  </div>
                </div>
              ))}
              {(!analytics?.top_performers || analytics.top_performers.length === 0) && (
                <p className="text-center text-slate-400 py-4">No data available</p>
              )}
            </div>
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
            value={academicYearFilter}
            onChange={(e) => setAcademicYearFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="2024-25">2024-25</option>
            <option value="2023-24">2023-24</option>
            <option value="2022-23">2022-23</option>
          </select>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="">All Departments</option>
            <option value="Computer Science">Computer Science</option>
            <option value="Electronics">Electronics</option>
            <option value="Mechanical">Mechanical</option>
          </select>
          <select
            value={semesterFilter}
            onChange={(e) => setSemesterFilter(e.target.value)}
            className="px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg"
          >
            <option value="">All Semesters</option>
            {[1,2,3,4,5,6,7,8].map(s => (
              <option key={s} value={s}>Semester {s}</option>
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
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Department</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Semester</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">SGPA</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">CGPA</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Attendance</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Level</th>
                  <th className="text-left px-4 py-3 text-sm font-medium text-slate-400">Status</th>
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
                    <td className="px-4 py-3 text-sm">{record.department}</td>
                    <td className="px-4 py-3 text-sm">{record.semester}</td>
                    <td className="px-4 py-3 font-medium">{record.sgpa?.toFixed(2) || '-'}</td>
                    <td className="px-4 py-3 font-medium text-blue-400">{record.cgpa?.toFixed(2) || '-'}</td>
                    <td className="px-4 py-3">
                      {record.overall_attendance_percentage !== null ? (
                        <span className={record.overall_attendance_percentage >= 75 ? 'text-green-400' : 'text-red-400'}>
                          {record.overall_attendance_percentage}%
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {record.performance_level && (
                        <span className={`text-xs px-2 py-1 rounded-full ${getLevelBadge(record.performance_level)}`}>
                          {record.performance_level.replace(/_/g, ' ')}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {record.is_passed !== null && (
                        <span className={`text-xs px-2 py-1 rounded-full ${record.is_passed ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                          {record.is_passed ? 'Passed' : `${record.backlogs_count} Backlog(s)`}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {filteredRecords.length === 0 && !isLoading && (
          <div className="text-center py-12 text-slate-400">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No performance records found. Add your first record.</p>
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
              <h2 className="text-lg font-semibold">Add Performance Record</h2>
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
                  <label className="block text-sm text-slate-400 mb-1">Program</label>
                  <input
                    type="text"
                    value={formData.program}
                    onChange={(e) => setFormData({ ...formData, program: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Semester *</label>
                  <select
                    value={formData.semester}
                    onChange={(e) => setFormData({ ...formData, semester: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  >
                    {[1,2,3,4,5,6,7,8].map(s => (
                      <option key={s} value={s}>Semester {s}</option>
                    ))}
                  </select>
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
                  <label className="block text-sm text-slate-400 mb-1">SGPA</label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    step="0.01"
                    value={formData.sgpa}
                    onChange={(e) => setFormData({ ...formData, sgpa: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">CGPA</label>
                  <input
                    type="number"
                    min="0"
                    max="10"
                    step="0.01"
                    value={formData.cgpa}
                    onChange={(e) => setFormData({ ...formData, cgpa: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Percentage</label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={formData.percentage}
                    onChange={(e) => setFormData({ ...formData, percentage: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Performance Level</label>
                  <select
                    value={formData.performance_level}
                    onChange={(e) => setFormData({ ...formData, performance_level: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg focus:border-blue-500 focus:outline-none"
                  >
                    {PERFORMANCE_LEVELS.map(l => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
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
