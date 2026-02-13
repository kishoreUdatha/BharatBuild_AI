'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  HelpCircle,
  CheckCircle2,
  XCircle,
  ChevronRight,
  ChevronLeft,
  Award,
  RefreshCw,
  Loader2,
  Lightbulb,
  Code2,
  ArrowRight,
  Trophy,
  AlertTriangle,
} from 'lucide-react'

export interface QuizQuestion {
  id: string
  questionText: string
  options: string[]
  concept?: string
  difficulty: string
  relatedFile?: string
}

export interface QuizResultItem {
  questionId: string
  questionText: string
  selectedOption: number | null
  correctOption: number
  isCorrect: boolean
  explanation?: string
  concept?: string
}

export interface QuizResult {
  totalQuestions: number
  correctAnswers: number
  score: number
  passingScore: number
  passed: boolean
  feedback: string
  results: QuizResultItem[]
}

interface ConceptQuizProps {
  projectId: string
  questions: QuizQuestion[]
  onSubmit: (answers: Record<string, number>) => Promise<QuizResult | null>
  previousResult?: QuizResult | null
  loading?: boolean
  onRetry?: () => void
}

type QuizState = 'intro' | 'quiz' | 'reviewing' | 'results'

export function ConceptQuiz({
  projectId,
  questions,
  onSubmit,
  previousResult,
  loading = false,
  onRetry,
}: ConceptQuizProps) {
  const [state, setState] = useState<QuizState>(previousResult ? 'results' : 'intro')
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [result, setResult] = useState<QuizResult | null>(previousResult || null)
  const [submitting, setSubmitting] = useState(false)
  const [showExplanation, setShowExplanation] = useState<string | null>(null)

  const totalQuestions = questions.length
  const answeredCount = Object.keys(answers).length
  const currentQ = questions[currentQuestion]
  const isAnswered = currentQ && answers[currentQ.id] !== undefined

  // Start quiz
  const startQuiz = useCallback(() => {
    setAnswers({})
    setCurrentQuestion(0)
    setResult(null)
    setState('quiz')
  }, [])

  // Select answer
  const selectAnswer = useCallback((questionId: string, optionIndex: number) => {
    setAnswers(prev => ({ ...prev, [questionId]: optionIndex }))
  }, [])

  // Navigate questions
  const goToNext = useCallback(() => {
    if (currentQuestion < totalQuestions - 1) {
      setCurrentQuestion(prev => prev + 1)
    }
  }, [currentQuestion, totalQuestions])

  const goToPrevious = useCallback(() => {
    if (currentQuestion > 0) {
      setCurrentQuestion(prev => prev - 1)
    }
  }, [currentQuestion])

  const goToQuestion = useCallback((index: number) => {
    setCurrentQuestion(index)
  }, [])

  // Submit quiz
  const handleSubmit = useCallback(async () => {
    setSubmitting(true)
    try {
      const quizResult = await onSubmit(answers)
      if (quizResult) {
        setResult(quizResult)
        setState('results')
      }
    } catch (error) {
      console.error('Failed to submit quiz:', error)
    } finally {
      setSubmitting(false)
    }
  }, [answers, onSubmit])

  // Retry quiz
  const handleRetry = useCallback(() => {
    if (onRetry) {
      onRetry()
    }
    startQuiz()
  }, [onRetry, startQuiz])

  // Review answers
  const reviewAnswers = useCallback(() => {
    setCurrentQuestion(0)
    setState('reviewing')
  }, [])

  // Get difficulty badge color
  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'hard':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      default:
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
    }
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
        <p className="text-gray-400">Loading quiz questions...</p>
      </div>
    )
  }

  // Intro screen
  if (state === 'intro') {
    return (
      <div className="text-center py-8">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center mx-auto mb-4">
          <HelpCircle className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-xl font-semibold text-white mb-2">Concept Quiz</h3>
        <p className="text-gray-400 mb-6 max-w-md mx-auto">
          Test your understanding of the code you just reviewed. You need 70% to pass and unlock the download.
        </p>

        <div className="flex flex-wrap justify-center gap-4 mb-6 text-sm">
          <div className="px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700">
            <span className="text-gray-400">Questions:</span>
            <span className="text-white ml-2 font-medium">{totalQuestions}</span>
          </div>
          <div className="px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700">
            <span className="text-gray-400">Passing Score:</span>
            <span className="text-green-400 ml-2 font-medium">70%</span>
          </div>
          <div className="px-4 py-2 rounded-lg bg-gray-800/50 border border-gray-700">
            <span className="text-gray-400">Time Limit:</span>
            <span className="text-white ml-2 font-medium">None</span>
          </div>
        </div>

        <button
          onClick={startQuiz}
          className="px-6 py-3 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 text-white font-medium hover:from-purple-600 hover:to-blue-600 transition-all flex items-center gap-2 mx-auto"
        >
          Start Quiz
          <ArrowRight className="w-4 h-4" />
        </button>

        {previousResult && (
          <p className="mt-4 text-sm text-gray-500">
            Previous attempt: {previousResult.score}% ({previousResult.passed ? 'Passed' : 'Failed'})
          </p>
        )}
      </div>
    )
  }

  // Results screen
  if (state === 'results' && result) {
    return (
      <div className="text-center py-6">
        {/* Result Header */}
        <div
          className={`w-20 h-20 rounded-2xl flex items-center justify-center mx-auto mb-4 ${
            result.passed
              ? 'bg-gradient-to-br from-green-500 to-emerald-600'
              : 'bg-gradient-to-br from-red-500 to-orange-600'
          }`}
        >
          {result.passed ? (
            <Trophy className="w-10 h-10 text-white" />
          ) : (
            <AlertTriangle className="w-10 h-10 text-white" />
          )}
        </div>

        <h3 className="text-2xl font-bold text-white mb-2">
          {result.passed ? 'Congratulations!' : 'Keep Learning!'}
        </h3>

        <div className="text-5xl font-bold mb-2">
          <span className={result.passed ? 'text-green-400' : 'text-red-400'}>
            {result.score}%
          </span>
        </div>

        <p className="text-gray-400 mb-4">
          {result.correctAnswers} out of {result.totalQuestions} correct
        </p>

        <p className="text-sm text-gray-300 max-w-md mx-auto mb-6">
          {result.feedback}
        </p>

        {/* Score breakdown */}
        <div className="flex justify-center gap-6 mb-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{result.correctAnswers}</div>
            <div className="text-xs text-gray-500">Correct</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-400">
              {result.totalQuestions - result.correctAnswers}
            </div>
            <div className="text-xs text-gray-500">Incorrect</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap justify-center gap-3">
          <button
            onClick={reviewAnswers}
            className="px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm hover:bg-gray-700 transition-colors flex items-center gap-2"
          >
            <HelpCircle className="w-4 h-4" />
            Review Answers
          </button>

          {!result.passed && (
            <button
              onClick={handleRetry}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Try Again
            </button>
          )}

          {result.passed && (
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm">
              <CheckCircle2 className="w-4 h-4" />
              Download Unlocked
            </div>
          )}
        </div>
      </div>
    )
  }

  // Quiz/Review screen
  if (!currentQ) {
    return (
      <div className="py-8 text-center text-gray-400">
        No questions available
      </div>
    )
  }

  const isReviewing = state === 'reviewing'
  const resultItem = isReviewing && result
    ? result.results.find(r => r.questionId === currentQ.id)
    : null

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      <div className="flex items-center gap-3 mb-4">
        <span className="text-sm text-gray-500">
          {currentQuestion + 1} / {totalQuestions}
        </span>
        <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden">
          <motion.div
            className={`h-full ${isReviewing ? 'bg-purple-500' : 'bg-blue-500'}`}
            initial={{ width: 0 }}
            animate={{ width: `${((currentQuestion + 1) / totalQuestions) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Question Navigation Dots */}
      <div className="flex justify-center gap-2 flex-wrap mb-4">
        {questions.map((q, idx) => {
          const isAnsweredQ = answers[q.id] !== undefined
          const resultQ = result?.results.find(r => r.questionId === q.id)
          const isCurrent = idx === currentQuestion

          let dotColor = 'bg-gray-700'
          if (isReviewing && resultQ) {
            dotColor = resultQ.isCorrect ? 'bg-green-500' : 'bg-red-500'
          } else if (isAnsweredQ) {
            dotColor = 'bg-blue-500'
          }

          return (
            <button
              key={q.id}
              onClick={() => goToQuestion(idx)}
              className={`w-3 h-3 rounded-full transition-all ${dotColor} ${
                isCurrent ? 'ring-2 ring-offset-2 ring-offset-gray-900 ring-blue-400' : ''
              }`}
            />
          )
        })}
      </div>

      {/* Question Card */}
      <div className="p-4 rounded-xl bg-gray-800/50 border border-gray-700/50">
        {/* Question Meta */}
        <div className="flex items-center gap-2 mb-3">
          {currentQ.concept && (
            <span className="px-2 py-0.5 text-xs rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
              {currentQ.concept}
            </span>
          )}
          <span
            className={`px-2 py-0.5 text-xs rounded border ${getDifficultyColor(
              currentQ.difficulty
            )}`}
          >
            {currentQ.difficulty}
          </span>
        </div>

        {/* Question Text */}
        <h4 className="text-white font-medium mb-4 leading-relaxed">
          {currentQ.questionText}
        </h4>

        {/* Related File */}
        {currentQ.relatedFile && (
          <div className="flex items-center gap-2 mb-4 text-xs text-gray-500">
            <Code2 className="w-3 h-3" />
            <span className="font-mono">{currentQ.relatedFile}</span>
          </div>
        )}

        {/* Options */}
        <div className="space-y-2">
          {currentQ.options.map((option, idx) => {
            const isSelected = answers[currentQ.id] === idx
            const isCorrect = resultItem?.correctOption === idx
            const isWrong = isReviewing && isSelected && !isCorrect

            let optionStyle = 'border-gray-700 bg-gray-900/50'
            if (isReviewing) {
              if (isCorrect) {
                optionStyle = 'border-green-500 bg-green-500/10'
              } else if (isWrong) {
                optionStyle = 'border-red-500 bg-red-500/10'
              }
            } else if (isSelected) {
              optionStyle = 'border-blue-500 bg-blue-500/10'
            }

            return (
              <button
                key={idx}
                onClick={() => !isReviewing && selectAnswer(currentQ.id, idx)}
                disabled={isReviewing}
                className={`w-full p-3 rounded-lg border text-left transition-all ${optionStyle} ${
                  !isReviewing ? 'hover:border-blue-500/50 hover:bg-blue-500/5' : ''
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                      isReviewing && isCorrect
                        ? 'bg-green-500 text-white'
                        : isWrong
                        ? 'bg-red-500 text-white'
                        : isSelected
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-700 text-gray-400'
                    }`}
                  >
                    {isReviewing && isCorrect ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : isWrong ? (
                      <XCircle className="w-4 h-4" />
                    ) : (
                      <span className="text-xs font-medium">
                        {String.fromCharCode(65 + idx)}
                      </span>
                    )}
                  </div>
                  <span
                    className={`text-sm ${
                      isReviewing && isCorrect
                        ? 'text-green-300'
                        : isWrong
                        ? 'text-red-300'
                        : isSelected
                        ? 'text-blue-300'
                        : 'text-gray-300'
                    }`}
                  >
                    {option}
                  </span>
                </div>
              </button>
            )
          })}
        </div>

        {/* Explanation (review mode) */}
        {isReviewing && resultItem?.explanation && (
          <div className="mt-4 p-3 rounded-lg bg-purple-500/10 border border-purple-500/30">
            <div className="flex items-center gap-2 text-purple-400 text-sm font-medium mb-2">
              <Lightbulb className="w-4 h-4" />
              <span>Explanation</span>
            </div>
            <p className="text-sm text-gray-300">{resultItem.explanation}</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={goToPrevious}
          disabled={currentQuestion === 0}
          className="px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          <ChevronLeft className="w-4 h-4" />
          Previous
        </button>

        {currentQuestion < totalQuestions - 1 ? (
          <button
            onClick={goToNext}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 transition-colors flex items-center gap-2"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        ) : isReviewing ? (
          <button
            onClick={() => setState('results')}
            className="px-4 py-2 rounded-lg bg-purple-600 text-white text-sm hover:bg-purple-700 transition-colors flex items-center gap-2"
          >
            Back to Results
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={answeredCount < totalQuestions || submitting}
            className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {submitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                Submit Quiz ({answeredCount}/{totalQuestions})
              </>
            )}
          </button>
        )}
      </div>

      {/* Unanswered Warning */}
      {!isReviewing && answeredCount < totalQuestions && currentQuestion === totalQuestions - 1 && (
        <p className="text-center text-xs text-yellow-500">
          Answer all questions to submit ({totalQuestions - answeredCount} remaining)
        </p>
      )}
    </div>
  )
}
