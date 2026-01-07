"""Tests for Dropbox API routes."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.api.routes import dropbox
from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount
from app.models.user import User
from tests.conftest import authentication_token_from_email, client, db


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="dropbox_test@example.com",
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
def dropbox_account(test_user: User, db: Session) -> ExternalAccount:
    """Create a Dropbox account for test user."""
    account = ExternalAccount(
        user_id=test_user.id,
        provider=EXTERNAL_ACCOUNT_PROVIDER.DROPBOX,
        access_token="test_token",
        provider_account_id="user_123",
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


class TestConnectDropboxWithTokens:
    """Test POST /dropbox/connect/token endpoint."""

    def test_connect_dropbox_with_tokens_success(
        self, client: TestClient, auth_headers: dict[str, str], test_user: User, db: Session
    ):
        """Test successful Dropbox connection."""
        token_data = {
            "access_token": "new_token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "refresh_token": "refresh_token",
            "scope": "files.content.read files.content.write",
        }

        mock_user_info = {"account_id": "user_123", "name": {"display_name": "Test User"}}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_user_info

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.dropbox_service.httpx.AsyncClient", mock_client_class):
            response = client.post(
                "/api/v1/dropbox/connect/token",
                json=token_data,
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Dropbox account connected successfully" in data["message"]

    def test_connect_dropbox_with_tokens_missing_token(
        self, client: TestClient, auth_headers: dict[str, str]
    ):
        """Test connection with missing access token."""
        token_data = {}

        response = client.post(
            "/api/v1/dropbox/connect/token",
            json=token_data,
            headers=auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_connect_dropbox_with_tokens_unauthorized(
        self, client: TestClient
    ):
        """Test connection without authentication."""
        token_data = {
            "access_token": "test_token",
        }

        response = client.post(
            "/api/v1/dropbox/connect/token",
            json=token_data,
        )

        assert response.status_code == 403  # Forbidden (no auth)


class TestGetAllFilesWithNamespaces:
    """Test GET /dropbox/files/all endpoint."""

    def test_get_all_files_with_namespaces_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        dropbox_account: ExternalAccount,
    ):
        """Test successful retrieval of all files with namespaces."""
        mock_result = {
            "namespaces": [
                {
                    "namespace": {"namespace_id": "namespace-1", "name": "Test Namespace"},
                    "files": [{"id": "file-1", "name": "test.txt"}],
                    "file_count": 1,
                }
            ],
            "total_files": 1,
        }

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_result)
        with patch.object(
            dropbox.controller.service,
            "get_all_files_with_namespaces",
            mock_service_method,
        ):
            response = client.get(
                "/api/v1/dropbox/files/all",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_all_files_with_namespaces_unauthorized(self, client: TestClient):
        """Test retrieval without authentication."""
        response = client.get("/api/v1/dropbox/files/all")

        assert response.status_code == 403


class TestGetAllNamespaces:
    """Test GET /dropbox/namespaces endpoint."""

    def test_get_all_namespaces_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        dropbox_account: ExternalAccount,
    ):
        """Test successful retrieval of all namespaces."""
        mock_namespaces = [
            {"namespace_id": "namespace-1", "name": "Personal Dropbox", "namespace_type": "personal"},
            {"namespace_id": "namespace-2", "name": "Team Namespace", "namespace_type": "team"},
        ]

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_namespaces)
        with patch.object(
            dropbox.controller.service,
            "get_all_namespaces",
            mock_service_method,
        ):
            response = client.get(
                "/api/v1/dropbox/namespaces",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully retrieved all namespaces" in data["message"]

    def test_get_all_namespaces_unauthorized(self, client: TestClient):
        """Test retrieval without authentication."""
        response = client.get("/api/v1/dropbox/namespaces")

        assert response.status_code == 403


class TestGetFilesForNamespace:
    """Test GET /dropbox/namespaces/{namespace_id}/files endpoint."""

    def test_get_files_for_namespace_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        dropbox_account: ExternalAccount,
    ):
        """Test successful retrieval of files for namespace."""
        mock_files = [
            {"id": "file-1", "name": "test.txt"},
            {"id": "file-2", "name": "document.docx"},
        ]

        # Patch the service method on the controller instance
        mock_service_method = AsyncMock(return_value=mock_files)
        with patch.object(
            dropbox.controller.service,
            "get_files_for_namespace",
            mock_service_method,
        ):
            response = client.get(
                "/api/v1/dropbox/namespaces/namespace-123/files",
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully retrieved files for namespace" in data["message"]

    def test_get_files_for_namespace_unauthorized(self, client: TestClient):
        """Test retrieval without authentication."""
        response = client.get("/api/v1/dropbox/namespaces/namespace-123/files")
        assert response.status_code == 403


class TestUploadFile:
    """Test POST /dropbox/upload/file endpoint."""

    def test_upload_file_success(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        test_user: User,
        dropbox_account: ExternalAccount,
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
            dropbox.controller.service,
            "upload_file_to_dropbox",
            mock_service_method,
        ):
            # Create a test file
            files = {"file": ("test.txt", b"test file content", "text/plain")}
            data = {"file_name": "test.txt"}

            response = client.post(
                "/api/v1/dropbox/upload/file",
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
            "/api/v1/dropbox/upload/file",
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
            "/api/v1/dropbox/upload/file",
            headers=auth_headers,
            data=data,
        )

        assert response.status_code == 422  # Validation error

    def test_upload_file_unauthorized(self, client: TestClient):
        """Test upload without authentication."""
        files = {"file": ("test.txt", b"test file content", "text/plain")}
        data = {"file_name": "test.txt"}

        response = client.post(
            "/api/v1/dropbox/upload/file",
            files=files,
            data=data,
        )

        assert response.status_code == 403

