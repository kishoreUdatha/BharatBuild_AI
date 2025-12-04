# Container Execution Guide

## Overview

BharatBuild uses Docker containers to provide isolated, secure execution environments for user projects - exactly like Bolt.new, Replit, and CodeSandbox.

## Architecture

```
                     USER'S BROWSER
                          |
           +--------------+--------------+
           |              |              |
        Editor        Terminal       Preview
       (Monaco)      (xterm.js)     (iframe)
           |              |              |
           +--------------+--------------+
                          |
                useContainerExecution()
                          |
                     HTTP / SSE
                          |
+--------------------------------------------------------+
|                    FASTAPI BACKEND                      |
|                                                        |
|  ContainerManager        CommandValidator              |
|  - create_container()    - validate()                  |
|  - execute_command()     - sanitize()                  |
|  - write_file()          - check_whitelist()           |
|  - cleanup_expired()                                   |
+--------------------------------------------------------+
                          |
                    Docker Socket
                          |
+--------------------------------------------------------+
|                    DOCKER ENGINE                        |
|                                                        |
|  +----------------+  +----------------+                |
|  | bb-project-abc |  | bb-project-def |                |
|  |                |  |                |                |
|  | /workspace/    |  | /workspace/    |                |
|  | - src/         |  | - app.py       |                |
|  | - package.json |  | - requirements |                |
|  |                |  |                |                |
|  | Port 3000      |  | Port 8000      |                |
|  | -> Host 10001  |  | -> Host 10002  |                |
|  +----------------+  +----------------+                |
+--------------------------------------------------------+
```

## Container Lifecycle

### 1. Container Creation

When a user starts working on a project, we create an isolated container:

```python
# Called when user opens project
container = await container_manager.create_container(
    project_id="abc123",
    user_id="user-001",
    project_type="node",  # or python, java, go, rust
    config=ContainerConfig(
        memory_limit="512m",
        cpu_limit=0.5,
        idle_timeout=3600,      # 1 hour
        max_lifetime=86400,     # 24 hours
    )
)

# Returns:
# {
#     "container_id": "d4e5f6...",
#     "port_mappings": {3000: 10001, 8000: 10002},
#     "status": "running"
# }
```

### 2. File Operations

Files are written directly to the mounted volume:

```python
# Write a file
await container_manager.write_file(
    project_id="abc123",
    file_path="src/App.tsx",
    content="export default function App() { ... }"
)

# Read a file
content = await container_manager.read_file(
    project_id="abc123",
    file_path="src/App.tsx"
)

# List files
files = await container_manager.list_files(
    project_id="abc123",
    path="src/"
)
```

### 3. Command Execution

Commands are executed inside the container with streaming output:

```python
async for event in container_manager.execute_command(
    project_id="abc123",
    command="npm install && npm run dev",
    timeout=300
):
    if event["type"] == "stdout":
        print(event["data"])  # Real-time output
    elif event["type"] == "exit":
        print(f"Exit code: {event['data']}")
```

**Output Events:**
```json
{"type": "status", "data": "Executing: npm install && npm run dev"}
{"type": "stdout", "data": "added 847 packages in 30s"}
{"type": "stdout", "data": "Starting dev server..."}
{"type": "stdout", "data": "Ready on http://localhost:3000"}
{"type": "exit", "data": 0, "success": true}
```

### 4. Preview URL

After the dev server starts, get the preview URL:

```python
url = await container_manager.get_preview_url(
    project_id="abc123",
    container_port=3000
)
# Returns: "http://localhost:10001"
```

### 5. Auto-Cleanup

Containers are automatically cleaned up:

```python
# Runs every 5 minutes in background
cleaned = await container_manager.cleanup_expired()

# A container is expired if:
# - Idle for > idle_timeout (default 1 hour)
# - Running for > max_lifetime (default 24 hours)
```

## Configuration Options

### ContainerConfig

```python
@dataclass
class ContainerConfig:
    # Resource limits
    memory_limit: str = "512m"      # "512m", "1g", "2g"
    cpu_limit: float = 0.5          # 0.5 = half a CPU core
    disk_limit: str = "1g"          # Max disk space

    # Timeouts
    idle_timeout: int = 3600        # Seconds until cleanup if idle
    max_lifetime: int = 86400       # Max seconds container can live
    command_timeout: int = 300      # Max seconds for single command

    # Network
    network_enabled: bool = True
    exposed_ports: List[int] = [3000, 3001, 5000, 8000, 8080]

    # Security
    read_only_root: bool = False
    privileged: bool = False        # NEVER set to True
    cap_drop: List[str] = ["ALL"]
    cap_add: List[str] = ["CHOWN", "SETUID", "SETGID"]
```

### Supported Runtime Images

| Project Type | Image | Pre-installed |
|--------------|-------|---------------|
| `node` | node:20-alpine | npm, yarn, pnpm |
| `python` | python:3.11-slim | pip, setuptools |
| `java` | eclipse-temurin:17-jdk | maven, gradle |
| `go` | golang:1.21-alpine | go modules |
| `rust` | rust:1.75-alpine | cargo, rustc |
| `ruby` | ruby:3.2-alpine | bundler, gem |
| `php` | php:8.2-cli-alpine | composer |
| `static` | nginx:alpine | nginx server |

## API Endpoints

### Create Container

```http
POST /api/v1/containers/{project_id}/create
Content-Type: application/json

{
  "project_type": "node",
  "config": {
    "memory_limit": "512m",
    "cpu_limit": 0.5
  }
}

Response:
{
  "container_id": "d4e5f6g7h8i9",
  "project_id": "abc123",
  "status": "running",
  "port_mappings": {
    "3000": 10001,
    "8000": 10002
  },
  "preview_urls": {
    "3000": "http://localhost:10001"
  },
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Execute Command (SSE)

```http
POST /api/v1/containers/{project_id}/exec
Content-Type: application/json

{
  "command": "npm install && npm run dev",
  "timeout": 300
}

Response (Server-Sent Events):
data: {"type": "status", "data": "Executing: npm install && npm run dev"}

data: {"type": "stdout", "data": "npm WARN deprecated..."}

data: {"type": "stdout", "data": "added 847 packages"}

data: {"type": "exit", "data": 0, "success": true}
```

### Write File

```http
POST /api/v1/containers/{project_id}/files
Content-Type: application/json

{
  "path": "src/App.tsx",
  "content": "export default function App() { return <div>Hello</div> }"
}

Response:
{
  "success": true,
  "path": "src/App.tsx"
}
```

### Write Multiple Files

```http
POST /api/v1/containers/{project_id}/files/batch
Content-Type: application/json

[
  {"path": "package.json", "content": "..."},
  {"path": "src/index.tsx", "content": "..."},
  {"path": "src/App.tsx", "content": "..."}
]

Response:
{
  "success": true,
  "files_written": 3
}
```

### List Files

```http
GET /api/v1/containers/{project_id}/files?path=src

Response:
{
  "files": [
    {"name": "App.tsx", "path": "src/App.tsx", "type": "file", "size": 1234},
    {"name": "components", "path": "src/components", "type": "directory", "size": 0}
  ]
}
```

### Read File

```http
GET /api/v1/containers/{project_id}/files/src/App.tsx

Response:
{
  "path": "src/App.tsx",
  "content": "export default function App() { ... }"
}
```

### Get Preview URL

```http
GET /api/v1/containers/{project_id}/preview?port=3000

Response:
{
  "preview_url": "http://localhost:10001",
  "status": "running"
}
```

### Get Container Stats

```http
GET /api/v1/containers/{project_id}/stats

Response:
{
  "cpu_percent": 12.5,
  "memory_usage_mb": 256.5,
  "memory_limit_mb": 512,
  "memory_percent": 50.1,
  "status": "running"
}
```

### Delete Container

```http
DELETE /api/v1/containers/{project_id}?delete_files=true

Response:
{
  "success": true,
  "message": "Container deleted"
}
```

## Frontend Integration

### React Hook

```typescript
import { useContainerExecution } from '@/hooks/useContainerExecution';

function ProjectEditor({ projectId }: { projectId: string }) {
  const {
    container,
    output,
    isExecuting,
    previewUrl,
    createContainer,
    executeCommand,
    writeFile,
    writeFiles,
    getPreviewUrl,
  } = useContainerExecution({
    projectId,
    projectType: 'node',
    onOutput: (event) => {
      // Handle real-time output
      terminal.write(event.data);
    },
    onError: (error) => {
      console.error('Execution error:', error);
    },
  });

  // Create container when component mounts
  useEffect(() => {
    createContainer();
  }, []);

  // Write files and run commands
  const handleRun = async () => {
    await writeFiles([
      { path: 'package.json', content: packageJson },
      { path: 'src/App.tsx', content: appCode },
    ]);

    await executeCommand('npm install');
    await executeCommand('npm run dev');

    const url = await getPreviewUrl(3000);
    console.log('Preview at:', url);
  };

  return (
    <div>
      <button onClick={handleRun} disabled={isExecuting}>
        Run Project
      </button>
      <iframe src={previewUrl} />
    </div>
  );
}
```

## Security

### Command Validation

All commands pass through `CommandValidator` before execution:

```python
validator = CommandValidator(strict_mode=True)
result = validator.validate("npm install && npm run dev")

if result.is_valid:
    # Safe to execute
    await container_manager.execute_command(project_id, result.sanitized_command)
else:
    # Blocked - show error
    print(f"Blocked: {result.error_message}")
```

### Blocked Commands

```python
BLOCKED = [
    "rm -rf /",           # System destruction
    "sudo", "su",         # Privilege escalation
    "docker", "kubectl",  # Container escape
    "cat /etc/passwd",    # System access
    "nc -l", "nmap",      # Network attacks
]
```

### Container Isolation

| Security Feature | Implementation |
|------------------|----------------|
| Process Isolation | Separate Docker container |
| Filesystem Isolation | Mounted volume only |
| Network Isolation | Container network |
| Resource Limits | cgroups (CPU, memory) |
| Capabilities | Dropped ALL, minimal add |
| No Privileged | Always false |

## Best Practices

### 1. Always Create Container First

```typescript
// Good
const container = await createContainer();
await writeFile('src/App.tsx', code);
await executeCommand('npm run dev');

// Bad - will fail
await writeFile('src/App.tsx', code);  // Container doesn't exist!
```

### 2. Handle Streaming Output

```typescript
// Process events as they come
await executeCommand('npm install', {
  onOutput: (event) => {
    switch (event.type) {
      case 'stdout':
        terminal.write(event.data);
        break;
      case 'stderr':
        terminal.write('\x1b[31m' + event.data + '\x1b[0m');
        break;
      case 'exit':
        if (event.success) {
          showSuccess('Command completed');
        } else {
          showError(`Exit code: ${event.data}`);
        }
        break;
    }
  },
});
```

### 3. Use Batch Writes for Multiple Files

```typescript
// Good - single request
await writeFiles([
  { path: 'package.json', content: '...' },
  { path: 'src/App.tsx', content: '...' },
  { path: 'src/styles.css', content: '...' },
]);

// Bad - multiple requests
await writeFile('package.json', '...');
await writeFile('src/App.tsx', '...');
await writeFile('src/styles.css', '...');
```

### 4. Clean Up When Done

```typescript
// Component unmount or user leaves
useEffect(() => {
  return () => {
    deleteContainer(projectId);
  };
}, [projectId]);
```

## Troubleshooting

### Container Won't Start

```bash
# Check Docker is running
docker ps

# Check image exists
docker images | grep bharatbuild/runtime

# Pull image if missing
docker pull node:20-alpine
```

### Command Timeout

```bash
# Increase timeout for long operations
POST /api/v1/containers/{project_id}/exec
{
  "command": "npm install",
  "timeout": 600  # 10 minutes
}
```

### Preview Not Working

```bash
# Check container is running
curl http://localhost:8000/api/v1/containers/{project_id}/stats

# Check port mapping
curl http://localhost:8000/api/v1/containers/{project_id}/preview

# Use CORS proxy
<iframe src="http://localhost:8000/api/v1/preview/{project_id}/" />
```

### Out of Memory

```bash
# Increase memory limit
{
  "config": {
    "memory_limit": "1g"  # Instead of 512m
  }
}
```

---

## Summary

The container execution system provides:

1. **Isolation** - Each project in separate Docker container
2. **Security** - Command validation, resource limits, no privileged
3. **Real-time Output** - SSE streaming for live terminal
4. **Auto-cleanup** - 24-hour ephemeral storage
5. **Multi-language** - Node, Python, Java, Go, Rust, Ruby, PHP

This is the same architecture used by Bolt.new, Replit, and CodeSandbox!
