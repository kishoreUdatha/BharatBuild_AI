'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  GraduationCap, User, Mail, Phone, Building2, CheckCircle2, AlertCircle,
  Clock, Users, Trophy, BookOpen, Brain, Code, MessageSquare, Sparkles,
  Target, Award, Zap, ArrowRight, Calendar, Shield
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface CampusDrive {
  id: string
  name: string
  company_name?: string
  description?: string
  registration_start: string
  registration_end?: string
  quiz_date?: string
  quiz_duration_minutes: number
  passing_percentage: number
  total_questions: number
  logical_questions: number
  technical_questions: number
  ai_ml_questions: number
  english_questions: number
  is_active: boolean
}

export default function CampusDrivePage() {
  const router = useRouter()
  const [drives, setDrives] = useState<CampusDrive[]>([])
  const [selectedDrive, setSelectedDrive] = useState<CampusDrive | null>(null)
  const [loading, setLoading] = useState(true)
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    college_name: '',
    department: '',
    year_of_study: '',
    roll_number: '',
    cgpa: ''
  })
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [registrationId, setRegistrationId] = useState('')

  useEffect(() => {
    fetchDrives()
  }, [])

  const fetchDrives = async () => {
    try {
      const response = await fetch(`${API_URL}/campus-drive/drives`)
      if (response.ok) {
        const data = await response.json()
        setDrives(data)
        if (data.length > 0) {
          setSelectedDrive(data[0])
        }
      }
    } catch (error) {
      console.error('Error fetching drives:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedDrive) return

    setIsSubmitting(true)
    setSubmitStatus('idle')
    setErrorMessage('')

    try {
      const payload = {
        ...formData,
        cgpa: formData.cgpa ? parseFloat(formData.cgpa) : null
      }

      const response = await fetch(`${API_URL}/campus-drive/drives/${selectedDrive.id}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Registration failed')
      }

      const data = await response.json()
      setRegistrationId(data.id)
      setSubmitStatus('success')

      localStorage.setItem('campus_drive_email', formData.email)
      localStorage.setItem('campus_drive_id', selectedDrive.id)

    } catch (error) {
      setSubmitStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Something went wrong')
    } finally {
      setIsSubmitting(false)
    }
  }

  const startQuiz = () => {
    if (selectedDrive) {
      router.push(`/campus-drive/quiz?drive=${selectedDrive.id}&email=${formData.email}`)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-cyan-500/30 rounded-full animate-spin border-t-cyan-500"></div>
            <Sparkles className="absolute inset-0 m-auto h-8 w-8 text-cyan-400 animate-pulse" />
          </div>
          <p className="mt-4 text-cyan-400 font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  // Show message when no drives are available
  if (!loading && drives.length === 0) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"></div>
        </div>

        <Card className="w-full max-w-lg bg-slate-900/80 backdrop-blur-xl border-slate-800 shadow-2xl relative z-10">
          <CardContent className="pt-10 pb-10 text-center">
            <div className="w-20 h-20 bg-amber-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="h-10 w-10 text-amber-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">No Active Drives</h2>
            <p className="text-slate-400 mb-6">
              There are currently no active campus placement drives. Please check back later or contact the administrator.
            </p>
            <Button
              onClick={() => window.location.reload()}
              className="bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-600 hover:to-blue-600 text-white"
            >
              <Zap className="mr-2 h-4 w-4" />
              Refresh Page
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (submitStatus === 'success') {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        {/* Animated background */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-green-500/10 rounded-full blur-3xl animate-pulse"></div>
          <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
        </div>

        <Card className="w-full max-w-lg bg-slate-900/80 backdrop-blur-xl border-slate-800 shadow-2xl relative z-10">
          <CardContent className="pt-10 pb-10">
            <div className="relative">
              <div className="absolute inset-0 bg-green-500/20 rounded-full blur-2xl animate-pulse"></div>
              <div className="relative w-24 h-24 bg-gradient-to-br from-green-400 to-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-green-500/30">
                <CheckCircle2 className="h-12 w-12 text-white" />
              </div>
            </div>

            <h2 className="text-3xl font-bold text-white mb-2 text-center">Registration Successful!</h2>
            <p className="text-slate-400 mb-8 text-center">
              You have been registered for <span className="text-cyan-400 font-semibold">{selectedDrive?.name}</span>
            </p>

            <div className="bg-slate-800/50 rounded-2xl p-6 mb-6 border border-slate-700">
              <h3 className="font-semibold text-white mb-4 flex items-center gap-2">
                <Target className="h-5 w-5 text-cyan-400" />
                Quiz Overview
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-slate-900/50 rounded-xl">
                  <Clock className="h-6 w-6 text-cyan-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{selectedDrive?.quiz_duration_minutes}</p>
                  <p className="text-xs text-slate-400">Minutes</p>
                </div>
                <div className="text-center p-3 bg-slate-900/50 rounded-xl">
                  <BookOpen className="h-6 w-6 text-purple-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{selectedDrive?.total_questions}</p>
                  <p className="text-xs text-slate-400">Questions</p>
                </div>
                <div className="text-center p-3 bg-slate-900/50 rounded-xl">
                  <Trophy className="h-6 w-6 text-amber-400 mx-auto mb-2" />
                  <p className="text-2xl font-bold text-white">{selectedDrive?.passing_percentage}%</p>
                  <p className="text-xs text-slate-400">To Pass</p>
                </div>
              </div>
            </div>

            <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 mb-6">
              <p className="text-amber-300 text-sm flex items-start gap-2">
                <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
                <span><strong>Important:</strong> Once you start, the timer begins. Ensure stable internet connection.</span>
              </p>
            </div>

            <Button
              onClick={startQuiz}
              className="w-full bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600 text-white py-6 text-lg font-semibold rounded-xl shadow-lg shadow-green-500/25 transition-all duration-300 hover:shadow-green-500/40 hover:scale-[1.02]"
            >
              <Zap className="mr-2 h-5 w-5" />
              Start Quiz Now
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-slate-950 relative overflow-hidden">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl"></div>
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-purple-500/10 rounded-full blur-3xl"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-500/5 rounded-full blur-3xl"></div>
      </div>

      {/* Grid pattern overlay */}
      <div className="fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px] pointer-events-none"></div>

      <div className="relative z-10 py-8 px-4">
        <div className="max-w-6xl mx-auto">

          {/* Hero Section */}
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/30 rounded-full px-4 py-2 mb-6">
              <Sparkles className="h-4 w-4 text-cyan-400" />
              <span className="text-cyan-400 text-sm font-medium">Campus Placement 2026</span>
            </div>

            <h1 className="text-5xl md:text-6xl font-bold mb-4">
              <span className="text-white">Launch Your</span>
              <br />
              <span className="bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-500 bg-clip-text text-transparent">
                Tech Career
              </span>
            </h1>

            <p className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto mb-8">
              Register for the placement drive, showcase your skills, and land your dream job at top tech companies.
            </p>

            {/* Stats */}
            <div className="flex flex-wrap justify-center gap-8 mb-8">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-cyan-500/10 rounded-lg flex items-center justify-center">
                  <Users className="h-5 w-5 text-cyan-400" />
                </div>
                <div className="text-left">
                  <p className="text-2xl font-bold text-white">500+</p>
                  <p className="text-xs text-slate-400">Students</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-purple-500/10 rounded-lg flex items-center justify-center">
                  <Building2 className="h-5 w-5 text-purple-400" />
                </div>
                <div className="text-left">
                  <p className="text-2xl font-bold text-white">50+</p>
                  <p className="text-xs text-slate-400">Companies</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 bg-green-500/10 rounded-lg flex items-center justify-center">
                  <Award className="h-5 w-5 text-green-400" />
                </div>
                <div className="text-left">
                  <p className="text-2xl font-bold text-white">90%</p>
                  <p className="text-xs text-slate-400">Placement</p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid lg:grid-cols-5 gap-8">
            {/* Left Column - Drive Info */}
            <div className="lg:col-span-2 space-y-6">
              {/* Drive Card */}
              {selectedDrive && (
                <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800 overflow-hidden">
                  <div className="bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <h2 className="text-xl font-bold text-white mb-1">{selectedDrive.name}</h2>
                        {selectedDrive.company_name && (
                          <p className="text-white/80 text-sm flex items-center gap-1">
                            <Building2 className="h-4 w-4" />
                            {selectedDrive.company_name}
                          </p>
                        )}
                      </div>
                      <div className="bg-white/20 backdrop-blur-sm rounded-lg px-3 py-1">
                        <span className="text-white text-sm font-medium">Live</span>
                      </div>
                    </div>
                  </div>

                  <CardContent className="p-6">
                    {selectedDrive.description && (
                      <p className="text-slate-400 text-sm mb-6">{selectedDrive.description}</p>
                    )}

                    {/* Question Categories */}
                    <div className="space-y-3 mb-6">
                      <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                        <Target className="h-4 w-4 text-cyan-400" />
                        Assessment Sections
                      </h3>

                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 hover:bg-blue-500/20 transition-colors">
                          <Brain className="h-6 w-6 text-blue-400 mb-2" />
                          <p className="text-white font-semibold">{selectedDrive.logical_questions}</p>
                          <p className="text-slate-400 text-xs">Logical Reasoning</p>
                        </div>

                        <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 hover:bg-green-500/20 transition-colors">
                          <Code className="h-6 w-6 text-green-400 mb-2" />
                          <p className="text-white font-semibold">{selectedDrive.technical_questions}</p>
                          <p className="text-slate-400 text-xs">Technical</p>
                        </div>

                        <div className="bg-purple-500/10 border border-purple-500/20 rounded-xl p-4 hover:bg-purple-500/20 transition-colors">
                          <BookOpen className="h-6 w-6 text-purple-400 mb-2" />
                          <p className="text-white font-semibold">{selectedDrive.ai_ml_questions}</p>
                          <p className="text-slate-400 text-xs">AI / ML</p>
                        </div>

                        <div className="bg-orange-500/10 border border-orange-500/20 rounded-xl p-4 hover:bg-orange-500/20 transition-colors">
                          <MessageSquare className="h-6 w-6 text-orange-400 mb-2" />
                          <p className="text-white font-semibold">{selectedDrive.english_questions}</p>
                          <p className="text-slate-400 text-xs">English</p>
                        </div>
                      </div>
                    </div>

                    {/* Quiz Info */}
                    <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-slate-400">
                          <Clock className="h-4 w-4" />
                          <span className="text-sm">Duration</span>
                        </div>
                        <span className="text-white font-semibold">{selectedDrive.quiz_duration_minutes} mins</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-slate-400">
                          <BookOpen className="h-4 w-4" />
                          <span className="text-sm">Questions</span>
                        </div>
                        <span className="text-white font-semibold">{selectedDrive.total_questions}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-slate-400">
                          <Trophy className="h-4 w-4" />
                          <span className="text-sm">Passing Score</span>
                        </div>
                        <span className="text-green-400 font-semibold">{selectedDrive.passing_percentage}%</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Features */}
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800">
                <CardContent className="p-6">
                  <h3 className="text-white font-semibold mb-4 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-cyan-400" />
                    Why Join?
                  </h3>
                  <div className="space-y-4">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 bg-cyan-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Zap className="h-4 w-4 text-cyan-400" />
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">Instant Results</p>
                        <p className="text-slate-400 text-xs">Get your score immediately after submission</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 bg-purple-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Award className="h-4 w-4 text-purple-400" />
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">Direct Interviews</p>
                        <p className="text-slate-400 text-xs">Qualified candidates get direct interview calls</p>
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 bg-green-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Calendar className="h-4 w-4 text-green-400" />
                      </div>
                      <div>
                        <p className="text-white text-sm font-medium">Flexible Timing</p>
                        <p className="text-slate-400 text-xs">Take the test at your convenience</p>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Right Column - Registration Form */}
            <div className="lg:col-span-3">
              <Card className="bg-slate-900/60 backdrop-blur-xl border-slate-800 shadow-2xl">
                <CardContent className="p-8">
                  <div className="mb-8">
                    <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                      <GraduationCap className="h-6 w-6 text-cyan-400" />
                      Student Registration
                    </h2>
                    <p className="text-slate-400">Fill in your details to register for the placement drive</p>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-6">
                    {submitStatus === 'error' && (
                      <Alert className="bg-red-500/10 border-red-500/30 text-red-400">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{errorMessage}</AlertDescription>
                      </Alert>
                    )}

                    {/* Personal Information */}
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 bg-cyan-500/10 rounded-lg flex items-center justify-center">
                          <User className="h-4 w-4 text-cyan-400" />
                        </div>
                        <h3 className="text-white font-semibold">Personal Information</h3>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="full_name" className="text-slate-300">Full Name *</Label>
                          <Input
                            id="full_name"
                            placeholder="John Doe"
                            value={formData.full_name}
                            onChange={(e) => handleInputChange('full_name', e.target.value)}
                            required
                            className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-cyan-500/20"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="email" className="text-slate-300">Email Address *</Label>
                          <div className="relative">
                            <Mail className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                            <Input
                              id="email"
                              type="email"
                              placeholder="john@example.com"
                              className="pl-10 bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-cyan-500/20"
                              value={formData.email}
                              onChange={(e) => handleInputChange('email', e.target.value)}
                              required
                            />
                          </div>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="phone" className="text-slate-300">Phone Number *</Label>
                        <div className="relative">
                          <Phone className="absolute left-3 top-3 h-4 w-4 text-slate-500" />
                          <Input
                            id="phone"
                            type="tel"
                            placeholder="9876543210"
                            className="pl-10 bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-cyan-500/20"
                            value={formData.phone}
                            onChange={(e) => handleInputChange('phone', e.target.value)}
                            required
                            pattern="[6-9][0-9]{9}"
                            title="Please enter a valid 10-digit Indian mobile number"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Academic Information */}
                    <div className="space-y-4 pt-4 border-t border-slate-800">
                      <div className="flex items-center gap-2 mb-4">
                        <div className="w-8 h-8 bg-purple-500/10 rounded-lg flex items-center justify-center">
                          <Building2 className="h-4 w-4 text-purple-400" />
                        </div>
                        <h3 className="text-white font-semibold">Academic Information</h3>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="college_name" className="text-slate-300">College/University Name *</Label>
                        <Input
                          id="college_name"
                          placeholder="Enter your college name"
                          value={formData.college_name}
                          onChange={(e) => handleInputChange('college_name', e.target.value)}
                          required
                          className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-cyan-500/20"
                        />
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="department" className="text-slate-300">Department *</Label>
                          <Select
                            value={formData.department}
                            onValueChange={(value) => handleInputChange('department', value)}
                            required
                          >
                            <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white focus:border-cyan-500 focus:ring-cyan-500/20">
                              <SelectValue placeholder="Select department" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-800 border-slate-700">
                              <SelectItem value="CSE" className="text-white hover:bg-slate-700">Computer Science & Engineering</SelectItem>
                              <SelectItem value="IT" className="text-white hover:bg-slate-700">Information Technology</SelectItem>
                              <SelectItem value="ECE" className="text-white hover:bg-slate-700">Electronics & Communication</SelectItem>
                              <SelectItem value="EEE" className="text-white hover:bg-slate-700">Electrical & Electronics</SelectItem>
                              <SelectItem value="MECH" className="text-white hover:bg-slate-700">Mechanical Engineering</SelectItem>
                              <SelectItem value="CIVIL" className="text-white hover:bg-slate-700">Civil Engineering</SelectItem>
                              <SelectItem value="AIDS" className="text-white hover:bg-slate-700">AI & Data Science</SelectItem>
                              <SelectItem value="OTHER" className="text-white hover:bg-slate-700">Other</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="year_of_study" className="text-slate-300">Year of Study *</Label>
                          <Select
                            value={formData.year_of_study}
                            onValueChange={(value) => handleInputChange('year_of_study', value)}
                            required
                          >
                            <SelectTrigger className="bg-slate-800/50 border-slate-700 text-white focus:border-cyan-500 focus:ring-cyan-500/20">
                              <SelectValue placeholder="Select year" />
                            </SelectTrigger>
                            <SelectContent className="bg-slate-800 border-slate-700">
                              <SelectItem value="1st Year" className="text-white hover:bg-slate-700">1st Year</SelectItem>
                              <SelectItem value="2nd Year" className="text-white hover:bg-slate-700">2nd Year</SelectItem>
                              <SelectItem value="3rd Year" className="text-white hover:bg-slate-700">3rd Year</SelectItem>
                              <SelectItem value="4th Year" className="text-white hover:bg-slate-700">4th Year</SelectItem>
                              <SelectItem value="PG 1st Year" className="text-white hover:bg-slate-700">PG 1st Year</SelectItem>
                              <SelectItem value="PG 2nd Year" className="text-white hover:bg-slate-700">PG 2nd Year</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="roll_number" className="text-slate-300">Roll Number</Label>
                          <Input
                            id="roll_number"
                            placeholder="Enter your roll number"
                            value={formData.roll_number}
                            onChange={(e) => handleInputChange('roll_number', e.target.value)}
                            className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-cyan-500/20"
                          />
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="cgpa" className="text-slate-300">CGPA (Optional)</Label>
                          <Input
                            id="cgpa"
                            type="number"
                            step="0.01"
                            min="0"
                            max="10"
                            placeholder="e.g., 8.5"
                            value={formData.cgpa}
                            onChange={(e) => handleInputChange('cgpa', e.target.value)}
                            className="bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 focus:border-cyan-500 focus:ring-cyan-500/20"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Submit Button */}
                    <div className="pt-4">
                      <Button
                        type="submit"
                        className="w-full bg-gradient-to-r from-cyan-500 via-blue-500 to-purple-500 hover:from-cyan-600 hover:via-blue-600 hover:to-purple-600 text-white py-6 text-lg font-semibold rounded-xl shadow-lg shadow-cyan-500/25 transition-all duration-300 hover:shadow-cyan-500/40 hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                        disabled={isSubmitting || !selectedDrive}
                      >
                        {isSubmitting ? (
                          <>
                            <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Registering...
                          </>
                        ) : (
                          <>
                            Register & Start Quiz
                            <ArrowRight className="ml-2 h-5 w-5" />
                          </>
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>

              <p className="text-center text-slate-500 text-sm mt-6">
                By registering, you agree to our terms and conditions.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
