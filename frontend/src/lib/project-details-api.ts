/**
 * Project details - the same form from both sides.
 *
 * The student portal and the faculty portal post to different routes but the
 * payload, the validation and the eight completeness checks are one thing on
 * the server. Keeping one client type here means a field added to the form
 * cannot reach one portal and not the other.
 */

import { apiClient } from '@/lib/api-client'

export interface ObjectiveInput {
  text: string
  status: 'complete' | 'in_progress' | 'pending' | string
}

export interface MethodologyInput {
  title: string
  description: string | null
}

export interface TechnologyInput {
  layer: string
  name: string
}

export interface ProjectCheck {
  key: string
  label: string
  passed: boolean
  hint: string
}

export interface ProjectDetailsForm {
  batch_code: string
  status: string
  locked: boolean
  locked_reason: string | null
  title: string | null
  domain: string | null
  project_type: string | null
  keywords: string[]
  problem_statement: string | null
  abstract: string | null
  objectives: ObjectiveInput[]
  methodology: MethodologyInput[]
  outcomes: string[]
  in_scope: string[]
  out_of_scope: string[]
  deliverables: string[]
  technologies: TechnologyInput[]
  start_date: string | null
  target_completion: string | null
  weekly_effort_hours: number | null
  checklist: ProjectCheck[]
  checks_passed: number
  checks_total: number
  /** Whether the registration is complete enough to go to a guide. */
  complete: boolean
  /** Whether THIS reader may press submit. Never true for faculty. */
  can_submit: boolean
  submit_blocked_reason?: string | null
  can_manage?: boolean
  is_lead?: boolean
  changed_fields?: string[]
  options: {
    project_types: string[]
    layers: string[]
    objective_statuses: string[]
    limits: Record<string, number>
  }
}

/** What a save sends. Omitted keys are left untouched by the server. */
export type ProjectDetailsPayload = Partial<{
  title: string | null
  domain: string | null
  project_type: string
  keywords: string[]
  problem_statement: string | null
  abstract: string | null
  objectives: ObjectiveInput[]
  methodology: MethodologyInput[]
  outcomes: string[]
  in_scope: string[]
  out_of_scope: string[]
  deliverables: string[]
  technologies: TechnologyInput[]
  start_date: string | null
  target_completion: string | null
  weekly_effort_hours: number | null
}>

export interface SubmitResult {
  status: string
  submitted_at: string
  review_due_at: string
  cycle: number
  resubmission: boolean
  message: string
}

// -- student side ----------------------------------------------------------

export const fetchStudentProject = () =>
  apiClient.get<ProjectDetailsForm>('/student/project')

export const saveStudentProject = (payload: ProjectDetailsPayload) =>
  apiClient.put<ProjectDetailsForm>('/student/project', payload)

export const submitStudentProject = (note?: string) =>
  apiClient.post<SubmitResult>('/student/project/submit', { note: note || null })

// -- faculty side ----------------------------------------------------------

export const fetchFacultyProjectForm = (code: string) =>
  apiClient.get<ProjectDetailsForm>(
    `/faculty/batches/${encodeURIComponent(code)}/project/form`)

export const saveFacultyProject = (code: string, payload: ProjectDetailsPayload) =>
  apiClient.put<ProjectDetailsForm>(
    `/faculty/batches/${encodeURIComponent(code)}/project`, payload)

/** Server refusals arrive as `detail`; anything else gets the fallback. */
export function projectError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}
