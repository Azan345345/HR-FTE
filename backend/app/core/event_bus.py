"""WebSocket event bus for real-time agent observability."""

import json
import asyncio
import structlog
from typing import Dict, Set
from fastapi import WebSocket

logger = structlog.get_logger()


class EventBus:
    """Manages WebSocket connections and broadcasts agent events."""

    def __init__(self):
        # user_id → set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket):
        """Register a new WebSocket connection for a user."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(websocket)
        logger.info("ws_connected", user_id=user_id)

    async def disconnect(self, user_id: str, websocket: WebSocket):
        """Remove a WebSocket connection."""
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(websocket)
                if not self._connections[user_id]:
                    del self._connections[user_id]
        logger.info("ws_disconnected", user_id=user_id)

    async def emit(self, user_id: str, event_type: str, data: dict):
        """Send an event to all connections for a user."""
        message = json.dumps({"type": event_type, "data": data})
        async with self._lock:
            connections = self._connections.get(user_id, set()).copy()

        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.get(user_id, set()).discard(ws)

    async def emit_agent_started(self, user_id: str, agent_name: str, plan: str = "", thought: str = None):
        payload = {"agent_name": agent_name, "plan": plan, "status": "processing"}
        if thought:
            payload["thought"] = thought
        await self.emit(user_id, "agent_started", payload)

    async def emit_agent_progress(
        self, user_id: str, agent_name: str,
        step: int, total_steps: int, current_action: str, details: str = ""
    ):
        await self.emit(user_id, "agent_progress", {
            "agent_name": agent_name,
            "step": step,
            "total_steps": total_steps,
            "current_action": current_action,
            "details": details,
        })
        
        # Also emit a generic log entry for the sidebar
        await self.emit(user_id, "log_entry", {
            "agent": agent_name,
            "title": current_action,
            "desc": details,
            "status": "running",
            "emoji": "🔄"
        })

    async def emit_agent_completed(
        self, user_id: str, agent_name: str,
        result_summary: str = "", time_taken: float = 0, tokens_used: int = 0,
        thought: str = None
    ):
        payload = {
            "agent_name": agent_name,
            "result_summary": result_summary,
            "time_taken": time_taken,
            "tokens_used": tokens_used,
            "status": "completed",
        }
        if thought:
            payload["thought"] = thought
        await self.emit(user_id, "agent_completed", payload)

        log_payload = {
            "agent": agent_name,
            "title": "Task Completed",
            "desc": result_summary,
            "status": "done",
            "emoji": "✅",
            "duration": f"{time_taken}s" if time_taken else None,
            "tokens": f"{tokens_used} tokens" if tokens_used else None,
        }
        if thought:
            log_payload["thought"] = thought
        await self.emit(user_id, "log_entry", log_payload)

    async def emit_agent_error(
        self, user_id: str, agent_name: str,
        error_message: str, retry_count: int = 0
    ):
        await self.emit(user_id, "agent_error", {
            "agent_name": agent_name,
            "error_message": error_message,
            "retry_count": retry_count,
            "status": "error",
        })
        
        # Also emit a generic log entry for the sidebar
        await self.emit(user_id, "log_entry", {
            "agent": agent_name,
            "title": "Error Occurred",
            "desc": error_message,
            "status": "error",
            "emoji": "❌"
        })

    async def emit_log_entry(
        self, user_id: str, agent: str, title: str, desc: str = "",
        status: str = "running", emoji: str = None, thought: str = None
    ):
        """Emit a direct log entry to the sidebar timeline."""
        emoji_map = {
            "supervisor": "🟢", "cv_parser": "📄", "job_hunter": "🔍",
            "cv_tailor": "✍️", "hr_finder": "📧", "email_sender": "📤",
            "interview_prep": "🎤", "doc_generator": "📝",
        }
        payload = {
            "agent": agent,
            "title": title,
            "desc": desc,
            "status": status,
            "emoji": emoji or emoji_map.get(agent, "🤖"),
        }
        if thought:
            payload["thought"] = thought
        await self.emit(user_id, "log_entry", payload)

    async def emit_workflow_update(self, user_id: str, active_node: str, completed_nodes: list, pending_nodes: list):
        await self.emit(user_id, "workflow_update", {
            "active_node": active_node,
            "completed_nodes": completed_nodes,
            "pending_nodes": pending_nodes,
        })

    async def emit_approval_requested(
        self, user_id: str, agent_name: str, 
        cv: dict, cover_letter: str, email: str, application_id: str = ""
    ):
        await self.emit(user_id, "approval_requested", {
            "agent_name": agent_name,
            "cv": cv,
            "cover_letter": cover_letter,
            "email": email,
            "application_id": application_id,
            "status": "waiting",
        })


# Global singleton event bus
event_bus = EventBus()
