"""
Project Execution API - Run and execute generated projects in Docker containers

This module provides Docker-based project execution with:
1. Auto-generated Dockerfile if missing
2. Automatic port detection from container logs
3. Live preview URL for iframe embedding
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
import asyncio
import json
import zipfile
import io

from app.core.database import get_db
from app.core.logging_config import logger
from app.models.user import User
from app.models.project import Project
from app.modules.auth.dependencies import get_current_user, get_optional_user
from app.modules.auth.feature_flags import require_feature
from app.modules.orchestrator.dynamic_orchestrator import dynamic_orchestrator, ExecutionContext, OrchestratorEvent
from app.modules.automation.file_manager import FileManager
from app.modules.agents.production_fixer_agent import production_fixer_agent
from app.modules.agents.base_agent import AgentContext
from app.modules.execution.docker_executor import docker_executor, docker_compose_executor, FrameworkType, DEFAULT_PORTS
from app.services.unified_storage import unified_storage
from app.services.sandbox_cleanup import touch_project
from app.services.log_bus import get_log_bus

# Store running processes by project_id for stop functionality
_running_processes: dict[str, asyncio.subprocess.Process] = {}

# File manager instance for fallback
_file_manager = FileManager()


def get_project_path(project_id: str, user_id: str = None):
    """
    Get project path - checks sandbox first (C:/tmp/sandbox/workspace),
    then falls back to permanent storage (USER_PROJECTS_PATH).

    The sandbox is the primary location for runtime/execution because:
    1. Files are written here during generation for live preview
    2. It's designed for ephemeral execution

    Args:
        project_id: Project UUID string
        user_id: User UUID string (required for correct sandbox path)
    """
    from pathlib import Path

    # Try sandbox first with user_id (primary for execution)
    sandbox_path = unified_storage.get_sandbox_path(project_id, user_id)
    if sandbox_path.exists():
        return sandbox_path

    # If user_id provided but path doesn't exist, try without user_id for backward compat
    if user_id:
        legacy_sandbox_path = unified_storage.get_sandbox_path(project_id)
        if legacy_sandbox_path.exists():
            logger.warning(f"[Execution] Using legacy sandbox path for {project_id} (missing user_id prefix)")
            return legacy_sandbox_path

    # Fallback to permanent storage
    permanent_path = _file_manager.get_project_path(project_id)
    if permanent_path.exists():
        logger.info(f"[Execution] Using permanent storage for {project_id}")
        return permanent_path

    # Return sandbox path (will be checked for existence by caller)
    return sandbox_path


async def verify_project_ownership(project_id: str, current_user: User, db: AsyncSession) -> bool:
    """Helper function to verify project ownership"""
    try:
        # GUID columns are String(36), so compare as strings (not UUID)
        result = await db.execute(
            text("SELECT id FROM projects WHERE id = :project_id AND user_id = :user_id"),
            {"project_id": str(project_id), "user_id": str(current_user.id)}
        )
        return result.scalar_one_or_none() is not None
    except Exception as e:
        logger.warning(f"[Execution] verify_project_ownership error: {e}")
        return False

router = APIRouter()


class RunProjectRequest(BaseModel):
    project_id: str
    commands: Optional[List[str]] = None  # Optional: custom commands to run


class FixErrorRequest(BaseModel):
    """Request model for auto-fixing runtime errors (Bolt.new style)"""
    error_message: str
    stack_trace: Optional[str] = None
    error_type: Optional[str] = None  # syntax, runtime, import, type, logic
    affected_files: Optional[List[str]] = None  # Files mentioned in error
    command: Optional[str] = None  # Command that failed (npm run dev, etc.)
    error_logs: Optional[List[str]] = None  # Additional error logs from terminal


@router.post("/run/{project_id}")
async def run_project(
    project_id: str,
    request: Optional[RunProjectRequest] = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Run/execute a generated project in Docker container

    This endpoint:
    1. Creates project directory if needed
    2. Auto-generates Dockerfile if missing
    3. Builds Docker image
    4. Runs container with port mapping
    5. Detects running port from logs
    6. Returns preview URL for iframe embedding
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Touch the project to keep it alive during execution
        touch_project(project_id)

        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        # Check if sandbox needs restoration (files might have been cleaned up)
        # Restore from database if sandbox is empty or missing key folders
        needs_restore = False
        if not project_path.exists():
            needs_restore = True
        else:
            # Check if project has actual content (not just metadata)
            has_frontend = (project_path / "frontend").exists()
            has_backend = (project_path / "backend").exists()
            has_src = (project_path / "src").exists()
            has_package = (project_path / "package.json").exists()

            # If it looks like a monorepo but missing folders, restore
            if has_package and not has_frontend and not has_backend and not has_src:
                # Check if this is supposed to be a monorepo by looking at DB file count
                needs_restore = True
                logger.info(f"[Execution] Sandbox appears incomplete, will restore from database")

        if needs_restore:
            logger.info(f"[Execution] Restoring project {project_id} from database...")
            restored_files = await unified_storage.restore_project_from_database(project_id, user_id)
            if restored_files:
                logger.info(f"[Execution] Restored {len(restored_files)} files")
                # Update project_path after restore
                project_path = get_project_path(project_id, user_id)
            else:
                logger.warning(f"[Execution] No files restored from database")

        if not project_path.exists():
            logger.error(f"[Execution] Project not found: {project_id}")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        logger.info(f"[Execution] Running project from: {project_path}")
        logger.info(f"[Execution] Path has frontend: {(project_path / 'frontend').exists()}")
        logger.info(f"[Execution] Path has backend: {(project_path / 'backend').exists()}")

        # Stream Docker execution
        return StreamingResponse(
            _execute_docker_stream(project_id, project_path),
            media_type="text/event-stream"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop/{project_id}")
async def stop_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stop a running project execution (Docker container).

    This endpoint stops the Docker container for the specified project.
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Use smart stop_project which handles both Docker and direct execution
        stopped = await docker_executor.stop_project(project_id)

        if stopped:
            logger.info(f"Stopped project: {project_id}")
            return {"status": "stopped", "message": "Project stopped successfully"}
        else:
            return {"status": "not_running", "message": "No running project found"}

    except Exception as e:
        logger.error(f"Error stopping project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix/{project_id}")
async def fix_runtime_error(
    project_id: str,
    request: FixErrorRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-fix runtime errors using the AI Fixer Agent.

    This endpoint:
    1. Analyzes the error message and stack trace
    2. Identifies affected files
    3. Uses AI to generate fixes
    4. Returns fixed file contents to apply

    Returns:
    - success: bool
    - fixed_files: List of {path, content} objects
    - instructions: Optional shell commands to run (e.g., npm install)
    - analysis: Error analysis details
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Touch the project to keep it alive during fixing
        touch_project(project_id)

        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        logger.info(f"[Fixer] Auto-fixing error for project: {project_id}")
        logger.info(f"[Fixer] Error: {request.error_message[:200]}...")
        logger.info(f"[Fixer] Command: {request.command}")

        # ============= BOLT.NEW STYLE: Use LogBus for context =============
        log_bus = get_log_bus(project_id)

        # Add error to LogBus (for tracking)
        log_bus.add_build_error(
            message=request.error_message,
            file=request.affected_files[0] if request.affected_files else None
        )

        # Add additional error logs if provided
        if request.error_logs:
            for error_log in request.error_logs:
                log_bus.add_build_log(error_log, level="error")

        # Get Bolt.new-style fixer payload with file context
        fixer_payload = log_bus.get_bolt_fixer_payload(
            project_path=str(project_path),
            command=request.command or "unknown",
            error_message=request.error_message
        )

        # Get all project files for context
        project_files = []
        file_contents = {}

        # Skip patterns - check BEFORE calling is_file() to avoid Windows file lock errors
        skip_patterns = ['node_modules', '__pycache__', '.git', '.env', 'dist', 'build', '.bin']

        for file_path in project_path.rglob("*"):
            try:
                # Get relative path first to check skip patterns
                rel_path = str(file_path.relative_to(project_path)).replace("\\", "/")

                # Skip certain directories and files BEFORE checking is_file()
                if any(pattern in rel_path for pattern in skip_patterns):
                    continue

                # Now safely check if it's a file (can fail with WinError 1920 on locked files)
                if not file_path.is_file():
                    continue

                project_files.append(rel_path)

                # Read file content if it might be affected
                # Only read source files to limit context size
                if any(ext in rel_path for ext in ['.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.html', '.css', '.yml', '.yaml']):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Limit file size for context
                            if len(content) < 50000:
                                file_contents[rel_path] = content
                    except Exception as e:
                        logger.warning(f"Could not read file {rel_path}: {e}")

            except OSError as e:
                # Handle WinError 1920 and other OS errors for locked files
                # This is common on Windows when node_modules/.bin files are in use
                continue

        # Merge file contents from LogBus payload
        file_contents.update(fixer_payload.get("fileContext", {}))

        # Prepare context for fixer agent (Bolt.new style)
        context = AgentContext(
            project_id=project_id,
            user_request=f"Fix this error: {request.error_message}",
            metadata={
                "error_message": request.error_message,
                "stack_trace": request.stack_trace or "",
                "error_type": request.error_type,
                "affected_files": request.affected_files or fixer_payload.get("errorFiles", []),
                "project_files": project_files,
                "file_contents": file_contents,
                "project_path": str(project_path),
                # Bolt.new style additions
                "command": request.command or "unknown",
                "environment": fixer_payload.get("environment", {}),
                "error_logs": fixer_payload.get("errorLogs", {}),
                "package_json": fixer_payload.get("fileContext", {}).get("package.json"),
                "dockerfile": fixer_payload.get("fileContext", {}).get("Dockerfile"),
            }
        )

        # Call the fixer agent
        result = await production_fixer_agent.process(context)

        if not result.get("success"):
            logger.warning(f"Fixer agent failed: {result.get('error')}")
            return {
                "success": False,
                "error": result.get("error", "Failed to generate fix"),
                "suggestion": result.get("suggestion", "Manual intervention may be required")
            }

        # Process fixed files - save them to disk
        fixed_files = result.get("fixed_files", [])
        saved_files = []

        for file_info in fixed_files:
            file_path_str = file_info.get("path")
            content = file_info.get("content")

            if file_path_str and content:
                # Ensure file path is within project
                full_path = project_path / file_path_str

                # Safety check: path must be within project
                try:
                    full_path.resolve().relative_to(project_path.resolve())
                except ValueError:
                    logger.error(f"Security: Attempted to write outside project: {file_path_str}")
                    continue

                # Create directory if needed
                full_path.parent.mkdir(parents=True, exist_ok=True)

                # Write the fixed content
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                saved_files.append({
                    "path": file_path_str,
                    "content": content,
                    "saved": True
                })
                logger.info(f"✅ Fixed and saved: {file_path_str}")

        # Build response
        response = {
            "success": True,
            "fixed_files": saved_files,
            "files_count": len(saved_files),
            "instructions": result.get("instructions"),
            "analysis": {
                "error_type": result.get("analysis", {}).error_type if hasattr(result.get("analysis"), "error_type") else None,
                "root_cause": result.get("analysis", {}).root_cause if hasattr(result.get("analysis"), "root_cause") else None,
                "confidence": result.get("analysis", {}).confidence if hasattr(result.get("analysis"), "confidence") else None
            } if result.get("analysis") else None
        }

        logger.info(f"🎉 Successfully fixed {len(saved_files)} files for project {project_id}")

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fixing project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _get_available_port(start_port: int = 3001) -> int:
    """Find an available port starting from start_port"""
    import socket
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    return start_port


async def _execute_docker_stream(project_id: str, project_path):
    """
    Execute project with smart Docker/Direct fallback and stream output.

    Flow:
    1. Detect framework type
    2. Auto-generate Dockerfile if missing
    3. Try Docker execution first
    4. If Docker fails, fall back to direct execution
    5. Stream logs and detect server start
    6. Return preview URL when server is ready
    """
    from pathlib import Path
    project_path = Path(project_path)

    try:
        # Send start event
        yield f"data: {json.dumps({'type': 'start', 'data': {'project_id': project_id}})}\n\n"

        yield f"data: {json.dumps({'type': 'output', 'content': 'Checking project structure...'})}\n\n"

        server_started = False
        preview_url = None

        # Use smart run_project which handles Docker + fallback
        async for output in docker_executor.run_project(project_id, project_path):
            # Check for special server started marker
            if output.startswith("__SERVER_STARTED__:"):
                preview_url = output.split(":", 1)[1].strip()
                server_started = True

                # Extract port from URL
                import re
                port_match = re.search(r':(\d+)', preview_url)
                port = int(port_match.group(1)) if port_match else 3000

                # Send server_started event for frontend
                yield f"data: {json.dumps({'type': 'server_started', 'port': port, 'preview_url': preview_url})}\n\n"
            else:
                # Regular output
                yield f"data: {json.dumps({'type': 'output', 'content': output.strip()})}\n\n"

        # Send completion event
        if server_started and preview_url:
            yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'Server running', 'preview_url': preview_url}})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'Execution completed'}})}\n\n"

    except Exception as e:
        logger.error(f"Execution error for {project_id}: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


def _detect_project_type(project_path) -> dict:
    """Detect project type and return info"""
    project_info = {
        "type": "unknown",
        "frontend": False,
        "backend": False,
        "has_docker": False,
        "framework": None
    }

    # Check for Docker
    if (project_path / "docker-compose.yml").exists() or (project_path / "Dockerfile").exists():
        project_info["has_docker"] = True

    # Check for Node.js/Frontend
    package_json_path = None
    if (project_path / "package.json").exists():
        package_json_path = project_path / "package.json"
    elif (project_path / "frontend/package.json").exists():
        package_json_path = project_path / "frontend/package.json"

    if package_json_path:
        project_info["frontend"] = True
        try:
            import json
            with open(package_json_path) as f:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    project_info["framework"] = "nextjs"
                elif "vite" in deps:
                    project_info["framework"] = "vite"
                elif "react" in deps:
                    project_info["framework"] = "react"
                elif "vue" in deps:
                    project_info["framework"] = "vue"
                else:
                    project_info["framework"] = "nodejs"
        except:
            project_info["framework"] = "nodejs"

    # Check for Python/Backend
    if (project_path / "requirements.txt").exists() or (project_path / "backend/requirements.txt").exists():
        project_info["backend"] = True
        req_path = project_path / "requirements.txt"
        if (project_path / "backend/requirements.txt").exists():
            req_path = project_path / "backend/requirements.txt"
        try:
            with open(req_path) as f:
                reqs = f.read().lower()
                if "fastapi" in reqs:
                    project_info["framework"] = "fastapi"
                elif "flask" in reqs:
                    project_info["framework"] = "flask"
                elif "django" in reqs:
                    project_info["framework"] = "django"
        except:
            pass

    # Check for simple HTML
    if (project_path / "index.html").exists():
        project_info["frontend"] = True
        if not project_info["framework"]:
            project_info["framework"] = "static"

    # Determine type
    if project_info["frontend"] and project_info["backend"]:
        project_info["type"] = "fullstack"
    elif project_info["frontend"]:
        project_info["type"] = "frontend"
    elif project_info["backend"]:
        project_info["type"] = "backend"

    return project_info


def _validate_project_files(project_path, project_info: dict) -> dict:
    """Validate project has all required files before execution"""
    validation = {
        "valid": True,
        "missing_files": [],
        "warnings": []
    }

    # Check for required files based on project type
    if project_info["frontend"]:
        if project_info["framework"] in ["nextjs", "vite", "react", "vue", "nodejs"]:
            # Need package.json
            pkg_path = project_path / "package.json"
            frontend_pkg = project_path / "frontend" / "package.json"
            if not pkg_path.exists() and not frontend_pkg.exists():
                validation["missing_files"].append("package.json")
                validation["valid"] = False
            else:
                # Validate package.json has scripts
                try:
                    import json
                    pkg_file = pkg_path if pkg_path.exists() else frontend_pkg
                    with open(pkg_file) as f:
                        pkg = json.load(f)
                        if "scripts" not in pkg or "dev" not in pkg.get("scripts", {}):
                            validation["warnings"].append("package.json missing 'dev' script")
                except Exception as e:
                    validation["warnings"].append(f"Could not validate package.json: {e}")

        elif project_info["framework"] == "static":
            # Need index.html
            if not (project_path / "index.html").exists():
                validation["missing_files"].append("index.html")
                validation["valid"] = False

    if project_info["backend"]:
        # Need requirements.txt or main entry point
        has_reqs = (project_path / "requirements.txt").exists() or (project_path / "backend" / "requirements.txt").exists()
        has_main = (project_path / "main.py").exists() or (project_path / "app.py").exists()

        if not has_reqs and not has_main:
            validation["warnings"].append("No requirements.txt or main.py found")

    return validation


async def _auto_detect_commands(project_id: str, user_id: str = None) -> List[str]:
    """Auto-detect commands based on project files"""
    commands = []
    project_path = get_project_path(project_id, user_id)
    project_info = _detect_project_type(project_path)

    logger.info(f"Detected project type: {project_info}")

    # Validate project files first
    validation = _validate_project_files(project_path, project_info)
    if not validation["valid"]:
        logger.error(f"Project validation failed: {validation['missing_files']}")
        return []  # Return empty - let the caller handle the error

    for warning in validation.get("warnings", []):
        logger.warning(f"Project validation warning: {warning}")

    # Get available port for frontend
    frontend_port = _get_available_port(3001)
    backend_port = _get_available_port(8001)

    # Handle Docker projects first
    if project_info["has_docker"] and (project_path / "docker-compose.yml").exists():
        commands.append("docker-compose up -d")
        return commands

    # Handle frontend
    if project_info["frontend"]:
        frontend_dir = "frontend" if (project_path / "frontend").exists() else ""

        if project_info["framework"] == "static":
            # Simple HTML - use Python HTTP server
            commands.append(f"python -m http.server {frontend_port}")
        elif project_info["framework"] in ["nextjs", "vite", "react", "vue", "nodejs"]:
            install_cmd = f"cd {frontend_dir} && npm install" if frontend_dir else "npm install"

            # Check if package.json has scripts
            pkg_path = project_path / frontend_dir / "package.json" if frontend_dir else project_path / "package.json"
            run_cmd = f"cd {frontend_dir} && npm run dev -- --port {frontend_port}" if frontend_dir else f"npm run dev -- --port {frontend_port}"

            # Framework-specific adjustments
            if project_info["framework"] == "vite":
                run_cmd = f"cd {frontend_dir} && npm run dev -- --port {frontend_port} --host" if frontend_dir else f"npm run dev -- --port {frontend_port} --host"
            elif project_info["framework"] == "nextjs":
                run_cmd = f"cd {frontend_dir} && npm run dev -- -p {frontend_port}" if frontend_dir else f"npm run dev -- -p {frontend_port}"

            commands.extend([install_cmd, run_cmd])

    # Handle backend
    if project_info["backend"]:
        backend_dir = "backend" if (project_path / "backend").exists() else ""

        install_cmd = f"cd {backend_dir} && pip install -r requirements.txt" if backend_dir else "pip install -r requirements.txt"

        # Framework-specific run commands
        if project_info["framework"] == "fastapi":
            run_cmd = f"cd {backend_dir} && uvicorn main:app --reload --host 0.0.0.0 --port {backend_port}" if backend_dir else f"uvicorn main:app --reload --host 0.0.0.0 --port {backend_port}"
        elif project_info["framework"] == "flask":
            run_cmd = f"cd {backend_dir} && flask run --host 0.0.0.0 --port {backend_port}" if backend_dir else f"flask run --host 0.0.0.0 --port {backend_port}"
        elif project_info["framework"] == "django":
            run_cmd = f"cd {backend_dir} && python manage.py runserver 0.0.0.0:{backend_port}" if backend_dir else f"python manage.py runserver 0.0.0.0:{backend_port}"
        else:
            # Generic Python
            main_file = "main.py" if (project_path / "main.py").exists() else "app.py"
            run_cmd = f"cd {backend_dir} && python {main_file}" if backend_dir else f"python {main_file}"

        commands.extend([install_cmd, run_cmd])

    return commands


async def _execute_commands_stream(project_id: str, commands: List[str], user_id: str = None):
    """Execute commands and stream output"""
    global _running_processes
    # Get project path (sandbox first, then permanent storage)
    project_path = get_project_path(project_id, user_id)

    # Send start event
    yield f"data: {json.dumps({'type': 'start', 'data': {'project_id': project_id, 'commands': commands}})}\n\n"

    for idx, command in enumerate(commands):
        try:
            # Send command start event
            yield f"data: {json.dumps({'type': 'command_start', 'data': {'command': command, 'index': idx}})}\n\n"

            # Execute command
            logger.info(f"Executing: {command} in {project_path}")

            # Use subprocess for actual execution
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project_path)
            )

            # Store process for stop functionality
            _running_processes[project_id] = process

            # Stream stdout
            async for line in process.stdout:
                output = line.decode().strip()
                if output:
                    yield f"data: {json.dumps({'type': 'output', 'data': {'output': output, 'stream': 'stdout'}})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for streaming

            # Wait for completion
            await process.wait()

            # Get stderr if any
            stderr = await process.stderr.read()
            if stderr:
                error_output = stderr.decode().strip()
                yield f"data: {json.dumps({'type': 'output', 'data': {'output': error_output, 'stream': 'stderr'}})}\n\n"

            # Send command complete event
            success = process.returncode == 0
            yield f"data: {json.dumps({'type': 'command_complete', 'data': {'command': command, 'success': success, 'exit_code': process.returncode}})}\n\n"

            if not success:
                logger.warning(f"Command failed with exit code {process.returncode}: {command}")
                # Continue to next command even if this one failed

        except asyncio.CancelledError:
            logger.info(f"Execution cancelled for project {project_id}")
            yield f"data: {json.dumps({'type': 'cancelled', 'data': {'message': 'Execution cancelled'}})}\n\n"
            break
        except Exception as e:
            logger.error(f"Error executing command '{command}': {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'command': command, 'error': str(e)}})}\n\n"

    # Clean up
    if project_id in _running_processes:
        del _running_processes[project_id]

    # Send completion event
    yield f"data: {json.dumps({'type': 'complete', 'data': {'message': 'All commands executed'}})}\n\n"


@router.get("/validate/{project_id}")
async def validate_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Validate if a project is ready to run.
    Returns validation status, detected type, and suggested commands.
    """
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Detect project type
        project_info = _detect_project_type(project_path)

        # Validate files
        validation = _validate_project_files(project_path, project_info)

        # Get suggested commands
        commands = await _auto_detect_commands(project_id, user_id)

        return {
            "project_id": project_id,
            "valid": validation["valid"],
            "missing_files": validation["missing_files"],
            "warnings": validation["warnings"],
            "project_info": project_info,
            "suggested_commands": commands,
            "ready_to_run": validation["valid"] and len(commands) > 0
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{project_id}")
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current status of a project"""
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        if not project_path.exists():
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Check what's in the project
        files = []
        # Skip patterns to avoid Windows file lock errors (WinError 1920)
        skip_patterns = ['node_modules', '__pycache__', '.git', '.env', 'dist', 'build', '.bin']
        for file_path in project_path.rglob("*"):
            try:
                rel_path_str = str(file_path.relative_to(project_path)).replace("\\", "/")
                # Skip system/locked directories before calling is_file()
                if any(pattern in rel_path_str for pattern in skip_patterns):
                    continue
                if file_path.is_file() and not rel_path_str.startswith('.'):
                    files.append(rel_path_str)
            except OSError:
                # Handle WinError 1920 and other OS errors for locked files
                continue

        # Detect project type
        project_info = _detect_project_type(project_path)

        # Validate
        validation = _validate_project_files(project_path, project_info)

        return {
            "project_id": project_id,
            "path": str(project_path),
            "type": project_info.get("framework", "unknown"),
            "project_info": project_info,
            "files_count": len(files),
            "files": files[:20],  # Return first 20 files
            "valid": validation["valid"],
            "warnings": validation["warnings"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{project_id}")
async def export_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("download_files"))
):
    """Export entire project as ZIP file"""
    # Verify project ownership (skip if no auth in dev mode)
    if current_user and not await verify_project_ownership(project_id, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    try:
        # Touch the project to keep it alive during export
        touch_project(project_id)

        # Get project path (sandbox first, then permanent storage)
        user_id = str(current_user.id) if current_user else None
        project_path = get_project_path(project_id, user_id)

        logger.info(f"[Export] Attempting to export project: {project_id}")
        logger.info(f"[Export] Project path: {project_path}")
        logger.info(f"[Export] Path exists: {project_path.exists()}")

        if not project_path.exists():
            logger.error(f"[Export] Project directory not found: {project_path}")
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        files_added = 0

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Skip certain files/folders - check BEFORE is_file() to avoid WinError 1920
            skip_patterns = [
                '.project_metadata.json',
                '__pycache__',
                'node_modules',
                '.git',
                '.DS_Store',
                'Thumbs.db',
                '.bin'
            ]

            # Walk through all files in project
            for file_path in project_path.rglob("*"):
                try:
                    # Get relative path and check skip patterns FIRST (before is_file())
                    rel_path = file_path.relative_to(project_path)
                    rel_path_str = str(rel_path)

                    # Check if should skip - do this BEFORE is_file() to avoid Windows file lock errors
                    should_skip = any(
                        pattern in rel_path_str
                        for pattern in skip_patterns
                    )

                    if should_skip:
                        continue

                    # Now safe to check is_file() after skip patterns
                    if file_path.is_file():
                        # Add file to ZIP
                        zip_file.write(file_path, rel_path)
                        files_added += 1
                        logger.debug(f"[Export] Added to ZIP: {rel_path}")
                except OSError as e:
                    # Handle WinError 1920 and other OS errors for locked files
                    logger.warning(f"[Export] Skipping locked file: {file_path} - {e}")
                    continue

        # Get ZIP data
        zip_buffer.seek(0)
        zip_data = zip_buffer.getvalue()

        logger.info(f"[Export] Successfully exported project {project_id}: {files_added} files, {len(zip_data)} bytes")

        if files_added == 0:
            logger.warning(f"[Export] ZIP is empty - no files found in project {project_id}")

        # Return ZIP file
        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={project_id}.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Export] Error exporting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
