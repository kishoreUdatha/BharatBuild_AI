'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  BookOpen, Code, Brain, ChevronRight, CheckCircle2, XCircle,
  Sparkles, Clock, ArrowLeft, Play, FileText, Zap, Star,
  Lightbulb, AlertCircle, ChevronLeft, Timer
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Topic {
  id: string
  lab_id: string
  title: string
  description?: string
  concept_content?: string
  video_url?: string
  mcq_count: number
  coding_count: number
}

interface MCQ {
  id: string
  question_text: string
  options: string[]
  difficulty: 'easy' | 'medium' | 'hard'
  marks: number
  time_limit_seconds: number
}

interface CodingProblem {
  id: string
  title: string
  description: string
  difficulty: 'easy' | 'medium' | 'hard'
  max_score: number
  supported_languages: string[]
}

interface TopicProgress {
  concept_read: boolean
  mcq_attempted: number
  mcq_correct: number
  mcq_score: number
  coding_attempted: number
  coding_solved: number
  coding_score: number
  progress_percentage: number
}

export default function TopicLearningPage() {
  const router = useRouter()
  const params = useParams()
  const topicId = params.topicId as string

  const [topic, setTopic] = useState<Topic | null>(null)
  const [mcqs, setMcqs] = useState<MCQ[]>([])
  const [problems, setProblems] = useState<CodingProblem[]>([])
  const [progress, setProgress] = useState<TopicProgress | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('concepts')

  // MCQ Quiz State
  const [currentMcqIndex, setCurrentMcqIndex] = useState(0)
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [mcqResults, setMcqResults] = useState<Record<string, { correct: boolean; correctOption: number }>>({})
  const [showExplanation, setShowExplanation] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (topicId) {
      fetchTopicData()
    }
  }, [topicId])

  const fetchTopicData = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      }
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      // Fetch topic, MCQs, problems in parallel (using public endpoints)
      const [topicRes, mcqsRes, problemsRes] = await Promise.all([
        fetch(`${API_URL}/lab/public/topics/${topicId}`),
        fetch(`${API_URL}/lab/public/topics/${topicId}/mcqs`),
        fetch(`${API_URL}/lab/public/topics/${topicId}/problems`)
      ])

      if (topicRes.ok) {
        const data = await topicRes.json()
        setTopic(data.topic || data)
        if (data.progress) {
          setProgress(data.progress)
        }
      }

      if (mcqsRes.ok) {
        const data = await mcqsRes.json()
        setMcqs(data)
      }

      if (problemsRes.ok) {
        const data = await problemsRes.json()
        setProblems(data)
      }

    } catch (error) {
      console.error('Error fetching topic data:', error)
    } finally {
      setLoading(false)
    }
  }

  const markConceptRead = async () => {
    try {
      const token = localStorage.getItem('token')
      await fetch(`${API_URL}/lab/topics/${topicId}/mark-read`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })
      // Refresh progress
      fetchTopicData()
    } catch (error) {
      console.error('Error marking concept as read:', error)
    }
  }

  const submitMcqAnswer = async () => {
    if (selectedOption === null) return

    const currentMcq = mcqs[currentMcqIndex]
    setIsSubmitting(true)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/lab/mcqs/${currentMcq.id}/answer`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          selected_option: selectedOption,
          time_taken_seconds: 30 // TODO: Track actual time
        })
      })

      if (response.ok) {
        const result = await response.json()
        setMcqResults(prev => ({
          ...prev,
          [currentMcq.id]: {
            correct: result.is_correct,
            correctOption: result.correct_option
          }
        }))
        setShowExplanation(true)
      }
    } catch (error) {
      console.error('Error submitting answer:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const nextMcq = () => {
    if (currentMcqIndex < mcqs.length - 1) {
      setCurrentMcqIndex(prev => prev + 1)
      setSelectedOption(null)
      setShowExplanation(false)
    }
  }

  const prevMcq = () => {
    if (currentMcqIndex > 0) {
      setCurrentMcqIndex(prev => prev - 1)
      setSelectedOption(null)
      setShowExplanation(false)
    }
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'text-green-400 bg-green-500/10 border-green-500/30'
      case 'medium': return 'text-amber-400 bg-amber-500/10 border-amber-500/30'
      case 'hard': return 'text-red-400 bg-red-500/10 border-red-500/30'
      default: return 'text-slate-400 bg-slate-500/10 border-slate-500/30'
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
          <p className="mt-4 text-cyan-400 font-medium">Loading Topic...</p>
        </div>
      </div>
    )
  }

  if (!topic) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-white mb-2">Topic Not Found</h2>
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

  const currentMcq = mcqs[currentMcqIndex]
  const currentResult = currentMcq ? mcqResults[currentMcq.id] : null

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl"></div>
      </div>
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none"></div>

      <div className="relative z-10 py-8 px-4">
        <div className="max-w-5xl mx-auto">
          {/* Back Button & Header */}
          <div className="flex items-center justify-between mb-6">
            <Link href={`/lab/${topic.lab_id}`} className="inline-flex items-center text-slate-400 hover:text-cyan-400 transition-colors">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Topics
            </Link>

            {progress && (
              <div className="flex items-center gap-2">
                <span className="text-slate-400 text-sm">Progress:</span>
                <div className="w-32">
                  <Progress value={progress.progress_percentage} className="h-2 bg-slate-800" />
                </div>
                <span className="text-cyan-400 font-semibold text-sm">{Math.round(progress.progress_percentage)}%</span>
              </div>
            )}
          </div>

          <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">{topic.title}</h1>
          {topic.description && (
            <p className="text-slate-400 mb-6">{topic.description}</p>
          )}

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="w-full bg-slate-900/60 border border-slate-800 p-1 mb-6">
              <TabsTrigger
                value="concepts"
                className="flex-1 data-[state=active]:bg-cyan-500 data-[state=active]:text-white"
              >
                <FileText className="h-4 w-4 mr-2" />
                Concepts
                {progress?.concept_read && <CheckCircle2 className="h-4 w-4 ml-2 text-green-400" />}
              </TabsTrigger>
              <TabsTrigger
                value="mcqs"
                className="flex-1 data-[state=active]:bg-purple-500 data-[state=active]:text-white"
              >
                <Brain className="h-4 w-4 mr-2" />
                MCQs ({mcqs.length})
                {progress && progress.mcq_score > 0 && (
                  <span className="ml-2 text-xs bg-purple-500/20 px-2 py-0.5 rounded">{Math.round(progress.mcq_score)}%</span>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="coding"
                className="flex-1 data-[state=active]:bg-green-500 data-[state=active]:text-white"
              >
                <Code className="h-4 w-4 mr-2" />
                Coding ({problems.length})
                {progress && progress.coding_solved > 0 && (
                  <span className="ml-2 text-xs bg-green-500/20 px-2 py-0.5 rounded">{progress.coding_solved} solved</span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* Concepts Tab */}
            <TabsContent value="concepts">
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-6">
                  {/* Video Tutorial Section */}
                  {topic.video_url ? (
                    <div className="mb-8">
                      <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                        <Play className="h-5 w-5 text-cyan-400" />
                        Video Tutorial
                      </h3>
                      <div className="aspect-video bg-slate-800 rounded-xl overflow-hidden border border-slate-700">
                        <iframe
                          src={topic.video_url}
                          className="w-full h-full"
                          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                          allowFullScreen
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="mb-8 p-4 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/30 rounded-xl">
                      <div className="flex items-center gap-4">
                        <div className="w-16 h-12 bg-slate-700 rounded-lg flex items-center justify-center">
                          <Play className="h-6 w-6 text-slate-400" />
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-white">Video Tutorial</p>
                          <p className="text-sm text-slate-400">Video content coming soon</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Concept Content */}
                  {topic.concept_content ? (
                    <div className="prose prose-invert prose-cyan max-w-none
                      prose-headings:text-white prose-headings:font-bold
                      prose-h1:text-2xl prose-h1:border-b prose-h1:border-slate-700 prose-h1:pb-4 prose-h1:mb-6
                      prose-h2:text-xl prose-h2:text-cyan-400 prose-h2:mt-8 prose-h2:mb-4
                      prose-h3:text-lg prose-h3:text-purple-400
                      prose-p:text-slate-300 prose-p:leading-relaxed
                      prose-strong:text-white prose-strong:font-semibold
                      prose-ul:text-slate-300 prose-ol:text-slate-300
                      prose-li:marker:text-cyan-400
                      prose-code:text-cyan-300 prose-code:bg-slate-800 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-mono
                      prose-pre:bg-slate-900 prose-pre:border prose-pre:border-slate-700 prose-pre:rounded-xl
                      prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline
                      prose-blockquote:border-cyan-500 prose-blockquote:bg-cyan-500/5 prose-blockquote:rounded-r-lg
                      prose-table:border-slate-700
                      prose-th:bg-slate-800 prose-th:text-white prose-th:px-4 prose-th:py-2
                      prose-td:border-slate-700 prose-td:px-4 prose-td:py-2
                    ">
                      <ReactMarkdown>{topic.concept_content}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="text-center py-12">
                      <Lightbulb className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                      <p className="text-slate-400">Concept content will be added soon.</p>
                    </div>
                  )}

                  {/* Mark as Read Button */}
                  {topic.concept_content && (
                    <div className="mt-8 pt-6 border-t border-slate-800 flex flex-col sm:flex-row gap-3">
                      {!progress?.concept_read ? (
                        <Button
                          onClick={markConceptRead}
                          className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600"
                        >
                          <CheckCircle2 className="h-4 w-4 mr-2" />
                          Mark as Read
                        </Button>
                      ) : (
                        <div className="flex-1 flex items-center justify-center gap-2 py-2 text-green-400">
                          <CheckCircle2 className="h-5 w-5" />
                          <span className="font-medium">Concept Read</span>
                        </div>
                      )}
                      <Button
                        onClick={() => setActiveTab('mcqs')}
                        className="flex-1 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
                      >
                        Continue to MCQs
                        <ChevronRight className="h-4 w-4 ml-2" />
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            {/* MCQs Tab */}
            <TabsContent value="mcqs">
              {mcqs.length === 0 ? (
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-12 text-center">
                    <Brain className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">No MCQs available for this topic yet.</p>
                  </CardContent>
                </Card>
              ) : (
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-6">
                    {/* Progress */}
                    <div className="flex items-center justify-between mb-6">
                      <div className="flex items-center gap-2">
                        <span className="text-slate-400 text-sm">Question {currentMcqIndex + 1} of {mcqs.length}</span>
                        <span className={`px-2 py-0.5 text-xs rounded border ${getDifficultyColor(currentMcq.difficulty)}`}>
                          {currentMcq.difficulty}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-slate-400">
                        <Timer className="h-4 w-4" />
                        <span className="text-sm">{currentMcq.time_limit_seconds}s</span>
                        <Star className="h-4 w-4 ml-2 text-amber-400" />
                        <span className="text-sm">{currentMcq.marks} marks</span>
                      </div>
                    </div>

                    <Progress value={((currentMcqIndex + 1) / mcqs.length) * 100} className="h-2 bg-slate-800 mb-6" />

                    {/* Question */}
                    <div className="mb-6">
                      <h3 className="text-lg font-semibold text-white mb-4">
                        {currentMcq.question_text}
                      </h3>

                      <div className="space-y-3">
                        {currentMcq.options.map((option, index) => {
                          const isSelected = selectedOption === index
                          const isCorrect = currentResult?.correctOption === index
                          const isWrong = currentResult && isSelected && !currentResult.correct

                          let optionClass = 'border-slate-700 hover:border-cyan-500/50 cursor-pointer'
                          if (currentResult) {
                            if (isCorrect) optionClass = 'border-green-500 bg-green-500/10'
                            else if (isWrong) optionClass = 'border-red-500 bg-red-500/10'
                          } else if (isSelected) {
                            optionClass = 'border-cyan-500 bg-cyan-500/10'
                          }

                          return (
                            <div
                              key={index}
                              className={`p-4 rounded-xl border transition-all ${optionClass} ${currentResult ? 'cursor-default' : ''}`}
                              onClick={() => !currentResult && setSelectedOption(index)}
                            >
                              <div className="flex items-center gap-3">
                                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-semibold ${
                                  currentResult && isCorrect ? 'bg-green-500 text-white' :
                                  currentResult && isWrong ? 'bg-red-500 text-white' :
                                  isSelected ? 'bg-cyan-500 text-white' :
                                  'bg-slate-800 text-slate-400'
                                }`}>
                                  {String.fromCharCode(65 + index)}
                                </div>
                                <span className="text-white">{option}</span>
                                {currentResult && isCorrect && <CheckCircle2 className="h-5 w-5 text-green-400 ml-auto" />}
                                {currentResult && isWrong && <XCircle className="h-5 w-5 text-red-400 ml-auto" />}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>

                    {/* Result Message */}
                    {currentResult && (
                      <Alert className={currentResult.correct ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}>
                        <AlertDescription className={currentResult.correct ? 'text-green-400' : 'text-red-400'}>
                          {currentResult.correct ? (
                            <span className="flex items-center gap-2">
                              <CheckCircle2 className="h-5 w-5" />
                              Correct! Well done!
                            </span>
                          ) : (
                            <span className="flex items-center gap-2">
                              <XCircle className="h-5 w-5" />
                              Incorrect. The correct answer is {String.fromCharCode(65 + currentResult.correctOption)}.
                            </span>
                          )}
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Navigation */}
                    <div className="flex items-center justify-between mt-6 pt-6 border-t border-slate-800">
                      <Button
                        variant="outline"
                        onClick={prevMcq}
                        disabled={currentMcqIndex === 0}
                        className="border-slate-700 text-slate-400"
                      >
                        <ChevronLeft className="h-4 w-4 mr-2" />
                        Previous
                      </Button>

                      {!currentResult ? (
                        <Button
                          onClick={submitMcqAnswer}
                          disabled={selectedOption === null || isSubmitting}
                          className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
                        >
                          {isSubmitting ? (
                            <>
                              <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                              </svg>
                              Checking...
                            </>
                          ) : (
                            <>
                              <Zap className="h-4 w-4 mr-2" />
                              Submit Answer
                            </>
                          )}
                        </Button>
                      ) : (
                        <Button
                          onClick={nextMcq}
                          disabled={currentMcqIndex === mcqs.length - 1}
                          className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600"
                        >
                          Next Question
                          <ChevronRight className="h-4 w-4 ml-2" />
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Coding Tab */}
            <TabsContent value="coding">
              {problems.length === 0 ? (
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-12 text-center">
                    <Code className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">No coding problems available for this topic yet.</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-4">
                  {problems.map((problem, index) => (
                    <Card
                      key={problem.id}
                      className="bg-slate-900/60 backdrop-blur-xl border-slate-800 hover:border-green-500/50 transition-all cursor-pointer"
                      onClick={() => router.push(`/lab/code/${problem.id}`)}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center">
                              <span className="text-green-400 font-bold">{index + 1}</span>
                            </div>
                            <div>
                              <h3 className="text-lg font-semibold text-white">{problem.title}</h3>
                              <div className="flex items-center gap-3 mt-1">
                                <span className={`px-2 py-0.5 text-xs rounded border ${getDifficultyColor(problem.difficulty)}`}>
                                  {problem.difficulty}
                                </span>
                                <span className="text-xs text-slate-400">
                                  {problem.max_score} points
                                </span>
                                <span className="text-xs text-slate-400">
                                  {problem.supported_languages.slice(0, 3).join(', ')}
                                  {problem.supported_languages.length > 3 && ` +${problem.supported_languages.length - 3}`}
                                </span>
                              </div>
                            </div>
                          </div>

                          <Button className="bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600">
                            <Play className="h-4 w-4 mr-2" />
                            Solve
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
