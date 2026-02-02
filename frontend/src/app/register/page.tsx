'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api-client'
import { setAccessToken } from '@/lib/auth-utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { UserPlus, Mail, Lock, User, AlertCircle, Briefcase, GraduationCap, Building2, Users, ChevronRight, ChevronLeft, Check, Phone, Zap, Sparkles, Shield, Clock } from 'lucide-react'

// Google Icon SVG
const GoogleIcon = () => (
  <svg className="h-4 w-4" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
)

// GitHub Icon SVG
const GitHubIcon = () => (
  <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
)

// Step indicator component
const StepIndicator = ({ currentStep, totalSteps, stepTitles }: { currentStep: number, totalSteps: number, stepTitles: string[] }) => (
  <div className="flex items-center justify-center gap-1">
    {stepTitles.map((title, index) => (
      <div key={index} className="flex items-center">
        <div className="flex flex-col items-center">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium transition-all ${
            index < currentStep
              ? 'bg-green-500 text-white'
              : index === currentStep
                ? 'bg-gradient-to-r from-blue-500 to-cyan-500 text-white shadow-lg shadow-blue-500/25'
                : 'bg-white/10 text-gray-400 border border-white/20'
          }`}>
            {index < currentStep ? <Check className="h-3 w-3" /> : index + 1}
          </div>
          <span className={`text-[10px] mt-1 ${index === currentStep ? 'text-cyan-400 font-medium' : 'text-gray-500'}`}>
            {title}
          </span>
        </div>
        {index < totalSteps - 1 && (
          <div className={`w-8 h-0.5 mx-1 ${index < currentStep ? 'bg-green-500' : 'bg-white/10'}`} />
        )}
      </div>
    ))}
  </div>
)

export default function RegisterPage() {
  const router = useRouter()
  const [currentStep, setCurrentStep] = useState(0)
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    phone: '',
    role: 'student',
    rollNumber: '',
    collegeName: '',
    universityName: '',
    department: '',
    course: '',
    yearSemester: '',
    batch: '',
    guideName: '',
    guideDesignation: '',
    hodName: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<'google' | 'github' | null>(null)
  const [isAlreadyLoggedIn, setIsAlreadyLoggedIn] = useState(false)

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      setIsAlreadyLoggedIn(true)
    }
  }, [])

  const isStudent = formData.role === 'student'
  const steps = isStudent ? ['Account', 'Academic', 'Guide'] : ['Account']
  const totalSteps = steps.length

  const validateStep = (step: number): boolean => {
    setError('')
    if (step === 0) {
      if (!formData.email) { setError('Email is required'); return false }
      if (!formData.password || formData.password.length < 8) { setError('Password must be at least 8 characters'); return false }
      if (formData.password !== formData.confirmPassword) { setError('Passwords do not match'); return false }
    }
    if (step === 1 && isStudent) {
      if (!formData.rollNumber.trim()) { setError('Roll Number is required'); return false }
      if (!formData.collegeName.trim()) { setError('College Name is required'); return false }
      if (!formData.department.trim()) { setError('Department is required'); return false }
      if (!formData.course) { setError('Course is required'); return false }
    }
    if (step === 2 && isStudent) {
      if (!formData.guideName.trim()) { setError('Guide Name is required'); return false }
    }
    return true
  }

  const nextStep = () => { if (validateStep(currentStep) && currentStep < totalSteps - 1) setCurrentStep(currentStep + 1) }
  const prevStep = () => { if (currentStep > 0) setCurrentStep(currentStep - 1) }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!validateStep(currentStep)) return
    setLoading(true)
    try {
      await apiClient.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName,
        phone: formData.phone || undefined,
        role: formData.role,
        roll_number: formData.role === 'student' ? formData.rollNumber : undefined,
        college_name: formData.role === 'student' ? formData.collegeName : undefined,
        university_name: formData.role === 'student' ? formData.universityName : undefined,
        department: formData.role === 'student' ? formData.department : undefined,
        course: formData.role === 'student' ? formData.course : undefined,
        year_semester: formData.role === 'student' ? formData.yearSemester : undefined,
        batch: formData.role === 'student' ? formData.batch : undefined,
        guide_name: formData.role === 'student' ? formData.guideName : undefined,
        guide_designation: formData.role === 'student' ? formData.guideDesignation : undefined,
        hod_name: formData.role === 'student' ? formData.hodName : undefined
      })
      const loginResponse = await apiClient.login(formData.email, formData.password)
      setAccessToken(loginResponse.access_token)
      localStorage.setItem('refresh_token', loginResponse.refresh_token)
      router.push('/build')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleOAuthRegister = async (provider: 'google' | 'github') => {
    setError('')
    setOauthLoading(provider)
    try {
      await apiClient.initiateOAuth(provider, formData.role)
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to initiate ${provider} sign-up.`)
      setOauthLoading(null)
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4">
            {/* OAuth + Role Row */}
            <div className="grid grid-cols-3 gap-3 items-end">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">I am a</Label>
                <Select value={formData.role} onValueChange={(value) => { setFormData({ ...formData, role: value }); setCurrentStep(0) }}>
                  <SelectTrigger className="h-10 bg-white/5 border-white/10 text-white">
                    <SelectValue placeholder="Role" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1a2e] border-white/10">
                    <SelectItem value="student">Student</SelectItem>
                    <SelectItem value="developer">Developer</SelectItem>
                    <SelectItem value="founder">Founder</SelectItem>
                    <SelectItem value="faculty">Faculty</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Quick Sign Up</Label>
                <Button type="button" variant="outline" onClick={() => handleOAuthRegister('google')} disabled={loading || oauthLoading !== null}
                  className="w-full h-10 bg-white/5 border-white/10 text-white hover:bg-white/10 hover:text-white">
                  {oauthLoading === 'google' ? <span className="animate-spin">...</span> : <GoogleIcon />}
                  <span className="ml-2 text-xs">Google</span>
                </Button>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400 opacity-0">.</Label>
                <Button type="button" variant="outline" onClick={() => handleOAuthRegister('github')} disabled={loading || oauthLoading !== null}
                  className="w-full h-10 bg-white/5 border-white/10 text-white hover:bg-white/10 hover:text-white">
                  {oauthLoading === 'github' ? <span className="animate-spin">...</span> : <GitHubIcon />}
                  <span className="ml-2 text-xs">GitHub</span>
                </Button>
              </div>
            </div>

            {/* Divider */}
            <div className="relative py-2">
              <div className="absolute inset-0 flex items-center"><span className="w-full border-t border-white/10" /></div>
              <div className="relative flex justify-center text-[10px] uppercase">
                <span className="bg-[#0f0f1a] px-3 text-gray-500">Or register with email</span>
              </div>
            </div>

            {/* Name, Email, Phone */}
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Full Name</Label>
                <div className="relative">
                  <User className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <Input id="fullName" type="text" placeholder="John Doe" value={formData.fullName}
                    onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                    className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Email <span className="text-red-400">*</span></Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <Input id="email" type="email" placeholder="you@example.com" value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Phone</Label>
                <div className="relative">
                  <Phone className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <Input id="phone" type="tel" placeholder="9876543210" value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value.replace(/\D/g, '').slice(0, 10) })}
                    className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" maxLength={10} />
                </div>
              </div>
            </div>

            {/* Password */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Password <span className="text-red-400">*</span></Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <Input id="password" type="password" placeholder="Min 8 characters" value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Confirm Password <span className="text-red-400">*</span></Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <Input id="confirmPassword" type="password" placeholder="Confirm password" value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
                </div>
              </div>
            </div>
          </div>
        )

      case 1:
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-cyan-400 font-medium">
              <GraduationCap className="h-4 w-4" />
              Academic Details
              <span className="text-[10px] text-gray-500 font-normal ml-auto">* Required fields</span>
            </div>

            {/* Row 1 */}
            <div className="grid grid-cols-4 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Roll No. <span className="text-red-400">*</span></Label>
                <Input id="rollNumber" type="text" placeholder="21CS101" value={formData.rollNumber}
                  onChange={(e) => setFormData({ ...formData, rollNumber: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Batch</Label>
                <Input id="batch" type="text" placeholder="2021-2025" value={formData.batch}
                  onChange={(e) => setFormData({ ...formData, batch: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Year / Sem</Label>
                <Input id="yearSemester" type="text" placeholder="4th / 8th" value={formData.yearSemester}
                  onChange={(e) => setFormData({ ...formData, yearSemester: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Course <span className="text-red-400">*</span></Label>
                <Select value={formData.course} onValueChange={(value) => setFormData({ ...formData, course: value })}>
                  <SelectTrigger className="h-10 bg-white/5 border-white/10 text-white">
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="bg-[#1a1a2e] border-white/10">
                    <SelectItem value="B.Tech">B.Tech</SelectItem>
                    <SelectItem value="M.Tech">M.Tech</SelectItem>
                    <SelectItem value="MCA">MCA</SelectItem>
                    <SelectItem value="BCA">BCA</SelectItem>
                    <SelectItem value="B.Sc">B.Sc</SelectItem>
                    <SelectItem value="M.Sc">M.Sc</SelectItem>
                    <SelectItem value="BE">BE</SelectItem>
                    <SelectItem value="ME">ME</SelectItem>
                    <SelectItem value="Other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Row 2 */}
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">College <span className="text-red-400">*</span></Label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-3 h-4 w-4 text-gray-500" />
                  <Input id="collegeName" type="text" placeholder="ABC Engineering College" value={formData.collegeName}
                    onChange={(e) => setFormData({ ...formData, collegeName: e.target.value })}
                    className="pl-10 h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">University</Label>
                <Input id="universityName" type="text" placeholder="JNTU Hyderabad" value={formData.universityName}
                  onChange={(e) => setFormData({ ...formData, universityName: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Department <span className="text-red-400">*</span></Label>
                <Input id="department" type="text" placeholder="Computer Science" value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
              </div>
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-xs text-cyan-400 font-medium">
              <Users className="h-4 w-4" />
              Guide / Mentor Details
              <span className="text-[10px] text-gray-500 font-normal ml-auto">* Required fields</span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Guide Name <span className="text-red-400">*</span></Label>
                <Input id="guideName" type="text" placeholder="Dr. John Smith" value={formData.guideName}
                  onChange={(e) => setFormData({ ...formData, guideName: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" required />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">Designation</Label>
                <Input id="guideDesignation" type="text" placeholder="Assistant Professor" value={formData.guideDesignation}
                  onChange={(e) => setFormData({ ...formData, guideDesignation: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs text-gray-400">HOD Name</Label>
                <Input id="hodName" type="text" placeholder="Dr. Jane Johnson" value={formData.hodName}
                  onChange={(e) => setFormData({ ...formData, hodName: e.target.value })}
                  className="h-10 bg-white/5 border-white/10 text-white placeholder:text-gray-500 focus:border-blue-500/50" />
              </div>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-xs text-blue-300">
              <p className="font-medium flex items-center gap-2">
                <Sparkles className="h-3 w-3" />
                These details will appear in: Project Report, SRS, PPT & Certificates
              </p>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  if (isAlreadyLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#0f0f1a] flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-[#111118] rounded-2xl border border-white/10 p-8 text-center">
          <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Check className="h-6 w-6 text-green-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Already Logged In</h2>
          <p className="text-gray-400 text-sm mb-6">You are already logged in to BharatBuild AI</p>
          <div className="space-y-3">
            <Button onClick={() => router.push('/build')} className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white">
              Go to Build <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
            <Button variant="outline" onClick={() => { localStorage.removeItem('access_token'); localStorage.removeItem('refresh_token'); localStorage.removeItem('user'); setIsAlreadyLoggedIn(false) }}
              className="w-full border-white/10 text-gray-300 hover:bg-white/5 hover:text-white">
              Logout & Create New Account
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#0f0f1a] flex">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-2/5 flex-col justify-between p-8 bg-gradient-to-br from-[#0a0a0f] via-[#111128] to-[#0a0a0f] border-r border-white/5">
        <div>
          <Link href="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="font-bold text-xl text-white">BharatBuild</span>
          </Link>
        </div>

        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-3">Build Your Final Year Project with AI</h1>
            <p className="text-gray-400">Complete working code + documentation in minutes, not months.</p>
          </div>

          <div className="space-y-4">
            {[
              { icon: Sparkles, title: 'AI-Powered Generation', desc: 'Full stack projects with one prompt' },
              { icon: Shield, title: 'Academic Ready', desc: 'SRS, Report, PPT & Viva Q&A included' },
              { icon: Clock, title: 'Save 100+ Hours', desc: 'From idea to submission in minutes' },
            ].map((feature, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center flex-shrink-0">
                  <feature.icon className="w-4 h-4 text-cyan-400" />
                </div>
                <div>
                  <h3 className="text-sm font-medium text-white">{feature.title}</h3>
                  <p className="text-xs text-gray-500">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="text-xs text-gray-600">
          Trusted by 95,000+ students across India
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="flex-1 flex items-center justify-center p-4 lg:p-8">
        <div className="w-full max-w-2xl">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center justify-center gap-2 mb-6">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-lg text-white">BharatBuild</span>
          </div>

          <div className="bg-[#111118]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-6 shadow-2xl">
            {/* Header */}
            <div className="text-center mb-5">
              <h2 className="text-xl font-bold text-white">Create Account</h2>
              <p className="text-gray-400 text-sm mt-1">
                {isStudent ? 'Student registration for academic projects' : 'Start building with AI'}
              </p>
            </div>

            {/* Step Indicator */}
            {isStudent && (
              <div className="mb-5">
                <StepIndicator currentStep={currentStep} totalSteps={totalSteps} stepTitles={steps} />
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2 text-red-400 text-sm">
                <AlertCircle className="h-4 w-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit}>
              {renderStepContent()}

              {/* Navigation */}
              <div className="flex items-center justify-between mt-6 pt-4 border-t border-white/10">
                {currentStep > 0 ? (
                  <Button type="button" variant="outline" onClick={prevStep} size="sm"
                    className="border-white/10 text-gray-300 hover:bg-white/5 hover:text-white">
                    <ChevronLeft className="h-4 w-4 mr-1" /> Back
                  </Button>
                ) : <div />}

                {currentStep < totalSteps - 1 ? (
                  <Button type="button" onClick={nextStep} size="sm"
                    className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white">
                    Next <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                ) : (
                  <Button type="submit" disabled={loading || oauthLoading !== null} size="sm"
                    className="bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white shadow-lg shadow-blue-500/25">
                    {loading ? 'Creating...' : 'Create Account'}
                  </Button>
                )}
              </div>
            </form>

            {/* Footer */}
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/10 text-xs text-gray-500">
              <span>
                Already have an account?{' '}
                <Link href="/login" className="text-cyan-400 hover:text-cyan-300 font-medium">Sign in</Link>
              </span>
              <span>
                <Link href="/terms" className="hover:text-gray-300">Terms</Link>
                {' & '}
                <Link href="/privacy" className="hover:text-gray-300">Privacy</Link>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
