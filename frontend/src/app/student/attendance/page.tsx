'use client'

/**
 * Attendance, as the student sees it.
 *
 * Read-only by design: the trainer marks the register, and a student who
 * disagrees argues with a person rather than editing the record. What this
 * screen owes them is the days their rate was built from, so a low rate is
 * arguable instead of merely asserted.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, CalendarDays, ChevronLeft, ChevronRight, ChevronsLeft,
  ChevronsRight, Info, Loader2, Lock, RotateCcw,
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E5E7EB] bg-white'
const PAGE_SIZES = [10, 25, 50]

interface Mark {
  status: string
  code: string
  label: string
  hint: string
}

interface Day {
  date: string
  day: string
  forenoon: Mark | null
  afternoon: Mark | null
  remarks: string | null
  trainer: string | null
  marked_at: string | null
}

interface Month {
  month: string | null
  month_label: string | null
  months: { value: string; label: string }[]
  batch_label: string
  sessions: { key: string; name: string; time: string }[]
  totals: {
    classes: number; present: number; present_pct: number
    absent: number; absent_pct: number; rate: number
    floor: number; below_floor: boolean
  }
  last_updated: string | null
  days: Day[]
}

/** A mark's colour. Never colour alone - the letter and a tooltip carry it. */
const MARK: Record<string, string> = {
  present: 'bg-[#F0FDF4] text-[#166534] border-[#BBF7D0]',
  absent: 'bg-[#FEF2F2] text-[#B91C1C] border-[#FECACA]',
  late: 'bg-[#FFFBEB] text-[#B45309] border-[#FDE68A]',
  excused: 'bg-[#EEF2FF] text-[#4338CA] border-[#C7D2FE]',
}

const fmtDay = (iso: string) =>
  new Date(iso).toLocaleDateString('en-IN',
    { day: '2-digit', month: 'short', year: 'numeric' })

const fmtWhen = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }) : '—'

export default function StudentAttendance() {
  const [data, setData] = useState<Month | null>(null)
  const [failed, setFailed] = useState('')
  const [month, setMonth] = useState('')
  const [size, setSize] = useState(10)
  const [page, setPage] = useState(1)

  const load = useCallback(async (want: string) => {
    try {
      setFailed('')
      const query = want ? `?month=${want}` : ''
      setData(await apiClient.get<Month>(`/student/attendance/month${query}`))
    } catch (err: any) {
      setFailed(err?.response?.data?.detail
        ?? 'Your attendance could not be loaded.')
    }
  }, [])

  useEffect(() => { load(month) }, [load, month])

  const days = data?.days ?? []
  const pages = Math.max(1, Math.ceil(days.length / size))
  const current = Math.min(page, pages)
  const slice = useMemo(
    () => days.slice((current - 1) * size, current * size),
    [days, current, size])

  if (failed) {
    return (
      <p className={cn(CARD, 'flex items-center gap-2 px-4 py-10 text-[12.5px] text-[#B91C1C]')}>
        <AlertCircle className="h-4 w-4" /> {failed}
      </p>
    )
  }
  if (!data) {
    return (
      <p className={cn(CARD, 'flex items-center justify-center gap-2 px-4 py-12 text-[12.5px] text-[#6B7280]')}>
        <Loader2 className="h-4 w-4 animate-spin" /> Loading your attendance…
      </p>
    )
  }

  const t = data.totals
  const dirty = Boolean(month) && month !== data.months[0]?.value

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-baseline gap-2">
          <h1 className="text-[17px] font-bold leading-tight text-[#1B1B3A]">
            Attendance
          </h1>
          <span className="text-[11.5px] text-[#6B7280]">
            Marked by your trainer.
          </span>
        </div>
        <span className="flex h-7 items-center gap-1.5 rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] px-2 text-[11px] font-medium text-[#1D4ED8]">
          <Lock className="h-3.5 w-3.5" /> Read-only
        </span>
      </div>

      {/*
        One band instead of three stacked cards. The figures, the filters and
        the key are all things you read once and then stop looking at, so they
        get one line each rather than a card each - the register itself is what
        the screen is for, and it should start near the top of the screen.
      */}
      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-3.5 py-2">
          <Stat label="Classes" value={String(t.classes)} />
          <Stat label="Present" value={String(t.present)}
            note={`${t.present_pct}%`} tone="text-[#166534]" />
          <Stat label="Absent" value={String(t.absent)}
            note={`${t.absent_pct}%`} tone={t.absent ? 'text-[#B91C1C]' : undefined} />
          <Stat label="Attendance" value={`${t.rate}%`}
            note={t.below_floor ? `below ${t.floor}%` : `min ${t.floor}%`}
            tone={t.below_floor ? 'text-[#B91C1C]' : 'text-[#166534]'} />
          <span className="ml-auto text-[10.5px] text-[#9CA3AF]">
            Updated {fmtWhen(data.last_updated)}
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 border-t border-[#F1F2F8] bg-[#FCFCFD] px-3.5 py-2">
          <span className="text-[11px] text-[#6B7280]">
            Batch <span className="font-medium text-[#374151]">
              {data.batch_label || '—'}
            </span>
          </span>
          <select value={data.month ?? ''} aria-label="Month"
            onChange={(e) => { setMonth(e.target.value); setPage(1) }}
            disabled={data.months.length === 0}
            className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-1.5 text-[11.5px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none disabled:bg-[#F9FAFC]">
            {data.months.length === 0 && <option value="">No records yet</option>}
            {data.months.map((m) => (
              <option key={m.value} value={m.value}>{m.label}</option>
            ))}
          </select>
          {dirty && (
            <button type="button" onClick={() => { setMonth(''); setPage(1) }}
              className="flex h-7 items-center gap-1 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
              <RotateCcw className="h-3 w-3" /> Latest
            </button>
          )}
          <span className="ml-auto flex flex-wrap items-center gap-1.5">
            <Key code="P" tone={MARK.present} label="Present" />
            <Key code="A" tone={MARK.absent} label="Absent" />
            <Key code="L" tone={MARK.late} label="Late" />
            <Key code="E" tone={MARK.excused} label="Excused" />
            <Key code="–" tone="bg-[#F3F4F6] text-[#6B7280] border-[#E5E7EB]"
              label="No class" />
          </span>
        </div>
      </div>

      {t.below_floor && (
        <p className="flex items-start gap-2 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11.5px] text-[#B91C1C]">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>
            You are at {t.rate}% for {data.month_label}, below the {t.floor}%
            requirement. If a row below looks wrong, take the date to your trainer.
          </span>
        </p>
      )}

      {/* -------------------------------------------------------------- table */}
      <div className={cn(CARD, 'overflow-hidden')}>
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-[#F1F2F8] px-3.5 py-2">
          <h2 className="text-[12.5px] font-semibold text-[#1B1B3A]">
            Daily records{data.month_label ? ` — ${data.month_label}` : ''}
          </h2>
          <span className="text-[10.5px] text-[#9CA3AF]">
            {data.sessions.length} sessions a day, newest first
          </span>
        </div>

        {days.length === 0 ? (
          <div className="px-4 py-12 text-center">
            <CalendarDays className="mx-auto h-6 w-6 text-[#D1D5DB]" />
            <p className="mt-2 text-[12.5px] text-[#6B7280]">
              Nothing marked yet. Days appear here as your trainer takes the
              register.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-left">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#F9FAFC] text-[11px] font-semibold text-[#374151]">
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Day</th>
                  {data.sessions.map((s) => (
                    <th key={s.key} className="px-3 py-2 text-center">
                      <span className="block">{s.name.split(' (')[0]}</span>
                      <span className="block text-[9.5px] font-normal text-[#2563EB]">
                        {s.time}
                      </span>
                    </th>
                  ))}
                  <th className="px-3 py-2">Remarks</th>
                  <th className="px-3 py-2">Trainer</th>
                </tr>
              </thead>
              <tbody>
                {slice.map((row) => (
                  <tr key={row.date}
                    className="border-b border-[#F1F2F8] text-[12px] last:border-0">
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1.5 font-medium text-[#1B1B3A]">
                        <CalendarDays className="h-3.5 w-3.5 text-[#9CA3AF]" />
                        {fmtDay(row.date)}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">{row.day}</td>
                    {data.sessions.map((s) => (
                      <td key={s.key} className="px-3 py-2 text-center">
                        <Cell mark={row[s.key as 'forenoon' | 'afternoon']} />
                      </td>
                    ))}
                    <td className="px-3 py-2 text-[#1B1B3A]">
                      {row.remarks ?? <span className="text-[#9CA3AF]">—</span>}
                    </td>
                    <td className="px-3 py-2 text-[11px] text-[#6B7280]">
                      {row.trainer ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#E5E7EB] px-3.5 py-2.5">
          <p className="text-[11px] text-[#6B7280]">
            {days.length === 0
              ? 'No days recorded'
              : `Showing ${(current - 1) * size + 1} to ${Math.min(current * size, days.length)} of ${days.length} days`}
          </p>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1.5 text-[11px] text-[#6B7280]">
              Rows per page
              <select value={size}
                onChange={(e) => { setSize(Number(e.target.value)); setPage(1) }}
                className="h-7 rounded border border-[#D1D5DB] bg-white px-1.5 text-[11px] text-[#1B1B3A] focus:border-[#2563EB] focus:outline-none">
                {PAGE_SIZES.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
            <div className="flex items-center gap-0.5">
              <Pager label="First" disabled={current === 1} onClick={() => setPage(1)}>
                <ChevronsLeft className="h-3.5 w-3.5" />
              </Pager>
              <Pager label="Previous" disabled={current === 1}
                onClick={() => setPage(current - 1)}>
                <ChevronLeft className="h-3.5 w-3.5" />
              </Pager>
              <span className="px-2 text-[11px] text-[#6B7280]">
                Page {current} of {pages}
              </span>
              <Pager label="Next" disabled={current === pages}
                onClick={() => setPage(current + 1)}>
                <ChevronRight className="h-3.5 w-3.5" />
              </Pager>
              <Pager label="Last" disabled={current === pages}
                onClick={() => setPage(pages)}>
                <ChevronsRight className="h-3.5 w-3.5" />
              </Pager>
            </div>
          </div>
        </div>

        <p className="flex items-start gap-2 border-t border-[#E5E7EB] bg-[#F7F9FF] px-3.5 py-2.5 text-[11px] text-[#4B5563]">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#2563EB]" />
          <span>
            A dash means no class was held for that session, not an absence.
            Late and excused sessions count as attended. If a row looks wrong,
            take the date to your trainer — only they can change it.
          </span>
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------- small parts

/** One session's mark. A blank is "no class", which is not an absence. */
function Cell({ mark }: { mark: Mark | null }) {
  if (!mark) {
    return (
      <span title="No class held for this session"
        className="inline-flex h-6 w-7 items-center justify-center rounded border border-[#E5E7EB] bg-[#F3F4F6] text-[11px] text-[#9CA3AF]">
        –
      </span>
    )
  }
  return (
    <span title={mark.hint}
      className={cn('inline-flex h-6 w-7 items-center justify-center rounded border text-[11px] font-semibold',
        MARK[mark.status] ?? MARK.present)}>
      {mark.code}
    </span>
  )
}

/** One figure on the summary line - label, number, and a small qualifier. */
function Stat({ label, value, note, tone }: {
  label: string; value: string; note?: string; tone?: string
}) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="text-[10.5px] text-[#6B7280]">{label}</span>
      <span className={cn('text-[13px] font-bold', tone ?? 'text-[#1B1B3A]')}>
        {value}
      </span>
      {note && <span className="text-[10px] text-[#9CA3AF]">{note}</span>}
    </span>
  )
}

function Key({ code, tone, label }: { code: string; tone: string; label: string }) {
  return (
    <span className="flex items-center gap-1 text-[10.5px] text-[#6B7280]">
      <span className={cn('inline-flex h-5 w-5 items-center justify-center rounded border text-[10px] font-semibold', tone)}>
        {code}
      </span>
      {label}
    </span>
  )
}

function Pager({ label, disabled, onClick, children }: {
  label: string; disabled: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      title={label}
      className="flex h-7 w-7 items-center justify-center rounded border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-30">
      {children}
    </button>
  )
}
