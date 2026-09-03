'use client'

/**
 * Choose a batch, then work on it.
 *
 * User Stories, Sprints and Tasks are all one batch's view of the same
 * project, so they all start the same way: the trainer's batches, narrowed by
 * department, section and batch number, and opening one goes to that batch's
 * screen. Only the column in the middle differs - stories, sprints or tasks -
 * which is what `metric` is for.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { ArrowRight } from 'lucide-react'
import {
  CARD, Chip, Empty, Failed, Loading, KpiRow, PageHeader,
} from '@/components/trainer/primitives'
import type { Kpi } from '@/components/trainer/primitives'
import {
  BatchFilters, EMPTY_SCOPE, batchesInScope,
} from '@/components/trainer/user-stories/BatchFilters'
import type { BatchScope } from '@/components/trainer/user-stories/BatchFilters'
import { errorText, fetchMyBatches } from '@/lib/trainer-api'
import type { BatchCard } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const STATUS_TONE: Record<string, 'blue' | 'amber' | 'green'> = {
  'In Progress': 'blue', Review: 'amber', Completed: 'green',
}

export function BatchPickerScreen({ title, subtitle, basePath, metric, kpis }: {
  title: string
  subtitle: string
  /** Where opening a batch goes: `${basePath}/${batch_code}`. */
  basePath: string
  metric: { header: string; render: (batch: BatchCard) => ReactNode }
  /**
   * The tiles above the list, computed from the batches in scope - so
   * narrowing to a section moves them, and they always describe the rows
   * underneath rather than everything the trainer owns.
   */
  kpis: (rows: BatchCard[]) => Kpi[]
}) {
  const router = useRouter()
  const [batches, setBatches] = useState<BatchCard[] | null>(null)
  const [error, setError] = useState('')
  const [scope, setScope] = useState<BatchScope>(EMPTY_SCOPE)

  const load = useCallback(async () => {
    setError('')
    try {
      // per_page is the API ceiling, so the list is never a truncated view.
      const data = await fetchMyBatches({ per_page: 100, sort: 'code' })
      setBatches(data.rows)
    } catch (err: any) {
      setError(errorText(err, 'Could not load your batches.'))
    }
  }, [])

  useEffect(() => { load() }, [load])

  const rows = useMemo(() => batchesInScope(batches ?? [], scope), [batches, scope])

  if (error) return <Failed message={error} onRetry={load} />
  if (!batches) return <Loading label="Loading your batches…" />

  const open = (code: string) => router.push(`${basePath}/${encodeURIComponent(code)}`)

  return (
    <div className="space-y-3">
      <PageHeader title={title} subtitle={subtitle} />

      <KpiRow kpis={kpis(rows)} />

      <BatchFilters batches={batches} scope={scope} onChange={setScope} />

      <div className={cn(CARD, 'p-4')}>
        <h2 className="text-[14px] font-bold text-[#1B1B3A]">Batches ({rows.length})</h2>

        {rows.length === 0 ? (
          <Empty message={batches.length === 0
            ? 'You have no batches this academic year.'
            : 'No batches match these filters.'} />
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[880px] text-left text-[12px]">
              <thead>
                <tr className="border-y border-[#E5E7EB] bg-[#FAFBFF] text-[11.5px] text-[#6B7280]">
                  {['Project ID', 'Tentative Title', 'Section', 'Batch No', 'Guide',
                    'Students', metric.header, 'Status', ''].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2.5 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F2F8]">
                {rows.map((b) => (
                  <tr key={b.id} onClick={() => open(b.batch_code)}
                    className="cursor-pointer hover:bg-[#FAFBFE]">
                    <td className="whitespace-nowrap px-3 py-2.5 font-medium text-[#2563EB]">
                      {b.batch_code}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="block max-w-[240px] truncate text-[#1B1B3A]">
                        {b.title ?? 'Untitled project'}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-[#4B5563]">
                      {b.section ?? '—'}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-[#4B5563]">
                      {b.batch_no ?? '—'}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-[#4B5563]">
                      {b.guide ?? 'Unassigned'}
                    </td>
                    <td className="px-3 py-2.5 text-center text-[#4B5563]">{b.members}</td>
                    <td className="whitespace-nowrap px-3 py-2.5">{metric.render(b)}</td>
                    <td className="whitespace-nowrap px-3 py-2.5">
                      <Chip tone={STATUS_TONE[b.status] ?? 'blue'}>{b.status}</Chip>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-right">
                      <span className="inline-flex items-center gap-1 text-[11.5px] font-medium text-[#2563EB]">
                        Open <ArrowRight className="h-3.5 w-3.5" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
