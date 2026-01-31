'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  Search, Users, TrendingUp, AlertTriangle, Award, X, Mail, Phone,
  BookOpen, Code, FileText, Calendar, Clock, Activity, ChevronRight,
  Bell, Flag, Download, BarChart3, PieChart, UserCheck, UserX,
  Filter, RefreshCw, Send, Target, Zap, Eye
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Interfaces
interface Department {
  id: string
  name: string
  code: string
}

interface Student {
  id: string
  roll_number: string
  name: string
  email: string
  phone?: string
  is_active: boolean
  attendance_percent: number
  lab_completion_percent: number
  project_status: string
  ai_usage_percent: number
  overall_score: number
  performance_tier: 'top' | 'average' | 'weak' | 'inactive'
  last_active: string | null
  guide_name?: string
  pending_labs: number
  missed_deadlines: number
}

interface StudentDetail {
  id: string
  email: string
  full_name: string
  roll_number: string
  phone?: string
  college_name: string
  department: string
  section: string
  semester: number
  batch: string
  is_active: boolean
  guide_name?: string
  attendance: {
    overall: number
    subject_wise: { subject: string; percent: number }[]
    lab_attendance: number
    monthly_trend: { month: string; percent: number }[]
  }
  learning_progress: {
    theory_completion: number
    lab_completion: number
    pending_labs: string[]
    missed_deadlines: number
  }
  project: {
    id: string
    title: string
    current_phase: string
    review_status: string
    next_review_date?: string
    reviewer_comments?: string
    guide_name: string
    is_approved: boolean
    plagiarism_score: number
    ai_detection_score: number
  } | null
  activity: {
    login_frequency: number
    time_spent_hours: number
    coding_activity_level: string
    last_active: string
  }
  lab_enrollments: {
    lab_id: string
    lab_name: string
    lab_code: string
    progress: number
    score: number
    rank?: number
  }[]
}

export default function StudentsPage() {
  // Selection states
  const [selectedDepartment, setSelectedDepartment] = useState<string>('CSE')
  const [selectedYear, setSelectedYear] = useState<number>(3)
  const [selectedSemester, setSelectedSemester] = useState<number>(5)
  const [selectedSection, setSelectedSection] = useState<string>('A')
  const [selectedSubject, setSelectedSubject] = useState<string>('')

  // Data states
  const [students, setStudents] = useState<Student[]>([])
  const [loading, setLoading] = useState(true)
  const [studentsLoading, setStudentsLoading] = useState(false)

  // Filter states
  const [searchQuery, setSearchQuery] = useState('')
  const [performanceFilter, setPerformanceFilter] = useState<string>('')
  const [quickFilter, setQuickFilter] = useState<string>('')

  // Detail panel states
  const [selectedStudent, setSelectedStudent] = useState<StudentDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [showDetailPanel, setShowDetailPanel] = useState(false)
  const [detailTab, setDetailTab] = useState<'overview' | 'attendance' | 'progress' | 'project' | 'activity'>('overview')

  // Static data
  const departments: Department[] = [
    { id: '1', name: 'Computer Science', code: 'CSE' },
    { id: '2', name: 'Electronics', code: 'ECE' },
    { id: '3', name: 'Artificial Intelligence', code: 'AI' },
    { id: '4', name: 'Information Technology', code: 'IT' },
  ]

  const years = [1, 2, 3, 4]
  const sections = ['A', 'B', 'C']
  const subjects = ['Data Structures', 'DBMS', 'OS', 'Networks', 'Web Development']

  useEffect(() => {
    fetchStudents()
  }, [selectedDepartment, selectedYear, selectedSemester, selectedSection])

  const fetchStudents = async () => {
    setStudentsLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const params = new URLSearchParams({
        department: selectedDepartment,
        year: selectedYear.toString(),
        semester: selectedSemester.toString(),
        section: selectedSection
      })

      const res = await fetch(`${API_BASE}/faculty/students?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setStudents(data.students || [])
      }
    } catch (e) {
      // Demo data
      const mockStudents: Student[] = [
        { id: '1', roll_number: '21CS101', name: 'Rahul Kumar', email: 'rahul@college.edu', is_active: true, attendance_percent: 92, lab_completion_percent: 85, project_status: 'Review-2', ai_usage_percent: 15, overall_score: 88, performance_tier: 'top', last_active: '2024-01-28', guide_name: 'Dr. Smith', pending_labs: 0, missed_deadlines: 0 },
        { id: '2', roll_number: '21CS102', name: 'Priya Sharma', email: 'priya@college.edu', is_active: true, attendance_percent: 78, lab_completion_percent: 72, project_status: 'Review-2', ai_usage_percent: 28, overall_score: 68, performance_tier: 'average', last_active: '2024-01-27', guide_name: 'Dr. Patel', pending_labs: 2, missed_deadlines: 1 },
        { id: '3', roll_number: '21CS103', name: 'Amit Patel', email: 'amit@college.edu', is_active: true, attendance_percent: 95, lab_completion_percent: 92, project_status: 'Review-3', ai_usage_percent: 8, overall_score: 91, performance_tier: 'top', last_active: '2024-01-28', guide_name: 'Dr. Smith', pending_labs: 0, missed_deadlines: 0 },
        { id: '4', roll_number: '21CS104', name: 'Sneha Reddy', email: 'sneha@college.edu', is_active: false, attendance_percent: 58, lab_completion_percent: 45, project_status: 'Review-1', ai_usage_percent: 65, overall_score: 42, performance_tier: 'weak', last_active: '2024-01-10', guide_name: 'Dr. Kumar', pending_labs: 5, missed_deadlines: 3 },
        { id: '5', roll_number: '21CS105', name: 'Vikram Singh', email: 'vikram@college.edu', is_active: true, attendance_percent: 72, lab_completion_percent: 65, project_status: 'Review-2', ai_usage_percent: 35, overall_score: 58, performance_tier: 'average', last_active: '2024-01-26', guide_name: 'Dr. Patel', pending_labs: 3, missed_deadlines: 2 },
        { id: '6', roll_number: '21CS106', name: 'Anjali Gupta', email: 'anjali@college.edu', is_active: true, attendance_percent: 88, lab_completion_percent: 88, project_status: 'Review-3', ai_usage_percent: 12, overall_score: 85, performance_tier: 'top', last_active: '2024-01-28', guide_name: 'Dr. Smith', pending_labs: 1, missed_deadlines: 0 },
        { id: '7', roll_number: '21CS107', name: 'Ravi Verma', email: 'ravi@college.edu', phone: '9876543210', is_active: false, attendance_percent: 45, lab_completion_percent: 32, project_status: 'Not Started', ai_usage_percent: 0, overall_score: 28, performance_tier: 'inactive', last_active: '2024-01-05', guide_name: 'Dr. Kumar', pending_labs: 8, missed_deadlines: 5 },
        { id: '8', roll_number: '21CS108', name: 'Meera Nair', email: 'meera@college.edu', is_active: true, attendance_percent: 82, lab_completion_percent: 78, project_status: 'Review-2', ai_usage_percent: 22, overall_score: 75, performance_tier: 'average', last_active: '2024-01-27', guide_name: 'Dr. Patel', pending_labs: 1, missed_deadlines: 1 },
      ]
      setStudents(mockStudents)
    }
    setLoading(false)
    setStudentsLoading(false)
  }

  const fetchStudentDetail = async (studentId: string) => {
    setDetailLoading(true)
    setShowDetailPanel(true)
    setDetailTab('overview')

    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/faculty/students/${studentId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setSelectedStudent(await res.json())
      }
    } catch (e) {
      const student = students.find(s => s.id === studentId)
      if (student) {
        setSelectedStudent({
          id: student.id,
          email: student.email,
          full_name: student.name,
          roll_number: student.roll_number,
          phone: '9876543210',
          college_name: 'ABC Engineering College',
          department: selectedDepartment,
          section: selectedSection,
          semester: selectedSemester,
          batch: '2021-2025',
          is_active: student.is_active,
          guide_name: student.guide_name,
          attendance: {
            overall: student.attendance_percent,
            subject_wise: [
              { subject: 'Data Structures', percent: 95 },
              { subject: 'DBMS', percent: 88 },
              { subject: 'OS', percent: 82 },
              { subject: 'Networks', percent: 78 },
            ],
            lab_attendance: 90,
            monthly_trend: [
              { month: 'Sep', percent: 85 },
              { month: 'Oct', percent: 88 },
              { month: 'Nov', percent: 92 },
              { month: 'Dec', percent: 90 },
              { month: 'Jan', percent: student.attendance_percent },
            ]
          },
          learning_progress: {
            theory_completion: 78,
            lab_completion: student.lab_completion_percent,
            pending_labs: student.pending_labs > 0 ? ['Lab 5: Graphs', 'Lab 6: Hashing'] : [],
            missed_deadlines: student.missed_deadlines
          },
          project: student.project_status !== 'Not Started' ? {
            id: 'p1',
            title: 'Smart Campus Management System',
            current_phase: student.project_status,
            review_status: 'Completed',
            next_review_date: '2024-02-15',
            reviewer_comments: 'Good progress. Focus on documentation.',
            guide_name: student.guide_name || 'Dr. Smith',
            is_approved: true,
            plagiarism_score: 12,
            ai_detection_score: student.ai_usage_percent
          } : null,
          activity: {
            login_frequency: student.is_active ? 5 : 0,
            time_spent_hours: student.is_active ? 12.5 : 0,
            coding_activity_level: student.is_active ? 'High' : 'None',
            last_active: student.last_active || 'N/A'
          },
          lab_enrollments: [
            { lab_id: '1', lab_name: 'Data Structures Lab', lab_code: 'CS301', progress: 78, score: 82, rank: 5 },
            { lab_id: '2', lab_name: 'Database Lab', lab_code: 'CS302', progress: 65, score: 70, rank: 12 },
          ]
        })
      }
    }
    setDetailLoading(false)
  }

  // Filtered students
  const filteredStudents = useMemo(() => {
    let result = students

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      result = result.filter(s => s.name.toLowerCase().includes(q) || s.roll_number.toLowerCase().includes(q))
    }

    if (performanceFilter) {
      result = result.filter(s => s.performance_tier === performanceFilter)
    }

    if (quickFilter) {
      switch (quickFilter) {
        case 'low_attendance':
          result = result.filter(s => s.attendance_percent < 75)
          break
        case 'pending_labs':
          result = result.filter(s => s.pending_labs > 0)
          break
        case 'high_ai':
          result = result.filter(s => s.ai_usage_percent > 50)
          break
        case 'inactive':
          result = result.filter(s => !s.is_active)
          break
        case 'review_pending':
          result = result.filter(s => s.project_status.includes('Review'))
          break
      }
    }

    return result
  }, [students, searchQuery, performanceFilter, quickFilter])

  // Stats
  const stats = useMemo(() => {
    const total = students.length
    const active = students.filter(s => s.is_active).length
    const inactive = students.filter(s => !s.is_active).length
    const top = students.filter(s => s.performance_tier === 'top').length
    const average = students.filter(s => s.performance_tier === 'average').length
    const weak = students.filter(s => s.performance_tier === 'weak').length
    const lowAttendance = students.filter(s => s.attendance_percent < 75).length
    const highAI = students.filter(s => s.ai_usage_percent > 50).length

    return { total, active, inactive, top, average, weak, lowAttendance, highAI }
  }, [students])

  // Helper functions
  const getPerformanceTag = (tier: string) => {
    switch (tier) {
      case 'top': return { label: 'Top Performer', color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' }
      case 'average': return { label: 'Average', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' }
      case 'weak': return { label: 'Weak', color: 'bg-red-500/20 text-red-400 border-red-500/30' }
      case 'inactive': return { label: 'Inactive', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' }
      default: return { label: 'Unknown', color: 'bg-gray-500/20 text-gray-400' }
    }
  }

  const getAttendanceColor = (percent: number) => {
    if (percent >= 75) return 'text-emerald-400'
    if (percent >= 65) return 'text-amber-400'
    return 'text-red-400'
  }

  const getProgressBarColor = (percent: number) => {
    if (percent >= 75) return 'bg-emerald-500'
    if (percent >= 50) return 'bg-amber-500'
    return 'bg-red-500'
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Top Selection Panel - Sticky */}
      <div className="bg-gray-800 border-b border-gray-700 p-4 sticky top-0 z-10">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Department */}
          <div>
            <label className="text-gray-500 text-xs mb-1 block">Department</label>
            <select
              value={selectedDepartment}
              onChange={(e) => setSelectedDepartment(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm min-w-[140px]"
            >
              {departments.map(d => (
                <option key={d.id} value={d.code}>{d.code}</option>
              ))}
            </select>
          </div>

          {/* Year */}
          <div>
            <label className="text-gray-500 text-xs mb-1 block">Year</label>
            <select
              value={selectedYear}
              onChange={(e) => {
                const year = parseInt(e.target.value)
                setSelectedYear(year)
                setSelectedSemester(year * 2 - 1) // Auto-map semester
              }}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm min-w-[100px]"
            >
              {years.map(y => (
                <option key={y} value={y}>{y}{y === 1 ? 'st' : y === 2 ? 'nd' : y === 3 ? 'rd' : 'th'} Year</option>
              ))}
            </select>
          </div>

          {/* Semester */}
          <div>
            <label className="text-gray-500 text-xs mb-1 block">Semester</label>
            <select
              value={selectedSemester}
              onChange={(e) => setSelectedSemester(parseInt(e.target.value))}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm min-w-[100px]"
            >
              <option value={selectedYear * 2 - 1}>Sem {selectedYear * 2 - 1}</option>
              <option value={selectedYear * 2}>Sem {selectedYear * 2}</option>
            </select>
          </div>

          {/* Section */}
          <div>
            <label className="text-gray-500 text-xs mb-1 block">Section</label>
            <select
              value={selectedSection}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm min-w-[80px]"
            >
              {sections.map(s => (
                <option key={s} value={s}>Section {s}</option>
              ))}
            </select>
          </div>

          {/* Subject/Lab Filter (Optional) */}
          <div>
            <label className="text-gray-500 text-xs mb-1 block">Subject/Lab</label>
            <select
              value={selectedSubject}
              onChange={(e) => setSelectedSubject(e.target.value)}
              className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm min-w-[140px]"
            >
              <option value="">All Subjects</option>
              {subjects.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="flex-1"></div>

          {/* Actions */}
          <button
            onClick={fetchStudents}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Visual Analytics */}
      <div className="bg-gray-800/50 border-b border-gray-700 p-4">
        <div className="flex items-center gap-6">
          {/* Total Students */}
          <div className="flex items-center gap-3 pr-6 border-r border-gray-700">
            <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="text-3xl font-bold text-white">{stats.total}</p>
              <p className="text-gray-500 text-xs">Total Students</p>
            </div>
          </div>

          {/* Active vs Inactive */}
          <div className="flex items-center gap-4 pr-6 border-r border-gray-700">
            <div className="flex items-center gap-2">
              <UserCheck className="w-5 h-5 text-emerald-400" />
              <div>
                <p className="text-xl font-bold text-white">{stats.active}</p>
                <p className="text-gray-500 text-xs">Active</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <UserX className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-xl font-bold text-white">{stats.inactive}</p>
                <p className="text-gray-500 text-xs">Inactive</p>
              </div>
            </div>
          </div>

          {/* Performance Distribution */}
          <div className="flex items-center gap-4 pr-6 border-r border-gray-700">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
              <span className="text-white font-bold">{stats.top}</span>
              <span className="text-gray-500 text-xs">Top</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-amber-500 rounded-full"></div>
              <span className="text-white font-bold">{stats.average}</span>
              <span className="text-gray-500 text-xs">Avg</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span className="text-white font-bold">{stats.weak}</span>
              <span className="text-gray-500 text-xs">Weak</span>
            </div>
          </div>

          {/* Performance Bar */}
          <div className="flex-1 max-w-xs">
            <div className="h-3 rounded-full overflow-hidden flex bg-gray-700">
              <div className="bg-emerald-500" style={{ width: `${(stats.top / stats.total) * 100}%` }}></div>
              <div className="bg-amber-500" style={{ width: `${(stats.average / stats.total) * 100}%` }}></div>
              <div className="bg-red-500" style={{ width: `${(stats.weak / stats.total) * 100}%` }}></div>
              <div className="bg-gray-500" style={{ width: `${((stats.total - stats.top - stats.average - stats.weak) / stats.total) * 100}%` }}></div>
            </div>
          </div>

          {/* Alerts */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-red-400" />
              <span className="text-red-400 font-medium text-sm">{stats.lowAttendance}</span>
              <span className="text-gray-500 text-xs">&lt;75% Att</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 bg-amber-500/10 rounded-lg">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-amber-400 font-medium text-sm">{stats.highAI}</span>
              <span className="text-gray-500 text-xs">High AI</span>
            </div>
          </div>
        </div>
      </div>

      {/* Filters & Quick Actions */}
      <div className="bg-gray-800/30 border-b border-gray-700 p-4">
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="flex-1 max-w-md relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by name or roll number..."
              className="w-full bg-gray-700 border border-gray-600 rounded-lg pl-10 pr-4 py-2 text-white placeholder-gray-500 text-sm"
            />
          </div>

          {/* Performance Filter */}
          <select
            value={performanceFilter}
            onChange={(e) => setPerformanceFilter(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm"
          >
            <option value="">All Performance</option>
            <option value="top">Top Performers</option>
            <option value="average">Average</option>
            <option value="weak">Weak</option>
            <option value="inactive">Inactive</option>
          </select>

          {/* Quick Filters */}
          <div className="flex items-center gap-2">
            <span className="text-gray-500 text-sm">Quick:</span>
            {[
              { key: 'low_attendance', label: 'Attendance <75%', icon: Calendar },
              { key: 'pending_labs', label: 'Labs Pending', icon: Code },
              { key: 'high_ai', label: 'High AI Usage', icon: Zap },
              { key: 'inactive', label: 'Inactive', icon: UserX },
            ].map((f) => (
              <button
                key={f.key}
                onClick={() => setQuickFilter(quickFilter === f.key ? '' : f.key)}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs transition-all ${
                  quickFilter === f.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                <f.icon className="w-3 h-3" />
                {f.label}
              </button>
            ))}
          </div>

          {quickFilter && (
            <button
              onClick={() => setQuickFilter('')}
              className="text-gray-400 hover:text-white text-sm"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Student Table */}
        <div className={`flex-1 overflow-auto scrollbar-hide ${showDetailPanel ? 'border-r border-gray-700' : ''}`}>
          {studentsLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          ) : filteredStudents.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Users className="w-12 h-12 mb-3" />
              <p>No students found</p>
            </div>
          ) : (
            <table className="w-full">
              <thead className="bg-gray-800 sticky top-0">
                <tr>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-xs uppercase">Roll No</th>
                  <th className="text-left px-4 py-3 text-gray-400 font-medium text-xs uppercase">Student Name</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium text-xs uppercase">Attendance</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium text-xs uppercase">Lab Progress</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium text-xs uppercase">Project</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium text-xs uppercase">AI Usage</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium text-xs uppercase">Performance</th>
                  <th className="text-center px-4 py-3 text-gray-400 font-medium text-xs uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((student) => {
                  const tag = getPerformanceTag(student.performance_tier)
                  return (
                    <tr
                      key={student.id}
                      onClick={() => fetchStudentDetail(student.id)}
                      className={`border-b border-gray-700/50 hover:bg-gray-800/50 cursor-pointer transition-colors ${
                        selectedStudent?.id === student.id ? 'bg-gray-800' : ''
                      }`}
                    >
                      <td className="px-4 py-3">
                        <span className="text-white font-mono text-sm">{student.roll_number}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                            <span className="text-white font-medium text-sm">{student.name.charAt(0)}</span>
                          </div>
                          <div>
                            <p className="text-white font-medium text-sm">{student.name}</p>
                            <p className="text-gray-500 text-xs">{student.guide_name || 'No guide'}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-medium ${getAttendanceColor(student.attendance_percent)}`}>
                          {student.attendance_percent}%
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden max-w-[80px]">
                            <div
                              className={`h-full rounded-full ${getProgressBarColor(student.lab_completion_percent)}`}
                              style={{ width: `${student.lab_completion_percent}%` }}
                            ></div>
                          </div>
                          <span className="text-white text-sm w-10">{student.lab_completion_percent}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded text-xs ${
                          student.project_status === 'Not Started' ? 'bg-gray-500/20 text-gray-400' :
                          student.project_status.includes('3') ? 'bg-emerald-500/20 text-emerald-400' :
                          'bg-blue-500/20 text-blue-400'
                        }`}>
                          {student.project_status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-medium ${
                          student.ai_usage_percent > 50 ? 'text-red-400' :
                          student.ai_usage_percent > 30 ? 'text-amber-400' :
                          'text-emerald-400'
                        }`}>
                          {student.ai_usage_percent}%
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${tag.color}`}>
                          {tag.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <div className="flex items-center justify-center gap-1">
                          <button
                            onClick={(e) => { e.stopPropagation(); fetchStudentDetail(student.id); }}
                            className="p-1.5 text-gray-400 hover:text-blue-400 hover:bg-blue-500/10 rounded"
                            title="View Profile"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => e.stopPropagation()}
                            className="p-1.5 text-gray-400 hover:text-amber-400 hover:bg-amber-500/10 rounded"
                            title="Send Reminder"
                          >
                            <Bell className="w-4 h-4" />
                          </button>
                          <button
                            onClick={(e) => e.stopPropagation()}
                            className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded"
                            title="Flag for HOD"
                          >
                            <Flag className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* Student Detail Slide Panel */}
        {showDetailPanel && (
          <div className="w-[450px] bg-gray-800 flex flex-col shrink-0">
            {/* Panel Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-white font-semibold">Student Profile</h3>
              <button
                onClick={() => { setShowDetailPanel(false); setSelectedStudent(null); }}
                className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-700 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {detailLoading ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
              </div>
            ) : selectedStudent ? (
              <>
                {/* Student Header */}
                <div className="p-4 border-b border-gray-700">
                  <div className="flex items-start gap-4">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center">
                      <span className="text-white text-2xl font-bold">{selectedStudent.full_name.charAt(0)}</span>
                    </div>
                    <div className="flex-1">
                      <h4 className="text-white text-lg font-semibold">{selectedStudent.full_name}</h4>
                      <p className="text-gray-400 text-sm">{selectedStudent.roll_number}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          selectedStudent.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'
                        }`}>
                          {selectedStudent.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <span className="text-gray-500 text-xs">
                          Sem {selectedStudent.semester} | Sec {selectedStudent.section}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Quick Contact */}
                  <div className="flex items-center gap-4 mt-4">
                    <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">
                      <Mail className="w-4 h-4" />
                      Email
                    </button>
                    <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm">
                      <Send className="w-4 h-4" />
                      Reminder
                    </button>
                  </div>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-700">
                  {[
                    { key: 'overview', label: 'Overview', icon: Target },
                    { key: 'attendance', label: 'Attendance', icon: Calendar },
                    { key: 'progress', label: 'Progress', icon: TrendingUp },
                    { key: 'project', label: 'Project', icon: FileText },
                    { key: 'activity', label: 'Activity', icon: Activity },
                  ].map((tab) => (
                    <button
                      key={tab.key}
                      onClick={() => setDetailTab(tab.key as any)}
                      className={`flex-1 flex items-center justify-center gap-1 px-2 py-3 text-xs font-medium transition-colors ${
                        detailTab === tab.key
                          ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-500/5'
                          : 'text-gray-400 hover:text-white'
                      }`}
                    >
                      <tab.icon className="w-3.5 h-3.5" />
                      {tab.label}
                    </button>
                  ))}
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-y-auto scrollbar-hide p-4">
                  {/* Overview Tab */}
                  {detailTab === 'overview' && (
                    <div className="space-y-4">
                      {/* Quick Stats */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-700/50 rounded-lg p-3">
                          <p className="text-gray-500 text-xs">Attendance</p>
                          <p className={`text-2xl font-bold ${getAttendanceColor(selectedStudent.attendance.overall)}`}>
                            {selectedStudent.attendance.overall}%
                          </p>
                        </div>
                        <div className="bg-gray-700/50 rounded-lg p-3">
                          <p className="text-gray-500 text-xs">Lab Progress</p>
                          <p className="text-2xl font-bold text-white">{selectedStudent.learning_progress.lab_completion}%</p>
                        </div>
                        <div className="bg-gray-700/50 rounded-lg p-3">
                          <p className="text-gray-500 text-xs">Pending Labs</p>
                          <p className={`text-2xl font-bold ${selectedStudent.learning_progress.pending_labs.length > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                            {selectedStudent.learning_progress.pending_labs.length}
                          </p>
                        </div>
                        <div className="bg-gray-700/50 rounded-lg p-3">
                          <p className="text-gray-500 text-xs">Missed Deadlines</p>
                          <p className={`text-2xl font-bold ${selectedStudent.learning_progress.missed_deadlines > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                            {selectedStudent.learning_progress.missed_deadlines}
                          </p>
                        </div>
                      </div>

                      {/* Basic Info */}
                      <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
                        <h5 className="text-white font-medium text-sm">Basic Information</h5>
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <p className="text-gray-500 text-xs">Email</p>
                            <p className="text-white">{selectedStudent.email}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Phone</p>
                            <p className="text-white">{selectedStudent.phone || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Guide</p>
                            <p className="text-white">{selectedStudent.guide_name || 'Not Assigned'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs">Batch</p>
                            <p className="text-white">{selectedStudent.batch}</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Attendance Tab */}
                  {detailTab === 'attendance' && (
                    <div className="space-y-4">
                      {/* Overall */}
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-white font-medium text-sm">Overall Attendance</h5>
                          <span className={`text-2xl font-bold ${getAttendanceColor(selectedStudent.attendance.overall)}`}>
                            {selectedStudent.attendance.overall}%
                          </span>
                        </div>
                        <div className="h-3 bg-gray-600 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${getProgressBarColor(selectedStudent.attendance.overall)}`}
                            style={{ width: `${selectedStudent.attendance.overall}%` }}
                          ></div>
                        </div>
                        <p className="text-gray-500 text-xs mt-2">
                          {selectedStudent.attendance.overall >= 75 ? '✓ Eligible for exams' : '⚠ Below minimum requirement'}
                        </p>
                      </div>

                      {/* Subject-wise */}
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <h5 className="text-white font-medium text-sm mb-3">Subject-wise Attendance</h5>
                        <div className="space-y-3">
                          {selectedStudent.attendance.subject_wise.map((sub, i) => (
                            <div key={i}>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-gray-400 text-sm">{sub.subject}</span>
                                <span className={`font-medium text-sm ${getAttendanceColor(sub.percent)}`}>{sub.percent}%</span>
                              </div>
                              <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${getProgressBarColor(sub.percent)}`}
                                  style={{ width: `${sub.percent}%` }}
                                ></div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Monthly Trend */}
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <h5 className="text-white font-medium text-sm mb-3">Monthly Trend</h5>
                        <div className="flex items-end justify-between h-24 gap-2">
                          {selectedStudent.attendance.monthly_trend.map((m, i) => (
                            <div key={i} className="flex-1 flex flex-col items-center">
                              <div
                                className={`w-full rounded-t ${getProgressBarColor(m.percent)}`}
                                style={{ height: `${m.percent}%` }}
                              ></div>
                              <span className="text-gray-500 text-xs mt-1">{m.month}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Progress Tab */}
                  {detailTab === 'progress' && (
                    <div className="space-y-4">
                      {/* Theory & Lab */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-700/50 rounded-lg p-4">
                          <p className="text-gray-500 text-xs mb-2">Theory Completion</p>
                          <p className="text-2xl font-bold text-white mb-2">{selectedStudent.learning_progress.theory_completion}%</p>
                          <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${selectedStudent.learning_progress.theory_completion}%` }}></div>
                          </div>
                        </div>
                        <div className="bg-gray-700/50 rounded-lg p-4">
                          <p className="text-gray-500 text-xs mb-2">Lab Completion</p>
                          <p className="text-2xl font-bold text-white mb-2">{selectedStudent.learning_progress.lab_completion}%</p>
                          <div className="h-2 bg-gray-600 rounded-full overflow-hidden">
                            <div className={`h-full rounded-full ${getProgressBarColor(selectedStudent.learning_progress.lab_completion)}`} style={{ width: `${selectedStudent.learning_progress.lab_completion}%` }}></div>
                          </div>
                        </div>
                      </div>

                      {/* Lab Enrollments */}
                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <h5 className="text-white font-medium text-sm mb-3">Lab Progress</h5>
                        <div className="space-y-3">
                          {selectedStudent.lab_enrollments.map((lab) => (
                            <div key={lab.lab_id} className="bg-gray-800/50 rounded-lg p-3">
                              <div className="flex items-center justify-between mb-2">
                                <div>
                                  <p className="text-white font-medium text-sm">{lab.lab_name}</p>
                                  <p className="text-gray-500 text-xs">{lab.lab_code}</p>
                                </div>
                                {lab.rank && (
                                  <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded text-xs">
                                    Rank #{lab.rank}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3">
                                <div className="flex-1 h-2 bg-gray-600 rounded-full overflow-hidden">
                                  <div className={`h-full rounded-full ${getProgressBarColor(lab.progress)}`} style={{ width: `${lab.progress}%` }}></div>
                                </div>
                                <span className="text-white text-sm w-12">{lab.progress}%</span>
                                <span className="text-gray-500 text-sm">Score: {lab.score}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Pending Labs */}
                      {selectedStudent.learning_progress.pending_labs.length > 0 && (
                        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                          <h5 className="text-amber-400 font-medium text-sm mb-2 flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4" />
                            Pending Labs
                          </h5>
                          <ul className="space-y-1">
                            {selectedStudent.learning_progress.pending_labs.map((lab, i) => (
                              <li key={i} className="text-gray-300 text-sm">• {lab}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Project Tab */}
                  {detailTab === 'project' && (
                    <div className="space-y-4">
                      {selectedStudent.project ? (
                        <>
                          <div className="bg-gray-700/50 rounded-lg p-4">
                            <h5 className="text-white font-medium mb-2">{selectedStudent.project.title}</h5>
                            <p className="text-gray-400 text-sm">Guide: {selectedStudent.project.guide_name}</p>
                            <div className="flex items-center gap-2 mt-3">
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                selectedStudent.project.is_approved ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                              }`}>
                                {selectedStudent.project.is_approved ? 'Approved' : 'Pending Approval'}
                              </span>
                              <span className="px-2 py-1 bg-blue-500/20 text-blue-400 rounded text-xs font-medium">
                                {selectedStudent.project.current_phase}
                              </span>
                            </div>
                          </div>

                          <div className="grid grid-cols-2 gap-3">
                            <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                              <p className="text-gray-500 text-xs">Plagiarism</p>
                              <p className={`text-xl font-bold ${selectedStudent.project.plagiarism_score > 30 ? 'text-red-400' : 'text-emerald-400'}`}>
                                {selectedStudent.project.plagiarism_score}%
                              </p>
                            </div>
                            <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                              <p className="text-gray-500 text-xs">AI Detection</p>
                              <p className={`text-xl font-bold ${selectedStudent.project.ai_detection_score > 50 ? 'text-red-400' : selectedStudent.project.ai_detection_score > 30 ? 'text-amber-400' : 'text-emerald-400'}`}>
                                {selectedStudent.project.ai_detection_score}%
                              </p>
                            </div>
                          </div>

                          {selectedStudent.project.next_review_date && (
                            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                              <p className="text-blue-400 text-sm font-medium">Next Review</p>
                              <p className="text-white">{new Date(selectedStudent.project.next_review_date).toLocaleDateString()}</p>
                            </div>
                          )}

                          {selectedStudent.project.reviewer_comments && (
                            <div className="bg-gray-700/50 rounded-lg p-4">
                              <p className="text-gray-500 text-xs mb-2">Reviewer Comments</p>
                              <p className="text-gray-300 text-sm">{selectedStudent.project.reviewer_comments}</p>
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="text-center py-8 text-gray-500">
                          <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                          <p>No project assigned</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Activity Tab */}
                  {detailTab === 'activity' && (
                    <div className="space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                          <p className="text-gray-500 text-xs mb-1">Login Frequency</p>
                          <p className="text-2xl font-bold text-white">{selectedStudent.activity.login_frequency}</p>
                          <p className="text-gray-500 text-xs">times/week</p>
                        </div>
                        <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                          <p className="text-gray-500 text-xs mb-1">Time Spent</p>
                          <p className="text-2xl font-bold text-white">{selectedStudent.activity.time_spent_hours}</p>
                          <p className="text-gray-500 text-xs">hours/week</p>
                        </div>
                      </div>

                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <p className="text-gray-500 text-sm">Coding Activity Level</p>
                          <span className={`px-3 py-1 rounded-lg text-sm font-medium ${
                            selectedStudent.activity.coding_activity_level === 'High' ? 'bg-emerald-500/20 text-emerald-400' :
                            selectedStudent.activity.coding_activity_level === 'Medium' ? 'bg-amber-500/20 text-amber-400' :
                            selectedStudent.activity.coding_activity_level === 'Low' ? 'bg-red-500/20 text-red-400' :
                            'bg-gray-500/20 text-gray-400'
                          }`}>
                            {selectedStudent.activity.coding_activity_level}
                          </span>
                        </div>
                      </div>

                      <div className="bg-gray-700/50 rounded-lg p-4">
                        <div className="flex items-center justify-between">
                          <p className="text-gray-500 text-sm">Last Active</p>
                          <p className="text-white text-sm">
                            {selectedStudent.activity.last_active !== 'N/A'
                              ? new Date(selectedStudent.activity.last_active).toLocaleDateString()
                              : 'N/A'}
                          </p>
                        </div>
                      </div>

                      {!selectedStudent.is_active && (
                        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                          <p className="text-red-400 text-sm font-medium flex items-center gap-2">
                            <AlertTriangle className="w-4 h-4" />
                            Student Inactive
                          </p>
                          <p className="text-gray-400 text-xs mt-1">No activity in last 15 days</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Quick Actions Footer */}
                <div className="p-4 border-t border-gray-700 flex gap-2">
                  <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm">
                    <Bell className="w-4 h-4" />
                    Send Reminder
                  </button>
                  <button className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm">
                    <Flag className="w-4 h-4" />
                    Flag for HOD
                  </button>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <p>Select a student to view details</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
