'use client'

import { useState } from 'react'
import {
  BookOpen,
  Upload,
  FileText,
  Video,
  File,
  Plus,
  Search,
  Filter,
  Calendar,
  Clock,
  Users,
  BarChart3,
  Eye,
  Download,
  Lock,
  Unlock,
  Edit,
  Trash2,
  Copy,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  HelpCircle,
  X,
  Settings,
  Tag,
  Layers,
  Target,
  Award,
  TrendingUp,
  Play,
  Pause,
  RefreshCw,
  Bell,
  ExternalLink
} from 'lucide-react'

interface Subject {
  id: string
  name: string
  code: string
  semester: number
  credits: number
  type: 'theory' | 'lab' | 'theory+lab'
  students_count: number
  content_count: number
  assignments_count: number
  quizzes_count: number
}

interface Content {
  id: string
  title: string
  type: 'pdf' | 'ppt' | 'video' | 'doc'
  unit: string
  topic: string
  version: string
  visibility: 'view_only' | 'downloadable'
  uploaded_at: string
  views: number
  downloads: number
}

interface Assignment {
  id: string
  title: string
  type: 'theory' | 'coding' | 'case_study' | 'research'
  due_date: string
  max_marks: number
  submissions: number
  total_students: number
  status: 'draft' | 'active' | 'closed'
  plagiarism_check: boolean
}

interface Quiz {
  id: string
  title: string
  questions_count: number
  duration_minutes: number
  difficulty: 'easy' | 'medium' | 'hard'
  attempts: number
  avg_score: number
  status: 'draft' | 'scheduled' | 'active' | 'completed'
  scheduled_at?: string
}

export default function SubjectsPage() {
  const [selectedSubject, setSelectedSubject] = useState<Subject | null>(null)
  const [activeTab, setActiveTab] = useState<'content' | 'assignments' | 'quizzes' | 'schedule' | 'analytics'>('content')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showAssignmentModal, setShowAssignmentModal] = useState(false)
  const [showQuizModal, setShowQuizModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')

  // Mock data
  const subjects: Subject[] = [
    { id: '1', name: 'Data Structures', code: 'CS301', semester: 3, credits: 4, type: 'theory+lab', students_count: 65, content_count: 24, assignments_count: 8, quizzes_count: 5 },
    { id: '2', name: 'Database Systems', code: 'CS302', semester: 3, credits: 4, type: 'theory+lab', students_count: 68, content_count: 18, assignments_count: 6, quizzes_count: 4 },
    { id: '3', name: 'Operating Systems', code: 'CS303', semester: 3, credits: 3, type: 'theory', students_count: 72, content_count: 20, assignments_count: 5, quizzes_count: 3 },
    { id: '4', name: 'Computer Networks', code: 'CS401', semester: 4, credits: 4, type: 'theory+lab', students_count: 60, content_count: 22, assignments_count: 7, quizzes_count: 4 },
    { id: '5', name: 'Software Engineering', code: 'CS402', semester: 4, credits: 3, type: 'theory', students_count: 58, content_count: 16, assignments_count: 4, quizzes_count: 2 },
  ]

  const contents: Content[] = [
    { id: '1', title: 'Introduction to Data Structures', type: 'pdf', unit: 'Unit 1', topic: 'Basics', version: 'v2', visibility: 'downloadable', uploaded_at: '2026-01-15', views: 156, downloads: 89 },
    { id: '2', title: 'Arrays and Linked Lists', type: 'ppt', unit: 'Unit 1', topic: 'Linear DS', version: 'v1', visibility: 'view_only', uploaded_at: '2026-01-18', views: 142, downloads: 0 },
    { id: '3', title: 'Stack Operations Demo', type: 'video', unit: 'Unit 2', topic: 'Stacks', version: 'v1', visibility: 'view_only', uploaded_at: '2026-01-20', views: 198, downloads: 0 },
    { id: '4', title: 'Queue Implementation', type: 'pdf', unit: 'Unit 2', topic: 'Queues', version: 'v3', visibility: 'downloadable', uploaded_at: '2026-01-22', views: 134, downloads: 78 },
    { id: '5', title: 'Tree Traversal Algorithms', type: 'ppt', unit: 'Unit 3', topic: 'Trees', version: 'v1', visibility: 'downloadable', uploaded_at: '2026-01-25', views: 112, downloads: 65 },
  ]

  const assignments: Assignment[] = [
    { id: '1', title: 'Implement Stack using Arrays', type: 'coding', due_date: '2026-02-05', max_marks: 20, submissions: 58, total_students: 65, status: 'active', plagiarism_check: true },
    { id: '2', title: 'Linked List Operations Case Study', type: 'case_study', due_date: '2026-02-10', max_marks: 30, submissions: 45, total_students: 65, status: 'active', plagiarism_check: true },
    { id: '3', title: 'Binary Tree Applications', type: 'theory', due_date: '2026-02-15', max_marks: 25, submissions: 0, total_students: 65, status: 'draft', plagiarism_check: false },
    { id: '4', title: 'Research on Graph Algorithms', type: 'research', due_date: '2026-02-20', max_marks: 40, submissions: 12, total_students: 65, status: 'active', plagiarism_check: true },
  ]

  const quizzes: Quiz[] = [
    { id: '1', title: 'Arrays & Linked Lists Quiz', questions_count: 20, duration_minutes: 30, difficulty: 'easy', attempts: 62, avg_score: 78, status: 'completed' },
    { id: '2', title: 'Stacks & Queues Assessment', questions_count: 25, duration_minutes: 40, difficulty: 'medium', attempts: 58, avg_score: 72, status: 'completed' },
    { id: '3', title: 'Trees Mid-Semester Test', questions_count: 30, duration_minutes: 45, difficulty: 'hard', attempts: 0, avg_score: 0, status: 'scheduled', scheduled_at: '2026-02-08 10:00' },
    { id: '4', title: 'Quick Revision Quiz', questions_count: 15, duration_minutes: 20, difficulty: 'easy', attempts: 0, avg_score: 0, status: 'draft' },
  ]

  const getContentIcon = (type: string) => {
    switch (type) {
      case 'pdf': return <FileText className="w-4 h-4 text-red-500" />
      case 'ppt': return <File className="w-4 h-4 text-orange-500" />
      case 'video': return <Video className="w-4 h-4 text-blue-500" />
      default: return <File className="w-4 h-4 text-gray-500" />
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-100 text-green-700'
      case 'completed': return 'bg-blue-100 text-blue-700'
      case 'scheduled': return 'bg-purple-100 text-purple-700'
      case 'draft': return 'bg-gray-100 text-gray-700'
      case 'closed': return 'bg-red-100 text-red-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  const filteredSubjects = subjects.filter(s =>
    s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.code.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Left Panel - Subject List */}
      <div className="w-72 border-r border-gray-700 bg-gray-800 flex flex-col">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-lg font-semibold text-white mb-3">My Subjects</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search subjects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-600 bg-gray-700 text-white rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-400"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto scrollbar-hide">
          {filteredSubjects.map((subject) => (
            <button
              key={subject.id}
              onClick={() => setSelectedSubject(subject)}
              className={`w-full p-4 text-left border-b border-gray-700 hover:bg-gray-700 transition-colors ${
                selectedSubject?.id === subject.id ? 'bg-blue-900/50 border-l-4 border-l-blue-500' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-white">{subject.code}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  subject.type === 'theory+lab' ? 'bg-purple-100 text-purple-700' :
                  subject.type === 'theory' ? 'bg-blue-100 text-blue-700' :
                  'bg-green-100 text-green-700'
                }`}>
                  {subject.type === 'theory+lab' ? 'T+L' : subject.type === 'theory' ? 'T' : 'L'}
                </span>
              </div>
              <p className="text-sm text-gray-300 mb-2">{subject.name}</p>
              <div className="flex items-center gap-3 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                  <Users className="w-3 h-3" />
                  {subject.students_count}
                </span>
                <span className="flex items-center gap-1">
                  <FileText className="w-3 h-3" />
                  {subject.content_count}
                </span>
                <span className="flex items-center gap-1">
                  <Target className="w-3 h-3" />
                  {subject.assignments_count}
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Panel */}
      <div className="flex-1 flex flex-col bg-gray-900">
        {selectedSubject ? (
          <>
            {/* Subject Header */}
            <div className="bg-gray-800 border-b border-gray-700 p-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h1 className="text-xl font-semibold text-white">{selectedSubject.name}</h1>
                  <p className="text-sm text-gray-400">
                    {selectedSubject.code} | Semester {selectedSubject.semester} | {selectedSubject.credits} Credits | {selectedSubject.students_count} Students
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-gray-700 rounded-lg text-gray-400">
                    <Bell className="w-5 h-5" />
                  </button>
                  <button className="p-2 hover:bg-gray-700 rounded-lg text-gray-400">
                    <Settings className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* Tabs */}
              <div className="flex gap-1">
                {[
                  { id: 'content', label: 'Content', icon: BookOpen },
                  { id: 'assignments', label: 'Assignments', icon: FileText },
                  { id: 'quizzes', label: 'Quizzes', icon: HelpCircle },
                  { id: 'schedule', label: 'Schedule', icon: Calendar },
                  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      activeTab === tab.id
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                    }`}
                  >
                    <tab.icon className="w-4 h-4" />
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto scrollbar-hide p-6">
              {activeTab === 'content' && (
                <div>
                  {/* Content Actions */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <select className="text-sm border border-gray-600 rounded-lg px-3 py-2 bg-gray-700 text-white">
                        <option value="">All Units</option>
                        <option value="1">Unit 1</option>
                        <option value="2">Unit 2</option>
                        <option value="3">Unit 3</option>
                        <option value="4">Unit 4</option>
                        <option value="5">Unit 5</option>
                      </select>
                      <select className="text-sm border border-gray-600 rounded-lg px-3 py-2 bg-gray-700 text-white">
                        <option value="">All Types</option>
                        <option value="pdf">PDF</option>
                        <option value="ppt">PPT</option>
                        <option value="video">Video</option>
                      </select>
                    </div>
                    <button
                      onClick={() => setShowUploadModal(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
                    >
                      <Upload className="w-4 h-4" />
                      Upload Content
                    </button>
                  </div>

                  {/* Content Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {contents.map((content) => (
                      <div key={content.id} className="bg-gray-800 rounded-xl border border-gray-700 p-4 hover:border-gray-600 transition-colors">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex items-center gap-2">
                            {getContentIcon(content.type)}
                            <span className="text-xs text-gray-400 uppercase">{content.type}</span>
                          </div>
                          <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">{content.version}</span>
                        </div>
                        <h3 className="text-sm font-medium text-white mb-2 line-clamp-2">{content.title}</h3>
                        <div className="flex items-center gap-2 mb-3">
                          <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded">{content.unit}</span>
                          <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">{content.topic}</span>
                        </div>
                        <div className="flex items-center justify-between text-xs text-gray-400">
                          <div className="flex items-center gap-3">
                            <span className="flex items-center gap-1">
                              <Eye className="w-3 h-3" />
                              {content.views}
                            </span>
                            <span className="flex items-center gap-1">
                              <Download className="w-3 h-3" />
                              {content.downloads}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            {content.visibility === 'view_only' ? (
                              <Lock className="w-3 h-3 text-orange-400" />
                            ) : (
                              <Unlock className="w-3 h-3 text-green-400" />
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-700">
                          <button className="flex-1 text-xs text-gray-400 hover:text-blue-400 py-1">
                            <Eye className="w-3 h-3 inline mr-1" />
                            View
                          </button>
                          <button className="flex-1 text-xs text-gray-400 hover:text-blue-400 py-1">
                            <Edit className="w-3 h-3 inline mr-1" />
                            Edit
                          </button>
                          <button className="flex-1 text-xs text-gray-400 hover:text-red-400 py-1">
                            <Trash2 className="w-3 h-3 inline mr-1" />
                            Delete
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'assignments' && (
                <div>
                  {/* Assignment Actions */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <select className="text-sm border border-gray-600 rounded-lg px-3 py-2 bg-gray-700 text-white">
                        <option value="">All Types</option>
                        <option value="theory">Theory</option>
                        <option value="coding">Coding</option>
                        <option value="case_study">Case Study</option>
                        <option value="research">Research</option>
                      </select>
                      <select className="text-sm border border-gray-600 rounded-lg px-3 py-2 bg-gray-700 text-white">
                        <option value="">All Status</option>
                        <option value="draft">Draft</option>
                        <option value="active">Active</option>
                        <option value="closed">Closed</option>
                      </select>
                    </div>
                    <button
                      onClick={() => setShowAssignmentModal(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
                    >
                      <Plus className="w-4 h-4" />
                      Create Assignment
                    </button>
                  </div>

                  {/* Assignments Table */}
                  <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
                    <table className="w-full">
                      <thead className="bg-gray-700/50">
                        <tr>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Assignment</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Type</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Due Date</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Submissions</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Marks</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Status</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-700">
                        {assignments.map((assignment) => (
                          <tr key={assignment.id} className="hover:bg-gray-700/50">
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-medium text-white">{assignment.title}</span>
                                {assignment.plagiarism_check && (
                                  <span className="text-xs bg-orange-500/20 text-orange-400 px-1.5 py-0.5 rounded">Plag Check</span>
                                )}
                              </div>
                            </td>
                            <td className="px-4 py-3">
                              <span className={`text-xs px-2 py-1 rounded capitalize ${
                                assignment.type === 'coding' ? 'bg-purple-500/20 text-purple-400' :
                                assignment.type === 'case_study' ? 'bg-blue-500/20 text-blue-400' :
                                assignment.type === 'research' ? 'bg-green-500/20 text-green-400' :
                                'bg-gray-700 text-gray-300'
                              }`}>
                                {assignment.type.replace('_', ' ')}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-300">{assignment.due_date}</td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-2">
                                <div className="w-20 h-2 bg-gray-700 rounded-full">
                                  <div
                                    className="h-2 bg-blue-500 rounded-full"
                                    style={{ width: `${(assignment.submissions / assignment.total_students) * 100}%` }}
                                  />
                                </div>
                                <span className="text-xs text-gray-400">{assignment.submissions}/{assignment.total_students}</span>
                              </div>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-300">{assignment.max_marks}</td>
                            <td className="px-4 py-3">
                              <span className={`text-xs px-2 py-1 rounded capitalize ${getStatusColor(assignment.status)}`}>
                                {assignment.status}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex items-center gap-1">
                                <button className="p-1.5 hover:bg-gray-600 rounded text-gray-400 hover:text-blue-400">
                                  <Eye className="w-4 h-4" />
                                </button>
                                <button className="p-1.5 hover:bg-gray-600 rounded text-gray-400 hover:text-blue-400">
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button className="p-1.5 hover:bg-gray-600 rounded text-gray-400 hover:text-blue-400">
                                  <Copy className="w-4 h-4" />
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

              {activeTab === 'quizzes' && (
                <div>
                  {/* Quiz Actions */}
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <select className="text-sm border border-gray-600 rounded-lg px-3 py-2 bg-gray-700 text-white">
                        <option value="">All Difficulty</option>
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                      <select className="text-sm border border-gray-600 rounded-lg px-3 py-2 bg-gray-700 text-white">
                        <option value="">All Status</option>
                        <option value="draft">Draft</option>
                        <option value="scheduled">Scheduled</option>
                        <option value="active">Active</option>
                        <option value="completed">Completed</option>
                      </select>
                    </div>
                    <button
                      onClick={() => setShowQuizModal(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
                    >
                      <Plus className="w-4 h-4" />
                      Create Quiz
                    </button>
                  </div>

                  {/* Quizzes Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {quizzes.map((quiz) => (
                      <div key={quiz.id} className="bg-gray-800 rounded-xl border border-gray-700 p-5 hover:border-gray-600 transition-colors">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="text-sm font-medium text-white">{quiz.title}</h3>
                            <p className="text-xs text-gray-400 mt-1">{quiz.questions_count} Questions | {quiz.duration_minutes} mins</p>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded capitalize ${getStatusColor(quiz.status)}`}>
                            {quiz.status}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 mb-4">
                          <span className={`text-xs px-2 py-1 rounded ${getDifficultyColor(quiz.difficulty)}`}>
                            {quiz.difficulty}
                          </span>
                          {quiz.scheduled_at && (
                            <span className="text-xs text-gray-400 flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {quiz.scheduled_at}
                            </span>
                          )}
                        </div>

                        {quiz.status === 'completed' && (
                          <div className="bg-gray-700/50 rounded-lg p-3 mb-4">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-gray-400">Attempts: {quiz.attempts}</span>
                              <span className="text-gray-400">Avg Score: {quiz.avg_score}%</span>
                            </div>
                            <div className="mt-2 h-2 bg-gray-700 rounded-full">
                              <div
                                className={`h-2 rounded-full ${quiz.avg_score >= 70 ? 'bg-green-500' : quiz.avg_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                style={{ width: `${quiz.avg_score}%` }}
                              />
                            </div>
                          </div>
                        )}

                        <div className="flex items-center gap-2">
                          {quiz.status === 'draft' && (
                            <>
                              <button className="flex-1 text-xs bg-blue-500/20 text-blue-400 py-2 rounded-lg hover:bg-blue-500/30">
                                Edit Quiz
                              </button>
                              <button className="flex-1 text-xs bg-green-500/20 text-green-400 py-2 rounded-lg hover:bg-green-500/30">
                                Schedule
                              </button>
                            </>
                          )}
                          {quiz.status === 'scheduled' && (
                            <>
                              <button className="flex-1 text-xs bg-blue-500/20 text-blue-400 py-2 rounded-lg hover:bg-blue-500/30">
                                Edit
                              </button>
                              <button className="flex-1 text-xs bg-orange-500/20 text-orange-400 py-2 rounded-lg hover:bg-orange-500/30">
                                Reschedule
                              </button>
                            </>
                          )}
                          {quiz.status === 'completed' && (
                            <>
                              <button className="flex-1 text-xs bg-blue-500/20 text-blue-400 py-2 rounded-lg hover:bg-blue-500/30">
                                View Results
                              </button>
                              <button className="flex-1 text-xs bg-gray-700 text-gray-300 py-2 rounded-lg hover:bg-gray-600">
                                Analytics
                              </button>
                            </>
                          )}
                          <button className="p-2 text-gray-400 hover:text-blue-400 hover:bg-gray-700 rounded-lg">
                            <Copy className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'schedule' && (
                <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
                  <div className="flex items-center justify-between mb-6">
                    <h3 className="text-lg font-semibold text-white">Class Schedule & Assessments</h3>
                    <div className="flex items-center gap-2">
                      <button className="flex items-center gap-2 px-3 py-2 text-sm border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700">
                        <ExternalLink className="w-4 h-4" />
                        Sync with Google Calendar
                      </button>
                      <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
                        <Plus className="w-4 h-4" />
                        Add Event
                      </button>
                    </div>
                  </div>

                  {/* Calendar View (Simplified) */}
                  <div className="grid grid-cols-7 gap-1">
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                      <div key={day} className="text-center text-xs font-medium text-gray-400 py-2">
                        {day}
                      </div>
                    ))}
                    {Array.from({ length: 35 }, (_, i) => {
                      const day = i - 3 // Offset for current month
                      const hasEvent = [5, 12, 15, 20, 22, 28].includes(day)
                      return (
                        <div
                          key={i}
                          className={`aspect-square p-1 text-xs rounded-lg border ${
                            day > 0 && day <= 31
                              ? hasEvent
                                ? 'border-blue-500/30 bg-blue-500/10'
                                : 'border-gray-700 hover:bg-gray-700 cursor-pointer'
                              : 'border-transparent text-gray-600'
                          }`}
                        >
                          {day > 0 && day <= 31 && (
                            <>
                              <span className={hasEvent ? 'text-blue-400 font-medium' : 'text-gray-300'}>
                                {day}
                              </span>
                              {hasEvent && (
                                <div className="mt-0.5 w-1.5 h-1.5 bg-blue-500 rounded-full mx-auto" />
                              )}
                            </>
                          )}
                        </div>
                      )
                    })}
                  </div>

                  {/* Upcoming Events */}
                  <div className="mt-6">
                    <h4 className="text-sm font-medium text-white mb-3">Upcoming Events</h4>
                    <div className="space-y-2">
                      {[
                        { date: 'Feb 5', time: '10:00 AM', title: 'Assignment Due: Stack Implementation', type: 'assignment' },
                        { date: 'Feb 8', time: '10:00 AM', title: 'Quiz: Trees Mid-Semester Test', type: 'quiz' },
                        { date: 'Feb 10', time: '11:00 AM', title: 'Class: Graph Algorithms Introduction', type: 'class' },
                        { date: 'Feb 12', time: '2:00 PM', title: 'Lab: Binary Tree Traversal', type: 'lab' },
                      ].map((event, i) => (
                        <div key={i} className="flex items-center gap-3 p-3 bg-gray-700/50 rounded-lg">
                          <div className="text-center min-w-[50px]">
                            <p className="text-xs text-gray-400">{event.date}</p>
                            <p className="text-xs font-medium text-white">{event.time}</p>
                          </div>
                          <div className="flex-1">
                            <p className="text-sm text-white">{event.title}</p>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded ${
                            event.type === 'assignment' ? 'bg-orange-500/20 text-orange-400' :
                            event.type === 'quiz' ? 'bg-purple-500/20 text-purple-400' :
                            event.type === 'class' ? 'bg-blue-500/20 text-blue-400' :
                            'bg-green-500/20 text-green-400'
                          }`}>
                            {event.type}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'analytics' && (
                <div className="space-y-6">
                  {/* Stats Grid */}
                  <div className="grid grid-cols-4 gap-4">
                    {[
                      { label: 'Content Views', value: '2,847', change: '+12%', icon: Eye },
                      { label: 'Avg Assignment Score', value: '76%', change: '+5%', icon: Target },
                      { label: 'Quiz Completion Rate', value: '89%', change: '+3%', icon: CheckCircle },
                      { label: 'Student Engagement', value: '85%', change: '+8%', icon: TrendingUp },
                    ].map((stat, i) => (
                      <div key={i} className="bg-gray-800 rounded-xl border border-gray-700 p-4">
                        <div className="flex items-center justify-between mb-2">
                          <stat.icon className="w-5 h-5 text-gray-500" />
                          <span className="text-xs text-green-400 font-medium">{stat.change}</span>
                        </div>
                        <p className="text-2xl font-semibold text-white">{stat.value}</p>
                        <p className="text-xs text-gray-400">{stat.label}</p>
                      </div>
                    ))}
                  </div>

                  {/* Charts Row */}
                  <div className="grid grid-cols-2 gap-6">
                    {/* Topic Performance */}
                    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
                      <h3 className="text-sm font-semibold text-white mb-4">Topic-wise Performance</h3>
                      <div className="space-y-3">
                        {[
                          { topic: 'Arrays', score: 85 },
                          { topic: 'Linked Lists', score: 78 },
                          { topic: 'Stacks', score: 82 },
                          { topic: 'Queues', score: 75 },
                          { topic: 'Trees', score: 68 },
                        ].map((item, i) => (
                          <div key={i}>
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-gray-300">{item.topic}</span>
                              <span className="font-medium text-white">{item.score}%</span>
                            </div>
                            <div className="h-2 bg-gray-700 rounded-full">
                              <div
                                className={`h-2 rounded-full ${item.score >= 80 ? 'bg-green-500' : item.score >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                style={{ width: `${item.score}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Weak Topics Alert */}
                    <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
                      <h3 className="text-sm font-semibold text-white mb-4">Weak Topics (Need Attention)</h3>
                      <div className="space-y-3">
                        {[
                          { topic: 'Tree Traversals', avg_score: 52, students_below_60: 28 },
                          { topic: 'Graph BFS/DFS', avg_score: 58, students_below_60: 22 },
                          { topic: 'Dynamic Programming Basics', avg_score: 61, students_below_60: 18 },
                        ].map((item, i) => (
                          <div key={i} className="flex items-center gap-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                            <AlertCircle className="w-5 h-5 text-red-400" />
                            <div className="flex-1">
                              <p className="text-sm font-medium text-white">{item.topic}</p>
                              <p className="text-xs text-gray-400">Avg: {item.avg_score}% | {item.students_below_60} students below 60%</p>
                            </div>
                            <button className="text-xs text-blue-400 hover:text-blue-300 font-medium">
                              Schedule Review
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Question Analysis */}
                  <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
                    <h3 className="text-sm font-semibold text-white mb-4">Question-wise Accuracy (Last Quiz)</h3>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="text-left text-xs text-gray-400">
                            <th className="py-2">Question</th>
                            <th className="py-2">Topic</th>
                            <th className="py-2">Difficulty</th>
                            <th className="py-2">Correct</th>
                            <th className="py-2">Wrong</th>
                            <th className="py-2">Accuracy</th>
                          </tr>
                        </thead>
                        <tbody className="text-sm text-gray-300">
                          {[
                            { q: 'Q1', topic: 'Trees', difficulty: 'easy', correct: 58, wrong: 7, accuracy: 89 },
                            { q: 'Q2', topic: 'Trees', difficulty: 'medium', correct: 52, wrong: 13, accuracy: 80 },
                            { q: 'Q3', topic: 'Traversal', difficulty: 'medium', correct: 45, wrong: 20, accuracy: 69 },
                            { q: 'Q4', topic: 'BST', difficulty: 'hard', correct: 38, wrong: 27, accuracy: 58 },
                            { q: 'Q5', topic: 'Balancing', difficulty: 'hard', correct: 32, wrong: 33, accuracy: 49 },
                          ].map((item, i) => (
                            <tr key={i} className="border-t border-gray-700">
                              <td className="py-2 font-medium text-white">{item.q}</td>
                              <td className="py-2">{item.topic}</td>
                              <td className="py-2">
                                <span className={`text-xs px-2 py-0.5 rounded ${getDifficultyColor(item.difficulty)}`}>
                                  {item.difficulty}
                                </span>
                              </td>
                              <td className="py-2 text-green-400">{item.correct}</td>
                              <td className="py-2 text-red-400">{item.wrong}</td>
                              <td className="py-2">
                                <div className="flex items-center gap-2">
                                  <div className="w-16 h-1.5 bg-gray-700 rounded-full">
                                    <div
                                      className={`h-1.5 rounded-full ${item.accuracy >= 70 ? 'bg-green-500' : item.accuracy >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                      style={{ width: `${item.accuracy}%` }}
                                    />
                                  </div>
                                  <span className="text-xs text-gray-400">{item.accuracy}%</span>
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <BookOpen className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">Select a Subject</h3>
              <p className="text-sm text-gray-400">Choose a subject from the left panel to manage content, assignments, and quizzes</p>
            </div>
          </div>
        )}
      </div>

      {/* Upload Content Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-lg mx-4">
            <div className="flex items-center justify-between p-4 border-b border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900">Upload Content</h3>
              <button onClick={() => setShowUploadModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Content Title</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter title"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option>Unit 1</option>
                    <option>Unit 2</option>
                    <option>Unit 3</option>
                    <option>Unit 4</option>
                    <option>Unit 5</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Topic</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="Enter topic"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Upload File</label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-500 cursor-pointer">
                  <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Drag & drop or click to upload</p>
                  <p className="text-xs text-gray-500 mt-1">PDF, PPT, DOC, or Video (max 100MB)</p>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Visibility</label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-2">
                    <input type="radio" name="visibility" defaultChecked className="text-indigo-600" />
                    <span className="text-sm text-gray-600">View Only</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="radio" name="visibility" className="text-indigo-600" />
                    <span className="text-sm text-gray-600">Downloadable</span>
                  </label>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200">
              <button
                onClick={() => setShowUploadModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-indigo-700">
                Upload
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Assignment Modal */}
      {showAssignmentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white">
              <h3 className="text-lg font-semibold text-gray-900">Create Assignment</h3>
              <button onClick={() => setShowAssignmentModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assignment Title</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter assignment title"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Assignment Type</label>
                <div className="grid grid-cols-4 gap-2">
                  {['Theory', 'Coding', 'Case Study', 'Research'].map((type) => (
                    <label key={type} className="flex items-center justify-center gap-2 p-3 border border-gray-200 rounded-lg cursor-pointer hover:border-indigo-500 has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50">
                      <input type="radio" name="type" className="sr-only" />
                      <span className="text-sm">{type}</span>
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  rows={4}
                  placeholder="Enter assignment description and instructions"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Due Date</label>
                  <input
                    type="datetime-local"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Marks</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Late Penalty (%/day)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="5"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Assignment Mode</label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2">
                      <input type="radio" name="mode" defaultChecked className="text-indigo-600" />
                      <span className="text-sm text-gray-600">Individual</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input type="radio" name="mode" className="text-indigo-600" />
                      <span className="text-sm text-gray-600">Group</span>
                    </label>
                  </div>
                </div>
                <div>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" className="rounded text-indigo-600" />
                    <span className="text-sm text-gray-700">Enable Plagiarism Check</span>
                  </label>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Rubrics (Optional)</label>
                <div className="space-y-2">
                  {['Correctness', 'Code Quality', 'Documentation', 'Innovation'].map((rubric) => (
                    <div key={rubric} className="flex items-center gap-3">
                      <input
                        type="text"
                        defaultValue={rubric}
                        className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg"
                      />
                      <input
                        type="number"
                        placeholder="Weight %"
                        className="w-24 px-3 py-2 text-sm border border-gray-300 rounded-lg"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 sticky bottom-0 bg-white">
              <button
                onClick={() => setShowAssignmentModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                Save as Draft
              </button>
              <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-indigo-700">
                Publish
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Quiz Modal */}
      {showQuizModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b border-gray-200 sticky top-0 bg-white">
              <h3 className="text-lg font-semibold text-gray-900">Create Quiz</h3>
              <button onClick={() => setShowQuizModal(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Quiz Title</label>
                <input
                  type="text"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Enter quiz title"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Duration (mins)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="30"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Total Marks</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    placeholder="50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Difficulty</label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Question Types</label>
                <div className="grid grid-cols-2 gap-2">
                  {['MCQ', 'Multiple Correct', 'True/False', 'Short Answer'].map((type) => (
                    <label key={type} className="flex items-center gap-2 p-2 border border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50">
                      <input type="checkbox" className="rounded text-indigo-600" />
                      <span className="text-sm text-gray-600">{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Quiz Settings</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" className="rounded text-indigo-600" />
                    <span className="text-sm text-gray-600">Randomize Questions</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" className="rounded text-indigo-600" />
                    <span className="text-sm text-gray-600">Randomize Options</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" className="rounded text-indigo-600" />
                    <span className="text-sm text-gray-600">Enable Negative Marking</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" className="rounded text-indigo-600" />
                    <span className="text-sm text-gray-600">Show Results After Submission</span>
                  </label>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Schedule Date & Time</label>
                  <input
                    type="datetime-local"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Max Attempts</label>
                  <select className="w-full px-3 py-2 border border-gray-300 rounded-lg">
                    <option value="1">1 Attempt</option>
                    <option value="2">2 Attempts</option>
                    <option value="3">3 Attempts</option>
                    <option value="unlimited">Unlimited</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 sticky bottom-0 bg-white">
              <button
                onClick={() => setShowQuizModal(false)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">
                Save as Draft
              </button>
              <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-indigo-700">
                Add Questions
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
