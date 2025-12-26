"""
FastAPI endpoints for Dynamic Orchestrator (Bolt.new-style)

This module provides REST API endpoints for:
- Executing workflows with SSE streaming
- Managing agents (update prompts/models dynamically)
- Managing workflows (list, create, update)
- Real-time event streaming to frontend
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncIterator, TypeVar
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import asyncio
import json
import uuid
from datetime import datetime

T = TypeVar('T')

# SSE Keepalive intervals (seconds)
# Use very aggressive keepalive (1s) to prevent any buffering/timeout issues
# This ensures data flows constantly to the client, preventing proxy/browser timeouts
SSE_KEEPALIVE_INITIAL_INTERVAL = 1  # First 60 seconds: send keepalive every 1s (very aggressive)
SSE_KEEPALIVE_INTERVAL = 5  # After 60 seconds: send keepalive every 5s
SSE_KEEPALIVE_AGGRESSIVE_DURATION = 60  # Duration of aggressive keepalive phase (longer)

from app.modules.orchestrator.dynamic_orchestrator import (
    DynamicOrchestrator,
    AgentType,
    AgentConfig,
    WorkflowStep,
    OrchestratorEvent
)
from app.core.database import get_db
from app.core.config import settings
from app.core.logging_config import logger
from app.models.project import Project, ProjectStatus, ProjectMode
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.usage_limits import check_token_limit, deduct_tokens, log_api_usage, get_user_limits, check_project_limit
from app.modules.auth.feature_flags import check_feature_access
from app.services.sandbox_cleanup import touch_project
from app.services.enterprise_tracker import EnterpriseTracker
from uuid import UUID as UUID_type

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

# Global orchestrator instance
orchestrator = DynamicOrchestrator()

# ==================== Cancellation Registry ====================
# Track cancelled project IDs to stop ongoing generation
_cancelled_projects: set = set()


def is_project_cancelled(project_id: str) -> bool:
    """Check if a project has been cancelled"""
    return project_id in _cancelled_projects


def cancel_project(project_id: str):
    """Mark a project as cancelled"""
    _cancelled_projects.add(project_id)
    logger.info(f"[Cancellation] Project {project_id} marked as cancelled")


def clear_cancellation(project_id: str):
    """Clear cancellation flag for a project"""
    _cancelled_projects.discard(project_id)
    logger.info(f"[Cancellation] Project {project_id} cancellation cleared")

# Optional security for SSE endpoints (auth is optional but recommended)
optional_security = HTTPBearer(auto_error=False)


# ==================== Helper Functions ====================

async def with_keepalive(async_iterator: AsyncIterator[T], project_id: str) -> AsyncIterator[T]:
    """
    Wrap an async iterator with SSE keepalive support.

    CloudFront has a 60-second origin read timeout. When Claude is processing
    (thinking/generating), no events are yielded, causing CloudFront to timeout.

    This wrapper sends keepalive events at two intervals:
    1. AGGRESSIVE PHASE (first 30s): Every 3 seconds to establish connection reliably
    2. NORMAL PHASE (after 30s): Every 10 seconds for ongoing connection

    Keepalive events are SSE comments (: keepalive) which are ignored by EventSource
    but keep the connection alive.
    """
    import time
    start_time = time.time()

    # Use aiter to make the async iterator work with anext
    ait = async_iterator.__aiter__()

    while True:
        try:
            # Determine timeout based on connection age
            elapsed = time.time() - start_time
            if elapsed < SSE_KEEPALIVE_AGGRESSIVE_DURATION:
                # Aggressive phase: use shorter interval
                timeout = SSE_KEEPALIVE_INITIAL_INTERVAL
            else:
                # Normal phase: use standard interval
                timeout = SSE_KEEPALIVE_INTERVAL

            # Try to get the next event with the dynamic timeout
            event = await asyncio.wait_for(
                ait.__anext__(),
                timeout=timeout
            )
            yield event
        except asyncio.TimeoutError:
            # No event received within timeout - send keepalive
            # SSE comment format (: comment) is ignored by browser EventSource
            # but keeps the TCP connection alive
            elapsed = time.time() - start_time
            logger.debug(f"[SSE Keepalive] Sending keepalive for project {project_id} (elapsed: {elapsed:.1f}s)")
            yield None  # Signal to send keepalive
        except StopAsyncIteration:
            # Iterator exhausted
            break


async def get_or_create_project(
    db: AsyncSession,
    project_id: str,
    user_id: str,
    title: str = None
) -> Project:
    """
    Get existing project or create a new one.

    - If project_id is a valid UUID and exists, validate ownership
    - If project_id is a timestamp format (project-XXX), create new project
    - Returns the Project record
    """
    # Check if project_id looks like a UUID
    try:
        uuid.UUID(project_id)
        is_uuid = True
    except ValueError:
        is_uuid = False

    if is_uuid:
        # Try to find existing project
        result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        existing_project = result.scalar_one_or_none()

        if existing_project:
            # Validate ownership
            if str(existing_project.user_id) != str(user_id):
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this project"
                )
            return existing_project

    # Create new project with the given project_id as title reference
    new_project = Project(
        user_id=user_id,
        title=title or f"Project {project_id}",
        description=f"Auto-created project from orchestrator",
        mode=ProjectMode.DEVELOPER,
        status=ProjectStatus.IN_PROGRESS
    )
    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    logger.info(f"Created new project {new_project.id} for user {user_id}")
    return new_project


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials],
    db: AsyncSession
) -> Optional[User]:
    """Get user from token if provided, otherwise return None"""
    # DETAILED LOGGING FOR DEBUG
    logger.info(f"[Auth Debug] get_optional_user called, credentials={credentials is not None}")

    if not credentials:
        logger.warning("[Auth Debug] No credentials provided - user will be anonymous")
        return None

    try:
        from app.core.security import decode_token
        token = credentials.credentials
        logger.info(f"[Auth Debug] Token received (first 20 chars): {token[:20] if token else 'None'}...")

        payload = decode_token(token)
        logger.info(f"[Auth Debug] Token decoded, payload keys: {list(payload.keys()) if payload else 'None'}")

        if payload.get("type") != "access":
            logger.warning(f"[Auth Debug] Invalid token type: {payload.get('type')}")
            return None

        user_id = payload.get("sub")
        logger.info(f"[Auth Debug] User ID from token: {user_id}")

        if not user_id:
            logger.warning("[Auth Debug] No user_id in token payload")
            return None

        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        logger.info(f"[Auth Debug] User lookup result: {user.email if user else 'None'}")

        if user and user.is_active:
            logger.info(f"[Auth Debug] SUCCESS - User authenticated: {user.id} ({user.email})")
            return user

        logger.warning(f"[Auth Debug] User not found or inactive")
        return None
    except Exception as e:
        logger.error(f"[Auth Debug] EXCEPTION in get_optional_user: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[Auth Debug] Traceback: {traceback.format_exc()}")
        return None


# ==================== Pydantic Models ====================

class WorkflowExecuteRequest(BaseModel):
    """Request to execute a workflow"""
    user_request: str = Field(..., description="User's request for code generation")
    project_id: str = Field(..., description="Project ID to work on")
    workflow_name: str = Field(default="bolt_standard", description="Workflow to execute")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="""Additional metadata. Supports:
        - color_theme: Custom UI colors for generated projects
          - preset: "ecommerce", "healthcare", "finance", "education", "social", "ai", "blockchain", "gaming", "portfolio", "food", "travel", "fitness"
          - OR: primary + secondary colors (e.g., {"primary": "pink", "secondary": "rose"})
        - project_name: Optional project name
        - user_id: User ID for authenticated requests
        """
    )


class AgentUpdatePromptRequest(BaseModel):
    """Request to update agent's system prompt"""
    system_prompt: str = Field(..., description="New system prompt for the agent")


class AgentUpdateModelRequest(BaseModel):
    """Request to update agent's model"""
    model: str = Field(..., description="Model name (haiku, sonnet, opus)")


class WorkflowCreateRequest(BaseModel):
    """Request to create a custom workflow"""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    steps: List[Dict[str, Any]] = Field(..., description="List of workflow steps")


class AgentConfigResponse(BaseModel):
    """Response containing agent configuration"""
    name: str
    agent_type: str
    model: str
    temperature: float
    max_tokens: int
    capabilities: List[str]
    enabled: bool
    has_custom_prompt: bool


class WorkflowResponse(BaseModel):
    """Response containing workflow details"""
    name: str
    steps: List[Dict[str, Any]]


# ==================== SSE Event Streaming ====================

async def event_generator(
    user_request: str,
    project_id: str,
    workflow_name: str,
    metadata: Optional[Dict[str, Any]],
    tracker: Optional[EnterpriseTracker] = None
):
    """
    Generator for Server-Sent Events (SSE) streaming.

    Yields events in SSE format:
    data: {"type": "status", "message": "Starting workflow..."}

    IMPORTANT: Each yield MUST be followed by an await to allow the event loop
    to flush the data to the client. Without this, events get buffered.

    If tracker is provided, important agent responses will be saved to the database.
    """
    try:
        logger.info("[SSE Generator] Starting event generator...")

        # Get file limit from metadata (FREE users get 3 files only)
        max_files_limit = metadata.get("max_files_limit") if metadata else None
        files_generated = 0

        # Send initial connection event to ensure stream is open
        initial_event = {
            "type": "connected",
            "data": {"message": "Stream connected"},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        logger.info("[SSE Generator] Sending initial connected event")
        yield f"data: {json.dumps(initial_event)}\n\n"
        # CRITICAL: Allow event loop to flush
        await asyncio.sleep(0)

        logger.info("[SSE Generator] Starting workflow execution...")
        if max_files_limit:
            logger.info(f"[SSE Generator] File limit active: {max_files_limit} files max")

        # Clear any previous cancellation for this project
        clear_cancellation(project_id)

        # Execute workflow and stream events with keepalive wrapper
        # The keepalive wrapper sends heartbeats every 30 seconds to prevent CloudFront timeout
        workflow_events = orchestrator.execute_workflow(
            user_request=user_request,
            project_id=project_id,
            workflow_name=workflow_name,
            metadata=metadata
        )

        async for event in with_keepalive(workflow_events, project_id):
            # Handle keepalive signal (None event)
            if event is None:
                # Send SSE comment as keepalive - ignored by EventSource but keeps connection alive
                yield ": keepalive\n\n"
                await asyncio.sleep(0)
                continue

            # Check for cancellation before processing each event
            if is_project_cancelled(project_id):
                logger.info(f"[SSE Generator] Project {project_id} cancelled, stopping generation")
                cancelled_event = {
                    "type": "cancelled",
                    "data": {"message": "Generation stopped by user"},
                    "step": None,
                    "agent": None,
                    "timestamp": None
                }
                yield f"data: {json.dumps(cancelled_event)}\n\n"
                await asyncio.sleep(0)
                # Clear cancellation flag after sending event
                clear_cancellation(project_id)
                return  # Exit the generator

            # Log all events for debugging
            event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
            logger.info(f"[SSE Generator] Yielding event: {event_type}")

            # Track file completions for FREE user limit
            if event_type == "file_complete" and max_files_limit:
                files_generated += 1
                logger.info(f"[SSE Generator] Files generated: {files_generated}/{max_files_limit}")

                # Check if file limit reached (FREE users get 3 files only)
                if files_generated >= max_files_limit:
                    # Send the current file event first
                    event_data = {
                        "type": event_type,
                        "data": event.data,
                        "step": event.step,
                        "agent": event.agent,
                        "timestamp": event.timestamp.isoformat() if event.timestamp else None
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    await asyncio.sleep(0)

                    # Then send upgrade required event
                    upgrade_event = {
                        "type": "upgrade_required",
                        "data": {
                            "message": f"🔒 FREE plan limit reached! You've generated {files_generated} files.",
                            "reason": "file_limit_reached",
                            "files_generated": files_generated,
                            "max_files": max_files_limit,
                            "upgrade_message": "Upgrade to Premium to generate the complete project with all files, bug fixing, and documentation.",
                            "upgrade_url": "/pricing"
                        },
                        "step": None,
                        "agent": None,
                        "timestamp": None
                    }
                    logger.info(f"[SSE Generator] File limit reached! Sending upgrade_required event")
                    yield f"data: {json.dumps(upgrade_event)}\n\n"
                    await asyncio.sleep(0)

                    # Send complete event to end the stream gracefully
                    complete_event = {
                        "type": "complete",
                        "data": {
                            "status": "partial",
                            "message": f"Generated {files_generated} preview files. Upgrade to Premium for the complete project.",
                            "files_generated": files_generated,
                            "upgrade_required": True
                        },
                        "step": None,
                        "agent": None,
                        "timestamp": None
                    }
                    yield f"data: {json.dumps(complete_event)}\n\n"
                    await asyncio.sleep(0)
                    return  # Stop generation

            # Log plan_created events and save planned files to DB
            if event_type == "plan_created":
                # Get files from plan.files (the actual file list to generate)
                plan_data = event.data.get('plan', {})
                plan_files = plan_data.get('files', [])
                logger.info(f"[SSE] Sending plan_created event with {len(plan_files)} files and {len(event.data.get('tasks', []))} workflow tasks")

                # Save planned files to database for resume capability
                try:
                    from app.models.project_file import ProjectFile, FileGenerationStatus
                    from app.core.database import AsyncSessionLocal

                    async with AsyncSessionLocal() as db_session:
                        order = 1
                        for file_item in plan_files:
                            # Extract file path - can be string or dict with 'path' key
                            if isinstance(file_item, str):
                                file_path = file_item
                            else:
                                file_path = file_item.get('path') or file_item.get('file') or file_item.get('name', '')

                            if file_path and '.' in file_path:
                                # Check if file already exists
                                existing = await db_session.execute(
                                    select(ProjectFile).where(
                                        ProjectFile.project_id == project_id,
                                        ProjectFile.path == file_path
                                    )
                                )
                                if not existing.scalar_one_or_none():
                                    # Create planned file entry
                                    planned_file = ProjectFile(
                                        project_id=project_id,
                                        path=file_path,
                                        name=file_path.split('/')[-1],
                                        generation_status=FileGenerationStatus.PLANNED,
                                        generation_order=order,
                                        is_folder=False
                                    )
                                    db_session.add(planned_file)
                                    order += 1
                        await db_session.commit()
                        logger.info(f"[SSE] Saved {order-1} planned files for project {project_id}")
                except Exception as plan_save_err:
                    logger.warning(f"[SSE] Failed to save planned files: {plan_save_err}")

            # Track important agent responses to database
            if tracker:
                try:
                    project_uuid = UUID_type(project_id)

                    # Track plan creation (planner agent response)
                    if event_type == "plan_created":
                        plan_content = json.dumps(event.data, indent=2)
                        await tracker.track_agent_response(
                            project_id=project_uuid,
                            agent_type="planner",
                            content=plan_content,
                            tokens_used=0,  # Actual tokens tracked in orchestrator
                            model_used=settings.CLAUDE_SONNET_MODEL
                        )
                        logger.debug(f"[SSE] Tracked planner response for project {project_id}")

                    # Track file completions (writer agent)
                    elif event_type == "file_complete":
                        file_path = event.data.get("file_path", "unknown")
                        await tracker.track_agent_response(
                            project_id=project_uuid,
                            agent_type="writer",
                            content=f"Generated file: {file_path}",
                            tokens_used=0
                        )
                except Exception as track_err:
                    logger.warning(f"[SSE] Failed to track agent response: {track_err}")

            # Update file status to COMPLETED when file is done
            if event_type == "file_complete":
                try:
                    from app.models.project_file import ProjectFile, FileGenerationStatus
                    from app.core.database import AsyncSessionLocal

                    file_path = event.data.get("path") or event.data.get("file_path", "")
                    if file_path:
                        async with AsyncSessionLocal() as db_session:
                            # Find and update the file status
                            result = await db_session.execute(
                                select(ProjectFile).where(
                                    ProjectFile.project_id == project_id,
                                    ProjectFile.path == file_path
                                )
                            )
                            file_record = result.scalar_one_or_none()
                            if file_record:
                                file_record.generation_status = FileGenerationStatus.COMPLETED
                                await db_session.commit()
                                logger.info(f"[SSE] Marked file as COMPLETED: {file_path}")
                except Exception as status_err:
                    logger.warning(f"[SSE] Failed to update file status: {status_err}")

            # Track important agent responses to database (continued)
            if tracker:
                try:
                    project_uuid = UUID_type(project_id)

                    # Track step completions with agent info
                    if event_type == "step_complete" and event.agent:
                        step_summary = event.data.get("message", "") or event.data.get("status", "completed")
                        await tracker.track_agent_response(
                            project_id=project_uuid,
                            agent_type=event.agent,
                            content=f"Step completed: {step_summary}",
                            tokens_used=0
                        )

                except Exception as track_err:
                    logger.warning(f"[SSE] Failed to track agent response: {track_err}")

            # Convert OrchestratorEvent to SSE format
            # Use event.type.value to ensure enum is serialized as string
            event_data = {
                "type": event_type,
                "data": event.data,
                "step": event.step,
                "agent": event.agent,
                "timestamp": event.timestamp
            }

            # SSE format: "data: {json}\n\n"
            event_message = f"data: {json.dumps(event_data)}\n\n"
            yield event_message

            # CRITICAL: Allow event loop to flush after each yield
            # This ensures the event is sent to the client immediately
            await asyncio.sleep(0.01)

            # Log after yielding for plan_created
            if event_type == "plan_created":
                logger.info(f"[SSE] plan_created event sent to client")

    except Exception as e:
        logger.error(f"Error in event streaming: {e}", exc_info=True)

        # Provide user-friendly error messages for common failures
        error_msg = str(e).lower()
        if "authentication" in error_msg or "api key" in error_msg or "401" in error_msg:
            user_error = "AI service authentication failed. Please contact support."
            error_code = "AUTH_ERROR"
        elif "rate" in error_msg or "429" in error_msg:
            user_error = "AI service is busy. Please try again in a few moments."
            error_code = "RATE_LIMITED"
        elif "timeout" in error_msg or "connection" in error_msg:
            user_error = "Connection to AI service timed out. Please try again."
            error_code = "TIMEOUT"
        elif "token" in error_msg and "limit" in error_msg:
            user_error = "You've reached your token limit. Please upgrade your plan."
            error_code = "TOKEN_LIMIT"
        else:
            user_error = "An error occurred during generation. Please try again."
            error_code = "GENERATION_ERROR"

        error_event = {
            "type": "error",
            "data": {
                "error": user_error,
                "code": error_code,
                "details": str(e) if settings.DEBUG else None
            },
            "step": None,
            "agent": None,
            "timestamp": None
        }
        yield f"data: {json.dumps(error_event)}\n\n"
        await asyncio.sleep(0)

    finally:
        # Send completion event
        logger.info("[SSE Generator] Sending completion event")
        complete_event = {
            "type": "complete",
            "data": {"status": "finished"},
            "step": None,
            "agent": None,
            "timestamp": None
        }
        yield f"data: {json.dumps(complete_event)}\n\n"
        await asyncio.sleep(0)


# ==================== Workflow Execution Endpoints ====================

@router.post("/execute")
async def execute_workflow(
    request: WorkflowExecuteRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a workflow with real-time SSE streaming.

    This endpoint returns a Server-Sent Events (SSE) stream that sends
    real-time updates as the workflow executes.

    **Authentication:** Optional but recommended. If authenticated:
    - Projects are linked to the user
    - Project ownership is validated
    - Database records are created

    **Event Types:**
    - `status`: Workflow status updates
    - `thinking_step`: AI thinking progress
    - `plan_created`: Plan generation complete
    - `file_operation`: File creation/modification started
    - `file_content`: File content chunk (streaming)
    - `file_complete`: File completed
    - `command_execute`: Command execution
    - `error`: Error occurred
    - `complete`: Workflow finished

    **Example Usage (JavaScript):**
    ```javascript
    const eventSource = new EventSource('/api/v1/orchestrator/execute', {
        method: 'POST',
        body: JSON.stringify({
            user_request: "Build a todo app",
            project_id: "my-project",
            workflow_name: "bolt_standard"
        })
    });

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data.type, data.message);
    };
    ```
    """
    try:
        logger.info(f"[Execute Workflow] Starting workflow: {request.workflow_name} for project: {request.project_id}")

        # Get user if authenticated
        current_user = await get_optional_user(credentials, db)

        # Check usage limits for authenticated users
        max_files_limit = None  # Default: unlimited
        if current_user:
            user_limits = await get_user_limits(current_user, db)
            logger.info(f"[Execute Workflow] User {current_user.email} on {user_limits.plan_name} plan")

            # Check if user has project_generation feature access (Premium required)
            feature_access = await check_feature_access(db, current_user, "project_generation")
            if not feature_access["allowed"]:
                logger.warning(f"[Execute Workflow] Feature blocked for user {current_user.email}: {feature_access['reason']}")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "feature_not_available",
                        "message": "Project generation requires Premium plan. Upgrade to create full projects with code, documents, and bug fixing.",
                        "feature": "project_generation",
                        "current_plan": feature_access["current_plan"],
                        "upgrade_to": "Premium",
                        "upgrade_url": "/billing/plans"
                    }
                )
            logger.info(f"[Execute Workflow] Feature access granted: project_generation")

            # Check if user's plan allows project generation (project limit)
            project_check = await check_project_limit(current_user, db)
            if not project_check.allowed:
                logger.warning(f"[Execute Workflow] Project limit reached for user {current_user.email}")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "project_limit_reached",
                        "message": project_check.reason or "You have reached your project limit. Please upgrade your plan.",
                        "current_usage": project_check.current_usage,
                        "limit": project_check.limit,
                        "upgrade_url": "/billing/plans"
                    }
                )
            logger.info(f"[Execute Workflow] Project limit check passed: {project_check.current_usage}/{project_check.limit} projects")

            # Get file limit for FREE users (3 files only)
            max_files_limit = user_limits.max_files_per_project
            if max_files_limit:
                logger.info(f"[Execute Workflow] File limit: {max_files_limit} files (FREE plan preview)")

            # Check token limit (estimate ~5000 tokens for a typical workflow)
            # The actual deduction happens in the orchestrator after completion
            if not user_limits.is_unlimited and user_limits.token_limit:
                from app.modules.auth.usage_limits import get_current_token_usage
                current_usage = await get_current_token_usage(current_user, db)
                if current_usage >= user_limits.token_limit:
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": "token_limit_exceeded",
                            "message": f"You've used all {user_limits.token_limit:,} tokens in your {user_limits.plan_name} plan",
                            "current_usage": current_usage,
                            "limit": user_limits.token_limit,
                            "upgrade_url": "/billing/plans"
                        }
                    )
                remaining_tokens = user_limits.token_limit - current_usage
                logger.info(f"[Execute Workflow] Token check passed: {remaining_tokens:,} tokens remaining")

        # Determine the actual project_id to use for file storage
        actual_project_id = request.project_id
        db_project = None

        if current_user:
            # User is authenticated - create/validate project in database
            logger.info(f"[Execute Workflow] Authenticated user: {current_user.email}")

            # Get or create project record
            db_project = await get_or_create_project(
                db=db,
                project_id=request.project_id,
                user_id=str(current_user.id),
                title=request.metadata.get("project_name") if request.metadata else None
            )

            # Use the database project ID for file storage (consistent UUID)
            actual_project_id = str(db_project.id)
            logger.info(f"[Execute Workflow] Using database project ID: {actual_project_id}")

            # Update project status
            db_project.status = ProjectStatus.PROCESSING
            await db.commit()

            # Track user message in database (Enterprise feature)
            tracker = EnterpriseTracker(db)
            try:
                await tracker.track_user_message(
                    project_id=UUID_type(actual_project_id),
                    content=request.user_request
                )
                logger.info(f"[Execute Workflow] Tracked user message for project {actual_project_id}")
            except Exception as e:
                logger.warning(f"[Execute Workflow] Failed to track user message: {e}")
        else:
            # Anonymous user - use the provided project_id as-is
            logger.info(f"[Execute Workflow] Anonymous user, using provided project_id: {actual_project_id}")
            tracker = None  # No tracking for anonymous users

        # Add user context to metadata
        enhanced_metadata = request.metadata or {}
        if current_user:
            enhanced_metadata["user_id"] = str(current_user.id)
            enhanced_metadata["user_email"] = current_user.email
            enhanced_metadata["db_project_id"] = actual_project_id
            # Add user_role for academic project detection
            # If user role is "student" or "faculty", project will be treated as academic
            enhanced_metadata["user_role"] = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
            logger.info(f"[Execute Workflow] User role: {enhanced_metadata['user_role']}")
            # Add subscription tier - documents only generated for PRO plan students
            enhanced_metadata["subscription_tier"] = user_limits.plan_name if user_limits else "FREE"
            # Add plan_type enum for reliable document generation check
            enhanced_metadata["plan_type"] = user_limits.plan_type.value if user_limits and user_limits.plan_type else "free"
            logger.info(f"[Execute Workflow] Subscription tier: {enhanced_metadata['subscription_tier']}, plan_type: {enhanced_metadata.get('plan_type')}")
            logger.info(f"[Execute Workflow] Added user_id={enhanced_metadata['user_id']} to metadata")
            # Add file limit for FREE users (3 files only)
            if max_files_limit:
                enhanced_metadata["max_files_limit"] = max_files_limit
                logger.info(f"[Execute Workflow] Added max_files_limit={max_files_limit} to metadata")
        else:
            logger.warning(f"[Execute Workflow] No authenticated user - sandbox will NOT have user-scoped path!")

        # Create a wrapper that yields bytes to ensure proper streaming
        async def byte_generator():
            try:
                # ==================== IMMEDIATE CONNECTION ESTABLISHMENT ====================
                # Send an immediate keepalive + connection event to ensure the SSE connection
                # is established before any processing begins. This prevents timeout issues
                # where CloudFront/browser may close the connection if no data is received
                # within the first few seconds.
                # ============================================================================

                # 1. Send SSE comment keepalive immediately (ignored by EventSource but establishes connection)
                yield b": connection-init\n\n"

                # 2. Send connection_established event immediately
                connection_event = {
                    "type": "connection_established",
                    "data": {
                        "project_id": actual_project_id,
                        "message": "SSE connection established",
                        "keepalive_interval": SSE_KEEPALIVE_INITIAL_INTERVAL
                    },
                    "step": None,
                    "agent": None,
                    "timestamp": None
                }
                yield f"data: {json.dumps(connection_event)}\n\n".encode('utf-8')
                logger.info(f"[Execute Workflow] Sent immediate connection event for {actual_project_id}")

                # Touch the project to reset its idle timer (keep alive during activity)
                touch_project(actual_project_id)
                logger.info(f"[Execute Workflow] Touched project {actual_project_id} to keep alive")

                # CRITICAL: Send project_id_updated event FIRST so frontend knows the actual DB project ID
                # This fixes the bug where frontend uses 'default-project' but files are saved to DB UUID
                if actual_project_id != request.project_id:
                    project_id_event = {
                        "type": "project_id_updated",
                        "data": {
                            "project_id": actual_project_id,
                            "original_project_id": request.project_id,
                            "message": "Project ID updated to database UUID"
                        },
                        "step": None,
                        "agent": None,
                        "timestamp": None
                    }
                    yield f"data: {json.dumps(project_id_event)}\n\n".encode('utf-8')
                    logger.info(f"[Execute Workflow] Sent project_id_updated event: {request.project_id} -> {actual_project_id}")

                async for event in event_generator(
                    user_request=request.user_request,
                    project_id=actual_project_id,
                    workflow_name=request.workflow_name,
                    metadata=enhanced_metadata,
                    tracker=tracker if current_user else None
                ):
                    # Encode to bytes for proper streaming
                    yield event.encode('utf-8')

                # ==================== PROJECT STATUS NOTE ====================
                # Project status is now set INSIDE execute_workflow() in dynamic_orchestrator.py
                # - COMPLETED: If academic documents were generated (PRO student)
                # - PARTIAL_COMPLETED: If documents were skipped (non-PRO or non-student)
                # We don't overwrite the status here to avoid undoing the COMPLETED status.
                # ================================================================

                # ==================== DOCUMENT GENERATION NOTE ====================
                # Documents are generated as part of the DOCUMENTER workflow step
                # in dynamic_orchestrator.py -> _execute_documenter() -> _execute_academic_documenter()
                # This runs for students with PRO/PREMIUM/ENTERPRISE subscription.
                # No duplicate generation needed here.
                #
                # For RESUME flow, documents are generated separately in the resume endpoint
                # since the DOCUMENTER workflow step doesn't run during resume.
                # ================================================================

            except asyncio.CancelledError:
                # Client disconnected during generation
                logger.warning(f"[Generation] Client disconnected for project {actual_project_id}")
                if db_project:
                    try:
                        # Mark as partial so user can resume
                        db_project.status = ProjectStatus.PARTIAL_COMPLETED
                        await db.commit()
                    except Exception:
                        pass
                # Try to send cancellation event
                try:
                    cancel_event = {
                        "type": "cancelled",
                        "data": {
                            "message": "Generation interrupted. You can resume later.",
                            "can_resume": True,
                            "project_id": actual_project_id
                        }
                    }
                    yield f"data: {json.dumps(cancel_event)}\n\n".encode('utf-8')
                except Exception:
                    pass
                raise

            except (ConnectionError, TimeoutError) as conn_err:
                # Network error during generation
                logger.error(f"[Generation] Connection error for project {actual_project_id}: {conn_err}")
                if db_project:
                    try:
                        db_project.status = ProjectStatus.PARTIAL_COMPLETED
                        await db.commit()
                    except Exception:
                        pass
                try:
                    error_event = {
                        "type": "error",
                        "data": {
                            "message": "Connection error. You can resume when connection is restored.",
                            "error": str(conn_err),
                            "can_resume": True
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n".encode('utf-8')
                except Exception:
                    pass
                raise

            except Exception as e:
                logger.error(f"Error in workflow execution: {e}", exc_info=True)
                # Send error event to frontend
                try:
                    error_event = {
                        "type": "error",
                        "data": {
                            "message": f"Generation failed: {str(e)[:100]}",
                            "error": str(e),
                            "can_resume": True
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n".encode('utf-8')
                except Exception:
                    pass

                # Update project status on failure
                if db_project:
                    try:
                        db_project.status = ProjectStatus.FAILED
                        await db.commit()
                    except Exception:
                        pass
                raise

        return StreamingResponse(
            byte_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*",
            }
        )
    except HTTPException:
        raise
    except asyncio.CancelledError:
        logger.warning(f"[Generation] Request cancelled for project {request.project_id}")
        raise HTTPException(status_code=499, detail="Client closed request")
    except Exception as e:
        logger.error(f"Failed to start workflow execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Resume Generation Endpoint ====================

class ResumeRequest(BaseModel):
    """Request to resume interrupted generation"""
    project_id: str
    continue_message: Optional[str] = "Continue generating the remaining files"


@router.post("/resume")
async def resume_generation(
    request: ResumeRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Resume an interrupted project generation.

    Use this when:
    - Internet connection dropped during generation
    - Browser was closed mid-generation
    - Generation failed/stopped unexpectedly

    The endpoint will:
    1. Find the project and check its status
    2. Get list of already generated files
    3. Continue generating remaining files
    """
    try:
        # Get authenticated user
        current_user = await get_optional_user(credentials, db)
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required to resume generation")

        # Get project from database
        project_result = await db.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.user_id == current_user.id
            )
        )
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # ============================================================
        # EDGE CASE 1: Check if project has a saved plan
        # Without plan_json, we can't know what files to generate
        # ============================================================
        if not project.plan_json:
            logger.warning(f"[Resume] Project {request.project_id} has no saved plan")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "no_plan",
                    "message": "This project has no saved plan. Please start a new generation.",
                    "can_regenerate": True
                }
            )

        # ============================================================
        # EDGE CASE 2: Check if project is already completed
        # ============================================================
        if project.status == ProjectStatus.COMPLETED:
            logger.info(f"[Resume] Project {request.project_id} is already completed")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "already_completed",
                    "message": "This project is already completed. No files need to be generated.",
                    "project_status": "completed"
                }
            )

        # ============================================================
        # EDGE CASE 3: Check if project is currently being generated
        # Block resume if generation is actively in progress
        # ============================================================
        if project.status == ProjectStatus.PROCESSING:
            # Check if the project is actively being generated
            # A project is considered "stale" if it's been PROCESSING for more than 10 minutes
            # (likely a crashed/abandoned generation)
            from datetime import timedelta
            stale_threshold = timedelta(minutes=10)
            is_stale = False

            if project.updated_at:
                time_since_update = datetime.utcnow() - project.updated_at
                is_stale = time_since_update > stale_threshold
                logger.info(f"[Resume] Project {request.project_id} PROCESSING status age: {time_since_update}, stale={is_stale}")

            if not is_stale:
                # Project is actively being generated - block resume
                logger.warning(f"[Resume] Project {request.project_id} is currently being generated - blocking resume")
                raise HTTPException(
                    status_code=409,  # Conflict
                    detail={
                        "error": "generation_in_progress",
                        "message": "Project generation is currently in progress. Please wait for it to complete or cancel the current generation first.",
                        "project_status": "processing",
                        "can_resume": False
                    }
                )
            else:
                # Stale PROCESSING status - likely a crashed generation, allow resume
                logger.info(f"[Resume] Project {request.project_id} has stale PROCESSING status, allowing resume")

        # Get existing files for this project
        # CRITICAL: Only consider files WITH CONTENT as "existing" (not empty placeholder entries)
        # This fixes the bug where resume skips files that were planned but never generated
        from app.models.project_file import ProjectFile, FileGenerationStatus
        files_result = await db.execute(
            select(ProjectFile).where(ProjectFile.project_id == request.project_id)
        )
        all_files = files_result.scalars().all()

        # Only count files that actually have content (content_inline or s3_key)
        existing_files = [f for f in all_files if f.content_inline or f.s3_key]
        existing_file_paths = [f.path for f in existing_files if f.path]

        # Count files that need to be generated (no content yet)
        # Include files with PLANNED, GENERATING (interrupted), or FAILED status
        pending_files = [f for f in all_files if not f.content_inline and not f.s3_key and f.path]
        pending_file_paths = [f.path for f in pending_files]

        # Also check for failed files that need retry
        failed_files = [f for f in all_files if f.generation_status == FileGenerationStatus.FAILED]
        if failed_files:
            for ff in failed_files:
                if ff.path not in pending_file_paths:
                    pending_file_paths.append(ff.path)
            logger.info(f"[Resume] Including {len(failed_files)} failed files for retry")

        # ============================================================
        # EDGE CASE 4: No pending files but project not marked complete
        # This can happen if generation completed but status wasn't updated
        # ============================================================
        if not pending_file_paths and existing_file_paths:
            logger.info(f"[Resume] All files generated, marking project as complete")
            project.status = ProjectStatus.PARTIAL_COMPLETED
            await db.commit()
            raise HTTPException(
                status_code=200,  # Not an error - just informing
                detail={
                    "error": "no_pending_files",
                    "message": f"All {len(existing_file_paths)} files have been generated.",
                    "completed_files": len(existing_file_paths),
                    "project_status": "partial_completed"
                }
            )

        # ============================================================
        # EDGE CASE 5: No files at all (plan exists but no files in DB)
        # Need to extract files from plan_json
        # ============================================================
        if not all_files and project.plan_json:
            plan_files = project.plan_json.get('files', [])
            if plan_files:
                pending_file_paths = [f.get('path') for f in plan_files if f.get('path')]
                logger.info(f"[Resume] No DB files found, using {len(pending_file_paths)} files from plan_json")

        logger.info(f"[Resume] Project {request.project_id}: {len(existing_file_paths)} completed files, {len(pending_file_paths)} pending files")

        # Build resume context
        resume_context = f"""Continue generating this project.

Already generated files (DO NOT regenerate these):
{chr(10).join(['- ' + p for p in existing_file_paths]) if existing_file_paths else '(none yet)'}

Files that STILL NEED to be generated:
{chr(10).join(['- ' + p for p in pending_file_paths]) if pending_file_paths else '(all files completed)'}

Original project: {project.title}
Description: {project.description or 'N/A'}

{request.continue_message}

Generate the remaining {len(pending_file_paths)} files needed to complete this project. Focus on creating the files listed above that still need to be generated."""

        # Update project status
        project.status = ProjectStatus.PROCESSING
        await db.commit()

        # Get user limits for file limit check
        user_limits = await get_user_limits(current_user, db)
        max_files_limit = user_limits.max_files_per_project

        # Build metadata - include plan_json so writer knows file descriptions
        metadata = {
            "user_id": str(current_user.id),
            "user_email": current_user.email,
            "db_project_id": request.project_id,
            "is_resume": True,
            "existing_files": existing_file_paths,
            "existing_file_count": len(existing_file_paths),
            "pending_files": pending_file_paths,
            "pending_file_count": len(pending_file_paths),
            # CRITICAL: Pass the saved plan so writer has file descriptions
            "saved_plan": project.plan_json if project.plan_json else None,
            "project_name": project.title,
            "project_description": project.description
        }

        # Add file limit if applicable (for FREE users)
        if max_files_limit:
            # Subtract already generated files from limit
            remaining_files = max(0, max_files_limit - len(existing_file_paths))
            if remaining_files <= 0:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "file_limit_reached",
                        "message": f"FREE plan limit reached. You've already generated {len(existing_file_paths)} files.",
                        "upgrade_url": "/pricing"
                    }
                )
            metadata["max_files_limit"] = remaining_files
            logger.info(f"[Resume] File limit: {remaining_files} more files allowed")

        # Create SSE generator
        async def byte_generator():
            try:
                # ==================== IMMEDIATE CONNECTION ESTABLISHMENT ====================
                # Send an immediate keepalive + connection event to prevent timeout issues
                # ============================================================================
                yield b": connection-init\n\n"

                connection_event = {
                    "type": "connection_established",
                    "data": {
                        "project_id": request.project_id,
                        "message": "SSE connection established for resume",
                        "keepalive_interval": SSE_KEEPALIVE_INITIAL_INTERVAL
                    },
                    "step": None,
                    "agent": None,
                    "timestamp": None
                }
                yield f"data: {json.dumps(connection_event)}\n\n".encode('utf-8')
                logger.info(f"[Resume] Sent immediate connection event for {request.project_id}")

                touch_project(request.project_id)

                # ============================================================
                # STEP 1: Send RESUME_INFO event with completed + pending files
                # This allows the frontend to show progress immediately
                # ============================================================
                resume_info_event = {
                    "type": "resume_info",
                    "data": {
                        "project_id": request.project_id,
                        "project_name": project.title,
                        "completed_count": len(existing_file_paths),
                        "pending_count": len(pending_file_paths),
                        "completed_files": existing_file_paths,
                        "pending_files": pending_file_paths,
                        "message": f"Resuming: {len(existing_file_paths)} completed, {len(pending_file_paths)} remaining"
                    }
                }
                yield f"data: {json.dumps(resume_info_event)}\n\n".encode('utf-8')
                logger.info(f"[Resume] Sent resume_info event: {len(existing_file_paths)} completed, {len(pending_file_paths)} pending")

                # ============================================================
                # STEP 2: Send completed files to frontend so user sees progress
                # Each completed file is sent as a FILE_OPERATION event
                # ============================================================
                from app.services.storage_service import storage_service

                for idx, completed_file in enumerate(existing_files, 1):
                    try:
                        # Get file content from S3 or inline
                        file_content = ""
                        if completed_file.s3_key:
                            content_bytes = await storage_service.download_file(completed_file.s3_key)
                            if content_bytes:
                                file_content = content_bytes.decode('utf-8', errors='replace')
                        elif completed_file.content_inline:
                            file_content = completed_file.content_inline

                        # Send file to frontend
                        completed_event = {
                            "type": "file_operation",
                            "data": {
                                "operation": "restore",
                                "path": completed_file.path,
                                "name": completed_file.name,
                                "operation_status": "complete",
                                "file_content": file_content,
                                "file_number": idx,
                                "total_files": len(existing_files) + len(pending_file_paths),
                                "generation_status": "completed",
                                "is_resumed": True
                            }
                        }
                        yield f"data: {json.dumps(completed_event)}\n\n".encode('utf-8')

                    except Exception as fe:
                        logger.warning(f"[Resume] Failed to load completed file {completed_file.path}: {fe}")

                logger.info(f"[Resume] Sent {len(existing_files)} completed files to frontend")

                # ============================================================
                # STEP 3: Continue generating remaining files
                # ============================================================
                if pending_file_paths:
                    status_event = {
                        "type": "status",
                        "data": {"message": f"Continuing generation... {len(pending_file_paths)} files remaining"}
                    }
                    yield f"data: {json.dumps(status_event)}\n\n".encode('utf-8')

                    async for event in event_generator(
                        user_request=resume_context,
                        project_id=request.project_id,
                        workflow_name="bolt_standard",
                        metadata=metadata,
                        tracker=None
                    ):
                        yield event.encode('utf-8')
                else:
                    # All files already completed
                    complete_event = {
                        "type": "complete",
                        "data": {
                            "message": "All files already generated!",
                            "total_files": len(existing_file_paths)
                        }
                    }
                    yield f"data: {json.dumps(complete_event)}\n\n".encode('utf-8')

                # Update project status on code completion
                # Mark as PARTIAL_COMPLETED (code done, documents pending)
                project.status = ProjectStatus.PARTIAL_COMPLETED
                await db.commit()
                logger.info(f"Project {project.id} marked as PARTIAL_COMPLETED after resume")

                # ==================== AUTO DOCUMENT GENERATION (RESUME) ====================
                # Generate documents for eligible students with PRO subscription
                user_role = current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role)
                plan_type = user_limits.plan_type.value if user_limits and user_limits.plan_type else "free"
                subscription_tier = user_limits.plan_name if user_limits else "FREE"

                is_student = user_role.lower() in ['student', 'faculty']
                is_premium_plan = plan_type.lower() in ['pro', 'enterprise'] or subscription_tier.upper() in ['PRO', 'PREMIUM', 'ENTERPRISE', 'UNLIMITED']
                is_eligible_for_docs = is_student and is_premium_plan

                logger.info(f"[Resume AutoDocs] Eligibility: user_role='{user_role}', plan_type='{plan_type}', is_eligible={is_eligible_for_docs}")

                if is_eligible_for_docs:
                    try:
                        from app.modules.agents.chunked_document_agent import chunked_document_agent, DocumentType
                        from app.models.document import DocumentType as DBDocumentType

                        # Send document generation starting event
                        doc_start_event = {
                            "type": "documents_starting",
                            "data": {
                                "message": "Code generation complete. Starting document generation...",
                                "documents": ["SRS", "Project Report", "PPT", "Viva Q&A"]
                            },
                            "step": None,
                            "agent": "document_generator",
                            "timestamp": None
                        }
                        yield f"data: {json.dumps(doc_start_event)}\n\n".encode('utf-8')
                        await asyncio.sleep(0.01)

                        # Documents to generate
                        documents_to_generate = [
                            ("srs", "SRS Document", DocumentType.SRS, DBDocumentType.SRS),
                            ("report", "Project Report", DocumentType.PROJECT_REPORT, DBDocumentType.REPORT),
                            ("ppt", "Presentation", DocumentType.PPT, DBDocumentType.PPT),
                            ("viva", "Viva Q&A", DocumentType.VIVA_QA, DBDocumentType.VIVA_QA),
                        ]

                        for doc_key, doc_name, doc_type, db_doc_type in documents_to_generate:
                            try:
                                doc_event = {
                                    "type": "document_generating",
                                    "data": {
                                        "document": doc_name,
                                        "key": doc_key,
                                        "message": f"Generating {doc_name}..."
                                    },
                                    "step": None,
                                    "agent": "document_generator",
                                    "timestamp": None
                                }
                                yield f"data: {json.dumps(doc_event)}\n\n".encode('utf-8')
                                await asyncio.sleep(0.01)

                                async for event in chunked_document_agent.generate_document_streaming(
                                    project_id=request.project_id,
                                    doc_type=doc_type,
                                    db=db
                                ):
                                    doc_progress_event = {
                                        "type": "document_progress",
                                        "data": {
                                            "document": doc_name,
                                            "key": doc_key,
                                            **event
                                        },
                                        "step": None,
                                        "agent": "document_generator",
                                        "timestamp": None
                                    }
                                    yield f"data: {json.dumps(doc_progress_event)}\n\n".encode('utf-8')
                                    await asyncio.sleep(0.01)

                                doc_complete_event = {
                                    "type": "document_complete",
                                    "data": {
                                        "document": doc_name,
                                        "key": doc_key,
                                        "message": f"{doc_name} generated successfully"
                                    },
                                    "step": None,
                                    "agent": "document_generator",
                                    "timestamp": None
                                }
                                yield f"data: {json.dumps(doc_complete_event)}\n\n".encode('utf-8')
                                await asyncio.sleep(0.01)

                                logger.info(f"[Resume AutoDocs] Generated {doc_name} for project {request.project_id}")

                            except Exception as doc_err:
                                logger.error(f"[Resume AutoDocs] Error generating {doc_name}: {doc_err}")
                                doc_error_event = {
                                    "type": "document_error",
                                    "data": {
                                        "document": doc_name,
                                        "key": doc_key,
                                        "error": str(doc_err)
                                    },
                                    "step": None,
                                    "agent": "document_generator",
                                    "timestamp": None
                                }
                                yield f"data: {json.dumps(doc_error_event)}\n\n".encode('utf-8')
                                await asyncio.sleep(0.01)

                        # Mark project as COMPLETED after all documents generated
                        project.status = ProjectStatus.COMPLETED
                        project.completed_at = datetime.utcnow()
                        await db.commit()
                        logger.info(f"[Resume AutoDocs] Project {project.id} marked as COMPLETED")

                        # Send all documents complete event
                        all_docs_event = {
                            "type": "all_documents_complete",
                            "data": {
                                "message": "All documents generated successfully!",
                                "project_status": "COMPLETED"
                            },
                            "step": None,
                            "agent": "document_generator",
                            "timestamp": None
                        }
                        yield f"data: {json.dumps(all_docs_event)}\n\n".encode('utf-8')
                        await asyncio.sleep(0.01)

                    except Exception as doc_gen_err:
                        logger.error(f"[Resume AutoDocs] Document generation failed: {doc_gen_err}")
                        doc_fail_event = {
                            "type": "documents_failed",
                            "data": {
                                "error": str(doc_gen_err),
                                "message": "Document generation failed. You can retry from the project page."
                            },
                            "step": None,
                            "agent": "document_generator",
                            "timestamp": None
                        }
                        yield f"data: {json.dumps(doc_fail_event)}\n\n".encode('utf-8')
                        await asyncio.sleep(0.01)
                else:
                    # User not eligible for documents - send notification
                    if not is_student:
                        reason = f"Document generation is only available for students. Your role: {user_role}"
                    elif not is_premium_plan:
                        reason = f"Document generation requires PRO or Premium subscription. Your plan: {subscription_tier}"
                    else:
                        reason = "Document generation requires student role with PRO subscription."

                    logger.info(f"[Resume AutoDocs] Skipping documents: {reason}")
                    doc_upgrade_event = {
                        "type": "documents_require_upgrade",
                        "data": {
                            "message": reason,
                            "current_plan": subscription_tier,
                            "user_role": user_role,
                            "upgrade_url": "/billing/plans"
                        },
                        "step": None,
                        "agent": "document_generator",
                        "timestamp": None
                    }
                    yield f"data: {json.dumps(doc_upgrade_event)}\n\n".encode('utf-8')
                    await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                # Client disconnected - mark project for potential resume
                logger.warning(f"[Resume] Client disconnected for project {request.project_id}")
                try:
                    project.status = ProjectStatus.PARTIAL_COMPLETED  # Allow resume
                    await db.commit()
                except Exception:
                    pass
                # Send cancellation event before closing
                try:
                    cancel_event = {
                        "type": "cancelled",
                        "data": {
                            "message": "Connection interrupted. You can resume later.",
                            "can_resume": True
                        }
                    }
                    yield f"data: {json.dumps(cancel_event)}\n\n".encode('utf-8')
                except Exception:
                    pass
                raise

            except (ConnectionError, TimeoutError) as conn_err:
                # Network error - mark for resume
                logger.error(f"[Resume] Connection error for project {request.project_id}: {conn_err}")
                try:
                    project.status = ProjectStatus.PARTIAL_COMPLETED  # Allow resume
                    await db.commit()
                except Exception:
                    pass
                # Send error event
                try:
                    error_event = {
                        "type": "error",
                        "data": {
                            "message": "Connection error. You can resume when connection is restored.",
                            "error": str(conn_err),
                            "can_resume": True
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n".encode('utf-8')
                except Exception:
                    pass
                raise

            except Exception as e:
                logger.error(f"Error in resume generation: {e}", exc_info=True)
                # Send error event to frontend before failing
                try:
                    error_event = {
                        "type": "error",
                        "data": {
                            "message": f"Generation failed: {str(e)[:100]}",
                            "error": str(e),
                            "can_resume": True
                        }
                    }
                    yield f"data: {json.dumps(error_event)}\n\n".encode('utf-8')
                except Exception:
                    pass

                # Mark project as failed but allow resume
                try:
                    project.status = ProjectStatus.FAILED
                    await db.commit()
                except Exception as db_err:
                    logger.error(f"[Resume] Failed to update project status: {db_err}")
                raise

        return StreamingResponse(
            byte_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    except HTTPException:
        raise
    except asyncio.CancelledError:
        logger.warning(f"[Resume] Request cancelled for project {request.project_id}")
        raise HTTPException(status_code=499, detail="Client closed request")
    except Exception as e:
        logger.error(f"Failed to resume generation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/status")
async def get_project_generation_status(
    project_id: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project generation status - useful for checking if resume is needed.

    Returns:
    - status: current project status
    - files_generated: number of files created
    - can_resume: whether resume is possible
    - last_activity: when project was last modified
    """
    current_user = await get_optional_user(credentials, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get file count
    from app.models.project_file import ProjectFile
    files_result = await db.execute(
        select(func.count(ProjectFile.id)).where(ProjectFile.project_id == project_id)
    )
    files_count = files_result.scalar() or 0

    # Determine if resume is possible
    can_resume = project.status in [ProjectStatus.PROCESSING, ProjectStatus.FAILED, ProjectStatus.IN_PROGRESS]

    return {
        "project_id": project_id,
        "title": project.title,
        "status": project.status.value,
        "files_generated": files_count,
        "can_resume": can_resume,
        "last_activity": project.last_activity.isoformat() if project.last_activity else None,
        "progress": project.progress or 0,
        "message": (
            "Generation was interrupted. Click 'Resume' to continue."
            if can_resume else
            "Project fully complete with documents." if project.status == ProjectStatus.COMPLETED else
            "Code generation complete. Generate documents to finish." if project.status == ProjectStatus.PARTIAL_COMPLETED else
            "Project is ready for generation."
        )
    }


@router.get("/project/{project_id}/progress")
async def get_generation_progress(
    project_id: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed generation progress with file statuses.

    Use this for polling when SSE connection is lost.
    Returns list of all planned files with their generation status.

    Status values:
    - planned: In plan, not yet generated
    - generating: Currently being generated
    - completed: Successfully generated (has content)
    - failed: Generation failed
    - skipped: Skipped
    """
    current_user = await get_optional_user(credentials, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all files with their status
    from app.models.project_file import ProjectFile, FileGenerationStatus
    files_result = await db.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.generation_order.asc().nullslast(), ProjectFile.created_at.asc())
    )
    files = files_result.scalars().all()

    # Count by status
    # IMPORTANT: For backward compatibility, determine status based on ACTUAL CONTENT
    # not just generation_status field (which defaults to "completed")
    status_counts = {
        "planned": 0,
        "generating": 0,
        "completed": 0,
        "failed": 0,
        "skipped": 0
    }

    file_list = []
    for f in files:
        has_content = bool(f.content_inline or f.s3_key)

        # Determine actual status based on content presence
        # This fixes backward compatibility for projects created before status tracking
        if has_content:
            # File has content = completed
            actual_status = "completed"
        elif f.generation_status and f.generation_status.value == "generating":
            # File is currently being generated
            actual_status = "generating"
        elif f.generation_status and f.generation_status.value == "failed":
            # File generation failed
            actual_status = "failed"
        elif f.generation_status and f.generation_status.value == "skipped":
            # File was skipped
            actual_status = "skipped"
        else:
            # No content and not generating/failed/skipped = pending (needs generation)
            actual_status = "planned"

        status_counts[actual_status] = status_counts.get(actual_status, 0) + 1

        file_list.append({
            "path": f.path,
            "name": f.name,
            "status": actual_status,
            "order": f.generation_order,
            "has_content": has_content,
            "updated_at": f.updated_at.isoformat() if f.updated_at else None
        })

    total_files = len(files)
    completed_files = status_counts["completed"]
    progress_percent = int((completed_files / total_files * 100)) if total_files > 0 else 0

    # Determine overall status
    is_complete = status_counts["planned"] == 0 and status_counts["generating"] == 0
    is_in_progress = status_counts["generating"] > 0 or (status_counts["planned"] > 0 and completed_files > 0)

    return {
        "project_id": project_id,
        "title": project.title,
        "project_status": project.status.value,
        "generation": {
            "total_files": total_files,
            "completed": completed_files,
            "planned": status_counts["planned"],
            "generating": status_counts["generating"],
            "failed": status_counts["failed"],
            "progress_percent": progress_percent,
            "is_complete": is_complete,
            "is_in_progress": is_in_progress
        },
        "files": file_list,
        "can_resume": status_counts["planned"] > 0 or status_counts["failed"] > 0,
        "last_update": project.updated_at.isoformat() if project.updated_at else None
    }


# ==================== Workflow Management Endpoints ====================

@router.get("/workflows", response_model=List[WorkflowResponse])
async def list_workflows():
    """
    List all available workflows.

    Returns workflows with their steps and configurations.

    **Default Workflows:**
    - `bolt_standard`: plan → write → run → fix → docs
    - `quick_iteration`: plan → write → test
    - `debug`: analyze → fix → verify
    """
    try:
        workflow_names = orchestrator.workflow_engine.list_workflows()

        response = []
        for name in workflow_names:
            try:
                steps = orchestrator.workflow_engine.get_workflow(name)
                workflow_data = {
                    "name": name,
                    "steps": [
                        {
                            "agent_type": step.agent_type.value,
                            "name": step.name,
                            "timeout": step.timeout,
                            "retry_count": step.retry_count,
                            "stream_output": step.stream_output
                        }
                        for step in steps
                    ]
                }
                response.append(workflow_data)
            except Exception as e:
                logger.warning(f"Failed to get workflow '{name}': {e}")
                continue

        return response
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/workflows", response_model=Dict[str, str])
async def create_workflow(request: WorkflowCreateRequest):
    """
    Create a custom workflow.

    **Request Example:**
    ```json
    {
        "name": "my_custom_workflow",
        "description": "Custom workflow for specific use case",
        "steps": [
            {
                "agent_type": "planner",
                "name": "Create Plan",
                "timeout": 120,
                "retry_count": 2
            },
            {
                "agent_type": "writer",
                "name": "Generate Code",
                "stream_output": true
            }
        ]
    }
    ```
    """
    try:
        # Convert steps to WorkflowStep objects
        steps = []
        for step_data in request.steps:
            step = WorkflowStep(
                agent_type=AgentType(step_data["agent_type"]),
                name=step_data["name"],
                timeout=step_data.get("timeout", 300),
                retry_count=step_data.get("retry_count", 2),
                stream_output=step_data.get("stream_output", False)
            )
            steps.append(step)

        # Register workflow
        orchestrator.workflow_engine.register_workflow(request.name, steps)

        return {
            "message": f"Workflow '{request.name}' created successfully",
            "workflow_name": request.name
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_name}", response_model=WorkflowResponse)
async def get_workflow(workflow_name: str):
    """
    Get details of a specific workflow.
    """
    try:
        steps = orchestrator.workflow_engine.get_workflow(workflow_name)

        return {
            "name": workflow_name,
            "steps": [
                {
                    "agent_type": step.agent_type.value,
                    "name": step.name,
                    "timeout": step.timeout,
                    "retry_count": step.retry_count,
                    "stream_output": step.stream_output
                }
                for step in steps
            ]
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")
    except Exception as e:
        logger.error(f"Failed to get workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Agent Configuration Endpoints ====================

@router.get("/agents", response_model=List[AgentConfigResponse])
async def list_agents():
    """
    List all registered agents with their configurations.

    Returns agent details including model, temperature, capabilities, etc.
    """
    try:
        agents = orchestrator.agent_registry.list_agents()

        response = []
        for agent_type, config in agents.items():
            agent_data = AgentConfigResponse(
                name=config.name,
                agent_type=config.agent_type.value,
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                capabilities=config.capabilities or [],
                enabled=config.enabled,
                has_custom_prompt=config.system_prompt is not None
            )
            response.append(agent_data)

        return response
    except Exception as e:
        logger.error(f"Failed to list agents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_type}", response_model=AgentConfigResponse)
async def get_agent(agent_type: str):
    """
    Get configuration for a specific agent.
    """
    try:
        config = orchestrator.agent_registry.get_agent(AgentType(agent_type))

        return AgentConfigResponse(
            name=config.name,
            agent_type=config.agent_type.value,
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            capabilities=config.capabilities or [],
            enabled=config.enabled,
            has_custom_prompt=config.system_prompt is not None
        )
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to get agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/prompt", response_model=Dict[str, str])
async def update_agent_prompt(agent_type: str, request: AgentUpdatePromptRequest):
    """
    Dynamically update an agent's system prompt.

    This allows you to customize agent behavior without restarting the server.

    **Example:**
    ```json
    {
        "system_prompt": "You are an expert Python developer specializing in FastAPI..."
    }
    ```
    """
    try:
        orchestrator.agent_registry.update_agent_prompt(
            AgentType(agent_type),
            request.system_prompt
        )

        return {
            "message": f"Agent '{agent_type}' prompt updated successfully",
            "agent_type": agent_type
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to update agent prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/model", response_model=Dict[str, str])
async def update_agent_model(agent_type: str, request: AgentUpdateModelRequest):
    """
    Dynamically update an agent's model.

    **Valid models:**
    - `haiku`: Fast, cost-effective (Claude 3 Haiku)
    - `sonnet`: Balanced performance (Claude 3.5 Sonnet) - Default
    - `opus`: Most powerful (Claude 3 Opus)

    **Example:**
    ```json
    {
        "model": "opus"
    }
    ```
    """
    try:
        if request.model not in ["haiku", "sonnet", "opus"]:
            raise ValueError(f"Invalid model: {request.model}. Must be haiku, sonnet, or opus")

        orchestrator.agent_registry.update_agent_model(
            AgentType(agent_type),
            request.model
        )

        return {
            "message": f"Agent '{agent_type}' model updated to '{request.model}'",
            "agent_type": agent_type,
            "model": request.model
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to update agent model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/enable", response_model=Dict[str, str])
async def enable_agent(agent_type: str):
    """Enable a disabled agent."""
    try:
        config = orchestrator.agent_registry.get_agent(AgentType(agent_type))
        config.enabled = True

        return {
            "message": f"Agent '{agent_type}' enabled",
            "agent_type": agent_type
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to enable agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agents/{agent_type}/disable", response_model=Dict[str, str])
async def disable_agent(agent_type: str):
    """Disable an agent (it will be skipped in workflows)."""
    try:
        config = orchestrator.agent_registry.get_agent(AgentType(agent_type))
        config.enabled = False

        return {
            "message": f"Agent '{agent_type}' disabled",
            "agent_type": agent_type
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_type}' not found")
    except Exception as e:
        logger.error(f"Failed to disable agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Regeneration (Bolt.new Style) ====================

class RegenerateRequest(BaseModel):
    """Request to regenerate a project from saved plan"""
    project_id: str = Field(..., description="Project ID to regenerate")


@router.post("/regenerate")
async def regenerate_project(
    request: RegenerateRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Regenerate a project by replaying Claude messages (Bolt.new style).

    This endpoint:
    1. Loads saved plan.json and history from database
    2. Creates new empty workspace
    3. Replays the plan to Claude's writer agent
    4. Claude generates ALL files fresh (not restored from storage)

    This is exactly how Bolt.new handles "opening old projects".
    """
    try:
        # Get user if authenticated
        current_user = await get_optional_user(credentials, db)

        if not current_user:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for regeneration"
            )

        # Get project from database
        result = await db.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        if not project.plan_json:
            raise HTTPException(
                status_code=400,
                detail="No saved plan found - cannot regenerate"
            )

        logger.info(f"[Regenerate] Starting regeneration for project: {request.project_id}")

        # Touch project to keep it alive
        touch_project(request.project_id)

        # Create regeneration event generator
        async def regenerate_generator():
            try:
                # Send start event
                yield f"data: {json.dumps({'type': 'regenerate_start', 'data': {'project_id': request.project_id, 'message': 'Loading saved plan...'}})}\n\n"
                await asyncio.sleep(0.01)

                # Extract plan data
                plan_data = project.plan_json
                files_to_generate = []

                # Get files from plan
                if isinstance(plan_data, dict):
                    files_to_generate = plan_data.get("files", [])
                    if not files_to_generate:
                        # Try alternate structure
                        tasks = plan_data.get("tasks", [])
                        for task in tasks:
                            if task.get("files"):
                                files_to_generate.extend(task["files"])

                yield f"data: {json.dumps({'type': 'plan_loaded', 'data': {'file_count': len(files_to_generate), 'message': f'Found {len(files_to_generate)} files to regenerate'}})}\n\n"
                await asyncio.sleep(0.01)

                # Execute writer workflow with saved plan (skip planning)
                async for event in orchestrator.execute_workflow(
                    user_request=project.description or project.title or "Regenerate project",
                    project_id=request.project_id,
                    workflow_name="writer_only",  # Skip planning, just write
                    metadata={
                        "mode": "regenerate",
                        "saved_plan": plan_data,
                        "skip_planning": True,
                        "user_id": str(current_user.id)
                    }
                ):
                    event_type = event.type.value if hasattr(event.type, 'value') else str(event.type)
                    event_data = {
                        "type": event_type,
                        "data": event.data,
                        "step": event.step,
                        "agent": event.agent,
                        "timestamp": event.timestamp
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    await asyncio.sleep(0.01)

                yield f"data: {json.dumps({'type': 'regenerate_complete', 'data': {'project_id': request.project_id, 'message': 'Project regenerated successfully'}})}\n\n"

            except Exception as e:
                logger.error(f"[Regenerate] Error: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}})}\n\n"

        return StreamingResponse(
            regenerate_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Regenerate] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Cancellation Endpoint ====================

class CancelRequest(BaseModel):
    """Request to cancel an ongoing workflow"""
    project_id: str = Field(..., description="Project ID to cancel")


@router.post("/cancel")
async def cancel_workflow(
    request: CancelRequest,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an ongoing workflow for a project.

    This immediately marks the project as cancelled, which will:
    - Stop any ongoing file generation
    - Skip remaining workflow steps
    - Return a cancellation event to the frontend

    The cancellation is checked:
    - Before each workflow step
    - During file content streaming
    - Before each agent execution
    """
    try:
        logger.info(f"[Cancel] Received cancel request for project: {request.project_id}")

        # Mark project as cancelled
        cancel_project(request.project_id)

        return {
            "success": True,
            "message": f"Cancellation requested for project {request.project_id}",
            "project_id": request.project_id
        }

    except Exception as e:
        logger.error(f"[Cancel] Failed to cancel project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@router.get("/health")
async def health_check():
    """
    Health check endpoint for the orchestrator.

    Returns orchestrator status and configuration.
    """
    try:
        agents = orchestrator.agent_registry.list_agents()
        workflows = orchestrator.workflow_engine.list_workflows()

        return {
            "status": "healthy",
            "agents_count": len(agents),
            "workflows_count": len(workflows),
            "default_workflow": "bolt_standard"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }
