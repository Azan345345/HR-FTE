import time
import json
import structlog
from typing import Dict, Any, List
import uuid

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.agents.prompts.hr_finder import HR_FINDER_SYSTEM_PROMPT, HR_FINDER_USER_PROMPT
from app.agents.cv_tailor import get_llm  # Reuse the LLM getter

logger = structlog.get_logger()

async def hr_finder_node(state: DigitalFTEState) -> dict:
    """
    HR Contact Intelligence Agent — Uses heuristic LLM search to find HR emails if tools are unavailable.
    """
    session_id = state.get("user_id", "unknown")
    
    # Process selected_jobs if available, else first job of jobs_found
    jobs_to_process = state.get("selected_jobs", [])
    if not jobs_to_process and state.get("jobs_found"):
        jobs_to_process = [state.get("jobs_found")[0]]
        
    if not jobs_to_process:
        return {
            "current_agent": "hr_finder",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["No jobs available to find HR contacts for."],
        }

    start_time = time.time()
    hr_contacts: List[dict] = state.get("hr_contacts", [])
    if hr_contacts is None:
        hr_contacts = []
    
    try:
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="hr_finder",
            plan="Analyze Job → Search for HR Contacts → Score Confidence",
            estimated_time=15.0,
        )

        llm = get_llm()

        for idx, job in enumerate(jobs_to_process):
            job_id = job.get("id", str(uuid.uuid4()))
            company_name = job.get("company", "Unknown Company")
            
            await event_bus.agent_progress(
                session_id=session_id,
                agent_name="hr_finder",
                step=idx + 1, total_steps=len(jobs_to_process),
                current_action=f"Finding HR contacts for: {company_name}",
            )

            # Invoke LLM to guess/search HR info heuristically
            user_content = HR_FINDER_USER_PROMPT.format(
                job_title=job.get("title", ""),
                company_name=company_name,
                job_description=job.get("description", "")[:1000]
            )

            messages = [
                SystemMessage(content=HR_FINDER_SYSTEM_PROMPT),
                HumanMessage(content=user_content)
            ]

            response = await llm.ainvoke(messages)
            content = response.content
            
            # Basic JSON cleanup
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            try:
                contact_data = json.loads(content)
            except json.JSONDecodeError:
                contact_data = {
                    "hr_name": "Hiring Manager",
                    "hr_email": f"careers@{company_name.lower().replace(' ', '')}.com",
                    "hr_title": "HR Manager",
                    "hr_linkedin": "",
                    "confidence_score": 0.5,
                    "source": "heuristic_fallback"
                }
                
            contact_data["job_id"] = str(job_id)
            hr_contacts.append(contact_data)
        
        elapsed = time.time() - start_time
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="hr_finder",
            result_summary=f"Found HR contacts for {len(jobs_to_process)} jobs.",
            time_taken=elapsed,
        )

        return {
            "hr_contacts": hr_contacts,
            "current_agent": "hr_finder",
            "agent_status": "completed",
            "agent_plan": "HR finding complete",
        }

    except Exception as e:
        logger.error("hr_finder_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="hr_finder",
            error_message=str(e),
        )
        return {
            "current_agent": "hr_finder",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
