'use client'

import { useCallback, useEffect, useState } from 'react'
import { ResourceState } from '@/components/faculty/PageShell'
import {
  addMilestone,
  approveMilestone,
  bulkMilestones,
  exportMilestones,
  fetchMilestoneBoard,
  fetchMilestoneDetail,
  fetchMilestoneInsight,
  fetchMilestoneQueue,
  fetchRecoveryPlan,
  requestMilestoneChanges,
  requestMilestoneEvidence,
  toggleMilestoneChecklist,
  verifyMilestoneEvidence,
} from '@/lib/faculty-api'
import type {
  FacultyFilterOptions,
  MilestoneBoardData,
  MilestoneDetail,
  MilestoneInsight,
  MilestoneItem,
  MilestoneQuery,
  MilestoneQueueData,
  RecoveryStep,
} from '@/lib/faculty-api'
import { fetchFacultyFilters } from '@/lib/faculty-api'

const CARD = 'rounded-xl border border-[#E3E6EC] bg-white p-4'
const LABEL = 'text-[10px] uppercase tracking-wider text-[#8A8FA8]'
const BTN = 'rounded-md border border-[#E3E6EC] px-2.5 py-1.5 text-[12px] text-[#131A24] disabled:opacity-40 hover:border-[#4F46E5]'
const BTN_PRIMARY = 'rounded-md bg-[#4F46E5] px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-40'
const SELECT = 'w-full rounded-md border border-[#E3E6EC] bg-white px-2 py-1.5 text-[12px] text-[#131A24] outline-none focus:border-[#4F46E5]'
/**
 * A review is a point in the schedule rather than a stretch of work, so the
 * tracker draws it as a diamond instead of a bar.
 */
function isReview(m: MilestoneItem): boolean {
  return /review/i.test(m.name) || m.stage === 'Final Review'
}

const ROW_H = 24   // one milestone row, so bars and connectors line up

const PAGE_BTN = 'min-w-[1.5rem] rounded border border-[#E3E6EC] px-1.5 py-0.5 text-[11px] text-[#6B7686] disabled:opacity-40'

/** Page numbers with gaps, so 40 pages do not become 40 buttons. */
function pageNumbers(current: number, total: number): number[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const out = new Set<number>([1, total, current, current - 1, current + 1])
  const kept = [...out].filter((n) => n >= 1 && n <= total).sort((a, b) => a - b)
  const withGaps: number[] = []
  kept.forEach((n, i) => {
    if (i > 0 && n - kept[i - 1] > 1) withGaps.push(0)   // 0 renders as an ellipsis
    withGaps.push(n)
  })
  return withGaps
}

const HEALTH_COLOUR: Record<string, string> = {
  'On Track': '#15803D',
  'At Risk': '#B45309',
  Delayed: '#DC2626',
  Blocked: '#7C2D12',
  'Not Started': '#9AA1B1',
}

const PRIORITY_TONE: Record<string, string> = {
  critical: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  high: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  medium: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  low: 'border-[#E2E5F0] bg-[#F7F8FC] text-[#6B7280]',
}

// A solid badge per counter, so the eight cards are told apart by colour at a
// glance rather than read one by one.
const KPI_MARK: Record<string, string> = {
  total: '▦', complete: '✓', progress: '◐', upcoming: '❚❚',
  delayed: '!', awaiting: '☰', evidence: '🔗', rate: '',
}
const KPI_COLOUR: Record<string, string> = {
  total: '#4F46E5', complete: '#15803D', progress: '#2563EB', upcoming: '#7C3AED',
  delayed: '#DC2626', awaiting: '#F59E0B', evidence: '#2563EB', rate: '#4F46E5',
}

const APPROVAL_LABEL: Record<string, string> = {
  not_ready: 'Not ready',
  pending: 'Pending',
  review_ready: 'Review ready',
  approved: 'Approved',
  changes_requested: 'Changes asked',
}

export function Milestones({
  filters, onViewActivity, onActions,
}: {
  filters: MilestoneQuery
  onViewActivity?: () => void
  // The page owns the title row, so the buttons that belong beside the title
  // are handed up rather than drawn again below the tabs.
  onActions?: (node: React.ReactNode) => void
}) {
  const [view, setView] = useState<'Timeline' | 'List' | 'Calendar'>('Timeline')
  const [weeks, setWeeks] = useState(2)
  const [board, setBoard] = useState<MilestoneBoardData | null>(null)
  const [queue, setQueue] = useState<MilestoneQueueData | null>(null)
  const [insight, setInsight] = useState<MilestoneInsight | null>(null)
  const [detail, setDetail] = useState<MilestoneDetail | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')

  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [options, setOptions] = useState<FacultyFilterOptions | null>(null)
  const [department, setDepartment] = useState('')
  const [year, setYear] = useState('')
  const [semester, setSemester] = useState('')
  const [section, setSection] = useState('')
  const [guide, setGuide] = useState('')
  const [batch, setBatch] = useState('')
  const [name, setName] = useState('')
  const [status, setStatus] = useState('')
  const [approval, setApproval] = useState('')
  const [dueFrom, setDueFrom] = useState('')
  const [dueTo, setDueTo] = useState('')
  const [search, setSearch] = useState('')
  const [term, setTerm] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [adding, setAdding] = useState(false)
  const [newBatch, setNewBatch] = useState('')
  const [newName, setNewName] = useState('')
  const [newDate, setNewDate] = useState('')
  const [newPriority, setNewPriority] = useState('medium')
  const [plan, setPlan] = useState<RecoveryStep[]>([])

  const query: MilestoneQuery = {
    ...filters,
    department: department || filters.department,
    year: year || filters.year,
    semester: semester || filters.semester,
    section: section || filters.section,
    guide_id: guide || filters.guide_id,
    batch_code: batch || undefined,
    milestone: name || undefined,
    status: status || undefined,
    approval: approval || undefined,
    due_from: dueFrom || undefined,
    due_to: dueTo || undefined,
    page,
    per_page: perPage,
  }
  const key = JSON.stringify(query)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const scope = {
        ...filters,
        department: department || filters.department,
        year: year || filters.year,
        semester: semester || filters.semester,
        section: section || filters.section,
        guide_id: guide || filters.guide_id,
        batch_code: batch || undefined,
      }
      const [b, q] = await Promise.all([
        fetchMilestoneBoard(query),
        fetchMilestoneQueue(scope),
      ])
      setBoard(b)
      setQueue(q)
      // Keep a milestone open across refreshes so approving one does not
      // throw the reader back to the top of the queue.
      const next = detail
        ? b.rows.find((r) => r.id === detail.id) ?? q.approvals[0] ?? b.rows[0]
        : q.approvals[0] ?? b.rows[0]
      if (next) fetchMilestoneDetail(next.id).then(setDetail).catch(() => setDetail(null))
    } catch (err: any) {
      setError(err?.message || 'Could not load milestones. Please try again.')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => { load() }, [load])
  useEffect(() => { fetchMilestoneInsight().then(setInsight).catch(() => setInsight(null)) }, [key])
  useEffect(() => { fetchFacultyFilters().then(setOptions).catch(() => setOptions(null)) }, [])

  useEffect(() => {
    onActions?.(
      <>
        <button className={BTN_PRIMARY} disabled={!!busy}
                onClick={() => setAdding((v) => !v)}>
          + Add Milestone
        </button>
        <button className={BTN} disabled={!!busy || picked.size === 0}
                onClick={() => act('evidence',
                  () => requestMilestoneEvidence([...picked], 'Evidence'))}>
          {busy === 'evidence' ? 'Working…' : 'Request Evidence'}
        </button>
        <button className={BTN} disabled={!!busy}
                onClick={() => act('export', async () => {
                  await exportMilestones(filters)
                  return { message: 'Exported what is currently filtered.' }
                })}>
          {busy === 'export' ? 'Exporting…' : 'Export Milestones'}
        </button>
      </>
    )
    return () => onActions?.(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busy, picked.size])

  const act = async (what: string, run: () => Promise<{ message: string }>) => {
    setBusy(what)
    setNotice('')
    try {
      const res = await run()
      setNotice(res.message)
      setPicked(new Set())
      await load()
    } catch (err: any) {
      setNotice(err?.response?.data?.detail || err?.message || 'That did not work.')
    } finally {
      setBusy('')
    }
  }

  const open = (id: string) =>
    fetchMilestoneDetail(id).then(setDetail).catch(() => setDetail(null))

  // Search runs here rather than server-side: the page is already loaded and
  // a coordinator typing a name expects the list to react as they type.
  const rows = (board?.rows ?? []).filter((r) => !term || [
    r.name, r.batch_code, r.project_title, r.owner,
  ].some((v) => (v || '').toLowerCase().includes(term)))
  const activeFilters = [department, year, semester, section, guide,
                         name, status, dueFrom, dueTo, term]
    .filter(Boolean).length

  return (
    <div className="flex flex-col gap-4">
      {(picked.size > 0 || notice) && (
        <div className="flex flex-wrap items-center gap-3 text-[12px]">
          {picked.size > 0 && (
            <span className="text-[#6B7686]">{picked.size} selected</span>
          )}
          {notice && <span className="text-[#4F46E5]">{notice}</span>}
        </div>
      )}

      {adding && (
        <div className={`${CARD} flex flex-wrap items-end gap-3`}>
          <Field label="Batch">
            <select className={SELECT} value={newBatch}
                    onChange={(e) => setNewBatch(e.target.value)}>
              <option value="">Choose a batch…</option>
              {(board?.options.batches ?? []).map((b) => <option key={b}>{b}</option>)}
            </select>
          </Field>
          <Field label="Milestone name">
            <input className={`${SELECT} w-56`} value={newName}
                   placeholder="e.g. API Integration"
                   onChange={(e) => setNewName(e.target.value)} />
          </Field>
          <Field label="Planned date">
            <input type="date" className={SELECT} value={newDate}
                   onChange={(e) => setNewDate(e.target.value)} />
          </Field>
          <Field label="Priority">
            <select className={SELECT} value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}>
              {(board?.options.priorities ?? ['medium']).map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </Field>
          <button className={BTN_PRIMARY}
                  disabled={!!busy || !newBatch || !newName.trim()}
                  onClick={() => act('add', async () => {
                    const res = await addMilestone(newBatch, {
                      name: newName.trim(),
                      planned_date: newDate || undefined,
                      priority: newPriority,
                    })
                    setAdding(false); setNewName(''); setNewDate('')
                    return res
                  })}>
            {busy === 'add' ? 'Adding…' : 'Add'}
          </button>
          <button className={BTN} onClick={() => setAdding(false)}>Cancel</button>
        </div>
      )}

      {/* filters — one strip, like the mockup, so nothing wraps to a second row */}
      <div className="flex flex-wrap items-end gap-2 xl:flex-nowrap">
        <Field label="Department">
          <select className={SELECT} value={department}
                  onChange={(e) => { setDepartment(e.target.value); setPage(1) }}>
            <option value="">All Departments</option>
            {(options?.departments ?? []).map((d) => <option key={d}>{d}</option>)}
          </select>
        </Field>
        <Field label="Year">
          <select className={SELECT} value={year}
                  onChange={(e) => { setYear(e.target.value); setPage(1) }}>
            <option value="">All Years</option>
            {(options?.years ?? []).map((y) => <option key={y}>{y}</option>)}
          </select>
        </Field>
        <Field label="Semester">
          <select className={SELECT} value={semester}
                  onChange={(e) => { setSemester(e.target.value); setPage(1) }}>
            <option value="">All Semesters</option>
            {(options?.semesters ?? []).map((v) => <option key={v}>{v}</option>)}
          </select>
        </Field>
        <Field label="Section">
          <select className={SELECT} value={section}
                  onChange={(e) => { setSection(e.target.value); setPage(1) }}>
            <option value="">All Sections</option>
            {(options?.sections ?? []).map((v) => <option key={v}>{v}</option>)}
          </select>
        </Field>
        <Field label="Guide">
          <select className={SELECT} value={guide}
                  onChange={(e) => { setGuide(e.target.value); setPage(1) }}>
            <option value="">All Guides</option>
            {(options?.guides ?? []).map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Milestone">
          <select className={SELECT} value={name}
                  onChange={(e) => { setName(e.target.value); setPage(1) }}>
            <option value="">All Milestones</option>
            {(board?.options.milestones ?? []).map((m) => <option key={m}>{m}</option>)}
          </select>
        </Field>
        <Field label="Status">
          <select className={SELECT} value={status}
                  onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
            <option value="">All Statuses</option>
            {(board?.options.statuses ?? []).map((v) => (
              <option key={v} value={v}>{v.replace('_', ' ')}</option>
            ))}
          </select>
        </Field>
        <Field label="Due date" grow>
          {/* One control, two bounds - the mockup shows a single field and a
              coordinator thinks of it as one range, not two dates. */}
          <div className="flex min-w-0 items-center gap-1 rounded-md border
                          border-[#E3E6EC] bg-white px-1.5 py-1">
            <input type="date" value={dueFrom} aria-label="Due from"
                   className="w-full min-w-0 border-0 p-0 text-[11px] outline-none"
                   onChange={(e) => { setDueFrom(e.target.value); setPage(1) }} />
            <span className="shrink-0 text-[#8A8FA8]">–</span>
            <input type="date" value={dueTo} aria-label="Due to"
                   className="w-full min-w-0 border-0 p-0 text-[11px] outline-none"
                   onChange={(e) => { setDueTo(e.target.value); setPage(1) }} />
          </div>
        </Field>
        <Field label="Search" grow>
          <input
            className={SELECT}
            placeholder="Milestone, batch or owner"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') setTerm(search.trim().toLowerCase()) }}
            onBlur={() => setTerm(search.trim().toLowerCase())}
          />
        </Field>
        {activeFilters > 0 && (
          <button className={BTN}
                  onClick={() => {
                    setDepartment(''); setYear(''); setSemester(''); setSection('')
                    setGuide(''); setBatch(''); setName(''); setStatus(''); setApproval('')
                    setDueFrom(''); setDueTo(''); setSearch(''); setTerm(''); setPage(1)
                  }}>
            Clear {activeFilters} filter{activeFilters > 1 ? 's' : ''}
          </button>
        )}
      </div>

      {/* counters */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {(board?.kpis ?? []).map((k) => (
          <div key={k.id} className={`${CARD} flex-row items-center gap-3`}>
            {/* The completion card is a ring rather than a badge - it is a
                proportion, and the mockup draws it as one. */}
            {k.id === 'rate' ? (
              <Ring percent={parseInt(String(k.value), 10) || 0} />
            ) : (
              <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center
                               rounded-xl text-[15px] text-white"
                    style={{ background: KPI_COLOUR[k.id] ?? '#6B7686' }}>
                {KPI_MARK[k.id] ?? '•'}
              </span>
            )}
            <div className="min-w-0">
              {/* Value first, label under it - the number is what the card is
                  for, and the mockup leads with it. */}
              <p className={`text-2xl font-semibold leading-tight ${
                k.tone === 'danger' ? 'text-[#DC2626]'
                  : k.tone === 'warn' ? 'text-[#B45309]' : 'text-[#131A24]'}`}>
                {k.value}
              </p>
              <p className="truncate text-[11px] text-[#6B7686]">{k.label}</p>
              {/* Only where a delta can be measured. The rest are point-in-time
                  counts with no history behind them, and inventing an arrow
                  for those would be worse than leaving the space empty. */}
              {typeof k.delta === 'number' && k.delta !== 0 && (() => {
                // On a counter where fewer is better - overdue work, an
                // approval backlog - a rise is bad news, so the colour follows
                // the meaning rather than the sign.
                const good = k.lower_is_better ? k.delta < 0 : k.delta > 0
                return (
                  <p className={`text-[10px] ${good ? 'text-[#15803D]' : 'text-[#DC2626]'}`}>
                    {k.delta > 0 ? '▲' : '▼'} {Math.abs(k.delta)}{k.suffix ?? ''} vs last 2 weeks
                  </p>
                )
              })()}
            </div>
          </div>
        ))}
      </div>

      <ResourceState loading={loading} error={error} empty={false} onRetry={load}>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_21rem]">
          <div className="flex min-w-0 flex-col gap-4">
            <div className={CARD}>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-[15px] font-semibold text-[#131A24]">Milestone Tracker</h3>
                <div className="flex gap-1">
                  {(['Timeline', 'List', 'Calendar'] as const).map((v) => (
                    <button key={v} onClick={() => setView(v)}
                            className={`rounded-md px-2.5 py-1 text-[12px] ${
                              view === v ? 'bg-[#4F46E5] text-white'
                                : 'border border-[#E3E6EC] text-[#6B7686]'}`}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {view === 'Timeline' && (
                <Timeline board={board} onPick={open} selected={detail?.id}
                          weeks={weeks} onWeeks={setWeeks} />
              )}
              {view === 'List' && (
                <Details rows={rows} picked={picked} setPicked={setPicked}
                         onPick={open} selected={detail?.id} busy={busy}
                         onApprove={(id) => act('approve', () => approveMilestone(id))}
                         onEvidence={(id) => act('evidence',
                           () => requestMilestoneEvidence([id], 'Evidence'))}
                         onChanges={(id) => {
                           const note = window.prompt('What needs changing?')
                           if (note && note.trim()) {
                             act('changes', () => requestMilestoneChanges(id, note.trim()))
                           }
                         }} />
              )}
              {view === 'Calendar' && (
                <Calendar rows={board?.rows ?? []} today={board?.window.today}
                          onPick={open} selected={detail?.id} />
              )}
            </div>

            {/* The details table sits under the two graphical views; the List
                view is that table, so showing it twice there is noise. */}
            {view !== 'List' && (
              <div className={CARD}>
                <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                  <h3 className="text-[15px] font-semibold text-[#131A24]">
                    Milestone Details
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    <button className={BTN} disabled={!!busy || picked.size === 0}
                            onClick={() => act('bulk-approve',
                              () => bulkMilestones([...picked], 'approve'))}>
                      ✓ Approve Selected
                    </button>
                    <button className={BTN} disabled={!!busy || picked.size === 0}
                            onClick={() => act('bulk-chase',
                              () => bulkMilestones([...picked], 'request_update', 'Progress update'))}>
                      Request Update
                    </button>
                    <button className={BTN} disabled={!!busy || picked.size === 0}
                            onClick={() => {
                              const when = window.prompt('New planned date (YYYY-MM-DD)')
                              if (when && when.trim()) {
                                act('bulk-date',
                                  () => bulkMilestones([...picked], 'due_date', when.trim()))
                              }
                            }}>
                      Change Due Date
                    </button>
                    <button className={BTN} disabled={!!busy}
                            onClick={() => act('export', async () => {
                              await exportMilestones(filters)
                              return { message: 'Exported what is currently filtered.' }
                            })}>
                      Export
                    </button>
                  </div>
                </div>
                <Details rows={rows} picked={picked} setPicked={setPicked}
                         onPick={open} selected={detail?.id} busy={busy}
                         onApprove={(id) => act('approve', () => approveMilestone(id))}
                         onEvidence={(id) => act('evidence',
                           () => requestMilestoneEvidence([id], 'Evidence'))}
                         onChanges={(id) => {
                           const note = window.prompt('What needs changing?')
                           if (note && note.trim()) {
                             act('changes', () => requestMilestoneChanges(id, note.trim()))
                           }
                         }} />
                <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#8A8FA8]">
                  <span>Showing {rows.length} of {board?.total ?? 0} milestones</span>
                  <div className="flex items-center gap-1">
                    <button className={PAGE_BTN} disabled={page <= 1}
                            onClick={() => setPage((p) => Math.max(1, p - 1))}>‹</button>
                    {pageNumbers(page, board?.pages ?? 1).map((n, i) =>
                      n === 0 ? (
                        <span key={`gap-${i}`} className="px-1">…</span>
                      ) : (
                        <button key={n}
                                className={`${PAGE_BTN} ${
                                  n === page ? 'bg-[#4F46E5] text-white border-[#4F46E5]' : ''}`}
                                onClick={() => setPage(n)}>
                          {n}
                        </button>
                      ))}
                    <button className={PAGE_BTN} disabled={!!board && page >= board.pages}
                            onClick={() => setPage((p) => p + 1)}>›</button>
                    <select className="ml-2 rounded border border-[#E3E6EC] px-1 py-0.5 text-[11px]"
                            value={perPage}
                            onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}>
                      {[5, 10, 20, 50].map((n) => (
                        <option key={n} value={n}>{n} / page</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* right rail */}
          <div className="flex flex-col gap-4">
            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">
                Approval Queue{queue?.approval_total ? ` (${queue.approval_total})` : ''}
              </h3>
              {(queue?.approvals ?? []).length === 0 ? (
                <p className="text-[12px] text-[#8A8FA8]">Nothing is waiting on a signature.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {(queue?.approvals ?? []).map((a) => (
                    <div key={a.id}
                         className={`flex items-center gap-2 rounded-md px-1.5 py-1 text-[12px] ${
                           detail?.id === a.id ? 'bg-[#F5F3FF]' : ''}`}>
                      <button onClick={() => open(a.id)}
                              className="flex-1 truncate text-left text-[#131A24]">
                        {a.name}
                        <span className="ml-1 text-[10px] text-[#8A8FA8]">{a.batch_code}</span>
                      </button>
                      <span className={`text-[10px] ${
                        a.evidence_verified < a.evidence_total
                          ? 'text-[#B45309]' : 'text-[#6B7686]'}`}>
                        {a.evidence_verified}/{a.evidence_total}
                      </span>
                      {/* Approve is offered only when the evidence is in - the
                          server refuses otherwise, and a button that always
                          fails is worse than no button. */}
                      {a.evidence_verified >= a.evidence_total ? (
                        <button className="rounded bg-[#4F46E5] px-1.5 py-0.5 text-[10px] text-white"
                                disabled={!!busy}
                                onClick={() => act('approve', () => approveMilestone(a.id))}>
                          Approve
                        </button>
                      ) : (
                        <button className="rounded border border-[#E3E6EC] px-1.5 py-0.5 text-[10px] text-[#6B7686]"
                                onClick={() => open(a.id)}>
                          Review
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {(queue?.approval_total ?? 0) > 0 && (
                <button
                  className={`${BTN_PRIMARY} mt-2 w-full`}
                  onClick={() => { setApproval('review_ready'); setPage(1) }}
                >
                  Open Approval Queue
                </button>
              )}
            </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Upcoming Deadlines</h3>
              {(queue?.upcoming ?? []).length === 0 ? (
                <p className="text-[12px] text-[#8A8FA8]">Nothing due.</p>
              ) : (queue?.upcoming ?? []).map((u) => (
                <div key={u.id} className="flex items-center gap-2 py-0.5 text-[12px]">
                  <span className="w-12 shrink-0 text-[#8A8FA8]">{u.planned_display}</span>
                  <span className="flex-1 truncate text-[#131A24]">{u.name}</span>
                  <span className="text-[10px] text-[#8A8FA8]">{u.batch_code}</span>
                  <span style={{ color: HEALTH_COLOUR[u.health] }}
                        className="text-[10px]">{u.health}</span>
                </div>
              ))}
              {(queue?.upcoming ?? []).length > 0 && (
                <button className={`${BTN} mt-2 w-full`}
                        onClick={() => setView('Calendar')}>
                  View Calendar
                </button>
              )}
            </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Milestone Health</h3>
              <div className="flex items-center gap-3">
                <Donut slices={queue?.health ?? []} />
                <div className="min-w-0 flex-1">
              {(queue?.health ?? []).map((h) => (
                <div key={h.label} className="mb-1 flex items-center gap-2 text-[12px]">
                  <span className="inline-block h-2 w-2 shrink-0 rounded-full"
                        style={{ background: HEALTH_COLOUR[h.label] }} />
                  <span className="flex-1 text-[#6B7686]">{h.label}</span>
                  <span className="text-[#131A24]">{h.count}</span>
                  <span className="w-10 text-right text-[10px] text-[#8A8FA8]">
                    ({h.percent}%)
                  </span>
                </div>
              ))}
                </div>
              </div>
            </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">
                Dependency Alerts{queue?.alert_total ? ` (${queue.alert_total})` : ''}
              </h3>
              {(queue?.alerts ?? []).length === 0 ? (
                <p className="text-[12px] text-[#8A8FA8]">Nothing is waiting on anything.</p>
              ) : (queue?.alerts ?? []).map((a, i) => (
                <div key={`${a.batch_code}-${i}`} className="py-0.5 text-[12px]">
                  <span className="text-[#B45309]">{a.message}</span>
                  <span className="ml-1 text-[10px] text-[#8A8FA8]">{a.batch_code}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ResourceState>

      {/* selected milestone, with the activity feed beside it */}
      {detail && (
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <div className={CARD}>
          <div className="flex flex-wrap items-baseline gap-2">
            <h3 className="text-[15px] font-semibold text-[#131A24]">
              Selected Milestone — {detail.name}
            </h3>
            <span className="text-[12px] text-[#6B7686]">
              {detail.batch_code} · {detail.project_title}
            </span>
            <span style={{ color: HEALTH_COLOUR[detail.health] }} className="text-[11px]">
              {detail.health}
            </span>
            <span className="text-[11px] text-[#8A8FA8]">
              {APPROVAL_LABEL[detail.approval] ?? detail.approval} · {detail.progress}%
            </span>
          </div>

          {detail.review_note && (
            <p className="mt-1 rounded-md border border-[#FDE68A] bg-[#FFFBEB] px-2 py-1 text-[11px] text-[#B45309]">
              Reviewer: {detail.review_note}
            </p>
          )}

          <div className="mt-3 grid gap-4 md:grid-cols-3">
            <div>
              <p className={`${LABEL} mb-1`}>Checklist</p>
              {detail.checklist.length === 0
                ? <p className="text-[12px] text-[#8A8FA8]">No checklist.</p>
                : detail.checklist.map((c) => (
                  <label key={c.id} className="flex items-center gap-2 py-0.5 text-[12px]">
                    <input type="checkbox" checked={c.done} disabled={!!busy}
                           onChange={(e) => act('checklist',
                             () => toggleMilestoneChecklist(c.id, e.target.checked))} />
                    <span className={c.done ? 'text-[#6B7686] line-through' : 'text-[#131A24]'}>
                      {c.label}
                    </span>
                  </label>
                ))}
            </div>

            <div>
              <p className={`${LABEL} mb-1`}>
                Evidence {detail.evidence_verified}/{detail.evidence_total}
              </p>
              {detail.evidence.length === 0
                ? <p className="text-[12px] text-[#8A8FA8]">None requested.</p>
                : detail.evidence.map((e) => (
                  <div key={e.id} className="flex items-center gap-2 py-0.5 text-[12px]">
                    <span className="flex-1 truncate text-[#131A24]">{e.label}</span>
                    <span className="text-[10px] capitalize text-[#6B7686]">{e.status}</span>
                    {e.status !== 'verified' && e.status !== 'pending' && (
                      <button className="text-[10px] text-[#4F46E5]" disabled={!!busy}
                              onClick={() => act('verify', () => verifyMilestoneEvidence(e.id))}>
                        Verify
                      </button>
                    )}
                  </div>
                ))}
            </div>

            <div>
              <p className={`${LABEL} mb-1`}>Waits on</p>
              {detail.depends_on.length === 0
                ? <p className="text-[12px] text-[#8A8FA8]">Nothing.</p>
                : detail.depends_on.map((d) => (
                  <div key={d.id} className="py-0.5 text-[12px]">
                    <span className="text-[#131A24]">{d.name}</span>
                    <span className={`ml-1 text-[10px] ${
                      d.status === 'complete' ? 'text-[#15803D]' : 'text-[#DC2626]'}`}>
                      {d.status.replace('_', ' ')}
                    </span>
                  </div>
                ))}
              <p className={`${LABEL} mb-1 mt-3`}>Owner / Reviewer</p>
              <p className="text-[12px] text-[#6B7686]">
                {detail.owner ?? 'Unassigned'} · {detail.reviewer ?? 'No reviewer'}
              </p>
              <p className="mt-1 text-[11px] text-[#8A8FA8]">
                Planned {detail.planned_display ?? '—'}
                {detail.slipping && detail.forecast_display && (
                  <span className="text-[#DC2626]"> · forecast {detail.forecast_display}</span>
                )}
              </p>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <button className={BTN_PRIMARY} disabled={!!busy || detail.approval === 'approved'}
                    onClick={() => act('approve', () => approveMilestone(detail.id))}>
              {detail.approval === 'approved' ? 'Approved' : 'Approve'}
            </button>
            <button className={BTN} disabled={!!busy}
                    onClick={() => {
                      const note = window.prompt('What needs changing?')
                      if (note && note.trim()) {
                        act('changes', () => requestMilestoneChanges(detail.id, note.trim()))
                      }
                    }}>
              Request Changes
            </button>
            <button className={BTN} disabled={!!busy}
                    onClick={() => act('evidence',
                      () => requestMilestoneEvidence([detail.id], 'Evidence'))}>
              Request Evidence
            </button>
            <button className={BTN}
                    onClick={() => {
                      setApproval('review_ready'); setBatch(detail.batch_code); setPage(1)
                    }}>
              Review Evidence
            </button>
            <a className={BTN}
               href={`/faculty/registrations/${encodeURIComponent(detail.batch_code)}`}>
              Open Project
            </a>
            {/* No messaging channel exists, so this says so rather than
                pretending to send something. */}
            <button className={BTN} disabled title="No messaging channel is configured yet">
              Message Owner
            </button>
          </div>

          {detail.evidence_verified < detail.evidence_total && (
            /* Said before they click, not after it is refused. */
            <p className="mt-2 text-[11px] text-[#B45309]">
              {detail.evidence_total - detail.evidence_verified} piece(s) of evidence
              still need verifying before this can be approved.
            </p>
          )}
        </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">
                Recent Milestone Activity
              </h3>
              {(detail?.activity ?? []).length === 0 ? (
                <p className="text-[12px] text-[#8A8FA8]">
                  Select a milestone to see its project's activity.
                </p>
              ) : (
                <>
                  {(detail?.activity ?? []).map((a) => (
                    <div key={a.code} className="py-0.5 text-[12px]">
                      <span className="text-[#131A24]">{a.summary}</span>
                      <span className="block text-[10px] text-[#8A8FA8]">
                        {a.at}{a.actor ? ` · ${a.actor}` : ''}
                      </span>
                    </div>
                  ))}
                  {onViewActivity && (
                    <button className="mt-2 text-[11px] text-[#4F46E5]"
                            onClick={onViewActivity}>
                      View All Activity
                    </button>
                  )}
                </>
              )}
            </div>
        </div>
      )}

      {insight && (
        <div className="rounded-xl border border-[#E0E7FF] bg-[#EEF2FF] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-2xl text-[13px] text-[#131A24]">
              <span className="font-semibold">Insight: </span>
              {insight.headline} {insight.detail}
            </p>
            <div className="flex flex-wrap gap-2">
              <button className={BTN_PRIMARY}
                      onClick={() => { setStatus('delayed'); setPage(1) }}>
                Review {insight.at_risk} At-Risk Milestones
              </button>
              <button className={BTN} disabled={!!busy}
                      onClick={() => act('plan', async () => {
                        const p = await fetchRecoveryPlan(filters)
                        setPlan(p.steps)
                        return { message: p.headline }
                      })}>
                {busy === 'plan' ? 'Working…' : 'Generate Recovery Plan'}
              </button>
            </div>
          </div>
          <p className="mt-2 text-[10px] text-[#6B7686]">
            Counted from milestones whose dates or dependencies have already slipped.
          </p>

          {plan.length > 0 && (
            <div className="mt-3 rounded-lg border border-[#E0E7FF] bg-white p-3">
              <div className="mb-2 flex items-center justify-between">
                <p className="text-[12px] font-semibold text-[#131A24]">
                  Recovery order — clear these first
                </p>
                <button className="text-[11px] text-[#6B7686]"
                        onClick={() => setPlan([])}>Dismiss</button>
              </div>
              {plan.map((step, i) => (
                <div key={step.id} className="flex gap-2 border-t border-[#F1F2F8] py-1.5 text-[12px]">
                  <span className="w-5 shrink-0 text-[#8A8FA8]">{i + 1}.</span>
                  <button className="min-w-0 flex-1 text-left"
                          onClick={() => open(step.id)}>
                    <span className="text-[#131A24]">{step.name}</span>
                    <span className="ml-1 text-[10px] text-[#4F46E5]">{step.batch_code}</span>
                    <span className="block text-[10px] text-[#6B7686]">
                      {step.why.join(' · ')}
                    </span>
                  </button>
                  <span className="shrink-0 text-[10px] text-[#8A8FA8]">
                    {step.blocks > 0 && `unblocks ${step.blocks}`}
                    {step.overdue_days > 0 && ` · ${step.overdue_days}d late`}
                  </span>
                </div>
              ))}
              {/* The plan is an ordering, not a prediction - said plainly so
                  nobody reads more into it than the data supports. */}
              <p className="mt-2 text-[10px] text-[#6B7686]">
                Ordered by how many milestones each one is holding up, then by
                how far past its date it is.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * One row per milestone, grouped under its project, over a short date window.
 *
 * The first version drew a single band per project with every milestone
 * squeezed onto it, across the whole cohort's range - March to December. At
 * that scale a fortnight's slip was a pixel. This gives each milestone its own
 * row with its name on the left, and defaults the axis to the weeks around
 * today, which is the span a coordinator is actually working in.
 */
function Timeline({
  board, onPick, selected, weeks, onWeeks,
}: {
  board: MilestoneBoardData | null
  onPick: (id: string) => void
  selected?: string
  weeks: number
  onWeeks: (w: number) => void
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const onToggle = (code: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev)
      next.has(code) ? next.delete(code) : next.add(code)
      return next
    })
  if (!board || board.tracker.length === 0) {
    return <p className="text-[12px] text-[#8A8FA8]">Nothing to plot.</p>
  }

  const today = new Date(board.window.today)
  // A day either side of today, then the chosen span. Starting three days
  // back pushed today off-centre and cost a column of the window.
  const from = new Date(today); from.setDate(from.getDate() - 1)
  const to = new Date(today); to.setDate(to.getDate() + weeks * 7 - 1)
  const start = from.getTime()
  const span = Math.max(1, to.getTime() - start)
  const at = (iso: string | null) =>
    iso ? ((new Date(iso).getTime() - start) / span) * 100 : null

  // Day ticks, thinned so the labels never collide.
  const days: Date[] = []
  for (let d = new Date(from); d <= to; d.setDate(d.getDate() + 1)) {
    days.push(new Date(d))
  }
  // A label per day on a fortnight's view - that is the density a schedule
  // is actually read at. Longer windows thin out or the labels collide.
  const step = days.length <= 16 ? 1 : Math.max(1, Math.round(days.length / 12))
  // Where today sits on the axis - the badge, the dashed line and every
  // gridline are positioned against it.
  const todayAt = at(board.window.today) ?? 0

  const inWindow = (m: MilestoneItem) => {
    const l = at(m.planned_start ?? m.planned_date)
    const r = at(m.forecast_date ?? m.planned_date)
    return l !== null && r !== null && r >= 0 && l <= 100
  }
  const groups = board.tracker
    .map((g) => ({ ...g, milestones: g.milestones.filter(inWindow) }))
    .filter((g) => g.milestones.length > 0)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-end gap-1 text-[11px]">
        <span className="text-[#8A8FA8]">Window</span>
        {[2, 4, 12].map((w) => (
          <button key={w} onClick={() => onWeeks(w)}
                  className={`rounded px-2 py-0.5 ${
                    weeks === w ? 'bg-[#4F46E5] text-white'
                      : 'border border-[#E3E6EC] text-[#6B7686]'}`}>
            {w}w
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[46rem]">
          {/* date axis: a tick per day, with today marked */}
          <div className="flex border-b border-[#E3E6EC] pb-1">
            <div className="w-56 shrink-0 text-[10px] uppercase tracking-wider
                            text-[#8A8FA8]">
              Batch / Milestone
            </div>
            <div className="relative h-6 flex-1">
              {days.filter((_, i) => i % step === 0).map((d) => (
                <span key={d.toISOString()}
                      className="absolute top-2 -translate-x-1/2 text-[10px] text-[#8A8FA8]"
                      style={{ left: `${at(d.toISOString().slice(0, 10))}%` }}>
                  {d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                </span>
              ))}
              {/* The badge sits on the axis, so the line below needs no label */}
              <span className="absolute -translate-x-1/2 rounded bg-[#4F46E5] px-1.5
                               py-0.5 text-[9px] font-medium text-white"
                    style={{ left: `${todayAt}%` }}>
                Today {new Date(board.window.today).toLocaleDateString('en-GB',
                  { day: '2-digit', month: 'short' })}
              </span>
            </div>
          </div>

          {groups.length === 0 && (
            <p className="py-3 text-[12px] text-[#8A8FA8]">
              Nothing falls in this window. Try a longer one.
            </p>
          )}

          {groups.map((g) => {
            const open = !collapsed.has(g.batch_code)
            const shown = open ? g.milestones : []
            const height = shown.length * ROW_H
            // Where each bar begins and ends, in percent, so the connectors
            // can be drawn from one row to the next.
            const spans = shown.map((m) => {
              const from = Math.max(0, at(m.planned_start ?? m.planned_date) ?? 0)
              const to = Math.min(100, at(m.forecast_date ?? m.planned_date) ?? 0)
              // A bar leaves from its right edge; a point marker leaves from
              // itself, which is the date it is due.
              const point = isReview(m) || m.status === 'complete'
              return { from: point ? to : from, to, anchor: to }
            })
            return (
              <div key={g.batch_code} className="border-b border-[#F1F2F8] py-1.5">
                <div className="flex">
                  <button
                    className="w-56 shrink-0 pr-2 text-left"
                    onClick={() => onToggle(g.batch_code)}
                    aria-expanded={open}
                  >
                    <span className="mr-1 inline-block w-3 text-[10px] text-[#8A8FA8]">
                      {open ? '▾' : '▸'}
                    </span>
                    <span className="text-[11px] font-medium text-[#4F46E5]">
                      {g.batch_code}
                    </span>
                    <span className="ml-1 text-[10px] text-[#8A8FA8]">
                      {g.project_title}
                    </span>
                  </button>
                </div>

                {open && (
                  <div className="flex">
                    {/* left: one line per milestone. A review reads as a
                        diamond and a finished item as a tick, matching the
                        marker drawn for it on the right. */}
                    <div className="w-56 shrink-0">
                      {shown.map((m) => (
                        <button key={m.id} onClick={() => onPick(m.id)}
                                style={{ height: ROW_H }}
                                className={`flex w-full items-center truncate pr-2 text-left text-[11px] ${
                                  selected === m.id
                                    ? 'font-medium text-[#4F46E5]' : 'text-[#6B7686]'}`}>
                          {isReview(m) ? (
                            <span className="mr-1.5 shrink-0 text-[8px] text-[#4F46E5]">◇</span>
                          ) : (
                            <span className="mr-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full"
                                  style={{ background: HEALTH_COLOUR[m.health] ?? '#9AA1B1' }} />
                          )}
                          <span className="truncate">{m.name}</span>
                        </button>
                      ))}
                    </div>

                    {/* right: markers, bars, gridlines and the connectors */}
                    <div className="relative flex-1" style={{ height }}>
                      {days.filter((_, i) => i % step === 0).map((d) => (
                        <div key={d.toISOString()}
                             className="absolute inset-y-0 w-px bg-[#F4F5F8]"
                             style={{ left: `${at(d.toISOString().slice(0, 10))}%` }} />
                      ))}
                      <div className="absolute inset-y-0 border-l border-dashed border-[#4F46E5]"
                           style={{ left: `${todayAt}%` }} />

                      {/* Elbows from each anchor to the next. Percentages are
                          valid on line coordinates but not inside a path's
                          `d` string, where they silently draw nothing. */}
                      <svg className="pointer-events-none absolute inset-0 h-full w-full"
                           preserveAspectRatio="none">
                        {spans.slice(0, -1).map((sp, i) => {
                          const next = spans[i + 1]
                          const y1 = i * ROW_H + ROW_H / 2
                          const y2 = (i + 1) * ROW_H + ROW_H / 2
                          const turn = Math.max(sp.anchor, next.from - 1.2)
                          return (
                            <g key={i} stroke="#B9BFCC" strokeWidth="1.25" fill="none">
                              <line x1={`${sp.anchor}%`} y1={y1} x2={`${turn}%`} y2={y1} />
                              <line x1={`${turn}%`} y1={y1} x2={`${turn}%`} y2={y2} />
                              <line x1={`${turn}%`} y1={y2} x2={`${next.from}%`} y2={y2} />
                            </g>
                          )
                        })}
                      </svg>

                      {shown.map((m, i) => {
                        const sp = spans[i]
                        const top = i * ROW_H
                        // A review is a point in time, not a span, so it is a
                        // diamond. A finished milestone is a tick rather than a
                        // greyed-out bar - it no longer occupies the schedule.
                        if (isReview(m)) {
                          return (
                            <button key={m.id} onClick={() => onPick(m.id)}
                                    title={`${m.name} · ${m.status}`}
                                    className="absolute -translate-x-1/2 text-[11px] text-[#4F46E5]"
                                    style={{ left: `${sp.anchor}%`, top: top + 3 }}>
                              ◇
                            </button>
                          )
                        }
                        if (m.status === 'complete') {
                          return (
                            <button key={m.id} onClick={() => onPick(m.id)}
                                    title={`${m.name} · complete`}
                                    className="absolute flex h-4 w-4 -translate-x-1/2 items-center
                                               justify-center rounded-full bg-[#15803D] text-[9px]
                                               font-bold text-white"
                                    style={{ left: `${sp.anchor}%`, top: top + 3 }}>
                              ✓
                            </button>
                          )
                        }
                        const width = Math.max(2, sp.to - sp.from)
                        return (
                          <div key={m.id} className="absolute inset-x-0"
                               style={{ top, height: ROW_H }}>
                            <button
                              onClick={() => onPick(m.id)}
                              title={`${m.name} · ${m.status} · ${m.progress}%`}
                              className={`absolute top-1 h-3.5 rounded-full ${
                                selected === m.id ? 'ring-2 ring-[#4F46E5]' : ''}`}
                              style={{
                                left: `${sp.from}%`,
                                width: `${width}%`,
                                background: HEALTH_COLOUR[m.health] ?? '#9AA1B1',
                              }}
                            />
                            {m.progress > 0 && (
                              <span className="absolute top-1 text-[10px] font-medium text-[#6B7686]"
                                    style={{ left: `${Math.min(93, sp.to + 0.8)}%` }}>
                                {m.progress}%
                              </span>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          <p className="mt-2 text-[11px] text-[#8A8FA8]">
            Bars run from planned start to forecast date. The vertical line is today.
          </p>
        </div>
      </div>
    </div>
  )
}

const MENU_ITEM = 'block w-full px-3 py-1.5 text-left text-[12px] text-[#131A24] hover:bg-[#FAFAFC]'

function Details({
  rows, picked, setPicked, onPick, selected, onApprove, onEvidence, onChanges, busy,
}: {
  rows: MilestoneItem[]
  picked: Set<string>
  setPicked: (s: Set<string>) => void
  onPick: (id: string) => void
  selected?: string
  onApprove: (id: string) => void
  onEvidence: (id: string) => void
  onChanges: (id: string) => void
  busy: string
}) {
  const [menu, setMenu] = useState<string | null>(null)
  const allOn = rows.length > 0 && rows.every((r) => picked.has(r.id))
  const toggleAll = () => {
    const next = new Set(picked)
    rows.forEach((r) => (allOn ? next.delete(r.id) : next.add(r.id)))
    setPicked(next)
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[54rem] text-[12px]">
        <thead>
          <tr className={`${LABEL} text-left`}>
            <th className="pb-2 pr-2">
              <input type="checkbox" checked={allOn} onChange={toggleAll}
                     aria-label="Select all milestones" />
            </th>
            <th className="pb-2 font-medium">Priority</th>
            <th className="pb-2 font-medium">Milestone</th>
            <th className="pb-2 font-medium">Batch / Project</th>
            <th className="pb-2 font-medium">Owner</th>
            <th className="pb-2 font-medium">Planned</th>
            <th className="pb-2 font-medium">Forecast</th>
            <th className="pb-2 font-medium">Progress</th>
            <th className="pb-2 font-medium">Evidence</th>
            <th className="pb-2 font-medium">Dependencies</th>
            <th className="pb-2 font-medium">Approval</th>
            <th className="pb-2 font-medium">Status</th>
            <th className="pb-2 font-medium">Action</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}
                onClick={() => onPick(r.id)}
                className={`cursor-pointer border-t border-[#F1F2F8] hover:bg-[#FAFAFC] ${
                  selected === r.id ? 'bg-[#F5F3FF]' : ''}`}>
              <td className="py-1.5 pr-2" onClick={(e) => e.stopPropagation()}>
                <input type="checkbox" checked={picked.has(r.id)}
                       onChange={() => {
                         const next = new Set(picked)
                         next.has(r.id) ? next.delete(r.id) : next.add(r.id)
                         setPicked(next)
                       }}
                       aria-label={`Select ${r.name}`} />
              </td>
              <td className="py-1.5">
                <span className={`rounded border px-1.5 py-0.5 text-[10px] ${
                  PRIORITY_TONE[r.priority] ?? PRIORITY_TONE.low}`}>{r.priority}</span>
              </td>
              <td className="py-1.5 text-[#131A24]">{r.name}</td>
              <td className="py-1.5">
                <span className="font-medium text-[#4F46E5]">{r.batch_code}</span>
                <span className="block text-[10px] text-[#8A8FA8]">{r.project_title}</span>
              </td>
              <td className="py-1.5 text-[#6B7686]">{r.owner ?? 'Unassigned'}</td>
              <td className="py-1.5 text-[#6B7686]">{r.planned_display ?? '—'}</td>
              <td className={`py-1.5 ${r.slipping ? 'text-[#DC2626]' : 'text-[#6B7686]'}`}>
                {r.forecast_display ?? '—'}
              </td>
              <td className="py-1.5">
                <div className="flex items-center gap-1.5">
                  <div className="h-1.5 w-16 overflow-hidden rounded-full bg-[#EEF0F4]">
                    <div className="h-full rounded-full"
                         style={{ width: `${r.progress}%`,
                                  background: HEALTH_COLOUR[r.health] ?? '#4F46E5' }} />
                  </div>
                  <span className="text-[10px] text-[#6B7686]">{r.progress}%</span>
                </div>
              </td>
              <td className={`py-1.5 ${
                r.evidence_verified < r.evidence_total ? 'text-[#B45309]' : 'text-[#6B7686]'}`}>
                {r.evidence_verified}/{r.evidence_total}
              </td>
              <td className="py-1.5">
                {r.waiting_on ? (
                  <span className={r.waiting_on.endsWith('✓')
                    ? 'text-[#15803D]' : 'text-[#B45309]'}>
                    {r.waiting_on}
                  </span>
                ) : (
                  <span className="text-[#8A8FA8]">—</span>
                )}
              </td>
              <td className="py-1.5 text-[#6B7686]">
                {APPROVAL_LABEL[r.approval] ?? r.approval}
              </td>
              <td className="py-1.5" style={{ color: HEALTH_COLOUR[r.health] }}>
                {r.status.replace('_', ' ')}
              </td>
              <td className="py-1.5" onClick={(e) => e.stopPropagation()}>
                {/* The row offers what is actually possible: approve only once
                    the evidence is in, otherwise open it and look. */}
                <div className="flex items-center gap-1">
                  {r.approval === 'approved' ? (
                    <span className="text-[10px] text-[#15803D]">Approved</span>
                  ) : r.evidence_verified >= r.evidence_total ? (
                    <button className="rounded bg-[#4F46E5] px-1.5 py-0.5 text-[10px] text-white"
                            disabled={!!busy}
                            onClick={() => onApprove(r.id)}>
                      Approve
                    </button>
                  ) : (
                    <button className="rounded border border-[#E3E6EC] px-1.5 py-0.5 text-[10px] text-[#6B7686]"
                            onClick={() => onPick(r.id)}>
                      Review
                    </button>
                  )}
                  <div className="relative">
                    <button className="px-1 text-[13px] text-[#8A8FA8]"
                            onClick={() => setMenu(menu === r.id ? null : r.id)}
                            aria-label="More actions">⋮</button>
                    {menu === r.id && (
                      <div className="absolute right-0 z-10 mt-1 w-40 rounded-md border
                                      border-[#E3E6EC] bg-white py-1 shadow-lg">
                        <button className={MENU_ITEM}
                                onClick={() => { setMenu(null); onPick(r.id) }}>
                          Open milestone
                        </button>
                        <button className={MENU_ITEM}
                                onClick={() => { setMenu(null); onEvidence(r.id) }}>
                          Request evidence
                        </button>
                        <button className={MENU_ITEM}
                                onClick={() => { setMenu(null); onChanges(r.id) }}>
                          Request changes
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={13} className="py-4 text-center text-[#8A8FA8]">
              No milestones match this view.
            </td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Milestones laid out by the day they are due.
 *
 * The timeline answers "is this slipping"; the calendar answers "what lands
 * this week", which is the question when planning review slots. Only days
 * that actually carry something are drawn - an empty grid of thirty boxes
 * tells a coordinator nothing.
 */
function Calendar({
  rows, today, onPick, selected,
}: {
  rows: MilestoneItem[]
  today?: string
  onPick: (id: string) => void
  selected?: string
}) {
  const byDay = new Map<string, MilestoneItem[]>()
  rows.forEach((r) => {
    const day = r.forecast_date ?? r.planned_date
    if (!day) return
    if (!byDay.has(day)) byDay.set(day, [])
    byDay.get(day)!.push(r)
  })
  const days = [...byDay.keys()].sort()

  if (days.length === 0) {
    return <p className="text-[12px] text-[#8A8FA8]">Nothing has a date in this view.</p>
  }

  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {days.map((day) => (
        <div key={day}
             className={`rounded-lg border p-2 ${
               day === today ? 'border-[#4F46E5] bg-[#F5F3FF]' : 'border-[#E3E6EC]'}`}>
          <p className="mb-1 text-[11px] font-medium text-[#131A24]">
            {fmt(day)}
            {day === today && <span className="ml-1 text-[10px] text-[#4F46E5]">today</span>}
            <span className="ml-1 text-[10px] text-[#8A8FA8]">
              {byDay.get(day)!.length} due
            </span>
          </p>
          {byDay.get(day)!.slice(0, 5).map((m) => (
            <button key={m.id} onClick={() => onPick(m.id)}
                    className={`block w-full truncate rounded px-1 py-0.5 text-left text-[11px] hover:bg-[#FAFAFC] ${
                      selected === m.id ? 'bg-[#EEF2FF]' : ''}`}>
              <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full align-middle"
                    style={{ background: HEALTH_COLOUR[m.health] ?? '#9AA1B1' }} />
              {m.name}
              <span className="ml-1 text-[10px] text-[#8A8FA8]">{m.batch_code}</span>
            </button>
          ))}
          {byDay.get(day)!.length > 5 && (
            <p className="px-1 text-[10px] text-[#8A8FA8]">
              +{byDay.get(day)!.length - 5} more
            </p>
          )}
        </div>
      ))}
    </div>
  )
}

/**
 * The health split as a ring.
 *
 * Drawn with stroke-dasharray on a single circle rather than arc paths - five
 * slices do not need path maths, and the segments stay crisp at any size.
 */
function Donut({ slices }: { slices: { label: string; count: number }[] }) {
  const total = slices.reduce((sum, s) => sum + s.count, 0)
  if (!total) return null
  const R = 42
  const C = 2 * Math.PI * R
  let offset = 0
  return (
    <div className="mb-2 flex justify-center">
      <svg viewBox="0 0 110 110" className="h-24 w-24 -rotate-90">
        {slices.filter((s) => s.count > 0).map((s) => {
          const len = (s.count / total) * C
          const el = (
            <circle
              key={s.label}
              cx="55" cy="55" r={R}
              fill="none"
              stroke={HEALTH_COLOUR[s.label] ?? '#9AA1B1'}
              strokeWidth="14"
              strokeDasharray={`${len} ${C - len}`}
              strokeDashoffset={-offset}
            >
              <title>{`${s.label}: ${s.count}`}</title>
            </circle>
          )
          offset += len
          return el
        })}
      </svg>
    </div>
  )
}

/** The completion rate as a ring, matching the last card in the mockup. */
function Ring({ percent }: { percent: number }) {
  const R = 15
  const C = 2 * Math.PI * R
  const filled = (Math.min(100, Math.max(0, percent)) / 100) * C
  return (
    <svg viewBox="0 0 40 40" className="h-10 w-10 shrink-0 -rotate-90">
      <circle cx="20" cy="20" r={R} fill="none" stroke="#EEF0F4" strokeWidth="5" />
      <circle cx="20" cy="20" r={R} fill="none" stroke="#4F46E5" strokeWidth="5"
              strokeLinecap="round" strokeDasharray={`${filled} ${C - filled}`} />
    </svg>
  )
}

function Field({
  label, children, grow,
}: {
  label: string
  children: React.ReactNode
  grow?: boolean
}) {
  // Every field gets an equal share of the strip; Search takes the slack so
  // nothing overflows into a scrollbar.
  return (
    <label className={`flex min-w-0 flex-col gap-1 ${
      grow ? 'flex-[1.4]' : 'flex-1'}`}>
      <span className={LABEL}>{label}</span>
      {children}
    </label>
  )
}

function fmt(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('en-GB',
    { day: '2-digit', month: 'short' })
}
