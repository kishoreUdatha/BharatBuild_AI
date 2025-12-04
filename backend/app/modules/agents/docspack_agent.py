"""
AGENT 5 — DOCSPACK AGENT (Documentation Generator)

Generates documentation for ALL project types:
- Academic: SRS, UML, Reports, PPT, Viva questions
- Standard: README, API docs, Architecture docs

Output format: <file path="...">content</file>
"""

from typing import Dict, Any, List, Optional
from app.utils.claude_client import ClaudeClient
from pathlib import Path
import json


class DocsPackAgent:
    """
    Document Pack Agent for generating documentation for all project types.
    Supports both academic (full IEEE docs) and standard (dev docs) modes.
    """

    def __init__(self, model: str = "sonnet"):
        self.claude_client = ClaudeClient()
        self.model = model

    async def generate_documents(self, project_analysis: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all academic documents based on project analysis.

        Args:
            project_analysis: Dict containing:
                - project_name: str
                - project_purpose: str
                - technology_stack: Dict
                - architecture: str
                - database_schema: Dict
                - modules: List[Dict]
                - features: List[str]
                - file_structure: Dict

        Returns:
            Dict with keys: abstract, srs, uml, erd, report, ppt_slides, viva, output_explanation
        """

        system_prompt = """You are the DOCUMENT PACK AGENT.

Your job:
Generate all academic documents required for a B.Tech/MCA/M.Tech student based on the project.

OUTPUT FORMAT:
<documents>
  <abstract>...</abstract>
  <srs>...</srs>
  <uml>...</uml>
  <erd>...</erd>
  <report>...</report>
  <ppt_slides>...</ppt_slides>
  <viva>...</viva>
  <output_explanation>...</output_explanation>
</documents>

Rules:
- No code.
- No file paths.
- Make content clean, detailed, and academic-standard.
- Use the provided project analysis to generate contextual, accurate documentation.
- All documents should be consistent with each other.
- SRS must be IEEE 830-1998 compliant.
- UML diagrams in Mermaid format.
- Report must be 30+ pages with proper chapters.
- PPT should have 15-18 slides.
- Viva should have 25+ questions with detailed answers.
"""

        user_prompt = f"""Based on the following project analysis, generate complete academic documentation:

# PROJECT ANALYSIS

## Project Name
{project_analysis.get('project_name', 'Unnamed Project')}

## Project Purpose
{project_analysis.get('project_purpose', 'Not specified')}

## Domain
{project_analysis.get('domain', 'Software Engineering')}

## Technology Stack
### Backend
{json.dumps(project_analysis.get('technology_stack', {}).get('backend', {}), indent=2)}

### Frontend
{json.dumps(project_analysis.get('technology_stack', {}).get('frontend', {}), indent=2)}

### Database
{json.dumps(project_analysis.get('technology_stack', {}).get('database', {}), indent=2)}

## System Architecture
{project_analysis.get('architecture', 'Not specified')}

## Database Schema
{json.dumps(project_analysis.get('database_schema', {}), indent=2)}

## Key Modules
{json.dumps(project_analysis.get('modules', []), indent=2)}

## Main Features
{chr(10).join(f"- {feature}" for feature in project_analysis.get('features', []))}

## File Structure Overview
{json.dumps(project_analysis.get('file_structure', {}), indent=2)}

---

Generate complete academic documentation following the OUTPUT FORMAT specified in the system prompt.

Make sure:
1. Abstract includes background, problem statement, objectives, methodology, results, conclusion
2. SRS has functional requirements (FR-001 to FR-050), non-functional requirements, use cases
3. UML includes Class Diagram, Sequence Diagram, ER Diagram, Use Case Diagram (all in Mermaid)
4. ER Diagram has detailed table descriptions with relationships
5. Report has 8 chapters: Intro, Literature, Analysis, Design, Implementation, Testing, Results, Conclusion
6. PPT has 15-18 slides with proper structure
7. Viva has 25+ Q&A across categories
8. Output explanation has how to run, setup, deploy instructions
"""

        # Call Claude API
        response = await self.claude_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            max_tokens=16000,  # Large token limit for comprehensive output
            temperature=0.7
        )

        # Parse XML response
        documents = self._parse_documents(response['content'][0]['text'])

        return documents

    def _parse_documents(self, xml_content: str) -> Dict[str, str]:
        """
        Parse XML formatted document output from Claude.

        Args:
            xml_content: XML string with <documents> root

        Returns:
            Dict with document types as keys
        """
        import re

        documents = {}

        # Extract each document type using regex
        doc_types = [
            'abstract',
            'srs',
            'uml',
            'erd',
            'report',
            'ppt_slides',
            'viva',
            'output_explanation'
        ]

        for doc_type in doc_types:
            pattern = f'<{doc_type}>(.*?)</{doc_type}>'
            match = re.search(pattern, xml_content, re.DOTALL)
            if match:
                documents[doc_type] = match.group(1).strip()
            else:
                documents[doc_type] = f"Error: {doc_type} not generated"

        return documents

    async def generate_abstract(self, project_analysis: Dict[str, Any]) -> str:
        """Generate only Abstract (faster, for preview)"""

        prompt = f"""Generate an academic abstract (3-4 pages) for this project:

Project: {project_analysis.get('project_name')}
Purpose: {project_analysis.get('project_purpose')}
Tech Stack: {json.dumps(project_analysis.get('technology_stack', {}), indent=2)}

Include:
1. Background and context
2. Problem statement
3. Objectives
4. Methodology
5. Key results
6. Conclusion
7. Keywords

Format in Markdown. Be detailed and academic-standard."""

        response = await self.claude_client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=2000
        )

        return response['content'][0]['text']

    async def generate_srs(self, project_analysis: Dict[str, Any]) -> str:
        """Generate only SRS Document"""

        prompt = f"""Generate an IEEE 830-1998 compliant Software Requirements Specification for:

Project: {project_analysis.get('project_name')}
Purpose: {project_analysis.get('project_purpose')}
Features: {json.dumps(project_analysis.get('features', []))}
Architecture: {project_analysis.get('architecture')}

Include:
1. Introduction (Purpose, Scope, Definitions, References)
2. Overall Description (Product Perspective, Functions, Users, Constraints)
3. Specific Requirements:
   - Functional Requirements (FR-001 to FR-050 minimum)
   - Non-Functional Requirements (Performance, Security, Usability)
   - External Interface Requirements
4. System Models (Use Cases, DFD)

Format in Markdown. Be comprehensive (20+ pages)."""

        response = await self.claude_client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=8000
        )

        return response['content'][0]['text']

    async def generate_uml(self, project_analysis: Dict[str, Any]) -> str:
        """Generate UML Diagrams in Mermaid format"""

        database_info = json.dumps(project_analysis.get('database_schema', {}), indent=2)
        modules_info = json.dumps(project_analysis.get('modules', []), indent=2)

        prompt = f"""Generate UML diagrams in Mermaid format for:

Project: {project_analysis.get('project_name')}
Database: {database_info}
Modules: {modules_info}

Generate these diagrams:
1. Class Diagram (showing all main classes and relationships)
2. Sequence Diagram (for a key workflow like user authentication or main feature)
3. ER Diagram (complete database schema)
4. Use Case Diagram (all actors and use cases)
5. Component Diagram (system architecture)

Format each diagram in Mermaid syntax with proper titles and explanations."""

        response = await self.claude_client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=4000
        )

        return response['content'][0]['text']

    async def generate_viva_qa(self, project_analysis: Dict[str, Any]) -> str:
        """Generate Viva Questions and Answers"""

        prompt = f"""Generate 25+ viva voce questions and detailed answers for:

Project: {project_analysis.get('project_name')}
Tech Stack: {json.dumps(project_analysis.get('technology_stack', {}))}
Features: {json.dumps(project_analysis.get('features', []))}

Categories:
1. Project Overview (5 questions)
2. Architecture & Design (5 questions)
3. Technology Stack (5 questions)
4. Implementation (5 questions)
5. Testing & Quality (3 questions)
6. Security (3 questions)
7. Future Scope (2 questions)

For each question, provide:
- Clear question
- Detailed 2-3 paragraph answer with technical depth
- Code examples where relevant

Format in Markdown with clear sections."""

        response = await self.claude_client.generate(
            prompt=prompt,
            model=self.model,
            max_tokens=6000
        )

        return response['content'][0]['text']

    async def generate_all_documents(
        self,
        plan: str,
        project_id: str,
        files: List[Dict[str, Any]],
        doc_type: str = "academic"
    ) -> Dict[str, Any]:
        """
        Generate all documentation based on project plan and files.

        Args:
            plan: Raw plan text from planner
            project_id: Project identifier
            files: List of files created
            doc_type: "academic" or "standard"

        Returns:
            Dict with response containing <file> tags
        """
        # Build file summary
        file_summary = "\n".join([
            f"- {f.get('path', 'unknown')}: {f.get('type', 'file')}"
            for f in files[:50]  # Limit to 50 files
        ])

        # Load appropriate prompt
        prompt_file = "documenter.txt"
        prompt_path = Path(__file__).parent.parent.parent / "config" / "prompts" / prompt_file

        system_prompt = ""
        if prompt_path.exists():
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()
        else:
            system_prompt = self._get_default_system_prompt(doc_type)

        # Build user prompt based on doc type
        # NOTE: Use paths that match planner.txt (lines 306-309):
        # - docs/SRS.md (Software Requirements Specification)
        # - docs/ARCHITECTURE.md (System architecture)
        # - docs/USER_MANUAL.md (How to use)
        # - README.md (Project overview)

        if doc_type == "academic":
            user_prompt = f"""Generate COMPLETE academic documentation for this project.

PROJECT ID: {project_id}

PROJECT PLAN:
{plan[:8000]}

FILES CREATED ({len(files)} files):
{file_summary}

OUTPUT REQUIRED - Generate ALL these files (matching project structure from planner):

<file path="README.md">
# Project Overview
- Project description, features, tech stack
- Quick start guide
- Installation instructions
- Usage examples
- License and credits
</file>

<file path="docs/SRS.md">
# Software Requirements Specification (IEEE 830-1998)
- Introduction (Purpose, Scope, Definitions)
- Overall Description (Product Perspective, Functions, User Characteristics)
- Functional Requirements (30+ requirements with FR-001 to FR-030)
- Non-Functional Requirements (15+ requirements)
- External Interface Requirements
</file>

<file path="docs/ARCHITECTURE.md">
# System Architecture
- High-level architecture diagram (Mermaid)
- Component descriptions
- Data flow diagrams
- Database schema (ER diagram in Mermaid)
- API architecture
</file>

<file path="docs/USER_MANUAL.md">
# User Manual
- Getting Started
- Feature walkthrough with screenshots descriptions
- Troubleshooting guide
- FAQ
</file>

<file path="docs/UML_DIAGRAMS.md">
# UML Diagrams
All diagrams in Mermaid format:
- Use Case Diagram
- Class Diagram
- Sequence Diagram
- Activity Diagram
- ER Diagram
</file>

<file path="docs/VIVA_QUESTIONS.md">
# Viva Questions & Answers
25+ questions with detailed answers covering:
- Project overview
- Architecture & Design
- Technology Stack
- Implementation details
- Testing & Quality
- Future scope
</file>

Generate COMPLETE content for EACH file. No placeholders. Use Mermaid syntax for ALL diagrams."""
        else:
            # Standard developer documentation
            user_prompt = f"""Generate developer documentation for this project.

PROJECT ID: {project_id}

PROJECT PLAN:
{plan[:8000]}

FILES CREATED ({len(files)} files):
{file_summary}

OUTPUT REQUIRED - Generate ALL these files (matching project structure from planner):

<file path="README.md">
# Project Name
- Project description with badges
- Features list
- Tech stack
- Quick start guide
- Installation instructions
- Usage examples with code
- API overview
- Configuration
- Deployment
- Contributing
- License
</file>

<file path="docs/SRS.md">
# Software Requirements Specification
- Introduction
- Functional Requirements
- Non-Functional Requirements
- System Constraints
</file>

<file path="docs/ARCHITECTURE.md">
# System Architecture
- High-level architecture diagram (ASCII or Mermaid)
- Component descriptions
- Data flow
- Database design
- API design
</file>

<file path="docs/USER_MANUAL.md">
# User Manual
- Getting Started
- Features
- Usage Guide
- Troubleshooting
</file>

<file path="docs/API_REFERENCE.md">
# API Reference
- Authentication
- Endpoints with request/response examples
- Error codes
- Rate limits
</file>

Generate COMPLETE content for EACH file. No placeholders."""

        # Call Claude
        response = await self.claude_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            max_tokens=16000,
            temperature=0.7
        )

        # Handle different response formats
        if isinstance(response, dict):
            if 'content' in response and isinstance(response['content'], list):
                content = response['content'][0].get('text', '')
            else:
                content = response.get('content', '')
        else:
            content = str(response)

        return {"response": content}

    def _get_default_system_prompt(self, doc_type: str) -> str:
        """Fallback system prompt if file not found"""
        if doc_type == "academic":
            return """You are an academic documentation generator.
Generate IEEE-standard documentation for student projects.
Output files using <file path="...">content</file> format."""
        else:
            return """You are a developer documentation generator.
Generate clean, professional documentation for software projects.
Output files using <file path="...">content</file> format."""


# Example usage
async def example_usage():
    """
    Example of how to use DocsPackAgent
    """

    # Project analysis from exploration
    project_analysis = {
        "project_name": "E-Commerce Platform",
        "project_purpose": "Online shopping platform with payment integration",
        "domain": "E-Commerce / Web Application",
        "technology_stack": {
            "backend": {
                "framework": "FastAPI",
                "language": "Python 3.11",
                "database": "PostgreSQL 15",
                "cache": "Redis 7"
            },
            "frontend": {
                "framework": "Next.js 14",
                "language": "TypeScript 5",
                "styling": "Tailwind CSS 3"
            },
            "database": {
                "primary": "PostgreSQL 15",
                "cache": "Redis 7"
            }
        },
        "architecture": "Microservices-oriented with layered architecture (Frontend, API Gateway, Backend, Database)",
        "database_schema": {
            "tables": ["users", "products", "orders", "payments", "cart"],
            "relationships": {
                "users_orders": "1:N",
                "orders_products": "N:M",
                "users_cart": "1:1"
            }
        },
        "modules": [
            {"name": "Authentication", "description": "User login, registration, JWT"},
            {"name": "Product Catalog", "description": "Browse products, search, filter"},
            {"name": "Shopping Cart", "description": "Add to cart, update quantities"},
            {"name": "Checkout", "description": "Order placement, payment processing"},
            {"name": "Admin Panel", "description": "Manage products, orders, users"}
        ],
        "features": [
            "User registration and authentication",
            "Product catalog with search and filters",
            "Shopping cart management",
            "Secure payment processing (Razorpay)",
            "Order tracking",
            "Admin dashboard",
            "Email notifications"
        ],
        "file_structure": {
            "backend": ["app/api/", "app/models/", "app/core/"],
            "frontend": ["src/app/", "src/components/", "src/lib/"]
        }
    }

    # Initialize agent
    agent = DocsPackAgent()

    # Generate all documents
    documents = await agent.generate_documents(project_analysis)

    # Save to files
    import os

    output_dir = "academic_documents"
    os.makedirs(output_dir, exist_ok=True)

    file_mapping = {
        "abstract": "01_ABSTRACT.md",
        "srs": "02_SRS_DOCUMENT.md",
        "uml": "03_UML_DIAGRAMS.md",
        "erd": "04_ER_DIAGRAM.md",
        "report": "05_PROJECT_REPORT.md",
        "ppt_slides": "06_PPT_SLIDES.md",
        "viva": "07_VIVA_QUESTIONS.md",
        "output_explanation": "08_OUTPUT_EXPLANATION.md"
    }

    for doc_type, filename in file_mapping.items():
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(documents[doc_type])
        print(f"✅ Generated: {filename}")

    print(f"\n📦 All documents generated in '{output_dir}/' directory")

    return documents
