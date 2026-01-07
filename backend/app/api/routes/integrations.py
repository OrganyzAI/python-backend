import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.api.controllers.integrations_controller import IntegrationsController
from app.api.deps import get_current_user_id
from app.schemas.external_account import GoogleDriveTokenResponse

router = APIRouter(prefix="/google-drive", tags=["Google Drive"])
controller = IntegrationsController()


@router.post(
    "/token",
)
async def connect_google_drive_with_tokens(
    token_response: GoogleDriveTokenResponse,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Connect Google Drive account using OAuth token response directly"""
    return await controller.connect_google_drive_with_tokens(
        token_response=token_response, user_id=user_id
    )


@router.post(
    "/files/upload",
)
async def upload_file_to_google_drive(
    file: UploadFile = File(...),
    file_name: str = Form(...),
    mime_type: str = Form(default="application/octet-stream"),
    parent_folder_id: str | None = Form(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Upload a file to Google Drive"""
    file_content = await file.read()
    return await controller.upload_file_to_google_drive(
        user_id=user_id,
        file_name=file_name,
        file_content=file_content,
        mime_type=mime_type,
        parent_folder_id=parent_folder_id,
    )


@router.get(
    "/files",
)
async def list_google_drive_files(
    page_size: int = Query(default=100, ge=1, le=1000),
    page_token: str | None = Query(None),
    query: str | None = Query(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """List all files in Google Drive"""
    return await controller.list_google_drive_files(
        user_id=user_id,
        page_size=page_size,
        page_token=page_token,
        query=query,
    )


@router.get(
    "/files/{file_id}",
)
async def read_google_drive_file(
    file_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Read file content from Google Drive (returns base64 encoded content)"""
    return await controller.read_google_drive_file(
        user_id=user_id,
        file_id=file_id,
    )


@router.get(
    "/files/{file_id}/download",
    response_model=None,
)
async def download_google_drive_file(
    file_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> Response | JSONResponse:
    """Download file content from Google Drive as a streaming response"""
    return await controller.download_google_drive_file(
        user_id=user_id,
        file_id=file_id,
    )


@router.patch(
    "/files/{file_id}",
)
async def update_google_drive_file(
    file_id: str,
    file: UploadFile | None = File(None),
    file_name: str | None = Form(None),
    mime_type: str | None = Form(None),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Update file content and/or metadata in Google Drive"""
    file_content = None
    if file:
        file_content = await file.read()
        if not mime_type:
            mime_type = file.content_type or "application/octet-stream"

    return await controller.update_google_drive_file(
        user_id=user_id,
        file_id=file_id,
        file_content=file_content,
        file_name=file_name,
        mime_type=mime_type,
    )
