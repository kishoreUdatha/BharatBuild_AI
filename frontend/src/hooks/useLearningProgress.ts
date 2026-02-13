/**
 * useLearningProgress Hook
 * Manages learning checkpoint state and API interactions
 * Gates download until student demonstrates understanding
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'

// API base URL
const API_BASE = '/api/v1/learning'

export interface LearningProgress {
  projectId: string
  userId: string

  // Checkpoint 1: Code Understanding
  checkpoint1Completed: boolean
  filesReviewed: string[]
  filesReviewedCount: number

  // Checkpoint 2: Concept Quiz
  checkpoint2Score: number | null
  checkpoint2Passed: boolean
  checkpoint2Attempts: number

  // Checkpoint 3: Viva Review
  checkpoint3Completed: boolean
  vivaQuestionsReviewed: number
  vivaTotalQuestions: number

  // Overall
  overallProgress: number
  canDownload: boolean
  certificateGenerated: boolean
  certificateId: string | null
}

export interface QuizQuestion {
  id: string
  questionText: string
  options: string[]
  concept?: string
  difficulty: string
  relatedFile?: string
}

export interface QuizResult {
  totalQuestions: number
  correctAnswers: number
  score: number
  passingScore: number
  passed: boolean
  feedback: string
  results: Array<{
    questionId: string
    questionText: string
    selectedOption: number | null
    correctOption: number
    isCorrect: boolean
    explanation?: string
    concept?: string
  }>
}

export interface FileExplanation {
  filePath: string
  simpleExplanation?: string
  technicalExplanation?: string
  keyConcepts: string[]
  analogies: string[]
  bestPractices: string[]
}

const defaultProgress: LearningProgress = {
  projectId: '',
  userId: '',
  checkpoint1Completed: false,
  filesReviewed: [],
  filesReviewedCount: 0,
  checkpoint2Score: null,
  checkpoint2Passed: false,
  checkpoint2Attempts: 0,
  checkpoint3Completed: false,
  vivaQuestionsReviewed: 0,
  vivaTotalQuestions: 25,
  overallProgress: 0,
  canDownload: false,
  certificateGenerated: false,
  certificateId: null,
}

export function useLearningProgress(projectId: string | null) {
  const [progress, setProgress] = useState<LearningProgress>(defaultProgress)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Quiz state
  const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([])
  const [quizLoading, setQuizLoading] = useState(false)
  const [quizResult, setQuizResult] = useState<QuizResult | null>(null)

  // Fetch learning progress
  const fetchProgress = useCallback(async () => {
    if (!projectId) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/progress`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Failed to fetch learning progress')
      }

      const data = await response.json()
      setProgress({
        projectId: data.project_id,
        userId: data.user_id,
        checkpoint1Completed: data.checkpoint_1_completed,
        filesReviewed: data.files_reviewed || [],
        filesReviewedCount: data.files_reviewed_count,
        checkpoint2Score: data.checkpoint_2_score,
        checkpoint2Passed: data.checkpoint_2_passed,
        checkpoint2Attempts: data.checkpoint_2_attempts,
        checkpoint3Completed: data.checkpoint_3_completed,
        vivaQuestionsReviewed: data.viva_questions_reviewed,
        vivaTotalQuestions: data.viva_total_questions,
        overallProgress: data.overall_progress,
        canDownload: data.can_download,
        certificateGenerated: data.certificate_generated,
        certificateId: data.certificate_id,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  // Mark a file as understood
  const markFileUnderstood = useCallback(async (filePath: string) => {
    if (!projectId) return

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/mark-understood`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ file_path: filePath }),
      })

      if (!response.ok) {
        throw new Error('Failed to mark file as understood')
      }

      const data = await response.json()

      // Update local state
      setProgress(prev => ({
        ...prev,
        filesReviewed: [...prev.filesReviewed, filePath],
        filesReviewedCount: data.files_reviewed,
        checkpoint1Completed: data.checkpoint_1_completed,
      }))

      if (data.checkpoint_1_completed) {
        toast.success('Checkpoint 1 Complete! You can now take the quiz.')
      }

      return data
    } catch (err) {
      toast.error('Failed to mark file as understood')
      throw err
    }
  }, [projectId])

  // Get file explanation
  const getFileExplanation = useCallback(async (filePath: string): Promise<FileExplanation | null> => {
    if (!projectId) return null

    try {
      const encodedPath = encodeURIComponent(filePath)
      const response = await fetch(
        `${API_BASE}/projects/${projectId}/file-explanation/${encodedPath}`,
        { credentials: 'include' }
      )

      if (!response.ok) {
        throw new Error('Failed to fetch explanation')
      }

      const data = await response.json()
      return {
        filePath: data.file_path,
        simpleExplanation: data.simple_explanation,
        technicalExplanation: data.technical_explanation,
        keyConcepts: data.key_concepts || [],
        analogies: data.analogies || [],
        bestPractices: data.best_practices || [],
      }
    } catch (err) {
      console.error('Failed to get file explanation:', err)
      return null
    }
  }, [projectId])

  // Fetch quiz questions
  const fetchQuiz = useCallback(async () => {
    if (!projectId) return

    setQuizLoading(true)

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/quiz`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Failed to fetch quiz')
      }

      const data = await response.json()
      setQuizQuestions(data.questions.map((q: any) => ({
        id: q.id,
        questionText: q.question_text,
        options: q.options,
        concept: q.concept,
        difficulty: q.difficulty,
        relatedFile: q.related_file,
      })))

      return data.questions
    } catch (err) {
      toast.error('Failed to load quiz questions')
      throw err
    } finally {
      setQuizLoading(false)
    }
  }, [projectId])

  // Submit quiz answers
  const submitQuiz = useCallback(async (answers: Record<string, number>): Promise<QuizResult | null> => {
    if (!projectId) return null

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/quiz/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ answers }),
      })

      if (!response.ok) {
        throw new Error('Failed to submit quiz')
      }

      const data = await response.json()
      const result: QuizResult = {
        totalQuestions: data.total_questions,
        correctAnswers: data.correct_answers,
        score: data.score,
        passingScore: data.passing_score,
        passed: data.passed,
        feedback: data.feedback,
        results: data.results.map((r: any) => ({
          questionId: r.question_id,
          questionText: r.question_text,
          selectedOption: r.selected_option,
          correctOption: r.correct_option,
          isCorrect: r.is_correct,
          explanation: r.explanation,
          concept: r.concept,
        })),
      }

      setQuizResult(result)

      // Update progress
      setProgress(prev => ({
        ...prev,
        checkpoint2Score: result.score,
        checkpoint2Passed: result.passed,
        checkpoint2Attempts: prev.checkpoint2Attempts + 1,
        canDownload: result.passed,
      }))

      if (result.passed) {
        toast.success(`Quiz passed with ${result.score}%! Download unlocked.`)
      } else {
        toast.info(`Score: ${result.score}%. Need 70% to pass. Try again!`)
      }

      return result
    } catch (err) {
      toast.error('Failed to submit quiz')
      throw err
    }
  }, [projectId])

  // Mark viva question as reviewed
  const markVivaReviewed = useCallback(async (questionIndex: number) => {
    if (!projectId) return

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/viva/mark-reviewed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ question_index: questionIndex }),
      })

      if (!response.ok) {
        throw new Error('Failed to mark viva question')
      }

      const data = await response.json()

      setProgress(prev => ({
        ...prev,
        vivaQuestionsReviewed: data.viva_questions_reviewed,
        vivaTotalQuestions: data.viva_total_questions,
        checkpoint3Completed: data.checkpoint_3_completed,
      }))

      if (data.checkpoint_3_completed) {
        toast.success('Checkpoint 3 Complete! Viva preparation done.')
      }

      return data
    } catch (err) {
      console.error('Failed to mark viva question:', err)
    }
  }, [projectId])

  // Check download eligibility
  const checkDownloadEligibility = useCallback(async () => {
    if (!projectId) return { canDownload: false }

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/can-download`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Failed to check eligibility')
      }

      const data = await response.json()

      setProgress(prev => ({
        ...prev,
        canDownload: data.can_download,
      }))

      return data
    } catch (err) {
      console.error('Failed to check download eligibility:', err)
      return { canDownload: false }
    }
  }, [projectId])

  // Generate certificate
  const generateCertificate = useCallback(async () => {
    if (!projectId) return null

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/certificate/generate`, {
        method: 'POST',
        credentials: 'include',
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to generate certificate')
      }

      const data = await response.json()

      setProgress(prev => ({
        ...prev,
        certificateGenerated: true,
        certificateId: data.certificate_id,
      }))

      toast.success('Certificate generated!')
      return data
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to generate certificate')
      throw err
    }
  }, [projectId])

  // Download certificate
  const downloadCertificate = useCallback(async () => {
    if (!projectId) return

    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/certificate/download`, {
        credentials: 'include',
      })

      if (!response.ok) {
        throw new Error('Failed to download certificate')
      }

      // Get filename from Content-Disposition header
      const disposition = response.headers.get('Content-Disposition')
      const filenameMatch = disposition?.match(/filename="(.+)"/)
      const filename = filenameMatch?.[1] || 'LEARNING_CERTIFICATE.pdf'

      // Download the file
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      toast.success('Certificate downloaded!')
    } catch (err) {
      toast.error('Failed to download certificate')
    }
  }, [projectId])

  // Fetch progress on mount and when projectId changes
  useEffect(() => {
    if (projectId) {
      fetchProgress()
    }
  }, [projectId, fetchProgress])

  return {
    // Progress state
    progress,
    loading,
    error,

    // Quiz state
    quizQuestions,
    quizLoading,
    quizResult,

    // Actions
    fetchProgress,
    markFileUnderstood,
    getFileExplanation,
    fetchQuiz,
    submitQuiz,
    markVivaReviewed,
    checkDownloadEligibility,
    generateCertificate,
    downloadCertificate,

    // Computed
    canDownload: progress.canDownload,
    learningProgress: progress.overallProgress,
  }
}
