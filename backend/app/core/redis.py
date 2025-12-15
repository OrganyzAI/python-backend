import asyncio
import json
import logging
from typing import Optional, AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_pool: Optional[aioredis.ConnectionPool] = None
_pool_lock = asyncio.Lock()


async def get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        async with _pool_lock:
            if _redis_pool is None:
                _redis_pool = aioredis.ConnectionPool.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    max_connections=50,
                    socket_connect_timeout=5,
                    health_check_interval=30,
                )
                logger.info("Redis connection pool created")
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    pool = await get_redis_pool()
    redis = aioredis.Redis(connection_pool=pool)
    try:
        yield redis
    finally:
        try:
            await redis.close()
        except Exception:
            logger.exception("Error closing temporary Redis client")


async def create_redis_client() -> aioredis.Redis:
    pool = await get_redis_pool()
    client = aioredis.Redis(connection_pool=pool)
    logger.info("Redis client created from pool")
    return client


async def close_redis_pool():
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.disconnect()
            logger.info("Redis connection pool disconnected")
        except Exception:
            logger.exception("Error disconnecting Redis pool")
        finally:
            _redis_pool = None


class CacheService:
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def get(self, key: str) -> Optional[dict]:
        try:
            value = await self.redis.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    async def set(self, key: str, value: dict, expire: int = 3600):
        try:
            await self.redis.set(key, json.dumps(value), ex=expire)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")

    async def delete(self, key: str):
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")

    async def exists(self, key: str) -> bool:
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error: {e}")
            return False
