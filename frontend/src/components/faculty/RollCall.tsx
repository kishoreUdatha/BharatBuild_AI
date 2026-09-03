'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertCircle, Check, Clock, Loader2, Save, Search, UserX, X } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import {
  attendanceError,
  fetchRoster,
  markAttendance,
  today,
  type AttendanceStatus,
  type Roster,
} from '@/lib/attendance-api'
import { cn } from '@/lib/utils'

interface CohortOptions {
  departments: { code: string; name: string; sections: { year: string; semester: string; name: string }[] }[]
}

const STATUS_STYLE: Record<AttendanceStatus, string> = {
  present: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  absent: 'border-[#FECACA] bg-[#FEF2F2] text-[#B91C1C]',
  late: 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
}

const STATUS_ICON = { present: Check, absent: UserX, late: Clock }

/**
 * The register: one section, one day.
 *
 * Everyone starts Present when a fresh day is opened, because that is what a
 * roll call actually is - you call out the exceptions. A day already taken
 * loads the marks that were saved rather than a blank sheet, so reopening it
 * to correct one student cannot silently overwrite the rest.
 */
export function RollCall({ onClose, onSaved }: {
  onClose: () => void
  onSaved: (message: string) => void
}) {
  const [options, setOptions] = useState<CohortOptions | null>(null)
  const [department, setDepartment] = useState('')
  const [cohort, setCohort] = useState('')
  const [day, setDay] = useState(today())

  const [roster, setRoster] = useState<Roster | null>(null)
  const [marks, setMarks] = useState<Record<string, AttendanceStatus>>({})
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    apiClient.get<CohortOptions>('/faculty/registrations/batch-options')
      .then((data) => {
        setOptions(data)
        setDepartment((d) => d || data.departments[0]?.code || '')
      })
      .catch((err) => setError(attendanceError(err, 'Could not load departments.')))
  }, [])

  const sections = useMemo(() => {
    const dept = options?.departments.find((d) => d.code === department)
    if (!dept) return []
    const seen = new Set<string>()
    return dept.sections.filter((s) => {
      const key = `${s.year}|${s.name}`
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [options, department])

  const load = useCallback(async () => {
    const [year, section] = cohort.split('|')
    if (!department || !section) { setRoster(null); return }
    setLoading(true); setError('')
    try {
      const data = await fetchRoster({ department, year, section, date: day })
      setRoster(data)
      // A day already taken keeps its marks; a fresh one starts everyone
      // present, which is what a roll call reads out.
      setMarks(Object.fromEntries(data.students.map((s) => [
        s.student_id, (s.status ?? 'present') as AttendanceStatus,
      ])))
    } catch (err) {
      setError(attendanceError(err, 'Could not load the register.'))
      setRoster(null)
    } finally {
      setLoading(false)
    }
  }, [department, cohort, day])

  useEffect(() => { load() }, [load])

  const setAll = (status: AttendanceStatus) => {
    if (!roster) return
    setMarks(Object.fromEntries(roster.students.map((s) => [s.student_id, status])))
  }

  const save = async () => {
    if (!roster) return
    const [year, section] = cohort.split('|')
    setSaving(true); setError('')
    try {
      const result = await markAttendance({
        department, year, section, date: day,
        marks: roster.students.map((s) => ({
          student_id: s.student_id, status: marks[s.student_id] ?? 'present',
        })),
      })
      setRoster(result)
      setMarks(Object.fromEntries(result.students.map((s) => [
        s.student_id, (s.status ?? 'present') as AttendanceStatus,
      ])))
      onSaved(result.message)
    } catch (err) {
      setError(attendanceError(err, 'The register could not be saved.'))
    } finally {
      setSaving(false)
    }
  }

  const visible = (roster?.students ?? []).filter((s) => {
    if (!search.trim()) return true
    const needle = search.trim().toLowerCase()
    return (s.roll_number ?? '').toLowerCase().includes(needle)
      || (s.full_name ?? '').toLowerCase().includes(needle)
  })

  const tally = { present: 0, absent: 0, late: 0 }
  for (const student of roster?.students ?? []) {
    tally[marks[student.student_id] ?? 'present'] += 1
  }

  return (
    <section className="rounded-xl border border-[#C7BDF5] bg-[#F5F3FF] p-3">
      <div className="mb-2.5 flex items-center justify-between">
        <p className="text-[12.5px] font-semibold text-[#1B1B3A]">Take attendance</p>
        <button type="button" onClick={onClose} aria-label="Close"
          className="text-[#5A5F7A] hover:text-[#1B1B3A]"><X className="h-4 w-4" /></button>
      </div>

      <div className="grid gap-2.5 sm:grid-cols-3">
        <label>
          <span className="mb-1 block text-[10.5px] text-[#8A8FA8]">Department</span>
          <select value={department} disabled={!options}
            onChange={(e) => { setDepartment(e.target.value); setCohort('') }}
            className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]">
            {options?.departments.map((d) => (
              <option key={d.code} value={d.code}>{d.code} &mdash; {d.name}</option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1 block text-[10.5px] text-[#8A8FA8]">Year and section</span>
          <select value={cohort} onChange={(e) => setCohort(e.target.value)}
            className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]">
            <option value="">Choose a section&hellip;</option>
            {sections.map((s) => (
              <option key={`${s.year}|${s.name}`} value={`${s.year}|${s.name}`}>
                {s.year} &middot; Section {s.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="mb-1 block text-[10.5px] text-[#8A8FA8]">Date</span>
          <input type="date" value={day} max={today()}
            onChange={(e) => setDay(e.target.value)}
            className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]" />
        </label>
      </div>

      {error && (
        <p className="mt-2 flex items-start gap-1.5 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-2.5 py-2 text-[11.5px] text-[#B91C1C]">
          <AlertCircle className="mt-[1px] h-3.5 w-3.5 shrink-0" /> {error}
        </p>
      )}

      {loading && (
        <p className="mt-3 flex items-center gap-2 text-[12px] text-[#5A5F7A]">
          <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> Loading the register&hellip;
        </p>
      )}

      {!loading && !roster && !error && (
        <p className="mt-3 text-[12px] text-[#5A5F7A]">
          Choose a section to open its register.
        </p>
      )}

      {!loading && roster && roster.total === 0 && (
        <p className="mt-3 text-[12px] text-[#B45309]">
          No students are enrolled in that section for {roster.academic_year}.
        </p>
      )}

      {!loading && roster && roster.total > 0 && (
        <>
          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[#DDD6FE] pt-2.5">
            <span className="text-[11.5px] text-[#3A3F58]">
              {roster.total} student{roster.total === 1 ? '' : 's'}
              {roster.already_taken && (
                <span className="ml-1.5 rounded bg-[#EDE9FE] px-1.5 py-0.5 text-[10.5px] text-[#5B21B6]">
                  already taken &mdash; loaded as saved
                </span>
              )}
            </span>
            <span className="ml-auto flex items-center gap-1.5">
              <span className="text-[10.5px] text-[#8A8FA8]">Mark everyone</span>
              {(['present', 'absent'] as const).map((s) => (
                <button key={s} type="button" onClick={() => setAll(s)}
                  className={cn('rounded-md border px-2 py-0.5 text-[10.5px] font-medium capitalize',
                    STATUS_STYLE[s])}>
                  {s}
                </button>
              ))}
            </span>
            <span className="relative">
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Find a student…"
                className="h-7 w-[170px] rounded-lg border border-[#DDE0EE] bg-white pl-2 pr-7 text-[11px] outline-none focus:border-[#4F46E5]" />
              <Search className="absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-[#8A8FA8]" />
            </span>
          </div>

          <ul className="mt-2 max-h-[420px] space-y-1 overflow-y-auto rounded-lg bg-white p-1.5">
            {visible.map((s) => {
              const current = marks[s.student_id] ?? 'present'
              return (
                <li key={s.student_id}
                  className="flex flex-wrap items-center gap-2 rounded-md px-2 py-1.5 hover:bg-[#FAFBFE]">
                  <span className="w-[86px] shrink-0 font-mono text-[11px] text-[#5A5F7A]">
                    {s.roll_number ?? '—'}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[12px] text-[#1B1B3A]">
                    {s.full_name ?? 'Unnamed'}
                  </span>
                  {s.attendance_rate !== null && (
                    <span className={cn('shrink-0 text-[10.5px] tabular-nums',
                      s.below_floor ? 'font-semibold text-[#B91C1C]' : 'text-[#8A8FA8]')}
                      title={s.below_floor ? `Below the ${roster.floor}% floor` : 'Year to date'}>
                      {s.attendance_rate}%
                    </span>
                  )}
                  <span className="flex shrink-0 gap-1">
                    {roster.statuses.map((status) => {
                      const Icon = STATUS_ICON[status.value]
                      const active = current === status.value
                      return (
                        <button key={status.value} type="button"
                          onClick={() => setMarks((m) => ({ ...m, [s.student_id]: status.value }))}
                          aria-pressed={active}
                          aria-label={`${status.label} — ${s.full_name ?? s.roll_number}`}
                          className={cn(
                            'flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10.5px] font-medium transition',
                            active ? STATUS_STYLE[status.value]
                              : 'border-[#EEF0F7] text-[#9CA3AF] hover:border-[#DDE0EE]')}>
                          <Icon className="h-3 w-3" /> {status.label}
                        </button>
                      )
                    })}
                  </span>
                </li>
              )
            })}
            {visible.length === 0 && (
              <li className="px-2 py-4 text-center text-[11.5px] text-[#8A8FA8]">
                Nobody matches &ldquo;{search}&rdquo;.
              </li>
            )}
          </ul>

          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <button type="button" onClick={save} disabled={saving}
              className="flex items-center gap-1.5 rounded-lg bg-[#4F46E5] px-3.5 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
              {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
              Save register
            </button>
            <span className="text-[11.5px] text-[#3A3F58]">
              <span className="text-[#15803D]">{tally.present} present</span>
              {' · '}<span className="text-[#B91C1C]">{tally.absent} absent</span>
              {' · '}<span className="text-[#B45309]">{tally.late} late</span>
            </span>
            <p className="text-[10.5px] text-[#8A8FA8]">
              {search ? 'Saving covers the whole section, not just what is filtered. ' : ''}
              Late counts as attended.
            </p>
          </div>
        </>
      )}
    </section>
  )
}
