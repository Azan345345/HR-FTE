"""Digital FTE - Integrations Routes (Google OAuth)"""
from fastapi import APIRouter
router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/google/connect")
async def connect_google():
    """Start Google OAuth flow. Implemented in Phase 5."""
    return {"message": "Not implemented yet"}


@router.get("/status")
async def integration_status():
    """Get connected integrations. Implemented in Phase 5."""
    return {"integrations": []}
