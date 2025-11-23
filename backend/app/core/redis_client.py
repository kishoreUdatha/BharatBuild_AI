import redis.asyncio as aioredis
from redis.asyncio import Redis
from typing import Optional
import json
from datetime import timedelta

from app.core.config import settings
from app.core.logging_config import logger


class RedisClient:
    """Redis client for caching and session management"""

    def __init__(self):
        self.redis: Optional[Redis] = None
        self.cache_redis: Optional[Redis] = None

    async def connect(self):
        """Connect to Redis"""
        try:
            # Main Redis connection
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )

            # Cache Redis connection (different DB)
            cache_url = settings.REDIS_URL.rsplit('/', 1)[0] + f"/{settings.REDIS_CACHE_DB}"
            self.cache_redis = await aioredis.from_url(
                cache_url,
                encoding="utf-8",
                decode_responses=True
            )

            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
        if self.cache_redis:
            await self.cache_redis.close()
        logger.info("Redis disconnected")

    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None
    ) -> bool:
        """Set value in Redis"""
        try:
            if expire:
                return await self.redis.setex(key, expire, value)
            return await self.redis.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        try:
            return await self.redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis"""
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False

    async def cache_get(self, key: str) -> Optional[dict]:
        """Get cached value"""
        try:
            value = await self.cache_redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Cache GET error: {e}")
            return None

    async def cache_set(
        self,
        key: str,
        value: dict,
        expire: int = 3600
    ) -> bool:
        """Set cached value"""
        try:
            return await self.cache_redis.setex(
                key,
                expire,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache SET error: {e}")
            return False

    async def cache_delete(self, key: str) -> bool:
        """Delete cached value"""
        try:
            return await self.cache_redis.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache DELETE error: {e}")
            return False

    async def increment(self, key: str) -> int:
        """Increment counter"""
        try:
            return await self.redis.incr(key)
        except Exception as e:
            logger.error(f"Redis INCR error: {e}")
            return 0

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        try:
            return await self.redis.expire(key, seconds)
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False


# Create Redis client instance
redis_client = RedisClient()


# Dependency
async def get_redis() -> RedisClient:
    """Get Redis client"""
    return redis_client
