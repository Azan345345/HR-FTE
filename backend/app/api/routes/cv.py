"""CV upload, parse, and management routes."""

import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.db.models import User, UserCV, TailoredCV, Job, JobSearch
from app.api.deps import get_current_user
from app.schemas.schemas import CVResponse, CVListResponse, TailoredCVResponse, TailorCVRequest
from app.config import settings

router = APIRouter(prefix="/cv", tags=["CV Management"])


@router.post("/upload", response_model=CVResponse, status_code=201)
async def upload_cv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a CV file (PDF or DOCX) for parsing."""
    # Validate file type
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else ""
    if ext not in ("pdf", "docx"):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported")

    # Save file locally
    upload_dir = os.path.join(settings.UPLOAD_DIR, current_user.id)
    os.makedirs(upload_dir, exist_ok=True)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(upload_dir, f"{file_id}.{ext}")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Check if first CV → make primary
    result = await db.execute(
        select(UserCV).where(UserCV.user_id == current_user.id)
    )
    is_first = result.first() is None

    # Create DB record
    cv = UserCV(
        id=file_id,
        user_id=current_user.id,
        file_name=file.filename or f"cv.{ext}",
        file_path=file_path,
        file_type=ext,
        is_primary=is_first,
    )
    db.add(cv)
    await db.commit()
    await db.refresh(cv)

    # Trigger background parsing
    background_tasks.add_task(_parse_cv_background, cv.id, file_path, ext, current_user.id)

    return CVResponse(
        id=cv.id,
        file_name=cv.file_name,
        file_type=cv.file_type,
        parsed_data=cv.parsed_data,
        is_primary=cv.is_primary,
        created_at=str(cv.created_at) if cv.created_at else None,
    )


async def _parse_cv_background(cv_id: str, file_path: str, file_type: str, user_id: str):
    """Background task to parse CV using the CV parser agent."""
    from app.db.database import AsyncSessionLocal
    from app.agents.cv_parser import parse_cv_file

    try:
        parsed_data = await parse_cv_file(file_path, file_type, user_id=user_id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(UserCV).where(UserCV.id == cv_id))
            cv = result.scalar_one_or_none()
            if cv:
                cv.parsed_data = parsed_data
                await db.commit()

    except Exception as e:
        from app.core.event_bus import event_bus
        await event_bus.emit_agent_error(user_id, "cv_parser", str(e))


@router.get("/list", response_model=CVListResponse)
async def list_cvs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all CVs for the current user."""
    result = await db.execute(
        select(UserCV).where(UserCV.user_id == current_user.id).order_by(UserCV.created_at.desc())
    )
    cvs = result.scalars().all()
    return CVListResponse(
        cvs=[
            CVResponse(
                id=cv.id,
                file_name=cv.file_name,
                file_type=cv.file_type,
                parsed_data=cv.parsed_data,
                is_primary=cv.is_primary,
                created_at=str(cv.created_at) if cv.created_at else None,
            )
            for cv in cvs
        ],
        total=len(cvs),
    )


@router.get("/{cv_id}", response_model=CVResponse)
async def get_cv(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific CV by ID."""
    result = await db.execute(
        select(UserCV).where(UserCV.id == cv_id, UserCV.user_id == current_user.id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    return CVResponse(
        id=cv.id,
        file_name=cv.file_name,
        file_type=cv.file_type,
        parsed_data=cv.parsed_data,
        is_primary=cv.is_primary,
        created_at=str(cv.created_at) if cv.created_at else None,
    )


@router.delete("/{cv_id}", status_code=204)
async def delete_cv(
    cv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a CV."""
    result = await db.execute(
        select(UserCV).where(UserCV.id == cv_id, UserCV.user_id == current_user.id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    # Delete associated tailored CVs and their files
    tailored_result = await db.execute(
        select(TailoredCV).where(TailoredCV.original_cv_id == cv.id)
    )
    tailored_cvs = tailored_result.scalars().all()
    for tcv in tailored_cvs:
        if tcv.pdf_path and os.path.exists(tcv.pdf_path):
            os.remove(tcv.pdf_path)
        await db.delete(tcv)

    # Delete main CV file
    if os.path.exists(cv.file_path):
        os.remove(cv.file_path)

    await db.delete(cv)
    await db.commit()
@router.patch("/tailored/{tailored_cv_id}")
async def update_tailored_cv(
    tailored_cv_id: str,
    edits: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persist user-edited sections into a TailoredCV record.

    Accepts a dict of {section: value} pairs — only provided keys are updated.
    Allowed sections: summary, skills, experience, cover_letter.
    """
    result = await db.execute(
        select(TailoredCV).where(
            TailoredCV.id == tailored_cv_id,
            TailoredCV.user_id == current_user.id,
        )
    )
    tcv = result.scalar_one_or_none()
    if not tcv:
        raise HTTPException(status_code=404, detail="Tailored CV not found")

    current = dict(tcv.tailored_data or {})
    allowed = {"summary", "skills", "experience", "cover_letter", "projects", "certifications"}
    for key, value in edits.items():
        if key in allowed and value is not None:
            current[key] = value

    tcv.tailored_data = current
    await db.commit()
    return {"status": "updated", "tailored_cv_id": tailored_cv_id}


@router.get("/tailored/{tailored_cv_id}/download")
async def download_tailored_cv(
    tailored_cv_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download a tailored CV PDF."""
    result = await db.execute(
        select(TailoredCV).where(TailoredCV.id == tailored_cv_id, TailoredCV.user_id == current_user.id)
    )
    tcv = result.scalar_one_or_none()
    if not tcv or not tcv.pdf_path:
        raise HTTPException(status_code=404, detail="Tailored CV or PDF not found")

    if not os.path.exists(tcv.pdf_path):
        raise HTTPException(status_code=404, detail="CV file missing on server")

    return FileResponse(
        tcv.pdf_path,
        media_type="application/pdf",
        filename=f"Tailored_CV_{tcv.id[:8]}.pdf"
    )

@router.post("/tailor", response_model=TailoredCVResponse)
async def tailor_cv(
    body: TailorCVRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tailor a CV for a specific job and save the result."""
    from app.agents.cv_tailor import tailor_cv_for_job
    from app.agents.doc_generator import generate_cv_pdf
    
    # 1. Verify job and CV ownership
    job_result = await db.execute(
        select(Job).join(JobSearch).where(Job.id == body.job_id, JobSearch.user_id == current_user.id)
    )
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    cv_id = body.cv_id
    if not cv_id:
        # Fallback to primary
        cv_result = await db.execute(
            select(UserCV).where(UserCV.user_id == current_user.id, UserCV.is_primary == True)
        )
        cv = cv_result.scalar_one_or_none()
    else:
        cv_result = await db.execute(
            select(UserCV).where(UserCV.id == cv_id, UserCV.user_id == current_user.id)
        )
        cv = cv_result.scalar_one_or_none()
        
    if not cv or not cv.parsed_data:
        raise HTTPException(status_code=400, detail="Primary CV not found or not parsed")

    # 2. Run agent
    job_data = {
        "title": job.title,
        "company": job.company,
        "description": job.description,
        "requirements": job.requirements,
    }
    
    tailoring_result = await tailor_cv_for_job(cv.parsed_data, job_data)
    
    # 3. Generate PDF
    pdf_path = await generate_cv_pdf(tailoring_result)
    
    # 4. Save to DB
    tcv = TailoredCV(
        user_id=current_user.id,
        original_cv_id=cv.id,
        job_id=job.id,
        tailored_data=tailoring_result.get("tailored_cv", {}),
        cover_letter=tailoring_result.get("cover_letter"),
        ats_score=tailoring_result.get("ats_score"),
        match_score=tailoring_result.get("match_score"),
        changes_made=tailoring_result.get("changes_made", []),
        pdf_path=pdf_path,
        status="completed"
    )
    db.add(tcv)
    await db.commit()
    await db.refresh(tcv)

    return TailoredCVResponse(
        id=tcv.id,
        job_id=tcv.job_id,
        match_score=tcv.match_score,
        ats_score=tcv.ats_score,
        cover_letter=tcv.cover_letter,
        pdf_path=tcv.pdf_path,
        changes_made=tcv.changes_made,
        status=tcv.status,
        created_at=str(tcv.created_at) if tcv.created_at else None
    )
