import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class ExternalAccount(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    user_id: uuid.UUID = Field(foreign_key="user.id", index=True, nullable=False)
    provider: str = Field(index=True)
    provider_account_id: str | None = Field(default=None, index=True)
    access_token: str | None = Field(default=None)
    refresh_token: str | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)
    extra_data: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # relationship back to user (optional)
    user: Optional["User"] = Relationship(back_populates=None)
