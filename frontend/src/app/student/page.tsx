'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  FileText,
  Clock,
  CheckCircle,
  AlertCircle,
  Award,
  TrendingUp,
  Calendar,
  ChevronRight,
  Loader2,
  Code,
  Target,
  Zap
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface DashboardData {
  student: {
    id: string
    name: string
    batch: string
  }
  stats: {
    total_assignments: number
    completed: number
    pending: number
    overdue: number
    total_submissions: number
    average_score: number
  }
  recent_submissions: any[]
  upcoming_deadlines: any[]
}

export default function StudentDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  const getAuthHeaders = () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null
    return {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    }
  }

  useEffect(() => {
    fetchDashboard()
  }, [])

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${API_URL}/student/dashboard`, {
        headers: getAuthHeaders()
      })

      if (res.ok) {
        setData(await res.json())
      } else {
        // Mock data
        setData({
          student: {
            id: '1',
            name: 'Student User',
            batch: 'CSE-3A'
          },
          stats: {
            total_assignments: 5,
            completed: 2,
            pending: 2,
            overdue: 1,
            total_submissions: 8,
            average_score: 78
          },
          recent_submissions: [
            { id: '1', assignment_id: 'demo-2', status: 'partial', score: 75, submitted_at: new Date().toISOString() }
          ],
          upcoming_deadlines: [
            { id: 'demo-1', title: 'Binary Search', due_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString() },
            { id: 'demo-2', title: 'Linked List Reversal', due_date: new Date(Date.now() + 3 * 24 * 60 * 60 * 1000).toISOString() }
          ]
        })
      }
    } catch (e) {
      console.error('Error:', e)
    }
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-green-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="p-6">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">
          Welcome back, {data?.student.name || 'Student'}!
        </h1>
        <p className="text-gray-400">
          Here's your learning progress overview
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-500/20 rounded-xl">
              <FileText className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="text-3xl font-bold text-white">{data?.stats.total_assignments || 0}</p>
              <p className="text-gray-400 text-sm">Total Assignments</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-500/20 rounded-xl">
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
            <div>
              <p className="text-3xl font-bold text-white">{data?.stats.completed || 0}</p>
              <p className="text-gray-400 text-sm">Completed</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-yellow-500/20 rounded-xl">
              <Clock className="w-6 h-6 text-yellow-400" />
            </div>
            <div>
              <p className="text-3xl font-bold text-white">{data?.stats.pending || 0}</p>
              <p className="text-gray-400 text-sm">Pending</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-500/20 rounded-xl">
              <TrendingUp className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <p className="text-3xl font-bold text-white">{data?.stats.average_score?.toFixed(0) || 0}%</p>
              <p className="text-gray-400 text-sm">Average Score</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Upcoming Deadlines */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700 flex items-center justify-between">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <Calendar className="w-5 h-5 text-orange-400" />
              Upcoming Deadlines
            </h2>
            <Link href="/student/assignments" className="text-blue-400 text-sm hover:underline">
              View all
            </Link>
          </div>
          <div className="p-4">
            {data?.upcoming_deadlines && data.upcoming_deadlines.length > 0 ? (
              <div className="space-y-3">
                {data.upcoming_deadlines.map((item: any) => (
                  <Link
                    key={item.id}
                    href={`/student/assignments/${item.id}`}
                    className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors group"
                  >
                    <div>
                      <p className="text-white font-medium group-hover:text-blue-400 transition-colors">
                        {item.title}
                      </p>
                      <p className="text-gray-500 text-sm">
                        Due: {new Date(item.due_date).toLocaleDateString()}
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-blue-400 group-hover:translate-x-1 transition-all" />
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <p className="text-gray-400">No upcoming deadlines!</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-400" />
              Quick Actions
            </h2>
          </div>
          <div className="p-4 space-y-3">
            <Link
              href="/student/assignments"
              className="flex items-center gap-4 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg hover:bg-blue-500/20 transition-colors group"
            >
              <div className="p-3 bg-blue-500/20 rounded-xl">
                <FileText className="w-6 h-6 text-blue-400" />
              </div>
              <div className="flex-1">
                <p className="text-white font-medium">View Assignments</p>
                <p className="text-gray-400 text-sm">Complete your pending assignments</p>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-500 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              href="/lab"
              className="flex items-center gap-4 p-4 bg-green-500/10 border border-green-500/30 rounded-lg hover:bg-green-500/20 transition-colors group"
            >
              <div className="p-3 bg-green-500/20 rounded-xl">
                <Code className="w-6 h-6 text-green-400" />
              </div>
              <div className="flex-1">
                <p className="text-white font-medium">Practice Coding</p>
                <p className="text-gray-400 text-sm">Improve your programming skills</p>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-500 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              href="/playground"
              className="flex items-center gap-4 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg hover:bg-purple-500/20 transition-colors group"
            >
              <div className="p-3 bg-purple-500/20 rounded-xl">
                <Target className="w-6 h-6 text-purple-400" />
              </div>
              <div className="flex-1">
                <p className="text-white font-medium">Code Playground</p>
                <p className="text-gray-400 text-sm">Experiment with code freely</p>
              </div>
              <ChevronRight className="w-5 h-5 text-gray-500 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      {data?.recent_submissions && data.recent_submissions.length > 0 && (
        <div className="mt-6 bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-white font-semibold flex items-center gap-2">
              <Clock className="w-5 h-5 text-blue-400" />
              Recent Submissions
            </h2>
          </div>
          <div className="p-4">
            <div className="space-y-2">
              {data.recent_submissions.map((sub: any) => (
                <div
                  key={sub.id}
                  className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {sub.status === 'passed' ? (
                      <CheckCircle className="w-5 h-5 text-green-400" />
                    ) : sub.status === 'partial' ? (
                      <AlertCircle className="w-5 h-5 text-yellow-400" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-red-400" />
                    )}
                    <div>
                      <p className="text-white">Assignment #{sub.assignment_id}</p>
                      <p className="text-gray-500 text-xs">
                        {new Date(sub.submitted_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <span className={`text-lg font-bold ${
                    sub.score >= 80 ? 'text-green-400' :
                    sub.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {sub.score}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
