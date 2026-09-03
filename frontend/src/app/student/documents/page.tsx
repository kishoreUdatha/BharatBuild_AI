'use client'

/**
 * The team's documents.
 *
 * Everything here is scoped to the reader's own batch by the server - none of
 * these routes take a batch id, so there is nothing in a URL for anyone to
 * change.
 */

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight,
  Download, Eye, File, FileArchive, FileCode, FileImage, FileSpreadsheet,
  FileText, FileVideo, FolderOpen, Info, Loader2, Lock, Presentation,
  RotateCcw, Search, Trash2, Upload, UploadCloud, X,
} from 'lucide-react'
import { fetchRegistration, type RegistrationState } from '@/lib/student-api'
import {
  downloadStudentBasePaper,
  downloadStudentDocument,
  fetchStudentDocuments,
  fileError,
  removeStudentDocument,
  uploadStudentBasePaper,
  uploadStudentDocument,
  type StudentDocuments as Docs,
} from '@/lib/file-api'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const ACCENT = '#2563EB'
const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'
const PAGE_SIZES = [10, 25, 50]

/** The system's own four states, not a second vocabulary for the same thing. */
const STATUS: Record<string, { label: string; tone: string }> = {
  verified: { label: 'Verified', tone: 'bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]' },
  awaiting_verification: { label: 'Awaiting review', tone: 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]' },
  changes_requested: { label: 'Changes requested', tone: 'bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]' },
  missing: { label: 'Missing', tone: 'bg-[#F3F4F6] text-[#6B7280] border-[#E5E7EB]' },
}

/**
 * The icon and colour for a file, by extension.
 *
 * Keyed on the extension rather than the mime type: the extension is what the
 * reader sees in the filename, and a .docx served as octet-stream should still
 * look like a Word document.
 */
const FILE_KIND: Record<string, { icon: typeof FileText; tone: string }> = {
  pdf: { icon: FileText, tone: 'text-[#DC2626]' },
  doc: { icon: FileText, tone: 'text-[#2563EB]' },
  docx: { icon: FileText, tone: 'text-[#2563EB]' },
  rtf: { icon: FileText, tone: 'text-[#2563EB]' },
  txt: { icon: FileText, tone: 'text-[#6B7280]' },
  ppt: { icon: Presentation, tone: 'text-[#EA580C]' },
  pptx: { icon: Presentation, tone: 'text-[#EA580C]' },
  xls: { icon: FileSpreadsheet, tone: 'text-[#16A34A]' },
  xlsx: { icon: FileSpreadsheet, tone: 'text-[#16A34A]' },
  csv: { icon: FileSpreadsheet, tone: 'text-[#16A34A]' },
  zip: { icon: FileArchive, tone: 'text-[#CA8A04]' },
  rar: { icon: FileArchive, tone: 'text-[#CA8A04]' },
  '7z': { icon: FileArchive, tone: 'text-[#CA8A04]' },
  png: { icon: FileImage, tone: 'text-[#7C3AED]' },
  jpg: { icon: FileImage, tone: 'text-[#7C3AED]' },
  jpeg: { icon: FileImage, tone: 'text-[#7C3AED]' },
  gif: { icon: FileImage, tone: 'text-[#7C3AED]' },
  svg: { icon: FileImage, tone: 'text-[#7C3AED]' },
  mp4: { icon: FileVideo, tone: 'text-[#0891B2]' },
  mov: { icon: FileVideo, tone: 'text-[#0891B2]' },
  py: { icon: FileCode, tone: 'text-[#0F766E]' },
  js: { icon: FileCode, tone: 'text-[#0F766E]' },
  ts: { icon: FileCode, tone: 'text-[#0F766E]' },
  java: { icon: FileCode, tone: 'text-[#0F766E]' },
  sql: { icon: FileCode, tone: 'text-[#0F766E]' },
}

const fileKind = (filename: string | null | undefined) => {
  const ext = (filename ?? '').split('.').pop()?.toLowerCase() ?? ''
  // An unknown extension gets a plain sheet rather than a wrong one - a
  // guessed icon is worse than an honest blank.
  return FILE_KIND[ext] ?? { icon: File, tone: 'text-[#9CA3AF]' }
}

/** Types a browser renders in a tab. Anything else is a download, not a view. */
const VIEWABLE = /^(application\/pdf|image\/|text\/plain)/

const fmtWhen = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }) : '—'

const humanSize = (bytes: number) => {
  if (!bytes) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let n = bytes
  let i = 0
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i += 1 }
  return `${n < 10 && i > 0 ? n.toFixed(2) : Math.round(n)} ${units[i]}`
}

export default function StudentDocumentsPage() {
  const [registration, setRegistration] = useState<RegistrationState | null>(null)
  const [docs, setDocs] = useState<Docs | null>(null)
  const [blocked, setBlocked] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [busy, setBusy] = useState('')

  const [q, setQ] = useState('')
  const [type, setType] = useState('all')
  const [status, setStatus] = useState('all')
  const [size, setSize] = useState(10)
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    const [reg, list] = await Promise.allSettled([
      fetchRegistration(), fetchStudentDocuments()])
    if (reg.status === 'fulfilled') setRegistration(reg.value)
    if (list.status === 'fulfilled') setDocs(list.value)
    else setBlocked((list.reason as any)?.response?.data?.detail
      ?? 'Your documents could not be loaded.')
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const rows = docs?.rows ?? []

  const types = useMemo(
    () => Array.from(new Set(rows.map((r) => r.category).filter(Boolean))).sort(),
    [rows])

  // Applied as you touch them; an Apply button would be a second click to do
  // what the first one already asked for.
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    return rows.filter((r) => {
      if (type !== 'all' && r.category !== type) return false
      if (status !== 'all' && r.status !== status) return false
      if (!needle) return true
      return [r.name, r.category, r.uploaded_by, r.file?.name]
        .some((f) => (f ?? '').toLowerCase().includes(needle))
    })
  }, [rows, q, type, status])

  const totals = useMemo(() => ({
    all: rows.length,
    verified: rows.filter((r) => r.status === 'verified').length,
    waiting: rows.filter((r) => r.status === 'awaiting_verification').length,
    changes: rows.filter((r) => r.status === 'changes_requested').length,
    bytes: rows.reduce((sum, r) => sum + (r.file?.byte_size ?? 0), 0),
  }), [rows])

  const pages = Math.max(1, Math.ceil(shown.length / size))
  const current = Math.min(page, pages)
  const slice = shown.slice((current - 1) * size, current * size)
  const dirty = Boolean(q) || type !== 'all' || status !== 'all'

  /** Open a document in a tab. Fetched with auth, so it cannot be a bare href. */
  const view = async (id: string, name: string) => {
    setBusy(id)
    setError('')
    try {
      const blob = await apiClient.get<Blob>(
        `/student/documents/${id}/download`, { responseType: 'blob' })
      const href = URL.createObjectURL(blob)
      window.open(href, '_blank', 'noopener')
      // Long enough for the new tab to have loaded it; revoking immediately
      // leaves the tab blank.
      setTimeout(() => URL.revokeObjectURL(href), 60_000)
    } catch {
      setError(`${name} could not be opened.`)
    } finally { setBusy('') }
  }

  const remove = async (id: string, name: string) => {
    setBusy(id)
    setError('')
    setNotice('')
    try {
      await removeStudentDocument(id)
      setNotice(`${name} removed.`)
      await load()
    } catch (err) {
      setError(fileError(err, `${name} could not be removed.`))
    } finally { setBusy('') }
  }

  if (loading) {
    return (
      <p className={cn(CARD, 'flex items-center justify-center gap-2 px-4 py-12 text-[12.5px] text-[#6B7280]')}>
        <Loader2 className="h-4 w-4 animate-spin" /> Loading your documents…
      </p>
    )
  }
  if (blocked || !docs) {
    return (
      <div className={cn(CARD, 'px-4 py-10 text-center')}>
        <Lock className="mx-auto h-6 w-6 text-[#D1D5DB]" />
        <p className="mt-2 text-[12.5px] text-[#B91C1C]">{blocked}</p>
        <Link href="/student/registration"
          className="mt-2 inline-block text-[12px] font-medium text-[#2563EB] hover:underline">
          Go to registration
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-2">
          <h1 className="text-[17px] font-bold leading-tight text-[#1B1B3A]">
            My Documents
          </h1>
          <span className="text-[11.5px] text-[#6B7280]">
            Everything your team has uploaded for {docs.batch_code}.
          </span>
        </div>
        <button type="button" onClick={() => setUploading((v) => !v)}
          className="flex h-8 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3 text-[12px] font-medium text-white hover:bg-[#1D4ED8]">
          {uploading ? <X className="h-4 w-4" /> : <Upload className="h-4 w-4" />}
          {uploading ? 'Close' : 'Upload document'}
        </button>
      </div>

      {docs.missing_required.length > 0 && (
        <p className="flex items-start gap-2 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] text-[#92400E]">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            Still required: {docs.missing_required.join(', ')}.
          </span>
        </p>
      )}
      {notice && (
        <p className="rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-3 py-2 text-[12px] text-[#166534]">
          {notice}
        </p>
      )}
      {error && (
        <p className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[12px] text-[#B91C1C]">
          {error}
        </p>
      )}

      {uploading && (
        <UploadDialog
          docs={docs}
          project={registration?.batch?.title ?? docs.batch_code}
          onClose={() => setUploading(false)}
          onDone={async (message) => {
            setUploading(false)
            setNotice(message)
            setError('')
            await load()
          }} />
      )}

      {/* ------------------------------------------------------------ summary */}
      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-3.5 py-2">
          <Stat label="Documents" value={String(totals.all)} />
          <Stat label="Verified" value={String(totals.verified)} tone="text-[#166534]" />
          <Stat label="Awaiting review" value={String(totals.waiting)}
            tone={totals.waiting ? 'text-[#B45309]' : undefined} />
          <Stat label="Changes requested" value={String(totals.changes)}
            tone={totals.changes ? 'text-[#B91C1C]' : undefined} />
          <Stat label="Total size" value={humanSize(totals.bytes)} />
        </div>

        <div className="flex flex-wrap items-center gap-2 border-t border-[#F1F2F8] bg-[#FCFCFD] px-3.5 py-2">
          <span className="text-[11px] text-[#6B7280]">
            Project <span className="font-medium text-[#374151]">
              {registration?.batch?.title ?? docs.batch_code}
            </span>
          </span>
          <select value={type} aria-label="Document type"
            onChange={(e) => { setType(e.target.value); setPage(1) }}
            className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-1.5 text-[11.5px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
            <option value="all">All types</option>
            {types.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select value={status} aria-label="Status"
            onChange={(e) => { setStatus(e.target.value); setPage(1) }}
            className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-1.5 text-[11.5px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
            <option value="all">All statuses</option>
            {Object.entries(STATUS).map(([key, s]) => (
              <option key={key} value={key}>{s.label}</option>
            ))}
          </select>
          <label className="relative min-w-[180px] flex-1">
            <Search className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
            <input value={q} onChange={(e) => { setQ(e.target.value); setPage(1) }}
              placeholder="Search documents"
              className="h-7 w-full rounded-lg border border-[#D1D5DB] bg-white pl-7 pr-2 text-[11.5px] text-[#1B1B3A] placeholder:text-[#9CA3AF] focus:border-[#2563EB] focus:outline-none" />
          </label>
          {dirty && (
            <button type="button"
              onClick={() => { setQ(''); setType('all'); setStatus('all'); setPage(1) }}
              className="flex h-7 items-center gap-1 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
              <RotateCcw className="h-3 w-3" /> Reset
            </button>
          )}
        </div>
      </div>

      {/* -------------------------------------------------------------- table */}
      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[#F1F2F8] px-3.5 py-2">
          <h2 className="text-[12.5px] font-semibold text-[#1B1B3A]">
            Uploaded documents
          </h2>
          <span className="text-[10.5px] text-[#9CA3AF]">
            A verified document is locked; a new upload supersedes it
          </span>
        </div>

        {shown.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <FolderOpen className="mx-auto h-6 w-6 text-[#D1D5DB]" />
            <p className="mt-2 text-[12.5px] text-[#6B7280]">
              {rows.length === 0
                ? 'Nothing uploaded yet. Use Upload document to add your first one.'
                : 'No document matches those filters.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[880px] border-collapse text-left">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
                  <th className="w-10 px-3 py-2">#</th>
                  <th className="px-3 py-2">Document name</th>
                  <th className="px-3 py-2">Type</th>
                  <th className="px-3 py-2">Uploaded on</th>
                  <th className="px-3 py-2">Uploaded by</th>
                  <th className="px-3 py-2 text-center">Status</th>
                  <th className="px-3 py-2 text-right">Size</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((row, i) => {
                  const state = STATUS[row.status] ?? STATUS.missing
                  const file = row.file
                  const working = busy === row.id
                  return (
                    <tr key={row.id}
                      className={cn('border-b border-[#F1F2F8] text-[12px] last:border-0',
                        row.superseded && 'opacity-60')}>
                      <td className="px-3 py-2 text-[#9CA3AF]">
                        {(current - 1) * size + i + 1}
                      </td>
                      <td className="px-3 py-2">
                        <span className="flex items-start gap-2">
                          {(() => {
                            const kind = fileKind(file?.name ?? row.name)
                            return <kind.icon className={cn('mt-0.5 h-4 w-4 shrink-0', kind.tone)} />
                          })()}
                          <span className="min-w-0">
                            <span className="block truncate font-medium text-[#1B1B3A]">
                              {file?.name ?? row.name}
                            </span>
                            <span className="block truncate text-[10px] text-[#9CA3AF]">
                              {row.name}
                              {row.version ? ` · ${row.version}` : ''}
                              {row.superseded ? ' · superseded' : ''}
                            </span>
                          </span>
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="rounded border border-[#E0E7FF] bg-[#EEF2FF] px-1.5 py-0.5 text-[10.5px] font-medium text-[#4338CA]">
                          {row.category}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                        {fmtWhen(row.uploaded_at)}
                      </td>
                      <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                        {row.uploaded_by ?? '—'}
                      </td>
                      <td className="px-3 py-2 text-center">
                        <span title={row.faculty_note ?? undefined}
                          className={cn('rounded border px-1.5 py-0.5 text-[10.5px] font-medium',
                            state.tone)}>
                          {state.label}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-[11px] text-[#6B7280]">
                        {file ? humanSize(file.byte_size) : '—'}
                      </td>
                      <td className="px-3 py-2">
                        <span className="flex items-center justify-end gap-1">
                          {file && VIEWABLE.test(file.mime_type ?? '') && (
                            <Action label="Open in a new tab" disabled={working}
                              onClick={() => view(row.id, file.name)}>
                              <Eye className="h-3.5 w-3.5" />
                            </Action>
                          )}
                          {file && (
                            <Action label="Download" disabled={working}
                              onClick={() => downloadStudentDocument(row.id, file.name)
                                .catch(() => setError(`${file.name} could not be downloaded.`))}>
                              <Download className="h-3.5 w-3.5" />
                            </Action>
                          )}
                          {row.can_remove ? (
                            <Action label="Remove" danger disabled={working}
                              onClick={() => remove(row.id, row.name)}>
                              {working ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                                : <Trash2 className="h-3.5 w-3.5" />}
                            </Action>
                          ) : (
                            // Verified and superseded documents are evidence an
                            // approval was granted against; neither may be taken back.
                            <span title={row.superseded
                              ? 'Superseded documents are kept as history'
                              : 'Verified documents are locked'}
                              className="flex h-7 w-7 items-center justify-center text-[#D1D5DB]">
                              <Lock className="h-3.5 w-3.5" />
                            </span>
                          )}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E5E7EB] px-3.5 py-2.5">
          <p className="text-[11px] text-[#6B7280]">
            {shown.length === 0
              ? 'No documents'
              : `Showing ${(current - 1) * size + 1} to ${Math.min(current * size, shown.length)} of ${shown.length} documents`}
            {dirty && rows.length !== shown.length ? ` (filtered from ${rows.length})` : ''}
          </p>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-[11px] text-[#6B7280]">
              Rows per page
              <select value={size}
                onChange={(e) => { setSize(Number(e.target.value)); setPage(1) }}
                className="h-7 rounded border border-[#D1D5DB] bg-white px-1.5 text-[11px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
                {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <div className="flex items-center gap-0.5">
              <Pager label="First" disabled={current === 1} onClick={() => setPage(1)}>
                <ChevronsLeft className="h-3.5 w-3.5" />
              </Pager>
              <Pager label="Previous" disabled={current === 1}
                onClick={() => setPage(current - 1)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </Pager>
              <span className="px-2 text-[11px] text-[#6B7280]">
                Page {current} of {pages}
              </span>
              <Pager label="Next" disabled={current === pages}
                onClick={() => setPage(current + 1)}>
                <ChevronRight className="h-3.5 w-3.5" />
              </Pager>
              <Pager label="Last" disabled={current === pages}
                onClick={() => setPage(pages)}>
                <ChevronsRight className="h-3.5 w-3.5" />
              </Pager>
            </div>
          </div>
        </div>

        <p className="flex items-start gap-2 border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2563EB]" />
          <span>
            Anyone on your team can upload. Once your guide verifies a document
            it is locked — uploading again creates a new version rather than
            replacing it, so what was approved stays on record.
          </span>
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- small parts

/**
 * The upload dialog.
 *
 * Only the fields that are actually stored appear here. A description or tag
 * box that quietly discarded what was typed would be worse than not offering
 * one, and versions are assigned by the server when a document supersedes an
 * earlier one - letting a student type their own would fight it.
 */
function UploadDialog({ docs, project, onClose, onDone }: {
  docs: Docs
  project: string
  onClose: () => void
  onDone: (message: string) => Promise<void> | void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [category, setCategory] = useState(
    docs.missing_required[0] ?? docs.categories[0] ?? '')
  const [over, setOver] = useState(false)
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState('')

  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [onClose])

  const limits = docs.limits

  /** Refuse locally what the server would refuse, before spending the upload. */
  const accept = (picked: File) => {
    setProblem('')
    const ext = picked.name.split('.').pop()?.toLowerCase() ?? ''
    if (limits.extensions?.length && !limits.extensions.includes(ext)) {
      setProblem(`${ext ? `.${ext}` : 'That file'} is not an accepted type.`)
      return
    }
    if (limits.max_bytes && picked.size > limits.max_bytes) {
      setProblem(`That file is ${humanSize(picked.size)}; the limit is ${limits.max_mb} MB.`)
      return
    }
    setFile(picked)
    // The filename is the name nine times out of ten, so offer it rather than
    // making them retype it - still editable.
    if (!name.trim()) setName(picked.name.replace(/\.[^.]+$/, ''))
  }

  const submit = async () => {
    if (!file || !name.trim() || !category) return
    setBusy(true)
    setProblem('')
    try {
      // "Base Paper" has its own store behind it, and the registration
      // checklist reads that one - not the document list.
      const result = category === 'Base Paper'
        ? await uploadStudentBasePaper(file, name.trim())
        : await uploadStudentDocument(file, category, name.trim())
      await onDone((result as any)?.message ?? `${name.trim()} uploaded.`)
    } catch (err) {
      setProblem(fileError(err, 'That file could not be uploaded.'))
      setBusy(false)
    }
  }

  const ready = Boolean(file) && Boolean(name.trim()) && Boolean(category)

  return (
    <div role="dialog" aria-modal="true" aria-label="Upload document"
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:items-center">
      <div className="w-full max-w-[620px] rounded-xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-[#E5E7EB] px-4 py-3">
          <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Upload document</h2>
          <button type="button" onClick={onClose} aria-label="Close"
            className="flex h-7 w-7 items-center justify-center rounded text-[#6B7280] hover:bg-[#F3F4F6]">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-3 p-4">
          <label
            onDragOver={(e) => { e.preventDefault(); setOver(true) }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setOver(false)
              const picked = e.dataTransfer.files?.[0]
              if (picked) accept(picked)
            }}
            className={cn('flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors',
              over ? 'border-[#2563EB] bg-[#EFF6FF]' : 'border-[#C7D2FE] bg-[#F9FAFC]')}>
            <input type="file" className="sr-only" accept={limits.accept}
              onChange={(e) => {
                const picked = e.target.files?.[0]
                if (picked) accept(picked)
                e.target.value = ''
              }} />
            {file ? (
              <>
                {(() => {
                  const kind = fileKind(file.name)
                  return <kind.icon className={cn('h-7 w-7', kind.tone)} />
                })()}
                <span className="mt-1.5 text-[12.5px] font-medium text-[#1B1B3A]">
                  {file.name}
                </span>
                <span className="text-[11px] text-[#6B7280]">
                  {humanSize(file.size)} · click to choose a different file
                </span>
              </>
            ) : (
              <>
                <UploadCloud className="h-7 w-7 text-[#2563EB]" />
                <span className="mt-1.5 text-[12.5px] font-medium text-[#1B1B3A]">
                  Drag and drop your file here
                </span>
                <span className="my-1 text-[11px] text-[#9CA3AF]">or</span>
                <span className="rounded-lg bg-[#2563EB] px-3 py-1.5 text-[12px] font-medium text-white">
                  Choose file
                </span>
              </>
            )}
            <span className="mt-2 text-[10.5px] text-[#6B7280]">
              Max {limits.max_mb} MB · {(limits.extensions ?? []).join(', ')}
            </span>
          </label>

          {problem && (
            <p className="flex items-start gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-2 text-[11.5px] text-[#B91C1C]">
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {problem}
            </p>
          )}

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-[#374151]">
                Document name <span className="text-[#B91C1C]">*</span>
              </span>
              <input value={name} onChange={(e) => setName(e.target.value)}
                placeholder="Enter document name"
                className="h-9 rounded-lg border border-[#D1D5DB] px-2.5 text-[12px] text-[#1B1B3A] placeholder:text-[#9CA3AF] focus:border-[#2563EB] focus:outline-none" />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-[11px] text-[#374151]">
                Document type <span className="text-[#B91C1C]">*</span>
              </span>
              <select value={category} onChange={(e) => setCategory(e.target.value)}
                className="h-9 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[12px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
                {docs.categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </label>
          </div>

          <label className="flex flex-col gap-1">
            <span className="text-[11px] text-[#374151]">Project</span>
            <span className="flex h-9 items-center rounded-lg border border-[#E5E7EB] bg-[#F9FAFC] px-2.5 text-[12px] text-[#6B7280]">
              {project}
            </span>
          </label>

          <p className="flex items-start gap-2 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[11px] text-[#1E3A8A]">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2563EB]" />
            <span>
              Your guide sees this for review and approval. Uploading a type you
              have already sent creates a new version — the earlier one is kept.
            </span>
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-[#E5E7EB] px-4 py-3">
          <button type="button" onClick={onClose} disabled={busy}
            className="h-9 rounded-lg border border-[#D1D5DB] bg-white px-3.5 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-50">
            Cancel
          </button>
          <button type="button" onClick={submit} disabled={!ready || busy}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-[#2563EB] px-3.5 text-[12px] font-medium text-white hover:bg-[#1D4ED8] disabled:opacity-40">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Upload className="h-4 w-4" />}
            Upload document
          </button>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-[10.5px] text-[#6B7280]">{label}</span>
      <span className={cn('text-[13px] font-bold', tone ?? 'text-[#1B1B3A]')}>
        {value}
      </span>
    </span>
  )
}

function Action({ label, onClick, disabled, danger, children }: {
  label: string; onClick: () => void; disabled?: boolean; danger?: boolean
  children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      aria-label={label} title={label}
      className={cn('flex h-7 w-7 items-center justify-center rounded border border-[#E5E7EB] bg-white hover:bg-[#F9FAFB] disabled:opacity-40',
        danger ? 'text-[#B91C1C] hover:border-[#FECACA]' : 'text-[#2563EB]')}>
      {children}
    </button>
  )
}

function Pager({ label, disabled, onClick, children }: {
  label: string; disabled: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      title={label}
      className="flex h-7 w-7 items-center justify-center rounded border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-30">
      {children}
    </button>
  )
}
