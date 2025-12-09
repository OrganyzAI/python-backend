**WebSocket Infrastructure**: Quick setup

- **Purpose**: Provide real-time sync across connected clients and across multiple app instances using Redis pub/sub.
- **Components**:

  - `app.api.websocket_manager.WebSocketManager`: manages local WebSocket connections and subscribes to Redis channels `ws:{room}`.
  - `app.api.routes.ws`: WebSocket endpoint at `GET /api/v1/ws/{room}` (path under API prefix).
  - Uses existing Redis client configured via `REDIS_URL` in `app.core.config.Settings`.

- **How it works**:

  - Each connected client opens a WebSocket to `/api/v1/ws/{room}`.
  - When a client sends a text message, the endpoint publishes the message to Redis channel `ws:{room}`.
  - The `WebSocketManager` subscribes to `ws:*` and forwards published messages to all local WebSocket connections in the given room.
  - This allows multiple app instances to broadcast to each other's connected clients.

- **Env / Config**:

  - Ensure `REDIS_URL` is configured in the project's environment (default: `redis://redis:6379/0`).

- **Frontend example** (browser JS):

```js
const ws = new WebSocket(`wss://your-backend.example.com/api/v1/ws/room-123`);
ws.addEventListener("message", (ev) => console.log("msg", ev.data));
ws.addEventListener("open", () => ws.send(JSON.stringify({ type: "hello" })));
```

- **Notes & next steps**:
  - Messages are sent/received as plain text; consider JSON schema enforcement and auth.
  - Add authentication (JWT in query param/header) and room access checks as needed.
  - Consider rate limiting and maximum connections per client.
