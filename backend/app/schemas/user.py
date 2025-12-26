from pydantic import BaseModel, EmailStr, field_validator

from app.enums.user_enum import AuthProvider
from app.utils_helper.messages import MSG
from app.utils_helper.regex import RegexClass


class LoginSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not RegexClass.is_strong_password(v):
            raise ValueError(MSG.VALIDATION["PASSWORD_TOO_WEAK"])
        return v


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not RegexClass.is_strong_password(v):
            raise ValueError(MSG.VALIDATION["PASSWORD_TOO_WEAK"])
        return v


class ResendEmailSchema(BaseModel):
    email: EmailStr


class VerifySchema(BaseModel):
    token: str


class SocialLoginSchema(BaseModel):
    provider: str
    access_token: str

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed_providers = [provider.value for provider in AuthProvider]
        if v not in allowed_providers:
            raise ValueError(f"Provider must be one of {allowed_providers}")
        return v
