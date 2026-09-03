'use client'

import Link from 'next/link'
import { CalendarDays } from 'lucide-react'
import { PageShell, ResourceState, useFacultyResource } from '@/components/faculty/PageShell'
import { fetchReviews } from '@/lib/faculty-api'

/** Groups upcoming reviews by day - a schedule list rather than a month grid. */
export default function CalendarPage() {
  const { data, loading, error, reload } = useFacultyResource(() => fetchReviews({ limit: 200 }), [])
  const items = data?.items ?? []

  const byDay = items.reduce<Record<string, typeof items>>((acc, r) => {
    // Grouped by the server's day label, not a browser-parsed date: the
    // stored timestamp is naive UTC, so parsing it here reads it as local and
    // lands reviews on the wrong day either side of midnight.
    const key = r.scheduled_day ?? new Date(r.scheduled_at).toLocaleDateString('en-IN', {
      weekday: 'long', day: '2-digit', month: 'short', year: 'numeric',
    })
    ;(acc[key] ||= []).push(r)
    return acc
  }, {})

  return (
    <PageShell
      title="Calendar"
      subtitle="Scheduled reviews grouped by day"
      actions={
        <Link
          href="/faculty/project-reviews"
          className="rounded-lg border border-[#DDE0EE] bg-white px-4 py-2 text-[12px] font-medium text-[#3A3F58] hover:bg-[#F7F8FC]"
        >
          Open full schedule
        </Link>
      }
    >
      <ResourceState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyMessage="Nothing scheduled."
        onRetry={reload}
      >
        <div className="space-y-3">
          {Object.entries(byDay).map(([day, reviews]) => (
            <div key={day} className="rounded-xl border border-[#E8E9F2] bg-white p-4">
              <h2 className="mb-2 text-[13px] font-semibold text-[#1B1B3A]">{day}</h2>
              <ul className="space-y-1.5">
                {reviews.map((r) => (
                  <li key={r.id} className="flex items-center gap-3 rounded-lg border border-[#EEF0F7] px-3 py-2">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[#EEF0F7] text-[#5A5F7A]">
                      <CalendarDays className="h-3.5 w-3.5" />
                    </span>
                    <span className="w-[70px] shrink-0 text-[12px] font-medium text-[#1B1B3A]">
                      {r.scheduled_time ?? new Date(r.scheduled_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                    <span className="w-[100px] shrink-0 text-[12px] text-[#1B1B3A]">{r.batch_code}</span>
                    <span className="flex-1 text-[12px] text-[#5A5F7A]">{r.review_type}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </ResourceState>
    </PageShell>
  )
}
