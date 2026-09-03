'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  Loader2,
  Search,
  Send,
  Sparkles,
  UserCog,
  UserPlus,
  Users,
} from 'lucide-react'
import {
  errorMessage,
  assignGuide,
  assignStudentsToBatch,
  fetchBatches,
  fetchIncomplete,
  recordReminders,
  type BatchRow,
  type FacultyFilterOptions,
  type IncompleteView,
} from '@/lib/faculty-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
const CELL = 'px-2 py-2'
// Record and Missing Information both flex; the fixed columns previously
// summed past the container and left Record about 76px wide.
const COL_WIDTHS = ['28px', 'auto', '58px', '84px', '88px', 'auto', '86px', '64px', '58px', '92px']

const KPI_TILE: Record<string, string> = {
  records: 'bg-[#6D5AE6]', batches: 'bg-[#3B82F6]', unbatched: 'bg-[#16A34A]',
  profiles: 'bg-[#F59E0B]', papers: 'bg-[#EF4444]', guides: 'bg-[#8B5CF6]',
}
const KPI_ICON: Record<string, typeof Users> = {
  records: FileText, batches: Users, unbatched: UserPlus,
  profiles: AlertTriangle, papers: FileText, guides: UserCog,
}

const PRIORITY_TONE: Record<string, string> = {
  Critical: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  High: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  Medium: 'border-[#C7D2FE] bg-[#EEF2FF] text-[#4F46E5]',
}

const SCOPES = [
  { key: 'all', label: 'All Issues' },
  { key: 'student', label: 'Student Issues' },
  { key: 'batch', label: 'Batch Issues' },
]

const FILTERS = [
  { key: 'department', label: 'Department', all: 'All Departments', from: 'departments' },
  { key: 'year', label: 'Year', all: 'All Years', from: 'years' },
  { key: 'semester', label: 'Semester', all: 'All Semesters', from: 'semesters' },
  { key: 'section', label: 'Section', all: 'All Sections', from: 'sections' },
] as const

const SELECT_CLASS =
  'h-8 w-full appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]'

function SelectShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      {children}
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
    </div>
  )
}

export function IncompleteRegistrations({
  options,
  onNotice,
}: {
  options: FacultyFilterOptions | null
  onNotice: (message: string) => void
}) {
  const [filters, setFilters] = useState<Record<string, string | undefined>>({})
  const [scope, setScope] = useState('all')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const [view, setView] = useState<IncompleteView | null>(null)
  const [batches, setBatches] = useState<BatchRow[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [picker, setPicker] = useState<'batch' | 'guide' | null>(null)
  const [pickValue, setPickValue] = useState('')

  const query = useMemo(
    () => ({ ...filters, scope, search: search || undefined, page, per_page: perPage }),
    [filters, scope, search, page, perPage]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setView(await fetchIncomplete(query))
    } catch (err: any) {
      setError(errorMessage(err, 'Could not load incomplete registrations.'))
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => { load() }, [load])
  useEffect(() => { fetchBatches({ limit: 200 }).then((r) => setBatches(r.items)).catch(() => setBatches([])) }, [])
  useEffect(() => setSelected([]), [scope, page, perPage, search, filters])

  const rows = view?.rows ?? []
  const selectedRows = rows.filter((r) => selected.includes(r.id))
  const allChecked = rows.length > 0 && selected.length === rows.length
  const optionsFor = (from: string, all: string) =>
    [all, ...(((options?.[from as keyof FacultyFilterOptions] as string[] | undefined) ?? []))]

  const run = async (fn: () => Promise<string>) => {
    setBusy(true)
    try { onNotice(await fn()); await load() }
    catch (err: any) { onNotice(errorMessage(err, 'That action could not be completed.')) }
    finally { setBusy(false); setPicker(null); setPickValue('') }
  }

  const runAssignBatch = () => run(async () => {
    const ids = selectedRows.filter((r) => r.kind === 'student').map((r) => r.id)
    if (!ids.length) return 'Select at least one student record to assign to a batch.'
    const res = await assignStudentsToBatch(ids, pickValue)
    return `Added ${res.added} student(s) to ${res.batch_code}.`
  })

  const runAssignGuide = () => run(async () => {
    const ids = selectedRows.filter((r) => r.kind === 'batch').map((r) => r.id)
    if (!ids.length) return 'Select at least one batch record to assign a guide.'
    const res = await assignGuide(ids, pickValue)
    return `Assigned a guide to ${res.updated} batch(es).`
  })

  const runReminder = () => run(async () => {
    const students = selectedRows.filter((r) => r.kind === 'student').map((r) => r.id)
    const batchIds = selectedRows.filter((r) => r.kind === 'batch').map((r) => r.id)
    let stamped = 0
    if (students.length) stamped += (await recordReminders(students, 'student')).stamped
    if (batchIds.length) stamped += (await recordReminders(batchIds, 'batch')).stamped
    return `Reminder recorded against ${stamped} record(s). No email was sent - the dispatch pipeline is not configured.`
  })

  return (
    <>
      {/* Filters */}
      <section className={cn(CARD, 'grid grid-cols-2 gap-2.5 p-2.5 md:grid-cols-3 xl:grid-cols-7')}>
        {FILTERS.map((f) => (
          <div key={f.key}>
            <label htmlFor={`i-${f.key}`} className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">{f.label}</label>
            <SelectShell>
              <select id={`i-${f.key}`} value={filters[f.key] ?? f.all} className={SELECT_CLASS}
                onChange={(e) => { const v = e.target.value; setFilters((p) => ({ ...p, [f.key]: v.startsWith('All ') ? undefined : v })); setPage(1) }}>
                {optionsFor(f.from, f.all).map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </SelectShell>
          </div>
        ))}
        <div>
          <label htmlFor="issue_type" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Issue Type</label>
          <SelectShell>
            <select id="issue_type" value={filters.issue_type ?? ''} className={SELECT_CLASS}
              onChange={(e) => { setFilters((p) => ({ ...p, issue_type: e.target.value || undefined })); setPage(1) }}>
              <option value="">All Issues</option>
              {(view?.issue_types ?? []).map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
            </select>
          </SelectShell>
        </div>
        <div>
          <label htmlFor="priority" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Priority</label>
          <SelectShell>
            <select id="priority" value={filters.priority ?? ''} className={SELECT_CLASS}
              onChange={(e) => { setFilters((p) => ({ ...p, priority: e.target.value || undefined })); setPage(1) }}>
              <option value="">All Priorities</option>
              {(view?.priorities ?? []).map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
          </SelectShell>
        </div>
        <div>
          <label htmlFor="i-search" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Search</label>
          <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1) }} className="relative">
            <input id="i-search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Student, batch, roll or missing item…"
              className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] outline-none focus:border-[#4F46E5]" />
            <button type="submit" aria-label="Search records" className="absolute right-2 top-1/2 -translate-y-1/2">
              <Search className="h-3.5 w-3.5 text-[#8A8FA8]" />
            </button>
          </form>
        </div>
      </section>

      {/* KPIs */}
      <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
        {(view?.kpis ?? []).map((k) => {
          const Icon = KPI_ICON[k.id] ?? FileText
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
              {SCOPES.map((s) => (
                <button key={s.key} type="button" onClick={() => { setScope(s.key); setPage(1) }}
                  className={cn('rounded-md px-3 py-1.5 text-[11.5px]',
                    scope === s.key ? 'bg-[#4F46E5] font-medium text-white' : 'text-[#5A5F7A] hover:text-[#1B1B3A]')}>
                  {s.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              <Tool icon={Users} label="Assign to Batch" disabled={!selected.length || busy} onClick={() => setPicker('batch')} />
              <Tool icon={UserCog} label="Assign Guide" disabled={!selected.length || busy} onClick={() => setPicker('guide')} />
              <Tool icon={Send} label="Send Reminder" disabled={!selected.length || busy} onClick={runReminder} />
              <Tool icon={CheckCircle2} label="Mark Resolved" disabled={!selected.length || busy}
                onClick={() => onNotice('A record leaves this list when its gap is filled - use Assign to Batch, Assign Guide, or complete the profile. There is no separate "resolved" flag to set.')} />
            </div>
          </div>

          {picker && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-2.5">
              <span className="text-[12px] text-[#3A3F58]">
                {picker === 'batch' ? 'Add selected students to:' : 'Assign guide to selected batches:'}
              </span>
              <select value={pickValue} onChange={(e) => setPickValue(e.target.value)}
                className="h-8 rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]">
                <option value="">Select…</option>
                {picker === 'batch'
                  ? batches.map((b) => <option key={b.id} value={b.id}>{b.batch_code} ({b.member_count} members)</option>)
                  : (options?.guides ?? []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
              </select>
              <button type="button" disabled={!pickValue || busy}
                onClick={picker === 'batch' ? runAssignBatch : runAssignGuide}
                className="rounded-lg bg-[#4F46E5] px-3 py-1.5 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
                Apply
              </button>
              <button type="button" onClick={() => { setPicker(null); setPickValue('') }}
                className="text-[12px] text-[#5A5F7A] hover:underline">Cancel</button>
            </div>
          )}

          <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Incomplete Registrations</h2>

          {loading ? (
            <div className="flex h-[260px] items-center justify-center gap-2 text-[#5A5F7A]">
              <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> <span className="text-[12px]">Loading…</span>
            </div>
          ) : error ? (
            <div className="flex h-[260px] flex-col items-center justify-center gap-3">
              <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
              <p className="text-[12px] text-[#5A5F7A]">{error}</p>
              <button type="button" onClick={load} className="rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white">Retry</button>
            </div>
          ) : rows.length === 0 ? (
            <p className="py-16 text-center text-[12px] text-[#8A8FA8]">Nothing incomplete in this view.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full table-fixed border-collapse text-[11.5px]">
                  <colgroup>{COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
                  <thead>
                    <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                      <th className={cn(CELL, 'text-left')}>
                        <input type="checkbox" checked={allChecked} aria-label="Select all records"
                          onChange={() => setSelected(allChecked ? [] : rows.map((r) => r.id))} />
                      </th>
                      {['Record', 'Type', 'Dept / Section', 'Batch', 'Missing Information', 'Completion', 'Priority', 'Reminder', 'Action'].map((h, i) => (
                        <th key={h} className={cn(CELL, 'font-medium', i === 0 ? 'text-left' : 'text-center')}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} className="border-b border-[#F1F2F8]">
                        <td className={CELL}>
                          <input type="checkbox" checked={selected.includes(r.id)} aria-label={`Select ${r.label}`}
                            onChange={() => setSelected((s) => s.includes(r.id) ? s.filter((x) => x !== r.id) : [...s, r.id])} />
                        </td>
                        <td className={cn(CELL, 'truncate text-[#1B1B3A]')} title={r.label}>{r.label}</td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn('rounded-full border px-2 py-0.5 text-[10.5px]',
                            r.kind === 'student' ? 'border-[#C7D2FE] bg-[#EEF2FF] text-[#4F46E5]' : 'border-[#BFDBFE] bg-[#EFF6FF] text-[#2563EB]')}>
                            {r.type}
                          </span>
                        </td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.department} / {r.section ?? '–'}</td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn(r.batch === 'Not Joined' || r.batch === 'Invitation Pending' ? 'text-[#DC2626]' : 'text-[#3A3F58]')}>
                            {r.batch}
                          </span>
                        </td>
                        <td className={cn(CELL, 'truncate text-center text-[#5A5F7A]')} title={r.missing}>{r.missing}</td>
                        <td className={CELL}>
                          <div className="flex items-center gap-1.5">
                            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F7]">
                              <span className="block h-full rounded-full bg-[#4F46E5]" style={{ width: `${r.completion}%` }} />
                            </span>
                            <span className="w-[26px] shrink-0 text-right text-[10.5px] text-[#5A5F7A]">{r.completion}%</span>
                          </div>
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          <span className={cn('rounded-full border px-2 py-0.5 text-[10.5px]', PRIORITY_TONE[r.priority])}>{r.priority}</span>
                        </td>
                        <td className={cn(CELL, 'text-center text-[10.5px] text-[#5A5F7A]')}>
                          {r.last_reminder ? new Date(r.last_reminder).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : '—'}
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          <button type="button"
                            onClick={() => {
                              setSelected([r.id])
                              setPicker(r.kind === 'student' ? 'batch' : 'guide')
                            }}
                            className="rounded-md border border-[#DDE0EE] px-2 py-1 text-[10.5px] font-medium text-[#4F46E5] hover:bg-[#F7F8FC]">
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
                  Showing {view?.showing_from} to {view?.showing_to} of {view?.total} incomplete records
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
                    aria-label="Records per page"
                    className="h-7 rounded-md border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]">
                    {[10, 25, 50].map((n) => <option key={n} value={n}>{n} per page</option>)}
                  </select>
                </div>
              </div>
            </>
          )}
        </section>

        {/* Right column */}
        <div className="space-y-2.5">
          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Issue Breakdown</h2>
            <ul className="space-y-1.5">
              {(view?.breakdown ?? []).map((b) => (
                <li key={b.id} className="flex items-center gap-2 rounded-lg border border-[#EEF0F7] px-2 py-1.5">
                  <span className="flex-1 text-[11px] leading-tight text-[#3A3F58]">{b.label}</span>
                  <span className="text-[14px] font-semibold text-[#4F46E5]">{b.count}</span>
                  <button type="button" onClick={() => { setFilters((p) => ({ ...p, issue_type: b.id })); setPage(1) }}
                    className="text-[11px] font-medium text-[#4F46E5] hover:underline">View</button>
                </li>
              ))}
            </ul>
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Resolution Progress</h2>
            <div className="flex items-center gap-4">
              <Donut percent={view?.resolution.percent_resolved ?? 0} label="resolved" />
              <ul className="flex-1 space-y-1 text-[11px]">
                <li className="flex justify-between"><span className="text-[#3A3F58]">Resolved This Week</span><span className="font-semibold text-[#16A34A]">{view?.resolution.resolved_this_week}</span></li>
                <li className="flex justify-between"><span className="text-[#3A3F58]">Pending</span><span className="font-semibold text-[#D97706]">{view?.resolution.pending}</span></li>
                <li className="flex justify-between"><span className="text-[#3A3F58]">Overdue</span><span className="font-semibold text-[#DC2626]">{view?.resolution.overdue}</span></li>
                <li className="flex justify-between border-t border-[#EEF0F7] pt-1"><span className="text-[#3A3F58]">Avg Resolution Time</span><span className="font-semibold text-[#4F46E5]">{view?.resolution.average_days}d</span></li>
              </ul>
            </div>
          </section>
        </div>
      </div>

      {/* Recommended actions + workflow cues */}
      <div className="grid gap-2.5 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
        <section className={cn(CARD, 'p-4')}>
          <h2 className="mb-2 text-[13px] font-semibold text-[#1B1B3A]">Recommended Actions</h2>
          <div className="grid gap-3 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
            <ol className="space-y-1.5">
              {(view?.recommendations ?? []).map((r, i) => (
                <li key={r} className="flex gap-2 text-[11.5px] text-[#3A3F58]">
                  <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#4F46E5] text-[9px] font-semibold text-white">{i + 1}</span>
                  {r}
                </li>
              ))}
            </ol>
            <div className="space-y-1.5">
              <Wide icon={Sparkles} label="Auto-Suggest Batch Allocation"
                onClick={() => onNotice('Auto-allocation needs a grouping algorithm plus a rule for cross-section moves - not built yet.')} />
              <Wide icon={Send} label="Send All Reminders"
                onClick={() => onNotice('Bulk reminders need the email dispatch pipeline - not wired up, so nothing was sent.')} />
              <Wide icon={Download} label="Download Resolution Report"
                onClick={() => onNotice('The resolution report needs the reporting endpoint - see Reports & Analytics.')} />
            </div>
          </div>
        </section>

        <section className={cn(CARD, 'p-4')}>
          <h2 className="mb-2 text-[13px] font-semibold text-[#1B1B3A]">Important Workflow Cues</h2>
          <ul className="space-y-1.5 text-[11px] leading-relaxed text-[#3A3F58]">
            {[
              'Faculty can open a record to see exactly which fields are missing.',
              'A student from one section cannot be assigned to another section unless an authorised coordinator approves.',
              'A batch cannot move to the Approval Queue until four members, project details and primary base paper are complete.',
            ].map((cue) => (
              <li key={cue} className="flex gap-2">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" /> {cue}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}

function Donut({ percent, label }: { percent: number; label: string }) {
  const r = 26, c = 2 * Math.PI * r
  return (
    <div className="relative h-[74px] w-[74px] shrink-0">
      <svg viewBox="0 0 64 64" className="h-full w-full -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#EEF0F7" strokeWidth="7" />
        <circle cx="32" cy="32" r={r} fill="none" stroke="#4F46E5" strokeWidth="7" strokeLinecap="round"
          strokeDasharray={`${(percent / 100) * c} ${c}`} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[14px] font-bold leading-none text-[#1B1B3A]">{percent}%</span>
        <span className="text-[8.5px] text-[#8A8FA8]">{label}</span>
      </div>
    </div>
  )
}

function Tool({ icon: Icon, label, onClick, disabled }: { icon: typeof Users; label: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] bg-white px-3 py-1.5 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-white">
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  )
}

function Wide({ icon: Icon, label, onClick }: { icon: typeof Users; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className="flex w-full items-center gap-2 rounded-lg border border-[#DDE0EE] px-3 py-2 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC]">
      <Icon className="h-3.5 w-3.5 text-[#4F46E5]" /> {label}
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
