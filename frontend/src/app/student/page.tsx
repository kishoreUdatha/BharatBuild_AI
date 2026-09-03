'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowRight, CheckCircle2, Clock, Loader2, Users } from 'lucide-react'
import { fetchRegistration, rupees, type RegistrationState } from '@/lib/student-api'

export default function StudentHome() {
  const [data, setData] = useState<RegistrationState | null>(null)

  useEffect(() => { fetchRegistration().then(setData).catch(() => setData(null)) }, [])

  if (!data) {
    return (
      <div className="flex h-[300px] items-center justify-center text-[#6B7280]">
        <Loader2 className="h-5 w-5 animate-spin text-[#2563EB]" />
      </div>
    )
  }

  const reg = data.your_registration
  const step = data.steps.find((s) => s.state === 'current') ?? data.steps[data.steps.length - 1]

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">
          Welcome back, {data.student.name ?? 'student'}
        </h1>
        <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
          {[data.student.department, data.student.year,
            data.student.section ? `Section ${data.student.section}` : null]
            .filter(Boolean).join('  •  ')}
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {[
          ['Current step', step?.label ?? '—', `Step ${step?.position ?? '—'} of ${data.steps.length}`],
          ['Batch', data.batch?.display_name ?? 'Not joined yet', data.batch?.join_code ?? 'Use your batch code'],
          ['Your share', rupees(reg.your_share),
            reg.payment.status === 'paid' ? 'Paid' : 'Not paid yet'],
        ].map(([label, value, sub]) => (
          <section key={label} className="rounded-xl border border-[#E5E7EB] bg-white p-4">
            <p className="text-[11.5px] text-[#6B7280]">{label}</p>
            <p className="mt-1 text-[17px] font-bold leading-tight text-[#1B1B3A]">{value}</p>
            <p className="mt-0.5 text-[11px] text-[#8A8FA8]">{sub}</p>
          </section>
        ))}
      </div>

      <section className="rounded-xl border border-[#E5E7EB] bg-white p-4">
        <h2 className="text-[14.5px] font-semibold text-[#1B1B3A]">Your registration checklist</h2>
        <ul className="mt-2 space-y-1.5">
          {reg.checklist.map((c) => (
            <li key={c.key} className="flex items-center gap-2 text-[12.5px]">
              {c.done
                ? <CheckCircle2 className="h-4 w-4 shrink-0 text-[#16A34A]" />
                : <Clock className="h-4 w-4 shrink-0 text-[#C7CBDD]" />}
              <span className={c.done ? 'text-[#1B1B3A]' : 'text-[#8A8FA8]'}>{c.label}</span>
            </li>
          ))}
        </ul>
        <Link href="/student/registration"
          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-[#2563EB] px-4 py-2 text-[12.5px] font-medium text-white hover:bg-[#1D4ED8]">
          <Users className="h-4 w-4" /> Open Team Registration <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </section>
    </div>
  )
}
