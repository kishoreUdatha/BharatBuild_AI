"""
Ephemeral Database Cleanup Service

Strategy (like Bolt.new):
- Create database when user runs project
- Track last activity time
- Delete after 30 minutes of inactivity
- Paid users can "save" to keep permanently

Cost Impact:
- Without cleanup: 100K users = $1,500-3,000/month
- With cleanup: 100K users = $25-100/month (only ~2% active at any time)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProjectTier(Enum):
    FREE = "free"           # 30 min ephemeral
    BASIC = "basic"         # 2 hour ephemeral
    PRO = "pro"             # 24 hour ephemeral
    SAVED = "saved"         # Permanent (user explicitly saved)


@dataclass
class ProjectDatabaseInfo:
    """Tracks database info for cleanup"""
    project_id: str
    user_id: str
    db_type: str  # postgresql, mysql, mongodb
    db_name: str
    created_at: datetime
    last_activity: datetime
    tier: ProjectTier = ProjectTier.FREE
    is_saved: bool = False  # User explicitly saved = permanent


class EphemeralDatabaseManager:
    """
    Manages ephemeral project databases with automatic cleanup.

    Lifecycle:
    1. User runs project → provision_database()
    2. User interacts → update_activity()
    3. 30 min no activity → cleanup deletes database
    4. User clicks "Save" → mark_as_saved() = permanent
    """

    # Cleanup intervals by tier
    CLEANUP_INTERVALS = {
        ProjectTier.FREE: timedelta(minutes=30),
        ProjectTier.BASIC: timedelta(hours=2),
        ProjectTier.PRO: timedelta(hours=24),
        ProjectTier.SAVED: None,  # Never cleanup
    }

    def __init__(self):
        self._active_databases: Dict[str, ProjectDatabaseInfo] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        """Start the cleanup background task"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Ephemeral database cleanup service started")

    async def stop(self):
        """Stop the cleanup background task"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Ephemeral database cleanup service stopped")

    async def register_database(
        self,
        project_id: str,
        user_id: str,
        db_type: str,
        db_name: str,
        tier: ProjectTier = ProjectTier.FREE
    ):
        """Register a new project database for tracking"""
        now = datetime.utcnow()

        self._active_databases[project_id] = ProjectDatabaseInfo(
            project_id=project_id,
            user_id=user_id,
            db_type=db_type,
            db_name=db_name,
            created_at=now,
            last_activity=now,
            tier=tier,
            is_saved=False
        )

        logger.info(f"Registered ephemeral database: {project_id} (tier: {tier.value})")

    def update_activity(self, project_id: str):
        """Update last activity time (call on any user interaction)"""
        if project_id in self._active_databases:
            self._active_databases[project_id].last_activity = datetime.utcnow()

    def mark_as_saved(self, project_id: str) -> bool:
        """
        Mark project as saved (permanent, no cleanup).
        Called when user clicks "Save Project" button.
        """
        if project_id in self._active_databases:
            self._active_databases[project_id].is_saved = True
            self._active_databases[project_id].tier = ProjectTier.SAVED
            logger.info(f"Project marked as saved (permanent): {project_id}")
            return True
        return False

    def get_time_remaining(self, project_id: str) -> Optional[timedelta]:
        """Get time remaining before database is deleted"""
        if project_id not in self._active_databases:
            return None

        info = self._active_databases[project_id]

        if info.is_saved or info.tier == ProjectTier.SAVED:
            return None  # Permanent

        interval = self.CLEANUP_INTERVALS.get(info.tier)
        if not interval:
            return None

        elapsed = datetime.utcnow() - info.last_activity
        remaining = interval - elapsed

        return remaining if remaining.total_seconds() > 0 else timedelta(seconds=0)

    def get_status(self, project_id: str) -> Optional[dict]:
        """Get database status for frontend display"""
        if project_id not in self._active_databases:
            return None

        info = self._active_databases[project_id]
        remaining = self.get_time_remaining(project_id)

        return {
            "project_id": project_id,
            "db_type": info.db_type,
            "db_name": info.db_name,
            "tier": info.tier.value,
            "is_saved": info.is_saved,
            "created_at": info.created_at.isoformat(),
            "last_activity": info.last_activity.isoformat(),
            "time_remaining_seconds": remaining.total_seconds() if remaining else None,
            "is_permanent": info.is_saved or info.tier == ProjectTier.SAVED
        }

    async def _cleanup_loop(self):
        """Background loop that cleans up expired databases"""
        while self._running:
            try:
                await self._perform_cleanup()
                await asyncio.sleep(60)  # Check every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)

    async def _perform_cleanup(self):
        """Check and delete expired databases"""
        now = datetime.utcnow()
        to_delete: Set[str] = set()

        for project_id, info in self._active_databases.items():
            # Skip saved/permanent projects
            if info.is_saved or info.tier == ProjectTier.SAVED:
                continue

            interval = self.CLEANUP_INTERVALS.get(info.tier)
            if not interval:
                continue

            elapsed = now - info.last_activity

            if elapsed >= interval:
                to_delete.add(project_id)
                logger.info(
                    f"Database expired: {project_id} "
                    f"(inactive for {elapsed.total_seconds():.0f}s, "
                    f"limit: {interval.total_seconds():.0f}s)"
                )

        # Delete expired databases
        for project_id in to_delete:
            await self._delete_database(project_id)

    async def _delete_database(self, project_id: str):
        """Delete an expired database"""
        if project_id not in self._active_databases:
            return

        info = self._active_databases[project_id]

        try:
            # Import here to avoid circular imports
            from app.modules.execution.database_infrastructure import (
                db_infrastructure,
                DatabaseType
            )

            # Map string to enum
            db_type_map = {
                "postgresql": DatabaseType.POSTGRESQL,
                "mysql": DatabaseType.MYSQL,
                "mongodb": DatabaseType.MONGODB,
                "redis": DatabaseType.REDIS,
            }

            db_type = db_type_map.get(info.db_type.lower())

            if db_type:
                await db_infrastructure.deprovision_database(
                    project_id=project_id,
                    db_type=db_type,
                    keep_data=False
                )

            # Remove from tracking
            del self._active_databases[project_id]

            logger.info(f"Cleaned up ephemeral database: {project_id} ({info.db_type})")

        except Exception as e:
            logger.error(f"Error cleaning up database {project_id}: {e}")

    def get_stats(self) -> dict:
        """Get cleanup service statistics"""
        now = datetime.utcnow()

        total = len(self._active_databases)
        saved = sum(1 for info in self._active_databases.values() if info.is_saved)

        by_tier = {}
        for tier in ProjectTier:
            by_tier[tier.value] = sum(
                1 for info in self._active_databases.values()
                if info.tier == tier
            )

        # Count expiring soon (< 5 min)
        expiring_soon = 0
        for project_id in self._active_databases:
            remaining = self.get_time_remaining(project_id)
            if remaining and remaining.total_seconds() < 300:
                expiring_soon += 1

        return {
            "total_active_databases": total,
            "saved_permanent": saved,
            "ephemeral": total - saved,
            "expiring_soon": expiring_soon,
            "by_tier": by_tier
        }


# Global instance
ephemeral_db_manager = EphemeralDatabaseManager()


# ============================================================================
# INTEGRATION WITH DATABASE INFRASTRUCTURE
# ============================================================================

async def provision_ephemeral_database(
    project_id: str,
    user_id: str,
    db_type: str,
    user_tier: str = "free"
) -> dict:
    """
    Provision a new ephemeral database for a project.
    Combines database creation + activity tracking.
    """
    from app.modules.execution.database_infrastructure import (
        db_infrastructure,
        DatabaseType
    )

    # Map user tier to project tier
    tier_map = {
        "free": ProjectTier.FREE,
        "basic": ProjectTier.BASIC,
        "pro": ProjectTier.PRO,
    }
    project_tier = tier_map.get(user_tier, ProjectTier.FREE)

    # Map db type string to enum
    db_type_map = {
        "postgresql": DatabaseType.POSTGRESQL,
        "postgres": DatabaseType.POSTGRESQL,
        "mysql": DatabaseType.MYSQL,
        "mongodb": DatabaseType.MONGODB,
        "mongo": DatabaseType.MONGODB,
        "redis": DatabaseType.REDIS,
    }

    db_type_enum = db_type_map.get(db_type.lower())
    if not db_type_enum:
        raise ValueError(f"Unknown database type: {db_type}")

    # Provision the database
    creds = await db_infrastructure.provision_database(project_id, db_type_enum)

    # Register for cleanup tracking
    await ephemeral_db_manager.register_database(
        project_id=project_id,
        user_id=user_id,
        db_type=db_type,
        db_name=creds.database,
        tier=project_tier
    )

    # Get cleanup info
    remaining = ephemeral_db_manager.get_time_remaining(project_id)
    cleanup_interval = EphemeralDatabaseManager.CLEANUP_INTERVALS.get(project_tier)

    return {
        "credentials": creds.to_env_vars(),
        "connection_url": creds.connection_url,
        "database_name": creds.database,
        "is_ephemeral": True,
        "tier": project_tier.value,
        "cleanup_after_minutes": cleanup_interval.total_seconds() / 60 if cleanup_interval else None,
        "time_remaining_seconds": remaining.total_seconds() if remaining else None
    }


async def save_project_database(project_id: str) -> bool:
    """
    Save a project database permanently (no auto-cleanup).
    Called when user clicks "Save Project".
    """
    return ephemeral_db_manager.mark_as_saved(project_id)


def touch_project_activity(project_id: str):
    """
    Update activity timestamp.
    Call this on any user interaction (file edit, run, etc.)
    """
    ephemeral_db_manager.update_activity(project_id)
