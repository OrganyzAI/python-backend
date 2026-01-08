import uuid

from fastapi import APIRouter, Depends, File, Form, Query
from fastapi.datastructures import UploadFile
from fastapi.responses import JSONResponse

from app.api.controllers.dropbox_controller import DropboxController
from app.api.deps import get_current_user_id
from app.schemas.external_account import DropboxTokenResponse

router = APIRouter(prefix="/dropbox", tags=["Dropbox"])
controller = DropboxController()


@router.get("/authorization-url")
async def get_authorization_url(
    state: str | None = Query(None, description="OAuth state parameter"),
) -> JSONResponse:
    """Get Dropbox OAuth authorization URL"""
    return controller.get_authorization_url(state=state)


@router.post(
    "/connect/token",
)
async def connect_dropbox_with_tokens(
    token_response: DropboxTokenResponse,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Connect Dropbox account using OAuth token response directly"""
    return await controller.connect_dropbox_with_tokens(
        token_response=token_response,
        user_id=user_id,
    )


@router.get("/files/all")
async def get_all_files_with_namespaces(
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Get all files organized by namespaces"""
    return await controller.get_all_files_with_namespaces(user_id=user_id)


@router.get("/namespaces")
async def get_all_namespaces(
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Get all namespaces"""
    return await controller.get_all_namespaces(user_id=user_id)


@router.get("/namespaces/{namespace_id}/files")
async def get_files_for_namespace(
    namespace_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Get all files for a specific namespace"""
    return await controller.get_files_for_namespace(
        user_id=user_id, namespace_id=namespace_id
    )


@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    file_name: str = Form(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Upload a file to Dropbox"""
    return await controller.upload_file(user_id=user_id, file_name=file_name, file=file)
