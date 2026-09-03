'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'
import { fetchRegistration, type RegistrationState } from '@/lib/student-api'

export default function StudentSettings() {
  const [data, setData] = useState<RegistrationState | null>(null)
  const [failed, setFailed] = useState(false)
  // A failed load must say so. Setting data back to null left the page
  // spinning for ever, which reads as a hang rather than an error.
  useEffect(() => {
    fetchRegistration()
      .then(setData)
      .catch(() => setFailed(true))
  }, [])

  if (failed) {
    return (
      <div className="rounded-xl border border-[#FECACA] bg-[#FEF2F2] p-8 text-center">
        <AlertCircle className="mx-auto h-7 w-7 text-[#B91C1C]" />
        <p className="mt-2 text-[13px] font-semibold text-[#1B1B3A]">
          Could not load your registration
        </p>
        <p className="mt-1 text-[12px] text-[#6B7280]">
          Check your connection and try again.
        </p>
        <button type="button" onClick={() => location.reload()}
          className="mt-3 rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white">
          Retry
        </button>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex h-[300px] items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
      </div>
    )
  }

  const s = data.student
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">Settings</h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">Your account and academic details.</p>
      </div>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4">
        <h2 className="text-[14.5px] font-semibold text-[#1B1B3A]">Academic profile</h2>
        <dl className="mt-2 grid gap-x-6 gap-y-2 sm:grid-cols-2">
          {[
            ['Name', s.name], ['Roll number', s.roll_number], ['Email', s.email],
            ['College', s.college], ['Department', s.department], ['Year', s.year],
            ['Section', s.section], ['Academic year', s.academic_year],
          ].map(([label, value]) => (
            <div key={label as string}>
              <dt className="text-[11px] text-[#6B7280]">{label}</dt>
              <dd className="text-[12.5px] font-medium text-[#1B1B3A]">{value ?? '—'}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 rounded-lg bg-[#F9FAFB] px-3 py-2 text-[11.5px] leading-snug text-[#6B7280]">
          Academic details come from your college enrolment and are edited by your department
          coordinator, not here.
        </p>
      </section>
    </div>
  )
}
