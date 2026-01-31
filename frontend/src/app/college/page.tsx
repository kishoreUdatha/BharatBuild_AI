'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Users, GraduationCap, BookOpen, Building2, ChevronRight,
  TrendingUp, AlertTriangle, CheckCircle2, Clock, FileText,
  BarChart3, PieChart, Activity, Bell, Settings, Search,
  Filter, Download, Eye, Edit, Trash2, Plus, RefreshCw,
  Shield, Brain, Target, Award, Calendar, MessageSquare
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface DashboardStats {
  overview: {
    total_students: number
    total_faculty: number
    total_departments: number
  }
  projects: {
    total: number
    active: number
    completed: number
    pending_review: number
  }
  compliance: {
    avg_plagiarism_score: number
    avg_ai_detection: number
    passing_plagiarism: number
    passing_ai: number
  }
  departments: Array<{
    name: string
    code: string
    students: number
    faculty: number
    projects: number
  }>
}

export default function CollegeManagementPage() {
  const [activeTab, setActiveTab] = useState('principal')
  const [loading, setLoading] = useState(true)
  const [principalData, setPrincipalData] = useState<any>(null)
  const [hodData, setHodData] = useState<any>(null)
  const [lecturerData, setLecturerData] = useState<any>(null)

  useEffect(() => {
    loadDashboardData()
  }, [activeTab])

  const loadDashboardData = async () => {
    setLoading(true)
    try {
      if (activeTab === 'principal') {
        const res = await fetch(`${API_URL}/college/test/principal-dashboard`)
        const data = await res.json()
        setPrincipalData(data)
      } else if (activeTab === 'hod') {
        const res = await fetch(`${API_URL}/college/test/hod-dashboard`)
        const data = await res.json()
        setHodData(data)
      } else if (activeTab === 'lecturer') {
        const res = await fetch(`${API_URL}/college/test/lecturer-dashboard`)
        const data = await res.json()
        setLecturerData(data)
      }
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  const StatCard = ({ icon: Icon, label, value, subValue, color = 'cyan' }: any) => (
    <Card className="bg-slate-800/50 border-slate-700">
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-slate-400 text-sm">{label}</p>
            <p className={`text-2xl font-bold text-${color}-400`}>{value}</p>
            {subValue && <p className="text-slate-500 text-xs">{subValue}</p>}
          </div>
          <div className={`p-3 rounded-lg bg-${color}-500/20`}>
            <Icon className={`h-6 w-6 text-${color}-400`} />
          </div>
        </div>
      </CardContent>
    </Card>
  )

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Building2 className="h-7 w-7 text-cyan-400" />
              College Management Dashboard
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Manage students, faculty, and project oversight
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
              <Bell className="h-4 w-4 mr-2" />
              Notifications
            </Button>
            <Button variant="outline" size="sm" className="border-slate-700 text-slate-300">
              <Settings className="h-4 w-4 mr-2" />
              Settings
            </Button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        {/* Role Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-slate-900 border border-slate-800 p-1">
            <TabsTrigger
              value="principal"
              className="data-[state=active]:bg-cyan-500 data-[state=active]:text-white"
            >
              <Award className="h-4 w-4 mr-2" />
              Principal View
            </TabsTrigger>
            <TabsTrigger
              value="hod"
              className="data-[state=active]:bg-purple-500 data-[state=active]:text-white"
            >
              <Users className="h-4 w-4 mr-2" />
              HOD View
            </TabsTrigger>
            <TabsTrigger
              value="lecturer"
              className="data-[state=active]:bg-amber-500 data-[state=active]:text-white text-black"
            >
              <GraduationCap className="h-4 w-4 mr-2" />
              Lecturer View
            </TabsTrigger>
          </TabsList>

          {/* Principal Dashboard */}
          <TabsContent value="principal" className="space-y-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-8 w-8 text-cyan-400 animate-spin" />
              </div>
            ) : principalData ? (
              <>
                {/* Overview Stats */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Card className="bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border-cyan-500/30">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-slate-300 text-sm">Total Students</p>
                          <p className="text-3xl font-bold text-white">{principalData.stats.overview.total_students}</p>
                        </div>
                        <GraduationCap className="h-10 w-10 text-cyan-400" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 border-purple-500/30">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-slate-300 text-sm">Total Faculty</p>
                          <p className="text-3xl font-bold text-white">{principalData.stats.overview.total_faculty}</p>
                        </div>
                        <Users className="h-10 w-10 text-purple-400" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="bg-gradient-to-br from-amber-500/20 to-orange-500/20 border-amber-500/30">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-slate-300 text-sm">Departments</p>
                          <p className="text-3xl font-bold text-white">{principalData.stats.overview.total_departments}</p>
                        </div>
                        <Building2 className="h-10 w-10 text-amber-400" />
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="bg-gradient-to-br from-green-500/20 to-emerald-500/20 border-green-500/30">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-slate-300 text-sm">Active Projects</p>
                          <p className="text-3xl font-bold text-white">{principalData.stats.projects.active}</p>
                        </div>
                        <FileText className="h-10 w-10 text-green-400" />
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Compliance Overview */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader>
                      <CardTitle className="text-white flex items-center gap-2">
                        <Shield className="h-5 w-5 text-cyan-400" />
                        Plagiarism Compliance
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Average Score</span>
                          <span className="text-2xl font-bold text-green-400">
                            {principalData.stats.compliance.avg_plagiarism_score}%
                          </span>
                        </div>
                        <Progress value={100 - principalData.stats.compliance.avg_plagiarism_score} className="h-3" />
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-500">Threshold: &lt;10%</span>
                          <Badge className="bg-green-500/20 text-green-400">
                            {principalData.stats.compliance.passing_plagiarism}% Passing
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="bg-slate-900 border-slate-800">
                    <CardHeader>
                      <CardTitle className="text-white flex items-center gap-2">
                        <Brain className="h-5 w-5 text-purple-400" />
                        AI Detection Compliance
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Average Score</span>
                          <span className="text-2xl font-bold text-green-400">
                            {principalData.stats.compliance.avg_ai_detection}%
                          </span>
                        </div>
                        <Progress value={100 - principalData.stats.compliance.avg_ai_detection} className="h-3" />
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-slate-500">Threshold: &lt;20%</span>
                          <Badge className="bg-green-500/20 text-green-400">
                            {principalData.stats.compliance.passing_ai}% Passing
                          </Badge>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Departments Table */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Building2 className="h-5 w-5 text-cyan-400" />
                        Department Overview
                      </span>
                      <Button size="sm" className="bg-cyan-500 hover:bg-cyan-600">
                        <Plus className="h-4 w-4 mr-2" />
                        Add Department
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b border-slate-800">
                            <th className="text-left py-3 px-4 text-slate-400 font-medium">Department</th>
                            <th className="text-left py-3 px-4 text-slate-400 font-medium">Code</th>
                            <th className="text-center py-3 px-4 text-slate-400 font-medium">Students</th>
                            <th className="text-center py-3 px-4 text-slate-400 font-medium">Faculty</th>
                            <th className="text-center py-3 px-4 text-slate-400 font-medium">Projects</th>
                            <th className="text-center py-3 px-4 text-slate-400 font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {principalData.departments.map((dept: any, i: number) => (
                            <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                              <td className="py-3 px-4 text-white font-medium">{dept.name}</td>
                              <td className="py-3 px-4">
                                <Badge className="bg-slate-700 text-slate-300">{dept.code}</Badge>
                              </td>
                              <td className="py-3 px-4 text-center text-slate-300">{dept.students}</td>
                              <td className="py-3 px-4 text-center text-slate-300">{dept.faculty}</td>
                              <td className="py-3 px-4 text-center text-slate-300">{dept.projects}</td>
                              <td className="py-3 px-4 text-center">
                                <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                                  <Eye className="h-4 w-4" />
                                </Button>
                                <Button variant="ghost" size="sm" className="text-slate-400 hover:text-white">
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <p className="text-slate-400">Failed to load dashboard data</p>
            )}
          </TabsContent>

          {/* HOD Dashboard */}
          <TabsContent value="hod" className="space-y-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-8 w-8 text-purple-400 animate-spin" />
              </div>
            ) : hodData ? (
              <>
                {/* Department Info */}
                <div className="bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-500/30 rounded-lg p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-bold text-white">{hodData.department.name}</h2>
                      <p className="text-slate-400">Department Code: {hodData.department.code}</p>
                    </div>
                    <Badge className="bg-purple-500 text-white text-lg px-4 py-1">HOD</Badge>
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <StatCard icon={GraduationCap} label="Total Students" value={hodData.stats.overview.total_students} color="cyan" />
                  <StatCard icon={Users} label="Faculty Members" value={hodData.stats.overview.total_faculty} color="purple" />
                  <StatCard icon={BookOpen} label="Sections" value={hodData.stats.overview.sections} color="amber" />
                  <StatCard icon={FileText} label="Active Projects" value={hodData.stats.overview.active_projects} color="green" />
                </div>

                {/* Projects by Phase */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <BarChart3 className="h-5 w-5 text-purple-400" />
                      Projects by Phase
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                      {Object.entries(hodData.stats.projects_by_phase).map(([phase, count]: [string, any]) => (
                        <div key={phase} className="text-center p-4 bg-slate-800/50 rounded-lg">
                          <p className="text-2xl font-bold text-white">{count}</p>
                          <p className="text-slate-400 text-sm capitalize">{phase}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Faculty List */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <Users className="h-5 w-5 text-purple-400" />
                      Faculty Members
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {hodData.faculty.map((f: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                              <span className="text-purple-400 font-medium">{f.name.charAt(0)}</span>
                            </div>
                            <div>
                              <p className="text-white font-medium">{f.name}</p>
                              <p className="text-slate-400 text-sm">{f.students} students guided</p>
                            </div>
                          </div>
                          {f.pending_reviews > 0 && (
                            <Badge className="bg-amber-500/20 text-amber-400">
                              {f.pending_reviews} pending reviews
                            </Badge>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <p className="text-slate-400">Failed to load dashboard data</p>
            )}
          </TabsContent>

          {/* Lecturer Dashboard */}
          <TabsContent value="lecturer" className="space-y-6">
            {loading ? (
              <div className="flex items-center justify-center h-64">
                <RefreshCw className="h-8 w-8 text-amber-400 animate-spin" />
              </div>
            ) : lecturerData ? (
              <>
                {/* Profile Header */}
                <div className="bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-4">
                    <div className="w-16 h-16 rounded-full bg-amber-500/20 flex items-center justify-center">
                      <GraduationCap className="h-8 w-8 text-amber-400" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-white">{lecturerData.profile.name}</h2>
                      <p className="text-slate-400">{lecturerData.profile.designation} - {lecturerData.profile.department}</p>
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardContent className="p-4 text-center">
                      <p className="text-3xl font-bold text-cyan-400">{lecturerData.stats.students_guided}</p>
                      <p className="text-slate-400">Students Guided</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardContent className="p-4 text-center">
                      <p className="text-3xl font-bold text-amber-400">{lecturerData.stats.pending_reviews}</p>
                      <p className="text-slate-400">Pending Reviews</p>
                    </CardContent>
                  </Card>
                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardContent className="p-4 text-center">
                      <p className="text-3xl font-bold text-green-400">{lecturerData.stats.completed_reviews}</p>
                      <p className="text-slate-400">Completed Reviews</p>
                    </CardContent>
                  </Card>
                </div>

                {/* Students List */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <GraduationCap className="h-5 w-5 text-amber-400" />
                      My Students
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {lecturerData.students.map((s: any, i: number) => (
                        <div key={i} className="p-4 bg-slate-800/50 rounded-lg">
                          <div className="flex items-center justify-between mb-3">
                            <div>
                              <p className="text-white font-medium">{s.name}</p>
                              <p className="text-slate-400 text-sm">{s.roll} - {s.project}</p>
                            </div>
                            <Badge className={
                              s.phase === 'development' ? 'bg-blue-500/20 text-blue-400' :
                              s.phase === 'testing' ? 'bg-purple-500/20 text-purple-400' :
                              'bg-slate-500/20 text-slate-400'
                            }>
                              {s.phase}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <Progress value={s.progress} className="flex-1 h-2" />
                            <span className="text-slate-400 text-sm">{s.progress}%</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Pending Reviews */}
                <Card className="bg-slate-900 border-slate-800">
                  <CardHeader>
                    <CardTitle className="text-white flex items-center gap-2">
                      <Clock className="h-5 w-5 text-amber-400" />
                      Pending Reviews
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {lecturerData.pending_reviews.map((r: any, i: number) => (
                        <div key={i} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                          <div>
                            <p className="text-white font-medium">{r.student}</p>
                            <p className="text-slate-400 text-sm">{r.phase} - Submitted {r.submitted}</p>
                          </div>
                          <Button size="sm" className="bg-amber-500 hover:bg-amber-600 text-black">
                            Review
                          </Button>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            ) : (
              <p className="text-slate-400">Failed to load dashboard data</p>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
