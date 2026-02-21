"""Digital FTE - Dashboard Routes"""
from fastapi import APIRouter
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_stats():
    """Get dashboard statistics. Implemented in Phase 8."""
    return {
        "cvs_uploaded": 0,
        "jobs_found": 0,
        "applications_sent": 0,
        "interviews_prepped": 0,
    }


@router.get("/activity")
async def get_recent_activity():
    """Get recent activity feed. Implemented in Phase 8."""
    return {"activities": []}
