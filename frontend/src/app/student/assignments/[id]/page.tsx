'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Play,
  Send,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Code,
  FileText,
  Terminal,
  Loader2,
  ChevronDown,
  ChevronUp,
  Award,
  History,
  Eye,
  EyeOff
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface TestCase {
  input: string
  expected_output: string
  weight: number
}

interface TestResult {
  test_case: number
  passed: boolean
  input?: string
  expected?: string
  actual?: string
  error?: string
  is_hidden: boolean
  execution_time?: number
}

interface Submission {
  id: string
  status: string
  score: number
  tests_passed: number
  tests_total: number
  submitted_at: string
  is_late: boolean
}

interface Assignment {
  id: string
  title: string
  subject: string
  description: string
  due_date: string
  problem_type: string
  difficulty: string
  language: string
  max_score: number
  starter_code: string
  visible_test_cases: TestCase[]
  hidden_test_cases_count: number
  total_test_cases: number
  my_submissions: Submission[]
  best_score: number | null
  allow_late_submission: boolean
  late_penalty_percent: number
}

interface SubmissionResult {
  submission_id: string
  status: string
  score: number
  max_score: number
  tests_passed: number
  tests_total: number
  visible_test_results: TestResult[]
  hidden_tests: { passed: number; total: number }
  execution_time_ms: number
  memory_used_kb: number
  error_message?: string
  is_late: boolean
  late_penalty?: number
  message: string
}

export default function AssignmentDetailPage() {
  const params = useParams()
  const router = useRouter()
  const assignmentId = params.id as string

  const [assignment, setAssignment] = useState<Assignment | null>(null)
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<SubmissionResult | null>(null)
  const [runOutput, setRunOutput] = useState<string | null>(null)
  const [testInput, setTestInput] = useState('')
  const [showTestCases, setShowTestCases] = useState(true)
  const [showHistory, setShowHistory] = useState(false)
  const [activeTab, setActiveTab] = useState<'problem' | 'submissions'>('problem')

  const getAuthHeaders = () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  useEffect(() => {
    fetchAssignment()
  }, [assignmentId])

  const fetchAssignment = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/student/assignments/${assignmentId}`, {
        headers: getAuthHeaders()
      })

      if (res.ok) {
        const data = await res.json()
        setAssignment(data)
        setCode(data.starter_code || '')
        setLanguage(data.language || 'python')
        if (data.visible_test_cases?.length > 0) {
          setTestInput(data.visible_test_cases[0].input)
        }
      } else {
        // Mock data for demo
        const mockAssignment: Assignment = {
          id: assignmentId,
          title: assignmentId === 'demo-1' ? 'Binary Search Implementation' :
                 assignmentId === 'demo-2' ? 'Linked List Reversal' : 'SQL Query',
          subject: 'Data Structures',
          description: assignmentId === 'demo-1' ?
            `Implement binary search algorithm that finds the position of a target value in a sorted array.

**Requirements:**
- Return the index of the target if found
- Return -1 if target is not found
- The array is guaranteed to be sorted in ascending order

**Input Format:**
- First line: Space-separated integers (the sorted array)
- Second line: Target integer to find

**Output Format:**
- Single integer: index of target or -1

**Example:**
\`\`\`
Input:
1 2 3 4 5
3

Output:
2
\`\`\`

**Constraints:**
- 1 <= array length <= 10^5
- -10^9 <= array elements <= 10^9` : 'Write a solution for this problem',
          due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
          problem_type: 'coding',
          difficulty: assignmentId === 'demo-1' ? 'easy' : 'medium',
          language: 'python',
          max_score: 100,
          starter_code: `def binary_search(arr, target):
    """
    Find the index of target in sorted array arr.
    Return -1 if not found.
    """
    # Your code here
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1

# Read input
arr = list(map(int, input().split()))
target = int(input())
print(binary_search(arr, target))`,
          visible_test_cases: [
            { input: '1 2 3 4 5\n3', expected_output: '2', weight: 1 },
            { input: '1 2 3 4 5\n6', expected_output: '-1', weight: 1 }
          ],
          hidden_test_cases_count: 2,
          total_test_cases: 4,
          my_submissions: [],
          best_score: null,
          allow_late_submission: true,
          late_penalty_percent: 10
        }
        setAssignment(mockAssignment)
        setCode(mockAssignment.starter_code)
        setLanguage(mockAssignment.language)
        if (mockAssignment.visible_test_cases?.length > 0) {
          setTestInput(mockAssignment.visible_test_cases[0].input)
        }
      }
    } catch (e) {
      console.error('Error fetching assignment:', e)
    }
    setLoading(false)
  }

  const handleRun = async () => {
    setRunning(true)
    setRunOutput(null)
    try {
      const res = await fetch(`${API_URL}/student/assignments/${assignmentId}/run`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          code,
          language,
          test_input: testInput
        })
      })

      if (res.ok) {
        const data = await res.json()
        setRunOutput(data.output || data.error || 'No output')
      } else {
        // Simulate run for demo
        try {
          // Simple simulation - in production this would go to Judge0
          setRunOutput('2') // Mock output for binary search demo
        } catch {
          setRunOutput('Error running code')
        }
      }
    } catch (e) {
      setRunOutput('Error connecting to server')
    }
    setRunning(false)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setResult(null)
    try {
      const res = await fetch(`${API_URL}/student/assignments/${assignmentId}/submit`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          code,
          language
        })
      })

      if (res.ok) {
        const data = await res.json()
        setResult(data)
        // Refresh assignment to get updated submissions
        fetchAssignment()
      } else {
        // Mock submission result for demo
        const mockResult: SubmissionResult = {
          submission_id: 'mock-' + Date.now(),
          status: 'passed',
          score: 100,
          max_score: 100,
          tests_passed: 4,
          tests_total: 4,
          visible_test_results: [
            { test_case: 1, passed: true, input: '1 2 3 4 5\n3', expected: '2', actual: '2', is_hidden: false },
            { test_case: 2, passed: true, input: '1 2 3 4 5\n6', expected: '-1', actual: '-1', is_hidden: false }
          ],
          hidden_tests: { passed: 2, total: 2 },
          execution_time_ms: 45,
          memory_used_kb: 2048,
          is_late: false,
          message: 'All tests passed! Great job!'
        }
        setResult(mockResult)
      }
    } catch (e) {
      console.error('Error submitting:', e)
    }
    setSubmitting(false)
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-green-500/20 text-green-400'
      case 'medium': return 'bg-yellow-500/20 text-yellow-400'
      case 'hard': return 'bg-red-500/20 text-red-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading assignment...</p>
        </div>
      </div>
    )
  }

  if (!assignment) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-white font-medium mb-2">Assignment not found</h2>
          <Link href="/student/assignments" className="text-blue-400 hover:underline">
            Back to assignments
          </Link>
        </div>
      </div>
    )
  }

  const isOverdue = new Date() > new Date(assignment.due_date)

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/student/assignments"
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-400" />
            </Link>
            <div>
              <h1 className="text-xl font-bold text-white">{assignment.title}</h1>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-gray-400 text-sm">{assignment.subject}</span>
                <span className={`px-2 py-0.5 rounded text-xs ${getDifficultyColor(assignment.difficulty)}`}>
                  {assignment.difficulty}
                </span>
                <span className="text-gray-500 text-sm flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {isOverdue ? 'Overdue' : `Due: ${new Date(assignment.due_date).toLocaleDateString()}`}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {assignment.best_score !== null && (
              <div className="text-right mr-4">
                <p className="text-gray-400 text-xs">Best Score</p>
                <p className={`text-xl font-bold ${
                  assignment.best_score >= 80 ? 'text-green-400' :
                  assignment.best_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                }`}>
                  {assignment.best_score}%
                </p>
              </div>
            )}
            <button
              onClick={handleRun}
              disabled={running || !code.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white rounded-lg transition-colors"
            >
              {running ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Run
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting || !code.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition-colors"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Submit
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Problem Description */}
        <div className="w-1/2 border-r border-gray-700 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-gray-700">
            <button
              onClick={() => setActiveTab('problem')}
              className={`px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'problem'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Problem
            </button>
            <button
              onClick={() => setActiveTab('submissions')}
              className={`px-4 py-3 text-sm font-medium transition-colors ${
                activeTab === 'submissions'
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Submissions ({assignment.my_submissions.length})
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            {activeTab === 'problem' ? (
              <div>
                {/* Description */}
                <div className="prose prose-invert max-w-none">
                  <div className="text-gray-300 whitespace-pre-wrap">
                    {assignment.description}
                  </div>
                </div>

                {/* Test Cases */}
                <div className="mt-6">
                  <button
                    onClick={() => setShowTestCases(!showTestCases)}
                    className="flex items-center gap-2 text-white font-medium mb-3"
                  >
                    {showTestCases ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    Sample Test Cases ({assignment.visible_test_cases.length})
                  </button>

                  {showTestCases && (
                    <div className="space-y-3">
                      {assignment.visible_test_cases.map((tc, idx) => (
                        <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-gray-400 text-sm">Test Case {idx + 1}</span>
                            <button
                              onClick={() => setTestInput(tc.input)}
                              className="text-blue-400 text-xs hover:underline"
                            >
                              Use as input
                            </button>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-gray-500 text-xs mb-1">Input:</p>
                              <pre className="bg-gray-900 p-2 rounded text-sm text-gray-300 overflow-x-auto">
                                {tc.input}
                              </pre>
                            </div>
                            <div>
                              <p className="text-gray-500 text-xs mb-1">Expected Output:</p>
                              <pre className="bg-gray-900 p-2 rounded text-sm text-gray-300 overflow-x-auto">
                                {tc.expected_output}
                              </pre>
                            </div>
                          </div>
                        </div>
                      ))}
                      {assignment.hidden_test_cases_count > 0 && (
                        <p className="text-gray-500 text-sm flex items-center gap-2">
                          <EyeOff className="w-4 h-4" />
                          + {assignment.hidden_test_cases_count} hidden test case(s)
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* Submissions History */
              <div>
                {assignment.my_submissions.length === 0 ? (
                  <div className="text-center py-12">
                    <History className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-400">No submissions yet</p>
                    <p className="text-gray-500 text-sm">Submit your code to see results here</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {assignment.my_submissions.map((sub, idx) => (
                      <div
                        key={sub.id}
                        className="bg-gray-800 rounded-lg p-4 border border-gray-700"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {sub.status === 'passed' ? (
                              <CheckCircle className="w-5 h-5 text-green-400" />
                            ) : sub.status === 'partial' ? (
                              <AlertCircle className="w-5 h-5 text-yellow-400" />
                            ) : (
                              <XCircle className="w-5 h-5 text-red-400" />
                            )}
                            <div>
                              <p className="text-white font-medium">
                                Submission #{assignment.my_submissions.length - idx}
                              </p>
                              <p className="text-gray-500 text-xs">
                                {new Date(sub.submitted_at).toLocaleString()}
                                {sub.is_late && <span className="text-yellow-400 ml-2">(Late)</span>}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`text-xl font-bold ${
                              sub.score >= 80 ? 'text-green-400' :
                              sub.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                            }`}>
                              {sub.score}%
                            </p>
                            <p className="text-gray-500 text-xs">
                              {sub.tests_passed}/{sub.tests_total} tests
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Panel - Code Editor */}
        <div className="w-1/2 flex flex-col overflow-hidden">
          {/* Language Selector */}
          <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4 text-gray-400" />
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="bg-gray-700 text-white text-sm rounded px-2 py-1 border border-gray-600"
              >
                <option value="python">Python</option>
                <option value="c">C</option>
                <option value="cpp">C++</option>
                <option value="java">Java</option>
                <option value="javascript">JavaScript</option>
              </select>
            </div>
            <button
              onClick={() => setCode(assignment.starter_code || '')}
              className="text-gray-400 hover:text-white text-sm"
            >
              Reset Code
            </button>
          </div>

          {/* Code Editor */}
          <div className="flex-1 overflow-hidden">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-full bg-gray-900 text-gray-100 font-mono text-sm p-4 resize-none focus:outline-none"
              placeholder="Write your code here..."
              spellCheck={false}
            />
          </div>

          {/* Test Input & Output */}
          <div className="h-48 border-t border-gray-700 flex flex-col">
            <div className="flex border-b border-gray-700">
              <div className="flex-1 px-4 py-2 border-r border-gray-700">
                <p className="text-gray-400 text-xs mb-1">Test Input</p>
              </div>
              <div className="flex-1 px-4 py-2">
                <p className="text-gray-400 text-xs mb-1">Output</p>
              </div>
            </div>
            <div className="flex-1 flex">
              <textarea
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                className="flex-1 bg-gray-900 text-gray-100 font-mono text-sm p-3 resize-none focus:outline-none border-r border-gray-700"
                placeholder="Enter test input..."
              />
              <div className="flex-1 bg-gray-900 p-3 overflow-auto">
                {running ? (
                  <div className="flex items-center gap-2 text-gray-400">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running...
                  </div>
                ) : runOutput ? (
                  <pre className="text-gray-100 font-mono text-sm whitespace-pre-wrap">{runOutput}</pre>
                ) : (
                  <p className="text-gray-500 text-sm">Output will appear here</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Submission Result Modal */}
      {result && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="p-6 border-b border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {result.status === 'passed' ? (
                    <div className="p-2 bg-green-500/20 rounded-full">
                      <CheckCircle className="w-6 h-6 text-green-400" />
                    </div>
                  ) : result.status === 'partial' ? (
                    <div className="p-2 bg-yellow-500/20 rounded-full">
                      <AlertCircle className="w-6 h-6 text-yellow-400" />
                    </div>
                  ) : (
                    <div className="p-2 bg-red-500/20 rounded-full">
                      <XCircle className="w-6 h-6 text-red-400" />
                    </div>
                  )}
                  <div>
                    <h2 className="text-xl font-bold text-white">Submission Result</h2>
                    <p className="text-gray-400 text-sm">{result.message}</p>
                  </div>
                </div>
                <button
                  onClick={() => setResult(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>
            </div>

            <div className="p-6">
              {/* Score Summary */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <p className={`text-3xl font-bold ${
                    result.score >= 80 ? 'text-green-400' :
                    result.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {result.score}%
                  </p>
                  <p className="text-gray-400 text-xs mt-1">Score</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-white">
                    {result.tests_passed}/{result.tests_total}
                  </p>
                  <p className="text-gray-400 text-xs mt-1">Tests Passed</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-white">
                    {result.execution_time_ms?.toFixed(0) || '-'}ms
                  </p>
                  <p className="text-gray-400 text-xs mt-1">Runtime</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-white">
                    {result.memory_used_kb ? (result.memory_used_kb / 1024).toFixed(1) : '-'}MB
                  </p>
                  <p className="text-gray-400 text-xs mt-1">Memory</p>
                </div>
              </div>

              {result.is_late && result.late_penalty && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 mb-4">
                  <p className="text-yellow-400 text-sm">
                    Late submission penalty: -{result.late_penalty}%
                  </p>
                </div>
              )}

              {/* Test Results */}
              <div>
                <h3 className="text-white font-medium mb-3">Test Results</h3>
                <div className="space-y-2">
                  {result.visible_test_results.map((tr, idx) => (
                    <div
                      key={idx}
                      className={`rounded-lg p-3 border ${
                        tr.passed
                          ? 'bg-green-500/10 border-green-500/30'
                          : 'bg-red-500/10 border-red-500/30'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          {tr.passed ? (
                            <CheckCircle className="w-4 h-4 text-green-400" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-400" />
                          )}
                          <span className="text-white text-sm">Test Case {tr.test_case}</span>
                        </div>
                        <span className={`text-xs ${tr.passed ? 'text-green-400' : 'text-red-400'}`}>
                          {tr.passed ? 'Passed' : 'Failed'}
                        </span>
                      </div>
                      {!tr.passed && tr.expected && tr.actual && (
                        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <p className="text-gray-500">Expected:</p>
                            <pre className="text-gray-300 bg-gray-900 p-1 rounded mt-1">{tr.expected}</pre>
                          </div>
                          <div>
                            <p className="text-gray-500">Your Output:</p>
                            <pre className="text-gray-300 bg-gray-900 p-1 rounded mt-1">{tr.actual}</pre>
                          </div>
                        </div>
                      )}
                      {tr.error && (
                        <pre className="mt-2 text-red-400 text-xs bg-gray-900 p-2 rounded overflow-x-auto">
                          {tr.error}
                        </pre>
                      )}
                    </div>
                  ))}

                  {/* Hidden Tests Summary */}
                  {result.hidden_tests.total > 0 && (
                    <div className="bg-gray-700/50 rounded-lg p-3 border border-gray-600">
                      <div className="flex items-center gap-2">
                        <EyeOff className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-300 text-sm">
                          Hidden Tests: {result.hidden_tests.passed}/{result.hidden_tests.total} passed
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Error Message */}
              {result.error_message && (
                <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                  <p className="text-red-400 text-sm font-mono">{result.error_message}</p>
                </div>
              )}
            </div>

            <div className="p-6 border-t border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setResult(null)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg"
              >
                Close
              </button>
              {result.status !== 'passed' && (
                <button
                  onClick={() => {
                    setResult(null)
                    // Focus on code editor
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg"
                >
                  Try Again
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
