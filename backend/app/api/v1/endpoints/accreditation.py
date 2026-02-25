"""
NAAC/NBA Accreditation API Endpoints - Complete 7 Criteria Support
Generates accreditation-compliant documents for Indian colleges.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.modules.agents.naac_nba_agent import (
    naac_nba_agent,
    NAACCriterion,
    AccreditationDocType
)
from app.modules.agents.base_agent import AgentContext

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
