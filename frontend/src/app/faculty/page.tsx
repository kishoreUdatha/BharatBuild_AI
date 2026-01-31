'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
  Users, FileText, Code, BarChart3, Shield,
  TrendingUp, AlertTriangle, CheckCircle,
  Calendar, ClipboardList
} from 'lucide-react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Analytics {
  total_students: number
  total_submissions: number
  active_assignments: number
  avg_score: number
  plagiarism_cases: number
  completion_rate: number
  pending_reviews: number
  guided_students: number
}

export default function FacultyDashboard() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [recentAlerts, setRecentAlerts] = useState<any[]>([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE}/faculty/analytics/overview`)
        if (res.ok) setAnalytics(await res.json())
      } catch (e) {
        setAnalytics({
          total_students: 156,
          total_submissions: 423,
          active_assignments: 5,
          avg_score: 72.5,
          plagiarism_cases: 3,
          completion_rate: 68.5,
          pending_reviews: 4,
          guided_students: 8
        })
      }

      setRecentAlerts([
        { id: 1, student: 'Rahul Kumar', message: 'No activity in 5 days', severity: 'high' },
        { id: 2, student: 'Priya Sharma', message: 'High AI score (72%)', severity: 'medium' },
        { id: 3, student: 'Amit Patel', message: 'Assignment submitted', severity: 'low' },
      ])

      setLoading(false)
    }
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="p-6 h-full">
      {/* Welcome */}
      <div className="mb-6">
        <p className="text-gray-400">Welcome back, Dr. Faculty. Here's your overview.</p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Students</p>
              <p className="text-3xl font-bold text-white mt-1">{analytics?.total_students}</p>
            </div>
            <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
              <Users className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span className="text-green-500">+12%</span>
            <span className="text-gray-500">this month</span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Submissions</p>
              <p className="text-3xl font-bold text-white mt-1">{analytics?.total_submissions}</p>
            </div>
            <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center">
              <FileText className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span className="text-green-500">+8%</span>
            <span className="text-gray-500">this week</span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Avg Score</p>
              <p className="text-3xl font-bold text-white mt-1">{analytics?.avg_score}%</p>
            </div>
            <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
              <BarChart3 className="w-6 h-6 text-purple-400" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <TrendingUp className="w-4 h-4 text-green-500" />
            <span className="text-green-500">+5%</span>
            <span className="text-gray-500">improvement</span>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Completion</p>
              <p className="text-3xl font-bold text-white mt-1">{analytics?.completion_rate}%</p>
            </div>
            <div className="w-12 h-12 bg-cyan-500/20 rounded-xl flex items-center justify-center">
              <CheckCircle className="w-6 h-6 text-cyan-400" />
            </div>
          </div>
          <div className="flex items-center gap-1 mt-3 text-sm">
            <span className="text-gray-500">Target: 85%</span>
          </div>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="col-span-2 space-y-6">
          {/* Pending Actions */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-white font-semibold mb-4">Pending Actions</h3>
            <div className="grid grid-cols-3 gap-4">
              <Link href="/faculty/reviews">
                <div className="bg-gray-700/50 rounded-lg p-4 hover:bg-gray-700 transition-colors cursor-pointer">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 bg-orange-500/20 rounded-lg flex items-center justify-center">
                      <ClipboardList className="w-5 h-5 text-orange-400" />
                    </div>
                    <span className="text-2xl font-bold text-white">{analytics?.pending_reviews}</span>
                  </div>
                  <p className="text-gray-400 text-sm">Project Reviews</p>
                </div>
              </Link>

              <Link href="/faculty/integrity">
                <div className="bg-gray-700/50 rounded-lg p-4 hover:bg-gray-700 transition-colors cursor-pointer">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 bg-red-500/20 rounded-lg flex items-center justify-center">
                      <Shield className="w-5 h-5 text-red-400" />
                    </div>
                    <span className="text-2xl font-bold text-white">{analytics?.plagiarism_cases}</span>
                  </div>
                  <p className="text-gray-400 text-sm">Integrity Flags</p>
                </div>
              </Link>

              <Link href="/faculty/code-review">
                <div className="bg-gray-700/50 rounded-lg p-4 hover:bg-gray-700 transition-colors cursor-pointer">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-10 h-10 bg-blue-500/20 rounded-lg flex items-center justify-center">
                      <Code className="w-5 h-5 text-blue-400" />
                    </div>
                    <span className="text-2xl font-bold text-white">12</span>
                  </div>
                  <p className="text-gray-400 text-sm">Code Reviews</p>
                </div>
              </Link>
            </div>
          </div>

          {/* Review Timeline */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-white font-semibold mb-4">Project Review Timeline</h3>
            <div className="flex items-center justify-between">
              {[
                { stage: 'R1', name: 'Problem Statement', status: 'complete' },
                { stage: 'R2', name: 'Design', status: 'current' },
                { stage: 'R3', name: 'Implementation', status: 'pending' },
                { stage: 'Final', name: 'Final Review', status: 'pending' },
              ].map((review, index) => (
                <div key={review.stage} className="flex items-center">
                  <div className="text-center">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-2 ${
                      review.status === 'complete' ? 'bg-green-500' :
                      review.status === 'current' ? 'bg-blue-500' : 'bg-gray-600'
                    }`}>
                      {review.status === 'complete' ? (
                        <CheckCircle className="w-6 h-6 text-white" />
                      ) : (
                        <span className="text-white font-bold text-sm">{review.stage}</span>
                      )}
                    </div>
                    <p className="text-white text-xs font-medium">{review.name}</p>
                  </div>
                  {index < 3 && (
                    <div className={`w-16 h-1 mx-2 rounded ${
                      review.status === 'complete' ? 'bg-green-500' : 'bg-gray-600'
                    }`}></div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Recent Activity */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-semibold">Recent Activity</h3>
              <Link href="/faculty/activity" className="text-blue-400 text-sm hover:underline">View All</Link>
            </div>
            <div className="space-y-3">
              {[
                { action: 'Submitted assignment', student: 'Rahul Kumar', time: '2 min ago', type: 'submission' },
                { action: 'Completed Lab 3', student: 'Priya Sharma', time: '15 min ago', type: 'complete' },
                { action: 'Started MCQ test', student: 'Amit Patel', time: '1 hour ago', type: 'start' },
                { action: 'Requested help', student: 'Sneha Reddy', time: '2 hours ago', type: 'help' },
              ].map((activity, idx) => (
                <div key={idx} className="flex items-center gap-4 p-3 bg-gray-700/30 rounded-lg">
                  <div className={`w-2 h-2 rounded-full ${
                    activity.type === 'submission' ? 'bg-green-500' :
                    activity.type === 'complete' ? 'bg-blue-500' :
                    activity.type === 'start' ? 'bg-yellow-500' : 'bg-purple-500'
                  }`}></div>
                  <div className="flex-1">
                    <p className="text-white text-sm">
                      <span className="font-medium">{activity.student}</span>
                      <span className="text-gray-400"> {activity.action}</span>
                    </p>
                  </div>
                  <span className="text-gray-500 text-xs">{activity.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Alerts */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              <h3 className="text-white font-semibold">Alerts</h3>
            </div>
            <div className="space-y-3">
              {recentAlerts.map((alert) => (
                <div key={alert.id} className="flex items-start gap-3 p-3 bg-gray-700/30 rounded-lg">
                  <div className={`w-2 h-2 mt-2 rounded-full flex-shrink-0 ${
                    alert.severity === 'high' ? 'bg-red-500' :
                    alert.severity === 'medium' ? 'bg-yellow-500' : 'bg-green-500'
                  }`}></div>
                  <div className="min-w-0">
                    <p className="text-white text-sm font-medium truncate">{alert.student}</p>
                    <p className="text-gray-500 text-xs truncate">{alert.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Upcoming */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-5 h-5 text-blue-500" />
              <h3 className="text-white font-semibold">Upcoming</h3>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3 p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
                <div className="text-center">
                  <p className="text-blue-400 text-xs font-medium">FEB</p>
                  <p className="text-white text-lg font-bold">10</p>
                </div>
                <div>
                  <p className="text-white text-sm font-medium">Project Review R2</p>
                  <p className="text-gray-500 text-xs">CSE-A, Sem 5</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                <div className="text-center">
                  <p className="text-emerald-400 text-xs font-medium">FEB</p>
                  <p className="text-white text-lg font-bold">05</p>
                </div>
                <div>
                  <p className="text-white text-sm font-medium">Lab 3 Deadline</p>
                  <p className="text-gray-500 text-xs">Data Structures</p>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
            <h3 className="text-white font-semibold mb-4">This Week</h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-gray-400 text-sm">Lab Progress</span>
                  <span className="text-white text-sm font-medium">68%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-blue-500 h-2 rounded-full" style={{ width: '68%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-gray-400 text-sm">Assignment Completion</span>
                  <span className="text-white text-sm font-medium">82%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '82%' }}></div>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-gray-400 text-sm">Attendance</span>
                  <span className="text-white text-sm font-medium">91%</span>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div className="bg-purple-500 h-2 rounded-full" style={{ width: '91%' }}></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
