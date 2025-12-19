import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from app.enums.user_enum import UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.otp import OTP


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    email: EmailStr = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    status: UserStatus = Field(default=UserStatus.inactive)
    role: UserRole = Field(default=UserRole.user)
    token: str | None = Field(default=None, index=True, unique=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # One-to-many relationship
    otp: list["OTP"] = Relationship(back_populates="user")


# Pydantic/SQLModel helper schemas used by the tests and API
class UserBase(SQLModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(SQLModel):
    password: str | None = None
