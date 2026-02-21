"""
Digital FTE - Observability Service
Provides data aggregations for the frontend dashboard and execution logs.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Dict, Any, List
from uuid import UUID

from app.db.models import AgentExecution, Job, Application, CV, InterviewPrep

async def get_dashboard_stats(db: AsyncSession, user_id: UUID) -> Dict[str, int]:
    """Retrieve top-level counts for the dashboard stats cards."""
    
    # Run independent count queries
    cvs_query = select(func.count(CV.id)).where(CV.user_id == user_id)
    jobs_query = select(func.count(Job.id)) # Jobs are globally harvested but we can count total available
    apps_query = select(func.count(Application.id)).where(Application.user_id == user_id)
    preps_query = select(func.count(InterviewPrep.id)).where(InterviewPrep.user_id == user_id)
    
    cvs = await db.scalar(cvs_query)
    jobs = await db.scalar(jobs_query)
    apps = await db.scalar(apps_query)
    preps = await db.scalar(preps_query)
    
    return {
        "cvs_count": cvs or 0,
        "jobs_count": jobs or 0,
        "apps_count": apps or 0,
        "preps_count": preps or 0
    }

async def get_execution_logs(db: AsyncSession, user_id: UUID, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieve LangGraph agent execution traces."""
    
    query = select(AgentExecution).where(
        AgentExecution.user_id == user_id
    ).order_by(desc(AgentExecution.created_at)).limit(limit)
    
    result = await db.execute(query)
    executions = result.scalars().all()
    
    return [
        {
            "id": str(ex.id),
            "agent_name": ex.agent_name,
            "status": ex.status,
            "error_message": ex.error_message,
            "result_data": ex.result_data,
            "created_at": ex.created_at.isoformat() if ex.created_at else None,
            "updated_at": ex.updated_at.isoformat() if ex.updated_at else None,
        }
        for ex in executions
    ]
