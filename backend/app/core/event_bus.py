"""
Digital FTE - WebSocket Event Bus
Emits agent status, progress, and workflow events to connected frontends.
"""

import json
import structlog
from typing import Dict, Optional
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """Manages active WebSocket connections by session_id."""

    def __init__(self):
        self._connections: Dict[str, WebSocket] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[session_id] = websocket
        logger.info("ws_connected", session_id=session_id)

    def disconnect(self, session_id: str):
        self._connections.pop(session_id, None)
        logger.info("ws_disconnected", session_id=session_id)

    async def send_event(self, session_id: str, event_type: str, data: dict):
        """Send a typed event to a specific session."""
        ws = self._connections.get(session_id)
        if ws:
            try:
                await ws.send_json({"type": event_type, "data": data})
            except Exception as e:
                logger.warning("ws_send_failed", session_id=session_id, error=str(e))
                self.disconnect(session_id)

    async def broadcast(self, event_type: str, data: dict):
        """Broadcast an event to all connected sessions."""
        dead = []
        for sid, ws in self._connections.items():
            try:
                await ws.send_json({"type": event_type, "data": data})
            except Exception:
                dead.append(sid)
        for sid in dead:
            self.disconnect(sid)


# Singleton
connection_manager = ConnectionManager()


class EventBus:
    """
    High-level event emitter for agent observability.
    Events are forwarded to WebSocket clients.
    """

    def __init__(self, manager: ConnectionManager):
        self._manager = manager

    async def agent_started(
        self, session_id: str, agent_name: str, plan: str = "", estimated_time: Optional[float] = None
    ):
        await self._manager.send_event(session_id, "agent_started", {
            "agent_name": agent_name,
            "plan": plan,
            "estimated_time": estimated_time,
        })

    async def agent_progress(
        self, session_id: str, agent_name: str, step: int, total_steps: int, current_action: str, details: str = ""
    ):
        await self._manager.send_event(session_id, "agent_progress", {
            "agent_name": agent_name,
            "step": step,
            "total_steps": total_steps,
            "current_action": current_action,
            "details": details,
        })

    async def agent_completed(
        self, session_id: str, agent_name: str, result_summary: str, time_taken: float, tokens_used: int = 0
    ):
        await self._manager.send_event(session_id, "agent_completed", {
            "agent_name": agent_name,
            "result_summary": result_summary,
            "time_taken": time_taken,
            "tokens_used": tokens_used,
        })

    async def agent_error(
        self, session_id: str, agent_name: str, error_message: str, retry_count: int = 0, fallback_action: str = ""
    ):
        await self._manager.send_event(session_id, "agent_error", {
            "agent_name": agent_name,
            "error_message": error_message,
            "retry_count": retry_count,
            "fallback_action": fallback_action,
        })

    async def model_switch(
        self, session_id: str, from_model: str, to_model: str, reason: str
    ):
        await self._manager.send_event(session_id, "model_switch", {
            "from_model": from_model,
            "to_model": to_model,
            "reason": reason,
        })

    async def quota_warning(
        self, session_id: str, provider: str, usage_percent: float, remaining: int
    ):
        await self._manager.send_event(session_id, "quota_warning", {
            "provider": provider,
            "usage_percent": usage_percent,
            "remaining": remaining,
        })

    async def workflow_update(
        self, session_id: str, graph_state: str, active_node: str,
        completed_nodes: list, pending_nodes: list
    ):
        await self._manager.send_event(session_id, "workflow_update", {
            "graph_state": graph_state,
            "active_node": active_node,
            "completed_nodes": completed_nodes,
            "pending_nodes": pending_nodes,
        })


event_bus = EventBus(connection_manager)
