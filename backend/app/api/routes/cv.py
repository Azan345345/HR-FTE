"""
Digital FTE - CV Routes
Full CRUD + AI parsing endpoints for CV management.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.services.cv_service import (
    upload_cv, parse_cv, get_cv, list_user_cvs, delete_cv, set_primary_cv,
)
from app.schemas.cv import CVUploadResponse, CVRead, CVListItem, CVAnalysis

router = APIRouter(prefix="/cv", tags=["cv"])


@router.post("/upload", response_model=CVUploadResponse, status_code=201)
async def upload_cv_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a CV file (PDF or DOCX). Auto-extracts text."""
    cv = await upload_cv(user.id, file, db)
    return CVUploadResponse(
        id=cv.id,
        file_name=cv.file_name,
        file_type=cv.file_type,
        is_primary=cv.is_primary,
        parsed_data=cv.parsed_data,
        created_at=cv.created_at,
    )


@router.post("/{cv_id}/parse", response_model=CVAnalysis)
async def parse_cv_endpoint(
    cv_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Parse a CV using AI to extract structured data and generate embeddings."""
    analysis = await parse_cv(cv_id, user.id, db)
    return analysis


@router.get("/", response_model=List[CVListItem])
async def list_cvs_endpoint(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all CVs for the authenticated user."""
    cvs = await list_user_cvs(user.id, db)
    return [
        CVListItem(
            id=cv.id,
            file_name=cv.file_name,
            file_type=cv.file_type,
            is_primary=cv.is_primary,
            has_parsed_data=bool(cv.parsed_data and cv.parsed_data != {}),
            created_at=cv.created_at,
        )
        for cv in cvs
    ]


@router.get("/{cv_id}", response_model=CVRead)
async def get_cv_endpoint(
    cv_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full CV details including parsed data."""
    cv = await get_cv(cv_id, user.id, db)
    return CVRead(
        id=cv.id,
        file_name=cv.file_name,
        file_type=cv.file_type,
        parsed_data=cv.parsed_data,
        raw_text=cv.raw_text,
        is_primary=cv.is_primary,
        created_at=cv.created_at,
        updated_at=cv.updated_at,
    )


@router.delete("/{cv_id}", status_code=204)
async def delete_cv_endpoint(
    cv_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a CV and its associated file."""
    await delete_cv(cv_id, user.id, db)


@router.put("/{cv_id}/primary", response_model=CVRead)
async def set_primary_cv_endpoint(
    cv_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Set a CV as the primary CV for the user."""
    cv = await set_primary_cv(cv_id, user.id, db)
    return CVRead(
        id=cv.id,
        file_name=cv.file_name,
        file_type=cv.file_type,
        parsed_data=cv.parsed_data,
        raw_text=cv.raw_text,
        is_primary=cv.is_primary,
        created_at=cv.created_at,
        updated_at=cv.updated_at,
    )


# ── Tailoring Extensions ─────────────────────────────

from pydantic import BaseModel
from fastapi import Response
from app.services.cv_tailor_service import tailor_cv, generate_tailored_pdf_bytes

class TailorRequest(BaseModel):
    job_id: UUID

@router.post("/{cv_id}/tailor", status_code=201)
async def tailor_cv_endpoint(
    cv_id: UUID,
    request: TailorRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Trigger AI to rewrite the CV for a specific job.
    Returns the tailored data and ID.
    """
    result = await tailor_cv(user.id, cv_id, request.job_id, db)
    return result


@router.get("/tailored/{tailored_id}/pdf")
async def get_tailored_pdf_endpoint(
    tailored_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Generate and download the PDF for a tailored CV.
    """
    pdf_bytes = await generate_tailored_pdf_bytes(tailored_id, user.id, db)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=tailored_cv.pdf"},
    )
