'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, User, GraduationCap, Building, BookOpen } from 'lucide-react'

export default function CompleteProfilePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [checking, setChecking] = useState(true)
  const [error, setError] = useState('')
  const [user, setUser] = useState<any>(null)

  // Form state
  const [formData, setFormData] = useState({
    full_name: '',
    phone: '',
    role: 'student',
    roll_number: '',
    college_name: '',
    university_name: '',
    department: '',
    course: '',
    year_semester: '',
    batch: '',
    guide_name: '',
    guide_designation: '',
    hod_name: ''
  })

  useEffect(() => {
    checkProfileStatus()
  }, [])

  const checkProfileStatus = async () => {
    try {
      const token = localStorage.getItem('access_token')
      if (!token) {
        router.push('/login')
        return
      }

      // Get current user
      const userData = await apiClient.getMe()
      setUser(userData)

      // Pre-fill form with existing data
      setFormData(prev => ({
        ...prev,
        full_name: userData.full_name || '',
        phone: userData.phone || '',
        role: userData.role || 'student',
        roll_number: userData.roll_number || '',
        college_name: userData.college_name || '',
        university_name: userData.university_name || '',
        department: userData.department || '',
        course: userData.course || '',
        year_semester: userData.year_semester || '',
        batch: userData.batch || '',
        guide_name: userData.guide_name || '',
        guide_designation: userData.guide_designation || '',
        hod_name: userData.hod_name || ''
      }))

      // Check if profile is already complete
      const status = await apiClient.get('/auth/me/profile-status')
      if (status.profile_complete) {
        router.push('/build')
        return
      }
    } catch (err) {
      console.error('Error checking profile:', err)
    } finally {
      setChecking(false)
    }
  }

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // Update profile
      const response = await apiClient.patch('/auth/me/profile', formData)

      // Store updated user info
      localStorage.setItem('user', JSON.stringify(response))

      // Redirect to build page
      router.push('/build?welcome=true')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update profile. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (checking) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 py-8 px-4">
      <div className="max-w-2xl mx-auto">
        <Card>
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <div className="h-16 w-16 bg-blue-100 rounded-full flex items-center justify-center">
                <GraduationCap className="h-8 w-8 text-blue-600" />
              </div>
            </div>
            <CardTitle className="text-2xl font-bold">Complete Your Profile</CardTitle>
            <CardDescription>
              Welcome{user?.full_name ? `, ${user.full_name}` : ''}! Please fill in your details to continue.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Basic Info */}
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                  <User className="h-4 w-4" />
                  Basic Information
                </div>

                {/* Email from OAuth - Read Only */}
                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    value={user?.email || ''}
                    disabled
                    className="bg-gray-50 text-gray-600"
                  />
                  <p className="text-xs text-gray-500">Email is from your {user?.oauth_provider || 'OAuth'} account and cannot be changed.</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name *</Label>
                    <Input
                      id="full_name"
                      value={formData.full_name}
                      onChange={(e) => handleChange('full_name', e.target.value)}
                      placeholder="Enter your full name"
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="phone">Phone Number</Label>
                    <Input
                      id="phone"
                      value={formData.phone}
                      onChange={(e) => handleChange('phone', e.target.value)}
                      placeholder="+91 9876543210"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="role">I am a *</Label>
                  <Select value={formData.role} onValueChange={(value) => handleChange('role', value)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select your role" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="student">Student</SelectItem>
                      <SelectItem value="developer">Developer</SelectItem>
                      <SelectItem value="founder">Founder / Entrepreneur</SelectItem>
                      <SelectItem value="faculty">Faculty / Professor</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Academic Details (show only for students) */}
              {formData.role === 'student' && (
                <>
                  <hr className="my-4" />
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                      <Building className="h-4 w-4" />
                      College Information
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="roll_number">Roll Number *</Label>
                        <Input
                          id="roll_number"
                          value={formData.roll_number}
                          onChange={(e) => handleChange('roll_number', e.target.value)}
                          placeholder="e.g., 21CS101"
                          required={formData.role === 'student'}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="batch">Batch</Label>
                        <Input
                          id="batch"
                          value={formData.batch}
                          onChange={(e) => handleChange('batch', e.target.value)}
                          placeholder="e.g., 2021-2025"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="college_name">College Name *</Label>
                      <Input
                        id="college_name"
                        value={formData.college_name}
                        onChange={(e) => handleChange('college_name', e.target.value)}
                        placeholder="e.g., ABC Engineering College"
                        required={formData.role === 'student'}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="university_name">University Name</Label>
                      <Input
                        id="university_name"
                        value={formData.university_name}
                        onChange={(e) => handleChange('university_name', e.target.value)}
                        placeholder="e.g., JNTU Hyderabad"
                      />
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="department">Department *</Label>
                        <Input
                          id="department"
                          value={formData.department}
                          onChange={(e) => handleChange('department', e.target.value)}
                          placeholder="e.g., Computer Science"
                          required={formData.role === 'student'}
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="course">Course</Label>
                        <Input
                          id="course"
                          value={formData.course}
                          onChange={(e) => handleChange('course', e.target.value)}
                          placeholder="e.g., B.Tech, MCA"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="year_semester">Year / Semester</Label>
                      <Input
                        id="year_semester"
                        value={formData.year_semester}
                        onChange={(e) => handleChange('year_semester', e.target.value)}
                        placeholder="e.g., 4th Year / 8th Semester"
                      />
                    </div>
                  </div>

                  <hr className="my-4" />
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
                      <BookOpen className="h-4 w-4" />
                      Guide / Mentor Details (Optional)
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="guide_name">Guide Name</Label>
                        <Input
                          id="guide_name"
                          value={formData.guide_name}
                          onChange={(e) => handleChange('guide_name', e.target.value)}
                          placeholder="e.g., Dr. Smith"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="guide_designation">Guide Designation</Label>
                        <Input
                          id="guide_designation"
                          value={formData.guide_designation}
                          onChange={(e) => handleChange('guide_designation', e.target.value)}
                          placeholder="e.g., Assistant Professor"
                        />
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="hod_name">HOD Name</Label>
                      <Input
                        id="hod_name"
                        value={formData.hod_name}
                        onChange={(e) => handleChange('hod_name', e.target.value)}
                        placeholder="e.g., Dr. Johnson"
                      />
                    </div>
                  </div>
                </>
              )}

              {error && (
                <Alert variant="destructive">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                    Saving...
                  </>
                ) : (
                  'Complete Profile & Continue'
                )}
              </Button>

              <p className="text-xs text-center text-gray-500">
                This information will be used in your generated project documents.
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
