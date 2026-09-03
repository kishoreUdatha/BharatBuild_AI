'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  AlertTriangle, ArrowRight, CheckCircle2, Database, Download, UserPlus, Users, XCircle,
} from 'lucide-react'
import { CARD, Chip, Failed, Loading } from '@/components/trainer/primitives'
import {
  downloadImportReport, errorText, fetchImportHistory, fetchImportResult,
} from '@/lib/trainer-api'
import type { ImportHistoryRow, ImportResult } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const BTN = 'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12.5px] font-medium'
const BTN_OUTLINE = `${BTN} border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]`
const BTN_PRIMARY = `${BTN} bg-[#2563EB] text-white hover:bg-[#1D4ED8]`

const fmtTime = (iso: string | null) => {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? '' : d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

const fmtWhen = (iso: string | null) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export default function ImportResultPage() {
  const params = useParams<{ id: string }>()
  const runId = params?.id

  const [data, setData] = useState<ImportResult | null>(null)
  const [history, setHistory] = useState<ImportHistoryRow[]>([])
  const [error, setError] = useState('')
  const [tab, setTab] = useState<'summary' | 'batches'>('summary')

  const load = useCallback(async () => {
    if (!runId) return
    setError('')
    try { setData(await fetchImportResult(runId)) }
    catch (err: any) { setError(errorText(err, 'Could not load this import.')) }
  }, [runId])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    fetchImportHistory(10).then((r) => setHistory(r.rows ?? [])).catch(() => setHistory([]))
  }, [])

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading the import…" />

  const s = data.summary ?? {
    batches: [], batches_created: 0, batches_updated: 0, students_assigned: 0, guides_assigned: 0,
  }
  // Nothing was rejected outright, and nothing needed attention.
  const clean = data.rows_failed === 0 && data.rows_duplicate === 0
  const failedOnly = data.rows_imported === 0 && data.rows_failed > 0

  return (
    <div className="space-y-3">
      {/* ---------------------------------------------------------- header */}
      <div className={cn(CARD, 'flex flex-wrap items-center justify-between gap-3 p-4')}>
        <div className="flex items-center gap-3">
          <span className={cn('flex h-11 w-11 items-center justify-center rounded-full',
            failedOnly ? 'bg-[#FEE2E2]' : clean ? 'bg-[#DCFCE7]' : 'bg-[#FEF3C7]')}>
            {failedOnly
              ? <XCircle className="h-6 w-6 text-[#DC2626]" />
              : clean
                ? <CheckCircle2 className="h-6 w-6 text-[#16A34A]" />
                : <AlertTriangle className="h-6 w-6 text-[#D97706]" />}
          </span>
          <div>
            <h1 className="text-[19px] font-bold leading-tight text-[#1B1B3A]">
              {failedOnly ? 'Import failed'
                : clean ? 'Import completed successfully!'
                  : 'Import completed with warnings'}
            </h1>
            <p className="mt-0.5 text-[12px] text-[#6B7280]">
              {failedOnly
                ? 'No rows were applied. The report lists what went wrong on each one.'
                : `${data.rows_imported} student${data.rows_imported === 1 ? '' : 's'} assigned across `
                  + `${s.batches.length} batch${s.batches.length === 1 ? '' : 'es'}.`}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" className={BTN_OUTLINE}
            onClick={() => downloadImportReport(data.id, data.import_code)}>
            <Download className="h-4 w-4" /> Download Report
          </button>
          <Link href="/trainer/batches" className={BTN_PRIMARY}>
            View My Batches <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>

      {/* ------------------------------------------------------------ KPIs */}
      <div className={cn(CARD, 'grid grid-cols-2 divide-x divide-[#F1F2F8] md:grid-cols-5')}>
        <Kpi icon={<Database className="h-4 w-4" />} tone="green"
          value={s.batches_created} label="Batches Created" />
        <Kpi icon={<Users className="h-4 w-4" />} tone="violet"
          value={s.students_assigned} label="Students Assigned" />
        <Kpi icon={<UserPlus className="h-4 w-4" />} tone="blue"
          value={s.guides_assigned} label="Guides Assigned" />
        <Kpi icon={<AlertTriangle className="h-4 w-4" />} tone="amber"
          value={data.rows_duplicate} label="Warnings" />
        <Kpi icon={<XCircle className="h-4 w-4" />} tone="red"
          value={data.rows_failed} label="Failed Rows" />
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* ------------------------------------------- summary / batches */}
        <div className={cn(CARD, 'p-4')}>
          <div className="flex gap-4 border-b border-[#E5E7EB]">
            {([['summary', 'Import Summary'],
               ['batches', `Imported Batches (${s.batches.length})`]] as const).map(([key, label]) => (
              <button key={key} type="button" onClick={() => setTab(key)}
                className={cn('-mb-px border-b-2 pb-2 text-[12.5px] font-medium',
                  tab === key
                    ? 'border-[#2563EB] text-[#2563EB]'
                    : 'border-transparent text-[#6B7280] hover:text-[#374151]')}>
                {label}
              </button>
            ))}
          </div>

          {tab === 'summary' ? (
            <div className="mt-3 grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
              <dl className="space-y-1.5 text-[12px]">
                <Row label="File Name" value={data.file_name} />
                <Row label="Imported By" value={data.imported_by ?? '—'} />
                <Row label="Imported On" value={fmtWhen(data.started_at)} />
                <Row label="Total Rows" value={String(data.rows_total)} />
                <Row label="Success Rows" value={String(data.rows_imported)} />
                <Row label="Warning Rows" value={String(data.rows_duplicate)} />
                <Row label="Failed Rows" value={String(data.rows_failed)} />
                <div className="flex items-center gap-2 pt-1">
                  <dt className="w-[104px] shrink-0 text-[#6B7280]">Status</dt>
                  <dd><Chip tone={failedOnly ? 'red' : clean ? 'green' : 'amber'}>{data.status}</Chip></dd>
                </div>
              </dl>
              <Donut total={data.rows_total} success={data.rows_imported}
                warning={data.rows_duplicate} failed={data.rows_failed} />
            </div>
          ) : (
            <ul className="mt-3 divide-y divide-[#F1F2F8]">
              {s.batches.length === 0 && (
                <li className="py-6 text-center text-[12px] text-[#6B7280]">
                  No batches were touched by this import.
                </li>
              )}
              {s.batches.map((b) => (
                <li key={b.batch_code} className="flex items-center justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-[12.5px] font-semibold text-[#1B1B3A]">{b.batch_code}</p>
                    <p className="truncate text-[11.5px] text-[#6B7280]">
                      {b.title || 'Untitled project'} · Section {b.section ?? '—'} · {b.students} students
                      {b.guide ? ` · ${b.guide}` : ''}
                    </p>
                  </div>
                  <Chip tone={b.outcome === 'Created' ? 'green' : 'blue'}>{b.outcome}</Chip>
                </li>
              ))}
            </ul>
          )}

          {data.issues.length > 0 && (
            <div className="mt-3 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] p-3">
              <p className="text-[11.5px] font-medium text-[#92400E]">
                {data.issue_count} row{data.issue_count === 1 ? '' : 's'} needed attention
              </p>
              <ul className="mt-1 space-y-0.5">
                {data.issues.slice(0, 5).map((i, n) => (
                  <li key={n} className="text-[11px] leading-snug text-[#78350F]">
                    Sheet row {i.row ?? '—'}: {i.message}
                  </li>
                ))}
              </ul>
              {data.issue_count > 5 && (
                <p className="mt-1 text-[11px] text-[#92400E]">
                  The full list is in the report.
                </p>
              )}
            </div>
          )}
        </div>

        {/* --------------------------------------------- imported batches */}
        <div className={cn(CARD, 'p-4')}>
          <div className="flex items-center justify-between">
            <h2 className="text-[13.5px] font-bold text-[#1B1B3A]">Recent Imported Batches</h2>
            <Link href="/trainer/batches" className="text-[11.5px] font-medium text-[#2563EB] hover:underline">
              View All
            </Link>
          </div>
          <ul className="mt-1 divide-y divide-[#F1F2F8]">
            {s.batches.length === 0 && (
              <li className="py-6 text-center text-[12px] text-[#6B7280]">Nothing to show.</li>
            )}
            {s.batches.slice(0, 6).map((b) => (
              <li key={b.batch_code} className="flex items-start gap-3 py-2.5">
                <span className="mt-0.5 shrink-0 rounded-md bg-[#EFF6FF] px-2 py-1.5 text-[11px] font-semibold text-[#1D4ED8]">
                  {b.batch_code}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12px] font-medium text-[#1B1B3A]"
                    title={b.title ?? undefined}>
                    {b.title || 'Untitled project'}
                  </p>
                  <p className="mt-0.5 text-[11px] text-[#6B7280]">
                    {b.batch_no ? `Batch ${b.batch_no} · ` : ''}
                    Section {b.department ?? ''}{b.section ? `-${b.section}` : ''} · {b.students} Students
                  </p>
                </div>
                <div className="shrink-0 text-right">
                  <Chip tone="green">Imported</Chip>
                  <p className="mt-1 text-[10.5px] text-[#9CA3AF]">{fmtTime(b.created_at)}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* -------------------------------------------------------- history */}
      <div className={cn(CARD, 'p-4')}>
        <h2 className="text-[13.5px] font-bold text-[#1B1B3A]">Import History</h2>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[11.5px]">
            <thead className="text-[#6B7280]">
              <tr className="border-b border-[#E5E7EB]">
                {['File Name', 'Imported By', 'Imported On', 'Total', 'Success',
                  'Warnings', 'Failed', 'Status', 'Report'].map((h) => (
                  <th key={h} className="whitespace-nowrap py-2 pr-3 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F2F8]">
              {history.length === 0 && (
                <tr><td colSpan={9} className="py-6 text-center text-[#6B7280]">
                  No imports yet.
                </td></tr>
              )}
              {history.map((r) => (
                <tr key={r.id} className={cn(r.id === data.id && 'bg-[#F7F9FF]')}>
                  <td className="py-2 pr-3">
                    <Link href={`/trainer/imports/${r.id}`}
                      className="font-medium text-[#2563EB] hover:underline">
                      {r.file_name}
                    </Link>
                  </td>
                  <td className="py-2 pr-3 text-[#4B5563]">{r.imported_by ?? '—'}</td>
                  <td className="whitespace-nowrap py-2 pr-3 text-[#4B5563]">{fmtWhen(r.started_at)}</td>
                  <td className="py-2 pr-3 text-[#4B5563]">{r.rows_total}</td>
                  <td className="py-2 pr-3 font-medium text-[#16A34A]">{r.rows_imported}</td>
                  <td className="py-2 pr-3 font-medium text-[#D97706]">{r.rows_duplicate}</td>
                  <td className="py-2 pr-3 font-medium text-[#DC2626]">{r.rows_failed}</td>
                  <td className="py-2 pr-3">
                    <Chip tone={r.rows_failed && !r.rows_imported ? 'red'
                      : r.rows_failed || r.rows_duplicate ? 'amber' : 'green'}>{r.status}</Chip>
                  </td>
                  <td className="py-2 pr-3">
                    <button type="button" aria-label={`Download report for ${r.file_name}`}
                      onClick={() => downloadImportReport(r.id, r.import_code)}
                      className="rounded p-1 text-[#2563EB] hover:bg-[#F4F7FF]">
                      <Download className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start gap-2">
      <dt className="w-[104px] shrink-0 text-[#6B7280]">{label}</dt>
      <dd className="min-w-0 break-words font-medium text-[#1B1B3A]">{value}</dd>
    </div>
  )
}

const TONES: Record<string, string> = {
  green: 'bg-[#DCFCE7] text-[#16A34A]',
  violet: 'bg-[#EDE9FE] text-[#7C3AED]',
  blue: 'bg-[#DBEAFE] text-[#2563EB]',
  amber: 'bg-[#FEF3C7] text-[#D97706]',
  red: 'bg-[#FEE2E2] text-[#DC2626]',
}

function Kpi({ icon, tone, value, label }: {
  icon: React.ReactNode; tone: keyof typeof TONES | string; value: number; label: string
}) {
  return (
    <div className="flex items-center gap-2.5 p-3.5">
      <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
        TONES[tone] ?? TONES.blue)}>
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-[19px] font-bold leading-tight text-[#1B1B3A]">{value}</span>
        <span className="block truncate text-[11px] text-[#6B7280]">{label}</span>
      </span>
    </div>
  )
}

/**
 * Row outcomes as one ring. Drawn with stroke offsets rather than a chart
 * library: three arcs and a number do not justify the bundle.
 */
function Donut({ total, success, warning, failed }: {
  total: number; success: number; warning: number; failed: number
}) {
  const R = 52
  const C = 2 * Math.PI * R
  const safe = total || 1
  const seg = (n: number) => (n / safe) * C

  let offset = 0
  const arcs = [
    { value: success, color: '#16A34A' },
    { value: warning, color: '#D97706' },
    { value: failed, color: '#DC2626' },
  ].map((a) => {
    const dash = seg(a.value)
    const arc = { ...a, dash, offset }
    offset += dash
    return arc
  })

  return (
    <figure className="mx-auto">
      <svg viewBox="0 0 140 140" className="h-[150px] w-[150px]" role="img"
        aria-label={`${total} rows: ${success} success, ${warning} warnings, ${failed} failed`}>
        <circle cx="70" cy="70" r={R} fill="none" stroke="#F1F2F8" strokeWidth="16" />
        {arcs.filter((a) => a.value > 0).map((a) => (
          <circle key={a.color} cx="70" cy="70" r={R} fill="none" stroke={a.color} strokeWidth="16"
            strokeDasharray={`${a.dash} ${C - a.dash}`} strokeDashoffset={-a.offset}
            transform="rotate(-90 70 70)" strokeLinecap="butt" />
        ))}
        <text x="70" y="66" textAnchor="middle" className="fill-[#1B1B3A] text-[22px] font-bold">
          {total}
        </text>
        <text x="70" y="84" textAnchor="middle" className="fill-[#6B7280] text-[10px]">
          Total Rows
        </text>
      </svg>
      <figcaption className="mt-1 flex flex-wrap justify-center gap-x-3 gap-y-1 text-[10.5px] text-[#4B5563]">
        <span className="flex items-center gap-1">
          <i className="h-2 w-2 rounded-full bg-[#16A34A]" /> Success ({success})
        </span>
        <span className="flex items-center gap-1">
          <i className="h-2 w-2 rounded-full bg-[#D97706]" /> Warnings ({warning})
        </span>
        <span className="flex items-center gap-1">
          <i className="h-2 w-2 rounded-full bg-[#DC2626]" /> Failed ({failed})
        </span>
      </figcaption>
    </figure>
  )
}
