'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import {
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  Clock,
  Sparkles,
  TrendingDown,
} from 'lucide-react'
import {
  Bar, CARD, Chip, Failed, Loading, fmtDate,
} from '@/components/trainer/primitives'
import { errorText, fetchTrainerHome } from '@/lib/trainer-api'
import type { TrainerHome } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

/** Severity drives the whole visual weight of a queue item. */
const SEVERITY = {
  critical: { ring: 'border-[#FECACA] bg-[#FEF2F2]', dot: 'bg-[#DC2626]',
    text: 'text-[#B91C1C]', icon: AlertTriangle },
  warning: { ring: 'border-[#FED7AA] bg-[#FFF7ED]', dot: 'bg-[#EA580C]',
    text: 'text-[#C2410C]', icon: Clock },
  info: { ring: 'border-[#DBEAFE] bg-[#EFF6FF]', dot: 'bg-[#2563EB]',
    text: 'text-[#1D4ED8]', icon: CalendarClock },
} as const

export default function TrainerHomePage() {
  const { user } = useAuth()
  // A manager has no Faculty Portal to be sent to, and their counts are the
  // whole college rather than a personal caseload - so the note explaining the
  // numbers would be wrong for them twice over.
  const isManager = user?.role === 'manager'
  const [data, setData] = useState<TrainerHome | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try { setData(await fetchTrainerHome()) }
    catch (err: any) { setError(errorText(err, 'Could not load your worklist.')) }
  }, [])

  useEffect(() => { load() }, [load])

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Working out what needs you…" />

  const s = data.scope

  return (
    <div className="space-y-4">
      {/* Who, and how much of it */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">
            {data.trainer ?? 'Trainer'}
          </h1>
          <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
            {s.batches} batch{s.batches === 1 ? '' : 'es'} &middot; {s.students} students
            &middot; {s.average_progress}% average progress &middot; {data.academic_year}
          </p>
        </div>
        <Link href="/trainer/batches"
          className="flex items-center gap-1.5 text-[12.5px] font-medium text-[#2563EB] hover:underline">
          See all batches <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* The queue */}
      {data.clear ? (
        <section className={cn(CARD, 'flex items-center gap-3 border-[#BBF7D0] bg-[#F0FDF4] p-5')}>
          <CheckCircle2 className="h-6 w-6 shrink-0 text-[#16A34A]" />
          <span>
            <span className="block text-[14px] font-semibold text-[#15803D]">
              Nothing is waiting on you
            </span>
            <span className="block text-[12px] text-[#4B5563]">
              No overdue reviews, no unreviewed stories, no missing documents across your batches.
            </span>
          </span>
        </section>
      ) : (
        <section>
          <h2 className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-[#6B7280]">
            Needs your decision
          </h2>
          <ul className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
            {data.attention.map((a) => {
              const tone = SEVERITY[a.severity as keyof typeof SEVERITY] ?? SEVERITY.info
              const Icon = tone.icon
              return (
                <li key={a.id}>
                  <Link href={a.href}
                    className={cn(CARD, tone.ring,
                      'flex h-full items-start gap-3 p-3.5 transition-shadow hover:shadow-sm')}>
                    <Icon className={cn('mt-0.5 h-4.5 w-4.5 shrink-0', tone.text)} />
                    <span className="min-w-0 flex-1">
                      <span className={cn('block text-[13px] font-semibold leading-snug', tone.text)}>
                        {a.label}
                      </span>
                      <span className="mt-0.5 block text-[11.5px] leading-snug text-[#4B5563]">
                        {a.hint}
                      </span>
                    </span>
                    <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-[#9CA3AF]" />
                  </Link>
                </li>
              )
            })}
          </ul>
        </section>
      )}

      <div className="grid gap-3 lg:grid-cols-3">
        {/* Most overdue first — the sharpest end of the queue */}
        <section className={cn(CARD, 'p-4')}>
          <div className="flex items-center justify-between">
            <h2 className="text-[13.5px] font-semibold text-[#1B1B3A]">Longest overdue</h2>
            <Link href="/trainer/reviews?status=overdue"
              className="text-[11.5px] font-medium text-[#2563EB] hover:underline">All reviews</Link>
          </div>
          {data.overdue_reviews.length === 0 ? (
            <p className="py-6 text-center text-[11.5px] text-[#9CA3AF]">No review is overdue.</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {data.overdue_reviews.map((r) => (
                <li key={r.id} className="flex items-start gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[#DC2626]" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[12px] font-medium text-[#1B1B3A]">
                      {r.review_type}
                    </span>
                    <span className="block truncate text-[10.5px] text-[#9CA3AF]">
                      {r.batch_code} &middot; was due {fmtDate(r.scheduled_at)}
                    </span>
                  </span>
                  <Chip tone="red">{Math.abs(r.days)}d</Chip>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Story approval is the trainer's exclusive job, so it gets its own panel */}
        <section className={cn(CARD, 'p-4')}>
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-1.5 text-[13.5px] font-semibold text-[#1B1B3A]">
              <Sparkles className="h-4 w-4 text-[#7C3AED]" /> Stories to review
            </h2>
            <Link href="/trainer/ai-planning"
              className="text-[11.5px] font-medium text-[#2563EB] hover:underline">All batches</Link>
          </div>
          {data.story_queue.length === 0 ? (
            <p className="py-6 text-center text-[11.5px] text-[#9CA3AF]">
              Every drafted story has been reviewed.
            </p>
          ) : (
            <ul className="mt-2 space-y-2">
              {data.story_queue.map((q) => (
                <li key={q.batch_code}>
                  <Link href={`/trainer/ai-planning/${encodeURIComponent(q.batch_code)}`}
                    className="flex items-center gap-2 rounded-lg px-1 py-1 hover:bg-[#FAFBFE]">
                    <span className="min-w-0 flex-1">
                      <span className="block text-[12px] font-medium text-[#1B1B3A]">
                        {q.batch_code}
                      </span>
                      <span className="block truncate text-[10.5px] text-[#9CA3AF]">
                        {q.batch_title ?? 'Untitled project'}
                      </span>
                    </span>
                    <Chip tone="violet">{q.needs_review} of {q.total}</Chip>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Where the work is actually slipping */}
        <section className={cn(CARD, 'p-4')}>
          <div className="flex items-center justify-between">
            <h2 className="flex items-center gap-1.5 text-[13.5px] font-semibold text-[#1B1B3A]">
              <TrendingDown className="h-4 w-4 text-[#EA580C]" /> Furthest behind
            </h2>
            <Link href="/trainer/reports"
              className="text-[11.5px] font-medium text-[#2563EB] hover:underline">Reports</Link>
          </div>
          {data.needs_attention.length === 0 ? (
            <p className="py-6 text-center text-[11.5px] text-[#9CA3AF]">No batches in scope.</p>
          ) : (
            <ul className="mt-2 space-y-2.5">
              {data.needs_attention.map((b) => (
                <li key={b.batch_code}>
                  <Link href={`/faculty/registrations/${encodeURIComponent(b.batch_code)}`}
                    className="block rounded-lg px-1 py-0.5 hover:bg-[#FAFBFE]">
                    <span className="flex items-center justify-between gap-2">
                      <span className="min-w-0">
                        <span className="block text-[12px] font-medium text-[#1B1B3A]">
                          {b.batch_code}
                          <span className="ml-1 font-normal text-[#9CA3AF]">
                            Section {b.section ?? '—'}
                          </span>
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-1.5">
                        {b.overdue > 0 && <Chip tone="red">{b.overdue} overdue</Chip>}
                        <span className="text-[11.5px] font-medium text-[#1B1B3A]">
                          {b.progress}%
                        </span>
                      </span>
                    </span>
                    <span className="mt-1 block">
                      <Bar value={b.progress}
                        tone={b.progress < 55 ? 'bg-[#EA580C]' : 'bg-[#2563EB]'} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <p className="text-[11.5px] text-[#9CA3AF]">
        {isManager
          ? 'Every count here is the college chosen above — every branch, every section, every trainer working in it. Switch colleges from the header.'
          : 'Every count here is your own scope — the batches you guide, review or coordinate. A coordinator’s wider view of the department lives in the Faculty Portal.'}
      </p>
    </div>
  )
}
