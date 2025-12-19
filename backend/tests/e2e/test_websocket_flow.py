import pytest
import asyncio

from app.api.websocket_manager import WebSocketManager


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_text(self, message):
        self.sent.append(message)


@pytest.mark.asyncio
async def test_broadcast_to_local():
    fake_redis = type("R", (), {"publish": lambda *a, **k: asyncio.sleep(0)})()
    mgr = WebSocketManager(fake_redis)

    ws1 = FakeWebSocket()
    ws2 = FakeWebSocket()

    # directly insert connections
    mgr.connections.setdefault("room1", set()).add(ws1)
    mgr.connections.setdefault("room1", set()).add(ws2)

    await mgr._broadcast_to_local("room1", "hello")
    assert "hello" in ws1.sent
    assert "hello" in ws2.sent
