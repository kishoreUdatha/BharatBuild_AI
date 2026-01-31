'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import {
  Users, FileText, CheckCircle, XCircle, Clock, Lock,
  Eye, MessageSquare, Award, Calendar, ChevronRight,
  Search, RefreshCw, Loader2, BookOpen, Code, Target,
  GraduationCap, Play, Shield, User, Star, Filter,
  AlertCircle, TrendingUp, ClipboardCheck, ChevronDown, X
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface ReviewProject {
  id: string
  title: string
  description: string
  project_type: string
  technology_stack: string
  domain: string
  team_name: string
  team_size: number
  semester: number
  batch: string
  department: string
  guide_name: string
  current_review: number
  total_score: number
  average_score: number
  ai_usage_percentage: number
  plagiarism_percentage: number
  phase_1_locked: boolean
  phase_2_locked: boolean
  phase_3_locked: boolean
  phase_4_locked: boolean
  github_url?: string
  demo_url?: string
}

interface ProjectReview {
  id: string
  project_id: string
  project_title?: string
  review_type: string
  review_number: number
  scheduled_date: string
  scheduled_time: string
  venue: string
  status: string
  decision: string | null
  total_score: number
  is_locked: boolean
}

const reviewInfo: Record<string, { name: string; short: string; color: string }> = {
  review_1: { name: 'Review 1 - Problem Statement', short: 'R1', color: 'blue' },
  review_2: { name: 'Review 2 - Literature & Design', short: 'R2', color: 'purple' },
  review_3: { name: 'Review 3 - Implementation', short: 'R3', color: 'amber' },
  final_review: { name: 'Final Review', short: 'Final', color: 'emerald' }
}

export default function ProjectGuidancePage() {
  const [projects, setProjects] = useState<ReviewProject[]>([])
  const [reviews, setReviews] = useState<ProjectReview[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSemester, setSelectedSemester] = useState<number | null>(null)
  const [projectTypeFilter, setProjectTypeFilter] = useState<'all' | 'mini_project' | 'major_project'>('all')
  const [reviewTypeFilter, setReviewTypeFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedReview, setSelectedReview] = useState<ProjectReview | null>(null)
  const [selectedProject, setSelectedProject] = useState<ReviewProject | null>(null)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [reviewDetails, setReviewDetails] = useState<any>(null)
  const [loadingDetails, setLoadingDetails] = useState(false)
  const [saving, setSaving] = useState(false)
  const [scores, setScores] = useState({ innovation: 0, technical: 0, implementation: 0, documentation: 0, presentation: 0 })
  const [feedback, setFeedback] = useState({ strengths: '', weaknesses: '', suggestions: '', overall: '' })
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)
  const [activeTab, setActiveTab] = useState<'reviews' | 'naac'>('reviews')
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)
  const [editMode, setEditMode] = useState(false)
  const [pendingSubmissions, setPendingSubmissions] = useState<string[]>([]) // Review IDs with pending submissions
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setOpenDropdown(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => { fetchData() }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const [projectsRes, reviewsRes, pendingRes] = await Promise.all([
        fetch(`${API_BASE}/project-guidance/projects`),
        fetch(`${API_BASE}/project-guidance/reviews`),
        fetch(`${API_BASE}/project-guidance/faculty/pending-submissions`)
      ])
      if (projectsRes.ok) setProjects(await projectsRes.json())
      if (reviewsRes.ok) setReviews(await reviewsRes.json())
      if (pendingRes.ok) {
        const pending = await pendingRes.json()
        setPendingSubmissions(pending.map((p: any) => p.id))
      }
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  // Get unique semesters
  const availableSemesters = useMemo(() => {
    const sems = Array.from(new Set(projects.map(p => p.semester).filter(Boolean))).sort((a, b) => a - b)
    return sems.length > 0 ? sems : [3, 4, 5, 6, 7, 8]
  }, [projects])

  // Get semester projects (all projects if no semester selected)
  const semesterProjects = useMemo(() =>
    selectedSemester ? projects.filter(p => p.semester === selectedSemester) : projects
  , [projects, selectedSemester])

  // Get filtered reviews for selected semester
  const filteredReviews = useMemo(() => {
    const semProjectIds = semesterProjects.map(p => p.id)
    let filtered = reviews.filter(r => semProjectIds.includes(r.project_id))

    // Apply project type filter
    if (projectTypeFilter !== 'all') {
      const typeProjectIds = semesterProjects.filter(p => p.project_type === projectTypeFilter).map(p => p.id)
      filtered = filtered.filter(r => typeProjectIds.includes(r.project_id))
    }

    // Apply review type filter
    if (reviewTypeFilter !== 'all') {
      filtered = filtered.filter(r => r.review_type === reviewTypeFilter)
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      if (statusFilter === 'submitted') {
        // Filter for reviews that have student submissions pending faculty review
        filtered = filtered.filter(r => pendingSubmissions.includes(r.id))
      } else {
        filtered = filtered.filter(r => r.status === statusFilter)
      }
    }

    // Apply search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(r => {
        const project = semesterProjects.find(p => p.id === r.project_id)
        return project?.team_name?.toLowerCase().includes(q) ||
               project?.title?.toLowerCase().includes(q) ||
               r.project_title?.toLowerCase().includes(q)
      })
    }

    return filtered
  }, [reviews, semesterProjects, projectTypeFilter, reviewTypeFilter, statusFilter, searchQuery, pendingSubmissions])

  // Dashboard stats for selected semester
  const dashboardStats = useMemo(() => {
    const semProjectIds = semesterProjects.map(p => p.id)
    const semReviews = reviews.filter(r => semProjectIds.includes(r.project_id))

    return {
      totalProjects: semesterProjects.length,
      miniProjects: semesterProjects.filter(p => p.project_type === 'mini_project').length,
      majorProjects: semesterProjects.filter(p => p.project_type === 'major_project').length,
      totalReviews: semReviews.length,
      pendingReviews: semReviews.filter(r => r.status === 'scheduled').length,
      inProgressReviews: semReviews.filter(r => r.status === 'in_progress').length,
      completedReviews: semReviews.filter(r => r.status === 'completed').length,
      avgScore: semReviews.filter(r => r.total_score > 0).length > 0
        ? (semReviews.filter(r => r.total_score > 0).reduce((sum, r) => sum + r.total_score, 0) / semReviews.filter(r => r.total_score > 0).length).toFixed(1)
        : '0'
    }
  }, [semesterProjects, reviews])

  const openReviewModal = async (review: ProjectReview) => {
    const project = semesterProjects.find(p => p.id === review.project_id)
    setSelectedReview(review)
    setSelectedProject(project || null)
    setShowReviewModal(true)
    setLoadingDetails(true)
    setScores({ innovation: 0, technical: 0, implementation: 0, documentation: 0, presentation: 0 })
    setFeedback({ strengths: '', weaknesses: '', suggestions: '', overall: '' })

    try {
      const res = await fetch(`${API_BASE}/project-guidance/reviews/${review.id}`)
      if (res.ok) {
        const data = await res.json()
        setReviewDetails(data)
        if (data.scores) {
          setScores({
            innovation: Math.round(data.scores.innovation || 0),
            technical: Math.round(data.scores.technical || 0),
            implementation: Math.round(data.scores.implementation || 0),
            documentation: Math.round(data.scores.documentation || 0),
            presentation: Math.round(data.scores.presentation || 0)
          })
        }
        if (data.feedback) {
          setFeedback({
            strengths: data.feedback.strengths || '',
            weaknesses: data.feedback.weaknesses || '',
            suggestions: data.feedback.suggestions || '',
            overall: data.feedback.overall || ''
          })
        }
      }
    } catch (e) { console.error(e) }
    setLoadingDetails(false)
  }

  const handleStartReview = async (id: string) => {
    const res = await fetch(`${API_BASE}/project-guidance/reviews/${id}/start`, { method: 'POST' })
    if (res.ok) { showToast('Review started'); fetchData() }
  }

  const handleSaveScore = async () => {
    if (!selectedReview || !reviewDetails) return
    const panelId = reviewDetails.panel_members?.[0]?.id
    if (!panelId) return showToast('No panel member assigned', 'error')
    const total = scores.innovation + scores.technical + scores.implementation + scores.documentation + scores.presentation
    if (total === 0) return showToast('Please enter scores', 'error')
    setSaving(true)
    try {
      const res = await fetch(`${API_BASE}/project-guidance/reviews/${selectedReview.id}/scores?panel_member_id=${panelId}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ innovation_score: scores.innovation, technical_score: scores.technical, implementation_score: scores.implementation, documentation_score: scores.documentation, presentation_score: scores.presentation })
      })
      if (res.ok) { showToast('Scores saved'); fetchData() }
      else showToast('Failed to save', 'error')
    } catch { showToast('Failed to save', 'error') }
    setSaving(false)
  }

  const handleSaveFeedback = async () => {
    if (!selectedReview) return
    setSaving(true)
    const res = await fetch(`${API_BASE}/project-guidance/reviews/${selectedReview.id}/feedback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ strengths: feedback.strengths, weaknesses: feedback.weaknesses, suggestions: feedback.suggestions, overall_feedback: feedback.overall })
    })
    if (res.ok) { showToast('Feedback saved'); fetchData() }
    else showToast('Failed to save', 'error')
    setSaving(false)
  }

  const handleDecision = async (decision: 'approved' | 'revision_needed') => {
    if (!selectedReview) return
    setSaving(true)
    const res = await fetch(`${API_BASE}/project-guidance/reviews/${selectedReview.id}/decision`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, feedback: feedback.overall, action_items: feedback.suggestions })
    })
    if (res.ok) { showToast(`${decision === 'approved' ? 'Approved' : 'Revision requested'}`); fetchData() }
    else showToast('Failed', 'error')
    setSaving(false)
  }

  const handleComplete = async () => {
    if (!selectedReview) return
    const res = await fetch(`${API_BASE}/project-guidance/reviews/${selectedReview.id}/complete`, { method: 'POST' })
    if (res.ok) { showToast('Review completed'); setShowReviewModal(false); fetchData() }
    else showToast('Failed', 'error')
  }

  const totalScore = Math.round((scores.innovation + scores.technical + scores.implementation + scores.documentation + scores.presentation) * 100) / 100

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800/50 border-b border-gray-700 px-6 py-4 shrink-0 overflow-visible relative z-20">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold text-white">Project Guidance & Reviews</h1>
            <p className="text-gray-400 text-sm">Review student projects and provide feedback</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Pending Submissions Badge */}
            {pendingSubmissions.length > 0 && (
              <div className="px-3 py-2 bg-orange-500/20 border border-orange-500/30 rounded-lg flex items-center gap-2 animate-pulse">
                <AlertCircle className="w-4 h-4 text-orange-400" />
                <span className="text-orange-400 text-sm font-medium">
                  {pendingSubmissions.length} Pending Submission{pendingSubmissions.length > 1 ? 's' : ''}
                </span>
              </div>
            )}
            <button
              onClick={() => setActiveTab('reviews')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'reviews' ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <ClipboardCheck className="w-4 h-4 inline mr-2" />Reviews
            </button>
            <button
              onClick={() => setActiveTab('naac')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                activeTab === 'naac' ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              <FileText className="w-4 h-4 inline mr-2" />NAAC
            </button>
            <button onClick={fetchData} className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Filters Row - Semester + Search + All Filters */}
        {activeTab === 'reviews' && (
          <div className="flex items-center gap-2" ref={dropdownRef}>
            {/* Semester Selection Dropdown */}
            <div className="relative shrink-0">
              <button
                className={`flex items-center gap-2 px-3 py-2.5 bg-gray-800 border rounded-xl text-sm font-medium hover:border-gray-500 focus:outline-none min-w-[150px] transition-all ${
                  openDropdown === 'semester' ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-gray-600'
                }`}
                onClick={() => setOpenDropdown(openDropdown === 'semester' ? null : 'semester')}
              >
                <GraduationCap className="w-4 h-4 text-indigo-400" />
                <span className="text-white font-medium whitespace-nowrap">
                  {selectedSemester ? `Sem ${selectedSemester}` : 'All Sem'}
                </span>
                <span className="px-1.5 py-0.5 bg-indigo-500/20 text-indigo-300 rounded text-xs font-semibold">
                  {selectedSemester ? projects.filter(p => p.semester === selectedSemester).length : projects.length}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-400 ml-auto transition-transform ${openDropdown === 'semester' ? 'rotate-180' : ''}`} />
              </button>
              {openDropdown === 'semester' && (
                <div className="absolute top-full left-0 mt-1 w-56 bg-gray-800 border border-gray-600 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200 max-h-80 overflow-y-auto">
                  {/* All Semesters Option */}
                  <button
                    onClick={() => {
                      setSelectedSemester(null)
                      setSearchQuery('')
                      setProjectTypeFilter('all')
                      setReviewTypeFilter('all')
                      setStatusFilter('all')
                      setOpenDropdown(null)
                    }}
                    className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-700 flex items-center justify-between transition-colors ${
                      selectedSemester === null ? 'bg-indigo-600/20 text-indigo-300' : 'text-gray-300'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold ${
                        selectedSemester === null ? 'bg-indigo-500 text-white' : 'bg-gray-700 text-gray-300'
                      }`}>
                        <Users className="w-4 h-4" />
                      </span>
                      <span className="font-medium">All Semesters</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        selectedSemester === null ? 'bg-indigo-500/30 text-indigo-300' : 'bg-gray-700 text-gray-400'
                      }`}>
                        {projects.length}
                      </span>
                      {selectedSemester === null && <CheckCircle className="w-4 h-4 text-indigo-400" />}
                    </div>
                  </button>

                  {/* Divider */}
                  <div className="border-t border-gray-700 my-1"></div>

                  {/* Individual Semesters */}
                  {availableSemesters.map(sem => {
                    const count = projects.filter(p => p.semester === sem).length
                    const isSelected = selectedSemester === sem
                    return (
                      <button
                        key={sem}
                        onClick={() => {
                          setSelectedSemester(sem)
                          setSearchQuery('')
                          setProjectTypeFilter('all')
                          setReviewTypeFilter('all')
                          setStatusFilter('all')
                          setOpenDropdown(null)
                        }}
                        className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-700 flex items-center justify-between transition-colors ${
                          isSelected ? 'bg-indigo-600/20 text-indigo-300' : 'text-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold ${
                            isSelected ? 'bg-indigo-500 text-white' : 'bg-gray-700 text-gray-300'
                          }`}>
                            {sem}
                          </span>
                          <span className="font-medium">Semester {sem}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            isSelected ? 'bg-indigo-500/30 text-indigo-300' : 'bg-gray-700 text-gray-400'
                          }`}>
                            {count}
                          </span>
                          {isSelected && <CheckCircle className="w-4 h-4 text-indigo-400" />}
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Search Input */}
            <div className="relative min-w-[180px] shrink-0">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-8 py-2.5 bg-gray-800 border border-gray-600 rounded-xl text-white text-sm placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Project Type Filter Dropdown */}
            <div className="relative shrink-0">
              <button
                className={`flex items-center gap-2 px-3 py-2.5 bg-gray-800 border rounded-xl text-sm font-medium hover:border-gray-500 focus:outline-none min-w-[110px] transition-all ${
                  openDropdown === 'projectType' ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-gray-600'
                }`}
                onClick={() => setOpenDropdown(openDropdown === 'projectType' ? null : 'projectType')}
              >
                <Code className="w-4 h-4 text-cyan-400" />
                <span className={projectTypeFilter === 'all' ? 'text-gray-400' : 'text-white'}>
                  {projectTypeFilter === 'all' ? 'All Types' : projectTypeFilter === 'mini_project' ? 'Mini' : 'Major'}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-400 ml-auto transition-transform ${openDropdown === 'projectType' ? 'rotate-180' : ''}`} />
              </button>
              {openDropdown === 'projectType' && (
                <div className="absolute top-full left-0 mt-1 w-40 bg-gray-800 border border-gray-600 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                  {[
                    { value: 'all', label: 'All Types', dotColor: 'bg-gray-400' },
                    { value: 'mini_project', label: 'Mini Project', dotColor: 'bg-cyan-400' },
                    { value: 'major_project', label: 'Major Project', dotColor: 'bg-orange-400' }
                  ].map(option => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setProjectTypeFilter(option.value as any)
                        setOpenDropdown(null)
                      }}
                      className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-700 flex items-center gap-2 transition-colors ${
                        projectTypeFilter === option.value ? 'bg-indigo-600/20 text-indigo-300' : 'text-gray-300'
                      }`}
                    >
                      <span className={`w-2 h-2 rounded-full ${option.dotColor}`}></span>
                      {option.label}
                      {projectTypeFilter === option.value && <CheckCircle className="w-4 h-4 ml-auto text-indigo-400" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Review Type Filter Dropdown */}
            <div className="relative shrink-0">
              <button
                className={`flex items-center gap-2 px-3 py-2.5 bg-gray-800 border rounded-xl text-sm font-medium hover:border-gray-500 focus:outline-none min-w-[120px] transition-all ${
                  openDropdown === 'reviewType' ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-gray-600'
                }`}
                onClick={() => setOpenDropdown(openDropdown === 'reviewType' ? null : 'reviewType')}
              >
                <ClipboardCheck className="w-4 h-4 text-purple-400" />
                <span className={reviewTypeFilter === 'all' ? 'text-gray-400' : 'text-white'}>
                  {reviewTypeFilter === 'all' ? 'All Reviews' : reviewInfo[reviewTypeFilter]?.short || reviewTypeFilter}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-400 ml-auto transition-transform ${openDropdown === 'reviewType' ? 'rotate-180' : ''}`} />
              </button>
              {openDropdown === 'reviewType' && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-gray-800 border border-gray-600 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                  {[
                    { value: 'all', label: 'All Reviews', badge: null },
                    { value: 'review_1', label: 'Problem Statement', badge: 'R1', badgeColor: 'bg-blue-500/20 text-blue-300' },
                    { value: 'review_2', label: 'Literature & Design', badge: 'R2', badgeColor: 'bg-purple-500/20 text-purple-300' },
                    { value: 'review_3', label: 'Implementation', badge: 'R3', badgeColor: 'bg-amber-500/20 text-amber-300' },
                    { value: 'final_review', label: 'Final Review', badge: 'Final', badgeColor: 'bg-emerald-500/20 text-emerald-300' }
                  ].map(option => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setReviewTypeFilter(option.value)
                        setOpenDropdown(null)
                      }}
                      className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-700 flex items-center gap-2 transition-colors ${
                        reviewTypeFilter === option.value ? 'bg-indigo-600/20 text-indigo-300' : 'text-gray-300'
                      }`}
                    >
                      {option.badge && (
                        <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${option.badgeColor}`}>
                          {option.badge}
                        </span>
                      )}
                      <span className="truncate">{option.label}</span>
                      {reviewTypeFilter === option.value && <CheckCircle className="w-4 h-4 ml-auto text-indigo-400 shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Status Filter Dropdown */}
            <div className="relative shrink-0">
              <button
                className={`flex items-center gap-2 px-3 py-2.5 bg-gray-800 border rounded-xl text-sm font-medium hover:border-gray-500 focus:outline-none min-w-[115px] transition-all ${
                  openDropdown === 'status' ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-gray-600'
                }`}
                onClick={() => setOpenDropdown(openDropdown === 'status' ? null : 'status')}
              >
                <Filter className="w-4 h-4 text-amber-400" />
                <span className={statusFilter === 'all' ? 'text-gray-400' : 'text-white'}>
                  {statusFilter === 'all' ? 'All Status' : statusFilter.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                <ChevronDown className={`w-4 h-4 text-gray-400 ml-auto transition-transform ${openDropdown === 'status' ? 'rotate-180' : ''}`} />
              </button>
              {openDropdown === 'status' && (
                <div className="absolute top-full left-0 mt-1 w-40 bg-gray-800 border border-gray-600 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                  {[
                    { value: 'all', label: 'All Status', Icon: null, iconColor: '' },
                    { value: 'submitted', label: 'Submitted', Icon: AlertCircle, iconColor: 'text-orange-400' },
                    { value: 'scheduled', label: 'Scheduled', Icon: Clock, iconColor: 'text-blue-400' },
                    { value: 'in_progress', label: 'In Progress', Icon: Play, iconColor: 'text-amber-400' },
                    { value: 'completed', label: 'Completed', Icon: CheckCircle, iconColor: 'text-emerald-400' }
                  ].map(option => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setStatusFilter(option.value)
                        setOpenDropdown(null)
                      }}
                      className={`w-full px-4 py-2.5 text-left text-sm hover:bg-gray-700 flex items-center gap-2 transition-colors ${
                        statusFilter === option.value ? 'bg-indigo-600/20 text-indigo-300' : 'text-gray-300'
                      }`}
                    >
                      {option.Icon ? <option.Icon className={`w-4 h-4 ${option.iconColor}`} /> : <span className="w-4 h-4 flex items-center justify-center"><span className="w-2 h-2 rounded-full bg-gray-400"></span></span>}
                      {option.label}
                      {statusFilter === option.value && <CheckCircle className="w-4 h-4 ml-auto text-indigo-400" />}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Results Count */}
            <div className="flex items-center gap-1.5 text-gray-400 text-sm bg-gray-800/50 px-2.5 py-2 rounded-lg shrink-0 whitespace-nowrap">
              <span className="font-semibold text-white">{semesterProjects.filter(p => {
                if (projectTypeFilter !== 'all' && p.project_type !== projectTypeFilter) return false
                if (searchQuery.trim()) {
                  const q = searchQuery.toLowerCase()
                  if (!p.team_name?.toLowerCase().includes(q) && !p.title?.toLowerCase().includes(q)) return false
                }
                return true
              }).length}</span>
              project{semesterProjects.length !== 1 ? 's' : ''}
            </div>

            {/* Clear Filters Button */}
            {(projectTypeFilter !== 'all' || reviewTypeFilter !== 'all' || statusFilter !== 'all' || searchQuery) && (
              <button
                onClick={() => {
                  setProjectTypeFilter('all')
                  setReviewTypeFilter('all')
                  setStatusFilter('all')
                  setSearchQuery('')
                }}
                className="px-2.5 py-2 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm font-medium hover:bg-red-500/20 flex items-center gap-1 shrink-0 whitespace-nowrap"
              >
                <X className="w-3.5 h-3.5" />
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {activeTab === 'naac' ? (
        <NAACReports />
      ) : (
        <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
          {/* Student Projects Table */}
          <div className="bg-gray-800/30 border border-gray-700 rounded-xl overflow-x-auto">
            <table className="w-full min-w-[1000px]">
              <thead>
                <tr className="bg-gray-800/50 text-left">
                  <th className="px-4 py-3 text-gray-400 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Student / Team</th>
                  <th className="px-4 py-3 text-gray-400 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Project</th>
                  <th className="px-3 py-3 text-gray-400 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Guide</th>
                  <th className="px-3 py-3 text-gray-400 text-xs font-semibold uppercase tracking-wider whitespace-nowrap text-center">Reviews</th>
                  <th className="px-3 py-3 text-gray-400 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Progress</th>
                  <th className="px-3 py-3 text-gray-400 text-xs font-semibold uppercase tracking-wider whitespace-nowrap">Action</th>
                </tr>
              </thead>
              <tbody>
                {semesterProjects
                  .filter(project => {
                    // Apply project type filter
                    if (projectTypeFilter !== 'all' && project.project_type !== projectTypeFilter) return false
                    // Apply search filter
                    if (searchQuery.trim()) {
                      const q = searchQuery.toLowerCase()
                      if (!project.team_name?.toLowerCase().includes(q) &&
                          !project.title?.toLowerCase().includes(q) &&
                          !project.guide_name?.toLowerCase().includes(q)) return false
                    }
                    return true
                  })
                  .map(project => {
                    // Get all reviews for this project
                    const projectReviews = reviews.filter(r => r.project_id === project.id)
                    const r1 = projectReviews.find(r => r.review_type === 'review_1')
                    const r2 = projectReviews.find(r => r.review_type === 'review_2')
                    const r3 = projectReviews.find(r => r.review_type === 'review_3')
                    const final = projectReviews.find(r => r.review_type === 'final_review')

                    // Calculate progress
                    const completedReviews = [r1, r2, r3, final].filter(r => r?.status === 'completed').length
                    const progressPercent = (completedReviews / 4) * 100

                    // Calculate total score from completed reviews
                    const completedScores = projectReviews.filter(r => r.status === 'completed' && r.total_score > 0)
                    const avgScore = completedScores.length > 0
                      ? Math.round(completedScores.reduce((sum, r) => sum + r.total_score, 0) / completedScores.length)
                      : 0

                    // Find next actionable review
                    const nextReview = projectReviews.find(r => r.status === 'scheduled' || r.status === 'in_progress')

                    // Review status helper
                    const getReviewStatus = (review: ProjectReview | undefined, isLocked: boolean) => {
                      if (!review) return isLocked ? 'locked' : 'pending'
                      if (review.status === 'completed') return 'completed'
                      if (review.status === 'in_progress') return 'in_progress'
                      return isLocked ? 'locked' : 'pending'
                    }

                    const ReviewIcon = ({ status }: { status: string }) => {
                      if (status === 'completed') return <CheckCircle className="w-4 h-4 text-emerald-400" />
                      if (status === 'in_progress') return <Clock className="w-4 h-4 text-amber-400" />
                      if (status === 'locked') return <Lock className="w-4 h-4 text-gray-600" />
                      return <div className="w-4 h-4 rounded-full border-2 border-gray-600" />
                    }

                    return (
                      <tr key={project.id} className="border-t border-gray-700/50 hover:bg-gray-800/30 transition-colors">
                        {/* Student / Team Column */}
                        <td className="px-4 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-sm shrink-0">
                              {project.team_name?.charAt(0)?.toUpperCase() || 'T'}
                            </div>
                            <div className="min-w-0">
                              <p className="text-white font-medium text-sm">{project.team_name || 'Unknown Team'}</p>
                              <div className="flex items-center gap-2 text-xs text-gray-500">
                                <span>{project.department || 'CSE'}</span>
                                <span>•</span>
                                <span>Batch {project.batch || '2021'}</span>
                                <span>•</span>
                                <span>{project.team_size || 4} members</span>
                              </div>
                            </div>
                          </div>
                        </td>

                        {/* Project Column */}
                        <td className="px-4 py-4">
                          <div className="min-w-0">
                            <p className="text-white font-medium text-sm truncate max-w-[200px]">{project.title}</p>
                            <div className="flex items-center gap-2 mt-1">
                              <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                project.project_type === 'major_project'
                                  ? 'bg-orange-500/20 text-orange-300'
                                  : 'bg-cyan-500/20 text-cyan-300'
                              }`}>
                                {project.project_type === 'major_project' ? 'Major' : 'Mini'}
                              </span>
                              {project.domain && (
                                <span className="text-gray-500 text-xs">{project.domain}</span>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Guide Column */}
                        <td className="px-3 py-4">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 bg-gray-700 rounded-full flex items-center justify-center">
                              <User className="w-4 h-4 text-gray-400" />
                            </div>
                            <span className="text-gray-300 text-sm">{project.guide_name || 'Not Assigned'}</span>
                          </div>
                        </td>

                        {/* Reviews Column */}
                        <td className="px-3 py-4">
                          <div className="flex items-center justify-center gap-1">
                            <div className="flex flex-col items-center" title="Review 1">
                              <ReviewIcon status={getReviewStatus(r1, project.phase_1_locked)} />
                              <span className="text-[10px] text-gray-500 mt-0.5">R1</span>
                            </div>
                            <div className="w-3 h-px bg-gray-700"></div>
                            <div className="flex flex-col items-center" title="Review 2">
                              <ReviewIcon status={getReviewStatus(r2, project.phase_2_locked)} />
                              <span className="text-[10px] text-gray-500 mt-0.5">R2</span>
                            </div>
                            <div className="w-3 h-px bg-gray-700"></div>
                            <div className="flex flex-col items-center" title="Review 3">
                              <ReviewIcon status={getReviewStatus(r3, project.phase_3_locked)} />
                              <span className="text-[10px] text-gray-500 mt-0.5">R3</span>
                            </div>
                            <div className="w-3 h-px bg-gray-700"></div>
                            <div className="flex flex-col items-center" title="Final Review">
                              <ReviewIcon status={getReviewStatus(final, project.phase_4_locked)} />
                              <span className="text-[10px] text-gray-500 mt-0.5">F</span>
                            </div>
                          </div>
                        </td>

                        {/* Progress Column */}
                        <td className="px-3 py-4">
                          <div className="min-w-[100px]">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-gray-400">{Math.round(progressPercent)}%</span>
                              {avgScore > 0 && (
                                <span className="text-xs font-semibold text-emerald-400">{avgScore}/100</span>
                              )}
                            </div>
                            <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${
                                  progressPercent === 100 ? 'bg-emerald-500' :
                                  progressPercent >= 50 ? 'bg-indigo-500' :
                                  progressPercent > 0 ? 'bg-amber-500' : 'bg-gray-600'
                                }`}
                                style={{ width: `${progressPercent}%` }}
                              />
                            </div>
                          </div>
                        </td>

                        {/* Action Column */}
                        <td className="px-3 py-4">
                          <div className="flex items-center gap-2">
                            {/* Check if any review has a pending submission */}
                            {(() => {
                              const submittedReview = projectReviews.find(r => pendingSubmissions.includes(r.id))
                              if (submittedReview) {
                                return (
                                  <button
                                    onClick={() => {
                                      handleStartReview(submittedReview.id)
                                      openReviewModal(submittedReview)
                                    }}
                                    className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors whitespace-nowrap animate-pulse"
                                  >
                                    <AlertCircle className="w-3.5 h-3.5" /> Review Submission
                                  </button>
                                )
                              }
                              return null
                            })()}
                            {!projectReviews.find(r => pendingSubmissions.includes(r.id)) && nextReview ? (
                              nextReview.status === 'scheduled' ? (
                                <button
                                  onClick={() => handleStartReview(nextReview.id)}
                                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors whitespace-nowrap"
                                >
                                  <Play className="w-3.5 h-3.5" /> Start {reviewInfo[nextReview.review_type]?.short}
                                </button>
                              ) : (
                                <button
                                  onClick={() => openReviewModal(nextReview)}
                                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors whitespace-nowrap"
                                >
                                  <Award className="w-3.5 h-3.5" /> Review {reviewInfo[nextReview.review_type]?.short}
                                </button>
                              )
                            ) : !projectReviews.find(r => pendingSubmissions.includes(r.id)) && completedReviews === 4 ? (
                              <button
                                onClick={() => {
                                  const lastReview = projectReviews.find(r => r.status === 'completed')
                                  if (lastReview) openReviewModal(lastReview)
                                }}
                                className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 rounded-lg text-xs font-medium flex items-center gap-1.5 hover:bg-emerald-500/30 transition-colors"
                              >
                                <CheckCircle className="w-3.5 h-3.5" /> View All
                              </button>
                            ) : !projectReviews.find(r => pendingSubmissions.includes(r.id)) && projectReviews.length === 0 ? (
                              <button
                                onClick={() => {
                                  setSelectedProject(project)
                                  setShowReviewModal(true)
                                  setSelectedReview(null as any)
                                }}
                                className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors whitespace-nowrap"
                              >
                                <Calendar className="w-3.5 h-3.5" /> Schedule R1
                              </button>
                            ) : !projectReviews.find(r => pendingSubmissions.includes(r.id)) ? (
                              <button
                                onClick={() => {
                                  const lastReview = [...projectReviews].sort((a, b) => b.review_number - a.review_number)[0]
                                  if (lastReview) openReviewModal(lastReview)
                                }}
                                className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors whitespace-nowrap"
                              >
                                <Eye className="w-3.5 h-3.5" /> View
                              </button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
              </tbody>
            </table>

            {semesterProjects.length === 0 && (
              <div className="text-center py-16">
                <GraduationCap className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                <p className="text-gray-400 font-medium">No projects found</p>
                <p className="text-gray-500 text-sm mt-1">Select a semester to view student projects</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Review Modal */}
      {showReviewModal && selectedReview && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden border border-gray-700 shadow-2xl flex flex-col">
            {/* Modal Header */}
            <div className="bg-gray-800/50 border-b border-gray-700 px-6 py-4 flex justify-between items-center shrink-0">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-indigo-500/20 rounded-xl flex items-center justify-center">
                  <span className="text-indigo-400 font-bold text-lg">
                    {selectedProject?.team_name?.charAt(0)?.toUpperCase() || 'T'}
                  </span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-white font-bold text-lg">{selectedProject?.team_name}</h3>
                    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      selectedProject?.project_type === 'major_project'
                        ? 'bg-orange-500/20 text-orange-300'
                        : 'bg-cyan-500/20 text-cyan-300'
                    }`}>
                      {selectedProject?.project_type === 'major_project' ? 'Major' : 'Mini'}
                    </span>
                    <span className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs font-semibold">
                      {reviewInfo[selectedReview.review_type]?.short}
                    </span>
                  </div>
                  <p className="text-gray-400 text-sm">{selectedProject?.title}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Edit Mode Toggle for Completed Reviews */}
                {selectedReview.status === 'completed' && (
                  <button
                    onClick={() => setEditMode(!editMode)}
                    className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors ${
                      editMode
                        ? 'bg-amber-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                  >
                    {editMode ? (
                      <>
                        <Eye className="w-4 h-4" /> View Mode
                      </>
                    ) : (
                      <>
                        <MessageSquare className="w-4 h-4" /> Edit Mode
                      </>
                    )}
                  </button>
                )}
                <button
                  onClick={() => { setShowReviewModal(false); setEditMode(false) }}
                  className="w-10 h-10 bg-gray-700 hover:bg-gray-600 rounded-xl flex items-center justify-center text-gray-400 hover:text-white"
                >
                  <XCircle className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
              {loadingDetails ? (
                <div className="text-center py-12">
                  <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mx-auto" />
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Project Info */}
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                      <p className="text-gray-500 text-xs uppercase mb-1">Technology</p>
                      <p className="text-white font-medium">{selectedProject?.technology_stack || '-'}</p>
                    </div>
                    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                      <p className="text-gray-500 text-xs uppercase mb-1">Domain</p>
                      <p className="text-white font-medium">{selectedProject?.domain || '-'}</p>
                    </div>
                    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                      <p className="text-gray-500 text-xs uppercase mb-1">Guide</p>
                      <p className="text-white font-medium">{selectedProject?.guide_name || '-'}</p>
                    </div>
                    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                      <p className="text-gray-500 text-xs uppercase mb-1">Team Size</p>
                      <p className="text-white font-medium">{selectedProject?.team_size || '-'} members</p>
                    </div>
                  </div>

                  {/* Student Submission Info */}
                  {reviewDetails?.submitted_at && (
                    <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-5">
                      <h4 className="text-orange-400 font-semibold mb-3 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5" /> Student Submission
                      </h4>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <p className="text-gray-500 text-xs mb-1">Submitted At</p>
                          <p className="text-white">{new Date(reviewDetails.submitted_at).toLocaleString()}</p>
                        </div>
                        {reviewDetails.submission_url && (
                          <div>
                            <p className="text-gray-500 text-xs mb-1">Documentation/Report</p>
                            <a href={reviewDetails.submission_url} target="_blank" rel="noopener noreferrer"
                              className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-sm">
                              <FileText className="w-4 h-4" /> View Document
                            </a>
                          </div>
                        )}
                        {selectedProject?.github_url && (
                          <div>
                            <p className="text-gray-500 text-xs mb-1">GitHub Repository</p>
                            <a href={selectedProject.github_url} target="_blank" rel="noopener noreferrer"
                              className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-sm">
                              <Code className="w-4 h-4" /> View Code
                            </a>
                          </div>
                        )}
                        {selectedProject?.demo_url && (
                          <div>
                            <p className="text-gray-500 text-xs mb-1">Live Demo</p>
                            <a href={selectedProject.demo_url} target="_blank" rel="noopener noreferrer"
                              className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-sm">
                              <Eye className="w-4 h-4" /> View Demo
                            </a>
                          </div>
                        )}
                      </div>
                      {reviewDetails.submission_notes && (
                        <div className="mt-3 pt-3 border-t border-orange-500/20">
                          <p className="text-gray-500 text-xs mb-1">Student Notes</p>
                          <p className="text-gray-300 text-sm">{reviewDetails.submission_notes}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Scoring Section */}
                  <div className="bg-gray-800/30 rounded-xl p-5 border border-gray-700">
                    <h4 className="text-white font-semibold mb-4 flex items-center gap-2">
                      <Star className="w-5 h-5 text-amber-400" /> Scoring (Total: {totalScore}/100)
                    </h4>
                    <div className="grid grid-cols-6 gap-4">
                      {[
                        { k: 'innovation', l: 'Innovation', m: 20 },
                        { k: 'technical', l: 'Technical', m: 25 },
                        { k: 'implementation', l: 'Implementation', m: 25 },
                        { k: 'documentation', l: 'Documentation', m: 15 },
                        { k: 'presentation', l: 'Presentation', m: 15 }
                      ].map(f => (
                        <div key={f.k}>
                          <label className="text-gray-400 text-xs mb-2 block">{f.l} (0-{f.m})</label>
                          <input
                            type="number"
                            min="0"
                            max={f.m}
                            step="1"
                            value={scores[f.k as keyof typeof scores] || ''}
                            onChange={e => setScores({ ...scores, [f.k]: Math.min(f.m, Math.round(Number(e.target.value) || 0)) })}
                            disabled={selectedReview.status === 'completed' && !editMode}
                            className="w-full px-3 py-2.5 bg-gray-900 border border-gray-600 rounded-lg text-white text-center text-lg font-bold disabled:opacity-50 focus:border-indigo-500 focus:outline-none"
                          />
                        </div>
                      ))}
                      <div className="flex items-center justify-center bg-indigo-500/10 rounded-xl border border-indigo-500/30">
                        <div className="text-center">
                          <p className="text-3xl font-bold text-white">{totalScore}</p>
                          <p className="text-gray-400 text-xs">/100</p>
                        </div>
                      </div>
                    </div>
                    {(selectedReview.status !== 'completed' || editMode) && (
                      <div className="flex justify-end mt-4">
                        <button onClick={handleSaveScore} disabled={saving} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                          {saving ? 'Saving...' : 'Save Scores'}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Feedback Section */}
                  <div className="bg-gray-800/30 rounded-xl p-5 border border-gray-700">
                    <h4 className="text-white font-semibold mb-4 flex items-center gap-2">
                      <MessageSquare className="w-5 h-5 text-emerald-400" /> Feedback
                    </h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-gray-400 text-xs mb-2 block">Strengths</label>
                        <textarea
                          value={feedback.strengths}
                          onChange={e => setFeedback({ ...feedback, strengths: e.target.value })}
                          rows={3}
                          disabled={selectedReview.status === 'completed' && !editMode}
                          placeholder="What did the team do well?"
                          className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white resize-none disabled:opacity-50 focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-gray-400 text-xs mb-2 block">Areas for Improvement</label>
                        <textarea
                          value={feedback.weaknesses}
                          onChange={e => setFeedback({ ...feedback, weaknesses: e.target.value })}
                          rows={3}
                          disabled={selectedReview.status === 'completed' && !editMode}
                          placeholder="What needs improvement?"
                          className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white resize-none disabled:opacity-50 focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-gray-400 text-xs mb-2 block">Suggestions / Action Items</label>
                        <textarea
                          value={feedback.suggestions}
                          onChange={e => setFeedback({ ...feedback, suggestions: e.target.value })}
                          rows={3}
                          disabled={selectedReview.status === 'completed' && !editMode}
                          placeholder="Specific actions for next review..."
                          className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white resize-none disabled:opacity-50 focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                      <div>
                        <label className="text-gray-400 text-xs mb-2 block">Overall Feedback</label>
                        <textarea
                          value={feedback.overall}
                          onChange={e => setFeedback({ ...feedback, overall: e.target.value })}
                          rows={3}
                          disabled={selectedReview.status === 'completed' && !editMode}
                          placeholder="Summary of the review..."
                          className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white resize-none disabled:opacity-50 focus:border-indigo-500 focus:outline-none"
                        />
                      </div>
                    </div>
                    {(selectedReview.status !== 'completed' || editMode) && (
                      <div className="flex justify-end mt-4">
                        <button onClick={handleSaveFeedback} disabled={saving} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                          {saving ? 'Saving...' : 'Save Feedback'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer - Actions */}
            {selectedReview.status === 'in_progress' && !loadingDetails && (
              <div className="bg-gray-800/50 border-t border-gray-700 px-6 py-4 flex justify-between items-center shrink-0">
                <div className="flex gap-3">
                  <button
                    onClick={() => handleDecision('approved')}
                    disabled={saving}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold flex items-center gap-2 disabled:opacity-50"
                  >
                    <CheckCircle className="w-5 h-5" /> Approve
                  </button>
                  <button
                    onClick={() => handleDecision('revision_needed')}
                    disabled={saving}
                    className="px-5 py-2.5 bg-amber-600 hover:bg-amber-500 text-white rounded-xl font-semibold flex items-center gap-2 disabled:opacity-50"
                  >
                    <RefreshCw className="w-5 h-5" /> Request Revision
                  </button>
                </div>
                <button
                  onClick={handleComplete}
                  className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-semibold flex items-center gap-2"
                >
                  <Award className="w-5 h-5" /> Complete Review
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-xl flex items-center gap-2 z-50 ${
          toast.type === 'success' ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {toast.type === 'success' ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      )}
    </div>
  )
}

function NAACReports() {
  const [allotmentData, setAllotmentData] = useState<any>(null)
  const [scheduleData, setScheduleData] = useState<any>(null)
  const [logsData, setLogsData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeReport, setActiveReport] = useState<'allotment' | 'schedule' | 'logs'>('allotment')

  useEffect(() => { fetchNAACData() }, [])

  const fetchNAACData = async () => {
    setLoading(true)
    try {
      const [allotment, schedule, logs] = await Promise.all([
        fetch(`${API_BASE}/project-guidance/naac/project-allotment-list`).then(r => r.json()),
        fetch(`${API_BASE}/project-guidance/naac/review-schedule`).then(r => r.json()),
        fetch(`${API_BASE}/project-guidance/naac/approval-logs`).then(r => r.json())
      ])
      setAllotmentData(allotment)
      setScheduleData(schedule)
      setLogsData(logs)
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="flex-1 p-6 overflow-auto">
      <div className="flex gap-2 mb-6">
        {[
          { key: 'allotment', label: 'Project Allotment', icon: FileText },
          { key: 'schedule', label: 'Review Schedule', icon: Calendar },
          { key: 'logs', label: 'Approval Logs', icon: Shield }
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveReport(tab.key as any)}
            className={`px-5 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
              activeReport === tab.key
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeReport === 'allotment' && allotmentData && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <div className="flex justify-between items-center p-5 border-b border-gray-700">
            <h3 className="text-lg font-semibold text-white">{allotmentData.title}</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 bg-gray-900/50">
                <th className="px-5 py-3 font-medium">S.No</th>
                <th className="px-5 py-3 font-medium">Title</th>
                <th className="px-5 py-3 font-medium">Team</th>
                <th className="px-5 py-3 font-medium">Guide</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {allotmentData.projects?.map((p: any) => (
                <tr key={p.sl_no} className="border-t border-gray-700 text-gray-300 hover:bg-gray-800/30">
                  <td className="px-5 py-3">{p.sl_no}</td>
                  <td className="px-5 py-3 max-w-xs truncate">{p.title}</td>
                  <td className="px-5 py-3">{p.team_name}</td>
                  <td className="px-5 py-3">{p.guide_name}</td>
                  <td className="px-5 py-3">{p.project_type}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      p.status === 'Completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
                    }`}>
                      {p.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeReport === 'schedule' && scheduleData && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-gray-700">
            <h3 className="text-lg font-semibold text-white">{scheduleData.title}</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-gray-400 bg-gray-900/50">
                <th className="px-5 py-3 font-medium">Project</th>
                <th className="px-5 py-3 font-medium">Review</th>
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="px-5 py-3 font-medium">Venue</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              {scheduleData.reviews?.map((r: any, i: number) => (
                <tr key={i} className="border-t border-gray-700 text-gray-300 hover:bg-gray-800/30">
                  <td className="px-5 py-3">{r.project_title}</td>
                  <td className="px-5 py-3">{r.review_type}</td>
                  <td className="px-5 py-3">{r.scheduled_date ? new Date(r.scheduled_date).toLocaleDateString() : '-'}</td>
                  <td className="px-5 py-3">{r.venue || '-'}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      r.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-5 py-3">{r.score || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeReport === 'logs' && logsData && (
        <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-white mb-4">Approval Logs</h3>
          {logsData.length > 0 ? (
            <div className="space-y-3">
              {logsData.map((log: any) => (
                <div key={log.id} className="bg-gray-900/50 rounded-xl p-4 flex justify-between items-center border border-gray-700">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-lg text-xs font-medium ${
                      log.action?.includes('locked') ? 'bg-yellow-500/20 text-yellow-400' :
                      log.action?.includes('completed') ? 'bg-emerald-500/20 text-emerald-400' :
                      'bg-indigo-500/20 text-indigo-400'
                    }`}>
                      {log.action}
                    </span>
                    <span className="text-gray-300">Phase {log.phase_number}</span>
                    {log.performed_by && <span className="text-gray-500">by {log.performed_by}</span>}
                  </div>
                  <span className="text-gray-400 text-sm">{new Date(log.timestamp).toLocaleString()}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">No logs found</div>
          )}
        </div>
      )}
    </div>
  )
}
