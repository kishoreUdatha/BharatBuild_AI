/**
 * Stage deliverables, from both sides.
 *
 * A team hands work in against one of the eight project stages; a guide
 * accepts it or sends it back with a reason. One client type, so the review
 * screen and the submit screen cannot disagree about what a submission is.
 */

import { apiClient } from '@/lib/api-client'
import type { StoredFileInfo, UploadLimits } from '@/lib/file-api'

export interface SubmissionRow {
  id: string
  document_type: string
  title: string | null
  stage: string | null
  stage_label: string | null
  version: string
  status: 'pending' | 'verified' | 'rejected' | string
  status_label: string
  submitted_by: string | null
  submitted_at: string
  reviewed_by: string | null
  reviewed_at: string | null
  faculty_note: string | null
  superseded: boolean
  file: StoredFileInfo | null
  /** Set instead of `file` when the work lives in a repository or drive. */
  link: string | null
  can_withdraw: boolean
  can_decide: boolean
}

export interface Deliverable {
  document_type: string
  stage: string
  stage_label: string
  position: number
  status: 'not_submitted' | 'pending' | 'verified' | 'rejected' | string
  version: string | null
}

export interface SubmissionList {
  batch_code: string
  rows: SubmissionRow[]
  deliverables: Deliverable[]
  pending: number
  overall_progress: number
  limits: UploadLimits
  can_manage?: boolean
  is_lead?: boolean
}

export interface SubmitResult extends SubmissionRow {
  replaced_version: string | null
  message: string
}

export interface DecisionResult extends SubmissionRow {
  stage_completed: string | null
  overall_progress: number
  message: string
}

function body(documentType: string, file: File | null, link: string, title?: string): FormData {
  const form = new FormData()
  form.append('document_type', documentType)
  // Exactly one of the two: the server refuses both, and refuses neither.
  if (file) form.append('file', file)
  else if (link.trim()) form.append('link', link.trim())
  if (title) form.append('title', title)
  return form
}

// -- student ---------------------------------------------------------------

export const fetchMySubmissions = () =>
  apiClient.get<SubmissionList>('/student/submissions')

export const submitWork = (
  documentType: string, file: File | null, link = '', title?: string,
) => apiClient.post<SubmitResult>('/student/submissions', body(documentType, file, link, title))

export const withdrawSubmission = (id: string) =>
  apiClient.delete<{ message: string }>(`/student/submissions/${id}`)

export const downloadMySubmission = (id: string, name: string) =>
  saveBlob(`/student/submissions/${id}/download`, name)

// -- faculty / trainer -----------------------------------------------------

export const fetchBatchSubmissions = (code: string) =>
  apiClient.get<SubmissionList>(`/faculty/batches/${encodeURIComponent(code)}/submissions`)

export const decideSubmission = (code: string, id: string, decision: 'verify' | 'reject', note?: string) =>
  apiClient.post<DecisionResult>(
    `/faculty/batches/${encodeURIComponent(code)}/submissions/${id}/decide`,
    { decision, note: note || null })

export const submitForBatch = (
  code: string, documentType: string, file: File | null, link = '', title?: string,
) => apiClient.post<SubmitResult>(
  `/faculty/batches/${encodeURIComponent(code)}/submissions`,
  body(documentType, file, link, title))

export const downloadBatchSubmission = (code: string, id: string, name: string) =>
  saveBlob(`/faculty/batches/${encodeURIComponent(code)}/submissions/${id}/download`, name)

// -- shared ----------------------------------------------------------------

async function saveBlob(path: string, filename: string): Promise<void> {
  const blob = await apiClient.get<Blob>(path, { responseType: 'blob' })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(href), 0)
}

export function submissionError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}
