'use client'

import { useState } from 'react'
import { Copy, Check, Download, Eye, Code2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface CodePreviewProps {
  code: string
  language?: string
  fileName?: string
  showPreview?: boolean
}

export function CodePreview({
  code,
  language = 'javascript',
  fileName = 'code.js',
  showPreview = false,
}: CodePreviewProps) {
  const [copied, setCopied] = useState(false)
  const [viewMode, setViewMode] = useState<'code' | 'preview'>(showPreview ? 'preview' : 'code')

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="h-full flex flex-col bg-[hsl(var(--bolt-bg-primary))]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--bolt-border))] bg-[hsl(var(--bolt-bg-secondary))]">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
            {fileName}
          </span>
          <span className="text-xs text-[hsl(var(--bolt-text-secondary))] bg-[hsl(var(--bolt-bg-tertiary))] px-2 py-0.5 rounded">
            {language}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View Mode Toggle */}
          {showPreview && (
            <div className="flex items-center gap-1 bg-[hsl(var(--bolt-bg-tertiary))] rounded p-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setViewMode('code')}
                className={`h-7 px-3 text-xs ${
                  viewMode === 'code'
                    ? 'bg-[hsl(var(--bolt-accent))] text-white'
                    : 'text-[hsl(var(--bolt-text-secondary))]'
                }`}
              >
                <Code2 className="w-3 h-3 mr-1" />
                Code
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setViewMode('preview')}
                className={`h-7 px-3 text-xs ${
                  viewMode === 'preview'
                    ? 'bg-[hsl(var(--bolt-accent))] text-white'
                    : 'text-[hsl(var(--bolt-text-secondary))]'
                }`}
              >
                <Eye className="w-3 h-3 mr-1" />
                Preview
              </Button>
            </div>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-7 px-2 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
          >
            {copied ? (
              <Check className="w-4 h-4" />
            ) : (
              <Copy className="w-4 h-4" />
            )}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            className="h-7 px-2 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
          >
            <Download className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Code Content */}
      <div className="flex-1 overflow-auto scrollbar-thin">
        {viewMode === 'code' ? (
          <pre className="p-4 text-sm font-mono leading-relaxed">
            <code className="text-[hsl(var(--bolt-text-primary))]">{code}</code>
          </pre>
        ) : (
          <div className="p-4">
            <div className="bg-white rounded border">
              <iframe
                srcDoc={code}
                className="w-full h-full min-h-[400px]"
                title="Preview"
                sandbox="allow-scripts"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
