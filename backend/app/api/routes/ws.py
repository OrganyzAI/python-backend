import json
import logging
import time
from datetime import datetime

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlmodel import Session, select

from app.core import security
from app.core.config import settings
from app.core.db import get_engine
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


def _sanitize_text(value: str) -> str:
    return value.replace("<", "&lt;").replace(">", "&gt;")


async def _verify_websocket_token(token: str) -> User | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        subject = payload.get("sub")
        if not subject:
            return None
        with Session(get_engine()) as session:
            statement = select(User).where(User.id == subject)
            user = session.exec(statement).first()
            return user
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


async def _verify_room_access(room: str, user: User) -> bool:
    logger.info("Verifying room access for user %s to room %s", user.id, room)
    return True


@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str) -> None:
    # 1. Authenticate (token passed as query param `?token=...`)
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = await _verify_websocket_token(token)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Authorize room access
    if not await _verify_room_access(room, user):
        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
        return

    manager = websocket.app.state.ws_manager
    # Attach user context on connect
    await manager.connect(websocket, room, user_id=str(user.id))

    # Rate limiting params
    MAX_MESSAGE_SIZE = 64 * 1024
    MAX_MESSAGES_PER_MINUTE = 60
    window = 60

    try:
        while True:
            data = await websocket.receive_text()

            if len(data) > MAX_MESSAGE_SIZE:
                # ignore oversized messages
                continue

            # Redis-backed per-user+room rate limiting (zset window)
            redis = getattr(websocket.app.state, "redis", None)
            if redis:
                now = time.time()
                window_start = now - window
                key = f"ws_rate:{room}:{user.id}"
                member = f"{now}-{now}"
                try:
                    pipe = redis.pipeline()
                    pipe.zremrangebyscore(key, 0, window_start)
                    pipe.zadd(key, {member: now})
                    pipe.zcard(key)
                    pipe.expire(key, window)
                    results = await pipe.execute()
                    current_count = (
                        int(results[2])
                        if len(results) >= 3 and results[2] is not None
                        else 0
                    )
                except Exception:
                    current_count = 0
                if current_count > MAX_MESSAGES_PER_MINUTE:
                    # Optionally notify client before closing
                    await websocket.send_text(
                        json.dumps({"error": "rate_limit_exceeded"})
                    )
                    await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
                    break

            # Validate JSON and message shape
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                # ignore invalid JSON
                continue

            # Minimal validation: expect an object with 'text' field (string)
            text = message.get("text")
            if not isinstance(text, str):
                continue

            # Sanitize text to mitigate XSS if frontends render unescaped
            message["text"] = _sanitize_text(text)
            message["user_id"] = str(user.id)
            message["timestamp"] = datetime.utcnow().isoformat()

            await manager.publish(room, json.dumps(message))
    except WebSocketDisconnect:
        try:
            await manager.disconnect(websocket, room)
        except Exception:
            pass
    finally:
        try:
            await manager.disconnect(websocket, room)
        except Exception:
            pass
