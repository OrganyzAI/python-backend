import pytest
import asyncio

from app.core.redis import CacheService


class FakeRedis:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ex=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def exists(self, key):
        return 1 if key in self.store else 0


@pytest.mark.asyncio
async def test_cache_set_get_delete_exists():
    redis = FakeRedis()
    cache = CacheService(redis)

    await cache.set("k", {"a": 1})
    v = await cache.get("k")
    assert v == {"a": 1}

    assert await cache.exists("k") is True

    await cache.delete("k")
    assert await cache.get("k") is None
    assert await cache.exists("k") is False
