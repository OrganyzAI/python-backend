import asyncio
import logging
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manage WebSocket connections and Redis pub/sub bridging.

    - Keeps in-memory mapping of rooms -> WebSocket connections for local broadcasts.
    - Subscribes to Redis channels `ws:{room}` and broadcasts published messages
      to local connections so multiple app instances stay in sync.
    """

    def __init__(self, redis_client):
        self.redis = redis_client
        self.connections: Dict[str, Set[WebSocket]] = {}
        self._pubsub = None
        self._listen_task: asyncio.Task | None = None

    async def start(self) -> None:
        try:
            self._pubsub = self.redis.pubsub()
            # Subscribe to all ws channels using pattern subscription
            await self._pubsub.psubscribe("ws:*")
            self._listen_task = asyncio.create_task(self._reader_loop())
            logger.info("WebSocketManager redis listener started")
        except Exception as e:
            logger.warning(f"WebSocketManager start failed: {e}")

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
                if isinstance(channel, (bytes, bytearray)):
                    channel = channel.decode()
                if isinstance(data, (bytes, bytearray)):
                    data = data.decode()
                # channel format: ws:<room>
                try:
                    room = str(channel).split("ws:", 1)[1]
                except Exception:
                    continue
                await self._broadcast_to_local(room, data)
        except asyncio.CancelledError:
            logger.info("WebSocketManager listener task cancelled")
        except Exception as e:
            logger.exception(f"WebSocketManager listener error: {e}")

    async def publish(self, room: str, message: str) -> None:
        try:
            await self.redis.publish(f"ws:{room}", message)
        except Exception as e:
            logger.warning(f"Failed to publish websocket message: {e}")

    async def connect(self, websocket: WebSocket, room: str) -> None:
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
                # ignore send errors; disconnect will clean up
                pass

    async def stop(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except Exception:
                pass
        if self._pubsub:
            try:
                await self._pubsub.close()
            except Exception:
                pass
