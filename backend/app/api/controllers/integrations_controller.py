import uuid
from typing import Any

from fastapi.responses import JSONResponse
from starlette import status

from app.core.exceptions import AppException
from app.schemas.external_account import ExternalAccountCreate
from app.schemas.response import ResponseSchema
from app.services.integrations_service import IntegrationService


class IntegrationsController:
    def __init__(self) -> None:
        self.service = IntegrationService()
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
            if code is None:
                if isinstance(fallback_status, int):
                    code = fallback_status
                else:
                    code = status.HTTP_400_BAD_REQUEST
            payload = self.response_class(
                success=False,
                message=getattr(exc, "message", str(exc)),
                errors=getattr(exc, "details", None),
                data=None,
            ).model_dump(exclude_none=True)
            return JSONResponse(status_code=int(code), content=payload)

        code = code if code is not None else status.HTTP_400_BAD_REQUEST
        msg = str(message)

        payload = self.response_class(
            success=False,
            message=msg,
            errors=errors,
            data=None,
        ).model_dump(exclude_none=True)

        return JSONResponse(status_code=int(code), content=payload)

    async def connect_account(
        self,
        request: ExternalAccountCreate,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        try:
            account = await self.service.connect_account(
                user_id=user_id,
                provider=request.provider,
                provider_account_id=request.provider_account_id,
                access_token=request.access_token,
                refresh_token=request.refresh_token,
                extra_data=request.extra_data,
            )
            return self._success(data=account, message="Account connected")
        except Exception as e:
            return self._error(message=e)

    async def get_google_drive_auth_url(
        self,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Get Google Drive OAuth2 authorization URL"""
        try:
            auth_data = self.service.get_google_drive_auth_url(user_id=user_id)
            return self._success(
                data=auth_data,
                message="Google Drive authorization URL generated",
            )
        except Exception as e:
            return self._error(message=e)

    async def google_drive_callback(
        self,
        code: str,
        user_id: uuid.UUID,
        state: str | None = None,
    ) -> JSONResponse:
        """Handle Google Drive OAuth2 callback"""
        try:
            account = await self.service.exchange_google_drive_code(
                code=code,
                user_id=user_id,
            )
            return self._success(
                data=account,
                message="Google Drive account connected successfully",
            )
        except Exception as e:
            return self._error(message=e)
