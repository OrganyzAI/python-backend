import time
import uuid
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis


class RateLimiterMiddleware(BaseHTTPMiddleware):

    def __init__(self, app, requests_per_minute: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window = window_seconds

    async def _get_redis(self) -> Optional[Redis]:
        redis = getattr(self.app.state, "redis", None)
        return redis

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - self.window

        redis = await self._get_redis()

        if not redis:
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "-1"
            return response

        key = f"rate_limit:{client_ip}"

        member = f"{now}-{uuid.uuid4().hex}"

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, self.window)
            results = await pipe.execute()
            current_count = int(results[2]) if len(results) >= 3 and results[2] is not None else 0
        except Exception:
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "-1"
            return response

        remaining = max(0, self.requests_per_minute - current_count)

        if current_count > self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
