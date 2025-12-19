import pytest
from fastapi import FastAPI
from starlette.requests import Request

from app.middlewares.logger import RequestLoggerMiddleware


@pytest.mark.asyncio
async def test_request_logger_middleware_sets_headers():
    app = FastAPI()
    mw = RequestLoggerMiddleware(app)

    async def call_next(req):
        class Resp:
            status_code = 200
            headers = {}
        return Resp()

    resp = await mw.dispatch(Request(scope={"type":"http", "method":"GET", "url": "/"}), call_next)
    assert "X-Process-Time" in resp.headers
    assert "X-Request-ID" in resp.headers
