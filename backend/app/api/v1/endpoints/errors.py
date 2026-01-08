"""
Unified Error Handler - Single Entry Point for All Errors

This module provides a centralized endpoint for receiving and processing
all types of errors from the frontend. It handles:
- Browser runtime errors
- Build/compile errors
- Docker container errors
- Network errors
- Backend errors

All errors are processed through the auto-fixer system automatically.
"""

import asyncio
import os
import tempfile
import shutil
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.simple_fixer import simple_fixer
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user_optional
from app.modules.auth.usage_limits import get_user_limits
from app.models.user import User
from app.services.log_bus import LogBus, get_log_bus
from app.services.auto_fixer import get_auto_fixer
from app.core.config import settings
from app.core.logging_config import logger
from pathlib import Path

# Import log stream manager for broadcasting errors to terminal
try:
    from app.api.v1.endpoints.log_stream import log_stream_manager
except ImportError:
    log_stream_manager = None

# Check if we're in remote Docker mode
IS_REMOTE_SANDBOX = bool(os.environ.get("SANDBOX_DOCKER_HOST"))

router = APIRouter()


class ErrorSource(str, Enum):
    """Source of the error (Bolt.new-style comprehensive capture)"""
    BROWSER = "browser"      # JS runtime errors
    BUILD = "build"          # Build/compile errors
    DOCKER = "docker"        # Container errors
    NETWORK = "network"      # Fetch/XHR errors
    BACKEND = "backend"      # Backend API errors
    TERMINAL = "terminal"    # Terminal output errors
    # NEW: Bolt.new-style error sources
    REACT = "react"          # React component errors
    HMR = "hmr"              # Hot Module Replacement errors
    RESOURCE = "resource"    # Resource load errors (img/script/css)
    CSP = "csp"              # Content Security Policy violations
    MODULE = "module"        # Module loader errors


class ErrorSeverity(str, Enum):
    """Severity level of the error"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorEntry(BaseModel):
    """Single error entry"""
    source: ErrorSource
    type: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    timestamp: Optional[int] = None


class RecentlyModifiedEntry(BaseModel):
    """Recently modified file entry"""
    path: str
    action: str  # 'created', 'updated', 'deleted'
    timestamp: int


class ErrorReportRequest(BaseModel):
    """Request body for error report"""
    errors: List[ErrorEntry]
    context: Optional[str] = None  # Full output context
    command: Optional[str] = None  # Command that was running
    timestamp: Optional[int] = None
    # Bolt.new-style fixer context
    file_tree: Optional[List[str]] = None  # All file paths in project
    recently_modified: Optional[List[RecentlyModifiedEntry]] = None  # Recently modified files


class ErrorReportResponse(BaseModel):
    """Response for error report"""
    success: bool
    project_id: str
    errors_received: int
    fix_triggered: bool
    fix_status: Optional[str] = None
    message: str


# WebSocket connections for real-time fix notifications
ws_connections: Dict[str, List[WebSocket]] = {}


@router.post("/report/{project_id}", response_model=ErrorReportResponse)
async def report_errors(
    project_id: str,
    request: ErrorReportRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    UNIFIED ERROR ENDPOINT - Single entry point for all errors

    This endpoint:
    1. Receives errors from all sources (browser, build, Docker, network)
    2. Logs them to the LogBus for tracking
    3. Triggers the auto-fixer automatically (if user has bug_fixing feature)
    4. Returns fix status

    NOTE: Bug fixing requires Premium plan. Free users can see errors but cannot auto-fix.
    """
    # Check if user has bug_fixing feature enabled
    can_auto_fix = True
    if current_user:
        try:
            limits = await get_user_limits(current_user, db)
            feature_flags = limits.feature_flags or {}
            can_auto_fix = feature_flags.get("bug_fixing", False) or feature_flags.get("all", False)
        except Exception as e:
            logger.warning(f"[ErrorHandler:{project_id}] Could not check feature flags: {e}")
            can_auto_fix = False
    else:
        # No user = anonymous, block auto-fix
        can_auto_fix = False

    if not request.errors:
        return ErrorReportResponse(
            success=True,
            project_id=project_id,
            errors_received=0,
            fix_triggered=False,
            message="No errors to process"
        )

    logger.info(f"[ErrorHandler:{project_id}] Received {len(request.errors)} errors")

    # Get LogBus for this project
    log_bus = get_log_bus(project_id)

    # Process each error and add to LogBus
    has_fixable_error = False
    primary_error = None

    for error in request.errors:
        logger.info(f"[ErrorHandler:{project_id}] Processing error: {error.source}/{error.type} - {error.message[:100]}")

        # Add to appropriate LogBus method based on source
        if error.source == ErrorSource.BROWSER:
            log_bus.add_browser_error(
                message=error.message,
                file=error.file,
                line=error.line,
                column=error.column,
                stack=error.stack
            )
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.BUILD:
            log_bus.add_build_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.DOCKER:
            log_bus.add_docker_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.NETWORK:
            log_bus.add_network_error(
                message=error.message,
                url=error.file or "",  # file field may contain URL
                status=error.line,  # line field may contain status code
                method="GET"
            )
            # Network errors are usually not auto-fixable

        elif error.source == ErrorSource.BACKEND:
            log_bus.add_backend_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        # ===== NEW: Bolt.new-style error sources =====
        elif error.source == ErrorSource.REACT:
            # React component errors (render errors, hook errors)
            log_bus.add_browser_error(
                message=f"[React] {error.message}",
                file=error.file,
                line=error.line,
                column=error.column,
                stack=error.stack
            )
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.HMR:
            # Hot Module Replacement errors (Vite/Webpack/Next.js)
            log_bus.add_build_error(message=f"[HMR] {error.message}")
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.RESOURCE:
            # Resource load errors (images, scripts, CSS)
            log_bus.add_browser_error(
                message=f"[Resource] {error.message}",
                file=error.file
            )
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.CSP:
            # Content Security Policy violations
            log_bus.add_browser_error(
                message=f"[CSP] {error.message}",
                file=error.file,
                line=error.line
            )
            # CSP errors might not be auto-fixable but log them
            has_fixable_error = False

        elif error.source == ErrorSource.MODULE:
            # Module loader errors (dynamic imports, missing modules)
            log_bus.add_build_error(message=f"[Module] {error.message}")
            has_fixable_error = True
            if not primary_error:
                primary_error = error

        elif error.source == ErrorSource.TERMINAL:
            # Terminal output errors
            log_bus.add_build_error(message=error.message)
            has_fixable_error = True
            if not primary_error:
                primary_error = error

    # Trigger auto-fix if we have fixable errors AND user has permission
    fix_triggered = False
    fix_status = None

    if has_fixable_error and primary_error:
        # Check if user can auto-fix
        if not can_auto_fix:
            logger.info(f"[ErrorHandler:{project_id}] Bug fixing blocked - upgrade required")
            return ErrorReportResponse(
                success=True,
                project_id=project_id,
                errors_received=len(request.errors),
                fix_triggered=False,
                fix_status="upgrade_required",
                message="Bug fixing requires Premium plan. Upgrade to automatically fix errors."
            )

        try:
            # Get the auto-fixer
            auto_fixer = get_auto_fixer(project_id)

            # Prepare error context
            error_context = request.context or primary_error.message
            stack_trace = primary_error.stack or ""

            # If we have full context, use it as the error message
            if request.context and len(request.context) > len(primary_error.message):
                error_context = request.context

            # IMPORTANT: Include actual docker/build errors from LogBus for better context
            docker_errors = log_bus.get_errors(source="docker")
            build_errors = log_bus.get_errors(source="build")
            if docker_errors or build_errors:
                all_error_entries = docker_errors + build_errors
                # Extract messages from error dicts, get last 20 for context
                error_messages = [e.get("message", "") for e in all_error_entries if e.get("level") == "error"]
                if error_messages:
                    error_logs = "\n".join(error_messages[-20:])
                    if error_logs and error_logs not in error_context:
                        error_context = f"{error_context}\n\nActual error output:\n{error_logs}"
                        logger.info(f"[ErrorHandler:{project_id}] Added {len(error_messages)} error logs to context")

            logger.info(f"[ErrorHandler:{project_id}] Triggering auto-fix...")
            logger.info(f"[ErrorHandler:{project_id}] Error: {error_context[:200]}")
            logger.info(f"[ErrorHandler:{project_id}] Command: {request.command}")

            # Notify WebSocket clients that fix is starting
            await notify_fix_started(project_id, primary_error.message[:100])

            # Trigger the fix (runs in background)
            # Convert errors to dict format for SimpleFixer
            errors_for_fixer = [
                {
                    "source": str(e.source.value) if hasattr(e.source, 'value') else str(e.source),
                    "type": e.type,
                    "message": e.message,
                    "file": e.file,
                    "line": e.line,
                    "column": e.column,
                    "stack": e.stack,
                    "severity": str(e.severity.value) if hasattr(e.severity, 'value') else str(e.severity)
                }
                for e in request.errors
            ]

            # Get user_id for token tracking
            fix_user_id = str(current_user.id) if current_user else None

            async def run_fix_with_logging():
                try:
                    logger.info(f"[ErrorHandler:{project_id}] Starting SimpleFixer background task...")
                    await execute_fix_with_notification(
                        project_id=project_id,
                        errors=errors_for_fixer,
                        context=error_context,
                        command=request.command,
                        file_tree=request.file_tree,
                        recently_modified=request.recently_modified,
                        user_id=fix_user_id
                    )
                    logger.info(f"[ErrorHandler:{project_id}] SimpleFixer background task completed")
                except Exception as e:
                    logger.error(f"[ErrorHandler:{project_id}] SimpleFixer background task FAILED: {e}")
                    import traceback
                    logger.error(traceback.format_exc())

            asyncio.create_task(run_fix_with_logging())

            fix_triggered = True
            fix_status = "fix_queued"

        except Exception as e:
            logger.error(f"[ErrorHandler:{project_id}] Failed to trigger auto-fix: {e}")
            fix_status = f"fix_error: {str(e)}"

    return ErrorReportResponse(
        success=True,
        project_id=project_id,
        errors_received=len(request.errors),
        fix_triggered=fix_triggered,
        fix_status=fix_status,
        message=f"Processed {len(request.errors)} errors" + (", fix triggered" if fix_triggered else "")
    )


async def execute_fix_with_notification(
    project_id: str,
    errors: List[Dict],
    context: str = "",
    command: Optional[str] = None,
    file_tree: Optional[List[str]] = None,
    recently_modified: Optional[List[RecentlyModifiedEntry]] = None,
    user_id: Optional[str] = None
):
    """Execute fix using SimpleFixer and send WebSocket notifications"""
    temp_dir = None
    try:
        # Find project path - handle remote sandbox mode
        project_path = None

        if IS_REMOTE_SANDBOX:
            # Remote sandbox mode: files are on EC2, need to restore from database
            logger.info(f"[ErrorHandler:{project_id}] Remote sandbox mode - restoring files from database")

            try:
                from app.services.unified_storage import UnifiedStorageService
                from app.core.database import AsyncSessionLocal

                # Create temp directory for fixer to work with
                temp_dir = tempfile.mkdtemp(prefix=f"fixer_{project_id[:8]}_")
                project_path = Path(temp_dir)

                # Restore files from database to temp directory
                async with AsyncSessionLocal() as db_session:
                    unified_storage = UnifiedStorageService()
                    restored_count = await unified_storage.restore_project_to_local(
                        db=db_session,
                        project_id=project_id,
                        target_path=project_path,
                        user_id=user_id
                    )
                    logger.info(f"[ErrorHandler:{project_id}] Restored {restored_count} files to temp directory")

            except Exception as restore_err:
                logger.error(f"[ErrorHandler:{project_id}] Failed to restore files: {restore_err}")
                import traceback
                logger.error(traceback.format_exc())
                # Try to get files directly from database as fallback
                project_path = None
        else:
            # Local mode: files are on the same machine
            project_path = Path(settings.USER_PROJECTS_PATH) / project_id

            if not project_path.exists():
                # Try sandbox path (uses settings.SANDBOX_PATH for EFS support)
                sandbox_base = Path(settings.SANDBOX_PATH)
                try:
                    for user_dir in sandbox_base.iterdir():
                        if user_dir.is_dir():
                            potential_path = user_dir / project_id
                            if potential_path.exists():
                                project_path = potential_path
                                break
                except FileNotFoundError:
                    logger.warning(f"[ErrorHandler:{project_id}] Sandbox path not found: {sandbox_base}")

        if project_path is None or not project_path.exists():
            logger.error(f"[ErrorHandler:{project_id}] Project path not found")
            await notify_fix_failed(project_id, "Could not find project files for auto-fix")
            return

        logger.info(f"[ErrorHandler:{project_id}] Using SimpleFixer (Bolt.new style)")
        logger.info(f"[ErrorHandler:{project_id}] Project path: {project_path}")

        # Convert recently_modified to dict format
        recently_mod_dicts = [
            {"path": f.path, "action": f.action, "timestamp": f.timestamp}
            for f in (recently_modified or [])
        ] if recently_modified else None

        # Reset token tracking before fix
        simple_fixer.reset_token_tracking()

        # Use SimpleFixer for ALL errors
        result = await simple_fixer.fix_from_frontend(
            project_id=project_id,
            project_path=project_path,
            errors=errors,
            context=context,
            command=command,
            file_tree=file_tree,
            recently_modified=recently_mod_dicts
        )

        # Save token transaction after fix
        token_usage = simple_fixer.get_token_usage()
        if token_usage.get("total_tokens", 0) > 0 and user_id:
            try:
                from app.services.token_tracker import token_tracker
                from app.models.usage import AgentType, OperationType

                await token_tracker.log_transaction_simple(
                    user_id=user_id,
                    project_id=project_id,
                    agent_type=AgentType.FIXER,
                    operation=OperationType.AUTO_FIX,
                    model=token_usage.get("model", "haiku"),
                    input_tokens=token_usage.get("input_tokens", 0),
                    output_tokens=token_usage.get("output_tokens", 0),
                    metadata={
                        "call_count": token_usage.get("call_count", 0),
                        "source": "simple_fixer",
                        "files_modified": result.files_modified if result.success else []
                    }
                )
                logger.info(f"[ErrorHandler:{project_id}] Token usage saved: {token_usage.get('total_tokens', 0)} tokens")
            except Exception as token_err:
                logger.warning(f"[ErrorHandler:{project_id}] Failed to save token usage: {token_err}")

        if result.success and result.files_modified:
            logger.info(f"[ErrorHandler:{project_id}] SimpleFixer completed: {len(result.files_modified)} files")

            # File tracking lists (defined outside try block to avoid NameError)
            config_files_modified = []
            source_files_modified = []
            env_files_modified = []
            startup_critical_modified = []  # Files that require container restart
            npm_files_modified = []  # package.json changes need npm install
            python_files_modified = []  # requirements.txt changes need pip install
            java_files_modified = []  # pom.xml/build.gradle changes need mvn/gradle
            go_files_modified = []  # go.mod changes need go mod download
            rust_files_modified = []  # Cargo.toml changes need cargo build

            # Sync modified files: SOURCE files to container (HMR), CONFIG files to DB/S3 only
            # CRITICAL: Config files (vite.config.ts, package.json, etc.) should NOT be synced
            # to running containers as they cause Vite to restart and create restart loops
            try:
                from app.services.unified_storage import UnifiedStorageService
                unified_storage = UnifiedStorageService()

                # Config files that should NOT be synced to running containers
                # These files cause Vite/build tool restarts when changed
                # NOTE: package.json moved to NPM_FILES - needs sync + npm install
                CONFIG_FILES = {
                    'vite.config.ts', 'vite.config.js', 'vite.config.mjs',
                    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',  # Lock files only
                    'tsconfig.json',
                    'postcss.config.js', 'postcss.config.cjs', 'postcss.config.mjs',
                    'tailwind.config.js', 'tailwind.config.ts',
                    'webpack.config.js', 'next.config.js', 'next.config.mjs',
                }

                # NPM FILES - MUST be synced + trigger npm install + restart
                # Covers: React, Vue, Next.js, Node.js, Blockchain (Hardhat/Truffle)
                NPM_FILES = {'package.json'}

                # PYTHON FILES - MUST be synced + trigger pip install + restart
                # Covers: FastAPI, Django, Flask, AI/ML (TensorFlow, PyTorch, scikit-learn)
                PYTHON_FILES = {'requirements.txt', 'pyproject.toml', 'environment.yml'}

                # JAVA FILES - MUST be synced + trigger mvn/gradle install + restart
                # Covers: Spring Boot, Java EE, Android
                JAVA_FILES = {'pom.xml', 'build.gradle', 'build.gradle.kts'}

                # GO FILES - MUST be synced + trigger go mod download + restart
                # Covers: Go microservices, Blockchain (Cosmos SDK)
                GO_FILES = {'go.mod', 'go.sum'}

                # RUST FILES - MUST be synced + trigger cargo build + restart
                # Covers: Rust, Blockchain (Solana, Substrate)
                RUST_FILES = {'Cargo.toml', 'Cargo.lock'}

                # Startup-critical files that SHOULD be synced but REQUIRE container restart
                # These are needed for Vite/build tools to start - if missing, Vite crashes
                STARTUP_CRITICAL_FILES = {
                    'tsconfig.node.json', 'tsconfig.app.json',  # Vite startup deps
                    'index.html',  # Entry point
                    'src/main.tsx', 'src/main.ts', 'src/main.jsx', 'src/main.js',  # App entry
                }

                # Environment files - sync to container but require restart
                ENV_FILES = {'.env', '.env.local', '.env.production', '.env.development'}

                for file_path in result.files_modified:
                    try:
                        full_path = project_path / file_path
                        if full_path.exists():
                            content = full_path.read_text(encoding='utf-8', errors='ignore')

                            # Check file type for sync strategy
                            file_name = Path(file_path).name
                            is_config_file = file_name in CONFIG_FILES
                            is_env_file = file_name in ENV_FILES
                            is_startup_critical = file_name in STARTUP_CRITICAL_FILES
                            is_npm_file = file_name in NPM_FILES
                            is_python_file = file_name in PYTHON_FILES
                            is_java_file = file_name in JAVA_FILES
                            is_go_file = file_name in GO_FILES
                            is_rust_file = file_name in RUST_FILES

                            # STEP 1: Sync SOURCE files, ENV files, and NPM files to RUNNING CONTAINER
                            # SKIP config files (except package.json) - they cause restart loops
                            # package.json MUST be synced for npm install to work
                            if IS_REMOTE_SANDBOX and user_id and not is_config_file:
                                # Retry logic with exponential backoff (configurable via settings)
                                max_retries = settings.CONTAINER_SYNC_MAX_RETRIES
                                retry_delay = 1.0  # Start with 1 second
                                retry_backoff = settings.CONTAINER_SYNC_RETRY_BACKOFF
                                container_synced = False

                                for attempt in range(max_retries):
                                    try:
                                        container_synced = await unified_storage._write_to_remote_sandbox(
                                            project_id=project_id,
                                            file_path=file_path,
                                            content=content,
                                            user_id=user_id
                                        )
                                        if container_synced:
                                            logger.info(f"[ErrorHandler:{project_id}] ✓ Synced to CONTAINER: {file_path}")
                                            if is_npm_file:
                                                npm_files_modified.append(file_path)
                                                logger.info(f"[ErrorHandler:{project_id}] 📦 NPM file synced: {file_path} (requires npm install)")
                                            elif is_python_file:
                                                python_files_modified.append(file_path)
                                                logger.info(f"[ErrorHandler:{project_id}] 🐍 Python file synced: {file_path} (requires pip install)")
                                            elif is_java_file:
                                                java_files_modified.append(file_path)
                                                logger.info(f"[ErrorHandler:{project_id}] ☕ Java file synced: {file_path} (requires mvn/gradle)")
                                            elif is_go_file:
                                                go_files_modified.append(file_path)
                                                logger.info(f"[ErrorHandler:{project_id}] 🐹 Go file synced: {file_path} (requires go mod download)")
                                            elif is_rust_file:
                                                rust_files_modified.append(file_path)
                                                logger.info(f"[ErrorHandler:{project_id}] 🦀 Rust file synced: {file_path} (requires cargo build)")
                                            elif is_startup_critical:
                                                startup_critical_modified.append(file_path)
                                                logger.info(f"[ErrorHandler:{project_id}] ⚡ Startup-critical file synced: {file_path} (requires restart)")
                                            elif is_env_file:
                                                env_files_modified.append(file_path)
                                            else:
                                                source_files_modified.append(file_path)
                                            break
                                        else:
                                            if attempt < max_retries - 1:
                                                logger.warning(f"[ErrorHandler:{project_id}] Container sync failed (attempt {attempt + 1}/{max_retries}): {file_path}")
                                                await asyncio.sleep(retry_delay)
                                                retry_delay *= retry_backoff  # Exponential backoff
                                            else:
                                                logger.error(f"[ErrorHandler:{project_id}] Container sync FAILED after {max_retries} attempts: {file_path}")
                                    except Exception as container_err:
                                        if attempt < max_retries - 1:
                                            logger.warning(f"[ErrorHandler:{project_id}] Container sync error (attempt {attempt + 1}/{max_retries}): {container_err}")
                                            await asyncio.sleep(retry_delay)
                                            retry_delay *= retry_backoff
                                        else:
                                            logger.error(f"[ErrorHandler:{project_id}] Container sync FAILED after {max_retries} attempts: {file_path} - {container_err}")
                            elif is_config_file:
                                config_files_modified.append(file_path)
                                logger.info(f"[ErrorHandler:{project_id}] ⚠️ Config file skipped for container sync: {file_path}")

                            # STEP 2: Save to database (Layer 3) for persistence
                            db_saved = await unified_storage.save_to_database(project_id, file_path, content)
                            if db_saved:
                                logger.info(f"[ErrorHandler:{project_id}] Synced to DB: {file_path}")

                            # STEP 3: Save to S3 (Layer 2) for persistence
                            if user_id:
                                try:
                                    s3_result = await unified_storage.upload_to_s3(
                                        user_id=user_id,
                                        project_id=project_id,
                                        file_path=file_path,
                                        content=content
                                    )
                                    if s3_result.get('success'):
                                        logger.info(f"[ErrorHandler:{project_id}] Synced to S3: {file_path}")
                                except Exception as s3_err:
                                    logger.warning(f"[ErrorHandler:{project_id}] S3 sync failed for {file_path}: {s3_err}")

                    except Exception as sync_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to sync {file_path}: {sync_err}")

                logger.info(f"[ErrorHandler:{project_id}] Synced {len(result.files_modified)} fixed files to Container + DB + S3")

                # STEP 4: If package.json was synced, run npm install in container
                # NOTE: Only run if file was actually synced (npm_files_modified), not just modified
                if npm_files_modified and IS_REMOTE_SANDBOX and user_id:
                    try:
                        from app.services.container_executor import container_executor

                        # Find the working directory (frontend/ or root)
                        pkg_file = npm_files_modified[0] if npm_files_modified else None
                        work_dir = "/app"
                        if pkg_file and '/' in pkg_file:
                            # e.g., frontend/package.json -> /app/frontend
                            work_dir = f"/app/{pkg_file.rsplit('/', 1)[0]}"

                        logger.info(f"[ErrorHandler:{project_id}] 📦 Running npm install after package.json sync (workdir={work_dir})")

                        # Find the container for this project
                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            # Run npm install in the container
                            exit_code, output = container.exec_run(
                                f"sh -c 'cd {work_dir} && npm install --legacy-peer-deps 2>&1'",
                                workdir="/app",
                                demux=True
                            )
                            stdout = output[0].decode('utf-8') if output[0] else ""
                            stderr = output[1].decode('utf-8') if output[1] else ""
                            full_output = stdout + stderr

                            if exit_code == 0:
                                logger.info(f"[ErrorHandler:{project_id}] ✓ npm install completed successfully")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] npm install exit code: {exit_code}")
                                logger.warning(f"[ErrorHandler:{project_id}] npm install output: {full_output[:500]}")
                        else:
                            logger.warning(f"[ErrorHandler:{project_id}] Container not found for npm install")
                    except Exception as npm_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to run npm install: {npm_err}")

                # STEP 4b: If requirements.txt was synced, run pip install in container
                if python_files_modified and IS_REMOTE_SANDBOX and user_id:
                    try:
                        from app.services.container_executor import container_executor

                        # Find the working directory (backend/ or root)
                        req_file = python_files_modified[0] if python_files_modified else None
                        work_dir = "/app"
                        if req_file and '/' in req_file:
                            # e.g., backend/requirements.txt -> /app/backend
                            work_dir = f"/app/{req_file.rsplit('/', 1)[0]}"

                        logger.info(f"[ErrorHandler:{project_id}] 🐍 Running pip install after requirements.txt sync (workdir={work_dir})")

                        # Find the container for this project
                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            # Run pip install in the container
                            exit_code, output = container.exec_run(
                                f"sh -c 'cd {work_dir} && pip install -r requirements.txt 2>&1'",
                                workdir="/app",
                                demux=True
                            )
                            stdout = output[0].decode('utf-8') if output[0] else ""
                            stderr = output[1].decode('utf-8') if output[1] else ""
                            full_output = stdout + stderr

                            if exit_code == 0:
                                logger.info(f"[ErrorHandler:{project_id}] ✓ pip install completed successfully")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] pip install exit code: {exit_code}")
                                logger.warning(f"[ErrorHandler:{project_id}] pip install output: {full_output[:500]}")
                        else:
                            logger.warning(f"[ErrorHandler:{project_id}] Container not found for pip install")
                    except Exception as pip_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to run pip install: {pip_err}")

                # STEP 4c: If pom.xml/build.gradle was synced, run mvn/gradle in container
                if java_files_modified and IS_REMOTE_SANDBOX and user_id:
                    try:
                        from app.services.container_executor import container_executor

                        java_file = java_files_modified[0]
                        work_dir = "/app"
                        if '/' in java_file:
                            work_dir = f"/app/{java_file.rsplit('/', 1)[0]}"

                        # Determine build tool (Maven vs Gradle)
                        is_gradle = 'gradle' in java_file.lower()
                        build_cmd = "gradle build --no-daemon" if is_gradle else "mvn install -DskipTests"

                        logger.info(f"[ErrorHandler:{project_id}] ☕ Running {build_cmd} (workdir={work_dir})")

                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            exit_code, output = container.exec_run(
                                f"sh -c 'cd {work_dir} && {build_cmd} 2>&1'",
                                workdir="/app",
                                demux=True
                            )
                            stdout = output[0].decode('utf-8') if output[0] else ""
                            if exit_code == 0:
                                logger.info(f"[ErrorHandler:{project_id}] ✓ Java build completed successfully")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] Java build exit code: {exit_code}")
                    except Exception as java_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to run Java build: {java_err}")

                # STEP 4d: If go.mod was synced, run go mod download in container
                if go_files_modified and IS_REMOTE_SANDBOX and user_id:
                    try:
                        from app.services.container_executor import container_executor

                        go_file = go_files_modified[0]
                        work_dir = "/app"
                        if '/' in go_file:
                            work_dir = f"/app/{go_file.rsplit('/', 1)[0]}"

                        logger.info(f"[ErrorHandler:{project_id}] 🐹 Running go mod download (workdir={work_dir})")

                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            exit_code, output = container.exec_run(
                                f"sh -c 'cd {work_dir} && go mod download 2>&1'",
                                workdir="/app",
                                demux=True
                            )
                            stdout = output[0].decode('utf-8') if output[0] else ""
                            if exit_code == 0:
                                logger.info(f"[ErrorHandler:{project_id}] ✓ Go mod download completed successfully")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] Go mod download exit code: {exit_code}")
                    except Exception as go_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to run go mod download: {go_err}")

                # STEP 4e: If Cargo.toml was synced, run cargo build in container
                if rust_files_modified and IS_REMOTE_SANDBOX and user_id:
                    try:
                        from app.services.container_executor import container_executor

                        rust_file = rust_files_modified[0]
                        work_dir = "/app"
                        if '/' in rust_file:
                            work_dir = f"/app/{rust_file.rsplit('/', 1)[0]}"

                        logger.info(f"[ErrorHandler:{project_id}] 🦀 Running cargo build (workdir={work_dir})")

                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            exit_code, output = container.exec_run(
                                f"sh -c 'cd {work_dir} && cargo build 2>&1'",
                                workdir="/app",
                                demux=True
                            )
                            stdout = output[0].decode('utf-8') if output[0] else ""
                            if exit_code == 0:
                                logger.info(f"[ErrorHandler:{project_id}] ✓ Cargo build completed successfully")
                            else:
                                logger.warning(f"[ErrorHandler:{project_id}] Cargo build exit code: {exit_code}")
                    except Exception as rust_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to run cargo build: {rust_err}")

            except Exception as storage_err:
                logger.warning(f"[ErrorHandler:{project_id}] Storage sync error: {storage_err}")


            # STEP 5: Handle file changes
            # SOURCE files: HMR handles automatically - preview refreshes without restart
            # CONFIG files: Need container restart to apply (npm install, etc.)
            # ENV files: Need container restart for process to pick up new env vars
            # STARTUP-CRITICAL files: Need container restart (vite crashed at startup)
            if startup_critical_modified:
                logger.info(f"[ErrorHandler:{project_id}] ⚡ STARTUP-CRITICAL files fixed: {startup_critical_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart REQUIRED - Vite needs these files to start")
                # Startup-critical files require restart (vite crashed, HMR won't help)
                config_files_modified.extend(startup_critical_modified)

            if npm_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] 📦 NPM files fixed: {npm_files_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart REQUIRED - dev server needs new packages")
                # NPM files require restart after npm install completes
                config_files_modified.extend(npm_files_modified)

            if python_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] 🐍 Python files fixed: {python_files_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart REQUIRED - Python needs new packages")
                # Python files require restart after pip install completes
                config_files_modified.extend(python_files_modified)

            if java_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] ☕ Java files fixed: {java_files_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart REQUIRED - Java needs rebuild")
                config_files_modified.extend(java_files_modified)

            if go_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] 🐹 Go files fixed: {go_files_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart REQUIRED - Go needs new modules")
                config_files_modified.extend(go_files_modified)

            if rust_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] 🦀 Rust files fixed: {rust_files_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart REQUIRED - Rust needs rebuild")
                config_files_modified.extend(rust_files_modified)

            if env_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] 🔧 ENV files fixed: {env_files_modified}")
                logger.info(f"[ErrorHandler:{project_id}] Container restart required for .env changes")
                # Treat env files same as config files - need restart
                config_files_modified.extend(env_files_modified)

            if config_files_modified:
                logger.info(f"[ErrorHandler:{project_id}] Config files fixed: {config_files_modified}")

                # AUTO-RESTART: When config files change, restart container with fixed files
                if IS_REMOTE_SANDBOX and user_id:
                    try:
                        logger.info(f"[ErrorHandler:{project_id}] 🔄 Auto-restarting container with fixed files...")

                        from app.services.container_executor import container_executor

                        # Step 1: Stop the current container
                        container = await container_executor._get_existing_container(project_id)
                        if container:
                            try:
                                container.stop(timeout=5)
                                container.remove(force=True)
                                logger.info(f"[ErrorHandler:{project_id}] ✓ Stopped old container")
                            except Exception as stop_err:
                                logger.warning(f"[ErrorHandler:{project_id}] Container stop warning: {stop_err}")

                        # Step 2: Get the sandbox path (uses settings.SANDBOX_PATH for EFS support)
                        sandbox_path = f"{settings.SANDBOX_PATH}/{user_id}/{project_id}"

                        # Step 3: Run the project again (will restore from S3, run npm install, start dev server)
                        logger.info(f"[ErrorHandler:{project_id}] 🚀 Starting fresh container...")

                        # Use asyncio to run in background so we don't block
                        import asyncio

                        async def restart_project():
                            try:
                                # Small delay to ensure files are synced to S3
                                await asyncio.sleep(2)

                                # Import here to avoid circular imports
                                from app.api.v1.endpoints.execution import _execute_docker_stream_with_progress
                                from app.core.database import AsyncSessionLocal

                                # Create a database session for the restart operation
                                async with AsyncSessionLocal() as db:
                                    # Run the project
                                    async for event in _execute_docker_stream_with_progress(
                                        project_id=project_id,
                                        user_id=user_id,
                                        db=db
                                    ):
                                        # Log progress but don't send to frontend (avoid confusion)
                                        if event.get("type") == "error":
                                            logger.error(f"[AutoRestart:{project_id}] {event.get('message', '')}")
                                        elif event.get("type") == "preview_ready":
                                            logger.info(f"[AutoRestart:{project_id}] ✓ Preview ready: {event.get('url', '')}")
                                            # Notify frontend that preview is ready
                                            await notify_fix_completed(project_id, len(config_files_modified), config_files_modified,
                                                                       extra_message="Auto-restart complete! Preview is ready.")
                                            break
                                        elif "server start detected" in str(event.get("message", "")).lower():
                                            logger.info(f"[AutoRestart:{project_id}] ✓ Server started")

                            except Exception as restart_err:
                                logger.error(f"[AutoRestart:{project_id}] Restart failed: {restart_err}")
                                import traceback
                                logger.error(traceback.format_exc())

                        # Run restart in background
                        asyncio.create_task(restart_project())
                        logger.info(f"[ErrorHandler:{project_id}] Auto-restart initiated in background")

                        # Notify that restart is happening
                        await notify_fix_started(project_id, "Restarting container with fixed files...")
                        return  # Exit early - restart task will send completion notification

                    except Exception as restart_err:
                        logger.error(f"[ErrorHandler:{project_id}] Auto-restart failed: {restart_err}")
                        import traceback
                        logger.error(traceback.format_exc())
                        # Fall back to manual restart message
                        logger.info(f"[ErrorHandler:{project_id}] Config changes will apply on next Run")

            if source_files_modified:
                # Source files only - HMR handles updates, just notify completion
                logger.info(f"[ErrorHandler:{project_id}] Source files synced via HMR: {source_files_modified}")

            await notify_fix_completed(project_id, result.patches_applied, result.files_modified)
        elif result.success:
            # SimpleFixer succeeded but didn't apply patches (e.g., package.json not in DB)
            # Try direct npm install for missing module errors as fallback
            if IS_REMOTE_SANDBOX and user_id:
                direct_packages = await _try_direct_npm_install_fallback(
                    project_id, errors, context, user_id
                )
                if direct_packages:
                    logger.info(f"[ErrorHandler:{project_id}] Direct npm install succeeded: {direct_packages}")
                    await notify_fix_completed(project_id, len(direct_packages),
                        [f"npm install {p}" for p in direct_packages])
                    return  # Exit early - fix was successful

            logger.info(f"[ErrorHandler:{project_id}] SimpleFixer: {result.message}")
            # No fix needed - don't notify as failed
        else:
            logger.warning(f"[ErrorHandler:{project_id}] SimpleFixer failed: {result.message}")
            await notify_fix_failed(project_id, result.message)

    except Exception as e:
        logger.error(f"[ErrorHandler:{project_id}] Fix execution error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await notify_fix_failed(project_id, str(e))
    finally:
        # Clean up temp directory if we created one
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"[ErrorHandler:{project_id}] Cleaned up temp directory")
            except Exception as cleanup_err:
                logger.warning(f"[ErrorHandler:{project_id}] Failed to cleanup temp dir: {cleanup_err}")


@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time fix notifications

    Connect to receive:
    - fix_started: When auto-fix begins
    - fix_completed: When fix is successful
    - fix_failed: When fix fails
    """
    await websocket.accept()

    # Add to connections
    if project_id not in ws_connections:
        ws_connections[project_id] = []
    ws_connections[project_id].append(websocket)

    logger.info(f"[ErrorHandler:{project_id}] WebSocket connected")

    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
            # Client can send ping/pong or other messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"[ErrorHandler:{project_id}] WebSocket disconnected")
    finally:
        if project_id in ws_connections:
            ws_connections[project_id].remove(websocket)
            if not ws_connections[project_id]:
                del ws_connections[project_id]


async def notify_fix_started(project_id: str, reason: str):
    """Notify WebSocket clients that fix has started"""
    await broadcast_to_project(project_id, {
        "type": "fix_started",
        "reason": reason,
        "timestamp": datetime.now().isoformat()
    })


async def notify_fix_completed(project_id: str, patches_applied: int, files_modified: List[str]):
    """Notify WebSocket clients that fix is complete"""
    await broadcast_to_project(project_id, {
        "type": "fix_completed",
        "patches_applied": patches_applied,
        "files_modified": files_modified,
        "timestamp": datetime.now().isoformat()
    })


async def notify_fix_failed(project_id: str, error: str):
    """Notify WebSocket clients that fix failed"""
    await broadcast_to_project(project_id, {
        "type": "fix_failed",
        "error": error,
        "timestamp": datetime.now().isoformat()
    })


async def _try_direct_npm_install_fallback(
    project_id: str,
    errors: List[Dict],
    context: str,
    user_id: str
) -> Optional[List[str]]:
    """
    Fallback: Directly run npm install for missing npm modules.

    This bypasses the need for package.json to be in the database/temp directory.
    Used when SimpleFixer can't find local files to modify but the error is
    clearly a missing npm package.

    Returns:
        List of installed packages if successful, None otherwise
    """
    import re

    # Known npm packages that are often missing
    KNOWN_NPM_PACKAGES = {
        '@tailwindcss/forms', '@tailwindcss/typography', '@tailwindcss/aspect-ratio',
        '@headlessui/react', '@radix-ui/react-dialog', '@radix-ui/react-slot',
        'clsx', 'class-variance-authority', 'tailwind-merge', 'lucide-react',
        'framer-motion', 'react-hook-form', '@hookform/resolvers', 'zod',
        'zustand', '@tanstack/react-query', 'date-fns', 'lodash', 'axios',
        'chart.js', 'react-chartjs-2', 'react-icons', 'daisyui',
    }

    # Patterns to extract missing package names
    patterns = [
        r"Cannot find module ['\"](@?[\w\-/.]+)['\"]",
        r"\[postcss\] Cannot find module ['\"](@?[\w\-/.]+)['\"]",
        r"Module not found.*Can't resolve ['\"](@?[\w\-/.]+)['\"]",
    ]

    # Combine all error messages and context
    combined_text = context + "\n" + "\n".join(e.get("message", "") for e in errors)

    # Extract missing packages
    missing_packages = set()
    for pattern in patterns:
        matches = re.findall(pattern, combined_text, re.IGNORECASE)
        for match in matches:
            pkg_name = match
            # Only include npm packages (not local files)
            if pkg_name.startswith('.') or pkg_name.startswith('/'):
                continue
            # Accept scoped packages (@scope/pkg) or known packages
            if pkg_name.startswith('@') or pkg_name in KNOWN_NPM_PACKAGES:
                missing_packages.add(pkg_name)

    if not missing_packages:
        logger.debug(f"[ErrorHandler:{project_id}] No missing npm packages detected for direct install")
        return None

    logger.info(f"[ErrorHandler:{project_id}] 📦 Attempting direct npm install for: {missing_packages}")

    try:
        from app.services.container_executor import container_executor

        # Get the container for this project
        container = await container_executor._get_existing_container(project_id)
        if not container:
            logger.warning(f"[ErrorHandler:{project_id}] No container found for direct npm install")
            return None

        # Install packages directly in the container
        packages_str = " ".join(missing_packages)
        install_cmd = f"npm install {packages_str} --save 2>&1"

        logger.info(f"[ErrorHandler:{project_id}] Running: {install_cmd}")

        exit_code, output = container.exec_run(
            f"sh -c 'cd /app && {install_cmd}'",
            demux=True
        )

        stdout = output[0].decode('utf-8') if output[0] else ""
        stderr = output[1].decode('utf-8') if output[1] else ""
        combined_output = stdout + stderr

        if exit_code == 0:
            logger.info(f"[ErrorHandler:{project_id}] ✅ Direct npm install succeeded: {packages_str}")
            logger.debug(f"[ErrorHandler:{project_id}] Output: {combined_output[:500]}")

            # Restart the dev server by stopping and letting it auto-restart
            try:
                # Kill any running dev server processes
                container.exec_run("sh -c 'pkill -f \"vite|next|webpack\" || true'", demux=True)
                logger.info(f"[ErrorHandler:{project_id}] Killed dev server for restart")

                # Give it a moment then restart
                import asyncio
                await asyncio.sleep(1)

                # Start the dev server again (in background)
                container.exec_run(
                    "sh -c 'cd /app && npm run dev > /tmp/dev.log 2>&1 &'",
                    detach=True
                )
                logger.info(f"[ErrorHandler:{project_id}] Dev server restarted")
            except Exception as restart_err:
                logger.warning(f"[ErrorHandler:{project_id}] Dev server restart failed: {restart_err}")

            return list(missing_packages)
        else:
            logger.warning(f"[ErrorHandler:{project_id}] Direct npm install failed (exit={exit_code}): {combined_output[:300]}")
            return None

    except Exception as e:
        logger.error(f"[ErrorHandler:{project_id}] Direct npm install error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


async def notify_rebuild_started(project_id: str):
    """Notify WebSocket clients that auto-rebuild is starting"""
    await broadcast_to_project(project_id, {
        "type": "rebuild_started",
        "message": "Rebuilding project after fix...",
        "timestamp": datetime.now().isoformat()
    })


async def notify_rebuild_completed(project_id: str, files_modified: List[str]):
    """Notify WebSocket clients that auto-rebuild is complete"""
    await broadcast_to_project(project_id, {
        "type": "rebuild_completed",
        "files_modified": files_modified,
        "message": "Project rebuilt successfully. Preview is ready.",
        "timestamp": datetime.now().isoformat()
    })

async def broadcast_to_project(project_id: str, message: dict):
    """Broadcast message to all WebSocket connections for a project"""
    import json

    if project_id not in ws_connections:
        return

    message_str = json.dumps(message)
    dead_connections = []

    for ws in ws_connections[project_id]:
        try:
            await ws.send_text(message_str)
        except Exception:
            dead_connections.append(ws)

    # Clean up dead connections
    for ws in dead_connections:
        ws_connections[project_id].remove(ws)


@router.get("/status/{project_id}")
async def get_error_status(project_id: str):
    """
    Get current error status for a project
    """
    log_bus = get_log_bus(project_id)
    auto_fixer = get_auto_fixer(project_id)

    # Get recent errors
    recent_errors = log_bus.get_recent_errors(limit=10)

    return {
        "project_id": project_id,
        "error_count": len(recent_errors),
        "recent_errors": recent_errors,
        "fix_attempts": auto_fixer.fix_attempts if hasattr(auto_fixer, 'fix_attempts') else 0,
        "is_fixing": auto_fixer.is_fixing if hasattr(auto_fixer, 'is_fixing') else False,
        "websocket_connections": len(ws_connections.get(project_id, []))
    }


# =============================================================================
# BROWSER ERROR CAPTURE ENDPOINT
# =============================================================================
# This endpoint receives errors from the browser error capture script
# (frontend/public/error-capture.js). The browser is the REPORTER, not the fixer.
# All actual fixing happens in the backend.
# =============================================================================

class BrowserErrorEntry(BaseModel):
    """Single browser error entry (from error-capture.js)"""
    type: str  # JS_RUNTIME, PROMISE_REJECTION, CONSOLE_ERROR, NETWORK_ERROR, RESOURCE_ERROR, REACT_ERROR
    category: str  # REFERENCE_ERROR, TYPE_ERROR, SYNTAX_ERROR, CORS_ERROR, etc.
    message: str
    file: Optional[str] = None
    source: Optional[str] = None  # Alternative to file
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = None
    framework: Optional[str] = None  # react, vue, angular, etc.
    timestamp: Optional[int] = None
    # Network error specific
    url: Optional[str] = None
    method: Optional[str] = None
    status: Optional[int] = None
    statusText: Optional[str] = None
    # Resource error specific
    resource: Optional[str] = None
    tagName: Optional[str] = None


class BrowserErrorReportRequest(BaseModel):
    """Request body for browser error report (from error-capture.js)"""
    project_id: str
    source: str = "browser"  # Always "browser" from this endpoint
    errors: List[BrowserErrorEntry]
    timestamp: int
    url: Optional[str] = None  # Page URL
    userAgent: Optional[str] = None


class BrowserErrorReportResponse(BaseModel):
    """Response for browser error report"""
    success: bool
    errors_received: int
    normalized_count: int
    fix_triggered: bool
    message: str


# Rule-based fixes for common browser errors (NO AI needed)
BROWSER_ERROR_RULES = {
    # Reference errors (missing imports, undefined variables)
    "REFERENCE_ERROR": {
        "is not defined": {
            "fix_type": "add_import",
            "description": "Missing import or variable declaration"
        },
        "is not a function": {
            "fix_type": "check_import",
            "description": "Function not imported or misspelled"
        }
    },
    # Type errors (null/undefined access)
    "TYPE_ERROR": {
        "cannot read properties of undefined": {
            "fix_type": "add_optional_chaining",
            "description": "Add optional chaining (?.) to prevent null access"
        },
        "cannot read properties of null": {
            "fix_type": "add_optional_chaining",
            "description": "Add optional chaining (?.) to prevent null access"
        },
        "is not a function": {
            "fix_type": "check_type",
            "description": "Check if variable is the expected type"
        }
    },
    # Network errors
    "NETWORK_ERROR": {
        "failed to fetch": {
            "fix_type": "check_backend",
            "description": "Backend server might be down or CORS issue"
        },
        "cors": {
            "fix_type": "add_cors_headers",
            "description": "Add CORS headers to backend"
        }
    },
    # Chunk load errors (usually stale cache)
    "CHUNK_LOAD_ERROR": {
        "loading chunk": {
            "fix_type": "clear_cache_reload",
            "description": "Clear cache and reload"
        },
        "chunk": {
            "fix_type": "rebuild",
            "description": "Rebuild the frontend bundle"
        }
    },
    # Hook errors (React specific)
    "HOOK_ERROR": {
        "invalid hook call": {
            "fix_type": "check_hooks",
            "description": "Hooks must be called at top level of component"
        },
        "rendered more hooks": {
            "fix_type": "fix_hook_order",
            "description": "Ensure hooks are called in the same order"
        }
    },
    # Hydration errors (SSR specific)
    "HYDRATION_ERROR": {
        "hydration": {
            "fix_type": "fix_hydration",
            "description": "Server/client content mismatch"
        }
    },
    # Module errors
    "MODULE_ERROR": {
        "cannot find module": {
            "fix_type": "npm_install",
            "description": "Run npm install to install missing module"
        },
        "failed to resolve import": {
            "fix_type": "check_import_path",
            "description": "Check import path and file existence"
        }
    }
}


def get_rule_based_fix(category: str, message: str) -> Optional[Dict[str, Any]]:
    """
    Try to get a rule-based fix for a browser error.
    Returns None if no rule matches (AI will be used instead).
    """
    rules = BROWSER_ERROR_RULES.get(category, {})
    message_lower = message.lower()

    for pattern, fix_info in rules.items():
        if pattern in message_lower:
            return fix_info

    return None


def normalize_browser_error(error: BrowserErrorEntry) -> Dict[str, Any]:
    """
    Normalize browser error into structured format for auto-fixer.

    This converts noisy browser errors into clean, structured events
    that the AI can reason about.
    """
    # Determine file from various sources
    file_path = error.file or error.source or error.url
    if file_path:
        # Clean up file path
        file_path = file_path.replace('http://localhost:3000', '')
        file_path = file_path.replace('https://localhost:3000', '')
        # Remove query params and hash
        if '?' in file_path:
            file_path = file_path.split('?')[0]
        if '#' in file_path:
            file_path = file_path.split('#')[0]

    # Get rule-based fix if available
    rule_fix = get_rule_based_fix(error.category, error.message)

    return {
        "source": "browser",
        "category": error.category,
        "type": error.type,
        "message": error.message,
        "file": file_path,
        "line": error.line,
        "column": error.column,
        "stack": error.stack,
        "framework": error.framework or "unknown",
        "timestamp": error.timestamp,
        # Rule-based fix info (if available)
        "has_rule_fix": rule_fix is not None,
        "rule_fix": rule_fix,
        # Network-specific
        "url": error.url,
        "method": error.method,
        "status": error.status,
    }


@router.post("/browser", response_model=BrowserErrorReportResponse)
async def report_browser_errors(
    request: BrowserErrorReportRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    BROWSER ERROR ENDPOINT - Receives errors from error-capture.js

    This endpoint:
    1. Receives errors captured in the browser (JS runtime, network, etc.)
    2. Normalizes them into structured format
    3. Applies rule-based fixes for common errors (NO AI)
    4. Triggers AI auto-fixer for complex errors

    ARCHITECTURE:
    - Browser = Reporter (captures and sends errors)
    - Backend = Doctor (analyzes and fixes errors)
    - Browser NEVER fixes itself

    Flow:
    Browser Error → Normalize → Rule Check → AI Fix → Rebuild → Browser Reload
    """
    project_id = request.project_id

    if not request.errors:
        return BrowserErrorReportResponse(
            success=True,
            errors_received=0,
            normalized_count=0,
            fix_triggered=False,
            message="No errors to process"
        )

    logger.info(f"[BrowserErrors:{project_id}] Received {len(request.errors)} browser errors")

    # Get LogBus for this project
    log_bus = get_log_bus(project_id)

    # Normalize all errors
    normalized_errors = []
    rule_fixable_errors = []
    ai_required_errors = []

    for error in request.errors:
        normalized = normalize_browser_error(error)
        normalized_errors.append(normalized)

        # Log to LogBus
        log_bus.add_browser_error(
            message=normalized["message"],
            file=normalized["file"],
            line=normalized["line"],
            column=normalized["column"],
            stack=normalized["stack"]
        )

        # Categorize by fix type
        if normalized["has_rule_fix"]:
            rule_fixable_errors.append(normalized)
        else:
            ai_required_errors.append(normalized)

    # BROADCAST ERRORS TO TERMINAL: Send errors to connected WebSocket clients
    # This makes browser errors visible in the execution terminal
    if log_stream_manager and normalized_errors:
        try:
            for err in normalized_errors[:10]:  # Limit to first 10 to avoid spam
                # Format error message for terminal display
                error_msg = f"[BROWSER] [{err['category']}] {err['message']}"
                if err["file"]:
                    error_msg = f"[BROWSER] {err['file']}"
                    if err["line"]:
                        error_msg += f":{err['line']}"
                    error_msg += f" - [{err['category']}] {err['message']}"

                # Broadcast to terminal
                await log_stream_manager.broadcast_to_project(project_id, {
                    "type": "browser_error",
                    "source": "browser",
                    "category": err["category"],
                    "message": err["message"],
                    "file": err["file"],
                    "line": err["line"],
                    "column": err["column"],
                    "stack": err.get("stack"),
                    "timestamp": datetime.utcnow().timestamp() * 1000,
                    # Also send as terminal-compatible format
                    "output": error_msg,
                    "stream": "stderr"
                })

            logger.debug(f"[BrowserErrors:{project_id}] Broadcasted {len(normalized_errors[:10])} errors to terminal")
        except Exception as broadcast_err:
            logger.warning(f"[BrowserErrors:{project_id}] Failed to broadcast to terminal: {broadcast_err}")

    logger.info(
        f"[BrowserErrors:{project_id}] Normalized {len(normalized_errors)} errors: "
        f"{len(rule_fixable_errors)} rule-fixable, {len(ai_required_errors)} need AI"
    )

    # Check if user can auto-fix
    can_auto_fix = True
    if current_user:
        try:
            limits = await get_user_limits(current_user, db)
            feature_flags = limits.feature_flags or {}
            can_auto_fix = feature_flags.get("bug_fixing", False) or feature_flags.get("all", False)
        except Exception as e:
            logger.warning(f"[BrowserErrors:{project_id}] Could not check feature flags: {e}")
            can_auto_fix = False
    else:
        can_auto_fix = False

    fix_triggered = False

    # Trigger fixes if we have fixable errors
    if normalized_errors and can_auto_fix:
        # Convert to ErrorEntry format for existing fix system
        errors_for_fixer = []
        for err in normalized_errors:
            errors_for_fixer.append({
                "source": "browser",
                "type": err["category"],
                "message": err["message"],
                "file": err["file"],
                "line": err["line"],
                "column": err["column"],
                "stack": err["stack"],
                "severity": "error"
            })

        try:
            # Notify WebSocket clients that fix is starting
            primary_message = normalized_errors[0]["message"][:100] if normalized_errors else "Browser error"
            await notify_fix_started(project_id, primary_message)

            # Get user_id for token tracking
            fix_user_id = str(current_user.id) if current_user else None

            # Build context
            context = f"Browser errors detected:\n"
            for err in normalized_errors[:5]:  # First 5 errors
                context += f"- [{err['category']}] {err['message'][:200]}\n"
                if err["file"]:
                    context += f"  File: {err['file']}"
                    if err["line"]:
                        context += f":{err['line']}"
                    context += "\n"
                if err["stack"]:
                    # First 3 lines of stack
                    stack_lines = err["stack"].split("\n")[:3]
                    context += f"  Stack: {' | '.join(stack_lines)}\n"

            # Trigger fix in background
            asyncio.create_task(execute_fix_with_notification(
                project_id=project_id,
                errors=errors_for_fixer,
                context=context,
                command=None,
                file_tree=None,
                recently_modified=None,
                user_id=fix_user_id
            ))

            fix_triggered = True
            logger.info(f"[BrowserErrors:{project_id}] Triggered fix for {len(errors_for_fixer)} errors")

        except Exception as fix_err:
            logger.error(f"[BrowserErrors:{project_id}] Failed to trigger fix: {fix_err}")

    return BrowserErrorReportResponse(
        success=True,
        errors_received=len(request.errors),
        normalized_count=len(normalized_errors),
        fix_triggered=fix_triggered,
        message=f"Processed {len(request.errors)} browser errors" + (
            f", fix triggered" if fix_triggered else
            ", upgrade required for auto-fix" if not can_auto_fix else ""
        )
    )


@router.post("/reset/{project_id}")
async def reset_error_state(project_id: str):
    """
    Reset error state for a project
    Clears error history and reset fix attempts
    """
    log_bus = get_log_bus(project_id)
    auto_fixer = get_auto_fixer(project_id)

    # Clear LogBus
    log_bus.clear()

    # Reset auto-fixer
    auto_fixer.reset_attempts()

    logger.info(f"[ErrorHandler:{project_id}] Reset error state")

    return {
        "success": True,
        "project_id": project_id,
        "message": "Error state reset successfully"
    }


# ==================== COST OPTIMIZATION: User Confirmation Endpoints ====================

@router.get("/pending-fix/{project_id}")
async def get_pending_fix(project_id: str):
    """
    Get pending fix details for user confirmation.

    Returns fix details including:
    - Error summary
    - Complexity classification (simple/moderate/complex)
    - Estimated API cost
    - Command that triggered the error
    """
    pending = simple_fixer.get_pending_fix(project_id)
    if not pending:
        return {
            "has_pending_fix": False,
            "project_id": project_id
        }

    return {
        "has_pending_fix": True,
        "project_id": project_id,
        **pending
    }


@router.post("/approve-fix/{project_id}")
async def approve_fix(
    project_id: str,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Approve and execute a pending fix.

    User clicked "Fix" button after seeing the estimated cost.
    Executes the fix and returns results.
    """
    # Find project path
    project_path = Path(settings.USER_PROJECTS_PATH) / project_id

    if not project_path.exists():
        # Use settings.SANDBOX_PATH for EFS support
        sandbox_base = Path(settings.SANDBOX_PATH)
        for user_dir in sandbox_base.iterdir():
            if user_dir.is_dir():
                potential_path = user_dir / project_id
                if potential_path.exists():
                    project_path = potential_path
                    break

    user_id = str(current_user.id) if current_user else None
    logger.info(f"[ErrorHandler:{project_id}] User approved fix, executing...")

    # Notify WebSocket clients
    await notify_fix_started(project_id, "User approved fix")

    try:
        # Reset token tracking before fix
        simple_fixer.reset_token_tracking()

        result = await simple_fixer.approve_and_execute_fix(project_id, project_path)

        if result.success and result.files_modified:
            # Sync modified files to database and S3
            try:
                from app.services.unified_storage import UnifiedStorageService
                unified_storage = UnifiedStorageService()

                for file_path in result.files_modified:
                    try:
                        full_path = project_path / file_path
                        if full_path.exists():
                            content = full_path.read_text(encoding='utf-8', errors='ignore')

                            # Save to database (Layer 3)
                            db_saved = await unified_storage.save_to_database(project_id, file_path, content)
                            if db_saved:
                                logger.info(f"[ErrorHandler:{project_id}] Synced to DB: {file_path}")

                            # Save to S3 (Layer 2) if user_id is available
                            if user_id:
                                try:
                                    s3_result = await unified_storage.upload_to_s3(
                                        user_id=user_id,
                                        project_id=project_id,
                                        file_path=file_path,
                                        content=content
                                    )
                                    if s3_result.get('success'):
                                        logger.info(f"[ErrorHandler:{project_id}] Synced to S3: {file_path}")
                                except Exception as s3_err:
                                    logger.warning(f"[ErrorHandler:{project_id}] S3 sync failed for {file_path}: {s3_err}")

                    except Exception as sync_err:
                        logger.warning(f"[ErrorHandler:{project_id}] Failed to sync {file_path}: {sync_err}")

                logger.info(f"[ErrorHandler:{project_id}] Synced {len(result.files_modified)} fixed files to DB and S3")
            except Exception as storage_err:
                logger.warning(f"[ErrorHandler:{project_id}] Storage sync error: {storage_err}")

            # Save token transaction
            token_usage = simple_fixer.get_token_usage()
            if token_usage.get("total_tokens", 0) > 0 and user_id:
                try:
                    from app.services.token_tracker import token_tracker
                    from app.models.usage import AgentType, OperationType

                    await token_tracker.log_transaction_simple(
                        user_id=user_id,
                        project_id=project_id,
                        agent_type=AgentType.FIXER,
                        operation=OperationType.AUTO_FIX,
                        model=token_usage.get("model", "haiku"),
                        input_tokens=token_usage.get("input_tokens", 0),
                        output_tokens=token_usage.get("output_tokens", 0),
                        metadata={
                            "call_count": token_usage.get("call_count", 0),
                            "source": "simple_fixer_approved",
                            "files_modified": result.files_modified
                        }
                    )
                    logger.info(f"[ErrorHandler:{project_id}] Token usage saved: {token_usage.get('total_tokens', 0)} tokens")
                except Exception as token_err:
                    logger.warning(f"[ErrorHandler:{project_id}] Failed to save token usage: {token_err}")

            await notify_fix_completed(project_id, result.patches_applied, result.files_modified)
        elif result.success:
            await notify_fix_completed(project_id, result.patches_applied, result.files_modified)
        else:
            await notify_fix_failed(project_id, result.message)

        return {
            "success": result.success,
            "project_id": project_id,
            "files_modified": result.files_modified,
            "patches_applied": result.patches_applied,
            "message": result.message
        }

    except Exception as e:
        logger.error(f"[ErrorHandler:{project_id}] Approved fix failed: {e}")
        await notify_fix_failed(project_id, str(e))
        return {
            "success": False,
            "project_id": project_id,
            "message": str(e)
        }


@router.post("/cancel-fix/{project_id}")
async def cancel_fix(project_id: str):
    """
    Cancel a pending fix.

    User decided not to proceed with the fix (to save API costs).
    """
    cancelled = simple_fixer.cancel_pending_fix(project_id)

    return {
        "success": cancelled,
        "project_id": project_id,
        "message": "Fix cancelled" if cancelled else "No pending fix found"
    }


@router.post("/set-auto-fix-mode")
async def set_auto_fix_mode(enabled: bool):
    """
    Toggle auto-fix mode.

    - enabled=True: Fix errors immediately (current behavior)
    - enabled=False: Queue fixes for user confirmation (Bolt.new style - saves costs)
    """
    simple_fixer.auto_fix_enabled = enabled
    logger.info(f"[ErrorHandler] Auto-fix mode set to: {enabled}")

    return {
        "success": True,
        "auto_fix_enabled": enabled,
        "message": f"Auto-fix {'enabled' if enabled else 'disabled (fixes will require confirmation)'}"
    }


@router.get("/auto-fix-mode")
async def get_auto_fix_mode():
    """Get current auto-fix mode setting"""
    return {
        "auto_fix_enabled": simple_fixer.auto_fix_enabled,
        "message": "Auto-fix is " + ("enabled" if simple_fixer.auto_fix_enabled else "disabled (requires confirmation)")
    }
