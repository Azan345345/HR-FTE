"""
Digital FTE - Supervisor Agent
Routes user requests to appropriate specialized agents.
"""
import json
import structlog
from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.agents.cv_tailor import get_llm
from app.agents.prompts.supervisor import SUPERVISOR_SYSTEM_PROMPT, SUPERVISOR_USER_PROMPT

logger = structlog.get_logger()

async def supervisor_node(state: DigitalFTEState) -> dict:
    """
    Master Orchestrator — Routes tasks to specialized agents.
    Uses LLM to classify natural language intent and manage workflow state.
    """
    session_id = state.get("user_id", "unknown")
    user_message = state.get("user_message", "")
    current_agent = state.get("current_agent", "supervisor")
    
    # If we are looping back from a completion, just stop unless told otherwise
    if current_agent != "supervisor" and state.get("agent_status") == "completed":
        return {"next_step": "end", "current_agent": "supervisor"}

    if not user_message:
        # Fallbacks for programmatic invocations without natural chat
        if not state.get("parsed_cv") and state.get("raw_cv_path"):
            return {"next_step": "parse_cv", "current_agent": "supervisor"}
        if state.get("jobs_found") and not state.get("tailored_cvs"):
            return {"next_step": "tailor_cv", "current_agent": "supervisor"}
        if state.get("tailored_cvs") and not state.get("hr_contacts"):
            return {"next_step": "find_hr", "current_agent": "supervisor"}
        return {"next_step": "end", "current_agent": "supervisor"}

    try:
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="supervisor",
            plan="Analyzing user intent to route to the correct agent node.",
            estimated_time=5.0,
        )

        llm = get_llm()
        state_summary = list(state.keys())
        missing_elements = "None"
        if state.get("jobs_found"):
            missing = []
            if not state.get("hr_contacts"): missing.append("HR Contacts")
            if not state.get("tailored_cvs"): missing.append("Tailored CV")
            missing_elements = ", ".join(missing) if missing else "None"

        user_content = SUPERVISOR_USER_PROMPT.format(
            user_message=user_message,
            state_summary=state_summary,
            missing_elements=missing_elements
        )

        messages = [
            SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
            HumanMessage(content=user_content)
        ]

        response = await llm.ainvoke(messages)
        content = response.content
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()

        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            decision = {"next_step": "respond_to_user", "reply": "I'm not sure how to handle that right now."}

        next_step = decision.get("next_step", "end")
        reply = decision.get("reply", "Routing request...")

        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="supervisor",
            result_summary=f"Decision: {next_step}",
            time_taken=0.0,
        )

        # Chat router catches respond_to_user, otherwise graph routing takes over
        return {
            "next_step": next_step if next_step != "respond_to_user" else "end",
            "current_agent": "supervisor",
            "chat_reply": reply, 
            "agent_status": "routing"
        }

    except Exception as e:
        logger.error("supervisor_failed", error=str(e))
        return {"next_step": "end", "current_agent": "supervisor"}
