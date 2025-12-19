import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # defensive access: some test Request scopes may omit headers
        try:
            request_id = request.headers.get("X-Request-ID", "N/A")
        except Exception:
            request_id = "N/A"

        start_time = time.time()

        # defensively get request path (tests may provide minimal scope)
        try:
            path = request.url.path
        except Exception:
            raw_path = request.scope.get("path") or request.scope.get("raw_path", "/")
            path = (
                raw_path.decode()
                if isinstance(raw_path, bytes | bytearray)
                else str(raw_path)
            )

        logger.info(
            f"Request started: {request.method} {path} [Request ID: {request_id}]"
        )

        response = await call_next(request)

        process_time = time.time() - start_time
        try:
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
        except Exception:
            # best-effort header setting; tests expect headers dict
            pass

        logger.info(
            f"Request completed: {request.method} {path} "
            f"Status: {getattr(response, 'status_code', 'n/a')} "
            f"Duration: {process_time:.3f}s "
            f"[Request ID: {request_id}]"
        )

        return response
