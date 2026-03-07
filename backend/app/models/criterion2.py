"""
NAAC Criterion 2: Teaching-Learning and Evaluation - Database Models

This module defines database models for managing NAAC Criterion 2 requirements (200 marks):
- LMS Adoption and Usage
- Lesson Plans with Bloom's Taxonomy
- Attendance Tracking
- Continuous Internal Evaluation (CIE)
- Student Performance Analytics
- Evaluation Rubrics
- Teacher Profiles and Development
- Digital Content/Resources
- Learning Outcomes Attainment
"""

from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer, Text, ForeignKey, JSON, Boolean, Index, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from app.core.database import Base
from app.core.types import GUID, generate_uuid


# ==================== ENUMS ====================

class LMSPlatform(str, enum.Enum):
    """Learning Management System platforms"""
    MOODLE = "moodle"
    GOOGLE_CLASSROOM = "google_classroom"
    MICROSOFT_TEAMS = "microsoft_teams"
    CANVAS = "canvas"
    BLACKBOARD = "blackboard"
    CUSTOM = "custom"
    OTHER = "other"


class BloomsLevel(str, enum.Enum):
    """Bloom's Taxonomy cognitive levels"""
    REMEMBER = "L1_remember"
    UNDERSTAND = "L2_understand"
    APPLY = "L3_apply"
    ANALYZE = "L4_analyze"
    EVALUATE = "L5_evaluate"
    CREATE = "L6_create"


class AttendanceStatus(str, enum.Enum):
    """Student attendance status"""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"
    ON_DUTY = "on_duty"


class AssessmentType(str, enum.Enum):
    """Types of assessments"""
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    MID_TERM = "mid_term"
    END_TERM = "end_term"
    PROJECT = "project"
    PRESENTATION = "presentation"
    LAB = "lab"
    VIVA = "viva"
    SEMINAR = "seminar"
    OTHER = "other"


class TeachingMethod(str, enum.Enum):
    """Student-centric teaching methods"""
    LECTURE = "lecture"
    FLIPPED_CLASSROOM = "flipped_classroom"
    PROJECT_BASED = "project_based"
    PROBLEM_BASED = "problem_based"
    CASE_STUDY = "case_study"
    GROUP_DISCUSSION = "group_discussion"
    EXPERIENTIAL = "experiential"
    PEER_LEARNING = "peer_learning"
    ICT_ENABLED = "ict_enabled"
    BLENDED = "blended"
    SIMULATION = "simulation"
    FIELD_VISIT = "field_visit"


class ContentType(str, enum.Enum):
    """Digital content types"""
    VIDEO = "video"
    PDF = "pdf"
    PPT = "ppt"
    INTERACTIVE = "interactive"
    SIMULATION = "simulation"
    E_BOOK = "e_book"
    MOOC = "mooc"
    QUIZ = "quiz"
    ANIMATION = "animation"
    OTHER = "other"


class TeacherDesignation(str, enum.Enum):
    """Teacher designations"""
    PROFESSOR = "professor"
    ASSOCIATE_PROFESSOR = "associate_professor"
    ASSISTANT_PROFESSOR = "assistant_professor"
    LECTURER = "lecturer"
    GUEST_FACULTY = "guest_faculty"
    ADJUNCT_FACULTY = "adjunct_faculty"
    VISITING_FACULTY = "visiting_faculty"


class PerformanceLevel(str, enum.Enum):
    """Student performance levels"""
    OUTSTANDING = "outstanding"
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    POOR = "poor"


# ==================== MODELS ====================

class LMSAdoption(Base):
    """
    LMS Adoption and Usage Tracking.
    Key Indicator 2.3: Teaching-Learning Process
    """
    __tablename__ = "lms_adoption"

    __table_args__ = (
        Index('ix_lms_adoption_platform', 'platform'),
        Index('ix_lms_adoption_department', 'department'),
        Index('ix_lms_adoption_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # LMS details
    platform = Column(SQLEnum(LMSPlatform), nullable=False)
    platform_name = Column(String(255), nullable=True)  # Custom name if OTHER
    platform_url = Column(String(500), nullable=True)

    # Adoption context
    department = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Usage statistics
    total_courses = Column(Integer, default=0)
    active_courses = Column(Integer, default=0)
    total_faculty_registered = Column(Integer, default=0)
    total_students_registered = Column(Integer, default=0)
    active_users_monthly = Column(Integer, default=0)

    # Content statistics
    total_resources_uploaded = Column(Integer, default=0)
    total_assignments_created = Column(Integer, default=0)
    total_quizzes_created = Column(Integer, default=0)
    total_discussion_forums = Column(Integer, default=0)

    # Engagement metrics
    avg_login_frequency = Column(Float, nullable=True)  # per student per month
    assignment_submission_rate = Column(Float, nullable=True)  # percentage
    quiz_completion_rate = Column(Float, nullable=True)

    # Evidence
    screenshots_path = Column(String(500), nullable=True)
    usage_report_path = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LMSAdoption {self.platform.value} - {self.department}>"


class LessonPlan(Base):
    """
    Lesson Plans with Bloom's Taxonomy mapping.
    Key Indicator 2.3: Teaching-Learning Process
    """
    __tablename__ = "lesson_plans"

    __table_args__ = (
        Index('ix_lesson_plans_course_code', 'course_code'),
        Index('ix_lesson_plans_department', 'department'),
        Index('ix_lesson_plans_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Course information
    course_name = Column(String(500), nullable=False)
    course_code = Column(String(50), nullable=False)
    department = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(20), nullable=False)
    credits = Column(Integer, nullable=True)

    # Faculty
    faculty_name = Column(String(255), nullable=False)
    faculty_email = Column(String(255), nullable=True)

    # Lesson plan structure
    unit_number = Column(Integer, nullable=True)
    unit_name = Column(String(500), nullable=True)
    topic = Column(String(500), nullable=False)
    subtopics = Column(JSON, nullable=True)  # ["subtopic1", "subtopic2"]

    # Duration
    planned_hours = Column(Float, nullable=False)
    actual_hours = Column(Float, nullable=True)
    session_date = Column(Date, nullable=True)

    # Learning outcomes
    learning_objectives = Column(JSON, nullable=True)  # ["LO1", "LO2"]
    course_outcomes_mapped = Column(JSON, nullable=True)  # ["CO1", "CO2"]
    blooms_levels = Column(JSON, nullable=True)  # ["L1_remember", "L3_apply"]

    # Teaching methodology
    teaching_methods = Column(JSON, nullable=True)  # ["lecture", "case_study"]
    teaching_aids = Column(JSON, nullable=True)  # ["PPT", "Video", "Board"]
    ict_tools_used = Column(JSON, nullable=True)  # ["Projector", "LMS"]

    # Assessment
    assessment_methods = Column(JSON, nullable=True)  # ["quiz", "assignment"]
    assessment_blooms_level = Column(SQLEnum(BloomsLevel), nullable=True)

    # Resources
    reference_materials = Column(JSON, nullable=True)  # ["Book1", "URL1"]
    additional_resources = Column(Text, nullable=True)

    # Delivery status
    is_completed = Column(Boolean, default=False)
    completion_date = Column(Date, nullable=True)
    remarks = Column(Text, nullable=True)

    # Document path
    document_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LessonPlan {self.course_code} - {self.topic}>"


class AttendanceRecord(Base):
    """
    Student Attendance Tracking.
    Key Indicator 2.1/2.3: Student Enrollment and Teaching Process
    """
    __tablename__ = "attendance_records"

    __table_args__ = (
        Index('ix_attendance_records_student_id', 'student_id'),
        Index('ix_attendance_records_course_code', 'course_code'),
        Index('ix_attendance_records_date', 'attendance_date'),
        Index('ix_attendance_records_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student info
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=True)
    semester = Column(Integer, nullable=True)

    # Course info
    course_code = Column(String(50), nullable=False)
    course_name = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Attendance details
    attendance_date = Column(Date, nullable=False)
    period = Column(Integer, nullable=True)  # Which period/hour
    status = Column(SQLEnum(AttendanceStatus), nullable=False)

    # Additional info
    marked_by = Column(String(255), nullable=True)
    remarks = Column(String(500), nullable=True)
    is_makeup_class = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AttendanceRecord {self.student_id} - {self.attendance_date}>"


class CIERecord(Base):
    """
    Continuous Internal Evaluation (CIE) Records.
    Key Indicator 2.5: Evaluation Process and Reforms
    """
    __tablename__ = "cie_records"

    __table_args__ = (
        Index('ix_cie_records_student_id', 'student_id'),
        Index('ix_cie_records_course_code', 'course_code'),
        Index('ix_cie_records_assessment_type', 'assessment_type'),
        Index('ix_cie_records_academic_year', 'academic_year'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student info
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    batch = Column(String(20), nullable=True)
    semester = Column(Integer, nullable=True)

    # Course info
    course_code = Column(String(50), nullable=False)
    course_name = Column(String(255), nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Assessment details
    assessment_type = Column(SQLEnum(AssessmentType), nullable=False)
    assessment_name = Column(String(255), nullable=False)  # e.g., "Quiz 1", "Mid-Term 1"
    assessment_date = Column(Date, nullable=False)

    # Scoring
    max_marks = Column(Float, nullable=False)
    marks_obtained = Column(Float, nullable=True)
    percentage = Column(Float, nullable=True)
    grade = Column(String(10), nullable=True)

    # CO-PO mapping
    course_outcomes_assessed = Column(JSON, nullable=True)  # ["CO1", "CO2"]
    blooms_level = Column(SQLEnum(BloomsLevel), nullable=True)

    # Rubric used
    rubric_id = Column(GUID, ForeignKey("evaluation_rubrics.id", ondelete="SET NULL"), nullable=True)

    # Feedback
    feedback = Column(Text, nullable=True)
    evaluated_by = Column(String(255), nullable=True)
    evaluated_at = Column(DateTime, nullable=True)

    # Evidence
    answer_sheet_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rubric = relationship("EvaluationRubric", back_populates="cie_records")

    def __repr__(self):
        return f"<CIERecord {self.student_id} - {self.assessment_name}>"


class EvaluationRubric(Base):
    """
    Rubrics-based Evaluation.
    Key Indicator 2.5: Evaluation Process and Reforms
    """
    __tablename__ = "evaluation_rubrics"

    __table_args__ = (
        Index('ix_evaluation_rubrics_course_code', 'course_code'),
        Index('ix_evaluation_rubrics_assessment_type', 'assessment_type'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Rubric info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Course context
    course_code = Column(String(50), nullable=True)
    course_name = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=True)

    # Assessment type this rubric is for
    assessment_type = Column(SQLEnum(AssessmentType), nullable=True)

    # Total points
    total_points = Column(Float, nullable=False)

    # Rubric criteria - JSON structure
    # [{"name": "Code Quality", "description": "...", "max_points": 20, "levels": {...}, "co_mapped": ["CO1"], "blooms_level": "L3"}]
    criteria = Column(JSON, nullable=False)

    # Performance levels definition
    # {"excellent": {"min": 90, "max": 100}, "good": {"min": 75, "max": 89}, ...}
    performance_levels = Column(JSON, nullable=True)

    # CO-PO mapping for the rubric
    course_outcomes_mapped = Column(JSON, nullable=True)
    blooms_levels_covered = Column(JSON, nullable=True)

    # Document
    document_path = Column(String(500), nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)  # Can be reused

    # Created by
    created_by = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    cie_records = relationship("CIERecord", back_populates="rubric")

    def __repr__(self):
        return f"<EvaluationRubric {self.name}>"


class StudentPerformance(Base):
    """
    Student Performance Analytics.
    Key Indicator 2.6: Student Performance and Learning Outcomes
    """
    __tablename__ = "student_performance"

    __table_args__ = (
        Index('ix_student_performance_student_id', 'student_id'),
        Index('ix_student_performance_department', 'department'),
        Index('ix_student_performance_academic_year', 'academic_year'),
        Index('ix_student_performance_level', 'performance_level'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Student info
    student_id = Column(String(50), nullable=False)
    student_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    batch = Column(String(20), nullable=True)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(20), nullable=False)

    # Overall performance
    sgpa = Column(Float, nullable=True)  # Semester GPA
    cgpa = Column(Float, nullable=True)  # Cumulative GPA
    total_credits_earned = Column(Integer, default=0)
    total_credits_attempted = Column(Integer, default=0)
    percentage = Column(Float, nullable=True)
    performance_level = Column(SQLEnum(PerformanceLevel), nullable=True)

    # Course-wise performance - JSON
    # [{"course_code": "CS101", "grade": "A", "credits": 4, "co_attainment": {...}}, ...]
    course_performance = Column(JSON, nullable=True)

    # CO-PO Attainment
    co_attainment = Column(JSON, nullable=True)  # {"CO1": 2.8, "CO2": 3.0, ...}
    po_attainment = Column(JSON, nullable=True)  # {"PO1": 2.5, "PO2": 2.7, ...}
    pso_attainment = Column(JSON, nullable=True)  # Program Specific Outcomes

    # Attendance summary
    overall_attendance_percentage = Column(Float, nullable=True)

    # CIE summary
    average_cie_score = Column(Float, nullable=True)
    cie_performance_trend = Column(JSON, nullable=True)  # [{"month": "Jan", "avg": 75}, ...]

    # Strengths and areas for improvement
    strengths = Column(JSON, nullable=True)  # ["Strong in programming", "Good analytical skills"]
    areas_for_improvement = Column(JSON, nullable=True)

    # Mentor feedback
    mentor_name = Column(String(255), nullable=True)
    mentor_remarks = Column(Text, nullable=True)

    # Pass/Fail status
    is_passed = Column(Boolean, nullable=True)
    backlogs_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<StudentPerformance {self.student_id} - Sem {self.semester}>"


class TeacherProfile(Base):
    """
    Teacher Profiles and Quality Tracking.
    Key Indicator 2.4: Teacher Quality
    """
    __tablename__ = "teacher_profiles"

    __table_args__ = (
        Index('ix_teacher_profiles_department', 'department'),
        Index('ix_teacher_profiles_designation', 'designation'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Basic info
    employee_id = Column(String(50), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    department = Column(String(255), nullable=False)
    designation = Column(SQLEnum(TeacherDesignation), nullable=False)

    # Qualifications
    highest_qualification = Column(String(255), nullable=True)  # Ph.D., M.Tech, etc.
    specialization = Column(String(255), nullable=True)
    qualifications_list = Column(JSON, nullable=True)  # [{"degree": "Ph.D.", "year": 2010, "university": "..."}]

    # Experience
    teaching_experience_years = Column(Float, default=0)
    industry_experience_years = Column(Float, default=0)
    research_experience_years = Column(Float, default=0)
    date_of_joining = Column(Date, nullable=True)

    # Awards and recognition
    awards = Column(JSON, nullable=True)  # [{"name": "Best Teacher", "year": 2023, "awarding_body": "..."}]

    # Research contributions
    publications_count = Column(Integer, default=0)
    patents_count = Column(Integer, default=0)
    funded_projects_count = Column(Integer, default=0)
    research_indices = Column(JSON, nullable=True)  # {"h_index": 5, "citations": 100}

    # Training and FDP
    fdp_attended = Column(JSON, nullable=True)  # [{"name": "AI/ML", "duration": "1 week", "year": 2024}]
    workshops_conducted = Column(JSON, nullable=True)
    certifications = Column(JSON, nullable=True)

    # Teaching load
    current_courses = Column(JSON, nullable=True)  # ["CS101", "CS202"]
    teaching_hours_per_week = Column(Float, nullable=True)

    # Performance metrics
    student_feedback_rating = Column(Float, nullable=True)  # 1-5 scale
    api_score = Column(Float, nullable=True)  # Academic Performance Index

    # ICT usage
    uses_lms = Column(Boolean, default=False)
    digital_content_created = Column(Integer, default=0)
    moocs_developed = Column(Integer, default=0)

    # Status
    is_active = Column(Boolean, default=True)
    is_phd_guide = Column(Boolean, default=False)
    phd_students_guided = Column(Integer, default=0)

    # Profile document
    profile_document_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TeacherProfile {self.name} - {self.department}>"


class DigitalContent(Base):
    """
    Digital Learning Content/Resources.
    Key Indicator 2.3: Teaching-Learning Process
    """
    __tablename__ = "digital_contents"

    __table_args__ = (
        Index('ix_digital_contents_course_code', 'course_code'),
        Index('ix_digital_contents_content_type', 'content_type'),
        Index('ix_digital_contents_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Content info
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    content_type = Column(SQLEnum(ContentType), nullable=False)

    # Course context
    course_code = Column(String(50), nullable=True)
    course_name = Column(String(255), nullable=True)
    department = Column(String(255), nullable=False)
    semester = Column(Integer, nullable=True)

    # Topics covered
    topics = Column(JSON, nullable=True)  # ["Topic 1", "Topic 2"]
    learning_outcomes = Column(JSON, nullable=True)  # ["LO1", "LO2"]
    blooms_level = Column(SQLEnum(BloomsLevel), nullable=True)

    # Content details
    file_path = Column(String(500), nullable=True)
    file_size = Column(Integer, nullable=True)  # in bytes
    external_url = Column(String(500), nullable=True)  # For MOOC links
    duration_minutes = Column(Integer, nullable=True)  # For videos

    # Creator info
    created_by = Column(String(255), nullable=False)
    creator_email = Column(String(255), nullable=True)

    # Usage statistics
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    average_rating = Column(Float, nullable=True)
    ratings_count = Column(Integer, default=0)

    # Accessibility
    is_accessible = Column(Boolean, default=True)  # ADA compliant
    has_transcripts = Column(Boolean, default=False)
    supported_languages = Column(JSON, nullable=True)

    # Status
    is_published = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    approved_by = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DigitalContent {self.title}>"


class LearningOutcomeAttainment(Base):
    """
    Course/Program Learning Outcomes Attainment Tracking.
    Key Indicator 2.6: Student Performance and Learning Outcomes
    """
    __tablename__ = "learning_outcome_attainments"

    __table_args__ = (
        Index('ix_lo_attainment_course_code', 'course_code'),
        Index('ix_lo_attainment_academic_year', 'academic_year'),
        Index('ix_lo_attainment_department', 'department'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Course info
    course_code = Column(String(50), nullable=False)
    course_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    semester = Column(Integer, nullable=False)
    academic_year = Column(String(20), nullable=False)
    batch = Column(String(20), nullable=True)

    # Class statistics
    total_students = Column(Integer, nullable=False)
    students_appeared = Column(Integer, nullable=True)
    students_passed = Column(Integer, nullable=True)
    pass_percentage = Column(Float, nullable=True)

    # Course Outcomes defined
    course_outcomes = Column(JSON, nullable=False)  # [{"id": "CO1", "statement": "...", "blooms": "L3"}, ...]

    # CO Attainment
    co_attainment_direct = Column(JSON, nullable=True)  # {"CO1": 2.8, "CO2": 3.0, ...}
    co_attainment_indirect = Column(JSON, nullable=True)  # Survey based
    co_attainment_overall = Column(JSON, nullable=True)
    co_attainment_target = Column(JSON, nullable=True)  # Target levels

    # PO Contribution
    co_po_mapping = Column(JSON, nullable=True)  # {"CO1": {"PO1": 3, "PO2": 2}, ...}
    po_contribution = Column(JSON, nullable=True)  # {"PO1": 2.5, ...}

    # Assessment methods used
    direct_assessment_methods = Column(JSON, nullable=True)  # ["CIE", "SEE", "Assignment"]
    indirect_assessment_methods = Column(JSON, nullable=True)  # ["Course Exit Survey"]

    # Attainment calculation details
    direct_weightage = Column(Float, default=80)  # percentage
    indirect_weightage = Column(Float, default=20)
    attainment_threshold = Column(Float, default=60)  # percentage needed for level 1

    # Analysis
    gap_analysis = Column(JSON, nullable=True)  # COs not meeting target
    action_taken = Column(Text, nullable=True)

    # Documents
    attainment_report_path = Column(String(500), nullable=True)

    # Faculty
    course_coordinator = Column(String(255), nullable=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<LearningOutcomeAttainment {self.course_code} - {self.academic_year}>"


class BlendedLearningSession(Base):
    """
    Blended Learning Sessions Tracking.
    Key Indicator 2.3: Teaching-Learning Process
    """
    __tablename__ = "blended_learning_sessions"

    __table_args__ = (
        Index('ix_blended_sessions_course_code', 'course_code'),
        Index('ix_blended_sessions_department', 'department'),
        Index('ix_blended_sessions_date', 'session_date'),
    )

    id = Column(GUID, primary_key=True, default=generate_uuid)

    # Course info
    course_code = Column(String(50), nullable=False)
    course_name = Column(String(255), nullable=False)
    department = Column(String(255), nullable=False)
    semester = Column(Integer, nullable=True)
    academic_year = Column(String(20), nullable=False)

    # Session details
    session_title = Column(String(500), nullable=False)
    session_date = Column(Date, nullable=False)
    duration_minutes = Column(Integer, nullable=True)

    # Teaching method
    teaching_method = Column(SQLEnum(TeachingMethod), nullable=False)
    is_synchronous = Column(Boolean, default=True)  # Live vs recorded

    # Mode split
    online_component_percentage = Column(Float, nullable=True)
    offline_component_percentage = Column(Float, nullable=True)

    # Tools used
    tools_used = Column(JSON, nullable=True)  # ["Zoom", "LMS", "Google Meet"]
    lms_platform = Column(String(100), nullable=True)

    # Content shared
    pre_class_materials = Column(JSON, nullable=True)  # Links to content
    in_class_activities = Column(JSON, nullable=True)
    post_class_assignments = Column(JSON, nullable=True)

    # Participation
    students_enrolled = Column(Integer, nullable=True)
    students_attended_online = Column(Integer, nullable=True)
    students_attended_offline = Column(Integer, nullable=True)
    attendance_percentage = Column(Float, nullable=True)

    # Faculty
    faculty_name = Column(String(255), nullable=False)
    faculty_email = Column(String(255), nullable=True)

    # Feedback
    student_feedback_rating = Column(Float, nullable=True)
    feedback_comments = Column(Text, nullable=True)

    # Learning outcomes
    learning_outcomes_covered = Column(JSON, nullable=True)
    blooms_levels_addressed = Column(JSON, nullable=True)

    # Evidence
    session_recording_path = Column(String(500), nullable=True)
    screenshots_path = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<BlendedLearningSession {self.session_title} - {self.session_date}>"
