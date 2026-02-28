"""WebSocket connection handler for real-time agent updates."""

from fastapi import WebSocket, WebSocketDisconnect
from app.core.event_bus import event_bus
from app.core.security import decode_access_token
import structlog

logger = structlog.get_logger()


async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections. Clients send a JWT token to authenticate."""
    # Accept first, then authenticate via message
    await websocket.accept()

    try:
        # Wait for auth message
        auth_msg = await websocket.receive_text()

        payload = decode_access_token(auth_msg)
        if not payload:
            await websocket.send_text('{"error": "Invalid token"}')
            await websocket.close()
            return

        user_id = payload.get("sub", "")
        if not user_id:
            await websocket.send_text('{"error": "Invalid token payload"}')
            await websocket.close()
            return

        # Re-register with the event bus (we already accepted above)
        # We need to track this connection ourselves
        if user_id not in event_bus._connections:
            event_bus._connections[user_id] = set()
        event_bus._connections[user_id].add(websocket)

        logger.info("ws_authenticated", user_id=user_id)
        await websocket.send_text('{"type": "connected", "data": {"status": "authenticated"}}')

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong or other client messages
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')

    except WebSocketDisconnect:
        if user_id:
            await event_bus.disconnect(user_id, websocket)
    except Exception as e:
        logger.error("ws_error", error=str(e))
        try:
            await websocket.close()
        except Exception:
            pass
