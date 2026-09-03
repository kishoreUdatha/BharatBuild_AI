'use client'

/**
 * Monthly Attendance.
 *
 * The register a college files: every day of the month across the top, both
 * sessions under each day, one row per student. The daily screen answers "who
 * is here now"; this answers the question a trainer actually gets asked -
 * has this student been drifting, and is anyone heading for a shortage.
 *
 * Weekends stay as columns rather than being dropped. A calendar with holes
 * where Saturdays should be is no longer a calendar, and the gaps are exactly
 * what the eye scans for. They are drawn greyed and never counted.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle, CalendarDays, ChevronLeft, ChevronRight, Clock, Download,
  Search,
} from 'lucide-react'
import { CARD, Failed, Loading } from '@/components/trainer/primitives'
import { apiClient } from '@/lib/api-client'
import { errorText } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const FIELD = 'h-8 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px] ' +
  'text-[#374151] outline-none focus:border-[#2563EB]'

interface Mark { status: string; code: string; remarks: string | null }
interface DayCell { date: string; forenoon: Mark | null; afternoon: Mark | null }

interface StudentMonth {
  student_id: string
  roll_number: string | null
  full_name: string
  batch_code: string
  days: DayCell[]
  sessions_recorded: number
  sessions_attended: number
  absent: number
  present_days: number
  absent_days: number
  late_days: number
  classes_held: number
  breakdown: Record<'forenoon' | 'afternoon', {
    present: number | null
    absent: number | null
    late: number | null
    excused: number | null
    recorded: number
  }>
  overall: number | null
  rate: number | null
  below_floor: boolean
}

/**
 * The bands a college reads a percentage against.
 *
 * A bare number means little on its own; 74% and 76% look alike and are not,
 * because one of them is a shortage notice.
 */
const BANDS = [
  { from: 90, label: 'Excellent', text: 'text-[#166534]', bar: 'bg-[#16A34A]', chip: 'bg-[#DCFCE7]' },
  { from: 75, label: 'Good', text: 'text-[#166534]', bar: 'bg-[#4ADE80]', chip: 'bg-[#F0FDF4]' },
  { from: 50, label: 'Average', text: 'text-[#B45309]', bar: 'bg-[#F59E0B]', chip: 'bg-[#FFFBEB]' },
  { from: 0, label: 'Poor', text: 'text-[#B91C1C]', bar: 'bg-[#DC2626]', chip: 'bg-[#FEF2F2]' },
] as const

const bandOf = (value: number | null) =>
  value === null ? null : BANDS.find((b) => value >= b.from) ?? BANDS[BANDS.length - 1]

const pct = (value: number | null) => (value === null ? '—' : `${value.toFixed(2)}%`)

interface MonthData {
  month: string
  label: string
  days: { date: string; day: number; weekday: string; weekend: boolean; held: boolean }[]
  classes_held: number
  working_days: number
  students: StudentMonth[]
  total: number
  page: number
  per_page: number
  pages: number
  overall: { present: number | null; absent: number | null; late: number | null; recorded: number }
  sessions: { value: string; label: string; window: string }[]
  filters: {
    departments: string[]
    sections: string[]
    batches: { code: string; title: string; section: string | null;
               department: string | null }[]
  }
  statuses: { value: string; label: string; code: string }[]
  floor: number
}

const TONE: Record<string, string> = {
  present: 'bg-[#F0FDF4] text-[#166534]',
  absent: 'bg-[#FEF2F2] text-[#B91C1C]',
  late: 'bg-[#FFFBEB] text-[#B45309]',
  excused: 'bg-[#EEF2FF] text-[#4338CA]',
}

const shiftMonth = (month: string, by: number) => {
  const [y, m] = month.split('-').map(Number)
  const d = new Date(y, m - 1 + by, 1)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

type Tab = 'calendar' | 'percentage' | 'summary'

export default function MonthlyAttendancePage() {
  const [data, setData] = useState<MonthData | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('calendar')

  const [summary, setSummary] = useState<Summary | null>(null)
  const [month, setMonth] = useState('')
  const [filters, setFilters] = useState({ department: '', section: '', batch_code: '' })
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const load = useCallback(async () => {
    setError('')
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
      if (month) params.set('month', month)
      if (filters.department) params.set('department', filters.department)
      if (filters.section) params.set('section', filters.section)
      if (filters.batch_code) params.set('batch_code', filters.batch_code)
      if (search.trim()) params.set('search', search.trim())
      const next = await apiClient.get<MonthData>(`/trainer/attendance/month?${params}`)
      setData(next)
      setMonth((m) => m || next.month)
    } catch (err: any) {
      setError(errorText(err, 'That month could not be loaded.'))
    }
  }, [month, filters, search, page, perPage])

  // Typing a name should not fire a request per keystroke.
  useEffect(() => {
    const id = setTimeout(load, search ? 300 : 0)
    return () => clearTimeout(id)
  }, [load, search])

  // Only when the tab is opened, and rolled up over every student rather
  // than the page - a summary that changes when you paginate is worse than
  // none, because it still looks authoritative.
  useEffect(() => {
    if (tab !== 'summary' || !data) return
    let alive = true
    const params = new URLSearchParams({ month: data.month })
    if (filters.department) params.set('department', filters.department)
    if (filters.section) params.set('section', filters.section)
    if (filters.batch_code) params.set('batch_code', filters.batch_code)
    setSummary(null)
    apiClient.get<Summary>(`/trainer/attendance/summary?${params}`)
      .then((next) => { if (alive) setSummary(next) })
      .catch(() => { if (alive) setSummary(null) })
    return () => { alive = false }
  }, [tab, data, filters])

  const set = (patch: Partial<typeof filters>) => {
    setPage(1)
    setFilters((f) => {
      const next = { ...f, ...patch }
      if (('department' in patch || 'section' in patch) && next.batch_code) {
        const still = data?.filters.batches.find((b) => b.code === next.batch_code)
        const fits = still
          && (!next.department || still.department === next.department)
          && (!next.section || (still.section ?? '') === next.section)
        if (!fits) next.batch_code = ''
      }
      return next
    })
  }

  const from = useMemo(() => (data ? (data.page - 1) * data.per_page + 1 : 0), [data])
  const to = useMemo(
    () => (data ? Math.min(data.page * data.per_page, data.total) : 0), [data])

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading the month…" />

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className="text-[18px] font-bold leading-none text-[#1B1B3A]">
          Monthly Attendance
        </h1>
        <Link href="/trainer/attendance"
          className="text-[11.5px] font-medium text-[#2563EB] hover:underline">
          Take today’s register
        </Link>
        <span className="text-[11.5px] text-[#9CA3AF]">{data.total} students</span>
      </div>

      {/* ------------------------------------------------- filters + overall */}
      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_auto]">
        <div className={cn(CARD, 'flex flex-wrap items-center gap-1.5 p-3')}>
          {/* h-8 to match the fields beside it. Without it the box sized to
              its own icons and sat 9px shorter than everything on the row. */}
          <span className="flex h-8 items-center gap-0.5 rounded-lg border border-[#D1D5DB] bg-white px-1">
            <button type="button" aria-label="Previous month"
              onClick={() => { setPage(1); setMonth(shiftMonth(data.month, -1)) }}
              className="flex h-6 w-6 items-center justify-center rounded text-[#6B7280] hover:bg-[#F4F5FA]">
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="min-w-[96px] text-center text-[11.5px] font-medium text-[#1B1B3A]">
              {data.label}
            </span>
            <button type="button" aria-label="Next month"
              onClick={() => { setPage(1); setMonth(shiftMonth(data.month, 1)) }}
              className="flex h-6 w-6 items-center justify-center rounded text-[#6B7280] hover:bg-[#F4F5FA]">
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </span>
          <select aria-label="Branch" value={filters.department} className={FIELD}
            onChange={(e) => set({ department: e.target.value })}>
            <option value="">All branches</option>
            {data.filters.departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select aria-label="Section" value={filters.section} className={FIELD}
            onChange={(e) => set({ section: e.target.value })}>
            <option value="">All sections</option>
            {data.filters.sections.map((x) => <option key={x} value={x}>Section {x}</option>)}
          </select>
          <select aria-label="Batch" value={filters.batch_code} className={FIELD}
            onChange={(e) => set({ batch_code: e.target.value })}>
            <option value="">All my batches</option>
            {data.filters.batches.map((b) => (
              <option key={b.code} value={b.code}>{b.code}</option>
            ))}
          </select>
          <span className="relative">
            <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
            <input value={search} aria-label="Search students"
              onChange={(e) => { setSearch(e.target.value); setPage(1) }}
              placeholder="Name or roll number"
              className={cn(FIELD, 'w-[168px] pl-7')} />
          </span>
          <button type="button" onClick={() => exportCsv(data)}
            className="ml-auto flex h-8 items-center gap-1.5 rounded-lg border border-[#D1D5DB] bg-white px-2.5 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
            <Download className="h-3.5 w-3.5" /> Export
          </button>
        </div>

        {/* The cohort's month, across every student - not just this page. */}
        <div className={cn(CARD, 'flex items-center gap-5 px-4 py-3')}>
          <Stat label="Present %" value={data.overall.present} tone="text-[#166534]" />
          <Stat label="Absent %" value={data.overall.absent} tone="text-[#B91C1C]" />
          <Stat label="Late %" value={data.overall.late} tone="text-[#B45309]" />
          <span>
            <span className="block text-[10.5px] text-[#6B7280]">Classes Held</span>
            <span className="block text-[15px] font-bold text-[#2563EB]">
              {data.classes_held}{' '}
              <span className="text-[11px] font-normal text-[#9CA3AF]">
                / {data.working_days}
              </span>
            </span>
          </span>
        </div>
      </div>

      {/* ------------------------------------------------------------- views */}
      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="flex flex-wrap gap-1 border-b border-[#E5E7EB] px-2">
          {([['calendar', 'Attendance Calendar'], ['percentage', 'Percentage View'],
             ['summary', 'Summary Report']] as const).map(([key, label]) => (
            <button key={key} type="button" onClick={() => setTab(key)}
              className={cn('-mb-px border-b-2 px-3 py-2 text-[12.5px] transition-colors',
                tab === key
                  ? 'border-[#2563EB] font-semibold text-[#2563EB]'
                  : 'border-transparent text-[#6B7280] hover:text-[#374151]')}>
              {label}
            </button>
          ))}
        </div>

        {data.overall.recorded === 0 ? (
          <p className="flex items-center justify-center gap-2 px-4 py-12 text-[12.5px] text-[#6B7280]">
            <CalendarDays className="h-4 w-4" />
            No attendance was recorded in {data.label}.
          </p>
        ) : tab === 'calendar' ? (
          <CalendarView data={data} from={from} />
        ) : tab === 'percentage' ? (
          <PercentageView data={data} />
        ) : (
          <SummaryView summary={summary} />
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#E5E7EB] px-3.5 py-2">
          <p className="text-[11.5px] text-[#6B7280]">
            Showing {data.total === 0 ? 0 : from} to {to} of {data.total} students
          </p>
          <div className="flex items-center gap-1.5">
            <select value={perPage} aria-label="Rows per page"
              onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
              className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px]">
              {[10, 25, 50].map((n) => <option key={n} value={n}>{n} per page</option>)}
            </select>
            <button type="button" disabled={data.page <= 1} onClick={() => setPage(data.page - 1)}
              className="flex h-7 items-center gap-1 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px] text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
              <ChevronLeft className="h-3.5 w-3.5" /> Previous
            </button>
            <span className="text-[11.5px] text-[#6B7280]">
              Page {data.page} of {data.pages}
            </span>
            <button type="button" disabled={data.page >= data.pages}
              onClick={() => setPage(data.page + 1)}
              className="flex h-7 items-center gap-1 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px] text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
              Next <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- the views

function CalendarView({ data, from }: { data: MonthData; from: number }) {
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-left">
        <thead>
          <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC]">
            <Sticky head className="left-0 min-w-[54px]">#</Sticky>
            <Sticky head className="left-[54px] min-w-[104px]">Roll Number</Sticky>
            <Sticky head className="left-[158px] min-w-[150px]">Student Name</Sticky>
            {data.days.map((d) => (
              <th key={d.date} colSpan={2}
                className={cn('border-l border-[#F1F2F8] px-1 pt-1.5 text-center text-[10px] font-semibold',
                  d.weekend ? 'bg-[#F4F5FA] text-[#C7CAD6]' : 'text-[#374151]')}>
                <span className="block leading-none">
                  {String(d.day).padStart(2, '0')}
                </span>
                <span className="block text-[9px] font-normal text-[#9CA3AF]">
                  {d.weekday}
                </span>
                <span className="mt-0.5 flex">
                  {['S1', 'S2'].map((s) => (
                    <span key={s}
                      className="w-[19px] text-[8.5px] font-medium text-[#2563EB]">
                      {s}
                    </span>
                  ))}
                </span>
              </th>
            ))}
            <Sticky head right className="right-[108px] min-w-[74px] text-right">
              Present %
              <span className="block text-[9px] font-normal text-[#9CA3AF]">
                (of {data.classes_held})
              </span>
            </Sticky>
            <Sticky head right className="right-[54px] min-w-[54px] text-right">
              Absent
            </Sticky>
            <Sticky head right className="right-0 min-w-[54px] text-right">
              Late
            </Sticky>
          </tr>
        </thead>
        <tbody>
          {data.students.map((s, i) => (
            <tr key={s.student_id}
              className="border-b border-[#F1F2F8] last:border-0 hover:bg-[#F9FAFC]">
              <Sticky className="left-0 text-[#9CA3AF]">{from + i}</Sticky>
              <Sticky className="left-[54px] font-mono text-[10.5px]">
                {s.roll_number ?? '—'}
              </Sticky>
              <Sticky className="left-[158px]">
                <span className="block truncate text-[12px] text-[#1B1B3A]">{s.full_name}</span>
                <span className="block truncate text-[9.5px] text-[#9CA3AF]">{s.batch_code}</span>
              </Sticky>
              {s.days.map((cell, di) => {
                const day = data.days[di]
                return ([cell.forenoon, cell.afternoon] as const).map((mark, si) => (
                  <td key={`${cell.date}-${si}`}
                    className={cn('px-0 py-1 text-center',
                      si === 0 && 'border-l border-[#F1F2F8]',
                      day.weekend && 'bg-[#F9FAFC]')}>
                    <span
                      title={`${cell.date} · ${si === 0 ? 'Forenoon' : 'Afternoon'}: `
                        + (mark ? mark.status : 'not taken')
                        + (mark?.remarks ? ` — ${mark.remarks}` : '')}
                      className={cn('mx-auto flex h-[18px] w-[17px] items-center justify-center rounded-[3px] text-[9.5px] font-bold',
                        mark ? TONE[mark.status] : 'text-[#D1D5DB]')}>
                      {mark ? mark.code : '–'}
                    </span>
                  </td>
                ))
              })}
              <Sticky right className="right-[108px] text-right">
                <span className={cn('text-[12px] font-bold',
                  s.rate === null ? 'text-[#9CA3AF]'
                    : s.below_floor ? 'text-[#B91C1C]' : 'text-[#166534]')}>
                  {s.rate === null ? '—' : `${s.rate.toFixed(2)}%`}
                </span>
              </Sticky>
              <Sticky right className="right-[54px] text-right text-[12px] font-semibold text-[#B91C1C]">
                {s.absent_days}
              </Sticky>
              <Sticky right className="right-0 text-right text-[12px] font-semibold text-[#B45309]">
                {s.late_days}
              </Sticky>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Percentage View - the month read session by session.
 *
 * A single overall figure hides the pattern that matters: a student who never
 * misses a morning but keeps missing the afternoon looks average, and is not.
 * Each session is scored against its own register, so a session the college
 * never took shows as nothing rather than as everybody being absent.
 */
function PercentageView({ data }: { data: MonthData }) {
  const sessions = [
    { key: 'forenoon' as const, title: 'Session 1 (Morning)' },
    { key: 'afternoon' as const, title: 'Session 2 (Afternoon)' },
  ]

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[1000px] border-collapse text-left">
          <thead>
            <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11.5px] font-semibold text-[#374151]">
              <th rowSpan={2} className="w-10 px-2 py-1.5">#</th>
              <th rowSpan={2} className="min-w-[104px] px-2 py-1.5">Roll Number</th>
              <th rowSpan={2} className="min-w-[150px] px-2 py-1.5">Student Name</th>
              {sessions.map((s) => (
                <th key={s.key} colSpan={3}
                  className="border-l border-[#E5E7EB] px-2 py-1.5 text-center">
                  {s.title}
                </th>
              ))}
              <th colSpan={5} className="border-l border-[#E5E7EB] px-2 py-1.5 text-center">
                Overall (both sessions)
              </th>
            </tr>
            <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[10.5px] font-medium text-[#6B7280]">
              {sessions.map((s) => (
                ['Present %', 'Absent %', 'Late %'].map((h, i) => (
                  <th key={`${s.key}-${h}`}
                    className={cn('px-2 py-1 text-right', i === 0 && 'border-l border-[#E5E7EB]')}>
                    {h}
                  </th>
                ))
              ))}
              <th className="border-l border-[#E5E7EB] px-2 py-1 text-right">Overall %</th>
              <th className="px-2 py-1 text-right">Present</th>
              <th className="px-2 py-1 text-right">Absent</th>
              <th className="px-2 py-1 text-right">Late</th>
              <th className="px-2 py-1 text-right">Classes</th>
            </tr>
          </thead>
          <tbody>
            {data.students.map((s, i) => {
              const band = bandOf(s.overall)
              return (
                <tr key={s.student_id}
                  className="border-b border-[#F1F2F8] text-[11.5px] last:border-0 hover:bg-[#F9FAFC]">
                  <td className="px-2 py-1.5 text-[#9CA3AF]">
                    {(data.page - 1) * data.per_page + i + 1}
                  </td>
                  <td className="px-2 py-1.5 font-mono text-[10.5px]">{s.roll_number ?? '—'}</td>
                  <td className="px-2 py-1.5">
                    <span className="block truncate text-[12px] text-[#1B1B3A]">{s.full_name}</span>
                    <span className="block truncate text-[9.5px] text-[#9CA3AF]">{s.batch_code}</span>
                  </td>

                  {sessions.map((session) => {
                    const b = s.breakdown[session.key]
                    return (
                      <>
                        <td key={`${session.key}-p`}
                          className="border-l border-[#F1F2F8] px-2 py-1.5 text-right font-medium text-[#166534]">
                          {pct(b.present)}
                        </td>
                        <td key={`${session.key}-a`}
                          className="px-2 py-1.5 text-right font-medium text-[#B91C1C]">
                          {pct(b.absent)}
                        </td>
                        <td key={`${session.key}-l`}
                          className="px-2 py-1.5 text-right font-medium text-[#B45309]">
                          {pct(b.late)}
                        </td>
                      </>
                    )
                  })}

                  <td className="border-l border-[#F1F2F8] px-2 py-1.5 text-right">
                    <span className={cn('block font-bold', band?.text ?? 'text-[#9CA3AF]')}>
                      {pct(s.overall)}
                    </span>
                    {/* The bar is what makes a column of numbers scannable -
                        you find the short ones without reading any of them. */}
                    <span className="mt-0.5 block h-1 w-full overflow-hidden rounded-full bg-[#F1F2F8]">
                      <span className={cn('block h-full rounded-full', band?.bar ?? '')}
                        style={{ width: `${s.overall ?? 0}%` }} />
                    </span>
                  </td>
                  <td className="px-2 py-1.5 text-right font-medium text-[#1B1B3A]">
                    {s.present_days}
                  </td>
                  <td className="px-2 py-1.5 text-right font-medium text-[#B91C1C]">
                    {s.absent_days}
                  </td>
                  <td className="px-2 py-1.5 text-right font-medium text-[#B45309]">
                    {s.late_days}
                  </td>
                  <td className="px-2 py-1.5 text-right text-[#6B7280]">{s.classes_held}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-[#E5E7EB] bg-[#F9FAFC] px-3.5 py-2">
        {BANDS.map((b, i) => (
          <span key={b.label} className="flex items-center gap-1.5 text-[11px]">
            <span className={cn('h-3 w-3 rounded', b.chip)} />
            <span className={cn('font-medium', b.text)}>
              {i === 0 ? '90% and above' : i === BANDS.length - 1
                ? `Below ${BANDS[i - 1].from}%`
                : `${b.from}% – ${BANDS[i - 1].from - 1}%`}
            </span>
            <span className="text-[#9CA3AF]">{b.label}</span>
          </span>
        ))}
        <span className="ml-auto text-[10.5px] text-[#6B7280]">
          Percentages are over the sessions actually recorded, so a register
          nobody took counts against nobody.
        </span>
      </div>
    </>
  )
}

interface Summary {
  label: string
  students: number
  classes_held: number
  working_days: number
  marked: number
  counts: { present: number; absent: number; late: number; excused: number }
  shares: { present: number | null; absent: number | null; late: number | null }
  overall: number | null
  sessions: {
    value: string; label: string; window: string; classes_held: number
    recorded: number; present: number | null; absent: number | null; late: number | null
  }[]
  by_day: {
    date: string; day: number; weekday: string; weekend: boolean
    held: boolean; rate: number | null
  }[]
  top: { student_id: string; full_name: string; roll_number: string | null; overall: number | null }[]
  bottom: { student_id: string; full_name: string; roll_number: string | null; overall: number | null }[]
  below_floor: number
  trend: { month: string; label: string; rate: number | null }[]
  floor: number
}

/**
 * Summary Report.
 *
 * Every figure is over the whole cohort the filters select, never the page
 * being shown. Colour carries meaning here - present, late, absent - so every
 * mark is also labelled: green and red are the pair colour-blind readers
 * cannot separate, and a register is not a chart to guess at.
 */
function SummaryView({ summary }: { summary: Summary | null }) {
  if (!summary) return <Loading label="Rolling up the month…" />
  if (summary.marked === 0) {
    return (
      <p className="flex items-center justify-center gap-2 px-4 py-12 text-[12.5px] text-[#6B7280]">
        <CalendarDays className="h-4 w-4" />
        Nothing was recorded in {summary.label}, so there is nothing to summarise.
      </p>
    )
  }

  const slices = [
    { key: 'present', label: 'Present', value: summary.counts.present,
      share: summary.shares.present, colour: '#16A34A' },
    { key: 'absent', label: 'Absent', value: summary.counts.absent,
      share: summary.shares.absent, colour: '#DC2626' },
    { key: 'late', label: 'Late', value: summary.counts.late,
      share: summary.shares.late, colour: '#F59E0B' },
  ].filter((x) => x.value > 0)

  return (
    <div className="space-y-3 p-3.5">
      <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Overall Attendance" sub="(average)"
          value={summary.overall === null ? '—' : `${summary.overall.toFixed(2)}%`}
          tone="text-[#16A34A]" />
        <Kpi label="Students" sub="(in scope)" value={String(summary.students)}
          tone="text-[#1B1B3A]" />
        <Kpi label="Present" sub={`(${(summary.shares.present ?? 0).toFixed(2)}%)`}
          value={String(summary.counts.present)} tone="text-[#16A34A]" />
        <Kpi label="Absent" sub={`(${(summary.shares.absent ?? 0).toFixed(2)}%)`}
          value={String(summary.counts.absent)} tone="text-[#B91C1C]" />
        <Kpi label="Late" sub={`(${(summary.shares.late ?? 0).toFixed(2)}%)`}
          value={String(summary.counts.late)} tone="text-[#B45309]" />
        <Kpi label="Classes Held" sub={`of ${summary.working_days} working days`}
          value={String(summary.classes_held)} tone="text-[#2563EB]" />
      </div>

      <div className="grid gap-3 xl:grid-cols-[300px_minmax(0,1fr)]">
        <section className="rounded-xl border border-[#E5E7EB] p-3.5">
          <h3 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">
            Attendance Distribution
          </h3>
          <div className="flex items-center gap-4">
            <Donut slices={slices} total={summary.marked} />
            <dl className="flex-1 space-y-1.5">
              {slices.map((sl) => (
                <div key={sl.key} className="flex items-center gap-2 text-[11.5px]">
                  <span className="h-2.5 w-2.5 shrink-0 rounded-sm"
                    style={{ background: sl.colour }} />
                  <dt className="flex-1 text-[#6B7280]">{sl.label}</dt>
                  <dd className="font-semibold text-[#1B1B3A]">
                    {(sl.share ?? 0).toFixed(2)}%
                    <span className="ml-1 font-normal text-[#9CA3AF]">({sl.value})</span>
                  </dd>
                </div>
              ))}
              <div className="flex items-center justify-between border-t border-[#F1F2F8] pt-1.5 text-[11.5px]">
                <dt className="text-[#6B7280]">Total marked</dt>
                <dd className="font-semibold text-[#1B1B3A]">{summary.marked}</dd>
              </div>
            </dl>
          </div>
        </section>

        <section className="rounded-xl border border-[#E5E7EB] p-3.5">
          <h3 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">
            Attendance Trend{' '}
            <span className="font-normal text-[#9CA3AF]">overall %, last 6 months</span>
          </h3>
          <TrendLine points={summary.trend} />
        </section>
      </div>

      <section className="rounded-xl border border-[#E5E7EB] p-3.5">
        <h3 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">
          Session Wise Overview
        </h3>
        <table className="w-full border-collapse text-left text-[11.5px]">
          <thead>
            <tr className="border-b border-[#E5E7EB] text-[11px] font-semibold text-[#6B7280]">
              <th className="px-2 py-1.5">Session</th>
              <th className="px-2 py-1.5 text-right">Sessions Taken</th>
              <th className="px-2 py-1.5 text-right">Present %</th>
              <th className="px-2 py-1.5 text-right">Absent %</th>
              <th className="px-2 py-1.5 text-right">Late %</th>
            </tr>
          </thead>
          <tbody>
            {summary.sessions.map((sess) => (
              <tr key={sess.value} className="border-b border-[#F1F2F8]">
                <td className="px-2 py-1.5">
                  <span className="block font-medium text-[#1B1B3A]">{sess.label}</span>
                  <span className="block text-[10.5px] text-[#9CA3AF]">{sess.window}</span>
                </td>
                <td className="px-2 py-1.5 text-right text-[#6B7280]">{sess.recorded}</td>
                <td className="px-2 py-1.5 text-right font-semibold text-[#166534]">
                  {sess.present === null ? '—' : `${sess.present.toFixed(2)}%`}
                </td>
                <td className="px-2 py-1.5 text-right font-semibold text-[#B91C1C]">
                  {sess.absent === null ? '—' : `${sess.absent.toFixed(2)}%`}
                </td>
                <td className="px-2 py-1.5 text-right font-semibold text-[#B45309]">
                  {sess.late === null ? '—' : `${sess.late.toFixed(2)}%`}
                </td>
              </tr>
            ))}
            <tr className="bg-[#F9FAFC] font-semibold">
              <td className="px-2 py-1.5 text-[#1B1B3A]">Overall (both sessions)</td>
              <td className="px-2 py-1.5 text-right text-[#6B7280]">{summary.marked}</td>
              <td className="px-2 py-1.5 text-right text-[#166534]">
                {(summary.shares.present ?? 0).toFixed(2)}%
              </td>
              <td className="px-2 py-1.5 text-right text-[#B91C1C]">
                {(summary.shares.absent ?? 0).toFixed(2)}%
              </td>
              <td className="px-2 py-1.5 text-right text-[#B45309]">
                {(summary.shares.late ?? 0).toFixed(2)}%
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <div className="grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
        <section className="rounded-xl border border-[#E5E7EB] p-3.5">
          <h3 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">
            Attendance by Day{' '}
            <span className="font-normal text-[#9CA3AF]">overall %</span>
          </h3>
          <DayBars days={summary.by_day} />
        </section>

        <TopBottom summary={summary} />
      </div>

      <p className="rounded-lg bg-[#F9FAFC] px-3 py-2 text-[10.5px] leading-relaxed text-[#6B7280]">
        Percentages are over the sessions actually recorded, so a register nobody
        took counts against nobody. Late counts as attended — a student who
        arrived late was there — which is why Present % and Overall % differ.
      </p>
    </div>
  )
}

/** Part-to-whole for three statuses. Every slice is labelled, never colour alone. */
function Donut({ slices, total }: {
  slices: { key: string; label: string; value: number; colour: string }[]
  total: number
}) {
  const R = 46
  const C = 2 * Math.PI * R
  let offset = 0
  return (
    <svg viewBox="0 0 120 120" className="h-[124px] w-[124px] shrink-0"
      role="img" aria-label={`${total} marks: ${slices.map((s) => `${s.label} ${s.value}`).join(', ')}`}>
      <circle cx="60" cy="60" r={R} fill="none" stroke="#F1F2F8" strokeWidth="16" />
      {slices.map((sl) => {
        const share = total ? sl.value / total : 0
        const dash = `${share * C} ${C}`
        const el = (
          <circle key={sl.key} cx="60" cy="60" r={R} fill="none" stroke={sl.colour}
            strokeWidth="16" strokeDasharray={dash}
            strokeDashoffset={-offset * C} transform="rotate(-90 60 60)">
            <title>{`${sl.label}: ${sl.value} (${(share * 100).toFixed(2)}%)`}</title>
          </circle>
        )
        offset += share
        return el
      })}
      <text x="60" y="58" textAnchor="middle"
        className="fill-[#1B1B3A] text-[15px] font-bold">
        {slices.length ? `${(((slices[0]?.value ?? 0) / (total || 1)) * 100).toFixed(0)}%` : '—'}
      </text>
      <text x="60" y="72" textAnchor="middle" className="fill-[#9CA3AF] text-[8px]">
        present
      </text>
    </svg>
  )
}

/** Six months as a line. Months with no register are a gap, not a zero. */
function TrendLine({ points }: {
  points: { month: string; label: string; rate: number | null }[]
}) {
  const W = 560
  const H = 128
  const pad = { l: 30, r: 8, t: 10, b: 20 }
  const step = points.length > 1
    ? (W - pad.l - pad.r) / (points.length - 1) : 0
  const y = (v: number) => pad.t + (1 - v / 100) * (H - pad.t - pad.b)
  const at = (i: number) => pad.l + i * step

  const drawn = points.map((p, i) => ({ ...p, i })).filter((p) => p.rate !== null)
  const path = drawn.map((p, n) =>
    `${n === 0 ? 'M' : 'L'}${at(p.i)},${y(p.rate as number)}`).join(' ')

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
      aria-label={`Attendance trend: ${points.map((p) =>
        `${p.label} ${p.rate === null ? 'no data' : `${p.rate}%`}`).join(', ')}`}>
      {[0, 50, 100].map((v) => (
        <g key={v}>
          <line x1={pad.l} x2={W - pad.r} y1={y(v)} y2={y(v)} stroke="#F1F2F8" />
          <text x={pad.l - 6} y={y(v) + 3} textAnchor="end"
            className="fill-[#9CA3AF] text-[8px]">{v}%</text>
        </g>
      ))}
      {drawn.length > 1 && (
        <path d={path} fill="none" stroke="#16A34A" strokeWidth="2"
          strokeLinejoin="round" strokeLinecap="round" />
      )}
      {drawn.map((p) => (
        <g key={p.month}>
          <circle cx={at(p.i)} cy={y(p.rate as number)} r="4" fill="#16A34A"
            stroke="#fff" strokeWidth="2">
            <title>{`${p.label}: ${p.rate}%`}</title>
          </circle>
          <text x={at(p.i)} y={y(p.rate as number) - 9} textAnchor="middle"
            className="fill-[#166534] text-[8.5px] font-semibold">
            {p.rate}%
          </text>
        </g>
      ))}
      {points.map((p, i) => (
        <text key={p.label} x={at(i)} y={H - 6} textAnchor="middle"
          className="fill-[#9CA3AF] text-[8px]">{p.label}</text>
      ))}
    </svg>
  )
}

/** One bar per day. Days with no register are marked, not drawn as zero. */
function DayBars({ days }: {
  days: { date: string; day: number; weekday: string; weekend: boolean
          held: boolean; rate: number | null }[]
}) {
  const H = 132
  const top = 16
  const floor = H - 18
  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${Math.max(days.length * 22, 200)} ${H}`}
        className="h-[132px] min-w-full" role="img"
        aria-label={days.filter((d) => d.held).map((d) =>
          `${d.day} ${d.weekday}: ${d.rate}%`).join(', ')}>
        {days.map((d, i) => {
          const x = i * 22 + 4
          const h = d.rate === null ? 0 : ((d.rate / 100) * (floor - top))
          return (
            <g key={d.date}>
              {d.rate === null ? (
                <>
                  <line x1={x + 2} x2={x + 12} y1={floor - 3} y2={floor - 3}
                    stroke="#D1D5DB" strokeWidth="2" strokeLinecap="round" />
                  <title>{`${d.day} ${d.weekday}: no class`}</title>
                </>
              ) : (
                <rect x={x} y={floor - h} width="14" height={Math.max(h, 2)} rx="3"
                  fill={d.rate >= 75 ? '#16A34A' : d.rate >= 50 ? '#F59E0B' : '#DC2626'}>
                  <title>{`${d.day} ${d.weekday}: ${d.rate}%`}</title>
                </rect>
              )}
              {d.rate !== null && (
                <text x={x + 7} y={floor - h - 4} textAnchor="middle"
                  className="fill-[#6B7280] text-[7.5px] font-semibold">
                  {Math.round(d.rate)}
                </text>
              )}
              <text x={x + 7} y={H - 8} textAnchor="middle"
                className={cn('text-[7.5px]',
                  d.weekend ? 'fill-[#D1D5DB]' : 'fill-[#9CA3AF]')}>
                {String(d.day).padStart(2, '0')}
              </text>
              <text x={x + 7} y={H - 1} textAnchor="middle"
                className="fill-[#C7CAD6] text-[6.5px]">{d.weekday}</text>
            </g>
          )
        })}
      </svg>
      <p className="mt-1 flex items-center gap-3 text-[10px] text-[#9CA3AF]">
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-[#16A34A]" /> 75%+
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-[#F59E0B]" /> 50–74%
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2 w-2 rounded-sm bg-[#DC2626]" /> below 50%
        </span>
        <span className="flex items-center gap-1">
          <span className="h-0.5 w-3 rounded bg-[#D1D5DB]" /> no class
        </span>
      </p>
    </div>
  )
}

function TopBottom({ summary }: { summary: Summary }) {
  const [side, setSide] = useState<'top' | 'bottom'>('top')
  const list = side === 'top' ? summary.top : summary.bottom
  return (
    <section className="rounded-xl border border-[#E5E7EB] p-3.5">
      <h3 className="mb-2 text-[12.5px] font-semibold text-[#1B1B3A]">
        Top / Bottom Attendance
        {summary.below_floor > 0 && (
          <span className="ml-2 font-normal text-[#B91C1C]">
            {summary.below_floor} below {summary.floor}%
          </span>
        )}
      </h3>
      <div className="mb-2 flex gap-1 border-b border-[#E5E7EB]">
        {([['top', 'Top 5'], ['bottom', 'Bottom 5']] as const).map(([key, label]) => (
          <button key={key} type="button" onClick={() => setSide(key)}
            className={cn('-mb-px border-b-2 px-2.5 py-1.5 text-[11.5px]',
              side === key ? 'border-[#2563EB] font-semibold text-[#2563EB]'
                : 'border-transparent text-[#6B7280] hover:text-[#374151]')}>
            {label}
          </button>
        ))}
      </div>
      {list.length === 0 ? (
        <p className="py-4 text-center text-[11.5px] text-[#9CA3AF]">
          Not enough recorded yet to rank anybody.
        </p>
      ) : (
        <ol className="divide-y divide-[#F1F2F8]">
          {list.map((row, i) => (
            <li key={row.student_id} className="flex items-center gap-2 py-1.5">
              <span className="w-4 text-[11px] text-[#9CA3AF]">{i + 1}</span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[12px] text-[#1B1B3A]">
                  {row.full_name}
                </span>
                <span className="block truncate font-mono text-[9.5px] text-[#9CA3AF]">
                  {row.roll_number ?? '—'}
                </span>
              </span>
              <span className={cn('text-[12px] font-bold',
                (row.overall ?? 0) >= summary.floor ? 'text-[#166534]' : 'text-[#B91C1C]')}>
                {row.overall === null ? '—' : `${row.overall.toFixed(2)}%`}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

function Kpi({ label, sub, value, tone }: {
  label: string; sub: string; value: string; tone: string
}) {
  return (
    <div className="rounded-xl border border-[#E5E7EB] px-3 py-2.5">
      <span className="block text-[10.5px] text-[#6B7280]">{label}</span>
      <span className={cn('block text-[18px] font-bold leading-tight', tone)}>{value}</span>
      <span className="block text-[10px] text-[#9CA3AF]">{sub}</span>
    </div>
  )
}

// ------------------------------------------------------------- small pieces

function Stat({ label, value, tone }: { label: string; value: number | null; tone: string }) {
  return (
    <span>
      <span className="block text-[10.5px] text-[#6B7280]">{label}</span>
      <span className={cn('block text-[15px] font-bold', tone)}>
        {value === null ? '—' : `${value.toFixed(2)}%`}
      </span>
    </span>
  )
}

/**
 * A column that stays put while the days scroll.
 *
 * A grid of single letters is unreadable the moment you cannot see whose row
 * you are on, or what the totals were.
 */
function Sticky({ children, className, head, right }: {
  children: React.ReactNode
  className?: string
  head?: boolean
  right?: boolean
}) {
  const Tag = head ? 'th' : 'td'
  return (
    <Tag className={cn('sticky z-10 px-2 py-1.5',
      head ? 'bg-[#F9FAFC] text-[11.5px] font-semibold text-[#374151]'
           : 'bg-white text-[12px] text-[#1B1B3A]',
      right ? 'border-l border-[#E5E7EB]' : 'border-r border-[#E5E7EB]',
      className)}>
      {children}
    </Tag>
  )
}

/** The month as a file: one row per student, one column per session. */
function exportCsv(data: MonthData) {
  const head = ['Roll Number', 'Student Name', 'Batch']
  for (const d of data.days) head.push(`${d.date} S1`, `${d.date} S2`)
  head.push('Present %', 'Absent Days', 'Late Days', 'Sessions')

  const lines = data.students.map((s) => {
    const cells: (string | number)[] = [s.roll_number ?? '', s.full_name, s.batch_code]
    for (const cell of s.days) {
      cells.push(cell.forenoon?.code ?? '', cell.afternoon?.code ?? '')
    }
    cells.push(s.rate === null ? '' : s.rate, s.absent_days, s.late_days,
      `${s.sessions_attended}/${s.sessions_recorded}`)
    return cells.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')
  })

  const blob = new Blob([[head.join(','), ...lines].join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `attendance-${data.month}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
