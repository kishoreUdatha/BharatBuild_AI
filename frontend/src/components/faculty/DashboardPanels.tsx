'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  BarChart3,
  Briefcase,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  FileText,
  Sparkles,
  Target,
  UserRound,
  Users,
} from 'lucide-react'
import type {
  ApiAttentionItem,
  ApiProjectRow,
  ApiSectionRow,
  ApiUpcomingReview,
  FacultyDashboard,
} from '@/lib/faculty-api'
import { ATTENTION_TONES, BASE_PAPER_TONES, SECTION_TABLE_NOTE, type Tone } from '@/lib/faculty-data'
import { cn } from '@/lib/utils'

// Spacing across this file is deliberately tight: the whole dashboard is meant
// to fit one screen without the page scrolling.
const CARD = 'rounded-xl border border-[#E8E9F2] bg-white'
const CARD_TITLE = 'mb-2 whitespace-nowrap text-[12px] font-semibold text-[#1B1B3A]'
const HEADING = 'text-[14px] font-semibold text-[#1B1B3A]'
const CELL = 'px-2.5 py-1'

const SOFT_TILE: Record<Tone, string> = {
  green: 'bg-[#DCFCE7] text-[#16A34A]',
  amber: 'bg-[#FEF3C7] text-[#D97706]',
  red: 'bg-[#FEE2E2] text-[#DC2626]',
  indigo: 'bg-[#E0E7FF] text-[#4F46E5]',
  blue: 'bg-[#DBEAFE] text-[#2563EB]',
  teal: 'bg-[#CCFBF1] text-[#0D9488]',
  slate: 'bg-[#EEF0F7] text-[#5A5F7A]',
}

const TEXT_TONE: Record<Tone, string> = {
  green: 'text-[#16A34A]',
  amber: 'text-[#D97706]',
  red: 'text-[#DC2626]',
  indigo: 'text-[#4F46E5]',
  blue: 'text-[#2563EB]',
  teal: 'text-[#0D9488]',
  slate: 'text-[#5A5F7A]',
}

const ATTENTION_ICONS: Record<string, typeof UserRound> = {
  attendance: UserRound,
  'base-papers': FileText,
  overdue: CalendarDays,
  inactive: Users,
}

/** Where each attention row drills into, pre-filtered to those records. */
const ATTENTION_LINKS: Record<string, string> = {
  attendance: '/faculty/attendance?below=1',
  'base-papers': '/faculty/base-papers?status=missing',
  overdue: '/faculty/project-reviews?status=overdue',
  inactive: '/faculty/project-tracking?inactive=1',
}

// ------------------------------------------------- Faculty Attention Required

export function AttentionPanel({ items }: { items: ApiAttentionItem[] }) {
  return (
    <section className={cn(CARD, 'p-4')}>
      <h2 className={cn(HEADING, 'mb-2')}>Faculty Attention Required</h2>
      <ul className="space-y-1">
        {items.map((item) => {
          const Icon = ATTENTION_ICONS[item.id] ?? UserRound
          const tone = ATTENTION_TONES[item.id] ?? 'slate'
          return (
            <li key={item.id} className="flex items-center gap-2.5 rounded-lg border border-[#EEF0F7] px-2.5 py-1">
              <span className={cn('flex h-6 w-6 shrink-0 items-center justify-center rounded-lg', SOFT_TILE[tone])}>
                <Icon className="h-3.5 w-3.5" />
              </span>
              <span className="flex-1 truncate whitespace-nowrap text-[12px] text-[#3A3F58]">{item.label}</span>
              <span className={cn('text-[14px] font-semibold', TEXT_TONE[tone])}>{item.count}</span>
              <Link
                href={ATTENTION_LINKS[item.id] ?? '/faculty'}
                className="text-[11px] font-medium text-[#4F46E5] hover:underline"
              >
                View
              </Link>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

// --------------------------------------------------------- Upcoming Reviews

export function UpcomingReviewsPanel({ reviews }: { reviews: ApiUpcomingReview[] }) {
  return (
    <section className={cn(CARD, 'flex flex-col p-4')}>
      <h2 className={cn(HEADING, 'mb-2')}>Upcoming Reviews</h2>
      {reviews.length === 0 ? (
        <p className="py-4 text-center text-[12px] text-[#8A8FA8]">No reviews scheduled.</p>
      ) : (
        <ul className="space-y-1">
          {reviews.slice(0, 3).map((review) => (
            <li key={review.id} className="flex items-center gap-2.5 rounded-lg border border-[#EEF0F7] px-2.5 py-1">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-lg bg-[#EEF0F7] text-[#5A5F7A]">
                <CalendarDays className="h-3.5 w-3.5" />
              </span>
              <span className="w-[150px] shrink-0 whitespace-nowrap text-[11px] text-[#1B1B3A]">
                <span className="font-medium">{review.date}</span>
                <span className="ml-1.5 text-[#8A8FA8]">{review.time}</span>
              </span>
              <span className="w-[85px] shrink-0 text-[11px] font-medium text-[#1B1B3A]">{review.batch_code}</span>
              <span className="flex-1 truncate text-[11px] text-[#5A5F7A]">{review.review_type}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-auto grid grid-cols-2 gap-2 pt-2">
        <Link
          href="/faculty/project-reviews"
          className="flex items-center justify-center gap-2 rounded-lg border border-[#DDE0EE] py-1 text-[12px] text-[#3A3F58] hover:bg-[#F7F8FC]"
        >
          <CalendarDays className="h-3.5 w-3.5" /> Open Schedule
        </Link>
        <Link
          href="/faculty/calendar"
          className="flex items-center justify-center gap-2 rounded-lg border border-[#DDE0EE] py-1 text-[12px] text-[#3A3F58] hover:bg-[#F7F8FC]"
        >
          <CalendarDays className="h-3.5 w-3.5" /> View Calendar
        </Link>
      </div>
    </section>
  )
}

// ------------------------------------------- Department & Section Performance

const SECTION_BADGE: Record<string, string> = {
  'On Track': 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  'Need Attention': 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]',
  Excellent: 'border-[#BBF7D0] bg-[#F0FDF4] text-[#15803D]',
  'Not Assigned': 'border-[#E2E5F0] bg-[#F7F8FC] text-[#6B7280]',
}

const pct = (v: number | null) => (v === null ? '–' : `${v}%`)

export function SectionPerformanceTable({ rows }: { rows: ApiSectionRow[] }) {
  return (
    <section className={cn(CARD, 'p-4')}>
      <h2 className={cn(HEADING, 'mb-2')}>Department &amp; Section Performance</h2>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[700px] border-collapse text-[11.5px]">
          <thead>
            <tr className="whitespace-nowrap border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
              <th className={cn(CELL, 'text-left font-medium')}>Section</th>
              <th className={cn(CELL, 'text-center font-medium')}>Students</th>
              <th className={cn(CELL, 'text-center font-medium')}>Batches</th>
              <th className={cn(CELL, 'text-center font-medium')}>Registration</th>
              <th className={cn(CELL, 'text-center font-medium')}>Attendance</th>
              <th className={cn(CELL, 'text-center font-medium')}>Avg Progress</th>
              <th className={cn(CELL, 'text-center font-medium')}>Pending Reviews</th>
              <th className={cn(CELL, 'text-center font-medium')}>Status</th>
              <th className={cn(CELL, 'text-center font-medium')}>Action</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.section} className="border-b border-[#F1F2F8]">
                <td className={cn(CELL, 'whitespace-nowrap text-[#1B1B3A]')}>{row.section}</td>
                <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{row.students}</td>
                <td className={cn(CELL, 'text-center text-[#3A3F58]')}>{row.batches ?? '–'}</td>
                <td className={cn(CELL, 'text-center font-medium text-[#16A34A]')}>{pct(row.registration)}</td>
                <td className={cn(CELL, 'text-center font-medium text-[#0D9488]')}>{pct(row.attendance)}</td>
                <td className={cn(CELL, 'text-center font-medium text-[#2563EB]')}>{pct(row.progress)}</td>
                <td className={cn(CELL, 'text-center font-medium text-[#D97706]')}>{row.pending_reviews}</td>
                <td className={cn(CELL, 'text-center')}>
                  <span
                    className={cn(
                      'inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px]',
                      SECTION_BADGE[row.status] ?? SECTION_BADGE['Not Assigned']
                    )}
                  >
                    {row.status}
                  </span>
                </td>
                <td className={cn(CELL, 'text-center')}>
                  <Link
                    href={
                      row.section === 'Unassigned'
                        ? '/faculty/registrations?unassigned=1'
                        : `/faculty/registrations?section=${encodeURIComponent(row.section.replace('Section ', ''))}`
                    }
                    className="font-medium text-[#4F46E5] hover:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-1.5 text-[10px] text-[#8A8FA8]">{SECTION_TABLE_NOTE}</p>
    </section>
  )
}

// ---------------------------------------------- Projects Requiring Attention

/** Rows per page - sized to fill the card without pushing the dashboard taller. */
const PROJECTS_PER_PAGE = 4

export function ProjectsAttentionTable({ rows }: { rows: ApiProjectRow[] }) {
  const [page, setPage] = useState(0)

  const pageCount = Math.max(1, Math.ceil(rows.length / PROJECTS_PER_PAGE))
  // A filter change can shrink the list under the current page.
  const current = Math.min(page, pageCount - 1)
  const start = current * PROJECTS_PER_PAGE
  const visible = rows.slice(start, start + PROJECTS_PER_PAGE)

  return (
    <section className={cn(CARD, 'flex flex-col p-4')}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className={HEADING}>Projects Requiring Attention</h2>
        {rows.length > 0 && (
          <span className="whitespace-nowrap text-[11px] text-[#8A8FA8]">
            {start + 1}–{Math.min(start + PROJECTS_PER_PAGE, rows.length)} of {rows.length}
          </span>
        )}
      </div>

      {rows.length === 0 ? (
        <p className="py-6 text-center text-[12px] text-[#8A8FA8]">
          Every batch is on track - nothing needs attention.
        </p>
      ) : (
        <>
          <div className="flex-1 overflow-x-auto">
            <table className="w-full min-w-[540px] border-collapse text-[11.5px]">
              <thead>
                <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                  <th className={cn(CELL, 'text-left font-medium')}>Batch ID</th>
                  <th className={cn(CELL, 'text-left font-medium')}>Project Title</th>
                  <th className={cn(CELL, 'text-left font-medium')}>Issue</th>
                  <th className={cn(CELL, 'text-left font-medium')}>Progress</th>
                  <th className={cn(CELL, 'text-center font-medium')}>Risk Level</th>
                  <th className={cn(CELL, 'text-center font-medium')}>Action</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => {
                  const atRisk = row.risk === 'At Risk'
                  return (
                    <tr key={row.batch_id} className="border-b border-[#F1F2F8]">
                      <td className={cn(CELL, 'whitespace-nowrap text-[#1B1B3A]')}>{row.batch_code}</td>
                      <td className={cn(CELL, 'text-[#3A3F58]')}>{row.title}</td>
                      <td className={cn(CELL, 'text-[#5A5F7A]')}>{row.issue}</td>
                      <td className={CELL}>
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-[60px] overflow-hidden rounded-full bg-[#EEF0F7]">
                            <div
                              className={cn('h-full rounded-full', atRisk ? 'bg-[#EF4444]' : 'bg-[#F59E0B]')}
                              style={{ width: `${row.progress}%` }}
                            />
                          </div>
                          <span className="text-[10.5px] text-[#5A5F7A]">{row.progress}%</span>
                        </div>
                      </td>
                      <td className={cn(CELL, 'text-center')}>
                        <span
                          className={cn(
                            'inline-block whitespace-nowrap rounded-full border px-2 py-0.5 text-[10.5px]',
                            atRisk
                              ? 'border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]'
                              : 'border-[#FDE68A] bg-[#FFFBEB] text-[#B45309]'
                          )}
                        >
                          {row.risk}
                        </span>
                      </td>
                      <td className={cn(CELL, 'text-center')}>
                        <Link
                          href={`/faculty/project-tracking?attention=1&batch=${encodeURIComponent(row.batch_code)}`}
                          className="whitespace-nowrap font-medium text-[#4F46E5] hover:underline"
                        >
                          Open Batch
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {pageCount > 1 && (
            <div className="mt-2 flex items-center justify-end gap-1.5">
              <button
                type="button"
                onClick={() => setPage(current - 1)}
                disabled={current === 0}
                aria-label="Previous page"
                className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-transparent"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
              </button>
              {Array.from({ length: pageCount }, (_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setPage(i)}
                  aria-current={i === current ? 'page' : undefined}
                  className={cn(
                    'h-7 min-w-[28px] rounded-md border px-1.5 text-[11px]',
                    i === current
                      ? 'border-[#4F46E5] bg-[#4F46E5] font-medium text-white'
                      : 'border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC]'
                  )}
                >
                  {i + 1}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setPage(current + 1)}
                disabled={current >= pageCount - 1}
                aria-label="Next page"
                className="flex h-7 w-7 items-center justify-center rounded-md border border-[#DDE0EE] text-[#3A3F58] hover:bg-[#F7F8FC] disabled:opacity-40 disabled:hover:bg-transparent"
              >
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

// ------------------------------------------------------------ summary cards

function CardLink({ label, href }: { label: string; href: string }) {
  return (
    <Link
      href={href}
      className="mt-2 block w-full border-t border-[#EEF0F7] pt-1.5 text-center text-[11px] font-medium text-[#4F46E5] hover:underline"
    >
      {label}
    </Link>
  )
}

export function AttendanceTodayCard({ data }: { data: FacultyDashboard['attendance_today'] }) {
  return (
    <section className={cn(CARD, 'flex flex-col p-4')}>
      <h3 className={CARD_TITLE}>Attendance Today</h3>
      <div className="flex items-center gap-2">
        <Users className="h-3.5 w-3.5 text-[#16A34A]" />
        <span className="text-[18px] font-bold text-[#16A34A]">{data.present}</span>
        <span className="text-[11px] text-[#5A5F7A]">Present</span>
      </div>
      <div className="mt-2 flex items-end gap-5">
        <div>
          <p className="text-[18px] font-bold text-[#DC2626]">{data.absent}</p>
          <p className="text-[11px] text-[#5A5F7A]">Absent</p>
        </div>
        <div>
          <p className="text-[18px] font-bold text-[#D97706]">{data.late}</p>
          <p className="text-[11px] text-[#5A5F7A]">Late</p>
        </div>
      </div>
    </section>
  )
}

export function RecentSubmissionsCard({ data }: { data: FacultyDashboard['recent_submissions'] }) {
  return (
    <section className={cn(CARD, 'flex flex-col p-4')}>
      <h3 className={CARD_TITLE}>Recent Submissions</h3>
      <div className="flex flex-1 items-start gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#EEF0F7] text-[#5A5F7A]">
          <FileText className="h-3.5 w-3.5" />
        </span>
        <div>
          <p className="text-[19px] font-bold leading-none text-[#1B1B3A]">{data.count}</p>
          <p className="mt-1 text-[11px] leading-snug text-[#5A5F7A]">{data.caption}</p>
        </div>
      </div>
      <CardLink label="View Submissions" href="/faculty/project-tracking" />
    </section>
  )
}

export function FacultyWorkloadCard({ data }: { data: FacultyDashboard['faculty_workload'] }) {
  return (
    <section className={cn(CARD, 'flex flex-col p-4')}>
      <h3 className={CARD_TITLE}>Faculty Workload</h3>
      <div className="flex flex-1 items-start gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#E0E7FF] text-[#4F46E5]">
          <Briefcase className="h-3.5 w-3.5" />
        </span>
        <div>
          <p className="text-[19px] font-bold leading-none text-[#1B1B3A]">{data.assigned_batches}</p>
          <p className="mt-0.5 text-[11px] text-[#5A5F7A]">Assigned Batches</p>
          <p className="mt-1.5 text-[16px] font-bold leading-none text-[#1B1B3A]">{data.reviews_this_week}</p>
          <p className="mt-0.5 text-[11px] text-[#5A5F7A]">Reviews this week</p>
        </div>
      </div>
      <CardLink label="View Workload" href="/faculty/guides" />
    </section>
  )
}

export function BasePaperStatusCard({ data }: { data: FacultyDashboard['base_paper_status'] }) {
  return (
    <section className={cn(CARD, 'flex flex-col p-4')}>
      <h3 className={CARD_TITLE}>Base Paper Status</h3>
      <div className="flex flex-1 items-start gap-2.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#EEF0F7] text-[#5A5F7A]">
          <FileText className="h-3.5 w-3.5" />
        </span>
        <ul className="flex-1 space-y-1">
          {data.rows.map((row) => {
            const tone = BASE_PAPER_TONES[row.label] ?? 'slate'
            return (
              <li key={row.label} className="flex items-center justify-between gap-2">
                <span className={cn('shrink-0 text-[14px] font-bold', TEXT_TONE[tone])}>{row.count}</span>
                <span className={cn('truncate text-[11px]', TEXT_TONE[tone])}>{row.label}</span>
              </li>
            )
          })}
        </ul>
      </div>
      <CardLink label="View Base Papers" href="/faculty/base-papers" />
    </section>
  )
}

// --------------------------------------------------------------- AI insight

export function AiInsightBar({ insight }: { insight: string }) {
  return (
    <section className={cn(CARD, 'flex flex-wrap items-center gap-3 p-2')}>
      <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#EDE9FE] text-[#7C3AED]">
        <Sparkles className="h-3.5 w-3.5" />
      </span>
      <p className="flex-1 text-[12px] text-[#3A3F58]">
        <span className="font-semibold text-[#1B1B3A]">AI Insight:</span> {insight}
      </p>
      <div className="flex gap-2.5">
        <Link
          href="/faculty/ai-assistant"
          className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-1.5 text-[12px] font-medium text-white hover:bg-[#4338CA]"
        >
          <BarChart3 className="h-3.5 w-3.5" /> View AI Analysis
        </Link>
        <Link
          href="/faculty/attendance?below=1"
          className="flex items-center gap-2 rounded-lg border border-[#C7BDF5] px-4 py-1.5 text-[12px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF]"
        >
          <Target className="h-3.5 w-3.5" /> Create Action Plan
        </Link>
      </div>
    </section>
  )
}
