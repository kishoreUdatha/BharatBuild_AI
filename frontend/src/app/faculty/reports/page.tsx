'use client'

import { NotBuiltYet, PageShell } from '@/components/faculty/PageShell'

export default function ReportsPage() {
  return (
    <PageShell title="Reports & Analytics" subtitle="Exportable reports across sections, batches and attendance">
      <NotBuiltYet
        what="Reports & Analytics"
        needs="The dashboard aggregate has the figures, but there is no reporting endpoint yet - nothing generates a PDF or CSV, and there is no historical data to trend against since attendance and progress are only stored for the current academic year. Building it means a report endpoint plus a place to keep period-over-period snapshots."
      />
    </PageShell>
  )
}
