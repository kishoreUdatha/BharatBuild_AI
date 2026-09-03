'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Download,
  FileText,
  Loader2,
  MessageSquare,
  RefreshCw,
  Search,
  UserCog,
  XCircle,
} from 'lucide-react'
import {
  errorMessage,
  assignReviewer,
  decideRegistrations,
  fetchQueue,
  fetchQueueDetail,
  type FacultyFilterOptions,
  type QueueDetail,
  type QueueView,
} from '@/lib/faculty-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
const CELL = 'px-2 py-2'
const COL_WIDTHS = ['30px', '86px', 'auto', '52px', '96px', '86px', '110px', '92px', '70px', '84px', '92px']

const KPI_TILE: Record<string, string> = {
  awaiting: 'bg-[#6D5AE6]', due: 'bg-[#3B82F6]', changes: 'bg-[#F59E0B]',
  approved: 'bg-[#16A34A]', papers: 'bg-[#2563EB]', overdue: 'bg-[#EF4444]',
}
const KPI_ICON: Record<string, typeof Clock> = {
  awaiting: Clock, due: CalendarClock, changes: RefreshCw,
  approved: CheckCircle2, papers: FileText, overdue: AlertCircle,
}

const PAPER_TONE: Record<string, string> = {
  Verified: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  'Pending Verification': 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  Missing: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
}

const FILTERS = [
  { key: 'department', label: 'Department', all: 'All Departments', from: 'departments' },
  { key: 'year', label: 'Year', all: 'All Years', from: 'years' },
  { key: 'semester', label: 'Semester', all: 'All Semesters', from: 'semesters' },
  { key: 'section', label: 'Section', all: 'All Sections', from: 'sections' },
] as const

const SELECT_CLASS =
  'h-8 w-full appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]'

export function ApprovalQueue({
  options,
  onNotice,
}: {
  options: FacultyFilterOptions | null
  onNotice: (message: string) => void
}) {
  const [filters, setFilters] = useState<Record<string, string | undefined>>({})
  const [reviewStatus, setReviewStatus] = useState('pending')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const [view, setView] = useState<QueueView | null>(null)
  const [detail, setDetail] = useState<QueueDetail | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [notify, setNotify] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [reviewerOpen, setReviewerOpen] = useState(false)
  const [reviewerId, setReviewerId] = useState('')

  const query = useMemo(
    () => ({ ...filters, review_status: reviewStatus, search: search || undefined, page, per_page: perPage }),
    [filters, reviewStatus, search, page, perPage]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchQueue(query)
      setView(data)
      setDetail(data.selected)
      setNote(data.selected?.faculty_note ?? '')
    } catch (err: any) {
      setError(errorMessage(err, 'Could not load the approval queue.'))
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => { load() }, [load])
  useEffect(() => setSelected([]), [reviewStatus, page, perPage, search, filters])

  const rows = view?.rows ?? []
  const allChecked = rows.length > 0 && selected.length === rows.length
  const optionsFor = (from: string, all: string) =>
    [all, ...(((options?.[from as keyof FacultyFilterOptions] as string[] | undefined) ?? []))]

  const openDetail = async (batchId: string) => {
    try {
      const d = await fetchQueueDetail(batchId)
      setDetail(d)
      setNote(d.faculty_note ?? '')
    } catch { onNotice('Could not open that registration.') }
  }

  const decide = async (decision: 'approve' | 'reject' | 'request_changes', ids?: string[]) => {
    const batchIds = ids ?? (detail ? [detail.id] : [])
    if (!batchIds.length) return
    setBusy(true)
    try {
      const res = await decideRegistrations(batchIds, decision, note || undefined)
      const skipped = res.skipped.map((s) => `${s.batch_code}: ${s.reason}`).join(' | ')
      const verb = decision === 'approve' ? 'Approved' : decision === 'reject' ? 'Rejected' : 'Sent back for changes'
      onNotice(
        `${verb} ${res.applied.length} registration(s).` +
        (skipped ? ` Blocked — ${skipped}` : '') +
        (notify && res.applied.length ? ' (Students would be notified once the email pipeline is wired up.)' : '')
      )
      await load()
    } catch (err: any) {
      onNotice(errorMessage(err, 'That decision could not be applied.'))
    } finally { setBusy(false) }
  }

  const runAssignReviewer = async () => {
    if (!reviewerId || !selected.length) return
    setBusy(true)
    try {
      const res = await assignReviewer(selected, reviewerId)
      onNotice(`Assigned a reviewer to ${res.updated} registration(s).`)
      setReviewerOpen(false); setReviewerId('')
      await load()
    } catch (err: any) {
      onNotice(errorMessage(err, 'Could not assign the reviewer.'))
    } finally { setBusy(false) }
  }

  return (
    <>
      {/* Filters */}
      <section className={cn(CARD, 'grid grid-cols-2 gap-2.5 p-2.5 md:grid-cols-3 xl:grid-cols-6')}>
        {FILTERS.map((f) => (
          <div key={f.key}>
            <label htmlFor={`q-${f.key}`} className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">{f.label}</label>
            <div className="relative">
              <select id={`q-${f.key}`} value={filters[f.key] ?? f.all} className={SELECT_CLASS}
                onChange={(e) => { const v = e.target.value; setFilters((p) => ({ ...p, [f.key]: v.startsWith('All ') ? undefined : v })); setPage(1) }}>
                {optionsFor(f.from, f.all).map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
            </div>
          </div>
        ))}
        <div className="md:col-span-2">
          <label htmlFor="q-search" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Search</label>
          <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1) }} className="relative">
            <input id="q-search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Batch code, project title, leader or guide…"
              className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] outline-none focus:border-[#4F46E5]" />
            <button type="submit" aria-label="Search queue" className="absolute right-2 top-1/2 -translate-y-1/2">
              <Search className="h-3.5 w-3.5 text-[#8A8FA8]" />
            </button>
          </form>
        </div>
      </section>

      {/* KPIs */}
      <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
        {(view?.kpis ?? []).map((k) => {
          const Icon = KPI_ICON[k.id] ?? Clock
          return (
            <div key={k.id} className={cn(CARD, 'flex items-center gap-2.5 p-2')}>
              <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl', KPI_TILE[k.id])}>
                <Icon className="h-4 w-4 text-white" />
              </span>
              <div className="min-w-0">
                <p className="text-[19px] font-bold leading-none text-[#1B1B3A]">{k.value}</p>
                <p className="mt-0.5 text-[11px] leading-tight text-[#5A5F7A]">{k.label}</p>
              </div>
            </div>
          )
        })}
      </section>

      <div className="grid gap-2.5 xl:grid-cols-[minmax(0,2.6fr)_minmax(0,1fr)]">
        <section className={cn(CARD, 'p-4')}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div className="flex gap-1 rounded-lg bg-[#F4F5FA] p-0.5">
              {(view?.tabs ?? []).map((t) => (
                <button key={t.key} type="button" onClick={() => { setReviewStatus(t.key); setPage(1) }}
                  className={cn('rounded-md px-3 py-1.5 text-[11.5px]',
                    reviewStatus === t.key ? 'bg-[#4F46E5] font-medium text-white' : 'text-[#5A5F7A] hover:text-[#1B1B3A]')}>
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Tool icon={CheckCircle2} label="Approve Selected" disabled={!selected.length || busy}
                onClick={() => decide('approve', selected)} />
              <Tool icon={UserCog} label="Assign Reviewer" disabled={!selected.length || busy}
                onClick={() => setReviewerOpen((v) => !v)} />
              <Tool icon={MessageSquare} label="Request Changes" disabled={!selected.length || busy}
                onClick={() => decide('request_changes', selected)} />
              <Tool icon={Download} label="Export" disabled={busy}
                onClick={() => onNotice('Queue export reuses the registrations CSV - use Export Registrations in the header.')} />
            </div>
          </div>

          {reviewerOpen && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-2.5">
              <span className="text-[12px] text-[#3A3F58]">Reviewer for {selected.length} registration(s):</span>
              <select value={reviewerId} onChange={(e) => setReviewerId(e.target.value)}
                className="h-8 rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]">
                <option value="">Select…</option>
                {(options?.guides ?? []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
              <button type="button" onClick={runAssignReviewer} disabled={!reviewerId || busy}
                className="rounded-lg bg-[#4F46E5] px-3 py-1.5 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
                Assign
              </button>
            </div>
          )}

          <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Registration Approval Queue</h2>

          {loading ? (
            <div className="flex h-[240px] items-center justify-center gap-2 text-[#5A5F7A]">
              <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> <span className="text-[12px]">Loading…</span>
            </div>
          ) : error ? (
            <div className="flex h-[240px] flex-col items-center justify-center gap-3">
              <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
              <p className="text-[12px] text-[#5A5F7A]">{error}</p>
              <button type="button" onClick={load} className="rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white">Retry</button>
            </div>
          ) : rows.length === 0 ? (
            <p className="py-16 text-center text-[12px] text-[#8A8FA8]">Nothing in this queue.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full table-fixed border-collapse text-[11.5px]">
                  <colgroup>{COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
                  <thead>
                    <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                      <th className={cn(CELL, 'text-left')}>
                        <input type="checkbox" checked={allChecked} aria-label="Select all registrations"
                          onChange={() => setSelected(allChecked ? [] : rows.map((r) => r.id))} />
                      </th>
                      {['Batch', 'Project Title', 'Sec', 'Team', 'Details', 'Base Paper', 'Guide', 'Submitted', 'SLA', 'Action'].map((h, i) => (
                        <th key={h} className={cn(CELL, 'font-medium', i <= 1 ? 'text-left' : 'text-center')}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} className={cn('border-b border-[#F1F2F8]', detail?.id === r.id && 'bg-[#F5F3FF]')}>
                        <td className={CELL}>
                          <input type="checkbox" checked={selected.includes(r.id)} aria-label={`Select ${r.batch_code}`}
                            onChange={() => setSelected((s) => s.includes(r.id) ? s.filter((x) => x !== r.id) : [...s, r.id])} />
                        </td>
                        <td className={CELL}>
                          <a href={`/faculty/registrations/${encodeURIComponent(r.batch_code)}`}
                            className="font-medium text-[#4F46E5] hover:underline">{r.batch_code}</a>
                        </td>
                        <td className={cn(CELL, 'truncate text-[#3A3F58]')} title={r.title ?? undefined}>{r.title ?? '–'}</td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.section ?? '–'}</td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn('whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px]',
                            r.team_complete ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]' : 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]')}>
                            {r.team}
                          </span>
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn('rounded-full border px-2 py-0.5 text-[10.5px]',
                            r.project_details === 'Complete' ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]' : 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]')}>
                            {r.project_details}
                          </span>
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn('whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px]', PAPER_TONE[r.base_paper])}>
                            {r.base_paper}
                          </span>
                        </td>
                        <td className={cn(CELL, 'truncate text-center text-[#3A3F58]')}>{r.guide ?? '–'}</td>
                        <td className={cn(CELL, 'whitespace-nowrap text-center text-[10.5px] text-[#5A5F7A]')}>
                          {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '–'}
                        </td>
                        <td className={cn(CELL, 'whitespace-nowrap text-center text-[10.5px] font-medium', r.overdue ? 'text-[#DC2626]' : 'text-[#3A3F58]')}>
                          {r.sla}
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          <button type="button" onClick={() => openDetail(r.id)}
                            className="whitespace-nowrap rounded-md border border-[#DDE0EE] px-2 py-1 text-[10.5px] font-medium text-[#4F46E5] hover:bg-[#F7F8FC]">
                            {r.action}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] text-[#8A8FA8]">
                  Showing {view?.showing_from} to {view?.showing_to} of {view?.total} registrations
                </p>
                <div className="flex items-center gap-2">
                  <Pager onClick={() => setPage((p) => p - 1)} disabled={(view?.page ?? 1) <= 1} aria-label="Previous page">
                    <ChevronLeft className="h-3.5 w-3.5" />
                  </Pager>
                  <span className="text-[11px] text-[#3A3F58]">Page {view?.page} of {view?.pages}</span>
                  <Pager onClick={() => setPage((p) => p + 1)} disabled={(view?.page ?? 1) >= (view?.pages ?? 1)} aria-label="Next page">
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Pager>
                  <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
                    aria-label="Registrations per page"
                    className="h-7 rounded-md border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]">
                    {[10, 25, 50].map((n) => <option key={n} value={n}>{n} per page</option>)}
                  </select>
                </div>
              </div>
            </>
          )}
        </section>

        {/* Checklist + summary */}
        <div className="space-y-2.5">
          <section className={cn(CARD, 'p-4')}>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Approval Checklist</h2>
              <span className="text-[11px] text-[#8A8FA8]">{detail?.batch_code ?? '—'}</span>
            </div>
            {detail ? (
              <>
                <ul className="space-y-1">
                  {detail.checklist.map((c) => (
                    <li key={c.key} className="flex items-center gap-2 text-[11px]">
                      {c.passed
                        ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                        : <AlertCircle className="h-3.5 w-3.5 shrink-0 text-[#D97706]" />}
                      <span className="flex-1 text-[#3A3F58]">{c.label}</span>
                      <span className={cn('whitespace-nowrap text-[10.5px]', c.passed ? 'text-[#16A34A]' : 'text-[#D97706]')}>{c.detail}</span>
                    </li>
                  ))}
                </ul>
                <div className="mt-3 flex items-center gap-3 border-t border-[#EEF0F7] pt-3">
                  <Donut percent={Math.round((detail.checks_passed / detail.checks_total) * 100)} />
                  <p className="text-[10.5px] leading-snug text-[#5A5F7A]">
                    <span className="font-semibold text-[#1B1B3A]">
                      {detail.checks_passed} of {detail.checks_total} checks passed
                    </span>
                    <br />All mandatory checks must be complete to enable approval.
                  </p>
                </div>
              </>
            ) : (
              <p className="py-6 text-center text-[11px] text-[#8A8FA8]">Select a registration to see its checklist.</p>
            )}
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Queue Summary</h2>
            <ul className="space-y-1 text-[11px]">
              {(view?.summary.by_section ?? []).map((s) => (
                <li key={s.section} className="flex justify-between">
                  <span className="text-[#3A3F58]">Section {s.section}</span>
                  <span className="font-semibold text-[#4F46E5]">{s.pending} Pending</span>
                </li>
              ))}
              <li className="flex justify-between border-t border-[#EEF0F7] pt-1">
                <span className="text-[#3A3F58]">Oldest submission</span>
                <span className="font-semibold text-[#D97706]">{view?.summary.oldest_days} day(s)</span>
              </li>
              <li className="flex justify-between">
                <span className="text-[#3A3F58]">Average review time</span>
                <span className="font-semibold text-[#4F46E5]">{view?.summary.average_review_hours} hours</span>
              </li>
            </ul>
          </section>
        </div>
      </div>

      {/* Selected registration */}
      {detail && (
        <section className={cn(CARD, 'p-4')}>
          <h2 className="mb-3 text-[14px] font-semibold text-[#1B1B3A]">
            Selected Registration — {detail.batch_code}
          </h2>
          <div className="grid gap-4 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)]">
            <div className="space-y-2 text-[11.5px]">
              <Field label="Project" value={detail.title ?? '–'} />
              <div>
                <p className="text-[10.5px] text-[#8A8FA8]">Base Paper</p>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[#1B1B3A]">{detail.base_paper_title ?? 'Not uploaded'}</span>
                  {detail.base_paper_url && (
                    <a href={detail.base_paper_url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 rounded-md border border-[#DDE0EE] px-2 py-1 text-[10.5px] text-[#4F46E5] hover:bg-[#F7F8FC]">
                      <FileText className="h-3 w-3" /> Open paper
                    </a>
                  )}
                </div>
              </div>
              <Field label="Project Abstract" value={detail.abstract ?? 'No abstract submitted.'} />
            </div>

            <div>
              <p className="mb-1.5 text-[10.5px] text-[#8A8FA8]">Team Members ({detail.members.length}/4)</p>
              <ul className="space-y-1">
                {detail.members.map((m) => (
                  <li key={m.roll_number ?? m.name} className="flex items-center gap-2 text-[11.5px]">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#DDE3F7] text-[9px] font-semibold text-[#2C2A6B]">
                      {(m.name ?? '?').split(' ').map((p) => p[0]).slice(-2).join('').toUpperCase()}
                    </span>
                    <span className="truncate text-[#1B1B3A]">{m.name ?? '–'}</span>
                    {m.is_lead && <span className="shrink-0 text-[10px] text-[#4F46E5]">Leader</span>}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-[10.5px] text-[#8A8FA8]">Faculty guide</p>
              <p className="text-[11.5px] text-[#1B1B3A]">{detail.guide ?? 'Not assigned'}</p>
              <p className="mt-2 text-[10.5px] text-[#8A8FA8]">Submitted on</p>
              <p className="text-[11.5px] text-[#1B1B3A]">
                {detail.submitted_at
                  ? new Date(detail.submitted_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
                  : 'Not submitted'}
              </p>
            </div>

            <div className="flex flex-col">
              <label htmlFor="faculty-note" className="mb-1 text-[10.5px] text-[#8A8FA8]">Faculty Note</label>
              <textarea id="faculty-note" value={note} onChange={(e) => setNote(e.target.value)}
                placeholder="Add approval remarks…" rows={4}
                className="w-full rounded-lg border border-[#DDE0EE] p-2 text-[11.5px] outline-none focus:border-[#4F46E5]" />
              <label className="mt-1.5 flex items-center gap-2 text-[10.5px] text-[#5A5F7A]">
                <input type="checkbox" checked={notify} onChange={(e) => setNotify(e.target.checked)} />
                Notify all four students and assigned guide
              </label>
              <div className="mt-2 flex flex-wrap gap-2">
                <button type="button" onClick={() => decide('request_changes')} disabled={busy}
                  className="flex items-center gap-1.5 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[11.5px] font-medium text-[#B45309] hover:bg-[#FEF3C7] disabled:opacity-50">
                  <MessageSquare className="h-3.5 w-3.5" /> Request Changes
                </button>
                <button type="button" onClick={() => decide('reject')} disabled={busy}
                  className="flex items-center gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11.5px] font-medium text-[#DC2626] hover:bg-[#FEE2E2] disabled:opacity-50">
                  <XCircle className="h-3.5 w-3.5" /> Reject
                </button>
                <button type="button" onClick={() => decide('approve')} disabled={busy || !detail.can_approve}
                  title={detail.can_approve ? undefined : 'All mandatory checks must pass first'}
                  className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3 py-2 text-[11.5px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-40">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Approve Registration
                </button>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Workflow notes */}
      <section className={cn(CARD, 'grid gap-3 p-3 text-[10.5px] leading-snug text-[#5A5F7A] md:grid-cols-4')}>
        {[
          'Approval is disabled until all mandatory checks pass.',
          'Faculty must preview the base paper when it is only Uploaded and not Verified.',
          'Approval activity is recorded in the backend log; a full audit table is not built yet.',
          'Approved registrations move to Project Tracking and development can start.',
        ].map((cue) => (
          <p key={cue} className="flex gap-1.5">
            <AlertCircle className="mt-0.5 h-3 w-3 shrink-0 text-[#4F46E5]" /> {cue}
          </p>
        ))}
      </section>
    </>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10.5px] text-[#8A8FA8]">{label}</p>
      <p className="text-[#1B1B3A]">{value}</p>
    </div>
  )
}

function Donut({ percent }: { percent: number }) {
  const r = 26, c = 2 * Math.PI * r
  return (
    <div className="relative h-[64px] w-[64px] shrink-0">
      <svg viewBox="0 0 64 64" className="h-full w-full -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#EEF0F7" strokeWidth="7" />
        <circle cx="32" cy="32" r={r} fill="none" stroke="#4F46E5" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${(percent / 100) * c} ${c}`} />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[13px] font-bold text-[#1B1B3A]">{percent}%</span>
    </div>
  )
}

function Tool({ icon: Icon, label, onClick, disabled }: { icon: typeof Clock; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] bg-white px-3 py-1.5 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-white">
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  )
}

function Pager({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" {...props}
      className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40">
      {children}
    </button>
  )
}
