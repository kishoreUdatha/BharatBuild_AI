'use client'

import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Assignment {
  id: string
  title: string
  subject: string
  description: string
  due_date: string
  batch_id: string
  problem_type: string
  difficulty: string
  language: string
  max_score: number
  submitted_count: number
  graded_count: number
  avg_score: number
  total_students: number
  status: string
  created_at: string
}

interface TestCase {
  input: string
  expected_output: string
  is_hidden: boolean
  weight: number
}

interface Batch {
  id: string
  name: string
  students: number
}

export default function AssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [batches, setBatches] = useState<Batch[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [creating, setCreating] = useState(false)

  // Filter states
  const [selectedBatch, setSelectedBatch] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('')
  const [selectedSubject, setSelectedSubject] = useState('')

  // Form state
  const [formData, setFormData] = useState({
    title: '',
    subject: '',
    description: '',
    due_date: '',
    batch_id: '',
    problem_type: 'coding',
    difficulty: 'medium',
    language: 'python',
    max_score: 100,
    allow_late_submission: false,
    late_penalty_percent: 10,
    enable_plagiarism_check: true,
    starter_code: '',
    test_cases: [{ input: '', expected_output: '', is_hidden: false, weight: 1 }] as TestCase[]
  })

  useEffect(() => {
    fetchData()
  }, [selectedBatch, selectedStatus, selectedSubject])

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('access_token')

      // Fetch batches
      const batchesRes = await fetch(`${API_BASE}/faculty/batches`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (batchesRes.ok) {
        setBatches(await batchesRes.json())
      }

      // Fetch assignments
      const params = new URLSearchParams()
      if (selectedBatch) params.append('batch_id', selectedBatch)
      if (selectedStatus) params.append('status', selectedStatus)
      if (selectedSubject) params.append('subject', selectedSubject)

      const assignmentsRes = await fetch(`${API_BASE}/faculty/assignments?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (assignmentsRes.ok) {
        setAssignments(await assignmentsRes.json())
      }
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const handleCreateAssignment = async () => {
    setCreating(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/faculty/assignments`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          due_date: new Date(formData.due_date).toISOString()
        })
      })

      if (res.ok) {
        setShowCreateModal(false)
        setFormData({
          title: '',
          subject: '',
          description: '',
          due_date: '',
          batch_id: '',
          problem_type: 'coding',
          difficulty: 'medium',
          language: 'python',
          max_score: 100,
          allow_late_submission: false,
          late_penalty_percent: 10,
          enable_plagiarism_check: true,
          starter_code: '',
          test_cases: [{ input: '', expected_output: '', is_hidden: false, weight: 1 }]
        })
        fetchData()
      }
    } catch (e) {
      console.error(e)
    }
    setCreating(false)
  }

  const addTestCase = () => {
    setFormData({
      ...formData,
      test_cases: [...formData.test_cases, { input: '', expected_output: '', is_hidden: false, weight: 1 }]
    })
  }

  const removeTestCase = (index: number) => {
    setFormData({
      ...formData,
      test_cases: formData.test_cases.filter((_, i) => i !== index)
    })
  }

  const updateTestCase = (index: number, field: string, value: any) => {
    const updated = [...formData.test_cases]
    updated[index] = { ...updated[index], [field]: value }
    setFormData({ ...formData, test_cases: updated })
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-emerald-500/20 text-emerald-400'
      case 'medium': return 'bg-amber-500/20 text-amber-400'
      case 'hard': return 'bg-red-500/20 text-red-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="h-full">
      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Page Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-white font-semibold text-lg">Assignments</h1>
            <p className="text-gray-500 text-xs">Create and manage coding assignments</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Assignment
          </button>
        </div>
        {/* Filters */}
        <div className="flex gap-4 mb-6">
          <select
            value={selectedBatch}
            onChange={(e) => setSelectedBatch(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
          >
            <option value="">All Batches</option>
            {batches.map((batch) => (
              <option key={batch.id} value={batch.id}>{batch.name}</option>
            ))}
          </select>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="closed">Closed</option>
          </select>
          <input
            type="text"
            value={selectedSubject}
            onChange={(e) => setSelectedSubject(e.target.value)}
            placeholder="Filter by subject..."
            className="flex-1 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500"
          />
        </div>

        {/* Assignments Grid */}
        {assignments.length === 0 ? (
          <div className="text-center py-16 bg-gray-900/50 border border-gray-800 rounded-xl">
            <svg className="w-16 h-16 text-gray-600 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <h3 className="text-white font-medium mb-2">No Assignments Yet</h3>
            <p className="text-gray-400 text-sm mb-4">Create your first assignment to get started</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm"
            >
              Create Assignment
            </button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {assignments.map((assignment) => (
              <div key={assignment.id} className="bg-gray-900/50 border border-gray-800 rounded-xl p-5 hover:border-gray-700 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-white font-medium">{assignment.title}</h3>
                    <p className="text-gray-500 text-xs">{assignment.subject}</p>
                  </div>
                  <span className={`px-2 py-1 rounded text-xs ${getDifficultyColor(assignment.difficulty)}`}>
                    {assignment.difficulty}
                  </span>
                </div>
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">{assignment.description}</p>

                <div className="grid grid-cols-3 gap-2 mb-4">
                  <div className="text-center p-2 bg-gray-800/50 rounded-lg">
                    <p className="text-white font-medium">{assignment.submitted_count}</p>
                    <p className="text-gray-500 text-xs">Submitted</p>
                  </div>
                  <div className="text-center p-2 bg-gray-800/50 rounded-lg">
                    <p className="text-white font-medium">{assignment.graded_count}</p>
                    <p className="text-gray-500 text-xs">Graded</p>
                  </div>
                  <div className="text-center p-2 bg-gray-800/50 rounded-lg">
                    <p className="text-white font-medium">{assignment.avg_score.toFixed(0)}%</p>
                    <p className="text-gray-500 text-xs">Avg Score</p>
                  </div>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-gray-800">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs ${
                      assignment.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {assignment.status}
                    </span>
                    <span className="text-gray-500 text-xs">
                      Due: {new Date(assignment.due_date).toLocaleDateString()}
                    </span>
                  </div>
                  <button className="text-indigo-400 hover:text-indigo-300 text-sm">
                    View
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Assignment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto scrollbar-hide">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
              <h2 className="text-white font-semibold text-lg">Create Assignment</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Basic Info */}
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Title *</label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    placeholder="Assignment title"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Subject *</label>
                  <input
                    type="text"
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    placeholder="e.g., Data Structures"
                  />
                </div>
              </div>

              <div>
                <label className="text-gray-400 text-sm mb-1 block">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white h-24 resize-none"
                  placeholder="Problem description..."
                />
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Batch *</label>
                  <select
                    value={formData.batch_id}
                    onChange={(e) => setFormData({ ...formData, batch_id: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="">Select batch</option>
                    {batches.map((batch) => (
                      <option key={batch.id} value={batch.id}>{batch.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Due Date *</label>
                  <input
                    type="datetime-local"
                    value={formData.due_date}
                    onChange={(e) => setFormData({ ...formData, due_date: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Max Score</label>
                  <input
                    type="number"
                    value={formData.max_score}
                    onChange={(e) => setFormData({ ...formData, max_score: parseInt(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Problem Type</label>
                  <select
                    value={formData.problem_type}
                    onChange={(e) => setFormData({ ...formData, problem_type: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="coding">Coding</option>
                    <option value="mcq">MCQ</option>
                    <option value="project">Project</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Difficulty</label>
                  <select
                    value={formData.difficulty}
                    onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Language</label>
                  <select
                    value={formData.language}
                    onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="python">Python</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                    <option value="java">Java</option>
                    <option value="javascript">JavaScript</option>
                  </select>
                </div>
              </div>

              {/* Test Cases */}
              {formData.problem_type === 'coding' && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <label className="text-gray-400 text-sm">Test Cases</label>
                    <button
                      type="button"
                      onClick={addTestCase}
                      className="text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Add Test Case
                    </button>
                  </div>
                  <div className="space-y-3">
                    {formData.test_cases.map((tc, index) => (
                      <div key={index} className="bg-gray-800/50 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-gray-400 text-sm">Test Case #{index + 1}</span>
                          {formData.test_cases.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeTestCase(index)}
                              className="text-red-400 hover:text-red-300"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}
                        </div>
                        <div className="grid md:grid-cols-2 gap-3">
                          <div>
                            <label className="text-gray-500 text-xs mb-1 block">Input</label>
                            <textarea
                              value={tc.input}
                              onChange={(e) => updateTestCase(index, 'input', e.target.value)}
                              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm h-20 resize-none font-mono"
                              placeholder="Test input"
                            />
                          </div>
                          <div>
                            <label className="text-gray-500 text-xs mb-1 block">Expected Output</label>
                            <textarea
                              value={tc.expected_output}
                              onChange={(e) => updateTestCase(index, 'expected_output', e.target.value)}
                              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm h-20 resize-none font-mono"
                              placeholder="Expected output"
                            />
                          </div>
                        </div>
                        <div className="flex items-center gap-4 mt-2">
                          <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
                            <input
                              type="checkbox"
                              checked={tc.is_hidden}
                              onChange={(e) => updateTestCase(index, 'is_hidden', e.target.checked)}
                              className="rounded bg-gray-700 border-gray-600"
                            />
                            Hidden
                          </label>
                          <div className="flex items-center gap-2">
                            <span className="text-gray-500 text-xs">Weight:</span>
                            <input
                              type="number"
                              value={tc.weight}
                              onChange={(e) => updateTestCase(index, 'weight', parseInt(e.target.value))}
                              className="w-16 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white text-sm"
                              min="1"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Options */}
              <div className="flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.allow_late_submission}
                    onChange={(e) => setFormData({ ...formData, allow_late_submission: e.target.checked })}
                    className="rounded bg-gray-700 border-gray-600"
                  />
                  Allow late submissions
                </label>
                <label className="flex items-center gap-2 text-gray-400 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.enable_plagiarism_check}
                    onChange={(e) => setFormData({ ...formData, enable_plagiarism_check: e.target.checked })}
                    className="rounded bg-gray-700 border-gray-600"
                  />
                  Enable plagiarism check
                </label>
              </div>

              {/* Starter Code */}
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Starter Code (Optional)</label>
                <textarea
                  value={formData.starter_code}
                  onChange={(e) => setFormData({ ...formData, starter_code: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white font-mono text-sm h-32 resize-none"
                  placeholder="# Starter code for students..."
                />
              </div>
            </div>

            <div className="sticky bottom-0 bg-gray-900 border-t border-gray-800 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border border-gray-700 text-gray-400 hover:text-white rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateAssignment}
                disabled={creating || !formData.title || !formData.subject || !formData.batch_id || !formData.due_date}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-800 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
              >
                {creating && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                Create Assignment
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
