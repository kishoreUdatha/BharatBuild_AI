"""
Storage Module - Ephemeral Job Storage

Best practice for 1,00,000+ students:
- Store files in /tmp/jobs/<job_id>/ during generation
- ZIP only when complete
- Auto-delete after 48 hours
- ZERO cloud storage cost during generation
"""

from .job_storage import (
    JobStorageManager,
    JobMetadata,
    get_job_storage,
    cleanup_loop,
    JOBS_BASE_PATH,
    JOB_EXPIRY_HOURS,
)

__all__ = [
    "JobStorageManager",
    "JobMetadata",
    "get_job_storage",
    "cleanup_loop",
    "JOBS_BASE_PATH",
    "JOB_EXPIRY_HOURS",
]
