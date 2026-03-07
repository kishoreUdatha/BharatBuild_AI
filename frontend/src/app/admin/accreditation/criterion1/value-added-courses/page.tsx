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
  X,
  Users,
  Clock,
  Award,
  Calendar,
  BookOpen,
  CheckCircle2,
  User
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface ValueAddedCourse {
  id: string
  course_name: string
  course_code: string | null
  course_type: string
  course_mode: string
  department: string
  academic_year: string
  semester: number | null
  description: string | null
  duration_hours: number
  credits: number | null
  instructor_name: string | null
  start_date: string | null
  end_date: string | null
  max_enrollment: number | null
  current_enrollment: number
  completed_count: number
  certification_provided: boolean
  certifying_body: string | null
  is_active: boolean
  created_at: string
}

const COURSE_TYPES = [
  { value: 'skill_development', label: 'Skill Development', color: 'blue' },
  { value: 'soft_skills', label: 'Soft Skills', color: 'pink' },
  { value: 'language', label: 'Language', color: 'purple' },
  { value: 'ict', label: 'ICT/Computer', color: 'green' },
  { value: 'employability', label: 'Employability', color: 'orange' },
  { value: 'entrepreneurship', label: 'Entrepreneurship', color: 'teal' },
  { value: 'certification', label: 'Certification', color: 'yellow' },
  { value: 'bridge_course', label: 'Bridge Course', color: 'red' }
]

const COURSE_MODES = [
  { value: 'offline', label: 'Offline' },
  { value: 'online', label: 'Online' },
  { value: 'hybrid', label: 'Hybrid' }
]

export default function ValueAddedCoursesPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [courses, setCourses] = useState<ValueAddedCourse[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [byType, setByType] = useState<Record<string, number>>({})

  const [newCourse, setNewCourse] = useState({
    course_name: '',
    course_code: '',
    course_type: 'skill_development',
    course_mode: 'offline',
    department: '',
    academic_year: '2024-25',
    semester: '',
    description: '',
    duration_hours: 30,
    credits: '',
    instructor_name: '',
    instructor_qualification: '',
    instructor_organization: '',
    start_date: '',
    end_date: '',
    max_enrollment: '',
    certification_provided: false,
    certifying_body: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchCourses()
    }
  }, [authLoading, isAuthenticated, typeFilter])

  const fetchCourses = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (typeFilter) params.append('course_type', typeFilter)
      params.append('page_size', '50')

      const response = await apiClient.get(`/accreditation/criterion1/value-added-courses?${params.toString()}`)
      setCourses(response.items || [])
      setByType(response.by_type || {})
    } catch (err: any) {
      console.error('Failed to fetch courses:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddCourse = async () => {
    if (!newCourse.course_name || !newCourse.department) {
      setError('Please fill in required fields')
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion1/value-added-courses', {
        ...newCourse,
        semester: newCourse.semester ? parseInt(newCourse.semester) : null,
        credits: newCourse.credits ? parseFloat(newCourse.credits) : null,
        max_enrollment: newCourse.max_enrollment ? parseInt(newCourse.max_enrollment) : null,
        start_date: newCourse.start_date || null,
        end_date: newCourse.end_date || null
      })
      setShowAddModal(false)
      setNewCourse({
        course_name: '',
        course_code: '',
        course_type: 'skill_development',
        course_mode: 'offline',
        department: '',
        academic_year: '2024-25',
        semester: '',
        description: '',
        duration_hours: 30,
        credits: '',
        instructor_name: '',
        instructor_qualification: '',
        instructor_organization: '',
        start_date: '',
        end_date: '',
        max_enrollment: '',
        certification_provided: false,
        certifying_body: ''
      })
      fetchCourses()
    } catch (err: any) {
      console.error('Failed to add course:', err)
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredCourses = courses.filter(c =>
    c.course_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.department.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const totalEnrollments = courses.reduce((sum, c) => sum + c.current_enrollment, 0)
  const totalCompleted = courses.reduce((sum, c) => sum + c.completed_count, 0)
  const activeCourses = courses.filter(c => c.is_active).length

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
      <div className="bg-gradient-to-r from-green-600 to-green-500 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 text-green-100 mb-2">
            <Link href="/admin/accreditation" className="hover:text-white">NAAC</Link>
            <ChevronRight className="w-4 h-4" />
            <Link href="/admin/accreditation/criterion1" className="hover:text-white">Criterion 1</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white">Value-Added Courses</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <GraduationCap className="w-6 h-6" />
                Value-Added Courses
              </h1>
              <p className="text-green-100">Key Indicator 1.3 - Curriculum Enrichment</p>
            </div>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-white text-green-600 px-4 py-2 rounded-lg font-medium hover:bg-green-50 transition-colors flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Add Course
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <BookOpen className="w-8 h-8 text-green-500" />
              <span className="text-2xl font-bold">{courses.length}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Total Courses</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <CheckCircle2 className="w-8 h-8 text-blue-500" />
              <span className="text-2xl font-bold">{activeCourses}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Active Courses</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <Users className="w-8 h-8 text-purple-500" />
              <span className="text-2xl font-bold">{totalEnrollments}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Total Enrollments</p>
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <Award className="w-8 h-8 text-orange-500" />
              <span className="text-2xl font-bold">{totalCompleted}</span>
            </div>
            <p className="text-slate-400 text-sm mt-2">Completed</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search courses..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-green-500"
            />
          </div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
          >
            <option value="">All Types</option>
            {COURSE_TYPES.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
        </div>

        {/* Courses Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-green-500" />
          </div>
        ) : filteredCourses.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-xl">
            <GraduationCap className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400">No courses found</h3>
            <p className="text-slate-500 mb-4">Add value-added courses for students</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-green-500 hover:bg-green-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Add First Course
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredCourses.map((course) => {
              const typeInfo = COURSE_TYPES.find(t => t.value === course.course_type)

              return (
                <div
                  key={course.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <span className={`bg-${typeInfo?.color || 'slate'}-500/10 text-${typeInfo?.color || 'slate'}-400 px-2 py-0.5 rounded text-xs`}>
                        {typeInfo?.label || course.course_type}
                      </span>
                    </div>
                    {course.is_active ? (
                      <span className="bg-green-500/10 text-green-400 px-2 py-0.5 rounded text-xs">Active</span>
                    ) : (
                      <span className="bg-slate-500/10 text-slate-400 px-2 py-0.5 rounded text-xs">Inactive</span>
                    )}
                  </div>

                  <h3 className="font-semibold text-lg mb-1">{course.course_name}</h3>
                  {course.course_code && (
                    <p className="text-sm text-slate-500 mb-2">{course.course_code}</p>
                  )}
                  <p className="text-sm text-slate-400 mb-4">{course.department}</p>

                  <div className="space-y-2 mb-4">
                    <div className="flex items-center gap-2 text-sm text-slate-400">
                      <Clock className="w-4 h-4" />
                      {course.duration_hours} hours
                      {course.credits && ` | ${course.credits} credits`}
                    </div>
                    {course.instructor_name && (
                      <div className="flex items-center gap-2 text-sm text-slate-400">
                        <User className="w-4 h-4" />
                        {course.instructor_name}
                      </div>
                    )}
                    {course.certification_provided && (
                      <div className="flex items-center gap-2 text-sm text-green-400">
                        <Award className="w-4 h-4" />
                        Certificate Provided
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-800">
                    <div>
                      <p className="text-2xl font-bold text-blue-400">{course.current_enrollment}</p>
                      <p className="text-xs text-slate-500">Enrolled</p>
                    </div>
                    <div>
                      <p className="text-2xl font-bold text-green-400">{course.completed_count}</p>
                      <p className="text-xs text-slate-500">Completed</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Add Course Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Add Value-Added Course</h2>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Course Name *</label>
                  <input
                    type="text"
                    value={newCourse.course_name}
                    onChange={(e) => setNewCourse({ ...newCourse, course_name: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                    placeholder="e.g., Python Programming"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Course Code</label>
                  <input
                    type="text"
                    value={newCourse.course_code}
                    onChange={(e) => setNewCourse({ ...newCourse, course_code: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                    placeholder="e.g., VAC-CS-001"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Course Type *</label>
                  <select
                    value={newCourse.course_type}
                    onChange={(e) => setNewCourse({ ...newCourse, course_type: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                  >
                    {COURSE_TYPES.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Mode</label>
                  <select
                    value={newCourse.course_mode}
                    onChange={(e) => setNewCourse({ ...newCourse, course_mode: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                  >
                    {COURSE_MODES.map(mode => (
                      <option key={mode.value} value={mode.value}>{mode.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Department *</label>
                  <input
                    type="text"
                    value={newCourse.department}
                    onChange={(e) => setNewCourse({ ...newCourse, department: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Duration (Hours) *</label>
                  <input
                    type="number"
                    value={newCourse.duration_hours}
                    onChange={(e) => setNewCourse({ ...newCourse, duration_hours: parseInt(e.target.value) || 0 })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                    min="1"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Description</label>
                <textarea
                  value={newCourse.description}
                  onChange={(e) => setNewCourse({ ...newCourse, description: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500 min-h-[80px]"
                  placeholder="Course description..."
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Instructor Name</label>
                  <input
                    type="text"
                    value={newCourse.instructor_name}
                    onChange={(e) => setNewCourse({ ...newCourse, instructor_name: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Max Enrollment</label>
                  <input
                    type="number"
                    value={newCourse.max_enrollment}
                    onChange={(e) => setNewCourse({ ...newCourse, max_enrollment: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                    min="1"
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="certification"
                  checked={newCourse.certification_provided}
                  onChange={(e) => setNewCourse({ ...newCourse, certification_provided: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-green-500 focus:ring-green-500"
                />
                <label htmlFor="certification" className="text-sm text-slate-300">Certificate will be provided</label>
              </div>

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
                onClick={handleAddCourse}
                disabled={isSubmitting}
                className="px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Add Course
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
