"""
Digital FTE - CV Service
Business logic for CV upload, parsing, listing, and management.
"""

import structlog
from typing import List, Optional
from uuid import UUID

from fastapi import UploadFile, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserCV
from app.schemas.cv import ParsedCVData, CVRead, CVListItem, CVAnalysis
from app.utils.file_handler import save_upload, extract_text, delete_file
from app.utils.text_processor import clean_text, extract_sections, estimate_years_experience
from app.agents.tools.cv_tools import store_cv_embeddings
from app.core.llm_router import llm_router
from app.agents.prompts.cv_parser import CV_PARSER_SYSTEM_PROMPT, CV_PARSER_USER_PROMPT

logger = structlog.get_logger()


async def upload_cv(
    user_id: UUID, file: UploadFile, db: AsyncSession
) -> UserCV:
    """
    Save uploaded file, extract text, create DB record.
    Returns the created UserCV model.
    """
    # Save file to disk
    file_path, file_type = await save_upload(file, str(user_id))
    logger.info("cv_file_saved", user_id=str(user_id), path=file_path)

    # Extract raw text
    raw_text = extract_text(file_path, file_type)
    cleaned_text = clean_text(raw_text)

    # Check if user has any CVs; first one is primary
    result = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id)
    )
    existing_cvs = result.scalars().all()
    is_primary = len(existing_cvs) == 0

    # Create DB record
    cv = UserCV(
        user_id=user_id,
        file_name=file.filename,
        file_path=file_path,
        file_type=file_type,
        raw_text=cleaned_text,
        parsed_data={},  # Will be populated after parsing
        is_primary=is_primary,
    )
    db.add(cv)
    await db.commit()
    await db.refresh(cv)

    logger.info("cv_record_created", cv_id=str(cv.id))
    return cv


async def parse_cv(cv_id: UUID, user_id: UUID, db: AsyncSession) -> CVAnalysis:
    """
    Parse a CV using the LLM and store the structured data.
    Also generates and stores embeddings in ChromaDB.
    """
    import json
    from langchain_core.messages import SystemMessage, HumanMessage

    # Fetch CV record
    result = await db.execute(
        select(UserCV).where(UserCV.id == cv_id, UserCV.user_id == user_id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")

    if not cv.raw_text:
        raise HTTPException(status_code=422, detail="CV has no extracted text")

    # Call LLM to parse
    messages = [
        SystemMessage(content=CV_PARSER_SYSTEM_PROMPT),
        HumanMessage(content=CV_PARSER_USER_PROMPT.format(cv_text=cv.raw_text[:8000])),
    ]

    response = await llm_router.invoke_with_fallback(messages)

    # Parse JSON from response
    content = response.content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines)

    try:
        parsed_json = json.loads(content)
    except json.JSONDecodeError as e:
        logger.error("cv_parse_json_error", error=str(e), content=content[:200])
        raise HTTPException(status_code=500, detail=f"LLM returned invalid JSON: {str(e)}")

    # Validate with schema
    parsed_data = ParsedCVData(**parsed_json)

    # Update DB record
    cv.parsed_data = parsed_data.model_dump()
    await db.commit()
    await db.refresh(cv)

    logger.info("cv_parsed", cv_id=str(cv_id))

    # Generate embeddings
    embedding_stored = False
    try:
        store_cv_embeddings(str(cv_id), str(user_id), cv.raw_text)
        cv.embedding_id = str(cv_id)
        await db.commit()
        embedding_stored = True
    except Exception as e:
        logger.warning("embedding_storage_failed", error=str(e))

    # Section analysis
    sections = extract_sections(cv.raw_text)
    years = estimate_years_experience(cv.raw_text)

    return CVAnalysis(
        cv_id=cv.id,
        parsed_data=parsed_data,
        estimated_years=years,
        sections_found=list(sections.keys()),
        embedding_stored=embedding_stored,
    )


async def get_cv(cv_id: UUID, user_id: UUID, db: AsyncSession) -> UserCV:
    """Fetch a single CV by ID, ensuring it belongs to the user."""
    result = await db.execute(
        select(UserCV).where(UserCV.id == cv_id, UserCV.user_id == user_id)
    )
    cv = result.scalar_one_or_none()
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    return cv


async def list_user_cvs(user_id: UUID, db: AsyncSession) -> List[UserCV]:
    """List all CVs for a user, ordered by creation date."""
    result = await db.execute(
        select(UserCV)
        .where(UserCV.user_id == user_id)
        .order_by(UserCV.created_at.desc())
    )
    return result.scalars().all()


async def delete_cv(cv_id: UUID, user_id: UUID, db: AsyncSession) -> bool:
    """Delete a CV and its file from disk."""
    cv = await get_cv(cv_id, user_id, db)

    # Delete file
    delete_file(cv.file_path)

    # Delete DB record
    await db.delete(cv)
    await db.commit()

    logger.info("cv_deleted", cv_id=str(cv_id))
    return True


async def set_primary_cv(cv_id: UUID, user_id: UUID, db: AsyncSession) -> UserCV:
    """Set a CV as the primary for the user."""
    # Unset all existing primary
    await db.execute(
        update(UserCV)
        .where(UserCV.user_id == user_id)
        .values(is_primary=False)
    )

    # Set new primary
    cv = await get_cv(cv_id, user_id, db)
    cv.is_primary = True
    await db.commit()
    await db.refresh(cv)

    logger.info("cv_set_primary", cv_id=str(cv_id))
    return cv
