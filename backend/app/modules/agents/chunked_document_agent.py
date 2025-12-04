"""
CHUNKED DOCUMENT GENERATOR AGENT
================================
Generates 60-80 page Word documents and PPTs by breaking into sections.

Architecture:
1. Phase 1: Generate Document Outline (structure + sections)
2. Phase 2: Generate each section content separately (parallel)
3. Phase 3: Generate UML diagrams
4. Phase 4: Assemble into final Word/PPT documents

Features:
- Token limit handling via chunking
- Parallel section generation for speed
- Retry logic for failed sections
- College info integration (Certificate, Declaration, Acknowledgement)
- Dynamic UML diagram generation

This bypasses Claude's token limits by chunking the generation.
"""

from typing import Dict, List, Optional, Any, AsyncGenerator, Tuple
from collections import OrderedDict
from dataclasses import dataclass, field
import json
import asyncio
from datetime import datetime
from enum import Enum

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.modules.automation.uml_generator import uml_generator


@dataclass
class CollegeInfo:
    """College information for academic documents"""
    college_name: str = "College Name"
    affiliated_to: str = "Autonomous Institution"
    college_address: str = ""
    department: str = "Department of Computer Science and Engineering"
    academic_year: str = "2024-2025"
    guide_name: str = "Dr. Guide Name"
    hod_name: str = "Dr. HOD Name"
    principal_name: str = "Dr. Principal Name"
    project_title: str = "Project Title"
    date: str = ""
    students: List[Dict] = field(default_factory=list)  # [{"name": "...", "roll_number": "..."}]

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%B %Y")
        if not self.students:
            self.students = [{"name": "Student Name", "roll_number": "ROLL001"}]

    def to_dict(self) -> Dict:
        return {
            "college_name": self.college_name,
            "affiliated_to": self.affiliated_to,
            "college_address": self.college_address,
            "department": self.department,
            "academic_year": self.academic_year,
            "guide_name": self.guide_name,
            "hod_name": self.hod_name,
            "principal_name": self.principal_name,
            "project_title": self.project_title,
            "date": self.date,
            "students": self.students
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CollegeInfo":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class DocumentType(str, Enum):
    """Supported document types"""
    SRS = "srs"
    SDS = "sds"
    PROJECT_REPORT = "project_report"
    PPT = "ppt"
    TESTING_PLAN = "testing_plan"
    USER_MANUAL = "user_manual"
    VIVA_QA = "viva_qa"  # Viva Questions and Answers document


class ChunkedDocumentAgent(BaseAgent):
    """
    Chunked Document Generator - Handles large documents (60-80 pages)

    Strategy:
    - Break document into logical sections
    - Generate each section with separate Claude calls
    - Assemble final document with python-docx/python-pptx
    """

    # Document structure templates (60-80 pages MAX)
    DOCUMENT_STRUCTURES = {
        DocumentType.PROJECT_REPORT: {
            "name": "Project Report",
            "estimated_pages": 65,  # Target 60-80 pages
            "sections": [
                {"id": "cover", "title": "Cover Page", "pages": 1, "type": "template"},
                {"id": "certificate", "title": "Certificate", "pages": 1, "type": "template"},
                {"id": "declaration", "title": "Declaration", "pages": 1, "type": "template"},
                {"id": "acknowledgement", "title": "Acknowledgement", "pages": 1, "type": "generate"},
                {"id": "abstract", "title": "Abstract", "pages": 1, "type": "generate"},
                {"id": "toc", "title": "Table of Contents", "pages": 2, "type": "auto"},
                {"id": "list_figures", "title": "List of Figures", "pages": 1, "type": "auto"},
                {"id": "list_tables", "title": "List of Tables", "pages": 1, "type": "auto"},
                {"id": "ch1_intro", "title": "Chapter 1: Introduction", "pages": 6, "type": "generate", "subsections": [
                    "1.1 Background",
                    "1.2 Problem Statement",
                    "1.3 Objectives",
                    "1.4 Scope of the Project",
                    "1.5 Methodology",
                    "1.6 Organization of Report"
                ]},
                {"id": "ch2_literature", "title": "Chapter 2: Literature Review", "pages": 6, "type": "generate", "subsections": [
                    "2.1 Existing Systems",
                    "2.2 Comparative Analysis",
                    "2.3 Technology Review",
                    "2.4 Gap Analysis"
                ]},
                {"id": "ch3_requirements", "title": "Chapter 3: Requirement Analysis", "pages": 8, "type": "generate", "subsections": [
                    "3.1 Functional Requirements",
                    "3.2 Non-Functional Requirements",
                    "3.3 Hardware Requirements",
                    "3.4 Software Requirements",
                    "3.5 Use Case Diagrams",
                    "3.6 Data Flow Diagrams"
                ]},
                {"id": "ch4_design", "title": "Chapter 4: System Design", "pages": 10, "type": "generate", "subsections": [
                    "4.1 System Architecture",
                    "4.2 Database Design",
                    "4.3 ER Diagram",
                    "4.4 Class Diagram",
                    "4.5 Sequence Diagrams",
                    "4.6 Activity Diagrams",
                    "4.7 API Design",
                    "4.8 UI/UX Design"
                ]},
                {"id": "ch5_implementation", "title": "Chapter 5: Implementation", "pages": 8, "type": "generate", "subsections": [
                    "5.1 Development Environment",
                    "5.2 Frontend Implementation",
                    "5.3 Backend Implementation",
                    "5.4 Database Implementation",
                    "5.5 Code Snippets"
                ]},
                {"id": "ch6_testing", "title": "Chapter 6: Testing", "pages": 6, "type": "generate", "subsections": [
                    "6.1 Testing Strategy",
                    "6.2 Unit Testing",
                    "6.3 Integration Testing",
                    "6.4 System Testing",
                    "6.5 Test Cases and Results"
                ]},
                {"id": "ch7_results", "title": "Chapter 7: Results and Discussion", "pages": 5, "type": "generate", "subsections": [
                    "7.1 Screenshots",
                    "7.2 Performance Analysis",
                    "7.3 User Feedback"
                ]},
                {"id": "ch8_conclusion", "title": "Chapter 8: Conclusion and Future Scope", "pages": 3, "type": "generate", "subsections": [
                    "8.1 Conclusion",
                    "8.2 Limitations",
                    "8.3 Future Enhancements"
                ]},
                {"id": "references", "title": "References", "pages": 2, "type": "generate"},
                {"id": "appendix_a", "title": "Appendix A: Source Code", "pages": 4, "type": "code"},
                {"id": "appendix_b", "title": "Appendix B: Database Schema", "pages": 2, "type": "generate"},
            ]
        },
        DocumentType.SRS: {
            "name": "Software Requirements Specification",
            "estimated_pages": 25,
            "sections": [
                {"id": "cover", "title": "Cover Page", "pages": 1, "type": "template"},
                {"id": "revision_history", "title": "Revision History", "pages": 1, "type": "template"},
                {"id": "toc", "title": "Table of Contents", "pages": 1, "type": "auto"},
                {"id": "sec1_intro", "title": "1. Introduction", "pages": 3, "type": "generate", "subsections": [
                    "1.1 Purpose",
                    "1.2 Scope",
                    "1.3 Definitions and Acronyms",
                    "1.4 References",
                    "1.5 Overview"
                ]},
                {"id": "sec2_overall", "title": "2. Overall Description", "pages": 5, "type": "generate", "subsections": [
                    "2.1 Product Perspective",
                    "2.2 Product Functions",
                    "2.3 User Characteristics",
                    "2.4 Constraints",
                    "2.5 Assumptions and Dependencies"
                ]},
                {"id": "sec3_requirements", "title": "3. Specific Requirements", "pages": 10, "type": "generate", "subsections": [
                    "3.1 External Interface Requirements",
                    "3.2 Functional Requirements",
                    "3.3 Performance Requirements",
                    "3.4 Design Constraints",
                    "3.5 Software System Attributes"
                ]},
                {"id": "sec4_appendix", "title": "4. Appendices", "pages": 4, "type": "generate"},
            ]
        },
        DocumentType.SDS: {
            "name": "Software Design Specification",
            "estimated_pages": 30,
            "sections": [
                {"id": "cover", "title": "Cover Page", "pages": 1, "type": "template"},
                {"id": "revision_history", "title": "Revision History", "pages": 1, "type": "template"},
                {"id": "toc", "title": "Table of Contents", "pages": 1, "type": "auto"},
                {"id": "sec1_intro", "title": "1. Introduction", "pages": 2, "type": "generate", "subsections": [
                    "1.1 Purpose",
                    "1.2 Scope",
                    "1.3 Definitions and Acronyms",
                    "1.4 References",
                    "1.5 Document Overview"
                ]},
                {"id": "sec2_architecture", "title": "2. System Architecture", "pages": 6, "type": "generate", "subsections": [
                    "2.1 Architecture Overview",
                    "2.2 Component Diagram",
                    "2.3 Deployment Architecture",
                    "2.4 Technology Stack",
                    "2.5 Design Patterns Used"
                ]},
                {"id": "sec3_database", "title": "3. Database Design", "pages": 5, "type": "generate", "subsections": [
                    "3.1 Database Schema",
                    "3.2 Entity Relationship Diagram",
                    "3.3 Table Descriptions",
                    "3.4 Data Dictionary",
                    "3.5 Database Constraints"
                ]},
                {"id": "sec4_api", "title": "4. API Design", "pages": 5, "type": "generate", "subsections": [
                    "4.1 API Architecture",
                    "4.2 Endpoint Documentation",
                    "4.3 Request/Response Formats",
                    "4.4 Authentication & Authorization",
                    "4.5 Error Handling"
                ]},
                {"id": "sec5_ui", "title": "5. UI/UX Design", "pages": 4, "type": "generate", "subsections": [
                    "5.1 User Interface Overview",
                    "5.2 Navigation Flow",
                    "5.3 Screen Wireframes",
                    "5.4 Design Guidelines"
                ]},
                {"id": "sec6_security", "title": "6. Security Design", "pages": 3, "type": "generate", "subsections": [
                    "6.1 Security Requirements",
                    "6.2 Authentication Mechanism",
                    "6.3 Data Protection",
                    "6.4 Security Best Practices"
                ]},
                {"id": "sec7_deployment", "title": "7. Deployment Architecture", "pages": 3, "type": "generate", "subsections": [
                    "7.1 Deployment Overview",
                    "7.2 Infrastructure Requirements",
                    "7.3 Scalability Considerations",
                    "7.4 Monitoring Strategy"
                ]},
            ]
        },
        DocumentType.PPT: {
            "name": "Project Presentation",
            "estimated_slides": 25,
            "sections": [
                {"id": "title", "title": "Title Slide", "slides": 1, "type": "template"},
                {"id": "agenda", "title": "Agenda", "slides": 1, "type": "generate"},
                {"id": "intro", "title": "Introduction", "slides": 3, "type": "generate"},
                {"id": "problem", "title": "Problem Statement", "slides": 2, "type": "generate"},
                {"id": "objectives", "title": "Objectives", "slides": 2, "type": "generate"},
                {"id": "literature", "title": "Literature Review", "slides": 2, "type": "generate"},
                {"id": "methodology", "title": "Methodology", "slides": 2, "type": "generate"},
                {"id": "architecture", "title": "System Architecture", "slides": 2, "type": "generate"},
                {"id": "implementation", "title": "Implementation", "slides": 3, "type": "generate"},
                {"id": "demo", "title": "Demo Screenshots", "slides": 3, "type": "generate"},
                {"id": "testing", "title": "Testing Results", "slides": 2, "type": "generate"},
                {"id": "conclusion", "title": "Conclusion", "slides": 1, "type": "generate"},
                {"id": "future", "title": "Future Scope", "slides": 1, "type": "generate"},
                {"id": "references", "title": "References", "slides": 1, "type": "generate"},
                {"id": "thankyou", "title": "Thank You", "slides": 1, "type": "template"},
            ]
        },
        DocumentType.VIVA_QA: {
            "name": "Viva Questions and Answers",
            "estimated_pages": 15,
            "sections": [
                {"id": "cover", "title": "Cover Page", "pages": 1, "type": "template"},
                {"id": "intro_qa", "title": "Project Introduction Questions", "pages": 2, "type": "generate", "subsections": [
                    "Q1: What is the project about?",
                    "Q2: Why did you choose this project?",
                    "Q3: What problem does it solve?",
                    "Q4: Who are the target users?",
                    "Q5: What are the main objectives?"
                ]},
                {"id": "tech_qa", "title": "Technology Stack Questions", "pages": 3, "type": "generate", "subsections": [
                    "Q1: What technologies did you use and why?",
                    "Q2: Explain the frontend technology choice",
                    "Q3: Explain the backend technology choice",
                    "Q4: Why did you choose this database?",
                    "Q5: What are the advantages of your tech stack?",
                    "Q6: What are the limitations of your tech stack?"
                ]},
                {"id": "architecture_qa", "title": "System Architecture Questions", "pages": 2, "type": "generate", "subsections": [
                    "Q1: Explain the system architecture",
                    "Q2: What design patterns did you use?",
                    "Q3: How does the frontend communicate with backend?",
                    "Q4: Explain the database schema design",
                    "Q5: How did you handle authentication?"
                ]},
                {"id": "implementation_qa", "title": "Implementation Questions", "pages": 3, "type": "generate", "subsections": [
                    "Q1: What were the main challenges in implementation?",
                    "Q2: How did you overcome those challenges?",
                    "Q3: Explain a critical code module",
                    "Q4: How did you manage state in the application?",
                    "Q5: Explain the API design",
                    "Q6: How did you handle error handling?"
                ]},
                {"id": "testing_qa", "title": "Testing Questions", "pages": 2, "type": "generate", "subsections": [
                    "Q1: What testing strategies did you use?",
                    "Q2: How did you perform unit testing?",
                    "Q3: Explain integration testing approach",
                    "Q4: How did you handle bug fixes?",
                    "Q5: What is the test coverage?"
                ]},
                {"id": "future_qa", "title": "Future Scope Questions", "pages": 1, "type": "generate", "subsections": [
                    "Q1: What are the limitations of your project?",
                    "Q2: What future enhancements do you suggest?",
                    "Q3: How would you scale this application?",
                    "Q4: What security improvements would you add?"
                ]},
                {"id": "general_qa", "title": "General Technical Questions", "pages": 1, "type": "generate", "subsections": [
                    "Q1: Explain the software development lifecycle you followed",
                    "Q2: How did you manage version control?",
                    "Q3: What tools did you use for development?",
                    "Q4: How did you collaborate as a team?"
                ]}
            ]
        }
    }

    OUTLINE_SYSTEM_PROMPT = """You are a Document Outline Generator for academic projects.

Your task is to create a detailed outline for a specific section of a document.

RULES:
1. Output ONLY valid JSON
2. Be specific to the project provided
3. Include realistic content points
4. Academic tone
5. No placeholders

Output format:
{
    "section_id": "chapter_id",
    "title": "Section Title",
    "subsections": [
        {
            "id": "1.1",
            "title": "Subsection Title",
            "key_points": ["point1", "point2", ...],
            "estimated_words": 500
        }
    ],
    "diagrams_needed": ["diagram_type1", ...],
    "tables_needed": ["table_type1", ...]
}
"""

    CONTENT_SYSTEM_PROMPT = """You are an Academic Content Writer for project documentation.

CRITICAL RULES:
1. Write PROFESSIONAL, CONCISE content (target words as specified)
2. Use the project data provided - include specific details
3. Include technical details and explanations
4. Academic writing style with proper paragraphs
5. NO placeholders or "TODO" - write real content
6. Each subsection should be focused and relevant (80-120 words each)
7. Use proper formatting:
   - **bold** for emphasis
   - `code` for technical terms
   - Bullet points where appropriate

IMPORTANT: You MUST output ONLY valid JSON. No markdown, no explanations, no text before or after the JSON.

JSON FORMAT (output exactly this structure):
{
    "section_id": "id",
    "title": "Title",
    "content": "Main section introduction (100-150 words)...",
    "subsections": [
        {
            "id": "1.1",
            "title": "Subsection Title",
            "content": "Concise subsection content (80-120 words)..."
        }
    ],
    "tables": [
        {
            "id": "table_1",
            "caption": "Table caption",
            "headers": ["Column 1", "Column 2"],
            "rows": [["data1", "data2"]]
        }
    ]
}
"""

    VIVA_QA_SYSTEM_PROMPT = """You are a Viva Questions and Answers Generator for academic projects.

Your task is to generate comprehensive Q&A content that helps students prepare for viva examinations.

CRITICAL RULES:
1. Generate REALISTIC questions that examiners would ask
2. Provide DETAILED answers with technical accuracy
3. Each answer should be 100-200 words
4. Include specific project details in answers
5. Cover both conceptual and implementation aspects
6. NO placeholders - provide real, usable answers

IMPORTANT: You MUST output ONLY valid JSON. No markdown, no explanations, no text before or after the JSON.

JSON FORMAT (output exactly this structure):
{
    "section_id": "id",
    "title": "Section Title",
    "content": "Brief introduction to this Q&A section...",
    "qa_pairs": [
        {
            "question": "Full question text?",
            "answer": "Detailed answer with technical content...",
            "follow_up_tips": "Tips for handling follow-up questions..."
        }
    ]
}
"""

    def __init__(self):
        super().__init__(
            name="Chunked Document Generator",
            role="chunked_document_generator",
            capabilities=[
                "large_document_generation",
                "section_by_section_generation",
                "word_document_creation",
                "ppt_creation",
                "60_80_page_documents"
            ]
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Process document generation request.

        Args:
            context: AgentContext with user request and metadata

        Returns:
            Dict with document generation result
        """
        # Extract document type from context
        doc_type_str = context.metadata.get("document_type", "project_report")
        try:
            document_type = DocumentType(doc_type_str)
        except ValueError:
            document_type = DocumentType.PROJECT_REPORT

        project_data = context.metadata.get("project_data", {
            "name": context.metadata.get("project_name", "Project"),
            "description": context.user_request
        })

        # Generate document and collect results
        results = []
        async for event in self.generate_document(context, document_type, project_data):
            results.append(event)

        # Return final result
        return {
            "success": True,
            "document_type": document_type.value,
            "events": results,
            "final_document": results[-1] if results else None
        }

    async def generate_document(
        self,
        context: AgentContext,
        document_type: DocumentType,
        project_data: Dict,
        college_info: Optional[CollegeInfo] = None,
        progress_callback: Optional[callable] = None,
        parallel: bool = True,
        max_retries: int = 3
    ) -> AsyncGenerator[Dict, None]:
        """
        Generate document section by section with progress updates.

        Args:
            context: Agent context
            document_type: Type of document to generate
            project_data: Project data for content generation
            college_info: College information for Certificate, Declaration, Acknowledgement
            progress_callback: Optional callback for progress updates
            parallel: Enable parallel section generation (faster)
            max_retries: Maximum retries for failed sections

        Yields progress events and final document.
        """
        try:
            structure = self.DOCUMENT_STRUCTURES.get(document_type)
            if not structure:
                raise ValueError(f"Unknown document type: {document_type}")

            total_sections = len(structure["sections"])
            generated_sections = []

            # Set project title in college_info if not set
            if college_info and not college_info.project_title:
                college_info.project_title = project_data.get("project_name", "Project")

            logger.info(f"[ChunkedDoc] Starting {document_type.value} generation with {total_sections} sections")
            logger.info(f"[ChunkedDoc] Parallel: {parallel}, Max Retries: {max_retries}")

            # Yield start event
            yield {
                "type": "start",
                "document_type": document_type.value,
                "total_sections": total_sections,
                "estimated_pages": structure.get("estimated_pages", structure.get("estimated_slides", 20)),
                "parallel_enabled": parallel
            }

            # Phase 1: Generate outline for the entire document
            yield {"type": "phase", "phase": "outline", "message": "Generating document outline..."}

            outline = await self._generate_document_outline(
                document_type,
                structure,
                project_data
            )

            yield {"type": "outline_complete", "outline": outline}

            # Phase 2: Generate each section
            yield {"type": "phase", "phase": "content", "message": "Generating section content..."}

            if parallel:
                # Parallel generation for AI sections
                generated_sections = await self._generate_sections_parallel(
                    structure["sections"],
                    outline,
                    project_data,
                    document_type,
                    college_info,
                    max_retries
                )
                yield {
                    "type": "sections_complete",
                    "sections_generated": len(generated_sections),
                    "progress": 100
                }
            else:
                # Sequential generation
                for idx, section in enumerate(structure["sections"]):
                    section_id = section["id"]
                    section_title = section["title"]
                    section_type = section["type"]

                    yield {
                        "type": "section_start",
                        "section_id": section_id,
                        "section_title": section_title,
                        "progress": (idx / total_sections) * 100
                    }

                    content = await self._generate_single_section(
                        section,
                        outline,
                        project_data,
                        document_type,
                        college_info,
                        max_retries
                    )

                    generated_sections.append({
                        "section_id": section_id,
                        "title": section_title,
                        "content": content,
                        "type": section_type
                    })

                    yield {
                        "type": "section_complete",
                        "section_id": section_id,
                        "section_title": section_title,
                        "progress": ((idx + 1) / total_sections) * 100
                    }

                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.5)

            # Phase 3: Generate UML Diagrams
            yield {"type": "phase", "phase": "diagrams", "message": "Generating UML diagrams..."}

            diagrams = await self._generate_all_diagrams(project_data)

            yield {
                "type": "diagrams_complete",
                "diagrams_generated": len(diagrams),
                "diagram_types": list(diagrams.keys())
            }

            # Store diagram paths in project_data for assembly
            project_data["generated_diagrams"] = diagrams

            # Phase 4: Assemble document
            yield {"type": "phase", "phase": "assembly", "message": "Assembling final document..."}

            # Get project_id from context for saving to project docs folder
            project_id = context.project_id if context else None

            if document_type == DocumentType.PPT:
                final_doc = await self._assemble_ppt(generated_sections, project_data, project_id)
            else:
                final_doc = await self._assemble_word_document(
                    generated_sections,
                    project_data,
                    document_type,
                    project_id
                )

            yield {
                "type": "complete",
                "document_type": document_type.value,
                "file_path": final_doc["path"],
                "pages": final_doc.get("pages", 0),
                "sections_generated": len(generated_sections)
            }

        except Exception as e:
            logger.error(f"[ChunkedDoc] Error: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }

    async def _generate_document_outline(
        self,
        document_type: DocumentType,
        structure: Dict,
        project_data: Dict
    ) -> Dict:
        """Generate outline for all sections"""

        prompt = f"""Generate a detailed outline for a {structure['name']}.

PROJECT: {project_data.get('project_name', 'Project')}
TYPE: {project_data.get('project_type', 'Software Project')}

TECHNOLOGIES:
{json.dumps(project_data.get('technologies', {}), indent=2)}

FEATURES:
{json.dumps(project_data.get('features', []), indent=2)}

SECTIONS TO OUTLINE:
{json.dumps([{"id": s["id"], "title": s["title"], "subsections": s.get("subsections", [])} for s in structure["sections"] if s["type"] == "generate"], indent=2)}

Generate outline with key points for each section.
Output JSON with section_id as keys.
"""

        response = await self._call_claude(
            system_prompt=self.OUTLINE_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.3,
            max_tokens=4096
        )

        result = self._parse_json(response)
        if not result:
            logger.warning("[ChunkedDoc] Empty outline, creating default structure")
            result = {"sections": {}}
        return result

    async def _generate_section_content(
        self,
        section: Dict,
        outline: Dict,
        project_data: Dict,
        document_type: DocumentType
    ) -> Dict:
        """Generate content for a single section"""

        section_id = section["id"]
        section_title = section["title"]
        subsections = section.get("subsections", [])
        target_pages = section.get("pages", section.get("slides", 2))

        # Estimate words needed (250 words per page for docs, 50 per slide)
        if document_type == DocumentType.PPT:
            target_words = target_pages * 50
        else:
            target_words = target_pages * 250

        # Use different prompt and system prompt for VIVA_QA
        if document_type == DocumentType.VIVA_QA:
            prompt = f"""Generate comprehensive VIVA Questions and Answers for this section:

SECTION: {section_title}

QUESTIONS TO ANSWER:
{json.dumps(subsections, indent=2)}

PROJECT DATA:
- Name: {project_data.get('project_name')}
- Type: {project_data.get('project_type')}
- Technologies: {json.dumps(project_data.get('technologies', {}))}
- Features: {json.dumps(project_data.get('features', []))}
- API Endpoints: {json.dumps(project_data.get('api_endpoints', [])[:10])}
- Database Tables: {json.dumps(project_data.get('database_tables', []))}

REQUIREMENTS:
1. Generate realistic viva questions that examiners would ask
2. Provide detailed, technical answers (100-200 words each)
3. Include follow-up tips for each question
4. Use project-specific details in answers
5. NO placeholders - provide actual answers
6. Each Q&A should demonstrate deep understanding of the project

Generate Q&A content in JSON format with qa_pairs array.
"""
            system_prompt = self.VIVA_QA_SYSTEM_PROMPT
        else:
            prompt = f"""Generate DETAILED content for this section:

SECTION: {section_title}
TARGET WORDS: {target_words} minimum

SUBSECTIONS TO COVER:
{json.dumps(subsections, indent=2)}

OUTLINE POINTS:
{json.dumps(outline, indent=2)}

PROJECT DATA:
- Name: {project_data.get('project_name')}
- Type: {project_data.get('project_type')}
- Technologies: {json.dumps(project_data.get('technologies', {}))}
- Features: {json.dumps(project_data.get('features', []))}
- API Endpoints: {json.dumps(project_data.get('api_endpoints', [])[:10])}
- Database Tables: {json.dumps(project_data.get('database_tables', []))}

REQUIREMENTS:
1. Write detailed, professional content
2. Include specific technical details from the project
3. Academic writing style
4. Create relevant tables and figures
5. Minimum {target_words} words
6. NO placeholders

Generate complete section content in JSON format.
"""
            system_prompt = self.CONTENT_SYSTEM_PROMPT

        response = await self._call_claude(
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.4,
            max_tokens=8192  # Increased for more detailed content
        )

        logger.info(f"[ChunkedDoc] Raw response length for {section_id}: {len(response) if response else 0} chars")

        result = self._parse_json(response, section_info=section)

        # Validate content was generated
        if not result.get("content") and not result.get("subsections") and not result.get("qa_pairs"):
            logger.warning(f"[ChunkedDoc] Empty content for section {section_id}, using fallback")
            result = self._create_fallback_content(section)

        return result

    def _get_template_content(self, section_id: str, project_data: Dict, college_info: Optional[CollegeInfo] = None) -> Dict:
        """Get pre-defined template content with college information"""

        # Use college_info if provided, otherwise use defaults from project_data
        if college_info:
            ci = college_info
        else:
            ci = CollegeInfo(
                college_name=project_data.get("institution", "University Name"),
                department=project_data.get("department", "Computer Science"),
                guide_name=project_data.get("guide", "Guide Name"),
                project_title=project_data.get("project_name", "Project")
            )

        # Format student list for display
        student_names = [s.get("name", "Student") for s in ci.students]
        student_list_formatted = "\n".join([
            f"{i+1}. {s.get('name', 'Student')} ({s.get('roll_number', '')})"
            for i, s in enumerate(ci.students)
        ])

        templates = {
            "cover": {
                "type": "cover_page",
                "project_name": ci.project_title,
                "subtitle": project_data.get("project_type", "Software Project"),
                "college_name": ci.college_name,
                "affiliated_to": ci.affiliated_to,
                "college_address": ci.college_address,
                "department": ci.department,
                "academic_year": ci.academic_year,
                "students": ci.students,
                "guide_name": ci.guide_name,
                "date": ci.date
            },
            "certificate": {
                "type": "certificate",
                "college_name": ci.college_name,
                "affiliated_to": ci.affiliated_to,
                "college_address": ci.college_address,
                "department": ci.department,
                "project_title": ci.project_title,
                "academic_year": ci.academic_year,
                "students": ci.students,
                "guide_name": ci.guide_name,
                "hod_name": ci.hod_name,
                "principal_name": ci.principal_name,
                "date": ci.date,
                "content": f"""
This is to certify that the project entitled "{ci.project_title}" is a bonafide work
carried out by the following students:

{student_list_formatted}

in partial fulfillment of the requirements for the award of Bachelor of Technology
in Computer Science and Engineering from {ci.college_name} during the academic year {ci.academic_year}.

This project work has been approved as it satisfies the academic requirements prescribed
for the said degree.


Project Guide                    Head of Department                    Principal
{ci.guide_name}                  {ci.hod_name}                         {ci.principal_name}

Signature: ____________          Signature: ____________               Signature: ____________
Date: ____________               Date: ____________                    Date: ____________


External Examiner
Name: ________________________
Signature: ____________________
Date: ________________________
"""
            },
            "declaration": {
                "type": "declaration",
                "college_name": ci.college_name,
                "department": ci.department,
                "project_title": ci.project_title,
                "guide_name": ci.guide_name,
                "students": ci.students,
                "date": ci.date,
                "content": f"""
DECLARATION

We, the undersigned, hereby declare that the project entitled "{ci.project_title}"
submitted to {ci.college_name}, {ci.department}, is a record of an original work done
by us under the guidance of {ci.guide_name}.

This project work is submitted in partial fulfillment of the requirements for the award
of the degree of Bachelor of Technology in Computer Science and Engineering.

We further declare that:

1. This project is based on our original work.
2. This project has not been submitted previously for any degree or examination in any other university.
3. All sources of information have been duly acknowledged.
4. We have followed the guidelines provided by the institute for preparing this report.


Student Signatures:

{chr(10).join([f"{s.get('name', 'Student'):30} {s.get('roll_number', ''):15} ________________" for s in ci.students])}


Date: {ci.date}
Place: {ci.college_name}
"""
            },
            "acknowledgement": {
                "type": "acknowledgement",
                "guide_name": ci.guide_name,
                "hod_name": ci.hod_name,
                "principal_name": ci.principal_name,
                "college_name": ci.college_name,
                "department": ci.department,
                "students": ci.students,
                "date": ci.date,
                "content": f"""
ACKNOWLEDGEMENT

We take this opportunity to express our profound gratitude and deep regards to our
project guide {ci.guide_name} for the exemplary guidance, monitoring, and constant
encouragement throughout the course of this project.

We would like to express our sincere thanks to {ci.hod_name}, Head of Department,
{ci.department}, for providing us with the opportunity to work on this project.

We also express our sincere gratitude to {ci.principal_name}, Principal, {ci.college_name},
for providing us with the necessary facilities and support.

We extend our heartfelt thanks to all the faculty members of the {ci.department}
for their valuable suggestions and support during the development of this project.

We would also like to thank our family and friends for their constant support and encouragement.

Finally, we thank all those who directly or indirectly helped us in the successful
completion of this project.


Team Members:
{chr(10).join([f"{i+1}. {s.get('name', 'Student')}" for i, s in enumerate(ci.students)])}


Date: {ci.date}
Place: {ci.college_name}
"""
            },
            "title": {
                "type": "title_slide",
                "project_name": ci.project_title,
                "subtitle": project_data.get("project_type", "Software Project"),
                "college_name": ci.college_name,
                "department": ci.department,
                "presented_by": student_names,
                "guide_name": ci.guide_name,
                "academic_year": ci.academic_year
            },
            "thankyou": {
                "type": "thankyou_slide",
                "message": "Thank You!",
                "college_name": ci.college_name,
                "presented_by": student_names,
                "contact": project_data.get("email", "")
            }
        }

        return templates.get(section_id, {"type": "template", "content": ""})

    def _get_code_content(self, section_id: str, project_data: Dict) -> Dict:
        """Get code snippets from project"""

        code_files = project_data.get("code_files", [])

        # Select representative files
        selected_code = []
        for file in code_files[:5]:  # Limit to 5 files
            selected_code.append({
                "filename": file.get("path", ""),
                "language": file.get("language", ""),
                "content": file.get("content", "")[:2000]  # Truncate long files
            })

        return {
            "type": "code_appendix",
            "files": selected_code
        }

    async def _assemble_word_document(
        self,
        sections: List[Dict],
        project_data: Dict,
        document_type: DocumentType,
        project_id: str = None
    ) -> Dict:
        """Assemble sections into Word document using python-docx"""

        from app.modules.automation.word_generator import WordDocumentGenerator

        generator = WordDocumentGenerator()

        file_path = await generator.create_document(
            sections=sections,
            project_data=project_data,
            document_type=document_type.value,
            project_id=project_id
        )

        return {
            "path": file_path,
            "format": "docx",
            "pages": sum(s.get("pages", 2) for s in sections if isinstance(s, dict))
        }

    async def _assemble_ppt(
        self,
        sections: List[Dict],
        project_data: Dict,
        project_id: str = None
    ) -> Dict:
        """Assemble sections into PowerPoint"""

        from app.modules.automation.ppt_generator_v2 import PPTGeneratorV2

        generator = PPTGeneratorV2()

        file_path = await generator.create_presentation(
            sections=sections,
            project_data=project_data,
            project_id=project_id
        )

        return {
            "path": file_path,
            "format": "pptx",
            "slides": sum(s.get("slides", 1) for s in sections if isinstance(s, dict))
        }

    def _parse_json(self, response: str, section_info: Optional[Dict] = None) -> Dict:
        """
        Parse JSON from Claude response with multiple fallback strategies.

        Args:
            response: The raw response from Claude
            section_info: Optional section metadata for fallback content generation

        Returns:
            Parsed JSON dict, or fallback content if parsing fails
        """
        import re

        if not response or not response.strip():
            logger.warning("[ChunkedDoc] Empty response received")
            return self._create_fallback_content(section_info)

        # Strategy 1: Try direct JSON parsing
        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            pass

        # Strategy 2: Find JSON between first { and last }
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Strategy 3: Try to find JSON in code blocks
        try:
            json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', response)
            if json_match:
                return json.loads(json_match.group(1))
        except (json.JSONDecodeError, AttributeError):
            pass

        # Strategy 4: Fix common JSON issues and retry
        try:
            # Get the JSON portion
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                # Fix common issues
                json_str = json_str.replace('\n', ' ')
                json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                json_str = re.sub(r',\s*]', ']', json_str)  # Remove trailing commas in arrays
                json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)  # Remove control chars
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Strategy 5: Extract content directly from text as fallback
        logger.warning("[ChunkedDoc] JSON parsing failed, extracting content from raw text")
        return self._extract_content_from_text(response, section_info)

    def _create_fallback_content(self, section_info: Optional[Dict] = None) -> Dict:
        """Create fallback content structure when parsing fails completely."""
        section_id = section_info.get("id", "section") if section_info else "section"
        title = section_info.get("title", "Section") if section_info else "Section"

        return {
            "section_id": section_id,
            "title": title,
            "content": f"This section covers {title}. The content provides a comprehensive overview of the relevant topics and concepts.",
            "subsections": [],
            "fallback": True
        }

    def _extract_content_from_text(self, response: str, section_info: Optional[Dict] = None) -> Dict:
        """
        Extract meaningful content from non-JSON response.

        This attempts to salvage useful content even when JSON parsing fails.
        """
        import re

        section_id = section_info.get("id", "section") if section_info else "section"
        title = section_info.get("title", "Section") if section_info else "Section"

        # Clean up the response
        text = response.strip()

        # Remove JSON artifacts and code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'^\s*\{[\s\S]*', '', text)  # Remove JSON at start
        text = re.sub(r'[\s\S]*\}\s*$', '', text)  # Remove JSON at end

        # If we have useful text content, use it
        if len(text.strip()) > 100:
            # Split into paragraphs
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]

            if paragraphs:
                main_content = paragraphs[0] if len(paragraphs[0]) > 50 else ' '.join(paragraphs[:2])

                subsections = []
                for i, para in enumerate(paragraphs[1:5], 1):  # Take up to 4 more paragraphs as subsections
                    if len(para) > 50:
                        subsections.append({
                            "id": f"{section_id}.{i}",
                            "title": f"Section {section_id}.{i}",
                            "content": para
                        })

                return {
                    "section_id": section_id,
                    "title": title,
                    "content": main_content,
                    "subsections": subsections,
                    "extracted_from_text": True
                }

        # Ultimate fallback
        return self._create_fallback_content(section_info)

    async def _generate_sections_parallel(
        self,
        sections: List[Dict],
        outline: Dict,
        project_data: Dict,
        document_type: DocumentType,
        college_info: Optional[CollegeInfo],
        max_retries: int
    ) -> List[Dict]:
        """
        Generate multiple sections in parallel for faster document generation.

        Sections are grouped by type:
        - Template sections: Generated immediately (no API call)
        - AI sections: Generated in parallel batches of 3
        """
        generated_sections = []

        # Separate sections by type
        template_sections = []
        ai_sections = []
        auto_sections = []
        code_sections = []

        for section in sections:
            section_type = section.get("type", "generate")
            if section_type == "template":
                template_sections.append(section)
            elif section_type == "auto":
                auto_sections.append(section)
            elif section_type == "code":
                code_sections.append(section)
            else:
                ai_sections.append(section)

        logger.info(f"[ChunkedDoc] Parallel: {len(template_sections)} templates, {len(ai_sections)} AI sections")

        # 1. Generate template sections immediately (no API call)
        for section in template_sections:
            content = self._get_template_content(section["id"], project_data, college_info)
            generated_sections.append({
                "section_id": section["id"],
                "title": section["title"],
                "content": content,
                "type": "template"
            })

        # 2. Generate auto sections
        for section in auto_sections:
            generated_sections.append({
                "section_id": section["id"],
                "title": section["title"],
                "content": {"type": "auto", "section_id": section["id"]},
                "type": "auto"
            })

        # 3. Generate code sections
        for section in code_sections:
            content = self._get_code_content(section["id"], project_data)
            generated_sections.append({
                "section_id": section["id"],
                "title": section["title"],
                "content": content,
                "type": "code"
            })

        # 4. Generate AI sections in parallel batches
        BATCH_SIZE = 3  # Process 3 sections at a time to avoid rate limits

        for i in range(0, len(ai_sections), BATCH_SIZE):
            batch = ai_sections[i:i + BATCH_SIZE]

            # Create tasks for parallel execution
            tasks = [
                self._generate_single_section_with_retry(
                    section,
                    outline,
                    project_data,
                    document_type,
                    college_info,
                    max_retries
                )
                for section in batch
            ]

            # Execute batch in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for section, result in zip(batch, results):
                if isinstance(result, Exception):
                    logger.error(f"[ChunkedDoc] Section {section['id']} failed: {result}")
                    content = {"error": str(result), "fallback": True}
                else:
                    content = result

                generated_sections.append({
                    "section_id": section["id"],
                    "title": section["title"],
                    "content": content,
                    "type": "generate"
                })

            # Small delay between batches to avoid rate limiting
            if i + BATCH_SIZE < len(ai_sections):
                await asyncio.sleep(1.0)

        # Sort sections by original order
        section_order = {s["id"]: idx for idx, s in enumerate(sections)}
        generated_sections.sort(key=lambda x: section_order.get(x["section_id"], 999))

        return generated_sections

    async def _generate_single_section(
        self,
        section: Dict,
        outline: Dict,
        project_data: Dict,
        document_type: DocumentType,
        college_info: Optional[CollegeInfo],
        max_retries: int
    ) -> Dict:
        """Generate a single section with appropriate method based on type."""
        section_type = section.get("type", "generate")

        if section_type == "template":
            return self._get_template_content(section["id"], project_data, college_info)
        elif section_type == "auto":
            return {"type": "auto", "section_id": section["id"]}
        elif section_type == "code":
            return self._get_code_content(section["id"], project_data)
        else:
            return await self._generate_single_section_with_retry(
                section, outline, project_data, document_type, college_info, max_retries
            )

    async def _generate_single_section_with_retry(
        self,
        section: Dict,
        outline: Dict,
        project_data: Dict,
        document_type: DocumentType,
        college_info: Optional[CollegeInfo],
        max_retries: int
    ) -> Dict:
        """
        Generate a single section with retry logic.

        Retries with exponential backoff on failure.
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                content = await self._generate_section_content(
                    section,
                    outline.get(section["id"], {}),
                    project_data,
                    document_type
                )

                if content and not content.get("error"):
                    return content

            except Exception as e:
                last_error = e
                wait_time = (2 ** attempt) + 0.5  # Exponential backoff: 1.5s, 2.5s, 4.5s
                logger.warning(
                    f"[ChunkedDoc] Section {section['id']} attempt {attempt + 1}/{max_retries} failed: {e}"
                )

                if attempt < max_retries - 1:
                    logger.info(f"[ChunkedDoc] Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)

        # All retries failed - return fallback content
        logger.error(f"[ChunkedDoc] Section {section['id']} failed after {max_retries} attempts")
        return {
            "error": str(last_error) if last_error else "Generation failed",
            "fallback": True,
            "section_id": section["id"],
            "title": section["title"],
            "content": f"[Content generation failed for {section['title']}. Please regenerate this section.]"
        }

    async def _generate_all_diagrams(self, project_data: Dict) -> Dict[str, str]:
        """
        Generate all UML diagrams for the document.

        Returns:
            Dict mapping diagram type to file path
        """
        diagrams = {}

        try:
            project_name = project_data.get('project_name', 'System')
            features = project_data.get('features', [])
            database_tables = project_data.get('database_tables', [])

            logger.info(f"[ChunkedDoc] Generating UML diagrams for {project_name}")

            # 1. Use Case Diagram
            try:
                actors = ['User', 'Admin']
                if 'authentication' in str(features).lower():
                    actors.append('Guest')
                use_cases = features[:8] if features else ['Login', 'Register', 'View Dashboard', 'Manage Data']

                diagrams['use_case'] = uml_generator.generate_use_case_diagram(
                    project_name=project_name,
                    actors=actors,
                    use_cases=use_cases
                )
                logger.info("[ChunkedDoc] Generated Use Case Diagram")
            except Exception as e:
                logger.error(f"[ChunkedDoc] Use Case Diagram error: {e}")

            # 2. Class Diagram
            try:
                classes = self._extract_classes_for_diagram(project_data)
                diagrams['class'] = uml_generator.generate_class_diagram(classes)
                logger.info("[ChunkedDoc] Generated Class Diagram")
            except Exception as e:
                logger.error(f"[ChunkedDoc] Class Diagram error: {e}")

            # 3. Sequence Diagram
            try:
                participants = ['User', 'Frontend', 'API', 'Database']
                messages = [
                    {'from': 'User', 'to': 'Frontend', 'message': 'Submit Request'},
                    {'from': 'Frontend', 'to': 'API', 'message': 'API Call'},
                    {'from': 'API', 'to': 'Database', 'message': 'Query'},
                    {'from': 'Database', 'to': 'API', 'message': 'Result', 'type': 'return'},
                    {'from': 'API', 'to': 'Frontend', 'message': 'Response', 'type': 'return'},
                    {'from': 'Frontend', 'to': 'User', 'message': 'Display', 'type': 'return'},
                ]
                diagrams['sequence'] = uml_generator.generate_sequence_diagram(participants, messages)
                logger.info("[ChunkedDoc] Generated Sequence Diagram")
            except Exception as e:
                logger.error(f"[ChunkedDoc] Sequence Diagram error: {e}")

            # 4. Activity Diagram
            try:
                activities = [
                    'Start Application',
                    'User Authentication',
                    'Load Dashboard',
                    'Process User Request',
                    'Update Database',
                    'Return Response'
                ]
                diagrams['activity'] = uml_generator.generate_activity_diagram(activities)
                logger.info("[ChunkedDoc] Generated Activity Diagram")
            except Exception as e:
                logger.error(f"[ChunkedDoc] Activity Diagram error: {e}")

            # 5. ER Diagram
            try:
                entities = self._extract_entities_for_diagram(project_data)
                diagrams['er'] = uml_generator.generate_er_diagram(entities)
                logger.info("[ChunkedDoc] Generated ER Diagram")
            except Exception as e:
                logger.error(f"[ChunkedDoc] ER Diagram error: {e}")

            # 6. DFD Level 0
            try:
                diagrams['dfd_0'] = uml_generator.generate_dfd(
                    level=0,
                    processes=[project_name],
                    data_stores=['Database'],
                    external_entities=['User', 'Admin'],
                    data_flows=[
                        {'from': 'User', 'to': project_name, 'data': 'Request'},
                        {'from': project_name, 'to': 'User', 'data': 'Response'},
                        {'from': project_name, 'to': 'Database', 'data': 'Query'},
                    ]
                )
                logger.info("[ChunkedDoc] Generated DFD Level 0")
            except Exception as e:
                logger.error(f"[ChunkedDoc] DFD error: {e}")

            logger.info(f"[ChunkedDoc] Generated {len(diagrams)} UML diagrams")

        except Exception as e:
            logger.error(f"[ChunkedDoc] Error generating diagrams: {e}")

        return diagrams

    def _extract_classes_for_diagram(self, project_data: Dict) -> List[Dict]:
        """Extract class information for class diagram"""
        classes = []

        tables = project_data.get('database_tables', [])
        for table in tables[:5]:
            classes.append({
                'name': table.title() if isinstance(table, str) else table.get('name', 'Entity'),
                'attributes': ['id', 'name', 'created_at', 'updated_at'],
                'methods': ['create', 'read', 'update', 'delete'],
                'relationships': []
            })

        if not classes:
            classes = [
                {
                    'name': 'User',
                    'attributes': ['id', 'name', 'email', 'password'],
                    'methods': ['login', 'logout', 'register'],
                    'relationships': []
                },
                {
                    'name': 'Controller',
                    'attributes': ['routes', 'middleware'],
                    'methods': ['handleRequest', 'validateInput'],
                    'relationships': [{'target': 'Service', 'type': 'association'}]
                },
                {
                    'name': 'Service',
                    'attributes': ['repository'],
                    'methods': ['processData', 'validateBusiness'],
                    'relationships': [{'target': 'Repository', 'type': 'association'}]
                },
                {
                    'name': 'Repository',
                    'attributes': ['database'],
                    'methods': ['find', 'save', 'delete'],
                    'relationships': []
                }
            ]

        return classes

    def _extract_entities_for_diagram(self, project_data: Dict) -> List[Dict]:
        """Extract entity information for ER diagram"""
        entities = []

        tables = project_data.get('database_tables', [])
        for table in tables[:6]:
            name = table if isinstance(table, str) else table.get('name', 'Entity')
            entities.append({
                'name': name,
                'attributes': ['id', 'name', 'description', 'created_at', 'updated_at'],
                'primary_key': 'id'
            })

        if not entities:
            entities = [
                {'name': 'User', 'attributes': ['id', 'name', 'email', 'password_hash'], 'primary_key': 'id'},
                {'name': 'Project', 'attributes': ['id', 'title', 'description', 'user_id'], 'primary_key': 'id'},
                {'name': 'Document', 'attributes': ['id', 'name', 'content', 'project_id'], 'primary_key': 'id'},
            ]

        return entities


# Singleton instance
chunked_document_agent = ChunkedDocumentAgent()
