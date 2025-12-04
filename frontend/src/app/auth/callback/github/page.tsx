'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react'

function GitHubCallbackContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [error, setError] = useState('')

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code')
      const state = searchParams.get('state')
      const errorParam = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')

      if (errorParam) {
        setStatus('error')
        setError(errorDescription || (errorParam === 'access_denied'
          ? 'You cancelled the sign-in process.'
          : `Authentication error: ${errorParam}`))
        return
      }

      if (!code) {
        setStatus('error')
        setError('No authorization code received from GitHub.')
        return
      }

      try {
        // Get stored state for verification (optional)
        const storedState = sessionStorage.getItem('oauth_state')
        if (storedState && state !== storedState) {
          setStatus('error')
          setError('Invalid state parameter. Please try again.')
          return
        }

        // Get stored role preference
        const role = sessionStorage.getItem('oauth_role') || 'student'

        // Exchange code for tokens
        const response = await apiClient.githubCallback(code, role)

        // Store tokens
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)

        // Clean up session storage
        sessionStorage.removeItem('oauth_state')
        sessionStorage.removeItem('oauth_role')

        setStatus('success')

        // Redirect after short delay to show success
        setTimeout(() => {
          if (response.is_new_user) {
            router.push('/dashboard?welcome=true')
          } else {
            router.push('/dashboard')
          }
        }, 1500)

      } catch (err: any) {
        setStatus('error')
        setError(err.response?.data?.detail || 'Failed to complete GitHub sign-in. Please try again.')
      }
    }

    handleCallback()
  }, [searchParams, router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex items-center justify-center mb-4">
            {status === 'loading' && (
              <div className="h-12 w-12 bg-gray-100 rounded-full flex items-center justify-center">
                <Loader2 className="h-6 w-6 text-gray-600 animate-spin" />
              </div>
            )}
            {status === 'success' && (
              <div className="h-12 w-12 bg-green-100 rounded-full flex items-center justify-center">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            )}
            {status === 'error' && (
              <div className="h-12 w-12 bg-red-100 rounded-full flex items-center justify-center">
                <AlertCircle className="h-6 w-6 text-red-600" />
              </div>
            )}
          </div>
          <CardTitle className="text-2xl font-bold">
            {status === 'loading' && 'Signing you in...'}
            {status === 'success' && 'Welcome!'}
            {status === 'error' && 'Sign-in Failed'}
          </CardTitle>
          <CardDescription>
            {status === 'loading' && 'Please wait while we complete your GitHub sign-in.'}
            {status === 'success' && 'Redirecting you to your dashboard...'}
            {status === 'error' && 'Something went wrong during sign-in.'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {status === 'error' && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {status === 'error' && (
            <div className="mt-4 text-center">
              <button
                onClick={() => router.push('/login')}
                className="text-indigo-600 hover:text-indigo-500 font-medium"
              >
                Return to login
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default function GitHubCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-gray-600 animate-spin" />
      </div>
    }>
      <GitHubCallbackContent />
    </Suspense>
  )
}
