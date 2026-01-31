'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  ClipboardList,
  Plus,
  Search,
  Calendar,
  Clock,
  Users,
  BarChart3,
  Eye,
  Edit,
  Trash2,
  Copy,
  Play,
  Pause,
  Square,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  X,
  Settings,
  Code,
  FileText,
  Target,
  Award,
  TrendingUp,
  AlertTriangle,
  Monitor,
  Wifi,
  WifiOff,
  RefreshCw,
  Download,
  Upload,
  Database,
  Cpu,
  Zap,
  Shield,
  Ban,
  Activity,
  Timer,
  Layers,
  Filter,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Loader2
} from 'lucide-react'
import { useToast } from '@/components/ui/toast'
import { useFacultyTests, Test, Question, LiveStudent, TestAlert, MonitorData } from '@/hooks/useFacultyTests'

export default function TestsPage() {
  const toast = useToast()
  const {
    tests,
    setTests,
    questions,
    loading,
    fetchTests,
    fetchQuestions,
    createTest,
    updateTest,
    deleteTest,
    duplicateTest,
    scheduleTest,
    startTest,
    endTest,
    getMonitorData,
    studentAction,
    getResults,
    evaluateTest,
    exportResults,
    addQuestionToTest
  } = useFacultyTests()

  const [activeView, setActiveView] = useState<'tests' | 'question-bank' | 'live-monitor' | 'evaluation'>('tests')
  const [showCreateWizard, setShowCreateWizard] = useState(false)
  const [wizardStep, setWizardStep] = useState(1)
  const [selectedTest, setSelectedTest] = useState<Test | null>(null)
  const [showEvaluationPanel, setShowEvaluationPanel] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)

  // Action modals
  const [showEditModal, setShowEditModal] = useState(false)
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [showResultsModal, setShowResultsModal] = useState(false)
  const [showStudentDetailModal, setShowStudentDetailModal] = useState(false)
  const [showQuestionPreviewModal, setShowQuestionPreviewModal] = useState(false)
  const [selectedStudent, setSelectedStudent] = useState<LiveStudent | null>(null)
  const [selectedQuestion, setSelectedQuestion] = useState<Question | null>(null)

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState<{
    show: boolean
    title: string
    message: string
    confirmText: string
    confirmColor: string
    onConfirm: () => void
  }>({ show: false, title: '', message: '', confirmText: 'Confirm', confirmColor: 'green', onConfirm: () => {} })

  // Selected live test for monitoring
  const [selectedLiveTestId, setSelectedLiveTestId] = useState<string | null>(null)

  // Live monitoring data
  const [monitorData, setMonitorData] = useState<MonitorData | null>(null)
  const [liveStudents, setLiveStudents] = useState<LiveStudent[]>([])
  const [liveAlerts, setLiveAlerts] = useState<TestAlert[]>([])

  // Edit form state
  const [editForm, setEditForm] = useState({
    title: '',
    lab: '',
    duration_minutes: 90,
    max_marks: 100,
    ai_control: 'blocked' as 'blocked' | 'limited' | 'hints_only'
  })

  // Schedule form state
  const [scheduleForm, setScheduleForm] = useState({
    date: '',
    time: '',
    assignTo: ''
  })

  // Derived state - Get all live tests
  const liveTests = tests.filter(t => t.status === 'live')
  const selectedLiveTest = liveTests.find(t => t.id === selectedLiveTestId) || liveTests[0] || null

  // Fetch monitor data for live test
  const refreshMonitorData = useCallback(async () => {
    if (selectedLiveTest) {
      const data = await getMonitorData(selectedLiveTest.id)
      if (data) {
        setMonitorData(data)
        setLiveStudents(data.students)
        setLiveAlerts(data.alerts)
      }
    }
  }, [selectedLiveTest, getMonitorData])

  // Poll for live updates when monitoring
  useEffect(() => {
    if (activeView === 'live-monitor' && selectedLiveTest) {
      refreshMonitorData()
      const interval = setInterval(refreshMonitorData, 5000) // Poll every 5 seconds
      return () => clearInterval(interval)
    }
  }, [activeView, selectedLiveTest, refreshMonitorData])

  // ==================== Action Handlers ====================

  // Edit Test
  const handleEditTest = (test: Test) => {
    setSelectedTest(test)
    setEditForm({
      title: test.title,
      lab: test.lab,
      duration_minutes: test.duration_minutes,
      max_marks: test.max_marks,
      ai_control: test.ai_control
    })
    setShowEditModal(true)
  }

  const handleSaveEdit = async () => {
    if (!selectedTest) return
    setActionLoading(true)
    try {
      await updateTest(selectedTest.id, {
        title: editForm.title,
        lab: editForm.lab,
        duration_minutes: editForm.duration_minutes,
        max_marks: editForm.max_marks,
        ai_control: editForm.ai_control
      })
      toast.success('Test Updated', 'Test details saved successfully')
      setShowEditModal(false)
      setSelectedTest(null)
    } catch (err) {
      toast.error('Error', 'Failed to update test')
    } finally {
      setActionLoading(false)
    }
  }

  // Schedule Test
  const handleScheduleTest = (test: Test) => {
    setSelectedTest(test)
    setScheduleForm({ date: '', time: '', assignTo: 'CSE-3A' })
    setShowScheduleModal(true)
  }

  const handleSaveSchedule = async () => {
    if (!selectedTest || !scheduleForm.date || !scheduleForm.time) return
    setActionLoading(true)
    try {
      const scheduledAt = `${scheduleForm.date}T${scheduleForm.time}:00`
      await scheduleTest(selectedTest.id, scheduledAt, [scheduleForm.assignTo])
      toast.success('Test Scheduled', `Scheduled for ${scheduleForm.date} at ${scheduleForm.time}`)
      setShowScheduleModal(false)
      setSelectedTest(null)
    } catch (err) {
      toast.error('Error', 'Failed to schedule test')
    } finally {
      setActionLoading(false)
    }
  }

  // Duplicate Test
  const handleDuplicateTest = async (test: Test) => {
    setActionLoading(true)
    try {
      await duplicateTest(test.id)
      toast.success('Test Duplicated', `Created a copy of "${test.title}"`)
    } catch (err) {
      toast.error('Error', 'Failed to duplicate test')
    } finally {
      setActionLoading(false)
    }
  }

  // Delete Test
  const handleDeleteTest = (test: Test) => {
    setConfirmModal({
      show: true,
      title: 'Delete Test?',
      message: `Are you sure you want to delete "${test.title}"? This action cannot be undone.`,
      confirmText: 'Delete',
      confirmColor: 'red',
      onConfirm: async () => {
        setActionLoading(true)
        try {
          await deleteTest(test.id)
          setConfirmModal(prev => ({ ...prev, show: false }))
          toast.success('Test Deleted', `"${test.title}" has been deleted`)
        } catch (err) {
          toast.error('Error', 'Failed to delete test')
        } finally {
          setActionLoading(false)
        }
      }
    })
  }

  // Legacy handleSaveSchedule compatibility
  const handleSaveScheduleLegacy = () => {
    if (!selectedTest || !scheduleForm.date || !scheduleForm.time) return
    const scheduledAt = `${scheduleForm.date} ${scheduleForm.time}`
    setTests(tests.map(t =>
      t.id === selectedTest.id
        ? { ...t, status: 'scheduled' as const, scheduled_at: scheduledAt }
        : t
    ))
    setShowScheduleModal(false)
    setSelectedTest(null)
  }

  // Start Test (scheduled -> live)
  const handleStartTest = (test: Test) => {
    setConfirmModal({
      show: true,
      title: 'Start Test Now?',
      message: `Start "${test.title}" now? Students will be able to begin the test immediately.`,
      confirmText: 'Start Test',
      confirmColor: 'green',
      onConfirm: async () => {
        setActionLoading(true)
        try {
          await startTest(test.id)
          setActiveView('live-monitor')
          setSelectedLiveTestId(test.id)
          setConfirmModal(prev => ({ ...prev, show: false }))
          toast.success('Test Started', `"${test.title}" is now live. Students can begin.`)
        } catch (err) {
          toast.error('Error', 'Failed to start test')
        } finally {
          setActionLoading(false)
        }
      }
    })
  }

  // End Test (live -> evaluating)
  const handleEndTest = (test: Test) => {
    setConfirmModal({
      show: true,
      title: 'End Test?',
      message: `End "${test.title}"? All ongoing submissions will be auto-submitted.`,
      confirmText: 'End Test',
      confirmColor: 'red',
      onConfirm: async () => {
        setActionLoading(true)
        try {
          const result = await endTest(test.id)
          setConfirmModal(prev => ({ ...prev, show: false }))
          toast.success('Test Ended', `"${test.title}" has been ended. ${result.force_submitted || 0} submissions auto-submitted.`)
        } catch (err) {
          toast.error('Error', 'Failed to end test')
        } finally {
          setActionLoading(false)
        }
      }
    })
  }

  // View Results
  const handleViewResults = (test: Test) => {
    setSelectedTest(test)
    setShowResultsModal(true)
  }

  // Export Results
  const handleExportResults = async (test: Test, format: 'pdf' | 'excel' | 'naac') => {
    try {
      const result = await exportResults(test.id, format === 'naac' ? 'pdf' : format)
      const filename = `${test.title.replace(/\s+/g, '_')}_results.${format === 'excel' ? 'xlsx' : format}`
      toast.success('Export Started', `Downloading ${filename}...`)
      console.log('Export data:', result)
    } catch (err) {
      toast.error('Error', 'Failed to export results')
    }
  }

  // Copy/Duplicate Test
  const handleCopyTest = async (test: Test) => {
    setActionLoading(true)
    try {
      await duplicateTest(test.id)
      toast.success('Test Duplicated', `Created a copy of "${test.title}"`)
    } catch (err) {
      toast.error('Error', 'Failed to duplicate test')
    } finally {
      setActionLoading(false)
    }
  }

  // Reschedule Test
  const handleRescheduleTest = (test: Test) => {
    setSelectedTest(test)
    const [date, time] = (test.scheduled_at || '').split(' ')
    setScheduleForm({ date: date || '', time: time || '', assignTo: 'CSE-3A' })
    setShowScheduleModal(true)
  }

  // Evaluate Test
  const handleEvaluateTest = (test: Test) => {
    setSelectedTest(test)
    setShowEvaluationPanel(true)
  }

  // Complete Evaluation
  const handleCompleteEvaluation = () => {
    if (!selectedTest) return
    setTests(tests.map(t =>
      t.id === selectedTest.id
        ? { ...t, status: 'completed' as const, avg_score: Math.floor(Math.random() * 30) + 60 }
        : t
    ))
    setShowEvaluationPanel(false)
    setSelectedTest(null)
  }

  // ==================== Live Monitor Actions ====================

  // View Student Detail
  const handleViewStudent = (student: LiveStudent) => {
    setSelectedStudent(student)
    setShowStudentDetailModal(true)
  }

  // Warn Student
  const handleWarnStudent = (student: LiveStudent) => {
    setConfirmModal({
      show: true,
      title: 'Send Warning?',
      message: `Send warning to ${student.name}? They will receive a notification.`,
      confirmText: 'Send Warning',
      confirmColor: 'orange',
      onConfirm: async () => {
        if (!selectedLiveTest) return
        setActionLoading(true)
        try {
          await studentAction(selectedLiveTest.id, student.id, 'warn', 'Warning from faculty: Please focus on your test.')
          setConfirmModal(prev => ({ ...prev, show: false }))
          toast.warning('Warning Sent', `Warning notification sent to ${student.name}`)
          refreshMonitorData()
        } catch (err) {
          toast.error('Error', 'Failed to send warning')
        } finally {
          setActionLoading(false)
        }
      }
    })
  }

  // End Student's Test
  const handleEndStudentTest = (student: LiveStudent) => {
    setConfirmModal({
      show: true,
      title: 'Force Submit?',
      message: `Force submit ${student.name}'s test? Their current work will be saved and submitted.`,
      confirmText: 'Force Submit',
      confirmColor: 'red',
      onConfirm: async () => {
        if (!selectedLiveTest) return
        setActionLoading(true)
        try {
          await studentAction(selectedLiveTest.id, student.id, 'force_submit')
          setConfirmModal(prev => ({ ...prev, show: false }))
          toast.success('Test Submitted', `${student.name}'s test has been force submitted.`)
          refreshMonitorData()
        } catch (err) {
          toast.error('Error', 'Failed to force submit')
        } finally {
          setActionLoading(false)
        }
      }
    })
  }

  // ==================== Question Bank Actions ====================

  // Preview Question
  const handlePreviewQuestion = (question: Question) => {
    setSelectedQuestion(question)
    setShowQuestionPreviewModal(true)
  }

  // Edit Question
  const handleEditQuestion = (question: Question) => {
    setSelectedQuestion(question)
    setShowQuestionPreviewModal(true)
  }

  // Add Question to Test
  const handleAddQuestionToTest = async (question: Question) => {
    if (!selectedTest) {
      toast.info('Select Test', 'Create or select a test first to add questions.')
      return
    }
    try {
      await addQuestionToTest(selectedTest.id, {
        title: question.title,
        question_type: question.question_type || 'coding',
        difficulty: question.difficulty || 'medium',
        marks: question.marks,
        time_estimate_minutes: question.time_estimate,
        topic: question.topic
      })
      toast.success('Question Added', `"${question.title}" added to "${selectedTest.title}".`)
    } catch (err) {
      toast.error('Error', 'Failed to add question to test')
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'live': return 'bg-green-100 text-green-700 border-green-200'
      case 'scheduled': return 'bg-blue-100 text-blue-700 border-blue-200'
      case 'completed': return 'bg-gray-100 text-gray-700 border-gray-200'
      case 'evaluating': return 'bg-purple-100 text-purple-700 border-purple-200'
      case 'draft': return 'bg-yellow-100 text-yellow-700 border-yellow-200'
      default: return 'bg-gray-100 text-gray-700 border-gray-200'
    }
  }

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-green-100 text-green-700'
      case 'medium': return 'bg-yellow-100 text-yellow-700'
      case 'hard': return 'bg-red-100 text-red-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  const getStudentStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500'
      case 'idle': return 'bg-yellow-500'
      case 'suspicious': return 'bg-red-500'
      case 'submitted': return 'bg-blue-500'
      default: return 'bg-gray-500'
    }
  }

  // Show loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)] bg-gray-900">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading tests...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold text-white">Lab Practice & Tests</h1>
            <p className="text-sm text-gray-400">Create tests, manage questions, monitor live sessions</p>
          </div>
          <button
            onClick={() => {
              setShowCreateWizard(true)
              setWizardStep(1)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Create Test
          </button>
          <button
            onClick={() => fetchTests()}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>

        {/* View Tabs */}
        <div className="flex gap-1">
          {[
            { id: 'tests', label: 'All Tests', icon: ClipboardList },
            { id: 'question-bank', label: 'Question Bank', icon: Database },
            { id: 'live-monitor', label: 'Live Monitor', icon: Monitor, badge: tests.filter(t => t.status === 'live').length },
            { id: 'evaluation', label: 'Evaluation', icon: Target },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveView(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                activeView === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:bg-gray-700 hover:text-white'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
              {tab.badge && tab.badge > 0 && (
                <span className="ml-1 px-1.5 py-0.5 text-xs bg-green-500 text-white rounded-full animate-pulse">
                  {tab.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto scrollbar-hide p-6 bg-gray-900">
        {activeView === 'tests' && (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            {/* Table Header */}
            <div className="bg-gray-800 border-b border-gray-600">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[30%]">Test Name</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[12%]">Lab</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Questions</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Duration</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Status</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Participants</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[18%]">Actions</th>
                  </tr>
                </thead>
              </table>
            </div>
            {/* Table Body */}
            <div className="max-h-[calc(100vh-200px)] overflow-y-auto scrollbar-hide">
              <table className="w-full">
                <tbody className="divide-y divide-gray-700">
                  {tests.map((test) => (
                    <tr key={test.id} className="hover:bg-gray-700/50">
                      <td className="px-4 py-3 w-[30%]">
                        <div>
                          <p className="text-sm font-medium text-white">{test.title}</p>
                          {test.scheduled_at && test.status === 'scheduled' && (
                            <p className="text-xs text-blue-400">{test.scheduled_at}</p>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 w-[12%]">
                        <span className="text-sm text-gray-300">{test.lab}</span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className="text-sm text-gray-300">{test.questions_count}</span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className="text-sm text-gray-300">{test.duration_minutes} min</span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded ${getStatusColor(test.status)}`}>
                          {test.status === 'live' && <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />}
                          {test.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        {test.participants ? (
                          <div>
                            <span className="text-sm text-gray-300">{test.participants}</span>
                            {test.avg_score !== undefined && (
                              <span className={`text-xs ml-2 ${test.avg_score >= 70 ? 'text-green-400' : 'text-yellow-400'}`}>
                                ({test.avg_score}%)
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-sm text-gray-500">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 w-[18%]">
                        <div className="flex items-center gap-2">
                          {test.status === 'draft' && (
                            <>
                              <button
                                onClick={() => handleEditTest(test)}
                                className="text-xs text-blue-400 hover:text-blue-300"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleScheduleTest(test)}
                                className="text-xs text-green-400 hover:text-green-300"
                              >
                                Schedule
                              </button>
                            </>
                          )}
                          {test.status === 'scheduled' && (
                            <>
                              <button
                                onClick={() => handleStartTest(test)}
                                className="text-xs text-green-400 hover:text-green-300"
                              >
                                Start
                              </button>
                              <button
                                onClick={() => handleRescheduleTest(test)}
                                className="text-xs text-gray-400 hover:text-gray-300"
                              >
                                Reschedule
                              </button>
                            </>
                          )}
                          {test.status === 'live' && (
                            <>
                              <button
                                onClick={() => setActiveView('live-monitor')}
                                className="text-xs text-green-400 hover:text-green-300"
                              >
                                Monitor
                              </button>
                              <button
                                onClick={() => handleEndTest(test)}
                                className="text-xs text-red-400 hover:text-red-300"
                              >
                                End
                              </button>
                            </>
                          )}
                          {test.status === 'evaluating' && (
                            <button
                              onClick={() => handleEvaluateTest(test)}
                              className="text-xs text-purple-400 hover:text-purple-300"
                            >
                              Evaluate
                            </button>
                          )}
                          {test.status === 'completed' && (
                            <>
                              <button
                                onClick={() => handleViewResults(test)}
                                className="text-xs text-blue-400 hover:text-blue-300"
                              >
                                Results
                              </button>
                              <button
                                onClick={() => handleExportResults(test, 'excel')}
                                className="text-xs text-gray-400 hover:text-gray-300"
                              >
                                Export
                              </button>
                            </>
                          )}
                          <button
                            onClick={() => handleCopyTest(test)}
                            className="text-xs text-gray-400 hover:text-gray-300"
                            title="Duplicate test"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeView === 'question-bank' && (
          <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            {/* Filters */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search questions..."
                    className="pl-10 pr-4 py-1.5 text-sm border border-gray-600 rounded-lg w-64 bg-gray-700 text-white focus:ring-2 focus:ring-blue-500 placeholder-gray-400"
                  />
                </div>
                <select className="text-sm border border-gray-600 rounded-lg px-3 py-1.5 bg-gray-700 text-white">
                  <option value="">All Types</option>
                  <option value="coding">Coding</option>
                  <option value="sql">SQL</option>
                  <option value="ml">ML</option>
                  <option value="analytics">Analytics</option>
                </select>
                <select className="text-sm border border-gray-600 rounded-lg px-3 py-1.5 bg-gray-700 text-white">
                  <option value="">All Difficulty</option>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
              <button className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
                <Plus className="w-4 h-4" />
                Add Question
              </button>
            </div>

            {/* Questions Table */}
            <div className="border-b border-gray-600">
              <table className="w-full">
                <thead className="bg-gray-800">
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[35%]">Question</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Type</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Difficulty</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Marks</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Time</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Tests</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[15%]">Actions</th>
                  </tr>
                </thead>
              </table>
            </div>
            <div className="max-h-[calc(100vh-280px)] overflow-y-auto scrollbar-hide">
              <table className="w-full">
                <tbody className="divide-y divide-gray-700">
                  {questions.map((q) => (
                    <tr key={q.id} className="hover:bg-gray-700/50">
                      <td className="px-4 py-3 w-[35%]">
                        <div>
                          <p className="text-sm font-medium text-white">{q.title}</p>
                          <p className="text-xs text-gray-500">{q.topic} | Used {q.usage_count}x</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          (q.type || q.question_type) === 'coding' ? 'bg-purple-500/20 text-purple-400' :
                          (q.type || q.question_type) === 'sql' ? 'bg-blue-500/20 text-blue-400' :
                          (q.type || q.question_type) === 'ml' ? 'bg-green-500/20 text-green-400' :
                          'bg-orange-500/20 text-orange-400'
                        }`}>
                          {(q.type || q.question_type || 'N/A').toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className={`text-xs px-2 py-0.5 rounded ${getDifficultyColor(q.difficulty)}`}>
                          {q.difficulty}
                        </span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className="text-sm text-gray-300">{q.marks}</span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className="text-sm text-gray-300">{q.time_estimate} min</span>
                      </td>
                      <td className="px-4 py-3 w-[10%]">
                        <span className="text-sm text-gray-300">{q.test_cases}</span>
                      </td>
                      <td className="px-4 py-3 w-[15%]">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => handlePreviewQuestion(q)}
                            className="text-xs text-blue-400 hover:text-blue-300"
                          >
                            Preview
                          </button>
                          <button
                            onClick={() => handleEditQuestion(q)}
                            className="text-xs text-gray-400 hover:text-gray-300"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleAddQuestionToTest(q)}
                            className="text-xs text-green-400 hover:text-green-300"
                          >
                            Add
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeView === 'live-monitor' && (
          <div className="space-y-4">
            {/* No Live Tests Message */}
            {liveTests.length === 0 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-12 text-center">
                <Monitor className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-white mb-2">No Live Tests</h3>
                <p className="text-gray-400 text-sm mb-4">Start a scheduled test to begin monitoring students.</p>
                <button
                  onClick={() => setActiveView('tests')}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
                >
                  View All Tests
                </button>
              </div>
            )}

            {/* Multiple Live Tests Selector */}
            {liveTests.length > 1 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-3">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-400">Live Tests ({liveTests.length}):</span>
                  <div className="flex flex-wrap gap-2">
                    {liveTests.map(test => (
                      <button
                        key={test.id}
                        onClick={() => setSelectedLiveTestId(test.id)}
                        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                          selectedLiveTest?.id === test.id
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        }`}
                      >
                        <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                        {test.title}
                        <span className="text-xs opacity-70">({test.participants || 0})</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Live Test Info Bar */}
            {selectedLiveTest && (
            <>
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-2">
                    <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-sm font-medium text-white">{selectedLiveTest.title}</span>
                  </span>
                  <span className="text-xs text-gray-400">{selectedLiveTest.lab} | Started {selectedLiveTest.scheduled_at?.split(' ')[1] || '10:00 AM'}</span>
                </div>
                <div className="flex items-center gap-6 text-sm">
                  <span className="text-green-400">Active: {liveStudents.filter(s => s.status === 'active').length}</span>
                  <span className="text-yellow-400">Idle: {liveStudents.filter(s => s.status === 'idle').length}</span>
                  <span className="text-red-400">Suspicious: {liveStudents.filter(s => s.status === 'suspicious').length}</span>
                  <span className="text-blue-400">Submitted: {liveStudents.filter(s => s.status === 'submitted').length}</span>
                  <span className="text-green-400 font-medium">Duration: {selectedLiveTest.duration_minutes} min</span>
                  <button
                    onClick={() => handleEndTest(selectedLiveTest)}
                    className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                  >
                    End Test
                  </button>
                </div>
              </div>

              {/* Filters */}
              <div className="flex items-center justify-between px-4 py-2 bg-gray-800/50">
                <span className="text-xs text-gray-400">Live Student Activity</span>
                <div className="flex items-center gap-2">
                  <button className="p-1.5 hover:bg-gray-700 rounded text-gray-400">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                  <select className="text-xs border border-gray-600 rounded px-2 py-1 bg-gray-700 text-white">
                    <option value="">All Students</option>
                    <option value="active">Active</option>
                    <option value="idle">Idle</option>
                    <option value="suspicious">Suspicious</option>
                  </select>
                </div>
              </div>

              {/* Student Table */}
              <div className="border-b border-gray-600">
                <table className="w-full">
                  <thead className="bg-gray-800">
                    <tr>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Student</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Status</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Progress</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Time</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Tab Switches</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">AI Usage</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Activity</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Actions</th>
                    </tr>
                  </thead>
                </table>
              </div>
              <div className="max-h-[calc(100vh-350px)] overflow-y-auto scrollbar-hide">
                <table className="w-full">
                  <tbody className="divide-y divide-gray-700">
                    {liveStudents.map((student) => (
                      <tr key={student.id} className={`hover:bg-gray-700/50 ${student.status === 'suspicious' ? 'bg-red-500/10' : ''}`}>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium text-white">{student.name}</p>
                            <p className="text-xs text-gray-400">{student.roll_number}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="flex items-center gap-2">
                            <span className={`w-2 h-2 rounded-full ${getStudentStatusColor(student.status)}`} />
                            <span className="text-sm text-gray-300 capitalize">{student.status}</span>
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-gray-700 rounded-full">
                              <div className="h-1.5 bg-blue-500 rounded-full" style={{ width: `${student.progress}%` }} />
                            </div>
                            <span className="text-xs text-gray-400">{student.progress}%</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-300">{student.time_spent} min</td>
                        <td className="px-4 py-3">
                          <span className={`text-sm ${student.tab_switches > 5 ? 'text-red-400 font-medium' : 'text-gray-300'}`}>
                            {student.tab_switches}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`text-sm ${student.ai_usage > 20 ? 'text-red-400 font-medium' : 'text-gray-300'}`}>
                            {student.ai_usage}%
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400">{student.last_activity}</td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-1">
                            <button
                              onClick={() => handleViewStudent(student)}
                              className="text-xs text-blue-400 hover:text-blue-300"
                            >
                              View
                            </button>
                            <button
                              onClick={() => handleWarnStudent(student)}
                              className="text-xs text-orange-400 hover:text-orange-300"
                            >
                              Warn
                            </button>
                            <button
                              onClick={() => handleEndStudentTest(student)}
                              className="text-xs text-red-400 hover:text-red-300"
                              disabled={student.status === 'submitted'}
                            >
                              End
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Alerts Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div className="px-4 py-2 border-b border-gray-700 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-sm font-medium text-white">Active Alerts ({liveStudents.filter(s => s.status === 'suspicious' || s.tab_switches > 5 || s.ai_usage > 20).length})</span>
              </div>
              <table className="w-full">
                <tbody className="divide-y divide-gray-700">
                  {[
                    { studentId: '4', student: 'Sneha Reddy', roll: '21CS004', message: 'High tab switch count (8 switches)', time: '2 min ago', severity: 'high' },
                    { studentId: '3', student: 'Amit Patel', roll: '21CS003', message: 'Idle for more than 5 minutes', time: '5 min ago', severity: 'medium' },
                    { studentId: '4', student: 'Sneha Reddy', roll: '21CS004', message: 'AI usage above 30%', time: '8 min ago', severity: 'high' },
                  ].map((alert, i) => (
                    <tr key={i} className={`${alert.severity === 'high' ? 'bg-red-500/5' : 'bg-yellow-500/5'}`}>
                      <td className="px-4 py-2 w-[20%]">
                        <p className="text-sm text-white">{alert.student}</p>
                        <p className="text-xs text-gray-500">{alert.roll}</p>
                      </td>
                      <td className="px-4 py-2 w-[50%]">
                        <span className={`text-sm ${alert.severity === 'high' ? 'text-red-400' : 'text-yellow-400'}`}>
                          {alert.message}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs text-gray-500 w-[15%]">{alert.time}</td>
                      <td className="px-4 py-2 w-[15%]">
                        <button
                          onClick={() => {
                            const student = liveStudents.find(s => s.id === alert.studentId)
                            if (student) handleViewStudent(student)
                          }}
                          className="text-xs text-blue-400 hover:text-blue-300"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </>
            )}
          </div>
        )}

        {activeView === 'evaluation' && (
          <div className="space-y-4">
            {/* Pending Evaluations Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-700 flex items-center justify-between">
                <span className="text-sm font-medium text-white">Pending Evaluations</span>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => {
                      const completedTests = tests.filter(t => t.status === 'completed' || t.status === 'evaluating')
                      if (completedTests.length > 0) handleExportResults(completedTests[0], 'pdf')
                    }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    PDF
                  </button>
                  <button
                    onClick={() => {
                      const completedTests = tests.filter(t => t.status === 'completed' || t.status === 'evaluating')
                      if (completedTests.length > 0) handleExportResults(completedTests[0], 'excel')
                    }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Excel
                  </button>
                  <button
                    onClick={() => {
                      const completedTests = tests.filter(t => t.status === 'completed' || t.status === 'evaluating')
                      if (completedTests.length > 0) handleExportResults(completedTests[0], 'naac')
                    }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    NAAC
                  </button>
                </div>
              </div>
              <div className="border-b border-gray-600">
                <table className="w-full">
                  <thead className="bg-gray-800">
                    <tr>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[35%]">Test Name</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[15%]">Lab</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[15%]">Submissions</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[15%]">Progress</th>
                      <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[20%]">Actions</th>
                    </tr>
                  </thead>
                </table>
              </div>
              <div className="max-h-[300px] overflow-y-auto scrollbar-hide">
                <table className="w-full">
                  <tbody className="divide-y divide-gray-700">
                    {tests.filter(t => t.status === 'evaluating' || t.status === 'completed').map((test) => (
                      <tr key={test.id} className="hover:bg-gray-700/50">
                        <td className="px-4 py-3 w-[35%]">
                          <span className="text-sm font-medium text-white">{test.title}</span>
                        </td>
                        <td className="px-4 py-3 w-[15%]">
                          <span className="text-sm text-gray-300">{test.lab}</span>
                        </td>
                        <td className="px-4 py-3 w-[15%]">
                          <span className="text-sm text-gray-300">{test.participants}</span>
                        </td>
                        <td className="px-4 py-3 w-[15%]">
                          {test.status === 'evaluating' ? (
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-gray-700 rounded-full">
                                <div className="w-1/3 h-1.5 bg-purple-500 rounded-full" />
                              </div>
                              <span className="text-xs text-gray-400">33%</span>
                            </div>
                          ) : (
                            <span className="text-xs text-green-400">Done</span>
                          )}
                        </td>
                        <td className="px-4 py-3 w-[20%]">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => test.status === 'evaluating' ? handleEvaluateTest(test) : handleViewResults(test)}
                              className="text-xs text-blue-400 hover:text-blue-300"
                            >
                              {test.status === 'evaluating' ? 'Continue' : 'Review'}
                            </button>
                            <button
                              onClick={() => handleExportResults(test, 'excel')}
                              className="text-xs text-gray-400 hover:text-gray-300"
                            >
                              Export
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Settings Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-700">
                <span className="text-sm font-medium text-white">Evaluation Settings</span>
              </div>
              <table className="w-full">
                <tbody className="divide-y divide-gray-700">
                  <tr className="hover:bg-gray-700/50">
                    <td className="px-4 py-2 text-sm text-gray-300 w-[40%]">Output Comparison</td>
                    <td className="px-4 py-2 text-sm text-green-400 w-[20%]">Enabled</td>
                    <td className="px-4 py-2 text-sm text-gray-300 w-[25%]">Auto Evaluation Weight</td>
                    <td className="px-4 py-2 text-sm text-blue-400 w-[15%]">60%</td>
                  </tr>
                  <tr className="hover:bg-gray-700/50">
                    <td className="px-4 py-2 text-sm text-gray-300">Test Case Validation</td>
                    <td className="px-4 py-2 text-sm text-green-400">Enabled</td>
                    <td className="px-4 py-2 text-sm text-gray-300">Manual Evaluation Weight</td>
                    <td className="px-4 py-2 text-sm text-blue-400">30%</td>
                  </tr>
                  <tr className="hover:bg-gray-700/50">
                    <td className="px-4 py-2 text-sm text-gray-300">Performance Metrics</td>
                    <td className="px-4 py-2 text-sm text-green-400">Enabled</td>
                    <td className="px-4 py-2 text-sm text-gray-300">Viva Marks</td>
                    <td className="px-4 py-2 text-sm text-blue-400">10%</td>
                  </tr>
                  <tr className="hover:bg-gray-700/50">
                    <td className="px-4 py-2 text-sm text-gray-300">Code Quality Checks</td>
                    <td className="px-4 py-2 text-sm text-yellow-400">Basic</td>
                    <td className="px-4 py-2 text-sm text-gray-500" colSpan={2}>Formula: Auto (60%) + Manual (30%) + Viva (10%)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Create Test Wizard Modal */}
      {/* Edit Test Modal */}
      {showEditModal && selectedTest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-lg mx-4 border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white">Edit Test</h3>
              <button onClick={() => setShowEditModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Test Title</label>
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Lab/Subject</label>
                <select
                  value={editForm.lab}
                  onChange={(e) => setEditForm({ ...editForm, lab: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="DS Lab">DS Lab</option>
                  <option value="DBMS Lab">DBMS Lab</option>
                  <option value="Python Lab">Python Lab</option>
                  <option value="ML Lab">ML Lab</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Duration (min)</label>
                  <input
                    type="number"
                    value={editForm.duration_minutes}
                    onChange={(e) => setEditForm({ ...editForm, duration_minutes: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Max Marks</label>
                  <input
                    type="number"
                    value={editForm.max_marks}
                    onChange={(e) => setEditForm({ ...editForm, max_marks: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">AI Control</label>
                <select
                  value={editForm.ai_control}
                  onChange={(e) => setEditForm({ ...editForm, ai_control: e.target.value as any })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="blocked">AI Fully Blocked</option>
                  <option value="limited">AI Limited</option>
                  <option value="hints_only">AI Hints Only</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-gray-700">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Test Modal */}
      {showScheduleModal && selectedTest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-lg mx-4 border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white">Schedule Test</h3>
              <button onClick={() => setShowScheduleModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div className="bg-gray-700/50 rounded-lg p-3">
                <p className="text-sm text-white font-medium">{selectedTest.title}</p>
                <p className="text-xs text-gray-400">{selectedTest.lab} | {selectedTest.duration_minutes} min | {selectedTest.max_marks} marks</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Date</label>
                  <input
                    type="date"
                    value={scheduleForm.date}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, date: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Time</label>
                  <input
                    type="time"
                    value={scheduleForm.time}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, time: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Assign To</label>
                <select
                  value={scheduleForm.assignTo}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, assignTo: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"
                >
                  <option value="CSE-3A">CSE-3A (65 students)</option>
                  <option value="CSE-3B">CSE-3B (68 students)</option>
                  <option value="All">All Sections (133 students)</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-gray-700">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveSchedule}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Schedule Test
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Results Modal */}
      {showResultsModal && selectedTest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div>
                <h3 className="text-lg font-semibold text-white">{selectedTest.title} - Results</h3>
                <p className="text-xs text-gray-400">{selectedTest.participants} students | Avg Score: {selectedTest.avg_score}%</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleExportResults(selectedTest, 'pdf')}
                  className="px-3 py-1.5 text-xs bg-red-600/20 text-red-400 rounded hover:bg-red-600/30"
                >
                  PDF
                </button>
                <button
                  onClick={() => handleExportResults(selectedTest, 'excel')}
                  className="px-3 py-1.5 text-xs bg-green-600/20 text-green-400 rounded hover:bg-green-600/30"
                >
                  Excel
                </button>
                <button onClick={() => setShowResultsModal(false)} className="p-1 hover:bg-gray-700 rounded">
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
            </div>
            <div className="overflow-y-auto scrollbar-hide max-h-[calc(90vh-120px)]">
              <table className="w-full">
                <thead className="bg-gray-800 sticky top-0">
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Student</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Roll No</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Score</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Time Taken</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {Array.from({ length: 10 }, (_, i) => ({
                    name: ['Rahul Kumar', 'Priya Sharma', 'Amit Patel', 'Sneha Reddy', 'Vikram Singh', 'Ananya Das', 'Rohan Gupta', 'Neha Verma', 'Arjun Nair', 'Kavya Menon'][i],
                    roll: `21CS${String(i + 1).padStart(3, '0')}`,
                    score: Math.floor(Math.random() * 40) + 60,
                    time: Math.floor(Math.random() * 30) + 40,
                  })).map((student, i) => (
                    <tr key={i} className="hover:bg-gray-700/50">
                      <td className="px-4 py-3 text-sm text-white">{student.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-300">{student.roll}</td>
                      <td className="px-4 py-3">
                        <span className={`text-sm font-medium ${student.score >= 70 ? 'text-green-400' : student.score >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>
                          {student.score}/{selectedTest.max_marks}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-300">{student.time} min</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-0.5 rounded ${student.score >= 40 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                          {student.score >= 40 ? 'Pass' : 'Fail'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Student Detail Modal */}
      {showStudentDetailModal && selectedStudent && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-2xl mx-4 border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${getStudentStatusColor(selectedStudent.status)}`} />
                <div>
                  <h3 className="text-lg font-semibold text-white">{selectedStudent.name}</h3>
                  <p className="text-xs text-gray-400">{selectedStudent.roll_number}</p>
                </div>
              </div>
              <button onClick={() => setShowStudentDetailModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-white">{selectedStudent.progress}%</p>
                  <p className="text-xs text-gray-400">Progress</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-white">{selectedStudent.time_spent}</p>
                  <p className="text-xs text-gray-400">Time (min)</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                  <p className={`text-2xl font-bold ${selectedStudent.tab_switches > 5 ? 'text-red-400' : 'text-white'}`}>{selectedStudent.tab_switches}</p>
                  <p className="text-xs text-gray-400">Tab Switches</p>
                </div>
                <div className="bg-gray-700/50 rounded-lg p-3 text-center">
                  <p className={`text-2xl font-bold ${selectedStudent.ai_usage > 20 ? 'text-red-400' : 'text-white'}`}>{selectedStudent.ai_usage}%</p>
                  <p className="text-xs text-gray-400">AI Usage</p>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Current Activity</h4>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <p className="text-sm text-white">{selectedStudent.last_activity}</p>
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Question Progress</h4>
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((q) => (
                    <div key={q} className="flex items-center justify-between bg-gray-700/50 rounded px-3 py-2">
                      <span className="text-sm text-gray-300">Question {q}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        q <= Math.ceil(selectedStudent.progress / 25) ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'
                      }`}>
                        {q <= Math.ceil(selectedStudent.progress / 25) ? 'Completed' : 'Pending'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-gray-700">
              <button
                onClick={() => {
                  handleWarnStudent(selectedStudent)
                  setShowStudentDetailModal(false)
                }}
                className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700"
              >
                Send Warning
              </button>
              <button
                onClick={() => {
                  handleEndStudentTest(selectedStudent)
                  setShowStudentDetailModal(false)
                }}
                className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                Force Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Question Preview Modal */}
      {showQuestionPreviewModal && selectedQuestion && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-2xl mx-4 border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div>
                <h3 className="text-lg font-semibold text-white">{selectedQuestion.title}</h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    (selectedQuestion.type || selectedQuestion.question_type) === 'coding' ? 'bg-purple-500/20 text-purple-400' :
                    (selectedQuestion.type || selectedQuestion.question_type) === 'sql' ? 'bg-blue-500/20 text-blue-400' :
                    (selectedQuestion.type || selectedQuestion.question_type) === 'ml' ? 'bg-green-500/20 text-green-400' :
                    'bg-orange-500/20 text-orange-400'
                  }`}>
                    {(selectedQuestion.type || selectedQuestion.question_type || 'N/A').toUpperCase()}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${getDifficultyColor(selectedQuestion.difficulty)}`}>
                    {selectedQuestion.difficulty}
                  </span>
                  <span className="text-xs text-gray-400">{selectedQuestion.marks} marks | {selectedQuestion.time_estimate} min</span>
                </div>
              </div>
              <button onClick={() => setShowQuestionPreviewModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-300 mb-2">Problem Description</h4>
                <div className="bg-gray-700/50 rounded-lg p-3">
                  <p className="text-sm text-gray-300">
                    {selectedQuestion.type === 'coding' && `Implement a ${selectedQuestion.title.toLowerCase()} with the following operations...`}
                    {selectedQuestion.type === 'sql' && `Write SQL queries to perform ${selectedQuestion.title.toLowerCase()}...`}
                    {selectedQuestion.type === 'ml' && `Build a ${selectedQuestion.title.toLowerCase()} using the provided dataset...`}
                    {selectedQuestion.type === 'analytics' && `Create a ${selectedQuestion.title.toLowerCase()} to process the data...`}
                  </p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Test Cases</h4>
                  <div className="bg-gray-700/50 rounded-lg p-3">
                    <p className="text-sm text-white">{selectedQuestion.test_cases} test cases</p>
                    <p className="text-xs text-gray-400">Including hidden cases</p>
                  </div>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-300 mb-2">Usage Stats</h4>
                  <div className="bg-gray-700/50 rounded-lg p-3">
                    <p className="text-sm text-white">Used {selectedQuestion.usage_count} times</p>
                    <p className="text-xs text-gray-400">Topic: {selectedQuestion.topic}</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 p-4 border-t border-gray-700">
              <button
                onClick={() => setShowQuestionPreviewModal(false)}
                className="px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-lg"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleAddQuestionToTest(selectedQuestion)
                  setShowQuestionPreviewModal(false)
                }}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Add to Test
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Evaluation Panel Modal */}
      {showEvaluationPanel && selectedTest && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <div>
                <h3 className="text-lg font-semibold text-white">Evaluate: {selectedTest.title}</h3>
                <p className="text-xs text-gray-400">{selectedTest.participants} submissions to evaluate</p>
              </div>
              <button onClick={() => setShowEvaluationPanel(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4 overflow-y-auto scrollbar-hide max-h-[calc(90vh-180px)]">
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
                <p className="text-sm text-blue-400">Auto-evaluation completed for code correctness (60%). Manual evaluation pending for code quality (30%) and viva (10%).</p>
              </div>
              <div className="space-y-2">
                {Array.from({ length: 5 }, (_, i) => ({
                  name: ['Rahul Kumar', 'Priya Sharma', 'Amit Patel', 'Sneha Reddy', 'Vikram Singh'][i],
                  roll: `21CS${String(i + 1).padStart(3, '0')}`,
                  autoScore: Math.floor(Math.random() * 20) + 40,
                  manualScore: i < 2 ? Math.floor(Math.random() * 10) + 20 : null,
                  evaluated: i < 2
                })).map((student, i) => (
                  <div key={i} className={`flex items-center justify-between p-3 rounded-lg ${student.evaluated ? 'bg-green-500/10 border border-green-500/30' : 'bg-gray-700/50'}`}>
                    <div>
                      <p className="text-sm text-white">{student.name}</p>
                      <p className="text-xs text-gray-400">{student.roll}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-xs text-gray-400">Auto</p>
                        <p className="text-sm text-white">{student.autoScore}/60</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs text-gray-400">Manual</p>
                        <p className="text-sm text-white">{student.manualScore !== null ? `${student.manualScore}/30` : '-'}</p>
                      </div>
                      <button className={`px-3 py-1.5 text-xs rounded ${student.evaluated ? 'bg-green-600 text-white' : 'bg-blue-600 text-white hover:bg-blue-700'}`}>
                        {student.evaluated ? 'Reviewed' : 'Evaluate'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-between p-4 border-t border-gray-700">
              <div className="text-sm text-gray-400">
                Progress: 2/5 students evaluated
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowEvaluationPanel(false)}
                  className="px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-lg"
                >
                  Save & Exit
                </button>
                <button
                  onClick={handleCompleteEvaluation}
                  className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Complete Evaluation
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showCreateWizard && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-y-auto scrollbar-hide">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white z-10">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Create New Test</h3>
                <p className="text-sm text-gray-500">Step {wizardStep} of 4</p>
              </div>
              <button onClick={() => setShowCreateWizard(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Progress Steps */}
            <div className="px-4 pt-4">
              <div className="flex items-center gap-2">
                {[1, 2, 3, 4].map((step) => (
                  <div key={step} className="flex items-center flex-1">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                      wizardStep >= step ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-600'
                    }`}>
                      {wizardStep > step ? <CheckCircle className="w-5 h-5" /> : step}
                    </div>
                    {step < 4 && (
                      <div className={`flex-1 h-1 mx-2 ${wizardStep > step ? 'bg-indigo-600' : 'bg-gray-200'}`} />
                    )}
                  </div>
                ))}
              </div>
              <div className="flex justify-between mt-2 text-xs text-gray-500">
                <span>Select Lab</span>
                <span>Add Questions</span>
                <span>Configure Rules</span>
                <span>Schedule</span>
              </div>
            </div>

            <div className="p-4">
              {/* Step 1: Select Lab */}
              {wizardStep === 1 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Test Title</label>
                    <input
                      type="text"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      placeholder="Enter test title"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Select Lab/Subject</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>Data Structures Lab (CS301L)</option>
                      <option>Database Lab (CS302L)</option>
                      <option>Operating Systems Lab (CS303L)</option>
                      <option>Machine Learning Lab (CS501L)</option>
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Duration (minutes)</label>
                      <input
                        type="number"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="90"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Total Marks</label>
                      <input
                        type="number"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                        placeholder="100"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Step 2: Add Questions */}
              {wizardStep === 2 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="font-medium text-gray-900">Select Questions (0 selected)</h4>
                    <div className="flex items-center gap-2">
                      <button className="text-sm text-indigo-600 hover:text-indigo-700">
                        + Create New Question
                      </button>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mb-4">
                    <input
                      type="text"
                      placeholder="Search questions..."
                      className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg"
                    />
                    <select className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white">
                      <option value="">All Types</option>
                      <option value="coding">Coding</option>
                      <option value="sql">SQL</option>
                    </select>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-hide">
                    {questions.map((q) => (
                      <label key={q.id} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                        <input type="checkbox" className="rounded text-indigo-600" />
                        <div className="flex-1">
                          <p className="text-sm font-medium text-gray-900">{q.title}</p>
                          <p className="text-xs text-gray-500">{q.type} | {q.difficulty} | {q.marks} marks</p>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Step 3: Configure Rules */}
              {wizardStep === 3 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Test Rules & Settings</h4>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Attempts Allowed</label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        <option value="1">1 Attempt</option>
                        <option value="2">2 Attempts</option>
                        <option value="3">3 Attempts</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Auto-save Interval</label>
                      <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                        <option value="30">Every 30 seconds</option>
                        <option value="60">Every 1 minute</option>
                        <option value="120">Every 2 minutes</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">AI Control</label>
                    <div className="space-y-2">
                      <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer has-[:checked]:border-red-500 has-[:checked]:bg-red-50">
                        <input type="radio" name="ai_control" defaultChecked className="text-red-600" />
                        <div>
                          <p className="text-sm font-medium">AI Fully Blocked</p>
                          <p className="text-xs text-gray-500">No AI assistance allowed during test</p>
                        </div>
                      </label>
                      <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer has-[:checked]:border-yellow-500 has-[:checked]:bg-yellow-50">
                        <input type="radio" name="ai_control" className="text-yellow-600" />
                        <div>
                          <p className="text-sm font-medium">AI Limited to X%</p>
                          <p className="text-xs text-gray-500">Allow limited AI usage with monitoring</p>
                        </div>
                      </label>
                      <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer has-[:checked]:border-blue-500 has-[:checked]:bg-blue-50">
                        <input type="radio" name="ai_control" className="text-blue-600" />
                        <div>
                          <p className="text-sm font-medium">AI Hints Only</p>
                          <p className="text-xs text-gray-500">Only allow AI hints, not full solutions</p>
                        </div>
                      </label>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <label className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="rounded text-indigo-600" />
                      <span className="text-sm text-gray-700">Enable tab switch detection</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" defaultChecked className="rounded text-indigo-600" />
                      <span className="text-sm text-gray-700">Block copy-paste</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="checkbox" className="rounded text-indigo-600" />
                      <span className="text-sm text-gray-700">Randomize questions per student</span>
                    </label>
                  </div>
                </div>
              )}

              {/* Step 4: Schedule */}
              {wizardStep === 4 && (
                <div className="space-y-4">
                  <h4 className="font-medium text-gray-900">Schedule & Publish</h4>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">When to Start</label>
                    <div className="space-y-2">
                      <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50">
                        <input type="radio" name="schedule" className="text-indigo-600" />
                        <div>
                          <p className="text-sm font-medium">Start Immediately</p>
                          <p className="text-xs text-gray-500">Test will be live as soon as you publish</p>
                        </div>
                      </label>
                      <label className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg cursor-pointer has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50">
                        <input type="radio" name="schedule" defaultChecked className="text-indigo-600" />
                        <div>
                          <p className="text-sm font-medium">Schedule for Later</p>
                          <p className="text-xs text-gray-500">Set a specific date and time</p>
                        </div>
                      </label>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                      <input
                        type="date"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Time</label>
                      <input
                        type="time"
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Assign To</label>
                    <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                      <option>CSE-3A (65 students)</option>
                      <option>CSE-3B (68 students)</option>
                      <option>All Sections</option>
                    </select>
                  </div>

                  <div className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked className="rounded text-indigo-600" />
                    <span className="text-sm text-gray-700">Send notification to students</span>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 mt-4">
                    <h5 className="text-sm font-medium text-gray-900 mb-2">Test Summary</h5>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <span className="text-gray-500">Duration:</span>
                      <span className="text-gray-900">90 minutes</span>
                      <span className="text-gray-500">Questions:</span>
                      <span className="text-gray-900">5 questions</span>
                      <span className="text-gray-500">Total Marks:</span>
                      <span className="text-gray-900">100 marks</span>
                      <span className="text-gray-500">AI Control:</span>
                      <span className="text-gray-900">Blocked</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between p-4 border-t border-gray-200 sticky bottom-0 bg-white">
              <button
                onClick={() => wizardStep > 1 ? setWizardStep(wizardStep - 1) : setShowCreateWizard(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                {wizardStep === 1 ? 'Cancel' : 'Back'}
              </button>
              <div className="flex items-center gap-2">
                <button className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                  Save as Draft
                </button>
                <button
                  onClick={() => wizardStep < 4 ? setWizardStep(wizardStep + 1) : setShowCreateWizard(false)}
                  className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  {wizardStep === 4 ? 'Publish Test' : 'Next'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal */}
      {confirmModal.show && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-md mx-4 border border-gray-700 shadow-2xl animate-in zoom-in-95 duration-200">
            <div className="p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  confirmModal.confirmColor === 'red' ? 'bg-red-500/20' :
                  confirmModal.confirmColor === 'orange' ? 'bg-orange-500/20' :
                  'bg-green-500/20'
                }`}>
                  {confirmModal.confirmColor === 'red' ? (
                    <AlertCircle className={`w-5 h-5 text-red-400`} />
                  ) : confirmModal.confirmColor === 'orange' ? (
                    <AlertTriangle className={`w-5 h-5 text-orange-400`} />
                  ) : (
                    <Play className={`w-5 h-5 text-green-400`} />
                  )}
                </div>
                <h3 className="text-lg font-semibold text-white">{confirmModal.title}</h3>
              </div>
              <p className="text-gray-300 text-sm mb-6">{confirmModal.message}</p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setConfirmModal(prev => ({ ...prev, show: false }))}
                  className="px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmModal.onConfirm}
                  className={`px-4 py-2 text-sm text-white rounded-lg transition-colors ${
                    confirmModal.confirmColor === 'red' ? 'bg-red-600 hover:bg-red-700' :
                    confirmModal.confirmColor === 'orange' ? 'bg-orange-600 hover:bg-orange-700' :
                    'bg-green-600 hover:bg-green-700'
                  }`}
                >
                  {confirmModal.confirmText}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
