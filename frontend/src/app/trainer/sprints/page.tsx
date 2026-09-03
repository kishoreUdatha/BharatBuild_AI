'use client'

import { BatchPickerScreen } from '@/components/trainer/BatchPickerScreen'

export default function SprintsIndex() {
  return (
    <BatchPickerScreen
      title="Sprints"
      subtitle="Pick a batch to plan its sprints and see what each one is carrying."
      basePath="/trainer/sprints"
      kpis={(rows) => [
        { id: 'batches', value: String(rows.length), label: 'Batches' },
        {
          id: 'sprints',
          value: String(rows.reduce((sum, b) => sum + (b.sprints_total ?? 0), 0)),
          label: 'Sprints',
        },
        {
          id: 'stories',
          value: String(rows.reduce((sum, b) => sum + (b.stories_in_backlog ?? 0), 0)),
          label: 'Stories to Schedule',
        },
        {
          // A backlog with no sprints is the work this screen exists to do.
          id: 'pending',
          value: String(rows.filter((b) => (b.sprints_total ?? 0) === 0
            && (b.stories_in_backlog ?? 0) > 0).length),
          label: 'Backlogs Unplanned',
        },
        {
          id: 'students',
          value: String(rows.reduce((sum, b) => sum + b.members, 0)),
          label: 'Students',
        },
      ]}
      metric={{
        header: 'Sprints',
        render: (b) => (b.sprints_total ?? 0) > 0 ? (
          <span className="font-medium text-[#2563EB]">
            {b.sprints_total} {b.sprints_total === 1 ? 'sprint' : 'sprints'}
          </span>
        ) : (
          <span className="text-[#EA580C]">Not planned yet</span>
        ),
      }}
    />
  )
}
