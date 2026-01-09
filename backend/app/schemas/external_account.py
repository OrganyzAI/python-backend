from pydantic import BaseModel, Field


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


class OneDriveTokenResponse(BaseModel):
    access_token: str = Field(..., description="Microsoft OAuth access token")
    expires_in: int | None = Field(
        None, description="Access token expiration time in seconds"
    )
    ext_expires_in: int | None = Field(
        None, description="Extended access token expiration time in seconds"
    )
    token_type: str | None = Field(default="Bearer", description="Token type")
    token_source: str | None = Field(None, description="Token source")


class DropboxTokenResponse(BaseModel):
    access_token: str = Field(..., description="Dropbox OAuth access token")
    expires_in: str | None = Field(
        None, description="Access token expiration time in ISO 8601 format"
    )
    refresh_token: str | None = Field(None, description="Dropbox OAuth refresh token")
    scope: str | None = Field(None, description="OAuth scopes granted")
