# BharatBuild AI - Complete API Reference

## Base URL

```
Development: http://localhost:8000/api/v1
Production:  https://api.bharatbuild.ai/api/v1
```

## Authentication

All API endpoints require authentication (except health check).

### Headers

```http
Authorization: Bearer <jwt_token>
X-User-ID: <user_id>  # For development/internal use
Content-Type: application/json
```

---

## Health Check

### GET /health

Check if the API is running.

```http
GET /health

Response 200:
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Jobs API

Manage ephemeral job storage for code generation.

### POST /jobs/create

Create a new generation job.

```http
POST /api/v1/jobs/create
Content-Type: application/json

{
  "project_name": "my-react-app",
  "job_id": "optional-custom-id"  // Optional
}

Response 200:
{
  "job_id": "abc123def456",
  "user_id": "user-001",
  "project_name": "my-react-app",
  "status": "generating",
  "files_count": 0,
  "total_size_mb": 0,
  "created_at": "2024-01-15T10:30:00Z",
  "zip_ready": false,
  "download_url": null
}
```

### GET /jobs/{job_id}

Get job status and metadata.

```http
GET /api/v1/jobs/abc123def456

Response 200:
{
  "job_id": "abc123def456",
  "user_id": "user-001",
  "project_name": "my-react-app",
  "status": "generating",  // "generating" | "complete" | "failed" | "expired"
  "files_count": 25,
  "total_size_mb": 1.5,
  "created_at": "2024-01-15T10:30:00Z",
  "zip_ready": true,
  "download_url": "/api/v1/jobs/abc123def456/download"
}

Response 404:
{
  "detail": "Job not found"
}
```

### POST /jobs/{job_id}/files

Write a single file to the job.

```http
POST /api/v1/jobs/abc123def456/files
Content-Type: application/json

{
  "path": "src/App.tsx",
  "content": "export default function App() {\n  return <div>Hello World</div>\n}"
}

Response 200:
{
  "success": true,
  "path": "src/App.tsx",
  "size": 67
}

Response 400:
{
  "detail": "Job is not in generating state"
}

Response 404:
{
  "detail": "Job not found"
}
```

### POST /jobs/{job_id}/files/batch

Write multiple files at once.

```http
POST /api/v1/jobs/abc123def456/files/batch
Content-Type: application/json

[
  {"path": "package.json", "content": "{\n  \"name\": \"my-app\"\n}"},
  {"path": "src/index.tsx", "content": "import App from './App'"},
  {"path": "src/App.tsx", "content": "export default function App() {}"},
  {"path": "src/styles.css", "content": "body { margin: 0; }"}
]

Response 200:
{
  "total": 4,
  "success": 4,
  "results": [
    {"path": "package.json", "success": true},
    {"path": "src/index.tsx", "success": true},
    {"path": "src/App.tsx", "success": true},
    {"path": "src/styles.css", "success": true}
  ]
}
```

### POST /jobs/{job_id}/plan

Write the generation plan.

```http
POST /api/v1/jobs/abc123def456/plan
Content-Type: application/json

{
  "tasks": [
    {
      "name": "Setup project structure",
      "files": ["package.json", "tsconfig.json", "vite.config.ts"]
    },
    {
      "name": "Create React components",
      "files": ["src/App.tsx", "src/main.tsx"]
    },
    {
      "name": "Add styling",
      "files": ["src/styles.css", "src/index.css"]
    }
  ],
  "metadata": {
    "framework": "react",
    "language": "typescript",
    "styling": "tailwind"
  }
}

Response 200:
{
  "success": true
}
```

### GET /jobs/{job_id}/files

List all files in the job.

```http
GET /api/v1/jobs/abc123def456/files

Response 200:
{
  "job_id": "abc123def456",
  "files": [
    {"path": "package.json", "name": "package.json", "size": 500, "modified": "2024-01-15T10:35:00Z"},
    {"path": "src/App.tsx", "name": "App.tsx", "size": 1200, "modified": "2024-01-15T10:36:00Z"},
    {"path": "src/components/Header.tsx", "name": "Header.tsx", "size": 800, "modified": "2024-01-15T10:37:00Z"}
  ],
  "count": 3
}
```

### GET /jobs/{job_id}/files/{file_path}

Read a specific file.

```http
GET /api/v1/jobs/abc123def456/files/src/App.tsx

Response 200:
{
  "path": "src/App.tsx",
  "content": "export default function App() {\n  return <div>Hello World</div>\n}"
}

Response 404:
{
  "detail": "File not found"
}
```

### POST /jobs/{job_id}/complete

Mark job as complete and create ZIP.

```http
POST /api/v1/jobs/abc123def456/complete

Response 200:
{
  "success": true,
  "status": "complete",
  "message": "ZIP creation started",
  "download_url": "/api/v1/jobs/abc123def456/download"
}
```

### GET /jobs/{job_id}/download

Download the project as ZIP.

```http
GET /api/v1/jobs/abc123def456/download

Response 200:
Content-Type: application/zip
Content-Disposition: attachment; filename="my-react-app.zip"
<binary zip data>

Response 404:
{
  "detail": "Job not found"
}

Response 500:
{
  "detail": "Failed to create ZIP"
}
```

### POST /jobs/{job_id}/fail

Mark job as failed.

```http
POST /api/v1/jobs/abc123def456/fail?error_message=Build%20failed

Response 200:
{
  "success": true,
  "status": "failed"
}
```

### DELETE /jobs/{job_id}

Delete a job and its files.

```http
DELETE /api/v1/jobs/abc123def456?keep_zip=false

Response 200:
{
  "success": true,
  "message": "Job abc123def456 deleted"
}
```

### GET /jobs/admin/stats

Get storage statistics (admin only).

```http
GET /api/v1/jobs/admin/stats

Response 200:
{
  "base_path": "/tmp/jobs",
  "job_count": 150,
  "file_count": 5400,
  "total_size_mb": 125.5,
  "expiry_hours": 48
}
```

### POST /jobs/admin/cleanup

Manually trigger cleanup (admin only).

```http
POST /api/v1/jobs/admin/cleanup

Response 200:
{
  "success": true,
  "cleaned_jobs": 12
}
```

---

## Containers API

Manage Docker containers for code execution.

### POST /containers/{project_id}/create

Create a new container for a project.

```http
POST /api/v1/containers/abc123/create
Content-Type: application/json

{
  "project_type": "node",  // "node" | "python" | "java" | "go" | "rust" | "ruby" | "php"
  "config": {
    "memory_limit": "512m",  // Optional, default "512m"
    "cpu_limit": 0.5,        // Optional, default 0.5
    "idle_timeout": 3600,    // Optional, default 3600
    "max_lifetime": 86400    // Optional, default 86400
  }
}

Response 200:
{
  "container_id": "d4e5f6g7h8i9j0k1",
  "project_id": "abc123",
  "status": "running",
  "port_mappings": {
    "3000": 10001,
    "8000": 10002,
    "5000": 10003
  },
  "preview_urls": {
    "3000": "http://localhost:10001",
    "8000": "http://localhost:10002"
  },
  "created_at": "2024-01-15T10:30:00Z"
}

Response 500:
{
  "detail": "Container creation failed: Docker not available"
}
```

### POST /containers/{project_id}/exec

Execute a command (streaming SSE response).

```http
POST /api/v1/containers/abc123/exec
Content-Type: application/json

{
  "command": "npm install && npm run dev",
  "timeout": 300  // Optional, default 300
}

Response 200 (Server-Sent Events):
Content-Type: text/event-stream

data: {"type": "status", "data": "Executing: npm install && npm run dev"}

data: {"type": "stdout", "data": "npm WARN deprecated rimraf@2.7.1"}

data: {"type": "stdout", "data": "added 847 packages in 30s"}

data: {"type": "stdout", "data": "Starting dev server..."}

data: {"type": "stdout", "data": "Ready on http://localhost:3000"}

data: {"type": "exit", "data": 0, "success": true}
```

**Event Types:**
| Type | Description |
|------|-------------|
| `status` | Command status updates |
| `stdout` | Standard output |
| `stderr` | Standard error |
| `error` | Execution error |
| `exit` | Command completed with exit code |

### POST /containers/{project_id}/files

Write a file to the container.

```http
POST /api/v1/containers/abc123/files
Content-Type: application/json

{
  "path": "src/App.tsx",
  "content": "export default function App() { return <div>Hello</div> }"
}

Response 200:
{
  "success": true,
  "path": "src/App.tsx"
}

Response 400:
{
  "detail": "Invalid file path: path traversal detected"
}
```

### POST /containers/{project_id}/files/batch

Write multiple files at once.

```http
POST /api/v1/containers/abc123/files/batch
Content-Type: application/json

[
  {"path": "package.json", "content": "..."},
  {"path": "src/App.tsx", "content": "..."},
  {"path": "src/styles.css", "content": "..."}
]

Response 200:
{
  "success": true,
  "files_written": 3
}
```

### GET /containers/{project_id}/files

List files in the container.

```http
GET /api/v1/containers/abc123/files?path=src

Response 200:
{
  "files": [
    {"name": "App.tsx", "path": "src/App.tsx", "type": "file", "size": 1234},
    {"name": "components", "path": "src/components", "type": "directory", "size": 0},
    {"name": "styles.css", "path": "src/styles.css", "type": "file", "size": 567}
  ]
}
```

### GET /containers/{project_id}/files/{file_path}

Read a file from the container.

```http
GET /api/v1/containers/abc123/files/src/App.tsx

Response 200:
{
  "path": "src/App.tsx",
  "content": "export default function App() { ... }"
}
```

### GET /containers/{project_id}/preview

Get the preview URL.

```http
GET /api/v1/containers/abc123/preview?port=3000

Response 200:
{
  "preview_url": "http://localhost:10001",
  "status": "running"
}

Response 404:
{
  "detail": "Container not found"
}
```

### GET /containers/{project_id}/stats

Get container resource usage.

```http
GET /api/v1/containers/abc123/stats

Response 200:
{
  "cpu_percent": 12.5,
  "memory_usage_mb": 256.5,
  "memory_limit_mb": 512,
  "memory_percent": 50.1,
  "status": "running",
  "uptime_seconds": 3600
}
```

### DELETE /containers/{project_id}

Delete the container.

```http
DELETE /api/v1/containers/abc123?delete_files=false

Response 200:
{
  "success": true,
  "message": "Container deleted"
}
```

---

## Preview API

CORS-safe proxy for iframe preview.

### GET /preview/{project_id}/

Proxy the root of the container's dev server.

```http
GET /api/v1/preview/abc123/

Response 200:
Content-Type: text/html
<html>...</html>
```

### GET /preview/{project_id}/{path}

Proxy a specific path.

```http
GET /api/v1/preview/abc123/assets/style.css

Response 200:
Content-Type: text/css
body { margin: 0; }
```

**Usage in iframe:**
```html
<iframe src="http://localhost:8000/api/v1/preview/abc123/" />
```

---

## Orchestrator API

AI agent orchestration for code generation.

### POST /orchestrator/generate

Start project generation.

```http
POST /api/v1/orchestrator/generate
Content-Type: application/json

{
  "prompt": "Create a React todo app with TypeScript and Tailwind CSS",
  "project_type": "react",
  "options": {
    "language": "typescript",
    "styling": "tailwind",
    "testing": true
  }
}

Response 200 (SSE):
data: {"type": "plan", "data": {"tasks": [...]}}
data: {"type": "file", "data": {"path": "package.json", "content": "..."}}
data: {"type": "file", "data": {"path": "src/App.tsx", "content": "..."}}
data: {"type": "status", "data": "Running npm install..."}
data: {"type": "complete", "data": {"job_id": "abc123", "files_count": 15}}
```

### POST /orchestrator/fix

Fix errors in generated code.

```http
POST /api/v1/orchestrator/fix
Content-Type: application/json

{
  "job_id": "abc123",
  "errors": [
    {"file": "src/App.tsx", "line": 15, "message": "Type 'string' is not assignable to 'number'"}
  ]
}

Response 200 (SSE):
data: {"type": "fixing", "data": "src/App.tsx"}
data: {"type": "file", "data": {"path": "src/App.tsx", "content": "..."}}
data: {"type": "complete", "data": {"fixed_files": 1}}
```

---

## Projects API

User project management.

### GET /projects

List user's projects.

```http
GET /api/v1/projects?page=1&limit=20

Response 200:
{
  "projects": [
    {
      "id": "proj-001",
      "name": "My Todo App",
      "type": "react",
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T12:30:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "pages": 1
}
```

### POST /projects

Create a new project.

```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "My Todo App",
  "type": "react",
  "description": "A simple todo application"
}

Response 201:
{
  "id": "proj-001",
  "name": "My Todo App",
  "type": "react",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### GET /projects/{project_id}

Get project details.

```http
GET /api/v1/projects/proj-001

Response 200:
{
  "id": "proj-001",
  "name": "My Todo App",
  "type": "react",
  "description": "A simple todo application",
  "status": "active",
  "container_id": "abc123",
  "files": [
    {"path": "package.json", "size": 500},
    {"path": "src/App.tsx", "size": 1200}
  ],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:30:00Z"
}
```

### DELETE /projects/{project_id}

Delete a project.

```http
DELETE /api/v1/projects/proj-001

Response 200:
{
  "success": true,
  "message": "Project deleted"
}
```

---

## Error Responses

All endpoints may return these error formats:

### 400 Bad Request

```json
{
  "detail": "Invalid request body"
}
```

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden

```json
{
  "detail": "Not authorized to access this resource"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "project_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /jobs/create | 10/minute |
| POST /jobs/{id}/files | 100/minute |
| POST /containers/{id}/exec | 30/minute |
| GET endpoints | 300/minute |

Rate limit headers:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705315200
```

---

## Webhooks

Configure webhooks to receive events:

### Job Events

```json
{
  "event": "job.complete",
  "data": {
    "job_id": "abc123",
    "project_name": "my-app",
    "files_count": 25,
    "download_url": "/api/v1/jobs/abc123/download"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Container Events

```json
{
  "event": "container.exit",
  "data": {
    "project_id": "abc123",
    "exit_code": 0,
    "command": "npm run build"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## SDKs

### JavaScript/TypeScript

```typescript
import { BharatBuildClient } from '@bharatbuild/sdk';

const client = new BharatBuildClient({
  apiKey: 'your-api-key',
  baseUrl: 'https://api.bharatbuild.ai'
});

// Create job
const job = await client.jobs.create({ projectName: 'my-app' });

// Write files
await client.jobs.writeFile(job.jobId, 'src/App.tsx', code);

// Execute command
const output = await client.containers.exec(projectId, 'npm run dev');
```

### Python

```python
from bharatbuild import BharatBuildClient

client = BharatBuildClient(
    api_key="your-api-key",
    base_url="https://api.bharatbuild.ai"
)

# Create job
job = client.jobs.create(project_name="my-app")

# Write files
client.jobs.write_file(job.job_id, "src/App.tsx", code)

# Execute command
async for event in client.containers.exec(project_id, "npm run dev"):
    print(event)
```

---

## OpenAPI Specification

Full OpenAPI/Swagger documentation available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json
