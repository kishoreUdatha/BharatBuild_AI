"""
Container State Service - Redis-based Container State Persistence

This service maintains container state in Redis to:
1. Survive backend restarts
2. Share state across multiple backend instances (horizontal scaling)
3. Track user-to-container mappings for quick lookup
4. Enable container reuse instead of creating new containers

Redis Key Structure:
- container:{project_id} -> Container details (JSON)
- user:{user_id}:containers -> Set of project_ids
- container:{project_id}:heartbeat -> Last activity timestamp
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from dataclasses import dataclass, asdict
from enum import Enum

from app.core.config import settings
from app.core.logging_config import logger

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None


class ContainerState(str, Enum):
    """Container lifecycle states"""
    CREATING = "creating"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    DELETED = "deleted"


@dataclass
class ContainerInfo:
    """Container information stored in Redis"""
    container_id: str
    project_id: str
    user_id: str
    state: str
    created_at: str
    last_activity: str
    port_mappings: Dict[int, int]  # container_port -> host_port
    active_port: Optional[int] = None
    docker_host: Optional[str] = None  # For multi-EC2 setup
    memory_limit: str = "512m"
    cpu_limit: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContainerInfo":
        return cls(**data)

    def is_expired(self, idle_timeout: int, max_lifetime: int) -> bool:
        """Check if container should be cleaned up"""
        now = datetime.utcnow()

        # Parse timestamps
        try:
            created = datetime.fromisoformat(self.created_at)
            last_activity = datetime.fromisoformat(self.last_activity)
        except (ValueError, TypeError):
            return True  # Invalid timestamp = expired

        # Check max lifetime
        if (now - created).total_seconds() > max_lifetime:
            return True

        # Check idle timeout
        if (now - last_activity).total_seconds() > idle_timeout:
            return True

        return False

    def should_pause(self, pause_after_idle: int) -> bool:
        """Check if container should be paused (not deleted)"""
        if self.state == ContainerState.PAUSED.value:
            return False  # Already paused

        now = datetime.utcnow()
        try:
            last_activity = datetime.fromisoformat(self.last_activity)
        except (ValueError, TypeError):
            return True

        return (now - last_activity).total_seconds() > pause_after_idle


class ContainerStateService:
    """
    Redis-based container state management.

    Features:
    - Persistent state across backend restarts
    - User-to-container mapping for quick lookup
    - Heartbeat tracking for idle detection
    - Support for horizontal scaling (multiple backend instances)
    """

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._local_cache: Dict[str, ContainerInfo] = {}  # Fallback if Redis unavailable
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Redis connection"""
        if self._initialized:
            return True

        if aioredis is None:
            logger.warning("[ContainerState] redis.asyncio not available, using local cache only")
            self._initialized = True
            return True

        try:
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                db=settings.REDIS_CACHE_DB
            )
            await self._redis.ping()
            logger.info("[ContainerState] Connected to Redis")
            self._initialized = True
            return True
        except Exception as e:
            logger.warning(f"[ContainerState] Redis connection failed: {e}, using local cache")
            self._redis = None
            self._initialized = True
            return True  # Still return True, we'll use local cache

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None

    def _get_container_key(self, project_id: str) -> str:
        """Get Redis key for container info"""
        return f"{settings.REDIS_CONTAINER_STATE_PREFIX}{project_id}"

    def _get_user_containers_key(self, user_id: str) -> str:
        """Get Redis key for user's container set"""
        return f"user:{user_id}:containers"

    def _get_heartbeat_key(self, project_id: str) -> str:
        """Get Redis key for container heartbeat"""
        return f"{settings.REDIS_CONTAINER_STATE_PREFIX}{project_id}:heartbeat"

    async def save_container(self, info: ContainerInfo) -> bool:
        """
        Save container info to Redis.

        Args:
            info: Container information to save

        Returns:
            True if successful
        """
        await self.initialize()

        # Always update local cache
        self._local_cache[info.project_id] = info

        if self._redis:
            try:
                # Save container info
                container_key = self._get_container_key(info.project_id)
                await self._redis.setex(
                    container_key,
                    settings.REDIS_CONTAINER_STATE_TTL,
                    json.dumps(info.to_dict())
                )

                # Add to user's container set
                user_key = self._get_user_containers_key(info.user_id)
                await self._redis.sadd(user_key, info.project_id)
                await self._redis.expire(user_key, settings.REDIS_CONTAINER_STATE_TTL)

                # Update heartbeat
                await self.update_heartbeat(info.project_id)

                logger.debug(f"[ContainerState] Saved container {info.project_id} for user {info.user_id}")
                return True
            except Exception as e:
                logger.error(f"[ContainerState] Failed to save to Redis: {e}")
                return False

        return True  # Local cache was updated

    async def get_container(self, project_id: str) -> Optional[ContainerInfo]:
        """
        Get container info by project ID.

        Args:
            project_id: Project identifier

        Returns:
            ContainerInfo or None if not found
        """
        await self.initialize()

        # Check Redis first
        if self._redis:
            try:
                container_key = self._get_container_key(project_id)
                data = await self._redis.get(container_key)
                if data:
                    info = ContainerInfo.from_dict(json.loads(data))
                    self._local_cache[project_id] = info  # Update local cache
                    return info
            except Exception as e:
                logger.warning(f"[ContainerState] Redis get failed: {e}")

        # Fallback to local cache
        return self._local_cache.get(project_id)

    async def get_user_containers(self, user_id: str) -> List[ContainerInfo]:
        """
        Get all containers for a user.

        Args:
            user_id: User identifier

        Returns:
            List of ContainerInfo objects
        """
        await self.initialize()

        containers = []

        if self._redis:
            try:
                user_key = self._get_user_containers_key(user_id)
                project_ids = await self._redis.smembers(user_key)

                for project_id in project_ids:
                    info = await self.get_container(project_id)
                    if info and info.state != ContainerState.DELETED.value:
                        containers.append(info)
            except Exception as e:
                logger.warning(f"[ContainerState] Redis user containers failed: {e}")

        # Also check local cache
        for project_id, info in self._local_cache.items():
            if info.user_id == user_id and info not in containers:
                if info.state != ContainerState.DELETED.value:
                    containers.append(info)

        return containers

    async def update_heartbeat(self, project_id: str) -> bool:
        """
        Update container heartbeat (last activity time).

        Args:
            project_id: Project identifier

        Returns:
            True if successful
        """
        await self.initialize()

        now = datetime.utcnow().isoformat()

        # Update local cache
        if project_id in self._local_cache:
            self._local_cache[project_id].last_activity = now

        if self._redis:
            try:
                # Update heartbeat key
                heartbeat_key = self._get_heartbeat_key(project_id)
                await self._redis.setex(
                    heartbeat_key,
                    settings.CONTAINER_IDLE_TIMEOUT_SECONDS + 60,  # Slightly longer than idle timeout
                    now
                )

                # Also update the container info
                info = await self.get_container(project_id)
                if info:
                    info.last_activity = now
                    await self.save_container(info)

                return True
            except Exception as e:
                logger.warning(f"[ContainerState] Heartbeat update failed: {e}")

        return True

    async def update_state(self, project_id: str, state: ContainerState) -> bool:
        """
        Update container state.

        Args:
            project_id: Project identifier
            state: New state

        Returns:
            True if successful
        """
        info = await self.get_container(project_id)
        if not info:
            return False

        info.state = state.value
        return await self.save_container(info)

    async def delete_container(self, project_id: str) -> bool:
        """
        Delete container from state store.

        Args:
            project_id: Project identifier

        Returns:
            True if successful
        """
        await self.initialize()

        # Get user_id before deletion
        info = await self.get_container(project_id)
        user_id = info.user_id if info else None

        # Remove from local cache
        self._local_cache.pop(project_id, None)

        if self._redis:
            try:
                # Delete container key
                container_key = self._get_container_key(project_id)
                await self._redis.delete(container_key)

                # Delete heartbeat key
                heartbeat_key = self._get_heartbeat_key(project_id)
                await self._redis.delete(heartbeat_key)

                # Remove from user's container set
                if user_id:
                    user_key = self._get_user_containers_key(user_id)
                    await self._redis.srem(user_key, project_id)

                logger.info(f"[ContainerState] Deleted container state for {project_id}")
                return True
            except Exception as e:
                logger.error(f"[ContainerState] Failed to delete from Redis: {e}")

        return True

    async def get_expired_containers(self) -> List[ContainerInfo]:
        """
        Get all expired containers (for cleanup).

        Returns:
            List of expired ContainerInfo objects
        """
        await self.initialize()

        expired = []
        idle_timeout = settings.CONTAINER_IDLE_TIMEOUT_SECONDS
        max_lifetime = settings.CONTAINER_MAX_LIFETIME_SECONDS

        # Check Redis
        if self._redis:
            try:
                # Scan all container keys
                prefix = settings.REDIS_CONTAINER_STATE_PREFIX
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
                    for key in keys:
                        if ":heartbeat" in key:
                            continue  # Skip heartbeat keys
                        try:
                            data = await self._redis.get(key)
                            if data:
                                info = ContainerInfo.from_dict(json.loads(data))
                                if info.is_expired(idle_timeout, max_lifetime):
                                    expired.append(info)
                        except Exception:
                            pass
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"[ContainerState] Failed to scan Redis for expired: {e}")

        # Also check local cache
        for project_id, info in list(self._local_cache.items()):
            if info.is_expired(idle_timeout, max_lifetime) and info not in expired:
                expired.append(info)

        return expired

    async def get_containers_to_pause(self) -> List[ContainerInfo]:
        """
        Get containers that should be paused (idle but not expired).

        Returns:
            List of ContainerInfo objects to pause
        """
        await self.initialize()

        to_pause = []
        pause_after = settings.CONTAINER_PAUSE_AFTER_IDLE_SECONDS

        # Check local cache and Redis
        all_containers = []

        if self._redis:
            try:
                prefix = settings.REDIS_CONTAINER_STATE_PREFIX
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
                    for key in keys:
                        if ":heartbeat" in key:
                            continue
                        try:
                            data = await self._redis.get(key)
                            if data:
                                all_containers.append(ContainerInfo.from_dict(json.loads(data)))
                        except Exception:
                            pass
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"[ContainerState] Failed to scan for pause candidates: {e}")

        # Add local cache
        for info in self._local_cache.values():
            if info not in all_containers:
                all_containers.append(info)

        # Filter to those that should be paused
        for info in all_containers:
            if info.state == ContainerState.RUNNING.value and info.should_pause(pause_after):
                to_pause.append(info)

        return to_pause

    async def get_stats(self) -> Dict[str, Any]:
        """Get container state statistics"""
        await self.initialize()

        stats = {
            "total_containers": 0,
            "running": 0,
            "paused": 0,
            "stopped": 0,
            "local_cache_size": len(self._local_cache),
            "redis_connected": self._redis is not None
        }

        if self._redis:
            try:
                prefix = settings.REDIS_CONTAINER_STATE_PREFIX
                cursor = 0
                while True:
                    cursor, keys = await self._redis.scan(cursor, match=f"{prefix}*", count=100)
                    for key in keys:
                        if ":heartbeat" in key:
                            continue
                        stats["total_containers"] += 1
                        try:
                            data = await self._redis.get(key)
                            if data:
                                info = json.loads(data)
                                state = info.get("state", "unknown")
                                if state == "running":
                                    stats["running"] += 1
                                elif state == "paused":
                                    stats["paused"] += 1
                                elif state == "stopped":
                                    stats["stopped"] += 1
                        except Exception:
                            pass
                    if cursor == 0:
                        break
            except Exception as e:
                logger.warning(f"[ContainerState] Failed to get stats: {e}")

        return stats


# Singleton instance
_container_state_service: Optional[ContainerStateService] = None


def get_container_state_service() -> ContainerStateService:
    """Get the global container state service instance"""
    global _container_state_service
    if _container_state_service is None:
        _container_state_service = ContainerStateService()
    return _container_state_service


# Convenience functions
async def save_container_state(info: ContainerInfo) -> bool:
    """Save container state"""
    return await get_container_state_service().save_container(info)


async def get_container_state(project_id: str) -> Optional[ContainerInfo]:
    """Get container state"""
    return await get_container_state_service().get_container(project_id)


async def update_container_heartbeat(project_id: str) -> bool:
    """Update container heartbeat"""
    return await get_container_state_service().update_heartbeat(project_id)


async def delete_container_state(project_id: str) -> bool:
    """Delete container state"""
    return await get_container_state_service().delete_container(project_id)
