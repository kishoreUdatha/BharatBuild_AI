'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  ClipboardCheck,
  ArrowLeft,
  Upload,
  Loader2,
  Award,
  Target,
  CheckCircle,
  XCircle,
  AlertTriangle,
  BarChart3,
  FileCode,
  Book,
  Shield,
  Lightbulb,
  Star,
  TrendingUp
} from 'lucide-react'

interface EvaluationResult {
  project_id: string
  total_score: number
  max_score: number
  percentage: number
  grade: string
  criteria_scores: Record<string, {
    score: number
    max_score: number
    feedback: string
    bloom_level: string
  }>
  co_attainment: Record<string, {
    level: number
    percentage: number
  }>
  po_contribution: Record<string, number>
  strengths: string[]
  improvements: string[]
  overall_feedback: string
  evaluated_at: string
}

interface RubricCriterion {
  name: string
  description: string
  max_score: number
  weight: number
  indicators: string[]
  bloom_level: string
  co_mapping: string[]
}

const gradeColors: Record<string, string> = {
  'A+': 'from-green-600 to-emerald-600',
  'A': 'from-green-500 to-teal-500',
  'B+': 'from-blue-600 to-cyan-600',
  'B': 'from-blue-500 to-sky-500',
  'C+': 'from-yellow-600 to-amber-600',
  'C': 'from-yellow-500 to-orange-500',
  'F': 'from-red-600 to-rose-600'
}

export default function EvaluationPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [loadingRubric, setLoadingRubric] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [projectId, setProjectId] = useState('')
  const [files, setFiles] = useState<Record<string, string>>({})
  const [fileList, setFileList] = useState<string[]>([])

  // Rubric state
  const [rubric, setRubric] = useState<{ name: string; criteria: RubricCriterion[] } | null>(null)

  // Result state
  const [result, setResult] = useState<EvaluationResult | null>(null)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchRubric()
  }, [])

  const fetchRubric = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/v1/accreditation/evaluation/rubrics`)
      const data = await response.json()
      setRubric(data)
    } catch (err) {
      console.error('Failed to fetch rubric:', err)
    } finally {
      setLoadingRubric(false)
    }
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const uploadedFiles = event.target.files
    if (!uploadedFiles) return

    const newFiles: Record<string, string> = { ...files }
    const newFileList: string[] = [...fileList]

    Array.from(uploadedFiles).forEach(file => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const content = e.target?.result as string
        newFiles[file.name] = content
        if (!newFileList.includes(file.name)) {
          newFileList.push(file.name)
        }
        setFiles({ ...newFiles })
        setFileList([...newFileList])
      }
      reader.readAsText(file)
    })
  }

  const removeFile = (filename: string) => {
    const newFiles = { ...files }
    delete newFiles[filename]
    setFiles(newFiles)
    setFileList(fileList.filter(f => f !== filename))
  }

  const handleEvaluate = async () => {
    if (!projectId) {
      setError('Please enter a project ID')
      return
    }

    if (Object.keys(files).length === 0) {
      setError('Please upload at least one file to evaluate')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/v1/accreditation/evaluation/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          files: files
        })
      })

      const data = await response.json()

      if (data.success) {
        setResult(data)
      } else {
        setError(data.detail || 'Evaluation failed')
      }
    } catch (err) {
      setError('Network error. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const renderCriteriaChart = () => {
    if (!result) return null

    return (
      <div className="space-y-3">
        {Object.entries(result.criteria_scores).map(([name, data]) => {
          const percentage = (data.score / data.max_score) * 100

          return (
            <div key={name}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-300">{name}</span>
                <span className="text-slate-400">{data.score}/{data.max_score}</span>
              </div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${
                    percentage >= 80 ? 'bg-green-500' :
                    percentage >= 60 ? 'bg-blue-500' :
                    percentage >= 40 ? 'bg-yellow-500' : 'bg-red-500'
                  }`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    )
  }

  const renderPOChart = () => {
    if (!result) return null

    return (
      <div className="grid grid-cols-6 gap-2">
        {Object.entries(result.po_contribution).map(([po, value]) => (
          <div key={po} className="text-center">
            <div className="relative w-12 h-12 mx-auto mb-1">
              <svg className="w-12 h-12 transform -rotate-90">
                <circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="transparent"
                  className="text-slate-700"
                />
                <circle
                  cx="24"
                  cy="24"
                  r="20"
                  stroke="currentColor"
                  strokeWidth="4"
                  fill="transparent"
                  strokeDasharray={`${value * 1.256} 125.6`}
                  className={value >= 70 ? 'text-green-500' : value >= 50 ? 'text-blue-500' : 'text-yellow-500'}
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-white">
                {value.toFixed(0)}%
              </span>
            </div>
            <span className="text-xs text-slate-400">{po}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-900/50 to-teal-900/50 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-r from-emerald-600 to-teal-600 rounded-xl flex items-center justify-center">
              <ClipboardCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Automated Project Evaluation</h1>
              <p className="text-slate-400">Evaluate projects using AI-powered rubric-based assessment with CO-PO attainment</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5" />
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Upload Section */}
          <div className="lg:col-span-1">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 sticky top-6">
              <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Upload className="w-5 h-5 text-emerald-400" />
                Upload Project Files
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Project ID</label>
                  <input
                    type="text"
                    value={projectId}
                    onChange={(e) => setProjectId(e.target.value)}
                    placeholder="e.g., PROJ-2024-001"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-2">Upload Code Files</label>
                  <label className="block">
                    <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center hover:border-emerald-500 transition-colors cursor-pointer">
                      <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                      <p className="text-sm text-slate-400">Click to upload or drag files here</p>
                      <p className="text-xs text-slate-500 mt-1">.js, .py, .ts, .html, .css, etc.</p>
                    </div>
                    <input
                      type="file"
                      multiple
                      accept=".js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.html,.css,.json,.md"
                      onChange={handleFileUpload}
                      className="hidden"
                    />
                  </label>
                </div>

                {fileList.length > 0 && (
                  <div>
                    <label className="block text-sm text-slate-400 mb-2">Uploaded Files ({fileList.length})</label>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {fileList.map(filename => (
                        <div key={filename} className="flex items-center justify-between bg-slate-800 px-3 py-2 rounded-lg">
                          <div className="flex items-center gap-2">
                            <FileCode className="w-4 h-4 text-emerald-400" />
                            <span className="text-sm text-slate-300 truncate max-w-[150px]">{filename}</span>
                          </div>
                          <button
                            onClick={() => removeFile(filename)}
                            className="text-slate-500 hover:text-red-400"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <button
                  onClick={handleEvaluate}
                  disabled={loading || Object.keys(files).length === 0}
                  className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 text-white rounded-lg font-medium hover:from-emerald-500 hover:to-teal-500 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Evaluating...
                    </>
                  ) : (
                    <>
                      <ClipboardCheck className="w-5 h-5" />
                      Evaluate Project
                    </>
                  )}
                </button>
              </div>

              {/* Rubric Preview */}
              {rubric && (
                <div className="mt-8 pt-6 border-t border-slate-700">
                  <h3 className="text-sm font-medium text-slate-400 mb-3 flex items-center gap-2">
                    <Book className="w-4 h-4" />
                    Evaluation Rubric
                  </h3>
                  <div className="space-y-2">
                    {rubric.criteria.map((criterion, i) => (
                      <div key={i} className="flex justify-between text-sm">
                        <span className="text-slate-400">{criterion.name}</span>
                        <span className="text-slate-500">{criterion.max_score} pts</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Results Section */}
          <div className="lg:col-span-2">
            {!result ? (
              <div className="text-center py-20">
                <ClipboardCheck className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-slate-400 mb-2">No Evaluation Yet</h3>
                <p className="text-slate-500">
                  Upload your project files and click evaluate to get detailed assessment
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Grade Card */}
                <div className={`bg-gradient-to-r ${gradeColors[result.grade] || 'from-slate-600 to-slate-700'} rounded-2xl p-8`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-white/80 mb-1">Overall Grade</p>
                      <div className="text-6xl font-bold text-white">{result.grade}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-4xl font-bold text-white">{result.percentage.toFixed(1)}%</div>
                      <p className="text-white/80">{result.total_score} / {result.max_score} points</p>
                    </div>
                  </div>
                </div>

                {/* Criteria Scores */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-blue-400" />
                    Criteria-wise Scores
                  </h3>
                  {renderCriteriaChart()}
                </div>

                {/* CO Attainment */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Target className="w-5 h-5 text-purple-400" />
                    Course Outcome Attainment
                  </h3>
                  <div className="grid grid-cols-3 gap-4">
                    {Object.entries(result.co_attainment).map(([co, data]) => (
                      <div key={co} className="bg-slate-800 rounded-lg p-4 text-center">
                        <div className="text-lg font-bold text-white">{co}</div>
                        <div className="text-2xl font-bold text-purple-400">{data.level.toFixed(2)}</div>
                        <div className="text-sm text-slate-400">{data.percentage.toFixed(1)}% attained</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* PO Contribution */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-cyan-400" />
                    Program Outcome Contribution
                  </h3>
                  {renderPOChart()}
                </div>

                {/* Strengths & Improvements */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <Star className="w-5 h-5 text-yellow-400" />
                      Strengths
                    </h3>
                    <div className="space-y-2">
                      {result.strengths.map((strength, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <CheckCircle className="w-4 h-4 text-green-400 mt-0.5 flex-shrink-0" />
                          <span className="text-slate-300 text-sm">{strength}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <Lightbulb className="w-5 h-5 text-orange-400" />
                      Areas for Improvement
                    </h3>
                    <div className="space-y-2">
                      {result.improvements.map((improvement, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <AlertTriangle className="w-4 h-4 text-orange-400 mt-0.5 flex-shrink-0" />
                          <span className="text-slate-300 text-sm">{improvement}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Overall Feedback */}
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Award className="w-5 h-5 text-emerald-400" />
                    Overall Feedback
                  </h3>
                  <p className="text-slate-300">{result.overall_feedback}</p>
                </div>

                {/* Actions */}
                <div className="flex gap-4">
                  <button
                    onClick={() => router.push(`/certificates?projectId=${result.project_id}`)}
                    className="flex-1 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:from-purple-500 hover:to-pink-500 transition-all flex items-center justify-center gap-2"
                  >
                    <Award className="w-5 h-5" />
                    Generate Certificate
                  </button>
                  <button
                    onClick={() => setResult(null)}
                    className="px-6 py-3 bg-slate-700 text-white rounded-lg font-medium hover:bg-slate-600 transition-all"
                  >
                    New Evaluation
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
