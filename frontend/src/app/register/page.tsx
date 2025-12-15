'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { UserPlus, Mail, Lock, User, AlertCircle, Briefcase, GraduationCap, Building2, Users, ChevronRight, ChevronLeft, Check } from 'lucide-react'

// Google Icon SVG
const GoogleIcon = () => (
  <svg className="h-5 w-5" viewBox="0 0 24 24">
    <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
)

// GitHub Icon SVG
const GitHubIcon = () => (
  <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
  </svg>
)

// Step indicator component
const StepIndicator = ({ currentStep, totalSteps, stepTitles }: { currentStep: number, totalSteps: number, stepTitles: string[] }) => (
  <div className="flex items-center justify-center mb-6">
    {stepTitles.map((title, index) => (
      <div key={index} className="flex items-center">
        <div className="flex flex-col items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-colors ${
            index < currentStep
              ? 'bg-green-500 text-white'
              : index === currentStep
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-200 text-gray-500'
          }`}>
            {index < currentStep ? <Check className="h-4 w-4" /> : index + 1}
          </div>
          <span className={`text-xs mt-1 ${index === currentStep ? 'text-indigo-600 font-medium' : 'text-gray-500'}`}>
            {title}
          </span>
        </div>
        {index < totalSteps - 1 && (
          <div className={`w-12 h-0.5 mx-2 ${index < currentStep ? 'bg-green-500' : 'bg-gray-200'}`} />
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
    role: 'student',
    // Student Academic Details
    rollNumber: '',
    collegeName: '',
    universityName: '',
    department: '',
    course: '',
    yearSemester: '',
    batch: '',
    // Guide Details
    guideName: '',
    guideDesignation: '',
    hodName: ''
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [oauthLoading, setOauthLoading] = useState<'google' | 'github' | null>(null)
  const [isAlreadyLoggedIn, setIsAlreadyLoggedIn] = useState(false)

  // Check if already logged in
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      setIsAlreadyLoggedIn(true)
    }
  }, [])

  // Define steps based on role
  const isStudent = formData.role === 'student'
  const steps = isStudent
    ? ['Account', 'Academic', 'Guide']
    : ['Account']
  const totalSteps = steps.length

  const validateStep = (step: number): boolean => {
    setError('')

    if (step === 0) {
      if (!formData.email) {
        setError('Email is required')
        return false
      }
      if (!formData.password || formData.password.length < 8) {
        setError('Password must be at least 8 characters')
        return false
      }
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match')
        return false
      }
    }

    // Validate Academic Details (Step 1) - Required for students
    if (step === 1 && isStudent) {
      if (!formData.rollNumber.trim()) {
        setError('Roll Number is required')
        return false
      }
      if (!formData.collegeName.trim()) {
        setError('College Name is required')
        return false
      }
      if (!formData.department.trim()) {
        setError('Department is required')
        return false
      }
      if (!formData.course) {
        setError('Course is required')
        return false
      }
    }

    // Validate Guide Details (Step 2) - Required for students
    if (step === 2 && isStudent) {
      if (!formData.guideName.trim()) {
        setError('Guide Name is required')
        return false
      }
    }

    return true
  }

  const nextStep = () => {
    if (validateStep(currentStep)) {
      if (currentStep < totalSteps - 1) {
        setCurrentStep(currentStep + 1)
      }
    }
  }

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validateStep(currentStep)) return

    setLoading(true)

    try {
      await apiClient.register({
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName,
        role: formData.role,
        // Student Academic Details (only for students)
        roll_number: formData.role === 'student' ? formData.rollNumber : undefined,
        college_name: formData.role === 'student' ? formData.collegeName : undefined,
        university_name: formData.role === 'student' ? formData.universityName : undefined,
        department: formData.role === 'student' ? formData.department : undefined,
        course: formData.role === 'student' ? formData.course : undefined,
        year_semester: formData.role === 'student' ? formData.yearSemester : undefined,
        batch: formData.role === 'student' ? formData.batch : undefined,
        // Guide Details
        guide_name: formData.role === 'student' ? formData.guideName : undefined,
        guide_designation: formData.role === 'student' ? formData.guideDesignation : undefined,
        hod_name: formData.role === 'student' ? formData.hodName : undefined
      })

      // Automatically log in after registration
      const loginResponse = await apiClient.login(formData.email, formData.password)

      // Store tokens
      localStorage.setItem('access_token', loginResponse.access_token)
      localStorage.setItem('refresh_token', loginResponse.refresh_token)

      // Redirect to build
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
      setError(err.response?.data?.detail || `Failed to initiate ${provider} sign-up. Please try again.`)
      setOauthLoading(null)
    }
  }

  // Render step content
  const renderStepContent = () => {
    switch (currentStep) {
      case 0:
        return (
          <div className="space-y-4">
            {/* Role Selection */}
            <div className="space-y-2">
              <Label htmlFor="role">I am a</Label>
              <div className="relative">
                <Briefcase className="absolute left-3 top-3 h-4 w-4 text-muted-foreground z-10" />
                <Select
                  value={formData.role}
                  onValueChange={(value) => {
                    setFormData({ ...formData, role: value })
                    setCurrentStep(0) // Reset to first step when role changes
                  }}
                >
                  <SelectTrigger className="pl-10">
                    <SelectValue placeholder="Select your role" />
                  </SelectTrigger>
                  <SelectContent className="z-[100]" position="popper" sideOffset={4}>
                    <SelectItem value="student">Student</SelectItem>
                    <SelectItem value="developer">Developer</SelectItem>
                    <SelectItem value="founder">Founder</SelectItem>
                    <SelectItem value="faculty">Faculty</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* OAuth Buttons */}
            <div className="grid grid-cols-2 gap-3">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOAuthRegister('google')}
                disabled={loading || oauthLoading !== null}
                className="w-full"
              >
                {oauthLoading === 'google' ? <span className="animate-spin mr-2">...</span> : <GoogleIcon />}
                <span className="ml-2">Google</span>
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOAuthRegister('github')}
                disabled={loading || oauthLoading !== null}
                className="w-full"
              >
                {oauthLoading === 'github' ? <span className="animate-spin mr-2">...</span> : <GitHubIcon />}
                <span className="ml-2">GitHub</span>
              </Button>
            </div>

            {/* Divider */}
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-muted-foreground">Or with email</span>
              </div>
            </div>

            {/* Basic Info */}
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <div className="relative">
                <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="fullName"
                  type="text"
                  placeholder="John Doe"
                  value={formData.fullName}
                  onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
                  className="pl-10"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="Min 8 chars"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="pl-10"
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder="Confirm"
                    value={formData.confirmPassword}
                    onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                    className="pl-10"
                    required
                  />
                </div>
              </div>
            </div>
          </div>
        )

      case 1:
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-indigo-600 font-medium mb-2">
              <GraduationCap className="h-4 w-4" />
              Academic Details
              <span className="text-xs text-gray-500 font-normal ml-auto">* Required</span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="rollNumber">Roll Number <span className="text-red-500">*</span></Label>
                <Input
                  id="rollNumber"
                  type="text"
                  placeholder="21CS101"
                  value={formData.rollNumber}
                  onChange={(e) => setFormData({ ...formData, rollNumber: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="batch">Batch</Label>
                <Input
                  id="batch"
                  type="text"
                  placeholder="2021-2025"
                  value={formData.batch}
                  onChange={(e) => setFormData({ ...formData, batch: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="collegeName">College Name <span className="text-red-500">*</span></Label>
              <div className="relative">
                <Building2 className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="collegeName"
                  type="text"
                  placeholder="ABC Engineering College"
                  value={formData.collegeName}
                  onChange={(e) => setFormData({ ...formData, collegeName: e.target.value })}
                  className="pl-10"
                  required
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="universityName">University Name</Label>
              <Input
                id="universityName"
                type="text"
                placeholder="JNTU Hyderabad"
                value={formData.universityName}
                onChange={(e) => setFormData({ ...formData, universityName: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="department">Department <span className="text-red-500">*</span></Label>
                <Input
                  id="department"
                  type="text"
                  placeholder="Computer Science"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="course">Course <span className="text-red-500">*</span></Label>
                <Select
                  value={formData.course}
                  onValueChange={(value) => setFormData({ ...formData, course: value })}
                  required
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select" />
                  </SelectTrigger>
                  <SelectContent className="z-[100]" position="popper" sideOffset={4}>
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

            <div className="space-y-2">
              <Label htmlFor="yearSemester">Year / Semester</Label>
              <Input
                id="yearSemester"
                type="text"
                placeholder="4th Year / 8th Semester"
                value={formData.yearSemester}
                onChange={(e) => setFormData({ ...formData, yearSemester: e.target.value })}
              />
            </div>
          </div>
        )

      case 2:
        return (
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-indigo-600 font-medium mb-2">
              <Users className="h-4 w-4" />
              Guide / Mentor Details
              <span className="text-xs text-gray-500 font-normal ml-auto">* Required</span>
            </div>

            <div className="space-y-2">
              <Label htmlFor="guideName">Guide Name <span className="text-red-500">*</span></Label>
              <Input
                id="guideName"
                type="text"
                placeholder="Dr. John Smith"
                value={formData.guideName}
                onChange={(e) => setFormData({ ...formData, guideName: e.target.value })}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="guideDesignation">Guide Designation</Label>
              <Input
                id="guideDesignation"
                type="text"
                placeholder="Assistant Professor"
                value={formData.guideDesignation}
                onChange={(e) => setFormData({ ...formData, guideDesignation: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="hodName">HOD Name</Label>
              <Input
                id="hodName"
                type="text"
                placeholder="Dr. Jane Johnson"
                value={formData.hodName}
                onChange={(e) => setFormData({ ...formData, hodName: e.target.value })}
              />
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-700">
              <p className="font-medium">These details will be used in:</p>
              <ul className="list-disc list-inside mt-1 text-blue-600">
                <li>Project Report cover page</li>
                <li>SRS Document</li>
                <li>PPT Presentation</li>
                <li>Certificate pages</li>
              </ul>
            </div>
          </div>
        )

      default:
        return null
    }
  }

  // If already logged in, show options
  if (isAlreadyLoggedIn) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="space-y-1 pb-4">
            <div className="flex items-center justify-center mb-2">
              <div className="h-10 w-10 bg-green-600 rounded-lg flex items-center justify-center">
                <Check className="h-5 w-5 text-white" />
              </div>
            </div>
            <CardTitle className="text-xl font-bold text-center">Already Logged In</CardTitle>
            <CardDescription className="text-center text-sm">
              You are already logged in to BharatBuild AI
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button className="w-full" onClick={() => router.push('/build')}>
              Go to Build
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => {
                localStorage.removeItem('access_token')
                localStorage.removeItem('refresh_token')
                localStorage.removeItem('user')
                setIsAlreadyLoggedIn(false)
              }}
            >
              Logout & Create New Account
            </Button>
          </CardContent>
          <CardFooter className="flex flex-col pt-0">
            <div className="text-center text-sm text-gray-600">
              <Link href="/dashboard" className="text-indigo-600 hover:text-indigo-500 font-medium">
                Go to Dashboard
              </Link>
            </div>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 pb-4">
          <div className="flex items-center justify-center mb-2">
            <div className="h-10 w-10 bg-indigo-600 rounded-lg flex items-center justify-center">
              <UserPlus className="h-5 w-5 text-white" />
            </div>
          </div>
          <CardTitle className="text-xl font-bold text-center">Create Account</CardTitle>
          <CardDescription className="text-center text-sm">
            {isStudent ? 'Student registration for BharatBuild AI' : 'Start building with BharatBuild AI'}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Step Indicator - Only show for students */}
          {isStudent && (
            <StepIndicator currentStep={currentStep} totalSteps={totalSteps} stepTitles={steps} />
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            {renderStepContent()}

            {/* Navigation Buttons */}
            <div className="flex justify-between mt-6 pt-4 border-t">
              {currentStep > 0 ? (
                <Button type="button" variant="outline" onClick={prevStep}>
                  <ChevronLeft className="h-4 w-4 mr-1" />
                  Back
                </Button>
              ) : (
                <div />
              )}

              {currentStep < totalSteps - 1 ? (
                <Button type="button" onClick={nextStep}>
                  Next
                  <ChevronRight className="h-4 w-4 ml-1" />
                </Button>
              ) : (
                <Button type="submit" disabled={loading || oauthLoading !== null}>
                  {loading ? 'Creating...' : 'Create Account'}
                </Button>
              )}
            </div>
          </form>

          {currentStep === 0 && (
            <div className="text-xs text-center text-gray-500 mt-2">
              By creating an account, you agree to our{' '}
              <Link href="/terms" className="text-indigo-600 hover:underline">Terms</Link>
              {' & '}
              <Link href="/privacy" className="text-indigo-600 hover:underline">Privacy</Link>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col pt-0">
          <div className="text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link href="/login" className="text-indigo-600 hover:text-indigo-500 font-medium">
              Sign in
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
