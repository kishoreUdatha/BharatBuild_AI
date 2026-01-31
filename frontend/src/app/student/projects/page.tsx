'use client'

import { useState, useEffect } from 'react'
import {
  BookOpen, CheckCircle, Clock, Lock, AlertCircle, Send,
  FileText, Github, ExternalLink, Award, Star, ChevronRight,
  Loader2, RefreshCw, MessageSquare, Target, XCircle, Calendar,
  User, Users, Code, TrendingUp
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Review {
  id: string
  review_type: string
  review_number: number
  status: string
  phase_status: string
  scheduled_date: string | null
  scheduled_time: string | null
  venue: string | null
  submitted_at: string | null
  submission_url: string | null
  submission_notes: string | null
  completed_at: string | null
  total_score: number
  decision: string | null
  is_locked: boolean
  feedback: {
    strengths: string | null
    weaknesses: string | null
    suggestions: string | null
    overall: string | null
    action_items: string | null
  }
  scores: {
    innovation: number
    technical: number
    implementation: number
    documentation: number
    presentation: number
  }
}

interface Project {
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
  github_url: string | null
  demo_url: string | null
  current_phase: number
  current_review: string | null
  total_score: number
  average_score: number
  is_approved: boolean
  is_completed: boolean
  progress_percent: number
  team_members: { name: string; roll_number: string; role: string }[]
  reviews: Review[]
}

const reviewInfo: Record<string, { name: string; short: string; description: string }> = {
  review_1: { name: 'Review 1', short: 'R1', description: 'Problem Statement & Literature Survey' },
  review_2: { name: 'Review 2', short: 'R2', description: 'System Design & Architecture' },
  review_3: { name: 'Review 3', short: 'R3', description: 'Implementation Progress (50%)' },
  final_review: { name: 'Final Review', short: 'Final', description: 'Complete Project Demo' }
}

export default function StudentProjectsPage() {
  const [project, setProject] = useState<Project | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedReview, setSelectedReview] = useState<Review | null>(null)
  const [showSubmitModal, setShowSubmitModal] = useState(false)
  const [showFeedbackModal, setShowFeedbackModal] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submission, setSubmission] = useState({
    submission_url: '',
    submission_notes: '',
    github_url: '',
    demo_url: ''
  })
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null)

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  useEffect(() => { fetchProject() }, [])

  const fetchProject = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/project-guidance/student/my-project`)
      if (res.ok) {
        const data = await res.json()
        setProject(data)
      }
    } catch (e) { console.error(e) }
    setLoading(false)
  }

  const handleSubmit = async () => {
    if (!selectedReview) return
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/project-guidance/reviews/${selectedReview.id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(submission)
      })
      if (res.ok) {
        showToast('Submitted successfully!')
        setShowSubmitModal(false)
        setSubmission({ submission_url: '', submission_notes: '', github_url: '', demo_url: '' })
        fetchProject()
      } else {
        showToast('Submission failed', 'error')
      }
    } catch (e) {
      showToast('Submission failed', 'error')
    }
    setSubmitting(false)
  }

  const getStatusIcon = (review: Review) => {
    if (review.status === 'completed') return <CheckCircle className="w-5 h-5 text-emerald-400" />
    if (review.phase_status === 'submitted') return <Clock className="w-5 h-5 text-amber-400" />
    if (review.is_locked) return <Lock className="w-5 h-5 text-gray-500" />
    if (review.status === 'scheduled') return <Calendar className="w-5 h-5 text-blue-400" />
    return <AlertCircle className="w-5 h-5 text-gray-500" />
  }

  const getStatusText = (review: Review) => {
    if (review.status === 'completed') return 'Completed'
    if (review.phase_status === 'submitted') return 'Awaiting Review'
    if (review.status === 'in_progress') return 'Under Review'
    if (review.is_locked) return 'Locked'
    if (review.status === 'scheduled') return 'Scheduled'
    return 'Pending'
  }

  const getStatusColor = (review: Review) => {
    if (review.status === 'completed') return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
    if (review.phase_status === 'submitted') return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
    if (review.status === 'in_progress') return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin mx-auto mb-3" />
          <p className="text-gray-400">Loading your project...</p>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">No Project Found</h2>
          <p className="text-gray-400 mb-4">You haven't registered a project yet.</p>
          <button className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium">
            Register Project
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800/50 border-b border-gray-700 px-6 py-4 shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">My Project</h1>
            <p className="text-gray-400 text-sm">Track your project progress and reviews</p>
          </div>
          <button onClick={fetchProject} className="p-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-gray-300">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scrollbar-hide">
        {/* Project Overview Card */}
        <div className="bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-2xl p-6 mb-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-indigo-500/30 rounded-xl flex items-center justify-center">
                <BookOpen className="w-7 h-7 text-indigo-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{project.title}</h2>
                <div className="flex items-center gap-3 mt-1">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    project.project_type === 'major_project'
                      ? 'bg-orange-500/20 text-orange-300'
                      : 'bg-cyan-500/20 text-cyan-300'
                  }`}>
                    {project.project_type === 'major_project' ? 'Major Project' : 'Mini Project'}
                  </span>
                  <span className="text-gray-400 text-sm">{project.domain}</span>
                </div>
              </div>
            </div>
            {project.is_completed && (
              <div className={`px-4 py-2 rounded-xl font-semibold flex items-center gap-2 ${
                project.is_approved ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'
              }`}>
                {project.is_approved ? <Award className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                {project.is_approved ? 'Approved' : 'Pending Approval'}
              </div>
            )}
          </div>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm">Overall Progress</span>
              <span className="text-white font-semibold">{Math.round(project.progress_percent)}%</span>
            </div>
            <div className="w-full h-3 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all"
                style={{ width: `${project.progress_percent}%` }}
              />
            </div>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-800/50 rounded-xl p-3 text-center">
              <p className="text-gray-500 text-xs mb-1">Team</p>
              <p className="text-white font-semibold">{project.team_name}</p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3 text-center">
              <p className="text-gray-500 text-xs mb-1">Guide</p>
              <p className="text-white font-semibold">{project.guide_name || 'Not Assigned'}</p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3 text-center">
              <p className="text-gray-500 text-xs mb-1">Current Phase</p>
              <p className="text-white font-semibold">Phase {project.current_phase}</p>
            </div>
            <div className="bg-gray-800/50 rounded-xl p-3 text-center">
              <p className="text-gray-500 text-xs mb-1">Avg Score</p>
              <p className="text-emerald-400 font-bold text-lg">{project.average_score.toFixed(1)}</p>
            </div>
          </div>
        </div>

        {/* Reviews Timeline */}
        <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-6 mb-6">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-indigo-400" />
            Review Timeline
          </h3>

          <div className="space-y-4">
            {['review_1', 'review_2', 'review_3', 'final_review'].map((reviewType, index) => {
              const review = project.reviews.find(r => r.review_type === reviewType)
              const info = reviewInfo[reviewType]
              const isCurrentPhase = project.current_review === reviewType

              return (
                <div
                  key={reviewType}
                  className={`relative flex items-center gap-4 p-4 rounded-xl border transition-all ${
                    isCurrentPhase
                      ? 'bg-indigo-500/10 border-indigo-500/50'
                      : review?.status === 'completed'
                      ? 'bg-emerald-500/5 border-emerald-500/20'
                      : 'bg-gray-800/50 border-gray-700'
                  }`}
                >
                  {/* Timeline connector */}
                  {index < 3 && (
                    <div className={`absolute left-[2.35rem] top-full w-0.5 h-4 ${
                      review?.status === 'completed' ? 'bg-emerald-500/50' : 'bg-gray-700'
                    }`} />
                  )}

                  {/* Review number badge */}
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-lg font-bold shrink-0 ${
                    review?.status === 'completed'
                      ? 'bg-emerald-500/20 text-emerald-400'
                      : isCurrentPhase
                      ? 'bg-indigo-500/20 text-indigo-400'
                      : 'bg-gray-700 text-gray-400'
                  }`}>
                    {info.short}
                  </div>

                  {/* Review info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-white font-medium">{info.name}</h4>
                      {review && (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getStatusColor(review)}`}>
                          {getStatusText(review)}
                        </span>
                      )}
                    </div>
                    <p className="text-gray-500 text-sm">{info.description}</p>
                    {review?.scheduled_date && review.status !== 'completed' && (
                      <p className="text-gray-400 text-xs mt-1 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Scheduled: {new Date(review.scheduled_date).toLocaleDateString()} {review.scheduled_time}
                      </p>
                    )}
                    {review?.status === 'completed' && (
                      <p className="text-emerald-400 text-sm mt-1 font-semibold">
                        Score: {review.total_score}/100
                      </p>
                    )}
                  </div>

                  {/* Action buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    {review?.status === 'completed' ? (
                      <button
                        onClick={() => { setSelectedReview(review); setShowFeedbackModal(true) }}
                        className="px-3 py-2 bg-emerald-600/20 text-emerald-400 rounded-lg text-sm font-medium hover:bg-emerald-600/30 flex items-center gap-1.5"
                      >
                        <MessageSquare className="w-4 h-4" /> View Feedback
                      </button>
                    ) : review?.phase_status === 'submitted' ? (
                      <span className="px-3 py-2 bg-amber-500/10 text-amber-400 rounded-lg text-sm font-medium flex items-center gap-1.5">
                        <Clock className="w-4 h-4" /> Awaiting Faculty Review
                      </span>
                    ) : review && review.status === 'scheduled' && !review.is_locked ? (
                      <button
                        onClick={() => {
                          setSelectedReview(review)
                          setSubmission({
                            submission_url: review.submission_url || '',
                            submission_notes: review.submission_notes || '',
                            github_url: project.github_url || '',
                            demo_url: project.demo_url || ''
                          })
                          setShowSubmitModal(true)
                        }}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium flex items-center gap-1.5"
                      >
                        <Send className="w-4 h-4" /> Submit for Review
                      </button>
                    ) : !review ? (
                      <span className="px-3 py-2 bg-gray-700/50 text-gray-500 rounded-lg text-sm font-medium flex items-center gap-1.5">
                        <Lock className="w-4 h-4" /> Not Scheduled
                      </span>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Project Details Grid */}
        <div className="grid grid-cols-2 gap-6">
          {/* Team Members */}
          <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-5">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-purple-400" />
              Team Members
            </h3>
            <div className="space-y-3">
              {project.team_members.map((member, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
                  <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-white font-medium">{member.name}</p>
                    <p className="text-gray-500 text-xs">{member.roll_number} • {member.role}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Project Links */}
          <div className="bg-gray-800/30 border border-gray-700 rounded-xl p-5">
            <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
              <Code className="w-5 h-5 text-cyan-400" />
              Project Links
            </h3>
            <div className="space-y-3">
              {project.github_url ? (
                <a
                  href={project.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-700/50 transition-colors"
                >
                  <Github className="w-5 h-5 text-gray-400" />
                  <span className="text-white">GitHub Repository</span>
                  <ExternalLink className="w-4 h-4 text-gray-500 ml-auto" />
                </a>
              ) : (
                <div className="flex items-center gap-3 p-3 bg-gray-800/30 rounded-lg text-gray-500">
                  <Github className="w-5 h-5" />
                  <span>GitHub not linked</span>
                </div>
              )}
              {project.demo_url ? (
                <a
                  href={project.demo_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg hover:bg-gray-700/50 transition-colors"
                >
                  <ExternalLink className="w-5 h-5 text-gray-400" />
                  <span className="text-white">Live Demo</span>
                  <ExternalLink className="w-4 h-4 text-gray-500 ml-auto" />
                </a>
              ) : (
                <div className="flex items-center gap-3 p-3 bg-gray-800/30 rounded-lg text-gray-500">
                  <ExternalLink className="w-5 h-5" />
                  <span>Demo not available</span>
                </div>
              )}
              <div className="flex items-center gap-3 p-3 bg-gray-800/50 rounded-lg">
                <FileText className="w-5 h-5 text-gray-400" />
                <div>
                  <span className="text-white">Technology Stack</span>
                  <p className="text-gray-500 text-sm">{project.technology_stack || 'Not specified'}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Submit Modal */}
      {showSubmitModal && selectedReview && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-2xl max-w-lg w-full border border-gray-700 shadow-2xl">
            <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
              <div>
                <h3 className="text-white font-bold text-lg">Submit for {reviewInfo[selectedReview.review_type]?.name}</h3>
                <p className="text-gray-400 text-sm">{reviewInfo[selectedReview.review_type]?.description}</p>
              </div>
              <button
                onClick={() => setShowSubmitModal(false)}
                className="w-10 h-10 bg-gray-700 hover:bg-gray-600 rounded-xl flex items-center justify-center text-gray-400"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div>
                <label className="text-gray-400 text-sm mb-2 block">GitHub Repository URL</label>
                <input
                  type="url"
                  value={submission.github_url}
                  onChange={e => setSubmission({ ...submission, github_url: e.target.value })}
                  placeholder="https://github.com/..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-gray-400 text-sm mb-2 block">Demo / Deployment URL (optional)</label>
                <input
                  type="url"
                  value={submission.demo_url}
                  onChange={e => setSubmission({ ...submission, demo_url: e.target.value })}
                  placeholder="https://..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-gray-400 text-sm mb-2 block">Documentation / Report URL (optional)</label>
                <input
                  type="url"
                  value={submission.submission_url}
                  onChange={e => setSubmission({ ...submission, submission_url: e.target.value })}
                  placeholder="https://drive.google.com/..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white focus:border-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-gray-400 text-sm mb-2 block">Notes for Reviewer</label>
                <textarea
                  value={submission.submission_notes}
                  onChange={e => setSubmission({ ...submission, submission_notes: e.target.value })}
                  rows={3}
                  placeholder="Describe what you've completed, any challenges, or specific areas you'd like feedback on..."
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-xl text-white resize-none focus:border-indigo-500 focus:outline-none"
                />
              </div>
            </div>

            <div className="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowSubmitModal(false)}
                className="px-4 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-medium flex items-center gap-2 disabled:opacity-50"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Modal */}
      {showFeedbackModal && selectedReview && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden border border-gray-700 shadow-2xl flex flex-col">
            <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                  selectedReview.decision === 'approved'
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-amber-500/20 text-amber-400'
                }`}>
                  {selectedReview.decision === 'approved' ? <CheckCircle className="w-6 h-6" /> : <AlertCircle className="w-6 h-6" />}
                </div>
                <div>
                  <h3 className="text-white font-bold text-lg">{reviewInfo[selectedReview.review_type]?.name} Feedback</h3>
                  <p className="text-gray-400 text-sm">
                    Score: <span className="text-emerald-400 font-semibold">{selectedReview.total_score}/100</span>
                    {selectedReview.decision && (
                      <span className={`ml-2 px-2 py-0.5 rounded text-xs font-medium ${
                        selectedReview.decision === 'approved'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-amber-500/20 text-amber-400'
                      }`}>
                        {selectedReview.decision === 'approved' ? 'Approved' : 'Revision Needed'}
                      </span>
                    )}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowFeedbackModal(false)}
                className="w-10 h-10 bg-gray-700 hover:bg-gray-600 rounded-xl flex items-center justify-center text-gray-400"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Score Breakdown */}
              <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700">
                <h4 className="text-white font-semibold mb-3 flex items-center gap-2">
                  <Star className="w-4 h-4 text-amber-400" /> Score Breakdown
                </h4>
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { k: 'innovation', l: 'Innovation', m: 20 },
                    { k: 'technical', l: 'Technical', m: 25 },
                    { k: 'implementation', l: 'Implementation', m: 25 },
                    { k: 'documentation', l: 'Documentation', m: 15 },
                    { k: 'presentation', l: 'Presentation', m: 15 }
                  ].map(f => (
                    <div key={f.k} className="text-center p-3 bg-gray-900/50 rounded-lg">
                      <p className="text-gray-500 text-xs mb-1">{f.l}</p>
                      <p className="text-white font-bold">
                        {selectedReview.scores[f.k as keyof typeof selectedReview.scores]}/{f.m}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Feedback Sections */}
              {selectedReview.feedback.strengths && (
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4">
                  <h4 className="text-emerald-400 font-semibold mb-2 flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" /> Strengths
                  </h4>
                  <p className="text-gray-300 text-sm whitespace-pre-wrap">{selectedReview.feedback.strengths}</p>
                </div>
              )}

              {selectedReview.feedback.weaknesses && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4">
                  <h4 className="text-amber-400 font-semibold mb-2 flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" /> Areas for Improvement
                  </h4>
                  <p className="text-gray-300 text-sm whitespace-pre-wrap">{selectedReview.feedback.weaknesses}</p>
                </div>
              )}

              {selectedReview.feedback.suggestions && (
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
                  <h4 className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" /> Suggestions
                  </h4>
                  <p className="text-gray-300 text-sm whitespace-pre-wrap">{selectedReview.feedback.suggestions}</p>
                </div>
              )}

              {selectedReview.feedback.action_items && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                  <h4 className="text-purple-400 font-semibold mb-2 flex items-center gap-2">
                    <Target className="w-4 h-4" /> Action Items for Next Review
                  </h4>
                  <p className="text-gray-300 text-sm whitespace-pre-wrap">{selectedReview.feedback.action_items}</p>
                </div>
              )}

              {selectedReview.feedback.overall && (
                <div className="bg-gray-800/50 border border-gray-700 rounded-xl p-4">
                  <h4 className="text-gray-300 font-semibold mb-2 flex items-center gap-2">
                    <MessageSquare className="w-4 h-4" /> Overall Feedback
                  </h4>
                  <p className="text-gray-300 text-sm whitespace-pre-wrap">{selectedReview.feedback.overall}</p>
                </div>
              )}
            </div>
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
