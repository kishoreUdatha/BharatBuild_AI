'use client'

import { useEffect, useRef, useState } from 'react'
import { RefreshCw, ExternalLink, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface LivePreviewProps {
  files: Record<string, string>
  entryPoint?: string
}

export function LivePreview({ files, entryPoint = 'index.html' }: LivePreviewProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (Object.keys(files).length === 0) return

    try {
      setIsLoading(true)
      setError(null)

      // Generate preview HTML
      const previewHTML = generatePreviewHTML(files, entryPoint)

      // Update iframe
      if (iframeRef.current) {
        const iframeDoc = iframeRef.current.contentDocument || iframeRef.current.contentWindow?.document

        if (iframeDoc) {
          iframeDoc.open()
          iframeDoc.write(previewHTML)
          iframeDoc.close()
        }
      }

      setIsLoading(false)
    } catch (err: any) {
      setError(err.message)
      setIsLoading(false)
    }
  }, [files, entryPoint])

  const handleRefresh = () => {
    if (iframeRef.current) {
      iframeRef.current.src = iframeRef.current.src
    }
  }

  const handleOpenInNewTab = () => {
    const previewHTML = generatePreviewHTML(files, entryPoint)
    const blob = new Blob([previewHTML], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
            Live Preview
          </span>
          {isLoading && (
            <div className="flex items-center gap-2 text-xs text-[hsl(var(--bolt-text-secondary))]">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              Loading...
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            className="h-7 px-2 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
            title="Refresh preview"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleOpenInNewTab}
            className="h-7 px-2 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
            title="Open in new tab"
          >
            <ExternalLink className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Preview Content */}
      <div className="flex-1 relative bg-white">
        {error ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-6">
              <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
              <p className="text-sm text-gray-600 mb-2">Preview Error</p>
              <p className="text-xs text-gray-500">{error}</p>
            </div>
          </div>
        ) : Object.keys(files).length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center p-6">
              <p className="text-sm text-gray-500">
                No preview available yet
              </p>
              <p className="text-xs text-gray-400 mt-2">
                Start building to see live preview
              </p>
            </div>
          </div>
        ) : (
          <iframe
            ref={iframeRef}
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin allow-forms allow-modals"
            title="Live Preview"
          />
        )}
      </div>
    </div>
  )
}

function generatePreviewHTML(files: Record<string, string>, entryPoint: string): string {
  // Check if we have an HTML file
  const htmlFile = files[entryPoint] || files['index.html'] || files['src/index.html']

  if (htmlFile) {
    // If HTML exists, inject other files
    let html = htmlFile

    // Inject CSS
    const cssFiles = Object.entries(files).filter(([path]) => path.endsWith('.css'))
    const cssContent = cssFiles.map(([_, content]) => content).join('\n')
    if (cssContent) {
      html = html.replace('</head>', `<style>${cssContent}</style></head>`)
    }

    // Inject JS (as modules)
    const jsFiles = Object.entries(files).filter(([path]) =>
      path.endsWith('.js') || path.endsWith('.jsx')
    )
    const jsContent = jsFiles.map(([_, content]) => content).join('\n')
    if (jsContent) {
      html = html.replace('</body>', `<script type="module">${jsContent}</script></body>`)
    }

    return html
  }

  // Generate HTML from scratch
  const jsFiles = Object.entries(files).filter(([path]) =>
    path.endsWith('.js') || path.endsWith('.jsx')
  )
  const cssFiles = Object.entries(files).filter(([path]) => path.endsWith('.css'))

  const css = cssFiles.map(([_, content]) => content).join('\n')
  const js = jsFiles.map(([_, content]) => content).join('\n')

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    ${css}
  </style>
</head>
<body>
  <div id="root"></div>
  <div id="app"></div>

  <script type="module">
    ${js}
  </script>
</body>
</html>`
}
