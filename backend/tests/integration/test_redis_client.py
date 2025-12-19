import asyncio
import pytest

import redis.asyncio as aioredis

from app.core import redis as redis_module


class DummyPool:
    pass


@pytest.mark.asyncio
async def test_get_redis_pool_is_singleton(monkeypatch):
    called = 0

    async def fake_from_url(url, **kwargs):
        nonlocal called
        called += 1
        return DummyPool()

    monkeypatch.setattr(aioredis.ConnectionPool, "from_url", staticmethod(fake_from_url))

    p1 = await redis_module.get_redis_pool()
    p2 = await redis_module.get_redis_pool()
    assert p1 is p2
    assert called == 1


@pytest.mark.asyncio
async def test_get_redis_generator(monkeypatch):
    class FakeRedis:
        async def close(self):
            pass

    async def fake_from_url(url, **kwargs):
        return DummyPool()

    monkeypatch.setattr(aioredis.ConnectionPool, "from_url", staticmethod(fake_from_url))

    # ensure generator yields a redis client and closes without error
    gen = redis_module.get_redis()
    client = await gen.__anext__()
    assert hasattr(client, "close")
    # finalize generator
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass
