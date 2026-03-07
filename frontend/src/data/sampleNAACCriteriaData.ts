/**
 * Sample Data for NAAC 7 Criteria (700 Marks Total)
 * Comprehensive seed data for all criteria with metrics, KPIs, and evidence
 */

// ============================================================================
// TYPE DEFINITIONS
// ============================================================================

export interface KeyIndicator {
  id: string
  name: string
  marks: number
}

export interface MetricData {
  metric: string
  data: Record<string, any>
  evidence?: string[]
}

export interface CriterionData {
  criterion_id: string
  criterion_name: string
  max_marks: number
  key_indicators: KeyIndicator[]
  sample_metrics: Record<string, MetricData>
  score: number
  percentage: number
}

export interface CriterionScore {
  marks: number
  score: number
  percentage: number
}

export interface NAACStrengths {
  overall_percentage: number
  strengths: string[]
  areas_for_improvement: string[]
}

// ============================================================================
// CRITERION 1: CURRICULAR ASPECTS (150 Marks)
// ============================================================================

export const CRITERION_1_DATA: CriterionData = {
  criterion_id: 'C1',
  criterion_name: 'Curricular Aspects',
  max_marks: 150,
  key_indicators: [
    { id: '1.1', name: 'Curricular Planning and Implementation', marks: 50 },
    { id: '1.2', name: 'Academic Flexibility', marks: 50 },
    { id: '1.3', name: 'Curriculum Enrichment', marks: 30 },
    { id: '1.4', name: 'Feedback System', marks: 20 },
  ],
  sample_metrics: {
    '1.1.1': {
      metric: 'Institution ensures effective curriculum planning and delivery',
      data: {
        curriculum_revision_year: '2023-24',
        programs_revised: 45,
        total_programs: 52,
        revision_percentage: 86.5,
        bos_meetings_held: 24,
        academic_council_meetings: 4,
      },
      evidence: [
        'Minutes of BoS meetings',
        'Academic Council resolutions',
        'Curriculum revision documents',
        'Program structure documents',
      ],
    },
    '1.2.1': {
      metric: 'Number of Add on/Certificate programs offered',
      data: {
        certificate_programs: 28,
        diploma_programs: 12,
        value_added_courses: 35,
        mooc_courses_integrated: 45,
        students_enrolled: 2850,
      },
      evidence: [
        'List of certificate programs',
        'Course completion certificates',
        'Student enrollment data',
      ],
    },
    '1.2.2': {
      metric: 'Percentage of students enrolled in Certificate/Add-on programs',
      data: {
        total_students: 5200,
        enrolled_students: 2850,
        percentage: 54.8,
      },
    },
    '1.3.1': {
      metric: 'Institution integrates crosscutting issues',
      data: {
        gender_courses: 8,
        environment_courses: 12,
        human_values_courses: 6,
        professional_ethics_courses: 10,
        total_courses_with_integration: 36,
      },
    },
    '1.4.1': {
      metric: 'Structured feedback system for curriculum',
      data: {
        student_feedback_collected: true,
        teacher_feedback_collected: true,
        employer_feedback_collected: true,
        alumni_feedback_collected: true,
        feedback_analysis_done: true,
        action_taken_reports: 12,
      },
    },
  },
  score: 138,
  percentage: 92.0,
}

// ============================================================================
// CRITERION 2: TEACHING-LEARNING AND EVALUATION (200 Marks)
// ============================================================================

export const CRITERION_2_DATA: CriterionData = {
  criterion_id: 'C2',
  criterion_name: 'Teaching-Learning and Evaluation',
  max_marks: 200,
  key_indicators: [
    { id: '2.1', name: 'Student Enrollment and Profile', marks: 30 },
    { id: '2.2', name: 'Student Teacher Ratio', marks: 20 },
    { id: '2.3', name: 'Teaching-Learning Process', marks: 40 },
    { id: '2.4', name: 'Teacher Profile and Quality', marks: 50 },
    { id: '2.5', name: 'Evaluation Process and Reforms', marks: 30 },
    { id: '2.6', name: 'Student Performance and Learning Outcomes', marks: 30 },
  ],
  sample_metrics: {
    '2.1.1': {
      metric: 'Enrollment percentage',
      data: {
        sanctioned_intake: 1800,
        enrolled_students: 1720,
        enrollment_percentage: 95.6,
      },
    },
    '2.2.1': {
      metric: 'Student-Teacher Ratio',
      data: {
        total_students: 5200,
        total_teachers: 320,
        ratio: '16:1',
      },
    },
    '2.3.1': {
      metric: 'Student-centric methods',
      data: {
        experiential_learning_courses: 45,
        participative_learning_courses: 68,
        problem_solving_courses: 52,
        ict_enabled_courses: 285,
      },
    },
    '2.4.1': {
      metric: 'Percentage of full time teachers with Ph.D.',
      data: {
        phd_teachers: 185,
        total_teachers: 320,
        percentage: 57.8,
      },
    },
    '2.6.2': {
      metric: 'Pass percentage of final year students',
      data: {
        appeared: 1450,
        passed: 1392,
        pass_percentage: 96.0,
        first_class_percentage: 72.5,
      },
    },
  },
  score: 185,
  percentage: 92.5,
}

// ============================================================================
// CRITERION 3: RESEARCH, INNOVATIONS AND EXTENSION (150 Marks)
// ============================================================================

export const CRITERION_3_DATA: CriterionData = {
  criterion_id: 'C3',
  criterion_name: 'Research, Innovations and Extension',
  max_marks: 150,
  key_indicators: [
    { id: '3.1', name: 'Resource Mobilization for Research', marks: 20 },
    { id: '3.2', name: 'Innovation Ecosystem', marks: 20 },
    { id: '3.3', name: 'Research Publications and Awards', marks: 50 },
    { id: '3.4', name: 'Extension Activities', marks: 40 },
    { id: '3.5', name: 'Collaboration', marks: 20 },
  ],
  sample_metrics: {
    '3.1.1': {
      metric: 'Grants received from Government and non-government agencies',
      data: {
        government_grants_rs_lakhs: 485,
        non_government_grants_rs_lakhs: 125,
        total_grants: 610,
        ongoing_projects: 42,
        completed_projects: 28,
      },
    },
    '3.2.1': {
      metric: 'Institution has incubation centre',
      data: {
        incubation_centre: true,
        startups_incubated: 28,
        successful_startups: 12,
        funding_raised_lakhs: 85,
      },
    },
    '3.3.1': {
      metric: 'Research papers published per teacher',
      data: {
        scopus_papers: 285,
        web_of_science_papers: 180,
        ugc_care_papers: 420,
        total_papers: 885,
        papers_per_teacher: 2.77,
      },
    },
    '3.3.3': {
      metric: 'Patents published/awarded',
      data: {
        patents_filed: 28,
        patents_published: 18,
        patents_granted: 8,
        copyrights: 12,
      },
    },
    '3.5.1': {
      metric: 'MoUs with institutions/industries',
      data: {
        academic_mous: 45,
        industry_mous: 35,
        international_mous: 18,
        functional_mous: 85,
      },
    },
  },
  score: 142,
  percentage: 94.7,
}

// ============================================================================
// CRITERION 4: INFRASTRUCTURE AND LEARNING RESOURCES (100 Marks)
// ============================================================================

export const CRITERION_4_DATA: CriterionData = {
  criterion_id: 'C4',
  criterion_name: 'Infrastructure and Learning Resources',
  max_marks: 100,
  key_indicators: [
    { id: '4.1', name: 'Physical Facilities', marks: 30 },
    { id: '4.2', name: 'Library as a Learning Resource', marks: 30 },
    { id: '4.3', name: 'IT Infrastructure', marks: 20 },
    { id: '4.4', name: 'Maintenance of Campus Infrastructure', marks: 20 },
  ],
  sample_metrics: {
    '4.1.1': {
      metric: 'Classrooms and seminar halls with ICT facilities',
      data: {
        total_classrooms: 150,
        ict_enabled_classrooms: 145,
        percentage: 96.7,
        seminar_halls: 12,
        auditoriums: 3,
      },
    },
    '4.2.2': {
      metric: 'Library resources',
      data: {
        total_books: 125000,
        journals_subscribed: 285,
        e_journals: 8500,
        e_books: 45000,
        databases: 12,
      },
    },
    '4.3.1': {
      metric: 'Institution has adequate IT facilities',
      data: {
        computers: 1200,
        computer_student_ratio: '1:4',
        internet_bandwidth_mbps: 1000,
        wifi_coverage_percentage: 100,
      },
    },
  },
  score: 92,
  percentage: 92.0,
}

// ============================================================================
// CRITERION 5: STUDENT SUPPORT AND PROGRESSION (100 Marks)
// ============================================================================

export const CRITERION_5_DATA: CriterionData = {
  criterion_id: 'C5',
  criterion_name: 'Student Support and Progression',
  max_marks: 100,
  key_indicators: [
    { id: '5.1', name: 'Student Support', marks: 30 },
    { id: '5.2', name: 'Student Progression', marks: 30 },
    { id: '5.3', name: 'Student Participation and Activities', marks: 25 },
    { id: '5.4', name: 'Alumni Engagement', marks: 15 },
  ],
  sample_metrics: {
    '5.1.1': {
      metric: 'Students benefited by scholarships and freeships',
      data: {
        government_scholarships: 1250,
        institutional_scholarships: 450,
        total_benefited: 2080,
        total_amount_lakhs: 285,
      },
    },
    '5.1.4': {
      metric: 'Career counselling and placement',
      data: {
        placement_cell_established: true,
        companies_visited: 185,
        students_placed: 1380,
        placement_percentage: 95.2,
        avg_package_lpa: 8.5,
        highest_package_lpa: 45,
      },
    },
    '5.2.1': {
      metric: 'Students qualifying state/national level examinations',
      data: {
        net_qualified: 28,
        gate_qualified: 85,
        civil_services_qualified: 5,
      },
    },
    '5.4.1': {
      metric: 'Alumni association registered and functional',
      data: {
        alumni_registered: true,
        active_members: 8500,
        chapters: 12,
        annual_meets: 4,
      },
    },
  },
  score: 88,
  percentage: 88.0,
}

// ============================================================================
// CRITERION 6: GOVERNANCE, LEADERSHIP AND MANAGEMENT (100 Marks)
// ============================================================================

export const CRITERION_6_DATA: CriterionData = {
  criterion_id: 'C6',
  criterion_name: 'Governance, Leadership and Management',
  max_marks: 100,
  key_indicators: [
    { id: '6.1', name: 'Institutional Vision and Leadership', marks: 15 },
    { id: '6.2', name: 'Strategy Development and Deployment', marks: 20 },
    { id: '6.3', name: 'Faculty Empowerment Strategies', marks: 25 },
    { id: '6.4', name: 'Financial Management and Resource Mobilization', marks: 20 },
    { id: '6.5', name: 'Internal Quality Assurance System', marks: 20 },
  ],
  sample_metrics: {
    '6.2.2': {
      metric: 'E-governance implementation',
      data: {
        administration: 'ERP System',
        finance_accounts: 'Fully Automated',
        student_admission: 'Online',
        examination: 'Online',
      },
    },
    '6.3.2': {
      metric: 'Faculty development programs',
      data: {
        fdps_organized: 25,
        faculty_attended_fdps: 285,
        refresher_courses: 45,
        total_faculty_days: 850,
      },
    },
    '6.4.2': {
      metric: 'Funds/Grants received from various bodies',
      data: {
        ugc_grants_lakhs: 125,
        aicte_grants_lakhs: 85,
        dst_grants_lakhs: 65,
        total_grants: 355,
      },
    },
    '6.5.2': {
      metric: 'Quality assurance initiatives',
      data: {
        iso_certification: 'ISO 9001:2015',
        nirf_participation: true,
        nirf_rank: 85,
      },
    },
  },
  score: 90,
  percentage: 90.0,
}

// ============================================================================
// CRITERION 7: INSTITUTIONAL VALUES AND BEST PRACTICES (100 Marks)
// ============================================================================

export const CRITERION_7_DATA: CriterionData = {
  criterion_id: 'C7',
  criterion_name: 'Institutional Values and Best Practices',
  max_marks: 100,
  key_indicators: [
    { id: '7.1', name: 'Institutional Values and Social Responsibilities', marks: 50 },
    { id: '7.2', name: 'Best Practices', marks: 30 },
    { id: '7.3', name: 'Institutional Distinctiveness', marks: 20 },
  ],
  sample_metrics: {
    '7.1.1': {
      metric: 'Gender equity measures',
      data: {
        women_cell_functional: true,
        icc_constituted: true,
        gender_sensitization_programs: 15,
        creche_facility: true,
      },
    },
    '7.1.3': {
      metric: 'Environmental consciousness',
      data: {
        green_audit_conducted: true,
        energy_audit_conducted: true,
        rainwater_harvesting: true,
        solar_power_kw: 250,
      },
    },
    '7.2.1': {
      metric: 'Best practices implemented',
      data: {
        best_practice_1: {
          title: 'Industry-Integrated Learning (IIL)',
          objective: 'Bridge academia-industry gap through real-world project experience',
          outcome: 'Enhanced employability and industry readiness',
        },
        best_practice_2: {
          title: 'Green Campus Initiative',
          objective: 'Achieve carbon neutrality and environmental sustainability',
          outcome: 'Reduced carbon footprint by 45%',
        },
      },
    },
    '7.3.1': {
      metric: 'Institutional distinctiveness',
      data: {
        title: 'Center for Innovation and Entrepreneurship',
        achievements: [
          '28 startups incubated',
          '12 successful exits',
          '85 lakhs funding raised',
          '5 patents granted',
        ],
      },
    },
  },
  score: 85,
  percentage: 85.0,
}

// ============================================================================
// CONSOLIDATED NAAC DATA
// ============================================================================

export const NAAC_CRITERIA_DATA: Record<string, CriterionData> = {
  C1: CRITERION_1_DATA,
  C2: CRITERION_2_DATA,
  C3: CRITERION_3_DATA,
  C4: CRITERION_4_DATA,
  C5: CRITERION_5_DATA,
  C6: CRITERION_6_DATA,
  C7: CRITERION_7_DATA,
}

export const NAAC_SUMMARY = {
  total_marks: 700,
  total_score: 820,
  cgpa_equivalent: 3.68,
  grade: 'A++',
  criteria_scores: {
    C1: { marks: 150, score: 138, percentage: 92.0 },
    C2: { marks: 200, score: 185, percentage: 92.5 },
    C3: { marks: 150, score: 142, percentage: 94.7 },
    C4: { marks: 100, score: 92, percentage: 92.0 },
    C5: { marks: 100, score: 88, percentage: 88.0 },
    C6: { marks: 100, score: 90, percentage: 90.0 },
    C7: { marks: 100, score: 85, percentage: 85.0 },
  } as Record<string, CriterionScore>,
  overall_percentage: 91.43,
  strengths: [
    'Excellent research output with high h-index publications',
    'Strong industry collaborations and placement record',
    'Robust ICT infrastructure with 100% digital classrooms',
    'Active IQAC with regular quality initiatives',
    'Comprehensive student support mechanisms',
  ],
  areas_for_improvement: [
    'Increase international collaborations and student exchange',
    'Enhance alumni contribution and engagement',
    'Expand green campus initiatives',
    'Improve entrepreneurship ecosystem',
  ],
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

export function getCriterionData(criterionId: string): CriterionData | undefined {
  return NAAC_CRITERIA_DATA[criterionId]
}

export function getAllCriteriaData(): Record<string, CriterionData> {
  return NAAC_CRITERIA_DATA
}

export function getNAACSummary() {
  return NAAC_SUMMARY
}

export function getCriteriaList() {
  return Object.values(NAAC_CRITERIA_DATA).map(c => ({
    id: c.criterion_id,
    name: c.criterion_name,
    maxMarks: c.max_marks,
    score: c.score,
    percentage: c.percentage,
  }))
}
