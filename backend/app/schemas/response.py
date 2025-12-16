from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseSchema(BaseModel, Generic[T]):
    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(default="Success", description="Response message")
    data: T | None = Field(default=None, description="Response data")
    errors: Any | None = Field(default=None, description="Error details")
    meta: Any | None = Field(
        default=None,
        description="Additional metadata or pagination info",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": {"id": 1, "name": "Example"},
                "errors": None,
                "meta": {"timestamp": "2024-01-01T00:00:00"},
            }
        }


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PaginatedResponseSchema(ResponseSchema[T], Generic[T]):
    meta: PaginationMeta | None = None
