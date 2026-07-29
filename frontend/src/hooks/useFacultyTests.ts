import { useState, useEffect, useCallback } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export interface Test {
  id: string
  title: string
  lab: string
  questions_count: number
  duration_minutes: number
  max_marks: number
  scheduled_at?: string
  status: 'draft' | 'scheduled' | 'live' | 'completed' | 'evaluating'
  participants?: number
  avg_score?: number
  ai_control: 'blocked' | 'limited' | 'hints_only'
}

export interface Question {
  id: string
  title: string
  question_type: string
  type?: string
  difficulty: string
  marks: number
  time_estimate: number
  topic: string
  test_cases_count?: number
  test_cases?: number
  times_used?: number
  usage_count?: number
  tags?: string[]
}

export interface LiveStudent {
  id: string
  student_id: string
  name: string
  roll_number: string
  status: 'not_started' | 'active' | 'idle' | 'suspicious' | 'submitted' | 'force_submitted'
  progress: number
  time_spent: number
  tab_switches: number
  ai_usage: number
  last_activity: string
  questions_attempted?: number
}

export interface TestAlert {
  id: string
  session_id: string
  student: string
  roll: string
  message: string
  severity: 'low' | 'medium' | 'high'
  time: string
  alert_type: string
}

export interface MonitorData {
  test: {
    id: string
    title: string
    lab: string
    status: string
    duration_minutes: number
    started_at: string | null
    time_remaining_seconds: number | null
  }
  stats: {
    active: number
    idle: number
    suspicious: number
    submitted: number
    not_started?: number
  }
  students: LiveStudent[]
  alerts: TestAlert[]
}

export interface TestResult {
  rank: number
  student_id: string
  name: string
  roll_number: string
  email: string
  score: number
  max_score: number
  percentage: number
  time_taken_minutes: number
  submitted_at: string
  is_evaluated: boolean
  status: string
}

const getAuthHeaders = () => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  }
}

export function useFacultyTests() {
  const [tests, setTests] = useState<Test[]>([])
  const [questions, setQuestions] = useState<Question[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Fetch all tests
  const fetchTests = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch(`${API_URL}/faculty-tests/tests`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setTests(data)
      } else {
        // Use mock data if API fails
        setTests([
          { id: '1', title: 'Data Structures Mid-Sem Lab Test', lab: 'DS Lab', questions_count: 5, duration_minutes: 120, max_marks: 100, scheduled_at: '2026-02-15 10:00', status: 'scheduled', ai_control: 'blocked' },
          { id: '2', title: 'SQL Proficiency Test', lab: 'DBMS Lab', questions_count: 8, duration_minutes: 90, max_marks: 80, status: 'live', participants: 45, ai_control: 'limited' },
          { id: '3', title: 'Python Programming Assessment', lab: 'Python Lab', questions_count: 6, duration_minutes: 60, max_marks: 60, status: 'completed', participants: 68, avg_score: 72, ai_control: 'hints_only' },
        ])
      }
    } catch (err) {
      console.error('Error fetching tests:', err)
      // Use mock data on error
      setTests([
        { id: '1', title: 'Data Structures Mid-Sem Lab Test', lab: 'DS Lab', questions_count: 5, duration_minutes: 120, max_marks: 100, scheduled_at: '2026-02-15 10:00', status: 'scheduled', ai_control: 'blocked' },
        { id: '2', title: 'SQL Proficiency Test', lab: 'DBMS Lab', questions_count: 8, duration_minutes: 90, max_marks: 80, status: 'live', participants: 45, ai_control: 'limited' },
      ])
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch question bank
  const fetchQuestions = useCallback(async (filters?: { type?: string; difficulty?: string; search?: string }) => {
    try {
      const params = new URLSearchParams()
      if (filters?.type) params.append('question_type', filters.type)
      if (filters?.difficulty) params.append('difficulty', filters.difficulty)
      if (filters?.search) params.append('search', filters.search)

      const response = await fetch(`${API_URL}/faculty-tests/question-bank?${params}`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        const data = await response.json()
        setQuestions(data)
      } else {
        // Mock data
        setQuestions([
          { id: '1', title: 'Implement Binary Search Tree', question_type: 'coding', difficulty: 'medium', marks: 20, time_estimate: 25, topic: 'Trees', test_cases_count: 10, times_used: 8 },
          { id: '2', title: 'SQL Join Operations', question_type: 'sql', difficulty: 'easy', marks: 15, time_estimate: 15, topic: 'SQL Joins', test_cases_count: 5, times_used: 12 },
        ])
      }
    } catch (err) {
      console.error('Error fetching questions:', err)
    }
  }, [])

  // Create test
  const createTest = async (testData: {
    title: string
    lab_name?: string
    duration_minutes: number
    max_marks: number
    ai_control: string
    questions?: any[]
  }) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(testData)
    })
    if (!response.ok) throw new Error('Failed to create test')
    const data = await response.json()
    await fetchTests()
    return data
  }

  // Update test
  const updateTest = async (testId: string, testData: Partial<Test>) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}`, {
      method: 'PUT',
      headers: getAuthHeaders(),
      body: JSON.stringify(testData)
    })
    if (!response.ok) throw new Error('Failed to update test')
    await fetchTests()
    return response.json()
  }

  // Delete test
  const deleteTest = async (testId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}`, {
      method: 'DELETE',
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to delete test')
    await fetchTests()
  }

  // Duplicate test
  const duplicateTest = async (testId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/duplicate`, {
      method: 'POST',
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to duplicate test')
    await fetchTests()
    return response.json()
  }

  // Schedule test
  const scheduleTest = async (testId: string, scheduledAt: string, sections: string[]) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/schedule`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({
        scheduled_at: scheduledAt,
        assigned_sections: sections
      })
    })
    if (!response.ok) throw new Error('Failed to schedule test')
    await fetchTests()
    return response.json()
  }

  // Start test
  const startTest = async (testId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/start`, {
      method: 'POST',
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to start test')
    await fetchTests()
    return response.json()
  }

  // End test
  const endTest = async (testId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/end`, {
      method: 'POST',
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to end test')
    await fetchTests()
    return response.json()
  }

  // Get live monitoring data
  const getMonitorData = async (testId: string): Promise<MonitorData | null> => {
    try {
      const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/monitor`, {
        headers: getAuthHeaders()
      })
      if (response.ok) {
        return response.json()
      }
      return null
    } catch (err) {
      console.error('Error fetching monitor data:', err)
      return null
    }
  }

  // Student action (warn, force submit)
  const studentAction = async (testId: string, sessionId: string, action: string, message?: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/students/${sessionId}/action`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ action, message })
    })
    if (!response.ok) throw new Error('Failed to perform action')
    return response.json()
  }

  // Get test results
  const getResults = async (testId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/results`, {
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to get results')
    return response.json()
  }

  // Auto-evaluate test
  const evaluateTest = async (testId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/evaluate`, {
      method: 'POST',
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to evaluate test')
    await fetchTests()
    return response.json()
  }

  // Export results
  const exportResults = async (testId: string, format: 'csv' | 'excel' | 'pdf') => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/export/${format}`, {
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to export results')
    return response.json()
  }

  // Add question to bank
  const addQuestion = async (questionData: any) => {
    const response = await fetch(`${API_URL}/faculty-tests/question-bank`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(questionData)
    })
    if (!response.ok) throw new Error('Failed to add question')
    await fetchQuestions()
    return response.json()
  }

  // Add question to test
  const addQuestionToTest = async (testId: string, questionData: any) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/questions`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(questionData)
    })
    if (!response.ok) throw new Error('Failed to add question to test')
    return response.json()
  }

  // Add question from bank to test
  const addQuestionFromBank = async (testId: string, bankQuestionId: string) => {
    const response = await fetch(`${API_URL}/faculty-tests/tests/${testId}/questions/from-bank/${bankQuestionId}`, {
      method: 'POST',
      headers: getAuthHeaders()
    })
    if (!response.ok) throw new Error('Failed to add question from bank')
    return response.json()
  }

  // Initial fetch
  useEffect(() => {
    fetchTests()
    fetchQuestions()
  }, [fetchTests, fetchQuestions])

  return {
    tests,
    questions,
    loading,
    error,
    setTests,
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
    addQuestion,
    addQuestionToTest,
    addQuestionFromBank
  }
}
