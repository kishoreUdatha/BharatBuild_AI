'use client'

import { useState, useEffect, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import {
  Clock, AlertCircle, ChevronLeft, ChevronRight, Brain, Code,
  BookOpen, MessageSquare, CheckCircle, Flag, Send
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Question {
  id: string
  question_text: string
  category: string
  options: string[]
  marks: number
}

interface QuizData {
  registration_id: string
  drive_name: string
  duration_minutes: number
  total_questions: number
  questions: Question[]
  start_time: string
}

const categoryColors: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
  logical: { bg: 'bg-blue-100', text: 'text-blue-700', icon: <Brain className="h-4 w-4" /> },
  technical: { bg: 'bg-green-100', text: 'text-green-700', icon: <Code className="h-4 w-4" /> },
  ai_ml: { bg: 'bg-purple-100', text: 'text-purple-700', icon: <BookOpen className="h-4 w-4" /> },
  english: { bg: 'bg-orange-100', text: 'text-orange-700', icon: <MessageSquare className="h-4 w-4" /> },
}

function QuizPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const driveId = searchParams.get('drive')
  const email = searchParams.get('email')

  const [quizData, setQuizData] = useState<QuizData | null>(null)
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number | null>>({})
  const [flagged, setFlagged] = useState<Set<string>>(new Set())
  const [timeLeft, setTimeLeft] = useState<number>(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showConfirmSubmit, setShowConfirmSubmit] = useState(false)

  const startQuiz = useCallback(async () => {
    if (!driveId || !email) {
      setError('Missing drive ID or email')
      setLoading(false)
      return
    }

    try {
      const response = await fetch(
        `${API_URL}/campus-drive/drives/${driveId}/quiz/start?email=${encodeURIComponent(email)}`,
        { method: 'POST' }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to start quiz')
      }

      const data: QuizData = await response.json()
      setQuizData(data)
      setTimeLeft(data.duration_minutes * 60)

      // Initialize answers
      const initialAnswers: Record<string, number | null> = {}
      data.questions.forEach(q => {
        initialAnswers[q.id] = null
      })
      setAnswers(initialAnswers)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start quiz')
    } finally {
      setLoading(false)
    }
  }, [driveId, email])

  useEffect(() => {
    startQuiz()
  }, [startQuiz])

  // Timer effect
  useEffect(() => {
    if (timeLeft <= 0 || !quizData) return

    const timer = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          // Auto-submit when time runs out
          handleSubmit(true)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [timeLeft, quizData])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const handleAnswerSelect = (optionIndex: number) => {
    if (!quizData) return
    const questionId = quizData.questions[currentQuestionIndex].id
    setAnswers(prev => ({ ...prev, [questionId]: optionIndex }))
  }

  const toggleFlag = () => {
    if (!quizData) return
    const questionId = quizData.questions[currentQuestionIndex].id
    setFlagged(prev => {
      const newSet = new Set(prev)
      if (newSet.has(questionId)) {
        newSet.delete(questionId)
      } else {
        newSet.add(questionId)
      }
      return newSet
    })
  }

  const goToQuestion = (index: number) => {
    setCurrentQuestionIndex(index)
  }

  const handleSubmit = async (autoSubmit = false) => {
    if (!quizData || submitting) return

    if (!autoSubmit && !showConfirmSubmit) {
      setShowConfirmSubmit(true)
      return
    }

    setSubmitting(true)
    setShowConfirmSubmit(false)

    try {
      const submission = {
        answers: Object.entries(answers).map(([questionId, selectedOption]) => ({
          question_id: questionId,
          selected_option: selectedOption
        }))
      }

      const response = await fetch(
        `${API_URL}/campus-drive/drives/${driveId}/quiz/submit?email=${encodeURIComponent(email!)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(submission)
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to submit quiz')
      }

      const result = await response.json()

      // Store result and redirect
      localStorage.setItem('quiz_result', JSON.stringify(result))
      router.push(`/campus-drive/result?drive=${driveId}&email=${email}`)

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit quiz')
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading quiz...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardContent className="pt-6">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
            <Button
              className="w-full mt-4"
              onClick={() => router.push('/campus-drive')}
            >
              Go Back to Registration
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!quizData) return null

  const currentQuestion = quizData.questions[currentQuestionIndex]
  const answeredCount = Object.values(answers).filter(a => a !== null).length
  const progress = (answeredCount / quizData.total_questions) * 100
  const category = categoryColors[currentQuestion.category] || categoryColors.logical

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header with Timer */}
      <div className="bg-white shadow-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold text-gray-900">{quizData.drive_name}</h1>
              <p className="text-sm text-gray-500">
                Question {currentQuestionIndex + 1} of {quizData.total_questions}
              </p>
            </div>

            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              timeLeft < 300 ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
            }`}>
              <Clock className="h-5 w-5" />
              <span className="text-xl font-mono font-bold">{formatTime(timeLeft)}</span>
            </div>
          </div>

          <div className="mt-2">
            <Progress value={progress} className="h-2" />
            <p className="text-xs text-gray-500 mt-1">
              {answeredCount} of {quizData.total_questions} answered
            </p>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Question Panel */}
          <div className="lg:col-span-3">
            <Card className="shadow-lg">
              <CardHeader className="border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium flex items-center gap-1 ${category.bg} ${category.text}`}>
                      {category.icon}
                      {currentQuestion.category.replace('_', '/')}
                    </span>
                    <span className="text-sm text-gray-500">
                      {currentQuestion.marks} mark{currentQuestion.marks > 1 ? 's' : ''}
                    </span>
                  </div>
                  <Button
                    variant={flagged.has(currentQuestion.id) ? 'default' : 'outline'}
                    size="sm"
                    onClick={toggleFlag}
                  >
                    <Flag className={`h-4 w-4 mr-1 ${flagged.has(currentQuestion.id) ? 'fill-current' : ''}`} />
                    {flagged.has(currentQuestion.id) ? 'Flagged' : 'Flag for Review'}
                  </Button>
                </div>
              </CardHeader>

              <CardContent className="p-6">
                <h2 className="text-xl font-medium text-gray-900 mb-6">
                  {currentQuestionIndex + 1}. {currentQuestion.question_text}
                </h2>

                <div className="space-y-3">
                  {currentQuestion.options.map((option, index) => (
                    <button
                      key={index}
                      onClick={() => handleAnswerSelect(index)}
                      className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                        answers[currentQuestion.id] === index
                          ? 'border-indigo-600 bg-indigo-50'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center font-medium ${
                          answers[currentQuestion.id] === index
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-200 text-gray-700'
                        }`}>
                          {String.fromCharCode(65 + index)}
                        </div>
                        <span className="text-gray-700">{option}</span>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Navigation */}
                <div className="flex items-center justify-between mt-8 pt-6 border-t">
                  <Button
                    variant="outline"
                    onClick={() => goToQuestion(currentQuestionIndex - 1)}
                    disabled={currentQuestionIndex === 0}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Previous
                  </Button>

                  {currentQuestionIndex === quizData.total_questions - 1 ? (
                    <Button
                      className="bg-green-600 hover:bg-green-700"
                      onClick={() => handleSubmit()}
                    >
                      <Send className="h-4 w-4 mr-1" />
                      Submit Quiz
                    </Button>
                  ) : (
                    <Button
                      onClick={() => goToQuestion(currentQuestionIndex + 1)}
                    >
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Question Navigator */}
          <div className="lg:col-span-1">
            <Card className="shadow-lg sticky top-24">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Question Navigator</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-5 gap-2">
                  {quizData.questions.map((q, index) => {
                    const isAnswered = answers[q.id] !== null
                    const isFlagged = flagged.has(q.id)
                    const isCurrent = index === currentQuestionIndex

                    return (
                      <button
                        key={q.id}
                        onClick={() => goToQuestion(index)}
                        className={`relative w-10 h-10 rounded-lg font-medium text-sm transition-all ${
                          isCurrent
                            ? 'ring-2 ring-indigo-600 ring-offset-2'
                            : ''
                        } ${
                          isAnswered
                            ? 'bg-green-500 text-white'
                            : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                        }`}
                      >
                        {index + 1}
                        {isFlagged && (
                          <Flag className="absolute -top-1 -right-1 h-3 w-3 text-orange-500 fill-current" />
                        )}
                      </button>
                    )
                  })}
                </div>

                <div className="mt-4 pt-4 border-t space-y-2 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-green-500 rounded"></div>
                    <span>Answered ({answeredCount})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-4 h-4 bg-gray-200 rounded"></div>
                    <span>Not Answered ({quizData.total_questions - answeredCount})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Flag className="h-4 w-4 text-orange-500 fill-current" />
                    <span>Flagged ({flagged.size})</span>
                  </div>
                </div>

                <Button
                  className="w-full mt-4 bg-green-600 hover:bg-green-700"
                  onClick={() => handleSubmit()}
                  disabled={submitting}
                >
                  <Send className="h-4 w-4 mr-1" />
                  Submit Quiz
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Confirm Submit Modal */}
      {showConfirmSubmit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle>Submit Quiz?</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <p className="text-gray-600">
                  You have answered <strong>{answeredCount}</strong> out of{' '}
                  <strong>{quizData.total_questions}</strong> questions.
                </p>

                {quizData.total_questions - answeredCount > 0 && (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      You have {quizData.total_questions - answeredCount} unanswered questions.
                    </AlertDescription>
                  </Alert>
                )}

                {flagged.size > 0 && (
                  <Alert>
                    <Flag className="h-4 w-4" />
                    <AlertDescription>
                      You have {flagged.size} flagged questions to review.
                    </AlertDescription>
                  </Alert>
                )}

                <div className="flex gap-3">
                  <Button
                    variant="outline"
                    className="flex-1"
                    onClick={() => setShowConfirmSubmit(false)}
                  >
                    Review Answers
                  </Button>
                  <Button
                    className="flex-1 bg-green-600 hover:bg-green-700"
                    onClick={() => handleSubmit(true)}
                    disabled={submitting}
                  >
                    {submitting ? 'Submitting...' : 'Confirm Submit'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

function QuizLoadingFallback() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
        <p className="text-gray-600">Loading quiz...</p>
      </div>
    </div>
  )
}

export default function QuizPage() {
  return (
    <Suspense fallback={<QuizLoadingFallback />}>
      <QuizPageContent />
    </Suspense>
  )
}
