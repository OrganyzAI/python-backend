import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.enums.otp_enum import EmailTokenStatus

if TYPE_CHECKING:
    from app.models.user import User


class OTP(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", nullable=False, index=True)
    email_token: str = Field(nullable=False, unique=True, index=True)
    token_status: EmailTokenStatus = Field(
        default=EmailTokenStatus.active, nullable=False, index=True
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Many-to-one relationship
    user: Optional["User"] = Relationship(back_populates="otp")
