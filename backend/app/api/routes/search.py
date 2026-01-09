import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.controllers.search_controller import SearchController
from app.api.deps import get_current_user_id

router = APIRouter(prefix="/search", tags=["Search"])
controller = SearchController()


@router.get("/search-files")
async def search_all_providers(
    query: str = Query(..., description="Search query string (e.g., 'asad')"),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    return await controller.search_all_providers(
        user_id=user_id,
        query=query,
    )
