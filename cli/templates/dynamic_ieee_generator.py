"""
Dynamic IEEE Document Generator

Generates IEEE-compliant documentation based on actual project analysis.
Each document is customized to the specific project being documented.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from typing import Tuple

from cli.templates.project_analyzer import (
    ProjectAnalyzer,
    ProjectAnalysis,
    DatabaseModel,
    APIEndpoint,
    Component,
    FunctionalRequirement,
    UseCase,
    TestCase
)


@dataclass
class DocumentConfig:
    """Configuration for document generation"""
    project_title: str
    team_name: str
    team_members: List[str]
    guide_name: str
    college_name: str
    department: str
    academic_year: str
    version: str = "1.0"
    date: str = ""
    logo_path: Optional[str] = None

    # Additional college information
    college_address: str = ""
    college_affiliated_to: str = ""  # e.g., "Affiliated to JNTU Hyderabad"
    hod_name: str = ""
    principal_name: str = ""
    external_guide: str = ""
    roll_numbers: List[str] = field(default_factory=list)  # Student roll numbers

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%B %d, %Y")
        if not self.roll_numbers:
            self.roll_numbers = ["" for _ in self.team_members]


class DynamicIEEEGenerator:
    """Generates dynamic IEEE documents based on project analysis"""

    def __init__(self, project_path: str, config: DocumentConfig):
        self.project_path = Path(project_path)
        self.config = config
        self.analysis: Optional[ProjectAnalysis] = None

    def analyze_project(self) -> ProjectAnalysis:
        """Analyze the project to extract information"""
        analyzer = ProjectAnalyzer(str(self.project_path))
        self.analysis = analyzer.analyze()
        return self.analysis

    def generate_srs(self, output_path: str = None) -> str:
        """Generate dynamic Software Requirements Specification"""
        if not self.analysis:
            self.analyze_project()

        content = self._generate_srs_content()

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return content

    def generate_sdd(self, output_path: str = None) -> str:
        """Generate dynamic Software Design Description"""
        if not self.analysis:
            self.analyze_project()

        content = self._generate_sdd_content()

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return content

    def generate_test_doc(self, output_path: str = None) -> str:
        """Generate dynamic Test Documentation"""
        if not self.analysis:
            self.analyze_project()

        content = self._generate_test_content()

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

        return content

    def generate_all(self, output_dir: str) -> Dict[str, str]:
        """Generate all IEEE documents"""
        if not self.analysis:
            self.analyze_project()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        results = {}

        # SRS
        srs_path = output_path / f"SRS_{self.config.project_title.replace(' ', '_')}.md"
        self.generate_srs(str(srs_path))
        results['srs'] = str(srs_path)

        # SDD
        sdd_path = output_path / f"SDD_{self.config.project_title.replace(' ', '_')}.md"
        self.generate_sdd(str(sdd_path))
        results['sdd'] = str(sdd_path)

        # Test Documentation
        test_path = output_path / f"Test_{self.config.project_title.replace(' ', '_')}.md"
        self.generate_test_doc(str(test_path))
        results['test'] = str(test_path)

        return results

    def _generate_srs_content(self) -> str:
        """Generate SRS document content"""
        a = self.analysis
        c = self.config

        # Team members formatting with roll numbers
        team_list = ""
        for i, member in enumerate(c.team_members):
            roll = c.roll_numbers[i] if i < len(c.roll_numbers) and c.roll_numbers[i] else f"ROLL{i+1:03d}"
            team_list += f"| {i+1} | {member} | {roll} |\n"

        team_signatures = "\n".join([f"| {m} | | |" for m in c.team_members])

        # Tech stack
        tech_stack_table = self._format_tech_stack()

        # Functional requirements table
        fr_table = self._format_functional_requirements()

        # Non-functional requirements
        nfr_table = self._generate_nfr_table()

        # Use cases
        use_cases_content = self._format_use_cases()

        # Models/ER content
        er_content = self._format_database_models()

        # API documentation
        api_content = self._format_api_endpoints()

        # Data dictionary
        data_dict = self._format_data_dictionary()

        # Actors
        actors_table = self._format_actors()

        # Modules
        modules_table = self._format_modules()

        # College info with defaults
        college_addr = c.college_address or f"{c.college_name}"
        affiliated = c.college_affiliated_to or "Autonomous Institution"
        hod = c.hod_name or "Head of Department"
        principal = c.principal_name or "Principal"

        content = f'''# SOFTWARE REQUIREMENTS SPECIFICATION

# {c.project_title}

---

<div align="center">

## {c.college_name}

**{affiliated}**

{college_addr}

---

### {c.department}

---

### PROJECT REPORT

**On**

## "{c.project_title}"

**Submitted in partial fulfillment of the requirements for the award of**

### BACHELOR OF TECHNOLOGY

**In**

### COMPUTER SCIENCE AND ENGINEERING

**Submitted by:**

| S.No | Name | Roll Number |
|------|------|-------------|
{team_list}

**Under the guidance of**

**{c.guide_name}**

**Academic Year: {c.academic_year}**

</div>

---

| Document Information | Details |
|---------------------|---------|
| Project Title | {c.project_title} |
| Team Name | {c.team_name} |
| Document Version | {c.version} |
| Date | {c.date} |
| Status | Final |
| Document Type | IEEE 830 SRS |
| Project Type | {a.project_type} |

---

## {c.college_name}

### {c.department}

---

## CERTIFICATE

This is to certify that the project entitled **"{c.project_title}"** is a bonafide work carried out by:

| S.No | Name | Roll Number |
|------|------|-------------|
{team_list}

in partial fulfillment of the requirements for the award of **Bachelor of Technology in Computer Science and Engineering** from **{c.college_name}** during the academic year **{c.academic_year}**.

This project work has been approved as it satisfies the academic requirements prescribed for the said degree.

---

| | | |
|:---:|:---:|:---:|
| **Project Guide** | **Head of Department** | **Principal** |
| | | |
| {c.guide_name} | {hod} | {principal} |
| | | |
| Signature: _____________ | Signature: _____________ | Signature: _____________ |
| | | |
| Date: _____________ | Date: _____________ | Date: _____________ |

---

**EXTERNAL EXAMINER**

Name: _________________________

Signature: _____________________

Date: _________________________

---

## DECLARATION

We, the undersigned, hereby declare that the project entitled **"{c.project_title}"** submitted to **{c.college_name}**, **{c.department}**, is a record of an original work done by us under the guidance of **{c.guide_name}**, {c.department}.

This project work is submitted in partial fulfillment of the requirements for the award of the degree of **Bachelor of Technology in Computer Science and Engineering**.

We further declare that:
1. This project is based on our original work
2. This project has not been submitted previously for any degree or examination in any other university
3. All sources of information have been duly acknowledged
4. We have followed the guidelines provided by the institute for preparing this report

| Name | Roll Number | Signature |
|------|-------------|-----------|
{team_signatures}

**Date:** {c.date}

**Place:** {c.college_name}

---

## ACKNOWLEDGEMENT

We take this opportunity to express our profound gratitude and deep regards to our project guide **{c.guide_name}** for the exemplary guidance, monitoring and constant encouragement throughout the course of this project.

We would like to express our sincere thanks to **{hod}**, Head of Department, {c.department}, for providing us with the opportunity to work on this project.

We also express our sincere gratitude to **{principal}**, Principal, {c.college_name}, for providing us with the necessary facilities and support.

We extend our heartfelt thanks to all the faculty members of the {c.department} for their valuable suggestions and support during the development of this project.

We would also like to thank our family and friends for their constant support and encouragement.

Finally, we thank all those who directly or indirectly helped us in the successful completion of this project.

**Team Members:**
| S.No | Name |
|------|------|'''
        for i, member in enumerate(c.team_members):
            content += f"\n| {i+1} | {member} |"

        content += f'''

**Date:** {c.date}

**Place:** {c.college_name}

---

## ABSTRACT

**{c.project_title}** is a {a.project_type} developed using modern technologies. The system is built with {self._get_tech_summary()} to provide a robust, scalable, and user-friendly solution.

This Software Requirements Specification (SRS) document provides a comprehensive description of the system following IEEE 830-1998 standard. The document covers {len(a.functional_requirements)} functional requirements, {len(a.use_cases)} use cases, and complete system specifications derived from actual code analysis.

**Key Features:**
{self._format_key_features()}

**Keywords:** {c.project_title}, {a.project_type}, {', '.join(list(a.tech_stack.values())[:4])}, IEEE 830

---

## REVISION HISTORY

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 | {c.date} | {c.team_name} | Initial draft |
| 1.0 | {c.date} | {c.team_name} | Final version |

---

## TABLE OF CONTENTS

1. [INTRODUCTION](#1-introduction)
2. [OVERALL DESCRIPTION](#2-overall-description)
3. [SPECIFIC REQUIREMENTS](#3-specific-requirements)
4. [SYSTEM MODELS](#4-system-models)
5. [DATA DICTIONARY](#5-data-dictionary)
6. [APPENDICES](#6-appendices)

---

## 1. INTRODUCTION

### 1.1 Purpose

This Software Requirements Specification (SRS) document provides a complete description of all requirements for **{c.project_title}**. This document is intended for:

- Development Team
- Project Guide ({c.guide_name})
- Quality Assurance Team
- Project Evaluators
- Future Maintainers

### 1.2 Scope

#### 1.2.1 Product Identification

| Attribute | Value |
|-----------|-------|
| Product Name | {c.project_title} |
| Product Type | {a.project_type} |
| Version | {c.version} |

#### 1.2.2 Technology Stack

{tech_stack_table}

#### 1.2.3 Project Structure

The project contains **{len(a.files)}** file types across **{len(a.directories)}** directories.

| Category | Count |
|----------|-------|
| Python Files | {len(a.files.get('.py', []))} |
| JavaScript/TypeScript Files | {len(a.files.get('.js', [])) + len(a.files.get('.ts', [])) + len(a.files.get('.jsx', [])) + len(a.files.get('.tsx', []))} |
| Database Models | {len(a.models)} |
| API Endpoints | {len(a.api_endpoints)} |
| UI Components | {len(a.components)} |
| Pages | {len(a.pages)} |

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| API | Application Programming Interface |
| CRUD | Create, Read, Update, Delete operations |
| JWT | JSON Web Token for authentication |
| REST | Representational State Transfer |
| UI | User Interface |
| UX | User Experience |
{self._generate_project_specific_terms()}

### 1.4 References

| Reference | Description |
|-----------|-------------|
| IEEE Std 830-1998 | IEEE Recommended Practice for SRS |
| IEEE Std 1016-2009 | IEEE Standard for SDD |
| IEEE Std 829-2008 | IEEE Standard for Test Documentation |
{self._generate_tech_references()}

---

## 2. OVERALL DESCRIPTION

### 2.1 Product Perspective

{c.project_title} is a {a.project_type} designed to provide comprehensive functionality through a modern architecture.

#### 2.1.1 System Architecture

```
{self._generate_architecture_diagram()}
```

### 2.2 Product Functions

The system provides the following major functions:

{modules_table}

### 2.3 User Classes and Characteristics

{actors_table}

### 2.4 Operating Environment

#### 2.4.1 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 50+ GB |
| Network | 10 Mbps | 100+ Mbps |

#### 2.4.2 Software Requirements

| Software | Version |
|----------|---------|
{self._format_software_requirements()}

### 2.5 Design and Implementation Constraints

| Constraint | Description |
|------------|-------------|
| Technology Stack | Must use {self._get_tech_summary()} |
| Browser Support | Chrome 90+, Firefox 88+, Safari 14+, Edge 90+ |
| Security | Must implement authentication and authorization |
| Performance | Response time must be < 3 seconds |

### 2.6 Assumptions and Dependencies

| Assumption/Dependency | Description |
|----------------------|-------------|
| Internet Connectivity | Users have stable internet access |
| Modern Browser | Users have modern web browsers |
| Server Availability | Backend services are available |
{self._format_dependencies()}

---

## 3. SPECIFIC REQUIREMENTS

### 3.1 External Interface Requirements

#### 3.1.1 User Interfaces

The system provides {len(a.pages)} pages and {len(a.components)} UI components.

**Pages:**
{self._format_pages_list()}

**Key Components:**
{self._format_components_list()}

#### 3.1.2 API Interfaces

The system exposes **{len(a.api_endpoints)} API endpoints**:

{api_content}

### 3.2 Functional Requirements

The system has **{len(a.functional_requirements)} functional requirements** derived from code analysis:

{fr_table}

### 3.3 Non-Functional Requirements

{nfr_table}

### 3.4 System Features

{self._format_system_features()}

---

## 4. SYSTEM MODELS

### 4.1 Use Case Diagram

```
{self._generate_use_case_diagram()}
```

### 4.2 Use Case Descriptions

{use_cases_content}

### 4.3 Entity-Relationship Diagram

```
{self._generate_er_diagram()}
```

### 4.4 Database Schema

{er_content}

### 4.5 Sequence Diagrams

{self._generate_sequence_diagrams()}

### 4.6 Activity Diagrams

{self._generate_activity_diagrams()}

### 4.7 Class Diagram

{self._generate_class_diagram()}

---

## 5. DATA DICTIONARY

{data_dict}

---

## 6. APPENDICES

### 6.1 Project File Structure

```
{self._format_project_structure()}
```

### 6.2 Dependencies

{self._format_all_dependencies()}

### 6.3 Glossary

{self._generate_glossary()}

---

**Document End**

---

**Prepared by:** {c.team_name}

**{c.college_name}**

**{c.department}**

**Academic Year: {c.academic_year}**

---

*This document was auto-generated based on actual project code analysis.*
*Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
'''

        return content

    def _generate_sdd_content(self) -> str:
        """Generate SDD document content"""
        a = self.analysis
        c = self.config

        team_list = "\n".join([f"- {m}" for m in c.team_members])

        content = f'''# SOFTWARE DESIGN DESCRIPTION

## {c.project_title}

---

**Version {c.version}**

**Prepared by:** {c.team_name}

**{c.college_name}**

**{c.department}**

**Academic Year: {c.academic_year}**

---

## CERTIFICATE

This is to certify that the Software Design Description for **"{c.project_title}"** is prepared following IEEE 1016-2009 standard.

{team_list}

Under the guidance of **{c.guide_name}**.

---

## ABSTRACT

This Software Design Description (SDD) provides the architectural and detailed design of **{c.project_title}**, a {a.project_type}. The document describes the system's components, their interactions, and implementation details based on actual code analysis.

**Technology Stack:** {self._get_tech_summary()}

---

## TABLE OF CONTENTS

1. [INTRODUCTION](#1-introduction)
2. [ARCHITECTURAL DESIGN](#2-architectural-design)
3. [DETAILED DESIGN](#3-detailed-design)
4. [DATA DESIGN](#4-data-design)
5. [INTERFACE DESIGN](#5-interface-design)

---

## 1. INTRODUCTION

### 1.1 Purpose

This SDD describes the design of {c.project_title} for implementation guidance.

### 1.2 Scope

The document covers:
- System architecture
- Component design
- Database design
- API design
- UI design

---

## 2. ARCHITECTURAL DESIGN

### 2.1 System Overview

```
{self._generate_architecture_diagram()}
```

### 2.2 Architecture Pattern

The system follows a **{self._detect_architecture_pattern()}** architecture.

### 2.3 Technology Stack

{self._format_tech_stack()}

### 2.4 Component Overview

{self._format_component_overview()}

---

## 3. DETAILED DESIGN

### 3.1 Module Design

{self._format_module_design()}

### 3.2 Service Layer

{self._format_services()}

### 3.3 API Layer

{self._format_api_design()}

### 3.4 Class Diagram

{self._generate_class_diagram()}

---

## 4. DATA DESIGN

### 4.1 Database Schema

{self._format_database_models()}

### 4.2 Entity-Relationship Diagram

```
{self._generate_er_diagram()}
```

### 4.3 Data Flow

{self._generate_data_flow()}

---

## 5. INTERFACE DESIGN

### 5.1 User Interface Design

#### 5.1.1 Pages

{self._format_pages_design()}

#### 5.1.2 Components

{self._format_components_design()}

### 5.2 API Interface Design

{self._format_api_interface_design()}

---

**Document End**

---

**Prepared by:** {c.team_name}

**{c.college_name}**

*Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
'''

        return content

    def _generate_test_content(self) -> str:
        """Generate Test Documentation content"""
        a = self.analysis
        c = self.config

        content = f'''# SOFTWARE TEST DOCUMENTATION

## {c.project_title}

---

**Version {c.version}**

**Prepared by:** {c.team_name}

**{c.college_name}**

**{c.department}**

**Academic Year: {c.academic_year}**

---

## ABSTRACT

This Test Documentation provides comprehensive test specifications for **{c.project_title}** following IEEE 829-2008 standard. The document includes **{len(a.test_cases)} test cases** derived from functional requirements and code analysis.

---

## 1. TEST PLAN

### 1.1 Test Items

| Item | Version | Description |
|------|---------|-------------|
| {c.project_title} | {c.version} | Complete system |
{self._format_test_items()}

### 1.2 Features to be Tested

{self._format_features_to_test()}

### 1.3 Test Approach

| Test Type | Description | Tools |
|-----------|-------------|-------|
| Unit Testing | Individual component testing | Jest/Pytest |
| Integration Testing | Module interaction testing | Jest/Pytest |
| API Testing | Endpoint testing | Postman/Pytest |
| UI Testing | User interface testing | Selenium/Cypress |
| Performance Testing | Load and response testing | JMeter/k6 |

### 1.4 Pass/Fail Criteria

| Criteria | Target |
|----------|--------|
| Test Pass Rate | >= 95% |
| Code Coverage | >= 80% |
| Critical Bugs | 0 |
| High Priority Bugs | <= 2 |

---

## 2. TEST CASES

### 2.1 Test Case Summary

| Category | Count |
|----------|-------|
| Functional Tests | {len([tc for tc in a.test_cases if tc.type == 'Functional'])} |
| API Tests | {len([tc for tc in a.test_cases if tc.type == 'API'])} |
| Negative Tests | {len([tc for tc in a.test_cases if tc.type == 'Negative'])} |
| **Total** | **{len(a.test_cases)}** |

### 2.2 Detailed Test Cases

{self._format_test_cases()}

---

## 3. TEST PROCEDURES

### 3.1 Test Environment Setup

1. Install dependencies: `npm install` / `pip install -r requirements.txt`
2. Configure environment variables
3. Start database server
4. Start application server
5. Run test suite

### 3.2 Test Execution

```bash
# Run all tests
npm test
# or
pytest

# Run specific test category
pytest -m api
pytest -m unit
```

---

## 4. TEST SUMMARY

### 4.1 Test Metrics Template

| Metric | Value |
|--------|-------|
| Total Test Cases | {len(a.test_cases)} |
| Executed | [To be filled] |
| Passed | [To be filled] |
| Failed | [To be filled] |
| Pass Rate | [To be filled] |

### 4.2 Defect Summary Template

| Severity | Count |
|----------|-------|
| Critical | [To be filled] |
| High | [To be filled] |
| Medium | [To be filled] |
| Low | [To be filled] |

---

**Document End**

---

**Prepared by:** {c.team_name}

*Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
'''

        return content

    # =====================================================
    # Helper Methods for Content Generation
    # =====================================================

    def _get_tech_summary(self) -> str:
        """Get technology stack summary"""
        tech = self.analysis.tech_stack
        parts = []
        if tech.get('frontend'):
            parts.append(tech['frontend'])
        if tech.get('frontend_framework'):
            parts.append(tech['frontend_framework'])
        if tech.get('backend'):
            parts.append(tech['backend'])
        if tech.get('backend_framework'):
            parts.append(tech['backend_framework'])
        if tech.get('database'):
            parts.append(tech['database'])
        return ', '.join(parts) if parts else 'Modern Web Technologies'

    def _format_tech_stack(self) -> str:
        """Format technology stack as table"""
        tech = self.analysis.tech_stack
        rows = []
        for key, value in tech.items():
            name = key.replace('_', ' ').title()
            rows.append(f"| {name} | {value} |")
        return "| Technology | Value |\n|------------|-------|\n" + "\n".join(rows) if rows else "| N/A | N/A |"

    def _format_functional_requirements(self) -> str:
        """Format functional requirements as table"""
        rows = []
        for req in self.analysis.functional_requirements[:50]:  # Limit to 50
            rows.append(f"| {req.id} | {req.name} | {req.description[:80]}... | {req.module} | {req.priority} |")

        header = "| ID | Name | Description | Module | Priority |\n|-----|------|-------------|--------|----------|\n"
        return header + "\n".join(rows)

    def _generate_nfr_table(self) -> str:
        """Generate non-functional requirements table"""
        nfrs = [
            ("NFR-001", "Performance", "Page load time shall be less than 3 seconds", "High"),
            ("NFR-002", "Performance", "API response time shall be less than 500ms", "High"),
            ("NFR-003", "Security", "All passwords shall be hashed using bcrypt", "High"),
            ("NFR-004", "Security", "All API endpoints shall require authentication", "High"),
            ("NFR-005", "Security", "HTTPS shall be used for all communications", "High"),
            ("NFR-006", "Reliability", "System availability shall be 99.5%", "Medium"),
            ("NFR-007", "Usability", "UI shall be responsive for mobile devices", "Medium"),
            ("NFR-008", "Scalability", "System shall support 100+ concurrent users", "Medium"),
            ("NFR-009", "Maintainability", "Code coverage shall be above 80%", "Medium"),
            ("NFR-010", "Compatibility", "System shall work on modern browsers", "High"),
        ]

        rows = [f"| {nfr[0]} | {nfr[1]} | {nfr[2]} | {nfr[3]} |" for nfr in nfrs]
        header = "| ID | Category | Requirement | Priority |\n|-----|----------|-------------|----------|\n"
        return header + "\n".join(rows)

    def _format_use_cases(self) -> str:
        """Format use cases"""
        content = ""
        for uc in self.analysis.use_cases[:15]:  # Limit to 15
            content += f'''
#### {uc.id}: {uc.name}

| Attribute | Value |
|-----------|-------|
| Actor | {uc.actor} |
| Description | {uc.description} |

**Preconditions:**
{chr(10).join(['- ' + p for p in uc.preconditions])}

**Main Flow:**
{chr(10).join([f'{i+1}. {step}' for i, step in enumerate(uc.main_flow)])}

**Postconditions:**
{chr(10).join(['- ' + p for p in uc.postconditions])}

---
'''
        return content

    def _format_database_models(self) -> str:
        """Format database models"""
        content = ""
        for model in self.analysis.models:
            content += f'''
#### {model.name}

| Field | Type | Constraints |
|-------|------|-------------|
'''
            for field in model.fields:
                constraints = ', '.join(field.get('constraints', [])) or '-'
                content += f"| {field['name']} | {field['type']} | {constraints} |\n"

            if model.relationships:
                content += "\n**Relationships:**\n"
                for rel in model.relationships:
                    content += f"- {rel['name']} -> {rel['target']}\n"

            content += "\n---\n"

        return content if content else "No database models detected."

    def _format_api_endpoints(self) -> str:
        """Format API endpoints"""
        if not self.analysis.api_endpoints:
            return "No API endpoints detected."

        content = "| Method | Endpoint | Description |\n|--------|----------|-------------|\n"
        for ep in self.analysis.api_endpoints[:30]:  # Limit to 30
            content += f"| {ep.method} | `{ep.path}` | {ep.description} |\n"

        return content

    def _format_data_dictionary(self) -> str:
        """Format data dictionary from models"""
        content = "### Data Elements\n\n"
        content += "| Entity | Field | Type | Description |\n|--------|-------|------|-------------|\n"

        for model in self.analysis.models:
            for field in model.fields:
                desc = f"Field in {model.name} entity"
                content += f"| {model.name} | {field['name']} | {field['type']} | {desc} |\n"

        return content if self.analysis.models else "No data elements detected."

    def _format_actors(self) -> str:
        """Format actors table"""
        content = "| Actor | Type | Description |\n|-------|------|-------------|\n"
        for actor in self.analysis.actors:
            content += f"| {actor['name']} | {actor['type'].title()} | {actor['description']} |\n"
        return content

    def _format_modules(self) -> str:
        """Format modules table"""
        content = "| Module | Description |\n|--------|-------------|\n"
        for module in self.analysis.modules[:15]:
            content += f"| {module['name']} | {module['description']} |\n"
        return content

    def _format_key_features(self) -> str:
        """Format key features list"""
        features = []
        if self.analysis.models:
            features.append(f"- Data management for {len(self.analysis.models)} entities")
        if self.analysis.api_endpoints:
            features.append(f"- {len(self.analysis.api_endpoints)} API endpoints")
        if self.analysis.pages:
            features.append(f"- {len(self.analysis.pages)} pages for user interaction")
        if self.analysis.components:
            features.append(f"- {len(self.analysis.components)} reusable UI components")

        # Add common features based on dependencies
        deps = list(self.analysis.dependencies.keys())
        if any('auth' in d.lower() or 'jwt' in d.lower() for d in deps):
            features.append("- User authentication and authorization")
        if any('redux' in d.lower() or 'zustand' in d.lower() for d in deps):
            features.append("- State management")

        return "\n".join(features) if features else "- Core functionality"

    def _generate_project_specific_terms(self) -> str:
        """Generate project-specific terms for glossary"""
        terms = []
        for model in self.analysis.models[:5]:
            terms.append(f"| {model.name} | A data entity in the system |")
        return "\n".join(terms)

    def _generate_tech_references(self) -> str:
        """Generate technology references"""
        refs = []
        tech = self.analysis.tech_stack
        if tech.get('frontend'):
            refs.append(f"| {tech['frontend']} Documentation | Official {tech['frontend']} documentation |")
        if tech.get('backend_framework'):
            refs.append(f"| {tech['backend_framework']} Documentation | Official {tech['backend_framework']} documentation |")
        if tech.get('database'):
            refs.append(f"| {tech['database']} Documentation | Official {tech['database']} documentation |")
        return "\n".join(refs)

    def _generate_architecture_diagram(self) -> str:
        """Generate ASCII architecture diagram"""
        tech = self.analysis.tech_stack

        frontend = tech.get('frontend', 'Frontend')
        backend = tech.get('backend_framework', tech.get('backend', 'Backend'))
        database = tech.get('database', 'Database')

        return f'''
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                  Web Browser                         │    │
│  │  ({frontend})                                        │    │
│  └───────────────────────┬─────────────────────────────┘    │
└──────────────────────────┼──────────────────────────────────┘
                           │ HTTPS/REST API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              {backend} API Server                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │    │
│  │  │ Routes   │  │ Services │  │   Middleware     │   │    │
│  │  │({len(self.analysis.api_endpoints)} endpoints)│  │({len(self.analysis.services)} svcs)│  │ (Auth, CORS)     │   │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘   │    │
│  └───────────────────────┬─────────────────────────────┘    │
└──────────────────────────┼──────────────────────────────────┘
                           │ Database Connection
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              {database}                              │    │
│  │         ({len(self.analysis.models)} Tables/Collections)                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
'''

    def _generate_use_case_diagram(self) -> str:
        """Generate dynamic ASCII use case diagram from actual actors and use cases"""
        actors = self.analysis.actors
        use_cases = self.analysis.use_cases

        if not use_cases:
            return "No use cases detected in the project."

        # Group use cases by actor
        actor_use_cases = {}
        for uc in use_cases:
            actor = uc.actor
            if actor not in actor_use_cases:
                actor_use_cases[actor] = []
            actor_use_cases[actor].append(uc.name)

        project_name = self.config.project_title

        diagram = f'''
                                {project_name} - USE CASE DIAGRAM
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

'''

        # Draw each actor with their use cases
        for actor_info in actors[:4]:  # Limit to 4 actors
            actor_name = actor_info['name']
            actor_ucs = actor_use_cases.get(actor_name, [])

            if not actor_ucs:
                # Find use cases that might be for this actor type
                if actor_info['type'] == 'primary':
                    actor_ucs = [uc.name for uc in use_cases[:3]]
                elif actor_info['type'] == 'system':
                    actor_ucs = [uc.name for uc in use_cases if 'system' in uc.description.lower()][:2]

            diagram += f'''
       ┌───────┐
       │ {actor_name[:6]:^6}│        ┌──────────────────────────────────────────────────┐
       │  ╱╲   │        │              SYSTEM BOUNDARY                      │
       │ /  \\  │        │                                                    │
       │      │        │'''

            # Add use cases for this actor
            for i, uc in enumerate(actor_ucs[:5]):
                uc_display = uc[:35] if len(uc) > 35 else uc
                if i == 0:
                    diagram += f"   ┌──────────────────────────────────────┐   │\n"
                    diagram += f"       │      │────────│  │  ({uc_display:<35}) │   │\n"
                    diagram += f"       │      │        │  └──────────────────────────────────────┘   │\n"
                else:
                    diagram += f"       │      │        │   ┌──────────────────────────────────────┐   │\n"
                    diagram += f"       │      │────────│   │  ({uc_display:<35}) │   │\n"
                    diagram += f"       │      │        │   └──────────────────────────────────────┘   │\n"

            diagram += f'''       └───────┘        │                                                    │
                        └──────────────────────────────────────────────────┘
'''

        # Legend
        diagram += '''
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    ACTORS:
'''
        for actor in actors[:4]:
            diagram += f"      • {actor['name']}: {actor['description']}\n"

        diagram += f'''
    USE CASES: {len(use_cases)} identified
'''
        for i, uc in enumerate(use_cases[:8], 1):
            diagram += f"      UC-{i:02d}: {uc.name}\n"

        return diagram

    def _generate_er_diagram(self) -> str:
        """Generate dynamic ASCII ER diagram from actual database models"""
        models = self.analysis.models

        if not models:
            return "No database models detected in the project."

        project_name = self.config.project_title

        diagram = f'''
                        {project_name} - ENTITY RELATIONSHIP DIAGRAM
    ════════════════════════════════════════════════════════════════════════════

'''

        # Calculate relationships between models
        relationships = []
        model_names = [m.name.lower() for m in models]

        for model in models:
            for rel in model.relationships:
                relationships.append((model.name, rel['target'], rel.get('type', 'has')))
            # Also check field names for implicit relationships
            for field in model.fields:
                field_lower = field['name'].lower()
                if field_lower.endswith('_id') or field_lower.endswith('id'):
                    ref_name = field_lower.replace('_id', '').replace('id', '')
                    for mn in model_names:
                        if ref_name in mn or mn in ref_name:
                            relationships.append((model.name, mn.title(), 'references'))

        # Draw entities
        for i, model in enumerate(models[:8]):  # Limit to 8 models
            # Calculate box width based on content
            max_field_len = max(len(f['name']) + len(f['type']) for f in model.fields[:8]) if model.fields else 10
            box_width = max(max_field_len + 8, len(model.name) + 4, 30)

            diagram += f'''    ┌{'─' * box_width}┐
    │{' ' * ((box_width - len(model.name)) // 2)}{model.name}{' ' * ((box_width - len(model.name) + 1) // 2)}│
    │{' ' * box_width}│
    ├{'─' * box_width}┤
'''
            # Primary key first
            pk_field = None
            for field in model.fields:
                if 'id' in field['name'].lower() and ('primary' in str(field.get('constraints', [])).lower() or field['name'] == 'id'):
                    pk_field = field
                    break

            if pk_field:
                pk_display = f" PK │ {pk_field['name']}: {pk_field['type']}"
                diagram += f"    │{pk_display:<{box_width}}│\n"
                diagram += f"    ├{'─' * box_width}┤\n"

            # Other fields
            for field in model.fields[:8]:
                if pk_field and field['name'] == pk_field['name']:
                    continue
                fk_marker = "FK" if field['name'].endswith('_id') else "  "
                field_display = f" {fk_marker} │ {field['name']}: {field['type']}"
                diagram += f"    │{field_display:<{box_width}}│\n"

            diagram += f"    └{'─' * box_width}┘\n"
            diagram += "\n"

        # Draw relationships
        if relationships:
            diagram += '''
    ════════════════════════════════════════════════════════════════════════════
                                    RELATIONSHIPS
    ════════════════════════════════════════════════════════════════════════════

'''
            seen = set()
            for rel in relationships:
                rel_key = f"{rel[0]}-{rel[1]}"
                if rel_key not in seen:
                    seen.add(rel_key)
                    diagram += f"    {rel[0]} ───────────────┤├─────────────── {rel[1]}\n"
                    diagram += f"                     ({rel[2]})\n\n"

        # Legend
        diagram += '''
    ════════════════════════════════════════════════════════════════════════════
                                      LEGEND
    ════════════════════════════════════════════════════════════════════════════
    PK = Primary Key
    FK = Foreign Key
    ───┤├─── = Relationship (One-to-Many)
    ────────  = Relationship (One-to-One)

'''
        diagram += f"    Total Entities: {len(models)}\n"
        diagram += f"    Total Relationships: {len(set(relationships))}\n"

        return diagram

    def _generate_sequence_diagrams(self) -> str:
        """Generate dynamic sequence diagrams based on actual API endpoints"""
        endpoints = self.analysis.api_endpoints
        models = self.analysis.models

        if not endpoints:
            return "No API endpoints detected for sequence diagram generation."

        tech = self.analysis.tech_stack
        frontend = tech.get('frontend', 'Frontend')
        backend = tech.get('backend_framework', tech.get('backend', 'Backend'))
        database = tech.get('database', 'Database')

        project_name = self.config.project_title

        content = f'''
### {project_name} - SEQUENCE DIAGRAMS

The following sequence diagrams show the interaction flow between system components.

'''

        # Group endpoints by resource
        resources = {}
        for ep in endpoints:
            parts = ep.path.strip('/').split('/')
            resource = parts[0] if parts else 'api'
            if resource not in resources:
                resources[resource] = []
            resources[resource].append(ep)

        # Generate sequence diagram for each major resource
        diagram_count = 0
        for resource, eps in list(resources.items())[:4]:  # Limit to 4 resources
            # Find CRUD operations for this resource
            get_ep = next((e for e in eps if e.method == 'GET'), None)
            post_ep = next((e for e in eps if e.method == 'POST'), None)
            put_ep = next((e for e in eps if e.method == 'PUT' or e.method == 'PATCH'), None)
            delete_ep = next((e for e in eps if e.method == 'DELETE'), None)

            resource_title = resource.replace('-', ' ').replace('_', ' ').title()

            if post_ep:
                diagram_count += 1
                content += f'''
#### Sequence Diagram {diagram_count}: Create {resource_title}

```
┌──────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────┐
│   User   │          │  {frontend[:10]:<10}  │          │  {backend[:10]:<10}  │          │{database[:8]:^10}│
└────┬─────┘          └──────┬───────┘          └──────┬───────┘          └────┬─────┘
     │                       │                         │                       │
     │   Fill Form           │                         │                       │
     │──────────────────────>│                         │                       │
     │                       │                         │                       │
     │                       │   POST {post_ep.path[:20]:<20}   │                       │
     │                       │────────────────────────>│                       │
     │                       │                         │                       │
     │                       │                         │  Validate Data        │
     │                       │                         │───────────┐           │
     │                       │                         │<──────────┘           │
     │                       │                         │                       │
     │                       │                         │  INSERT {resource[:10]:<10}   │
     │                       │                         │──────────────────────>│
     │                       │                         │                       │
     │                       │                         │    Success/ID         │
     │                       │                         │<──────────────────────│
     │                       │                         │                       │
     │                       │   201 Created + Data    │                       │
     │                       │<────────────────────────│                       │
     │                       │                         │                       │
     │   Show Success        │                         │                       │
     │<──────────────────────│                         │                       │
     │                       │                         │                       │
└────┴─────┘          └──────┴───────┘          └──────┴───────┘          └────┴─────┘
```

'''

            if get_ep:
                diagram_count += 1
                content += f'''
#### Sequence Diagram {diagram_count}: Get {resource_title}

```
┌──────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────┐
│   User   │          │  {frontend[:10]:<10}  │          │  {backend[:10]:<10}  │          │{database[:8]:^10}│
└────┬─────┘          └──────┬───────┘          └──────┬───────┘          └────┬─────┘
     │                       │                         │                       │
     │   View {resource[:10]:<10}     │                         │                       │
     │──────────────────────>│                         │                       │
     │                       │                         │                       │
     │                       │   GET {get_ep.path[:20]:<20}    │                       │
     │                       │────────────────────────>│                       │
     │                       │                         │                       │
     │                       │                         │  SELECT {resource[:10]:<10}  │
     │                       │                         │──────────────────────>│
     │                       │                         │                       │
     │                       │                         │    Result Set         │
     │                       │                         │<──────────────────────│
     │                       │                         │                       │
     │                       │   200 OK + Data         │                       │
     │                       │<────────────────────────│                       │
     │                       │                         │                       │
     │   Display Data        │                         │                       │
     │<──────────────────────│                         │                       │
     │                       │                         │                       │
└────┴─────┘          └──────┴───────┘          └──────┴───────┘          └────┴─────┘
```

'''

        # Always include authentication sequence if relevant endpoints exist
        auth_eps = [e for e in endpoints if 'auth' in e.path.lower() or 'login' in e.path.lower()]
        if auth_eps:
            diagram_count += 1
            login_ep = auth_eps[0]
            content += f'''
#### Sequence Diagram {diagram_count}: User Authentication

```
┌──────────┐          ┌──────────────┐          ┌──────────────┐          ┌──────────┐
│   User   │          │  {frontend[:10]:<10}  │          │  {backend[:10]:<10}  │          │{database[:8]:^10}│
└────┬─────┘          └──────┬───────┘          └──────┬───────┘          └────┬─────┘
     │                       │                         │                       │
     │   Enter Credentials   │                         │                       │
     │──────────────────────>│                         │                       │
     │                       │                         │                       │
     │                       │   POST {login_ep.path[:18]:<18}     │                       │
     │                       │────────────────────────>│                       │
     │                       │                         │                       │
     │                       │                         │  Query User           │
     │                       │                         │──────────────────────>│
     │                       │                         │                       │
     │                       │                         │  User + Hash          │
     │                       │                         │<──────────────────────│
     │                       │                         │                       │
     │                       │                         │  Verify Password      │
     │                       │                         │───────────┐           │
     │                       │                         │<──────────┘           │
     │                       │                         │                       │
     │                       │                         │  Generate JWT Token   │
     │                       │                         │───────────┐           │
     │                       │                         │<──────────┘           │
     │                       │                         │                       │
     │                       │   200 OK + JWT Token    │                       │
     │                       │<────────────────────────│                       │
     │                       │                         │                       │
     │   Store Token         │                         │                       │
     │   Redirect Dashboard  │                         │                       │
     │<──────────────────────│                         │                       │
     │                       │                         │                       │
└────┴─────┘          └──────┴───────┘          └──────┴───────┘          └────┴─────┘
```

'''

        content += f'''
---

**Total Sequence Diagrams:** {diagram_count}

**Components:**
- **User**: End user interacting with the system
- **{frontend}**: Frontend application layer
- **{backend}**: Backend API server
- **{database}**: Database server

'''
        return content

    def _generate_activity_diagrams(self) -> str:
        """Generate dynamic activity diagrams based on actual use cases"""
        use_cases = self.analysis.use_cases
        modules = self.analysis.modules

        if not use_cases:
            return "No use cases detected for activity diagram generation."

        project_name = self.config.project_title

        content = f'''
### {project_name} - ACTIVITY DIAGRAMS

'''

        # Generate activity diagram for main user flows
        for i, uc in enumerate(use_cases[:4], 1):  # Limit to 4 use cases
            content += f'''
#### Activity Diagram {i}: {uc.name}

**Actor:** {uc.actor}

```
                    ┌─────────────────┐
                    │    ● Start      │
                    └────────┬────────┘
                             │
                             ▼
'''
            # Add preconditions as decision
            if uc.preconditions:
                condition = uc.preconditions[0][:30] if uc.preconditions else "Precondition"
                content += f'''                    ┌─────────────────┐
                    │ {condition:<15} │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │    Check        │
                    └────────┬────────┘
                       Yes   │   No
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
'''

            # Add main flow steps
            for j, step in enumerate(uc.main_flow[:5]):
                step_display = step[:25] if len(step) > 25 else step
                if j < len(uc.main_flow) - 1:
                    content += f'''              ┌─────────────────────────┐
              │ {step_display:<23} │
              └────────────┬────────────┘
                           │
                           ▼
'''
                else:
                    content += f'''              ┌─────────────────────────┐
              │ {step_display:<23} │
              └────────────┬────────────┘
                           │
'''

            # Add postconditions
            if uc.postconditions:
                post = uc.postconditions[0][:25] if uc.postconditions else "Complete"
                content += f'''                           ▼
              ┌─────────────────────────┐
              │ {post:<23} │
              └────────────┬────────────┘
'''

            content += f'''                           │
                           ▼
                    ┌─────────────────┐
                    │    ○ End        │
                    └─────────────────┘
```

**Description:** {uc.description}

---
'''

        # Generate a main system flow activity diagram
        content += f'''
#### Activity Diagram: Overall System Flow

```
                              ┌─────────────────┐
                              │    ● Start      │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │   User Access   │
                              └────────┬────────┘
                                       │
                              ┌────────┴────────┐
                              │ Authenticated?  │
                              └────────┬────────┘
                              Yes      │      No
                         ┌─────────────┴─────────────┐
                         │                           │
                         ▼                           ▼
               ┌─────────────────┐         ┌─────────────────┐
               │   Dashboard     │         │    Login Page   │
               └────────┬────────┘         └────────┬────────┘
                        │                           │
                        │                           ▼
                        │                  ┌─────────────────┐
                        │                  │ Enter Creds     │
                        │                  └────────┬────────┘
                        │                           │
                        ▼                           │
'''

        # Add modules as activities
        for j, module in enumerate(modules[:4]):
            module_name = module['name'][:15]
            content += f'''               ┌─────────────────┐
               │ {module_name:<15} │──────┐
               └────────┬────────┘      │
                        │               │
'''

        content += f'''                        ▼               │
               ┌─────────────────┐      │
               │    Logout       │◄─────┘
               └────────┬────────┘
                        │
                        ▼
               ┌─────────────────┐
               │    ○ End        │
               └─────────────────┘
```

**System Modules:** {len(modules)}
'''
        for module in modules[:6]:
            content += f"- {module['name']}: {module['description']}\n"

        return content

    def _generate_class_diagram(self) -> str:
        """Generate dynamic class diagram from actual models and services"""
        models = self.analysis.models
        services = self.analysis.services

        if not models and not services:
            return "No classes detected in the project."

        project_name = self.config.project_title

        content = f'''
### {project_name} - CLASS DIAGRAM

The following class diagram represents the main classes in the system including models, services, and their relationships.

'''

        # Draw model classes
        if models:
            content += '''
#### Entity Classes (Models)

```
'''
            for model in models[:6]:
                # Calculate box width
                max_width = len(model.name) + 4
                for field in model.fields[:10]:
                    field_str = f"+ {field['name']}: {field['type']}"
                    max_width = max(max_width, len(field_str) + 2)
                max_width = max(max_width, 35)

                # Class header
                content += f'''┌{'─' * max_width}┐
│{model.name:^{max_width}}│
│{'《Entity》':^{max_width}}│
├{'─' * max_width}┤
│{'ATTRIBUTES':^{max_width}}│
├{'─' * max_width}┤
'''
                # Attributes
                for field in model.fields[:8]:
                    visibility = '+' if not field['name'].startswith('_') else '-'
                    field_str = f"{visibility} {field['name']}: {field['type']}"
                    content += f"│ {field_str:<{max_width-2}} │\n"

                # Methods section
                content += f'''├{'─' * max_width}┤
│{'METHODS':^{max_width}}│
├{'─' * max_width}┤
│ + create(): {model.name:<{max_width-15}} │
│ + read(): {model.name:<{max_width-13}} │
│ + update(): void{' ' * (max_width-17)} │
│ + delete(): void{' ' * (max_width-17)} │
└{'─' * max_width}┘

'''

            content += "```\n"

        # Draw service classes
        if services:
            content += '''
#### Service Classes

```
'''
            for svc in services[:4]:
                svc_name = svc['name']
                methods = svc.get('methods', [])[:6]

                max_width = len(svc_name) + 4
                for method in methods:
                    method_str = f"+ {method}()"
                    max_width = max(max_width, len(method_str) + 2)
                max_width = max(max_width, 35)

                content += f'''┌{'─' * max_width}┐
│{svc_name:^{max_width}}│
│{'《Service》':^{max_width}}│
├{'─' * max_width}┤
│{'METHODS':^{max_width}}│
├{'─' * max_width}┤
'''
                for method in methods:
                    method_str = f"+ {method}()"
                    content += f"│ {method_str:<{max_width-2}} │\n"

                content += f"└{'─' * max_width}┘\n\n"

            content += "```\n"

        # Draw relationships
        content += '''
#### Class Relationships

```
'''
        # Entity relationships
        relationships_drawn = set()
        for model in models[:6]:
            for rel in model.relationships:
                rel_key = f"{model.name}-{rel['target']}"
                if rel_key not in relationships_drawn:
                    relationships_drawn.add(rel_key)
                    content += f"    {model.name} ──────────────── {rel['target']}\n"
                    content += f"         │  ({rel.get('type', 'has')})  │\n\n"

            # Check for FK relationships
            for field in model.fields:
                if field['name'].endswith('_id'):
                    ref = field['name'].replace('_id', '').title()
                    rel_key = f"{model.name}-{ref}"
                    if rel_key not in relationships_drawn:
                        relationships_drawn.add(rel_key)
                        content += f"    {model.name} ◆──────────────── {ref}\n"
                        content += f"         │  (references)  │\n\n"

        # Service to Model relationships
        for svc in services[:4]:
            content += f"    {svc['name']} ─ ─ ─ ─ ─► Models\n"
            content += f"         │  (uses)  │\n\n"

        content += '''```

#### Relationship Legend

| Symbol | Meaning |
|--------|---------|
| ───── | Association |
| ◆───── | Composition |
| ◇───── | Aggregation |
| ─ ─ ─► | Dependency |
| ───▷ | Inheritance |

'''

        # Class summary
        content += f'''
#### Class Summary

| Category | Count | Description |
|----------|-------|-------------|
| Entity Classes | {len(models)} | Database models/entities |
| Service Classes | {len(services)} | Business logic services |
| Total Classes | {len(models) + len(services)} | All identified classes |

'''

        return content

    def _format_software_requirements(self) -> str:
        """Format software requirements"""
        reqs = []
        tech = self.analysis.tech_stack

        if tech.get('backend') == 'Python':
            reqs.append("| Python | 3.9+ |")
        if tech.get('frontend') == 'React':
            reqs.append("| Node.js | 16+ |")
        if tech.get('database') == 'PostgreSQL':
            reqs.append("| PostgreSQL | 13+ |")
        elif tech.get('database') == 'MongoDB':
            reqs.append("| MongoDB | 5.0+ |")

        reqs.append("| Git | 2.30+ |")
        reqs.append("| Modern Browser | Chrome 90+, Firefox 88+ |")

        return "\n".join(reqs)

    def _format_dependencies(self) -> str:
        """Format project dependencies"""
        rows = []
        for dep in list(self.analysis.dependencies.keys())[:10]:
            rows.append(f"| {dep} | Required npm/pip package |")
        return "\n".join(rows)

    def _format_pages_list(self) -> str:
        """Format pages list"""
        if not self.analysis.pages:
            return "No pages detected."

        content = "| Page | File | Description |\n|------|------|-------------|\n"
        for page in self.analysis.pages[:10]:
            content += f"| {page.name} | `{page.file_path}` | {page.type.title()} page |\n"
        return content

    def _format_components_list(self) -> str:
        """Format components list"""
        if not self.analysis.components:
            return "No components detected."

        content = "| Component | File | Type |\n|-----------|------|------|\n"
        for comp in self.analysis.components[:15]:
            content += f"| {comp.name} | `{comp.file_path}` | {comp.type} |\n"
        return content

    def _format_system_features(self) -> str:
        """Format system features"""
        content = ""
        for i, module in enumerate(self.analysis.modules[:8], 1):
            content += f'''
#### Feature {i}: {module['name']}

**Description:** {module['description']}

**Related Requirements:**
'''
            # Find related requirements
            related = [r for r in self.analysis.functional_requirements
                      if module['name'].lower() in r.module.lower()][:3]
            for r in related:
                content += f"- {r.id}: {r.name}\n"

        return content

    def _format_project_structure(self) -> str:
        """Format project directory structure"""
        structure = f"{self.analysis.project_name}/\n"
        for dir_path in sorted(self.analysis.directories)[:20]:
            depth = dir_path.count('/')
            indent = "  " * (depth + 1)
            name = dir_path.split('/')[-1]
            structure += f"{indent}├── {name}/\n"
        return structure

    def _format_all_dependencies(self) -> str:
        """Format all dependencies"""
        content = "| Package | Version |\n|---------|--------|\n"
        for dep, version in list(self.analysis.dependencies.items())[:20]:
            ver = version if isinstance(version, str) else str(version)
            content += f"| {dep} | {ver[:20]} |\n"
        return content

    def _generate_glossary(self) -> str:
        """Generate glossary"""
        terms = [
            ("API", "Application Programming Interface"),
            ("CRUD", "Create, Read, Update, Delete"),
            ("JWT", "JSON Web Token"),
            ("REST", "Representational State Transfer"),
            ("UI", "User Interface"),
            ("UX", "User Experience"),
        ]

        content = "| Term | Definition |\n|------|------------|\n"
        for term, definition in terms:
            content += f"| {term} | {definition} |\n"

        # Add model names
        for model in self.analysis.models[:5]:
            content += f"| {model.name} | Data entity in the system |\n"

        return content

    def _detect_architecture_pattern(self) -> str:
        """Detect architecture pattern"""
        dirs = [d.lower() for d in self.analysis.directories]

        if any('controller' in d for d in dirs) and any('model' in d for d in dirs):
            return "MVC (Model-View-Controller)"
        elif any('service' in d for d in dirs) and any('repository' in d for d in dirs):
            return "Layered Architecture"
        elif any('domain' in d for d in dirs):
            return "Domain-Driven Design"
        else:
            return "Modular Architecture"

    def _format_component_overview(self) -> str:
        """Format component overview"""
        content = "| Component | Type | Count |\n|-----------|------|-------|\n"
        content += f"| API Endpoints | Backend | {len(self.analysis.api_endpoints)} |\n"
        content += f"| Database Models | Data | {len(self.analysis.models)} |\n"
        content += f"| UI Components | Frontend | {len(self.analysis.components)} |\n"
        content += f"| Pages | Frontend | {len(self.analysis.pages)} |\n"
        content += f"| Services | Backend | {len(self.analysis.services)} |\n"
        return content

    def _format_module_design(self) -> str:
        """Format module design"""
        content = ""
        for module in self.analysis.modules[:10]:
            content += f'''
#### {module['name']}

**Purpose:** {module['description']}

**Responsibilities:**
- Handle {module['name'].lower()} related operations
- Validate input data
- Process business logic
- Return appropriate responses

'''
        return content

    def _format_services(self) -> str:
        """Format services"""
        if not self.analysis.services:
            return "No services detected."

        content = ""
        for svc in self.analysis.services[:10]:
            content += f'''
#### {svc['name']}

**File:** `{svc['file']}`

**Methods:**
'''
            for method in svc.get('methods', [])[:5]:
                content += f"- `{method}()`\n"

        return content

    def _format_api_design(self) -> str:
        """Format API design details"""
        content = "### API Endpoints\n\n"
        for ep in self.analysis.api_endpoints[:20]:
            content += f'''
#### {ep.method} {ep.path}

- **Description:** {ep.description}
- **Module:** {ep.module}
- **Authentication:** Required

'''
        return content

    def _generate_data_flow(self) -> str:
        """Generate data flow description"""
        return '''
### Data Flow

1. **User Request** → Frontend captures user input
2. **API Call** → Frontend sends request to Backend API
3. **Validation** → Backend validates request data
4. **Business Logic** → Service layer processes the request
5. **Database Operation** → Repository layer interacts with database
6. **Response** → Backend returns response to Frontend
7. **UI Update** → Frontend updates the user interface
'''

    def _format_pages_design(self) -> str:
        """Format pages design"""
        content = ""
        for page in self.analysis.pages[:10]:
            content += f'''
#### {page.name}

- **File:** `{page.file_path}`
- **Type:** {page.type.title()}
- **Dependencies:** {', '.join(page.dependencies[:5]) if page.dependencies else 'None'}

'''
        return content

    def _format_components_design(self) -> str:
        """Format components design"""
        content = ""
        for comp in self.analysis.components[:10]:
            content += f'''
#### {comp.name}

- **File:** `{comp.file_path}`
- **Type:** {comp.type.title()}

'''
        return content

    def _format_api_interface_design(self) -> str:
        """Format API interface design"""
        return self._format_api_endpoints()

    def _format_test_items(self) -> str:
        """Format test items"""
        items = []
        for module in self.analysis.modules[:8]:
            items.append(f"| {module['name']} Module | {self.config.version} | {module['description']} |")
        return "\n".join(items)

    def _format_features_to_test(self) -> str:
        """Format features to test"""
        content = "| Feature | Priority | Description |\n|---------|----------|-------------|\n"
        for req in self.analysis.functional_requirements[:15]:
            content += f"| {req.name} | {req.priority} | {req.description[:50]}... |\n"
        return content

    def _format_test_cases(self) -> str:
        """Format test cases"""
        content = ""
        for tc in self.analysis.test_cases[:50]:
            content += f'''
#### {tc.id}: {tc.name}

| Attribute | Value |
|-----------|-------|
| Module | {tc.module} |
| Type | {tc.type} |
| Priority | {tc.priority} |

**Description:** {tc.description}

**Preconditions:**
{chr(10).join(['- ' + p for p in tc.preconditions])}

**Test Steps:**
{chr(10).join([f'{i+1}. {step}' for i, step in enumerate(tc.steps)])}

**Expected Result:** {tc.expected_result}

---
'''
        return content


def generate_dynamic_ieee_documents(
    project_path: str,
    config: DocumentConfig,
    output_dir: str
) -> Dict[str, str]:
    """Convenience function to generate all dynamic IEEE documents"""
    generator = DynamicIEEEGenerator(project_path, config)
    return generator.generate_all(output_dir)
