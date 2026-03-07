'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  Award,
  BookOpen,
  GraduationCap,
  FileText,
  Building2,
  Users,
  Shield,
  Leaf,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  BarChart3,
  Target
} from 'lucide-react'

interface CriterionProgress {
  number: number
  name: string
  marks: number
  earnedMarks: number
  progress: number
  status: 'not_started' | 'in_progress' | 'submitted' | 'approved'
  keyIndicators: number
  completedIndicators: number
  lastUpdated?: string
  assignedTo?: string
}

const CRITERIA_INFO = [
  { number: 1, name: 'Curricular Aspects', marks: 150, icon: BookOpen, color: 'orange', keyIndicators: 4 },
  { number: 2, name: 'Teaching-Learning and Evaluation', marks: 200, icon: GraduationCap, color: 'blue', keyIndicators: 7 },
  { number: 3, name: 'Research, Innovations and Extension', marks: 150, icon: FileText, color: 'green', keyIndicators: 5 },
  { number: 4, name: 'Infrastructure and Learning Resources', marks: 100, icon: Building2, color: 'purple', keyIndicators: 4 },
  { number: 5, name: 'Student Support and Progression', marks: 50, icon: Users, color: 'cyan', keyIndicators: 4 },
  { number: 6, name: 'Governance, Leadership and Management', marks: 50, icon: Shield, color: 'indigo', keyIndicators: 5 },
  { number: 7, name: 'Institutional Values and Best Practices', marks: 50, icon: Leaf, color: 'emerald', keyIndicators: 3 },
]

export default function CriteriaPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [criteria, setCriteria] = useState<CriterionProgress[]>([])

  useEffect(() => {
    loadCriteria()
  }, [])

  const loadCriteria = async () => {
    setIsLoading(true)
    try {
      // TODO: Replace with API call
      await new Promise(r => setTimeout(r, 500))

      setCriteria(CRITERIA_INFO.map(c => ({
        number: c.number,
        name: c.name,
        marks: c.marks,
        earnedMarks: Math.floor(Math.random() * c.marks * 0.4),
        progress: Math.floor(Math.random() * 50),
        status: Math.random() > 0.5 ? 'in_progress' : 'not_started',
        keyIndicators: c.keyIndicators,
        completedIndicators: Math.floor(Math.random() * c.keyIndicators),
        lastUpdated: '2 days ago',
        assignedTo: Math.random() > 0.3 ? 'Dr. Faculty Name' : undefined
      })))
    } finally {
      setIsLoading(false)
    }
  }

  const totalMarks = 750
  const earnedMarks = criteria.reduce((sum, c) => sum + c.earnedMarks, 0)
  const overallProgress = criteria.length > 0
    ? Math.round(criteria.reduce((sum, c) => sum + c.progress, 0) / criteria.length)
    : 0

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'approved':
        return (
          <span className="flex items-center gap-1 text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded-full">
            <CheckCircle2 className="w-3 h-3" />
            Approved
          </span>
        )
      case 'submitted':
        return (
          <span className="flex items-center gap-1 text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded-full">
            <Clock className="w-3 h-3" />
            Submitted
          </span>
        )
      case 'in_progress':
        return (
          <span className="flex items-center gap-1 text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded-full">
            <AlertCircle className="w-3 h-3" />
            In Progress
          </span>
        )
      default:
        return (
          <span className="flex items-center gap-1 text-xs bg-slate-500/20 text-slate-400 px-2 py-1 rounded-full">
            <Clock className="w-3 h-3" />
            Not Started
          </span>
        )
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => router.push('/accreditation/dashboard')}
                className="p-2 hover:bg-slate-800 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <div>
                <h1 className="font-bold text-lg">All Criteria</h1>
                <p className="text-sm text-slate-400">NAAC 7 Criteria Framework - 750 Total Marks</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Overall Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <Target className="w-8 h-8 text-orange-500" />
              <span className="text-sm text-slate-400">Overall Progress</span>
            </div>
            <div className="text-3xl font-bold">{overallProgress}%</div>
            <div className="mt-2 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-orange-500 to-amber-500"
                style={{ width: `${overallProgress}%` }}
              />
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <Award className="w-8 h-8 text-green-500" />
              <span className="text-sm text-slate-400">Marks Earned</span>
            </div>
            <div className="text-3xl font-bold">{earnedMarks}<span className="text-lg text-slate-400">/{totalMarks}</span></div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <BarChart3 className="w-8 h-8 text-blue-500" />
              <span className="text-sm text-slate-400">Criteria Status</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold">{criteria.filter(c => c.status === 'in_progress').length}</span>
              <span className="text-slate-400">in progress</span>
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-3">
              <CheckCircle2 className="w-8 h-8 text-emerald-500" />
              <span className="text-sm text-slate-400">Completed</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold">{criteria.filter(c => c.status === 'approved').length}</span>
              <span className="text-slate-400">of 7 criteria</span>
            </div>
          </div>
        </div>

        {/* Criteria List */}
        <div className="space-y-4">
          {criteria.map((criterion) => {
            const info = CRITERIA_INFO.find(c => c.number === criterion.number)
            const Icon = info?.icon || FileText

            return (
              <Link
                key={criterion.number}
                href={`/accreditation/criterion/${criterion.number}`}
                className="block bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-orange-500/50 transition-all hover:shadow-lg hover:shadow-orange-500/5"
              >
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className={`p-3 bg-${info?.color || 'orange'}-500/20 rounded-xl`}>
                    <Icon className={`w-6 h-6 text-${info?.color || 'orange'}-500`} />
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h3 className="font-semibold text-lg">Criterion {criterion.number}</h3>
                        <p className="text-slate-400">{criterion.name}</p>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-orange-500">{criterion.marks}</div>
                        <div className="text-xs text-slate-400">marks</div>
                      </div>
                    </div>

                    {/* Progress */}
                    <div className="flex items-center gap-4 mb-3">
                      <div className="flex-1">
                        <div className="flex items-center justify-between text-sm mb-1">
                          <span className="text-slate-400">Progress</span>
                          <span className="font-medium">{criterion.progress}%</span>
                        </div>
                        <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-orange-500 to-amber-500 transition-all"
                            style={{ width: `${criterion.progress}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-sm text-slate-400">
                        {criterion.earnedMarks}/{criterion.marks} marks
                      </div>
                    </div>

                    {/* Meta Info */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4 text-sm">
                        {getStatusBadge(criterion.status)}
                        <span className="text-slate-500">
                          {criterion.completedIndicators}/{criterion.keyIndicators} Key Indicators
                        </span>
                        {criterion.lastUpdated && (
                          <span className="text-slate-500">
                            Updated {criterion.lastUpdated}
                          </span>
                        )}
                      </div>
                      <ChevronRight className="w-5 h-5 text-slate-500" />
                    </div>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>

        {/* NAAC Grading Scale */}
        <div className="mt-8 bg-slate-900 border border-slate-800 rounded-xl p-6">
          <h3 className="font-semibold mb-4">NAAC Grading Scale</h3>
          <div className="grid grid-cols-4 md:grid-cols-8 gap-3">
            {[
              { grade: 'A++', cgpa: '3.51-4.00', color: 'bg-green-500' },
              { grade: 'A+', cgpa: '3.26-3.50', color: 'bg-green-400' },
              { grade: 'A', cgpa: '3.01-3.25', color: 'bg-emerald-500' },
              { grade: 'B++', cgpa: '2.76-3.00', color: 'bg-yellow-500' },
              { grade: 'B+', cgpa: '2.51-2.75', color: 'bg-yellow-400' },
              { grade: 'B', cgpa: '2.01-2.50', color: 'bg-orange-500' },
              { grade: 'C', cgpa: '1.51-2.00', color: 'bg-orange-400' },
              { grade: 'D', cgpa: '≤1.50', color: 'bg-red-500' },
            ].map(item => (
              <div key={item.grade} className="text-center p-3 bg-slate-800 rounded-lg">
                <div className={`w-10 h-10 ${item.color} rounded-full mx-auto mb-2 flex items-center justify-center text-white font-bold`}>
                  {item.grade}
                </div>
                <div className="text-xs text-slate-400">{item.cgpa}</div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
