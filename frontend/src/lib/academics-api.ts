/**
 * Departments & Sections API.
 *
 * The structure tree, the department cohort view and the four section tabs.
 * Kept separate from faculty-api.ts, which is about registration lists.
 */

import { apiClient } from '@/lib/api-client'

type Params = Record<string, string | number | boolean | undefined>

const clean = (params: Params) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ''))

export interface StructureSemester {
  semester: string
  sections: string[]
  section_count: number
}

export interface StructureYear {
  year: string
  section_count: number
  semesters: StructureSemester[]
}

export interface StructureDepartment {
  id: string
  code: string
  name: string
  students: number
  section_count: number
  years: StructureYear[]
}

export interface StructureTree {
  academic_year: string
  schools: { school: string; students: number; departments: StructureDepartment[] }[]
}

export interface SectionCard {
  id: string
  name: string
  students: number
  batches: number
  coordinator: string | null
  guide_count: number
  guides: string[]
  registration: number | null
  attendance: number | null
  progress: number | null
  pending_reviews: number
  status: string
  status_key: string
}

export interface AllocationRow {
  id: string
  section: string
  capacity: number
  assigned: number
  unassigned: number
  over_capacity: number
  batches: number
  guides: number
  ratio: string
  coordinator: string | null
  room: string | null
  timetable: string
  status: string
  status_key: string
}

export interface DepartmentNotice {
  id: string
  title: string
  detail: string | null
  window_label: string | null
  due_at: string | null
  severity: string
}

export interface AcademicOverview {
  department: {
    id: string
    code: string
    name: string
    school: string
    academic_year: string
    hod: string | null
    dept_coordinator: string | null
    project_coordinator: string | null
  }
  year: string
  semester: string
  section_count: number
  assigned_students: number
  batch_count: number
  cards: SectionCard[]
  matrix: AllocationRow[]
  unmapped_students: number
  notices: DepartmentNotice[]
}

export interface SectionHeader {
  id: string
  name: string
  department: string
  department_name: string
  year: string
  semester: string
  academic_year: string
  status: string
  status_key: string
  coordinator: string | null
  room: string | null
  schedule_days: string | null
  schedule_time: string | null
  capacity: number
}

export interface SectionFacultyRow {
  id: string
  name: string | null
  roles: string[]
  role_label: string
  responsibilities: string[]
  subjects?: string[]
}

export interface SectionOverview {
  header: SectionHeader
  kpis: { id: string; value: string; label: string; warn?: boolean }[]
  faculty: SectionFacultyRow[]
  distribution: { domain: string; count: number; share: number }[]
  attention: { kind: string; severity: string; label: string }[]
  metrics: {
    students: number
    batches: number
    registration: number | null
    attendance: number | null
    progress: number | null
    pending_reviews: number
    health: string
  }
}

export interface SectionFacultyTab {
  header: SectionHeader
  rows: SectionFacultyRow[]
  role_counts: { role: string; count: number }[]
}

export interface SectionSubjectsTab {
  header: SectionHeader
  rows: {
    id: string
    code: string | null
    title: string
    kind: string
    kind_key: string
    credits: number | null
    faculty: string | null
  }[]
  total_credits: number
}

export interface SectionProjectsTab {
  header: SectionHeader
  rows: {
    id: string
    batch_code: string
    title: string | null
    domain: string | null
    guide: string | null
    members: number
    progress: number
    status: string
    status_key: string
    base_paper: string
  }[]
}

export interface MyAccess {
  name: string | null
  departments: string[]
  department_label: string
  sections: string[]
  section_label: string
  roles: string[]
  assignments: {
    department: string
    year: string
    semester: string
    section: string
    role: string
    responsibility: string | null
  }[]
}

const BASE = '/faculty/academics'

export const fetchStructure = (academicYear?: string) =>
  apiClient.get<StructureTree>(`${BASE}/structure`, { params: clean({ academic_year: academicYear }) })

export const fetchAcademicOverview = (
  department: string, year: string, semester: string, academicYear?: string
) =>
  apiClient.get<AcademicOverview>(`${BASE}/overview`, {
    params: clean({ department, year, semester, academic_year: academicYear }),
  })

export const fetchSectionOverview = (id: string) =>
  apiClient.get<SectionOverview>(`${BASE}/sections/${id}`)

export const fetchSectionFaculty = (id: string) =>
  apiClient.get<SectionFacultyTab>(`${BASE}/sections/${id}/faculty`)

export const fetchSectionSubjects = (id: string) =>
  apiClient.get<SectionSubjectsTab>(`${BASE}/sections/${id}/subjects`)

export const fetchSectionProjects = (id: string) =>
  apiClient.get<SectionProjectsTab>(`${BASE}/sections/${id}/projects`)

export const fetchMyAccess = (academicYear?: string) =>
  apiClient.get<MyAccess>(`${BASE}/my-access`, { params: clean({ academic_year: academicYear }) })

export const requestSectionUpdate = (body: {
  department: string
  section_id?: string
  kind: string
  note: string
  academic_year?: string
}) => apiClient.post<{ id: string; kind: string; status: string }>(`${BASE}/update-requests`, body)

export const fetchUpdateRequests = (department: string, academicYear?: string) =>
  apiClient.get<{
    rows: {
      id: string
      section: string | null
      kind: string
      note: string
      status: string
      status_key: string
      requested_by: string | null
      created_at: string
    }[]
  }>(`${BASE}/update-requests`, { params: clean({ department, academic_year: academicYear }) })

/** Export Structure - one row per section with its live allocation figures. */
export async function downloadStructure(department?: string, academicYear?: string): Promise<void> {
  const blob = await apiClient.get<Blob>(`${BASE}/structure.csv`, {
    params: clean({ department, academic_year: academicYear }),
    responseType: 'blob',
  })
  const href = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = `${department ?? 'all-departments'}-structure.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(href)
}
