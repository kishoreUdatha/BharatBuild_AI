"""
NAAC/NBA Accreditation Agent
Generates accreditation-compliant documents for Indian colleges.

Supports:
- Course Outcomes (COs)
- Program Outcomes (POs)
- CO-PO Mapping Matrix
- Bloom's Taxonomy Classification
- Rubrics for Assessment
- Attainment Calculation Templates
- OBE (Outcome-Based Education) Documents
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.modules.agents.base_agent import BaseAgent, AgentContext

logger = logging.getLogger(__name__)

# Prompts directory
PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


class AccreditationDocType(str, Enum):
    """Types of accreditation documents"""
    COURSE_OUTCOMES = "course_outcomes"
    PROGRAM_OUTCOMES = "program_outcomes"
    CO_PO_MAPPING = "co_po_mapping"
    BLOOMS_TAXONOMY = "blooms_taxonomy"
    RUBRICS = "rubrics"
    ATTAINMENT = "attainment"
    FULL_REPORT = "full_report"


@dataclass
class AccreditationContext:
    """Context for accreditation document generation"""
    course_name: str
    course_code: str
    department: str
    semester: int
    credits: int
    project_description: str
    program_name: Optional[str] = None
    university: Optional[str] = None
    doc_type: AccreditationDocType = AccreditationDocType.FULL_REPORT


class NAACNBAAgent(BaseAgent):
    """
    Agent for generating NAAC/NBA accreditation documents.

    Generates documents compliant with:
    - NAAC (National Assessment and Accreditation Council)
    - NBA (National Board of Accreditation)
    - AICTE guidelines
    - UGC regulations
    """

    SYSTEM_PROMPT = """You are an expert in Indian higher education accreditation systems, specifically NAAC (National Assessment and Accreditation Council) and NBA (National Board of Accreditation).

Your role is to generate accreditation-compliant academic documents for engineering and technical education in India.

## Your Expertise Includes:
1. **Outcome-Based Education (OBE)** framework
2. **Bloom's Taxonomy** - Cognitive, Affective, and Psychomotor domains
3. **Course Outcomes (COs)** - Measurable learning outcomes for courses
4. **Program Outcomes (POs)** - Graduate attributes as per NBA
5. **Program Specific Outcomes (PSOs)** - Department-specific outcomes
6. **CO-PO Mapping** - Correlation matrices with justification
7. **Rubrics** - Assessment criteria with levels
8. **Attainment Calculation** - Direct and indirect methods

## NBA's 12 Program Outcomes (POs):
1. Engineering Knowledge
2. Problem Analysis
3. Design/Development of Solutions
4. Conduct Investigations of Complex Problems
5. Modern Tool Usage
6. The Engineer and Society
7. Environment and Sustainability
8. Ethics
9. Individual and Team Work
10. Communication
11. Project Management and Finance
12. Life-long Learning

## Bloom's Taxonomy Levels (Cognitive Domain):
1. Remember (L1) - Recall facts and basic concepts
2. Understand (L2) - Explain ideas or concepts
3. Apply (L3) - Use information in new situations
4. Analyze (L4) - Draw connections among ideas
5. Evaluate (L5) - Justify a stand or decision
6. Create (L6) - Produce new or original work

## Action Verbs by Bloom's Level:
- L1 (Remember): Define, List, State, Identify, Recall, Name
- L2 (Understand): Describe, Explain, Summarize, Classify, Compare
- L3 (Apply): Apply, Demonstrate, Implement, Solve, Use, Execute
- L4 (Analyze): Analyze, Differentiate, Examine, Compare, Contrast, Investigate
- L5 (Evaluate): Evaluate, Justify, Critique, Assess, Judge, Recommend
- L6 (Create): Design, Develop, Create, Construct, Produce, Formulate

## CO-PO Mapping Correlation Levels:
- 3 (High): The CO directly and significantly contributes to the PO
- 2 (Medium): The CO moderately contributes to the PO
- 1 (Low): The CO has minimal contribution to the PO
- 0 or blank: No correlation

## Output Format Guidelines:
- Always use proper academic language
- Include justifications for mappings
- Follow IEEE/academic formatting standards
- Provide actionable assessment criteria
- Include both direct and indirect assessment methods

Generate documents that are ready for NAAC/NBA audit and accreditation visits."""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="NAAC/NBA Accreditation Agent",
            role="accreditation_document_generator",
            capabilities=[
                "course_outcome_generation",
                "program_outcome_mapping",
                "co_po_matrix_creation",
                "blooms_taxonomy_classification",
                "rubric_generation",
                "attainment_calculation",
                "obe_compliance_check"
            ],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Process accreditation document generation request.

        Args:
            context: AgentContext with user_request containing project details

        Returns:
            Dict containing generated accreditation documents
        """
        try:
            logger.info(f"[{self.name}] Processing accreditation request")

            # Parse the request to determine what documents to generate
            request = context.user_request
            metadata = context.metadata or {}

            # Extract course/project information
            course_info = self._extract_course_info(request, metadata)

            # Build comprehensive prompt
            user_prompt = self._build_accreditation_prompt(request, course_info)

            # Call Claude for generation
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
                max_tokens=8000,
                temperature=0.3  # Lower temperature for consistency
            )

            # Parse and structure the response
            documents = self._parse_accreditation_response(response, course_info)

            logger.info(f"[{self.name}] Generated {len(documents)} accreditation documents")

            return self.format_output(
                content=documents,
                metadata={
                    "course_info": course_info,
                    "doc_types_generated": list(documents.keys()),
                    "compliance": ["NAAC", "NBA", "AICTE", "OBE"]
                }
            )

        except Exception as e:
            logger.error(f"[{self.name}] Error: {e}")
            return {
                "success": False,
                "error": str(e),
                "agent": self.name
            }

    def _extract_course_info(self, request: str, metadata: Dict) -> Dict[str, Any]:
        """Extract course information from request and metadata."""
        return {
            "course_name": metadata.get("course_name", "Software Engineering Project"),
            "course_code": metadata.get("course_code", "CS601"),
            "department": metadata.get("department", "Computer Science and Engineering"),
            "semester": metadata.get("semester", 6),
            "credits": metadata.get("credits", 4),
            "program_name": metadata.get("program_name", "B.Tech Computer Science and Engineering"),
            "university": metadata.get("university", ""),
            "project_description": request
        }

    def _build_accreditation_prompt(self, request: str, course_info: Dict) -> str:
        """Build detailed prompt for accreditation document generation."""
        return f"""Generate complete NAAC/NBA accreditation documents for the following project/course:

## Course Information:
- Course Name: {course_info['course_name']}
- Course Code: {course_info['course_code']}
- Department: {course_info['department']}
- Semester: {course_info['semester']}
- Credits: {course_info['credits']}
- Program: {course_info['program_name']}

## Project/Course Description:
{course_info['project_description']}

## Required Documents:

### 1. COURSE OUTCOMES (COs)
Generate 5-6 Course Outcomes that:
- Start with action verbs from Bloom's Taxonomy
- Are specific, measurable, achievable, relevant, and time-bound (SMART)
- Cover different cognitive levels (at least L1 to L4)
- Align with the project/course objectives

Format each CO as:
CO1: [Action Verb] + [Content] + [Condition/Context]
Bloom's Level: [L1-L6]

### 2. CO-PO MAPPING MATRIX
Create a mapping matrix showing correlation between COs and all 12 POs:
- Use correlation levels: 3 (High), 2 (Medium), 1 (Low), - (None)
- Provide brief justification for each mapping >= 2
- Calculate average PO attainment

### 3. PROGRAM SPECIFIC OUTCOMES (PSOs)
Generate 2-3 PSOs specific to the department that:
- Complement the standard 12 POs
- Reflect department specialization
- Are achievable through this course

### 4. BLOOM'S TAXONOMY ANALYSIS
For each CO, provide:
- Cognitive level classification
- Action verbs used
- Assessment methods suitable for that level

### 5. ASSESSMENT RUBRICS
Create detailed rubrics for:
- Project evaluation (if applicable)
- Lab/practical assessment
- Viva voce
Include 4-5 criteria with 4 performance levels each (Excellent, Good, Satisfactory, Needs Improvement)

### 6. ATTAINMENT CALCULATION TEMPLATE
Provide:
- Direct assessment methods (exams, assignments, projects)
- Indirect assessment methods (surveys, exit feedback)
- Weightage distribution
- Target attainment levels
- Sample calculation formula

Output all documents in a structured JSON format with clear sections."""

    def _parse_accreditation_response(self, response: str, course_info: Dict) -> Dict[str, Any]:
        """Parse Claude's response into structured documents."""
        documents = {
            "course_outcomes": [],
            "co_po_mapping": {},
            "program_specific_outcomes": [],
            "blooms_analysis": [],
            "rubrics": [],
            "attainment_template": {},
            "raw_response": response
        }

        # Try to parse as JSON first
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
                parsed = json.loads(json_str)
                documents.update(parsed)
            elif response.strip().startswith("{"):
                parsed = json.loads(response)
                documents.update(parsed)
        except json.JSONDecodeError:
            # Keep raw response for manual parsing
            logger.warning("Could not parse JSON, keeping raw response")

        # Add metadata
        documents["metadata"] = {
            "course_info": course_info,
            "generated_by": self.name,
            "compliance_standards": ["NAAC", "NBA", "AICTE", "OBE"],
            "blooms_levels_covered": self._analyze_blooms_coverage(documents.get("course_outcomes", []))
        }

        return documents

    def _analyze_blooms_coverage(self, course_outcomes: List) -> Dict[str, int]:
        """Analyze Bloom's Taxonomy coverage in COs."""
        coverage = {
            "L1_Remember": 0,
            "L2_Understand": 0,
            "L3_Apply": 0,
            "L4_Analyze": 0,
            "L5_Evaluate": 0,
            "L6_Create": 0
        }

        # Action verb mappings
        level_verbs = {
            "L1_Remember": ["define", "list", "state", "identify", "recall", "name", "recognize"],
            "L2_Understand": ["describe", "explain", "summarize", "classify", "compare", "interpret"],
            "L3_Apply": ["apply", "demonstrate", "implement", "solve", "use", "execute", "compute"],
            "L4_Analyze": ["analyze", "differentiate", "examine", "compare", "contrast", "investigate"],
            "L5_Evaluate": ["evaluate", "justify", "critique", "assess", "judge", "recommend"],
            "L6_Create": ["design", "develop", "create", "construct", "produce", "formulate", "build"]
        }

        for co in course_outcomes:
            co_text = str(co).lower() if co else ""
            for level, verbs in level_verbs.items():
                if any(verb in co_text for verb in verbs):
                    coverage[level] += 1
                    break

        return coverage

    async def generate_course_outcomes(self, context: AgentContext) -> Dict[str, Any]:
        """Generate only Course Outcomes."""
        context.metadata = context.metadata or {}
        context.metadata["doc_type"] = AccreditationDocType.COURSE_OUTCOMES.value
        return await self.process(context)

    async def generate_co_po_mapping(self, context: AgentContext, course_outcomes: List[str]) -> Dict[str, Any]:
        """Generate CO-PO mapping matrix for given COs."""
        prompt = f"""Create a detailed CO-PO mapping matrix for these Course Outcomes:

{chr(10).join([f"CO{i+1}: {co}" for i, co in enumerate(course_outcomes)])}

Generate a matrix with:
1. All 12 NBA Program Outcomes
2. Correlation levels (3=High, 2=Medium, 1=Low, -=None)
3. Justification for each significant mapping (>=2)
4. Row and column averages

Output as JSON with structure:
{{
    "matrix": [[correlation values]],
    "po_list": ["PO1 description", ...],
    "co_list": ["CO1", ...],
    "justifications": {{"CO1-PO1": "reason", ...}},
    "co_averages": [...],
    "po_averages": [...]
}}"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4000,
            temperature=0.2
        )

        return self.format_output(content=response, metadata={"type": "co_po_mapping"})

    async def generate_rubrics(self, context: AgentContext, assessment_type: str = "project") -> Dict[str, Any]:
        """Generate assessment rubrics."""
        prompt = f"""Create detailed assessment rubrics for: {assessment_type}

Project/Course: {context.user_request}

Generate rubrics with:
1. 5-6 assessment criteria
2. 4 performance levels: Excellent (4), Good (3), Satisfactory (2), Needs Improvement (1)
3. Clear descriptors for each cell
4. Weightage for each criterion
5. Maximum marks calculation

Output as JSON with structure:
{{
    "assessment_type": "{assessment_type}",
    "total_marks": 100,
    "criteria": [
        {{
            "name": "criterion name",
            "weightage": 20,
            "max_marks": 20,
            "levels": {{
                "excellent": {{"marks": "18-20", "descriptor": "..."}},
                "good": {{"marks": "14-17", "descriptor": "..."}},
                "satisfactory": {{"marks": "10-13", "descriptor": "..."}},
                "needs_improvement": {{"marks": "0-9", "descriptor": "..."}}
            }}
        }}
    ]
}}"""

        response = await self._call_claude(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=prompt,
            max_tokens=4000,
            temperature=0.3
        )

        return self.format_output(content=response, metadata={"type": "rubrics"})


# Singleton instance
naac_nba_agent = NAACNBAAgent()
