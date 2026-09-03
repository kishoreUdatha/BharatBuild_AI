'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertCircle, GraduationCap, Loader2, Lock, Mail } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { removeAccessToken, setAccessToken } from '@/lib/auth-utils'

export default function TrainerLoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [next, setNext] = useState('/trainer')

  // The layout sends an expired session here as ?next=<the page they wanted>,
  // so signing back in returns them to it rather than the portal home.
  useEffect(() => {
    const raw = new URLSearchParams(window.location.search).get('next')
    // Only same-portal paths: an open redirect here would hand a session to
    // whatever host an attacker put in the query string.
    if (raw && raw.startsWith('/trainer')) setNext(raw)
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await apiClient.login(email, password)
      const role = response.user?.role?.toLowerCase()

      // Trainer is its own role now, so this door only opens for one. Every
      // /trainer route would answer 403 anyway; refusing here means the
      // wrong account gets a sentence instead of an empty, broken portal.
      if (role !== 'trainer') {
        removeAccessToken()
        setError(
          role === 'faculty'
            ? 'This is a faculty account. Faculty sign in at the main login.'
            : 'This account is not a trainer account.'
        )
        return
      }

      setAccessToken(response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)
      if (response.user) localStorage.setItem('user', JSON.stringify(response.user))

      router.replace(next)
    } catch (err: any) {
      // 429 is the login rate limit, which otherwise reads as a wrong password.
      setError(
        err?.response?.status === 429
          ? 'Too many attempts. Wait a minute and try again.'
          : err?.response?.data?.detail || 'Sign in failed. Check your email and password.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#F5F7FB] px-4 text-[#1B1B3A]">
      <div className="w-full max-w-[380px]">
        <div className="mb-5 flex flex-col items-center text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#0B1B4D] text-white">
            <GraduationCap className="h-6 w-6" />
          </span>
          <h1 className="mt-3 text-[19px] font-bold">Trainer Portal</h1>
          <p className="mt-1 text-[12.5px] text-[#6B7280]">
            Sign in to review AI-drafted stories and your batches.
          </p>
        </div>

        <form onSubmit={handleSubmit}
          className="rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-sm">
          {error && (
            <div className="mb-4 flex items-start gap-2 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2">
              <AlertCircle className="mt-[1px] h-4 w-4 shrink-0 text-[#DC2626]" />
              <p className="text-[12px] leading-snug text-[#DC2626]">{error}</p>
            </div>
          )}

          <label htmlFor="email" className="block text-[12px] font-medium text-[#3A3F58]">
            Email
          </label>
          <div className="relative mt-1.5 mb-4">
            <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9CA3AF]" />
            <input id="email" type="email" required autoComplete="email"
              value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="trainer@college.edu"
              className="w-full rounded-lg border border-[#DBE3F5] py-2 pl-9 pr-3 text-[13px] outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]" />
          </div>

          <label htmlFor="password" className="block text-[12px] font-medium text-[#3A3F58]">
            Password
          </label>
          <div className="relative mt-1.5 mb-5">
            <Lock className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#9CA3AF]" />
            <input id="password" type="password" required autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border border-[#DBE3F5] py-2 pl-9 pr-3 text-[13px] outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]" />
          </div>

          <button type="submit" disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#2563EB] py-2.5 text-[13px] font-medium text-white transition-colors hover:bg-[#1D4ED8] disabled:cursor-not-allowed disabled:opacity-60">
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-4 text-center text-[11.5px] text-[#6B7280]">
          Faculty, student or admin?{' '}
          <Link href="/login" className="font-medium text-[#2563EB] hover:underline">
            Use the main login
          </Link>
        </p>
      </div>
    </div>
  )
}
