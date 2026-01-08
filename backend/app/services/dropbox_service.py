import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

import dropbox
import httpx
from dropbox import Dropbox
from dropbox.exceptions import ApiError, AuthError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.db import get_engine
from app.enums.external_account_enum import EXTERNAL_ACCOUNT_PROVIDER
from app.models.external_account import ExternalAccount

logger = logging.getLogger(__name__)


class DropboxService:
    async def connect_dropbox_with_tokens(
        self,
        access_token: str,
        refresh_token: str | None = None,
        expires_in: int | None = None,
        token_type: str | None = None,
        scope: str | None = None,
        user_id: uuid.UUID | None = None,
        session: Session | None = None,
    ) -> ExternalAccount:
        if not access_token:
            raise ValueError("Access token is required")

        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        user_info = await self._get_dropbox_user_info(access_token)
        provider_account_id = user_info.get("account_id")

        # Use scope from settings if not provided
        final_scope = scope or settings.DROPBOX_SCOPE

        token_info = {
            "token_type": token_type,
            "expires_in": expires_in,
            "refresh_token": refresh_token,
            "scope": final_scope,
        }
        if user_info:
            user_info.update(token_info)
        else:
            user_info = token_info

        # User ID is required
        if not user_id:
            raise ValueError("User ID is required")

        # Check if account already exists
        own_session = None
        if session is None:
            own_session = Session(get_engine())
            session = own_session

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.DROPBOX,
            )
            existing_account = session.exec(stmt).first()

            if existing_account:
                # Update existing account
                existing_account.access_token = access_token
                existing_account.refresh_token = refresh_token
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
                provider=EXTERNAL_ACCOUNT_PROVIDER.DROPBOX,
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
            if own_session:
                own_session.close()

    async def _get_dropbox_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Dropbox API using access token"""
        try:
            dbx = Dropbox(access_token)
            account = await asyncio.to_thread(dbx.users_get_current_account)
            # Convert the account object to dict
            result: dict[str, Any] = {
                "account_id": account.account_id,
                "name": {
                    "display_name": account.name.display_name,
                    "given_name": account.name.given_name,
                    "surname": account.name.surname,
                    "familiar_name": account.name.familiar_name,
                    "abbreviated_name": account.name.abbreviated_name,
                },
                "email": account.email,
                "locale": account.locale,
                "referral_link": account.referral_link,
                "is_paired": account.is_paired,
                "account_type": account.account_type.get_tag(),
                "country": account.country,
            }
            return result
        except (ApiError, AuthError) as e:
            logger.error(f"Failed to get Dropbox user info: {e}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error getting Dropbox user info: {e}")
            return {}

    async def refresh_dropbox_token(
        self,
        account: ExternalAccount,
        session: Session | None = None,
    ) -> ExternalAccount:
        """Refresh Dropbox access token using refresh token"""
        if not account.refresh_token:
            raise ValueError("No refresh token available")

        if not settings.DROPBOX_CLIENT_ID or not settings.DROPBOX_CLIENT_SECRET:
            raise ValueError("Dropbox OAuth2 credentials not configured")

        own_session = None
        if session is None:
            own_session = Session(get_engine())
            session = own_session

        try:
            # Use OAuth2 endpoint for token refresh (standard OAuth2, not Dropbox-specific API)
            # The Dropbox SDK doesn't provide a refresh method, so we use httpx for OAuth2 token endpoint
            token_url = "https://api.dropbox.com/oauth2/token"
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": account.refresh_token,
                "client_id": settings.DROPBOX_CLIENT_ID,
                "client_secret": settings.DROPBOX_CLIENT_SECRET,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(token_url, data=token_data)
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"Failed to refresh Dropbox token: {error_detail}")
                    raise ValueError(f"Failed to refresh token: {error_detail}")

                token_response = response.json()

            access_token = token_response.get("access_token")
            expires_in = token_response.get("expires_in", 14400)  # Default 4 hours
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            refresh_token = token_response.get("refresh_token") or account.refresh_token

            # Update account with new tokens
            account.access_token = access_token
            account.refresh_token = refresh_token
            account.expires_at = expires_at
            account.updated_at = datetime.utcnow()

            session.add(account)
            session.commit()
            session.refresh(account)

            return account
        except (ApiError, AuthError) as e:
            error_detail = str(e)
            logger.error(f"Failed to refresh Dropbox token: {error_detail}")
            raise ValueError(f"Failed to refresh token: {error_detail}")
        except Exception as e:
            logger.error(f"Unexpected error refreshing Dropbox token: {e}")
            raise ValueError(f"Failed to refresh token: {str(e)}")
        finally:
            if own_session:
                own_session.close()

    async def _ensure_valid_token(
        self, account: ExternalAccount, session: Session | None = None
    ) -> str:
        """Ensure the access token is valid, refresh if necessary"""
        if account.expires_at and account.expires_at > datetime.utcnow():
            return account.access_token or ""
        if not account.refresh_token:
            raise ValueError("No refresh token available")

        # Refresh token if expired
        refreshed_account = await self.refresh_dropbox_token(account, session=session)
        if not refreshed_account.access_token:
            raise ValueError("No access token available after refresh")
        return refreshed_account.access_token

    def get_dropbox_authorization_url(self, state: str | None = None) -> str:
        """Generate Dropbox OAuth authorization URL"""
        if not settings.DROPBOX_CLIENT_ID:
            raise ValueError("Dropbox CLIENT_ID not configured")

        if not settings.DROPBOX_REDIRECT_URI:
            raise ValueError("Dropbox REDIRECT_URI not configured")

        from urllib.parse import urlencode

        base_url = (
            settings.DROPBOX_AUTHORIZATION_URL
            or "https://www.dropbox.com/oauth2/authorize"
        )
        response_type = settings.DROPBOX_RESPONSE_TYPE or "code"
        scope = settings.DROPBOX_SCOPE or ""

        params = {
            "client_id": settings.DROPBOX_CLIENT_ID,
            "redirect_uri": settings.DROPBOX_REDIRECT_URI,
            "response_type": response_type,
        }

        if scope:
            params["scope"] = scope

        if state:
            params["state"] = state

        return f"{base_url}?{urlencode(params)}"

    async def get_all_files_with_namespaces(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> dict[str, Any]:
        """Get all files organized by namespace (personal, team, etc.)"""
        namespaces = await self.get_all_namespaces(user_id, session=session)
        result: dict[str, Any] = {
            "namespaces": [],
            "total_files": 0,
        }

        for namespace in namespaces:
            namespace_id = namespace.get("namespace_id")
            if not namespace_id:
                continue

            try:
                files = await self.get_files_for_namespace(
                    user_id, namespace_id, session=session
                )
                namespace_data = {
                    "namespace": namespace,
                    "files": files,
                    "file_count": len(files),
                }
                result["namespaces"].append(namespace_data)
                result["total_files"] += len(files)
            except Exception as e:
                logger.error(f"Failed to get files for namespace {namespace_id}: {e}")
                namespace_data = {
                    "namespace": namespace,
                    "files": [],
                    "file_count": 0,
                    "error": str(e),
                }
                result["namespaces"].append(namespace_data)

        return result

    async def get_all_namespaces(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Get all namespaces from Dropbox API (personal, team, etc.)"""
        account = await self.get_dropbox_account(user_id, session=session)
        if not account:
            raise ValueError("Dropbox account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        namespaces = []
        dbx = Dropbox(access_token)

        # Get user's personal account info
        try:
            account_obj = await asyncio.to_thread(dbx.users_get_current_account)
            namespaces.append(
                {
                    "namespace_id": account_obj.account_id,
                    "name": account_obj.name.display_name or "Personal Dropbox",
                    "email": account_obj.email,
                    "namespace_type": "personal",
                    "account": {
                        "account_id": account_obj.account_id,
                        "name": {
                            "display_name": account_obj.name.display_name,
                            "given_name": account_obj.name.given_name,
                            "surname": account_obj.name.surname,
                        },
                        "email": account_obj.email,
                        "locale": account_obj.locale,
                        "account_type": account_obj.account_type.get_tag(),
                    },
                }
            )
        except Exception as e:
            logger.error(f"Failed to get personal Dropbox account: {e}")

        # Get team namespaces if available (requires team scope)
        try:
            team_namespaces = await asyncio.to_thread(dbx.team_namespaces_list)
            for namespace in team_namespaces.namespaces:
                namespace_info = {
                    "namespace_id": namespace.namespace_id,
                    "name": namespace.name,
                    "namespace_type": namespace.namespace_type.get_tag()
                    if hasattr(namespace.namespace_type, "get_tag")
                    else "team",
                    "namespace": {
                        "namespace_id": namespace.namespace_id,
                        "name": namespace.name,
                        "namespace_type": namespace.namespace_type.get_tag()
                        if hasattr(namespace.namespace_type, "get_tag")
                        else "team",
                    },
                }
                namespaces.append(namespace_info)
        except (ApiError, AttributeError) as e:
            logger.debug(f"Team namespaces not available or not accessible: {e}")
        except Exception as e:
            logger.debug(f"Error getting team namespaces: {e}")

        return namespaces

    async def get_files_for_namespace(
        self,
        user_id: uuid.UUID,
        namespace_id: str,
        session: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Get all files for a specific namespace (recursively)"""
        account = await self.get_dropbox_account(user_id, session=session)
        if not account:
            raise ValueError("Dropbox account not connected")

        access_token = await self._ensure_valid_token(account, session=session)

        all_files = []
        dbx = Dropbox(access_token)

        def convert_metadata_to_dict(metadata: Any) -> dict[str, Any]:
            """Convert Dropbox metadata object to dictionary"""
            if hasattr(metadata, "__dict__"):
                result = {}
                for key, value in metadata.__dict__.items():
                    if key.startswith("_"):
                        continue
                    if hasattr(value, "__dict__"):
                        result[key] = convert_metadata_to_dict(value)
                    elif hasattr(value, "get_tag"):
                        result[key] = value.get_tag()
                    else:
                        result[key] = value
                return result
            return {}

        async def get_files_recursive(path: str = "") -> None:
            """Recursively get all files from a folder"""
            try:
                # List folder using SDK
                result = await asyncio.to_thread(dbx.files_list_folder, path or "")

                # Process entries
                for entry in result.entries:
                    entry_dict = convert_metadata_to_dict(entry)
                    # Add .tag for compatibility
                    if hasattr(entry, "get_tag"):
                        entry_dict[".tag"] = entry.get_tag()
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        entry_dict[".tag"] = "folder"
                    elif isinstance(entry, dropbox.files.FileMetadata):
                        entry_dict[".tag"] = "file"

                    all_files.append(entry_dict)

                    # If it's a folder, recursively get its contents
                    if isinstance(entry, dropbox.files.FolderMetadata):
                        entry_path = entry.path_lower or entry.path_display
                        if entry_path:
                            await get_files_recursive(path=entry_path)

                # Handle pagination
                while result.has_more:
                    cursor = result.cursor
                    result = await asyncio.to_thread(
                        dbx.files_list_folder_continue, cursor
                    )

                    for entry in result.entries:
                        entry_dict = convert_metadata_to_dict(entry)
                        if hasattr(entry, "get_tag"):
                            entry_dict[".tag"] = entry.get_tag()
                        elif isinstance(entry, dropbox.files.FolderMetadata):
                            entry_dict[".tag"] = "folder"
                        elif isinstance(entry, dropbox.files.FileMetadata):
                            entry_dict[".tag"] = "file"

                        all_files.append(entry_dict)

                        if isinstance(entry, dropbox.files.FolderMetadata):
                            entry_path = entry.path_lower or entry.path_display
                            if entry_path:
                                await get_files_recursive(path=entry_path)
            except ApiError as e:
                logger.error(f"Failed to get files from {path}: {e}")
            except Exception as e:
                logger.error(f"Error fetching files from {path}: {e}")

        # Start recursive file fetching from root
        await get_files_recursive()

        return all_files

    async def get_dropbox_account(
        self,
        user_id: uuid.UUID,
        session: Session | None = None,
    ) -> ExternalAccount | None:
        """Get Dropbox account for user"""
        own_session = None
        if session is None:
            own_session = Session(get_engine())
            session = own_session

        try:
            stmt = select(ExternalAccount).where(
                ExternalAccount.user_id == user_id,
                ExternalAccount.provider == EXTERNAL_ACCOUNT_PROVIDER.DROPBOX,
            )
            account = session.exec(stmt).first()
            return account
        finally:
            if own_session:
                own_session.close()

    async def upload_file_to_dropbox(
        self,
        user_id: uuid.UUID,
        file_name: str,
        file_content: bytes,
    ) -> dict[str, Any]:
        """Upload a file to Dropbox"""
        account = await self.get_dropbox_account(user_id)
        if not account:
            raise ValueError("Dropbox account not connected")

        access_token = await self._ensure_valid_token(account)

        dbx = Dropbox(access_token)

        try:
            # Upload file using SDK
            path = f"/{file_name}"
            mode = dropbox.files.WriteMode.add
            metadata = await asyncio.to_thread(
                dbx.files_upload,
                file_content,
                path,
                mode=mode,
                autorename=True,
            )

            # Convert metadata to dict
            result: dict[str, Any] = {
                "id": metadata.id,
                "name": metadata.name,
                "path_lower": metadata.path_lower,
                "path_display": metadata.path_display,
                "size": metadata.size,
                "server_modified": metadata.server_modified.isoformat()
                if metadata.server_modified
                else None,
                "client_modified": metadata.client_modified.isoformat()
                if metadata.client_modified
                else None,
                "rev": metadata.rev,
                "content_hash": metadata.content_hash
                if hasattr(metadata, "content_hash")
                else None,
            }

            return {
                "file_metadata": result,
                "file_name": file_name,
                "file_id": result.get("id"),
            }
        except ApiError as e:
            logger.error(f"Failed to upload file to Dropbox: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading file to Dropbox: {e}")
            raise ValueError(f"Failed to upload file: {str(e)}")
