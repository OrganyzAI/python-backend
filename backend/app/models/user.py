import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel
from app.enums.user_enum import UserRole

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr = Field(index=True, unique=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    phone_number: Optional[str] = None
    role: UserRole = Field(default=UserRole.user)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # One-to-many relationship
    otp: List["OTP"] = Relationship(back_populates="user")
