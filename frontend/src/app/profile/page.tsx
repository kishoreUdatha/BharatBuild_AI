'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  User,
  Mail,
  Building2,
  Shield,
  Calendar,
  Clock,
  Save,
  ArrowLeft,
  CheckCircle,
  AlertCircle,
  Loader2,
  Zap
} from 'lucide-react'

interface UserProfile {
  id: string
  email: string
  full_name: string | null
  username: string | null
  role: string
  organization: string | null
  is_active: boolean
  is_verified: boolean
  avatar_url: string | null
  oauth_provider: string | null
  created_at: string
  last_login: string | null
}

export default function ProfilePage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading, checkAuth } = useAuth()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Form state
  const [fullName, setFullName] = useState('')
  const [organization, setOrganization] = useState('')

  // Check auth and load profile
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login?redirect=/profile')
      return
    }

    if (user?.id) {
      loadProfile()
    }
  }, [authLoading, isAuthenticated, user, router])

  const loadProfile = async () => {
    try {
      setLoading(true)
      const data = await apiClient.get(`/users/${user?.id}`)
      setProfile(data)
      setFullName(data.full_name || '')
      setOrganization(data.organization || '')
    } catch (err: any) {
      setError('Failed to load profile')
      console.error('Profile load error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!user?.id) return

    setSaving(true)
    setError('')
    setSuccess('')

    try {
      const updated = await apiClient.patch(`/users/${user.id}`, {
        full_name: fullName || null,
        organization: organization || null
      })

      setProfile(updated)
      setSuccess('Profile updated successfully!')

      // Update local storage user info
      const storedUser = localStorage.getItem('user')
      if (storedUser) {
        const userInfo = JSON.parse(storedUser)
        userInfo.full_name = fullName
        localStorage.setItem('user', JSON.stringify(userInfo))
      }

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(''), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never'
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'developer': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'founder': return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      case 'faculty': return 'bg-green-500/20 text-green-400 border-green-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f]">
      {/* Header */}
      <header className="border-b border-[#1a1a2e]">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-xl text-white">BharatBuild</span>
            </Link>
          </div>
          <Link href="/build">
            <Button variant="outline" className="border-[#333] text-gray-300 hover:bg-[#1a1a2e]">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Build
            </Button>
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-12 max-w-2xl">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Profile Settings</h1>
          <p className="text-gray-400">Manage your account information</p>
        </div>

        {/* Success Message */}
        {success && (
          <div className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/30 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-green-400" />
            <span className="text-green-400">{success}</span>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
          </div>
        )}

        {/* Profile Card */}
        <div className="bg-[#12121a] rounded-xl border border-[#1a1a2e] overflow-hidden">
          {/* Avatar Section */}
          <div className="bg-gradient-to-r from-blue-500/10 to-cyan-500/10 p-6 border-b border-[#1a1a2e]">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white text-2xl font-bold">
                {fullName ? fullName.charAt(0).toUpperCase() : profile?.email?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">
                  {fullName || profile?.email?.split('@')[0] || 'User'}
                </h2>
                <p className="text-gray-400">{profile?.email}</p>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`px-2 py-0.5 text-xs font-medium rounded-full border ${getRoleBadgeColor(profile?.role || 'student')}`}>
                    {profile?.role?.replace('_', ' ').toUpperCase() || 'STUDENT'}
                  </span>
                  {profile?.is_verified && (
                    <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                      Verified
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Edit Form */}
          <div className="p-6 space-y-6">
            {/* Full Name */}
            <div className="space-y-2">
              <Label htmlFor="fullName" className="text-gray-300 flex items-center gap-2">
                <User className="w-4 h-4" />
                Full Name
              </Label>
              <Input
                id="fullName"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Enter your full name"
                className="bg-[#0a0a0f] border-[#333] text-white placeholder:text-gray-500 focus:border-blue-500"
              />
            </div>

            {/* Email (Read-only) */}
            <div className="space-y-2">
              <Label htmlFor="email" className="text-gray-300 flex items-center gap-2">
                <Mail className="w-4 h-4" />
                Email Address
              </Label>
              <Input
                id="email"
                value={profile?.email || ''}
                disabled
                className="bg-[#0a0a0f] border-[#333] text-gray-500 cursor-not-allowed"
              />
              <p className="text-xs text-gray-500">Email cannot be changed</p>
            </div>

            {/* Organization */}
            <div className="space-y-2">
              <Label htmlFor="organization" className="text-gray-300 flex items-center gap-2">
                <Building2 className="w-4 h-4" />
                Organization / College
              </Label>
              <Input
                id="organization"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder="Enter your organization or college name"
                className="bg-[#0a0a0f] border-[#333] text-white placeholder:text-gray-500 focus:border-blue-500"
              />
            </div>

            {/* Account Info */}
            <div className="pt-4 border-t border-[#1a1a2e] space-y-3">
              <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Account Information</h3>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="flex items-center gap-2 text-gray-400">
                  <Shield className="w-4 h-4" />
                  <span>Role:</span>
                  <span className="text-white">{profile?.role?.replace('_', ' ') || 'Student'}</span>
                </div>

                <div className="flex items-center gap-2 text-gray-400">
                  <Calendar className="w-4 h-4" />
                  <span>Joined:</span>
                  <span className="text-white">{formatDate(profile?.created_at || null)}</span>
                </div>

                <div className="flex items-center gap-2 text-gray-400">
                  <Clock className="w-4 h-4" />
                  <span>Last Login:</span>
                  <span className="text-white">{formatDate(profile?.last_login || null)}</span>
                </div>

                {profile?.oauth_provider && (
                  <div className="flex items-center gap-2 text-gray-400">
                    <span>Signed in via:</span>
                    <span className="text-white capitalize">{profile.oauth_provider}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Save Button */}
            <div className="pt-4">
              <Button
                onClick={handleSave}
                disabled={saving}
                className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
