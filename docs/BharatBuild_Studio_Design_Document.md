# BharatBuild Studio - Product Design Document

> **Version:** 1.0
> **Date:** January 2026
> **Status:** Design Phase
> **Confidential:** Internal Use Only

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Vision](#2-product-vision)
3. [User Personas](#3-user-personas)
4. [Product Modes](#4-product-modes)
5. [Feature Specifications](#5-feature-specifications)
6. [UI/UX Design](#6-uiux-design)
7. [User Flows](#7-user-flows)
8. [Technical Architecture](#8-technical-architecture)
9. [Database Design](#9-database-design)
10. [AI Integration](#10-ai-integration)
11. [Security Architecture](#11-security-architecture)
12. [Plagiarism Detection System](#12-plagiarism-detection-system)
13. [Deployment Options](#13-deployment-options)
14. [Revenue Model](#14-revenue-model)
15. [Implementation Roadmap](#15-implementation-roadmap)
16. [Competitive Analysis](#16-competitive-analysis)
17. [Appendix](#17-appendix)

---

## 1. Executive Summary

### 1.1 Problem Statement

Indian engineering colleges face critical challenges:

- **Students copy code** without understanding, failing in viva/interviews
- **Faculty can't track** real learning progress or detect plagiarism effectively
- **No integrated solution** combines coding, learning, and assessment
- **Accreditation pressure** (NAAC/NBA) requires outcome-based education proof

### 1.2 Solution

**BharatBuild Studio** is an integrated development environment (IDE) that:

- Teaches students while they build projects
- Tracks every interaction for genuine learning verification
- Provides faculty with complete visibility and control
- Generates accreditation-ready reports

### 1.3 Key Value Proposition

```
"The only IDE where students learn while they build - with proof"
```

### 1.4 Target Market

| Segment | Count in India | Priority |
|---------|---------------|----------|
| Private Engineering Colleges | 3,500+ | High |
| Deemed Universities | 130+ | High |
| State Technical Universities | 50+ | Medium |
| Government Engineering Colleges | 500+ | Low |

### 1.5 Revenue Potential

| Year | Colleges | Revenue |
|------|----------|---------|
| Year 1 | 20 | ₹80 lakhs |
| Year 2 | 80 | ₹4 Cr |
| Year 3 | 200 | ₹12-15 Cr |

---

## 2. Product Vision

### 2.1 Vision Statement

```
Transform engineering education by ensuring every student
who submits a project truly understands what they built.
```

### 2.2 Mission

Provide colleges with a complete platform that:
1. **Generates** industry-standard projects
2. **Teaches** concepts alongside code
3. **Tracks** genuine learning progress
4. **Verifies** student understanding
5. **Reports** outcomes for accreditation

### 2.3 Core Principles

| Principle | Description |
|-----------|-------------|
| **Learning First** | Every feature should enhance learning, not replace it |
| **Transparency** | Faculty sees everything, students know they're being tracked |
| **Fairness** | Same opportunities for all students, difficulty normalized |
| **Privacy** | Student data protected, only aggregates shared externally |
| **Accessibility** | Works on low-end computers, slow internet |

---

## 3. User Personas

### 3.1 Primary Persona: Student

```
┌─────────────────────────────────────────────────────────────┐
│ PERSONA: RAHUL KUMAR                                        │
│ Role: 3rd Year B.Tech CSE Student                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ DEMOGRAPHICS                                                │
│ • Age: 20                                                   │
│ • Location: Tier-2 city, Andhra Pradesh                    │
│ • Device: Budget laptop, 4GB RAM                           │
│ • Internet: Inconsistent (5-20 Mbps)                       │
│                                                             │
│ GOALS                                                       │
│ • Complete mini project for semester                        │
│ • Actually understand what he's building                    │
│ • Pass viva examination with confidence                     │
│ • Get good grades and placement                            │
│                                                             │
│ PAIN POINTS                                                 │
│ • Copies code from internet, doesn't understand            │
│ • Struggles with environment setup                          │
│ • No guidance on project structure                          │
│ • Fear of viva questions                                    │
│ • Limited access to good learning resources                │
│                                                             │
│ BEHAVIORS                                                   │
│ • Searches YouTube for tutorials                            │
│ • Uses ChatGPT for quick answers                           │
│ • Studies night before exams                                │
│ • Shares code with friends                                  │
│                                                             │
│ SUCCESS METRICS                                             │
│ • Can explain any part of their project                    │
│ • Passes viva without memorizing                            │
│ • Gets internship/placement                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Secondary Persona: Faculty

```
┌─────────────────────────────────────────────────────────────┐
│ PERSONA: PROF. SHARMA                                       │
│ Role: Assistant Professor, 15 years experience             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ DEMOGRAPHICS                                                │
│ • Age: 42                                                   │
│ • Teaching: Software Engineering Lab                        │
│ • Students: 120 per semester                               │
│ • Tech Comfort: Moderate                                    │
│                                                             │
│ GOALS                                                       │
│ • Ensure students actually learn programming               │
│ • Identify and help struggling students                    │
│ • Conduct fair assessments                                  │
│ • Meet accreditation requirements                          │
│                                                             │
│ PAIN POINTS                                                 │
│ • Can't verify if student wrote the code                   │
│ • Manual plagiarism checking is tedious                    │
│ • No visibility into student progress                      │
│ • Lab exam proctoring is difficult                         │
│ • 120 students, limited time per student                   │
│                                                             │
│ BEHAVIORS                                                   │
│ • Asks viva questions to verify understanding              │
│ • Manually compares code submissions                        │
│ • Maintains Excel sheets for tracking                       │
│ • Relies on gut feeling for grades                         │
│                                                             │
│ SUCCESS METRICS                                             │
│ • All students demonstrate understanding                   │
│ • Zero plagiarism incidents                                │
│ • NAAC/NBA compliance achieved                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Buyer Persona: HOD/Principal

```
┌─────────────────────────────────────────────────────────────┐
│ PERSONA: DR. REDDY                                          │
│ Role: Head of Department, Computer Science                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ GOALS                                                       │
│ • Improve department outcomes and rankings                 │
│ • NAAC/NBA accreditation compliance                        │
│ • Better placement statistics                              │
│ • Justify technology investments to management             │
│                                                             │
│ PAIN POINTS                                                 │
│ • No data on actual student skill levels                   │
│ • Project quality is inconsistent                          │
│ • Hard to prove learning outcomes to NAAC                  │
│ • Multiple disconnected tools                              │
│ • Faculty resistance to new technology                     │
│                                                             │
│ BUYING CRITERIA                                             │
│ • Clear ROI demonstration                                   │
│ • Accreditation report generation                          │
│ • Easy adoption (minimal training)                          │
│ • Reliable vendor support                                   │
│ • Competitive pricing                                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Product Modes

### 4.1 Mode Overview

BharatBuild Studio operates in three distinct modes:

```
┌─────────────────────────────────────────────────────────────┐
│                    THREE OPERATING MODES                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   LEARN     │  │   BUILD     │  │    EXAM     │         │
│  │    MODE     │  │    MODE     │  │    MODE     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│        │                │                │                  │
│        ▼                ▼                ▼                  │
│  Guided learning   Free coding     Locked down             │
│  Step-by-step      Full AI help    No external help        │
│  Must pass quiz    All features    Proctored               │
│  Progress gated    Track activity  Timed                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Learn Mode

**Purpose:** Ensure students understand concepts before writing code

**Features:**
- Concept explanation before each coding stage
- Embedded video tutorials (2-3 minutes each)
- Quiz gates (must pass to proceed)
- Progressive hints (not direct solutions)
- Learning checkpoints in code

**Restrictions:**
- Cannot skip to next stage without quiz
- Solution only available after 3 hint levels
- All interactions tracked

### 4.3 Build Mode

**Purpose:** Allow students to code freely with AI assistance

**Features:**
- Full code editor with IntelliSense
- AI chat assistant (BharatBuild integrated)
- Unlimited hints and help
- Run and debug capabilities
- Git integration

**Tracking:**
- Time spent per file
- AI interactions logged
- Copy-paste detected
- Code changes versioned

### 4.4 Exam Mode

**Purpose:** Conduct secure, proctored coding assessments

**Features:**
- Full-screen lockdown
- Webcam proctoring (optional)
- Question-by-question navigation
- Auto-submit on timeout
- Test case validation

**Restrictions:**
- No copy-paste from external sources
- No tab switching
- No AI assistance
- No external browser access
- Flagged on violations

---

## 5. Feature Specifications

### 5.1 Student Features

#### 5.1.1 Code Editor

| Feature | Description | Priority |
|---------|-------------|----------|
| Syntax Highlighting | All major languages | P0 |
| IntelliSense | Auto-completion | P0 |
| Error Detection | Real-time linting | P0 |
| Multi-file Support | Tabs, file tree | P0 |
| Terminal | Integrated terminal | P0 |
| Debugger | Breakpoints, step-through | P1 |
| Git Integration | Commit, push, pull | P1 |
| Themes | Dark/Light mode | P2 |

#### 5.1.2 Learning Panel

| Feature | Description | Priority |
|---------|-------------|----------|
| Concept Cards | Brief explanations | P0 |
| Video Tutorials | Embedded 2-3 min videos | P1 |
| Documentation Links | External resources | P1 |
| Quiz System | MCQ before proceeding | P0 |
| Progress Tracker | Visual stage progress | P0 |

#### 5.1.3 AI Assistant

| Feature | Description | Priority |
|---------|-------------|----------|
| Context-Aware Chat | Understands current file | P0 |
| Hint System | Progressive hints | P0 |
| Code Explanation | Explain selected code | P0 |
| Error Help | Explain compilation errors | P0 |
| Best Practices | Suggest improvements | P1 |

#### 5.1.4 Submission

| Feature | Description | Priority |
|---------|-------------|----------|
| Stage Submission | Submit per stage | P0 |
| Final Submission | Complete project submit | P0 |
| Self-Review | Checklist before submit | P1 |
| Submission History | View past submissions | P1 |

### 5.2 Faculty Features

#### 5.2.1 Dashboard

| Feature | Description | Priority |
|---------|-------------|----------|
| Class Overview | All students at glance | P0 |
| Progress Tracking | Per-student progress | P0 |
| Alerts | Stuck students, plagiarism | P0 |
| Filters | By status, progress, date | P1 |
| Export | CSV, PDF reports | P1 |

#### 5.2.2 Student Deep-Dive

| Feature | Description | Priority |
|---------|-------------|----------|
| Activity Timeline | All actions visualized | P0 |
| Code Viewer | See student's code | P0 |
| Behavioral Analysis | Patterns, anomalies | P1 |
| Communication | Message student | P1 |
| Grading | Assign grades | P0 |

#### 5.2.3 Plagiarism Tools

| Feature | Description | Priority |
|---------|-------------|----------|
| Similarity Report | Cross-student comparison | P0 |
| Code Comparison | Side-by-side view | P0 |
| External Source Check | GitHub, StackOverflow | P1 |
| AI Detection | Detect AI-generated code | P1 |
| Bulk Check | Check all submissions | P0 |

#### 5.2.4 Viva Support

| Feature | Description | Priority |
|---------|-------------|----------|
| Question Generation | AI-generated from code | P0 |
| Question Bank | Save custom questions | P1 |
| AI Viva Mode | Simulated viva | P2 |
| Viva Report | Record answers/scores | P1 |

#### 5.2.5 Exam Management

| Feature | Description | Priority |
|---------|-------------|----------|
| Create Exam | Questions, duration, rules | P0 |
| Schedule | Set date/time | P0 |
| Monitor Live | See all students live | P0 |
| Auto-Grade | Test case validation | P0 |
| Manual Override | Adjust grades | P0 |

### 5.3 Admin Features

#### 5.3.1 College Management

| Feature | Description | Priority |
|---------|-------------|----------|
| Add Users | Bulk upload students/faculty | P0 |
| Create Classes | Batch, section management | P0 |
| Assign Projects | Project templates to class | P0 |
| License Management | View usage, limits | P0 |

#### 5.3.2 Reports

| Feature | Description | Priority |
|---------|-------------|----------|
| Usage Reports | Active users, projects | P0 |
| Outcome Reports | Skills, competencies | P1 |
| Accreditation Export | NAAC/NBA format | P1 |
| Custom Reports | Build own reports | P2 |

---

## 6. UI/UX Design

### 6.1 Design Principles

1. **Familiar** - Similar to VS Code, low learning curve
2. **Clean** - Minimal distractions, focus on code
3. **Informative** - Progress always visible
4. **Accessible** - Works on low-end devices
5. **Responsive** - Adapts to screen sizes

### 6.2 Color Scheme

```
PRIMARY COLORS:
├── Brand Blue: #2563EB
├── Success Green: #10B981
├── Warning Yellow: #F59E0B
├── Error Red: #EF4444
└── Purple Accent: #8B5CF6

DARK THEME:
├── Background: #1E1E1E
├── Surface: #252526
├── Border: #3C3C3C
├── Text Primary: #CCCCCC
└── Text Secondary: #808080

LIGHT THEME:
├── Background: #FFFFFF
├── Surface: #F3F4F6
├── Border: #E5E7EB
├── Text Primary: #1F2937
└── Text Secondary: #6B7280
```

### 6.3 Main Interface Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ HEADER: Logo | Project Name | User | Settings | Notifications               │
├────────┬─────────────────────────────────────────────────────┬───────────────┤
│        │                                                     │               │
│  LEFT  │                    CENTER                           │    RIGHT      │
│ PANEL  │                   PANEL                             │    PANEL      │
│        │                                                     │               │
│ Files  │              Code Editor                            │ AI Assistant  │
│ +      │              (Monaco)                               │ +             │
│Progress│                                                     │ Learning      │
│        │                                                     │               │
│        ├─────────────────────────────────────────────────────┤               │
│        │           BOTTOM PANEL                              │               │
│        │    Terminal | Problems | Output | Debug             │               │
└────────┴─────────────────────────────────────────────────────┴───────────────┘
```

### 6.4 Panel Specifications

#### 6.4.1 Left Panel (250px default, resizable)

```
┌─────────────────────┐
│ FILES               │  ← Section header
├─────────────────────┤
│ 🔍 Search files...  │  ← Quick search
│                     │
│ 📁 src              │  ← Folder (expandable)
│  ├─📁 auth          │
│  │  ├─📄 login.py   │  ← File (clickable)
│  │  └─📄 register.py│
│  └─📁 models        │
│ 📁 tests            │
│ 📄 README.md        │
│                     │
├─────────────────────┤
│ LEARNING PROGRESS   │  ← Section header
├─────────────────────┤
│ Stage 3 of 7        │
│ ████████░░░░░ 45%   │  ← Progress bar
│                     │
│ ✅ 1. Project Setup │  ← Completed
│ ✅ 2. Database      │  ← Completed
│ 🔄 3. Auth ◄────────│  ← Current (highlighted)
│ ⬜ 4. Models        │  ← Pending
│ ⬜ 5. Routes        │
│                     │
├─────────────────────┤
│ 📊 SESSION STATS    │
├─────────────────────┤
│ ⏱️ Time: 4h 23m     │
│ 📝 Lines: 347       │
│ 💡 Hints: 5/15      │
│                     │
├─────────────────────┤
│ ┌─────────────────┐ │
│ │   📤 SUBMIT     │ │  ← Primary action
│ └─────────────────┘ │
└─────────────────────┘
```

#### 6.4.2 Center Panel (Flexible width)

```
┌─────────────────────────────────────────────────────────────┐
│ login.py    register.py    models.py    ×  +                │  ← Tabs
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1│ from fastapi import APIRouter                           │
│  2│ from app.models import User                             │
│  3│                                                         │
│  4│ router = APIRouter()                                    │
│  5│                                                         │
│  6│ @router.post("/login")                      ┌─────────┐ │
│  7│ async def login(email, password):           │💡 Hint  │ │ ← Inline hint
│  8│     # Implement authentication              │available│ │
│  9│     |                                       └─────────┘ │
│ 10│                                                         │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Ln 9, Col 5 | Python | UTF-8 | Spaces: 4                   │  ← Status bar
└─────────────────────────────────────────────────────────────┘
```

#### 6.4.3 Right Panel (300px default, collapsible)

```
┌─────────────────────────┐
│ 🤖 AI ASSISTANT         │
├─────────────────────────┤
│ ┌─────────┬───────────┐ │
│ │ 🎓LEARN │ 💬 CHAT   │ │  ← Tab switch
│ └─────────┴───────────┘ │
│                         │
│ ─── CURRENT TOPIC ───   │
│                         │
│ ┌─────────────────────┐ │
│ │ Password Hashing    │ │
│ │                     │ │
│ │ Bcrypt is a secure  │ │
│ │ password hashing    │ │
│ │ algorithm that...   │ │
│ │                     │ │
│ │ [▶️ Watch Video]     │ │
│ │ [📄 Documentation]  │ │
│ └─────────────────────┘ │
│                         │
│ ─── QUIZ ───            │
│                         │
│ ┌─────────────────────┐ │
│ │ Q: Why not use MD5  │ │
│ │ for passwords?      │ │
│ │                     │ │
│ │ ○ A) Too slow       │ │
│ │ ● B) Not secure     │ │
│ │ ○ C) Too complex    │ │
│ │                     │ │
│ │ [Check Answer]      │ │
│ └─────────────────────┘ │
│                         │
├─────────────────────────┤
│ 💬 Ask a question...    │
│ ┌─────────────────────┐ │
│ │                     │ │
│ └─────────────────────┘ │
│ [Send]                  │
└─────────────────────────┘
```

#### 6.4.4 Bottom Panel (200px default, resizable)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TERMINAL    PROBLEMS (2)    OUTPUT    DEBUG                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ (venv) $ python main.py                                                     │
│ INFO:     Started server process [12345]                                    │
│ INFO:     Uvicorn running on http://127.0.0.1:8000                         │
│                                                                             │
│ $ |                                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.5 Exam Mode Interface

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 🔒 EXAM MODE    CS-301 Lab Exam    ⏱️ 1:23:45    📹 Recording               │
├────────────┬─────────────────────────────────────────────────────────────────┤
│            │                                                                 │
│ QUESTIONS  │  Question 2 of 5                              Marks: 10        │
│            │  ────────────────────────────────────────────────────────────   │
│ ✅ Q1      │                                                                 │
│ 🔄 Q2 ◄    │  Write a function to implement binary search.                   │
│ ⬜ Q3      │                                                                 │
│ ⬜ Q4      │  Requirements:                                                  │
│ ⬜ Q5      │  • Input: Sorted array and target                               │
│            │  • Output: Index or -1                                          │
│────────────│  • Iterative approach only                                      │
│            │                                                                 │
│ RULES:     │  ────────────────────────────────────────────────────────────   │
│ ❌ No copy │                                                                 │
│ ❌ No paste│  ┌───────────────────────────────────────────────────────────┐  │
│ ❌ No AI   │  │ def binary_search(arr, target):                           │  │
│            │  │     left, right = 0, len(arr) - 1                         │  │
│────────────│  │     |                                                      │  │
│ 📹 Webcam  │  └───────────────────────────────────────────────────────────┘  │
│ ┌────────┐ │                                                                 │
│ │  👤    │ │  [▶️ Run Code]    [✅ Submit]    [➡️ Next]                       │
│ └────────┘ │                                                                 │
│            │  OUTPUT:                                                        │
│ Warnings:0 │  Test 1: PASSED ✅    Test 2: FAILED ❌                         │
└────────────┴─────────────────────────────────────────────────────────────────┘
```

### 6.6 Faculty Dashboard

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📊 Faculty Dashboard         Prof. Sharma         CS-301 Software Engg      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │     45      │ │     67%     │ │     12      │ │      3      │            │
│  │  Students   │ │ Avg Progress│ │ Submitted   │ │ Need Help   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                                              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
│                                                                              │
│  STUDENT PROGRESS                                          [🔍] [Export]    │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ Student          │ Project      │ Progress │ Time   │ Hints │ Status   │ │
│  ├────────────────────────────────────────────────────────────────────────┤ │
│  │ 🔴 Rahul Kumar   │ E-Commerce   │ ██░░░ 35%│ 2h 15m │ 8/10  │ Stuck    │ │
│  │ 🟡 Priya Singh   │ E-Commerce   │ ████░ 78%│ 8h 30m │ 3/10  │ On Track │ │
│  │ 🟢 Amit Patel    │ E-Commerce   │ █████ 95%│ 12h 5m │ 2/10  │ Review   │ │
│  │ 🔴 Sneha Reddy   │ E-Commerce   │ █░░░░ 15%│ 45m    │ 0/10  │ Inactive │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  🚨 PLAGIARISM ALERTS                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ ⚠️ Rahul Kumar ↔ Vikram Shah: 87% similarity in auth/login.py          │ │
│  │ [View Comparison] [Dismiss] [Mark Plagiarism]                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. User Flows

### 7.1 Student: Project Completion Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     STUDENT PROJECT FLOW                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  START                                                                      │
│    │                                                                        │
│    ▼                                                                        │
│  ┌─────────────┐                                                            │
│  │   LOGIN     │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐     ┌─────────────┐                                       │
│  │   SELECT    │────►│   CREATE    │  (if new)                              │
│  │   PROJECT   │     │   PROJECT   │                                        │
│  └──────┬──────┘     └─────────────┘                                       │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │                    FOR EACH STAGE                        │               │
│  │  ┌─────────────┐                                        │               │
│  │  │ READ CONCEPT│                                        │               │
│  │  └──────┬──────┘                                        │               │
│  │         │                                               │               │
│  │         ▼                                               │               │
│  │  ┌─────────────┐     NO      ┌─────────────┐           │               │
│  │  │ TAKE QUIZ   │────────────►│ REVIEW &    │           │               │
│  │  └──────┬──────┘             │ RETRY       │           │               │
│  │         │ YES                └─────────────┘           │               │
│  │         ▼                                               │               │
│  │  ┌─────────────┐                                        │               │
│  │  │ WRITE CODE  │◄──────────────────────────┐           │               │
│  │  └──────┬──────┘                           │           │               │
│  │         │                                  │           │               │
│  │         ▼                                  │           │               │
│  │  ┌─────────────┐     YES     ┌─────────────┐           │               │
│  │  │   STUCK?    │────────────►│ GET HINT    │───────────┘               │
│  │  └──────┬──────┘             └─────────────┘                           │
│  │         │ NO                                                            │
│  │         ▼                                                               │
│  │  ┌─────────────┐                                                        │
│  │  │   RUN &     │                                                        │
│  │  │   DEBUG     │                                                        │
│  │  └──────┬──────┘                                                        │
│  │         │                                                               │
│  │         ▼                                                               │
│  │  ┌─────────────┐     NO      ┌─────────────┐                           │
│  │  │   TESTS     │────────────►│ FIX ERRORS  │───────────┐               │
│  │  │   PASS?     │             └─────────────┘           │               │
│  │  └──────┬──────┘                                       │               │
│  │         │ YES                                          │               │
│  │         ▼                                              │               │
│  │  ┌─────────────┐                                       │               │
│  │  │   SUBMIT    │                                       │               │
│  │  │   STAGE     │                                       │               │
│  │  └──────┬──────┘                                       │               │
│  │         │                                               │               │
│  └─────────┼───────────────────────────────────────────────┘               │
│            │                                                                │
│            ▼                                                                │
│  ┌─────────────┐                                                            │
│  │   FINAL     │                                                            │
│  │  SUBMISSION │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│       END                                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Faculty: Monitoring Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FACULTY MONITORING FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐                                                            │
│  │   LOGIN     │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────┐               │
│  │                    DASHBOARD                             │               │
│  │                                                         │               │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐          │               │
│  │   │ Overview  │  │  Alerts   │  │  Actions  │          │               │
│  │   └─────┬─────┘  └─────┬─────┘  └─────┬─────┘          │               │
│  └─────────┼──────────────┼──────────────┼─────────────────┘               │
│            │              │              │                                  │
│            ▼              ▼              ▼                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │ VIEW CLASS  │  │ PLAGIARISM  │  │ CREATE EXAM │                         │
│  │ PROGRESS    │  │ REVIEW      │  │             │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                │                │                                 │
│         ▼                ▼                ▼                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │  STUDENT    │  │  COMPARE    │  │  MONITOR    │                         │
│  │  DETAIL     │  │  CODE       │  │  LIVE       │                         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                         │
│         │                │                │                                 │
│    ┌────┴────┐          │                │                                 │
│    ▼         ▼          ▼                ▼                                 │
│ ┌──────┐ ┌──────┐  ┌─────────┐    ┌─────────────┐                          │
│ │ VIEW │ │ VIVA │  │ TAKE    │    │ AUTO-GRADE  │                          │
│ │ CODE │ │ Q's  │  │ ACTION  │    │             │                          │
│ └──────┘ └──────┘  └─────────┘    └─────────────┘                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Exam Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EXAM FLOW                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FACULTY                              STUDENT                               │
│  ────────                              ───────                               │
│                                                                             │
│  ┌─────────────┐                                                            │
│  │ Create Exam │                                                            │
│  │ • Questions │                                                            │
│  │ • Duration  │                                                            │
│  │ • Rules     │                                                            │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────┐                                                            │
│  │ Schedule &  │                      ┌─────────────┐                       │
│  │ Share Link  │─────────────────────►│ Open Link   │                       │
│  └──────┬──────┘                      └──────┬──────┘                       │
│         │                                    │                              │
│         │                                    ▼                              │
│         │                             ┌─────────────┐                       │
│         │                             │ System Check│                       │
│         │                             │ • Webcam    │                       │
│         │                             │ • Browser   │                       │
│         │                             └──────┬──────┘                       │
│         │                                    │                              │
│         │                                    ▼                              │
│         │                             ┌─────────────┐                       │
│         │                             │  LOCKDOWN   │                       │
│         │                             │  ACTIVATED  │                       │
│         │                             └──────┬──────┘                       │
│         │                                    │                              │
│         ▼                                    ▼                              │
│  ┌─────────────┐                      ┌─────────────┐                       │
│  │  MONITOR    │◄────────────────────►│   SOLVE     │                       │
│  │  • Progress │    Real-time         │  QUESTIONS  │                       │
│  │  • Flags    │                      └──────┬──────┘                       │
│  │  • Webcam   │                             │                              │
│  └──────┬──────┘                             │ Timeout                      │
│         │                                    ▼                              │
│         │                             ┌─────────────┐                       │
│         │                             │ AUTO-SUBMIT │                       │
│         │                             └──────┬──────┘                       │
│         │                                    │                              │
│         ▼                                    ▼                              │
│  ┌───────────────────────────────────────────────────┐                      │
│  │                  AUTO-GRADING                     │                      │
│  │  • Run test cases    • Check plagiarism           │                      │
│  └───────────────────────────────────────────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Technical Architecture

### 8.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SYSTEM ARCHITECTURE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                            ┌─────────────┐                                  │
│                            │    CDN      │                                  │
│                            │ CloudFlare  │                                  │
│                            └──────┬──────┘                                  │
│                                   │                                         │
│         ┌─────────────────────────┼─────────────────────────┐              │
│         │                         │                         │              │
│         ▼                         ▼                         ▼              │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐         │
│  │ Desktop App │          │   Web IDE   │          │  Dashboard  │         │
│  │ (Electron)  │          │  (React)    │          │  (React)    │         │
│  └──────┬──────┘          └──────┬──────┘          └──────┬──────┘         │
│         │                        │                        │                │
│         └────────────────────────┼────────────────────────┘                │
│                                  │                                          │
│                                  ▼                                          │
│                     ┌────────────────────────┐                              │
│                     │     API GATEWAY        │                              │
│                     │     (Kong/AWS)         │                              │
│                     └───────────┬────────────┘                              │
│                                 │                                           │
│         ┌───────────────────────┼───────────────────────┐                  │
│         │                       │                       │                  │
│         ▼                       ▼                       ▼                  │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐          │
│  │    Auth     │         │   Project   │         │  Analytics  │          │
│  │   Service   │         │   Service   │         │   Service   │          │
│  └─────────────┘         └──────┬──────┘         └─────────────┘          │
│                                 │                                          │
│         ┌───────────────────────┼───────────────────────┐                  │
│         │                       │                       │                  │
│         ▼                       ▼                       ▼                  │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐          │
│  │     AI      │         │  Plagiarism │         │  Code Exec  │          │
│  │   Service   │         │   Service   │         │   Service   │          │
│  │ (BharatBuild│         └─────────────┘         └──────┬──────┘          │
│  │  existing)  │                                        │                  │
│  └─────────────┘                                        ▼                  │
│                                                  ┌─────────────┐           │
│                                                  │   Docker    │           │
│                                                  │ Containers  │           │
│                                                  └─────────────┘           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                   │   │
│  ├─────────────┬─────────────┬─────────────┬─────────────┬─────────────┤   │
│  │ PostgreSQL  │   Redis     │    S3       │ Elasticsearch│ ClickHouse │   │
│  │  (main DB)  │  (cache)    │  (files)    │   (search)   │ (analytics)│   │
│  └─────────────┴─────────────┴─────────────┴─────────────┴─────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Component Details

#### 8.2.1 Frontend Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Desktop App | Electron + React | VS Code fork for desktop |
| Web IDE | React + Monaco | Browser-based editor |
| Faculty Dashboard | React + TailwindCSS | Monitoring interface |
| Mobile App (future) | React Native | Progress viewing |

#### 8.2.2 Backend Services

| Service | Technology | Purpose |
|---------|------------|---------|
| API Gateway | Kong/AWS API Gateway | Rate limiting, routing |
| Auth Service | FastAPI + JWT | Authentication, SSO |
| Project Service | FastAPI | Project CRUD, files |
| AI Service | Existing BharatBuild | Code generation, hints |
| Plagiarism Service | FastAPI + Python | Similarity detection |
| Analytics Service | FastAPI + ClickHouse | Usage tracking |
| Code Execution | Docker + Kubernetes | Sandboxed execution |

#### 8.2.3 Data Stores

| Store | Technology | Purpose |
|-------|------------|---------|
| Primary Database | PostgreSQL | Users, projects, submissions |
| Cache | Redis | Sessions, frequently accessed |
| File Storage | S3/MinIO | Code files, documents |
| Search | Elasticsearch | Code search, plagiarism |
| Analytics | ClickHouse | Activity events, reports |
| Message Queue | RabbitMQ/SQS | Async tasks |

### 8.3 API Design

#### 8.3.1 REST Endpoints

```
AUTH:
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me

PROJECTS:
GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/:id
PUT    /api/v1/projects/:id
DELETE /api/v1/projects/:id
GET    /api/v1/projects/:id/files
PUT    /api/v1/projects/:id/files/:path
POST   /api/v1/projects/:id/submit

LEARNING:
GET    /api/v1/learning/stages/:projectId
GET    /api/v1/learning/content/:stageId
POST   /api/v1/learning/quiz/:stageId/submit
POST   /api/v1/learning/hint/:stageId

AI:
POST   /api/v1/ai/chat
POST   /api/v1/ai/explain
POST   /api/v1/ai/generate

EXECUTION:
POST   /api/v1/execute/run
POST   /api/v1/execute/test
GET    /api/v1/execute/status/:jobId

FACULTY:
GET    /api/v1/faculty/classes
GET    /api/v1/faculty/classes/:id/students
GET    /api/v1/faculty/students/:id/progress
GET    /api/v1/faculty/students/:id/activity
POST   /api/v1/faculty/plagiarism/check
GET    /api/v1/faculty/plagiarism/report/:id
POST   /api/v1/faculty/viva/generate/:studentId

EXAMS:
POST   /api/v1/exams
GET    /api/v1/exams/:id
POST   /api/v1/exams/:id/start
POST   /api/v1/exams/:id/submit
GET    /api/v1/exams/:id/results
```

#### 8.3.2 WebSocket Events

```
CONNECTION:
connect          - Client connects
disconnect       - Client disconnects
authenticate     - Send JWT token

EDITOR:
file:change      - File content changed
file:save        - File saved
cursor:move      - Cursor position changed

ACTIVITY:
activity:log     - Log user activity
activity:sync    - Sync pending activities

COLLABORATION:
collab:join      - Join collaborative session
collab:leave     - Leave session
collab:cursor    - Cursor updates
collab:edit      - Edit updates

EXAM:
exam:start       - Exam started
exam:tick        - Time remaining
exam:warning     - Violation warning
exam:submit      - Auto-submit
```

---

## 9. Database Design

### 9.1 Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐               │
│  │   COLLEGE   │       │    USER     │       │   CLASS     │               │
│  ├─────────────┤       ├─────────────┤       ├─────────────┤               │
│  │ id (PK)     │◄──┐   │ id (PK)     │   ┌──►│ id (PK)     │               │
│  │ name        │   │   │ email       │   │   │ name        │               │
│  │ code        │   │   │ password    │   │   │ college_id  │               │
│  │ license_type│   │   │ role        │   │   │ faculty_id  │               │
│  │ valid_until │   └───│ college_id  │   │   │ semester    │               │
│  │ settings    │       │ class_id    │───┘   │ year        │               │
│  └─────────────┘       │ created_at  │       │ settings    │               │
│                        └─────────────┘       └─────────────┘               │
│                              │                     │                        │
│                              │                     │                        │
│  ┌─────────────┐            │                     │     ┌─────────────┐    │
│  │  PROJECT    │◄───────────┘                     │     │ ASSIGNMENT  │    │
│  ├─────────────┤                                  │     ├─────────────┤    │
│  │ id (PK)     │                                  └────►│ id (PK)     │    │
│  │ user_id(FK) │                                        │ class_id(FK)│    │
│  │ title       │       ┌─────────────┐                  │ title       │    │
│  │ description │       │    FILE     │                  │ due_date    │    │
│  │ type        │◄─────►├─────────────┤                  │ project_type│    │
│  │ status      │       │ id (PK)     │                  │ settings    │    │
│  │ created_at  │       │ project_id  │                  └─────────────┘    │
│  │ settings    │       │ path        │                                     │
│  └─────────────┘       │ content     │                                     │
│        │               │ version     │                                     │
│        │               │ updated_at  │                                     │
│        │               └─────────────┘                                     │
│        │                                                                    │
│        ▼                                                                    │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐               │
│  │  PROGRESS   │       │  ACTIVITY   │       │ PLAGIARISM  │               │
│  ├─────────────┤       ├─────────────┤       ├─────────────┤               │
│  │ id (PK)     │       │ id (PK)     │       │ id (PK)     │               │
│  │ project_id  │       │ user_id(FK) │       │ project_id  │               │
│  │ stage       │       │ project_id  │       │ matched_with│               │
│  │ percentage  │       │ event_type  │       │ similarity  │               │
│  │ hints_used  │       │ event_data  │       │ file_path   │               │
│  │ quiz_scores │       │ timestamp   │       │ status      │               │
│  │ time_spent  │       │ metadata    │       │ reviewed_by │               │
│  └─────────────┘       └─────────────┘       └─────────────┘               │
│                                                                             │
│  ┌─────────────┐       ┌─────────────┐       ┌─────────────┐               │
│  │    EXAM     │       │EXAM_RESPONSE│       │  KEYSTROKE  │               │
│  ├─────────────┤       ├─────────────┤       ├─────────────┤               │
│  │ id (PK)     │◄──────│ id (PK)     │       │ id (PK)     │               │
│  │ class_id(FK)│       │ exam_id(FK) │       │ user_id(FK) │               │
│  │ title       │       │ user_id(FK) │       │ project_id  │               │
│  │ duration    │       │ answers     │       │ file_path   │               │
│  │ questions   │       │ score       │       │ event_type  │               │
│  │ start_time  │       │ flags       │       │ event_data  │               │
│  │ rules       │       │ submitted_at│       │ timestamp   │               │
│  └─────────────┘       └─────────────┘       └─────────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Table Definitions

#### 9.2.1 Core Tables

```sql
-- Colleges
CREATE TABLE colleges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,
    license_type VARCHAR(50) NOT NULL, -- 'starter', 'standard', 'premium', 'enterprise'
    license_valid_until TIMESTAMP,
    max_students INTEGER DEFAULT 500,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id),
    class_id UUID REFERENCES classes(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL, -- 'student', 'faculty', 'hod', 'admin'
    full_name VARCHAR(255),
    roll_number VARCHAR(50),
    profile_data JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Classes
CREATE TABLE classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    college_id UUID REFERENCES colleges(id),
    faculty_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL,
    semester VARCHAR(20),
    year INTEGER,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    assignment_id UUID REFERENCES assignments(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50), -- 'web', 'mobile', 'api', 'ml', etc.
    tech_stack VARCHAR(100),
    status VARCHAR(50) DEFAULT 'in_progress', -- 'in_progress', 'submitted', 'graded'
    current_stage INTEGER DEFAULT 1,
    total_stages INTEGER DEFAULT 7,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    graded_at TIMESTAMP
);

-- Files
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    path VARCHAR(500) NOT NULL,
    content TEXT,
    content_hash VARCHAR(64),
    language VARCHAR(50),
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, path)
);
```

#### 9.2.2 Progress & Activity Tables

```sql
-- Progress
CREATE TABLE progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    stage INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
    percentage INTEGER DEFAULT 0,
    hints_used INTEGER DEFAULT 0,
    quiz_score INTEGER,
    quiz_attempts INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    UNIQUE(project_id, stage)
);

-- Activity Log (high volume, consider partitioning)
CREATE TABLE activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    project_id UUID REFERENCES projects(id),
    session_id UUID,
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB DEFAULT '{}',
    file_path VARCHAR(500),
    timestamp TIMESTAMP DEFAULT NOW()
) PARTITION BY RANGE (timestamp);

-- Keystroke Analysis (for plagiarism detection)
CREATE TABLE keystrokes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    project_id UUID REFERENCES projects(id) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'type', 'paste', 'delete', 'undo'
    char_count INTEGER,
    content_snippet TEXT, -- first 100 chars for paste detection
    typing_speed FLOAT, -- chars per minute
    timestamp TIMESTAMP DEFAULT NOW()
);
```

#### 9.2.3 Assessment Tables

```sql
-- Assignments
CREATE TABLE assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID REFERENCES classes(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    project_type VARCHAR(50),
    tech_stack VARCHAR(100),
    due_date TIMESTAMP,
    max_hints INTEGER DEFAULT 15,
    learning_mode_required BOOLEAN DEFAULT true,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Exams
CREATE TABLE exams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    class_id UUID REFERENCES classes(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    questions JSONB NOT NULL, -- array of question objects
    duration_minutes INTEGER NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    rules JSONB DEFAULT '{}', -- lockdown settings
    proctoring_enabled BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Exam Responses
CREATE TABLE exam_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    exam_id UUID REFERENCES exams(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    answers JSONB DEFAULT '{}',
    code_submissions JSONB DEFAULT '{}',
    score INTEGER,
    max_score INTEGER,
    flags JSONB DEFAULT '[]', -- violation flags
    started_at TIMESTAMP,
    submitted_at TIMESTAMP,
    graded_at TIMESTAMP,
    graded_by UUID REFERENCES users(id),
    UNIQUE(exam_id, user_id)
);

-- Plagiarism Reports
CREATE TABLE plagiarism_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) NOT NULL,
    matched_project_id UUID REFERENCES projects(id),
    matched_source VARCHAR(500), -- external URL if applicable
    similarity_percentage FLOAT NOT NULL,
    file_path VARCHAR(500),
    matched_lines JSONB, -- line ranges that match
    detection_method VARCHAR(50), -- 'token', 'ast', 'semantic'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'confirmed', 'dismissed'
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 9.3 Indexes

```sql
-- User indexes
CREATE INDEX idx_users_college ON users(college_id);
CREATE INDEX idx_users_class ON users(class_id);
CREATE INDEX idx_users_role ON users(role);

-- Project indexes
CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_assignment ON projects(assignment_id);

-- Activity indexes (critical for performance)
CREATE INDEX idx_activities_user_time ON activities(user_id, timestamp DESC);
CREATE INDEX idx_activities_project ON activities(project_id);
CREATE INDEX idx_activities_type ON activities(event_type);

-- File indexes
CREATE INDEX idx_files_project ON files(project_id);
CREATE INDEX idx_files_hash ON files(content_hash);

-- Plagiarism indexes
CREATE INDEX idx_plagiarism_project ON plagiarism_reports(project_id);
CREATE INDEX idx_plagiarism_status ON plagiarism_reports(status);
```

---

## 10. AI Integration

### 10.1 AI Service Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI SERVICE ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌─────────────────┐                                 │
│                         │   AI Gateway    │                                 │
│                         │   (Router)      │                                 │
│                         └────────┬────────┘                                 │
│                                  │                                          │
│         ┌────────────────────────┼────────────────────────┐                │
│         │                        │                        │                │
│         ▼                        ▼                        ▼                │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐          │
│  │   Claude    │         │   Gemini    │         │    Local    │          │
│  │   Sonnet    │         │   Flash     │         │   Models    │          │
│  │   (Complex) │         │  (Simple)   │         │   (Cache)   │          │
│  └─────────────┘         └─────────────┘         └─────────────┘          │
│                                                                             │
│  ROUTING RULES:                                                             │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Architecture design → Claude Sonnet                                     │
│  • Complex code generation → Claude Sonnet                                 │
│  • Simple file generation → Gemini Flash                                   │
│  • Code completion → Local/Cached                                          │
│  • Quiz questions → Pre-written (no AI)                                    │
│  • Concept explanations → Pre-written (no AI)                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.2 AI Use Cases

| Feature | AI Model | Trigger | Caching |
|---------|----------|---------|---------|
| Project Architecture | Claude Sonnet | New project | By project type |
| File Generation | Gemini Flash | Per file | By template |
| Code Completion | Local | While typing | Recent context |
| Hint Level 1 | Pre-written | Student request | Always cached |
| Hint Level 2 | GPT-4o-mini | Student request | By concept |
| Hint Level 3 (Solution) | Cached | Student request | By stage |
| Custom Question | GPT-4o-mini | Student asks | By similarity |
| Code Explanation | GPT-4o-mini | Selection | By code hash |
| Viva Questions | Claude Sonnet | Faculty request | By project |
| Plagiarism AI Check | Claude Sonnet | On submit | None |

### 10.3 Cost Optimization Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     AI COST OPTIMIZATION                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STRATEGY 1: PRE-WRITTEN CONTENT                                            │
│  ────────────────────────────────────────────────────────────────────────   │
│  • 500 concept explanations (written once)                                  │
│  • 100 project templates (cached)                                           │
│  • 2000 quiz questions (database)                                           │
│  • 300 common hints (by stage/concept)                                      │
│  IMPACT: 60% of AI calls eliminated                                         │
│                                                                             │
│  STRATEGY 2: SMART MODEL ROUTING                                            │
│  ────────────────────────────────────────────────────────────────────────   │
│  • Complex (20%) → Claude ($$$)                                             │
│  • Medium (30%) → Gemini Flash ($)                                          │
│  • Simple (30%) → GPT-4o-mini ($)                                           │
│  • Cached (20%) → Free                                                      │
│  IMPACT: 70% cost reduction                                                 │
│                                                                             │
│  STRATEGY 3: RESPONSE CACHING                                               │
│  ────────────────────────────────────────────────────────────────────────   │
│  • Cache by: question hash, code context hash                               │
│  • 80% of student questions are similar                                     │
│  • TTL: 30 days                                                             │
│  IMPACT: 50% fewer API calls                                                │
│                                                                             │
│  STRATEGY 4: BATCH PROCESSING                                               │
│  ────────────────────────────────────────────────────────────────────────   │
│  • Viva questions: Generate for whole class at once                         │
│  • Plagiarism: Batch check all submissions                                  │
│  IMPACT: 30% cost reduction                                                 │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════   │
│  TOTAL SAVINGS: 80-85%                                                      │
│  Cost per project: ₹300 → ₹50-60                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.4 AI Prompts

#### 10.4.1 Hint Generation Prompt

```
You are a patient programming tutor helping a student who is stuck.

CONTEXT:
- Student is working on: {project_type}
- Current stage: {stage_name}
- File they're editing: {file_path}
- Their current code:
```
{student_code}
```

TASK: {what_they_need_to_implement}

RULES:
1. DO NOT give the solution directly
2. Ask a guiding question OR give a small hint
3. Reference concepts they should know
4. Keep response under 100 words
5. Be encouraging

HINT LEVEL: {1|2|3}
- Level 1: Conceptual hint only
- Level 2: Pseudo-code or approach
- Level 3: Partial implementation with explanation
```

#### 10.4.2 Viva Question Generation Prompt

```
You are generating viva questions for a student's coding project.

PROJECT TYPE: {project_type}
TECH STACK: {tech_stack}

STUDENT'S CODE:
```
{code_files}
```

Generate 5 viva questions that:
1. Test understanding of concepts used (not memorization)
2. Ask "why" questions about design decisions
3. Include at least one "what if" scenario
4. Progress from basic to advanced
5. Can't be answered by just reading the code

FORMAT:
1. [Basic] Question...
2. [Basic] Question...
3. [Intermediate] Question...
4. [Advanced] Question...
5. [Scenario] Question...
```

---

## 11. Security Architecture

### 11.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SECURITY ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LAYER 1: NETWORK                                                           │
│  ─────────────────────────────────────────────────────────────────────     │
│  • WAF (Web Application Firewall)                                          │
│  • DDoS protection (CloudFlare)                                            │
│  • TLS 1.3 everywhere                                                      │
│  • VPC isolation                                                           │
│                                                                             │
│  LAYER 2: AUTHENTICATION                                                    │
│  ─────────────────────────────────────────────────────────────────────     │
│  • JWT tokens (15 min access, 7 day refresh)                               │
│  • SSO/SAML for colleges                                                   │
│  • MFA for faculty/admin (optional)                                        │
│  • Session management                                                       │
│                                                                             │
│  LAYER 3: AUTHORIZATION                                                     │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Role-based access control (RBAC)                                        │
│  • Resource-level permissions                                              │
│  • Row-level security in database                                          │
│                                                                             │
│  LAYER 4: DATA PROTECTION                                                   │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Encryption at rest (AES-256)                                            │
│  • Encryption in transit (TLS)                                             │
│  • PII handling compliance                                                 │
│  • Data retention policies                                                 │
│                                                                             │
│  LAYER 5: CODE EXECUTION                                                    │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Sandboxed Docker containers                                             │
│  • No network access                                                       │
│  • Resource limits (CPU, memory, time)                                     │
│  • Auto-cleanup                                                            │
│                                                                             │
│  LAYER 6: AUDIT                                                             │
│  ─────────────────────────────────────────────────────────────────────     │
│  • All admin actions logged                                                │
│  • Immutable audit trail                                                   │
│  • 1 year retention                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Role Permissions

| Permission | Student | Faculty | HOD | Admin |
|------------|---------|---------|-----|-------|
| View own projects | ✅ | ✅ | ✅ | ✅ |
| View class projects | ❌ | ✅ | ✅ | ✅ |
| View all projects | ❌ | ❌ | ✅ | ✅ |
| Create exams | ❌ | ✅ | ✅ | ✅ |
| View plagiarism reports | ❌ | ✅ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ✅ | ✅ |
| Manage college settings | ❌ | ❌ | ❌ | ✅ |
| View billing | ❌ | ❌ | ✅ | ✅ |

### 11.3 Exam Security

```
EXAM MODE LOCKDOWN:
─────────────────────────────────────────────────────────────────────

BROWSER RESTRICTIONS:
├── Full-screen enforcement
├── Right-click disabled
├── Keyboard shortcuts disabled (Ctrl+C, Ctrl+V, etc.)
├── Developer tools blocked
├── Tab switching detection
└── Browser extension detection

PROCTORING (Optional):
├── Webcam monitoring
├── Face detection
├── Multiple face alert
├── Audio monitoring
└── Screen recording

VIOLATION HANDLING:
├── Warning on first violation
├── Flag after 3 warnings
├── Auto-submit option after threshold
└── All violations logged with timestamp

DATA INTEGRITY:
├── Answers saved every 30 seconds
├── Local storage backup
├── Server sync on reconnect
└── Anti-tampering checksums
```

---

## 12. Plagiarism Detection System

### 12.1 Detection Methods

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PLAGIARISM DETECTION ENGINE                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  METHOD 1: TOKEN-BASED (MOSS-like)                                          │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Convert code to tokens                                                  │
│  • Remove whitespace, comments                                             │
│  • Compare token sequences                                                 │
│  • Detect variable renaming                                                │
│  DETECTS: Direct copying, variable rename                                  │
│                                                                             │
│  METHOD 2: AST COMPARISON                                                   │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Parse code to Abstract Syntax Tree                                      │
│  • Compare tree structures                                                 │
│  • Ignore superficial changes                                              │
│  DETECTS: Reordered statements, extracted functions                        │
│                                                                             │
│  METHOD 3: BEHAVIORAL ANALYSIS                                              │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Typing patterns (speed, rhythm)                                         │
│  • Copy-paste events                                                       │
│  • Time vs complexity mismatch                                             │
│  • Edit patterns                                                           │
│  DETECTS: External copying, contract cheating                              │
│                                                                             │
│  METHOD 4: AI DETECTION                                                     │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Detect AI-generated patterns                                            │
│  • Unusual code consistency                                                │
│  • Perfect naming conventions                                              │
│  DETECTS: ChatGPT, Copilot generated code                                  │
│                                                                             │
│  METHOD 5: EXTERNAL SOURCE MATCHING                                         │
│  ─────────────────────────────────────────────────────────────────────     │
│  • GitHub repository search                                                │
│  • StackOverflow matching                                                  │
│  • Tutorial code detection                                                 │
│  DETECTS: Internet copying                                                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.2 Similarity Score Calculation

```
OVERALL SCORE = weighted average of:

├── Token Similarity: 40%
│   Formula: (matching_tokens / total_tokens) × 100
│
├── AST Similarity: 30%
│   Formula: (matching_nodes / total_nodes) × 100
│
├── Behavioral Score: 20%
│   Factors:
│   ├── Paste events (high = suspicious)
│   ├── Typing speed anomalies
│   ├── Time vs code ratio
│   └── Error patterns
│
└── AI Detection Score: 10%
    Factors:
    ├── Code style consistency
    ├── Comment patterns
    └── Naming conventions

THRESHOLDS:
├── < 30%: Normal (green)
├── 30-50%: Review recommended (yellow)
├── 50-70%: Likely plagiarism (orange)
└── > 70%: Confirmed plagiarism (red)
```

### 12.3 Report Format

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PLAGIARISM REPORT                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Student: Rahul Kumar (CS2024-045)                                          │
│  Project: E-Commerce Application                                             │
│  Checked: January 22, 2026                                                  │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  OVERALL ORIGINALITY SCORE: 67% ⚠️                                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BREAKDOWN BY FILE                                 │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ File                    │ Originality │ Matches              │ Flag │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ auth/login.py           │ 45%         │ Vikram S. (87%)      │ 🔴   │   │
│  │ models/user.py          │ 92%         │ -                    │ 🟢   │   │
│  │ routes/products.py      │ 76%         │ GitHub (24%)         │ 🟡   │   │
│  │ utils/helpers.py        │ 58%         │ StackOverflow (42%)  │ 🟡   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BEHAVIORAL FLAGS                                  │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ ⚠️ 34 lines pasted at once (14:32:05 on Jan 18)                      │   │
│  │ ⚠️ Typing speed spike: 450 chars/min (avg: 120)                      │   │
│  │ ⚠️ No compilation errors in auth module (unusual)                    │   │
│  │ ✅ Consistent coding style throughout                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    RECOMMENDATION                                    │   │
│  ├─────────────────────────────────────────────────────────────────────┤   │
│  │ Based on analysis, this submission requires manual review.          │   │
│  │ Suggested actions:                                                   │   │
│  │ 1. Conduct viva on auth/login.py implementation                     │   │
│  │ 2. Ask student to explain JWT flow                                  │   │
│  │ 3. Compare with Vikram Shah's submission timeline                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [View Code Comparison] [Generate Viva Questions] [Mark as Reviewed]       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Deployment Options

### 13.1 Deployment Models

| Model | Description | Best For | Price Model |
|-------|-------------|----------|-------------|
| **SaaS (Cloud)** | Multi-tenant, hosted by us | Most colleges | Subscription |
| **Private Cloud** | Dedicated instance | Large universities | Premium subscription |
| **On-Premise** | Installed on college servers | Government/security-sensitive | License + support |
| **Hybrid** | IDE local, AI in cloud | Mixed requirements | Custom |

### 13.2 Infrastructure Requirements

#### SaaS Deployment

```
AWS/GCP INFRASTRUCTURE:
─────────────────────────────────────────────────────────────────────

COMPUTE:
├── API Servers: 3-5 instances (c5.xlarge or equivalent)
├── Worker Servers: 2-3 instances (for async tasks)
├── Code Execution: Kubernetes cluster (auto-scaling)
└── Load Balancer: Application Load Balancer

DATABASE:
├── Primary: RDS PostgreSQL (db.r5.xlarge)
├── Read Replicas: 2 instances
├── Redis: ElastiCache (r5.large)
└── Elasticsearch: 3-node cluster

STORAGE:
├── S3: Unlimited (code files, documents)
├── EBS: Attached to compute instances
└── Backup: S3 with lifecycle policies

NETWORKING:
├── VPC with private subnets
├── NAT Gateway for outbound
├── CloudFront CDN
└── Route53 DNS

ESTIMATED MONTHLY COST (at scale):
├── Compute: ₹1.5-2.5L
├── Database: ₹80K-1.2L
├── Storage: ₹30-50K
├── Network: ₹20-40K
├── Monitoring: ₹20-30K
└── TOTAL: ₹3-5L/month
```

#### On-Premise Requirements

```
MINIMUM SERVER REQUIREMENTS:
─────────────────────────────────────────────────────────────────────

APPLICATION SERVER (1-2 required):
├── CPU: 16 cores
├── RAM: 64 GB
├── Storage: 500 GB SSD
├── Network: 1 Gbps

DATABASE SERVER (1 required):
├── CPU: 8 cores
├── RAM: 32 GB
├── Storage: 1 TB SSD (RAID)
├── Network: 1 Gbps

CODE EXECUTION SERVER (1-2 required):
├── CPU: 32 cores
├── RAM: 64 GB
├── Storage: 500 GB SSD
├── Docker/Kubernetes installed

NETWORK:
├── Internal: 1 Gbps minimum
├── External: 100 Mbps minimum
├── SSL certificate
└── Firewall configured

SOFTWARE:
├── Ubuntu 22.04 LTS or RHEL 8+
├── Docker 24+
├── Kubernetes 1.28+ (optional)
├── PostgreSQL 15+
├── Redis 7+
└── Nginx
```

---

## 14. Revenue Model

### 14.1 Pricing Tiers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PRICING STRUCTURE                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TIER           PRICE           INCLUDES                                    │
│  ────────────────────────────────────────────────────────────────────────   │
│                                                                             │
│  STARTER        ₹1,50,000/yr    • 200 students                              │
│                                 • 1,000 projects/year                       │
│                                 • Basic plagiarism detection                │
│                                 • Email support                             │
│                                                                             │
│  STANDARD       ₹3,50,000/yr    • 500 students                              │
│                                 • 3,000 projects/year                       │
│                                 • Full plagiarism suite                     │
│                                 • Exam mode                                 │
│                                 • Priority support                          │
│                                                                             │
│  PREMIUM        ₹6,00,000/yr    • 1,000 students                            │
│                                 • 7,000 projects/year                       │
│                                 • All features                              │
│                                 • White-labeling                            │
│                                 • Dedicated support                         │
│                                 • Custom reports                            │
│                                                                             │
│  ENTERPRISE     Custom          • Unlimited students                        │
│                                 • Unlimited projects                        │
│                                 • On-premise option                         │
│                                 • SLA guarantee                             │
│                                 • Dedicated account manager                 │
│                                                                             │
│  ════════════════════════════════════════════════════════════════════════   │
│                                                                             │
│  ADD-ONS:                                                                   │
│  ├── Additional 100 projects: ₹15,000                                      │
│  ├── White-labeling: ₹2,00,000/year                                        │
│  ├── On-premise deployment: ₹5,00,000 (one-time) + ₹2L/year support       │
│  ├── Custom integration: ₹50,000 - ₹2,00,000                               │
│  └── Faculty training: ₹25,000/session                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.2 Unit Economics

```
STANDARD TIER ECONOMICS:
─────────────────────────────────────────────────────────────────────

REVENUE: ₹3,50,000/year

COSTS:
├── Projects: 3,000 × ₹60 (optimized) = ₹1,80,000
├── Infrastructure allocation = ₹40,000
├── Support allocation = ₹30,000
└── TOTAL COST: ₹2,50,000

GROSS PROFIT: ₹1,00,000 (29% margin)

AT SCALE (100 Standard customers):
├── Revenue: ₹3.5 Cr
├── Costs: ₹2.5 Cr
├── Gross Profit: ₹1 Cr
└── After OpEx: ~₹40-50L net profit
```

### 14.3 Financial Projections

| Year | Colleges | Revenue | Costs | Profit |
|------|----------|---------|-------|--------|
| 1 | 20 | ₹80L | ₹3 Cr | -₹2.2 Cr |
| 2 | 80 | ₹4 Cr | ₹3.5 Cr | ₹50L |
| 3 | 200 | ₹12 Cr | ₹7 Cr | ₹5 Cr |
| 4 | 400 | ₹25 Cr | ₹12 Cr | ₹13 Cr |
| 5 | 700 | ₹45 Cr | ₹20 Cr | ₹25 Cr |

---

## 15. Implementation Roadmap

### 15.1 Phase Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     IMPLEMENTATION ROADMAP                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: MVP (Month 1-3)                                                   │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Learning mode (concept + quiz gates)                                    │
│  • Basic faculty dashboard                                                  │
│  • Peer plagiarism detection                                               │
│  • VS Code extension                                                       │
│  GOAL: Pilot-ready product                                                 │
│                                                                             │
│  PHASE 2: ACADEMIC SUITE (Month 4-6)                                        │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Web-based IDE                                                           │
│  • Exam mode with lockdown                                                 │
│  • Viva question generation                                                │
│  • External plagiarism sources                                             │
│  • Reports & analytics                                                     │
│  GOAL: Full academic feature set                                           │
│                                                                             │
│  PHASE 3: SCALE (Month 7-9)                                                 │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Infrastructure scaling                                                  │
│  • Performance optimization                                                │
│  • Security hardening                                                      │
│  • Desktop app (Electron)                                                  │
│  GOAL: Handle 50+ colleges                                                 │
│                                                                             │
│  PHASE 4: ENTERPRISE (Month 10-12)                                          │
│  ─────────────────────────────────────────────────────────────────────     │
│  • White-labeling                                                          │
│  • SSO/SAML integration                                                    │
│  • On-premise deployment                                                   │
│  • API platform                                                            │
│  • Advanced analytics                                                      │
│  GOAL: Enterprise-ready product                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 15.2 Detailed Task Breakdown

#### Phase 1: MVP (Month 1-3)

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 1-2 | Learning content creation | 50 concept explanations, 200 quiz questions |
| 2-3 | Learning mode UI | Sidebar panel, quiz component, progress tracker |
| 3-4 | Learning mode backend | Quiz API, progress tracking, hint system |
| 4-5 | Faculty dashboard UI | Class list, student progress table |
| 5-6 | Faculty dashboard backend | Aggregation APIs, activity queries |
| 6-7 | Plagiarism engine v1 | Token comparison, peer matching |
| 7-8 | VS Code extension | Basic panels, BharatBuild integration |
| 9-10 | Integration & testing | End-to-end testing, bug fixes |
| 11-12 | Pilot preparation | Documentation, demo, pilot college setup |

#### Phase 2: Academic Suite (Month 4-6)

| Week | Tasks | Deliverables |
|------|-------|--------------|
| 1-3 | Web IDE core | Monaco editor, file system, terminal |
| 3-5 | Code execution | Docker sandbox, language support |
| 5-6 | Exam mode UI | Lockdown interface, question navigation |
| 6-7 | Exam mode backend | Timer, auto-submit, violation detection |
| 7-8 | Proctoring | Webcam integration, face detection |
| 8-9 | Viva system | Question generation, AI viva mode |
| 9-10 | Reports | PDF generation, NAAC format |
| 10-12 | External plagiarism | GitHub/SO integration, AI detection |

### 15.3 Team Requirements

| Phase | Developers | Designers | QA | DevOps | Total |
|-------|------------|-----------|-----|--------|-------|
| Phase 1 | 3 | 1 | 1 | 0.5 | 5.5 |
| Phase 2 | 4 | 1 | 1 | 1 | 7 |
| Phase 3 | 3 | 0.5 | 1 | 2 | 6.5 |
| Phase 4 | 4 | 1 | 1 | 1 | 7 |

---

## 16. Competitive Analysis

### 16.1 Competitor Comparison

| Feature | VS Code | Replit | GitHub Copilot | HackerRank | BharatBuild Studio |
|---------|---------|--------|----------------|------------|-------------------|
| Code Editor | ✅ | ✅ | ❌ | ✅ | ✅ |
| AI Code Gen | ❌ | ✅ | ✅ | ❌ | ✅ |
| Full Project Gen | ❌ | ❌ | ❌ | ❌ | ✅ |
| Learning Mode | ❌ | ❌ | ❌ | ✅ | ✅ |
| Plagiarism Detection | ❌ | ❌ | ❌ | ❌ | ✅ |
| Faculty Dashboard | ❌ | ❌ | ❌ | ✅ | ✅ |
| Exam Lockdown | ❌ | ❌ | ❌ | ✅ | ✅ |
| Viva Support | ❌ | ❌ | ❌ | ❌ | ✅ |
| India Syllabus | ❌ | ❌ | ❌ | ❌ | ✅ |
| Accreditation Reports | ❌ | ❌ | ❌ | ❌ | ✅ |

### 16.2 Competitive Advantages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMPETITIVE MOATS                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. INTEGRATED SOLUTION                                                     │
│     No competitor offers: IDE + AI Gen + Learning + Assessment + Proctoring│
│     Colleges currently use 4-5 different tools                             │
│                                                                             │
│  2. LEARNING VERIFICATION                                                   │
│     We prove students learned, not just submitted                          │
│     No other platform tracks this deeply                                   │
│                                                                             │
│  3. INDIA-SPECIFIC                                                          │
│     Syllabus mapping to Indian universities                                │
│     NAAC/NBA report formats                                                │
│     Hindi language support (future)                                        │
│     Pricing for Indian market                                              │
│                                                                             │
│  4. BEHAVIORAL PLAGIARISM                                                   │
│     Not just code comparison                                               │
│     Typing patterns, time analysis                                         │
│     AI-generated code detection                                            │
│                                                                             │
│  5. FACULTY EMPOWERMENT                                                     │
│     Auto-generated viva questions                                          │
│     Real-time monitoring                                                   │
│     Reduces faculty workload by 50%+                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 17. Appendix

### 17.1 Glossary

| Term | Definition |
|------|------------|
| AST | Abstract Syntax Tree - code structure representation |
| JWT | JSON Web Token - authentication mechanism |
| LMS | Learning Management System |
| MOSS | Measure of Software Similarity - plagiarism tool |
| NAAC | National Assessment and Accreditation Council |
| NBA | National Board of Accreditation |
| OBE | Outcome Based Education |
| SAML | Security Assertion Markup Language - SSO protocol |
| SSO | Single Sign-On |
| WAF | Web Application Firewall |

### 17.2 References

- VS Code Architecture: https://code.visualstudio.com/docs
- Monaco Editor: https://microsoft.github.io/monaco-editor/
- MOSS (Stanford): https://theory.stanford.edu/~aiken/moss/
- NAAC Guidelines: https://www.naac.gov.in
- NBA Accreditation: https://www.nbaind.org

### 17.3 Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 2026 | BharatBuild Team | Initial document |

---

**Document Status:** Draft for Review
**Next Review:** February 2026
**Owner:** Product Team

---

*This document is confidential and intended for internal use only.*
