'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Trophy, XCircle, CheckCircle2, Brain, Code, BookOpen, MessageSquare,
  Home, Download, Share2
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface QuizResult {
  registration_id: string
  total_questions: number
  attempted: number
  correct: number
  wrong: number
  total_marks: number
  marks_obtained: number
  percentage: number
  is_qualified: boolean
  passing_percentage: number
  logical_score: number
  logical_total: number
  technical_score: number
  technical_total: number
  ai_ml_score: number
  ai_ml_total: number
  english_score: number
  english_total: number
}

function ResultPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const driveId = searchParams.get('drive')
  const email = searchParams.get('email')

  const [result, setResult] = useState<QuizResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // First try to get from localStorage (just submitted)
    const storedResult = localStorage.getItem('quiz_result')
    if (storedResult) {
      setResult(JSON.parse(storedResult))
      localStorage.removeItem('quiz_result')
      setLoading(false)
      return
    }

    // Otherwise fetch from API
    if (driveId && email) {
      fetchResult()
    } else {
      setLoading(false)
    }
  }, [driveId, email])

  const fetchResult = async () => {
    try {
      const response = await fetch(
        `${API_URL}/api/v1/campus-drive/drives/${driveId}/result/${email}`
      )

      if (response.ok) {
        const data = await response.json()
        setResult(data)
      }
    } catch (error) {
      console.error('Error fetching result:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-6">
            <XCircle className="h-16 w-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-bold text-gray-900 mb-2">Result Not Found</h2>
            <p className="text-gray-600 mb-4">
              We couldn&apos;t find your quiz result. Please make sure you have completed the quiz.
            </p>
            <Button onClick={() => router.push('/campus-drive')}>
              Go to Registration
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const sections = [
    { name: 'Logical Thinking', score: result.logical_score, total: result.logical_total, icon: Brain, color: 'blue' },
    { name: 'Technical', score: result.technical_score, total: result.technical_total, icon: Code, color: 'green' },
    { name: 'AI/ML', score: result.ai_ml_score, total: result.ai_ml_total, icon: BookOpen, color: 'purple' },
    { name: 'English', score: result.english_score, total: result.english_total, icon: MessageSquare, color: 'orange' },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Result Header */}
        <Card className={`mb-8 shadow-2xl overflow-hidden ${
          result.is_qualified ? 'border-green-500 border-2' : 'border-red-500 border-2'
        }`}>
          <div className={`p-8 text-center ${
            result.is_qualified
              ? 'bg-gradient-to-r from-green-500 to-emerald-500'
              : 'bg-gradient-to-r from-red-500 to-rose-500'
          } text-white`}>
            <div className={`w-24 h-24 mx-auto mb-4 rounded-full flex items-center justify-center ${
              result.is_qualified ? 'bg-white/20' : 'bg-white/20'
            }`}>
              {result.is_qualified ? (
                <Trophy className="h-12 w-12" />
              ) : (
                <XCircle className="h-12 w-12" />
              )}
            </div>

            <h1 className="text-3xl font-bold mb-2">
              {result.is_qualified ? 'Congratulations!' : 'Better Luck Next Time'}
            </h1>
            <p className="text-xl opacity-90">
              {result.is_qualified
                ? 'You have qualified for the next round!'
                : 'You did not meet the minimum qualifying score.'}
            </p>
          </div>

          <CardContent className="p-8">
            {/* Score Circle */}
            <div className="flex justify-center mb-8">
              <div className="relative">
                <svg className="w-48 h-48 transform -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    stroke="#e5e7eb"
                    strokeWidth="12"
                    fill="none"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    stroke={result.is_qualified ? '#22c55e' : '#ef4444'}
                    strokeWidth="12"
                    fill="none"
                    strokeDasharray={2 * Math.PI * 88}
                    strokeDashoffset={2 * Math.PI * 88 * (1 - result.percentage / 100)}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-5xl font-bold text-gray-900">
                    {result.percentage.toFixed(1)}%
                  </span>
                  <span className="text-gray-500">Score</span>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-blue-600">{result.total_questions}</p>
                <p className="text-sm text-gray-600">Total Questions</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-green-600">{result.correct}</p>
                <p className="text-sm text-gray-600">Correct</p>
              </div>
              <div className="bg-red-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-red-600">{result.wrong}</p>
                <p className="text-sm text-gray-600">Wrong</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <p className="text-3xl font-bold text-gray-600">
                  {result.total_questions - result.attempted}
                </p>
                <p className="text-sm text-gray-600">Skipped</p>
              </div>
            </div>

            {/* Pass Info */}
            <div className={`rounded-lg p-4 mb-8 ${
              result.is_qualified ? 'bg-green-50' : 'bg-amber-50'
            }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {result.is_qualified ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  ) : (
                    <XCircle className="h-5 w-5 text-amber-600" />
                  )}
                  <span className={result.is_qualified ? 'text-green-800' : 'text-amber-800'}>
                    Passing Score: {result.passing_percentage}%
                  </span>
                </div>
                <span className={`font-medium ${
                  result.is_qualified ? 'text-green-600' : 'text-amber-600'
                }`}>
                  Your Score: {result.percentage.toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Section-wise Scores */}
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Section-wise Performance</h3>
            <div className="space-y-4">
              {sections.map((section) => {
                const percentage = section.total > 0 ? (section.score / section.total) * 100 : 0
                const Icon = section.icon

                return (
                  <div key={section.name} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <Icon className={`h-5 w-5 text-${section.color}-600`} />
                        <span className="font-medium text-gray-700">{section.name}</span>
                      </div>
                      <span className="font-medium">
                        {section.score} / {section.total}
                      </span>
                    </div>
                    <Progress
                      value={percentage}
                      className="h-2"
                    />
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button
            variant="outline"
            className="flex items-center gap-2"
            onClick={() => router.push('/')}
          >
            <Home className="h-4 w-4" />
            Go to Home
          </Button>

          {result.is_qualified && (
            <Button
              className="bg-green-600 hover:bg-green-700 flex items-center gap-2"
              onClick={() => {
                // Could implement certificate download here
                alert('Certificate will be sent to your registered email.')
              }}
            >
              <Download className="h-4 w-4" />
              Download Certificate
            </Button>
          )}
        </div>

        {/* Footer Message */}
        <div className="text-center mt-8 text-gray-600">
          <p>
            {result.is_qualified
              ? 'Your result has been shared with the admin. You will be contacted for the next round.'
              : 'Keep practicing and try again in the next drive!'}
          </p>
        </div>
      </div>
    </div>
  )
}

function ResultLoadingFallback() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  )
}

export default function ResultPage() {
  return (
    <Suspense fallback={<ResultLoadingFallback />}>
      <ResultPageContent />
    </Suspense>
  )
}
