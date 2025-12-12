import logging
import sentry_sdk
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.api.main import api_router
from app.core.config import settings

# middlewares
from app.middlewares.logger import RequestLoggerMiddleware
from app.middlewares.rate_limiter import RateLimiterMiddleware

# redis client and threading utils
from app.core.redis import RedisClient
from app.utils_helper.threading import ThreadingUtils


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


if settings.SENTRY_DSN and settings.ENVIRONMENT != "local":
    sentry_sdk.init(dsn=str(settings.SENTRY_DSN), enable_tracing=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)

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


@app.on_event("startup")
async def startup_event():
    # Configure basic logging
    logging.basicConfig(level=logging.INFO)

    # Initialize redis client and attach to app.state
    try:
        app.state.redis = await RedisClient.get_client()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Redis init failed: {e}")

    # Attach threading utilities to app state for global access
    app.state.threading = ThreadingUtils


@app.on_event("shutdown")
async def shutdown_event():
    try:
        await RedisClient.close()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Redis close failed: {e}")
