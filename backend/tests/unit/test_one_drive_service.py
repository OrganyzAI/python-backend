"""Tests for OneDriveService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session

from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount
from app.models.user import User
from app.services.one_drive_service import OneDriveService
from tests.conftest import db


@pytest.fixture
def service():
    """Create OneDriveService instance."""
    return OneDriveService()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email=f"test_onedrive_service_{uuid.uuid4()}@example.com",
        hashed_password="hashed",
        first_name="Test",
        last_name="User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_access_token() -> str:
    """Return a test access token."""
    return "test_access_token_123"


class TestConnectOneDriveWithTokens:
    """Test connect_one_drive_with_tokens method."""

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_missing_access_token(self, service):
        """Test that missing access token raises ValueError."""
        with pytest.raises(ValueError, match="Access token is required"):
            await service.connect_one_drive_with_tokens(
                access_token="", user_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_missing_user_id(self, service):
        """Test that missing user_id raises ValueError."""
        with pytest.raises(ValueError, match="User ID is required"):
            await service.connect_one_drive_with_tokens(
                access_token="test_token", user_id=None
            )

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_new_account(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test creating a new OneDrive account."""
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

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            account = await service.connect_one_drive_with_tokens(
                access_token=test_access_token,
                expires_in=3600,
                ext_expires_in=7200,
                token_type="Bearer",
                token_source="oauth",
                user_id=test_user.id,
                session=db,
            )

            assert account is not None
            assert account.user_id == test_user.id
            assert account.provider == EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE
            assert account.access_token == test_access_token
            assert account.provider_account_id == "user_123"
            assert account.expires_at is not None
            assert account.extra_data is not None
            assert account.extra_data.get("id") == "user_123"
            assert account.extra_data.get("displayName") == "Test User"

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_update_existing(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test updating an existing OneDrive account."""
        # Create existing account
        existing_account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            provider_account_id="old_id",
            access_token="old_token",
        )
        db.add(existing_account)
        db.commit()
        db.refresh(existing_account)

        mock_user_info = {"id": "new_user_123", "displayName": "Updated User"}

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

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            account = await service.connect_one_drive_with_tokens(
                access_token="new_token",
                expires_in=3600,
                user_id=test_user.id,
                session=db,
            )

            assert account.id == existing_account.id
            assert account.access_token == "new_token"
            assert account.provider_account_id == "new_user_123"
            assert account.updated_at > existing_account.updated_at

    @pytest.mark.asyncio
    async def test_connect_one_drive_with_tokens_user_info_failure(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test handling when user info API call fails."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            account = await service.connect_one_drive_with_tokens(
                access_token=test_access_token,
                user_id=test_user.id,
                session=db,
            )

            # Should still create account even if user info fails
            assert account is not None
            assert account.user_id == test_user.id
            assert account.provider_account_id is None


class TestGetOneDriveUserInfo:
    """Test _get_one_drive_user_info method."""

    @pytest.mark.asyncio
    async def test_get_one_drive_user_info_success(self, service):
        """Test successful user info retrieval."""
        mock_user_info = {"id": "user_123", "displayName": "Test User", "mail": "test@example.com"}

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

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            result = await service._get_one_drive_user_info("test_token")

            assert result == mock_user_info
            mock_client_instance.get.assert_called_once_with(
                "https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": "Bearer test_token"},
            )

    @pytest.mark.asyncio
    async def test_get_one_drive_user_info_failure(self, service):
        """Test user info retrieval failure."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            result = await service._get_one_drive_user_info("test_token")

            assert result == {}


class TestEnsureValidToken:
    """Test _ensure_valid_token method."""

    @pytest.mark.asyncio
    async def test_ensure_valid_token_valid_token(self, service, test_user, db: Session):
        """Test with valid, non-expired token."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token="valid_token",
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        token = await service._ensure_valid_token(account, session=db)
        assert token == "valid_token"

    @pytest.mark.asyncio
    async def test_ensure_valid_token_no_refresh_token(self, service, test_user, db: Session):
        """Test with expired token but no refresh token."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token="expired_token",
            expires_at=datetime.utcnow() - timedelta(hours=1),
            refresh_token=None,
        )
        db.add(account)
        db.commit()

        with pytest.raises(ValueError, match="No refresh token available"):
            await service._ensure_valid_token(account, session=db)

    @pytest.mark.asyncio
    async def test_ensure_valid_token_no_access_token(self, service, test_user, db: Session):
        """Test with no access token."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=None,
            expires_at=None,
        )
        db.add(account)
        db.commit()

        with pytest.raises(ValueError, match="No access token available"):
            await service._ensure_valid_token(account, session=db)


class TestGetOneDriveAccount:
    """Test get_one_drive_account method."""

    @pytest.mark.asyncio
    async def test_get_one_drive_account_exists(self, service, test_user, db: Session):
        """Test retrieving existing OneDrive account."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token="test_token",
        )
        db.add(account)
        db.commit()

        result = await service.get_one_drive_account(test_user.id, session=db)
        assert result is not None
        assert result.id == account.id
        assert result.access_token == "test_token"

    @pytest.mark.asyncio
    async def test_get_one_drive_account_not_exists(self, service, test_user):
        """Test retrieving non-existent OneDrive account."""
        result = await service.get_one_drive_account(test_user.id)
        assert result is None


class TestGetAllTenants:
    """Test get_all_tenants method."""

    @pytest.mark.asyncio
    async def test_get_all_tenants_success(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test successful retrieval of all tenants."""
        # Create account
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=test_access_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        # Mock personal OneDrive response
        mock_drive_response = MagicMock()
        mock_drive_response.status_code = 200
        mock_drive_response.json.return_value = {
            "id": "drive-123",
            "webUrl": "https://onedrive.live.com",
        }

        # Mock sites response
        mock_sites_response = MagicMock()
        mock_sites_response.status_code = 200
        mock_sites_response.json.return_value = {
            "value": [
                {
                    "id": "site-123",
                    "name": "Test Site",
                    "webUrl": "https://test.sharepoint.com",
                }
            ]
        }

        # Mock site drive response
        mock_site_drive_response = MagicMock()
        mock_site_drive_response.status_code = 200
        mock_site_drive_response.json.return_value = {"id": "site-drive-123"}

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=[
                mock_drive_response,  # Personal OneDrive
                mock_sites_response,  # Sites list
                mock_site_drive_response,  # Site drive
            ]
        )

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            tenants = await service.get_all_tenants(test_user.id, session=db)

            assert len(tenants) >= 1
            # Check personal OneDrive
            personal = next((t for t in tenants if t.get("driveType") == "personal"), None)
            assert personal is not None
            assert personal["id"] == "drive-123"

    @pytest.mark.asyncio
    async def test_get_all_tenants_no_account(self, service, test_user):
        """Test get_all_tenants when account doesn't exist."""
        with pytest.raises(ValueError, match="OneDrive account not connected"):
            await service.get_all_tenants(test_user.id)


class TestGetFilesForTenant:
    """Test get_files_for_tenant method."""

    @pytest.mark.asyncio
    async def test_get_files_for_tenant_personal_drive(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test getting files from personal OneDrive."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=test_access_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "file-1",
                    "name": "test.txt",
                    "file": {"mimeType": "text/plain"},
                },
                {
                    "id": "folder-1",
                    "name": "folder",
                    "folder": {},
                },
            ]
        }

        # Mock folder contents
        mock_folder_response = MagicMock()
        mock_folder_response.status_code = 200
        mock_folder_response.json.return_value = {
            "value": [
                {
                    "id": "file-2",
                    "name": "nested.txt",
                    "file": {"mimeType": "text/plain"},
                }
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=[mock_response, mock_folder_response]
        )

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            files = await service.get_files_for_tenant(
                test_user.id, "personal", session=db
            )

            assert len(files) >= 2  # At least root files

    @pytest.mark.asyncio
    async def test_get_files_for_tenant_sharepoint_site(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test getting files from SharePoint site."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=test_access_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": [
                {
                    "id": "file-1",
                    "name": "document.docx",
                    "file": {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
                }
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            files = await service.get_files_for_tenant(
                test_user.id, "site-123", session=db
            )

            assert len(files) >= 1

    @pytest.mark.asyncio
    async def test_get_files_for_tenant_no_account(self, service, test_user):
        """Test get_files_for_tenant when account doesn't exist."""
        with pytest.raises(ValueError, match="OneDrive account not connected"):
            await service.get_files_for_tenant(test_user.id, "site-123")


class TestGetAllFilesWithTenants:
    """Test get_all_files_with_tenants method."""

    @pytest.mark.asyncio
    async def test_get_all_files_with_tenants_success(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test successful retrieval of all files with tenants."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=test_access_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        # Mock responses for get_all_tenants
        mock_drive_response = MagicMock()
        mock_drive_response.status_code = 200
        mock_drive_response.json.return_value = {
            "id": "drive-123",
            "webUrl": "https://onedrive.live.com",
        }

        mock_sites_response = MagicMock()
        mock_sites_response.status_code = 200
        mock_sites_response.json.return_value = {"value": []}

        # Mock responses for get_files_for_tenant
        mock_files_response = MagicMock()
        mock_files_response.status_code = 200
        mock_files_response.json.return_value = {
            "value": [
                {
                    "id": "file-1",
                    "name": "test.txt",
                    "file": {},
                }
            ]
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.get = AsyncMock(
            side_effect=[
                mock_drive_response,  # Personal OneDrive
                mock_sites_response,  # Sites (empty)
                mock_files_response,  # Files for personal drive
            ]
        )

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            result = await service.get_all_files_with_tenants(test_user.id, session=db)

            assert "tenants" in result
            assert "total_files" in result
            assert isinstance(result["tenants"], list)
            assert result["total_files"] >= 0


class TestUploadFileToOneDrive:
    """Test upload_file_to_one_drive method."""

    @pytest.mark.asyncio
    async def test_upload_file_to_one_drive_success(
        self, service, test_user, test_access_token, db: Session
    ):
        """Test successful file upload."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=test_access_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "id": "file-123",
            "name": "test.txt",
            "webUrl": "https://onedrive.live.com/test.txt",
        }

        mock_client_instance = AsyncMock()
        mock_client_instance.put = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            result = await service.upload_file_to_one_drive(
                user_id=test_user.id,
                file_name="test.txt",
                file_content=b"test content",
            )

            assert "file_metadata" in result
            assert result["file_name"] == "test.txt"
            assert result["file_id"] == "file-123"

    @pytest.mark.asyncio
    async def test_upload_file_to_one_drive_failure(self, service, test_user, test_access_token, db: Session):
        """Test file upload failure."""
        account = ExternalAccount(
            user_id=test_user.id,
            provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            access_token=test_access_token,
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(account)
        db.commit()

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_client_instance = AsyncMock()
        mock_client_instance.put = AsyncMock(return_value=mock_response)

        class AsyncContextManager:
            async def __aenter__(self):
                return mock_client_instance

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return False

        mock_client_class = MagicMock(return_value=AsyncContextManager())

        with patch("app.services.one_drive_service.httpx.AsyncClient", mock_client_class):
            with pytest.raises(ValueError, match="Failed to upload file"):
                await service.upload_file_to_one_drive(
                    user_id=test_user.id,
                    file_name="test.txt",
                    file_content=b"test content",
                )

    @pytest.mark.asyncio
    async def test_upload_file_to_one_drive_no_account(self, service, test_user):
        """Test upload when account doesn't exist."""
        with pytest.raises(ValueError, match="OneDrive account not connected"):
            await service.upload_file_to_one_drive(
                user_id=test_user.id,
                file_name="test.txt",
                file_content=b"test content",
            )

