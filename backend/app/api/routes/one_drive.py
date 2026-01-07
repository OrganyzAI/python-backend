import uuid

from fastapi import APIRouter, Depends, File, Form
from fastapi.datastructures import UploadFile
from fastapi.responses import JSONResponse

from app.api.controllers.one_drive_controller import OneDriveController
from app.api.deps import get_current_user_id
from app.schemas.external_account import OneDriveTokenResponse

router = APIRouter(prefix="/one-drive", tags=["One Drive"])
controller = OneDriveController()


@router.post(
    "/connect/token",
)
async def connect_one_drive_with_tokens(
    token_response: OneDriveTokenResponse,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Connect One Drive account using OAuth token response directly"""
    return await controller.connect_one_drive_with_tokens(
        token_response=token_response,
        user_id=user_id,
    )


@router.get("/files/all")
async def get_all_files_with_tenants(
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Get all files organized by tenants"""
    return await controller.get_all_files_with_tenants(user_id=user_id)


@router.get("/tenants")
async def get_all_tenants(
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Get all tenants/sites"""
    return await controller.get_all_tenants(user_id=user_id)


@router.get("/tenants/{site_id}/files")
async def get_files_for_tenant(
    site_id: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Get all files for a specific tenant"""
    return await controller.get_files_for_tenant(user_id=user_id, site_id=site_id)


@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    file_name: str = Form(...),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Upload a file to One Drive"""
    return await controller.upload_file(user_id=user_id, file_name=file_name, file=file)
