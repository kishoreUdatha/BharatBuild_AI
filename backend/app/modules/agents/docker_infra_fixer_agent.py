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
    DOCKERFILE_MISSING = "dockerfile_missing"  # Cannot locate specified Dockerfile
    DOCKERFILE_TARGET_MISSING = "dockerfile_target_missing"  # target stage not found in Dockerfile
    DOCKERFILE_ALPINE_COMMANDS = "dockerfile_alpine_commands"  # groupadd/useradd not found on Alpine
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

    # Dockerfile not found error (e.g., nginx with 'build: .' but no Dockerfile in root)
    (r"Cannot locate specified Dockerfile|Dockerfile not found|unable to evaluate symlinks in Dockerfile path|failed to solve.*dockerfile parse error.*not found",
     InfraErrorType.DOCKERFILE_MISSING,
     "Dockerfile not found - service may need 'image:' instead of 'build:'",
     None),

    # Target stage not found (AI added 'target: dev' but Dockerfile has no multi-stage build)
    (r"target stage .* could not be found|failed to solve.*target.*not found",
     InfraErrorType.DOCKERFILE_TARGET_MISSING,
     "Target stage not found - remove 'target:' from docker-compose.yml build config",
     None),

    # Alpine Linux command compatibility (groupadd/useradd not available on Alpine)
    (r"groupadd:.*not found|useradd:.*not found|/bin/sh:.*groupadd|/bin/sh:.*useradd|groupadd: command not found|useradd: command not found",
     InfraErrorType.DOCKERFILE_ALPINE_COMMANDS,
     "Alpine Linux uses addgroup/adduser instead of groupadd/useradd",
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

    # Volume mount errors (file vs directory mismatch)
    (r"error mounting.*not a directory|mount.*not a directory|Are you trying to mount a directory onto a file",
     InfraErrorType.COMPOSE_VOLUME,
     "Volume mount error - file/directory mismatch",
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
    # OpenJDK images - use Eclipse Temurin (official OpenJDK distribution)
    "openjdk:latest": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17-slim": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17-jdk-slim": "eclipse-temurin:17-jdk-alpine",
    "openjdk:17-jdk": "eclipse-temurin:17-jdk-alpine",
    "openjdk:11": "eclipse-temurin:11-jdk-alpine",
    "openjdk:11-slim": "eclipse-temurin:11-jdk-alpine",
    "openjdk:11-jdk-slim": "eclipse-temurin:11-jdk-alpine",
    "openjdk:11-jdk": "eclipse-temurin:11-jdk-alpine",
    "openjdk:21": "eclipse-temurin:21-jdk-alpine",
    "openjdk:21-slim": "eclipse-temurin:21-jdk-alpine",
    "openjdk:21-jdk-slim": "eclipse-temurin:21-jdk-alpine",
    "openjdk:21-jdk": "eclipse-temurin:21-jdk-alpine",
    "java:latest": "eclipse-temurin:17-jdk-alpine",
    # Maven images - use eclipse-temurin based versions
    "maven:latest": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8.4-openjdk-17-slim": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8-openjdk-17-slim": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.9-openjdk-17-slim": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8-openjdk-17": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.9-openjdk-17": "maven:3.9-eclipse-temurin-17-alpine",
    "maven:3.8-openjdk-11-slim": "maven:3.9-eclipse-temurin-11-alpine",
    "maven:3.9-openjdk-11-slim": "maven:3.9-eclipse-temurin-11-alpine",
    # Gradle images
    "gradle:latest": "gradle:8-jdk17-alpine",
    "gradle:7-jdk17": "gradle:8-jdk17-alpine",
    "gradle:8-jdk17": "gradle:8-jdk17-alpine",
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
            InfraErrorType.COMPOSE_VOLUME,  # Volume mount errors (file/directory mismatch)
            InfraErrorType.DOCKERFILE_MISSING,  # Missing Dockerfile (e.g., nginx with build: .)
            InfraErrorType.DOCKERFILE_TARGET_MISSING,  # Target stage not found (remove 'target:')
            InfraErrorType.DOCKERFILE_ALPINE_COMMANDS,  # Alpine uses addgroup/adduser
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
        Run SAFE pre-flight checks before docker-compose up.

        IMPORTANT: We only do non-destructive cleanup operations here.
        NO file modifications - those caused too many issues.
        """
        fixes: List[FixResult] = []

        if not project_name:
            project_name = f"bharatbuild_{project_id[:8]}"

        logger.info(f"[DockerInfraFixer] Running safe pre-flight checks for {project_id}")

        # 1. Prune unused networks (safe - only removes unused)
        fix = await self._prune_networks(sandbox_runner)
        if fix and fix.success:
            fixes.append(fix)

        # 2. Remove stale containers for THIS project only
        fix = await self._cleanup_stale_containers(project_name, sandbox_runner)
        if fix:
            fixes.append(fix)

        # 3. Check Docker daemon is running
        fix = await self._check_docker_daemon(sandbox_runner)
        if fix and not fix.success:
            fixes.append(fix)

        # 4. Check disk space and prune if critically low (>90%)
        fix = await self._check_disk_space(sandbox_runner)
        if fix:
            fixes.append(fix)

        # 5. Validate volume mounts exist (SAFE: only creates missing files, never modifies)
        # This prevents "mount a directory onto a file" errors
        if project_path:
            volume_fixes = await self._validate_volume_mounts(project_path, sandbox_runner)
            fixes.extend(volume_fixes)

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
            InfraErrorType.NETWORK_POOL_OVERLAP: lambda sr: self._fix_network_overlap(project_path, sr),
            InfraErrorType.STALE_NETWORK: lambda sr: self._fix_network_overlap(project_path, sr),
            InfraErrorType.PORT_CONFLICT: lambda sr: self._fix_port_conflict(error_message, sr, project_path),
            InfraErrorType.STALE_CONTAINER: lambda sr: self._fix_stale_container(error_message, sr),
            InfraErrorType.DISK_SPACE: self._fix_disk_space,
            InfraErrorType.IMAGE_NOT_FOUND: lambda sr: self._fix_missing_image(error_message, sr, project_path),
            InfraErrorType.MEMORY_LIMIT: lambda sr: self._fix_memory_limit(project_path, sr),
            InfraErrorType.DOCKERFILE_SYNTAX: lambda sr: self._fix_dockerfile_error(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_BASE_IMAGE: lambda sr: self._fix_dockerfile_base_image(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_COPY_ERROR: lambda sr: self._fix_dockerfile_copy(error_message, project_path, sr),
            InfraErrorType.COMPOSE_SYNTAX: lambda sr: self._fix_compose_syntax(project_path, sr),
            InfraErrorType.COMPOSE_DEPENDS_ON: lambda sr: self._fix_compose_depends_on(project_path, sr),
            InfraErrorType.COMPOSE_PORT_MAPPING: lambda sr: self._fix_compose_ports(error_message, project_path, sr),
            InfraErrorType.VOLUME_PERMISSION: lambda sr: self._fix_volume_permissions(error_message, project_path, sr),
            InfraErrorType.COMPOSE_VOLUME: lambda sr: self._fix_volume_mount(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_MISSING: lambda sr: self._fix_missing_dockerfile(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_TARGET_MISSING: lambda sr: self._fix_missing_target(error_message, project_path, sr),
            InfraErrorType.DOCKERFILE_ALPINE_COMMANDS: lambda sr: self._fix_alpine_commands(error_message, project_path, sr),
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
                if usage > 90:  # Only prune at critical level (90%+)
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

    async def _fix_network_overlap(self, project_path: str, sandbox_runner: callable) -> FixResult:
        """Fix network pool overlap by removing hardcoded subnets and pruning networks."""
        try:
            changes_made = []

            # Step 1: Remove hardcoded subnets from docker-compose.yml
            # This is the ROOT CAUSE of the "Pool overlaps" error
            compose_file = f"{project_path}/docker-compose.yml"
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)

            if content:
                try:
                    compose_data = yaml.safe_load(content)
                    modified = False

                    if compose_data and 'networks' in compose_data:
                        for network_name, network_config in compose_data.get('networks', {}).items():
                            if isinstance(network_config, dict) and 'ipam' in network_config:
                                # Remove the hardcoded IPAM configuration
                                del network_config['ipam']
                                modified = True
                                logger.info(f"[DockerInfraFixer] Removed hardcoded IPAM/subnet from network '{network_name}'")
                                changes_made.append(f"Removed hardcoded subnet from '{network_name}'")

                    if modified:
                        fixed_content = yaml.dump(
                            compose_data,
                            default_flow_style=False,
                            sort_keys=False,
                            allow_unicode=True,
                            width=1000
                        )
                        if self._write_file_to_sandbox(compose_file, fixed_content, sandbox_runner):
                            logger.info(f"[DockerInfraFixer] Fixed docker-compose.yml - removed hardcoded subnets")

                except Exception as e:
                    logger.warning(f"[DockerInfraFixer] Could not fix docker-compose.yml: {e}")

            # Step 2: Prune unused networks (original fix)
            exit_code, output = sandbox_runner("docker network prune -f", None, 30)

            if exit_code == 0 or changes_made:
                message = "Pruned unused networks"
                if changes_made:
                    message = "; ".join(changes_made) + "; " + message
                return FixResult(
                    success=True,
                    message=message,
                    command_executed="docker network prune -f",
                    output=output,
                    file_modified=compose_file if changes_made else None,
                    changes_made="; ".join(changes_made) if changes_made else None
                )

            # More aggressive: remove all custom bridge networks
            exit_code, output = sandbox_runner(
                "docker network ls --filter 'driver=bridge' -q | xargs -r docker network rm 2>/dev/null || true",
                None, 60
            )
            return FixResult(
                success=True,
                message="Removed custom Docker networks" + (f"; {'; '.join(changes_made)}" if changes_made else ""),
                command_executed="docker network rm (all custom)",
                output=output
            )
        except Exception as e:
            return FixResult(success=False, message=f"Network fix failed: {e}")

    async def _fix_port_conflict(
        self,
        error_message: str,
        sandbox_runner: callable,
        project_path: str = None
    ) -> FixResult:
        """Fix port conflict by killing processes OR dynamically remapping ports.

        Strategy:
        1. First try to kill processes using the conflicting ports
        2. Wait briefly and check if ports are still in use
        3. If ports persist (system services that auto-restart), remap ports in docker-compose.yml

        This handles system-level services like nginx/apache that restart via systemd.
        """
        # Find ALL ports mentioned in the error - not just the first one
        ports_found = set()

        # Pattern 1: "0.0.0.0:5432" or "127.0.0.1:8080" - IP:PORT format
        for match in re.finditer(r'\d+\.\d+\.\d+\.\d+:(\d+)', error_message):
            ports_found.add(match.group(1))

        # Pattern 2: "port 5432" or "port: 5432"
        for match in re.finditer(r'port[:\s]+(\d+)', error_message, re.IGNORECASE):
            ports_found.add(match.group(1))

        # Pattern 3: Common service ports that might be blocked
        common_ports = ['3000', '3001', '5173', '5174', '8080', '8081', '5432', '5433', '6379', '27017', '3306', '80', '443']
        for port in common_ports:
            if port in error_message:
                ports_found.add(port)

        if not ports_found:
            return FixResult(success=False, message="Could not determine conflicting port")

        freed_ports = []
        persistent_ports = []

        try:
            # Step 1: Try to kill processes on each port
            for port in ports_found:
                # Kill process using port
                sandbox_runner(f"fuser -k {port}/tcp 2>/dev/null || true", None, 10)

                # Remove containers using port
                sandbox_runner(f"docker ps --filter 'publish={port}' -q | xargs -r docker rm -f", None, 30)

                logger.info(f"[DockerInfraFixer] Attempted to free port {port}")

            # Step 2: Wait for systemd services to potentially restart
            await asyncio.sleep(2)

            # Step 3: Check which ports are still in use
            for port in ports_found:
                exit_code, output = sandbox_runner(
                    f"lsof -i :{port} -t 2>/dev/null || ss -tlnp 2>/dev/null | grep ':{port} '",
                    None, 5
                )
                if exit_code == 0 and output and output.strip():
                    # Port is still in use - likely a system service that auto-restarted
                    persistent_ports.append(port)
                    logger.warning(f"[DockerInfraFixer] Port {port} still in use after kill - system service detected")
                else:
                    freed_ports.append(port)

            # Step 4: If there are persistent ports, try dynamic port remapping
            if persistent_ports and project_path:
                remap_result = await self._remap_ports_in_compose(
                    persistent_ports, project_path, sandbox_runner
                )
                if remap_result.success:
                    message_parts = []
                    if freed_ports:
                        message_parts.append(f"Freed port(s): {', '.join(freed_ports)}")
                    message_parts.append(remap_result.message)
                    return FixResult(
                        success=True,
                        message="; ".join(message_parts),
                        file_modified=remap_result.file_modified,
                        changes_made=remap_result.changes_made
                    )
                else:
                    # Remapping failed, return partial success if some ports were freed
                    if freed_ports:
                        return FixResult(
                            success=True,
                            message=f"Freed port(s): {', '.join(freed_ports)}; Could not remap: {', '.join(persistent_ports)}",
                            command_executed=f"kill processes on ports: {', '.join(freed_ports)}"
                        )
                    return FixResult(
                        success=False,
                        message=f"Ports {', '.join(persistent_ports)} blocked by system services - manual intervention required"
                    )

            # All ports were freed successfully
            if freed_ports:
                return FixResult(
                    success=True,
                    message=f"Freed port(s): {', '.join(freed_ports)}",
                    command_executed=f"kill processes and containers on ports: {', '.join(freed_ports)}"
                )

            return FixResult(success=False, message="No ports could be freed")

        except Exception as e:
            return FixResult(success=False, message=f"Port fix failed: {e}")

    async def _remap_ports_in_compose(
        self,
        blocked_ports: List[str],
        project_path: str,
        sandbox_runner: callable
    ) -> FixResult:
        """Dynamically remap blocked ports to alternative ports in docker-compose.yml.

        Port remapping strategy:
        - 80 -> 8880 (nginx/web server)
        - 443 -> 8443 (HTTPS)
        - 8080 -> 8180 (backend/API)
        - 3000 -> 3100 (frontend dev server)
        - 5173 -> 5273 (Vite dev server)
        - Other ports -> port + 100
        """
        PORT_ALTERNATIVES = {
            '80': '8880',
            '443': '8443',
            '8080': '8180',
            '3000': '3100',
            '3001': '3101',
            '5173': '5273',
            '5174': '5274',
        }

        compose_file = f"{project_path}/docker-compose.yml"

        if not self._file_exists_in_sandbox(compose_file, sandbox_runner):
            return FixResult(success=False, message="docker-compose.yml not found for port remapping")

        try:
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                return FixResult(success=False, message="Could not read docker-compose.yml")

            compose_data = yaml.safe_load(content)
            if not compose_data or 'services' not in compose_data:
                return FixResult(success=False, message="Invalid docker-compose.yml structure")

            remapped = []
            modified = False

            for service_name, service in compose_data.get('services', {}).items():
                if not isinstance(service, dict) or 'ports' not in service:
                    continue

                new_ports = []
                for port_mapping in service['ports']:
                    port_str = str(port_mapping)
                    changed = False

                    for blocked_port in blocked_ports:
                        # Handle various port mapping formats:
                        # "80:80" -> "8880:80"
                        # "8080:8080" -> "8180:8080"
                        # "0.0.0.0:80:80" -> "0.0.0.0:8880:80"

                        # Pattern: host_port:container_port (we only change host_port)
                        pattern = rf'^({blocked_port}):(\d+)$'
                        match = re.match(pattern, port_str)
                        if match:
                            container_port = match.group(2)
                            alt_port = PORT_ALTERNATIVES.get(blocked_port, str(int(blocked_port) + 100))

                            # Verify the alternative port is available
                            exit_code, _ = sandbox_runner(
                                f"lsof -i :{alt_port} -t 2>/dev/null || ss -tlnp 2>/dev/null | grep ':{alt_port} '",
                                None, 5
                            )
                            if exit_code == 0:
                                # Alt port also in use, try +200
                                alt_port = str(int(alt_port) + 100)

                            port_str = f"{alt_port}:{container_port}"
                            remapped.append(f"{service_name}: {blocked_port} -> {alt_port}")
                            changed = True
                            modified = True
                            logger.info(f"[DockerInfraFixer] Remapped {service_name} port {blocked_port} -> {alt_port}")
                            break

                        # Pattern with IP: 0.0.0.0:host_port:container_port
                        pattern_ip = rf'^(\d+\.\d+\.\d+\.\d+):({blocked_port}):(\d+)$'
                        match_ip = re.match(pattern_ip, port_str)
                        if match_ip:
                            ip = match_ip.group(1)
                            container_port = match_ip.group(3)
                            alt_port = PORT_ALTERNATIVES.get(blocked_port, str(int(blocked_port) + 100))

                            port_str = f"{ip}:{alt_port}:{container_port}"
                            remapped.append(f"{service_name}: {blocked_port} -> {alt_port}")
                            changed = True
                            modified = True
                            logger.info(f"[DockerInfraFixer] Remapped {service_name} port {blocked_port} -> {alt_port}")
                            break

                    new_ports.append(port_str)

                service['ports'] = new_ports

            if modified:
                fixed_yaml = yaml.dump(
                    compose_data,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=1000
                )

                if self._write_file_to_sandbox(compose_file, fixed_yaml, sandbox_runner):
                    changes_summary = "; ".join(remapped)
                    return FixResult(
                        success=True,
                        message=f"Remapped ports to avoid system services: {changes_summary}",
                        file_modified=compose_file,
                        changes_made=changes_summary
                    )
                else:
                    return FixResult(success=False, message="Failed to write port remapping to docker-compose.yml")

            return FixResult(
                success=False,
                message=f"Could not find port mappings to remap for ports: {', '.join(blocked_ports)}"
            )

        except Exception as e:
            logger.error(f"[DockerInfraFixer] Port remapping failed: {e}")
            return FixResult(success=False, message=f"Port remapping failed: {e}")

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

    async def _fix_missing_image(
        self,
        error_message: str,
        sandbox_runner: callable,
        project_path: str = None
    ) -> FixResult:
        """Auto-pull missing Docker image AND update Dockerfile if needed.

        IMPORTANT: This method now also modifies the Dockerfile to use the
        replacement image, not just pull it. Otherwise the next build will
        fail with the same error.
        """
        # Extract image name from error
        match = re.search(r'manifest for ([^\s]+) not found|pull access denied for ([^\s,]+)|repository ([^\s]+) not found',
                         error_message, re.IGNORECASE)
        if not match:
            return FixResult(success=False, message="Could not determine missing image name")

        original_image = match.group(1) or match.group(2) or match.group(3)

        # Check if we have an alternative
        alt_image = DOCKERFILE_FIXES.get(original_image)
        image_to_pull = alt_image if alt_image else original_image

        dockerfile_modified = False
        modified_file = None

        # If we have an alternative image AND project_path, update the Dockerfile
        if alt_image and project_path:
            # Find and update all Dockerfiles that use the old image
            dockerfile_paths = [
                f"{project_path}/Dockerfile",
                f"{project_path}/frontend/Dockerfile",
                f"{project_path}/backend/Dockerfile",
            ]

            for dockerfile_path in dockerfile_paths:
                if self._file_exists_in_sandbox(dockerfile_path, sandbox_runner):
                    try:
                        content = self._read_file_from_sandbox(dockerfile_path, sandbox_runner)
                        if content and original_image in content:
                            # Replace the old image with the new one
                            fixed_content = content.replace(original_image, alt_image)
                            if self._write_file_to_sandbox(dockerfile_path, fixed_content, sandbox_runner):
                                dockerfile_modified = True
                                modified_file = dockerfile_path
                                logger.info(f"[DockerInfraFixer] Updated Dockerfile: {original_image} -> {alt_image}")
                    except Exception as e:
                        logger.warning(f"[DockerInfraFixer] Failed to update {dockerfile_path}: {e}")

        try:
            exit_code, output = sandbox_runner(f"docker pull {image_to_pull}", None, 300)
            if exit_code == 0:
                message = f"Pulled image: {image_to_pull}"
                if dockerfile_modified:
                    message = f"Updated Dockerfile ({original_image} -> {alt_image}) and pulled image"
                return FixResult(
                    success=True,
                    message=message,
                    command_executed=f"docker pull {image_to_pull}",
                    file_modified=modified_file,
                    changes_made=f"Replaced {original_image} with {alt_image}" if dockerfile_modified else None
                )
            else:
                # Try without tag
                base_image = image_to_pull.split(':')[0]
                exit_code, output = sandbox_runner(f"docker pull {base_image}:latest", None, 300)
                return FixResult(
                    success=exit_code == 0,
                    message=f"Pulled image: {base_image}:latest",
                    command_executed=f"docker pull {base_image}:latest",
                    file_modified=modified_file if dockerfile_modified else None
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

    async def _fix_volume_mount(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """
        Fix volume mount errors where file/directory type mismatches.

        Common case: docker-compose mounts ./nginx/nginx.conf:/etc/nginx/nginx.conf
        but ./nginx/nginx.conf is a directory or doesn't exist.
        """
        try:
            # Extract the source path from error message
            # Pattern: "mounting "/path/to/file" to rootfs"
            path_match = re.search(r'mounting\s+"([^"]+)"', error_message)
            if not path_match:
                # Try another pattern: "mount src=/path/to/file"
                path_match = re.search(r'mount src=([^,]+)', error_message)

            if not path_match:
                return FixResult(
                    success=False,
                    message="Could not extract file path from volume mount error"
                )

            source_path = path_match.group(1)
            logger.info(f"[DockerInfraFixer] Volume mount issue with: {source_path}")

            # Check if it's supposed to be a file (ends with a filename, not a directory)
            filename = source_path.split('/')[-1]
            # Common directory patterns that contain dots:
            # - .d suffix (conf.d, sites.d, modules.d) - Linux config directories
            is_dot_d_directory = filename.endswith('.d')
            is_common_directory = filename.lower() in {'data', 'logs', 'cache', 'tmp', 'config', 'ssl', 'certs'}
            has_file_extension = '.' in filename and not filename.startswith('.') and not is_dot_d_directory
            is_supposed_to_be_file = has_file_extension and not is_common_directory

            if is_supposed_to_be_file:
                # Check if path exists as a directory (the problem)
                exit_code, output = sandbox_runner(f'test -d "{source_path}" && echo "is_dir"', None, 10)
                if exit_code == 0 and 'is_dir' in output:
                    # It's a directory but should be a file - remove directory
                    sandbox_runner(f'rm -rf "{source_path}"', None, 10)
                    logger.info(f"[DockerInfraFixer] Removed directory that should be file: {source_path}")

                # Create parent directory
                parent_dir = '/'.join(source_path.split('/')[:-1])
                sandbox_runner(f'mkdir -p "{parent_dir}"', None, 10)

                # Create the file with appropriate default content
                filename = source_path.split('/')[-1].lower()

                if 'nginx.conf' in filename:
                    # Create default nginx.conf for reverse proxy
                    nginx_config = '''events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8080;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        location /api {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
'''
                    # Write using base64 to handle special chars
                    import base64
                    encoded = base64.b64encode(nginx_config.encode()).decode()
                    sandbox_runner(f'echo "{encoded}" | base64 -d > "{source_path}"', None, 10)
                    return FixResult(
                        success=True,
                        message=f"Created nginx.conf at {source_path}",
                        file_modified=source_path
                    )
                else:
                    # Create empty file for other types
                    sandbox_runner(f'touch "{source_path}"', None, 10)
                    return FixResult(
                        success=True,
                        message=f"Created empty file at {source_path}",
                        file_modified=source_path
                    )
            else:
                # It's supposed to be a directory
                sandbox_runner(f'mkdir -p "{source_path}"', None, 10)
                return FixResult(
                    success=True,
                    message=f"Created directory at {source_path}"
                )

        except Exception as e:
            logger.error(f"[DockerInfraFixer] Volume mount fix failed: {e}")
            return FixResult(success=False, message=f"Volume mount fix failed: {e}")

    async def _fix_missing_dockerfile(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """
        Fix "Cannot locate specified Dockerfile" error.

        Common case: nginx service with 'build: .' but no Dockerfile in root.
        Fix: Change 'build: .' to 'image: nginx:alpine' in docker-compose.yml.

        This is a SAFE fix that only changes the build strategy, not the service config.
        """
        try:
            compose_file = f"{project_path}/docker-compose.yml"

            # Read docker-compose.yml
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                return FixResult(
                    success=False,
                    message="Could not read docker-compose.yml"
                )

            compose_data = yaml.safe_load(content)
            if not compose_data or 'services' not in compose_data:
                return FixResult(
                    success=False,
                    message="Invalid docker-compose.yml structure"
                )

            modified = False
            fixed_services = []

            for service_name, service in compose_data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                # Check if service has 'build: .' pointing to a non-existent Dockerfile
                if 'build' in service:
                    build_config = service.get('build')
                    build_context = '.'

                    if isinstance(build_config, str):
                        build_context = build_config
                    elif isinstance(build_config, dict):
                        build_context = build_config.get('context', '.')

                    # Check if Dockerfile exists for this context
                    if build_context in ['.', './']:
                        dockerfile_path = f"{project_path}/Dockerfile"
                    else:
                        dockerfile_path = f"{project_path}/{build_context}/Dockerfile"

                    exit_code, _ = sandbox_runner(f'test -f "{dockerfile_path}" && echo "exists"', None, 5)

                    if exit_code != 0:  # Dockerfile doesn't exist
                        # For nginx, use pre-built image
                        if 'nginx' in service_name.lower():
                            del service['build']
                            service['image'] = 'nginx:alpine'

                            # Ensure nginx.conf volume mount
                            if 'volumes' not in service:
                                service['volumes'] = []

                            has_nginx_conf = any('nginx.conf' in str(v) for v in service.get('volumes', []))
                            if not has_nginx_conf:
                                service['volumes'].append('./nginx.conf:/etc/nginx/nginx.conf:ro')

                            modified = True
                            fixed_services.append(service_name)
                            logger.info(f"[DockerInfraFixer] Fixed {service_name}: changed 'build:' to 'image: nginx:alpine'")

                        # For other common services, use appropriate images
                        elif 'redis' in service_name.lower():
                            del service['build']
                            service['image'] = 'redis:alpine'
                            modified = True
                            fixed_services.append(service_name)

                        elif 'postgres' in service_name.lower() or 'db' in service_name.lower():
                            del service['build']
                            service['image'] = 'postgres:15-alpine'
                            modified = True
                            fixed_services.append(service_name)

            if modified:
                # Write updated docker-compose.yml
                import base64
                fixed_yaml = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
                encoded = base64.b64encode(fixed_yaml.encode()).decode()
                sandbox_runner(f'echo "{encoded}" | base64 -d > "{compose_file}"', None, 10)

                return FixResult(
                    success=True,
                    message=f"Fixed missing Dockerfile for: {', '.join(fixed_services)}",
                    file_modified=compose_file,
                    changes_made=f"Changed 'build:' to 'image:' for services without Dockerfile"
                )
            else:
                return FixResult(
                    success=False,
                    message="Could not auto-fix missing Dockerfile - may need manual Dockerfile creation"
                )

        except Exception as e:
            logger.error(f"[DockerInfraFixer] Missing Dockerfile fix failed: {e}")
            return FixResult(success=False, message=f"Missing Dockerfile fix failed: {e}")

    async def _fix_missing_target(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """
        Fix "target stage could not be found" error.

        Common cause: AI fixer added 'target: dev' to docker-compose.yml build config,
        but the Dockerfile doesn't have multi-stage builds with that target name.

        Fix: Remove 'target:' from all service build configurations in docker-compose.yml.
        """
        try:
            compose_file = f"{project_path}/docker-compose.yml"

            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                return FixResult(
                    success=False,
                    message="Could not read docker-compose.yml"
                )

            compose_data = yaml.safe_load(content)
            if not compose_data or 'services' not in compose_data:
                return FixResult(
                    success=False,
                    message="Invalid docker-compose.yml structure"
                )

            modified = False
            fixed_services = []

            for service_name, service in compose_data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                # Check if service has build config with 'target' key
                if 'build' in service:
                    build_config = service.get('build')

                    if isinstance(build_config, dict) and 'target' in build_config:
                        # Remove the target key
                        del build_config['target']
                        modified = True
                        fixed_services.append(service_name)
                        logger.info(f"[DockerInfraFixer] Removed 'target:' from {service_name} build config")

            if modified:
                fixed_yaml = yaml.dump(compose_data, default_flow_style=False, sort_keys=False)
                if self._write_file_to_sandbox(compose_file, fixed_yaml, sandbox_runner):
                    return FixResult(
                        success=True,
                        message=f"Removed invalid 'target:' from: {', '.join(fixed_services)}",
                        file_modified=compose_file,
                        changes_made="Removed 'target:' key from build configurations"
                    )

            return FixResult(
                success=False,
                message="Could not find 'target:' in docker-compose.yml to remove"
            )

        except Exception as e:
            logger.error(f"[DockerInfraFixer] Missing target fix failed: {e}")
            return FixResult(success=False, message=f"Missing target fix failed: {e}")

    async def _fix_alpine_commands(self, error_message: str, project_path: str, sandbox_runner: callable) -> FixResult:
        """
        Fix Alpine Linux command compatibility issues in Dockerfile.

        Alpine uses:
        - addgroup instead of groupadd
        - adduser instead of useradd

        Common patterns to fix:
        - RUN groupadd -r appuser && useradd -r -g appuser appuser
          → RUN addgroup -S appuser && adduser -S -G appuser appuser
        - RUN groupadd --system appuser
          → RUN addgroup -S appuser
        - RUN useradd --system --gid appuser appuser
          → RUN adduser -S -G appuser appuser
        """
        try:
            # Find all Dockerfiles
            dockerfile_paths = [
                f"{project_path}/Dockerfile",
                f"{project_path}/backend/Dockerfile",
                f"{project_path}/frontend/Dockerfile",
            ]

            fixed_files = []

            for dockerfile_path in dockerfile_paths:
                if not self._file_exists_in_sandbox(dockerfile_path, sandbox_runner):
                    continue

                content = self._read_file_from_sandbox(dockerfile_path, sandbox_runner)
                if not content:
                    continue

                # Check if this Dockerfile has groupadd/useradd commands
                if 'groupadd' not in content and 'useradd' not in content:
                    continue

                original_content = content

                # Replace groupadd patterns with addgroup
                # Pattern: groupadd -r groupname OR groupadd --system groupname
                content = re.sub(
                    r'groupadd\s+(?:-r|--system)\s+(\w+)',
                    r'addgroup -S \1',
                    content
                )

                # Pattern: groupadd groupname (without flags)
                content = re.sub(
                    r'groupadd\s+(\w+)(?!\s)',
                    r'addgroup -S \1',
                    content
                )

                # Replace useradd patterns with adduser
                # Pattern: useradd -r -g groupname username OR useradd --system --gid groupname username
                content = re.sub(
                    r'useradd\s+(?:-r|--system)\s+(?:-g|--gid)\s+(\w+)\s+(\w+)',
                    r'adduser -S -G \1 \2',
                    content
                )

                # Pattern: useradd -r username (system user without group)
                content = re.sub(
                    r'useradd\s+(?:-r|--system)\s+(\w+)(?!\s+-)',
                    r'adduser -S \1',
                    content
                )

                # Pattern: useradd --no-create-home --shell /sbin/nologin -g group user
                content = re.sub(
                    r'useradd\s+(?:--no-create-home\s+)?(?:--shell\s+\S+\s+)?(?:-g|--gid)\s+(\w+)\s+(\w+)',
                    r'adduser -S -G \1 -H -D \2',
                    content
                )

                # Pattern: useradd -u UID -g GID username
                content = re.sub(
                    r'useradd\s+(?:-u|--uid)\s+(\d+)\s+(?:-g|--gid)\s+(\w+)\s+(\w+)',
                    r'adduser -S -u \1 -G \2 \3',
                    content
                )

                # Pattern: Simple useradd username
                content = re.sub(
                    r'useradd\s+(\w+)(?!\s+-)',
                    r'adduser -S -D \1',
                    content
                )

                if content != original_content:
                    if self._write_file_to_sandbox(dockerfile_path, content, sandbox_runner):
                        fixed_files.append(dockerfile_path.split('/')[-1])
                        logger.info(f"[DockerInfraFixer] Fixed Alpine commands in {dockerfile_path}")

            if fixed_files:
                return FixResult(
                    success=True,
                    message=f"Fixed Alpine commands (groupadd→addgroup, useradd→adduser) in: {', '.join(fixed_files)}",
                    file_modified=dockerfile_paths[0] if len(fixed_files) == 1 else None,
                    changes_made="Replaced Debian user/group commands with Alpine equivalents"
                )

            return FixResult(
                success=False,
                message="Could not find groupadd/useradd commands to fix in Dockerfiles"
            )

        except Exception as e:
            logger.error(f"[DockerInfraFixer] Alpine commands fix failed: {e}")
            return FixResult(success=False, message=f"Alpine commands fix failed: {e}")

    async def _validate_volume_mounts(self, project_path: str, sandbox_runner: callable) -> List[FixResult]:
        """
        Validate and create missing volume mount files BEFORE docker-compose up.

        This is a SAFE preflight operation:
        - Only creates files that don't exist
        - Never modifies existing files
        - Prevents "mount a directory onto a file" errors

        Dynamically detects file types and creates appropriate defaults.
        """
        fixes = []
        compose_file = f"{project_path}/docker-compose.yml"

        if not self._file_exists_in_sandbox(compose_file, sandbox_runner):
            return fixes

        try:
            content = self._read_file_from_sandbox(compose_file, sandbox_runner)
            if not content:
                return fixes

            import yaml
            compose_data = yaml.safe_load(content)

            if not compose_data or 'services' not in compose_data:
                return fixes

            for service_name, service in compose_data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                volumes = service.get('volumes', [])
                for volume in volumes:
                    if isinstance(volume, str) and ':' in volume:
                        # Parse volume mount: ./nginx/nginx.conf:/etc/nginx/nginx.conf
                        parts = volume.split(':')
                        source = parts[0].strip()

                        # Only handle relative paths (starting with . or simple relative)
                        if not source.startswith('./') and not source.startswith('.\\'):
                            if source.startswith('/') or source.startswith('$'):
                                continue  # Skip absolute paths and variables

                        # Normalize path
                        if source.startswith('./'):
                            source_path = f"{project_path}/{source[2:]}"
                        else:
                            source_path = f"{project_path}/{source}"

                        # Check if file/dir already exists
                        exit_code, _ = sandbox_runner(f'test -e "{source_path}" && echo "exists"', None, 5)
                        if exit_code == 0:
                            continue  # Already exists, skip

                        # Determine if it's a file (has extension) or directory
                        filename = source_path.split('/')[-1]
                        # Common directory patterns that contain dots:
                        # - .d suffix (conf.d, sites.d, modules.d) - Linux config directories
                        # - data directories, etc.
                        is_dot_d_directory = filename.endswith('.d')
                        is_common_directory = filename.lower() in {'data', 'logs', 'cache', 'tmp', 'config', 'ssl', 'certs'}
                        has_file_extension = '.' in filename and not filename.startswith('.') and not is_dot_d_directory
                        is_file = has_file_extension and not is_common_directory

                        if is_file:
                            # Create parent directory
                            parent_dir = '/'.join(source_path.split('/')[:-1])
                            sandbox_runner(f'mkdir -p "{parent_dir}"', None, 5)

                            # Create file with appropriate default content
                            file_created = self._create_default_file(source_path, filename, sandbox_runner)
                            if file_created:
                                fixes.append(FixResult(
                                    success=True,
                                    message=f"Created {source} for {service_name} volume mount",
                                    file_modified=source_path
                                ))
                                logger.info(f"[DockerInfraFixer] Preflight: Created {source_path}")
                        else:
                            # Create directory
                            sandbox_runner(f'mkdir -p "{source_path}"', None, 5)
                            fixes.append(FixResult(
                                success=True,
                                message=f"Created directory {source} for {service_name} volume mount"
                            ))
                            logger.info(f"[DockerInfraFixer] Preflight: Created directory {source_path}")

        except yaml.YAMLError as e:
            logger.warning(f"[DockerInfraFixer] Could not parse docker-compose.yml: {e}")
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Error validating volume mounts: {e}")

        return fixes

    def _create_default_file(self, file_path: str, filename: str, sandbox_runner: callable) -> bool:
        """
        Create a default file based on its type.

        Returns True if file was created, False otherwise.
        """
        import base64

        filename_lower = filename.lower()

        # Default content templates for common files
        DEFAULT_CONTENTS = {
            'nginx.conf': '''events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream frontend {
        server frontend:3000;
    }

    upstream backend {
        server backend:8080;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        location /api {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
    }
}
''',
            '.env': '# Environment variables\n',
            '.gitignore': 'node_modules/\n.env\n*.log\n',
            'init.sql': '-- Database initialization\n',
            'schema.sql': '-- Database schema\n',
            'seed.sql': '-- Seed data\n',
        }

        # Find matching template
        content = None
        for key, template in DEFAULT_CONTENTS.items():
            if key in filename_lower:
                content = template
                break

        if content is None:
            # Default: create empty file
            content = f'# Auto-generated {filename}\n'

        try:
            # Write using base64 to handle special characters
            encoded = base64.b64encode(content.encode()).decode()
            exit_code, _ = sandbox_runner(f'echo "{encoded}" | base64 -d > "{file_path}"', None, 10)
            return exit_code == 0
        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Could not create {file_path}: {e}")
            return False

    # ========================================================================
    # DOCKERFILE FIXES
    # ========================================================================

    async def _validate_and_fix_dockerfile(self, project_path: str, sandbox_runner: callable) -> List[FixResult]:
        """Validate and fix Dockerfile issues (works with remote sandbox).

        CONSERVATIVE APPROACH: Only fix files that have actual problems.
        We verify the Dockerfile is valid before and after any changes.
        """
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
                if not content or not content.strip():
                    logger.warning(f"[DockerInfraFixer] Dockerfile is empty or unreadable: {dockerfile_path}")
                    continue

                # Validate Dockerfile has basic structure
                if 'FROM' not in content.upper():
                    logger.warning(f"[DockerInfraFixer] Dockerfile missing FROM instruction: {dockerfile_path}")
                    continue

                fixed_content = content
                changes = []

                # ONLY fix base images that are EXACT matches (not partial)
                # This prevents accidentally modifying valid images like node:18-alpine
                for old_image, new_image in DOCKERFILE_FIXES.items():
                    # Very strict pattern: FROM <exact-image> end-of-line or AS
                    # This won't match "node:18-alpine" when looking for "node:18"
                    pattern = rf'^(FROM\s+){re.escape(old_image)}(\s*(?:AS\s+\w+)?\s*)$'
                    match = re.search(pattern, fixed_content, re.MULTILINE | re.IGNORECASE)
                    if match:
                        # Only replace if the image doesn't already have a variant
                        image_in_file = match.group(0).split()[1]  # Get the actual image name
                        if image_in_file.lower() == old_image.lower():
                            # Check if this exact image (without variant) needs replacement
                            fixed_content = re.sub(
                                pattern,
                                rf'\g<1>{new_image}\g<2>',
                                fixed_content,
                                flags=re.MULTILINE | re.IGNORECASE
                            )
                            changes.append(f"Changed base image: {old_image} -> {new_image}")

                # ONLY add WORKDIR if truly missing AND there are COPY/RUN commands
                # that would fail without it
                has_workdir = bool(re.search(r'^WORKDIR\s+', fixed_content, re.MULTILINE | re.IGNORECASE))
                has_copy_or_run = bool(re.search(r'^(COPY|RUN)\s+', fixed_content, re.MULTILINE | re.IGNORECASE))

                if not has_workdir and has_copy_or_run:
                    # Only add WORKDIR for simple Dockerfiles that clearly need it
                    # Skip multi-stage builds which handle their own WORKDIR
                    from_count = len(re.findall(r'^FROM\s+', fixed_content, re.MULTILINE | re.IGNORECASE))
                    if from_count == 1:
                        fixed_content = re.sub(
                            r'^(FROM .+)$',
                            r'\1\nWORKDIR /app',
                            fixed_content,
                            count=1,
                            flags=re.MULTILINE
                        )
                        changes.append("Added WORKDIR /app")

                # ONLY write if we have MEANINGFUL changes (not just whitespace)
                if changes:
                    logger.info(f"[DockerInfraFixer] Applying Dockerfile fixes: {changes}")

                    if self._write_file_to_sandbox(dockerfile_path, fixed_content, sandbox_runner):
                        # Verify the Dockerfile is still valid after our changes
                        verify_content = self._read_file_from_sandbox(dockerfile_path, sandbox_runner)
                        if verify_content and 'FROM' in verify_content.upper():
                            fixes.append(FixResult(
                                success=True,
                                message=f"Fixed Dockerfile: {dockerfile_path.split('/')[-1]}",
                                file_modified=dockerfile_path,
                                changes_made="; ".join(changes)
                            ))
                            logger.info(f"[DockerInfraFixer] Successfully fixed Dockerfile: {changes}")
                        else:
                            logger.error(f"[DockerInfraFixer] Dockerfile corrupted after fix, backup should restore")
                    else:
                        logger.warning(f"[DockerInfraFixer] Failed to write Dockerfile fixes")
                else:
                    logger.debug(f"[DockerInfraFixer] Dockerfile looks valid, no fixes needed: {dockerfile_path}")

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
        # Extract the missing file - handle multiple error formats
        match = re.search(
            r'stat ([^:]+): file does not exist|'  # stat mvnw: file does not exist
            r'COPY.*"([^"]+)".*not found|'         # COPY "file" not found
            r'failed to compute cache key.*"([^"]+)"',  # cache key "file"
            error_message
        )
        if not match:
            return FixResult(success=False, message="Could not determine missing file")

        missing_file = (match.group(1) or match.group(2) or match.group(3)).strip()

        # For mvnw/gradlew, return helpful message for Claude to fix
        if missing_file in ['mvnw', 'gradlew', '.mvn', 'gradle']:
            return FixResult(
                success=False,
                message=f"Missing {missing_file} - remove wrapper COPY from Dockerfile and use mvn/gradle directly"
            )

        return FixResult(
            success=False,
            message=f"COPY failed for {missing_file} - file not found in build context"
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
        """Write a file to the sandbox (works for both local and remote).

        Uses a chunked write approach with heredoc for reliability.
        """
        try:
            import base64

            # Create a backup first
            backup_path = f"{file_path}.bak"
            sandbox_runner(f'cp "{file_path}" "{backup_path}" 2>/dev/null || true', None, 10)

            # Encode content to base64
            encoded = base64.b64encode(content.encode()).decode()

            # Write base64 in chunks to avoid command line length limits
            temp_file = f"{file_path}.b64tmp"
            chunk_size = 50000  # Safe chunk size for shell commands

            # Clear/create temp file
            sandbox_runner(f'> "{temp_file}"', None, 10)

            # Write in chunks
            for i in range(0, len(encoded), chunk_size):
                chunk = encoded[i:i + chunk_size]
                # Use echo with double quotes - base64 only has A-Za-z0-9+/= which are shell-safe
                write_cmd = f'echo -n "{chunk}" >> "{temp_file}"'
                exit_code, output = sandbox_runner(write_cmd, None, 30)
                if exit_code != 0:
                    logger.warning(f"[DockerInfraFixer] Failed to write chunk {i//chunk_size}: {output}")
                    sandbox_runner(f'mv "{backup_path}" "{file_path}" 2>/dev/null || true', None, 10)
                    sandbox_runner(f'rm -f "{temp_file}"', None, 10)
                    return False

            # Decode temp file to final file
            decode_cmd = f'base64 -d "{temp_file}" > "{file_path}" && rm -f "{temp_file}"'
            exit_code, output = sandbox_runner(decode_cmd, None, 30)

            if exit_code != 0:
                logger.warning(f"[DockerInfraFixer] Failed to decode file: {output}")
                sandbox_runner(f'mv "{backup_path}" "{file_path}" 2>/dev/null || true', None, 10)
                return False

            # Verify the file exists and has content
            verify_code, verify_output = sandbox_runner(f'test -s "{file_path}" && head -1 "{file_path}"', None, 10)
            if verify_code != 0:
                logger.warning(f"[DockerInfraFixer] File verification failed: {file_path}")
                sandbox_runner(f'mv "{backup_path}" "{file_path}" 2>/dev/null || true', None, 10)
                return False

            # Clean up backup on success
            sandbox_runner(f'rm -f "{backup_path}"', None, 10)

            logger.info(f"[DockerInfraFixer] Successfully wrote {file_path}")
            return True

        except Exception as e:
            logger.warning(f"[DockerInfraFixer] Failed to write {file_path}: {e}")
            # Try to restore backup
            sandbox_runner(f'mv "{backup_path}" "{file_path}" 2>/dev/null || true', None, 10)
            return False

    def _file_exists_in_sandbox(self, file_path: str, sandbox_runner: callable) -> bool:
        """Check if a file exists in the sandbox."""
        try:
            exit_code, output = sandbox_runner(f'test -f "{file_path}" && echo "EXISTS"', None, 10)
            return exit_code == 0 and "EXISTS" in output
        except Exception:
            return False

    async def _validate_and_fix_compose(self, project_path: str, sandbox_runner: callable) -> List[FixResult]:
        """Validate and fix docker-compose.yml issues (works with remote sandbox).

        CONSERVATIVE APPROACH: Only fix known issues, preserve all other settings.
        We use targeted string replacements when possible to avoid YAML reformatting.
        """
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

            original_content = content  # Keep original for comparison
            data = yaml.safe_load(content)
            modified = False
            changes = []

            if not isinstance(data, dict):
                return fixes

            # Fix depends_on format - convert dict format to simple list
            for service_name, service in data.get('services', {}).items():
                if not isinstance(service, dict):
                    continue

                # Fix depends_on: convert dict to list format
                if 'depends_on' in service:
                    depends = service['depends_on']
                    if isinstance(depends, dict):
                        # Convert {"db": {"condition": "service_healthy"}} to ["db"]
                        service['depends_on'] = list(depends.keys())
                        modified = True
                        changes.append(f"Fixed depends_on format for {service_name}")
                    elif isinstance(depends, list):
                        # Normalize list items to simple strings
                        normalized = []
                        for item in depends:
                            if isinstance(item, dict):
                                # Extract service name from dict format
                                normalized.extend(item.keys())
                            else:
                                normalized.append(str(item))
                        if normalized != depends:
                            service['depends_on'] = normalized
                            modified = True
                            changes.append(f"Normalized depends_on for {service_name}")

            # Remove top-level networks section to avoid pool overlap issues
            if 'networks' in data:
                networks = data['networks']
                if isinstance(networks, dict):
                    del data['networks']
                    modified = True
                    changes.append("Removed custom networks (prevents pool overlap)")

                    # Also remove network references from services
                    for service_name, service in data.get('services', {}).items():
                        if isinstance(service, dict) and 'networks' in service:
                            del service['networks']
                            changes.append(f"Removed network reference from {service_name}")

            if modified:
                # Use custom YAML dump to preserve formatting as much as possible
                fixed_content = yaml.dump(
                    data,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=1000  # Prevent line wrapping
                )

                logger.info(f"[DockerInfraFixer] Applying compose fixes: {changes}")

                if self._write_file_to_sandbox(compose_file, fixed_content, sandbox_runner):
                    # Verify the file is still valid YAML and has services
                    verify_content = self._read_file_from_sandbox(compose_file, sandbox_runner)
                    if verify_content:
                        try:
                            verify_data = yaml.safe_load(verify_content)
                            if verify_data and 'services' in verify_data:
                                fixes.append(FixResult(
                                    success=True,
                                    message="Fixed docker-compose.yml issues",
                                    file_modified=compose_file,
                                    changes_made="; ".join(changes)
                                ))
                                logger.info(f"[DockerInfraFixer] Successfully fixed compose file: {changes}")
                            else:
                                logger.error(f"[DockerInfraFixer] Compose file missing services after fix")
                        except yaml.YAMLError:
                            logger.error(f"[DockerInfraFixer] Compose file invalid YAML after fix")
                else:
                    logger.warning(f"[DockerInfraFixer] Failed to write fixed compose file")
            else:
                logger.debug(f"[DockerInfraFixer] docker-compose.yml looks valid, no fixes needed")

        except yaml.YAMLError as e:
            # YAML syntax error - try to fix common issues
            logger.warning(f"[DockerInfraFixer] YAML parse error: {e}")
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
