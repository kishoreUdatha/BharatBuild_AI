"""
Job Storage Manager - Ephemeral File Storage for Code Generation

PRODUCTION BEST PRACTICE FOR 1,00,000+ STUDENTS:

1. Store files in /tmp/jobs/<job_id>/  (FAST, FREE)
2. ZIP only when complete
3. Upload ZIP to S3 (optional)
4. Auto-delete after 24-48 hours

WHY THIS APPROACH:
┌─────────────────────────────────────────────────────────────┐
│ Storage Method    │ Speed  │ Cost    │ Good for Generation │
├───────────────────┼────────┼─────────┼─────────────────────│
│ Database (Postgres)│ Slow   │ High    │ ❌ NO              │
│ S3/Cloud Storage  │ Slow   │ Medium  │ ❌ NO (1000s writes)│
│ /tmp (Local Disk) │ FAST   │ FREE    │ ✅ YES             │
└─────────────────────────────────────────────────────────────┘

LIFECYCLE:
    User Request → Create /tmp/jobs/<job_id>/
                 → Planner writes plan.json
                 → Writer writes files one by one
                 → Fixer updates broken files
                 → Runner mounts folder into Docker
                 → ZIP created → Optional S3 upload
                 → Auto-delete after 48 hours
"""

import os
import shutil
import zipfile
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import uuid
import aiofiles
import aiofiles.os

from app.core.logging_config import logger

# Configuration
JOBS_BASE_PATH = os.getenv("JOBS_BASE_PATH", "/tmp/jobs")
JOB_EXPIRY_HOURS = int(os.getenv("JOB_EXPIRY_HOURS", "48"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_PROJECT_SIZE_MB = int(os.getenv("MAX_PROJECT_SIZE_MB", "100"))


@dataclass
class JobMetadata:
    """Metadata for a generation job"""
    job_id: str
    user_id: str
    project_name: str
    created_at: datetime
    status: str  # "generating", "complete", "failed", "expired"
    files_count: int = 0
    total_size_bytes: int = 0
    zip_path: Optional[str] = None
    s3_url: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "user_id": self.user_id,
            "project_name": self.project_name,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "files_count": self.files_count,
            "total_size_bytes": self.total_size_bytes,
            "zip_path": self.zip_path,
            "s3_url": self.s3_url,
            "error_message": self.error_message,
        }


class JobStorageManager:
    """
    Manages ephemeral file storage for code generation jobs.

    This is the CORE storage system that makes BharatBuild scale
    to 1,00,000+ students efficiently.

    Key Principles:
    1. Use /tmp for ALL file operations during generation
    2. Never write to database during generation
    3. Never write to S3 during generation
    4. ZIP only when complete
    5. Auto-cleanup after 48 hours
    """

    def __init__(self, base_path: str = JOBS_BASE_PATH):
        """
        Initialize job storage manager.

        Args:
            base_path: Base directory for job storage (default: /tmp/jobs)
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # In-memory job tracking (could use Redis for multi-server)
        self.jobs: Dict[str, JobMetadata] = {}

        logger.info(f"JobStorageManager initialized at {self.base_path}")

    def _get_job_path(self, job_id: str) -> Path:
        """Get the filesystem path for a job"""
        return self.base_path / job_id

    def _get_file_path(self, job_id: str, file_path: str) -> Path:
        """Get the full filesystem path for a file in a job"""
        # Prevent path traversal
        safe_path = Path(file_path).as_posix().lstrip("/")
        if ".." in safe_path:
            raise ValueError("Path traversal detected")
        return self._get_job_path(job_id) / safe_path

    # ==================== JOB LIFECYCLE ====================

    async def create_job(self,
                         user_id: str,
                         project_name: str,
                         job_id: Optional[str] = None) -> str:
        """
        Create a new generation job.

        This is called when user starts a new project generation.

        Args:
            user_id: User who owns the job
            project_name: Name of the project
            job_id: Optional custom job ID

        Returns:
            job_id: Unique identifier for this job
        """
        job_id = job_id or str(uuid.uuid4())[:12]
        job_path = self._get_job_path(job_id)

        # Create job directory
        job_path.mkdir(parents=True, exist_ok=True)

        # Create metadata
        metadata = JobMetadata(
            job_id=job_id,
            user_id=user_id,
            project_name=project_name,
            created_at=datetime.utcnow(),
            status="generating"
        )

        # Store metadata
        self.jobs[job_id] = metadata

        # Write metadata file
        metadata_path = job_path / ".job_metadata.json"
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata.to_dict(), indent=2))

        logger.info(f"Created job {job_id} for user {user_id}")

        return job_id

    async def get_job(self, job_id: str) -> Optional[JobMetadata]:
        """Get job metadata"""
        if job_id in self.jobs:
            return self.jobs[job_id]

        # Try to load from disk
        metadata_path = self._get_job_path(job_id) / ".job_metadata.json"
        if metadata_path.exists():
            async with aiofiles.open(metadata_path, "r") as f:
                data = json.loads(await f.read())
                metadata = JobMetadata(
                    job_id=data["job_id"],
                    user_id=data["user_id"],
                    project_name=data["project_name"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    status=data["status"],
                    files_count=data.get("files_count", 0),
                    total_size_bytes=data.get("total_size_bytes", 0),
                    zip_path=data.get("zip_path"),
                    s3_url=data.get("s3_url"),
                    error_message=data.get("error_message"),
                )
                self.jobs[job_id] = metadata
                return metadata

        return None

    async def update_job_status(self, job_id: str, status: str, error: Optional[str] = None):
        """Update job status"""
        metadata = await self.get_job(job_id)
        if metadata:
            metadata.status = status
            metadata.error_message = error

            # Update metadata file
            metadata_path = self._get_job_path(job_id) / ".job_metadata.json"
            async with aiofiles.open(metadata_path, "w") as f:
                await f.write(json.dumps(metadata.to_dict(), indent=2))

    # ==================== FILE OPERATIONS ====================

    async def write_file(self,
                         job_id: str,
                         file_path: str,
                         content: str) -> bool:
        """
        Write a file to the job directory.

        This is called by Writer Agent for each generated file.
        FAST because it writes directly to /tmp (local disk).

        Args:
            job_id: Job identifier
            file_path: Relative path within project (e.g., "src/App.tsx")
            content: File content

        Returns:
            True if successful
        """
        try:
            full_path = self._get_file_path(job_id, file_path)

            # Check file size
            if len(content.encode("utf-8")) > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"File too large (max {MAX_FILE_SIZE_MB}MB)")

            # Create parent directories
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
                await f.write(content)

            # Update metadata
            if job_id in self.jobs:
                self.jobs[job_id].files_count += 1
                self.jobs[job_id].total_size_bytes += len(content.encode("utf-8"))

            logger.debug(f"Wrote file {file_path} to job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to write file {file_path}: {e}")
            return False

    async def read_file(self, job_id: str, file_path: str) -> Optional[str]:
        """Read a file from the job directory"""
        try:
            full_path = self._get_file_path(job_id, file_path)

            if not full_path.exists():
                return None

            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                return await f.read()

        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    async def delete_file(self, job_id: str, file_path: str) -> bool:
        """Delete a file from the job directory"""
        try:
            full_path = self._get_file_path(job_id, file_path)

            if full_path.exists():
                await aiofiles.os.remove(full_path)
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    async def list_files(self, job_id: str) -> List[Dict[str, Any]]:
        """List all files in the job directory"""
        job_path = self._get_job_path(job_id)
        files = []

        if not job_path.exists():
            return files

        for file_path in job_path.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                relative_path = file_path.relative_to(job_path)
                files.append({
                    "path": str(relative_path),
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                })

        return sorted(files, key=lambda x: x["path"])

    async def write_plan(self, job_id: str, plan: Dict[str, Any]) -> bool:
        """
        Write the generation plan to plan.json

        Called by Planner Agent at the start of generation.
        """
        return await self.write_file(job_id, "plan.json", json.dumps(plan, indent=2))

    async def get_plan(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Read the generation plan"""
        content = await self.read_file(job_id, "plan.json")
        if content:
            return json.loads(content)
        return None

    # ==================== ZIP & EXPORT ====================

    async def create_zip(self, job_id: str) -> Optional[str]:
        """
        Create a ZIP file of the entire project.

        Called AFTER generation is complete.
        This is when we package everything for download.

        Args:
            job_id: Job identifier

        Returns:
            Path to the ZIP file
        """
        job_path = self._get_job_path(job_id)

        if not job_path.exists():
            return None

        zip_path = self.base_path / f"{job_id}.zip"

        try:
            # Create ZIP in a thread to not block
            def create_zip_sync():
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_path in job_path.rglob("*"):
                        if file_path.is_file() and not file_path.name.startswith("."):
                            arcname = file_path.relative_to(job_path)
                            zf.write(file_path, arcname)
                return str(zip_path)

            result = await asyncio.get_event_loop().run_in_executor(
                None, create_zip_sync
            )

            # Update metadata
            if job_id in self.jobs:
                self.jobs[job_id].zip_path = result

            logger.info(f"Created ZIP for job {job_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Failed to create ZIP for job {job_id}: {e}")
            return None

    async def upload_to_s3(self,
                           job_id: str,
                           s3_client,
                           bucket: str,
                           prefix: str = "projects") -> Optional[str]:
        """
        Upload ZIP to S3 (OPTIONAL).

        Only call this if you want permanent storage.
        Most student projects don't need this.

        Args:
            job_id: Job identifier
            s3_client: boto3 S3 client
            bucket: S3 bucket name
            prefix: S3 key prefix

        Returns:
            S3 URL if successful
        """
        metadata = await self.get_job(job_id)
        if not metadata or not metadata.zip_path:
            return None

        try:
            key = f"{prefix}/{job_id}.zip"

            # Upload in thread
            def upload_sync():
                s3_client.upload_file(metadata.zip_path, bucket, key)
                return f"s3://{bucket}/{key}"

            s3_url = await asyncio.get_event_loop().run_in_executor(
                None, upload_sync
            )

            # Update metadata
            metadata.s3_url = s3_url

            logger.info(f"Uploaded job {job_id} to S3: {s3_url}")
            return s3_url

        except Exception as e:
            logger.error(f"Failed to upload to S3: {e}")
            return None

    # ==================== CLEANUP ====================

    async def delete_job(self, job_id: str, keep_zip: bool = False) -> bool:
        """
        Delete a job and all its files.

        Args:
            job_id: Job identifier
            keep_zip: If True, keep the ZIP file

        Returns:
            True if successful
        """
        try:
            job_path = self._get_job_path(job_id)
            zip_path = self.base_path / f"{job_id}.zip"

            # Delete job directory
            if job_path.exists():
                shutil.rmtree(job_path)

            # Delete ZIP unless keeping it
            if not keep_zip and zip_path.exists():
                zip_path.unlink()

            # Remove from memory
            if job_id in self.jobs:
                del self.jobs[job_id]

            logger.info(f"Deleted job {job_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            return False

    async def cleanup_expired_jobs(self) -> int:
        """
        Delete jobs older than JOB_EXPIRY_HOURS.

        This should be called periodically (e.g., every hour).
        Keeps storage costs at ZERO.

        Returns:
            Number of jobs cleaned up
        """
        cleaned = 0
        expiry_time = datetime.utcnow() - timedelta(hours=JOB_EXPIRY_HOURS)

        # Check all job directories
        for job_dir in self.base_path.iterdir():
            if not job_dir.is_dir():
                continue

            job_id = job_dir.name
            metadata = await self.get_job(job_id)

            if metadata and metadata.created_at < expiry_time:
                logger.info(f"Cleaning up expired job {job_id} (created {metadata.created_at})")
                await self.delete_job(job_id)
                cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} expired jobs")

        return cleaned

    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_size = 0
        job_count = 0
        file_count = 0

        for job_dir in self.base_path.iterdir():
            if job_dir.is_dir():
                job_count += 1
                for file_path in job_dir.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        total_size += file_path.stat().st_size

        return {
            "base_path": str(self.base_path),
            "job_count": job_count,
            "file_count": file_count,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "expiry_hours": JOB_EXPIRY_HOURS,
        }


# ==================== SINGLETON & BACKGROUND TASK ====================

_storage_manager: Optional[JobStorageManager] = None


def get_job_storage() -> JobStorageManager:
    """Get the global job storage manager"""
    global _storage_manager

    if _storage_manager is None:
        _storage_manager = JobStorageManager()

    return _storage_manager


async def cleanup_loop():
    """
    Background task to clean up expired jobs.

    Run this in FastAPI startup:
        asyncio.create_task(cleanup_loop())
    """
    storage = get_job_storage()

    while True:
        try:
            cleaned = await storage.cleanup_expired_jobs()
            if cleaned > 0:
                logger.info(f"Cleanup loop: removed {cleaned} expired jobs")
        except Exception as e:
            logger.error(f"Cleanup loop error: {e}")

        # Run every hour
        await asyncio.sleep(3600)
