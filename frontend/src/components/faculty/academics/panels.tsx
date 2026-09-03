'use client'

import { useState } from 'react'
import {
  AlertTriangle,
  BookOpen,
  Building2,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FileText,
  FolderClosed,
  FolderOpen,
  GraduationCap,
  LineChart,
  Users,
} from 'lucide-react'
import {
  Bar,
  Btn,
  Card,
  Initials,
  Tag,
  statusTone,
} from '@/components/faculty/batch/primitives'
import type {
  AcademicOverview,
  AllocationRow,
  MyAccess,
  SectionCard,
  SectionFacultyTab,
  SectionOverview,
  SectionProjectsTab,
  SectionSubjectsTab,
  StructureTree,
} from '@/lib/academics-api'
import { cn } from '@/lib/utils'

export interface Cursor {
  department: string
  year: string
  semester: string
}

// ============================================================ Structure tree

export function StructurePanel({ tree, cursor, onSelect }: {
  tree: StructureTree
  cursor: Cursor
  onSelect: (next: Cursor) => void
}) {
  // Only the branch in view starts open; the rest would bury it.
  const [openDepts, setOpenDepts] = useState<Record<string, boolean>>({ [cursor.department]: true })
  const [openYears, setOpenYears] = useState<Record<string, boolean>>({
    [`${cursor.department}:${cursor.year}`]: true,
  })

  const toggle = (set: typeof setOpenDepts, key: string) =>
    set((prev) => ({ ...prev, [key]: !prev[key] }))

  return (
    <Card title="Academic Structure">
      <ul className="space-y-0.5">
        {tree.schools.map((school) => (
          <li key={school.school}>
            <span className="flex items-center gap-1.5 py-1 text-[11.5px] font-medium text-[#1B1B3A]">
              <ChevronDown className="h-3.5 w-3.5 text-[#8A8FA8]" />
              <Building2 className="h-3.5 w-3.5 text-[#8A8FA8]" />
              {school.school}
            </span>

            <ul className="ml-2 border-l border-[#EEF0F7] pl-2">
              {school.departments.map((dept) => {
                const deptOpen = openDepts[dept.code]
                const active = dept.code === cursor.department
                return (
                  <li key={dept.code}>
                    <button type="button"
                      onClick={() => {
                        toggle(setOpenDepts, dept.code)
                        if (!active) {
                          const year = dept.years[dept.years.length - 1]
                          if (year) {
                            onSelect({
                              department: dept.code,
                              year: year.year,
                              semester: year.semesters[0]?.semester ?? 'I',
                            })
                          }
                        }
                      }}
                      className={cn('flex w-full items-start gap-1.5 rounded-md px-1.5 py-1 text-left hover:bg-[#F7F8FC]',
                        active && 'bg-[#EEF2FF]')}>
                      {deptOpen
                        ? <ChevronDown className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />
                        : <ChevronRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />}
                      {deptOpen
                        ? <FolderOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#4F46E5]" />
                        : <FolderClosed className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />}
                      <span className="min-w-0 flex-1">
                        <span className={cn('block truncate text-[11.5px]',
                          active ? 'font-semibold text-[#4F46E5]' : 'text-[#1B1B3A]')}>
                          {dept.name}
                        </span>
                        <span className="block text-[9.5px] text-[#8A8FA8]">
                          {dept.students > 0
                            ? `${dept.students} students`
                            : `${dept.section_count} sections · no cohort loaded`}
                        </span>
                      </span>
                    </button>

                    {deptOpen && (
                      <ul className="ml-3 border-l border-[#EEF0F7] pl-2">
                        {dept.years.map((year) => {
                          const yearKey = `${dept.code}:${year.year}`
                          const yearOpen = openYears[yearKey]
                          return (
                            <li key={year.year}>
                              <button type="button" onClick={() => toggle(setOpenYears, yearKey)}
                                className="flex w-full items-start gap-1.5 rounded-md px-1.5 py-1 text-left hover:bg-[#F7F8FC]">
                                {yearOpen
                                  ? <ChevronDown className="mt-0.5 h-3 w-3 shrink-0 text-[#8A8FA8]" />
                                  : <ChevronRight className="mt-0.5 h-3 w-3 shrink-0 text-[#8A8FA8]" />}
                                <FolderClosed className="mt-0.5 h-3 w-3 shrink-0 text-[#8A8FA8]" />
                                <span className="min-w-0 flex-1">
                                  <span className="block text-[11px] text-[#1B1B3A]">{year.year}</span>
                                  <span className="block text-[9.5px] text-[#8A8FA8]">
                                    {year.section_count} sections
                                  </span>
                                </span>
                              </button>

                              {yearOpen && (
                                <ul className="ml-3 border-l border-[#EEF0F7] pl-2">
                                  {year.semesters.map((sem) => {
                                    const on = active && year.year === cursor.year
                                      && sem.semester === cursor.semester
                                    return (
                                      <li key={sem.semester}>
                                        <button type="button"
                                          onClick={() => onSelect({
                                            department: dept.code, year: year.year, semester: sem.semester,
                                          })}
                                          className={cn('flex w-full items-start gap-1.5 rounded-md px-1.5 py-1 text-left hover:bg-[#F7F8FC]',
                                            on && 'bg-[#EEF2FF]')}>
                                          <FileText className={cn('mt-0.5 h-3 w-3 shrink-0',
                                            on ? 'text-[#4F46E5]' : 'text-[#8A8FA8]')} />
                                          <span className="min-w-0 flex-1">
                                            <span className={cn('block text-[11px]',
                                              on ? 'font-semibold text-[#4F46E5]' : 'text-[#1B1B3A]')}>
                                              Semester {sem.semester}
                                            </span>
                                            <span className="block text-[9.5px] text-[#8A8FA8]">
                                              {sem.sections.length
                                                ? `Sections ${sem.sections.join(', ')}`
                                                : 'No sections'}
                                            </span>
                                          </span>
                                        </button>
                                      </li>
                                    )
                                  })}
                                </ul>
                              )}
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </li>
                )
              })}
            </ul>
          </li>
        ))}
      </ul>
    </Card>
  )
}

// ================================================================= My access

export function MyAccessPanel({ access, onDetails }: {
  access: MyAccess | null
  onDetails: () => void
}) {
  return (
    <Card title="My Access">
      {access ? (
        <>
          <div className="space-y-1.5">
            <p className="text-[11.5px] text-[#1B1B3A]">
              {access.department_label} <span className="text-[#8A8FA8]">&bull;</span> {access.section_label}
            </p>
            <div>
              <p className="text-[10.5px] text-[#8A8FA8]">Role</p>
              <p className="text-[11.5px] text-[#1B1B3A]">{access.roles.join(', ')}</p>
            </div>
          </div>
          <Btn full className="mt-2" onClick={onDetails}>View Access Details</Btn>
        </>
      ) : (
        <p className="py-3 text-center text-[11px] text-[#8A8FA8]">
          You have no section assignments this academic year.
        </p>
      )}
    </Card>
  )
}

// ============================================================= Section cards

const HEALTH_TONE: Record<string, 'green' | 'amber' | 'red' | 'slate'> = {
  excellent: 'green',
  on_track: 'green',
  needs_attention: 'amber',
  not_assigned: 'slate',
}

function Metric({ label, value, tone }: { label: string; value: number | null; tone: string }) {
  return (
    <span className="flex items-center gap-2">
      <span className="w-[84px] shrink-0 whitespace-nowrap text-[10px] text-[#5A5F7A]">{label}</span>
      <span className="min-w-[52px] flex-1"><Bar value={value ?? 0} tone={tone} /></span>
      <span className="w-[30px] shrink-0 text-right text-[10px] font-medium text-[#1B1B3A]">
        {value === null ? '—' : `${value}%`}
      </span>
    </span>
  )
}

export function SectionCards({ cards, selectedId, onSelect, onStudents }: {
  cards: SectionCard[]
  selectedId: string | null
  onSelect: (id: string) => void
  onStudents: (name: string) => void
}) {
  if (cards.length === 0) {
    return <p className="py-8 text-center text-[12px] text-[#8A8FA8]">No sections defined for this semester.</p>
  }
  return (
    <ul className="space-y-2.5">
      {cards.map((c) => (
        <li key={c.id}
          className={cn('rounded-xl border p-3 transition-colors',
            selectedId === c.id ? 'border-[#C7BDF5] bg-[#FAF9FF]' : 'border-[#EEF0F7] bg-white')}>
          <div className="grid gap-x-3 gap-y-2.5 sm:grid-cols-2 xl:grid-cols-[minmax(126px,0.85fr)_minmax(116px,0.85fr)_minmax(196px,1.35fr)_auto]">
            <div>
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#4F46E5] text-[12px] font-bold text-white">
                  {c.name}
                </span>
                <p className="text-[13px] font-semibold text-[#1B1B3A]">Section {c.name}</p>
              </div>
              <p className="mt-2 flex items-center gap-1.5 text-[11px] text-[#3A3F58]">
                <Users className="h-3.5 w-3.5 text-[#8A8FA8]" /> {c.students} students
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-[11px] text-[#3A3F58]">
                <CalendarDays className="h-3.5 w-3.5 text-[#8A8FA8]" /> {c.batches} project batches
              </p>
            </div>

            <div>
              <p className="text-[10.5px] text-[#8A8FA8]">Class Coordinator</p>
              <p className="text-[11.5px] font-medium text-[#1B1B3A]">{c.coordinator ?? '—'}</p>
              <p className="mt-2 text-[10.5px] text-[#8A8FA8]">
                Project Guides <span className="ml-1 font-semibold text-[#1B1B3A]">{c.guide_count}</span>
              </p>
              <span className="mt-1 flex items-center">
                {c.guides.slice(0, 4).map((g, i) => (
                  <span key={g} className={cn('rounded-full ring-2 ring-white', i > 0 && '-ml-1.5')}>
                    <Initials name={g} size="h-6 w-6" />
                  </span>
                ))}
                {c.guides.length > 4 && (
                  <span className="-ml-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-[#EEF2FF] text-[9px] font-semibold text-[#4F46E5] ring-2 ring-white">
                    +{c.guides.length - 4}
                  </span>
                )}
              </span>
            </div>

            <div className="space-y-1">
              <Metric label="Registration" value={c.registration} tone="bg-[#16A34A]" />
              <Metric label="Attendance" value={c.attendance}
                tone={(c.attendance ?? 100) < 75 ? 'bg-[#DC2626]' : 'bg-[#16A34A]'} />
              <Metric label="Average Progress" value={c.progress} tone="bg-[#4F46E5]" />
              <span className="flex items-center justify-between gap-2 pt-0.5">
                <span className="whitespace-nowrap text-[10px] text-[#5A5F7A]">Reviews Pending</span>
                <span className="flex items-center gap-2">
                  <span className={cn('text-[11px] font-semibold',
                    c.pending_reviews > 0 ? 'text-[#D97706]' : 'text-[#16A34A]')}>
                    {c.pending_reviews}
                  </span>
                  <Tag tone={HEALTH_TONE[c.status_key] ?? 'slate'}>{c.status}</Tag>
                </span>
              </span>
            </div>

            <div className="flex flex-col gap-1.5">
              <Btn size="sm" tone="ghost" icon={ExternalLink} onClick={() => onSelect(c.id)}>Open Section</Btn>
              <Btn size="sm" icon={Users} onClick={() => onStudents(c.name)}>View Students</Btn>
            </div>
          </div>
        </li>
      ))}
    </ul>
  )
}

// ========================================================= Allocation matrix

const HEAD = ['Section', 'Capacity', 'Assigned\nStudents', 'Unassigned', 'Project\nBatches',
  'Faculty\nGuides', 'Student-Guide\nRatio', 'Coordinator', 'Room', 'Timetable', 'Status', 'Action']
const WIDTHS = ['42px', '48px', '54px', '64px', '48px', '46px', '58px', 'auto', '52px', '76px', '74px', '40px']

export function AllocationMatrix({ rows, onSelect }: {
  rows: AllocationRow[]
  onSelect: (id: string) => void
}) {
  return (
    <table className="w-full table-fixed border-collapse text-[10.5px]">
      <colgroup>{WIDTHS.map((w, i) => <col key={i} style={{ width: w }} />)}</colgroup>
      <thead>
        <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
          {HEAD.map((h, i) => (
            <th key={h} className={cn('px-1.5 py-1.5 align-bottom text-[9.5px] font-medium leading-tight',
              i === 7 ? 'text-left' : 'text-center')}>
              {h.split('\n').map((line) => <span key={line} className="block">{line}</span>)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="border-b border-[#F1F2F8]">
            <td className="px-1.5 py-1.5 text-center font-medium text-[#1B1B3A]">{r.section}</td>
            <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">{r.capacity}</td>
            <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">
              {r.assigned}
              {r.over_capacity > 0 && (
                <span className="ml-1 text-[9.5px] font-semibold text-[#DC2626]"
                  title={`${r.over_capacity} over capacity`}>+{r.over_capacity}</span>
              )}
            </td>
            <td className={cn('px-1.5 py-1.5 text-center font-medium',
              r.unassigned > 0 ? 'text-[#D97706]' : 'text-[#16A34A]')}>{r.unassigned}</td>
            <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">{r.batches}</td>
            <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">{r.guides}</td>
            <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">{r.ratio}</td>
            <td className="truncate px-1.5 py-1.5 text-[#3A3F58]" title={r.coordinator ?? ''}>
              {r.coordinator ?? '—'}
            </td>
            <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">{r.room ?? '—'}</td>
            <td className="px-1.5 py-1.5 text-center">
              <Tag tone={r.timetable === 'Published' ? 'green' : 'slate'}>{r.timetable}</Tag>
            </td>
            <td className="px-1.5 py-1.5 text-center">
              <Tag tone={r.status_key === 'published' ? 'green' : r.status_key === 'draft' ? 'amber' : 'slate'}>
                {r.status}
              </Tag>
            </td>
            <td className="px-1.5 py-1.5 text-center">
              <button type="button" onClick={() => onSelect(r.id)}
                className="font-medium text-[#4F46E5] hover:underline">View</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

// ========================================================== Section detail

const SECTION_TABS = ['Overview', 'Faculty', 'Subjects', 'Projects'] as const
export type SectionTab = (typeof SECTION_TABS)[number]

export function SectionPanel({
  tab, onTab, overview, faculty, subjects, projects, loading, onNotice, onWorkspace,
}: {
  tab: SectionTab
  onTab: (t: SectionTab) => void
  overview: SectionOverview | null
  faculty: SectionFacultyTab | null
  subjects: SectionSubjectsTab | null
  projects: SectionProjectsTab | null
  loading: boolean
  onNotice: (m: string) => void
  onWorkspace: () => void
}) {
  const header = overview?.header ?? faculty?.header ?? subjects?.header ?? projects?.header ?? null

  if (!header) {
    return (
      <Card>
        <p className="py-16 text-center text-[12px] text-[#8A8FA8]">
          {loading ? 'Loading section…' : 'Select a section to see its detail.'}
        </p>
      </Card>
    )
  }

  return (
    <div className="space-y-2.5">
      <Card>
        <div className="flex items-start justify-between gap-2">
          <div>
            <h2 className="text-[16px] font-bold leading-tight text-[#1B1B3A]">Section {header.name}</h2>
            <p className="mt-0.5 text-[11px] text-[#5A5F7A]">
              {header.department} &bull; {header.year} &bull; Semester {header.semester}
            </p>
          </div>
          <span className="flex items-center gap-1.5">
            <span className="text-[10.5px] text-[#8A8FA8]">Status</span>
            <Tag tone={header.status_key === 'published' ? 'green' : header.status_key === 'draft' ? 'amber' : 'slate'}>
              {header.status}
            </Tag>
          </span>
        </div>

        <div className="mt-3 flex flex-wrap items-start gap-3">
          <Initials name={header.coordinator} size="h-11 w-11" />
          <span>
            <p className="text-[10.5px] text-[#8A8FA8]">Coordinator</p>
            <p className="text-[12px] font-semibold text-[#1B1B3A]">{header.coordinator ?? '—'}</p>
          </span>
          <span>
            <p className="text-[10.5px] text-[#8A8FA8]">Room</p>
            <p className="text-[12px] font-medium text-[#1B1B3A]">{header.room ?? '—'}</p>
          </span>
          <span>
            <p className="text-[10.5px] text-[#8A8FA8]">Schedule</p>
            <p className="text-[12px] font-medium text-[#1B1B3A]">
              {header.schedule_days ?? '—'}
              {header.schedule_time && <span className="text-[#8A8FA8]"> &bull; </span>}
              {header.schedule_time}
            </p>
          </span>
        </div>

        <div className="mt-3 flex gap-1 border-b border-[#E8E9F2]">
          {SECTION_TABS.map((t) => (
            <button key={t} type="button" onClick={() => onTab(t)}
              className={cn('border-b-2 px-3 py-1.5 text-[11.5px] transition-colors',
                tab === t ? 'border-[#4F46E5] font-medium text-[#4F46E5]'
                  : 'border-transparent text-[#5A5F7A] hover:text-[#1B1B3A]')}>
              {t}
            </button>
          ))}
        </div>

        <div className={cn('pt-3', loading && 'opacity-60 transition-opacity')}>
          {tab === 'Overview' && overview && (
            <SectionOverviewTab data={overview} onFacultyTab={() => onTab('Faculty')} />
          )}
          {tab === 'Faculty' && faculty && <SectionFacultyList data={faculty} />}
          {tab === 'Subjects' && subjects && <SectionSubjectList data={subjects} />}
          {tab === 'Projects' && projects && <SectionProjectList data={projects} />}
        </div>
      </Card>

      {tab === 'Overview' && overview && (
        <Card title="Attention">
          {overview.attention.length === 0 ? (
            <p className="py-2 text-center text-[11px] text-[#16A34A]">Nothing needs attention here.</p>
          ) : (
            <ul className="space-y-1.5">
              {overview.attention.map((a) => (
                <li key={a.kind} className="flex items-start gap-2 text-[11.5px] text-[#3A3F58]">
                  <AlertTriangle className={cn('mt-0.5 h-3.5 w-3.5 shrink-0',
                    a.severity === 'critical' ? 'text-[#DC2626]' : 'text-[#D97706]')} />
                  {a.label}
                </li>
              ))}
            </ul>
          )}
          <Btn full tone="primary" size="md" icon={ExternalLink} className="mt-3" onClick={onWorkspace}>
            Open Section Workspace
          </Btn>
        </Card>
      )}
    </div>
  )
}

function SectionOverviewTab({ data, onFacultyTab }: {
  data: SectionOverview; onFacultyTab: () => void
}) {
  const ICONS: Record<string, typeof Users> = {
    students: Users, batches: CalendarDays, guides: GraduationCap,
    core: BookOpen, labs: Building2, progress: LineChart, attendance: CalendarDays,
  }
  return (
    <>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5">
        {data.kpis.map((k) => {
          const Icon = ICONS[k.id] ?? Users
          return (
            <span key={k.id} className="flex items-start gap-2">
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-[#4F46E5]" />
              <span>
                <span className={cn('block text-[14px] font-bold leading-tight',
                  k.warn ? 'text-[#DC2626]' : 'text-[#1B1B3A]')}>{k.value}</span>
                <span className="block text-[10.5px] leading-tight text-[#5A5F7A]">{k.label}</span>
              </span>
            </span>
          )
        })}
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="mb-1.5 text-[11.5px] font-semibold text-[#1B1B3A]">Faculty &amp; Responsibilities</p>
          <ul className="space-y-1.5">
            {data.faculty.slice(0, 4).map((f) => (
              <li key={f.id} className="flex items-center gap-2">
                <Initials name={f.name} size="h-6 w-6" />
                <span className="min-w-0">
                  <span className="block truncate text-[11.5px] text-[#1B1B3A]">{f.name}</span>
                  <span className="block truncate text-[9.5px] text-[#8A8FA8]">{f.role_label}</span>
                </span>
              </li>
            ))}
          </ul>
          <Btn size="xs" full className="mt-2" icon={Users} onClick={onFacultyTab}>
            View Faculty Allocation
            {data.faculty.length > 4 && <span className="ml-1 text-[#8A8FA8]">({data.faculty.length})</span>}
          </Btn>
        </div>
        <div>
          <p className="mb-1.5 text-[11.5px] font-semibold text-[#1B1B3A]">Project Distribution</p>
          <ul className="space-y-1.5">
            {data.distribution.map((d) => (
              <li key={d.domain} className="flex items-center gap-2">
                <span className="w-[92px] shrink-0 truncate text-[10px] text-[#3A3F58]" title={d.domain}>
                  {d.domain}
                </span>
                <span className="min-w-[42px] flex-1"><Bar value={d.share} /></span>
                <span className="w-[14px] shrink-0 text-right text-[10.5px] font-medium text-[#1B1B3A]">
                  {d.count}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  )
}

function SectionFacultyList({ data }: { data: SectionFacultyTab }) {
  return (
    <>
      <div className="mb-2 flex flex-wrap gap-1.5">
        {data.role_counts.map((r) => (
          <Tag key={r.role} tone="indigo">{r.role} &middot; {r.count}</Tag>
        ))}
      </div>
      <ul className="space-y-1.5">
        {data.rows.map((f) => (
          <li key={f.id} className="rounded-lg border border-[#EEF0F7] p-2.5">
            <div className="flex items-center gap-2">
              <Initials name={f.name} size="h-7 w-7" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[11.5px] font-medium text-[#1B1B3A]">{f.name}</span>
                <span className="block truncate text-[10px] text-[#8A8FA8]">{f.role_label}</span>
              </span>
            </div>
            {(f.subjects?.length ?? 0) > 0 && (
              <p className="mt-1.5 text-[10px] text-[#5A5F7A]">
                Teaches: {f.subjects!.join(', ')}
              </p>
            )}
            {f.responsibilities.length > 0 && (
              <p className="mt-0.5 text-[10px] text-[#8A8FA8]">{f.responsibilities.join(' · ')}</p>
            )}
          </li>
        ))}
      </ul>
    </>
  )
}

function SectionSubjectList({ data }: { data: SectionSubjectsTab }) {
  if (data.rows.length === 0) {
    return <p className="py-6 text-center text-[11px] text-[#8A8FA8]">No subjects recorded for this section.</p>
  }
  return (
    <>
      <ul className="space-y-1.5">
        {data.rows.map((s) => (
          <li key={s.id} className="flex items-center gap-2 rounded-lg border border-[#EEF0F7] px-2.5 py-2">
            <BookOpen className="h-3.5 w-3.5 shrink-0 text-[#4F46E5]" />
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[11.5px] text-[#1B1B3A]">{s.title}</span>
              <span className="block text-[9.5px] text-[#8A8FA8]">
                {[s.code, s.faculty].filter(Boolean).join(' · ')}
              </span>
            </span>
            <Tag tone={s.kind_key === 'lab' ? 'indigo' : 'slate'}>{s.kind}</Tag>
            <span className="w-[38px] shrink-0 text-right text-[10.5px] text-[#5A5F7A]">
              {s.credits ?? '—'} cr
            </span>
          </li>
        ))}
      </ul>
      <p className="mt-2 text-right text-[10.5px] text-[#8A8FA8]">{data.total_credits} credits total</p>
    </>
  )
}

function SectionProjectList({ data }: { data: SectionProjectsTab }) {
  if (data.rows.length === 0) {
    return <p className="py-6 text-center text-[11px] text-[#8A8FA8]">No project batches in this section.</p>
  }
  return (
    <ul className="max-h-[420px] space-y-1.5 overflow-y-auto pr-1">
      {data.rows.map((p) => (
        <li key={p.id} className="rounded-lg border border-[#EEF0F7] px-2.5 py-2">
          <div className="flex items-center justify-between gap-2">
            <a href={`/faculty/registrations/${encodeURIComponent(p.batch_code)}`}
              className="truncate text-[11.5px] font-medium text-[#4F46E5] hover:underline">
              {p.batch_code}
            </a>
            <Tag tone={statusTone(p.status_key)}>{p.status}</Tag>
          </div>
          <p className="truncate text-[11px] text-[#1B1B3A]" title={p.title ?? ''}>{p.title ?? '—'}</p>
          <div className="mt-1 flex items-center gap-2">
            <span className="flex-1"><Bar value={p.progress} /></span>
            <span className="w-[30px] shrink-0 text-right text-[10px] text-[#5A5F7A]">{p.progress}%</span>
          </div>
          <p className="mt-0.5 text-[9.5px] text-[#8A8FA8]">
            {p.guide ?? 'No guide'} &bull; {p.members} members &bull; base paper {p.base_paper}
          </p>
        </li>
      ))}
    </ul>
  )
}

// =========================================================== Notices strip

export function NoticeStrip({ notices, onAll, onContact }: {
  notices: AcademicOverview['notices']
  onAll: () => void
  onContact: () => void
}) {
  return (
    <section className="flex flex-wrap items-center gap-3 rounded-xl border border-[#E8E9F2] bg-white p-3">
      <span className="flex items-center gap-2">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#EEF2FF]">
          <AlertTriangle className="h-4 w-4 text-[#4F46E5]" />
        </span>
        <span className="text-[13px] font-bold leading-tight text-[#1B1B3A]">
          Department<br />Notices
        </span>
      </span>
      {notices.length === 0 ? (
        <p className="flex-1 text-[11px] text-[#8A8FA8]">No active notices.</p>
      ) : (
        <ul className="flex flex-1 flex-wrap items-center gap-x-5 gap-y-2">
          {notices.slice(0, 3).map((n) => (
            <li key={n.id} className="flex items-start gap-2 border-l border-[#EEF0F7] pl-3 first:border-l-0 first:pl-0">
              <CalendarDays className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />
              <span>
                <span className="block text-[11.5px] text-[#1B1B3A]">{n.title}:</span>
                <span className={cn('block text-[11px] font-medium',
                  n.severity === 'warning' ? 'text-[#D97706]'
                    : n.severity === 'critical' ? 'text-[#DC2626]' : 'text-[#3A3F58]')}>
                  {n.window_label ?? '—'}
                </span>
              </span>
            </li>
          ))}
        </ul>
      )}
      <span className="flex gap-2">
        <Btn size="md" icon={FileText} onClick={onAll}>View All Notices</Btn>
        <Btn size="md" icon={Users} onClick={onContact}>Contact Coordinator</Btn>
      </span>
    </section>
  )
}
