import uuid
from typing import Any

import httpx

from app.core.config import settings


async def send_email(to_email: str, verify_url: str, ttl: int = 60) -> dict[str, Any]:
    """
    Sends a transactional email using WebEngage API.
    """

    if not settings.webengage_enabled:
        raise RuntimeError("WebEngage is not enabled")

    url = "https://api.webengage.com/v2/accounts/11b5648a7/experiments/~2o21rqq/transaction"
    headers = {
        "Authorization": f"Bearer {settings.WEBENGAGE_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    # Generate a unique userId for each email to avoid conflicts
    unique_user_id = str(uuid.uuid4())

    body = {
        "userId": unique_user_id,
        "ttl": ttl,
        "overrideData": {
            "email": to_email,
            "context": {"token": {"USER_EMAIL": to_email, "VERIFY_URL": verify_url}},
        },
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()
