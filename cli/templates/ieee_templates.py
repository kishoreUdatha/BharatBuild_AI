"""
IEEE Standard Documentation Templates for Student Projects

Supports:
- IEEE 830 - Software Requirements Specification (SRS)
- IEEE 1016 - Software Design Description (SDD)
- IEEE 829 - Software Test Documentation
- IEEE 1058 - Software Project Management Plan (SPMP)
- IEEE 730 - Software Quality Assurance Plan (SQAP)
- IEEE 828 - Software Configuration Management Plan (SCMP)
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProjectInfo:
    """Project information for document generation"""
    title: str
    team_name: str
    team_members: list
    guide_name: str
    college_name: str
    department: str
    academic_year: str
    version: str = "1.0"
    date: str = None

    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%B %d, %Y")


# =============================================================================
# IEEE 830 - Software Requirements Specification (SRS)
# =============================================================================

IEEE_830_SRS_TEMPLATE = '''
# Software Requirements Specification

## For {project_title}

**Version {version}**

---

| Document Information | |
|---------------------|---|
| Project Title | {project_title} |
| Team Name | {team_name} |
| Version | {version} |
| Date | {date} |
| Status | Draft |

---

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | {date} | {team_name} | Initial SRS document |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Specific Requirements](#3-specific-requirements)
4. [Appendices](#4-appendices)

---

## 1. Introduction

### 1.1 Purpose

[Describe the purpose of this SRS document. Identify the intended audience.]

This Software Requirements Specification (SRS) document provides a complete description of all the requirements for the {project_title} system. It is intended for use by the development team, project stakeholders, and quality assurance team.

### 1.2 Scope

[Identify the software product(s) to be produced by name. Explain what the product will do and what it will not do.]

{project_title} is a software application that will:
- [List main features/capabilities]
- [Feature 2]
- [Feature 3]

The system will NOT:
- [List exclusions]

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| SRS | Software Requirements Specification |
| API | Application Programming Interface |
| UI | User Interface |
| [Add more terms] | [Definitions] |

### 1.4 References

1. IEEE Std 830-1998, IEEE Recommended Practice for Software Requirements Specifications
2. [Add project-specific references]

### 1.5 Overview

This document is organized as follows:
- **Section 2** provides an overall description of the product
- **Section 3** contains the specific functional and non-functional requirements
- **Section 4** contains supporting appendices

---

## 2. Overall Description

### 2.1 Product Perspective

[Describe the context and origin of the product. Is it a new product? A replacement? Part of a larger system?]

{project_title} is a [standalone/component of larger system] that [brief description].

#### 2.1.1 System Interfaces

[List external systems that interact with this product]

#### 2.1.2 User Interfaces

[Describe the logical characteristics of each interface between the software and users]

#### 2.1.3 Hardware Interfaces

[Specify the logical characteristics of each interface between the software and hardware]

#### 2.1.4 Software Interfaces

[Specify the use of other required software products and interfaces]

| Software | Version | Purpose |
|----------|---------|---------|
| [Database] | [Version] | [Data storage] |
| [Framework] | [Version] | [Purpose] |

#### 2.1.5 Communication Interfaces

[Describe communication interfaces such as network protocols, email, etc.]

### 2.2 Product Functions

[Summarize the major functions the product must perform]

1. **[Function 1]**: [Brief description]
2. **[Function 2]**: [Brief description]
3. **[Function 3]**: [Brief description]

### 2.3 User Characteristics

[Describe the general characteristics of the intended users]

| User Type | Description | Technical Expertise |
|-----------|-------------|---------------------|
| Administrator | System administrator | High |
| End User | Regular users | Low to Medium |
| [Add more] | | |

### 2.4 Constraints

[List any constraints that will limit the developers' options]

1. **Technical Constraints**: [List constraints]
2. **Regulatory Constraints**: [List constraints]
3. **Business Constraints**: [List constraints]

### 2.5 Assumptions and Dependencies

**Assumptions:**
1. [List assumptions made]
2. [Assumption 2]

**Dependencies:**
1. [List external factors the project depends on]
2. [Dependency 2]

---

## 3. Specific Requirements

### 3.1 External Interface Requirements

#### 3.1.1 User Interfaces

| UI-ID | Description | Priority |
|-------|-------------|----------|
| UI-01 | Login screen with username/password fields | High |
| UI-02 | Dashboard displaying summary information | High |
| [Add more] | | |

#### 3.1.2 Hardware Interfaces

[Specify hardware interface requirements]

#### 3.1.3 Software Interfaces

[Specify software interface requirements]

### 3.2 Functional Requirements

#### 3.2.1 [Feature/Module 1]

| Req ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| FR-001 | The system shall allow users to register with email and password | High | Proposed |
| FR-002 | The system shall validate email format during registration | High | Proposed |
| FR-003 | [Add requirement] | Medium | Proposed |

#### 3.2.2 [Feature/Module 2]

| Req ID | Requirement | Priority | Status |
|--------|-------------|----------|--------|
| FR-010 | [Requirement description] | High | Proposed |
| FR-011 | [Requirement description] | Medium | Proposed |

### 3.3 Non-Functional Requirements

#### 3.3.1 Performance Requirements

| Req ID | Requirement | Metric |
|--------|-------------|--------|
| NFR-P01 | System shall respond to user requests within 2 seconds | Response time < 2s |
| NFR-P02 | System shall support 100 concurrent users | Concurrent users >= 100 |

#### 3.3.2 Safety Requirements

[Specify requirements to prevent unsafe operations]

#### 3.3.3 Security Requirements

| Req ID | Requirement | Priority |
|--------|-------------|----------|
| NFR-S01 | All passwords shall be encrypted using bcrypt | High |
| NFR-S02 | Sessions shall expire after 30 minutes of inactivity | High |
| NFR-S03 | System shall implement HTTPS for all communications | High |

#### 3.3.4 Software Quality Attributes

**Reliability:**
- System uptime shall be 99.5%
- Mean Time Between Failures (MTBF) shall be > 720 hours

**Maintainability:**
- Code shall follow [coding standard]
- All modules shall have > 80% test coverage

**Portability:**
- System shall run on Windows, Linux, and macOS

**Usability:**
- New users shall be able to complete basic tasks within 5 minutes
- System shall conform to WCAG 2.1 Level AA accessibility standards

---

## 4. Appendices

### Appendix A: Glossary

[Additional terms and definitions]

### Appendix B: Analysis Models

[Include any data flow diagrams, entity-relationship diagrams, etc.]

### Appendix C: To Be Determined List

| TBD ID | Description | Target Resolution Date |
|--------|-------------|----------------------|
| TBD-01 | [Item to be determined] | [Date] |

---

## Document Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Guide | {guide_name} | | |
| Team Lead | | | |
| Team Members | {team_members_str} | | |

---

**Prepared by:** {team_name}
**{college_name}**
**{department}**
**Academic Year: {academic_year}**
'''


# =============================================================================
# IEEE 1016 - Software Design Description (SDD)
# =============================================================================

IEEE_1016_SDD_TEMPLATE = '''
# Software Design Description

## For {project_title}

**Version {version}**

---

| Document Information | |
|---------------------|---|
| Project Title | {project_title} |
| Team Name | {team_name} |
| Version | {version} |
| Date | {date} |

---

## Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 1.0 | {date} | {team_name} | Initial SDD document |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Considerations](#2-design-considerations)
3. [Architectural Design](#3-architectural-design)
4. [Data Design](#4-data-design)
5. [Component Design](#5-component-design)
6. [User Interface Design](#6-user-interface-design)

---

## 1. Introduction

### 1.1 Purpose

This Software Design Description (SDD) document describes the architecture and system design of {project_title}. It provides a detailed design view of the system based on the requirements specified in the SRS document.

### 1.2 Scope

This document covers:
- System architecture and design decisions
- Data design and database schema
- Component interfaces and interactions
- User interface design

### 1.3 Definitions and Acronyms

| Term | Definition |
|------|------------|
| SDD | Software Design Description |
| API | Application Programming Interface |
| MVC | Model-View-Controller |
| REST | Representational State Transfer |

### 1.4 References

1. IEEE Std 1016-2009, IEEE Standard for Information Technology—Systems Design—Software Design Descriptions
2. Software Requirements Specification for {project_title}

---

## 2. Design Considerations

### 2.1 Assumptions and Dependencies

**Assumptions:**
1. [List design assumptions]
2. Users have access to modern web browsers

**Dependencies:**
1. [List external dependencies]
2. [Database system]
3. [Third-party APIs]

### 2.2 General Constraints

1. **Technology Constraints**: [List constraints]
2. **Time Constraints**: Project must be completed by [date]
3. **Resource Constraints**: [List constraints]

### 2.3 Goals and Guidelines

- **Modularity**: System shall be designed with loosely coupled modules
- **Scalability**: Architecture shall support horizontal scaling
- **Security**: Security shall be considered at every layer
- **Maintainability**: Code shall follow clean code principles

### 2.4 Development Methods

- **Methodology**: [Agile/Waterfall/Hybrid]
- **Version Control**: Git
- **Code Review**: All code changes require peer review
- **Testing Strategy**: Unit testing, Integration testing, System testing

---

## 3. Architectural Design

### 3.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Web UI    │  │  Mobile App │  │   API Docs  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Controllers │  │  Services   │  │  Middleware │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Models    │  │ Repositories│  │    Cache    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE LAYER                           │
│  ┌─────────────┐  ┌─────────────┐                          │
│  │  Primary DB │  │  Redis Cache│                          │
│  └─────────────┘  └─────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Architecture Pattern

**Pattern Used**: [MVC / Microservices / Layered / etc.]

**Justification**: [Explain why this pattern was chosen]

### 3.3 Component Overview

| Component | Description | Technology |
|-----------|-------------|------------|
| Frontend | User interface | React/Vue/Angular |
| Backend API | Business logic | Node.js/Python/Java |
| Database | Data persistence | PostgreSQL/MongoDB |
| Cache | Performance optimization | Redis |

---

## 4. Data Design

### 4.1 Database Design

#### 4.1.1 Entity-Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    USERS     │       │   PROJECTS   │       │    TASKS     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │───┐   │ id (PK)      │───┐   │ id (PK)      │
│ name         │   │   │ name         │   │   │ title        │
│ email        │   │   │ description  │   │   │ description  │
│ password     │   └──▶│ owner_id(FK) │   └──▶│ project_id(FK│
│ created_at   │       │ created_at   │       │ status       │
└──────────────┘       └──────────────┘       │ created_at   │
                                              └──────────────┘
```

#### 4.1.2 Table Definitions

**Table: users**

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique identifier |
| name | VARCHAR(100) | NOT NULL | User's full name |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User's email |
| password | VARCHAR(255) | NOT NULL | Hashed password |
| created_at | TIMESTAMP | DEFAULT NOW() | Creation timestamp |

**Table: [Add more tables]**

### 4.2 Data Flow

```
User Input → Validation → Controller → Service → Repository → Database
                                                      ↓
User Output ← Response ← Controller ← Service ← Repository ←
```

---

## 5. Component Design

### 5.1 Module: Authentication

**Purpose**: Handle user authentication and authorization

**Interfaces**:
```
POST /api/auth/register - Register new user
POST /api/auth/login    - User login
POST /api/auth/logout   - User logout
GET  /api/auth/profile  - Get user profile
```

**Dependencies**: Database, JWT library

**Processing**: [Describe the logic]

### 5.2 Module: [Module Name]

**Purpose**: [Description]

**Interfaces**:
```
[List API endpoints or function signatures]
```

**Dependencies**: [List dependencies]

**Processing**: [Describe the logic]

---

## 6. User Interface Design

### 6.1 Screen Layout

#### 6.1.1 Login Screen

```
┌────────────────────────────────────────┐
│              {project_title}            │
├────────────────────────────────────────┤
│                                        │
│     ┌──────────────────────────┐      │
│     │ Email                    │      │
│     └──────────────────────────┘      │
│                                        │
│     ┌──────────────────────────┐      │
│     │ Password                 │      │
│     └──────────────────────────┘      │
│                                        │
│     ┌──────────────────────────┐      │
│     │        LOGIN             │      │
│     └──────────────────────────┘      │
│                                        │
│     Don't have account? Register       │
└────────────────────────────────────────┘
```

#### 6.1.2 Dashboard Screen

```
┌────────────────────────────────────────────────────────────┐
│  Logo    Home  Projects  Settings              User ▼      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │  Card 1     │  │  Card 2     │  │  Card 3     │       │
│  │  Stats      │  │  Stats      │  │  Stats      │       │
│  └─────────────┘  └─────────────┘  └─────────────┘       │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │                                                    │   │
│  │              Main Content Area                     │   │
│  │                                                    │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

### 6.2 Navigation Flow

```
Login → Dashboard → [Feature Screens] → Logout
              ↓
         Settings
```

---

## 7. Appendices

### Appendix A: API Documentation

[Detailed API documentation]

### Appendix B: Database Scripts

[SQL scripts for database creation]

---

**Prepared by:** {team_name}
**{college_name}**
**{department}**
**Academic Year: {academic_year}**
'''


# =============================================================================
# IEEE 829 - Software Test Documentation
# =============================================================================

IEEE_829_TEST_TEMPLATE = '''
# Software Test Documentation

## For {project_title}

**Version {version}**

---

| Document Information | |
|---------------------|---|
| Project Title | {project_title} |
| Team Name | {team_name} |
| Version | {version} |
| Date | {date} |

---

## Table of Contents

1. [Test Plan](#1-test-plan)
2. [Test Design Specification](#2-test-design-specification)
3. [Test Case Specification](#3-test-case-specification)
4. [Test Procedure Specification](#4-test-procedure-specification)
5. [Test Summary Report](#5-test-summary-report)

---

## 1. Test Plan

### 1.1 Test Plan Identifier

TP-{project_title_short}-001

### 1.2 Introduction

This document describes the test plan for {project_title}. It outlines the testing strategy, scope, resources, and schedule for the testing activities.

### 1.3 Test Items

| Item | Version | Description |
|------|---------|-------------|
| {project_title} | {version} | Complete system |
| User Authentication Module | {version} | Login, Registration, Profile |
| [Add more modules] | | |

### 1.4 Features to be Tested

| Feature ID | Feature Description | Priority |
|------------|---------------------|----------|
| F-001 | User Registration | High |
| F-002 | User Login | High |
| F-003 | Password Reset | Medium |
| F-004 | [Add more features] | |

### 1.5 Features Not to be Tested

| Feature | Reason |
|---------|--------|
| [Feature] | [Reason - e.g., Third-party component] |

### 1.6 Approach

**Testing Levels:**
1. **Unit Testing**: Test individual components/functions
2. **Integration Testing**: Test component interactions
3. **System Testing**: Test complete system functionality
4. **User Acceptance Testing (UAT)**: Validate with end users

**Testing Types:**
- Functional Testing
- Performance Testing
- Security Testing
- Usability Testing

### 1.7 Item Pass/Fail Criteria

| Criteria | Pass Condition |
|----------|---------------|
| Unit Tests | 100% pass rate |
| Integration Tests | 95% pass rate |
| Critical Defects | 0 open critical defects |
| Code Coverage | Minimum 80% |

### 1.8 Test Environment

| Component | Specification |
|-----------|--------------|
| Operating System | Windows 10 / Ubuntu 20.04 |
| Browser | Chrome 90+, Firefox 88+ |
| Database | PostgreSQL 13 |
| Test Framework | Jest / PyTest / JUnit |

### 1.9 Schedule

| Activity | Start Date | End Date |
|----------|------------|----------|
| Unit Testing | [Date] | [Date] |
| Integration Testing | [Date] | [Date] |
| System Testing | [Date] | [Date] |
| UAT | [Date] | [Date] |

### 1.10 Responsibilities

| Role | Name | Responsibilities |
|------|------|------------------|
| Test Lead | | Overall test coordination |
| Tester | | Execute test cases |
| Developer | | Fix defects |

---

## 2. Test Design Specification

### 2.1 Test Design Identifier

TD-{project_title_short}-001

### 2.2 Features to be Tested

#### 2.2.1 User Authentication

**Test Approach**: Black-box testing
**Test Techniques**:
- Equivalence Partitioning
- Boundary Value Analysis
- Error Guessing

**Test Coverage Items**:
- Valid login credentials
- Invalid login credentials
- Empty fields
- SQL injection attempts
- Session management

### 2.3 Test Identification

| Test ID | Feature | Test Type | Priority |
|---------|---------|-----------|----------|
| TC-AUTH-001 | Login - Valid credentials | Functional | High |
| TC-AUTH-002 | Login - Invalid password | Functional | High |
| TC-AUTH-003 | Login - SQL injection | Security | High |
| TC-REG-001 | Registration - Valid data | Functional | High |
| TC-REG-002 | Registration - Duplicate email | Functional | Medium |

---

## 3. Test Case Specification

### Test Case: TC-AUTH-001

| Field | Value |
|-------|-------|
| **Test Case ID** | TC-AUTH-001 |
| **Test Case Name** | Login with Valid Credentials |
| **Module** | Authentication |
| **Priority** | High |
| **Created By** | {team_name} |
| **Created Date** | {date} |

**Preconditions:**
1. User is registered in the system
2. User is on the login page

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login page is displayed |
| 2 | Enter valid email | Email field accepts input |
| 3 | Enter valid password | Password field accepts input (masked) |
| 4 | Click Login button | User is logged in successfully |
| 5 | Verify dashboard | Dashboard is displayed |

**Test Data:**
- Email: testuser@example.com
- Password: Test@123

**Expected Result:** User should be redirected to dashboard with success message

**Actual Result:** [To be filled during execution]

**Status:** [Pass/Fail/Blocked]

---

### Test Case: TC-AUTH-002

| Field | Value |
|-------|-------|
| **Test Case ID** | TC-AUTH-002 |
| **Test Case Name** | Login with Invalid Password |
| **Module** | Authentication |
| **Priority** | High |

**Preconditions:**
1. User is registered in the system

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to login page | Login page is displayed |
| 2 | Enter valid email | Email field accepts input |
| 3 | Enter invalid password | Password field accepts input |
| 4 | Click Login button | Error message displayed |

**Expected Result:** "Invalid email or password" error message should be displayed

---

### Test Case: TC-AUTH-003

| Field | Value |
|-------|-------|
| **Test Case ID** | TC-AUTH-003 |
| **Test Case Name** | Login - SQL Injection Attempt |
| **Module** | Authentication |
| **Priority** | High |
| **Type** | Security |

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Enter `' OR '1'='1` in email field | Input is sanitized |
| 2 | Enter any password | |
| 3 | Click Login | Attack is prevented |

**Expected Result:** System should prevent SQL injection and show error message

---

### Test Case: TC-REG-001

| Field | Value |
|-------|-------|
| **Test Case ID** | TC-REG-001 |
| **Test Case Name** | User Registration - Valid Data |
| **Module** | Authentication |
| **Priority** | High |

**Test Steps:**

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to registration page | Registration form displayed |
| 2 | Enter valid name | Field accepts input |
| 3 | Enter valid email | Field accepts input |
| 4 | Enter valid password | Field accepts input |
| 5 | Confirm password | Passwords match |
| 6 | Click Register | Account created successfully |

**Test Data:**
- Name: Test User
- Email: newuser@example.com
- Password: Test@123

---

## 4. Test Procedure Specification

### 4.1 Test Execution Order

1. Unit Tests (automated)
2. Integration Tests (automated)
3. System Tests (manual + automated)
4. Security Tests
5. Performance Tests
6. UAT

### 4.2 Test Execution Procedure

1. Set up test environment
2. Load test data
3. Execute test cases in priority order
4. Document results
5. Report defects
6. Retest after fixes

---

## 5. Test Summary Report

### 5.1 Summary

| Metric | Value |
|--------|-------|
| Total Test Cases | [Number] |
| Executed | [Number] |
| Passed | [Number] |
| Failed | [Number] |
| Blocked | [Number] |
| Pass Rate | [Percentage] |

### 5.2 Defect Summary

| Severity | Open | Fixed | Closed |
|----------|------|-------|--------|
| Critical | | | |
| High | | | |
| Medium | | | |
| Low | | | |

### 5.3 Test Coverage

| Module | Test Cases | Executed | Pass Rate |
|--------|------------|----------|-----------|
| Authentication | | | |
| [Module 2] | | | |
| [Module 3] | | | |

### 5.4 Recommendations

[List recommendations based on testing results]

---

**Prepared by:** {team_name}
**{college_name}**
**{department}**
**Academic Year: {academic_year}**
'''


# =============================================================================
# IEEE 1058 - Software Project Management Plan (SPMP)
# =============================================================================

IEEE_1058_SPMP_TEMPLATE = '''
# Software Project Management Plan

## For {project_title}

**Version {version}**

---

| Document Information | |
|---------------------|---|
| Project Title | {project_title} |
| Team Name | {team_name} |
| Version | {version} |
| Date | {date} |

---

## 1. Introduction

### 1.1 Project Overview

{project_title} is a software project developed by {team_name} at {college_name}, {department} during the academic year {academic_year}.

### 1.2 Project Deliverables

| Deliverable | Description | Due Date |
|-------------|-------------|----------|
| SRS Document | Software Requirements Specification | [Date] |
| SDD Document | Software Design Description | [Date] |
| Source Code | Complete implementation | [Date] |
| Test Report | Testing documentation | [Date] |
| User Manual | End-user documentation | [Date] |
| Final Report | Project report | [Date] |

### 1.3 Reference Materials

1. IEEE Std 1058-1998, IEEE Standard for Software Project Management Plans
2. Project SRS Document
3. College project guidelines

---

## 2. Project Organization

### 2.1 Team Structure

```
                    ┌─────────────────┐
                    │  Project Guide  │
                    │  {guide_name}   │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Team Lead     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴───────┐   ┌───────┴───────┐   ┌───────┴───────┐
│   Developer   │   │   Developer   │   │    Tester     │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 2.2 Team Members and Roles

| Name | Role | Responsibilities |
|------|------|------------------|
{team_members_table}

### 2.3 External Interfaces

| Interface | Contact | Purpose |
|-----------|---------|---------|
| Project Guide | {guide_name} | Technical guidance |
| Department | {department} | Administrative support |

---

## 3. Managerial Process

### 3.1 Project Schedule (Gantt Chart Representation)

```
Phase                   | Week 1 | Week 2 | Week 3 | Week 4 | Week 5 | Week 6 |
------------------------|--------|--------|--------|--------|--------|--------|
Requirements Analysis   | ██████ | ██████ |        |        |        |        |
System Design          |        | ██████ | ██████ |        |        |        |
Implementation         |        |        | ██████ | ██████ | ██████ |        |
Testing                |        |        |        | ██████ | ██████ | ██████ |
Documentation          |        |        |        |        | ██████ | ██████ |
Final Review           |        |        |        |        |        | ██████ |
```

### 3.2 Milestones

| Milestone | Description | Target Date | Status |
|-----------|-------------|-------------|--------|
| M1 | Requirements Complete | [Date] | [Status] |
| M2 | Design Complete | [Date] | [Status] |
| M3 | Implementation Complete | [Date] | [Status] |
| M4 | Testing Complete | [Date] | [Status] |
| M5 | Project Submission | [Date] | [Status] |

### 3.3 Risk Management

| Risk ID | Risk Description | Probability | Impact | Mitigation Strategy |
|---------|------------------|-------------|--------|---------------------|
| R1 | Scope creep | Medium | High | Strict change control |
| R2 | Technical complexity | Medium | Medium | Prototyping, research |
| R3 | Team member unavailability | Low | High | Cross-training |
| R4 | Technology issues | Low | Medium | Backup alternatives |

---

## 4. Technical Process

### 4.1 Development Methodology

**Methodology**: [Agile/Waterfall/Iterative]

**Tools and Technologies**:

| Category | Tool/Technology |
|----------|-----------------|
| Programming Language | [Language] |
| Framework | [Framework] |
| Database | [Database] |
| Version Control | Git/GitHub |
| IDE | [IDE] |
| Project Management | [Tool] |

### 4.2 Quality Assurance

- Code reviews before merging
- Unit test coverage > 80%
- Documentation for all modules
- Regular project meetings

---

## 5. Work Packages and Dependencies

### 5.1 Work Breakdown Structure (WBS)

```
{project_title}
├── 1.0 Project Management
│   ├── 1.1 Planning
│   ├── 1.2 Monitoring
│   └── 1.3 Reporting
├── 2.0 Requirements
│   ├── 2.1 Gathering
│   ├── 2.2 Analysis
│   └── 2.3 Documentation
├── 3.0 Design
│   ├── 3.1 System Architecture
│   ├── 3.2 Database Design
│   └── 3.3 UI Design
├── 4.0 Implementation
│   ├── 4.1 Backend Development
│   ├── 4.2 Frontend Development
│   └── 4.3 Integration
├── 5.0 Testing
│   ├── 5.1 Unit Testing
│   ├── 5.2 Integration Testing
│   └── 5.3 System Testing
└── 6.0 Deployment
    ├── 6.1 Documentation
    └── 6.2 Handover
```

---

## 6. Resource Allocation

### 6.1 Human Resources

| Resource | Allocation | Duration |
|----------|------------|----------|
| Team Lead | 100% | Full project |
| Developers | 100% | Full project |
| Tester | 50% | Testing phase |

### 6.2 Hardware Resources

| Resource | Specification | Purpose |
|----------|--------------|---------|
| Development PCs | [Specs] | Development |
| Server | [Specs] | Deployment |

### 6.3 Software Resources

| Software | License | Purpose |
|----------|---------|---------|
| [IDE] | [License type] | Development |
| [Database] | [License type] | Data storage |

---

## 7. Budget (if applicable)

| Item | Cost | Notes |
|------|------|-------|
| Cloud hosting | | |
| Software licenses | | |
| Miscellaneous | | |
| **Total** | | |

---

**Prepared by:** {team_name}
**Project Guide:** {guide_name}
**{college_name}**
**{department}**
**Academic Year: {academic_year}**
'''


# =============================================================================
# Additional Templates
# =============================================================================

IEEE_USER_MANUAL_TEMPLATE = '''
# User Manual

## {project_title}

**Version {version}**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation Guide](#3-installation-guide)
4. [Getting Started](#4-getting-started)
5. [Features Guide](#5-features-guide)
6. [Troubleshooting](#6-troubleshooting)
7. [FAQ](#7-faq)

---

## 1. Introduction

### 1.1 Purpose

This user manual provides instructions for using {project_title}.

### 1.2 Intended Audience

This manual is intended for:
- End users
- System administrators
- Technical support staff

---

## 2. System Requirements

### 2.1 Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| Operating System | Windows 10 / macOS 10.14 / Ubuntu 18.04 |
| RAM | 4 GB |
| Storage | 500 MB free space |
| Browser | Chrome 80+ / Firefox 75+ |

### 2.2 Recommended Requirements

| Component | Requirement |
|-----------|-------------|
| RAM | 8 GB |
| Storage | 1 GB free space |
| Internet | Broadband connection |

---

## 3. Installation Guide

### 3.1 Step-by-Step Installation

1. [Step 1 - Download/Clone]
2. [Step 2 - Install dependencies]
3. [Step 3 - Configure settings]
4. [Step 4 - Run application]

---

## 4. Getting Started

### 4.1 First-Time Setup

[Instructions for first-time users]

### 4.2 Login/Registration

[How to create account and login]

---

## 5. Features Guide

### 5.1 Feature 1

[Detailed instructions with screenshots]

### 5.2 Feature 2

[Detailed instructions with screenshots]

---

## 6. Troubleshooting

### 6.1 Common Issues

| Issue | Solution |
|-------|----------|
| Cannot login | Check credentials, clear cache |
| Page not loading | Check internet connection |

---

## 7. FAQ

**Q: [Question 1]?**
A: [Answer]

**Q: [Question 2]?**
A: [Answer]

---

**{college_name}**
**{department}**
**{academic_year}**
'''


# =============================================================================
# Template Registry and Helper Functions
# =============================================================================

IEEE_TEMPLATES = {
    "srs": {
        "name": "Software Requirements Specification (IEEE 830)",
        "standard": "IEEE 830-1998",
        "template": IEEE_830_SRS_TEMPLATE,
        "filename": "SRS_Document.md",
        "description": "Comprehensive requirements specification following IEEE 830 standard"
    },
    "sdd": {
        "name": "Software Design Description (IEEE 1016)",
        "standard": "IEEE 1016-2009",
        "template": IEEE_1016_SDD_TEMPLATE,
        "filename": "SDD_Document.md",
        "description": "Detailed software design document following IEEE 1016 standard"
    },
    "test": {
        "name": "Software Test Documentation (IEEE 829)",
        "standard": "IEEE 829-2008",
        "template": IEEE_829_TEST_TEMPLATE,
        "filename": "Test_Documentation.md",
        "description": "Complete test plan and test cases following IEEE 829 standard"
    },
    "spmp": {
        "name": "Software Project Management Plan (IEEE 1058)",
        "standard": "IEEE 1058-1998",
        "template": IEEE_1058_SPMP_TEMPLATE,
        "filename": "SPMP_Document.md",
        "description": "Project management plan following IEEE 1058 standard"
    },
    "user_manual": {
        "name": "User Manual",
        "standard": "General",
        "template": IEEE_USER_MANUAL_TEMPLATE,
        "filename": "User_Manual.md",
        "description": "End-user documentation and guide"
    }
}


def generate_ieee_document(
    template_id: str,
    project_info: ProjectInfo,
    output_path: Optional[str] = None
) -> str:
    """
    Generate an IEEE standard document from template.

    Args:
        template_id: One of 'srs', 'sdd', 'test', 'spmp', 'user_manual'
        project_info: ProjectInfo dataclass with project details
        output_path: Optional path to save the document

    Returns:
        Generated document content as string
    """
    if template_id not in IEEE_TEMPLATES:
        raise ValueError(f"Unknown template: {template_id}. Available: {list(IEEE_TEMPLATES.keys())}")

    template = IEEE_TEMPLATES[template_id]["template"]

    # Format team members
    team_members_str = ", ".join(project_info.team_members)
    team_members_table = "\n".join([
        f"| {member} | Developer | Development, Testing |"
        for member in project_info.team_members
    ])

    # Generate short project title for IDs
    project_title_short = "".join(
        word[0].upper() for word in project_info.title.split()[:3]
    )

    # Fill template
    content = template.format(
        project_title=project_info.title,
        project_title_short=project_title_short,
        team_name=project_info.team_name,
        team_members_str=team_members_str,
        team_members_table=team_members_table,
        guide_name=project_info.guide_name,
        college_name=project_info.college_name,
        department=project_info.department,
        academic_year=project_info.academic_year,
        version=project_info.version,
        date=project_info.date
    )

    # Save if output path provided
    if output_path:
        import os
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)

    return content


def generate_all_ieee_documents(
    project_info: ProjectInfo,
    output_dir: str = "docs"
) -> Dict[str, str]:
    """
    Generate all IEEE standard documents for a project.

    Args:
        project_info: ProjectInfo dataclass with project details
        output_dir: Directory to save documents

    Returns:
        Dictionary mapping template_id to file path
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    generated_files = {}

    for template_id, template_info in IEEE_TEMPLATES.items():
        filename = template_info["filename"]
        output_path = os.path.join(output_dir, filename)

        generate_ieee_document(template_id, project_info, output_path)
        generated_files[template_id] = output_path

    return generated_files


def list_ieee_templates() -> Dict[str, Dict[str, str]]:
    """List all available IEEE document templates."""
    return {
        tid: {
            "name": info["name"],
            "standard": info["standard"],
            "description": info["description"],
            "filename": info["filename"]
        }
        for tid, info in IEEE_TEMPLATES.items()
    }
