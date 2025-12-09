from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str):
    """Simple WebSocket endpoint that forwards client messages to Redis
    and receives published messages via the WebSocketManager (attached to
    the app state) to broadcast to local clients.
    """
    manager = websocket.app.state.ws_manager
    await manager.connect(websocket, room)
    try:
        while True:
            # receive text from client and publish to Redis so other instances
            # receive it and forward to their connected clients
            data = await websocket.receive_text()
            await manager.publish(room, data)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, room)
