from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.controllers.auth_controller import UserController
from app.schemas.user import (
    LoginSchema,
    ResendEmailSchema,
    ResetPasswordSchema,
    VerifySchema,
)

router = APIRouter(prefix="/auth", tags=["auth"])

controller = UserController()


@router.post("/login")
async def login(request: LoginSchema) -> JSONResponse:
    return await controller.login(request)


@router.post("/register")
async def register(request: LoginSchema) -> JSONResponse:
    return await controller.register(request)


@router.post("/verify")
async def verify(request: VerifySchema) -> JSONResponse:
    return await controller.verify(request)


@router.post("/resend-email")
async def resend_email(request: ResendEmailSchema) -> JSONResponse:
    return await controller.resend_email(request)


@router.post("/forgot-password")
async def forgot_password(request: ResendEmailSchema) -> JSONResponse:
    return await controller.forgot_password(request)


@router.post("/reset-password")
async def reset_password(request: ResetPasswordSchema) -> JSONResponse:
    return await controller.reset_password(request)


@router.post("/logout")
async def logout() -> JSONResponse:
    return await controller.logout()
