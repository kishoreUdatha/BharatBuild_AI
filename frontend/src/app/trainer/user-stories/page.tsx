'use client'

import { Sparkles } from 'lucide-react'
import { BatchPickerScreen } from '@/components/trainer/BatchPickerScreen'

export default function UserStoriesIndex() {
  return (
    <BatchPickerScreen
      title="User Stories"
      subtitle="Pick a batch to assign, schedule and track its approved stories."
      basePath="/trainer/user-stories"
      kpis={(rows) => [
        { id: 'batches', value: String(rows.length), label: 'Batches' },
        {
          id: 'students',
          value: String(rows.reduce((sum, b) => sum + b.members, 0)),
          label: 'Students',
        },
        {
          id: 'stories',
          value: String(rows.reduce((sum, b) => sum + (b.stories_in_backlog ?? 0), 0)),
          label: 'Stories in Backlog',
        },
        {
          id: 'pending',
          value: String(rows.reduce((sum, b) => sum + (b.stories_needs_review ?? 0), 0)),
          label: 'Awaiting AI Review',
        },
        {
          // Batches whose drafts are approved-but-unmoved, or still in review:
          // the ones whose User Stories screen has nothing to show yet.
          id: 'outstanding',
          value: String(rows.filter((b) => (b.stories_in_backlog ?? 0) === 0
            && b.stories_total > 0).length),
          label: 'Backlogs Not Started',
        },
      ]}
      metric={{
        header: 'Backlog',
        // What the batch's screen will actually be able to show, so one still
        // in review says so before it is opened.
        render: (b) => (b.stories_in_backlog ?? 0) > 0 ? (
          <span className="font-medium text-[#2563EB]">
            {b.stories_in_backlog} {b.stories_in_backlog === 1 ? 'story' : 'stories'}
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[#7C3AED]">
            <Sparkles className="h-3.5 w-3.5" />
            {b.stories_total > 0 ? 'In AI Planning' : 'No stories yet'}
          </span>
        ),
      }}
    />
  )
}
