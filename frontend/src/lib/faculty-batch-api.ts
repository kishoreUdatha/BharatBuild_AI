/**
 * Batch Registration Details API.
 *
 * Kept separate from faculty-api.ts: the detail screen has seven tabs with
 * their own shapes, and folding them into the list API would make that module
 * hard to read.
 */

import { apiClient } from '@/lib/api-client'
import type { StoredFileInfo, UploadOptions } from '@/lib/file-api'

type Params = Record<string, string | number | boolean | undefined>

const clean = (params: Params) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''))

/** Present on every tab payload: whether this reader may change the batch. */
export interface BatchTabBase { can_manage?: boolean }

export interface BatchHeader {
  id: string
  batch_code: string
  title: string | null
  project_type: string | null
  department: string
  year: string | null
  semester: string | null
  section: string | null
  academic_year: string
  guide: string | null
  status: string
  status_key: string
  registration_complete: boolean
  completeness: number
  created_at: string
  updated_at: string | null
  submitted_at: string | null
}

export interface Check {
  key: string
  label: string
  passed: boolean
  detail?: string
}

export interface TabKpi {
  id: string
  value: string
  label: string
}

export interface TimelineStep {
  step: string
  occurred_at: string | null
  actor: string | null
  done: boolean
}

export interface BatchMember {
  id: string
  student_id: string
  name: string | null
  roll_number: string | null
  role: string
  responsibility: string | null
  mobile: string | null
  email: string | null
  department: string | null
  section: string | null
  profile_verified: boolean
  is_active: boolean
  joined_at?: string
  profile_completion?: number
  declaration_signed?: boolean
}

export interface PaperSummary {
  title: string | null
  authors: string | null
  publication: string | null
  year: number | null
  doi: string | null
  url: string | null
  status: string
  verified_by: string | null
  verified_at: string | null
  improvement_note: string | null
  publisher?: string | null
  publication_type?: string | null
  volume?: string | null
  pages?: string | null
  indexing?: string | null
  quartile?: string | null
  file_name?: string | null
  file_size?: number | null
  page_count?: number | null
  /** Distinct from `url`: whether we hold the PDF, not where it was published. */
  has_file?: boolean
  uploaded_by?: string | null
  uploaded_at?: string | null
  abstract_summary?: string | null
  dataset?: string | null
  key_methods?: string[]
  metrics?: { name: string; value: string }[]
}

export interface OverviewTab {
  header: BatchHeader
  members: BatchMember[]
  cohort_note: string
  project: {
    title: string | null
    domain: string | null
    problem_statement: string | null
    abstract: string | null
    objectives: string[]
    technologies: string[]
    expected_outcome: string | null
  }
  base_paper: PaperSummary | null
  checklist: Check[]
  checks_passed: number
  checks_total: number
  approval: {
    status: string
    submitted_by: string | null
    submitted_at: string | null
    reviewer: string | null
    sla: string | null
  }
  documents: { name: string; status: string; status_key: string }[]
  document_count: number
  timeline: TimelineStep[]
}

export interface TeamTab {
  header: BatchHeader
  kpis: TabKpi[]
  members: BatchMember[]
  checklist: Check[]
  checks_passed: number
  checks_total: number
  roles: { role: string; count: number }[]
  internal_note: string | null
  note_updated_by: string | null
  note_updated_at: string | null
  timeline: TimelineStep[]
}

export interface ProjectTab {
  header: BatchHeader
  kpis: TabKpi[]
  overview: {
    title: string | null
    domain: string | null
    project_type: string | null
    keywords: string[]
    problem_statement: string | null
    abstract: string | null
  }
  objectives: { position: number; text: string; status: string }[]
  methodology: { position: number; title: string; description: string | null }[]
  outcomes: string[]
  in_scope: string[]
  out_of_scope: string[]
  deliverables: string[]
  technology_stack: { layer: string; items: string[] }[]
  duration: {
    start_date: string | null
    target_completion: string | null
    weeks: number | null
    weekly_effort_hours: number | null
  }
  checklist: Check[]
  checks_passed: number
  checks_total: number
  faculty_note: string | null
  /** True while the registration is with a guide or already approved. */
  locked: boolean
  locked_reason: string | null
  history: TimelineStep[]
}

export interface PapersTab {
  header: BatchHeader
  kpis: TabKpi[]
  primary: PaperSummary | null
  improvement: {
    current_limitation: string | null
    proposed: string | null
    contributions: string[]
  }
  supporting: {
    id: string
    title: string
    authors: string | null
    source: string | null
    year: number | null
    doi: string | null
    doi_label: string
    purpose: string | null
    url: string | null
  }[]
  checklist: Check[]
  checks_passed: number
  checks_total: number
  quality: {
    relevance: number | null
    methodology: number | null
    recency: number | null
    credibility: number | null
    overall: number | null
    label: string | null
  }
  faculty_note: string | null
  verification_note: { body: string | null; actor: string | null; at: string | null }
  primary_tags: { label: string; tone: string }[]
  activity: TimelineStep[]
  quick_actions: {
    pending_papers: number
    papers_total: number
    has_doi: boolean
    similarity_percent: number | null
  }
}

export interface BatchDocumentRow {
  id: string
  name: string
  category: string
  version: string | null
  uploaded_by: string | null
  uploaded_at: string | null
  file_size: number
  status: string
  status_key: string
  similarity_percent: number | null
  is_required: boolean
  /** Whether bytes exist behind this row, as opposed to a "Missing" slot. */
  has_file: boolean
  superseded: boolean
  can_remove: boolean
  page_count?: number | null
  faculty_note?: string | null
  virus_scan_passed?: boolean
  file?: StoredFileInfo | null
}

export interface DocumentsTab {
  header: BatchHeader
  kpis: TabKpi[]
  rows: BatchDocumentRow[]
  checklist: { name: string; status: string; status_key: string; passed: boolean }[]
  checklist_complete: number
  checklist_total: number
  queue: BatchDocumentRow[]
  storage_by_category: { category: string; bytes: number }[]
  storage_used: number
  categories: string[]
  selected: BatchDocumentRow | null
  recent_activity: { activity: string; actor: string | null; occurred_at: string; severity: string }[]
  can_manage: boolean
  upload: UploadOptions
  missing_required: string[]
}

export interface JourneyStage {
  key: string
  step: string
  kind: string
  occurred_at: string | null
  actor: string | null
  state: 'done' | 'current' | 'pending'
  done: boolean
}

export interface ApprovalHistoryEntry {
  id: string
  kind: string
  title: string
  body: string | null
  summary: string | null
  bullets: string[]
  status_label: string | null
  actor: string | null
  actor_role: string | null
  occurred_at: string
  duration_minutes: number | null
  cycle: number
  actions: string[]
}

export interface ApprovalsTab {
  header: BatchHeader
  kpis: TabKpi[]
  current_status: string
  current_status_key: string
  total_review_time_hours: number | null
  approval_status: {
    status: string
    status_key: string
    checks_passed: number
    checks_total: number
    percent: number
    reviewer: string | null
    submitted_by: string | null
    last_action_at: string | null
    sla: string | null
    blocking_item: string | null
  }
  journey: JourneyStage[]
  history: ApprovalHistoryEntry[]
  internal_notes: { id: string; title: string; body: string | null; actor: string | null; occurred_at: string }[]
  comparison: {
    field: string
    original: string
    revised: string
    resolved: boolean
    source: string
  }[]
  comparison_resolved: number
  checklist: Check[]
  checks_passed: number
  checks_total: number
  blocking_item: string | null
  sla: string | null
  participants: { name: string; role: string; tag: string }[]
  decision_summary: {
    approvals: number
    change_requests: number
    resubmissions: number
    rejections: number
    avg_student_response_hours: number | null
    avg_faculty_review_hours: number | null
  }
}

export interface ActivityRow {
  id: string
  event_code: string
  occurred_at: string
  actor: string | null
  actor_role: string | null
  activity: string
  module: string
  details: string | null
  status_label: string | null
  severity: string
  ip_address?: string | null
  user_agent?: string | null
  source?: string | null
  changed_field?: string | null
  previous_value?: string | null
  current_value?: string | null
}

export interface ActivityTab {
  header: BatchHeader
  kpis: TabKpi[]
  rows: ActivityRow[]
  page: number
  pages: number
  per_page: number
  total: number
  showing_from: number
  showing_to: number
  summary: { module: string; count: number }[]
  participants: { name: string; count: number }[]
  high_priority: { activity: string; severity: string; occurred_at: string }[]
  modules: string[]
  actors: string[]
  selected: ActivityRow | null
  last_integrity_check: string | null
}

function tab<T>(code: string, name: string, params: Params = {}): Promise<T> {
  return apiClient.get<T>(`/faculty/batches/${encodeURIComponent(code)}/${name}`, { params: clean(params) })
}

export const fetchBatchOverview = (code: string) => tab<OverviewTab>(code, 'overview')
export const fetchBatchTeam = (code: string) => tab<TeamTab>(code, 'team')
export const fetchBatchProject = (code: string) => tab<ProjectTab>(code, 'project')
export const fetchBatchPapers = (code: string) => tab<PapersTab>(code, 'papers')
export const fetchBatchDocuments = (code: string) => tab<DocumentsTab>(code, 'documents')
export const fetchBatchApprovals = (code: string) => tab<ApprovalsTab>(code, 'approvals')
export const fetchBatchActivity = (code: string, params: Params = {}) =>
  tab<ActivityTab>(code, 'activity', params)

const base = (code: string) => `/faculty/batches/${encodeURIComponent(code)}`

export const updateInternalNote = (code: string, note: string) =>
  apiClient.patch<{ internal_note: string | null }>(`${base(code)}/internal-note`, { note })

export const changeBatchLeader = (code: string, memberId: string) =>
  apiClient.post<{ leader_id: string }>(`${base(code)}/leader`, { member_id: memberId })

export const updateMemberRoles = (code: string, roles: Record<string, string>) =>
  apiClient.patch<{ updated: number }>(`${base(code)}/roles`, { roles })

export const removeBatchMember = (code: string, memberId: string, reason: string) =>
  apiClient.post<{ removed: string; reason: string }>(`${base(code)}/remove-member`, {
    member_id: memberId,
    reason,
  })

export const decideDocument = (
  code: string,
  documentId: string,
  decision: 'verify' | 'request_changes',
  note?: string
) =>
  apiClient.post<{ document_id: string; status: string }>(`${base(code)}/documents/decide`, {
    document_id: documentId,
    decision,
    note,
  })

export async function downloadTeamList(code: string): Promise<void> {
  const blob = await apiClient.get<Blob>(`${base(code)}/team-list`, { responseType: 'blob' })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = `${code}-team.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** Export Log - exports the rows the current filters select, not the whole table. */
export async function downloadActivityLog(code: string, params: Params = {}): Promise<void> {
  const blob = await apiClient.get<Blob>(`${base(code)}/activity-log.csv`, {
    params: clean(params),
    responseType: 'blob',
  })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = `${code}-activity-log.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** Saves text the browser already has - used by Download Abstract. */
export function downloadText(filename: string, text: string): void {
  const href = URL.createObjectURL(new Blob([text], { type: 'text/plain;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** Verify the primary base paper, or send it back with a reason. */
export const decideBasePaper = (code: string, decision: 'verify' | 'request_changes', note?: string) =>
  apiClient.post<{ status: string; message: string }>(
    `/faculty/batches/${encodeURIComponent(code)}/base-paper/decide`,
    { decision, note: note || null })
