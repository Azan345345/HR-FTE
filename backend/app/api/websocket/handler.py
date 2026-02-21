"""
Digital FTE - WebSocket Connection Handler
"""

from fastapi import WebSocket, WebSocketDisconnect

from app.core.event_bus import connection_manager


async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Handle WebSocket connections for real-time agent observability."""
    await connection_manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send pings or commands
            data = await websocket.receive_text()
            # For now, echo acknowledgment
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
