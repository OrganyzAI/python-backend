"""Tests for OneDrive and Google Drive token response schemas."""

import pytest

from app.schemas.external_account import GoogleDriveTokenResponse, OneDriveTokenResponse


class TestOneDriveTokenResponse:
    """Test OneDriveTokenResponse schema."""

    def test_one_drive_token_response_required_fields(self):
        """Test OneDriveTokenResponse with required fields only."""
        token_response = OneDriveTokenResponse(access_token="test_token")
        assert token_response.access_token == "test_token"
        assert token_response.expires_in is None
        assert token_response.ext_expires_in is None
        assert token_response.token_type == "Bearer"
        assert token_response.token_source is None

    def test_one_drive_token_response_all_fields(self):
        """Test OneDriveTokenResponse with all fields."""
        token_response = OneDriveTokenResponse(
            access_token="test_token",
            expires_in=3600,
            ext_expires_in=7200,
            token_type="Bearer",
            token_source="oauth",
        )
        assert token_response.access_token == "test_token"
        assert token_response.expires_in == 3600
        assert token_response.ext_expires_in == 7200
        assert token_response.token_type == "Bearer"
        assert token_response.token_source == "oauth"

    def test_one_drive_token_response_default_token_type(self):
        """Test OneDriveTokenResponse defaults token_type to Bearer."""
        token_response = OneDriveTokenResponse(access_token="test_token")
        assert token_response.token_type == "Bearer"

    def test_one_drive_token_response_missing_access_token(self):
        """Test OneDriveTokenResponse raises error when access_token is missing."""
        with pytest.raises(Exception):  # Pydantic validation error
            OneDriveTokenResponse()


class TestGoogleDriveTokenResponse:
    """Test GoogleDriveTokenResponse schema."""

    def test_google_drive_token_response_required_fields(self):
        """Test GoogleDriveTokenResponse with required fields only."""
        token_response = GoogleDriveTokenResponse(access_token="test_token")
        assert token_response.access_token == "test_token"
        assert token_response.refresh_token is None
        assert token_response.expires_in is None
        assert token_response.refresh_token_expires_in is None
        assert token_response.token_type == "Bearer"
        assert token_response.scope is None

    def test_google_drive_token_response_all_fields(self):
        """Test GoogleDriveTokenResponse with all fields."""
        token_response = GoogleDriveTokenResponse(
            access_token="test_token",
            refresh_token="refresh_token",
            expires_in=3600,
            refresh_token_expires_in=86400,
            token_type="Bearer",
            scope="https://www.googleapis.com/auth/drive",
        )
        assert token_response.access_token == "test_token"
        assert token_response.refresh_token == "refresh_token"
        assert token_response.expires_in == 3600
        assert token_response.refresh_token_expires_in == 86400
        assert token_response.token_type == "Bearer"
        assert token_response.scope == "https://www.googleapis.com/auth/drive"

    def test_google_drive_token_response_default_token_type(self):
        """Test GoogleDriveTokenResponse defaults token_type to Bearer."""
        token_response = GoogleDriveTokenResponse(access_token="test_token")
        assert token_response.token_type == "Bearer"

    def test_google_drive_token_response_missing_access_token(self):
        """Test GoogleDriveTokenResponse raises error when access_token is missing."""
        with pytest.raises(Exception):  # Pydantic validation error
            GoogleDriveTokenResponse()

