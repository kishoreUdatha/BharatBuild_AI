/**
 * The file store, from both portals.
 *
 * Uploads go out as multipart; downloads come back as blobs and are handed to
 * the browser here rather than as plain links, because every download route is
 * authenticated and a bare `<a href>` carries no Authorization header.
 */

import { apiClient } from '@/lib/api-client'

export interface StoredFileInfo {
  id: string
  name: string
  mime_type: string
  byte_size: number
  size_label: string
  page_count: number | null
  sha256: string
  uploaded_at: string
}

export interface UploadLimits {
  max_mb: number
  max_bytes: number
  extensions: string[]
  /** Ready for an <input type="file" accept="…"> attribute. */
  accept: string
}

export interface UploadOptions {
  categories: string[]
  limits: UploadLimits
  can_manage?: boolean
}

export interface UploadResult {
  id: string
  name: string
  category: string
  version: string
  status: string
  replaced_version: string | null
  file: StoredFileInfo
  message: string
}

export interface StudentDocumentRow {
  id: string
  name: string
  category: string
  version: string
  status: string
  is_required: boolean
  superseded: boolean
  faculty_note: string | null
  uploaded_by: string | null
  uploaded_at: string
  file: StoredFileInfo | null
  can_remove: boolean
}

export interface StudentDocuments extends UploadOptions {
  batch_code: string
  rows: StudentDocumentRow[]
  missing_required: string[]
  is_lead: boolean
}

function form(file: File, category: string, name?: string): FormData {
  const body = new FormData()
  body.append('file', file)
  body.append('category', category)
  if (name) body.append('name', name)
  return body
}

// -- faculty ---------------------------------------------------------------

// The Documents tab already carries its categories and limits in the tab
// payload, so there is nothing left for a separate options fetch to answer.
// The endpoint stays for API callers; the client helper would only be a second
// source of the same truth.

export const uploadBatchDocument = (code: string, file: File, category: string, name?: string) =>
  apiClient.post<UploadResult>(
    `/faculty/batches/${encodeURIComponent(code)}/documents`, form(file, category, name))

export const removeBatchDocument = (code: string, documentId: string) =>
  apiClient.delete<{ message: string }>(
    `/faculty/batches/${encodeURIComponent(code)}/documents/${documentId}`)

export const uploadBatchBasePaper = (code: string, file: File, title?: string) => {
  const body = new FormData()
  body.append('file', file)
  if (title) body.append('title', title)
  return apiClient.post<{ message: string; file: StoredFileInfo }>(
    `/faculty/batches/${encodeURIComponent(code)}/base-paper`, body)
}

export const downloadBatchDocument = (code: string, documentId: string, name: string) =>
  save(`/faculty/batches/${encodeURIComponent(code)}/documents/${documentId}/download`, name)

export const downloadBatchBasePaper = (code: string, name = 'base-paper.pdf') =>
  save(`/faculty/batches/${encodeURIComponent(code)}/base-paper/download`, name)

// -- student ---------------------------------------------------------------

export const fetchStudentDocuments = () =>
  apiClient.get<StudentDocuments>('/student/documents')

export const uploadStudentDocument = (file: File, category: string, name?: string) =>
  apiClient.post<UploadResult>('/student/documents', form(file, category, name))

export const removeStudentDocument = (documentId: string) =>
  apiClient.delete<{ message: string }>(`/student/documents/${documentId}`)

export const uploadStudentBasePaper = (file: File, title?: string) => {
  const body = new FormData()
  body.append('file', file)
  if (title) body.append('title', title)
  return apiClient.post<{ message: string; file: StoredFileInfo }>('/student/base-paper', body)
}

export const downloadStudentDocument = (documentId: string, name: string) =>
  save(`/student/documents/${documentId}/download`, name)

export const downloadStudentBasePaper = (name = 'base-paper.pdf') =>
  save('/student/base-paper/download', name)

// -- shared ----------------------------------------------------------------

/** Fetch an authenticated file and hand it to the browser as a download. */
async function save(path: string, filename: string): Promise<void> {
  const blob = await apiClient.get<Blob>(path, { responseType: 'blob' })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  // Revoked on the next tick: revoking synchronously can cancel the download
  // in some browsers before it has started reading.
  setTimeout(() => URL.revokeObjectURL(href), 0)
}

/**
 * Refuse locally what the server would refuse anyway.
 *
 * Not a security check - the server repeats every one of these - but it saves
 * a person waiting for a 25 MB upload to be told no at the end of it.
 */
export function checkFile(file: File, limits: UploadLimits): string | null {
  const extension = file.name.includes('.')
    ? file.name.split('.').pop()!.toLowerCase() : ''
  if (!limits.extensions.includes(extension)) {
    return `${extension ? `.${extension}` : 'That file type'} is not accepted. `
      + `Use one of: ${limits.extensions.join(', ')}.`
  }
  if (file.size > limits.max_bytes) {
    return `That file is ${(file.size / 1024 / 1024).toFixed(1)} MB. `
      + `The limit is ${limits.max_mb} MB.`
  }
  if (file.size === 0) return 'That file is empty.'
  return null
}

export function fileError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}
