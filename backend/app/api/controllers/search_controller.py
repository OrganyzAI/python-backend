import uuid
from typing import Any

from fastapi.responses import JSONResponse
from sqlmodel import SQLModel
from starlette import status

from app.core.exceptions import AppException
from app.schemas.response import ResponseSchema
from app.services.search_service import SearchService


class SearchController:
    def __init__(self) -> None:
        self.service = SearchService()
        self.response_class: type[ResponseSchema[Any]] = ResponseSchema
        self.error_class = AppException

    def _serialize_datetime(self, obj: Any) -> Any:
        """Recursively serialize datetime objects to ISO format strings"""
        if isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        elif hasattr(obj, "isoformat"):  # datetime objects
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
            # Recursively serialize any remaining datetime objects
            data_payload = self._serialize_datetime(data_payload)

        # Serialize datetime objects in data_payload
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

    async def search_all_providers(
        self,
        user_id: uuid.UUID,
        query: str,
        search_in_content: bool = True,
        max_file_size: int = 10 * 1024 * 1024,
    ) -> JSONResponse:
        try:
            if not query or not query.strip():
                return self._error(
                    message="Search query cannot be empty",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            results = await self.service.search_all_providers(
                user_id=user_id,
                search_query=query,
                search_in_content=search_in_content,
                max_file_size=max_file_size,
            )

            return self._success(
                data=results,
                message=f"Search completed. Found {results.get('total_files', 0)} files matching '{query}'",
            )
        except Exception as e:
            return self._error(message=e)
