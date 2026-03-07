'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  MessageSquare,
  ChevronRight,
  Loader2,
  Plus,
  Filter,
  CheckCircle2,
  Clock,
  AlertCircle,
  Search,
  Download,
  X,
  Star,
  User,
  Building2,
  GraduationCap,
  Briefcase,
  Users
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface Feedback {
  id: string
  feedback_type: string
  respondent_name: string | null
  respondent_email: string | null
  respondent_organization: string | null
  department: string
  program: string | null
  course_name: string | null
  academic_year: string
  feedback_content: string
  rating: number | null
  suggestions: string | null
  status: string
  action_taken: string | null
  action_date: string | null
  submitted_at: string
  created_at: string
}

const FEEDBACK_TYPES = [
  { value: 'student', label: 'Student', icon: GraduationCap, color: 'blue' },
  { value: 'alumni', label: 'Alumni', icon: Users, color: 'purple' },
  { value: 'employer', label: 'Employer', icon: Briefcase, color: 'green' },
  { value: 'teacher', label: 'Teacher', icon: User, color: 'orange' },
  { value: 'industry_expert', label: 'Industry Expert', icon: Building2, color: 'teal' },
  { value: 'parent', label: 'Parent', icon: Users, color: 'pink' }
]

const STATUS_COLORS = {
  pending: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  reviewed: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  action_taken: 'bg-green-500/10 text-green-400 border-green-500/20',
  closed: 'bg-slate-500/10 text-slate-400 border-slate-500/20'
}

export default function FeedbackManagementPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [feedbackList, setFeedbackList] = useState<Feedback[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)
  const [showActionModal, setShowActionModal] = useState(false)
  const [selectedFeedback, setSelectedFeedback] = useState<Feedback | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // Form state
  const [newFeedback, setNewFeedback] = useState({
    feedback_type: 'student',
    respondent_name: '',
    respondent_email: '',
    respondent_organization: '',
    respondent_designation: '',
    department: '',
    program: '',
    course_code: '',
    course_name: '',
    academic_year: '2024-25',
    semester: '',
    feedback_content: '',
    rating: 0,
    suggestions: ''
  })

  const [actionForm, setActionForm] = useState({
    action_taken: '',
    action_evidence: ''
  })

  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      fetchFeedback()
    }
  }, [authLoading, isAuthenticated, activeTab, statusFilter, page])

  const fetchFeedback = async () => {
    setIsLoading(true)
    try {
      const params = new URLSearchParams()
      if (activeTab !== 'all') params.append('feedback_type', activeTab)
      if (statusFilter) params.append('status', statusFilter)
      params.append('page', page.toString())
      params.append('page_size', '20')

      const response = await apiClient.get(`/accreditation/criterion1/feedback?${params.toString()}`)
      setFeedbackList(response.items || [])
      setTotal(response.total || 0)
    } catch (err: any) {
      console.error('Failed to fetch feedback:', err)
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSubmitFeedback = async () => {
    if (!newFeedback.department || !newFeedback.feedback_content) {
      setError('Please fill in required fields')
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.post('/accreditation/criterion1/feedback', {
        ...newFeedback,
        semester: newFeedback.semester ? parseInt(newFeedback.semester) : null,
        rating: newFeedback.rating || null
      })
      setShowAddModal(false)
      setNewFeedback({
        feedback_type: 'student',
        respondent_name: '',
        respondent_email: '',
        respondent_organization: '',
        respondent_designation: '',
        department: '',
        program: '',
        course_code: '',
        course_name: '',
        academic_year: '2024-25',
        semester: '',
        feedback_content: '',
        rating: 0,
        suggestions: ''
      })
      fetchFeedback()
    } catch (err: any) {
      console.error('Failed to submit feedback:', err)
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleSubmitAction = async () => {
    if (!selectedFeedback || !actionForm.action_taken) {
      setError('Please provide action taken details')
      return
    }

    setIsSubmitting(true)
    try {
      await apiClient.put(`/accreditation/criterion1/feedback/${selectedFeedback.id}/action`, actionForm)
      setShowActionModal(false)
      setSelectedFeedback(null)
      setActionForm({ action_taken: '', action_evidence: '' })
      fetchFeedback()
    } catch (err: any) {
      console.error('Failed to update action:', err)
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleGenerateReport = async () => {
    try {
      const response = await apiClient.post('/accreditation/criterion1/feedback/generate-report', {
        academic_year: '2024-25',
        include_pending: true
      })
      console.log('Report generated:', response)
      alert('Report generated successfully!')
    } catch (err: any) {
      console.error('Failed to generate report:', err)
      alert('Failed to generate report: ' + err.message)
    }
  }

  const filteredFeedback = feedbackList.filter(f =>
    f.feedback_content.toLowerCase().includes(searchQuery.toLowerCase()) ||
    f.department.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (f.respondent_name && f.respondent_name.toLowerCase().includes(searchQuery.toLowerCase()))
  )

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
      <div className="bg-gradient-to-r from-orange-600 to-orange-500 py-6">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2 text-orange-100 mb-2">
            <Link href="/admin/accreditation" className="hover:text-white">NAAC</Link>
            <ChevronRight className="w-4 h-4" />
            <Link href="/admin/accreditation/criterion1" className="hover:text-white">Criterion 1</Link>
            <ChevronRight className="w-4 h-4" />
            <span className="text-white">Feedback</span>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold flex items-center gap-2">
                <MessageSquare className="w-6 h-6" />
                Feedback Management
              </h1>
              <p className="text-orange-100">Key Indicator 1.4 - Stakeholder Feedback</p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleGenerateReport}
                className="bg-orange-700 hover:bg-orange-800 text-white px-4 py-2 rounded-lg flex items-center gap-2 transition-colors"
              >
                <Download className="w-4 h-4" />
                Export Report
              </button>
              <button
                onClick={() => setShowAddModal(true)}
                className="bg-white text-orange-600 px-4 py-2 rounded-lg font-medium hover:bg-orange-50 transition-colors flex items-center gap-2"
              >
                <Plus className="w-4 h-4" />
                Add Feedback
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Tabs */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
          <button
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors ${
              activeTab === 'all' ? 'bg-orange-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            All Feedback
          </button>
          {FEEDBACK_TYPES.map(type => (
            <button
              key={type.value}
              onClick={() => setActiveTab(type.value)}
              className={`px-4 py-2 rounded-lg font-medium whitespace-nowrap transition-colors flex items-center gap-2 ${
                activeTab === type.value ? 'bg-orange-500 text-white' : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <type.icon className="w-4 h-4" />
              {type.label}
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-4 mb-6">
          <div className="flex-1 relative">
            <Search className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search feedback..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-white placeholder-slate-400 focus:outline-none focus:border-orange-500"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
          >
            <option value="">All Status</option>
            <option value="pending">Pending</option>
            <option value="reviewed">Reviewed</option>
            <option value="action_taken">Action Taken</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        {/* Feedback List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
          </div>
        ) : filteredFeedback.length === 0 ? (
          <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-xl">
            <MessageSquare className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-slate-400">No feedback found</h3>
            <p className="text-slate-500 mb-4">Start collecting feedback from stakeholders</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              Add First Feedback
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredFeedback.map((feedback) => {
              const typeInfo = FEEDBACK_TYPES.find(t => t.value === feedback.feedback_type)
              const TypeIcon = typeInfo?.icon || MessageSquare

              return (
                <div
                  key={feedback.id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-6 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-lg bg-${typeInfo?.color || 'slate'}-500/10`}>
                        <TypeIcon className={`w-5 h-5 text-${typeInfo?.color || 'slate'}-500`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium capitalize">{feedback.feedback_type.replace('_', ' ')}</span>
                          {feedback.respondent_name && (
                            <span className="text-slate-400">- {feedback.respondent_name}</span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400">
                          {feedback.department} | {feedback.academic_year}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {feedback.rating && (
                        <div className="flex items-center gap-1">
                          {[1, 2, 3, 4, 5].map((star) => (
                            <Star
                              key={star}
                              className={`w-4 h-4 ${
                                star <= feedback.rating! ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'
                              }`}
                            />
                          ))}
                        </div>
                      )}
                      <span className={`px-3 py-1 rounded-full text-sm border ${STATUS_COLORS[feedback.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.pending}`}>
                        {feedback.status.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  <p className="text-slate-300 mb-4">{feedback.feedback_content}</p>

                  {feedback.suggestions && (
                    <div className="bg-slate-800 rounded-lg p-3 mb-4">
                      <p className="text-sm text-slate-400 mb-1">Suggestions:</p>
                      <p className="text-slate-300">{feedback.suggestions}</p>
                    </div>
                  )}

                  {feedback.action_taken && (
                    <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3 mb-4">
                      <p className="text-sm text-green-400 mb-1 flex items-center gap-1">
                        <CheckCircle2 className="w-4 h-4" />
                        Action Taken ({new Date(feedback.action_date!).toLocaleDateString()})
                      </p>
                      <p className="text-slate-300">{feedback.action_taken}</p>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                    <p className="text-sm text-slate-500">
                      Submitted: {new Date(feedback.submitted_at).toLocaleDateString()}
                    </p>
                    {feedback.status !== 'action_taken' && feedback.status !== 'closed' && (
                      <button
                        onClick={() => {
                          setSelectedFeedback(feedback)
                          setShowActionModal(true)
                        }}
                        className="bg-green-500/10 hover:bg-green-500/20 text-green-400 px-4 py-2 rounded-lg text-sm transition-colors flex items-center gap-2"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                        Record Action
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Pagination */}
        {total > 20 && (
          <div className="flex items-center justify-center gap-2 mt-6">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 bg-slate-800 rounded-lg disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-slate-400">Page {page} of {Math.ceil(total / 20)}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(total / 20)}
              className="px-4 py-2 bg-slate-800 rounded-lg disabled:opacity-50"
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* Add Feedback Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Add New Feedback</h2>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Feedback Type *</label>
                  <select
                    value={newFeedback.feedback_type}
                    onChange={(e) => setNewFeedback({ ...newFeedback, feedback_type: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                  >
                    {FEEDBACK_TYPES.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Academic Year *</label>
                  <select
                    value={newFeedback.academic_year}
                    onChange={(e) => setNewFeedback({ ...newFeedback, academic_year: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                  >
                    <option value="2024-25">2024-25</option>
                    <option value="2023-24">2023-24</option>
                    <option value="2022-23">2022-23</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Respondent Name</label>
                  <input
                    type="text"
                    value={newFeedback.respondent_name}
                    onChange={(e) => setNewFeedback({ ...newFeedback, respondent_name: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                    placeholder="Optional"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Email</label>
                  <input
                    type="email"
                    value={newFeedback.respondent_email}
                    onChange={(e) => setNewFeedback({ ...newFeedback, respondent_email: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                    placeholder="Optional"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Department *</label>
                  <input
                    type="text"
                    value={newFeedback.department}
                    onChange={(e) => setNewFeedback({ ...newFeedback, department: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                    placeholder="e.g., Computer Science"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Program</label>
                  <input
                    type="text"
                    value={newFeedback.program}
                    onChange={(e) => setNewFeedback({ ...newFeedback, program: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                    placeholder="e.g., B.Tech"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Rating</label>
                <div className="flex items-center gap-2">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setNewFeedback({ ...newFeedback, rating: star })}
                      className="focus:outline-none"
                    >
                      <Star
                        className={`w-8 h-8 ${
                          star <= newFeedback.rating ? 'text-yellow-400 fill-yellow-400' : 'text-slate-600'
                        }`}
                      />
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Feedback Content *</label>
                <textarea
                  value={newFeedback.feedback_content}
                  onChange={(e) => setNewFeedback({ ...newFeedback, feedback_content: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500 min-h-[120px]"
                  placeholder="Enter feedback details..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Suggestions</label>
                <textarea
                  value={newFeedback.suggestions}
                  onChange={(e) => setNewFeedback({ ...newFeedback, suggestions: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500 min-h-[80px]"
                  placeholder="Any suggestions for improvement..."
                />
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
                onClick={handleSubmitFeedback}
                disabled={isSubmitting}
                className="px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Submit Feedback
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Action Modal */}
      {showActionModal && selectedFeedback && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full">
            <div className="p-6 border-b border-slate-800 flex items-center justify-between">
              <h2 className="text-xl font-semibold">Record Action Taken</h2>
              <button onClick={() => setShowActionModal(false)} className="text-slate-400 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-slate-800 rounded-lg p-4">
                <p className="text-sm text-slate-400 mb-2">Original Feedback:</p>
                <p className="text-slate-300">{selectedFeedback.feedback_content}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Action Taken *</label>
                <textarea
                  value={actionForm.action_taken}
                  onChange={(e) => setActionForm({ ...actionForm, action_taken: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500 min-h-[120px]"
                  placeholder="Describe the action taken in response to this feedback..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-400 mb-1">Evidence Reference</label>
                <input
                  type="text"
                  value={actionForm.action_evidence}
                  onChange={(e) => setActionForm({ ...actionForm, action_evidence: e.target.value })}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-orange-500"
                  placeholder="e.g., Meeting minutes, Revised syllabus, etc."
                />
              </div>
            </div>
            <div className="p-6 border-t border-slate-800 flex justify-end gap-3">
              <button
                onClick={() => setShowActionModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitAction}
                disabled={isSubmitting}
                className="px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                Save Action
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
