'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
  Building2,
  Users,
  BookOpen,
  CheckCircle2,
  ArrowRight,
  Plus,
  Trash2,
  Loader2,
  GraduationCap,
  Mail,
  Send,
  UserPlus,
  ChevronRight,
  Award
} from 'lucide-react'

interface Department {
  name: string
  code: string
  hod_name: string
  hod_email: string
}

interface Program {
  name: string
  code: string
  department_id: string
  degree_type: string
  duration_years: number
  intake: number
}

interface TeamMember {
  email: string
  name: string
  naac_role: string
  criterion_number?: number
}

const DEGREE_TYPES = [
  'B.Tech', 'M.Tech', 'B.E', 'M.E', 'MBA', 'MCA', 'BCA', 'B.Sc', 'M.Sc',
  'B.Com', 'M.Com', 'BA', 'MA', 'B.Pharm', 'M.Pharm', 'MBBS', 'BDS'
]

const NAAC_ROLES = [
  { value: 'iqac_coordinator', label: 'IQAC Coordinator', description: 'Manages quality assurance' },
  { value: 'criterion_coordinator', label: 'Criterion Coordinator', description: 'Manages specific criterion' },
  { value: 'department_coordinator', label: 'Department Coordinator', description: 'Manages department data' },
  { value: 'documentation_team', label: 'Documentation Team', description: 'Uploads evidence' },
  { value: 'it_analytics', label: 'IT/Data Analytics', description: 'Manages reports' },
]

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export default function SetupWizardPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const collegeId = searchParams.get('college_id')

  const [currentStep, setCurrentStep] = useState<'departments' | 'programs' | 'team' | 'complete'>('departments')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  // Departments
  const [departments, setDepartments] = useState<Department[]>([
    { name: '', code: '', hod_name: '', hod_email: '' }
  ])

  // Programs
  const [programs, setPrograms] = useState<Program[]>([
    { name: '', code: '', department_id: '', degree_type: 'B.Tech', duration_years: 4, intake: 60 }
  ])
  const [savedDepartments, setSavedDepartments] = useState<Array<{ id: string, name: string }>>([])

  // Team
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([
    { email: '', name: '', naac_role: 'iqac_coordinator' }
  ])

  // Progress
  const [progress, setProgress] = useState({
    departments_added: false,
    programs_added: false,
    team_invited: false,
    completion_percentage: 15
  })

  const addDepartment = () => {
    setDepartments([...departments, { name: '', code: '', hod_name: '', hod_email: '' }])
  }

  const removeDepartment = (index: number) => {
    if (departments.length > 1) {
      setDepartments(departments.filter((_, i) => i !== index))
    }
  }

  const updateDepartment = (index: number, field: keyof Department, value: string) => {
    const updated = [...departments]
    updated[index] = { ...updated[index], [field]: value }
    setDepartments(updated)
  }

  const addProgram = () => {
    setPrograms([...programs, { name: '', code: '', department_id: '', degree_type: 'B.Tech', duration_years: 4, intake: 60 }])
  }

  const removeProgram = (index: number) => {
    if (programs.length > 1) {
      setPrograms(programs.filter((_, i) => i !== index))
    }
  }

  const updateProgram = (index: number, field: keyof Program, value: any) => {
    const updated = [...programs]
    updated[index] = { ...updated[index], [field]: value }
    setPrograms(updated)
  }

  const addTeamMember = () => {
    setTeamMembers([...teamMembers, { email: '', name: '', naac_role: 'department_coordinator' }])
  }

  const removeTeamMember = (index: number) => {
    if (teamMembers.length > 1) {
      setTeamMembers(teamMembers.filter((_, i) => i !== index))
    }
  }

  const updateTeamMember = (index: number, field: keyof TeamMember, value: any) => {
    const updated = [...teamMembers]
    updated[index] = { ...updated[index], [field]: value }
    setTeamMembers(updated)
  }

  const saveDepartments = async () => {
    const validDepts = departments.filter(d => d.name.trim())
    if (validDepts.length === 0) {
      setError('Please add at least one department')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/onboarding/profile/${collegeId}/departments`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ departments: validDepts })
      })

      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Failed to save departments')

      setSavedDepartments(data.map((d: any) => ({ id: d.id, name: d.name })))
      setProgress(prev => ({ ...prev, departments_added: true, completion_percentage: 40 }))
      setCurrentStep('programs')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const savePrograms = async () => {
    const validProgs = programs.filter(p => p.name.trim())
    if (validProgs.length === 0) {
      setError('Please add at least one program')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/onboarding/profile/${collegeId}/programs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ programs: validProgs })
      })

      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Failed to save programs')

      setProgress(prev => ({ ...prev, programs_added: true, completion_percentage: 65 }))
      setCurrentStep('team')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const inviteTeam = async () => {
    const validMembers = teamMembers.filter(m => m.email.trim())
    if (validMembers.length === 0) {
      // Skip team invitation
      completeOnboarding()
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_URL}/onboarding/profile/${collegeId}/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ invitations: validMembers })
      })

      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Failed to send invitations')

      setProgress(prev => ({ ...prev, team_invited: true, completion_percentage: 85 }))
      completeOnboarding()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const completeOnboarding = async () => {
    setIsLoading(true)
    try {
      await fetch(`${API_URL}/onboarding/profile/${collegeId}/complete-onboarding`, {
        method: 'POST'
      })
      setCurrentStep('complete')
    } catch (err) {
      // Continue anyway
      setCurrentStep('complete')
    } finally {
      setIsLoading(false)
    }
  }

  const skipStep = () => {
    if (currentStep === 'departments') {
      setCurrentStep('programs')
    } else if (currentStep === 'programs') {
      setCurrentStep('team')
    } else if (currentStep === 'team') {
      completeOnboarding()
    }
  }

  if (!collegeId) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">Invalid setup link</p>
          <Link href="/onboarding/college" className="text-orange-400 hover:underline">
            Start Registration
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-amber-500 rounded-xl flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold bg-gradient-to-r from-orange-400 to-amber-400 bg-clip-text text-transparent">
              Setup Wizard
            </span>
          </div>

          {/* Progress Bar */}
          <div className="flex items-center gap-4">
            <div className="w-48 h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-orange-500 to-amber-500 transition-all duration-500"
                style={{ width: `${progress.completion_percentage}%` }}
              />
            </div>
            <span className="text-sm text-slate-400">{progress.completion_percentage}%</span>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12">
        {/* Step Indicators */}
        <div className="flex items-center justify-center mb-12">
          {[
            { key: 'departments', label: 'Departments', icon: Building2 },
            { key: 'programs', label: 'Programs', icon: BookOpen },
            { key: 'team', label: 'Team', icon: Users },
            { key: 'complete', label: 'Complete', icon: CheckCircle2 },
          ].map((step, index) => (
            <div key={step.key} className="flex items-center">
              <div className={`flex items-center gap-2 px-4 py-2 rounded-full transition-colors ${
                currentStep === step.key
                  ? 'bg-orange-500 text-white'
                  : progress[`${step.key}_added` as keyof typeof progress] || step.key === 'complete' && currentStep === 'complete'
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-slate-800 text-slate-400'
              }`}>
                <step.icon className="w-4 h-4" />
                <span className="text-sm font-medium hidden sm:block">{step.label}</span>
              </div>
              {index < 3 && <ChevronRight className="w-5 h-5 text-slate-600 mx-2" />}
            </div>
          ))}
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg mb-6 text-center">
            {error}
          </div>
        )}

        {/* Step 1: Departments */}
        {currentStep === 'departments' && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold mb-2">Add Your Departments</h1>
              <p className="text-slate-400">
                Add the departments in your college. You can add more later.
              </p>
            </div>

            <div className="space-y-4">
              {departments.map((dept, index) => (
                <div key={index} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium">Department {index + 1}</h3>
                    {departments.length > 1 && (
                      <button
                        onClick={() => removeDepartment(index)}
                        className="text-red-400 hover:text-red-300 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Department Name *</label>
                      <input
                        type="text"
                        value={dept.name}
                        onChange={(e) => updateDepartment(index, 'name', e.target.value)}
                        placeholder="e.g., Computer Science & Engineering"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Code</label>
                      <input
                        type="text"
                        value={dept.code}
                        onChange={(e) => updateDepartment(index, 'code', e.target.value)}
                        placeholder="e.g., CSE"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">HOD Name</label>
                      <input
                        type="text"
                        value={dept.hod_name}
                        onChange={(e) => updateDepartment(index, 'hod_name', e.target.value)}
                        placeholder="e.g., Dr. Sharma"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">HOD Email</label>
                      <input
                        type="email"
                        value={dept.hod_email}
                        onChange={(e) => updateDepartment(index, 'hod_email', e.target.value)}
                        placeholder="hod.cse@college.edu"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={addDepartment}
              className="flex items-center gap-2 text-orange-400 hover:text-orange-300"
            >
              <Plus className="w-4 h-4" /> Add Another Department
            </button>

            <div className="flex justify-between pt-6">
              <button
                onClick={skipStep}
                className="text-slate-400 hover:text-white"
              >
                Skip for now
              </button>
              <button
                onClick={saveDepartments}
                disabled={isLoading}
                className="flex items-center gap-2 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium disabled:opacity-50"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Save & Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Programs */}
        {currentStep === 'programs' && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold mb-2">Add Your Programs</h1>
              <p className="text-slate-400">
                Add the academic programs offered by your college.
              </p>
            </div>

            <div className="space-y-4">
              {programs.map((prog, index) => (
                <div key={index} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium">Program {index + 1}</h3>
                    {programs.length > 1 && (
                      <button
                        onClick={() => removeProgram(index)}
                        className="text-red-400 hover:text-red-300 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="md:col-span-2">
                      <label className="block text-sm text-slate-400 mb-1">Program Name *</label>
                      <input
                        type="text"
                        value={prog.name}
                        onChange={(e) => updateProgram(index, 'name', e.target.value)}
                        placeholder="e.g., Computer Science & Engineering"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Degree Type</label>
                      <select
                        value={prog.degree_type}
                        onChange={(e) => updateProgram(index, 'degree_type', e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-orange-500 outline-none"
                      >
                        {DEGREE_TYPES.map(type => (
                          <option key={type} value={type}>{type}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Department</label>
                      <select
                        value={prog.department_id}
                        onChange={(e) => updateProgram(index, 'department_id', e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-orange-500 outline-none"
                      >
                        <option value="">Select Department</option>
                        {savedDepartments.map(dept => (
                          <option key={dept.id} value={dept.id}>{dept.name}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Duration (Years)</label>
                      <input
                        type="number"
                        value={prog.duration_years}
                        onChange={(e) => updateProgram(index, 'duration_years', parseInt(e.target.value))}
                        min={1}
                        max={7}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-orange-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Intake</label>
                      <input
                        type="number"
                        value={prog.intake}
                        onChange={(e) => updateProgram(index, 'intake', parseInt(e.target.value))}
                        min={1}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-orange-500 outline-none"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={addProgram}
              className="flex items-center gap-2 text-orange-400 hover:text-orange-300"
            >
              <Plus className="w-4 h-4" /> Add Another Program
            </button>

            <div className="flex justify-between pt-6">
              <button
                onClick={skipStep}
                className="text-slate-400 hover:text-white"
              >
                Skip for now
              </button>
              <button
                onClick={savePrograms}
                disabled={isLoading}
                className="flex items-center gap-2 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium disabled:opacity-50"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Save & Continue <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Team */}
        {currentStep === 'team' && (
          <div className="space-y-6">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold mb-2">Invite Your Team</h1>
              <p className="text-slate-400">
                Invite faculty members to help with accreditation data entry.
              </p>
            </div>

            <div className="space-y-4">
              {teamMembers.map((member, index) => (
                <div key={index} className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-medium">Team Member {index + 1}</h3>
                    {teamMembers.length > 1 && (
                      <button
                        onClick={() => removeTeamMember(index)}
                        className="text-red-400 hover:text-red-300 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Email *</label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
                        <input
                          type="email"
                          value={member.email}
                          onChange={(e) => updateTeamMember(index, 'email', e.target.value)}
                          placeholder="faculty@college.edu"
                          className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Name</label>
                      <input
                        type="text"
                        value={member.name}
                        onChange={(e) => updateTeamMember(index, 'name', e.target.value)}
                        placeholder="Dr. Faculty Name"
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white placeholder-slate-500 focus:border-orange-500 outline-none"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-slate-400 mb-1">Role</label>
                      <select
                        value={member.naac_role}
                        onChange={(e) => updateTeamMember(index, 'naac_role', e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-white focus:border-orange-500 outline-none"
                      >
                        {NAAC_ROLES.map(role => (
                          <option key={role.value} value={role.value}>{role.label}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={addTeamMember}
              className="flex items-center gap-2 text-orange-400 hover:text-orange-300"
            >
              <UserPlus className="w-4 h-4" /> Add Another Member
            </button>

            <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <p className="text-sm text-slate-300">
                Team members will receive an email invitation to join and can start entering data
                for their assigned criteria.
              </p>
            </div>

            <div className="flex justify-between pt-6">
              <button
                onClick={skipStep}
                className="text-slate-400 hover:text-white"
              >
                Skip for now
              </button>
              <button
                onClick={inviteTeam}
                disabled={isLoading}
                className="flex items-center gap-2 px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium disabled:opacity-50"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Send Invitations & Finish
              </button>
            </div>
          </div>
        )}

        {/* Step 4: Complete */}
        {currentStep === 'complete' && (
          <div className="text-center py-12">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="w-10 h-10 text-green-400" />
            </div>

            <h1 className="text-3xl font-bold mb-4">Setup Complete!</h1>
            <p className="text-slate-400 mb-8 max-w-md mx-auto">
              Your college is now set up for NAAC/NBA accreditation.
              Start entering your accreditation data.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link
                href="/accreditation/dashboard"
                className="flex items-center justify-center gap-2 px-8 py-3 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white rounded-lg font-medium"
              >
                <Award className="w-5 h-5" />
                Go to Dashboard
              </Link>
              <Link
                href="/accreditation/criterion/1"
                className="flex items-center justify-center gap-2 px-8 py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-lg font-medium"
              >
                Start Data Entry
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-2xl mx-auto">
              <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <div className="text-2xl font-bold text-orange-400 mb-1">7</div>
                <div className="text-sm text-slate-400">Criteria to Complete</div>
              </div>
              <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <div className="text-2xl font-bold text-green-400 mb-1">700</div>
                <div className="text-sm text-slate-400">Total Marks</div>
              </div>
              <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
                <div className="text-2xl font-bold text-blue-400 mb-1">AI</div>
                <div className="text-sm text-slate-400">Assisted SSR</div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
