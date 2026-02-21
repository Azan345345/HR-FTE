import time
import json
import structlog
from typing import Dict, Any, List
import uuid

from langchain_core.messages import SystemMessage, HumanMessage

from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.agents.prompts.interview_prep import INTERVIEW_PREP_SYSTEM_PROMPT, INTERVIEW_PREP_USER_PROMPT
from app.agents.cv_tailor import get_llm

logger = structlog.get_logger()

async def interview_prep_node(state: DigitalFTEState) -> dict:
    """
    Interview Coach — Generates technical/behavioral questions,
    company research, salary tips, and study materials based on role.
    """
    session_id = state.get("user_id", "unknown")
    
    # Process selected_jobs if available, else first job of jobs_found
    jobs_to_process = state.get("selected_jobs", [])
    if not jobs_to_process and state.get("jobs_found"):
        jobs_to_process = [state.get("jobs_found")[0]]
        
    if not jobs_to_process:
        return {
            "current_agent": "interview_prep",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["No jobs available to prepare an interview for."],
        }
    
    parsed_cv = state.get("parsed_cv", {})
    start_time = time.time()
    interview_prep_data: List[dict] = state.get("interview_prep_data", [])
    if interview_prep_data is None:
        interview_prep_data = []

    try:
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="interview_prep",
            plan="Analyze Role & Company → Generate Questions → Compile Research",
            estimated_time=25.0,
        )

        llm = get_llm()

        for idx, job in enumerate(jobs_to_process):
            job_id = job.get("id", str(uuid.uuid4()))
            company_name = job.get("company", "Unknown Company")
            job_title = job.get("title", "Role")
            
            await event_bus.agent_progress(
                session_id=session_id,
                agent_name="interview_prep",
                step=idx + 1, total_steps=len(jobs_to_process),
                current_action=f"Synthesizing prep for: {job_title} at {company_name}",
            )

            user_content = INTERVIEW_PREP_USER_PROMPT.format(
                job_title=job_title,
                company_name=company_name,
                job_description=job.get("description", "")[:1500],
                candidate_summary=parsed_cv.get("summary", "")[:500] if parsed_cv else "Unknown"
            )

            messages = [
                SystemMessage(content=INTERVIEW_PREP_SYSTEM_PROMPT),
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
                prep_data = json.loads(content)
            except json.JSONDecodeError:
                prep_data = {
                    "company_research": {"overview": "Company information not available.", "culture_insights": ""},
                    "technical_questions": [],
                    "behavioral_questions": [],
                    "salary_research": {},
                    "tips": ["Review the job description thoroughly."]
                }
                
            prep_data["job_id"] = str(job_id)
            prep_data["id"] = str(uuid.uuid4())
            interview_prep_data.append(prep_data)
        
        elapsed = time.time() - start_time
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="interview_prep",
            result_summary=f"Synthesized interview materials for {len(jobs_to_process)} roles.",
            time_taken=elapsed,
        )

        return {
            "interview_prep_data": interview_prep_data,
            "current_agent": "interview_prep",
            "agent_status": "completed",
            "agent_plan": "Interview preparation complete",
        }

    except Exception as e:
        logger.error("interview_prep_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="interview_prep",
            error_message=str(e),
        )
        return {
            "current_agent": "interview_prep",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
