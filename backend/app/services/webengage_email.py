from typing import Any, cast

import httpx

from app.core.config import settings


async def send_email(
    to_email: str,
    subject: str,
    template_id: str | None = None,
    variables: dict[str, Any] | None = None,
    from_email: str | None = None,
    from_name: str | None = None,
) -> dict[str, Any]:

    if not settings.webengage_enabled:
        raise RuntimeError("WebEngage is not configured (WEBENGAGE_API_URL/KEY missing)")

    url = str(settings.WEBENGAGE_API_URL)
    headers = {
        "Authorization": f"Bearer {settings.WEBENGAGE_API_KEY}",
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {
        "to": {"email": to_email},
        "subject": subject,
        "personalization": variables or {},
    }

    if template_id:
        body["template_id"] = template_id

    if from_email or settings.EMAILS_FROM_EMAIL:
        body["from"] = {
            "email": from_email or str(settings.EMAILS_FROM_EMAIL),
            "name": from_name or settings.EMAILS_FROM_NAME,
        }

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json())
