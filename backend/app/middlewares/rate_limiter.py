import time
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Dict
from collections import defaultdict
import asyncio


class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 60
        self._start_cleanup_task()

    def _start_cleanup_task(self):
        asyncio.create_task(self._cleanup_old_requests())

    async def _cleanup_old_requests(self):
        while True:
            await asyncio.sleep(self.cleanup_interval)
            current_time = time.time()
            for ip in list(self.requests.keys()):
                self.requests[ip] = [
                    req_time for req_time in self.requests[ip]
                    if current_time - req_time < 60
                ]
                if not self.requests[ip]:
                    del self.requests[ip]

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = request.client.host
        current_time = time.time()

        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < 60
        ]

        if len(self.requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

        self.requests[client_ip].append(current_time)
        response = await call_next(request)

        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.requests[client_ip])
        )

        return response
