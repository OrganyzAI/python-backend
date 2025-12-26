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


class GoogleDriveFileUpload(BaseModel):
    file_name: str = Field(..., description="Name of the file to upload")
    parent_folder_id: str | None = Field(
        None, description="Parent folder ID in Google Drive"
    )
    mime_type: str = Field(
        default="application/octet-stream",
        description="MIME type of the file",
    )


class GoogleDriveFileList(BaseModel):
    page_size: int = Field(
        default=100, ge=1, le=1000, description="Number of files per page"
    )
    page_token: str | None = Field(None, description="Token for pagination")
    query: str | None = Field(None, description="Query string to filter files")


class GoogleDriveFileUpdate(BaseModel):
    file_name: str | None = Field(None, description="New name for the file")
    mime_type: str | None = Field(None, description="MIME type of the file content")


class GoogleDriveTokenResponse(BaseModel):
    access_token: str = Field(..., description="Google OAuth access token")
    refresh_token: str | None = Field(None, description="Google OAuth refresh token")
    expires_in: int | None = Field(
        None, description="Access token expiration time in seconds"
    )
    refresh_token_expires_in: int | None = Field(
        None, description="Refresh token expiration time in seconds"
    )
    token_type: str | None = Field(default="Bearer", description="Token type")
    scope: str | None = Field(None, description="OAuth scopes granted")
