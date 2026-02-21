"""
Digital FTE - Job Service
Business logic for job searching, storing, listing, and management.
"""

import uuid
import structlog
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, JobSearch, UserCV
from app.agents.tools.job_tools import search_all_sources
from app.utils.scoring import score_jobs_against_cv

logger = structlog.get_logger()


async def search_jobs(
    user_id: UUID,
    query: str,
    target_role: Optional[str],
    target_location: Optional[str],
    num_results: int,
    db: AsyncSession,
) -> List[dict]:
    """
    Search for jobs via external APIs, score against user's primary CV,
    and store results in DB.
    """
    # Get user's primary CV for scoring
    parsed_cv = {}
    result = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    primary_cv = result.scalar_one_or_none()
    if primary_cv and primary_cv.parsed_data:
        parsed_cv = primary_cv.parsed_data

    # Build search query
    search_query = query
    if target_role:
        search_query = target_role
    if target_location:
        search_query = f"{search_query} {target_location}"

    # Create job search record
    job_search = JobSearch(
        user_id=user_id,
        query=search_query,
        target_role=target_role or "",
        target_location=target_location or "",
        filters={},
    )
    db.add(job_search)
    await db.flush()

    # Search external APIs
    raw_jobs = await search_all_sources(
        query=search_query,
        location=target_location or "",
        num_results=num_results,
    )

    if not raw_jobs:
        await db.commit()
        return []

    # Score against CV
    if parsed_cv:
        scored_jobs = score_jobs_against_cv(raw_jobs, parsed_cv)
    else:
        scored_jobs = [{**j, "match_score": 0, "matching_skills": [], "missing_skills": []} for j in raw_jobs]

    # Store jobs in DB
    stored_jobs = []
    for j in scored_jobs:
        job = Job(
            search_id=job_search.id,
            title=j.get("title", ""),
            company=j.get("company", ""),
            location=j.get("location", ""),
            salary_range=j.get("salary_range", ""),
            job_type=j.get("job_type", ""),
            description=j.get("description", "")[:5000],  # Trim long descriptions
            requirements=j.get("requirements", []),
            nice_to_have=j.get("nice_to_have", []),
            responsibilities=j.get("responsibilities", []),
            posted_date=j.get("posted_date", ""),
            application_url=j.get("application_url", ""),
            source=j.get("source", ""),
            match_score=j.get("match_score", 0),
            matching_skills=j.get("matching_skills", []),
            missing_skills=j.get("missing_skills", []),
        )
        db.add(job)
        stored_jobs.append(job)

    job_search.results_count = len(stored_jobs)
    await db.commit()

    # Refresh to get IDs
    for job in stored_jobs:
        await db.refresh(job)

    logger.info("jobs_stored", count=len(stored_jobs), search_id=str(job_search.id))
    return stored_jobs


async def list_user_jobs(user_id: UUID, db: AsyncSession) -> List[Job]:
    """List all jobs from the user's searches, most recent first."""
    result = await db.execute(
        select(Job)
        .join(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(Job.match_score.desc().nullslast())
    )
    return result.scalars().all()


async def get_job(job_id: UUID, user_id: UUID, db: AsyncSession) -> Job:
    """Get a single job by ID, verifying ownership."""
    result = await db.execute(
        select(Job)
        .join(JobSearch)
        .where(Job.id == job_id, JobSearch.user_id == user_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def list_job_searches(user_id: UUID, db: AsyncSession) -> List[JobSearch]:
    """List all job searches by the user."""
    result = await db.execute(
        select(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(JobSearch.created_at.desc())
    )
    return result.scalars().all()
