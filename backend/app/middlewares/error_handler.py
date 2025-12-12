import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.exceptions import AppException
from app.schemas.response import ResponseSchema

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"AppException: {exc.message} - Details: {exc.details}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseSchema(
            success=False,
            message=exc.message,
            errors=exc.details,
            data=None
        ).model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"]
        }
        for err in exc.errors()
    ]

    logger.warning(f"Validation error: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseSchema(
            success=False,
            message="Validation error",
            errors=errors,
            data=None
        ).model_dump()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseSchema(
            success=False,
            message=exc.detail,
            errors=None,
            data=None
        ).model_dump()
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResponseSchema(
            success=False,
            message="Internal server error",
            errors=str(exc) if request.app.state.settings.DEBUG else None,
            data=None
        ).model_dump()
    )
