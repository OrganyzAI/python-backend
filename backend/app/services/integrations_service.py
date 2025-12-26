import base64
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_engine
from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount

logger = logging.getLogger(__name__)


class IntegrationService:
    async def connect_account(
        self,
        user_id: uuid.UUID,
        provider: str,
        provider_account_id: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        extra_data: dict[str, Any] | None = None,
        session: Session | None = None,
    ) -> ExternalAccount:
        own = False
        if session is None:
            session = Session(get_engine())
            own = True
        account = ExternalAccount(
            user_id=user_id,
            provider=provider,
            provider_account_id=provider_account_id,
            access_token=access_token,
            refresh_token=refresh_token,
            extra_data=extra_data,
        )
        try:
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
        finally:
            if own:
                session.close()

    def get_google_drive_auth_url(self, user_id: uuid.UUID) -> dict[str, str]:
        """Generate Google Drive OAuth2 authorization URL"""
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_REDIRECT_URI:
            raise ValueError("Google OAuth2 credentials not configured")
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
        ]
        state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": settings.GOOGLE_DRIVE_RESPONSE_TYPE or "code",
            "scope": " ".join(scopes),
            "access_type": settings.GOOGLE_DRIVE_ACCESS_TYPE or "offline",
            "prompt": settings.GOOGLE_DRIVE_PROMPT or "consent",
            "state": state,
        }

        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

        return {
            "auth_url": auth_url,
            "state": state,
        }

    async def exchange_google_drive_code(
        self,
        code: str,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> ExternalAccount:
        """Exchange authorization code for access token and refresh token"""
        if (
            not settings.GOOGLE_CLIENT_ID
            or not settings.GOOGLE_CLIENT_SECRET
            or not settings.GOOGLE_REDIRECT_URI
        ):
            raise ValueError("Google OAuth2 credentials not configured")

        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(token_url, data=token_data)
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to exchange Google Drive code: {error_detail}")
                raise ValueError(
                    f"Failed to exchange authorization code: {error_detail}"
                )

            token_response = response.json()

        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Get user info from Google
        user_info = await self._get_google_user_info(access_token)
        provider_account_id = user_info.get("id") or user_info.get("sub")

        # Check if account already exists
        own = False
        if session is None:
            session = Session(get_engine())
            own = True

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.GOOGLE_DRIVE,
            )
            existing_account = session.exec(stmt).first()

            if existing_account:
                # Update existing account
                existing_account.access_token = access_token
                existing_account.refresh_token = (
                    refresh_token or existing_account.refresh_token
                )
                existing_account.expires_at = expires_at
                existing_account.provider_account_id = provider_account_id
                existing_account.extra_data = user_info
                existing_account.updated_at = datetime.utcnow()
                session.add(existing_account)
                session.commit()
                session.refresh(existing_account)
                return existing_account
            else:
                # Create new account
                account = ExternalAccount(
                    user_id=user_id,
                    provider=EXTERNAL_ACCOUNT_PROVIDER.GOOGLE_DRIVE,
                    provider_account_id=provider_account_id,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    extra_data=user_info,
                )
                session.add(account)
                session.commit()
                session.refresh(account)
                return account
        finally:
            if own:
                session.close()

    async def connect_google_drive_with_tokens(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None = None,
        scope: str | None = None,
        user_id: uuid.UUID | None = None,
        session: Session | None = None,
    ) -> ExternalAccount:
        """Connect Google Drive account using provided tokens directly"""
        if not access_token:
            raise ValueError("Access token is required")

        # Calculate expiration time
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Get user info from Google
        user_info = await self._get_google_user_info(access_token)
        provider_account_id = user_info.get("id") or user_info.get("sub")

        # Add token info to extra_data
        token_info = {
            "scope": scope,
            "token_type": "Bearer",
        }
        if user_info:
            user_info.update(token_info)
        else:
            user_info = token_info

        # User ID is required
        if not user_id:
            raise ValueError("User ID is required")

        # Check if account already exists
        own = False
        if session is None:
            session = Session(get_engine())
            own = True

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.GOOGLE_DRIVE,
            )
            existing_account = session.exec(stmt).first()

            if existing_account:
                # Update existing account
                existing_account.access_token = access_token
                existing_account.refresh_token = (
                    refresh_token or existing_account.refresh_token
                )
                existing_account.expires_at = expires_at
                existing_account.provider_account_id = provider_account_id
                existing_account.extra_data = user_info
                existing_account.updated_at = datetime.utcnow()
                session.add(existing_account)
                session.commit()
                session.refresh(existing_account)
                return existing_account

            # Create new account
            account = ExternalAccount(
                user_id=user_id,
                provider=EXTERNAL_ACCOUNT_PROVIDER.GOOGLE_DRIVE,
                provider_account_id=provider_account_id,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
                extra_data=user_info,
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
        finally:
            if own:
                session.close()

    async def _get_google_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Google using access token"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                logger.error(f"Failed to get Google user info: {response.text}")
                return {}
            result: dict[str, Any] = response.json()
            return result

    async def refresh_google_drive_token(
        self,
        account: ExternalAccount,
        session: Session | None = None,
    ) -> ExternalAccount:
        """Refresh Google Drive access token using refresh token"""
        if not account.refresh_token:
            raise ValueError("No refresh token available")

        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth2 credentials not configured")

        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "refresh_token": account.refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(token_url, data=token_data)
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to refresh Google Drive token: {error_detail}")
                raise ValueError(f"Failed to refresh token: {error_detail}")

            token_response = response.json()

        access_token = token_response.get("access_token")
        expires_in = token_response.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        own = False
        if session is None:
            session = Session(get_engine())
            own = True

        try:
            account.access_token = access_token
            account.expires_at = expires_at
            account.updated_at = datetime.utcnow()
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
        finally:
            if own:
                session.close()

    async def get_google_drive_account(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> ExternalAccount | None:
        """Get Google Drive account for user"""
        own = False
        if session is None:
            session = Session(get_engine())
            own = True

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.GOOGLE_DRIVE,
            )
            account = session.exec(stmt).first()
            return account
        finally:
            if own:
                session.close()

    async def _ensure_valid_token(
        self, account: ExternalAccount, session: Session | None = None
    ) -> str:
        """Ensure access token is valid, refresh if needed"""
        if account.expires_at and account.expires_at <= datetime.utcnow():
            if account.refresh_token:
                account = await self.refresh_google_drive_token(
                    account, session=session
                )
            else:
                raise ValueError("Access token expired and no refresh token available")
        if not account.access_token:
            raise ValueError("No access token available")
        return account.access_token

    async def upload_file_to_google_drive(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file_content: bytes,
        mime_type: str = "application/octet-stream",
        parent_folder_id: str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Upload a file to Google Drive"""
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        # Upload file metadata first
        metadata = {
            "name": file_name,
        }
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]

        # Create multipart upload
        boundary = secrets.token_urlsafe(16)
        body_parts = []

        # Metadata part
        body_parts.append(
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
        )

        # File content part
        body_parts.append(f"--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n")
        body_parts.append(file_content)
        body_parts.append(f"\r\n--{boundary}--\r\n")

        body = b"".join(
            part.encode("utf-8") if isinstance(part, str) else part
            for part in body_parts
        )

        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, content=body)
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to upload file to Google Drive: {error_detail}")
                raise ValueError(f"Failed to upload file: {error_detail}")

            return response.json()

    async def list_google_drive_files(
        self,
        user_id: uuid.UUID,
        page_size: int = 100,
        page_token: str | None = None,
        query: str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """List all files in Google Drive"""
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        params: dict[str, Any] = {
            "pageSize": page_size,
            "fields": "nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink)",
        }
        if page_token:
            params["pageToken"] = page_token
        if query:
            params["q"] = query

        url = "https://www.googleapis.com/drive/v3/files"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to list Google Drive files: {error_detail}")
                raise ValueError(f"Failed to list files: {error_detail}")

            return response.json()

    async def read_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Read file content from Google Drive"""
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        # First get file metadata
        metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        metadata_headers = {"Authorization": f"Bearer {access_token}"}
        metadata_params = {
            "fields": "id, name, mimeType, size, createdTime, modifiedTime, webViewLink"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            metadata_response = await client.get(
                metadata_url, headers=metadata_headers, params=metadata_params
            )
            if metadata_response.status_code != 200:
                error_detail = metadata_response.text
                logger.error(
                    f"Failed to get Google Drive file metadata: {error_detail}"
                )
                raise ValueError(f"Failed to get file metadata: {error_detail}")

            file_metadata = metadata_response.json()

            # Get file content
            content_url = (
                f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            )
            content_headers = {"Authorization": f"Bearer {access_token}"}

            content_response = await client.get(content_url, headers=content_headers)
            if content_response.status_code != 200:
                error_detail = content_response.text
                logger.error(f"Failed to read Google Drive file: {error_detail}")
                raise ValueError(f"Failed to read file: {error_detail}")

            content_type = content_response.headers.get(
                "Content-Type", "application/octet-stream"
            )
            # Base64 encode content for JSON response
            content_base64 = base64.b64encode(content_response.content).decode("utf-8")

            return {
                "metadata": file_metadata,
                "content": content_base64,
                "content_type": content_type,
                "size": len(content_response.content),
            }

    async def download_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
        session: Session | None = None,
    ) -> tuple[bytes, str, dict[str, Any]]:
        """Download file content from Google Drive (returns raw bytes for streaming)"""
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        # Get file metadata
        metadata_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
        metadata_headers = {"Authorization": f"Bearer {access_token}"}
        metadata_params = {
            "fields": "id, name, mimeType, size, createdTime, modifiedTime"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            metadata_response = await client.get(
                metadata_url, headers=metadata_headers, params=metadata_params
            )
            if metadata_response.status_code != 200:
                error_detail = metadata_response.text
                logger.error(
                    f"Failed to get Google Drive file metadata: {error_detail}"
                )
                raise ValueError(f"Failed to get file metadata: {error_detail}")

            file_metadata = metadata_response.json()

            # Get file content
            content_url = (
                f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
            )
            content_headers = {"Authorization": f"Bearer {access_token}"}

            content_response = await client.get(content_url, headers=content_headers)
            if content_response.status_code != 200:
                error_detail = content_response.text
                logger.error(f"Failed to download Google Drive file: {error_detail}")
                raise ValueError(f"Failed to download file: {error_detail}")

            content_type = content_response.headers.get(
                "Content-Type", "application/octet-stream"
            )

            return (
                content_response.content,
                content_type,
                file_metadata,
            )

    async def update_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
        file_content: bytes | None = None,
        file_name: str | None = None,
        mime_type: str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Update file content and/or metadata in Google Drive"""
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        # If updating both content and metadata, use multipart upload
        if file_content is not None and (
            file_name is not None or mime_type is not None
        ):
            metadata: dict[str, Any] = {}
            if file_name:
                metadata["name"] = file_name

            boundary = secrets.token_urlsafe(16)
            body_parts = []

            # Metadata part
            if metadata:
                body_parts.append(
                    f"--{boundary}\r\n"
                    f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                    f"{json.dumps(metadata)}\r\n"
                )

            # File content part
            content_type = mime_type or "application/octet-stream"
            body_parts.append(f"--{boundary}\r\nContent-Type: {content_type}\r\n\r\n")
            body_parts.append(file_content)
            body_parts.append(f"\r\n--{boundary}--\r\n")

            body = b"".join(
                part.encode("utf-8") if isinstance(part, str) else part
                for part in body_parts
            )

            url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=multipart"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.patch(url, headers=headers, content=body)
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Failed to update Google Drive file: {error_detail}")
                    raise ValueError(f"Failed to update file: {error_detail}")

                return response.json()

        # If only updating content
        elif file_content is not None:
            url = f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": mime_type or "application/octet-stream",
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.patch(
                    url, headers=headers, content=file_content
                )
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"Failed to update Google Drive file content: {error_detail}"
                    )
                    raise ValueError(f"Failed to update file content: {error_detail}")

                return response.json()

        # If only updating metadata
        elif file_name is not None:
            metadata = {"name": file_name}
            url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.patch(url, headers=headers, json=metadata)
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"Failed to update Google Drive file metadata: {error_detail}"
                    )
                    raise ValueError(f"Failed to update file metadata: {error_detail}")

                return response.json()

        else:
            raise ValueError("No update parameters provided")
