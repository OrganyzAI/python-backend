from pydantic import BaseModel, EmailStr, validator

from app.utils_helper.messages import MSG
from app.utils_helper.regex import RegexClass


class LoginSchema(BaseModel):
    email: EmailStr
    password: str
    @validator('password')
    def password_strength(self, v: str) -> str:
        if not RegexClass.is_strong_password(v):
            raise ValueError(MSG.VALIDATION["PASSWORD_TOO_WEAK"])
        return v


class RegisterSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number: str | None = None

    @validator('password')
    def password_strength(self, v: str) -> str:
        if not RegexClass.is_strong_password(v):
            raise ValueError(MSG.VALIDATION["PASSWORD_TOO_WEAK"])
        return v


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str


class ResendEmailSchema(BaseModel):
    email: EmailStr


class VerifySchema(BaseModel):
    token: str
