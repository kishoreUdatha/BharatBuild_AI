'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  GraduationCap, User, Mail, Phone, Building2, CheckCircle2, AlertCircle,
  Clock, Users, Trophy, BookOpen, Brain, Code, MessageSquare
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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
      const response = await fetch(`${API_URL}/api/v1/campus-drive/drives`)
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

      const response = await fetch(`${API_URL}/api/v1/campus-drive/drives/${selectedDrive.id}/register`, {
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

      // Store email for quiz
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
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  if (submitStatus === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-lg text-center shadow-2xl">
          <CardContent className="pt-10 pb-10">
            <div className="w-24 h-24 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="h-12 w-12 text-green-600" />
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Registration Successful!</h2>
            <p className="text-gray-600 mb-6">
              You have been registered for <strong>{selectedDrive?.name}</strong>
            </p>

            <div className="bg-blue-50 rounded-lg p-6 mb-6 text-left">
              <h3 className="font-semibold text-blue-900 mb-3">Quiz Details:</h3>
              <ul className="space-y-2 text-blue-800">
                <li className="flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Duration: {selectedDrive?.quiz_duration_minutes} minutes
                </li>
                <li className="flex items-center gap-2">
                  <BookOpen className="h-4 w-4" />
                  Total Questions: {selectedDrive?.total_questions}
                </li>
                <li className="flex items-center gap-2">
                  <Trophy className="h-4 w-4" />
                  Passing: {selectedDrive?.passing_percentage}%
                </li>
              </ul>
            </div>

            <div className="bg-amber-50 rounded-lg p-4 mb-6">
              <p className="text-amber-800 text-sm">
                <strong>Important:</strong> Once you start the quiz, the timer will begin.
                Make sure you have a stable internet connection.
              </p>
            </div>

            <Button
              onClick={startQuiz}
              className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white py-6 text-lg"
            >
              <Brain className="mr-2 h-5 w-5" />
              Start Quiz Now
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <GraduationCap className="h-10 w-10 text-indigo-600" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-2">Campus Placement Drive</h1>
          <p className="text-gray-600 text-lg">Register and take the assessment to qualify</p>
        </div>

        {/* Drive Info Card */}
        {selectedDrive && (
          <Card className="mb-8 shadow-lg border-0 overflow-hidden">
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-6">
              <h2 className="text-2xl font-bold mb-2">{selectedDrive.name}</h2>
              {selectedDrive.company_name && (
                <p className="text-indigo-100">Organized by {selectedDrive.company_name}</p>
              )}
            </div>
            <CardContent className="p-6">
              {selectedDrive.description && (
                <p className="text-gray-600 mb-6">{selectedDrive.description}</p>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <Brain className="h-8 w-8 text-blue-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Logical</p>
                  <p className="text-xl font-bold text-blue-600">{selectedDrive.logical_questions} Q</p>
                </div>
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <Code className="h-8 w-8 text-green-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">Technical</p>
                  <p className="text-xl font-bold text-green-600">{selectedDrive.technical_questions} Q</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-4 text-center">
                  <BookOpen className="h-8 w-8 text-purple-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">AI/ML</p>
                  <p className="text-xl font-bold text-purple-600">{selectedDrive.ai_ml_questions} Q</p>
                </div>
                <div className="bg-orange-50 rounded-lg p-4 text-center">
                  <MessageSquare className="h-8 w-8 text-orange-600 mx-auto mb-2" />
                  <p className="text-sm text-gray-600">English</p>
                  <p className="text-xl font-bold text-orange-600">{selectedDrive.english_questions} Q</p>
                </div>
              </div>

              <div className="flex items-center justify-center gap-6 mt-6 text-gray-600">
                <div className="flex items-center gap-2">
                  <Clock className="h-5 w-5" />
                  <span>{selectedDrive.quiz_duration_minutes} minutes</span>
                </div>
                <div className="flex items-center gap-2">
                  <Trophy className="h-5 w-5" />
                  <span>Pass: {selectedDrive.passing_percentage}%</span>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Registration Form */}
        <Card className="shadow-xl border-0">
          <CardHeader className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-t-lg">
            <CardTitle className="text-xl flex items-center gap-2">
              <Users className="h-5 w-5" />
              Student Registration
            </CardTitle>
            <CardDescription className="text-blue-100">
              Fill in your details to register for the placement drive
            </CardDescription>
          </CardHeader>

          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {submitStatus === 'error' && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{errorMessage}</AlertDescription>
                </Alert>
              )}

              {/* Personal Information */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <User className="h-5 w-5 text-indigo-600" />
                  Personal Information
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name *</Label>
                    <Input
                      id="full_name"
                      placeholder="Enter your full name"
                      value={formData.full_name}
                      onChange={(e) => handleInputChange('full_name', e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email">Email Address *</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                      <Input
                        id="email"
                        type="email"
                        placeholder="your.email@example.com"
                        className="pl-10"
                        value={formData.email}
                        onChange={(e) => handleInputChange('email', e.target.value)}
                        required
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number *</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
                    <Input
                      id="phone"
                      type="tel"
                      placeholder="9876543210"
                      className="pl-10"
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
              <div className="space-y-4 pt-4 border-t">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <Building2 className="h-5 w-5 text-indigo-600" />
                  Academic Information
                </h3>

                <div className="space-y-2">
                  <Label htmlFor="college_name">College/University Name *</Label>
                  <Input
                    id="college_name"
                    placeholder="Enter your college name"
                    value={formData.college_name}
                    onChange={(e) => handleInputChange('college_name', e.target.value)}
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="department">Department *</Label>
                    <Select
                      value={formData.department}
                      onValueChange={(value) => handleInputChange('department', value)}
                      required
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select department" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="CSE">Computer Science & Engineering</SelectItem>
                        <SelectItem value="IT">Information Technology</SelectItem>
                        <SelectItem value="ECE">Electronics & Communication</SelectItem>
                        <SelectItem value="EEE">Electrical & Electronics</SelectItem>
                        <SelectItem value="MECH">Mechanical Engineering</SelectItem>
                        <SelectItem value="CIVIL">Civil Engineering</SelectItem>
                        <SelectItem value="AIDS">AI & Data Science</SelectItem>
                        <SelectItem value="OTHER">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="year_of_study">Year of Study *</Label>
                    <Select
                      value={formData.year_of_study}
                      onValueChange={(value) => handleInputChange('year_of_study', value)}
                      required
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select year" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1st Year">1st Year</SelectItem>
                        <SelectItem value="2nd Year">2nd Year</SelectItem>
                        <SelectItem value="3rd Year">3rd Year</SelectItem>
                        <SelectItem value="4th Year">4th Year</SelectItem>
                        <SelectItem value="PG 1st Year">PG 1st Year</SelectItem>
                        <SelectItem value="PG 2nd Year">PG 2nd Year</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="roll_number">Roll Number</Label>
                    <Input
                      id="roll_number"
                      placeholder="Enter your roll number"
                      value={formData.roll_number}
                      onChange={(e) => handleInputChange('roll_number', e.target.value)}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="cgpa">CGPA (Optional)</Label>
                    <Input
                      id="cgpa"
                      type="number"
                      step="0.01"
                      min="0"
                      max="10"
                      placeholder="e.g., 8.5"
                      value={formData.cgpa}
                      onChange={(e) => handleInputChange('cgpa', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-4">
                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white py-6 text-lg"
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
                      <GraduationCap className="mr-2 h-5 w-5" />
                      Register & Continue to Quiz
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <p className="text-center text-gray-500 text-sm mt-6">
          By registering, you agree to our terms and conditions.
        </p>
      </div>
    </div>
  )
}
