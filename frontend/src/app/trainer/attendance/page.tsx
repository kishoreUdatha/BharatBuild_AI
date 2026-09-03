'use client'

/**
 * Take Attendance.
 *
 * One session at a time, because that is how a register is actually taken:
 * the trainer is standing in a morning class, not reconciling a whole day.
 * The two summary cards keep the other half in view, and the tabs move
 * between them.
 *
 * Marks write themselves shortly after the last click - a register is dozens
 * of small decisions and asking for a Save after each is how a morning's work
 * gets lost to a closed tab. Submitting stays a deliberate act: it says the
 * session is finished, not that it is frozen, and corrections afterwards are
 * still accepted.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, ChevronsLeft,
  ChevronsRight, Loader2, RotateCcw, Save,
} from 'lucide-react'
import { CARD, Failed, Loading } from '@/components/trainer/primitives'
import { apiClient } from '@/lib/api-client'
import { errorText } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const FIELD = 'h-8 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px] ' +
  'text-[#374151] outline-none focus:border-[#2563EB]'

interface Cell {
  status: string | null
  status_label: string
  code: string | null
  remarks: string | null
}

interface Row {
  student_id: string
  roll_number: string | null
  full_name: string
  batch_code: string
  section: string | null
  forenoon: Cell
  afternoon: Cell
  day_percent: number | null
}

interface SessionInfo {
  value: string
  label: string
  window: string
  open: boolean
  live: boolean
  taken_by: string | null
  started_at: string | null
  submitted_at: string | null
  counts: Record<string, number | null>
}

interface Day {
  date: string
  students: Row[]
  total: number
  page: number
  per_page: number
  pages: number
  sessions: SessionInfo[]
  overall_rate: number | null
  marked_total: number
  marked_of: number
  complete: boolean
  kpis: { total: number; present: number; absent: number; late: number; excused: number }
  filters: {
    departments: string[]
    sections: string[]
    batches: { code: string; title: string; section: string | null;
               department: string | null }[]
    department: string | null
    section: string | null
    batch_code: string | null
  }
  statuses: { value: string; label: string; code: string; hint: string }[]
  floor: number
}

type SessionKey = 'forenoon' | 'afternoon'

/** One colour per status, shared by the buttons and the summary figures. */
const TONE: Record<string, { text: string; bg: string; ring: string }> = {
  present: { text: 'text-[#166534]', bg: 'bg-[#F0FDF4]', ring: 'border-[#86EFAC]' },
  absent: { text: 'text-[#B91C1C]', bg: 'bg-[#FEF2F2]', ring: 'border-[#FCA5A5]' },
  late: { text: 'text-[#B45309]', bg: 'bg-[#FFFBEB]', ring: 'border-[#FCD34D]' },
  excused: { text: 'text-[#4338CA]', bg: 'bg-[#EEF2FF]', ring: 'border-[#A5B4FC]' },
}

/** A share of the cohort, for the figures on the session cards. */
const pct = (part: number, whole: number) =>
  whole ? `${((part / whole) * 100).toFixed(2)}%` : '—'

const fmtClock = (iso: string | null) =>
  iso ? new Date(iso).toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit',
  }) : '—'

const SESSION_TITLE: Record<SessionKey, string> = {
  forenoon: 'Session 1 · Morning',
  afternoon: 'Session 2 · Afternoon',
}

export default function TakeAttendancePage() {
  // Read once: the byline is only interesting when another trainer took the
  // register, which is the co-teaching case.
  const meName = useMemo(() => {
    try { return JSON.parse(localStorage.getItem('user') || '{}').full_name ?? null }
    catch { return null }
  }, [])

  const [data, setData] = useState<Day | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState<{ text: string; bad?: boolean } | null>(null)

  // Applied as they change. A filter that needs a second click to take effect
  // reads as broken, and the request it saves is not worth that.
  const [applied, setApplied] = useState({ date: '', department: '', section: '', batch_code: '' })
  const setFilter = (patch: Partial<typeof applied>) => {
    setPage(1)
    setApplied((f) => {
      const next = { ...f, ...patch }
      // A batch chosen under one section must not survive a move to another:
      // it would silently narrow the register to nothing.
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
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [tab, setTab] = useState<SessionKey>('forenoon')

  // Edits not yet written, keyed student -> session. They do not stay here
  // long: a change schedules its own save.
  const [edits, setEdits] = useState<Record<string, { status?: string; remarks?: string }>>({})
  const [savedAt, setSavedAt] = useState<number | null>(null)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  // The timer fires later than the render that scheduled it, so the flush has
  // to read the current edits rather than the ones it closed over.
  const editsRef = useRef(edits)
  editsRef.current = edits
  // What the in-flight request is writing, so an edit made while it is out
  // survives instead of being cleared with the rest.
  const inFlight = useRef<string[]>([])
  const tableTop = useRef<HTMLDivElement>(null)
  // Set by the pager only: a save also reloads, and that must not yank the
  // trainer away from the row they were marking.
  const jumpToTop = useRef(false)
  const saving = useRef(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
      if (applied.date) params.set('date', applied.date)
      if (applied.department) params.set('department', applied.department)
      if (applied.section) params.set('section', applied.section)
      if (applied.batch_code) params.set('batch_code', applied.batch_code)
      setData(await apiClient.get<Day>(`/trainer/attendance/day?${params}`))
      // The pager sits under a long table: changing page swapped the rows
      // above the fold and left the trainer looking at an identical-looking
      // bottom, so nothing appeared to happen. Back to row one - after the
      // rows arrive, and instantly, because a smooth scroll is cancelled by
      // the relayout that replacing them causes.
      if (jumpToTop.current) {
        jumpToTop.current = false
        requestAnimationFrame(() =>
          tableTop.current?.scrollIntoView({ block: 'start' }))
      }
    } catch (err: any) {
      setError(errorText(err, 'That register could not be loaded.'))
    }
  }, [applied, page, perPage])

  useEffect(() => { load() }, [load])


  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current) }, [])

  const key = (studentId: string, session: string) => `${studentId}:${session}`

  const statusOf = (row: Row, session: SessionKey) =>
    edits[key(row.student_id, session)]?.status ?? row[session].status

  const remarksOf = (row: Row, session: SessionKey) =>
    edits[key(row.student_id, session)]?.remarks ?? row[session].remarks

  /**
   * Write shortly after the last change.
   *
   * Remarks are typed rather than clicked, so the wait is long enough not to
   * fire on every keystroke.
   */
  const queueSave = () => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => { void flush() }, 900)
  }

  const setCell = (studentId: string, session: string,
                   patch: { status?: string; remarks?: string }) => {
    setEdits((e) => ({ ...e, [key(studentId, session)]: { ...e[key(studentId, session)], ...patch } }))
    queueSave()
  }

  const flush = async () => {
    if (!data) return
    const current = editsRef.current
    const keys = Object.keys(current)
    if (keys.length === 0) return
    // Never two writes at once. The upsert on the server makes an overlap
    // survivable, but a second request would still be racing the first for
    // the same rows.
    if (saving.current) { queueSave(); return }
    saving.current = true
    if (saveTimer.current) { clearTimeout(saveTimer.current); saveTimer.current = null }
    inFlight.current = keys
    setBusy(true)
    setNotice(null)
    try {
      // One request per session: the API records a session at a time, which is
      // also what keeps each session's "started at" honest.
      for (const session of ['forenoon', 'afternoon'] as const) {
        const marks = data.students
          .map((row) => {
            const edit = current[key(row.student_id, session)]
            if (!edit?.status && !edit?.remarks) return null
            const status = edit.status ?? row[session].status
            if (!status) return null
            return {
              student_id: row.student_id,
              status,
              remarks: edit.remarks ?? row[session].remarks ?? null,
            }
          })
          .filter(Boolean)
        if (marks.length) {
          await apiClient.post('/trainer/attendance', {
            date: data.date, session, batch_code: data.filters.batch_code, marks,
          })
        }
      }
      setSavedAt(Date.now())
      // Only what this request carried is cleared; anything clicked while it
      // was in flight stays pending and schedules its own save.
      setEdits((e) => {
        const rest = { ...e }
        for (const k of inFlight.current) delete rest[k]
        return rest
      })
      await load()
    } catch (err: any) {
      setNotice({ bad: true, text: errorText(err, 'That register could not be saved. '
        + 'Your marks are still on screen — try again.') })
    } finally {
      inFlight.current = []
      saving.current = false
      setBusy(false)
      // Anything clicked while that was in flight still needs writing.
      if (Object.keys(editsRef.current).length > 0) queueSave()
    }
  }

  const goPage = (n: number) => {
    jumpToTop.current = true
    setPage(n)
  }

  const from = useMemo(() => (data ? (data.page - 1) * data.per_page + 1 : 0), [data])
  const to = useMemo(() => (data ? Math.min(data.page * data.per_page, data.total) : 0), [data])
  const pendingCount = Object.keys(edits).length

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading the register…" />

  const active = data.sessions.find((s) => s.value === tab) ?? data.sessions[0]

  return (
    <div className="space-y-3">
      {/* Title and controls on one line. Stacking a heading, a subtitle and
          a card of labelled fields cost 487px before the first student - on a
          laptop that is a register with no students on screen. */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className="text-[18px] font-bold leading-none text-[#1B1B3A]">Take Attendance</h1>
        <Link href="/trainer/attendance/month"
          className="text-[11.5px] font-medium text-[#2563EB] hover:underline">
          Monthly view
        </Link>
        <span className="text-[11.5px] text-[#9CA3AF]">
          {data.total} students
          {data.filters.batch_code ? ` · ${data.filters.batch_code}` : ''}
          {/* A percentage only once both registers are finished - ten present
              out of ten marked is not "100% today". Progress is not repeated
              here: each tab already carries its own marked/total, which is the
              unit a trainer thinks in. A day-wide count of student-sessions is
              a number nobody asked for. */}
          {data.complete && data.overall_rate !== null && (
            <span className="ml-1.5 font-medium text-[#16A34A]">
              {data.overall_rate}% attendance today
            </span>
          )}
        </span>

        {/* The labels are gone because each control says what it is: a date
            field looks like one, and "All branches" reads as its own label. */}
        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <input type="date" aria-label="Date" value={applied.date || data.date}
            className={FIELD} onChange={(e) => setFilter({ date: e.target.value })} />
          <select aria-label="Branch" value={applied.department} className={FIELD}
            onChange={(e) => setFilter({ department: e.target.value })}>
            <option value="">All branches</option>
            {data.filters.departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
          <select aria-label="Section" value={applied.section} className={FIELD}
            onChange={(e) => setFilter({ section: e.target.value })}>
            <option value="">All sections</option>
            {data.filters.sections.map((x) => <option key={x} value={x}>Section {x}</option>)}
          </select>
          <select aria-label="Batch" value={applied.batch_code} className={FIELD}
            onChange={(e) => setFilter({ batch_code: e.target.value })}>
            <option value="">All my batches</option>
            {data.filters.batches.map((b) => (
              <option key={b.code} value={b.code}>{b.code}</option>
            ))}
          </select>
          <button type="button" onClick={load} aria-label="Reload the register" title="Reload"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#D1D5DB] bg-white text-[#6B7280] hover:bg-[#F9FAFB]">
            <RotateCcw className="h-3.5 w-3.5" />
          </button>
          <button type="button" title="Clear the filters"
            onClick={() => setFilter({ date: '', department: '', section: '', batch_code: '' })}
            className="h-8 rounded-lg border border-[#D1D5DB] bg-white px-2.5 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
            Reset
          </button>
        </div>
      </div>

      {notice && (
        <p className={cn('flex items-start gap-1.5 rounded-lg border px-3 py-2 text-[12.5px]',
          notice.bad
            ? 'border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]'
            : 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]')}>
          {notice.bad
            ? <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            : <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
          {notice.text}
        </p>
      )}

      {/* -------------------------------------------------------- the register */}
      <div ref={tableTop} className={cn(CARD, 'scroll-mt-3 overflow-hidden')}>
        {/* The two summary cards folded in here. A tab already names the
            session; carrying its figures costs one line instead of 240px. */}
        <div className="flex flex-wrap gap-1 border-b border-[#E5E7EB] px-2">
          {data.sessions.map((s) => {
            const on = tab === s.value
            return (
              <button key={s.value} type="button" onClick={() => setTab(s.value as SessionKey)}
                className={cn('-mb-px flex items-center gap-2.5 border-b-2 px-3 py-2 text-left transition-colors',
                  on ? 'border-[#2563EB]' : 'border-transparent hover:bg-[#F9FAFC]')}>
                <span>
                  <span className={cn('block text-[12.5px] leading-tight',
                    on ? 'font-semibold text-[#2563EB]' : 'text-[#374151]')}>
                    {SESSION_TITLE[s.value as SessionKey]}
                    {s.live && (
                      <span className="ml-1.5 rounded bg-[#DCFCE7] px-1 py-0.5 text-[9.5px] font-semibold text-[#166534]">
                        NOW
                      </span>
                    )}
                  </span>
                  <span className="block text-[10.5px] text-[#9CA3AF]">{s.window}</span>
                </span>
                <span className="flex items-center gap-1.5 border-l border-[#F1F2F8] pl-2.5">
                  {(['present', 'absent', 'late', 'excused'] as const)
                    .filter((k) => k !== 'excused' || Number(s.counts.excused ?? 0) > 0)
                    .map((k) => (
                      <span key={k} title={k}
                        className={cn('rounded px-1.5 py-0.5 text-[11px] font-semibold',
                          TONE[k].bg, TONE[k].text)}>
                        {s.counts[k] ?? 0}
                      </span>
                    ))}
                  <span className="text-[10.5px] text-[#9CA3AF]">
                    {s.counts.marked ?? 0}/{data.total}
                  </span>
                </span>
              </button>
            )
          })}
        </div>

        {/* Only present when it has something to say, so an untouched
            register does not carry an empty band above it. */}
        {(busy || pendingCount > 0 || savedAt) && (
          <div className="flex items-center justify-end px-3.5 py-1.5">
            <span className="flex items-center gap-1.5 text-[11.5px] text-[#6B7280]">
              {busy ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving…</>
                : pendingCount > 0 ? <><Save className="h-3.5 w-3.5" /> {pendingCount} to save…</>
                : <><CheckCircle2 className="h-3.5 w-3.5 text-[#16A34A]" /> Saved{' '}
                    {new Date(savedAt!).toLocaleTimeString('en-IN',
                      { hour: '2-digit', minute: '2-digit' })}</>}
            </span>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] border-collapse text-left">
            <thead>
              <tr className="sticky top-0 z-10 border-y border-[#E5E7EB] bg-[#F9FAFC]">
                <Th className="w-10">#</Th>
                <Th>Roll Number</Th>
                <Th>Student Name</Th>
                <Th className="text-center">
                  Status
                  <span className="ml-1 font-normal text-[10px] text-[#9CA3AF]">
                    ({active?.window})
                  </span>
                </Th>
                <Th className="w-[210px]">Remarks</Th>
              </tr>
            </thead>
            <tbody>
              {data.students.map((row, i) => {
                const status = statusOf(row, tab)
                return (
                  <tr key={row.student_id}
                    className="border-b border-[#F1F2F8] last:border-0 hover:bg-[#F9FAFC]">
                    <Td className="text-[#9CA3AF]">{from + i}</Td>
                    <Td className="font-mono text-[11.5px]">{row.roll_number ?? '—'}</Td>
                    <Td>
                      {row.full_name}
                      <span className="block text-[10.5px] text-[#9CA3AF]">{row.batch_code}</span>
                    </Td>
                    <Td>
                      {/* Four buttons rather than a dropdown: marking a class is
                          one click per student, not click-open-choose. */}
                      <div className="flex flex-wrap justify-center gap-1.5">
                        {data.statuses.map((st) => {
                          const on = status === st.value
                          const tone = TONE[st.value]
                          return (
                            <button key={st.value} type="button"
                              aria-pressed={on}
                              aria-label={`${st.label}: ${row.full_name}`}
                              onClick={() => setCell(row.student_id, tab, { status: st.value })}
                              className={cn('flex min-w-[92px] items-center justify-center gap-1.5 rounded-lg border px-2 py-1.5 text-[11.5px] transition-colors',
                                on
                                  ? cn(tone.ring, tone.bg, tone.text, 'font-semibold')
                                  : 'border-[#E5E7EB] bg-white text-[#9CA3AF] hover:bg-[#F9FAFB]')}>
                              <span className={cn('font-bold', on ? '' : 'text-[#6B7280]')}>
                                {st.code}
                              </span>
                              {st.label}
                            </button>
                          )
                        })}
                      </div>
                    </Td>
                    <Td>
                      {/* On the row rather than behind a button: a remark is
                          written while marking the student, not afterwards. */}
                      <input
                        aria-label={`Remark for ${row.full_name}`}
                        value={remarksOf(row, tab) ?? ''}
                        placeholder="Add a remark"
                        onChange={(e) => setCell(row.student_id, tab, { remarks: e.target.value })}
                        className="h-8 w-full rounded-lg border border-[#E5E7EB] bg-white px-2 text-[11.5px] text-[#374151] outline-none placeholder:text-[#C7CAD6] focus:border-[#2563EB]" />
                    </Td>
                  </tr>
                )
              })}

              {data.students.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-[12.5px] text-[#6B7280]">
                    No students match those filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#E5E7EB] px-3.5 py-2.5">
          <p className="text-[11.5px] text-[#6B7280]">
            Showing {data.total === 0 ? 0 : from} to {to} of {data.total} students
          </p>
          <div className="flex items-center gap-1.5">
            <select value={perPage} aria-label="Rows per page"
              onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
              className="h-7 rounded-lg border border-[#D1D5DB] bg-white px-2 text-[11.5px]">
              {[10, 25, 50].map((n) => <option key={n} value={n}>{n} per page</option>)}
            </select>
            <PageBtn label="First" disabled={data.page <= 1} onClick={() => goPage(1)}>
              <ChevronsLeft className="h-3.5 w-3.5" />
            </PageBtn>
            <PageBtn label="Previous" disabled={data.page <= 1}
              onClick={() => goPage(data.page - 1)}>
              <ChevronLeft className="h-3.5 w-3.5" />
            </PageBtn>
            {pageNumbers(data.page, data.pages).map((n, i) => (
              n === null ? (
                <span key={`gap-${i}`} className="px-1 text-[11.5px] text-[#9CA3AF]">…</span>
              ) : (
                <button key={n} type="button" onClick={() => goPage(n)}
                  aria-current={n === data.page ? 'page' : undefined}
                  className={cn('h-7 min-w-[28px] rounded-lg px-2 text-[11.5px] font-medium',
                    n === data.page
                      ? 'bg-[#2563EB] text-white'
                      : 'border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]')}>
                  {n}
                </button>
              )
            ))}
            <PageBtn label="Next" disabled={data.page >= data.pages}
              onClick={() => goPage(data.page + 1)}>
              <ChevronRight className="h-3.5 w-3.5" />
            </PageBtn>
            <PageBtn label="Last" disabled={data.page >= data.pages}
              onClick={() => goPage(data.pages)}>
              <ChevronsRight className="h-3.5 w-3.5" />
            </PageBtn>
          </div>
        </div>
      </div>
    </div>
  )
}

/** Page numbers around the current one, with gaps rather than sixty buttons. */
function pageNumbers(current: number, total: number): (number | null)[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const out: (number | null)[] = [1]
  const from = Math.max(2, current - 2)
  const to = Math.min(total - 1, current + 2)
  if (from > 2) out.push(null)
  for (let n = from; n <= to; n += 1) out.push(n)
  if (to < total - 1) out.push(null)
  out.push(total)
  return out
}


function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <th className={cn('px-3 py-2.5 text-[11.5px] font-semibold text-[#374151]', className)}>
      {children}
    </th>
  )
}

function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2.5 text-[12px] text-[#1B1B3A]', className)}>{children}</td>
}

function PageBtn({ label, disabled, onClick, children }: {
  label: string; disabled: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button type="button" aria-label={label} disabled={disabled} onClick={onClick}
      className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
      {children}
    </button>
  )
}
