"""
Digital FTE - Chat Service (business logic).
Orchestrates the LangGraph execution triggered from Chat natural language entry.
"""
from uuid import UUID
import uuid
import structlog
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import graph
from app.agents.state import DigitalFTEState
from app.db.models import AgentExecution

logger = structlog.get_logger()

async def process_chat_message(db: AsyncSession, user_id: UUID, message: str) -> Dict[str, Any]:
    """
    Submits the natural language intent directly to the agent supervisor graph 
    and awaits the computed completion states.
    """
    thread_id = str(uuid.uuid4())
    
    # Pre-populate known states (For brevity, typically we'd look up historical user Context here)
    initial_state: DigitalFTEState = {
        "user_id": str(user_id),
        "user_message": message,
        "raw_cv_text": "",
        "jobs_found": [],
        "errors": []
    }
    
    # Store the intended execution log
    execution = AgentExecution(
        id=uuid.UUID(thread_id),
        user_id=user_id,
        agent_name="supervisor_graph",
        status="running"
    )
    db.add(execution)
    await db.commit()

    config = {"configurable": {"thread_id": thread_id}}

    try:
        final_state = await graph.ainvoke(initial_state, config=config)
        
        execution.status = "completed"
        execution.result_data = final_state.get("chat_reply", "Agents finished their internal tasks.")
        await db.commit()

        return {
            "reply": final_state.get("chat_reply", "I've processed your request. Please check the dashboard context elements for updates!"),
            "state_snapshot": {
                "jobs_count": len(final_state.get("jobs_found", [])),
                "apps_count": len(final_state.get("pending_approvals", [])),
                "prep_count": len(final_state.get("interview_prep_data", []))
            }
        }
        
    except Exception as e:
        logger.error("graph_execution_failed", error=str(e), thread_id=thread_id)
        execution.status = "failed"
        execution.error_message = str(e)
        await db.commit()
        
        return {
            "reply": "I encountered an error trying to orchestrate the tasks.",
            "error": str(e)
        }
