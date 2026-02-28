"""Observability routes — agent status, quota, execution logs."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, AgentExecution, Application, Job, HRContact
from app.api.deps import get_current_user
from app.core.quota_manager import get_all_quota_status
from app.schemas.schemas import QuotaStatusResponse

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/quota", response_model=list[QuotaStatusResponse])
async def get_quota_status():
    """Get current API quota usage for all models."""
    statuses = await get_all_quota_status()
    return [QuotaStatusResponse(**s) for s in statuses]


@router.get("/executions")
async def get_executions(
    session_id: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get agent execution logs."""
    query = (
        select(AgentExecution)
        .where(AgentExecution.user_id == current_user.id)
        .order_by(AgentExecution.created_at.desc())
        .limit(limit)
    )
    if session_id:
        query = query.where(AgentExecution.session_id == session_id)

    result = await db.execute(query)
    executions = result.scalars().all()

    return {
        "executions": [
            {
                "id": e.id,
                "agent_name": e.agent_name,
                "action": e.action,
                "status": e.status,
                "execution_time_ms": e.execution_time_ms,
                "tokens_input": e.tokens_input,
                "tokens_output": e.tokens_output,
                "llm_model": e.llm_model,
                "error_message": e.error_message,
                "created_at": str(e.created_at) if e.created_at else None,
            }
            for e in executions
        ],
        "total": len(executions),
    }


@router.get("/api-usage")
async def get_api_usage(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get per-model API usage stats aggregated from execution logs."""
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.user_id == current_user.id)
        .order_by(AgentExecution.created_at.desc())
        .limit(500)
    )
    execs = result.scalars().all()

    model_stats: dict = {}
    for e in execs:
        model = e.llm_model or "unknown"
        if model not in model_stats:
            model_stats[model] = {
                "model": model,
                "calls": 0,
                "success": 0,
                "failed": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "total_ms": 0,
            }
        s = model_stats[model]
        s["calls"] += 1
        if e.status == "success":
            s["success"] += 1
        else:
            s["failed"] += 1
        s["tokens_in"] += e.tokens_input or 0
        s["tokens_out"] += e.tokens_output or 0
        s["total_ms"] += e.execution_time_ms or 0

    models_out = []
    for s in model_stats.values():
        models_out.append({
            **s,
            "avg_latency_ms": s["total_ms"] // s["calls"] if s["calls"] else 0,
            "success_rate": round(s["success"] / s["calls"] * 100, 1) if s["calls"] else 0,
        })
    models_out.sort(key=lambda x: x["calls"], reverse=True)

    # Also fetch quota status
    quota = await get_all_quota_status()
    return {"models": models_out, "quota": quota}


@router.get("/gmail-watcher")
async def get_gmail_watcher_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Gmail watcher running status, watched application list with job/HR details."""
    from app.agents.gmail_watcher import gmail_watcher

    apps_result = await db.execute(
        select(Application).where(
            Application.user_id == current_user.id,
            Application.status == "sent",
        ).order_by(Application.created_at.desc())
    )
    apps = apps_result.scalars().all()

    # Enrich with job and HR contact info
    enriched = []
    for app in apps:
        job_title, company, hr_email = None, None, None
        if app.job_id:
            job_row = await db.execute(select(Job).where(Job.id == app.job_id))
            job = job_row.scalar_one_or_none()
            if job:
                job_title = job.title
                company = job.company
        if app.hr_contact_id:
            hr_row = await db.execute(select(HRContact).where(HRContact.id == app.hr_contact_id))
            hr = hr_row.scalar_one_or_none()
            if hr:
                hr_email = hr.hr_email
        enriched.append({
            "id": app.id,
            "job_id": app.job_id,
            "job_title": job_title,
            "company": company,
            "hr_email": hr_email,
            "status": app.status,
            "created_at": str(app.created_at) if app.created_at else None,
        })

    return {
        "is_running": gmail_watcher.is_running,
        "interval_seconds": gmail_watcher.interval,
        "apps_watched": len(enriched),
        "total_checks": gmail_watcher._total_checks,
        "replies_detected": gmail_watcher._replies_detected,
        "last_check_at": gmail_watcher._last_check_at,
        "watched_applications": enriched,
    }


@router.post("/gmail-watcher/toggle")
async def toggle_gmail_watcher(current_user: User = Depends(get_current_user)):
    """Start or stop the Gmail watcher background service."""
    from app.agents.gmail_watcher import gmail_watcher

    if gmail_watcher.is_running:
        await gmail_watcher.stop()
        return {"is_running": False, "message": "Gmail watcher stopped"}
    else:
        await gmail_watcher.start()
        return {"is_running": True, "message": "Gmail watcher started"}
