'use client'

/**
 * The small, repeated pieces of the User Stories screen.
 *
 * They live here because the table, the board, the sprint view and the detail
 * panel all render the same story in four sizes - a status that is amber in
 * one place and orange in another reads as two different states.
 */

import type { ReactNode } from 'react'
import { ChevronDown, ChevronUp, Minus } from 'lucide-react'
import type { Person, SprintRef } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

export const STATUS_TONE: Record<string, string> = {
  to_do: 'border-[#DBEAFE] bg-[#EFF6FF] text-[#1D4ED8]',
  in_progress: 'border-[#FED7AA] bg-[#FFF7ED] text-[#C2410C]',
  in_review: 'border-[#DDD6FE] bg-[#F5F3FF] text-[#6D28D9]',
  done: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
}

/** The column accents on the board, in the same order as the workflow. */
export const STATUS_BAR: Record<string, string> = {
  to_do: 'bg-[#2563EB]',
  in_progress: 'bg-[#EA580C]',
  testing: 'bg-[#0891B2]',
  in_review: 'bg-[#7C3AED]',
  done: 'bg-[#16A34A]',
  // Blocked is a warning, not a stage colour - it reads as "stop", which is
  // the whole point of the column.
  blocked: 'bg-[#DC2626]',
}

const TYPE_TONE: Record<string, string> = {
  story: 'border-[#E5E7EB] bg-[#F9FAFB] text-[#6B7280]',
  task: 'border-[#DBEAFE] bg-[#EFF6FF] text-[#1D4ED8]',
  bug: 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]',
  spike: 'border-[#DDD6FE] bg-[#F5F3FF] text-[#6D28D9]',
}

/** Four fixed tints, picked from the id so one student keeps one colour. */
const AVATAR_TONES = [
  'bg-[#DCFCE7] text-[#15803D]',
  'bg-[#DBEAFE] text-[#1D4ED8]',
  'bg-[#FEF3C7] text-[#B45309]',
  'bg-[#FFE4E6] text-[#BE123C]',
]

export const toneOf = (id: string) => {
  let sum = 0
  for (let i = 0; i < id.length; i += 1) sum += id.charCodeAt(i)
  return AVATAR_TONES[sum % AVATAR_TONES.length]
}

export function StatusChip({ value, label }: { value: string; label: string }) {
  return (
    <span className={cn('inline-block whitespace-nowrap rounded-md border px-2 py-0.5',
      'text-[10.5px] font-medium', STATUS_TONE[value] ?? STATUS_TONE.to_do)}>
      {label}
    </span>
  )
}

export function TypeChip({ value, label }: { value: string; label: string }) {
  return (
    <span className={cn('inline-block whitespace-nowrap rounded-md border px-1.5 py-0.5',
      'text-[10px] font-medium', TYPE_TONE[value] ?? TYPE_TONE.story)}>
      {label}
    </span>
  )
}

export function PriorityCell({ value, label }: { value: string; label: string }) {
  const Icon = value === 'high' ? ChevronUp : value === 'low' ? ChevronDown : Minus
  const tone = value === 'high' ? 'text-[#DC2626]'
    : value === 'low' ? 'text-[#6B7280]' : 'text-[#D97706]'
  return (
    <span className={cn('inline-flex items-center gap-1 text-[11.5px]', tone)}>
      <Icon className="h-3.5 w-3.5" /> {label}
    </span>
  )
}

/** The roll number is the label a trainer actually recognises, so it leads. */
export function AssigneeChip({ person }: { person: Person | null }) {
  if (!person) {
    return <span className="text-[11px] italic text-[#9CA3AF]">Unassigned</span>
  }
  return (
    <span className="flex min-w-0 items-center gap-1.5">
      <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-semibold',
        toneOf(person.id))}>
        {person.roll ?? person.initials}
      </span>
      <span className="truncate text-[11.5px] text-[#3A3F58]">{person.name}</span>
    </span>
  )
}

export function Avatar({ person, size = 'md' }: { person: Person; size?: 'sm' | 'md' }) {
  return (
    <span className={cn('flex shrink-0 items-center justify-center rounded-full font-semibold',
      toneOf(person.id),
      size === 'sm' ? 'h-6 w-6 text-[9.5px]' : 'h-9 w-9 text-[11px]')}>
      {person.initials}
    </span>
  )
}

export function SprintLabel({ sprint }: { sprint: SprintRef | null }) {
  if (!sprint) {
    return <span className="text-[11px] italic text-[#9CA3AF]">Unscheduled</span>
  }
  return (
    <span className="block">
      <span className="block text-[11.5px] text-[#3A3F58]">{sprint.name}</span>
      {sprint.window && (
        <span className="block text-[10px] text-[#9CA3AF]">{sprint.window}</span>
      )}
    </span>
  )
}

/** Completion ring for one student. Pure SVG - no chart library for one arc. */
export function Donut({ percent, tone }: { percent: number; tone: string }) {
  const radius = 16
  const circumference = 2 * Math.PI * radius
  const filled = Math.max(0, Math.min(100, percent)) / 100
  return (
    <span className="relative flex h-10 w-10 items-center justify-center">
      <svg viewBox="0 0 40 40" className="h-10 w-10 -rotate-90">
        <circle cx="20" cy="20" r={radius} fill="none" stroke="#EEF0F7" strokeWidth="4" />
        <circle cx="20" cy="20" r={radius} fill="none" stroke={tone} strokeWidth="4"
          strokeLinecap="round" strokeDasharray={`${circumference * filled} ${circumference}`} />
      </svg>
      <span className="absolute text-[10px] font-semibold text-[#1B1B3A]">{percent}%</span>
    </span>
  )
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="block text-[11.5px] font-medium text-[#374151]">{label}</span>
      <span className="mt-1 block">{children}</span>
    </label>
  )
}

export const FIELD = 'h-9 w-full rounded-lg border border-[#D1D5DB] bg-white px-2.5 ' +
  'text-[12.5px] text-[#374151] outline-none focus:border-[#2563EB] disabled:opacity-50'

export const BTN = 'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12.5px] ' +
  'font-medium disabled:cursor-not-allowed disabled:opacity-50'
export const BTN_OUTLINE = `${BTN} border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]`
export const BTN_PRIMARY = `${BTN} bg-[#2563EB] text-white hover:bg-[#1D4ED8]`

export const fmtDay = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('en-IN',
    { day: '2-digit', month: 'short', year: 'numeric' }) : '—'

export const fmtMoment = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString('en-IN',
    { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'
