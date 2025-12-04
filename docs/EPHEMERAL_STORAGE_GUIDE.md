# Ephemeral Storage Guide

## Overview

BharatBuild uses ephemeral storage to achieve **ZERO cloud storage cost** during code generation. Files are stored in `/tmp/jobs/` during generation and only zipped when complete.

This is the **production best practice** used by platforms serving millions of users.

## Why Ephemeral Storage?

### The Problem with Traditional Storage

```
Traditional Approach:
User writes file → Save to S3 → 100ms latency + $0.005/1000 writes

For 1,00,000 students x 50 files:
= 5,000,000 S3 PUT requests/month
= $25 just for writes
= $500+ with storage, transfer, etc.
```

### The BharatBuild Solution

```
Ephemeral Approach:
User writes file → Save to /tmp → <1ms latency + $0 cost

For 1,00,000 students:
= $0/month during generation
= Only pay for final ZIP downloads
```

## Architecture

```
                     AI AGENT (Planner/Writer/Fixer)
                                  |
                     POST /api/v1/jobs/{job_id}/files
                                  |
                                  v
+----------------------------------------------------------------+
|                      JobStorageManager                          |
|                                                                |
|  create_job()      → mkdir /tmp/jobs/<job_id>/                  |
|  write_file()      → write to /tmp/jobs/<job_id>/<path>        |
|  write_plan()      → write /tmp/jobs/<job_id>/plan.json        |
|  create_zip()      → zip -r /tmp/jobs/<job_id>.zip             |
|  cleanup_expired() → rm -rf jobs older than 48 hours           |
+----------------------------------------------------------------+
                                  |
                                  v
+----------------------------------------------------------------+
|                        FILE SYSTEM                              |
|                                                                |
|  /tmp/jobs/                                                     |
|  ├── abc123/                     # Job directory                |
|  │   ├── .job_metadata.json      # Job tracking                |
|  │   ├── plan.json               # Generation plan             |
|  │   ├── package.json            # Generated file              |
|  │   ├── src/                                                   |
|  │   │   ├── App.tsx             # Generated file              |
|  │   │   └── styles.css          # Generated file              |
|  │   └── README.md               # Generated file              |
|  │                                                              |
|  ├── abc123.zip                  # Created on complete          |
|  │                                                              |
|  └── def456/                     # Another job                  |
|      └── ...                                                    |
+----------------------------------------------------------------+
```

## Job Lifecycle

### Phase 1: Job Creation

```python
# POST /api/v1/jobs/create
{
  "project_name": "my-react-app"
}

# Response
{
  "job_id": "abc123",
  "status": "generating",
  "files_count": 0,
  "download_url": null
}
```

**What happens:**
1. Generate unique job_id
2. Create directory: `/tmp/jobs/abc123/`
3. Create metadata file: `/tmp/jobs/abc123/.job_metadata.json`
4. Track job in memory

### Phase 2: Plan Generation

```python
# POST /api/v1/jobs/abc123/plan
{
  "tasks": [
    {"name": "Setup project", "files": ["package.json", "tsconfig.json"]},
    {"name": "Create components", "files": ["src/App.tsx", "src/index.tsx"]},
    {"name": "Add styling", "files": ["src/styles.css"]}
  ]
}
```

**What happens:**
1. Write `/tmp/jobs/abc123/plan.json`
2. Plan is used by Writer Agent to know what to generate

### Phase 3: File Generation

```python
# POST /api/v1/jobs/abc123/files (called multiple times)
{
  "path": "package.json",
  "content": "{\n  \"name\": \"my-app\",\n  ..."
}

# Or batch write
# POST /api/v1/jobs/abc123/files/batch
[
  {"path": "src/App.tsx", "content": "..."},
  {"path": "src/index.tsx", "content": "..."},
  {"path": "src/styles.css", "content": "..."}
]
```

**What happens:**
1. Validate path (no traversal)
2. Create parent directories
3. Write file to `/tmp/jobs/abc123/<path>`
4. Update file count in metadata

**Performance:**
- Each write: <1ms
- 50 files: ~50ms total
- No network latency
- No cloud API calls

### Phase 4: Job Completion

```python
# POST /api/v1/jobs/abc123/complete

# Response
{
  "success": true,
  "status": "complete",
  "download_url": "/api/v1/jobs/abc123/download"
}
```

**What happens:**
1. Update status to "complete"
2. Create ZIP: `/tmp/jobs/abc123.zip`
3. ZIP contains all generated files
4. Download URL becomes available

### Phase 5: Download

```python
# GET /api/v1/jobs/abc123/download

# Response: ZIP file download
# Content-Disposition: attachment; filename="my-react-app.zip"
```

### Phase 6: Auto-Cleanup (48 hours)

```python
# Background task runs every hour
cleaned = await storage.cleanup_expired_jobs()

# Jobs older than 48 hours are deleted:
# - /tmp/jobs/abc123/ (directory)
# - /tmp/jobs/abc123.zip (zip file)
```

## API Reference

### Create Job

```http
POST /api/v1/jobs/create
Content-Type: application/json

{
  "project_name": "my-react-app",
  "job_id": "optional-custom-id"
}

Response:
{
  "job_id": "abc123",
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

### Get Job Status

```http
GET /api/v1/jobs/{job_id}

Response:
{
  "job_id": "abc123",
  "status": "generating",  // "generating", "complete", "failed", "expired"
  "files_count": 15,
  "total_size_mb": 0.5,
  "zip_ready": false,
  "download_url": null
}
```

### Write File

```http
POST /api/v1/jobs/{job_id}/files
Content-Type: application/json

{
  "path": "src/App.tsx",
  "content": "export default function App() { ... }"
}

Response:
{
  "success": true,
  "path": "src/App.tsx",
  "size": 1234
}
```

### Write Multiple Files (Batch)

```http
POST /api/v1/jobs/{job_id}/files/batch
Content-Type: application/json

[
  {"path": "package.json", "content": "..."},
  {"path": "src/index.tsx", "content": "..."},
  {"path": "src/App.tsx", "content": "..."}
]

Response:
{
  "total": 3,
  "success": 3,
  "results": [
    {"path": "package.json", "success": true},
    {"path": "src/index.tsx", "success": true},
    {"path": "src/App.tsx", "success": true}
  ]
}
```

### Write Generation Plan

```http
POST /api/v1/jobs/{job_id}/plan
Content-Type: application/json

{
  "tasks": [
    {"name": "Setup", "files": ["package.json"]},
    {"name": "Components", "files": ["src/App.tsx"]}
  ],
  "metadata": {
    "framework": "react",
    "language": "typescript"
  }
}

Response:
{
  "success": true
}
```

### List Files

```http
GET /api/v1/jobs/{job_id}/files

Response:
{
  "job_id": "abc123",
  "files": [
    {"path": "package.json", "name": "package.json", "size": 500, "modified": "..."},
    {"path": "src/App.tsx", "name": "App.tsx", "size": 1200, "modified": "..."},
    {"path": "src/styles.css", "name": "styles.css", "size": 800, "modified": "..."}
  ],
  "count": 3
}
```

### Read File

```http
GET /api/v1/jobs/{job_id}/files/src/App.tsx

Response:
{
  "path": "src/App.tsx",
  "content": "export default function App() { ... }"
}
```

### Mark Job Complete

```http
POST /api/v1/jobs/{job_id}/complete

Response:
{
  "success": true,
  "status": "complete",
  "message": "ZIP creation started",
  "download_url": "/api/v1/jobs/abc123/download"
}
```

### Download ZIP

```http
GET /api/v1/jobs/{job_id}/download

Response: Binary ZIP file
Content-Type: application/zip
Content-Disposition: attachment; filename="my-react-app.zip"
```

### Mark Job Failed

```http
POST /api/v1/jobs/{job_id}/fail?error_message=Generation%20failed

Response:
{
  "success": true,
  "status": "failed"
}
```

### Delete Job

```http
DELETE /api/v1/jobs/{job_id}?keep_zip=false

Response:
{
  "success": true,
  "message": "Job abc123 deleted"
}
```

### Get Storage Stats (Admin)

```http
GET /api/v1/jobs/admin/stats

Response:
{
  "base_path": "/tmp/jobs",
  "job_count": 150,
  "file_count": 5400,
  "total_size_mb": 125.5,
  "expiry_hours": 48
}
```

### Trigger Cleanup (Admin)

```http
POST /api/v1/jobs/admin/cleanup

Response:
{
  "success": true,
  "cleaned_jobs": 12
}
```

## Configuration

### Environment Variables

```bash
# Base path for job storage
JOBS_BASE_PATH=/tmp/jobs

# Hours before auto-deletion
JOB_EXPIRY_HOURS=48

# Max file size in MB
MAX_FILE_SIZE_MB=10

# Max project size in MB
MAX_PROJECT_SIZE_MB=100
```

### JobMetadata Structure

```python
@dataclass
class JobMetadata:
    job_id: str                    # Unique identifier
    user_id: str                   # Owner
    project_name: str              # Display name
    created_at: datetime           # Creation time
    status: str                    # "generating", "complete", "failed"
    files_count: int = 0           # Number of files
    total_size_bytes: int = 0      # Total size
    zip_path: Optional[str] = None # Path to ZIP when complete
    s3_url: Optional[str] = None   # Optional S3 URL
    error_message: Optional[str]   # Error if failed
```

## Integration with AI Agents

### Planner Agent

```python
# Planner creates the plan
plan = {
    "tasks": [
        {
            "name": "Setup project structure",
            "files": ["package.json", "tsconfig.json", "vite.config.ts"]
        },
        {
            "name": "Create React components",
            "files": ["src/App.tsx", "src/main.tsx", "src/components/Header.tsx"]
        }
    ]
}

await storage.write_plan(job_id, plan)
```

### Writer Agent

```python
# Writer generates files based on plan
for task in plan["tasks"]:
    for file_path in task["files"]:
        content = await generate_file_content(file_path)
        await storage.write_file(job_id, file_path, content)
```

### Fixer Agent

```python
# Fixer updates broken files
errors = await run_build(job_id)
for error in errors:
    fixed_content = await fix_file(error.file_path, error.message)
    await storage.write_file(job_id, error.file_path, fixed_content)
```

## Cost Analysis

### Traditional S3 Storage

```
100,000 students/month
x 50 files each
x 3 generations per student
= 15,000,000 PUT requests

S3 PUT: $0.005 per 1000 requests
= $75/month just for writes

+ Storage: ~$23/month for 1TB
+ Transfer: ~$90/month for 1TB out

Total: ~$200/month minimum
```

### Ephemeral /tmp Storage

```
100,000 students/month
x 1 ZIP download each
= 100,000 downloads

Bandwidth: Included in server cost
Storage: $0 (auto-deleted after 48h)

Total: $0 additional
```

### Savings: $200+/month

## Best Practices

### 1. Use Batch Writes

```python
# Good - single call
files = [
    {"path": "package.json", "content": "..."},
    {"path": "src/App.tsx", "content": "..."},
    {"path": "src/styles.css", "content": "..."},
]
await storage.write_files_batch(job_id, files)

# Bad - multiple calls
await storage.write_file(job_id, "package.json", "...")
await storage.write_file(job_id, "src/App.tsx", "...")
await storage.write_file(job_id, "src/styles.css", "...")
```

### 2. Validate Paths

```python
# The storage manager automatically validates:
# - No path traversal (../)
# - No absolute paths
# - No system directories

# This is BLOCKED:
await storage.write_file(job_id, "../../../etc/passwd", "hack")
# Raises: ValueError("Path traversal detected")
```

### 3. Handle Large Files

```python
# Files > 10MB are rejected
if len(content) > MAX_FILE_SIZE_MB * 1024 * 1024:
    raise ValueError(f"File too large (max {MAX_FILE_SIZE_MB}MB)")
```

### 4. Monitor Storage

```python
# Regular monitoring
stats = await storage.get_storage_stats()
print(f"Jobs: {stats['job_count']}")
print(f"Total size: {stats['total_size_mb']}MB")

# Alert if too much storage used
if stats['total_size_mb'] > 10000:  # 10GB
    await alert_admin("Storage usage high!")
```

### 5. Handle Failures

```python
try:
    await storage.write_file(job_id, path, content)
except ValueError as e:
    # Path traversal or size limit
    await storage.update_job_status(job_id, "failed", str(e))
except Exception as e:
    # Disk full or other error
    await storage.update_job_status(job_id, "failed", str(e))
```

## Optional: S3 Upload for Permanent Storage

```python
# After ZIP creation, optionally upload to S3
s3_url = await storage.upload_to_s3(
    job_id=job_id,
    s3_client=boto3.client('s3'),
    bucket="bharatbuild-projects",
    prefix="projects"
)

# Returns: "s3://bharatbuild-projects/projects/abc123.zip"
```

**When to use S3:**
- Pro users who need permanent storage
- Backup before cleanup
- Analytics/compliance requirements

**When NOT to use S3:**
- Student projects (temporary by nature)
- Cost optimization
- Most use cases

## Troubleshooting

### Disk Full

```bash
# Check disk usage
df -h /tmp

# Manual cleanup
curl -X POST http://localhost:8000/api/v1/jobs/admin/cleanup

# Or reduce expiry time
JOB_EXPIRY_HOURS=24
```

### Job Not Found

```python
# Job might have been cleaned up
metadata = await storage.get_job(job_id)
if not metadata:
    # Job expired or deleted
    return {"error": "Job not found or expired"}
```

### ZIP Creation Failed

```python
# Check disk space and permissions
zip_path = await storage.create_zip(job_id)
if not zip_path:
    # Check logs for specific error
    logger.error(f"ZIP creation failed for {job_id}")
```

---

## Summary

Ephemeral storage provides:

1. **Zero Cost** - No S3 charges during generation
2. **Maximum Speed** - <1ms writes to local disk
3. **Auto-Cleanup** - 48 hour expiry, no manual management
4. **Scalability** - Works for 1,00,000+ students
5. **Simplicity** - Just files on disk, no complex systems

This is the **production best practice** used by Bolt.new, Replit, and CodeSandbox!
