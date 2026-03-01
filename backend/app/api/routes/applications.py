"""Application management routes: create, approve, track, list."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.db.database import get_db
from app.db.models import User, Application, Job, JobSearch
from app.api.deps import get_current_user
from app.schemas.schemas import (
    ApplicationCreateRequest, ApplicationApproveRequest,
    ApplicationResponse, ApplicationListResponse,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/", response_model=ApplicationResponse, status_code=201)
async def create_application(
    body: ApplicationCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new job application (pending approval)."""
    # Verify job belongs to user
    result = await db.execute(
        select(Job).join(JobSearch).where(Job.id == body.job_id, JobSearch.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    app = Application(
        user_id=current_user.id,
        job_id=body.job_id,
        tailored_cv_id=body.tailored_cv_id,
        status="pending_approval",
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)

    return _to_response(app)


@router.post("/{app_id}/approve", response_model=ApplicationResponse)
async def approve_application(
    app_id: str,
    body: ApplicationApproveRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve an application — attempt Gmail send if integration is connected."""
    from app.db.models import UserIntegration, TailoredCV

    app = await _get_user_app(app_id, current_user.id, db)

    app.user_approved = True
    app.user_approved_at = datetime.utcnow()
    if body:
        if body.email_subject:
            app.email_subject = body.email_subject
        if body.email_body:
            app.email_body = body.email_body

    # Try to send via Gmail if the user has a connected integration
    int_result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == current_user.id,
            UserIntegration.service_name == "gmail",
            UserIntegration.is_active == True,
        )
    )
    integration = int_result.scalar_one_or_none()

    if integration and integration.access_token and app.email_subject and app.email_body:
        # Load HR contact email
        hr_email = None
        if app.hr_contact_id:
            from app.db.models import HRContact
            hr_result = await db.execute(
                select(HRContact).where(HRContact.id == app.hr_contact_id)
            )
            hr = hr_result.scalar_one_or_none()
            if hr:
                hr_email = hr.hr_email

        if hr_email:
            # Load PDF path
            pdf_path = None
            if app.tailored_cv_id:
                tc_result = await db.execute(
                    select(TailoredCV).where(TailoredCV.id == app.tailored_cv_id)
                )
                tc = tc_result.scalar_one_or_none()
                if tc:
                    pdf_path = tc.pdf_path

            from app.agents.email_sender import send_via_gmail
            send_result = await send_via_gmail(
                user_tokens={
                    "access_token": integration.access_token,
                    "refresh_token": integration.refresh_token,
                },
                to_email=hr_email,
                subject=app.email_subject,
                body=app.email_body,
                attachment_path=pdf_path,
            )
            if send_result.get("status") == "sent":
                app.status = "sent"
                app.email_sent_at = datetime.utcnow()
                app.gmail_message_id = send_result.get("message_id")
            else:
                app.status = "approved"
        else:
            app.status = "approved"
    else:
        app.status = "approved"

    await db.commit()
    await db.refresh(app)
    return _to_response(app)


@router.post("/{app_id}/reject", response_model=ApplicationResponse)
async def reject_application(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject / skip an application."""
    app = await _get_user_app(app_id, current_user.id, db)
    app.status = "rejected"
    await db.commit()
    await db.refresh(app)
    return _to_response(app)


@router.get("/list", response_model=ApplicationListResponse)
async def list_applications(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all applications for the current user."""
    query = (
        select(Application)
        .where(Application.user_id == current_user.id)
        .order_by(Application.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if status:
        query = query.where(Application.status == status)

    result = await db.execute(query)
    apps = result.scalars().all()

    count_q = select(func.count(Application.id)).where(Application.user_id == current_user.id)
    if status:
        count_q = count_q.where(Application.status == status)
    total = (await db.execute(count_q)).scalar() or 0

    return ApplicationListResponse(
        applications=[_to_response(a) for a in apps],
        total=total,
    )


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(
    app_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific application."""
    app = await _get_user_app(app_id, current_user.id, db)
    return _to_response(app)


# ── Helpers ───────────────────────────────────
async def _get_user_app(app_id: str, user_id: str, db: AsyncSession) -> Application:
    result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user_id)
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


def _to_response(app: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=app.id,
        job_id=app.job_id,
        tailored_cv_id=app.tailored_cv_id,
        status=app.status,
        email_subject=app.email_subject,
        email_body=app.email_body,
        email_sent_at=str(app.email_sent_at) if app.email_sent_at else None,
        user_approved=app.user_approved,
        created_at=str(app.created_at) if app.created_at else None,
    )
