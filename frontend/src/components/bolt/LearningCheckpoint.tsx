'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  GraduationCap,
  BookOpen,
  HelpCircle,
  MessageSquare,
  Download,
  Award,
  CheckCircle2,
  Circle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Lock,
  Unlock,
  ArrowRight,
  Trophy,
} from 'lucide-react'
import { FileExplanationList, FileExplanationData } from '../learning/FileExplanation'
import { ConceptQuiz, QuizQuestion, QuizResult } from '../learning/ConceptQuiz'
import { useLearningProgress } from '@/hooks/useLearningProgress'

interface ProjectFile {
  path: string
  content?: string
  type: 'file' | 'folder'
  children?: ProjectFile[]
  language?: string
}

interface LearningCheckpointProps {
  projectId: string
  files: ProjectFile[]
  onDownloadEnabled?: () => void
}

type CheckpointId = 'checkpoint1' | 'checkpoint2' | 'checkpoint3'

export function LearningCheckpoint({
  projectId,
  files,
  onDownloadEnabled,
}: LearningCheckpointProps) {
  const [activeCheckpoint, setActiveCheckpoint] = useState<CheckpointId>('checkpoint1')
  const [explanations, setExplanations] = useState<Map<string, FileExplanationData>>(new Map())
  const [loadingFiles, setLoadingFiles] = useState<string[]>([])

  const {
    progress,
    loading,
    quizQuestions,
    quizLoading,
    quizResult,
    fetchProgress,
    markFileUnderstood,
    getFileExplanation,
    fetchQuiz,
    submitQuiz,
    markVivaReviewed,
    generateCertificate,
    downloadCertificate,
    canDownload,
  } = useLearningProgress(projectId)

  // Flatten files for display
  const flattenFiles = useCallback((fileList: ProjectFile[]): ProjectFile[] => {
    const result: ProjectFile[] = []
    for (const f of fileList) {
      if (f.type === 'file') {
        result.push(f)
      }
      if (f.children) {
        result.push(...flattenFiles(f.children))
      }
    }
    return result
  }, [])

  const flatFiles = useMemo(() => flattenFiles(files), [files, flattenFiles])

  // Handle marking file as understood
  const handleMarkUnderstood = useCallback(async (filePath: string) => {
    await markFileUnderstood(filePath)
  }, [markFileUnderstood])

  // Fetch explanation when expanding file
  const handleFetchExplanation = useCallback(async (filePath: string) => {
    if (explanations.has(filePath)) return

    setLoadingFiles(prev => [...prev, filePath])
    const explanation = await getFileExplanation(filePath)
    if (explanation) {
      setExplanations(prev => new Map(prev).set(filePath, explanation))
    }
    setLoadingFiles(prev => prev.filter(f => f !== filePath))
  }, [explanations, getFileExplanation])

  // Load quiz when switching to checkpoint 2
  useEffect(() => {
    if (activeCheckpoint === 'checkpoint2' && progress.checkpoint1Completed && quizQuestions.length === 0) {
      fetchQuiz()
    }
  }, [activeCheckpoint, progress.checkpoint1Completed, quizQuestions.length, fetchQuiz])

  // Notify parent when download becomes enabled
  useEffect(() => {
    if (canDownload && onDownloadEnabled) {
      onDownloadEnabled()
    }
  }, [canDownload, onDownloadEnabled])

  // Checkpoint data
  const checkpoints = [
    {
      id: 'checkpoint1' as CheckpointId,
      title: 'Code Understanding',
      icon: BookOpen,
      description: 'Review and understand each file in your project',
      completed: progress.checkpoint1Completed,
      progress: Math.min(100, (progress.filesReviewedCount / 5) * 100),
      requirement: 'Review at least 5 files',
    },
    {
      id: 'checkpoint2' as CheckpointId,
      title: 'Concept Quiz',
      icon: HelpCircle,
      description: 'Test your understanding with a short quiz',
      completed: progress.checkpoint2Passed,
      progress: progress.checkpoint2Score || 0,
      requirement: 'Score 70% or higher',
      locked: !progress.checkpoint1Completed,
    },
    {
      id: 'checkpoint3' as CheckpointId,
      title: 'Viva Preparation',
      icon: MessageSquare,
      description: 'Review Q&A to prepare for project defense',
      completed: progress.checkpoint3Completed,
      progress: progress.vivaTotalQuestions > 0
        ? (progress.vivaQuestionsReviewed / progress.vivaTotalQuestions) * 100
        : 0,
      requirement: 'Review 80% of viva questions',
      locked: !progress.checkpoint2Passed,
    },
  ]

  // Get checkpoint status
  const getCheckpointStatus = (checkpoint: typeof checkpoints[0]) => {
    if (checkpoint.completed) return 'completed'
    if (checkpoint.locked) return 'locked'
    if (activeCheckpoint === checkpoint.id) return 'active'
    return 'pending'
  }

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-4" />
        <p className="text-gray-400">Loading learning progress...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
            <GraduationCap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Learning Mode</h2>
            <p className="text-xs text-gray-400">Complete checkpoints to download</p>
          </div>
        </div>

        {/* Overall Progress */}
        <div className="text-right">
          <span className="text-2xl font-bold text-white">{progress.overallProgress}%</span>
          <p className="text-xs text-gray-400">Complete</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-purple-500 via-blue-500 to-cyan-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress.overallProgress}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>

      {/* Download Status */}
      <div
        className={`p-4 rounded-xl border ${
          canDownload
            ? 'border-green-500/50 bg-green-500/10'
            : 'border-yellow-500/50 bg-yellow-500/10'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {canDownload ? (
              <Unlock className="w-5 h-5 text-green-400" />
            ) : (
              <Lock className="w-5 h-5 text-yellow-400" />
            )}
            <div>
              <p className={`font-medium ${canDownload ? 'text-green-400' : 'text-yellow-400'}`}>
                {canDownload ? 'Download Unlocked!' : 'Complete Checkpoint 2 to Download'}
              </p>
              <p className="text-xs text-gray-400">
                {canDownload
                  ? 'You can now download your project'
                  : `Score: ${progress.checkpoint2Score?.toFixed(0) || 0}% (Need 70%)`}
              </p>
            </div>
          </div>

          {canDownload && (
            <div className="flex items-center gap-2">
              {!progress.certificateGenerated && (
                <button
                  onClick={generateCertificate}
                  className="px-3 py-1.5 rounded-lg bg-purple-600 text-white text-xs font-medium hover:bg-purple-700 transition-colors flex items-center gap-1"
                >
                  <Award className="w-3 h-3" />
                  Generate Certificate
                </button>
              )}
              {progress.certificateGenerated && (
                <button
                  onClick={downloadCertificate}
                  className="px-3 py-1.5 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700 transition-colors flex items-center gap-1"
                >
                  <Download className="w-3 h-3" />
                  Download Certificate
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Checkpoint Cards */}
      <div className="space-y-3">
        {checkpoints.map((checkpoint, index) => {
          const status = getCheckpointStatus(checkpoint)
          const isExpanded = activeCheckpoint === checkpoint.id && !checkpoint.locked

          return (
            <div
              key={checkpoint.id}
              className={`rounded-xl border transition-all duration-300 ${
                status === 'completed'
                  ? 'border-green-500/50 bg-green-500/5'
                  : status === 'active'
                  ? 'border-blue-500/50 bg-blue-500/5'
                  : status === 'locked'
                  ? 'border-gray-700/50 bg-gray-800/30 opacity-60'
                  : 'border-gray-700/50 bg-gray-800/30'
              }`}
            >
              {/* Checkpoint Header */}
              <button
                onClick={() => !checkpoint.locked && setActiveCheckpoint(checkpoint.id)}
                disabled={checkpoint.locked}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors rounded-t-xl disabled:cursor-not-allowed"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      status === 'completed'
                        ? 'bg-green-500/20 text-green-400'
                        : status === 'active'
                        ? 'bg-blue-500/20 text-blue-400'
                        : status === 'locked'
                        ? 'bg-gray-700/50 text-gray-500'
                        : 'bg-gray-700/50 text-gray-400'
                    }`}
                  >
                    {status === 'locked' ? (
                      <Lock className="w-5 h-5" />
                    ) : status === 'completed' ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <checkpoint.icon className="w-5 h-5" />
                    )}
                  </div>
                  <div className="text-left">
                    <div className="flex items-center gap-2">
                      <span
                        className={`font-medium ${
                          status === 'completed'
                            ? 'text-green-400'
                            : status === 'active'
                            ? 'text-blue-400'
                            : 'text-gray-400'
                        }`}
                      >
                        {checkpoint.title}
                      </span>
                      {checkpoint.id === 'checkpoint2' && progress.checkpoint2Passed && (
                        <Trophy className="w-4 h-4 text-yellow-500" />
                      )}
                    </div>
                    <p className="text-xs text-gray-500">{checkpoint.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {/* Progress indicator */}
                  <div className="text-right hidden sm:block">
                    <span
                      className={`text-sm font-medium ${
                        status === 'completed' ? 'text-green-400' : 'text-gray-400'
                      }`}
                    >
                      {Math.round(checkpoint.progress)}%
                    </span>
                    <p className="text-[10px] text-gray-500">{checkpoint.requirement}</p>
                  </div>

                  {/* Expand/collapse arrow */}
                  {!checkpoint.locked &&
                    (isExpanded ? (
                      <ChevronDown className="w-5 h-5 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-500" />
                    ))}
                </div>
              </button>

              {/* Checkpoint Content */}
              <AnimatePresence>
                {isExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="px-4 pb-4 border-t border-white/10">
                      {/* Checkpoint 1: File Understanding */}
                      {checkpoint.id === 'checkpoint1' && (
                        <div className="pt-4">
                          <FileExplanationList
                            files={flatFiles.map(f => ({
                              path: f.path,
                              content: f.content,
                              language: f.language,
                            }))}
                            explanations={explanations}
                            understoodFiles={progress.filesReviewed}
                            onMarkUnderstood={handleMarkUnderstood}
                            onFetchExplanation={handleFetchExplanation}
                            loadingFiles={loadingFiles}
                          />
                        </div>
                      )}

                      {/* Checkpoint 2: Concept Quiz */}
                      {checkpoint.id === 'checkpoint2' && (
                        <div className="pt-4">
                          <ConceptQuiz
                            projectId={projectId}
                            questions={quizQuestions}
                            onSubmit={submitQuiz}
                            previousResult={quizResult}
                            loading={quizLoading}
                            onRetry={fetchQuiz}
                          />
                        </div>
                      )}

                      {/* Checkpoint 3: Viva Preparation */}
                      {checkpoint.id === 'checkpoint3' && (
                        <div className="pt-4">
                          <VivaPreparation
                            vivaQuestionsReviewed={progress.vivaQuestionsReviewed}
                            vivaTotalQuestions={progress.vivaTotalQuestions}
                            onMarkReviewed={markVivaReviewed}
                          />
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Viva Preparation Sub-component
interface VivaPreparationProps {
  vivaQuestionsReviewed: number
  vivaTotalQuestions: number
  onMarkReviewed: (index: number) => void
}

function VivaPreparation({
  vivaQuestionsReviewed,
  vivaTotalQuestions,
  onMarkReviewed,
}: VivaPreparationProps) {
  const [currentQuestion, setCurrentQuestion] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)

  // Sample viva questions (in production, these would come from the backend)
  const sampleQuestions = [
    {
      question: 'What is the main purpose of your project?',
      answer: 'This project is designed to [describe main functionality]. It solves [problem] by [approach].',
      category: 'Project Overview',
    },
    {
      question: 'Explain the architecture of your application.',
      answer: 'The application follows a [architecture pattern] architecture. The frontend handles [responsibilities], while the backend manages [responsibilities].',
      category: 'Technical',
    },
    {
      question: 'Why did you choose this tech stack?',
      answer: 'I chose this tech stack because [reasons]. It offers [benefits] which are essential for [use case].',
      category: 'Design Decisions',
    },
    {
      question: 'How does authentication work in your project?',
      answer: 'Authentication is implemented using [method]. When a user logs in, [process]. This ensures [security benefits].',
      category: 'Implementation',
    },
    {
      question: 'What challenges did you face during development?',
      answer: 'The main challenges included [challenge 1] and [challenge 2]. I overcame them by [solutions].',
      category: 'Practical',
    },
  ]

  const progress = (vivaQuestionsReviewed / vivaTotalQuestions) * 100

  return (
    <div className="space-y-4">
      {/* Progress */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-gray-400">
          {vivaQuestionsReviewed} / {vivaTotalQuestions} reviewed
        </span>
        <span className="text-sm font-medium text-white">{Math.round(progress)}%</span>
      </div>
      <div className="h-2 rounded-full bg-gray-800 overflow-hidden">
        <motion.div
          className="h-full bg-gradient-to-r from-purple-500 to-pink-500"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>

      {/* Current Question */}
      <div className="p-4 rounded-lg bg-gray-900/50 border border-gray-700/50">
        <div className="flex items-center gap-2 mb-2">
          <span className="px-2 py-0.5 text-xs rounded bg-purple-500/20 text-purple-400 border border-purple-500/30">
            {sampleQuestions[currentQuestion % sampleQuestions.length].category}
          </span>
          <span className="text-xs text-gray-500">
            Question {currentQuestion + 1}
          </span>
        </div>

        <h4 className="text-white font-medium mb-4">
          {sampleQuestions[currentQuestion % sampleQuestions.length].question}
        </h4>

        <AnimatePresence mode="wait">
          {showAnswer ? (
            <motion.div
              key="answer"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-3 rounded-lg bg-green-500/10 border border-green-500/30"
            >
              <p className="text-sm text-gray-300">
                {sampleQuestions[currentQuestion % sampleQuestions.length].answer}
              </p>
            </motion.div>
          ) : (
            <motion.button
              key="show"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowAnswer(true)}
              className="w-full py-2 rounded-lg border border-dashed border-gray-600 text-gray-400 text-sm hover:border-blue-500 hover:text-blue-400 transition-colors"
            >
              Click to reveal answer
            </motion.button>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={() => {
            setCurrentQuestion(prev => Math.max(0, prev - 1))
            setShowAnswer(false)
          }}
          disabled={currentQuestion === 0}
          className="px-4 py-2 rounded-lg bg-gray-800 border border-gray-700 text-white text-sm hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          Previous
        </button>

        {showAnswer && (
          <button
            onClick={() => {
              onMarkReviewed(currentQuestion)
              if (currentQuestion < vivaTotalQuestions - 1) {
                setCurrentQuestion(prev => prev + 1)
              }
              setShowAnswer(false)
            }}
            className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm hover:bg-green-700 transition-colors flex items-center gap-2"
          >
            <CheckCircle2 className="w-4 h-4" />
            Mark Reviewed & Next
          </button>
        )}

        {!showAnswer && (
          <button
            onClick={() => {
              setCurrentQuestion(prev => prev + 1)
              setShowAnswer(false)
            }}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm hover:bg-blue-700 transition-colors"
          >
            Skip
          </button>
        )}
      </div>

      {/* Checkpoint complete indicator */}
      {vivaQuestionsReviewed >= vivaTotalQuestions * 0.8 && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
          <CheckCircle2 className="w-5 h-5 text-green-500" />
          <span className="text-sm text-green-400">
            Checkpoint Complete! You've reviewed enough viva questions.
          </span>
        </div>
      )}
    </div>
  )
}
