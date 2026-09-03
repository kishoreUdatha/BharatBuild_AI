'use client'

/**
 * Sprints for one batch.
 *
 * Every figure on a sprint is a roll-up of the stories scheduled into it, so
 * the only things editable here are the sprint's own facts - its name, its
 * dates, its goal and whether it is running. Progress is not typed in; it
 * follows the backlog.
 *
 * The planning act this screen exists for is scheduling: tick stories, choose
 * a sprint, move them. Unscheduled work sits at the bottom for exactly that.
 */

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  AlertTriangle, ArrowLeft, CalendarClock, CalendarRange, CheckCircle2,
  ChevronDown, ChevronRight, Circle, Clock, Pencil, Plus, X,
} from 'lucide-react'
import { CARD, Failed, Loading } from '@/components/trainer/primitives'
import {
  AssigneeChip, BTN_OUTLINE, BTN_PRIMARY, FIELD, fmtDay,
} from '@/components/trainer/user-stories/bits'
import { AddSprintDialog } from '@/components/trainer/user-stories/dialogs'
import {
  addSprint, errorText, fetchSprints, patchSprint, scheduleStories,
} from '@/lib/trainer-api'
import type {
  NewSprintInput, SprintBoard, SprintRollUp, SprintRow, SprintStoryLine,
} from '@/lib/trainer-api'
import { BurndownChart } from '@/components/trainer/Burndown'
import { cn } from '@/lib/utils'

const KPI_ICON: Record<string, typeof CalendarRange> = {
  sprints: CalendarRange, active: Clock, planned: Circle,
  completed: CheckCircle2, scheduled: CheckCircle2, unscheduled: AlertTriangle,
}

const KPI_TONE: Record<string, string> = {
  sprints: 'bg-[#EFF6FF] text-[#2563EB]',
  active: 'bg-[#FFF7ED] text-[#EA580C]',
  planned: 'bg-[#F4F5FA] text-[#6B7280]',
  completed: 'bg-[#F0FDF4] text-[#16A34A]',
  scheduled: 'bg-[#EFF6FF] text-[#2563EB]',
  unscheduled: 'bg-[#FEF2F2] text-[#DC2626]',
}

const STATE_TONE: Record<string, string> = {
  planned: 'border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280]',
  active: 'border-[#BFDBFE] bg-[#EFF6FF] text-[#1D4ED8]',
  completed: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
}

const STORY_TONE: Record<string, string> = {
  to_do: 'bg-[#EFF6FF] text-[#1D4ED8]',
  in_progress: 'bg-[#FFF7ED] text-[#C2410C]',
  in_review: 'bg-[#F5F3FF] text-[#6D28D9]',
  done: 'bg-[#F0FDF4] text-[#15803D]',
}

export default function SprintsPage() {
  const params = useParams<{ code: string }>()
  const code = decodeURIComponent(params?.code ?? '')

  const [data, setData] = useState<SprintBoard | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState<Set<string>>(new Set())
  const [checked, setChecked] = useState<Set<string>>(new Set())
  const [dialog, setDialog] = useState<'add' | SprintRow | null>(null)

  const load = useCallback(async () => {
    setError('')
    try {
      setData(await fetchSprints(code))
    } catch (err: any) {
      const httpStatus = err?.response?.status
      if (httpStatus === 404) { setError(`No batch found with code ${code}.`); return }
      if (httpStatus === 403) {
        setError('This batch belongs to a department you are not attached to.')
        return
      }
      setError(errorText(err, 'Could not load the sprints.'))
    }
  }, [code])

  useEffect(() => { load() }, [load])

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true)
    setNotice(null)
    try {
      await fn()
      setNotice({ tone: 'ok', text: ok })
      await load()
      return true
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'That could not be saved.') })
      return false
    } finally {
      setBusy(false)
    }
  }

  const toggleOpen = (id: string) => setOpen((prev) => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  const toggleChecked = (id: string) => setChecked((prev) => {
    const next = new Set(prev)
    next.has(id) ? next.delete(id) : next.add(id)
    return next
  })

  const move = (sprintId: string | null, label: string) =>
    act(() => scheduleStories(code, sprintId, [...checked]),
      `${checked.size} ${checked.size === 1 ? 'story' : 'stories'} moved to ${label}.`)
      .then((done) => { if (done) setChecked(new Set()) })

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading sprints…" />

  const header = data.header

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <nav className="flex flex-wrap items-center gap-1.5 text-[12px]">
          <Link href="/trainer/batches" className="text-[#2563EB] hover:underline">My Batches</Link>
          <span className="text-[#C7CBDD]">/</span>
          <Link href="/trainer/sprints" className="text-[#2563EB] hover:underline">Sprints</Link>
          <span className="text-[#C7CBDD]">/</span>
          <span className="text-[#6B7280]">{code}</span>
        </nav>
        <Link href="/trainer/sprints" className={BTN_OUTLINE}>
          <ArrowLeft className="h-3.5 w-3.5" /> All batches
        </Link>
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">Sprints</h1>
          <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
            Project: {header.project_title ?? 'Untitled project'}
          </p>
          <p className="text-[11.5px] text-[#9CA3AF]">
            Batch: {header.batch_code} · Guide: {header.guide ?? '—'} ·
            {' '}{data.backlog_total} stories in the backlog
          </p>
        </div>
        <button type="button" className={BTN_PRIMARY} disabled={busy}
          onClick={() => setDialog('add')}>
          <Plus className="h-4 w-4" /> Add Sprint
        </button>
      </div>

      {notice && (
        <div className={cn('flex items-start justify-between gap-3 rounded-lg border px-3 py-2 text-[12.5px]',
          notice.tone === 'ok'
            ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
            : 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]')}>
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((k) => {
          const Icon = KPI_ICON[k.id] ?? CalendarRange
          return (
            <div key={k.id} className={cn(CARD, 'p-3')}>
              <div className="flex items-center gap-2">
                <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                  KPI_TONE[k.id])}>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0 flex-1 text-[11px] leading-tight text-[#6B7280]">
                  {k.label}
                </span>
              </div>
              <p className="mt-1.5 text-[20px] font-bold leading-none text-[#1B1B3A]">{k.value}</p>
              {k.hint && <p className="mt-1 text-[10px] text-[#9CA3AF]">{k.hint}</p>}
            </div>
          )
        })}
      </div>

      {/* The scheduling toolbar. It appears only with a selection, because
          that is the only time there is anything to move. */}
      {checked.size > 0 && (
        <div className="sticky top-2 z-20 flex flex-wrap items-center gap-2 rounded-xl border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2">
          <span className="text-[12px] font-medium text-[#1E40AF]">
            {checked.size} {checked.size === 1 ? 'story' : 'stories'} selected
          </span>
          <span className="flex-1" />
          <select aria-label="Move to sprint" defaultValue="" disabled={busy}
            onChange={(e) => {
              const value = e.target.value
              e.target.value = ''
              if (!value) return
              const sprint = data.rows.find((r) => r.id === value)
              move(value === 'none' ? null : value,
                value === 'none' ? 'the backlog' : sprint?.name ?? 'that sprint')
            }}
            className={cn(FIELD, 'h-8 w-auto')}>
            <option value="">Move to…</option>
            {data.rows.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
            <option value="none">Unschedule</option>
          </select>
          <button type="button" onClick={() => setChecked(new Set())}
            className="text-[12px] font-medium text-[#1E40AF] hover:underline">Clear</button>
        </div>
      )}

      {data.rows.length === 0 ? (
        <div className={cn(CARD, 'px-6 py-14 text-center')}>
          <p className="text-[12.5px] text-[#6B7280]">
            No sprints on this batch yet. Add one to start scheduling the backlog.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.rows.map((sprint) => (
            <SprintCard key={sprint.id} sprint={sprint} code={code} busy={busy}
              expanded={open.has(sprint.id)} onToggle={() => toggleOpen(sprint.id)}
              checked={checked} onCheck={toggleChecked}
              states={data.states}
              onState={(state) => act(() => patchSprint(code, sprint.id, { state }),
                `${sprint.name} is now ${state.replace('_', ' ')}.`)}
              onEdit={() => setDialog(sprint)} />
          ))}
        </div>
      )}

      <UnscheduledCard rollUp={data.unscheduled} checked={checked} onCheck={toggleChecked}
        expanded={open.has('unscheduled')} onToggle={() => toggleOpen('unscheduled')} />

      {dialog !== null && (
        <AddSprintDialog
          busy={busy}
          mode={dialog === 'add' ? 'create' : 'edit'}
          initial={dialog === 'add' ? undefined : {
            name: dialog.name,
            goal: dialog.goal ?? '',
            start_date: dialog.start_date ?? '',
            end_date: dialog.end_date ?? '',
            state: dialog.state,
          }}
          onClose={() => setDialog(null)}
          onSubmit={async (input: NewSprintInput) => {
            const done = dialog === 'add'
              ? await act(() => addSprint(code, input), `${input.name} added.`)
              : await act(() => patchSprint(code, dialog.id, {
                name: input.name,
                goal: input.goal ?? '',
                start_date: input.start_date || null,
                end_date: input.end_date || null,
                state: input.state,
              }), `${input.name} saved.`)
            if (done) setDialog(null)
          }} />
      )}
    </div>
  )
}

function SprintCard({
  sprint, code, busy, expanded, onToggle, checked, onCheck, states, onState, onEdit,
}: {
  sprint: SprintRow
  code: string
  busy: boolean
  expanded: boolean
  onToggle: () => void
  checked: Set<string>
  onCheck: (id: string) => void
  states: { value: string; label: string }[]
  onState: (state: string) => void
  onEdit: () => void
}) {
  return (
    <section className={cn(CARD, sprint.overdue && 'border-[#FED7AA]')}>
      <header className="flex flex-wrap items-center gap-2 border-b border-[#F1F2F8] px-4 py-3">
        <button type="button" onClick={onToggle} aria-label={`Toggle ${sprint.name}`}
          className="rounded p-0.5 text-[#9CA3AF] hover:bg-[#F4F5FA]">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <h2 className="text-[14px] font-bold text-[#1B1B3A]">{sprint.name}</h2>
        <span className="text-[11px] text-[#9CA3AF]">{sprint.key}</span>
        {sprint.window && (
          <span className="flex items-center gap-1 text-[11.5px] text-[#6B7280]">
            <CalendarClock className="h-3.5 w-3.5" /> {sprint.window}
          </span>
        )}
        <span className={cn('rounded-md border px-2 py-0.5 text-[10.5px] font-medium',
          STATE_TONE[sprint.state])}>
          {sprint.state_label}
        </span>
        {sprint.overdue && (
          <span className="flex items-center gap-1 rounded-md border border-[#FED7AA] bg-[#FFF7ED] px-2 py-0.5 text-[10.5px] font-medium text-[#C2410C]">
            <AlertTriangle className="h-3 w-3" /> Past its end date
          </span>
        )}
        {sprint.days_left !== null && sprint.days_left >= 0 && (
          <span className="text-[11px] text-[#6B7280]">
            {sprint.days_left} {sprint.days_left === 1 ? 'day' : 'days'} left
          </span>
        )}

        <span className="flex-1" />

        <select value={sprint.state} disabled={busy} aria-label={`${sprint.name} state`}
          onChange={(e) => onState(e.target.value)} className={cn(FIELD, 'h-8 w-auto')}>
          {states.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <button type="button" onClick={onEdit} aria-label={`Edit ${sprint.name}`}
          className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#2563EB] hover:bg-[#F4F7FF]">
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </header>

      <div className="space-y-2 px-4 py-3">
        {sprint.goal && <p className="text-[11.5px] text-[#6B7280]">{sprint.goal}</p>}

        <div className="flex flex-wrap items-center gap-3">
          <span className="min-w-[180px] flex-1">
            <span className="mb-1 flex items-center justify-between text-[11px] text-[#6B7280]">
              <span>{sprint.done} of {sprint.stories} stories done</span>
              <span>{sprint.done_points} / {sprint.points} pts</span>
            </span>
            <span className="block h-1.5 overflow-hidden rounded-full bg-[#EEF0F7]">
              <span className={cn('block h-full rounded-full',
                sprint.points_percent === 100 ? 'bg-[#16A34A]' : 'bg-[#2563EB]')}
                style={{ width: `${sprint.points_percent}%` }} />
            </span>
          </span>
          <span className="flex flex-wrap gap-1.5">
            {Object.entries(sprint.counts).map(([status, count]) => count > 0 && (
              <span key={status}
                className={cn('rounded-md px-1.5 py-0.5 text-[10px] font-medium',
                  STORY_TONE[status])}>
                {count} {status.replace('_', ' ')}
              </span>
            ))}
          </span>
        </div>

        {expanded && (
          sprint.story_rows.length === 0 ? (
            <p className="py-4 text-center text-[11.5px] text-[#9CA3AF]">
              Nothing scheduled into this sprint yet.
            </p>
          ) : (
            <StoryLines rows={sprint.story_rows} checked={checked} onCheck={onCheck} />
          )
        )}
      </div>

      {/* Only for an open sprint: the chart is a read of the sprint's shape,
          and it costs a request, so it loads when the card is opened. */}
      {expanded && sprint.story_rows.length > 0 && (
        <div className="border-t border-[#F1F2F8] pt-3">
          <BurndownChart code={code} sprintId={sprint.id} />
        </div>
      )}
    </section>
  )
}

function UnscheduledCard({ rollUp, checked, onCheck, expanded, onToggle }: {
  rollUp: SprintRollUp
  checked: Set<string>
  onCheck: (id: string) => void
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <section className={cn(CARD, rollUp.stories > 0 && 'border-[#FED7AA]')}>
      <header className="flex flex-wrap items-center gap-2 px-4 py-3">
        <button type="button" onClick={onToggle} aria-label="Toggle unscheduled stories"
          className="rounded p-0.5 text-[#9CA3AF] hover:bg-[#F4F5FA]">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </button>
        <h2 className="text-[14px] font-bold text-[#1B1B3A]">Unscheduled</h2>
        <span className="text-[11.5px] text-[#6B7280]">
          {rollUp.stories} {rollUp.stories === 1 ? 'story' : 'stories'} · {rollUp.points} pts
        </span>
        {rollUp.stories > 0 && (
          <span className="text-[11px] text-[#C2410C]">
            In the backlog but not in any sprint
          </span>
        )}
      </header>

      {expanded && (
        <div className="px-4 pb-3">
          {rollUp.story_rows.length === 0 ? (
            <p className="py-4 text-center text-[11.5px] text-[#9CA3AF]">
              Everything in the backlog is scheduled.
            </p>
          ) : (
            <StoryLines rows={rollUp.story_rows} checked={checked} onCheck={onCheck} />
          )}
        </div>
      )}
    </section>
  )
}

function StoryLines({ rows, checked, onCheck }: {
  rows: SprintStoryLine[]
  checked: Set<string>
  onCheck: (id: string) => void
}) {
  return (
    <ul className="divide-y divide-[#F1F2F8] border-t border-[#F1F2F8]">
      {rows.map((s) => (
        <li key={s.id} className="flex flex-wrap items-center gap-2 py-2">
          <input type="checkbox" aria-label={`Select ${s.key}`}
            checked={checked.has(s.id)} onChange={() => onCheck(s.id)} />
          <span className="w-[54px] shrink-0 text-[11.5px] font-medium text-[#2563EB]">
            {s.key}
          </span>
          <span className="min-w-[180px] flex-1 truncate text-[12px] text-[#1B1B3A]">
            {s.title}
          </span>
          <AssigneeChip person={s.assignee} />
          <span className="rounded bg-[#F4F5FA] px-1.5 py-0.5 text-[10px] text-[#6B7280]">
            {s.story_points} pts
          </span>
          <span className={cn('rounded-md px-1.5 py-0.5 text-[10px] font-medium',
            STORY_TONE[s.status])}>
            {s.status_label}
          </span>
        </li>
      ))}
    </ul>
  )
}
