'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { ShieldCheck } from 'lucide-react'
import {
  CARD, Chip, Empty, Failed, Loading, PageHeader,
} from '@/components/trainer/primitives'
import { errorText, fetchTrainerSettings } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

type Settings = Awaited<ReturnType<typeof fetchTrainerSettings>>

export default function TrainerSettingsPage() {
  const [data, setData] = useState<Settings | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try { setData(await fetchTrainerSettings()) }
    catch (err: any) { setError(errorText(err, 'Could not load your settings.')) }
  }, [])

  useEffect(() => { load() }, [load])

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading settings…" />

  const p = data.profile

  return (
    <div className="space-y-3">
      <PageHeader
        title="Settings"
        subtitle="Your account, the roles you hold, and what those roles let you reach."
      />

      <div className="grid gap-3 lg:grid-cols-2">
        <section className={cn(CARD, 'p-4')}>
          <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Account</h2>
          <dl className="mt-2 grid gap-x-6 gap-y-2 sm:grid-cols-2">
            {[
              ['Name', p.name], ['Email', p.email], ['Role', p.role],
              ['Department', p.department], ['College', p.college],
              ['Academic year', data.academic_year],
            ].map(([label, value]) => (
              <div key={label as string}>
                <dt className="text-[11px] text-[#9CA3AF]">{label}</dt>
                <dd className="text-[12.5px] font-medium text-[#1B1B3A]">{value ?? '—'}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-3 rounded-lg bg-[#F9FAFB] px-3 py-2 text-[11.5px] leading-snug text-[#6B7280]">
            These details come from your college record. Your department coordinator changes them,
            not this screen.
          </p>
        </section>

        <section className={cn(CARD, 'p-4')}>
          <h2 className="flex items-center gap-2 text-[14px] font-semibold text-[#1B1B3A]">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#EFF6FF] text-[#2563EB]">
              <ShieldCheck className="h-4 w-4" />
            </span>
            What you can reach
          </h2>
          <p className="mt-2 text-[12.5px] text-[#4B5563]">
            <span className="text-[19px] font-bold text-[#1B1B3A]">{data.managed_batches}</span>
            <span className="ml-1.5">batch{data.managed_batches === 1 ? '' : 'es'} in scope</span>
          </p>
          <p className="mt-1.5 text-[11.5px] leading-snug text-[#6B7280]">
            Scope comes from three places: batches you guide or review, sections you coordinate,
            and departments you hold office in. A batch outside all three is not yours to open,
            even with its code.
          </p>
          <Link href="/trainer/batches"
            className="mt-3 inline-block rounded-lg bg-[#2563EB] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#1D4ED8]">
            See the batches
          </Link>
        </section>
      </div>

      <section className={cn(CARD, 'p-4')}>
        <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Roles held</h2>

        {data.department_offices.length > 0 && (
          <div className="mt-2.5">
            <p className="mb-1.5 text-[11px] uppercase tracking-wide text-[#9CA3AF]">
              Department office
            </p>
            <ul className="flex flex-wrap gap-1.5">
              {data.department_offices.map((o, i) => (
                <li key={i}><Chip tone="violet">{o.department} &middot; {o.role}</Chip></li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-3">
          <p className="mb-1.5 text-[11px] uppercase tracking-wide text-[#9CA3AF]">
            Section assignments
          </p>
          {data.section_roles.length === 0 ? (
            <p className="text-[12px] text-[#9CA3AF]">No section assignments this academic year.</p>
          ) : (
            <ul className="space-y-1.5">
              {data.section_roles.map((r, i) => (
                <li key={i}
                  className="flex flex-wrap items-center gap-2 rounded-lg border border-[#F1F2F8] px-3 py-2">
                  <span className="text-[12px] font-medium text-[#1B1B3A]">
                    {r.department} &middot; {r.year} &middot; Sem {r.semester} &middot; Section {r.section}
                  </span>
                  <Chip tone={r.role === 'Class Coordinator' ? 'blue' : 'grey'}>{r.role}</Chip>
                  {r.responsibility && (
                    <span className="text-[11px] text-[#9CA3AF]">{r.responsibility}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  )
}
