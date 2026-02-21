"""Digital FTE - Interview Prep Routes"""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.auth import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.schemas.interview import InterviewPrepRead, InterviewPrepCreate
from app.services import interview_service

router = APIRouter(prefix="/interview", tags=["interview"])

@router.get("/", response_model=List[InterviewPrepRead])
async def list_preps(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List interview preparations."""
    return await interview_service.get_preps_by_user(db, current_user.id)

@router.post("/{job_id}/prepare", response_model=InterviewPrepRead)
async def prepare_interview(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start interview prep for a job."""
    # Logic to trigger interview_prep agent would go here (or via Celery)
    
    # Returning a mock created struct for immediate validation purpose
    return await interview_service.create_prep(
        db, current_user.id, InterviewPrepCreate(job_id=job_id)
    )

@router.get("/{prep_id}", response_model=InterviewPrepRead)
async def get_prep(
    prep_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get prep details."""
    prep = await interview_service.get_prep(db, prep_id, current_user.id)
    if not prep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview Prep not found")
    return prep
