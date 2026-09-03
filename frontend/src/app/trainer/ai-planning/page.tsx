'use client'

/**
 * AI Planning - pick a batch whose drafted stories need a decision.
 *
 * The batches come from `/trainer/batches`, the trainer's own scope. This
 * screen used to read `/faculty/registrations`, which is guarded by the
 * faculty role: every trainer got a 403, and because the failure was swallowed
 * the screen showed an empty list rather than an error. Nothing else in the
 * portal reads a faculty route, and this one is no longer the exception.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { AlertTriangle, ArrowRight, CheckCircle2, Search, Sparkles } from 'lucide-react'
import { CARD, Empty, Failed, Loading, PageHeader } from '@/components/trainer/primitives'
import { errorText, fetchMyBatches } from '@/lib/trainer-api'
import type { BatchCard } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

/** What this batch is waiting on, in the words the screen should use. */
function reviewState(b: BatchCard) {
  const total = b.stories_total ?? 0
  const needs = b.stories_needs_review ?? 0
  const inBacklog = b.stories_in_backlog ?? 0
  if (needs > 0) {
    return {
      tone: 'amber' as const,
      text: `${needs} of ${total} ${needs === 1 ? 'story needs' : 'stories need'} review`,
    }
  }
  if (total === 0) return { tone: 'grey' as const, text: 'No stories drafted yet' }
  if (inBacklog === total) {
    return { tone: 'green' as const, text: `All ${total} stories moved to the backlog` }
  }
  return { tone: 'green' as const, text: `All ${total} reviewed — ready to move across` }
}

const TONE = {
  amber: { chip: 'bg-[#FFF7ED] text-[#EA580C]', text: 'text-[#C2410C]' },
  green: { chip: 'bg-[#F0FDF4] text-[#16A34A]', text: 'text-[#15803D]' },
  grey: { chip: 'bg-[#F4F5FA] text-[#9CA3AF]', text: 'text-[#9CA3AF]' },
}

export default function AiPlanningIndex() {
  const [rows, setRows] = useState<BatchCard[] | null>(null)
  const [error, setError] = useState('')
  const [q, setQ] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      // per_page is the API ceiling, so the picker is never a truncated view.
      const data = await fetchMyBatches({ per_page: 100, sort: 'code' })
      setRows(data.rows)
    } catch (err: any) {
      setError(errorText(err, 'Could not load your batches.'))
    }
  }, [])

  useEffect(() => { load() }, [load])

  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const matched = (rows ?? []).filter((b) => !needle
      || [b.batch_code, b.title, b.section].some((v) => (v ?? '').toLowerCase().includes(needle)))
    // Outstanding review first: this screen is a worklist, and the batch with
    // nothing left to decide is the one that can wait.
    return matched.sort((a, b) =>
      (b.stories_needs_review ?? 0) - (a.stories_needs_review ?? 0)
      || a.batch_code.localeCompare(b.batch_code))
  }, [rows, q])

  if (error) return <Failed message={error} onRetry={load} />
  if (!rows) return <Loading label="Loading your batches…" />

  const outstanding = rows.reduce((sum, b) => sum + (b.stories_needs_review ?? 0), 0)

  return (
    <div className="space-y-3">
      <PageHeader
        title="AI Planning"
        subtitle="Pick a batch to review its AI-drafted epics and user stories."
        right={outstanding > 0 ? (
          <span className="flex items-center gap-1.5 rounded-lg border border-[#FED7AA] bg-[#FFF7ED] px-3 py-1.5 text-[12px] font-medium text-[#C2410C]">
            <AlertTriangle className="h-3.5 w-3.5" />
            {outstanding} {outstanding === 1 ? 'story' : 'stories'} awaiting review
          </span>
        ) : undefined}
      />

      <span className="relative block max-w-[380px]">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
        <input value={q} onChange={(e) => setQ(e.target.value)}
          aria-label="Search batches"
          placeholder="Search batch code, project title or section…"
          className="h-9 w-full rounded-lg border border-[#D1D5DB] bg-white pl-8 pr-2.5 text-[12.5px] outline-none focus:border-[#2563EB]" />
      </span>

      {shown.length === 0 ? (
        <Empty message={rows.length === 0
          ? 'You have no batches this academic year.'
          : 'No batches match that search.'} />
      ) : (
        <ul className="grid gap-2.5 md:grid-cols-2 xl:grid-cols-3">
          {shown.map((b) => {
            const state = reviewState(b)
            return (
              <li key={b.id}>
                <Link href={`/trainer/ai-planning/${encodeURIComponent(b.batch_code)}`}
                  className={cn(CARD, 'flex h-full items-start gap-3 p-4',
                    'hover:border-[#BFDBFE] hover:bg-[#FAFBFE]')}>
                  <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
                    TONE[state.tone].chip)}>
                    {state.tone === 'amber' ? <Sparkles className="h-4 w-4" />
                      : state.tone === 'green' ? <CheckCircle2 className="h-4 w-4" />
                        : <Sparkles className="h-4 w-4" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[13px] font-semibold text-[#1B1B3A]">
                      {b.batch_code}
                    </span>
                    <span className="block truncate text-[11.5px] text-[#6B7280]">
                      {b.title ?? 'Untitled project'}
                    </span>
                    <span className="mt-1 block text-[10.5px] text-[#9CA3AF]">
                      Section {b.section ?? '—'} · {b.members} members
                    </span>
                    <span className={cn('mt-1.5 block text-[10.5px] font-medium',
                      TONE[state.tone].text)}>
                      {state.text}
                    </span>
                  </span>
                  <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-[#9CA3AF]" />
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
