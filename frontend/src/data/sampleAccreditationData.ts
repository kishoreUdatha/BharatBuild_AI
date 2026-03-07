/**
 * Sample Data for NAAC 2025 Binary Accreditation and MBGL Framework
 * Comprehensive data for demonstration and testing
 */

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export type BinaryStatus = 'not_applied' | 'applied' | 'under_review' | 'accredited' | 'not_accredited' | 'expired'
export type MBGLLevel = 'not_assessed' | 'level_1' | 'level_2' | 'level_3' | 'level_4' | 'level_5'
export type AssessmentPhase = 'self_study' | 'ssr_submission' | 'ai_assessment' | 'dvv_clarification' | 'peer_review' | 'decision' | 'completed'

export interface Institution {
  id: string
  name: string
  type: 'autonomous' | 'affiliated' | 'deemed' | 'central'
  location: string
  established: number
  students: number
  faculty: number
}

export interface AccreditationApplication {
  id: string
  institutionId: string
  applicationNumber: string
  applicationDate: string
  cycle: 'first' | 'second' | 'third' | 'fourth' | 'fifth'
  cycleNumber: number
  binaryStatus: BinaryStatus
  binaryAssessmentDate?: string
  binaryValidityStart?: string
  binaryValidityEnd?: string
  mbglLevel: MBGLLevel
  mbglAssessmentDate?: string
  mbglScore?: number
  mbglValidityStart?: string
  mbglValidityEnd?: string
  previousGrade?: string
  previousCgpa?: number
  previousValidityEnd?: string
  currentPhase: AssessmentPhase
  selfStudyScore?: number
  aiAssessmentScore?: number
  stakeholderScore?: number
  finalScore?: number
  notes?: string
}

export interface AttributeScore {
  attribute: string
  attributeName: string
  weightage: number
  maxScore: number
  selfScore: number
  verifiedScore?: number
  finalScore?: number
  aiScore?: number
  aiConfidence?: number
  evidenceCount: number
  evidenceVerified: number
  isComplete: boolean
  aiFeedback?: string
}

export interface MBGLAssessment {
  id: string
  applicationId: string
  assessmentYear: string
  assessmentDate: string
  leadershipMaturity: number
  processMaturity: number
  peopleMaturity: number
  technologyMaturity: number
  outcomeMaturity: number
  innovationMaturity: number
  stakeholderMaturity: number
  sustainabilityMaturity: number
  averageMaturity: number
  weightedScore: number
  recommendedLevel: MBGLLevel
  finalLevel: MBGLLevel
  level1CriteriaMet: boolean
  level2CriteriaMet: boolean
  level3CriteriaMet: boolean
  level4CriteriaMet: boolean
  level5CriteriaMet: boolean
  strengths: string[]
  improvementsNeeded: string[]
  actionPlan: string
  assessedBy: string
  verifiedBy: string
}

export interface MBGLLevelCriteria {
  id: string
  level: MBGLLevel
  levelNumber: number
  levelName: string
  levelDescription: string
  minBinaryStatus: boolean
  minMaturityScore: number
  mandatoryCriteria: string[]
  optionalCriteria: string[]
  optionalCriteriaMin: number
  validityYears: number
  recognitionBenefits: string[]
  isActive: boolean
}

export interface TimelineMilestone {
  milestoneName: string
  milestoneType: 'submission' | 'approval' | 'assessment' | 'clarification' | 'review' | 'decision' | 'certificate'
  plannedDate: string
  actualDate?: string
  isCompleted: boolean
  notes?: string
}

// ============================================================================
// SAMPLE INSTITUTIONS DATA
// ============================================================================

export const SAMPLE_INSTITUTIONS: Institution[] = [
  {
    id: 'inst-001',
    name: 'Bharath Institute of Technology',
    type: 'autonomous',
    location: 'Chennai, Tamil Nadu',
    established: 1995,
    students: 5200,
    faculty: 320,
  },
  {
    id: 'inst-002',
    name: 'Vidya Engineering College',
    type: 'affiliated',
    location: 'Bangalore, Karnataka',
    established: 2005,
    students: 3500,
    faculty: 180,
  },
  {
    id: 'inst-003',
    name: 'National College of Arts & Science',
    type: 'autonomous',
    location: 'Hyderabad, Telangana',
    established: 1980,
    students: 8000,
    faculty: 450,
  },
  {
    id: 'inst-004',
    name: 'Sunrise University',
    type: 'deemed',
    location: 'Pune, Maharashtra',
    established: 2010,
    students: 4200,
    faculty: 250,
  },
  {
    id: 'inst-005',
    name: 'Heritage Institute of Management',
    type: 'affiliated',
    location: 'Delhi NCR',
    established: 2008,
    students: 2800,
    faculty: 150,
  },
]

// ============================================================================
// SAMPLE ACCREDITATION APPLICATIONS
// ============================================================================

export const SAMPLE_APPLICATIONS: AccreditationApplication[] = [
  {
    id: 'app-001',
    institutionId: 'inst-001',
    applicationNumber: 'NAAC/2025/TN/001234',
    applicationDate: '2025-06-15',
    cycle: 'third',
    cycleNumber: 3,
    binaryStatus: 'accredited',
    binaryAssessmentDate: '2025-09-20',
    binaryValidityStart: '2025-10-01',
    binaryValidityEnd: '2028-09-30',
    mbglLevel: 'level_4',
    mbglAssessmentDate: '2025-10-05',
    mbglScore: 4.2,
    mbglValidityStart: '2025-10-15',
    mbglValidityEnd: '2028-10-14',
    previousGrade: 'A++',
    previousCgpa: 3.75,
    previousValidityEnd: '2025-05-31',
    currentPhase: 'completed',
    selfStudyScore: 92.5,
    aiAssessmentScore: 88.0,
    stakeholderScore: 90.0,
    finalScore: 90.2,
    notes: 'Excellent performance in all criteria. Strong research output.',
  },
  {
    id: 'app-002',
    institutionId: 'inst-002',
    applicationNumber: 'NAAC/2025/KA/002567',
    applicationDate: '2025-08-01',
    cycle: 'first',
    cycleNumber: 1,
    binaryStatus: 'under_review',
    currentPhase: 'peer_review',
    selfStudyScore: 78.5,
    aiAssessmentScore: 75.0,
    mbglLevel: 'not_assessed',
    notes: 'First cycle application. AI assessment completed, awaiting peer review.',
  },
  {
    id: 'app-003',
    institutionId: 'inst-003',
    applicationNumber: 'NAAC/2025/TS/003891',
    applicationDate: '2025-04-10',
    cycle: 'fourth',
    cycleNumber: 4,
    binaryStatus: 'accredited',
    binaryAssessmentDate: '2025-07-15',
    binaryValidityStart: '2025-08-01',
    binaryValidityEnd: '2028-07-31',
    mbglLevel: 'level_5',
    mbglAssessmentDate: '2025-08-10',
    mbglScore: 4.75,
    mbglValidityStart: '2025-08-20',
    mbglValidityEnd: '2028-08-19',
    previousGrade: 'A++',
    previousCgpa: 3.85,
    previousValidityEnd: '2025-03-31',
    currentPhase: 'completed',
    selfStudyScore: 96.0,
    aiAssessmentScore: 94.5,
    stakeholderScore: 95.0,
    finalScore: 95.2,
    notes: 'Excellence in all dimensions. National ranking in top 10.',
  },
  {
    id: 'app-004',
    institutionId: 'inst-004',
    applicationNumber: 'NAAC/2025/MH/004123',
    applicationDate: '2025-07-20',
    cycle: 'second',
    cycleNumber: 2,
    binaryStatus: 'accredited',
    binaryAssessmentDate: '2025-11-10',
    binaryValidityStart: '2025-11-20',
    binaryValidityEnd: '2028-11-19',
    mbglLevel: 'level_3',
    mbglAssessmentDate: '2025-11-25',
    mbglScore: 3.4,
    mbglValidityStart: '2025-12-01',
    mbglValidityEnd: '2028-11-30',
    previousGrade: 'A',
    previousCgpa: 3.25,
    previousValidityEnd: '2025-06-30',
    currentPhase: 'completed',
    selfStudyScore: 82.0,
    aiAssessmentScore: 80.0,
    stakeholderScore: 81.0,
    finalScore: 81.0,
    notes: 'Good improvement from previous cycle.',
  },
  {
    id: 'app-005',
    institutionId: 'inst-005',
    applicationNumber: 'NAAC/2025/DL/005678',
    applicationDate: '2025-09-01',
    cycle: 'first',
    cycleNumber: 1,
    binaryStatus: 'applied',
    currentPhase: 'ssr_submission',
    selfStudyScore: 72.0,
    mbglLevel: 'not_assessed',
    notes: 'First cycle. SSR preparation in progress.',
  },
]

// ============================================================================
// ATTRIBUTES DEFINITION (10 Attributes Framework)
// ============================================================================

export const ATTRIBUTES_DEFINITION = [
  { number: 1, attribute: 'curricular_aspects', name: 'Curricular Aspects', weightage: 10.0, maxScore: 100 },
  { number: 2, attribute: 'teaching_learning', name: 'Teaching-Learning & Evaluation', weightage: 15.0, maxScore: 100 },
  { number: 3, attribute: 'research_innovation', name: 'Research, Innovations & Extension', weightage: 15.0, maxScore: 100 },
  { number: 4, attribute: 'infrastructure', name: 'Infrastructure & Learning Resources', weightage: 10.0, maxScore: 100 },
  { number: 5, attribute: 'student_support', name: 'Student Support & Progression', weightage: 10.0, maxScore: 100 },
  { number: 6, attribute: 'governance', name: 'Governance, Leadership & Management', weightage: 10.0, maxScore: 100 },
  { number: 7, attribute: 'institutional_values', name: 'Institutional Values & Best Practices', weightage: 10.0, maxScore: 100 },
  { number: 8, attribute: 'nep_alignment', name: 'NEP 2020 Alignment', weightage: 8.0, maxScore: 100 },
  { number: 9, attribute: 'digital_infrastructure', name: 'Digital Infrastructure & ICT', weightage: 7.0, maxScore: 100 },
  { number: 10, attribute: 'sustainability', name: 'Sustainability & Environment', weightage: 5.0, maxScore: 100 },
]

// ============================================================================
// SAMPLE ATTRIBUTE SCORES
// ============================================================================

// Scores for Application 1 (Bharath Institute - Level 4)
export const SAMPLE_ATTRIBUTE_SCORES_APP1: AttributeScore[] = [
  { attribute: 'curricular_aspects', attributeName: 'Curricular Aspects', weightage: 10, maxScore: 100, selfScore: 88, verifiedScore: 86, finalScore: 86, aiScore: 85, aiConfidence: 0.92, evidenceCount: 45, evidenceVerified: 42, isComplete: true, aiFeedback: 'Strong curriculum design with good industry alignment. Minor gaps in interdisciplinary courses.' },
  { attribute: 'teaching_learning', attributeName: 'Teaching-Learning & Evaluation', weightage: 15, maxScore: 100, selfScore: 92, verifiedScore: 90, finalScore: 90, aiScore: 89, aiConfidence: 0.95, evidenceCount: 68, evidenceVerified: 65, isComplete: true, aiFeedback: 'Excellent teaching practices with innovative pedagogy. OBE implementation is exemplary.' },
  { attribute: 'research_innovation', attributeName: 'Research, Innovations & Extension', weightage: 15, maxScore: 100, selfScore: 95, verifiedScore: 94, finalScore: 94, aiScore: 93, aiConfidence: 0.94, evidenceCount: 120, evidenceVerified: 118, isComplete: true, aiFeedback: 'Outstanding research output. 150+ publications annually. Strong patent portfolio.' },
  { attribute: 'infrastructure', attributeName: 'Infrastructure & Learning Resources', weightage: 10, maxScore: 100, selfScore: 90, verifiedScore: 88, finalScore: 88, aiScore: 87, aiConfidence: 0.91, evidenceCount: 35, evidenceVerified: 33, isComplete: true, aiFeedback: 'Modern infrastructure with 100% digital classrooms. Library resources adequate.' },
  { attribute: 'student_support', attributeName: 'Student Support & Progression', weightage: 10, maxScore: 100, selfScore: 87, verifiedScore: 85, finalScore: 85, aiScore: 84, aiConfidence: 0.90, evidenceCount: 55, evidenceVerified: 52, isComplete: true, aiFeedback: 'Good student support systems. Placement rate above 95%. Mentoring programs effective.' },
  { attribute: 'governance', attributeName: 'Governance, Leadership & Management', weightage: 10, maxScore: 100, selfScore: 91, verifiedScore: 89, finalScore: 89, aiScore: 88, aiConfidence: 0.93, evidenceCount: 40, evidenceVerified: 38, isComplete: true, aiFeedback: 'Strong governance structure with transparent processes. IQAC very active.' },
  { attribute: 'institutional_values', attributeName: 'Institutional Values & Best Practices', weightage: 10, maxScore: 100, selfScore: 93, verifiedScore: 92, finalScore: 92, aiScore: 91, aiConfidence: 0.94, evidenceCount: 30, evidenceVerified: 29, isComplete: true, aiFeedback: 'Excellent institutional culture. Gender sensitivity and inclusivity well established.' },
  { attribute: 'nep_alignment', attributeName: 'NEP 2020 Alignment', weightage: 8, maxScore: 100, selfScore: 85, verifiedScore: 83, finalScore: 83, aiScore: 82, aiConfidence: 0.88, evidenceCount: 25, evidenceVerified: 23, isComplete: true, aiFeedback: 'Good progress on NEP implementation. Multiple entry/exit being implemented.' },
  { attribute: 'digital_infrastructure', attributeName: 'Digital Infrastructure & ICT', weightage: 7, maxScore: 100, selfScore: 94, verifiedScore: 93, finalScore: 93, aiScore: 92, aiConfidence: 0.96, evidenceCount: 28, evidenceVerified: 27, isComplete: true, aiFeedback: 'Excellent ICT infrastructure. ERP fully integrated. LMS widely used.' },
  { attribute: 'sustainability', attributeName: 'Sustainability & Environment', weightage: 5, maxScore: 100, selfScore: 88, verifiedScore: 86, finalScore: 86, aiScore: 85, aiConfidence: 0.89, evidenceCount: 20, evidenceVerified: 19, isComplete: true, aiFeedback: 'Good sustainability initiatives. Solar power covers 40% needs. Green audit conducted.' },
]

// Scores for Application 2 (Vidya Engineering - Under Review)
export const SAMPLE_ATTRIBUTE_SCORES_APP2: AttributeScore[] = [
  { attribute: 'curricular_aspects', attributeName: 'Curricular Aspects', weightage: 10, maxScore: 100, selfScore: 75, aiScore: 72, aiConfidence: 0.85, evidenceCount: 30, evidenceVerified: 15, isComplete: false, aiFeedback: 'Curriculum needs updating. Industry alignment can be improved.' },
  { attribute: 'teaching_learning', attributeName: 'Teaching-Learning & Evaluation', weightage: 15, maxScore: 100, selfScore: 78, aiScore: 75, aiConfidence: 0.87, evidenceCount: 45, evidenceVerified: 20, isComplete: false, aiFeedback: 'Teaching practices satisfactory. OBE implementation in progress.' },
  { attribute: 'research_innovation', attributeName: 'Research, Innovations & Extension', weightage: 15, maxScore: 100, selfScore: 70, aiScore: 68, aiConfidence: 0.82, evidenceCount: 50, evidenceVerified: 25, isComplete: false, aiFeedback: 'Research output needs improvement. Few publications per faculty.' },
  { attribute: 'infrastructure', attributeName: 'Infrastructure & Learning Resources', weightage: 10, maxScore: 100, selfScore: 80, aiScore: 78, aiConfidence: 0.88, evidenceCount: 25, evidenceVerified: 12, isComplete: false, aiFeedback: 'Infrastructure adequate. Some labs need upgradation.' },
  { attribute: 'student_support', attributeName: 'Student Support & Progression', weightage: 10, maxScore: 100, selfScore: 76, aiScore: 74, aiConfidence: 0.84, evidenceCount: 35, evidenceVerified: 18, isComplete: false, aiFeedback: 'Student support systems functional. Placement cell needs strengthening.' },
  { attribute: 'governance', attributeName: 'Governance, Leadership & Management', weightage: 10, maxScore: 100, selfScore: 82, aiScore: 80, aiConfidence: 0.89, evidenceCount: 28, evidenceVerified: 14, isComplete: false, aiFeedback: 'Governance structure in place. IQAC functioning.' },
  { attribute: 'institutional_values', attributeName: 'Institutional Values & Best Practices', weightage: 10, maxScore: 100, selfScore: 79, aiScore: 77, aiConfidence: 0.86, evidenceCount: 22, evidenceVerified: 11, isComplete: false, aiFeedback: 'Good institutional values. Some best practices documented.' },
  { attribute: 'nep_alignment', attributeName: 'NEP 2020 Alignment', weightage: 8, maxScore: 100, selfScore: 72, aiScore: 70, aiConfidence: 0.80, evidenceCount: 18, evidenceVerified: 9, isComplete: false, aiFeedback: 'NEP implementation started. More work needed.' },
  { attribute: 'digital_infrastructure', attributeName: 'Digital Infrastructure & ICT', weightage: 7, maxScore: 100, selfScore: 85, aiScore: 83, aiConfidence: 0.91, evidenceCount: 20, evidenceVerified: 10, isComplete: false, aiFeedback: 'Good ICT infrastructure. WiFi campus-wide.' },
  { attribute: 'sustainability', attributeName: 'Sustainability & Environment', weightage: 5, maxScore: 100, selfScore: 74, aiScore: 72, aiConfidence: 0.83, evidenceCount: 15, evidenceVerified: 7, isComplete: false, aiFeedback: 'Basic sustainability measures. Scope for improvement.' },
]

// Scores for Application 3 (National College - Level 5)
export const SAMPLE_ATTRIBUTE_SCORES_APP3: AttributeScore[] = [
  { attribute: 'curricular_aspects', attributeName: 'Curricular Aspects', weightage: 10, maxScore: 100, selfScore: 96, verifiedScore: 95, finalScore: 95, aiScore: 94, aiConfidence: 0.97, evidenceCount: 60, evidenceVerified: 60, isComplete: true, aiFeedback: 'Exceptional curriculum with global standards. Industry 4.0 integrated.' },
  { attribute: 'teaching_learning', attributeName: 'Teaching-Learning & Evaluation', weightage: 15, maxScore: 100, selfScore: 97, verifiedScore: 96, finalScore: 96, aiScore: 95, aiConfidence: 0.98, evidenceCount: 85, evidenceVerified: 85, isComplete: true, aiFeedback: 'World-class teaching practices. International faculty exchanges.' },
  { attribute: 'research_innovation', attributeName: 'Research, Innovations & Extension', weightage: 15, maxScore: 100, selfScore: 98, verifiedScore: 97, finalScore: 97, aiScore: 96, aiConfidence: 0.98, evidenceCount: 150, evidenceVerified: 150, isComplete: true, aiFeedback: '200+ publications annually. 15 patents. Research funding >10 Cr.' },
  { attribute: 'infrastructure', attributeName: 'Infrastructure & Learning Resources', weightage: 10, maxScore: 100, selfScore: 95, verifiedScore: 94, finalScore: 94, aiScore: 93, aiConfidence: 0.96, evidenceCount: 45, evidenceVerified: 45, isComplete: true, aiFeedback: 'State-of-the-art infrastructure. Smart campus fully implemented.' },
  { attribute: 'student_support', attributeName: 'Student Support & Progression', weightage: 10, maxScore: 100, selfScore: 94, verifiedScore: 93, finalScore: 93, aiScore: 92, aiConfidence: 0.95, evidenceCount: 70, evidenceVerified: 70, isComplete: true, aiFeedback: '100% placement. Average package 12 LPA. Excellent mentoring.' },
  { attribute: 'governance', attributeName: 'Governance, Leadership & Management', weightage: 10, maxScore: 100, selfScore: 96, verifiedScore: 95, finalScore: 95, aiScore: 94, aiConfidence: 0.97, evidenceCount: 50, evidenceVerified: 50, isComplete: true, aiFeedback: 'Visionary leadership. Transparent governance. Strategic planning excellent.' },
  { attribute: 'institutional_values', attributeName: 'Institutional Values & Best Practices', weightage: 10, maxScore: 100, selfScore: 97, verifiedScore: 96, finalScore: 96, aiScore: 95, aiConfidence: 0.97, evidenceCount: 40, evidenceVerified: 40, isComplete: true, aiFeedback: 'Model institution for values. Multiple best practices nationally recognized.' },
  { attribute: 'nep_alignment', attributeName: 'NEP 2020 Alignment', weightage: 8, maxScore: 100, selfScore: 93, verifiedScore: 92, finalScore: 92, aiScore: 91, aiConfidence: 0.94, evidenceCount: 35, evidenceVerified: 35, isComplete: true, aiFeedback: 'Full NEP implementation. ABC credits operational. Multi-disciplinary programs.' },
  { attribute: 'digital_infrastructure', attributeName: 'Digital Infrastructure & ICT', weightage: 7, maxScore: 100, selfScore: 98, verifiedScore: 97, finalScore: 97, aiScore: 96, aiConfidence: 0.98, evidenceCount: 38, evidenceVerified: 38, isComplete: true, aiFeedback: 'Digital excellence. AI/ML labs. Cybersecurity center.' },
  { attribute: 'sustainability', attributeName: 'Sustainability & Environment', weightage: 5, maxScore: 100, selfScore: 95, verifiedScore: 94, finalScore: 94, aiScore: 93, aiConfidence: 0.96, evidenceCount: 28, evidenceVerified: 28, isComplete: true, aiFeedback: 'Green campus. Zero carbon footprint. Sustainability leadership.' },
]

// ============================================================================
// SAMPLE MBGL ASSESSMENTS
// ============================================================================

export const SAMPLE_MBGL_ASSESSMENTS: MBGLAssessment[] = [
  {
    id: 'mbgl-001',
    applicationId: 'app-001',
    assessmentYear: '2025-26',
    assessmentDate: '2025-10-05',
    leadershipMaturity: 4,
    processMaturity: 4,
    peopleMaturity: 5,
    technologyMaturity: 5,
    outcomeMaturity: 4,
    innovationMaturity: 4,
    stakeholderMaturity: 4,
    sustainabilityMaturity: 4,
    averageMaturity: 4.25,
    weightedScore: 85.0,
    recommendedLevel: 'level_4',
    finalLevel: 'level_4',
    level1CriteriaMet: true,
    level2CriteriaMet: true,
    level3CriteriaMet: true,
    level4CriteriaMet: true,
    level5CriteriaMet: false,
    strengths: [
      'Strong technology infrastructure with 100% digital classrooms',
      'Excellent faculty development programs',
      'High research output with 150+ publications annually',
      'Industry partnerships with 25+ companies',
      'Student placement rate above 95%',
    ],
    improvementsNeeded: [
      'Increase international collaborations',
      'Enhance sustainability initiatives',
      'Expand community outreach programs',
      'Improve alumni engagement',
    ],
    actionPlan: 'Focus on establishing 5 new international MOUs, implement solar power for 50% campus, and launch 3 new community extension programs by next assessment cycle.',
    assessedBy: 'Dr. Ramesh Kumar',
    verifiedBy: 'Prof. Sunita Sharma',
  },
  {
    id: 'mbgl-002',
    applicationId: 'app-003',
    assessmentYear: '2025-26',
    assessmentDate: '2025-08-10',
    leadershipMaturity: 5,
    processMaturity: 5,
    peopleMaturity: 5,
    technologyMaturity: 5,
    outcomeMaturity: 5,
    innovationMaturity: 4,
    stakeholderMaturity: 5,
    sustainabilityMaturity: 4,
    averageMaturity: 4.75,
    weightedScore: 95.0,
    recommendedLevel: 'level_5',
    finalLevel: 'level_5',
    level1CriteriaMet: true,
    level2CriteriaMet: true,
    level3CriteriaMet: true,
    level4CriteriaMet: true,
    level5CriteriaMet: true,
    strengths: [
      'National ranking in top 10 institutions',
      'International accreditations (ABET, AACSB)',
      '200+ research publications annually',
      '50+ international collaborations',
      '100% placement with average package 12 LPA',
      'Green campus with zero carbon footprint',
      'Industry-sponsored research centers',
    ],
    improvementsNeeded: [
      'Further enhance innovation ecosystem',
      'Expand patent portfolio',
    ],
    actionPlan: 'Continue excellence trajectory. Target 10 new patents, establish innovation hub, and achieve carbon negative status by 2027.',
    assessedBy: 'Dr. Anil Verma',
    verifiedBy: 'Prof. Lakshmi Narayanan',
  },
  {
    id: 'mbgl-003',
    applicationId: 'app-004',
    assessmentYear: '2025-26',
    assessmentDate: '2025-11-25',
    leadershipMaturity: 3,
    processMaturity: 4,
    peopleMaturity: 3,
    technologyMaturity: 4,
    outcomeMaturity: 3,
    innovationMaturity: 3,
    stakeholderMaturity: 4,
    sustainabilityMaturity: 3,
    averageMaturity: 3.38,
    weightedScore: 75.0,
    recommendedLevel: 'level_3',
    finalLevel: 'level_3',
    level1CriteriaMet: true,
    level2CriteriaMet: true,
    level3CriteriaMet: true,
    level4CriteriaMet: false,
    level5CriteriaMet: false,
    strengths: [
      'Good governance and process documentation',
      'Strong industry connections',
      'Active stakeholder engagement',
      'Modern digital infrastructure',
    ],
    improvementsNeeded: [
      'Enhance research output',
      'Improve faculty qualifications',
      'Strengthen innovation ecosystem',
      'Develop sustainability practices',
      'Increase placement rates',
    ],
    actionPlan: 'Focus on faculty development with PhD targets, establish research cells in each department, and implement green campus initiatives.',
    assessedBy: 'Dr. Priya Menon',
    verifiedBy: 'Prof. Rajesh Singh',
  },
]

// ============================================================================
// SAMPLE MBGL LEVEL CRITERIA
// ============================================================================

export const MBGL_LEVEL_CRITERIA: MBGLLevelCriteria[] = [
  {
    id: 'mbgl-level-1',
    level: 'level_1',
    levelNumber: 1,
    levelName: 'Basic Compliance',
    levelDescription: 'Institution meets basic accreditation requirements and demonstrates fundamental quality processes.',
    minBinaryStatus: true,
    minMaturityScore: 1.0,
    mandatoryCriteria: [
      'Valid institutional recognition',
      'Basic infrastructure in place',
      'Qualified faculty as per norms',
      'Functional governance structure',
    ],
    optionalCriteria: [],
    optionalCriteriaMin: 0,
    validityYears: 3,
    recognitionBenefits: [
      'Basic accreditation certificate',
      'Eligible for government grants',
      'Can apply for MBGL Level 2 after 1 year',
    ],
    isActive: true,
  },
  {
    id: 'mbgl-level-2',
    level: 'level_2',
    levelNumber: 2,
    levelName: 'Developing',
    levelDescription: 'Institution shows developing quality practices with documented processes and improvement initiatives.',
    minBinaryStatus: true,
    minMaturityScore: 2.0,
    mandatoryCriteria: [
      'All Level 1 criteria',
      'IQAC functioning effectively',
      'Student feedback system in place',
      'Faculty development programs',
      'Basic research activities',
    ],
    optionalCriteria: [
      'Industry collaborations',
      'Community extension activities',
      'Digital learning resources',
    ],
    optionalCriteriaMin: 1,
    validityYears: 3,
    recognitionBenefits: [
      'Enhanced accreditation certificate',
      'Priority for UGC schemes',
      'Eligible for autonomy consideration',
      'Can apply for MBGL Level 3 after 1 year',
    ],
    isActive: true,
  },
  {
    id: 'mbgl-level-3',
    level: 'level_3',
    levelNumber: 3,
    levelName: 'Established',
    levelDescription: 'Institution has established quality systems with consistent outcomes and stakeholder satisfaction.',
    minBinaryStatus: true,
    minMaturityScore: 3.0,
    mandatoryCriteria: [
      'All Level 2 criteria',
      'Outcome-based education implemented',
      'Research publications track record',
      'Industry partnerships established',
      'Student placement cell active',
      'Alumni association functional',
    ],
    optionalCriteria: [
      'International collaborations',
      'Patent/IP activities',
      'Incubation center',
      'Green campus initiatives',
    ],
    optionalCriteriaMin: 2,
    validityYears: 3,
    recognitionBenefits: [
      'Premium accreditation status',
      'Autonomy fast-track',
      'Increased intake permitted',
      'International recognition eligible',
      'Can apply for MBGL Level 4',
    ],
    isActive: true,
  },
  {
    id: 'mbgl-level-4',
    level: 'level_4',
    levelNumber: 4,
    levelName: 'Advanced',
    levelDescription: 'Institution demonstrates advanced quality practices with innovation, research excellence, and national recognition.',
    minBinaryStatus: true,
    minMaturityScore: 4.0,
    mandatoryCriteria: [
      'All Level 3 criteria',
      'Research centers established',
      'PhD programs running',
      'International collaborations active',
      'Innovation ecosystem in place',
      'High placement rate (>80%)',
      'NEP 2020 implementation advanced',
    ],
    optionalCriteria: [
      'International accreditation',
      'Funded research projects >5 Cr',
      'Patents granted',
      'Industry-sponsored labs',
      'Start-up incubation success',
    ],
    optionalCriteriaMin: 3,
    validityYears: 3,
    recognitionBenefits: [
      'National excellence recognition',
      'Research university eligibility',
      'International student recruitment',
      'Government policy advisory roles',
      'Can apply for MBGL Level 5',
    ],
    isActive: true,
  },
  {
    id: 'mbgl-level-5',
    level: 'level_5',
    levelNumber: 5,
    levelName: 'Excellence',
    levelDescription: 'Institution achieves excellence in all dimensions with global standards, innovation leadership, and transformative impact.',
    minBinaryStatus: true,
    minMaturityScore: 4.5,
    mandatoryCriteria: [
      'All Level 4 criteria',
      'Global ranking presence',
      'International accreditations (ABET/AACSB/NBA Tier-1)',
      'Research funding >10 Cr annually',
      'Patent portfolio >10',
      'International faculty exchange',
      'Sustainability leadership',
      'Industry 4.0 integration',
    ],
    optionalCriteria: [
      'Top 100 global ranking',
      'Nobel/Turing laureate association',
      'Major innovation/discovery',
      'National policy contribution',
    ],
    optionalCriteriaMin: 1,
    validityYears: 3,
    recognitionBenefits: [
      'Institution of Eminence pathway',
      'Global brand recognition',
      'International research grants',
      'Government flagship programs partner',
      'Policy making participation',
      'Mentorship role for other institutions',
    ],
    isActive: true,
  },
]

// ============================================================================
// SAMPLE ACCREDITATION TIMELINES
// ============================================================================

export const SAMPLE_TIMELINES: Record<string, TimelineMilestone[]> = {
  'app-001': [
    { milestoneName: 'Application Submitted', milestoneType: 'submission', plannedDate: '2025-06-15', actualDate: '2025-06-15', isCompleted: true },
    { milestoneName: 'IIQA Approved', milestoneType: 'approval', plannedDate: '2025-06-30', actualDate: '2025-06-28', isCompleted: true },
    { milestoneName: 'SSR Submitted', milestoneType: 'submission', plannedDate: '2025-07-31', actualDate: '2025-07-25', isCompleted: true },
    { milestoneName: 'AI Assessment Completed', milestoneType: 'assessment', plannedDate: '2025-08-15', actualDate: '2025-08-10', isCompleted: true },
    { milestoneName: 'DVV Clarifications', milestoneType: 'clarification', plannedDate: '2025-08-31', actualDate: '2025-08-28', isCompleted: true },
    { milestoneName: 'Peer Review Visit', milestoneType: 'review', plannedDate: '2025-09-15', actualDate: '2025-09-18', isCompleted: true },
    { milestoneName: 'Binary Decision', milestoneType: 'decision', plannedDate: '2025-09-25', actualDate: '2025-09-20', isCompleted: true },
    { milestoneName: 'MBGL Assessment', milestoneType: 'assessment', plannedDate: '2025-10-10', actualDate: '2025-10-05', isCompleted: true },
    { milestoneName: 'Final Certificate Issued', milestoneType: 'certificate', plannedDate: '2025-10-20', actualDate: '2025-10-15', isCompleted: true },
  ],
  'app-002': [
    { milestoneName: 'Application Submitted', milestoneType: 'submission', plannedDate: '2025-08-01', actualDate: '2025-08-01', isCompleted: true },
    { milestoneName: 'IIQA Approved', milestoneType: 'approval', plannedDate: '2025-08-15', actualDate: '2025-08-12', isCompleted: true },
    { milestoneName: 'SSR Submitted', milestoneType: 'submission', plannedDate: '2025-09-15', actualDate: '2025-09-10', isCompleted: true },
    { milestoneName: 'AI Assessment Completed', milestoneType: 'assessment', plannedDate: '2025-09-30', actualDate: '2025-09-28', isCompleted: true },
    { milestoneName: 'DVV Clarifications', milestoneType: 'clarification', plannedDate: '2025-10-15', isCompleted: false },
    { milestoneName: 'Peer Review Visit', milestoneType: 'review', plannedDate: '2025-11-01', isCompleted: false },
    { milestoneName: 'Binary Decision', milestoneType: 'decision', plannedDate: '2025-11-15', isCompleted: false },
    { milestoneName: 'MBGL Assessment', milestoneType: 'assessment', plannedDate: '2025-11-25', isCompleted: false },
    { milestoneName: 'Final Certificate Issued', milestoneType: 'certificate', plannedDate: '2025-12-05', isCompleted: false },
  ],
  'app-003': [
    { milestoneName: 'Application Submitted', milestoneType: 'submission', plannedDate: '2025-04-10', actualDate: '2025-04-10', isCompleted: true },
    { milestoneName: 'IIQA Approved', milestoneType: 'approval', plannedDate: '2025-04-25', actualDate: '2025-04-22', isCompleted: true },
    { milestoneName: 'SSR Submitted', milestoneType: 'submission', plannedDate: '2025-05-25', actualDate: '2025-05-20', isCompleted: true },
    { milestoneName: 'AI Assessment Completed', milestoneType: 'assessment', plannedDate: '2025-06-10', actualDate: '2025-06-05', isCompleted: true },
    { milestoneName: 'DVV Clarifications', milestoneType: 'clarification', plannedDate: '2025-06-25', actualDate: '2025-06-20', isCompleted: true },
    { milestoneName: 'Peer Review Visit', milestoneType: 'review', plannedDate: '2025-07-10', actualDate: '2025-07-08', isCompleted: true },
    { milestoneName: 'Binary Decision', milestoneType: 'decision', plannedDate: '2025-07-20', actualDate: '2025-07-15', isCompleted: true },
    { milestoneName: 'MBGL Assessment', milestoneType: 'assessment', plannedDate: '2025-08-15', actualDate: '2025-08-10', isCompleted: true },
    { milestoneName: 'Final Certificate Issued', milestoneType: 'certificate', plannedDate: '2025-08-25', actualDate: '2025-08-20', isCompleted: true },
  ],
}

// ============================================================================
// DASHBOARD STATISTICS
// ============================================================================

export const DASHBOARD_STATS = {
  totalApplications: 5,
  accredited: 3,
  underReview: 1,
  applied: 1,
  notAccredited: 0,
  mbglDistribution: {
    level_1: 0,
    level_2: 0,
    level_3: 1,
    level_4: 1,
    level_5: 1,
    not_assessed: 2,
  },
  averageMaturityScore: 4.13,
  attributePerformance: {
    curricular_aspects: 85.3,
    teaching_learning: 87.0,
    research_innovation: 86.3,
    infrastructure: 86.7,
    student_support: 84.0,
    governance: 86.3,
    institutional_values: 88.0,
    nep_alignment: 81.7,
    digital_infrastructure: 91.0,
    sustainability: 84.7,
  },
  completionRate: 60.0,
  avgProcessingDays: 95,
  cycleDistribution: {
    first: 2,
    second: 1,
    third: 1,
    fourth: 1,
  },
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function getInstitutionById(id: string): Institution | undefined {
  return SAMPLE_INSTITUTIONS.find(inst => inst.id === id)
}

export function getApplicationById(id: string): AccreditationApplication | undefined {
  return SAMPLE_APPLICATIONS.find(app => app.id === id)
}

export function getAttributeScoresForApplication(applicationId: string): AttributeScore[] {
  switch (applicationId) {
    case 'app-001':
      return SAMPLE_ATTRIBUTE_SCORES_APP1
    case 'app-002':
      return SAMPLE_ATTRIBUTE_SCORES_APP2
    case 'app-003':
      return SAMPLE_ATTRIBUTE_SCORES_APP3
    default:
      return []
  }
}

export function getMBGLAssessmentForApplication(applicationId: string): MBGLAssessment | undefined {
  return SAMPLE_MBGL_ASSESSMENTS.find(assessment => assessment.applicationId === applicationId)
}

export function getTimelineForApplication(applicationId: string): TimelineMilestone[] {
  return SAMPLE_TIMELINES[applicationId] || []
}

export function getBinaryStatusLabel(status: BinaryStatus): string {
  const labels: Record<BinaryStatus, string> = {
    not_applied: 'Not Applied',
    applied: 'Applied',
    under_review: 'Under Review',
    accredited: 'Accredited',
    not_accredited: 'Not Accredited',
    expired: 'Expired',
  }
  return labels[status]
}

export function getMBGLLevelLabel(level: MBGLLevel): string {
  const labels: Record<MBGLLevel, string> = {
    not_assessed: 'Not Assessed',
    level_1: 'Level 1 - Basic Compliance',
    level_2: 'Level 2 - Developing',
    level_3: 'Level 3 - Established',
    level_4: 'Level 4 - Advanced',
    level_5: 'Level 5 - Excellence',
  }
  return labels[level]
}

export function getPhaseLabel(phase: AssessmentPhase): string {
  const labels: Record<AssessmentPhase, string> = {
    self_study: 'Self Study',
    ssr_submission: 'SSR Submission',
    ai_assessment: 'AI Assessment',
    dvv_clarification: 'DVV Clarification',
    peer_review: 'Peer Review',
    decision: 'Decision',
    completed: 'Completed',
  }
  return labels[phase]
}

export function calculateWeightedScore(scores: AttributeScore[]): number {
  let totalWeight = 0
  let weightedSum = 0

  scores.forEach(score => {
    const finalScore = score.finalScore || score.verifiedScore || score.selfScore
    weightedSum += finalScore * score.weightage
    totalWeight += score.weightage
  })

  return totalWeight > 0 ? weightedSum / totalWeight : 0
}

export function determineMBGLLevel(averageMaturity: number): MBGLLevel {
  if (averageMaturity >= 4.5) return 'level_5'
  if (averageMaturity >= 4.0) return 'level_4'
  if (averageMaturity >= 3.0) return 'level_3'
  if (averageMaturity >= 2.0) return 'level_2'
  if (averageMaturity >= 1.0) return 'level_1'
  return 'not_assessed'
}
