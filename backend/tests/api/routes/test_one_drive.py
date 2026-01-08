"""Tests for OneDrive API routes."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.routes import one_drive
from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount
from app.models.user import User
from tests.conftest import authentication_token_from_email, client, db


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="onedrive_test@example.com",
        hashed_password="hashed",
        first_name="Test",
        last_name="User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user: User, db: Session) -> dict[str, str]:
    """Get authentication headers for test user."""
    return authentication_token_from_email(client, test_user.email, db)


@pytest.fixture
def one_drive_account(test_user: User, db: Session) -> ExternalAccount:
    """Create a OneDrive account for test user."""
    account = ExternalAccount(
        user_id=test_user.id,
        provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
        access_token="test_token",
        provider_account_id="user_123",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


class TestConnectOneDriveWithTokens:
    """Test POST /one-drive/connect/token endpoint."""

    def test_connect_one_drive_with_tokens_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        db: Session,
    ):
        """Test successful OneDrive connection."""
        token_data = {
            "access_token": "new_token",
            "expires_in": 3600,
            "ext_expires_in": 7200,
            "token_type": "Bearer",
            "token_source": "oauth",
        }

        mock_user_info = {"id": "user_123", "displayName": "Test User"}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_user_info

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch(
            "app.services.one_drive_service.httpx.AsyncClient", mock_client_class
        ):
            response = client.post(
                "/api/v1/one-drive/connect/token",
                json=token_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "One Drive account connected successfully" in data["message"]

    def test_connect_one_drive_with_tokens_missing_token(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        """Test connection with missing access token."""
        token_data = {}

        response = client.post(
            "/api/v1/one-drive/connect/token",
            json=token_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_connect_one_drive_with_tokens_unauthorized(self, client: TestClient):
        """Test connection without authentication."""
        token_data = {
            "access_token": "test_token",
        }

        response = client.post(
            "/api/v1/one-drive/connect/token",
            json=token_data,
        )

        assert response.status_code == 403  # Forbidden (no auth)


class TestGetAllFilesWithTenants:
    """Test GET /one-drive/files/all endpoint."""

    def test_get_all_files_with_tenants_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        one_drive_account: ExternalAccount,
    ):
        """Test successful retrieval of all files with tenants."""
        mock_result = {
            "tenants": [
                {
                    "tenant": {"id": "tenant-1", "name": "Test Tenant"},
                    "files": [{"id": "file-1", "name": "test.txt"}],
                    "file_count": 1,
                }
            ],
            "total_files": 1,
        }

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_result)
        with patch.object(
            one_drive.controller.service,
            "get_all_files_with_tenants",
            mock_service_method,
        ):
            response = client.get(
                "/api/v1/one-drive/files/all",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_all_files_with_tenants_unauthorized(self, client: TestClient):
        """Test retrieval without authentication."""
        response = client.get("/api/v1/one-drive/files/all")

        assert response.status_code == 403


class TestGetAllTenants:
    """Test GET /one-drive/tenants endpoint."""

    def test_get_all_tenants_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        one_drive_account: ExternalAccount,
    ):
        """Test successful retrieval of all tenants."""
        mock_tenants = [
            {"id": "tenant-1", "name": "Personal OneDrive", "driveType": "personal"},
            {"id": "tenant-2", "name": "SharePoint Site", "driveType": "sharepoint"},
        ]

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_tenants)
        with patch.object(
            one_drive.controller.service,
            "get_all_tenants",
            mock_service_method,
        ):
            response = client.get(
                "/api/v1/one-drive/tenants",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully retrieved all tenants" in data["message"]

    def test_get_all_tenants_unauthorized(self, client: TestClient):
        """Test retrieval without authentication."""
        response = client.get("/api/v1/one-drive/tenants")

        assert response.status_code == 403


class TestGetFilesForTenant:
    """Test GET /one-drive/tenants/{site_id}/files endpoint."""

    def test_get_files_for_tenant_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        one_drive_account: ExternalAccount,
    ):
        """Test successful retrieval of files for tenant."""
        mock_files = [
            {"id": "file-1", "name": "test.txt"},
            {"id": "file-2", "name": "document.docx"},
        ]

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_files)
        with patch.object(
            one_drive.controller.service,
            "get_files_for_tenant",
            mock_service_method,
        ):
            response = client.get(
                "/api/v1/one-drive/tenants/site-123/files",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully retrieved files for tenant" in data["message"]

    def test_get_files_for_tenant_unauthorized(self, client: TestClient):
        """Test retrieval without authentication."""
        response = client.get("/api/v1/one-drive/tenants/site-123/files")
        assert response.status_code == 403


class TestUploadFile:
    """Test POST /one-drive/upload/file endpoint."""

    def test_upload_file_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        one_drive_account: ExternalAccount,
    ):
        """Test successful file upload."""
        mock_result = {
            "file_metadata": {"id": "file-123", "name": "test.txt"},
            "file_name": "test.txt",
            "file_id": "file-123",
        }

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_result)
        with patch.object(
            one_drive.controller.service,
            "upload_file_to_one_drive",
            mock_service_method,
        ):
            # Create a test file
            files = {"file": ("test.txt", b"test file content", "text/plain")}
            data = {"file_name": "test.txt"}

            response = client.post(
                "/api/v1/one-drive/upload/file",
                headers=auth_headers,
                files=files,
                data=data,
            )

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True
            assert "Successfully uploaded file" in response_data["message"]

    def test_upload_file_missing_file_name(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        """Test upload with missing file name."""
        files = {"file": ("test.txt", b"test file content", "text/plain")}

        response = client.post(
            "/api/v1/one-drive/upload/file",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 422  # Validation error

    def test_upload_file_missing_file(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        """Test upload with missing file."""
        data = {"file_name": "test.txt"}

        response = client.post(
            "/api/v1/one-drive/upload/file",
            headers=auth_headers,
            data=data,
        )

        assert response.status_code == 422  # Validation error

    def test_upload_file_unauthorized(self, client: TestClient):
        """Test upload without authentication."""
        files = {"file": ("test.txt", b"test file content", "text/plain")}
        data = {"file_name": "test.txt"}

        response = client.post(
            "/api/v1/one-drive/upload/file",
            files=files,
            data=data,
        )

        assert response.status_code == 403
