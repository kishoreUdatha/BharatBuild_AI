'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  BookOpen,
  Search,
  Loader2,
  ChevronRight,
  Code,
  Briefcase,
  Clock,
  Star,
  Target,
  CheckCircle,
  Filter,
  ArrowLeft,
  Sparkles,
  GraduationCap,
  Building2
} from 'lucide-react'

interface ProjectSuggestion {
  title: string
  description: string
  difficulty: string
  project_type: string
  domain: string
  technologies: string[]
  estimated_duration: string
  course_outcomes: string[]
  po_mapping: Record<string, number>
  deliverables: string[]
  evaluation_criteria: string[]
  relevance_score: number
}

interface IndustryUseCase {
  id: string
  title: string
  description: string
  difficulty: string
  technologies: string[]
  duration_weeks: number
  course_outcomes: string[]
  po_mapping: Record<string, number>
  deliverables: string[]
  industry_relevance: string
}

const difficultyColors: Record<string, string> = {
  beginner: 'bg-green-500/20 text-green-400 border-green-500/30',
  intermediate: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  advanced: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  expert: 'bg-purple-500/20 text-purple-400 border-purple-500/30'
}

const domainOptions = [
  { id: 'web_development', name: 'Web Development' },
  { id: 'mobile_development', name: 'Mobile Development' },
  { id: 'ai_ml', name: 'AI/ML' },
  { id: 'data_science', name: 'Data Science' },
  { id: 'cloud_computing', name: 'Cloud Computing' },
  { id: 'devops', name: 'DevOps' },
  { id: 'cybersecurity', name: 'Cybersecurity' },
  { id: 'iot', name: 'IoT' },
  { id: 'blockchain', name: 'Blockchain' },
  { id: 'game_development', name: 'Game Development' },
  { id: 'embedded_systems', name: 'Embedded Systems' },
  { id: 'enterprise', name: 'Enterprise Software' }
]

export default function CurriculumMappingPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<'mapping' | 'library'>('mapping')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Mapping form state
  const [courseName, setCourseName] = useState('')
  const [courseCode, setCourseCode] = useState('')
  const [department, setDepartment] = useState('')
  const [semester, setSemester] = useState(1)
  const [credits, setCredits] = useState(3)
  const [syllabusTopics, setSyllabusTopics] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')
  const [suggestions, setSuggestions] = useState<ProjectSuggestion[]>([])

  // Library state
  const [selectedDomain, setSelectedDomain] = useState('web_development')
  const [libraryDifficulty, setLibraryDifficulty] = useState('')
  const [useCases, setUseCases] = useState<IndustryUseCase[]>([])

  // Selected project for details
  const [selectedProject, setSelectedProject] = useState<ProjectSuggestion | IndustryUseCase | null>(null)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleMapCurriculum = async () => {
    if (!courseName || !courseCode || !department || !syllabusTopics) {
      setError('Please fill in all required fields')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const topics = syllabusTopics.split('\n').filter(t => t.trim())

      const response = await fetch(`${API_BASE}/api/v1/accreditation/curriculum/map`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          course_name: courseName,
          course_code: courseCode,
          department,
          semester,
          credits,
          syllabus_topics: topics,
          difficulty_filter: difficultyFilter || null,
          num_suggestions: 5
        })
      })

      const data = await response.json()

      if (data.success) {
        setSuggestions(data.suggestions)
      } else {
        setError(data.detail || 'Failed to get project suggestions')
      }
    } catch (err) {
      setError('Network error. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleGetUseCases = async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/v1/accreditation/industry/use-cases`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: selectedDomain,
          difficulty: libraryDifficulty || null,
          limit: 20
        })
      })

      const data = await response.json()

      if (data.success) {
        setUseCases(data.use_cases)
      } else {
        setError(data.detail || 'Failed to get industry use cases')
      }
    } catch (err) {
      setError('Network error. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'library') {
      handleGetUseCases()
    }
  }, [selectedDomain, libraryDifficulty, activeTab])

  const renderProjectCard = (project: ProjectSuggestion | IndustryUseCase, index: number, isUseCase: boolean = false) => {
    const difficulty = project.difficulty
    const difficultyClass = difficultyColors[difficulty] || difficultyColors.intermediate

    return (
      <div
        key={index}
        onClick={() => setSelectedProject(project)}
        className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 cursor-pointer hover:border-blue-500/50 transition-all duration-200 hover:shadow-lg hover:shadow-blue-500/10"
      >
        <div className="flex justify-between items-start mb-4">
          <h3 className="text-lg font-semibold text-white">{project.title}</h3>
          <span className={`px-3 py-1 rounded-full text-xs font-medium border ${difficultyClass}`}>
            {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
          </span>
        </div>

        <p className="text-slate-400 text-sm mb-4 line-clamp-2">{project.description}</p>

        <div className="flex flex-wrap gap-2 mb-4">
          {project.technologies.slice(0, 4).map((tech, i) => (
            <span key={i} className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
              {tech}
            </span>
          ))}
          {project.technologies.length > 4 && (
            <span className="px-2 py-1 bg-slate-700 text-slate-400 text-xs rounded">
              +{project.technologies.length - 4} more
            </span>
          )}
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4 text-slate-400">
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              {isUseCase
                ? `${(project as IndustryUseCase).duration_weeks} weeks`
                : (project as ProjectSuggestion).estimated_duration}
            </span>
            <span className="flex items-center gap-1">
              <Target className="w-4 h-4" />
              {project.course_outcomes.length} COs
            </span>
          </div>
          {!isUseCase && (project as ProjectSuggestion).relevance_score && (
            <div className="flex items-center gap-1 text-yellow-400">
              <Star className="w-4 h-4 fill-current" />
              <span>{((project as ProjectSuggestion).relevance_score * 100).toFixed(0)}%</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  const renderProjectDetails = () => {
    if (!selectedProject) return null

    const isUseCase = 'industry_relevance' in selectedProject
    const project = selectedProject

    return (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
        <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6 border-b border-slate-700">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">{project.title}</h2>
                <span className={`px-3 py-1 rounded-full text-xs font-medium border ${difficultyColors[project.difficulty]}`}>
                  {project.difficulty.charAt(0).toUpperCase() + project.difficulty.slice(1)}
                </span>
              </div>
              <button
                onClick={() => setSelectedProject(null)}
                className="text-slate-400 hover:text-white p-2"
              >
                &times;
              </button>
            </div>
          </div>

          <div className="p-6 space-y-6">
            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Description</h3>
              <p className="text-white">{project.description}</p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Technologies</h3>
              <div className="flex flex-wrap gap-2">
                {project.technologies.map((tech, i) => (
                  <span key={i} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-full text-sm">
                    {tech}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Course Outcomes</h3>
              <div className="space-y-2">
                {project.course_outcomes.map((co, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                    <span className="text-slate-300 text-sm">{co}</span>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Program Outcome Mapping</h3>
              <div className="grid grid-cols-6 gap-2">
                {Object.entries(project.po_mapping).map(([po, level]) => (
                  <div key={po} className="text-center p-2 bg-slate-800 rounded">
                    <div className="text-xs text-slate-400">{po}</div>
                    <div className={`text-lg font-bold ${level >= 3 ? 'text-green-400' : level >= 2 ? 'text-yellow-400' : 'text-slate-500'}`}>
                      {level}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h3 className="text-sm font-medium text-slate-400 mb-2">Deliverables</h3>
              <div className="space-y-2">
                {project.deliverables.map((d, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <ChevronRight className="w-4 h-4 text-blue-400 mt-0.5 flex-shrink-0" />
                    <span className="text-slate-300 text-sm">{d}</span>
                  </div>
                ))}
              </div>
            </div>

            {isUseCase && (
              <div>
                <h3 className="text-sm font-medium text-slate-400 mb-2">Industry Relevance</h3>
                <p className="text-slate-300">{(project as IndustryUseCase).industry_relevance}</p>
              </div>
            )}

            <div className="flex gap-4 pt-4">
              <button
                onClick={() => {
                  // Navigate to build page with project details
                  router.push(`/build?template=${encodeURIComponent(project.title)}`)
                }}
                className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-lg font-medium hover:from-blue-500 hover:to-cyan-500 transition-all"
              >
                Start This Project
              </button>
              <button
                onClick={() => setSelectedProject(null)}
                className="px-6 py-3 bg-slate-700 text-white rounded-lg font-medium hover:bg-slate-600 transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-900/50 to-purple-900/50 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl flex items-center justify-center">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Curriculum to Project Mapping</h1>
              <p className="text-slate-400">Map your course syllabus to industry-aligned projects with OBE support</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setActiveTab('mapping')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'mapping'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-5 h-5" />
            AI Mapping
          </button>
          <button
            onClick={() => setActiveTab('library')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'library'
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Building2 className="w-5 h-5" />
            Industry Library
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* AI Mapping Tab */}
        {activeTab === 'mapping' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Form */}
            <div className="lg:col-span-1">
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 sticky top-6">
                <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-blue-400" />
                  Course Details
                </h2>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Course Name *</label>
                    <input
                      type="text"
                      value={courseName}
                      onChange={(e) => setCourseName(e.target.value)}
                      placeholder="e.g., Web Development"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Course Code *</label>
                    <input
                      type="text"
                      value={courseCode}
                      onChange={(e) => setCourseCode(e.target.value)}
                      placeholder="e.g., CS401"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Department *</label>
                    <input
                      type="text"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      placeholder="e.g., Computer Science"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Semester</label>
                      <select
                        value={semester}
                        onChange={(e) => setSemester(parseInt(e.target.value))}
                        className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                      >
                        {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                          <option key={s} value={s}>Semester {s}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Credits</label>
                      <select
                        value={credits}
                        onChange={(e) => setCredits(parseInt(e.target.value))}
                        className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                      >
                        {[1, 2, 3, 4, 5, 6].map(c => (
                          <option key={c} value={c}>{c} Credits</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Syllabus Topics * (one per line)</label>
                    <textarea
                      value={syllabusTopics}
                      onChange={(e) => setSyllabusTopics(e.target.value)}
                      placeholder="HTML, CSS, JavaScript&#10;React Framework&#10;Node.js Backend&#10;Database Integration"
                      rows={6}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 resize-none"
                    />
                  </div>

                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Difficulty Filter</label>
                    <select
                      value={difficultyFilter}
                      onChange={(e) => setDifficultyFilter(e.target.value)}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="">All Levels</option>
                      <option value="beginner">Beginner</option>
                      <option value="intermediate">Intermediate</option>
                      <option value="advanced">Advanced</option>
                      <option value="expert">Expert</option>
                    </select>
                  </div>

                  <button
                    onClick={handleMapCurriculum}
                    disabled={loading}
                    className="w-full py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-lg font-medium hover:from-blue-500 hover:to-cyan-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-5 h-5" />
                        Get Project Suggestions
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>

            {/* Results */}
            <div className="lg:col-span-2">
              {suggestions.length === 0 ? (
                <div className="text-center py-20">
                  <BookOpen className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-slate-400 mb-2">No Projects Yet</h3>
                  <p className="text-slate-500">
                    Enter your course details and syllabus topics to get AI-powered project suggestions
                  </p>
                </div>
              ) : (
                <div>
                  <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Code className="w-5 h-5 text-green-400" />
                    Suggested Projects ({suggestions.length})
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {suggestions.map((project, index) => renderProjectCard(project, index))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Industry Library Tab */}
        {activeTab === 'library' && (
          <div>
            {/* Filters */}
            <div className="flex flex-wrap gap-4 mb-8">
              <div className="flex-1 min-w-[200px]">
                <label className="block text-sm text-slate-400 mb-1">Domain</label>
                <select
                  value={selectedDomain}
                  onChange={(e) => setSelectedDomain(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  {domainOptions.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div className="w-48">
                <label className="block text-sm text-slate-400 mb-1">Difficulty</label>
                <select
                  value={libraryDifficulty}
                  onChange={(e) => setLibraryDifficulty(e.target.value)}
                  className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Levels</option>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                  <option value="expert">Expert</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="text-center py-20">
                <Loader2 className="w-12 h-12 text-blue-400 mx-auto mb-4 animate-spin" />
                <p className="text-slate-400">Loading industry use cases...</p>
              </div>
            ) : useCases.length === 0 ? (
              <div className="text-center py-20">
                <Briefcase className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-400 mb-2">No Use Cases Found</h3>
                <p className="text-slate-500">Try selecting a different domain or difficulty level</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {useCases.map((uc, index) => renderProjectCard(uc, index, true))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Project Details Modal */}
      {renderProjectDetails()}
    </div>
  )
}
