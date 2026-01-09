"""
Bolt Fixer - Unified fixer using Bolt.new architecture

This replaces SimpleFixer with the proper Bolt.new pattern:
1. Error Classifier (rule-based, NO AI)
2. Decision Gate (should Claude be called?)
3. Retry Limiter (max attempts)
4. Claude API (strict prompt, diff only)
5. Patch Validator (validate before apply)
6. Diff Parser (pure Python, no git)
7. Patch Applier (atomic with rollback)

Claude is a tool, not a controller.
"""

from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from pathlib import Path
import json
import re

from app.core.logging_config import logger
from app.services.error_classifier import ErrorClassifier, ErrorType, ClassifiedError
from app.services.patch_validator import PatchValidator
from app.services.retry_limiter import retry_limiter
from app.services.diff_parser import DiffParser
from app.services.patch_applier import PatchApplier
from app.services.storage_service import storage_service
from app.services.batch_tracker import batch_tracker
from app.services.dependency_graph import build_dependency_graph, DependencyGraph
from app.services.project_sanitizer import sanitize_project_file


# =============================================================================
# CONTEXT LIMIT CONFIGURATION
# =============================================================================
MAX_CONTEXT_CHARS = 100000      # ~25k tokens - safe limit for Claude
MAX_FILES_PER_BATCH = 6         # Max files to include in one fix
CHARS_PER_FILE_LIMIT = 12000    # Truncate files larger than this
CONTEXT_LINES_AROUND_ERROR = 60 # Lines to keep around error when truncating
MAX_FIX_PASSES = 5              # Maximum multi-pass fix attempts

# =============================================================================
# DOCKERFILE BASE IMAGE FIXES (Deterministic - No AI needed)
# =============================================================================
# Maps deprecated/unavailable Docker base images to working alternatives
DOCKERFILE_BASE_IMAGE_FIXES = {
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
    # Node images
    "node:latest": "node:20-alpine",
    "node:18": "node:18-alpine",
    "node:20": "node:20-alpine",
    # Python images
    "python:latest": "python:3.11-slim",
    "python:3": "python:3.11-slim",
}


async def get_ai_image_replacement(bad_image: str, error_message: str = "") -> Optional[str]:
    """
    Use AI to suggest replacement for ANY unavailable Docker image.

    This is a generic approach that works for all technologies:
    - Java, Python, Node, Go, Rust, Ruby, PHP, .NET
    - Databases, web servers, tools
    - Any current or future images

    Args:
        bad_image: The Docker image that failed (e.g., "openjdk:17-jdk-slim")
        error_message: Optional error context for better suggestions

    Returns:
        Replacement image string or None if AI couldn't suggest
    """
    import anthropic
    from app.core.config import settings

    # First check exact match (fast, no AI cost)
    if bad_image in DOCKERFILE_BASE_IMAGE_FIXES:
        return DOCKERFILE_BASE_IMAGE_FIXES[bad_image]

    try:
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        # Focused prompt - minimal tokens, fast response
        prompt = f"""Docker image "{bad_image}" is unavailable (manifest not found).

Return ONLY the working replacement image name. No explanation.

Requirements:
- Must be a real, currently available Docker Hub image
- Prefer official images or well-maintained alternatives
- Use alpine/slim variants when available for smaller size
- Keep the same major version if possible

Examples:
- openjdk:17-jdk-slim → eclipse-temurin:17-jdk-alpine
- maven:3.8-openjdk-17-slim → maven:3.9-eclipse-temurin-17-alpine
- node:18 → node:18-alpine
- python:3.11 → python:3.11-slim

Reply with ONLY the replacement image (e.g., "eclipse-temurin:17-jdk-alpine"):"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,  # Very small - just need image name
            temperature=0,  # Deterministic
            messages=[{"role": "user", "content": prompt}]
        )

        if response.content:
            replacement = response.content[0].text.strip()
            # Validate response looks like a Docker image
            if replacement and ':' in replacement and len(replacement) < 100:
                # Remove any quotes or extra text
                replacement = replacement.strip('"\'').split('\n')[0].strip()
                logger.info(f"[BoltFixer] AI suggested replacement: {bad_image} → {replacement}")
                return replacement

    except Exception as e:
        logger.warning(f"[BoltFixer] AI image replacement failed: {e}")

    return None


@dataclass
class BoltFixResult:
    """Result from BoltFixer - compatible with SimpleFixResult"""
    success: bool
    files_modified: List[str]
    message: str
    patches_applied: int = 0
    error_type: Optional[str] = None
    fix_strategy: Optional[str] = None
    current_pass: int = 1
    remaining_errors: int = 0
    needs_another_pass: bool = False


class BoltFixer:
    """
    Bolt.new style fixer with rule-based classification and atomic patches.

    Flow:
    1. Classify error (rule-based)
    2. Check if Claude-fixable
    3. Check retry limits
    4. Call Claude (strict prompt)
    5. Validate patch
    6. Apply atomically
    """

    # Strict system prompt - Claude returns ONLY diffs
    SYSTEM_PROMPT = """You are an automated code-fix agent.

STRICT RULES:
- Return ONLY unified diffs or file blocks
- Do NOT explain
- Do NOT invent files
- Do NOT modify unrelated code

CRITICAL - FIX ALL ERROR FILES IN ONE RESPONSE:
The build has MULTIPLE files with errors. You MUST fix ALL of them in a single response.
- Read the ERROR FILES section carefully - each file listed has errors
- Output a separate <file> or <patch> block for EACH file that needs fixing
- Do NOT just fix one file and stop - fix ALL files with errors

IMPORTANT - DEPENDENCY ERRORS:
When you see errors like:
- "cannot find symbol: method X()" - Add the missing method to the CLASS that should have it
- "no suitable constructor found for X(...)" - Fix the constructor in X.java, not the calling file
- "incompatible types" - Fix the SOURCE class that has wrong return type
- "cannot find symbol: class X" - The class file may be missing or has wrong package

FIX THE ROOT CAUSE, NOT THE SYMPTOM:
- If OrderService.java fails because Product.java is missing getPrice(), fix Product.java
- If the error file imports/uses another class, check RELATED FILES section for the fix
- Return patches for ALL files that need changes (you can return multiple patches)

JAVA CONSISTENCY (MULTI-FILE):
When fixing Java "cannot find symbol" errors:
1. You MUST check ALL RELATED FILES (Entity, DTO, Service, Controller)
2. Ensure field/method names match EXACTLY across related files
3. If DTO missing getter/setter - add it to the DTO
4. If Service interface missing method - add to BOTH interface AND implementation
5. Output MULTIPLE <file> blocks - one for EACH file that needs changes
6. If you see errors in UserDto, UserService, AND UserController - fix ALL THREE

OUTPUT FORMAT:

For patching existing files:
<patch>
--- path/to/file
+++ path/to/file
@@ -line,count +line,count @@
- old line
+ new line
</patch>

For creating missing files:
<newfile path="path/to/file">
file content
</newfile>

For full file replacement (syntax errors):
<file path="path/to/file">
complete file content
</file>

If no fix possible: <patch></patch>

No text outside blocks. No markdown. No commentary."""

    SYNTAX_FIX_PROMPT = """You are fixing a SYNTAX ERROR.

Return the COMPLETE fixed file using:
<file path="filepath">complete content</file>

Rules:
- Return ENTIRE file, not a patch
- Fix all bracket mismatches
- Remove duplicate code blocks
- Maintain proper structure

No explanations. Only the <file> block."""

    def __init__(self):
        self._claude_client = None
        self._sandbox_file_writer = None  # Set by fix_from_backend if provided
        self._sandbox_file_reader = None  # Set by fix_from_backend if provided
        self._sandbox_file_lister = None  # Set by fix_from_backend if provided
        self._dependency_graph: Optional[DependencyGraph] = None
        self._current_project_id: Optional[str] = None

    def _write_file(self, file_path: Path, content: str, project_id: str) -> bool:
        """
        Write a file using sandbox writer if available, otherwise local.

        In ECS/remote mode, files must be written via sandbox helper container,
        not directly via Python, because the sandbox filesystem is on a different host.
        """
        try:
            # AUTO-SANITIZE: Apply technology-specific fixes before writing
            # This handles CSS @import order, Tailwind plugins, Vite config, pom.xml, etc.
            try:
                relative_path = file_path.name  # Use filename for sanitizer matching
                sanitized_path, content, fixes = sanitize_project_file(relative_path, content)
                if fixes:
                    logger.info(f"[BoltFixer:{project_id}] Sanitizer applied: {', '.join(fixes)}")
            except Exception as sanitize_err:
                logger.warning(f"[BoltFixer:{project_id}] Sanitization skipped: {sanitize_err}")

            if self._sandbox_file_writer:
                # Use sandbox file writer (handles remote mode)
                # Use str(file_path) directly - path is already absolute from project_path / relative_path
                # Don't use resolve() as the directory may not exist on backend container
                abs_path = str(file_path)
                success = self._sandbox_file_writer(abs_path, content)
                if success:
                    logger.info(f"[BoltFixer:{project_id}] Wrote file via sandbox: {abs_path}")
                else:
                    logger.error(f"[BoltFixer:{project_id}] Sandbox write failed: {abs_path}")
                return success
            else:
                # Local mode - direct file write
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding='utf-8')
                logger.info(f"[BoltFixer:{project_id}] Wrote file locally: {file_path}")
                return True
        except Exception as e:
            logger.error(f"[BoltFixer:{project_id}] Error writing file {file_path}: {e}")
            return False

    async def _try_deterministic_dockerfile_fix(
        self,
        project_id: str,
        project_path: Path,
        error_output: str
    ) -> Optional[BoltFixResult]:
        """
        Deterministically fix Docker base image errors (NO AI NEEDED).

        This handles errors like:
        - "manifest for openjdk:17-jdk-slim not found"
        - "manifest unknown: manifest unknown"

        These are caused by deprecated/unavailable Docker base images.
        Fix: Replace with working alternatives from DOCKERFILE_BASE_IMAGE_FIXES.

        Args:
            project_id: Project ID for logging
            project_path: Path to project root
            error_output: Combined stdout/stderr from Docker build

        Returns:
            BoltFixResult if fixed, None if not applicable
        """
        # Check if this is a Docker base image error
        manifest_pattern = r'manifest for ([^\s]+) not found|manifest unknown.*manifest unknown'
        match = re.search(manifest_pattern, error_output, re.IGNORECASE)

        if not match:
            return None

        # Extract the problematic image name
        bad_image = match.group(1) if match.group(1) else None

        logger.info(f"[BoltFixer:{project_id}] Detected Docker base image error: {bad_image or 'unknown'}")

        # Find all Dockerfiles in the project
        dockerfile_paths = []
        possible_dockerfiles = [
            project_path / "Dockerfile",
            project_path / "backend" / "Dockerfile",
            project_path / "backend" / "Dockerfile.light",
            project_path / "frontend" / "Dockerfile",
        ]

        for dockerfile in possible_dockerfiles:
            try:
                if self._sandbox_file_reader:
                    content = self._sandbox_file_reader(str(dockerfile))
                    if content:
                        dockerfile_paths.append((dockerfile, content))
                elif dockerfile.exists():
                    dockerfile_paths.append((dockerfile, dockerfile.read_text(encoding='utf-8')))
            except Exception:
                continue

        if not dockerfile_paths:
            logger.warning(f"[BoltFixer:{project_id}] No Dockerfiles found to fix")
            return None

        files_modified = []

        for dockerfile_path, content in dockerfile_paths:
            original_content = content
            modified = False

            # Try to fix the specific bad image
            if bad_image:
                # Tier 1: Check exact match in dictionary (fast, no AI cost)
                replacement = DOCKERFILE_BASE_IMAGE_FIXES.get(bad_image)

                # Tier 2: Use AI to get replacement (generic, works for any image)
                if not replacement:
                    logger.info(f"[BoltFixer:{project_id}] No exact match for {bad_image}, asking AI...")
                    replacement = await get_ai_image_replacement(bad_image, error_output)

                # Apply the replacement if found
                if replacement:
                    pattern = rf'^(FROM\s+){re.escape(bad_image)}(\s|$)'
                    new_content = re.sub(pattern, rf'\g<1>{replacement}\2', content, flags=re.MULTILINE)
                    if new_content != content:
                        content = new_content
                        modified = True
                        logger.info(f"[BoltFixer:{project_id}] Fixed: {bad_image} -> {replacement}")

            # Also scan for any other deprecated images in the file (dictionary only - fast)
            for old_image, new_image in DOCKERFILE_BASE_IMAGE_FIXES.items():
                if old_image in content:
                    pattern = rf'^(FROM\s+){re.escape(old_image)}(\s|$)'
                    new_content = re.sub(pattern, rf'\g<1>{new_image}\2', content, flags=re.MULTILINE)
                    if new_content != content:
                        content = new_content
                        modified = True
                        logger.info(f"[BoltFixer:{project_id}] Fixed: {old_image} -> {new_image}")

            if modified and content != original_content:
                # Write the fixed content to sandbox
                if self._write_file(dockerfile_path, content, project_id):
                    try:
                        rel_path = str(dockerfile_path.relative_to(project_path))
                    except ValueError:
                        rel_path = str(dockerfile_path)

                    # IMMEDIATELY persist this fix to S3/database
                    # This ensures fix survives even if process crashes or retry limit reached
                    await self._persist_single_fix(project_id, project_path, rel_path, content)

                    files_modified.append(rel_path)
                    logger.info(f"[BoltFixer:{project_id}] ✓ Fixed & persisted: {rel_path}")

        if files_modified:
            return BoltFixResult(
                success=True,
                files_modified=files_modified,
                message=f"Deterministic fix: Replaced deprecated Docker base images in {len(files_modified)} file(s)",
                patches_applied=len(files_modified),
                error_type="dockerfile_base_image",
                fix_strategy="deterministic"
            )

        return None

    async def _persist_single_fix(
        self,
        project_id: str,
        project_path: Path,
        file_path: str,
        content: str
    ) -> bool:
        """
        Persist a SINGLE fix to S3/database IMMEDIATELY after fixing.

        This is called after EACH file is fixed, not at the end.
        Benefits:
        - No fixes lost if process crashes
        - Partial progress saved even if retry limit reached
        - User can continue from where they left off

        Args:
            project_id: Project ID
            project_path: Path to project root
            file_path: Relative path of fixed file
            content: Fixed file content

        Returns:
            True if persisted successfully, False otherwise
        """
        try:
            content_bytes = content.encode('utf-8')

            # Step 1: Upload to S3
            try:
                await storage_service.upload_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=content_bytes,
                    content_type="text/plain"
                )
                logger.info(f"[BoltFixer:{project_id}] ✓ S3: {file_path}")
            except Exception as s3_err:
                logger.warning(f"[BoltFixer:{project_id}] S3 failed: {file_path} - {s3_err}")
                return False

            # Step 2: Update database record
            try:
                from uuid import UUID
                from sqlalchemy import select
                from app.core.database import AsyncSessionLocal
                from app.models.project_file import ProjectFile
                import hashlib

                s3_key = f"projects/{project_id}/{file_path.replace(chr(92), '/')}"

                async with AsyncSessionLocal() as session:
                    stmt = select(ProjectFile).where(
                        ProjectFile.project_id == UUID(project_id),
                        ProjectFile.path == file_path
                    )
                    db_result = await session.execute(stmt)
                    file_record = db_result.scalar_one_or_none()

                    if file_record:
                        file_record.content_hash = hashlib.sha256(content_bytes).hexdigest()
                        file_record.size_bytes = len(content_bytes)
                        file_record.s3_key = s3_key
                        await session.commit()
                        logger.info(f"[BoltFixer:{project_id}] ✓ DB: {file_path}")
                    else:
                        logger.warning(f"[BoltFixer:{project_id}] No DB record: {file_path}")
                        return False

            except Exception as db_err:
                logger.warning(f"[BoltFixer:{project_id}] DB failed: {file_path} - {db_err}")
                return False

            return True

        except Exception as e:
            logger.error(f"[BoltFixer:{project_id}] Persist failed: {file_path} - {e}")
            return False

    async def _persist_fix_to_storage(
        self,
        project_id: str,
        project_path: Path,
        files_modified: List[str]
    ) -> None:
        """
        Persist fixes to database/S3 so they survive "restore from database" step.

        NOTE: This is now a fallback/batch method. Primary persistence happens
        in _persist_single_fix() immediately after each fix.
        """
        logger.info(f"[BoltFixer:{project_id}] Persisting {len(files_modified)} fix(es) to storage")

        for file_path in files_modified:
            try:
                # Read the fixed content
                full_path = project_path / file_path
                content = None

                if self._sandbox_file_reader:
                    content = self._sandbox_file_reader(str(full_path))
                elif full_path.exists():
                    content = full_path.read_text(encoding='utf-8')

                if not content:
                    logger.warning(f"[BoltFixer:{project_id}] Could not read fixed file: {file_path}")
                    continue

                content_bytes = content.encode('utf-8')

                # Upload to S3
                try:
                    await storage_service.upload_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content_bytes,
                        content_type="text/plain"
                    )
                    logger.info(f"[BoltFixer:{project_id}] ✓ Uploaded to S3: {file_path}")
                except Exception as s3_err:
                    logger.warning(f"[BoltFixer:{project_id}] S3 upload failed for {file_path}: {s3_err}")

                # Update database record with new hash, size, and s3_key
                try:
                    from uuid import UUID
                    from sqlalchemy import select
                    from app.core.database import AsyncSessionLocal
                    from app.models.project_file import ProjectFile
                    import hashlib

                    # Generate the s3_key that storage_service used
                    s3_key = f"projects/{project_id}/{file_path.replace(chr(92), '/')}"

                    async with AsyncSessionLocal() as session:
                        stmt = select(ProjectFile).where(
                            ProjectFile.project_id == UUID(project_id),
                            ProjectFile.path == file_path
                        )
                        db_result = await session.execute(stmt)
                        file_record = db_result.scalar_one_or_none()

                        if file_record:
                            # Update all relevant fields
                            file_record.content_hash = hashlib.sha256(content_bytes).hexdigest()
                            file_record.size_bytes = len(content_bytes)
                            file_record.s3_key = s3_key  # Ensure s3_key matches S3 upload
                            await session.commit()
                            logger.info(f"[BoltFixer:{project_id}] ✓ Updated DB: {file_path} (s3_key={s3_key})")
                        else:
                            logger.warning(f"[BoltFixer:{project_id}] No DB record for: {file_path}")
                except Exception as db_err:
                    logger.warning(f"[BoltFixer:{project_id}] DB update failed for {file_path}: {db_err}")

            except Exception as e:
                logger.error(f"[BoltFixer:{project_id}] Error persisting {file_path}: {e}")

    async def fix_from_backend(
        self,
        project_id: str,
        project_path: Path,
        payload: Dict[str, Any],
        sandbox_file_writer: Optional[Callable[[str, str], bool]] = None,
        sandbox_file_reader: Optional[Callable[[str], Optional[str]]] = None,
        sandbox_file_lister: Optional[Callable[[str, str], List[str]]] = None
    ) -> BoltFixResult:
        """
        BOLT.NEW STYLE: Fix errors from backend execution.

        Same interface as SimpleFixer.fix_from_backend for drop-in replacement.

        Args:
            project_id: Project ID
            project_path: Path to project files
            payload: Error payload from ExecutionContext
            sandbox_file_writer: Optional callback to write files directly to sandbox.
                                 Signature: (file_path: str, content: str) -> bool
                                 If None, uses local Path.write_text() (only works in local mode)
            sandbox_file_reader: Optional callback to read files from sandbox.
                                 Signature: (file_path: str) -> Optional[str]
                                 If None, uses local Path.read_text() (only works in local mode)
            sandbox_file_lister: Optional callback to list files matching a pattern from sandbox.
                                 Signature: (directory: str, pattern: str) -> List[str]
                                 If None, uses local glob (only works in local mode)

        Returns:
            BoltFixResult with success status and modified files
        """
        # Store the sandbox callbacks for use in file operations
        self._sandbox_file_writer = sandbox_file_writer
        self._sandbox_file_reader = sandbox_file_reader
        self._sandbox_file_lister = sandbox_file_lister
        # Extract payload
        stderr = payload.get("stderr", "")
        stdout = payload.get("stdout", "")
        exit_code = payload.get("exit_code", 1)
        error_file = payload.get("error_file")
        error_line = payload.get("error_line")
        primary_error_type = payload.get("primary_error_type")

        # Combine stdout and stderr for classification
        # Vite/esbuild errors often go to stdout, not stderr
        combined_output = f"{stderr}\n{stdout}".strip() if stderr or stdout else ""

        logger.info(
            f"[BoltFixer:{project_id}] fix_from_backend: "
            f"exit_code={exit_code}, stderr_len={len(stderr)}, stdout_len={len(stdout)}"
        )

        # =================================================================
        # STEP 1: CLASSIFY ERROR (Rule-based, NO AI)
        # =================================================================
        classified = ErrorClassifier.classify(
            error_message=combined_output[:2000],
            stderr=combined_output,
            exit_code=exit_code
        )

        logger.info(
            f"[BoltFixer:{project_id}] Classified: {classified.error_type.value}, "
            f"fixable={classified.is_claude_fixable}, confidence={classified.confidence}"
        )

        # =================================================================
        # STEP 2: DECISION GATE - Should Claude be called?
        # =================================================================
        should_call, reason = ErrorClassifier.should_call_claude(classified)
        if not should_call:
            logger.info(f"[BoltFixer:{project_id}] NOT calling Claude: {reason}")
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=reason,
                error_type=classified.error_type.value,
                fix_strategy="skipped"
            )

        # =================================================================
        # STEP 3: CHECK RETRY LIMITS
        # =================================================================
        error_hash = retry_limiter.hash_error(combined_output[:500])
        can_retry, retry_reason = retry_limiter.can_retry(project_id, error_hash)
        if not can_retry:
            logger.warning(f"[BoltFixer:{project_id}] Retry limit: {retry_reason}")
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=retry_reason,
                error_type=classified.error_type.value,
                fix_strategy="retry_blocked"
            )

        # =================================================================
        # STEP 3a: TRY DETERMINISTIC FIXES FIRST (fast, free, no AI cost)
        # =================================================================
        # Docker base image fixes (openjdk:17-jdk-slim -> eclipse-temurin:17-jdk-alpine)
        dockerfile_fix_result = await self._try_deterministic_dockerfile_fix(
            project_id=project_id,
            project_path=project_path,
            error_output=combined_output
        )
        if dockerfile_fix_result:
            logger.info(f"[BoltFixer:{project_id}] Deterministic Dockerfile fix applied - skipping AI")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=0, fixed=True)
            return dockerfile_fix_result

        # =================================================================
        # STEP 4: GATHER CONTEXT (file content for Claude)
        # =================================================================
        file_content = ""
        related_files_content = ""
        all_error_files_content = ""
        target_file = classified.file_path or error_file
        self._current_project_id = project_id

        # =================================================================
        # STEP 4a: Extract ALL error files with DEPENDENCY-AWARE SELECTION
        # =================================================================
        all_error_files = ErrorClassifier.extract_all_error_files(combined_output)
        total_error_count = len(all_error_files)
        logger.info(f"[BoltFixer:{project_id}] Found {total_error_count} files with errors: {[f[0] for f in all_error_files]}")

        # OPTIMIZATION: Only build dependency graph for multi-file errors
        # Single file errors don't need graph - just fix the file directly
        if total_error_count <= 1:
            logger.info(f"[BoltFixer:{project_id}] Single file error - skipping dependency graph")

        if total_error_count > 1:
            # BUILD DEPENDENCY GRAPH (only for multi-file errors)
            try:
                self._dependency_graph = build_dependency_graph(
                    project_path,
                    file_reader=self._sandbox_file_reader,
                    file_lister=self._sandbox_file_lister
                )
                graph_stats = self._dependency_graph.get_stats()
                logger.info(f"[BoltFixer:{project_id}] Dependency graph: {graph_stats}")
            except Exception as e:
                logger.warning(f"[BoltFixer:{project_id}] Could not build dependency graph: {e}")
                self._dependency_graph = None

            # USE DEPENDENCY GRAPH for smarter prioritization
            if self._dependency_graph:
                # Get fix order from dependency graph
                all_error_files = self._dependency_graph.get_fix_order(all_error_files)
                logger.info(f"[BoltFixer:{project_id}] Dependency-ordered files: {[f[0].split('/')[-1] for f in all_error_files[:6]]}")
            else:
                # Fallback to rule-based prioritization
                all_error_files = self._prioritize_error_files(all_error_files, combined_output)

            # USE BATCH TRACKER for multi-pass fixing
            batch_files, current_pass = batch_tracker.get_next_batch(
                project_id, all_error_files, MAX_FILES_PER_BATCH
            )

            if not batch_files:
                logger.info(f"[BoltFixer:{project_id}] No more batches to process")
                return BoltFixResult(
                    success=False,
                    files_modified=[],
                    message="All batches attempted",
                    error_type=classified.error_type.value,
                    fix_strategy="batch_exhausted",
                    current_pass=current_pass
                )

            # Check if batch can be attempted
            can_attempt, batch_reason = batch_tracker.can_attempt_batch(
                project_id, [f for f, _ in batch_files]
            )
            if not can_attempt:
                logger.warning(f"[BoltFixer:{project_id}] Batch blocked: {batch_reason}")
                return BoltFixResult(
                    success=False,
                    files_modified=[],
                    message=batch_reason,
                    error_type=classified.error_type.value,
                    fix_strategy="batch_blocked",
                    current_pass=current_pass
                )

            all_error_files = batch_files
            logger.info(f"[BoltFixer:{project_id}] Pass {current_pass}: Processing batch of {len(batch_files)} files")

            # READ with smart truncation and context limit tracking
            error_files_sections = []
            total_chars = 0

            for err_file, err_line in all_error_files:
                content = await self._read_file_content(project_path, err_file)
                if not content:
                    continue

                # SMART TRUNCATE: Keep relevant context around error
                if len(content) > CHARS_PER_FILE_LIMIT:
                    content = self._smart_truncate(content, err_line, CHARS_PER_FILE_LIMIT)

                # CHECK CONTEXT LIMIT: Stop if we're approaching max
                if total_chars + len(content) > MAX_CONTEXT_CHARS:
                    logger.warning(f"[BoltFixer:{project_id}] Context limit reached at {total_chars} chars, included {len(error_files_sections)} files")
                    break

                error_files_sections.append(f"""
--- ERROR FILE: {err_file} (line {err_line}) ---
```java
{content}
```
""")
                total_chars += len(content)

            if error_files_sections:
                all_error_files_content = "\n".join(error_files_sections)
                logger.info(f"[BoltFixer:{project_id}] Batch fixing {len(error_files_sections)}/{total_error_count} files ({total_chars} chars)")

        if target_file and project_path:
            # Try different paths to find the file
            possible_paths = [
                project_path / target_file,
                project_path / "frontend" / target_file,
                project_path / "backend" / target_file,
            ]

            for file_path in possible_paths:
                try:
                    # Use sandbox_file_reader for remote mode, local read for local mode
                    if self._sandbox_file_reader:
                        content = self._sandbox_file_reader(str(file_path))
                        if content:
                            file_content = content
                            logger.info(f"[BoltFixer:{project_id}] Read file via sandbox: {file_path} ({len(file_content)} chars)")
                            break
                    elif file_path.exists():
                        file_content = file_path.read_text(encoding='utf-8')
                        logger.info(f"[BoltFixer:{project_id}] Read file locally: {file_path} ({len(file_content)} chars)")
                        break
                except Exception as e:
                    logger.debug(f"[BoltFixer:{project_id}] Could not read {file_path}: {e}")
                    continue

            if not file_content:
                logger.warning(f"[BoltFixer:{project_id}] Could not read target file from any path: {target_file}")

        # For Java errors, also read related class files mentioned in the error
        if target_file and target_file.endswith('.java'):
            related_files_content = await self._read_related_java_files(
                project_path, combined_output, target_file
            )

        # =================================================================
        # STEP 5: CALL CLAUDE (strict prompt)
        # =================================================================
        # Choose prompt based on error type
        if classified.error_type == ErrorType.SYNTAX_ERROR:
            system_prompt = self.SYNTAX_FIX_PROMPT
            max_tokens = 16384
        else:
            system_prompt = self.SYSTEM_PROMPT
            # Increase max_tokens for batch fixing (multiple files)
            max_tokens = 16384 if len(all_error_files) > 1 else 4096

        # Build user prompt
        error_type_template = ErrorClassifier.get_claude_prompt_template(classified.error_type)

        # Include related files section if available
        related_section = ""
        if related_files_content:
            related_section = f"""
RELATED FILES (may need modification):
{related_files_content}
"""

        # Include all error files section for batch fixing
        all_errors_section = ""
        if all_error_files_content:
            all_errors_section = f"""
=== ALL FILES WITH ERRORS (FIX ALL OF THEM) ===
{all_error_files_content}
=== END OF ERROR FILES ===

IMPORTANT: The above files ALL have errors. Output a <file> or <patch> block for EACH one.
"""

        user_prompt = f"""{error_type_template}

ERROR: {combined_output[:2000]}
FILE: {target_file or 'unknown'}
LINE: {classified.line_number or error_line or 0}

FILE CONTENT:
```
{file_content[:10000] if file_content else 'No file content available'}
```
{all_errors_section}{related_section}
BUILD LOG:
{combined_output[-2000:]}
"""

        logger.info(f"[BoltFixer:{project_id}] Calling Claude for {classified.error_type.value}")

        try:
            response = await self._call_claude(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens
            )
        except Exception as e:
            logger.error(f"[BoltFixer:{project_id}] Claude call failed: {e}")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=0, fixed=False)
            return BoltFixResult(
                success=False,
                files_modified=[],
                message=f"Claude API error: {str(e)}",
                error_type=classified.error_type.value,
                fix_strategy="claude_error"
            )

        # Estimate tokens
        tokens_used = len(user_prompt.split()) + len(response.split())

        # =================================================================
        # STEP 6: PARSE RESPONSE
        # =================================================================
        patches = self._parse_patch_blocks(response)
        full_files = self._parse_file_blocks(response)
        new_files = self._parse_newfile_blocks(response)

        logger.info(
            f"[BoltFixer:{project_id}] Claude returned: "
            f"{len(patches)} patches, {len(full_files)} files, {len(new_files)} new files"
        )

        if not patches and not full_files and not new_files:
            logger.warning(f"[BoltFixer:{project_id}] No fixes in Claude response")
            retry_limiter.record_attempt(project_id, error_hash, tokens_used=tokens_used, fixed=False)
            return BoltFixResult(
                success=False,
                files_modified=[],
                message="Claude returned no fixes",
                error_type=classified.error_type.value,
                fix_strategy="no_fix"
            )

        # =================================================================
        # STEP 7: VALIDATE AND APPLY
        # =================================================================
        files_modified = []
        applier = PatchApplier(project_path)

        # Apply patches using DiffParser
        for patch in patches:
            patch_content = patch.get("patch", "")
            file_path = patch.get("path", "")

            # Validate
            result = PatchValidator.validate_diff(patch_content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid patch: {result.errors}")
                continue

            # Find target file
            parsed = DiffParser.parse(patch_content)
            actual_file = parsed.new_file or parsed.old_file or file_path

            # Try different paths to find the file
            possible_paths = [
                (project_path / actual_file, actual_file),
                (project_path / "frontend" / actual_file, f"frontend/{actual_file}"),
                (project_path / "backend" / actual_file, f"backend/{actual_file}"),
            ]

            original = None
            target_path = None
            final_file = actual_file

            for path, rel_path in possible_paths:
                try:
                    if self._sandbox_file_reader:
                        content = self._sandbox_file_reader(str(path))
                        if content:
                            original = content
                            target_path = path
                            final_file = rel_path
                            break
                    elif path.exists():
                        original = path.read_text(encoding='utf-8')
                        target_path = path
                        final_file = rel_path
                        break
                except Exception:
                    continue

            if original and target_path:
                try:
                    apply_result = DiffParser.apply(original, parsed)

                    if apply_result.success:
                        # Use sandbox-aware file writer
                        if self._write_file(target_path, apply_result.new_content, project_id):
                            # IMMEDIATELY persist to S3/database (survives restore)
                            await self._persist_single_fix(project_id, project_path, final_file, apply_result.new_content)
                            files_modified.append(final_file)
                            logger.info(f"[BoltFixer:{project_id}] Applied & persisted patch: {final_file}")
                except Exception as e:
                    logger.error(f"[BoltFixer:{project_id}] Error applying patch to {final_file}: {e}")

        # Apply full file replacements
        for file_info in full_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            # PROTECTION: Block full docker-compose.yml replacement
            # AI has been known to corrupt docker-compose.yml by deleting services
            if "docker-compose" in file_path.lower():
                logger.warning(
                    f"[BoltFixer:{project_id}] BLOCKING full docker-compose.yml replacement - "
                    "AI must use patches, not full file replacement"
                )
                continue

            # Validate
            result = PatchValidator.validate_full_file(file_path, content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid file: {result.errors}")
                continue

            # Determine best target path based on file type
            # IMPORTANT: Check if path already has backend/frontend prefix to avoid duplication
            if file_path.startswith('backend/') or file_path.startswith('frontend/'):
                # Path already has prefix, use as-is
                target_path = project_path / file_path
            elif file_path.endswith('.java'):
                target_path = project_path / "backend" / file_path
            elif file_path.endswith(('.ts', '.tsx', '.js', '.jsx', '.css', '.html')):
                target_path = project_path / "frontend" / file_path
            else:
                target_path = project_path / file_path

            # Use sandbox-aware file writer
            if self._write_file(target_path, content, project_id):
                # IMMEDIATELY persist to S3/database (survives restore)
                await self._persist_single_fix(project_id, project_path, file_path, content)
                files_modified.append(file_path)
                logger.info(f"[BoltFixer:{project_id}] Wrote & persisted full file: {file_path}")

        # Create new files
        for file_info in new_files:
            file_path = file_info.get("path", "")
            content = file_info.get("content", "")

            # PROTECTION: Don't create new docker-compose.yml if one already exists
            if "docker-compose" in file_path.lower():
                existing_compose = project_path / "docker-compose.yml"
                # Check existence using sandbox reader or local check
                exists = False
                if self._sandbox_file_reader:
                    exists = self._sandbox_file_reader(str(existing_compose)) is not None
                else:
                    exists = existing_compose.exists()

                if exists:
                    logger.warning(
                        f"[BoltFixer:{project_id}] BLOCKING creation of new docker-compose.yml - "
                        "original already exists"
                    )
                    continue

            # Validate
            result = PatchValidator.validate_new_file(file_path, content, project_path)
            if not result.is_valid:
                logger.warning(f"[BoltFixer:{project_id}] Invalid new file: {result.errors}")
                continue

            # Determine best target path based on file type
            # IMPORTANT: Check if path already has backend/frontend prefix to avoid duplication
            if file_path.startswith('backend/') or file_path.startswith('frontend/'):
                # Path already has prefix, use as-is
                target_path = project_path / file_path
            elif file_path.endswith('.java'):
                target_path = project_path / "backend" / file_path
            elif file_path.endswith(('.ts', '.tsx', '.js', '.jsx', '.css', '.html')):
                target_path = project_path / "frontend" / file_path
            else:
                target_path = project_path / file_path

            # Use sandbox-aware file writer
            if self._write_file(target_path, content, project_id):
                # IMMEDIATELY persist to S3/database (survives restore)
                await self._persist_single_fix(project_id, project_path, file_path, content)
                files_modified.append(file_path)
                logger.info(f"[BoltFixer:{project_id}] Created & persisted new file: {file_path}")

        # =================================================================
        # STEP 8: PERSISTENCE NOW HAPPENS IMMEDIATELY (above)
        # Each fix is persisted to S3/database right after it's applied.
        # This ensures fixes survive "restore from database" on retry.
        # Benefits:
        # - No fix is ever lost, even if build fails for another reason
        # - Retry doesn't re-fix the same files (efficient)
        # - If a fix is wrong, next fix attempt will overwrite it
        # =================================================================

        # =================================================================
        # STEP 9: RECORD BATCH ATTEMPT AND RETURN
        # =================================================================
        success = len(files_modified) > 0
        # Never mark as "fixed" - we can't know if fix is complete from here
        # MAX_RETRIES_PER_ERROR (3) prevents infinite loops
        # Container health check determines if truly fixed (container starts successfully)
        retry_limiter.record_attempt(project_id, error_hash, tokens_used=tokens_used, fixed=False)

        # Record batch attempt for multi-pass tracking
        current_pass = 1
        remaining_errors = total_error_count - len(files_modified)
        needs_another_pass = remaining_errors > 0 and success

        if total_error_count > 1:
            batch_tracker.record_batch_attempt(
                project_id=project_id,
                files=[f for f, _ in all_error_files],
                success=success,
                files_fixed=files_modified,
                error_count_before=total_error_count,
                error_count_after=remaining_errors
            )
            progress = batch_tracker.get_fix_progress(project_id)
            current_pass = progress.get("current_pass", 1)
            logger.info(
                f"[BoltFixer:{project_id}] Batch complete: "
                f"pass={current_pass}, fixed={len(files_modified)}, remaining={remaining_errors}"
            )

        return BoltFixResult(
            success=success,
            files_modified=files_modified,
            message=f"Pass {current_pass}: Fixed {len(files_modified)} file(s)" if success else "No files fixed",
            patches_applied=len(files_modified),
            error_type=classified.error_type.value,
            fix_strategy="bolt_fixer",
            current_pass=current_pass,
            remaining_errors=remaining_errors,
            needs_another_pass=needs_another_pass
        )

    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096
    ) -> str:
        """Call Claude API with strict prompts."""
        import anthropic

        if self._claude_client is None:
            from app.core.config import settings
            self._claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        response = self._claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=0.1,  # Very low for precise fixes
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return response.content[0].text if response.content else ""

    def _parse_patch_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <patch>...</patch> blocks."""
        import re
        patches = []
        pattern = r'<patch>(.*?)</patch>'

        for match in re.findall(pattern, response, re.DOTALL):
            content = match.strip()
            if not content:
                continue

            # Extract file path
            path_match = re.search(r'^(?:---|\+\+\+)\s+(?:[ab]/)?([^\s]+)', content, re.MULTILINE)
            file_path = path_match.group(1) if path_match else "unknown"

            patches.append({"path": file_path, "patch": content})

        return patches

    def _parse_file_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <file path="...">...</file> blocks."""
        import re
        files = []
        pattern = r'<file\s+path="([^"]+)">(.*?)</file>'

        for path, content in re.findall(pattern, response, re.DOTALL):
            files.append({"path": path.strip(), "content": content.strip()})

        return files

    def _parse_newfile_blocks(self, response: str) -> List[Dict[str, str]]:
        """Parse <newfile path="...">...</newfile> blocks."""
        import re
        files = []
        pattern = r'<newfile\s+path="([^"]+)">(.*?)</newfile>'

        for path, content in re.findall(pattern, response, re.DOTALL):
            # Clean markdown if present
            content = content.strip()
            if content.startswith('```'):
                lines = content.split('\n')[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                content = '\n'.join(lines)

            files.append({"path": path.strip(), "content": content.strip()})

        return files

    def _prioritize_error_files(
        self,
        error_files: List[Tuple[str, int]],
        error_output: str
    ) -> List[Tuple[str, int]]:
        """
        Prioritize files by error severity - fix ROOT CAUSE files first.

        Priority order:
        1. DTO/Entity files (often the root cause of "cannot find symbol")
        2. Files with most error mentions
        3. Service/Repository interfaces
        4. Other files

        Returns:
            Sorted list of (file_path, line_num) by priority
        """
        scored_files = []

        for file_path, line_num in error_files:
            score = 0
            file_name = Path(file_path).stem

            # Count how many times this file appears in errors
            error_count = error_output.lower().count(file_name.lower())
            score += error_count * 10

            # HIGH PRIORITY: DTO/Entity files (often root cause)
            if 'Dto' in file_name or 'DTO' in file_name:
                score += 100
            if 'Entity' in file_name or file_name[0].isupper() and len(file_name) < 20:
                # Short capitalized names are often entity classes
                score += 80

            # MEDIUM PRIORITY: Service interfaces (dependencies)
            if 'Service' in file_name and 'Impl' not in file_name:
                score += 60  # Interface before implementation
            if 'Repository' in file_name:
                score += 50

            # LOWER PRIORITY: Implementation files
            if 'ServiceImpl' in file_name or 'Impl' in file_name:
                score += 30
            if 'Controller' in file_name:
                score += 20

            # Boost if "cannot find symbol" mentions this class
            if f"class {file_name}" in error_output or f"symbol: class {file_name}" in error_output:
                score += 70

            # Boost if error location is IN this file
            if f"{file_path}:" in error_output or f"{file_name}.java:" in error_output:
                score += 40

            scored_files.append((file_path, line_num, score))

        # Sort by score (highest first)
        scored_files.sort(key=lambda x: x[2], reverse=True)

        # Log prioritization for debugging
        logger.info(f"[BoltFixer] File priority: {[(f[0].split('/')[-1], f[2]) for f in scored_files[:5]]}")

        # Return without score
        return [(f[0], f[1]) for f in scored_files]

    def _smart_truncate(
        self,
        content: str,
        error_line: int,
        max_chars: int = CHARS_PER_FILE_LIMIT
    ) -> str:
        """
        Truncate file content intelligently, keeping:
        1. Package/import declarations (top)
        2. Context around error line
        3. Class closing braces (bottom)

        Args:
            content: Full file content
            error_line: Line number where error occurred
            max_chars: Maximum characters to return

        Returns:
            Truncated content with markers
        """
        if len(content) <= max_chars:
            return content

        lines = content.split('\n')
        total_lines = len(lines)

        if error_line <= 0:
            error_line = total_lines // 2  # Default to middle

        # Sections to include
        result_sections = []
        chars_used = 0

        # SECTION 1: Keep first 15 lines (package, imports, class declaration)
        header_lines = min(15, total_lines)
        header = '\n'.join(lines[:header_lines])
        result_sections.append(header)
        chars_used += len(header)

        # SECTION 2: Context around error line
        context_lines = CONTEXT_LINES_AROUND_ERROR
        remaining_chars = max_chars - chars_used - 500  # Reserve for footer

        # Adjust context based on remaining space
        while context_lines > 10:
            start = max(header_lines, error_line - context_lines)
            end = min(total_lines - 5, error_line + context_lines)
            context = '\n'.join(lines[start:end])

            if len(context) <= remaining_chars:
                break
            context_lines -= 10

        start = max(header_lines, error_line - context_lines)
        end = min(total_lines - 5, error_line + context_lines)

        if start > header_lines:
            result_sections.append(f"\n// ... [TRUNCATED lines {header_lines + 1}-{start}] ...\n")

        result_sections.append('\n'.join(lines[start:end]))

        # SECTION 3: Keep last 5 lines (closing braces)
        if end < total_lines - 5:
            result_sections.append(f"\n// ... [TRUNCATED lines {end + 1}-{total_lines - 5}] ...\n")

        result_sections.append('\n'.join(lines[-5:]))

        truncated = '\n'.join(result_sections)
        logger.debug(f"[BoltFixer] Truncated file from {len(content)} to {len(truncated)} chars")

        return truncated

    async def _sync_to_s3(
        self,
        project_id: str,
        project_path: Path,
        files_modified: List[str]
    ) -> None:
        """
        Sync fixed files to S3 and update database for persistence.

        This ensures fixes survive container restarts.
        Database stores metadata, S3 stores content.

        NOTE: S3 sync ALWAYS happens for long-term archive.
        EFS is for fast working storage, S3 is for retrieval after months.
        The container_executor handles the sync after build success.
        """
        from uuid import UUID
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.project_file import ProjectFile
        from app.core.config import settings

        # Log EFS status but ALWAYS sync to S3 for long-term archive
        if getattr(settings, 'EFS_ENABLED', False):
            logger.info(f"[BoltFixer:{project_id}] EFS mode - files safe, archiving to S3 for long-term storage")

        for file_path in files_modified:
            try:
                # Read the fixed content from sandbox
                full_path = project_path / file_path
                actual_path = file_path  # Path to use for DB lookup

                if not full_path.exists():
                    # Try frontend subdirectory
                    full_path = project_path / "frontend" / file_path
                    if full_path.exists():
                        actual_path = f"frontend/{file_path}"

                if not full_path.exists():
                    # Try backend subdirectory
                    full_path = project_path / "backend" / file_path
                    if full_path.exists():
                        actual_path = f"backend/{file_path}"

                if not full_path.exists():
                    logger.warning(f"[BoltFixer:{project_id}] File not found for S3 sync: {file_path}")
                    continue

                content = full_path.read_text(encoding='utf-8')
                content_bytes = content.encode('utf-8')

                # Upload to S3
                result = await storage_service.upload_file(
                    project_id=project_id,
                    file_path=actual_path,
                    content=content_bytes,
                    content_type="text/plain"
                )

                # Update database record with new size and hash
                try:
                    async with AsyncSessionLocal() as session:
                        # Find existing file record
                        stmt = select(ProjectFile).where(
                            ProjectFile.project_id == UUID(project_id),
                            ProjectFile.path == actual_path
                        )
                        db_result = await session.execute(stmt)
                        file_record = db_result.scalar_one_or_none()

                        if file_record:
                            # Update existing record
                            file_record.s3_key = result['s3_key']
                            file_record.size_bytes = result['size_bytes']
                            file_record.content_hash = result['content_hash']
                            await session.commit()
                            logger.info(f"[BoltFixer:{project_id}] ✓ Updated DB: {actual_path}")
                        else:
                            logger.warning(f"[BoltFixer:{project_id}] No DB record for: {actual_path}")
                except Exception as db_err:
                    logger.warning(f"[BoltFixer:{project_id}] DB update failed for {actual_path}: {db_err}")

                logger.info(f"[BoltFixer:{project_id}] ✓ Synced to S3: {actual_path}")

            except Exception as e:
                logger.error(f"[BoltFixer:{project_id}] ✗ S3 sync failed for {file_path}: {e}")

    async def _read_related_java_files(
        self,
        project_path: Path,
        error_output: str,
        current_file: str
    ) -> str:
        """
        Extract and read Java class files mentioned in compilation errors.

        IMPORTANT: This method identifies ROOT CAUSE files, not just mentioned files.
        For errors like "cannot find symbol: method getPrice() in class Product",
        we need to read Product.java because THAT is where the fix should be applied.

        Works with both local and remote sandbox by using the sandbox callbacks.

        Args:
            project_path: Root path of the project
            error_output: Full error output from compilation
            current_file: The file already being read (to avoid duplicates)

        Returns:
            Formatted string with related file contents, marking ROOT CAUSE files
        """
        import re
        import glob

        # Get current file's class name to exclude
        current_class = None
        if current_file:
            current_class = Path(current_file).stem

        project_str = str(project_path)

        # =====================================================================
        # STEP 1: Extract ROOT CAUSE classes from error patterns
        # These are classes that likely need to be FIXED (not just referenced)
        # =====================================================================
        root_cause_classes = set()

        # Pattern: "cannot find symbol...in class X" or "cannot find symbol: class X"
        for match in re.finditer(r'cannot find symbol.*?(?:class|interface)\s+(\w+)', error_output, re.IGNORECASE):
            root_cause_classes.add(match.group(1))

        # Pattern: "location: variable xxx of type com.package.ClassName" - CRITICAL for Java errors
        # This catches errors like "location: variable userDto of type com.complaint.dto.UserDto"
        for match in re.finditer(r'location:\s*variable\s+\w+\s+of\s+type\s+(?:@[\w.]+\s+)?(?:[\w.]+\.)?(\w+)', error_output, re.IGNORECASE):
            root_cause_classes.add(match.group(1))

        # Pattern: "type com.package.ClassName" - generic type reference
        for match in re.finditer(r'\btype\s+(?:[\w.]+\.)?(\w+)(?:\s|$|,)', error_output):
            cls = match.group(1)
            if cls[0].isupper():  # Only class names (capitalized)
                root_cause_classes.add(cls)

        # Pattern: "no suitable constructor found for X(...)"
        for match in re.finditer(r'no suitable (?:constructor|method).*?for\s+(\w+)', error_output, re.IGNORECASE):
            root_cause_classes.add(match.group(1))

        # Pattern: "incompatible types...cannot be converted to X" or "found: X"
        for match in re.finditer(r'(?:cannot be converted to|found:\s*)(\w+)', error_output, re.IGNORECASE):
            cls = match.group(1)
            if cls[0].isupper():  # Only class names (capitalized)
                root_cause_classes.add(cls)

        # Pattern: "method X() in class Y" - Y is the root cause
        for match in re.finditer(r'method\s+\w+\([^)]*\)\s+in\s+(?:class|interface)\s+(\w+)', error_output, re.IGNORECASE):
            root_cause_classes.add(match.group(1))

        # Pattern: "variable xxxRepository of type com.package.XxxRepository" - for repository errors
        for match in re.finditer(r'variable\s+(\w+Repository)\s+of\s+type', error_output, re.IGNORECASE):
            root_cause_classes.add(match.group(1))

        # =====================================================================
        # STEP 1b: Add RELATED files by entity name pattern
        # If error is in UserServiceImpl, also include User, UserDto, UserService, UserRepository
        # =====================================================================
        if current_class:
            # Extract entity name from patterns like UserServiceImpl, UserService, UserController
            entity_patterns = [
                (r'^(\w+)ServiceImpl$', lambda m: m.group(1)),      # UserServiceImpl -> User
                (r'^(\w+)Service$', lambda m: m.group(1)),          # UserService -> User
                (r'^(\w+)Controller$', lambda m: m.group(1)),       # UserController -> User
                (r'^(\w+)Repository$', lambda m: m.group(1)),       # UserRepository -> User
                (r'^(\w+)Dto$', lambda m: m.group(1)),              # UserDto -> User
                (r'^(\w+)DTO$', lambda m: m.group(1)),              # UserDTO -> User
            ]

            entity_name = None
            for pattern, extractor in entity_patterns:
                match = re.match(pattern, current_class)
                if match:
                    entity_name = extractor(match)
                    break

            if entity_name:
                # Add all related class patterns
                related_patterns = [
                    entity_name,                    # User (entity)
                    f"{entity_name}Dto",            # UserDto
                    f"{entity_name}DTO",            # UserDTO
                    f"{entity_name}Service",        # UserService (interface)
                    f"{entity_name}ServiceImpl",    # UserServiceImpl
                    f"{entity_name}Repository",     # UserRepository
                    f"{entity_name}Controller",     # UserController
                ]
                for pattern in related_patterns:
                    if pattern != current_class:
                        root_cause_classes.add(pattern)
                logger.info(f"[BoltFixer] Added related classes for entity '{entity_name}': {related_patterns}")

        logger.info(f"[BoltFixer] Identified root cause classes: {root_cause_classes}")

        # =====================================================================
        # STEP 2: Find Java files - use sandbox_file_lister if available
        # =====================================================================
        all_java_files = []

        if self._sandbox_file_lister:
            try:
                all_java_files = self._sandbox_file_lister(project_str, "*.java")
                logger.info(f"[BoltFixer] Found {len(all_java_files)} Java files via sandbox lister")
            except Exception as e:
                logger.warning(f"[BoltFixer] Sandbox file listing failed: {e}")
                all_java_files = []
        else:
            all_java_files = glob.glob(f"{project_str}/**/*.java", recursive=True)

        # =====================================================================
        # STEP 3: Read files - prioritize ROOT CAUSE classes
        # =====================================================================
        related_contents = []
        files_found = 0

        # First pass: Read ROOT CAUSE files (these need to be fixed)
        for java_file in all_java_files:
            if files_found >= 8:  # Increased to accommodate related files
                break

            class_name = Path(java_file).stem

            if class_name == current_class:
                continue

            if class_name in root_cause_classes:
                content = self._read_java_file(java_file, project_path)
                if content:
                    related_contents.append(f"""
--- {content['path']} --- [ROOT CAUSE - FIX THIS FILE]
```java
{content['content'][:8000]}
```
""")
                    files_found += 1
                    logger.info(f"[BoltFixer] Read ROOT CAUSE file: {content['path']}")

        # Second pass: Read other mentioned files (for context)
        for java_file in all_java_files:
            if files_found >= 8:  # Increased to accommodate related files
                break

            class_name = Path(java_file).stem

            if class_name == current_class:
                continue

            if class_name in root_cause_classes:
                continue  # Already read

            if re.search(rf'\b{re.escape(class_name)}\b', error_output):
                content = self._read_java_file(java_file, project_path)
                if content:
                    related_contents.append(f"""
--- {content['path']} --- [CONTEXT]
```java
{content['content'][:8000]}
```
""")
                    files_found += 1
                    logger.info(f"[BoltFixer] Read context file: {content['path']}")

        if related_contents:
            logger.info(f"[BoltFixer] Found {files_found} related Java files")

        return "\n".join(related_contents)

    def _read_java_file(self, java_file: str, project_path: Path) -> Optional[Dict[str, str]]:
        """Helper to read a Java file from local or remote sandbox."""
        try:
            if self._sandbox_file_reader:
                content = self._sandbox_file_reader(java_file)
            else:
                content = Path(java_file).read_text(encoding='utf-8')

            if content:
                try:
                    rel_path = Path(java_file).relative_to(project_path)
                except ValueError:
                    rel_path = Path(java_file).name
                return {"path": str(rel_path), "content": content}
        except Exception as e:
            logger.warning(f"[BoltFixer] Could not read {java_file}: {e}")
        return None

    async def _read_file_content(self, project_path: Path, file_path: str) -> Optional[str]:
        """
        Read file content by trying multiple possible paths.

        Args:
            project_path: Root project path
            file_path: Relative file path (may or may not include backend/frontend prefix)

        Returns:
            File content or None if not found
        """
        # Try different path combinations
        possible_paths = [
            project_path / file_path,
            project_path / "frontend" / file_path,
            project_path / "backend" / file_path,
        ]

        # Also try without backend/ prefix if file_path already has it
        if file_path.startswith("backend/"):
            possible_paths.append(project_path / file_path.replace("backend/", ""))

        for path in possible_paths:
            try:
                if self._sandbox_file_reader:
                    content = self._sandbox_file_reader(str(path))
                    if content:
                        return content
                elif path.exists():
                    return path.read_text(encoding='utf-8')
            except Exception as e:
                logger.debug(f"[BoltFixer] Could not read {path}: {e}")
                continue

        return None


# Singleton instance
bolt_fixer = BoltFixer()
