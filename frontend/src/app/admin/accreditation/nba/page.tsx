'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  Target,
  BookOpen,
  Award,
  TrendingUp,
  Users,
  Building2,
  ChevronRight,
  Loader2,
  AlertCircle,
  Download,
  RefreshCw,
  GraduationCap,
  LineChart,
  FileText,
  CheckCircle2,
  BarChart3,
  Layers,
  Settings,
  ClipboardCheck,
  Microscope,
  Eye,
  Calendar,
  Clock,
  Building,
  Cpu,
  FlaskConical,
  Heart
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'
import AccreditationNav from '@/components/AccreditationNav'
import {
  SAMPLE_PROGRAMS,
  SAMPLE_PEOS,
  PROGRAM_OUTCOMES,
  SAMPLE_PO_ATTAINMENT,
  SAMPLE_FACULTY,
  FACULTY_SUMMARY,
  SAMPLE_STUDENT_PERFORMANCE,
  NBA_CRITERIA_SCORES,
  NBA_DASHBOARD_STATS,
  NBA_CRITERIA,
  SAMPLE_COURSES,
  getProgramById,
  type NBAProgram,
  type Faculty,
  type POAttainment
} from '@/data/sampleNBAData'

interface DashboardStats {
  total_programs: number
  active_programs: number
  ug_programs: number
  pg_programs: number
  total_pos: number
  total_cos: number
  co_attainment_records: number
  average_co_attainment: number
  po_attainment_records: number
  average_po_attainment: number
  programs_above_target: number
  total_faculty: number
  faculty_with_phd: number
  total_lab_facilities: number
  active_labs: number
  total_improvements: number
  completed_improvements: number
  pending_improvements: number
  total_result_analysis: number
  average_pass_percentage: number
}

const KEY_INDICATORS = [
  {
    id: '1',
    name: 'Vision, Mission & PEOs',
    description: 'Program educational objectives aligned with institution vision',
    icon: Target,
    links: [
      { name: 'Programs', href: '/admin/accreditation/nba/programs' },
      { name: 'PEOs', href: '/admin/accreditation/nba/peos' }
    ],
    color: 'blue'
  },
  {
    id: '2',
    name: 'Program Curriculum',
    description: 'Curriculum design with OBE framework and industry relevance',
    icon: BookOpen,
    links: [
      { name: 'Curriculum', href: '/admin/accreditation/nba/curriculum' }
    ],
    color: 'green'
  },
  {
    id: '3',
    name: 'Course Outcomes',
    description: 'CO statements with Bloom\'s taxonomy and assessment methods',
    icon: Layers,
    links: [
      { name: 'Course Outcomes', href: '/admin/accreditation/nba/course-outcomes' },
      { name: 'CO-PO Mapping', href: '/admin/accreditation/nba/co-po-mapping' }
    ],
    color: 'purple'
  },
  {
    id: '4',
    name: 'Students\' Performance',
    description: 'Academic performance, result analysis, and progression',
    icon: GraduationCap,
    links: [
      { name: 'Result Analysis', href: '/admin/accreditation/nba/result-analysis' },
      { name: 'Student Performance', href: '/admin/accreditation/nba/performance' }
    ],
    color: 'orange'
  },
  {
    id: '5',
    name: 'Faculty Information',
    description: 'Faculty qualifications, contributions, and development',
    icon: Users,
    links: [
      { name: 'Faculty', href: '/admin/accreditation/nba/faculty' },
      { name: 'Faculty Contributions', href: '/admin/accreditation/nba/faculty-contributions' }
    ],
    color: 'teal'
  },
  {
    id: '6',
    name: 'Facilities & Support',
    description: 'Laboratory facilities, infrastructure, and technical support',
    icon: Building2,
    links: [
      { name: 'Lab Facilities', href: '/admin/accreditation/nba/lab-facilities' }
    ],
    color: 'yellow'
  },
  {
    id: '7-9',
    name: 'Attainment & Assessment',
    description: 'CO/PO attainment calculation and gap analysis',
    icon: BarChart3,
    links: [
      { name: 'CO Attainment', href: '/admin/accreditation/nba/co-attainment' },
      { name: 'PO Attainment', href: '/admin/accreditation/nba/po-attainment' }
    ],
    color: 'red'
  },
  {
    id: '10',
    name: 'Continuous Improvement',
    description: 'Action plans based on attainment gaps and feedback',
    icon: TrendingUp,
    links: [
      { name: 'Improvements', href: '/admin/accreditation/nba/continuous-improvement' }
    ],
    color: 'indigo'
  }
]

export default function NBADashboardPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<'overview' | 'programs' | 'attainment' | 'faculty'>('overview')
  const [selectedProgram, setSelectedProgram] = useState<string>('prog-001')
  const [academicYear, setAcademicYear] = useState('2024-25')
  const [isGeneratingReport, setIsGeneratingReport] = useState(false)

  // Use sample data directly
  const stats: DashboardStats = {
    total_programs: NBA_DASHBOARD_STATS.total_programs,
    active_programs: NBA_DASHBOARD_STATS.accredited_programs,
    ug_programs: NBA_DASHBOARD_STATS.tier1_programs,
    pg_programs: NBA_DASHBOARD_STATS.tier2_programs,
    total_pos: 12,
    total_cos: 150,
    co_attainment_records: 45,
    average_co_attainment: 82.5,
    po_attainment_records: 60,
    average_po_attainment: NBA_DASHBOARD_STATS.avg_po_attainment,
    programs_above_target: 4,
    total_faculty: NBA_DASHBOARD_STATS.total_faculty,
    faculty_with_phd: Math.round(NBA_DASHBOARD_STATS.total_faculty * NBA_DASHBOARD_STATS.phd_percentage / 100),
    total_lab_facilities: NBA_DASHBOARD_STATS.total_labs,
    active_labs: NBA_DASHBOARD_STATS.total_labs,
    total_improvements: 15,
    completed_improvements: 12,
    pending_improvements: 3,
    total_result_analysis: 20,
    average_pass_percentage: NBA_DASHBOARD_STATS.avg_placement
  }

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true)
    // Simulate report generation
    setTimeout(() => {
      setIsGeneratingReport(false)
      alert('SAR Report generated successfully!')
    }, 2000)
  }

  const getColorClasses = (color: string) => {
    const colors: Record<string, { bg: string; border: string; text: string; icon: string; solid: string }> = {
      blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30', text: 'text-blue-400', icon: 'text-blue-500', solid: 'bg-blue-500' },
      purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/30', text: 'text-purple-400', icon: 'text-purple-500', solid: 'bg-purple-500' },
      green: { bg: 'bg-green-500/10', border: 'border-green-500/30', text: 'text-green-400', icon: 'text-green-500', solid: 'bg-green-500' },
      orange: { bg: 'bg-orange-500/10', border: 'border-orange-500/30', text: 'text-orange-400', icon: 'text-orange-500', solid: 'bg-orange-500' },
      red: { bg: 'bg-red-500/10', border: 'border-red-500/30', text: 'text-red-400', icon: 'text-red-500', solid: 'bg-red-500' },
      yellow: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: 'text-yellow-500', solid: 'bg-yellow-500' },
      teal: { bg: 'bg-teal-500/10', border: 'border-teal-500/30', text: 'text-teal-400', icon: 'text-teal-500', solid: 'bg-teal-500' },
      indigo: { bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', text: 'text-indigo-400', icon: 'text-indigo-500', solid: 'bg-indigo-500' },
      cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', text: 'text-cyan-400', icon: 'text-cyan-500', solid: 'bg-cyan-500' },
      pink: { bg: 'bg-pink-500/10', border: 'border-pink-500/30', text: 'text-pink-400', icon: 'text-pink-500', solid: 'bg-pink-500' },
    }
    return colors[color] || colors.blue
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'accredited': return 'green'
      case 'under_review': return 'yellow'
      case 'expired': return 'red'
      default: return 'slate'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'accredited': return 'Accredited'
      case 'under_review': return 'Under Review'
      case 'expired': return 'Expired'
      case 'not_applied': return 'Not Applied'
      default: return status
    }
  }

  // Get selected program data
  const selectedProgramData = getProgramById(selectedProgram)
  const selectedPOAttainment = SAMPLE_PO_ATTAINMENT[selectedProgram]
  const selectedFaculty = SAMPLE_FACULTY[selectedProgram] || []
  const selectedFacultySummary = FACULTY_SUMMARY[selectedProgram]
  const selectedPerformance = SAMPLE_STUDENT_PERFORMANCE[selectedProgram]
  const selectedCriteriaScores = NBA_CRITERIA_SCORES[selectedProgram]
  const selectedCourses = SAMPLE_COURSES[selectedProgram] || []

  if (authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <AccreditationNav />

      {/* Header */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 text-sm text-slate-400 mb-2">
                <Link href="/admin/accreditation" className="hover:text-white">Accreditation</Link>
                <ChevronRight className="w-4 h-4" />
                <span className="text-white">NBA</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <Award className="w-8 h-8 text-yellow-500" />
                NBA Accreditation - Outcome Based Education
              </h1>
              <p className="text-slate-400 mt-1">Program-level accreditation with CO-PO attainment tracking</p>
            </div>
            <div className="flex items-center gap-4">
              <select
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
              >
                <option value="2024-25">2024-25</option>
                <option value="2023-24">2023-24</option>
                <option value="2022-23">2022-23</option>
              </select>
              <button
                onClick={handleGenerateReport}
                disabled={isGeneratingReport}
                className="flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black rounded-lg disabled:opacity-50 font-medium"
              >
                {isGeneratingReport ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                Generate SAR
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Key Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-8">
          <StatCard icon={Target} label="Programs" value={stats.total_programs} subValue={`${stats.active_programs} accredited`} color="blue" />
          <StatCard icon={Layers} label="Course Outcomes" value={stats.total_cos} subValue={`${stats.total_pos} POs`} color="purple" />
          <StatCard icon={BarChart3} label="Avg CO Attain" value={`${stats.average_co_attainment.toFixed(1)}%`} color="green" />
          <StatCard icon={LineChart} label="Avg PO Attain" value={`${stats.average_po_attainment.toFixed(1)}%`} color="orange" />
          <StatCard icon={Users} label="Faculty" value={stats.total_faculty} subValue={`${stats.faculty_with_phd} PhD`} color="teal" />
          <StatCard icon={Microscope} label="Labs" value={stats.total_lab_facilities} color="yellow" />
          <StatCard icon={CheckCircle2} label="Pass %" value={`${stats.average_pass_percentage}%`} color="cyan" />
          <StatCard icon={TrendingUp} label="Improvements" value={`${stats.completed_improvements}/${stats.total_improvements}`} color="indigo" />
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'programs', label: 'Programs', icon: Target },
            { id: 'attainment', label: 'PO Attainment', icon: LineChart },
            { id: 'faculty', label: 'Faculty', icon: Users },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-yellow-500 text-black'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <>
            {/* NBA Criteria (Tier-1) */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <ClipboardCheck className="w-5 h-5 text-yellow-500" />
                NBA Tier-1 Criteria (1000 Marks)
              </h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {NBA_CRITERIA.tier1.criteria.map((criterion, idx) => {
                  const colors = ['blue', 'green', 'purple', 'orange', 'teal', 'yellow', 'red', 'indigo']
                  const color = colors[idx % colors.length]
                  const colorClasses = getColorClasses(color)
                  return (
                    <div key={criterion.id} className={`p-4 ${colorClasses.bg} border ${colorClasses.border} rounded-xl`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className={`text-xs font-medium ${colorClasses.text}`}>Criterion {criterion.id}</span>
                        <span className="text-sm font-bold">{criterion.marks}</span>
                      </div>
                      <h3 className="text-sm font-medium">{criterion.name}</h3>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Key Indicators */}
            <div className="mb-8">
              <h2 className="text-lg font-semibold mb-4">Quick Access</h2>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
                {KEY_INDICATORS.map((indicator) => {
                  const colorClasses = getColorClasses(indicator.color)
                  const Icon = indicator.icon
                  return (
                    <div key={indicator.id} className={`p-4 ${colorClasses.bg} border ${colorClasses.border} rounded-xl`}>
                      <div className="flex items-start gap-3 mb-2">
                        <div className={`p-2 rounded-lg ${colorClasses.bg}`}>
                          <Icon className={`w-4 h-4 ${colorClasses.icon}`} />
                        </div>
                        <div>
                          <div className={`text-xs font-medium ${colorClasses.text}`}>Criterion {indicator.id}</div>
                          <h3 className="font-semibold text-sm">{indicator.name}</h3>
                        </div>
                      </div>
                      <p className="text-xs text-slate-400 mb-2">{indicator.description}</p>
                      <div className="flex flex-wrap gap-1">
                        {indicator.links.map((link) => (
                          <Link
                            key={link.href}
                            href={link.href}
                            className={`text-xs px-2 py-1 ${colorClasses.bg} ${colorClasses.text} rounded-full hover:opacity-80 transition-opacity`}
                          >
                            {link.name}
                          </Link>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}

        {/* Programs Tab */}
        {activeTab === 'programs' && (
          <>
            {/* Program Cards */}
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
              {SAMPLE_PROGRAMS.map(program => {
                const statusColor = getStatusColor(program.accreditation_status)
                const colorClasses = getColorClasses(statusColor)
                const isSelected = selectedProgram === program.id
                return (
                  <div
                    key={program.id}
                    onClick={() => setSelectedProgram(program.id)}
                    className={`p-5 rounded-xl cursor-pointer transition-all ${
                      isSelected
                        ? `${colorClasses.bg} border-2 ${colorClasses.border}`
                        : 'bg-slate-900 border border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className={`px-3 py-1 ${colorClasses.solid} text-white text-xs font-bold rounded-full`}>
                        {program.code}
                      </div>
                      <span className={`px-2 py-1 ${colorClasses.bg} ${colorClasses.text} text-xs rounded-full border ${colorClasses.border}`}>
                        {getStatusLabel(program.accreditation_status)}
                      </span>
                    </div>
                    <h3 className="font-semibold mb-1">{program.name}</h3>
                    <p className="text-sm text-slate-400 mb-3">{program.department}</p>
                    <div className="grid grid-cols-3 gap-2 text-center">
                      <div className="bg-slate-800 rounded-lg p-2">
                        <p className="text-lg font-bold">{program.intake}</p>
                        <p className="text-xs text-slate-400">Intake</p>
                      </div>
                      <div className="bg-slate-800 rounded-lg p-2">
                        <p className="text-lg font-bold">{program.duration_years}Y</p>
                        <p className="text-xs text-slate-400">Duration</p>
                      </div>
                      <div className="bg-slate-800 rounded-lg p-2">
                        <p className={`text-lg font-bold ${colorClasses.text}`}>{program.percentage}%</p>
                        <p className="text-xs text-slate-400">Score</p>
                      </div>
                    </div>
                    {program.validity_end && (
                      <p className="text-xs text-slate-500 mt-3 flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        Valid till: {program.validity_end}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Selected Program Details */}
            {selectedProgramData && selectedCriteriaScores && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <Target className="w-5 h-5 text-yellow-500" />
                  {selectedProgramData.name} - Criteria Scores
                </h3>
                <div className="grid md:grid-cols-4 gap-4 mb-6">
                  {selectedCriteriaScores.criteria_scores.map(criterion => {
                    const percentage = criterion.percentage
                    let color = 'green'
                    if (percentage < 70) color = 'red'
                    else if (percentage < 80) color = 'orange'
                    else if (percentage < 90) color = 'yellow'
                    const colorClasses = getColorClasses(color)
                    return (
                      <div key={criterion.id} className={`p-4 ${colorClasses.bg} border ${colorClasses.border} rounded-xl`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">C{criterion.id}</span>
                          <span className={`text-lg font-bold ${colorClasses.text}`}>{criterion.score}/{criterion.max}</span>
                        </div>
                        <p className="text-xs text-slate-400 mb-2">{criterion.name}</p>
                        <div className="bg-slate-800 rounded-full h-2">
                          <div className={`h-2 rounded-full ${colorClasses.solid}`} style={{ width: `${percentage}%` }} />
                        </div>
                        <p className={`text-xs ${colorClasses.text} mt-1 text-right`}>{percentage.toFixed(1)}%</p>
                      </div>
                    )
                  })}
                </div>
                <div className="flex items-center justify-between p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                  <div>
                    <p className="text-sm text-slate-400">Total Score</p>
                    <p className="text-2xl font-bold text-yellow-400">{selectedCriteriaScores.total_score} / {selectedCriteriaScores.total_marks}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-slate-400">Overall</p>
                    <p className="text-2xl font-bold text-yellow-400">{selectedCriteriaScores.overall_percentage}%</p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}

        {/* PO Attainment Tab */}
        {activeTab === 'attainment' && selectedPOAttainment && (
          <>
            {/* Program Selector */}
            <div className="flex items-center gap-4 mb-6">
              <label className="text-sm text-slate-400">Select Program:</label>
              <select
                value={selectedProgram}
                onChange={e => setSelectedProgram(e.target.value)}
                className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2"
              >
                {SAMPLE_PROGRAMS.map(p => (
                  <option key={p.id} value={p.id}>{p.code} - {p.name}</option>
                ))}
              </select>
            </div>

            {/* 12 Program Outcomes */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <LineChart className="w-5 h-5 text-orange-500" />
                Program Outcomes Attainment (Batch: {selectedPOAttainment.batch})
              </h3>
              <p className="text-sm text-slate-400 mb-4">Method: {selectedPOAttainment.attainment_method}</p>
              <div className="grid md:grid-cols-3 lg:grid-cols-4 gap-4">
                {PROGRAM_OUTCOMES.map(po => {
                  const attainment = selectedPOAttainment.po_attainment[po.id]
                  if (!attainment) return null
                  const isAchieved = attainment.status === 'achieved'
                  const color = isAchieved ? 'green' : 'red'
                  const colorClasses = getColorClasses(color)
                  return (
                    <div key={po.id} className={`p-4 ${colorClasses.bg} border ${colorClasses.border} rounded-xl`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold">{po.id}</span>
                        {isAchieved ? (
                          <CheckCircle2 className={`w-5 h-5 ${colorClasses.text}`} />
                        ) : (
                          <AlertCircle className={`w-5 h-5 ${colorClasses.text}`} />
                        )}
                      </div>
                      <p className="text-xs text-slate-400 mb-3">{po.name}</p>
                      <div className="space-y-1 text-xs">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Direct:</span>
                          <span>{attainment.direct}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Indirect:</span>
                          <span>{attainment.indirect}%</span>
                        </div>
                        <div className="flex justify-between font-bold">
                          <span>Overall:</span>
                          <span className={colorClasses.text}>{attainment.overall}%</span>
                        </div>
                        <div className="flex justify-between text-slate-500">
                          <span>Target:</span>
                          <span>{attainment.target}%</span>
                        </div>
                      </div>
                      <div className="mt-3 bg-slate-800 rounded-full h-2">
                        <div className={`h-2 rounded-full ${colorClasses.solid}`} style={{ width: `${Math.min(attainment.overall, 100)}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* PSO Attainment */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
              <h3 className="font-semibold mb-4">Program Specific Outcomes (PSOs)</h3>
              <div className="grid md:grid-cols-3 gap-4">
                {Object.entries(selectedPOAttainment.pso_attainment).map(([psoId, attainment]) => {
                  const isAchieved = attainment.status === 'achieved'
                  const color = isAchieved ? 'green' : 'red'
                  const colorClasses = getColorClasses(color)
                  return (
                    <div key={psoId} className={`p-4 ${colorClasses.bg} border ${colorClasses.border} rounded-xl`}>
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-bold">{psoId}</span>
                        <span className={`text-xl font-bold ${colorClasses.text}`}>{attainment.overall}%</span>
                      </div>
                      <div className="bg-slate-800 rounded-full h-2">
                        <div className={`h-2 rounded-full ${colorClasses.solid}`} style={{ width: `${attainment.overall}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Sample Courses with CO Attainment */}
            {selectedCourses.length > 0 && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4">Sample Courses - CO Attainment</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700">
                        <th className="text-left py-3 px-4">Code</th>
                        <th className="text-left py-3 px-4">Course Name</th>
                        <th className="text-center py-3 px-4">Credits</th>
                        <th className="text-center py-3 px-4">Sem</th>
                        <th className="text-center py-3 px-4">Direct</th>
                        <th className="text-center py-3 px-4">Indirect</th>
                        <th className="text-center py-3 px-4">Overall</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedCourses.map(course => {
                        const overall = course.attainment.overall
                        let color = 'green'
                        if (overall < 60) color = 'red'
                        else if (overall < 70) color = 'orange'
                        else if (overall < 80) color = 'yellow'
                        const colorClasses = getColorClasses(color)
                        return (
                          <tr key={course.code} className="border-b border-slate-800">
                            <td className="py-3 px-4 font-mono font-bold">{course.code}</td>
                            <td className="py-3 px-4">{course.name}</td>
                            <td className="py-3 px-4 text-center">{course.credits}</td>
                            <td className="py-3 px-4 text-center">{course.semester}</td>
                            <td className="py-3 px-4 text-center">{course.attainment.direct}%</td>
                            <td className="py-3 px-4 text-center">{course.attainment.indirect}%</td>
                            <td className="py-3 px-4 text-center">
                              <span className={`px-2 py-1 ${colorClasses.bg} ${colorClasses.text} rounded font-bold`}>
                                {course.attainment.overall}%
                              </span>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {/* Faculty Tab */}
        {activeTab === 'faculty' && (
          <>
            {/* Faculty Summary */}
            {selectedFacultySummary && (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-blue-400">{selectedFacultySummary.total_faculty}</p>
                  <p className="text-xs text-slate-400">Total Faculty</p>
                </div>
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-purple-400">{selectedFacultySummary.phd_percentage}%</p>
                  <p className="text-xs text-slate-400">PhD Holders</p>
                </div>
                <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-green-400">{selectedFacultySummary.avg_experience}y</p>
                  <p className="text-xs text-slate-400">Avg Experience</p>
                </div>
                <div className="bg-orange-500/10 border border-orange-500/30 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-orange-400">{selectedFacultySummary.total_publications}</p>
                  <p className="text-xs text-slate-400">Publications</p>
                </div>
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-yellow-400">{selectedFacultySummary.total_patents}</p>
                  <p className="text-xs text-slate-400">Patents</p>
                </div>
                <div className="bg-teal-500/10 border border-teal-500/30 rounded-xl p-4 text-center">
                  <p className="text-2xl font-bold text-teal-400">{selectedFacultySummary.total_funding_lakhs}L</p>
                  <p className="text-xs text-slate-400">Project Funding</p>
                </div>
              </div>
            )}

            {/* Faculty List */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Users className="w-5 h-5 text-teal-500" />
                Faculty Members - {selectedProgramData?.code}
              </h3>
              <div className="grid md:grid-cols-2 gap-4">
                {selectedFaculty.map(faculty => (
                  <div key={faculty.id} className="p-4 bg-slate-800 rounded-xl">
                    <div className="flex items-start gap-4">
                      <div className="w-12 h-12 bg-teal-500 rounded-full flex items-center justify-center text-white font-bold">
                        {faculty.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold">{faculty.name}</h4>
                        <p className="text-sm text-teal-400">{faculty.designation}</p>
                        <p className="text-xs text-slate-400 mt-1">{faculty.qualification}</p>
                        <p className="text-xs text-slate-500">{faculty.specialization}</p>
                        <div className="grid grid-cols-4 gap-2 mt-3">
                          <div className="text-center">
                            <p className="text-sm font-bold">{faculty.experience_years}y</p>
                            <p className="text-xs text-slate-500">Exp</p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-bold">{faculty.publications}</p>
                            <p className="text-xs text-slate-500">Pubs</p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-bold">{faculty.h_index}</p>
                            <p className="text-xs text-slate-500">h-index</p>
                          </div>
                          <div className="text-center">
                            <p className="text-sm font-bold">{faculty.patents}</p>
                            <p className="text-xs text-slate-500">Patents</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Student Performance */}
            {selectedPerformance && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mt-8">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-orange-500" />
                  Student Performance - Batch {selectedPerformance.batch}
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold">{selectedPerformance.enrolled}</p>
                    <p className="text-xs text-slate-400">Enrolled</p>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-green-400">{selectedPerformance.pass_percentage}%</p>
                    <p className="text-xs text-slate-400">Pass %</p>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-blue-400">{selectedPerformance.placement_percentage}%</p>
                    <p className="text-xs text-slate-400">Placement</p>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-purple-400">{selectedPerformance.avg_salary_lpa} LPA</p>
                    <p className="text-xs text-slate-400">Avg Salary</p>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-yellow-400">{selectedPerformance.max_salary_lpa} LPA</p>
                    <p className="text-xs text-slate-400">Max Salary</p>
                  </div>
                  <div className="bg-slate-800 rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-teal-400">{selectedPerformance.companies_visited}</p>
                    <p className="text-xs text-slate-400">Companies</p>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  subValue,
  color
}: {
  icon: any
  label: string
  value: string | number
  subValue?: string
  color: string
}) {
  const colorClasses: Record<string, string> = {
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    green: 'text-green-400',
    orange: 'text-orange-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    teal: 'text-teal-400',
    indigo: 'text-indigo-400',
    cyan: 'text-cyan-400',
    pink: 'text-pink-400'
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <Icon className={`w-5 h-5 ${colorClasses[color]} mb-2`} />
      <p className="text-xl font-bold">{value}</p>
      <p className="text-xs text-slate-400">{label}</p>
      {subValue && <p className={`text-xs ${colorClasses[color]} mt-1`}>{subValue}</p>}
    </div>
  )
}
