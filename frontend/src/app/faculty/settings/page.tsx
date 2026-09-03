'use client'

import { NotBuiltYet, PageShell } from '@/components/faculty/PageShell'

export default function FacultySettingsPage() {
  return (
    <PageShell title="Settings" subtitle="Portal preferences and thresholds">
      <NotBuiltYet
        what="Settings"
        needs="The thresholds this portal grades on - the 75% attendance floor and the progress bands for Excellent / On Track / Need Attention - are constants in app/services/faculty_dashboard.py. Making them editable needs a settings table and an update endpoint so each institution can set its own."
      />
    </PageShell>
  )
}
