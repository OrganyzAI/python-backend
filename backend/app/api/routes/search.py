import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.controllers.search_controller import SearchController
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/search", tags=["Search"])
controller = SearchController()


@router.get("/files")
async def search_all_providers(
    query: str = Query(..., description="Search query string (e.g., 'asad')"),
    search_in_content: bool = Query(
        True, description="Whether to search inside file contents"
    ),
    max_file_size: int = Query(
        10 * 1024 * 1024,
        description="Maximum file size to search content in bytes (default: 10MB)",
    ),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    return await controller.search_all_providers(
        user_id=user_id,
        query=query,
        search_in_content=search_in_content,
        max_file_size=max_file_size,
    )
