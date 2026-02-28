"""Gmail Watcher — background service to detect HR replies to job applications."""

import asyncio
import structlog
from typing import List
from app.core.event_bus import event_bus
from app.db.database import AsyncSessionLocal
from sqlalchemy import select
from app.db.models import Application, Job

logger = structlog.get_logger()

class GmailWatcher:
    """Service to poll Gmail for replies every 60 seconds."""

    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self.is_running = False
        self._task = None
        self._total_checks: int = 0
        self._replies_detected: int = 0
        self._last_check_at: str | None = None

    async def start(self):
        """Start the background watching loop."""
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("gmail_watcher_started", interval=self.interval)

    async def stop(self):
        """Stop the background watching loop."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("gmail_watcher_stopped")

    async def _run_loop(self):
        """Main polling loop."""
        while self.is_running:
            try:
                await self._check_for_replies()
            except Exception as e:
                logger.error("gmail_watcher_error", error=str(e))
            
            await asyncio.sleep(self.interval)

    async def _check_for_replies(self):
        """Check for new messages in relevant Gmail threads."""
        from datetime import datetime, timezone
        self._total_checks += 1
        self._last_check_at = datetime.now(timezone.utc).isoformat()

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Application).where(Application.status == "sent")
            )
            apps = result.scalars().all()

            for app in apps:
                # Real implementation: call Gmail API to check threads.
                # Currently a stub — integration requires valid Gmail OAuth token.
                pass

    async def handle_reply_detected(self, user_id: str, app_id: str, snippet: str):
        """Process a detected reply."""
        self._replies_detected += 1
        logger.info("hr_reply_detected", user_id=user_id, app_id=app_id)
        
        # 1. Notify UI
        await event_bus.emit_agent_started(user_id, "gmail_watcher", "HR Reply Detected!")
        await event_bus.emit_agent_progress(user_id, "gmail_watcher", 1, 1, f"Reply: {snippet[:50]}...")
        
        # 2. Check if it's an interview offer
        is_interview = any(word in snippet.lower() for word in ["interview", "meet", "schedule", "call", "chat"])
        
        if is_interview:
            await event_bus.emit_agent_completed(user_id, "gmail_watcher", "Interview offered! Initiating prep agent.")
            # Trigger interview prep flow (would be handled by supervisor/graph)
        else:
            await event_bus.emit_agent_completed(user_id, "gmail_watcher", "Reply received. User notified.")

# Global instance
gmail_watcher = GmailWatcher()
