"""
NAAC/NBA Accreditation API Endpoints
Generates accreditation-compliant documents for Indian colleges.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging

from app.modules.agents.naac_nba_agent import naac_nba_agent, AccreditationDocType
from app.modules.agents.base_agent import AgentContext

logger = logging.getLogger(__name__)

router = APIRouter()


class CourseInfo(BaseModel):
    """Course information for accreditation documents"""
    course_name: str = Field(..., description="Name of the course", example="Software Engineering Project")
    course_code: str = Field(..., description="Course code", example="CS601")
    department: str = Field(..., description="Department name", example="Computer Science and Engineering")
    semester: int = Field(..., description="Semester number", ge=1, le=8, example=6)
    credits: int = Field(..., description="Course credits", ge=1, le=6, example=4)
    program_name: Optional[str] = Field(None, description="Program name", example="B.Tech Computer Science")
    university: Optional[str] = Field(None, description="University name", example="JNTU Hyderabad")


class AccreditationRequest(BaseModel):
    """Request for generating accreditation documents"""
    project_description: str = Field(
        ...,
        description="Description of the project/course for which to generate documents",
        example="E-commerce web application with React frontend, Node.js backend, and MongoDB database"
    )
    course_info: CourseInfo
    doc_types: Optional[List[str]] = Field(
        None,
        description="Specific document types to generate. If not provided, generates all.",
        example=["course_outcomes", "co_po_mapping", "rubrics"]
    )


class CourseOutcomesRequest(BaseModel):
    """Request for generating only Course Outcomes"""
    project_description: str
    course_info: CourseInfo
    num_outcomes: int = Field(default=6, ge=4, le=8, description="Number of COs to generate")


class COPOMappingRequest(BaseModel):
    """Request for generating CO-PO mapping"""
    course_outcomes: List[str] = Field(
        ...,
        description="List of course outcomes to map",
        example=["CO1: Analyze software requirements", "CO2: Design software architecture"]
    )
    course_info: CourseInfo


class RubricsRequest(BaseModel):
    """Request for generating assessment rubrics"""
    project_description: str
    course_info: CourseInfo
    assessment_type: str = Field(
        default="project",
        description="Type of assessment",
        example="project"
    )
    criteria_count: int = Field(default=5, ge=3, le=8, description="Number of rubric criteria")


class AccreditationResponse(BaseModel):
    """Response containing generated accreditation documents"""
    success: bool
    documents: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/generate", response_model=AccreditationResponse, tags=["Accreditation"])
async def generate_accreditation_documents(request: AccreditationRequest):
    """
    Generate complete NAAC/NBA accreditation documents.

    Generates:
    - Course Outcomes (COs) with Bloom's Taxonomy levels
    - CO-PO Mapping Matrix with justifications
    - Program Specific Outcomes (PSOs)
    - Assessment Rubrics
    - Attainment Calculation Templates

    Compliant with NAAC, NBA, AICTE, and UGC guidelines.
    """
    try:
        logger.info(f"Generating accreditation documents for: {request.course_info.course_code}")

        # Create agent context
        context = AgentContext(
            user_request=request.project_description,
            project_id=f"accred-{request.course_info.course_code}",
            metadata={
                "course_name": request.course_info.course_name,
                "course_code": request.course_info.course_code,
                "department": request.course_info.department,
                "semester": request.course_info.semester,
                "credits": request.course_info.credits,
                "program_name": request.course_info.program_name,
                "university": request.course_info.university,
                "doc_types": request.doc_types
            }
        )

        # Generate documents
        result = await naac_nba_agent.process(context)

        if not result.get("success", True):
            raise HTTPException(status_code=500, detail=result.get("error", "Generation failed"))

        return AccreditationResponse(
            success=True,
            documents=result.get("content", {}),
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating accreditation documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/course-outcomes", response_model=AccreditationResponse, tags=["Accreditation"])
async def generate_course_outcomes(request: CourseOutcomesRequest):
    """
    Generate Course Outcomes (COs) only.

    Each CO includes:
    - Statement with action verb
    - Bloom's Taxonomy level (L1-L6)
    - Suggested assessment methods
    """
    try:
        context = AgentContext(
            user_request=f"""Generate {request.num_outcomes} Course Outcomes for:

Project: {request.project_description}
Course: {request.course_info.course_code} - {request.course_info.course_name}
Department: {request.course_info.department}
Semester: {request.course_info.semester}

Requirements:
- Each CO must start with an action verb from Bloom's Taxonomy
- Cover cognitive levels from L1 to L6
- Make COs specific, measurable, and assessable
- Align with project objectives

Output as JSON array of course outcomes.""",
            project_id=f"co-{request.course_info.course_code}",
            metadata={
                "doc_type": AccreditationDocType.COURSE_OUTCOMES.value,
                **request.course_info.model_dump()
            }
        )

        result = await naac_nba_agent.generate_course_outcomes(context)

        return AccreditationResponse(
            success=True,
            documents={"course_outcomes": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating course outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/co-po-mapping", response_model=AccreditationResponse, tags=["Accreditation"])
async def generate_co_po_mapping(request: COPOMappingRequest):
    """
    Generate CO-PO Mapping Matrix.

    Maps Course Outcomes to the 12 NBA Program Outcomes with:
    - Correlation levels (1-3)
    - Justifications for significant mappings
    - Average attainment calculations
    """
    try:
        context = AgentContext(
            user_request="Generate CO-PO mapping matrix",
            project_id=f"copo-{request.course_info.course_code}",
            metadata={
                "doc_type": AccreditationDocType.CO_PO_MAPPING.value,
                **request.course_info.model_dump()
            }
        )

        result = await naac_nba_agent.generate_co_po_mapping(context, request.course_outcomes)

        return AccreditationResponse(
            success=True,
            documents={"co_po_mapping": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating CO-PO mapping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rubrics", response_model=AccreditationResponse, tags=["Accreditation"])
async def generate_rubrics(request: RubricsRequest):
    """
    Generate Assessment Rubrics.

    Creates detailed rubrics with:
    - Multiple assessment criteria
    - 4 performance levels (Excellent, Good, Satisfactory, Needs Improvement)
    - Clear descriptors for each level
    - Weightage distribution
    """
    try:
        context = AgentContext(
            user_request=request.project_description,
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
            documents={"rubrics": result.get("content", {})},
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Error generating rubrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/program-outcomes", tags=["Accreditation"])
async def get_program_outcomes():
    """
    Get the standard 12 NBA Program Outcomes.

    Returns the official NBA PO definitions for reference.
    """
    return {
        "program_outcomes": [
            {
                "id": "PO1",
                "name": "Engineering Knowledge",
                "description": "Apply the knowledge of mathematics, science, engineering fundamentals, and an engineering specialization to the solution of complex engineering problems."
            },
            {
                "id": "PO2",
                "name": "Problem Analysis",
                "description": "Identify, formulate, review research literature, and analyze complex engineering problems reaching substantiated conclusions using first principles of mathematics, natural sciences, and engineering sciences."
            },
            {
                "id": "PO3",
                "name": "Design/Development of Solutions",
                "description": "Design solutions for complex engineering problems and design system components or processes that meet the specified needs with appropriate consideration for public health and safety, and cultural, societal, and environmental considerations."
            },
            {
                "id": "PO4",
                "name": "Conduct Investigations of Complex Problems",
                "description": "Use research-based knowledge and research methods including design of experiments, analysis and interpretation of data, and synthesis of the information to provide valid conclusions."
            },
            {
                "id": "PO5",
                "name": "Modern Tool Usage",
                "description": "Create, select, and apply appropriate techniques, resources, and modern engineering and IT tools including prediction and modeling to complex engineering activities with an understanding of the limitations."
            },
            {
                "id": "PO6",
                "name": "The Engineer and Society",
                "description": "Apply reasoning informed by the contextual knowledge to assess societal, health, safety, legal, and cultural issues and the consequent responsibilities relevant to the professional engineering practice."
            },
            {
                "id": "PO7",
                "name": "Environment and Sustainability",
                "description": "Understand the impact of the professional engineering solutions in societal and environmental contexts, and demonstrate the knowledge of, and need for sustainable development."
            },
            {
                "id": "PO8",
                "name": "Ethics",
                "description": "Apply ethical principles and commit to professional ethics and responsibilities and norms of the engineering practice."
            },
            {
                "id": "PO9",
                "name": "Individual and Team Work",
                "description": "Function effectively as an individual, and as a member or leader in diverse teams, and in multidisciplinary settings."
            },
            {
                "id": "PO10",
                "name": "Communication",
                "description": "Communicate effectively on complex engineering activities with the engineering community and with society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations, and give and receive clear instructions."
            },
            {
                "id": "PO11",
                "name": "Project Management and Finance",
                "description": "Demonstrate knowledge and understanding of the engineering and management principles and apply these to one's own work, as a member and leader in a team, to manage projects and in multidisciplinary environments."
            },
            {
                "id": "PO12",
                "name": "Life-long Learning",
                "description": "Recognize the need for, and have the preparation and ability to engage in independent and life-long learning in the broadest context of technological change."
            }
        ],
        "source": "NBA (National Board of Accreditation) - India",
        "compliance": ["NAAC", "NBA", "AICTE", "Washington Accord"]
    }


@router.get("/blooms-taxonomy", tags=["Accreditation"])
async def get_blooms_taxonomy():
    """
    Get Bloom's Taxonomy levels and action verbs.

    Returns cognitive domain levels with appropriate action verbs for CO writing.
    """
    return {
        "taxonomy": {
            "L1": {
                "name": "Remember",
                "description": "Recall facts and basic concepts",
                "action_verbs": ["Define", "List", "State", "Identify", "Recall", "Name", "Recognize", "Label", "Match", "Select", "Memorize"]
            },
            "L2": {
                "name": "Understand",
                "description": "Explain ideas or concepts",
                "action_verbs": ["Describe", "Explain", "Summarize", "Classify", "Compare", "Interpret", "Discuss", "Distinguish", "Predict", "Paraphrase", "Translate"]
            },
            "L3": {
                "name": "Apply",
                "description": "Use information in new situations",
                "action_verbs": ["Apply", "Demonstrate", "Implement", "Solve", "Use", "Execute", "Compute", "Operate", "Practice", "Calculate", "Illustrate"]
            },
            "L4": {
                "name": "Analyze",
                "description": "Draw connections among ideas",
                "action_verbs": ["Analyze", "Differentiate", "Examine", "Compare", "Contrast", "Investigate", "Categorize", "Distinguish", "Test", "Diagnose", "Deconstruct"]
            },
            "L5": {
                "name": "Evaluate",
                "description": "Justify a stand or decision",
                "action_verbs": ["Evaluate", "Justify", "Critique", "Assess", "Judge", "Recommend", "Defend", "Prioritize", "Rate", "Validate", "Argue"]
            },
            "L6": {
                "name": "Create",
                "description": "Produce new or original work",
                "action_verbs": ["Design", "Develop", "Create", "Construct", "Produce", "Formulate", "Build", "Compose", "Plan", "Propose", "Invent"]
            }
        },
        "domain": "Cognitive",
        "source": "Bloom's Revised Taxonomy (Anderson & Krathwohl, 2001)"
    }
