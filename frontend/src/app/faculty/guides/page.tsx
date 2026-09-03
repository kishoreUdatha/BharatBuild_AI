'use client'

import { DataTable, PageShell, ResourceState, TD, TD_LEFT, useFacultyResource } from '@/components/faculty/PageShell'
import { fetchGuides } from '@/lib/faculty-api'

export default function FacultyGuidesPage() {
  const { data, loading, error, reload } = useFacultyResource(() => fetchGuides(), [])
  const items = data?.items ?? []

  return (
    <PageShell title="Faculty Guides" subtitle="Guides and the batches assigned to them this academic year">
      <ResourceState
        loading={loading}
        error={error}
        empty={items.length === 0}
        emptyMessage="No guides have batches assigned yet."
        onRetry={reload}
      >
        <DataTable head={['Guide', 'Email', 'Department', 'Assigned Batches', 'Avg Progress']}>
          {items.map((g) => (
            <tr key={g.id} className="border-b border-[#F1F2F8]">
              <td className={TD_LEFT}>{g.full_name ?? '–'}</td>
              <td className={TD}>{g.email}</td>
              <td className={TD}>{g.department ?? '–'}</td>
              <td className={TD}>{g.batches}</td>
              <td className={TD}>{g.avg_progress}%</td>
            </tr>
          ))}
        </DataTable>
        <p className="text-[11px] text-[#8A8FA8]">{items.length} guide(s)</p>
      </ResourceState>
    </PageShell>
  )
}
