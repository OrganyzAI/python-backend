import uuid
from typing import Any

from fastapi.datastructures import UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from starlette import status

from app.core.exceptions import AppException
from app.schemas.external_account import OneDriveTokenResponse
from app.schemas.response import ResponseSchema
from app.services.one_drive_service import OneDriveService


class OneDriveController:
    def __init__(self) -> None:
        self.service = OneDriveService()
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

    async def connect_one_drive_with_tokens(
        self,
        token_response: OneDriveTokenResponse,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Connect One Drive account using token response directly"""
        try:
            account = await self.service.connect_one_drive_with_tokens(
                access_token=token_response.access_token,
                expires_in=token_response.expires_in,
                ext_expires_in=token_response.ext_expires_in,
                token_source=token_response.token_source,
                token_type=token_response.token_type,
                user_id=user_id,
            )
            return self._success(
                data=account,
                message="One Drive account connected successfully with provided tokens",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_all_files_with_tenants(
        self,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Get all files organized by tenants"""
        try:
            result = await self.service.get_all_files_with_tenants(user_id=user_id)
            return self._success(
                data=result,
                message="Successfully retrieved all files with tenants",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_all_tenants(
        self,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Get all tenants/sites"""
        try:
            tenants = await self.service.get_all_tenants(user_id=user_id)
            return self._success(
                data=tenants,
                message="Successfully retrieved all tenants",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_files_for_tenant(
        self,
        user_id: uuid.UUID,
        site_id: str,
    ) -> JSONResponse:
        """Get all files for a specific tenant"""
        try:
            files = await self.service.get_files_for_tenant(
                user_id=user_id, site_id=site_id
            )
            return self._success(
                data=files,
                message=f"Successfully retrieved files for tenant {site_id}",
            )
        except Exception as e:
            return self._error(message=e)

    async def upload_file(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file: UploadFile,
    ) -> JSONResponse:
        """Upload a file to One Drive"""
        try:
            file_content = await file.read()
            result = await self.service.upload_file_to_one_drive(
                user_id=user_id, file_name=file_name, file_content=file_content
            )
            return self._success(
                data=result,
                message="Successfully uploaded file to One Drive",
            )
        except Exception as e:
            return self._error(message=e)
