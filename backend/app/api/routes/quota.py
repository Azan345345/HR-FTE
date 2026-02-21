"""Digital FTE - Quota Routes"""
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.quota_manager import quota_manager

router = APIRouter(prefix="/quota", tags=["quota"])

@router.get("/usage", response_model=Dict[str, Any])
async def get_quota_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve current API quota usage and limits for the authenticated user."""
    try:
        usage = await quota_manager.get_usage(current_user.id)
        return usage
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve quota: {str(e)}"
        )
