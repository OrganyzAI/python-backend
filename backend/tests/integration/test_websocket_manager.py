import asyncio
import pytest

from app.api.websocket_manager import WebSocketManager


class FakePubSub:
    def __init__(self, messages):
        self._messages = messages

    async def psubscribe(self, pattern):
        return None

    async def listen(self):
        for m in self._messages:
            yield m

    async def close(self):
        pass


class FakeRedis:
    def __init__(self, messages=None):
        self._messages = messages or []

    def pubsub(self):
        return FakePubSub(self._messages)

    async def publish(self, channel, message):
        # pretend to publish
        return 1


@pytest.mark.asyncio
async def test_websocket_manager_start_stop():
    fake_redis = FakeRedis(messages=[{"type":"pmessage","pattern":"ws:*","channel":"ws:room1","data":"hello"}])
    mgr = WebSocketManager(fake_redis)

    await mgr.start()
    assert mgr._listen_task is not None

    await mgr.stop()
    assert mgr._listen_task is None or mgr._listen_task.cancelled()


@pytest.mark.asyncio
async def test_publish_no_error():
    fake_redis = FakeRedis()
    mgr = WebSocketManager(fake_redis)
    await mgr.publish("room1", "msg")
