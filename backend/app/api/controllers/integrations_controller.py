import uuid
from typing import Any

from fastapi.responses import JSONResponse, Response
from sqlmodel import SQLModel
from starlette import status

from app.core.exceptions import AppException
from app.schemas.external_account import (
    ExternalAccountCreate,
    GoogleDriveTokenResponse,
)
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
        elif isinstance(data, SQLModel):
            # Convert SQLModel to dict with proper UUID serialization
            data_payload = data.model_dump(mode="json")

        payload = self.response_class(
            success=True,
            message=msg,
            data=data_payload,
            errors=None,
            meta=None,
        ).model_dump(mode="json", exclude_none=True)

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
            ).model_dump(mode="json", exclude_none=True)
            return JSONResponse(status_code=int(code), content=payload)

        code = code if code is not None else status.HTTP_400_BAD_REQUEST
        msg = str(message)

        payload = self.response_class(
            success=False,
            message=msg,
            errors=errors,
            data=None,
        ).model_dump(mode="json", exclude_none=True)

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

    async def connect_google_drive_with_tokens(
        self,
        token_response: GoogleDriveTokenResponse,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Connect Google Drive account using token response directly"""
        try:
            account = await self.service.connect_google_drive_with_tokens(
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                expires_in=token_response.expires_in,
                scope=token_response.scope,
                user_id=user_id,
            )
            return self._success(
                data=account,
                message="Google Drive account connected successfully with provided tokens",
            )
        except Exception as e:
            return self._error(message=e)

    async def upload_file_to_google_drive(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file_content: bytes,
        mime_type: str,
        parent_folder_id: str | None = None,
    ) -> JSONResponse:
        """Upload a file to Google Drive"""
        try:
            result = await self.service.upload_file_to_google_drive(
                user_id=user_id,
                file_name=file_name,
                file_content=file_content,
                mime_type=mime_type,
                parent_folder_id=parent_folder_id,
            )
            return self._success(
                data=result,
                message="File uploaded to Google Drive successfully",
            )
        except Exception as e:
            return self._error(message=e)

    async def list_google_drive_files(
        self,
        user_id: uuid.UUID,
        page_size: int = 100,
        page_token: str | None = None,
        query: str | None = None,
    ) -> JSONResponse:
        """List all files in Google Drive"""
        try:
            result = await self.service.list_google_drive_files(
                user_id=user_id,
                page_size=page_size,
                page_token=page_token,
                query=query,
            )
            return self._success(
                data=result,
                message="Files retrieved successfully",
            )
        except Exception as e:
            return self._error(message=e)

    async def read_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
    ) -> JSONResponse:
        """Read file content from Google Drive"""
        try:
            result = await self.service.read_google_drive_file(
                user_id=user_id,
                file_id=file_id,
            )
            return self._success(
                data=result,
                message="File read successfully",
            )
        except Exception as e:
            return self._error(message=e)

    async def update_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
        file_content: bytes | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
    ) -> JSONResponse:
        """Update file content and/or metadata in Google Drive"""
        try:
            result = await self.service.update_google_drive_file(
                user_id=user_id,
                file_id=file_id,
                file_content=file_content,
                file_name=file_name,
                mime_type=mime_type,
            )
            return self._success(
                data=result,
                message="File updated successfully",
            )
        except Exception as e:
            return self._error(message=e)

    async def download_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
    ) -> Response | JSONResponse:
        """Download file content from Google Drive as a streaming response"""
        try:
            (
                content,
                content_type,
                metadata,
            ) = await self.service.download_google_drive_file(
                user_id=user_id,
                file_id=file_id,
            )
            filename = metadata.get("name", "file")
            return Response(
                content=content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                },
            )
        except Exception as e:
            return self._error(message=e)
