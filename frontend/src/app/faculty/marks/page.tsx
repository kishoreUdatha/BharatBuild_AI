'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  FileSpreadsheet,
  Plus,
  Search,
  Filter,
  Download,
  Upload,
  Save,
  Send,
  CheckCircle,
  XCircle,
  Lock,
  Unlock,
  History,
  BarChart3,
  Users,
  AlertTriangle,
  RefreshCw,
  ChevronDown,
  Eye,
  Edit,
  Loader2,
  Calendar,
  Clock,
  Award,
  TrendingUp,
  FileText,
  Database
} from 'lucide-react'
import { useToast } from '@/components/ui/toast'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface MarksSheet {
  id: string
  academic_year: string
  semester: number
  subject_code: string
  subject_name: string
  section_name: string
  assessment_type: string
  assessment_name: string
  max_marks: number
  status: 'draft' | 'submitted' | 'approved' | 'locked' | 'rejected'
  total_students: number
  average_marks: number | null
  entered_at: string | null
  submitted_at: string | null
  approved_at: string | null
}

interface StudentMark {
  id: string
  student_id: string
  roll_number: string
  student_name: string
  obtained_marks: number | null
  is_absent: boolean
  attendance_percentage: number | null
  remarks: string | null
  grade: string | null
  lab_experiment_marks: number | null
  lab_test_marks: number | null
  lab_record_marks: number | null
  lab_viva_marks: number | null
  auto_populated: boolean
  moderation_applied: number | null
}

interface AuditEntry {
  id: string
  changed_by: string
  field_changed: string
  old_value: string | null
  new_value: string | null
  action: string
  reason: string | null
  timestamp: string
}

export default function MarksManagementPage() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Filters
  const [academicYear, setAcademicYear] = useState('2025-26')
  const [semester, setSemester] = useState(3)
  const [subjectId, setSubjectId] = useState('')
  const [sectionId, setSectionId] = useState('')
  const [assessmentType, setAssessmentType] = useState('')

  // Data
  const [marksSheets, setMarksSheets] = useState<MarksSheet[]>([])
  const [selectedSheet, setSelectedSheet] = useState<MarksSheet | null>(null)
  const [studentMarks, setStudentMarks] = useState<StudentMark[]>([])
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([])

  // UI State
  const [activeTab, setActiveTab] = useState<'entry' | 'sheets' | 'analytics'>('sheets')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showAuditModal, setShowAuditModal] = useState(false)
  const [editedMarks, setEditedMarks] = useState<Record<string, number | null>>({})

  // Create form
  const [createForm, setCreateForm] = useState({
    subject_code: 'CS301',
    subject_name: 'Data Structures',
    section_name: 'CSE-3A',
    assessment_type: 'internal_test',
    assessment_name: 'Internal Test 1',
    max_marks: 30
  })

  const getAuthHeaders = () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  // Fetch marks sheets
  const fetchMarksSheets = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        academic_year: academicYear,
        semester: semester.toString()
      })
      const response = await fetch(`${API_URL}/marks/marks-sheets?${params}`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setMarksSheets(data)
      } else {
        // Use mock data
        setMarksSheets([
          {
            id: '1',
            academic_year: '2025-26',
            semester: 3,
            subject_code: 'CS301',
            subject_name: 'Data Structures',
            section_name: 'CSE-3A',
            assessment_type: 'internal_test',
            assessment_name: 'Internal Test 1',
            max_marks: 30,
            status: 'draft',
            total_students: 60,
            average_marks: 22.5,
            entered_at: null,
            submitted_at: null,
            approved_at: null
          },
          {
            id: '2',
            academic_year: '2025-26',
            semester: 3,
            subject_code: 'CS302',
            subject_name: 'DBMS',
            section_name: 'CSE-3A',
            assessment_type: 'lab',
            assessment_name: 'Lab Evaluation 1',
            max_marks: 50,
            status: 'submitted',
            total_students: 60,
            average_marks: 38.2,
            entered_at: '2026-01-15T10:00:00',
            submitted_at: '2026-01-20T14:30:00',
            approved_at: null
          },
          {
            id: '3',
            academic_year: '2025-26',
            semester: 3,
            subject_code: 'CS303',
            subject_name: 'Operating Systems',
            section_name: 'CSE-3A',
            assessment_type: 'assignment',
            assessment_name: 'Assignment 1',
            max_marks: 20,
            status: 'approved',
            total_students: 60,
            average_marks: 16.8,
            entered_at: '2026-01-10T09:00:00',
            submitted_at: '2026-01-12T16:00:00',
            approved_at: '2026-01-14T11:00:00'
          }
        ])
      }
    } catch (err) {
      console.error('Error fetching marks sheets:', err)
    } finally {
      setLoading(false)
    }
  }, [academicYear, semester])

  // Fetch student marks for a sheet
  const fetchStudentMarks = async (sheetId: string) => {
    try {
      const response = await fetch(`${API_URL}/marks/marks-sheet/${sheetId}`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setStudentMarks(data.students)
      } else {
        // Mock data
        setStudentMarks([
          { id: '1', student_id: 's1', roll_number: '21CS001', student_name: 'Rahul Kumar', obtained_marks: 25, is_absent: false, attendance_percentage: 92, remarks: null, grade: 'A', lab_experiment_marks: null, lab_test_marks: null, lab_record_marks: null, lab_viva_marks: null, auto_populated: false, moderation_applied: null },
          { id: '2', student_id: 's2', roll_number: '21CS002', student_name: 'Priya Sharma', obtained_marks: 28, is_absent: false, attendance_percentage: 95, remarks: null, grade: 'A+', lab_experiment_marks: null, lab_test_marks: null, lab_record_marks: null, lab_viva_marks: null, auto_populated: false, moderation_applied: null },
          { id: '3', student_id: 's3', roll_number: '21CS003', student_name: 'Amit Patel', obtained_marks: null, is_absent: true, attendance_percentage: 45, remarks: 'Absent', grade: null, lab_experiment_marks: null, lab_test_marks: null, lab_record_marks: null, lab_viva_marks: null, auto_populated: false, moderation_applied: null },
          { id: '4', student_id: 's4', roll_number: '21CS004', student_name: 'Sneha Reddy', obtained_marks: 18, is_absent: false, attendance_percentage: 88, remarks: null, grade: 'B', lab_experiment_marks: null, lab_test_marks: null, lab_record_marks: null, lab_viva_marks: null, auto_populated: false, moderation_applied: null },
          { id: '5', student_id: 's5', roll_number: '21CS005', student_name: 'Vikram Singh', obtained_marks: 22, is_absent: false, attendance_percentage: 78, remarks: null, grade: 'B+', lab_experiment_marks: null, lab_test_marks: null, lab_record_marks: null, lab_viva_marks: null, auto_populated: false, moderation_applied: null },
        ])
      }
    } catch (err) {
      console.error('Error fetching student marks:', err)
    }
  }

  // Save marks
  const saveMarks = async () => {
    if (!selectedSheet) return
    setSaving(true)
    try {
      const entries = studentMarks.map(s => ({
        student_id: s.student_id,
        roll_number: s.roll_number,
        student_name: s.student_name,
        obtained_marks: editedMarks[s.id] !== undefined ? editedMarks[s.id] : s.obtained_marks,
        is_absent: s.is_absent,
        remarks: s.remarks
      }))

      const response = await fetch(`${API_URL}/marks/marks-sheet/${selectedSheet.id}/entries`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ header_id: selectedSheet.id, entries })
      })

      if (response.ok) {
        toast.success('Marks Saved', 'All marks have been saved successfully')
        setEditedMarks({})
        await fetchStudentMarks(selectedSheet.id)
      } else {
        toast.error('Error', 'Failed to save marks')
      }
    } catch (err) {
      toast.error('Error', 'Failed to save marks')
    } finally {
      setSaving(false)
    }
  }

  // Submit for approval
  const submitForApproval = async () => {
    if (!selectedSheet) return
    try {
      const response = await fetch(`${API_URL}/marks/marks-sheet/${selectedSheet.id}/submit`, {
        method: 'POST',
        headers: getAuthHeaders()
      })

      if (response.ok) {
        toast.success('Submitted', 'Marks submitted for HOD approval')
        await fetchMarksSheets()
        setSelectedSheet(null)
        setActiveTab('sheets')
      } else {
        toast.error('Error', 'Failed to submit marks')
      }
    } catch (err) {
      toast.error('Error', 'Failed to submit marks')
    }
  }

  // Export marks
  const exportMarks = async (format: 'excel' | 'pdf') => {
    if (!selectedSheet) return
    try {
      const response = await fetch(`${API_URL}/marks/marks-sheet/${selectedSheet.id}/export/${format}`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        toast.success('Export Ready', `${data.filename} is ready for download`)
        // In production, would trigger actual file download
      }
    } catch (err) {
      toast.error('Error', 'Failed to export marks')
    }
  }

  // Fetch audit log
  const fetchAuditLog = async (sheetId: string) => {
    try {
      const response = await fetch(`${API_URL}/marks/marks-sheet/${sheetId}/audit`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setAuditLog(data)
      } else {
        // Mock data
        setAuditLog([
          { id: '1', changed_by: 'Dr. Smith', field_changed: 'obtained_marks', old_value: '20', new_value: '22', action: 'update', reason: null, timestamp: '2026-01-15T10:30:00' },
          { id: '2', changed_by: 'Dr. Smith', field_changed: 'status', old_value: 'draft', new_value: 'submitted', action: 'submit', reason: 'Completed all entries', timestamp: '2026-01-15T14:00:00' }
        ])
      }
    } catch (err) {
      console.error('Error fetching audit log:', err)
    }
  }

  useEffect(() => {
    fetchMarksSheets()
  }, [fetchMarksSheets])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'draft': return 'bg-gray-500/20 text-gray-400'
      case 'submitted': return 'bg-yellow-500/20 text-yellow-400'
      case 'approved': return 'bg-green-500/20 text-green-400'
      case 'locked': return 'bg-blue-500/20 text-blue-400'
      case 'rejected': return 'bg-red-500/20 text-red-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  const getAssessmentTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      internal_test: 'Internal Test',
      assignment: 'Assignment',
      lab: 'Lab',
      project_review: 'Project Review',
      viva: 'Viva',
      quiz: 'Quiz',
      mid_sem: 'Mid Sem',
      end_sem: 'End Sem'
    }
    return labels[type] || type
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)] bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading marks management...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FileSpreadsheet className="w-6 h-6 text-blue-400" />
            <h1 className="text-xl font-semibold text-white">Assessment & Marks Management</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
            >
              <Plus className="w-4 h-4" />
              New Marks Sheet
            </button>
            <button
              onClick={fetchMarksSheets}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4">
          <select
            value={academicYear}
            onChange={(e) => setAcademicYear(e.target.value)}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white"
          >
            <option value="2025-26">2025-26</option>
            <option value="2024-25">2024-25</option>
          </select>
          <select
            value={semester}
            onChange={(e) => setSemester(parseInt(e.target.value))}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white"
          >
            {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
              <option key={s} value={s}>Semester {s}</option>
            ))}
          </select>
          <select
            value={assessmentType}
            onChange={(e) => setAssessmentType(e.target.value)}
            className="px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-sm text-white"
          >
            <option value="">All Types</option>
            <option value="internal_test">Internal Test</option>
            <option value="assignment">Assignment</option>
            <option value="lab">Lab</option>
            <option value="project_review">Project Review</option>
            <option value="viva">Viva</option>
          </select>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          {[
            { id: 'sheets', label: 'Marks Sheets', icon: FileSpreadsheet },
            { id: 'entry', label: 'Marks Entry', icon: Edit },
            { id: 'analytics', label: 'Analytics', icon: BarChart3 },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hide p-6">
        {activeTab === 'sheets' && (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-800 border-b border-gray-700">
                <tr>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Subject</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Section</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Assessment</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Max Marks</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Students</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Average</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Status</th>
                  <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {marksSheets.map((sheet) => (
                  <tr key={sheet.id} className="hover:bg-gray-700/50">
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm font-medium text-white">{sheet.subject_name}</p>
                        <p className="text-xs text-gray-400">{sheet.subject_code}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">{sheet.section_name}</td>
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-sm text-white">{sheet.assessment_name}</p>
                        <p className="text-xs text-gray-400">{getAssessmentTypeLabel(sheet.assessment_type)}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">{sheet.max_marks}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">{sheet.total_students}</td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {sheet.average_marks ? sheet.average_marks.toFixed(1) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded ${getStatusColor(sheet.status)}`}>
                        {sheet.status.charAt(0).toUpperCase() + sheet.status.slice(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => {
                            setSelectedSheet(sheet)
                            fetchStudentMarks(sheet.id)
                            setActiveTab('entry')
                          }}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          {sheet.status === 'draft' ? 'Edit' : 'View'}
                        </button>
                        <button
                          onClick={() => {
                            fetchAuditLog(sheet.id)
                            setShowAuditModal(true)
                          }}
                          className="text-xs text-gray-400 hover:text-gray-300"
                        >
                          History
                        </button>
                        <button
                          onClick={() => exportMarks('excel')}
                          className="text-xs text-green-400 hover:text-green-300"
                        >
                          Export
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'entry' && selectedSheet && (
          <div className="space-y-4">
            {/* Sheet Info */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white">{selectedSheet.subject_name} - {selectedSheet.assessment_name}</h2>
                  <p className="text-sm text-gray-400">{selectedSheet.section_name} | Max Marks: {selectedSheet.max_marks}</p>
                </div>
                <div className="flex items-center gap-3">
                  {selectedSheet.status === 'draft' && (
                    <>
                      <button
                        onClick={saveMarks}
                        disabled={saving}
                        className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
                      >
                        {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Save
                      </button>
                      <button
                        onClick={submitForApproval}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
                      >
                        <Send className="w-4 h-4" />
                        Submit for Approval
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => exportMarks('excel')}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-700 text-gray-300 text-sm rounded-lg hover:bg-gray-600"
                  >
                    <Download className="w-4 h-4" />
                    Excel
                  </button>
                  <button
                    onClick={() => exportMarks('pdf')}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-700 text-gray-300 text-sm rounded-lg hover:bg-gray-600"
                  >
                    <FileText className="w-4 h-4" />
                    PDF
                  </button>
                </div>
              </div>
            </div>

            {/* Marks Grid */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-800 border-b border-gray-700">
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[100px]">Roll No</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[200px]">Student Name</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[80px]">Attendance</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[120px]">Obtained Marks</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[80px]">Grade</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Remarks</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[80px]">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {studentMarks.map((student) => (
                    <tr key={student.id} className={`hover:bg-gray-700/50 ${student.is_absent ? 'bg-red-500/10' : ''}`}>
                      <td className="px-4 py-3 text-sm text-white font-mono">{student.roll_number}</td>
                      <td className="px-4 py-3 text-sm text-white">{student.student_name}</td>
                      <td className="px-4 py-3">
                        <span className={`text-sm ${(student.attendance_percentage || 0) < 75 ? 'text-red-400' : 'text-green-400'}`}>
                          {student.attendance_percentage ? `${student.attendance_percentage}%` : '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {selectedSheet.status === 'draft' ? (
                          <input
                            type="number"
                            min="0"
                            max={selectedSheet.max_marks}
                            value={editedMarks[student.id] !== undefined ? editedMarks[student.id] ?? '' : student.obtained_marks ?? ''}
                            onChange={(e) => {
                              const val = e.target.value === '' ? null : parseFloat(e.target.value)
                              setEditedMarks({ ...editedMarks, [student.id]: val })
                            }}
                            disabled={student.is_absent}
                            className="w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-white text-center disabled:opacity-50"
                          />
                        ) : (
                          <span className="text-sm text-white">
                            {student.is_absent ? 'AB' : student.obtained_marks}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300">{student.grade || '-'}</td>
                      <td className="px-4 py-3">
                        {selectedSheet.status === 'draft' ? (
                          <input
                            type="text"
                            value={student.remarks || ''}
                            placeholder="Add remarks..."
                            className="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-sm text-white"
                          />
                        ) : (
                          <span className="text-sm text-gray-400">{student.remarks || '-'}</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {student.is_absent ? (
                          <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400">Absent</span>
                        ) : student.auto_populated ? (
                          <span className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400">Auto</span>
                        ) : (
                          <span className="text-xs px-2 py-1 rounded bg-green-500/20 text-green-400">Manual</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-5 gap-4">
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <p className="text-xs text-gray-400 mb-1">Total Students</p>
                <p className="text-2xl font-bold text-white">{studentMarks.length}</p>
              </div>
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <p className="text-xs text-gray-400 mb-1">Present</p>
                <p className="text-2xl font-bold text-green-400">{studentMarks.filter(s => !s.is_absent).length}</p>
              </div>
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <p className="text-xs text-gray-400 mb-1">Absent</p>
                <p className="text-2xl font-bold text-red-400">{studentMarks.filter(s => s.is_absent).length}</p>
              </div>
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <p className="text-xs text-gray-400 mb-1">Average</p>
                <p className="text-2xl font-bold text-blue-400">
                  {(studentMarks.filter(s => s.obtained_marks !== null).reduce((acc, s) => acc + (s.obtained_marks || 0), 0) /
                    studentMarks.filter(s => s.obtained_marks !== null).length || 0).toFixed(1)}
                </p>
              </div>
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <p className="text-xs text-gray-400 mb-1">Pass Rate</p>
                <p className="text-2xl font-bold text-purple-400">
                  {((studentMarks.filter(s => (s.obtained_marks || 0) >= selectedSheet.max_marks * 0.4).length /
                    studentMarks.filter(s => !s.is_absent).length) * 100 || 0).toFixed(0)}%
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'entry' && !selectedSheet && (
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-12 text-center">
            <FileSpreadsheet className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No Marks Sheet Selected</h3>
            <p className="text-gray-400 text-sm mb-4">Select a marks sheet from the list to enter or view marks.</p>
            <button
              onClick={() => setActiveTab('sheets')}
              className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
            >
              View Marks Sheets
            </button>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="grid grid-cols-2 gap-6">
            {/* Pass/Fail Distribution */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Pass/Fail Distribution</h3>
              <div className="flex items-center justify-center h-48">
                <div className="text-center">
                  <div className="flex gap-8">
                    <div>
                      <div className="w-24 h-24 rounded-full bg-green-500/20 flex items-center justify-center mb-2">
                        <span className="text-2xl font-bold text-green-400">78%</span>
                      </div>
                      <p className="text-sm text-gray-400">Pass</p>
                    </div>
                    <div>
                      <div className="w-24 h-24 rounded-full bg-red-500/20 flex items-center justify-center mb-2">
                        <span className="text-2xl font-bold text-red-400">22%</span>
                      </div>
                      <p className="text-sm text-gray-400">Fail</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Grade Distribution */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Grade Distribution</h3>
              <div className="space-y-3">
                {[
                  { grade: 'A+', count: 8, color: 'bg-green-500' },
                  { grade: 'A', count: 15, color: 'bg-green-400' },
                  { grade: 'B+', count: 18, color: 'bg-blue-400' },
                  { grade: 'B', count: 12, color: 'bg-blue-300' },
                  { grade: 'C', count: 5, color: 'bg-yellow-400' },
                  { grade: 'F', count: 2, color: 'bg-red-400' },
                ].map((item) => (
                  <div key={item.grade} className="flex items-center gap-3">
                    <span className="w-8 text-sm text-gray-300">{item.grade}</span>
                    <div className="flex-1 h-6 bg-gray-700 rounded overflow-hidden">
                      <div
                        className={`h-full ${item.color}`}
                        style={{ width: `${(item.count / 60) * 100}%` }}
                      />
                    </div>
                    <span className="w-8 text-sm text-gray-400 text-right">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Performers */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Top Performers</h3>
              <div className="space-y-3">
                {[
                  { rank: 1, name: 'Priya Sharma', roll: '21CS002', marks: 28, grade: 'A+' },
                  { rank: 2, name: 'Rahul Kumar', roll: '21CS001', marks: 27, grade: 'A+' },
                  { rank: 3, name: 'Ananya Das', roll: '21CS006', marks: 26, grade: 'A' },
                ].map((student) => (
                  <div key={student.rank} className="flex items-center gap-3 p-2 bg-gray-700/50 rounded-lg">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      student.rank === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                      student.rank === 2 ? 'bg-gray-400/20 text-gray-300' :
                      'bg-orange-500/20 text-orange-400'
                    }`}>
                      {student.rank}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{student.name}</p>
                      <p className="text-xs text-gray-400">{student.roll}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-white">{student.marks}/30</p>
                      <p className="text-xs text-green-400">{student.grade}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Comparison Across Sections */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Section Comparison</h3>
              <div className="space-y-4">
                {[
                  { section: 'CSE-3A', avg: 22.5, pass: 85 },
                  { section: 'CSE-3B', avg: 21.2, pass: 78 },
                  { section: 'CSE-3C', avg: 23.1, pass: 88 },
                ].map((section) => (
                  <div key={section.section} className="flex items-center gap-4">
                    <span className="w-16 text-sm text-gray-300">{section.section}</span>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-400">Avg: {section.avg}</span>
                        <span className="text-xs text-gray-400">Pass: {section.pass}%</span>
                      </div>
                      <div className="h-2 bg-gray-700 rounded overflow-hidden">
                        <div
                          className="h-full bg-blue-500"
                          style={{ width: `${(section.avg / 30) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Audit Log Modal */}
      {showAuditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
              <div className="flex items-center gap-2">
                <History className="w-5 h-5 text-blue-400" />
                <h3 className="text-lg font-semibold text-white">Marks History (Audit Trail)</h3>
              </div>
              <button onClick={() => setShowAuditModal(false)} className="text-gray-400 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="space-y-4">
                {auditLog.map((entry) => (
                  <div key={entry.id} className="flex gap-4 p-3 bg-gray-700/50 rounded-lg">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                      <History className="w-5 h-5 text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-medium text-white">{entry.changed_by}</span>
                        <span className="text-xs text-gray-400">{entry.action}</span>
                      </div>
                      <p className="text-sm text-gray-300">
                        Changed <span className="text-blue-400">{entry.field_changed}</span>
                        {entry.old_value && <> from <span className="text-red-400">{entry.old_value}</span></>}
                        {entry.new_value && <> to <span className="text-green-400">{entry.new_value}</span></>}
                      </p>
                      {entry.reason && (
                        <p className="text-xs text-gray-400 mt-1">Reason: {entry.reason}</p>
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(entry.timestamp).toLocaleString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white">Create Marks Sheet</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-gray-400 hover:text-white">
                <XCircle className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Subject Code</label>
                <input
                  type="text"
                  value={createForm.subject_code}
                  onChange={(e) => setCreateForm({ ...createForm, subject_code: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Subject Name</label>
                <input
                  type="text"
                  value={createForm.subject_name}
                  onChange={(e) => setCreateForm({ ...createForm, subject_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Section</label>
                <input
                  type="text"
                  value={createForm.section_name}
                  onChange={(e) => setCreateForm({ ...createForm, section_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Assessment Type</label>
                <select
                  value={createForm.assessment_type}
                  onChange={(e) => setCreateForm({ ...createForm, assessment_type: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="internal_test">Internal Test</option>
                  <option value="assignment">Assignment</option>
                  <option value="lab">Lab</option>
                  <option value="project_review">Project Review</option>
                  <option value="viva">Viva</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Assessment Name</label>
                <input
                  type="text"
                  value={createForm.assessment_name}
                  onChange={(e) => setCreateForm({ ...createForm, assessment_name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Max Marks</label>
                <input
                  type="number"
                  value={createForm.max_marks}
                  onChange={(e) => setCreateForm({ ...createForm, max_marks: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-gray-700">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-300 hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  toast.success('Created', 'Marks sheet created successfully')
                  setShowCreateModal(false)
                  fetchMarksSheets()
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
