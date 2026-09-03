'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  Filter,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Upload,
} from 'lucide-react'
import {
  AllocationMatrix,
  MyAccessPanel,
  NoticeStrip,
  SectionCards,
  SectionPanel,
  StructurePanel,
  type Cursor,
  type SectionTab,
} from '@/components/faculty/academics/panels'
import { Btn, CARD, Card } from '@/components/faculty/batch/primitives'
import { errorMessage } from '@/lib/faculty-api'
import {
  downloadStructure,
  fetchAcademicOverview,
  fetchMyAccess,
  fetchSectionFaculty,
  fetchSectionOverview,
  fetchSectionProjects,
  fetchSectionSubjects,
  fetchStructure,
  requestSectionUpdate,
  type AcademicOverview,
  type MyAccess,
  type SectionFacultyTab,
  type SectionOverview,
  type SectionProjectsTab,
  type SectionSubjectsTab,
  type StructureTree,
} from '@/lib/academics-api'
import { cn } from '@/lib/utils'

const DEFAULT_CURSOR: Cursor = { department: 'CSE', year: '4th Year', semester: 'I' }
const REQUEST_KINDS = ['Capacity', 'Room', 'Timetable', 'Coordinator', 'Allocation', 'Other']

export default function DepartmentsPage() {
  const router = useRouter()

  const [tree, setTree] = useState<StructureTree | null>(null)
  const [access, setAccess] = useState<MyAccess | null>(null)
  const [cursor, setCursor] = useState<Cursor>(DEFAULT_CURSOR)
  const [overview, setOverview] = useState<AcademicOverview | null>(null)

  const [sectionId, setSectionId] = useState<string | null>(null)
  const [sectionTab, setSectionTab] = useState<SectionTab>('Overview')
  const [sectionOverview, setSectionOverview] = useState<SectionOverview | null>(null)
  const [sectionFaculty, setSectionFaculty] = useState<SectionFacultyTab | null>(null)
  const [sectionSubjects, setSectionSubjects] = useState<SectionSubjectsTab | null>(null)
  const [sectionProjects, setSectionProjects] = useState<SectionProjectsTab | null>(null)
  const [sectionLoading, setSectionLoading] = useState(false)

  const [search, setSearch] = useState('')
  const [showFilters, setShowFilters] = useState(false)
  const [statusFilter, setStatusFilter] = useState('')
  const [healthFilter, setHealthFilter] = useState('')

  const [requesting, setRequesting] = useState(false)
  const [requestKind, setRequestKind] = useState(REQUEST_KINDS[0])
  const [requestNote, setRequestNote] = useState('')
  const [showAccess, setShowAccess] = useState(false)
  const [showNotices, setShowNotices] = useState(false)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  // --- structure and access load once; the cohort reloads as the tree moves
  const loadShell = useCallback(async () => {
    try {
      const [structure, myAccess] = await Promise.all([fetchStructure(), fetchMyAccess()])
      setTree(structure)
      setAccess(myAccess)
    } catch (err: any) {
      if (err?.response?.status === 401) { router.push('/login?next=/faculty/departments'); return }
      setError(errorMessage(err, 'Could not load the academic structure.'))
    }
  }, [router])

  const loadCohort = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await fetchAcademicOverview(cursor.department, cursor.year, cursor.semester)
      setOverview(data)
      // Keep the panel on the section in view; fall back to the first one.
      setSectionId((current) =>
        current && data.cards.some((c) => c.id === current) ? current : data.cards[0]?.id ?? null
      )
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 401) { router.push('/login?next=/faculty/departments'); return }
      setOverview(null)
      setError(status === 404
        ? `No structure recorded for ${cursor.department} in this academic year.`
        : errorMessage(err, 'Could not load this department.'))
    } finally {
      setLoading(false)
    }
  }, [cursor, router])

  useEffect(() => { loadShell() }, [loadShell])
  useEffect(() => { loadCohort() }, [loadCohort])

  // --- the section panel fetches only the tab being looked at
  useEffect(() => {
    if (!sectionId) {
      setSectionOverview(null); setSectionFaculty(null)
      setSectionSubjects(null); setSectionProjects(null)
      return
    }
    let cancelled = false
    setSectionLoading(true)
    const loader =
      sectionTab === 'Faculty' ? fetchSectionFaculty(sectionId).then((d) => !cancelled && setSectionFaculty(d))
        : sectionTab === 'Subjects' ? fetchSectionSubjects(sectionId).then((d) => !cancelled && setSectionSubjects(d))
          : sectionTab === 'Projects' ? fetchSectionProjects(sectionId).then((d) => !cancelled && setSectionProjects(d))
            : fetchSectionOverview(sectionId).then((d) => !cancelled && setSectionOverview(d))

    loader
      .catch((err: any) => { if (!cancelled) setNotice(errorMessage(err, 'Could not load that section.')) })
      .finally(() => { if (!cancelled) setSectionLoading(false) })

    return () => { cancelled = true }
  }, [sectionId, sectionTab])

  // Switching section invalidates the other tabs' payloads, otherwise the
  // panel would show section A's faculty under section B's header.
  const selectSection = (id: string) => {
    if (id === sectionId) return
    setSectionOverview(null); setSectionFaculty(null)
    setSectionSubjects(null); setSectionProjects(null)
    setSectionId(id)
  }

  const filtered = useMemo(() => {
    if (!overview) return { cards: [], matrix: [] }
    const needle = search.trim().toLowerCase()
    const keep = (name: string, coordinator: string | null, statusKey: string, healthKey?: string) =>
      (!needle
        || name.toLowerCase().includes(needle)
        || (coordinator ?? '').toLowerCase().includes(needle)
        || overview.department.name.toLowerCase().includes(needle)
        || overview.department.code.toLowerCase().includes(needle))
      && (!statusFilter || statusKey === statusFilter)
      && (!healthFilter || healthKey === healthFilter)

    const statusById = new Map(overview.matrix.map((m) => [m.id, m.status_key]))
    return {
      cards: overview.cards.filter((c) =>
        keep(`Section ${c.name}`, c.coordinator, statusById.get(c.id) ?? '', c.status_key)),
      matrix: overview.matrix.filter((m) =>
        keep(`Section ${m.section}`, m.coordinator, m.status_key,
          overview.cards.find((c) => c.id === m.id)?.status_key)),
    }
  }, [overview, search, statusFilter, healthFilter])

  const submitRequest = async () => {
    if (requestNote.trim().length < 8) {
      setNotice('Describe the change in a sentence or two so the coordinator can action it.')
      return
    }
    try {
      await requestSectionUpdate({
        department: cursor.department,
        section_id: sectionId ?? undefined,
        kind: requestKind,
        note: requestNote.trim(),
      })
      setNotice(`Sent to ${overview?.department.dept_coordinator ?? 'the coordinator'}: ${requestKind} update requested.`)
      setRequesting(false)
      setRequestNote('')
    } catch (err: any) {
      setNotice(errorMessage(err, 'That request could not be submitted.'))
    }
  }

  const crumbs = [
    `Academic Year ${tree?.academic_year ?? '—'}`,
    overview?.department.school.replace('School of ', '') ?? 'Engineering',
    cursor.department,
    cursor.year,
    `Semester ${cursor.semester}`,
  ]

  return (
    <div className="space-y-2.5">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[19px] font-bold leading-tight text-[#1B1B3A]">Departments &amp; Sections</h1>
          <p className="mt-0.5 text-[12px] text-[#5A5F7A]">
            Browse academic structure, section ownership and project allocation
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Btn size="md" icon={Upload}
            onClick={() => downloadStructure(cursor.department)
              .then(() => setNotice(`${cursor.department} structure exported.`))
              .catch(() => setNotice('The structure could not be exported.'))}>
            Export Structure
          </Btn>
          <Btn size="md" tone="primary" icon={Plus} onClick={() => setRequesting((v) => !v)}>
            Request Section Update
          </Btn>
        </div>
      </div>

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] px-3 py-2 text-[12px] text-[#3A3F58]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium text-[#4F46E5]">Dismiss</button>
        </div>
      )}

      {requesting && (
        <section className={cn(CARD, 'space-y-2 p-3')}>
          <p className="text-[12px] font-semibold text-[#1B1B3A]">
            Request a structure change for {cursor.department}
            {sectionId && overview
              ? ` — Section ${overview.cards.find((c) => c.id === sectionId)?.name ?? ''}`
              : ''}
          </p>
          <p className="text-[10.5px] text-[#8A8FA8]">
            Structure is owned by the HOD and coordinator. This records the ask for them to action.
          </p>
          <div className="flex flex-wrap items-start gap-2">
            <select value={requestKind} onChange={(e) => setRequestKind(e.target.value)} aria-label="Request type"
              className="h-8 rounded-lg border border-[#DDE0EE] px-2 text-[11.5px] outline-none focus:border-[#4F46E5]">
              {REQUEST_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
            <input value={requestNote} onChange={(e) => setRequestNote(e.target.value)}
              placeholder="What needs to change, and why?"
              className="h-8 min-w-[260px] flex-1 rounded-lg border border-[#DDE0EE] px-2.5 text-[11.5px] outline-none focus:border-[#4F46E5]" />
            <Btn size="md" tone="primary" onClick={submitRequest}>Send Request</Btn>
            <Btn size="md" onClick={() => setRequesting(false)}>Cancel</Btn>
          </div>
        </section>
      )}

      {/* Breadcrumb */}
      <nav className={cn(CARD, 'flex flex-wrap items-center gap-1.5 px-3 py-2 text-[11.5px]')}>
        {crumbs.map((c, i) => (
          <span key={c} className="flex items-center gap-1.5">
            {i > 0 && <span className="text-[#C7CBDD]">/</span>}
            <span className={i === 0 ? 'text-[#5A5F7A]' : 'font-medium text-[#4F46E5]'}>{c}</span>
          </span>
        ))}
      </nav>

      <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,1fr)_minmax(0,392px)]">
        <div className="space-y-2.5">
          {/* Search + filters */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="relative min-w-[240px] flex-1">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[#8A8FA8]" />
              <input value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Search department, section, coordinator or faculty…"
                className={cn(CARD, 'h-9 w-full pl-8 pr-2.5 text-[12px] outline-none focus:border-[#4F46E5]')} />
            </span>
            <Btn size="md" icon={Filter} onClick={() => setShowFilters((v) => !v)}>Filters</Btn>
          </div>

          {showFilters && (
            <section className={cn(CARD, 'flex flex-wrap items-center gap-2 p-3')}>
              <label className="text-[11px] text-[#5A5F7A]" htmlFor="f-status">Allocation status</label>
              <select id="f-status" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                className="h-8 rounded-lg border border-[#DDE0EE] px-2 text-[11.5px] outline-none focus:border-[#4F46E5]">
                <option value="">All</option>
                <option value="published">Published</option>
                <option value="draft">Draft</option>
                <option value="archived">Archived</option>
              </select>
              <label className="ml-2 text-[11px] text-[#5A5F7A]" htmlFor="f-health">Section health</label>
              <select id="f-health" value={healthFilter} onChange={(e) => setHealthFilter(e.target.value)}
                className="h-8 rounded-lg border border-[#DDE0EE] px-2 text-[11.5px] outline-none focus:border-[#4F46E5]">
                <option value="">All</option>
                <option value="excellent">Excellent</option>
                <option value="on_track">On Track</option>
                <option value="needs_attention">Needs Attention</option>
              </select>
              <Btn size="sm" className="ml-auto"
                onClick={() => { setStatusFilter(''); setHealthFilter(''); setSearch('') }}>
                Clear
              </Btn>
            </section>
          )}

          <div className="grid gap-2.5 lg:grid-cols-[minmax(0,224px)_minmax(0,1fr)]">
            <div className="space-y-2.5">
              {tree
                ? <StructurePanel tree={tree} cursor={cursor} onSelect={setCursor} />
                : <Card><p className="py-8 text-center text-[11px] text-[#8A8FA8]">Loading structure…</p></Card>}
              <MyAccessPanel access={access} onDetails={() => setShowAccess((v) => !v)} />
              {showAccess && access && (
                <Card title="Access Details">
                  {access.assignments.length === 0 ? (
                    <p className="py-2 text-center text-[11px] text-[#8A8FA8]">No assignments recorded.</p>
                  ) : (
                    <ul className="space-y-1.5">
                      {access.assignments.map((a, i) => (
                        <li key={i} className="rounded-lg border border-[#EEF0F7] px-2 py-1.5">
                          <p className="text-[11px] font-medium text-[#1B1B3A]">
                            {a.department} · {a.year} · Sem {a.semester} · Section {a.section}
                          </p>
                          <p className="text-[10px] text-[#8A8FA8]">
                            {a.role}{a.responsibility ? ` — ${a.responsibility}` : ''}
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                </Card>
              )}
            </div>

            {/* Department cohort */}
            {loading && !overview ? (
              <div className={cn(CARD, 'flex h-[360px] flex-col items-center justify-center gap-3 text-[#5A5F7A]')}>
                <Loader2 className="h-5 w-5 animate-spin text-[#4F46E5]" />
                <p className="text-[12px]">Loading {cursor.department}…</p>
              </div>
            ) : error ? (
              <div className={cn(CARD, 'flex h-[360px] flex-col items-center justify-center gap-3')}>
                <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
                <p className="text-[12px] text-[#5A5F7A]">{error}</p>
                <Btn size="md" tone="primary" icon={RefreshCw} onClick={loadCohort}>Retry</Btn>
              </div>
            ) : overview ? (
              <section className={cn(CARD, 'p-4', loading && 'opacity-60 transition-opacity')}>
                <h2 className="text-[15px] font-bold text-[#1B1B3A]">
                  {overview.department.code} — {overview.year}, Semester {overview.semester}
                </h2>
                <p className="mt-0.5 text-[11.5px] text-[#5A5F7A]">
                  {overview.section_count} sections &nbsp;&bull;&nbsp; {overview.assigned_students} assigned
                  students &nbsp;&bull;&nbsp; {overview.batch_count} project batches
                </p>
                <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 border-b border-[#EEF0F7] pb-2.5">
                  {[
                    ['HOD', overview.department.hod],
                    ['Department Coordinator', overview.department.dept_coordinator],
                    ['Project Coordinator', overview.department.project_coordinator],
                    ['Academic Year', overview.department.academic_year],
                  ].map(([label, value]) => (
                    <span key={label as string} className="flex items-baseline gap-1.5">
                      <span className="text-[10.5px] text-[#8A8FA8]">{label}</span>
                      <span className="text-[11.5px] font-medium text-[#1B1B3A]">{value ?? '—'}</span>
                    </span>
                  ))}
                </div>

                <div className="mt-3">
                  <SectionCards cards={filtered.cards} selectedId={sectionId}
                    onSelect={selectSection}
                    onStudents={(name) =>
                      router.push(`/faculty/registrations?tab=students&section=${name}&department=${cursor.department}`)} />
                </div>

                <div className="mt-4">
                  <h3 className="mb-2 text-[13px] font-semibold text-[#1B1B3A]">Section Allocation Matrix</h3>
                  <AllocationMatrix rows={filtered.matrix} onSelect={selectSection} />
                  <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-[#EEF0F7] pt-2.5">
                    <p className="flex items-center gap-1.5 text-[11px] text-[#5A5F7A]">
                      <AlertTriangle className={cn('h-3.5 w-3.5',
                        overview.unmapped_students > 0 ? 'text-[#D97706]' : 'text-[#16A34A]')} />
                      {overview.unmapped_students > 0
                        ? `${overview.unmapped_students} students are not mapped to sections`
                        : 'Every student in this year is mapped to a section'}
                    </p>
                    <Link href={`/faculty/registrations?tab=students&unassigned=1&department=${cursor.department}`}
                      className="rounded-lg border border-[#DDE0EE] px-3 py-1.5 text-[11.5px] font-medium text-[#3A3F58] hover:bg-[#F7F8FC]">
                      Review Allocation
                    </Link>
                  </div>
                </div>
              </section>
            ) : null}
          </div>
        </div>

        {/* Section detail */}
        <SectionPanel
          tab={sectionTab}
          onTab={setSectionTab}
          overview={sectionOverview}
          faculty={sectionFaculty}
          subjects={sectionSubjects}
          projects={sectionProjects}
          loading={sectionLoading}
          onNotice={setNotice}
          onWorkspace={() => {
            const name = overview?.cards.find((c) => c.id === sectionId)?.name
            router.push(`/faculty/project-tracking?section=${name ?? ''}&department=${cursor.department}`)
          }}
        />
      </div>

      {overview && (
        <NoticeStrip notices={overview.notices}
          onAll={() => setShowNotices((v) => !v)}
          onContact={() => setNotice(
            `Contact ${overview.department.dept_coordinator ?? 'the coordinator'} — messaging needs the email pipeline, which is not wired up.`)} />
      )}

      {showNotices && overview && (
        <Card title={`All Notices (${overview.notices.length})`}>
          {overview.notices.length === 0 ? (
            <p className="py-3 text-center text-[11px] text-[#8A8FA8]">No active notices.</p>
          ) : (
            <ul className="space-y-1.5">
              {overview.notices.map((n) => (
                <li key={n.id} className="rounded-lg border border-[#EEF0F7] px-2.5 py-2">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[11.5px] font-medium text-[#1B1B3A]">{n.title}</p>
                    <span className="text-[10.5px] text-[#8A8FA8]">{n.window_label}</span>
                  </div>
                  {n.detail && <p className="mt-0.5 text-[11px] text-[#5A5F7A]">{n.detail}</p>}
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <p className={cn(CARD, 'flex items-center gap-2 px-3 py-2 text-[11px] text-[#5A5F7A]')}>
        <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />
        Department and section structure is managed by the HOD and coordinator. Faculty can request
        changes for assigned sections.
      </p>
    </div>
  )
}
