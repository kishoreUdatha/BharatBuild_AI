'use client'

/**
 * Which project's backlog am I looking at?
 *
 * A trainer thinks in department, section and batch number - that is how the
 * allocation sheet is laid out and how a batch is referred to in a review - so
 * that is how the batch is chosen here, rather than by hunting for a code.
 *
 * The three lists cascade, and every option comes from the trainer's own
 * batches. A choice can therefore never lead to an empty result: if a section
 * is offered, this trainer has a batch in it.
 */

import { useMemo } from 'react'
import { Search, X } from 'lucide-react'
import type { BatchCard } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'
import { FIELD } from './bits'

export interface BatchScope {
  department: string
  section: string
  batch_no: string
  search: string
}

export const EMPTY_SCOPE: BatchScope = {
  department: '', section: '', batch_no: '', search: '',
}

/** Everything the scope allows, before the batch number narrows it to one. */
export function batchesInScope(batches: BatchCard[], scope: BatchScope): BatchCard[] {
  const needle = scope.search.trim().toLowerCase()
  return batches.filter((b) => {
    if (scope.department && b.department !== scope.department) return false
    if (scope.section && (b.section ?? '') !== scope.section) return false
    if (scope.batch_no && (b.batch_no ?? '') !== scope.batch_no) return false
    if (needle && ![b.batch_code, b.title, b.guide]
      .some((v) => (v ?? '').toLowerCase().includes(needle))) return false
    return true
  })
}

const unique = (values: (string | null | undefined)[]) =>
  Array.from(new Set(values.filter((v): v is string => Boolean(v)))).sort()

export function BatchFilters({ batches, scope, onChange }: {
  batches: BatchCard[]
  scope: BatchScope
  onChange: (scope: BatchScope) => void
}) {
  const departments = useMemo(() => unique(batches.map((b) => b.department)), [batches])

  const sections = useMemo(() => unique(batches
    .filter((b) => !scope.department || b.department === scope.department)
    .map((b) => b.section)), [batches, scope.department])

  const batchNos = useMemo(() => unique(batches
    .filter((b) => (!scope.department || b.department === scope.department)
      && (!scope.section || (b.section ?? '') === scope.section))
    .map((b) => b.batch_no)), [batches, scope.department, scope.section])

  // Narrowing a level up invalidates the levels below it: a section from the
  // old department would filter to nothing and read as "no batches".
  const setDepartment = (department: string) =>
    onChange({ ...scope, department, section: '', batch_no: '' })
  const setSection = (section: string) => onChange({ ...scope, section, batch_no: '' })

  const matches = batchesInScope(batches, scope)
  const touched = Boolean(scope.department || scope.section || scope.batch_no || scope.search)

  return (
    <section className="rounded-xl border border-[#E5E7EB] bg-white p-3">
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        <label className="block">
          <span className="block text-[11.5px] font-medium text-[#374151]">Department</span>
          <select value={scope.department} aria-label="Department" className={cn(FIELD, 'mt-1')}
            onChange={(e) => setDepartment(e.target.value)}>
            <option value="">All Departments</option>
            {departments.map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>

        <label className="block">
          <span className="block text-[11.5px] font-medium text-[#374151]">Section</span>
          <select value={scope.section} aria-label="Section" className={cn(FIELD, 'mt-1')}
            onChange={(e) => setSection(e.target.value)}>
            <option value="">All Sections</option>
            {sections.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>

        <label className="block">
          <span className="block text-[11.5px] font-medium text-[#374151]">Batch No</span>
          <select value={scope.batch_no} aria-label="Batch number" className={cn(FIELD, 'mt-1')}
            onChange={(e) => onChange({ ...scope, batch_no: e.target.value })}>
            <option value="">All Batch No</option>
            {batchNos.map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>

        <label className="block">
          <span className="block text-[11.5px] font-medium text-[#374151]">Project</span>
          <span className="relative mt-1 block">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
            <input value={scope.search} aria-label="Search projects"
              placeholder="Project title, code or guide…"
              onChange={(e) => onChange({ ...scope, search: e.target.value })}
              className={cn(FIELD, 'pl-8')} />
          </span>
        </label>
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-2 border-t border-[#F1F2F8] pt-2.5">
        <span className="text-[11px] text-[#6B7280]">
          {matches.length} {matches.length === 1 ? 'batch' : 'batches'} match
        </span>
        <span className="flex-1" />
        {touched && (
          <button type="button" onClick={() => onChange(EMPTY_SCOPE)}
            className="flex items-center gap-1 text-[12px] font-medium text-[#6B7280] hover:text-[#374151]">
            <X className="h-3.5 w-3.5" /> Clear
          </button>
        )}
      </div>
    </section>
  )
}
