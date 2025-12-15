import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, Relationship, SQLModel
from app.enums.otp_enum import OTPType

class OTP(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    code: int = Field(nullable=False)
    type: OTPType = Field(nullable=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Many-to-one relationship
    user: Optional["User"] = Relationship(back_populates="otp")
