/**
 * Faculty dashboard API client.
 *
 * Mirrors `backend/app/schemas/faculty.py`. The backend returns one aggregate
 * for the whole screen, so the dashboard costs a single request.
 */

import { apiClient } from '@/lib/api-client'

export interface ApiKpi {
  id: string
  value: string
  label: string
}

export interface ApiStage {
  key: string
  label: string
  percent: number
}

export interface ApiStagePoint {
  stage: string
  values: Record<string, number>
}

export interface ApiAttentionItem {
  id: string
  label: string
  count: number
}

export interface ApiUpcomingReview {
  id: string
  date: string
  time: string
  batch_code: string
  review_type: string
  scheduled_at: string
}

export interface ApiSectionRow {
  section: string
  students: number
  batches: number | null
  registration: number | null
  attendance: number | null
  progress: number | null
  pending_reviews: number
  status: string
}

export interface ApiProjectRow {
  batch_id: string
  batch_code: string
  title: string
  issue: string
  progress: number
  risk: string
}

export interface FacultyDashboard {
  faculty: {
    name: string
    department: string | null
    sections: string | null
    academic_year: string
  }
  filters_applied: Record<string, string | null>
  kpis: ApiKpi[]
  stages: ApiStage[]
  progress_series: ApiStagePoint[]
  series_names: string[]
  attention_items: ApiAttentionItem[]
  upcoming_reviews: ApiUpcomingReview[]
  section_rows: ApiSectionRow[]
  project_rows: ApiProjectRow[]
  attendance_today: { present: number; absent: number; late: number }
  recent_submissions: { count: number; caption: string }
  faculty_workload: { assigned_batches: number; reviews_this_week: number }
  base_paper_status: { rows: { count: number; label: string }[] }
  ai_insight: string | null
}

export interface FacultyFilterOptions {
  departments: string[]
  years: string[]
  semesters: string[]
  sections: string[]
  project_types: string[]
  guides: { id: string; name: string }[]
  academic_years: string[]
}

export interface DashboardQuery {
  academic_year?: string
  department?: string
  section?: string
  year?: string
  semester?: string
  project_type?: string
  guide_id?: string
}

/** Drop empty values so the backend treats them as "no filter". */
function toParams(query: DashboardQuery): Record<string, string> {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => value !== undefined && value !== null && value !== '')
  ) as Record<string, string>
}

export async function fetchFacultyDashboard(query: DashboardQuery = {}): Promise<FacultyDashboard> {
  return apiClient.get<FacultyDashboard>('/faculty/dashboard', { params: toParams(query) })
}

export async function fetchFacultyFilters(academicYear?: string): Promise<FacultyFilterOptions> {
  return apiClient.get<FacultyFilterOptions>('/faculty/filters', {
    params: academicYear ? { academic_year: academicYear } : {},
  })
}

// ---------------------------------------------------------- drill-down lists

export interface BatchRow {
  id: string
  batch_code: string
  title: string | null
  department: string
  section: string | null
  project_type: string
  progress: number
  /** Where this batch should be by today, from its own start and target dates.
   *  Null when the batch has no usable schedule - then it is never called behind. */
  expected_progress: number | null
  schedule_state: 'ahead' | 'on_track' | 'behind' | 'unknown'
  schedule_note: string
  days_remaining: number | null
  guide_name: string | null
  member_count: number
  inactive_members: number
  overdue_reviews: number
  base_paper_status: string
  needs_attention: boolean
}

export interface ReviewRow {
  id: string
  batch_code: string
  review_type: string
  /** Naive UTC. Never parse this in the browser - it has no zone, so it is
   *  read as local and lands 5.5 hours out. Use the labels below. */
  scheduled_at: string
  /** Server-formatted in the institution's timezone. */
  scheduled_label?: string
  scheduled_day?: string
  scheduled_time?: string
  status: string
}

export interface StudentRow {
  id: string
  student_id: string
  full_name: string | null
  email: string
  roll_number: string | null
  department: string
  section: string | null
  year: string
  semester: string | null
  is_registered: boolean
}

export interface AttendanceRow {
  student_id: string
  full_name: string | null
  roll_number: string | null
  department: string
  section: string | null
  attendance_rate: number | null
  below_floor: boolean
}

export interface GuideRow {
  id: string
  full_name: string | null
  email: string
  department: string | null
  batches: number
  avg_progress: number
}

/**
 * Turn any API error into a displayable string.
 *
 * FastAPI returns a *list of objects* for 422 validation errors, and rendering
 * that straight into JSX crashes React with "Objects are not valid as a React
 * child". Every catch block goes through here.
 */
export function errorMessage(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d: any) => {
        const field = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : undefined
        return field ? `${field}: ${d?.msg ?? 'invalid'}` : d?.msg
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  if (typeof err?.message === 'string' && err.message) return err.message
  return fallback
}

type Params = Record<string, string | number | boolean | undefined>

const clean = (params: Params) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''))

export const fetchBatches = (params: Params = {}) =>
  apiClient.get<{ items: BatchRow[]; count: number }>('/faculty/batches', { params: clean(params) })

export const fetchReviews = (params: Params = {}) =>
  apiClient.get<{ items: ReviewRow[] }>('/faculty/reviews', { params: clean(params) })

export const fetchStudents = (params: Params = {}) =>
  apiClient.get<{ items: StudentRow[] }>('/faculty/students', { params: clean(params) })

export const fetchAttendance = (params: Params = {}) =>
  apiClient.get<{
    items: AttendanceRow[]
    count: number
    today: { present: number; absent: number; late: number }
    floor: number
  }>('/faculty/attendance', { params: clean(params) })

export const fetchGuides = (params: Params = {}) =>
  apiClient.get<{ items: GuideRow[] }>('/faculty/guides', { params: clean(params) })

// -------------------------------------------------- Student & Batch Registrations

export interface RegistrationRow {
  id: string
  batch_code: string
  title: string | null
  section: string | null
  members: number
  team_size: number
  batch_leader: string | null
  base_paper: string
  base_paper_status: string
  guide: string | null
  guide_id: string | null
  status: string
  status_key: string
  last_updated: string
}

export interface RegistrationsView {
  kpis: { id: string; value: string; label: string }[]
  attention_items: { id: string; label: string; count: number }[]
  progress: { label: string; done: number; total: number }[]
  rows: RegistrationRow[]
  page: number
  pages: number
  per_page: number
  total: number
  showing_from: number
  showing_to: number
  statuses: { key: string; label: string }[]
}

export interface RegistrationQuery extends Params {
  department?: string
  section?: string
  year?: string
  semester?: string
  project_type?: string
  reg_status?: string
  search?: string
  page?: number
  per_page?: number
}

export const fetchRegistrations = (params: RegistrationQuery = {}) =>
  apiClient.get<RegistrationsView>('/faculty/registrations', { params: clean(params) })

export const assignGuide = (batchIds: string[], guideId: string) =>
  apiClient.post<{ updated: number }>('/faculty/registrations/assign-guide', {
    batch_ids: batchIds,
    guide_id: guideId,
  })

export const approveRegistrations = (batchIds: string[]) =>
  apiClient.post<{ approved: string[]; skipped: { batch_code: string; reason: string }[] }>(
    '/faculty/registrations/approve',
    { batch_ids: batchIds }
  )

/** Streams the filtered set as CSV. Goes through the client so the JWT is sent. */
export async function exportRegistrations(params: RegistrationQuery = {}): Promise<void> {
  const blob = await apiClient.get<Blob>('/faculty/registrations/export', {
    params: clean(params),
    responseType: 'blob',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'registrations.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

// ------------------------------------------------ Student Registrations tab

export interface StudentRegistrationRow {
  id: string
  student_id: string
  full_name: string | null
  roll_number: string | null
  department: string
  section: string | null
  mobile: string | null
  email: string
  batch_code: string | null
  role: string | null
  profile_status: string
  profile_status_key: string
}

export interface StudentRegistrationsView {
  kpis: { id: string; value: string; label: string }[]
  attention_items: { id: string; label: string; count: number }[]
  completion: { label: string; done: number; total: number }[]
  rows: StudentRegistrationRow[]
  page: number
  pages: number
  per_page: number
  total: number
  showing_from: number
  showing_to: number
  profile_statuses: { key: string; label: string }[]
}

export interface StudentQuery extends Params {
  department?: string
  section?: string
  year?: string
  semester?: string
  batch_status?: string
  profile_status?: string
  search?: string
  page?: number
  per_page?: number
}

export const fetchStudentRegistrations = (params: StudentQuery = {}) =>
  apiClient.get<StudentRegistrationsView>('/faculty/registrations/students', { params: clean(params) })

export const verifyStudents = (enrollmentIds: string[]) =>
  apiClient.post<{ verified: string[]; skipped: { roll_number: string; reason: string }[] }>(
    '/faculty/registrations/students/verify',
    { enrollment_ids: enrollmentIds }
  )

export const assignStudentsToBatch = (enrollmentIds: string[], batchId: string) =>
  apiClient.post<{ added: number; batch_code: string; skipped: { reason: string }[] }>(
    '/faculty/registrations/students/assign-batch',
    { enrollment_ids: enrollmentIds, batch_id: batchId }
  )

export async function exportStudentRegistrations(params: StudentQuery = {}): Promise<void> {
  const blob = await apiClient.get<Blob>('/faculty/registrations/students/export', {
    params: clean(params),
    responseType: 'blob',
  })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'students.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

// ------------------------------ Incomplete Registrations + Approval Queue

export interface IncompleteRow {
  id: string
  kind: 'student' | 'batch'
  label: string
  type: string
  department: string
  section: string | null
  batch: string
  missing: string
  completion: number
  issues: string[]
  priority: string
  last_reminder: string | null
  action: string
}

export interface IncompleteView {
  kpis: { id: string; value: string; label: string }[]
  breakdown: { id: string; label: string; count: number }[]
  resolution: {
    resolved_this_week: number
    pending: number
    overdue: number
    average_days: number
    percent_resolved: number
  }
  recommendations: string[]
  rows: IncompleteRow[]
  page: number
  pages: number
  total: number
  showing_from: number
  showing_to: number
  issue_types: { key: string; label: string }[]
  priorities: string[]
}

export interface QueueRow {
  id: string
  batch_code: string
  title: string | null
  section: string | null
  team: string
  team_complete: boolean
  project_details: string
  base_paper: string
  guide: string | null
  reviewer: string | null
  submitted_at: string | null
  sla: string
  overdue: boolean
  status_key: string
  checks_passed: number
  checks_total: number
  action: string
}

export interface QueueDetail {
  id: string
  batch_code: string
  title: string | null
  abstract: string | null
  base_paper_title: string | null
  base_paper_url: string | null
  base_paper_status: string
  guide: string | null
  submitted_at: string | null
  faculty_note: string | null
  status_key: string
  members: { name: string | null; roll_number: string | null; is_lead: boolean }[]
  checklist: { key: string; label: string; passed: boolean; detail: string }[]
  checks_passed: number
  checks_total: number
  can_approve: boolean
}

export interface QueueView {
  kpis: { id: string; value: string; label: string }[]
  rows: QueueRow[]
  page: number
  pages: number
  total: number
  showing_from: number
  showing_to: number
  summary: {
    by_section: { section: string; pending: number }[]
    oldest_days: number
    average_review_hours: number
  }
  selected: QueueDetail | null
  tabs: { key: string; label: string }[]
}

export const fetchIncomplete = (params: Params = {}) =>
  apiClient.get<IncompleteView>('/faculty/registrations/incomplete', { params: clean(params) })

export const fetchQueue = (params: Params = {}) =>
  apiClient.get<QueueView>('/faculty/registrations/queue', { params: clean(params) })

export const fetchQueueDetail = (batchId: string) =>
  apiClient.get<QueueDetail>(`/faculty/registrations/queue/${batchId}`)

export const decideRegistrations = (
  batchIds: string[],
  decision: 'approve' | 'reject' | 'request_changes',
  note?: string
) =>
  apiClient.post<{ applied: string[]; skipped: { batch_code: string; reason: string }[] }>(
    '/faculty/registrations/queue/decide',
    { batch_ids: batchIds, decision, note }
  )

export const assignReviewer = (batchIds: string[], reviewerId: string) =>
  apiClient.post<{ updated: number }>('/faculty/registrations/queue/assign-reviewer', {
    batch_ids: batchIds,
    reviewer_id: reviewerId,
  })

export const recordReminders = (recordIds: string[], kind: 'student' | 'batch') =>
  apiClient.post<{ stamped: number; emails_sent: number; detail: string }>(
    '/faculty/registrations/reminders',
    { record_ids: recordIds, kind }
  )

// --------------------------------------------------------- Import History

export interface ImportRow {
  id: string
  import_code: string
  file_name: string
  file_size: number
  import_type: string
  import_type_key: string
  department: string | null
  rows_total: number
  rows_imported: number
  rows_failed: number
  rows_duplicate: number
  status: string
  status_key: string
  imported_by: string | null
  started_at: string
  is_archived: boolean
  action: string
}

export interface ImportDetail extends ImportRow {
  duration_seconds: number
  completed_at: string | null
  percent_processed: number
  timeline: { step: string; actor: string | null; note: string | null; occurred_at: string; is_warning: boolean }[]
  issues: { row: number; field: string | null; message: string; value: string | null; severity: string }[]
  issue_count: number
}

export interface ImportsView {
  kpis: { id: string; value: string; label: string }[]
  rows: ImportRow[]
  page: number
  pages: number
  total: number
  showing_from: number
  showing_to: number
  selected: ImportDetail | null
  import_types: { key: string; label: string }[]
  statuses: { key: string; label: string }[]
  importers: [string, string][]
}

export const fetchImports = (params: Params = {}) =>
  apiClient.get<ImportsView>('/faculty/imports', { params: clean(params) })

export const fetchImportDetail = (runId: string) =>
  apiClient.get<ImportDetail>(`/faculty/imports/${runId}`)

export const archiveImports = (runIds: string[]) =>
  apiClient.post<{ archived: number }>('/faculty/imports/archive', { run_ids: runIds })

export async function uploadImport(
  file: File,
  importType: string,
  opts: { academicYear?: string; department?: string } = {}
): Promise<ImportDetail> {
  const form = new FormData()
  form.append('file', file)
  form.append('import_type', importType)
  if (opts.academicYear) form.append('academic_year', opts.academicYear)
  if (opts.department) form.append('department', opts.department)
  // The axios instance defaults to application/json; unset it so axios can set
  // multipart/form-data with the boundary, otherwise the file never arrives.
  return apiClient.post<ImportDetail>('/faculty/imports', form, {
    headers: { 'Content-Type': undefined },
  })
}

/** Streams a file through the client so the JWT is sent, then saves it. */
async function download(url: string, fallbackName: string, params?: Params) {
  const blob = await apiClient.get<Blob>(url, { params: params ? clean(params) : undefined, responseType: 'blob' })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = fallbackName
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

export const downloadImportTemplate = (importType: string) =>
  download('/faculty/imports/template', `${importType}-template.csv`, { import_type: importType })

export const downloadImportOriginal = (runId: string, fileName: string) =>
  download(`/faculty/imports/${runId}/original`, fileName)

export const downloadImportErrors = (runId: string, code: string) =>
  download(`/faculty/imports/${runId}/errors`, `${code}-errors.csv`)

// ---------------------------------------------------------------- tracking

export interface TrackingKpi { id: string; value: string | number; label: string; tone?: string }

export interface TrackingRow {
  id: string
  batch_code: string
  title: string | null
  section: string | null
  guide_name: string | null
  members: { id: string; is_active: boolean }[]
  member_count: number
  active_members: number
  current_phase: string
  progress: number
  expected_progress: number | null
  schedule_state: 'ahead' | 'on_track' | 'behind' | 'unknown'
  milestones_done: number
  milestones_total: number
  tasks_done: number
  tasks_total: number
  deliverables_done: number
  deliverables_total: number
  last_activity: string | null
  next_due: { label: string; date: string; display: string } | null
  health: string
  reasons: string[]
  blocked_tasks: number
  overdue_tasks: number
}

export interface TrackingOverview {
  kpis: TrackingKpi[]
  rows: TrackingRow[]
  total: number
  page: number
  per_page: number
  pages: number
  academic_year: string
}

export interface TrackingDetail {
  batch_code: string
  title: string | null
  progress: number
  current_phase: string
  guide_name: string | null
  health: string
  reasons: string[]
  team: { id: string; name: string; is_lead: boolean; is_active: boolean }[]
  integrations: { kind: string; state: string; detail: string | null; url: string | null }[]
  workstreams: { stage: string; label: string; percent: number }[]
  milestones: {
    stage: string; label: string; planned: string | null
    actual: string | null; percent: number; status: string
  }[]
  tasks: {
    id: string; title: string; assignee: string | null; priority: string
    status: string; due_display: string | null; overdue: boolean
    blocked_reason: string | null
  }[]
  deliverables: { id: string; name: string; progress: number; status: string; evidence_url: string | null }[]
  activity: { code: string; summary: string; module: string; actor: string | null; at: string }[]
}

export interface TrackingAlerts {
  alerts: { id: string; count: number; label: string; tone: string }[]
  upcoming: { batch_code: string; health: string; label: string; date: string; display: string }[]
}

export interface TrackingQuery {
  academic_year?: string
  department?: string
  section?: string
  year?: string
  semester?: string
  guide_id?: string
  phase?: string
  health?: string
  search?: string
  mine?: boolean
  page?: number
  per_page?: number
}

export const fetchTracking = (params: TrackingQuery = {}) =>
  apiClient.get<TrackingOverview>('/faculty/tracking', { params: clean(params as Params) })

export const fetchTrackingDetail = (batchCode: string) =>
  apiClient.get<TrackingDetail>(`/faculty/tracking/${encodeURIComponent(batchCode)}`)

export const fetchTrackingAlerts = (academic_year?: string) =>
  apiClient.get<TrackingAlerts>('/faculty/tracking/alerts',
    { params: clean({ academic_year } as Params) })

export const addTrackingTask = (batchCode: string, body: Record<string, unknown>) =>
  apiClient.post(`/faculty/tracking/${encodeURIComponent(batchCode)}/tasks`, body)

export const updateTrackingTask = (taskId: string, body: Record<string, unknown>) =>
  apiClient.patch(`/faculty/tracking/tasks/${taskId}`, body)

export const updateDeliverable = (deliverableId: string, body: Record<string, unknown>) =>
  apiClient.patch(`/faculty/tracking/deliverables/${deliverableId}`, body)

// ------------------------------------------------- cohort-wide tracker views

export interface MilestoneRow {
  batch_code: string; title: string | null; guide_name: string | null
  label: string; planned: string | null; percent: number; status: string
}
export interface TaskRow {
  id: string; batch_code: string; title: string | null; guide_name: string | null
  task_title?: string; assignee: string | null; priority: string; status: string
  due_display: string | null; overdue: boolean; blocked_reason: string | null
}
export interface DeliverableRow {
  id: string; batch_code: string; title: string | null
  name: string; progress: number; status: string; evidence_url: string | null
}
export interface ActivityRow {
  code: string; batch_code: string; summary: string
  module: string; actor: string | null; at: string
}
export interface TrackerInsight {
  headline: string; detail?: string
  codes: string[]; causes: string[]; critical_count?: number
}

type ViewParams = Omit<TrackingQuery, 'phase' | 'health' | 'search' | 'mine' | 'page' | 'per_page'>

export const fetchTrackerMilestones = (params: ViewParams = {}) =>
  apiClient.get<{ items: MilestoneRow[]; count: number }>(
    '/faculty/tracking-views/milestones', { params: clean(params as Params) })

export const fetchTrackerTasks = (params: ViewParams = {}) =>
  apiClient.get<{ items: TaskRow[]; count: number }>(
    '/faculty/tracking-views/tasks', { params: clean(params as Params) })

export const fetchTrackerDeliverables = (params: ViewParams = {}) =>
  apiClient.get<{ items: DeliverableRow[]; count: number }>(
    '/faculty/tracking-views/deliverables', { params: clean(params as Params) })

export const fetchTrackerActivity = (params: ViewParams = {}) =>
  apiClient.get<{ items: ActivityRow[]; count: number }>(
    '/faculty/tracking-views/activity', { params: clean(params as Params) })

export const fetchTrackerInsight = () =>
  apiClient.get<TrackerInsight>('/faculty/tracking-views/insight')

export const requestProgressUpdate = (batch_codes: string[], note = '') =>
  apiClient.post<{ asked: string[]; skipped: string[]; message: string }>(
    '/faculty/tracking/request-update', { batch_codes, note })

export const bulkMilestoneDate = (batch_codes: string[], stage: string, planned_date: string) =>
  apiClient.post<{ updated: string[]; skipped: string[]; message: string }>(
    '/faculty/tracking/bulk-milestone', { batch_codes, stage, planned_date })

/**
 * The tracker as a spreadsheet, honouring whatever filters are applied.
 *
 * Streamed through the client rather than linked directly, so the JWT goes
 * with it - a plain href would arrive unauthenticated and download a 403.
 */
export const exportTracker = (params: TrackingQuery = {}) =>
  download('/faculty/tracking-views/export.csv',
           `project-tracker-${params.academic_year ?? 'current'}.csv`,
           clean(params as Params))


// -------------------------------------------------------- tasks & blockers

export interface TaskCard {
  id: string
  title: string
  batch_code: string
  project_title: string | null
  assignee: string | null
  assignee_id: string | null
  priority: string
  status: string
  progress: number
  stage: string | null
  due_date: string | null
  due_display: string | null
  created_display: string | null
  age_days: number | null
  overdue: boolean
  blocked_reason: string | null
  comments: number
  attachments: number
  dependencies: number
  waiting_on: string | null
}

export interface BoardColumn {
  status: string
  label: string
  count: number
  cards: TaskCard[]
}

export interface BatchCatalogueEntry {
  code: string
  department: string | null
  section: string | null
  team: string | null
  team_label: string
}

export interface TaskBoardOptions {
  catalogue: BatchCatalogueEntry[]
  departments: string[]
  sections: string[]
  batches: string[]
  assignees: { id: string; name: string; is_active: boolean; has_tasks: boolean }[]
  priorities: string[]
  statuses: string[]
  due: string[]
}

export interface TaskBoardData {
  kpis: { id: string; value: string | number; label: string; tone?: string }[]
  options: TaskBoardOptions
  columns: BoardColumn[]
  rows: TaskCard[]
  total: number
  academic_year: string
}

export interface BlockerRow {
  id: string
  title: string
  batch_code: string
  category: string
  category_label: string
  severity: string
  status: string
  root_cause: string | null
  impact: string | null
  reported_by: string | null
  reported_at: string | null
  owner: string | null
  owner_id: string | null
  target_resolution: string | null
  resolved_at: string | null
  resolution_note: string | null
  task_title: string | null
  age_days: number | null
}

export interface BlockerData {
  queue: BlockerRow[]
  resolved_count: number
  analysis: { label: string; count: number }[]
  sla: {
    bands: { label: string; count: number; percent: number }[]
    average_days: number | null
    resolved: number
  }
}

export interface WorkloadData {
  students: {
    id: string; name: string; tasks: number
    overdue: number; blocked: number; done: number; load_percent: number
  }[]
  normal_load: number
  overdue_by_batch: { batch_code: string; count: number }[]
}

export interface TaskInsight {
  headline: string
  detail: string
  critical: number
  downstream: number
  milestones: number
}

export interface TaskBoardQuery {
  academic_year?: string
  department?: string
  section?: string
  year?: string
  semester?: string
  batch_code?: string
  guide_id?: string
  assignee_id?: string
  priority?: string
  status?: string
  due?: string
  unassigned?: boolean
  search?: string
}

export const fetchTaskBoard = (params: TaskBoardQuery = {}) =>
  apiClient.get<TaskBoardData>('/faculty/tasks/board', { params: clean(params as Params) })

export const fetchBlockers = (params: TaskBoardQuery = {}) =>
  apiClient.get<BlockerData>('/faculty/tasks/blockers', { params: clean(params as Params) })

export const fetchTaskWorkload = (params: TaskBoardQuery = {}) =>
  apiClient.get<WorkloadData>('/faculty/tasks/workload', { params: clean(params as Params) })

export const fetchTaskInsight = () =>
  apiClient.get<TaskInsight>('/faculty/tasks/insight')

export const reportBlocker = (batchCode: string, body: Record<string, unknown>) =>
  apiClient.post<{ id: string; message: string }>(
    `/faculty/tasks/${encodeURIComponent(batchCode)}/blockers`, body)

export const assignBlocker = (blockerId: string, owner_id: string, target_resolution?: string) =>
  apiClient.post<{ message: string }>(
    `/faculty/tasks/blockers/${blockerId}/assign`, { owner_id, target_resolution })

export const escalateBlocker = (blockerId: string, note = '') =>
  apiClient.post<{ message: string }>(`/faculty/tasks/blockers/${blockerId}/escalate`, { note })

export const resolveBlocker = (blockerId: string, note: string) =>
  apiClient.post<{ message: string }>(`/faculty/tasks/blockers/${blockerId}/resolve`, { note })

export const bulkEditTasks = (task_ids: string[], changes: Record<string, unknown>) =>
  apiClient.post<{ changed: number; skipped: number; message: string }>(
    '/faculty/tasks/bulk-edit', { task_ids, ...changes })

export const commentOnTask = (taskId: string, body: string) =>
  apiClient.post<{ message: string }>(`/faculty/tasks/${taskId}/comments`, { body })

/** The register as a spreadsheet, honouring the filters in force. */
export const exportTasks = (params: TaskBoardQuery = {}) =>
  download('/faculty/tracking-views/export.csv',
           `tasks-${params.academic_year ?? 'current'}.csv`,
           clean(params as Params))


// ------------------------------------------------------------- milestones

export interface MilestoneItem {
  id: string
  name: string
  batch_code: string
  project_title: string | null
  guide_name: string | null
  stage: string | null
  priority: string
  status: string
  health: string
  approval: string
  owner: string | null
  owner_id: string | null
  reviewer: string | null
  planned_start: string | null
  planned_date: string | null
  planned_display: string | null
  forecast_date: string | null
  forecast_display: string | null
  slipping: boolean
  progress: number
  evidence_verified: number
  evidence_total: number
  dependencies: number
  // Which milestone this one is blocked behind, already formatted for
  // display by the server; null when nothing is holding it up.
  waiting_on: string | null
}

export interface MilestoneBoardData {
  kpis: { id: string; value: string | number; label: string; tone?: string; delta?: number | null; lower_is_better?: boolean; suffix?: string }[]
  options: {
    batches: string[]
    milestones: string[]
    statuses: string[]
    approvals: string[]
    priorities: string[]
  }
  tracker: { batch_code: string; project_title: string | null; milestones: MilestoneItem[] }[]
  rows: MilestoneItem[]
  total: number
  page: number
  per_page: number
  pages: number
  window: { start: string; end: string; today: string }
  academic_year: string
}

export interface MilestoneQueueData {
  approvals: MilestoneItem[]
  approval_total: number
  upcoming: MilestoneItem[]
  health: { label: string; count: number; percent: number }[]
  alerts: { blocker: string; waiting: string; batch_code: string; message: string }[]
  alert_total: number
}

export interface MilestoneDetail extends MilestoneItem {
  detail: string | null
  review_note: string | null
  checklist: { id: string; label: string; done: boolean }[]
  evidence: { id: string; label: string; status: string; url: string | null }[]
  depends_on: { id: string; name: string; status: string }[]
  activity: { code: string; summary: string; actor: string | null; at: string }[]
}

export interface MilestoneInsight {
  headline: string
  detail: string
  at_risk: number
  codes: string[]
}

export interface MilestoneQuery {
  academic_year?: string
  department?: string
  section?: string
  year?: string
  semester?: string
  batch_code?: string
  guide_id?: string
  milestone?: string
  status?: string
  approval?: string
  due_from?: string
  due_to?: string
  page?: number
  per_page?: number
}

export const fetchMilestoneBoard = (params: MilestoneQuery = {}) =>
  apiClient.get<MilestoneBoardData>('/faculty/milestones/board',
    { params: clean(params as Params) })

export const fetchMilestoneQueue = (params: MilestoneQuery = {}) =>
  apiClient.get<MilestoneQueueData>('/faculty/milestones/queue',
    { params: clean(params as Params) })

export const fetchMilestoneInsight = () =>
  apiClient.get<MilestoneInsight>('/faculty/milestones/insight')

export interface RecoveryStep extends MilestoneItem {
  blocks: number
  overdue_days: number
  why: string[]
}

export const fetchRecoveryPlan = (params: MilestoneQuery = {}) =>
  apiClient.get<{ steps: RecoveryStep[]; total: number; headline: string }>(
    '/faculty/milestones/recovery-plan', { params: clean(params as Params) })

export const fetchMilestoneDetail = (id: string) =>
  apiClient.get<MilestoneDetail>(`/faculty/milestones/${id}`)

export const addMilestone = (batchCode: string, body: Record<string, unknown>) =>
  apiClient.post<{ id: string; message: string }>(
    `/faculty/milestones/${encodeURIComponent(batchCode)}`, body)

export const bulkMilestones = (
  milestone_ids: string[], action: string, value?: string,
) =>
  apiClient.post<{ done: number; skipped: number; message: string }>(
    '/faculty/milestones/bulk', { milestone_ids, action, value })

export const approveMilestone = (id: string, note = '') =>
  apiClient.post<{ message: string }>(`/faculty/milestones/${id}/approve`, { note })

export const requestMilestoneChanges = (id: string, note: string) =>
  apiClient.post<{ message: string }>(`/faculty/milestones/${id}/request-changes`, { note })

export const submitMilestone = (id: string) =>
  apiClient.post<{ message: string }>(`/faculty/milestones/${id}/submit`, {})

export const requestMilestoneEvidence = (milestone_ids: string[], label = 'Evidence') =>
  apiClient.post<{ asked: number; skipped: number; message: string }>(
    '/faculty/milestones/request-evidence', { milestone_ids, label })

export const verifyMilestoneEvidence = (evidenceId: string, accept = true) =>
  apiClient.post<{ message: string }>(
    `/faculty/milestones/evidence/${evidenceId}/verify`, { accept })

export const toggleMilestoneChecklist = (itemId: string, done: boolean) =>
  apiClient.patch<{ message: string; progress: number }>(
    `/faculty/milestones/checklist/${itemId}`, { done })

/** The milestone table as a spreadsheet, honouring the filters in force. */
export const exportMilestones = (params: MilestoneQuery = {}) =>
  download('/faculty/tracking-views/export.csv',
           `milestones-${params.academic_year ?? 'current'}.csv`,
           clean(params as Params))
