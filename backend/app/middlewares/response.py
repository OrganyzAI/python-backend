import json
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.schemas.response import ResponseSchema


class ResponseFormatterMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)

        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return response

        # Read response body (consume iterator when present)
        body_bytes = b""
        body_iterator = getattr(response, "body_iterator", None)
        if body_iterator is not None:
            try:
                async for chunk in body_iterator:
                    body_bytes += chunk
            except Exception:
                # fallback to body attribute if iteration fails
                body_bytes = getattr(response, "body", b"") or b""
        else:
            body_bytes = getattr(response, "body", b"") or b""

        try:
            text = body_bytes.decode("utf-8") if body_bytes else ""
        except Exception:
            return response

        if not text:
            original = None
        else:
            try:
                original = json.loads(text)
            except Exception:
                # Not JSON-parsable — leave response unchanged
                return response

        status_code = getattr(response, "status_code", 200)

        # If already formatted (has `success` key), return as-is
        if isinstance(original, dict) and "success" in original:
            new_content = original
        else:
            # For error HTTP statuses, mark success=False
            if status_code >= 400:
                message = None
                errors: Any = None
                if isinstance(original, dict):
                    message = (
                        original.get("detail")
                        or original.get("message")
                        or str(original)
                    )
                    errors = original.get("errors") or original.get("detail")
                else:
                    message = str(original) if original is not None else "Error"

                # Use model_dump(exclude_none=True) so `data` is removed when None
                new_content = ResponseSchema(
                    success=False,
                    message=message or "Error",
                    errors=errors,
                    data=None,
                ).model_dump(exclude_none=True)
            else:
                # Build success response. Normalize common shapes:
                # - If original has top-level "message", use it as top-level message
                # - If original has "user", place that object into `data`
                # - If original has `data` and that inner dict contains a "message", remove that inner "message"
                message = "Success"
                data_payload = original

                if isinstance(original, dict):
                    message = original.get("message") or message

                    if "user" in original:
                        data_payload = original.get("user")
                    elif "data" in original:
                        data_payload = original.get("data")
                        if isinstance(data_payload, dict) and "message" in data_payload:
                            # remove nested message inside data
                            data_payload = {
                                k: v for k, v in data_payload.items() if k != "message"
                            }

                new_content = ResponseSchema(
                    success=True,
                    message=message,
                    data=data_payload,
                    errors=None,
                ).model_dump(exclude_none=True)

        # Preserve headers (except content-length which will be recalculated)
        headers = {
            k: v for k, v in response.headers.items() if k.lower() != "content-length"
        }
        return JSONResponse(
            status_code=status_code, content=new_content, headers=headers
        )
