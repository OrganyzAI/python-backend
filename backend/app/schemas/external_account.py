from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER


class ExternalAccountCreate(BaseModel):
    provider: EXTERNAL_ACCOUNT_PROVIDER
    provider_account_id: str | None = None
    access_token: str | None = None
    refresh_token: str | None = None
    expires_at: datetime | None = None
    extra_data: dict[str, Any] | None = None


class ExternalAccountRead(BaseModel):
    id: str
    user_id: str
    provider: EXTERNAL_ACCOUNT_PROVIDER
    provider_account_id: str | None = None
    extra_data: dict[str, Any] | None = None
    created_at: datetime | None = None


class GoogleDriveAccountRead(BaseModel):
    id: str
    user_id: str
    provider: EXTERNAL_ACCOUNT_PROVIDER
    provider_account_id: str | None = None
    extra_data: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class callback_request(BaseModel):
    code: str = Field(..., description="Authorization code from Google")
    state: str | None = Field(None, description="State parameter for OAuth")
