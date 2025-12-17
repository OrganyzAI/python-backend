import asyncio
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self, redis_client: Any):
        self.redis = redis_client
        self.connections: dict[str, set[WebSocket]] = {}
        self._pubsub: Any = None
        self._listen_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not self.redis:
            logger.warning("WebSocketManager start skipped: no redis client provided")
            return

        max_retries = 5
        base_delay = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                # try ping if available, but tolerate missing ping (e.g. fake redis in tests)
                ping = getattr(self.redis, "ping", None)
                if ping is not None:
                    result = await ping()
                    if not result:
                        raise Exception("Redis ping failed")

                logger.info(
                    "Starting WebSocketManager redis listener: %s",
                    getattr(self.redis, "pubsub", None),
                )
                # pubsub may be sync factory in fakes
                pubsub_factory = getattr(self.redis, "pubsub", None)
                if callable(pubsub_factory):
                    self._pubsub = pubsub_factory()
                else:
                    self._pubsub = pubsub_factory

                # subscribe (await if coroutine)
                subscribe = getattr(self._pubsub, "psubscribe", None)
                if subscribe is not None:
                    maybe = subscribe("ws:*")
                    if asyncio.iscoroutine(maybe):
                        await maybe

                self._listen_task = asyncio.create_task(self._reader_loop())
                return
            except Exception as e:
                logger.error(
                    f"WebSocketManager redis connection error on attempt {attempt}: {e}"
                )
                logger.warning(f"WebSocketManager start attempt {attempt} failed: {e}")
                if attempt == max_retries:
                    logger.warning(
                        "WebSocketManager failed to start after retries; continuing without Redis listener"
                    )
                    return
                await asyncio.sleep(base_delay * (2 ** (attempt - 1)))

    async def _reader_loop(self) -> None:
        try:
            async for message in self._pubsub.listen():
                if not message:
                    continue
                mtype = message.get("type")
                # handle pmessage (pattern) and message
                if mtype not in ("pmessage", "message"):
                    continue
                # redis.asyncio returns bytes for channel/data in some setups
                channel = message.get("channel") or message.get("pattern")
                data = message.get("data")
                if isinstance(channel, bytes | bytearray):
                    channel = channel.decode()
                if isinstance(data, bytes | bytearray):
                    data = data.decode()
                # channel format: ws:<room>
                try:
                    room = str(channel).split("ws:", 1)[1]
                except Exception:
                    continue
                await self._broadcast_to_local(room, data)
        except asyncio.CancelledError:
            logger.info("WebSocketManager listener task cancelled")
            raise
        except Exception as e:
            logger.exception(f"WebSocketManager listener error: {e}")

    async def publish(self, room: str, message: str) -> None:
        try:
            await self.redis.publish(f"ws:{room}", message)
        except Exception as e:
            logger.warning(f"Failed to publish websocket message: {e}")

    async def connect(
        self, websocket: WebSocket, room: str, user_id: str | None = None
    ) -> None:
        await websocket.accept()
        self.connections.setdefault(room, set()).add(websocket)

    async def disconnect(self, websocket: WebSocket, room: str) -> None:
        conns = self.connections.get(room)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self.connections.pop(room, None)

    async def send_personal(self, websocket: WebSocket, message: str) -> None:
        await websocket.send_text(message)

    async def _broadcast_to_local(self, room: str, message: str) -> None:
        conns = list(self.connections.get(room, []))
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                logger.exception("Error sending websocket message to local connection")

    async def stop(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                # task was cancelled as expected; swallow the exception so callers
                # awaiting stop don't observe a CancelledError.
                logger.info("WebSocketManager listener task cancelled during stop")
            except Exception:
                logger.exception("Error waiting for websocket listener task to stop")
        if self._pubsub:
            try:
                await self._pubsub.close()
            except Exception:
                logger.exception("Error closing websocket pubsub")
