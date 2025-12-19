import asyncio
import pytest
import time

from app.middlewares.rate_limiter import RateLimiterMiddleware
from starlette.requests import Request
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    app = FastAPI()
    mw = RateLimiterMiddleware(app, requests_per_minute=5, window_seconds=1)

    class Dummy:
        client = type("C", (), {"host": "127.0.0.1"})

    async def call_next(req):
        class Resp:
            headers = {}
        return Resp()

    # send 3 requests quickly
    for _ in range(3):
        allowed_resp = await mw.dispatch(Request(scope={"type":"http"}), call_next)
        assert allowed_resp.headers["X-RateLimit-Limit"] == "5"


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    app = FastAPI()
    mw = RateLimiterMiddleware(app, requests_per_minute=2, window_seconds=1)

    async def call_next(req):
        class Resp:
            headers = {}
        return Resp()

    # monkeypatch request.client.host via scope
    class Dummy:
        client = type("C", (), {"host": "127.0.0.1"})

    # first two allowed
    await mw.dispatch(Request(scope={"type":"http"}), call_next)
    await mw.dispatch(Request(scope={"type":"http"}), call_next)

    # third should raise HTTPException
    with pytest.raises(Exception):
        await mw.dispatch(Request(scope={"type":"http"}), call_next)
