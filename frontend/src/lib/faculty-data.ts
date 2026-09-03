/**
 * Faculty dashboard presentation config.
 *
 * Values come from `GET /faculty/dashboard` (see faculty-api.ts). What lives
 * here is only how those values are dressed: which colour a KPI tile gets,
 * which ring a stage shows at a given percent, and the fallback filter lists
 * used before `/faculty/filters` responds.
 */

export type Tone = 'green' | 'amber' | 'red' | 'indigo' | 'blue' | 'teal' | 'slate'

export const INSTITUTE = {
  name: 'Sri Guru Institute of Technology',
}

export const ACADEMIC_YEARS = ['2026-27', '2025-26', '2024-25']

/** Displayed as "Academic Year 2026–27"; the API takes the raw "2026-27". */
export const formatAcademicYear = (value: string) => `Academic Year ${value.replace('-', '–')}`

export const NOTIFICATION_COUNT = 3

// ------------------------------------------------------------------ filters

export interface FilterConfig {
  key: 'department' | 'year' | 'semester' | 'section' | 'project_type' | 'guide_id'
  label: string
  /** Prepended to whatever the API reports, and means "no filter". */
  allLabel?: string
  fallback: string[]
}

export const FILTERS: FilterConfig[] = [
  { key: 'department', label: 'Department', allLabel: 'All Departments', fallback: ['CSE', 'IT', 'ECE'] },
  { key: 'year', label: 'Year', allLabel: 'All Years', fallback: ['4th Year', '3rd Year'] },
  { key: 'semester', label: 'Semester', allLabel: 'All Semesters', fallback: ['I', 'II'] },
  { key: 'section', label: 'Section', allLabel: 'All Sections', fallback: ['A', 'B', 'C'] },
  { key: 'project_type', label: 'Project Type', allLabel: 'All Types', fallback: ['Major Project', 'Mini Project'] },
  // Guides come back as {id, name}; handled separately in the page.
  { key: 'guide_id', label: 'Faculty Guide', allLabel: 'All Guides', fallback: [] },
]

// --------------------------------------------------------------- KPI tiles

export const KPI_TONES: Record<string, Tone> = {
  students: 'indigo',
  batches: 'blue',
  progress: 'green',
  attendance: 'teal',
  reviews: 'amber',
  attention: 'red',
}

export const ATTENTION_TONES: Record<string, Tone> = {
  attendance: 'green',
  'base-papers': 'amber',
  overdue: 'red',
  inactive: 'indigo',
}

export const BASE_PAPER_TONES: Record<string, Tone> = {
  Verified: 'green',
  Pending: 'amber',
  Missing: 'red',
}

// ------------------------------------------------------------ stage stepper

export type StageState = 'complete' | 'active' | 'pending'

/**
 * A stage's ring colour and shape follow its percentage, so the stepper stays
 * meaningful no matter which cohort is loaded.
 */
export function stageAppearance(percent: number): { state: StageState; tone: Tone } {
  if (percent >= 90) return { state: 'complete', tone: 'green' }
  if (percent >= 80) return { state: 'active', tone: 'green' }
  if (percent >= 70) return { state: 'active', tone: 'indigo' }
  if (percent >= 50) return { state: 'active', tone: 'red' }
  return { state: 'pending', tone: 'slate' }
}

// ------------------------------------------------------------- chart series

const SERIES_PALETTE = ['#6366F1', '#3B82F6', '#16A34A', '#F59E0B', '#EC4899', '#0D9488']

/** Stable colour per section, in the order the API lists them. */
export function seriesColors(names: string[]): Record<string, string> {
  return Object.fromEntries(names.map((name, i) => [name, SERIES_PALETTE[i % SERIES_PALETTE.length]]))
}

export const sectionLabel = (name: string) => (name.length <= 2 ? `Section ${name}` : name)

export const SECTION_TABLE_NOTE = '* Unassigned students are not mapped to any section yet.'
