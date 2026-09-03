'use client'

import { useState } from 'react'
import {
  AlertCircle, CalendarPlus, Check, Clock, Loader2, Undo2, X, XCircle,
} from 'lucide-react'
import {
  cancelReview,
  completeReview,
  rescheduleReview,
  reviewError,
  scheduleBatchReview,
  tomorrow,
  type ReviewRow,
} from '@/lib/reviews-api'
import { cn } from '@/lib/utils'

export interface BatchReviews {
  batch_code: string
  items: ReviewRow[]
  can_manage: boolean
  review_types: string[]
}

const FIELD = 'h-8 w-full rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]'
const LABEL = 'mb-1 block text-[10.5px] text-[#8A8FA8]'

/**
 * One batch's reviews: what has happened, what is booked, and the three
 * things a guide does about it.
 *
 * The round booker on the Project Reviews page schedules a whole section at
 * once, which is the common case. This is the other one - a single team that
 * needs its own slot, and the guide who has to record how it went.
 */
export function ReviewsPane({ data, code, onNotice, reload, canManage = true }: {
  data: BatchReviews
  code: string
  onNotice: (message: string) => void
  reload: () => void
  canManage?: boolean
}) {
  const [booking, setBooking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [acting, setActing] = useState<{ id: string; kind: 'complete' | 'move' | 'cancel' } | null>(null)

  const may = canManage && data.can_manage
  const scheduled = data.items.filter((r) => r.status === 'scheduled')
  const done = data.items.filter((r) => r.status !== 'scheduled')

  const run = async (label: string, fn: () => Promise<any>) => {
    setBusy(true); setError('')
    try {
      await fn()
      onNotice(label)
      setActing(null)
      reload()
    } catch (err) {
      setError(reviewError(err, 'That could not be recorded.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-2.5">
      <div className="rounded-xl border border-[#E8E9F2] bg-white p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[12.5px] font-semibold text-[#1B1B3A]">
            Reviews for {data.batch_code}
            <span className="ml-2 font-normal text-[11px] text-[#8A8FA8]">
              {scheduled.length} scheduled &middot; {done.length} closed
            </span>
          </p>
          <button type="button" disabled={!may} onClick={() => setBooking((o) => !o)}
            title={may ? undefined : 'Only the batch owner can schedule reviews'}
            className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3 py-1.5 text-[11.5px] font-medium text-white disabled:opacity-40">
            <CalendarPlus className="h-3.5 w-3.5" />
            {booking ? 'Close' : 'Schedule a review'}
          </button>
        </div>

        {booking && may && (
          <BookOne code={code} types={data.review_types}
            onDone={(m) => { onNotice(m); setBooking(false); reload() }} />
        )}

        {error && (
          <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-2 text-[11.5px] text-[#B91C1C]">
            <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {error}
          </p>
        )}

        {data.items.length === 0 ? (
          <p className="py-6 text-center text-[12px] text-[#8A8FA8]">
            No reviews have been scheduled for this batch yet.
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {data.items.map((r) => (
              <li key={r.id} className={cn('rounded-lg border px-2.5 py-2',
                r.overdue ? 'border-[#FECACA] bg-[#FEF2F2]' : 'border-[#EEF0F7]')}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="min-w-0 flex-1">
                    <span className="block text-[12px] font-medium text-[#1B1B3A]">
                      {r.review_type}
                      <span className="ml-1.5 font-normal text-[11px] text-[#8A8FA8]">
                        {r.scheduled_label} &middot; {r.slot_minutes} min
                      </span>
                    </span>
                    <span className="block text-[10.5px] text-[#8A8FA8]">
                      {r.reviewer ?? 'No reviewer assigned'}
                      {r.score != null && ` · scored ${r.score}`}
                    </span>
                    {r.remarks && (
                      <span className="mt-0.5 block text-[10.5px] text-[#B45309]">{r.remarks}</span>
                    )}
                  </span>

                  <span className={cn('shrink-0 rounded px-2 py-0.5 text-[10.5px] font-medium',
                    r.overdue ? 'bg-[#FEE2E2] text-[#B91C1C]'
                      : r.status === 'completed' ? 'bg-[#DCFCE7] text-[#15803D]'
                        : r.status === 'cancelled' ? 'bg-[#F3F4F6] text-[#6B7280]'
                          : 'bg-[#FEF3C7] text-[#B45309]')}>
                    {r.overdue ? 'Overdue' : r.status_label}
                  </span>

                  {may && r.status === 'scheduled' && (
                    <span className="flex shrink-0 gap-1.5">
                      <Action icon={Check} label="Record outcome" tone="green"
                        onClick={() => setActing({ id: r.id, kind: 'complete' })} />
                      <Action icon={Clock} label="Move" tone="amber"
                        onClick={() => setActing({ id: r.id, kind: 'move' })} />
                      <Action icon={XCircle} label="Cancel" tone="red"
                        onClick={() => setActing({ id: r.id, kind: 'cancel' })} />
                    </span>
                  )}
                </div>

                {acting?.id === r.id && (
                  <ActionForm kind={acting.kind} busy={busy}
                    onClose={() => setActing(null)}
                    onSubmit={(payload) => {
                      if (acting.kind === 'complete') {
                        return run(`${r.review_type} recorded.`,
                          () => completeReview(code, r.id, payload as any))
                      }
                      if (acting.kind === 'move') {
                        const p = payload as { date: string; time: string }
                        return run(`${r.review_type} moved.`,
                          () => rescheduleReview(code, r.id, p.date, p.time))
                      }
                      return run(`${r.review_type} cancelled.`,
                        () => cancelReview(code, r.id, (payload as { reason: string }).reason))
                    }} />
                )}
              </li>
            ))}
          </ul>
        )}

        {!may && data.items.length > 0 && (
          <p className="mt-2 text-[10.5px] text-[#8A8FA8]">
            You can see this batch&rsquo;s reviews. Its guide or coordinator records them.
          </p>
        )}
      </div>
    </div>
  )
}

function Action({ icon: Icon, label, tone, onClick }: {
  icon: any; label: string; tone: 'green' | 'amber' | 'red'; onClick: () => void
}) {
  const style = tone === 'green' ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]'
    : tone === 'amber' ? 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]'
      : 'border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]'
  return (
    <button type="button" onClick={onClick}
      className={cn('flex items-center gap-1 rounded-md border px-2 py-0.5 text-[10.5px] font-medium', style)}>
      <Icon className="h-3 w-3" /> {label}
    </button>
  )
}

/** Recording an outcome, moving a slot, or calling one off. */
function ActionForm({ kind, busy, onClose, onSubmit }: {
  kind: 'complete' | 'move' | 'cancel'
  busy: boolean
  onClose: () => void
  onSubmit: (payload: Record<string, any>) => void
}) {
  const [score, setScore] = useState('')
  const [remarks, setRemarks] = useState('')
  const [date, setDate] = useState(tomorrow())
  const [time, setTime] = useState('10:00')
  const [reason, setReason] = useState('')

  const ready = kind === 'cancel' ? reason.trim().length >= 3
    : kind === 'move' ? !!date && !!time
      : true

  return (
    <div className="mt-2 flex flex-wrap items-end gap-2 border-t border-[#EEF0F7] pt-2">
      {kind === 'complete' && (
        <>
          <label className="w-[92px]">
            <span className={LABEL}>Score /100</span>
            <input type="number" min={0} max={100} className={FIELD} value={score}
              onChange={(e) => setScore(e.target.value)} />
          </label>
          <label className="min-w-[220px] flex-1">
            <span className={LABEL}>Remarks</span>
            <input className={FIELD} value={remarks} placeholder="How did it go?"
              onChange={(e) => setRemarks(e.target.value)} />
          </label>
        </>
      )}
      {kind === 'move' && (
        <>
          <label><span className={LABEL}>New date</span>
            <input type="date" className={FIELD} value={date}
              onChange={(e) => setDate(e.target.value)} /></label>
          <label><span className={LABEL}>New time</span>
            <input type="time" className={FIELD} value={time}
              onChange={(e) => setTime(e.target.value)} /></label>
        </>
      )}
      {kind === 'cancel' && (
        <label className="min-w-[260px] flex-1">
          <span className={LABEL}>Why is it being cancelled?</span>
          <input className={FIELD} value={reason} autoFocus
            placeholder="Required — this goes on the batch's record"
            onChange={(e) => setReason(e.target.value)} />
        </label>
      )}

      <button type="button" disabled={busy || !ready}
        onClick={() => onSubmit(
          kind === 'complete'
            ? { score: score === '' ? undefined : Number(score), remarks: remarks || undefined }
            : kind === 'move' ? { date, time } : { reason })}
        className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3 py-1.5 text-[11.5px] font-medium text-white disabled:opacity-40">
        {busy && <Loader2 className="h-3 w-3 animate-spin" />}
        {kind === 'complete' ? 'Record' : kind === 'move' ? 'Move it' : 'Cancel review'}
      </button>
      <button type="button" onClick={onClose}
        className="rounded-lg border border-[#DDE0EE] px-2.5 py-1.5 text-[11.5px] text-[#5A5F7A]">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  )
}

/** Booking a slot for this one batch. */
function BookOne({ code, types, onDone }: {
  code: string; types: string[]; onDone: (message: string) => void
}) {
  const [form, setForm] = useState({
    review_type: types[0] ?? 'Progress Review',
    date: tomorrow(), time: '10:00', slot_minutes: 20,
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const book = async () => {
    setBusy(true); setError('')
    try {
      const result = await scheduleBatchReview(code, {
        review_type: form.review_type, date: form.date, time: form.time,
        slot_minutes: Number(form.slot_minutes),
      })
      onDone(result.message)
    } catch (err) {
      setError(reviewError(err, 'That review could not be booked.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mb-2.5 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-2.5">
      <div className="flex flex-wrap items-end gap-2">
        <label className="min-w-[150px]">
          <span className={LABEL}>Review</span>
          <select className={FIELD} value={form.review_type}
            onChange={(e) => setForm((f) => ({ ...f, review_type: e.target.value }))}>
            {types.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label><span className={LABEL}>Date</span>
          <input type="date" className={FIELD} value={form.date}
            onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} /></label>
        <label><span className={LABEL}>Time</span>
          <input type="time" className={FIELD} value={form.time}
            onChange={(e) => setForm((f) => ({ ...f, time: e.target.value }))} /></label>
        <label className="w-[92px]"><span className={LABEL}>Minutes</span>
          <input type="number" min={5} max={240} className={FIELD} value={form.slot_minutes}
            onChange={(e) => setForm((f) => ({ ...f, slot_minutes: Number(e.target.value) }))} /></label>
        <button type="button" onClick={book} disabled={busy}
          className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3 py-2 text-[11.5px] font-medium text-white disabled:opacity-50">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CalendarPlus className="h-3.5 w-3.5" />}
          Book it
        </button>
      </div>
      <p className="mt-1.5 text-[10px] text-[#8A8FA8]">
        The batch&rsquo;s guide takes it unless the round booker assigned someone else. A reviewer
        already busy at that time is refused.
      </p>
      {error && (
        <p className="mt-1.5 flex items-start gap-1.5 text-[11px] text-[#B91C1C]">
          <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}
    </div>
  )
}
