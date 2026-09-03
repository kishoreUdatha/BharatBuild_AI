/**
 * Review scheduling.
 *
 * Dates and times go out as local wall clock — "2026-09-02", "10:00" — and the
 * server converts to UTC for storage. `scheduled_label` comes back already
 * written in the institution's timezone, so nothing here re-derives it.
 */

import { apiClient } from '@/lib/api-client'

export interface ReviewRow {
  id: string
  batch_code: string
  review_type: string
  scheduled_at: string
  /** Already formatted in the institution's timezone. */
  scheduled_label: string
  slot_minutes: number
  status: string
  status_label: string
  reviewer: string | null
  reviewer_id: string | null
  score: number | null
  remarks: string | null
  completed_at: string | null
  overdue: boolean
  /** Batch codes this reviewer is double-booked against, if any. */
  clashes_with?: string[]
}

export interface ReviewOptions {
  review_types: string[]
  reviewers: { id: string; name: string }[]
  defaults: { slot_minutes: number; start_time: string }
  limits: {
    max_batches: number
    min_slot_minutes: number
    max_slot_minutes: number
    max_days_ahead: number
  }
  academic_year: string
}

export interface Agenda {
  items: ReviewRow[]
  count: number
  overdue: number
  unassigned: number
  clashing: number
  academic_year: string
}

export interface CohortPreview {
  batches: {
    batch_code: string
    title: string | null
    section: string | null
    already_scheduled: boolean
  }[]
  total: number
  to_book: number
  review_type: string
}

export interface RoundResult {
  created: ReviewRow[]
  count: number
  skipped: string[]
  review_type: string
  reviewer: string | null
  slot_minutes: number
  starts_at: string
  ends_at: string
  message: string
}

export const fetchReviewOptions = () =>
  apiClient.get<ReviewOptions>('/faculty/reviews/options')

export const fetchAgenda = (params: {
  date?: string; department?: string; section?: string
  reviewer_id?: string; include_past?: boolean; limit?: number
} = {}) => apiClient.get<Agenda>('/faculty/reviews/schedule', { params: clean(params) })

export const fetchCohortPreview = (params: {
  department: string; review_type: string; year?: string; section?: string
}) => apiClient.get<CohortPreview>('/faculty/reviews/cohort-preview', { params: clean(params) })

export const scheduleRound = (body: {
  department: string; section?: string; year?: string
  review_type: string; date: string; start_time: string
  slot_minutes?: number; reviewer_id?: string; batch_codes?: string[]
}) => apiClient.post<RoundResult>('/faculty/reviews/round', clean(body))

export const fetchBatchReviews = (code: string) =>
  apiClient.get<{
    batch_code: string; items: ReviewRow[]
    can_manage: boolean; review_types: string[]
  }>(`/faculty/batches/${encodeURIComponent(code)}/reviews`)

export const scheduleBatchReview = (code: string, body: {
  review_type: string; date: string; time: string
  reviewer_id?: string; slot_minutes?: number
}) => apiClient.post<ReviewRow & { message: string }>(
  `/faculty/batches/${encodeURIComponent(code)}/reviews`, clean(body))

export const completeReview = (code: string, id: string, body: {
  score?: number; remarks?: string
}) => apiClient.post(
  `/faculty/batches/${encodeURIComponent(code)}/reviews/${id}/complete`, clean(body))

export const rescheduleReview = (code: string, id: string, date: string, time: string) =>
  apiClient.post(
    `/faculty/batches/${encodeURIComponent(code)}/reviews/${id}/reschedule`, { date, time })

export const cancelReview = (code: string, id: string, reason: string) =>
  apiClient.post(
    `/faculty/batches/${encodeURIComponent(code)}/reviews/${id}/cancel`, { reason })

function clean<T extends Record<string, any>>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ) as Partial<T>
}

export function reviewError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}

/** Tomorrow, as the YYYY-MM-DD a date input wants — a sane default to book. */
export function tomorrow(): string {
  const d = new Date()
  d.setDate(d.getDate() + 1)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}
