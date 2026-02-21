"""
Digital FTE - Job Hunter Agent
Searches multiple job platforms, scores against parsed CV, stores results.
"""

import time
import uuid
import structlog

from app.agents.state import DigitalFTEState
from app.agents.tools.job_tools import search_all_sources
from app.utils.scoring import score_jobs_against_cv
from app.core.event_bus import event_bus

logger = structlog.get_logger()


async def job_hunter_node(state: DigitalFTEState) -> dict:
    """
    Job Market Intelligence Scout — Full pipeline:
    1. Build search query from state
    2. Search SerpAPI + JSearch
    3. Score and rank against parsed CV
    4. Emit WebSocket events
    """
    session_id = state.get("user_id", "unknown")
    search_query = state.get("search_query", "")
    target_role = state.get("target_role", "")
    target_location = state.get("target_location", "")
    parsed_cv = state.get("parsed_cv", {})

    if not search_query and not target_role:
        return {
            "current_agent": "job_hunter",
            "agent_status": "error",
            "errors": state.get("errors", []) + ["No search query or target role provided"],
        }

    start_time = time.time()

    try:
        # ── Step 1: Emit started ───────────────────
        await event_bus.agent_started(
            session_id=session_id,
            agent_name="job_hunter",
            plan="Search job platforms → Score against CV → Rank results",
            estimated_time=20.0,
        )

        # ── Step 2: Build query ────────────────────
        query = search_query or target_role
        if target_location:
            query = f"{query} {target_location}"

        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="job_hunter",
            step=1, total_steps=3,
            current_action=f"Searching for: {query}",
        )

        # ── Step 3: Search all sources ─────────────
        raw_jobs = await search_all_sources(
            query=query,
            location=target_location,
            num_results=10,
        )

        if not raw_jobs:
            await event_bus.agent_completed(
                session_id=session_id,
                agent_name="job_hunter",
                result_summary="No jobs found matching your criteria",
                time_taken=time.time() - start_time,
            )
            return {
                "jobs_found": [],
                "current_agent": "job_hunter",
                "agent_status": "completed",
                "agent_plan": "No jobs found",
            }

        logger.info("jobs_fetched", count=len(raw_jobs))

        # ── Step 4: Score against CV ───────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="job_hunter",
            step=2, total_steps=3,
            current_action=f"Scoring {len(raw_jobs)} jobs against your CV",
        )

        if parsed_cv:
            scored_jobs = score_jobs_against_cv(raw_jobs, parsed_cv)
        else:
            # No CV to score against, assign default score
            scored_jobs = [{**j, "match_score": 0, "matching_skills": [], "missing_skills": []} for j in raw_jobs]

        # Add unique IDs
        for job in scored_jobs:
            if "id" not in job or not job["id"]:
                job["id"] = str(uuid.uuid4())

        # ── Step 5: Emit completed ─────────────────
        await event_bus.agent_progress(
            session_id=session_id,
            agent_name="job_hunter",
            step=3, total_steps=3,
            current_action="Finalizing results",
        )

        elapsed = time.time() - start_time
        top_match = scored_jobs[0] if scored_jobs else {}
        await event_bus.agent_completed(
            session_id=session_id,
            agent_name="job_hunter",
            result_summary=f"Found {len(scored_jobs)} jobs. Top match: {top_match.get('title', 'N/A')} at {top_match.get('company', 'N/A')} ({top_match.get('match_score', 0)}%)",
            time_taken=elapsed,
        )

        return {
            "jobs_found": scored_jobs,
            "current_agent": "job_hunter",
            "agent_status": "completed",
            "agent_plan": f"Found and scored {len(scored_jobs)} jobs",
        }

    except Exception as e:
        logger.error("job_hunter_failed", error=str(e))
        await event_bus.agent_error(
            session_id=session_id,
            agent_name="job_hunter",
            error_message=str(e),
        )
        return {
            "current_agent": "job_hunter",
            "agent_status": "error",
            "errors": state.get("errors", []) + [str(e)],
        }
