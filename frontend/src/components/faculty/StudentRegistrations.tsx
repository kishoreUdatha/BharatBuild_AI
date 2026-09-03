'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  AlertTriangle,
  BadgeCheck,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Copy,
  Download,
  FileText,
  Loader2,
  Mail,
  Search,
  Send,
  ShieldCheck,
  UserPlus,
  Users,
} from 'lucide-react'
import { Pill } from '@/components/faculty/PageShell'
import {
  errorMessage,
  assignStudentsToBatch,
  exportStudentRegistrations,
  fetchBatches,
  fetchStudentRegistrations,
  verifyStudents,
  type BatchRow,
  type FacultyFilterOptions,
  type StudentQuery,
  type StudentRegistrationsView,
} from '@/lib/faculty-api'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
const CELL = 'px-2 py-2'

/**
 * Fixed widths for everything except Student, which takes the remainder.
 * Profile Status needs 118px or the "Verification Pending" pill runs into the
 * Action column; Email is pinned so it does not compete for the same slack.
 */
const COL_WIDTHS = ['30px', 'auto', '84px', '48px', '48px', '88px', '132px', '84px', '70px', '118px', '56px']

const KPI_TILE: Record<string, string> = {
  total: 'bg-[#6D5AE6]',
  profiles: 'bg-[#3B82F6]',
  joined: 'bg-[#16A34A]',
  unbatched: 'bg-[#EF4444]',
  pending: 'bg-[#F59E0B]',
  duplicates: 'bg-[#DC2626]',
}

const KPI_ICON: Record<string, typeof Users> = {
  total: Users,
  profiles: BadgeCheck,
  joined: CheckCircle2,
  unbatched: UserPlus,
  pending: ShieldCheck,
  duplicates: Copy,
}

const ATTENTION_ICON: Record<string, typeof Users> = {
  unbatched: UserPlus,
  pending: ShieldCheck,
  contact: Mail,
  duplicates: Copy,
  invites: Send,
}

const PROFILE_TONE: Record<string, 'green' | 'amber' | 'red'> = {
  verified: 'green',
  verification_pending: 'amber',
  profile_incomplete: 'red',
}

const BATCH_STATUSES = [
  { key: '', label: 'All' },
  { key: 'in_batch', label: 'In a batch' },
  { key: 'not_in_batch', label: 'Not in a batch' },
]

const FILTERS = [
  { key: 'department', label: 'Department', all: 'All Departments', from: 'departments' },
  { key: 'year', label: 'Year', all: 'All Years', from: 'years' },
  { key: 'semester', label: 'Semester', all: 'All Semesters', from: 'semesters' },
  { key: 'section', label: 'Section', all: 'All Sections', from: 'sections' },
] as const

/** Initials stand in for the photo the design shows; no avatars are stored. */
function Avatar({ name }: { name: string | null }) {
  const initials = (name ?? '?')
    .split(' ')
    .map((p) => p[0])
    .slice(-2)
    .join('')
    .toUpperCase()
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#DDE3F7] text-[9px] font-semibold text-[#2C2A6B]">
      {initials}
    </span>
  )
}

export function StudentRegistrations({
  options,
  onNotice,
}: {
  options: FacultyFilterOptions | null
  onNotice: (message: string) => void
}) {
  const [filters, setFilters] = useState<StudentQuery>({})
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const [view, setView] = useState<StudentRegistrationsView | null>(null)
  const [batches, setBatches] = useState<BatchRow[]>([])
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [batchPickerOpen, setBatchPickerOpen] = useState(false)
  const [batchId, setBatchId] = useState('')

  const query: StudentQuery = useMemo(
    () => ({ ...filters, search: search || undefined, page, per_page: perPage }),
    [filters, search, page, perPage]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setView(await fetchStudentRegistrations(query))
    } catch (err: any) {
      setError(errorMessage(err, 'Could not load student registrations.'))
    } finally {
      setLoading(false)
    }
  }, [query])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    fetchBatches({ limit: 200 }).then((r) => setBatches(r.items)).catch(() => setBatches([]))
  }, [])
  useEffect(() => setSelected([]), [page, perPage, search, filters])

  const rows = view?.rows ?? []
  const allChecked = rows.length > 0 && selected.length === rows.length
  const toggleAll = () => setSelected(allChecked ? [] : rows.map((r) => r.id))
  const toggleOne = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  const optionsFor = (from: string, all: string) =>
    [all, ...(((options?.[from as keyof FacultyFilterOptions] as string[] | undefined) ?? []))]

  const runVerify = async () => {
    if (!selected.length) return
    setBusy(true)
    try {
      const res = await verifyStudents(selected)
      const skipped = res.skipped.map((s) => `${s.roll_number} (${s.reason})`).join(', ')
      onNotice(`Verified ${res.verified.length} profile(s).` + (skipped ? ` Skipped: ${skipped}` : ''))
      await load()
    } catch (err: any) {
      onNotice(errorMessage(err, 'Could not verify the selection.'))
    } finally {
      setBusy(false)
    }
  }

  const runAssign = async () => {
    if (!batchId || !selected.length) return
    setBusy(true)
    try {
      const res = await assignStudentsToBatch(selected, batchId)
      onNotice(
        `Added ${res.added} student(s) to ${res.batch_code}.` +
          (res.skipped.length ? ` Skipped ${res.skipped.length} already in that batch.` : '')
      )
      setBatchPickerOpen(false)
      setBatchId('')
      await load()
    } catch (err: any) {
      onNotice(errorMessage(err, 'Could not assign the students.'))
    } finally {
      setBusy(false)
    }
  }

  const runExport = async () => {
    setBusy(true)
    try {
      await exportStudentRegistrations({ ...filters, search: search || undefined })
      onNotice('Student list downloaded.')
    } catch {
      onNotice('Could not export the student list.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {/* Filters + search */}
      <section className={cn(CARD, 'grid grid-cols-2 gap-2.5 p-2.5 md:grid-cols-3 xl:grid-cols-7')}>
        {FILTERS.map((f) => (
          <div key={f.key}>
            <label htmlFor={`s-${f.key}`} className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">{f.label}</label>
            <SelectShell>
              <select
                id={`s-${f.key}`}
                value={(filters as any)[f.key] ?? f.all}
                onChange={(e) => {
                  const v = e.target.value
                  setFilters((prev) => ({ ...prev, [f.key]: v.startsWith('All ') ? undefined : v }))
                  setPage(1)
                }}
                className={SELECT_CLASS}
              >
                {optionsFor(f.from, f.all).map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </SelectShell>
          </div>
        ))}

        <div>
          <label htmlFor="batch_status" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Batch Status</label>
          <SelectShell>
            <select
              id="batch_status"
              value={filters.batch_status ?? ''}
              onChange={(e) => { setFilters((p) => ({ ...p, batch_status: e.target.value || undefined })); setPage(1) }}
              className={SELECT_CLASS}
            >
              {BATCH_STATUSES.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </SelectShell>
        </div>

        <div>
          <label htmlFor="profile_status" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Profile Status</label>
          <SelectShell>
            <select
              id="profile_status"
              value={filters.profile_status ?? ''}
              onChange={(e) => { setFilters((p) => ({ ...p, profile_status: e.target.value || undefined })); setPage(1) }}
              className={SELECT_CLASS}
            >
              <option value="">All Statuses</option>
              {(view?.profile_statuses ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
            </select>
          </SelectShell>
        </div>

        <div>
          <label htmlFor="s-search" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Search</label>
          <form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1) }} className="relative">
            <input
              id="s-search"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Name, roll, email, mobile or batch…"
              className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]"
            />
            <button type="submit" aria-label="Search students" className="absolute right-2 top-1/2 -translate-y-1/2">
              <Search className="h-3.5 w-3.5 text-[#8A8FA8]" />
            </button>
          </form>
        </div>
      </section>

      {/* KPI row */}
      <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
        {(view?.kpis ?? []).map((k) => {
          const Icon = KPI_ICON[k.id] ?? Users
          return (
            <div key={k.id} className={cn(CARD, 'flex items-center gap-2.5 p-2')}>
              <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl', KPI_TILE[k.id])}>
                <Icon className="h-4 w-4 text-white" />
              </span>
              <div className="min-w-0">
                <p className="text-[19px] font-bold leading-none text-[#1B1B3A]">{k.value}</p>
                <p className="mt-0.5 text-[11px] leading-tight text-[#5A5F7A]">{k.label}</p>
              </div>
            </div>
          )
        })}
      </section>

      <div className="grid gap-2.5 xl:grid-cols-[minmax(0,2.6fr)_minmax(0,1fr)]">
        <section className={cn(CARD, 'p-4')}>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Student Registrations</h2>
            <div className="flex flex-wrap gap-2">
              <Toolbar icon={Users} label="Assign to Batch" disabled={!selected.length || busy}
                onClick={() => setBatchPickerOpen((v) => !v)} />
              <Toolbar icon={CheckCircle2} label="Verify Selected" disabled={!selected.length || busy} onClick={runVerify} />
              <Toolbar icon={Send} label="Send Reminder" disabled={!selected.length || busy}
                onClick={() => onNotice('Reminders need an email dispatch pipeline - not wired up, so nothing was sent.')} />
              <Toolbar icon={Download} label="Export" disabled={busy} onClick={runExport} />
            </div>
          </div>

          {batchPickerOpen && (
            <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-2.5">
              <span className="text-[12px] text-[#3A3F58]">Add {selected.length} student(s) to:</span>
              <select value={batchId} onChange={(e) => setBatchId(e.target.value)}
                className="h-8 rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]">
                <option value="">Select a batch…</option>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.batch_code} — {b.title ?? 'Untitled'} ({b.member_count} members)
                  </option>
                ))}
              </select>
              <button type="button" onClick={runAssign} disabled={!batchId || busy}
                className="rounded-lg bg-[#4F46E5] px-3 py-1.5 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50">
                Assign
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex h-[260px] items-center justify-center gap-2 text-[#5A5F7A]">
              <Loader2 className="h-4 w-4 animate-spin text-[#4F46E5]" /> <span className="text-[12px]">Loading…</span>
            </div>
          ) : error ? (
            <div className="flex h-[260px] flex-col items-center justify-center gap-3">
              <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
              <p className="text-[12px] text-[#5A5F7A]">{error}</p>
              <button type="button" onClick={load} className="rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white">Retry</button>
            </div>
          ) : rows.length === 0 ? (
            <p className="py-16 text-center text-[12px] text-[#8A8FA8]">No students match this view.</p>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full table-fixed border-collapse text-[11.5px]">
                  <colgroup>{COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
                  <thead>
                    <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                      <th className={cn(CELL, 'text-left')}>
                        <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Select all students" />
                      </th>
                      {['Student', 'Roll Number', 'Dept', 'Section', 'Mobile', 'Email', 'Batch Code', 'Role', 'Profile Status', 'Action'].map((h, i) => (
                        <th key={h} className={cn(CELL, 'font-medium', i === 0 ? 'text-left' : 'text-center')}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr key={r.id} className="border-b border-[#F1F2F8]">
                        <td className={CELL}>
                          <input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggleOne(r.id)}
                            aria-label={`Select ${r.roll_number ?? r.email}`} />
                        </td>
                        <td className={CELL}>
                          <span className="flex items-center gap-2">
                            <Avatar name={r.full_name} />
                            <span className="truncate text-[#1B1B3A]" title={r.full_name ?? undefined}>{r.full_name ?? '–'}</span>
                          </span>
                        </td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.roll_number ?? '–'}</td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.department}</td>
                        <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.section ?? '–'}</td>
                        <td className={cn(CELL, 'text-center')}>
                          {r.mobile ?? <span className="text-[#DC2626]">Missing</span>}
                        </td>
                        <td className={cn(CELL, 'truncate text-center text-[#3A3F58]')} title={r.email}>{r.email}</td>
                        <td className={cn(CELL, 'text-center')}>
                          {r.batch_code ?? <span className="text-[#DC2626]">Not Joined</span>}
                        </td>
                        <td className={cn(CELL, 'whitespace-nowrap text-center text-[10.5px] text-[#3A3F58]')}>{r.role ?? '—'}</td>
                        <td className={cn(CELL, 'text-center')}>
                          <Pill tone={PROFILE_TONE[r.profile_status_key] ?? 'slate'}>{r.profile_status}</Pill>
                        </td>
                        <td className={cn(CELL, 'text-center')}>
                          {r.batch_code ? (
                            <Link href={`/faculty/project-tracking?batch=${encodeURIComponent(r.batch_code)}`}
                              className="font-medium text-[#4F46E5] hover:underline">
                              View
                            </Link>
                          ) : (
                            <button type="button" onClick={() => { toggleOne(r.id); setBatchPickerOpen(true) }}
                              className="font-medium text-[#4F46E5] hover:underline">
                              Assign
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-[11px] text-[#8A8FA8]">
                  Showing {view?.showing_from} to {view?.showing_to} of {view?.total} students
                </p>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <Pager onClick={() => setPage((p) => p - 1)} disabled={(view?.page ?? 1) <= 1} aria-label="Previous page">
                      <ChevronLeft className="h-3.5 w-3.5" />
                    </Pager>
                    {pageWindow(view?.page ?? 1, view?.pages ?? 1).map((n, i) =>
                      n === null ? (
                        <span key={`gap-${i}`} className="px-1 text-[11px] text-[#8A8FA8]">…</span>
                      ) : (
                        <button key={n} type="button" onClick={() => setPage(n)}
                          className={cn('h-7 min-w-[28px] rounded-md border px-1.5 text-[11px]',
                            n === view?.page ? 'border-[#4F46E5] bg-[#4F46E5] font-medium text-white' : 'border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC]')}>
                          {n}
                        </button>
                      )
                    )}
                    <Pager onClick={() => setPage((p) => p + 1)} disabled={(view?.page ?? 1) >= (view?.pages ?? 1)} aria-label="Next page">
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Pager>
                  </div>
                  <select value={perPage} onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
                    aria-label="Students per page"
                    className="h-7 rounded-md border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]">
                    {[10, 25, 50].map((n) => <option key={n} value={n}>{n} per page</option>)}
                  </select>
                </div>
              </div>
            </>
          )}
        </section>

        {/* Right column */}
        <div className="space-y-2.5">
          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Student Attention Required</h2>
            <ul className="space-y-1.5">
              {(view?.attention_items ?? []).map((a) => {
                const Icon = ATTENTION_ICON[a.id] ?? Users
                return (
                  <li key={a.id} className="flex items-center gap-2 rounded-lg border border-[#EEF0F7] px-2 py-1.5">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[#EEF0F7] text-[#5A5F7A]">
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <span className="flex-1 text-[11px] leading-tight text-[#3A3F58]">{a.label}</span>
                    <span className="text-[14px] font-semibold text-[#4F46E5]">{a.count}</span>
                    <button type="button" onClick={() => applyAttention(a.id, setFilters, setPage, onNotice)}
                      className="text-[11px] font-medium text-[#4F46E5] hover:underline">
                      View
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>

          <section className={cn(CARD, 'p-4')}>
            <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Profile Completion</h2>
            <ul className="space-y-2">
              {(view?.completion ?? []).map((c) => (
                <li key={c.label} className="flex items-center gap-2.5">
                  <span className="w-[92px] shrink-0 text-[10.5px] leading-tight text-[#3A3F58]">{c.label}</span>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F7]">
                    <span className="block h-full rounded-full bg-[#4F46E5]"
                      style={{ width: `${c.total ? (c.done / c.total) * 100 : 0}%` }} />
                  </span>
                  <span className="w-[54px] shrink-0 whitespace-nowrap text-right text-[10.5px] text-[#5A5F7A]">
                    {c.done} / {c.total}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>

      {/* Quick actions */}
      <section className={cn(CARD, 'p-3')}>
        <h2 className="mb-2 text-[13px] font-semibold text-[#1B1B3A]">Quick Actions</h2>
        <div className="flex flex-wrap items-center gap-2">
          <Quick icon={UserPlus} label="Add Individual Student"
            onClick={() => onNotice('Adding a student needs a create-student endpoint - not built yet.')} />
          <Quick icon={FileText} label="Import Student List"
            onClick={() => onNotice('Bulk import needs an upload endpoint that parses and validates a roster - not built yet.')} />
          <Quick icon={Users} label="Assign Students to Batch"
            onClick={() => { setBatchPickerOpen(true); onNotice('Select students in the table, then choose a batch.') }} />
          <Quick icon={Send} label="Resend Batch Invitations"
            onClick={() => onNotice('Invitations need an email dispatch pipeline - not wired up, so nothing was sent.')} />
          <Quick icon={Download} label="Download Student Report" onClick={runExport} />
        </div>
      </section>
    </>
  )
}

const SELECT_CLASS =
  'h-8 w-full appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]'

function SelectShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      {children}
      <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
    </div>
  )
}

/** 1 … 5 6 7 … 40 - keeps the pager short when there are 40 pages. */
function pageWindow(current: number, pages: number): (number | null)[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1)
  const out: (number | null)[] = [1]
  const from = Math.max(2, current - 1)
  const to = Math.min(pages - 1, current + 1)
  if (from > 2) out.push(null)
  for (let n = from; n <= to; n++) out.push(n)
  if (to < pages - 1) out.push(null)
  out.push(pages)
  return out
}

/** Attention rows re-filter this tab rather than navigating away. */
function applyAttention(
  id: string,
  setFilters: (fn: (p: StudentQuery) => StudentQuery) => void,
  setPage: (n: number) => void,
  onNotice: (m: string) => void
) {
  setPage(1)
  if (id === 'unbatched') setFilters((p) => ({ ...p, batch_status: 'not_in_batch', profile_status: undefined }))
  else if (id === 'pending') setFilters((p) => ({ ...p, profile_status: 'verification_pending', batch_status: undefined }))
  else if (id === 'contact') onNotice('Students missing a mobile or email show "Missing" in the Mobile column.')
  else if (id === 'duplicates') onNotice('Duplicate roll numbers are counted across the filtered set; there are none right now.')
  else if (id === 'invites') onNotice('Invitation state is tracked per enrollment; resending needs the email pipeline.')
}

function Toolbar({ icon: Icon, label, onClick, disabled }: {
  icon: typeof Users; label: string; onClick: () => void; disabled?: boolean
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] bg-white px-3 py-1.5 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-white">
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  )
}

function Pager({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button type="button" {...props}
      className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-transparent">
      {children}
    </button>
  )
}

function Quick({ icon: Icon, label, onClick }: { icon: typeof Users; label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className="flex items-center gap-2 rounded-lg border border-[#EEF0F7] px-3 py-2 text-[12px] text-[#3A3F58] hover:bg-[#F7F8FC]">
      <Icon className="h-4 w-4 text-[#4F46E5]" /> {label}
    </button>
  )
}
