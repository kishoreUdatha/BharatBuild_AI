# BharatBuild Studio - Business Plan

> **Version:** 1.0
> **Date:** January 2026
> **Status:** Planning Phase
> **Confidential:** Internal Use Only

---

## Executive Summary

### The Opportunity

India has **3,500+ engineering colleges** producing **1.5 million+ engineering graduates** annually. These colleges face:

- **Plagiarism epidemic:** 60-70% of student projects are copied
- **No learning verification:** Students submit without understanding
- **Accreditation pressure:** NAAC/NBA require outcome-based education proof
- **Faculty overload:** 1 faculty for 60+ students, manual tracking impossible

### The Solution

**BharatBuild Studio** - An AI-powered IDE that ensures students learn while building projects, with complete tracking and plagiarism detection.

### Market Size

| Segment | Count | Avg Price | TAM |
|---------|-------|-----------|-----|
| Private Engineering Colleges | 3,500 | ₹5L/yr | ₹1,750 Cr |
| Deemed Universities | 130 | ₹15L/yr | ₹195 Cr |
| State Tech Universities | 50 | ₹50L/yr | ₹250 Cr |
| **Total Addressable Market** | | | **₹2,195 Cr** |

### Financial Projections

| Year | Colleges | Revenue | Profit |
|------|----------|---------|--------|
| Year 1 | 20 | ₹80L | -₹2.2 Cr (Investment) |
| Year 2 | 80 | ₹4 Cr | ₹50L |
| Year 3 | 200 | ₹12 Cr | ₹5 Cr |

### Funding Required

**Seed Round: ₹2-3 Cr** for 12-18 month runway to reach break-even.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Solution Overview](#2-solution-overview)
3. [Market Analysis](#3-market-analysis)
4. [Business Model](#4-business-model)
5. [Go-to-Market Strategy](#5-go-to-market-strategy)
6. [Competitive Landscape](#6-competitive-landscape)
7. [Financial Plan](#7-financial-plan)
8. [Team & Organization](#8-team--organization)
9. [Risk Analysis](#9-risk-analysis)
10. [Funding Requirements](#10-funding-requirements)
11. [Milestones & Timeline](#11-milestones--timeline)

---

## 1. Problem Statement

### 1.1 The Education Crisis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     THE PROBLEM                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  STUDENTS:                                                                  │
│  ├── Copy projects from seniors, GitHub, internet                          │
│  ├── Use ChatGPT to generate code they don't understand                    │
│  ├── Fail in viva examinations                                             │
│  ├── Struggle in technical interviews                                       │
│  └── 47% of engineering graduates are unemployable (Aspiring Minds, 2019)  │
│                                                                             │
│  FACULTY:                                                                   │
│  ├── 60+ students per faculty member                                       │
│  ├── Cannot manually check each submission for plagiarism                  │
│  ├── No visibility into student progress during semester                   │
│  ├── Viva is the only verification, easily gamed                           │
│  └── Burnout from repetitive grading tasks                                 │
│                                                                             │
│  COLLEGES:                                                                  │
│  ├── NAAC/NBA require outcome-based education evidence                     │
│  ├── Placement rates affected by skill gaps                                │
│  ├── Multiple disconnected tools (LMS, IDE, plagiarism checker)            │
│  └── No data to prove students actually learned                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Current Solutions Fall Short

| Solution | Problem |
|----------|---------|
| Traditional LMS (Moodle) | No code execution, no AI, no plagiarism |
| Plagiarism tools (Turnitin) | Checks documents, not code behavior |
| Coding platforms (HackerRank) | Tests skills, doesn't teach or build projects |
| AI tools (ChatGPT) | Generates code, no learning, increases plagiarism |

### 1.3 The Gap

**No existing solution combines:**
- Project generation WITH learning
- Plagiarism detection WITH behavioral analysis
- Faculty monitoring WITH automated reporting
- AI assistance WITH understanding verification

---

## 2. Solution Overview

### 2.1 Product Description

**BharatBuild Studio** is an integrated development environment (IDE) specifically designed for engineering education that:

1. **Generates full projects** using AI while teaching concepts
2. **Tracks every interaction** for genuine learning proof
3. **Detects plagiarism** through code AND behavioral analysis
4. **Empowers faculty** with real-time dashboards and automated tools
5. **Conducts secure exams** with lockdown and proctoring

### 2.2 Key Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     FEATURE MATRIX                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  FOR STUDENTS:                                                              │
│  ├── Full-featured code editor (VS Code-based)                             │
│  ├── AI assistant that teaches, not just generates                         │
│  ├── Progressive hints (not direct solutions)                              │
│  ├── Concept explanations with quizzes                                     │
│  ├── Progress tracking and achievements                                    │
│  └── Viva preparation mode                                                 │
│                                                                             │
│  FOR FACULTY:                                                               │
│  ├── Real-time class dashboard                                             │
│  ├── Individual student deep-dives                                         │
│  ├── Automated plagiarism detection                                        │
│  ├── AI-generated viva questions                                           │
│  ├── Secure exam mode with proctoring                                      │
│  └── One-click NAAC/NBA reports                                            │
│                                                                             │
│  FOR ADMINISTRATION:                                                        │
│  ├── College-wide analytics                                                │
│  ├── Batch management                                                      │
│  ├── License and usage tracking                                            │
│  └── Integration with existing systems                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 How It Works

```
STUDENT JOURNEY:
─────────────────────────────────────────────────────────────────────

1. CREATE PROJECT
   └── Student describes what they want to build
       └── AI creates project structure

2. LEARN & BUILD (per stage)
   ├── Read concept explanation
   ├── Pass quiz to proceed
   ├── Write code with AI hints
   ├── Run and debug
   └── Submit stage

3. VERIFICATION
   ├── Plagiarism check (automatic)
   ├── Understanding quiz
   └── Viva preparation

4. SUBMISSION
   ├── Final project review
   ├── Faculty approval
   └── Grade assigned

FACULTY JOURNEY:
─────────────────────────────────────────────────────────────────────

1. ASSIGN PROJECT
   └── Select project type, deadline, rules

2. MONITOR
   ├── Real-time progress dashboard
   ├── Identify struggling students
   └── Review plagiarism alerts

3. ASSESS
   ├── AI-generated viva questions
   ├── Code review
   └── Grade submission

4. REPORT
   └── Export for accreditation
```

---

## 3. Market Analysis

### 3.1 Target Market

#### Primary: Private Engineering Colleges

```
Count: 3,500+
Decision Maker: Principal/Director
Budget: ₹3-10 lakhs available
Buying Cycle: 2-4 months
Pain Points:
├── Placement pressure
├── Accreditation requirements
├── Project quality concerns
└── Faculty workload
```

#### Secondary: Deemed Universities

```
Count: 130+
Decision Maker: Academic Council
Budget: ₹10-30 lakhs
Buying Cycle: 4-6 months
Pain Points:
├── NAAC rankings
├── Research output measurement
├── Outcome-based education compliance
└── Multiple campus management
```

#### Tertiary: State Technical Universities

```
Count: 50+
Decision Maker: Vice Chancellor / Board
Budget: ₹50L - 2 Cr
Buying Cycle: 6-12 months
Impact: 100+ affiliated colleges each
Pain Points:
├── Standardization across colleges
├── Central monitoring
├── Quality assurance
└── Exam integrity
```

### 3.2 Market Size

```
TOTAL ADDRESSABLE MARKET (TAM):
─────────────────────────────────────────────────────────────────────

Private Colleges: 3,500 × ₹5L = ₹1,750 Cr
Deemed Universities: 130 × ₹15L = ₹195 Cr
State Universities: 50 × ₹50L = ₹250 Cr
─────────────────────────────────────────────
TOTAL TAM: ₹2,195 Cr/year

SERVICEABLE ADDRESSABLE MARKET (SAM):
─────────────────────────────────────────────────────────────────────

Assuming 30% adopt EdTech solutions:
₹2,195 Cr × 30% = ₹658 Cr/year

SERVICEABLE OBTAINABLE MARKET (SOM):
─────────────────────────────────────────────────────────────────────

Year 1: 0.1% = ₹65L (20 colleges)
Year 3: 1% = ₹6.5 Cr (130 colleges)
Year 5: 3% = ₹20 Cr (400 colleges)
```

### 3.3 Market Trends

| Trend | Impact |
|-------|--------|
| NEP 2020 | Emphasis on outcome-based education |
| AICTE mandates | Digital infrastructure requirements |
| AI in education | Growing acceptance of AI tools |
| Remote/hybrid learning | Need for online assessment |
| Employability focus | Pressure on practical skills |

---

## 4. Business Model

### 4.1 Revenue Streams

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     REVENUE STREAMS                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PRIMARY: SUBSCRIPTION (85% of revenue)                                     │
│  ─────────────────────────────────────────────────────────────────────     │
│  Annual college licenses based on student count                            │
│                                                                             │
│  Tier        Price           Students    Projects                          │
│  Starter     ₹1,50,000/yr    200         1,000                             │
│  Standard    ₹3,50,000/yr    500         3,000                             │
│  Premium     ₹6,00,000/yr    1,000       7,000                             │
│  Enterprise  Custom          Unlimited   Unlimited                         │
│                                                                             │
│  SECONDARY: ADD-ONS (10% of revenue)                                        │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Additional projects: ₹15,000 per 100                                    │
│  • White-labeling: ₹2,00,000/year                                          │
│  • Custom integrations: ₹50,000 - 2,00,000                                 │
│                                                                             │
│  TERTIARY: SERVICES (5% of revenue)                                         │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Faculty training: ₹25,000/session                                       │
│  • Implementation support: ₹50,000                                         │
│  • Custom development: Time & material                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Unit Economics

```
STANDARD TIER ANALYSIS:
─────────────────────────────────────────────────────────────────────

REVENUE PER COLLEGE: ₹3,50,000/year

VARIABLE COSTS:
├── AI API costs (3,000 projects × ₹60) = ₹1,80,000
├── Infrastructure allocation = ₹40,000
├── Support (tickets, calls) = ₹30,000
└── TOTAL VARIABLE: ₹2,50,000

CONTRIBUTION MARGIN: ₹1,00,000 (29%)

FIXED COSTS (spread across 100 customers):
├── Team: ₹1.5 Cr / 100 = ₹1,50,000
├── Infrastructure (fixed) = ₹30,000
├── Other = ₹20,000
└── TOTAL FIXED ALLOCATION: ₹2,00,000

NET MARGIN: -₹1,00,000 per customer at 100 scale

BREAK-EVEN: ~150 colleges
```

### 4.3 Customer Lifetime Value

```
ASSUMPTIONS:
├── Average contract: ₹4,00,000/year
├── Churn rate: 15%/year
├── Average lifetime: 6.7 years
└── Upsell rate: 20%/year

LTV CALCULATION:
├── Base LTV: ₹4L × 6.7 = ₹26.8L
├── With upsells: ₹26.8L × 1.2 = ₹32L
└── LTV: ₹32,00,000

CAC TARGET (LTV:CAC = 3:1):
└── Max CAC: ₹10,66,000

CURRENT CAC ESTIMATE:
├── Sales cycle: 3 months
├── Sales rep cost: ₹15L/year
├── Deals per rep: 10/year
├── Marketing per deal: ₹50,000
└── CAC: ₹2,00,000

LTV:CAC RATIO: 16:1 ✓ (Excellent)
```

---

## 5. Go-to-Market Strategy

### 5.1 Sales Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SALES APPROACH                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PHASE 1: PILOT PROGRAM (Month 1-3)                                         │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Offer FREE pilots to 10 colleges                                        │
│  • 1 semester, 50-100 students each                                        │
│  • Collect testimonials and case studies                                   │
│  • Build reference customers                                               │
│  COST: ₹5-10L (API + support)                                              │
│                                                                             │
│  PHASE 2: EARLY ADOPTER (Month 4-6)                                         │
│  ─────────────────────────────────────────────────────────────────────     │
│  • 50% discount for first 20 customers                                     │
│  • 2-year contract lock-in                                                 │
│  • Case study participation required                                       │
│  TARGET: 15-20 colleges, ₹40-50L revenue                                   │
│                                                                             │
│  PHASE 3: SCALE (Month 7-12)                                                │
│  ─────────────────────────────────────────────────────────────────────     │
│  • Full pricing                                                            │
│  • Hire 2-3 sales reps                                                     │
│  • Regional expansion                                                      │
│  • Partner channel development                                             │
│  TARGET: 40-60 more colleges                                               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Marketing Strategy

| Channel | Activity | Budget | Expected Leads |
|---------|----------|--------|----------------|
| **Events** | AICTE conferences, education summits | ₹10L/year | 50 |
| **Digital** | LinkedIn ads, Google ads | ₹15L/year | 100 |
| **Content** | Blog, webinars, case studies | ₹5L/year | 80 |
| **Referrals** | Customer referral program | ₹5L/year | 30 |
| **Partnerships** | System integrators, EdTech platforms | ₹5L/year | 40 |

### 5.3 Channel Strategy

```
DIRECT SALES (60% of revenue):
├── Target: Premium and Enterprise customers
├── Team: 3-5 sales reps by Year 2
├── Average deal: ₹5-15L
└── Cycle: 2-4 months

PARTNER CHANNEL (30% of revenue):
├── System integrators (TCS, Infosys education arms)
├── EdTech aggregators
├── University technology partners
├── Revenue share: 20-30%
└── Deals: ₹3-5L average

SELF-SERVE (10% of revenue):
├── Target: Small colleges, individual departments
├── Online signup and payment
├── Lower price point: ₹1-2L
└── Minimal sales touch
```

---

## 6. Competitive Landscape

### 6.1 Competitor Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     COMPETITIVE MATRIX                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Feature              │ VS Code │ Replit │ HackerRank │ BharatBuild Studio │
│  ─────────────────────────────────────────────────────────────────────     │
│  Code Editor          │ ✅      │ ✅     │ ✅         │ ✅                  │
│  AI Code Generation   │ ❌      │ ✅     │ ❌         │ ✅                  │
│  Full Project Gen     │ ❌      │ ❌     │ ❌         │ ✅                  │
│  Learning Mode        │ ❌      │ ❌     │ ✅         │ ✅                  │
│  Plagiarism Detection │ ❌      │ ❌     │ ❌         │ ✅                  │
│  Behavioral Analysis  │ ❌      │ ❌     │ ❌         │ ✅                  │
│  Faculty Dashboard    │ ❌      │ ❌     │ ✅         │ ✅                  │
│  Exam Mode           │ ❌      │ ❌     │ ✅         │ ✅                  │
│  Viva Support        │ ❌      │ ❌     │ ❌         │ ✅                  │
│  India Syllabus      │ ❌      │ ❌     │ ❌         │ ✅                  │
│  NAAC/NBA Reports    │ ❌      │ ❌     │ ❌         │ ✅                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Competitive Advantages

| Advantage | Description | Defensibility |
|-----------|-------------|---------------|
| **Integration** | Only platform with IDE + AI + Learning + Assessment | High - requires 12+ months to replicate |
| **Learning Verification** | Behavioral analysis proves understanding | Medium - algorithm can be copied |
| **India Focus** | Syllabus mapping, NAAC reports, local support | High - requires local expertise |
| **BharatBuild Engine** | Existing AI project generation IP | High - years of development |
| **Data Network Effects** | More data = better plagiarism detection | Grows with usage |

### 6.3 Barriers to Entry

1. **Technical complexity:** Combining IDE + AI + Analytics requires diverse expertise
2. **Content library:** 500+ concept explanations, 2000+ quiz questions
3. **India knowledge:** Understanding NAAC, NBA, university systems
4. **Trust:** Colleges need proven vendor with references
5. **Integration:** Existing BharatBuild user base and technology

---

## 7. Financial Plan

### 7.1 Revenue Projections

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     5-YEAR REVENUE PROJECTION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Year    Colleges   Avg Deal   Revenue      Growth                          │
│  ─────────────────────────────────────────────────────────────────────     │
│  Year 1     20      ₹4.0L      ₹80L         -                              │
│  Year 2     80      ₹5.0L      ₹4.0 Cr      400%                           │
│  Year 3    200      ₹6.0L      ₹12.0 Cr     200%                           │
│  Year 4    400      ₹6.5L      ₹26.0 Cr     117%                           │
│  Year 5    700      ₹7.0L      ₹49.0 Cr     88%                            │
│                                                                             │
│  REVENUE MIX (Year 3):                                                      │
│  ├── Subscriptions: ₹10.2 Cr (85%)                                         │
│  ├── Add-ons: ₹1.2 Cr (10%)                                                │
│  └── Services: ₹0.6 Cr (5%)                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Cost Structure

```
YEAR 1 COSTS:
─────────────────────────────────────────────────────────────────────

DEVELOPMENT:
├── Team (5-6 people): ₹60-80L
├── Contractors/freelancers: ₹10-15L
└── Tools & licenses: ₹5L
SUBTOTAL: ₹75-100L

INFRASTRUCTURE:
├── Cloud (AWS/GCP): ₹25-40L
├── AI APIs: ₹20-30L
└── Other services: ₹10L
SUBTOTAL: ₹55-80L

OPERATIONS:
├── Sales & marketing: ₹30-40L
├── Support: ₹10-15L
├── Admin & legal: ₹15-20L
└── Miscellaneous: ₹10L
SUBTOTAL: ₹65-85L

─────────────────────────────────────────────────────────────────────
TOTAL YEAR 1: ₹1.95 - 2.65 Cr
AVERAGE: ~₹2.3 Cr
```

### 7.3 Profitability Timeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PROFIT & LOSS PROJECTION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│             Year 1    Year 2    Year 3    Year 4    Year 5                 │
│  ─────────────────────────────────────────────────────────────────────     │
│  Revenue     ₹80L     ₹4.0Cr   ₹12.0Cr   ₹26.0Cr   ₹49.0Cr                │
│                                                                             │
│  COGS        ₹30L     ₹1.5Cr   ₹4.0Cr    ₹8.0Cr    ₹14.0Cr                │
│  (AI, Infra)                                                               │
│                                                                             │
│  Gross       ₹50L     ₹2.5Cr   ₹8.0Cr    ₹18.0Cr   ₹35.0Cr                │
│  Profit      (63%)    (63%)    (67%)     (69%)     (71%)                   │
│                                                                             │
│  OpEx        ₹2.5Cr   ₹2.0Cr   ₹3.0Cr    ₹5.0Cr    ₹8.0Cr                 │
│  (Team, S&M)                                                               │
│                                                                             │
│  EBITDA      -₹2.0Cr  ₹50L     ₹5.0Cr    ₹13.0Cr   ₹27.0Cr                │
│              (-250%)  (13%)    (42%)     (50%)     (55%)                   │
│                                                                             │
│  Status      Invest   Break    Profit    Scale     Scale                   │
│                       even                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Cash Flow

```
MONTHLY BURN RATE:
─────────────────────────────────────────────────────────────────────

Year 1: ₹2.3 Cr / 12 = ₹19L/month
Year 2: ₹3.5 Cr / 12 = ₹29L/month (before revenue)

FUNDING REQUIREMENTS:
─────────────────────────────────────────────────────────────────────

Months to break-even: 18-20
Burn until break-even: ₹19L × 18 = ₹3.4 Cr
Revenue during period: ~₹1.2 Cr
Net funding needed: ₹2.2 Cr

Recommended raise: ₹2.5-3 Cr (with buffer)
```

---

## 8. Team & Organization

### 8.1 Current Team

```
FOUNDERS:
─────────────────────────────────────────────────────────────────────

[Your details here]
├── Role: CEO / Product
├── Background: [Your background]
└── Responsibilities: Vision, product, fundraising

CORE TEAM:
─────────────────────────────────────────────────────────────────────

[Existing team members]
```

### 8.2 Hiring Plan

| Role | Year 1 | Year 2 | Year 3 |
|------|--------|--------|--------|
| Engineering | 4 | 8 | 15 |
| Product | 1 | 2 | 3 |
| Design | 1 | 2 | 2 |
| Sales | 1 | 3 | 6 |
| Marketing | 0 | 1 | 2 |
| Customer Success | 1 | 3 | 5 |
| Operations | 1 | 2 | 3 |
| **Total** | **9** | **21** | **36** |

### 8.3 Organization Structure

```
Year 1:
─────────────────────────────────────────────────────────────────────

                    CEO/Founder
                        │
        ┌───────────────┼───────────────┐
        │               │               │
    Engineering     Product &       Sales &
    Lead (1)        Design (2)      Ops (2)
        │
    Engineers (3)


Year 3:
─────────────────────────────────────────────────────────────────────

                        CEO
                         │
    ┌────────────┬───────┼───────┬────────────┐
    │            │       │       │            │
   CTO         CPO     CFO    VP Sales    VP Customer
    │           │               │          Success
    │           │               │            │
Engineering  Product        Sales (6)   CS Team (5)
Team (15)   & Design (5)
```

---

## 9. Risk Analysis

### 9.1 Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Slow college adoption** | Medium | High | Pilot program, reference customers, ROI calculator |
| **AI cost overruns** | Medium | High | Cost optimization (caching, model routing), usage limits |
| **Competition from big players** | Low | High | India focus, integration depth, speed to market |
| **Technical scalability issues** | Medium | Medium | Early architecture decisions, load testing |
| **Regulatory changes** | Low | Medium | Stay updated on AICTE/UGC policies |
| **Key person dependency** | Medium | Medium | Documentation, knowledge sharing, key hires |
| **Data security breach** | Low | High | Security audits, encryption, compliance |

### 9.2 Contingency Plans

```
SCENARIO 1: Slower than expected adoption
─────────────────────────────────────────────────────────────────────
Triggers: <10 colleges in Year 1
Actions:
├── Extend pilot program
├── Reduce team size
├── Focus on 1-2 key features
├── Pivot to per-student pricing
└── Consider B2B2C model

SCENARIO 2: AI costs exceed projections
─────────────────────────────────────────────────────────────────────
Triggers: >₹150/project average
Actions:
├── Aggressive caching
├── Shift to cheaper models
├── Pre-generate more content
├── Implement usage limits
└── Raise prices

SCENARIO 3: Major competitor enters market
─────────────────────────────────────────────────────────────────────
Triggers: Google/Microsoft launches similar product
Actions:
├── Double down on India specifics
├── Accelerate feature development
├── Lock in customers with long contracts
├── Consider acquisition discussions
└── Niche focus (specific university systems)
```

---

## 10. Funding Requirements

### 10.1 Use of Funds

```
SEED ROUND: ₹2.5 - 3 Cr
─────────────────────────────────────────────────────────────────────

ALLOCATION:
├── Product Development: ₹1.2 Cr (40%)
│   ├── Engineering salaries
│   ├── AI/ML development
│   └── Infrastructure setup
│
├── Go-to-Market: ₹90L (30%)
│   ├── Sales team
│   ├── Marketing campaigns
│   ├── Pilot program costs
│   └── Events and conferences
│
├── Operations: ₹60L (20%)
│   ├── Office and admin
│   ├── Legal and compliance
│   └── Tools and software
│
└── Buffer: ₹30L (10%)
    └── Contingency

RUNWAY: 18-20 months (to break-even)
```

### 10.2 Funding Sources

| Source | Amount | Probability | Timeline |
|--------|--------|-------------|----------|
| Angel investors | ₹50L - 1Cr | High | 1-2 months |
| Seed funds (India) | ₹1-2 Cr | Medium | 2-3 months |
| EdTech-focused VCs | ₹2-5 Cr | Medium | 3-4 months |
| Government grants | ₹25-50L | Low | 4-6 months |
| Revenue (self-fund) | ₹50-80L | Medium | 6-12 months |

### 10.3 Investor Targets

```
ANGEL INVESTORS:
├── Indian Angel Network
├── LetsVenture
├── AngelList India
├── EdTech founder angels
└── College/University alumni networks

SEED FUNDS:
├── Blume Ventures
├── Kalaari Capital (early)
├── 100X.VC
├── Titan Capital
└── Better Capital

EDTECH-FOCUSED:
├── Owl Ventures
├── GSV Ventures
├── Unitus Ventures
├── Gray Matters Capital
└── Kaizen PE (education focus)
```

---

## 11. Milestones & Timeline

### 11.1 Key Milestones

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     MILESTONE ROADMAP                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Q1 2026 (Month 1-3):                                                       │
│  ├── ✓ Complete product design document                                    │
│  ├── □ MVP development (Learning mode + Faculty dashboard)                 │
│  ├── □ 5 pilot colleges signed                                             │
│  └── □ Seed funding closed                                                 │
│                                                                             │
│  Q2 2026 (Month 4-6):                                                       │
│  ├── □ Pilot program running                                               │
│  ├── □ Web IDE launched                                                    │
│  ├── □ 10 paying customers                                                 │
│  └── □ ₹50L ARR                                                            │
│                                                                             │
│  Q3 2026 (Month 7-9):                                                       │
│  ├── □ Exam mode launched                                                  │
│  ├── □ 30 paying customers                                                 │
│  ├── □ ₹1.5 Cr ARR                                                         │
│  └── □ Desktop app beta                                                    │
│                                                                             │
│  Q4 2026 (Month 10-12):                                                     │
│  ├── □ Full platform launched                                              │
│  ├── □ 50+ customers                                                       │
│  ├── □ ₹3 Cr ARR                                                           │
│  └── □ Series A discussions                                                │
│                                                                             │
│  2027:                                                                      │
│  ├── □ 200 colleges                                                        │
│  ├── □ ₹12 Cr ARR                                                          │
│  ├── □ Profitability achieved                                              │
│  └── □ Enterprise features complete                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Success Metrics

| Metric | Q2 2026 | Q4 2026 | Q4 2027 |
|--------|---------|---------|---------|
| Paying Colleges | 10 | 50 | 200 |
| ARR | ₹50L | ₹3 Cr | ₹12 Cr |
| Active Students | 2,000 | 15,000 | 80,000 |
| NPS Score | 30 | 40 | 50 |
| Churn Rate | <20% | <15% | <10% |
| CAC Payback | 18 mo | 12 mo | 8 mo |

---

## Contact

**BharatBuild**
[Your contact details]

---

*This business plan is confidential and intended for potential investors and partners only.*
