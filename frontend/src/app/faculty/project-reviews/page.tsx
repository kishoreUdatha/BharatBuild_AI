'use client'

import { Suspense, useCallback, useEffect, useState  } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { AlertTriangle, CalendarPlus, Users } from 'lucide-react'
import {
  DataTable, PageShell, Pill, ResourceState, TD, TD_LEFT,
} from '@/components/faculty/PageShell'
import { ScheduleRound } from '@/components/faculty/ScheduleRound'
import {
  fetchAgenda, fetchReviewOptions, reviewError,
  type Agenda, type ReviewOptions,
} from '@/lib/reviews-api'
import { cn } from '@/lib/utils'

/**
 * The review calendar.
 *
 * Times come back already written in the institution's timezone, so nothing
 * here re-formats an instant — a browser in another zone would otherwise
 * disagree with the register a coordinator printed.
 */
function ProjectReviewsPageContent() {
  const params = useSearchParams()
  // ?status=overdue shows scheduled reviews whose date has passed.
  const overdueOnly = params.get('status') === 'overdue'

  const [data, setData] = useState<Agenda | null>(null)
  const [options, setOptions] = useState<ReviewOptions | null>(null)
  const [reviewerId, setReviewerId] = useState('')
  const [day, setDay] = useState('')
  const [booking, setBooking] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      setData(await fetchAgenda({
        include_past: overdueOnly, reviewer_id: reviewerId || undefined,
        date: day || undefined, limit: 500,
      }))
    } catch (err) {
      setError(reviewError(err, 'Could not load the review schedule.'))
    } finally {
      setLoading(false)
    }
  }, [overdueOnly, reviewerId, day])

  useEffect(() => { load() }, [load])
  useEffect(() => { fetchReviewOptions().then(setOptions).catch(() => setOptions(null)) }, [])

  const items = overdueOnly ? (data?.items ?? []).filter((r) => r.overdue) : (data?.items ?? [])

  return (
    <PageShell
      title="Project Reviews"
      subtitle={overdueOnly
        ? 'Scheduled reviews whose date has passed'
        : 'The review calendar. Times are shown in the institution’s timezone.'}
    >
      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5 text-[11px] text-[#5A5F7A]">
          Reviewer
          <select value={reviewerId} onChange={(e) => setReviewerId(e.target.value)}
            className="h-7 rounded-lg border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]">
            <option value="">Everyone</option>
            {options?.reviewers.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-[#5A5F7A]">
          Day
          <input type="date" value={day} onChange={(e) => setDay(e.target.value)}
            className="h-7 rounded-lg border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]" />
        </label>
        {day && (
          <button type="button" onClick={() => setDay('')}
            className="text-[11px] font-medium text-[#4F46E5] hover:underline">Clear day</button>
        )}
        <button type="button" onClick={() => setBooking((open) => !open)}
          className="ml-auto flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]">
          <CalendarPlus className="h-3.5 w-3.5" />
          {booking ? 'Close' : 'Schedule reviews'}
        </button>
      </div>

      {notice && (
        <p className="flex items-start justify-between gap-2 rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] px-3 py-2 text-[12px] text-[#15803D]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')}
            className="shrink-0 font-medium hover:underline">Dismiss</button>
        </p>
      )}

      {booking && (
        <ScheduleRound
          onClose={() => setBooking(false)}
          onBooked={(message) => { setNotice(message); load() }} />
      )}

      {data && (data.overdue > 0 || data.clashing > 0 || data.unassigned > 0) && (
        <div className="flex flex-wrap gap-3">
          {[
            { label: 'Overdue', value: data.overdue, tone: 'text-[#DC2626]' },
            { label: 'Double-booked', value: data.clashing, tone: 'text-[#B45309]' },
            { label: 'No reviewer', value: data.unassigned, tone: 'text-[#5A5F7A]' },
          ].filter((s) => s.value > 0).map((s) => (
            <div key={s.label} className="rounded-xl border border-[#E8E9F2] bg-white px-3 py-2">
              <p className={cn('text-[18px] font-bold leading-none', s.tone)}>{s.value}</p>
              <p className="mt-0.5 text-[11px] text-[#5A5F7A]">{s.label}</p>
            </div>
          ))}
        </div>
      )}

      <ResourceState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyMessage={overdueOnly ? 'No overdue reviews.' : 'Nothing scheduled for this view.'}
        onRetry={load}
      >
        <DataTable head={['Batch', 'Review', 'When', 'Slot', 'Reviewer', 'Status']}>
          {items.map((r) => (
            <tr key={r.id} className="border-b border-[#F1F2F8]">
              <td className={TD_LEFT}>
                <Link href={`/faculty/registrations/${encodeURIComponent(r.batch_code)}`}
                  className="font-medium text-[#4F46E5] hover:underline">
                  {r.batch_code}
                </Link>
              </td>
              <td className={TD}>{r.review_type}</td>
              <td className={TD}>{r.scheduled_label}</td>
              <td className={TD}>{r.slot_minutes} min</td>
              <td className={TD}>
                {r.reviewer ?? <span className="text-[#B45309]">Unassigned</span>}
                {r.clashes_with && r.clashes_with.length > 0 && (
                  <span title={`Also reviewing ${r.clashes_with.join(', ')} at this time`}
                    className="ml-1.5 inline-flex items-center gap-0.5 rounded bg-[#FFFBEB] px-1.5 py-0.5 text-[10px] font-medium text-[#B45309]">
                    <Users className="h-2.5 w-2.5" />
                    clash
                  </span>
                )}
              </td>
              <td className={TD}>
                {r.overdue ? <Pill tone="red">Overdue</Pill>
                  : r.status === 'completed' ? <Pill tone="green">Completed</Pill>
                    : r.status === 'cancelled' ? <Pill tone="slate">Cancelled</Pill>
                      : <Pill tone="amber">Scheduled</Pill>}
              </td>
            </tr>
          ))}
        </DataTable>
        <p className="flex items-center gap-1.5 text-[11px] text-[#8A8FA8]">
          {items.length} review(s)
          {data && data.clashing > 0 && !overdueOnly && (
            <span className="flex items-center gap-1 text-[#B45309]">
              <AlertTriangle className="h-3 w-3" />
              {data.clashing} sit on top of another booking for the same reviewer
            </span>
          )}
        </p>
      </ResourceState>
    </PageShell>
  )
}

/**
 * useSearchParams() opts the tree out of static rendering, and Next 14
 * fails the production build unless that bail-out sits behind a Suspense
 * boundary. Without this the page compiles in dev and breaks `next build`.
 */
export default function ProjectReviewsPage() {
  return (
    <Suspense fallback={<PageShell title="Project Reviews" subtitle="Loading…">{null}</PageShell>}>
      <ProjectReviewsPageContent />
    </Suspense>
  )
}
