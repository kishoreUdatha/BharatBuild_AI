'use client'

/**
 * Three ways of reading the same rows.
 *
 * Table is the list of record and the only paged one. Board and Sprint are
 * groupings of the whole filtered set, which is why the page asks for every
 * row when either is showing - a kanban that stopped at the tenth card would
 * be lying about the column totals underneath it.
 */

import { useState } from 'react'
import Link from 'next/link'
import { CalendarPlus, Eye, GripVertical, MoreVertical } from 'lucide-react'
import type { Option, SprintRef, UserStoryRow } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'
import {
  AssigneeChip, BTN_OUTLINE, Donut, PriorityCell, SprintLabel, STATUS_BAR,
  StatusChip, TypeChip, fmtDay,
} from './bits'

const HEADERS = ['ID', 'User Story Title', 'Epic', 'Assignee', 'Sprint',
  'Priority', 'Story Points', 'Status', 'Created On', 'Actions']

export function TableView({ rows, selectedId, statuses, onOpen, onStatus }: {
  rows: UserStoryRow[]
  selectedId: string | null
  statuses: Option[]
  onOpen: (row: UserStoryRow) => void
  onStatus: (row: UserStoryRow, status: string) => void
}) {
  const [menu, setMenu] = useState<string | null>(null)

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[960px] text-left text-[12px]">
        <thead>
          <tr className="border-y border-[#E5E7EB] bg-[#FAFBFF] text-[11.5px] text-[#6B7280]">
            {HEADERS.map((h) => (
              <th key={h} className="whitespace-nowrap px-3 py-2.5 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#F1F2F8]">
          {rows.map((r) => (
            <tr key={r.id} onClick={() => onOpen(r)}
              className={cn('cursor-pointer hover:bg-[#FAFBFE]',
                selectedId === r.id && 'bg-[#EFF6FF]')}>
              {/* The key opens the story on its own page, in its own tab: the
                  trainer is working through a list, and losing the filtered
                  board to read one story is the wrong trade. */}
              <td className="whitespace-nowrap px-3 py-2.5"
                onClick={(e) => e.stopPropagation()}>
                <Link href={`/stories/${r.id}`} target="_blank" rel="noopener"
                  title={`Open ${r.key} in a new tab`}
                  className="font-medium text-[#2563EB] hover:underline">
                  {r.key}
                </Link>
              </td>
              <td className="px-3 py-2.5">
                <span className="flex items-center gap-2">
                  <span className="line-clamp-2 text-[#1B1B3A]">{r.title}</span>
                  {r.type !== 'story' && <TypeChip value={r.type} label={r.type_label} />}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-2.5 text-[#6B7280]">
                {r.epic_title ?? '—'}
              </td>
              <td className="px-3 py-2.5"><AssigneeChip person={r.assignee} /></td>
              <td className="whitespace-nowrap px-3 py-2.5"><SprintLabel sprint={r.sprint} /></td>
              <td className="whitespace-nowrap px-3 py-2.5">
                <PriorityCell value={r.priority} label={r.priority_label} />
              </td>
              <td className="px-3 py-2.5 text-center text-[#3A3F58]">{r.story_points}</td>
              <td className="whitespace-nowrap px-3 py-2.5">
                <StatusChip value={r.status} label={r.status_label} />
              </td>
              <td className="whitespace-nowrap px-3 py-2.5 text-[#6B7280]">
                {fmtDay(r.created_at)}
              </td>
              <td className="whitespace-nowrap px-3 py-2.5"
                onClick={(e) => e.stopPropagation()}>
                <span className="relative flex items-center gap-1">
                  <Link href={`/stories/${r.id}`} target="_blank" rel="noopener"
                    aria-label={`Open ${r.key} in a new tab`}
                    className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#2563EB] hover:bg-[#F4F7FF]">
                    <Eye className="h-3.5 w-3.5" />
                  </Link>
                  <button type="button" aria-label={`Move ${r.key}`}
                    onClick={() => setMenu(menu === r.id ? null : r.id)}
                    className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#6B7280] hover:bg-[#F9FAFB]">
                    <MoreVertical className="h-3.5 w-3.5" />
                  </button>
                  {menu === r.id && (
                    <span className="absolute right-0 top-8 z-20 w-[160px] overflow-hidden rounded-lg border border-[#E5E7EB] bg-white shadow-lg">
                      {statuses.map((s) => (
                        <button key={s.value} type="button"
                          disabled={s.value === r.status}
                          onClick={() => { setMenu(null); onStatus(r, s.value) }}
                          className="block w-full px-3 py-2 text-left text-[11.5px] text-[#374151] hover:bg-[#F9FAFB] disabled:bg-[#F4F5FA] disabled:text-[#9CA3AF]">
                          Move to {s.label}
                        </button>
                      ))}
                    </span>
                  )}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function BoardView({ rows, statuses, selectedId, onOpen, onStatus, onReorder }: {
  rows: UserStoryRow[]
  statuses: Option[]
  selectedId: string | null
  onOpen: (row: UserStoryRow) => void
  onStatus: (row: UserStoryRow, status: string) => void
  onReorder?: (columnIds: string[]) => void
}) {
  const [over, setOver] = useState<string | null>(null)
  // Which card the pointer is above, so the gap opens where it will land.
  const [overCard, setOverCard] = useState<string | null>(null)
  const [dragging, setDragging] = useState<string | null>(null)
  const byId = new Map(rows.map((r) => [r.id, r]))

  /** Rebuild a column with `moved` inserted before `beforeId` (or appended). */
  const reordered = (columnCards: UserStoryRow[], movedId: string, beforeId: string | null) => {
    const without = columnCards.filter((c) => c.id !== movedId)
    const at = beforeId === null ? without.length : without.findIndex((c) => c.id === beforeId)
    const target = at < 0 ? without.length : at
    const ids = without.map((c) => c.id)
    ids.splice(target, 0, movedId)
    return ids
  }

  return (
    // One row for however many statuses the workflow has - a four-column grid
    // wrapped the moment Testing and Blocked arrived, which splits the board
    // into two halves you cannot compare. Narrow screens scroll sideways
    // instead of stacking, which is what every board does.
    <div className="grid gap-3 overflow-x-auto pb-1"
      style={{ gridTemplateColumns: `repeat(${statuses.length}, minmax(190px, 1fr))` }}>
      {statuses.map((column) => {
        // The board is a manual order: whatever sort the list is using, the
        // columns follow the position a person dragged the card into.
        const cards = rows
          .filter((r) => r.status === column.value)
          .slice()
          .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
        const points = cards.reduce((sum, r) => sum + r.story_points, 0)
        return (
          <section key={column.value}
            onDragOver={(e) => { e.preventDefault(); setOver(column.value) }}
            onDragLeave={() => setOver((v) => (v === column.value ? null : v))}
            onDrop={(e) => {
              e.preventDefault()
              setOver(null)
              const landedOn = overCard
              setOverCard(null)
              setDragging(null)
              const row = byId.get(e.dataTransfer.getData('text/plain'))
              if (!row) return
              if (row.status !== column.value) {
                // Crossing columns is a status change; where it lands inside
                // the new column is a detail the status move settles.
                onStatus(row, column.value)
                return
              }
              if (onReorder) onReorder(reordered(cards, row.id, landedOn))
            }}
            className={cn('rounded-xl border p-2.5 transition-colors',
              over === column.value
                ? 'border-[#2563EB] bg-[#EFF6FF]'
                : 'border-[#E5E7EB] bg-[#FAFBFF]')}>
            <header className="mb-2 flex items-center gap-2 px-0.5">
              <span className={cn('h-2 w-2 rounded-full', STATUS_BAR[column.value])} />
              <h3 className="text-[12px] font-semibold text-[#1B1B3A]">{column.label}</h3>
              <span className="text-[11px] text-[#9CA3AF]">{cards.length}</span>
              <span className="flex-1" />
              <span className="text-[10.5px] text-[#9CA3AF]">{points} pts</span>
            </header>

            <ul className="space-y-2">
              {cards.map((r) => (
                <li key={r.id} draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', r.id)
                    setDragging(r.id)
                  }}
                  onDragEnd={() => { setDragging(null); setOverCard(null) }}
                  onDragOver={(e) => {
                    // Above the midpoint means "insert here", below means
                    // "after this card" - the same rule every board uses.
                    e.preventDefault()
                    const box = e.currentTarget.getBoundingClientRect()
                    const above = e.clientY < box.top + box.height / 2
                    const next = cards[cards.findIndex((c) => c.id === r.id) + 1]
                    setOverCard(above ? r.id : (next ? next.id : null))
                  }}
                  onClick={() => onOpen(r)}
                  className={cn('cursor-pointer rounded-lg border bg-white p-2.5',
                    'hover:border-[#BFDBFE]',
                    dragging === r.id && 'opacity-40',
                    overCard === r.id && 'border-t-2 border-t-[#2563EB]',
                    selectedId === r.id ? 'border-[#2563EB]' : 'border-[#E5E7EB]')}>
                  <span className="flex items-start gap-1.5">
                    <GripVertical className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#D1D5DB]" />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-1.5">
                        <Link href={`/stories/${r.id}`} target="_blank" rel="noopener"
                          onClick={(e) => e.stopPropagation()}
                          className="text-[11px] font-semibold text-[#2563EB] hover:underline">
                          {r.key}
                        </Link>
                        <PriorityCell value={r.priority} label={r.priority_label} />
                      </span>
                      <span className="mt-1 block text-[11.5px] leading-snug text-[#1B1B3A]">
                        {r.title}
                      </span>
                      <span className="mt-1.5 flex items-center justify-between gap-2">
                        <AssigneeChip person={r.assignee} />
                        <span className="shrink-0 rounded bg-[#F4F5FA] px-1.5 py-0.5 text-[10px] text-[#6B7280]">
                          {r.story_points} pts
                        </span>
                      </span>
                    </span>
                  </span>
                </li>
              ))}
              {cards.length === 0 && (
                <li className="rounded-lg border border-dashed border-[#E5E7EB] px-2 py-6 text-center text-[11px] text-[#9CA3AF]">
                  Drop a story here
                </li>
              )}
            </ul>
          </section>
        )
      })}
    </div>
  )
}

export function SprintView({ rows, sprints, selectedId, onOpen, onAddSprint }: {
  rows: UserStoryRow[]
  sprints: SprintRef[]
  selectedId: string | null
  onOpen: (row: UserStoryRow) => void
  onAddSprint: () => void
}) {
  // Unscheduled work goes last: it is a backlog, not a sprint, and putting it
  // first would push the sprint a batch is actually in below the fold.
  const groups: { key: string; sprint: SprintRef | null; rows: UserStoryRow[] }[] = [
    ...sprints.map((s) => ({
      key: s.id, sprint: s, rows: rows.filter((r) => r.sprint?.id === s.id),
    })),
    { key: 'unscheduled', sprint: null, rows: rows.filter((r) => !r.sprint) },
  ]

  return (
    <div className="space-y-3">
      <div className="flex justify-end">
        <button type="button" className={BTN_OUTLINE} onClick={onAddSprint}>
          <CalendarPlus className="h-4 w-4" /> Add Sprint
        </button>
      </div>

      {groups.map((g) => {
        const points = g.rows.reduce((sum, r) => sum + r.story_points, 0)
        const done = g.rows.filter((r) => r.status === 'done').length
        return (
          <section key={g.key} className="rounded-xl border border-[#E5E7EB]">
            <header className="flex flex-wrap items-center gap-2 border-b border-[#F1F2F8] px-3 py-2.5">
              <h3 className="text-[12.5px] font-semibold text-[#1B1B3A]">
                {g.sprint?.name ?? 'Unscheduled'}
              </h3>
              {g.sprint?.window && (
                <span className="text-[11px] text-[#9CA3AF]">{g.sprint.window}</span>
              )}
              {g.sprint && (
                <span className={cn('rounded-md border px-2 py-0.5 text-[10.5px] font-medium',
                  g.sprint.state === 'active' ? 'border-[#BFDBFE] bg-[#EFF6FF] text-[#1D4ED8]'
                    : g.sprint.state === 'completed'
                      ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]'
                      : 'border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280]')}>
                  {g.sprint.state_label}
                </span>
              )}
              <span className="flex-1" />
              <span className="text-[11px] text-[#6B7280]">
                {g.rows.length} {g.rows.length === 1 ? 'story' : 'stories'} · {points} pts ·
                {' '}{done} done
              </span>
            </header>

            {g.sprint?.goal && (
              <p className="border-b border-[#F1F2F8] px-3 py-1.5 text-[11px] text-[#6B7280]">
                {g.sprint.goal}
              </p>
            )}

            {g.rows.length === 0 ? (
              <p className="px-3 py-5 text-center text-[11.5px] text-[#9CA3AF]">
                {g.sprint ? 'Nothing scheduled into this sprint.' : 'Everything is scheduled.'}
              </p>
            ) : (
              <ul className="divide-y divide-[#F1F2F8]">
                {g.rows.map((r) => (
                  <li key={r.id}>
                    <button type="button" onClick={() => onOpen(r)}
                      className={cn('flex w-full flex-wrap items-center gap-2 px-3 py-2 text-left hover:bg-[#FAFBFE]',
                        selectedId === r.id && 'bg-[#EFF6FF]')}>
                      <span className="w-[54px] shrink-0 text-[11.5px] font-medium text-[#2563EB]">
                        {r.key}
                      </span>
                      <span className="min-w-[180px] flex-1 truncate text-[12px] text-[#1B1B3A]">
                        {r.title}
                      </span>
                      <AssigneeChip person={r.assignee} />
                      <span className="rounded bg-[#F4F5FA] px-1.5 py-0.5 text-[10px] text-[#6B7280]">
                        {r.story_points} pts
                      </span>
                      <StatusChip value={r.status} label={r.status_label} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>
        )
      })}
    </div>
  )
}

export function StudentCards({ students, onShowUnassigned }: {
  students: {
    id: string; name: string; roll: string | null; initials: string
    responsibility: string | null
    stories: number; points: number; done: number; percent: number
  }[]
  onShowUnassigned: () => void
}) {
  const TONE = ['#16A34A', '#2563EB', '#D97706', '#7C3AED']
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {students.map((s, i) => (
        <div key={s.id} className="rounded-xl border border-[#E5E7EB] p-3">
          <div className="flex items-center gap-2.5">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#F4F5FA] text-[11px] font-semibold text-[#6B7280]">
              {s.initials}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[12px] font-semibold text-[#1B1B3A]">
                {s.roll ?? s.name}
              </span>
              <span className="block truncate text-[11px] text-[#6B7280]">{s.name}</span>
            </span>
          </div>
          <div className="mt-2.5 flex items-end justify-between gap-2">
            <dl className="flex gap-4">
              {[['Stories', s.stories], ['Points', s.points], ['Done', s.done]].map(([label, value]) => (
                <div key={label as string}>
                  <dt className="text-[10px] text-[#9CA3AF]">{label}</dt>
                  <dd className="text-[15px] font-bold leading-tight text-[#1B1B3A]">{value}</dd>
                </div>
              ))}
            </dl>
            <Donut percent={s.percent} tone={TONE[i % TONE.length]} />
          </div>
          {s.stories === 0 && (
            // The point of this row of cards: a member holding nothing.
            <button type="button" onClick={onShowUnassigned}
              className="mt-2 block text-left text-[10.5px] font-medium text-[#C2410C] hover:underline">
              Nothing assigned yet — see unassigned stories
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
