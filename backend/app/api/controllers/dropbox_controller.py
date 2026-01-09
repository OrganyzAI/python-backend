import uuid
from datetime import datetime
from typing import Any

from fastapi.datastructures import UploadFile
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from starlette import status

from app.core.exceptions import AppException
from app.schemas.external_account import DropboxTokenResponse
from app.schemas.response import ResponseSchema
from app.services.dropbox_service import DropboxService


class DropboxController:
    def __init__(self) -> None:
        self.service = DropboxService()
        self.response_class: type[ResponseSchema[Any]] = ResponseSchema
        self.error_class = AppException

    def _serialize_datetime(self, obj: Any) -> Any:
        """Recursively serialize datetime objects to ISO format strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {k: self._serialize_datetime(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj

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
            # Recursively serialize any remaining datetime objects (e.g., in extra_data)
            data_payload = self._serialize_datetime(data_payload)

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

    async def connect_dropbox_with_tokens(
        self,
        token_response: DropboxTokenResponse,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Connect Dropbox account using token response directly"""
        try:
            account = await self.service.connect_dropbox_with_tokens(
                access_token=token_response.access_token,
                expires_in=token_response.expires_in,
                refresh_token=token_response.refresh_token,
                scope=token_response.scope,
                user_id=user_id,
            )
            return self._success(
                data=account,
                message="Dropbox account connected successfully with provided tokens",
            )
        except Exception as e:
            return self._error(message=e)

    def get_authorization_url(
        self,
        state: str | None = None,
    ) -> JSONResponse:
        """Get Dropbox OAuth authorization URL"""
        try:
            auth_url = self.service.get_dropbox_authorization_url(state=state)
            return self._success(
                data={"authorization_url": auth_url},
                message="Successfully generated authorization URL",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_all_files_with_namespaces(
        self,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Get all files organized by namespaces"""
        try:
            result = await self.service.get_all_files_with_namespaces(user_id=user_id)
            return self._success(
                data=result,
                message="Successfully retrieved all files with namespaces",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_all_files(
        self,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Get all files as a flat list without namespace organization"""
        try:
            files = await self.service.get_all_files_combined(user_id=user_id)
            return self._success(
                data={"files": files, "total_files": len(files)},
                message="Successfully retrieved all files",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_all_namespaces(
        self,
        user_id: uuid.UUID,
    ) -> JSONResponse:
        """Get all namespaces"""
        try:
            namespaces = await self.service.get_all_namespaces(user_id=user_id)
            return self._success(
                data=namespaces,
                message="Successfully retrieved all namespaces",
            )
        except Exception as e:
            return self._error(message=e)

    async def get_files_for_namespace(
        self,
        user_id: uuid.UUID,
        namespace_id: str,
    ) -> JSONResponse:
        """Get all files for a specific namespace"""
        try:
            files = await self.service.get_files_for_namespace(
                user_id=user_id, namespace_id=namespace_id
            )
            return self._success(
                data=files,
                message=f"Successfully retrieved files for namespace {namespace_id}",
            )
        except Exception as e:
            return self._error(message=e)

    async def upload_file(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file: UploadFile,
    ) -> JSONResponse:
        """Upload a file to Dropbox"""
        try:
            file_content = await file.read()
            result = await self.service.upload_file_to_dropbox(
                user_id=user_id, file_name=file_name, file_content=file_content
            )
            return self._success(
                data=result,
                message="Successfully uploaded file to Dropbox",
            )
        except Exception as e:
            return self._error(message=e)
