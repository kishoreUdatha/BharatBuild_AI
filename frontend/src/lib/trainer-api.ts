/**
 * Trainer Portal API - AI story approval.
 */

import { apiClient } from '@/lib/api-client'
import type { SubmissionRow } from '@/lib/submissions-api'

type Params = Record<string, string | number | boolean | undefined>

const clean = (params: Params) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''))

export interface StoryRow {
  id: string
  key: string
  title: string
  epic_key: string | null
  epic_title: string | null
  acceptance_met: number
  acceptance_total: number
  acceptance_complete: boolean
  story_points: number
  position: number
  priority: string
  priority_label: string
  ai_confidence: number | null
  review_status: string
  review_status_label: string
}

export interface StoryDetail extends StoryRow {
  narrative: string | null
  dependencies: string | null
  trainer_comment: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  acceptance_criteria: { id: string; text: string; met: boolean }[]
  definition_of_done: { id: string; text: string; met: boolean }[]
  acceptance_label: string
  open_revision: { note: string; requested_at: string } | null
}

export interface StoryBoard {
  header: {
    batch_id: string
    batch_code: string
    join_code: string | null
    display_name: string
    project_title: string | null
    department: string
    guide: string | null
  }
  run: {
    model: string | null
    generated_at: string | null
    source_summary: string | null
    quality_percent: number | null
  } | null
  stages: { key: string; label: string; state: 'complete' | 'active' | 'locked'; note: string }[]
  kpis: { id: string; value: string; label: string }[]
  rows: StoryRow[]
  selected: StoryDetail | null
  epics: { key: string; title: string }[]
  priorities: string[]
  counts: {
    total: number
    reviewed: number
    needs_review: number
    approved: number
    rejected: number
    in_backlog: number
    showing: number
  }
  checklist: {
    items: { key: string; label: string; passed: boolean; detail: string }[]
    passed: number
    total: number
    outstanding: number
    outstanding_label: string
  }
  can_continue: boolean
  after_approval: string[]
  governance: string
}

const base = (code: string) => `/trainer/batches/${encodeURIComponent(code)}`

export const fetchStoryBoard = (code: string, params: Params = {}) =>
  apiClient.get<StoryBoard>(`${base(code)}/stories`, { params: clean(params) })

export const decideStory = (code: string, storyId: string, decision: string, note?: string) =>
  apiClient.post<{ key: string; review_status: string }>(
    `${base(code)}/stories/${storyId}/decision`, { decision, note }
  )

export const updateStory = (code: string, storyId: string, patch: {
  story_points?: number
  priority?: string
  trainer_comment?: string
  dependencies?: string
}) => apiClient.patch<StoryDetail>(`${base(code)}/stories/${storyId}`, patch)

export const markStoriesReviewed = (code: string, storyIds: string[]) =>
  apiClient.post<{ marked: string[]; count: number }>(
    `${base(code)}/stories/mark-reviewed`, { story_ids: storyIds }
  )

export const moveToBacklog = (code: string) =>
  apiClient.post<{ moved: string[]; count: number }>(`${base(code)}/stories/move-to-backlog`, {})

export interface RegenerationPlan {
  scope: string
  total: number
  undecided: number
  decided: number
  will_replace: number
  decisions_discarded: number
}

export const previewRegeneration = (code: string, scope: 'pending' | 'all') =>
  apiClient.get<RegenerationPlan>(`${base(code)}/stories/regenerate-preview`, { params: { scope } })

export const regenerateDrafts = (
  code: string, scope: 'pending' | 'all' = 'pending', confirm = false
) => apiClient.post<{
  scope: string
  model: string
  created_count: number
  kept_count: number
  replaced_count: number
  decisions_discarded: number
}>(`${base(code)}/stories/regenerate`, { scope, confirm })

export function errorText(err: any, fallback: string): string {
  const d = err?.response?.data?.detail
  if (typeof d === 'string' && d.trim()) return d
  if (Array.isArray(d)) return d.map((x: any) => x?.msg).filter(Boolean).join('; ') || fallback
  return fallback
}


// ------------------------------------------------------------- workspace

export interface Kpi { id: string; value: string; label: string }

export interface BatchCard {
  id: string
  batch_code: string
  title: string | null
  section: string | null
  year: string | null
  department: string
  my_role: string
  members: number
  team_size: number
  progress: number
  registration_status: string
  registration_status_key: string
  reviews_pending: number
  reviews_overdue: number
  stories_total: number
  stories_needs_review: number
  stories_in_backlog: number
  sprints_total: number
  tasks_total: number
  tasks_open: number
  tasks_overdue: number
  base_paper: string
  status: string
  batch_no: string | null
  semester: string | null
  project_type: string | null
  guide: string | null
  student_names: string[]
  team: { roll: string; name: string | null }[]
  created_at: string | null
}

export interface ReviewRow {
  id: string
  can_complete: boolean
  batch_code: string
  batch_title: string | null
  section: string | null
  review_type: string
  scheduled_at: string
  status: string
  status_label: string
  score: number | null
  remarks: string | null
  completed_at: string | null
  days_out: number
}

export interface WorkBatch {
  batch_code: string
  title: string | null
  section: string | null
  progress: number
  members: { name: string | null; roll_number: string | null; is_lead: boolean; responsibility: string | null }[]
  stages: { stage: string; percent: number; complete: boolean }[]
  /** The shared submission shape - built by the submissions service. */
  submissions: SubmissionRow[]
  pending_submissions: number
}

export interface EvidenceRow {
  kind: string
  id: string | null
  actionable: boolean
  batch_code: string
  name: string
  category: string
  state: string
  state_label: string
  verified: boolean
  required: boolean
  at: string | null
}

const T = (path: string, params: Params = {}) =>
  apiClient.get<any>(`/trainer/${path}`, { params: clean(params) })

export interface BatchQuery {
  search?: string
  department?: string
  section?: string
  batch_no?: string
  project_status?: string
  semester?: string
  guide?: string
  batch_type?: string
  date_from?: string
  date_to?: string
  sort?: string
  page?: number
  per_page?: number
}

export interface BatchListView {
  rows: BatchCard[]
  kpis: Kpi[]
  total: number
  page: number
  pages: number
  per_page: number
  sort: string
  academic_year: string
  stats: {
    total_batches: number
    active_batches: number
    completed_batches: number
    pending_reviews: number
    total_students: number
  }
  filters: {
    departments: string[]
    sections: string[]
    batch_nos: string[]
    semesters: string[]
    guides: string[]
    types: string[]
    statuses: string[]
  }
}

export const fetchMyBatches = (query: BatchQuery = {}) =>
  T('batches', query as Params) as Promise<BatchListView>

export const fetchTrainerReviews = (status?: string) =>
  T('reviews', { status }) as Promise<{ rows: ReviewRow[]; kpis: Kpi[]; statuses: string[] }>

export const fetchStudentWork = (batch?: string) =>
  T('student-work', { batch }) as Promise<{ rows: WorkBatch[]; kpis: Kpi[] }>

export const fetchEvidence = (status?: string) =>
  T('evidence', { status }) as Promise<{ rows: EvidenceRow[]; kpis: Kpi[]; coverage: number }>

export const fetchTrainerReports = () =>
  T('reports') as Promise<{
    academic_year: string
    kpis: Kpi[]
    sections: { section: string; batches: number; students: number; progress: number
                reviews_pending: number; reviews_overdue: number }[]
    stages: { stage: string; percent: number }[]
  }>

export const fetchTrainerSettings = () =>
  T('settings') as Promise<{
    profile: { name: string | null; email: string; department: string | null
               college: string | null; role: string }
    academic_year: string
    section_roles: { department: string; year: string; semester: string
                     section: string; role: string; responsibility: string | null }[]
    department_offices: { department: string; role: string }[]
    managed_batches: number
  }>


// --------------------------------------------------------- trainer decisions
// These write the same rows the Faculty Portal writes, through the same rules.

export const completeReview = (code: string, reviewId: string,
  body: { score?: number; remarks?: string }) =>
  apiClient.post<{ review_id: string; status: string; review_type: string; score: number | null }>(
    `${base(code)}/reviews/${reviewId}/complete`, body)

export const rescheduleReview = (code: string, reviewId: string, scheduledAt: string) =>
  apiClient.post<{ review_id: string; scheduled_at: string }>(
    `${base(code)}/reviews/${reviewId}/reschedule`, { scheduled_at: scheduledAt })

export const cancelReview = (code: string, reviewId: string, reason: string) =>
  apiClient.post<{ review_id: string; status: string }>(
    `${base(code)}/reviews/${reviewId}/cancel`, { reason })

export interface TrainerPending {
  /** Keyed by nav destination, so a new badge needs no new endpoint. */
  counts: Record<string, number>
  total: number
}

export interface TrainerCollege {
  id: string
  name: string
  code: string
  /** The sections they teach there, e.g. ["CSE-A", "ECE-B"]. */
  sections: string[]
}

export interface TrainerColleges {
  academic_year: string
  colleges: TrainerCollege[]
  /** False when they teach at one college and have nothing to choose. */
  must_choose: boolean
}

export const fetchTrainerColleges = () =>
  apiClient.get<TrainerColleges>('/trainer/colleges')

/** The college every request is scoped to. Read by the api client. */
export const ACTIVE_COLLEGE_KEY = 'active_college_id'

export const getActiveCollege = () =>
  typeof window === 'undefined' ? null : localStorage.getItem(ACTIVE_COLLEGE_KEY)

export const setActiveCollege = (id: string | null) => {
  if (typeof window === 'undefined') return
  if (id) localStorage.setItem(ACTIVE_COLLEGE_KEY, id)
  else localStorage.removeItem(ACTIVE_COLLEGE_KEY)
}

export interface CollegeTrainer {
  id: string
  name: string
  email: string
  /** What they cover here: "Whole college", or "CSE-A". */
  scope: string[]
  batches: number
}

export interface CollegeTrainers {
  academic_year: string
  trainers: CollegeTrainer[]
  /** False when one trainer works here and there is nothing to choose. */
  can_filter: boolean
}

export const fetchCollegeTrainers = () =>
  apiClient.get<CollegeTrainers>('/trainer/trainers')

/** The trainer a manager has focused on. Read by the api client. */
export const ACTIVE_TRAINER_KEY = 'active_trainer_id'

export const getActiveTrainer = () =>
  typeof window === 'undefined' ? null : localStorage.getItem(ACTIVE_TRAINER_KEY)

export const setActiveTrainer = (id: string | null) => {
  if (typeof window === 'undefined') return
  if (id) localStorage.setItem(ACTIVE_TRAINER_KEY, id)
  else localStorage.removeItem(ACTIVE_TRAINER_KEY)
}

export const fetchTrainerPending = () =>
  apiClient.get<TrainerPending>('/trainer/pending')

export const decideDocument = (code: string, documentId: string,
  decision: 'verify' | 'request_changes', note?: string) =>
  apiClient.post<{ document_id: string; status: string; name: string }>(
    `${base(code)}/documents/decide`, { document_id: documentId, decision, note })


export interface TrainerHome {
  trainer: string | null
  academic_year: string
  scope: { batches: number; students: number; average_progress: number }
  attention: { id: string; count: number; severity: string; label: string; hint: string; href: string }[]
  clear: boolean
  overdue_reviews: {
    id: string; batch_code: string; batch_title: string | null
    review_type: string; scheduled_at: string; days: number
  }[]
  story_queue: { batch_code: string; batch_title: string | null; needs_review: number; total: number }[]
  needs_attention: {
    batch_code: string; batch_title: string | null; section: string | null
    progress: number; overdue: number
  }[]
}

export const fetchTrainerHome = () => T('home') as Promise<TrainerHome>

// ============================================
// Batch roster: capabilities, export, import, create
// ============================================

export interface TrainerCapabilities {
  academic_year: string
  departments: string[]
  manageable_departments: string[]
  can_manage_department: boolean
}

export const fetchTrainerCapabilities = () =>
  T('capabilities') as Promise<TrainerCapabilities>

/** Pull a file through the client so an expired token still refreshes. */
async function downloadCsv(path: string, filename: string, params: Params = {}) {
  const blob = await apiClient.get<Blob>(`/trainer/${path}`, {
    params: clean(params),
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

export const exportMyBatches = (search?: string, academicYear?: string) =>
  downloadCsv('batches.csv', `my-batches-${academicYear ?? 'current'}.csv`, { search })

/** The filled-in sample allocation sheet, in either format. */
export const downloadSampleSheet = (format: 'xlsx' | 'csv' = 'xlsx') =>
  downloadCsv('imports/template', `batch-allocation-sample.${format}`, { format })

export const importBatchAllocation = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  form.append('import_type', 'batch_allocation')
  return apiClient.post<ImportResult>('/trainer/imports', form) as Promise<ImportResult>
}

export interface CreateBatchInput {
  department: string
  year: string
  semester: string
  section: string
  project_type?: string
  team_size?: number
  count?: number
}

export const createTrainerBatches = (input: CreateBatchInput) =>
  apiClient.post<any>('/trainer/batches', input)

// ============================================
// Import results
// ============================================

export interface ImportBatchRow {
  batch_code: string
  batch_no: string | null
  title: string | null
  department: string | null
  section: string | null
  students: number
  guide: string | null
  outcome: 'Created' | 'Updated'
  created_at: string | null
}

export interface ImportIssue {
  row: number | null
  field: string | null
  message: string
  value: string | null
  severity: string
}

export interface ImportResult {
  id: string
  import_code: string
  file_name: string
  imported_by: string | null
  started_at: string
  status: string
  status_key: string
  rows_total: number
  rows_imported: number
  rows_failed: number
  rows_duplicate: number
  issues: ImportIssue[]
  issue_count: number
  summary: {
    batches: ImportBatchRow[]
    batches_created: number
    batches_updated: number
    students_assigned: number
    guides_assigned: number
  }
}

export interface ImportHistoryRow {
  id: string
  import_code: string
  file_name: string
  imported_by: string | null
  started_at: string
  rows_total: number
  rows_imported: number
  rows_failed: number
  rows_duplicate: number
  status: string
  status_key: string
}

export const fetchImportResult = (runId: string) =>
  apiClient.get<ImportResult>(`/trainer/imports/${runId}`)

export const fetchImportHistory = (limit = 10) =>
  apiClient.get<{ rows: ImportHistoryRow[]; total?: number }>('/trainer/imports', {
    params: { limit },
  })

export interface ImportKpi { id: string; value: string; label: string }

export interface ImportHistory {
  kpis: ImportKpi[]
  rows: ImportHistoryRow[]
  page: number
  pages: number
  per_page: number
  total: number
  showing_from: number
  showing_to: number
  import_types: { key: string; label: string }[]
  statuses: { key: string; label: string }[]
}

export const fetchImports = (params: {
  page?: number
  limit?: number
  search?: string
  import_type?: string
  status?: string
} = {}) =>
  apiClient.get<ImportHistory>('/trainer/imports', {
    // Blank filters are dropped rather than sent as empty strings, which the
    // server would treat as "match the empty value" and return nothing.
    params: Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== '' && v !== undefined)),
  })

export const downloadImportReport = (runId: string, importCode: string) =>
  downloadCsv(`imports/${runId}/report.csv`, `${importCode}-report.csv`)


// ----------------------------------------------------------- user stories
//
// The product backlog: what AI planning hands over, and everything a trainer
// does to it afterwards. `base(code)` is the same batch-scoped prefix the
// approval screen uses, so both talk to one batch through one address.

export interface Person {
  id: string
  name: string
  roll: string | null
  initials: string
}

export interface SprintRef {
  id: string
  key: string
  name: string
  goal: string | null
  state: string
  state_label: string
  window: string | null
  start_date: string | null
  end_date: string | null
}

export interface UserStoryRow {
  id: string
  key: string
  title: string
  type: string
  type_label: string
  epic_key: string | null
  epic_title: string | null
  assignee: Person | null
  sprint: SprintRef | null
  priority: string
  priority_label: string
  story_points: number
  status: string
  status_label: string
  review_status: string
  review_status_label: string
  created_at: string
  created_by: string
  labels: string[]
  due_date: string | null
  /** Worked out from the due date on every read, never stored. */
  overdue: boolean
  /** Where the card sits in its column, rewritten on every drop. */
  position: number
}

export interface StoryTask {
  id: string
  title: string
  status: string
  status_label: string
  done: boolean
  assignee: Person | null
  due_date: string | null
}

export interface StoryNote {
  id: string
  author: string
  body: string
  created_at: string
}

export interface StoryActivity {
  id: string
  kind: string
  actor: string
  summary: string
  from_value: string | null
  to_value: string | null
  occurred_at: string
}

export interface StoryAttachment {
  id: string
  name: string
  mime: string | null
  size: number
  size_label: string
  uploaded_by: string | null
  uploaded_by_id: string | null
  uploaded_at: string
}

export interface UserStoryDetail extends UserStoryRow {
  narrative: string | null
  dependencies: string | null
  trainer_comment: string | null
  ai_confidence: number | null
  started_at: string | null
  completed_at: string | null
  updated_at: string | null
  acceptance_criteria: { id: string; text: string; met: boolean }[]
  definition_of_done: { id: string; text: string; met: boolean }[]
  tasks: StoryTask[]
  comments: StoryNote[]
  activity: StoryActivity[]
  attachments: StoryAttachment[]
  counts: {
    tasks: number
    tasks_done: number
    comments: number
    activity: number
    attachments: number
  }
}

export interface StoryKpi {
  id: string
  value: number
  label: string
  percent: number | null
}

export interface Option { value: string; label: string }

export interface UserStoryBoard {
  header: {
    batch_id: string
    batch_code: string
    project_title: string | null
    department: string
    section: string | null
    guide: string | null
    members: number
  }
  kpis: StoryKpi[]
  rows: UserStoryRow[]
  selected: UserStoryDetail | null
  total: number
  page: number
  pages: number
  per_page: number
  sort: string
  backlog_total: number
  counts: Record<string, number>
  filters: {
    epics: { key: string; title: string }[]
    sprints: SprintRef[]
    assignees: (Person & { responsibility: string | null })[]
    statuses: Option[]
    priorities: Option[]
    types: Option[]
    points: number[]
    creators: string[]
    sorts: Option[]
  }
  students: (Person & {
    responsibility: string | null
    stories: number
    points: number
    done: number
    percent: number
  })[]
  /** Set only while the backlog is empty: what is still upstream in planning. */
  planning: { drafted: number; needs_review: number; awaiting_move: number } | null
}

export interface StoryQuery {
  search?: string
  status?: string
  epic?: string
  assignee?: string
  sprint?: string
  priority?: string
  points?: string
  type?: string
  created_by?: string
  date_from?: string
  date_to?: string
  sort?: string
  page?: number
  per_page?: number
  selected?: string
}

export const fetchUserStories = (code: string, query: StoryQuery = {}) =>
  apiClient.get<UserStoryBoard>(`${base(code)}/user-stories`,
    { params: clean(query as Params) })

export interface NewStoryInput {
  title: string
  narrative?: string
  epic_key?: string
  story_points?: number
  priority?: string
  story_type?: string
  status?: string
  assignee_id?: string
  sprint_id?: string
  dependencies?: string
  acceptance_criteria?: string[]
}

export const addUserStory = (code: string, input: NewStoryInput) =>
  apiClient.post<{ id: string; key: string }>(`${base(code)}/user-stories`, input)

/**
 * Patch one story.
 *
 * `null` clears a field and an omitted key leaves it alone, which is the same
 * distinction the API makes - so pass `assignee_id: null` to unassign rather
 * than an empty string.
 */
export interface StoryPatch {
  title?: string
  narrative?: string
  story_points?: number
  priority?: string
  story_type?: string
  status?: string
  assignee_id?: string | null
  sprint_id?: string | null
  dependencies?: string
  trainer_comment?: string
  due_date?: string | null
}

/** The column, top to bottom, after a drag. */
export const reorderUserStories = (code: string, storyIds: string[]) =>
  apiClient.post<{ reordered: number; changed: number }>(
    `${base(code)}/user-stories/reorder`, { story_ids: storyIds })

export const patchUserStory = (code: string, storyId: string, patch: StoryPatch) =>
  apiClient.patch<{ id: string; key: string; changed: string[] }>(
    `${base(code)}/user-stories/${storyId}`, patch
  )

export const deleteUserStory = (code: string, storyId: string) =>
  apiClient.delete<{
    deleted: string
    title: string
    detached_commits: number
    detached_tasks: number
    message: string
  }>(`${base(code)}/user-stories/${storyId}`)

export const commentOnStory = (code: string, storyId: string, body: string) =>
  apiClient.post<{ story: string; author: string }>(
    `${base(code)}/user-stories/${storyId}/comments`, { body }
  )

export interface NewSprintInput {
  name: string
  goal?: string
  start_date?: string
  end_date?: string
  state?: string
}

export const addSprint = (code: string, input: NewSprintInput) =>
  apiClient.post<SprintRef>(`${base(code)}/sprints`, input)

export interface GitConnection {
  batch_code: string
  /** Paste this into the repository's webhook settings. */
  webhook_url: string
  /** False on a local instance: correct, but not resolvable from GitHub. */
  reachable: boolean
  repo_url: string | null
  secret: string | null
  connected: boolean
  /** Whoever wired it up - often the batch leader, whose repo it is. */
  connected_by: { name: string; role: string; at: string | null } | null
  commits: number
  last_received_at: string | null
  key_example: string
  /** One repository, several committers: who has claimed which identity. */
  team: {
    student_id: string
    name: string
    username: string | null
    emails: string[]
    connected: boolean
    verified: boolean
    commits: number
    last_commit_at: string | null
  }[]
}

export const decideRegistration = (
  code: string,
  decision: 'request_changes' | 'approve' | 'reject',
  note?: string,
) =>
  apiClient.post<{ batch_code: string; registration_status: string; message: string }>(
    `${base(code)}/registration/decide`, { decision, note: note ?? null })

export const getGitConnection = (code: string) =>
  apiClient.get<GitConnection>(`${base(code)}/git`)

export const connectGit = (code: string, input: { repo_url?: string; rotate_secret?: boolean }) =>
  apiClient.post<GitConnection>(`${base(code)}/git`, input)

export const exportUserStories = (code: string, query: StoryQuery = {}) =>
  downloadCsv(`batches/${encodeURIComponent(code)}/user-stories.csv`,
    `${code}-user-stories.csv`,
    // Paging and the open story are not part of what gets exported: the file
    // is the filtered view, not the page the trainer happens to be looking at.
    clean({
      search: query.search, status: query.status, epic: query.epic,
      assignee: query.assignee, sprint: query.sprint,
      priority: query.priority, type: query.type,
    } as Params))

/** The workbook the importer reads: story sheet plus its field guide. */
export const downloadStoryTemplate = (code: string) =>
  downloadCsv(`batches/${encodeURIComponent(code)}/user-stories/template.xlsx`,
    'bharatbuild-user-stories-template.xlsx')

export interface ImportPreviewRow {
  row: number
  key: string
  summary: string
  work_type: string | null
  epic: string | null
  new_epic: boolean
  priority: string | null
  story_points: number | null
  assignee: Person | null
  sprint: string | null
  new_sprint: boolean
  status: string | null
  labels: string | null
  criteria: number
  note: string | null
  /** Blocking: the row will not be imported until these are fixed. */
  issues: string[]
  /** Non-blocking: the row imports, with something worth knowing about it. */
  warnings: string[]
}

export interface StoryImportResult {
  dry_run: boolean
  /** Which template columns were found in the uploaded sheet. */
  columns: string[]
  rows: number
  ready: number
  preview: ImportPreviewRow[]
  created: string[]
  count: number
  issues: { row: number; issue: string }[]
  notes: { row: number; issue: string }[]
}

/**
 * Read an import sheet.
 *
 * `dryRun` is the template's own Validate step: the same rows come back, with
 * the same per-row problems, and nothing is written until it is called again
 * without it.
 */
export const importUserStories = (code: string, file: File, dryRun = false) => {
  const form = new FormData()
  form.append('file', file)
  return apiClient.post<StoryImportResult>(
    `${base(code)}/user-stories/import${dryRun ? '?dry_run=true' : ''}`, form
  ) as Promise<StoryImportResult>
}


// ---------------------------------------------------------------- sprints
//
// A sprint's numbers are its stories' numbers - the API rolls them up rather
// than storing them, so nothing here can drift from the backlog it describes.

export interface SprintStoryLine {
  id: string
  key: string
  title: string
  status: string
  status_label: string
  story_points: number
  assignee: Person | null
  epic_key: string | null
}

export interface SprintRollUp {
  stories: number
  points: number
  done: number
  done_points: number
  percent: number
  points_percent: number
  counts: Record<string, number>
  days_left: number | null
  overdue: boolean
  story_rows: SprintStoryLine[]
}

export interface SprintRow extends SprintRollUp {
  id: string
  key: string
  name: string
  goal: string | null
  state: string
  state_label: string
  start_date: string | null
  end_date: string | null
  window: string | null
}

export interface BatchHeader {
  batch_id: string
  batch_code: string
  project_title: string | null
  department: string
  section: string | null
  guide: string | null
}

export interface SprintBoard {
  header: BatchHeader
  kpis: { id: string; value: number; label: string; hint: string | null }[]
  rows: SprintRow[]
  unscheduled: SprintRollUp
  states: Option[]
  backlog_total: number
}

export const fetchSprints = (code: string) =>
  apiClient.get<SprintBoard>(`${base(code)}/sprints`)

export interface SprintPatch {
  name?: string
  goal?: string
  start_date?: string | null
  end_date?: string | null
  state?: string
}

export const patchSprint = (code: string, sprintId: string, patch: SprintPatch) =>
  apiClient.patch<{ id: string; name: string; state: string }>(
    `${base(code)}/sprints/${sprintId}`, patch
  )

/** `sprintId: null` takes the stories out of every sprint. */
export const scheduleStories = (code: string, sprintId: string | null, storyIds: string[]) =>
  apiClient.post<{ moved: string[]; count: number; sprint: string | null }>(
    `${base(code)}/sprints/schedule`, { sprint_id: sprintId, story_ids: storyIds }
  )

// ------------------------------------------------------ one story, any portal
//
// `/stories/{id}` is outside the trainer prefix on purpose: a trainer, a guide,
// an admin and the batch's own students all open the same address. The API
// returns what this account may do with it rather than the caller assuming.

export interface SharedStory {
  story: UserStoryDetail
  batch: {
    batch_id: string
    batch_code: string
    project_title: string | null
    department: string
    section: string | null
    guide: string | null
    members: number
  }
  permissions: {
    can_edit: boolean
    can_comment: boolean
    /** The assignee gets the status and progress controls without full edit. */
    can_change_status: boolean
    can_update_progress: boolean
    is_assignee: boolean
    role: string
    user_id: string
  }
  /** Written by the repository webhook, so it sits beside the story. */
  commits: {
    sha: string
    short_sha: string
    message: string
    url: string | null
    branch: string | null
    author: string
    committed_at: string | null
  }[]
  options: {
    sprints: { id: string; name: string; window: string | null }[]
    epics: { key: string; title: string }[]
    assignees: { id: string; name: string; roll: string | null }[]
  }
}

export const fetchStory = (storyId: string) =>
  apiClient.get<SharedStory>(`/stories/${storyId}`)

export const patchSharedStory = (storyId: string, patch: StoryPatch) =>
  apiClient.patch<{ id: string; key: string; changed: string[] }>(
    `/stories/${storyId}`, patch
  )

export const attachToStory = (storyId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return apiClient.post<{ id: string; name: string; size_label: string }>(
    `/stories/${storyId}/attachments`, form
  ) as Promise<{ id: string; name: string; size_label: string }>
}

/** Pulled through the client so the request carries the auth header. */
export async function downloadAttachment(storyId: string, id: string, name: string) {
  const blob = await apiClient.get<Blob>(`/stories/${storyId}/attachments/${id}`,
    { responseType: 'blob' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

export const removeAttachment = (storyId: string, id: string) =>
  apiClient.delete<{ removed: string }>(`/stories/${storyId}/attachments/${id}`)

/** Criteria are rows, so each one is added, reworded, ticked and dropped. */
export const addCriterion = (storyId: string, text: string, kind = 'acceptance') =>
  apiClient.post<{ id: string; text: string; met: boolean }>(
    `/stories/${storyId}/criteria`, { text, kind }
  )

export const patchCriterion = (storyId: string, criterionId: string,
  patch: { text?: string; met?: boolean }) =>
  apiClient.patch<{ id: string; text: string; met: boolean }>(
    `/stories/${storyId}/criteria/${criterionId}`, patch
  )

export const removeCriterion = (storyId: string, criterionId: string) =>
  apiClient.delete<{ removed: string }>(`/stories/${storyId}/criteria/${criterionId}`)

export interface NewSubTask {
  title: string
  detail?: string
  assignee_id?: string
  priority?: string
  status?: string
  due_date?: string
  blocked_reason?: string
}

/** A sub-task is an ordinary batch task with the story attached to it. */
export const addSubTask = (storyId: string, input: NewSubTask) =>
  apiClient.post<{ id: string; title: string }>(`/stories/${storyId}/tasks`, input)

export const patchSubTask = (storyId: string, taskId: string, patch: {
  title?: string
  assignee_id?: string | null
  priority?: string
  status?: string
  due_date?: string | null
  progress?: number
}) => apiClient.patch<{ id: string; title: string; status: string }>(
  `/stories/${storyId}/tasks/${taskId}`, patch
)

export const commentOnSharedStory = (storyId: string, body: string) =>
  apiClient.post<{ story: string; author: string }>(
    `/stories/${storyId}/comments`, { body }
  )

/** The AI build workspace a batch's team shares. */
export interface TeamBuilder {
  exists: boolean
  project_id: string | null
  workspace_id: string | null
  title: string | null
  status: string | null
  progress: number
  updated_at?: string | null
}

/** The git repository the batch works in, if one is connected. */
export interface TeamRepo {
  connected: boolean
  url: string | null
  /** "owner/repo", for showing rather than for linking. */
  name: string | null
  state: string
  connected_at?: string | null
  /** Why there is none, when we could not make one. */
  reason?: string | null
  just_created?: boolean
}

export interface BuilderResponse {
  batch_code: string
  created?: boolean
  workspace: TeamBuilder
  repo: TeamRepo
}

export const fetchBatchBuilder = (code: string) =>
  apiClient.get<BuilderResponse>(`${base(code)}/builder`)

export const openBatchBuilder = (code: string) =>
  apiClient.post<BuilderResponse>(`${base(code)}/builder`, {})
