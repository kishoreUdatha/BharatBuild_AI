"""
Download Endpoint - ZIP download with immediate cleanup

Flow:
1. User generates project → files stored in temp session
2. User clicks "Download ZIP"
3. Server creates ZIP → streams to user
4. Server DELETES session immediately after download

Zero permanent storage!
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional
import os
import asyncio

from app.services.temp_session_storage import temp_storage

router = APIRouter()


@router.get("/session/{session_id}")
async def download_project_zip(
    session_id: str,
    background_tasks: BackgroundTasks,
    cleanup: bool = True  # Set to False if user wants to keep editing
):
    """
    Download project as ZIP file.

    After download, session is automatically deleted (unless cleanup=False).
    """
    # Check session exists
    if not temp_storage.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please regenerate the project."
        )

    # Get session info for filename
    session_info = temp_storage.get_session_info(session_id)
    project_name = session_info.project_name if session_info else "project"
    project_name = project_name or "project"

    # Sanitize filename
    safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
    safe_name = safe_name or "project"
    filename = f"{safe_name}.zip"

    # Create ZIP if not exists
    zip_path = temp_storage.get_zip_path(session_id)
    if not zip_path:
        zip_path = temp_storage.create_zip(session_id, project_name)

    if not zip_path or not zip_path.exists():
        raise HTTPException(
            status_code=500,
            detail="Failed to create ZIP file"
        )

    # Schedule cleanup after response is sent
    if cleanup:
        background_tasks.add_task(cleanup_session_delayed, session_id, delay_seconds=5)

    return FileResponse(
        path=str(zip_path),
        filename=filename,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/session/{session_id}/stream")
async def stream_project_zip(
    session_id: str,
    background_tasks: BackgroundTasks
):
    """
    Stream ZIP file for large projects.
    Useful for projects > 100MB.
    """
    if not temp_storage.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )

    session_info = temp_storage.get_session_info(session_id)
    project_name = session_info.project_name if session_info else "project"
    safe_name = "".join(c for c in (project_name or "project") if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_name or 'project'}.zip"

    # Create ZIP
    zip_path = temp_storage.create_zip(session_id, project_name)
    if not zip_path:
        raise HTTPException(status_code=500, detail="Failed to create ZIP")

    async def generate():
        with open(zip_path, "rb") as f:
            while chunk := f.read(8192):  # 8KB chunks
                yield chunk

    # Cleanup after streaming
    background_tasks.add_task(cleanup_session_delayed, session_id, delay_seconds=10)

    return StreamingResponse(
        generate(),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/session/{session_id}/files")
async def list_session_files(session_id: str):
    """
    List all files in session (for UI preview).
    """
    if not temp_storage.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    files = temp_storage.list_files(session_id)
    file_tree = temp_storage.get_file_tree(session_id)
    session_info = temp_storage.get_session_info(session_id)

    return {
        "session_id": session_id,
        "project_name": session_info.project_name if session_info else None,
        "file_count": len(files),
        "files": files,
        "tree": file_tree
    }


@router.get("/session/{session_id}/file/{file_path:path}")
async def get_session_file(session_id: str, file_path: str):
    """
    Get content of a specific file (for editor).
    """
    if not temp_storage.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    content = temp_storage.read_file(session_id, file_path)
    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "path": file_path,
        "content": content
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Manually delete a session (user cancels generation).
    """
    if temp_storage.session_exists(session_id):
        temp_storage.delete_session(session_id)
        return {"message": "Session deleted", "session_id": session_id}

    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/stats")
async def get_storage_stats():
    """
    Get temp storage statistics (admin endpoint).
    """
    return temp_storage.get_stats()


@router.post("/cleanup")
async def trigger_cleanup():
    """
    Manually trigger cleanup of expired sessions (admin endpoint).
    """
    deleted_count = temp_storage.cleanup_expired_sessions()
    return {
        "message": f"Cleaned up {deleted_count} expired sessions",
        "stats": temp_storage.get_stats()
    }


# Helper function for delayed cleanup
async def cleanup_session_delayed(session_id: str, delay_seconds: int = 5):
    """
    Delete session after a delay.
    Gives time for download to complete.
    """
    await asyncio.sleep(delay_seconds)
    try:
        temp_storage.delete_session(session_id)
    except Exception as e:
        # Log but don't fail - cleanup will happen on next cleanup cycle
        print(f"Delayed cleanup failed for {session_id}: {e}")
