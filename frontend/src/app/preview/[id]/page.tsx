'use client'

/**
 * Full-page WebContainer Preview
 * ===============================
 * Opens WebContainer preview in a new tab/window
 * This page receives the WebContainer URL via query params and displays it full-screen
 */

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { Loader2, AlertCircle } from 'lucide-react'

export default function PreviewPage({ params }: { params: { id: string } }) {
  const searchParams = useSearchParams()
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Get the preview URL from query params
    const url = searchParams.get('url')

    if (url) {
      setPreviewUrl(decodeURIComponent(url))
      setIsLoading(false)
    } else {
      // Try to get from sessionStorage (set by the build page)
      const storedUrl = sessionStorage.getItem(`preview_url_${params.id}`)
      if (storedUrl) {
        setPreviewUrl(storedUrl)
        setIsLoading(false)
      } else {
        setError('Preview URL not found. Please go back to the build page and try again.')
        setIsLoading(false)
      }
    }
  }, [params.id, searchParams])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-purple-500 animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Loading preview...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md px-6">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h1 className="text-white text-xl font-semibold mb-2">Preview Not Available</h1>
          <p className="text-gray-400">{error}</p>
          <a
            href="/build"
            className="inline-block mt-6 px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
          >
            Go to Build Page
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-white">
      {/* Header bar */}
      <div className="bg-gray-900 text-white px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm font-medium">Live Preview</span>
          <span className="text-xs text-gray-400 font-mono">{previewUrl}</span>
        </div>
        <a
          href="/build"
          className="text-sm text-gray-400 hover:text-white transition-colors"
        >
          Back to Editor
        </a>
      </div>

      {/* Full-screen iframe */}
      <iframe
        src={previewUrl || ''}
        className="w-full border-0"
        style={{ height: 'calc(100vh - 40px)' }}
        sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-popups"
        title="Full Page Preview"
      />
    </div>
  )
}
