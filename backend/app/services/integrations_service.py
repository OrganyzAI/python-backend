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

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        # Google OAuth2 scopes for Drive API
        scopes = [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/drive.metadata.readonly",
        ]

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",  # Required to get refresh token
            "prompt": "consent",  # Force consent screen to get refresh token
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
