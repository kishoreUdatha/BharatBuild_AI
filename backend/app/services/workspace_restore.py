"""
Workspace Restoration Service - Bolt.new Style

When a user opens an old project and the sandbox has been cleaned up,
this service can restore the workspace in two ways:

1. RESTORE from Database/S3 (Fast)
   - Read file metadata from ProjectFile table
   - Download content from S3 (all content stored in S3)
   - Fallback to inline content for legacy data
   - Write to sandbox

2. REGENERATE from Plan (Like Bolt.new)
   - Read plan_json from Project table
   - Re-run the writer agent to regenerate all files
   - Creates fresh files based on the original plan
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
import asyncio
from datetime import datetime
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, String

from app.core.logging_config import logger
from app.core.config import settings
from app.models.project import Project
from app.models.project_file import ProjectFile


# =============================================================================
# CRITICAL FILES CONFIGURATION
# =============================================================================
# These files MUST exist for a project to run. If any are missing, restoration fails.

CRITICAL_FILES_BY_TYPE = {
    "node": {
        "required": ["package.json"],  # Must have package.json
        "optional_entry": ["src/index.tsx", "src/index.ts", "src/index.js", "src/App.tsx", "src/App.js", "index.html", "src/main.tsx", "src/main.ts"],
    },
    "vite": {
        "required": ["package.json"],
        "any_of": ["vite.config.ts", "vite.config.js"],  # At least one vite config
        "optional_entry": ["index.html", "src/main.tsx", "src/main.ts", "src/App.tsx"],
    },
    "python": {
        "required": [],  # At least one of these
        "any_of": ["requirements.txt", "pyproject.toml", "setup.py"],
        "optional_entry": ["main.py", "app.py", "app/main.py", "src/main.py"],
    },
    "java": {
        "required": [],
        "any_of": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "optional_entry": ["src/main/java"],
    },
    "go": {
        "required": ["go.mod"],
        "optional_entry": ["main.go", "cmd/main.go"],
    },
    "static": {
        "required": ["index.html"],
        "optional_entry": [],
    },
}

# S3 Retry Configuration
S3_MAX_RETRIES = 3
S3_INITIAL_DELAY = 0.5  # seconds
S3_MAX_DELAY = 4.0  # seconds
S3_BACKOFF_MULTIPLIER = 2.0


@dataclass
class RestoreResult:
    """Result of a workspace restoration operation"""
    success: bool
    method: str = ""
    restored_files: int = 0
    total_files: int = 0
    missing_critical: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    workspace_path: str = ""
    message: str = ""

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "method": self.method,
            "restored_files": self.restored_files,
            "total_files": self.total_files,
            "missing_critical": self.missing_critical if self.missing_critical else None,
            "errors": self.errors if self.errors else None,
            "workspace_path": self.workspace_path,
            "message": self.message,
        }


class WorkspaceRestoreService:
    """
    Service to restore project workspace after sandbox cleanup.

    Two restoration modes:
    - RESTORE: Fast restore from database/S3 storage
    - REGENERATE: Re-run planner/writer from plan_json (Bolt.new style)
    """

    def __init__(self):
        self.sandbox_path = Path(settings.SANDBOX_PATH)

    def _get_workspace_path(self, project_id: str, user_id: str = None) -> Path:
        """
        Get the workspace path for a project.

        Uses user-scoped paths to match container_manager:
        - sandbox_path / user_id / project_id (if user_id provided)
        - sandbox_path / project_id (fallback for backwards compatibility)
        """
        if user_id:
            return self.sandbox_path / user_id / project_id
        return self.sandbox_path / project_id

    async def check_workspace_status(
        self,
        project_id: str,
        db: AsyncSession,
        user_id: str = None
    ) -> Dict:
        """
        Check if a project's workspace exists and what restoration options are available.

        Returns:
            Dict with:
            - exists: bool - workspace exists in sandbox
            - can_restore: bool - can restore from database/S3
            - can_regenerate: bool - can regenerate from plan
            - file_count: int - number of files in database
            - has_plan: bool - has plan_json stored
        """
        # Check database for restoration options (also gets user_id)
        project = await self._get_project(project_id, db)

        # Use user_id from project if not provided
        if not user_id and project:
            user_id = str(project.user_id)

        workspace_path = self._get_workspace_path(project_id, user_id)

        # Check if workspace exists
        exists = workspace_path.exists() and any(workspace_path.iterdir()) if workspace_path.exists() else False

        files = await self._get_project_files(project_id, db) if project else []

        has_plan = project and project.plan_json is not None
        file_count = len(files)
        can_restore = file_count > 0
        can_regenerate = has_plan

        return {
            "project_id": project_id,
            "workspace_exists": exists,
            "can_restore": can_restore,
            "can_regenerate": can_regenerate,
            "file_count": file_count,
            "has_plan": has_plan,
            "restoration_options": self._get_restoration_options(exists, can_restore, can_regenerate)
        }

    def _get_restoration_options(self, exists: bool, can_restore: bool, can_regenerate: bool) -> List[str]:
        """Get available restoration options"""
        options = []
        if exists:
            options.append("workspace_exists")  # No restoration needed
        if can_restore:
            options.append("restore_from_storage")  # Fast restore from DB/S3
        if can_regenerate:
            options.append("regenerate_from_plan")  # Re-run planner/writer
        return options

    async def restore_from_storage(
        self,
        project_id: str,
        db: AsyncSession,
        user_id: str = None,
        progress_callback: Optional[callable] = None,
        strict_mode: bool = True
    ) -> Dict:
        """
        Restore workspace from database/S3 storage with critical file validation.

        This is the FAST method - directly copies stored files to sandbox.

        GUARANTEES (when strict_mode=True):
        - All critical files (package.json, etc.) MUST be restored
        - If any critical file fails, entire restoration fails
        - Uses S3 retry with exponential backoff (3 attempts)

        Args:
            project_id: Project to restore
            db: Database session
            user_id: User ID for user-scoped paths (optional, fetched from project if not provided)
            progress_callback: Optional callback for progress updates
            strict_mode: If True, fail if critical files are missing (default: True)

        Returns:
            Dict with restoration results including critical file validation
        """
        # Get project to find user_id if not provided
        project = await self._get_project(project_id, db)
        if not user_id and project:
            user_id = str(project.user_id)

        workspace_path = self._get_workspace_path(project_id, user_id)

        # Get files from database
        files = await self._get_project_files(project_id, db)

        if not files:
            return RestoreResult(
                success=False,
                method="restore_from_storage",
                message="No files found in storage",
            ).to_dict()

        # Detect project type for critical file validation
        project_type = self._detect_project_type(files)
        logger.info(f"[WorkspaceRestore] Detected project type: {project_type} for {project_id}")

        # Create workspace directory
        workspace_path.mkdir(parents=True, exist_ok=True)

        restored_count = 0
        restored_paths: Set[str] = set()
        errors = []
        critical_failures = []

        # Identify critical files upfront
        config = CRITICAL_FILES_BY_TYPE.get(project_type, CRITICAL_FILES_BY_TYPE["node"])
        critical_files = set(config.get("required", []))
        any_of_files = set(config.get("any_of", []))

        for i, file in enumerate(files):
            is_critical = file.path in critical_files or file.path in any_of_files

            try:
                file_path = workspace_path / file.path

                # Create parent directories
                file_path.parent.mkdir(parents=True, exist_ok=True)

                # Get content - prioritize S3 with retry, fallback to inline for legacy data
                content = None
                if file.s3_key:
                    # Download from S3 with retry
                    content = await self._download_from_s3(file.s3_key)
                    if content is None:
                        error_msg = f"Failed to download {file.path} from S3 after {S3_MAX_RETRIES} retries"
                        if is_critical:
                            critical_failures.append(file.path)
                            logger.error(f"[WorkspaceRestore] CRITICAL FILE FAILED: {file.path}")
                        errors.append(error_msg)
                        continue

                elif file.content_inline:
                    # Legacy fallback for old inline content
                    content = file.content_inline
                else:
                    error_msg = f"No content available for {file.path}"
                    if is_critical:
                        critical_failures.append(file.path)
                    errors.append(error_msg)
                    continue

                # Write file with Gap #18: Windows file locking handling
                write_success = False
                for write_attempt in range(3):
                    try:
                        file_path.write_text(content, encoding='utf-8')
                        write_success = True
                        break
                    except PermissionError as perm_err:
                        # Gap #18: File may be locked by another process (common on Windows)
                        import platform
                        if platform.system() == "Windows" and write_attempt < 2:
                            logger.warning(f"[WorkspaceRestore] File locked, retry {write_attempt + 1}/3: {file.path}")
                            await asyncio.sleep(0.5 * (write_attempt + 1))  # Backoff
                            continue
                        raise perm_err
                    except OSError as os_err:
                        # Handle other OS errors (disk full, etc.)
                        if "WinError" in str(os_err) and write_attempt < 2:
                            logger.warning(f"[WorkspaceRestore] WinError, retry {write_attempt + 1}/3: {file.path}")
                            await asyncio.sleep(0.5 * (write_attempt + 1))
                            continue
                        raise os_err

                if not write_success:
                    error_msg = f"Failed to write {file.path} after 3 attempts (file locked)"
                    if is_critical:
                        critical_failures.append(file.path)
                    errors.append(error_msg)
                    continue

                # Gap #8: Verify written file matches expected hash/size
                if file.content_hash:
                    import hashlib
                    actual_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                    if actual_hash != file.content_hash:
                        error_msg = f"Checksum mismatch for {file.path}: expected {file.content_hash[:8]}..., got {actual_hash[:8]}..."
                        logger.warning(f"[WorkspaceRestore] {error_msg}")
                        if is_critical:
                            critical_failures.append(file.path)
                        errors.append(error_msg)
                        # Don't count as restored if checksum fails
                        continue

                if file.size_bytes:
                    actual_size = len(content.encode('utf-8'))
                    if actual_size != file.size_bytes:
                        logger.warning(f"[WorkspaceRestore] Size mismatch for {file.path}: expected {file.size_bytes}, got {actual_size}")

                restored_count += 1
                restored_paths.add(file.path)

                # Progress callback
                if progress_callback:
                    await progress_callback({
                        "type": "file_restored",
                        "file": file.path,
                        "progress": (i + 1) / len(files) * 100,
                        "is_critical": is_critical
                    })

            except Exception as e:
                error_msg = f"Error restoring {file.path}: {str(e)}"
                if is_critical:
                    critical_failures.append(file.path)
                errors.append(error_msg)
                logger.error(f"[WorkspaceRestore] Error restoring {file.path}: {e}")

        # Validate critical files were restored
        is_valid, missing_critical = self._validate_critical_files(restored_paths, project_type)

        logger.info(
            f"[WorkspaceRestore] Restored {restored_count}/{len(files)} files for {project_id}. "
            f"Critical valid: {is_valid}, Missing: {missing_critical}"
        )

        # Apply common fixes to prevent container startup failures
        fix_result = await self.fix_common_issues(workspace_path, project_id=project_id)
        if fix_result.get("fixes_applied"):
            logger.info(f"[WorkspaceRestore] Applied fixes: {fix_result['fixes_applied']}")

        # Determine success based on strict mode
        if strict_mode:
            # Strict: Fail if any critical files missing
            success = is_valid and restored_count > 0
            if not is_valid:
                message = f"CRITICAL FILES MISSING: {', '.join(missing_critical)}. Restoration failed."
            else:
                message = f"Successfully restored {restored_count} files with all critical files present."
        else:
            # Lenient: Success if at least one file restored
            success = restored_count > 0
            if not is_valid:
                message = f"Restored {restored_count} files but missing critical: {', '.join(missing_critical)}"
            else:
                message = f"Successfully restored {restored_count} files."

        return RestoreResult(
            success=success,
            method="restore_from_storage",
            restored_files=restored_count,
            total_files=len(files),
            missing_critical=missing_critical,
            errors=errors,
            workspace_path=str(workspace_path),
            message=message,
        ).to_dict()

    async def regenerate_from_plan(
        self,
        project_id: str,
        db: AsyncSession,
        user_id: str = None,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        """
        Regenerate workspace by replaying Claude messages (Bolt.new style).

        This is exactly how Bolt.new works:
        1. Load saved plan.json and chat history from DB
        2. Create new empty workspace
        3. Replay Claude messages to regenerate files
        4. Claude generates fresh files (NOT retrieved from storage)

        Args:
            project_id: Project to regenerate
            db: Database session
            user_id: User ID for user-scoped paths (optional, fetched from project if not provided)
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with regeneration info for orchestrator
        """
        # Get project with plan and history
        project = await self._get_project(project_id, db)

        if not project:
            return {
                "success": False,
                "error": "Project not found"
            }

        # Get user_id from project if not provided
        if not user_id:
            user_id = str(project.user_id)

        if not project.plan_json and not project.history:
            return {
                "success": False,
                "error": "No plan or history found - cannot regenerate"
            }

        # Create new empty workspace (Bolt.new step 2)
        workspace_path = self._get_workspace_path(project_id, user_id)
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path)  # Clear any leftover files
        workspace_path.mkdir(parents=True, exist_ok=True)

        # Prepare regeneration context (Bolt.new step 3)
        # This will be sent to the orchestrator to replay
        regeneration_context = {
            "project_id": project_id,
            "plan_json": project.plan_json,
            "history": project.history,  # Claude messages to replay
            "original_request": project.description or project.title,
            "tech_stack": project.tech_stack,
            "framework": project.framework,
            "mode": "regenerate"  # Skip planning, go straight to writing
        }

        return {
            "success": True,
            "mode": "regenerate",
            "regeneration_context": regeneration_context,
            "workspace_path": str(workspace_path),
            "message": "Ready to regenerate - call orchestrator with this context",
            "instructions": {
                "endpoint": "/api/v1/orchestrator/regenerate",
                "method": "POST",
                "body": {
                    "project_id": project_id,
                    "skip_planning": True,
                    "use_saved_plan": True
                }
            }
        }

    def _check_essential_files(self, workspace_path: Path, project_type: str = "node") -> Dict:
        """
        Check if essential files exist in the workspace.

        Essential files by project type:
        - node: package.json
        - python: requirements.txt or main.py or app.py
        - static: index.html

        Returns:
            Dict with:
            - complete: bool - all essential files present
            - missing: List[str] - list of missing essential files
            - found: List[str] - list of found essential files
        """
        essential_files = {
            "node": ["package.json"],
            "python": ["requirements.txt", "main.py", "app.py"],  # Any one of these
            "static": ["index.html"],
        }

        required = essential_files.get(project_type, ["package.json"])

        found = []
        for f in required:
            if (workspace_path / f).exists():
                found.append(f)

        # For python, only one file is required (any of them)
        if project_type == "python":
            is_complete = len(found) > 0
        else:
            is_complete = len(found) == len(required)

        return {
            "complete": is_complete,
            "missing": [f for f in required if f not in found],
            "found": found
        }

    async def auto_restore(
        self,
        project_id: str,
        db: AsyncSession,
        user_id: str = None,
        prefer_regenerate: bool = False,
        project_type: str = "node"
    ) -> Dict:
        """
        Automatically restore workspace using best available method.

        Args:
            project_id: Project to restore
            db: Database session
            user_id: User ID for user-scoped paths (optional, fetched from project if not provided)
            prefer_regenerate: If True, prefer regeneration over restoration
            project_type: Type of project (node, python, static)

        Returns:
            Dict with restoration results
        """
        # =====================================================================
        # CRITICAL: Remote Docker mode handling
        # When SANDBOX_DOCKER_HOST is set, files must be restored to remote EC2
        # not the local ECS filesystem. Delegate to unified_storage's remote restore.
        # =====================================================================
        sandbox_docker_host = os.environ.get("SANDBOX_DOCKER_HOST")
        if sandbox_docker_host:
            logger.info(f"[WorkspaceRestore] Remote Docker mode detected, delegating to unified_storage")
            try:
                from app.services.unified_storage import unified_storage
                # Get user_id from project if not provided
                project = await self._get_project(project_id, db)
                if not user_id and project:
                    user_id = str(project.user_id)

                # Use unified_storage's remote restore which handles EC2 sandbox
                restored_files = await unified_storage._restore_to_remote_sandbox(project_id, user_id)
                if restored_files:
                    return {
                        "success": True,
                        "method": "restore_from_storage",
                        "restored_files": len(restored_files),
                        "total_files": len(restored_files),
                        "message": f"Restored {len(restored_files)} files to remote sandbox"
                    }
                else:
                    return {
                        "success": False,
                        "method": "restore_from_storage",
                        "error": "No files restored to remote sandbox"
                    }
            except Exception as remote_err:
                logger.error(f"[WorkspaceRestore] Remote restore failed: {remote_err}")
                return {
                    "success": False,
                    "method": "restore_from_storage",
                    "error": f"Remote restore failed: {str(remote_err)}"
                }

        status = await self.check_workspace_status(project_id, db, user_id)

        # Get workspace path to check essential files
        project = await self._get_project(project_id, db)
        if not user_id and project:
            user_id = str(project.user_id)
        workspace_path = self._get_workspace_path(project_id, user_id)

        if status["workspace_exists"]:
            # Check if essential files are present
            essential_check = self._check_essential_files(workspace_path, project_type)

            if essential_check["complete"]:
                logger.info(f"[WorkspaceRestore] Workspace exists with essential files: {essential_check['found']}")

                # Apply common fixes even for existing workspaces (prevents container failures)
                fix_result = await self.fix_common_issues(workspace_path, project_id=project_id)
                if fix_result.get("fixes_applied"):
                    logger.info(f"[WorkspaceRestore] Applied fixes to existing workspace: {fix_result['fixes_applied']}")

                return {
                    "success": True,
                    "method": "already_exists",
                    "message": "Workspace already exists with essential files",
                    "workspace_path": str(workspace_path),
                    "fixes_applied": fix_result.get("fixes_applied", [])
                }
            else:
                # Workspace exists but missing essential files - try to restore
                logger.warning(f"[WorkspaceRestore] Workspace incomplete, missing: {essential_check['missing']}")

                # Try to restore missing files from storage
                if status["can_restore"]:
                    logger.info(f"[WorkspaceRestore] Restoring missing files from storage for {project_id}")
                    restore_result = await self.restore_from_storage(project_id, db, user_id)
                    if restore_result.get("success"):
                        return restore_result

                # If can't restore, return with warning
                return {
                    "success": True,  # Workspace exists, just incomplete
                    "method": "incomplete",
                    "message": f"Workspace exists but missing essential files: {essential_check['missing']}",
                    "missing_files": essential_check["missing"],
                    "workspace_path": str(workspace_path)
                }

        if prefer_regenerate and status["can_regenerate"]:
            return await self.regenerate_from_plan(project_id, db, user_id)

        if status["can_restore"]:
            return await self.restore_from_storage(project_id, db, user_id)

        if status["can_regenerate"]:
            return await self.regenerate_from_plan(project_id, db, user_id)

        return {
            "success": False,
            "error": "No restoration method available",
            "status": status
        }

    async def _get_project(self, project_id: str, db: AsyncSession) -> Optional[Project]:
        """Get project from database"""
        try:
            # projects.id is stored as String(36) not UUID
            # Cast column to String(36) to handle UUID/VARCHAR mismatch
            result = await db.execute(
                select(Project).where(cast(Project.id, String(36)) == str(project_id))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"[WorkspaceRestore] Error getting project: {e}")
            return None

    async def _get_project_files(self, project_id: str, db: AsyncSession) -> List[ProjectFile]:
        """Get all files for a project from database"""
        try:
            # project_id in project_files table is stored as varchar, not UUID
            # Cast column to String(36) to handle UUID/VARCHAR mismatch
            result = await db.execute(
                select(ProjectFile).where(cast(ProjectFile.project_id, String(36)) == str(project_id))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"[WorkspaceRestore] Error getting project files: {e}")
            return []

    async def _download_from_s3(self, s3_key: str) -> Optional[str]:
        """
        Download file content from S3/MinIO with retry and exponential backoff.

        Retry Strategy:
        - Max 3 attempts
        - Exponential backoff: 0.5s → 1s → 2s
        - Logs each attempt for debugging
        """
        from app.services.unified_storage import unified_storage

        last_error = None
        delay = S3_INITIAL_DELAY

        for attempt in range(1, S3_MAX_RETRIES + 1):
            try:
                logger.debug(f"[WorkspaceRestore] S3 download attempt {attempt}/{S3_MAX_RETRIES}: {s3_key}")
                content = await unified_storage.download_from_s3(s3_key)

                if content is not None:
                    logger.debug(f"[WorkspaceRestore] S3 download success: {s3_key}")
                    return content.decode('utf-8') if isinstance(content, bytes) else content

                # Content is None but no exception - treat as failure
                last_error = "S3 returned empty content"

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"[WorkspaceRestore] S3 download attempt {attempt}/{S3_MAX_RETRIES} failed: {s3_key} - {e}"
                )

            # Don't wait after the last attempt
            if attempt < S3_MAX_RETRIES:
                logger.debug(f"[WorkspaceRestore] Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * S3_BACKOFF_MULTIPLIER, S3_MAX_DELAY)

        logger.error(f"[WorkspaceRestore] S3 download failed after {S3_MAX_RETRIES} attempts: {s3_key} - {last_error}")
        return None

    def _detect_project_type(self, files: List[ProjectFile]) -> str:
        """
        Detect project type from file list.

        Returns: 'node', 'vite', 'python', 'java', 'go', 'static'
        """
        file_paths = {f.path.lower() for f in files}

        # Check for Vite projects first (more specific)
        if any('vite.config' in p for p in file_paths):
            return 'vite'

        # Check for Node.js
        if 'package.json' in file_paths:
            return 'node'

        # Check for Python
        if any(p in file_paths for p in ['requirements.txt', 'pyproject.toml', 'setup.py']):
            return 'python'

        # Check for Java
        if any(p in file_paths for p in ['pom.xml', 'build.gradle', 'build.gradle.kts']):
            return 'java'

        # Check for Go
        if 'go.mod' in file_paths:
            return 'go'

        # Default to static
        return 'static'

    def _validate_critical_files(
        self,
        restored_files: Set[str],
        project_type: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all critical files were restored.

        Supports both frontend-only and full-stack projects by checking
        critical files at root level AND in common subdirectories.

        Args:
            restored_files: Set of file paths that were restored
            project_type: Type of project (node, python, etc.)

        Returns:
            Tuple of (is_valid, missing_critical_files)
        """
        config = CRITICAL_FILES_BY_TYPE.get(project_type, CRITICAL_FILES_BY_TYPE["node"])

        missing = []

        # Common subdirectories for full-stack projects
        # Full-stack projects often have frontend code in subdirectories
        COMMON_SUBDIRS = ["", "frontend/", "client/", "web/", "app/", "src/"]

        def file_exists_anywhere(filename: str) -> bool:
            """Check if file exists at root or in common subdirectories."""
            for subdir in COMMON_SUBDIRS:
                if f"{subdir}{filename}" in restored_files:
                    return True
            return False

        # Check required files (ALL must exist - at root or subdirectory)
        for required_file in config.get("required", []):
            # Check at root level and in common subdirectories
            if file_exists_anywhere(required_file):
                continue
            missing.append(required_file)

        # Check any_of files (AT LEAST ONE must exist - at root or subdirectory)
        any_of = config.get("any_of", [])
        if any_of:
            if not any(file_exists_anywhere(f) for f in any_of):
                missing.append(f"one of: {', '.join(any_of)}")

        # Check optional entry points (warn but don't fail)
        # optional_entry = config.get("optional_entry", [])
        # These are just warnings, not critical

        return len(missing) == 0, missing


    async def fix_common_issues(self, workspace_path: Path, project_id: str = None) -> Dict:
        """
        Comprehensive pre-start fixer for AI-generated projects.

        Automatically fixes common issues that cause container startup failures:
        1. vite.config: Remove 'open: true' (crashes in Docker), set correct base path
        2. tsconfig.node.json: Create if missing
        3. Tailwind plugins: Add missing plugins to package.json
        4. Missing dependencies: Scan imports and add to package.json
        5. Entry points: Validate index.html and main files exist
        6. TypeScript config: Fix common issues
        7. Package.json scripts: Ensure dev/build scripts exist
        8. index.html: Add <base> tag for correct URL resolution

        IMPORTANT: This function is IDEMPOTENT - calling it multiple times should not
        cause repeated file modifications. Each fix checks if the correction is already
        applied before making changes.

        Args:
            workspace_path: Path to the project workspace
            project_id: Optional project ID for preview URL routing (sets Vite base path)

        Returns:
            Dict with fixes applied and any errors
        """
        import json
        import re
        import shutil

        fixes_applied = []
        errors = []

        # =====================================================
        # FIRST: Fix Package Manager Conflicts (Bolt.new style)
        # This MUST run before anything else to ensure npm install works
        # =====================================================
        try:
            # Check for package manager conflicts in root and common subdirectories
            check_paths = [workspace_path]
            for subdir in ['frontend', 'client', 'web', 'app']:
                subdir_path = workspace_path / subdir
                if subdir_path.exists():
                    check_paths.append(subdir_path)

            for check_path in check_paths:
                pkg_json_path = check_path / 'package.json'
                pnpm_lock = check_path / 'pnpm-lock.yaml'
                yarn_lock = check_path / 'yarn.lock'
                npm_lock = check_path / 'package-lock.json'
                node_modules = check_path / 'node_modules'
                pnpm_store = check_path / '.pnpm-store'

                # Remove packageManager field from package.json (forces npm)
                if pkg_json_path.exists():
                    try:
                        pkg_content = pkg_json_path.read_text(encoding='utf-8')
                        if '"packageManager"' in pkg_content:
                            # Remove the packageManager line
                            import re as regex
                            new_content = regex.sub(r',?\s*"packageManager"\s*:\s*"[^"]*"', '', pkg_content)
                            # Clean up any trailing commas before }
                            new_content = regex.sub(r',(\s*})', r'\1', new_content)
                            pkg_json_path.write_text(new_content, encoding='utf-8')
                            rel_path = check_path.relative_to(workspace_path) if check_path != workspace_path else Path('.')
                            fixes_applied.append(f"Removed packageManager field from {rel_path}/package.json")
                            logger.info(f"[WorkspaceRestore] Removed packageManager field from {pkg_json_path}")
                    except Exception as e:
                        logger.warning(f"[WorkspaceRestore] Could not fix packageManager in {pkg_json_path}: {e}")

                # Remove conflicting lockfiles (keep only package-lock.json for npm)
                for lockfile in [pnpm_lock, yarn_lock]:
                    if lockfile.exists():
                        try:
                            lockfile.unlink()
                            rel_path = check_path.relative_to(workspace_path) if check_path != workspace_path else Path('.')
                            fixes_applied.append(f"Removed {lockfile.name} from {rel_path}")
                            logger.info(f"[WorkspaceRestore] Removed conflicting lockfile: {lockfile}")
                        except Exception as e:
                            logger.warning(f"[WorkspaceRestore] Could not remove {lockfile}: {e}")

                # Remove .pnpm-store directory
                if pnpm_store.exists():
                    try:
                        shutil.rmtree(pnpm_store)
                        rel_path = check_path.relative_to(workspace_path) if check_path != workspace_path else Path('.')
                        fixes_applied.append(f"Removed .pnpm-store from {rel_path}")
                        logger.info(f"[WorkspaceRestore] Removed .pnpm-store: {pnpm_store}")
                    except Exception as e:
                        logger.warning(f"[WorkspaceRestore] Could not remove .pnpm-store: {e}")

                # If pnpm/yarn was used but node_modules exists, it may be corrupted
                # Clear node_modules to allow clean npm install
                if node_modules.exists() and (pnpm_lock.exists() or yarn_lock.exists() or
                    (pkg_json_path.exists() and '"packageManager"' in pkg_json_path.read_text(encoding='utf-8', errors='ignore'))):
                    try:
                        shutil.rmtree(node_modules)
                        rel_path = check_path.relative_to(workspace_path) if check_path != workspace_path else Path('.')
                        fixes_applied.append(f"Cleared corrupted node_modules from {rel_path}")
                        logger.info(f"[WorkspaceRestore] Cleared corrupted node_modules: {node_modules}")
                    except Exception as e:
                        logger.warning(f"[WorkspaceRestore] Could not clear node_modules: {e}")

        except Exception as e:
            logger.error(f"[WorkspaceRestore] Error fixing package manager conflicts: {e}")
            errors.append(f"Package manager fix error: {e}")

        # =====================================================
        # Clear Vite cache to prevent corrupted cache issues
        # =====================================================
        vite_cache_path = workspace_path / 'node_modules' / '.vite'
        if vite_cache_path.exists():
            try:
                shutil.rmtree(vite_cache_path)
                fixes_applied.append("Cleared Vite cache (.vite)")
                logger.info(f"[WorkspaceRestore] Cleared Vite cache at {vite_cache_path}")
            except Exception as e:
                logger.warning(f"[WorkspaceRestore] Could not clear Vite cache: {e}")

        # Common packages that are often imported but missing from package.json
        COMMON_PACKAGES = {
            # React ecosystem
            'react': '^18.2.0',
            'react-dom': '^18.2.0',
            'react-router-dom': '^6.20.0',
            'react-query': '^3.39.3',
            '@tanstack/react-query': '^5.0.0',

            # UI Libraries
            'lucide-react': '^0.294.0',
            'react-icons': '^4.12.0',
            '@heroicons/react': '^2.0.18',
            'framer-motion': '^10.16.0',

            # Utilities
            'axios': '^1.6.0',
            'date-fns': '^2.30.0',
            'clsx': '^2.0.0',
            'classnames': '^2.3.2',
            'uuid': '^9.0.0',
            'lodash': '^4.17.21',

            # Charts
            'chart.js': '^4.4.0',
            'react-chartjs-2': '^5.2.0',
            'recharts': '^2.10.0',

            # Forms
            'react-hook-form': '^7.48.0',
            'zod': '^3.22.0',
            '@hookform/resolvers': '^3.3.0',

            # State management
            'zustand': '^4.4.0',
            'jotai': '^2.5.0',
            'recoil': '^0.7.7',
        }

        DEV_PACKAGES = {
            # TypeScript
            'typescript': '^5.3.0',
            '@types/react': '^18.2.0',
            '@types/react-dom': '^18.2.0',
            '@types/node': '^20.10.0',
            '@types/uuid': '^9.0.0',
            '@types/lodash': '^4.14.0',

            # Vite
            'vite': '^5.0.0',
            '@vitejs/plugin-react': '^4.2.0',

            # Tailwind
            'tailwindcss': '^3.3.0',
            'postcss': '^8.4.0',
            'autoprefixer': '^10.4.0',
            '@tailwindcss/forms': '^0.5.0',
            '@tailwindcss/typography': '^0.5.0',
            '@tailwindcss/aspect-ratio': '^0.4.0',
        }

        # Preview base path for Vite
        # With subdomain-based preview (like Vercel/Netlify), base should be "/"
        # since the project is served at the subdomain root (e.g., https://project-id.bharatbuild.ai/)
        preview_base = "/"

        try:
            # =====================================================
            # 1. FIX VITE CONFIG - Remove open: true, set base path for preview proxy
            # =====================================================
            # CRITICAL: When project_id is provided, set base to preview URL path
            # This ensures browser requests for assets like /src/main.tsx go to
            # /api/v1/preview/{project_id}/src/main.tsx instead of root domain
            #
            # IDEMPOTENCY: Only modify if the file actually needs changes
            for vite_config in ['vite.config.ts', 'vite.config.js', 'vite.config.mjs']:
                vite_path = workspace_path / vite_config
                if vite_path.exists():
                    try:
                        content = vite_path.read_text(encoding='utf-8')
                        original = content
                        changes_made = []

                        # Fix open: true in all variations (causes xdg-open ENOENT in Docker)
                        # Only if 'open: true' or 'open:true' actually exists
                        if re.search(r"['\"]?open['\"]?\s*:\s*true", content):
                            content = re.sub(r"['\"]?open['\"]?\s*:\s*true", 'open: false', content)
                            # Also remove open entirely to be safe
                            content = re.sub(r',?\s*open\s*:\s*false\s*,?', '', content)
                            changes_made.append("removed open:true")

                        # Ensure host is set for Docker (only add if not present)
                        if 'server:' in content and "host:" not in content and "host'" not in content:
                            content = re.sub(
                                r'(server\s*:\s*\{)',
                                r"\1\n    host: '0.0.0.0',",
                                content
                            )
                            changes_made.append("added host:0.0.0.0")

                        # CRITICAL: Disable HMR for subdomain preview
                        # WebSocket proxying through CloudFront/ALB is complex and unreliable
                        # Users can refresh manually - this is more stable than broken HMR
                        if project_id and 'server:' in content:
                            # Check if HMR is already disabled
                            hmr_disabled = 'hmr: false' in content or 'hmr:false' in content

                            if not hmr_disabled:
                                # Check if there's an existing hmr block to replace
                                hmr_block_pattern = r'hmr\s*:\s*\{[^}]*\}'
                                if re.search(hmr_block_pattern, content):
                                    # Replace existing hmr block with hmr: false
                                    content = re.sub(hmr_block_pattern, 'hmr: false', content)
                                    changes_made.append("replaced HMR config with hmr:false")
                                elif 'hmr:' not in content:
                                    # No hmr config at all, add hmr: false
                                    content = re.sub(
                                        r'(server\s*:\s*\{)',
                                        r"\1\n    hmr: false,",
                                        content
                                    )
                                    changes_made.append("disabled HMR for subdomain preview")

                        # CRITICAL FIX: Set base path for preview proxy routing
                        # IDEMPOTENCY: Only modify if base is not already set to correct value
                        if project_id:
                            # Check current base value
                            base_match = re.search(r"\bbase\s*:\s*['\"]([^'\"]*)['\"]", content)
                            current_base = base_match.group(1) if base_match else None

                            if current_base != preview_base:
                                if base_match:
                                    # Replace existing base with correct preview path
                                    content = re.sub(
                                        r"(\bbase\s*:\s*)['\"][^'\"]*['\"]",
                                        f"\\1'{preview_base}'",
                                        content
                                    )
                                    changes_made.append(f"changed base from '{current_base}' to '{preview_base}'")
                                else:
                                    # Add base to defineConfig or export default
                                    if 'defineConfig' in content:
                                        content = re.sub(
                                            r'(defineConfig\s*\(\s*\{)',
                                            f"\\1\n  base: '{preview_base}',",
                                            content
                                        )
                                        changes_made.append(f"added base:'{preview_base}'")
                                    elif re.search(r'export\s+default\s*\{', content):
                                        content = re.sub(
                                            r'(export\s+default\s*\{)',
                                            f"\\1\n  base: '{preview_base}',",
                                            content
                                        )
                                        changes_made.append(f"added base:'{preview_base}'")

                        # Only write if actual changes were made
                        if content != original and changes_made:
                            vite_path.write_text(content, encoding='utf-8')
                            fixes_applied.append(f"Fixed {vite_config}: {', '.join(changes_made)}")
                            logger.info(f"[WorkspaceRestore] Modified {vite_config}: {changes_made}")
                        elif not changes_made:
                            logger.debug(f"[WorkspaceRestore] {vite_config} already correct, no changes needed")
                    except Exception as e:
                        errors.append(f"Error fixing {vite_config}: {e}")

            # =====================================================
            # 2. CREATE TSCONFIG.NODE.JSON IF MISSING
            # =====================================================
            tsconfig_path = workspace_path / 'tsconfig.json'
            tsconfig_node_path = workspace_path / 'tsconfig.node.json'
            if tsconfig_path.exists() and not tsconfig_node_path.exists():
                try:
                    tsconfig_content = tsconfig_path.read_text(encoding='utf-8')
                    if 'tsconfig.node.json' in tsconfig_content:
                        tsconfig_node_content = '''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts", "vite.config.js"]
}
'''
                        tsconfig_node_path.write_text(tsconfig_node_content, encoding='utf-8')
                        fixes_applied.append("Created tsconfig.node.json")
                except Exception as e:
                    errors.append(f"Error creating tsconfig.node.json: {e}")

            # =====================================================
            # 3. SCAN IMPORTS AND ADD MISSING PACKAGES
            # =====================================================
            package_json_path = workspace_path / 'package.json'
            if package_json_path.exists():
                try:
                    package_content = package_json_path.read_text(encoding='utf-8')
                    package_data = json.loads(package_content)

                    deps = package_data.get('dependencies', {})
                    dev_deps = package_data.get('devDependencies', {})
                    all_deps = {**deps, **dev_deps}

                    # Collect all imports from source files
                    imported_packages = set()
                    src_path = workspace_path / 'src'

                    # Scan .tsx, .ts, .jsx, .js files
                    for ext in ['**/*.tsx', '**/*.ts', '**/*.jsx', '**/*.js']:
                        for file_path in workspace_path.glob(ext):
                            if 'node_modules' in str(file_path):
                                continue
                            try:
                                file_content = file_path.read_text(encoding='utf-8')

                                # Match import statements
                                # import X from 'package'
                                # import { X } from 'package'
                                # import 'package'
                                import_pattern = r'''(?:import\s+(?:[\w{}\s,*]+\s+from\s+)?['"]([^'"./][^'"]*?)['"]|require\s*\(\s*['"]([^'"./][^'"]*?)['"]\s*\))'''
                                matches = re.findall(import_pattern, file_content)

                                for match in matches:
                                    pkg = match[0] or match[1]
                                    # Get base package name (e.g., @scope/pkg from @scope/pkg/sub)
                                    if pkg.startswith('@'):
                                        parts = pkg.split('/')
                                        if len(parts) >= 2:
                                            pkg = '/'.join(parts[:2])
                                    else:
                                        pkg = pkg.split('/')[0]

                                    if pkg and not pkg.startswith('.'):
                                        imported_packages.add(pkg)
                            except Exception:
                                pass

                    # Find missing packages
                    added_deps = []
                    added_dev_deps = []

                    for pkg in imported_packages:
                        if pkg not in all_deps:
                            # Check if it's a known package
                            if pkg in COMMON_PACKAGES:
                                deps[pkg] = COMMON_PACKAGES[pkg]
                                added_deps.append(pkg)
                            elif pkg in DEV_PACKAGES:
                                dev_deps[pkg] = DEV_PACKAGES[pkg]
                                added_dev_deps.append(pkg)

                    # Check tailwind.config for plugins
                    for tailwind_config in ['tailwind.config.js', 'tailwind.config.ts', 'tailwind.config.cjs']:
                        tailwind_path = workspace_path / tailwind_config
                        if tailwind_path.exists():
                            try:
                                tw_content = tailwind_path.read_text(encoding='utf-8')
                                for plugin in ['@tailwindcss/forms', '@tailwindcss/typography',
                                              '@tailwindcss/aspect-ratio', '@tailwindcss/container-queries']:
                                    if plugin in tw_content and plugin not in all_deps:
                                        dev_deps[plugin] = DEV_PACKAGES.get(plugin, '^0.5.0')
                                        added_dev_deps.append(plugin)
                            except Exception:
                                pass
                            break

                    # Update package.json if we added anything
                    if added_deps or added_dev_deps:
                        package_data['dependencies'] = deps
                        package_data['devDependencies'] = dev_deps
                        package_json_path.write_text(
                            json.dumps(package_data, indent=2),
                            encoding='utf-8'
                        )
                        if added_deps:
                            fixes_applied.append(f"Added dependencies: {', '.join(added_deps)}")
                        if added_dev_deps:
                            fixes_applied.append(f"Added devDependencies: {', '.join(added_dev_deps)}")
                        logger.info(f"[WorkspaceRestore] Added packages: deps={added_deps}, devDeps={added_dev_deps}")

                    # =====================================================
                    # 4. ENSURE REQUIRED SCRIPTS EXIST AND ARE DOCKER-SAFE
                    # =====================================================
                    scripts = package_data.get('scripts', {})
                    scripts_added = []
                    scripts_fixed = []

                    # Check for vite project
                    is_vite = any((workspace_path / f).exists() for f in ['vite.config.ts', 'vite.config.js'])

                    if is_vite:
                        if 'dev' not in scripts:
                            scripts['dev'] = 'vite --host 0.0.0.0'
                            scripts_added.append('dev')
                        else:
                            # Fix existing dev script to be Docker-safe
                            dev_script = scripts['dev']
                            if '--host' not in dev_script:
                                scripts['dev'] = dev_script + ' --host 0.0.0.0'
                                scripts_fixed.append('dev (added --host)')
                        if 'build' not in scripts:
                            scripts['build'] = 'vite build'
                            scripts_added.append('build')
                        if 'preview' not in scripts:
                            scripts['preview'] = 'vite preview'
                            scripts_added.append('preview')
                    else:
                        # Generic React project
                        if 'start' not in scripts and 'dev' not in scripts:
                            scripts['start'] = 'react-scripts start'
                            scripts_added.append('start')

                    if scripts_added or scripts_fixed:
                        package_data['scripts'] = scripts
                        package_json_path.write_text(
                            json.dumps(package_data, indent=2),
                            encoding='utf-8'
                        )
                        if scripts_added:
                            fixes_applied.append(f"Added scripts: {', '.join(scripts_added)}")
                        if scripts_fixed:
                            fixes_applied.append(f"Fixed scripts: {', '.join(scripts_fixed)}")

                except Exception as e:
                    errors.append(f"Error processing package.json: {e}")

            # =====================================================
            # 5. VALIDATE/CREATE INDEX.HTML with base tag for preview proxy
            # =====================================================
            index_html_path = workspace_path / 'index.html'
            if not index_html_path.exists():
                # Check if this is a Vite/React project
                if package_json_path.exists():
                    try:
                        pkg = json.loads(package_json_path.read_text(encoding='utf-8'))
                        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}

                        if 'vite' in deps or 'react' in deps:
                            # Create basic index.html with base tag if project_id is provided
                            main_file = 'src/main.tsx' if (workspace_path / 'src/main.tsx').exists() else 'src/main.jsx'
                            if not (workspace_path / main_file).exists():
                                main_file = 'src/index.tsx' if (workspace_path / 'src/index.tsx').exists() else 'src/index.jsx'

                            # Note: Don't add <base> tag since Vite's base="/" in config handles paths
                            # Adding <base href="/"> is redundant and can sometimes cause conflicts
                            index_content = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/{main_file}"></script>
  </body>
</html>
'''
                            index_html_path.write_text(index_content, encoding='utf-8')
                            fixes_applied.append("Created index.html")
                    except Exception as e:
                        errors.append(f"Error creating index.html: {e}")
            else:
                # Fix any existing index.html issues (but don't add base tag)
                pass

            # =====================================================
            # 6. FIX POSTCSS CONFIG
            # =====================================================
            postcss_path = workspace_path / 'postcss.config.js'
            if not postcss_path.exists():
                # Check if tailwind is used
                if any((workspace_path / f).exists() for f in ['tailwind.config.js', 'tailwind.config.ts']):
                    postcss_content = '''export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''
                    postcss_path.write_text(postcss_content, encoding='utf-8')
                    fixes_applied.append("Created postcss.config.js")

            # =====================================================
            # 7. FIX COMMON TYPESCRIPT ISSUES
            # =====================================================
            if tsconfig_path.exists():
                try:
                    tsconfig_content = tsconfig_path.read_text(encoding='utf-8')
                    tsconfig_data = json.loads(tsconfig_content)

                    compiler_options = tsconfig_data.get('compilerOptions', {})
                    modified = False

                    # Ensure skipLibCheck is true (prevents type errors from node_modules)
                    if not compiler_options.get('skipLibCheck'):
                        compiler_options['skipLibCheck'] = True
                        modified = True

                    # Ensure moduleResolution is set
                    if 'moduleResolution' not in compiler_options:
                        compiler_options['moduleResolution'] = 'bundler'
                        modified = True

                    # Ensure jsx is set for React
                    if 'jsx' not in compiler_options:
                        compiler_options['jsx'] = 'react-jsx'
                        modified = True

                    if modified:
                        tsconfig_data['compilerOptions'] = compiler_options
                        tsconfig_path.write_text(
                            json.dumps(tsconfig_data, indent=2),
                            encoding='utf-8'
                        )
                        fixes_applied.append("Fixed tsconfig.json compiler options")
                except Exception as e:
                    # tsconfig might have comments, can't parse as JSON
                    pass

            # =====================================================
            # 8. FIX SRC/INDEX.CSS FOR TAILWIND (especially shadcn/ui)
            # =====================================================
            index_css_path = workspace_path / 'src' / 'index.css'
            src_exists = (workspace_path / 'src').exists()
            tailwind_exists = any((workspace_path / f).exists() for f in ['tailwind.config.js', 'tailwind.config.ts'])

            if src_exists and tailwind_exists:
                # Check if tailwind.config uses CSS variables (shadcn/ui pattern)
                uses_css_variables = False
                for tw_config in ['tailwind.config.js', 'tailwind.config.ts']:
                    tw_path = workspace_path / tw_config
                    if tw_path.exists():
                        try:
                            tw_content = tw_path.read_text(encoding='utf-8')
                            # Check for CSS variable patterns like var(--border), hsl(var(--primary))
                            if 'var(--' in tw_content or 'hsl(var(' in tw_content:
                                uses_css_variables = True
                                break
                        except Exception:
                            pass

                # shadcn/ui style CSS with CSS variables
                shadcn_css_content = '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
    --chart-1: 12 76% 61%;
    --chart-2: 173 58% 39%;
    --chart-3: 197 37% 24%;
    --chart-4: 43 74% 66%;
    --chart-5: 27 87% 67%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
    --chart-1: 220 70% 50%;
    --chart-2: 160 60% 45%;
    --chart-3: 30 80% 55%;
    --chart-4: 280 65% 60%;
    --chart-5: 340 75% 55%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
'''
                # Simple Tailwind CSS (no CSS variables)
                simple_css_content = '''@tailwind base;
@tailwind components;
@tailwind utilities;
'''

                if not index_css_path.exists():
                    # Create new file
                    index_css_path.parent.mkdir(parents=True, exist_ok=True)
                    if uses_css_variables:
                        index_css_path.write_text(shadcn_css_content, encoding='utf-8')
                        fixes_applied.append("Created src/index.css with shadcn/ui CSS variables")
                    else:
                        index_css_path.write_text(simple_css_content, encoding='utf-8')
                        fixes_applied.append("Created src/index.css with Tailwind imports")
                elif uses_css_variables:
                    # Check if existing file has CSS variables
                    try:
                        existing_content = index_css_path.read_text(encoding='utf-8')
                        if '--border' not in existing_content and '--background' not in existing_content:
                            # Add CSS variables to existing file
                            index_css_path.write_text(shadcn_css_content, encoding='utf-8')
                            fixes_applied.append("Fixed src/index.css: Added shadcn/ui CSS variables")
                    except Exception:
                        pass

            # =====================================================
            # 9. FIX INCORRECT IMPORT PATHS IN ALL SOURCE FILES
            # =====================================================
            # Common issue: AI generates imports like './src/App' when already in src/
            # This causes double paths like /src/src/App.tsx
            # Also fix @/ alias issues that might cause problems
            src_dir = workspace_path / 'src'
            if src_dir.exists():
                files_fixed = []
                for ext in ['*.tsx', '*.ts', '*.jsx', '*.js']:
                    for source_file in src_dir.rglob(ext):
                        if 'node_modules' in str(source_file):
                            continue
                        try:
                            content = source_file.read_text(encoding='utf-8')
                            original = content

                            # Fix imports that incorrectly reference ./src/ when already in src/
                            # import App from './src/App' -> import App from './App'
                            content = re.sub(r"from\s+['\"]\.\/src\/", "from './", content)
                            content = re.sub(r"import\s+['\"]\.\/src\/", "import './", content)

                            # Fix imports that use /src/ absolute path (should be relative)
                            content = re.sub(r"from\s+['\"]\/src\/", "from './", content)
                            content = re.sub(r"import\s+['\"]\/src\/", "import './", content)

                            # Fix double-dot issues: from '../src/' -> from '../'
                            content = re.sub(r"from\s+['\"]\.\.\/src\/", "from '../", content)

                            if content != original:
                                source_file.write_text(content, encoding='utf-8')
                                rel_path = source_file.relative_to(workspace_path)
                                files_fixed.append(str(rel_path))
                        except Exception as e:
                            errors.append(f"Error fixing imports in {source_file.name}: {e}")

                if files_fixed:
                    if len(files_fixed) <= 3:
                        fixes_applied.append(f"Fixed import paths in: {', '.join(files_fixed)}")
                    else:
                        fixes_applied.append(f"Fixed import paths in {len(files_fixed)} source files")

            # =====================================================
            # 10. FIX DOCKERFILE: Replace production multi-stage builds with dev Dockerfiles
            # - npm ci requires package-lock.json which AI-generated projects don't have
            # - npm run build fails on TypeScript errors, but dev containers don't need it
            # - Multi-stage builds with COPY --from expect dist/ which doesn't exist without build
            # =====================================================
            dockerfile_patterns = ['Dockerfile', 'Dockerfile.*', '*/Dockerfile', 'frontend/Dockerfile', 'backend/Dockerfile']
            dockerfiles_fixed = []

            # Development Dockerfile templates
            VITE_DEV_DOCKERFILE = '''FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
'''
            REACT_DEV_DOCKERFILE = '''FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
'''

            for pattern in dockerfile_patterns:
                for dockerfile_path in workspace_path.glob(pattern):
                    if dockerfile_path.is_file():
                        try:
                            content = dockerfile_path.read_text(encoding='utf-8')
                            original = content
                            fixes = []

                            # Check if it's a multi-stage Node.js production build
                            is_multistage = 'npm run build' in content and 'COPY --from' in content

                            if is_multistage:
                                # Replace entire Dockerfile with development version
                                is_vite = '5173' in content or 'vite' in content.lower()
                                content = VITE_DEV_DOCKERFILE if is_vite else REACT_DEV_DOCKERFILE
                                fixes.append('replaced_multistage')
                            else:
                                # Simple fixes for non-multi-stage Dockerfiles
                                if 'npm ci' in content:
                                    content = content.replace('npm ci', 'npm install')
                                    fixes.append('npm_ci')

                                # Fix --only=production (skips devDependencies like vite)
                                if '--only=production' in content or '--omit=dev' in content:
                                    content = content.replace('npm install --only=production', 'npm install')
                                    content = content.replace('npm install --omit=dev', 'npm install')
                                    content = content.replace('--production', '')
                                    fixes.append('prod_deps')

                                if 'RUN npm run build' in content:
                                    lines = content.split('\n')
                                    lines = [l for l in lines if 'RUN npm run build' not in l]
                                    content = '\n'.join(lines)
                                    fixes.append('npm_build')

                                # Fix npm start -> npm run dev for Vite projects
                                if 'npm' in content and 'start' in content:
                                    # Check if this is a Vite project
                                    is_vite = '5173' in content or 'vite' in content.lower()
                                    # Also check package.json in same directory
                                    if not is_vite:
                                        pkg_json = dockerfile_path.parent / 'package.json'
                                        if pkg_json.exists():
                                            try:
                                                pkg_content = pkg_json.read_text(encoding='utf-8')
                                                is_vite = '"vite"' in pkg_content
                                            except:
                                                pass
                                    if is_vite:
                                        content = content.replace('CMD ["npm", "start"]', 'CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]')
                                        content = content.replace('CMD ["npm", "start", "--", "--host", "0.0.0.0"]', 'CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]')
                                        content = content.replace('npm start', 'npm run dev -- --host 0.0.0.0')
                                        fixes.append('vite_cmd')

                            if content != original:
                                dockerfile_path.write_text(content, encoding='utf-8')
                                rel_path = dockerfile_path.relative_to(workspace_path)
                                dockerfiles_fixed.append(f"{rel_path} ({', '.join(fixes)})")
                        except Exception as e:
                            errors.append(f"Error fixing Dockerfile {dockerfile_path.name}: {e}")

            if dockerfiles_fixed:
                fixes_applied.append(f"Fixed Dockerfiles: {', '.join(dockerfiles_fixed)}")
                logger.info(f"[WorkspaceRestore] Fixed Dockerfiles: {dockerfiles_fixed}")

            # =====================================================
            # 11. FIX INCORRECT PATHS AND TAGS IN INDEX.HTML
            # =====================================================
            index_html_path = workspace_path / 'index.html'
            if index_html_path.exists():
                try:
                    content = index_html_path.read_text(encoding='utf-8')
                    original = content
                    html_fixes = []

                    # Remove any <base> tag - Vite's base config handles path resolution
                    # Having both can cause conflicts and double-path issues
                    if re.search(r'<base[^>]*/?>', content, re.IGNORECASE):
                        content = re.sub(r'\s*<base[^>]*/?>\s*', '', content, flags=re.IGNORECASE)
                        html_fixes.append("removed base tag")

                    # Fix CSS/JS links that use /src/src/ (double src)
                    if '/src/src/' in content:
                        content = re.sub(r'"/src/src/', '"/src/', content)
                        content = re.sub(r"'/src/src/", "'/src/", content)
                        html_fixes.append("fixed double /src/src/")

                    # Fix other doubled path patterns
                    content = re.sub(r'"/node_modules/node_modules/', '"/node_modules/', content)
                    content = re.sub(r'"/.vite/.vite/', '"/.vite/', content)

                    # Ensure script src points to correct main file with proper path
                    main_tsx = workspace_path / 'src/main.tsx'
                    main_jsx = workspace_path / 'src/main.jsx'
                    index_tsx = workspace_path / 'src/index.tsx'
                    index_jsx = workspace_path / 'src/index.jsx'

                    correct_main = None
                    if main_tsx.exists():
                        correct_main = '/src/main.tsx'
                    elif main_jsx.exists():
                        correct_main = '/src/main.jsx'
                    elif index_tsx.exists():
                        correct_main = '/src/index.tsx'
                    elif index_jsx.exists():
                        correct_main = '/src/index.jsx'

                    if correct_main:
                        # Find current script src and fix if wrong
                        script_match = re.search(r'<script[^>]*type="module"[^>]*src="([^"]*)"', content)
                        if script_match:
                            current_src = script_match.group(1)
                            # Check if it's wrong (double path, wrong file, etc.)
                            if current_src != correct_main and (
                                '/src/src/' in current_src or
                                not current_src.startswith('/src/')
                            ):
                                content = re.sub(
                                    r'(<script[^>]*type="module"[^>]*src=")[^"]*"',
                                    f'\\1{correct_main}"',
                                    content
                                )
                                html_fixes.append(f"fixed script src to {correct_main}")

                    if content != original:
                        index_html_path.write_text(content, encoding='utf-8')
                        if html_fixes:
                            fixes_applied.append(f"Fixed index.html: {', '.join(html_fixes)}")
                        else:
                            fixes_applied.append("Fixed paths in index.html")
                except Exception as e:
                    errors.append(f"Error fixing index.html: {e}")

        except Exception as e:
            errors.append(f"Unexpected error in fix_common_issues: {e}")
            logger.error(f"[WorkspaceRestore] Error in fix_common_issues: {e}")

        if fixes_applied:
            logger.info(f"[WorkspaceRestore] Applied {len(fixes_applied)} fixes: {fixes_applied}")

        return {
            "fixes_applied": fixes_applied,
            "errors": errors,
            "success": len(errors) == 0
        }


# Singleton instance
workspace_restore = WorkspaceRestoreService()
