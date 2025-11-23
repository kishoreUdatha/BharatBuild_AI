# BharatBuild AI - System Architecture

## Overview

BharatBuild AI is a microservices-based platform with a modern, scalable architecture designed for high availability and performance.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Load Balancer (Nginx)                   │
└────────────┬────────────────────────────────────┬────────────────┘
             │                                    │
     ┌───────▼────────┐                  ┌────────▼────────┐
     │   Frontend     │                  │    Backend      │
     │   (Next.js)    │◄─────────────────┤   (FastAPI)     │
     │   Port 3000    │      REST API    │   Port 8000     │
     └────────────────┘                  └────┬────┬───┬───┘
                                              │    │   │
                    ┌─────────────────────────┘    │   └─────────────┐
                    │                              │                 │
            ┌───────▼────────┐          ┌──────────▼────────┐  ┌────▼─────┐
            │   PostgreSQL   │          │   Redis Cache     │  │  MinIO   │
            │   Database     │          │   Session Store   │  │  Storage │
            │   Port 5432    │          │   Port 6379       │  │  Port 9000│
            └────────────────┘          └───────────────────┘  └──────────┘
                                                  │
                                        ┌─────────▼────────┐
                                        │  Celery Workers  │
                                        │  (Background)    │
                                        └──────────────────┘
                                                  │
                                        ┌─────────▼────────┐
                                        │  Claude AI API   │
                                        │  (Anthropic)     │
                                        └──────────────────┘
```

## Component Architecture

### Frontend Layer (Next.js)

```
┌──────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                    │
├──────────────────────────────────────────────────────────┤
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   Pages    │  │ Components │  │   Hooks    │         │
│  │            │  │            │  │            │         │
│  │ - Home     │  │ - Dashboard│  │ - useAuth  │         │
│  │ - Dashboard│  │ - Projects │  │ - useAPI   │         │
│  │ - Projects │  │ - Forms    │  │ - useUser  │         │
│  │ - Auth     │  │ - Layout   │  │            │         │
│  └────────────┘  └────────────┘  └────────────┘         │
│                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │   State    │  │   API      │  │   Utils    │         │
│  │ Management │  │  Client    │  │            │         │
│  │            │  │            │  │            │         │
│  │ - Zustand  │  │ - Axios    │  │ - Helpers  │         │
│  │ - SWR      │  │ - Fetch    │  │ - Validators│        │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
```

### Backend Layer (FastAPI)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                         │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      API Layer                          │    │
│  │                                                          │    │
│  │  /auth      /projects    /api-keys    /billing         │    │
│  │     │            │            │            │            │    │
│  └─────┼────────────┼────────────┼────────────┼────────────┘    │
│        │            │            │            │                 │
│  ┌─────▼────────────▼────────────▼────────────▼────────────┐    │
│  │                   Business Logic                        │    │
│  │                                                          │    │
│  │  AuthModule  ProjectModule  APIKeyModule  BillingModule│    │
│  └──────────────────────────┬───────────────────────────────┘    │
│                             │                                    │
│  ┌──────────────────────────▼───────────────────────────────┐    │
│  │                  AI Agent Layer                          │    │
│  │                                                          │    │
│  │  ┌────────────────────────────────────────────────┐     │    │
│  │  │        Multi-Agent Orchestrator                │     │    │
│  │  │                                                │     │    │
│  │  │  IdeaAgent  SRSAgent  CodeAgent  PRDAgent     │     │    │
│  │  │      │         │         │          │         │     │    │
│  │  │      └─────────┴─────────┴──────────┘         │     │    │
│  │  │                    │                          │     │    │
│  │  │            Claude API Client                  │     │    │
│  │  └────────────────────────────────────────────────┘     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    Data Layer                           │    │
│  │                                                          │    │
│  │  Models    Schemas    Database    Cache    Storage     │    │
│  │     │         │           │          │         │        │    │
│  └─────┼─────────┼───────────┼──────────┼─────────┼────────┘    │
│        │         │           │          │         │             │
│   PostgreSQL  Pydantic  SQLAlchemy  Redis     MinIO            │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### User Registration Flow

```
User → Frontend → POST /auth/register → Backend
                                          ├─> Validate input (Pydantic)
                                          ├─> Hash password (bcrypt)
                                          ├─> Create user (SQLAlchemy)
                                          ├─> Save to PostgreSQL
                                          └─> Return user data
```

### Project Creation & Execution Flow

```
User → Frontend → POST /projects → Backend
                                     ├─> Authenticate (JWT)
                                     ├─> Validate project data
                                     ├─> Create project record
                                     ├─> Save to PostgreSQL
                                     └─> Return project ID

User → Frontend → POST /projects/{id}/execute → Backend
                                                  ├─> Queue Celery task
                                                  └─> Return task ID

Celery Worker ─> Multi-Agent Orchestrator
                  ├─> IdeaAgent → Claude API
                  │   └─> Save result to DB
                  │
                  ├─> SRSAgent → Claude API
                  │   └─> Save document to MinIO
                  │
                  ├─> CodeAgent → Claude API
                  │   └─> Save code to MinIO
                  │
                  └─> Update project status
                      └─> Notify user (WebSocket)
```

### API Key Authentication Flow

```
Partner → API Request with X-API-Key header
           ├─> Extract API key
           ├─> Verify key in database
           ├─> Check rate limits (Redis)
           ├─> Track usage (Redis counter)
           ├─> Process request
           └─> Log usage to PostgreSQL
```

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│    Users    │◄───────┤   Projects   │────────►│  Documents  │
├─────────────┤         ├──────────────┤         ├─────────────┤
│ id          │         │ id           │         │ id          │
│ email       │         │ user_id  (FK)│         │ project_id  │
│ password    │         │ title        │         │ type        │
│ role        │         │ mode         │         │ content     │
│ is_active   │         │ status       │         │ file_url    │
└─────────────┘         │ progress     │         └─────────────┘
      │                 └──────────────┘
      │                        │
      │                        │
      │                 ┌──────▼──────┐
      │                 │ AgentTasks  │
      │                 ├─────────────┤
      │                 │ id          │
      │                 │ project_id  │
      │                 │ agent_type  │
      │                 │ status      │
      │                 │ tokens_used │
      │                 └─────────────┘
      │
      ├──────────────────────┐
      │                      │
┌─────▼─────┐         ┌──────▼──────┐
│  APIKeys  │         │Subscriptions│
├───────────┤         ├─────────────┤
│ id        │         │ id          │
│ user_id   │         │ user_id     │
│ key       │         │ plan_id     │
│ status    │         │ status      │
└───────────┘         │ start_date  │
      │               └─────────────┘
      │                      │
┌─────▼─────┐         ┌──────▼──────┐
│UsageLogs  │         │Transactions │
├───────────┤         ├─────────────┤
│ id        │         │ id          │
│ api_key_id│         │ subscription│
│ tokens    │         │ amount      │
│ timestamp │         │ status      │
└───────────┘         └─────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Security Layers                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Layer 1: Network Security                             │
│  ┌────────────────────────────────────────────┐        │
│  │ - HTTPS/TLS encryption                     │        │
│  │ - Firewall rules                           │        │
│  │ - DDoS protection (via CDN)                │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Layer 2: Application Security                         │
│  ┌────────────────────────────────────────────┐        │
│  │ - CORS configuration                       │        │
│  │ - Rate limiting (per IP/user)              │        │
│  │ - Input validation (Pydantic)              │        │
│  │ - SQL injection prevention (ORM)           │        │
│  │ - XSS protection (Next.js)                 │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Layer 3: Authentication & Authorization               │
│  ┌────────────────────────────────────────────┐        │
│  │ - JWT tokens (with expiry)                 │        │
│  │ - Password hashing (bcrypt)                │        │
│  │ - OAuth 2.0 (Google)                       │        │
│  │ - Role-based access control                │        │
│  │ - API key authentication                   │        │
│  └────────────────────────────────────────────┘        │
│                                                          │
│  Layer 4: Data Security                                │
│  ┌────────────────────────────────────────────┐        │
│  │ - Database encryption at rest              │        │
│  │ - Encrypted environment variables          │        │
│  │ - Secure secret management                 │        │
│  │ - Regular backups                          │        │
│  └────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

## Scalability Architecture

### Horizontal Scaling

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
    ┌────▼────┐         ┌────▼────┐        ┌────▼────┐
    │Backend-1│         │Backend-2│        │Backend-3│
    └────┬────┘         └────┬────┘        └────┬────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             │
                    ┌────────▼────────┐
                    │  Database Pool  │
                    └─────────────────┘
```

### Caching Strategy

```
Request → Check Redis Cache
           │
           ├─> Cache Hit → Return cached data
           │
           └─> Cache Miss → Query Database
                            ├─> Store in Redis
                            └─> Return data

Cache Invalidation:
- TTL-based expiry
- Event-based invalidation
- Manual cache clearing
```

## Monitoring & Observability

```
┌──────────────────────────────────────────────────────┐
│              Monitoring Stack                        │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Application Logs                                    │
│  ├─> Structured logging                             │
│  ├─> Log aggregation                                │
│  └─> Error tracking                                 │
│                                                       │
│  Metrics                                             │
│  ├─> Request rate                                   │
│  ├─> Response time                                  │
│  ├─> Error rate                                     │
│  ├─> Token usage                                    │
│  └─> Database performance                           │
│                                                       │
│  Health Checks                                       │
│  ├─> /health endpoint                               │
│  ├─> Database connectivity                          │
│  ├─> Redis connectivity                             │
│  └─> External API status                            │
│                                                       │
│  Alerts                                              │
│  ├─> High error rate                                │
│  ├─> Slow response time                             │
│  ├─> Database connection issues                     │
│  └─> API rate limit reached                         │
└──────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Development Environment

```
Developer Machine
├─> Docker Compose
    ├─> PostgreSQL container
    ├─> Redis container
    ├─> MinIO container
    ├─> Backend container (hot reload)
    └─> Frontend container (hot reload)
```

### Production Environment (AWS ECS)

```
┌─────────────────────────────────────────────────────┐
│                    AWS Cloud                        │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐                                  │
│  │   Route 53   │ (DNS)                            │
│  └──────┬───────┘                                  │
│         │                                           │
│  ┌──────▼────────────┐                             │
│  │  CloudFront (CDN) │                             │
│  └──────┬────────────┘                             │
│         │                                           │
│  ┌──────▼─────────────┐                            │
│  │  Application       │                            │
│  │  Load Balancer     │                            │
│  └──────┬─────────────┘                            │
│         │                                           │
│  ┌──────▼─────────────────────┐                    │
│  │     ECS Cluster            │                    │
│  │  ┌────────────────────┐    │                    │
│  │  │  Backend Service   │    │                    │
│  │  │  (Auto-scaling)    │    │                    │
│  │  └────────────────────┘    │                    │
│  │  ┌────────────────────┐    │                    │
│  │  │  Celery Workers    │    │                    │
│  │  │  (Auto-scaling)    │    │                    │
│  │  └────────────────────┘    │                    │
│  └────────────────────────────┘                    │
│                                                      │
│  ┌────────────────┐  ┌─────────────┐               │
│  │ RDS PostgreSQL │  │ ElastiCache │               │
│  │   (Multi-AZ)   │  │   (Redis)   │               │
│  └────────────────┘  └─────────────┘               │
│                                                      │
│  ┌────────────────┐  ┌─────────────┐               │
│  │      S3        │  │ CloudWatch  │               │
│  │   (Storage)    │  │ (Monitoring)│               │
│  └────────────────┘  └─────────────┘               │
└──────────────────────────────────────────────────────┘
```

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 14 | React framework |
| | Tailwind CSS | Styling |
| | shadcn/ui | UI components |
| | TypeScript | Type safety |
| **Backend** | FastAPI | API framework |
| | Python 3.11+ | Language |
| | SQLAlchemy | ORM |
| | Pydantic | Validation |
| **Database** | PostgreSQL 15 | Primary database |
| | Alembic | Migrations |
| **Cache** | Redis 7 | Caching & sessions |
| **Queue** | Celery | Background tasks |
| **AI** | Claude 3.5 | AI models |
| **Storage** | MinIO/S3 | File storage |
| **Auth** | JWT | Authentication |
| | OAuth 2.0 | Social login |
| **DevOps** | Docker | Containerization |
| | Nginx | Reverse proxy |
| | GitHub Actions | CI/CD |

---

**Last Updated**: January 2025
**Version**: 1.0.0
