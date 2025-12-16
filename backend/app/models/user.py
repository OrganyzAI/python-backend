from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from app.enums.user_enum import UserRole

if TYPE_CHECKING:
    from app.models.otp import OTP


class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    phone_number: str | None = None
    role: UserRole = Field(default=UserRole.user)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # One-to-many relationship
    otp: list[OTP] = Relationship(back_populates="user")


# Pydantic/SQLModel helper schemas used by the tests and API
class UserBase(SQLModel):
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(SQLModel):
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None
    phone_number: str | None = None
