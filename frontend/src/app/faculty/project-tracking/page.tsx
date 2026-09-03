'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { PageShell, ResourceState } from '@/components/faculty/PageShell'
import {
  AlertsPanel,
  CohortView,
  DeliverableList,
  HealthPill,
  MilestoneTimeline,
  ProgressBar,
  TaskList,
  TeamAvatars,
  UpcomingPanel,
} from '@/components/faculty/tracking/TrackerPanels'
import { Milestones } from '@/components/faculty/tracking/Milestones'
import { TasksBlockers } from '@/components/faculty/tracking/TasksBlockers'
import {
  bulkMilestoneDate,
  exportTracker,
  fetchFacultyFilters,
  fetchTracking,
  fetchTrackerActivity,
  fetchTrackerDeliverables,
  fetchTrackerInsight,
  fetchTrackerMilestones,
  fetchTrackerTasks,
  fetchTrackingAlerts,
  fetchTrackingDetail,
  requestProgressUpdate,
} from '@/lib/faculty-api'
import type {
  ActivityRow,
  DeliverableRow,
  FacultyFilterOptions,
  MilestoneRow,
  TaskRow,
  TrackerInsight,
  TrackingAlerts,
  TrackingDetail,
  TrackingOverview,
  TrackingRow,
} from '@/lib/faculty-api'

const PHASES = [
  'All Phases', 'Topic Approval', 'Base Paper', 'Requirements', 'Design',
  'Development', 'Testing', 'Documentation', 'Final Review',
]
const HEALTHS = ['All Health', 'On Track', 'Needs Attention', 'At Risk', 'Critical']
const TABS = ['All Projects', 'My Batches', 'Milestones', 'Tasks & Blockers', 'Deliverables', 'Activity']

const CARD = 'rounded-xl border border-[#E3E6EC] bg-white p-4'
const LABEL = 'text-[10px] uppercase tracking-wider text-[#8A8FA8]'

function ProjectTrackingContent() {
  const params = useSearchParams()

  const [tab, setTab] = useState('All Projects')
  // Whichever tab is open supplies the buttons that sit beside the page title.
  const [tabActions, setTabActions] = useState<React.ReactNode>(null)

  // The dropdowns are filled from the batches that actually exist, so a
  // coordinator is never offered a section with nothing in it.
  const [options, setOptions] = useState<FacultyFilterOptions | null>(null)
  const [department, setDepartment] = useState('')
  const [year, setYear] = useState('')
  const [semester, setSemester] = useState('')
  const [section, setSection] = useState(params.get('section') ?? '')
  const [guide, setGuide] = useState('')
  const [phase, setPhase] = useState('All Phases')
  const [health, setHealth] = useState(
    params.get('attention') === '1' ? 'Critical' : 'All Health')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(params.get('batch'))

  // Ticked rows drive the bulk actions. Kept as a Set of batch codes because
  // that is what every bulk endpoint takes.
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState('')
  const [notice, setNotice] = useState('')

  // The four cohort-wide tabs, each loaded only when opened.
  const [viewRows, setViewRows] = useState<
    MilestoneRow[] | TaskRow[] | DeliverableRow[] | ActivityRow[] | null>(null)
  const [viewLoading, setViewLoading] = useState(false)
  const [insight, setInsight] = useState<TrackerInsight | null>(null)

  const [data, setData] = useState<TrackingOverview | null>(null)
  const [detail, setDetail] = useState<TrackingDetail | null>(null)
  const [alerts, setAlerts] = useState<TrackingAlerts | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const overview = await fetchTracking({
        phase: phase === 'All Phases' ? undefined : phase,
        health: health === 'All Health' ? undefined : health,
        search: search.trim() || undefined,
        department: department || undefined,
        year: year || undefined,
        semester: semester || undefined,
        section: section || undefined,
        guide_id: guide || undefined,
        mine: tab === 'My Batches',
        page,
        per_page: 10,
      })
      setData(overview)
      // Selecting the first row keeps the side panel populated rather than
      // showing an empty frame the reader has to fill by clicking.
      if (!selected && overview.rows.length) setSelected(overview.rows[0].batch_code)
    } catch (err: any) {
      setError(err?.message || 'Could not load the tracker. Please try again.')
    } finally {
      setLoading(false)
    }
  }, [phase, health, search, page, tab, department, year, semester, section, guide, selected])

  useEffect(() => { load() }, [load])
  useEffect(() => { fetchTrackingAlerts().then(setAlerts).catch(() => setAlerts(null)) }, [])
  useEffect(() => { fetchFacultyFilters().then(setOptions).catch(() => setOptions(null)) }, [])
  useEffect(() => { fetchTrackerInsight().then(setInsight).catch(() => setInsight(null)) }, [])

  // Cohort views share the dropdown filters but not phase, health or search -
  // those describe a project, and these lists are of milestones and tasks.
  const viewFilters = { department, year, semester, section, guide_id: guide }
  const isTableTab = tab === 'All Projects' || tab === 'My Batches'
  useEffect(() => {
    if (isTableTab) { setViewRows(null); return }
    let live = true
    setViewLoading(true)
    const fetcher =
      tab === 'Milestones' ? fetchTrackerMilestones
        : tab === 'Tasks & Blockers' ? fetchTrackerTasks
          : tab === 'Deliverables' ? fetchTrackerDeliverables
            : fetchTrackerActivity
    fetcher(viewFilters as never)
      .then((r: { items: unknown[] }) => { if (live) setViewRows(r.items as never) })
      .catch(() => { if (live) setViewRows([]) })
      .finally(() => { if (live) setViewLoading(false) })
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, department, year, semester, section, guide])

  useEffect(() => {
    if (!selected) { setDetail(null); return }
    let live = true
    fetchTrackingDetail(selected)
      .then((d) => { if (live) setDetail(d) })
      .catch(() => { if (live) setDetail(null) })
    return () => { live = false }
  }, [selected])

  const rows = data?.rows ?? []
  const activeFilters = [
    department, year, semester, section, guide, search.trim(),
    phase === 'All Phases' ? '' : phase,
    health === 'All Health' ? '' : health,
  ].filter(Boolean).length

  const allOnPage = rows.length > 0 && rows.every((r) => picked.has(r.batch_code))
  const toggleAll = () =>
    setPicked((prev) => {
      const next = new Set(prev)
      rows.forEach((r) => (allOnPage ? next.delete(r.batch_code) : next.add(r.batch_code)))
      return next
    })
  const toggleOne = (code: string) =>
    setPicked((prev) => {
      const next = new Set(prev)
      next.has(code) ? next.delete(code) : next.add(code)
      return next
    })

  const runBulk = async (what: 'update' | 'milestone') => {
    if (picked.size === 0) return
    setBusy(what)
    setNotice('')
    try {
      const codes = [...picked]
      const res = what === 'update'
        ? await requestProgressUpdate(codes)
        : await bulkMilestoneDate(codes, 'testing', isoInDays(14))
      setNotice(res.message)
      setPicked(new Set())
      load()
    } catch (err: any) {
      setNotice(err?.response?.data?.detail || err?.message || 'That did not work.')
    } finally {
      setBusy('')
    }
  }

  const runExport = async () => {
    setBusy('export')
    setNotice('')
    try {
      await exportTracker({
        department: department || undefined, year: year || undefined,
        semester: semester || undefined, section: section || undefined,
        guide_id: guide || undefined,
        phase: phase === 'All Phases' ? undefined : phase,
        health: health === 'All Health' ? undefined : health,
        search: search.trim() || undefined,
      })
      setNotice('Exported what is currently filtered.')
    } catch {
      setNotice('The export could not be produced.')
    } finally {
      setBusy('')
    }
  }

  return (
    <PageShell
      actions={tabActions}
      title="Project Tracking"
      subtitle={
        tab === 'Milestones'
          ? 'Plan, monitor and approve milestones across project batches'
          : tab === 'Tasks & Blockers'
            ? 'Monitor task execution, ownership, dependencies and blocker resolution'
            : 'Track every batch from approved topic to deployment'
      }
    >
      {/* header actions — each tab brings its own, so this row is only for
          the project views */}
      <div className={`flex flex-wrap items-center gap-2 ${
        (tab === 'Milestones' || tab === 'Tasks & Blockers') ? 'hidden' : ''}`}>
        <button className={btnPrimary} disabled={!!busy || picked.size === 0}
                onClick={() => runBulk('milestone')}>
          {busy === 'milestone' ? 'Working…' : 'Add Milestone'}
        </button>
        <button className={btnGhost} disabled={!!busy || picked.size === 0}
                onClick={() => runBulk('update')}>
          {busy === 'update' ? 'Working…' : 'Request Progress Update'}
        </button>
        <button className={btnGhost} disabled={!!busy} onClick={runExport}>
          {busy === 'export' ? 'Exporting…' : 'Export Tracker'}
        </button>
        {picked.size > 0 && (
          <span className="text-[12px] text-[#6B7686]">{picked.size} selected</span>
        )}
        {notice && <span className="text-[12px] text-[#4F46E5]">{notice}</span>}
      </div>

      {/* tabs */}
      <div className="flex gap-1 overflow-x-auto border-b border-[#E3E6EC]">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => { setTab(t); setPage(1); setTabActions(null) }}
            className={`whitespace-nowrap px-3 py-2 text-[13px] ${
              tab === t
                ? 'border-b-2 border-[#4F46E5] font-medium text-[#4F46E5]'
                : 'text-[#6B7686] hover:text-[#131A24]'
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* filters — hidden on Tasks & Blockers, which brings its own row for
          batch, assignee, priority, status and due date */}
      <div className={`flex flex-wrap items-end gap-3 ${
        (tab === 'Tasks & Blockers' || tab === 'Milestones') ? 'hidden' : ''}`}>
        <Field label="Department">
          <Choice value={department} onChange={setDepartment} reset={() => setPage(1)}
                  all="All Departments" items={options?.departments} />
        </Field>
        <Field label="Year">
          <Choice value={year} onChange={setYear} reset={() => setPage(1)}
                  all="All Years" items={options?.years} />
        </Field>
        <Field label="Semester">
          <Choice value={semester} onChange={setSemester} reset={() => setPage(1)}
                  all="All Semesters" items={options?.semesters} />
        </Field>
        <Field label="Section">
          <Choice value={section} onChange={setSection} reset={() => setPage(1)}
                  all="All Sections" items={options?.sections} />
        </Field>
        <Field label="Guide">
          <select
            className={selectCls}
            value={guide}
            onChange={(e) => { setGuide(e.target.value); setPage(1) }}
          >
            <option value="">All Guides</option>
            {(options?.guides ?? []).map((g) => (
              <option key={g.id} value={g.id}>{g.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Phase">
          <select className={selectCls} value={phase}
                  onChange={(e) => { setPhase(e.target.value); setPage(1) }}>
            {PHASES.map((p) => <option key={p}>{p}</option>)}
          </select>
        </Field>
        <Field label="Health">
          <select className={selectCls} value={health}
                  onChange={(e) => { setHealth(e.target.value); setPage(1) }}>
            {HEALTHS.map((h) => <option key={h}>{h}</option>)}
          </select>
        </Field>
        <Field label="Search">
          <input
            className={`${selectCls} w-64`}
            placeholder="Batch, project or guide"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') { setPage(1); load() } }}
          />
        </Field>
        {activeFilters > 0 && (
          <button
            onClick={() => {
              setDepartment(''); setYear(''); setSemester(''); setSection('')
              setGuide(''); setPhase('All Phases'); setHealth('All Health')
              setSearch(''); setPage(1)
            }}
            className="rounded-md border border-[#E3E6EC] px-2.5 py-1.5 text-[12px] text-[#6B7686] hover:border-[#4F46E5] hover:text-[#4F46E5]"
          >
            Clear {activeFilters} filter{activeFilters > 1 ? 's' : ''}
          </button>
        )}
      </div>

      {/* counters — the tasks screen has its own eight */}
      <div className={`grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 ${
        (tab === 'Tasks & Blockers' || tab === 'Milestones') ? 'hidden' : ''}`}>
        {(data?.kpis ?? []).map((k) => (
          <div key={k.id} className={CARD}>
            <p className={`${LABEL} mb-1`}>{k.label}</p>
            <p
              className={`text-2xl font-semibold ${
                k.tone === 'danger' ? 'text-[#DC2626]'
                  : k.tone === 'warn' ? 'text-[#B45309]' : 'text-[#131A24]'
              }`}
            >
              {k.value}
            </p>
          </div>
        ))}
      </div>

      {tab === 'Milestones' && (
        <Milestones
          onActions={setTabActions}
          onViewActivity={() => setTab('Activity')}
          filters={{
            department: department || undefined,
            year: year || undefined,
            semester: semester || undefined,
            section: section || undefined,
            guide_id: guide || undefined,
          }}
        />
      )}

      {tab === 'Tasks & Blockers' && (
        <TasksBlockers
          filters={{
            department: department || undefined,
            year: year || undefined,
            semester: semester || undefined,
            section: section || undefined,
            guide_id: guide || undefined,
          }}
        />
      )}

      {!isTableTab && tab !== 'Tasks & Blockers' && tab !== 'Milestones' && (
        <div className={CARD}>
          <h3 className="mb-3 text-[15px] font-semibold text-[#131A24]">{tab}</h3>
          <ResourceState
            loading={viewLoading}
            error=""
            empty={!viewRows || viewRows.length === 0}
            emptyMessage={`Nothing outstanding under ${tab.toLowerCase()}.`}
            onRetry={() => setTab(tab)}
          >
            <CohortView tab={tab} rows={viewRows ?? []} onPick={setSelected} />
          </ResourceState>
        </div>
      )}

      <div className={`grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem] ${isTableTab ? '' : 'hidden'}`}>
        {/* table */}
        <div className={`${CARD} min-w-0`}>
          <h3 className="mb-3 text-[15px] font-semibold text-[#131A24]">Project Batch Tracker</h3>
          <ResourceState
            loading={loading}
            error={error}
            empty={rows.length === 0}
            emptyMessage="No projects match this view."
            onRetry={load}
          >
            <div className="overflow-x-auto">
              <table className="w-full min-w-[56rem] text-[12px]">
                <thead>
                  <tr className={`${LABEL} text-left`}>
                    <th className="pb-2 pr-2 font-medium">
                      <input type="checkbox" checked={allOnPage} onChange={toggleAll}
                             aria-label="Select all on this page" />
                    </th>
                    <th className="pb-2 font-medium">Batch / Project</th>
                    <th className="pb-2 font-medium">Team</th>
                    <th className="pb-2 font-medium">Guide</th>
                    <th className="pb-2 font-medium">Phase</th>
                    <th className="pb-2 font-medium">Progress</th>
                    <th className="pb-2 font-medium">Milestones</th>
                    <th className="pb-2 font-medium">Tasks</th>
                    <th className="pb-2 font-medium">Deliverables</th>
                    <th className="pb-2 font-medium">Last Activity</th>
                    <th className="pb-2 font-medium">Next Due</th>
                    <th className="pb-2 font-medium">Health</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r: TrackingRow) => (
                    <tr
                      key={r.id}
                      onClick={() => setSelected(r.batch_code)}
                      className={`cursor-pointer border-t border-[#F1F2F8] hover:bg-[#FAFAFC] ${
                        selected === r.batch_code ? 'bg-[#F5F3FF]' : ''
                      }`}
                    >
                      <td className="py-2 pr-2" onClick={(e) => e.stopPropagation()}>
                        <input type="checkbox" checked={picked.has(r.batch_code)}
                               onChange={() => toggleOne(r.batch_code)}
                               aria-label={`Select ${r.batch_code}`} />
                      </td>
                      <td className="py-2 pr-3">
                        <span className="font-medium text-[#4F46E5]">{r.batch_code}</span>
                        <span className="block text-[11px] text-[#6B7686]">{r.title ?? '–'}</span>
                      </td>
                      <td className="py-2 pr-3">
                        <TeamAvatars members={r.members} activeCount={r.active_members} />
                      </td>
                      <td className="py-2 pr-3 text-[#6B7686]">
                        {r.guide_name ?? <span className="text-[#DC2626]">Not assigned</span>}
                      </td>
                      <td className="py-2 pr-3">
                        <span className="rounded border border-[#E0E7FF] bg-[#EEF2FF] px-1.5 py-0.5 text-[11px] text-[#4338CA]">
                          {r.current_phase}
                        </span>
                      </td>
                      <td className="py-2 pr-3">
                        <ProgressBar value={r.progress} expected={r.expected_progress}
                                     state={r.schedule_state} />
                      </td>
                      <td className="py-2 pr-3 text-[#6B7686]">
                        {r.milestones_done}/{r.milestones_total}
                      </td>
                      <td className="py-2 pr-3 text-[#6B7686]">
                        {r.tasks_done}/{r.tasks_total}
                        {r.overdue_tasks > 0 && (
                          <span className="ml-1 text-[10px] text-[#DC2626]">
                            {r.overdue_tasks} late
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-3 text-[#6B7686]">
                        {r.deliverables_done}/{r.deliverables_total}
                      </td>
                      <td className="py-2 pr-3 text-[#6B7686]">
                        {r.last_activity ?? 'No activity'}
                      </td>
                      <td className="py-2 pr-3 text-[#6B7686]">
                        {r.next_due?.display ?? '–'}
                      </td>
                      <td className="py-2">
                        <HealthPill health={r.health} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-3 flex items-center justify-between text-[11px] text-[#8A8FA8]">
              <span>
                Showing {rows.length} of {data?.total ?? 0} projects
              </span>
              <div className="flex items-center gap-2">
                <button
                  className={pageBtn}
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </button>
                <span>
                  {data?.page ?? 1} / {data?.pages ?? 1}
                </span>
                <button
                  className={pageBtn}
                  disabled={!!data && page >= data.pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </button>
              </div>
            </div>
          </ResourceState>
        </div>

        {/* selected project */}
        <div className={`${CARD} h-fit`}>
          {detail ? (
            <div className="flex flex-col gap-3">
              <div>
                <p className={LABEL}>Selected — {detail.batch_code}</p>
                <h3 className="text-[15px] font-semibold text-[#131A24]">
                  {detail.title ?? 'Untitled project'}
                </h3>
                <div className="mt-1 flex items-center gap-2">
                  <HealthPill health={detail.health} />
                  <span className="text-[12px] text-[#6B7686]">{detail.progress}% complete</span>
                </div>
                {detail.reasons.length > 0 && (
                  <p className="mt-1.5 text-[11px] text-[#B45309]">
                    {detail.reasons.join(' · ')}
                  </p>
                )}
              </div>

              <div>
                <p className={`${LABEL} mb-1`}>Team</p>
                <p className="text-[12px] text-[#6B7686]">
                  {detail.team.map((m) => m.name).join(', ') || 'No members yet'}
                </p>
                <p className="mt-1 text-[11px] text-[#8A8FA8]">
                  Guide: {detail.guide_name ?? 'Not assigned'}
                </p>
              </div>

              {detail.integrations.length > 0 && (
                <div>
                  <p className={`${LABEL} mb-1`}>Recorded status</p>
                  {detail.integrations.map((i) => (
                    <div key={i.kind} className="flex justify-between text-[12px]">
                      <span className="capitalize text-[#6B7686]">{i.kind}</span>
                      <span className="text-[#131A24]">
                        {i.state.replace('_', ' ')}
                        {i.detail && (
                          <span className="ml-1 text-[10px] text-[#8A8FA8]">{i.detail}</span>
                        )}
                      </span>
                    </div>
                  ))}
                  {/* Said plainly: nothing here is checked live. */}
                  <p className="mt-1 text-[10px] text-[#8A8FA8]">
                    Entered by staff, not detected automatically.
                  </p>
                </div>
              )}

              <div>
                <p className={`${LABEL} mb-1`}>Progress by workstream</p>
                {detail.workstreams.map((w) => (
                  <div key={w.stage} className="mb-1 flex items-center gap-2">
                    <span className="w-24 shrink-0 text-[11px] text-[#6B7686]">{w.label}</span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F4]">
                      <div className="h-full rounded-full bg-[#4F46E5]"
                           style={{ width: `${w.percent}%` }} />
                    </div>
                    <span className="w-9 text-right text-[10px] text-[#6B7686]">{w.percent}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[12px] text-[#8A8FA8]">Select a project to see its detail.</p>
          )}
        </div>
      </div>

      {/* lower cards */}
      <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-4">
        <div className={CARD}>
          <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Milestone Timeline</h3>
          {detail ? <MilestoneTimeline milestones={detail.milestones} />
                  : <p className="text-[12px] text-[#8A8FA8]">Select a project.</p>}
        </div>
        <div className={CARD}>
          <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Open Tasks &amp; Blockers</h3>
          {detail ? <TaskList tasks={detail.tasks} />
                  : <p className="text-[12px] text-[#8A8FA8]">Select a project.</p>}
        </div>
        <div className={CARD}>
          <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Deliverables &amp; Evidence</h3>
          {detail ? <DeliverableList deliverables={detail.deliverables} />
                  : <p className="text-[12px] text-[#8A8FA8]">Select a project.</p>}
        </div>
        <div className="flex flex-col gap-4">
          <div className={CARD}>
            <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Alerts</h3>
            <AlertsPanel data={alerts} />
          </div>
          <div className={CARD}>
            <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">Upcoming</h3>
            <UpcomingPanel data={alerts} />
          </div>
        </div>
      </div>

      {insight && (
        <div className="rounded-xl border border-[#E0E7FF] bg-[#EEF2FF] p-4">
          <p className="text-[13px] text-[#131A24]">
            <span className="font-semibold">Insight: </span>
            {insight.headline} {insight.detail}
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              className={btnPrimary}
              onClick={() => { setTab('All Projects'); setHealth('Critical'); setPage(1) }}
            >
              Review critical projects
              {insight.critical_count ? ` (${insight.critical_count})` : ''}
            </button>
            {insight.codes.length > 0 && (
              <button className={btnGhost} onClick={() => setSelected(insight.codes[0])}>
                Open {insight.codes[0]}
              </button>
            )}
          </div>
          {/* Said plainly: this is arithmetic on the table above, not a model. */}
          <p className="mt-2 text-[10px] text-[#6B7686]">
            Derived from the projects currently marked critical.
          </p>
        </div>
      )}

      {detail && detail.activity.length > 0 && (
        <div className={CARD}>
          <h3 className="mb-2 text-[14px] font-semibold text-[#131A24]">
            Recent Activity — {detail.batch_code}
          </h3>
          <div className="flex flex-col gap-1">
            {detail.activity.map((a) => (
              <div key={a.code} className="flex gap-3 text-[12px]">
                <span className="w-28 shrink-0 text-[#8A8FA8]">{a.at}</span>
                <span className="text-[#131A24]">{a.summary}</span>
                {a.actor && <span className="text-[11px] text-[#8A8FA8]">{a.actor}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </PageShell>
  )
}

const btnPrimary =
  'rounded-md bg-[#4F46E5] px-3 py-1.5 text-[13px] font-medium text-white disabled:opacity-40'
const btnGhost =
  'rounded-md border border-[#E3E6EC] px-3 py-1.5 text-[13px] text-[#131A24] disabled:opacity-40 hover:border-[#4F46E5]'

/** A date N days out, for the bulk milestone default. */
function isoInDays(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

const selectCls =
  'rounded-md border border-[#E3E6EC] bg-white px-2 py-1.5 text-[13px] text-[#131A24] outline-none focus:border-[#4F46E5]'
const pageBtn =
  'rounded-md border border-[#E3E6EC] px-2 py-1 text-[11px] text-[#6B7686] disabled:opacity-40'

/** A dropdown whose options come from the data, with an "all" first entry. */
function Choice({
  value, onChange, reset, all, items,
}: {
  value: string
  onChange: (v: string) => void
  reset: () => void
  all: string
  items?: string[]
}) {
  return (
    <select
      className={selectCls}
      value={value}
      onChange={(e) => { onChange(e.target.value); reset() }}
    >
      <option value="">{all}</option>
      {(items ?? []).map((i) => <option key={i} value={i}>{i}</option>)}
    </select>
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

/**
 * useSearchParams() opts the tree out of static rendering, and Next 14 fails
 * the production build unless that bail-out sits behind a Suspense boundary.
 */
export default function ProjectTrackingPage() {
  return (
    <Suspense
      fallback={<PageShell title="Project Tracking" subtitle="Loading…">{null}</PageShell>}
    >
      <ProjectTrackingContent />
    </Suspense>
  )
}
