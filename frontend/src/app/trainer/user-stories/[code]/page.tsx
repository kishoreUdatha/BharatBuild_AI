'use client'

/**
 * One batch's user stories.
 *
 * Reached by opening a batch from the User Stories list, or by the link
 * itself. The batch is fixed here - choosing a different one happens on the
 * list, which is one click back up the breadcrumb.
 */

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { StoriesBoard } from '@/components/trainer/user-stories/StoriesBoard'

export default function UserStoriesForBatchPage() {
  const params = useParams<{ code: string }>()
  const code = decodeURIComponent(params?.code ?? '')

  const above = (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <nav className="flex flex-wrap items-center gap-1.5 text-[12px]">
        <Link href="/trainer/batches" className="text-[#2563EB] hover:underline">My Batches</Link>
        <span className="text-[#C7CBDD]">/</span>
        <Link href="/trainer/user-stories" className="text-[#2563EB] hover:underline">
          User Stories
        </Link>
        <span className="text-[#C7CBDD]">/</span>
        <span className="text-[#6B7280]">{code}</span>
      </nav>
      <Link href="/trainer/user-stories"
        className="inline-flex items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
        <ArrowLeft className="h-3.5 w-3.5" /> All batches
      </Link>
    </div>
  )

  return <StoriesBoard code={code} above={above} />
}
