'use client'

import { useState, Suspense } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Zap, ArrowLeft, Mail, Loader2, CheckCircle, AlertCircle } from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

function ForgotPasswordContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const resetToken = searchParams.get('token')

  const [email, setEmail] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      const response = await fetch(`${API_URL}/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email })
      })

      const data = await response.json()

      if (data.success) {
        setSuccess(true)
        setMessage(data.message)
      } else {
        setError(data.message)
      }
    } catch (err) {
      setError('Failed to connect to server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      setLoading(false)
      return
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters')
      setLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_URL}/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          token: resetToken,
          new_password: newPassword
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSuccess(true)
        setMessage(data.message)
        // Redirect to login after 3 seconds
        setTimeout(() => {
          router.push('/login')
        }, 3000)
      } else {
        setError(data.detail || data.message || 'Failed to reset password')
      }
    } catch (err) {
      setError('Failed to connect to server. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // Show reset password form if token is present
  if (resetToken) {
    return (
      <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex flex-col">
        {/* Header */}
        <header className="border-b border-[hsl(var(--bolt-border))]">
          <div className="container mx-auto px-6 py-4">
            <Link href="/" className="flex items-center gap-2 w-fit">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-xl text-[hsl(var(--bolt-text-primary))]">BharatBuild</span>
            </Link>
          </div>
        </header>

        {/* Reset Password Form */}
        <main className="flex-1 flex items-center justify-center p-6">
          <div className="w-full max-w-md">
            <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8">
              <h1 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">
                Set New Password
              </h1>
              <p className="text-[hsl(var(--bolt-text-secondary))] mb-6">
                Enter your new password below.
              </p>

              {success ? (
                <div className="text-center py-8">
                  <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                  <h2 className="text-xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                    Password Reset Successful!
                  </h2>
                  <p className="text-[hsl(var(--bolt-text-secondary))] mb-4">
                    {message}
                  </p>
                  <p className="text-sm text-[hsl(var(--bolt-text-tertiary))]">
                    Redirecting to login...
                  </p>
                </div>
              ) : (
                <form onSubmit={handleResetPassword} className="space-y-4">
                  <div>
                    <Label htmlFor="new-password" className="text-[hsl(var(--bolt-text-secondary))]">
                      New Password
                    </Label>
                    <Input
                      id="new-password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                      required
                      minLength={8}
                      className="mt-1 bg-[hsl(var(--bolt-bg-tertiary))] border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))]"
                    />
                  </div>

                  <div>
                    <Label htmlFor="confirm-password" className="text-[hsl(var(--bolt-text-secondary))]">
                      Confirm Password
                    </Label>
                    <Input
                      id="confirm-password"
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm new password"
                      required
                      minLength={8}
                      className="mt-1 bg-[hsl(var(--bolt-bg-tertiary))] border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))]"
                    />
                  </div>

                  {error && (
                    <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 p-3 rounded-lg">
                      <AlertCircle className="w-4 h-4 flex-shrink-0" />
                      {error}
                    </div>
                  )}

                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bolt-gradient hover:opacity-90"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                        Resetting...
                      </>
                    ) : (
                      'Reset Password'
                    )}
                  </Button>
                </form>
              )}
            </div>
          </div>
        </main>
      </div>
    )
  }

  // Show forgot password form (request reset)
  return (
    <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex flex-col">
      {/* Header */}
      <header className="border-b border-[hsl(var(--bolt-border))]">
        <div className="container mx-auto px-6 py-4">
          <Link href="/" className="flex items-center gap-2 w-fit">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-[hsl(var(--bolt-text-primary))]">BharatBuild</span>
          </Link>
        </div>
      </header>

      {/* Forgot Password Form */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="bg-[hsl(var(--bolt-bg-secondary))] border border-[hsl(var(--bolt-border))] rounded-2xl p-8">
            <Link href="/login" className="inline-flex items-center text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))] mb-6">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Login
            </Link>

            <h1 className="text-2xl font-bold text-[hsl(var(--bolt-text-primary))] mb-2">
              Forgot Password?
            </h1>
            <p className="text-[hsl(var(--bolt-text-secondary))] mb-6">
              Enter your email address and we'll send you a link to reset your password.
            </p>

            {success ? (
              <div className="text-center py-4">
                <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-4">
                  <Mail className="w-8 h-8 text-green-500" />
                </div>
                <h2 className="text-xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                  Check Your Email
                </h2>
                <p className="text-[hsl(var(--bolt-text-secondary))] text-sm mb-4">
                  {message}
                </p>
                <p className="text-[hsl(var(--bolt-text-tertiary))] text-xs">
                  Didn't receive the email? Check your spam folder or try again.
                </p>
                <Button
                  variant="outline"
                  className="mt-4 border-[hsl(var(--bolt-border))]"
                  onClick={() => {
                    setSuccess(false)
                    setMessage(null)
                  }}
                >
                  Try Again
                </Button>
              </div>
            ) : (
              <form onSubmit={handleForgotPassword} className="space-y-4">
                <div>
                  <Label htmlFor="email" className="text-[hsl(var(--bolt-text-secondary))]">
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com"
                    required
                    className="mt-1 bg-[hsl(var(--bolt-bg-tertiary))] border-[hsl(var(--bolt-border))] text-[hsl(var(--bolt-text-primary))]"
                  />
                </div>

                {error && (
                  <div className="flex items-center gap-2 text-red-400 text-sm bg-red-900/20 p-3 rounded-lg">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    {error}
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={loading}
                  className="w-full bolt-gradient hover:opacity-90"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    'Send Reset Link'
                  )}
                </Button>
              </form>
            )}

            <div className="mt-6 text-center text-sm text-[hsl(var(--bolt-text-secondary))]">
              Remember your password?{' '}
              <Link href="/login" className="text-[hsl(var(--bolt-accent))] hover:underline">
                Sign in
              </Link>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default function ForgotPasswordPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-[hsl(var(--bolt-bg-primary))] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[hsl(var(--bolt-accent))]" />
      </div>
    }>
      <ForgotPasswordContent />
    </Suspense>
  )
}
