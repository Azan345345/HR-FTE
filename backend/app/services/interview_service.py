"""Digital FTE - Interview Service"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import InterviewPrep
from app.schemas.interview import InterviewPrepCreate

async def get_preps_by_user(db: AsyncSession, user_id: UUID) -> List[InterviewPrep]:
    result = await db.execute(
        select(InterviewPrep)
        .options(selectinload(InterviewPrep.job))
        .where(InterviewPrep.user_id == user_id)
        .order_by(InterviewPrep.created_at.desc())
    )
    return list(result.scalars().all())

async def get_prep(db: AsyncSession, prep_id: UUID, user_id: UUID) -> Optional[InterviewPrep]:
    result = await db.execute(
        select(InterviewPrep)
        .options(selectinload(InterviewPrep.job))
        .where(InterviewPrep.id == prep_id, InterviewPrep.user_id == user_id)
    )
    return result.scalars().first()

async def create_prep(db: AsyncSession, user_id: UUID, prep_in: InterviewPrepCreate) -> InterviewPrep:
    prep_data = prep_in.model_dump(exclude_unset=True)
    prep_data["user_id"] = user_id
    db_prep = InterviewPrep(**prep_data)
    db.add(db_prep)
    await db.commit()
    await db.refresh(db_prep)
    
    result = await db.execute(
        select(InterviewPrep)
        .options(selectinload(InterviewPrep.job))
        .where(InterviewPrep.id == db_prep.id)
    )
    return result.scalars().first()
