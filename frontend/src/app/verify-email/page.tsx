'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import { CheckCircle, XCircle, Loader2, Mail, Zap } from 'lucide-react'

function VerifyEmailContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const verifyEmail = async () => {
      if (!token) {
        setStatus('error')
        setMessage('Invalid verification link. No token provided.')
        return
      }

      try {
        const response = await apiClient.post('/auth/verify-email', { token })
        setStatus('success')
        setMessage(response.data?.message || 'Your email has been verified successfully!')
      } catch (err: any) {
        setStatus('error')
        setMessage(err.response?.data?.detail || 'Failed to verify email. The link may have expired.')
      }
    }

    verifyEmail()
  }, [token])

  return (
    <div className="bg-[#111118]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-8 shadow-2xl text-center">
      {status === 'loading' && (
        <>
          <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Verifying Email</h2>
          <p className="text-gray-400 text-sm">Please wait while we verify your email address...</p>
        </>
      )}

      {status === 'success' && (
        <>
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="h-8 w-8 text-green-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Email Verified!</h2>
          <p className="text-gray-400 text-sm mb-6">{message}</p>
          <div className="space-y-3">
            <Button
              onClick={() => router.push('/login')}
              className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white"
            >
              Continue to Login
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push('/build')}
              className="w-full border-white/10 text-gray-300 hover:bg-white/5 hover:text-white"
            >
              Go to Dashboard
            </Button>
          </div>
        </>
      )}

      {status === 'error' && (
        <>
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="h-8 w-8 text-red-400" />
          </div>
          <h2 className="text-xl font-bold text-white mb-2">Verification Failed</h2>
          <p className="text-gray-400 text-sm mb-6">{message}</p>
          <div className="space-y-3">
            <Button
              onClick={() => router.push('/login')}
              className="w-full bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-white"
            >
              Go to Login
            </Button>
            <p className="text-xs text-gray-500">
              Need a new verification link?{' '}
              <Link href="/login" className="text-cyan-400 hover:text-cyan-300">
                Login and request one
              </Link>
            </p>
          </div>
        </>
      )}
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="bg-[#111118]/80 backdrop-blur-xl rounded-2xl border border-white/10 p-8 shadow-2xl text-center">
      <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
        <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
      </div>
      <h2 className="text-xl font-bold text-white mb-2">Loading...</h2>
      <p className="text-gray-400 text-sm">Please wait...</p>
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#0a0a0f] to-[#0f0f1a] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/25">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <span className="font-bold text-xl text-white">BharatBuild</span>
        </div>

        <Suspense fallback={<LoadingFallback />}>
          <VerifyEmailContent />
        </Suspense>

        {/* Footer */}
        <div className="text-center mt-6 text-xs text-gray-500">
          <Link href="/" className="hover:text-gray-300">Back to Home</Link>
          {' · '}
          <Link href="/contact" className="hover:text-gray-300">Contact Support</Link>
        </div>
      </div>
    </div>
  )
}
