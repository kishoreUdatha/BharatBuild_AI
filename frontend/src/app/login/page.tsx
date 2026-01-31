'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api-client'
import { setAccessToken } from '@/lib/auth-utils'
import {
  Zap,
  GraduationCap,
  BookOpen,
  Shield,
  User,
  Eye,
  EyeOff,
  Loader2,
  ArrowLeft,
  Check
} from 'lucide-react'

type Role = 'student' | 'faculty' | 'admin' | 'user'

const roles = [
  {
    id: 'student' as Role,
    label: 'Student',
    description: 'Lab practice, coding & placement prep',
    icon: GraduationCap,
    color: 'from-green-500 to-emerald-600',
    borderColor: 'border-green-500',
    bgColor: 'bg-green-500/10',
    redirect: '/lab'
  },
  {
    id: 'faculty' as Role,
    label: 'Faculty',
    description: 'Assignments, grading & analytics',
    icon: BookOpen,
    color: 'from-blue-500 to-indigo-600',
    borderColor: 'border-blue-500',
    bgColor: 'bg-blue-500/10',
    redirect: '/faculty'
  },
  {
    id: 'admin' as Role,
    label: 'Admin',
    description: 'Platform management & reports',
    icon: Shield,
    color: 'from-purple-500 to-pink-600',
    borderColor: 'border-purple-500',
    bgColor: 'bg-purple-500/10',
    redirect: '/admin'
  },
  {
    id: 'user' as Role,
    label: 'Builder',
    description: 'Build apps with AI',
    icon: User,
    color: 'from-orange-500 to-red-500',
    borderColor: 'border-orange-500',
    bgColor: 'bg-orange-500/10',
    redirect: '/build'
  }
]

export default function LoginPage() {
  const router = useRouter()
  const [selectedRole, setSelectedRole] = useState<Role>('user')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const selectedRoleData = roles.find(r => r.id === selectedRole)!

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      // Try API login first
      let loginSuccess = false
      try {
        const response = await apiClient.login(email, password)
        if (response.access_token) {
          setAccessToken(response.access_token)
          localStorage.setItem('refresh_token', response.refresh_token)
          if (response.user) {
            localStorage.setItem('user', JSON.stringify(response.user))
            // Use role from API response if available
            localStorage.setItem('userRole', response.user.role || selectedRole)
          }
          loginSuccess = true
        }
      } catch (apiError: any) {
        // If API fails, check if it's auth error or connection error
        console.log('API login failed:', apiError.message)
        if (apiError.response?.status === 401 || apiError.response?.status === 400) {
          setError('Invalid email or password')
          setLoading(false)
          return
        }
        // Connection error - use demo mode
        console.log('Using demo mode due to connection error')
      }

      // Store role info
      if (!localStorage.getItem('userRole')) {
        localStorage.setItem('userRole', selectedRole)
      }
      localStorage.setItem('userEmail', email)
      localStorage.setItem('userName', email.split('@')[0])

      // Small delay to ensure localStorage is persisted before navigation
      await new Promise(resolve => setTimeout(resolve, 100))

      // Redirect based on role - use replace to prevent back button to login
      window.location.href = selectedRoleData.redirect
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const fillDemoCredentials = () => {
    const demoCredentials: Record<Role, { email: string; password: string }> = {
      student: { email: 'rahul@college.edu', password: 'student123' },
      faculty: { email: 'faculty@bharatbuild.com', password: 'faculty123' },
      admin: { email: 'admin@bharatbuild.ai', password: 'admin123' },
      user: { email: 'user@example.com', password: 'demo123' }
    }
    setEmail(demoCredentials[selectedRole].email)
    setPassword(demoCredentials[selectedRole].password)
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Back Link */}
        <Link href="/" className="inline-flex items-center gap-2 text-gray-400 hover:text-white mb-6 transition">
          <ArrowLeft className="w-4 h-4" />
          Back to Home
        </Link>

        {/* Login Card */}
        <div className="bg-gray-900 rounded-2xl border border-gray-800 overflow-hidden">
          {/* Header */}
          <div className="p-6 border-b border-gray-800 text-center">
            <Link href="/" className="inline-flex items-center gap-2 mb-4">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Zap className="w-6 h-6 text-white" />
              </div>
              <span className="font-bold text-xl text-white">BharatBuild</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-gradient-to-r from-orange-500 to-green-500 text-white font-medium">AI</span>
            </Link>
            <h1 className="text-2xl font-bold text-white">Welcome Back</h1>
            <p className="text-gray-400 mt-1">Select your role and sign in</p>
          </div>

          {/* Role Selection */}
          <div className="p-6 border-b border-gray-800">
            <label className="block text-sm text-gray-400 mb-3">I am a:</label>
            <div className="grid grid-cols-2 gap-3">
              {roles.map((role) => (
                <button
                  key={role.id}
                  type="button"
                  onClick={() => setSelectedRole(role.id)}
                  className={`relative p-4 rounded-xl border-2 transition-all text-left ${
                    selectedRole === role.id
                      ? `${role.borderColor} ${role.bgColor}`
                      : 'border-gray-700 hover:border-gray-600'
                  }`}
                >
                  {selectedRole === role.id && (
                    <div className={`absolute top-2 right-2 w-5 h-5 rounded-full bg-gradient-to-br ${role.color} flex items-center justify-center`}>
                      <Check className="w-3 h-3 text-white" />
                    </div>
                  )}
                  <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${role.color} flex items-center justify-center mb-2`}>
                    <role.icon className="w-5 h-5 text-white" />
                  </div>
                  <div className="font-semibold text-white">{role.label}</div>
                  <div className="text-xs text-gray-400 mt-0.5">{role.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {/* Error Message */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-sm text-gray-400 mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={`Enter your ${selectedRole} email`}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500 transition"
                required
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500 transition pr-12"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 text-gray-400 cursor-pointer">
                <input type="checkbox" className="rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500" />
                Remember me
              </label>
              <Link href="/forgot-password" className="text-blue-400 hover:underline">
                Forgot password?
              </Link>
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-3 bg-gradient-to-r ${selectedRoleData.color} text-white font-semibold rounded-xl hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-2`}
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Signing in...
                </>
              ) : (
                `Sign In as ${selectedRoleData.label}`
              )}
            </button>

            {/* Demo Account */}
            <button
              type="button"
              onClick={fillDemoCredentials}
              className="w-full py-3 bg-gray-800 text-gray-300 font-medium rounded-xl hover:bg-gray-700 transition border border-gray-700"
            >
              Use Demo Account
            </button>
          </form>

          {/* Footer */}
          <div className="p-6 border-t border-gray-800 text-center">
            <p className="text-gray-500 text-sm">
              Don't have an account?{' '}
              <Link href="/register" className="text-blue-400 hover:underline">
                Sign up for free
              </Link>
            </p>
          </div>
        </div>

        {/* Powered By */}
        <div className="text-center mt-6">
          <span className="text-gray-600 text-sm">Powered by BharatBuild AI</span>
        </div>
      </div>
    </div>
  )
}
