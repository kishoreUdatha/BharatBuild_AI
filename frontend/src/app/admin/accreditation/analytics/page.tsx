'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  BarChart3,
  TrendingUp,
  Building,
  Users,
  Calendar,
  CheckCircle2,
  AlertCircle,
  Clock,
  FileText,
  Award,
  Target,
  ChevronRight,
  Eye,
  Download,
  Filter,
  Search,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  BookOpen,
  GraduationCap,
  FlaskConical,
  Settings,
  Heart,
  Cpu,
  Leaf
} from 'lucide-react'
import AccreditationNav from '@/components/AccreditationNav'
import {
  SAMPLE_INSTITUTIONS,
  SAMPLE_APPLICATIONS,
  SAMPLE_MBGL_ASSESSMENTS,
  SAMPLE_TIMELINES,
  SAMPLE_ATTRIBUTE_SCORES_APP1,
  SAMPLE_ATTRIBUTE_SCORES_APP2,
  SAMPLE_ATTRIBUTE_SCORES_APP3,
  ATTRIBUTES_DEFINITION,
  DASHBOARD_STATS,
  MBGL_LEVEL_CRITERIA,
  getInstitutionById,
  getAttributeScoresForApplication,
  getTimelineForApplication,
  getBinaryStatusLabel,
  getMBGLLevelLabel,
  getPhaseLabel,
  type AccreditationApplication,
  type BinaryStatus,
  type MBGLLevel,
  type AssessmentPhase
} from '@/data/sampleAccreditationData'

const MBGL_LEVELS = [
  { value: 'not_assessed', label: 'Not Assessed', number: 0, color: 'slate' },
  { value: 'level_1', label: 'Level 1', number: 1, color: 'red' },
  { value: 'level_2', label: 'Level 2', number: 2, color: 'orange' },
  { value: 'level_3', label: 'Level 3', number: 3, color: 'yellow' },
  { value: 'level_4', label: 'Level 4', number: 4, color: 'blue' },
  { value: 'level_5', label: 'Level 5', number: 5, color: 'green' }
]

export default function AccreditationAnalyticsPage() {
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterLevel, setFilterLevel] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedApplication, setSelectedApplication] = useState<string | null>(null)

  const getColorClasses = (color: string) => {
    const colors: Record<string, { bg: string; border: string; text: string; solid: string }> = {
      blue: { bg: 'bg-blue-500/20', border: 'border-blue-500/30', text: 'text-blue-400', solid: 'bg-blue-500' },
      green: { bg: 'bg-green-500/20', border: 'border-green-500/30', text: 'text-green-400', solid: 'bg-green-500' },
      purple: { bg: 'bg-purple-500/20', border: 'border-purple-500/30', text: 'text-purple-400', solid: 'bg-purple-500' },
      cyan: { bg: 'bg-cyan-500/20', border: 'border-cyan-500/30', text: 'text-cyan-400', solid: 'bg-cyan-500' },
      orange: { bg: 'bg-orange-500/20', border: 'border-orange-500/30', text: 'text-orange-400', solid: 'bg-orange-500' },
      yellow: { bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', text: 'text-yellow-400', solid: 'bg-yellow-500' },
      pink: { bg: 'bg-pink-500/20', border: 'border-pink-500/30', text: 'text-pink-400', solid: 'bg-pink-500' },
      teal: { bg: 'bg-teal-500/20', border: 'border-teal-500/30', text: 'text-teal-400', solid: 'bg-teal-500' },
      red: { bg: 'bg-red-500/20', border: 'border-red-500/30', text: 'text-red-400', solid: 'bg-red-500' },
      slate: { bg: 'bg-slate-500/20', border: 'border-slate-500/30', text: 'text-slate-400', solid: 'bg-slate-500' }
    }
    return colors[color] || colors.blue
  }

  const getStatusColor = (status: BinaryStatus): string => {
    const colors: Record<BinaryStatus, string> = {
      not_applied: 'slate',
      applied: 'blue',
      under_review: 'yellow',
      accredited: 'green',
      not_accredited: 'red',
      expired: 'orange'
    }
    return colors[status]
  }

  const getLevelColor = (level: MBGLLevel): string => {
    const levelInfo = MBGL_LEVELS.find(l => l.value === level)
    return levelInfo?.color || 'slate'
  }

  // Filter applications
  const filteredApplications = SAMPLE_APPLICATIONS.filter(app => {
    const institution = getInstitutionById(app.institutionId)
    const matchesStatus = filterStatus === 'all' || app.binaryStatus === filterStatus
    const matchesLevel = filterLevel === 'all' || app.mbglLevel === filterLevel
    const matchesSearch = !searchQuery ||
      institution?.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      app.applicationNumber.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesStatus && matchesLevel && matchesSearch
  })

  // Get selected application details
  const selectedApp = selectedApplication ? SAMPLE_APPLICATIONS.find(a => a.id === selectedApplication) : null
  const selectedInst = selectedApp ? getInstitutionById(selectedApp.institutionId) : null
  const selectedScores = selectedApp ? getAttributeScoresForApplication(selectedApp.id) : []
  const selectedTimeline = selectedApp ? getTimelineForApplication(selectedApp.id) : []
  const selectedMBGL = selectedApp ? SAMPLE_MBGL_ASSESSMENTS.find(m => m.applicationId === selectedApp.id) : null

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
                <span className="text-white">Analytics</span>
              </div>
              <h1 className="text-2xl font-bold flex items-center gap-3">
                <BarChart3 className="w-8 h-8 text-orange-500" />
                Accreditation Analytics
              </h1>
              <p className="text-slate-400 mt-1">NAAC 2025 Framework - Sample Data & Scenarios</p>
            </div>
            <div className="flex items-center gap-3">
              <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-sm">
                <Download className="w-4 h-4" />
                Export Report
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Key Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <p className="text-xs text-slate-400">Total Applications</p>
            <p className="text-2xl font-bold text-white">{DASHBOARD_STATS.totalApplications}</p>
          </div>
          <div className={`${getColorClasses('green').bg} border ${getColorClasses('green').border} rounded-xl p-4`}>
            <p className="text-xs text-green-400">Accredited</p>
            <p className={`text-2xl font-bold ${getColorClasses('green').text}`}>{DASHBOARD_STATS.accredited}</p>
          </div>
          <div className={`${getColorClasses('yellow').bg} border ${getColorClasses('yellow').border} rounded-xl p-4`}>
            <p className="text-xs text-yellow-400">Under Review</p>
            <p className={`text-2xl font-bold ${getColorClasses('yellow').text}`}>{DASHBOARD_STATS.underReview}</p>
          </div>
          <div className={`${getColorClasses('blue').bg} border ${getColorClasses('blue').border} rounded-xl p-4`}>
            <p className="text-xs text-blue-400">Applied</p>
            <p className={`text-2xl font-bold ${getColorClasses('blue').text}`}>{DASHBOARD_STATS.applied}</p>
          </div>
          <div className={`${getColorClasses('purple').bg} border ${getColorClasses('purple').border} rounded-xl p-4`}>
            <p className="text-xs text-purple-400">Avg Maturity</p>
            <p className={`text-2xl font-bold ${getColorClasses('purple').text}`}>{DASHBOARD_STATS.averageMaturityScore.toFixed(2)}</p>
          </div>
          <div className={`${getColorClasses('cyan').bg} border ${getColorClasses('cyan').border} rounded-xl p-4`}>
            <p className="text-xs text-cyan-400">Completion %</p>
            <p className={`text-2xl font-bold ${getColorClasses('cyan').text}`}>{DASHBOARD_STATS.completionRate}%</p>
          </div>
          <div className={`${getColorClasses('orange').bg} border ${getColorClasses('orange').border} rounded-xl p-4`}>
            <p className="text-xs text-orange-400">Avg Days</p>
            <p className={`text-2xl font-bold ${getColorClasses('orange').text}`}>{DASHBOARD_STATS.avgProcessingDays}</p>
          </div>
          <div className={`${getColorClasses('teal').bg} border ${getColorClasses('teal').border} rounded-xl p-4`}>
            <p className="text-xs text-teal-400">MBGL Assessed</p>
            <p className={`text-2xl font-bold ${getColorClasses('teal').text}`}>{SAMPLE_MBGL_ASSESSMENTS.length}</p>
          </div>
        </div>

        {/* MBGL Level Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-green-500" />
              MBGL Level Distribution
            </h3>
            <div className="grid grid-cols-6 gap-2">
              {MBGL_LEVELS.map(level => {
                const count = DASHBOARD_STATS.mbglDistribution[level.value as keyof typeof DASHBOARD_STATS.mbglDistribution] || 0
                const colors = getColorClasses(level.color)
                return (
                  <div key={level.value} className={`p-3 ${colors.bg} border ${colors.border} rounded-xl text-center`}>
                    <div className={`text-2xl font-bold ${colors.text}`}>{count}</div>
                    <div className="text-xs mt-1 text-slate-400">{level.number === 0 ? 'N/A' : `L${level.number}`}</div>
                  </div>
                )
              })}
            </div>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-500" />
              Cycle Distribution
            </h3>
            <div className="grid grid-cols-4 gap-2">
              {Object.entries(DASHBOARD_STATS.cycleDistribution).map(([cycle, count]) => (
                <div key={cycle} className="p-3 bg-slate-800 rounded-xl text-center">
                  <div className="text-2xl font-bold text-white">{count}</div>
                  <div className="text-xs mt-1 text-slate-400 capitalize">{cycle} Cycle</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Attribute Performance */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-orange-500" />
            10 Attributes Performance (Avg Scores)
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {ATTRIBUTES_DEFINITION.map(attr => {
              const score = DASHBOARD_STATS.attributePerformance[attr.attribute as keyof typeof DASHBOARD_STATS.attributePerformance] || 0
              const percentage = score
              let color = 'green'
              if (percentage < 70) color = 'red'
              else if (percentage < 80) color = 'orange'
              else if (percentage < 90) color = 'yellow'

              return (
                <div key={attr.attribute} className="bg-slate-800 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium truncate">{attr.name.split(' ')[0]}</span>
                    <span className={`text-sm font-bold ${getColorClasses(color).text}`}>{score.toFixed(1)}</span>
                  </div>
                  <div className="bg-slate-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${getColorClasses(color).solid}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-500 mt-2">Weight: {attr.weightage}%</p>
                </div>
              )
            })}
          </div>
        </div>

        {/* Applications List */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5 text-purple-500" />
              All Applications ({filteredApplications.length})
            </h3>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm w-48"
                />
              </div>
              <select
                value={filterStatus}
                onChange={e => setFilterStatus(e.target.value)}
                className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm"
              >
                <option value="all">All Status</option>
                <option value="accredited">Accredited</option>
                <option value="under_review">Under Review</option>
                <option value="applied">Applied</option>
                <option value="not_applied">Not Applied</option>
              </select>
              <select
                value={filterLevel}
                onChange={e => setFilterLevel(e.target.value)}
                className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm"
              >
                <option value="all">All Levels</option>
                {MBGL_LEVELS.map(level => (
                  <option key={level.value} value={level.value}>{level.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-700">
                  <th className="text-left py-3 px-4">Institution</th>
                  <th className="text-left py-3 px-4">Application #</th>
                  <th className="text-center py-3 px-4">Cycle</th>
                  <th className="text-center py-3 px-4">Binary Status</th>
                  <th className="text-center py-3 px-4">MBGL</th>
                  <th className="text-center py-3 px-4">Phase</th>
                  <th className="text-center py-3 px-4">Score</th>
                  <th className="text-center py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredApplications.map(app => {
                  const institution = getInstitutionById(app.institutionId)
                  const statusColor = getStatusColor(app.binaryStatus)
                  const levelColor = getLevelColor(app.mbglLevel)
                  const levelInfo = MBGL_LEVELS.find(l => l.value === app.mbglLevel)

                  return (
                    <tr
                      key={app.id}
                      className={`border-b border-slate-800 hover:bg-slate-800/50 cursor-pointer ${
                        selectedApplication === app.id ? 'bg-slate-800/80' : ''
                      }`}
                      onClick={() => setSelectedApplication(selectedApplication === app.id ? null : app.id)}
                    >
                      <td className="py-3 px-4">
                        <div>
                          <p className="font-medium">{institution?.name}</p>
                          <p className="text-xs text-slate-400">{institution?.location}</p>
                        </div>
                      </td>
                      <td className="py-3 px-4 font-mono text-xs">{app.applicationNumber}</td>
                      <td className="py-3 px-4 text-center">
                        <span className="px-2 py-1 bg-slate-700 rounded text-xs capitalize">{app.cycle}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-2 py-1 ${getColorClasses(statusColor).bg} ${getColorClasses(statusColor).text} rounded text-xs`}>
                          {getBinaryStatusLabel(app.binaryStatus)}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`px-3 py-1 ${getColorClasses(levelColor).solid} text-white rounded-full font-bold text-xs`}>
                          {levelInfo?.number === 0 ? 'N/A' : `L${levelInfo?.number}`}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="text-xs text-slate-400">{getPhaseLabel(app.currentPhase)}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-bold">{app.finalScore?.toFixed(1) || '-'}</span>
                      </td>
                      <td className="py-3 px-4 text-center">
                        <button className="p-2 hover:bg-slate-700 rounded-lg">
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Application Details */}
        {selectedApp && selectedInst && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold flex items-center gap-2">
                <Building className="w-5 h-5 text-blue-500" />
                {selectedInst.name} - Detailed View
              </h3>
              <button
                onClick={() => setSelectedApplication(null)}
                className="text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Institution Info */}
              <div className="bg-slate-800 rounded-xl p-4">
                <h4 className="font-medium mb-3 text-sm text-slate-400">Institution Details</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Type:</span>
                    <span className="capitalize">{selectedInst.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Established:</span>
                    <span>{selectedInst.established}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Students:</span>
                    <span>{selectedInst.students.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Faculty:</span>
                    <span>{selectedInst.faculty}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Location:</span>
                    <span>{selectedInst.location}</span>
                  </div>
                </div>
              </div>

              {/* Application Status */}
              <div className="bg-slate-800 rounded-xl p-4">
                <h4 className="font-medium mb-3 text-sm text-slate-400">Application Status</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Application #:</span>
                    <span className="font-mono text-xs">{selectedApp.applicationNumber}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Cycle:</span>
                    <span className="capitalize">{selectedApp.cycle} (#{selectedApp.cycleNumber})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Binary Status:</span>
                    <span className={`px-2 py-0.5 rounded text-xs ${getColorClasses(getStatusColor(selectedApp.binaryStatus)).bg} ${getColorClasses(getStatusColor(selectedApp.binaryStatus)).text}`}>
                      {getBinaryStatusLabel(selectedApp.binaryStatus)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">MBGL Level:</span>
                    <span>{getMBGLLevelLabel(selectedApp.mbglLevel)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Current Phase:</span>
                    <span>{getPhaseLabel(selectedApp.currentPhase)}</span>
                  </div>
                </div>
              </div>

              {/* Scores */}
              <div className="bg-slate-800 rounded-xl p-4">
                <h4 className="font-medium mb-3 text-sm text-slate-400">Assessment Scores</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Self-Study:</span>
                    <span className="font-bold">{selectedApp.selfStudyScore?.toFixed(1) || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">AI Assessment:</span>
                    <span className="font-bold">{selectedApp.aiAssessmentScore?.toFixed(1) || '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Stakeholder:</span>
                    <span className="font-bold">{selectedApp.stakeholderScore?.toFixed(1) || '-'}</span>
                  </div>
                  <div className="flex justify-between border-t border-slate-700 pt-2 mt-2">
                    <span className="text-slate-400">Final Score:</span>
                    <span className="font-bold text-lg text-green-400">{selectedApp.finalScore?.toFixed(1) || '-'}</span>
                  </div>
                  {selectedApp.mbglScore && (
                    <div className="flex justify-between">
                      <span className="text-slate-400">MBGL Score:</span>
                      <span className="font-bold">{selectedApp.mbglScore.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Attribute Scores */}
            {selectedScores.length > 0 && (
              <div className="mt-6">
                <h4 className="font-medium mb-4 text-sm text-slate-400">10 Attributes Scores</h4>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  {selectedScores.map(score => {
                    const finalScore = score.finalScore || score.verifiedScore || score.selfScore
                    let color = 'green'
                    if (finalScore < 70) color = 'red'
                    else if (finalScore < 80) color = 'orange'
                    else if (finalScore < 90) color = 'yellow'

                    return (
                      <div key={score.attribute} className={`${getColorClasses(color).bg} border ${getColorClasses(color).border} rounded-lg p-3`}>
                        <p className="text-xs text-slate-400 truncate">{score.attributeName}</p>
                        <p className={`text-xl font-bold ${getColorClasses(color).text}`}>{finalScore}</p>
                        <div className="flex items-center justify-between mt-1 text-xs text-slate-500">
                          <span>AI: {score.aiScore || '-'}</span>
                          <span>{score.isComplete ? <CheckCircle2 className="w-3 h-3 text-green-400" /> : <Clock className="w-3 h-3 text-yellow-400" />}</span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Timeline */}
            {selectedTimeline.length > 0 && (
              <div className="mt-6">
                <h4 className="font-medium mb-4 text-sm text-slate-400">Assessment Timeline</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedTimeline.map((milestone, idx) => (
                    <div
                      key={idx}
                      className={`px-3 py-2 rounded-lg text-xs ${
                        milestone.isCompleted
                          ? 'bg-green-500/20 border border-green-500/30 text-green-400'
                          : 'bg-slate-800 border border-slate-700 text-slate-400'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        {milestone.isCompleted ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <Clock className="w-3 h-3" />
                        )}
                        <span>{milestone.milestoneName}</span>
                      </div>
                      <p className="mt-1 text-xs opacity-70">
                        {milestone.actualDate || milestone.plannedDate}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* MBGL Assessment */}
            {selectedMBGL && (
              <div className="mt-6">
                <h4 className="font-medium mb-4 text-sm text-slate-400">MBGL Assessment Details</h4>
                <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
                  {[
                    { name: 'Leadership', score: selectedMBGL.leadershipMaturity, icon: Target, color: 'blue' },
                    { name: 'Process', score: selectedMBGL.processMaturity, icon: BarChart3, color: 'green' },
                    { name: 'People', score: selectedMBGL.peopleMaturity, icon: Users, color: 'purple' },
                    { name: 'Technology', score: selectedMBGL.technologyMaturity, icon: Cpu, color: 'cyan' },
                    { name: 'Outcome', score: selectedMBGL.outcomeMaturity, icon: Award, color: 'orange' },
                    { name: 'Innovation', score: selectedMBGL.innovationMaturity, icon: FlaskConical, color: 'yellow' },
                    { name: 'Stakeholder', score: selectedMBGL.stakeholderMaturity, icon: Heart, color: 'pink' },
                    { name: 'Sustainability', score: selectedMBGL.sustainabilityMaturity, icon: Leaf, color: 'teal' },
                  ].map(dim => {
                    const Icon = dim.icon
                    const colors = getColorClasses(dim.color)
                    return (
                      <div key={dim.name} className={`${colors.bg} border ${colors.border} rounded-lg p-3 text-center`}>
                        <Icon className={`w-5 h-5 mx-auto ${colors.text}`} />
                        <p className={`text-xl font-bold ${colors.text} mt-1`}>{dim.score}</p>
                        <p className="text-xs text-slate-400">{dim.name}</p>
                      </div>
                    )
                  })}
                </div>
                <div className="mt-4 flex items-center gap-4">
                  <div className="bg-slate-800 rounded-lg px-4 py-2">
                    <span className="text-sm text-slate-400">Average: </span>
                    <span className="font-bold text-green-400">{selectedMBGL.averageMaturity.toFixed(2)}</span>
                  </div>
                  <div className="bg-slate-800 rounded-lg px-4 py-2">
                    <span className="text-sm text-slate-400">Weighted: </span>
                    <span className="font-bold text-blue-400">{selectedMBGL.weightedScore.toFixed(1)}</span>
                  </div>
                  <div className="bg-slate-800 rounded-lg px-4 py-2">
                    <span className="text-sm text-slate-400">Final Level: </span>
                    <span className="font-bold text-purple-400">{selectedMBGL.finalLevel.replace('level_', 'Level ')}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Notes */}
            {selectedApp.notes && (
              <div className="mt-6 p-4 bg-slate-800 rounded-lg">
                <h4 className="font-medium mb-2 text-sm text-slate-400">Notes</h4>
                <p className="text-sm">{selectedApp.notes}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
