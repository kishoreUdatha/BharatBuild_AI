"""
Jobs API - Manage Generation Jobs and Downloads

Endpoints for:
- Creating generation jobs
- Writing files during generation
- Creating ZIP downloads
- Cleanup management
"""

import asyncio
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.modules.storage import (
    get_job_storage,
    JobMetadata,
)
from app.core.logging_config import logger

router = APIRouter(prefix="/jobs", tags=["Job Storage"])


# Request/Response Models

class CreateJobRequest(BaseModel):
    """Request to create a new job"""
    project_name: str = Field(..., description="Name of the project")
    job_id: Optional[str] = Field(None, description="Optional custom job ID")


class WriteFileRequest(BaseModel):
    """Request to write a file"""
    path: str = Field(..., description="Relative file path")
    content: str = Field(..., description="File content")


class WritePlanRequest(BaseModel):
    """Request to write generation plan"""
    tasks: List[dict] = Field(..., description="List of generation tasks")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class JobResponse(BaseModel):
    """Job information response"""
    job_id: str
    user_id: str
    project_name: str
    status: str
    files_count: int
    total_size_mb: float
    created_at: str
    zip_ready: bool
    download_url: Optional[str]


# Helper to get user_id from request
async def get_current_user_id(request: Request) -> str:
    """Extract user ID from request"""
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return user_id

    # Check auth token (implement based on your auth)
    auth_header = request.headers.get("Authorization")
    if auth_header:
        # Decode JWT and get user_id
        pass

    return "anonymous"


# Endpoints

@router.post("/create", response_model=JobResponse)
async def create_job(
    request_data: CreateJobRequest,
    request: Request,
):
    """
    Create a new generation job.

    Called when user starts a new project generation.
    Creates /tmp/jobs/<job_id>/ directory for file storage.
    """
    storage = get_job_storage()
    user_id = await get_current_user_id(request)

    job_id = await storage.create_job(
        user_id=user_id,
        project_name=request_data.project_name,
        job_id=request_data.job_id,
    )

    metadata = await storage.get_job(job_id)

    return JobResponse(
        job_id=job_id,
        user_id=user_id,
        project_name=request_data.project_name,
        status="generating",
        files_count=0,
        total_size_mb=0,
        created_at=metadata.created_at.isoformat(),
        zip_ready=False,
        download_url=None,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get job information and status.
    """
    storage = get_job_storage()
    metadata = await storage.get_job(job_id)

    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        job_id=metadata.job_id,
        user_id=metadata.user_id,
        project_name=metadata.project_name,
        status=metadata.status,
        files_count=metadata.files_count,
        total_size_mb=round(metadata.total_size_bytes / 1024 / 1024, 2),
        created_at=metadata.created_at.isoformat(),
        zip_ready=metadata.zip_path is not None,
        download_url=f"/api/v1/jobs/{job_id}/download" if metadata.zip_path else None,
    )


@router.post("/{job_id}/files")
async def write_file(
    job_id: str,
    request_data: WriteFileRequest,
):
    """
    Write a file to the job directory.

    Called by Writer Agent for each generated file.
    Files are stored in /tmp/jobs/<job_id>/<path>
    """
    storage = get_job_storage()

    # Check job exists
    metadata = await storage.get_job(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    if metadata.status != "generating":
        raise HTTPException(status_code=400, detail="Job is not in generating state")

    success = await storage.write_file(
        job_id=job_id,
        file_path=request_data.path,
        content=request_data.content,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to write file")

    return {
        "success": True,
        "path": request_data.path,
        "size": len(request_data.content),
    }


@router.post("/{job_id}/files/batch")
async def write_files_batch(
    job_id: str,
    files: List[WriteFileRequest],
):
    """
    Write multiple files at once.

    More efficient for bulk file generation.
    """
    storage = get_job_storage()

    # Check job exists
    metadata = await storage.get_job(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    results = []
    for file in files:
        success = await storage.write_file(job_id, file.path, file.content)
        results.append({
            "path": file.path,
            "success": success,
        })

    return {
        "total": len(files),
        "success": sum(1 for r in results if r["success"]),
        "results": results,
    }


@router.post("/{job_id}/plan")
async def write_plan(
    job_id: str,
    request_data: WritePlanRequest,
):
    """
    Write the generation plan.

    Called by Planner Agent at the start of generation.
    Stores plan.json in the job directory.
    """
    storage = get_job_storage()

    plan_data = {
        "tasks": request_data.tasks,
        "metadata": request_data.metadata,
    }

    success = await storage.write_plan(job_id, plan_data)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to write plan")

    return {"success": True}


@router.get("/{job_id}/files")
async def list_files(job_id: str):
    """
    List all files in the job directory.
    """
    storage = get_job_storage()

    files = await storage.list_files(job_id)

    return {
        "job_id": job_id,
        "files": files,
        "count": len(files),
    }


@router.get("/{job_id}/files/{file_path:path}")
async def read_file(job_id: str, file_path: str):
    """
    Read a specific file from the job directory.
    """
    storage = get_job_storage()

    content = await storage.read_file(job_id, file_path)

    if content is None:
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "path": file_path,
        "content": content,
    }


@router.post("/{job_id}/complete")
async def complete_job(
    job_id: str,
    background_tasks: BackgroundTasks,
):
    """
    Mark job as complete and create ZIP.

    Called when all files have been generated.
    Creates a downloadable ZIP file.
    """
    storage = get_job_storage()

    metadata = await storage.get_job(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    # Update status
    await storage.update_job_status(job_id, "complete")

    # Create ZIP in background
    async def create_zip_async():
        await storage.create_zip(job_id)

    background_tasks.add_task(create_zip_async)

    return {
        "success": True,
        "status": "complete",
        "message": "ZIP creation started",
        "download_url": f"/api/v1/jobs/{job_id}/download",
    }


@router.get("/{job_id}/download")
async def download_zip(job_id: str):
    """
    Download the project as a ZIP file.

    Only available after job is complete.
    """
    storage = get_job_storage()

    metadata = await storage.get_job(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Job not found")

    # Create ZIP if not exists
    if not metadata.zip_path:
        zip_path = await storage.create_zip(job_id)
        if not zip_path:
            raise HTTPException(status_code=500, detail="Failed to create ZIP")
        metadata.zip_path = zip_path

    # Check file exists
    from pathlib import Path
    if not Path(metadata.zip_path).exists():
        raise HTTPException(status_code=404, detail="ZIP file not found")

    return FileResponse(
        path=metadata.zip_path,
        filename=f"{metadata.project_name}.zip",
        media_type="application/zip",
    )


@router.post("/{job_id}/fail")
async def fail_job(
    job_id: str,
    error_message: str = "Generation failed",
):
    """
    Mark job as failed.

    Called when generation encounters an error.
    """
    storage = get_job_storage()

    await storage.update_job_status(job_id, "failed", error_message)

    return {
        "success": True,
        "status": "failed",
    }


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    keep_zip: bool = False,
):
    """
    Delete a job and all its files.

    Usually called automatically after 48 hours.
    """
    storage = get_job_storage()

    success = await storage.delete_job(job_id, keep_zip)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete job")

    return {
        "success": True,
        "message": f"Job {job_id} deleted",
    }


# Admin endpoints

@router.get("/admin/stats")
async def get_storage_stats():
    """
    Get storage statistics.

    Admin endpoint to monitor storage usage.
    """
    storage = get_job_storage()
    return await storage.get_storage_stats()


@router.post("/admin/cleanup")
async def trigger_cleanup():
    """
    Manually trigger cleanup of expired jobs.

    Admin endpoint for manual cleanup.
    """
    storage = get_job_storage()
    cleaned = await storage.cleanup_expired_jobs()

    return {
        "success": True,
        "cleaned_jobs": cleaned,
    }
