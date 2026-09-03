'use client'

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import {
  CalendarDays,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ClipboardList,
  Download,
  ExternalLink,
  FileText,
  History,
  Loader2,
  MessageSquare,
  Pencil,
  Printer,
  RefreshCw,
  Users,
} from 'lucide-react'
import {
  ActivityPane,
  ApprovalsPane,
  DocumentsPane,
  OverviewPane,
  PapersPane,
  ProjectPane,
  TeamPane,
} from '@/components/faculty/batch/tabs'
import { Bar, Btn, CARD, Menu, Tag, fmtDateTime, statusTone } from '@/components/faculty/batch/primitives'
import {
  fetchBatchActivity,
  fetchBatchApprovals,
  fetchBatchDocuments,
  fetchBatchOverview,
  fetchBatchPapers,
  fetchBatchProject,
  fetchBatchTeam,
  downloadTeamList,
  downloadText,
  type BatchHeader,
} from '@/lib/faculty-batch-api'
import { ReviewsPane } from '@/components/faculty/batch/ReviewsPane'
import { fetchBatchReviews } from '@/lib/reviews-api'
import { cn } from '@/lib/utils'

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'team', label: 'Team Members' },
  { key: 'project', label: 'Project Details' },
  { key: 'papers', label: 'Base Papers' },
  { key: 'documents', label: 'Documents' },
  { key: 'reviews', label: 'Reviews' },
  { key: 'approvals', label: 'Approval History' },
  { key: 'activity', label: 'Activity Log' },
] as const
type TabKey = (typeof TABS)[number]['key']

const SUBTITLES: Record<TabKey, string> = {
  overview: 'Review submitted project information and documentation.',
  team: 'Review team members, verification status and team management',
  project: 'Review submitted project information and documentation.',
  papers: 'Review submitted project information and documentation.',
  documents: 'Review submitted project information and documentation.',
  reviews: 'Every review this batch has had, and the ones still to come.',
  approvals: 'Review submitted project information and documentation.',
  activity: 'Review submitted project information and documentation.',
}

const LOADERS: Record<TabKey, (code: string, params?: any) => Promise<any>> = {
  overview: fetchBatchOverview,
  team: fetchBatchTeam,
  project: fetchBatchProject,
  papers: fetchBatchPapers,
  documents: fetchBatchDocuments,
  reviews: fetchBatchReviews,
  approvals: fetchBatchApprovals,
  activity: fetchBatchActivity,
}

export default function BatchDetailPage() {
  const params = useParams<{ code: string }>()
  const router = useRouter()
  const code = decodeURIComponent(params?.code ?? '')

  const [tab, setTab] = useState<TabKey>('overview')
  const [data, setData] = useState<any>(null)
  // Which tab the payload in `data` belongs to. Without this the new pane
  // renders against the previous tab's payload for a frame - e.g. TeamPane
  // reading data.kpis off an Overview response - and crashes on undefined.
  const [loadedTab, setLoadedTab] = useState<TabKey | null>(null)
  const [header, setHeader] = useState<BatchHeader | null>(null)
  const [activityParams, setActivityParams] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const result = tab === 'activity'
        ? await fetchBatchActivity(code, activityParams)
        : await LOADERS[tab](code)
      setData(result)
      setLoadedTab(tab)
      setHeader(result.header)
    } catch (err: any) {
      const status = err?.response?.status
      if (status === 401) { router.push(`/login?next=/faculty/registrations/${code}`); return }
      setError(
        status === 404 ? `No batch found with code ${code}.`
          : status === 403 ? 'This area is for faculty accounts.'
            : 'Could not load this batch.'
      )
    } finally {
      setLoading(false)
    }
  }, [code, tab, activityParams, router])

  useEffect(() => { load() }, [load])

  const goToTab = useCallback((next: TabKey) => {
    setTab(next)
    setActivityParams({})
  }, [])

  const downloadApprovalHistory = useCallback(() => {
    const rows = loadedTab === 'approvals' ? data?.history ?? [] : []
    if (rows.length === 0) {
      setNotice('Open the Approval History tab first — the export is built from what it loads.')
      return
    }
    downloadText(
      `${code}-approval-history.csv`,
      ['Time,Cycle,Event,Status,Actor,Role,Duration (min),Detail',
        ...rows.map((h: any) => [h.occurred_at, h.cycle, h.title, h.status_label ?? '',
          h.actor ?? '', h.actor_role ?? '', h.duration_minutes ?? '', h.body ?? '']
          .map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n')
    )
    setNotice('Approval history exported.')
  }, [code, data, loadedTab])

  // Built from the payload already on screen, so the report says exactly what
  // the tab shows rather than re-querying and possibly diverging.
  const downloadPaperReport = useCallback(() => {
    if (loadedTab !== 'papers' || !data) {
      setNotice('Open the Base Papers tab first — the report is built from what it loads.')
      return
    }
    const p = data.primary
    const lines = [
      `Base paper report — ${code}`,
      '',
      'PRIMARY PAPER',
      ...(p
        ? [`Title: ${p.title ?? '—'}`, `Authors: ${p.authors ?? '—'}`,
           `Publication: ${p.publication ?? '—'} (${p.year ?? '—'})`,
           `DOI: ${p.doi ?? '—'}`, `Status: ${p.status}`,
           `Verified: ${p.verified_by ?? '—'} ${p.verified_at ?? ''}`]
        : ['No primary paper uploaded.']),
      '',
      `QUALITY: ${data.quality.overall ?? '—'}/100 ${data.quality.label ?? ''}`,
      `CHECKS: ${data.checks_passed}/${data.checks_total} passed`,
      ...data.checklist.map((c: any) => `  [${c.passed ? 'x' : ' '}] ${c.label} — ${c.detail ?? ''}`),
      '',
      `SUPPORTING PAPERS (${data.supporting.length})`,
      ...data.supporting.map((sp: any) =>
        `  ${sp.title} — ${sp.authors ?? '—'}, ${sp.source ?? '—'} ${sp.year ?? ''} [${sp.purpose ?? ''}]`),
    ]
    downloadText(`${code}-base-paper-report.txt`, lines.join('\n'))
    setNotice('Paper report downloaded.')
  }, [code, data, loadedTab])

  const paneProps = useMemo(
    () => ({
      data, code, onNotice: setNotice, reload: load, busy, onTab: goToTab,
      canManage: data?.can_manage !== false,
    }),
    [data, code, load, busy, goToTab]
  )

  // Each tab closes with the actions its own mock ends on. Keeping them in one
  // map means the footer stays a single element instead of seven near-copies.
  const footer = useMemo(() => {
    const notice = (m: string) => () => setNotice(m)
    const shared = {
      approvalReview: (
        <Link key="approval" href="/faculty/registrations?tab=approval"
          className="inline-flex items-center gap-2 whitespace-nowrap rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]">
          <ExternalLink className="h-4 w-4" /> Open Approval Review
        </Link>
      ),
    }

    const map: Record<TabKey, { note: string; actions: ReactNode[] }> = {
      overview: {
        note: 'Verified documents are locked. New updates create a new version and preserve previous versions in the audit history.',
        actions: [
          <Btn key="msg" size="md" icon={MessageSquare}
            onClick={notice('Messaging needs the email/notification pipeline \u2014 not wired up.')}>
            Message Batch Leader
          </Btn>,
          <Btn key="print" size="md" icon={Printer}
            onClick={notice('Printable reports need the reporting endpoint \u2014 see Reports & Analytics.')}>
            Print Registration
          </Btn>,
          shared.approvalReview,
        ],
      },
      team: {
        note: 'After registration approval, member replacement, removal or batch-leader changes require coordinator approval and are recorded in the audit log.',
        actions: [
          <Btn key="msg" size="md" icon={MessageSquare}
            onClick={notice('Messaging needs the email/notification pipeline \u2014 not wired up.')}>
            Send Message to Team
          </Btn>,
          <Btn key="dl" size="md" icon={Download}
            onClick={() => downloadTeamList(code)
              .then(() => setNotice('Team list downloaded.'))
              .catch(() => setNotice('The team list could not be downloaded.'))}>
            Download Team List
          </Btn>,
          shared.approvalReview,
        ],
      },
      project: {
        note: 'Project details are student-submitted and stay editable until the registration is approved. Every revision is kept in the activity log.',
        actions: [
          <Btn key="req" size="md" icon={FileText} onClick={() => goToTab('papers')}>View Requirements</Btn>,
          <Btn key="act" size="md" icon={History} onClick={() => goToTab('activity')}>View Change History</Btn>,
          shared.approvalReview,
        ],
      },
      papers: {
        note: 'The primary base paper cannot be removed after registration approval. Replacements require faculty approval and are recorded in the audit history.',
        actions: [
          <Btn key="chg" size="md" tone="amber" icon={RefreshCw}
            onClick={notice('Request Changes is recorded with the decision on the Approval Queue tab.')}>
            Request Paper Changes
          </Btn>,
          <Btn key="report" size="md" icon={Download} onClick={downloadPaperReport}>
            Download Paper Report
          </Btn>,
          <Btn key="docs" size="md" icon={FileText} onClick={() => goToTab('documents')}>Open Documents</Btn>,
          shared.approvalReview,
        ],
      },
      documents: {
        note: 'Verified documents are locked. New updates create a new version and preserve previous versions in the audit history.',
        actions: [
          <Btn key="queue" size="md" icon={ClipboardList} onClick={() => goToTab('approvals')}>View Queue</Btn>,
          <Btn key="act" size="md" icon={History} onClick={() => goToTab('activity')}>View Activity</Btn>,
          shared.approvalReview,
        ],
      },
      reviews: {
        note: 'A review that has been recorded cannot be edited. Correcting one means cancelling it, with a reason, and booking another.',
        actions: [
          <Btn key="cal" size="md" icon={CalendarDays}
            onClick={() => router.push('/faculty/project-reviews')}>
            Open Review Calendar
          </Btn>,
          <Btn key="log" size="md" icon={ClipboardList} onClick={() => goToTab('activity')}>
            Open Activity Log
          </Btn>,
        ],
      },
      approvals: {
        note: 'Every approval decision, remark and submitted version is permanently recorded. Students can view shared feedback but cannot see private faculty notes.',
        actions: [
          <Btn key="dl" size="md" icon={Download} onClick={downloadApprovalHistory}>
            Download Approval History
          </Btn>,
          <Btn key="msg" size="md" icon={MessageSquare}
            onClick={notice('Messaging needs the email/notification pipeline — not wired up.')}>
            Message Batch Leader
          </Btn>,
          <Btn key="log" size="md" icon={ClipboardList} onClick={() => goToTab('activity')}>
            Open Activity Log
          </Btn>,
          <Link key="complete" href="/faculty/registrations?tab=approval"
            className="inline-flex items-center gap-2 whitespace-nowrap rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]">
            <CheckCircle2 className="h-4 w-4" /> Complete Approval Review
          </Link>,
        ],
      },
      activity: {
        note: 'Activity logs are append-only and retained for audit. Times shown in your local timezone.',
        actions: [
          <Btn key="refresh" size="md" icon={RefreshCw} onClick={load}>Refresh</Btn>,
          shared.approvalReview,
        ],
      },
    }
    return map[tab]
  }, [tab, code, load, goToTab, downloadApprovalHistory, downloadPaperReport])

  return (
    <div className="space-y-2.5">
      {/* Breadcrumb + actions */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <nav className="mb-1 flex items-center gap-1 text-[11px] text-[#5A5F7A]">
            <Link href="/faculty/registrations" className="hover:text-[#4F46E5]">Registrations</Link>
            <span>/</span>
            <Link href="/faculty/registrations" className="hover:text-[#4F46E5]">Batch Registrations</Link>
            <span>/</span>
            <span className="text-[#1B1B3A]">{code}</span>
          </nav>
          <h1 className="text-[19px] font-bold leading-tight text-[#1B1B3A]">Batch Registration Details</h1>
          <p className="mt-0.5 text-[12px] text-[#5A5F7A]">{SUBTITLES[tab]}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/faculty/registrations"
            className="flex items-center gap-2 rounded-lg border border-[#DDE0EE] bg-white px-3 py-2 text-[12px] font-medium text-[#3A3F58] hover:bg-[#F7F8FC]">
            <ArrowLeft className="h-4 w-4" /> Back to Registrations
          </Link>
          <button type="button"
            onClick={() => setNotice('A printable registration PDF needs the reporting endpoint — see Reports & Analytics.')}
            className="flex items-center gap-2 rounded-lg border border-[#DDE0EE] bg-white px-3 py-2 text-[12px] font-medium text-[#3A3F58] hover:bg-[#F7F8FC]">
            <Download className="h-4 w-4" /> Download Registration
          </button>
          <button type="button"
            onClick={() => setNotice('Editing a submitted registration is a student-side action; faculty can request changes from the Approval Queue.')}
            className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-3 py-2 text-[12px] font-medium text-white hover:bg-[#4338CA]">
            <Pencil className="h-4 w-4" /> Edit Registration
          </button>
          <Menu items={[
            { label: 'Open Activity Log', onClick: () => goToTab('activity') },
            { label: 'Open Approval History', onClick: () => goToTab('approvals') },
            { label: 'Download approval history', onClick: downloadApprovalHistory },
            { label: 'Copy batch code', onClick: () => setNotice(`Batch code: ${code}`) },
          ]} />
        </div>
      </div>

      {data && loadedTab === tab && data.can_manage === false && (
        <div className="flex items-start gap-2 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] px-3 py-2 text-[12px] text-[#B45309]">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>
            You can read this batch because it is in your department, but you are not its guide,
            section coordinator or a department officer &mdash; so its actions are unavailable.
          </span>
        </div>
      )}

      {notice && (
        <div className="flex items-start justify-between gap-3 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] px-3 py-2 text-[12px] text-[#3A3F58]">
          <span>{notice}</span>
          <button type="button" onClick={() => setNotice('')} className="font-medium text-[#4F46E5]">Dismiss</button>
        </div>
      )}

      {/* Summary strip */}
      {header && (
        <section className={cn(CARD, 'grid gap-3 p-3 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,2fr)]')}>
          <div>
            <div className="flex flex-wrap items-baseline gap-4">
              <span>
                <p className="text-[10.5px] text-[#8A8FA8]">Batch Code</p>
                <p className="text-[18px] font-bold text-[#1B1B3A]">{header.batch_code}</p>
              </span>
              <span className="min-w-0">
                <p className="text-[10.5px] text-[#8A8FA8]">Project Title</p>
                <p className="truncate text-[16px] font-semibold text-[#1B1B3A]">{header.title ?? '—'}</p>
              </span>
            </div>
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              <Tag tone="indigo">{header.project_type ?? 'Project'}</Tag>
              <Tag tone={statusTone(header.status_key)}>{header.status}</Tag>
              {header.registration_complete && <Tag tone="green">Registration Complete</Tag>}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-4">
            {[
              ['Department', header.department],
              ['Year', header.year],
              ['Semester', header.semester],
              ['Section', header.section],
              ['Academic Year', header.academic_year],
              ['Faculty Guide', header.guide],
              ['Batch Created', fmtDateTime(header.created_at)],
              ['Last Updated', fmtDateTime(header.updated_at)],
            ].map(([label, value]) => (
              <span key={label as string}>
                <p className="text-[10.5px] text-[#8A8FA8]">{label}</p>
                <p className="truncate text-[12px] font-medium text-[#1B1B3A]">{value ?? '—'}</p>
              </span>
            ))}
            <span className="col-span-2 sm:col-span-4">
              <p className="text-[10.5px] text-[#8A8FA8]">Overall Completeness</p>
              <span className="flex items-center gap-2">
                <span className="flex-1"><Bar value={header.completeness} tone="bg-[#16A34A]" /></span>
                <span className="text-[12px] font-semibold text-[#1B1B3A]">{header.completeness}%</span>
              </span>
            </span>
          </div>
        </section>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-1 border-b border-[#E8E9F2]">
        {TABS.map((t) => (
          <button key={t.key} type="button" onClick={() => goToTab(t.key)}
            className={cn('border-b-2 px-3.5 py-2 text-[12px] transition-colors',
              tab === t.key ? 'border-[#4F46E5] font-medium text-[#4F46E5]'
                : 'border-transparent text-[#5A5F7A] hover:text-[#1B1B3A]')}>
            {t.label}
          </button>
        ))}
      </div>

      {loading && (!data || loadedTab !== tab) ? (
        <div className={cn(CARD, 'flex h-[320px] flex-col items-center justify-center gap-3 text-[#5A5F7A]')}>
          <Loader2 className="h-5 w-5 animate-spin text-[#4F46E5]" />
          <p className="text-[12px]">Loading {code}…</p>
        </div>
      ) : error ? (
        <div className={cn(CARD, 'flex h-[320px] flex-col items-center justify-center gap-3')}>
          <AlertTriangle className="h-6 w-6 text-[#DC2626]" />
          <p className="text-[12px] text-[#5A5F7A]">{error}</p>
          <button type="button" onClick={load}
            className="flex items-center gap-2 rounded-lg bg-[#4F46E5] px-4 py-2 text-[12px] font-medium text-white">
            <RefreshCw className="h-3.5 w-3.5" /> Retry
          </button>
        </div>
      ) : data && loadedTab === tab ? (
        <div className={cn(loading && 'opacity-60 transition-opacity')}>
          {tab === 'overview' && <OverviewPane {...paneProps} />}
          {tab === 'team' && <TeamPane {...paneProps} />}
          {tab === 'project' && <ProjectPane {...paneProps} />}
          {tab === 'papers' && <PapersPane {...paneProps} />}
          {tab === 'documents' && <DocumentsPane {...paneProps} />}
          {tab === 'reviews' && <ReviewsPane {...paneProps} />}
          {tab === 'approvals' && <ApprovalsPane {...paneProps} />}
          {tab === 'activity' && (
            <ActivityPane {...paneProps}
              onFilter={(p) => setActivityParams((prev) => ({ ...prev, ...p }))} />
          )}
        </div>
      ) : null}

      {/* Footer actions - specific to the tab in view */}
      <section className={cn(CARD, 'flex flex-wrap items-center gap-2 p-3')}>
        <p className="min-w-[240px] flex-1 text-[10.5px] leading-snug text-[#5A5F7A]">{footer.note}</p>
        {footer.actions}
      </section>
    </div>
  )
}
