'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { fetchBatchBuilder, openBatchBuilder } from '@/lib/trainer-api'
import { TeamBuilderCard } from '@/components/project/TeamBuilderCard'
import {
  Check, ChevronDown, ChevronRight, Download, ExternalLink, FileText, Loader2, Undo2,
} from 'lucide-react'
import {
  decideSubmission, downloadBatchSubmission, submissionError, submitForBatch,
  type SubmissionRow,
} from '@/lib/submissions-api'
import {
  Bar, CARD, Chip, Empty, Failed, KpiRow, Loading, PageHeader, fmtDate,
} from '@/components/trainer/primitives'
import { errorText, fetchStudentWork } from '@/lib/trainer-api'
import type { Kpi, WorkBatch } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

export default function StudentWorkPage() {
  const [data, setData] = useState<{ rows: WorkBatch[]; kpis: Kpi[] } | null>(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState<string | null>(null)
  const [notice, setNotice] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const result = await fetchStudentWork()
      setData(result)
      // Open the batch with work waiting, since that is why you came.
      setOpen((cur) => cur ?? (result.rows.find((r) => r.pending_submissions > 0)
        ?? result.rows[0])?.batch_code ?? null)
    } catch (err: any) { setError(errorText(err, 'Could not load student work.')) }
  }, [])

  useEffect(() => { load() }, [load])

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading student work…" />

  return (
    <div className="space-y-3">
      <PageHeader
        title="Student Work"
        subtitle="Team composition, stage progress and what each batch has submitted."
      />
      <KpiRow kpis={data.kpis} />

      {notice && (
        <p className="flex items-start justify-between gap-2 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[12.5px] text-[#1E40AF]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')}
            className="shrink-0 font-medium hover:underline">Dismiss</button>
        </p>
      )}

      {data.rows.length === 0 ? (
        <Empty message="You are not assigned to any batches this academic year." />
      ) : (
        <ul className="space-y-2">
          {data.rows.map((b) => {
            const expanded = open === b.batch_code
            return (
              <li key={b.batch_code} className={cn(CARD, 'overflow-hidden')}>
                <button type="button"
                  onClick={() => setOpen(expanded ? null : b.batch_code)}
                  aria-expanded={expanded}
                  className="flex w-full flex-wrap items-center gap-3 p-3.5 text-left hover:bg-[#FAFBFE]">
                  {expanded ? <ChevronDown className="h-4 w-4 shrink-0 text-[#9CA3AF]" />
                    : <ChevronRight className="h-4 w-4 shrink-0 text-[#9CA3AF]" />}
                  <span className="min-w-[180px] flex-1">
                    <span className="block text-[13px] font-semibold text-[#1B1B3A]">
                      {b.batch_code} <span className="font-normal text-[#6B7280]">
                        &middot; {b.title ?? 'Untitled'}</span>
                    </span>
                    <span className="block text-[11.5px] text-[#9CA3AF]">
                      Section {b.section ?? '—'} &middot; {b.members.length} students
                    </span>
                  </span>
                  <span className="w-[150px]">
                    <span className="flex items-center justify-between text-[11px] text-[#6B7280]">
                      <span>Progress</span>
                      <span className="font-medium text-[#1B1B3A]">{b.progress}%</span>
                    </span>
                    <span className="mt-1 block"><Bar value={b.progress} /></span>
                  </span>
                  {b.pending_submissions > 0
                    ? <Chip tone="amber">{b.pending_submissions} awaiting review</Chip>
                    : <Chip tone="green">Nothing waiting</Chip>}
                </button>

                {expanded && (
                  <div className="grid gap-5 border-t border-[#F1F2F8] p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1.1fr)]">
                    <div>
                      <p className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">Team</p>
                      <ul className="space-y-1">
                        {b.members.map((m) => (
                          <li key={m.roll_number ?? m.name} className="text-[11.5px] text-[#4B5563]">
                            <span className="font-medium text-[#1B1B3A]">{m.name}</span>
                            {m.is_lead && <span className="ml-1"><Chip tone="blue">Lead</Chip></span>}
                            {m.responsibility && (
                              <span className="block text-[10.5px] text-[#9CA3AF]">{m.responsibility}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <p className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">Stage progress</p>
                      <ul className="space-y-1.5">
                        {b.stages.map((s) => (
                          <li key={s.stage} className="flex items-center gap-2">
                            <span className="w-[104px] shrink-0 truncate text-[10.5px] text-[#4B5563]"
                              title={s.stage}>{s.stage}</span>
                            <span className="flex-1"><Bar value={s.percent}
                              tone={s.complete ? 'bg-[#16A34A]' : 'bg-[#2563EB]'} /></span>
                            <span className="w-[32px] shrink-0 text-right text-[10.5px] text-[#6B7280]">
                              {s.percent}%
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <p className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">Recent submissions</p>
                      {b.submissions.length === 0 ? (
                        <p className="text-[11.5px] text-[#9CA3AF]">Nothing submitted yet.</p>
                      ) : (
                        <ul className="space-y-1.5">
                          {b.submissions.map((s) => (
                            <SubmissionItem key={s.id} code={b.batch_code} row={s}
                              onNotice={setNotice} onChanged={load} />
                          ))}
                        </ul>
                      )}
                      <OnBehalf code={b.batch_code}
                        onNotice={setNotice} onChanged={load} />
                      <Link href={`/faculty/registrations/${encodeURIComponent(b.batch_code)}`}
                        className="mt-2.5 inline-block text-[11.5px] font-medium text-[#2563EB] hover:underline">
                        Open batch documents
                      </Link>

                      <div className="mt-3">
                        <TeamBuilderCard
                          batchCode={b.batch_code}
                          load={() => fetchBatchBuilder(b.batch_code)}
                          open={() => openBatchBuilder(b.batch_code)}
                          readOnlyNote="The team starts this themselves, or you can." />
                      </div>
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}


/**
 * One submission, with the two things a reviewer does to it.
 *
 * Sending work back asks for a reason before it will go: the server refuses a
 * rejection without one, and a team told only "rejected" has nothing to act on.
 */
function SubmissionItem({ code, row, onNotice, onChanged }: {
  code: string
  row: SubmissionRow
  onNotice: (message: string) => void
  onChanged: () => void
}) {
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  const decide = async (decision: 'verify' | 'reject') => {
    setBusy(true)
    try {
      const result = await decideSubmission(code, row.id, decision, note.trim() || undefined)
      onNotice(result.message)
      setRejecting(false)
      setNote('')
      onChanged()
    } catch (err) {
      onNotice(submissionError(err, 'That decision could not be recorded.'))
    } finally {
      setBusy(false)
    }
  }

  const download = async () => {
    if (!row.file) return
    try { await downloadBatchSubmission(code, row.id, row.file.name) }
    catch (err) { onNotice(submissionError(err, 'That file could not be downloaded.')) }
  }

  const meta = [row.stage_label, row.submitted_by, fmtDate(row.submitted_at),
    row.file?.size_label, row.link ? 'link' : null].filter(Boolean).join(' \u00b7 ')

  return (
    <li className={cn('rounded-lg border border-[#EEF0F7] px-2.5 py-2', row.superseded && 'opacity-60')}>
      <div className="flex flex-wrap items-center gap-2">
        <FileText className="h-3.5 w-3.5 shrink-0 text-[#9CA3AF]" />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[11.5px] text-[#1B1B3A]">
            {row.title ?? row.document_type}
            <span className="ml-1.5 text-[10px] text-[#9CA3AF]">{row.version}</span>
          </span>
          <span className="block text-[10px] text-[#9CA3AF]">{meta}</span>
          {row.faculty_note && (
            <span className="mt-0.5 block text-[10.5px] text-[#B45309]">{row.faculty_note}</span>
          )}
        </span>

        {row.link && (
          <a href={row.link} target="_blank" rel="noopener noreferrer" title={row.link}
            aria-label="Open the submitted link"
            className="shrink-0 rounded-md border border-[#E5E7EB] p-1 text-[#2563EB] hover:bg-[#F7F8FC]">
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        {row.file && (
          <button type="button" onClick={download} aria-label={`Download ${row.file.name}`}
            className="shrink-0 rounded-md border border-[#E5E7EB] p-1 text-[#2563EB] hover:bg-[#F7F8FC]">
            <Download className="h-3.5 w-3.5" />
          </button>
        )}

        <Chip tone={row.status === 'verified' ? 'green'
          : row.status === 'rejected' ? 'red' : 'amber'}>
          {row.status_label}
        </Chip>

        {row.can_decide && (
          <span className="flex shrink-0 gap-1.5">
            <button type="button" disabled={busy} onClick={() => decide('verify')}
              className="flex items-center gap-1 rounded-md border border-[#BBF7D0] bg-[#F0FDF4] px-2 py-0.5 text-[10.5px] font-medium text-[#15803D] disabled:opacity-50">
              {busy ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
              Accept
            </button>
            <button type="button" disabled={busy}
              onClick={() => { setRejecting((v) => !v); setNote('') }}
              className="flex items-center gap-1 rounded-md border border-[#FDE68A] bg-[#FFFBEB] px-2 py-0.5 text-[10.5px] font-medium text-[#B45309] disabled:opacity-50">
              <Undo2 className="h-3 w-3" /> Send back
            </button>
          </span>
        )}
      </div>

      {rejecting && (
        <div className="mt-2 flex flex-wrap items-start gap-1.5 border-t border-[#EEF0F7] pt-2">
          <input value={note} onChange={(e) => setNote(e.target.value)} autoFocus
            placeholder="What has to change before they resubmit?"
            onKeyDown={(e) => { if (e.key === 'Enter' && note.trim()) decide('reject') }}
            className="min-w-[220px] flex-1 rounded-lg border border-[#DDE0EE] px-2.5 py-1.5 text-[11.5px] outline-none focus:border-[#2563EB]" />
          <button type="button" disabled={busy || !note.trim()} onClick={() => decide('reject')}
            className="rounded-lg bg-[#B45309] px-2.5 py-1.5 text-[11.5px] font-medium text-white disabled:opacity-40">
            Send back
          </button>
          <button type="button" onClick={() => { setRejecting(false); setNote('') }}
            className="rounded-lg border border-[#DDE0EE] px-2.5 py-1.5 text-[11.5px] text-[#6B7280]">
            Cancel
          </button>
        </div>
      )}
    </li>
  )
}


/**
 * Filing a deliverable a team handed over outside the portal.
 *
 * Happens constantly - work arrives by email, on a pen drive, in person. With
 * no way to record it the stage never advances and the tracking numbers drift
 * away from what actually happened.
 */
function OnBehalf({ code, onNotice, onChanged }: {
  code: string
  onNotice: (message: string) => void
  onChanged: () => void
}) {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState('Synopsis')
  const [file, setFile] = useState<File | null>(null)
  const [busy, setBusy] = useState(false)

  const TYPES = ['Synopsis', 'Literature Survey', 'SRS', 'System Design',
    'Source Code', 'Test Report', 'Project Report', 'Presentation']

  const send = async () => {
    if (!file) return
    setBusy(true)
    try {
      const result = await submitForBatch(code, type, file)
      onNotice(`${result.message} Filed on the team's behalf.`)
      setFile(null); setOpen(false)
      onChanged()
    } catch (err) {
      onNotice(submissionError(err, 'That could not be filed.'))
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        className="mt-2.5 mr-3 inline-block text-[11.5px] font-medium text-[#2563EB] hover:underline">
        File work on their behalf
      </button>
    )
  }

  return (
    <div className="mt-2.5 space-y-1.5 rounded-lg border border-[#E5E7EB] bg-[#FAFBFE] p-2">
      <select value={type} onChange={(e) => setType(e.target.value)}
        className="h-7 w-full rounded-lg border border-[#DDE0EE] bg-white px-2 text-[11.5px] outline-none">
        {TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
      </select>
      <input type="file" accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.csv,.png,.jpg,.jpeg"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="w-full text-[11px] text-[#5A5F7A]" />
      <div className="flex gap-1.5">
        <button type="button" onClick={send} disabled={busy || !file}
          className="flex items-center gap-1 rounded-lg bg-[#2563EB] px-2.5 py-1 text-[11px] font-medium text-white disabled:opacity-40">
          {busy && <Loader2 className="h-3 w-3 animate-spin" />} File it
        </button>
        <button type="button" onClick={() => { setOpen(false); setFile(null) }}
          className="rounded-lg border border-[#DDE0EE] px-2.5 py-1 text-[11px] text-[#6B7280]">
          Cancel
        </button>
      </div>
      <p className="text-[10px] text-[#9CA3AF]">
        Recorded as submitted by you, and still needs accepting like any other.
      </p>
    </div>
  )
}
