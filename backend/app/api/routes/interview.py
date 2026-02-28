"""Interview preparation routes."""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import User, InterviewPrep, Job, JobSearch
from app.api.deps import get_current_user
from app.schemas.schemas import InterviewPrepRequest, InterviewPrepResponse


class InterviewChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class CVRewriteRequest(BaseModel):
    section: str  # "summary" | "experience_bullet" | "skills" | "cover_letter"
    content: str
    instruction: str
    job_title: Optional[str] = ""
    job_company: Optional[str] = ""
    job_description: Optional[str] = ""


class EmailRewriteRequest(BaseModel):
    subject: str
    body: str
    instruction: str
    job_title: Optional[str] = ""
    job_company: Optional[str] = ""

router = APIRouter(prefix="/interview", tags=["Interview Prep"])


@router.post("/prepare", response_model=InterviewPrepResponse, status_code=201)
async def create_interview_prep(
    body: InterviewPrepRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate interview preparation materials for a specific job."""
    # Verify job belongs to user
    result = await db.execute(
        select(Job).join(JobSearch).where(Job.id == body.job_id, JobSearch.user_id == current_user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    prep = InterviewPrep(
        user_id=current_user.id,
        job_id=body.job_id,
        application_id=body.application_id,
        status="generating",
    )
    db.add(prep)
    await db.commit()
    await db.refresh(prep)

    # Background generation
    background_tasks.add_task(
        _generate_prep_background, prep.id, body.job_id, job.title, job.company,
        job.description, current_user.id,
    )

    return _to_response(prep)


async def _save_prep(prep_id: str, prep_data: dict, status: str = "completed"):
    """Write prep data to DB. Isolated so it can be called from multiple paths."""
    from app.db.database import AsyncSessionLocal
    from app.db.models import InterviewPrep
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
        prep = result.scalar_one_or_none()
        if prep:
            prep.company_research      = prep_data.get("company_research", {})
            prep.technical_questions   = prep_data.get("technical_questions", [])
            prep.behavioral_questions  = prep_data.get("behavioral_questions", [])
            prep.situational_questions = prep_data.get("situational_questions", [])
            prep.salary_research       = prep_data.get("salary_research", {})
            prep.tips                  = prep_data.get("tips", [])
            prep.questions_to_ask      = prep_data.get("questions_to_ask", [])
            prep.system_design_questions = prep_data.get("system_design_questions", [])
            prep.coding_challenges     = prep_data.get("coding_challenges", [])
            prep.cultural_questions    = prep_data.get("cultural_questions", [])
            prep.study_plan            = prep_data.get("study_plan", {})
            prep.status                = status
            await db.commit()


async def _generate_prep_background(
    prep_id: str, job_id: str, job_title: str, company: str, description: str, user_id: str
):
    """Background task: generate interview prep and persist to DB."""
    import asyncio
    from app.db.database import AsyncSessionLocal
    from app.agents.interview_prep import generate_interview_prep
    from app.core.event_bus import event_bus
    from app.db.models import TailoredCV, InterviewPrep
    from sqlalchemy import select, desc

    async def _mark_failed():
        try:
            from app.db.database import AsyncSessionLocal as _ASL
            from app.db.models import InterviewPrep as _IP
            from sqlalchemy import select as _sel
            async with _ASL() as db:
                result = await db.execute(_sel(_IP).where(_IP.id == prep_id))
                prep = result.scalar_one_or_none()
                if prep and prep.status == "generating":
                    prep.status = "failed"
                    await db.commit()
        except Exception:
            pass

    try:
        # Non-blocking event (swallow errors so it never blocks the task)
        try:
            await event_bus.emit_agent_started(
                user_id, "interview_prep", f"Preparing for {job_title} at {company}"
            )
        except Exception:
            pass

        # Fetch tailored CV context (optional, don't crash if DB slow)
        tailored_cv_data = None
        try:
            async with AsyncSessionLocal() as db:
                tcv_result = await db.execute(
                    select(TailoredCV)
                    .where(TailoredCV.job_id == job_id, TailoredCV.user_id == user_id)
                    .order_by(desc(TailoredCV.created_at))
                    .limit(1)
                )
                tcv = tcv_result.scalar_one_or_none()
                if tcv:
                    tailored_cv_data = tcv.tailored_data
        except Exception:
            pass

        # Generate — each internal LLM call has its own 90s asyncio timeout.
        # Wrap the whole generation in a 4-minute safety net.
        prep_data = await asyncio.wait_for(
            generate_interview_prep(job_title, company, description, tailored_cv_data),
            timeout=240.0,
        )

        await _save_prep(prep_id, prep_data, "completed")

        try:
            await event_bus.emit_agent_completed(user_id, "interview_prep", "Interview prep ready")
        except Exception:
            pass

    except asyncio.TimeoutError:
        # Generation blew the 4-minute safety cap — save whatever partial data exists
        # then mark failed so frontend stops polling immediately.
        await _mark_failed()
        try:
            await event_bus.emit_agent_error(user_id, "interview_prep", "Generation timed out")
        except Exception:
            pass

    except Exception as e:
        await _mark_failed()
        try:
            await event_bus.emit_agent_error(user_id, "interview_prep", str(e))
        except Exception:
            pass


@router.get("/list")
async def list_preps(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all interview preps."""
    result = await db.execute(
        select(InterviewPrep)
        .where(InterviewPrep.user_id == current_user.id)
        .order_by(InterviewPrep.created_at.desc())
    )
    preps = result.scalars().all()
    return {"preps": [_to_response(p) for p in preps], "total": len(preps)}


@router.get("/{prep_id}", response_model=InterviewPrepResponse)
async def get_prep(
    prep_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific interview prep."""
    result = await db.execute(
        select(InterviewPrep).where(InterviewPrep.id == prep_id, InterviewPrep.user_id == current_user.id)
    )
    prep = result.scalar_one_or_none()
    if not prep:
        raise HTTPException(status_code=404, detail="Interview prep not found")
    return _to_response(prep)


@router.post("/{prep_id}/chat")
async def chat_with_prep_coach(
    prep_id: str,
    body: InterviewChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Chat with AI interview coach about a specific prep."""
    from app.agents.interview_prep import chat_with_coach

    result = await db.execute(
        select(InterviewPrep).where(InterviewPrep.id == prep_id, InterviewPrep.user_id == current_user.id)
    )
    prep = result.scalar_one_or_none()
    if not prep:
        raise HTTPException(status_code=404, detail="Interview prep not found")

    # Get job context
    job_result = await db.execute(select(Job).where(Job.id == prep.job_id))
    job = job_result.scalar_one_or_none()
    job_title = job.title if job else "the role"
    company = job.company if job else "the company"

    prep_data = {
        "company_research": prep.company_research or {},
        "technical_questions": prep.technical_questions or [],
        "behavioral_questions": prep.behavioral_questions or [],
    }

    response_text = await chat_with_coach(
        prep_data=prep_data,
        job_title=job_title,
        company=company,
        message=body.message,
        history=body.history,
    )
    return {"response": response_text}


@router.post("/ai-rewrite-cv")
async def ai_rewrite_cv_section(
    body: CVRewriteRequest,
    current_user: User = Depends(get_current_user),
):
    """AI-powered rewrite of a CV section based on instruction."""
    from app.agents.interview_prep import ai_rewrite_cv_section

    result = await ai_rewrite_cv_section(
        section=body.section,
        content=body.content,
        instruction=body.instruction,
        job_context={
            "title": body.job_title,
            "company": body.job_company,
            "description": body.job_description,
        },
    )
    return {"content": result}


@router.post("/ai-rewrite-email")
async def ai_rewrite_email(
    body: EmailRewriteRequest,
    current_user: User = Depends(get_current_user),
):
    """AI-powered rewrite of application email based on instruction."""
    from app.agents.interview_prep import ai_rewrite_email

    result = await ai_rewrite_email(
        email_subject=body.subject,
        email_body=body.body,
        instruction=body.instruction,
        job_context={
            "title": body.job_title,
            "company": body.job_company,
        },
    )
    return result


def _safe_list(val) -> list:
    """Parse a DB value that may be a JSON string or a list into a list."""
    import json as _json
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            parsed = _json.loads(val)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return []


def _safe_dict(val) -> dict:
    """Parse a DB value that may be a JSON string or a dict into a dict."""
    import json as _json
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            parsed = _json.loads(val)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _to_response(prep: InterviewPrep) -> InterviewPrepResponse:
    return InterviewPrepResponse(
        id=prep.id,
        job_id=prep.job_id,
        company_research=_safe_dict(prep.company_research),
        technical_questions=_safe_list(prep.technical_questions),
        behavioral_questions=_safe_list(prep.behavioral_questions),
        situational_questions=_safe_list(prep.situational_questions),
        salary_research=_safe_dict(prep.salary_research),
        tips=_safe_list(prep.tips),
        questions_to_ask=_safe_list(getattr(prep, "questions_to_ask", None)),
        system_design_questions=_safe_list(getattr(prep, "system_design_questions", None)),
        coding_challenges=_safe_list(getattr(prep, "coding_challenges", None)),
        cultural_questions=_safe_list(getattr(prep, "cultural_questions", None)),
        study_plan=_safe_dict(getattr(prep, "study_plan", None)),
        study_material_path=prep.study_material_path,
        prep_score=prep.prep_score,
        status=prep.status,
        created_at=str(prep.created_at) if prep.created_at else None,
    )
