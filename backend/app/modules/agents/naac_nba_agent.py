"""
NAAC/NBA Accreditation Agent - Complete 7 Criteria Support
Generates accreditation-compliant documents for Indian colleges.

Supports ALL 7 NAAC Criteria:
1. Curricular Aspects (150 marks)
2. Teaching-Learning and Evaluation (200 marks)
3. Research, Innovations and Extension (150 marks)
4. Infrastructure and Learning Resources (100 marks)
5. Student Support and Progression (100 marks)
6. Governance, Leadership and Management (100 marks)
7. Institutional Values and Best Practices (100 marks)

Also supports NBA accreditation for engineering programs.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

from app.modules.agents.base_agent import BaseAgent, AgentContext

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


class NAACCriterion(str, Enum):
    """NAAC 7 Criteria"""
    CRITERION_1 = "curricular_aspects"
    CRITERION_2 = "teaching_learning_evaluation"
    CRITERION_3 = "research_innovations_extension"
    CRITERION_4 = "infrastructure_learning_resources"
    CRITERION_5 = "student_support_progression"
    CRITERION_6 = "governance_leadership_management"
    CRITERION_7 = "institutional_values_best_practices"


class AccreditationDocType(str, Enum):
    """Types of accreditation documents"""
    # Criterion 1: Curricular Aspects
    CURRICULUM_DESIGN = "curriculum_design"
    ACADEMIC_FLEXIBILITY = "academic_flexibility"
    CURRICULUM_ENRICHMENT = "curriculum_enrichment"
    FEEDBACK_SYSTEM = "feedback_system"

    # Criterion 2: Teaching-Learning (OBE)
    COURSE_OUTCOMES = "course_outcomes"
    PROGRAM_OUTCOMES = "program_outcomes"
    CO_PO_MAPPING = "co_po_mapping"
    BLOOMS_TAXONOMY = "blooms_taxonomy"
    RUBRICS = "rubrics"
    ATTAINMENT = "attainment"
    STUDENT_CENTRIC_METHODS = "student_centric_methods"
    EVALUATION_REFORMS = "evaluation_reforms"

    # Criterion 3: Research
    RESEARCH_PROMOTION = "research_promotion"
    RESOURCE_MOBILIZATION = "resource_mobilization"
    INNOVATION_ECOSYSTEM = "innovation_ecosystem"
    RESEARCH_PUBLICATIONS = "research_publications"
    CONSULTANCY = "consultancy"
    EXTENSION_ACTIVITIES = "extension_activities"
    COLLABORATION = "collaboration"

    # Criterion 4: Infrastructure
    PHYSICAL_FACILITIES = "physical_facilities"
    LIBRARY_RESOURCES = "library_resources"
    IT_INFRASTRUCTURE = "it_infrastructure"
    MAINTENANCE = "maintenance"

    # Criterion 5: Student Support
    SCHOLARSHIPS = "scholarships"
    CAPABILITY_ENHANCEMENT = "capability_enhancement"
    STUDENT_PROGRESSION = "student_progression"
    ALUMNI_ENGAGEMENT = "alumni_engagement"

    # Criterion 6: Governance
    VISION_MISSION = "vision_mission"
    STRATEGIC_PLAN = "strategic_plan"
    FACULTY_EMPOWERMENT = "faculty_empowerment"
    FINANCIAL_MANAGEMENT = "financial_management"
    IQAC = "iqac"

    # Criterion 7: Values & Best Practices
    GENDER_EQUITY = "gender_equity"
    ENVIRONMENTAL_CONSCIOUSNESS = "environmental_consciousness"
    INCLUSIVENESS = "inclusiveness"
    BEST_PRACTICES = "best_practices"
    INSTITUTIONAL_DISTINCTIVENESS = "institutional_distinctiveness"

    # Complete Reports
    FULL_SSR = "full_ssr"  # Self Study Report
    CRITERION_REPORT = "criterion_report"
    DVV_CLARIFICATION = "dvv_clarification"  # Data Validation & Verification


@dataclass
class InstitutionProfile:
    """Institution details for NAAC documentation"""
    name: str
    type: str  # University/Autonomous/Affiliated
    location: str
    state: str
    established_year: int
    naac_cycle: int = 1  # 1st, 2nd, 3rd cycle
    previous_grade: Optional[str] = None
    affiliated_university: Optional[str] = None
    programs_offered: List[str] = field(default_factory=list)
    total_students: int = 0
    total_faculty: int = 0


@dataclass
class AccreditationContext:
    """Context for accreditation document generation"""
    institution: Optional[InstitutionProfile] = None
    course_name: Optional[str] = None
    course_code: Optional[str] = None
    department: Optional[str] = None
    semester: Optional[int] = None
    credits: Optional[int] = None
    program_name: Optional[str] = None
    academic_year: str = "2024-25"
    criterion: Optional[NAACCriterion] = None
    doc_type: AccreditationDocType = AccreditationDocType.FULL_SSR


class NAACNBAAgent(BaseAgent):
    """
    Comprehensive NAAC/NBA Accreditation Agent.

    Generates documents for ALL 7 NAAC Criteria:
    - Criterion 1: Curricular Aspects (150 marks)
    - Criterion 2: Teaching-Learning and Evaluation (200 marks)
    - Criterion 3: Research, Innovations and Extension (150 marks)
    - Criterion 4: Infrastructure and Learning Resources (100 marks)
    - Criterion 5: Student Support and Progression (100 marks)
    - Criterion 6: Governance, Leadership and Management (100 marks)
    - Criterion 7: Institutional Values and Best Practices (100 marks)

    Also supports NBA accreditation for engineering programs.
    """

    SYSTEM_PROMPT = """You are an expert in Indian higher education accreditation, specifically:
- NAAC (National Assessment and Accreditation Council)
- NBA (National Board of Accreditation)
- AICTE (All India Council for Technical Education)
- UGC (University Grants Commission)

You have deep knowledge of all 7 NAAC criteria and their key indicators.

## NAAC CRITERIA OVERVIEW (Total: 700 marks)

### CRITERION 1: CURRICULAR ASPECTS (150 marks)
Key Indicators:
1.1 Curricular Planning and Implementation
1.2 Academic Flexibility
1.3 Curriculum Enrichment
1.4 Feedback System

Documents to generate:
- Curriculum development committee minutes
- CBCS/Elective structure documentation
- Value-added course proposals
- Feedback analysis reports (students, alumni, employers, parents)
- Cross-cutting issues integration report

### CRITERION 2: TEACHING-LEARNING AND EVALUATION (200 marks)
Key Indicators:
2.1 Student Enrollment and Profile
2.2 Catering to Student Diversity
2.3 Teaching-Learning Process
2.4 Teacher Quality
2.5 Evaluation Process and Reforms
2.6 Student Performance and Learning Outcomes

Documents to generate:
- Course Outcomes (COs) with Bloom's Taxonomy
- Program Outcomes (POs) - NBA 12 POs
- Program Specific Outcomes (PSOs)
- CO-PO-PSO Mapping with attainment
- Rubrics for all assessments
- Student-centric learning methods
- Mentor-mentee documentation
- Slow learner/Advanced learner programs
- ICT-enabled teaching tools

### CRITERION 3: RESEARCH, INNOVATIONS AND EXTENSION (150 marks)
Key Indicators:
3.1 Promotion of Research and Facilities
3.2 Resource Mobilization for Research
3.3 Innovation Ecosystem
3.4 Research Publications and Awards
3.5 Consultancy
3.6 Extension Activities
3.7 Collaboration

Documents to generate:
- Research policy document
- Seed money/incentive schemes
- Research project proposals
- Publication analysis report
- Patent/IPR documentation
- MoU templates and reports
- Extension activity reports
- Industry collaboration documentation

### CRITERION 4: INFRASTRUCTURE AND LEARNING RESOURCES (100 marks)
Key Indicators:
4.1 Physical Facilities
4.2 Library as a Learning Resource
4.3 IT Infrastructure
4.4 Maintenance of Campus Infrastructure

Documents to generate:
- Infrastructure audit report
- Lab equipment inventory
- Library usage statistics
- IT infrastructure report
- Budget allocation for infrastructure
- Maintenance policy and records

### CRITERION 5: STUDENT SUPPORT AND PROGRESSION (100 marks)
Key Indicators:
5.1 Student Support
5.2 Student Progression
5.3 Student Participation and Activities
5.4 Alumni Engagement

Documents to generate:
- Scholarship/freeships report
- Career counseling documentation
- Placement statistics
- Higher education progression data
- Student awards and recognitions
- Alumni association activities
- Alumni contribution report

### CRITERION 6: GOVERNANCE, LEADERSHIP AND MANAGEMENT (100 marks)
Key Indicators:
6.1 Institutional Vision and Leadership
6.2 Strategy Development and Deployment
6.3 Faculty Empowerment Strategies
6.4 Financial Management and Resource Mobilization
6.5 Internal Quality Assurance System

Documents to generate:
- Vision, Mission, PEOs documentation
- Strategic plan and perspective plan
- Organogram and governance structure
- Faculty development programs
- Performance appraisal system
- Financial audit highlights
- IQAC composition and minutes
- Academic and administrative audit
- Quality initiatives documentation

### CRITERION 7: INSTITUTIONAL VALUES AND BEST PRACTICES (100 marks)
Key Indicators:
7.1 Institutional Values and Social Responsibilities
7.2 Best Practices
7.3 Institutional Distinctiveness

Documents to generate:
- Gender equity initiatives
- Green campus policy
- Environmental audit report
- Energy audit report
- Waste management policy
- Divyangjan facilities report
- Code of conduct
- Best practices documentation (2 practices)
- Institutional distinctiveness document

## NBA SPECIFIC REQUIREMENTS (For Engineering Programs)

### Program Outcomes (POs) - 12 Graduate Attributes:
PO1: Engineering Knowledge
PO2: Problem Analysis
PO3: Design/Development of Solutions
PO4: Conduct Investigations
PO5: Modern Tool Usage
PO6: Engineer and Society
PO7: Environment and Sustainability
PO8: Ethics
PO9: Individual and Team Work
PO10: Communication
PO11: Project Management and Finance
PO12: Life-long Learning

### Bloom's Taxonomy Levels:
L1: Remember (Define, List, State)
L2: Understand (Describe, Explain, Summarize)
L3: Apply (Apply, Demonstrate, Solve)
L4: Analyze (Analyze, Compare, Investigate)
L5: Evaluate (Evaluate, Justify, Assess)
L6: Create (Design, Develop, Formulate)

### Assessment & Attainment:
- Direct Assessment: CIE (40%) + SEE (60%)
- Indirect Assessment: Course Exit Survey, Alumni Feedback
- Target Attainment: 60% students scoring 60% marks = Level 2

## OUTPUT REQUIREMENTS:
1. Use proper academic/formal language
2. Follow NAAC SSR format
3. Include quantitative metrics where applicable
4. Provide supporting evidence templates
5. Generate data in formats suitable for NAAC portal upload
6. Include DVV (Data Validation & Verification) ready formats"""

    # Criterion details with marks and key indicators
    CRITERIA_DETAILS = {
        NAACCriterion.CRITERION_1: {
            "name": "Curricular Aspects",
            "marks": 150,
            "key_indicators": [
                {"id": "1.1", "name": "Curricular Planning and Implementation", "marks": 50},
                {"id": "1.2", "name": "Academic Flexibility", "marks": 50},
                {"id": "1.3", "name": "Curriculum Enrichment", "marks": 30},
                {"id": "1.4", "name": "Feedback System", "marks": 20},
            ]
        },
        NAACCriterion.CRITERION_2: {
            "name": "Teaching-Learning and Evaluation",
            "marks": 200,
            "key_indicators": [
                {"id": "2.1", "name": "Student Enrollment and Profile", "marks": 30},
                {"id": "2.2", "name": "Catering to Student Diversity", "marks": 30},
                {"id": "2.3", "name": "Teaching-Learning Process", "marks": 40},
                {"id": "2.4", "name": "Teacher Quality", "marks": 40},
                {"id": "2.5", "name": "Evaluation Process and Reforms", "marks": 30},
                {"id": "2.6", "name": "Student Performance and Learning Outcomes", "marks": 30},
            ]
        },
        NAACCriterion.CRITERION_3: {
            "name": "Research, Innovations and Extension",
            "marks": 150,
            "key_indicators": [
                {"id": "3.1", "name": "Promotion of Research and Facilities", "marks": 20},
                {"id": "3.2", "name": "Resource Mobilization for Research", "marks": 20},
                {"id": "3.3", "name": "Innovation Ecosystem", "marks": 30},
                {"id": "3.4", "name": "Research Publications and Awards", "marks": 30},
                {"id": "3.5", "name": "Consultancy", "marks": 20},
                {"id": "3.6", "name": "Extension Activities", "marks": 20},
                {"id": "3.7", "name": "Collaboration", "marks": 10},
            ]
        },
        NAACCriterion.CRITERION_4: {
            "name": "Infrastructure and Learning Resources",
            "marks": 100,
            "key_indicators": [
                {"id": "4.1", "name": "Physical Facilities", "marks": 30},
                {"id": "4.2", "name": "Library as a Learning Resource", "marks": 30},
                {"id": "4.3", "name": "IT Infrastructure", "marks": 20},
                {"id": "4.4", "name": "Maintenance of Campus Infrastructure", "marks": 20},
            ]
        },
        NAACCriterion.CRITERION_5: {
            "name": "Student Support and Progression",
            "marks": 100,
            "key_indicators": [
                {"id": "5.1", "name": "Student Support", "marks": 30},
                {"id": "5.2", "name": "Student Progression", "marks": 30},
                {"id": "5.3", "name": "Student Participation and Activities", "marks": 20},
                {"id": "5.4", "name": "Alumni Engagement", "marks": 20},
            ]
        },
        NAACCriterion.CRITERION_6: {
            "name": "Governance, Leadership and Management",
            "marks": 100,
            "key_indicators": [
                {"id": "6.1", "name": "Institutional Vision and Leadership", "marks": 10},
                {"id": "6.2", "name": "Strategy Development and Deployment", "marks": 20},
                {"id": "6.3", "name": "Faculty Empowerment Strategies", "marks": 20},
                {"id": "6.4", "name": "Financial Management and Resource Mobilization", "marks": 20},
                {"id": "6.5", "name": "Internal Quality Assurance System", "marks": 30},
            ]
        },
        NAACCriterion.CRITERION_7: {
            "name": "Institutional Values and Best Practices",
            "marks": 100,
            "key_indicators": [
                {"id": "7.1", "name": "Institutional Values and Social Responsibilities", "marks": 50},
                {"id": "7.2", "name": "Best Practices", "marks": 30},
                {"id": "7.3", "name": "Institutional Distinctiveness", "marks": 20},
            ]
        },
    }

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="NAAC/NBA Accreditation Agent",
            role="accreditation_document_generator",
            capabilities=[
                # Criterion 1
                "curriculum_design",
                "academic_flexibility",
                "curriculum_enrichment",
                "feedback_analysis",
                # Criterion 2 (OBE)
                "course_outcome_generation",
                "program_outcome_mapping",
                "co_po_matrix_creation",
                "blooms_taxonomy_classification",
                "rubric_generation",
                "attainment_calculation",
                # Criterion 3
                "research_documentation",
                "publication_analysis",
                "extension_activities",
                # Criterion 4
                "infrastructure_audit",
                "library_documentation",
                "it_infrastructure",
                # Criterion 5
                "placement_documentation",
                "alumni_engagement",
                "student_progression",
                # Criterion 6
                "governance_documentation",
                "iqac_reports",
                "strategic_planning",
                # Criterion 7
                "best_practices",
                "green_audit",
                "gender_audit",
                # Complete Reports
                "ssr_generation",
                "dvv_clarification"
            ],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """Process accreditation document generation request."""
        try:
            logger.info(f"[{self.name}] Processing accreditation request")

            request = context.user_request
            metadata = context.metadata or {}

            # Determine which criterion/document to generate
            criterion = metadata.get("criterion")
            doc_type = metadata.get("doc_type", "full_ssr")

            if criterion:
                # Generate specific criterion report
                result = await self._generate_criterion_report(criterion, request, metadata)
            elif doc_type == "full_ssr":
                # Generate complete SSR
                result = await self._generate_full_ssr(request, metadata)
            else:
                # Generate specific document type
                result = await self._generate_specific_document(doc_type, request, metadata)

            return self.format_output(
                content=result,
                metadata={
                    "criterion": criterion,
                    "doc_type": doc_type,
                    "compliance": ["NAAC", "NBA", "AICTE", "UGC"],
                    "generated_at": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return {"success": False, "error": str(e), "agent": self.name}

    async def _generate_criterion_report(self, criterion: str, request: str, metadata: Dict) -> Dict[str, Any]:
        """Generate report for a specific NAAC criterion."""
        criterion_enum = NAACCriterion(criterion) if isinstance(criterion, str) else criterion
        criterion_info = self.CRITERIA_DETAILS.get(criterion_enum, {})

        prompt = f"""Generate a comprehensive NAAC {criterion_info.get('name', criterion)} report.

## Institution/Program Details:
{json.dumps(metadata, indent=2)}

## Context:
{request}

## Criterion Information:
- Name: {criterion_info.get('name')}
- Total Marks: {criterion_info.get('marks')}
- Key Indicators: {json.dumps(criterion_info.get('key_indicators', []), indent=2)}

## Requirements:
1. Generate content for ALL key indicators
2. Include quantitative metrics (QnM) and qualitative metrics (QlM)
3. Provide supporting document templates
4. Format for NAAC portal upload
5. Include DVV-ready data formats

Output as structured JSON with sections for each key indicator."""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8000,
            temperature=0.3
        )

        return self._parse_response(response)

    async def _generate_full_ssr(self, request: str, metadata: Dict) -> Dict[str, Any]:
        """Generate complete Self Study Report (SSR) structure."""
        prompt = f"""Generate a complete NAAC Self Study Report (SSR) structure for the institution.

## Institution Details:
{json.dumps(metadata, indent=2)}

## Context:
{request}

## Required Sections:

### PART A: INSTITUTIONAL DATA
1. Profile of the Institution
2. Extended Profile
3. Quality Indicator Framework (QIF)

### PART B: CRITERIA-WISE INPUTS
Generate templates and guidance for all 7 criteria:

**Criterion 1: Curricular Aspects (150 marks)**
- 1.1 Curricular Planning and Implementation
- 1.2 Academic Flexibility
- 1.3 Curriculum Enrichment
- 1.4 Feedback System

**Criterion 2: Teaching-Learning and Evaluation (200 marks)**
- 2.1 Student Enrollment and Profile
- 2.2 Catering to Student Diversity
- 2.3 Teaching-Learning Process
- 2.4 Teacher Quality
- 2.5 Evaluation Process and Reforms
- 2.6 Student Performance and Learning Outcomes

**Criterion 3: Research, Innovations and Extension (150 marks)**
- 3.1 Promotion of Research and Facilities
- 3.2 Resource Mobilization for Research
- 3.3 Innovation Ecosystem
- 3.4 Research Publications and Awards
- 3.5 Consultancy
- 3.6 Extension Activities
- 3.7 Collaboration

**Criterion 4: Infrastructure and Learning Resources (100 marks)**
- 4.1 Physical Facilities
- 4.2 Library as a Learning Resource
- 4.3 IT Infrastructure
- 4.4 Maintenance of Campus Infrastructure

**Criterion 5: Student Support and Progression (100 marks)**
- 5.1 Student Support
- 5.2 Student Progression
- 5.3 Student Participation and Activities
- 5.4 Alumni Engagement

**Criterion 6: Governance, Leadership and Management (100 marks)**
- 6.1 Institutional Vision and Leadership
- 6.2 Strategy Development and Deployment
- 6.3 Faculty Empowerment Strategies
- 6.4 Financial Management and Resource Mobilization
- 6.5 Internal Quality Assurance System

**Criterion 7: Institutional Values and Best Practices (100 marks)**
- 7.1 Institutional Values and Social Responsibilities
- 7.2 Best Practices (2 best practices)
- 7.3 Institutional Distinctiveness

Output as JSON with complete structure and templates for each section."""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=8000,
            temperature=0.3
        )

        return self._parse_response(response)

    async def _generate_specific_document(self, doc_type: str, request: str, metadata: Dict) -> Dict[str, Any]:
        """Generate a specific accreditation document."""
        doc_prompts = {
            # Criterion 1 documents
            "curriculum_design": self._get_curriculum_design_prompt,
            "feedback_system": self._get_feedback_system_prompt,

            # Criterion 2 documents (OBE)
            "course_outcomes": self._get_course_outcomes_prompt,
            "co_po_mapping": self._get_co_po_mapping_prompt,
            "rubrics": self._get_rubrics_prompt,
            "attainment": self._get_attainment_prompt,

            # Criterion 3 documents
            "research_promotion": self._get_research_promotion_prompt,
            "extension_activities": self._get_extension_activities_prompt,

            # Criterion 4 documents
            "infrastructure_audit": self._get_infrastructure_audit_prompt,
            "library_resources": self._get_library_resources_prompt,

            # Criterion 5 documents
            "student_progression": self._get_student_progression_prompt,
            "alumni_engagement": self._get_alumni_engagement_prompt,

            # Criterion 6 documents
            "vision_mission": self._get_vision_mission_prompt,
            "iqac": self._get_iqac_prompt,

            # Criterion 7 documents
            "best_practices": self._get_best_practices_prompt,
            "green_audit": self._get_green_audit_prompt,
        }

        prompt_func = doc_prompts.get(doc_type, self._get_generic_prompt)
        prompt = prompt_func(request, metadata)

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=6000,
            temperature=0.3
        )

        return self._parse_response(response)

    # ==================== CRITERION 1 PROMPTS ====================

    def _get_curriculum_design_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Curriculum Design and Development documentation for NAAC Criterion 1.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Curriculum Development Process
   - Board of Studies composition and meetings
   - Industry expert involvement
   - Stakeholder consultation process

2. Curriculum Revision Cycle
   - Frequency of revision
   - Changes made in last 5 years
   - Alignment with NEP 2020

3. CBCS Implementation
   - Core courses
   - Elective courses (DSE, GE, SEC, VAC)
   - Credit distribution

4. Cross-cutting Issues Integration
   - Gender
   - Environment and Sustainability
   - Human Values
   - Professional Ethics

5. Sample Documentation Templates

Output as JSON with all sections."""

    def _get_feedback_system_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Feedback System documentation for NAAC Criterion 1.4.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Feedback Collection Mechanisms
   - Student feedback on curriculum
   - Teacher feedback
   - Alumni feedback
   - Employer feedback
   - Parent feedback

2. Feedback Forms Templates
   - Questionnaire design
   - Rating scales
   - Open-ended questions

3. Feedback Analysis Process
   - Analysis methodology
   - Action taken reports
   - Feedback loop closure

4. Sample Feedback Analysis Report
   - Statistical analysis
   - Graphical representation
   - Recommendations

5. Evidence of Curriculum Changes Based on Feedback

Output as JSON with templates and sample reports."""

    # ==================== CRITERION 2 PROMPTS ====================

    def _get_course_outcomes_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Course Outcomes (COs) documentation for NAAC Criterion 2.

Context: {request}
Course Details: {json.dumps(metadata, indent=2)}

Requirements:
1. Generate 5-6 Course Outcomes following:
   - SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound)
   - Starting with Bloom's Taxonomy action verbs
   - Covering cognitive levels L1 to L6

2. For each CO include:
   - CO Statement
   - Bloom's Level (L1-L6)
   - Action Verb used
   - Knowledge/Skill domain
   - Assessment methods

3. CO-PO Mapping Matrix:
   - Map to all 12 NBA POs
   - Correlation levels (1=Low, 2=Medium, 3=High)
   - Justification for level 2-3 mappings

4. CO-PSO Mapping:
   - Map to department PSOs
   - Justifications

5. Assessment Rubrics:
   - Criteria for each CO
   - Performance levels (4-point scale)
   - Descriptors

Output as JSON with complete OBE documentation."""

    def _get_co_po_mapping_prompt(self, request: str, metadata: Dict) -> str:
        course_outcomes = metadata.get("course_outcomes", [])
        return f"""Generate CO-PO Mapping Matrix for the given Course Outcomes.

Course Outcomes:
{json.dumps(course_outcomes, indent=2)}

Course Details: {json.dumps(metadata, indent=2)}

Generate:
1. Complete CO-PO Matrix (COs × 12 POs)
2. Correlation Levels:
   - 3 = High/Strong correlation
   - 2 = Medium/Moderate correlation
   - 1 = Low/Slight correlation
   - 0 or - = No correlation

3. Justifications for each mapping ≥ 2

4. CO-PSO Mapping (if PSOs provided)

5. Attainment Calculation Template:
   - Direct assessment weightage
   - Indirect assessment weightage
   - Target attainment levels

6. Summary Statistics:
   - CO averages
   - PO attainment through this course
   - Coverage analysis

Output as JSON matrix with justifications."""

    def _get_rubrics_prompt(self, request: str, metadata: Dict) -> str:
        assessment_type = metadata.get("assessment_type", "project")
        return f"""Generate Assessment Rubrics for NAAC/NBA compliance.

Assessment Type: {assessment_type}
Context: {request}
Details: {json.dumps(metadata, indent=2)}

Generate rubrics with:
1. 5-6 Assessment Criteria relevant to {assessment_type}

2. 4 Performance Levels:
   - Excellent (4 points): 90-100%
   - Good (3 points): 70-89%
   - Satisfactory (2 points): 50-69%
   - Needs Improvement (1 point): Below 50%

3. For each criterion:
   - Clear descriptor for each level
   - Specific, measurable indicators
   - Weightage/marks allocation

4. Scoring Guide:
   - Maximum marks
   - Calculation formula
   - Grade conversion

5. CO Mapping:
   - Which COs are assessed by each criterion

Output as JSON with complete rubric structure."""

    def _get_attainment_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Attainment Calculation documentation for OBE compliance.

Context: {request}
Course Details: {json.dumps(metadata, indent=2)}

Generate:
1. Direct Assessment Methods:
   - CIE (Continuous Internal Evaluation) - 40%
     - Mid-term exams
     - Assignments
     - Quizzes
     - Lab work
   - SEE (Semester End Examination) - 60%

2. Indirect Assessment Methods:
   - Course Exit Survey
   - Alumni Feedback
   - Employer Feedback

3. Attainment Levels:
   - Level 3: ≥70% students scoring ≥60%
   - Level 2: ≥60% students scoring ≥50%
   - Level 1: ≥50% students scoring ≥40%
   - Level 0: <50% students scoring ≥40%

4. Calculation Templates:
   - CO Attainment calculation
   - PO Attainment via CO-PO mapping
   - PSO Attainment

5. Sample Calculations with formulas

6. Attainment Gap Analysis and Action Plan

Output as JSON with templates and formulas."""

    # ==================== CRITERION 3 PROMPTS ====================

    def _get_research_promotion_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Research Promotion documentation for NAAC Criterion 3.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Research Policy Document
   - Objectives
   - Incentive schemes
   - Seed money provisions
   - Leave policy for research

2. Research Facilities
   - Labs and equipment
   - Library resources
   - Computing facilities
   - Funding sources

3. Research Projects Template
   - Ongoing projects
   - Completed projects
   - Funding details

4. Publications Documentation
   - Journal publications
   - Conference papers
   - Books/chapters
   - Citation metrics

5. Patents and IPR
   - Filed/Granted patents
   - Technology transfers

6. Research Awards and Recognition

Output as JSON with templates."""

    def _get_extension_activities_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Extension Activities documentation for NAAC Criterion 3.6.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Extension Activity Categories:
   - NSS activities
   - NCC activities
   - Community outreach
   - Social awareness programs
   - Environmental initiatives
   - Health camps
   - Literacy programs

2. Activity Documentation Template:
   - Activity name
   - Date and duration
   - Location
   - Number of participants
   - Beneficiaries
   - Impact assessment

3. Adopted Village/Slum Programs
   - Area adopted
   - Activities conducted
   - Outcomes achieved

4. Collaboration with NGOs
   - MoU details
   - Joint activities

5. Awards and Recognition for Extension

Output as JSON with documentation templates."""

    # ==================== CRITERION 4 PROMPTS ====================

    def _get_infrastructure_audit_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Infrastructure Audit documentation for NAAC Criterion 4.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Physical Infrastructure
   - Classrooms (area, capacity, ICT facilities)
   - Laboratories (equipment list, utilization)
   - Seminar halls and auditoriums
   - Sports facilities
   - Hostels
   - Administrative buildings

2. Infrastructure Utilization Data
   - Classroom utilization %
   - Lab utilization %
   - Library utilization

3. Budget Allocation
   - Infrastructure budget (last 5 years)
   - Expenditure details
   - Future plans

4. Accessibility Features
   - Ramps and lifts
   - Accessible toilets
   - Signage
   - Other Divyangjan facilities

5. Safety and Security
   - Fire safety
   - CCTV coverage
   - Security personnel

Output as JSON with audit templates."""

    def _get_library_resources_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Library Resources documentation for NAAC Criterion 4.2.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Library Collection
   - Books (title-wise, volume-wise)
   - Journals (print and online)
   - E-resources (databases subscribed)
   - Digital library
   - Back volumes
   - Rare books

2. Library Services
   - OPAC
   - Remote access
   - Reprography
   - ILL (Inter-Library Loan)
   - Reference service
   - User orientation

3. Library Usage Statistics
   - Footfall data
   - Books issued
   - E-resource usage
   - Average usage per student

4. Library Automation
   - Software used
   - Bar-coding
   - RFID

5. Library Budget
   - Annual expenditure
   - New additions

6. User Feedback and Satisfaction

Output as JSON with statistics templates."""

    # ==================== CRITERION 5 PROMPTS ====================

    def _get_student_progression_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Student Progression documentation for NAAC Criterion 5.2.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Placement Data (Last 5 years)
   - Year-wise placement percentage
   - Number of students placed
   - Salary packages (minimum, maximum, average)
   - Recruiting companies
   - Sector-wise placement

2. Higher Education Progression
   - Students going for higher studies
   - Institutions joined
   - Courses pursued

3. Entrepreneurship
   - Students becoming entrepreneurs
   - Startups incubated
   - Support provided

4. Competitive Examination Success
   - GATE, CAT, GRE, UPSC, etc.
   - Number of qualifiers

5. Career Counseling
   - Activities conducted
   - External experts involved

6. Training and Skill Development
   - Soft skills training
   - Technical training
   - Industry certifications

Output as JSON with data templates."""

    def _get_alumni_engagement_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Alumni Engagement documentation for NAAC Criterion 5.4.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Alumni Association
   - Registration details
   - Office bearers
   - Constitution/Bylaws

2. Alumni Database
   - Total registered alumni
   - Batch-wise distribution
   - Location-wise distribution

3. Alumni Contributions
   - Financial contributions
   - Scholarships/endowments
   - Infrastructure donations
   - Guest lectures
   - Mentorship programs

4. Alumni Meets
   - Frequency
   - Participation
   - Activities conducted

5. Alumni in Advisory Roles
   - Board of Studies
   - Industry Advisory Board
   - Placement assistance

6. Notable Alumni
   - Achievements
   - Recognition

7. Alumni Feedback Mechanism
   - Curriculum feedback
   - Employability feedback

Output as JSON with templates."""

    # ==================== CRITERION 6 PROMPTS ====================

    def _get_vision_mission_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Vision, Mission, PEO documentation for NAAC Criterion 6.1.

Context: {request}
Institution Details: {json.dumps(metadata, indent=2)}

Include:
1. Vision Statement
   - Clear, concise vision
   - Alignment with national goals
   - Uniqueness

2. Mission Statements
   - 4-6 mission statements
   - Alignment with vision
   - Stakeholder focus

3. Core Values
   - Institutional values
   - Integration in curriculum

4. Program Educational Objectives (PEOs)
   - 4-5 PEOs per program
   - Alignment with mission
   - Graduate attributes addressed

5. PEO-Mission Mapping
   - Matrix showing alignment

6. Deployment Mechanism
   - How vision/mission is communicated
   - Display locations
   - Website integration
   - Orientation programs

7. Distinctive Features Supporting Vision

Output as JSON with complete documentation."""

    def _get_iqac_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate IQAC documentation for NAAC Criterion 6.5.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. IQAC Composition
   - Chairperson
   - Members (internal and external)
   - Coordinator

2. IQAC Functions
   - Development of quality benchmarks
   - Quality improvement strategies
   - Academic and administrative audit

3. IQAC Initiatives
   - Quality enhancement measures
   - Best practices identified
   - Innovations introduced

4. IQAC Meetings
   - Meeting minutes template
   - Action taken reports

5. AQAR (Annual Quality Assurance Report)
   - Structure and template
   - Submission timeline

6. Academic and Administrative Audit
   - Internal audit process
   - External audit
   - Audit report template

7. Quality Initiatives
   - ISO certification
   - NBA accreditation
   - Other quality certifications

8. Feedback Integration
   - Stakeholder feedback
   - Quality improvement cycle

Output as JSON with templates."""

    # ==================== CRITERION 7 PROMPTS ====================

    def _get_best_practices_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Best Practices documentation for NAAC Criterion 7.2.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Generate TWO Best Practices following NAAC format:

For EACH Best Practice include:
1. Title of the Practice

2. Objectives of the Practice
   - What it aims to achieve
   - Target beneficiaries

3. The Context
   - Background
   - Need identification
   - Relevance

4. The Practice
   - Detailed description
   - Uniqueness
   - Implementation process

5. Evidence of Success
   - Quantitative outcomes
   - Qualitative outcomes
   - Beneficiary feedback

6. Problems Encountered and Resources Required
   - Challenges faced
   - Resources (human, financial, infrastructure)
   - How challenges were addressed

7. Notes (Optional)
   - Future plans
   - Scalability
   - Replicability

Best Practice 1: Focus on Academic/Teaching-Learning
Best Practice 2: Focus on Community Engagement/Institutional

Output as JSON with both practices."""

    def _get_green_audit_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate Green/Environmental Audit documentation for NAAC Criterion 7.1.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Include:
1. Environmental Policy
   - Policy statement
   - Objectives
   - Implementation strategy

2. Energy Audit
   - Energy consumption data
   - Renewable energy usage
   - Energy conservation measures
   - Solar/wind installations

3. Water Management
   - Water consumption
   - Rainwater harvesting
   - Wastewater treatment
   - Water recycling

4. Waste Management
   - Solid waste management
   - E-waste disposal
   - Biomedical waste (if applicable)
   - Hazardous waste

5. Green Campus Initiatives
   - Tree plantation
   - Plastic-free campus
   - Green landscaping
   - Carbon footprint reduction

6. Environmental Awareness
   - Programs conducted
   - NSS/NCC involvement
   - Celebrations (Environment Day, etc.)

7. Green Audit Report
   - Third-party audit
   - Recommendations
   - Action taken

8. Certifications
   - ISO 14001
   - Green building certifications

Output as JSON with audit templates."""

    def _get_generic_prompt(self, request: str, metadata: Dict) -> str:
        return f"""Generate NAAC/NBA accreditation documentation.

Context: {request}
Details: {json.dumps(metadata, indent=2)}

Generate comprehensive documentation following NAAC SSR format.
Include all relevant metrics, templates, and evidence requirements.

Output as structured JSON."""

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse Claude's response into structured format."""
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                return json.loads(json_str)
            elif response.strip().startswith("{"):
                return json.loads(response)
        except json.JSONDecodeError:
            pass

        return {"raw_response": response, "parsed": False}

    # ==================== PUBLIC API METHODS ====================

    async def generate_criterion_1(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 1: Curricular Aspects documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_1.value
        return await self.process(context)

    async def generate_criterion_2(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 2: Teaching-Learning and Evaluation documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_2.value
        return await self.process(context)

    async def generate_criterion_3(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 3: Research, Innovations and Extension documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_3.value
        return await self.process(context)

    async def generate_criterion_4(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 4: Infrastructure and Learning Resources documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_4.value
        return await self.process(context)

    async def generate_criterion_5(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 5: Student Support and Progression documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_5.value
        return await self.process(context)

    async def generate_criterion_6(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 6: Governance, Leadership and Management documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_6.value
        return await self.process(context)

    async def generate_criterion_7(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Criterion 7: Institutional Values and Best Practices documentation."""
        context.metadata = context.metadata or {}
        context.metadata["criterion"] = NAACCriterion.CRITERION_7.value
        return await self.process(context)

    async def generate_full_ssr(self, context: AgentContext) -> Dict[str, Any]:
        """Generate complete Self Study Report (SSR)."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = "full_ssr"
        return await self.process(context)

    async def generate_course_outcomes(self, context: AgentContext) -> Dict[str, Any]:
        """Generate Course Outcomes with Bloom's Taxonomy."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = AccreditationDocType.COURSE_OUTCOMES.value
        return await self.process(context)

    async def generate_co_po_mapping(self, context: AgentContext, course_outcomes: List[str]) -> Dict[str, Any]:
        """Generate CO-PO mapping matrix."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = AccreditationDocType.CO_PO_MAPPING.value
        context.metadata["course_outcomes"] = course_outcomes
        return await self.process(context)

    async def generate_rubrics(self, context: AgentContext, assessment_type: str = "project") -> Dict[str, Any]:
        """Generate assessment rubrics."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = AccreditationDocType.RUBRICS.value
        context.metadata["assessment_type"] = assessment_type
        return await self.process(context)

    async def generate_best_practices(self, context: AgentContext) -> Dict[str, Any]:
        """Generate two best practices for Criterion 7.2."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = AccreditationDocType.BEST_PRACTICES.value
        return await self.process(context)

    async def generate_iqac_report(self, context: AgentContext) -> Dict[str, Any]:
        """Generate IQAC documentation."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = AccreditationDocType.IQAC.value
        return await self.process(context)

    def get_criteria_overview(self) -> Dict[str, Any]:
        """Get overview of all 7 NAAC criteria."""
        return {
            "total_marks": 700,
            "criteria": {
                k.value: v for k, v in self.CRITERIA_DETAILS.items()
            },
            "grading": {
                "A++": "3.51 - 4.00 (CGPA)",
                "A+": "3.26 - 3.50",
                "A": "3.01 - 3.25",
                "B++": "2.76 - 3.00",
                "B+": "2.51 - 2.75",
                "B": "2.01 - 2.50",
                "C": "1.51 - 2.00",
                "D": "≤ 1.50"
            }
        }


# Singleton instance
naac_nba_agent = NAACNBAAgent()
