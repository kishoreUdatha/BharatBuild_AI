'use client'

import { useState, useEffect } from 'react'
import {
  Beaker,
  Plus,
  Search,
  Filter,
  Calendar,
  Clock,
  Users,
  BarChart3,
  Eye,
  Edit,
  Trash2,
  Copy,
  Lock,
  Unlock,
  ChevronRight,
  CheckCircle,
  AlertCircle,
  X,
  Settings,
  Code,
  FileText,
  Play,
  Target,
  Award,
  TrendingUp,
  Layers,
  Download,
  Upload,
  Database,
  Cpu,
  Zap,
  AlertTriangle,
  MoreVertical,
  ChevronDown,
  Loader2
} from 'lucide-react'
import { useLabManagement, Lab, LabTopic, LabAssignment } from '@/hooks/useLabManagement'
import { apiClient } from '@/lib/api-client'

// Local interfaces for UI-specific types
interface Experiment {
  id: string
  number: number
  title: string
  difficulty: 'easy' | 'medium' | 'hard'
  status: 'draft' | 'assigned' | 'locked'
  submissions: number
  total_students: number
  avg_score: number
  deadline?: string
  ai_limit?: number
}

interface Assignment {
  id: string
  experiment_id: string
  experiment_title: string
  assigned_to: 'class' | 'batch' | 'individual'
  target: string
  deadline: string
  deadline_type: 'soft' | 'hard'
  submissions: number
  total: number
  status: 'active' | 'completed' | 'locked'
}

export default function LabManagementPage() {
  const {
    labs,
    selectedLab,
    topics,
    assignments: apiAssignments,
    analytics,
    loading,
    error,
    selectLab,
    createTopic,
    assignTopic
  } = useLabManagement()

  const [activeTab, setActiveTab] = useState<'experiments' | 'assignments' | 'progress' | 'settings'>('experiments')
  const [showExperimentModal, setShowExperimentModal] = useState(false)
  const [showAssignModal, setShowAssignModal] = useState(false)
  const [selectedExperiment, setSelectedExperiment] = useState<Experiment | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showLabDropdown, setShowLabDropdown] = useState(false)
  const [creating, setCreating] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [difficultyFilter, setDifficultyFilter] = useState('')
  const [semesterFilter, setSemesterFilter] = useState<number | ''>('')
  const [assignmentStatusFilter, setAssignmentStatusFilter] = useState('')
  const [assignmentTypeFilter, setAssignmentTypeFilter] = useState('')
  const [assignmentSearchQuery, setAssignmentSearchQuery] = useState('')
  const [showStudentModal, setShowStudentModal] = useState(false)
  const [selectedExpForStudents, setSelectedExpForStudents] = useState<Experiment | null>(null)
  const [studentStatusFilter, setStudentStatusFilter] = useState<'all' | 'completed' | 'pending' | 'in_progress'>('all')
  const [studentData, setStudentData] = useState<any[]>([])
  const [loadingStudents, setLoadingStudents] = useState(false)
  const [studentStats, setStudentStats] = useState({ total: 0, completed: 0, pending: 0, avgScore: 0 })
  const [showCodeModal, setShowCodeModal] = useState(false)
  const [selectedStudentCode, setSelectedStudentCode] = useState<{ name: string; roll_number: string; code: string; score: number } | null>(null)

  // Form state for creating experiment
  const [newExperiment, setNewExperiment] = useState({
    title: '',
    description: '',
    week_number: 1,
    difficulty: 'medium' as 'easy' | 'medium' | 'hard'
  })

  // Form state for assignment
  const [assignmentForm, setAssignmentForm] = useState({
    assign_to: 'class' as 'class' | 'batch' | 'individual',
    class_id: '',
    batch_id: '',
    deadline: '',
    deadline_type: 'soft' as 'soft' | 'hard'
  })

  // Map topics to experiments format for UI
  const experiments: Experiment[] = topics.map((topic, index) => ({
    id: topic.id,
    number: index + 1,
    title: topic.title,
    difficulty: (topic.difficulty as 'easy' | 'medium' | 'hard') || 'medium',
    status: topic.status || 'draft',
    submissions: topic.submissions || 0,
    total_students: topic.total_students || analytics?.total_students || 0,
    avg_score: topic.avg_score || 0,
    deadline: topic.deadline,
    ai_limit: topic.ai_limit || 20
  }))

  // Map API assignments to local format
  const assignments: Assignment[] = apiAssignments.map(a => ({
    id: a.id,
    experiment_id: a.topic_id,
    experiment_title: a.topic_title,
    assigned_to: a.assigned_to,
    target: a.target_name,
    deadline: a.deadline,
    deadline_type: a.deadline_type,
    submissions: a.submissions,
    total: a.total,
    status: a.status
  }))

  // Fallback mock data if no labs from API
  const fallbackLabs = [
    { id: '1', name: 'Data Structures Lab', code: 'CS301L', semester: 3, total_topics: 12, total_mcqs: 0, total_coding_problems: 0, branch: 'CSE', faculty_id: '', is_active: true, created_at: '' },
    { id: '2', name: 'Database Lab', code: 'CS302L', semester: 3, total_topics: 10, total_mcqs: 0, total_coding_problems: 0, branch: 'CSE', faculty_id: '', is_active: true, created_at: '' },
    { id: '3', name: 'Operating Systems Lab', code: 'CS401L', semester: 4, total_topics: 8, total_mcqs: 0, total_coding_problems: 0, branch: 'CSE', faculty_id: '', is_active: true, created_at: '' },
    { id: '4', name: 'Computer Networks Lab', code: 'CS501L', semester: 5, total_topics: 10, total_mcqs: 0, total_coding_problems: 0, branch: 'CSE', faculty_id: '', is_active: true, created_at: '' },
    { id: '5', name: 'Machine Learning Lab', code: 'CS601L', semester: 6, total_topics: 8, total_mcqs: 0, total_coding_problems: 0, branch: 'CSE', faculty_id: '', is_active: true, created_at: '' },
  ]

  const allLabs = labs.length > 0 ? labs : fallbackLabs

  // Get unique semesters from labs
  const availableSemesters = [...new Set(allLabs.map(lab => lab.semester))].sort((a, b) => a - b)

  // Filter labs by semester
  const displayLabs = semesterFilter ? allLabs.filter(lab => lab.semester === semesterFilter) : allLabs
  const currentLab = selectedLab || displayLabs[0]

  // Handle create experiment
  const handleCreateExperiment = async () => {
    if (!currentLab || !newExperiment.title) return
    setCreating(true)
    try {
      await createTopic(currentLab.id, {
        title: newExperiment.title,
        description: newExperiment.description,
        week_number: newExperiment.week_number
      })
      setShowExperimentModal(false)
      setNewExperiment({ title: '', description: '', week_number: 1, difficulty: 'medium' })
    } catch (err) {
      console.error('Failed to create experiment:', err)
    }
    setCreating(false)
  }

  // Handle assign experiment
  const handleAssignExperiment = async () => {
    if (!selectedExperiment || !currentLab) return
    setCreating(true)
    try {
      await assignTopic({
        topic_id: selectedExperiment.id,
        lab_id: currentLab.id,
        class_id: assignmentForm.assign_to === 'class' ? assignmentForm.class_id : undefined,
        batch_id: assignmentForm.assign_to === 'batch' ? assignmentForm.batch_id : undefined,
        deadline: new Date(assignmentForm.deadline).toISOString(),
        deadline_type: assignmentForm.deadline_type
      })
      setShowAssignModal(false)
      setSelectedExperiment(null)
    } catch (err) {
      console.error('Failed to assign experiment:', err)
    }
    setCreating(false)
  }

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
      case 'assigned': return 'bg-blue-500/20 text-blue-400'
      case 'locked': return 'bg-green-500/20 text-green-400'
      case 'completed': return 'bg-green-500/20 text-green-400'
      case 'active': return 'bg-blue-500/20 text-blue-400'
      case 'draft': return 'bg-gray-500/20 text-gray-400'
      default: return 'bg-gray-500/20 text-gray-400'
    }
  }

  // Fetch student progress data from backend
  const fetchStudentProgress = async (topicId: string) => {
    setLoadingStudents(true)
    try {
      const response = await apiClient.getTopicStudentProgress(topicId)
      setStudentData(response.students || [])
      setStudentStats({
        total: response.total_students || 0,
        completed: response.completed_count || 0,
        pending: response.pending_count || 0,
        avgScore: response.avg_score || 0
      })
    } catch (err) {
      console.log('Using demo data for student progress')
      // Fallback to demo data
      const demoStudents = generateDemoStudentData(selectedExpForStudents!)
      setStudentData(demoStudents)
      const completed = demoStudents.filter((s: any) => s.status === 'completed').length
      setStudentStats({
        total: demoStudents.length,
        completed,
        pending: demoStudents.length - completed,
        avgScore: 72
      })
    }
    setLoadingStudents(false)
  }

  // Demo data fallback
  const generateDemoStudentData = (exp: Experiment) => {
    const firstNames = ['Rahul', 'Priya', 'Amit', 'Sneha', 'Vikram', 'Ananya', 'Karthik', 'Divya', 'Arjun', 'Meera',
      'Rohan', 'Neha', 'Siddharth', 'Pooja', 'Aditya', 'Kavita', 'Nikhil', 'Riya', 'Varun', 'Shreya',
      'Manish', 'Anjali', 'Deepak', 'Sunita', 'Rajesh', 'Preeti', 'Ashok', 'Rekha', 'Suresh', 'Lakshmi']
    const lastNames = ['Kumar', 'Sharma', 'Singh', 'Patel', 'Reddy', 'Gupta', 'Nair', 'Krishnan', 'Menon', 'Iyer',
      'Das', 'Kapoor', 'Joshi', 'Verma', 'Rao', 'Agarwal', 'Mishra', 'Chauhan', 'Yadav', 'Pandey']

    const seed = exp.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
    const seededRandom = (s: number) => {
      const x = Math.sin(s * 9999) * 10000
      return x - Math.floor(x)
    }

    // Generate students for the full total_students count
    return Array.from({ length: exp.total_students }, (_, idx) => {
      const isCompleted = idx < exp.submissions
      const score = isCompleted ? Math.floor(50 + seededRandom(seed + idx) * 50) : 0
      const firstName = firstNames[Math.floor(seededRandom(seed + idx * 7) * firstNames.length)]
      const lastName = lastNames[Math.floor(seededRandom(seed + idx * 13) * lastNames.length)]

      return {
        id: `student-${idx}`,
        name: `${firstName} ${lastName}`,
        roll_number: `21CS${String(idx + 1).padStart(3, '0')}`,
        section: idx % 2 === 0 ? 'A' : 'B',
        status: isCompleted ? 'completed' : 'pending',
        score,
        submitted_at: isCompleted
          ? new Date(Date.now() - Math.floor(seededRandom(seed + idx + 100) * 7 * 24 * 60 * 60 * 1000)).toISOString()
          : null,
        attempts: isCompleted ? Math.floor(1 + seededRandom(seed + idx + 200) * 3) : 0
      }
    })
  }

  // Fetch student data when modal opens
  useEffect(() => {
    if (showStudentModal && selectedExpForStudents) {
      fetchStudentProgress(selectedExpForStudents.id)
    }
  }, [showStudentModal, selectedExpForStudents?.id])

  // Generate demo code for a student
  const generateDemoCode = (student: any, exp: Experiment) => {
    const codeTemplates = [
      `#include <stdio.h>

int main() {
    // ${exp.title} - Solution by ${student.name}
    int n, i;
    printf("Enter the number of elements: ");
    scanf("%d", &n);

    int arr[n];
    printf("Enter %d elements: ", n);
    for(i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }

    // Processing logic
    int result = 0;
    for(i = 0; i < n; i++) {
        result += arr[i];
    }

    printf("Result: %d\\n", result);
    return 0;
}`,
      `def solve():
    """
    ${exp.title}
    Solution by: ${student.name}
    """
    n = int(input("Enter number of elements: "))
    arr = list(map(int, input().split()))

    # Processing logic
    result = sum(arr)

    print(f"Result: {result}")

if __name__ == "__main__":
    solve()`,
      `import java.util.Scanner;

public class Solution {
    // ${exp.title} - ${student.name}
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

        System.out.print("Enter n: ");
        int n = sc.nextInt();
        int[] arr = new int[n];

        for(int i = 0; i < n; i++) {
            arr[i] = sc.nextInt();
        }

        int result = 0;
        for(int i = 0; i < n; i++) {
            result += arr[i];
        }

        System.out.println("Result: " + result);
    }
}`
    ]

    const seed = student.id.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0)
    return codeTemplates[seed % codeTemplates.length]
  }

  // Handle view code click
  const handleViewCode = (student: any) => {
    if (selectedExpForStudents) {
      setSelectedStudentCode({
        name: student.name,
        roll_number: student.roll_number,
        code: generateDemoCode(student, selectedExpForStudents),
        score: student.score
      })
      setShowCodeModal(true)
    }
  }

  const filteredStudentData = studentData.filter(s =>
    studentStatusFilter === 'all' || s.status === studentStatusFilter
  )
  const completedCount = studentStats.completed
  const pendingCount = studentStats.pending
  const inProgressCount = studentData.filter(s => s.status === 'in_progress').length

  const filteredExperiments = experiments.filter(exp => {
    const matchesSearch = exp.title.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = !statusFilter || exp.status === statusFilter
    const matchesDifficulty = !difficultyFilter || exp.difficulty === difficultyFilter
    return matchesSearch && matchesStatus && matchesDifficulty
  })

  const filteredAssignments = assignments.filter(assignment => {
    const matchesSearch = assignment.experiment_title.toLowerCase().includes(assignmentSearchQuery.toLowerCase())
    const matchesStatus = !assignmentStatusFilter || assignment.status === assignmentStatusFilter
    const matchesType = !assignmentTypeFilter || assignment.assigned_to === assignmentTypeFilter
    return matchesSearch && matchesStatus && matchesType
  })

  // Loading state
  if (loading && labs.length === 0) {
    return (
      <div className="h-[calc(100vh-4rem)] flex items-center justify-center bg-gray-900">
        <div className="flex items-center gap-3 text-gray-400">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Loading labs...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-gray-900">
      {/* Compact Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-6 py-3">
        <div className="flex items-center justify-between gap-4">
          {/* Semester Filter & Lab Selector */}
          <div className="flex items-center gap-2">
            {/* Semester Filter */}
            <select
              value={semesterFilter}
              onChange={(e) => {
                setSemesterFilter(e.target.value ? Number(e.target.value) : '')
              }}
              className="px-2.5 py-1.5 bg-gray-700 border border-gray-600 rounded-md text-xs text-gray-300 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">All Semesters</option>
              {availableSemesters.map((sem) => (
                <option key={sem} value={sem}>Semester {sem}</option>
              ))}
            </select>

            {/* Lab Selector */}
            <div className="relative">
              <button
                onClick={() => setShowLabDropdown(!showLabDropdown)}
                className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-700 hover:bg-gray-600 border border-gray-600 rounded-md transition-colors text-xs"
              >
                <span className="text-blue-400 font-medium">{currentLab?.code || 'Select Lab'}</span>
                <ChevronDown className={`w-3 h-3 text-gray-400 transition-transform ${showLabDropdown ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Menu */}
              {showLabDropdown && (
                <div className="absolute top-full left-0 mt-1 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50 overflow-hidden">
                  <div className="p-1 max-h-64 overflow-y-auto">
                    {displayLabs.length > 0 ? displayLabs.map((lab) => (
                      <button
                        key={lab.id}
                        onClick={() => {
                          selectLab(lab as Lab)
                          setShowLabDropdown(false)
                        }}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded text-xs transition-colors ${
                          currentLab?.id === lab.id
                            ? 'bg-blue-600/20 text-blue-400'
                            : 'text-gray-300 hover:bg-gray-700'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{lab.code}</span>
                          <span className="text-gray-500 text-[10px]">Sem {lab.semester}</span>
                        </div>
                        <span className="text-gray-500 truncate max-w-[120px]">{lab.name}</span>
                      </button>
                    )) : (
                      <div className="px-2.5 py-2 text-xs text-gray-500 text-center">
                        No labs in this semester
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex bg-gray-700/50 rounded-lg p-0.5">
            {[
              { id: 'experiments', label: 'Experiments', icon: Beaker },
              { id: 'assignments', label: 'Assignments', icon: Target },
              { id: 'progress', label: 'Progress', icon: BarChart3 },
              { id: 'settings', label: 'Settings', icon: Settings },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <tab.icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Stats + Action */}
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-3 text-xs text-gray-400">
              <span><span className="text-white">{currentLab?.total_topics || experiments.length}</span> Exp</span>
              <span><span className="text-white">{analytics?.total_students || 0}</span> Students</span>
              <span className="text-green-400">{analytics?.completion_rate || 0}%</span>
            </div>
            <button
              onClick={() => setShowExperimentModal(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors flex-shrink-0"
            >
              <Plus className="w-3.5 h-3.5" />
              New
            </button>
          </div>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto scrollbar-hide p-4">
        {activeTab === 'experiments' && (
          <div>
            {/* Filters */}
            <div className="flex gap-3 mb-4">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="">All Status</option>
                <option value="draft">Draft</option>
                <option value="assigned">Assigned</option>
                <option value="locked">Locked</option>
              </select>
              <select
                value={difficultyFilter}
                onChange={(e) => setDifficultyFilter(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="">All Difficulty</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search experiments..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
              />
            </div>

            {/* Experiments Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-700/50">
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">#</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Experiment</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Difficulty</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Progress</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Avg Score</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Status</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {filteredExperiments.map((exp) => (
                    <tr key={exp.id} className="hover:bg-gray-700/50">
                      <td className="px-4 py-3">
                        <span className="text-sm font-medium text-white">{exp.number}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="text-sm font-medium text-white">{exp.title}</p>
                          {exp.deadline && <p className="text-xs text-gray-500">Due: {exp.deadline}</p>}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${getDifficultyColor(exp.difficulty)}`}>
                          {exp.difficulty}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-700 rounded-full">
                            <div className="h-1.5 bg-blue-500 rounded-full" style={{ width: `${exp.total_students > 0 ? (exp.submissions / exp.total_students) * 100 : 0}%` }} />
                          </div>
                          <span className="text-xs text-gray-400">{exp.submissions}/{exp.total_students}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-sm font-medium ${exp.avg_score >= 70 ? 'text-green-400' : exp.avg_score >= 50 ? 'text-yellow-400' : 'text-gray-500'}`}>
                          {exp.avg_score > 0 ? `${exp.avg_score}%` : '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${getStatusColor(exp.status)}`}>
                          {exp.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => { setSelectedExperiment(exp); setShowAssignModal(true) }}
                            className="text-xs text-blue-400 hover:text-blue-300"
                          >
                            Assign
                          </button>
                          <button className="text-xs text-gray-400 hover:text-white">Edit</button>
                          <button
                            onClick={() => { setSelectedExpForStudents(exp); setShowStudentModal(true); setStudentStatusFilter('all') }}
                            className="text-xs text-gray-400 hover:text-white"
                          >
                            View
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredExperiments.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  {experiments.length === 0
                    ? 'No experiments found. Click "New" to create one.'
                    : 'No experiments match your filters.'}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'assignments' && (
          <div>
            {/* Filters */}
            <div className="flex gap-3 mb-4">
              <select
                value={assignmentStatusFilter}
                onChange={(e) => setAssignmentStatusFilter(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="">All Status</option>
                <option value="active">Active</option>
                <option value="completed">Completed</option>
                <option value="locked">Locked</option>
              </select>
              <select
                value={assignmentTypeFilter}
                onChange={(e) => setAssignmentTypeFilter(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="">All Types</option>
                <option value="class">Class</option>
                <option value="batch">Batch</option>
                <option value="individual">Individual</option>
              </select>
              <input
                type="text"
                value={assignmentSearchQuery}
                onChange={(e) => setAssignmentSearchQuery(e.target.value)}
                placeholder="Search assignments..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500"
              />
            </div>

            {/* Assignments Table */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-700/50">
                  <tr>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Experiment</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Assigned To</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Deadline</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Progress</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Status</th>
                    <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700">
                  {filteredAssignments.map((assignment) => (
                    <tr key={assignment.id} className="hover:bg-gray-700/50">
                      <td className="px-4 py-3">
                        <span className="text-sm font-medium text-white">{assignment.experiment_title}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            assignment.assigned_to === 'class' ? 'bg-blue-500/20 text-blue-400' :
                            assignment.assigned_to === 'batch' ? 'bg-purple-500/20 text-purple-400' :
                            'bg-green-500/20 text-green-400'
                          }`}>
                            {assignment.assigned_to}
                          </span>
                          <span className="text-sm text-gray-300">{assignment.target}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="text-sm text-gray-300">{assignment.deadline}</span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            assignment.deadline_type === 'hard' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {assignment.deadline_type}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-gray-700 rounded-full">
                            <div className={`h-1.5 rounded-full ${assignment.submissions === assignment.total ? 'bg-green-500' : 'bg-blue-500'}`}
                              style={{ width: `${(assignment.submissions / assignment.total) * 100}%` }} />
                          </div>
                          <span className="text-xs text-gray-400">{assignment.submissions}/{assignment.total}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${getStatusColor(assignment.status)}`}>
                          {assignment.status}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <button className="text-xs text-blue-400 hover:text-blue-300">Edit</button>
                          <button className="text-xs text-gray-400 hover:text-white">View</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filteredAssignments.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  {assignments.length === 0
                    ? 'No assignments yet. Assign an experiment to get started.'
                    : 'No assignments match your filters.'}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'progress' && (
          <div className="space-y-6">
            {/* Overall Progress */}
            <div className="grid grid-cols-3 gap-6">
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Completion Rate</h3>
                <div className="relative w-32 h-32 mx-auto">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="64" cy="64" r="56" stroke="#374151" strokeWidth="12" fill="none" />
                    <circle
                      cx="64"
                      cy="64"
                      r="56"
                      stroke="#3B82F6"
                      strokeWidth="12"
                      fill="none"
                      strokeDasharray={`${2 * Math.PI * 56 * (analytics?.completion_rate || 0) / 100} ${2 * Math.PI * 56}`}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-2xl font-bold text-white">{analytics?.completion_rate || 0}%</span>
                  </div>
                </div>
                <div className="text-center mt-4">
                  <p className="text-sm text-gray-400">{analytics?.active_students || 0} of {analytics?.total_students || 0} students completed all labs</p>
                </div>
              </div>

              <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-white mb-4">Score Distribution</h3>
                <div className="space-y-3">
                  {[
                    { range: '90-100%', count: 12, color: 'bg-green-500' },
                    { range: '80-89%', count: 18, color: 'bg-blue-500' },
                    { range: '70-79%', count: 15, color: 'bg-yellow-500' },
                    { range: '60-69%', count: 12, color: 'bg-orange-500' },
                    { range: '<60%', count: 8, color: 'bg-red-500' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-xs text-gray-400 w-16">{item.range}</span>
                      <div className="flex-1 h-4 bg-gray-700 rounded-full">
                        <div
                          className={`h-4 ${item.color} rounded-full`}
                          style={{ width: `${(item.count / 65) * 100}%` }}
                        />
                      </div>
                      <span className="text-xs font-medium text-gray-300 w-8">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
                <h3 className="text-sm font-semibold text-white mb-4">At-Risk Students</h3>
                <div className="space-y-3">
                  {[
                    { name: 'Rahul K.', pending: 4, last_active: '5 days ago' },
                    { name: 'Priya M.', pending: 3, last_active: '7 days ago' },
                    { name: 'Amit S.', pending: 3, last_active: '10 days ago' },
                    { name: 'Sneha R.', pending: 2, last_active: '3 days ago' },
                  ].map((student, i) => (
                    <div key={i} className="flex items-center gap-3 p-2 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-white">{student.name}</p>
                        <p className="text-xs text-gray-400">{student.pending} pending | {student.last_active}</p>
                      </div>
                      <button className="text-xs text-blue-400 hover:text-blue-300">Notify</button>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Experiment-wise Progress */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Experiment-wise Progress</h3>
              <div className="space-y-4">
                {experiments.slice(0, 4).map((exp) => (
                  <div key={exp.id} className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-sm font-bold border ${getDifficultyColor(exp.difficulty)}`}>
                      {exp.number}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-white">{exp.title}</span>
                        <span className="text-xs text-gray-400">{exp.submissions}/{exp.total_students}</span>
                      </div>
                      <div className="h-2 bg-gray-700 rounded-full">
                        <div
                          className="h-2 bg-blue-500 rounded-full"
                          style={{ width: `${(exp.submissions / exp.total_students) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="text-right w-16">
                      <p className="text-sm font-semibold text-white">{exp.avg_score}%</p>
                      <p className="text-xs text-gray-400">avg</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="max-w-2xl space-y-6">
            {/* General Settings */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-semibold text-white mb-4">General Settings</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Lab Name</label>
                  <input
                    type="text"
                    defaultValue={selectedLab?.name}
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Lab Code</label>
                  <input
                    type="text"
                    defaultValue={selectedLab?.code}
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                  />
                </div>
              </div>
            </div>

            {/* AI Settings */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-semibold text-white mb-4">AI Usage Control</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Default AI Limit (%)</label>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    defaultValue="20"
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>0% (Fully blocked)</span>
                    <span>20%</span>
                    <span>100% (Unlimited)</span>
                  </div>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-300">AI Hints Allowed</p>
                    <p className="text-xs text-gray-400">Students can request AI hints during practice</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="sr-only peer" />
                    <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-500/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
              </div>
            </div>

            {/* Deadline Settings */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Deadline Settings</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-300">Auto-lock after deadline</p>
                    <p className="text-xs text-gray-400">Automatically lock submissions after hard deadline</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" defaultChecked className="sr-only peer" />
                    <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-500/30 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                  </label>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Late Submission Penalty (%/day)</label>
                  <input
                    type="number"
                    defaultValue="10"
                    className="w-32 px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Grace Period (hours)</label>
                  <input
                    type="number"
                    defaultValue="2"
                    className="w-32 px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                  />
                </div>
              </div>
            </div>

            <button className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700">
              Save Settings
            </button>
          </div>
        )}
      </div>

      {/* Create Experiment Modal */}
      {showExperimentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-3xl mx-4 max-h-[90vh] overflow-y-auto border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700 sticky top-0 bg-gray-800">
              <h3 className="text-lg font-semibold text-white">Create New Experiment</h3>
              <button onClick={() => setShowExperimentModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Exp. No.</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                    placeholder="1"
                  />
                </div>
                <div className="col-span-3">
                  <label className="block text-sm font-medium text-gray-300 mb-1">Experiment Title</label>
                  <input
                    type="text"
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                    placeholder="Enter experiment title"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Problem Statement</label>
                <textarea
                  className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                  rows={4}
                  placeholder="Describe the problem students need to solve..."
                />
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Difficulty</label>
                  <select className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg">
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Max Marks</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                    placeholder="100"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">AI Limit (%)</label>
                  <input
                    type="number"
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                    placeholder="20"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Sample Input</label>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg font-mono text-sm"
                    rows={4}
                    placeholder="5&#10;1 2 3 4 5"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Expected Output</label>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg font-mono text-sm"
                    rows={4}
                    placeholder="15"
                  />
                </div>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700 sticky bottom-0 bg-gray-800">
              <button
                onClick={() => setShowExperimentModal(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 text-sm border border-gray-600 text-gray-300 rounded-lg hover:bg-gray-700">
                Save as Draft
              </button>
              <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Create & Assign
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Assign Experiment Modal */}
      {showAssignModal && selectedExperiment && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-lg mx-4 border border-gray-700">
            <div className="flex items-center justify-between p-4 border-b border-gray-700">
              <h3 className="text-lg font-semibold text-white">Assign Experiment</h3>
              <button onClick={() => setShowAssignModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              <div className="bg-gray-700/50 rounded-lg p-3">
                <p className="text-sm text-gray-400">Experiment</p>
                <p className="text-sm font-medium text-white">{selectedExperiment.number}. {selectedExperiment.title}</p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Assign To</label>
                <div className="grid grid-cols-3 gap-2">
                  {['Class', 'Batch', 'Individual'].map((type) => (
                    <label key={type} className="flex items-center justify-center gap-2 p-3 border border-gray-600 rounded-lg cursor-pointer hover:border-blue-500 has-[:checked]:border-blue-500 has-[:checked]:bg-blue-500/10">
                      <input type="radio" name="assign_type" className="sr-only" defaultChecked={type === 'Class'} />
                      <span className="text-sm text-gray-300">{type}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">Select Target</label>
                <select className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg">
                  <option>CSE-3A (65 students)</option>
                  <option>CSE-3B (68 students)</option>
                  <option>Batch A - CSE-3A (32 students)</option>
                  <option>Batch B - CSE-3A (33 students)</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Deadline</label>
                  <input
                    type="datetime-local"
                    className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">Deadline Type</label>
                  <select className="w-full px-3 py-2 border border-gray-600 bg-gray-700 text-white rounded-lg">
                    <option value="soft">Soft (Warning only)</option>
                    <option value="hard">Hard (Blocks submission)</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" className="rounded text-blue-600 bg-gray-700 border-gray-600" />
                <span className="text-sm text-gray-300">Send notification to students</span>
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700">
              <button
                onClick={() => setShowAssignModal(false)}
                className="px-4 py-2 text-sm text-gray-400 hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Assign
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Student Completion Modal */}
      {showStudentModal && selectedExpForStudents && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl w-full max-w-4xl mx-4 max-h-[85vh] overflow-hidden border border-gray-700 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
              <div>
                <h3 className="text-lg font-semibold text-white">Student Progress</h3>
                <p className="text-sm text-gray-400">
                  Exp {selectedExpForStudents.number}: {selectedExpForStudents.title}
                </p>
              </div>
              <button onClick={() => setShowStudentModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2 p-4 border-b border-gray-700">
              {[
                { id: 'all', label: `All (${studentData.length})` },
                { id: 'completed', label: `Completed (${completedCount})`, color: 'text-green-400' },
                { id: 'pending', label: `Pending (${pendingCount})`, color: 'text-orange-400' }
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setStudentStatusFilter(tab.id as any)}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    studentStatusFilter === tab.id
                      ? 'bg-blue-600 text-white'
                      : `bg-gray-700 ${tab.color || 'text-gray-300'} hover:bg-gray-600`
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Student List */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {loadingStudents ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 animate-spin text-blue-400" />
                  <span className="ml-2 text-gray-400">Loading student data...</span>
                </div>
              ) : (
                <>
                  {/* Fixed Header */}
                  <div className="bg-gray-800 border-b border-gray-600">
                    <table className="w-full">
                      <thead>
                        <tr>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[12%]">Roll No.</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[20%]">Student Name</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Section</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[14%]">Status</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[10%]">Score</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[18%]">Submitted</th>
                          <th className="text-left text-xs font-medium text-gray-400 uppercase px-4 py-3 w-[16%]">Actions</th>
                        </tr>
                      </thead>
                    </table>
                  </div>
                  {/* Scrollable Body */}
                  <div className="flex-1 overflow-y-auto">
                    <table className="w-full">
                      <tbody className="divide-y divide-gray-700">
                      {filteredStudentData.map((student) => (
                        <tr key={student.id || student.student_id} className="hover:bg-gray-700/50">
                          <td className="px-4 py-3 w-[12%]">
                            <span className="text-sm font-mono text-gray-300">{student.roll_number}</span>
                          </td>
                          <td className="px-4 py-3 w-[20%]">
                            <span className="text-sm font-medium text-white">{student.name || student.student_name}</span>
                          </td>
                          <td className="px-4 py-3 w-[10%]">
                            <span className="text-sm text-gray-400">{student.section || '-'}</span>
                          </td>
                          <td className="px-4 py-3 w-[14%]">
                            <span className={`inline-flex items-center gap-1.5 text-xs px-2 py-1 rounded ${
                              student.status === 'completed'
                                ? 'bg-green-500/20 text-green-400'
                                : student.status === 'in_progress'
                                  ? 'bg-blue-500/20 text-blue-400'
                                  : 'bg-orange-500/20 text-orange-400'
                            }`}>
                              {student.status === 'completed' ? (
                                <CheckCircle className="w-3 h-3" />
                              ) : student.status === 'in_progress' ? (
                                <Play className="w-3 h-3" />
                              ) : (
                                <Clock className="w-3 h-3" />
                              )}
                              {student.status === 'completed' ? 'Completed' : student.status === 'in_progress' ? 'In Progress' : 'Pending'}
                            </span>
                          </td>
                          <td className="px-4 py-3 w-[10%]">
                            {student.status === 'completed' ? (
                              <span className={`text-sm font-medium ${
                                student.score >= 80 ? 'text-green-400' :
                                student.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                              }`}>
                                {student.score}%
                              </span>
                            ) : (
                              <span className="text-sm text-gray-500">-</span>
                            )}
                          </td>
                          <td className="px-4 py-3 w-[18%]">
                            {student.submitted_at ? (
                              <span className="text-xs text-gray-400">
                                {new Date(student.submitted_at).toLocaleDateString('en-IN', {
                                  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
                                })}
                              </span>
                            ) : (
                              <span className="text-xs text-gray-500">Not submitted</span>
                            )}
                          </td>
                          <td className="px-4 py-3 w-[16%]">
                            <div className="flex items-center gap-2">
                              {student.status === 'completed' ? (
                                <button
                                  onClick={() => handleViewCode(student)}
                                  className="text-xs text-blue-400 hover:text-blue-300"
                                >
                                  View Code
                                </button>
                              ) : (
                                <button className="text-xs text-orange-400 hover:text-orange-300">Send Reminder</button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                      </tbody>
                    </table>
                    {filteredStudentData.length === 0 && (
                      <div className="text-center py-8 text-gray-500">
                        No students found for this filter.
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between p-4 border-t border-gray-700 bg-gray-800">
              <button className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600">
                <Download className="w-4 h-4" />
                Export CSV
              </button>
              <div className="flex gap-3">
                {pendingCount > 0 && (
                  <button className="flex items-center gap-2 px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700">
                    <AlertCircle className="w-4 h-4" />
                    Remind All Pending ({pendingCount})
                  </button>
                )}
                <button
                  onClick={() => setShowStudentModal(false)}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Code View Modal */}
      {showCodeModal && selectedStudentCode && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
          <div className="bg-gray-800 rounded-xl w-full max-w-3xl mx-4 max-h-[85vh] overflow-hidden border border-gray-700 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
              <div>
                <h3 className="text-lg font-semibold text-white">Student Submission</h3>
                <p className="text-sm text-gray-400">
                  {selectedStudentCode.name} ({selectedStudentCode.roll_number}) - Score: <span className={selectedStudentCode.score >= 70 ? 'text-green-400' : 'text-yellow-400'}>{selectedStudentCode.score}%</span>
                </p>
              </div>
              <button onClick={() => setShowCodeModal(false)} className="p-1 hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Code Content */}
            <div className="flex-1 overflow-auto p-4 bg-gray-900">
              <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                <code>{selectedStudentCode.code}</code>
              </pre>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-700 bg-gray-800">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(selectedStudentCode.code)
                }}
                className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600"
              >
                <Copy className="w-4 h-4" />
                Copy Code
              </button>
              <button
                onClick={() => setShowCodeModal(false)}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Click outside to close dropdown */}
      {showLabDropdown && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowLabDropdown(false)}
        />
      )}
    </div>
  )
}
