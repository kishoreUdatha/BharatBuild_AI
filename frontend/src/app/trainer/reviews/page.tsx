'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, CalendarClock, CheckCircle2 } from 'lucide-react'
import {
  CARD, Chip, Empty, Failed, FilterTabs, KpiRow, Loading, PageHeader, fmtDate,
} from '@/components/trainer/primitives'
import {
  cancelReview, completeReview, errorText, fetchTrainerReviews, rescheduleReview,
} from '@/lib/trainer-api'
import type { Kpi, ReviewRow } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'overdue', label: 'Overdue' },
  { key: 'scheduled', label: 'Scheduled' },
  { key: 'completed', label: 'Completed' },
]

/** How far out a review is, said the way a person would say it. */
function when(row: ReviewRow) {
  if (row.status === 'completed') return `Completed ${fmtDate(row.completed_at)}`
  const d = row.days_out
  if (d < 0) return `${Math.abs(d)} day${Math.abs(d) === 1 ? '' : 's'} overdue`
  if (d === 0) return 'Due today'
  return `In ${d} day${d === 1 ? '' : 's'}`
}

/** Opens on the filter the link asked for, so a worklist card lands on its own rows. */
function initialTab(allowed: string[], fallback: string) {
  if (typeof window === 'undefined') return fallback
  const wanted = new URLSearchParams(window.location.search).get('status')
  return wanted && allowed.includes(wanted) ? wanted : fallback
}

export default function TrainerReviewsPage() {
  const [data, setData] = useState<{ rows: ReviewRow[]; kpis: Kpi[] } | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState(() =>
    initialTab(TABS.map((t) => t.key), 'all'))
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  // Which review is open for a decision, and the values being entered.
  const [open, setOpen] = useState<string | null>(null)
  const [form, setForm] = useState({ score: '', remarks: '', when: '', reason: '' })

  const load = useCallback(async () => {
    setError('')
    try { setData(await fetchTrainerReviews(tab)) }
    catch (err: any) { setError(errorText(err, 'Could not load your reviews.')) }
  }, [tab])

  useEffect(() => { load() }, [load])

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    try {
      await fn()
      setNotice(ok)
      setOpen(null)
      setForm({ score: '', remarks: '', when: '', reason: '' })
      await load()
    } catch (err: any) {
      setNotice(errorText(err, 'That decision could not be recorded.'))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading reviews…" />

  return (
    <div className="space-y-3">
      <PageHeader
        title="Project Reviews"
        subtitle="Every review scheduled against a batch you are responsible for."
      />
      <KpiRow kpis={data.kpis} />

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-[12.5px] text-[#1E40AF]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium">Dismiss</button>
        </div>
      )}

      <FilterTabs options={TABS} value={tab} onChange={setTab} />

      {data.rows.length === 0 ? (
        <Empty message={tab === 'all'
          ? 'No reviews are scheduled against your batches.'
          : `No ${tab} reviews.`} />
      ) : (
        <ul className="space-y-2">
          {data.rows.map((r) => {
            const overdue = r.status === 'overdue'
            const done = r.status === 'completed'
            return (
              <li key={r.id} className={cn(CARD, 'flex flex-wrap items-center gap-3 p-3.5',
                overdue && 'border-[#FECACA]')}>
                <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                  overdue ? 'bg-[#FEF2F2] text-[#DC2626]'
                    : done ? 'bg-[#F0FDF4] text-[#16A34A]' : 'bg-[#EFF6FF] text-[#2563EB]')}>
                  {overdue ? <AlertTriangle className="h-4 w-4" />
                    : done ? <CheckCircle2 className="h-4 w-4" />
                      : <CalendarClock className="h-4 w-4" />}
                </span>

                <span className="min-w-[190px] flex-1">
                  <span className="block text-[13px] font-semibold text-[#1B1B3A]">{r.review_type}</span>
                  <span className="block text-[11.5px] text-[#6B7280]">
                    {r.batch_code} &middot; {r.batch_title ?? 'Untitled'} &middot; Section {r.section ?? '—'}
                  </span>
                </span>

                <span className="min-w-[130px]">
                  <span className="block text-[11px] text-[#9CA3AF]">Scheduled</span>
                  <span className="block text-[12px] font-medium text-[#1B1B3A]">
                    {fmtDate(r.scheduled_at)}
                  </span>
                </span>

                <span className={cn('min-w-[110px] text-[12px] font-medium',
                  overdue ? 'text-[#DC2626]' : done ? 'text-[#15803D]' : 'text-[#4B5563]')}>
                  {when(r)}
                </span>

                {r.score != null && (
                  <span className="min-w-[64px]">
                    <span className="block text-[11px] text-[#9CA3AF]">Score</span>
                    <span className="block text-[12px] font-medium text-[#1B1B3A]">{r.score}</span>
                  </span>
                )}

                <Chip tone={overdue ? 'red' : done ? 'green' : 'blue'}>{r.status_label}</Chip>

                {r.can_complete && (
                  <button type="button"
                    onClick={() => setOpen(open === r.id ? null : r.id)}
                    aria-expanded={open === r.id}
                    className="rounded-lg bg-[#2563EB] px-3 py-1.5 text-[11.5px] font-medium text-white hover:bg-[#1D4ED8]">
                    {open === r.id ? 'Close' : 'Record outcome'}
                  </button>
                )}

                <Link href={`/faculty/registrations/${encodeURIComponent(r.batch_code)}`}
                  className="rounded-lg border border-[#D1D5DB] px-3 py-1.5 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                  Open batch
                </Link>

                {open === r.id && (
                  <div className="w-full border-t border-[#F1F2F8] pt-3">
                    <div className="grid gap-3 lg:grid-cols-[92px_minmax(0,1.6fr)_minmax(0,1fr)]">
                      <label className="block">
                        <span className="mb-1 block text-[11px] text-[#6B7280]">Score</span>
                        <input type="number" min={0} max={100} value={form.score}
                          onChange={(e) => setForm((f) => ({ ...f, score: e.target.value }))}
                          className="h-8 w-full rounded-lg border border-[#D1D5DB] px-2 text-[12px] outline-none focus:border-[#2563EB]" />
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-[11px] text-[#6B7280]">Remarks</span>
                        <input value={form.remarks}
                          onChange={(e) => setForm((f) => ({ ...f, remarks: e.target.value }))}
                          placeholder="What came out of the review?"
                          className="h-8 w-full rounded-lg border border-[#D1D5DB] px-2 text-[12px] outline-none focus:border-[#2563EB]" />
                      </label>
                      <label className="block">
                        <span className="mb-1 block text-[11px] text-[#6B7280]">Move to</span>
                        <input type="date" value={form.when}
                          onChange={(e) => setForm((f) => ({ ...f, when: e.target.value }))}
                          className="h-8 w-full rounded-lg border border-[#D1D5DB] px-2 text-[12px] outline-none focus:border-[#2563EB]" />
                      </label>
                    </div>

                    <div className="mt-2.5 flex flex-wrap items-center gap-2">
                      <button type="button" disabled={busy}
                        onClick={() => act(() => completeReview(r.batch_code, r.id, {
                          score: form.score === '' ? undefined : Number(form.score),
                          remarks: form.remarks || undefined,
                        }), `${r.review_type} recorded as completed.`)}
                        className="rounded-lg bg-[#16A34A] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#15803D] disabled:opacity-50">
                        Mark completed
                      </button>
                      <button type="button" disabled={busy || !form.when}
                        onClick={() => act(() => rescheduleReview(r.batch_code, r.id,
                          new Date(`${form.when}T10:00:00`).toISOString()),
                          `${r.review_type} moved.`)}
                        title={form.when ? undefined : 'Pick a date first'}
                        className="rounded-lg border border-[#BFDBFE] px-3.5 py-2 text-[12px] font-medium text-[#2563EB] hover:bg-[#EFF6FF] disabled:opacity-40">
                        Reschedule
                      </button>
                      <input value={form.reason}
                        onChange={(e) => setForm((f) => ({ ...f, reason: e.target.value }))}
                        placeholder="Reason, if cancelling"
                        className="h-9 min-w-[190px] flex-1 rounded-lg border border-[#D1D5DB] px-2.5 text-[12px] outline-none focus:border-[#DC2626]" />
                      <button type="button" disabled={busy || form.reason.trim().length < 4}
                        onClick={() => act(() => cancelReview(r.batch_code, r.id, form.reason.trim()),
                          `${r.review_type} cancelled.`)}
                        title={form.reason.trim().length < 4 ? 'Give a reason first' : undefined}
                        className="rounded-lg border border-[#FECACA] px-3.5 py-2 text-[12px] font-medium text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-40">
                        Cancel review
                      </button>
                    </div>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      <p className="text-[11.5px] text-[#9CA3AF]">
        Outcomes recorded here write the same review record the Faculty Portal reads, through the
        same rules — a completed review cannot be completed twice or moved afterwards.
      </p>
    </div>
  )
}
