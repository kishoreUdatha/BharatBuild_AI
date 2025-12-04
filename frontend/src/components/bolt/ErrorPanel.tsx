'use client'

import { useState } from 'react'
import {
  AlertTriangle,
  X,
  Wrench,
  Trash2,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Loader2,
  Check
} from 'lucide-react'
import { useErrorStore, CollectedError } from '@/store/errorStore'
import { useErrorCollector } from '@/hooks/useErrorCollector'

interface ErrorPanelProps {
  projectId?: string
  isOpen: boolean
  onClose: () => void
  onFileOpen?: (filePath: string, line?: number) => void
}

export function ErrorPanel({
  projectId,
  isOpen,
  onClose,
  onFileOpen
}: ErrorPanelProps) {
  const { errors, clearErrors, clearResolvedErrors } = useErrorStore()
  const { fixError, fixAllErrors, isFixing, unresolvedErrors, errorCount } = useErrorCollector({ projectId })
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set())
  const [fixingErrorId, setFixingErrorId] = useState<string | null>(null)

  if (!isOpen) return null

  const toggleError = (id: string) => {
    const newExpanded = new Set(expandedErrors)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedErrors(newExpanded)
  }

  const handleFixError = async (error: CollectedError) => {
    setFixingErrorId(error.id)
    try {
      await fixError(error)
    } finally {
      setFixingErrorId(null)
    }
  }

  const handleFixAll = async () => {
    await fixAllErrors()
  }

  const getSourceIcon = (source: string) => {
    switch (source) {
      case 'browser':
        return '🌐'
      case 'build':
        return '🔨'
      case 'runtime':
        return '⚡'
      case 'terminal':
        return '💻'
      case 'network':
        return '🔗'
      default:
        return '❌'
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'text-red-400 bg-red-500/10 border-red-500/30'
      case 'warning':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
      case 'info':
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30'
      default:
        return 'text-gray-400 bg-gray-500/10 border-gray-500/30'
    }
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-[hsl(var(--bolt-bg-secondary))] border-t border-[hsl(var(--bolt-border))] shadow-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[hsl(var(--bolt-border))]">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span className="text-sm font-medium text-[hsl(var(--bolt-text-primary))]">
            Problems ({errorCount.total})
          </span>
          <span className="text-xs text-[hsl(var(--bolt-text-tertiary))]">
            {errorCount.errors} errors, {errorCount.warnings} warnings
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* Fix All Button */}
          {unresolvedErrors.length > 0 && (
            <button
              onClick={handleFixAll}
              disabled={isFixing || !projectId}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-xs font-medium transition-colors"
            >
              {isFixing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Fixing...</span>
                </>
              ) : (
                <>
                  <Wrench className="w-3.5 h-3.5" />
                  <span>Fix All Errors</span>
                </>
              )}
            </button>
          )}

          {/* Clear Resolved */}
          <button
            onClick={clearResolvedErrors}
            className="p-1.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] transition-colors"
            title="Clear resolved errors"
          >
            <Trash2 className="w-4 h-4" />
          </button>

          {/* Close */}
          <button
            onClick={onClose}
            className="p-1.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Error List */}
      <div className="max-h-64 overflow-y-auto">
        {errors.length === 0 ? (
          <div className="p-8 text-center">
            <Check className="w-8 h-8 text-green-400 mx-auto mb-2" />
            <p className="text-sm text-[hsl(var(--bolt-text-secondary))]">No errors detected</p>
          </div>
        ) : (
          <div className="divide-y divide-[hsl(var(--bolt-border))]">
            {errors.map((error) => (
              <div
                key={error.id}
                className={`${error.resolved ? 'opacity-50' : ''}`}
              >
                {/* Error Row */}
                <div
                  className="flex items-start gap-3 px-4 py-2 hover:bg-[hsl(var(--bolt-bg-tertiary))] cursor-pointer group"
                  onClick={() => toggleError(error.id)}
                >
                  {/* Expand Icon */}
                  <button className="mt-0.5 text-[hsl(var(--bolt-text-tertiary))]">
                    {expandedErrors.has(error.id) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>

                  {/* Source Icon */}
                  <span className="text-sm" title={error.source}>
                    {getSourceIcon(error.source)}
                  </span>

                  {/* Severity Badge */}
                  <span className={`text-xs px-1.5 py-0.5 rounded border ${getSeverityColor(error.severity)}`}>
                    {error.severity}
                  </span>

                  {/* Error Message */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-[hsl(var(--bolt-text-primary))] truncate">
                      {error.message}
                    </p>
                    {error.file && (
                      <p className="text-xs text-[hsl(var(--bolt-text-tertiary))] mt-0.5">
                        {error.file}
                        {error.line && `:${error.line}`}
                        {error.column && `:${error.column}`}
                      </p>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    {/* Fix Button */}
                    {!error.resolved && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleFixError(error)
                        }}
                        disabled={isFixing || !projectId}
                        className="p-1.5 rounded hover:bg-green-600/20 text-green-400 disabled:opacity-50"
                        title="Fix this error"
                      >
                        {fixingErrorId === error.id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Wrench className="w-4 h-4" />
                        )}
                      </button>
                    )}

                    {/* Go to file */}
                    {error.file && onFileOpen && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onFileOpen(error.file!, error.line)
                        }}
                        className="p-1.5 rounded hover:bg-[hsl(var(--bolt-bg-tertiary))] text-[hsl(var(--bolt-text-secondary))]"
                        title="Go to file"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </button>
                    )}

                    {/* Resolved check */}
                    {error.resolved && (
                      <span className="text-green-400">
                        <Check className="w-4 h-4" />
                      </span>
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {expandedErrors.has(error.id) && (
                  <div className="px-12 pb-3 space-y-2">
                    {error.stack && (
                      <pre className="text-xs text-[hsl(var(--bolt-text-tertiary))] bg-[hsl(var(--bolt-bg-primary))] p-2 rounded overflow-x-auto whitespace-pre-wrap">
                        {error.stack}
                      </pre>
                    )}
                    {/* Network error specific details */}
                    {error.source === 'network' && error.url && (
                      <div className="text-xs bg-[hsl(var(--bolt-bg-primary))] p-2 rounded space-y-1">
                        <p className="text-[hsl(var(--bolt-text-secondary))]">
                          <span className="text-[hsl(var(--bolt-text-tertiary))]">URL:</span>{' '}
                          <span className="font-mono break-all">{error.url}</span>
                        </p>
                        {error.method && (
                          <p className="text-[hsl(var(--bolt-text-secondary))]">
                            <span className="text-[hsl(var(--bolt-text-tertiary))]">Method:</span>{' '}
                            <span className="font-mono">{error.method}</span>
                          </p>
                        )}
                        {error.status !== undefined && error.status > 0 && (
                          <p className="text-[hsl(var(--bolt-text-secondary))]">
                            <span className="text-[hsl(var(--bolt-text-tertiary))]">Status:</span>{' '}
                            <span className={`font-mono ${error.status >= 500 ? 'text-red-400' : error.status >= 400 ? 'text-yellow-400' : ''}`}>
                              {error.status}
                            </span>
                          </p>
                        )}
                      </div>
                    )}
                    <div className="text-xs text-[hsl(var(--bolt-text-tertiary))] space-y-1">
                      <p>Source: {error.source}</p>
                      <p>Time: {error.timestamp.toLocaleTimeString()}</p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ErrorPanel
