'use client'

import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Lab {
  id: string
  name: string
  code: string
  description: string
  branch: string
  semester: string
  technologies: string[]
  total_topics: number
  total_mcqs: number
  total_coding_problems: number
  enrolled_students: number
  is_active: boolean
  created_at: string
}

interface Topic {
  id: string
  title: string
  description: string
  week_number: number
  order_index: number
  concept_content: string
  video_url: string
  mcq_count: number
  coding_count: number
  is_active: boolean
}

export default function LabManagementPage() {
  const [labs, setLabs] = useState<Lab[]>([])
  const [selectedLab, setSelectedLab] = useState<Lab | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
  const [loading, setLoading] = useState(true)
  const [topicsLoading, setTopicsLoading] = useState(false)

  // Modal states
  const [showTopicModal, setShowTopicModal] = useState(false)
  const [showMcqModal, setShowMcqModal] = useState(false)
  const [showProblemModal, setShowProblemModal] = useState(false)
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null)
  const [creating, setCreating] = useState(false)

  // Topic form
  const [topicForm, setTopicForm] = useState({
    title: '',
    description: '',
    week_number: 1,
    order_index: 0,
    concept_content: '',
    video_url: ''
  })

  // MCQ form
  const [mcqForm, setMcqForm] = useState({
    question_text: '',
    options: ['', '', '', ''],
    correct_option: 0,
    explanation: '',
    difficulty: 'medium',
    marks: 1,
    time_limit_seconds: 60,
    tags: ''
  })

  // Problem form
  const [problemForm, setProblemForm] = useState({
    title: '',
    description: '',
    difficulty: 'medium',
    max_score: 100,
    supported_languages: ['python'],
    time_limit_ms: 2000,
    memory_limit_mb: 256,
    starter_code: '',
    test_cases: [{ input: '', expected_output: '', is_sample: true }],
    hints: [''],
    tags: ''
  })

  useEffect(() => {
    fetchLabs()
  }, [])

  useEffect(() => {
    if (selectedLab) {
      fetchTopics(selectedLab.id)
    }
  }, [selectedLab])

  const fetchLabs = async () => {
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/faculty/labs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setLabs(data)
        if (data.length > 0) {
          setSelectedLab(data[0])
        }
      }
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const fetchTopics = async (labId: string) => {
    setTopicsLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/lab/labs/${labId}/topics`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setTopics(await res.json())
      }
    } catch (e) {
      console.error(e)
    }
    setTopicsLoading(false)
  }

  const handleCreateTopic = async () => {
    if (!selectedLab) return
    setCreating(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/lab/labs/${selectedLab.id}/topics`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(topicForm)
      })
      if (res.ok) {
        setShowTopicModal(false)
        setTopicForm({ title: '', description: '', week_number: 1, order_index: 0, concept_content: '', video_url: '' })
        fetchTopics(selectedLab.id)
        fetchLabs() // Refresh lab stats
      }
    } catch (e) {
      console.error(e)
    }
    setCreating(false)
  }

  const handleCreateMcq = async () => {
    if (!selectedTopic) return
    setCreating(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/lab/topics/${selectedTopic.id}/mcqs`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...mcqForm,
          tags: mcqForm.tags ? mcqForm.tags.split(',').map(t => t.trim()) : []
        })
      })
      if (res.ok) {
        setShowMcqModal(false)
        setMcqForm({ question_text: '', options: ['', '', '', ''], correct_option: 0, explanation: '', difficulty: 'medium', marks: 1, time_limit_seconds: 60, tags: '' })
        fetchTopics(selectedLab!.id)
      }
    } catch (e) {
      console.error(e)
    }
    setCreating(false)
  }

  const handleCreateProblem = async () => {
    if (!selectedTopic) return
    setCreating(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/lab/topics/${selectedTopic.id}/problems`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...problemForm,
          tags: problemForm.tags ? problemForm.tags.split(',').map(t => t.trim()) : [],
          hints: problemForm.hints.filter(h => h.trim()),
          starter_code: problemForm.starter_code ? { [problemForm.supported_languages[0]]: problemForm.starter_code } : null
        })
      })
      if (res.ok) {
        setShowProblemModal(false)
        setProblemForm({ title: '', description: '', difficulty: 'medium', max_score: 100, supported_languages: ['python'], time_limit_ms: 2000, memory_limit_mb: 256, starter_code: '', test_cases: [{ input: '', expected_output: '', is_sample: true }], hints: [''], tags: '' })
        fetchTopics(selectedLab!.id)
      }
    } catch (e) {
      console.error(e)
    }
    setCreating(false)
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
        <div className="grid lg:grid-cols-4 gap-6">
          {/* Labs List */}
          <div className="lg:col-span-1">
            <h3 className="text-white font-medium mb-3">Your Labs</h3>
            <div className="space-y-2">
              {labs.length === 0 ? (
                <p className="text-gray-400 text-sm">No labs assigned</p>
              ) : (
                labs.map((lab) => (
                  <button
                    key={lab.id}
                    onClick={() => setSelectedLab(lab)}
                    className={`w-full text-left p-4 rounded-xl border transition-colors ${
                      selectedLab?.id === lab.id
                        ? 'bg-indigo-500/10 border-indigo-500/50'
                        : 'bg-gray-900/50 border-gray-800 hover:border-gray-700'
                    }`}
                  >
                    <h4 className="text-white font-medium">{lab.name}</h4>
                    <p className="text-gray-500 text-xs">{lab.code}</p>
                    <div className="flex gap-2 mt-2">
                      <span className="px-2 py-0.5 bg-gray-800 text-gray-400 rounded text-xs">
                        {lab.total_topics} topics
                      </span>
                      <span className="px-2 py-0.5 bg-gray-800 text-gray-400 rounded text-xs">
                        {lab.enrolled_students} students
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>

          {/* Lab Content */}
          <div className="lg:col-span-3">
            {selectedLab ? (
              <>
                {/* Lab Info */}
                <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 mb-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h2 className="text-white text-xl font-semibold">{selectedLab.name}</h2>
                      <p className="text-gray-400 text-sm">{selectedLab.description}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-lg text-sm ${selectedLab.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-gray-500/20 text-gray-400'}`}>
                      {selectedLab.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                      <p className="text-white text-xl font-bold">{selectedLab.total_topics}</p>
                      <p className="text-gray-500 text-xs">Topics</p>
                    </div>
                    <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                      <p className="text-white text-xl font-bold">{selectedLab.total_mcqs}</p>
                      <p className="text-gray-500 text-xs">MCQs</p>
                    </div>
                    <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                      <p className="text-white text-xl font-bold">{selectedLab.total_coding_problems}</p>
                      <p className="text-gray-500 text-xs">Problems</p>
                    </div>
                    <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                      <p className="text-white text-xl font-bold">{selectedLab.enrolled_students}</p>
                      <p className="text-gray-500 text-xs">Students</p>
                    </div>
                  </div>
                </div>

                {/* Topics */}
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white font-medium">Topics</h3>
                  <button
                    onClick={() => setShowTopicModal(true)}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm flex items-center gap-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Add Topic
                  </button>
                </div>

                {topicsLoading ? (
                  <div className="text-center py-8">
                    <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  </div>
                ) : topics.length === 0 ? (
                  <div className="text-center py-16 bg-gray-900/50 border border-gray-800 rounded-xl">
                    <p className="text-gray-400">No topics yet. Create your first topic.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {topics.map((topic) => (
                      <div key={topic.id} className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className="w-10 h-10 bg-indigo-500/20 rounded-lg flex items-center justify-center text-indigo-400 font-medium">
                              W{topic.week_number}
                            </div>
                            <div>
                              <h4 className="text-white font-medium">{topic.title}</h4>
                              <p className="text-gray-500 text-sm line-clamp-1">{topic.description}</p>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => { setSelectedTopic(topic); setShowMcqModal(true); }}
                              className="px-3 py-1.5 bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 rounded-lg text-xs flex items-center gap-1"
                            >
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                              </svg>
                              MCQ ({topic.mcq_count})
                            </button>
                            <button
                              onClick={() => { setSelectedTopic(topic); setShowProblemModal(true); }}
                              className="px-3 py-1.5 bg-purple-500/20 text-purple-400 hover:bg-purple-500/30 rounded-lg text-xs flex items-center gap-1"
                            >
                              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                              </svg>
                              Problem ({topic.coding_count})
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-16 bg-gray-900/50 border border-gray-800 rounded-xl">
                <p className="text-gray-400">Select a lab to manage its content</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Topic Modal */}
      {showTopicModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto scrollbar-hide">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
              <h2 className="text-white font-semibold">Create Topic</h2>
              <button onClick={() => setShowTopicModal(false)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Title *</label>
                <input
                  type="text"
                  value={topicForm.title}
                  onChange={(e) => setTopicForm({ ...topicForm, title: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Description</label>
                <textarea
                  value={topicForm.description}
                  onChange={(e) => setTopicForm({ ...topicForm, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white h-20 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Week Number</label>
                  <input
                    type="number"
                    value={topicForm.week_number}
                    onChange={(e) => setTopicForm({ ...topicForm, week_number: parseInt(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    min="1"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Order Index</label>
                  <input
                    type="number"
                    value={topicForm.order_index}
                    onChange={(e) => setTopicForm({ ...topicForm, order_index: parseInt(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    min="0"
                  />
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Concept Content (Markdown)</label>
                <textarea
                  value={topicForm.concept_content}
                  onChange={(e) => setTopicForm({ ...topicForm, concept_content: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white h-40 resize-none font-mono text-sm"
                  placeholder="# Introduction..."
                />
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Video URL (Optional)</label>
                <input
                  type="url"
                  value={topicForm.video_url}
                  onChange={(e) => setTopicForm({ ...topicForm, video_url: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="https://youtube.com/..."
                />
              </div>
            </div>
            <div className="sticky bottom-0 bg-gray-900 border-t border-gray-800 px-6 py-4 flex justify-end gap-3">
              <button onClick={() => setShowTopicModal(false)} className="px-4 py-2 border border-gray-700 text-gray-400 rounded-lg text-sm">Cancel</button>
              <button
                onClick={handleCreateTopic}
                disabled={creating || !topicForm.title}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
              >
                {creating && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                Create Topic
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create MCQ Modal */}
      {showMcqModal && selectedTopic && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto scrollbar-hide">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-white font-semibold">Create MCQ</h2>
                <p className="text-gray-500 text-xs">Topic: {selectedTopic.title}</p>
              </div>
              <button onClick={() => setShowMcqModal(false)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Question *</label>
                <textarea
                  value={mcqForm.question_text}
                  onChange={(e) => setMcqForm({ ...mcqForm, question_text: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white h-24 resize-none"
                />
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-2 block">Options *</label>
                <div className="space-y-2">
                  {mcqForm.options.map((opt, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="correct"
                        checked={mcqForm.correct_option === i}
                        onChange={() => setMcqForm({ ...mcqForm, correct_option: i })}
                        className="text-indigo-500"
                      />
                      <input
                        type="text"
                        value={opt}
                        onChange={(e) => {
                          const newOpts = [...mcqForm.options]
                          newOpts[i] = e.target.value
                          setMcqForm({ ...mcqForm, options: newOpts })
                        }}
                        className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
                        placeholder={`Option ${String.fromCharCode(65 + i)}`}
                      />
                    </div>
                  ))}
                </div>
                <p className="text-gray-500 text-xs mt-1">Select the correct answer</p>
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Explanation</label>
                <textarea
                  value={mcqForm.explanation}
                  onChange={(e) => setMcqForm({ ...mcqForm, explanation: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white h-20 resize-none"
                  placeholder="Explain why this is the correct answer..."
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Difficulty</label>
                  <select
                    value={mcqForm.difficulty}
                    onChange={(e) => setMcqForm({ ...mcqForm, difficulty: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Marks</label>
                  <input
                    type="number"
                    value={mcqForm.marks}
                    onChange={(e) => setMcqForm({ ...mcqForm, marks: parseFloat(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    min="0.5"
                    step="0.5"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Time Limit (sec)</label>
                  <input
                    type="number"
                    value={mcqForm.time_limit_seconds}
                    onChange={(e) => setMcqForm({ ...mcqForm, time_limit_seconds: parseInt(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                    min="30"
                  />
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={mcqForm.tags}
                  onChange={(e) => setMcqForm({ ...mcqForm, tags: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="loops, arrays, basics"
                />
              </div>
            </div>
            <div className="sticky bottom-0 bg-gray-900 border-t border-gray-800 px-6 py-4 flex justify-end gap-3">
              <button onClick={() => setShowMcqModal(false)} className="px-4 py-2 border border-gray-700 text-gray-400 rounded-lg text-sm">Cancel</button>
              <button
                onClick={handleCreateMcq}
                disabled={creating || !mcqForm.question_text || mcqForm.options.some(o => !o)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
              >
                {creating && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                Create MCQ
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Problem Modal */}
      {showProblemModal && selectedTopic && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto scrollbar-hide">
            <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
              <div>
                <h2 className="text-white font-semibold">Create Coding Problem</h2>
                <p className="text-gray-500 text-xs">Topic: {selectedTopic.title}</p>
              </div>
              <button onClick={() => setShowProblemModal(false)} className="text-gray-400 hover:text-white">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Title *</label>
                <input
                  type="text"
                  value={problemForm.title}
                  onChange={(e) => setProblemForm({ ...problemForm, title: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                />
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-1 block">Description (Markdown) *</label>
                <textarea
                  value={problemForm.description}
                  onChange={(e) => setProblemForm({ ...problemForm, description: e.target.value })}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white h-32 resize-none font-mono text-sm"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Difficulty</label>
                  <select
                    value={problemForm.difficulty}
                    onChange={(e) => setProblemForm({ ...problemForm, difficulty: e.target.value })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Max Score</label>
                  <input
                    type="number"
                    value={problemForm.max_score}
                    onChange={(e) => setProblemForm({ ...problemForm, max_score: parseInt(e.target.value) })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  />
                </div>
                <div>
                  <label className="text-gray-400 text-sm mb-1 block">Language</label>
                  <select
                    value={problemForm.supported_languages[0]}
                    onChange={(e) => setProblemForm({ ...problemForm, supported_languages: [e.target.value] })}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  >
                    <option value="python">Python</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                    <option value="java">Java</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-gray-400 text-sm mb-2 block">Test Cases *</label>
                <div className="space-y-3">
                  {problemForm.test_cases.map((tc, i) => (
                    <div key={i} className="grid grid-cols-2 gap-3 p-3 bg-gray-800/50 rounded-lg">
                      <div>
                        <label className="text-gray-500 text-xs mb-1 block">Input</label>
                        <textarea
                          value={tc.input}
                          onChange={(e) => {
                            const newTc = [...problemForm.test_cases]
                            newTc[i] = { ...newTc[i], input: e.target.value }
                            setProblemForm({ ...problemForm, test_cases: newTc })
                          }}
                          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm h-20 resize-none font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-gray-500 text-xs mb-1 block">Expected Output</label>
                        <textarea
                          value={tc.expected_output}
                          onChange={(e) => {
                            const newTc = [...problemForm.test_cases]
                            newTc[i] = { ...newTc[i], expected_output: e.target.value }
                            setProblemForm({ ...problemForm, test_cases: newTc })
                          }}
                          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm h-20 resize-none font-mono"
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => setProblemForm({ ...problemForm, test_cases: [...problemForm.test_cases, { input: '', expected_output: '', is_sample: false }] })}
                  className="mt-2 text-indigo-400 hover:text-indigo-300 text-sm flex items-center gap-1"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Add Test Case
                </button>
              </div>
            </div>
            <div className="sticky bottom-0 bg-gray-900 border-t border-gray-800 px-6 py-4 flex justify-end gap-3">
              <button onClick={() => setShowProblemModal(false)} className="px-4 py-2 border border-gray-700 text-gray-400 rounded-lg text-sm">Cancel</button>
              <button
                onClick={handleCreateProblem}
                disabled={creating || !problemForm.title || !problemForm.description || problemForm.test_cases.every(tc => !tc.input)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm flex items-center gap-2"
              >
                {creating && <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>}
                Create Problem
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
