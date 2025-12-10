"""
FILE SYNC ENDPOINTS - 3-Layer Storage Architecture

LAYER 1: Sandbox (Runtime) - /sandbox/workspace/<project-id>/
         For preview, run, build, test. Ephemeral, deleted on close.

LAYER 2: S3/MinIO (Permanent) - s3://bucket/projects/<user>/<project>/
         All real files, ZIP, PDFs, diagrams. Permanent storage.

LAYER 3: PostgreSQL (Metadata) - projects table
         project_id, s3_path, plan_json, file_index, history
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, cast, String
import json

from app.core.logging_config import logger
from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project, ProjectStatus, ProjectMode
from app.models.project_file import ProjectFile
from app.services.unified_storage import unified_storage


router = APIRouter(prefix="/sync", tags=["File Sync (3-Layer)"])


# ==================== REQUEST/RESPONSE MODELS ====================

class FileSyncRequest(BaseModel):
    """Request to sync a single file"""
    project_id: str
    path: str
    content: str
    language: Optional[str] = None


class BulkFileSyncRequest(BaseModel):
    """Request to sync multiple files"""
    project_id: str
    files: List[dict]  # [{path, content, language?}, ...]


class SaveToS3Request(BaseModel):
    """Request to save sandbox to S3 (Layer 1 → Layer 2)"""
    project_id: str
    create_zip: bool = True


class FileSyncResponse(BaseModel):
    """Response for file sync operations"""
    success: bool
    message: str
    files_synced: int = 0
    layer: str = "sandbox"  # Which layer was used


# ==================== LAYER 1: SANDBOX OPERATIONS ====================

@router.post("/sandbox/file", response_model=FileSyncResponse)
async def write_to_sandbox(
    request: FileSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Write a single file to sandbox (Layer 1).
    Used during active editing/generation.
    """
    try:
        # Get user_id for user-scoped paths (Bolt.new structure)
        user_id = str(current_user.id)

        # Ensure sandbox exists with user-scoped path
        await unified_storage.create_sandbox(request.project_id, user_id)

        # Write file to user-scoped sandbox
        success = await unified_storage.write_to_sandbox(
            project_id=request.project_id,
            file_path=request.path,
            content=request.content,
            user_id=user_id
        )

        if success:
            logger.info(f"[Layer 1] Wrote to sandbox: {request.project_id}/{request.path}")
            return FileSyncResponse(
                success=True,
                message=f"File written to sandbox: {request.path}",
                files_synced=1,
                layer="sandbox"
            )
        else:
            return FileSyncResponse(
                success=False,
                message="Failed to write file to sandbox",
                layer="sandbox"
            )

    except Exception as e:
        logger.error(f"Sandbox write error: {e}", exc_info=True)
        return FileSyncResponse(
            success=False,
            message=str(e),
            layer="sandbox"
        )


@router.post("/sandbox/files", response_model=FileSyncResponse)
async def write_multiple_to_sandbox(
    request: BulkFileSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Write multiple files to sandbox (Layer 1).
    Used during bulk generation.
    """
    try:
        # Get user_id for user-scoped paths (Bolt.new structure)
        user_id = str(current_user.id)

        await unified_storage.create_sandbox(request.project_id, user_id)

        synced_count = 0
        for file_data in request.files:
            file_path = file_data.get('path')
            content = file_data.get('content', '')

            if file_path:
                success = await unified_storage.write_to_sandbox(
                    project_id=request.project_id,
                    file_path=file_path,
                    content=content,
                    user_id=user_id
                )
                if success:
                    synced_count += 1

        logger.info(f"[Layer 1] Bulk wrote {synced_count} files to sandbox: {request.project_id}")

        return FileSyncResponse(
            success=synced_count > 0,
            message=f"Wrote {synced_count} files to sandbox",
            files_synced=synced_count,
            layer="sandbox"
        )

    except Exception as e:
        logger.error(f"Sandbox bulk write error: {e}", exc_info=True)
        return FileSyncResponse(
            success=False,
            message=str(e),
            layer="sandbox"
        )


@router.get("/sandbox/{project_id}/files")
async def get_sandbox_files(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all files from sandbox (Layer 1) with content.
    Returns hierarchical tree structure.
    """
    try:
        # Get user_id for user-scoped paths (Bolt.new structure)
        user_id = str(current_user.id)

        files = await unified_storage.list_sandbox_files(project_id, user_id)

        if not files:
            return {
                "success": True,
                "project_id": project_id,
                "tree": [],
                "layer": "sandbox",
                "message": "No files in sandbox"
            }

        # Add content to files
        async def add_content_recursive(file_list):
            result = []
            for f in file_list:
                file_dict = f.to_dict()
                if f.type == 'file':
                    file_dict['content'] = await unified_storage.read_from_sandbox(
                        project_id, f.path, user_id
                    ) or ''
                elif f.children:
                    file_dict['children'] = await add_content_recursive(f.children)
                result.append(file_dict)
            return result

        tree_with_content = await add_content_recursive(files)

        return {
            "success": True,
            "project_id": project_id,
            "tree": tree_with_content,
            "layer": "sandbox",
            "total": len(unified_storage._flatten_tree(files))
        }

    except Exception as e:
        logger.error(f"Get sandbox files error: {e}", exc_info=True)
        return {
            "success": False,
            "project_id": project_id,
            "tree": [],
            "error": str(e)
        }


@router.delete("/sandbox/{project_id}")
async def delete_sandbox(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete sandbox workspace (Layer 1).
    Called when tab is closed or session ends.
    """
    try:
        # Get user_id for user-scoped paths (Bolt.new structure)
        user_id = str(current_user.id)

        success = await unified_storage.delete_sandbox(project_id, user_id)
        return {
            "success": success,
            "message": "Sandbox deleted" if success else "Sandbox not found"
        }
    except Exception as e:
        logger.error(f"Delete sandbox error: {e}")
        return {"success": False, "error": str(e)}


# ==================== LAYER 2: S3 OPERATIONS ====================

@router.post("/s3/save")
async def save_to_s3(
    request: SaveToS3Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Save sandbox (Layer 1) to S3 (Layer 2).
    Also updates PostgreSQL metadata (Layer 3).

    This is called when:
    - Generation is complete
    - User clicks "Save to cloud"
    - Auto-save interval
    """
    try:
        user_id = str(current_user.id)
        project_id = request.project_id

        # Check if sandbox exists (with user-scoped path)
        if not await unified_storage.sandbox_exists(project_id, user_id):
            raise HTTPException(status_code=404, detail="Sandbox not found")

        # Save to S3 (Layer 2)
        result = await unified_storage.save_project(
            user_id=user_id,
            project_id=project_id,
            persist_to_s3=True
        )

        if not result.get('success'):
            return result

        # Update PostgreSQL metadata (Layer 3)
        # Note: Project.id is String(36) not UUID, use cast() to prevent asyncpg UUID conversion
        try:
            db_result = await db.execute(
                select(Project).where(Project.id == cast(project_id, String(36)))
            )
            project = db_result.scalar_one_or_none()

            if project:
                project.s3_path = result.get('s3_prefix')
                project.s3_zip_key = result.get('zip_s3_key')
                project.file_index = result.get('file_index')
                project.status = ProjectStatus.COMPLETED
                await db.commit()
                logger.info(f"[Layer 3] Updated project metadata: {project_id}")
        except ValueError:
            # Not a valid UUID, skip database update
            pass

        return {
            "success": True,
            "message": "Project saved to S3",
            "s3_prefix": result.get('s3_prefix'),
            "zip_key": result.get('zip_s3_key'),
            "total_files": result.get('total_files'),
            "total_size_bytes": result.get('total_size_bytes'),
            "layer": "s3"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Save to S3 error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/s3/{project_id}/download-url")
async def get_download_url(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get presigned download URL for project ZIP from S3 (Layer 2).
    """
    try:
        user_id = str(current_user.id)
        url = await unified_storage.get_download_url(user_id, project_id)

        if url:
            return {"success": True, "download_url": url}
        else:
            return {"success": False, "error": "Download URL not available"}

    except Exception as e:
        logger.error(f"Get download URL error: {e}")
        return {"success": False, "error": str(e)}


# ==================== UNIFIED: GET FILES (ALL LAYERS) ====================

@router.get("/files/{project_id}")
async def get_project_files(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get project files from the appropriate layer.

    Priority:
    1. Check Layer 1 (sandbox) - if exists, use it (active editing)
    2. Check Layer 3 (PostgreSQL) for s3_path and file_index
    3. Fetch from Layer 2 (S3) using file_index

    Response includes project_title for proper display in frontend.
    """
    try:
        user_id = str(current_user.id)
        actual_user_id = user_id  # Track actual user_id used

        # Fetch project title from database upfront
        project_title = None
        project_description = None
        try:
            db_result = await db.execute(
                select(Project).where(Project.id == cast(project_id, String(36)))
            )
            project_record = db_result.scalar_one_or_none()
            if project_record:
                project_title = project_record.title
                project_description = project_record.description
                logger.debug(f"[get_project_files] Found project: {project_title}")
        except Exception as e:
            logger.warning(f"[get_project_files] Could not fetch project title: {e}")

        # Helper function to load files from sandbox
        async def load_from_sandbox(proj_id: str, uid: str, layer_name: str):
            files = await unified_storage.list_sandbox_files(proj_id, uid)

            async def add_content_recursive(file_list):
                result = []
                for f in file_list:
                    file_dict = f.to_dict()
                    if f.type == 'file':
                        file_dict['content'] = await unified_storage.read_from_sandbox(
                            proj_id, f.path, uid
                        ) or ''
                    elif f.children:
                        file_dict['children'] = await add_content_recursive(f.children)
                    result.append(file_dict)
                return result

            tree = await add_content_recursive(files)
            return {
                "success": True,
                "project_id": proj_id,
                "tree": tree,
                "layer": layer_name,
                "total": len(unified_storage._flatten_tree(files))
            }

        # 1. Check sandbox (Layer 1) with user-scoped path
        # Only use sandbox if it exists AND has files (not empty) - Fixed
        if await unified_storage.sandbox_exists(project_id, user_id):
            sandbox_files = await unified_storage.list_sandbox_files(project_id, user_id)
            if sandbox_files:  # Has files, use sandbox
                logger.info(f"[Layer 1] Loading from sandbox: {user_id}/{project_id} ({len(sandbox_files)} files)")
                result = await load_from_sandbox(project_id, user_id, "sandbox")
                # Add project title from database lookup
                if project_title:
                    result["project_title"] = project_title
                    result["project_description"] = project_description
                return result
            else:
                logger.info(f"[Layer 1] Sandbox exists but empty for {user_id}/{project_id}, falling through to database")

        # 1.5 FALLBACK: Search for project in ANY user's sandbox directory
        # This handles cases where files were created by auto-fix or other processes
        from pathlib import Path
        import platform
        sandbox_base = Path("C:/tmp/sandbox/workspace") if platform.system() == "Windows" else Path("/tmp/sandbox/workspace")

        if sandbox_base.exists():
            for potential_user_dir in sandbox_base.iterdir():
                if potential_user_dir.is_dir():
                    potential_project_path = potential_user_dir / project_id
                    if potential_project_path.exists() and any(potential_project_path.iterdir()):
                        found_user_id = potential_user_dir.name
                        logger.info(f"[Layer 1.5] Found project in {found_user_id}/{project_id} (current user: {user_id})")
                        result = await load_from_sandbox(project_id, found_user_id, "sandbox_found")
                        # Add project title from database lookup
                        if project_title:
                            result["project_title"] = project_title
                            result["project_description"] = project_description
                        return result

        # 2. Check PostgreSQL (Layer 3) for metadata
        # Note: Project.id is String(36) not UUID, use cast() to prevent asyncpg UUID conversion
        try:
            db_result = await db.execute(
                select(Project).where(Project.id == cast(project_id, String(36)))
            )
            project = db_result.scalar_one_or_none()

            if project and project.s3_path and project.file_index:
                logger.info(f"[Layer 2] Loading from S3 via metadata: {project_id}")

                # Load from S3 using file_index
                files = await unified_storage.load_project_for_editing(
                    user_id=user_id,
                    project_id=project_id,
                    s3_prefix=project.s3_path,
                    file_index=project.file_index
                )

                # Convert to dict
                tree = [f.to_dict() for f in files]

                # Add content (with user-scoped path)
                async def add_content(items):
                    for item in items:
                        if item.get('type') == 'file':
                            item['content'] = await unified_storage.read_from_sandbox(
                                project_id, item['path'], user_id
                            ) or ''
                        if item.get('children'):
                            await add_content(item['children'])

                await add_content(tree)

                return {
                    "success": True,
                    "project_id": project_id,
                    "project_title": project_title,
                    "project_description": project_description,
                    "tree": tree,
                    "layer": "s3",
                    "total": len(project.file_index or [])
                }
        except ValueError:
            pass  # Not a valid UUID

        # 3. Check ProjectFile table (Layer 4 - Database storage)
        # This is where files are stored by the writer agent
        # Use cast() to prevent asyncpg UUID conversion
        try:
            db_result = await db.execute(
                select(ProjectFile).where(ProjectFile.project_id == cast(project_id, String(36)))
            )
            project_files = db_result.scalars().all()

            if project_files:
                logger.info(f"[Layer 4] Loading {len(project_files)} files from database: {project_id}")

                # IMPORTANT: Restore files to sandbox so they can be executed!
                # This ensures /execution/run can find the files
                try:
                    await unified_storage.create_sandbox(project_id, user_id)
                    files_restored = 0
                    for pf in project_files:
                        if pf.content_inline and not pf.is_folder:
                            success = await unified_storage.write_to_sandbox(
                                project_id=project_id,
                                file_path=pf.path,
                                content=pf.content_inline,
                                user_id=user_id
                            )
                            if success:
                                files_restored += 1
                    logger.info(f"[Layer 4] Restored {files_restored} files to sandbox for execution")
                except Exception as restore_error:
                    logger.warning(f"[Layer 4] Failed to restore to sandbox: {restore_error}")

                # Build hierarchical tree from flat file list
                def build_tree(files):
                    """Convert flat file list to hierarchical tree"""
                    root = []
                    # Track folders by path to avoid duplicates
                    folder_registry = {}

                    # First pass: identify all folder paths from files
                    # This prevents creating duplicate folders
                    for pf in files:
                        if pf.is_folder:
                            # Skip folder records - they'll be created from file paths
                            continue

                        file_path = pf.path
                        content = pf.content_inline or ""

                        # Detect language from extension
                        ext = file_path.rsplit(".", 1)[-1] if "." in file_path else ""
                        lang_map = {
                            "ts": "typescript", "tsx": "typescript",
                            "js": "javascript", "jsx": "javascript",
                            "py": "python", "json": "json",
                            "html": "html", "css": "css",
                            "md": "markdown", "yaml": "yaml", "yml": "yaml"
                        }
                        language = lang_map.get(ext, "plaintext")

                        # Split path into parts
                        parts = file_path.split("/")

                        if len(parts) == 1:
                            # Root level file
                            root.append({
                                "path": file_path,
                                "name": file_path,
                                "type": "file",
                                "content": content,
                                "language": language
                            })
                        else:
                            # Nested file - create folder structure
                            current_level = root
                            current_path = ""

                            for i, part in enumerate(parts[:-1]):
                                current_path = f"{current_path}/{part}" if current_path else part

                                # Check if folder already exists in registry
                                if current_path in folder_registry:
                                    folder = folder_registry[current_path]
                                else:
                                    # Find or create folder in current level
                                    folder = None
                                    for item in current_level:
                                        if item.get("type") == "folder" and item.get("path") == current_path:
                                            folder = item
                                            break

                                    if not folder:
                                        folder = {
                                            "path": current_path,
                                            "name": part,
                                            "type": "folder",
                                            "children": []
                                        }
                                        current_level.append(folder)
                                        folder_registry[current_path] = folder

                                current_level = folder.get("children", [])
                                if "children" not in folder:
                                    folder["children"] = current_level

                            # Add file to current folder
                            current_level.append({
                                "path": file_path,
                                "name": parts[-1],
                                "type": "file",
                                "content": content,
                                "language": language
                            })

                    return root

                tree = build_tree(project_files)

                return {
                    "success": True,
                    "project_id": project_id,
                    "project_title": project_title,
                    "project_description": project_description,
                    "tree": tree,
                    "layer": "database",
                    "total": len(project_files)
                }
        except Exception as db_error:
            logger.warning(f"[Layer 4] Database lookup failed: {db_error}")

        # 4. No files found
        return {
            "success": True,
            "project_id": project_id,
            "project_title": project_title,
            "project_description": project_description,
            "tree": [],
            "layer": "none",
            "message": "No files found for this project"
        }

    except Exception as e:
        logger.error(f"Get project files error: {e}", exc_info=True)
        return {
            "success": False,
            "project_id": project_id,
            "tree": [],
            "error": str(e)
        }


# ==================== LIST PROJECTS (ALL LAYERS) ====================

@router.get("/projects")
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List all projects from Layer 3 (PostgreSQL).
    Shows projects with their storage locations.
    """
    try:
        # Get from PostgreSQL (Layer 3)
        result = await db.execute(
            select(Project)
            .where(Project.user_id == current_user.id)
            .order_by(Project.updated_at.desc())
        )
        projects = result.scalars().all()

        project_list = []
        for p in projects:
            project_list.append({
                "id": str(p.id),
                "title": p.title,
                "description": p.description,
                "status": p.status.value if p.status else "draft",
                "technology": p.technology,
                "s3_path": p.s3_path,
                "has_files": bool(p.file_index),
                "file_count": len(p.file_index) if p.file_index else 0,
                "total_tokens": p.total_tokens,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None
            })

        return {
            "success": True,
            "projects": project_list,
            "total": len(project_list)
        }

    except Exception as e:
        logger.error(f"List projects error: {e}", exc_info=True)
        return {
            "success": False,
            "projects": [],
            "error": str(e)
        }


# ==================== LEGACY COMPATIBILITY ====================
# Keep old endpoints working for backward compatibility

@router.post("/file", response_model=FileSyncResponse)
async def sync_file_legacy(
    request: FileSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """Legacy: Redirect to sandbox write"""
    return await write_to_sandbox(request, current_user)


@router.post("/files", response_model=FileSyncResponse)
async def sync_files_legacy(
    request: BulkFileSyncRequest,
    current_user: User = Depends(get_current_user)
):
    """Legacy: Redirect to sandbox bulk write"""
    return await write_multiple_to_sandbox(request, current_user)
# Trigger reload
