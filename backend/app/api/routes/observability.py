"""Digital FTE - Observability/Analytics Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from app.db.database import get_db
from app.api.routes.auth import get_current_user
from app.db.models import User
from app.services import observability_service

router = APIRouter(prefix="/observability", tags=["observability"])

@router.get("/stats", response_model=Dict[str, int])
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated top-level counts for the dashboard cards."""
    return await observability_service.get_dashboard_stats(db, current_user.id)

@router.get("/logs", response_model=List[Dict[str, Any]])
async def get_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve system execution logs for the user."""
    return await observability_service.get_execution_logs(db, current_user.id, limit)
