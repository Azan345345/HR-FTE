"""
Digital FTE - CV Service (Tailoring Implementation)
Contains business logic for CV tailoring and PDF generation.
"""

from typing import Dict, Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserCV, Job, TailoredCV
from app.agents.cv_tailor import cv_tailor_node
from app.agents.state import DigitalFTEState
from app.utils.pdf_generator import generate_cv_pdf
from app.services.cv_service import get_cv
from app.services.job_service import get_job

import structlog

logger = structlog.get_logger()

async def tailor_cv(
    user_id: UUID,
    cv_id: UUID,
    job_id: UUID,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Orchestrate the tailoring process:
    1. Fetch CV and Job.
    2. Invoke CV Tailor Agent (LLM).
    3. Store result in TailoredCV table.
    4. Return tailored data for frontend preview.
    """
    # 1. Fetch & Validate
    logger.info("tailoring_start", user_id=str(user_id), cv_id=str(cv_id), job_id=str(job_id))
    
    cv = await get_cv(cv_id, user_id, db)
    job = await get_job(job_id, user_id, db)
    
    if not cv.parsed_data:
        raise HTTPException(status_code=400, detail="Original CV must be parsed before tailoring")

    # 2. Run Agent
    # Construct state object mimicking LangGraph state
    state = {
        "user_id": str(user_id),
        "parsed_cv": cv.parsed_data,
        "job_description": {
            "title": job.title,
            "company": job.company,
            "description": job.description,
            "requirements": job.requirements
        },
        "errors": []
    }
    
    logger.info("invoking_agent", agent="cv_tailor")
    result = await cv_tailor_node(state)
    
    if result.get("agent_status") == "error":
        error_msg = result.get("errors", ["Unknown error"])[0]
        logger.error("tailoring_failed", error=error_msg)
        raise HTTPException(status_code=500, detail=f"Tailoring failed: {error_msg}")

    tailored_data = result.get("tailored_cv")

    # 3. Store Result
    new_record = TailoredCV(
        user_id=user_id,
        original_cv_id=cv_id,
        job_id=job_id,
        tailored_data=tailored_data,
        match_score=0.0 # Placeholder
    )
    db.add(new_record)
    await db.commit()
    await db.refresh(new_record)

    logger.info("tailoring_complete", tailored_cv_id=str(new_record.id))

    return {
        "id": new_record.id,
        "tailored_data": tailored_data,
        "job_title": job.title,
        "company": job.company
    }


async def get_tailored_cv_record(
    tailored_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> TailoredCV:
    """Fetch a TailoredCV record by ID."""
    result = await db.execute(
        select(TailoredCV)
        .where(TailoredCV.id == tailored_id, TailoredCV.user_id == user_id)
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Tailored CV not found")
    return record


async def generate_tailored_pdf_bytes(
    tailored_id: UUID,
    user_id: UUID,
    db: AsyncSession
) -> bytes:
    """Generate PDF binary content for a tailored CV."""
    record = await get_tailored_cv_record(tailored_id, user_id, db)
    
    if not record.tailored_data:
        raise HTTPException(status_code=400, detail="Tailored data is empty")

    # Generate PDF using utility
    pdf_content = generate_cv_pdf(record.tailored_data)
    return pdf_content
