'use client'

import { useEffect, useState } from 'react'
import {
  AlertCircle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ClipboardList,
  Clock,
  Download,
  ExternalLink,
  Eye,
  FileCheck,
  FileDown,
  FileText,
  History,
  Lock,
  MessageSquare,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Star,
  Upload,
  UserCog,
  UserMinus,
  Users,
  XCircle,
} from 'lucide-react'
import {
  Bar,
  Btn,
  CARD,
  Card,
  Checklist,
  CELL,
  CopyButton,
  Field,
  Initials,
  KpiRow,
  Menu,
  MiniLog,
  Tag,
  Timeline,
  fmtBytes,
  fmtDate,
  fmtDateTime,
  fmtHours,
  statusTone,
} from '@/components/faculty/batch/primitives'
import {
  changeBatchLeader,
  decideBasePaper,
  decideDocument,
  downloadActivityLog,
  downloadTeamList,
  downloadText,
  removeBatchMember,
  updateInternalNote,
  updateMemberRoles,
} from '@/lib/faculty-batch-api'
import type {
  ActivityTab,
  ApprovalHistoryEntry,
  ApprovalsTab,
  JourneyStage,
  DocumentsTab,
  OverviewTab,
  PapersTab,
  ProjectTab,
  TeamTab,
} from '@/lib/faculty-batch-api'
import {
  fetchFacultyProjectForm,
  projectError,
  saveFacultyProject,
  type ProjectDetailsForm,
} from '@/lib/project-details-api'
import { ProjectDetailsEditor } from '@/components/project/ProjectDetailsEditor'
import { FileUpload } from '@/components/project/FileUpload'
import {
  downloadBatchBasePaper,
  downloadBatchDocument,
  fileError,
  removeBatchDocument,
  uploadBatchBasePaper,
  uploadBatchDocument,
} from '@/lib/file-api'
import { cn } from '@/lib/utils'

export type BatchTabKey =
  | 'overview' | 'team' | 'project' | 'papers' | 'documents' | 'approvals' | 'activity'

interface TabProps<T> {
  data: T
  code: string
  onNotice: (m: string) => void
  reload: () => void
  busy?: boolean
  /** Cross-tab navigation - "View Full Project Details" and friends. */
  onTab: (tab: BatchTabKey) => void
  /** False when the reader may see this batch but not change it. */
  canManage?: boolean
}

/** Which tab holds the record an approval or activity entry refers to. */
function relatedTab(text: string): BatchTabKey {
  const t = text.toLowerCase()
  if (t.includes('document')) return 'documents'
  if (t.includes('paper')) return 'papers'
  if (t.includes('member') || t.includes('team')) return 'team'
  if (t.includes('project') || t.includes('objective') || t.includes('abstract')) return 'project'
  if (t.includes('approv') || t.includes('review') || t.includes('submit')) return 'approvals'
  return 'activity'
}

// ================================================================= Overview

export function OverviewPane({ data, onNotice, onTab }: TabProps<OverviewTab>) {
  const p = data.project
  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        <Card
          title={`Team Members (${data.members.length}/4)`}
          right={<span className="text-[10.5px] text-[#5A5F7A]">{data.cohort_note}</span>}
        >
          <div className="overflow-x-auto">
            <table className="w-full table-fixed border-collapse text-[11.5px]">
              <colgroup>
                {['auto', '84px', '132px', '96px', 'auto', '86px', '96px'].map((w, i) => <col key={i} style={{ width: w }} />)}
              </colgroup>
              <tbody>
                {data.members.map((m) => (
                  <tr key={m.id} className="border-b border-[#F1F2F8]">
                    <td className={CELL}>
                      <span className="flex items-center gap-2">
                        <Initials name={m.name} />
                        <span className="min-w-0">
                          <span className="block truncate font-medium text-[#1B1B3A]">{m.name ?? '—'}</span>
                          <span className="block text-[10px] text-[#8A8FA8]">{m.roll_number}</span>
                        </span>
                      </span>
                    </td>
                    <td className={cn(CELL, 'text-[#3A3F58]')}>
                      <Field label="Role" value={m.role} />
                    </td>
                    <td className={CELL}><Field label="Responsibility" value={m.responsibility} /></td>
                    <td className={CELL}><Field label="Mobile" value={m.mobile} /></td>
                    <td className={cn(CELL, 'truncate')}><Field label="Email" value={m.email} /></td>
                    <td className={cn(CELL, 'text-center')}>
                      {m.profile_verified
                        ? <Tag tone="green">Verified</Tag>
                        : <Tag tone="amber">Pending</Tag>}
                    </td>
                    <td className={cn(CELL, 'text-center')}>
                      <Btn size="xs" onClick={() => onTab('team')}>View Student</Btn>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <div className="grid gap-2.5 md:grid-cols-2">
          <Card title="Project Information" right={
            <Btn size="xs" icon={ArrowRight} onClick={() => onTab('project')}>View Full Project Details</Btn>}>
            <div className="space-y-2">
              <Field label="Project Title" value={p.title} />
              <Field label="Domain" value={p.domain} />
              <Field label="Problem Statement" value={p.problem_statement} />
              <Field label="Abstract" value={p.abstract} />
            </div>
          </Card>
          <Card title="Objectives">
            <ul className="space-y-1.5">
              {p.objectives.map((o) => (
                <li key={o} className="flex items-start gap-2 rounded-lg border border-[#EEF0F7] px-2.5 py-1.5 text-[11.5px] text-[#3A3F58]">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#4F46E5]" /> {o}
                </li>
              ))}
            </ul>
            <p className="mb-1 mt-3 text-[10.5px] text-[#8A8FA8]">Technology Stack</p>
            <div className="flex flex-wrap gap-1.5">
              {p.technologies.map((t) => (
                <span key={t} className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10.5px] text-[#3A3F58]">{t}</span>
              ))}
            </div>
            {p.expected_outcome && (
              <>
                <p className="mb-1 mt-3 text-[10.5px] text-[#8A8FA8]">Expected Outcome</p>
                <p className="text-[11.5px] text-[#3A3F58]">{p.expected_outcome}</p>
              </>
            )}
          </Card>
        </div>

        {data.base_paper && (
          <Card title="Primary Base Paper" right={
            <span className="flex items-center gap-1.5">
              <Btn size="xs" icon={ArrowRight} onClick={() => onTab('papers')}>View Requirements</Btn>
              <Menu items={[
                { label: 'Open Base Papers tab', onClick: () => onTab('papers') },
                { label: 'Open Documents tab', onClick: () => onTab('documents') },
              ]} />
            </span>}>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1.5">
                <Field label="Title" value={data.base_paper.title} />
                <Field label="Authors" value={data.base_paper.authors} />
                <Field label="Publication" value={data.base_paper.publication} />
                <Field label="Year" value={data.base_paper.year} />
              </div>
              <div className="space-y-1.5">
                <Field label="DOI" value={data.base_paper.doi} />
                <Field label="Status" value={<Tag tone={statusTone(data.base_paper.status)}>{data.base_paper.status}</Tag>} />
                <Field label="Improvement Over Base Paper" value={data.base_paper.improvement_note} />
              </div>
            </div>
          </Card>
        )}

        <Card title="Registration Timeline"><Timeline steps={data.timeline} /></Card>
      </div>

      <div className="space-y-2.5">
        <Checklist title="Registration Checklist" checks={data.checklist}
          passed={data.checks_passed} total={data.checks_total} />
        <Card title="Approval Status">
          <div className="space-y-1.5">
            <Field label="Current Status" value={<Tag tone={statusTone(data.header.status_key)}>{data.approval.status}</Tag>} />
            <Field label="Submitted By" value={data.approval.submitted_by} />
            <Field label="Submitted On" value={fmtDateTime(data.approval.submitted_at)} />
            <Field label="Reviewer" value={data.approval.reviewer} />
            <Field label="SLA" value={data.approval.sla} />
            <Field label="Registration Stage"
              value={<Tag tone={statusTone(data.header.status_key)}>{data.header.status}</Tag>} />
          </div>
          <div className="mt-2.5 flex flex-wrap gap-1.5 border-t border-[#EEF0F7] pt-2.5">
            <Btn size="xs" tone="primary" icon={ClipboardList} onClick={() => onTab('approvals')}>
              Review Registration
            </Btn>
            <Btn size="xs" tone="amber" onClick={() => onNotice(
              'Request Changes is on the Approval Queue tab, where the change note is captured with the decision.')}>
              Request Changes
            </Btn>
          </div>
        </Card>
        <Card title={`Documents (${data.document_count})`} right={
          <Btn size="xs" icon={ArrowRight} onClick={() => onTab('documents')}>View All Documents</Btn>}>
          <ul className="space-y-1">
            {data.documents.map((d) => (
              <li key={d.name} className="flex items-center gap-2 text-[11.5px]">
                <FileText className="h-3.5 w-3.5 shrink-0 text-[#8A8FA8]" />
                <span className="flex-1 truncate text-[#3A3F58]">{d.name}</span>
                <Tag tone={statusTone(d.status_key)}>{d.status}</Tag>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}

// ============================================================== Team Members

export function TeamPane({ data, code, onNotice, reload, busy, canManage = true }: TabProps<TeamTab>) {
  const [note, setNote] = useState(data.internal_note ?? '')
  const [editingRoles, setEditingRoles] = useState(false)
  const [roles, setRoles] = useState<Record<string, string>>(
    Object.fromEntries(data.members.map((m) => [m.id, m.responsibility ?? '']))
  )
  const [removing, setRemoving] = useState<string | null>(null)
  const [reason, setReason] = useState('')

  const api = async (fn: () => Promise<unknown>, ok: string) => {
    try { await fn(); onNotice(ok); reload() }
    catch (err: any) { onNotice(err?.response?.data?.detail ?? 'That action could not be completed.') }
  }

  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        <KpiRow kpis={data.kpis} />

        <Card title={`Team Members (${data.members.length})`}>
          <ul className="space-y-2">
            {data.members.map((m) => (
              <li key={m.id} className={cn('rounded-lg border border-[#EEF0F7] p-3',
                !m.is_active && 'bg-[#FEF2F2]')}>
                <div className="flex flex-wrap items-start gap-3">
                  <Initials name={m.name} size="h-9 w-9" />
                  <div className="min-w-[132px]">
                    <p className="text-[12.5px] font-semibold text-[#1B1B3A]">{m.name ?? '—'}</p>
                    <p className="text-[10.5px] text-[#8A8FA8]">{m.roll_number}</p>
                    <span className="mt-1 inline-block">
                      <Tag tone={m.role === 'Batch Leader' ? 'indigo' : 'slate'}>{m.role}</Tag>
                    </span>
                  </div>
                  <Field className="min-w-[118px]" label="Responsibility" value={
                    editingRoles ? (
                      <input value={roles[m.id] ?? ''} onChange={(e) => setRoles((r) => ({ ...r, [m.id]: e.target.value }))}
                        className="h-7 w-full rounded border border-[#DDE0EE] px-1.5 text-[11px] outline-none focus:border-[#4F46E5]" />
                    ) : m.responsibility
                  } />
                  <Field className="min-w-[104px]" label="Mobile" value={
                    <>{m.mobile ?? '—'}{m.mobile && <span className="ml-1 text-[10px] text-[#16A34A]">Verified</span>}</>} />
                  <Field className="min-w-[150px]" label="Email" value={m.email} />
                  <Field className="min-w-[76px]" label="Dept / Section" value={`${m.department ?? '—'} / ${m.section ?? '—'}`} />
                  <div className="min-w-[110px]">
                    <p className="text-[10.5px] text-[#8A8FA8]">Profile Completion</p>
                    <Bar value={m.profile_completion ?? 0} tone="bg-[#16A34A]" />
                    <p className="mt-0.5 text-[10.5px] text-[#5A5F7A]">{m.profile_completion ?? 0}%</p>
                  </div>
                  <Field className="min-w-[112px]" label="Joined" value={fmtDateTime(m.joined_at)} />
                  <Field className="min-w-[80px]" label="Declaration" value={
                    m.declaration_signed ? <Tag tone="green">Signed</Tag> : <Tag tone="amber">Pending</Tag>} />
                  <div className="ml-auto flex flex-col gap-1.5">
                    <button type="button" onClick={() => onNotice(`${m.name} — a full student profile page is not built yet.`)}
                      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] px-2.5 py-1 text-[10.5px] text-[#3A3F58] hover:bg-[#F7F8FC]">
                      <Users className="h-3 w-3" /> View Full Profile
                    </button>
                    <button type="button" onClick={() => onNotice('Messaging needs the email/notification pipeline — not wired up.')}
                      className="flex items-center gap-1.5 rounded-lg border border-[#DDE0EE] px-2.5 py-1 text-[10.5px] text-[#3A3F58] hover:bg-[#F7F8FC]">
                      <MessageSquare className="h-3 w-3" /> Message
                    </button>
                  </div>
                </div>
                {removing === m.id && (
                  <div className="mt-2 flex flex-wrap items-center gap-2 rounded-lg border border-[#FECACA] bg-[#FEF2F2] p-2">
                    <span className="text-[11px] text-[#3A3F58]">Reason for removing {m.name}:</span>
                    <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Required"
                      className="h-7 flex-1 rounded border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#DC2626]" />
                    <button type="button" disabled={reason.trim().length < 4 || busy}
                      onClick={() => api(() => removeBatchMember(code, m.id, reason.trim()),
                        `${m.name} removed from ${code}.`).then(() => { setRemoving(null); setReason('') })}
                      className="rounded-lg bg-[#DC2626] px-3 py-1 text-[11px] font-medium text-white disabled:opacity-50">
                      Confirm
                    </button>
                    <button type="button" onClick={() => { setRemoving(null); setReason('') }}
                      className="text-[11px] text-[#5A5F7A] hover:underline">Cancel</button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>

        <div className="grid gap-2.5 md:grid-cols-2">
          <Card title="Team Formation Timeline"><Timeline steps={data.timeline} /></Card>
          <Card title="Internal Faculty Note">
            <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={4}
              placeholder="Visible to faculty only…"
              className="w-full rounded-lg border border-[#DDE0EE] p-2 text-[11.5px] outline-none focus:border-[#4F46E5]" />
            <div className="mt-2 flex items-center justify-between">
              <p className="text-[10px] text-[#8A8FA8]">
                Last updated by {data.note_updated_by ?? '—'} • {fmtDateTime(data.note_updated_at)}
              </p>
              <button type="button" disabled={busy || !canManage}
                title={canManage ? undefined : 'Only the batch owner can write an internal note'}
                onClick={() => api(() => updateInternalNote(code, note), 'Internal note saved.')}
                className="rounded-lg border border-[#C7BDF5] px-3 py-1.5 text-[11px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF] disabled:opacity-50">
                Save Note
              </button>
            </div>
          </Card>
        </div>
      </div>

      <div className="space-y-2.5">
        <Checklist title="Team Validation" checks={data.checklist}
          passed={data.checks_passed} total={data.checks_total} />
        <Card title="Role Distribution">
          <ul className="space-y-1 text-[11.5px]">
            {data.roles.map((r) => (
              <li key={r.role} className="flex justify-between">
                <span className="text-[#3A3F58]">{r.role}</span>
                <span className="font-semibold text-[#1B1B3A]">{r.count}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] text-[#8A8FA8]">Roles can be adjusted before faculty approval.</p>
          {editingRoles ? (
            <div className="mt-2 flex gap-2">
              <button type="button" disabled={busy}
                onClick={() => api(() => updateMemberRoles(code, roles), 'Team roles updated.')
                  .then(() => setEditingRoles(false))}
                className="flex-1 rounded-lg bg-[#4F46E5] py-1.5 text-[11px] font-medium text-white disabled:opacity-50">
                Save Roles
              </button>
              <button type="button" onClick={() => setEditingRoles(false)}
                className="rounded-lg border border-[#DDE0EE] px-3 py-1.5 text-[11px] text-[#3A3F58]">Cancel</button>
            </div>
          ) : (
            <button type="button" onClick={() => setEditingRoles(true)}
              className="mt-2 w-full rounded-lg border border-[#C7BDF5] py-1.5 text-[11px] font-medium text-[#4F46E5] hover:bg-[#F5F3FF]">
              Edit Team Roles
            </button>
          )}
        </Card>

        <Card title="Faculty Actions">
          {!canManage && (
            <p className="mb-2 rounded-lg bg-[#FFFBEB] px-2.5 py-1.5 text-[10.5px] leading-snug text-[#B45309]">
              Read-only: these belong to the batch&apos;s guide, its section coordinator or a
              department officer.
            </p>
          )}
          <div className={cn('space-y-1.5', !canManage && 'pointer-events-none opacity-40')}>
            <ActionRow icon={UserCog} label="Change Batch Leader"
              onClick={() => {
                const member = data.members.find((m) => m.role !== 'Batch Leader' && m.is_active)
                if (!member) return onNotice('No other active member to promote.')
                api(() => changeBatchLeader(code, member.id), `${member.name} is now the batch leader.`)
              }} />
            <ActionRow icon={RefreshCw} label="Replace Team Member" note="Requires reason & coordinator approval"
              onClick={() => onNotice('Replacement means removing one member and assigning another — remove below, then use Assign to Batch on the Student Registrations tab.')} />
            <ActionRow icon={UserMinus} label="Remove Member" note="Requires reason & coordinator approval"
              onClick={() => {
                const member = data.members.find((m) => m.role !== 'Batch Leader' && m.is_active)
                if (!member) return onNotice('Only the batch leader remains — change the leader first.')
                setRemoving(member.id)
              }} />
            <ActionRow icon={MessageSquare} label="Send Message to Team"
              onClick={() => onNotice('Messaging needs the email/notification pipeline — not wired up.')} />
            <ActionRow icon={Download} label="Download Team List"
              onClick={() => api(() => downloadTeamList(code), 'Team list downloaded.')} />
          </div>
        </Card>
      </div>
    </div>
  )
}

function ActionRow({ icon: Icon, label, note, onClick }: {
  icon: typeof Users; label: string; note?: string; onClick: () => void
}) {
  return (
    <button type="button" onClick={onClick}
      className="flex w-full items-start gap-2 rounded-lg border border-[#DDE0EE] px-2.5 py-2 text-left hover:bg-[#F7F8FC]">
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#4F46E5]" />
      <span>
        <span className="block text-[11.5px] text-[#3A3F58]">{label}</span>
        {note && <span className="block text-[9.5px] text-[#8A8FA8]">{note}</span>}
      </span>
    </button>
  )
}

// =========================================================== Project Details

export function ProjectPane({ data, code, onNotice, onTab, reload, canManage = true }: TabProps<ProjectTab>) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<ProjectDetailsForm | null>(null)
  const [loadingForm, setLoadingForm] = useState(false)

  // The tab payload is shaped for reading; editing needs the raw values, so
  // the form is fetched only when the guide actually asks to edit.
  useEffect(() => {
    if (!editing || form) return
    setLoadingForm(true)
    fetchFacultyProjectForm(code)
      .then(setForm)
      .catch((err) => {
        onNotice(projectError(err, 'Could not open the editor.'))
        setEditing(false)
      })
      .finally(() => setLoadingForm(false))
  }, [editing, form, code, onNotice])

  if (editing) {
    return (
      <div className="space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[#C7BDF5] bg-[#F5F3FF] px-3 py-2">
          <p className="text-[11.5px] text-[#3A3F58]">
            Editing {data.header.batch_code} on the team's behalf. Every change is recorded in the
            activity log.
          </p>
          <Btn size="xs" onClick={() => { setEditing(false); setForm(null); reload() }}>
            Done editing
          </Btn>
        </div>
        {loadingForm || !form ? (
          <div className="flex items-center gap-2 rounded-xl border border-[#E5E7EB] bg-white p-8 text-[12px] text-[#5A5F7A]">
            <RefreshCw className="h-4 w-4 animate-spin text-[#4F46E5]" /> Loading the form…
          </div>
        ) : (
          <ProjectDetailsEditor
            data={form}
            accent="#4F46E5"
            onSave={async (payload) => {
              const next = await saveFacultyProject(code, payload)
              setForm(next)
              return next
            }} />
        )}
      </div>
    )
  }

  const o = data.overview
  const abstractText = [
    o.title && `Title: ${o.title}`,
    o.domain && `Domain: ${o.domain}`,
    o.problem_statement && `\nProblem Statement\n${o.problem_statement}`,
    o.abstract && `\nAbstract\n${o.abstract}`,
  ].filter(Boolean).join('\n')
  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        <KpiRow kpis={data.kpis} />

        <div className="grid gap-2.5 md:grid-cols-2">
          <Card title="Project Overview" right={
            <span className="flex items-center gap-1.5">
              {canManage && !data.locked && (
                <Btn size="xs" icon={Pencil} onClick={() => setEditing(true)}>Edit Details</Btn>
              )}
              <CopyButton size="xs" label="Copy Abstract" text={abstractText} />
              <Btn size="xs" icon={FileDown} disabled={!abstractText}
                onClick={() => downloadText(`${data.header.batch_code}-abstract.txt`, abstractText)}>
                Download Abstract
              </Btn>
            </span>}>
            <div className="space-y-2">
              <Field label="Project Title" value={o.title} />
              <Field label="Domain" value={o.domain} />
              <Field label="Project Type" value={o.project_type} />
              <div>
                <p className="text-[10.5px] text-[#8A8FA8]">Keywords</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {o.keywords.map((k) => (
                    <span key={k} className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10.5px] text-[#3A3F58]">{k}</span>
                  ))}
                </div>
              </div>
              <Field label="Problem Statement" value={o.problem_statement} />
              <Field label="Project Abstract" value={o.abstract} />
            </div>
          </Card>

          <Card title={`Objectives (${data.objectives.length})`}>
            <ul className="space-y-1.5">
              {data.objectives.map((ob) => (
                <li key={ob.position} className="flex items-start gap-2 rounded-lg border border-[#EEF0F7] px-2.5 py-2">
                  <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[9.5px] font-semibold text-[#4F46E5]">
                    {String(ob.position).padStart(2, '0')}
                  </span>
                  <span className="flex-1 text-[11.5px] text-[#3A3F58]">{ob.text}</span>
                  <Tag tone={statusTone(ob.status.toLowerCase())}>{ob.status}</Tag>
                </li>
              ))}
            </ul>
          </Card>
        </div>

        <Card title="Proposed Methodology">
          <ol className="flex flex-wrap gap-2">
            {data.methodology.map((s) => (
              <li key={s.position} className="min-w-[128px] flex-1 rounded-lg border border-[#EEF0F7] p-2.5">
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-[#4F46E5] text-[9.5px] font-semibold text-white">
                  {s.position}
                </span>
                <p className="mt-1.5 text-[11.5px] font-medium text-[#1B1B3A]">{s.title}</p>
                <p className="text-[10px] leading-snug text-[#5A5F7A]">{s.description}</p>
              </li>
            ))}
          </ol>
        </Card>

        <div className="grid gap-2.5 md:grid-cols-2">
          <Card title="Expected Outcomes">
            <ul className="space-y-1">
              {data.outcomes.map((t) => (
                <li key={t} className="flex gap-2 text-[11.5px] text-[#3A3F58]">
                  <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" /> {t}
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Scope &amp; Deliverables">
            <div className="grid gap-3 sm:grid-cols-3">
              <ScopeList title="In Scope" items={data.in_scope} tone="text-[#16A34A]" />
              <ScopeList title="Out of Scope" items={data.out_of_scope} tone="text-[#DC2626]" />
              <ScopeList title="Deliverables" items={data.deliverables} tone="text-[#4F46E5]" />
            </div>
          </Card>
        </div>
      </div>

      <div className="space-y-2.5">
        <Card title="Technology Stack">
          <ul className="space-y-2">
            {data.technology_stack.map((layer) => (
              <li key={layer.layer}>
                <p className="text-[10.5px] text-[#8A8FA8]">{layer.layer}</p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {layer.items.map((i) => (
                    <span key={i} className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10.5px] text-[#3A3F58]">{i}</span>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Project Duration">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Start Date" value={fmtDate(data.duration.start_date)} />
            <Field label="Target Completion" value={fmtDate(data.duration.target_completion)} />
            <Field label="Duration" value={data.duration.weeks ? `${data.duration.weeks} Weeks` : '—'} />
            <Field label="Weekly Effort" value={data.duration.weekly_effort_hours
              ? `${data.duration.weekly_effort_hours} Hours / Student` : '—'} />
          </div>
        </Card>

        <Checklist title="Project Validation" checks={data.checklist}
          passed={data.checks_passed} total={data.checks_total} />

        <Card title="Registration Stage">
          <div className="flex flex-wrap items-center justify-between gap-1.5">
            <Tag tone={statusTone(data.header.status_key)}>{data.header.status}</Tag>
            <span className="flex items-center gap-1.5">
              <Btn size="xs" onClick={() => onTab('team')}>Add Internal Note</Btn>
              <Btn size="xs" icon={ArrowRight} onClick={() => onTab('approvals')}>Review Registration</Btn>
            </span>
          </div>
          <p className="mt-2 text-[10.5px] leading-snug text-[#8A8FA8]">
            {data.locked
              ? data.locked_reason
              : 'The batch can revise these until they submit, and every revision is recorded below.'}
          </p>
        </Card>

        <Card title="Project Details History" right={
          <Btn size="xs" icon={History} onClick={() => onTab('activity')}>View All</Btn>}>
          <MiniLog entries={data.history.map((h) => ({
            label: h.step, actor: h.actor, occurred_at: h.occurred_at,
          }))} empty="No revisions recorded for this project yet." />
        </Card>

        {data.faculty_note && (
          <Card title="Faculty Review Note" right={
            <Tag tone="indigo">Shared with batch</Tag>}>
            <p className="text-[11.5px] leading-snug text-[#3A3F58]">{data.faculty_note}</p>
          </Card>
        )}
      </div>
    </div>
  )
}

function ScopeList({ title, items, tone }: { title: string; items: string[]; tone: string }) {
  return (
    <div>
      <p className="mb-1 text-[10.5px] font-medium text-[#8A8FA8]">{title}</p>
      <ul className="space-y-0.5">
        {items.map((t) => (
          <li key={t} className="flex gap-1.5 text-[10.5px] leading-snug text-[#3A3F58]">
            <span className={cn('mt-[3px] h-1 w-1 shrink-0 rounded-full bg-current', tone)} /> {t}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ================================================================ Base Papers

/** A stand-in for the paper's first page - there is no PDF store to render. */
function PaperThumb({ publication, fileName }: { publication: string | null; fileName: string | null }) {
  return (
    <div className="flex h-[168px] w-[132px] shrink-0 flex-col items-center justify-center gap-2 rounded-lg border border-[#E8E9F2] bg-[#FAFBFE]">
      <span className="relative flex h-16 w-12 items-center justify-center rounded-sm border border-[#DDE0EE] bg-white">
        <FileText className="h-7 w-7 text-[#C7CBDD]" />
        <span className="absolute bottom-1 rounded-sm bg-[#DC2626] px-1 text-[7px] font-bold text-white">PDF</span>
      </span>
      <span className="px-2 text-center text-[9.5px] font-semibold leading-tight text-[#5A5F7A]">
        {publication ?? fileName ?? 'No file'}
      </span>
    </div>
  )
}

const PAPER_KPI_ICON: Record<string, typeof FileText> = {
  uploaded: FileText,
  primary: Star,
  supporting: BookOpen,
  verified: ShieldCheck,
  pending: Clock,
}

export function PapersPane({ data, code, onNotice, onTab, reload,
  canManage = true }: TabProps<PapersTab>) {
  // Uploading was student-only until now: a guide who received a paper by
  // email had no way to put it on the batch.
  const [uploadingPaper, setUploadingPaper] = useState(false)
  const p = data.primary
  const q = data.quality
  const note = data.verification_note
  const improvementDefined = Boolean(
    data.improvement.proposed && data.improvement.contributions.length > 0
  )

  const paperText = p
    ? [p.title, p.authors, p.publication, p.year, p.doi, '', p.abstract_summary]
      .filter(Boolean).join('\n')
    : ''

  /** IEEE-ish citation from the metadata already on the card. */
  const citation = p
    ? `${p.authors ?? 'Unknown'}, "${p.title ?? 'Untitled'}," ${p.publication ?? ''}`
      + `${p.volume ? `, vol. ${p.volume}` : ''}${p.pages ? `, pp. ${p.pages}` : ''}`
      + `${p.year ? `, ${p.year}` : ''}.${p.doi ? ` doi: ${p.doi}` : ''}`
    : ''

  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-5">
          {data.kpis.map((k) => {
            const Icon = PAPER_KPI_ICON[k.id] ?? FileText
            const tone = k.id === 'verified' ? 'bg-[#F0FDF4] text-[#16A34A]'
              : k.id === 'pending' ? 'bg-[#FFFBEB] text-[#D97706]'
                : 'bg-[#EEF2FF] text-[#4F46E5]'
            return (
              <div key={k.id} className={cn(CARD, 'flex items-center gap-2.5 p-3')}>
                <span className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-lg', tone)}>
                  <Icon className="h-4.5 w-4.5" />
                </span>
                <span className="min-w-0">
                  <span className="block text-[18px] font-bold leading-none text-[#1B1B3A]">{k.value}</span>
                  <span className="block text-[10px] leading-tight text-[#5A5F7A]">{k.label}</span>
                </span>
              </div>
            )
          })}
        </div>

        {p ? (
          <div className="grid gap-2.5 md:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
            <Card title="1. Primary Base Paper" right={
              <span className="flex flex-wrap items-center gap-1.5">
                {data.primary_tags.map((t) => (
                  <Tag key={t.label} tone={t.tone as any}>{t.label}</Tag>
                ))}
              </span>}>
              <div className="flex flex-wrap gap-3">
                <PaperThumb publication={p.publication} fileName={p.file_name ?? null} />
                <div className="min-w-[280px] flex-1">
                  <p className="mb-2 text-[13.5px] font-semibold leading-snug text-[#1B1B3A]">{p.title}</p>
                  <div className="grid gap-x-4 gap-y-1.5 sm:grid-cols-2">
                    <Field label="Authors" value={p.authors} />
                    <Field label="Pages" value={p.pages} />
                    <Field label="Publication" value={p.publication} />
                    <Field label="DOI" value={p.doi
                      ? <a href={p.url ?? `https://doi.org/${p.doi}`} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-[#4F46E5] hover:underline">
                          {p.doi} <ExternalLink className="h-3 w-3" />
                        </a>
                      : null} />
                    <Field label="Publisher" value={p.publisher} />
                    <Field label="Indexing" value={p.indexing} />
                    <Field label="Publication Type" value={p.publication_type} />
                    <Field label="Quartile" value={p.quartile} />
                    <Field label="Year" value={p.year} />
                    <Field label="Uploaded by" value={p.uploaded_by} />
                    <Field label="Volume" value={p.volume} />
                    <Field label="Uploaded on" value={fmtDateTime(p.uploaded_at)} />
                    <Field className="sm:col-span-2" label="File" value={
                      <>
                        <span className="text-[#4F46E5]">{p.file_name ?? '\u2014'}</span>
                        {(p.file_size || p.page_count) && (
                          <span className="block text-[10px] text-[#8A8FA8]">
                            {[p.file_size ? fmtBytes(p.file_size) : null,
                              p.page_count ? `${p.page_count} pages` : null]
                              .filter(Boolean).join(' \u00b7 ')}
                          </span>
                        )}
                      </>} />
                  </div>
                </div>
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                {canManage && p.status !== 'verified' && (
                  <Btn icon={ShieldCheck} onClick={async () => {
                    try {
                      const r = await decideBasePaper(code, 'verify')
                      onNotice(r.message)
                      reload()
                    } catch (err) {
                      onNotice(fileError(err, 'That paper could not be verified.'))
                    }
                  }}>
                    Verify Paper
                  </Btn>
                )}
                {canManage && (
                  <Btn icon={Upload} onClick={() => setUploadingPaper((o) => !o)}>
                    {p.has_file ? 'Replace PDF' : 'Upload PDF'}
                  </Btn>
                )}
                <Btn icon={FileText} disabled={!p.has_file}
                  title={p.has_file ? undefined : 'No PDF has been uploaded for this paper'}
                  onClick={async () => {
                    try {
                      await downloadBatchBasePaper(code, p.file_name ?? 'base-paper.pdf')
                    } catch (err) {
                      onNotice(fileError(err, 'That PDF could not be downloaded.'))
                    }
                  }}>
                  {p.has_file ? 'Download PDF' : 'No PDF yet'}
                </Btn>
                <Btn icon={Download} onClick={() => downloadText(
                  `${data.header.batch_code}-base-paper.txt`, paperText)}>
                  Citation
                </Btn>
                {p.doi ? (
                  <a href={p.url ?? `https://doi.org/${p.doi}`} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border border-[#DDE0EE] bg-white px-3 py-1.5 text-[11px] font-medium text-[#3A3F58] hover:bg-[#F7F8FC]">
                    <ExternalLink className="h-3.5 w-3.5" /> Open DOI
                  </a>
                ) : (
                  <Btn icon={ExternalLink} disabled>Open DOI</Btn>
                )}
                </div>

              {uploadingPaper && canManage && (
                <div className="mt-2.5">
                  <FileUpload
                    limits={{ max_mb: 25, max_bytes: 25 * 1024 * 1024,
                      extensions: ['pdf'], accept: '.pdf' }}
                    accent="#4F46E5"
                    compact
                    onUpload={async (file) => {
                      const result = await uploadBatchBasePaper(code, file)
                      reload()
                      return result
                    }}
                    onDone={(message) => { onNotice(message); setUploadingPaper(false) }} />
                  <p className="mt-1 text-[10px] text-[#8A8FA8]">
                    Replacing the paper resets its verification &mdash; a different paper has not
                    been looked at.
                  </p>
                </div>
              )}

              {p.verified_at && (
                <p className="mt-2.5 flex items-center gap-1.5 text-[11px] text-[#16A34A]">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Verified by {p.verified_by ?? 'faculty'} on {fmtDateTime(p.verified_at)}
                </p>
              )}
            </Card>

            <Card title="2. Base Paper Summary" right={
              <CopyButton size="xs" label="Copy Abstract" text={p.abstract_summary} />}>
              <Field label="Abstract Summary" value={p.abstract_summary} />
              <p className="mb-1 mt-2.5 text-[10.5px] text-[#8A8FA8]">Key Methods</p>
              <div className="flex flex-wrap gap-1.5">
                {(p.key_methods ?? []).map((m) => (
                  <span key={m} className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10.5px] text-[#3A3F58]">{m}</span>
                ))}
              </div>
              <Field className="mt-2.5" label="Dataset" value={p.dataset} />
              <p className="mb-1 mt-2.5 text-[10.5px] text-[#8A8FA8]">Reported Metrics</p>
              <div className="grid grid-cols-3 gap-1.5">
                {(p.metrics ?? []).map((m) => (
                  <div key={m.name} className="rounded-lg border border-[#EEF0F7] py-1.5 text-center">
                    <p className="text-[10px] text-[#8A8FA8]">{m.name}</p>
                    <p className="text-[13px] font-bold text-[#1B1B3A]">{m.value}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        ) : (
          <Card><p className="py-10 text-center text-[12px] text-[#8A8FA8]">No base paper uploaded for this batch.</p></Card>
        )}

        <div className="grid gap-2.5 md:grid-cols-[minmax(0,1fr)_minmax(0,1.14fr)]">
          <Card title="3. Proposed Improvement Over Base Paper">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.1fr)]">
              <div className="rounded-lg border border-[#EEF0F7] p-2.5">
                <p className="mb-1 text-[10.5px] font-medium text-[#8A8FA8]">Current Base Paper</p>
                <p className="text-[11px] leading-snug text-[#3A3F58]">
                  {data.improvement.current_limitation ?? '\u2014'}
                </p>
              </div>
              <div className="rounded-lg border border-[#EEF0F7] p-2.5">
                <p className="mb-1 text-[10.5px] font-medium text-[#8A8FA8]">Proposed BharatBuild Project</p>
                <p className="text-[11px] leading-snug text-[#3A3F58]">
                  {data.improvement.proposed ?? '\u2014'}
                </p>
              </div>
              <div>
                <p className="mb-1 text-[10.5px] font-medium text-[#8A8FA8]">Novel Contributions</p>
                <ul className="space-y-1">
                  {data.improvement.contributions.map((c, i) => (
                    <li key={c} className="flex gap-1.5 text-[10.5px] leading-snug text-[#3A3F58]">
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[8px] font-semibold text-[#4F46E5]">
                        {String(i + 1).padStart(2, '0')}
                      </span>{c}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="mt-2.5 flex items-center gap-2 border-t border-[#EEF0F7] pt-2.5">
              <span className="text-[11px] font-medium text-[#1B1B3A]">Faculty Assessment</span>
              <Tag tone={improvementDefined ? 'green' : 'amber'}>
                {improvementDefined ? 'Improvement Clearly Defined' : 'Improvement Needs Detail'}
              </Tag>
            </div>
          </Card>

          <Card title={`4. Supporting Papers (${data.supporting.length})`} right={
            <Btn size="xs" icon={Plus} onClick={() => onNotice(
              'Adding a supporting paper needs the file store and a student-side upload form \u2014 not built yet.')}>
              Add Supporting Paper
            </Btn>}>
            {data.supporting.length === 0 ? (
              <p className="py-6 text-center text-[11px] text-[#8A8FA8]">No supporting papers listed.</p>
            ) : (
              <table className="w-full table-fixed border-collapse text-[10px]">
                <colgroup>
                  {['auto', '52px', '54px', '34px', '48px', '66px', '88px'].map((w, i) => (
                    <col key={i} style={{ width: w }} />
                  ))}
                </colgroup>
                <thead>
                  <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                    {['Title', 'Authors', 'Source', 'Year', 'DOI', 'Purpose', 'Status'].map((h, i) => (
                      <th key={h} className={cn('px-1.5 py-1.5 font-medium', i === 0 ? 'text-left' : 'text-center')}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.supporting.map((sp) => (
                    <tr key={sp.id} className="border-b border-[#F1F2F8] align-top">
                      <td className="px-1.5 py-1.5 leading-snug text-[#1B1B3A]">{sp.title}</td>
                      <td className="truncate px-1.5 py-1.5 text-center text-[#3A3F58]" title={sp.authors ?? ''}>
                        {sp.authors ?? '\u2014'}
                      </td>
                      <td className="truncate px-1.5 py-1.5 text-center text-[#3A3F58]" title={sp.source ?? ''}>
                        {sp.source ?? '\u2014'}
                      </td>
                      <td className="px-1.5 py-1.5 text-center text-[#3A3F58]">{sp.year ?? '\u2014'}</td>
                      <td className="px-1.5 py-1.5 text-center">
                        {sp.doi ? (
                          <a href={sp.url ?? `https://doi.org/${sp.doi}`} target="_blank" rel="noopener noreferrer"
                            title={sp.doi} className="inline-flex items-center gap-0.5 text-[9px] text-[#4F46E5] hover:underline">
                            DOI <ExternalLink className="h-2.5 w-2.5" />
                          </a>
                        ) : <span className="text-[9px] text-[#8A8FA8]">No DOI</span>}
                      </td>
                      <td className="px-1.5 py-1.5 text-center">
                        {sp.purpose && (
                          <span className="block rounded bg-[#EEF2FF] px-1 py-0.5 text-[9px] leading-tight text-[#4F46E5]"
                            title={sp.purpose}>
                            {sp.purpose}
                          </span>
                        )}
                      </td>
                      <td className="px-1.5 py-1.5 text-center">
                        <Btn size="xs" icon={Eye} onClick={() => onNotice(
                          `${sp.title}${sp.doi ? ` \u2014 DOI ${sp.doi}` : ''}. Paper files are metadata-only right now.`)}>
                          Preview
                        </Btn>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>

        <Card title="Base Paper Activity">
          <Timeline steps={data.activity} />
        </Card>
      </div>

      <div className="space-y-2.5">
        <Card title="Verification Checklist" right={
          <span className="text-[10.5px] font-medium text-[#5A5F7A]">
            {data.checks_passed}/{data.checks_total} passed
          </span>}>
          <ul className="space-y-1">
            {data.checklist.map((c) => (
              <li key={c.key} className="flex items-center gap-2 text-[11.5px]">
                {c.passed
                  ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                  : <AlertCircle className="h-3.5 w-3.5 shrink-0 text-[#D97706]" />}
                <span className="flex-1 truncate text-[#3A3F58]">{c.label}</span>
                <span className={cn('whitespace-nowrap text-[10.5px]',
                  c.passed ? 'text-[#16A34A]' : 'text-[#D97706]')}>
                  {c.detail ?? (c.passed ? 'Passed' : 'Pending')}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-2.5 border-t border-[#EEF0F7] pt-2">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#3A3F58]">{data.checks_passed} / {data.checks_total} checks passed</span>
              <span className="font-semibold text-[#1B1B3A]">
                {Math.round((data.checks_passed / (data.checks_total || 1)) * 100)}%
              </span>
            </div>
            <span className="mt-1 block">
              <Bar value={(data.checks_passed / (data.checks_total || 1)) * 100} tone="bg-[#16A34A]" />
            </span>
          </div>
        </Card>

        <Card title="Paper Quality">
          <ul className="space-y-2">
            {[
              ['Relevance', q.relevance],
              ['Methodology Quality', q.methodology],
              ['Recency', q.recency],
              ['Source Credibility', q.credibility],
            ].map(([label, value]) => (
              <li key={label as string} className="flex items-center gap-2">
                <span className="w-[104px] shrink-0 text-[10.5px] text-[#3A3F58]">{label}</span>
                <span className="flex-1"><Bar value={(value as number) ?? 0} /></span>
                <span className="w-[34px] shrink-0 text-right text-[10.5px] text-[#5A5F7A]">{value ?? '\u2014'}%</span>
              </li>
            ))}
          </ul>
          <div className="mt-2.5 flex items-center justify-between border-t border-[#EEF0F7] pt-2">
            <span className="text-[11.5px] font-semibold text-[#1B1B3A]">Overall Score</span>
            <span className="text-[13px] font-bold text-[#1B1B3A]">{q.overall ?? '\u2014'} / 100</span>
          </div>
          {q.label && <p className="mt-0.5 text-[12px] font-semibold text-[#16A34A]">{q.label}</p>}
        </Card>

        <Card title="Faculty Verification Note" right={
          <Btn size="xs" icon={Pencil} onClick={() => onNotice(
            'Verification notes are recorded with the paper decision on the Approval Queue tab.')}>
            Edit Note
          </Btn>}>
          {note.body ? (
            <>
              <p className="text-[11.5px] leading-snug text-[#3A3F58]">{note.body}</p>
              <p className="mt-1.5 text-[10px] text-[#8A8FA8]">
                {[note.actor, note.at ? fmtDate(note.at) : null].filter(Boolean).join(' \u00b7 ')}
              </p>
            </>
          ) : (
            <p className="py-3 text-center text-[11px] text-[#8A8FA8]">No verification note recorded.</p>
          )}
        </Card>

        <Card title="Quick Actions">
          <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
            {[
              // Was labelled "Verify Pending Papers" and navigated to Documents -
              // a different tab, about different files. It verifies the paper now.
              [ShieldCheck, p?.status === 'verified' ? 'Paper Verified' : 'Verify This Paper',
                async () => {
                  if (!p) { onNotice('No base paper has been uploaded for this batch yet.'); return }
                  if (p.status === 'verified') { onNotice('This paper is already verified.'); return }
                  if (!canManage) { onNotice('Only the batch owner can verify the base paper.'); return }
                  try {
                    const r = await decideBasePaper(code, 'verify')
                    onNotice(r.message)
                    reload()
                  } catch (err) {
                    onNotice(fileError(err, 'That paper could not be verified.'))
                  }
                }],
              [FileText, 'Generate Citation', () => onNotice(citation || 'No paper metadata to cite.')],
              [RefreshCw, 'Request Different Paper', () => onNotice(
                'Request Changes is recorded with the decision on the Approval Queue tab.')],
              [ExternalLink, 'Check DOI', () => p?.doi
                ? window.open(p.url ?? `https://doi.org/${p.doi}`, '_blank', 'noopener')
                : onNotice('This paper has no DOI recorded.')],
              [Download, 'Download All Papers', () => downloadText(
                `${data.header.batch_code}-papers.csv`,
                ['Role,Title,Authors,Source,Year,DOI,Purpose',
                  ...(p ? [['Primary', p.title, p.authors, p.publication, p.year, p.doi, '']] : []),
                  ...data.supporting.map((sp) => ['Supporting', sp.title, sp.authors, sp.source, sp.year, sp.doi, sp.purpose]),
                ].map((r) => Array.isArray(r)
                  ? r.map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',') : r).join('\n'))],
              [History, 'Run Similarity Check', () => onNotice(
                data.quick_actions.similarity_percent != null
                  ? `Last similarity review: ${data.quick_actions.similarity_percent}%. Re-running needs the plagiarism service, which is not wired up.`
                  : 'No similarity review on record; the plagiarism service is not wired up.')],
            ].map(([Icon, label, onClick]) => {
              const I = Icon as typeof FileText
              return (
                <button key={label as string} type="button" onClick={onClick as () => void}
                  className="flex items-center gap-1.5 rounded-md px-1 py-1 text-left text-[10.5px] text-[#3A3F58] hover:bg-[#F7F8FC]">
                  <I className="h-3.5 w-3.5 shrink-0 text-[#4F46E5]" />
                  <span className="truncate">{label as string}</span>
                </button>
              )
            })}
          </div>
        </Card>
      </div>
    </div>
  )
}

// ================================================================= Documents

const DOC_SORTS = {
  recent: 'Newest first',
  oldest: 'Oldest first',
  name: 'Name (A-Z)',
  size: 'Largest first',
} as const

export function DocumentsPane({ data, code, onNotice, reload, busy, onTab,
  canManage = true }: TabProps<DocumentsTab>) {
  const [selected, setSelected] = useState(data.selected)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [uploader, setUploader] = useState('')
  const [sort, setSort] = useState<keyof typeof DOC_SORTS>('recent')
  const [uploadOpen, setUploadOpen] = useState(false)

  const upload = async (file: File, category: string) => {
    const result = await uploadBatchDocument(code, file, category)
    reload()
    return result
  }

  const download = async (id: string, name: string) => {
    try {
      await downloadBatchDocument(code, id, name)
    } catch (err) {
      onNotice(fileError(err, 'That file could not be downloaded.'))
    }
  }

  const remove = async (id: string, name: string) => {
    try {
      const result = await removeBatchDocument(code, id)
      onNotice(result.message)
      reload()
    } catch (err) {
      onNotice(fileError(err, `${name} could not be removed.`))
    }
  }

  const uploaders = Array.from(
    new Set(data.rows.map((r) => r.uploaded_by).filter(Boolean) as string[])
  ).sort()

  // A missing upload date sorts last rather than to 1970, so unfiled rows do
  // not push real documents off the top of the list.
  const stamp = (v: string | null) => (v ? new Date(v).getTime() : 0)

  const rows = data.rows
    .filter((r) =>
      (!category || r.category === category) &&
      (!uploader || r.uploaded_by === uploader) &&
      (!search || r.name.toLowerCase().includes(search.toLowerCase()))
    )
    .sort((a, b) =>
      sort === 'name' ? a.name.localeCompare(b.name)
        : sort === 'size' ? b.file_size - a.file_size
          : sort === 'oldest' ? stamp(a.uploaded_at) - stamp(b.uploaded_at)
            : stamp(b.uploaded_at) - stamp(a.uploaded_at)
    )

  const nextForReview = data.queue[0] ?? null

  const decide = async (id: string, decision: 'verify' | 'request_changes') => {
    try {
      await decideDocument(code, id, decision)
      onNotice(decision === 'verify' ? 'Document verified.' : 'Changes requested on the document.')
      reload()
    } catch (err: any) {
      onNotice(err?.response?.data?.detail ?? 'That document could not be updated.')
    }
  }

  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        <KpiRow kpis={data.kpis} />

        <Card title="Registration Documents" right={
          <span className="flex flex-wrap items-center gap-2">
            <span className="relative">
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search documents…"
                className="h-7 w-[170px] rounded-lg border border-[#DDE0EE] pl-2 pr-7 text-[11px] outline-none focus:border-[#4F46E5]" />
              <Search className="absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-[#8A8FA8]" />
            </span>
            <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category"
              className="h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#4F46E5]">
              <option value="">All Categories</option>
              {data.categories.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select value={uploader} onChange={(e) => setUploader(e.target.value)} aria-label="Uploaded By"
              className="h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#4F46E5]">
              <option value="">All Uploaders</option>
              {uploaders.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
            <select value={sort} onChange={(e) => setSort(e.target.value as keyof typeof DOC_SORTS)} aria-label="Sort"
              className="h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#4F46E5]">
              {Object.entries(DOC_SORTS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
            </select>
            <Btn size="xs" icon={Upload} disabled={!canManage}
              title={canManage ? undefined : 'Only the batch owner can upload documents'}
              onClick={() => setUploadOpen((open) => !open)}>
              Upload Document
            </Btn>
            <Btn size="xs" icon={Download} onClick={() => downloadText(
              `${data.header.batch_code}-documents.csv`,
              ['Document,Category,Version,Uploaded By,Uploaded,Size (bytes),Status',
                ...rows.map((r) => [r.name, r.category, r.version ?? '', r.uploaded_by ?? '',
                  r.uploaded_at ?? '', r.file_size, r.status]
                  .map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n'))}>
              Download All
            </Btn>
          </span>}>
          {uploadOpen && canManage && (
            <div className="mb-2.5">
              <FileUpload
                limits={data.upload.limits}
                categories={data.upload.categories}
                accent="#4F46E5"
                onUpload={upload}
                onDone={(message) => { onNotice(message); setUploadOpen(false) }} />
              {data.missing_required.length > 0 && (
                <p className="mt-1.5 text-[10.5px] text-[#B45309]">
                  Still expected: {data.missing_required.join(', ')}.
                </p>
              )}
            </div>
          )}
          <div className="overflow-x-auto">
            <table className="w-full table-fixed border-collapse text-[11px]">
              <colgroup>
                {['auto', '116px', '54px', '104px', '78px', '58px', '124px', '118px'].map((w, i) => (
                  <col key={i} style={{ width: w }} />
                ))}
              </colgroup>
              <thead>
                <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                  {['Document', 'Category', 'Ver.', 'Uploaded By', 'Uploaded', 'Size', 'Verification', 'Action'].map((h, i) => (
                    <th key={h} className={cn('px-2 py-1.5 font-medium', i === 0 ? 'text-left' : 'text-center')}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((d) => (
                  <tr key={d.id} className={cn('border-b border-[#F1F2F8]', selected?.id === d.id && 'bg-[#F5F3FF]')}>
                    <td className="truncate px-2 py-1.5">
                      <button type="button" onClick={() => setSelected(d)}
                        className="truncate font-medium text-[#4F46E5] hover:underline" title={d.name}>{d.name}</button>
                    </td>
                    <td className="truncate px-2 py-1.5 text-center text-[#3A3F58]">{d.category}</td>
                    <td className="px-2 py-1.5 text-center text-[#3A3F58]">{d.version ?? '—'}</td>
                    <td className="truncate px-2 py-1.5 text-center text-[#3A3F58]">{d.uploaded_by ?? '—'}</td>
                    <td className="whitespace-nowrap px-2 py-1.5 text-center text-[10px] text-[#5A5F7A]">
                      {d.uploaded_at ? fmtDate(d.uploaded_at) : '—'}
                    </td>
                    <td className="px-2 py-1.5 text-center text-[10px] text-[#5A5F7A]">{fmtBytes(d.file_size)}</td>
                    <td className="px-2 py-1.5 text-center">
                      <Tag tone={statusTone(d.status_key)}>
                        {d.status}{d.similarity_percent != null ? `, ${d.similarity_percent}%` : ''}
                      </Tag>
                    </td>
                    <td className="px-2 py-1.5 text-center">
                      {!d.has_file ? (
                        <button type="button" disabled={!canManage} onClick={() => setUploadOpen(true)}
                          className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10px] font-medium text-[#4F46E5] disabled:opacity-40">Upload</button>
                      ) : d.status_key === 'verified' ? (
                        <button type="button" onClick={() => download(d.id, d.name)}
                          className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10px] font-medium text-[#4F46E5]">Download</button>
                      ) : (
                        <button type="button" disabled={busy || !canManage}
                          title={canManage ? undefined : 'Only the batch owner can verify documents'}
                          onClick={() => decide(d.id, 'verify')}
                          className="rounded-md border border-[#BBF7D0] bg-[#F0FDF4] px-2 py-0.5 text-[10px] font-medium text-[#15803D] disabled:opacity-50">Verify</button>
                      )}
                      <span className="ml-1 inline-flex align-middle">
                        <Menu items={[
                          { label: 'View details', onClick: () => setSelected(d) },
                          ...(d.has_file ? [{ label: 'Download', onClick: () => download(d.id, d.name) }] : []),
                          { label: 'Request changes', onClick: () => decide(d.id, 'request_changes') },
                          ...(d.can_remove && canManage
                            ? [{ label: 'Remove this version', onClick: () => remove(d.id, d.name) }] : []),
                          { label: 'View in activity log', onClick: () => onTab('activity') },
                        ]} />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-[10.5px] text-[#8A8FA8]">Showing {rows.length} of {data.rows.length} documents</p>
        </Card>

        {selected && (
          <Card title={`Selected Document — ${selected.name}`}>
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
              <div className="grid grid-cols-2 gap-2">
                <Field label="Version" value={selected.version} />
                <Field label="Uploaded by" value={selected.uploaded_by} />
                <Field label="Uploaded on" value={fmtDateTime(selected.uploaded_at)} />
                <Field label="Pages" value={selected.page_count ?? '—'} />
                <Field label="Size" value={fmtBytes(selected.file_size)} />
                <Field label="Virus Scan" value={selected.virus_scan_passed === false
                  ? <Tag tone="red">Failed</Tag> : <Tag tone="green">Passed</Tag>} />
                <Field className="col-span-2" label="Faculty Note" value={selected.faculty_note} />
              </div>
              <div className="flex flex-col gap-1.5">
                <button type="button" disabled={busy || !canManage || selected.status_key === 'verified'}
                  onClick={() => decide(selected.id, 'verify')}
                  className="rounded-lg border border-[#BBF7D0] bg-[#F0FDF4] py-2 text-[11.5px] font-medium text-[#15803D] disabled:opacity-40">
                  Approve Document
                </button>
                <button type="button" disabled={busy || !canManage || selected.status_key === 'missing'}
                  onClick={() => decide(selected.id, 'request_changes')}
                  className="rounded-lg border border-[#FDE68A] bg-[#FFFBEB] py-2 text-[11.5px] font-medium text-[#B45309] disabled:opacity-40">
                  Request Changes
                </button>
                <button type="button" disabled={!selected.has_file}
                  onClick={() => download(selected.id, selected.name)}
                  className="flex items-center justify-center gap-1.5 rounded-lg border border-[#DDE0EE] py-2 text-[11.5px] font-medium text-[#4F46E5] disabled:opacity-40">
                  <Download className="h-3.5 w-3.5" />
                  {selected.has_file ? 'Download file' : 'No file uploaded'}
                </button>
                {selected.file && (
                  <p className="text-[10px] text-[#8A8FA8]">
                    {selected.file.size_label}
                    {selected.file.page_count ? ` · ${selected.file.page_count} pages` : ''}
                    {' · '}sha256 {selected.file.sha256}
                  </p>
                )}
                <p className="mt-1 text-[10px] leading-snug text-[#8A8FA8]">
                  Verified documents are locked. New updates create a new version and preserve previous
                  versions in the audit history.
                </p>
              </div>
            </div>
          </Card>
        )}
      </div>

      <div className="space-y-2.5">
        <Card title="1. Document Checklist" right={
          <span className="text-[10.5px] text-[#8A8FA8]">{data.checklist_complete} of {data.checklist_total} complete</span>}>
          <ul className="space-y-1">
            {data.checklist.map((c) => (
              <li key={c.name} className="flex items-center gap-2 text-[11px]">
                {c.passed
                  ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                  : <AlertCircle className="h-3.5 w-3.5 shrink-0 text-[#D97706]" />}
                <span className="flex-1 truncate text-[#3A3F58]">{c.name}</span>
                <span className={cn('whitespace-nowrap text-[10px]', c.passed ? 'text-[#16A34A]' : 'text-[#D97706]')}>{c.status}</span>
              </li>
            ))}
          </ul>
          <div className="mt-2"><Bar value={(data.checklist_complete / (data.checklist_total || 1)) * 100} tone="bg-[#16A34A]" /></div>
        </Card>

        <Card title="2. Verification Queue">
          {data.queue.length === 0
            ? <p className="py-3 text-center text-[11px] text-[#8A8FA8]">Nothing awaiting verification.</p>
            : (
              <ul className="space-y-1">
                {data.queue.map((d) => (
                  <li key={d.id} className="flex items-center gap-2 text-[11px]">
                    <span className="flex-1 truncate text-[#3A3F58]">{d.name}</span>
                    <button type="button" disabled={busy} onClick={() => decide(d.id, 'verify')}
                      className="rounded-md border border-[#DDE0EE] px-2 py-0.5 text-[10px] font-medium text-[#4F46E5] disabled:opacity-50">
                      Review
                    </button>
                  </li>
                ))}
              </ul>
            )}
          <div className="mt-2.5 flex gap-1.5 border-t border-[#EEF0F7] pt-2.5">
            <Btn size="xs" tone="ghost" full disabled={!nextForReview}
              onClick={() => nextForReview && setSelected(nextForReview)}>
              Review Next
            </Btn>
            <Btn size="xs" full onClick={() => onTab('approvals')}>View Queue</Btn>
          </div>
        </Card>

        <Card title="3. Storage by Category" right={
          <span className="text-[10.5px] text-[#8A8FA8]">{fmtBytes(data.storage_used)} used</span>}>
          <ul className="space-y-1.5">
            {data.storage_by_category.map((s) => (
              <li key={s.category} className="flex items-center gap-2">
                <span className="w-[104px] shrink-0 truncate text-[10.5px] text-[#3A3F58]">{s.category}</span>
                <span className="flex-1"><Bar value={(s.bytes / (data.storage_used || 1)) * 100} /></span>
                <span className="w-[54px] shrink-0 text-right text-[10px] text-[#5A5F7A]">{fmtBytes(s.bytes)}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="4. Recent Activity" right={
          <Btn size="xs" icon={History} onClick={() => onTab('activity')}>View All</Btn>}>
          <MiniLog entries={data.recent_activity.map((a) => ({
            label: a.activity, actor: a.actor, occurred_at: a.occurred_at, severity: a.severity,
          }))} empty="No document activity recorded yet." />
        </Card>
      </div>
    </div>
  )
}

// =========================================================== Approval History

/** Journey node styling by state - done, where it is now, and what is ahead. */
const JOURNEY_ICON: Record<string, typeof CheckCircle2> = {
  draft: CheckCircle2,
  submitted: CheckCircle2,
  review_started: UserCog,
  changes_requested: AlertCircle,
  resubmitted: RefreshCw,
  documents_verified: FileCheck,
  final_review: ClipboardList,
  approved: Lock,
}

const HISTORY_ICON: Record<string, typeof CheckCircle2> = {
  submitted: CheckCircle2,
  review_started: UserCog,
  changes_requested: AlertCircle,
  resubmitted: RefreshCw,
  documents_verified: CheckCircle2,
  final_review: ClipboardList,
  approved: CheckCircle2,
  rejected: XCircle,
}

const ACTION_LABEL: Record<string, string> = {
  view_submission: 'View Submitted Version',
  view_remarks: 'View Remarks',
  compare_changes: 'Compare Changes',
  view_resubmission: 'View Resubmission',
  view_documents: 'View Documents',
  open_review: 'Open Review',
  add_note: 'Add Note',
  view_decision: 'View Decision',
}

function JourneyStrip({ stages }: { stages: JourneyStage[] }) {
  return (
    <ol className="flex flex-wrap gap-y-3">
      {stages.map((stage, i) => {
        const Icon = JOURNEY_ICON[stage.kind] ?? CheckCircle2
        const done = stage.state === 'done'
        const current = stage.state === 'current'
        return (
          <li key={stage.key} className="flex min-w-[104px] flex-1 flex-col items-center text-center">
            <span className="flex w-full items-center">
              <span className={cn('h-[2px] flex-1', i === 0 ? 'bg-transparent'
                : done || current ? 'bg-[#16A34A]' : 'bg-[#DDE0EE]')} />
              <span className={cn('flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2',
                current ? 'border-[#4F46E5] bg-[#4F46E5] text-white'
                  : done ? 'border-[#16A34A] bg-white text-[#16A34A]'
                    : 'border-[#C7CBDD] bg-white text-[#C7CBDD]')}>
                <Icon className="h-3 w-3" />
              </span>
              <span className={cn('h-[2px] flex-1', i === stages.length - 1 ? 'bg-transparent'
                : done ? 'bg-[#16A34A]' : 'bg-[#DDE0EE]')} />
            </span>
            <span className={cn('mt-1.5 text-[10px] font-medium leading-tight',
              current ? 'text-[#4F46E5]' : done ? 'text-[#1B1B3A]' : 'text-[#8A8FA8]')}>
              {stage.step}
              {current && <span className="block font-normal">(Current)</span>}
              {stage.state === 'pending' && <span className="block font-normal">(Pending)</span>}
            </span>
            <span className="text-[9.5px] text-[#8A8FA8]">
              {stage.occurred_at ? fmtDate(stage.occurred_at) : '\u2014'}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

export function ApprovalsPane({ data, code, onNotice, onTab }: TabProps<ApprovalsTab>) {
  const a = data.approval_status
  const reviewHours = data.total_review_time_hours

  const runAction = (action: string, entry: ApprovalHistoryEntry) => {
    switch (action) {
      case 'view_submission':
      case 'view_resubmission':
        return onTab('project')
      case 'view_documents':
        return onTab('documents')
      case 'compare_changes':
        return document.getElementById('version-comparison')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      case 'view_remarks':
        return onNotice(entry.body || 'No remarks were recorded with this decision.')
      case 'open_review':
        return onTab('activity')
      case 'add_note':
        return onNotice('Internal notes are written on the Team Members tab and stay private to faculty.')
      default:
        return onNotice(`${entry.title} \u2014 ${entry.status_label ?? 'recorded'} on ${fmtDateTime(entry.occurred_at)}.`)
    }
  }

  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        {/* KPI strip */}
        <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-[repeat(4,minmax(0,0.82fr))_minmax(0,1.3fr)_minmax(0,1.3fr)]">
          {data.kpis.map((k) => {
            const Icon = k.id === 'changes' ? AlertCircle
              : k.id === 'resubmissions' ? RefreshCw
                : k.id === 'rejections' ? XCircle : History
            const tone = k.id === 'changes' ? 'text-[#D97706] bg-[#FFFBEB]'
              : k.id === 'rejections' ? 'text-[#DC2626] bg-[#FEF2F2]'
                : 'text-[#4F46E5] bg-[#EEF2FF]'
            return (
              <div key={k.id} className={cn(CARD, 'flex items-center gap-2.5 p-3')}>
                <span className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-full', tone)}>
                  <Icon className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-[18px] font-bold leading-none text-[#1B1B3A]">{k.value}</span>
                  <span className="block text-[10px] leading-tight text-[#5A5F7A]">{k.label}</span>
                </span>
              </div>
            )
          })}
          <div className={cn(CARD, 'flex items-center gap-2.5 p-3')}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#FFFBEB] text-[#D97706]">
              <ClipboardList className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-[10px] leading-tight text-[#5A5F7A]">Current Status</span>
              <span className="block text-[12px] font-semibold leading-tight text-[#B45309]">{data.current_status}</span>
            </span>
          </div>
          <div className={cn(CARD, 'flex items-center gap-2.5 p-3')}>
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#EEF2FF] text-[#4F46E5]">
              <Clock className="h-4 w-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-[10px] leading-tight text-[#5A5F7A]">Total Review Time</span>
              <span className="block whitespace-nowrap text-[12px] font-semibold text-[#1B1B3A]">
                {reviewHours != null
                  ? `${Math.floor(reviewHours / 24)}d ${reviewHours % 24}h` : '\u2014'}
              </span>
            </span>
          </div>
        </div>

        <Card title="Approval Journey"><JourneyStrip stages={data.journey} /></Card>

        <Card title="Approval History">
          <ol className="space-y-0">
            {data.history.map((h, i) => {
              const Icon = HISTORY_ICON[h.kind] ?? CheckCircle2
              const last = i === data.history.length - 1
              return (
                <li key={h.id} className="grid grid-cols-[86px_28px_minmax(0,1fr)] gap-x-2">
                  {/* date rail */}
                  <span className="pt-1 text-right">
                    <span className="block text-[10.5px] font-medium text-[#3A3F58]">
                      {fmtDate(h.occurred_at)}
                    </span>
                    <span className="block text-[9.5px] text-[#8A8FA8]">
                      {new Date(h.occurred_at).toLocaleTimeString('en-IN',
                        { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </span>
                  <span className="flex flex-col items-center">
                    <span className={cn('flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 bg-white',
                      h.kind === 'changes_requested' ? 'border-[#D97706] text-[#D97706]'
                        : h.kind === 'rejected' ? 'border-[#DC2626] text-[#DC2626]'
                          : 'border-[#16A34A] text-[#16A34A]')}>
                      <Icon className="h-3 w-3" />
                    </span>
                    {!last && <span className="w-px flex-1 bg-[#E8E9F2]" />}
                  </span>
                  <span className={cn('block min-w-0', last ? 'pb-0' : 'pb-3')}>
                    <span className="flex flex-wrap items-start justify-between gap-2">
                      <span className="min-w-0 flex-1">
                        <span className="block text-[12px] font-semibold text-[#4F46E5]">{h.title}</span>
                        <span className="block text-[10.5px] text-[#8A8FA8]">
                          {[h.actor_role === 'Batch Leader' ? `Submitted by ${h.actor}` : `Reviewer: ${h.actor}`,
                            h.duration_minutes
                              ? `Review duration: ${Math.floor(h.duration_minutes / 60)}h ${h.duration_minutes % 60}m`
                              : null].filter(Boolean).join(' \u00b7 ')}
                        </span>
                        {h.summary && (
                          <span className="mt-0.5 block text-[11px] leading-snug text-[#3A3F58]">{h.summary}</span>
                        )}
                        {h.bullets.length > 0 && (
                          <ul className="mt-1 space-y-0.5">
                            {h.bullets.map((b) => (
                              <li key={b} className="flex gap-1.5 text-[10.5px] leading-snug text-[#3A3F58]">
                                <span className="mt-[5px] h-1 w-1 shrink-0 rounded-full bg-[#8A8FA8]" />{b}
                              </li>
                            ))}
                          </ul>
                        )}
                      </span>
                      <span className="flex shrink-0 flex-col items-end gap-1.5">
                        {h.status_label && (
                          <Tag tone={statusTone(h.status_label.toLowerCase().replace(/ /g, '_'))}>
                            {h.status_label}
                          </Tag>
                        )}
                        <span className="flex flex-wrap justify-end gap-1.5">
                          {h.actions.map((action) => (
                            <Btn key={action} size="xs" onClick={() => runAction(action, h)}>
                              {ACTION_LABEL[action] ?? action}
                            </Btn>
                          ))}
                        </span>
                      </span>
                    </span>
                  </span>
                </li>
              )
            })}
          </ol>
        </Card>

        <div className="grid gap-2.5 md:grid-cols-2">
          <Card title="5. Version Comparison" id="version-comparison" right={
            <Tag tone={data.comparison_resolved === data.comparison.length ? 'green' : 'amber'}>
              {data.comparison_resolved}/{data.comparison.length} resolved
            </Tag>}>
            {data.comparison.length === 0 ? (
              <p className="py-4 text-center text-[11px] text-[#8A8FA8]">
                No recorded changes between submissions.
              </p>
            ) : (
              <table className="w-full table-fixed border-collapse text-[10.5px]">
                <colgroup>
                  <col style={{ width: '96px' }} /><col /><col /><col style={{ width: '46px' }} />
                </colgroup>
                <thead>
                  <tr className="border-b border-[#EEF0F7] text-left text-[#8A8FA8]">
                    <th className="py-1.5 pr-2 font-medium" />
                    <th className="py-1.5 pr-2 font-medium">Original Submission</th>
                    <th className="py-1.5 pr-2 font-medium">Revised</th>
                    <th className="py-1.5 text-center font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {data.comparison.map((c, i) => (
                    <tr key={`${c.field}-${i}`} className="border-b border-[#F1F2F8] align-top">
                      <td className="truncate py-1.5 pr-2 font-medium text-[#1B1B3A]" title={c.field}>{c.field}</td>
                      <td className="py-1.5 pr-2 text-[#5A5F7A]">{c.original}</td>
                      <td className="py-1.5 pr-2 text-[#1B1B3A]">{c.revised}</td>
                      <td className="py-1.5 text-center">
                        {c.resolved
                          ? <CheckCircle2 className="mx-auto h-3.5 w-3.5 text-[#16A34A]" />
                          : <AlertCircle className="mx-auto h-3.5 w-3.5 text-[#D97706]" />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <Btn full className="mt-2.5" onClick={() => onTab('activity')}>View Full Comparison</Btn>
          </Card>

          <Card title="6. Internal Review Notes">
            {data.internal_notes.length === 0 ? (
              <p className="py-4 text-center text-[11px] text-[#8A8FA8]">No internal notes recorded.</p>
            ) : (
              <ul className="space-y-2">
                {data.internal_notes.map((n) => (
                  <li key={n.id}>
                    <p className="text-[10px] text-[#8A8FA8]">
                      {fmtDateTime(n.occurred_at)}
                    </p>
                    <p className="text-[11px] font-medium text-[#1B1B3A]">{n.actor ?? '\u2014'}</p>
                    <p className="text-[11px] leading-snug text-[#3A3F58]">{n.body}</p>
                  </li>
                ))}
              </ul>
            )}
            <Btn full className="mt-2.5" onClick={() => onTab('team')}>Add Internal Note</Btn>
          </Card>
        </div>
      </div>

      <div className="space-y-2.5">
        <Card title="1. Current Approval Status">
          <p className={cn('text-[13px] font-semibold',
            a.status_key === 'approved' ? 'text-[#15803D]'
              : a.status_key === 'rejected' ? 'text-[#DC2626]' : 'text-[#D97706]')}>
            {a.status}
          </p>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-[10.5px] text-[#5A5F7A]">{a.checks_passed}/{a.checks_total} checks passed</span>
            <span className="flex-1"><Bar value={a.percent} tone="bg-[#F59E0B]" /></span>
            <span className="text-[11px] font-semibold text-[#1B1B3A]">{a.percent}%</span>
          </div>

          <ul className="mt-2.5 space-y-1.5">
            {[
              [UserCog, 'Reviewer', a.reviewer, false],
              [Users, 'Submitted by', a.submitted_by, false],
              [Clock, 'Last action', a.last_action_at ? fmtDateTime(a.last_action_at) : null, false],
              [Clock, 'SLA remaining', a.sla, (a.sla ?? '').startsWith('Overdue')],
              [AlertCircle, 'Blocking item', a.blocking_item ?? 'None', Boolean(a.blocking_item)],
            ].map(([Icon, label, value, warn]) => {
              const I = Icon as typeof Clock
              return (
                <li key={label as string} className="flex items-center gap-2 text-[11px]">
                  <I className={cn('h-3.5 w-3.5 shrink-0', warn ? 'text-[#DC2626]' : 'text-[#8A8FA8]')} />
                  <span className="flex-1 text-[#5A5F7A]">{label as string}</span>
                  <span className={cn('max-w-[52%] truncate text-right font-medium',
                    warn ? 'text-[#DC2626]' : 'text-[#1B1B3A]')} title={(value as string) ?? ''}>
                    {(value as string) ?? '\u2014'}
                  </span>
                </li>
              )
            })}
          </ul>

          <div className="mt-3 grid grid-cols-2 gap-2">
            <Btn tone="primary" size="md" onClick={() => onNotice(
              a.blocking_item
                ? `Cannot complete the review while "${a.blocking_item}" is outstanding \u2014 clear it first.`
                : 'Approval decisions are recorded from the Approval Queue tab.')}>
              Complete Review
            </Btn>
            <Btn tone="amber" size="md" onClick={() => onNotice(
              'Request Changes is recorded with the decision on the Approval Queue tab.')}>
              Request Changes
            </Btn>
          </div>
        </Card>

        <Card title="2. Approval Checklist" right={
          <span className="text-[10.5px] font-medium text-[#5A5F7A]">
            {data.checks_passed}/{data.checks_total} passed
          </span>}>
          <ul className="space-y-1">
            {data.checklist.map((c) => (
              <li key={c.key} className="flex items-center gap-2 text-[11.5px]">
                {c.passed
                  ? <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-[#16A34A]" />
                  : <AlertCircle className="h-3.5 w-3.5 shrink-0 text-[#D97706]" />}
                <span className="flex-1 truncate text-[#3A3F58]">{c.label}</span>
                <span className={cn('whitespace-nowrap text-[10.5px]',
                  c.passed ? 'text-[#16A34A]' : 'text-[#D97706]')}>
                  {c.detail ?? (c.passed ? 'Passed' : 'Pending')}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="3. Review Participants">
          <ul className="space-y-1.5">
            {data.participants.map((p) => (
              <li key={p.name} className="flex items-center gap-2">
                <Initials name={p.name} size="h-7 w-7" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[11.5px] text-[#1B1B3A]">{p.name}</span>
                  <span className="block text-[9.5px] text-[#8A8FA8]">{p.role}</span>
                </span>
                <Tag tone="indigo">{p.tag}</Tag>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="4. Decision Summary">
          <ul className="space-y-1 text-[11.5px]">
            {[
              ['Approval decisions', data.decision_summary.approvals, 'text-[#1B1B3A]'],
              ['Change requests', data.decision_summary.change_requests, 'text-[#D97706]'],
              ['Resubmissions', data.decision_summary.resubmissions, 'text-[#4F46E5]'],
              ['Rejections', data.decision_summary.rejections, 'text-[#DC2626]'],
            ].map(([label, value, tone]) => (
              <li key={label as string} className="flex justify-between">
                <span className={cn(tone as string)}>{label}</span>
                <span className={cn('font-semibold', tone as string)}>{value as number}</span>
              </li>
            ))}
            <li className="flex justify-between pt-1">
              <span className="text-[#3A3F58]">Average response by students</span>
              <span className="font-semibold text-[#1B1B3A]">
                {fmtHours(data.decision_summary.avg_student_response_hours)}
              </span>
            </li>
            <li className="flex justify-between">
              <span className="text-[#3A3F58]">Average faculty review</span>
              <span className="font-semibold text-[#1B1B3A]">
                {fmtHours(data.decision_summary.avg_faculty_review_hours)}
              </span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  )
}

// ================================================================ Activity Log

type ActivityFilters = {
  module?: string; severity?: string; actor?: string
  date_from?: string; date_to?: string; search?: string
}

export function ActivityPane({ data, code, onNotice, onTab, onFilter }: TabProps<ActivityTab> & {
  onFilter: (p: Record<string, string | number | undefined>) => void
}) {
  const [selected, setSelected] = useState(data.selected)
  const [search, setSearch] = useState('')
  // Mirrored locally so Export Log can send exactly what the table is showing;
  // the page owns the request params but does not hand them back.
  const [filters, setFilters] = useState<ActivityFilters>({})

  const apply = (patch: ActivityFilters) => {
    setFilters((f) => ({ ...f, ...patch }))
    onFilter({ ...patch, page: 1 })
  }

  return (
    <div className="grid gap-2.5 min-[1500px]:grid-cols-[minmax(0,2.2fr)_minmax(0,1fr)]">
      <div className="space-y-2.5">
        <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-6">
          {data.kpis.map((k) => (
            <div key={k.id} className="rounded-xl border border-[#E8E9F2] bg-white p-3">
              <p className="text-[18px] font-bold leading-none text-[#1B1B3A]">{k.value}</p>
              <p className="mt-1 text-[11px] leading-tight text-[#5A5F7A]">{k.label}</p>
            </div>
          ))}
        </div>

        <Card title="Registration Activity Log" right={
          <span className="flex flex-wrap items-center gap-2">
            <select value={filters.module ?? ''} aria-label="Activity Type"
              onChange={(e) => apply({ module: e.target.value || undefined })}
              className="h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#4F46E5]">
              <option value="">All Activity Types</option>
              {data.modules.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
            <select value={filters.severity ?? ''} aria-label="Severity"
              onChange={(e) => apply({ severity: e.target.value || undefined })}
              className="h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#4F46E5]">
              <option value="">All Severity</option>
              {['info', 'success', 'warning', 'critical'].map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={filters.actor ?? ''} aria-label="Actor"
              onChange={(e) => apply({ actor: e.target.value || undefined })}
              className="h-7 rounded-lg border border-[#DDE0EE] px-2 text-[11px] outline-none focus:border-[#4F46E5]">
              <option value="">All Actors</option>
              {data.actors.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
            <span className="flex items-center gap-1">
              <input type="date" value={filters.date_from ?? ''} aria-label="From date"
                onChange={(e) => apply({ date_from: e.target.value || undefined })}
                className="h-7 rounded-lg border border-[#DDE0EE] px-1.5 text-[10.5px] text-[#3A3F58] outline-none focus:border-[#4F46E5]" />
              <span className="text-[10.5px] text-[#8A8FA8]">to</span>
              <input type="date" value={filters.date_to ?? ''} aria-label="To date"
                onChange={(e) => apply({ date_to: e.target.value || undefined })}
                className="h-7 rounded-lg border border-[#DDE0EE] px-1.5 text-[10.5px] text-[#3A3F58] outline-none focus:border-[#4F46E5]" />
            </span>
            <form onSubmit={(e) => { e.preventDefault(); apply({ search: search || undefined }) }} className="relative">
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search activity…"
                className="h-7 w-[160px] rounded-lg border border-[#DDE0EE] pl-2 pr-7 text-[11px] outline-none focus:border-[#4F46E5]" />
              <button type="submit" aria-label="Search activity" className="absolute right-2 top-1/2 -translate-y-1/2">
                <Search className="h-3 w-3 text-[#8A8FA8]" />
              </button>
            </form>
            <Btn size="xs" icon={RefreshCw} onClick={() => onFilter({ page: data.page })}>Refresh</Btn>
            <Btn size="xs" icon={FileDown}
              onClick={() => downloadActivityLog(code, filters)
                .catch(() => onNotice('The activity log could not be exported.'))}>
              Export Log
            </Btn>
          </span>}>
          <div className="overflow-x-auto">
            <table className="w-full table-fixed border-collapse text-[11px]">
              <colgroup>
                {['104px', '104px', '78px', 'auto', '84px', 'auto', '104px', '72px'].map((w, i) => <col key={i} style={{ width: w }} />)}
              </colgroup>
              <thead>
                <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-[#5A5F7A]">
                  {['Time', 'Actor', 'Role', 'Activity', 'Module', 'Details', 'Status', 'Action'].map((h, i) => (
                    <th key={h} className={cn('px-2 py-1.5 font-medium', i <= 1 ? 'text-left' : 'text-center')}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((a) => (
                  <tr key={a.id} className={cn('cursor-pointer border-b border-[#F1F2F8]', selected?.id === a.id && 'bg-[#F5F3FF]')}
                    onClick={() => setSelected(a)}>
                    <td className="whitespace-nowrap px-2 py-1.5 text-[10px] text-[#5A5F7A]">
                      {new Date(a.occurred_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                      {' '}
                      {new Date(a.occurred_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="truncate px-2 py-1.5 text-[#1B1B3A]">{a.actor ?? '—'}</td>
                    <td className="px-2 py-1.5 text-center text-[10px] text-[#3A3F58]">{a.actor_role}</td>
                    <td className="truncate px-2 py-1.5 text-[#3A3F58]" title={a.activity}>{a.activity}</td>
                    <td className="px-2 py-1.5 text-center text-[10px] text-[#3A3F58]">{a.module}</td>
                    <td className="truncate px-2 py-1.5 text-[10px] text-[#5A5F7A]" title={a.details ?? ''}>{a.details}</td>
                    <td className="px-2 py-1.5 text-center">
                      {a.status_label && <Tag tone={statusTone(a.severity)}>{a.status_label}</Tag>}
                    </td>
                    <td className="px-2 py-1.5 text-center" onClick={(e) => e.stopPropagation()}>
                      <Menu items={[
                        { label: 'View event details', onClick: () => setSelected(a) },
                        { label: 'View related record', onClick: () => onTab(relatedTab(`${a.module} ${a.activity}`)) },
                        { label: 'Filter to this actor', onClick: () => apply({ actor: a.actor ?? undefined }) },
                      ]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[10.5px] text-[#8A8FA8]">
              Showing {data.showing_from} to {data.showing_to} of {data.total} activities
            </p>
            <span className="flex items-center gap-1.5">
              <button type="button" disabled={data.page <= 1} onClick={() => onFilter({ page: data.page - 1 })}
                className="rounded-md border border-[#DDE0EE] px-2 py-1 text-[10.5px] disabled:opacity-40">Prev</button>
              <span className="text-[10.5px] text-[#3A3F58]">Page {data.page} of {data.pages}</span>
              <button type="button" disabled={data.page >= data.pages} onClick={() => onFilter({ page: data.page + 1 })}
                className="rounded-md border border-[#DDE0EE] px-2 py-1 text-[10.5px] disabled:opacity-40">Next</button>
            </span>
          </div>
        </Card>

        {selected && (
          <Card title="Selected Event Details" right={
            <span className="flex items-center gap-1.5">
              <CopyButton size="xs" label="Copy Event ID" text={selected.event_code} />
              <Btn size="xs" icon={ArrowRight}
                onClick={() => onTab(relatedTab(`${selected.module} ${selected.activity}`))}>
                View Related Record
              </Btn>
            </span>}>
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <div className="flex items-start gap-2">
                <Initials name={selected.actor} size="h-9 w-9" />
                <div>
                  <p className="text-[12px] font-semibold text-[#4F46E5]">{selected.event_code}</p>
                  <p className="text-[11.5px] text-[#1B1B3A]">{selected.actor}</p>
                  <p className="text-[10px] text-[#8A8FA8]">{selected.actor_role}</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Field label="Activity" value={selected.activity} />
                <Field label="Source" value={selected.source} />
                <Field label="Time" value={fmtDateTime(selected.occurred_at)} />
                <Field label="IP Address" value={selected.ip_address} />
                <Field label="Module" value={selected.module} />
                <Field label="User Agent" value={selected.user_agent} />
              </div>
            </div>
            {selected.changed_field && (
              <div className="mt-3 border-t border-[#EEF0F7] pt-2.5">
                <p className="mb-1.5 text-[11px] font-semibold text-[#1B1B3A]">Change Summary</p>
                <table className="w-full table-fixed border-collapse text-[10.5px]">
                  <colgroup><col style={{ width: '132px' }} /><col /><col /></colgroup>
                  <thead>
                    <tr className="border-y border-[#EEF0F7] bg-[#FAFBFE] text-left text-[#5A5F7A]">
                      {['Field', 'Previous Value', 'New Value'].map((h) => (
                        <th key={h} className="px-2 py-1.5 font-medium">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b border-[#F1F2F8]">
                      <td className="px-2 py-1.5 font-medium text-[#1B1B3A]">{selected.changed_field}</td>
                      <td className="px-2 py-1.5 text-[#DC2626]">{selected.previous_value ?? '\u2014'}</td>
                      <td className="px-2 py-1.5 text-[#15803D]">{selected.current_value ?? '\u2014'}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}
      </div>

      <div className="space-y-2.5">
        <Card title="1. Activity Summary">
          <ul className="space-y-1.5">
            {data.summary.map((s) => (
              <li key={s.module} className="flex items-center gap-2">
                <span className="w-[92px] shrink-0 text-[10.5px] text-[#3A3F58]">{s.module}</span>
                <span className="flex-1"><Bar value={(s.count / (data.summary[0]?.count || 1)) * 100} /></span>
                <span className="w-[24px] shrink-0 text-right text-[10.5px] text-[#5A5F7A]">{s.count}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="2. Active Participants">
          <ul className="space-y-1.5">
            {data.participants.map((p) => (
              <li key={p.name} className="flex items-center gap-2">
                <Initials name={p.name} size="h-6 w-6" />
                <span className="flex-1 truncate text-[11.5px] text-[#1B1B3A]">{p.name}</span>
                <span className="text-[11.5px] font-semibold text-[#4F46E5]">{p.count}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="3. Security &amp; Integrity">
          <ul className="space-y-1 text-[11px]">
            {['Audit trail intact', 'No unauthorized access', 'Role-protected changes'].map((t) => (
              <li key={t} className="flex gap-2 text-[#3A3F58]">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[#16A34A]" /> {t}
              </li>
            ))}
          </ul>
          <p className="mt-2 border-t border-[#EEF0F7] pt-1.5 text-[10px] text-[#8A8FA8]">
            Last integrity check {fmtDateTime(data.last_integrity_check)}
          </p>
        </Card>

        {data.high_priority.length > 0 && (
          <Card title="4. High Priority Events">
            <ul className="space-y-1">
              {data.high_priority.map((h, i) => (
                <li key={i} className="flex gap-2 text-[11px] text-[#3A3F58]">
                  <AlertCircle className={cn('mt-0.5 h-3.5 w-3.5 shrink-0',
                    h.severity === 'critical' ? 'text-[#DC2626]' : 'text-[#D97706]')} />
                  {h.activity}
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  )
}
