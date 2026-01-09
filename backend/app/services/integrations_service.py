import base64
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_engine
from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount

logger = logging.getLogger(__name__)


class IntegrationService:
    async def connect_google_drive_with_tokens(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_in: int | None = None,
        scope: str | None = None,
        user_id: uuid.UUID | None = None,
        session: Session | None = None,
    ) -> ExternalAccount:
        if not access_token:
            raise ValueError("Access token is required")

        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        user_info = await self._get_google_user_info(access_token)
        provider_account_id = user_info.get("id") or user_info.get("sub")

        token_info = {
            "scope": scope,
            "token_type": "Bearer",
        }
        if user_info:
            user_info.update(token_info)
        else:
            user_info = token_info

        if not user_id:
            raise ValueError("User ID is required")

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
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.GOOGLE_DRIVE_URL}/oauth2/v2/userinfo",
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
        if not account.refresh_token:
            raise ValueError("No refresh token available")

        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise ValueError("Google OAuth2 credentials not configured")

        token_url = f"{settings.GOOGLE_DRIVE_URL}/oauth2/token"
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
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        metadata: dict[str, Any] = {
            "name": file_name,
        }
        if parent_folder_id:
            metadata["parents"] = [parent_folder_id]

        boundary = secrets.token_urlsafe(16)
        body_parts: list[str | bytes] = []

        body_parts.append(
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
        )

        body_parts.append(f"--{boundary}\r\nContent-Type: {mime_type}\r\n\r\n")
        body_parts.append(file_content)
        body_parts.append(f"\r\n--{boundary}--\r\n")

        body = b"".join(
            part.encode("utf-8") if isinstance(part, str) else part
            for part in body_parts
        )

        url = f"{settings.GOOGLE_DRIVE_URL}/upload/drive/v3/files?uploadType=multipart"
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

            result: dict[str, Any] = response.json()
            return result

    async def list_google_drive_files(
        self,
        user_id: uuid.UUID,
        page_size: int = 100,
        page_token: str | None = None,
        query: str | None = None,
        session: Session | None = None,
    ) -> dict[str, Any]:
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

        url = f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files"
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"Failed to list Google Drive files: {error_detail}")
                raise ValueError(f"Failed to list files: {error_detail}")

            result: dict[str, Any] = response.json()
            return result

    async def read_google_drive_file(
        self,
        user_id: uuid.UUID,
        file_id: str,
        session: Session | None = None,
    ) -> dict[str, Any]:
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        metadata_url = f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files/{file_id}"
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

            content_url = (
                f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files/{file_id}?alt=media"
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
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        metadata_url = f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files/{file_id}"
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

            content_url = (
                f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files/{file_id}?alt=media"
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
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        if file_content is not None and (
            file_name is not None or mime_type is not None
        ):
            metadata: dict[str, Any] = {}
            if file_name:
                metadata["name"] = file_name

            boundary = secrets.token_urlsafe(16)
            body_parts: list[str | bytes] = []

            if metadata:
                body_parts.append(
                    f"--{boundary}\r\n"
                    f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
                    f"{json.dumps(metadata)}\r\n"
                )

            content_type = mime_type or "application/octet-stream"
            body_parts.append(f"--{boundary}\r\nContent-Type: {content_type}\r\n\r\n")
            body_parts.append(file_content)
            body_parts.append(f"\r\n--{boundary}--\r\n")

            body = b"".join(
                part.encode("utf-8") if isinstance(part, str) else part
                for part in body_parts
            )

            url = f"{settings.GOOGLE_DRIVE_URL}/upload/drive/v3/files/{file_id}?uploadType=multipart"
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

                multipart_result: dict[str, Any] = response.json()
                return multipart_result

        elif file_content is not None:
            url = f"{settings.GOOGLE_DRIVE_URL}/upload/drive/v3/files/{file_id}?uploadType=media"
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

                content_result: dict[str, Any] = response.json()
                return content_result

        elif file_name is not None:
            metadata = {"name": file_name}
            url = f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files/{file_id}"
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

                metadata_result: dict[str, Any] = response.json()
                return metadata_result

        else:
            raise ValueError("No update parameters provided")

    async def search_google_drive_files(
        self,
        user_id: uuid.UUID,
        query: str,
        search_in_content: bool = True,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        account = await self.get_google_drive_account(user_id, session=session)
        if not account:
            raise ValueError("Google Drive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        results: list[dict[str, Any]] = []

        escaped_query = query.replace("'", "\\'")

        if search_in_content:
            q = (
                f"(name contains '{escaped_query}' "
                f"or fullText contains '{escaped_query}') "
                f"and trashed = false"
            )
        else:
            q = f"name contains '{escaped_query}' and trashed = false"

        params: dict[str, Any] = {
            "q": q,
            "pageSize": 100,
            "fields": (
                "nextPageToken, "
                "files(id, name, mimeType, size, "
                "createdTime, modifiedTime, "
                "webViewLink, webContentLink, parents)"
            ),
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
            "corpora": "user",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            page_token: str | None = None

            while True:
                if page_token:
                    params["pageToken"] = page_token
                else:
                    params.pop("pageToken", None)

                try:
                    resp = await client.get(
                        f"{settings.GOOGLE_DRIVE_URL}/drive/v3/files",
                        headers=headers,
                        params=params,
                    )

                    if resp.status_code != 200:
                        logger.error("Google Drive search failed: %s", resp.text)
                        break

                    data = resp.json()

                    for item in data.get("files", []):
                        results.append(
                            {
                                "id": item.get("id"),
                                "name": item.get("name"),
                                "mime_type": item.get("mimeType"),
                                "size": item.get("size"),
                                "created_time": item.get("createdTime"),
                                "modified_time": item.get("modifiedTime"),
                                "web_url": item.get("webViewLink"),
                                "download_url": item.get("webContentLink"),
                                "provider": "google_drive",
                                "type": (
                                    "folder"
                                    if item.get("mimeType")
                                    == "application/vnd.google-apps.folder"
                                    else "file"
                                ),
                            }
                        )

                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break

                except Exception:
                    logger.exception("Error searching Google Drive")
                    break

        return results
