'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { ResourceState } from '@/components/faculty/PageShell'
import {
  assignBlocker,
  bulkEditTasks,
  escalateBlocker,
  exportTasks,
  fetchBlockers,
  fetchTaskBoard,
  fetchTaskInsight,
  fetchTaskWorkload,
  resolveBlocker,
} from '@/lib/faculty-api'
import type {
  BlockerData,
  BlockerRow,
  TaskBoardData,
  TaskBoardQuery,
  TaskCard,
  TaskInsight,
  WorkloadData,
} from '@/lib/faculty-api'

const CARD = 'rounded-xl border border-[#E3E6EC] bg-white p-4'
const LABEL = 'text-[10px] uppercase tracking-wider text-[#8A8FA8]'
const BTN = 'rounded-md border border-[#E3E6EC] px-2.5 py-1.5 text-[12px] text-[#131A24] disabled:opacity-40 hover:border-[#4F46E5]'
const BTN_PRIMARY = 'rounded-md bg-[#4F46E5] px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-40'
const SELECT = 'rounded-md border border-[#E3E6EC] bg-white px-2 py-1.5 text-[13px] text-[#131A24] outline-none focus:border-[#4F46E5]'

const PRIORITY_TONE: Record<string, string> = {
  high: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  medium: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  low: 'border-[#E2E5F0] bg-[#F7F8FC] text-[#6B7280]',
}

const SEVERITY_TONE: Record<string, string> = {
  critical: 'text-[#DC2626]',
  high: 'text-[#B45309]',
  medium: 'text-[#6B7686]',
  low: 'text-[#8A8FA8]',
}

const COLUMN_TINT: Record<string, string> = {
  open: 'bg-[#FAFAFC]',
  in_progress: 'bg-[#F5F7FF]',
  blocked: 'bg-[#FEF6F6]',
  done: 'bg-[#F6FBF7]',
}

export function TasksBlockers({ filters }: { filters: TaskBoardQuery }) {
  const [view, setView] = useState<'Board' | 'List' | 'Workload'>('Board')
  const [board, setBoard] = useState<TaskBoardData | null>(null)
  const [blockers, setBlockers] = useState<BlockerData | null>(null)
  const [workload, setWorkload] = useState<WorkloadData | null>(null)
  const [insight, setInsight] = useState<TaskInsight | null>(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')

  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [openBlocker, setOpenBlocker] = useState<BlockerRow | null>(null)

  // This screen filters by task, not by project, so it owns its own controls.
  // Batch is the one a coordinator reaches for most - "show me this team's
  // work" is the whole reason to open it.
  const [branch, setBranch] = useState('')
  const [section, setSection] = useState('')
  const [batch, setBatch] = useState('')
  const [assignee, setAssignee] = useState('')
  const [priority, setPriority] = useState('')
  const [taskStatus, setTaskStatus] = useState('')
  const [due, setDue] = useState('')

  const query: TaskBoardQuery = {
    ...filters,
    department: branch || filters.department,
    section: section || filters.section,
    batch_code: batch || undefined,
    assignee_id: assignee || undefined,
    priority: priority || undefined,
    status: taskStatus || undefined,
    due: due || undefined,
  }
  const key = JSON.stringify(query)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      // The blocker queue and workload follow the same batch, so filtering to
      // one team narrows every panel rather than only the board.
      const scope = {
        ...filters,
        department: branch || filters.department,
        section: section || filters.section,
        batch_code: batch || undefined,
      }
      const [b, k, w] = await Promise.all([
        fetchTaskBoard(query),
        fetchBlockers(scope),
        fetchTaskWorkload(scope),
      ])
      setBoard(b)
      setBlockers(k)
      setWorkload(w)
      setOpenBlocker((prev) =>
        prev ? k.queue.find((q) => q.id === prev.id) ?? k.queue[0] ?? null : k.queue[0] ?? null)
    } catch (err: any) {
      setError(err?.message || 'Could not load tasks. Please try again.')
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])

  useEffect(() => { load() }, [load])
  useEffect(() => { fetchTaskInsight().then(setInsight).catch(() => setInsight(null)) }, [key])

  const rows = board?.rows ?? []
  const staff = useMemo(
    () => Array.from(new Set((blockers?.queue ?? [])
      .map((q) => q.owner).filter(Boolean) as string[])),
    [blockers])

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

  // Cascade: each level offers only what exists under the one above it, so a
  // coordinator is never shown a section with no batches in it.
  const catalogue = board?.options.catalogue ?? []
  const sections = Array.from(new Set(
    catalogue.filter((c) => !branch || c.department === branch)
      .map((c) => c.section).filter(Boolean) as string[])).sort()
  const inScope = catalogue.filter(
    (c) => (!branch || c.department === branch) && (!section || c.section === section))

  const activeFilters = [branch, section, batch, assignee, priority, taskStatus, due]
    .filter(Boolean).length

  const bulk = (changes: Record<string, unknown>, label: string) =>
    act(label, () => bulkEditTasks([...picked], changes))

  return (
    <div className="flex flex-col gap-4">
      {/* header actions */}
      <div className="flex flex-wrap items-center gap-2">
        <button className={BTN_PRIMARY} disabled={!!busy || picked.size === 0}
                onClick={() => bulk({ status: 'done' }, 'complete')}>
          {busy === 'complete' ? 'Working…' : 'Complete Tasks'}
        </button>
        <button className={BTN} disabled={!!busy || picked.size === 0}
                onClick={() => bulk({ priority: 'high' }, 'priority')}>
          Change Priority
        </button>
        <button className={BTN} disabled={!!busy || picked.size === 0}
                onClick={() => bulk({ due_date: isoInDays(7) }, 'due')}>
          Change Due Date
        </button>
        <button className={BTN} disabled={!!busy}
                onClick={() => act('export', async () => {
                  await exportTasks(filters)
                  return { message: 'Exported what is currently filtered.' }
                })}>
          {busy === 'export' ? 'Exporting…' : 'Export Tasks'}
        </button>
        {picked.size > 0 && (
          <span className="text-[12px] text-[#6B7686]">{picked.size} selected</span>
        )}
        {notice && <span className="text-[12px] text-[#4F46E5]">{notice}</span>}
      </div>

      {/* filters — branch narrows section, section narrows batch, and the
          team dropdown is the same list said the way staff say it out loud */}
      <div className="flex flex-wrap items-end gap-3">
        <Field label="Branch">
          <select className={SELECT} value={branch}
                  onChange={(e) => { setBranch(e.target.value); setSection(''); setBatch('') }}>
            <option value="">All Branches</option>
            {(board?.options.departments ?? []).map((d) => <option key={d}>{d}</option>)}
          </select>
        </Field>
        <Field label="Section">
          <select className={SELECT} value={section}
                  onChange={(e) => { setSection(e.target.value); setBatch('') }}>
            <option value="">All Sections</option>
            {sections.map((v) => <option key={v}>{v}</option>)}
          </select>
        </Field>
        <Field label="Batch / Team">
          {/* One control, not two. The batch code and the team number are the
              same thing said differently - CSE-B-003 is team 3 - so a separate
              Team dropdown was a second way to set a value already set. */}
          <select className={SELECT} value={batch}
                  onChange={(e) => setBatch(e.target.value)}>
            <option value="">All Batches</option>
            {inScope.map((c) => (
              <option key={c.code} value={c.code}>
                {c.team ? `${c.code} · ${c.team_label}` : c.code}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Assignee">
          <select className={SELECT} value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}>
            <option value="">All Students</option>
            {(board?.options.assignees ?? []).map((a) => (
              <option key={a.id} value={a.id}>
                {a.name}
                {/* A member with nothing assigned, or one who has left the
                    team, is the reason to open this list at all. */}
                {!a.is_active ? ' — inactive' : !a.has_tasks ? ' — no tasks' : ''}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Priority">
          <select className={SELECT} value={priority}
                  onChange={(e) => setPriority(e.target.value)}>
            <option value="">All Priorities</option>
            {(board?.options.priorities ?? []).map((p) => (
              <option key={p} value={p} className="capitalize">{p}</option>
            ))}
          </select>
        </Field>
        <Field label="Status">
          <select className={SELECT} value={taskStatus}
                  onChange={(e) => setTaskStatus(e.target.value)}>
            <option value="">All Statuses</option>
            {(board?.options.statuses ?? []).map((v) => (
              <option key={v} value={v}>{v.replace('_', ' ')}</option>
            ))}
          </select>
        </Field>
        <Field label="Due date">
          <select className={SELECT} value={due} onChange={(e) => setDue(e.target.value)}>
            <option value="">All Dates</option>
            <option value="overdue">Overdue</option>
            <option value="today">Due today</option>
            <option value="week">Due this week</option>
          </select>
        </Field>
        {activeFilters > 0 && (
          <button
            className={BTN}
            onClick={() => {
              setBranch(''); setSection(''); setBatch(''); setAssignee(''); setPriority('')
              setTaskStatus(''); setDue('')
            }}
          >
            Clear {activeFilters} filter{activeFilters > 1 ? 's' : ''}
          </button>
        )}
      </div>

      {/* counters */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        {(board?.kpis ?? []).map((k) => (
          <div key={k.id} className={CARD}>
            <p className={`${LABEL} mb-1`}>{k.label}</p>
            <p className={`text-xl font-semibold ${
              k.tone === 'danger' ? 'text-[#DC2626]'
                : k.tone === 'warn' ? 'text-[#B45309]' : 'text-[#131A24]'}`}>
              {k.value}
            </p>
          </div>
        ))}
      </div>

      <ResourceState loading={loading} error={error} empty={false} onRetry={load}>
        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_21rem]">
          <div className="flex min-w-0 flex-col gap-4">
            {/* board / list / workload */}
            <div className={CARD}>
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-[15px] font-semibold text-[#131A24]">Task Board</h3>
                <div className="flex gap-1">
                  {(['Board', 'List', 'Workload'] as const).map((v) => (
                    <button key={v} onClick={() => setView(v)}
                            className={`rounded-md px-2.5 py-1 text-[12px] ${
                              view === v
                                ? 'bg-[#4F46E5] text-white'
                                : 'border border-[#E3E6EC] text-[#6B7686]'}`}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {view === 'Board' && (
                <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {(board?.columns ?? []).map((col) => (
                    <div key={col.status}
                         className={`rounded-lg p-2 ${COLUMN_TINT[col.status] ?? ''}`}>
                      <p className="mb-2 text-[12px] font-medium text-[#131A24]">
                        {col.label} <span className="text-[#8A8FA8]">({col.count})</span>
                      </p>
                      <div className="flex flex-col gap-2">
                        {col.cards.slice(0, 6).map((c) => <Card key={c.id} card={c} />)}
                        {col.count > 6 && (
                          <p className="px-1 text-[11px] text-[#8A8FA8]">
                            +{col.count - 6} more
                          </p>
                        )}
                        {col.count === 0 && (
                          <p className="px-1 text-[11px] text-[#8A8FA8]">Nothing here.</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {view === 'List' && (
                <Register rows={rows} picked={picked} setPicked={setPicked} />
              )}

              {view === 'Workload' && <Workload data={workload} />}
            </div>
          </div>

          {/* right rail */}
          <div className="flex flex-col gap-4">
            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">
                Blocker Resolution Queue
              </h3>
              {(blockers?.queue ?? []).length === 0 ? (
                <p className="text-[12px] text-[#8A8FA8]">Nothing is blocked.</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  {(blockers?.queue ?? []).slice(0, 6).map((q) => (
                    <button key={q.id} onClick={() => setOpenBlocker(q)}
                            className={`flex items-center gap-2 rounded-md px-1.5 py-1 text-left text-[12px] hover:bg-[#FAFAFC] ${
                              openBlocker?.id === q.id ? 'bg-[#F5F3FF]' : ''}`}>
                      <span className={`w-14 shrink-0 text-[10px] uppercase ${
                        SEVERITY_TONE[q.severity] ?? ''}`}>{q.severity}</span>
                      <span className="flex-1 truncate text-[#131A24]">{q.title}</span>
                      <span className="text-[10px] text-[#8A8FA8]">{q.batch_code}</span>
                      <span className="w-10 text-right text-[10px] text-[#6B7686]">
                        {q.age_days}d
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Blocker Analysis</h3>
              <Bars rows={blockers?.analysis ?? []} />
            </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">SLA &amp; Aging</h3>
              {blockers?.sla.resolved ? (
                <>
                  {blockers.sla.bands.map((b) => (
                    <div key={b.label} className="mb-1 flex items-center gap-2 text-[12px]">
                      <span className="w-20 shrink-0 text-[#6B7686]">{b.label}</span>
                      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F4]">
                        <div className="h-full rounded-full bg-[#4F46E5]"
                             style={{ width: `${b.percent}%` }} />
                      </div>
                      <span className="w-9 text-right text-[10px] text-[#6B7686]">
                        {b.percent}%
                      </span>
                    </div>
                  ))}
                  <p className="mt-2 text-[12px] text-[#131A24]">
                    Average resolution{' '}
                    <span className="font-semibold">{blockers.sla.average_days} days</span>
                    <span className="text-[10px] text-[#8A8FA8]">
                      {' '}across {blockers.sla.resolved} resolved
                    </span>
                  </p>
                </>
              ) : (
                <p className="text-[12px] text-[#8A8FA8]">
                  Nothing resolved yet, so there is no timing to report.
                </p>
              )}
            </div>

            <div className={CARD}>
              <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Overdue by Batch</h3>
              <Bars rows={(workload?.overdue_by_batch ?? []).map((o) => ({
                label: o.batch_code, count: o.count }))} tone="#DC2626" />
            </div>
          </div>
        </div>
      </ResourceState>

      {/* selected blocker */}
      {openBlocker && (
        <div className={CARD}>
          <div className="flex flex-wrap items-baseline gap-2">
            <h3 className="text-[15px] font-semibold text-[#131A24]">
              Selected Blocker — {openBlocker.title}
            </h3>
            <span className="text-[12px] text-[#6B7686]">{openBlocker.batch_code}</span>
            <span className={`text-[11px] uppercase ${SEVERITY_TONE[openBlocker.severity]}`}>
              {openBlocker.severity}
            </span>
            <span className="text-[11px] text-[#8A8FA8]">
              {openBlocker.status} · {openBlocker.age_days} days old
            </span>
          </div>

          <div className="mt-2 grid gap-3 text-[12px] md:grid-cols-3">
            <Detail label="Reported by"
                    value={`${openBlocker.reported_by ?? 'Unknown'} · ${openBlocker.reported_at ?? ''}`} />
            <Detail label="Root cause" value={openBlocker.root_cause ?? '—'} />
            <Detail label="Impact" value={openBlocker.impact ?? '—'} />
            <Detail label="Resolution owner" value={openBlocker.owner ?? 'Not assigned'} />
            <Detail label="Target resolution" value={openBlocker.target_resolution ?? 'None set'} />
            <Detail label="Category" value={openBlocker.category_label} />
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            <button
              className={BTN_PRIMARY}
              disabled={!!busy}
              onClick={() => {
                const note = window.prompt('How was it resolved?')
                if (note && note.trim()) {
                  act('resolve', () => resolveBlocker(openBlocker.id, note.trim()))
                }
              }}
            >
              Resolve Blocker
            </button>
            <button
              className={BTN}
              disabled={!!busy || openBlocker.status === 'escalated'}
              onClick={() => act('escalate', () => escalateBlocker(openBlocker.id, ''))}
            >
              Escalate
            </button>
            {!openBlocker.owner_id && staff.length > 0 && (
              <span className="self-center text-[11px] text-[#B45309]">
                Assign an owner before escalating.
              </span>
            )}
          </div>
        </div>
      )}

      {insight && (
        <div className="rounded-xl border border-[#E0E7FF] bg-[#EEF2FF] p-4">
          <p className="text-[13px] text-[#131A24]">
            <span className="font-semibold">Insight: </span>
            {insight.headline} {insight.detail}
          </p>
          <p className="mt-2 text-[10px] text-[#6B7686]">
            Counted from the open blockers and the tasks that depend on them.
          </p>
        </div>
      )}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1">
      <span className={LABEL}>{label}</span>
      {children}
    </label>
  )
}

function Card({ card }: { card: TaskCard }) {
  return (
    <div className="rounded-md border border-[#E3E6EC] bg-white p-2">
      <p className="text-[12px] font-medium text-[#131A24]">{card.title}</p>
      <p className="text-[10px] text-[#4F46E5]">
        {card.batch_code}
        <span className="ml-1 text-[#8A8FA8]">{card.project_title}</span>
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        <span className={`rounded border px-1.5 py-0.5 text-[10px] ${
          PRIORITY_TONE[card.priority] ?? PRIORITY_TONE.low}`}>
          {card.priority}
        </span>
        {card.progress > 0 && card.status !== 'done' && (
          <span className="text-[10px] text-[#6B7686]">{card.progress}%</span>
        )}
        <span className={`text-[10px] ${card.overdue ? 'text-[#DC2626]' : 'text-[#8A8FA8]'}`}>
          {card.due_display ?? 'No date'}
        </span>
      </div>
      {card.blocked_reason && (
        <p className="mt-1 text-[10px] text-[#DC2626]">{card.blocked_reason}</p>
      )}
      <div className="mt-1.5 flex items-center gap-2 text-[10px] text-[#8A8FA8]">
        <span>{card.assignee ?? 'Unassigned'}</span>
        {card.comments > 0 && <span>💬 {card.comments}</span>}
        {card.dependencies > 0 && <span>⛓ {card.dependencies}</span>}
        {card.stage && (
          <span className="ml-auto rounded bg-[#F1F2F8] px-1 py-0.5 text-[9px] text-[#6B7686]">
            {card.stage}
          </span>
        )}
      </div>
    </div>
  )
}

function Register({
  rows, picked, setPicked,
}: {
  rows: TaskCard[]
  picked: Set<string>
  setPicked: (s: Set<string>) => void
}) {
  const allOn = rows.length > 0 && rows.every((r) => picked.has(r.id))
  const toggleAll = () => {
    const next = new Set(picked)
    rows.forEach((r) => (allOn ? next.delete(r.id) : next.add(r.id)))
    setPicked(next)
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[52rem] text-[12px]">
        <thead>
          <tr className={`${LABEL} text-left`}>
            <th className="pb-2 pr-2">
              <input type="checkbox" checked={allOn} onChange={toggleAll}
                     aria-label="Select all tasks" />
            </th>
            <th className="pb-2 font-medium">Priority</th>
            <th className="pb-2 font-medium">Task</th>
            <th className="pb-2 font-medium">Batch / Project</th>
            <th className="pb-2 font-medium">Assignee</th>
            <th className="pb-2 font-medium">Milestone</th>
            <th className="pb-2 font-medium">Created</th>
            <th className="pb-2 font-medium">Due</th>
            <th className="pb-2 font-medium">Age</th>
            <th className="pb-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 40).map((r) => (
            <tr key={r.id} className="border-t border-[#F1F2F8]">
              <td className="py-1.5 pr-2">
                <input
                  type="checkbox"
                  checked={picked.has(r.id)}
                  onChange={() => {
                    const next = new Set(picked)
                    next.has(r.id) ? next.delete(r.id) : next.add(r.id)
                    setPicked(next)
                  }}
                  aria-label={`Select ${r.title}`}
                />
              </td>
              <td className="py-1.5">
                <span className={`rounded border px-1.5 py-0.5 text-[10px] ${
                  PRIORITY_TONE[r.priority] ?? PRIORITY_TONE.low}`}>{r.priority}</span>
              </td>
              <td className="py-1.5 text-[#131A24]">
                {r.title}
                {r.blocked_reason && (
                  <span className="block text-[10px] text-[#DC2626]">{r.blocked_reason}</span>
                )}
              </td>
              <td className="py-1.5">
                <span className="font-medium text-[#4F46E5]">{r.batch_code}</span>
                <span className="block text-[10px] text-[#8A8FA8]">{r.project_title}</span>
              </td>
              <td className="py-1.5 text-[#6B7686]">{r.assignee ?? 'Unassigned'}</td>
              <td className="py-1.5 text-[#6B7686]">{r.stage ?? '—'}</td>
              <td className="py-1.5 text-[#6B7686]">{r.created_display ?? '—'}</td>
              <td className={`py-1.5 ${r.overdue ? 'text-[#DC2626]' : 'text-[#6B7686]'}`}>
                {r.due_display ?? '—'}
              </td>
              <td className="py-1.5 text-[#6B7686]">{r.age_days}d</td>
              <td className="py-1.5 capitalize text-[#6B7686]">
                {r.status.replace('_', ' ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-[#8A8FA8]">
        Showing {Math.min(40, rows.length)} of {rows.length} tasks
      </p>
    </div>
  )
}

function Workload({ data }: { data: WorkloadData | null }) {
  if (!data || data.students.length === 0) {
    return <p className="text-[12px] text-[#8A8FA8]">No work is assigned yet.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[36rem] text-[12px]">
        <thead>
          <tr className={`${LABEL} text-left`}>
            <th className="pb-2 font-medium">Student</th>
            <th className="pb-2 font-medium">Open</th>
            <th className="pb-2 font-medium">Overdue / Blocked</th>
            <th className="pb-2 font-medium">Done</th>
            <th className="pb-2 font-medium">Load</th>
          </tr>
        </thead>
        <tbody>
          {data.students.slice(0, 12).map((s) => (
            <tr key={s.id} className="border-t border-[#F1F2F8]">
              <td className="py-1.5 text-[#131A24]">{s.name}</td>
              <td className="py-1.5 text-[#6B7686]">{s.tasks}</td>
              <td className="py-1.5">
                {s.overdue > 0 && <span className="text-[#DC2626]">{s.overdue} overdue</span>}
                {s.overdue > 0 && s.blocked > 0 && <span className="text-[#8A8FA8]"> · </span>}
                {s.blocked > 0 && <span className="text-[#B45309]">{s.blocked} blocked</span>}
                {s.overdue === 0 && s.blocked === 0 && <span className="text-[#8A8FA8]">—</span>}
              </td>
              <td className="py-1.5 text-[#6B7686]">{s.done}</td>
              <td className="py-1.5">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#EEF0F4]">
                    <div className="h-full rounded-full"
                         style={{
                           width: `${Math.min(100, s.load_percent)}%`,
                           background: s.load_percent > 100 ? '#DC2626'
                             : s.load_percent > 75 ? '#B45309' : '#15803D',
                         }} />
                  </div>
                  <span className="text-[10px] text-[#6B7686]">{s.load_percent}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* The yardstick is stated, because a percentage with no denominator
          invites the reader to invent one. */}
      <p className="mt-2 text-[11px] text-[#8A8FA8]">
        Load is open tasks against a normal load of {data.normal_load}.
      </p>
    </div>
  )
}

function Bars({ rows, tone = '#4F46E5' }: {
  rows: { label: string; count: number }[]
  tone?: string
}) {
  if (rows.length === 0) return <p className="text-[12px] text-[#8A8FA8]">Nothing to show.</p>
  const max = Math.max(...rows.map((r) => r.count), 1)
  return (
    <div className="flex flex-col gap-1">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-2 text-[12px]">
          <span className="w-28 shrink-0 truncate text-[#6B7686]">{r.label}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F4]">
            <div className="h-full rounded-full"
                 style={{ width: `${(r.count / max) * 100}%`, background: tone }} />
          </div>
          <span className="w-6 text-right text-[10px] text-[#6B7686]">{r.count}</span>
        </div>
      ))}
    </div>
  )
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className={LABEL}>{label}</p>
      <p className="text-[#131A24]">{value}</p>
    </div>
  )
}

function isoInDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}
