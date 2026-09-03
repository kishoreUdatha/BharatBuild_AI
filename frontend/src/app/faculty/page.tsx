'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  CalendarPlus,
  ChevronDown,
  Clock,
  FolderClosed,
  Loader2,
  RefreshCw,
  TrendingUp,
  Upload,
  Users,
  UsersRound,
} from 'lucide-react'
import { ProgressOverview } from '@/components/faculty/ProgressOverview'
import {
  AiInsightBar,
  AttendanceTodayCard,
  AttentionPanel,
  BasePaperStatusCard,
  FacultyWorkloadCard,
  ProjectsAttentionTable,
  RecentSubmissionsCard,
  SectionPerformanceTable,
  UpcomingReviewsPanel,
} from '@/components/faculty/DashboardPanels'
import {
  errorMessage,
  fetchFacultyDashboard,
  fetchFacultyFilters,
  type DashboardQuery,
  type FacultyDashboard,
  type FacultyFilterOptions,
} from '@/lib/faculty-api'
import { FILTERS, KPI_TONES, type Tone } from '@/lib/faculty-data'
import { cn } from '@/lib/utils'

const KPI_ICONS: Record<string, typeof UsersRound> = {
  students: UsersRound,
  batches: FolderClosed,
  progress: TrendingUp,
  attendance: Users,
  reviews: Clock,
  attention: AlertTriangle,
}

/** Each KPI drills into the list it counts. */
const KPI_LINKS: Record<string, string> = {
  students: '/faculty/registrations',
  batches: '/faculty/project-tracking',
  progress: '/faculty/project-tracking',
  attendance: '/faculty/attendance',
  reviews: '/faculty/project-reviews',
  attention: '/faculty/project-tracking?attention=1',
}

const KPI_TILE: Record<Tone, string> = {
  indigo: 'bg-[#6D5AE6]',
  blue: 'bg-[#3B82F6]',
  green: 'bg-[#16A34A]',
  teal: 'bg-[#0D9488]',
  amber: 'bg-[#F59E0B]',
  red: 'bg-[#EF4444]',
  slate: 'bg-[#94A3B8]',
}

/** Filter keys map onto FilterOptions list names. */
const OPTION_KEYS: Record<string, keyof FacultyFilterOptions> = {
  department: 'departments',
  year: 'years',
  semester: 'semesters',
  section: 'sections',
  project_type: 'project_types',
}

export default function FacultyDashboardPage() {
  const router = useRouter()
  const [data, setData] = useState<FacultyDashboard | null>(null)
  const [options, setOptions] = useState<FacultyFilterOptions | null>(null)
  const [selected, setSelected] = useState<DashboardQuery>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async (query: DashboardQuery) => {
    setLoading(true)
    setError('')
    try {
      setData(await fetchFacultyDashboard(query))
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 401) {
        router.push('/login?next=/faculty')
        return
      }
      setError(
        status === 403
          ? 'This dashboard is for faculty accounts. Ask an admin to update your role.'
          : errorMessage(err, 'Could not load the dashboard. Please try again.')
      )
    } finally {
      setLoading(false)
    }
  }, [router])

  useEffect(() => {
    load({})
    fetchFacultyFilters()
      .then(setOptions)
      .catch(() => setOptions(null)) // fall back to the static lists
  }, [load])

  const applyFilter = (key: string, value: string) => {
    // The "All ..." entries clear the filter rather than sending a literal.
    const next: DashboardQuery = { ...selected, [key]: value.startsWith('All ') ? undefined : value }
    setSelected(next)
    load(next)
  }

  const optionsFor = (key: string, fallback: string[], allLabel?: string) => {
    const fromApi = options?.[OPTION_KEYS[key]] as string[] | undefined
    const values = fromApi?.length ? fromApi : fallback
    return allLabel ? [allLabel, ...values] : values
  }

  if (loading && !data) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-3 text-[#5A5F7A]">
        <Loader2 className="h-6 w-6 animate-spin text-[#4F46E5]" />
        <p className="text-[13px]">Loading dashboard…</p>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="flex h-[60vh] flex-col items-center justify-center gap-4">
        <AlertTriangle className="h-8 w-8 text-[#DC2626]" />
        <p className="max-w-md text-center text-[13px] text-[#5A5F7A]">{error}</p>
        <button
          type="button"
          onClick={() => load(selected)}
          className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-5 py-2.5 text-[13px] font-medium text-white hover:bg-[#4338CA]"
        >
          <RefreshCw className="h-4 w-4" /> Retry
        </button>
      </div>
    )
  }

  if (!data) return null

  const initials = data.faculty.name
    .split(' ')
    .map((part) => part[0])
    .slice(-2)
    .join('')
    .toUpperCase()

  return (
    <div className={cn('space-y-2', loading && 'opacity-60 transition-opacity')}>
      {/* Greeting and page actions share one row - a separate title block above
          this only repeated what the sidebar and the greeting already say. */}
      <section className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-[#E8E9F2] bg-white p-2.5">
        <h1 className="sr-only">Faculty Dashboard</h1>
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#DDE3F7] text-[12px] font-semibold text-[#2C2A6B]">
            {initials}
          </span>
          <div>
            <p className="text-[15px] font-semibold leading-tight text-[#1B1B3A]">
              Good morning, {data.faculty.name}
            </p>
            <p className="mt-0.5 text-[11px] text-[#5A5F7A]">
              {[data.faculty.department, data.faculty.sections, data.faculty.academic_year]
                .filter(Boolean)
                .join('  •  ')}
            </p>
          </div>
        </div>
        <div className="flex gap-2.5">
          <Link
            href="/faculty/project-reviews"
            className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]"
          >
            <CalendarPlus className="h-4 w-4" /> Schedule Review
          </Link>
          <Link
            href="/faculty/reports"
            className="flex items-center gap-2 rounded-lg border border-[#C7BDF5] bg-white px-4 py-2 text-[12px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF]"
          >
            <Upload className="h-4 w-4" /> Export Report
          </Link>
        </div>
      </section>

      {/* Filter bar */}
      <section className="grid grid-cols-2 gap-2.5 rounded-xl border border-[#E8E9F2] bg-white p-2 md:grid-cols-3 xl:grid-cols-6">
        {FILTERS.map((filter) => {
          // Guides are {id, name}: the option label is the name, its value the id.
          const entries =
            filter.key === 'guide_id'
              ? (options?.guides ?? []).map((g) => ({ value: g.id, label: g.name }))
              : optionsFor(filter.key, filter.fallback, filter.allLabel).map((v) => ({ value: v, label: v }))
          const all = filter.allLabel ?? 'All'
          const values = filter.key === 'guide_id' ? [{ value: all, label: all }, ...entries] : entries

          return (
            <div key={filter.key}>
              <label htmlFor={filter.key} className="mb-0.5 block text-[10.5px] text-[#5A5F7A]">
                {filter.label}
              </label>
              <div className="relative">
                <select
                  id={filter.key}
                  value={selected[filter.key] ?? all}
                  onChange={(e) => applyFilter(filter.key, e.target.value)}
                  disabled={loading}
                  className="h-8 w-full appearance-none rounded-lg border border-[#DDE0EE] bg-white pl-2.5 pr-8 text-[12px] text-[#1B1B3A] outline-none focus:border-[#4F46E5] disabled:opacity-60"
                >
                  {values.map((option) => (
                    <option key={option.value} value={option.value}>{option.label}</option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#8A8FA8]" />
              </div>
            </div>
          )
        })}
      </section>

      {/* KPI row */}
      <section className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
        {data.kpis.map((kpi) => {
          const Icon = KPI_ICONS[kpi.id] ?? UsersRound
          const tone = KPI_TONES[kpi.id] ?? 'slate'
          return (
            <Link
              key={kpi.id}
              href={KPI_LINKS[kpi.id] ?? '/faculty'}
              className="flex items-center gap-2.5 rounded-xl border border-[#E8E9F2] bg-white p-2 transition-colors hover:border-[#C7BDF5] hover:bg-[#FAFAFF]"
            >
              <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-xl', KPI_TILE[tone])}>
                <Icon className="h-4 w-4 text-white" />
              </span>
              <div className="min-w-0">
                <p className="text-[19px] font-bold leading-none text-[#1B1B3A]">{kpi.value}</p>
                <p className="mt-0.5 text-[11px] leading-tight text-[#5A5F7A]">{kpi.label}</p>
              </div>
            </Link>
          )
        })}
      </section>

      {/* A real 2x2 grid rather than two independently stacked columns: grid
          rows size to their tallest card, so Attention lines up with the
          progress chart and Upcoming Reviews lines up with the section table -
          top and bottom edges both. Stacking them as two columns let the
          right-hand cards start wherever the left-hand card happened to end. */}
      <div className="grid gap-2 xl:grid-cols-[minmax(0,1.66fr)_minmax(0,1fr)]">
        <ProgressOverview
          stages={data.stages}
          series={data.progress_series}
          seriesNames={data.series_names}
        />
        <AttentionPanel items={data.attention_items} />
        <SectionPerformanceTable rows={data.section_rows} />
        <UpcomingReviewsPanel reviews={data.upcoming_reviews} />
      </div>

      {/* Projects needing attention + summary cards */}
      <div className="grid gap-2 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <ProjectsAttentionTable rows={data.project_rows} />
        {/* 4-across matches the design, but only once this column is wide
            enough to give each card ~150px - which needs the viewport past
            ~1750px, not the 1536px `2xl` breakpoint. Below that: 2x2. */}
        <div className="grid gap-2 grid-cols-2 min-[1750px]:grid-cols-4">
          <AttendanceTodayCard data={data.attendance_today} />
          <RecentSubmissionsCard data={data.recent_submissions} />
          <FacultyWorkloadCard data={data.faculty_workload} />
          <BasePaperStatusCard data={data.base_paper_status} />
        </div>
      </div>

      {data.ai_insight && <AiInsightBar insight={data.ai_insight} />}
    </div>
  )
}
