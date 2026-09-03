'use client'

import { Suspense, useCallback, useEffect, useMemo, useState  } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Download,
  FileCheck2,
  FolderPlus,
  Loader2,
  Search,
  Plus,
  Send,
  Upload,
  UserPlus,
  Users,
  UserCog,
} from 'lucide-react'
import { PageShell, Pill } from '@/components/faculty/PageShell'
import { StudentRegistrations } from '@/components/faculty/StudentRegistrations'
import { IncompleteRegistrations } from '@/components/faculty/IncompleteRegistrations'
import { ApprovalQueue } from '@/components/faculty/ApprovalQueue'
import { ImportHistory } from '@/components/faculty/ImportHistory'
import {
  errorMessage,
  approveRegistrations,
  assignGuide,
  exportRegistrations,
  fetchFacultyFilters,
  fetchRegistrations,
  type FacultyFilterOptions,
  type RegistrationQuery,
  type RegistrationsView,
} from '@/lib/faculty-api'
import { NewBatchForm } from '@/components/faculty/NewBatchForm'
import { cn } from '@/lib/utils'

const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
const CELL = 'px-2 py-2'

/** Fixed widths for everything except Project Title, which takes the remainder. */
const COL_WIDTHS = ['32px', '84px', 'auto', '52px', '58px', '92px', '78px', '76px', '104px', '62px', '64px']

const TABS = [
  { key: 'batches', label: 'Batch Registrations' },
  { key: 'students', label: 'Student Registrations' },
  { key: 'incomplete', label: 'Incomplete Registrations' },
  { key: 'approval', label: 'Approval Queue' },
  { key: 'imports', label: 'Import History' },
] as const
type TabKey = (typeof TABS)[number]['key']

/**
 * Only the Batch tab uses the batch-list endpoint. Incomplete and Approval
 * each have their own aggregate, so no status mapping is needed for them.
 */
const TAB_STATUS: Partial<Record<TabKey, string>> = {}

const FILTERS = [
  { key: 'department', label: 'Department', all: 'All Departments', from: 'departments' },
  { key: 'year', label: 'Year', all: 'All Years', from: 'years' },
  { key: 'semester', label: 'Semester', all: 'All Semesters', from: 'semesters' },
  { key: 'section', label: 'Section', all: 'All Sections', from: 'sections' },
  { key: 'project_type', label: 'Project Type', all: 'All Types', from: 'project_types' },
] as const

const KPI_TILE: Record<string, string> = {
  students: 'bg-[#6D5AE6]',
  expected: 'bg-[#3B82F6]',
  complete: 'bg-[#16A34A]',
  incomplete: 'bg-[#F59E0B]',
  pending: 'bg-[#EAB308]',
  unbatched: 'bg-[#EF4444]',
}

const KPI_ICON: Record<string, typeof Users> = {
  students: Users,
  expected: FolderPlus,
  complete: CheckCircle2,
  incomplete: AlertTriangle,
  pending: Send,
  unbatched: UserPlus,
}

const STATUS_TONE: Record<string, 'green' | 'amber' | 'red' | 'slate'> = {
  approved: 'green',
  submitted: 'green',
  pending_approval: 'amber',
  changes_requested: 'amber',
  incomplete: 'red',
  draft: 'slate',
}

const PAPER_TONE: Record<string, 'green' | 'amber' | 'red'> = {
  verified: 'green',
  pending: 'amber',
  missing: 'red',
}

const ATTENTION_LINKS: Record<string, string> = {
  unbatched: '/faculty/registrations?tab=students&unbatched=1',
  'short-teams': '/faculty/project-tracking?inactive=1',
  'missing-papers': '/faculty/base-papers?status=missing',
  'no-guide': '/faculty/guides',
  awaiting: '/faculty/registrations?tab=approval',
}

function RegistrationsPageContent() {
  const params = useSearchParams()
  const initialTab = (params.get('tab') as TabKey) || 'batches'

  const [tab, setTab] = useState<TabKey>(TABS.some((t) => t.key === initialTab) ? initialTab : 'batches')
  const [filters, setFilters] = useState<RegistrationQuery>({
    section: params.get('section') ?? undefined,
  })
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)

  const [view, setView] = useState<RegistrationsView | null>(null)
  const [options, setOptions] = useState<FacultyFilterOptions | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [guidePickerOpen, setGuidePickerOpen] = useState(false)
  const [newBatchOpen, setNewBatchOpen] = useState(false)
  const [guideId, setGuideId] = useState('')
  const [busy, setBusy] = useState(false)

  const query: RegistrationQuery = useMemo(
    () => ({ ...filters, reg_status: TAB_STATUS[tab], search: search || undefined, page, per_page: perPage }),
    [filters, tab, search, page, perPage]
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setView(await fetchRegistrations(query))
    } catch (err: any) {
      setError(errorMessage(err, 'Could not load registrations.'))
    } finally {
      setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    fetchFacultyFilters().then(setOptions).catch(() => setOptions(null))
  }, [])

  // Selection is per page of results; a reload invalidates it.
  useEffect(() => setSelected([]), [tab, page, perPage, search, filters])

  const rows = view?.rows ?? []
  const allChecked = rows.length > 0 && selected.length === rows.length
  const toggleAll = () => setSelected(allChecked ? [] : rows.map((r) => r.id))
  const toggleOne = (id: string) =>
    setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))

  const optionsFor = (from: string, all: string) => {
    const values = (options?.[from as keyof FacultyFilterOptions] as string[] | undefined) ?? []
    return [all, ...values]
  }

  const runAssignGuide = async () => {
    if (!guideId || selected.length === 0) return
    setBusy(true)
    try {
      const res = await assignGuide(selected, guideId)
      setNotice(`Assigned a guide to ${res.updated} batch(es).`)
      setGuidePickerOpen(false)
      setGuideId('')
      await load()
    } catch (err: any) {
      setNotice(errorMessage(err, 'Could not assign the guide.'))
    } finally {
      setBusy(false)
    }
  }

  const runApprove = async () => {
    if (selected.length === 0) return
    setBusy(true)
    try {
      const res = await approveRegistrations(selected)
      const skipped = res.skipped.map((s) => `${s.batch_code} (${s.reason})`).join(', ')
      setNotice(
        `Approved ${res.approved.length} batch(es).` + (skipped ? ` Skipped: ${skipped}` : '')
      )
      await load()
    } catch (err: any) {
      setNotice(errorMessage(err, 'Could not approve the selection.'))
    } finally {
      setBusy(false)
    }
  }

  const runExport = async () => {
    setBusy(true)
    try {
      await exportRegistrations({ ...filters, reg_status: TAB_STATUS[tab], search: search || undefined })
      setNotice('Export downloaded.')
    } catch {
      setNotice('Could not export this view.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <PageShell
      title="Student & Batch Registrations"
      subtitle={
        tab === 'imports'
          ? 'Track uploaded files, validation results, imported records and correction history'
          : tab === 'incomplete'
          ? 'Identify and resolve missing student, team, project and base-paper information'
          : tab === 'approval'
            ? 'Verify complete teams, project details and base papers before faculty approval'
            : 'Review student profiles, four-member teams, project titles and base-paper submissions'
      }
      actions={
        <>
          <button
            type="button"
            onClick={() =>
              tab === 'imports'
                ? setNotice('Use "Choose file & import" below to upload a roster.')
                : setNotice('Adding one student at a time needs a create-student endpoint. Bulk import works today - see the Import History tab.')
            }
            className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]"
          >
            <UserPlus className="h-4 w-4" /> Add Student
          </button>
          <button
            type="button"
            onClick={() => setTab('imports')}
            className="flex items-center gap-2 rounded-lg border border-[#C7BDF5] bg-white px-4 py-2 text-[12px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF]"
          >
            <Upload className="h-4 w-4" /> Import Students
          </button>
          <button
            type="button"
            onClick={runExport}
            disabled={busy}
            className="flex items-center gap-2 rounded-lg border border-[#C7BDF5] bg-white px-4 py-2 text-[12px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF] disabled:opacity-50"
          >
            <Download className="h-4 w-4" /> Export Registrations
          </button>
        </>
      }
    >
      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-[#E8E9F2]">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => { setTab(t.key); setPage(1) }}
            className={cn(
              'border-b-2 px-4 py-2 text-[12px] transition-colors',
              tab === t.key
                ? 'border-[#4F46E5] font-medium text-[#4F46E5]'
                : 'border-transparent text-[#5A5F7A] hover:text-[#1B1B3A]'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] px-3 py-2 text-[12px] text-[#3A3F58]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium text-[#4F46E5]">
            Dismiss
          </button>
        </div>
      )}

      {tab === 'students' ? (
        <StudentRegistrations options={options} onNotice={setNotice} />
      ) : tab === 'incomplete' ? (
        <IncompleteRegistrations options={options} onNotice={setNotice} />
      ) : tab === 'approval' ? (
        <ApprovalQueue options={options} onNotice={setNotice} />
      ) : tab === 'imports' ? (
        <ImportHistory options={options} onNotice={setNotice} />
      ) : (
        <>
          {/* Filters + search */}
          <section className={cn(CARD, 'grid grid-cols-2 gap-2.5 p-2.5 md:grid-cols-3 xl:grid-cols-6')}>
            {FILTERS.map((f) => (
              <div key={f.key}>
                <label htmlFor={f.key} className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">{f.label}</label>
                <div className="relative">
                  <select
                    id={f.key}
                    value={(filters as any)[f.key] ?? f.all}
                    onChange={(e) => {
                      const v = e.target.value
                      setFilters((prev) => ({ ...prev, [f.key]: v.startsWith('All ') ? undefined : v }))
                      setPage(1)
                    }}
                    className="h-8 w-full appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]"
                  >
                    {optionsFor(f.from, f.all).map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                  <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
                </div>
              </div>
            ))}
            <div>
              <label htmlFor="search" className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">Search</label>
              <form
                onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1) }}
                className="relative"
              >
                <input
                  id="search"
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Batch code, title, student or roll number…"
                  className="h-8 w-full rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5]"
                />
                <button type="submit" aria-label="Search" className="absolute right-2 top-1/2 -translate-y-1/2">
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
            {/* Main table */}
            <section className={cn(CARD, 'p-4')}>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-[14px] font-semibold text-[#1B1B3A]">Batch Registrations</h2>
                <div className="flex flex-wrap gap-2">
                    <ToolbarButton icon={Plus} label="New Batch" disabled={busy}
                      onClick={() => setNewBatchOpen((v) => !v)} />
                    <ToolbarButton icon={UserCog} label="Assign Guide" disabled={!selected.length || busy}
                      onClick={() => setGuidePickerOpen((v) => !v)} />
                    <ToolbarButton icon={CheckCircle2} label="Approve Selected" disabled={!selected.length || busy}
                      onClick={runApprove} />
                    <ToolbarButton icon={Send} label="Send Reminder" disabled={!selected.length || busy}
                      onClick={() => setNotice('Reminders need an email dispatch pipeline - not wired up, so nothing was sent.')} />
                  <ToolbarButton icon={Download} label="Export" disabled={busy} onClick={runExport} />
                </div>
              </div>

              {newBatchOpen && (
                <NewBatchForm
                  onClose={() => setNewBatchOpen(false)}
                  onCreated={(message) => { setNotice(message); load() }}
                />
              )}

              {guidePickerOpen && (
                <div className="mb-3 flex flex-wrap items-center gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] p-2.5">
                  <span className="text-[12px] text-[#3A3F58]">Assign to {selected.length} batch(es):</span>
                  <select
                    value={guideId}
                    onChange={(e) => setGuideId(e.target.value)}
                    className="h-8 rounded-lg border border-[#DDE0EE] bg-white px-2 text-[12px] outline-none focus:border-[#4F46E5]"
                  >
                    <option value="">Select a guide…</option>
                    {(options?.guides ?? []).map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                  <button
                    type="button"
                    onClick={runAssignGuide}
                    disabled={!guideId || busy}
                    className="rounded-lg bg-[#4F46E5] px-3 py-1.5 text-[12px] font-medium text-white hover:bg-[#4338CA] disabled:opacity-50"
                  >
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
                <p className="py-16 text-center text-[12px] text-[#8A8FA8]">No batches match this view.</p>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full table-fixed border-collapse text-[11.5px]">
                      <colgroup>
                        {COL_WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}
                      </colgroup>
                      <thead>
                        <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                          <th className={cn(CELL, 'text-left')}>
                            <input type="checkbox" checked={allChecked} onChange={toggleAll} aria-label="Select all" />
                          </th>
                          {['Batch Code', 'Project Title', 'Section', 'Members', 'Batch Leader', 'Base Paper', 'Guide', 'Status', 'Updated', 'Action'].map((h, i) => (
                            <th key={h} className={cn(CELL, 'font-medium', i < 2 ? 'text-left' : 'text-center')}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((r) => {
                          const short = r.members < r.team_size
                          return (
                            <tr key={r.id} className="border-b border-[#F1F2F8]">
                              <td className={CELL}>
                                <input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggleOne(r.id)} aria-label={`Select ${r.batch_code}`} />
                              </td>
                              <td className={cn(CELL, 'whitespace-nowrap')}>
                                <Link href={`/faculty/registrations/${encodeURIComponent(r.batch_code)}`}
                                  className="font-medium text-[#4F46E5] hover:underline">{r.batch_code}</Link>
                              </td>
                              <td className={cn(CELL, 'text-[#3A3F58]')}>{r.title ?? '–'}</td>
                              <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.section ?? '–'}</td>
                              <td className={cn(CELL, 'text-center font-medium', short ? 'text-[#DC2626]' : 'text-[#16A34A]')}>
                                {r.members}/{r.team_size}
                              </td>
                              <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{r.batch_leader ?? '–'}</td>
                              <td className={cn(CELL, 'text-center')}>
                                <Pill tone={PAPER_TONE[r.base_paper_status] ?? 'slate'}>{r.base_paper}</Pill>
                              </td>
                              <td className={cn(CELL, 'text-center text-[#3A3F58]')}>
                                {r.guide ?? <span className="text-[#8A8FA8]">Not Assigned</span>}
                              </td>
                              <td className={cn(CELL, 'text-center')}>
                                <Pill tone={STATUS_TONE[r.status_key] ?? 'slate'}>{r.status}</Pill>
                              </td>
                              <td className={cn(CELL, 'whitespace-nowrap text-center text-[#5A5F7A]')}>
                                {new Date(r.last_updated).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                              </td>
                              <td className={cn(CELL, 'text-center')}>
                                <Link href={`/faculty/registrations/${encodeURIComponent(r.batch_code)}`} className="font-medium text-[#4F46E5] hover:underline">
                                  {r.status_key === 'incomplete' || r.status_key === 'draft' ? 'Complete' : r.status_key === 'pending_approval' || r.status_key === 'changes_requested' ? 'Review' : 'View'}
                                </Link>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-[11px] text-[#8A8FA8]">
                      Showing {view?.showing_from} to {view?.showing_to} of {view?.total} entries
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center gap-1.5">
                        <PagerButton onClick={() => setPage((p) => p - 1)} disabled={(view?.page ?? 1) <= 1} aria-label="Previous page">
                          <ChevronLeft className="h-3.5 w-3.5" />
                        </PagerButton>
                        {Array.from({ length: view?.pages ?? 1 }, (_, i) => i + 1)
                          .filter((n) => Math.abs(n - (view?.page ?? 1)) < 3 || n === 1 || n === view?.pages)
                          .map((n) => (
                            <button key={n} type="button" onClick={() => setPage(n)}
                              className={cn('h-7 min-w-[28px] rounded-md border px-1.5 text-[11px]',
                                n === view?.page ? 'border-[#4F46E5] bg-[#4F46E5] font-medium text-white' : 'border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC]')}>
                              {n}
                            </button>
                          ))}
                        <PagerButton onClick={() => setPage((p) => p + 1)} disabled={(view?.page ?? 1) >= (view?.pages ?? 1)} aria-label="Next page">
                          <ChevronRight className="h-3.5 w-3.5" />
                        </PagerButton>
                      </div>
                      <select
                        value={perPage}
                        onChange={(e) => { setPerPage(Number(e.target.value)); setPage(1) }}
                        aria-label="Rows per page"
                        className="h-7 rounded-md border border-[#DDE0EE] bg-white px-2 text-[11px] outline-none focus:border-[#4F46E5]"
                      >
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
                <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Registration Attention Required</h2>
                <ul className="space-y-1.5">
                  {(view?.attention_items ?? []).map((a) => (
                    <li key={a.id} className="flex items-center gap-2 rounded-lg border border-[#EEF0F7] px-2 py-1.5">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[#EEF0F7] text-[#5A5F7A]">
                        <Users className="h-3.5 w-3.5" />
                      </span>
                      <span className="flex-1 text-[11px] leading-tight text-[#3A3F58]">{a.label}</span>
                      <span className="text-[14px] font-semibold text-[#4F46E5]">{a.count}</span>
                      <Link href={ATTENTION_LINKS[a.id] ?? '/faculty/registrations'} className="text-[11px] font-medium text-[#4F46E5] hover:underline">
                        View
                      </Link>
                    </li>
                  ))}
                </ul>
              </section>

              <section className={cn(CARD, 'p-4')}>
                <h2 className="mb-2 text-[14px] font-semibold text-[#1B1B3A]">Registration Progress</h2>
                <ul className="space-y-2">
                  {(view?.progress ?? []).map((p) => (
                    <li key={p.label} className="flex items-center gap-2.5">
                      <span className="w-[92px] shrink-0 text-[10.5px] leading-tight text-[#3A3F58]">{p.label}</span>
                      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-[#EEF0F7]">
                        <span
                          className="block h-full rounded-full bg-[#4F46E5]"
                          style={{ width: `${p.total ? (p.done / p.total) * 100 : 0}%` }}
                        />
                      </span>
                      <span className="w-[54px] shrink-0 whitespace-nowrap text-right text-[10.5px] text-[#5A5F7A]">
                        {p.done} / {p.total}
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
              <QuickAction icon={FolderPlus} label="Create Batch"
                onClick={() => setNotice('Creating a batch needs a create-batch endpoint - not built yet.')} />
              <QuickAction icon={Users} label="Assign Students"
                onClick={() => setNotice('Assigning students to a batch needs a membership endpoint - not built yet.')} />
              <QuickAction icon={FileCheck2} label="Verify Base Papers" href="/faculty/base-papers?status=pending" />
              <QuickAction icon={UserCog} label="Assign Faculty Guide"
                onClick={() => { setTab('batches'); setGuidePickerOpen(true); setNotice('Select batches in the table, then choose a guide.') }} />
              <QuickAction icon={Send} label="Send Registration Reminder"
                onClick={() => setNotice('Reminders need an email dispatch pipeline - not wired up, so nothing was sent.')} />
            </div>
          </section>
        </>
      )}
    </PageShell>
  )
}

function ToolbarButton({ icon: Icon, label, onClick, disabled }: {
  icon: typeof Users; label: string; onClick: () => void; disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] bg-white px-3 py-1.5 text-[11.5px] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-white"
    >
      <Icon className="h-3.5 w-3.5" /> {label}
    </button>
  )
}

function PagerButton({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-transparent"
    >
      {children}
    </button>
  )
}

function QuickAction({ icon: Icon, label, onClick, href }: {
  icon: typeof Users; label: string; onClick?: () => void; href?: string
}) {
  const cls = 'flex items-center gap-2 rounded-lg border border-[#EEF0F7] px-3 py-2 text-[12px] text-[#3A3F58] hover:bg-[#F7F8FC]'
  const body = (<><Icon className="h-4 w-4 text-[#4F46E5]" /> {label}</>)
  return href
    ? <Link href={href} className={cls}>{body}</Link>
    : <button type="button" onClick={onClick} className={cls}>{body}</button>
}

/**
 * useSearchParams() opts the tree out of static rendering, and Next 14
 * fails the production build unless that bail-out sits behind a Suspense
 * boundary. Without this the page compiles in dev and breaks `next build`.
 */
export default function RegistrationsPage() {
  return (
    <Suspense fallback={<PageShell title="Registrations" subtitle="Loading…">{null}</PageShell>}>
      <RegistrationsPageContent />
    </Suspense>
  )
}
