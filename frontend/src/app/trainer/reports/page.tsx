'use client'

import { useCallback, useEffect, useState } from 'react'
import { Download } from 'lucide-react'
import {
  Bar, CARD, Chip, Empty, Failed, KpiRow, Loading, PageHeader,
} from '@/components/trainer/primitives'
import { errorText, fetchTrainerReports } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

type Report = Awaited<ReturnType<typeof fetchTrainerReports>>

/** Builds the CSV from what is on screen, so the export cannot disagree with it. */
function toCsv(data: Report): string {
  const lines = [
    `Trainer report,${data.academic_year}`,
    '',
    'Section,Batches,Students,Average progress %,Reviews pending,Reviews overdue',
    ...data.sections.map((s) =>
      [s.section, s.batches, s.students, s.progress, s.reviews_pending, s.reviews_overdue].join(',')),
    '',
    'Stage,Average completion %',
    ...data.stages.map((s) => [`"${s.stage}"`, s.percent].join(',')),
  ]
  return lines.join('\n')
}

export default function TrainerReportsPage() {
  const [data, setData] = useState<Report | null>(null)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setError('')
    try { setData(await fetchTrainerReports()) }
    catch (err: any) { setError(errorText(err, 'Could not load reports.')) }
  }, [])

  useEffect(() => { load() }, [load])

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading reports…" />

  const download = () => {
    const href = URL.createObjectURL(new Blob([toCsv(data)], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = href
    link.download = `trainer-report-${data.academic_year}.csv`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(href)
  }

  const worst = data.sections.reduce<null | Report['sections'][number]>(
    (acc, s) => (acc === null || s.progress < acc.progress ? s : acc), null)

  return (
    <div className="space-y-3">
      <PageHeader
        title="Reports"
        subtitle={`Roll-ups across the batches you are responsible for, ${data.academic_year}.`}
        right={
          <button type="button" onClick={download}
            className="flex items-center gap-2 rounded-lg border border-[#BFDBFE] px-3.5 py-2 text-[12.5px] font-medium text-[#2563EB] hover:bg-[#EFF6FF]">
            <Download className="h-4 w-4" /> Export CSV
          </button>
        }
      />
      <KpiRow kpis={data.kpis} />

      {data.sections.length === 0 ? (
        <Empty message="You are not assigned to any batches this academic year." />
      ) : (
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[14px] font-semibold text-[#1B1B3A]">By section</h2>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full table-fixed border-collapse text-[11.5px]">
                <colgroup>
                  {['70px', '62px', '68px', 'auto', '68px', '68px'].map((w, i) => (
                    <col key={i} style={{ width: w }} />
                  ))}
                </colgroup>
                <thead>
                  <tr className="border-b border-[#E5E7EB] text-[#6B7280]">
                    {['Section', 'Batches', 'Students', 'Average progress', 'Pending', 'Overdue']
                      .map((h, i) => (
                        <th key={h} className={cn('px-2 py-2 text-[11px] font-medium',
                          i === 0 ? 'text-left' : i === 3 ? 'text-left' : 'text-center')}>{h}</th>
                      ))}
                  </tr>
                </thead>
                <tbody>
                  {data.sections.map((s) => (
                    <tr key={s.section} className="border-b border-[#F1F2F8] last:border-b-0">
                      <td className="px-2 py-2 font-medium text-[#1B1B3A]">{s.section}</td>
                      <td className="px-2 py-2 text-center text-[#4B5563]">{s.batches}</td>
                      <td className="px-2 py-2 text-center text-[#4B5563]">{s.students}</td>
                      <td className="px-2 py-2">
                        <span className="flex items-center gap-2">
                          <span className="flex-1"><Bar value={s.progress} /></span>
                          <span className="w-[32px] shrink-0 text-right text-[#1B1B3A]">
                            {s.progress}%
                          </span>
                        </span>
                      </td>
                      <td className="px-2 py-2 text-center text-[#4B5563]">{s.reviews_pending}</td>
                      <td className="px-2 py-2 text-center">
                        {s.reviews_overdue > 0
                          ? <Chip tone="red">{s.reviews_overdue}</Chip>
                          : <span className="text-[#9CA3AF]">0</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {worst && data.sections.length > 1 && (
              <p className="mt-2.5 border-t border-[#F1F2F8] pt-2.5 text-[11.5px] text-[#6B7280]">
                Section {worst.section} is furthest behind at {worst.progress}%.
              </p>
            )}
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Average completion by stage</h2>
            <ul className="mt-2 space-y-2">
              {data.stages.map((s) => (
                <li key={s.stage} className="flex items-center gap-2">
                  <span className="w-[118px] shrink-0 truncate text-[11px] text-[#4B5563]"
                    title={s.stage}>{s.stage}</span>
                  <span className="flex-1">
                    <Bar value={s.percent} tone={s.percent >= 80 ? 'bg-[#16A34A]' : 'bg-[#2563EB]'} />
                  </span>
                  <span className="w-[34px] shrink-0 text-right text-[11px] text-[#1B1B3A]">
                    {s.percent}%
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-3 border-t border-[#F1F2F8] pt-2.5 text-[11px] leading-snug text-[#9CA3AF]">
              Averaged across every batch in your scope. A stage sitting low across all sections is
              usually a sequencing problem rather than a batch problem.
            </p>
          </section>
        </div>
      )}
    </div>
  )
}
