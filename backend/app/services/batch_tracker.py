"""
Batch Tracker - Track batch fix attempts to prevent duplicate processing

Features:
1. Track which file combinations have been attempted
2. Prevent same batch from repeating in same session
3. Track success/failure per batch
4. Support multi-pass fixing for large error sets
"""

from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import hashlib

from app.core.logging_config import logger


@dataclass
class BatchAttempt:
    """Single batch fix attempt"""
    batch_hash: str
    files: List[str]
    attempt_time: datetime
    success: bool = False
    files_fixed: List[str] = field(default_factory=list)
    error_count_before: int = 0
    error_count_after: int = 0


@dataclass
class ProjectBatchState:
    """Batch tracking state for a project"""
    project_id: str
    batches: Dict[str, BatchAttempt] = field(default_factory=dict)
    current_pass: int = 1
    total_files_fixed: int = 0
    files_attempted: Set[str] = field(default_factory=set)
    session_start: datetime = field(default_factory=datetime.utcnow)


class BatchTracker:
    """
    Tracks batch fix attempts to prevent duplicate processing.

    Supports multi-pass fixing:
    - Pass 1: Fix first batch of 6 files
    - Pass 2: Fix next batch (excluding already fixed files)
    - Pass N: Continue until all errors fixed or max passes reached
    """

    MAX_PASSES = 5  # Maximum fix passes per session
    MAX_BATCH_ATTEMPTS = 2  # Max attempts per unique batch
    SESSION_TIMEOUT = timedelta(minutes=30)

    def __init__(self):
        self._projects: Dict[str, ProjectBatchState] = {}
        self._lock = threading.Lock()

    def get_next_batch(
        self,
        project_id: str,
        all_error_files: List[Tuple[str, int]],
        batch_size: int = 6
    ) -> Tuple[List[Tuple[str, int]], int]:
        """
        Get next batch of files to fix, excluding already attempted files.

        Args:
            project_id: Project ID
            all_error_files: List of (file_path, line_number) tuples
            batch_size: Maximum files per batch

        Returns:
            Tuple of (batch_files, current_pass_number)
        """
        with self._lock:
            state = self._get_or_create_state(project_id)

            # Check session timeout
            if datetime.utcnow() - state.session_start > self.SESSION_TIMEOUT:
                logger.info(f"[BatchTracker:{project_id}] Session expired, resetting")
                self._projects[project_id] = ProjectBatchState(project_id=project_id)
                state = self._projects[project_id]

            # Check max passes
            if state.current_pass > self.MAX_PASSES:
                logger.warning(f"[BatchTracker:{project_id}] Max passes reached ({self.MAX_PASSES})")
                return [], state.current_pass

            # Filter out already fixed files
            remaining_files = [
                (f, line) for f, line in all_error_files
                if f not in state.files_attempted or self._should_retry_file(state, f)
            ]

            if not remaining_files:
                logger.info(f"[BatchTracker:{project_id}] No remaining files to fix")
                return [], state.current_pass

            # Take next batch
            batch = remaining_files[:batch_size]

            # Check if this exact batch was already attempted
            batch_hash = self._hash_batch([f for f, _ in batch])
            if batch_hash in state.batches:
                attempt = state.batches[batch_hash]
                if attempt.success or len([b for b in state.batches.values() if b.batch_hash == batch_hash]) >= self.MAX_BATCH_ATTEMPTS:
                    # Try different files or advance pass
                    batch = remaining_files[batch_size:batch_size*2] if len(remaining_files) > batch_size else []
                    if not batch:
                        state.current_pass += 1
                        logger.info(f"[BatchTracker:{project_id}] Advancing to pass {state.current_pass}")

            logger.info(
                f"[BatchTracker:{project_id}] Pass {state.current_pass}: "
                f"Returning batch of {len(batch)} files from {len(all_error_files)} total errors"
            )

            return batch, state.current_pass

    def can_attempt_batch(
        self,
        project_id: str,
        files: List[str]
    ) -> Tuple[bool, str]:
        """
        Check if a batch can be attempted.

        Args:
            project_id: Project ID
            files: List of file paths in the batch

        Returns:
            Tuple of (can_attempt, reason)
        """
        with self._lock:
            state = self._get_or_create_state(project_id)

            # Check max passes
            if state.current_pass > self.MAX_PASSES:
                return False, f"Max passes reached ({self.MAX_PASSES})"

            # Check if batch was already successful
            batch_hash = self._hash_batch(files)
            if batch_hash in state.batches:
                attempt = state.batches[batch_hash]
                if attempt.success:
                    return False, "Batch already fixed successfully"

                # Count attempts for this batch
                attempt_count = sum(1 for b in state.batches.values() if b.batch_hash == batch_hash)
                if attempt_count >= self.MAX_BATCH_ATTEMPTS:
                    return False, f"Batch already attempted {self.MAX_BATCH_ATTEMPTS} times"

            return True, "Batch can be attempted"

    def record_batch_attempt(
        self,
        project_id: str,
        files: List[str],
        success: bool,
        files_fixed: List[str] = None,
        error_count_before: int = 0,
        error_count_after: int = 0
    ) -> None:
        """
        Record a batch fix attempt.

        Args:
            project_id: Project ID
            files: List of file paths in the batch
            success: Whether fix was successful
            files_fixed: List of files actually fixed
            error_count_before: Error count before fix
            error_count_after: Error count after fix
        """
        with self._lock:
            state = self._get_or_create_state(project_id)

            batch_hash = self._hash_batch(files)
            attempt = BatchAttempt(
                batch_hash=batch_hash,
                files=files,
                attempt_time=datetime.utcnow(),
                success=success,
                files_fixed=files_fixed or [],
                error_count_before=error_count_before,
                error_count_after=error_count_after
            )

            state.batches[batch_hash] = attempt
            state.files_attempted.update(files)

            if files_fixed:
                state.total_files_fixed += len(files_fixed)

            # Advance pass if batch was successful or all files attempted
            if success and error_count_after > 0:
                state.current_pass += 1
                logger.info(f"[BatchTracker:{project_id}] Batch succeeded, advancing to pass {state.current_pass}")

            logger.info(
                f"[BatchTracker:{project_id}] Recorded batch attempt: "
                f"files={len(files)}, success={success}, fixed={len(files_fixed or [])}, "
                f"errors_before={error_count_before}, errors_after={error_count_after}"
            )

    def get_fix_progress(self, project_id: str) -> Dict:
        """Get batch fix progress for a project"""
        with self._lock:
            state = self._projects.get(project_id)
            if not state:
                return {
                    "current_pass": 1,
                    "total_batches": 0,
                    "total_files_fixed": 0,
                    "files_attempted": 0,
                    "session_age_seconds": 0
                }

            return {
                "current_pass": state.current_pass,
                "total_batches": len(state.batches),
                "total_files_fixed": state.total_files_fixed,
                "files_attempted": len(state.files_attempted),
                "session_age_seconds": (datetime.utcnow() - state.session_start).total_seconds(),
                "successful_batches": sum(1 for b in state.batches.values() if b.success),
                "remaining_passes": max(0, self.MAX_PASSES - state.current_pass)
            }

    def reset_session(self, project_id: str) -> None:
        """Reset batch tracking for a project"""
        with self._lock:
            if project_id in self._projects:
                del self._projects[project_id]
            logger.info(f"[BatchTracker:{project_id}] Session reset")

    def _get_or_create_state(self, project_id: str) -> ProjectBatchState:
        """Get or create project batch state"""
        if project_id not in self._projects:
            self._projects[project_id] = ProjectBatchState(project_id=project_id)
        return self._projects[project_id]

    def _hash_batch(self, files: List[str]) -> str:
        """Create hash for a batch of files"""
        sorted_files = sorted(files)
        content = "|".join(sorted_files)
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def _should_retry_file(self, state: ProjectBatchState, file_path: str) -> bool:
        """Check if a file should be retried (failed in previous batch)"""
        for batch in state.batches.values():
            if file_path in batch.files and not batch.success:
                # File was in a failed batch, allow retry
                return True
            if file_path in batch.files_fixed:
                # File was already fixed, don't retry
                return False
        return False


# Singleton instance
batch_tracker = BatchTracker()
