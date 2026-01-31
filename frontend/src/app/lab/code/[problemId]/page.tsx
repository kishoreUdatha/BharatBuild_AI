'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Code, Play, CheckCircle2, XCircle, Clock, ArrowLeft, Sparkles,
  FileCode, TestTube, Send, Lightbulb, ChevronRight, Timer,
  Terminal, AlertCircle, RefreshCw, Copy, Check
} from 'lucide-react'
import Editor from '@monaco-editor/react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface CodingProblem {
  id: string
  topic_id: string
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  max_score: number
  supported_languages: string[]
  starter_code?: Record<string, string>
  hints?: string[]
  time_limit_ms: number
  memory_limit_mb: number
  test_cases?: Array<{ input: string; expected: string; is_sample: boolean }>
}

interface TestResult {
  test: number
  passed: boolean
  time_ms: number
  memory_mb?: number
  status?: string
  input?: string
  expected_output?: string
  actual_output?: string | null
  error?: string | null
  simulated?: boolean
}

interface Submission {
  id: string
  status: 'pending' | 'running' | 'passed' | 'failed' | 'error' | 'timeout'
  tests_passed: number
  tests_total: number
  score: number
  execution_time_ms?: number
  memory_used_mb?: number
  error_message?: string
  test_results?: TestResult[]
}

const languageMap: Record<string, string> = {
  python: 'python',
  javascript: 'javascript',
  typescript: 'typescript',
  java: 'java',
  c: 'c',
  cpp: 'cpp',
  go: 'go',
  rust: 'rust',
  ruby: 'ruby',
  php: 'php',
  sql: 'sql'
}

const languageLabels: Record<string, string> = {
  python: 'Python 3',
  javascript: 'JavaScript (Node.js)',
  typescript: 'TypeScript',
  java: 'Java',
  c: 'C',
  cpp: 'C++',
  go: 'Go',
  rust: 'Rust',
  ruby: 'Ruby',
  php: 'PHP',
  sql: 'SQL'
}

export default function CodeEditorPage() {
  const router = useRouter()
  const params = useParams()
  const problemId = params.problemId as string

  const [problem, setProblem] = useState<CodingProblem | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedLanguage, setSelectedLanguage] = useState('')
  const [code, setCode] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submission, setSubmission] = useState<Submission | null>(null)
  const [activeTab, setActiveTab] = useState('description')
  const [showHints, setShowHints] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (problemId) {
      fetchProblem()
    }
  }, [problemId])

  const fetchProblem = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch(`${API_URL}/lab/problems/${problemId}`, { headers })
      if (response.ok) {
        const data = await response.json()
        setProblem(data)

        // Set default language
        if (data.supported_languages && data.supported_languages.length > 0) {
          const defaultLang = data.supported_languages.includes('python') ? 'python' : data.supported_languages[0]
          setSelectedLanguage(defaultLang)

          // Set starter code
          if (data.starter_code && data.starter_code[defaultLang]) {
            setCode(data.starter_code[defaultLang])
          }
        }
      }
    } catch (error) {
      console.error('Error fetching problem:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLanguageChange = (lang: string) => {
    setSelectedLanguage(lang)
    if (problem?.starter_code?.[lang]) {
      setCode(problem.starter_code[lang])
    } else {
      setCode('')
    }
    setSubmission(null)
  }

  const runCode = async () => {
    setIsRunning(true)
    setActiveTab('output')

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/lab/problems/${problemId}/run`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          language: selectedLanguage,
          code: code
        })
      })

      if (response.ok) {
        const result = await response.json()
        setSubmission({
          ...result,
          status: result.all_passed ? 'passed' : 'failed'
        })
      }
    } catch (error) {
      console.error('Error running code:', error)
      setSubmission({
        id: '',
        status: 'error',
        tests_passed: 0,
        tests_total: 0,
        score: 0,
        error_message: 'Failed to run code. Please try again.'
      })
    } finally {
      setIsRunning(false)
    }
  }

  const submitCode = async () => {
    setIsSubmitting(true)
    setActiveTab('output')

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/lab/problems/${problemId}/submit`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          language: selectedLanguage,
          code: code
        })
      })

      if (response.ok) {
        const result = await response.json()
        setSubmission(result)

        // Poll for results if pending
        if (result.status === 'pending' || result.status === 'running') {
          pollSubmissionStatus(result.id)
        }
      }
    } catch (error) {
      console.error('Error submitting code:', error)
      setSubmission({
        id: '',
        status: 'error',
        tests_passed: 0,
        tests_total: 0,
        score: 0,
        error_message: 'Failed to submit code. Please try again.'
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  const pollSubmissionStatus = async (submissionId: string) => {
    const token = localStorage.getItem('token')
    let attempts = 0
    const maxAttempts = 30

    const poll = async () => {
      if (attempts >= maxAttempts) return

      try {
        const response = await fetch(`${API_URL}/lab/submissions/${submissionId}`, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })

        if (response.ok) {
          const result = await response.json()
          setSubmission(result)

          if (result.status === 'pending' || result.status === 'running') {
            attempts++
            setTimeout(poll, 1000)
          }
        }
      } catch (error) {
        console.error('Error polling submission:', error)
      }
    }

    poll()
  }

  const copyCode = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const resetCode = () => {
    if (problem?.starter_code?.[selectedLanguage]) {
      setCode(problem.starter_code[selectedLanguage])
    } else {
      setCode('')
    }
    setSubmission(null)
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'text-green-400 bg-green-500/10 border-green-500/30'
      case 'medium': return 'text-amber-400 bg-amber-500/10 border-amber-500/30'
      case 'hard': return 'text-red-400 bg-red-500/10 border-red-500/30'
      default: return 'text-slate-400'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'passed': return 'text-green-400 bg-green-500/10'
      case 'failed': return 'text-red-400 bg-red-500/10'
      case 'error': return 'text-amber-400 bg-amber-500/10'
      case 'timeout': return 'text-orange-400 bg-orange-500/10'
      case 'running': return 'text-cyan-400 bg-cyan-500/10'
      default: return 'text-slate-400 bg-slate-500/10'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-cyan-500/30 rounded-full animate-spin border-t-cyan-500"></div>
            <Sparkles className="absolute inset-0 m-auto h-8 w-8 text-cyan-400 animate-pulse" />
          </div>
          <p className="mt-4 text-cyan-400 font-medium">Loading Problem...</p>
        </div>
      </div>
    )
  }

  if (!problem) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Problem Not Found</h2>
          <Link href="/lab">
            <Button variant="outline" className="border-cyan-500/50 text-cyan-400">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Labs
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  const sampleTestCases = problem.test_cases?.filter(tc => tc.is_sample) || []

  return (
    <div className="h-screen bg-slate-950 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-900/80 border-b border-slate-800">
        <div className="flex items-center gap-4">
          <Link href={`/lab/topic/${problem.topic_id}`} className="text-slate-400 hover:text-cyan-400 transition-colors">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-white">{problem.title}</h1>
            <div className="flex items-center gap-3 mt-1">
              <span className={`px-2 py-0.5 text-xs rounded border ${getDifficultyColor(problem.difficulty)}`}>
                {problem.difficulty}
              </span>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3" /> {problem.time_limit_ms}ms
              </span>
              <span className="text-xs text-slate-400">
                {problem.max_score} points
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Select value={selectedLanguage} onValueChange={handleLanguageChange}>
            <SelectTrigger className="w-48 bg-slate-800 border-slate-700 text-white">
              <SelectValue placeholder="Select Language" />
            </SelectTrigger>
            <SelectContent className="bg-slate-800 border-slate-700">
              {problem.supported_languages.map(lang => (
                <SelectItem key={lang} value={lang} className="text-white hover:bg-slate-700">
                  {languageLabels[lang] || lang}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={runCode}
            disabled={isRunning || !code}
            className="border-cyan-500/50 text-cyan-400 hover:bg-cyan-500/10"
          >
            {isRunning ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Run
          </Button>

          <Button
            onClick={submitCode}
            disabled={isSubmitting || !code}
            className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
          >
            {isSubmitting ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Send className="h-4 w-4 mr-2" />
            )}
            Submit
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Problem Description */}
        <div className="w-1/2 border-r border-slate-800 flex flex-col overflow-hidden">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
            <TabsList className="bg-slate-900/60 border-b border-slate-800 rounded-none justify-start px-4">
              <TabsTrigger value="description" className="data-[state=active]:bg-slate-800">
                <FileCode className="h-4 w-4 mr-2" />
                Description
              </TabsTrigger>
              <TabsTrigger value="output" className="data-[state=active]:bg-slate-800">
                <Terminal className="h-4 w-4 mr-2" />
                Output
                {submission && (
                  <span className={`ml-2 w-2 h-2 rounded-full ${
                    submission.status === 'passed' ? 'bg-green-400' :
                    submission.status === 'failed' ? 'bg-red-400' :
                    submission.status === 'running' ? 'bg-cyan-400 animate-pulse' :
                    'bg-slate-400'
                  }`} />
                )}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="description" className="flex-1 overflow-auto p-6 m-0">
              <div className="prose prose-invert prose-cyan max-w-none">
                <div className="whitespace-pre-wrap text-slate-300">{problem.description}</div>
              </div>

              {/* Sample Test Cases */}
              {sampleTestCases.length > 0 && (
                <div className="mt-6">
                  <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                    <TestTube className="h-5 w-5 text-cyan-400" />
                    Sample Test Cases
                  </h3>
                  <div className="space-y-4">
                    {sampleTestCases.map((tc, index) => (
                      <div key={index} className="bg-slate-800/50 rounded-xl p-4">
                        <div className="mb-3">
                          <p className="text-xs text-slate-400 mb-1">Input:</p>
                          <pre className="bg-slate-900 p-3 rounded-lg text-sm text-slate-300 overflow-x-auto">
                            {tc.input}
                          </pre>
                        </div>
                        <div>
                          <p className="text-xs text-slate-400 mb-1">Expected Output:</p>
                          <pre className="bg-slate-900 p-3 rounded-lg text-sm text-slate-300 overflow-x-auto">
                            {tc.expected}
                          </pre>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Hints */}
              {problem.hints && problem.hints.length > 0 && (
                <div className="mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setShowHints(!showHints)}
                    className="border-amber-500/50 text-amber-400 hover:bg-amber-500/10"
                  >
                    <Lightbulb className="h-4 w-4 mr-2" />
                    {showHints ? 'Hide Hints' : 'Show Hints'}
                  </Button>

                  {showHints && (
                    <div className="mt-4 space-y-2">
                      {problem.hints.map((hint, index) => (
                        <div key={index} className="flex items-start gap-2 p-3 bg-amber-500/10 rounded-lg border border-amber-500/30">
                          <Lightbulb className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                          <p className="text-sm text-amber-300">{hint}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </TabsContent>

            <TabsContent value="output" className="flex-1 overflow-auto p-6 m-0">
              {!submission ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <Terminal className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">Run or submit your code to see output</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Status */}
                  <div className={`p-4 rounded-xl ${getStatusColor(submission.status)}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {submission.status === 'passed' && <CheckCircle2 className="h-5 w-5" />}
                        {submission.status === 'failed' && <XCircle className="h-5 w-5" />}
                        {submission.status === 'running' && <RefreshCw className="h-5 w-5 animate-spin" />}
                        {submission.status === 'error' && <AlertCircle className="h-5 w-5" />}
                        <span className="font-semibold capitalize">{submission.status}</span>
                      </div>
                      <div className="text-sm">
                        {submission.tests_passed}/{submission.tests_total} tests passed
                      </div>
                    </div>
                  </div>

                  {/* Score */}
                  {submission.score > 0 && (
                    <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-xl">
                      <span className="text-slate-400">Score</span>
                      <span className="text-2xl font-bold text-green-400">{submission.score}/{problem.max_score}</span>
                    </div>
                  )}

                  {/* Execution metrics */}
                  {(submission.execution_time_ms || submission.memory_used_mb) && (
                    <div className="grid grid-cols-2 gap-4">
                      {submission.execution_time_ms && (
                        <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                          <Timer className="h-4 w-4 text-cyan-400 mx-auto mb-1" />
                          <p className="text-lg font-semibold text-white">{submission.execution_time_ms}ms</p>
                          <p className="text-xs text-slate-400">Runtime</p>
                        </div>
                      )}
                      {submission.memory_used_mb && (
                        <div className="p-3 bg-slate-800/50 rounded-xl text-center">
                          <Code className="h-4 w-4 text-purple-400 mx-auto mb-1" />
                          <p className="text-lg font-semibold text-white">{submission.memory_used_mb.toFixed(2)}MB</p>
                          <p className="text-xs text-slate-400">Memory</p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Error message */}
                  {submission.error_message && (
                    <Alert className="bg-red-500/10 border-red-500/30">
                      <AlertCircle className="h-4 w-4 text-red-400" />
                      <AlertDescription className="text-red-400">
                        <pre className="whitespace-pre-wrap text-sm">{submission.error_message}</pre>
                      </AlertDescription>
                    </Alert>
                  )}

                  {/* Test results */}
                  {submission.test_results && submission.test_results.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
                        Test Results
                        {submission.test_results.some(r => r.simulated) && (
                          <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded">
                            Simulated
                          </span>
                        )}
                      </h4>
                      <div className="space-y-3">
                        {submission.test_results.map((result, index) => (
                          <div
                            key={index}
                            className={`p-3 rounded-lg border ${
                              result.passed
                                ? 'bg-green-500/10 border-green-500/30'
                                : 'bg-red-500/10 border-red-500/30'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {result.passed ? (
                                  <CheckCircle2 className="h-4 w-4 text-green-400" />
                                ) : (
                                  <XCircle className="h-4 w-4 text-red-400" />
                                )}
                                <span className={result.passed ? 'text-green-400' : 'text-red-400'}>
                                  Test {result.test}
                                </span>
                                {result.status && result.status !== 'passed' && result.status !== 'wrong_answer' && (
                                  <span className="text-xs text-orange-400 bg-orange-500/10 px-1.5 py-0.5 rounded">
                                    {result.status.replace(/_/g, ' ')}
                                  </span>
                                )}
                              </div>
                              <div className="flex items-center gap-3 text-xs text-slate-400">
                                <span>{result.time_ms?.toFixed(0) || 0}ms</span>
                                {result.memory_mb && (
                                  <span>{result.memory_mb.toFixed(1)}MB</span>
                                )}
                              </div>
                            </div>

                            {/* Show details for failed tests */}
                            {!result.passed && (result.expected_output || result.actual_output || result.error) && (
                              <div className="mt-2 space-y-2 text-xs">
                                {result.input && (
                                  <div>
                                    <span className="text-slate-500">Input: </span>
                                    <pre className="inline text-slate-300 bg-slate-800 px-1.5 py-0.5 rounded">
                                      {result.input.length > 50 ? result.input.slice(0, 50) + '...' : result.input}
                                    </pre>
                                  </div>
                                )}
                                {result.expected_output && (
                                  <div>
                                    <span className="text-slate-500">Expected: </span>
                                    <pre className="inline text-green-400 bg-slate-800 px-1.5 py-0.5 rounded">
                                      {result.expected_output.length > 50 ? result.expected_output.slice(0, 50) + '...' : result.expected_output}
                                    </pre>
                                  </div>
                                )}
                                {result.actual_output !== undefined && result.actual_output !== null && (
                                  <div>
                                    <span className="text-slate-500">Got: </span>
                                    <pre className="inline text-red-400 bg-slate-800 px-1.5 py-0.5 rounded">
                                      {result.actual_output.length > 50 ? result.actual_output.slice(0, 50) + '...' : (result.actual_output || '(empty)')}
                                    </pre>
                                  </div>
                                )}
                                {result.error && (
                                  <div className="mt-1">
                                    <span className="text-orange-400">{result.error}</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>

        {/* Right Panel - Code Editor */}
        <div className="w-1/2 flex flex-col overflow-hidden">
          {/* Editor toolbar */}
          <div className="flex items-center justify-between px-4 py-2 bg-slate-900/60 border-b border-slate-800">
            <span className="text-sm text-slate-400">
              {languageLabels[selectedLanguage] || selectedLanguage}
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={copyCode}
                className="text-slate-400 hover:text-white"
              >
                {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={resetCode}
                className="text-slate-400 hover:text-white"
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Monaco Editor */}
          <div className="flex-1">
            <Editor
              height="100%"
              language={languageMap[selectedLanguage] || 'plaintext'}
              value={code}
              onChange={(value) => setCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 2,
                wordWrap: 'on',
                padding: { top: 16 }
              }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
