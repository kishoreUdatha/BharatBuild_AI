'use client'

import { useRef, useState } from 'react'
import { AlertCircle, FileUp, Loader2, Paperclip, X } from 'lucide-react'
import { checkFile, fileError, type UploadLimits } from '@/lib/file-api'
import { cn } from '@/lib/utils'

/**
 * Picking a file and sending it.
 *
 * Shared by both portals for the same reason the project editor is: the rules
 * about what may be uploaded live on the server, arrive in `limits`, and are
 * repeated here only to save someone a wasted upload. Nothing is decided here
 * that the server does not decide again.
 */
export function FileUpload({
  limits, categories, accent = '#4F46E5', disabled = false, compact = false,
  defaultCategory, onUpload, onDone,
}: {
  limits: UploadLimits
  /** Absent for a single-purpose target like the base paper. */
  categories?: string[]
  accent?: string
  disabled?: boolean
  compact?: boolean
  defaultCategory?: string
  onUpload: (file: File, category: string) => Promise<{ message: string }>
  onDone?: (message: string) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [category, setCategory] = useState(defaultCategory ?? categories?.[0] ?? 'Project Document')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)

  const pick = (chosen: File | null) => {
    setError('')
    if (!chosen) { setFile(null); return }
    const problem = checkFile(chosen, limits)
    if (problem) { setError(problem); setFile(null); return }
    setFile(chosen)
  }

  const send = async () => {
    if (!file) return
    setBusy(true); setError('')
    try {
      const result = await onUpload(file, category)
      setFile(null)
      if (input.current) input.current.value = ''
      onDone?.(result.message)
    } catch (err) {
      setError(fileError(err, 'That file could not be uploaded.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-1.5">
      <div
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault(); setDragging(false)
          if (!disabled) pick(e.dataTransfer.files?.[0] ?? null)
        }}
        className={cn(
          'flex flex-wrap items-center gap-2 rounded-lg border border-dashed px-2.5 py-2 transition',
          dragging ? 'bg-[#F5F3FF]' : 'bg-white',
          disabled && 'opacity-50'
        )}
        style={{ borderColor: dragging ? accent : '#DDE0EE' }}>

        <input ref={input} type="file" accept={limits.accept} disabled={disabled}
          className="hidden"
          onChange={(e) => pick(e.target.files?.[0] ?? null)} />

        <button type="button" disabled={disabled} onClick={() => input.current?.click()}
          className="flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[11.5px] font-medium transition disabled:opacity-50"
          style={{ borderColor: accent, color: accent }}>
          <Paperclip className="h-3.5 w-3.5" /> Choose file
        </button>

        {file ? (
          <span className="flex min-w-0 items-center gap-1.5 text-[11.5px] text-[#1B1B3A]">
            <span className="truncate max-w-[220px]">{file.name}</span>
            <span className="shrink-0 text-[#8A8FA8]">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </span>
            <button type="button" aria-label="Clear" onClick={() => pick(null)}
              className="shrink-0 text-[#C7CBDD] hover:text-[#DC2626]">
              <X className="h-3.5 w-3.5" />
            </button>
          </span>
        ) : (
          <span className="text-[11px] text-[#8A8FA8]">
            {compact ? `PDF, up to ${limits.max_mb} MB`
              : `or drop one here — ${limits.extensions.join(', ')}, up to ${limits.max_mb} MB`}
          </span>
        )}

        {categories && categories.length > 0 && (
          <select value={category} onChange={(e) => setCategory(e.target.value)} disabled={disabled}
            className="ml-auto h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11.5px] text-[#3A3F58] outline-none">
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}

        <button type="button" onClick={send} disabled={disabled || busy || !file}
          className={cn('flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[11.5px] font-medium text-white transition disabled:opacity-40',
            !categories?.length && 'ml-auto')}
          style={{ background: accent }}>
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileUp className="h-3.5 w-3.5" />}
          Upload
        </button>
      </div>

      {error && (
        <p className="flex items-start gap-1.5 text-[11px] leading-snug text-[#DC2626]">
          <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}
    </div>
  )
}
