'use client'

import React, { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Award,
  ArrowLeft,
  Download,
  Loader2,
  CheckCircle,
  Shield,
  QrCode,
  User,
  Building,
  BookOpen,
  Code,
  Star,
  ExternalLink,
  Copy,
  Check,
  FileText
} from 'lucide-react'

interface Certificate {
  certificate_id: string
  certificate_type: string
  student: {
    name: string
    id: string
  }
  institution: {
    name: string
    department: string
  }
  project?: {
    title: string
    description: string
    duration_weeks: number
    technologies: string[]
  }
  skills: Array<{
    name: string
    category: string
    level: string
  }>
  obe_metrics: {
    course_outcomes: Array<{
      co_id: string
      attainment_percentage: number
    }>
    program_outcomes: Array<{
      po_id: string
      contribution: number
    }>
    overall_attainment: number
  }
  assessment: {
    grade: string
    score: number
  }
  verification: {
    code: string
    url: string
  }
  metadata: {
    issue_date: string
    faculty_name: string
  }
}

interface SkillBadge {
  badge_id: string
  student_name: string
  skill_name: string
  skill_category: string
  level: string
  assessment_score: number
  issue_date: string
  verification_code: string
}

const skillLevelColors: Record<string, string> = {
  beginner: 'from-green-600 to-emerald-600',
  intermediate: 'from-blue-600 to-cyan-600',
  advanced: 'from-orange-600 to-amber-600',
  expert: 'from-purple-600 to-pink-600'
}

export default function CertificatesPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [activeTab, setActiveTab] = useState<'generate' | 'verify' | 'badges'>('generate')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copiedCode, setCopiedCode] = useState(false)

  // Form state
  const [studentName, setStudentName] = useState('')
  const [studentId, setStudentId] = useState('')
  const [institutionName, setInstitutionName] = useState('')
  const [department, setDepartment] = useState('')
  const [certificateType, setCertificateType] = useState('project_completion')
  const [projectTitle, setProjectTitle] = useState('')
  const [projectDescription, setProjectDescription] = useState('')
  const [technologies, setTechnologies] = useState('')
  const [facultyName, setFacultyName] = useState('')

  // Skill badge state
  const [skillName, setSkillName] = useState('')
  const [skillLevel, setSkillLevel] = useState('intermediate')
  const [assessmentScore, setAssessmentScore] = useState(80)
  const [hoursPracticed, setHoursPracticed] = useState(0)

  // Verification state
  const [verificationCode, setVerificationCode] = useState('')
  const [verificationResult, setVerificationResult] = useState<any>(null)

  // Generated certificate/badge
  const [certificate, setCertificate] = useState<Certificate | null>(null)
  const [certificateHtml, setCertificateHtml] = useState<string | null>(null)
  const [badge, setBadge] = useState<SkillBadge | null>(null)

  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Pre-fill project ID if coming from evaluation
  useEffect(() => {
    const projectId = searchParams.get('projectId')
    if (projectId) {
      setProjectTitle(`Project ${projectId}`)
    }
  }, [searchParams])

  const handleGenerateCertificate = async () => {
    if (!studentName || !studentId || !institutionName || !department) {
      setError('Please fill in all required fields')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // First get JSON data
      const response = await fetch(`${API_BASE}/api/v1/accreditation/certification/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_name: studentName,
          student_id: studentId,
          institution_name: institutionName,
          department,
          certificate_type: certificateType,
          project_data: projectTitle ? {
            title: projectTitle,
            description: projectDescription,
            technologies: technologies.split(',').map(t => t.trim()).filter(Boolean)
          } : null,
          faculty_name: facultyName || null
        })
      })

      const data = await response.json()

      if (data.success) {
        setCertificate(data.certificate)

        // Also get HTML for preview
        const htmlResponse = await fetch(`${API_BASE}/api/v1/accreditation/certification/html`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            student_name: studentName,
            student_id: studentId,
            institution_name: institutionName,
            department,
            certificate_type: certificateType,
            project_data: projectTitle ? {
              title: projectTitle,
              description: projectDescription,
              technologies: technologies.split(',').map(t => t.trim()).filter(Boolean)
            } : null,
            faculty_name: facultyName || null
          })
        })

        const htmlData = await htmlResponse.json()
        if (htmlData.success) {
          setCertificateHtml(htmlData.html)
        }
      } else {
        setError(data.detail || 'Failed to generate certificate')
      }
    } catch (err) {
      setError('Network error. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleGenerateBadge = async () => {
    if (!studentName || !studentId || !skillName) {
      setError('Please fill in all required fields')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/v1/accreditation/certification/badge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          student_name: studentName,
          student_id: studentId,
          skill_name: skillName,
          skill_level: skillLevel,
          assessment_score: assessmentScore,
          hours_practiced: hoursPracticed,
          projects_completed: 1
        })
      })

      const data = await response.json()

      if (data.success) {
        setBadge(data.badge)
      } else {
        setError(data.detail || 'Failed to generate badge')
      }
    } catch (err) {
      setError('Network error. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    if (!verificationCode) {
      setError('Please enter a verification code')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/api/v1/accreditation/certification/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          verification_code: verificationCode
        })
      })

      const data = await response.json()
      setVerificationResult(data.verification_result)
    } catch (err) {
      setError('Network error. Please check if the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopiedCode(true)
    setTimeout(() => setCopiedCode(false), 2000)
  }

  const downloadCertificate = () => {
    if (!certificateHtml) return

    // Create a new window with the certificate
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(certificateHtml)
      printWindow.document.close()
      printWindow.print()
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900/50 to-pink-900/50 border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-slate-400 hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>

          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-r from-purple-600 to-pink-600 rounded-xl flex items-center justify-center">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">Skill Certification Generator</h1>
              <p className="text-slate-400">Generate certificates and badges with OBE metrics and verification</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setActiveTab('generate')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'generate'
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <FileText className="w-5 h-5" />
            Generate Certificate
          </button>
          <button
            onClick={() => setActiveTab('badges')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'badges'
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Star className="w-5 h-5" />
            Skill Badges
          </button>
          <button
            onClick={() => setActiveTab('verify')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
              activeTab === 'verify'
                ? 'bg-purple-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-white'
            }`}
          >
            <Shield className="w-5 h-5" />
            Verify
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-400">
            {error}
          </div>
        )}

        {/* Generate Certificate Tab */}
        {activeTab === 'generate' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Form */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <User className="w-5 h-5 text-purple-400" />
                Certificate Details
              </h2>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Student Name *</label>
                    <input
                      type="text"
                      value={studentName}
                      onChange={(e) => setStudentName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Student ID *</label>
                    <input
                      type="text"
                      value={studentId}
                      onChange={(e) => setStudentId(e.target.value)}
                      placeholder="STU123456"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Institution Name *</label>
                  <input
                    type="text"
                    value={institutionName}
                    onChange={(e) => setInstitutionName(e.target.value)}
                    placeholder="ABC Engineering College"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Department *</label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    placeholder="Computer Science and Engineering"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Certificate Type</label>
                  <select
                    value={certificateType}
                    onChange={(e) => setCertificateType(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="project_completion">Project Completion</option>
                    <option value="skill_proficiency">Skill Proficiency</option>
                    <option value="course_completion">Course Completion</option>
                    <option value="internship">Internship</option>
                    <option value="hackathon">Hackathon</option>
                    <option value="workshop">Workshop</option>
                  </select>
                </div>

                <div className="border-t border-slate-700 pt-4">
                  <h3 className="text-sm font-medium text-slate-300 mb-3">Project Details (Optional)</h3>

                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Project Title</label>
                      <input
                        type="text"
                        value={projectTitle}
                        onChange={(e) => setProjectTitle(e.target.value)}
                        placeholder="E-Commerce Web Application"
                        className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Project Description</label>
                      <textarea
                        value={projectDescription}
                        onChange={(e) => setProjectDescription(e.target.value)}
                        placeholder="A full-stack e-commerce application..."
                        rows={3}
                        className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500 resize-none"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Technologies (comma-separated)</label>
                      <input
                        type="text"
                        value={technologies}
                        onChange={(e) => setTechnologies(e.target.value)}
                        placeholder="React, Node.js, MongoDB"
                        className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Faculty Advisor</label>
                      <input
                        type="text"
                        value={facultyName}
                        onChange={(e) => setFacultyName(e.target.value)}
                        placeholder="Dr. Jane Smith"
                        className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>
                </div>

                <button
                  onClick={handleGenerateCertificate}
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:from-purple-500 hover:to-pink-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Award className="w-5 h-5" />
                      Generate Certificate
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Preview */}
            <div>
              {certificate ? (
                <div className="space-y-6">
                  {/* Certificate Preview */}
                  {certificateHtml && (
                    <div className="bg-white rounded-xl overflow-hidden">
                      <div
                        dangerouslySetInnerHTML={{ __html: certificateHtml }}
                        className="p-4"
                      />
                    </div>
                  )}

                  {/* Verification Info */}
                  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                      <Shield className="w-5 h-5 text-green-400" />
                      Verification Details
                    </h3>

                    <div className="space-y-4">
                      <div className="flex items-center justify-between bg-slate-800 p-4 rounded-lg">
                        <div>
                          <p className="text-sm text-slate-400">Certificate ID</p>
                          <p className="text-white font-mono">{certificate.certificate_id}</p>
                        </div>
                        <button
                          onClick={() => copyToClipboard(certificate.certificate_id)}
                          className="p-2 hover:bg-slate-700 rounded"
                        >
                          {copiedCode ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                        </button>
                      </div>

                      <div className="flex items-center justify-between bg-slate-800 p-4 rounded-lg">
                        <div>
                          <p className="text-sm text-slate-400">Verification Code</p>
                          <p className="text-white font-mono">{certificate.verification.code}</p>
                        </div>
                        <button
                          onClick={() => copyToClipboard(certificate.verification.code)}
                          className="p-2 hover:bg-slate-700 rounded"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      </div>

                      <div className="flex items-center justify-between bg-slate-800 p-4 rounded-lg">
                        <div>
                          <p className="text-sm text-slate-400">Verification URL</p>
                          <p className="text-blue-400 text-sm">{certificate.verification.url}</p>
                        </div>
                        <a
                          href={certificate.verification.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-2 hover:bg-slate-700 rounded"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </a>
                      </div>
                    </div>

                    <div className="flex gap-4 mt-6">
                      <button
                        onClick={downloadCertificate}
                        className="flex-1 py-3 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-lg font-medium hover:from-blue-500 hover:to-cyan-500 flex items-center justify-center gap-2"
                      >
                        <Download className="w-5 h-5" />
                        Download/Print
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                  <Award className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-slate-400 mb-2">Certificate Preview</h3>
                  <p className="text-slate-500">Fill in the details and generate to see the certificate preview</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Skill Badges Tab */}
        {activeTab === 'badges' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Form */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Star className="w-5 h-5 text-yellow-400" />
                Skill Badge Details
              </h2>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Student Name *</label>
                    <input
                      type="text"
                      value={studentName}
                      onChange={(e) => setStudentName(e.target.value)}
                      placeholder="John Doe"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Student ID *</label>
                    <input
                      type="text"
                      value={studentId}
                      onChange={(e) => setStudentId(e.target.value)}
                      placeholder="STU123456"
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Skill Name *</label>
                  <input
                    type="text"
                    value={skillName}
                    onChange={(e) => setSkillName(e.target.value)}
                    placeholder="React.js"
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                  />
                </div>

                <div>
                  <label className="block text-sm text-slate-400 mb-1">Skill Level</label>
                  <select
                    value={skillLevel}
                    onChange={(e) => setSkillLevel(e.target.value)}
                    className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                  >
                    <option value="beginner">Beginner</option>
                    <option value="intermediate">Intermediate</option>
                    <option value="advanced">Advanced</option>
                    <option value="expert">Expert</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Assessment Score</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={assessmentScore}
                      onChange={(e) => setAssessmentScore(parseInt(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Hours Practiced</label>
                    <input
                      type="number"
                      min="0"
                      value={hoursPracticed}
                      onChange={(e) => setHoursPracticed(parseInt(e.target.value))}
                      className="w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-yellow-500"
                    />
                  </div>
                </div>

                <button
                  onClick={handleGenerateBadge}
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-yellow-600 to-orange-600 text-white rounded-lg font-medium hover:from-yellow-500 hover:to-orange-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Star className="w-5 h-5" />
                      Generate Badge
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Badge Preview */}
            <div>
              {badge ? (
                <div className={`bg-gradient-to-r ${skillLevelColors[badge.level]} rounded-xl p-8`}>
                  <div className="text-center">
                    <div className="w-24 h-24 bg-white/20 rounded-full mx-auto mb-4 flex items-center justify-center">
                      <Star className="w-12 h-12 text-white" />
                    </div>
                    <h3 className="text-2xl font-bold text-white mb-2">{badge.skill_name}</h3>
                    <p className="text-white/80 text-lg mb-1">{badge.level.charAt(0).toUpperCase() + badge.level.slice(1)} Level</p>
                    <p className="text-white/60">{badge.skill_category}</p>

                    <div className="mt-6 bg-white/10 rounded-lg p-4">
                      <p className="text-white/80">Awarded to</p>
                      <p className="text-xl font-semibold text-white">{badge.student_name}</p>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mt-6">
                      <div className="bg-white/10 rounded-lg p-3">
                        <p className="text-white/60 text-sm">Score</p>
                        <p className="text-2xl font-bold text-white">{badge.assessment_score}%</p>
                      </div>
                      <div className="bg-white/10 rounded-lg p-3">
                        <p className="text-white/60 text-sm">Issued</p>
                        <p className="text-sm font-medium text-white">
                          {new Date(badge.issue_date).toLocaleDateString()}
                        </p>
                      </div>
                    </div>

                    <div className="mt-6 text-sm text-white/60">
                      <p>Verification: {badge.verification_code}</p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center">
                  <Star className="w-16 h-16 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-xl font-semibold text-slate-400 mb-2">Badge Preview</h3>
                  <p className="text-slate-500">Fill in the details and generate to see the badge preview</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Verify Tab */}
        {activeTab === 'verify' && (
          <div className="max-w-xl mx-auto">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-6 flex items-center gap-2">
                <Shield className="w-5 h-5 text-green-400" />
                Verify Certificate
              </h2>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Verification Code</label>
                  <input
                    type="text"
                    value={verificationCode}
                    onChange={(e) => setVerificationCode(e.target.value.toUpperCase())}
                    placeholder="Enter verification code"
                    className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-lg text-white text-center text-lg font-mono tracking-wider focus:outline-none focus:border-green-500"
                  />
                </div>

                <button
                  onClick={handleVerify}
                  disabled={loading}
                  className="w-full py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-medium hover:from-green-500 hover:to-emerald-500 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Verifying...
                    </>
                  ) : (
                    <>
                      <Shield className="w-5 h-5" />
                      Verify
                    </>
                  )}
                </button>
              </div>

              {verificationResult && (
                <div className="mt-6 p-6 rounded-lg border">
                  {verificationResult.verified ? (
                    <div className="bg-green-500/20 border-green-500/30 rounded-lg p-6">
                      <div className="flex items-center gap-3 mb-4">
                        <CheckCircle className="w-8 h-8 text-green-400" />
                        <div>
                          <h3 className="text-lg font-semibold text-green-400">Certificate Verified</h3>
                          <p className="text-green-400/80">This certificate is authentic</p>
                        </div>
                      </div>

                      <div className="space-y-3 text-sm">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Certificate ID</span>
                          <span className="text-white font-mono">{verificationResult.certificate_id}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Student Name</span>
                          <span className="text-white">{verificationResult.student_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Type</span>
                          <span className="text-white">{verificationResult.certificate_type}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Institution</span>
                          <span className="text-white">{verificationResult.institution_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Issue Date</span>
                          <span className="text-white">
                            {new Date(verificationResult.issue_date).toLocaleDateString()}
                          </span>
                        </div>
                        {verificationResult.grade && (
                          <div className="flex justify-between">
                            <span className="text-slate-400">Grade</span>
                            <span className="text-white font-bold">{verificationResult.grade}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-red-500/20 border-red-500/30 rounded-lg p-6">
                      <div className="flex items-center gap-3">
                        <XCircle className="w-8 h-8 text-red-400" />
                        <div>
                          <h3 className="text-lg font-semibold text-red-400">Certificate Not Found</h3>
                          <p className="text-red-400/80">{verificationResult.message}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
