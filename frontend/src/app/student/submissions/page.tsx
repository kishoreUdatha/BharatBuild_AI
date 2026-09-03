'use client'

import Link from 'next/link'
import { useCallback, useEffect, useRef, useState } from 'react'
import {
  AlertCircle, Check, Download, ExternalLink, FileText, Link2,
  Loader2, Lock, Paperclip, Send, Trash2, X,
} from 'lucide-react'
import {
  downloadMySubmission,
  fetchMySubmissions,
  submissionError,
  submitWork,
  withdrawSubmission,
  type Deliverable,
  type SubmissionList,
  type SubmissionRow,
} from '@/lib/submissions-api'
import { checkFile } from '@/lib/file-api'
import { cn } from '@/lib/utils'

const ACCENT = '#2563EB'
const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'

/**
 * Submissions - the work itself, handed in stage by stage.
 *
 * Separate from Documents, which proves the batch is properly formed. What is
 * accepted here is what moves the project's tracked progress, so the eight
 * deliverables lead and the history sits underneath.
 */
export default function StudentSubmissionsPage() {
  const [data, setData] = useState<SubmissionList | null>(null)
  const [blocked, setBlocked] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [openFor, setOpenFor] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setData(await fetchMySubmissions())
      setBlocked('')
    } catch (err) {
      setBlocked(submissionError(err, 'Your submissions are not available yet.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const withdraw = async (row: SubmissionRow) => {
    try {
      const result = await withdrawSubmission(row.id)
      setNotice(result.message)
      load()
    } catch (err) {
      setNotice(submissionError(err, 'That could not be withdrawn.'))
    }
  }

  const download = async (row: SubmissionRow) => {
    if (!row.file) return
    try { await downloadMySubmission(row.id, row.file.name) }
    catch (err) { setNotice(submissionError(err, 'That file could not be downloaded.')) }
  }

  if (loading) {
    return (
      <div className={cn(CARD, 'flex items-center gap-2 p-8 text-[12.5px] text-[#6B7280]')}>
        <Loader2 className="h-4 w-4 animate-spin text-[#2563EB]" /> Loading your submissions…
      </div>
    )
  }

  if (blocked || !data) {
    return (
      <div className="space-y-3">
        <Header />
        <section className={cn(CARD, 'p-8 text-center')}>
          <Lock className="mx-auto h-8 w-8 text-[#C7CBDD]" />
          <h2 className="mt-3 text-[16px] font-semibold text-[#1B1B3A]">Submissions are not open</h2>
          <p className="mx-auto mt-1.5 max-w-md text-[12.5px] leading-snug text-[#6B7280]">{blocked}</p>
          <Link href="/student/registration"
            className="mt-4 inline-block rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
            Go to registration
          </Link>
        </section>
      </div>
    )
  }

  const latest = (type: string) =>
    data.rows.find((r) => r.document_type === type && !r.superseded) ?? null

  return (
    <div className="space-y-3">
      <Header batch={data.batch_code} progress={data.overall_progress} />

      {notice && (
        <p className="flex items-start justify-between gap-2 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[12.5px] text-[#1E40AF]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')}
            className="shrink-0 font-medium hover:underline">Dismiss</button>
        </p>
      )}

      <section className={cn(CARD, 'p-4')}>
        <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-[13px] font-semibold text-[#1B1B3A]">What your project needs</h2>
          <span className="text-[11.5px] text-[#6B7280]">
            {data.deliverables.filter((d) => d.status === 'verified').length} of{' '}
            {data.deliverables.length} accepted
            {data.pending > 0 && ` · ${data.pending} with your guide`}
          </span>
        </div>

        <ul className="space-y-1.5">
          {data.deliverables.map((d) => (
            <DeliverableRow
              key={d.document_type}
              deliverable={d}
              current={latest(d.document_type)}
              limits={data.limits}
              open={openFor === d.document_type}
              onToggle={() => setOpenFor(openFor === d.document_type ? null : d.document_type)}
              onSubmitted={(message) => { setNotice(message); setOpenFor(null); load() }}
              onDownload={download}
              onWithdraw={withdraw} />
          ))}
        </ul>
      </section>

      {data.rows.some((r) => r.superseded) && (
        <section className={cn(CARD, 'p-4')}>
          <h2 className="mb-2 text-[13px] font-semibold text-[#1B1B3A]">
            Earlier attempts
            <span className="ml-2 font-normal text-[11.5px] text-[#8A8FA8]">
              kept so you can see what was asked for
            </span>
          </h2>
          <ul className="divide-y divide-[#F1F2F8]">
            {data.rows.filter((r) => r.superseded).map((r) => (
              <li key={r.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2 opacity-70">
                <FileText className="h-3.5 w-3.5 shrink-0 text-[#9CA3AF]" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[12px] text-[#1B1B3A]">
                    {r.document_type} <span className="text-[11px] text-[#8A8FA8]">{r.version}</span>
                  </span>
                  {r.faculty_note && (
                    <span className="block text-[11px] text-[#B45309]">
                      {r.reviewed_by ?? 'Guide'}: {r.faculty_note}
                    </span>
                  )}
                </span>
                <StatusChip status={r.status} label={r.status_label} />
                {r.file && (
                  <button type="button" onClick={() => download(r)} aria-label={`Download ${r.file.name}`}
                    className="shrink-0 rounded-md border border-[#DDE0EE] p-1 text-[#2563EB] hover:bg-[#F7F8FC]">
                    <Download className="h-3.5 w-3.5" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}

function Header({ batch, progress }: { batch?: string; progress?: number }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-2">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">Submissions</h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
          The work itself, handed in stage by stage. What your guide accepts moves your progress.
        </p>
      </div>
      {batch && (
        <span className="flex items-center gap-2 text-[11.5px]">
          <span className="rounded-md border border-[#DDE0EE] px-2 py-0.5 font-medium text-[#3A3F58]">
            {batch}
          </span>
          <span className="text-[#6B7280]">{progress}% complete</span>
        </span>
      )}
    </div>
  )
}

function DeliverableRow({
  deliverable, current, limits, open, onToggle, onSubmitted, onDownload, onWithdraw,
}: {
  deliverable: Deliverable
  current: SubmissionRow | null
  limits: SubmissionList['limits']
  open: boolean
  onToggle: () => void
  onSubmitted: (message: string) => void
  onDownload: (row: SubmissionRow) => void
  onWithdraw: (row: SubmissionRow) => void
}) {
  const accepted = deliverable.status === 'verified'
  return (
    <li className="rounded-lg border border-[#EEF0F7]">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF] text-[10.5px] font-semibold text-[#2563EB]">
          {deliverable.position}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-[12.5px] font-medium text-[#1B1B3A]">
            {deliverable.document_type}
            {deliverable.version && (
              <span className="ml-1.5 text-[11px] font-normal text-[#8A8FA8]">
                {deliverable.version}
              </span>
            )}
          </span>
          <span className="block text-[11px] text-[#8A8FA8]">
            {deliverable.stage_label} stage
            {current?.link && ' · submitted as a link'}
            {current?.file && ` · ${current.file.size_label}`}
          </span>
          {current?.faculty_note && current.status === 'rejected' && (
            <span className="mt-0.5 block text-[11px] text-[#B45309]">
              {current.reviewed_by ?? 'Guide'}: {current.faculty_note}
            </span>
          )}
        </span>

        <StatusChip status={deliverable.status} label={
          deliverable.status === 'not_submitted' ? 'not submitted'
            : current?.status_label ?? deliverable.status} />

        {current?.link && (
          <a href={current.link} target="_blank" rel="noopener noreferrer"
            title={current.link} aria-label="Open the submitted link"
            className="shrink-0 rounded-md border border-[#DDE0EE] p-1 text-[#2563EB] hover:bg-[#F7F8FC]">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        {current?.file && (
          <button type="button" onClick={() => onDownload(current)}
            aria-label={`Download ${current.file.name}`}
            className="shrink-0 rounded-md border border-[#DDE0EE] p-1 text-[#2563EB] hover:bg-[#F7F8FC]">
            <Download className="h-3.5 w-3.5" />
          </button>
        )}
        {current?.can_withdraw && (
          <button type="button" onClick={() => onWithdraw(current)}
            title="Take this back" aria-label={`Withdraw ${deliverable.document_type}`}
            className="shrink-0 rounded-md border border-[#DDE0EE] p-1 text-[#8A8FA8] hover:border-[#FECACA] hover:text-[#DC2626]">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        )}

        {accepted ? (
          <span title="Accepted work is fixed; ask your guide to reopen it"
            className="shrink-0 p-1 text-[#C7CBDD]"><Lock className="h-3.5 w-3.5" /></span>
        ) : (
          <button type="button" onClick={onToggle}
            className="shrink-0 rounded-lg border px-2.5 py-1 text-[11.5px] font-medium"
            style={{ borderColor: ACCENT, color: ACCENT }}>
            {open ? 'Cancel' : deliverable.status === 'not_submitted' ? 'Submit' : 'Resubmit'}
          </button>
        )}
      </div>

      {open && !accepted && (
        <div className="border-t border-[#EEF0F7] px-3 py-2.5">
          <SubmitForm
            documentType={deliverable.document_type}
            limits={limits}
            onDone={onSubmitted} />
        </div>
      )}
    </li>
  )
}

/** File or link, never both — the server refuses both and refuses neither. */
function SubmitForm({ documentType, limits, onDone }: {
  documentType: string
  limits: SubmissionList['limits']
  onDone: (message: string) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<'file' | 'link'>('file')
  const [file, setFile] = useState<File | null>(null)
  const [link, setLink] = useState('')
  const [title, setTitle] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const pick = (chosen: File | null) => {
    setError('')
    if (!chosen) { setFile(null); return }
    const problem = checkFile(chosen, limits)
    if (problem) { setError(problem); setFile(null); return }
    setFile(chosen)
  }

  const send = async () => {
    setBusy(true); setError('')
    try {
      const result = await submitWork(
        documentType, mode === 'file' ? file : null, mode === 'link' ? link : '',
        title.trim() || undefined)
      onDone(result.message)
    } catch (err) {
      setError(submissionError(err, 'That could not be submitted.'))
    } finally {
      setBusy(false)
    }
  }

  const ready = mode === 'file' ? !!file : !!link.trim()

  return (
    <div className="space-y-2">
      <div className="flex gap-1.5">
        {(['file', 'link'] as const).map((m) => (
          <button key={m} type="button" onClick={() => { setMode(m); setError('') }}
            className={cn('flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[11.5px] font-medium',
              mode === m ? 'border-[#2563EB] bg-[#EFF6FF] text-[#2563EB]'
                : 'border-[#DDE0EE] text-[#6B7280]')}>
            {m === 'file' ? <Paperclip className="h-3.5 w-3.5" /> : <Link2 className="h-3.5 w-3.5" />}
            {m === 'file' ? 'Upload a file' : 'Give a link'}
          </button>
        ))}
      </div>

      {mode === 'file' ? (
        <div className="flex flex-wrap items-center gap-2">
          <input ref={input} type="file" accept={limits.accept} className="hidden"
            onChange={(e) => pick(e.target.files?.[0] ?? null)} />
          <button type="button" onClick={() => input.current?.click()}
            className="rounded-lg border border-[#DDE0EE] px-2.5 py-1.5 text-[11.5px] font-medium text-[#2563EB]">
            Choose file
          </button>
          {file ? (
            <span className="flex items-center gap-1.5 text-[11.5px] text-[#1B1B3A]">
              <span className="max-w-[240px] truncate">{file.name}</span>
              <span className="text-[#8A8FA8]">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
              <button type="button" aria-label="Clear" onClick={() => pick(null)}
                className="text-[#C7CBDD] hover:text-[#DC2626]"><X className="h-3.5 w-3.5" /></button>
            </span>
          ) : (
            <span className="text-[11px] text-[#8A8FA8]">
              {limits.extensions.join(', ')}, up to {limits.max_mb} MB
            </span>
          )}
        </div>
      ) : (
        <input value={link} onChange={(e) => setLink(e.target.value)}
          placeholder="https://github.com/your-team/project"
          className="w-full rounded-lg border border-[#DDE0EE] px-2.5 py-1.5 text-[12.5px] outline-none focus:border-[#2563EB]" />
      )}

      <input value={title} onChange={(e) => setTitle(e.target.value)}
        placeholder="A short title (optional)"
        className="w-full rounded-lg border border-[#DDE0EE] px-2.5 py-1.5 text-[12.5px] outline-none focus:border-[#2563EB]" />

      {error && (
        <p className="flex items-start gap-1.5 text-[11px] leading-snug text-[#DC2626]">
          <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}

      <button type="button" onClick={send} disabled={busy || !ready}
        className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[12px] font-medium text-white disabled:opacity-40"
        style={{ background: ACCENT }}>
        {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
        Hand in {documentType}
      </button>
    </div>
  )
}

function StatusChip({ status, label }: { status: string; label: string }) {
  const tone = status === 'verified' ? 'bg-[#DCFCE7] text-[#15803D]'
    : status === 'rejected' ? 'bg-[#FEE2E2] text-[#B91C1C]'
      : status === 'pending' ? 'bg-[#FEF3C7] text-[#B45309]'
        : 'bg-[#F3F4F6] text-[#6B7280]'
  return (
    <span className={cn('shrink-0 whitespace-nowrap rounded px-2 py-0.5 text-[10.5px] font-medium', tone)}>
      {status === 'verified' && <Check className="mr-0.5 inline h-3 w-3 align-[-2px]" />}
      {label}
    </span>
  )
}
