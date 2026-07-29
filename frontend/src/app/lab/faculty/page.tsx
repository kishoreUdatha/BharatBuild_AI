'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import {
  Users, BookOpen, Brain, Code, Trophy, Clock, ArrowLeft,
  Sparkles, Search, Download, TrendingUp, TrendingDown,
  BarChart3, Target, Award, ChevronRight, AlertCircle
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface Lab {
  id: string
  name: string
  code: string
  branch: string
  semester: string
  total_topics: number
  total_mcqs: number
  total_coding_problems: number
}

interface StudentProgress {
  user_id: string
  full_name: string
  email: string
  roll_number?: string
  section?: string
  overall_progress: number
  mcq_score: number
  coding_score: number
  total_score: number
  topics_completed: number
  mcqs_attempted: number
  mcqs_correct: number
  problems_solved: number
  class_rank?: number
  last_activity?: string
}

interface LabAnalytics {
  total_enrolled: number
  active_students: number
  avg_progress: number
  avg_mcq_score: number
  avg_coding_score: number
  completion_rate: number
  top_performers: StudentProgress[]
  struggling_students: StudentProgress[]
}

export default function FacultyDashboardPage() {
  const router = useRouter()
  const [labs, setLabs] = useState<Lab[]>([])
  const [selectedLab, setSelectedLab] = useState<string>('')
  const [students, setStudents] = useState<StudentProgress[]>([])
  const [analytics, setAnalytics] = useState<LabAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState('total_score')

  useEffect(() => {
    fetchLabs()
  }, [])

  useEffect(() => {
    if (selectedLab) {
      fetchStudents()
      fetchAnalytics()
    }
  }, [selectedLab])

  const fetchLabs = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/lab/labs`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        setLabs(data)
        if (data.length > 0) {
          setSelectedLab(data[0].id)
        }
      }
    } catch (error) {
      console.error('Error fetching labs:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchStudents = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/lab/labs/${selectedLab}/students`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        const data = await response.json()
        setStudents(data)
      }
    } catch (error) {
      console.error('Error fetching students:', error)
    }
  }

  const fetchAnalytics = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/lab/labs/${selectedLab}/analytics`, {
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
    }
  }

  const exportToCSV = () => {
    const headers = ['Name', 'Email', 'Roll Number', 'Section', 'Progress', 'MCQ Score', 'Coding Score', 'Total Score', 'Rank']
    const rows = filteredStudents.map(s => [
      s.full_name,
      s.email,
      s.roll_number || '',
      s.section || '',
      `${s.overall_progress.toFixed(1)}%`,
      `${s.mcq_score.toFixed(1)}%`,
      `${s.coding_score.toFixed(1)}%`,
      `${s.total_score.toFixed(1)}%`,
      s.class_rank || ''
    ])

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `lab_progress_${selectedLab}.csv`
    a.click()
  }

  const filteredStudents = students
    .filter(s =>
      s.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.roll_number?.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name': return a.full_name.localeCompare(b.full_name)
        case 'progress': return b.overall_progress - a.overall_progress
        case 'mcq_score': return b.mcq_score - a.mcq_score
        case 'coding_score': return b.coding_score - a.coding_score
        case 'total_score': return b.total_score - a.total_score
        default: return 0
      }
    })

  const currentLab = labs.find(l => l.id === selectedLab)

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-purple-500/30 rounded-full animate-spin border-t-purple-500"></div>
            <Sparkles className="absolute inset-0 m-auto h-8 w-8 text-purple-400 animate-pulse" />
          </div>
          <p className="mt-4 text-purple-400 font-medium">Loading Dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl"></div>
      </div>
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none"></div>

      <div className="relative z-10 py-8 px-4">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <Link href="/lab" className="inline-flex items-center text-slate-400 hover:text-purple-400 mb-4 transition-colors">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Labs
              </Link>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                <Users className="h-8 w-8 text-purple-400" />
                Faculty Dashboard
              </h1>
              <p className="text-slate-400 mt-1">Track student progress and performance</p>
            </div>

            <div className="flex items-center gap-4">
              <Select value={selectedLab} onValueChange={setSelectedLab}>
                <SelectTrigger className="w-64 bg-slate-900/50 border-slate-700 text-white">
                  <SelectValue placeholder="Select Lab" />
                </SelectTrigger>
                <SelectContent className="bg-slate-800 border-slate-700">
                  {labs.map(lab => (
                    <SelectItem key={lab.id} value={lab.id} className="text-white hover:bg-slate-700">
                      {lab.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              <Button
                variant="outline"
                onClick={exportToCSV}
                className="border-purple-500/50 text-purple-400 hover:bg-purple-500/10"
              >
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
            </div>
          </div>

          {/* Lab Info */}
          {currentLab && (
            <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800 mb-6">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                    <BookOpen className="h-6 w-6 text-purple-400" />
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-white">{currentLab.name}</h2>
                    <p className="text-sm text-slate-400">{currentLab.code} | {currentLab.branch.toUpperCase()} - {currentLab.semester.replace('sem_', 'Semester ')}</p>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{currentLab.total_topics}</p>
                    <p className="text-xs text-slate-400">Topics</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{currentLab.total_mcqs}</p>
                    <p className="text-xs text-slate-400">MCQs</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xl font-bold text-white">{currentLab.total_coding_problems}</p>
                    <p className="text-xs text-slate-400">Problems</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Analytics Overview */}
          {analytics && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-4 text-center">
                  <Users className="h-6 w-6 text-cyan-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{analytics.total_enrolled}</p>
                  <p className="text-xs text-slate-400">Enrolled</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-4 text-center">
                  <Target className="h-6 w-6 text-green-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{analytics.active_students}</p>
                  <p className="text-xs text-slate-400">Active</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-4 text-center">
                  <BarChart3 className="h-6 w-6 text-purple-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{analytics.avg_progress.toFixed(1)}%</p>
                  <p className="text-xs text-slate-400">Avg Progress</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-4 text-center">
                  <Brain className="h-6 w-6 text-blue-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{analytics.avg_mcq_score.toFixed(1)}%</p>
                  <p className="text-xs text-slate-400">Avg MCQ Score</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-4 text-center">
                  <Code className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{analytics.avg_coding_score.toFixed(1)}%</p>
                  <p className="text-xs text-slate-400">Avg Coding</p>
                </CardContent>
              </Card>
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-4 text-center">
                  <Trophy className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{analytics.completion_rate.toFixed(1)}%</p>
                  <p className="text-xs text-slate-400">Completion</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Top Performers & Struggling Students */}
          {analytics && (
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-green-400" />
                    Top Performers
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analytics.top_performers.slice(0, 5).map((student, index) => (
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
                            <p className="text-xs text-slate-400">{student.roll_number || student.email}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-green-400 font-semibold">{student.total_score.toFixed(1)}%</p>
                          <p className="text-xs text-slate-400">{student.overall_progress.toFixed(0)}% progress</p>
                        </div>
                      </div>
                    ))}
                    {analytics.top_performers.length === 0 && (
                      <p className="text-slate-400 text-center py-4">No data yet</p>
                    )}
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <AlertCircle className="h-5 w-5 text-red-400" />
                    Need Attention
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {analytics.struggling_students.slice(0, 5).map((student) => (
                      <div key={student.user_id} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl border border-red-500/20">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-red-500/20 flex items-center justify-center">
                            <TrendingDown className="h-4 w-4 text-red-400" />
                          </div>
                          <div>
                            <p className="text-white font-medium">{student.full_name}</p>
                            <p className="text-xs text-slate-400">{student.roll_number || student.email}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="text-red-400 font-semibold">{student.total_score.toFixed(1)}%</p>
                          <p className="text-xs text-slate-400">{student.overall_progress.toFixed(0)}% progress</p>
                        </div>
                      </div>
                    ))}
                    {analytics.struggling_students.length === 0 && (
                      <p className="text-slate-400 text-center py-4">No struggling students</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Student List */}
          <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">All Students ({filteredStudents.length})</CardTitle>
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <Input
                      placeholder="Search students..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-10 w-64 bg-slate-800/50 border-slate-700 text-white"
                    />
                  </div>
                  <Select value={sortBy} onValueChange={setSortBy}>
                    <SelectTrigger className="w-40 bg-slate-800/50 border-slate-700 text-white">
                      <SelectValue placeholder="Sort by" />
                    </SelectTrigger>
                    <SelectContent className="bg-slate-800 border-slate-700">
                      <SelectItem value="total_score" className="text-white">Total Score</SelectItem>
                      <SelectItem value="progress" className="text-white">Progress</SelectItem>
                      <SelectItem value="mcq_score" className="text-white">MCQ Score</SelectItem>
                      <SelectItem value="coding_score" className="text-white">Coding Score</SelectItem>
                      <SelectItem value="name" className="text-white">Name</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-800">
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Rank</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Student</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Section</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Progress</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">MCQ</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Coding</th>
                      <th className="text-left py-3 px-4 text-slate-400 font-medium">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredStudents.map((student, index) => (
                      <tr key={student.user_id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                        <td className="py-3 px-4">
                          <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            student.class_rank === 1 ? 'bg-amber-500 text-white' :
                            student.class_rank === 2 ? 'bg-slate-400 text-white' :
                            student.class_rank === 3 ? 'bg-amber-700 text-white' :
                            'bg-slate-700 text-slate-400'
                          }`}>
                            {student.class_rank || index + 1}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div>
                            <p className="text-white font-medium">{student.full_name}</p>
                            <p className="text-xs text-slate-400">{student.roll_number || student.email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-400">{student.section || '-'}</td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <Progress value={student.overall_progress} className="w-20 h-2 bg-slate-800" />
                            <span className="text-cyan-400 text-sm">{student.overall_progress.toFixed(0)}%</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-sm ${student.mcq_score >= 70 ? 'text-green-400' : student.mcq_score >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                            {student.mcq_score.toFixed(1)}%
                          </span>
                          <span className="text-xs text-slate-500 ml-1">({student.mcqs_correct}/{student.mcqs_attempted})</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-sm ${student.coding_score >= 70 ? 'text-green-400' : student.coding_score >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                            {student.coding_score.toFixed(1)}%
                          </span>
                          <span className="text-xs text-slate-500 ml-1">({student.problems_solved} solved)</span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`font-semibold ${student.total_score >= 70 ? 'text-green-400' : student.total_score >= 40 ? 'text-amber-400' : 'text-red-400'}`}>
                            {student.total_score.toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filteredStudents.length === 0 && (
                  <div className="text-center py-12">
                    <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                    <p className="text-slate-400">No students found</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
