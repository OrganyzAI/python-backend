"""Tests for OneDriveController."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.datastructures import UploadFile
from fastapi.responses import JSONResponse

from app.api.controllers.one_drive_controller import OneDriveController
from app.core.exceptions import AppException
from app.models.external_account import ExternalAccount
from app.schemas.external_account import OneDriveTokenResponse


@pytest.fixture
def controller():
    """Create OneDriveController instance."""
    return OneDriveController()


@pytest.fixture
def test_user_id() -> uuid.UUID:
    """Return a test user ID."""
    return uuid.uuid4()


@pytest.fixture
def token_response() -> OneDriveTokenResponse:
    """Return a test token response."""
    return OneDriveTokenResponse(
        access_token="test_token",
        expires_in=3600,
        ext_expires_in=7200,
        token_type="Bearer",
        token_source="oauth",
    )


@pytest.fixture
def mock_external_account(test_user_id: uuid.UUID) -> ExternalAccount:
    """Return a mock ExternalAccount."""
    return ExternalAccount(
        id=uuid.uuid4(),
        user_id=test_user_id,
        provider="one_drive",
        access_token="test_token",
        provider_account_id="user_123",
    )


class TestConnectOneDriveWithTokens:
    """Test connect_one_drive_with_tokens method."""

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_success(
        self, controller, test_user_id, token_response, mock_external_account
    ):
        """Test successful OneDrive connection."""
        with patch.object(
            controller.service,
            "connect_one_drive_with_tokens",
            new_callable=AsyncMock,
            return_value=mock_external_account,
        ):
            response = await controller.connect_one_drive_with_tokens(
                token_response=token_response, user_id=test_user_id
            )

            assert isinstance(response, JSONResponse)
            response_data = response.body.decode()
            assert "success" in response_data
            assert "One Drive account connected successfully" in response_data

            controller.service.connect_one_drive_with_tokens.assert_called_once_with(
                access_token=token_response.access_token,
                expires_in=token_response.expires_in,
                ext_expires_in=token_response.ext_expires_in,
                token_source=token_response.token_source,
                token_type=token_response.token_type,
                user_id=test_user_id,
            )

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_error(
        self, controller, test_user_id, token_response
    ):
        """Test OneDrive connection with error."""
        error = ValueError("Invalid token")
        with patch.object(
            controller.service,
            "connect_one_drive_with_tokens",
            new_callable=AsyncMock,
            side_effect=error,
        ):
            response = await controller.connect_one_drive_with_tokens(
                token_response=token_response, user_id=test_user_id
            )

            assert isinstance(response, JSONResponse)
            response_data = response.body.decode()
            assert "success" in response_data
            assert response.status_code == 400


class TestGetAllFilesWithTenants:
    """Test get_all_files_with_tenants method."""

    @pytest.mark.asyncio
    async def test_get_all_files_with_tenants_success(self, controller, test_user_id):
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

        with patch.object(
            controller.service,
            "get_all_files_with_tenants",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await controller.get_all_files_with_tenants(user_id=test_user_id)

            assert isinstance(response, JSONResponse)
            response_data = response.body.decode()
            assert "success" in response_data
            assert "Successfully retrieved all files" in response_data

            controller.service.get_all_files_with_tenants.assert_called_once_with(
                user_id=test_user_id
            )

    @pytest.mark.asyncio
    async def test_get_all_files_with_tenants_error(self, controller, test_user_id):
        """Test get_all_files_with_tenants with error."""
        error = ValueError("Account not connected")
        with patch.object(
            controller.service,
            "get_all_files_with_tenants",
            new_callable=AsyncMock,
            side_effect=error,
        ):
            response = await controller.get_all_files_with_tenants(user_id=test_user_id)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 400


class TestGetAllTenants:
    """Test get_all_tenants method."""

    @pytest.mark.asyncio
    async def test_get_all_tenants_success(self, controller, test_user_id):
        """Test successful retrieval of all tenants."""
        mock_tenants = [
            {"id": "tenant-1", "name": "Personal OneDrive", "driveType": "personal"},
            {"id": "tenant-2", "name": "SharePoint Site", "driveType": "sharepoint"},
        ]

        with patch.object(
            controller.service,
            "get_all_tenants",
            new_callable=AsyncMock,
            return_value=mock_tenants,
        ):
            response = await controller.get_all_tenants(user_id=test_user_id)

            assert isinstance(response, JSONResponse)
            response_data = response.body.decode()
            assert "success" in response_data
            assert "Successfully retrieved all tenants" in response_data

            controller.service.get_all_tenants.assert_called_once_with(user_id=test_user_id)

    @pytest.mark.asyncio
    async def test_get_all_tenants_error(self, controller, test_user_id):
        """Test get_all_tenants with error."""
        error = ValueError("Account not connected")
        with patch.object(
            controller.service,
            "get_all_tenants",
            new_callable=AsyncMock,
            side_effect=error,
        ):
            response = await controller.get_all_tenants(user_id=test_user_id)

            assert isinstance(response, JSONResponse)
            assert response.status_code == 400


class TestGetFilesForTenant:
    """Test get_files_for_tenant method."""

    @pytest.mark.asyncio
    async def test_get_files_for_tenant_success(self, controller, test_user_id):
        """Test successful retrieval of files for tenant."""
        mock_files = [
            {"id": "file-1", "name": "test.txt"},
            {"id": "file-2", "name": "document.docx"},
        ]

        with patch.object(
            controller.service,
            "get_files_for_tenant",
            new_callable=AsyncMock,
            return_value=mock_files,
        ):
            response = await controller.get_files_for_tenant(
                user_id=test_user_id, site_id="site-123"
            )

            assert isinstance(response, JSONResponse)
            response_data = response.body.decode()
            assert "success" in response_data
            assert "Successfully retrieved files for tenant" in response_data

            controller.service.get_files_for_tenant.assert_called_once_with(
                user_id=test_user_id, site_id="site-123"
            )

    @pytest.mark.asyncio
    async def test_get_files_for_tenant_error(self, controller, test_user_id):
        """Test get_files_for_tenant with error."""
        error = ValueError("Account not connected")
        with patch.object(
            controller.service,
            "get_files_for_tenant",
            new_callable=AsyncMock,
            side_effect=error,
        ):
            response = await controller.get_files_for_tenant(
                user_id=test_user_id, site_id="site-123"
            )

            assert isinstance(response, JSONResponse)
            assert response.status_code == 400


class TestUploadFile:
    """Test upload_file method."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, controller, test_user_id):
        """Test successful file upload."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=b"test file content")
        mock_file.filename = "test.txt"

        mock_result = {
            "file_metadata": {"id": "file-123", "name": "test.txt"},
            "file_name": "test.txt",
            "file_id": "file-123",
        }

        with patch.object(
            controller.service,
            "upload_file_to_one_drive",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await controller.upload_file(
                user_id=test_user_id, file_name="test.txt", file=mock_file
            )

            assert isinstance(response, JSONResponse)
            response_data = response.body.decode()
            assert "success" in response_data
            assert "Successfully uploaded file" in response_data

            controller.service.upload_file_to_one_drive.assert_called_once_with(
                user_id=test_user_id, file_name="test.txt", file_content=b"test file content"
            )

    @pytest.mark.asyncio
    async def test_upload_file_error(self, controller, test_user_id):
        """Test file upload with error."""
        mock_file = MagicMock(spec=UploadFile)
        mock_file.read = AsyncMock(return_value=b"test file content")

        error = ValueError("Account not connected")
        with patch.object(
            controller.service,
            "upload_file_to_one_drive",
            new_callable=AsyncMock,
            side_effect=error,
        ):
            response = await controller.upload_file(
                user_id=test_user_id, file_name="test.txt", file=mock_file
            )

            assert isinstance(response, JSONResponse)
            assert response.status_code == 400


class TestControllerHelpers:
    """Test controller helper methods."""

    def test_success_response_with_dict(self, controller):
        """Test _success method with dict data."""
        data = {"message": "Custom message", "data": {"key": "value"}}
        response = controller._success(data=data, message="Default")

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        response_data = response.body.decode()
        assert "Custom message" in response_data or "Default" in response_data

    def test_success_response_with_sqlmodel(self, controller, mock_external_account):
        """Test _success method with SQLModel data."""
        response = controller._success(data=mock_external_account)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 200

    def test_error_response_with_exception(self, controller):
        """Test _error method with AppException."""
        exc = AppException(message="Test error", status_code=404)
        response = controller._error(message=exc)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 404
        response_data = response.body.decode()
        assert "Test error" in response_data

    def test_error_response_with_string(self, controller):
        """Test _error method with string message."""
        response = controller._error(message="Test error", status_code=500)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 500
        response_data = response.body.decode()
        assert "Test error" in response_data

    def test_error_response_with_errors(self, controller):
        """Test _error method with errors dict."""
        errors = {"field": ["Error message"]}
        response = controller._error(message="Validation error", errors=errors)

        assert isinstance(response, JSONResponse)
        assert response.status_code == 400

