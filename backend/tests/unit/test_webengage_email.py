import pytest

from app.core import config
from app.services.webengage_email import send_email


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"status": "sent"}


class DummyAsyncClient:
    def __init__(self, *args, **kwargs):
        self.called = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.called = {"url": url, "json": json, "headers": headers}
        return DummyResponse()


@pytest.mark.asyncio
async def test_send_email_success(monkeypatch):
    # Enable webengage settings
    # Enable webengage by setting the underlying config values
    monkeypatch.setattr(
        config.settings, "WEBENGAGE_API_URL", "https://api.webengage.com", raising=False
    )
    monkeypatch.setattr(config.settings, "WEBENGAGE_API_KEY", "fake-key", raising=False)

    # Patch httpx.AsyncClient used by the module
    import httpx as _httpx

    monkeypatch.setattr(_httpx, "AsyncClient", DummyAsyncClient)

    result = await send_email(
        to_email="to@example.com",
        verify_url="https://example.com/verify?token=abc123",
        ttl=60,
    )

    assert result == {"status": "sent"}


@pytest.mark.asyncio
async def test_send_email_not_configured(monkeypatch):
    # Ensure webengage disabled
    # Disable webengage by clearing the API URL (computed property reads this)
    monkeypatch.setattr(config.settings, "WEBENGAGE_API_URL", None, raising=False)

    with pytest.raises(RuntimeError):
        await send_email("a@b.com", "s")
