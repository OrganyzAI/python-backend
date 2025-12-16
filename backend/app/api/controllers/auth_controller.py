from typing import Any

from fastapi.responses import JSONResponse
from starlette import status

from app.core.exceptions import AppException
from app.schemas.response import ResponseSchema
from app.schemas.user import (
    ForgotPasswordSchema,
    LoginSchema,
    RegisterSchema,
    ResendEmailSchema,
    ResetPasswordSchema,
    VerifySchema,
)
from app.services.auth_service import AuthService
from app.utils_helper.messages import Messages as MSG


class UserController:
    def __init__(self) -> None:
        self.service = AuthService()
        self.response_class: type[ResponseSchema[Any]] = ResponseSchema
        self.error_class = AppException

    def _success(
        self,
        data: Any = None,
        message: str = "OK",
        status_code: int = status.HTTP_200_OK,
    ) -> JSONResponse:
        msg = message
        data_payload = data

        if isinstance(data, dict):
            msg = data.get("message") or message
            if "user" in data:
                data_payload = data.get("user")
            elif "data" in data:
                data_payload = data.get("data")
                if isinstance(data_payload, dict) and "message" in data_payload:
                    data_payload = {
                        k: v for k, v in data_payload.items() if k != "message"
                    }

        payload = self.response_class(
            success=True,
            message=msg,
            data=data_payload,
            errors=None,
            meta=None,
        ).model_dump(exclude_none=True)

        return JSONResponse(status_code=status_code, content=payload)

    def _error(
        self, message: Any = "Error", errors: Any = None, status_code: int | None = None
    ) -> JSONResponse:
        code = status_code
        if isinstance(message, self.error_class):
            exc = message
            fallback_status = getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST)
            code = (
                code
                if code is not None
                else fallback_status
                if isinstance(fallback_status, int)
                else status.HTTP_400_BAD_REQUEST
            )
            payload = self.response_class(
                success=False,
                message=getattr(exc, "message", str(exc)),
                errors=getattr(exc, "details", None),
                data=None,
            ).model_dump(exclude_none=True)
            return JSONResponse(status_code=int(code), content=payload)

        if isinstance(message, Exception):
            code = code if code is not None else status.HTTP_400_BAD_REQUEST
            msg = str(message)
        else:
            code = code if code is not None else status.HTTP_400_BAD_REQUEST
            msg = str(message)

        payload = self.response_class(
            success=False,
            message=msg,
            errors=errors,
            data=None,
        ).model_dump(exclude_none=True)

        return JSONResponse(status_code=int(code), content=payload)

    async def login(self, request: LoginSchema) -> JSONResponse:
        try:
            result = await self.service.login(request.email, request.password)
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["USER_LOGGED_IN"],
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            return self._error(exc)

    async def register(self, request: RegisterSchema) -> JSONResponse:
        try:
            result = await self.service.register(
                request.email,
                request.password,
                request.first_name,
                request.last_name,
                request.phone_number,
            )
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["USER_REGISTERED"],
                status_code=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            return self._error(exc)

    async def verify(self, request: VerifySchema) -> JSONResponse:
        try:
            result = await self.service.verify(token=request.token)
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["EMAIL_VERIFIED"],
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            return self._error(exc)

    async def forgot_password(self, request: ForgotPasswordSchema) -> JSONResponse:
        try:
            result = await self.service.forgot_password(email=request.email)
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["PASSWORD_RESET_EMAIL_SENT"],
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            return self._error(exc)

    async def reset_password(self, request: ResetPasswordSchema) -> JSONResponse:
        try:
            result = await self.service.reset_password(
                token=request.token, new_password=request.new_password
            )
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["PASSWORD_HAS_BEEN_RESET"],
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            return self._error(exc)

    async def resend_email(self, request: ResendEmailSchema) -> JSONResponse:
        try:
            result = await self.service.resend_email(email=request.email)
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["VERIFICATION_EMAIL_RESENT"],
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            return self._error(exc)

    async def logout(self) -> JSONResponse:
        try:
            result = await self.service.logout()
            return self._success(
                data=result,
                message=MSG.AUTH["SUCCESS"]["LOGGED_OUT"],
                status_code=status.HTTP_200_OK,
            )
        except Exception as exc:
            return self._error(exc)
