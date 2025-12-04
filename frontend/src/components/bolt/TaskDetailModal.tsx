'use client'

import { FileOperation } from '@/store/chatStore'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  FilePlus,
  FileEdit,
  Trash2,
  Copy,
  Check,
  X,
} from 'lucide-react'
import { useState } from 'react'
import Editor from '@monaco-editor/react'
import { monacoTheme } from '@/utils/editorThemes'

// Helper: Get language from file path
const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase()
  const languageMap: Record<string, string> = {
    js: 'javascript',
    jsx: 'javascript',
    ts: 'typescript',
    tsx: 'typescript',
    py: 'python',
    java: 'java',
    html: 'html',
    css: 'css',
    json: 'json',
    md: 'markdown',
    yaml: 'yaml',
    yml: 'yaml',
  }
  return languageMap[ext || ''] || 'plaintext'
}

interface TaskDetailModalProps {
  isOpen: boolean
  task: FileOperation | null
  onClose: () => void
}

export function TaskDetailModal({ isOpen, task, onClose }: TaskDetailModalProps) {
  const [copied, setCopied] = useState(false)

  if (!task) return null

  const handleCopyPath = async () => {
    await navigator.clipboard.writeText(task.path)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleCopyContent = async () => {
    if (task.content) {
      await navigator.clipboard.writeText(task.content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const getStatusIcon = () => {
    switch (task.status) {
      case 'complete':
        return <CheckCircle2 className="w-5 h-5 text-green-500" />
      case 'in-progress':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
      case 'error':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'pending':
        return <Clock className="w-5 h-5 text-gray-500" />
    }
  }

  const getStatusBadge = () => {
    const variants: Record<FileOperation['status'], string> = {
      complete: 'bg-green-500/10 text-green-500 border-green-500/20',
      'in-progress': 'bg-blue-500/10 text-blue-500 border-blue-500/20',
      error: 'bg-red-500/10 text-red-500 border-red-500/20',
      pending: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
    }

    return (
      <Badge className={`${variants[task.status]} border`}>
        {task.status.toUpperCase()}
      </Badge>
    )
  }

  const getTypeIcon = () => {
    switch (task.type) {
      case 'create':
        return <FilePlus className="w-5 h-5 text-green-500" />
      case 'modify':
        return <FileEdit className="w-5 h-5 text-blue-500" />
      case 'delete':
        return <Trash2 className="w-5 h-5 text-red-500" />
    }
  }

  const getTypeBadge = () => {
    const variants: Record<FileOperation['type'], string> = {
      create: 'bg-green-500/10 text-green-500 border-green-500/20',
      modify: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
      delete: 'bg-red-500/10 text-red-500 border-red-500/20',
    }

    return (
      <Badge className={`${variants[task.type]} border`}>
        {task.type.toUpperCase()}
      </Badge>
    )
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden flex flex-col bg-[hsl(var(--bolt-bg-secondary))] border-[hsl(var(--bolt-border))]">
        {/* Header */}
        <DialogHeader className="border-b border-[hsl(var(--bolt-border))] pb-4">
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div className="mt-1">{getStatusIcon()}</div>
              <div>
                <DialogTitle className="text-xl font-semibold text-[hsl(var(--bolt-text-primary))] mb-2">
                  Task Details
                </DialogTitle>
                <DialogDescription className="text-[hsl(var(--bolt-text-secondary))]">
                  View complete information about this file operation
                </DialogDescription>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        {/* Content */}
        <div className="flex-1 overflow-y-auto space-y-6 py-4">
          {/* Status & Type */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
                Status
              </label>
              <div className="flex items-center gap-2">
                {getStatusIcon()}
                {getStatusBadge()}
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
                Operation Type
              </label>
              <div className="flex items-center gap-2">
                {getTypeIcon()}
                {getTypeBadge()}
              </div>
            </div>
          </div>

          {/* File Path */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
              File Path
            </label>
            <div className="flex items-center gap-2">
              <div className="flex-1 px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] font-mono text-sm text-[hsl(var(--bolt-text-primary))]">
                {task.path}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyPath}
                className="h-9 px-3 text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
              >
                {copied ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
              Description
            </label>
            <div className="px-3 py-2 rounded-lg bg-[hsl(var(--bolt-bg-tertiary))] border border-[hsl(var(--bolt-border))] text-sm text-[hsl(var(--bolt-text-primary))]">
              {task.description || 'No description provided'}
            </div>
          </div>

          {/* File Content */}
          {task.content && task.type !== 'delete' && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-[hsl(var(--bolt-text-secondary))]">
                  File Content
                </label>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyContent}
                  className="h-7 px-2 text-xs text-[hsl(var(--bolt-text-secondary))] hover:text-[hsl(var(--bolt-text-primary))]"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 mr-1" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3 mr-1" />
                      Copy Content
                    </>
                  )}
                </Button>
              </div>
              <div className="rounded-lg border border-[hsl(var(--bolt-border))] overflow-hidden" style={{ height: '400px' }}>
                <Editor
                  height="100%"
                  theme="bharatbuild"
                  language={getLanguageFromPath(task.path)}
                  value={task.content}
                  beforeMount={(monaco) => {
                    monaco.editor.defineTheme('bharatbuild', monacoTheme)
                  }}
                  options={{
                    readOnly: true,
                    fontSize: 14,
                    minimap: { enabled: false },
                    scrollBeyondLastLine: false,
                    wordWrap: 'on',
                  }}
                />
              </div>
            </div>
          )}

          {/* Error Details (if status is error) */}
          {task.status === 'error' && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-red-500">
                Error Details
              </label>
              <div className="px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-500">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">Failed to {task.type} file</p>
                    <p className="text-xs opacity-80">
                      The operation could not be completed. This might be due to permission issues,
                      file conflicts, or syntax errors in the generated code.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Progress Info (if in-progress) */}
          {task.status === 'in-progress' && (
            <div className="space-y-2">
              <div className="px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-sm text-blue-500">
                <div className="flex items-start gap-2">
                  <Loader2 className="w-4 h-4 mt-0.5 flex-shrink-0 animate-spin" />
                  <div>
                    <p className="font-medium mb-1">Operation in progress...</p>
                    <p className="text-xs opacity-80">
                      AI is currently {task.type === 'create' ? 'generating' : task.type === 'modify' ? 'modifying' : 'removing'} this file.
                      Please wait while the operation completes.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Success Info (if complete) */}
          {task.status === 'complete' && (
            <div className="space-y-2">
              <div className="px-3 py-2 rounded-lg bg-green-500/10 border border-green-500/20 text-sm text-green-500">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="font-medium mb-1">Operation completed successfully</p>
                    <p className="text-xs opacity-80">
                      File has been {task.type === 'create' ? 'created' : task.type === 'modify' ? 'modified' : 'deleted'} successfully.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[hsl(var(--bolt-border))] pt-4 flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            className="text-[hsl(var(--bolt-text-primary))] border-[hsl(var(--bolt-border))] hover:bg-[hsl(var(--bolt-bg-tertiary))]"
          >
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
