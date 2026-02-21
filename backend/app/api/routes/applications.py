"""Digital FTE - Applications Routes"""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.application import ApplicationRead, ApplicationApproval, ApplicationCreate
from app.services import application_service

router = APIRouter(prefix="/applications", tags=["applications"])

@router.get("/", response_model=List[ApplicationRead])
async def list_applications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List applications."""
    return await application_service.get_applications_by_user(db, current_user.id)

@router.post("/{application_id}/approve", response_model=ApplicationRead)
async def approve_application(
    application_id: UUID,
    approval: ApplicationApproval,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve an application for sending."""
    app_db = await application_service.approve_application(db, application_id, current_user.id, approval)
    if not app_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    
    # Logic to trigger email_sender agent would go here (or via Celery)
    
    return app_db

@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application(
    application_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get application details."""
    app_db = await application_service.get_application(db, application_id, current_user.id)
    if not app_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app_db

@router.post("/", response_model=ApplicationRead)
async def create_application(
    app_in: ApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new application record."""
    return await application_service.create_application(db, current_user.id, app_in)
