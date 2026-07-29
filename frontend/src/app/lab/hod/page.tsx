'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import {
  Users, BookOpen, Brain, Code, Trophy, Building2, ArrowLeft,
  Sparkles, Download, TrendingUp, BarChart3, Target, Award,
  GraduationCap, Layers, PieChart, Activity
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface DepartmentAnalytics {
  total_labs: number
  total_students: number
  total_topics: number
  total_mcqs: number
  total_problems: number
  active_students: number
  avg_progress: number
  avg_mcq_score: number
  avg_coding_score: number
  completion_rate: number
  labs_by_semester: Record<string, number>
  performance_by_lab: Array<{
    lab_id: string
    lab_name: string
    enrolled: number
    avg_progress: number
    avg_score: number
    completion_rate: number
  }>
  top_students: Array<{
    user_id: string
    full_name: string
    email: string
    labs_completed: number
    avg_score: number
  }>
  faculty_performance: Array<{
    faculty_id: string
    faculty_name: string
    labs_assigned: number
    total_students: number
    avg_student_score: number
  }>
}

const branchOptions = [
  { value: 'all', label: 'All Branches' },
  { value: 'cse', label: 'Computer Science' },
  { value: 'it', label: 'Information Technology' },
  { value: 'ece', label: 'Electronics & Comm' },
  { value: 'eee', label: 'Electrical' },
  { value: 'me', label: 'Mechanical' },
  { value: 'ce', label: 'Civil' },
  { value: 'ai_ml', label: 'AI & ML' },
  { value: 'data_science', label: 'Data Science' }
]

export default function HODDashboardPage() {
  const router = useRouter()
  const [selectedBranch, setSelectedBranch] = useState('all')
  const [analytics, setAnalytics] = useState<DepartmentAnalytics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAnalytics()
  }, [selectedBranch])

  const fetchAnalytics = async () => {
    try {
      setLoading(true)
      const token = localStorage.getItem('token')
      const params = new URLSearchParams()
      if (selectedBranch !== 'all') {
        params.append('branch', selectedBranch)
      }

      const response = await fetch(`${API_URL}/lab/department/analytics?${params}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        setAnalytics(data)
      }
    } catch (error) {
      console.error('Error fetching analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  const exportReport = () => {
    // Generate a comprehensive report
    const report = {
      generated_at: new Date().toISOString(),
      branch: selectedBranch === 'all' ? 'All Branches' : selectedBranch.toUpperCase(),
      analytics: analytics
    }

    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `department_report_${selectedBranch}_${new Date().toISOString().split('T')[0]}.json`
    a.click()
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-amber-500/30 rounded-full animate-spin border-t-amber-500"></div>
            <Sparkles className="absolute inset-0 m-auto h-8 w-8 text-amber-400 animate-pulse" />
          </div>
          <p className="mt-4 text-amber-400 font-medium">Loading Department Analytics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-amber-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl"></div>
      </div>
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none"></div>

      <div className="relative z-10 py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <Link href="/lab" className="inline-flex items-center text-slate-400 hover:text-amber-400 mb-4 transition-colors">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Labs
              </Link>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <Building2 className="h-8 w-8 text-amber-400" />
                HOD Dashboard
              </h1>
              <p className="text-slate-400 mt-1">Department-wide analytics and insights</p>
            </div>

            <div className="flex items-center gap-4">
              <Select value={selectedBranch} onValueChange={setSelectedBranch}>
                <SelectTrigger className="w-56 bg-slate-900/50 border-slate-700 text-white">
                  <SelectValue placeholder="Select Branch" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {branchOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value} className="text-white hover:bg-slate-700">
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                onClick={exportReport}
                className="border-amber-500/50 text-amber-400 hover:bg-amber-500/10"
              >
                <Download className="h-4 w-4 mr-2" />
                Export Report
              </Button>
            </div>
          </div>

          {analytics && (
            <>
              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-4 text-center">
                    <BookOpen className="h-6 w-6 text-cyan-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{analytics.total_labs}</p>
                    <p className="text-xs text-slate-400">Total Labs</p>
                  </CardContent>
                </Card>
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-4 text-center">
                    <Users className="h-6 w-6 text-green-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{analytics.total_students}</p>
                    <p className="text-xs text-slate-400">Total Students</p>
                  </CardContent>
                </Card>
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-4 text-center">
                    <Activity className="h-6 w-6 text-purple-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{analytics.active_students}</p>
                    <p className="text-xs text-slate-400">Active Students</p>
                  </CardContent>
                </Card>
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-4 text-center">
                    <BarChart3 className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{analytics.avg_progress.toFixed(1)}%</p>
                    <p className="text-xs text-slate-400">Avg Progress</p>
                  </CardContent>
                </Card>
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-4 text-center">
                    <Trophy className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                    <p className="text-2xl font-bold text-white">{analytics.completion_rate.toFixed(1)}%</p>
                    <p className="text-xs text-slate-400">Completion Rate</p>
                  </CardContent>
                </Card>
              </div>

              {/* Content Stats */}
              <div className="grid grid-cols-3 gap-4 mb-8">
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-3xl font-bold text-white">{analytics.total_topics}</p>
                        <p className="text-sm text-slate-400">Topics</p>
                      </div>
                      <div className="w-12 h-12 bg-cyan-500/20 rounded-xl flex items-center justify-center">
                        <Layers className="h-6 w-6 text-cyan-400" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-3xl font-bold text-white">{analytics.total_mcqs}</p>
                        <p className="text-sm text-slate-400">MCQ Questions</p>
                        <p className="text-xs text-cyan-400 mt-1">Avg Score: {analytics.avg_mcq_score.toFixed(1)}%</p>
                      </div>
                      <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                        <Brain className="h-6 w-6 text-purple-400" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-3xl font-bold text-white">{analytics.total_problems}</p>
                        <p className="text-sm text-slate-400">Coding Problems</p>
                        <p className="text-xs text-green-400 mt-1">Avg Score: {analytics.avg_coding_score.toFixed(1)}%</p>
                      </div>
                      <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center">
                        <Code className="h-6 w-6 text-green-400" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Lab Performance */}
              <div className="grid md:grid-cols-2 gap-6 mb-8">
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <PieChart className="h-5 w-5 text-cyan-400" />
                      Lab Performance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {analytics.performance_by_lab.slice(0, 6).map((lab) => (
                        <div key={lab.lab_id} className="p-4 bg-slate-800/50 rounded-xl">
                          <div className="flex items-center justify-between mb-2">
                            <h4 className="text-white font-medium">{lab.lab_name}</h4>
                            <span className="text-xs text-slate-400">{lab.enrolled} students</span>
                          </div>
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div>
                              <p className="text-cyan-400 font-semibold">{lab.avg_progress.toFixed(0)}%</p>
                              <p className="text-xs text-slate-500">Progress</p>
                            </div>
                            <div>
                              <p className="text-purple-400 font-semibold">{lab.avg_score.toFixed(0)}%</p>
                              <p className="text-xs text-slate-500">Avg Score</p>
                            </div>
                            <div>
                              <p className="text-green-400 font-semibold">{lab.completion_rate.toFixed(0)}%</p>
                              <p className="text-xs text-slate-500">Completion</p>
                            </div>
                          </div>
                        </div>
                      ))}
                      {analytics.performance_by_lab.length === 0 && (
                        <p className="text-slate-400 text-center py-8">No lab data available</p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Labs by Semester */}
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <GraduationCap className="h-5 w-5 text-purple-400" />
                      Labs by Semester
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {Object.entries(analytics.labs_by_semester).map(([semester, count]) => (
                        <div key={semester} className="flex items-center gap-4">
                          <span className="w-24 text-slate-400 text-sm">
                            {semester.replace('sem_', 'Semester ')}
                          </span>
                          <div className="flex-1">
                            <Progress
                              value={(count / Math.max(...Object.values(analytics.labs_by_semester))) * 100}
                              className="h-3 bg-slate-800"
                            />
                          </div>
                          <span className="w-8 text-white text-sm font-semibold">{count}</span>
                        </div>
                      ))}
                      {Object.keys(analytics.labs_by_semester).length === 0 && (
                        <p className="text-slate-400 text-center py-8">No data available</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Top Students & Faculty Performance */}
              <div className="grid md:grid-cols-2 gap-6">
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <Award className="h-5 w-5 text-amber-400" />
                      Top Performing Students
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {analytics.top_students.slice(0, 5).map((student, index) => (
                        <div key={student.user_id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl">
                          <div className="flex items-center gap-3">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                              index === 0 ? 'bg-amber-500 text-white' :
                              index === 1 ? 'bg-slate-400 text-white' :
                              index === 2 ? 'bg-amber-700 text-white' :
                              'bg-slate-700 text-slate-400'
                            }`}>
                              {index + 1}
                            </div>
                            <div>
                              <p className="text-white font-medium">{student.full_name}</p>
                              <p className="text-xs text-slate-400">{student.labs_completed} labs completed</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="text-green-400 font-semibold">{student.avg_score.toFixed(1)}%</p>
                            <p className="text-xs text-slate-400">Avg Score</p>
                          </div>
                        </div>
                      ))}
                      {analytics.top_students.length === 0 && (
                        <p className="text-slate-400 text-center py-8">No student data yet</p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <Users className="h-5 w-5 text-cyan-400" />
                      Faculty Performance
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {analytics.faculty_performance.map((faculty, index) => (
                        <div key={faculty.faculty_id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-cyan-500/20 flex items-center justify-center">
                              <Users className="h-5 w-5 text-cyan-400" />
                            </div>
                            <div>
                              <p className="text-white font-medium">{faculty.faculty_name}</p>
                              <p className="text-xs text-slate-400">
                                {faculty.labs_assigned} labs | {faculty.total_students} students
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className={`font-semibold ${
                              faculty.avg_student_score >= 70 ? 'text-green-400' :
                              faculty.avg_student_score >= 50 ? 'text-amber-400' : 'text-red-400'
                            }`}>
                              {faculty.avg_student_score.toFixed(1)}%
                            </p>
                            <p className="text-xs text-slate-400">Student Avg</p>
                          </div>
                        </div>
                      ))}
                      {analytics.faculty_performance.length === 0 && (
                        <p className="text-slate-400 text-center py-8">No faculty data yet</p>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}

          {!analytics && !loading && (
            <div className="text-center py-16">
              <Building2 className="h-16 w-16 text-slate-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">No Analytics Available</h3>
              <p className="text-slate-400">Analytics data will appear once students start using labs.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
