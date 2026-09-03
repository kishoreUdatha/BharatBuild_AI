'use client'

/**
 * The open story.
 *
 * Everything in the top half is editable and saves the moment it changes: the
 * job on this screen is handing work out and moving it along, and a panel that
 * needed a separate Save step would put a click between the trainer and the
 * only two fields they came here to set.
 */

import { useEffect, useState } from 'react'
import { BranchHint } from '@/components/story/BranchHint'
import {
  Activity, AlertTriangle, CalendarClock, CheckCircle2, Circle, ClipboardList,
  Trash2,
  ExternalLink, Loader2, MessageSquare, Pencil, Send, X,
} from 'lucide-react'
import type {
  Option, Person, SprintRef, StoryPatch, UserStoryDetail,
} from '@/lib/trainer-api'
import { cn } from '@/lib/utils'
import {
  Avatar, BTN_PRIMARY, FIELD, StatusChip, TypeChip, fmtDay, fmtMoment,
} from './bits'

const TABS = ['Details', 'Tasks', 'Activity', 'Comments'] as const
type Tab = (typeof TABS)[number]

export function StoryPanel({
  story, sprints, assignees, statuses, priorities, types, busy,
  onPatch, onComment, onClose, onDelete, historyHref,
}: {
  story: UserStoryDetail
  sprints: SprintRef[]
  assignees: Person[]
  statuses: Option[]
  priorities: Option[]
  types: Option[]
  busy: boolean
  onPatch: (patch: StoryPatch) => void
  onComment: (body: string) => Promise<void>
  onDelete: () => Promise<void>
  onClose: () => void
  historyHref: string
}) {
  const [confirming, setConfirming] = useState(false)
  const [tab, setTab] = useState<Tab>('Details')
  const [points, setPoints] = useState(String(story.story_points))
  const [note, setNote] = useState('')
  const [sending, setSending] = useState(false)
  // The draft while the title and description are open for editing. Held apart
  // from `story` so a rejected save leaves the panel showing what the server
  // actually has.
  const [editing, setEditing] = useState<{ title: string; narrative: string } | null>(null)

  // A different story is a different set of values; without this the points
  // box would keep showing the previous story's number.
  useEffect(() => {
    setPoints(String(story.story_points))
    setNote('')
    setEditing(null)
  }, [story.id, story.story_points])

  const count = (t: Tab) =>
    t === 'Tasks' ? story.counts.tasks
      : t === 'Comments' ? story.counts.comments
        : t === 'Activity' ? story.counts.activity : 0

  const savePoints = () => {
    const value = Number(points)
    if (points === '' || Number.isNaN(value) || value === story.story_points) {
      setPoints(String(story.story_points))
      return
    }
    onPatch({ story_points: value })
  }

  const send = async () => {
    const body = note.trim()
    if (!body) return
    setSending(true)
    try {
      await onComment(body)
      setNote('')
    } finally {
      setSending(false)
    }
  }

  return (
    <aside className="flex h-full flex-col">
      <header className="flex items-start justify-between gap-2 border-b border-[#F1F2F8] px-4 py-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[13px] font-bold text-[#2563EB]">{story.key}</span>
            <StatusChip value={story.status} label={story.status_label} />
            <TypeChip value={story.type} label={story.type_label} />
            {busy && <Loader2 className="h-3.5 w-3.5 animate-spin text-[#2563EB]" />}
          </div>
          {editing ? (
            <input value={editing.title} autoFocus aria-label="Story title"
              onChange={(e) => setEditing({ ...editing, title: e.target.value })}
              className="mt-1.5 w-full rounded-lg border border-[#D1D5DB] px-2 py-1 text-[13px] font-semibold outline-none focus:border-[#2563EB]" />
          ) : (
            <h2 className="mt-1.5 flex items-start gap-1.5 text-[13.5px] font-semibold leading-snug text-[#1B1B3A]">
              <span className="min-w-0 flex-1">{story.title}</span>
              <button type="button" aria-label="Edit story" disabled={busy}
                onClick={() => setEditing({
                  title: story.title, narrative: story.narrative ?? '',
                })}
                className="shrink-0 rounded p-0.5 text-[#9CA3AF] hover:bg-[#F4F5FA] hover:text-[#2563EB] disabled:opacity-50">
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </h2>
          )}
        </div>
        <button type="button" onClick={onClose} aria-label="Close story"
          className="rounded-lg p-1 text-[#9CA3AF] hover:bg-[#F4F5FA]">
          <X className="h-4 w-4" />
        </button>
      </header>

      <div className="space-y-2 border-b border-[#F1F2F8] px-4 py-3">
        <Row label="Epic">
          <span className="text-[11.5px] text-[#3A3F58]">
            {story.epic_key ? `${story.epic_key} · ${story.epic_title}` : '—'}
          </span>
        </Row>

        <Row label="Assignee">
          <select aria-label="Assignee" disabled={busy}
            value={story.assignee?.id ?? ''}
            onChange={(e) => onPatch({ assignee_id: e.target.value || null })}
            className={cn(FIELD, 'h-8 text-[11.5px]')}>
            <option value="">Unassigned</option>
            {assignees.map((p) => (
              <option key={p.id} value={p.id}>
                {p.roll ? `${p.roll} · ${p.name}` : p.name}
              </option>
            ))}
          </select>
        </Row>

        <Row label="Sprint">
          <select aria-label="Sprint" disabled={busy}
            value={story.sprint?.id ?? ''}
            onChange={(e) => onPatch({ sprint_id: e.target.value || null })}
            className={cn(FIELD, 'h-8 text-[11.5px]')}>
            <option value="">Unscheduled</option>
            {sprints.map((s) => (
              <option key={s.id} value={s.id}>
                {s.window ? `${s.name} (${s.window})` : s.name}
              </option>
            ))}
          </select>
        </Row>

        <Row label="Status">
          <select aria-label="Status" disabled={busy} value={story.status}
            onChange={(e) => onPatch({ status: e.target.value })}
            className={cn(FIELD, 'h-8 text-[11.5px]')}>
            {statuses.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Row>

        <Row label="Priority">
          <select aria-label="Priority" disabled={busy} value={story.priority}
            onChange={(e) => onPatch({ priority: e.target.value })}
            className={cn(FIELD, 'h-8 text-[11.5px]')}>
            {priorities.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Row>

        <Row label="Type">
          <select aria-label="Story type" disabled={busy} value={story.type}
            onChange={(e) => onPatch({ story_type: e.target.value })}
            className={cn(FIELD, 'h-8 text-[11.5px]')}>
            {types.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </Row>

        <Row label="Story Points">
          <input type="number" min={0} max={100} aria-label="Story points"
            disabled={busy} value={points}
            onChange={(e) => setPoints(e.target.value)}
            onBlur={savePoints}
            onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
            className={cn(FIELD, 'h-8 text-[11.5px]')} />
        </Row>

        <Row label="Due date">
          <input type="date" aria-label="Due date" disabled={busy}
            value={story.due_date ?? ''}
            onChange={(e) => onPatch({ due_date: e.target.value || null })}
            className={cn(FIELD, 'h-8 text-[11.5px]',
              story.overdue && 'border-[#FECACA] text-[#DC2626]')} />
        </Row>

        {story.overdue && (
          <p className="flex items-center gap-1 pl-[94px] text-[10.5px] font-medium text-[#DC2626]">
            <AlertTriangle className="h-3 w-3" /> Past its due date
          </p>
        )}
      </div>

      <nav className="flex gap-1 border-b border-[#F1F2F8] px-3 pt-2">
        {TABS.map((t) => (
          <button key={t} type="button" onClick={() => setTab(t)}
            className={cn('rounded-t-lg px-2.5 py-1.5 text-[11.5px] font-medium transition-colors',
              tab === t
                ? 'border-b-2 border-[#2563EB] text-[#2563EB]'
                : 'text-[#6B7280] hover:text-[#374151]')}>
            {t}{t !== 'Details' && count(t) > 0 ? ` (${count(t)})` : ''}
          </button>
        ))}
      </nav>

      <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {tab === 'Details' && (
          <>
            {/* Collapsed by default here. A trainer is usually reading the
                story, not starting a branch on it - but when a team asks
                "what do we call it", the answer should not be somewhere else. */}
            <BranchHint storyId={story.id} storyKey={story.key} title={story.title} compact />

            <Section title="Description">
              {editing ? (
                <div className="space-y-2">
                  <textarea rows={4} value={editing.narrative} aria-label="Description"
                    placeholder="As a …, I want … so that …"
                    onChange={(e) => setEditing({ ...editing, narrative: e.target.value })}
                    className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[11.5px] leading-relaxed outline-none focus:border-[#2563EB]" />
                  <div className="flex justify-end gap-2">
                    <button type="button" onClick={() => setEditing(null)}
                      className="rounded-lg border border-[#D1D5DB] px-2.5 py-1 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                      Cancel
                    </button>
                    <button type="button" disabled={busy || editing.title.trim().length < 3}
                      onClick={() => {
                        onPatch({
                          title: editing.title.trim(),
                          narrative: editing.narrative.trim(),
                        })
                        setEditing(null)
                      }}
                      className={cn(BTN_PRIMARY, 'px-3 py-1 text-[11.5px]')}>
                      Save
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-[11.5px] leading-relaxed text-[#4B5563]">
                  {story.narrative ?? 'No description was written for this story.'}
                </p>
              )}
            </Section>

            <Section title={`Acceptance Criteria (${story.acceptance_criteria.length})`}>
              {story.acceptance_criteria.length === 0 ? (
                <p className="text-[11px] italic text-[#9CA3AF]">None recorded.</p>
              ) : (
                <ul className="space-y-1">
                  {story.acceptance_criteria.map((c) => (
                    <li key={c.id} className="flex gap-1.5 text-[11px] leading-snug text-[#4B5563]">
                      {c.met
                        ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                        : <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#EA580C]" />}
                      {c.text}
                    </li>
                  ))}
                </ul>
              )}
            </Section>

            {story.definition_of_done.length > 0 && (
              <Section title="Definition of Done">
                <ul className="space-y-1">
                  {story.definition_of_done.map((d) => (
                    <li key={d.id} className="flex gap-1.5 text-[11px] leading-snug text-[#4B5563]">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                      {d.text}
                    </li>
                  ))}
                </ul>
              </Section>
            )}

            {story.dependencies && (
              <Section title="Dependencies">
                <p className="text-[11.5px] text-[#4B5563]">{story.dependencies}</p>
              </Section>
            )}

            {story.labels.length > 0 && (
              <Section title="Labels">
                <span className="flex flex-wrap gap-1.5">
                  {story.labels.map((label) => (
                    <span key={label}
                      className="rounded-md border border-[#E5E7EB] bg-[#F9FAFB] px-1.5 py-0.5 text-[10.5px] text-[#4B5563]">
                      {label}
                    </span>
                  ))}
                </span>
              </Section>
            )}
          </>
        )}

        {tab === 'Tasks' && (
          <>
            {/* Adding one needs a title, an assignee and a date - more than
                this column can hold without cramping, so it happens on the
                story's own page. */}
            <a href={`/stories/${story.id}`} target="_blank" rel="noopener"
              className="mb-2 flex items-center justify-center gap-1.5 rounded-lg border border-[#D1D5DB] py-1.5 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
              <ExternalLink className="h-3.5 w-3.5" /> Add a sub-task
            </a>
            {story.tasks.length === 0 ? (
              <Blank icon={<ClipboardList className="h-5 w-5" />}
                message="No tasks break this story down yet." />
            ) : (
            <ul className="space-y-1.5">
              {story.tasks.map((t) => (
                <li key={t.id} className="flex items-start gap-2 rounded-lg border border-[#F1F2F8] p-2">
                  {t.done
                    ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                    : <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#9CA3AF]" />}
                  <span className="min-w-0 flex-1">
                    <span className={cn('block text-[11.5px] leading-snug',
                      t.done ? 'text-[#9CA3AF] line-through' : 'text-[#1B1B3A]')}>
                      {t.title}
                    </span>
                    <span className="mt-0.5 flex flex-wrap items-center gap-2 text-[10px] text-[#9CA3AF]">
                      <span>{t.status_label}</span>
                      {t.assignee && <span>· {t.assignee.name}</span>}
                      {t.due_date && (
                        <span className="flex items-center gap-1">
                          <CalendarClock className="h-3 w-3" /> {fmtDay(t.due_date)}
                        </span>
                      )}
                    </span>
                  </span>
                </li>
              ))}
              </ul>
            )}
          </>
        )}

        {tab === 'Activity' && (
          story.activity.length === 0 ? (
            <Blank icon={<Activity className="h-5 w-5" />}
              message="Nothing has happened to this story yet." />
          ) : (
            <ol className="space-y-2.5">
              {story.activity.map((a) => (
                <li key={a.id} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-[#BFDBFE]" />
                  <span className="min-w-0">
                    <span className="block text-[11.5px] text-[#1B1B3A]">
                      {a.summary}
                      {a.from_value && a.to_value && (
                        <span className="text-[#6B7280]"> · {a.from_value} → {a.to_value}</span>
                      )}
                    </span>
                    <span className="block text-[10px] text-[#9CA3AF]">
                      {a.actor} · {fmtMoment(a.occurred_at)}
                    </span>
                  </span>
                </li>
              ))}
            </ol>
          )
        )}

        {tab === 'Comments' && (
          <>
            <div className="space-y-1.5">
              <textarea rows={3} value={note} onChange={(e) => setNote(e.target.value)}
                maxLength={2000} aria-label="Add a comment"
                placeholder="Leave a note on this story…"
                className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[11.5px] outline-none focus:border-[#2563EB]" />
              <button type="button" onClick={send} disabled={sending || !note.trim()}
                className={cn(BTN_PRIMARY, 'w-full justify-center py-1.5 text-[11.5px]')}>
                {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : <Send className="h-3.5 w-3.5" />}
                Add comment
              </button>
            </div>

            {story.comments.length === 0 ? (
              <Blank icon={<MessageSquare className="h-5 w-5" />}
                message="No comments on this story." />
            ) : (
              <ul className="space-y-2">
                {story.comments.map((c) => (
                  <li key={c.id} className="rounded-lg border border-[#F1F2F8] p-2">
                    <p className="text-[11.5px] leading-snug text-[#4B5563]">{c.body}</p>
                    <p className="mt-1 text-[10px] text-[#9CA3AF]">
                      {c.author} · {fmtMoment(c.created_at)}
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>

      <footer className="space-y-2 border-t border-[#F1F2F8] px-4 py-3">
        <div className="grid grid-cols-2 gap-2 text-[10.5px]">
          <span>
            <span className="block text-[#9CA3AF]">Created On</span>
            <span className="block text-[#4B5563]">{fmtMoment(story.created_at)}</span>
          </span>
          <span>
            <span className="block text-[#9CA3AF]">Created By</span>
            <span className="block text-[#4B5563]">{story.created_by}</span>
          </span>
        </div>
        {story.assignee && (
          <div className="flex items-center gap-2 rounded-lg bg-[#FAFBFE] px-2 py-1.5">
            <Avatar person={story.assignee} size="sm" />
            <span className="min-w-0">
              <span className="block truncate text-[11px] font-medium text-[#1B1B3A]">
                {story.assignee.name}
              </span>
              <span className="block text-[10px] text-[#9CA3AF]">
                {story.assignee.roll ?? 'No roll number'}
              </span>
            </span>
          </div>
        )}
        {/* Where this story came from. The approval screen holds its draft,
            its AI confidence and the trainer decision that let it through. */}
        <a href={historyHref}
          className="block rounded-lg border border-[#D1D5DB] py-1.5 text-center text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
          Review history in AI Planning
        </a>

        {/* Two steps, because the criteria, comments and history go with it
            and there is no undo. Deliberately quiet until asked for. */}
        {confirming ? (
          <div className="rounded-lg border border-[#FECACA] bg-[#FEF2F2] p-2.5">
            <p className="text-[11.5px] font-semibold text-[#B91C1C]">
              Delete {story.key}?
            </p>
            <p className="mt-0.5 text-[10.5px] leading-relaxed text-[#B91C1C]">
              Its acceptance criteria, comments and history go too, and this
              cannot be undone. Sub-tasks and any commits that named it are kept.
            </p>
            <div className="mt-2 flex gap-2">
              <button type="button" disabled={busy}
                onClick={() => { setConfirming(false); void onDelete() }}
                className="flex-1 rounded-lg bg-[#DC2626] py-1.5 text-[11.5px] font-medium text-white hover:bg-[#B91C1C] disabled:opacity-50">
                Delete it
              </button>
              <button type="button" onClick={() => setConfirming(false)}
                className="flex-1 rounded-lg border border-[#D1D5DB] bg-white py-1.5 text-[11.5px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                Keep it
              </button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => setConfirming(true)} disabled={busy}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-[#FECACA] py-1.5 text-[11.5px] font-medium text-[#DC2626] hover:bg-[#FEF2F2] disabled:opacity-50">
            <Trash2 className="h-3.5 w-3.5" /> Delete story
          </button>
        )}
      </footer>
    </aside>
  )
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[86px_minmax(0,1fr)] items-center gap-2">
      <span className="text-[11px] text-[#9CA3AF]">{label}</span>
      {children}
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="mb-1.5 text-[12px] font-semibold text-[#1B1B3A]">{title}</h3>
      {children}
    </section>
  )
}

function Blank({ icon, message }: { icon: React.ReactNode; message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-8 text-center text-[#9CA3AF]">
      {icon}
      <p className="text-[11.5px]">{message}</p>
    </div>
  )
}
