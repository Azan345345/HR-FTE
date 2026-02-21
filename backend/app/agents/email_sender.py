import time
import json
import structlog
from typing import Dict, Any, List
import uuid

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.agents.prompts.email_sender import EMAIL_SENDER_SYSTEM_PROMPT, EMAIL_SENDER_USER_PROMPT
from app.agents.cv_tailor import get_llm

logger = structlog.get_logger()

async def email_sender_node(state: DigitalFTEState) -> dict:
    session_id = state.get("user_id", "unknown")
    
    hr_contacts = state.get("hr_contacts", [])
    jobs_found = state.get("jobs_found", [])
    parsed_cv = state.get("parsed_cv", {})
    
    if not hr_contacts:
        return {
            "current_agent": "email_sender",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["No HR contacts available to email."],
        }

    start_time = time.time()
    pending_approvals = state.get("pending_approvals", [])
    if pending_approvals is None:
        pending_approvals = []
        
    try:
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="email_sender",
            plan="Draft personalized outreach emails for HR contacts",
            estimated_time=15.0,
        )

        llm = get_llm()
        
        # Build dictionary of jobs for quick lookup
        job_map = {str(j.get("id")): j for j in jobs_found}

        for idx, contact in enumerate(hr_contacts):
            job_id = contact.get("job_id")
            job = job_map.get(job_id, {})
            company_name = job.get("company", "the company")
            hr_name = contact.get("hr_name", "Hiring Manager")
            
            await event_bus.agent_progress(
                session_id=session_id,
                agent_name="email_sender",
                step=idx + 1, total_steps=len(hr_contacts),
                current_action=f"Drafting email to {hr_name} at {company_name}",
            )

            # Invoke LLM to draft email
            user_content = EMAIL_SENDER_USER_PROMPT.format(
                job_title=job.get("title", "the role"),
                company_name=company_name,
                hr_name=hr_name,
                candidate_summary=parsed_cv.get("summary", "")[:500] if parsed_cv else "",
                matched_skills=", ".join(job.get("matching_skills", [])[:5])
            )

            messages = [
                SystemMessage(content=EMAIL_SENDER_SYSTEM_PROMPT),
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
                email_data = json.loads(content)
            except json.JSONDecodeError:
                email_data = {
                    "subject": f"Application for {job.get('title', 'Role')}",
                    "body": f"Hi {hr_name},\n\nPlease find my application attached for the position at {company_name}.\n\nBest regards,"
                }
                
            email_data["job_id"] = str(job_id)
            email_data["hr_contact_id"] = contact.get("id", str(uuid.uuid4()))
            pending_approvals.append(email_data)
        
        elapsed = time.time() - start_time
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="email_sender",
            result_summary=f"Drafted emails for {len(hr_contacts)} contacts. Awaiting user approval.",
            time_taken=elapsed,
        )

        return {
            "pending_approvals": pending_approvals,
            "current_agent": "email_sender",
            "agent_status": "completed",
            "agent_plan": "Emails drafted, awaiting approval",
        }

    except Exception as e:
        logger.error("email_sender_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="email_sender",
            error_message=str(e),
        )
        return {
            "current_agent": "email_sender",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
