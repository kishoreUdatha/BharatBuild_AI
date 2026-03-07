'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
  Award,
  FileText,
  GraduationCap,
  Building2,
  ClipboardCheck,
  BookOpen,
  Users,
  Shield,
  Leaf,
  ChevronRight,
  Loader2,
  Download,
  CheckCircle2,
  Info,
  Sparkles,
  FolderKanban,
  RefreshCw,
  ExternalLink,
  AlertCircle
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useAuth } from '@/hooks/useAuth'

interface CriterionInfo {
  number: number
  name: string
  marks: number
  key_indicators: string[]
}

interface InstitutionForm {
  name: string
  type: string
  location: string
  state: string
  established_year: number
  naac_cycle: number
  previous_grade: string
  programs_offered: string[]
  total_students: number
  total_faculty: number
}

interface CourseForm {
  course_name: string
  course_code: string
  department: string
  semester: number
  credits: number
  program_name: string
}

interface UserProfile {
  id: string
  email: string
  full_name: string
  role: string
  roll_number?: string
  college_name?: string
  university_name?: string
  department?: string
  course?: string
  year_semester?: string
  batch?: string
  guide_name?: string
  guide_designation?: string
  hod_name?: string
}

interface Project {
  id: string
  title: string
  description: string | null
  mode: string
  status: string
  tech_stack?: any
  framework?: string
  domain?: string
  created_at: string
}

const CRITERIA_ICONS = [
  BookOpen,      // Criterion 1: Curricular
  GraduationCap, // Criterion 2: Teaching-Learning
  FileText,      // Criterion 3: Research
  Building2,     // Criterion 4: Infrastructure
  Users,         // Criterion 5: Student Support
  Shield,        // Criterion 6: Governance
  Leaf           // Criterion 7: Values
]

export default function AccreditationPage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading } = useAuth()

  const [criteria, setCriteria] = useState<CriterionInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'ssr' | 'obe' | 'criterion'>('overview')
  const [selectedCriterion, setSelectedCriterion] = useState<number | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedDoc, setGeneratedDoc] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  // User profile and projects for auto-fill
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null)
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [isAutoFilled, setIsAutoFilled] = useState(false)

  // Form states
  const [institutionForm, setInstitutionForm] = useState<InstitutionForm>({
    name: '',
    type: 'Affiliated',
    location: '',
    state: '',
    established_year: 2000,
    naac_cycle: 1,
    previous_grade: '',
    programs_offered: [],
    total_students: 0,
    total_faculty: 0
  })

  const [courseForm, setCourseForm] = useState<CourseForm>({
    course_name: '',
    course_code: '',
    department: '',
    semester: 6,
    credits: 4,
    program_name: ''
  })

  const [projectDescription, setProjectDescription] = useState('')

  // Fetch user profile and projects for auto-fill
  useEffect(() => {
    if (isAuthenticated) {
      fetchUserProfile()
      fetchUserProjects()
    }
  }, [isAuthenticated])

  useEffect(() => {
    fetchCriteria()
  }, [])

  // Auto-fill forms when user profile is loaded
  useEffect(() => {
    if (userProfile && !isAutoFilled) {
      autoFillFromProfile(userProfile)
    }
  }, [userProfile])

  // Auto-fill project description when project is selected
  useEffect(() => {
    if (selectedProject) {
      autoFillFromProject(selectedProject)
    }
  }, [selectedProject])

  const fetchUserProfile = async () => {
    try {
      const profile = await apiClient.getMe()
      setUserProfile(profile)
    } catch (err) {
      console.error('Failed to fetch user profile:', err)
    }
  }

  const fetchUserProjects = async () => {
    try {
      const response = await apiClient.getProjects({ page: 1, limit: 50 })
      setProjects(response.projects || [])
      // Auto-select the most recent completed project
      const completedProjects = (response.projects || []).filter(
        (p: Project) => p.status === 'completed'
      )
      if (completedProjects.length > 0) {
        setSelectedProject(completedProjects[0])
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err)
    }
  }

  const autoFillFromProfile = (profile: UserProfile) => {
    // Auto-fill institution form from user's college details
    if (profile.college_name) {
      setInstitutionForm(prev => ({
        ...prev,
        name: profile.college_name || prev.name,
        // Try to extract state from college name or use default
        state: prev.state || 'Telangana'
      }))
    }

    // Auto-fill course form from user's academic details
    setCourseForm(prev => ({
      ...prev,
      department: profile.department || prev.department,
      program_name: profile.course || prev.program_name,
      semester: extractSemester(profile.year_semester) || prev.semester
    }))

    setIsAutoFilled(true)
  }

  const autoFillFromProject = (project: Project) => {
    // Extract project description
    let description = project.description || ''

    // Add tech stack info to description
    if (project.tech_stack) {
      const techInfo = typeof project.tech_stack === 'string'
        ? project.tech_stack
        : JSON.stringify(project.tech_stack)
      description += `\n\nTechnologies Used: ${techInfo}`
    }

    if (project.framework) {
      description += `\nFramework: ${project.framework}`
    }

    if (project.domain) {
      description += `\nDomain: ${project.domain}`
    }

    setProjectDescription(description.trim())

    // Auto-fill course name from project title
    setCourseForm(prev => ({
      ...prev,
      course_name: prev.course_name || generateCourseName(project),
      course_code: prev.course_code || generateCourseCode(project)
    }))
  }

  const extractSemester = (yearSemester?: string): number | null => {
    if (!yearSemester) return null
    // Try to extract semester number from strings like "4th Year / 8th Semester"
    const match = yearSemester.match(/(\d+)\s*(th|st|nd|rd)?\s*sem/i)
    if (match) return parseInt(match[1])
    // Try just a number
    const numMatch = yearSemester.match(/(\d+)/)
    if (numMatch) return parseInt(numMatch[1])
    return null
  }

  const generateCourseName = (project: Project): string => {
    // Generate course name based on project domain/framework
    if (project.domain) {
      return `${project.domain} Project`
    }
    if (project.framework) {
      return `${project.framework} Development`
    }
    return 'Software Engineering Project'
  }

  const generateCourseCode = (project: Project): string => {
    // Generate a course code based on department and semester
    const dept = courseForm.department?.substring(0, 2).toUpperCase() || 'CS'
    const sem = courseForm.semester || 6
    return `${dept}${sem}01`
  }

  const fetchCriteria = async () => {
    try {
      const response = await apiClient.getAccreditationCriteria()
      setCriteria(response.criteria || [])
    } catch (err) {
      console.error('Failed to fetch criteria:', err)
      setError('Failed to load NAAC criteria')
    } finally {
      setIsLoading(false)
    }
  }

  const handleGenerateSSR = async () => {
    if (!institutionForm.name || !institutionForm.location) {
      setError('Please fill in institution details')
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const response = await apiClient.generateSSR({
        institution: institutionForm,
        academic_year: '2024-25',
        naac_cycle: institutionForm.naac_cycle
      })
      setGeneratedDoc(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate SSR')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateCriterion = async (criterionNumber: number) => {
    if (!institutionForm.name) {
      setError('Please fill in institution details first')
      return
    }

    setIsGenerating(true)
    setError(null)
    setSelectedCriterion(criterionNumber)
    try {
      const response = await apiClient.generateCriterionDocuments(criterionNumber, {
        institution: institutionForm,
        criterion: `criterion_${criterionNumber}`,
        academic_year: '2024-25'
      })
      setGeneratedDoc(response)
    } catch (err: any) {
      setError(err.message || `Failed to generate Criterion ${criterionNumber}`)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateCourseOutcomes = async () => {
    if (!courseForm.course_name || !projectDescription) {
      setError('Please fill in course details and project description')
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const response = await apiClient.generateCourseOutcomes({
        course_info: courseForm,
        project_description: projectDescription
      })
      setGeneratedDoc(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate Course Outcomes')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateRubrics = async () => {
    if (!courseForm.course_name) {
      setError('Please fill in course details')
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const response = await apiClient.generateRubrics({
        course_info: courseForm,
        assessment_type: 'project',
        criteria_count: 5
      })
      setGeneratedDoc(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate Rubrics')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateCOPOMapping = async () => {
    if (!courseForm.course_name) {
      setError('Please fill in course details')
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const response = await apiClient.generateCOPOMapping({
        course_info: courseForm,
        course_outcomes: [] // Will be generated based on project
      })
      setGeneratedDoc(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate CO-PO Mapping')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleGenerateAttainment = async () => {
    if (!courseForm.course_name || !projectDescription) {
      setError('Please fill in course details and project description')
      return
    }

    setIsGenerating(true)
    setError(null)
    try {
      const response = await apiClient.generateAttainment({
        course_info: courseForm,
        project_description: projectDescription
      })
      setGeneratedDoc(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate Attainment')
    } finally {
      setIsGenerating(false)
    }
  }

  // Check if user is faculty/admin - show banner to access admin dashboard
  const isAdminOrFaculty = user?.role === 'admin' || user?.role === 'faculty'

  if (isLoading || authLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Admin/Faculty Banner */}
      {isAdminOrFaculty && (
        <div className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white">
          <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              <span className="font-medium">You have IQAC Coordinator access</span>
            </div>
            <button
              onClick={() => router.push('/admin/accreditation')}
              className="flex items-center gap-2 bg-white/20 hover:bg-white/30 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors"
            >
              Open Admin Dashboard
              <ExternalLink className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Award className="w-8 h-8 text-orange-500" />
            <div>
              <h1 className="text-xl font-bold">NAAC/NBA Accreditation</h1>
              <p className="text-sm text-slate-400">
                {isAdminOrFaculty
                  ? 'Student OBE Documents - For full dashboard, use Admin Portal'
                  : 'Generate OBE documents for your projects'
                }
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {isAutoFilled && (
              <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Auto-filled
              </span>
            )}
            <span className="bg-green-500/20 text-green-400 px-3 py-1 rounded-full text-sm">
              OBE Compliant
            </span>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4">
          <nav className="flex gap-1">
            {[
              { id: 'overview', label: 'Overview', icon: Info },
              { id: 'ssr', label: 'Complete SSR', icon: FileText },
              { id: 'criterion', label: 'Criterion-wise', icon: ClipboardCheck },
              { id: 'obe', label: 'OBE Documents', icon: GraduationCap },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center gap-2 px-4 py-3 border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-orange-500 text-orange-500'
                    : 'border-transparent text-slate-400 hover:text-white'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-400">
            {error}
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold mb-2">NAAC 7 Criteria Framework</h2>
              <p className="text-slate-400">Generate comprehensive documentation for NAAC accreditation</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {criteria.map((criterion, index) => {
                const Icon = CRITERIA_ICONS[index] || FileText
                return (
                  <div
                    key={criterion.number}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-orange-500/50 transition-colors cursor-pointer"
                    onClick={() => {
                      setActiveTab('criterion')
                      setSelectedCriterion(criterion.number)
                    }}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="p-2 bg-orange-500/20 rounded-lg">
                        <Icon className="w-5 h-5 text-orange-500" />
                      </div>
                      <span className="text-2xl font-bold text-orange-500">{criterion.marks}</span>
                    </div>
                    <h3 className="font-semibold mb-1">Criterion {criterion.number}</h3>
                    <p className="text-sm text-slate-400 mb-3">{criterion.name}</p>
                    <div className="text-xs text-slate-500">
                      {criterion.key_indicators.length} Key Indicators
                    </div>
                  </div>
                )
              })}
            </div>

            {/* Grading Scale */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="font-semibold mb-4">NAAC Grading Scale</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
                {[
                  { grade: 'A++', cgpa: '3.51-4.00', color: 'bg-green-500' },
                  { grade: 'A+', cgpa: '3.26-3.50', color: 'bg-green-400' },
                  { grade: 'A', cgpa: '3.01-3.25', color: 'bg-green-300' },
                  { grade: 'B++', cgpa: '2.76-3.00', color: 'bg-yellow-500' },
                  { grade: 'B+', cgpa: '2.51-2.75', color: 'bg-yellow-400' },
                  { grade: 'B', cgpa: '2.01-2.50', color: 'bg-orange-500' },
                  { grade: 'C', cgpa: '1.51-2.00', color: 'bg-orange-400' },
                  { grade: 'D', cgpa: '<=1.50', color: 'bg-red-500' },
                ].map(item => (
                  <div key={item.grade} className="text-center p-3 bg-slate-800 rounded-lg">
                    <div className={`w-8 h-8 ${item.color} rounded-full mx-auto mb-2 flex items-center justify-center text-white font-bold text-sm`}>
                      {item.grade}
                    </div>
                    <div className="text-xs text-slate-400">{item.cgpa}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick Actions - New Features */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-500" />
                Quick Actions
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button
                  onClick={() => router.push('/curriculum')}
                  className="p-4 bg-gradient-to-r from-blue-600/20 to-cyan-600/20 border border-blue-500/30 rounded-xl hover:border-blue-500 transition-all text-left"
                >
                  <BookOpen className="w-8 h-8 text-blue-400 mb-3" />
                  <h4 className="font-semibold text-white mb-1">Curriculum Mapping</h4>
                  <p className="text-sm text-slate-400">Map course syllabus to industry projects with CO-PO alignment</p>
                </button>

                <button
                  onClick={() => router.push('/evaluation')}
                  className="p-4 bg-gradient-to-r from-emerald-600/20 to-teal-600/20 border border-emerald-500/30 rounded-xl hover:border-emerald-500 transition-all text-left"
                >
                  <ClipboardCheck className="w-8 h-8 text-emerald-400 mb-3" />
                  <h4 className="font-semibold text-white mb-1">Project Evaluation</h4>
                  <p className="text-sm text-slate-400">Automated rubric-based assessment with CO attainment</p>
                </button>

                <button
                  onClick={() => router.push('/certificates')}
                  className="p-4 bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-xl hover:border-purple-500 transition-all text-left"
                >
                  <Award className="w-8 h-8 text-purple-400 mb-3" />
                  <h4 className="font-semibold text-white mb-1">Skill Certificates</h4>
                  <p className="text-sm text-slate-400">Generate certificates with OBE metrics and verification</p>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* SSR Tab */}
        {activeTab === 'ssr' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Institution Form */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-orange-500" />
                Institution Details
                {isAutoFilled && (
                  <span className="ml-2 text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                    Auto-filled from profile
                  </span>
                )}
              </h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Institution Name *</label>
                  <input
                    type="text"
                    value={institutionForm.name}
                    onChange={e => setInstitutionForm({ ...institutionForm, name: e.target.value })}
                    className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    placeholder="e.g., ABC College of Engineering"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Type</label>
                    <select
                      value={institutionForm.type}
                      onChange={e => setInstitutionForm({ ...institutionForm, type: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    >
                      <option value="University">University</option>
                      <option value="Autonomous">Autonomous</option>
                      <option value="Affiliated">Affiliated</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">NAAC Cycle</label>
                    <select
                      value={institutionForm.naac_cycle}
                      onChange={e => setInstitutionForm({ ...institutionForm, naac_cycle: parseInt(e.target.value) })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    >
                      <option value={1}>1st Cycle</option>
                      <option value={2}>2nd Cycle</option>
                      <option value={3}>3rd Cycle</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Location *</label>
                    <input
                      type="text"
                      value={institutionForm.location}
                      onChange={e => setInstitutionForm({ ...institutionForm, location: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      placeholder="City"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">State *</label>
                    <input
                      type="text"
                      value={institutionForm.state}
                      onChange={e => setInstitutionForm({ ...institutionForm, state: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      placeholder="State"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Established Year</label>
                    <input
                      type="number"
                      value={institutionForm.established_year}
                      onChange={e => setInstitutionForm({ ...institutionForm, established_year: parseInt(e.target.value) })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Previous Grade</label>
                    <input
                      type="text"
                      value={institutionForm.previous_grade}
                      onChange={e => setInstitutionForm({ ...institutionForm, previous_grade: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      placeholder="e.g., A+"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Total Students</label>
                    <input
                      type="number"
                      value={institutionForm.total_students}
                      onChange={e => setInstitutionForm({ ...institutionForm, total_students: parseInt(e.target.value) })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Total Faculty</label>
                    <input
                      type="number"
                      value={institutionForm.total_faculty}
                      onChange={e => setInstitutionForm({ ...institutionForm, total_faculty: parseInt(e.target.value) })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                    />
                  </div>
                </div>
                <button
                  onClick={handleGenerateSSR}
                  disabled={isGenerating}
                  className="w-full mt-4 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
                >
                  {isGenerating ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Generating SSR...
                    </>
                  ) : (
                    <>
                      <FileText className="w-5 h-5" />
                      Generate Complete SSR
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Generated Document Preview */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
                Generated Document
              </h3>
              {generatedDoc ? (
                <div className="space-y-4">
                  <div className="bg-slate-800 rounded-lg p-4 max-h-96 overflow-auto">
                    <pre className="text-sm text-slate-300 whitespace-pre-wrap">
                      {JSON.stringify(generatedDoc, null, 2)}
                    </pre>
                  </div>
                  <button className="w-full bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded-lg flex items-center justify-center gap-2">
                    <Download className="w-5 h-5" />
                    Download Document
                  </button>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500">
                  <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Generated documents will appear here</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Criterion-wise Tab */}
        {activeTab === 'criterion' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {criteria.map((criterion, index) => {
                const Icon = CRITERIA_ICONS[index] || FileText
                const isSelected = selectedCriterion === criterion.number
                return (
                  <button
                    key={criterion.number}
                    onClick={() => handleGenerateCriterion(criterion.number)}
                    disabled={isGenerating}
                    className={`text-left bg-slate-900 border rounded-xl p-5 transition-all ${
                      isSelected
                        ? 'border-orange-500 ring-2 ring-orange-500/20'
                        : 'border-slate-800 hover:border-orange-500/50'
                    } ${isGenerating ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className={`p-2 rounded-lg ${isSelected ? 'bg-orange-500' : 'bg-orange-500/20'}`}>
                        <Icon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-orange-500'}`} />
                      </div>
                      <span className="text-lg font-bold text-orange-500">{criterion.marks}</span>
                    </div>
                    <h3 className="font-semibold mb-1">Criterion {criterion.number}</h3>
                    <p className="text-sm text-slate-400 mb-3">{criterion.name}</p>
                    <div className="flex items-center text-xs text-orange-500">
                      Generate <ChevronRight className="w-4 h-4" />
                    </div>
                  </button>
                )
              })}
            </div>

            {isGenerating && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
                <Loader2 className="w-10 h-10 animate-spin text-orange-500 mx-auto mb-4" />
                <p className="text-lg font-semibold">Generating Criterion {selectedCriterion} Documentation...</p>
                <p className="text-slate-400">This may take a few moments</p>
              </div>
            )}

            {generatedDoc && !isGenerating && (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4">Generated: Criterion {selectedCriterion}</h3>
                <div className="bg-slate-800 rounded-lg p-4 max-h-96 overflow-auto">
                  <pre className="text-sm text-slate-300 whitespace-pre-wrap">
                    {JSON.stringify(generatedDoc, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}

        {/* OBE Tab - with Auto-fill */}
        {activeTab === 'obe' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Project Selector + Course Form */}
            <div className="space-y-6">
              {/* Project Selector - NEW */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <FolderKanban className="w-5 h-5 text-orange-500" />
                  Select Your Project
                  <span className="ml-auto text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded-full">
                    Auto-fills details
                  </span>
                </h3>

                {projects.length > 0 ? (
                  <div className="space-y-3">
                    <select
                      value={selectedProject?.id || ''}
                      onChange={e => {
                        const project = projects.find(p => p.id === e.target.value)
                        setSelectedProject(project || null)
                      }}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 focus:outline-none focus:border-orange-500"
                    >
                      <option value="">-- Select a project --</option>
                      {projects.map(project => (
                        <option key={project.id} value={project.id}>
                          {project.title} ({project.status})
                        </option>
                      ))}
                    </select>

                    {selectedProject && (
                      <div className="bg-slate-800 rounded-lg p-4 border border-green-500/30">
                        <div className="flex items-center gap-2 text-green-400 text-sm mb-2">
                          <CheckCircle2 className="w-4 h-4" />
                          Project selected - details auto-filled
                        </div>
                        <p className="text-sm text-slate-400">
                          <strong>{selectedProject.title}</strong>
                          {selectedProject.description && (
                            <span className="block mt-1 text-xs">{selectedProject.description.substring(0, 100)}...</span>
                          )}
                        </p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-6 text-slate-500">
                    <FolderKanban className="w-10 h-10 mx-auto mb-2 opacity-50" />
                    <p>No projects found</p>
                    <button
                      onClick={() => router.push('/build')}
                      className="mt-3 text-orange-500 hover:text-orange-400 text-sm"
                    >
                      Create a project first →
                    </button>
                  </div>
                )}
              </div>

              {/* Course Form */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4 flex items-center gap-2">
                  <GraduationCap className="w-5 h-5 text-orange-500" />
                  Course Details
                  {userProfile?.department && (
                    <span className="ml-2 text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">
                      Auto-filled
                    </span>
                  )}
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Course Name *</label>
                    <input
                      type="text"
                      value={courseForm.course_name}
                      onChange={e => setCourseForm({ ...courseForm, course_name: e.target.value })}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                      placeholder="e.g., Software Engineering"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Course Code *</label>
                      <input
                        type="text"
                        value={courseForm.course_code}
                        onChange={e => setCourseForm({ ...courseForm, course_code: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="e.g., CS601"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Department</label>
                      <input
                        type="text"
                        value={courseForm.department}
                        onChange={e => setCourseForm({ ...courseForm, department: e.target.value })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                        placeholder="e.g., CSE"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Semester</label>
                      <input
                        type="number"
                        value={courseForm.semester}
                        onChange={e => setCourseForm({ ...courseForm, semester: parseInt(e.target.value) })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                        min={1}
                        max={8}
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Credits</label>
                      <input
                        type="number"
                        value={courseForm.credits}
                        onChange={e => setCourseForm({ ...courseForm, credits: parseInt(e.target.value) })}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500"
                        min={1}
                        max={6}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">
                      Project/Course Description *
                      {selectedProject && (
                        <span className="ml-2 text-green-400">(Auto-filled from project)</span>
                      )}
                    </label>
                    <textarea
                      value={projectDescription}
                      onChange={e => setProjectDescription(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 focus:outline-none focus:border-orange-500 h-32"
                      placeholder="Describe the course content or project..."
                    />
                  </div>

                  {/* OBE Generation Buttons */}
                  <div className="grid grid-cols-2 gap-3 pt-4">
                    <button
                      onClick={handleGenerateCourseOutcomes}
                      disabled={isGenerating}
                      className="bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
                    >
                      {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                      Course Outcomes
                    </button>
                    <button
                      onClick={handleGenerateCOPOMapping}
                      disabled={isGenerating}
                      className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
                    >
                      {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <ClipboardCheck className="w-4 h-4" />}
                      CO-PO Mapping
                    </button>
                    <button
                      onClick={handleGenerateRubrics}
                      disabled={isGenerating}
                      className="bg-green-500 hover:bg-green-600 disabled:bg-green-500/50 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
                    >
                      {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Award className="w-4 h-4" />}
                      Rubrics
                    </button>
                    <button
                      onClick={handleGenerateAttainment}
                      disabled={isGenerating}
                      className="bg-purple-500 hover:bg-purple-600 disabled:bg-purple-500/50 text-white font-semibold py-3 rounded-lg flex items-center justify-center gap-2 transition-colors"
                    >
                      {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <GraduationCap className="w-4 h-4" />}
                      Attainment
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Side - Document Types + Generated Output */}
            <div className="space-y-6">
              {/* OBE Document Types Info */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                <h3 className="font-semibold mb-4">OBE Document Types</h3>
                <div className="space-y-3">
                  {[
                    { name: 'Course Outcomes (COs)', desc: 'With Bloom\'s Taxonomy levels (L1-L6)', color: 'bg-orange-500' },
                    { name: 'CO-PO Mapping', desc: '12 NBA Program Outcomes matrix', color: 'bg-blue-500' },
                    { name: 'Assessment Rubrics', desc: '4-level performance criteria', color: 'bg-green-500' },
                    { name: 'Attainment Calculation', desc: 'Direct & indirect methods', color: 'bg-purple-500' },
                  ].map((item, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-800 rounded-lg">
                      <div className={`w-3 h-3 rounded-full ${item.color}`} />
                      <div>
                        <div className="font-medium">{item.name}</div>
                        <div className="text-xs text-slate-400">{item.desc}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Generated Document */}
              {generatedDoc && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    Generated Document
                  </h3>
                  <div className="bg-slate-800 rounded-lg p-4 max-h-80 overflow-auto">
                    <pre className="text-sm text-slate-300 whitespace-pre-wrap">
                      {JSON.stringify(generatedDoc, null, 2)}
                    </pre>
                  </div>
                  <button className="w-full mt-4 bg-green-500 hover:bg-green-600 text-white font-semibold py-2 rounded-lg flex items-center justify-center gap-2">
                    <Download className="w-5 h-5" />
                    Download Document
                  </button>
                </div>
              )}

              {/* User Info Card */}
              {userProfile && (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
                  <h3 className="font-semibold mb-4 flex items-center gap-2">
                    <Users className="w-5 h-5 text-orange-500" />
                    Your Academic Profile
                  </h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Name:</span>
                      <span>{userProfile.full_name || 'Not set'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">College:</span>
                      <span>{userProfile.college_name || 'Not set'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Department:</span>
                      <span>{userProfile.department || 'Not set'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Semester:</span>
                      <span>{userProfile.year_semester || 'Not set'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Guide:</span>
                      <span>{userProfile.guide_name || 'Not set'}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => router.push('/complete-profile')}
                    className="w-full mt-4 text-orange-500 hover:text-orange-400 text-sm flex items-center justify-center gap-1"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Update Profile for better auto-fill
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
