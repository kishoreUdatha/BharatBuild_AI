"""
Unified File Manager - Single source of truth for ALL file operations

This module centralizes all file I/O operations across the application:
- Works with both local and remote (EC2) sandboxes
- Automatic project structure detection and path prefixing
- Syncs to S3 for persistence
- Used by all agents (BoltInstantAgent, CoderAgent, DynamicOrchestrator, etc.)

IMPORTANT: All file operations in the codebase should go through this manager.
Do NOT use direct open(), Path.write_text(), or other file I/O.
"""

import os
import base64
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from app.core.logging_config import logger


class ProjectStructure(Enum):
    """Project structure types"""
    FLAT = "flat"                    # Frontend only at root (package.json at root)
    FULLSTACK = "fullstack"          # frontend/ and backend/ folders
    BACKEND_ONLY = "backend_only"    # Backend only
    MONOREPO = "monorepo"            # Multiple packages


@dataclass
class ProjectConfig:
    """Project configuration for file operations"""
    project_id: str
    user_id: str
    structure: ProjectStructure = ProjectStructure.FLAT
    frontend_path: str = ""          # Empty for flat, "frontend" for fullstack
    backend_path: str = ""           # Empty for none, "backend" for fullstack
    detected_tech: str = ""          # nodejs, python, java, etc.

    # Auto-detected paths
    has_frontend: bool = False
    has_backend: bool = False
    has_database: bool = False


class UnifiedFileManager:
    """
    Centralized file manager for all project file operations.

    Features:
    - Works with local and remote (EC2) sandboxes
    - Automatic path normalization and prefixing
    - Project structure detection
    - S3 sync for persistence

    Usage:
        from app.services.unified_file_manager import file_manager

        # Write a file (auto-detects structure)
        await file_manager.write_file(project_id, user_id, "src/App.tsx", content)

        # For fullstack, specify component
        await file_manager.write_file(project_id, user_id, "src/App.tsx", content, component="frontend")
    """

    # Sandbox base path
    SANDBOX_BASE = "/tmp/sandbox/workspace"

    def __init__(self):
        self._docker_client = None
        self._project_configs: Dict[str, ProjectConfig] = {}

    @property
    def docker_client(self):
        """Lazy load Docker client"""
        if self._docker_client is None:
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
            if sandbox_docker_host:
                try:
                    import docker
                    self._docker_client = docker.DockerClient(
                        base_url=sandbox_docker_host,
                        timeout=30
                    )
                    self._docker_client.ping()
                    logger.info(f"[UnifiedFileManager] Connected to remote Docker: {sandbox_docker_host}")
                except Exception as e:
                    logger.warning(f"[UnifiedFileManager] Remote Docker unavailable: {e}")
        return self._docker_client

    def _is_remote_sandbox(self) -> bool:
        """Check if using remote Docker sandbox"""
        return bool(os.environ.get("SANDBOX_DOCKER_HOST") and self.docker_client)

    def _get_project_path(self, project_id: str, user_id: str) -> str:
        """Get the full sandbox path for a project"""
        return f"{self.SANDBOX_BASE}/{user_id}/{project_id}"

    def _get_config_key(self, project_id: str, user_id: str) -> str:
        """Get cache key for project config"""
        return f"{user_id}:{project_id}"

    # =========================================================================
    # PROJECT STRUCTURE DETECTION
    # =========================================================================

    async def detect_project_structure(
        self,
        project_id: str,
        user_id: str,
        files: List[str] = None
    ) -> ProjectConfig:
        """
        Detect project structure from existing files or file list.

        Args:
            project_id: Project ID
            user_id: User ID
            files: Optional list of file paths to analyze

        Returns:
            ProjectConfig with detected structure
        """
        config_key = self._get_config_key(project_id, user_id)

        # Return cached config if available
        if config_key in self._project_configs:
            return self._project_configs[config_key]

        config = ProjectConfig(
            project_id=project_id,
            user_id=user_id
        )

        # If files provided, analyze them
        if files:
            config = self._analyze_file_list(config, files)
        else:
            # Try to detect from filesystem
            config = await self._analyze_filesystem(config)

        # Cache the config
        self._project_configs[config_key] = config

        logger.info(f"[UnifiedFileManager] Detected structure: {config.structure.value} "
                   f"(frontend={config.has_frontend}, backend={config.has_backend})")

        return config

    def _analyze_file_list(self, config: ProjectConfig, files: List[str]) -> ProjectConfig:
        """Analyze file list to detect structure"""
        files_lower = [f.lower() for f in files]

        # Check for fullstack indicators
        has_frontend_folder = any(f.startswith("frontend/") for f in files)
        has_backend_folder = any(f.startswith("backend/") for f in files)

        # Check for backend tech at root
        has_root_backend = any(f in ["requirements.txt", "pom.xml", "build.gradle", "go.mod", "main.py", "app.py"]
                               for f in files_lower)

        # Check for frontend at root
        has_root_frontend = "package.json" in files_lower or "index.html" in files_lower

        if has_frontend_folder and has_backend_folder:
            config.structure = ProjectStructure.FULLSTACK
            config.frontend_path = "frontend"
            config.backend_path = "backend"
            config.has_frontend = True
            config.has_backend = True
        elif has_frontend_folder:
            config.structure = ProjectStructure.FULLSTACK
            config.frontend_path = "frontend"
            config.has_frontend = True
            config.has_backend = has_root_backend
            if has_root_backend:
                config.backend_path = ""  # Backend at root
        elif has_backend_folder:
            config.structure = ProjectStructure.FULLSTACK
            config.backend_path = "backend"
            config.has_backend = True
            config.has_frontend = has_root_frontend
            if has_root_frontend:
                config.frontend_path = ""  # Frontend at root
        elif has_root_backend and has_root_frontend:
            # Both at root - treat as fullstack but with folders
            config.structure = ProjectStructure.FULLSTACK
            config.frontend_path = "frontend"
            config.backend_path = "backend"
            config.has_frontend = True
            config.has_backend = True
        elif has_root_backend:
            config.structure = ProjectStructure.BACKEND_ONLY
            config.has_backend = True
        else:
            config.structure = ProjectStructure.FLAT
            config.has_frontend = has_root_frontend

        # Detect tech
        if any("requirements.txt" in f or ".py" in f for f in files_lower):
            config.detected_tech = "python"
        elif any("pom.xml" in f or ".java" in f for f in files_lower):
            config.detected_tech = "java"
        elif any("go.mod" in f or ".go" in f for f in files_lower):
            config.detected_tech = "go"
        elif any("package.json" in f for f in files_lower):
            config.detected_tech = "nodejs"

        return config

    async def _analyze_filesystem(self, config: ProjectConfig) -> ProjectConfig:
        """Analyze filesystem to detect structure"""
        project_path = self._get_project_path(config.project_id, config.user_id)

        # Check key paths
        paths_to_check = [
            f"{project_path}/frontend/package.json",
            f"{project_path}/backend/requirements.txt",
            f"{project_path}/backend/pom.xml",
            f"{project_path}/backend/package.json",
            f"{project_path}/package.json",
            f"{project_path}/requirements.txt",
            f"{project_path}/pom.xml",
        ]

        exists_map = await self._check_files_exist(paths_to_check)

        has_frontend_folder = exists_map.get(f"{project_path}/frontend/package.json", False)
        has_backend_folder = any(exists_map.get(f"{project_path}/backend/{f}", False)
                                  for f in ["requirements.txt", "pom.xml", "package.json"])

        if has_frontend_folder and has_backend_folder:
            config.structure = ProjectStructure.FULLSTACK
            config.frontend_path = "frontend"
            config.backend_path = "backend"
            config.has_frontend = True
            config.has_backend = True
        elif has_frontend_folder:
            config.structure = ProjectStructure.FULLSTACK
            config.frontend_path = "frontend"
            config.has_frontend = True
        elif has_backend_folder:
            config.structure = ProjectStructure.FULLSTACK
            config.backend_path = "backend"
            config.has_backend = True
        elif exists_map.get(f"{project_path}/package.json", False):
            config.structure = ProjectStructure.FLAT
            config.has_frontend = True

        return config

    async def _check_files_exist(self, paths: List[str]) -> Dict[str, bool]:
        """Check multiple paths for existence"""
        result = {}

        if not self._is_remote_sandbox():
            for path in paths:
                result[path] = os.path.exists(path)
            return result

        # Remote mode - batch check
        try:
            check_script = " && ".join([f'test -f "{p}" && echo "{p}:EXISTS"' for p in paths])
            output = self.docker_client.containers.run(
                "alpine:latest",
                ["-c", f'{check_script} || true'],
                entrypoint="/bin/sh",
                volumes={self.SANDBOX_BASE: {"bind": self.SANDBOX_BASE, "mode": "ro"}},
                remove=True,
                detach=False
            )

            output_str = output.decode() if isinstance(output, bytes) else str(output)
            for path in paths:
                result[path] = f"{path}:EXISTS" in output_str

        except Exception as e:
            logger.warning(f"[UnifiedFileManager] Failed to check paths: {e}")
            for path in paths:
                result[path] = False

        return result

    # =========================================================================
    # FILE OPERATIONS
    # =========================================================================

    def set_project_structure(
        self,
        project_id: str,
        user_id: str,
        structure: ProjectStructure,
        frontend_path: str = "frontend",
        backend_path: str = "backend"
    ):
        """
        Explicitly set project structure (call before generating files).

        Args:
            project_id: Project ID
            user_id: User ID
            structure: Project structure type
            frontend_path: Path prefix for frontend files
            backend_path: Path prefix for backend files
        """
        config = ProjectConfig(
            project_id=project_id,
            user_id=user_id,
            structure=structure,
            frontend_path=frontend_path if structure == ProjectStructure.FULLSTACK else "",
            backend_path=backend_path if structure in [ProjectStructure.FULLSTACK, ProjectStructure.BACKEND_ONLY] else "",
            has_frontend=structure in [ProjectStructure.FLAT, ProjectStructure.FULLSTACK],
            has_backend=structure in [ProjectStructure.BACKEND_ONLY, ProjectStructure.FULLSTACK]
        )

        config_key = self._get_config_key(project_id, user_id)
        self._project_configs[config_key] = config

        logger.info(f"[UnifiedFileManager] Set structure: {structure.value} "
                   f"(frontend={frontend_path}, backend={backend_path})")

    def normalize_path(
        self,
        file_path: str,
        project_id: str,
        user_id: str,
        component: str = None
    ) -> str:
        """
        Normalize file path based on project structure.

        Args:
            file_path: Original file path (e.g., "src/App.tsx" or "package.json")
            project_id: Project ID
            user_id: User ID
            component: Optional component hint ("frontend" or "backend")

        Returns:
            Normalized path with proper prefix
        """
        config_key = self._get_config_key(project_id, user_id)
        config = self._project_configs.get(config_key)

        # No config = flat structure (backward compatibility)
        if not config or config.structure == ProjectStructure.FLAT:
            return file_path

        # Already has proper prefix
        if file_path.startswith("frontend/") or file_path.startswith("backend/"):
            return file_path

        # Component explicitly specified
        if component == "frontend" and config.frontend_path:
            return f"{config.frontend_path}/{file_path}"
        elif component == "backend" and config.backend_path:
            return f"{config.backend_path}/{file_path}"

        # Auto-detect based on file type
        frontend_files = [
            "package.json", "tsconfig.json", "vite.config", "next.config",
            "tailwind.config", "postcss.config", "index.html", ".eslintrc",
            "src/", "public/", "components/", "pages/", "app/", "styles/"
        ]

        backend_files = [
            "requirements.txt", "pom.xml", "build.gradle", "go.mod",
            "main.py", "app.py", "manage.py", "Cargo.toml",
            "src/main/", "cmd/", "internal/", "pkg/"
        ]

        # Check if it's a frontend file
        if any(file_path.startswith(f) or file_path == f for f in frontend_files):
            if config.frontend_path:
                return f"{config.frontend_path}/{file_path}"

        # Check if it's a backend file
        if any(file_path.startswith(f) or file_path == f for f in backend_files):
            if config.backend_path:
                return f"{config.backend_path}/{file_path}"

        # For fullstack with both paths, default to frontend for common web files
        if config.structure == ProjectStructure.FULLSTACK:
            if file_path.endswith(('.tsx', '.jsx', '.ts', '.js', '.css', '.html')):
                if config.frontend_path:
                    return f"{config.frontend_path}/{file_path}"
            elif file_path.endswith(('.py', '.java', '.go', '.rs')):
                if config.backend_path:
                    return f"{config.backend_path}/{file_path}"

        return file_path

    async def write_file(
        self,
        project_id: str,
        user_id: str,
        file_path: str,
        content: str,
        component: str = None,
        normalize: bool = True
    ) -> bool:
        """
        Write a file to the project.

        Args:
            project_id: Project ID
            user_id: User ID
            file_path: File path (will be normalized if needed)
            content: File content
            component: Optional hint ("frontend" or "backend")
            normalize: Whether to normalize path (default True)

        Returns:
            True if successful
        """
        # Normalize path if needed
        if normalize:
            file_path = self.normalize_path(file_path, project_id, user_id, component)

        # Get full path
        project_path = self._get_project_path(project_id, user_id)
        full_path = f"{project_path}/{file_path}"

        logger.info(f"[UnifiedFileManager] Writing: {file_path}")

        try:
            if not self._is_remote_sandbox():
                # Local mode
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True

            # Remote mode - use helper container
            encoded_content = base64.b64encode(content.encode()).decode()

            script = f'''
mkdir -p "$(dirname {full_path})"
echo "{encoded_content}" | base64 -d > "{full_path}"
'''

            self.docker_client.containers.run(
                "alpine:latest",
                ["-c", script],
                entrypoint="/bin/sh",
                volumes={self.SANDBOX_BASE: {"bind": self.SANDBOX_BASE, "mode": "rw"}},
                remove=True,
                detach=False
            )

            return True

        except Exception as e:
            logger.error(f"[UnifiedFileManager] Failed to write {file_path}: {e}")
            return False

    async def read_file(
        self,
        project_id: str,
        user_id: str,
        file_path: str
    ) -> Optional[str]:
        """
        Read a file from the project.

        Returns:
            File content or None if not found
        """
        project_path = self._get_project_path(project_id, user_id)
        full_path = f"{project_path}/{file_path}"

        try:
            if not self._is_remote_sandbox():
                if os.path.exists(full_path):
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                return None

            # Remote mode
            result = self.docker_client.containers.run(
                "alpine:latest",
                ["-c", f'cat "{full_path}" 2>/dev/null || echo "__FILE_NOT_FOUND__"'],
                entrypoint="/bin/sh",
                volumes={self.SANDBOX_BASE: {"bind": self.SANDBOX_BASE, "mode": "ro"}},
                remove=True,
                detach=False
            )

            content = result.decode() if isinstance(result, bytes) else str(result)
            if "__FILE_NOT_FOUND__" in content:
                return None
            return content

        except Exception as e:
            logger.error(f"[UnifiedFileManager] Failed to read {file_path}: {e}")
            return None

    async def file_exists(
        self,
        project_id: str,
        user_id: str,
        file_path: str
    ) -> bool:
        """Check if a file exists"""
        project_path = self._get_project_path(project_id, user_id)
        full_path = f"{project_path}/{file_path}"

        try:
            if not self._is_remote_sandbox():
                return os.path.exists(full_path)

            result = self.docker_client.containers.run(
                "alpine:latest",
                ["-c", f'test -f "{full_path}" && echo "EXISTS" || echo "MISSING"'],
                entrypoint="/bin/sh",
                volumes={self.SANDBOX_BASE: {"bind": self.SANDBOX_BASE, "mode": "ro"}},
                remove=True,
                detach=False
            )

            return b"EXISTS" in result

        except Exception as e:
            logger.warning(f"[UnifiedFileManager] Failed to check {file_path}: {e}")
            return False

    async def delete_file(
        self,
        project_id: str,
        user_id: str,
        file_path: str
    ) -> bool:
        """Delete a file"""
        project_path = self._get_project_path(project_id, user_id)
        full_path = f"{project_path}/{file_path}"

        try:
            if not self._is_remote_sandbox():
                if os.path.exists(full_path):
                    os.remove(full_path)
                return True

            self.docker_client.containers.run(
                "alpine:latest",
                ["-c", f'rm -f "{full_path}"'],
                entrypoint="/bin/sh",
                volumes={self.SANDBOX_BASE: {"bind": self.SANDBOX_BASE, "mode": "rw"}},
                remove=True,
                detach=False
            )

            return True

        except Exception as e:
            logger.error(f"[UnifiedFileManager] Failed to delete {file_path}: {e}")
            return False

    async def list_files(
        self,
        project_id: str,
        user_id: str,
        path: str = ""
    ) -> List[str]:
        """List files in a directory"""
        project_path = self._get_project_path(project_id, user_id)
        full_path = f"{project_path}/{path}" if path else project_path

        try:
            if not self._is_remote_sandbox():
                if os.path.exists(full_path):
                    files = []
                    for root, dirs, filenames in os.walk(full_path):
                        for filename in filenames:
                            rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                            files.append(rel_path.replace("\\", "/"))
                    return files
                return []

            result = self.docker_client.containers.run(
                "alpine:latest",
                ["-c", f'find "{full_path}" -type f 2>/dev/null | head -500'],
                entrypoint="/bin/sh",
                volumes={self.SANDBOX_BASE: {"bind": self.SANDBOX_BASE, "mode": "ro"}},
                remove=True,
                detach=False
            )

            output = result.decode() if isinstance(result, bytes) else str(result)
            files = []
            for line in output.strip().split('\n'):
                if line and line.startswith(project_path):
                    rel_path = line[len(project_path):].lstrip('/')
                    files.append(rel_path)

            return files

        except Exception as e:
            logger.error(f"[UnifiedFileManager] Failed to list files: {e}")
            return []

    async def write_multiple_files(
        self,
        project_id: str,
        user_id: str,
        files: Dict[str, str],
        component: str = None
    ) -> Tuple[int, int]:
        """
        Write multiple files at once.

        Args:
            project_id: Project ID
            user_id: User ID
            files: Dict of {path: content}
            component: Optional hint ("frontend" or "backend")

        Returns:
            Tuple of (success_count, fail_count)
        """
        success = 0
        fail = 0

        for file_path, content in files.items():
            if await self.write_file(project_id, user_id, file_path, content, component):
                success += 1
            else:
                fail += 1

        logger.info(f"[UnifiedFileManager] Wrote {success} files, {fail} failed")
        return success, fail

    def clear_project_config(self, project_id: str, user_id: str):
        """Clear cached project config"""
        config_key = self._get_config_key(project_id, user_id)
        if config_key in self._project_configs:
            del self._project_configs[config_key]


# Singleton instance
unified_file_manager = UnifiedFileManager()
