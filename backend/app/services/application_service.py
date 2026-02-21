"""Digital FTE - Application Service (business logic). Implemented in Phase 5."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.db.models import Application, HRContact, Job
from app.schemas.application import ApplicationCreate, ApplicationApproval

async def get_applications_by_user(db: AsyncSession, user_id: UUID) -> List[Application]:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.hr_contact), selectinload(Application.job))
        .where(Application.user_id == user_id)
        .order_by(Application.created_at.desc())
    )
    return list(result.scalars().all())

async def get_application(db: AsyncSession, application_id: UUID, user_id: UUID) -> Optional[Application]:
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.hr_contact), selectinload(Application.job))
        .where(Application.id == application_id, Application.user_id == user_id)
    )
    return result.scalars().first()

async def create_application(db: AsyncSession, user_id: UUID, app_in: ApplicationCreate) -> Application:
    app_data = app_in.model_dump(exclude_unset=True)
    app_data["user_id"] = user_id
    db_app = Application(**app_data)
    db.add(db_app)
    await db.commit()
    await db.refresh(db_app)
    
    # Eager load relationships for return
    result = await db.execute(
        select(Application)
        .options(selectinload(Application.hr_contact), selectinload(Application.job))
        .where(Application.id == db_app.id)
    )
    return result.scalars().first()

async def approve_application(db: AsyncSession, application_id: UUID, user_id: UUID, approval: ApplicationApproval) -> Optional[Application]:
    db_app = await get_application(db, application_id, user_id)
    if not db_app:
        return None
    
    if approval.approved:
        db_app.user_approved = True
        db_app.user_approved_at = datetime.now(timezone.utc)
        db_app.status = "approved"
        # We can also update email subject/body if they were edited
        if approval.edited_email_subject:
            db_app.email_subject = approval.edited_email_subject
        if approval.edited_email_body:
            db_app.email_body = approval.edited_email_body
    else:
        db_app.status = "rejected"
        db_app.user_approved = False
        
    await db.commit()
    await db.refresh(db_app)
    return db_app

async def update_application_status(db: AsyncSession, application_id: UUID, user_id: UUID, status: str) -> Optional[Application]:
    db_app = await get_application(db, application_id, user_id)
    if not db_app:
        return None
    db_app.status = status
    if status == "sent":
        db_app.email_sent_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_app)
    return db_app

# HR Contact functions
async def get_hr_contact_by_job(db: AsyncSession, job_id: UUID) -> Optional[HRContact]:
    result = await db.execute(select(HRContact).where(HRContact.job_id == job_id))
    return result.scalars().first()

async def create_hr_contact(db: AsyncSession, job_id: UUID, hr_data: dict) -> HRContact:
    hr_contact = HRContact(job_id=job_id, **hr_data)
    db.add(hr_contact)
    await db.commit()
    await db.refresh(hr_contact)
    return hr_contact
