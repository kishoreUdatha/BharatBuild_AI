"""
Checkpoint Service - Handles workflow state persistence and recovery

This service enables:
1. Saving workflow progress at each step
2. Resuming from last successful checkpoint on disconnect
3. Recovering partial file generation
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from uuid import UUID
from pathlib import Path
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.core.logging_config import logger


class CheckpointStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class WorkflowStep(str, Enum):
    PLANNING = "planning"
    ANALYZING = "analyzing"
    GENERATING_BACKEND = "generating_backend"
    GENERATING_FRONTEND = "generating_frontend"
    GENERATING_CONFIG = "generating_config"
    FINALIZING = "finalizing"


class CheckpointService:
    """
    Manages workflow checkpoints for resilient project generation.

    Features:
    - Saves state after each successful step
    - Tracks generated files
    - Enables resume from last checkpoint
    - Auto-cleanup of old checkpoints
    """

    def __init__(self, checkpoint_dir: str = "./checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._active_checkpoints: Dict[str, Dict] = {}

    def _get_checkpoint_path(self, project_id: str) -> Path:
        """Get checkpoint file path for a project"""
        return self.checkpoint_dir / f"{project_id}.checkpoint.json"

    async def create_checkpoint(
        self,
        project_id: str,
        user_id: str,
        workflow_type: str,
        initial_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a new checkpoint for a workflow.

        Args:
            project_id: Unique project identifier
            user_id: User who owns this project
            workflow_type: Type of workflow (e.g., "project_generation")
            initial_request: Original user request data

        Returns:
            Checkpoint data
        """
        checkpoint = {
            "id": project_id,
            "user_id": user_id,
            "workflow_type": workflow_type,
            "status": CheckpointStatus.PENDING,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "current_step": None,
            "completed_steps": [],
            "failed_step": None,
            "error_message": None,
            "initial_request": initial_request,
            "generated_files": [],
            "pending_files": [],
            "context": {},
            "retry_count": 0,
            "max_retries": 3,
            "can_resume": True
        }

        # Save to file
        await self._save_checkpoint(project_id, checkpoint)

        # Keep in memory for fast access
        self._active_checkpoints[project_id] = checkpoint

        logger.info(f"[Checkpoint] Created checkpoint for project {project_id}")
        return checkpoint

    async def update_step(
        self,
        project_id: str,
        step: str,
        status: CheckpointStatus,
        context: Optional[Dict] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update checkpoint with step progress.

        Args:
            project_id: Project identifier
            step: Current workflow step
            status: Step status
            context: Additional context data
            error: Error message if failed
        """
        checkpoint = await self.get_checkpoint(project_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint not found for project {project_id}")

        checkpoint["updated_at"] = datetime.utcnow().isoformat()
        checkpoint["current_step"] = step
        checkpoint["status"] = status

        if status == CheckpointStatus.COMPLETED:
            if step not in checkpoint["completed_steps"]:
                checkpoint["completed_steps"].append(step)
        elif status == CheckpointStatus.FAILED:
            checkpoint["failed_step"] = step
            checkpoint["error_message"] = error
            checkpoint["can_resume"] = checkpoint["retry_count"] < checkpoint["max_retries"]
        elif status == CheckpointStatus.INTERRUPTED:
            checkpoint["can_resume"] = True

        if context:
            checkpoint["context"].update(context)

        await self._save_checkpoint(project_id, checkpoint)
        self._active_checkpoints[project_id] = checkpoint

        logger.info(f"[Checkpoint] Updated step '{step}' to '{status}' for project {project_id}")
        return checkpoint

    async def add_generated_file(
        self,
        project_id: str,
        file_path: str,
        file_type: str,
        size_bytes: int
    ) -> None:
        """
        Track a successfully generated file.

        Args:
            project_id: Project identifier
            file_path: Path of generated file
            file_type: Type of file (e.g., "backend", "frontend")
            size_bytes: File size
        """
        checkpoint = await self.get_checkpoint(project_id)
        if not checkpoint:
            return

        file_entry = {
            "path": file_path,
            "type": file_type,
            "size_bytes": size_bytes,
            "generated_at": datetime.utcnow().isoformat()
        }

        # Remove from pending if exists
        checkpoint["pending_files"] = [
            f for f in checkpoint["pending_files"]
            if f.get("path") != file_path
        ]

        # Add to generated
        checkpoint["generated_files"].append(file_entry)
        checkpoint["updated_at"] = datetime.utcnow().isoformat()

        await self._save_checkpoint(project_id, checkpoint)
        self._active_checkpoints[project_id] = checkpoint

    async def add_pending_files(
        self,
        project_id: str,
        files: List[Dict[str, str]]
    ) -> None:
        """
        Add files that are planned to be generated.

        Args:
            project_id: Project identifier
            files: List of file info dicts with 'path' and 'type'
        """
        checkpoint = await self.get_checkpoint(project_id)
        if not checkpoint:
            return

        checkpoint["pending_files"].extend(files)
        checkpoint["updated_at"] = datetime.utcnow().isoformat()

        await self._save_checkpoint(project_id, checkpoint)
        self._active_checkpoints[project_id] = checkpoint

    async def get_checkpoint(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get checkpoint for a project.

        Args:
            project_id: Project identifier

        Returns:
            Checkpoint data or None
        """
        # Check memory first
        if project_id in self._active_checkpoints:
            return self._active_checkpoints[project_id]

        # Load from file
        checkpoint_path = self._get_checkpoint_path(project_id)
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, 'r') as f:
                    checkpoint = json.load(f)
                self._active_checkpoints[project_id] = checkpoint
                return checkpoint
            except Exception as e:
                logger.error(f"[Checkpoint] Failed to load checkpoint: {e}")

        return None

    async def can_resume(self, project_id: str) -> bool:
        """Check if a project can be resumed"""
        checkpoint = await self.get_checkpoint(project_id)
        if not checkpoint:
            return False

        return (
            checkpoint.get("can_resume", False) and
            checkpoint.get("status") in [
                CheckpointStatus.INTERRUPTED,
                CheckpointStatus.FAILED,
                CheckpointStatus.IN_PROGRESS
            ] and
            checkpoint.get("retry_count", 0) < checkpoint.get("max_retries", 3)
        )

    async def get_resume_point(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information needed to resume a workflow.

        Returns:
            Dict with resume information or None
        """
        checkpoint = await self.get_checkpoint(project_id)
        if not checkpoint or not await self.can_resume(project_id):
            return None

        completed_steps = checkpoint.get("completed_steps", [])
        all_steps = [step.value for step in WorkflowStep]

        # Find next step to execute
        next_step = None
        for step in all_steps:
            if step not in completed_steps:
                next_step = step
                break

        # Get files that still need to be generated
        generated_paths = {f["path"] for f in checkpoint.get("generated_files", [])}
        remaining_files = [
            f for f in checkpoint.get("pending_files", [])
            if f.get("path") not in generated_paths
        ]

        return {
            "project_id": project_id,
            "next_step": next_step,
            "completed_steps": completed_steps,
            "remaining_files": remaining_files,
            "context": checkpoint.get("context", {}),
            "initial_request": checkpoint.get("initial_request", {}),
            "generated_files_count": len(checkpoint.get("generated_files", [])),
            "retry_count": checkpoint.get("retry_count", 0)
        }

    async def mark_resumed(self, project_id: str) -> None:
        """Mark checkpoint as being resumed"""
        checkpoint = await self.get_checkpoint(project_id)
        if checkpoint:
            checkpoint["retry_count"] = checkpoint.get("retry_count", 0) + 1
            checkpoint["status"] = CheckpointStatus.IN_PROGRESS
            checkpoint["updated_at"] = datetime.utcnow().isoformat()
            await self._save_checkpoint(project_id, checkpoint)
            self._active_checkpoints[project_id] = checkpoint
            logger.info(f"[Checkpoint] Marked project {project_id} as resumed (attempt {checkpoint['retry_count']})")

    async def mark_completed(self, project_id: str) -> None:
        """Mark workflow as completed"""
        checkpoint = await self.get_checkpoint(project_id)
        if checkpoint:
            checkpoint["status"] = CheckpointStatus.COMPLETED
            checkpoint["updated_at"] = datetime.utcnow().isoformat()
            checkpoint["can_resume"] = False
            await self._save_checkpoint(project_id, checkpoint)
            self._active_checkpoints[project_id] = checkpoint
            logger.info(f"[Checkpoint] Marked project {project_id} as completed")

    async def mark_interrupted(self, project_id: str, reason: str = "Connection lost") -> None:
        """Mark workflow as interrupted (can be resumed)"""
        checkpoint = await self.get_checkpoint(project_id)
        if checkpoint:
            checkpoint["status"] = CheckpointStatus.INTERRUPTED
            checkpoint["error_message"] = reason
            checkpoint["updated_at"] = datetime.utcnow().isoformat()
            checkpoint["can_resume"] = True
            await self._save_checkpoint(project_id, checkpoint)
            self._active_checkpoints[project_id] = checkpoint
            logger.info(f"[Checkpoint] Marked project {project_id} as interrupted: {reason}")

    async def delete_checkpoint(self, project_id: str) -> None:
        """Delete checkpoint for a project"""
        checkpoint_path = self._get_checkpoint_path(project_id)
        if checkpoint_path.exists():
            checkpoint_path.unlink()

        if project_id in self._active_checkpoints:
            del self._active_checkpoints[project_id]

        logger.info(f"[Checkpoint] Deleted checkpoint for project {project_id}")

    async def cleanup_old_checkpoints(self, max_age_hours: int = 24) -> int:
        """
        Clean up checkpoints older than max_age_hours.

        Returns:
            Number of checkpoints deleted
        """
        deleted = 0
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        for checkpoint_file in self.checkpoint_dir.glob("*.checkpoint.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)

                updated_at = datetime.fromisoformat(checkpoint.get("updated_at", ""))

                if updated_at < cutoff:
                    checkpoint_file.unlink()
                    deleted += 1
            except Exception as e:
                logger.warning(f"[Checkpoint] Error cleaning up {checkpoint_file}: {e}")

        logger.info(f"[Checkpoint] Cleaned up {deleted} old checkpoints")
        return deleted

    async def get_user_checkpoints(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all checkpoints for a user"""
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("*.checkpoint.json"):
            try:
                with open(checkpoint_file, 'r') as f:
                    checkpoint = json.load(f)

                if checkpoint.get("user_id") == user_id:
                    checkpoints.append({
                        "id": checkpoint.get("id"),
                        "status": checkpoint.get("status"),
                        "current_step": checkpoint.get("current_step"),
                        "can_resume": checkpoint.get("can_resume"),
                        "created_at": checkpoint.get("created_at"),
                        "updated_at": checkpoint.get("updated_at"),
                        "generated_files_count": len(checkpoint.get("generated_files", [])),
                        "error_message": checkpoint.get("error_message")
                    })
            except Exception:
                continue

        return sorted(checkpoints, key=lambda x: x.get("updated_at", ""), reverse=True)

    async def _save_checkpoint(self, project_id: str, checkpoint: Dict) -> None:
        """Save checkpoint to file"""
        checkpoint_path = self._get_checkpoint_path(project_id)
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)


# Global instance
checkpoint_service = CheckpointService()
