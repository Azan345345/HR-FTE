"""
Digital FTE - CV Tailor Agent
Rewrites CVs to match job descriptions using LLMs.
"""

import time
import json
import structlog
from typing import Dict, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.config import settings
from app.agents.state import DigitalFTEState
from app.core.event_bus import event_bus
from app.agents.prompts.cv_tailor import CV_TAILOR_SYSTEM_PROMPT, CV_TAILOR_USER_PROMPT

logger = structlog.get_logger()

# Logic to pick LLM (reused from router concept but simpler for agent node)
def get_llm():
    if settings.GOOGLE_AI_API_KEY:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GOOGLE_AI_API_KEY,
            temperature=0.2, # Low temp for factual adherence
        )
    elif settings.GROQ_API_KEY:
        # Fallback to Llama 3 on Groq
        return ChatGroq(
            model="llama3-70b-8192",
            api_key=settings.GROQ_API_KEY,
            temperature=0.2,
        )
    else:
        raise ValueError("No LLM API keys configured")


async def cv_tailor_node(state: DigitalFTEState) -> dict:
    """
    CV Transformation Specialist — Rewrites CV targeting specific job,
    optimizes keywords, restructures experience, preserves truthfulness.
    """
    session_id = state.get("user_id", "unknown")
    parsed_cv = state.get("parsed_cv", {})
    job_description = state.get("job_description", {}) # Passed in state

    if not parsed_cv or not job_description:
        return {
            "current_agent": "cv_tailor",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["Missing parsed CV or job description"],
        }

    start_time = time.time()
    
    try:
        # ── Step 1: Emit started ───────────────────
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="cv_tailor",
            plan="Analyze Job → Rewrite CV Content → General JSON → Validate",
            estimated_time=15.0,
        )

        llm = get_llm()

        # ── Step 2: Prepare Prompt ─────────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="cv_tailor",
            step=1, total_steps=3,
            current_action=f"Analyzing job: {job_description.get('title', 'Target Role')}",
        )

        user_content = CV_TAILOR_USER_PROMPT.format(
            job_title=job_description.get("title", ""),
            job_company=job_description.get("company", ""),
            job_description=job_description.get("description", "")[:2000], # Truncate if too long
            job_requirements=str(job_description.get("requirements", [])),
            cv_json=json.dumps(parsed_cv, indent=2)
        )

        messages = [
            SystemMessage(content=CV_TAILOR_SYSTEM_PROMPT),
            HumanMessage(content=user_content)
        ]

        # ── Step 3: Invoke LLM ─────────────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="cv_tailor",
            step=2, total_steps=3,
            current_action="Rewriting CV logic...",
        )

        response = await llm.ainvoke(messages)
        
        # ── Step 4: Parse & Validate ───────────────
        content = response.content
        # Basic JSON cleanup
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()

        tailored_data = json.loads(content)
        
        logger.info("cv_tailored", 
                   job=job_description.get("title"), 
                   original_role=parsed_cv.get("experience", [{}])[0].get("role"))

        # ── Step 5: Emit completed ─────────────────
        elapsed = time.time() - start_time
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="cv_tailor",
            result_summary="CV successfully retargeted for relevance",
            time_taken=elapsed,
        )

        return {
            "tailored_cv": tailored_data, # Store in state for next steps (e.g. PDF generation)
            "current_agent": "cv_tailor",
            "agent_status": "completed",
            "agent_plan": "Tailoring complete",
            # We assume the caller might want to persist this
        }

    except Exception as e:
        logger.error("cv_tailor_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="cv_tailor",
            error_message=str(e),
        )
        return {
            "current_agent": "cv_tailor",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
