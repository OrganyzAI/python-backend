from typing import Optional
import re
from pydantic import BaseModel, EmailStr, validator
from app.utils_helper.regex import RegexClass
from app.utils_helper.messages import MSG


class LoginSchema(BaseModel):
    email: EmailStr
    password: str

    @validator('password')
    def password_strength(cls, v: str) -> str:
        if not RegexClass.is_strong_password(v):
            raise ValueError(MSG.VALIDATION["PASSWORD_TOO_WEAK"])
        return v


class RegisterSchema(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone_number : Optional[str] = None

    @validator('password')
    def password_strength(cls, v: str) -> str:
        if not RegexClass.is_strong_password(v):
            raise ValueError(MSG.VALIDATION["PASSWORD_TOO_WEAK"])
        return v
