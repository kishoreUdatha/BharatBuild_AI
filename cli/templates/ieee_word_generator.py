"""
IEEE Word/PDF Document Generator

Generates professional IEEE-standard documents with:
- Word (.docx) format with proper formatting
- PDF format
- UML diagrams (Use Case, Class, Sequence, ER)
- Images and figures
- Table of Contents
- Professional cover page
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from cli.templates.ieee_templates import ProjectInfo, IEEE_TEMPLATES
from cli.templates.document_generator import (
    WordDocumentGenerator,
    PDFDocumentGenerator,
    UMLGenerator,
    DocumentStyle,
    check_dependencies,
    DOCX_AVAILABLE,
    PDF_AVAILABLE
)


class IEEEWordGenerator:
    """Generate IEEE-standard Word documents"""

    def __init__(self, project_info: ProjectInfo, output_dir: str = "docs"):
        self.project_info = project_info
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.diagrams_dir = self.output_dir / "diagrams"
        self.diagrams_dir.mkdir(exist_ok=True)

        if not DOCX_AVAILABLE:
            raise ImportError(
                "python-docx is required for Word generation. "
                "Install with: pip install python-docx"
            )

        self.style = DocumentStyle()
        self.uml = UMLGenerator()

    def generate_srs(self,
                     functional_requirements: List[Dict] = None,
                     non_functional_requirements: List[Dict] = None,
                     use_cases: List[str] = None,
                     actors: List[str] = None,
                     include_diagrams: bool = True,
                     logo_path: str = None) -> str:
        """
        Generate IEEE 830 SRS Document in Word format

        Args:
            functional_requirements: List of FR dicts with id, description, priority
            non_functional_requirements: List of NFR dicts
            use_cases: List of use case names for diagram
            actors: List of actor names for diagram
            include_diagrams: Whether to include UML diagrams
            logo_path: Path to college/project logo

        Returns:
            Path to generated document
        """
        doc_gen = WordDocumentGenerator(self.style)
        doc = doc_gen.create_document()

        # Cover page
        doc_gen.add_cover_page(
            title="Software Requirements Specification",
            subtitle=self.project_info.title,
            team_name=self.project_info.team_name,
            college=self.project_info.college_name,
            department=self.project_info.department,
            guide=self.project_info.guide_name,
            team_members=self.project_info.team_members,
            academic_year=self.project_info.academic_year,
            logo_path=logo_path
        )

        # Table of Contents
        doc_gen.add_table_of_contents()

        # 1. Introduction
        doc_gen.add_heading("1. Introduction", level=1)

        doc_gen.add_heading("1.1 Purpose", level=2)
        doc_gen.add_paragraph(
            f"This Software Requirements Specification (SRS) document provides a complete "
            f"description of all the requirements for the {self.project_info.title} system. "
            f"It is intended for use by the development team, project stakeholders, and quality assurance team."
        )

        doc_gen.add_heading("1.2 Scope", level=2)
        doc_gen.add_paragraph(
            f"{self.project_info.title} is a software application that aims to provide "
            f"comprehensive solutions for the target users. This document describes the "
            f"functional and non-functional requirements of the system."
        )

        doc_gen.add_heading("1.3 Definitions, Acronyms, and Abbreviations", level=2)
        doc_gen.add_table(
            headers=["Term", "Definition"],
            rows=[
                ["SRS", "Software Requirements Specification"],
                ["API", "Application Programming Interface"],
                ["UI", "User Interface"],
                ["FR", "Functional Requirement"],
                ["NFR", "Non-Functional Requirement"]
            ]
        )

        doc_gen.add_heading("1.4 References", level=2)
        doc_gen.add_paragraph("1. IEEE Std 830-1998, IEEE Recommended Practice for Software Requirements Specifications")
        doc_gen.add_paragraph("2. Project Proposal Document")

        doc_gen.add_page_break()

        # 2. Overall Description
        doc_gen.add_heading("2. Overall Description", level=1)

        doc_gen.add_heading("2.1 Product Perspective", level=2)
        doc_gen.add_paragraph(
            f"The {self.project_info.title} is a standalone system designed to meet the "
            f"requirements of the target users. The system architecture follows modern "
            f"software design principles."
        )

        # Add Use Case Diagram
        if include_diagrams and use_cases and actors:
            doc_gen.add_heading("2.1.1 Use Case Diagram", level=3)
            uml_code = self.uml.get_use_case_diagram(
                actors=actors or ["User", "Admin"],
                use_cases=use_cases or ["Login", "Register", "View Dashboard"],
                project_name=self.project_info.title
            )
            doc_gen.add_uml_diagram(uml_code, "UseCase", "System Use Case Diagram")

        doc_gen.add_heading("2.2 Product Functions", level=2)
        doc_gen.add_paragraph("The major functions of the system include:")
        if use_cases:
            for uc in use_cases:
                doc_gen.add_paragraph(f"• {uc}")
        else:
            doc_gen.add_paragraph("• User Management")
            doc_gen.add_paragraph("• Core Business Functions")
            doc_gen.add_paragraph("• Reporting and Analytics")

        doc_gen.add_heading("2.3 User Characteristics", level=2)
        doc_gen.add_table(
            headers=["User Type", "Description", "Technical Expertise"],
            rows=[
                ["Administrator", "System administrator with full access", "High"],
                ["End User", "Regular users of the system", "Low to Medium"],
                ["Guest", "Unauthenticated users with limited access", "Low"]
            ]
        )

        doc_gen.add_heading("2.4 Constraints", level=2)
        doc_gen.add_paragraph("• Technical Constraints: Must be compatible with modern web browsers")
        doc_gen.add_paragraph("• Regulatory Constraints: Must comply with data protection regulations")
        doc_gen.add_paragraph("• Time Constraints: Project completion within academic timeline")

        doc_gen.add_page_break()

        # 3. Specific Requirements
        doc_gen.add_heading("3. Specific Requirements", level=1)

        doc_gen.add_heading("3.1 Functional Requirements", level=2)

        # Default functional requirements if none provided
        if not functional_requirements:
            functional_requirements = [
                {"id": "FR-001", "description": "The system shall allow users to register with email and password", "priority": "High"},
                {"id": "FR-002", "description": "The system shall authenticate users during login", "priority": "High"},
                {"id": "FR-003", "description": "The system shall display a dashboard after successful login", "priority": "High"},
                {"id": "FR-004", "description": "The system shall allow users to update their profile", "priority": "Medium"},
                {"id": "FR-005", "description": "The system shall allow users to reset their password", "priority": "Medium"},
            ]

        doc_gen.add_table(
            headers=["Req ID", "Description", "Priority"],
            rows=[[fr["id"], fr["description"], fr["priority"]] for fr in functional_requirements]
        )

        doc_gen.add_heading("3.2 Non-Functional Requirements", level=2)

        # Default NFRs if none provided
        if not non_functional_requirements:
            non_functional_requirements = [
                {"id": "NFR-001", "category": "Performance", "description": "System shall respond within 2 seconds", "priority": "High"},
                {"id": "NFR-002", "category": "Security", "description": "All passwords shall be encrypted", "priority": "High"},
                {"id": "NFR-003", "category": "Usability", "description": "System shall be accessible on mobile devices", "priority": "Medium"},
                {"id": "NFR-004", "category": "Reliability", "description": "System uptime shall be 99.5%", "priority": "High"},
            ]

        doc_gen.add_table(
            headers=["Req ID", "Category", "Description", "Priority"],
            rows=[[nfr["id"], nfr["category"], nfr["description"], nfr["priority"]] for nfr in non_functional_requirements]
        )

        doc_gen.add_page_break()

        # 4. Appendices
        doc_gen.add_heading("4. Appendices", level=1)

        doc_gen.add_heading("4.1 Document Approval", level=2)
        doc_gen.add_table(
            headers=["Role", "Name", "Signature", "Date"],
            rows=[
                ["Project Guide", self.project_info.guide_name, "", ""],
                ["Team Lead", self.project_info.team_members[0] if self.project_info.team_members else "", "", ""],
            ]
        )

        # Save
        output_path = self.output_dir / "SRS_Document.docx"
        doc_gen.save(str(output_path))
        return str(output_path)

    def generate_sdd(self,
                     classes: List[Dict] = None,
                     entities: List[Dict] = None,
                     include_diagrams: bool = True,
                     logo_path: str = None) -> str:
        """
        Generate IEEE 1016 SDD Document in Word format

        Args:
            classes: List of class definitions for class diagram
            entities: List of entity definitions for ER diagram
            include_diagrams: Whether to include UML diagrams
            logo_path: Path to logo

        Returns:
            Path to generated document
        """
        doc_gen = WordDocumentGenerator(self.style)
        doc = doc_gen.create_document()

        # Cover page
        doc_gen.add_cover_page(
            title="Software Design Description",
            subtitle=self.project_info.title,
            team_name=self.project_info.team_name,
            college=self.project_info.college_name,
            department=self.project_info.department,
            guide=self.project_info.guide_name,
            team_members=self.project_info.team_members,
            academic_year=self.project_info.academic_year,
            logo_path=logo_path
        )

        # TOC
        doc_gen.add_table_of_contents()

        # 1. Introduction
        doc_gen.add_heading("1. Introduction", level=1)

        doc_gen.add_heading("1.1 Purpose", level=2)
        doc_gen.add_paragraph(
            f"This Software Design Description (SDD) document describes the architecture "
            f"and design of the {self.project_info.title} system. It provides a detailed "
            f"view of the system design based on the requirements in the SRS document."
        )

        doc_gen.add_heading("1.2 Scope", level=2)
        doc_gen.add_paragraph(
            "This document covers the system architecture, data design, component design, "
            "and user interface design."
        )

        doc_gen.add_page_break()

        # 2. Architectural Design
        doc_gen.add_heading("2. Architectural Design", level=1)

        doc_gen.add_heading("2.1 System Architecture", level=2)
        doc_gen.add_paragraph(
            "The system follows a layered architecture pattern with clear separation of concerns:"
        )
        doc_gen.add_paragraph("• Presentation Layer - User interface components")
        doc_gen.add_paragraph("• Business Logic Layer - Core application logic")
        doc_gen.add_paragraph("• Data Access Layer - Database operations")
        doc_gen.add_paragraph("• Database Layer - Data persistence")

        doc_gen.add_heading("2.2 Technology Stack", level=2)
        doc_gen.add_table(
            headers=["Component", "Technology", "Purpose"],
            rows=[
                ["Frontend", "React/Vue/Angular", "User Interface"],
                ["Backend", "Node.js/Python/Java", "Business Logic"],
                ["Database", "PostgreSQL/MongoDB", "Data Storage"],
                ["Cache", "Redis", "Performance Optimization"],
            ]
        )

        doc_gen.add_page_break()

        # 3. Data Design
        doc_gen.add_heading("3. Data Design", level=1)

        doc_gen.add_heading("3.1 Database Schema", level=2)

        # Add ER Diagram
        if include_diagrams:
            if not entities:
                entities = [
                    {
                        "name": "Users",
                        "fields": [
                            {"name": "id", "type": "UUID", "primary_key": True},
                            {"name": "name", "type": "VARCHAR(100)"},
                            {"name": "email", "type": "VARCHAR(255)"},
                            {"name": "password", "type": "VARCHAR(255)"},
                            {"name": "created_at", "type": "TIMESTAMP"}
                        ],
                        "relationships": []
                    },
                    {
                        "name": "Projects",
                        "fields": [
                            {"name": "id", "type": "UUID", "primary_key": True},
                            {"name": "name", "type": "VARCHAR(200)"},
                            {"name": "user_id", "type": "UUID", "foreign_key": True},
                            {"name": "created_at", "type": "TIMESTAMP"}
                        ],
                        "relationships": [{"type": "||--o{", "target": "Users", "label": "belongs to"}]
                    }
                ]

            uml_code = self.uml.get_er_diagram(entities)
            doc_gen.add_uml_diagram(uml_code, "ER", "Entity-Relationship Diagram")

        doc_gen.add_heading("3.2 Table Definitions", level=2)

        for entity in (entities or []):
            doc_gen.add_heading(f"Table: {entity['name']}", level=3)
            rows = []
            for field in entity.get("fields", []):
                constraints = []
                if field.get("primary_key"):
                    constraints.append("PRIMARY KEY")
                if field.get("foreign_key"):
                    constraints.append("FOREIGN KEY")
                rows.append([field["name"], field["type"], ", ".join(constraints) or "-"])

            doc_gen.add_table(
                headers=["Column", "Type", "Constraints"],
                rows=rows
            )

        doc_gen.add_page_break()

        # 4. Component Design
        doc_gen.add_heading("4. Component Design", level=1)

        doc_gen.add_heading("4.1 Class Diagram", level=2)

        if include_diagrams:
            if not classes:
                classes = [
                    {
                        "name": "User",
                        "attributes": ["-id: UUID", "-name: String", "-email: String"],
                        "methods": ["+login()", "+logout()", "+updateProfile()"],
                        "relationships": []
                    },
                    {
                        "name": "Project",
                        "attributes": ["-id: UUID", "-name: String", "-userId: UUID"],
                        "methods": ["+create()", "+update()", "+delete()"],
                        "relationships": [{"type": "-->", "target": "User"}]
                    }
                ]

            uml_code = self.uml.get_class_diagram(classes)
            doc_gen.add_uml_diagram(uml_code, "Class", "Class Diagram")

        doc_gen.add_page_break()

        # 5. User Interface Design
        doc_gen.add_heading("5. User Interface Design", level=1)

        doc_gen.add_heading("5.1 Screen Layouts", level=2)
        doc_gen.add_paragraph(
            "The user interface follows modern design principles with a clean, intuitive layout. "
            "Key screens include:"
        )
        doc_gen.add_paragraph("• Login/Registration Screen")
        doc_gen.add_paragraph("• Dashboard")
        doc_gen.add_paragraph("• Settings")
        doc_gen.add_paragraph("• Main Feature Screens")

        # Save
        output_path = self.output_dir / "SDD_Document.docx"
        doc_gen.save(str(output_path))
        return str(output_path)

    def generate_test_document(self,
                               test_cases: List[Dict] = None,
                               logo_path: str = None) -> str:
        """
        Generate IEEE 829 Test Documentation in Word format

        Args:
            test_cases: List of test case definitions
            logo_path: Path to logo

        Returns:
            Path to generated document
        """
        doc_gen = WordDocumentGenerator(self.style)
        doc = doc_gen.create_document()

        # Cover page
        doc_gen.add_cover_page(
            title="Software Test Documentation",
            subtitle=self.project_info.title,
            team_name=self.project_info.team_name,
            college=self.project_info.college_name,
            department=self.project_info.department,
            guide=self.project_info.guide_name,
            team_members=self.project_info.team_members,
            academic_year=self.project_info.academic_year,
            logo_path=logo_path
        )

        # TOC
        doc_gen.add_table_of_contents()

        # 1. Test Plan
        doc_gen.add_heading("1. Test Plan", level=1)

        doc_gen.add_heading("1.1 Introduction", level=2)
        doc_gen.add_paragraph(
            f"This document describes the test plan for {self.project_info.title}. "
            f"It outlines the testing strategy, scope, and schedule."
        )

        doc_gen.add_heading("1.2 Test Items", level=2)
        doc_gen.add_table(
            headers=["Item", "Version", "Description"],
            rows=[
                [self.project_info.title, self.project_info.version, "Complete System"],
                ["Authentication Module", self.project_info.version, "Login, Registration"],
                ["Core Features", self.project_info.version, "Main functionality"],
            ]
        )

        doc_gen.add_heading("1.3 Testing Approach", level=2)
        doc_gen.add_paragraph("The following testing levels will be performed:")
        doc_gen.add_paragraph("• Unit Testing - Test individual components")
        doc_gen.add_paragraph("• Integration Testing - Test component interactions")
        doc_gen.add_paragraph("• System Testing - Test complete system")
        doc_gen.add_paragraph("• User Acceptance Testing - Validate with users")

        doc_gen.add_heading("1.4 Pass/Fail Criteria", level=2)
        doc_gen.add_table(
            headers=["Criteria", "Pass Condition"],
            rows=[
                ["Unit Tests", "100% pass rate"],
                ["Integration Tests", "95% pass rate"],
                ["Critical Defects", "0 open critical defects"],
                ["Code Coverage", "Minimum 80%"],
            ]
        )

        doc_gen.add_page_break()

        # 2. Test Cases
        doc_gen.add_heading("2. Test Cases", level=1)

        if not test_cases:
            test_cases = [
                {
                    "id": "TC-001",
                    "name": "Login with Valid Credentials",
                    "module": "Authentication",
                    "priority": "High",
                    "preconditions": "User is registered",
                    "steps": [
                        "Navigate to login page",
                        "Enter valid email",
                        "Enter valid password",
                        "Click Login button"
                    ],
                    "expected": "User is redirected to dashboard"
                },
                {
                    "id": "TC-002",
                    "name": "Login with Invalid Password",
                    "module": "Authentication",
                    "priority": "High",
                    "preconditions": "User is registered",
                    "steps": [
                        "Navigate to login page",
                        "Enter valid email",
                        "Enter invalid password",
                        "Click Login button"
                    ],
                    "expected": "Error message is displayed"
                },
                {
                    "id": "TC-003",
                    "name": "User Registration",
                    "module": "Authentication",
                    "priority": "High",
                    "preconditions": "User is not registered",
                    "steps": [
                        "Navigate to registration page",
                        "Fill all required fields",
                        "Click Register button"
                    ],
                    "expected": "Account is created successfully"
                }
            ]

        for tc in test_cases:
            doc_gen.add_heading(f"Test Case: {tc['id']}", level=2)

            doc_gen.add_table(
                headers=["Field", "Value"],
                rows=[
                    ["Test Case ID", tc["id"]],
                    ["Test Case Name", tc["name"]],
                    ["Module", tc["module"]],
                    ["Priority", tc["priority"]],
                    ["Preconditions", tc["preconditions"]],
                ]
            )

            doc_gen.add_paragraph("Test Steps:", bold=True)
            for i, step in enumerate(tc["steps"], 1):
                doc_gen.add_paragraph(f"{i}. {step}")

            doc_gen.add_paragraph(f"Expected Result: {tc['expected']}", bold=True)
            doc_gen.add_paragraph("")

        doc_gen.add_page_break()

        # 3. Test Summary
        doc_gen.add_heading("3. Test Summary Report", level=1)

        doc_gen.add_heading("3.1 Summary", level=2)
        doc_gen.add_table(
            headers=["Metric", "Value"],
            rows=[
                ["Total Test Cases", str(len(test_cases))],
                ["Executed", "[To be filled]"],
                ["Passed", "[To be filled]"],
                ["Failed", "[To be filled]"],
                ["Pass Rate", "[To be filled]"],
            ]
        )

        # Save
        output_path = self.output_dir / "Test_Documentation.docx"
        doc_gen.save(str(output_path))
        return str(output_path)

    def generate_all(self, **kwargs) -> Dict[str, str]:
        """
        Generate all IEEE documents

        Returns:
            Dictionary mapping document type to file path
        """
        generated = {}

        try:
            generated["srs"] = self.generate_srs(**kwargs)
        except Exception as e:
            generated["srs"] = f"Error: {e}"

        try:
            generated["sdd"] = self.generate_sdd(**kwargs)
        except Exception as e:
            generated["sdd"] = f"Error: {e}"

        try:
            generated["test"] = self.generate_test_document(**kwargs)
        except Exception as e:
            generated["test"] = f"Error: {e}"

        return generated


def generate_ieee_word_document(
    template_id: str,
    project_info: ProjectInfo,
    output_dir: str = "docs",
    **kwargs
) -> str:
    """
    Generate IEEE document in Word format

    Args:
        template_id: 'srs', 'sdd', or 'test'
        project_info: Project information
        output_dir: Output directory
        **kwargs: Additional arguments for specific templates

    Returns:
        Path to generated document
    """
    generator = IEEEWordGenerator(project_info, output_dir)

    if template_id == "srs":
        return generator.generate_srs(**kwargs)
    elif template_id == "sdd":
        return generator.generate_sdd(**kwargs)
    elif template_id == "test":
        return generator.generate_test_document(**kwargs)
    else:
        raise ValueError(f"Unknown template: {template_id}")


def generate_all_ieee_word_documents(
    project_info: ProjectInfo,
    output_dir: str = "docs",
    **kwargs
) -> Dict[str, str]:
    """Generate all IEEE documents in Word format"""
    generator = IEEEWordGenerator(project_info, output_dir)
    return generator.generate_all(**kwargs)
