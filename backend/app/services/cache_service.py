"""
Redis Cache Service - High-performance caching layer
Optimized for 100K+ users with intelligent TTL and LRU eviction
"""

import json
import pickle
from typing import Optional, Any, List
from datetime import timedelta
import redis.asyncio as redis

from app.core.config import settings
from app.core.logging_config import logger


class CacheService:
    """
    Redis-based caching service for project files and metadata

    Cache Strategy:
    - Project metadata: 1 hour TTL
    - Active project files: 15 minutes TTL (LRU eviction)
    - File content: 5 minutes TTL (for hot files)
    - User sessions: 30 minutes TTL
    """

    # TTL constants loaded from settings (in seconds)
    @property
    def TTL_PROJECT_META(self):
        return settings.CACHE_TTL_PROJECT_META

    @property
    def TTL_PROJECT_FILES(self):
        return settings.CACHE_TTL_PROJECT_FILES

    @property
    def TTL_FILE_CONTENT(self):
        return settings.CACHE_TTL_FILE_CONTENT

    @property
    def TTL_USER_SESSION(self):
        return settings.CACHE_TTL_USER_SESSION

    # Key prefixes for organization
    PREFIX_PROJECT = "project:"
    PREFIX_FILES = "files:"
    PREFIX_CONTENT = "content:"
    PREFIX_USER = "user:"

    def __init__(self):
        self._pool = None
        self._redis = None

    async def _get_redis(self) -> redis.Redis:
        """Lazy initialization of Redis connection pool"""
        if self._redis is None:
            self._pool = redis.ConnectionPool.from_url(
                settings.REDIS_URL,
                db=settings.REDIS_CACHE_DB,
                max_connections=50,
                decode_responses=False  # We'll handle encoding ourselves
            )
            self._redis = redis.Redis(connection_pool=self._pool)
            logger.info("Redis cache connection established")
        return self._redis

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    # ========== Project Metadata Cache ==========

    async def get_project(self, project_id: str) -> Optional[dict]:
        """Get cached project metadata"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_PROJECT}{project_id}"
            data = await r.get(key)
            if data:
                logger.debug(f"Cache HIT: project {project_id}")
                return json.loads(data)
            logger.debug(f"Cache MISS: project {project_id}")
            return None
        except Exception as e:
            logger.warning(f"Cache error (get_project): {e}")
            return None

    async def set_project(self, project_id: str, data: dict) -> bool:
        """Cache project metadata"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_PROJECT}{project_id}"
            await r.setex(key, self.TTL_PROJECT_META, json.dumps(data))
            logger.debug(f"Cached project: {project_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache error (set_project): {e}")
            return False

    async def invalidate_project(self, project_id: str) -> bool:
        """Invalidate project cache"""
        try:
            r = await self._get_redis()
            keys = [
                f"{self.PREFIX_PROJECT}{project_id}",
                f"{self.PREFIX_FILES}{project_id}"
            ]
            await r.delete(*keys)
            logger.debug(f"Invalidated cache for project: {project_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache error (invalidate_project): {e}")
            return False

    # ========== Project Files List Cache ==========

    async def get_project_files(self, project_id: str) -> Optional[List[dict]]:
        """Get cached list of project files"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_FILES}{project_id}"
            data = await r.get(key)
            if data:
                logger.debug(f"Cache HIT: files for project {project_id}")
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache error (get_project_files): {e}")
            return None

    async def set_project_files(self, project_id: str, files: List[dict]) -> bool:
        """Cache list of project files"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_FILES}{project_id}"
            await r.setex(key, self.TTL_PROJECT_FILES, json.dumps(files))
            logger.debug(f"Cached {len(files)} files for project: {project_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache error (set_project_files): {e}")
            return False

    # ========== File Content Cache ==========

    async def get_file_content(self, project_id: str, file_path: str) -> Optional[str]:
        """Get cached file content"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_CONTENT}{project_id}:{file_path}"
            data = await r.get(key)
            if data:
                logger.debug(f"Cache HIT: content for {file_path}")
                return data.decode('utf-8')
            return None
        except Exception as e:
            logger.warning(f"Cache error (get_file_content): {e}")
            return None

    async def set_file_content(self, project_id: str, file_path: str, content: str) -> bool:
        """Cache file content (only for frequently accessed files)"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_CONTENT}{project_id}:{file_path}"
            # Only cache files under 100KB
            if len(content) < 102400:
                await r.setex(key, self.TTL_FILE_CONTENT, content.encode('utf-8'))
                logger.debug(f"Cached content for: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Cache error (set_file_content): {e}")
            return False

    async def invalidate_file(self, project_id: str, file_path: str) -> bool:
        """
        Invalidate file content cache.
        Also invalidates file list and project metadata (since updated_at changes).
        """
        try:
            r = await self._get_redis()
            keys = [
                f"{self.PREFIX_CONTENT}{project_id}:{file_path}",  # File content
                f"{self.PREFIX_FILES}{project_id}",  # File list
                f"{self.PREFIX_PROJECT}{project_id}"  # Project metadata (updated_at changes)
            ]
            await r.delete(*keys)
            logger.debug(f"Invalidated cache for file: {file_path} in project: {project_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache error (invalidate_file): {e}")
            return False

    # ========== User Session Cache ==========

    async def get_user_active_project(self, user_id: str) -> Optional[str]:
        """Get user's currently active project ID"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_USER}{user_id}:active_project"
            data = await r.get(key)
            return data.decode('utf-8') if data else None
        except Exception as e:
            logger.warning(f"Cache error (get_user_active_project): {e}")
            return None

    async def set_user_active_project(self, user_id: str, project_id: str) -> bool:
        """Set user's currently active project"""
        try:
            r = await self._get_redis()
            key = f"{self.PREFIX_USER}{user_id}:active_project"
            await r.setex(key, self.TTL_USER_SESSION, project_id.encode('utf-8'))
            return True
        except Exception as e:
            logger.warning(f"Cache error (set_user_active_project): {e}")
            return False

    # ========== Bulk Operations ==========

    async def warm_project_cache(self, project_id: str, metadata: dict, files: List[dict]) -> bool:
        """Warm cache with project data (called on project load)"""
        try:
            await self.set_project(project_id, metadata)
            await self.set_project_files(project_id, files)
            logger.info(f"Warmed cache for project: {project_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to warm cache: {e}")
            return False

    async def clear_all_project_cache(self, project_id: str) -> bool:
        """Clear all cache related to a project"""
        try:
            r = await self._get_redis()
            # Find all keys for this project
            pattern = f"*{project_id}*"
            cursor = 0
            keys_to_delete = []

            while True:
                cursor, keys = await r.scan(cursor, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break

            if keys_to_delete:
                await r.delete(*keys_to_delete)
                logger.info(f"Cleared {len(keys_to_delete)} cache keys for project: {project_id}")

            return True
        except Exception as e:
            logger.warning(f"Cache error (clear_all_project_cache): {e}")
            return False

    # ========== Stats ==========

    async def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        try:
            r = await self._get_redis()
            info = await r.info('memory')
            return {
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'total_keys': await r.dbsize()
            }
        except Exception as e:
            logger.warning(f"Cache error (get_cache_stats): {e}")
            return {}


# Singleton instance
cache_service = CacheService()
