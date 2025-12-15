import pytest

from app.services.webengage_email import send_email
from app.core import config


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
    monkeypatch.setattr(config.settings, "WEBENGAGE_API_URL", "https://api.webengage.test")
    monkeypatch.setattr(config.settings, "WEBENGAGE_API_KEY", "fake-key")

    # Patch httpx.AsyncClient used by the module
    import httpx as _httpx

    monkeypatch.setattr(_httpx, "AsyncClient", DummyAsyncClient)

    result = await send_email(
        to_email="to@example.com",
        subject="Hi",
        template_id=None,
        variables={"name": "Alice"},
        from_email="from@example.com",
        from_name="Sender",
    )

    assert result == {"status": "sent"}


@pytest.mark.asyncio
async def test_send_email_not_configured(monkeypatch):
    # Ensure webengage disabled
    monkeypatch.setattr(config.settings, "WEBENGAGE_API_URL", None)
    monkeypatch.setattr(config.settings, "WEBENGAGE_API_KEY", None)

    with pytest.raises(RuntimeError):
        await send_email("a@b.com", "s")
