from typing import Any, TypedDict


class ErrorResponse(TypedDict):
    success: bool
    message: str
    errors: Any | None


class AppException(Exception):

    def __init__(
        self,
        message: str = "Application error",
        status_code: int = 400,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_dict(self) -> ErrorResponse:
        return {
            "success": False,
            "message": self.message,
            "errors": self.details,
        }

    def __str__(self) -> str:
        return self.message


class NotFoundException(AppException):

    def __init__(self, message: str = "Not found", details: Any | None = None) -> None:
        super().__init__(message=message, status_code=404, details=details)


class UnauthorizedException(AppException):

    def __init__(
        self, message: str = "Unauthorized", details: Any | None = None
    ) -> None:
        super().__init__(message=message, status_code=401, details=details)


class ForbiddenException(AppException):

    def __init__(self, message: str = "Forbidden", details: Any | None = None) -> None:
        super().__init__(message=message, status_code=403, details=details)
