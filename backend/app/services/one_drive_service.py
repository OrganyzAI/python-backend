import logging
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_engine
from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount

logger = logging.getLogger(__name__)


class OneDriveService:
    async def connect_one_drive_with_tokens(
        self,
        access_token: str,
        token_source: str | None = None,
        expires_in: int | None = None,
        ext_expires_in: int | None = None,
        token_type: str | None = None,
        user_id: uuid.UUID | None = None,
        session: Session | None = None,
    ) -> ExternalAccount:
        if not access_token:
            raise ValueError("Access token is required")

        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        user_info = await self._get_one_drive_user_info(access_token)
        provider_account_id = user_info.get("id") or user_info.get("sub")

        token_info = {
            "token_source": token_source,
            "token_type": token_type,
            "expires_in": expires_in,
            "ext_expires_in": ext_expires_in,
        }
        if user_info:
            user_info.update(token_info)
        else:
            user_info = token_info

        if not user_id:
            raise ValueError("User ID is required")

        own_session = None
        if session is None:
            own_session = Session(get_engine())
            session = own_session

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            )
            existing_account = session.exec(stmt).first()

            if existing_account:
                existing_account.access_token = access_token
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
                provider=EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
                provider_account_id=provider_account_id,
                access_token=access_token,
                expires_at=expires_at,
                extra_data=user_info,
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            return account
        finally:
            if own_session:
                own_session.close()

    async def _get_one_drive_user_info(self, access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{settings.MICROSOFT_URL}/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code != 200:
                logger.error(f"Failed to get OneDrive user info: {response.text}")
                return {}
            result: dict[str, Any] = response.json()
            return result

    async def _ensure_valid_token(
        self, account: ExternalAccount, session: Session | None = None
    ) -> str:
        if account.expires_at and account.expires_at > datetime.utcnow():
            return account.access_token or ""
        if not account.refresh_token:
            raise ValueError("No refresh token available")
        if not account.access_token:
            raise ValueError("No access token available")
        return account.access_token

    async def get_all_tenants(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        account = await self.get_one_drive_account(user_id, session=session)
        if not account:
            raise ValueError("OneDrive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        tenants = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {access_token}"}

            try:
                response = await client.get(
                    f"{settings.MICROSOFT_GRAPH_URL}/v1.0/me/drive",
                    headers=headers,
                )
                if response.status_code == 200:
                    drive_data = response.json()
                    tenants.append(
                        {
                            "id": drive_data.get("id"),
                            "name": "Personal OneDrive",
                            "webUrl": drive_data.get("webUrl"),
                            "driveType": "personal",
                            "drive": drive_data,
                        }
                    )
            except Exception as e:
                logger.error(f"Failed to get personal OneDrive: {e}")

            url = f"{settings.MICROSOFT_GRAPH_URL}/v1.0/sites?search=*"
            while url:
                try:
                    response = await client.get(url, headers=headers)
                    if response.status_code != 200:
                        logger.error(f"Failed to get sites: {response.text}")
                        break

                    data = response.json()
                    for site in data.get("value", []):
                        site_id = site.get("id")
                        if site_id:
                            try:
                                drive_response = await client.get(
                                    f"{settings.MICROSOFT_GRAPH_URL}/v1.0/sites/{site_id}/drive",
                                    headers=headers,
                                )
                                if drive_response.status_code == 200:
                                    drive_data = drive_response.json()
                                    site["drive"] = drive_data
                                    site["driveType"] = "sharepoint"
                            except Exception as e:
                                logger.error(
                                    f"Failed to get drive for site {site_id}: {e}"
                                )

                    tenants.extend(data.get("value", []))

                    url = data.get("@odata.nextLink")
                except Exception as e:
                    logger.error(f"Error fetching sites: {e}")
                    break

        return tenants

    async def get_files_for_tenant(
        self,
        user_id: uuid.UUID,
        site_id: str,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        account = await self.get_one_drive_account(user_id, session=session)
        if not account:
            raise ValueError("OneDrive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        all_files = []
        headers = {"Authorization": f"Bearer {access_token}"}

        if site_id == "personal" or site_id.startswith("drive-"):
            base_url = f"{settings.MICROSOFT_GRAPH_URL}/v1.0/me/drive"
        else:
            base_url = f"{settings.MICROSOFT_GRAPH_URL}/v1.0/sites/{site_id}/drive"

        async def get_files_recursive(folder_id: str = "root") -> None:
            url = (
                f"{base_url}/items/{folder_id}/children"
                if folder_id != "root"
                else f"{base_url}/root/children"
            )

            async with httpx.AsyncClient(timeout=30.0) as client:
                current_url = url

                while current_url:
                    try:
                        response = await client.get(current_url, headers=headers)
                        if response.status_code != 200:
                            logger.error(
                                f"Failed to get files from {current_url}: {response.text}"
                            )
                            break

                        data = response.json()
                        items = data.get("value", [])

                        for item in items:
                            all_files.append(item)

                            if item.get("folder"):
                                item_id = item.get("id")
                                if item_id:
                                    await get_files_recursive(folder_id=item_id)

                        current_url = data.get("@odata.nextLink")
                    except Exception as e:
                        logger.error(f"Error fetching files from {current_url}: {e}")
                        break

        await get_files_recursive()

        return all_files

    async def get_all_files_with_tenants(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> dict[str, Any]:
        tenants = await self.get_all_tenants(user_id, session=session)
        result: dict[str, Any] = {
            "tenants": [],
            "total_files": 0,
        }

        for tenant in tenants:
            site_id = tenant.get("id")
            drive_type = tenant.get("driveType", "sharepoint")
            if not site_id:
                continue

            try:
                if drive_type == "personal":
                    drive_id = tenant.get("drive", {}).get("id")
                    tenant_id = drive_id or "personal"
                else:
                    tenant_id = site_id

                files = await self.get_files_for_tenant(
                    user_id, tenant_id, session=session
                )
                tenant_data = {
                    "tenant": tenant,
                    "files": files,
                    "file_count": len(files),
                }
                result["tenants"].append(tenant_data)
                result["total_files"] += len(files)
            except Exception as e:
                logger.error(f"Failed to get files for tenant {site_id}: {e}")
                tenant_data = {
                    "tenant": tenant,
                    "files": [],
                    "file_count": 0,
                    "error": str(e),
                }
                result["tenants"].append(tenant_data)

        return result

    async def get_one_drive_account(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> ExternalAccount | None:
        own_session = None
        if session is None:
            own_session = Session(get_engine())
            session = own_session

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.ONE_DRIVE,
            )
            account = session.exec(stmt).first()
            return account
        finally:
            if own_session:
                own_session.close()

    async def upload_file_to_one_drive(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file_content: bytes,
    ) -> dict[str, Any]:
        account = await self.get_one_drive_account(user_id)
        if not account:
            raise ValueError("OneDrive account not connected")

        access_token = await self._ensure_valid_token(account)

        encoded_filename = quote(file_name)
        url = f"{settings.MICROSOFT_GRAPH_URL}/v1.0/me/drive/root:/{encoded_filename}:/content"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=headers, content=file_content)
            if response.status_code not in (200, 201):
                logger.error(
                    f"Failed to upload file to One Drive: {response.status_code} - {response.text}"
                )
                raise ValueError(
                    f"Failed to upload file: {response.status_code} {response.text}"
                )
            result: dict[str, Any] = response.json()
            return {
                "file_metadata": result,
                "file_name": file_name,
                "file_id": result.get("id"),
            }

    async def search_files(
        self,
        user_id: uuid.UUID,
        query: str,
        search_in_content: bool = True,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        account = await self.get_one_drive_account(user_id, session=session)
        if not account:
            raise ValueError("OneDrive account not connected")

        access_token = await self._ensure_valid_token(account, session=session)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

        results: list[dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=30.0) as client:

            async def fetch_search(url: str, tenant: dict):
                while url:
                    resp = await client.get(url, headers=headers)
                    if resp.status_code != 200:
                        logger.warning("OneDrive search failed: %s", resp.text)
                        return

                    data = resp.json()
                    for item in data.get("value", []):
                        if not search_in_content:
                            if query.lower() not in item.get("name", "").lower():
                                continue

                        results.append(
                            {
                                "id": item.get("id"),
                                "name": item.get("name"),
                                "path": item.get("parentReference", {}).get("path"),
                                "web_url": item.get("webUrl"),
                                "size": item.get("size"),
                                "provider": "onedrive",
                                "type": "file" if "file" in item else "folder",
                                "last_modified": item.get("lastModifiedDateTime"),
                                "tenant": tenant,
                            }
                        )

                    url = data.get("@odata.nextLink")

            personal_url = (
                f"{settings.MICROSOFT_GRAPH_URL}/v1.0/me/drive/root/search(q='{query}')"
            )

            await fetch_search(
                personal_url,
                {"driveType": "personal", "name": "Personal OneDrive"},
            )

            tenants = await self.get_all_tenants(user_id, session=session)

            for tenant in tenants:
                if tenant.get("driveType") == "personal":
                    continue

                site_id = tenant.get("id")
                if not site_id:
                    continue

                site_url = (
                    f"{settings.MICROSOFT_GRAPH_URL}/v1.0/sites/{site_id}"
                    f"/drive/root/search(q='{query}')"
                )

                await fetch_search(site_url, tenant)

        return results
