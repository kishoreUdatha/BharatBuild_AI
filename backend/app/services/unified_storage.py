"""
Unified 3-Layer Storage Service for BharatBuild AI

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Sandbox (Runtime)         LAYER 2 — S3/MinIO (Permanent)        │
│  /sandbox/workspace/<project-id>/    s3://bucket/projects/<user>/<proj>/   │
│  • Preview, Run, Build, Test         • All source files                    │
│  • Deleted on idle/close             • Project ZIP, PDFs, diagrams         │
│                                                                             │
│                    LAYER 3 — PostgreSQL (Metadata)                         │
│                    • project_id, user_id, s3_path                          │
│                    • plan_json, file_index, history                        │
└─────────────────────────────────────────────────────────────────────────────┘

FLOW:
1. During generation → Write to Layer 1 (sandbox)
2. Generation complete → Upload to Layer 2 (S3)
3. Store metadata in Layer 3 (PostgreSQL)
4. User opens project → Fetch from Layer 2, load into Layer 1 for preview
"""

import os
import json
import shutil
import zipfile
import asyncio
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, field
from uuid import UUID

from app.services.storage_service import storage_service
from app.core.config import settings
from app.core.logging_config import logger

# Configuration - Use Windows-compatible path on Windows
# NOTE: Must match SANDBOX_PATH in config.py for consistency
import platform
if platform.system() == "Windows":
    _default_sandbox = "C:/tmp/sandbox/workspace"
else:
    _default_sandbox = "/tmp/sandbox/workspace"

SANDBOX_BASE_PATH = os.getenv("SANDBOX_BASE_PATH", _default_sandbox)
S3_WORKSPACE_PREFIX = "workspaces"  # Structure: workspaces/{user_id}/{project_id}/


@dataclass
class FileInfo:
    """Information about a single file"""
    path: str
    name: str
    type: str  # 'file' or 'folder'
    content: Optional[str] = None
    language: str = 'plaintext'
    size_bytes: int = 0
    children: List['FileInfo'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'path': self.path,
            'name': self.name,
            'type': self.type,
            'language': self.language,
        }
        if self.type == 'file':
            result['content'] = self.content or ''
            result['size_bytes'] = self.size_bytes
        elif self.children:
            result['children'] = [c.to_dict() for c in self.children]
        return result


class UnifiedStorageService:
    """
    Unified storage service that manages all 3 layers:
    - Layer 1: Sandbox (runtime, ephemeral)
    - Layer 2: S3/MinIO (permanent files)
    - Layer 3: PostgreSQL (metadata only - handled by SQLAlchemy models)
    """

    def __init__(self):
        self.sandbox_path = Path(SANDBOX_BASE_PATH)
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"UnifiedStorageService initialized. Sandbox: {self.sandbox_path}")

    def _sanitize_xml_content(self, content: str) -> str:
        """
        Sanitize XML content to ensure proper formatting.

        CRITICAL: XML files MUST have <?xml declaration on line 1.
        No whitespace or empty lines are allowed before the XML declaration.
        This fixes Maven "Non-parseable POM" errors caused by:
        - Empty lines before <?xml
        - BOM (Byte Order Mark) characters
        - Leading whitespace
        """
        import re

        # Remove BOM if present
        if content.startswith('\ufeff'):
            content = content[1:]

        # Check if content has XML declaration
        xml_decl_match = re.search(r'<\?xml[^?]*\?>', content)
        if xml_decl_match:
            # Strip everything before the XML declaration
            xml_decl_start = xml_decl_match.start()
            if xml_decl_start > 0:
                # There's content before <?xml - remove leading whitespace/empty lines
                leading_content = content[:xml_decl_start]
                if leading_content.strip() == '':
                    # Only whitespace before <?xml - safe to remove
                    content = content[xml_decl_start:]
                    logger.debug(f"[XMLSanitize] Removed {xml_decl_start} chars of leading whitespace before <?xml")
        else:
            # No XML declaration - just strip leading whitespace for safety
            content = content.lstrip()

        return content

    def _sanitize_source_content(self, content: str, file_path: str) -> str:
        """
        Sanitize source code content to ensure proper formatting.

        Fixes:
        - Empty first line (AI often generates files with leading newlines)
        - Missing trailing newline (POSIX convention)
        - BOM characters
        """
        # Remove BOM if present
        if content.startswith('﻿'):
            content = content[1:]

        # Source file extensions that should start with code on line 1
        source_extensions = {
            '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.c', '.cpp',
            '.h', '.hpp', '.cs', '.rb', '.php', '.swift', '.kt', '.scala', '.vue',
            '.svelte', '.css', '.scss', '.less', '.html', '.json', '.yaml', '.yml',
            '.toml', '.ini', '.cfg', '.properties', '.env', '.sh', '.bash', '.sql',
            '.md', '.txt', '.gradle'
        }

        # Get file extension
        ext = '.' + file_path.rsplit('.', 1)[-1].lower() if '.' in file_path else ''

        # Only sanitize known source files
        if ext in source_extensions or file_path.lower() in {'dockerfile', 'makefile', '.gitignore', '.dockerignore'}:
            # Remove leading empty lines (content should start from line 1)
            content = content.lstrip('\n')
            # Ensure file ends with exactly one newline (POSIX convention)
            content = content.rstrip() + '\n'

        return content

    # ==================== LAYER 1: SANDBOX ====================

    def get_sandbox_path(self, project_id: str, user_id: Optional[str] = None) -> Path:
        """
        Get sandbox workspace path for a project.

        Path structure: /workspaces/{user_id}/{project_id}/

        IMPORTANT: user_id MUST be provided for proper isolation.
        Projects without user_id will be created at root level which is NOT recommended.

        Args:
            project_id: Project UUID
            user_id: User UUID (REQUIRED for proper isolation)

        Returns:
            Path to sandbox workspace
        """
        if user_id:
            return self.sandbox_path / user_id / project_id
        # WARNING: This creates project at root level - not isolated per user!
        logger.warning(f"[Sandbox] DEPRECATED: Creating project {project_id} WITHOUT user_id - project will NOT be in user folder!")
        return self.sandbox_path / project_id

    async def create_sandbox(self, project_id: str, user_id: Optional[str] = None) -> Path:
        """
        Create a sandbox workspace for runtime execution.

        IMPORTANT: user_id MUST be provided for proper project isolation.
        All projects should be under: /workspace/{user_id}/{project_id}/
        """
        if not user_id:
            logger.error(f"[Sandbox] CRITICAL: Creating sandbox WITHOUT user_id for project {project_id}! "
                        f"This will create project at root level, breaking user isolation!")

        sandbox = self.get_sandbox_path(project_id, user_id)
        sandbox.mkdir(parents=True, exist_ok=True)
        # Log the actual path being created for debugging
        logger.info(f"[Sandbox] Created at: {sandbox} (user_id={user_id or 'MISSING!'}, project_id={project_id})")
        return sandbox

    async def write_to_sandbox(
        self,
        project_id: str,
        file_path: str,
        content: str,
        user_id: Optional[str] = None
    ) -> bool:
        """
        Write a file to the sandbox workspace.

        - If SANDBOX_DOCKER_HOST is set: Writes to remote EC2 sandbox via Docker
        - Otherwise: Writes to local sandbox path

        Args:
            project_id: Project UUID
            file_path: Relative file path
            content: File content
            user_id: User ID for path scoping

        Returns:
            True if file was written successfully
        """
        try:
            # Prevent path traversal
            if '..' in file_path:
                logger.error(f"[Sandbox] Path traversal detected: {file_path}")
                raise ValueError("Path traversal detected")

            # SANITIZE XML FILES: Ensure <?xml declaration is on line 1
            if file_path.endswith('.xml') or file_path.endswith('.pom'):
                content = self._sanitize_xml_content(content)
            else:
                # SANITIZE ALL SOURCE FILES: Remove leading empty lines
                content = self._sanitize_source_content(content, file_path)

            # Check if using remote EC2 sandbox
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
            if sandbox_docker_host:
                # Write to REMOTE EC2 sandbox using Docker
                logger.debug(f"[Sandbox] Using remote EC2 sandbox: {sandbox_docker_host}")
                return await self._write_to_remote_sandbox(project_id, file_path, content, user_id)

            # Local sandbox (ECS or development)
            sandbox = self.get_sandbox_path(project_id, user_id)
            full_path = sandbox / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"[Sandbox] ✓ Wrote to local sandbox: {user_id or 'anon'}/{project_id}/{file_path} ({len(content)} bytes)")
            return True

        except Exception as e:
            logger.error(f"[Sandbox] ✗ Failed to write {file_path}: {e}", exc_info=True)
            return False

    async def _write_to_remote_sandbox(
        self,
        project_id: str,
        file_path: str,
        content: str,
        user_id: Optional[str] = None,
        max_retries: int = 3
    ) -> bool:
        """
        Write a file to REMOTE EC2 sandbox using Docker container with retry logic.

        Uses alpine container with base64 encoding to handle special characters.
        Volume mount: /tmp/sandbox/workspace on EC2 host.

        Retry behavior:
            - Retries on Docker API errors and connection errors
            - Exponential backoff: 1s, 2s, 4s...
            - Max 3 retries by default

        Args:
            project_id: Project UUID
            file_path: Relative file path
            content: File content
            user_id: User ID for path scoping
            max_retries: Maximum retry attempts

        Returns:
            True if file was written successfully to EC2
        """
        import docker
        import base64
        import asyncio

        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")

        # Build workspace path on EC2
        if user_id:
            workspace_path = f"/tmp/sandbox/workspace/{user_id}/{project_id}"
        else:
            workspace_path = f"/tmp/sandbox/workspace/{project_id}"

        full_path = f"{workspace_path}/{file_path}"
        dir_path = "/".join(full_path.rsplit("/", 1)[:-1]) if "/" in file_path else workspace_path

        last_exception = None

        for attempt in range(max_retries):
            try:
                # Connect to remote Docker on EC2
                docker_client = docker.DockerClient(base_url=sandbox_docker_host)

                # Encode content as base64 to handle special characters safely
                content_b64 = base64.b64encode(content.encode('utf-8')).decode('ascii')

                # Create directory and write file using alpine container
                # Using printf instead of echo for better compatibility
                write_script = f"mkdir -p {dir_path} && printf '%s' '{content_b64}' | base64 -d > {full_path}"

                try:
                    docker_client.containers.run(
                        image="alpine:latest",
                        command=f"sh -c \"{write_script}\"",
                        volumes={"/tmp/sandbox/workspace": {"bind": "/tmp/sandbox/workspace", "mode": "rw"}},
                        remove=True,
                        detach=False,
                    )
                except docker.errors.ImageNotFound:
                    logger.warning("[RemoteWrite] Alpine image not found, pulling...")
                    docker_client.images.pull("alpine:latest")
                    # Retry after pulling
                    docker_client.containers.run(
                        image="alpine:latest",
                        command=f"sh -c \"{write_script}\"",
                        volumes={"/tmp/sandbox/workspace": {"bind": "/tmp/sandbox/workspace", "mode": "rw"}},
                        remove=True,
                        detach=False,
                    )

                logger.info(f"[RemoteWrite] ✓ Wrote to EC2 sandbox: {user_id or 'anon'}/{project_id}/{file_path} ({len(content)} bytes)")
                return True

            except docker.errors.ContainerError as ce:
                last_exception = ce
                error_msg = ce.stderr.decode() if ce.stderr else str(ce)
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"[RemoteWrite] Attempt {attempt + 1}/{max_retries} failed for {file_path}: {error_msg}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[RemoteWrite] ✗ All {max_retries} attempts failed for {file_path}: {error_msg}")

            except docker.errors.APIError as ae:
                last_exception = ae
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"[RemoteWrite] Attempt {attempt + 1}/{max_retries} Docker API error for {file_path}: {ae}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[RemoteWrite] ✗ All {max_retries} attempts failed for {file_path}: {ae}")

            except (ConnectionError, TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = 1.0 * (2 ** attempt)
                    logger.warning(f"[RemoteWrite] Attempt {attempt + 1}/{max_retries} connection error for {file_path}: {e}. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[RemoteWrite] ✗ All {max_retries} attempts failed for {file_path}: {e}")

            except Exception as e:
                logger.error(f"[RemoteWrite] ✗ Unexpected error for {file_path}: {e}", exc_info=True)
                return False

        # All retries exhausted
        logger.error(f"[RemoteWrite] ✗ Failed to write to EC2 sandbox after {max_retries} attempts: {file_path}")
        return False

    async def read_from_sandbox(
        self,
        project_id: str,
        file_path: str,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """Read a file from the sandbox workspace"""
        try:
            sandbox = self.get_sandbox_path(project_id, user_id)
            full_path = sandbox / file_path

            if not full_path.exists():
                return None

            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read from sandbox: {e}")
            return None

    async def list_sandbox_files(
        self,
        project_id: str,
        user_id: Optional[str] = None
    ) -> List[FileInfo]:
        """List all files in the sandbox as a hierarchical tree"""
        sandbox = self.get_sandbox_path(project_id, user_id)

        if not sandbox.exists():
            return []

        return self._build_file_tree(sandbox, sandbox)

    # Directories to skip when building file tree (large/binary/generated)
    SKIP_DIRS = {'node_modules', '__pycache__', '.git', 'dist', 'build', '.next', 'venv', '.venv', 'target'}

    def _build_file_tree(self, base_path: Path, current_path: Path) -> List[FileInfo]:
        """Recursively build file tree structure"""
        items = []

        try:
            for item in sorted(current_path.iterdir()):
                # Skip hidden files
                if item.name.startswith('.'):
                    continue

                # Skip large/binary directories
                if item.is_dir() and item.name in self.SKIP_DIRS:
                    continue

                relative_path = str(item.relative_to(base_path)).replace("\\", "/")

                if item.is_dir():
                    children = self._build_file_tree(base_path, item)
                    items.append(FileInfo(
                        path=relative_path,
                        name=item.name,
                        type='folder',
                        children=children
                    ))
                else:
                    language = self._detect_language(item.name)
                    try:
                        size = item.stat().st_size
                    except OSError:
                        # Skip files that can't be accessed (locked by other process)
                        continue
                    items.append(FileInfo(
                        path=relative_path,
                        name=item.name,
                        type='file',
                        language=language,
                        size_bytes=size
                    ))
        except (PermissionError, OSError) as e:
            # OSError includes WinError 1920 (file locked by another process)
            # This commonly happens with node_modules/.bin files on Windows
            pass

        return items

    async def delete_sandbox(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Delete the sandbox workspace (called on idle/close)"""
        try:
            sandbox = self.get_sandbox_path(project_id, user_id)
            if sandbox.exists():
                shutil.rmtree(sandbox)
                logger.info(f"Deleted sandbox for project {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete sandbox: {e}")
            return False

    async def sandbox_exists(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Check if sandbox exists for a project (on EC2 if SANDBOX_DOCKER_HOST is set)"""
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if sandbox_docker_host:
            return await self._sandbox_exists_remote(project_id, user_id)
        return self.get_sandbox_path(project_id, user_id).exists()

    async def _sandbox_exists_remote(self, project_id: str, user_id: Optional[str] = None) -> bool:
        """Check if sandbox exists on REMOTE EC2"""
        import docker
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        workspace_path = f"/tmp/sandbox/workspace/{user_id}/{project_id}" if user_id else f"/tmp/sandbox/workspace/{project_id}"
        try:
            docker_client = docker.DockerClient(base_url=sandbox_docker_host)
            result = docker_client.containers.run(
                image="alpine:latest",
                command=f"sh -c '[ -d {workspace_path} ] && [ \"$(ls -A {workspace_path})\" ] && echo EXISTS || echo MISSING'",
                volumes={"/tmp/sandbox/workspace": {"bind": "/tmp/sandbox/workspace", "mode": "ro"}},
                remove=True, detach=False,
            )
            return result.decode().strip() == "EXISTS" if result else False
        except Exception as e:
            logger.warning(f"[RemoteCheck] Failed to check EC2 sandbox: {e}")
            return False

    # ==================== LAYER 2: S3/MINIO ====================

    def get_s3_prefix(self, user_id: str, project_id: str) -> str:
        """Get S3 prefix for a project: workspaces/<user-id>/<project-id>/"""
        return f"{S3_WORKSPACE_PREFIX}/{user_id}/{project_id}"

    async def upload_to_s3(
        self,
        user_id: str,
        project_id: str,
        file_path: str,
        content: str
    ) -> Dict[str, Any]:
        """Upload a single file to S3 (Layer 2)"""
        s3_key = f"{self.get_s3_prefix(user_id, project_id)}/{file_path}"
        content_bytes = content.encode('utf-8')

        result = await storage_service.upload_file(
            project_id=project_id,
            file_path=file_path,
            content=content_bytes
        )

        return {
            's3_key': result.get('s3_key'),
            'content_hash': result.get('content_hash'),
            'size_bytes': result.get('size_bytes'),
            'path': file_path
        }

    async def download_from_s3(self, s3_key: str) -> Optional[str]:
        """Download a file from S3"""
        content_bytes = await storage_service.download_file(s3_key)
        if content_bytes:
            return content_bytes.decode('utf-8')
        return None

    async def upload_content(
        self,
        content: bytes,
        key: str,
        content_type: str = 'text/plain'
    ) -> Dict[str, Any]:
        """
        Upload raw content directly to S3.

        Used by SimpleFixer to sync fixed files back to S3.

        Args:
            content: Raw bytes to upload
            key: S3 key (e.g., 'projects/{project_id}/{file_path}')
            content_type: MIME type of the content

        Returns:
            Dict with upload details
        """
        try:
            # Extract project_id and file_path from key
            # Expected format: projects/{project_id}/{file_path}
            parts = key.split('/', 2)
            if len(parts) >= 3:
                project_id = parts[1]
                file_path = parts[2]
            else:
                project_id = "unknown"
                file_path = key

            # Use storage_service to upload
            result = await storage_service.upload_file(
                project_id=project_id,
                file_path=file_path,
                content=content
            )

            logger.info(f"[UnifiedStorage] Uploaded content to S3: {key}")
            return {
                's3_key': result.get('s3_key', key),
                'content_hash': result.get('content_hash'),
                'size_bytes': len(content)
            }
        except Exception as e:
            logger.error(f"[UnifiedStorage] Failed to upload content to S3: {e}")
            raise

    async def upload_project_to_s3(
        self,
        user_id: str,
        project_id: str,
        files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Upload all project files to S3"""
        uploaded = []
        errors = []

        for file_data in files:
            try:
                result = await self.upload_to_s3(
                    user_id=user_id,
                    project_id=project_id,
                    file_path=file_data['path'],
                    content=file_data['content']
                )
                uploaded.append(result)
            except Exception as e:
                errors.append({'path': file_data['path'], 'error': str(e)})

        return {
            'uploaded': len(uploaded),
            'errors': len(errors),
            'files': uploaded,
            's3_prefix': self.get_s3_prefix(user_id, project_id)
        }

    async def create_and_upload_zip(
        self,
        user_id: str,
        project_id: str,
        source_path: Optional[Path] = None
    ) -> Optional[str]:
        """Create ZIP from sandbox and upload to S3"""
        if source_path is None:
            source_path = self.get_sandbox_path(project_id, user_id)

        if not source_path.exists():
            return None

        # Create ZIP
        zip_path = self.sandbox_path / f"{project_id}.zip"

        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in source_path.rglob('*'):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        arcname = file_path.relative_to(source_path)
                        zf.write(file_path, arcname)

            # Upload ZIP to S3
            with open(zip_path, 'rb') as f:
                zip_content = f.read()

            s3_key = f"{self.get_s3_prefix(user_id, project_id)}/project.zip"

            await storage_service.upload_file(
                project_id=project_id,
                file_path="project.zip",
                content=zip_content,
                content_type='application/zip'
            )

            # Clean up local ZIP
            zip_path.unlink()

            logger.info(f"Created and uploaded ZIP for project {project_id}")
            return s3_key

        except Exception as e:
            logger.error(f"Failed to create/upload ZIP: {e}")
            if zip_path.exists():
                zip_path.unlink()
            return None

    async def get_download_url(self, user_id: str, project_id: str) -> Optional[str]:
        """Get presigned download URL for project ZIP"""
        s3_key = f"{self.get_s3_prefix(user_id, project_id)}/project.zip"
        try:
            return await storage_service.get_presigned_url(s3_key)
        except Exception as e:
            logger.error(f"Failed to get download URL: {e}")
            return None

    # ==================== UNIFIED OPERATIONS ====================

    async def load_project_for_editing(
        self,
        user_id: str,
        project_id: str,
        s3_prefix: Optional[str] = None,
        file_index: Optional[List[Dict]] = None
    ) -> List[FileInfo]:
        """
        Load project files for editing in the UI.

        Priority order:
        1. Check Layer 1 (sandbox) - if active, use it
        2. Fetch from Layer 2 (S3) - permanent storage

        Returns hierarchical file tree with content.
        """
        # Check if sandbox exists (project is actively being edited)
        if await self.sandbox_exists(project_id, user_id):
            logger.info(f"Loading project {project_id} from sandbox (Layer 1)")
            files = await self.list_sandbox_files(project_id, user_id)
            # Add content to files
            for file_info in self._flatten_tree(files):
                if file_info.type == 'file':
                    file_info.content = await self.read_from_sandbox(project_id, file_info.path, user_id)
            return files

        # Fetch from S3 (Layer 2)
        if file_index and s3_prefix:
            logger.info(f"Loading project {project_id} from S3 (Layer 2)")
            return await self._load_from_s3(project_id, s3_prefix, file_index, user_id)

        # No files found
        logger.warning(f"No files found for project {project_id}")
        return []

    async def _load_from_s3(
        self,
        project_id: str,
        s3_prefix: str,
        file_index: List[Dict],
        user_id: Optional[str] = None
    ) -> List[FileInfo]:
        """Load files from S3 based on file index"""
        # Create sandbox and populate from S3
        await self.create_sandbox(project_id, user_id)

        files = []
        for file_info in file_index:
            if file_info.get('is_folder') or file_info.get('type') == 'folder':
                continue

            s3_key = file_info.get('s3_key')
            if s3_key:
                content = await self.download_from_s3(s3_key)
                if content:
                    # Write to sandbox for editing
                    await self.write_to_sandbox(project_id, file_info['path'], content, user_id)

        # Return tree from sandbox
        return await self.list_sandbox_files(project_id, user_id)

    async def save_project(
        self,
        user_id: str,
        project_id: str,
        persist_to_s3: bool = True
    ) -> Dict[str, Any]:
        """
        Save project from sandbox (Layer 1) to S3 (Layer 2).

        Returns metadata for Layer 3 (PostgreSQL).
        """
        sandbox = self.get_sandbox_path(project_id, user_id)

        if not sandbox.exists():
            return {'success': False, 'error': 'Sandbox not found'}

        files = await self.list_sandbox_files(project_id, user_id)
        flat_files = self._flatten_tree(files)

        # Collect file data
        file_index = []
        total_size = 0

        for file_info in flat_files:
            if file_info.type == 'file':
                content = await self.read_from_sandbox(project_id, file_info.path, user_id)
                size = len(content.encode('utf-8')) if content else 0

                file_entry = {
                    'path': file_info.path,
                    'name': file_info.name,
                    'language': file_info.language,
                    'size_bytes': size,
                    'is_folder': False
                }

                if persist_to_s3 and content:
                    # Upload to S3
                    result = await self.upload_to_s3(user_id, project_id, file_info.path, content)
                    file_entry['s3_key'] = result.get('s3_key')
                    file_entry['content_hash'] = result.get('content_hash')

                file_index.append(file_entry)
                total_size += size

        # Create ZIP
        zip_key = None
        if persist_to_s3:
            zip_key = await self.create_and_upload_zip(user_id, project_id)

        # Return metadata for Layer 3
        return {
            'success': True,
            'project_id': project_id,
            's3_prefix': self.get_s3_prefix(user_id, project_id),
            'zip_s3_key': zip_key,
            'file_index': file_index,
            'total_files': len(file_index),
            'total_size_bytes': total_size,
            'saved_at': datetime.utcnow().isoformat()
        }

    def _flatten_tree(self, files: List[FileInfo]) -> List[FileInfo]:
        """Flatten hierarchical file tree"""
        result = []
        for f in files:
            result.append(f)
            if f.children:
                result.extend(self._flatten_tree(f.children))
        return result

    def _detect_language(self, filename: str) -> str:
        """Detect language from file extension"""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        language_map = {
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'py': 'python',
            'java': 'java',
            'go': 'go',
            'rs': 'rust',
            'rb': 'ruby',
            'php': 'php',
            'html': 'html',
            'css': 'css',
            'scss': 'scss',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sql': 'sql',
            'sh': 'shell',
        }
        return language_map.get(ext, 'plaintext')

    # ==================== LAYER 3: DATABASE PERSISTENCE ====================

    async def save_to_database(
        self,
        project_id: str,
        file_path: str,
        content: str,
        language: Optional[str] = None
    ) -> bool:
        """
        Save file metadata to PostgreSQL database, content to S3 (Layer 3).

        This enables project recovery after sandbox cleanup.
        - Content: Always stored in S3 FIRST (verified before DB commit)
        - Metadata: Stored in PostgreSQL (path, name, size, hash, s3_key)

        CRITICAL: S3 upload is verified before database commit.
        If S3 upload fails, database is NOT updated (transaction rollback).

        Args:
            project_id: Project UUID string
            file_path: Relative file path
            content: File content
            language: Optional language override

        Returns:
            True if BOTH S3 upload AND database save succeeded
        """
        s3_key = None
        s3_upload_verified = False

        try:
            # Import here to avoid circular imports
            from app.core.database import AsyncSessionLocal
            from app.models.project_file import ProjectFile
            from sqlalchemy import select

            # Validate project_id format (convert to UUID and back to string)
            # GUID column is String(36), so we need string, not UUID object
            try:
                project_uuid = str(UUID(project_id))  # Validate format, keep as string
                logger.debug(f"[Layer3-DB] Validated project_id: {project_uuid}")
            except ValueError as ve:
                logger.error(f"[Layer3-DB] Invalid project_id format: '{project_id}' - {ve}")
                return False

            # Calculate file metadata
            content_bytes = content.encode('utf-8')
            size_bytes = len(content_bytes)
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            file_name = file_path.split('/')[-1]
            parent_path = '/'.join(file_path.split('/')[:-1]) or None

            # Detect language if not provided
            if not language:
                language = self._detect_language(file_name)

            # ==================== STEP 1: UPLOAD TO S3 FIRST ====================
            # S3 upload MUST succeed before we touch the database
            try:
                logger.info(f"[Layer3-S3] Uploading to S3: {project_id}/{file_path} ({size_bytes} bytes)")
                upload_result = await storage_service.upload_file(
                    project_id,
                    file_path,
                    content_bytes
                )
                s3_key = upload_result.get('s3_key')

                # VERIFY S3 upload succeeded
                if not s3_key:
                    logger.error(f"[Layer3-S3] ✗ S3 upload returned no s3_key for {file_path}")
                    return False

                # Verify the key format is correct
                if not s3_key.startswith('projects/'):
                    logger.error(f"[Layer3-S3] ✗ Invalid s3_key format: {s3_key}")
                    return False

                s3_upload_verified = True
                logger.info(f"[Layer3-S3] ✓ Uploaded: {s3_key}")

            except Exception as s3_err:
                logger.error(f"[Layer3-S3] ✗ S3 upload FAILED for {file_path}: {s3_err}", exc_info=True)
                return False

            # ==================== STEP 2: SAVE METADATA TO DATABASE ====================
            # Only proceed if S3 upload was verified
            if not s3_upload_verified:
                logger.error(f"[Layer3-DB] Skipping database save - S3 upload not verified for {file_path}")
                return False

            async with AsyncSessionLocal() as session:
                try:
                    # Check if file already exists - cast to string to handle UUID/VARCHAR mismatch
                    from sqlalchemy import cast, String as SQLString
                    result = await session.execute(
                        select(ProjectFile)
                        .where(cast(ProjectFile.project_id, SQLString(36)) == project_uuid)
                        .where(ProjectFile.path == file_path)
                    )
                    existing_file = result.scalar_one_or_none()

                    content_inline = None  # Never store content inline
                    is_inline = False  # Always use S3

                    if existing_file:
                        # Update existing file
                        old_s3_key = existing_file.s3_key

                        existing_file.content_inline = content_inline
                        existing_file.s3_key = s3_key
                        existing_file.content_hash = content_hash
                        existing_file.size_bytes = size_bytes
                        existing_file.is_inline = is_inline
                        existing_file.language = language

                        logger.debug(f"[Layer3-DB] Updating existing file record: {file_path}")

                        # Delete old S3 file if storage method changed
                        if old_s3_key and old_s3_key != s3_key:
                            try:
                                await storage_service.delete_file(old_s3_key)
                                logger.debug(f"[Layer3-S3] Deleted old S3 file: {old_s3_key}")
                            except Exception:
                                pass  # Ignore cleanup errors
                    else:
                        # Create new file record
                        new_file = ProjectFile(
                            project_id=project_uuid,
                            path=file_path,
                            name=file_name,
                            language=language,
                            s3_key=s3_key,
                            content_hash=content_hash,
                            size_bytes=size_bytes,
                            content_inline=content_inline,
                            is_inline=is_inline,
                            is_folder=False,
                            parent_path=parent_path
                        )
                        session.add(new_file)
                        logger.debug(f"[Layer3-DB] Creating new file record: {file_path}")

                        # Create parent folders if needed
                        await self._ensure_parent_folders_db(session, project_uuid, file_path)

                    # Commit transaction
                    await session.commit()
                    logger.info(f"[Layer3-DB] ✓ Saved metadata: {project_id}/{file_path} (s3_key={s3_key[:50]}...)")
                    return True

                except Exception as db_err:
                    # Rollback on database error
                    await session.rollback()
                    logger.error(f"[Layer3-DB] ✗ Database error for {file_path}, rolled back: {db_err}", exc_info=True)

                    # NOTE: S3 file is orphaned at this point, but that's acceptable
                    # as orphaned files can be cleaned up later, and content is preserved
                    return False

        except Exception as e:
            logger.error(f"[Layer3-DB] ✗ Unexpected error saving {file_path}: {e}", exc_info=True)
            return False

    async def _ensure_parent_folders_db(self, session, project_uuid: str, file_path: str):
        """Create parent folder records in database if they don't exist"""
        from app.models.project_file import ProjectFile
        from sqlalchemy import select

        parts = file_path.split('/')
        if len(parts) <= 1:
            return

        current_path = ''
        for part in parts[:-1]:  # Exclude the file itself
            current_path = f"{current_path}/{part}" if current_path else part

            # Check if folder exists - cast to string to handle UUID/VARCHAR mismatch
            from sqlalchemy import cast, String as SQLString
            result = await session.execute(
                select(ProjectFile)
                .where(cast(ProjectFile.project_id, SQLString(36)) == project_uuid)
                .where(ProjectFile.path == current_path)
            )
            existing = result.scalar_one_or_none()

            if not existing:
                folder = ProjectFile(
                    project_id=project_uuid,
                    path=current_path,
                    name=part,
                    is_folder=True,
                    is_inline=True,
                    size_bytes=0
                )
                session.add(folder)

    async def get_file_from_database(self, project_id: str, file_path: str) -> Optional[str]:
        """
        Retrieve file content from database (Layer 3).

        Used for project recovery when sandbox is cleaned up.

        Args:
            project_id: Project UUID string
            file_path: Relative file path

        Returns:
            File content or None if not found
        """
        try:
            from app.core.database import AsyncSessionLocal
            from app.models.project_file import ProjectFile
            from sqlalchemy import select

            # Validate format, keep as string for String(36) column
            project_uuid = str(UUID(project_id))

            async with AsyncSessionLocal() as session:
                # Cast to string to handle UUID/VARCHAR mismatch
                from sqlalchemy import cast, String as SQLString
                result = await session.execute(
                    select(ProjectFile)
                    .where(cast(ProjectFile.project_id, SQLString(36)) == project_uuid)
                    .where(ProjectFile.path == file_path)
                )
                file_record = result.scalar_one_or_none()

                if not file_record:
                    return None

                # All content is stored in S3
                if file_record.s3_key:
                    content_bytes = await storage_service.download_file(file_record.s3_key)
                    return content_bytes.decode('utf-8') if content_bytes else None

                # Fallback for legacy inline content (migration support)
                if file_record.content_inline:
                    return file_record.content_inline

                return None

        except Exception as e:
            logger.error(f"[Layer3-DB] Failed to get {file_path}: {e}")
            return None

    async def restore_project_from_database(self, project_id: str, user_id: Optional[str] = None) -> List[FileInfo]:
        """
        Restore project files from database to sandbox.

        Call this when a user opens a project whose sandbox was cleaned up.

        Args:
            project_id: Project UUID string
            user_id: User UUID string (for user-scoped paths)

        Returns:
            List of restored files
        """
        try:
            # Check if using remote sandbox - files must be restored ON the sandbox EC2
            sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
            if sandbox_docker_host:
                logger.info(f"[Layer3-DB] Remote sandbox detected, restoring to remote sandbox for {project_id}")
                return await self._restore_to_remote_sandbox(project_id, user_id)

            from app.core.database import AsyncSessionLocal
            from app.models.project_file import ProjectFile
            from sqlalchemy import select

            # Validate format, keep as string for String(36) column
            project_uuid = str(UUID(project_id))
            restored_files = []

            async with AsyncSessionLocal() as session:
                # Get all files for project - cast to string to handle UUID/VARCHAR mismatch
                from sqlalchemy import cast, String as SQLString
                result = await session.execute(
                    select(ProjectFile)
                    .where(cast(ProjectFile.project_id, SQLString(36)) == project_uuid)
                    .where(ProjectFile.is_folder == False)
                    .order_by(ProjectFile.path)
                )
                files = result.scalars().all()

                if not files:
                    logger.info(f"[Layer3-DB] No files to restore for project {project_id}")
                    return []

                # Create sandbox with user-scoped path
                await self.create_sandbox(project_id, user_id)

                # Restore each file
                for file_record in files:
                    content = None

                    # All content is stored in S3
                    if file_record.s3_key:
                        content_bytes = await storage_service.download_file(file_record.s3_key)
                        content = content_bytes.decode('utf-8') if content_bytes else None
                    # Fallback for legacy inline content (migration support)
                    elif file_record.content_inline:
                        content = file_record.content_inline

                    if content:
                        await self.write_to_sandbox(project_id, file_record.path, content, user_id)
                        restored_files.append(FileInfo(
                            path=file_record.path,
                            name=file_record.name,
                            type='file',
                            language=file_record.language or 'plaintext',
                            size_bytes=file_record.size_bytes
                        ))

                logger.info(f"[Layer3-DB] Restored {len(restored_files)} files for project {project_id}")
                return restored_files

        except Exception as e:
            logger.error(f"[Layer3-DB] Failed to restore project {project_id}: {e}")
            return []

    async def _restore_to_remote_sandbox(self, project_id: str, user_id: Optional[str] = None) -> List[FileInfo]:
        """Restore files to REMOTE sandbox EC2 using Docker container with AWS CLI."""
        import docker
        from app.core.database import AsyncSessionLocal
        from app.models.project_file import ProjectFile
        from sqlalchemy import select, cast, String as SQLString

        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        # CRITICAL: Use the SAME bucket as storage_service to ensure consistency
        # storage_service uses settings.effective_bucket_name for uploads
        s3_bucket = settings.effective_bucket_name
        aws_region = settings.AWS_REGION or "ap-south-1"

        logger.info(f"[RemoteRestore] Using S3 bucket: {s3_bucket}, region: {aws_region}")
        workspace_path = f"/tmp/sandbox/workspace/{user_id}/{project_id}" if user_id else f"/tmp/sandbox/workspace/{project_id}"

        try:
            project_uuid = str(UUID(project_id))
            logger.info(f"[RemoteRestore] Querying database for project: {project_uuid}")

            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(ProjectFile).where(cast(ProjectFile.project_id, SQLString(36)) == project_uuid).where(ProjectFile.is_folder == False)
                )
                file_records = result.scalars().all()

            if not file_records:
                logger.warning(f"[RemoteRestore] No files found in database for project {project_id}")
                return []

            # Count files with s3_key
            files_with_s3 = [f for f in file_records if f.s3_key]
            logger.info(f"[RemoteRestore] Found {len(file_records)} files in DB, {len(files_with_s3)} have S3 keys")

            if not files_with_s3:
                logger.error(f"[RemoteRestore] No files have S3 keys! Files were not uploaded to S3.")
                return []

            docker_client = docker.DockerClient(base_url=sandbox_docker_host)
            restore_commands = [f"mkdir -p {workspace_path}"]
            for f in files_with_s3:
                fp = f"{workspace_path}/{f.path}"
                dp = "/".join(fp.rsplit("/", 1)[:-1]) if "/" in f.path else workspace_path
                restore_commands.extend([f"mkdir -p {dp}", f"aws s3 cp s3://{s3_bucket}/{f.s3_key} {fp}"])

            logger.info(f"[RemoteRestore] Restoring {len(files_with_s3)} files to {workspace_path}")
            logger.debug(f"[RemoteRestore] Sample S3 keys: {[f.s3_key for f in files_with_s3[:3]]}")

            # amazon/aws-cli image has entrypoint set to 'aws', so we override it
            # When entrypoint="/bin/sh", command should be ["-c", script] not ["/bin/sh", "-c", script]
            restore_script = ' && '.join(restore_commands)

            try:
                output = docker_client.containers.run(
                    "amazon/aws-cli:latest",
                    ["-c", restore_script],  # Just the args for /bin/sh
                    entrypoint="/bin/sh",    # Override entrypoint to use shell
                    volumes={"/tmp/sandbox/workspace": {"bind": "/tmp/sandbox/workspace", "mode": "rw"}},
                    environment={"AWS_REGION": aws_region},
                    remove=True,
                    detach=False,
                    network_mode="host"
                )
                if output:
                    logger.debug(f"[RemoteRestore] Docker output: {output.decode()[:500]}")
            except docker.errors.ContainerError as ce:
                logger.error(f"[RemoteRestore] Docker container error: {ce.stderr.decode() if ce.stderr else ce}")
                return []
            except docker.errors.ImageNotFound:
                logger.error(f"[RemoteRestore] Docker image 'amazon/aws-cli:latest' not found. Pulling...")
                docker_client.images.pull("amazon/aws-cli:latest")
                # Retry after pulling
                docker_client.containers.run(
                    "amazon/aws-cli:latest",
                    ["-c", restore_script],
                    entrypoint="/bin/sh",
                    volumes={"/tmp/sandbox/workspace": {"bind": "/tmp/sandbox/workspace", "mode": "rw"}},
                    environment={"AWS_REGION": aws_region},
                    remove=True,
                    detach=False,
                    network_mode="host"
                )

            logger.info(f"[RemoteRestore] Successfully restored {len(files_with_s3)} files to EC2 sandbox")
            return [FileInfo(path=f.path, name=f.name, type='file', language=f.language or 'plaintext', size_bytes=f.size_bytes or 0) for f in files_with_s3]
        except Exception as e:
            logger.error(f"[RemoteRestore] Failed to restore project {project_id}: {e}", exc_info=True)
            return []


# Singleton instance
unified_storage = UnifiedStorageService()
