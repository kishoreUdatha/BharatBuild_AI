"""
NBA (National Board of Accreditation) - Database Models

This module defines database models for managing NBA Program-Level Accreditation:
- Criterion 1: Vision, Mission & PEOs
- Criterion 2: Program Curriculum & Teaching
- Criterion 3: Course Outcomes & Attainment (Most Critical)
- Criterion 4: Students' Performance
- Criterion 5: Faculty Information & Contributions
- Criterion 6: Facilities & Technical Support
- Criterion 7: Continuous Improvement
- Criteria 8-10: Supporting Criteria
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class ProgramType(str, enum.Enum):
    """Types of academic programs"""
    UG = "ug"  # Undergraduate
    PG = "pg"  # Postgraduate
    DIPLOMA = "diploma"
    INTEGRATED = "integrated"


class AttainmentLevel(str, enum.Enum):
    """Attainment levels for CO/PO"""
    NOT_ATTAINED = "not_attained"
    PARTIALLY_ATTAINED = "partially_attained"
    SUBSTANTIALLY_ATTAINED = "substantially_attained"
    FULLY_ATTAINED = "fully_attained"


class AssessmentMethod(str, enum.Enum):
    """Assessment methods for attainment"""
    DIRECT = "direct"
    INDIRECT = "indirect"


class FeedbackSource(str, enum.Enum):
    """Sources of feedback"""
    STUDENT = "student"
    ALUMNI = "alumni"
    EMPLOYER = "employer"
    FACULTY = "faculty"
    PARENT = "parent"
    INDUSTRY = "industry"


class ActionStatus(str, enum.Enum):
    """Status of action items"""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"


# ==================== MODELS ====================

class ProgramVisionMission(Base):
    """
    Program Vision, Mission & PEOs.
    NBA Criterion 1: Vision, Mission & PEOs
    """
    __tablename__ = "program_vision_mission"

    __table_args__ = (
        Index('ix_program_vision_mission_program', 'program_code'),
        Index('ix_program_vision_mission_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_name = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=False)
    program_type = Column(SQLEnum(ProgramType), nullable=False)
    department = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Vision and Mission
    institute_vision = Column(Text, nullable=True)
    institute_mission = Column(Text, nullable=True)
    department_vision = Column(Text, nullable=True)
    department_mission = Column(Text, nullable=True)
    program_vision = Column(Text, nullable=True)
    program_mission = Column(Text, nullable=True)

    # Program Educational Objectives (PEOs)
    peos = Column(JSON, nullable=True)  # [{"peo_id": "PEO1", "description": "", "keywords": []}]
    peo_mission_mapping = Column(JSON, nullable=True)  # {"PEO1": ["M1", "M2"]}

    # Stakeholder involvement
    stakeholders_consulted = Column(JSON, nullable=True)  # ["industry", "alumni", "faculty"]
    consultation_process = Column(Text, nullable=True)

    # PEO formulation process
    formulation_process = Column(Text, nullable=True)
    review_frequency = Column(String(50), nullable=True)
    last_review_date = Column(Date, nullable=True)
    changes_made = Column(JSON, nullable=True)

    # Documents
    vision_mission_document_path = Column(String(500), nullable=True)
    peo_mapping_path = Column(String(500), nullable=True)
    stakeholder_feedback_path = Column(String(500), nullable=True)

    # Approval
    approved_by = Column(String(255), nullable=True)
    approved_date = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProgramVisionMission {self.program_name}>"


class ProgramOutcome(Base):
    """
    Program Outcomes (POs) and PSOs.
    NBA Criterion 2 & 3: Program Curriculum & CO Attainment
    """
    __tablename__ = "program_outcomes"

    __table_args__ = (
        Index('ix_program_outcomes_program', 'program_code'),
        Index('ix_program_outcomes_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_name = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Program Outcomes (POs) - Standard 12 POs for engineering
    pos = Column(JSON, nullable=True)  # [{"po_id": "PO1", "description": "", "bloom_level": ""}]

    # Program Specific Outcomes (PSOs)
    psos = Column(JSON, nullable=True)  # [{"pso_id": "PSO1", "description": ""}]

    # PO-PEO Mapping
    po_peo_mapping = Column(JSON, nullable=True)  # {"PO1": ["PEO1", "PEO2"]}
    pso_peo_mapping = Column(JSON, nullable=True)

    # Graduate Attributes alignment
    graduate_attributes = Column(JSON, nullable=True)

    # Attainment targets
    po_attainment_target = Column(Float, nullable=True)  # e.g., 60%
    pso_attainment_target = Column(Float, nullable=True)

    # Documents
    po_document_path = Column(String(500), nullable=True)
    mapping_document_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ProgramOutcome {self.program_name}>"


class CourseOutcome(Base):
    """
    Course Outcomes (COs) Definition.
    NBA Criterion 3: Course Outcomes & Attainment
    """
    __tablename__ = "course_outcomes"

    __table_args__ = (
        Index('ix_course_outcomes_course', 'course_code'),
        Index('ix_course_outcomes_program', 'program_code'),
        Index('ix_course_outcomes_semester', 'semester'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Course details
    course_name = Column(String(500), nullable=False)
    course_code = Column(String(50), nullable=False)
    program_name = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Course type
    course_type = Column(String(50), nullable=True)  # Theory, Lab, Project
    credits = Column(Integer, nullable=True)
    contact_hours = Column(Integer, nullable=True)

    # Course Outcomes
    cos = Column(JSON, nullable=False)  # [{"co_id": "CO1", "description": "", "bloom_level": "L3"}]

    # CO-PO Mapping
    co_po_mapping = Column(JSON, nullable=True)  # {"CO1": {"PO1": 3, "PO2": 2}}  3=Strong, 2=Moderate, 1=Weak
    co_pso_mapping = Column(JSON, nullable=True)

    # Attainment target
    attainment_target = Column(Float, nullable=True)  # e.g., 60%

    # Documents
    syllabus_path = Column(String(500), nullable=True)
    co_mapping_path = Column(String(500), nullable=True)

    # Coordinator
    course_coordinator = Column(String(255), nullable=True)
    coordinator_email = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CourseOutcome {self.course_code} - {self.course_name}>"


class COAttainment(Base):
    """
    Course Outcome Attainment Records.
    NBA Criterion 3: Course Outcomes & Attainment (Most Critical)
    """
    __tablename__ = "co_attainments"

    __table_args__ = (
        Index('ix_co_attainments_course', 'course_code'),
        Index('ix_co_attainments_semester', 'semester'),
        Index('ix_co_attainments_batch', 'batch'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Course details
    course_name = Column(String(500), nullable=False)
    course_code = Column(String(50), nullable=False)
    program_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    semester = Column(Integer, nullable=False)
    batch = Column(String(20), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Students
    total_students = Column(Integer, nullable=False)
    students_appeared = Column(Integer, nullable=True)

    # Assessment details
    assessment_methods = Column(JSON, nullable=True)  # [{"name": "CIA1", "type": "direct", "weightage": 20}]
    direct_assessment_weightage = Column(Float, default=80)
    indirect_assessment_weightage = Column(Float, default=20)

    # CO Attainment - Direct
    co_attainment_direct = Column(JSON, nullable=True)  # {"CO1": 72.5, "CO2": 68.3}
    co_attainment_indirect = Column(JSON, nullable=True)  # From surveys
    co_attainment_overall = Column(JSON, nullable=True)  # Weighted average

    # Attainment levels
    co_attainment_level = Column(JSON, nullable=True)  # {"CO1": "L2", "CO2": "L3"}
    attainment_threshold = Column(JSON, nullable=True)  # {"L3": 70, "L2": 55, "L1": 40}

    # Target vs achieved
    attainment_target = Column(Float, nullable=True)
    average_attainment = Column(Float, nullable=True)
    target_achieved = Column(Boolean, nullable=True)

    # Question paper analysis
    question_paper_analysis = Column(JSON, nullable=True)  # CO-wise question distribution
    sample_papers_path = Column(String(500), nullable=True)

    # Gap analysis
    gap_analysis = Column(JSON, nullable=True)  # {"CO2": {"gap": 5, "reason": "", "action": ""}}
    action_taken = Column(Text, nullable=True)

    # Documents
    attainment_calculation_path = Column(String(500), nullable=True)
    result_analysis_path = Column(String(500), nullable=True)
    course_end_survey_path = Column(String(500), nullable=True)

    # Verified by
    verified_by = Column(String(255), nullable=True)
    verified_date = Column(Date, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<COAttainment {self.course_code} - {self.batch}>"


class POAttainment(Base):
    """
    Program Outcome Attainment Records.
    NBA Criterion 3: CO & PO Attainment
    """
    __tablename__ = "po_attainments"

    __table_args__ = (
        Index('ix_po_attainments_program', 'program_code'),
        Index('ix_po_attainments_batch', 'batch'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_name = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Students
    total_students = Column(Integer, nullable=False)
    graduated_students = Column(Integer, nullable=True)

    # PO Attainment - Direct (from COs)
    po_attainment_direct = Column(JSON, nullable=True)  # {"PO1": 68.5, "PO2": 72.1}

    # PO Attainment - Indirect (from surveys, exit surveys)
    po_attainment_indirect = Column(JSON, nullable=True)
    indirect_sources = Column(JSON, nullable=True)  # ["exit_survey", "alumni_survey", "employer_survey"]

    # Overall PO Attainment
    po_attainment_overall = Column(JSON, nullable=True)
    direct_weightage = Column(Float, default=80)
    indirect_weightage = Column(Float, default=20)

    # PSO Attainment
    pso_attainment = Column(JSON, nullable=True)

    # Attainment levels
    po_attainment_level = Column(JSON, nullable=True)  # {"PO1": "L2", "PO2": "L3"}
    attainment_threshold = Column(JSON, nullable=True)

    # Target vs achieved
    attainment_target = Column(Float, nullable=True)
    average_po_attainment = Column(Float, nullable=True)
    average_pso_attainment = Column(Float, nullable=True)
    peo_attainment = Column(JSON, nullable=True)

    # Gap analysis
    gap_analysis = Column(JSON, nullable=True)
    improvement_actions = Column(JSON, nullable=True)

    # Documents
    calculation_path = Column(String(500), nullable=True)
    analysis_report_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<POAttainment {self.program_code} - {self.batch}>"


class StudentResultAnalysis(Base):
    """
    Student Result Analysis.
    NBA Criterion 4: Students' Performance
    """
    __tablename__ = "student_result_analysis"

    __table_args__ = (
        Index('ix_student_result_analysis_program', 'program_code'),
        Index('ix_student_result_analysis_batch', 'batch'),
        Index('ix_student_result_analysis_semester', 'semester'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_name = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=False)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(20), nullable=False)
    exam_type = Column(String(50), nullable=True)  # Regular, Supplementary

    # Student counts
    registered_students = Column(Integer, nullable=False)
    appeared_students = Column(Integer, nullable=True)
    passed_students = Column(Integer, nullable=True)
    failed_students = Column(Integer, nullable=True)
    detained_students = Column(Integer, default=0)

    # Results
    pass_percentage = Column(Float, nullable=True)
    first_class = Column(Integer, nullable=True)
    distinction = Column(Integer, nullable=True)
    first_class_distinction = Column(Integer, nullable=True)
    average_cgpa = Column(Float, nullable=True)
    average_percentage = Column(Float, nullable=True)

    # Grade distribution
    grade_distribution = Column(JSON, nullable=True)  # {"O": 10, "A+": 25, ...}

    # Backlogs
    with_backlogs = Column(Integer, nullable=True)
    backlog_distribution = Column(JSON, nullable=True)  # {"1": 20, "2": 10, "3+": 5}

    # Performance trend
    improvement_from_previous = Column(Float, nullable=True)

    # Subject-wise analysis
    subject_wise_results = Column(JSON, nullable=True)

    # Documents
    result_sheet_path = Column(String(500), nullable=True)
    analysis_report_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StudentResultAnalysis {self.program_code} - {self.batch} - Sem {self.semester}>"


class NBAContinuousImprovement(Base):
    """
    Continuous Improvement Records.
    NBA Criterion 7: Continuous Improvement
    """
    __tablename__ = "nba_continuous_improvement"

    __table_args__ = (
        Index('ix_nba_ci_program', 'program_code'),
        Index('ix_nba_ci_year', 'academic_year'),
        Index('ix_nba_ci_status', 'status'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Program details
    program_name = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Feedback source
    feedback_source = Column(SQLEnum(FeedbackSource), nullable=False)
    feedback_date = Column(Date, nullable=True)
    feedback_summary = Column(Text, nullable=True)

    # Issue/Gap identified
    issue_identified = Column(Text, nullable=False)
    po_co_affected = Column(JSON, nullable=True)  # ["PO2", "CO3"]
    criterion_affected = Column(String(100), nullable=True)

    # Action plan
    action_planned = Column(Text, nullable=False)
    action_type = Column(String(100), nullable=True)  # curriculum_revision, lab_upgrade, etc.
    responsible_person = Column(String(255), nullable=True)
    target_date = Column(Date, nullable=True)

    # Implementation
    status = Column(SQLEnum(ActionStatus), default=ActionStatus.PLANNED)
    action_taken = Column(Text, nullable=True)
    completion_date = Column(Date, nullable=True)

    # Impact assessment
    impact_assessment = Column(Text, nullable=True)
    improvement_achieved = Column(Text, nullable=True)
    quantitative_improvement = Column(JSON, nullable=True)  # {"before": 60, "after": 72}

    # Documents
    feedback_path = Column(String(500), nullable=True)
    action_report_path = Column(String(500), nullable=True)
    evidence_path = Column(String(500), nullable=True)

    # Review
    reviewed_by = Column(String(255), nullable=True)
    review_date = Column(Date, nullable=True)
    review_remarks = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NBAContinuousImprovement {self.program_code} - {self.issue_identified[:30]}>"


class NBAFacultyContribution(Base):
    """
    Faculty Contributions for NBA.
    NBA Criterion 5: Faculty Information & Contributions
    """
    __tablename__ = "nba_faculty_contributions"

    __table_args__ = (
        Index('ix_nba_faculty_department', 'department'),
        Index('ix_nba_faculty_program', 'program_code'),
        Index('ix_nba_faculty_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Faculty details
    faculty_id = Column(String(50), nullable=False)
    faculty_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    designation = Column(String(100), nullable=True)
    program_code = Column(String(50), nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Qualifications
    highest_degree = Column(String(100), nullable=True)
    specialization = Column(String(255), nullable=True)
    experience_years = Column(Float, nullable=True)
    industry_experience = Column(Float, nullable=True)

    # Teaching load
    courses_taught = Column(JSON, nullable=True)  # [{"code": "", "name": "", "credits": ""}]
    teaching_hours_per_week = Column(Float, nullable=True)
    theory_hours = Column(Float, nullable=True)
    lab_hours = Column(Float, nullable=True)

    # Research contributions
    publications = Column(JSON, nullable=True)  # [{"title": "", "journal": "", "year": ""}]
    scopus_publications = Column(Integer, default=0)
    wos_publications = Column(Integer, default=0)
    patents = Column(Integer, default=0)
    funded_projects = Column(Integer, default=0)
    consultancy_projects = Column(Integer, default=0)

    # FDPs and training
    fdps_attended = Column(JSON, nullable=True)
    fdps_organized = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)

    # Student guidance
    phd_students_guided = Column(Integer, default=0)
    pg_projects_guided = Column(Integer, default=0)
    ug_projects_guided = Column(Integer, default=0)

    # Awards
    awards = Column(JSON, nullable=True)

    # Student feedback rating
    student_feedback_score = Column(Float, nullable=True)

    # Documents
    cv_path = Column(String(500), nullable=True)
    profile_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NBAFacultyContribution {self.faculty_name}>"


class NBALabFacility(Base):
    """
    Laboratory Facilities for NBA.
    NBA Criterion 6: Facilities & Technical Support
    """
    __tablename__ = "nba_lab_facilities"

    __table_args__ = (
        Index('ix_nba_lab_department', 'department'),
        Index('ix_nba_lab_program', 'program_code'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Lab details
    lab_name = Column(String(255), nullable=False)
    lab_number = Column(String(50), nullable=True)
    department = Column(String(255), nullable=False)
    program_code = Column(String(50), nullable=True)

    # Physical details
    area_sqft = Column(Float, nullable=True)
    capacity = Column(Integer, nullable=True)
    establishment_year = Column(Integer, nullable=True)

    # Equipment
    major_equipment = Column(JSON, nullable=True)  # [{"name": "", "make": "", "qty": "", "value": ""}]
    total_equipment_count = Column(Integer, nullable=True)
    total_equipment_value = Column(Float, nullable=True)

    # Software
    software_available = Column(JSON, nullable=True)  # [{"name": "", "license_type": "", "qty": ""}]

    # Courses supported
    courses_supported = Column(JSON, nullable=True)  # [{"code": "", "name": ""}]

    # Utilization
    hours_per_week = Column(Float, nullable=True)
    student_computer_ratio = Column(String(20), nullable=True)  # "1:1", "2:1"
    utilization_percentage = Column(Float, nullable=True)

    # Technical staff
    lab_incharge = Column(String(255), nullable=True)
    technical_staff = Column(JSON, nullable=True)

    # Maintenance
    amc_available = Column(Boolean, default=False)
    last_upgraded = Column(Date, nullable=True)

    # Safety
    safety_measures = Column(JSON, nullable=True)
    safety_training_conducted = Column(Boolean, default=False)

    # Documents
    lab_manual_path = Column(String(500), nullable=True)
    equipment_list_path = Column(String(500), nullable=True)
    photos_path = Column(String(500), nullable=True)
    utilization_log_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NBALabFacility {self.lab_name}>"
