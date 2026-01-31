/**
 * usePlayground Hook
 *
 * React hook for managing code playground state and API calls.
 * Integrates with Judge0-powered backend for real code execution.
 */

import { useState, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'

// =============================================
// Types
// =============================================

export interface ExecutionResult {
  status: string
  status_id: number
  stdout: string | null
  stderr: string | null
  compile_output: string | null
  message: string | null
  time_ms: number
  memory_kb: number
  exit_code: number | null
  is_success: boolean
  is_error: boolean
}

export interface TestCase {
  input: string
  expected_output: string
}

export interface TestCaseResult {
  test_case_id: number
  input: string
  expected_output: string
  actual_output: string | null
  status: string
  passed: boolean
  time_ms: number
  memory_kb: number
  error: string | null
}

export interface TestRunResult {
  total_tests: number
  passed_tests: number
  failed_tests: number
  status: string
  results: TestCaseResult[]
  total_time_ms: number
  max_memory_kb: number
  all_passed: boolean
  pass_percentage: number
}

export interface LanguageInfo {
  id: number
  name: string
  aliases: string[]
  has_template: boolean
}

export interface PlaygroundState {
  isRunning: boolean
  result: ExecutionResult | null
  testResult: TestRunResult | null
  error: string | null
  languages: LanguageInfo[]
  languagesLoading: boolean
}

// =============================================
// Hook
// =============================================

export function usePlayground() {
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<ExecutionResult | null>(null)
  const [testResult, setTestResult] = useState<TestRunResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [languages, setLanguages] = useState<LanguageInfo[]>([])
  const [languagesLoading, setLanguagesLoading] = useState(false)

  /**
   * Execute code and return result
   */
  const runCode = useCallback(async (
    code: string,
    language: string,
    stdin: string = '',
    options: {
      timeLimitSec?: number
      memoryLimitMb?: number
    } = {}
  ): Promise<ExecutionResult | null> => {
    setIsRunning(true)
    setError(null)
    setResult(null)

    try {
      const response = await apiClient.post<ExecutionResult>('/playground/run', {
        source_code: code,
        language,
        stdin,
        time_limit_sec: options.timeLimitSec ?? 2.0,
        memory_limit_mb: options.memoryLimitMb ?? 128,
      })

      setResult(response)
      return response
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Execution failed'
      setError(errorMessage)
      return null
    } finally {
      setIsRunning(false)
    }
  }, [])

  /**
   * Run code against test cases
   */
  const runWithTests = useCallback(async (
    code: string,
    language: string,
    testCases: TestCase[],
    options: {
      timeLimitSec?: number
      memoryLimitMb?: number
    } = {}
  ): Promise<TestRunResult | null> => {
    setIsRunning(true)
    setError(null)
    setTestResult(null)

    try {
      const response = await apiClient.post<TestRunResult>('/playground/run-with-tests', {
        source_code: code,
        language,
        test_cases: testCases,
        time_limit_sec: options.timeLimitSec ?? 2.0,
        memory_limit_mb: options.memoryLimitMb ?? 128,
      })

      setTestResult(response)
      return response
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Test execution failed'
      setError(errorMessage)
      return null
    } finally {
      setIsRunning(false)
    }
  }, [])

  /**
   * Load available languages
   */
  const loadLanguages = useCallback(async (): Promise<LanguageInfo[]> => {
    setLanguagesLoading(true)

    try {
      const response = await apiClient.get<LanguageInfo[]>('/playground/languages')
      setLanguages(response)
      return response
    } catch (err: any) {
      console.error('Failed to load languages:', err)
      return []
    } finally {
      setLanguagesLoading(false)
    }
  }, [])

  /**
   * Get code template for a language
   */
  const getTemplate = useCallback(async (language: string): Promise<string> => {
    try {
      const response = await apiClient.get<{ template: string }>(`/playground/templates/${language}`)
      return response.template
    } catch (err: any) {
      console.error('Failed to get template:', err)
      return `// ${language}\n// Your code here\n`
    }
  }, [])

  /**
   * Check Judge0 health
   */
  const checkHealth = useCallback(async (): Promise<boolean> => {
    try {
      const response = await apiClient.get<{ status: string }>('/playground/health')
      return response.status === 'healthy'
    } catch {
      return false
    }
  }, [])

  /**
   * Clear results
   */
  const clearResults = useCallback(() => {
    setResult(null)
    setTestResult(null)
    setError(null)
  }, [])

  return {
    // State
    isRunning,
    result,
    testResult,
    error,
    languages,
    languagesLoading,

    // Actions
    runCode,
    runWithTests,
    loadLanguages,
    getTemplate,
    checkHealth,
    clearResults,
  }
}

// =============================================
// Utility Functions
// =============================================

/**
 * Format execution time for display
 */
export function formatExecutionTime(timeMs: number): string {
  if (timeMs < 1) {
    return '< 1 ms'
  }
  if (timeMs < 1000) {
    return `${timeMs.toFixed(0)} ms`
  }
  return `${(timeMs / 1000).toFixed(2)} s`
}

/**
 * Format memory usage for display
 */
export function formatMemoryUsage(memoryKb: number): string {
  if (memoryKb < 1024) {
    return `${memoryKb} KB`
  }
  return `${(memoryKb / 1024).toFixed(2)} MB`
}

/**
 * Get status color for result
 */
export function getStatusColor(status: string): string {
  switch (status) {
    case 'accepted':
    case 'passed':
    case 'all_passed':
      return 'text-green-500'
    case 'wrong_answer':
    case 'partial':
    case 'all_failed':
      return 'text-red-500'
    case 'time_limit_exceeded':
      return 'text-yellow-500'
    case 'compilation_error':
    case 'runtime_error_sigsegv':
    case 'runtime_error_nzec':
    case 'runtime_error_other':
      return 'text-orange-500'
    case 'in_queue':
    case 'processing':
      return 'text-blue-500'
    default:
      return 'text-gray-500'
  }
}

/**
 * Get human-readable status message
 */
export function getStatusMessage(status: string): string {
  const messages: Record<string, string> = {
    'accepted': 'Accepted',
    'passed': 'Passed',
    'all_passed': 'All Tests Passed',
    'partial': 'Partial Success',
    'all_failed': 'All Tests Failed',
    'wrong_answer': 'Wrong Answer',
    'time_limit_exceeded': 'Time Limit Exceeded',
    'compilation_error': 'Compilation Error',
    'runtime_error_sigsegv': 'Runtime Error (SIGSEGV)',
    'runtime_error_sigxfsz': 'Runtime Error (File Size)',
    'runtime_error_sigfpe': 'Runtime Error (Math Error)',
    'runtime_error_sigabrt': 'Runtime Error (SIGABRT)',
    'runtime_error_nzec': 'Runtime Error (Non-Zero Exit)',
    'runtime_error_other': 'Runtime Error',
    'internal_error': 'Internal Error',
    'in_queue': 'In Queue',
    'processing': 'Processing',
  }
  return messages[status] || status
}

/**
 * Popular languages for quick selection
 */
export const POPULAR_LANGUAGES = [
  { id: 71, name: 'Python', icon: '🐍' },
  { id: 63, name: 'JavaScript', icon: '📜' },
  { id: 74, name: 'TypeScript', icon: '💠' },
  { id: 62, name: 'Java', icon: '☕' },
  { id: 54, name: 'C++', icon: '⚡' },
  { id: 50, name: 'C', icon: '🔧' },
  { id: 51, name: 'C#', icon: '🎯' },
  { id: 60, name: 'Go', icon: '🐹' },
  { id: 73, name: 'Rust', icon: '🦀' },
  { id: 72, name: 'Ruby', icon: '💎' },
  { id: 78, name: 'Kotlin', icon: '🎨' },
  { id: 83, name: 'Swift', icon: '🍎' },
]

export default usePlayground
