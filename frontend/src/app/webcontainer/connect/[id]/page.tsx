'use client'

/**
 * WebContainer Connect Handler
 * ============================
 * This page handles direct access to WebContainer URLs.
 * WebContainer URLs only work within the browser context where WebContainer was booted.
 * This page redirects the user back to the build page to see the preview.
 */

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Loader2, AlertCircle, ArrowLeft } from 'lucide-react'

export default function WebContainerConnectPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [countdown, setCountdown] = useState(5)

  useEffect(() => {
    // Countdown and redirect to build page
    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer)
          router.push('/build')
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [router])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 flex items-center justify-center">
      <div className="text-center max-w-lg px-6">
        <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-purple-500/20 flex items-center justify-center">
          <AlertCircle className="w-10 h-10 text-purple-400" />
        </div>

        <h1 className="text-white text-2xl font-bold mb-3">
          Preview Only Available in Editor
        </h1>

        <p className="text-purple-200 text-lg mb-6">
          WebContainer previews run in your browser and are connected to the editor.
          Opening this URL directly won't work.
        </p>

        <div className="bg-purple-800/30 rounded-xl p-6 mb-6">
          <p className="text-purple-300 text-sm mb-2">
            The preview is available inside the Build page where your project is running.
          </p>
          <p className="text-purple-400 text-xs">
            Connection ID: {params.id}
          </p>
        </div>

        <div className="flex items-center justify-center gap-3 text-purple-300 mb-6">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span>Redirecting to Build page in {countdown}s...</span>
        </div>

        <button
          onClick={() => router.push('/build')}
          className="inline-flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-medium transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Go to Build Page Now
        </button>

        <p className="text-purple-400/60 text-xs mt-8">
          Powered by StackBlitz WebContainer API
        </p>
      </div>
    </div>
  )
}
