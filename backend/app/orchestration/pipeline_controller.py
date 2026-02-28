"""Pipeline Controller — manages the autonomous job application loop."""

import asyncio
import structlog
import time
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.core.redis_client import update_agent_status
from app.db.models import AgentExecution
from app.core.llm_router import get_llm, QuotaExceededError

logger = structlog.get_logger()

class ApplicationPipelineController:
    """Controls the end-to-end autonomous job application flow."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_full_pipeline(self, state: DigitalFTEState) -> DigitalFTEState:
        """Execute the full application pipeline for all jobs in the queue."""
        queue = state.get("automation_queue", [])
        total_jobs = len(queue)
        user_id = state.get("user_id")
        session_id = state.get("session_id")

        if not queue:
            logger.info("pipeline_empty_queue", session_id=session_id)
            state["response_text"] = "No jobs found in the queue to process."
            return state

        logger.info("pipeline_started", session_id=session_id, job_count=total_jobs)
        processed = 0
        state["waiting_for_user"] = False
        state["response_text"] = ""
        state["full_pipeline_requested"] = True # Ensure it stays true during loop

        # Import nodes here to avoid circular imports
        from app.agents.graph import (
            cv_tailor_node, 
            hr_finder_node, 
            email_drafter_node, 
            pdf_generator_node, 
            email_sender_node
        )

        while state.get("automation_queue"):
            job = state["automation_queue"][0] # Peek
            processed += 1
            state["current_work_item"] = job
            
            # Check if this job was JUST approved in this turn
            user_msg = state.get("user_message", "").lower()
            is_approval = any(w in user_msg for w in ["approve", "send", "proceed", "go ahead", "ok", "confirm"])
            
            # If we are resuming with an approval, we should run the email_sender directly
            if is_approval and state.get("draft_email"):
                try:
                    state = await self._run_node_with_logging(
                        "email_sender", email_sender_node, state, processed, total_jobs, 90
                    )
                    # Success! Pop from queue and continue to next job
                    state["automation_queue"].pop(0)
                    state["draft_cv"] = None
                    state["draft_email"] = None
                    state["draft_cover_letter"] = None
                    continue 
                except Exception as e:
                    logger.error("pipeline_resumption_failed", error=str(e))
                    # Fall through to normal flow or handle error
            
            try:
                # 1. Tailor CV
                state = await self._run_node_with_logging(
                    "cv_tailor", cv_tailor_node, state, processed, total_jobs, 10
                )

                # 2. Find HR
                state = await self._run_node_with_logging(
                    "hr_finder", hr_finder_node, state, processed, total_jobs, 30
                )

                # 3. Draft Email
                state = await self._run_node_with_logging(
                    "email_drafter", email_drafter_node, state, processed, total_jobs, 50
                )

                # 4. Generate PDF
                state = await self._run_node_with_logging(
                    "pdf_generator", pdf_generator_node, state, processed, total_jobs, 70
                )

                # 5. Send Email (Wait for approval if not already approved)
                # Before sending, we check if the user needs to approve.
                # In this loop, we always want to show the HitLBlock if it's a full pipeline run
                # to give the user the final say.
                
                # We stop the loop here, return state, and wait for the "APPROVE" message
                # The state will have waiting_for_user=True
                state["waiting_for_user"] = True
                state["current_agent"] = "supervisor"
                state["next_step"] = "email_sender" # Set next step for when they approve
                
                # Emit the approval request via WebSocket for the HitLBlock
                await event_bus.emit_approval_requested(
                    user_id=user_id,
                    agent_name="email_sender",
                    cv=state.get("draft_cv") or state.get("parsed_cv") or {},
                    cover_letter=state.get("draft_cover_letter") or "",
                    email=state.get("draft_email", {}).get("body", "") if isinstance(state.get("draft_email"), dict) else state.get("draft_email") or "",
                    application_id=state.get("current_work_item", {}).get("id", "pending")
                )
                
                state["response_text"] = "I've prepared the application for **{}**. Please review the tailored CV and email draft below before I send it.".format(job.get('company', 'this company'))
                
                return state

                # Update progress and POP from queue
                await self.emit_progress(user_id, session_id, "pipeline", processed, total_jobs, 100, f"Completed job {processed}/{total_jobs}")
                state["automation_queue"].pop(0)
                state["current_work_item"] = None
                state["draft_cv"] = None
                state["draft_email"] = None
                state["draft_cover_letter"] = None

            except Exception as e:
                logger.error("pipeline_job_failed", job_id=job.get("id"), error=str(e))
                state["errors"] = state.get("errors", []) + [f"Failed to process job {job.get('company')}: {str(e)}"]
                # Continue to next job despite failure
                continue

        state["automation_queue"] = []
        state["current_work_item"] = None
        state["waiting_for_user"] = False
        state["full_pipeline_requested"] = False
        state["response_text"] = f"🚀 **Autonomous Pipeline Complete**\nSuccessfully applied to {processed} jobs in one go using gpt-oss-120b."
        
        return state

    async def _run_node_with_logging(
        self, agent_name: str, node_func, state: DigitalFTEState, 
        job_index: int, total_jobs: int, base_progress: int
    ) -> DigitalFTEState:
        """Run a LangGraph node with full observability instrumentation."""
        user_id = state.get("user_id")
        session_id = state.get("session_id")
        
        start_time = time.time()
        
        # Calculate overall progress
        overall_progress = int(((job_index - 1) / total_jobs * 100) + (base_progress / total_jobs))
        
        # Emit start
        await self.emit_progress(user_id, session_id, agent_name, job_index, total_jobs, overall_progress, f"Executing {agent_name}")
        
        try:
            # Execute node
            try:
                result = await node_func(state)
            except QuotaExceededError:
                logger.warning("quota_exceeded_retry_fallback", agent=agent_name)
                result = await node_func(state)
            
            # Merge results back into state
            state.update(result)
            
            # REMOVED FORCE AUTONOMY: allow nodes to set waiting_for_user if needed
            # state["waiting_for_user"] = False
            # state["requires_user_input"] = False
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Log to DB
            await self._log_execution(
                user_id, session_id, agent_name, 
                input_data={"job": state.get("current_work_item")},
                output_data=result,
                execution_time_ms=execution_time_ms,
                status="completed"
            )
            
            return state
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            await self._log_execution(
                user_id, session_id, agent_name, 
                input_data={"job": state.get("current_work_item")},
                output_data={"error": str(e)},
                execution_time_ms=execution_time_ms,
                status="error"
            )
            raise e

    async def emit_progress(
        self, user_id: str, session_id: str, agent_name: str, 
        processed: int, total: int, progress_value: int, plan: str
    ):
        """Emit real-time progress to Redis and WebSocket."""
        # 1. Update Redis
        await update_agent_status(
            session_id=session_id,
            agent_name=agent_name,
            status="processing",
            progress=progress_value,
            plan=plan
        )

        # 2. Update WebSocket
        await event_bus.emit_agent_progress(
            user_id=user_id,
            agent_name=agent_name,
            step=processed,
            total_steps=total,
            current_action=plan,
            details=f"Job {processed} of {total}"
        )
        
        # Also broadcast for observability panel specifically as requested
        await event_bus.emit(user_id, "agent_update", {
            "agent": agent_name,
            "progress": progress_value,
            "status": "processing",
            "job_info": f"{processed}/{total}"
        })

    async def _log_execution(
        self, user_id: str, session_id: str, agent_name: str, 
        input_data: dict, output_data: dict, execution_time_ms: int, status: str
    ):
        """Save agent execution details to the database."""
        try:
            execution = AgentExecution(
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                action=f"pipeline_step_{agent_name}",
                input_data=input_data,
                output_data=output_data,
                execution_time_ms=execution_time_ms,
                status=status,
                llm_model="dual-chain-fallback" # Hardcoded for now, or extracted from response if possible
            )
            self.db.add(execution)
            await self.db.commit()
        except Exception as e:
            logger.error("db_log_failed", error=str(e))
            await self.db.rollback()
