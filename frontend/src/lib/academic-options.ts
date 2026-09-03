/**
 * Single source of truth for the academic dropdowns used in student registration.
 *
 * Used by:
 *  - /register        (email signup, Step 2 "Academic")
 *  - /complete-profile (OAuth signup completion)
 *
 * These values end up on generated deliverables (report cover page, PPT,
 * certificates) via the backend document pipeline, so keep the stored strings
 * in the canonical formats produced by the helpers below.
 */

export const OTHER = 'Other'

export interface CourseConfig {
  /** Programme duration in years - drives the Year/Sem and Batch option lists. */
  duration: number
  /** Departments offered under this course. */
  departments: string[]
}

export const COURSE_CONFIG: Record<string, CourseConfig> = {
  'B.Tech': {
    duration: 4,
    departments: [
      'Computer Science & Engineering',
      'CSE (AI & Machine Learning)',
      'CSE (Data Science)',
      'CSE (Cyber Security)',
      'Information Technology',
      'Artificial Intelligence & Data Science',
      'Electronics & Communication Engineering',
      'Electrical & Electronics Engineering',
      'Mechanical Engineering',
      'Civil Engineering',
      'Chemical Engineering',
      'Biotechnology',
      OTHER,
    ],
  },
  'BE': {
    duration: 4,
    departments: [
      'Computer Science & Engineering',
      'CSE (AI & Machine Learning)',
      'CSE (Data Science)',
      'Information Technology',
      'Artificial Intelligence & Data Science',
      'Electronics & Communication Engineering',
      'Electrical & Electronics Engineering',
      'Mechanical Engineering',
      'Civil Engineering',
      'Chemical Engineering',
      OTHER,
    ],
  },
  'M.Tech': {
    duration: 2,
    departments: [
      'Computer Science & Engineering',
      'Software Engineering',
      'Artificial Intelligence & Data Science',
      'VLSI Design',
      'Embedded Systems',
      'Power Systems',
      'Power Electronics',
      'Structural Engineering',
      'Thermal Engineering',
      OTHER,
    ],
  },
  'ME': {
    duration: 2,
    departments: [
      'Computer Science & Engineering',
      'Artificial Intelligence & Data Science',
      'VLSI Design',
      'Embedded Systems',
      'Structural Engineering',
      'Thermal Engineering',
      OTHER,
    ],
  },
  'MCA': {
    duration: 2,
    departments: ['Computer Applications', 'Computer Science', OTHER],
  },
  'BCA': {
    duration: 3,
    departments: ['Computer Applications', 'Computer Science', OTHER],
  },
  'B.Sc': {
    duration: 3,
    departments: [
      'Computer Science',
      'Information Technology',
      'Data Science',
      'Mathematics',
      'Physics',
      'Chemistry',
      'Electronics',
      OTHER,
    ],
  },
  'M.Sc': {
    duration: 2,
    departments: [
      'Computer Science',
      'Information Technology',
      'Data Science',
      'Mathematics',
      'Physics',
      'Chemistry',
      'Electronics',
      OTHER,
    ],
  },
  [OTHER]: {
    duration: 4,
    departments: [OTHER],
  },
}

export const COURSES = Object.keys(COURSE_CONFIG)

export const SECTIONS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'N/A']

const ORDINALS = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th']

const ordinal = (n: number): string => ORDINALS[n - 1] || `${n}th`

/** Departments for a course. Empty array when no course is selected yet. */
export function getDepartments(course: string): string[] {
  return COURSE_CONFIG[course]?.departments ?? []
}

/**
 * Year/Semester options for a course, e.g. B.Tech (4 years) yields
 * "1st Year / 1st Semester" ... "4th Year / 8th Semester".
 */
export function getYearSemesterOptions(course: string): string[] {
  const duration = COURSE_CONFIG[course]?.duration
  if (!duration) return []

  const options: string[] = []
  for (let year = 1; year <= duration; year++) {
    for (const sem of [year * 2 - 1, year * 2]) {
      options.push(`${ordinal(year)} Year / ${ordinal(sem)} Semester`)
    }
  }
  return options
}

/**
 * Batch options derived from the current year and the course duration, e.g.
 * a 4-year course in 2026 yields 2021-2025 ... 2026-2030. Computed rather than
 * hardcoded so the list never goes stale.
 */
export function getBatchOptions(course: string, now: Date = new Date()): string[] {
  const duration = COURSE_CONFIG[course]?.duration
  if (!duration) return []

  const currentYear = now.getFullYear()
  const options: string[] = []
  // Cover students who already started (back to one full cycle) plus next intake.
  for (let start = currentYear - duration - 1; start <= currentYear + 1; start++) {
    options.push(`${start}-${start + duration}`)
  }
  return options.reverse()
}

/** True when a stored value predates the dropdowns / came from an "Other" entry. */
export function isCustomValue(value: string, allowed: string[]): boolean {
  return !!value && !allowed.includes(value)
}
