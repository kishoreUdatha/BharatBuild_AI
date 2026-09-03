'use client'

import Link from 'next/link'
import { BookOpen, Headphones, Mail } from 'lucide-react'

const STEPS = [
  'Sign in with the college account your department issued you.',
  'Enter the batch code your coordinator gave you and press Verify Batch.',
  'Join the batch to take your seat. Your seat is confirmed immediately.',
  'Pay your individual share. Each student pays separately from their own account.',
  'Once every seat is confirmed and paid, Project Setup unlocks for the whole team.',
]

export default function StudentSupport() {
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">Help &amp; Support</h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
          Wrong batch code, a member who cannot join, or a payment that has not appeared.
        </p>
      </div>

      <section id="guide" className="rounded-xl border border-[#E5E7EB] bg-white p-4">
        <h2 className="flex items-center gap-2 text-[14.5px] font-semibold text-[#1B1B3A]">
          <BookOpen className="h-4 w-4 text-[#2563EB]" /> Registration guide
        </h2>
        <ol className="mt-2 space-y-1.5">
          {STEPS.map((s, i) => (
            <li key={s} className="flex gap-2 text-[12.5px] leading-snug text-[#374151]">
              <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#EFF6FF] text-[10px] font-semibold text-[#2563EB]">
                {i + 1}
              </span>{s}
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4">
        <h2 className="flex items-center gap-2 text-[14.5px] font-semibold text-[#1B1B3A]">
          <Headphones className="h-4 w-4 text-[#2563EB]" /> Contact your coordinator
        </h2>
        <p className="mt-1.5 text-[12.5px] leading-snug text-[#374151]">
          Batch codes, seat changes and fee records are handled by your department coordinator,
          not by the portal. In-app messaging is not connected yet, so reach them directly.
        </p>
        <p className="mt-2 flex items-center gap-2 text-[12.5px] text-[#374151]">
          <Mail className="h-4 w-4 text-[#6B7280]" />
          Ask your class coordinator for the project cell address for your department.
        </p>
        <Link href="/student/registration"
          className="mt-3 inline-block rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8]">
          Back to registration
        </Link>
      </section>
    </div>
  )
}
