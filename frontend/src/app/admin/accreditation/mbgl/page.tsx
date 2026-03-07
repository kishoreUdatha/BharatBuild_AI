'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  TrendingUp,
  ArrowLeft,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Save,
  Download,
  RefreshCw,
  Target,
  Users,
  Cpu,
  Lightbulb,
  BarChart3,
  Heart,
  Leaf,
  Award,
  Info,
  Shield,
  Building,
  Calendar,
  FileText,
  Eye,
  ChevronDown
} from 'lucide-react'
import AccreditationNav from '@/components/AccreditationNav'
import {
  SAMPLE_INSTITUTIONS,
  SAMPLE_APPLICATIONS,
  SAMPLE_MBGL_ASSESSMENTS,
  MBGL_LEVEL_CRITERIA,
  SAMPLE_ATTRIBUTE_SCORES_APP1,
  SAMPLE_ATTRIBUTE_SCORES_APP3,
  DASHBOARD_STATS,
  getInstitutionById,
  getMBGLLevelLabel,
  getBinaryStatusLabel,
  type MBGLLevel,
  type BinaryStatus,
  type MBGLAssessment as SampleMBGLAssessment
} from '@/data/sampleAccreditationData'

// MBGL Level Type
type MBGLLevelType = 'not_assessed' | 'level_1' | 'level_2' | 'level_3' | 'level_4' | 'level_5'

// Maturity Dimension Interface
interface MaturityDimension {
  id: string
  name: string
  description: string
  icon: any
  color: string
  score: number
  indicators: string[]
}

// MBGL Assessment Interface
interface MBGLAssessment {
  assessment_year: string
  assessment_date: string
  dimensions: {
    leadership: number
    process: number
    people: number
    technology: number
    outcome: number
    innovation: number
    stakeholder: number
    sustainability: number
  }
  strengths: string[]
  improvements: string[]
  action_plan: string
}

const MBGL_LEVELS = [
  { value: 'not_assessed', label: 'Not Assessed', number: 0, color: 'slate', minScore: 0 },
  { value: 'level_1', label: 'Level 1 - Basic Compliance', number: 1, color: 'red', minScore: 1.0 },
  { value: 'level_2', label: 'Level 2 - Developing', number: 2, color: 'orange', minScore: 2.0 },
  { value: 'level_3', label: 'Level 3 - Established', number: 3, color: 'yellow', minScore: 3.0 },
  { value: 'level_4', label: 'Level 4 - Advanced', number: 4, color: 'blue', minScore: 4.0 },
  { value: 'level_5', label: 'Level 5 - Excellence', number: 5, color: 'green', minScore: 4.5 }
]

const MATURITY_DIMENSIONS: MaturityDimension[] = [
  {
    id: 'leadership',
    name: 'Leadership Maturity',
    description: 'Vision, governance, strategic planning, and institutional leadership',
    icon: Target,
    color: 'blue',
    score: 1,
    indicators: ['Clear vision & mission', 'Participative governance', 'Strategic planning', 'Change management']
  },
  {
    id: 'process',
    name: 'Process Maturity',
    description: 'Quality processes, documentation, and continuous improvement',
    icon: BarChart3,
    color: 'green',
    score: 1,
    indicators: ['Documented processes', 'Quality standards', 'Audit mechanisms', 'Process optimization']
  },
  {
    id: 'people',
    name: 'People Maturity',
    description: 'Faculty development, student support, and human resources',
    icon: Users,
    color: 'purple',
    score: 1,
    indicators: ['Faculty development', 'Student-centric approach', 'Staff welfare', 'Skill development']
  },
  {
    id: 'technology',
    name: 'Technology Maturity',
    description: 'ICT infrastructure, digital learning, and technology adoption',
    icon: Cpu,
    color: 'cyan',
    score: 1,
    indicators: ['Digital infrastructure', 'LMS adoption', 'Smart classrooms', 'Digital records']
  },
  {
    id: 'outcome',
    name: 'Outcome Maturity',
    description: 'Learning outcomes, placements, and institutional achievements',
    icon: Award,
    color: 'orange',
    score: 1,
    indicators: ['Graduate outcomes', 'Placement success', 'Research output', 'Student achievements']
  },
  {
    id: 'innovation',
    name: 'Innovation Maturity',
    description: 'Research culture, innovation ecosystem, and entrepreneurship',
    icon: Lightbulb,
    color: 'yellow',
    score: 1,
    indicators: ['Research promotion', 'Innovation cells', 'Startup incubation', 'IPR awareness']
  },
  {
    id: 'stakeholder',
    name: 'Stakeholder Maturity',
    description: 'Engagement with students, alumni, industry, and community',
    icon: Heart,
    color: 'pink',
    score: 1,
    indicators: ['Student feedback', 'Alumni engagement', 'Industry collaboration', 'Community outreach']
  },
  {
    id: 'sustainability',
    name: 'Sustainability Maturity',
    description: 'Environmental practices, social responsibility, and institutional sustainability',
    icon: Leaf,
    color: 'teal',
    score: 1,
    indicators: ['Green practices', 'Energy efficiency', 'Waste management', 'Social responsibility']
  }
]

const defaultAssessment: MBGLAssessment = {
  assessment_year: '2025-26',
  assessment_date: new Date().toISOString().split('T')[0],
  dimensions: {
    leadership: 1,
    process: 1,
    people: 1,
    technology: 1,
    outcome: 1,
    innovation: 1,
    stakeholder: 1,
    sustainability: 1
  },
  strengths: [],
  improvements: [],
  action_plan: ''
}

export default function MBGLAssessmentPage() {
  const router = useRouter()
  const [assessment, setAssessment] = useState<MBGLAssessment>(defaultAssessment)
  const [saved, setSaved] = useState(false)
  const [binaryStatus, setBinaryStatus] = useState<string>('accredited')
  const [newStrength, setNewStrength] = useState('')
  const [newImprovement, setNewImprovement] = useState('')
  const [activeTab, setActiveTab] = useState<'assessment' | 'samples' | 'comparison'>('samples')
  const [selectedSample, setSelectedSample] = useState<string>('app-001')

  useEffect(() => {
    // Load saved assessment
    const savedAssessment = localStorage.getItem('naac_mbgl_assessment')
    if (savedAssessment) {
      setAssessment(JSON.parse(savedAssessment))
    }

    // Load binary status from profile
    const profile = localStorage.getItem('naac_institution_profile')
    if (profile) {
      const parsed = JSON.parse(profile)
      setBinaryStatus(parsed.binary_status || 'accredited')
    }
  }, [])

  // Load sample data when selected
  useEffect(() => {
    const sampleData = SAMPLE_MBGL_ASSESSMENTS.find(s => s.applicationId === selectedSample)
    if (sampleData) {
      setAssessment({
        assessment_year: sampleData.assessmentYear,
        assessment_date: sampleData.assessmentDate,
        dimensions: {
          leadership: sampleData.leadershipMaturity,
          process: sampleData.processMaturity,
          people: sampleData.peopleMaturity,
          technology: sampleData.technologyMaturity,
          outcome: sampleData.outcomeMaturity,
          innovation: sampleData.innovationMaturity,
          stakeholder: sampleData.stakeholderMaturity,
          sustainability: sampleData.sustainabilityMaturity
        },
        strengths: sampleData.strengths,
        improvements: sampleData.improvementsNeeded,
        action_plan: sampleData.actionPlan
      })
    }
  }, [selectedSample])

  const handleSave = () => {
    localStorage.setItem('naac_mbgl_assessment', JSON.stringify(assessment))

    // Also update the profile with calculated level
    const profile = localStorage.getItem('naac_institution_profile')
    if (profile) {
      const parsed = JSON.parse(profile)
      parsed.mbgl_level = calculatedLevel.value
      parsed.mbgl_score = (averageMaturity / 5) * 100
      parsed.mbgl_assessment_date = assessment.assessment_date
      localStorage.setItem('naac_institution_profile', JSON.stringify(parsed))
    }

    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  const updateDimension = (dimension: keyof MBGLAssessment['dimensions'], value: number) => {
    setAssessment(prev => ({
      ...prev,
      dimensions: {
        ...prev.dimensions,
        [dimension]: value
      }
    }))
  }

  const addStrength = () => {
    if (newStrength.trim()) {
      setAssessment(prev => ({
        ...prev,
        strengths: [...prev.strengths, newStrength.trim()]
      }))
      setNewStrength('')
    }
  }

  const removeStrength = (index: number) => {
    setAssessment(prev => ({
      ...prev,
      strengths: prev.strengths.filter((_, i) => i !== index)
    }))
  }

  const addImprovement = () => {
    if (newImprovement.trim()) {
      setAssessment(prev => ({
        ...prev,
        improvements: [...prev.improvements, newImprovement.trim()]
      }))
      setNewImprovement('')
    }
  }

  const removeImprovement = (index: number) => {
    setAssessment(prev => ({
      ...prev,
      improvements: prev.improvements.filter((_, i) => i !== index)
    }))
  }

  // Calculate average maturity
  const averageMaturity = Object.values(assessment.dimensions).reduce((a, b) => a + b, 0) / 8

  // Determine MBGL level based on average
  const calculatedLevel = MBGL_LEVELS.reduce((prev, curr) => {
    if (averageMaturity >= curr.minScore) return curr
    return prev
  }, MBGL_LEVELS[0])

  const getColorClasses = (color: string) => {
    const colors: Record<string, { bg: string; border: string; text: string }> = {
      blue: { bg: 'bg-blue-500/20', border: 'border-blue-500/30', text: 'text-blue-400' },
      green: { bg: 'bg-green-500/20', border: 'border-green-500/30', text: 'text-green-400' },
      purple: { bg: 'bg-purple-500/20', border: 'border-purple-500/30', text: 'text-purple-400' },
      cyan: { bg: 'bg-cyan-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400' },
      orange: { bg: 'bg-orange-500/20', border: 'border-orange-500/30', text: 'text-orange-400' },
      yellow: { bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', text: 'text-yellow-400' },
      pink: { bg: 'bg-pink-500/20', border: 'border-pink-500/30', text: 'text-pink-400' },
      teal: { bg: 'bg-teal-500/20', border: 'border-teal-500/30', text: 'text-teal-400' },
      red: { bg: 'bg-red-500/20', border: 'border-red-500/30', text: 'text-red-400' },
      slate: { bg: 'bg-slate-500/20', border: 'border-slate-500/30', text: 'text-slate-400' }
    }
    return colors[color] || colors.blue
  }

  const getLevelColor = (level: string) => {
    const colorMap: Record<string, string> = {
      slate: 'bg-slate-500',
      red: 'bg-red-500',
      orange: 'bg-orange-500',
      yellow: 'bg-yellow-500',
      blue: 'bg-blue-500',
      green: 'bg-green-500'
    }
    return colorMap[level] || 'bg-slate-500'
  }

  const isEligible = binaryStatus === 'accredited'

  // Get sample applications with MBGL assessments
  const applicationsWithMBGL = SAMPLE_APPLICATIONS.filter(app =>
    SAMPLE_MBGL_ASSESSMENTS.some(m => m.applicationId === app.id)
  )

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
                <span className="text-white">MBGL Assessment</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <TrendingUp className="w-8 h-8 text-green-500" />
                MBGL - Maturity-Based Graded Levels
              </h1>
              <p className="text-slate-400 mt-1">NAAC 2025 Framework - 8 Maturity Dimensions Assessment</p>
            </div>
            <div className="flex items-center gap-3">
              {saved && (
                <span className="flex items-center gap-2 text-green-400 text-sm">
                  <CheckCircle2 className="w-4 h-4" /> Saved
                </span>
              )}
              <button
                onClick={handleSave}
                disabled={!isEligible}
                className="flex items-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-700 disabled:cursor-not-allowed rounded-lg"
              >
                <Save className="w-4 h-4" />
                Save Assessment
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Dashboard Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <p className="text-xs text-slate-400">Total Applications</p>
            <p className="text-2xl font-bold text-white">{DASHBOARD_STATS.totalApplications}</p>
          </div>
          <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
            <p className="text-xs text-green-400">Accredited</p>
            <p className="text-2xl font-bold text-green-400">{DASHBOARD_STATS.accredited}</p>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4">
            <p className="text-xs text-yellow-400">Under Review</p>
            <p className="text-2xl font-bold text-yellow-400">{DASHBOARD_STATS.underReview}</p>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <p className="text-xs text-blue-400">Avg Maturity</p>
            <p className="text-2xl font-bold text-blue-400">{DASHBOARD_STATS.averageMaturityScore.toFixed(2)}</p>
          </div>
          <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
            <p className="text-xs text-purple-400">Completion Rate</p>
            <p className="text-2xl font-bold text-purple-400">{DASHBOARD_STATS.completionRate}%</p>
          </div>
          <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-xl p-4">
            <p className="text-xs text-cyan-400">Avg Processing</p>
            <p className="text-2xl font-bold text-cyan-400">{DASHBOARD_STATS.avgProcessingDays}d</p>
          </div>
        </div>

        {/* MBGL Distribution */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
          <h3 className="font-semibold mb-4">MBGL Level Distribution</h3>
          <div className="grid grid-cols-6 gap-3">
            {MBGL_LEVELS.map(level => {
              const count = DASHBOARD_STATS.mbglDistribution[level.value as keyof typeof DASHBOARD_STATS.mbglDistribution] || 0
              return (
                <div key={level.value} className={`p-4 rounded-xl text-center ${getColorClasses(level.color).bg} border ${getColorClasses(level.color).border}`}>
                  <div className={`text-3xl font-bold ${getColorClasses(level.color).text}`}>{count}</div>
                  <div className="text-xs mt-1 text-slate-400">{level.number === 0 ? 'Not Assessed' : `Level ${level.number}`}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setActiveTab('samples')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'samples'
                ? 'bg-green-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <Eye className="w-4 h-4 inline mr-2" />
            Sample Scenarios
          </button>
          <button
            onClick={() => setActiveTab('assessment')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'assessment'
                ? 'bg-green-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <FileText className="w-4 h-4 inline mr-2" />
            Your Assessment
          </button>
          <button
            onClick={() => setActiveTab('comparison')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'comparison'
                ? 'bg-green-500 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            <BarChart3 className="w-4 h-4 inline mr-2" />
            Comparison View
          </button>
        </div>

        {/* Sample Scenarios Tab */}
        {activeTab === 'samples' && (
          <>
            {/* Institution Selector */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
              <h3 className="font-semibold mb-4">Select Institution to View MBGL Assessment</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {applicationsWithMBGL.map(app => {
                  const institution = getInstitutionById(app.institutionId)
                  const mbglData = SAMPLE_MBGL_ASSESSMENTS.find(m => m.applicationId === app.id)
                  const isSelected = selectedSample === app.id
                  const levelInfo = MBGL_LEVELS.find(l => l.value === app.mbglLevel)

                  return (
                    <button
                      key={app.id}
                      onClick={() => setSelectedSample(app.id)}
                      className={`p-4 rounded-xl text-left transition-all ${
                        isSelected
                          ? `${getColorClasses(levelInfo?.color || 'green').bg} border-2 ${getColorClasses(levelInfo?.color || 'green').border}`
                          : 'bg-slate-800 border border-slate-700 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`w-12 h-12 ${getLevelColor(levelInfo?.color || 'green')} rounded-xl flex items-center justify-center text-white font-bold text-xl`}>
                          {levelInfo?.number || 0}
                        </div>
                        <div className="flex-1">
                          <h4 className="font-semibold">{institution?.name}</h4>
                          <p className="text-sm text-slate-400">{institution?.location}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <span className={`px-2 py-0.5 text-xs rounded-full ${getColorClasses(levelInfo?.color || 'green').bg} ${getColorClasses(levelInfo?.color || 'green').text}`}>
                              {levelInfo?.label}
                            </span>
                            <span className="text-xs text-slate-500">Score: {mbglData?.averageMaturity.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Selected Institution Details */}
            {(() => {
              const selectedApp = SAMPLE_APPLICATIONS.find(a => a.id === selectedSample)
              const selectedInst = selectedApp ? getInstitutionById(selectedApp.institutionId) : null
              const selectedMBGL = SAMPLE_MBGL_ASSESSMENTS.find(m => m.applicationId === selectedSample)
              const levelInfo = MBGL_LEVELS.find(l => l.value === selectedApp?.mbglLevel)

              if (!selectedApp || !selectedInst || !selectedMBGL) return null

              return (
                <>
                  {/* Institution Header */}
                  <div className={`${getColorClasses(levelInfo?.color || 'green').bg} border ${getColorClasses(levelInfo?.color || 'green').border} rounded-xl p-6 mb-6`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`w-20 h-20 ${getLevelColor(levelInfo?.color || 'green')} rounded-2xl flex items-center justify-center`}>
                          <span className="text-4xl font-bold text-white">{levelInfo?.number}</span>
                        </div>
                        <div>
                          <h2 className="text-xl font-bold">{selectedInst.name}</h2>
                          <p className="text-slate-400">{selectedInst.location} | Est. {selectedInst.established}</p>
                          <div className="flex items-center gap-4 mt-2">
                            <span className="text-sm"><Users className="w-4 h-4 inline mr-1" />{selectedInst.students} Students</span>
                            <span className="text-sm"><Building className="w-4 h-4 inline mr-1" />{selectedInst.faculty} Faculty</span>
                            <span className="text-sm"><Calendar className="w-4 h-4 inline mr-1" />Cycle {selectedApp.cycleNumber}</span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={`text-3xl font-bold ${getColorClasses(levelInfo?.color || 'green').text}`}>
                          {selectedMBGL.averageMaturity.toFixed(2)}
                        </p>
                        <p className="text-sm text-slate-400">Average Maturity</p>
                        <p className="text-sm mt-2">{levelInfo?.label}</p>
                      </div>
                    </div>
                  </div>

                  {/* Dimension Scores */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
                    <h3 className="font-semibold mb-4">8 Maturity Dimension Scores</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        { id: 'leadership', score: selectedMBGL.leadershipMaturity, icon: Target, color: 'blue', name: 'Leadership' },
                        { id: 'process', score: selectedMBGL.processMaturity, icon: BarChart3, color: 'green', name: 'Process' },
                        { id: 'people', score: selectedMBGL.peopleMaturity, icon: Users, color: 'purple', name: 'People' },
                        { id: 'technology', score: selectedMBGL.technologyMaturity, icon: Cpu, color: 'cyan', name: 'Technology' },
                        { id: 'outcome', score: selectedMBGL.outcomeMaturity, icon: Award, color: 'orange', name: 'Outcome' },
                        { id: 'innovation', score: selectedMBGL.innovationMaturity, icon: Lightbulb, color: 'yellow', name: 'Innovation' },
                        { id: 'stakeholder', score: selectedMBGL.stakeholderMaturity, icon: Heart, color: 'pink', name: 'Stakeholder' },
                        { id: 'sustainability', score: selectedMBGL.sustainabilityMaturity, icon: Leaf, color: 'teal', name: 'Sustainability' },
                      ].map(dim => {
                        const Icon = dim.icon
                        const colors = getColorClasses(dim.color)
                        return (
                          <div key={dim.id} className={`p-4 ${colors.bg} border ${colors.border} rounded-xl`}>
                            <div className="flex items-center gap-3">
                              <Icon className={`w-6 h-6 ${colors.text}`} />
                              <div>
                                <p className="text-sm text-slate-400">{dim.name}</p>
                                <p className={`text-2xl font-bold ${colors.text}`}>{dim.score}/5</p>
                              </div>
                            </div>
                            <div className="mt-3 bg-slate-800 rounded-full h-2">
                              <div className={`h-2 rounded-full ${getLevelColor(dim.color)}`} style={{ width: `${(dim.score / 5) * 100}%` }} />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Strengths & Improvements */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                      <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <CheckCircle2 className="w-5 h-5 text-green-500" />
                        Strengths ({selectedMBGL.strengths.length})
                      </h3>
                      <div className="space-y-2">
                        {selectedMBGL.strengths.map((strength, idx) => (
                          <div key={idx} className="flex items-start gap-2 p-3 bg-green-500/10 border border-green-500/30 rounded-lg">
                            <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0 mt-0.5" />
                            <span className="text-sm">{strength}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                      <h3 className="font-semibold mb-4 flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-orange-500" />
                        Areas for Improvement ({selectedMBGL.improvementsNeeded.length})
                      </h3>
                      <div className="space-y-2">
                        {selectedMBGL.improvementsNeeded.map((improvement, idx) => (
                          <div key={idx} className="flex items-start gap-2 p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                            <AlertCircle className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                            <span className="text-sm">{improvement}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Action Plan */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6">
                    <h3 className="font-semibold mb-4 flex items-center gap-2">
                      <Target className="w-5 h-5 text-blue-500" />
                      Action Plan
                    </h3>
                    <p className="text-slate-300 bg-slate-800 rounded-lg p-4">{selectedMBGL.actionPlan}</p>
                  </div>

                  {/* Level Criteria Met */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h3 className="font-semibold mb-4">Level Criteria Status</h3>
                    <div className="grid grid-cols-5 gap-3">
                      {[
                        { level: 1, met: selectedMBGL.level1CriteriaMet, color: 'red' },
                        { level: 2, met: selectedMBGL.level2CriteriaMet, color: 'orange' },
                        { level: 3, met: selectedMBGL.level3CriteriaMet, color: 'yellow' },
                        { level: 4, met: selectedMBGL.level4CriteriaMet, color: 'blue' },
                        { level: 5, met: selectedMBGL.level5CriteriaMet, color: 'green' },
                      ].map(({ level, met, color }) => (
                        <div key={level} className={`p-4 rounded-xl text-center ${met ? `${getColorClasses(color).bg} border ${getColorClasses(color).border}` : 'bg-slate-800 border border-slate-700'}`}>
                          <div className={`text-2xl font-bold ${met ? getColorClasses(color).text : 'text-slate-500'}`}>L{level}</div>
                          <div className="mt-2">
                            {met ? (
                              <CheckCircle2 className={`w-6 h-6 mx-auto ${getColorClasses(color).text}`} />
                            ) : (
                              <AlertCircle className="w-6 h-6 mx-auto text-slate-500" />
                            )}
                          </div>
                          <p className="text-xs mt-1 text-slate-400">{met ? 'Met' : 'Not Met'}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )
            })()}
          </>
        )}

        {/* Comparison Tab */}
        {activeTab === 'comparison' && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-6">Institution Comparison - MBGL Dimensions</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4">Institution</th>
                    <th className="text-center py-3 px-4">Level</th>
                    <th className="text-center py-3 px-4">Avg</th>
                    <th className="text-center py-3 px-4"><Target className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><BarChart3 className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><Users className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><Cpu className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><Award className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><Lightbulb className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><Heart className="w-4 h-4 inline" /></th>
                    <th className="text-center py-3 px-4"><Leaf className="w-4 h-4 inline" /></th>
                  </tr>
                </thead>
                <tbody>
                  {SAMPLE_MBGL_ASSESSMENTS.map(mbgl => {
                    const app = SAMPLE_APPLICATIONS.find(a => a.id === mbgl.applicationId)
                    const inst = app ? getInstitutionById(app.institutionId) : null
                    const levelInfo = MBGL_LEVELS.find(l => l.value === app?.mbglLevel)

                    if (!inst || !app) return null

                    return (
                      <tr key={mbgl.id} className="border-b border-slate-800 hover:bg-slate-800/50">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium">{inst.name}</p>
                            <p className="text-xs text-slate-400">{inst.location}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span className={`px-3 py-1 ${getLevelColor(levelInfo?.color || 'slate')} text-white rounded-full font-bold`}>
                            {levelInfo?.number}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-center font-bold">{mbgl.averageMaturity.toFixed(2)}</td>
                        <td className="py-3 px-4 text-center">{mbgl.leadershipMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.processMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.peopleMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.technologyMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.outcomeMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.innovationMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.stakeholderMaturity}</td>
                        <td className="py-3 px-4 text-center">{mbgl.sustainabilityMaturity}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {/* Dimension Legend */}
            <div className="mt-6 grid grid-cols-4 md:grid-cols-8 gap-2 text-xs">
              {MATURITY_DIMENSIONS.map(dim => {
                const Icon = dim.icon
                const colors = getColorClasses(dim.color)
                return (
                  <div key={dim.id} className={`p-2 ${colors.bg} rounded-lg text-center`}>
                    <Icon className={`w-4 h-4 mx-auto ${colors.text}`} />
                    <p className="mt-1 text-slate-400">{dim.name.split(' ')[0]}</p>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Assessment Tab (Original Form) */}
        {activeTab === 'assessment' && (
          <>
            {/* Eligibility Check */}
            {!isEligible && (
              <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-yellow-500 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold text-yellow-400">MBGL Not Available</h3>
                  <p className="text-sm text-yellow-300 mt-1">
                    MBGL assessment is only available for institutions with Binary Accreditation status of "Accredited".
                    Please complete Binary Accreditation first.
                  </p>
                  <Link
                    href="/admin/accreditation/settings"
                    className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black rounded-lg text-sm"
                  >
                    <Shield className="w-4 h-4" />
                    Update Accreditation Status
                  </Link>
                </div>
              </div>
            )}

            {/* Current Level Summary */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              {/* Level Card */}
              <div className={`${getColorClasses(calculatedLevel.color).bg} border ${getColorClasses(calculatedLevel.color).border} rounded-xl p-6`}>
                <div className="flex items-center gap-4">
                  <div className={`w-20 h-20 ${getLevelColor(calculatedLevel.color)} rounded-2xl flex items-center justify-center`}>
                    <span className="text-4xl font-bold text-white">{calculatedLevel.number}</span>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Current MBGL Level</p>
                    <h2 className="text-xl font-bold">{calculatedLevel.label}</h2>
                    <p className={`text-sm ${getColorClasses(calculatedLevel.color).text} mt-1`}>
                      Average Maturity: {averageMaturity.toFixed(2)} / 5.00
                    </p>
                  </div>
                </div>
              </div>

              {/* Score Card */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <p className="text-sm text-slate-400 mb-2">Weighted Score</p>
                <div className="flex items-end gap-2">
                  <span className="text-4xl font-bold">{((averageMaturity / 5) * 100).toFixed(1)}</span>
                  <span className="text-xl text-slate-400 mb-1">/ 100</span>
                </div>
                <div className="mt-4 bg-slate-800 rounded-full h-3">
                  <div
                    className={`h-3 rounded-full ${getLevelColor(calculatedLevel.color)}`}
                    style={{ width: `${(averageMaturity / 5) * 100}%` }}
                  />
                </div>
              </div>

              {/* Assessment Info */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-slate-400">Assessment Year</p>
                    <select
                      value={assessment.assessment_year}
                      onChange={e => setAssessment({ ...assessment, assessment_year: e.target.value })}
                      className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                      disabled={!isEligible}
                    >
                      <option value="2024-25">2024-25</option>
                      <option value="2025-26">2025-26</option>
                      <option value="2026-27">2026-27</option>
                    </select>
                  </div>
                  <div>
                    <p className="text-sm text-slate-400">Assessment Date</p>
                    <input
                      type="date"
                      value={assessment.assessment_date}
                      onChange={e => setAssessment({ ...assessment, assessment_date: e.target.value })}
                      className="mt-1 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                      disabled={!isEligible}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* MBGL Levels Visual */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
              <h3 className="font-semibold mb-4">MBGL Level Progression</h3>
              <div className="grid grid-cols-5 gap-2">
                {MBGL_LEVELS.filter(l => l.number > 0).map(level => {
                  const isActive = calculatedLevel.value === level.value
                  const isAchieved = calculatedLevel.number >= level.number
                  return (
                    <div
                      key={level.value}
                      className={`p-4 rounded-xl text-center transition-all ${
                        isActive
                          ? `${getLevelColor(level.color)} text-white`
                          : isAchieved
                            ? `${getColorClasses(level.color).bg} ${getColorClasses(level.color).border} border`
                            : 'bg-slate-800 border border-slate-700 text-slate-500'
                      }`}
                    >
                      <div className="text-3xl font-bold">{level.number}</div>
                      <div className="text-sm mt-1 font-medium">{level.label.split(' - ')[1]}</div>
                      <div className="text-xs mt-2 opacity-70">Min: {level.minScore.toFixed(1)}</div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Maturity Dimensions */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
              <h3 className="font-semibold mb-6">8 Maturity Dimensions (Score 1-5 each)</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {MATURITY_DIMENSIONS.map(dimension => {
                  const Icon = dimension.icon
                  const colors = getColorClasses(dimension.color)
                  const score = assessment.dimensions[dimension.id as keyof MBGLAssessment['dimensions']]
                  return (
                    <div key={dimension.id} className={`p-5 ${colors.bg} border ${colors.border} rounded-xl`}>
                      <div className="flex items-start gap-4">
                        <div className={`p-3 ${colors.bg} rounded-lg`}>
                          <Icon className={`w-6 h-6 ${colors.text}`} />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-semibold">{dimension.name}</h4>
                          <p className="text-sm text-slate-400 mt-1">{dimension.description}</p>

                          {/* Score Selector */}
                          <div className="mt-4">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-slate-400 w-16">Score:</span>
                              <div className="flex gap-1">
                                {[1, 2, 3, 4, 5].map(s => (
                                  <button
                                    key={s}
                                    onClick={() => updateDimension(dimension.id as keyof MBGLAssessment['dimensions'], s)}
                                    disabled={!isEligible}
                                    className={`w-10 h-10 rounded-lg font-bold transition-all ${
                                      score === s
                                        ? `${getLevelColor(dimension.color)} text-white`
                                        : 'bg-slate-700 hover:bg-slate-600 disabled:hover:bg-slate-700'
                                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                                  >
                                    {s}
                                  </button>
                                ))}
                              </div>
                              <span className={`ml-2 text-lg font-bold ${colors.text}`}>{score}/5</span>
                            </div>
                          </div>

                          {/* Indicators */}
                          <div className="mt-3 flex flex-wrap gap-2">
                            {dimension.indicators.map((indicator, idx) => (
                              <span
                                key={idx}
                                className={`px-2 py-1 ${colors.bg} ${colors.text} text-xs rounded-full`}
                              >
                                {indicator}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Strengths & Improvements */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
              {/* Strengths */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                  Strengths Identified
                </h3>
                <div className="space-y-2 mb-4">
                  {assessment.strengths.map((strength, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-green-500/10 border border-green-500/30 rounded-lg">
                      <CheckCircle2 className="w-4 h-4 text-green-400 flex-shrink-0" />
                      <span className="flex-1 text-sm">{strength}</span>
                      <button
                        onClick={() => removeStrength(idx)}
                        className="text-red-400 hover:text-red-300 text-sm"
                        disabled={!isEligible}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  {assessment.strengths.length === 0 && (
                    <p className="text-sm text-slate-500">No strengths added yet</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newStrength}
                    onChange={e => setNewStrength(e.target.value)}
                    placeholder="Add a strength..."
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                    disabled={!isEligible}
                    onKeyPress={e => e.key === 'Enter' && addStrength()}
                  />
                  <button
                    onClick={addStrength}
                    disabled={!isEligible || !newStrength.trim()}
                    className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-700 rounded-lg text-sm"
                  >
                    Add
                  </button>
                </div>
              </div>

              {/* Improvements */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-orange-500" />
                  Areas for Improvement
                </h3>
                <div className="space-y-2 mb-4">
                  {assessment.improvements.map((improvement, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                      <AlertCircle className="w-4 h-4 text-orange-400 flex-shrink-0" />
                      <span className="flex-1 text-sm">{improvement}</span>
                      <button
                        onClick={() => removeImprovement(idx)}
                        className="text-red-400 hover:text-red-300 text-sm"
                        disabled={!isEligible}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                  {assessment.improvements.length === 0 && (
                    <p className="text-sm text-slate-500">No improvements added yet</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={newImprovement}
                    onChange={e => setNewImprovement(e.target.value)}
                    placeholder="Add an improvement area..."
                    className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm"
                    disabled={!isEligible}
                    onKeyPress={e => e.key === 'Enter' && addImprovement()}
                  />
                  <button
                    onClick={addImprovement}
                    disabled={!isEligible || !newImprovement.trim()}
                    className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-700 rounded-lg text-sm"
                  >
                    Add
                  </button>
                </div>
              </div>
            </div>

            {/* Action Plan */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-500" />
                Action Plan for Level Improvement
              </h3>
              <textarea
                value={assessment.action_plan}
                onChange={e => setAssessment({ ...assessment, action_plan: e.target.value })}
                placeholder="Describe the action plan to improve MBGL level..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm h-32"
                disabled={!isEligible}
              />
            </div>
          </>
        )}

        {/* Level Criteria Info - Always visible */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mt-8">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Info className="w-5 h-5 text-blue-500" />
            MBGL Level Criteria (NAAC 2025)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4">Level</th>
                  <th className="text-left py-3 px-4">Name</th>
                  <th className="text-left py-3 px-4">Min Score</th>
                  <th className="text-left py-3 px-4">Validity</th>
                  <th className="text-left py-3 px-4">Key Benefits</th>
                </tr>
              </thead>
              <tbody>
                {MBGL_LEVEL_CRITERIA.map(criteria => {
                  const levelInfo = MBGL_LEVELS.find(l => l.value === criteria.level)
                  return (
                    <tr key={criteria.id} className="border-b border-slate-800">
                      <td className="py-3 px-4">
                        <span className={`px-3 py-1 ${getLevelColor(levelInfo?.color || 'slate')} text-white rounded-full font-bold`}>
                          {criteria.levelNumber}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <p className="font-medium">{criteria.levelName}</p>
                        <p className="text-xs text-slate-400 mt-1">{criteria.levelDescription}</p>
                      </td>
                      <td className="py-3 px-4">{criteria.minMaturityScore.toFixed(1)}</td>
                      <td className="py-3 px-4">{criteria.validityYears} years</td>
                      <td className="py-3 px-4">
                        <ul className="text-xs text-slate-400 space-y-1">
                          {criteria.recognitionBenefits.slice(0, 2).map((benefit, idx) => (
                            <li key={idx}>• {benefit}</li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
