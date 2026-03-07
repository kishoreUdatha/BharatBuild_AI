"""
NAAC/NBA Accreditation API Endpoints - Complete 7 Criteria Support
Generates accreditation-compliant documents for Indian colleges.
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Path, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import logging
import io
import os
import uuid

from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.criterion1 import (
    CurriculumFeedback,
    CurriculumEvidence,
    IndustryPartner,
    AdvisoryBoardMeeting,
    ValueAddedCourse,
    ValueAddedCourseEnrollment,
    InternshipRecord,
    FeedbackType as FeedbackTypeEnum,
    FeedbackStatus as FeedbackStatusEnum,
    EvidenceType as EvidenceTypeEnum,
    PartnerType as PartnerTypeEnum,
    MoUStatus as MoUStatusEnum,
    CourseType as CourseTypeEnum,
    CourseMode as CourseModeEnum,
    InternshipType as InternshipTypeEnum,
    InternshipStatus as InternshipStatusEnum,
)
from app.models.criterion2 import (
    LMSAdoption,
    LessonPlan,
    AttendanceRecord,
    CIERecord,
    EvaluationRubric as EvaluationRubricModel,
    StudentPerformance,
    TeacherProfile,
    DigitalContent,
    LearningOutcomeAttainment,
    BlendedLearningSession,
    LMSPlatform as LMSPlatformEnum,
    BloomsLevel as BloomsLevelEnum,
    AttendanceStatus as AttendanceStatusEnum,
    AssessmentType as AssessmentTypeEnum,
    TeachingMethod as TeachingMethodEnum,
    ContentType as ContentTypeEnum,
    TeacherDesignation as TeacherDesignationEnum,
    PerformanceLevel as PerformanceLevelEnum,
)
from app.schemas.criterion1 import (
    FeedbackCreate, FeedbackUpdate, FeedbackResponse, FeedbackListResponse, FeedbackActionRequest, FeedbackReportRequest,
    EvidenceCreate, EvidenceUpdate, EvidenceVerifyRequest, EvidenceResponse, EvidenceListResponse,
    PartnerCreate, PartnerUpdate, PartnerMoUUpdate, PartnerActivityCreate, PartnerResponse, PartnerListResponse,
    MeetingCreate, MeetingUpdate, MeetingResponse, MeetingListResponse,
    ValueAddedCourseCreate, ValueAddedCourseUpdate, CourseEnrollmentCreate, CourseEnrollmentUpdate,
    CourseEnrollmentResponse, ValueAddedCourseResponse, ValueAddedCourseListResponse,
    InternshipCreate, InternshipUpdate, InternshipResponse, InternshipListResponse, InternshipAnalytics,
    Criterion1DashboardStats, Criterion1ReportRequest, Criterion1ReportResponse,
    FeedbackType, FeedbackStatus, EvidenceType, PartnerType, MoUStatus, CourseType, CourseMode, InternshipType, InternshipStatus,
)
from app.schemas.criterion2 import (
    LMSAdoptionCreate, LMSAdoptionUpdate, LMSAdoptionResponse, LMSAdoptionListResponse,
    LessonPlanCreate, LessonPlanUpdate, LessonPlanResponse, LessonPlanListResponse,
    AttendanceCreate, AttendanceBulkCreate, AttendanceUpdate, AttendanceResponse, AttendanceListResponse, AttendanceSummary,
    CIECreate, CIEUpdate, CIEResponse, CIEListResponse, CIEBulkCreate,
    RubricCreate, RubricUpdate, RubricResponse, RubricListResponse,
    StudentPerformanceCreate, StudentPerformanceUpdate, StudentPerformanceResponse, StudentPerformanceListResponse, StudentPerformanceAnalytics,
    TeacherProfileCreate, TeacherProfileUpdate, TeacherProfileResponse, TeacherProfileListResponse,
    DigitalContentCreate, DigitalContentUpdate, DigitalContentResponse, DigitalContentListResponse,
    LOAttainmentCreate, LOAttainmentUpdate, LOAttainmentResponse, LOAttainmentListResponse,
    BlendedLearningCreate, BlendedLearningUpdate, BlendedLearningResponse, BlendedLearningListResponse,
    Criterion2DashboardStats, Criterion2ReportRequest, Criterion2ReportResponse,
    LMSPlatform, BloomsLevel, AttendanceStatus, AssessmentType, TeachingMethod, ContentType, TeacherDesignation, PerformanceLevel,
)
from app.models.criterion3 import (
    ResearchProject,
    Publication,
    Patent,
    Startup,
    InnovationCell,
    Hackathon,
    ExtensionActivity,
    Consultancy,
    ResearchFunding,
    ProjectType as ProjectTypeEnum,
    ProjectStatus as ResearchProjectStatusEnum,
    PublicationType as PublicationTypeEnum,
    PublicationIndexing as PublicationIndexingEnum,
    PatentStatus as PatentStatusEnum,
    PatentType as PatentTypeEnum,
    StartupStage as StartupStageEnum,
    StartupStatus as StartupStatusEnum,
    EventType as EventTypeEnum,
    ExtensionType as ExtensionTypeEnum,
    FundingAgency as FundingAgencyEnum,
)
from app.schemas.criterion3 import (
    ResearchProjectCreate, ResearchProjectUpdate, ResearchProjectResponse, ResearchProjectListResponse,
    PublicationCreate, PublicationUpdate, PublicationResponse, PublicationListResponse,
    PatentCreate, PatentUpdate, PatentResponse, PatentListResponse,
    StartupCreate, StartupUpdate, StartupResponse, StartupListResponse,
    InnovationCellCreate, InnovationCellUpdate, InnovationCellResponse, InnovationCellListResponse,
    HackathonCreate, HackathonUpdate, HackathonResponse, HackathonListResponse,
    ExtensionActivityCreate, ExtensionActivityUpdate, ExtensionActivityResponse, ExtensionActivityListResponse,
    ConsultancyCreate, ConsultancyUpdate, ConsultancyResponse, ConsultancyListResponse,
    ResearchFundingCreate, ResearchFundingUpdate, ResearchFundingResponse, ResearchFundingListResponse,
    Criterion3DashboardStats, Criterion3ReportRequest, Criterion3ReportResponse,
    ProjectType, ProjectStatus, PublicationType, PublicationIndexing, PatentStatus, PatentType,
    StartupStage, StartupStatus, EventType, ExtensionType, FundingAgency,
)

from app.modules.agents.naac_nba_agent import (
    naac_nba_agent,
    NAACCriterion,
    AccreditationDocType
)
from app.modules.agents.base_agent import AgentContext
from app.modules.curriculum import (
    curriculum_mapping_engine,
    industry_library,
    CourseInfo as CurriculumCourseInfo,
    DifficultyLevel,
    ProjectType,
    TechnologyDomain
)
from app.modules.evaluation import (
    project_evaluator,
    EvaluationRubric,
    RubricCriterion,
    GradeLevel
)
from app.modules.certification import (
    certificate_generator,
    CertificateType,
    SkillLevel
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== REQUEST MODELS ====================

class InstitutionInfo(BaseModel):
    """Institution details for NAAC documentation"""
    name: str = Field(..., description="Institution name")
    type: str = Field(..., description="University/Autonomous/Affiliated")
    location: str = Field(..., description="City")
    state: str = Field(..., description="State")
    established_year: int = Field(..., description="Year of establishment")
    naac_cycle: int = Field(default=1, description="NAAC cycle (1st, 2nd, 3rd)")
    previous_grade: Optional[str] = Field(None, description="Previous NAAC grade")
    affiliated_university: Optional[str] = Field(None, description="Affiliated to university")
    programs_offered: List[str] = Field(default=[], description="Programs offered")
    total_students: int = Field(default=0, description="Total student strength")
    total_faculty: int = Field(default=0, description="Total faculty count")


class CourseInfo(BaseModel):
    """Course information for OBE documents"""
    course_name: str = Field(..., description="Course name")
    course_code: str = Field(..., description="Course code")
    department: str = Field(..., description="Department")
    semester: int = Field(..., ge=1, le=8, description="Semester")
    credits: int = Field(..., ge=1, le=6, description="Credits")
    program_name: Optional[str] = Field(None, description="Program name")


class CriterionRequest(BaseModel):
    """Request for generating criterion-specific documents"""
    institution: InstitutionInfo
    criterion: str = Field(..., description="Criterion number (1-7)")
    academic_year: str = Field(default="2024-25", description="Academic year")
    additional_context: Optional[str] = Field(None, description="Additional context")


class SSRRequest(BaseModel):
    """Request for generating complete Self Study Report"""
    institution: InstitutionInfo
    academic_year: str = Field(default="2024-25")
    naac_cycle: int = Field(default=1, description="1st, 2nd, or 3rd cycle")
    previous_grade: Optional[str] = Field(None)


class OBERequest(BaseModel):
    """Request for OBE (Criterion 2) documents"""
    course_info: CourseInfo
    project_description: str = Field(..., description="Course/project description")
    doc_type: str = Field(
        default="course_outcomes",
        description="Document type: course_outcomes, co_po_mapping, rubrics, attainment"
    )


class COPOMappingRequest(BaseModel):
    """Request for CO-PO mapping"""
    course_info: CourseInfo
    course_outcomes: List[str] = Field(..., description="List of course outcomes")


class RubricsRequest(BaseModel):
    """Request for assessment rubrics"""
    course_info: CourseInfo
    assessment_type: str = Field(default="project", description="Type of assessment")
    criteria_count: int = Field(default=5, ge=3, le=8)


class BestPracticesRequest(BaseModel):
    """Request for best practices documentation"""
    institution: InstitutionInfo
    focus_areas: Optional[List[str]] = Field(
        None,
        description="Focus areas for best practices"
    )


class IQACRequest(BaseModel):
    """Request for IQAC documentation"""
    institution: InstitutionInfo
    academic_year: str = Field(default="2024-25")


class GreenAuditRequest(BaseModel):
    """Request for green/environmental audit"""
    institution: InstitutionInfo
    audit_year: str = Field(default="2024-25")


# ==================== RESPONSE MODELS ====================

class AccreditationResponse(BaseModel):
    """Standard response for accreditation documents"""
    success: bool
    criterion: Optional[str] = None
    documents: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ==================== OVERVIEW ENDPOINTS ====================

@router.get("/overview", tags=["NAAC Overview"])
async def get_naac_overview():
    """
    Get overview of all 7 NAAC criteria with marks distribution.
    """
    return naac_nba_agent.get_criteria_overview()


@router.get("/criteria", tags=["NAAC Overview"])
async def list_criteria():
    """
    List all NAAC criteria with key indicators.
    """
    return {
        "criteria": [
            {
                "number": 1,
                "name": "Curricular Aspects",
                "marks": 150,
                "key_indicators": ["1.1 Curricular Planning", "1.2 Academic Flexibility",
                                   "1.3 Curriculum Enrichment", "1.4 Feedback System"]
            },
            {
                "number": 2,
                "name": "Teaching-Learning and Evaluation",
                "marks": 200,
                "key_indicators": ["2.1 Student Enrollment", "2.2 Student Diversity",
                                   "2.3 Teaching-Learning Process", "2.4 Teacher Quality",
                                   "2.5 Evaluation Process", "2.6 Learning Outcomes"]
            },
            {
                "number": 3,
                "name": "Research, Innovations and Extension",
                "marks": 150,
                "key_indicators": ["3.1 Research Promotion", "3.2 Resource Mobilization",
                                   "3.3 Innovation Ecosystem", "3.4 Publications",
                                   "3.5 Consultancy", "3.6 Extension", "3.7 Collaboration"]
            },
            {
                "number": 4,
                "name": "Infrastructure and Learning Resources",
                "marks": 100,
                "key_indicators": ["4.1 Physical Facilities", "4.2 Library",
                                   "4.3 IT Infrastructure", "4.4 Maintenance"]
            },
            {
                "number": 5,
                "name": "Student Support and Progression",
                "marks": 100,
                "key_indicators": ["5.1 Student Support", "5.2 Student Progression",
                                   "5.3 Student Participation", "5.4 Alumni Engagement"]
            },
            {
                "number": 6,
                "name": "Governance, Leadership and Management",
                "marks": 100,
                "key_indicators": ["6.1 Vision & Leadership", "6.2 Strategy",
                                   "6.3 Faculty Empowerment", "6.4 Financial Management",
                                   "6.5 IQAC"]
            },
            {
                "number": 7,
                "name": "Institutional Values and Best Practices",
                "marks": 100,
                "key_indicators": ["7.1 Values & Social Responsibility",
                                   "7.2 Best Practices", "7.3 Distinctiveness"]
            }
        ],
        "total_marks": 700,
        "grading_scale": {
            "A++": "CGPA 3.51-4.00",
            "A+": "CGPA 3.26-3.50",
            "A": "CGPA 3.01-3.25",
            "B++": "CGPA 2.76-3.00",
            "B+": "CGPA 2.51-2.75",
            "B": "CGPA 2.01-2.50",
            "C": "CGPA 1.51-2.00",
            "D": "CGPA ≤1.50"
        }
    }


# ==================== COMPLETE SSR ENDPOINT ====================

@router.post("/ssr/generate", response_model=AccreditationResponse, tags=["Complete SSR"])
async def generate_complete_ssr(request: SSRRequest):
    """
    Generate complete Self Study Report (SSR) structure for all 7 criteria.

    This generates templates, guidelines, and document structures for:
    - Part A: Institutional Data
    - Part B: All 7 Criteria
    - Extended Profile
    - Quality Indicator Framework (QIF)
    """
    try:
        context = AgentContext(
            user_request=f"Generate complete SSR for {request.institution.name}",
            project_id=f"ssr-{request.institution.name[:10]}",
            metadata={
                "doc_type": "full_ssr",
                **request.institution.model_dump(),
                "academic_year": request.academic_year,
                "naac_cycle": request.naac_cycle
            }
        )

        result = await naac_nba_agent.generate_full_ssr(context)

        return AccreditationResponse(
            success=True,
            documents=result.get("content", {}),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating SSR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRITERION-WISE ENDPOINTS ====================

@router.post("/criterion/{criterion_number}", response_model=AccreditationResponse, tags=["Criterion-wise"])
async def generate_criterion_documents(
    criterion_number: int,
    request: CriterionRequest
):
    """
    Generate documents for a specific NAAC criterion (1-7).

    - Criterion 1: Curricular Aspects (150 marks)
    - Criterion 2: Teaching-Learning and Evaluation (200 marks)
    - Criterion 3: Research, Innovations and Extension (150 marks)
    - Criterion 4: Infrastructure and Learning Resources (100 marks)
    - Criterion 5: Student Support and Progression (100 marks)
    - Criterion 6: Governance, Leadership and Management (100 marks)
    - Criterion 7: Institutional Values and Best Practices (100 marks)
    """
    if criterion_number < 1 or criterion_number > 7:
        raise HTTPException(status_code=400, detail="Criterion must be between 1 and 7")

    criterion_map = {
        1: NAACCriterion.CRITERION_1,
        2: NAACCriterion.CRITERION_2,
        3: NAACCriterion.CRITERION_3,
        4: NAACCriterion.CRITERION_4,
        5: NAACCriterion.CRITERION_5,
        6: NAACCriterion.CRITERION_6,
        7: NAACCriterion.CRITERION_7,
    }

    try:
        context = AgentContext(
            user_request=request.additional_context or f"Generate Criterion {criterion_number} documentation",
            project_id=f"criterion-{criterion_number}-{request.institution.name[:10]}",
            metadata={
                "criterion": criterion_map[criterion_number].value,
                **request.institution.model_dump(),
                "academic_year": request.academic_year
            }
        )

        # Call appropriate criterion generator
        generators = {
            1: naac_nba_agent.generate_criterion_1,
            2: naac_nba_agent.generate_criterion_2,
            3: naac_nba_agent.generate_criterion_3,
            4: naac_nba_agent.generate_criterion_4,
            5: naac_nba_agent.generate_criterion_5,
            6: naac_nba_agent.generate_criterion_6,
            7: naac_nba_agent.generate_criterion_7,
        }

        result = await generators[criterion_number](context)

        return AccreditationResponse(
            success=True,
            criterion=f"Criterion {criterion_number}",
            documents=result.get("content", {}),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating Criterion {criterion_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRITERION 2: OBE ENDPOINTS ====================

@router.post("/obe/course-outcomes", response_model=AccreditationResponse, tags=["OBE (Criterion 2)"])
async def generate_course_outcomes(request: OBERequest):
    """
    Generate Course Outcomes (COs) with Bloom's Taxonomy levels.

    Each CO includes:
    - Statement with action verb
    - Bloom's Taxonomy level (L1-L6)
    - Assessment methods
    - Knowledge domain
    """
    try:
        context = AgentContext(
            user_request=request.project_description,
            project_id=f"co-{request.course_info.course_code}",
            metadata={
                "doc_type": AccreditationDocType.COURSE_OUTCOMES.value,
                **request.course_info.model_dump()
            }
        )

        result = await naac_nba_agent.generate_course_outcomes(context)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 2 - OBE",
            documents={"course_outcomes": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating course outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/obe/co-po-mapping", response_model=AccreditationResponse, tags=["OBE (Criterion 2)"])
async def generate_co_po_mapping(request: COPOMappingRequest):
    """
    Generate CO-PO Mapping Matrix.

    Maps Course Outcomes to 12 NBA Program Outcomes with:
    - Correlation levels (1-3)
    - Justifications
    - Attainment calculations
    """
    try:
        context = AgentContext(
            user_request="Generate CO-PO mapping",
            project_id=f"copo-{request.course_info.course_code}",
            metadata={
                "doc_type": AccreditationDocType.CO_PO_MAPPING.value,
                **request.course_info.model_dump()
            }
        )

        result = await naac_nba_agent.generate_co_po_mapping(context, request.course_outcomes)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 2 - OBE",
            documents={"co_po_mapping": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating CO-PO mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/obe/rubrics", response_model=AccreditationResponse, tags=["OBE (Criterion 2)"])
async def generate_rubrics(request: RubricsRequest):
    """
    Generate Assessment Rubrics with 4 performance levels.

    Includes:
    - Multiple criteria
    - Performance descriptors
    - Weightage distribution
    - CO mapping
    """
    try:
        context = AgentContext(
            user_request=f"Generate rubrics for {request.assessment_type}",
            project_id=f"rubric-{request.course_info.course_code}",
            metadata={
                "doc_type": AccreditationDocType.RUBRICS.value,
                "assessment_type": request.assessment_type,
                "criteria_count": request.criteria_count,
                **request.course_info.model_dump()
            }
        )

        result = await naac_nba_agent.generate_rubrics(context, request.assessment_type)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 2 - OBE",
            documents={"rubrics": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating rubrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/obe/attainment", response_model=AccreditationResponse, tags=["OBE (Criterion 2)"])
async def generate_attainment_template(request: OBERequest):
    """
    Generate Attainment Calculation templates.

    Includes:
    - Direct assessment methods
    - Indirect assessment methods
    - Calculation formulas
    - Target levels
    """
    try:
        context = AgentContext(
            user_request=request.project_description,
            project_id=f"attain-{request.course_info.course_code}",
            metadata={
                "doc_type": AccreditationDocType.ATTAINMENT.value,
                **request.course_info.model_dump()
            }
        )

        result = await naac_nba_agent.process(context)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 2 - OBE",
            documents={"attainment": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating attainment template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRITERION 6: IQAC ENDPOINTS ====================

@router.post("/iqac/report", response_model=AccreditationResponse, tags=["IQAC (Criterion 6)"])
async def generate_iqac_documentation(request: IQACRequest):
    """
    Generate IQAC documentation for Criterion 6.5.

    Includes:
    - IQAC composition
    - Meeting templates
    - AQAR structure
    - Quality initiatives
    """
    try:
        context = AgentContext(
            user_request=f"Generate IQAC documentation for {request.institution.name}",
            project_id=f"iqac-{request.institution.name[:10]}",
            metadata={
                "doc_type": AccreditationDocType.IQAC.value,
                **request.institution.model_dump(),
                "academic_year": request.academic_year
            }
        )

        result = await naac_nba_agent.generate_iqac_report(context)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 6 - IQAC",
            documents={"iqac": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating IQAC documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRITERION 7: BEST PRACTICES & GREEN AUDIT ====================

@router.post("/best-practices", response_model=AccreditationResponse, tags=["Best Practices (Criterion 7)"])
async def generate_best_practices(request: BestPracticesRequest):
    """
    Generate TWO Best Practices for Criterion 7.2.

    Each practice includes:
    - Title and objectives
    - Context and need
    - Implementation details
    - Evidence of success
    - Resources required
    """
    try:
        context = AgentContext(
            user_request=f"Generate best practices for {request.institution.name}",
            project_id=f"bp-{request.institution.name[:10]}",
            metadata={
                "doc_type": AccreditationDocType.BEST_PRACTICES.value,
                **request.institution.model_dump(),
                "focus_areas": request.focus_areas
            }
        )

        result = await naac_nba_agent.generate_best_practices(context)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 7 - Best Practices",
            documents={"best_practices": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating best practices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/green-audit", response_model=AccreditationResponse, tags=["Green Audit (Criterion 7)"])
async def generate_green_audit(request: GreenAuditRequest):
    """
    Generate Green/Environmental Audit documentation for Criterion 7.1.

    Includes:
    - Energy audit
    - Water management
    - Waste management
    - Green campus initiatives
    - Environmental policy
    """
    try:
        context = AgentContext(
            user_request=f"Generate green audit for {request.institution.name}",
            project_id=f"green-{request.institution.name[:10]}",
            metadata={
                "doc_type": AccreditationDocType.ENVIRONMENTAL_CONSCIOUSNESS.value,
                **request.institution.model_dump(),
                "audit_year": request.audit_year
            }
        )

        result = await naac_nba_agent.process(context)

        return AccreditationResponse(
            success=True,
            criterion="Criterion 7 - Green Audit",
            documents={"green_audit": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating green audit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== REFERENCE ENDPOINTS ====================

@router.get("/program-outcomes", tags=["Reference"])
async def get_program_outcomes():
    """Get the 12 NBA Program Outcomes (POs)."""
    return {
        "program_outcomes": [
            {"id": "PO1", "name": "Engineering Knowledge", "description": "Apply the knowledge of mathematics, science, engineering fundamentals, and an engineering specialization to the solution of complex engineering problems."},
            {"id": "PO2", "name": "Problem Analysis", "description": "Identify, formulate, review research literature, and analyze complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences, and engineering sciences."},
            {"id": "PO3", "name": "Design/Development of Solutions", "description": "Design solutions for complex engineering problems and design system components or processes that meet the specified needs with appropriate consideration for public health and safety, and cultural, societal, and environmental considerations."},
            {"id": "PO4", "name": "Conduct Investigations", "description": "Use research-based knowledge and research methods including design of experiments, analysis and interpretation of data, and synthesis of the information to provide valid conclusions."},
            {"id": "PO5", "name": "Modern Tool Usage", "description": "Create, select, and apply appropriate techniques, resources, and modern engineering and IT tools including prediction and modeling to complex engineering activities with an understanding of the limitations."},
            {"id": "PO6", "name": "Engineer and Society", "description": "Apply reasoning informed by the contextual knowledge to assess societal, health, safety, legal, and cultural issues and the consequent responsibilities relevant to the professional engineering practice."},
            {"id": "PO7", "name": "Environment and Sustainability", "description": "Understand the impact of the professional engineering solutions in societal and environmental contexts, and demonstrate the knowledge of, and need for sustainable development."},
            {"id": "PO8", "name": "Ethics", "description": "Apply ethical principles and commit to professional ethics and responsibilities and norms of the engineering practice."},
            {"id": "PO9", "name": "Individual and Team Work", "description": "Function effectively as an individual, and as a member or leader in diverse teams, and in multidisciplinary settings."},
            {"id": "PO10", "name": "Communication", "description": "Communicate effectively on complex engineering activities with the engineering community and with society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations, and give and receive clear instructions."},
            {"id": "PO11", "name": "Project Management and Finance", "description": "Demonstrate knowledge and understanding of the engineering and management principles and apply these to one's own work, as a member and leader in a team, to manage projects and in multidisciplinary environments."},
            {"id": "PO12", "name": "Life-long Learning", "description": "Recognize the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change."},
        ],
        "source": "NBA (National Board of Accreditation)"
    }


@router.get("/blooms-taxonomy", tags=["Reference"])
async def get_blooms_taxonomy():
    """Get Bloom's Taxonomy levels with action verbs."""
    return {
        "taxonomy": {
            "L1": {"name": "Remember", "description": "Recall facts and basic concepts", "verbs": ["Define", "List", "State", "Identify", "Recall", "Name", "Recognize", "Match"]},
            "L2": {"name": "Understand", "description": "Explain ideas or concepts", "verbs": ["Describe", "Explain", "Summarize", "Classify", "Compare", "Interpret", "Discuss"]},
            "L3": {"name": "Apply", "description": "Use information in new situations", "verbs": ["Apply", "Demonstrate", "Implement", "Solve", "Use", "Execute", "Calculate"]},
            "L4": {"name": "Analyze", "description": "Draw connections among ideas", "verbs": ["Analyze", "Differentiate", "Examine", "Compare", "Contrast", "Investigate", "Test"]},
            "L5": {"name": "Evaluate", "description": "Justify a stand or decision", "verbs": ["Evaluate", "Justify", "Critique", "Assess", "Judge", "Recommend", "Defend"]},
            "L6": {"name": "Create", "description": "Produce new or original work", "verbs": ["Design", "Develop", "Create", "Construct", "Produce", "Formulate", "Build"]},
        },
        "source": "Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001)"
    }


@router.get("/document-types", tags=["Reference"])
async def get_document_types():
    """Get all supported document types by criterion."""
    return {
        "criterion_1": {
            "name": "Curricular Aspects",
            "documents": ["curriculum_design", "academic_flexibility", "curriculum_enrichment", "feedback_system"]
        },
        "criterion_2": {
            "name": "Teaching-Learning and Evaluation",
            "documents": ["course_outcomes", "program_outcomes", "co_po_mapping", "rubrics", "attainment", "student_centric_methods"]
        },
        "criterion_3": {
            "name": "Research, Innovations and Extension",
            "documents": ["research_promotion", "resource_mobilization", "innovation_ecosystem", "research_publications", "consultancy", "extension_activities", "collaboration"]
        },
        "criterion_4": {
            "name": "Infrastructure and Learning Resources",
            "documents": ["physical_facilities", "library_resources", "it_infrastructure", "maintenance"]
        },
        "criterion_5": {
            "name": "Student Support and Progression",
            "documents": ["scholarships", "capability_enhancement", "student_progression", "alumni_engagement"]
        },
        "criterion_6": {
            "name": "Governance, Leadership and Management",
            "documents": ["vision_mission", "strategic_plan", "faculty_empowerment", "financial_management", "iqac"]
        },
        "criterion_7": {
            "name": "Institutional Values and Best Practices",
            "documents": ["gender_equity", "environmental_consciousness", "inclusiveness", "best_practices", "institutional_distinctiveness"]
        }
    }


# ==================== DOCUMENT DOWNLOAD ENDPOINTS ====================

class DownloadRequest(BaseModel):
    """Request for downloading document in various formats"""
    content: Dict[str, Any] = Field(..., description="Document content")
    title: str = Field(..., description="Document title")
    format: str = Field(default="word", description="Output format: word or pdf")


# ==================== CURRICULUM MAPPING REQUEST MODELS ====================

class CurriculumMappingRequest(BaseModel):
    """Request for curriculum-to-project mapping"""
    course_name: str = Field(..., description="Course name")
    course_code: str = Field(..., description="Course code")
    department: str = Field(..., description="Department")
    semester: int = Field(..., ge=1, le=8, description="Semester")
    credits: int = Field(default=3, ge=1, le=6, description="Credits")
    syllabus_topics: List[str] = Field(..., description="List of syllabus topics")
    course_description: Optional[str] = Field(None, description="Course description")
    num_suggestions: int = Field(default=5, ge=1, le=10, description="Number of project suggestions")
    difficulty_filter: Optional[str] = Field(None, description="Filter by difficulty: beginner, intermediate, advanced, expert")


class IndustryUseCaseRequest(BaseModel):
    """Request for industry use cases"""
    domain: str = Field(..., description="Technology domain (web, mobile, ai_ml, data_science, etc.)")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of use cases")


# ==================== EVALUATION REQUEST MODELS ====================

class ProjectEvaluationRequest(BaseModel):
    """Request for project evaluation"""
    project_id: str = Field(..., description="Project ID")
    files: Dict[str, str] = Field(..., description="Dictionary of file paths to file contents")
    custom_rubric: Optional[Dict[str, Any]] = Field(None, description="Custom evaluation rubric")
    course_outcomes: Optional[List[str]] = Field(None, description="Course outcomes to assess")


class AttainmentCalculationRequest(BaseModel):
    """Request for CO-PO attainment calculation"""
    project_id: str = Field(..., description="Project ID")
    evaluation_scores: Dict[str, float] = Field(..., description="Evaluation scores per criterion")
    course_outcomes: List[Dict[str, Any]] = Field(..., description="Course outcomes with mappings")


# ==================== CERTIFICATION REQUEST MODELS ====================

class CertificateGenerationRequest(BaseModel):
    """Request for certificate generation"""
    student_name: str = Field(..., description="Student name")
    student_id: str = Field(..., description="Student ID")
    institution_name: str = Field(..., description="Institution name")
    department: str = Field(..., description="Department")
    certificate_type: str = Field(default="project_completion", description="Type of certificate")
    project_data: Optional[Dict[str, Any]] = Field(None, description="Project details")
    evaluation_result: Optional[Dict[str, Any]] = Field(None, description="Evaluation results")
    skills: Optional[List[Dict[str, Any]]] = Field(None, description="Skills demonstrated")
    faculty_name: Optional[str] = Field(None, description="Faculty advisor name")


class SkillBadgeRequest(BaseModel):
    """Request for skill badge generation"""
    student_name: str = Field(..., description="Student name")
    student_id: str = Field(..., description="Student ID")
    skill_name: str = Field(..., description="Skill name")
    skill_level: str = Field(default="intermediate", description="Skill level")
    assessment_score: float = Field(..., ge=0, le=100, description="Assessment score")
    hours_practiced: int = Field(default=0, ge=0, description="Hours practiced")
    projects_completed: int = Field(default=1, ge=0, description="Projects completed")


class CertificateVerificationRequest(BaseModel):
    """Request for certificate verification"""
    verification_code: str = Field(..., description="Certificate verification code")


@router.post("/download", tags=["Download"])
async def download_document(request: DownloadRequest):
    """
    Download accreditation document in Word or PDF format.

    Converts JSON content to formatted document.
    """
    try:
        from app.utils.document_generator import document_generator

        if request.format == "word":
            # Generate Word document
            doc_bytes = document_generator.generate_accreditation_docx(
                content=request.content,
                title=request.title
            )
            filename = f"{request.title.replace(' ', '_')}.docx"
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        elif request.format == "pdf":
            # Generate PDF document
            doc_bytes = document_generator.generate_accreditation_pdf(
                content=request.content,
                title=request.title
            )
            filename = f"{request.title.replace(' ', '_')}.pdf"
            media_type = "application/pdf"

        else:
            raise HTTPException(status_code=400, detail="Format must be 'word' or 'pdf'")

        return StreamingResponse(
            io.BytesIO(doc_bytes),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CURRICULUM MAPPING ENDPOINTS ====================

@router.post("/curriculum/map", tags=["Curriculum Mapping"])
async def map_curriculum_to_projects(request: CurriculumMappingRequest):
    """
    Map course curriculum to industry project suggestions.

    Features:
    - AI-powered project suggestions based on syllabus topics
    - CO-PO mapping for each suggested project
    - Difficulty-appropriate recommendations
    - Industry-aligned use cases
    """
    try:
        # Create course info object
        course = CurriculumCourseInfo(
            course_name=request.course_name,
            course_code=request.course_code,
            department=request.department,
            semester=request.semester,
            credits=request.credits,
            topics=request.syllabus_topics  # Map API field to internal field
        )

        # Parse difficulty filter
        difficulty = None
        if request.difficulty_filter:
            try:
                difficulty = DifficultyLevel(request.difficulty_filter)
            except ValueError:
                pass

        # Get project suggestions
        suggestions = curriculum_mapping_engine.map_course_to_projects(
            course=course,
            num_suggestions=request.num_suggestions,
            difficulty_filter=difficulty
        )

        return {
            "success": True,
            "course": {
                "name": request.course_name,
                "code": request.course_code,
                "department": request.department
            },
            "suggestions": [
                {
                    "title": s.title,
                    "description": s.description,
                    "difficulty": s.difficulty.value,
                    "project_type": s.project_type.value,
                    "domain": s.domain.value,
                    "technologies": s.technologies,
                    "estimated_duration": f"{s.duration_weeks} weeks",
                    "duration_weeks": s.duration_weeks,
                    "team_size": s.team_size,
                    "course_outcomes": s.course_outcomes_mapped,
                    "po_mapping": {po: 3 for po in s.program_outcomes_mapped},  # Convert list to dict
                    "blooms_levels": s.blooms_levels,
                    "industry_relevance": s.industry_relevance,
                    "learning_objectives": s.learning_objectives,
                    "deliverables": s.deliverables,
                    "evaluation_criteria": s.evaluation_criteria,
                    "relevance_score": 0.85  # Default relevance score
                }
                for s in suggestions
            ],
            "total_suggestions": len(suggestions)
        }

    except Exception as e:
        logger.error(f"Error mapping curriculum: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/curriculum/domains", tags=["Curriculum Mapping"])
async def get_technology_domains():
    """Get all supported technology domains."""
    return {
        "domains": [
            {"id": d.value, "name": d.value.replace("_", " ").title()}
            for d in TechnologyDomain
        ]
    }


@router.get("/curriculum/difficulty-levels", tags=["Curriculum Mapping"])
async def get_difficulty_levels():
    """Get all difficulty levels with descriptions."""
    return {
        "levels": [
            {"id": "beginner", "name": "Beginner", "description": "1-2 weeks, basic concepts"},
            {"id": "intermediate", "name": "Intermediate", "description": "2-4 weeks, moderate complexity"},
            {"id": "advanced", "name": "Advanced", "description": "4-8 weeks, complex implementation"},
            {"id": "expert", "name": "Expert", "description": "8+ weeks, research-level project"}
        ]
    }


# ==================== INDUSTRY USE-CASE LIBRARY ENDPOINTS ====================

@router.post("/industry/use-cases", tags=["Industry Use-Cases"])
async def get_industry_use_cases(request: IndustryUseCaseRequest):
    """
    Get industry use cases by domain and difficulty.

    Features:
    - 50+ pre-built industry project templates
    - Domain-specific use cases
    - Difficulty filtering
    - CO-PO mappings included
    """
    try:
        # Parse domain
        try:
            domain = TechnologyDomain(request.domain)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid domain: {request.domain}")

        # Get use cases
        use_cases = industry_library.get_use_cases_by_domain(domain)

        # Filter by difficulty if specified
        if request.difficulty:
            try:
                difficulty = DifficultyLevel(request.difficulty)
                use_cases = [uc for uc in use_cases if uc.get("difficulty") == difficulty.value]
            except ValueError:
                pass

        # Limit results
        use_cases = use_cases[:request.limit]

        return {
            "success": True,
            "domain": request.domain,
            "use_cases": [
                {
                    "id": f"UC-{request.domain.upper()[:3]}-{i+1:03d}",
                    "title": uc.get("title", ""),
                    "description": uc.get("description", ""),
                    "difficulty": uc.get("difficulty", "intermediate"),
                    "technologies": uc.get("technologies", []),
                    "duration_weeks": uc.get("duration_weeks", 4),
                    "course_outcomes": uc.get("learning_objectives", []),
                    "po_mapping": {"PO1": 3, "PO3": 2, "PO5": 3, "PO9": 2, "PO12": 2},  # Default PO mapping
                    "deliverables": uc.get("deliverables", []),
                    "industry_relevance": uc.get("industry_relevance", ""),
                    "team_size": uc.get("team_size", 2),
                    "evaluation_criteria": uc.get("evaluation_criteria", [])
                }
                for i, uc in enumerate(use_cases)
            ],
            "total": len(use_cases)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting industry use cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/all-domains", tags=["Industry Use-Cases"])
async def get_all_industry_use_cases():
    """Get use cases from all domains."""
    try:
        all_use_cases = industry_library.get_all_use_cases()

        # Group by domain
        by_domain = {}
        for uc in all_use_cases:
            domain = uc.domain.value
            if domain not in by_domain:
                by_domain[domain] = []
            by_domain[domain].append({
                "id": uc.id,
                "title": uc.title,
                "difficulty": uc.difficulty.value
            })

        return {
            "success": True,
            "by_domain": by_domain,
            "total_use_cases": len(all_use_cases)
        }

    except Exception as e:
        logger.error(f"Error getting all use cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== PROJECT EVALUATION ENDPOINTS ====================

@router.post("/evaluation/evaluate", tags=["Project Evaluation"])
async def evaluate_project(request: ProjectEvaluationRequest):
    """
    Evaluate a project using automated rubric-based assessment.

    Features:
    - Code quality analysis
    - Architecture evaluation
    - Documentation assessment
    - Security check
    - CO attainment calculation
    """
    try:
        # Create custom rubric if provided
        rubric = None
        if request.custom_rubric:
            criteria = []
            for c in request.custom_rubric.get("criteria", []):
                # Build levels dict from indicators if provided
                indicators = c.get("indicators", [])
                levels = c.get("levels", {})
                if not levels and indicators:
                    levels = {f"Level {i+1}": ind for i, ind in enumerate(indicators[:4])}

                criteria.append(RubricCriterion(
                    name=c.get("name", ""),
                    description=c.get("description", ""),
                    max_points=c.get("max_score", c.get("max_points", 10)),
                    levels=levels if levels else {"Excellent": "Meets all criteria", "Good": "Meets most criteria", "Satisfactory": "Meets some criteria", "Needs Improvement": "Needs work"},
                    co_mapped=c.get("co_mapping", c.get("co_mapped", [])),
                    po_mapped=c.get("po_mapping", c.get("po_mapped", []))
                ))
            total_points = sum(c.max_points for c in criteria)
            rubric = EvaluationRubric(
                name=request.custom_rubric.get("name", "Custom Rubric"),
                total_points=total_points,
                criteria=criteria
            )

        # Evaluate project
        result = project_evaluator.evaluate_project(
            project_id=request.project_id,
            files=request.files,
            rubric=rubric
        )

        return {
            "success": True,
            "project_id": result.project_id,
            "total_score": result.total_score,
            "max_score": result.max_score,
            "percentage": result.percentage,
            "grade": result.grade.value,
            "criteria_scores": result.criteria_scores,
            "co_attainment": result.co_attainment,
            "po_contribution": result.po_attainment,
            "strengths": result.strengths,
            "improvements": result.improvements,
            "overall_feedback": result.detailed_feedback,
            "evaluated_at": result.evaluated_at
        }

    except Exception as e:
        logger.error(f"Error evaluating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation/rubrics", tags=["Project Evaluation"])
async def get_default_rubric():
    """Get the default evaluation rubric."""
    rubric = project_evaluator.default_rubric
    return {
        "name": rubric.name,
        "total_points": rubric.total_points,
        "criteria": [
            {
                "name": c.name,
                "description": c.description,
                "max_points": c.max_points,
                "levels": c.levels,
                "co_mapped": c.co_mapped,
                "po_mapped": c.po_mapped
            }
            for c in rubric.criteria
        ],
        "total_max_score": sum(c.max_points for c in rubric.criteria)
    }


@router.post("/evaluation/attainment", tags=["Project Evaluation"])
async def calculate_attainment(request: AttainmentCalculationRequest):
    """
    Calculate CO-PO attainment from evaluation scores.

    Features:
    - Direct attainment calculation
    - Target vs achieved comparison
    - Attainment percentage
    """
    try:
        attainment = project_evaluator.calculate_attainment(
            evaluation_scores=request.evaluation_scores,
            course_outcomes=request.course_outcomes
        )

        return {
            "success": True,
            "project_id": request.project_id,
            "co_attainment": attainment.get("co_attainment", {}),
            "po_contribution": attainment.get("po_contribution", {}),
            "overall_attainment": attainment.get("overall_attainment", 0)
        }

    except Exception as e:
        logger.error(f"Error calculating attainment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluation/grade-scale", tags=["Project Evaluation"])
async def get_grade_scale():
    """Get the grading scale used for evaluation."""
    return {
        "grades": [
            {"grade": "A+", "range": "90-100%", "description": "Exceptional"},
            {"grade": "A", "range": "80-89%", "description": "Excellent"},
            {"grade": "B+", "range": "70-79%", "description": "Very Good"},
            {"grade": "B", "range": "60-69%", "description": "Good"},
            {"grade": "C+", "range": "50-59%", "description": "Satisfactory"},
            {"grade": "C", "range": "40-49%", "description": "Pass"},
            {"grade": "F", "range": "Below 40%", "description": "Fail"}
        ]
    }


# ==================== CERTIFICATION ENDPOINTS ====================

@router.post("/certification/generate", tags=["Certification"])
async def generate_certificate(request: CertificateGenerationRequest):
    """
    Generate a skill certificate with OBE metrics.

    Features:
    - Auto-generate from project data
    - Skill proficiency mapping
    - CO-PO attainment visualization
    - Verification QR code
    """
    try:
        # Parse certificate type
        try:
            cert_type = CertificateType(request.certificate_type)
        except ValueError:
            cert_type = CertificateType.PROJECT_COMPLETION

        # Generate certificate
        certificate = certificate_generator.generate_certificate(
            student_name=request.student_name,
            student_id=request.student_id,
            institution_name=request.institution_name,
            department=request.department,
            certificate_type=cert_type,
            project_data=request.project_data,
            evaluation_result=request.evaluation_result,
            skills=request.skills,
            faculty_name=request.faculty_name
        )

        # Return certificate data as JSON
        return {
            "success": True,
            "certificate": certificate_generator.get_certificate_json(certificate)
        }

    except Exception as e:
        logger.error(f"Error generating certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/certification/badge", tags=["Certification"])
async def generate_skill_badge(request: SkillBadgeRequest):
    """
    Generate a skill badge for specific skill proficiency.

    Features:
    - Skill-specific badges
    - Level indicators
    - Verification support
    """
    try:
        # Parse skill level
        try:
            level = SkillLevel(request.skill_level)
        except ValueError:
            level = SkillLevel.INTERMEDIATE

        badge = certificate_generator.generate_skill_badge(
            student_name=request.student_name,
            student_id=request.student_id,
            skill_name=request.skill_name,
            skill_level=level,
            assessment_score=request.assessment_score,
            hours_practiced=request.hours_practiced,
            projects_completed=request.projects_completed
        )

        return {
            "success": True,
            "badge": badge
        }

    except Exception as e:
        logger.error(f"Error generating skill badge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/certification/verify", tags=["Certification"])
async def verify_certificate(request: CertificateVerificationRequest):
    """
    Verify a certificate by its verification code.

    Features:
    - Certificate authenticity check
    - Expiry validation
    - Basic certificate details
    """
    try:
        result = certificate_generator.verify_certificate(request.verification_code)

        return {
            "success": result.get("verified", False),
            "verification_result": result
        }

    except Exception as e:
        logger.error(f"Error verifying certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certification/types", tags=["Certification"])
async def get_certificate_types():
    """Get all available certificate types."""
    return {
        "types": [
            {"id": "project_completion", "name": "Project Completion Certificate"},
            {"id": "skill_proficiency", "name": "Skill Proficiency Certificate"},
            {"id": "course_completion", "name": "Course Completion Certificate"},
            {"id": "internship", "name": "Internship Certificate"},
            {"id": "hackathon", "name": "Hackathon Certificate"},
            {"id": "workshop", "name": "Workshop Certificate"},
            {"id": "assessment", "name": "Assessment Certificate"}
        ]
    }


@router.post("/certification/html", tags=["Certification"])
async def get_certificate_html(request: CertificateGenerationRequest):
    """
    Generate certificate as HTML for preview or printing.

    Returns styled HTML that can be converted to PDF client-side.
    """
    try:
        # Parse certificate type
        try:
            cert_type = CertificateType(request.certificate_type)
        except ValueError:
            cert_type = CertificateType.PROJECT_COMPLETION

        # Generate certificate
        certificate = certificate_generator.generate_certificate(
            student_name=request.student_name,
            student_id=request.student_id,
            institution_name=request.institution_name,
            department=request.department,
            certificate_type=cert_type,
            project_data=request.project_data,
            evaluation_result=request.evaluation_result,
            skills=request.skills,
            faculty_name=request.faculty_name
        )

        # Get HTML
        html = certificate_generator.get_certificate_html(certificate)

        return {
            "success": True,
            "certificate_id": certificate.certificate_id,
            "html": html,
            "verification_code": certificate.verification_code,
            "verification_url": certificate.verification_url
        }

    except Exception as e:
        logger.error(f"Error generating certificate HTML: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/certification/skill-categories", tags=["Certification"])
async def get_skill_categories():
    """Get all skill categories and their constituent skills."""
    return {
        "categories": certificate_generator.skill_categories
    }


# ==================== CRITERION 1: CURRICULAR ASPECTS ====================
# Key Indicators:
# 1.1 - Curriculum Planning and Implementation
# 1.2 - Academic Flexibility
# 1.3 - Curriculum Enrichment (Value-added courses, Internships)
# 1.4 - Feedback System


# ==================== FEEDBACK MANAGEMENT (Key Indicator 1.4) ====================

@router.post("/criterion1/feedback", response_model=FeedbackResponse, tags=["Criterion 1 - Feedback"])
async def create_feedback(request: FeedbackCreate, db: Session = Depends(get_db)):
    """
    Create curriculum feedback from stakeholders.

    Supports feedback from:
    - Students
    - Alumni
    - Employers
    - Teachers
    - Industry Experts
    - Parents
    """
    try:
        feedback = CurriculumFeedback(
            feedback_type=FeedbackTypeEnum(request.feedback_type.value),
            respondent_name=request.respondent_name,
            respondent_email=request.respondent_email,
            respondent_organization=request.respondent_organization,
            respondent_designation=request.respondent_designation,
            department=request.department,
            program=request.program,
            course_code=request.course_code,
            course_name=request.course_name,
            academic_year=request.academic_year,
            semester=request.semester,
            feedback_content=request.feedback_content,
            rating=request.rating,
            suggestions=request.suggestions,
            structured_responses=request.structured_responses,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return FeedbackResponse(
            id=str(feedback.id),
            feedback_type=feedback.feedback_type.value,
            respondent_name=feedback.respondent_name,
            respondent_email=feedback.respondent_email,
            respondent_organization=feedback.respondent_organization,
            respondent_designation=feedback.respondent_designation,
            department=feedback.department,
            program=feedback.program,
            course_code=feedback.course_code,
            course_name=feedback.course_name,
            academic_year=feedback.academic_year,
            semester=feedback.semester,
            feedback_content=feedback.feedback_content,
            rating=feedback.rating,
            suggestions=feedback.suggestions,
            structured_responses=feedback.structured_responses,
            status=feedback.status.value,
            reviewed_by=feedback.reviewed_by,
            reviewed_at=feedback.reviewed_at,
            action_taken=feedback.action_taken,
            action_date=feedback.action_date,
            action_evidence=feedback.action_evidence,
            submitted_at=feedback.submitted_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )
    except Exception as e:
        logger.error(f"Error creating feedback: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion1/feedback", response_model=FeedbackListResponse, tags=["Criterion 1 - Feedback"])
async def list_feedback(
    feedback_type: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List curriculum feedback with filters.
    """
    try:
        query = db.query(CurriculumFeedback)

        if feedback_type:
            query = query.filter(CurriculumFeedback.feedback_type == FeedbackTypeEnum(feedback_type))
        if status:
            query = query.filter(CurriculumFeedback.status == FeedbackStatusEnum(status))
        if department:
            query = query.filter(CurriculumFeedback.department == department)
        if academic_year:
            query = query.filter(CurriculumFeedback.academic_year == academic_year)

        total = query.count()
        items = query.order_by(CurriculumFeedback.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return FeedbackListResponse(
            items=[FeedbackResponse(
                id=str(f.id),
                feedback_type=f.feedback_type.value,
                respondent_name=f.respondent_name,
                respondent_email=f.respondent_email,
                respondent_organization=f.respondent_organization,
                respondent_designation=f.respondent_designation,
                department=f.department,
                program=f.program,
                course_code=f.course_code,
                course_name=f.course_name,
                academic_year=f.academic_year,
                semester=f.semester,
                feedback_content=f.feedback_content,
                rating=f.rating,
                suggestions=f.suggestions,
                structured_responses=f.structured_responses,
                status=f.status.value,
                reviewed_by=f.reviewed_by,
                reviewed_at=f.reviewed_at,
                action_taken=f.action_taken,
                action_date=f.action_date,
                action_evidence=f.action_evidence,
                submitted_at=f.submitted_at,
                created_at=f.created_at,
                updated_at=f.updated_at,
            ) for f in items],
            total=total,
            page=page,
            page_size=page_size,
            filters={"feedback_type": feedback_type, "status": status, "department": department, "academic_year": academic_year}
        )
    except Exception as e:
        logger.error(f"Error listing feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion1/feedback/{feedback_id}/action", response_model=FeedbackResponse, tags=["Criterion 1 - Feedback"])
async def update_feedback_action(
    feedback_id: str,
    request: FeedbackActionRequest,
    db: Session = Depends(get_db)
):
    """
    Update action taken on feedback.
    """
    try:
        feedback = db.query(CurriculumFeedback).filter(CurriculumFeedback.id == feedback_id).first()
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")

        feedback.action_taken = request.action_taken
        feedback.action_evidence = request.action_evidence
        feedback.action_date = datetime.utcnow()
        feedback.status = FeedbackStatusEnum.ACTION_TAKEN

        db.commit()
        db.refresh(feedback)

        return FeedbackResponse(
            id=str(feedback.id),
            feedback_type=feedback.feedback_type.value,
            respondent_name=feedback.respondent_name,
            respondent_email=feedback.respondent_email,
            respondent_organization=feedback.respondent_organization,
            respondent_designation=feedback.respondent_designation,
            department=feedback.department,
            program=feedback.program,
            course_code=feedback.course_code,
            course_name=feedback.course_name,
            academic_year=feedback.academic_year,
            semester=feedback.semester,
            feedback_content=feedback.feedback_content,
            rating=feedback.rating,
            suggestions=feedback.suggestions,
            structured_responses=feedback.structured_responses,
            status=feedback.status.value,
            reviewed_by=feedback.reviewed_by,
            reviewed_at=feedback.reviewed_at,
            action_taken=feedback.action_taken,
            action_date=feedback.action_date,
            action_evidence=feedback.action_evidence,
            submitted_at=feedback.submitted_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating feedback action: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion1/feedback/generate-report", tags=["Criterion 1 - Feedback"])
async def generate_feedback_report(request: FeedbackReportRequest, db: Session = Depends(get_db)):
    """
    Generate action-taken report for feedback.
    """
    try:
        query = db.query(CurriculumFeedback).filter(
            CurriculumFeedback.academic_year == request.academic_year
        )

        if request.department:
            query = query.filter(CurriculumFeedback.department == request.department)
        if request.feedback_types:
            query = query.filter(CurriculumFeedback.feedback_type.in_([FeedbackTypeEnum(ft.value) for ft in request.feedback_types]))
        if not request.include_pending:
            query = query.filter(CurriculumFeedback.status != FeedbackStatusEnum.PENDING)

        feedback_items = query.all()

        # Generate report data
        report = {
            "academic_year": request.academic_year,
            "department": request.department,
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_feedback": len(feedback_items),
                "action_taken": sum(1 for f in feedback_items if f.status == FeedbackStatusEnum.ACTION_TAKEN),
                "pending": sum(1 for f in feedback_items if f.status == FeedbackStatusEnum.PENDING),
                "by_type": {}
            },
            "feedback_items": []
        }

        # Group by type
        for f in feedback_items:
            ft = f.feedback_type.value
            if ft not in report["summary"]["by_type"]:
                report["summary"]["by_type"][ft] = {"total": 0, "action_taken": 0}
            report["summary"]["by_type"][ft]["total"] += 1
            if f.status == FeedbackStatusEnum.ACTION_TAKEN:
                report["summary"]["by_type"][ft]["action_taken"] += 1

            report["feedback_items"].append({
                "id": str(f.id),
                "type": f.feedback_type.value,
                "department": f.department,
                "feedback_summary": f.feedback_content[:200] + "..." if len(f.feedback_content) > 200 else f.feedback_content,
                "status": f.status.value,
                "action_taken": f.action_taken,
                "action_date": f.action_date.isoformat() if f.action_date else None
            })

        return {
            "success": True,
            "report": report
        }
    except Exception as e:
        logger.error(f"Error generating feedback report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EVIDENCE MANAGEMENT ====================

@router.post("/criterion1/evidence/upload", response_model=EvidenceResponse, tags=["Criterion 1 - Evidence"])
async def upload_evidence(
    evidence_type: str = Form(...),
    key_indicator: str = Form(...),
    title: str = Form(...),
    academic_year: str = Form(...),
    uploaded_by: str = Form(...),
    description: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    program: Optional[str] = Form(None),
    course_code: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload evidence document for Criterion 1.
    """
    try:
        # Save file
        upload_dir = "uploads/criterion1/evidence"
        os.makedirs(upload_dir, exist_ok=True)

        file_ext = os.path.splitext(file.filename)[1]
        file_id = str(uuid.uuid4())
        file_path = f"{upload_dir}/{file_id}{file_ext}"

        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        evidence = CurriculumEvidence(
            evidence_type=EvidenceTypeEnum(evidence_type),
            key_indicator=key_indicator,
            title=title,
            description=description,
            file_path=file_path,
            file_name=file.filename,
            file_size=len(content),
            file_type=file_ext[1:] if file_ext else None,
            department=department,
            program=program,
            course_code=course_code,
            academic_year=academic_year,
            uploaded_by=uploaded_by,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        return EvidenceResponse(
            id=str(evidence.id),
            evidence_type=evidence.evidence_type.value,
            key_indicator=evidence.key_indicator,
            title=evidence.title,
            description=evidence.description,
            file_path=evidence.file_path,
            file_name=evidence.file_name,
            file_size=evidence.file_size,
            file_type=evidence.file_type,
            department=evidence.department,
            program=evidence.program,
            course_code=evidence.course_code,
            academic_year=evidence.academic_year,
            is_verified=evidence.is_verified,
            verified_by=evidence.verified_by,
            verified_at=evidence.verified_at,
            verification_remarks=evidence.verification_remarks,
            uploaded_by=evidence.uploaded_by,
            metadata=evidence.metadata,
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
        )
    except Exception as e:
        logger.error(f"Error uploading evidence: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion1/evidence", response_model=EvidenceListResponse, tags=["Criterion 1 - Evidence"])
async def list_evidence(
    key_indicator: Optional[str] = None,
    evidence_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_verified: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List evidence documents with filters.
    """
    try:
        query = db.query(CurriculumEvidence)

        if key_indicator:
            query = query.filter(CurriculumEvidence.key_indicator == key_indicator)
        if evidence_type:
            query = query.filter(CurriculumEvidence.evidence_type == EvidenceTypeEnum(evidence_type))
        if academic_year:
            query = query.filter(CurriculumEvidence.academic_year == academic_year)
        if is_verified is not None:
            query = query.filter(CurriculumEvidence.is_verified == is_verified)

        total = query.count()
        items = query.order_by(CurriculumEvidence.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Count by key indicator
        by_indicator = {}
        for e in db.query(CurriculumEvidence).all():
            ki = e.key_indicator
            by_indicator[ki] = by_indicator.get(ki, 0) + 1

        return EvidenceListResponse(
            items=[EvidenceResponse(
                id=str(e.id),
                evidence_type=e.evidence_type.value,
                key_indicator=e.key_indicator,
                title=e.title,
                description=e.description,
                file_path=e.file_path,
                file_name=e.file_name,
                file_size=e.file_size,
                file_type=e.file_type,
                department=e.department,
                program=e.program,
                course_code=e.course_code,
                academic_year=e.academic_year,
                is_verified=e.is_verified,
                verified_by=e.verified_by,
                verified_at=e.verified_at,
                verification_remarks=e.verification_remarks,
                uploaded_by=e.uploaded_by,
                metadata=e.metadata,
                created_at=e.created_at,
                updated_at=e.updated_at,
            ) for e in items],
            total=total,
            page=page,
            page_size=page_size,
            by_key_indicator=by_indicator
        )
    except Exception as e:
        logger.error(f"Error listing evidence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion1/evidence/{evidence_id}", tags=["Criterion 1 - Evidence"])
async def delete_evidence(evidence_id: str, db: Session = Depends(get_db)):
    """
    Delete evidence document.
    """
    try:
        evidence = db.query(CurriculumEvidence).filter(CurriculumEvidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")

        # Delete file
        if os.path.exists(evidence.file_path):
            os.remove(evidence.file_path)

        db.delete(evidence)
        db.commit()

        return {"success": True, "message": "Evidence deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting evidence: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion1/evidence/{evidence_id}/verify", response_model=EvidenceResponse, tags=["Criterion 1 - Evidence"])
async def verify_evidence(
    evidence_id: str,
    request: EvidenceVerifyRequest,
    db: Session = Depends(get_db)
):
    """
    Mark evidence as verified.
    """
    try:
        evidence = db.query(CurriculumEvidence).filter(CurriculumEvidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence not found")

        evidence.is_verified = True
        evidence.verified_by = request.verified_by
        evidence.verified_at = datetime.utcnow()
        evidence.verification_remarks = request.verification_remarks

        db.commit()
        db.refresh(evidence)

        return EvidenceResponse(
            id=str(evidence.id),
            evidence_type=evidence.evidence_type.value,
            key_indicator=evidence.key_indicator,
            title=evidence.title,
            description=evidence.description,
            file_path=evidence.file_path,
            file_name=evidence.file_name,
            file_size=evidence.file_size,
            file_type=evidence.file_type,
            department=evidence.department,
            program=evidence.program,
            course_code=evidence.course_code,
            academic_year=evidence.academic_year,
            is_verified=evidence.is_verified,
            verified_by=evidence.verified_by,
            verified_at=evidence.verified_at,
            verification_remarks=evidence.verification_remarks,
            uploaded_by=evidence.uploaded_by,
            metadata=evidence.metadata,
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying evidence: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INDUSTRY PARTNERS ====================

@router.post("/criterion1/industry-partners", response_model=PartnerResponse, tags=["Criterion 1 - Industry Partners"])
async def create_industry_partner(request: PartnerCreate, db: Session = Depends(get_db)):
    """
    Add industry partner for MoU and collaboration.
    """
    try:
        partner = IndustryPartner(
            name=request.name,
            partner_type=PartnerTypeEnum(request.partner_type.value),
            industry_sector=request.industry_sector,
            website=request.website,
            contact_person=request.contact_person,
            contact_email=request.contact_email,
            contact_phone=request.contact_phone,
            address=request.address,
            department=request.department,
            collaboration_areas=request.collaboration_areas,
        )
        db.add(partner)
        db.commit()
        db.refresh(partner)

        return PartnerResponse(
            id=str(partner.id),
            name=partner.name,
            partner_type=partner.partner_type.value,
            industry_sector=partner.industry_sector,
            website=partner.website,
            contact_person=partner.contact_person,
            contact_email=partner.contact_email,
            contact_phone=partner.contact_phone,
            address=partner.address,
            mou_number=partner.mou_number,
            mou_status=partner.mou_status.value,
            mou_signed_date=partner.mou_signed_date,
            mou_expiry_date=partner.mou_expiry_date,
            mou_document_path=partner.mou_document_path,
            department=partner.department,
            collaboration_areas=partner.collaboration_areas,
            activities_conducted=partner.activities_conducted,
            students_benefited=partner.students_benefited,
            projects_completed=partner.projects_completed,
            placements_provided=partner.placements_provided,
            created_at=partner.created_at,
            updated_at=partner.updated_at,
        )
    except Exception as e:
        logger.error(f"Error creating industry partner: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion1/industry-partners", response_model=PartnerListResponse, tags=["Criterion 1 - Industry Partners"])
async def list_industry_partners(
    partner_type: Optional[str] = None,
    mou_status: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List industry partners with filters.
    """
    try:
        query = db.query(IndustryPartner)

        if partner_type:
            query = query.filter(IndustryPartner.partner_type == PartnerTypeEnum(partner_type))
        if mou_status:
            query = query.filter(IndustryPartner.mou_status == MoUStatusEnum(mou_status))
        if department:
            query = query.filter(IndustryPartner.department == department)

        total = query.count()
        items = query.order_by(IndustryPartner.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Count by type
        by_type = {}
        for p in db.query(IndustryPartner).all():
            pt = p.partner_type.value
            by_type[pt] = by_type.get(pt, 0) + 1

        return PartnerListResponse(
            items=[PartnerResponse(
                id=str(p.id),
                name=p.name,
                partner_type=p.partner_type.value,
                industry_sector=p.industry_sector,
                website=p.website,
                contact_person=p.contact_person,
                contact_email=p.contact_email,
                contact_phone=p.contact_phone,
                address=p.address,
                mou_number=p.mou_number,
                mou_status=p.mou_status.value,
                mou_signed_date=p.mou_signed_date,
                mou_expiry_date=p.mou_expiry_date,
                mou_document_path=p.mou_document_path,
                department=p.department,
                collaboration_areas=p.collaboration_areas,
                activities_conducted=p.activities_conducted,
                students_benefited=p.students_benefited,
                projects_completed=p.projects_completed,
                placements_provided=p.placements_provided,
                created_at=p.created_at,
                updated_at=p.updated_at,
            ) for p in items],
            total=total,
            page=page,
            page_size=page_size,
            by_type=by_type
        )
    except Exception as e:
        logger.error(f"Error listing industry partners: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion1/industry-partners/{partner_id}", response_model=PartnerResponse, tags=["Criterion 1 - Industry Partners"])
async def update_industry_partner(
    partner_id: str,
    request: PartnerUpdate,
    db: Session = Depends(get_db)
):
    """
    Update industry partner details.
    """
    try:
        partner = db.query(IndustryPartner).filter(IndustryPartner.id == partner_id).first()
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        for field, value in request.model_dump(exclude_unset=True).items():
            if field == "partner_type" and value:
                setattr(partner, field, PartnerTypeEnum(value.value))
            elif field == "mou_status" and value:
                setattr(partner, field, MoUStatusEnum(value.value))
            elif value is not None:
                setattr(partner, field, value)

        db.commit()
        db.refresh(partner)

        return PartnerResponse(
            id=str(partner.id),
            name=partner.name,
            partner_type=partner.partner_type.value,
            industry_sector=partner.industry_sector,
            website=partner.website,
            contact_person=partner.contact_person,
            contact_email=partner.contact_email,
            contact_phone=partner.contact_phone,
            address=partner.address,
            mou_number=partner.mou_number,
            mou_status=partner.mou_status.value,
            mou_signed_date=partner.mou_signed_date,
            mou_expiry_date=partner.mou_expiry_date,
            mou_document_path=partner.mou_document_path,
            department=partner.department,
            collaboration_areas=partner.collaboration_areas,
            activities_conducted=partner.activities_conducted,
            students_benefited=partner.students_benefited,
            projects_completed=partner.projects_completed,
            placements_provided=partner.placements_provided,
            created_at=partner.created_at,
            updated_at=partner.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating industry partner: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion1/industry-partners/{partner_id}/meetings", response_model=MeetingResponse, tags=["Criterion 1 - Industry Partners"])
async def add_partner_meeting(
    partner_id: str,
    request: MeetingCreate,
    db: Session = Depends(get_db)
):
    """
    Add advisory board meeting for partner.
    """
    try:
        partner = db.query(IndustryPartner).filter(IndustryPartner.id == partner_id).first()
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        meeting = AdvisoryBoardMeeting(
            title=request.title,
            meeting_type=request.meeting_type,
            meeting_date=request.meeting_date,
            venue=request.venue,
            department=request.department,
            academic_year=request.academic_year,
            partner_id=partner_id,
            attendees=request.attendees,
            external_experts=request.external_experts,
            agenda=request.agenda,
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        return MeetingResponse(
            id=str(meeting.id),
            title=meeting.title,
            meeting_type=meeting.meeting_type,
            meeting_date=meeting.meeting_date,
            venue=meeting.venue,
            department=meeting.department,
            academic_year=meeting.academic_year,
            partner_id=str(meeting.partner_id) if meeting.partner_id else None,
            attendees=meeting.attendees,
            external_experts=meeting.external_experts,
            agenda=meeting.agenda,
            minutes=meeting.minutes,
            resolutions=meeting.resolutions,
            minutes_document_path=meeting.minutes_document_path,
            attendance_sheet_path=meeting.attendance_sheet_path,
            action_items=meeting.action_items,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding partner meeting: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== VALUE-ADDED COURSES (Key Indicator 1.3) ====================

@router.post("/criterion1/value-added-courses", response_model=ValueAddedCourseResponse, tags=["Criterion 1 - Value-Added Courses"])
async def create_value_added_course(request: ValueAddedCourseCreate, db: Session = Depends(get_db)):
    """
    Create value-added course for skill development.
    """
    try:
        course = ValueAddedCourse(
            course_name=request.course_name,
            course_code=request.course_code,
            course_type=CourseTypeEnum(request.course_type.value),
            course_mode=CourseModeEnum(request.course_mode.value),
            department=request.department,
            academic_year=request.academic_year,
            semester=request.semester,
            description=request.description,
            objectives=request.objectives,
            outcomes=request.outcomes,
            duration_hours=request.duration_hours,
            credits=request.credits,
            co_po_mapping=request.co_po_mapping,
            instructor_name=request.instructor_name,
            instructor_qualification=request.instructor_qualification,
            instructor_organization=request.instructor_organization,
            start_date=request.start_date,
            end_date=request.end_date,
            schedule=request.schedule,
            max_enrollment=request.max_enrollment,
            certification_provided=request.certification_provided,
            certifying_body=request.certifying_body,
        )
        db.add(course)
        db.commit()
        db.refresh(course)

        return ValueAddedCourseResponse(
            id=str(course.id),
            course_name=course.course_name,
            course_code=course.course_code,
            course_type=course.course_type.value,
            course_mode=course.course_mode.value,
            department=course.department,
            academic_year=course.academic_year,
            semester=course.semester,
            description=course.description,
            objectives=course.objectives,
            outcomes=course.outcomes,
            duration_hours=course.duration_hours,
            credits=course.credits,
            co_po_mapping=course.co_po_mapping,
            instructor_name=course.instructor_name,
            instructor_qualification=course.instructor_qualification,
            instructor_organization=course.instructor_organization,
            start_date=course.start_date,
            end_date=course.end_date,
            schedule=course.schedule,
            max_enrollment=course.max_enrollment,
            current_enrollment=course.current_enrollment,
            completed_count=course.completed_count,
            certification_provided=course.certification_provided,
            certifying_body=course.certifying_body,
            syllabus_path=course.syllabus_path,
            materials_path=course.materials_path,
            is_active=course.is_active,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
    except Exception as e:
        logger.error(f"Error creating value-added course: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion1/value-added-courses", response_model=ValueAddedCourseListResponse, tags=["Criterion 1 - Value-Added Courses"])
async def list_value_added_courses(
    course_type: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List value-added courses with filters.
    """
    try:
        query = db.query(ValueAddedCourse)

        if course_type:
            query = query.filter(ValueAddedCourse.course_type == CourseTypeEnum(course_type))
        if department:
            query = query.filter(ValueAddedCourse.department == department)
        if academic_year:
            query = query.filter(ValueAddedCourse.academic_year == academic_year)
        if is_active is not None:
            query = query.filter(ValueAddedCourse.is_active == is_active)

        total = query.count()
        items = query.order_by(ValueAddedCourse.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Count by type
        by_type = {}
        for c in db.query(ValueAddedCourse).all():
            ct = c.course_type.value
            by_type[ct] = by_type.get(ct, 0) + 1

        return ValueAddedCourseListResponse(
            items=[ValueAddedCourseResponse(
                id=str(c.id),
                course_name=c.course_name,
                course_code=c.course_code,
                course_type=c.course_type.value,
                course_mode=c.course_mode.value,
                department=c.department,
                academic_year=c.academic_year,
                semester=c.semester,
                description=c.description,
                objectives=c.objectives,
                outcomes=c.outcomes,
                duration_hours=c.duration_hours,
                credits=c.credits,
                co_po_mapping=c.co_po_mapping,
                instructor_name=c.instructor_name,
                instructor_qualification=c.instructor_qualification,
                instructor_organization=c.instructor_organization,
                start_date=c.start_date,
                end_date=c.end_date,
                schedule=c.schedule,
                max_enrollment=c.max_enrollment,
                current_enrollment=c.current_enrollment,
                completed_count=c.completed_count,
                certification_provided=c.certification_provided,
                certifying_body=c.certifying_body,
                syllabus_path=c.syllabus_path,
                materials_path=c.materials_path,
                is_active=c.is_active,
                created_at=c.created_at,
                updated_at=c.updated_at,
            ) for c in items],
            total=total,
            page=page,
            page_size=page_size,
            by_type=by_type
        )
    except Exception as e:
        logger.error(f"Error listing value-added courses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion1/value-added-courses/{course_id}", response_model=ValueAddedCourseResponse, tags=["Criterion 1 - Value-Added Courses"])
async def update_value_added_course(
    course_id: str,
    request: ValueAddedCourseUpdate,
    db: Session = Depends(get_db)
):
    """
    Update value-added course.
    """
    try:
        course = db.query(ValueAddedCourse).filter(ValueAddedCourse.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        for field, value in request.model_dump(exclude_unset=True).items():
            if field == "course_type" and value:
                setattr(course, field, CourseTypeEnum(value.value))
            elif field == "course_mode" and value:
                setattr(course, field, CourseModeEnum(value.value))
            elif value is not None:
                setattr(course, field, value)

        db.commit()
        db.refresh(course)

        return ValueAddedCourseResponse(
            id=str(course.id),
            course_name=course.course_name,
            course_code=course.course_code,
            course_type=course.course_type.value,
            course_mode=course.course_mode.value,
            department=course.department,
            academic_year=course.academic_year,
            semester=course.semester,
            description=course.description,
            objectives=course.objectives,
            outcomes=course.outcomes,
            duration_hours=course.duration_hours,
            credits=course.credits,
            co_po_mapping=course.co_po_mapping,
            instructor_name=course.instructor_name,
            instructor_qualification=course.instructor_qualification,
            instructor_organization=course.instructor_organization,
            start_date=course.start_date,
            end_date=course.end_date,
            schedule=course.schedule,
            max_enrollment=course.max_enrollment,
            current_enrollment=course.current_enrollment,
            completed_count=course.completed_count,
            certification_provided=course.certification_provided,
            certifying_body=course.certifying_body,
            syllabus_path=course.syllabus_path,
            materials_path=course.materials_path,
            is_active=course.is_active,
            created_at=course.created_at,
            updated_at=course.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating value-added course: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion1/value-added-courses/{course_id}/enrollments", response_model=CourseEnrollmentResponse, tags=["Criterion 1 - Value-Added Courses"])
async def record_enrollment(
    course_id: str,
    request: CourseEnrollmentCreate,
    db: Session = Depends(get_db)
):
    """
    Record student enrollment in value-added course.
    """
    try:
        course = db.query(ValueAddedCourse).filter(ValueAddedCourse.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        enrollment = ValueAddedCourseEnrollment(
            course_id=course_id,
            student_id=request.student_id,
            student_name=request.student_name,
            student_email=request.student_email,
            department=request.department,
            batch=request.batch,
            enrollment_date=request.enrollment_date,
        )
        db.add(enrollment)

        # Update course enrollment count
        course.current_enrollment += 1

        db.commit()
        db.refresh(enrollment)

        return CourseEnrollmentResponse(
            id=str(enrollment.id),
            course_id=str(enrollment.course_id),
            student_id=enrollment.student_id,
            student_name=enrollment.student_name,
            student_email=enrollment.student_email,
            department=enrollment.department,
            batch=enrollment.batch,
            enrollment_date=enrollment.enrollment_date,
            status=enrollment.status,
            completion_date=enrollment.completion_date,
            grade=enrollment.grade,
            score=enrollment.score,
            certificate_issued=enrollment.certificate_issued,
            certificate_path=enrollment.certificate_path,
            created_at=enrollment.created_at,
            updated_at=enrollment.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error recording enrollment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== INTERNSHIPS (Key Indicator 1.3) ====================

@router.post("/criterion1/internships", response_model=InternshipResponse, tags=["Criterion 1 - Internships"])
async def record_internship(request: InternshipCreate, db: Session = Depends(get_db)):
    """
    Record student internship.
    """
    try:
        internship = InternshipRecord(
            student_id=request.student_id,
            student_name=request.student_name,
            student_email=request.student_email,
            department=request.department,
            batch=request.batch,
            semester=request.semester,
            academic_year=request.academic_year,
            internship_type=InternshipTypeEnum(request.internship_type.value),
            company_name=request.company_name,
            company_website=request.company_website,
            industry_sector=request.industry_sector,
            location=request.location,
            is_remote=request.is_remote,
            start_date=request.start_date,
            end_date=request.end_date,
            duration_weeks=request.duration_weeks,
            role_title=request.role_title,
            project_title=request.project_title,
            project_description=request.project_description,
            skills_used=request.skills_used,
            company_mentor=request.company_mentor,
            faculty_mentor=request.faculty_mentor,
            is_paid=request.is_paid,
            stipend_amount=request.stipend_amount,
            stipend_currency=request.stipend_currency,
        )
        db.add(internship)
        db.commit()
        db.refresh(internship)

        return InternshipResponse(
            id=str(internship.id),
            student_id=internship.student_id,
            student_name=internship.student_name,
            student_email=internship.student_email,
            department=internship.department,
            batch=internship.batch,
            semester=internship.semester,
            academic_year=internship.academic_year,
            internship_type=internship.internship_type.value,
            company_name=internship.company_name,
            company_website=internship.company_website,
            industry_sector=internship.industry_sector,
            location=internship.location,
            is_remote=internship.is_remote,
            start_date=internship.start_date,
            end_date=internship.end_date,
            duration_weeks=internship.duration_weeks,
            role_title=internship.role_title,
            project_title=internship.project_title,
            project_description=internship.project_description,
            skills_used=internship.skills_used,
            company_mentor=internship.company_mentor,
            faculty_mentor=internship.faculty_mentor,
            is_paid=internship.is_paid,
            stipend_amount=internship.stipend_amount,
            stipend_currency=internship.stipend_currency,
            status=internship.status.value,
            ppo_offered=internship.ppo_offered,
            converted_to_job=internship.converted_to_job,
            performance_rating=internship.performance_rating,
            feedback=internship.feedback,
            offer_letter_path=internship.offer_letter_path,
            completion_certificate_path=internship.completion_certificate_path,
            report_path=internship.report_path,
            created_at=internship.created_at,
            updated_at=internship.updated_at,
        )
    except Exception as e:
        logger.error(f"Error recording internship: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion1/internships", response_model=InternshipListResponse, tags=["Criterion 1 - Internships"])
async def list_internships(
    internship_type: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    List internships with filters.
    """
    try:
        query = db.query(InternshipRecord)

        if internship_type:
            query = query.filter(InternshipRecord.internship_type == InternshipTypeEnum(internship_type))
        if status:
            query = query.filter(InternshipRecord.status == InternshipStatusEnum(status))
        if department:
            query = query.filter(InternshipRecord.department == department)
        if academic_year:
            query = query.filter(InternshipRecord.academic_year == academic_year)

        total = query.count()
        items = query.order_by(InternshipRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Count by type and status
        by_type = {}
        by_status = {}
        for i in db.query(InternshipRecord).all():
            it = i.internship_type.value
            ist = i.status.value
            by_type[it] = by_type.get(it, 0) + 1
            by_status[ist] = by_status.get(ist, 0) + 1

        return InternshipListResponse(
            items=[InternshipResponse(
                id=str(i.id),
                student_id=i.student_id,
                student_name=i.student_name,
                student_email=i.student_email,
                department=i.department,
                batch=i.batch,
                semester=i.semester,
                academic_year=i.academic_year,
                internship_type=i.internship_type.value,
                company_name=i.company_name,
                company_website=i.company_website,
                industry_sector=i.industry_sector,
                location=i.location,
                is_remote=i.is_remote,
                start_date=i.start_date,
                end_date=i.end_date,
                duration_weeks=i.duration_weeks,
                role_title=i.role_title,
                project_title=i.project_title,
                project_description=i.project_description,
                skills_used=i.skills_used,
                company_mentor=i.company_mentor,
                faculty_mentor=i.faculty_mentor,
                is_paid=i.is_paid,
                stipend_amount=i.stipend_amount,
                stipend_currency=i.stipend_currency,
                status=i.status.value,
                ppo_offered=i.ppo_offered,
                converted_to_job=i.converted_to_job,
                performance_rating=i.performance_rating,
                feedback=i.feedback,
                offer_letter_path=i.offer_letter_path,
                completion_certificate_path=i.completion_certificate_path,
                report_path=i.report_path,
                created_at=i.created_at,
                updated_at=i.updated_at,
            ) for i in items],
            total=total,
            page=page,
            page_size=page_size,
            by_type=by_type,
            by_status=by_status
        )
    except Exception as e:
        logger.error(f"Error listing internships: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion1/internships/analytics", response_model=InternshipAnalytics, tags=["Criterion 1 - Internships"])
async def get_internship_analytics(
    academic_year: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get internship analytics.
    """
    try:
        query = db.query(InternshipRecord)
        if academic_year:
            query = query.filter(InternshipRecord.academic_year == academic_year)

        internships = query.all()

        # Calculate analytics
        total = len(internships)
        ongoing = sum(1 for i in internships if i.status == InternshipStatusEnum.ONGOING)
        completed = sum(1 for i in internships if i.status == InternshipStatusEnum.COMPLETED)
        paid = sum(1 for i in internships if i.is_paid)
        ppo = sum(1 for i in internships if i.ppo_offered)
        converted = sum(1 for i in internships if i.converted_to_job)

        # By type
        by_type = {}
        for i in internships:
            it = i.internship_type.value
            by_type[it] = by_type.get(it, 0) + 1

        # By department
        by_department = {}
        for i in internships:
            dept = i.department
            by_department[dept] = by_department.get(dept, 0) + 1

        # By industry sector
        by_sector = {}
        for i in internships:
            if i.industry_sector:
                by_sector[i.industry_sector] = by_sector.get(i.industry_sector, 0) + 1

        # Average duration
        durations = [i.duration_weeks for i in internships if i.duration_weeks]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Average stipend
        stipends = [i.stipend_amount for i in internships if i.is_paid and i.stipend_amount]
        avg_stipend = sum(stipends) / len(stipends) if stipends else None

        # Top companies
        company_counts = {}
        for i in internships:
            company_counts[i.company_name] = company_counts.get(i.company_name, 0) + 1
        top_companies = sorted([{"company": k, "count": v} for k, v in company_counts.items()], key=lambda x: x["count"], reverse=True)[:10]

        return InternshipAnalytics(
            total_internships=total,
            ongoing=ongoing,
            completed=completed,
            by_type=by_type,
            by_department=by_department,
            by_industry_sector=by_sector,
            paid_internships=paid,
            ppo_offered=ppo,
            converted_to_jobs=converted,
            average_duration_weeks=round(avg_duration, 1),
            average_stipend=round(avg_stipend, 2) if avg_stipend else None,
            top_companies=top_companies
        )
    except Exception as e:
        logger.error(f"Error getting internship analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DASHBOARD & REPORTS ====================

@router.get("/criterion1/dashboard", response_model=Criterion1DashboardStats, tags=["Criterion 1 - Dashboard"])
async def get_criterion1_dashboard(
    academic_year: Optional[str] = None,
):
    """
    Get Criterion 1 dashboard statistics.
    """
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion1DashboardStats(
        curriculum_revisions=0,
        board_meetings=0,
        industry_expert_inputs=0,
        elective_courses=0,
        interdisciplinary_programs=0,
        value_added_courses=0,
        total_enrollments=0,
        certifications_issued=0,
        internships_total=0,
        internships_ongoing=0,
        total_feedback=0,
        feedback_by_type={},
        action_taken_percentage=0,
        total_evidence=0,
        verified_evidence=0,
        evidence_by_indicator={},
        active_mous=0,
        total_partners=0,
        students_benefited=0,
        completion_percentage=0,
        pending_items=[]
    )


@router.post("/criterion1/generate-report", response_model=Criterion1ReportResponse, tags=["Criterion 1 - Reports"])
async def generate_criterion1_report(
    request: Criterion1ReportRequest,
    db: Session = Depends(get_db)
):
    """
    Generate complete Criterion 1 report for NAAC submission.
    """
    try:
        from app.utils.document_generator import document_generator

        # Get all data for the academic year
        feedback = db.query(CurriculumFeedback).filter(CurriculumFeedback.academic_year == request.academic_year).all()
        evidence = db.query(CurriculumEvidence).filter(CurriculumEvidence.academic_year == request.academic_year).all()
        partners = db.query(IndustryPartner).all()
        meetings = db.query(AdvisoryBoardMeeting).filter(AdvisoryBoardMeeting.academic_year == request.academic_year).all()
        courses = db.query(ValueAddedCourse).filter(ValueAddedCourse.academic_year == request.academic_year).all()
        internships = db.query(InternshipRecord).filter(InternshipRecord.academic_year == request.academic_year).all()

        # Prepare report content
        sections = request.include_sections or ["1.1", "1.2", "1.3", "1.4"]

        report_content = {
            "title": f"NAAC Criterion 1: Curricular Aspects - {request.institution_name}",
            "academic_year": request.academic_year,
            "generated_at": datetime.utcnow().isoformat(),
            "sections": {}
        }

        if "1.1" in sections:
            report_content["sections"]["1.1"] = {
                "title": "Curriculum Planning and Implementation",
                "curriculum_revisions": sum(1 for e in evidence if e.evidence_type == EvidenceTypeEnum.CURRICULUM_REVISION),
                "board_meetings": len(meetings),
                "industry_inputs": sum(len(m.external_experts or []) for m in meetings),
            }

        if "1.2" in sections:
            report_content["sections"]["1.2"] = {
                "title": "Academic Flexibility",
                "note": "To be populated with elective course data"
            }

        if "1.3" in sections:
            report_content["sections"]["1.3"] = {
                "title": "Curriculum Enrichment",
                "value_added_courses": len(courses),
                "course_details": [{"name": c.course_name, "type": c.course_type.value, "enrollments": c.current_enrollment} for c in courses[:10]],
                "internships": len(internships),
                "internship_summary": {
                    "total": len(internships),
                    "ongoing": sum(1 for i in internships if i.status == InternshipStatusEnum.ONGOING),
                    "completed": sum(1 for i in internships if i.status == InternshipStatusEnum.COMPLETED),
                    "paid": sum(1 for i in internships if i.is_paid),
                }
            }

        if "1.4" in sections:
            feedback_summary = {}
            for f in feedback:
                ft = f.feedback_type.value
                if ft not in feedback_summary:
                    feedback_summary[ft] = {"total": 0, "action_taken": 0}
                feedback_summary[ft]["total"] += 1
                if f.status == FeedbackStatusEnum.ACTION_TAKEN:
                    feedback_summary[ft]["action_taken"] += 1

            report_content["sections"]["1.4"] = {
                "title": "Feedback System",
                "total_feedback": len(feedback),
                "feedback_by_type": feedback_summary,
                "action_taken_percentage": round(sum(1 for f in feedback if f.status == FeedbackStatusEnum.ACTION_TAKEN) / len(feedback) * 100, 1) if feedback else 0
            }

        if request.include_evidence_list:
            report_content["evidence_list"] = [
                {"title": e.title, "type": e.evidence_type.value, "key_indicator": e.key_indicator, "verified": e.is_verified}
                for e in evidence
            ]

        if request.include_analytics:
            report_content["analytics"] = {
                "partners": {
                    "total": len(partners),
                    "active_mous": sum(1 for p in partners if p.mou_status == MoUStatusEnum.ACTIVE),
                    "students_benefited": sum(p.students_benefited for p in partners)
                }
            }

        # Generate document
        if request.format == "docx":
            doc_bytes = document_generator.generate_accreditation_docx(
                content=report_content,
                title=f"Criterion 1 Report - {request.academic_year}"
            )
            file_ext = "docx"
        else:
            doc_bytes = document_generator.generate_accreditation_pdf(
                content=report_content,
                title=f"Criterion 1 Report - {request.academic_year}"
            )
            file_ext = "pdf"

        # Save report
        report_dir = "uploads/criterion1/reports"
        os.makedirs(report_dir, exist_ok=True)
        report_path = f"{report_dir}/criterion1_report_{request.academic_year.replace('-', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_ext}"

        with open(report_path, "wb") as f:
            f.write(doc_bytes)

        return Criterion1ReportResponse(
            success=True,
            report_path=report_path,
            sections_included=sections,
            generated_at=datetime.utcnow(),
            metadata={"file_size": len(doc_bytes), "format": request.format}
        )
    except Exception as e:
        logger.error(f"Error generating Criterion 1 report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRITERION 2: TEACHING-LEARNING AND EVALUATION ====================

# -------------------- LMS ADOPTION --------------------

@router.post("/criterion2/lms", response_model=LMSAdoptionResponse, tags=["Criterion 2 - LMS"])
async def create_lms_adoption(
    data: LMSAdoptionCreate,
    db: Session = Depends(get_db)
):
    """Create LMS adoption record for a department."""
    try:
        lms = LMSAdoption(
            platform=LMSPlatformEnum(data.platform.value),
            platform_name=data.platform_name,
            platform_url=data.platform_url,
            department=data.department,
            academic_year=data.academic_year,
            total_courses=data.total_courses,
            active_courses=data.active_courses,
            total_faculty_registered=data.total_faculty_registered,
            total_students_registered=data.total_students_registered,
        )
        db.add(lms)
        db.commit()
        db.refresh(lms)
        return LMSAdoptionResponse.model_validate(lms)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating LMS adoption: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/lms", response_model=LMSAdoptionListResponse, tags=["Criterion 2 - LMS"])
async def list_lms_adoptions(
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    platform: Optional[LMSPlatform] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List LMS adoption records with filters."""
    try:
        query = db.query(LMSAdoption)

        if department:
            query = query.filter(LMSAdoption.department == department)
        if academic_year:
            query = query.filter(LMSAdoption.academic_year == academic_year)
        if platform:
            query = query.filter(LMSAdoption.platform == LMSPlatformEnum(platform.value))

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        # Get platform distribution
        by_platform = {}
        for p in LMSPlatformEnum:
            count = db.query(LMSAdoption).filter(LMSAdoption.platform == p).count()
            if count > 0:
                by_platform[p.value] = count

        return LMSAdoptionListResponse(
            items=[LMSAdoptionResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            by_platform=by_platform
        )
    except Exception as e:
        logger.error(f"Error listing LMS adoptions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/lms/{lms_id}", response_model=LMSAdoptionResponse, tags=["Criterion 2 - LMS"])
async def update_lms_adoption(
    lms_id: str,
    data: LMSAdoptionUpdate,
    db: Session = Depends(get_db)
):
    """Update LMS adoption record."""
    try:
        lms = db.query(LMSAdoption).filter(LMSAdoption.id == lms_id).first()
        if not lms:
            raise HTTPException(status_code=404, detail="LMS adoption record not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(lms, key, value)

        db.commit()
        db.refresh(lms)
        return LMSAdoptionResponse.model_validate(lms)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating LMS adoption: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- LESSON PLANS --------------------

@router.post("/criterion2/lesson-plans", response_model=LessonPlanResponse, tags=["Criterion 2 - Lesson Plans"])
async def create_lesson_plan(
    data: LessonPlanCreate,
    db: Session = Depends(get_db)
):
    """Create lesson plan with Bloom's Taxonomy mapping."""
    try:
        lesson = LessonPlan(
            course_name=data.course_name,
            course_code=data.course_code,
            department=data.department,
            program=data.program,
            semester=data.semester,
            academic_year=data.academic_year,
            credits=data.credits,
            faculty_name=data.faculty_name,
            faculty_email=data.faculty_email,
            unit_number=data.unit_number,
            unit_name=data.unit_name,
            topic=data.topic,
            subtopics=data.subtopics,
            planned_hours=data.planned_hours,
            session_date=data.session_date,
            learning_objectives=data.learning_objectives,
            course_outcomes_mapped=data.course_outcomes_mapped,
            blooms_levels=[b.value for b in data.blooms_levels] if data.blooms_levels else None,
            teaching_methods=[m.value for m in data.teaching_methods] if data.teaching_methods else None,
            teaching_aids=data.teaching_aids,
            ict_tools_used=data.ict_tools_used,
            assessment_methods=[a.value for a in data.assessment_methods] if data.assessment_methods else None,
            assessment_blooms_level=BloomsLevelEnum(data.assessment_blooms_level.value) if data.assessment_blooms_level else None,
            reference_materials=data.reference_materials,
            additional_resources=data.additional_resources,
        )
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return LessonPlanResponse.model_validate(lesson)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating lesson plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/lesson-plans", response_model=LessonPlanListResponse, tags=["Criterion 2 - Lesson Plans"])
async def list_lesson_plans(
    department: Optional[str] = None,
    course_code: Optional[str] = None,
    academic_year: Optional[str] = None,
    faculty_name: Optional[str] = None,
    is_completed: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List lesson plans with filters."""
    try:
        query = db.query(LessonPlan)

        if department:
            query = query.filter(LessonPlan.department == department)
        if course_code:
            query = query.filter(LessonPlan.course_code == course_code)
        if academic_year:
            query = query.filter(LessonPlan.academic_year == academic_year)
        if faculty_name:
            query = query.filter(LessonPlan.faculty_name.ilike(f"%{faculty_name}%"))
        if is_completed is not None:
            query = query.filter(LessonPlan.is_completed == is_completed)

        total = query.count()
        items = query.order_by(LessonPlan.unit_number, LessonPlan.session_date).offset((page - 1) * page_size).limit(page_size).all()

        return LessonPlanListResponse(
            items=[LessonPlanResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing lesson plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/lesson-plans/{plan_id}", response_model=LessonPlanResponse, tags=["Criterion 2 - Lesson Plans"])
async def update_lesson_plan(
    plan_id: str,
    data: LessonPlanUpdate,
    db: Session = Depends(get_db)
):
    """Update lesson plan."""
    try:
        lesson = db.query(LessonPlan).filter(LessonPlan.id == plan_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson plan not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(lesson, key, value)

        db.commit()
        db.refresh(lesson)
        return LessonPlanResponse.model_validate(lesson)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating lesson plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- ATTENDANCE --------------------

@router.post("/criterion2/attendance", response_model=AttendanceResponse, tags=["Criterion 2 - Attendance"])
async def create_attendance_record(
    data: AttendanceCreate,
    db: Session = Depends(get_db)
):
    """Create attendance record."""
    try:
        attendance = AttendanceRecord(
            student_id=data.student_id,
            student_name=data.student_name,
            department=data.department,
            batch=data.batch,
            semester=data.semester,
            course_code=data.course_code,
            course_name=data.course_name,
            academic_year=data.academic_year,
            attendance_date=data.attendance_date,
            period=data.period,
            status=AttendanceStatusEnum(data.status.value),
            marked_by=data.marked_by,
            remarks=data.remarks,
            is_makeup_class=data.is_makeup_class,
        )
        db.add(attendance)
        db.commit()
        db.refresh(attendance)
        return AttendanceResponse.model_validate(attendance)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating attendance record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion2/attendance/bulk", tags=["Criterion 2 - Attendance"])
async def create_bulk_attendance(
    data: AttendanceBulkCreate,
    db: Session = Depends(get_db)
):
    """Bulk create attendance records for a class."""
    try:
        created = []
        for record in data.records:
            attendance = AttendanceRecord(
                student_id=record["student_id"],
                student_name=record["student_name"],
                department=data.department,
                course_code=data.course_code,
                course_name=data.course_name,
                academic_year=data.academic_year,
                attendance_date=data.attendance_date,
                period=data.period,
                status=AttendanceStatusEnum(record.get("status", "present")),
                marked_by=data.marked_by,
            )
            db.add(attendance)
            created.append(attendance)

        db.commit()
        return {"success": True, "records_created": len(created)}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bulk attendance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/attendance", response_model=AttendanceListResponse, tags=["Criterion 2 - Attendance"])
async def list_attendance_records(
    student_id: Optional[str] = None,
    course_code: Optional[str] = None,
    department: Optional[str] = None,
    attendance_date: Optional[date] = None,
    academic_year: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List attendance records with filters."""
    try:
        query = db.query(AttendanceRecord)

        if student_id:
            query = query.filter(AttendanceRecord.student_id == student_id)
        if course_code:
            query = query.filter(AttendanceRecord.course_code == course_code)
        if department:
            query = query.filter(AttendanceRecord.department == department)
        if attendance_date:
            query = query.filter(AttendanceRecord.attendance_date == attendance_date)
        if academic_year:
            query = query.filter(AttendanceRecord.academic_year == academic_year)

        total = query.count()
        items = query.order_by(AttendanceRecord.attendance_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return AttendanceListResponse(
            items=[AttendanceResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing attendance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/attendance/summary", response_model=List[AttendanceSummary], tags=["Criterion 2 - Attendance"])
async def get_attendance_summary(
    course_code: str,
    academic_year: str,
    db: Session = Depends(get_db)
):
    """Get attendance summary by student for a course."""
    try:
        from sqlalchemy import func

        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.course_code == course_code,
            AttendanceRecord.academic_year == academic_year
        ).all()

        # Group by student
        student_summary = {}
        for r in records:
            if r.student_id not in student_summary:
                student_summary[r.student_id] = {
                    "student_id": r.student_id,
                    "student_name": r.student_name,
                    "present": 0,
                    "absent": 0,
                    "late": 0,
                    "excused": 0,
                    "on_duty": 0,
                    "total_classes": 0
                }
            student_summary[r.student_id]["total_classes"] += 1
            status = r.status.value
            if status in student_summary[r.student_id]:
                student_summary[r.student_id][status] += 1

        # Calculate percentages
        summaries = []
        for sid, data in student_summary.items():
            total = data["total_classes"]
            present_equivalent = data["present"] + data["late"] * 0.5 + data["on_duty"]
            data["attendance_percentage"] = round(present_equivalent / total * 100, 2) if total > 0 else 0
            summaries.append(AttendanceSummary(**data))

        return summaries
    except Exception as e:
        logger.error(f"Error getting attendance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- CIE (CONTINUOUS INTERNAL EVALUATION) --------------------

@router.post("/criterion2/cie", response_model=CIEResponse, tags=["Criterion 2 - CIE"])
async def create_cie_record(
    data: CIECreate,
    db: Session = Depends(get_db)
):
    """Create CIE record."""
    try:
        cie = CIERecord(
            student_id=data.student_id,
            student_name=data.student_name,
            department=data.department,
            batch=data.batch,
            semester=data.semester,
            course_code=data.course_code,
            course_name=data.course_name,
            academic_year=data.academic_year,
            assessment_type=AssessmentTypeEnum(data.assessment_type.value),
            assessment_name=data.assessment_name,
            assessment_date=data.assessment_date,
            max_marks=data.max_marks,
            marks_obtained=data.marks_obtained,
            percentage=round(data.marks_obtained / data.max_marks * 100, 2) if data.marks_obtained else None,
            course_outcomes_assessed=data.course_outcomes_assessed,
            blooms_level=BloomsLevelEnum(data.blooms_level.value) if data.blooms_level else None,
            rubric_id=data.rubric_id,
        )
        db.add(cie)
        db.commit()
        db.refresh(cie)
        return CIEResponse.model_validate(cie)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating CIE record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion2/cie/bulk", tags=["Criterion 2 - CIE"])
async def create_bulk_cie(
    data: CIEBulkCreate,
    db: Session = Depends(get_db)
):
    """Bulk create CIE records for an assessment."""
    try:
        created = []
        for record in data.records:
            cie = CIERecord(
                student_id=record["student_id"],
                student_name=record["student_name"],
                department=data.department,
                course_code=data.course_code,
                course_name=data.course_name,
                academic_year=data.academic_year,
                assessment_type=AssessmentTypeEnum(data.assessment_type.value),
                assessment_name=data.assessment_name,
                assessment_date=data.assessment_date,
                max_marks=data.max_marks,
                marks_obtained=record.get("marks_obtained"),
                percentage=round(record.get("marks_obtained", 0) / data.max_marks * 100, 2) if record.get("marks_obtained") else None,
                course_outcomes_assessed=data.course_outcomes_assessed,
                blooms_level=BloomsLevelEnum(data.blooms_level.value) if data.blooms_level else None,
            )
            db.add(cie)
            created.append(cie)

        db.commit()
        return {"success": True, "records_created": len(created)}
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating bulk CIE: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/cie", response_model=CIEListResponse, tags=["Criterion 2 - CIE"])
async def list_cie_records(
    student_id: Optional[str] = None,
    course_code: Optional[str] = None,
    assessment_type: Optional[AssessmentType] = None,
    academic_year: Optional[str] = None,
    department: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List CIE records with filters."""
    try:
        query = db.query(CIERecord)

        if student_id:
            query = query.filter(CIERecord.student_id == student_id)
        if course_code:
            query = query.filter(CIERecord.course_code == course_code)
        if assessment_type:
            query = query.filter(CIERecord.assessment_type == AssessmentTypeEnum(assessment_type.value))
        if academic_year:
            query = query.filter(CIERecord.academic_year == academic_year)
        if department:
            query = query.filter(CIERecord.department == department)

        total = query.count()
        items = query.order_by(CIERecord.assessment_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Get distribution by type
        by_type = {}
        for t in AssessmentTypeEnum:
            count = db.query(CIERecord).filter(CIERecord.assessment_type == t).count()
            if count > 0:
                by_type[t.value] = count

        return CIEListResponse(
            items=[CIEResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            by_assessment_type=by_type
        )
    except Exception as e:
        logger.error(f"Error listing CIE records: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/cie/{cie_id}", response_model=CIEResponse, tags=["Criterion 2 - CIE"])
async def update_cie_record(
    cie_id: str,
    data: CIEUpdate,
    db: Session = Depends(get_db)
):
    """Update CIE record with marks and feedback."""
    try:
        cie = db.query(CIERecord).filter(CIERecord.id == cie_id).first()
        if not cie:
            raise HTTPException(status_code=404, detail="CIE record not found")

        update_data = data.model_dump(exclude_unset=True)

        if "marks_obtained" in update_data and update_data["marks_obtained"] is not None:
            update_data["percentage"] = round(update_data["marks_obtained"] / cie.max_marks * 100, 2)

        if "blooms_level" in update_data and update_data["blooms_level"]:
            update_data["blooms_level"] = BloomsLevelEnum(update_data["blooms_level"].value)

        if "evaluated_by" in update_data:
            update_data["evaluated_at"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(cie, key, value)

        db.commit()
        db.refresh(cie)
        return CIEResponse.model_validate(cie)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating CIE record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- EVALUATION RUBRICS --------------------

@router.post("/criterion2/rubrics", response_model=RubricResponse, tags=["Criterion 2 - Rubrics"])
async def create_rubric(
    data: RubricCreate,
    db: Session = Depends(get_db)
):
    """Create evaluation rubric."""
    try:
        rubric = EvaluationRubricModel(
            name=data.name,
            description=data.description,
            course_code=data.course_code,
            course_name=data.course_name,
            department=data.department,
            academic_year=data.academic_year,
            assessment_type=AssessmentTypeEnum(data.assessment_type.value) if data.assessment_type else None,
            total_points=data.total_points,
            criteria=[c.model_dump() for c in data.criteria],
            performance_levels=data.performance_levels,
            course_outcomes_mapped=data.course_outcomes_mapped,
            blooms_levels_covered=[b.value for b in data.blooms_levels_covered] if data.blooms_levels_covered else None,
            is_template=data.is_template,
        )
        db.add(rubric)
        db.commit()
        db.refresh(rubric)
        return RubricResponse.model_validate(rubric)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating rubric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/rubrics", response_model=RubricListResponse, tags=["Criterion 2 - Rubrics"])
async def list_rubrics(
    course_code: Optional[str] = None,
    assessment_type: Optional[AssessmentType] = None,
    department: Optional[str] = None,
    is_template: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List evaluation rubrics."""
    try:
        query = db.query(EvaluationRubricModel).filter(EvaluationRubricModel.is_active == True)

        if course_code:
            query = query.filter(EvaluationRubricModel.course_code == course_code)
        if assessment_type:
            query = query.filter(EvaluationRubricModel.assessment_type == AssessmentTypeEnum(assessment_type.value))
        if department:
            query = query.filter(EvaluationRubricModel.department == department)
        if is_template is not None:
            query = query.filter(EvaluationRubricModel.is_template == is_template)

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return RubricListResponse(
            items=[RubricResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing rubrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/rubrics/{rubric_id}", response_model=RubricResponse, tags=["Criterion 2 - Rubrics"])
async def update_rubric(
    rubric_id: str,
    data: RubricUpdate,
    db: Session = Depends(get_db)
):
    """Update evaluation rubric."""
    try:
        rubric = db.query(EvaluationRubricModel).filter(EvaluationRubricModel.id == rubric_id).first()
        if not rubric:
            raise HTTPException(status_code=404, detail="Rubric not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rubric, key, value)

        db.commit()
        db.refresh(rubric)
        return RubricResponse.model_validate(rubric)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating rubric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- STUDENT PERFORMANCE --------------------

@router.post("/criterion2/performance", response_model=StudentPerformanceResponse, tags=["Criterion 2 - Performance"])
async def create_student_performance(
    data: StudentPerformanceCreate,
    db: Session = Depends(get_db)
):
    """Create student performance record."""
    try:
        performance = StudentPerformance(
            student_id=data.student_id,
            student_name=data.student_name,
            department=data.department,
            program=data.program,
            batch=data.batch,
            semester=data.semester,
            academic_year=data.academic_year,
            sgpa=data.sgpa,
            cgpa=data.cgpa,
            total_credits_earned=data.total_credits_earned,
            total_credits_attempted=data.total_credits_attempted,
            percentage=data.percentage,
            performance_level=PerformanceLevelEnum(data.performance_level.value) if data.performance_level else None,
        )
        db.add(performance)
        db.commit()
        db.refresh(performance)
        return StudentPerformanceResponse.model_validate(performance)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating student performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/performance", response_model=StudentPerformanceListResponse, tags=["Criterion 2 - Performance"])
async def list_student_performance(
    student_id: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[int] = None,
    academic_year: Optional[str] = None,
    performance_level: Optional[PerformanceLevel] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List student performance records."""
    try:
        query = db.query(StudentPerformance)

        if student_id:
            query = query.filter(StudentPerformance.student_id == student_id)
        if department:
            query = query.filter(StudentPerformance.department == department)
        if semester:
            query = query.filter(StudentPerformance.semester == semester)
        if academic_year:
            query = query.filter(StudentPerformance.academic_year == academic_year)
        if performance_level:
            query = query.filter(StudentPerformance.performance_level == PerformanceLevelEnum(performance_level.value))

        total = query.count()
        items = query.order_by(StudentPerformance.cgpa.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Get performance level distribution
        by_level = {}
        for level in PerformanceLevelEnum:
            count = db.query(StudentPerformance).filter(StudentPerformance.performance_level == level).count()
            if count > 0:
                by_level[level.value] = count

        return StudentPerformanceListResponse(
            items=[StudentPerformanceResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            by_performance_level=by_level
        )
    except Exception as e:
        logger.error(f"Error listing student performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/performance/{performance_id}", response_model=StudentPerformanceResponse, tags=["Criterion 2 - Performance"])
async def update_student_performance(
    performance_id: str,
    data: StudentPerformanceUpdate,
    db: Session = Depends(get_db)
):
    """Update student performance record."""
    try:
        performance = db.query(StudentPerformance).filter(StudentPerformance.id == performance_id).first()
        if not performance:
            raise HTTPException(status_code=404, detail="Performance record not found")

        update_data = data.model_dump(exclude_unset=True)

        if "performance_level" in update_data and update_data["performance_level"]:
            update_data["performance_level"] = PerformanceLevelEnum(update_data["performance_level"].value)

        for key, value in update_data.items():
            setattr(performance, key, value)

        db.commit()
        db.refresh(performance)
        return StudentPerformanceResponse.model_validate(performance)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating student performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/performance/analytics", response_model=StudentPerformanceAnalytics, tags=["Criterion 2 - Performance"])
async def get_performance_analytics(
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
    semester: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get student performance analytics."""
    try:
        query = db.query(StudentPerformance)

        if department:
            query = query.filter(StudentPerformance.department == department)
        if academic_year:
            query = query.filter(StudentPerformance.academic_year == academic_year)
        if semester:
            query = query.filter(StudentPerformance.semester == semester)

        records = query.all()
        total = len(records)

        if total == 0:
            return StudentPerformanceAnalytics(
                total_students=0,
                average_sgpa=0,
                average_cgpa=0,
                pass_percentage=0,
                performance_distribution={},
                top_performers=[],
                at_risk_students=0,
                average_attendance=0
            )

        # Calculate analytics
        avg_sgpa = sum(r.sgpa or 0 for r in records) / total
        avg_cgpa = sum(r.cgpa or 0 for r in records) / total
        passed = sum(1 for r in records if r.is_passed)
        pass_pct = (passed / total * 100) if total > 0 else 0
        avg_attendance = sum(r.overall_attendance_percentage or 0 for r in records) / total

        # Performance distribution
        dist = {}
        for level in PerformanceLevelEnum:
            count = sum(1 for r in records if r.performance_level == level)
            if count > 0:
                dist[level.value] = count

        # Top performers
        top = sorted([r for r in records if r.cgpa], key=lambda x: x.cgpa or 0, reverse=True)[:10]
        top_performers = [{"student_id": r.student_id, "student_name": r.student_name, "cgpa": r.cgpa} for r in top]

        # At-risk students (CGPA < 5 or attendance < 75%)
        at_risk = sum(1 for r in records if (r.cgpa and r.cgpa < 5) or (r.overall_attendance_percentage and r.overall_attendance_percentage < 75))

        return StudentPerformanceAnalytics(
            total_students=total,
            average_sgpa=round(avg_sgpa, 2),
            average_cgpa=round(avg_cgpa, 2),
            pass_percentage=round(pass_pct, 2),
            performance_distribution=dist,
            top_performers=top_performers,
            at_risk_students=at_risk,
            average_attendance=round(avg_attendance, 2)
        )
    except Exception as e:
        logger.error(f"Error getting performance analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- TEACHER PROFILES --------------------

@router.post("/criterion2/teachers", response_model=TeacherProfileResponse, tags=["Criterion 2 - Teachers"])
async def create_teacher_profile(
    data: TeacherProfileCreate,
    db: Session = Depends(get_db)
):
    """Create teacher profile."""
    try:
        # Check if employee_id already exists
        existing = db.query(TeacherProfile).filter(TeacherProfile.employee_id == data.employee_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Employee ID already exists")

        teacher = TeacherProfile(
            employee_id=data.employee_id,
            name=data.name,
            email=data.email,
            phone=data.phone,
            department=data.department,
            designation=TeacherDesignationEnum(data.designation.value),
            highest_qualification=data.highest_qualification,
            specialization=data.specialization,
            qualifications_list=data.qualifications_list,
            teaching_experience_years=data.teaching_experience_years,
            industry_experience_years=data.industry_experience_years,
            research_experience_years=data.research_experience_years,
            date_of_joining=data.date_of_joining,
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        return TeacherProfileResponse.model_validate(teacher)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating teacher profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/teachers", response_model=TeacherProfileListResponse, tags=["Criterion 2 - Teachers"])
async def list_teacher_profiles(
    department: Optional[str] = None,
    designation: Optional[TeacherDesignation] = None,
    is_active: bool = True,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List teacher profiles."""
    try:
        query = db.query(TeacherProfile).filter(TeacherProfile.is_active == is_active)

        if department:
            query = query.filter(TeacherProfile.department == department)
        if designation:
            query = query.filter(TeacherProfile.designation == TeacherDesignationEnum(designation.value))

        total = query.count()
        items = query.order_by(TeacherProfile.name).offset((page - 1) * page_size).limit(page_size).all()

        # Get designation distribution
        by_designation = {}
        for d in TeacherDesignationEnum:
            count = db.query(TeacherProfile).filter(TeacherProfile.designation == d, TeacherProfile.is_active == True).count()
            if count > 0:
                by_designation[d.value] = count

        return TeacherProfileListResponse(
            items=[TeacherProfileResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            by_designation=by_designation
        )
    except Exception as e:
        logger.error(f"Error listing teacher profiles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/teachers/{teacher_id}", response_model=TeacherProfileResponse, tags=["Criterion 2 - Teachers"])
async def update_teacher_profile(
    teacher_id: str,
    data: TeacherProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update teacher profile."""
    try:
        teacher = db.query(TeacherProfile).filter(TeacherProfile.id == teacher_id).first()
        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher profile not found")

        update_data = data.model_dump(exclude_unset=True)

        if "designation" in update_data and update_data["designation"]:
            update_data["designation"] = TeacherDesignationEnum(update_data["designation"].value)

        for key, value in update_data.items():
            setattr(teacher, key, value)

        db.commit()
        db.refresh(teacher)
        return TeacherProfileResponse.model_validate(teacher)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating teacher profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- DIGITAL CONTENT --------------------

@router.post("/criterion2/digital-content", response_model=DigitalContentResponse, tags=["Criterion 2 - Digital Content"])
async def create_digital_content(
    data: DigitalContentCreate,
    db: Session = Depends(get_db)
):
    """Create digital content record."""
    try:
        content = DigitalContent(
            title=data.title,
            description=data.description,
            content_type=ContentTypeEnum(data.content_type.value),
            course_code=data.course_code,
            course_name=data.course_name,
            department=data.department,
            semester=data.semester,
            topics=data.topics,
            learning_outcomes=data.learning_outcomes,
            blooms_level=BloomsLevelEnum(data.blooms_level.value) if data.blooms_level else None,
            external_url=data.external_url,
            duration_minutes=data.duration_minutes,
            created_by=data.created_by,
            creator_email=data.creator_email,
        )
        db.add(content)
        db.commit()
        db.refresh(content)
        return DigitalContentResponse.model_validate(content)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating digital content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/digital-content", response_model=DigitalContentListResponse, tags=["Criterion 2 - Digital Content"])
async def list_digital_content(
    department: Optional[str] = None,
    course_code: Optional[str] = None,
    content_type: Optional[ContentType] = None,
    is_published: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List digital content."""
    try:
        query = db.query(DigitalContent)

        if department:
            query = query.filter(DigitalContent.department == department)
        if course_code:
            query = query.filter(DigitalContent.course_code == course_code)
        if content_type:
            query = query.filter(DigitalContent.content_type == ContentTypeEnum(content_type.value))
        if is_published is not None:
            query = query.filter(DigitalContent.is_published == is_published)

        total = query.count()
        items = query.order_by(DigitalContent.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Get type distribution
        by_type = {}
        for t in ContentTypeEnum:
            count = db.query(DigitalContent).filter(DigitalContent.content_type == t).count()
            if count > 0:
                by_type[t.value] = count

        return DigitalContentListResponse(
            items=[DigitalContentResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            by_type=by_type
        )
    except Exception as e:
        logger.error(f"Error listing digital content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/digital-content/{content_id}", response_model=DigitalContentResponse, tags=["Criterion 2 - Digital Content"])
async def update_digital_content(
    content_id: str,
    data: DigitalContentUpdate,
    db: Session = Depends(get_db)
):
    """Update digital content."""
    try:
        content = db.query(DigitalContent).filter(DigitalContent.id == content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Digital content not found")

        update_data = data.model_dump(exclude_unset=True)

        if "blooms_level" in update_data and update_data["blooms_level"]:
            update_data["blooms_level"] = BloomsLevelEnum(update_data["blooms_level"].value)

        for key, value in update_data.items():
            setattr(content, key, value)

        db.commit()
        db.refresh(content)
        return DigitalContentResponse.model_validate(content)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating digital content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- LEARNING OUTCOME ATTAINMENT --------------------

@router.post("/criterion2/lo-attainment", response_model=LOAttainmentResponse, tags=["Criterion 2 - LO Attainment"])
async def create_lo_attainment(
    data: LOAttainmentCreate,
    db: Session = Depends(get_db)
):
    """Create learning outcome attainment record."""
    try:
        attainment = LearningOutcomeAttainment(
            course_code=data.course_code,
            course_name=data.course_name,
            department=data.department,
            semester=data.semester,
            academic_year=data.academic_year,
            batch=data.batch,
            total_students=data.total_students,
            students_appeared=data.students_appeared,
            students_passed=data.students_passed,
            pass_percentage=round(data.students_passed / data.students_appeared * 100, 2) if data.students_passed and data.students_appeared else None,
            course_outcomes=[co.model_dump() for co in data.course_outcomes],
            co_po_mapping=data.co_po_mapping,
            direct_assessment_methods=data.direct_assessment_methods,
            indirect_assessment_methods=data.indirect_assessment_methods,
            direct_weightage=data.direct_weightage,
            indirect_weightage=data.indirect_weightage,
            attainment_threshold=data.attainment_threshold,
            course_coordinator=data.course_coordinator,
        )
        db.add(attainment)
        db.commit()
        db.refresh(attainment)
        return LOAttainmentResponse.model_validate(attainment)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating LO attainment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/lo-attainment", response_model=LOAttainmentListResponse, tags=["Criterion 2 - LO Attainment"])
async def list_lo_attainments(
    department: Optional[str] = None,
    course_code: Optional[str] = None,
    academic_year: Optional[str] = None,
    semester: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List learning outcome attainment records."""
    try:
        query = db.query(LearningOutcomeAttainment)

        if department:
            query = query.filter(LearningOutcomeAttainment.department == department)
        if course_code:
            query = query.filter(LearningOutcomeAttainment.course_code == course_code)
        if academic_year:
            query = query.filter(LearningOutcomeAttainment.academic_year == academic_year)
        if semester:
            query = query.filter(LearningOutcomeAttainment.semester == semester)

        total = query.count()
        items = query.order_by(LearningOutcomeAttainment.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return LOAttainmentListResponse(
            items=[LOAttainmentResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error listing LO attainments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/lo-attainment/{attainment_id}", response_model=LOAttainmentResponse, tags=["Criterion 2 - LO Attainment"])
async def update_lo_attainment(
    attainment_id: str,
    data: LOAttainmentUpdate,
    db: Session = Depends(get_db)
):
    """Update learning outcome attainment with calculated values."""
    try:
        attainment = db.query(LearningOutcomeAttainment).filter(LearningOutcomeAttainment.id == attainment_id).first()
        if not attainment:
            raise HTTPException(status_code=404, detail="LO attainment record not found")

        update_data = data.model_dump(exclude_unset=True)

        if "verified_by" in update_data:
            update_data["verified_at"] = datetime.utcnow()

        for key, value in update_data.items():
            setattr(attainment, key, value)

        db.commit()
        db.refresh(attainment)
        return LOAttainmentResponse.model_validate(attainment)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating LO attainment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- BLENDED LEARNING --------------------

@router.post("/criterion2/blended-learning", response_model=BlendedLearningResponse, tags=["Criterion 2 - Blended Learning"])
async def create_blended_learning_session(
    data: BlendedLearningCreate,
    db: Session = Depends(get_db)
):
    """Create blended learning session record."""
    try:
        session = BlendedLearningSession(
            course_code=data.course_code,
            course_name=data.course_name,
            department=data.department,
            semester=data.semester,
            academic_year=data.academic_year,
            session_title=data.session_title,
            session_date=data.session_date,
            duration_minutes=data.duration_minutes,
            teaching_method=TeachingMethodEnum(data.teaching_method.value),
            is_synchronous=data.is_synchronous,
            online_component_percentage=data.online_component_percentage,
            offline_component_percentage=data.offline_component_percentage,
            tools_used=data.tools_used,
            lms_platform=data.lms_platform,
            faculty_name=data.faculty_name,
            faculty_email=data.faculty_email,
            students_enrolled=data.students_enrolled,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return BlendedLearningResponse.model_validate(session)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating blended learning session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion2/blended-learning", response_model=BlendedLearningListResponse, tags=["Criterion 2 - Blended Learning"])
async def list_blended_learning_sessions(
    department: Optional[str] = None,
    course_code: Optional[str] = None,
    academic_year: Optional[str] = None,
    teaching_method: Optional[TeachingMethod] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List blended learning sessions."""
    try:
        query = db.query(BlendedLearningSession)

        if department:
            query = query.filter(BlendedLearningSession.department == department)
        if course_code:
            query = query.filter(BlendedLearningSession.course_code == course_code)
        if academic_year:
            query = query.filter(BlendedLearningSession.academic_year == academic_year)
        if teaching_method:
            query = query.filter(BlendedLearningSession.teaching_method == TeachingMethodEnum(teaching_method.value))

        total = query.count()
        items = query.order_by(BlendedLearningSession.session_date.desc()).offset((page - 1) * page_size).limit(page_size).all()

        # Get method distribution
        by_method = {}
        for m in TeachingMethodEnum:
            count = db.query(BlendedLearningSession).filter(BlendedLearningSession.teaching_method == m).count()
            if count > 0:
                by_method[m.value] = count

        return BlendedLearningListResponse(
            items=[BlendedLearningResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            page_size=page_size,
            by_method=by_method
        )
    except Exception as e:
        logger.error(f"Error listing blended learning sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/criterion2/blended-learning/{session_id}", response_model=BlendedLearningResponse, tags=["Criterion 2 - Blended Learning"])
async def update_blended_learning_session(
    session_id: str,
    data: BlendedLearningUpdate,
    db: Session = Depends(get_db)
):
    """Update blended learning session."""
    try:
        session = db.query(BlendedLearningSession).filter(BlendedLearningSession.id == session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Blended learning session not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(session, key, value)

        db.commit()
        db.refresh(session)
        return BlendedLearningResponse.model_validate(session)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating blended learning session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- CRITERION 2 DASHBOARD --------------------

@router.get("/criterion2/dashboard", response_model=Criterion2DashboardStats, tags=["Criterion 2 - Dashboard"])
async def get_criterion2_dashboard(
    academic_year: Optional[str] = None,
    department: Optional[str] = None,
):
    """Get Criterion 2 dashboard statistics."""
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion2DashboardStats(
        total_students=0,
        student_diversity={"total": 0},
        total_teachers=0,
        student_teacher_ratio=0,
        teachers_with_phd=0,
        phd_percentage=0,
        lms_adoption_rate=0,
        total_digital_content=0,
        blended_learning_sessions=0,
        lesson_plans_created=0,
        teaching_methods_used={},
        teachers_with_awards=0,
        average_experience_years=0,
        fdp_participation_rate=0,
        average_feedback_rating=0,
        rubrics_created=0,
        cie_assessments=0,
        blooms_coverage={},
        average_pass_percentage=0,
        students_with_distinction=0,
        average_co_attainment=0,
        average_po_attainment=0,
        completion_percentage=0,
        pending_items=[]
    )


# -------------------- CRITERION 2 REPORT GENERATION --------------------

@router.post("/criterion2/generate-report", response_model=Criterion2ReportResponse, tags=["Criterion 2 - Reports"])
async def generate_criterion2_report(
    request: Criterion2ReportRequest,
    db: Session = Depends(get_db)
):
    """Generate complete Criterion 2 report for NAAC submission."""
    try:
        from app.utils.document_generator import document_generator

        # Get all data for the academic year
        lms_records = db.query(LMSAdoption).filter(LMSAdoption.academic_year == request.academic_year).all()
        lesson_plans = db.query(LessonPlan).filter(LessonPlan.academic_year == request.academic_year).all()
        teachers = db.query(TeacherProfile).filter(TeacherProfile.is_active == True).all()
        rubrics = db.query(EvaluationRubricModel).filter(EvaluationRubricModel.is_active == True).all()
        performances = db.query(StudentPerformance).filter(StudentPerformance.academic_year == request.academic_year).all()
        lo_records = db.query(LearningOutcomeAttainment).filter(LearningOutcomeAttainment.academic_year == request.academic_year).all()
        blended_sessions = db.query(BlendedLearningSession).filter(BlendedLearningSession.academic_year == request.academic_year).all()
        digital_content = db.query(DigitalContent).all()

        if request.department:
            teachers = [t for t in teachers if t.department == request.department]
            performances = [p for p in performances if p.department == request.department]

        # Prepare report content
        sections = request.include_sections or ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6"]

        report_content = {
            "title": f"NAAC Criterion 2: Teaching-Learning and Evaluation - {request.institution_name}",
            "academic_year": request.academic_year,
            "generated_at": datetime.utcnow().isoformat(),
            "sections": {}
        }

        if "2.1" in sections:
            report_content["sections"]["2.1"] = {
                "title": "Student Enrollment and Profile",
                "total_students": len(performances),
                "note": "Enrollment data from performance records"
            }

        if "2.2" in sections:
            total_teachers = len(teachers)
            total_students = len(performances)
            report_content["sections"]["2.2"] = {
                "title": "Student-Teacher Ratio",
                "total_teachers": total_teachers,
                "total_students": total_students,
                "ratio": round(total_students / total_teachers, 2) if total_teachers > 0 else 0,
                "teachers_with_phd": sum(1 for t in teachers if t.highest_qualification and "ph.d" in t.highest_qualification.lower())
            }

        if "2.3" in sections:
            report_content["sections"]["2.3"] = {
                "title": "Teaching-Learning Process",
                "lms_platforms": len(lms_records),
                "lesson_plans": len(lesson_plans),
                "blended_sessions": len(blended_sessions),
                "digital_content": len(digital_content),
                "ict_usage": sum(1 for t in teachers if t.uses_lms)
            }

        if "2.4" in sections:
            report_content["sections"]["2.4"] = {
                "title": "Teacher Quality",
                "total_faculty": len(teachers),
                "professors": sum(1 for t in teachers if t.designation == TeacherDesignationEnum.PROFESSOR),
                "associate_professors": sum(1 for t in teachers if t.designation == TeacherDesignationEnum.ASSOCIATE_PROFESSOR),
                "assistant_professors": sum(1 for t in teachers if t.designation == TeacherDesignationEnum.ASSISTANT_PROFESSOR),
                "average_experience": round(sum(t.teaching_experience_years for t in teachers) / len(teachers), 2) if teachers else 0,
                "with_awards": sum(1 for t in teachers if t.awards)
            }

        if "2.5" in sections:
            report_content["sections"]["2.5"] = {
                "title": "Evaluation Process and Reforms",
                "rubrics_created": len(rubrics),
                "rubric_types": list(set(r.assessment_type.value for r in rubrics if r.assessment_type))
            }

        if "2.6" in sections:
            passed = sum(1 for p in performances if p.is_passed)
            report_content["sections"]["2.6"] = {
                "title": "Student Performance and Learning Outcomes",
                "total_evaluated": len(performances),
                "pass_percentage": round(passed / len(performances) * 100, 2) if performances else 0,
                "lo_attainments_recorded": len(lo_records)
            }

        if request.include_analytics:
            report_content["analytics"] = {
                "avg_cgpa": round(sum(p.cgpa or 0 for p in performances) / len(performances), 2) if performances else 0,
                "lms_adoption_summary": [{"platform": l.platform.value, "department": l.department, "students": l.total_students_registered} for l in lms_records[:5]]
            }

        # Generate document
        if request.format == "docx":
            doc_bytes = document_generator.generate_accreditation_docx(
                content=report_content,
                title=f"Criterion 2 Report - {request.academic_year}"
            )
            file_ext = "docx"
        else:
            doc_bytes = document_generator.generate_accreditation_pdf(
                content=report_content,
                title=f"Criterion 2 Report - {request.academic_year}"
            )
            file_ext = "pdf"

        # Save report
        report_dir = "uploads/criterion2/reports"
        os.makedirs(report_dir, exist_ok=True)
        report_path = f"{report_dir}/criterion2_report_{request.academic_year.replace('-', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_ext}"

        with open(report_path, "wb") as f:
            f.write(doc_bytes)

        return Criterion2ReportResponse(
            success=True,
            report_path=report_path,
            sections_included=sections,
            generated_at=datetime.utcnow(),
            metadata={"file_size": len(doc_bytes), "format": request.format}
        )
    except Exception as e:
        logger.error(f"Error generating Criterion 2 report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CRITERION 3: RESEARCH, INNOVATIONS & EXTENSION ====================

# --- Research Projects ---

@router.post("/criterion3/research-projects", response_model=ResearchProjectResponse, tags=["Criterion 3: Research Projects"])
async def create_research_project(request: ResearchProjectCreate, db: Session = Depends(get_db)):
    """Create a new research project."""
    try:
        project = ResearchProject(
            title=request.title,
            project_type=ProjectTypeEnum(request.project_type),
            description=request.description,
            objectives=request.objectives,
            methodology=request.methodology,
            department=request.department,
            domain=request.domain,
            keywords=request.keywords,
            start_date=request.start_date,
            end_date=request.end_date,
            duration_months=request.duration_months,
            academic_year=request.academic_year,
            status=ResearchProjectStatusEnum(request.status) if request.status else ResearchProjectStatusEnum.PROPOSED,
            principal_investigator=request.principal_investigator,
            pi_designation=request.pi_designation,
            pi_email=request.pi_email,
            co_investigators=request.co_investigators,
            student_researchers=request.student_researchers,
            funding_agency=FundingAgencyEnum(request.funding_agency) if request.funding_agency else None,
            funding_agency_name=request.funding_agency_name,
            sanctioned_amount=request.sanctioned_amount,
            received_amount=request.received_amount,
            grant_number=request.grant_number,
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return ResearchProjectResponse.model_validate(project)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating research project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/research-projects", response_model=ResearchProjectListResponse, tags=["Criterion 3: Research Projects"])
async def list_research_projects(
    department: Optional[str] = None,
    project_type: Optional[str] = None,
    status: Optional[str] = None,
    academic_year: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List research projects with optional filters."""
    try:
        query = db.query(ResearchProject)

        if department:
            query = query.filter(ResearchProject.department == department)
        if project_type:
            query = query.filter(ResearchProject.project_type == project_type)
        if status:
            query = query.filter(ResearchProject.status == status)
        if academic_year:
            query = query.filter(ResearchProject.academic_year == academic_year)

        total = query.count()
        projects = query.order_by(ResearchProject.created_at.desc()).offset(skip).limit(limit).all()

        return ResearchProjectListResponse(
            projects=[ResearchProjectResponse.model_validate(p) for p in projects],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing research projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/research-projects/{project_id}", response_model=ResearchProjectResponse, tags=["Criterion 3: Research Projects"])
async def get_research_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific research project by ID."""
    project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found")
    return ResearchProjectResponse.model_validate(project)


@router.put("/criterion3/research-projects/{project_id}", response_model=ResearchProjectResponse, tags=["Criterion 3: Research Projects"])
async def update_research_project(project_id: str, request: ResearchProjectUpdate, db: Session = Depends(get_db)):
    """Update a research project."""
    try:
        project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Research project not found")

        update_data = request.model_dump(exclude_unset=True)
        if "project_type" in update_data and update_data["project_type"]:
            update_data["project_type"] = ProjectTypeEnum(update_data["project_type"])
        if "status" in update_data and update_data["status"]:
            update_data["status"] = ResearchProjectStatusEnum(update_data["status"])
        if "funding_agency" in update_data and update_data["funding_agency"]:
            update_data["funding_agency"] = FundingAgencyEnum(update_data["funding_agency"])

        for key, value in update_data.items():
            setattr(project, key, value)

        db.commit()
        db.refresh(project)
        return ResearchProjectResponse.model_validate(project)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating research project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/research-projects/{project_id}", tags=["Criterion 3: Research Projects"])
async def delete_research_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a research project."""
    try:
        project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Research project not found")

        db.delete(project)
        db.commit()
        return {"success": True, "message": "Research project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting research project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Publications ---

@router.post("/criterion3/publications", response_model=PublicationResponse, tags=["Criterion 3: Publications"])
async def create_publication(request: PublicationCreate, db: Session = Depends(get_db)):
    """Create a new publication record."""
    try:
        publication = Publication(
            title=request.title,
            publication_type=PublicationTypeEnum(request.publication_type),
            abstract=request.abstract,
            keywords=request.keywords,
            authors=request.authors,
            corresponding_author=request.corresponding_author,
            department=request.department,
            journal_name=request.journal_name,
            conference_name=request.conference_name,
            publisher=request.publisher,
            volume=request.volume,
            issue=request.issue,
            pages=request.pages,
            publication_year=request.publication_year,
            publication_date=request.publication_date,
            indexing=PublicationIndexingEnum(request.indexing) if request.indexing else PublicationIndexingEnum.NONE,
            impact_factor=request.impact_factor,
            h_index=request.h_index,
            citations=request.citations or 0,
            doi=request.doi,
            issn=request.issn,
            isbn=request.isbn,
            paper_url=request.paper_url,
            project_id=request.project_id,
        )
        db.add(publication)
        db.commit()
        db.refresh(publication)
        return PublicationResponse.model_validate(publication)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating publication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/publications", response_model=PublicationListResponse, tags=["Criterion 3: Publications"])
async def list_publications(
    department: Optional[str] = None,
    publication_type: Optional[str] = None,
    publication_year: Optional[int] = None,
    indexing: Optional[str] = None,
    is_verified: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List publications with optional filters."""
    try:
        query = db.query(Publication)

        if department:
            query = query.filter(Publication.department == department)
        if publication_type:
            query = query.filter(Publication.publication_type == publication_type)
        if publication_year:
            query = query.filter(Publication.publication_year == publication_year)
        if indexing:
            query = query.filter(Publication.indexing == indexing)
        if is_verified is not None:
            query = query.filter(Publication.is_verified == is_verified)

        total = query.count()
        publications = query.order_by(Publication.publication_year.desc(), Publication.created_at.desc()).offset(skip).limit(limit).all()

        return PublicationListResponse(
            publications=[PublicationResponse.model_validate(p) for p in publications],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing publications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/publications/{publication_id}", response_model=PublicationResponse, tags=["Criterion 3: Publications"])
async def get_publication(publication_id: str, db: Session = Depends(get_db)):
    """Get a specific publication by ID."""
    publication = db.query(Publication).filter(Publication.id == publication_id).first()
    if not publication:
        raise HTTPException(status_code=404, detail="Publication not found")
    return PublicationResponse.model_validate(publication)


@router.put("/criterion3/publications/{publication_id}", response_model=PublicationResponse, tags=["Criterion 3: Publications"])
async def update_publication(publication_id: str, request: PublicationUpdate, db: Session = Depends(get_db)):
    """Update a publication record."""
    try:
        publication = db.query(Publication).filter(Publication.id == publication_id).first()
        if not publication:
            raise HTTPException(status_code=404, detail="Publication not found")

        update_data = request.model_dump(exclude_unset=True)
        if "publication_type" in update_data and update_data["publication_type"]:
            update_data["publication_type"] = PublicationTypeEnum(update_data["publication_type"])
        if "indexing" in update_data and update_data["indexing"]:
            update_data["indexing"] = PublicationIndexingEnum(update_data["indexing"])

        for key, value in update_data.items():
            setattr(publication, key, value)

        db.commit()
        db.refresh(publication)
        return PublicationResponse.model_validate(publication)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating publication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/criterion3/publications/{publication_id}/verify", response_model=PublicationResponse, tags=["Criterion 3: Publications"])
async def verify_publication(publication_id: str, verified_by: str = Query(...), db: Session = Depends(get_db)):
    """Verify a publication record."""
    try:
        publication = db.query(Publication).filter(Publication.id == publication_id).first()
        if not publication:
            raise HTTPException(status_code=404, detail="Publication not found")

        publication.is_verified = True
        publication.verified_by = verified_by
        publication.verified_at = datetime.utcnow()

        db.commit()
        db.refresh(publication)
        return PublicationResponse.model_validate(publication)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error verifying publication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/publications/{publication_id}", tags=["Criterion 3: Publications"])
async def delete_publication(publication_id: str, db: Session = Depends(get_db)):
    """Delete a publication record."""
    try:
        publication = db.query(Publication).filter(Publication.id == publication_id).first()
        if not publication:
            raise HTTPException(status_code=404, detail="Publication not found")

        db.delete(publication)
        db.commit()
        return {"success": True, "message": "Publication deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting publication: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Patents ---

@router.post("/criterion3/patents", response_model=PatentResponse, tags=["Criterion 3: Patents"])
async def create_patent(request: PatentCreate, db: Session = Depends(get_db)):
    """Create a new patent record."""
    try:
        patent = Patent(
            title=request.title,
            patent_type=PatentTypeEnum(request.patent_type),
            status=PatentStatusEnum(request.status) if request.status else PatentStatusEnum.FILED,
            description=request.description,
            claims=request.claims,
            application_number=request.application_number,
            filing_date=request.filing_date,
            filing_year=request.filing_year,
            inventors=request.inventors,
            applicant=request.applicant,
            department=request.department,
            ipc_class=request.ipc_class,
            technology_area=request.technology_area,
            project_id=request.project_id,
        )
        db.add(patent)
        db.commit()
        db.refresh(patent)
        return PatentResponse.model_validate(patent)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating patent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/patents", response_model=PatentListResponse, tags=["Criterion 3: Patents"])
async def list_patents(
    department: Optional[str] = None,
    patent_type: Optional[str] = None,
    status: Optional[str] = None,
    filing_year: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List patents with optional filters."""
    try:
        query = db.query(Patent)

        if department:
            query = query.filter(Patent.department == department)
        if patent_type:
            query = query.filter(Patent.patent_type == patent_type)
        if status:
            query = query.filter(Patent.status == status)
        if filing_year:
            query = query.filter(Patent.filing_year == filing_year)

        total = query.count()
        patents = query.order_by(Patent.filing_date.desc()).offset(skip).limit(limit).all()

        return PatentListResponse(
            patents=[PatentResponse.model_validate(p) for p in patents],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing patents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/patents/{patent_id}", response_model=PatentResponse, tags=["Criterion 3: Patents"])
async def get_patent(patent_id: str, db: Session = Depends(get_db)):
    """Get a specific patent by ID."""
    patent = db.query(Patent).filter(Patent.id == patent_id).first()
    if not patent:
        raise HTTPException(status_code=404, detail="Patent not found")
    return PatentResponse.model_validate(patent)


@router.put("/criterion3/patents/{patent_id}", response_model=PatentResponse, tags=["Criterion 3: Patents"])
async def update_patent(patent_id: str, request: PatentUpdate, db: Session = Depends(get_db)):
    """Update a patent record."""
    try:
        patent = db.query(Patent).filter(Patent.id == patent_id).first()
        if not patent:
            raise HTTPException(status_code=404, detail="Patent not found")

        update_data = request.model_dump(exclude_unset=True)
        if "patent_type" in update_data and update_data["patent_type"]:
            update_data["patent_type"] = PatentTypeEnum(update_data["patent_type"])
        if "status" in update_data and update_data["status"]:
            update_data["status"] = PatentStatusEnum(update_data["status"])

        for key, value in update_data.items():
            setattr(patent, key, value)

        db.commit()
        db.refresh(patent)
        return PatentResponse.model_validate(patent)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating patent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/patents/{patent_id}", tags=["Criterion 3: Patents"])
async def delete_patent(patent_id: str, db: Session = Depends(get_db)):
    """Delete a patent record."""
    try:
        patent = db.query(Patent).filter(Patent.id == patent_id).first()
        if not patent:
            raise HTTPException(status_code=404, detail="Patent not found")

        db.delete(patent)
        db.commit()
        return {"success": True, "message": "Patent deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting patent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Startups ---

@router.post("/criterion3/startups", response_model=StartupResponse, tags=["Criterion 3: Startups"])
async def create_startup(request: StartupCreate, db: Session = Depends(get_db)):
    """Create a new startup record."""
    try:
        startup = Startup(
            name=request.name,
            description=request.description,
            problem_statement=request.problem_statement,
            solution=request.solution,
            industry_sector=request.industry_sector,
            technology_used=request.technology_used,
            stage=StartupStageEnum(request.stage) if request.stage else StartupStageEnum.IDEATION,
            status=StartupStatusEnum(request.status) if request.status else StartupStatusEnum.INCUBATED,
            founders=request.founders,
            department=request.department,
            incubated_at=request.incubated_at,
            registration_number=request.registration_number,
            registration_date=request.registration_date,
            dpiit_recognized=request.dpiit_recognized or False,
            dpiit_number=request.dpiit_number,
            seed_funding=request.seed_funding,
            total_funding=request.total_funding,
            website=request.website,
            email=request.email,
            phone=request.phone,
            founded_date=request.founded_date,
        )
        db.add(startup)
        db.commit()
        db.refresh(startup)
        return StartupResponse.model_validate(startup)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating startup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/startups", response_model=StartupListResponse, tags=["Criterion 3: Startups"])
async def list_startups(
    department: Optional[str] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    dpiit_recognized: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List startups with optional filters."""
    try:
        query = db.query(Startup)

        if department:
            query = query.filter(Startup.department == department)
        if stage:
            query = query.filter(Startup.stage == stage)
        if status:
            query = query.filter(Startup.status == status)
        if dpiit_recognized is not None:
            query = query.filter(Startup.dpiit_recognized == dpiit_recognized)

        total = query.count()
        startups = query.order_by(Startup.created_at.desc()).offset(skip).limit(limit).all()

        return StartupListResponse(
            startups=[StartupResponse.model_validate(s) for s in startups],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing startups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/startups/{startup_id}", response_model=StartupResponse, tags=["Criterion 3: Startups"])
async def get_startup(startup_id: str, db: Session = Depends(get_db)):
    """Get a specific startup by ID."""
    startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not startup:
        raise HTTPException(status_code=404, detail="Startup not found")
    return StartupResponse.model_validate(startup)


@router.put("/criterion3/startups/{startup_id}", response_model=StartupResponse, tags=["Criterion 3: Startups"])
async def update_startup(startup_id: str, request: StartupUpdate, db: Session = Depends(get_db)):
    """Update a startup record."""
    try:
        startup = db.query(Startup).filter(Startup.id == startup_id).first()
        if not startup:
            raise HTTPException(status_code=404, detail="Startup not found")

        update_data = request.model_dump(exclude_unset=True)
        if "stage" in update_data and update_data["stage"]:
            update_data["stage"] = StartupStageEnum(update_data["stage"])
        if "status" in update_data and update_data["status"]:
            update_data["status"] = StartupStatusEnum(update_data["status"])

        for key, value in update_data.items():
            setattr(startup, key, value)

        db.commit()
        db.refresh(startup)
        return StartupResponse.model_validate(startup)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating startup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/startups/{startup_id}", tags=["Criterion 3: Startups"])
async def delete_startup(startup_id: str, db: Session = Depends(get_db)):
    """Delete a startup record."""
    try:
        startup = db.query(Startup).filter(Startup.id == startup_id).first()
        if not startup:
            raise HTTPException(status_code=404, detail="Startup not found")

        db.delete(startup)
        db.commit()
        return {"success": True, "message": "Startup deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting startup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Innovation Cells ---

@router.post("/criterion3/innovation-cells", response_model=InnovationCellResponse, tags=["Criterion 3: Innovation Cells"])
async def create_innovation_cell(request: InnovationCellCreate, db: Session = Depends(get_db)):
    """Create a new innovation cell/IIC record."""
    try:
        cell = InnovationCell(
            name=request.name,
            cell_type=request.cell_type,
            registration_number=request.registration_number,
            establishment_date=request.establishment_date,
            academic_year=request.academic_year,
            coordinator_name=request.coordinator_name,
            coordinator_designation=request.coordinator_designation,
            coordinator_email=request.coordinator_email,
            coordinator_phone=request.coordinator_phone,
            faculty_members=request.faculty_members,
            student_members=request.student_members,
            external_mentors=request.external_mentors,
            iic_star_rating=request.iic_star_rating,
            annual_budget=request.annual_budget,
        )
        db.add(cell)
        db.commit()
        db.refresh(cell)
        return InnovationCellResponse.model_validate(cell)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating innovation cell: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/innovation-cells", response_model=InnovationCellListResponse, tags=["Criterion 3: Innovation Cells"])
async def list_innovation_cells(
    cell_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List innovation cells with optional filters."""
    try:
        query = db.query(InnovationCell)

        if cell_type:
            query = query.filter(InnovationCell.cell_type == cell_type)
        if academic_year:
            query = query.filter(InnovationCell.academic_year == academic_year)
        if is_active is not None:
            query = query.filter(InnovationCell.is_active == is_active)

        total = query.count()
        cells = query.order_by(InnovationCell.created_at.desc()).offset(skip).limit(limit).all()

        return InnovationCellListResponse(
            innovation_cells=[InnovationCellResponse.model_validate(c) for c in cells],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing innovation cells: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/innovation-cells/{cell_id}", response_model=InnovationCellResponse, tags=["Criterion 3: Innovation Cells"])
async def get_innovation_cell(cell_id: str, db: Session = Depends(get_db)):
    """Get a specific innovation cell by ID."""
    cell = db.query(InnovationCell).filter(InnovationCell.id == cell_id).first()
    if not cell:
        raise HTTPException(status_code=404, detail="Innovation cell not found")
    return InnovationCellResponse.model_validate(cell)


@router.put("/criterion3/innovation-cells/{cell_id}", response_model=InnovationCellResponse, tags=["Criterion 3: Innovation Cells"])
async def update_innovation_cell(cell_id: str, request: InnovationCellUpdate, db: Session = Depends(get_db)):
    """Update an innovation cell record."""
    try:
        cell = db.query(InnovationCell).filter(InnovationCell.id == cell_id).first()
        if not cell:
            raise HTTPException(status_code=404, detail="Innovation cell not found")

        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(cell, key, value)

        db.commit()
        db.refresh(cell)
        return InnovationCellResponse.model_validate(cell)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating innovation cell: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/innovation-cells/{cell_id}", tags=["Criterion 3: Innovation Cells"])
async def delete_innovation_cell(cell_id: str, db: Session = Depends(get_db)):
    """Delete an innovation cell record."""
    try:
        cell = db.query(InnovationCell).filter(InnovationCell.id == cell_id).first()
        if not cell:
            raise HTTPException(status_code=404, detail="Innovation cell not found")

        db.delete(cell)
        db.commit()
        return {"success": True, "message": "Innovation cell deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting innovation cell: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Hackathons & Events ---

@router.post("/criterion3/hackathons", response_model=HackathonResponse, tags=["Criterion 3: Hackathons"])
async def create_hackathon(request: HackathonCreate, db: Session = Depends(get_db)):
    """Create a new hackathon/event record."""
    try:
        hackathon = Hackathon(
            name=request.name,
            event_type=EventTypeEnum(request.event_type),
            description=request.description,
            theme=request.theme,
            problem_statements=request.problem_statements,
            organized_by=request.organized_by,
            is_internal=request.is_internal if request.is_internal is not None else True,
            department=request.department,
            academic_year=request.academic_year,
            event_date=request.event_date,
            end_date=request.end_date,
            duration_hours=request.duration_hours,
            venue=request.venue,
            mode=request.mode,
            registrations_count=request.registrations_count or 0,
            participants_count=request.participants_count or 0,
            teams_count=request.teams_count or 0,
            submissions_count=request.submissions_count or 0,
            total_prize_pool=request.total_prize_pool,
            sponsors=request.sponsors,
        )
        db.add(hackathon)
        db.commit()
        db.refresh(hackathon)
        return HackathonResponse.model_validate(hackathon)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating hackathon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/hackathons", response_model=HackathonListResponse, tags=["Criterion 3: Hackathons"])
async def list_hackathons(
    department: Optional[str] = None,
    event_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    is_internal: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List hackathons with optional filters."""
    try:
        query = db.query(Hackathon)

        if department:
            query = query.filter(Hackathon.department == department)
        if event_type:
            query = query.filter(Hackathon.event_type == event_type)
        if academic_year:
            query = query.filter(Hackathon.academic_year == academic_year)
        if is_internal is not None:
            query = query.filter(Hackathon.is_internal == is_internal)

        total = query.count()
        hackathons = query.order_by(Hackathon.event_date.desc()).offset(skip).limit(limit).all()

        return HackathonListResponse(
            hackathons=[HackathonResponse.model_validate(h) for h in hackathons],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing hackathons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/hackathons/{hackathon_id}", response_model=HackathonResponse, tags=["Criterion 3: Hackathons"])
async def get_hackathon(hackathon_id: str, db: Session = Depends(get_db)):
    """Get a specific hackathon by ID."""
    hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return HackathonResponse.model_validate(hackathon)


@router.put("/criterion3/hackathons/{hackathon_id}", response_model=HackathonResponse, tags=["Criterion 3: Hackathons"])
async def update_hackathon(hackathon_id: str, request: HackathonUpdate, db: Session = Depends(get_db)):
    """Update a hackathon record."""
    try:
        hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        update_data = request.model_dump(exclude_unset=True)
        if "event_type" in update_data and update_data["event_type"]:
            update_data["event_type"] = EventTypeEnum(update_data["event_type"])

        for key, value in update_data.items():
            setattr(hackathon, key, value)

        db.commit()
        db.refresh(hackathon)
        return HackathonResponse.model_validate(hackathon)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating hackathon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/hackathons/{hackathon_id}", tags=["Criterion 3: Hackathons"])
async def delete_hackathon(hackathon_id: str, db: Session = Depends(get_db)):
    """Delete a hackathon record."""
    try:
        hackathon = db.query(Hackathon).filter(Hackathon.id == hackathon_id).first()
        if not hackathon:
            raise HTTPException(status_code=404, detail="Hackathon not found")

        db.delete(hackathon)
        db.commit()
        return {"success": True, "message": "Hackathon deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting hackathon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Extension Activities ---

@router.post("/criterion3/extension-activities", response_model=ExtensionActivityResponse, tags=["Criterion 3: Extension Activities"])
async def create_extension_activity(request: ExtensionActivityCreate, db: Session = Depends(get_db)):
    """Create a new extension activity record."""
    try:
        activity = ExtensionActivity(
            title=request.title,
            activity_type=ExtensionTypeEnum(request.activity_type),
            description=request.description,
            objectives=request.objectives,
            outcomes=request.outcomes,
            organized_by=request.organized_by,
            department=request.department,
            academic_year=request.academic_year,
            venue=request.venue,
            village_adopted=request.village_adopted,
            district=request.district,
            state=request.state,
            activity_date=request.activity_date,
            end_date=request.end_date,
            duration_days=request.duration_days or 1,
            faculty_involved=request.faculty_involved,
            students_participated=request.students_participated or 0,
            beneficiaries_count=request.beneficiaries_count or 0,
            beneficiaries_type=request.beneficiaries_type,
            collaborating_agencies=request.collaborating_agencies,
            funding_received=request.funding_received,
            funding_source=request.funding_source,
            sdg_goals_addressed=request.sdg_goals_addressed,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        return ExtensionActivityResponse.model_validate(activity)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating extension activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/extension-activities", response_model=ExtensionActivityListResponse, tags=["Criterion 3: Extension Activities"])
async def list_extension_activities(
    department: Optional[str] = None,
    activity_type: Optional[str] = None,
    academic_year: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List extension activities with optional filters."""
    try:
        query = db.query(ExtensionActivity)

        if department:
            query = query.filter(ExtensionActivity.department == department)
        if activity_type:
            query = query.filter(ExtensionActivity.activity_type == activity_type)
        if academic_year:
            query = query.filter(ExtensionActivity.academic_year == academic_year)

        total = query.count()
        activities = query.order_by(ExtensionActivity.activity_date.desc()).offset(skip).limit(limit).all()

        return ExtensionActivityListResponse(
            extension_activities=[ExtensionActivityResponse.model_validate(a) for a in activities],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing extension activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/extension-activities/{activity_id}", response_model=ExtensionActivityResponse, tags=["Criterion 3: Extension Activities"])
async def get_extension_activity(activity_id: str, db: Session = Depends(get_db)):
    """Get a specific extension activity by ID."""
    activity = db.query(ExtensionActivity).filter(ExtensionActivity.id == activity_id).first()
    if not activity:
        raise HTTPException(status_code=404, detail="Extension activity not found")
    return ExtensionActivityResponse.model_validate(activity)


@router.put("/criterion3/extension-activities/{activity_id}", response_model=ExtensionActivityResponse, tags=["Criterion 3: Extension Activities"])
async def update_extension_activity(activity_id: str, request: ExtensionActivityUpdate, db: Session = Depends(get_db)):
    """Update an extension activity record."""
    try:
        activity = db.query(ExtensionActivity).filter(ExtensionActivity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Extension activity not found")

        update_data = request.model_dump(exclude_unset=True)
        if "activity_type" in update_data and update_data["activity_type"]:
            update_data["activity_type"] = ExtensionTypeEnum(update_data["activity_type"])

        for key, value in update_data.items():
            setattr(activity, key, value)

        db.commit()
        db.refresh(activity)
        return ExtensionActivityResponse.model_validate(activity)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating extension activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/extension-activities/{activity_id}", tags=["Criterion 3: Extension Activities"])
async def delete_extension_activity(activity_id: str, db: Session = Depends(get_db)):
    """Delete an extension activity record."""
    try:
        activity = db.query(ExtensionActivity).filter(ExtensionActivity.id == activity_id).first()
        if not activity:
            raise HTTPException(status_code=404, detail="Extension activity not found")

        db.delete(activity)
        db.commit()
        return {"success": True, "message": "Extension activity deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting extension activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Consultancies ---

@router.post("/criterion3/consultancies", response_model=ConsultancyResponse, tags=["Criterion 3: Consultancies"])
async def create_consultancy(request: ConsultancyCreate, db: Session = Depends(get_db)):
    """Create a new consultancy project record."""
    try:
        consultancy = Consultancy(
            title=request.title,
            description=request.description,
            scope_of_work=request.scope_of_work,
            deliverables=request.deliverables,
            client_name=request.client_name,
            client_type=request.client_type,
            client_contact=request.client_contact,
            client_email=request.client_email,
            department=request.department,
            academic_year=request.academic_year,
            consultant_name=request.consultant_name,
            consultant_designation=request.consultant_designation,
            team_members=request.team_members,
            start_date=request.start_date,
            end_date=request.end_date,
            status=ResearchProjectStatusEnum(request.status) if request.status else ResearchProjectStatusEnum.ONGOING,
            consultancy_amount=request.consultancy_amount,
            amount_received=request.amount_received,
            institute_share=request.institute_share,
            mou_number=request.mou_number,
            mou_date=request.mou_date,
        )
        db.add(consultancy)
        db.commit()
        db.refresh(consultancy)
        return ConsultancyResponse.model_validate(consultancy)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating consultancy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/consultancies", response_model=ConsultancyListResponse, tags=["Criterion 3: Consultancies"])
async def list_consultancies(
    department: Optional[str] = None,
    status: Optional[str] = None,
    academic_year: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List consultancies with optional filters."""
    try:
        query = db.query(Consultancy)

        if department:
            query = query.filter(Consultancy.department == department)
        if status:
            query = query.filter(Consultancy.status == status)
        if academic_year:
            query = query.filter(Consultancy.academic_year == academic_year)

        total = query.count()
        consultancies = query.order_by(Consultancy.created_at.desc()).offset(skip).limit(limit).all()

        return ConsultancyListResponse(
            consultancies=[ConsultancyResponse.model_validate(c) for c in consultancies],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing consultancies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/consultancies/{consultancy_id}", response_model=ConsultancyResponse, tags=["Criterion 3: Consultancies"])
async def get_consultancy(consultancy_id: str, db: Session = Depends(get_db)):
    """Get a specific consultancy by ID."""
    consultancy = db.query(Consultancy).filter(Consultancy.id == consultancy_id).first()
    if not consultancy:
        raise HTTPException(status_code=404, detail="Consultancy not found")
    return ConsultancyResponse.model_validate(consultancy)


@router.put("/criterion3/consultancies/{consultancy_id}", response_model=ConsultancyResponse, tags=["Criterion 3: Consultancies"])
async def update_consultancy(consultancy_id: str, request: ConsultancyUpdate, db: Session = Depends(get_db)):
    """Update a consultancy record."""
    try:
        consultancy = db.query(Consultancy).filter(Consultancy.id == consultancy_id).first()
        if not consultancy:
            raise HTTPException(status_code=404, detail="Consultancy not found")

        update_data = request.model_dump(exclude_unset=True)
        if "status" in update_data and update_data["status"]:
            update_data["status"] = ResearchProjectStatusEnum(update_data["status"])

        for key, value in update_data.items():
            setattr(consultancy, key, value)

        db.commit()
        db.refresh(consultancy)
        return ConsultancyResponse.model_validate(consultancy)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating consultancy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/consultancies/{consultancy_id}", tags=["Criterion 3: Consultancies"])
async def delete_consultancy(consultancy_id: str, db: Session = Depends(get_db)):
    """Delete a consultancy record."""
    try:
        consultancy = db.query(Consultancy).filter(Consultancy.id == consultancy_id).first()
        if not consultancy:
            raise HTTPException(status_code=404, detail="Consultancy not found")

        db.delete(consultancy)
        db.commit()
        return {"success": True, "message": "Consultancy deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting consultancy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Research Funding ---

@router.post("/criterion3/research-funding", response_model=ResearchFundingResponse, tags=["Criterion 3: Research Funding"])
async def create_research_funding(request: ResearchFundingCreate, db: Session = Depends(get_db)):
    """Create a new research funding record."""
    try:
        funding = ResearchFunding(
            scheme_name=request.scheme_name,
            funding_agency=FundingAgencyEnum(request.funding_agency),
            agency_name=request.agency_name,
            project_id=request.project_id,
            project_title=request.project_title,
            pi_name=request.pi_name,
            pi_designation=request.pi_designation,
            department=request.department,
            financial_year=request.financial_year,
            sanctioned_amount=request.sanctioned_amount,
            received_amount=request.received_amount,
            utilized_amount=request.utilized_amount,
            grant_number=request.grant_number,
            sanction_date=request.sanction_date,
            duration_years=request.duration_years,
        )
        db.add(funding)
        db.commit()
        db.refresh(funding)
        return ResearchFundingResponse.model_validate(funding)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating research funding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/research-funding", response_model=ResearchFundingListResponse, tags=["Criterion 3: Research Funding"])
async def list_research_funding(
    department: Optional[str] = None,
    funding_agency: Optional[str] = None,
    financial_year: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List research funding with optional filters."""
    try:
        query = db.query(ResearchFunding)

        if department:
            query = query.filter(ResearchFunding.department == department)
        if funding_agency:
            query = query.filter(ResearchFunding.funding_agency == funding_agency)
        if financial_year:
            query = query.filter(ResearchFunding.financial_year == financial_year)

        total = query.count()
        funding_records = query.order_by(ResearchFunding.created_at.desc()).offset(skip).limit(limit).all()

        return ResearchFundingListResponse(
            funding_records=[ResearchFundingResponse.model_validate(f) for f in funding_records],
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
    except Exception as e:
        logger.error(f"Error listing research funding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/criterion3/research-funding/{funding_id}", response_model=ResearchFundingResponse, tags=["Criterion 3: Research Funding"])
async def get_research_funding(funding_id: str, db: Session = Depends(get_db)):
    """Get a specific research funding record by ID."""
    funding = db.query(ResearchFunding).filter(ResearchFunding.id == funding_id).first()
    if not funding:
        raise HTTPException(status_code=404, detail="Research funding not found")
    return ResearchFundingResponse.model_validate(funding)


@router.put("/criterion3/research-funding/{funding_id}", response_model=ResearchFundingResponse, tags=["Criterion 3: Research Funding"])
async def update_research_funding(funding_id: str, request: ResearchFundingUpdate, db: Session = Depends(get_db)):
    """Update a research funding record."""
    try:
        funding = db.query(ResearchFunding).filter(ResearchFunding.id == funding_id).first()
        if not funding:
            raise HTTPException(status_code=404, detail="Research funding not found")

        update_data = request.model_dump(exclude_unset=True)
        if "funding_agency" in update_data and update_data["funding_agency"]:
            update_data["funding_agency"] = FundingAgencyEnum(update_data["funding_agency"])

        for key, value in update_data.items():
            setattr(funding, key, value)

        db.commit()
        db.refresh(funding)
        return ResearchFundingResponse.model_validate(funding)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating research funding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/criterion3/research-funding/{funding_id}", tags=["Criterion 3: Research Funding"])
async def delete_research_funding(funding_id: str, db: Session = Depends(get_db)):
    """Delete a research funding record."""
    try:
        funding = db.query(ResearchFunding).filter(ResearchFunding.id == funding_id).first()
        if not funding:
            raise HTTPException(status_code=404, detail="Research funding not found")

        db.delete(funding)
        db.commit()
        return {"success": True, "message": "Research funding deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting research funding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Criterion 3 Dashboard ---

@router.get("/criterion3/dashboard", response_model=Criterion3DashboardStats, tags=["Criterion 3: Dashboard"])
async def get_criterion3_dashboard(
    department: Optional[str] = None,
    academic_year: Optional[str] = None,
):
    """Get Criterion 3 dashboard statistics."""
    # Return default stats (database queries will be implemented with async patterns later)
    return Criterion3DashboardStats(
        total_projects=0,
        ongoing_projects=0,
        completed_projects=0,
        total_funding_sanctioned=0,
        total_funding_received=0,
        funding_by_agency={},
        total_patents_filed=0,
        patents_granted=0,
        total_startups=0,
        startups_funded=0,
        innovation_cells=0,
        iic_star_rating=None,
        total_publications=0,
        publications_by_type={},
        publications_by_indexing={},
        total_citations=0,
        average_impact_factor=0,
        total_extension_activities=0,
        students_participated=0,
        beneficiaries_reached=0,
        extension_by_type={},
        total_consultancies=0,
        consultancy_revenue=0,
        hackathons_conducted=0,
        completion_percentage=0,
        pending_items=[]
    )


# --- Criterion 3 Report Generation ---

@router.post("/criterion3/generate-report", response_model=Criterion3ReportResponse, tags=["Criterion 3: Reports"])
async def generate_criterion3_report(request: Criterion3ReportRequest, db: Session = Depends(get_db)):
    """Generate Criterion 3 report in Word/PDF format."""
    try:
        # Import document generator
        from app.utils.document_generator import document_generator

        # Fetch all data
        projects_query = db.query(ResearchProject)
        pub_query = db.query(Publication)
        patent_query = db.query(Patent)
        startup_query = db.query(Startup)
        cell_query = db.query(InnovationCell)
        hack_query = db.query(Hackathon)
        ext_query = db.query(ExtensionActivity)
        cons_query = db.query(Consultancy)
        fund_query = db.query(ResearchFunding)

        if request.academic_year:
            projects_query = projects_query.filter(ResearchProject.academic_year == request.academic_year)
            cell_query = cell_query.filter(InnovationCell.academic_year == request.academic_year)
            hack_query = hack_query.filter(Hackathon.academic_year == request.academic_year)
            ext_query = ext_query.filter(ExtensionActivity.academic_year == request.academic_year)
            cons_query = cons_query.filter(Consultancy.academic_year == request.academic_year)

        if request.department:
            projects_query = projects_query.filter(ResearchProject.department == request.department)
            pub_query = pub_query.filter(Publication.department == request.department)
            patent_query = patent_query.filter(Patent.department == request.department)
            startup_query = startup_query.filter(Startup.department == request.department)
            hack_query = hack_query.filter(Hackathon.department == request.department)
            ext_query = ext_query.filter(ExtensionActivity.department == request.department)
            cons_query = cons_query.filter(Consultancy.department == request.department)
            fund_query = fund_query.filter(ResearchFunding.department == request.department)

        projects = projects_query.all()
        publications = pub_query.all()
        patents = patent_query.all()
        startups = startup_query.all()
        cells = cell_query.all()
        hackathons = hack_query.all()
        activities = ext_query.all()
        consultancies = cons_query.all()
        funding = fund_query.all()

        # Prepare report content
        sections = request.include_sections or ["3.1", "3.2", "3.3", "3.4", "3.5"]

        report_content = {
            "title": f"NAAC Criterion 3: Research, Innovations and Extension - {request.institution_name}",
            "academic_year": request.academic_year,
            "generated_at": datetime.utcnow().isoformat(),
            "sections": {}
        }

        if "3.1" in sections:
            total_funding_amount = sum(f.sanctioned_amount or 0 for f in funding)
            report_content["sections"]["3.1"] = {
                "title": "Resource Mobilization for Research",
                "total_projects": len(projects),
                "ongoing_projects": sum(1 for p in projects if p.status == ResearchProjectStatusEnum.ONGOING),
                "completed_projects": sum(1 for p in projects if p.status == ResearchProjectStatusEnum.COMPLETED),
                "total_funding_grants": len(funding),
                "total_funding_amount": total_funding_amount,
                "funding_by_agency": {}
            }
            for f in funding:
                agency = f.funding_agency.value if f.funding_agency else "other"
                if agency not in report_content["sections"]["3.1"]["funding_by_agency"]:
                    report_content["sections"]["3.1"]["funding_by_agency"][agency] = {"count": 0, "amount": 0}
                report_content["sections"]["3.1"]["funding_by_agency"][agency]["count"] += 1
                report_content["sections"]["3.1"]["funding_by_agency"][agency]["amount"] += f.sanctioned_amount or 0

        if "3.2" in sections:
            report_content["sections"]["3.2"] = {
                "title": "Innovation Ecosystem",
                "total_patents": len(patents),
                "filed_patents": sum(1 for p in patents if p.status == PatentStatusEnum.FILED),
                "granted_patents": sum(1 for p in patents if p.status == PatentStatusEnum.GRANTED),
                "total_startups": len(startups),
                "dpiit_recognized": sum(1 for s in startups if s.dpiit_recognized),
                "innovation_cells": len(cells),
                "hackathons_conducted": len(hackathons),
                "hackathon_participants": sum(h.participants_count or 0 for h in hackathons)
            }

        if "3.3" in sections:
            report_content["sections"]["3.3"] = {
                "title": "Research Publications",
                "total_publications": len(publications),
                "journal_international": sum(1 for p in publications if p.publication_type == PublicationTypeEnum.JOURNAL_INTERNATIONAL),
                "journal_national": sum(1 for p in publications if p.publication_type == PublicationTypeEnum.JOURNAL_NATIONAL),
                "conference_international": sum(1 for p in publications if p.publication_type == PublicationTypeEnum.CONFERENCE_INTERNATIONAL),
                "conference_national": sum(1 for p in publications if p.publication_type == PublicationTypeEnum.CONFERENCE_NATIONAL),
                "books": sum(1 for p in publications if p.publication_type == PublicationTypeEnum.BOOK),
                "book_chapters": sum(1 for p in publications if p.publication_type == PublicationTypeEnum.BOOK_CHAPTER),
                "scopus_indexed": sum(1 for p in publications if p.indexing == PublicationIndexingEnum.SCOPUS),
                "wos_indexed": sum(1 for p in publications if p.indexing == PublicationIndexingEnum.WEB_OF_SCIENCE),
                "ugc_care": sum(1 for p in publications if p.indexing == PublicationIndexingEnum.UGC_CARE),
                "total_citations": sum(p.citations or 0 for p in publications)
            }

        if "3.4" in sections:
            report_content["sections"]["3.4"] = {
                "title": "Extension Activities",
                "total_activities": len(activities),
                "nss_activities": sum(1 for a in activities if a.activity_type == ExtensionTypeEnum.NSS),
                "ncc_activities": sum(1 for a in activities if a.activity_type == ExtensionTypeEnum.NCC),
                "community_service": sum(1 for a in activities if a.activity_type == ExtensionTypeEnum.COMMUNITY_SERVICE),
                "total_beneficiaries": sum(a.beneficiaries_count or 0 for a in activities),
                "students_participated": sum(a.students_participated or 0 for a in activities),
                "villages_adopted": len(set(a.village_adopted for a in activities if a.village_adopted))
            }

        if "3.5" in sections:
            report_content["sections"]["3.5"] = {
                "title": "Collaboration",
                "total_consultancies": len(consultancies),
                "consultancy_revenue": sum(c.consultancy_amount or 0 for c in consultancies),
                "completed_consultancies": sum(1 for c in consultancies if c.status == ResearchProjectStatusEnum.COMPLETED),
                "ongoing_consultancies": sum(1 for c in consultancies if c.status == ResearchProjectStatusEnum.ONGOING)
            }

        if request.include_analytics:
            report_content["analytics"] = {
                "research_output_trend": "Computed based on year-over-year data",
                "top_departments": [],
                "funding_utilization": round(sum(f.utilized_amount or 0 for f in funding) / max(sum(f.sanctioned_amount or 0 for f in funding), 1) * 100, 2)
            }

        # Generate document
        if request.format == "docx":
            doc_bytes = document_generator.generate_accreditation_docx(
                content=report_content,
                title=f"Criterion 3 Report - {request.academic_year}"
            )
            file_ext = "docx"
        else:
            doc_bytes = document_generator.generate_accreditation_pdf(
                content=report_content,
                title=f"Criterion 3 Report - {request.academic_year}"
            )
            file_ext = "pdf"

        # Save report
        report_dir = "uploads/criterion3/reports"
        os.makedirs(report_dir, exist_ok=True)
        report_path = f"{report_dir}/criterion3_report_{request.academic_year.replace('-', '_')}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.{file_ext}"

        with open(report_path, "wb") as f:
            f.write(doc_bytes)

        return Criterion3ReportResponse(
            success=True,
            report_path=report_path,
            sections_included=sections,
            generated_at=datetime.utcnow(),
            metadata={"file_size": len(doc_bytes), "format": request.format}
        )
    except Exception as e:
        logger.error(f"Error generating Criterion 3 report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DVV CLARIFICATIONS ====================

class DVVResponseRequest(BaseModel):
    """Request for generating DVV clarification response"""
    institution_name: str = Field(..., min_length=1)
    metric_number: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    original_data: Optional[str] = None
    dvv_query: str = Field(..., min_length=10)
    query_type: Optional[str] = None
    academic_year: Optional[str] = None


class DVVResponseResponse(BaseModel):
    """Response for DVV clarification generation"""
    success: bool
    metric_number: str
    clarification: str
    suggested_evidence: List[str]
    generated_at: datetime
    ai_generated: bool = True


# DVV Query Response Templates
DVV_RESPONSE_TEMPLATES = {
    "Data mismatch between years": """With reference to the DVV query on Metric {metric_number}, we would like to clarify that the data submitted is accurate and verified as per institutional records.

The apparent mismatch is due to the following reasons:
1. [Specify reason for variation - e.g., change in admission policy, new programs started, etc.]
2. [Additional context if applicable]

Year-wise breakup of data:
- Year 1 (20XX-XX): [Data]
- Year 2 (20XX-XX): [Data]
- Year 3 (20XX-XX): [Data]
- Year 4 (20XX-XX): [Data]
- Year 5 (20XX-XX): [Data]

The data has been verified by the respective departments and validated by IQAC. Supporting documents including registers, certificates, and consolidated lists are attached for verification.

We trust this clarifies the query raised by the DVV team.""",

    "Supporting documents not clear": """In response to the DVV observation regarding Metric {metric_number}, we are providing clearer and more comprehensive supporting documents.

The original submission has been reviewed, and we now attach the following documents with improved clarity:

1. [Document Name] - [Brief description of what it proves]
2. [Document Name] - [Brief description of what it proves]
3. [Document Name] - [Brief description of what it proves]

All documents have been:
- Scanned at higher resolution for better readability
- Properly indexed and labeled
- Authenticated with institution seal and signatures

These documents clearly establish and validate the data claimed in the SSR for this metric.""",

    "Calculation error in metrics": """We acknowledge the observation on Metric {metric_number} regarding the calculation methodology.

After reviewing our calculations as per NAAC guidelines, we provide the following clarification:

Original Data Submitted: {original_data}

Calculation Methodology:
- Numerator: [Explain what constitutes the numerator]
- Denominator: [Explain what constitutes the denominator]
- Formula applied: [State the formula as per NAAC guidelines]

Recalculated Value: [If applicable, provide corrected value]

The detailed calculation worksheet following NAAC methodology is attached as Annexure. The data sources include:
1. [Source 1 - e.g., Examination section records]
2. [Source 2 - e.g., Academic office data]
3. [Source 3 - e.g., Department registers]

We confirm the calculation adheres to NAAC DVV guidelines.""",

    "Missing evidence/proof": """In response to the DVV query for Metric {metric_number} regarding missing evidence, we are now providing comprehensive documentary proof.

The following documents are attached to substantiate the data claimed:

1. [Primary Evidence Document] - Certified copy with authentication
2. [Supporting Register/Record] - Relevant pages highlighted
3. [Consolidated List] - Department-wise/Year-wise as applicable
4. [Third-party verification] - If applicable (e.g., university records, funding agency letters)

Document Index:
- Annexure {metric_number}.1: [Description]
- Annexure {metric_number}.2: [Description]
- Annexure {metric_number}.3: [Description]

All documents bear institutional seal and authorized signatures. We trust these documents adequately address the DVV observation.""",

    "Format not as per NAAC guidelines": """We have reformatted the data for Metric {metric_number} strictly as per NAAC DVV guidelines.

The revised submission includes:

1. Data presented in the prescribed NAAC template format
2. Year-wise segregation as required
3. All mandatory fields completed
4. Required certifications and declarations included

Changes made from original submission:
- [Specific change 1]
- [Specific change 2]
- [Specific change 3]

The reformatted documents are attached. We have ensured compliance with the latest NAAC DVV data template requirements.""",

    "Incomplete data submission": """In response to the DVV observation on incomplete data for Metric {metric_number}, we are providing the complete dataset.

Original Submission Gap: [Describe what was missing]

Complete Data Now Provided:
{original_data}

Additional Information Added:
1. [Additional data point 1]
2. [Additional data point 2]
3. [Additional data point 3]

The complete dataset covers all parameters required under this metric as per NAAC guidelines. Supporting evidence for the additional data is also attached.""",

    "Clarification on methodology": """With reference to the query on methodology adopted for Metric {metric_number}, we provide the following clarification:

Methodology Adopted:
1. Data Collection: [Describe how data was collected]
2. Verification Process: [Describe verification steps]
3. Calculation Method: [Describe calculation approach]
4. Quality Check: [Describe validation process]

This methodology aligns with NAAC guidelines as specified in:
- [Reference to NAAC manual/guideline section]
- [Any clarifications issued by NAAC]

The process was overseen by IQAC and validated by respective department heads. Documentation of the methodology is attached for reference.""",

    "Year-wise breakup required": """As requested, we provide the year-wise breakup for Metric {metric_number}:

Year-wise Data:

Academic Year 20XX-XX (Year 1):
- [Parameter]: [Value]
- [Supporting Document]: Annexure {metric_number}.Y1

Academic Year 20XX-XX (Year 2):
- [Parameter]: [Value]
- [Supporting Document]: Annexure {metric_number}.Y2

Academic Year 20XX-XX (Year 3):
- [Parameter]: [Value]
- [Supporting Document]: Annexure {metric_number}.Y3

Academic Year 20XX-XX (Year 4):
- [Parameter]: [Value]
- [Supporting Document]: Annexure {metric_number}.Y4

Academic Year 20XX-XX (Year 5):
- [Parameter]: [Value]
- [Supporting Document]: Annexure {metric_number}.Y5

Consolidated Total: [Sum/Average as applicable]

Year-wise supporting documents are attached with proper indexing.""",

    "Additional proof needed": """In response to the DVV requirement for additional proof for Metric {metric_number}, we submit the following supplementary documents:

Additional Evidence Provided:

1. [Document Type]: [Description and relevance]
   - Source: [Where this document comes from]
   - Authentication: [How it's verified]

2. [Document Type]: [Description and relevance]
   - Source: [Where this document comes from]
   - Authentication: [How it's verified]

3. [Document Type]: [Description and relevance]
   - Source: [Where this document comes from]
   - Authentication: [How it's verified]

These additional documents complement the original submission and provide comprehensive proof for the data claimed. All documents bear necessary authentication.""",

    "Other": """With reference to DVV query on Metric {metric_number}:

DVV Query/Observation:
{dvv_query}

Clarification Response:

We respectfully submit the following clarification in response to the above observation:

1. Background/Context:
[Provide relevant context for the data/metric]

2. Clarification:
[Detailed response addressing the specific query]

3. Supporting Evidence:
[List of documents being provided]

4. Additional Information:
[Any other relevant details]

We trust this clarification adequately addresses the DVV observation. We remain available for any further clarification required.

Submitted by: IQAC Coordinator
Verified by: Head of Institution"""
}


@router.post("/dvv/generate-response", response_model=DVVResponseResponse, tags=["DVV Clarifications"])
async def generate_dvv_response(request: DVVResponseRequest):
    """
    Generate AI-powered DVV clarification response for a specific metric.

    This endpoint provides template-based responses that can be customized
    for specific DVV queries received from NAAC.
    """
    try:
        # Get appropriate template based on query type
        query_type = request.query_type or "Other"
        template = DVV_RESPONSE_TEMPLATES.get(query_type, DVV_RESPONSE_TEMPLATES["Other"])

        # Format the template with provided data
        clarification = template.format(
            metric_number=request.metric_number,
            original_data=request.original_data or "[Original data to be specified]",
            dvv_query=request.dvv_query
        )

        # Generate suggested evidence based on metric number
        criterion = request.metric_number.split('.')[0]
        suggested_evidence = generate_suggested_evidence(criterion, request.metric_number, query_type)

        return DVVResponseResponse(
            success=True,
            metric_number=request.metric_number,
            clarification=clarification,
            suggested_evidence=suggested_evidence,
            generated_at=datetime.utcnow(),
            ai_generated=True
        )

    except Exception as e:
        logger.error(f"Error generating DVV response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_suggested_evidence(criterion: str, metric_number: str, query_type: str) -> List[str]:
    """Generate suggested evidence list based on criterion and query type"""

    base_evidence = [
        f"Annexure {metric_number}.1 - Consolidated data sheet with institutional seal",
        f"Annexure {metric_number}.2 - Year-wise breakup document",
        f"Annexure {metric_number}.3 - Supporting registers/records (relevant pages)",
    ]

    criterion_specific = {
        "1": [
            "Curriculum revision documents with BoS approval",
            "Feedback collection forms and analysis reports",
            "MoU copies with industry partners",
            "Value-added course completion certificates",
        ],
        "2": [
            "Student enrollment data from university portal",
            "Result analysis sheets with pass percentages",
            "Teacher qualification certificates",
            "ICT-enabled classroom usage logs",
        ],
        "3": [
            "Research project sanction letters",
            "Publication copies with ISSN/ISBN",
            "Patent filing/grant certificates",
            "Extension activity photographs and reports",
        ],
        "4": [
            "Infrastructure utilization records",
            "Library accession registers",
            "IT infrastructure inventory",
            "Maintenance and AMC records",
        ],
        "5": [
            "Scholarship disbursement records",
            "Placement offer letters and data",
            "Career counseling session records",
            "Alumni association meeting minutes",
        ],
        "6": [
            "Governing body meeting minutes",
            "IQAC meeting minutes and ATRs",
            "Strategic plan documents",
            "Financial audit reports",
        ],
        "7": [
            "Best practices documentation",
            "Green audit reports",
            "Gender sensitization program records",
            "Divyangjan facilities documentation",
        ],
    }

    evidence = base_evidence.copy()
    if criterion in criterion_specific:
        evidence.extend(criterion_specific[criterion][:2])

    # Add query-type specific evidence
    if query_type == "Calculation error in metrics":
        evidence.append("Detailed calculation worksheet with formula")
    elif query_type == "Data mismatch between years":
        evidence.append("Year-wise comparative statement")
    elif query_type == "Missing evidence/proof":
        evidence.append("Third-party verification documents (if applicable)")

    return evidence


@router.get("/dvv/templates", tags=["DVV Clarifications"])
async def get_dvv_templates():
    """
    Get all available DVV response templates.

    Returns template types and their descriptions for reference.
    """
    return {
        "success": True,
        "templates": [
            {"type": key, "description": key, "preview": value[:200] + "..."}
            for key, value in DVV_RESPONSE_TEMPLATES.items()
        ],
        "total_templates": len(DVV_RESPONSE_TEMPLATES)
    }


@router.get("/dvv/metrics/{criterion}", tags=["DVV Clarifications"])
async def get_criterion_metrics(criterion: int = Path(..., ge=1, le=7)):
    """
    Get all metrics for a specific NAAC criterion.

    Returns metric numbers and their descriptions for the specified criterion.
    """
    # Define metrics for each criterion
    CRITERION_METRICS = {
        1: {
            "1.1.1": "Curricula developed and implemented with industry/employer/professional bodies",
            "1.1.2": "Percentage of programmes with CBCS/Elective/Learning outcomes",
            "1.2.1": "Percentage of new courses introduced across programmes",
            "1.2.2": "Percentage of programmes with focus on employability/entrepreneurship",
            "1.3.1": "Value-added courses with skills certification",
            "1.3.2": "Number of students enrolled in value-added courses",
            "1.4.1": "Structured feedback system for curriculum",
            "1.4.2": "Feedback processes for curriculum design",
        },
        2: {
            "2.1.1": "Average enrolment percentage",
            "2.1.2": "Average percentage of seats filled against reserved categories",
            "2.2.1": "Student-full time teacher ratio",
            "2.3.1": "Student centric methods for enhancing learning",
            "2.4.1": "Percentage of full time teachers against sanctioned posts",
            "2.4.2": "Percentage of teachers with NET/SET/Ph.D.",
            "2.5.1": "Average percentage of students scoring above minimum marks",
            "2.6.1": "Programme outcomes and course outcomes stated and communicated",
            "2.6.2": "Attainment of POs and COs",
            "2.6.3": "Pass percentage of students",
        },
        3: {
            "3.1.1": "Research facilities and promotion of research culture",
            "3.2.1": "Grants received for research projects from government and non-government",
            "3.2.2": "Teachers with research projects and grants",
            "3.3.1": "Research papers in UGC-CARE/Scopus/Web of Science",
            "3.3.2": "Books and chapters in edited volumes",
            "3.4.1": "Patents filed/published/granted",
            "3.4.2": "Ph.D.s awarded per teacher",
            "3.4.3": "Awards/recognitions for research/innovation",
            "3.5.1": "Consultancy revenue generated",
            "3.6.1": "Extension activities conducted",
            "3.7.1": "Collaborative activities with other institutions/industries",
        },
        4: {
            "4.1.1": "Physical facilities for teaching-learning",
            "4.1.2": "Facilities for cultural activities and sports",
            "4.2.1": "Library automation and facilities",
            "4.3.1": "IT facilities including Wi-Fi and computing resources",
            "4.3.2": "Student-computer ratio",
            "4.4.1": "Expenditure on infrastructure augmentation",
        },
        5: {
            "5.1.1": "Students benefited by scholarships and freeships",
            "5.1.2": "Capability enhancement and development schemes",
            "5.1.3": "Career counseling and guidance activities",
            "5.2.1": "Students qualifying in national examinations",
            "5.2.2": "Percentage of placement and higher education",
            "5.3.1": "Awards/medals in sports and cultural activities",
            "5.3.2": "Student participation in activities",
            "5.4.1": "Alumni association contribution and engagement",
        },
        6: {
            "6.1.1": "Effective governance and institutional vision",
            "6.2.1": "Strategic development and deployment",
            "6.2.2": "Organizational structure and governance",
            "6.3.1": "Faculty empowerment strategies",
            "6.3.2": "Professional development programmes for faculty",
            "6.4.1": "Resource mobilization through funds/grants",
            "6.5.1": "Internal Quality Assurance System",
            "6.5.2": "Institutionalized quality assurance strategies",
        },
        7: {
            "7.1.1": "Gender equity measures",
            "7.1.2": "Environmental and energy conservation initiatives",
            "7.1.3": "Facilities for differently-abled persons",
            "7.2.1": "Best practices adopted by the institution",
            "7.3.1": "Institutional distinctiveness",
        },
    }

    if criterion not in CRITERION_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid criterion number: {criterion}")

    return {
        "success": True,
        "criterion": criterion,
        "criterion_name": [
            "Curricular Aspects",
            "Teaching-Learning and Evaluation",
            "Research, Innovations and Extension",
            "Infrastructure and Learning Resources",
            "Student Support and Progression",
            "Governance, Leadership and Management",
            "Institutional Values and Best Practices"
        ][criterion - 1],
        "metrics": CRITERION_METRICS[criterion],
        "total_metrics": len(CRITERION_METRICS[criterion])
    }
