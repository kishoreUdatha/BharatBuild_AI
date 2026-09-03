/**
 * Taking attendance.
 *
 * The register is a section on a day. Saving the same day again corrects it
 * rather than adding to it, so a screen may safely re-save what it loaded.
 */

import { apiClient } from '@/lib/api-client'

export type AttendanceStatus = 'present' | 'absent' | 'late'

export interface RosterStudent {
  student_id: string
  full_name: string | null
  roll_number: string | null
  section: string | null
  /** null when this day has not been marked for them yet. */
  status: AttendanceStatus | null
  status_label: string
  attendance_rate: number | null
  below_floor: boolean
}

export interface Roster {
  date: string
  department: string
  year: string | null
  section: string | null
  academic_year: string
  students: RosterStudent[]
  total: number
  marked: number
  already_taken: boolean
  counts: Record<string, number>
  floor: number
  statuses: { value: AttendanceStatus; label: string }[]
}

export interface MarkResult extends Roster {
  created: number
  updated: number
  unchanged: number
  message: string
}

export interface StudentAttendance {
  academic_year: string
  department?: string | null
  section?: string | null
  days_recorded: number
  present: number
  late: number
  absent: number
  attendance_rate: number | null
  floor: number
  below_floor: boolean
  /** Sessions, not days: a date appears once per half of the college day. */
  sessions_recorded?: number
  days_covered?: number
  days: {
    date: string
    session?: string
    session_label?: string
    status: AttendanceStatus
    status_label: string
  }[]
  absences: { date: string; session: string }[]
  student?: {
    id: string
    full_name: string | null
    roll_number: string | null
    department: string | null
    section: string | null
  }
}

export interface RosterQuery {
  department: string
  section?: string
  year?: string
  date?: string
  academic_year?: string
}

export const fetchRoster = (params: RosterQuery) =>
  apiClient.get<Roster>('/faculty/attendance/roster', { params: clean(params) })

export const markAttendance = (
  params: RosterQuery & { marks: { student_id: string; status: AttendanceStatus }[] },
) => apiClient.post<MarkResult>('/faculty/attendance/mark', clean(params))

export const fetchStudentAttendance = (studentId: string, academicYear?: string) =>
  apiClient.get<StudentAttendance>(
    `/faculty/attendance/student/${studentId}`,
    { params: clean({ academic_year: academicYear }) })

export const fetchMyAttendance = () =>
  apiClient.get<StudentAttendance>('/student/attendance')

/** Drop empty values so an unset filter is absent rather than an empty string. */
function clean<T extends Record<string, any>>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  ) as Partial<T>
}

export function attendanceError(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg).filter(Boolean).join('; ') || fallback
  }
  return fallback
}

/** Today, as the YYYY-MM-DD the date input and the API both expect. */
export function today(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
}
