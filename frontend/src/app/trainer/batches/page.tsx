'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  CalendarDays, CheckCircle2, ChevronDown, ChevronLeft, ChevronRight, ChevronUp, Clock,
  Download, Eye, FileSpreadsheet, Layers, Loader2, MoreVertical, Pencil, Play, Plus,
  Undo2,
  Search, SlidersHorizontal, Upload, Users, X,
} from 'lucide-react'
import { CARD, Chip, Empty, Failed, Loading } from '@/components/trainer/primitives'
import {
  createTrainerBatches, decideRegistration, downloadSampleSheet, errorText,
  exportMyBatches,
  fetchMyBatches, fetchTrainerCapabilities, importBatchAllocation,
} from '@/lib/trainer-api'
import type { BatchCard, BatchListView, BatchQuery, TrainerCapabilities } from '@/lib/trainer-api'
import { cn } from '@/lib/utils'

const YEARS = ['1st Year', '2nd Year', '3rd Year', '4th Year']
const SEMESTERS = ['I', 'II']
const PAGE_SIZES = [10, 25, 50]
const SORTS = [
  { value: 'latest', label: 'Latest Created' },
  { value: 'oldest', label: 'Oldest Created' },
  { value: 'code', label: 'Project ID' },
  { value: 'progress', label: 'Progress' },
  { value: 'students', label: 'Students' },
]

const BTN = 'inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-[12.5px] font-medium ' +
  'disabled:cursor-not-allowed disabled:opacity-50'
const BTN_OUTLINE = `${BTN} border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]`
const BTN_PRIMARY = `${BTN} bg-[#2563EB] text-white hover:bg-[#1D4ED8]`
const FIELD = 'h-9 w-full rounded-lg border border-[#D1D5DB] bg-white px-2.5 text-[12.5px] ' +
  'text-[#374151] outline-none focus:border-[#2563EB]'
const LABEL = 'block text-[11.5px] font-medium text-[#374151]'

const NO_AUTHORITY = 'Requires department coordinator access'
const EMPTY: BatchQuery = { sort: 'latest', page: 1, per_page: 10 }

const fmtDate = (iso: string | null) => {
  if (!iso) return null
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return null
  return {
    day: d.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' }),
    time: d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' }),
  }
}

/** Initials for a student's circle: from the name, or the roll if unnamed. */
const initialsOf = (name: string | null, roll: string) => {
  const parts = (name || '').trim().split(/\s+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (roll || '??').replace(/[^A-Za-z0-9]/g, '').slice(-2).toUpperCase()
}

export default function MyBatchesPage() {
  const router = useRouter()
  const [data, setData] = useState<BatchListView | null>(null)
  const [caps, setCaps] = useState<TrainerCapabilities | null>(null)
  const [error, setError] = useState('')

  // `query` is what has been applied; `draft` is what the panel holds. Keeping
  // them apart is what makes "Apply Filters" mean something.
  const [query, setQuery] = useState<BatchQuery>(EMPTY)
  const [draft, setDraft] = useState<BatchQuery>(EMPTY)
  const [showFilters, setShowFilters] = useState(false)
  const [showMore, setShowMore] = useState(false)

  const [busy, setBusy] = useState<'export' | 'import' | 'create' | null>(null)
  const [notice, setNotice] = useState<{ tone: 'ok' | 'bad'; text: string } | null>(null)
  const [sendBack, setSendBack] = useState<BatchCard | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    setError('')
    try { setData(await fetchMyBatches(query)) }
    catch (err: any) { setError(errorText(err, 'Could not load your batches.')) }
  }, [query])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    fetchTrainerCapabilities().then(setCaps).catch(() => setCaps(null))
  }, [])

  const canManage = caps?.can_manage_department ?? false
  // How many filters are actually narrowing the list, so the button can say so
  // while the panel is shut. Paging and sorting are not filters.
  const activeCount = (['search', 'department', 'section', 'batch_no', 'project_status',
    'semester', 'guide', 'batch_type', 'date_from', 'date_to'] as const)
    .filter((k) => query[k]).length
  const set = (patch: Partial<BatchQuery>) => setDraft((d) => ({ ...d, ...patch }))
  // Sort and page size are how the list is *presented*, not what it contains,
  // and they live outside the panel - so applying or clearing filters must
  // carry them over. Replacing the whole query with `draft` silently reset the
  // sort to Latest Created every time Apply was pressed.
  const apply = () => {
    setQuery((q) => ({ ...draft, sort: q.sort, per_page: q.per_page, page: 1 }))
    setShowFilters(false)
  }
  const clearAll = () => {
    setDraft(EMPTY)
    setQuery((q) => ({ ...EMPTY, sort: q.sort, per_page: q.per_page }))
  }
  const goPage = (page: number) => setQuery((q) => ({ ...q, page }))

  const onExport = async () => {
    setBusy('export'); setNotice(null)
    try {
      await exportMyBatches(query.search, data?.academic_year)
      setNotice({ tone: 'ok', text: 'Export downloaded to your Downloads folder.' })
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'Could not export your batches.') })
    } finally { setBusy(null) }
  }

  const onImport = async (file: File) => {
    setBusy('import'); setNotice(null)
    try {
      const r = await importBatchAllocation(file)
      setShowImport(false)
      if (r.id) { router.push(`/trainer/imports/${r.id}`); return }
      await load()
    } catch (err: any) {
      setNotice({ tone: 'bad', text: errorText(err, 'The import could not be processed.') })
    } finally {
      setBusy(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  if (error) return <Failed message={error} onRetry={load} />
  if (!data) return <Loading label="Loading your batches…" />

  const stats = data.stats
  const from = data.total === 0 ? 0 : (data.page - 1) * data.per_page + 1
  const to = Math.min(data.page * data.per_page, data.total)

  return (
    <div className="space-y-3">
      {/* --------------------------------------------------------- header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-bold leading-tight text-[#1B1B3A]">My Batches</h1>
          <p className="mt-0.5 text-[12.5px] text-[#6B7280]">
            View and manage all your project batches.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" disabled={!canManage || busy !== null}
            onClick={() => setShowImport(true)}
            title={canManage ? 'Upload a batch allocation sheet' : NO_AUTHORITY}
            className={BTN_OUTLINE}>
            {busy === 'import'
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Upload className="h-4 w-4" />}
            Import Batches
          </button>
          <button type="button" onClick={onExport} disabled={busy !== null} className={BTN_OUTLINE}>
            {busy === 'export'
              ? <Loader2 className="h-4 w-4 animate-spin" />
              : <Download className="h-4 w-4" />}
            Export
          </button>
          <button type="button" onClick={() => setShowFilters(true)} className={BTN_OUTLINE}>
            <SlidersHorizontal className="h-4 w-4" /> Filters
            {activeCount > 0 && (
              <span className="ml-0.5 rounded-full bg-[#2563EB] px-1.5 text-[10px] font-semibold text-white">
                {activeCount}
              </span>
            )}
          </button>
          <button type="button" disabled={!canManage || busy !== null}
            onClick={() => setShowCreate(true)}
            title={canManage ? 'Form new batches for a section' : NO_AUTHORITY}
            className={BTN_PRIMARY}>
            <Plus className="h-4 w-4" /> Create Batch
          </button>
          <input ref={fileRef} type="file" accept=".csv,.xlsx" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onImport(f) }} />
        </div>
      </div>

      {!canManage && caps && (
        <p className="text-[11.5px] text-[#6B7280]">
          Import Batches and Create Batch need department coordinator access. You can still export.
        </p>
      )}

      {notice && (
        <div className={cn('flex items-start justify-between gap-3 rounded-lg border px-3 py-2 text-[12px]',
          notice.tone === 'ok'
            ? 'border-[#BBF7D0] bg-[#F0FDF4] text-[#166534]'
            : 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]')}>
          <span>{notice.text}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* ------------------------------------------------------------ KPIs */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Stat icon={<Layers className="h-4 w-4" />} tone="violet" label="Total Batches"
          value={stats.total_batches} hint="All time" />
        <Stat icon={<Play className="h-4 w-4" />} tone="green" label="Active Batches"
          value={stats.active_batches} hint="Currently running" />
        <Stat icon={<CheckCircle2 className="h-4 w-4" />} tone="blue" label="Completed Batches"
          value={stats.completed_batches} hint="Successfully completed" />
        <Stat icon={<Clock className="h-4 w-4" />} tone="amber" label="Pending Reviews"
          value={stats.pending_reviews} hint="Awaiting review" />
        <Stat icon={<Users className="h-4 w-4" />} tone="violet" label="Total Students"
          value={stats.total_students} hint="Across all batches" />
      </div>

      {/* ------------------------------------------------------ batch list */}
      <div className={cn(CARD, 'p-4')}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-[14px] font-bold text-[#1B1B3A]">Batch List ({data.total})</h2>
          <label className="flex items-center gap-2 text-[11.5px] text-[#6B7280]">
            Sort by:
            <select value={query.sort ?? 'latest'} aria-label="Sort batches"
              onChange={(e) => setQuery((q) => ({ ...q, sort: e.target.value, page: 1 }))}
              className={cn(FIELD, 'h-8 w-auto')}>
              {SORTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        </div>

        {data.rows.length === 0 ? (
          <Empty message="No batches match these filters." />
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[980px] text-left text-[12px]">
              <thead>
                <tr className="border-y border-[#E5E7EB] bg-[#FAFBFF] text-[11.5px] text-[#374151]">
                  {['Project ID', 'Tentative Title', 'Batch No', 'Section', 'Guide', 'Students',
                    'Status', 'Progress', 'Created On', 'Actions'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2.5 font-bold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F1F2F8]">
                {data.rows.map((b) => (
                  <BatchRow key={b.id} batch={b} onSendBack={setSendBack} />
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-[#F1F2F8] pt-3">
          <p className="text-[11.5px] text-[#6B7280]">
            Showing {from} to {to} of {data.total} results
          </p>
          <div className="flex items-center gap-1.5">
            <PageBtn onClick={() => goPage(data.page - 1)} disabled={data.page <= 1}
              label="Previous page"><ChevronLeft className="h-3.5 w-3.5" /></PageBtn>
            {pageWindow(data.page, data.pages).map((n) => (
              <button key={n} type="button" onClick={() => goPage(n)}
                aria-current={n === data.page ? 'page' : undefined}
                className={cn('h-7 min-w-[28px] rounded-lg px-2 text-[11.5px] font-medium',
                  n === data.page
                    ? 'bg-[#2563EB] text-white'
                    : 'border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB]')}>
                {n}
              </button>
            ))}
            <PageBtn onClick={() => goPage(data.page + 1)} disabled={data.page >= data.pages}
              label="Next page"><ChevronRight className="h-3.5 w-3.5" /></PageBtn>
            <select value={data.per_page} aria-label="Rows per page"
              onChange={(e) => setQuery((q) => ({ ...q, per_page: Number(e.target.value), page: 1 }))}
              className={cn(FIELD, 'ml-1 h-7 w-auto')}>
              {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
            </select>
          </div>
        </div>
      </div>


      {/* --------------------------------------------------- filter panel */}
      {showFilters && (
        <div className="fixed inset-0 z-[60] flex justify-end" role="dialog" aria-modal="true"
          aria-label="Filter batches">
          {/* The backdrop closes the panel. The panel is a sibling, not a
              child, so a click inside it never reaches the backdrop. */}
          <div className="absolute inset-0 bg-black/30" onClick={() => setShowFilters(false)} />
          <aside className="relative flex h-full w-full max-w-[340px] flex-col bg-white shadow-xl">
            <header className="flex items-center justify-between border-b border-[#E5E7EB] px-4 py-3">
              <div>
                <h2 className="text-[14px] font-bold text-[#1B1B3A]">Filters</h2>
                <p className="text-[11px] text-[#6B7280]">
                  {activeCount === 0 ? 'Nothing applied' : activeCount + ' applied'}
                </p>
              </div>
              <button type="button" onClick={() => setShowFilters(false)} aria-label="Close filters"
                className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
                <X className="h-4 w-4" />
              </button>
            </header>

            <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
              <div>
                <label htmlFor="q" className={LABEL}>Search</label>
                <span className="relative mt-1 block">
                  <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#9CA3AF]" />
                  <input id="q" value={draft.search ?? ''}
                    placeholder="Title, project ID or batch no."
                    onChange={(e) => set({ search: e.target.value })}
                    onKeyDown={(e) => { if (e.key === 'Enter') apply() }}
                    className={cn(FIELD, 'pl-8')} />
                </span>
              </div>

              <Select label="Department" value={draft.department} all="All Departments"
                options={data.filters.departments} onChange={(v) => set({ department: v })} />
              <Select label="Section" value={draft.section} all="All Sections"
                options={data.filters.sections} onChange={(v) => set({ section: v })} />
              <Select label="Batch No" value={draft.batch_no} all="All Batch No"
                options={data.filters.batch_nos} onChange={(v) => set({ batch_no: v })} />
              <Select label="Project Status" value={draft.project_status} all="All Status"
                options={data.filters.statuses} onChange={(v) => set({ project_status: v })} />

              <button type="button" onClick={() => setShowMore((v) => !v)}
                className="flex w-full items-center justify-between rounded-lg border border-[#E5E7EB] px-3 py-2 text-[12px] font-medium text-[#374151] hover:bg-[#F9FAFB]">
                <span className="flex items-center gap-1.5">
                  <SlidersHorizontal className="h-3.5 w-3.5" />
                  {showMore ? 'Fewer Filters' : 'More Filters'}
                </span>
                {showMore ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
              </button>

              {showMore && (
                <>
                  <div>
                    <label className={LABEL} htmlFor="ay">Academic Year</label>
                    {/* One year at a time: the trainer's scope is resolved for a
                        single academic year, so offering others would filter to
                        an empty list rather than widen it. */}
                    <input id="ay" value={data.academic_year} readOnly
                      className={cn(FIELD, 'mt-1 bg-[#F4F5FA]')} />
                  </div>
                  <Select label="Semester" value={draft.semester} all="All Semesters"
                    options={data.filters.semesters} onChange={(v) => set({ semester: v })} />
                  <Select label="Guide" value={draft.guide} all="All Guides"
                    options={data.filters.guides} onChange={(v) => set({ guide: v })} />
                  <Select label="Batch Type" value={draft.batch_type} all="All Types"
                    options={data.filters.types} onChange={(v) => set({ batch_type: v })} />
                  <div>
                    <label htmlFor="from" className={LABEL}>Created between</label>
                    <div className="mt-1 flex items-center gap-1.5">
                      <CalendarDays className="h-3.5 w-3.5 shrink-0 text-[#9CA3AF]" />
                      <input id="from" type="date" value={draft.date_from ?? ''} aria-label="Created from"
                        onChange={(e) => set({ date_from: e.target.value })} className={FIELD} />
                      <input type="date" value={draft.date_to ?? ''} aria-label="Created to"
                        onChange={(e) => set({ date_to: e.target.value })} className={FIELD} />
                    </div>
                  </div>
                </>
              )}
            </div>

            <footer className="flex gap-2 border-t border-[#E5E7EB] px-4 py-3">
              <button type="button" onClick={clearAll}
                className={cn(BTN_OUTLINE, 'flex-1 justify-center')}>
                Clear All
              </button>
              <button type="button" onClick={apply}
                className={cn(BTN_PRIMARY, 'flex-1 justify-center')}>
                Apply Filters
              </button>
            </footer>
          </aside>
        </div>
      )}

      {sendBack && (
        <SendBackDialog batch={sendBack} onClose={() => setSendBack(null)}
          onDone={(message) => {
            setSendBack(null)
            setNotice({ tone: 'ok', text: message })
            load()
          }} />
      )}

      {showImport && (
        <ImportDialog busy={busy === 'import'} onClose={() => setShowImport(false)}
          onPick={() => fileRef.current?.click()} />
      )}

      {showCreate && caps && (
        <AddBatchDialog
          caps={caps}
          busy={busy === 'create'}
          onClose={() => setShowCreate(false)}
          onSubmit={async (input) => {
            setBusy('create'); setNotice(null)
            try {
              const r: any = await createTrainerBatches(input)
              const n = r?.created?.length ?? r?.count ?? input.count ?? 1
              setNotice({ tone: 'ok', text: `Created ${n} batch${n === 1 ? '' : 'es'}.` })
              setShowCreate(false)
              await load()
            } catch (err: any) {
              setNotice({ tone: 'bad', text: errorText(err, 'Could not create the batches.') })
            } finally { setBusy(null) }
          }}
        />
      )}
    </div>
  )
}

/** At most five numbers, centred on the current page. */
function pageWindow(page: number, pages: number): number[] {
  const span = Math.min(5, Math.max(1, pages))
  let first = Math.max(1, page - Math.floor(span / 2))
  first = Math.min(first, Math.max(1, pages - span + 1))
  return Array.from({ length: span }, (_, i) => first + i)
}

function PageBtn({ onClick, disabled, label, children }: {
  onClick: () => void; disabled: boolean; label: string; children: React.ReactNode
}) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} aria-label={label}
      className="flex h-7 w-7 items-center justify-center rounded-lg border border-[#D1D5DB] bg-white text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40">
      {children}
    </button>
  )
}

function Select({ label, value, all, options, onChange }: {
  label: string; value?: string; all: string; options: string[]
  onChange: (v: string | undefined) => void
}) {
  return (
    <div>
      <label className={LABEL} htmlFor={`f-${label}`}>{label}</label>
      <select id={`f-${label}`} value={value ?? ''}
        onChange={(e) => onChange(e.target.value || undefined)}
        className={cn(FIELD, 'mt-1')}>
        <option value="">{all}</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  )
}

const TONES: Record<string, string> = {
  violet: 'bg-[#EDE9FE] text-[#7C3AED]',
  green: 'bg-[#DCFCE7] text-[#16A34A]',
  blue: 'bg-[#DBEAFE] text-[#2563EB]',
  amber: 'bg-[#FEF3C7] text-[#D97706]',
}

function Stat({ icon, tone, label, value, hint }: {
  icon: React.ReactNode; tone: string; label: string; value: number; hint: string
}) {
  return (
    <div className={cn(CARD, 'flex items-start gap-3 p-3.5')}>
      <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg',
        TONES[tone] ?? TONES.blue)}>{icon}</span>
      <span className="min-w-0">
        <span className="block text-[11.5px] text-[#6B7280]">{label}</span>
        <span className="block text-[20px] font-bold leading-tight text-[#1B1B3A]">{value}</span>
        <span className="block truncate text-[10.5px] text-[#9CA3AF]">{hint}</span>
      </span>
    </div>
  )
}

const STATUS_TONE: Record<string, 'blue' | 'amber' | 'green'> = {
  'In Progress': 'blue', Review: 'amber', Completed: 'green',
}
const BAR_COLOUR: Record<string, string> = {
  'In Progress': '#2563EB', Review: '#EA580C', Completed: '#16A34A',
}

// The states in which a registration is sitting with the guide, and so the
// only ones a trainer can hand back.
const WAITING = new Set(['submitted', 'pending_approval'])

function BatchRow({ batch: b, onSendBack }: {
  batch: BatchCard
  onSendBack?: (batch: BatchCard) => void
}) {
  const when = fmtDate(b.created_at)
  const team = b.team ?? []
  const shown = team.slice(0, 3)
  const extra = b.members - shown.length

  return (
    <tr className="align-middle hover:bg-[#FAFBFF]">
      <td className="whitespace-nowrap px-3 py-3 font-medium text-[#1B1B3A]">{b.batch_code}</td>
      <td className="px-3 py-3">
        <span className="block max-w-[230px] text-[#374151]">{b.title || 'Untitled project'}</span>
      </td>
      <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">{b.batch_no ?? '—'}</td>
      <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">
        {b.department}{b.section ? `-${b.section}` : ''}
      </td>
      <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">{b.guide ?? 'Unassigned'}</td>
      <td className="px-3 py-3">
        {/* One circle per student, overlapping, with the rest rolled into a
            +N chip - the roster has no photographs, so the circles carry
            initials. Hovering any of them gives the full name and roll. */}
        <span className="flex items-center">
          {shown.map((m, i) => (
            <span key={`${m.roll}-${i}`}
              title={[m.name, m.roll].filter(Boolean).join(' · ')}
              className={cn('flex h-7 w-7 items-center justify-center rounded-full border-2 border-white',
                'bg-[#DBE3F5] text-[9.5px] font-semibold text-[#1B2A6B]', i > 0 && '-ml-2')}>
              {initialsOf(m.name, m.roll)}
            </span>
          ))}
          {extra > 0 && (
            <span className="-ml-2 flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-[#EEF1F8] text-[9.5px] font-semibold text-[#4B5563]"
              title={team.slice(shown.length)
                .map((m) => [m.name, m.roll].filter(Boolean).join(' · ')).join(', ')}>
              +{extra}
            </span>
          )}
          {b.members === 0 && <span className="text-[11px] text-[#9CA3AF]">None</span>}
        </span>
      </td>
      <td className="whitespace-nowrap px-3 py-3">
        <Chip tone={STATUS_TONE[b.status] ?? 'blue'}>{b.status}</Chip>
      </td>
      <td className="px-3 py-3">
        <span className="flex items-center gap-2">
          <span className="block h-1.5 w-[90px] overflow-hidden rounded-full bg-[#EEF1F8]">
            <span className="block h-full rounded-full"
              style={{ width: `${b.progress}%`, background: BAR_COLOUR[b.status] ?? '#2563EB' }} />
          </span>
          <span className="text-[11px] font-medium text-[#1B1B3A]">{b.progress}%</span>
        </span>
      </td>
      <td className="whitespace-nowrap px-3 py-3 text-[#4B5563]">
        {when ? (
          <>
            <span className="block">{when.day}</span>
            <span className="block text-[10.5px] text-[#9CA3AF]">{when.time}</span>
          </>
        ) : '—'}
      </td>
      <td className="whitespace-nowrap px-3 py-3">
        <span className="flex items-center gap-1">
          <Link href={`/trainer/ai-planning/${encodeURIComponent(b.batch_code)}`}
            aria-label={`Open ${b.batch_code}`} title="AI planning"
            className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#2563EB] hover:bg-[#F4F7FF]">
            <Eye className="h-3.5 w-3.5" />
          </Link>
          <Link href={`/trainer/student-work?batch=${encodeURIComponent(b.batch_code)}`}
            aria-label={`Student work for ${b.batch_code}`} title="Student work"
            className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#4B5563] hover:bg-[#F9FAFB]">
            <Pencil className="h-3.5 w-3.5" />
          </Link>
          <Link href={`/trainer/reviews?batch=${encodeURIComponent(b.batch_code)}`}
            aria-label={`Reviews for ${b.batch_code}`} title="Reviews"
            className="rounded-lg border border-[#E5E7EB] p-1.5 text-[#4B5563] hover:bg-[#F9FAFB]">
            <MoreVertical className="h-3.5 w-3.5" />
          </Link>
          {/* Only for a registration actually waiting on the trainer. The
              student's locked screen tells them to ask for it back, and until
              now only a faculty coordinator could do it. */}
          {WAITING.has(b.registration_status_key) && onSendBack && (
            <button type="button" onClick={() => onSendBack(b)}
              aria-label={`Send ${b.batch_code} back to the team`}
              title="Send back to the team to edit"
              className="rounded-lg border border-[#FDE68A] bg-[#FFFBEB] p-1.5 text-[#B45309] hover:bg-[#FEF3C7]">
              <Undo2 className="h-3.5 w-3.5" />
            </button>
          )}
        </span>
      </td>
    </tr>
  )
}

function ImportDialog({ busy, onClose, onPick }: {
  busy: boolean; onClose: () => void; onPick: () => void
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
      role="dialog" aria-modal="true" aria-label="Import batch allocation">
      <div className="w-full max-w-[460px] rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-[15px] font-bold text-[#1B1B3A]">Import batch allocation</h2>
            <p className="mt-0.5 text-[11.5px] text-[#6B7280]">
              One row per batch, the team across Student columns.
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 rounded-lg border border-[#DBE3F5] bg-[#F7F9FF] p-3">
          <p className="text-[11.5px] font-medium text-[#1B2A6B]">Start from the sample sheet</p>
          <p className="mt-0.5 text-[11px] leading-snug text-[#4B5563]">
            It has two example batches and a “How to fill this in” tab. Replace the rows
            with your own and upload it back.
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <button type="button" onClick={() => downloadSampleSheet('xlsx')} className={BTN_OUTLINE}>
              <FileSpreadsheet className="h-3.5 w-3.5" /> Sample .xlsx
            </button>
            <button type="button" onClick={() => downloadSampleSheet('csv')} className={BTN_OUTLINE}>
              <Download className="h-3.5 w-3.5" /> Sample .csv
            </button>
          </div>
        </div>

        <dl className="mt-3 space-y-1 text-[11px] text-[#4B5563]">
          <div><dt className="inline font-medium text-[#1B1B3A]">Student N: </dt>
            <dd className="inline">roll and name in one cell — “23K91A05L5 - Royyala Sindhuja”.
              Student 1 is the team leader.</dd></div>
          <div><dt className="inline font-medium text-[#1B1B3A]">Email N: </dt>
            <dd className="inline">optional — a login is generated from the roll number
              if you leave it out.</dd></div>
          <div><dt className="inline font-medium text-[#1B1B3A]">Blank cells: </dt>
            <dd className="inline">a smaller team, not an error. Re-uploading is safe.</dd></div>
        </dl>

        <div className="mt-4 flex justify-end gap-2">
          <button type="button" onClick={onClose} className={BTN_OUTLINE}>Cancel</button>
          <button type="button" onClick={onPick} disabled={busy} className={BTN_PRIMARY}>
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Upload className="h-3.5 w-3.5" />}
            {busy ? 'Importing…' : 'Choose file'}
          </button>
        </div>
      </div>
    </div>
  )
}

function AddBatchDialog({ caps, busy, onClose, onSubmit }: {
  caps: TrainerCapabilities
  busy: boolean
  onClose: () => void
  onSubmit: (input: {
    department: string; year: string; semester: string; section: string
    team_size: number; count: number
  }) => void
}) {
  const departments = caps.manageable_departments.length
    ? caps.manageable_departments
    : caps.departments
  const [department, setDepartment] = useState(departments[0] ?? '')
  const [year, setYear] = useState('4th Year')
  const [semester, setSemester] = useState('I')
  const [section, setSection] = useState('A')
  const [teamSize, setTeamSize] = useState(4)
  const [count, setCount] = useState(1)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
      role="dialog" aria-modal="true" aria-label="Create batches">
      <div className="w-full max-w-[420px] rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-[15px] font-bold text-[#1B1B3A]">Create batches</h2>
            <p className="mt-0.5 text-[11.5px] text-[#6B7280]">
              Empty batches for one section. Students join with the code each one gets.
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form className="mt-4 space-y-3"
          onSubmit={(e) => {
            e.preventDefault()
            onSubmit({ department, year, semester, section, team_size: teamSize, count })
          }}>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="dept" className={LABEL}>Department</label>
              <select id="dept" value={department} onChange={(e) => setDepartment(e.target.value)}
                className={cn(FIELD, 'mt-1')}>
                {departments.map((d) => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="section" className={LABEL}>Section</label>
              <input id="section" value={section} required maxLength={4}
                onChange={(e) => setSection(e.target.value.toUpperCase())}
                className={cn(FIELD, 'mt-1')} />
            </div>
            <div>
              <label htmlFor="year" className={LABEL}>Year</label>
              <select id="year" value={year} onChange={(e) => setYear(e.target.value)}
                className={cn(FIELD, 'mt-1')}>
                {YEARS.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="sem" className={LABEL}>Semester</label>
              <select id="sem" value={semester} onChange={(e) => setSemester(e.target.value)}
                className={cn(FIELD, 'mt-1')}>
                {SEMESTERS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="team" className={LABEL}>Team size</label>
              <input id="team" type="number" min={2} max={8} value={teamSize}
                onChange={(e) => setTeamSize(Number(e.target.value))} className={cn(FIELD, 'mt-1')} />
            </div>
            <div>
              <label htmlFor="count" className={LABEL}>How many</label>
              <input id="count" type="number" min={1} max={20} value={count}
                onChange={(e) => setCount(Number(e.target.value))} className={cn(FIELD, 'mt-1')} />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className={BTN_OUTLINE}>Cancel</button>
            <button type="submit" disabled={busy || !department} className={BTN_PRIMARY}>
              {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
              {busy ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}


/**
 * Handing a registration back to the team.
 *
 * The note is required rather than optional: "changes requested" with no
 * reason leaves a team re-reading their own proposal guessing what the guide
 * objected to, and this note is the only thing that reaches them.
 */
function SendBackDialog({ batch, onClose, onDone }: {
  batch: BatchCard
  onClose: () => void
  onDone: (message: string) => void
}) {
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const send = async () => {
    setBusy(true)
    setError('')
    try {
      const result = await decideRegistration(batch.batch_code, 'request_changes', note.trim())
      onDone(result.message)
    } catch (err: any) {
      setError(errorText(err, 'That could not be sent back.'))
    } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 px-4"
      role="dialog" aria-modal="true" aria-label="Send registration back">
      <div className="w-full max-w-[460px] rounded-xl border border-[#E5E7EB] bg-white p-5 shadow-xl">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-[15px] font-bold text-[#1B1B3A]">
              Send {batch.batch_code} back
            </h2>
            <p className="mt-0.5 text-[11.5px] text-[#6B7280]">
              The team can edit their Project Setup again and resubmit.
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close"
            className="rounded-lg p-1 text-[#6B7280] hover:bg-[#F4F5FA]">
            <X className="h-4 w-4" />
          </button>
        </div>

        <label className="mt-3 block">
          <span className="mb-1 block text-[11.5px] font-medium text-[#374151]">
            What needs changing?
          </span>
          <textarea value={note} autoFocus rows={4}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Objectives need to be measurable - give each one a number."
            className="w-full rounded-lg border border-[#D1D5DB] p-2 text-[12.5px] outline-none focus:border-[#2563EB]" />
          <span className="mt-1 block text-[10.5px] text-[#9CA3AF]">
            This is the only thing the team sees, so say what to fix.
          </span>
        </label>

        {error && (
          <p className="mt-2 rounded-lg border border-[#FECACA] bg-[#FEF2F2] px-3 py-2 text-[11.5px] text-[#DC2626]">
            {error}
          </p>
        )}

        <div className="mt-3 flex justify-end gap-2">
          <button type="button" onClick={onClose} className={BTN_OUTLINE}>Cancel</button>
          <button type="button" onClick={send} disabled={busy || note.trim().length < 5}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-[#B45309] px-3.5 text-[12.5px] font-medium text-white hover:bg-[#92400E] disabled:opacity-50">
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Undo2 className="h-3.5 w-3.5" />}
            Send back
          </button>
        </div>
      </div>
    </div>
  )
}
