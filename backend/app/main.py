import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import sentry_sdk
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.api.websocket_manager import WebSocketManager
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.redis import close_redis_pool, create_redis_client
from app.middlewares.error_handler import (
    app_exception_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.middlewares.logger import RequestLoggerMiddleware
from app.middlewares.rate_limiter import RateLimiterMiddleware
from app.utils_helper.threading import ThreadingUtils

sys.dont_write_bytecode = True


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)

    # Initialize redis client and attach to app.state
    try:
        app.state.redis = await create_redis_client()
        # Initialize WebSocket manager and start Redis listener
        try:
            app.state.ws_manager = WebSocketManager(app.state.redis)
            # start the manager which spawns a background redis subscription
            await app.state.ws_manager.start()
        except Exception as e:
            logging.getLogger(__name__).warning(f"WS manager init failed: {e}")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Redis init failed: {e}")

    # Attach threading utilities to app state for global access
    app.state.threading = ThreadingUtils

    try:
        yield
    finally:
        try:
            # Close long-lived redis client and disconnect pool
            if getattr(app.state, "redis", None):
                try:
                    await app.state.redis.close()
                except Exception:
                    logging.getLogger(__name__).warning("Redis client close failed")
            await close_redis_pool()
        except Exception as e:
            logging.getLogger(__name__).warning(f"Redis close failed: {e}")
        # stop websocket manager if present
        try:
            if getattr(app.state, "ws_manager", None):
                await app.state.ws_manager.stop()
        except Exception as e:
            logging.getLogger(__name__).warning(f"WS manager stop failed: {e}")


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
    lifespan=lifespan,
)


# Customize OpenAPI schema to include security scheme
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description=app.description,
        routes=app.routes,
    )
    # Merge with existing security schemes if any, or create new
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    # Add Bearer token security scheme
    openapi_schema["components"]["securitySchemes"]["bearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "Enter your JWT token (without 'Bearer' prefix)",
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix=settings.API_V1_STR)

# Register additional middlewares
app.add_middleware(RequestLoggerMiddleware)
app.add_middleware(RateLimiterMiddleware, requests_per_minute=100)


# Wrapper handlers to satisfy FastAPI's exception handler signature typing
async def _app_exception_handler(request: Request, exc: Exception) -> Response:
    return await app_exception_handler(request, cast(AppException, exc))


async def _validation_exception_handler(request: Request, exc: Exception) -> Response:
    return await validation_exception_handler(
        request, cast(RequestValidationError, exc)
    )


async def _http_exception_handler(request: Request, exc: Exception) -> Response:
    return await http_exception_handler(request, cast(StarletteHTTPException, exc))


# Register global exception handlers
app.add_exception_handler(AppException, _app_exception_handler)
app.add_exception_handler(RequestValidationError, _validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
