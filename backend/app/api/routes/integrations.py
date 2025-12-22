import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.controllers.integrations_controller import IntegrationsController
from app.api.deps import get_current_user_id
from app.schemas.external_account import ExternalAccountCreate, callback_request

router = APIRouter(prefix="/integrations", tags=["integrations"])
controller = IntegrationsController()


@router.post(
    "/connect",
)
async def connect_account(
    request: ExternalAccountCreate,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    return await controller.connect_account(request, user_id=user_id)


@router.get(
    "/google-drive/auth-url",
)
async def get_google_drive_auth_url(
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    return await controller.get_google_drive_auth_url(user_id=user_id)


@router.get(
    "/google-drive/callback",
)
async def google_drive_callback(
    request: callback_request,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JSONResponse:
    return await controller.google_drive_callback(
        code=request.code, state=request.state, user_id=user_id
    )
