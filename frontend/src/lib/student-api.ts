/**
 * Student Portal API - the student's own registration journey.
 */

import { apiClient } from '@/lib/api-client'

export interface RegistrationStep {
  key: string
  label: string
  position: number
  state: 'done' | 'current' | 'pending'
  /** Set when a step cannot progress for a reason outside the student's control. */
  blocked_reason?: string | null
}

export interface BatchSummary {
  id: string
  batch_code: string
  join_code: string | null
  display_name: string
  department: string
  year: string | null
  section: string | null
  project_type: string | null
  guide: string | null
  team_size: number
  joined: number
  title: string | null
  project_fee: number
  share: number
}

export interface TeamRow {
  position: number
  member_id: string
  student_id: string
  name: string | null
  roll_number: string | null
  is_you: boolean
  is_lead: boolean
  invite_status: string
  chip: string
  identity_verified: boolean | null
  seat_confirmed: boolean | null
  payment_status: string | null
  can_remind: boolean
  reminded_at: string | null
}

export interface RegistrationState {
  student: {
    name: string | null
    roll_number: string | null
    email: string
    department: string | null
    section: string | null
    year: string | null
    college: string | null
    academic_year: string | null
  }
  enrolled: boolean
  steps: RegistrationStep[]
  current_step: string | null
  batch: BatchSummary | null
  team: TeamRow[]
  team_joined: number
  team_size: number
  your_registration: {
    confirmed: number
    total: number
    percent: number
    project_fee: number | null
    team_members: number
    your_share: number | null
    payment: {
      status: string | null
      amount: number | null
      receipt_number: string | null
      paid_at: string | null
      method: string | null
    }
    checklist: { key: string; label: string; done: boolean }[]
    waiting_for: number
    team_all_paid?: boolean
    next_action: {
      label: string
      enabled: boolean
      reason: string | null
      href?: string | null
    }
  }
  invite: { code: string; path: string; message: string } | null
  eligibility_note: string | null
}

const BASE = '/student/registration'

export const fetchRegistration = () => apiClient.get<RegistrationState>(BASE)

export const verifyBatchCode = (code: string) =>
  apiClient.post<{ batch: BatchSummary; verified: boolean }>(`${BASE}/verify-batch`, { code })

export const joinBatch = (code: string) =>
  apiClient.post<{ batch: BatchSummary; verified: boolean }>(`${BASE}/join`, { code })

export const resendInvite = (memberId: string) =>
  apiClient.post<{ member_id: string; delivered: boolean; detail: string }>(
    `${BASE}/resend-invite`, { member_id: memberId }
  )

export async function downloadReceipt(): Promise<void> {
  const blob = await apiClient.get<Blob>(`${BASE}/receipt.pdf`, { responseType: 'blob' })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = 'registration-receipt.pdf'
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}

/** Rupee amounts, in the Indian digit grouping the fee is quoted in. */
export interface PaymentOrder {
  order_id: string
  amount: number
  amount_paise: number
  currency: string
  key_id: string
  batch_code: string
  student_name: string | null
  student_email: string | null
  description: string
}

export const openPaymentOrder = () =>
  apiClient.post<PaymentOrder>('/student/payments/order', {})

export const confirmPayment = (payload: {
  razorpay_order_id: string
  razorpay_payment_id: string
  razorpay_signature: string
}) =>
  apiClient.post<{
    status: string
    amount?: number
    receipt_number?: string
    message: string
  }>('/student/payments/confirm', payload)

export const rupees = (value: number | null | undefined) =>
  value == null ? '—' : `₹${value.toLocaleString('en-IN')}`

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

export const fetchTeamBuilder = () =>
  apiClient.get<BuilderResponse>('/student/builder')

/** Opens the team's workspace, creating it if this is the first time. */
export const openTeamBuilder = () =>
  apiClient.post<BuilderResponse>('/student/builder', {})
