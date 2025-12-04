# BharatBuild AI - Complete Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Container Execution System](#container-execution-system)
4. [Ephemeral Storage System](#ephemeral-storage-system)
5. [API Reference](#api-reference)
6. [Security Implementation](#security-implementation)
7. [Scaling Guide](#scaling-guide)
8. [Deployment Guide](#deployment-guide)
9. [Cost Analysis](#cost-analysis)

---

## System Overview

BharatBuild AI is a production-grade code generation and execution platform designed for 1,00,000+ Indian students. It provides:

- **AI-powered code generation** using Claude 3.5
- **Isolated container execution** (like Bolt.new/Replit)
- **Ephemeral storage** for cost optimization
- **Real-time streaming** output via SSE
- **Multi-language support** (Node.js, Python, Java, Go, Rust)

### Key Design Principles

| Principle | Implementation |
|-----------|----------------|
| Cost Efficiency | Store in /tmp during generation, ZIP only when complete |
| Security | Per-project Docker isolation, command validation |
| Scalability | Stateless design, horizontal scaling ready |
| Performance | Local disk writes (<1ms), SSE streaming |
| Reliability | Auto-cleanup, health monitoring, auto-restart |

---

## Architecture

### High-Level Architecture

```
                                USER BROWSER
                                     |
                     +---------------+---------------+
                     |               |               |
                  Editor         Terminal        Preview
                 (Monaco)        (xterm.js)      (iframe)
                     |               |               |
                     +-------+-------+-------+-------+
                             |
                     useContainerExecution()
                             |
                             | HTTP/SSE
                             v
+----------------------------------------------------------------+
|                       FASTAPI BACKEND                           |
|                                                                 |
|  +------------------+  +------------------+  +----------------+ |
|  |   Jobs API       |  | Containers API   |  |  Preview API   | |
|  | /api/v1/jobs/    |  | /api/v1/containers| | /api/v1/preview| |
|  +--------+---------+  +--------+---------+  +-------+--------+ |
|           |                     |                    |          |
|           v                     v                    v          |
|  +------------------+  +------------------+  +----------------+ |
|  | JobStorageManager|  |ContainerManager  |  |  CORS Proxy    | |
|  | (Ephemeral /tmp) |  | (Docker Engine)  |  |                | |
|  +--------+---------+  +--------+---------+  +----------------+ |
|           |                     |                               |
+-----------|---------------------|--------------------------------+
            |                     |
            v                     v
    +---------------+     +------------------+
    |  /tmp/jobs/   |     |  Docker Engine   |
    |  <job_id>/    |     |                  |
    |  - plan.json  |     |  +------------+  |
    |  - src/       |     |  | Container  |  |
    |  - package.json     |  | /workspace |  |
    +---------------+     |  | Port: 3000 |  |
                          |  +------------+  |
                          +------------------+
```

### Component Overview

| Component | File | Purpose |
|-----------|------|---------|
| JobStorageManager | `backend/app/modules/storage/job_storage.py` | Ephemeral file storage in /tmp |
| ContainerManager | `backend/app/modules/execution/container_manager.py` | Docker container lifecycle |
| CommandValidator | `backend/app/modules/execution/command_validator.py` | Security command filtering |
| HealthMonitor | `backend/app/modules/execution/health_monitor.py` | Auto-restart crashed containers |
| ProjectExecutor | `backend/app/modules/execution/project_executor.py` | AI output to container bridge |
| Jobs API | `backend/app/api/v1/endpoints/jobs.py` | Job storage REST endpoints |
| Containers API | `backend/app/api/v1/endpoints/containers.py` | Container execution endpoints |
| Preview API | `backend/app/api/v1/endpoints/preview.py` | CORS proxy for iframe preview |

---

## Container Execution System

### How It Works

The container execution system provides isolated environments for running user code, similar to Bolt.new and Replit.

#### Lifecycle

```
1. User Creates Project
        |
        v
2. ContainerManager.create_container()
   - Allocate ports (10000-60000)
   - Create Docker container
   - Mount project directory to /workspace
   - Apply resource limits (512MB RAM, 0.5 CPU)
        |
        v
3. User Writes Code
   - Files written to /tmp/jobs/<job_id>/
   - ContainerManager.write_file() updates container volume
        |
        v
4. User Runs Commands
   - ContainerManager.execute_command()
   - Streams output via SSE
   - Example: "npm install && npm run dev"
        |
        v
5. Preview Available
   - Container port 3000 -> Host port 10001
   - Preview proxy: /api/v1/preview/{project_id}/
        |
        v
6. Auto-Cleanup (24 hours)
   - cleanup_loop() runs every 5 minutes
   - Deletes expired containers and files
```

### Container Configuration

```python
@dataclass
class ContainerConfig:
    # Resource limits
    memory_limit: str = "512m"      # Max memory
    cpu_limit: float = 0.5          # CPU cores (0.5 = half)
    disk_limit: str = "1g"          # Max disk space

    # Timeouts
    idle_timeout: int = 3600        # 1 hour idle = cleanup
    max_lifetime: int = 86400       # 24 hours max
    command_timeout: int = 300      # 5 minute command timeout

    # Network
    exposed_ports: [3000, 3001, 5000, 8000, 8080]

    # Security
    privileged: bool = False        # Never privileged
    cap_drop: ["ALL"]               # Drop all capabilities
    cap_add: ["CHOWN", "SETUID", "SETGID"]  # Minimal caps
```

### Supported Runtimes

| Project Type | Docker Image | Use Case |
|--------------|--------------|----------|
| node | node:20-alpine | React, Vue, Next.js, Express |
| python | python:3.11-slim | Django, Flask, FastAPI |
| java | eclipse-temurin:17-jdk | Spring Boot, Maven |
| go | golang:1.21-alpine | Go applications |
| rust | rust:1.75-alpine | Rust applications |
| ruby | ruby:3.2-alpine | Rails applications |
| php | php:8.2-cli-alpine | PHP applications |

### API Usage

#### Create Container
```bash
POST /api/v1/containers/{project_id}/create
Content-Type: application/json

{
  "project_type": "node",
  "config": {
    "memory_limit": "512m",
    "cpu_limit": 0.5
  }
}
```

#### Execute Command (SSE Streaming)
```bash
POST /api/v1/containers/{project_id}/exec
Content-Type: application/json

{
  "command": "npm install && npm run dev"
}

# Response (SSE):
data: {"type": "status", "data": "Executing: npm install && npm run dev"}
data: {"type": "stdout", "data": "added 847 packages in 30s"}
data: {"type": "stdout", "data": "Ready on http://localhost:3000"}
data: {"type": "exit", "data": 0, "success": true}
```

#### Write File
```bash
POST /api/v1/containers/{project_id}/files
Content-Type: application/json

{
  "path": "src/App.tsx",
  "content": "export default function App() { return <div>Hello</div> }"
}
```

#### Get Preview URL
```bash
GET /api/v1/containers/{project_id}/preview

# Response:
{
  "preview_url": "http://localhost:10001",
  "status": "running"
}
```

---

## Ephemeral Storage System

### Why Ephemeral Storage?

Traditional storage approaches are expensive at scale:

| Method | Speed | Cost per 1000 files | Good for Generation? |
|--------|-------|---------------------|----------------------|
| PostgreSQL | 50ms/file | High (DB load) | NO |
| S3 | 100ms/file | $0.5-1 per 1000 writes | NO |
| Local /tmp | <1ms/file | $0 | YES |

**For 1,00,000 students generating 50 files each:**
- S3: 5,000,000 writes/month = $500+/month
- /tmp: $0/month

### Storage Architecture

```
/tmp/jobs/
├── abc123/                    # Job directory
│   ├── .job_metadata.json     # Job metadata
│   ├── plan.json              # Generation plan
│   ├── package.json           # Generated file
│   ├── src/
│   │   ├── App.tsx            # Generated file
│   │   ├── components/
│   │   │   └── Header.tsx     # Generated file
│   │   └── styles.css         # Generated file
│   └── README.md              # Generated file
├── abc123.zip                 # ZIP created on completion
└── def456/                    # Another job
    └── ...
```

### Job Lifecycle

```
1. POST /api/v1/jobs/create
   - Creates /tmp/jobs/<job_id>/
   - Returns job_id
        |
        v
2. POST /api/v1/jobs/{job_id}/plan
   - Writer stores plan.json
        |
        v
3. POST /api/v1/jobs/{job_id}/files (multiple times)
   - Each file written to /tmp/jobs/<job_id>/<path>
   - INSTANT writes (<1ms each)
        |
        v
4. POST /api/v1/jobs/{job_id}/complete
   - Creates ZIP file
   - Status = "complete"
        |
        v
5. GET /api/v1/jobs/{job_id}/download
   - Returns ZIP file
        |
        v
6. AUTO-DELETE after 48 hours
   - cleanup_loop() deletes old jobs
   - Storage cost = $0
```

### API Reference

#### Create Job
```bash
POST /api/v1/jobs/create
{
  "project_name": "my-react-app",
  "job_id": "optional-custom-id"
}

# Response:
{
  "job_id": "abc123",
  "status": "generating",
  "download_url": null
}
```

#### Write File
```bash
POST /api/v1/jobs/{job_id}/files
{
  "path": "src/App.tsx",
  "content": "..."
}
```

#### Batch Write Files
```bash
POST /api/v1/jobs/{job_id}/files/batch
[
  {"path": "package.json", "content": "..."},
  {"path": "src/index.tsx", "content": "..."},
  {"path": "src/App.tsx", "content": "..."}
]
```

#### Complete Job
```bash
POST /api/v1/jobs/{job_id}/complete

# Response:
{
  "success": true,
  "status": "complete",
  "download_url": "/api/v1/jobs/abc123/download"
}
```

#### Download ZIP
```bash
GET /api/v1/jobs/{job_id}/download
# Returns: my-react-app.zip
```

---

## API Reference

### Authentication

All APIs require authentication via:
- `Authorization: Bearer <jwt_token>` header
- `X-User-ID: <user_id>` header (for development)

### Jobs API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/jobs/create` | POST | Create new generation job |
| `/api/v1/jobs/{job_id}` | GET | Get job status |
| `/api/v1/jobs/{job_id}/files` | POST | Write file to job |
| `/api/v1/jobs/{job_id}/files/batch` | POST | Write multiple files |
| `/api/v1/jobs/{job_id}/files` | GET | List all files |
| `/api/v1/jobs/{job_id}/files/{path}` | GET | Read specific file |
| `/api/v1/jobs/{job_id}/plan` | POST | Write generation plan |
| `/api/v1/jobs/{job_id}/complete` | POST | Mark job complete, create ZIP |
| `/api/v1/jobs/{job_id}/download` | GET | Download ZIP file |
| `/api/v1/jobs/{job_id}/fail` | POST | Mark job as failed |
| `/api/v1/jobs/{job_id}` | DELETE | Delete job |
| `/api/v1/jobs/admin/stats` | GET | Storage statistics |
| `/api/v1/jobs/admin/cleanup` | POST | Trigger manual cleanup |

### Containers API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/containers/{project_id}/create` | POST | Create container |
| `/api/v1/containers/{project_id}/exec` | POST | Execute command (SSE) |
| `/api/v1/containers/{project_id}/files` | POST | Write file |
| `/api/v1/containers/{project_id}/files` | GET | List files |
| `/api/v1/containers/{project_id}/files/{path}` | GET | Read file |
| `/api/v1/containers/{project_id}/preview` | GET | Get preview URL |
| `/api/v1/containers/{project_id}/stats` | GET | Resource usage |
| `/api/v1/containers/{project_id}` | DELETE | Delete container |

### Preview API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/preview/{project_id}/` | GET | Proxy to container (CORS-safe) |
| `/api/v1/preview/{project_id}/{path}` | GET | Proxy specific path |

---

## Security Implementation

### Command Validation

The `CommandValidator` prevents injection attacks with multiple layers:

#### Layer 1: Blocklist
```python
BLOCKED_COMMANDS = {
    "rm -rf /", "rm -rf /*", "sudo", "su ",
    "cat /etc/passwd", "docker", "kubectl",
    "mount", "chroot", "nc -l", "nmap"
}
```

#### Layer 2: Pattern Matching
```python
BLOCKED_PATTERNS = [
    r"rm\s+(-[rf]+\s+)*[/~]",      # rm with root paths
    r"curl.*\|\s*(ba)?sh",          # Pipe curl to shell
    r">\s*/dev/sd[a-z]",            # Write to disk devices
    r"\$\(.*\)",                    # Command substitution
    r"`.*`",                        # Backtick execution
]
```

#### Layer 3: Whitelist Mode
```python
ALLOWED_COMMANDS = {
    "npm": ["install", "run", "start", "build", "test"],
    "python": ["*"],
    "node": ["*"],
    "git": ["clone", "init", "add", "commit", "status"],
    ...
}
```

#### Layer 4: Path Traversal Prevention
```python
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",           # ../
    r"/etc/", r"/var/", r"/usr/", r"/root/",
    r"/proc/", r"/sys/", r"/dev/"
]
```

### Container Security

| Feature | Implementation |
|---------|----------------|
| Isolation | Each project in separate Docker container |
| Resource Limits | Memory: 512MB, CPU: 0.5 cores |
| Capabilities | Drop ALL, add only CHOWN, SETUID, SETGID |
| Privileged Mode | NEVER enabled |
| Network | Controlled, no host network |
| Auto-cleanup | 24 hour max lifetime |
| Path Traversal | Blocked at file write |

### Risk Levels

```python
class CommandRisk(Enum):
    SAFE = "safe"           # npm install, python main.py
    MODERATE = "moderate"   # curl, wget (network access)
    DANGEROUS = "dangerous" # rm -rf, sudo (blocked)
    BLOCKED = "blocked"     # Never allowed
```

---

## Scaling Guide

### Phase 1: Single Server (Current)
- **Users**: 100-500 concurrent
- **Cost**: $50-100/month
- **Stack**: Docker Compose on single VPS

### Phase 2: Managed Platform (Fly.io/Railway)
- **Users**: 1,000-50,000 concurrent
- **Cost**: $500-2,000/month
- **Stack**: Auto-scaling containers

### Phase 3: Kubernetes
- **Users**: 100,000+ concurrent
- **Cost**: $3,000-15,000/month
- **Stack**: EKS/GKE with auto-scaling

### Industry Comparison

| Platform | Technology | Scale |
|----------|------------|-------|
| Bolt.new | WebContainers + GCP VMs | 100k+ |
| Replit | Kubernetes + gVisor | 1M+ |
| CodeSandbox | Firecracker + K8s | 500k+ |
| BharatBuild | Docker → K8s + gVisor | 100k+ |

### Recommended Path

1. **Start**: Docker Compose (free, 500 users)
2. **Scale**: Fly.io at 1,000+ users ($200/month)
3. **Enterprise**: Kubernetes at 50,000+ ($3,000/month)
4. **Optimize**: Add WebContainers for frontend projects (40% savings)

---

## Deployment Guide

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Docker (all services)
docker-compose up -d
```

### Production Deployment

#### Docker Compose
```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### Fly.io
```bash
fly auth login
fly launch --name bharatbuild-backend
fly deploy
```

#### Kubernetes
```bash
kubectl apply -f k8s/
kubectl apply -f k8s/backend-hpa.yaml
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/bharatbuild

# Redis
REDIS_URL=redis://localhost:6379

# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Storage
JOBS_BASE_PATH=/tmp/jobs
JOB_EXPIRY_HOURS=48

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=bharatbuild-projects
```

---

## Cost Analysis

### Storage Cost Comparison

| Storage Method | 1,00,000 students x 50 files | Monthly Cost |
|----------------|------------------------------|--------------|
| S3 writes | 5,000,000 writes | $600 |
| /tmp + ZIP | 100,000 ZIPs | $12 |
| **Savings** | | **$588/month** |

### Infrastructure Cost by Scale

| Users | Docker | Fly.io | Kubernetes |
|-------|--------|--------|------------|
| 100 | $50 | $50 | N/A |
| 1,000 | N/A | $200 | $1,500 |
| 10,000 | N/A | $800 | $2,500 |
| 100,000 | N/A | $4,000 | $4,500 |

### Cost Per User at Scale

| Users | Cost/User/Month |
|-------|-----------------|
| 10,000 | $0.08 |
| 50,000 | $0.04 |
| 100,000 | $0.04 |

---

## File Structure

```
BharatBuild_AI/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/
│   │   │   ├── jobs.py          # Job storage API
│   │   │   ├── containers.py    # Container execution API
│   │   │   └── preview.py       # Preview proxy API
│   │   ├── modules/
│   │   │   ├── storage/
│   │   │   │   └── job_storage.py     # Ephemeral storage
│   │   │   ├── execution/
│   │   │   │   ├── container_manager.py  # Docker management
│   │   │   │   ├── command_validator.py  # Security
│   │   │   │   ├── health_monitor.py     # Auto-restart
│   │   │   │   └── project_executor.py   # AI bridge
│   │   │   └── agents/
│   │   │       ├── planner_agent.py
│   │   │       ├── writer_agent.py
│   │   │       └── fixer_agent.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   └── useContainerExecution.ts
│   │   └── lib/
│   │       └── api-client.ts
│   └── package.json
├── docker/
│   └── runtime/
│       └── Dockerfile           # Multi-runtime image
├── docs/
│   ├── COMPLETE_DOCUMENTATION.md  # This file
│   ├── SCALING_GUIDE.md
│   └── API_DOCUMENTATION.md
└── docker-compose.yml
```

---

## Quick Reference

### Common Operations

```bash
# Create job and write files
curl -X POST http://localhost:8000/api/v1/jobs/create \
  -H "Content-Type: application/json" \
  -d '{"project_name": "my-app"}'

# Execute in container
curl -X POST http://localhost:8000/api/v1/containers/abc123/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "npm run dev"}'

# Get preview
curl http://localhost:8000/api/v1/containers/abc123/preview

# Download ZIP
curl -O http://localhost:8000/api/v1/jobs/abc123/download
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Storage stats
curl http://localhost:8000/api/v1/jobs/admin/stats

# Container stats
curl http://localhost:8000/api/v1/containers/abc123/stats
```

---

## Support

- **Documentation**: `/docs/COMPLETE_DOCUMENTATION.md`
- **API Docs**: http://localhost:8000/docs (Swagger)
- **Issues**: GitHub Issues

---

**This is how Bolt.new, Replit, and CodeSandbox work - and now BharatBuild does too!**
