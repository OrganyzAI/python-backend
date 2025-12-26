import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any

import httpx
import jwt

from app.core.config import settings


def generate_uuid() -> str:
    return str(uuid.uuid4())


def generate_hash(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def get_current_timestamp() -> datetime:
    return datetime.utcnow()


def add_time(hours: int = 0, minutes: int = 0, days: int = 0) -> datetime:
    return datetime.utcnow() + timedelta(hours=hours, minutes=minutes, days=days)


def format_datetime(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


def parse_datetime(dt_str: str, fmt: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    return datetime.strptime(dt_str, fmt)


async def verify_google_token(token: str) -> dict[str, Any] | None:
    """
    Verify Google token. Supports both id_token and access_token.
    - If id_token: verifies using tokeninfo endpoint
    - If access_token: fetches user info from userinfo endpoint
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, try to verify as id_token
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token},
            )
            if resp.status_code == 200:
                data: dict[str, Any] = resp.json()
                google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", None)
                if google_client_id and data.get("aud") != google_client_id:
                    return None
                return data

            # If id_token verification failed, try as access_token
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                data: dict[str, Any] = resp.json()
                # Normalize the response to match id_token format
                # userinfo returns 'sub' for user ID, which matches id_token format
                return data

            return None
    except Exception:
        return None


async def verify_apple_token(id_token: str) -> dict[str, Any] | None:
    try:
        try:
            jwk_client = jwt.PyJWKClient("https://appleid.apple.com/auth/keys")
            signing_key = jwk_client.get_signing_key_from_jwt(id_token)
            public_key = signing_key.key
        except Exception:
            return None

        audience = getattr(settings, "APPLE_CLIENT_ID", None)
        options = {"verify_aud": bool(audience)}
        payload: dict[str, Any] = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=audience if audience else None,
            options=options,
        )
        return payload
    except Exception:
        return None
