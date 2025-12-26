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
