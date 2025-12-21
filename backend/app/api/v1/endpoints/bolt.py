"""
Bolt.new-style AI Code Editor Endpoints
Streaming chat, file operations, and code execution
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import json
import asyncio
from datetime import datetime

from app.core.database import get_db
from app.core.logging_config import logger
from app.utils.claude_client import claude_client
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from sqlalchemy import select
import hashlib
import os
from uuid import UUID
from app.schemas.bolt import (
    BoltChatRequest,
    BoltChatResponse,
    ApplyPatchRequest,
    ApplyPatchResponse,
    CreateFileRequest,
    UpdateFileRequest,
    DeleteFileRequest,
    FileOperationResponse,
    ExecuteCodeRequest,
    ExecuteCodeResponse,
    StreamEvent,
    ProjectFileSchema,
    GenerateProjectRequest,
    GenerateProjectResponse,
    GenerateProjectStreamEvent,
    BulkSyncFilesRequest,
    BulkSyncFilesResponse,
    GetProjectFilesResponse
)
from app.modules.bolt.prompts import BOLT_SYSTEM_PROMPT
from app.modules.bolt.context_builder import context_builder
from app.services.unified_storage import UnifiedStorageService
from app.services.enterprise_tracker import EnterpriseTracker
from app.services.storage_service import storage_service


router = APIRouter(prefix="/bolt", tags=["Bolt AI Editor"])


@router.post("/chat/stream")
async def stream_bolt_chat(
    request: BoltChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Stream AI responses for Bolt.new-style chat
    Uses Server-Sent Events (SSE) for real-time streaming
    """
    # Initialize enterprise tracker for message logging
    tracker = EnterpriseTracker(db)
    project_uuid = UUID(request.project_id) if hasattr(request, 'project_id') and request.project_id else None

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Track user message if project exists
            if project_uuid:
                await tracker.track_user_message(project_uuid, request.message)

            # Send status event
            yield f"data: {json.dumps({'type': 'status', 'data': {'message': 'Building context...'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Build context from project files
            files_dict = [f.model_dump() for f in request.files]

            context = context_builder.build_context(
                user_prompt=request.message,
                files=files_dict,
                project_name=request.project_name,
                selected_file_path=request.selected_file,
                max_files=10,
                max_tokens=50000
            )

            # Format context for Claude
            formatted_context = context_builder.format_for_claude(context)

            # Send status event
            yield f"data: {json.dumps({'type': 'status', 'data': {'message': 'Generating response...', 'files_analyzed': len(context.selected_files)}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Build messages for Claude
            messages = []
            for msg in request.conversation_history:
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            # Stream response from Claude
            full_response = ""
            total_tokens = 0
            async for chunk in claude_client.generate_stream(
                prompt=formatted_context,
                system_prompt=BOLT_SYSTEM_PROMPT,
                model="sonnet",
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                messages=messages if messages else None
            ):
                full_response += chunk
                total_tokens += len(chunk) // 4  # Rough token estimate

                # Send content event
                yield f"data: {json.dumps({'type': 'content', 'data': {'chunk': chunk}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Track AI response if project exists
            if project_uuid:
                await tracker.track_agent_response(
                    project_uuid,
                    agent_type="assistant",
                    content=full_response,
                    tokens_used=total_tokens
                )

            # Parse response for file changes (unified diffs)
            file_changes = _extract_file_changes(full_response)

            if file_changes:
                yield f"data: {json.dumps({'type': 'file_changes', 'data': {'changes': file_changes}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

            # Send done event
            yield f"data: {json.dumps({'type': 'done', 'data': {'message': 'Response complete'}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

        except Exception as e:
            logger.error(f"Bolt streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'error': str(e)}, 'timestamp': datetime.utcnow().isoformat()})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/chat", response_model=BoltChatResponse)
async def bolt_chat(
    request: BoltChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Non-streaming Bolt chat endpoint
    Returns complete response at once
    """
    try:
        # Build context
        files_dict = [f.model_dump() for f in request.files]

        context = context_builder.build_context(
            user_prompt=request.message,
            files=files_dict,
            project_name=request.project_name,
            selected_file_path=request.selected_file,
            max_files=10,
            max_tokens=50000
        )

        formatted_context = context_builder.format_for_claude(context)

        # Build messages
        messages = []
        for msg in request.conversation_history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        # Generate response
        response = await claude_client.generate(
            prompt=formatted_context,
            system_prompt=BOLT_SYSTEM_PROMPT,
            model="sonnet",
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            messages=messages if messages else None
        )

        return BoltChatResponse(**response)

    except Exception as e:
        logger.error(f"Bolt chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/apply-patch", response_model=ApplyPatchResponse)
async def apply_patch(
    request: ApplyPatchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Apply a unified diff patch to a file
    """
    try:
        from app.modules.bolt.patch_applier import apply_unified_patch

        result = apply_unified_patch(
            original_content=request.original_content,
            patch=request.patch
        )

        return ApplyPatchResponse(**result)

    except Exception as e:
        logger.error(f"Patch application error: {e}", exc_info=True)
        return ApplyPatchResponse(
            success=False,
            error=str(e)
        )


@router.post("/files/create", response_model=FileOperationResponse)
async def create_file(
    request: CreateFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new file"""
    try:
        file_schema = ProjectFileSchema(
            path=request.path,
            content=request.content,
            language=request.language,
            type="file"
        )

        # Save to database if project_id provided
        if request.project_id:
            try:
                project_uuid = UUID(request.project_id)

                # Verify project exists and belongs to user
                result = await db.execute(
                    select(Project).where(
                        Project.id == project_uuid,
                        Project.user_id == current_user.id
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")

                # Check if file already exists
                existing_result = await db.execute(
                    select(ProjectFile).where(
                        ProjectFile.project_id == project_uuid,
                        ProjectFile.path == request.path
                    )
                )
                existing_file = existing_result.scalar_one_or_none()

                if existing_file:
                    raise HTTPException(status_code=400, detail="File already exists")

                # Calculate content hash and size
                content_bytes = request.content.encode('utf-8')
                content_hash = hashlib.sha256(content_bytes).hexdigest()
                size_bytes = len(content_bytes)

                # Extract file name from path
                file_name = os.path.basename(request.path)
                parent_path = os.path.dirname(request.path) or None

                # Upload content to S3 (all content goes to S3, not inline)
                upload_result = await storage_service.upload_file(
                    str(project_uuid),
                    request.path,
                    content_bytes
                )
                s3_key = upload_result.get('s3_key')

                # Create new file record (metadata only, content in S3)
                new_file = ProjectFile(
                    project_id=project_uuid,
                    path=request.path,
                    name=file_name,
                    language=request.language,
                    content_hash=content_hash,
                    size_bytes=size_bytes,
                    s3_key=s3_key,
                    content_inline=None,  # Never store content inline
                    is_inline=False,  # Always use S3
                    is_folder=False,
                    parent_path=parent_path
                )

                db.add(new_file)
                await db.commit()
                await db.refresh(new_file)

                # Track file creation in version history
                tracker = EnterpriseTracker(db)
                await tracker.track_file_created(
                    project_id=project_uuid,
                    file_id=new_file.id,
                    content=request.content,
                    created_by="user"
                )

                logger.info(f"File {request.path} created in project {request.project_id}")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project_id format")

        return FileOperationResponse(
            success=True,
            message=f"File {request.path} created successfully",
            file=file_schema
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/update", response_model=FileOperationResponse)
async def update_file(
    request: UpdateFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing file"""
    try:
        # Update in database if project_id provided
        if request.project_id:
            try:
                project_uuid = UUID(request.project_id)

                # Verify project exists and belongs to user
                result = await db.execute(
                    select(Project).where(
                        Project.id == project_uuid,
                        Project.user_id == current_user.id
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")

                # Find the existing file
                file_result = await db.execute(
                    select(ProjectFile).where(
                        ProjectFile.project_id == project_uuid,
                        ProjectFile.path == request.path
                    )
                )
                existing_file = file_result.scalar_one_or_none()

                tracker = EnterpriseTracker(db)

                if not existing_file:
                    # File doesn't exist, create it
                    content_bytes = request.content.encode('utf-8')
                    content_hash = hashlib.sha256(content_bytes).hexdigest()
                    size_bytes = len(content_bytes)
                    file_name = os.path.basename(request.path)
                    parent_path = os.path.dirname(request.path) or None

                    # Upload content to S3
                    upload_result = await storage_service.upload_file(
                        str(project_uuid),
                        request.path,
                        content_bytes
                    )
                    s3_key = upload_result.get('s3_key')

                    new_file = ProjectFile(
                        project_id=project_uuid,
                        path=request.path,
                        name=file_name,
                        language="plaintext",
                        content_hash=content_hash,
                        size_bytes=size_bytes,
                        s3_key=s3_key,
                        content_inline=None,  # Never store content inline
                        is_inline=False,  # Always use S3
                        is_folder=False,
                        parent_path=parent_path
                    )
                    db.add(new_file)
                    await db.commit()
                    await db.refresh(new_file)

                    # Track file creation
                    await tracker.track_file_created(
                        project_id=project_uuid,
                        file_id=new_file.id,
                        content=request.content,
                        created_by="user"
                    )
                else:
                    # Capture old content for version tracking
                    old_content = ""
                    if existing_file.s3_key:
                        old_bytes = await storage_service.download_file(existing_file.s3_key)
                        old_content = old_bytes.decode('utf-8') if old_bytes else ""
                    elif existing_file.content_inline:
                        old_content = existing_file.content_inline

                    # Update existing file - upload new content to S3
                    content_bytes = request.content.encode('utf-8')
                    old_s3_key = existing_file.s3_key

                    # Upload new content to S3
                    upload_result = await storage_service.upload_file(
                        str(project_uuid),
                        request.path,
                        content_bytes
                    )
                    new_s3_key = upload_result.get('s3_key')

                    existing_file.content_hash = hashlib.sha256(content_bytes).hexdigest()
                    existing_file.size_bytes = len(content_bytes)
                    existing_file.s3_key = new_s3_key
                    existing_file.content_inline = None  # Never store content inline
                    existing_file.is_inline = False  # Always use S3
                    existing_file.updated_at = datetime.utcnow()

                    await db.commit()

                    # Delete old S3 file if key changed
                    if old_s3_key and old_s3_key != new_s3_key:
                        try:
                            await storage_service.delete_file(old_s3_key)
                        except Exception:
                            pass  # Ignore cleanup errors

                    # Track file edit in version history
                    await tracker.track_file_edited(
                        project_id=project_uuid,
                        file_id=existing_file.id,
                        new_content=request.content,
                        old_content=old_content,
                        edited_by="user"
                    )

                logger.info(f"File {request.path} updated in project {request.project_id}")

            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project_id format")

        return FileOperationResponse(
            success=True,
            message=f"File {request.path} updated successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/delete", response_model=FileOperationResponse)
async def delete_file(
    request: DeleteFileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a file"""
    try:
        # Delete from database if project_id provided
        if request.project_id:
            try:
                project_uuid = UUID(request.project_id)

                # Verify project exists and belongs to user
                result = await db.execute(
                    select(Project).where(
                        Project.id == project_uuid,
                        Project.user_id == current_user.id
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise HTTPException(status_code=404, detail="Project not found")

                # Find the file to delete
                file_result = await db.execute(
                    select(ProjectFile).where(
                        ProjectFile.project_id == project_uuid,
                        ProjectFile.path == request.path
                    )
                )
                existing_file = file_result.scalar_one_or_none()

                if existing_file:
                    await db.delete(existing_file)
                    await db.commit()
                    logger.info(f"File {request.path} deleted from project {request.project_id}")
                else:
                    logger.warning(f"File {request.path} not found in project {request.project_id}")

            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid project_id format")

        return FileOperationResponse(
            success=True,
            message=f"File {request.path} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute", response_model=ExecuteCodeResponse)
async def execute_code(
    request: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute code in Docker sandbox
    """
    try:
        from app.modules.sandbox.docker_executor import docker_executor

        # Check if Docker is available
        if not docker_executor.check_docker_available():
            raise HTTPException(
                status_code=503,
                detail="Docker service is not available"
            )

        # Convert files to dict format
        files_dict = [f.model_dump() for f in request.files]

        # Execute code
        result = await docker_executor.execute(
            files=files_dict,
            command=request.command,
            environment=request.environment,
            timeout=request.timeout
        )

        return ExecuteCodeResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            exit_code=result.exit_code,
            execution_time=result.execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Code execution error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute/stream")
async def execute_code_stream(
    request: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Execute code and stream logs in real-time
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            from app.modules.sandbox.docker_executor import docker_executor

            if not docker_executor.check_docker_available():
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Docker not available'}})}\n\n"
                return

            files_dict = [f.model_dump() for f in request.files]

            yield f"data: {json.dumps({'type': 'status', 'data': {'message': 'Starting container...'}})}\n\n"

            async for log_line in docker_executor.execute_stream(
                files=files_dict,
                command=request.command,
                environment=request.environment,
                timeout=request.timeout
            ):
                yield f"data: {json.dumps({'type': 'log', 'data': {'line': log_line}})}\n\n"

            yield f"data: {json.dumps({'type': 'done', 'data': {'message': 'Execution complete'}})}\n\n"

        except Exception as e:
            logger.error(f"Stream execution error: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/install-dependencies", response_model=ExecuteCodeResponse)
async def install_dependencies(
    request: ExecuteCodeRequest,
    current_user: User = Depends(get_current_user)
):
    """Install project dependencies"""
    try:
        from app.modules.sandbox.docker_executor import docker_executor

        if not docker_executor.check_docker_available():
            raise HTTPException(
                status_code=503,
                detail="Docker service is not available"
            )

        files_dict = [f.model_dump() for f in request.files]

        result = await docker_executor.install_dependencies(
            files=files_dict,
            environment=request.environment
        )

        return ExecuteCodeResponse(
            success=result.success,
            output=result.output,
            error=result.error,
            exit_code=result.exit_code,
            execution_time=result.execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dependency installation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _extract_file_changes(response: str) -> list:
    """Extract unified diff patches from AI response"""
    import re

    # Pattern to match unified diffs
    diff_pattern = r'```diff\n(.*?)\n```'
    matches = re.findall(diff_pattern, response, re.DOTALL)

    changes = []
    for match in matches:
        # Extract file path from diff header
        file_match = re.search(r'\+\+\+ b/(.*)', match)
        if file_match:
            changes.append({
                'file_path': file_match.group(1),
                'patch': match
            })

    return changes


@router.get("/files/{project_id}", response_model=GetProjectFilesResponse)
async def get_project_files(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all files for a project.

    COMPLETE FLOW (Bolt.new style):
    UI → Bolt API → Workspace Loader → Metadata DB → Reconstruct Files → Return Tree + Files → UI Editor

    1. Check if sandbox workspace exists
    2. If not, auto-restore from database/S3 using WorkspaceRestoreService
    3. Return files with content
    """
    try:
        from app.services.workspace_restore import workspace_restore

        user_id = str(current_user.id)

        # Step 1: Check workspace status using WorkspaceRestoreService
        status = await workspace_restore.check_workspace_status(project_id, db, user_id)
        logger.info(f"[Bolt] Workspace status for {project_id}: exists={status['workspace_exists']}, can_restore={status['can_restore']}")

        # Step 2: If workspace doesn't exist, auto-restore from storage
        if not status["workspace_exists"] and status["can_restore"]:
            logger.info(f"[Bolt] Auto-restoring workspace for {project_id}")
            restore_result = await workspace_restore.restore_from_storage(project_id, db, user_id)
            if restore_result.get("success"):
                logger.info(f"[Bolt] Restored {restore_result.get('restored_files')} files for {project_id}")
            else:
                logger.warning(f"[Bolt] Restore failed: {restore_result.get('error')}")

        # Step 3: Try to get files from sandbox first (Layer 1 - fastest)
        storage = UnifiedStorageService()
        if await storage.sandbox_exists(project_id, user_id):
            # Load from sandbox
            files = await storage.list_sandbox_files(project_id, user_id)
            file_schemas = []

            def process_files(file_list):
                for f in file_list:
                    if f.type == 'file':
                        # Read content from sandbox
                        import asyncio
                        content = asyncio.get_event_loop().run_until_complete(
                            storage.read_from_sandbox(project_id, f.path, user_id)
                        ) if hasattr(asyncio, 'get_event_loop') else None
                        file_schemas.append(ProjectFileSchema(
                            path=f.path,
                            content=content or '',
                            language=f.language or "plaintext",
                            type="file"
                        ))
                    elif f.children:
                        process_files(f.children)

            # Async version
            async def process_files_async(file_list):
                for f in file_list:
                    if f.type == 'file':
                        content = await storage.read_from_sandbox(project_id, f.path, user_id)
                        file_schemas.append(ProjectFileSchema(
                            path=f.path,
                            content=content or '',
                            language=f.language or "plaintext",
                            type="file"
                        ))
                    elif f.children:
                        await process_files_async(f.children)

            await process_files_async(files)

            return GetProjectFilesResponse(
                success=True,
                project_id=project_id,
                files=file_schemas,
                total_files=len(file_schemas)
            )

        # Step 4: Fallback to database (Layer 4 - ProjectFile table)
        # Cast column to String(36) to handle UUID/VARCHAR mismatch
        from sqlalchemy import cast, String as SQLString
        files_result = await db.execute(
            select(ProjectFile).where(
                cast(ProjectFile.project_id, SQLString(36)) == str(project_id),
                ProjectFile.is_folder == False
            ).order_by(ProjectFile.path)
        )
        files = files_result.scalars().all()

        # Convert to schema - fetch content from S3 or fallback to inline
        file_schemas = []
        for f in files:
            content = None
            if f.s3_key:
                content_bytes = await storage_service.download_file(f.s3_key)
                content = content_bytes.decode('utf-8') if content_bytes else None
            elif f.content_inline:
                content = f.content_inline  # Legacy fallback

            file_schemas.append(ProjectFileSchema(
                path=f.path,
                content=content,
                language=f.language or "plaintext",
                type="file"
            ))

        return GetProjectFilesResponse(
            success=True,
            project_id=project_id,
            files=file_schemas,
            total_files=len(file_schemas)
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get project files error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/sync", response_model=BulkSyncFilesResponse)
async def bulk_sync_files(
    request: BulkSyncFilesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk sync files for a project.
    Creates new files, updates existing ones, preserves files not in the request.

    IMPORTANT: This endpoint now syncs to BOTH:
    1. PostgreSQL database (Layer 3) - for persistence/recovery
    2. Sandbox disk (Layer 1) - for preview/execution
    """
    try:
        project_uuid = UUID(request.project_id)

        # Verify project exists and belongs to user
        result = await db.execute(
            select(Project).where(
                Project.id == project_uuid,
                Project.user_id == current_user.id
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Initialize storage service for sandbox writes
        storage = UnifiedStorageService()

        # Get user_id for user-scoped paths (Bolt.new structure)
        user_id = str(current_user.id)

        # Ensure sandbox exists with user-scoped path: {user_id}/{project_id}
        await storage.create_sandbox(request.project_id, user_id)

        # Get existing files
        existing_result = await db.execute(
            select(ProjectFile).where(ProjectFile.project_id == project_uuid)
        )
        existing_files = {f.path: f for f in existing_result.scalars().all()}

        files_created = 0
        files_updated = 0
        sandbox_writes = 0

        # Process each file in the request
        for file_data in request.files:
            if file_data.type == "folder":
                continue  # Skip folders

            content = file_data.content or ""
            content_bytes = content.encode('utf-8')
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            size_bytes = len(content_bytes)

            # ========== LAYER 1: Write to Sandbox (for preview/execution) ==========
            try:
                sandbox_success = await storage.write_to_sandbox(
                    request.project_id,
                    file_data.path,
                    content,
                    user_id  # User-scoped path
                )
                if sandbox_success:
                    sandbox_writes += 1
            except Exception as e:
                logger.warning(f"Failed to write {file_data.path} to sandbox: {e}")

            # ========== LAYER 2: Upload to S3 ==========
            upload_result = await storage_service.upload_file(
                request.project_id,
                file_data.path,
                content_bytes
            )
            s3_key = upload_result.get('s3_key')

            # ========== LAYER 3: Write to Database (metadata only) ==========
            if file_data.path in existing_files:
                # Update existing file
                existing_file = existing_files[file_data.path]
                if existing_file.content_hash != content_hash:
                    old_s3_key = existing_file.s3_key
                    existing_file.content_hash = content_hash
                    existing_file.size_bytes = size_bytes
                    existing_file.s3_key = s3_key
                    existing_file.content_inline = None  # Never store content inline
                    existing_file.is_inline = False  # Always use S3
                    existing_file.language = file_data.language
                    existing_file.updated_at = datetime.utcnow()
                    files_updated += 1
                    # Clean up old S3 key if different
                    if old_s3_key and old_s3_key != s3_key:
                        try:
                            await storage_service.delete_file(old_s3_key)
                        except Exception:
                            pass
            else:
                # Create new file
                file_name = os.path.basename(file_data.path)
                parent_path = os.path.dirname(file_data.path) or None

                new_file = ProjectFile(
                    project_id=project_uuid,
                    path=file_data.path,
                    name=file_name,
                    language=file_data.language,
                    content_hash=content_hash,
                    size_bytes=size_bytes,
                    s3_key=s3_key,
                    content_inline=None,  # Never store content inline
                    is_inline=False,  # Always use S3
                    is_folder=False,
                    parent_path=parent_path
                )
                db.add(new_file)
                files_created += 1

        await db.commit()

        logger.info(
            f"Synced files for project {request.project_id}: "
            f"{files_created} created, {files_updated} updated, "
            f"{sandbox_writes} written to sandbox"
        )

        return BulkSyncFilesResponse(
            success=True,
            files_created=files_created,
            files_updated=files_updated,
            files_deleted=0,
            message=f"Synced {files_created + files_updated} files to DB, {sandbox_writes} to sandbox"
        )

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid project_id format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Bulk sync files error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PROJECT GENERATION - Use /api/v1/orchestrator/execute instead
# These endpoints are deprecated. Use dynamic_orchestrator via /orchestrator/execute
# ============================================================================
