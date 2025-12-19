import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import AppException
from app.schemas.response import ResponseSchema

logger = logging.getLogger(__name__)


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    logger.error(f"AppException: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseSchema(
            success=False, message=exc.message, errors=exc.details, data=None
        ).model_dump(exclude_none=True),
    )


async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]

    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseSchema(
            success=False, message="Validation error", errors=errors, data=None
        ).model_dump(exclude_none=True),
    )


async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseSchema(
            success=False, message=exc.detail, errors=None, data=None
        ).model_dump(exclude_none=True),
    )


async def unhandled_exception_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResponseSchema(
            success=False,
            message="Internal server error",
            errors=str(exc) if settings.DEBUG else None,
            data=None,
        ).model_dump(exclude_none=True),
    )
