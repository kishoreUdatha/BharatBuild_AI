'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { GraduationCap, User, Mail, Phone, Building2, BookOpen, CheckCircle2, AlertCircle } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function StudentFormPage() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    phone: '',
    college_name: '',
    department: '',
    year_of_study: '',
    roll_number: '',
    workshop_name: 'AI & Machine Learning Workshop',
    previous_experience: '',
    expectations: '',
    how_did_you_hear: ''
  })

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitStatus, setSubmitStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setSubmitStatus('idle')
    setErrorMessage('')

    try {
      const response = await fetch(`${API_URL}/workshop/enroll`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Registration failed')
      }

      setSubmitStatus('success')
      // Reset form
      setFormData({
        full_name: '',
        email: '',
        phone: '',
        college_name: '',
        department: '',
        year_of_study: '',
        roll_number: '',
        workshop_name: 'AI & Machine Learning Workshop',
        previous_experience: '',
        expectations: '',
        how_did_you_hear: ''
      })
    } catch (error) {
      setSubmitStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Something went wrong')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitStatus === 'success') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-10 pb-10">
            <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="h-10 w-10 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Registration Successful!</h2>
            <p className="text-gray-600 mb-6">
              Thank you for registering for the workshop. We&apos;ll send you a confirmation email shortly.
            </p>
            <Button onClick={() => setSubmitStatus('idle')} variant="outline">
              Register Another Student
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <GraduationCap className="h-8 w-8 text-indigo-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Workshop Registration</h1>
          <p className="text-gray-600">Fill in your details to register for the workshop</p>
        </div>

        <Card className="shadow-xl border-0">
          <CardHeader className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-t-lg">
            <CardTitle className="text-xl">Student Enrollment Form</CardTitle>
            <CardDescription className="text-indigo-100">
              AI & Machine Learning Workshop - BharatBuild
            </CardDescription>
          </CardHeader>

          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Error Alert */}
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
                      placeholder="+91 9876543210"
                      className="pl-10"
                      value={formData.phone}
                      onChange={(e) => handleInputChange('phone', e.target.value)}
                      required
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

                <div className="space-y-2">
                  <Label htmlFor="roll_number">Roll Number (Optional)</Label>
                  <Input
                    id="roll_number"
                    placeholder="Enter your roll number"
                    value={formData.roll_number}
                    onChange={(e) => handleInputChange('roll_number', e.target.value)}
                  />
                </div>
              </div>

              {/* Additional Information */}
              <div className="space-y-4 pt-4 border-t">
                <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
                  <BookOpen className="h-5 w-5 text-indigo-600" />
                  Additional Information
                </h3>

                <div className="space-y-2">
                  <Label htmlFor="previous_experience">Previous Experience with AI/ML (Optional)</Label>
                  <Textarea
                    id="previous_experience"
                    placeholder="Describe any prior experience with AI, Machine Learning, or programming..."
                    rows={3}
                    value={formData.previous_experience}
                    onChange={(e) => handleInputChange('previous_experience', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="expectations">What do you expect to learn? (Optional)</Label>
                  <Textarea
                    id="expectations"
                    placeholder="Share your expectations from this workshop..."
                    rows={3}
                    value={formData.expectations}
                    onChange={(e) => handleInputChange('expectations', e.target.value)}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="how_did_you_hear">How did you hear about us?</Label>
                  <Select
                    value={formData.how_did_you_hear}
                    onValueChange={(value) => handleInputChange('how_did_you_hear', value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select an option" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="College Notice">College Notice</SelectItem>
                      <SelectItem value="Social Media">Social Media</SelectItem>
                      <SelectItem value="Friend/Colleague">Friend/Colleague</SelectItem>
                      <SelectItem value="Website">Website</SelectItem>
                      <SelectItem value="Other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-4">
                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white py-6 text-lg"
                  disabled={isSubmitting}
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
                      Register for Workshop
                    </>
                  )}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-gray-500 text-sm mt-6">
          By registering, you agree to our terms and conditions.
        </p>
      </div>
    </div>
  )
}
