"""Dashboard statistics routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.database import get_db
from app.db.models import User, UserCV, Job, JobSearch, Application, InterviewPrep, AgentExecution
from app.api.deps import get_current_user
from app.schemas.schemas import DashboardStatsResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics for the current user."""

    # Total CVs
    cv_count = (await db.execute(
        select(func.count(UserCV.id)).where(UserCV.user_id == current_user.id)
    )).scalar() or 0

    # Total jobs found
    job_count = (await db.execute(
        select(func.count(Job.id))
        .join(JobSearch)
        .where(JobSearch.user_id == current_user.id)
    )).scalar() or 0

    # Total applications
    app_count = (await db.execute(
        select(func.count(Application.id)).where(Application.user_id == current_user.id)
    )).scalar() or 0

    # Total interview preps
    interview_count = (await db.execute(
        select(func.count(InterviewPrep.id)).where(InterviewPrep.user_id == current_user.id)
    )).scalar() or 0

    # Application pipeline
    pipeline = {}
    for status_val in ["pending_approval", "approved", "sent", "delivered", "opened", "replied", "interview_scheduled"]:
        count = (await db.execute(
            select(func.count(Application.id)).where(
                Application.user_id == current_user.id,
                Application.status == status_val,
            )
        )).scalar() or 0
        pipeline[status_val] = count

    # Match score distribution
    distribution = {"90_100": 0, "70_89": 0, "50_69": 0, "below_50": 0}
    jobs_result = await db.execute(
        select(Job.match_score)
        .join(JobSearch)
        .where(JobSearch.user_id == current_user.id, Job.match_score.isnot(None))
    )
    for (score,) in jobs_result.all():
        if score >= 90:
            distribution["90_100"] += 1
        elif score >= 70:
            distribution["70_89"] += 1
        elif score >= 50:
            distribution["50_69"] += 1
        else:
            distribution["below_50"] += 1

    # Token stats from AgentExecution
    token_result = await db.execute(
        select(
            func.sum(AgentExecution.tokens_input).label("input"),
            func.sum(AgentExecution.tokens_output).label("output")
        ).where(AgentExecution.user_id == current_user.id)
    )
    token_row = token_result.one()
    total_tokens = (token_row.input or 0) + (token_row.output or 0)
    total_cost = total_tokens * 0.00002 # Mock cost: $0.02 per 1k tokens

    return DashboardStatsResponse(
        total_cvs=cv_count,
        total_jobs_found=job_count,
        total_applications=app_count,
        total_interviews=interview_count,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 2),
        budget_limit=5.00,
        recent_activity=[],
        application_pipeline=pipeline,
        match_score_distribution=distribution,
    )
