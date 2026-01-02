"""
Docker Infrastructure Fixer Agent - Comprehensive Docker Issue Handler

Handles ALL Docker/Compose issues:

INFRASTRUCTURE ISSUES:
- Network pool overlaps ("Pool overlaps with other one on this address space")
- Port conflicts (EADDRINUSE)
- Stale containers/networks
- Disk space issues
- Docker daemon connectivity

DOCKERFILE ISSUES:
- Syntax errors
- Missing/invalid base images
- Common mistakes (wrong COPY paths, missing WORKDIR, etc.)

DOCKER-COMPOSE ISSUES:
- YAML syntax errors
- Invalid depends_on format
- Port mapping errors
- Network configuration issues
- Volume mount errors

RUNTIME ISSUES:
- Memory limit exceeded (OOM) - auto-adjusts limits
- Missing images - auto-pulls
- Permission denied on volumes

This agent runs:
1. PRE-FLIGHT: Before docker-compose up (proactive cleanup)
2. ON-ERROR: When docker-compose fails (reactive fixes)
3. VALIDATION: Validates Dockerfile and docker-compose.yml before execution
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re
import asyncio
import yaml

from app.core.logging_config import logger


class InfraErrorType(Enum):
    """Types of Docker infrastructure errors"""
    # Infrastructure
    NETWORK_POOL_OVERLAP = "network_pool_overlap"
    PORT_CONFLICT = "port_conflict"
    STALE_CONTAINER = "stale_container"
    STALE_NETWORK = "stale_network"
    VOLUME_PERMISSION = "volume_permission"
    IMAGE_NOT_FOUND = "image_not_found"
    DAEMON_NOT_RUNNING = "daemon_not_running"
    MEMORY_LIMIT = "memory_limit"
    DISK_SPACE = "disk_space"
    # Dockerfile
    DOCKERFILE_SYNTAX = "dockerfile_syntax"
    DOCKERFILE_BASE_IMAGE = "dockerfile_base_image"
    DOCKERFILE_COPY_ERROR = "dockerfile_copy_error"
    DOCKERFILE_WORKDIR = "dockerfile_workdir"
    # Docker Compose
    COMPOSE_SYNTAX = "compose_syntax"
    COMPOSE_DEPENDS_ON = "compose_depends_on"
    COMPOSE_PORT_MAPPING = "compose_port_mapping"
    COMPOSE_NETWORK = "compose_network"
    COMPOSE_VOLUME = "compose_volume"
    COMPOSE_SERVICE = "compose_service"
    # Unknown
    UNKNOWN = "unknown"


@dataclass
class InfraError:
    """Represents a Docker infrastructure error"""
    error_type: InfraErrorType
    message: str
    details: Optional[str] = None
    fix_command: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None
    is_fixable: bool = True


@dataclass
class FixResult:
    """Result of applying a fix"""
    success: bool
    message: str
    command_executed: Optional[str] = None
    output: Optional[str] = None
    file_modified: Optional[str] = None
    changes_made: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validating Dockerfile or docker-compose.yml"""
    valid: bool
    errors: List[InfraError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    auto_fixed: bool = False


# ============================================================================
# ERROR DETECTION PATTERNS
# ============================================================================

ERROR_PATTERNS: List[Tuple[str, InfraErrorType, str, Optional[str]]] = [
    # Network errors
    (r"Pool overlaps with other one on this address space",
     InfraErrorType.NETWORK_POOL_OVERLAP,
     "Docker network IP address pool exhausted",
     "docker network prune -f"),

    (r"network .+ was found but has incorrect label",
     InfraErrorType.STALE_NETWORK,
     "Stale Docker network with incorrect labels",
     "docker network prune -f"),

    # Port errors
    (r"address already in use|EADDRINUSE|port is already allocated|Bind for .+ failed",
     InfraErrorType.PORT_CONFLICT,
     "Port is already in use",
     None),

    # Container errors
    (r"Conflict\. The container name .+ is already in use",
     InfraErrorType.STALE_CONTAINER,
     "Container name conflict",
     None),

    # Daemon errors
    (r"Cannot connect to the Docker daemon|Is the docker daemon running|error during connect",
     InfraErrorType.DAEMON_NOT_RUNNING,
     "Docker daemon is not running",
     None),

    # Image errors
    (r"manifest for .+ not found|pull access denied|repository does not exist|ImageNotFound|image .+ not found",
     InfraErrorType.IMAGE_NOT_FOUND,
     "Docker image not found",
     None),

    # Disk errors
    (r"no space left on device|disk quota exceeded",
     InfraErrorType.DISK_SPACE,
     "Disk space exhausted",
     "docker system prune -af --volumes"),

    # Memory errors
    (r"OCI runtime create failed.*memory|MemoryError|out of memory|Killed|ENOMEM|heap out of memory|allocation failed",
     InfraErrorType.MEMORY_LIMIT,
     "Memory limit exceeded",
     None),

    # Permission errors
    (r"permission denied|EACCES|Operation not permitted",
     InfraErrorType.VOLUME_PERMISSION,
     "Permission denied",
     None),

    # Dockerfile errors
    (r"failed to solve.*dockerfile parse error|Dockerfile parse error|unknown instruction",
     InfraErrorType.DOCKERFILE_SYNTAX,
     "Dockerfile syntax error",
     None),

    (r"failed to solve.*pull.*manifest unknown|failed to resolve source metadata",
     InfraErrorType.DOCKERFILE_BASE_IMAGE,
     "Invalid base image in Dockerfile",
     None),

    (r"COPY failed|failed to compute cache key.*not found|file not found in build context",
     InfraErrorType.DOCKERFILE_COPY_ERROR,
     "COPY command failed - file not found",
     None),

    # Docker Compose errors
    (r"yaml:|YAML|error validating|mapping values are not allowed|could not find expected",
     InfraErrorType.COMPOSE_SYNTAX,
     "Docker Compose YAML syntax error",
     None),

    (r"depends_on.*must be a|depends_on.*should be|Invalid type for depends_on",
     InfraErrorType.COMPOSE_DEPENDS_ON,
     "Invalid depends_on format in docker-compose.yml",
     None),

    (r"invalid port|port.*invalid|Invalid port",
     InfraErrorType.COMPOSE_PORT_MAPPING,
     "Invalid port mapping in docker-compose.yml",
     None),

    (r"service .+ has neither|no such service|undefined service",
     InfraErrorType.COMPOSE_SERVICE,
     "Invalid service reference",
     None),
]

# Common Dockerfile fixes
DOCKERFILE_FIXES = {
    # Base image alternatives
    "node:latest": "node:20-alpine",
    "node:18": "node:18-alpine",
    "node:20": "node:20-alpine",
    "python:latest": "python:3.11-slim",
    "python:3": "python:3.11-slim",
    "openjdk:latest": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17": "eclipse-temurin:17-jdk-alpine",
    "openjdk:11": "eclipse-temurin:11-jdk-alpine",
    "java:latest": "eclipse-temurin:17-jdk-alpine",
    "maven:latest": "maven:3.9-eclipse-temurin-17-alpine",
    "gradle:latest": "gradle:8-jdk17-alpine",
}

# Common Dockerfile patterns to fix
DOCKERFILE_PATTERN_FIXES = [
    # Missing WORKDIR before COPY
    (r"^(COPY .+ \./?)\n(?!WORKDIR)", r"WORKDIR /app\n\1\n"),
    # npm install without package.json copy first
    (r"^(RUN npm install)\n(?!.*COPY.*package)", r"COPY package*.json ./\n\1\n"),
    # pip install without requirements copy
    (r"^(RUN pip install -r requirements\.txt)\n(?!.*COPY.*requirements)",
     r"COPY requirements.txt ./\n\1\n"),
]


class DockerInfraFixerAgent:
    """
    Comprehensive Docker Infrastructure Fixer Agent

    Handles all Docker/Compose issues with automatic detection and fixing.
    """

    def __init__(self):
        self.fix_history: Dict[str, List[FixResult]] = {}
        self.max_fixes_per_error = 3
        self.default_memory_limit = "512m"
        self.increased_memory_limit = "1g"
        self.max_memory_limit = "2g"

    # ========================================================================
    # ERROR DETECTION
    # ========================================================================

    def detect_error_type(self, error_message: str) -> InfraError:
        """Detect the type of infrastructure error from the error message."""
        for pattern, error_type, description, fix_command in ERROR_PATTERNS:
            if re.search(pattern, error_message, re.IGNORECASE):
                return InfraError(
                    error_type=error_type,
                    message=description,
                    details=error_message[:1000],
                    fix_command=fix_command,
                    is_fixable=self._is_error_fixable(error_type)
                )

        return InfraError(
            error_type=InfraErrorType.UNKNOWN,
            message="Unknown infrastructure error",
            details=error_message[:500],
            is_fixable=False
        )

    def _is_error_fixable(self, error_type: InfraErrorType) -> bool:
        """Check if an error type can be auto-fixed."""
        fixable_types = {
            InfraErrorType.NETWORK_POOL_OVERLAP,
            InfraErrorType.PORT_CONFLICT,
            InfraErrorType.STALE_CONTAINER,
            InfraErrorType.STALE_NETWORK,
            InfraErrorType.DISK_SPACE,
            InfraErrorType.IMAGE_NOT_FOUND,
            InfraErrorType.MEMORY_LIMIT,
            InfraErrorType.DOCKERFILE_SYNTAX,
            InfraErrorType.DOCKERFILE_BASE_IMAGE,
            InfraErrorType.DOCKERFILE_COPY_ERROR,
            InfraErrorType.COMPOSE_SYNTAX,
            InfraErrorType.COMPOSE_DEPENDS_ON,
            InfraErrorType.COMPOSE_PORT_MAPPING,
            InfraErrorType.VOLUME_PERMISSION,
        }
        return error_type in fixable_types

    # ========================================================================
    # PRE-FLIGHT CHECKS
    # ========================================================================

    async def preflight_check(
        self,
        project_id: str,
        sandbox_runner: callable,
        project_name: str = None,
        project_path: str = None
    ) -> List[FixResult]:
        """
        Run comprehensive pre-flight checks before docker-compose up.
        """
        fixes: List[FixResult] = []

        if not project_name:
            project_name = f"bharatbuild_{project_id[:8]}"

        logger.info(f"[DockerInfraFixer] Running pre-flight checks for {project_id}")

        # 1. Prune unused networks
        fix = await self._prune_networks(sandbox_runner)
        if fix and fix.success:
            fixes.append(fix)

        # 2. Remove stale containers
        fix = await self._cleanup_stale_containers(project_name, sandbox_runner)
        if fix:
            fixes.append(fix)

        # 3. Check Docker daemon
        fix = await self._check_docker_daemon(sandbox_runner)
        if fix and not fix.success:
            fixes.append(fix)

        # 4. Check disk space and prune if needed
        fix = await self._check_disk_space(sandbox_runner)
        if fix:
            fixes.append(fix)

        # 5. Validate and fix Dockerfile (if project_path provided)
        if project_path:
            dockerfile_fixes = await self._validate_and_fix_dockerfile(project_path, sandbox_runner)
            fixes.extend(dockerfile_fixes)

            # 6. Validate and fix docker-compose.yml
            compose_fixes = await self._validate_and_fix_compose(project_path, sandbox_runner)
            fixes.extend(compose_fixes)

        self.fix_history[project_id] = self.fix_history.get(project_id, []) + fixes
        return fixes

    # ========================================================================
    # ERROR FIXING
    # ========================================================================

    async def fix_error(
        self,
        error_message: str,
        project_id: str,
        sandbox_runner: callable,
        project_name: str = None,
        project_path: str = None
    ) -> FixResult:
        """
        Attempt to fix a Docker infrastructure error automatically.
        """
        if not project_name:
            project_name = f"bharatbuild_{project_id[:8]}"

        error = self.detect_error_type(error_message)
        logger.info(f"[DockerInfraFixer] Detected: {error.error_type.value} - {error.message}")

        if not error.is_fixable:
            return FixResult(
                success=False,
                message=f"Cannot auto-fix: {error.message}"
            )

        # Route to appropriate fix handler
        fix_handlers = {
            InfraErrorType.NETWORK_POOL_OVERLAP: self._fix_network_overlap,
            InfraErrorType.STALE_NETWORK: self._fix_network_overlap,
            InfraErrorType.PORT_CONFLICT: lambda sr: self._fix_port_conflict(error_message, sr),
            InfraErrorType.STALE_CONTAINER: lambda sr: self._fix_stale_container(error_message, sr),
            InfraErrorType.DISK_SPACE: self._fix_disk_space,
            InfraErrorType.IMAGE_NOT_FOUND: lambda sr: self._fix_missing_image(error_message, sr),
            InfraErrorType.MEMORY_LIMIT: lambda sr: self._fix_memory_limit(project_path, sr),
            InfraErrorType.DOCKERFILE_SYNTAX: lambda sr: self._fix_dockerfile_error(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_BASE_IMAGE: lambda sr: self._fix_dockerfile_base_image(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_COPY_ERROR: lambda sr: self._fix_dockerfile_copy(error_message, project_path, sr),
            InfraErrorType.COMPOSE_SYNTAX: lambda sr: self._fix_compose_syntax(project_path, sr),
            InfraErrorType.COMPOSE_DEPENDS_ON: lambda sr: self._fix_compose_depends_on(project_path, sr),
            InfraErrorType.COMPOSE_PORT_MAPPING: lambda sr: self._fix_compose_ports(error_message, project_path, sr),
            InfraErrorType.VOLUME_PERMISSION: lambda sr: self._fix_volume_permissions(error_message, project_path, sr),
        }

        handler = fix_handlers.get(error.error_type)
        if handler:
            return await handler(sandbox_runner)

        # Fallback: use predefined command if available
        if error.fix_command:
            try:
                exit_code, output = sandbox_runner(error.fix_command, None, 60)
                return FixResult(
                    success=exit_code == 0,
                    message=f"Executed: {error.fix_command}",
                    command_executed=error.fix_command,
                    output=output
                )
            except Exception as e:
                return FixResult(success=False, message=f"Fix failed: {e}")

        return FixResult(
            success=False,
            message=f"No fix available for: {error.error_type.value}"
        )

    # ========================================================================
    # INFRASTRUCTURE FIXES
    # ========================================================================

    async def _prune_networks(self, sandbox_runner: callable) -> Optional[FixResult]:
        """Prune unused Docker networks."""
        try:
            exit_code, output = sandbox_runner("docker network prune -f", None, 30)
            if exit_code == 0 and output:
                deleted = [l.strip() for l in output.split('\n') if l.strip() and not l.startswith('Deleted') and not l.startswith('Total')]
                if deleted:
                    return FixResult(
                        success=True,
                        message=f"Pruned {len(deleted)} unused networks",
                        command_executed="docker network prune -f",
                        output=output
                    )
            return None
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Network prune failed: {e}")
            return None

    async def _cleanup_stale_containers(self, project_name: str, sandbox_runner: callable) -> Optional[FixResult]:
        """Remove stale containers for this project."""
        try:
            exit_code, output = sandbox_runner(
                f"docker ps -a --filter 'name={project_name}' --format '{{{{.Names}}}}' | xargs -r docker rm -f",
                None, 30
            )
            if exit_code == 0 and output and output.strip():
                return FixResult(
                    success=True,
                    message=f"Removed stale containers: {output.strip()}",
                    command_executed=f"docker rm -f (project containers)"
                )
            return None
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Container cleanup failed: {e}")
            return None

    async def _check_docker_daemon(self, sandbox_runner: callable) -> Optional[FixResult]:
        """Check Docker daemon health."""
        try:
            exit_code, output = sandbox_runner("docker info --format '{{.ServerVersion}}'", None, 10)
            if exit_code != 0:
                return FixResult(
                    success=False,
                    message="Docker daemon not responding - manual intervention required"
                )
            return None
        except Exception as e:
            return FixResult(success=False, message=f"Docker check failed: {e}")

    async def _check_disk_space(self, sandbox_runner: callable) -> Optional[FixResult]:
        """Check disk space and prune if needed."""
        try:
            exit_code, output = sandbox_runner("df -h / | tail -1 | awk '{print $5}' | tr -d '%'", None, 10)
            if exit_code == 0 and output.strip().isdigit():
                usage = int(output.strip())
                if usage > 85:
                    prune_code, prune_output = sandbox_runner("docker system prune -f", None, 60)
                    return FixResult(
                        success=prune_code == 0,
                        message=f"Disk at {usage}%, pruned Docker resources",
                        command_executed="docker system prune -f",
                        output=prune_output
                    )
            return None
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Disk check failed: {e}")
            return None

    async def _fix_network_overlap(self, sandbox_runner: callable) -> FixResult:
        """Fix network pool overlap."""
        try:
            # First try normal prune
            exit_code, output = sandbox_runner("docker network prune -f", None, 30)

            if exit_code == 0:
                return FixResult(
                    success=True,
                    message="Pruned unused networks to free IP address space",
                    command_executed="docker network prune -f",
                    output=output
                )

            # More aggressive: remove all custom bridge networks
            exit_code, output = sandbox_runner(
                "docker network ls --filter 'driver=bridge' -q | xargs -r docker network rm 2>/dev/null || true",
                None, 60
            )
            return FixResult(
                success=True,
                message="Removed custom Docker networks",
                command_executed="docker network rm (all custom)",
                output=output
            )
        except Exception as e:
            return FixResult(success=False, message=f"Network fix failed: {e}")

    async def _fix_port_conflict(self, error_message: str, sandbox_runner: callable) -> FixResult:
        """Fix port conflict by killing processes and containers."""
        port_match = re.search(r':(\d+)|port[:\s]+(\d+)', error_message, re.IGNORECASE)
        if not port_match:
            return FixResult(success=False, message="Could not determine conflicting port")

        port = port_match.group(1) or port_match.group(2)

        try:
            # Kill process using port
            sandbox_runner(f"fuser -k {port}/tcp 2>/dev/null || true", None, 10)

            # Remove containers using port
            sandbox_runner(f"docker ps --filter 'publish={port}' -q | xargs -r docker rm -f", None, 30)

            return FixResult(
                success=True,
                message=f"Freed port {port}",
                command_executed=f"kill processes and containers on port {port}"
            )
        except Exception as e:
            return FixResult(success=False, message=f"Port fix failed: {e}")

    async def _fix_stale_container(self, error_message: str, sandbox_runner: callable) -> FixResult:
        """Fix stale container by removing it."""
        match = re.search(r'container name ["\']?([^"\']+)["\']? is already in use', error_message, re.IGNORECASE)
        if not match:
            match = re.search(r'Conflict.*["\'/]([a-zA-Z0-9_-]+)["\']', error_message)

        if not match:
            return FixResult(success=False, message="Could not determine container name")

        container = match.group(1)
        try:
            exit_code, output = sandbox_runner(f"docker rm -f {container}", None, 30)
            return FixResult(
                success=exit_code == 0,
                message=f"Removed stale container: {container}",
                command_executed=f"docker rm -f {container}"
            )
        except Exception as e:
            return FixResult(success=False, message=f"Container removal failed: {e}")

    async def _fix_disk_space(self, sandbox_runner: callable) -> FixResult:
        """Fix disk space by aggressive pruning."""
        try:
            exit_code, output = sandbox_runner("docker system prune -af --volumes", None, 120)
            return FixResult(
                success=exit_code == 0,
                message="Pruned Docker system (images, containers, volumes)",
                command_executed="docker system prune -af --volumes",
                output=output
            )
        except Exception as e:
            return FixResult(success=False, message=f"Disk cleanup failed: {e}")

    async def _fix_missing_image(self, error_message: str, sandbox_runner: callable) -> FixResult:
        """Auto-pull missing Docker image."""
        # Extract image name from error
        match = re.search(r'manifest for ([^\s]+) not found|pull access denied for ([^\s,]+)|repository ([^\s]+) not found',
                         error_message, re.IGNORECASE)
        if not match:
            return FixResult(success=False, message="Could not determine missing image name")

        image = match.group(1) or match.group(2) or match.group(3)

        # Check if we have an alternative
        alt_image = DOCKERFILE_FIXES.get(image)
        if alt_image:
            image = alt_image

        try:
            exit_code, output = sandbox_runner(f"docker pull {image}", None, 300)
            if exit_code == 0:
                return FixResult(
                    success=True,
                    message=f"Pulled image: {image}",
                    command_executed=f"docker pull {image}"
                )
            else:
                # Try without tag
                base_image = image.split(':')[0]
                exit_code, output = sandbox_runner(f"docker pull {base_image}:latest", None, 300)
                return FixResult(
                    success=exit_code == 0,
                    message=f"Pulled image: {base_image}:latest",
                    command_executed=f"docker pull {base_image}:latest"
                )
        except Exception as e:
            return FixResult(success=False, message=f"Image pull failed: {e}")

    async def _fix_memory_limit(self, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix OOM by increasing memory limits in docker-compose.yml."""
        if not project_path:
            return FixResult(success=False, message="Project path required for memory fix")

        compose_file = Path(project_path) / "docker-compose.yml"
        if not compose_file.exists():
            return FixResult(success=False, message="docker-compose.yml not found")

        try:
            content = compose_file.read_text()
            data = yaml.safe_load(content)

            modified = False
            for service_name, service in data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                # Add or update deploy.resources.limits.memory
                if 'deploy' not in service:
                    service['deploy'] = {}
                if 'resources' not in service['deploy']:
                    service['deploy']['resources'] = {}
                if 'limits' not in service['deploy']['resources']:
                    service['deploy']['resources']['limits'] = {}

                current_mem = service['deploy']['resources']['limits'].get('memory', self.default_memory_limit)

                # Increase memory limit
                if current_mem == self.default_memory_limit:
                    service['deploy']['resources']['limits']['memory'] = self.increased_memory_limit
                    modified = True
                elif current_mem == self.increased_memory_limit:
                    service['deploy']['resources']['limits']['memory'] = self.max_memory_limit
                    modified = True

                # Also add mem_limit for older compose versions
                if 'mem_limit' not in service:
                    service['mem_limit'] = service['deploy']['resources']['limits']['memory']
                    modified = True

            if modified:
                with open(compose_file, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

                return FixResult(
                    success=True,
                    message=f"Increased memory limits in docker-compose.yml",
                    file_modified=str(compose_file),
                    changes_made="Increased memory limits for services"
                )
            else:
                return FixResult(
                    success=False,
                    message="Memory already at maximum limit"
                )

        except Exception as e:
            return FixResult(success=False, message=f"Memory fix failed: {e}")

    async def _fix_volume_permissions(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix volume permission issues."""
        try:
            # Try to fix common permission issues
            if project_path:
                sandbox_runner(f"chmod -R 755 {project_path} 2>/dev/null || true", None, 30)

            # Also try to fix node_modules permissions
            sandbox_runner("chmod -R 755 node_modules 2>/dev/null || true", None, 30)

            return FixResult(
                success=True,
                message="Applied permission fixes",
                command_executed="chmod -R 755 on project directories"
            )
        except Exception as e:
            return FixResult(success=False, message=f"Permission fix failed: {e}")

    # ========================================================================
    # DOCKERFILE FIXES
    # ========================================================================

    async def _validate_and_fix_dockerfile(self, project_path: str, sandbox_runner: callable) -> List[FixResult]:
        """Validate and fix Dockerfile issues (works with remote sandbox)."""
        fixes = []

        # Check multiple possible Dockerfile locations
        dockerfile_paths = [
            f"{project_path}/Dockerfile",
            f"{project_path}/frontend/Dockerfile",
            f"{project_path}/backend/Dockerfile",
        ]

        for dockerfile_path in dockerfile_paths:
            if not self._file_exists_in_sandbox(dockerfile_path, sandbox_runner):
                continue

            try:
                content = self._read_file_from_sandbox(dockerfile_path, sandbox_runner)
                if not content:
                    continue

                fixed_content = content
                changes = []

                # Fix base images
                for old_image, new_image in DOCKERFILE_FIXES.items():
                    pattern = rf'^FROM\s+{re.escape(old_image)}\s*$'
                    if re.search(pattern, fixed_content, re.MULTILINE | re.IGNORECASE):
                        fixed_content = re.sub(pattern, f'FROM {new_image}', fixed_content, flags=re.MULTILINE | re.IGNORECASE)
                        changes.append(f"Changed base image: {old_image} -> {new_image}")

                # Fix missing WORKDIR
                if 'WORKDIR' not in fixed_content and ('COPY' in fixed_content or 'RUN' in fixed_content):
                    # Add WORKDIR /app after FROM
                    fixed_content = re.sub(
                        r'^(FROM .+)$',
                        r'\1\nWORKDIR /app',
                        fixed_content,
                        count=1,
                        flags=re.MULTILINE
                    )
                    changes.append("Added WORKDIR /app")

                # Fix common syntax issues
                # Remove duplicate blank lines
                fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)

                # Ensure file ends with newline
                if not fixed_content.endswith('\n'):
                    fixed_content += '\n'

                if changes and fixed_content != content:
                    if self._write_file_to_sandbox(dockerfile_path, fixed_content, sandbox_runner):
                        fixes.append(FixResult(
                            success=True,
                            message=f"Fixed Dockerfile: {dockerfile_path.split('/')[-1]}",
                            file_modified=dockerfile_path,
                            changes_made="; ".join(changes)
                        ))
                        logger.info(f"[DockerInfraFixer] Fixed Dockerfile: {changes}")

            except Exception as e:
                logger.warning(f"[DockerInfraFixer] Dockerfile fix failed for {dockerfile_path}: {e}")

        return fixes

    async def _fix_dockerfile_error(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix Dockerfile syntax error based on error message (works with remote sandbox)."""
        if not project_path:
            return FixResult(success=False, message="Project path required")

        # Find Dockerfile
        dockerfile_path = None
        for path in [f"{project_path}/Dockerfile", f"{project_path}/frontend/Dockerfile", f"{project_path}/backend/Dockerfile"]:
            if self._file_exists_in_sandbox(path, sandbox_runner):
                dockerfile_path = path
                break

        if not dockerfile_path:
            return FixResult(success=False, message="Dockerfile not found")

        try:
            content = self._read_file_from_sandbox(dockerfile_path, sandbox_runner)
            if not content:
                return FixResult(success=False, message="Could not read Dockerfile")

            fixed = content

            # Fix "unknown instruction" errors
            unknown_match = re.search(r'unknown instruction:\s*(\w+)', error_message, re.IGNORECASE)
            if unknown_match:
                bad_instruction = unknown_match.group(1)
                # Common typos
                typo_fixes = {
                    'RRUN': 'RUN', 'RUn': 'RUN', 'ruN': 'RUN',
                    'COPPY': 'COPY', 'COPy': 'COPY',
                    'EXPOST': 'EXPOSE', 'EXPOSe': 'EXPOSE',
                    'WORDIR': 'WORKDIR', 'WORKDI': 'WORKDIR',
                    'ENRTRYPOINT': 'ENTRYPOINT', 'ENTRYPOITN': 'ENTRYPOINT',
                    'COMD': 'CMD', 'CMd': 'CMD',
                }
                if bad_instruction in typo_fixes:
                    fixed = fixed.replace(bad_instruction, typo_fixes[bad_instruction])

            if fixed != content:
                if self._write_file_to_sandbox(dockerfile_path, fixed, sandbox_runner):
                    return FixResult(
                        success=True,
                        message="Fixed Dockerfile syntax error",
                        file_modified=dockerfile_path
                    )

            return FixResult(success=False, message="Could not auto-fix Dockerfile syntax")

        except Exception as e:
            return FixResult(success=False, message=f"Dockerfile fix failed: {e}")

    async def _fix_dockerfile_base_image(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix invalid base image in Dockerfile (works with remote sandbox)."""
        if not project_path:
            return FixResult(success=False, message="Project path required")

        # Extract the problematic image
        match = re.search(r'manifest for ([^\s]+) not found|pull.*([^\s]+).*not found', error_message, re.IGNORECASE)
        if not match:
            return FixResult(success=False, message="Could not determine problematic image")

        bad_image = match.group(1) or match.group(2)

        # Find Dockerfile
        for dockerfile_path in [f"{project_path}/Dockerfile", f"{project_path}/frontend/Dockerfile", f"{project_path}/backend/Dockerfile"]:
            if self._file_exists_in_sandbox(dockerfile_path, sandbox_runner):
                try:
                    content = self._read_file_from_sandbox(dockerfile_path, sandbox_runner)
                    if not content:
                        continue

                    # Check if this Dockerfile has the bad image
                    if bad_image in content:
                        alt_image = DOCKERFILE_FIXES.get(bad_image)
                        if not alt_image:
                            # Try to find a close match
                            base = bad_image.split(':')[0]
                            for old, new in DOCKERFILE_FIXES.items():
                                if base in old:
                                    alt_image = new
                                    break

                        if alt_image:
                            fixed = content.replace(bad_image, alt_image)
                            if self._write_file_to_sandbox(dockerfile_path, fixed, sandbox_runner):
                                return FixResult(
                                    success=True,
                                    message=f"Changed base image: {bad_image} -> {alt_image}",
                                    file_modified=dockerfile_path
                                )

                except Exception as e:
                    logger.warning(f"[DockerInfraFixer] Base image fix failed: {e}")

        return FixResult(success=False, message=f"Could not find alternative for image: {bad_image}")

    async def _fix_dockerfile_copy(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix COPY command errors in Dockerfile."""
        # Extract the missing file
        match = re.search(r'COPY.*"([^"]+)".*not found|failed to compute cache key.*"([^"]+)"', error_message)
        if not match:
            return FixResult(success=False, message="Could not determine missing file")

        missing_file = match.group(1) or match.group(2)

        # Common fixes
        if missing_file == "package.json":
            # Check if we're copying from wrong location
            return FixResult(
                success=False,
                message=f"Missing {missing_file} - ensure file exists in build context"
            )

        return FixResult(
            success=False,
            message=f"COPY failed for {missing_file} - check if file exists in build context"
        )

    # ========================================================================
    # DOCKER-COMPOSE FIXES
    # ========================================================================

    def _read_file_from_sandbox(self, file_path: str, sandbox_runner: callable) -> Optional[str]:
        """Read a file from the sandbox (works for both local and remote)."""
        try:
            # Try using sandbox_runner (for remote sandbox)
            exit_code, output = sandbox_runner(f'cat "{file_path}"', None, 30)
            if exit_code == 0 and output:
                return output
            return None
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Failed to read {file_path}: {e}")
            return None

    def _write_file_to_sandbox(self, file_path: str, content: str, sandbox_runner: callable) -> bool:
        """Write a file to the sandbox (works for both local and remote)."""
        try:
            # Escape content for shell - use base64 to avoid escaping issues
            import base64
            encoded = base64.b64encode(content.encode()).decode()
            cmd = f'echo "{encoded}" | base64 -d > "{file_path}"'
            exit_code, output = sandbox_runner(cmd, None, 30)
            return exit_code == 0
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Failed to write {file_path}: {e}")
            return False

    def _file_exists_in_sandbox(self, file_path: str, sandbox_runner: callable) -> bool:
        """Check if a file exists in the sandbox."""
        try:
            exit_code, output = sandbox_runner(f'test -f "{file_path}" && echo "EXISTS"', None, 10)
            return exit_code == 0 and "EXISTS" in output
        except Exception:
            return False

    async def _validate_and_fix_compose(self, project_path: str, sandbox_runner: callable) -> List[FixResult]:
        """Validate and fix docker-compose.yml issues (works with remote sandbox)."""
        fixes = []
        compose_file = f"{project_path}/docker-compose.yml"

        # Check if file exists using sandbox_runner
        if not self._file_exists_in_sandbox(compose_file, sandbox_runner):
            logger.info(f"[DockerInfraFixer] docker-compose.yml not found at {compose_file}")
            return fixes

        try:
            # Read file from sandbox
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                logger.warning(f"[DockerInfraFixer] Could not read docker-compose.yml")
                return fixes

            data = yaml.safe_load(content)
            modified = False
            changes = []

            if not isinstance(data, dict):
                return fixes

            # Fix depends_on format
            for service_name, service in data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                # Fix depends_on: convert dict to list
                if 'depends_on' in service:
                    depends = service['depends_on']
                    if isinstance(depends, dict):
                        # Convert {"db": {"condition": "service_healthy"}} to ["db"]
                        service['depends_on'] = list(depends.keys())
                        modified = True
                        changes.append(f"Fixed depends_on format for {service_name}")

                # Ensure ports are strings
                if 'ports' in service:
                    fixed_ports = []
                    for port in service['ports']:
                        if isinstance(port, int):
                            fixed_ports.append(str(port))
                            modified = True
                        else:
                            fixed_ports.append(port)
                    if modified:
                        service['ports'] = fixed_ports
                        changes.append(f"Fixed port format for {service_name}")

            # Remove top-level networks section to avoid pool overlap issues
            if 'networks' in data:
                # Check if using custom networks
                networks = data['networks']
                if isinstance(networks, dict):
                    # Remove the networks section - let Docker create default network
                    del data['networks']
                    modified = True
                    changes.append("Removed custom networks (prevents pool overlap)")

                    # Also remove network references from services
                    for service_name, service in data.get('services', {}).items():
                        if isinstance(service, dict) and 'networks' in service:
                            del service['networks']
                            changes.append(f"Removed network reference from {service_name}")

            if modified:
                # Write fixed content back to sandbox
                fixed_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
                if self._write_file_to_sandbox(compose_file, fixed_content, sandbox_runner):
                    fixes.append(FixResult(
                        success=True,
                        message="Fixed docker-compose.yml issues",
                        file_modified=compose_file,
                        changes_made="; ".join(changes)
                    ))
                    logger.info(f"[DockerInfraFixer] Fixed compose file: {changes}")
                else:
                    logger.warning(f"[DockerInfraFixer] Failed to write fixed compose file")

        except yaml.YAMLError as e:
            # YAML syntax error - try to fix common issues
            fix = await self._fix_compose_syntax(project_path, sandbox_runner)
            if fix.success:
                fixes.append(fix)
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Compose fix failed: {e}")

        return fixes

    async def _fix_compose_syntax(self, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix docker-compose.yml YAML syntax errors (works with remote sandbox)."""
        if not project_path:
            return FixResult(success=False, message="Project path required")

        compose_file = f"{project_path}/docker-compose.yml"

        if not self._file_exists_in_sandbox(compose_file, sandbox_runner):
            return FixResult(success=False, message="docker-compose.yml not found")

        try:
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                return FixResult(success=False, message="Could not read docker-compose.yml")

            fixed = content

            # Fix common YAML issues
            # 1. Fix tabs (YAML requires spaces)
            fixed = fixed.replace('\t', '  ')

            # 2. Fix missing colons after keys
            fixed = re.sub(r'^(\s*\w+)\s*$', r'\1:', fixed, flags=re.MULTILINE)

            # 3. Fix incorrect indentation (try to normalize to 2 spaces)
            lines = fixed.split('\n')
            fixed_lines = []
            for line in lines:
                # Count leading spaces
                stripped = line.lstrip()
                if stripped:
                    indent = len(line) - len(stripped)
                    # Normalize odd indentation to even
                    if indent % 2 == 1:
                        indent = indent + 1
                    fixed_lines.append(' ' * indent + stripped)
                else:
                    fixed_lines.append(line)
            fixed = '\n'.join(fixed_lines)

            # 4. Fix missing quotes around special values
            fixed = re.sub(r':\s*(\d+\.\d+\.\d+\.\d+)\s*$', r': "\1"', fixed, flags=re.MULTILINE)

            if fixed != content:
                if self._write_file_to_sandbox(compose_file, fixed, sandbox_runner):
                    return FixResult(
                        success=True,
                        message="Fixed docker-compose.yml syntax",
                        file_modified=compose_file,
                        changes_made="Fixed tabs, indentation, and quotes"
                    )
                else:
                    return FixResult(success=False, message="Failed to write fixed file")

            return FixResult(success=False, message="Could not auto-fix YAML syntax")

        except Exception as e:
            return FixResult(success=False, message=f"Syntax fix failed: {e}")

    async def _fix_compose_depends_on(self, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix depends_on format in docker-compose.yml."""
        fixes = await self._validate_and_fix_compose(project_path, sandbox_runner)
        if fixes:
            return fixes[0]
        return FixResult(success=False, message="No depends_on fixes needed")

    async def _fix_compose_ports(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix port mapping issues in docker-compose.yml (works with remote sandbox)."""
        if not project_path:
            return FixResult(success=False, message="Project path required")

        compose_file = f"{project_path}/docker-compose.yml"

        if not self._file_exists_in_sandbox(compose_file, sandbox_runner):
            return FixResult(success=False, message="docker-compose.yml not found")

        try:
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                return FixResult(success=False, message="Could not read docker-compose.yml")

            data = yaml.safe_load(content)
            modified = False

            for service_name, service in data.get('services', {}).items():
                if not isinstance(service, dict) or 'ports' not in service:
                    continue

                fixed_ports = []
                for port in service['ports']:
                    if isinstance(port, int):
                        fixed_ports.append(f"{port}:{port}")
                        modified = True
                    elif isinstance(port, str):
                        # Ensure format is "host:container"
                        if ':' not in port:
                            fixed_ports.append(f"{port}:{port}")
                            modified = True
                        else:
                            fixed_ports.append(port)
                    else:
                        fixed_ports.append(str(port))

                service['ports'] = fixed_ports

            if modified:
                fixed_content = yaml.dump(data, default_flow_style=False, sort_keys=False)
                if self._write_file_to_sandbox(compose_file, fixed_content, sandbox_runner):
                    return FixResult(
                        success=True,
                        message="Fixed port mappings in docker-compose.yml",
                        file_modified=compose_file
                    )
                else:
                    return FixResult(success=False, message="Failed to write fixed file")

            return FixResult(success=False, message="No port fixes needed")

        except Exception as e:
            return FixResult(success=False, message=f"Port fix failed: {e}")

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_fix_history(self, project_id: str) -> List[FixResult]:
        """Get history of fixes applied for a project."""
        return self.fix_history.get(project_id, [])

    def clear_fix_history(self, project_id: str) -> None:
        """Clear fix history for a project."""
        if project_id in self.fix_history:
            del self.fix_history[project_id]


# Global instance
docker_infra_fixer = DockerInfraFixerAgent()
