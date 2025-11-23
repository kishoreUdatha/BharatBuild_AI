# SOFTWARE REQUIREMENTS SPECIFICATION (SRS)

**Project Name:** BharatBuild AI Platform
**Version:** 1.0
**Date:** November 23, 2025
**Document Standard:** IEEE 830-1998

---

## TABLE OF CONTENTS

1. Introduction
   - 1.1 Purpose
   - 1.2 Scope
   - 1.3 Definitions, Acronyms, and Abbreviations
   - 1.4 References
   - 1.5 Overview

2. Overall Description
   - 2.1 Product Perspective
   - 2.2 Product Functions
   - 2.3 User Characteristics
   - 2.4 Constraints
   - 2.5 Assumptions and Dependencies

3. Specific Requirements
   - 3.1 Functional Requirements
   - 3.2 Non-Functional Requirements
   - 3.3 External Interface Requirements
   - 3.4 System Features

---

## 1. INTRODUCTION

### 1.1 Purpose
This Software Requirements Specification (SRS) document provides a complete description of the BharatBuild AI platform. It details the functional and non-functional requirements, system constraints, and interface specifications for the development team, project stakeholders, and quality assurance personnel.

### 1.2 Scope
BharatBuild AI is an intelligent multi-agent platform designed to automate academic project generation and accelerate software development processes.

**In Scope:**
- Multi-mode operation (Student, Developer, Founder, College, API Partner)
- AI-powered document generation (SRS, UML, reports, presentations, code)
- Real-time code generation with streaming capabilities
- Token-based economy with usage tracking
- User authentication and authorization (JWT, OAuth)
- Payment integration (Razorpay)
- API access for third-party integrations

**Out of Scope:**
- In-browser code execution
- Mobile native applications
- Video tutorial generation
- Plagiarism detection
- Direct deployment to cloud platforms

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| AI | Artificial Intelligence |
| API | Application Programming Interface |
| JWT | JSON Web Token |
| LLM | Large Language Model |
| OAuth | Open Authorization |
| PRD | Product Requirements Document |
| SRS | Software Requirements Specification |
| SSE | Server-Sent Events |
| UML | Unified Modeling Language |
| UUID | Universally Unique Identifier |

### 1.4 References
- IEEE Std 830-1998: IEEE Recommended Practice for Software Requirements Specifications
- FastAPI Documentation: https://fastapi.tiangolo.com
- Next.js Documentation: https://nextjs.org/docs
- Anthropic Claude API Documentation: https://docs.anthropic.com

### 1.5 Overview
This SRS document is organized into four main sections covering introduction, general system description, detailed specific requirements, and system models.

---

## 2. OVERALL DESCRIPTION

### 2.1 Product Perspective
BharatBuild AI is a standalone web-based platform that integrates with external AI services (Anthropic Claude), payment gateways (Razorpay), cloud storage (AWS S3/MinIO), and authentication providers (Google OAuth).

### 2.2 Product Functions
1. **User Management:** Registration, login, profile management, role-based access
2. **Academic Project Generation:** SRS, UML, code, reports, presentations, viva Q&A
3. **Rapid Code Generation:** Bolt.new-style interactive development
4. **Business Planning:** PRD and business plan generation
5. **College Administration:** Faculty, student, batch management
6. **API Access:** RESTful API for third-party integrations
7. **Multi-Agent Orchestration:** 16 specialized AI agents
8. **Token Economy:** Balance management, usage tracking, billing

### 2.3 User Characteristics

| User Type | Technical Expertise | Primary Goals |
|-----------|---------------------|---------------|
| Student | Low to Medium | Generate academic projects quickly |
| Developer | High | Rapid prototyping, code generation |
| Founder | Medium | Business planning, PRD generation |
| Faculty | Medium | Monitor student projects |
| Admin | Low to Medium | Manage institution activities |
| API Partner | High | Programmatic access to AI capabilities |

### 2.4 Constraints
- AI API dependency on Anthropic Claude availability
- Token limits (200K context window for Claude)
- Rate limiting enforced by Anthropic API
- Browser compatibility requirements
- Database performance limits
- Storage costs scale with document volume

### 2.5 Assumptions and Dependencies
- Users have stable internet connectivity (minimum 2 Mbps)
- Target users familiar with basic software development concepts
- Claude API maintains service availability > 99%
- Educational institutions approve AI-generated content use
- Users have valid payment methods for token purchases

---

## 3. SPECIFIC REQUIREMENTS

### 3.1 Functional Requirements

#### FR-UM: User Management Module

**FR-UM-001: User Registration**
- System shall allow new users to register with email and password
- Input: Email, username, full name, password, role
- Processing: Validate email uniqueness, hash password with bcrypt
- Output: User account created, JWT tokens issued
- Priority: High

**FR-UM-002: User Login**
- Registered users shall authenticate with credentials
- Input: Email/username, password
- Processing: Verify credentials, generate JWT tokens
- Output: Access token (15 min), refresh token (7 days)
- Priority: High

**FR-UM-003: Google OAuth Login**
- Users shall authenticate using Google account
- Input: Google authorization code
- Processing: Verify with Google, create/update user, issue JWT
- Output: User authenticated, session created
- Priority: Medium

**FR-UM-004: Profile Management**
- Users shall update profile information
- Input: Full name, avatar, phone, organization, bio
- Processing: Validate inputs, update user record
- Output: Profile updated confirmation
- Priority: Medium

**FR-UM-005: Role-Based Access Control**
- System shall enforce permissions based on user roles
- Roles: student, developer, founder, faculty, admin, api_partner
- Processing: Check role before granting access
- Priority: High

#### FR-PM: Project Management Module

**FR-PM-001: Create Project**
- Users shall create new projects with mode-specific configurations
- Input: Title, description, mode, config JSON
- Processing: Validate inputs, create project record (status: draft)
- Output: Project created with UUID
- Priority: High

**FR-PM-002: List User Projects**
- Users shall view all their projects with filtering
- Input: User ID, filters (status, mode, date range)
- Processing: Query projects with pagination
- Output: Paginated project list (20 per page)
- Priority: High

**FR-PM-003: Execute Project**
- Users shall trigger multi-agent execution
- Input: Project UUID
- Processing: Validate token balance, queue Celery task
- Output: Celery task ID, execution started
- Priority: High

**FR-PM-004: Download Project Package**
- Users shall download complete project as ZIP
- Input: Project UUID
- Processing: Gather all files, create ZIP archive
- Output: ZIP file download
- Priority: High

#### FR-MA: Multi-Agent Execution Module

**FR-MA-001: Student Mode Execution**
- System shall execute student project workflow
- Agents: Idea → SRS → UML → Code → Report → PPT → Viva
- Input: Title, domain, tech_stack, requirements
- Processing: Sequential agent execution with context passing
- Output: 7 documents (SRS, UML, Code, Report, PPT, Viva, Explanation)
- Duration: 12-15 minutes
- Priority: High

**FR-MA-002: Developer Mode Execution**
- System shall execute code generation workflow
- Modes: full, code_only, debug_only, explain_only
- Input: User prompt, framework, deployment_target
- Processing: Execute relevant agents based on mode
- Output: Source code files, documentation
- Priority: High

**FR-MA-003: Real-Time Streaming**
- System shall stream execution progress via SSE
- Events: agent_start, agent_progress, agent_complete, error
- Processing: Publish events to SSE endpoint
- Output: JSON events with status and data
- Priority: High

**FR-MA-004: Token Usage Tracking**
- System shall track tokens consumed per agent
- Processing: Count tokens, calculate cost, deduct from balance
- Output: Usage logged to database
- Priority: High

#### FR-DM: Document Management Module

**FR-DM-001: Document Upload**
- System shall upload generated documents to S3/MinIO
- Input: File content, project_id, doc_type
- Processing: Upload to S3, create document record
- Output: Document metadata with file_url
- Priority: High

**FR-DM-002: Document Download**
- Users shall download generated documents
- Input: Document UUID
- Processing: Verify ownership, generate presigned URL
- Output: Temporary download URL (valid 1 hour)
- Priority: High

#### FR-API: API Management Module

**FR-API-001: Generate API Key**
- API partners shall generate API keys
- Input: Key name, rate limits (optional)
- Processing: Generate random key, hash, store
- Output: API key (shown once), key_prefix
- Priority: Medium

**FR-API-002: API Key Authentication**
- System shall authenticate API requests via X-API-Key header
- Input: API key in header
- Processing: Hash key, verify in database
- Output: User context for request
- Priority: High

**FR-API-003: Rate Limiting**
- System shall enforce API rate limits
- Limits: Per-minute and per-day based on key
- Processing: Track requests in Redis
- Output: HTTP 429 if limit exceeded
- Priority: High

#### FR-BT: Billing & Token Module

**FR-BT-001: Token Balance Management**
- System shall track user token balances
- Processing: Initialize on registration, update on usage/purchase
- Output: Current token balance
- Priority: High

**FR-BT-002: Token Purchase**
- Users shall purchase token packages via Razorpay
- Input: Package amount (e.g., 10K tokens for ₹99)
- Processing: Create Razorpay order, verify payment, credit tokens
- Output: Updated token balance
- Priority: High

**FR-BT-003: Usage Logging**
- System shall log all token usage
- Input: Endpoint, tokens_used, model, response_time
- Processing: Insert to usage_logs table
- Output: Usage record
- Priority: High

**FR-BT-004: Cost Calculation**
- System shall calculate costs in INR paise
- Model Pricing: Haiku ($0.25/1M), Sonnet ($3/1M)
- Processing: Convert USD to INR, convert to paise
- Output: Cost in paise
- Priority: High

#### FR-CM: College Management Module

**FR-CM-001: College Registration**
- Admins shall register colleges
- Input: Name, address, contact details, admin_user_id
- Processing: Create college record
- Output: College created
- Priority: Medium

**FR-CM-002: Batch Management**
- Admins shall create academic batches
- Input: College_id, name, academic_year, dates
- Processing: Create batch record
- Output: Batch created
- Priority: Medium

**FR-CM-003: Project Monitoring**
- Faculty shall view student projects
- Input: College_id/batch_id
- Processing: Fetch projects for students
- Output: Project list with progress
- Priority: Medium

### 3.2 Non-Functional Requirements

#### NFR-P: Performance Requirements

**NFR-P-001: API Response Time**
- Non-AI endpoints shall respond within 200ms (95th percentile)
- Priority: High

**NFR-P-002: AI Generation Time**
- Code-only mode: < 5 minutes
- Full student project: < 15 minutes
- Priority: High

**NFR-P-003: Concurrent Users**
- Support minimum 10,000 concurrent users
- Priority: Medium

**NFR-P-004: Database Query Performance**
- Database queries < 50ms (95th percentile)
- Priority: High

#### NFR-S: Scalability Requirements

**NFR-S-001: Horizontal Scalability**
- System shall scale horizontally by adding instances
- Implementation: Stateless backend, shared Redis/PostgreSQL
- Priority: High

**NFR-S-002: Database Scalability**
- Support 1 million users, 10 million projects
- Priority: Medium

#### NFR-SEC: Security Requirements

**NFR-SEC-001: Authentication**
- All API endpoints require JWT authentication (except public)
- Priority: High

**NFR-SEC-002: Password Security**
- Passwords hashed with bcrypt (cost factor 12)
- Priority: High

**NFR-SEC-003: Data Encryption**
- Data in transit: TLS 1.3
- Data at rest: AES-256
- Priority: High

**NFR-SEC-004: OWASP Compliance**
- Protection against OWASP Top 10 vulnerabilities
- Priority: High

**NFR-SEC-005: Rate Limiting**
- API endpoints: 100 requests/minute per IP
- Login: 5 attempts per 15 minutes
- Priority: High

#### NFR-R: Reliability Requirements

**NFR-R-001: System Availability**
- 99.9% uptime (< 8.76 hours downtime/year)
- Priority: High

**NFR-R-002: Data Backup**
- Daily PostgreSQL backups, 30-day retention
- Priority: High

**NFR-R-003: Error Recovery**
- Failed agent tasks retry up to 3 times
- Priority: Medium

#### NFR-U: Usability Requirements

**NFR-U-001: Browser Compatibility**
- Support Chrome 100+, Firefox 100+, Safari 15+, Edge 100+
- Priority: High

**NFR-U-002: Responsive Design**
- Functional on desktop, tablet, mobile (375px to 1920px)
- Priority: High

**NFR-U-003: Accessibility**
- WCAG 2.1 Level AA compliance
- Priority: Medium

#### NFR-M: Maintainability Requirements

**NFR-M-001: Code Quality**
- Python: PEP 8 compliance, type hints
- TypeScript: ESLint rules, strict mode
- Priority: Medium

**NFR-M-002: Documentation**
- API documentation (OpenAPI/Swagger)
- Inline code comments for complex logic
- Priority: Medium

**NFR-M-003: Logging**
- Structured logging (JSON) for all requests and errors
- Priority: High

### 3.3 External Interface Requirements

#### User Interface Requirements

**UI-001: Landing Page**
- Components: Hero section, features, pricing, testimonials
- Navigation: Login, Register, Pricing, Documentation

**UI-002: Authentication Pages**
- Login: Email/password, Google OAuth, "Forgot Password"
- Register: Email, username, full name, password, role

**UI-003: Dashboard**
- Components: Project list, token balance, quick actions
- Filters: Status, mode, date range

**UI-004: Project Creation Form**
- Student Mode: Title, domain, tech stack, requirements
- Developer Mode: Prompt, framework, deployment target
- Founder Mode: Business idea, industry, target market

**UI-005: Bolt Interface**
- Layout: Split view (chat + Monaco editor)
- Components: File tree, editor tabs, streaming chat

#### Software Interfaces

**SI-001: Anthropic Claude API**
- Protocol: HTTPS REST API
- Authentication: API key in x-api-key header
- Endpoints: POST /v1/messages
- Data Format: JSON

**SI-002: PostgreSQL Database**
- Version: 15.x
- Protocol: TCP/IP (port 5432)
- Connection: Async SQLAlchemy pool

**SI-003: Redis**
- Version: 7.x
- Protocol: Redis Protocol (RESP)
- Usage: Caching, session storage, Celery broker

**SI-004: AWS S3 / MinIO**
- Protocol: S3 API (HTTPS)
- Authentication: AWS Signature Version 4
- Operations: PutObject, GetObject, DeleteObject

**SI-005: Google OAuth 2.0**
- Protocol: OAuth 2.0
- Scopes: email, profile

**SI-006: Razorpay Payment Gateway**
- Version: API v1
- Protocol: HTTPS REST
- Endpoints: Create order, capture payment, verify

#### Communication Interfaces

**CI-001: RESTful API**
- Protocol: HTTP/1.1, HTTPS
- Base URL: https://api.bharatbuild.ai/api/v1
- Content-Type: application/json
- Authentication: Bearer token (JWT) or X-API-Key

**CI-002: Server-Sent Events (SSE)**
- Protocol: HTTP with text/event-stream
- Endpoint: /api/v1/automation/execute/stream
- Event Format: JSON events
- Heartbeat: Every 30 seconds

### 3.4 System Features

#### Multi-Agent Orchestration System
Core feature enabling coordinated execution of 16 specialized AI agents with sequential execution, context passing, parallel execution capabilities, error handling, and real-time streaming.

#### Real-Time Code Generation (Bolt Mode)
Interactive code generation interface with Monaco editor, SSE streaming, file tree visualization, and downloadable project packages.

#### Academic Document Generation
Automated generation of IEEE-compliant SRS, UML diagrams, full-stack code, project reports, PowerPoint presentations, and viva Q&A materials.

#### Token Economy System
Usage-based billing with transparent cost tracking, token balance management, Razorpay integration, and detailed usage analytics.

---

**END OF SOFTWARE REQUIREMENTS SPECIFICATION**
