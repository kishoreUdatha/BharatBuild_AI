'use client'

import { Suspense } from 'react'

import { useSearchParams } from 'next/navigation'
import { DataTable, PageShell, Pill, ResourceState, TD, TD_LEFT, useFacultyResource } from '@/components/faculty/PageShell'
import { fetchBatches } from '@/lib/faculty-api'

const TONE = { verified: 'green', pending: 'amber', missing: 'red' } as const

function BasePapersPageContent() {
  const params = useSearchParams()
  const status = params.get('status') ?? undefined   // verified | pending | missing

  const { data, loading, error, reload } = useFacultyResource(() => fetchBatches({ limit: 200 }), [])

  let items = data?.items ?? []
  if (status) items = items.filter((b) => b.base_paper_status === status)

  const counts = (data?.items ?? []).reduce<Record<string, number>>((acc, b) => {
    acc[b.base_paper_status] = (acc[b.base_paper_status] ?? 0) + 1
    return acc
  }, {})

  return (
    <PageShell
      title="Base Papers"
      subtitle={status ? `Batches whose base paper is ${status}` : 'Base paper verification state per batch'}
    >
      <div className="grid grid-cols-3 gap-3">
        {(['verified', 'pending', 'missing'] as const).map((k) => (
          <div key={k} className="rounded-xl border border-[#E8E9F2] bg-white p-3">
            <p className="text-[20px] font-bold leading-none text-[#1B1B3A]">{counts[k] ?? 0}</p>
            <p className="mt-1 text-[11px] capitalize text-[#5A5F7A]">{k}</p>
          </div>
        ))}
      </div>

      <ResourceState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyMessage="No batches match this view."
        onRetry={reload}
      >
        <DataTable head={['Batch ID', 'Project Title', 'Section', 'Base Paper']}>
          {items.map((b) => (
            <tr key={b.id} className="border-b border-[#F1F2F8]">
              <td className={TD_LEFT}>{b.batch_code}</td>
              <td className={TD}>{b.title ?? '–'}</td>
              <td className={TD}>{b.section ?? '–'}</td>
              <td className={TD}>
                <Pill tone={TONE[b.base_paper_status as keyof typeof TONE] ?? 'slate'}>{b.base_paper_status}</Pill>
              </td>
            </tr>
          ))}
        </DataTable>
        <p className="text-[11px] text-[#8A8FA8]">{items.length} batch(es)</p>
      </ResourceState>
    </PageShell>
  )
}

/**
 * useSearchParams() opts the tree out of static rendering, and Next 14
 * fails the production build unless that bail-out sits behind a Suspense
 * boundary. Without this the page compiles in dev and breaks `next build`.
 */
export default function BasePapersPage() {
  return (
    <Suspense fallback={<PageShell title="Base Papers" subtitle="Loading…">{null}</PageShell>}>
      <BasePapersPageContent />
    </Suspense>
  )
}
