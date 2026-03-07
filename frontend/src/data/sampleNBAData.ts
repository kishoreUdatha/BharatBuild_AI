/**
 * Sample Data for NBA Accreditation
 * Comprehensive seed data for Outcome-Based Education (OBE) accreditation
 */

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface NBACriterion {
  id: number
  name: string
  marks: number
}

export interface NBAProgram {
  id: string
  name: string
  code: string
  department: string
  duration_years: number
  intake: number
  tier: 'tier1' | 'tier2'
  accreditation_status: 'accredited' | 'under_review' | 'not_applied' | 'expired'
  validity_start?: string
  validity_end?: string
  score: number
  percentage: number
}

export interface PEO {
  id: string
  statement: string
  attainment_level: number
}

export interface ProgramOutcome {
  id: string
  name: string
  description: string
}

export interface PSO {
  id: string
  statement: string
}

export interface CourseOutcome {
  id: string
  statement: string
  po_mapping: Record<string, number>
}

export interface Course {
  code: string
  name: string
  credits: number
  semester: number
  course_outcomes: CourseOutcome[]
  attainment: {
    direct: number
    indirect: number
    overall: number
  }
}

export interface POAttainment {
  direct: number
  indirect: number
  overall: number
  target: number
  status: 'achieved' | 'not_achieved'
}

export interface Faculty {
  id: string
  name: string
  designation: string
  qualification: string
  experience_years: number
  specialization: string
  publications: number
  h_index: number
  patents: number
  funded_projects: number
  project_amount_lakhs: number
}

export interface CriteriaScore {
  id: number
  name: string
  max: number
  score: number
  percentage: number
}

// ============================================================================
// NBA CRITERIA DEFINITIONS
// ============================================================================

export const NBA_CRITERIA = {
  tier1: {
    name: 'NBA Tier-1 (SAR Format)',
    total_marks: 1000,
    criteria: [
      { id: 1, name: 'Vision, Mission and Program Educational Objectives', marks: 75 },
      { id: 2, name: 'Program Curriculum and Teaching-Learning Processes', marks: 125 },
      { id: 3, name: 'Course Outcomes and Program Outcomes', marks: 225 },
      { id: 4, name: "Students' Performance", marks: 150 },
      { id: 5, name: 'Faculty Information and Contributions', marks: 200 },
      { id: 6, name: 'Facilities and Technical Support', marks: 100 },
      { id: 7, name: 'Continuous Improvement', marks: 75 },
      { id: 8, name: 'First Year Academics', marks: 50 },
    ] as NBACriterion[],
  },
  tier2: {
    name: 'NBA Tier-2 (Autonomous Institutions)',
    total_marks: 1000,
    criteria: [
      { id: 1, name: 'Program Educational Objectives', marks: 100 },
      { id: 2, name: 'Attainment of Program Outcomes', marks: 300 },
      { id: 3, name: 'Faculty Contributions', marks: 200 },
      { id: 4, name: 'Facilities and Infrastructure', marks: 150 },
      { id: 5, name: 'Academic Support', marks: 100 },
      { id: 6, name: 'Governance and Transparency', marks: 100 },
      { id: 7, name: 'Continuous Improvement', marks: 50 },
    ] as NBACriterion[],
  },
}

// ============================================================================
// SAMPLE PROGRAMS
// ============================================================================

export const SAMPLE_PROGRAMS: NBAProgram[] = [
  {
    id: 'prog-001',
    name: 'B.Tech Computer Science and Engineering',
    code: 'CSE',
    department: 'Computer Science and Engineering',
    duration_years: 4,
    intake: 120,
    tier: 'tier1',
    accreditation_status: 'accredited',
    validity_start: '2024-07-01',
    validity_end: '2027-06-30',
    score: 885,
    percentage: 88.5,
  },
  {
    id: 'prog-002',
    name: 'B.Tech Electronics and Communication Engineering',
    code: 'ECE',
    department: 'Electronics and Communication Engineering',
    duration_years: 4,
    intake: 60,
    tier: 'tier1',
    accreditation_status: 'accredited',
    validity_start: '2024-07-01',
    validity_end: '2027-06-30',
    score: 820,
    percentage: 82.0,
  },
  {
    id: 'prog-003',
    name: 'B.Tech Mechanical Engineering',
    code: 'ME',
    department: 'Mechanical Engineering',
    duration_years: 4,
    intake: 60,
    tier: 'tier1',
    accreditation_status: 'accredited',
    validity_start: '2023-07-01',
    validity_end: '2026-06-30',
    score: 795,
    percentage: 79.5,
  },
  {
    id: 'prog-004',
    name: 'B.Tech Electrical and Electronics Engineering',
    code: 'EEE',
    department: 'Electrical and Electronics Engineering',
    duration_years: 4,
    intake: 60,
    tier: 'tier1',
    accreditation_status: 'under_review',
    score: 780,
    percentage: 78.0,
  },
  {
    id: 'prog-005',
    name: 'M.Tech Data Science',
    code: 'MDS',
    department: 'Computer Science and Engineering',
    duration_years: 2,
    intake: 30,
    tier: 'tier2',
    accreditation_status: 'accredited',
    validity_start: '2024-01-01',
    validity_end: '2027-12-31',
    score: 850,
    percentage: 85.0,
  },
]

// ============================================================================
// PROGRAM EDUCATIONAL OBJECTIVES (PEOs)
// ============================================================================

export const SAMPLE_PEOS: Record<string, PEO[]> = {
  'prog-001': [
    {
      id: 'PEO1',
      statement: 'Graduates will demonstrate technical competence in computer science fundamentals and apply them to solve complex engineering problems.',
      attainment_level: 85,
    },
    {
      id: 'PEO2',
      statement: 'Graduates will pursue successful careers in software industry, research, or entrepreneurship with continuous learning.',
      attainment_level: 88,
    },
    {
      id: 'PEO3',
      statement: 'Graduates will exhibit professional ethics, effective communication, and teamwork skills in diverse environments.',
      attainment_level: 82,
    },
    {
      id: 'PEO4',
      statement: 'Graduates will contribute to society through innovation, leadership, and socially responsible computing solutions.',
      attainment_level: 78,
    },
  ],
}

// ============================================================================
// PROGRAM OUTCOMES (POs) - Washington Accord
// ============================================================================

export const PROGRAM_OUTCOMES: ProgramOutcome[] = [
  { id: 'PO1', name: 'Engineering Knowledge', description: 'Apply knowledge of mathematics, science, engineering fundamentals to complex problems.' },
  { id: 'PO2', name: 'Problem Analysis', description: 'Identify, formulate, and analyze complex engineering problems.' },
  { id: 'PO3', name: 'Design/Development', description: 'Design solutions for complex engineering problems meeting specified needs.' },
  { id: 'PO4', name: 'Conduct Investigations', description: 'Use research-based knowledge including design of experiments and data analysis.' },
  { id: 'PO5', name: 'Modern Tool Usage', description: 'Create, select and apply appropriate techniques, resources, and modern tools.' },
  { id: 'PO6', name: 'Engineer and Society', description: 'Apply reasoning to assess societal, health, safety, legal and cultural issues.' },
  { id: 'PO7', name: 'Environment and Sustainability', description: 'Understand impact of engineering solutions and need for sustainable development.' },
  { id: 'PO8', name: 'Ethics', description: 'Apply ethical principles and commit to professional ethics and responsibilities.' },
  { id: 'PO9', name: 'Individual and Teamwork', description: 'Function effectively as individual, member or leader in diverse teams.' },
  { id: 'PO10', name: 'Communication', description: 'Communicate effectively on complex engineering activities.' },
  { id: 'PO11', name: 'Project Management', description: 'Apply engineering and management principles to manage projects.' },
  { id: 'PO12', name: 'Life-long Learning', description: 'Engage in independent and life-long learning in technological change.' },
]

// Program Specific Outcomes
export const SAMPLE_PSOS: Record<string, PSO[]> = {
  'prog-001': [
    { id: 'PSO1', statement: 'Ability to design and develop software solutions using modern programming paradigms and frameworks.' },
    { id: 'PSO2', statement: 'Ability to apply AI/ML techniques for solving real-world problems in various domains.' },
    { id: 'PSO3', statement: 'Ability to work on emerging technologies like cloud computing, IoT, and blockchain.' },
  ],
}

// ============================================================================
// SAMPLE COURSES WITH CO-PO MAPPING
// ============================================================================

export const SAMPLE_COURSES: Record<string, Course[]> = {
  'prog-001': [
    {
      code: 'CS201',
      name: 'Data Structures',
      credits: 4,
      semester: 3,
      course_outcomes: [
        { id: 'CO1', statement: 'Analyze algorithms for time and space complexity', po_mapping: { PO1: 3, PO2: 3, PO3: 2, PO4: 1 } },
        { id: 'CO2', statement: 'Design and implement linear data structures', po_mapping: { PO1: 3, PO3: 3, PO5: 2 } },
        { id: 'CO3', statement: 'Apply tree and graph algorithms for problem solving', po_mapping: { PO1: 3, PO2: 3, PO3: 3, PO5: 2 } },
        { id: 'CO4', statement: 'Implement sorting and searching techniques', po_mapping: { PO1: 2, PO3: 3, PO5: 3 } },
      ],
      attainment: { direct: 82.5, indirect: 78.0, overall: 81.1 },
    },
    {
      code: 'CS301',
      name: 'Database Management Systems',
      credits: 4,
      semester: 5,
      course_outcomes: [
        { id: 'CO1', statement: 'Design ER diagrams and relational schemas', po_mapping: { PO1: 2, PO3: 3 } },
        { id: 'CO2', statement: 'Write complex SQL queries and stored procedures', po_mapping: { PO1: 3, PO5: 3 } },
        { id: 'CO3', statement: 'Apply normalization techniques', po_mapping: { PO1: 3, PO2: 3 } },
        { id: 'CO4', statement: 'Implement transaction management and recovery', po_mapping: { PO1: 2, PO3: 2, PO4: 2 } },
      ],
      attainment: { direct: 85.0, indirect: 80.0, overall: 83.5 },
    },
    {
      code: 'CS401',
      name: 'Machine Learning',
      credits: 4,
      semester: 7,
      course_outcomes: [
        { id: 'CO1', statement: 'Apply supervised learning algorithms', po_mapping: { PO1: 3, PO2: 3, PO4: 3, PO5: 3 } },
        { id: 'CO2', statement: 'Implement unsupervised learning techniques', po_mapping: { PO1: 3, PO3: 3, PO5: 3 } },
        { id: 'CO3', statement: 'Design and evaluate ML models', po_mapping: { PO2: 3, PO3: 3, PO4: 3 } },
        { id: 'CO4', statement: 'Apply deep learning for real-world applications', po_mapping: { PO3: 3, PO5: 3, PO7: 2 } },
      ],
      attainment: { direct: 78.0, indirect: 75.0, overall: 77.1 },
    },
  ],
}

// ============================================================================
// PO ATTAINMENT DATA
// ============================================================================

export const SAMPLE_PO_ATTAINMENT: Record<string, {
  batch: string
  attainment_method: string
  po_attainment: Record<string, POAttainment>
  pso_attainment: Record<string, POAttainment>
}> = {
  'prog-001': {
    batch: '2020-2024',
    attainment_method: 'Direct + Indirect (80:20)',
    po_attainment: {
      PO1: { direct: 85.2, indirect: 82.0, overall: 84.6, target: 70, status: 'achieved' },
      PO2: { direct: 82.5, indirect: 79.5, overall: 81.9, target: 70, status: 'achieved' },
      PO3: { direct: 80.8, indirect: 78.0, overall: 80.2, target: 70, status: 'achieved' },
      PO4: { direct: 78.5, indirect: 75.0, overall: 77.8, target: 70, status: 'achieved' },
      PO5: { direct: 88.0, indirect: 85.0, overall: 87.4, target: 70, status: 'achieved' },
      PO6: { direct: 75.5, indirect: 72.0, overall: 74.8, target: 70, status: 'achieved' },
      PO7: { direct: 72.0, indirect: 70.5, overall: 71.7, target: 70, status: 'achieved' },
      PO8: { direct: 80.0, indirect: 78.0, overall: 79.6, target: 70, status: 'achieved' },
      PO9: { direct: 85.0, indirect: 82.0, overall: 84.4, target: 70, status: 'achieved' },
      PO10: { direct: 82.0, indirect: 80.0, overall: 81.6, target: 70, status: 'achieved' },
      PO11: { direct: 78.0, indirect: 75.0, overall: 77.4, target: 70, status: 'achieved' },
      PO12: { direct: 75.0, indirect: 73.0, overall: 74.6, target: 70, status: 'achieved' },
    },
    pso_attainment: {
      PSO1: { direct: 86.0, indirect: 83.0, overall: 85.4, target: 70, status: 'achieved' },
      PSO2: { direct: 82.0, indirect: 78.0, overall: 81.2, target: 70, status: 'achieved' },
      PSO3: { direct: 79.0, indirect: 76.0, overall: 78.4, target: 70, status: 'achieved' },
    },
  },
}

// ============================================================================
// FACULTY DATA
// ============================================================================

export const SAMPLE_FACULTY: Record<string, Faculty[]> = {
  'prog-001': [
    {
      id: 'fac-001',
      name: 'Dr. Rajesh Kumar',
      designation: 'Professor & HOD',
      qualification: 'Ph.D. (IIT Madras)',
      experience_years: 22,
      specialization: 'Machine Learning, Data Science',
      publications: 85,
      h_index: 18,
      patents: 3,
      funded_projects: 5,
      project_amount_lakhs: 125,
    },
    {
      id: 'fac-002',
      name: 'Dr. Priya Sharma',
      designation: 'Associate Professor',
      qualification: 'Ph.D. (IISc Bangalore)',
      experience_years: 15,
      specialization: 'Computer Networks, Security',
      publications: 52,
      h_index: 12,
      patents: 2,
      funded_projects: 3,
      project_amount_lakhs: 65,
    },
    {
      id: 'fac-003',
      name: 'Dr. Arun Menon',
      designation: 'Associate Professor',
      qualification: 'Ph.D. (NIT Trichy)',
      experience_years: 12,
      specialization: 'Software Engineering, DevOps',
      publications: 38,
      h_index: 9,
      patents: 1,
      funded_projects: 2,
      project_amount_lakhs: 35,
    },
    {
      id: 'fac-004',
      name: 'Ms. Divya Nair',
      designation: 'Assistant Professor',
      qualification: 'M.Tech (IIT Delhi), Ph.D. (Pursuing)',
      experience_years: 6,
      specialization: 'Cloud Computing, IoT',
      publications: 15,
      h_index: 5,
      patents: 0,
      funded_projects: 1,
      project_amount_lakhs: 12,
    },
  ],
}

export const FACULTY_SUMMARY: Record<string, {
  total_faculty: number
  professors: number
  associate_professors: number
  assistant_professors: number
  phd_holders: number
  phd_percentage: number
  avg_experience: number
  student_faculty_ratio: string
  total_publications: number
  total_patents: number
  total_funded_projects: number
  total_funding_lakhs: number
}> = {
  'prog-001': {
    total_faculty: 18,
    professors: 4,
    associate_professors: 6,
    assistant_professors: 8,
    phd_holders: 14,
    phd_percentage: 77.8,
    avg_experience: 12.5,
    student_faculty_ratio: '15:1',
    total_publications: 285,
    total_patents: 8,
    total_funded_projects: 15,
    total_funding_lakhs: 425,
  },
}

// ============================================================================
// STUDENT PERFORMANCE DATA
// ============================================================================

export const SAMPLE_STUDENT_PERFORMANCE: Record<string, {
  batch: string
  intake: number
  enrolled: number
  graduated: number
  pass_percentage: number
  first_class_percentage: number
  distinction_percentage: number
  placement_percentage: number
  higher_studies_percentage: number
  avg_salary_lpa: number
  max_salary_lpa: number
  companies_visited: number
  offers_made: number
  internships_completed: number
}> = {
  'prog-001': {
    batch: '2020-2024',
    intake: 120,
    enrolled: 118,
    graduated: 115,
    pass_percentage: 97.5,
    first_class_percentage: 78.5,
    distinction_percentage: 32.0,
    placement_percentage: 95.5,
    higher_studies_percentage: 18.0,
    avg_salary_lpa: 9.2,
    max_salary_lpa: 52,
    companies_visited: 85,
    offers_made: 142,
    internships_completed: 115,
  },
}

// ============================================================================
// NBA CRITERIA SCORES
// ============================================================================

export const NBA_CRITERIA_SCORES: Record<string, {
  tier: string
  criteria_scores: CriteriaScore[]
  total_marks: number
  total_score: number
  overall_percentage: number
  accreditation_status: string
  validity_years: number
}> = {
  'prog-001': {
    tier: 'tier1',
    criteria_scores: [
      { id: 1, name: 'Vision, Mission and PEOs', max: 75, score: 68, percentage: 90.7 },
      { id: 2, name: 'Curriculum and Teaching-Learning', max: 125, score: 112, percentage: 89.6 },
      { id: 3, name: 'Course Outcomes and Program Outcomes', max: 225, score: 198, percentage: 88.0 },
      { id: 4, name: "Students' Performance", max: 150, score: 135, percentage: 90.0 },
      { id: 5, name: 'Faculty Information', max: 200, score: 175, percentage: 87.5 },
      { id: 6, name: 'Facilities and Technical Support', max: 100, score: 88, percentage: 88.0 },
      { id: 7, name: 'Continuous Improvement', max: 75, score: 65, percentage: 86.7 },
      { id: 8, name: 'First Year Academics', max: 50, score: 44, percentage: 88.0 },
    ],
    total_marks: 1000,
    total_score: 885,
    overall_percentage: 88.5,
    accreditation_status: 'accredited',
    validity_years: 3,
  },
}

// ============================================================================
// NBA DASHBOARD STATISTICS
// ============================================================================

export const NBA_DASHBOARD_STATS = {
  total_programs: 5,
  accredited_programs: 4,
  under_review: 1,
  tier1_programs: 4,
  tier2_programs: 1,
  avg_score: 83.2,
  avg_po_attainment: 80.5,
  avg_placement: 92.0,
  total_faculty: 85,
  phd_percentage: 72.0,
  avg_publications_per_faculty: 3.2,
  total_labs: 25,
  total_equipment_value_lakhs: 650,
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function getProgramById(programId: string): NBAProgram | undefined {
  return SAMPLE_PROGRAMS.find(p => p.id === programId)
}

export function getAllPrograms(): NBAProgram[] {
  return SAMPLE_PROGRAMS
}

export function getPEOData(programId: string): PEO[] {
  return SAMPLE_PEOS[programId] || []
}

export function getPOAttainment(programId: string) {
  return SAMPLE_PO_ATTAINMENT[programId]
}

export function getFacultyData(programId: string): Faculty[] {
  return SAMPLE_FACULTY[programId] || []
}

export function getStudentPerformance(programId: string) {
  return SAMPLE_STUDENT_PERFORMANCE[programId]
}

export function getNBACriteriaScores(programId: string) {
  return NBA_CRITERIA_SCORES[programId]
}

export function getNBADashboardStats() {
  return NBA_DASHBOARD_STATS
}

export function getAccreditedPrograms(): NBAProgram[] {
  return SAMPLE_PROGRAMS.filter(p => p.accreditation_status === 'accredited')
}

export function getProgramsByTier(tier: 'tier1' | 'tier2'): NBAProgram[] {
  return SAMPLE_PROGRAMS.filter(p => p.tier === tier)
}
