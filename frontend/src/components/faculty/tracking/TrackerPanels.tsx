'use client'

import type { TrackingAlerts, TrackingDetail, TrackingRow } from '@/lib/faculty-api'

const HEALTH_TONE: Record<string, string> = {
  'On Track': 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  'At Risk': 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  'Needs Attention': 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  Critical: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
}

const PRIORITY_TONE: Record<string, string> = {
  high: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  medium: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  low: 'border-[#E2E5F0] bg-[#F7F8FC] text-[#6B7280]',
}

const MILESTONE_TONE: Record<string, string> = {
  Complete: 'text-[#15803D]',
  'In Progress': 'text-[#4F46E5]',
  Overdue: 'text-[#DC2626]',
  Upcoming: 'text-[#8A8FA8]',
}

export function HealthPill({ health }: { health: string }) {
  return (
    <span
      className={`inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] ${
        HEALTH_TONE[health] ?? HEALTH_TONE['On Track']
      }`}
    >
      {health}
    </span>
  )
}

/**
 * A percentage against what the schedule expected by today.
 *
 * The bare number was never enough on its own: 55% is healthy in month two
 * and alarming in month six, so the bar is coloured by whether the batch is
 * keeping up rather than by how large the number is.
 */
export function ProgressBar({
  value,
  expected,
  state,
}: {
  value: number
  expected?: number | null
  state?: string
}) {
  const colour =
    state === 'behind' ? '#DC2626' : state === 'ahead' ? '#15803D' : '#4F46E5'
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-baseline gap-1.5">
        <span className="text-[13px] font-medium text-[#131A24]">{value}%</span>
        {expected != null && (
          <span className="text-[10px] text-[#8A8FA8]">of {expected}%</span>
        )}
      </div>
      <div className="relative h-1.5 w-24 overflow-hidden rounded-full bg-[#EEF0F4]">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-[width]"
          style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: colour }}
        />
        {expected != null && (
          // A hairline where the batch was meant to be, so the gap is visible
          // rather than something the reader has to work out.
          <div
            className="absolute inset-y-0 w-px bg-[#6B7686]"
            style={{ left: `${Math.min(100, Math.max(0, expected))}%` }}
            title={`Expected ${expected}% by today`}
          />
        )}
      </div>
    </div>
  )
}

/** Initials rather than photographs — the portal holds no avatars. */
export function TeamAvatars({
  members,
  activeCount,
}: {
  members: { id: string; is_active: boolean }[]
  activeCount: number
}) {
  const shown = members.slice(0, 4)
  return (
    <div className="flex items-center gap-1">
      <div className="flex -space-x-1.5">
        {shown.map((m, i) => (
          <span
            key={m.id}
            className={`inline-flex h-6 w-6 items-center justify-center rounded-full border-2 border-white text-[10px] font-medium ${
              m.is_active ? 'bg-[#E0E7FF] text-[#4338CA]' : 'bg-[#F1F2F8] text-[#9AA1B1]'
            }`}
            title={m.is_active ? 'Active' : 'Inactive'}
          >
            {i + 1}
          </span>
        ))}
      </div>
      <span className="text-[11px] text-[#8A8FA8]">
        {activeCount === members.length
          ? `${members.length} members`
          : `${activeCount}/${members.length} members`}
      </span>
    </div>
  )
}

export function MilestoneTimeline({ milestones }: { milestones: TrackingDetail['milestones'] }) {
  return (
    <table className="w-full text-[12px]">
      <thead>
        <tr className="text-left text-[10px] uppercase tracking-wider text-[#8A8FA8]">
          <th className="pb-2 font-medium">Milestone</th>
          <th className="pb-2 font-medium">Planned</th>
          <th className="pb-2 font-medium">Actual</th>
          <th className="pb-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {milestones.map((m) => (
          <tr key={m.stage} className="border-t border-[#F1F2F8]">
            <td className="py-1.5 text-[#131A24]">{m.label}</td>
            <td className="py-1.5 text-[#6B7686]">{fmt(m.planned)}</td>
            <td className="py-1.5 text-[#6B7686]">{fmt(m.actual) || '–'}</td>
            <td className={`py-1.5 ${MILESTONE_TONE[m.status] ?? ''}`}>{m.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function TaskList({ tasks }: { tasks: TrackingDetail['tasks'] }) {
  const blocked = tasks.filter((t) => t.blocked_reason)
  const open = tasks.filter((t) => t.status !== 'done')
  return (
    <div className="flex flex-col gap-2">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wider text-[#8A8FA8]">
            <th className="pb-2 font-medium">Task</th>
            <th className="pb-2 font-medium">Assignee</th>
            <th className="pb-2 font-medium">Priority</th>
            <th className="pb-2 font-medium">Due</th>
          </tr>
        </thead>
        <tbody>
          {open.slice(0, 6).map((t) => (
            <tr key={t.id} className="border-t border-[#F1F2F8]">
              <td className="py-1.5 text-[#131A24]">{t.title}</td>
              <td className="py-1.5 text-[#6B7686]">{t.assignee ?? 'Unassigned'}</td>
              <td className="py-1.5">
                <span
                  className={`inline-block rounded border px-1.5 py-0.5 text-[10px] ${
                    t.status === 'blocked'
                      ? PRIORITY_TONE.high
                      : PRIORITY_TONE[t.priority] ?? PRIORITY_TONE.low
                  }`}
                >
                  {t.status === 'blocked' ? 'Blocked' : t.priority}
                </span>
              </td>
              <td className={`py-1.5 ${t.overdue ? 'text-[#DC2626]' : 'text-[#6B7686]'}`}>
                {t.due_display ?? '–'}
              </td>
            </tr>
          ))}
          {open.length === 0 && (
            <tr>
              <td colSpan={4} className="py-3 text-center text-[#8A8FA8]">
                No open tasks.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {blocked.map((t) => (
        <p
          key={t.id}
          className="rounded-md border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11px] text-[#DC2626]"
        >
          {t.blocked_reason}
        </p>
      ))}
    </div>
  )
}

export function DeliverableList({
  deliverables,
}: {
  deliverables: TrackingDetail['deliverables']
}) {
  return (
    <table className="w-full text-[12px]">
      <thead>
        <tr className="text-left text-[10px] uppercase tracking-wider text-[#8A8FA8]">
          <th className="pb-2 font-medium">Item</th>
          <th className="pb-2 font-medium">Progress</th>
          <th className="pb-2 font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {deliverables.map((d) => (
          <tr key={d.id} className="border-t border-[#F1F2F8]">
            <td className="py-1.5 text-[#131A24]">{d.name}</td>
            <td className="py-1.5">
              <div className="flex items-center gap-2">
                <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#EEF0F4]">
                  <div
                    className="h-full rounded-full bg-[#4F46E5]"
                    style={{ width: `${d.progress}%` }}
                  />
                </div>
                <span className="text-[10px] text-[#6B7686]">{d.progress}%</span>
              </div>
            </td>
            <td className="py-1.5 capitalize text-[#6B7686]">{d.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function AlertsPanel({ data }: { data: TrackingAlerts | null }) {
  if (!data) return null
  return (
    <div className="flex flex-col gap-2">
      {data.alerts.map((a) => (
        <div key={a.id} className="flex items-center gap-2 text-[12px]">
          <span
            className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-semibold ${
              a.tone === 'danger'
                ? 'bg-[#FEF2F2] text-[#DC2626]'
                : a.tone === 'warn'
                  ? 'bg-[#FFFBEB] text-[#B45309]'
                  : 'bg-[#F7F8FC] text-[#6B7280]'
            }`}
          >
            {a.count}
          </span>
          <span className="text-[#6B7686]">{a.label}</span>
        </div>
      ))}
    </div>
  )
}

export function UpcomingPanel({ data }: { data: TrackingAlerts | null }) {
  if (!data || data.upcoming.length === 0) {
    return <p className="text-[12px] text-[#8A8FA8]">Nothing scheduled.</p>
  }
  return (
    <div className="flex flex-col gap-1.5">
      {data.upcoming.map((u) => (
        <div key={`${u.batch_code}-${u.date}`} className="flex items-center gap-2 text-[12px]">
          <span className="w-14 shrink-0 text-[#8A8FA8]">{u.display}</span>
          <span className="flex-1 truncate text-[#131A24]">{u.label}</span>
          <span className="text-[11px] text-[#6B7686]">{u.batch_code}</span>
          <HealthPill health={u.health} />
        </div>
      ))}
    </div>
  )
}

export function rowSummary(row: TrackingRow): string {
  return row.reasons.length ? row.reasons.join(' · ') : 'No open problems.'
}

function fmt(iso: string | null): string {
  if (!iso) return ''
  // Date-only strings are parsed as UTC by the Date constructor, which shifts
  // them a day backwards east of Greenwich. Split the parts instead.
  const [y, m, d] = iso.split('-').map(Number)
  if (!y || !m || !d) return iso
  return new Date(y, m - 1, d).toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
  })
}

/**
 * The four cohort-wide tabs.
 *
 * Same rows as the table, regrouped by the thing rather than by the batch:
 * a coordinator chasing overdue milestones wants every overdue milestone,
 * not to open forty-five projects and find them one at a time.
 */
export function CohortView({
  tab,
  rows,
  onPick,
}: {
  tab: string
  rows: any[]
  onPick: (batchCode: string) => void
}) {
  const head =
    tab === 'Milestones' ? ['Project', 'Milestone', 'Planned', 'Progress', 'Status']
      : tab === 'Tasks & Blockers' ? ['Project', 'Task', 'Assignee', 'Priority', 'Due', 'Status']
        : tab === 'Deliverables' ? ['Project', 'Item', 'Progress', 'Status']
          : ['When', 'Project', 'Activity', 'By']

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[44rem] text-[12px]">
        <thead>
          <tr className="text-left text-[10px] uppercase tracking-wider text-[#8A8FA8]">
            {head.map((h) => <th key={h} className="pb-2 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr
              key={r.id ?? r.code ?? `${r.batch_code}-${r.label ?? r.name ?? i}`}
              className="cursor-pointer border-t border-[#F1F2F8] hover:bg-[#FAFAFC]"
              onClick={() => onPick(r.batch_code)}
            >
              {tab === 'Milestones' && (
                <>
                  <Project row={r} />
                  <td className="py-1.5 text-[#131A24]">{r.label}</td>
                  <td className="py-1.5 text-[#6B7686]">{fmt(r.planned) || '–'}</td>
                  <td className="py-1.5 text-[#6B7686]">{r.percent}%</td>
                  <td className={`py-1.5 ${MILESTONE_TONE[r.status] ?? ''}`}>{r.status}</td>
                </>
              )}
              {tab === 'Tasks & Blockers' && (
                <>
                  <Project row={r} />
                  <td className="py-1.5 text-[#131A24]">
                    {r.title ?? '—'}
                    {r.blocked_reason && (
                      <span className="block text-[10px] text-[#DC2626]">{r.blocked_reason}</span>
                    )}
                  </td>
                  <td className="py-1.5 text-[#6B7686]">{r.assignee ?? 'Unassigned'}</td>
                  <td className="py-1.5">
                    <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] ${
                      PRIORITY_TONE[r.priority] ?? PRIORITY_TONE.low}`}>
                      {r.priority}
                    </span>
                  </td>
                  <td className={`py-1.5 ${r.overdue ? 'text-[#DC2626]' : 'text-[#6B7686]'}`}>
                    {r.due_display ?? '–'}
                  </td>
                  <td className="py-1.5 capitalize text-[#6B7686]">
                    {String(r.status).replace('_', ' ')}
                  </td>
                </>
              )}
              {tab === 'Deliverables' && (
                <>
                  <Project row={r} />
                  <td className="py-1.5 text-[#131A24]">{r.name}</td>
                  <td className="py-1.5">
                    <div className="flex items-center gap-2">
                      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-[#EEF0F4]">
                        <div className="h-full rounded-full bg-[#4F46E5]"
                             style={{ width: `${r.progress}%` }} />
                      </div>
                      <span className="text-[10px] text-[#6B7686]">{r.progress}%</span>
                    </div>
                  </td>
                  <td className="py-1.5 capitalize text-[#6B7686]">{r.status}</td>
                </>
              )}
              {tab === 'Activity' && (
                <>
                  <td className="py-1.5 whitespace-nowrap text-[#8A8FA8]">{r.at}</td>
                  <td className="py-1.5 font-medium text-[#4F46E5]">{r.batch_code}</td>
                  <td className="py-1.5 text-[#131A24]">{r.summary}</td>
                  <td className="py-1.5 text-[#6B7686]">{r.actor ?? 'System'}</td>
                </>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-[11px] text-[#8A8FA8]">{rows.length} row(s)</p>
    </div>
  )
}

function Project({ row }: { row: any }) {
  // Task rows carry the project name separately, because `title` there is
  // the task's own.
  const project = row.project_title ?? row.title
  return (
    <td className="py-1.5 pr-3">
      <span className="font-medium text-[#4F46E5]">{row.batch_code}</span>
      {project && <span className="block text-[10px] text-[#8A8FA8]">{project}</span>}
    </td>
  )
}
