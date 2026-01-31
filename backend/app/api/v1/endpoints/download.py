"""
Download Endpoint - ZIP download with immediate cleanup

Flow:
1. User generates project → files stored in temp session
2. User clicks "Download ZIP"
3. Server creates ZIP → streams to user
4. Server DELETES session immediately after download

Zero permanent storage!

Mobile Support:
- APK download for Flutter/Android projects
- IPA download for iOS projects (when available)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional, List
from pathlib import Path
import os
import asyncio
import glob

from app.services.temp_session_storage import temp_storage
from app.core.logging_config import logger

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


# =============================================================================
# MOBILE APP DOWNLOADS (APK, IPA)
# =============================================================================

def find_apk_files(session_path: Path) -> List[Path]:
    """
    Find APK files in a Flutter/Android project.

    Common APK locations:
    - build/app/outputs/flutter-apk/app-debug.apk
    - build/app/outputs/flutter-apk/app-release.apk
    - build/app/outputs/apk/debug/app-debug.apk
    - build/app/outputs/apk/release/app-release.apk
    - app/build/outputs/apk/debug/app-debug.apk (Android native)
    """
    apk_patterns = [
        "**/build/app/outputs/flutter-apk/*.apk",
        "**/build/app/outputs/apk/**/*.apk",
        "**/app/build/outputs/apk/**/*.apk",
        "**/build/outputs/apk/**/*.apk",
        "**/*.apk",
    ]

    apk_files = []
    for pattern in apk_patterns:
        found = list(session_path.glob(pattern))
        apk_files.extend(found)

    # Remove duplicates and sort (release first, then debug)
    unique_apks = list(set(apk_files))
    unique_apks.sort(key=lambda x: (
        0 if 'release' in x.name.lower() else 1,
        x.stat().st_mtime if x.exists() else 0
    ), reverse=True)

    return unique_apks


@router.get("/session/{session_id}/apk")
async def download_apk(
    session_id: str,
    build_type: str = "release",  # "release" or "debug"
):
    """
    Download APK file for Flutter/Android project.

    Args:
        session_id: The project session ID
        build_type: "release" or "debug" (default: release)

    Returns:
        APK file download
    """
    if not temp_storage.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please regenerate the project."
        )

    session_info = temp_storage.get_session_info(session_id)
    session_path = temp_storage.get_session_path(session_id)

    if not session_path or not session_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Project files not found"
        )

    # Find APK files
    apk_files = find_apk_files(session_path)

    if not apk_files:
        raise HTTPException(
            status_code=404,
            detail="No APK file found. Make sure the Flutter/Android project was built successfully. "
                   "The project needs to run 'flutter build apk' first."
        )

    # Filter by build type preference
    preferred_apk = None
    for apk in apk_files:
        apk_name = apk.name.lower()
        if build_type == "release" and "release" in apk_name:
            preferred_apk = apk
            break
        elif build_type == "debug" and "debug" in apk_name:
            preferred_apk = apk
            break

    # Fallback to first available APK
    if not preferred_apk:
        preferred_apk = apk_files[0]
        logger.warning(f"[APK Download] Requested {build_type} but not found, using {preferred_apk.name}")

    # Generate download filename
    project_name = session_info.project_name if session_info else "app"
    safe_name = "".join(c for c in (project_name or "app") if c.isalnum() or c in ('-', '_')).strip()
    filename = f"{safe_name or 'app'}-{build_type}.apk"

    logger.info(f"[APK Download] Serving {preferred_apk} as {filename}")

    return FileResponse(
        path=str(preferred_apk),
        filename=filename,
        media_type="application/vnd.android.package-archive",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/session/{session_id}/apk/info")
async def get_apk_info(session_id: str):
    """
    Get information about available APK files in the project.

    Returns:
        List of available APK files with metadata
    """
    if not temp_storage.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )

    session_path = temp_storage.get_session_path(session_id)
    session_info = temp_storage.get_session_info(session_id)

    if not session_path or not session_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Project files not found"
        )

    # Check if this is a Flutter project
    pubspec_path = session_path / "pubspec.yaml"
    build_gradle = session_path / "android" / "app" / "build.gradle"
    is_flutter = pubspec_path.exists()
    is_android = build_gradle.exists() or (session_path / "app" / "build.gradle").exists()

    # Find APK files
    apk_files = find_apk_files(session_path)

    apk_info = []
    for apk in apk_files:
        try:
            stat = apk.stat()
            apk_info.append({
                "filename": apk.name,
                "path": str(apk.relative_to(session_path)),
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "build_type": "release" if "release" in apk.name.lower() else "debug",
                "created_at": stat.st_mtime,
            })
        except Exception as e:
            logger.warning(f"[APK Info] Error getting info for {apk}: {e}")

    return {
        "session_id": session_id,
        "project_name": session_info.project_name if session_info else None,
        "is_flutter_project": is_flutter,
        "is_android_project": is_android,
        "apk_available": len(apk_info) > 0,
        "apk_count": len(apk_info),
        "apk_files": apk_info,
        "download_url": f"/api/v1/download/session/{session_id}/apk" if apk_info else None,
        "build_instructions": {
            "flutter": "Run 'flutter build apk --release' to generate APK",
            "android": "Run './gradlew assembleRelease' to generate APK"
        } if not apk_info else None
    }


@router.post("/session/{session_id}/build-apk")
async def trigger_apk_build(
    session_id: str,
    background_tasks: BackgroundTasks,
    build_type: str = "debug",  # "release" or "debug"
):
    """
    Trigger APK build for a Flutter project.

    This endpoint initiates the Flutter APK build process.
    The build runs in the background and the APK will be available
    at the /apk endpoint once complete.

    Args:
        session_id: The project session ID
        build_type: "release" or "debug" (default: debug for faster builds)

    Returns:
        Build status and estimated time
    """
    if not temp_storage.session_exists(session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired"
        )

    session_path = temp_storage.get_session_path(session_id)

    if not session_path or not session_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Project files not found"
        )

    # Verify this is a Flutter project
    pubspec_path = session_path / "pubspec.yaml"
    if not pubspec_path.exists():
        raise HTTPException(
            status_code=400,
            detail="Not a Flutter project. pubspec.yaml not found."
        )

    # Check if APK already exists
    existing_apks = find_apk_files(session_path)
    if existing_apks:
        return {
            "status": "already_built",
            "message": "APK already exists",
            "apk_count": len(existing_apks),
            "download_url": f"/api/v1/download/session/{session_id}/apk"
        }

    # For now, return instructions since build would require Docker execution
    # In production, this would trigger the Docker build process
    return {
        "status": "build_required",
        "message": "APK build needs to be triggered through project execution",
        "instructions": [
            "1. The APK is built automatically when you run the project",
            "2. Use the 'Run' button in the project editor",
            "3. Once the build completes, the APK will be available for download",
            "4. For manual build: 'flutter build apk --" + build_type + "'"
        ],
        "build_type": build_type,
        "estimated_time": "2-5 minutes for debug, 5-10 minutes for release"
    }
