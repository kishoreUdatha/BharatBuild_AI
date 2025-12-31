"""
Patch Applier - Atomic patch workflow with rollback

Claude NEVER edits files directly.
This service applies fixes using validated, atomic patch workflow:

1. Parse diff (DiffParser - pure Python, no external tools)
2. Validate (check context matches)
3. Snapshot (backup)
4. Apply atomically (in-memory, then write)
5. Rebuild (verify fix)
6. Rollback if needed

AI proposes, System disposes, Runtime decides.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json

from app.core.logging_config import logger
from app.services.diff_parser import DiffParser, ParsedDiff, ApplyResult as DiffApplyResult


@dataclass
class PatchResult:
    """Result of a patch operation"""
    success: bool
    message: str
    files_modified: List[str]
    rollback_available: bool
    build_output: Optional[str] = None


@dataclass
class ApplyResult:
    """Result of applying a single patch"""
    success: bool
    file_path: str
    error: Optional[str] = None


class PatchApplier:
    """
    Applies patches atomically with validation and rollback.

    Workflow:
    1. Validate patch (dry-run)
    2. Create snapshot
    3. Apply atomically
    4. Run build
    5. Rollback if build fails
    """

    # Files that are NEVER allowed to be modified
    FORBIDDEN_FILES = [
        '.env', '.env.local', '.env.production',
        'docker-compose.yml', 'Dockerfile',
        '.git/config', '.gitignore',
        'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',  # Lock files
    ]

    # Maximum files allowed in a single patch operation
    MAX_FILES_PER_PATCH = 5

    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.snapshot_path: Optional[Path] = None
        self._snapshot_files: Dict[str, str] = {}

    async def apply_patches(
        self,
        patches: List[Dict[str, str]],
        run_build: bool = True,
        build_command: str = "npm run build"
    ) -> PatchResult:
        """
        Apply multiple patches atomically.

        Args:
            patches: List of {path, patch} dicts with unified diff content
            run_build: Whether to run build after applying
            build_command: Command to verify build

        Returns:
            PatchResult with success status and rollback info
        """
        if not patches:
            return PatchResult(
                success=True,
                message="No patches to apply",
                files_modified=[],
                rollback_available=False
            )

        # Check file count limit
        if len(patches) > self.MAX_FILES_PER_PATCH:
            return PatchResult(
                success=False,
                message=f"Too many files: {len(patches)} > {self.MAX_FILES_PER_PATCH}",
                files_modified=[],
                rollback_available=False
            )

        files_to_modify = []
        for p in patches:
            file_path = p.get("path", "")
            # Check forbidden files
            if self._is_forbidden(file_path):
                return PatchResult(
                    success=False,
                    message=f"Cannot modify forbidden file: {file_path}",
                    files_modified=[],
                    rollback_available=False
                )
            files_to_modify.append(file_path)

        # Step 1: Validate all patches (dry-run)
        logger.info(f"[PatchApplier] Validating {len(patches)} patches...")
        for patch in patches:
            valid, error = await self._validate_patch(patch)
            if not valid:
                return PatchResult(
                    success=False,
                    message=f"Patch validation failed: {error}",
                    files_modified=[],
                    rollback_available=False
                )

        # Step 2: Create snapshot
        logger.info(f"[PatchApplier] Creating snapshot of {len(files_to_modify)} files...")
        self._create_snapshot(files_to_modify)

        # Step 3: Apply patches atomically
        logger.info(f"[PatchApplier] Applying patches atomically...")
        applied_files = []
        try:
            for patch in patches:
                result = await self._apply_single_patch(patch)
                if result.success:
                    applied_files.append(result.file_path)
                else:
                    # Rollback on first failure
                    logger.error(f"[PatchApplier] Patch failed: {result.error}")
                    self._rollback()
                    return PatchResult(
                        success=False,
                        message=f"Patch apply failed: {result.error}",
                        files_modified=[],
                        rollback_available=False
                    )

            # Step 4: Run build (if requested)
            if run_build:
                logger.info(f"[PatchApplier] Running build to verify fix...")
                build_success, build_output = await self._run_build(build_command)

                if not build_success:
                    logger.error(f"[PatchApplier] Build failed, rolling back...")
                    self._rollback()
                    return PatchResult(
                        success=False,
                        message="Build failed after patch, rolled back",
                        files_modified=[],
                        rollback_available=False,
                        build_output=build_output
                    )

            # Success!
            logger.info(f"[PatchApplier] Successfully applied {len(applied_files)} patches")
            return PatchResult(
                success=True,
                message=f"Applied {len(applied_files)} patches",
                files_modified=applied_files,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"[PatchApplier] Exception during apply: {e}")
            self._rollback()
            return PatchResult(
                success=False,
                message=f"Exception: {str(e)}",
                files_modified=[],
                rollback_available=False
            )

    async def apply_full_files(
        self,
        files: List[Dict[str, str]],
        run_build: bool = True,
        build_command: str = "npm run build"
    ) -> PatchResult:
        """
        Apply full file replacements atomically.

        Args:
            files: List of {path, content} dicts
            run_build: Whether to run build after applying
            build_command: Command to verify build

        Returns:
            PatchResult with success status
        """
        if not files:
            return PatchResult(
                success=True,
                message="No files to apply",
                files_modified=[],
                rollback_available=False
            )

        files_to_modify = [f.get("path", "") for f in files]

        # Check forbidden files
        for file_path in files_to_modify:
            if self._is_forbidden(file_path):
                return PatchResult(
                    success=False,
                    message=f"Cannot modify forbidden file: {file_path}",
                    files_modified=[],
                    rollback_available=False
                )

        # Step 1: Create snapshot
        logger.info(f"[PatchApplier] Creating snapshot of {len(files_to_modify)} files...")
        self._create_snapshot(files_to_modify)

        # Step 2: Write files atomically
        logger.info(f"[PatchApplier] Writing {len(files)} files...")
        written_files = []
        try:
            for file_info in files:
                file_path = file_info.get("path", "")
                content = file_info.get("content", "")

                target_path = self.project_path / file_path
                target_path.parent.mkdir(parents=True, exist_ok=True)

                # Write to temp file first, then atomic rename
                temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
                temp_path.write_text(content, encoding='utf-8')
                temp_path.replace(target_path)

                written_files.append(file_path)
                logger.info(f"[PatchApplier] Wrote: {file_path}")

            # Step 3: Run build (if requested)
            if run_build:
                logger.info(f"[PatchApplier] Running build to verify fix...")
                build_success, build_output = await self._run_build(build_command)

                if not build_success:
                    logger.error(f"[PatchApplier] Build failed, rolling back...")
                    self._rollback()
                    return PatchResult(
                        success=False,
                        message="Build failed after file write, rolled back",
                        files_modified=[],
                        rollback_available=False,
                        build_output=build_output
                    )

            # Success!
            logger.info(f"[PatchApplier] Successfully wrote {len(written_files)} files")
            return PatchResult(
                success=True,
                message=f"Applied {len(written_files)} files",
                files_modified=written_files,
                rollback_available=True
            )

        except Exception as e:
            logger.error(f"[PatchApplier] Exception during write: {e}")
            self._rollback()
            return PatchResult(
                success=False,
                message=f"Exception: {str(e)}",
                files_modified=[],
                rollback_available=False
            )

    async def create_new_files(
        self,
        new_files: List[Dict[str, str]]
    ) -> PatchResult:
        """
        Create new files (no rollback needed for new files).

        Args:
            new_files: List of {path, content} dicts

        Returns:
            PatchResult
        """
        if not new_files:
            return PatchResult(
                success=True,
                message="No new files to create",
                files_modified=[],
                rollback_available=False
            )

        created_files = []
        for file_info in new_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            if self._is_forbidden(file_path):
                logger.warning(f"[PatchApplier] Skipping forbidden file: {file_path}")
                continue

            target_path = self.project_path / file_path
            if target_path.exists():
                logger.warning(f"[PatchApplier] File already exists, skipping: {file_path}")
                continue

            try:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(content, encoding='utf-8')
                created_files.append(file_path)
                logger.info(f"[PatchApplier] Created: {file_path}")
            except Exception as e:
                logger.error(f"[PatchApplier] Failed to create {file_path}: {e}")

        return PatchResult(
            success=len(created_files) > 0,
            message=f"Created {len(created_files)} files",
            files_modified=created_files,
            rollback_available=False
        )

    async def _validate_patch(self, patch: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """
        Validate patch using DiffParser (pure Python, no external tools).

        Checks:
        1. Diff can be parsed
        2. Target file exists
        3. Context lines match
        """
        patch_content = patch.get("patch", "")
        if not patch_content.strip():
            return False, "Empty patch content"

        # Step 1: Parse the diff
        parsed = DiffParser.parse(patch_content)
        if not parsed.is_valid:
            return False, f"Invalid diff format: {parsed.error}"

        # Step 2: Check target file exists
        file_path = parsed.new_file or parsed.old_file
        if not file_path:
            return False, "No file path in diff"

        target_path = self.project_path / file_path
        if not target_path.exists():
            # Try with frontend/ prefix
            target_path = self.project_path / "frontend" / file_path
            if not target_path.exists():
                return False, f"Target file not found: {file_path}"

        # Step 3: Dry-run apply to check context matches
        try:
            original_content = target_path.read_text(encoding='utf-8')
            result = DiffParser.apply(original_content, parsed)

            if not result.success:
                return False, f"Context mismatch: {result.error}"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def _apply_single_patch(self, patch: Dict[str, str]) -> ApplyResult:
        """
        Apply a single patch using DiffParser (pure Python, no git/patch needed).
        """
        patch_content = patch.get("patch", "")
        file_path = patch.get("path", "unknown")

        # Parse the diff
        parsed = DiffParser.parse(patch_content)
        if not parsed.is_valid:
            return ApplyResult(
                success=False,
                file_path=file_path,
                error=f"Invalid diff: {parsed.error}"
            )

        # Get actual file path from diff
        actual_file = parsed.new_file or parsed.old_file or file_path

        # Find the target file
        target_path = self.project_path / actual_file
        if not target_path.exists():
            target_path = self.project_path / "frontend" / actual_file
            if not target_path.exists():
                return ApplyResult(
                    success=False,
                    file_path=actual_file,
                    error=f"File not found: {actual_file}"
                )

        try:
            # Read original content
            original_content = target_path.read_text(encoding='utf-8')

            # Apply diff in memory
            result = DiffParser.apply(original_content, parsed)

            if not result.success:
                return ApplyResult(
                    success=False,
                    file_path=actual_file,
                    error=result.error
                )

            # Write atomically (temp file + rename)
            temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
            temp_path.write_text(result.new_content, encoding='utf-8')
            temp_path.replace(target_path)

            logger.info(f"[PatchApplier] Applied patch to {actual_file}: +{result.lines_added} -{result.lines_deleted}")

            return ApplyResult(success=True, file_path=actual_file)

        except Exception as e:
            return ApplyResult(
                success=False,
                file_path=actual_file,
                error=str(e)
            )

    def _create_snapshot(self, files: List[str]) -> None:
        """
        Create in-memory snapshot of files before modification.
        """
        self._snapshot_files = {}
        for file_path in files:
            full_path = self.project_path / file_path
            if full_path.exists():
                try:
                    self._snapshot_files[file_path] = full_path.read_text(encoding='utf-8')
                except Exception as e:
                    logger.warning(f"[PatchApplier] Could not snapshot {file_path}: {e}")

        logger.info(f"[PatchApplier] Snapshot created for {len(self._snapshot_files)} files")

    def _rollback(self) -> bool:
        """
        Rollback to snapshot state.
        """
        if not self._snapshot_files:
            logger.warning("[PatchApplier] No snapshot available for rollback")
            return False

        logger.info(f"[PatchApplier] Rolling back {len(self._snapshot_files)} files...")
        for file_path, content in self._snapshot_files.items():
            try:
                full_path = self.project_path / file_path
                full_path.write_text(content, encoding='utf-8')
                logger.info(f"[PatchApplier] Rolled back: {file_path}")
            except Exception as e:
                logger.error(f"[PatchApplier] Failed to rollback {file_path}: {e}")

        self._snapshot_files = {}
        return True

    async def _run_build(self, command: str) -> Tuple[bool, str]:
        """
        Run build command to verify fix.
        """
        try:
            result = subprocess.run(
                command.split(),
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )

            output = result.stdout + "\n" + result.stderr
            return result.returncode == 0, output

        except subprocess.TimeoutExpired:
            return False, "Build timed out"
        except Exception as e:
            return False, str(e)

    def _is_forbidden(self, file_path: str) -> bool:
        """Check if file is in forbidden list."""
        normalized = file_path.lower().replace('\\', '/')
        for forbidden in self.FORBIDDEN_FILES:
            if forbidden.lower() in normalized:
                return True
        return False
