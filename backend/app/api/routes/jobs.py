"""
Digital FTE - Jobs Routes
Search, list, and retrieve job listings.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.job import JobSearchRequest, JobRead, JobListItem, JobSearchResponse
from app.services.job_service import search_jobs, list_user_jobs, get_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs_endpoint(
    request: JobSearchRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Search for jobs matching the query, scored against the user's primary CV."""
    jobs = await search_jobs(
        user_id=user.id,
        query=request.query,
        target_role=request.target_role,
        target_location=request.target_location,
        num_results=request.num_results,
        db=db,
    )

    job_items = [
        JobListItem(
            id=j.id,
            title=j.title,
            company=j.company,
            location=j.location,
            job_type=j.job_type,
            salary_range=j.salary_range,
            source=j.source,
            match_score=j.match_score,
            matching_skills=j.matching_skills or [],
            created_at=j.created_at,
        )
        for j in jobs
    ]

    return JobSearchResponse(
        jobs=job_items,
        total=len(job_items),
        query=request.query,
    )


@router.get("/", response_model=List[JobListItem])
async def list_jobs_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all jobs from the user's searches."""
    jobs = await list_user_jobs(user.id, db)
    return [
        JobListItem(
            id=j.id,
            title=j.title,
            company=j.company,
            location=j.location,
            job_type=j.job_type,
            salary_range=j.salary_range,
            source=j.source,
            match_score=j.match_score,
            matching_skills=j.matching_skills or [],
            created_at=j.created_at,
        )
        for j in jobs
    ]


@router.get("/{job_id}", response_model=JobRead)
async def get_job_endpoint(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full job details."""
    j = await get_job(job_id, user.id, db)
    return JobRead(
        id=j.id,
        title=j.title,
        company=j.company,
        location=j.location,
        salary_range=j.salary_range,
        job_type=j.job_type,
        description=j.description,
        requirements=j.requirements or [],
        nice_to_have=j.nice_to_have or [],
        responsibilities=j.responsibilities or [],
        posted_date=j.posted_date,
        application_url=j.application_url,
        source=j.source,
        match_score=j.match_score,
        matching_skills=j.matching_skills or [],
        missing_skills=j.missing_skills or [],
        created_at=j.created_at,
    )
