"""Job search, listing, and detail routes."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import User, Job, JobSearch, UserCV
from app.api.deps import get_current_user
from app.schemas.schemas import (
    JobSearchRequest, JobResponse, JobListResponse,
)

router = APIRouter(prefix="/jobs", tags=["Job Search"])


@router.post("/search", response_model=JobListResponse)
async def search_jobs(
    body: JobSearchRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search for jobs matching a query. Triggers the Job Hunter agent."""
    from app.agents.job_hunter import search_jobs as agent_search
    from app.core.event_bus import event_bus

    # Find user's primary CV if any
    cv_result = await db.execute(
        select(UserCV).where(UserCV.user_id == current_user.id, UserCV.is_primary == True)
    )
    primary_cv = cv_result.scalar_one_or_none()

    # Create search record
    search = JobSearch(
        user_id=current_user.id,
        cv_id=primary_cv.id if primary_cv else None,
        search_query=body.query,
        target_role=body.query,
        target_location=body.location,
        status="searching",
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)

    try:
        await event_bus.emit_agent_started(current_user.id, "job_hunter", f"Searching for: {body.query}")

        # Run job search agent
        jobs_data = await agent_search(
            query=body.query,
            location=body.location,
            job_type=body.job_type,
            limit=body.limit,
            cv_data=primary_cv.parsed_data if primary_cv else None,
        )

        # Store jobs in DB
        job_models = []
        for jd in jobs_data:
            job = Job(
                search_id=search.id,
                title=jd.get("title", "Unknown"),
                company=jd.get("company", "Unknown"),
                location=jd.get("location"),
                salary_range=jd.get("salary_range"),
                job_type=jd.get("job_type"),
                description=jd.get("description", ""),
                requirements=jd.get("requirements", []),
                nice_to_have=jd.get("nice_to_have", []),
                responsibilities=jd.get("responsibilities", []),
                posted_date=jd.get("posted_date"),
                application_url=jd.get("application_url"),
                source=jd.get("source", "search"),
                match_score=jd.get("match_score"),
                matching_skills=jd.get("matching_skills", []),
                missing_skills=jd.get("missing_skills", []),
                raw_data=jd,
            )
            db.add(job)
            job_models.append(job)

        search.status = "completed"
        await db.commit()

        for jm in job_models:
            await db.refresh(jm)

        await event_bus.emit_agent_completed(
            current_user.id, "job_hunter",
            f"Found {len(job_models)} jobs",
        )

        return JobListResponse(
            jobs=[
                JobResponse(
                    id=j.id,
                    title=j.title,
                    company=j.company,
                    location=j.location,
                    salary_range=j.salary_range,
                    job_type=j.job_type,
                    description=j.description,
                    requirements=j.requirements or [],
                    source=j.source,
                    match_score=j.match_score,
                    matching_skills=j.matching_skills or [],
                    missing_skills=j.missing_skills or [],
                    application_url=j.application_url,
                    posted_date=j.posted_date,
                    created_at=str(j.created_at) if j.created_at else None,
                )
                for j in job_models
            ],
            total=len(job_models),
            search_id=search.id,
        )
    except Exception as e:
        search.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")


@router.get("/list", response_model=JobListResponse)
async def list_jobs(
    search_id: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List jobs from previous searches."""
    query = (
        select(Job)
        .join(JobSearch)
        .where(JobSearch.user_id == current_user.id)
        .order_by(Job.match_score.desc().nullslast())
        .offset(offset)
        .limit(limit)
    )
    if search_id:
        query = query.where(Job.search_id == search_id)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Count total
    count_q = (
        select(func.count(Job.id))
        .join(JobSearch)
        .where(JobSearch.user_id == current_user.id)
    )
    if search_id:
        count_q = count_q.where(Job.search_id == search_id)
    total = (await db.execute(count_q)).scalar() or 0

    return JobListResponse(
        jobs=[
            JobResponse(
                id=j.id,
                title=j.title,
                company=j.company,
                location=j.location,
                salary_range=j.salary_range,
                job_type=j.job_type,
                description=j.description,
                requirements=j.requirements or [],
                source=j.source,
                match_score=j.match_score,
                matching_skills=j.matching_skills or [],
                missing_skills=j.missing_skills or [],
                application_url=j.application_url,
                posted_date=j.posted_date,
                created_at=str(j.created_at) if j.created_at else None,
            )
            for j in jobs
        ],
        total=total,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific job by ID."""
    result = await db.execute(
        select(Job)
        .join(JobSearch)
        .where(Job.id == job_id, JobSearch.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        salary_range=job.salary_range,
        job_type=job.job_type,
        description=job.description,
        requirements=job.requirements or [],
        source=job.source,
        match_score=job.match_score,
        matching_skills=job.matching_skills or [],
        missing_skills=job.missing_skills or [],
        application_url=job.application_url,
        posted_date=job.posted_date,
        created_at=str(job.created_at) if job.created_at else None,
    )
