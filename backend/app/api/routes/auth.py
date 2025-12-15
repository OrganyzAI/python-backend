from fastapi import APIRouter
from app.schemas.user import LoginSchema, RegisterSchema
from app.api.controllers.auth_controller import UserController

router = APIRouter(prefix="/auth", tags=["auth"])

controller = UserController()


@router.post("/login")
async def login(request: LoginSchema):
    return await controller.login(request)


@router.post("/register")
async def register(request: RegisterSchema):
    return await controller.register(request)

@router.post("/verify")
async def verify():
    return await controller.verify()

@router.post("/forgot-password")
async def forgot_password():
    return await controller.forgot_password()

@router.post("/reset-password")
async def reset_password():
    return await controller.reset_password()

@router.post("/resend-email")
async def resend_email():
    return await controller.resend_email()

@router.post("/logout")
async def logout():
    return await controller.logout()
