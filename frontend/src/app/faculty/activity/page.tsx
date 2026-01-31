'use client'

import { useState, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface StudentClass {
  id: string
  name: string
}

interface EngagementData {
  student_id: string
  name: string
  activity_count: number
  submission_count: number
  engagement_level: string
}

interface Alert {
  id: string
  student_id: string
  student_name: string
  alert_type: string
  severity: string
  message: string
  is_read: boolean
  is_resolved: boolean
  created_at: string
}

interface HeatmapDay {
  date: string
  count: number
  level: number
  weekday: number
}

export default function ActivityDashboardPage() {
  const [classes, setClasses] = useState<StudentClass[]>([])
  const [selectedClass, setSelectedClass] = useState<string>('')
  const [engagement, setEngagement] = useState<{
    total_students: number
    avg_activities_per_student: number
    engagement_distribution: { high: number; medium: number; low: number }
    students: EngagementData[]
  } | null>(null)
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [engagementLoading, setEngagementLoading] = useState(false)
  const [selectedStudent, setSelectedStudent] = useState<string | null>(null)
  const [heatmap, setHeatmap] = useState<HeatmapDay[]>([])
  const [heatmapLoading, setHeatmapLoading] = useState(false)

  // Filter states
  const [days, setDays] = useState(7)

  useEffect(() => {
    fetchInitialData()
  }, [])

  useEffect(() => {
    if (selectedClass) {
      fetchEngagement()
    }
  }, [selectedClass, days])

  useEffect(() => {
    if (selectedStudent) {
      fetchHeatmap(selectedStudent)
    }
  }, [selectedStudent])

  const fetchInitialData = async () => {
    try {
      const token = localStorage.getItem('access_token')

      // Fetch classes
      const classesRes = await fetch(`${API_BASE}/faculty/classes`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (classesRes.ok) {
        const data = await classesRes.json()
        setClasses(data)
        if (data.length > 0) {
          setSelectedClass(data[0].id)
        }
      }

      // Fetch alerts
      const alertsRes = await fetch(`${API_BASE}/activity/alerts?limit=10`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (alertsRes.ok) {
        setAlerts(await alertsRes.json())
      }
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  const fetchEngagement = async () => {
    setEngagementLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/activity/class/${selectedClass}/engagement?days=${days}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        setEngagement(await res.json())
      }
    } catch (e) {
      console.error(e)
    }
    setEngagementLoading(false)
  }

  const fetchHeatmap = async (studentId: string) => {
    setHeatmapLoading(true)
    try {
      const token = localStorage.getItem('access_token')
      const res = await fetch(`${API_BASE}/activity/heatmap/${studentId}?weeks=12`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (res.ok) {
        const data = await res.json()
        setHeatmap(data.heatmap)
      }
    } catch (e) {
      console.error(e)
    }
    setHeatmapLoading(false)
  }

  const resolveAlert = async (alertId: string) => {
    try {
      const token = localStorage.getItem('access_token')
      await fetch(`${API_BASE}/activity/alerts/${alertId}/resolve`, {
        method: 'PUT',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAlerts(alerts.filter(a => a.id !== alertId))
    } catch (e) {
      console.error(e)
    }
  }

  const getEngagementColor = (level: string) => {
    switch (level) {
      case 'high': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
      case 'medium': return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
      case 'low': return 'bg-red-500/20 text-red-400 border-red-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-500/20 text-red-400'
      case 'medium': return 'bg-amber-500/20 text-amber-400'
      case 'low': return 'bg-blue-500/20 text-blue-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  const getHeatmapColor = (level: number) => {
    switch (level) {
      case 0: return 'bg-gray-800'
      case 1: return 'bg-emerald-900'
      case 2: return 'bg-emerald-700'
      case 3: return 'bg-emerald-500'
      case 4: return 'bg-emerald-400'
      default: return 'bg-gray-800'
    }
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <div className="h-full">
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Filters */}
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="text-gray-400 text-xs mb-1 block">Class</label>
                <select
                  value={selectedClass}
                  onChange={(e) => setSelectedClass(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  {classes.map((cls) => (
                    <option key={cls.id} value={cls.id}>{cls.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-gray-400 text-xs mb-1 block">Period</label>
                <select
                  value={days}
                  onChange={(e) => setDays(parseInt(e.target.value))}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-white"
                >
                  <option value={7}>Last 7 days</option>
                  <option value={14}>Last 14 days</option>
                  <option value={30}>Last 30 days</option>
                </select>
              </div>
            </div>

            {/* Engagement Overview */}
            {engagement && (
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
                <h3 className="text-white font-medium mb-4">Engagement Overview</h3>
                <div className="grid grid-cols-4 gap-4 mb-6">
                  <div className="text-center p-3 bg-gray-800/50 rounded-lg">
                    <p className="text-white text-2xl font-bold">{engagement.total_students}</p>
                    <p className="text-gray-500 text-xs">Total Students</p>
                  </div>
                  <div className="text-center p-3 bg-emerald-500/10 rounded-lg">
                    <p className="text-emerald-400 text-2xl font-bold">{engagement.engagement_distribution.high}</p>
                    <p className="text-gray-500 text-xs">High Engagement</p>
                  </div>
                  <div className="text-center p-3 bg-amber-500/10 rounded-lg">
                    <p className="text-amber-400 text-2xl font-bold">{engagement.engagement_distribution.medium}</p>
                    <p className="text-gray-500 text-xs">Medium</p>
                  </div>
                  <div className="text-center p-3 bg-red-500/10 rounded-lg">
                    <p className="text-red-400 text-2xl font-bold">{engagement.engagement_distribution.low}</p>
                    <p className="text-gray-500 text-xs">Low Engagement</p>
                  </div>
                </div>

                {/* Engagement Bar Chart */}
                <div className="mb-4">
                  <div className="flex h-4 rounded-full overflow-hidden bg-gray-800">
                    <div
                      className="bg-emerald-500"
                      style={{ width: `${(engagement.engagement_distribution.high / engagement.total_students) * 100}%` }}
                    ></div>
                    <div
                      className="bg-amber-500"
                      style={{ width: `${(engagement.engagement_distribution.medium / engagement.total_students) * 100}%` }}
                    ></div>
                    <div
                      className="bg-red-500"
                      style={{ width: `${(engagement.engagement_distribution.low / engagement.total_students) * 100}%` }}
                    ></div>
                  </div>
                </div>

                <p className="text-gray-400 text-sm">
                  Average: <span className="text-white font-medium">{engagement.avg_activities_per_student.toFixed(1)}</span> activities per student
                </p>
              </div>
            )}

            {/* Student Activity Table */}
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-800">
                <h3 className="text-white font-medium">Student Activity</h3>
              </div>
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-gray-400 text-sm font-medium">Student</th>
                    <th className="px-4 py-3 text-center text-gray-400 text-sm font-medium">Activities</th>
                    <th className="px-4 py-3 text-center text-gray-400 text-sm font-medium">Submissions</th>
                    <th className="px-4 py-3 text-center text-gray-400 text-sm font-medium">Engagement</th>
                    <th className="px-4 py-3 text-center text-gray-400 text-sm font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {engagementLoading ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                        <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                      </td>
                    </tr>
                  ) : engagement?.students.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                        No students found
                      </td>
                    </tr>
                  ) : (
                    engagement?.students.map((student) => (
                      <tr key={student.student_id} className="border-t border-gray-800 hover:bg-gray-800/30">
                        <td className="px-4 py-3">
                          <p className="text-white font-medium">{student.name}</p>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-white">{student.activity_count}</span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className="text-white">{student.submission_count}</span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <span className={`px-2 py-1 rounded-lg text-xs font-medium border ${getEngagementColor(student.engagement_level)}`}>
                            {student.engagement_level}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => setSelectedStudent(student.student_id)}
                            className="text-indigo-400 hover:text-indigo-300 text-sm"
                          >
                            View Heatmap
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Activity Heatmap */}
            {selectedStudent && (
              <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-white font-medium">Activity Heatmap</h3>
                  <button
                    onClick={() => setSelectedStudent(null)}
                    className="text-gray-400 hover:text-white text-sm"
                  >
                    Close
                  </button>
                </div>
                {heatmapLoading ? (
                  <div className="flex justify-center py-8">
                    <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                  </div>
                ) : (
                  <>
                    <div className="flex flex-wrap gap-1 mb-4">
                      {heatmap.map((day, i) => (
                        <div
                          key={i}
                          className={`w-3 h-3 rounded-sm ${getHeatmapColor(day.level)}`}
                          title={`${day.date}: ${day.count} activities`}
                        ></div>
                      ))}
                    </div>
                    <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
                      <span>Less</span>
                      <div className="w-3 h-3 rounded-sm bg-gray-800"></div>
                      <div className="w-3 h-3 rounded-sm bg-emerald-900"></div>
                      <div className="w-3 h-3 rounded-sm bg-emerald-700"></div>
                      <div className="w-3 h-3 rounded-sm bg-emerald-500"></div>
                      <div className="w-3 h-3 rounded-sm bg-emerald-400"></div>
                      <span>More</span>
                    </div>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Alerts Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-gray-900/50 border border-gray-800 rounded-xl">
              <div className="px-6 py-4 border-b border-gray-800">
                <h3 className="text-white font-medium flex items-center gap-2">
                  <svg className="w-5 h-5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Engagement Alerts
                </h3>
              </div>
              <div className="p-4 space-y-3 max-h-96 overflow-y-auto scrollbar-hide">
                {alerts.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-4">No active alerts</p>
                ) : (
                  alerts.map((alert) => (
                    <div key={alert.id} className="bg-gray-800/50 rounded-lg p-3">
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-white font-medium text-sm">{alert.student_name}</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </div>
                      <p className="text-gray-400 text-xs mb-2">{alert.message}</p>
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500 text-xs">
                          {new Date(alert.created_at).toLocaleDateString()}
                        </span>
                        <button
                          onClick={() => resolveAlert(alert.id)}
                          className="text-emerald-400 hover:text-emerald-300 text-xs"
                        >
                          Resolve
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
