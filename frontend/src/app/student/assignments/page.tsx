'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Code,
  Database,
  Filter,
  Search,
  Calendar,
  Award,
  TrendingUp,
  ChevronRight,
  Loader2,
  RefreshCw
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Assignment {
  id: string
  title: string
  subject: string
  description: string
  due_date: string
  problem_type: string
  difficulty: string
  language: string
  max_score: number
  submission_status: string
  submissions_count: number
  best_score: number | null
  is_overdue: boolean
  time_remaining: string | null
}

interface DashboardStats {
  total_assignments: number
  completed: number
  pending: number
  overdue: number
  total_submissions: number
  average_score: number
}

export default function StudentAssignmentsPage() {
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'active' | 'completed' | 'overdue'>('all')
  const [searchQuery, setSearchQuery] = useState('')

  const getAuthHeaders = () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      // Fetch dashboard stats
      const dashRes = await fetch(`${API_URL}/student/dashboard`, {
        headers: getAuthHeaders()
      })
      if (dashRes.ok) {
        const dashData = await dashRes.json()
        setStats(dashData.stats)
      }

      // Fetch assignments
      const params = new URLSearchParams()
      if (filter !== 'all') params.append('status', filter)

      const assignRes = await fetch(`${API_URL}/student/assignments?${params}`, {
        headers: getAuthHeaders()
      })
      if (assignRes.ok) {
        const data = await assignRes.json()
        setAssignments(data.assignments || [])
      } else {
        // Use mock data
        setAssignments([
          {
            id: 'demo-1',
            title: 'Binary Search Implementation',
            subject: 'Data Structures',
            description: 'Implement binary search algorithm',
            due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
            problem_type: 'coding',
            difficulty: 'easy',
            language: 'python',
            max_score: 100,
            submission_status: 'active',
            submissions_count: 0,
            best_score: null,
            is_overdue: false,
            time_remaining: '7 days'
          },
          {
            id: 'demo-2',
            title: 'Linked List Reversal',
            subject: 'Data Structures',
            description: 'Reverse a singly linked list',
            due_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString(),
            problem_type: 'coding',
            difficulty: 'medium',
            language: 'python',
            max_score: 100,
            submission_status: 'active',
            submissions_count: 2,
            best_score: 75,
            is_overdue: false,
            time_remaining: '3 days'
          },
          {
            id: 'demo-3',
            title: 'SQL Query - Employee Salary',
            subject: 'DBMS',
            description: 'Write SQL query to find employees',
            due_date: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
            problem_type: 'sql',
            difficulty: 'medium',
            language: 'sql',
            max_score: 50,
            submission_status: 'overdue',
            submissions_count: 0,
            best_score: null,
            is_overdue: true,
            time_remaining: null
          }
        ])
        setStats({
          total_assignments: 3,
          completed: 0,
          pending: 2,
          overdue: 1,
          total_submissions: 2,
          average_score: 75
        })
      }
    } catch (e) {
      console.error('Error fetching data:', e)
    }
    setLoading(false)
  }

  useEffect(() => {
    fetchData()
  }, [filter])

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'easy': return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'hard': return 'bg-red-500/20 text-red-400 border-red-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500/20 text-green-400'
      case 'active': return 'bg-blue-500/20 text-blue-400'
      case 'overdue': return 'bg-red-500/20 text-red-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'coding': return <Code className="w-4 h-4" />
      case 'sql': return <Database className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  const filteredAssignments = assignments.filter(a =>
    a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.subject.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading assignments...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-white">My Assignments</h1>
              <p className="text-gray-400 text-sm mt-1">View and submit your coding assignments</p>
            </div>
            <button
              onClick={fetchData}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
          </div>

          {/* Stats Cards */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="bg-gray-700/50 rounded-xl p-4 border border-gray-600">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-500/20 rounded-lg">
                    <FileText className="w-5 h-5 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.total_assignments}</p>
                    <p className="text-gray-400 text-xs">Total</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-700/50 rounded-xl p-4 border border-gray-600">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-500/20 rounded-lg">
                    <CheckCircle className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.completed}</p>
                    <p className="text-gray-400 text-xs">Completed</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-700/50 rounded-xl p-4 border border-gray-600">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-500/20 rounded-lg">
                    <Clock className="w-5 h-5 text-yellow-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.pending}</p>
                    <p className="text-gray-400 text-xs">Pending</p>
                  </div>
                </div>
              </div>
              <div className="bg-gray-700/50 rounded-xl p-4 border border-gray-600">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-500/20 rounded-lg">
                    <TrendingUp className="w-5 h-5 text-purple-400" />
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-white">{stats.average_score.toFixed(0)}%</p>
                    <p className="text-gray-400 text-xs">Avg Score</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filters & Search */}
      <div className="max-w-7xl mx-auto px-6 py-4">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          {/* Filter Tabs */}
          <div className="flex gap-2">
            {[
              { id: 'all', label: 'All' },
              { id: 'active', label: 'Active' },
              { id: 'completed', label: 'Completed' },
              { id: 'overdue', label: 'Overdue' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setFilter(tab.id as any)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  filter === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search assignments..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      {/* Assignments List */}
      <div className="max-w-7xl mx-auto px-6 pb-8">
        {filteredAssignments.length === 0 ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-12 text-center">
            <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
            <h3 className="text-white font-medium mb-2">No assignments found</h3>
            <p className="text-gray-400 text-sm">Check back later for new assignments</p>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredAssignments.map(assignment => (
              <Link
                key={assignment.id}
                href={`/student/assignments/${assignment.id}`}
                className="block bg-gray-800 rounded-xl border border-gray-700 p-5 hover:border-blue-500/50 transition-all group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className={`p-2 rounded-lg ${
                        assignment.problem_type === 'coding' ? 'bg-blue-500/20' :
                        assignment.problem_type === 'sql' ? 'bg-purple-500/20' : 'bg-gray-500/20'
                      }`}>
                        {getTypeIcon(assignment.problem_type)}
                      </div>
                      <div>
                        <h3 className="text-white font-medium group-hover:text-blue-400 transition-colors">
                          {assignment.title}
                        </h3>
                        <p className="text-gray-500 text-sm">{assignment.subject}</p>
                      </div>
                    </div>

                    <p className="text-gray-400 text-sm mb-4 line-clamp-2">
                      {assignment.description}
                    </p>

                    <div className="flex flex-wrap items-center gap-3">
                      <span className={`px-2 py-1 rounded text-xs border ${getDifficultyColor(assignment.difficulty)}`}>
                        {assignment.difficulty}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs ${getStatusColor(assignment.submission_status)}`}>
                        {assignment.submission_status === 'completed' ? 'Completed' :
                         assignment.submission_status === 'overdue' ? 'Overdue' : 'Active'}
                      </span>
                      <span className="text-gray-500 text-xs flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {assignment.is_overdue ? 'Overdue' : `Due: ${new Date(assignment.due_date).toLocaleDateString()}`}
                      </span>
                      <span className="text-gray-500 text-xs">
                        {assignment.submissions_count} submission{assignment.submissions_count !== 1 ? 's' : ''}
                      </span>
                    </div>
                  </div>

                  <div className="text-right flex-shrink-0">
                    {assignment.best_score !== null ? (
                      <div className="mb-2">
                        <p className={`text-2xl font-bold ${
                          assignment.best_score >= 80 ? 'text-green-400' :
                          assignment.best_score >= 60 ? 'text-yellow-400' : 'text-red-400'
                        }`}>
                          {assignment.best_score}%
                        </p>
                        <p className="text-gray-500 text-xs">Best Score</p>
                      </div>
                    ) : (
                      <div className="mb-2">
                        <p className="text-gray-500 text-sm">Not attempted</p>
                      </div>
                    )}
                    <div className="flex items-center gap-1 text-blue-400 text-sm">
                      <span>Solve</span>
                      <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
