"""Supervisor Agent — routes user requests to specialized agents.

Returns (response_text, metadata_or_None) tuples to enable rich UI cards.
Action prefixes (__TAILOR_APPLY__:, etc.) are programmatic button-click handlers.
"""

import os
import re
import asyncio
import structlog
import json
import time
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.llm_router import get_llm
from app.core.event_bus import event_bus

logger = structlog.get_logger()

# Strong references to background tasks — prevents Python GC from collecting
# asyncio.create_task() results before they complete (Python 3.10+ documented issue).
_background_tasks: set = set()

# Track background tasks per user so they can be cancelled on conversation stop.
_user_bg_tasks: dict[str, list] = {}


def cancel_user_tasks(user_id: str) -> int:
    """Cancel all background tasks for a user. Returns number cancelled."""
    tasks = _user_bg_tasks.pop(user_id, [])
    cancelled = 0
    for t in tasks:
        if not t.done():
            t.cancel()
            cancelled += 1
    return cancelled


def _ensure_str(value) -> str:
    """Coerce a value to a string. Handles lists like ['Full-time'] → 'Full-time'."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else ""
    return str(value)


async def _log_execution(
    db: AsyncSession,  # kept for signature compat; not used — always uses fresh session
    user_id: str,
    session_id: str,
    agent_name: str,
    action: str,
    status: str,
    execution_time_ms: int,
    error_message: str = None,
):
    """Write an AgentExecution record so the Observability tab shows real logs.

    Always opens its own DB session so a stale/dead connection on the request
    session never corrupts this write or the caller's session state.
    """
    try:
        from app.db.database import AsyncSessionLocal
        from app.db.models import AgentExecution
        async with AsyncSessionLocal() as fresh_db:
            record = AgentExecution(
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                action=action,
                status=status,
                execution_time_ms=execution_time_ms,
                error_message=error_message,
            )
            fresh_db.add(record)
            await fresh_db.commit()
    except Exception as e:
        logger.warning("log_execution_failed", error=str(e))


async def process_chat_message(
    user_id: str,
    session_id: str,
    message: str,
    db: AsyncSession,
    pipeline: Optional[str] = None,
) -> Tuple[str, Optional[dict]]:
    """Process a user chat message and route to the appropriate handler.

    Returns:
        (response_text, metadata) where metadata drives rich UI card rendering.
    """
    # M18 fix: Generate correlation ID for tracing this entire request across agents
    import uuid as _uuid
    correlation_id = str(_uuid.uuid4())[:8]
    logger.info("chat_request_start", correlation_id=correlation_id,
                user_id=user_id, session_id=session_id, message=message[:80])

    await event_bus.emit_agent_started(user_id, "supervisor", "Analyzing your request")

    result: Tuple[str, Optional[dict]] = ("", None)
    _t0 = time.monotonic()

    # ── Strip [ATTACHED FILE:] block for handlers that don't use it ──────────
    # interview_prep explicitly parses the block; all other handlers receive
    # only the user's plain-text intent so they don't choke on 6000-char dumps.
    def _strip_file_block(msg: str) -> str:
        if "[ATTACHED FILE:" not in msg:
            return msg
        clean = msg.split("[ATTACHED FILE:", 1)[0].strip()
        return clean or "Please process my attached file."

    try:
        # ── Slash-command pipeline override (bypasses LLM intent detection) ──
        if pipeline and not message.startswith("__"):
            history = await _load_conversation_history(user_id, session_id, db, limit=20)
            if pipeline == "job_search":
                result = await _handle_job_search_v2(user_id, session_id, _strip_file_block(message), db)
            elif pipeline == "cv_general":
                result = await _handle_cv_general_request(user_id, _strip_file_block(message), history, db)
            elif pipeline == "cv_tailor":
                result = await _handle_cv_tailor_intent(user_id, _strip_file_block(message), db)
            elif pipeline == "hr_finder":
                result = await _handle_hr_finder_standalone(user_id, _strip_file_block(message), db)
            elif pipeline == "interview_prep":
                result = await _handle_interview_prep_intent(user_id, message, db)  # keeps full block
            elif pipeline == "automated_apply":
                result = await _handle_auto_pipeline(user_id, _strip_file_block(message), db, session_id=session_id)
            elif pipeline == "cv_analysis":
                result = await _handle_cv_general_request(user_id, _strip_file_block(message), history, db)
            elif pipeline == "email":
                result = await _handle_email_compose_send(user_id, message, history, db)
            elif pipeline == "apply_jd":
                result = await _handle_apply_from_jd(user_id, _strip_file_block(message), db)
            elif pipeline == "cover_letter":
                result = await _handle_cover_letter(user_id, message, history, db)
            else:
                llm = get_llm(task="supervisor_routing")
                text = await _general_response(llm, _strip_file_block(message), history, user_id=user_id, db=db)
                result = (text, None)

        # ── Action Prefix Routing (programmatic card button clicks) ──────────
        elif message.startswith("__TAILOR_APPLY__:"):
            job_id = message.split(":", 1)[1].strip()
            result = await _handle_tailor_apply(user_id, job_id, db)

        elif message.startswith("__APPROVE_CV__:"):
            app_id = message.split(":", 1)[1].strip()
            result = await _handle_approve_cv(user_id, app_id, db)

        elif message.startswith("__SEND_EMAIL__:"):
            app_id = message.split(":", 1)[1].strip()
            result = await _handle_send_email(user_id, app_id, db)

        elif message.startswith("__REGENERATE_CV__:"):
            job_id = message.split(":", 1)[1].strip()
            result = await _handle_tailor_apply(user_id, job_id, db, regenerate=True)

        elif message.startswith("__PREP_INTERVIEW__:"):
            job_id = message.split(":", 1)[1].strip()
            result = await _handle_prep_interview(user_id, job_id, db)

        elif message.startswith("__EDIT_CV__:"):
            # Format: __EDIT_CV__:{tailored_cv_id}:{json_payload}
            rest = message[len("__EDIT_CV__:"):].strip()
            cv_id, _, json_str = rest.partition(":")
            result = await _handle_edit_cv(user_id, cv_id.strip(), json_str.strip(), db)

        elif message == "__APPLY_CV_IMPROVEMENTS__":
            result = await _handle_apply_cv_improvements(user_id, session_id, db)

        elif message.startswith("__SELECT_CV__:"):
            # Format: __SELECT_CV__:{cv_id}:{pending_intent}:{pending_context}
            rest = message[len("__SELECT_CV__:"):].strip()
            parts = rest.split(":", 2)
            if len(parts) == 3:
                sel_cv_id, pending_intent, pending_context = parts
                if pending_intent == "job_search":
                    import base64 as _b64
                    try:
                        original_msg = _b64.urlsafe_b64decode(pending_context.encode()).decode()
                    except Exception:
                        original_msg = pending_context
                    result = await _handle_job_search_v2(
                        user_id, session_id, original_msg, db, selected_cv_id=sel_cv_id.strip()
                    )
                elif pending_intent == "tailor":
                    result = await _handle_tailor_apply(
                        user_id, pending_context.strip(), db, selected_cv_id=sel_cv_id.strip()
                    )
                else:
                    result = ("Unrecognised pending action after CV selection.", None)
            else:
                result = ("Invalid CV selection format.", None)

        else:
            # ── Load conversation history for context-aware responses ─────────
            history = await _load_conversation_history(user_id, session_id, db, limit=20)
            clean_msg = _strip_file_block(message)

            # ── Fast keyword pre-classifier for unambiguous signals ───────────
            keyword_intent = _keyword_classify(clean_msg)
            logger.info("supervisor_keyword_intent", intent=keyword_intent, message=clean_msg[:80])

            if keyword_intent == "continuation":
                result = await _handle_continuation(user_id, session_id, history, db, message=clean_msg)

            elif keyword_intent == "cv_upload":
                result = (
                    "I'd love to help with your CV! Use the **CV upload button** "
                    "in the sidebar to upload your PDF or DOCX file. Once uploaded, "
                    "I'll automatically parse and analyze it for you.",
                    None,
                )

            elif keyword_intent == "automated_apply":
                # Direct full pipeline — no LLM needed for routing
                result = await _handle_auto_pipeline(user_id, clean_msg, db, session_id=session_id)

            elif keyword_intent == "job_search":
                # Explicit job listing request — show job cards via orchestrator
                result = await _orchestrate_agents(
                    user_id, session_id, clean_msg, history, ["job_search"], db
                )

            elif keyword_intent in ("cv_tailor", "cv_analysis", "cv_general"):
                result = await _handle_cv_general_request(user_id, clean_msg, history, db)

            elif keyword_intent == "interview_prep":
                result = await _handle_interview_prep_intent(user_id, message, db)

            elif keyword_intent == "status":
                text = await _handle_status_request(user_id, db)
                result = (text, None)

            else:
                # ── Intelligent multi-agent pipeline planner ──────────────────
                llm = get_llm(task="supervisor_routing")
                agents = await _plan_agents(llm, clean_msg, history)
                logger.info("supervisor_pipeline_plan", agents=agents, message=clean_msg[:100])
                result = await _orchestrate_agents(
                    user_id, session_id, clean_msg, history, agents, db
                )

    except Exception as e:
        logger.error("supervisor_handler_error", error=str(e), exc_info=True)
        result = (
            f"I ran into an issue processing your request: {str(e)}. Please try again.",
            None,
        )
        try:
            await db.rollback()  # clear PendingRollback state before logging
        except Exception:
            pass
        await _log_execution(db, user_id, session_id, "supervisor", "process_message",
                             "failed", int((time.monotonic() - _t0) * 1000), str(e))
        await event_bus.emit_agent_completed(user_id, "supervisor", result[0][:100])
        return result

    ms = int((time.monotonic() - _t0) * 1000)
    logger.info("chat_request_complete", correlation_id=correlation_id,
                duration_ms=ms, response_len=len(result[0]))
    await _log_execution(db, user_id, session_id, "supervisor", "process_message", "success", ms)
    await event_bus.emit_agent_completed(user_id, "supervisor", result[0][:100])
    return result


async def _load_conversation_history(
    user_id: str, session_id: str, db: AsyncSession, limit: int = 25
) -> list:
    """Load the last N messages for this session as a list of {role, content} dicts."""
    from sqlalchemy import select
    from app.db.models import ChatMessage

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    messages = list(reversed(messages))  # oldest first
    return [{"role": m.role, "content": m.content} for m in messages]


# ── User Context Loader ───────────────────────────────────────────────────────

async def _load_user_context(user_id: str, db: AsyncSession) -> dict:
    """Load the user's complete profile + pipeline state for personalised responses."""
    from sqlalchemy import select, desc, func
    from app.db.models import UserCV, Job, JobSearch, Application, InterviewPrep

    ctx: dict = {}

    # CV
    cv_row = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    cv = cv_row.scalar_one_or_none()
    if cv and cv.parsed_data:
        pd = cv.parsed_data
        personal = pd.get("personal_info", {})
        skills = pd.get("skills", {})
        exp = pd.get("experience", [])
        edu = pd.get("education", [])
        ctx["cv"] = {
            "name": personal.get("name", ""),
            "email": personal.get("email", ""),
            "location": personal.get("location", ""),
            "current_title": exp[0].get("role", "") if exp else "",
            "years_of_experience": len(exp),
            "technical_skills": skills.get("technical", [])[:12],
            "soft_skills": skills.get("soft", [])[:6],
            "tools": skills.get("tools", [])[:8],
            "recent_companies": [e.get("company", "") for e in exp[:4]],
            "education": [f"{e.get('degree','')} in {e.get('field','')} from {e.get('institution','')}" for e in edu[:2]],
            "summary": pd.get("summary", "")[:400],
        }

    # Job search history
    jobs_row = await db.execute(
        select(Job).join(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(desc(Job.created_at))
        .limit(15)
    )
    jobs = jobs_row.scalars().all()
    if jobs:
        ctx["recent_jobs"] = [
            {
                "title": j.title, "company": j.company,
                "location": j.location, "match_score": j.match_score,
                "hr_found": bool(getattr(j, "hr_found", None)),
            }
            for j in jobs
        ]

    # Applications
    apps_row = await db.execute(
        select(Application).where(Application.user_id == user_id)
        .order_by(desc(Application.created_at)).limit(10)
    )
    apps = apps_row.scalars().all()
    if apps:
        ctx["applications"] = [{"status": a.status, "job_id": a.job_id} for a in apps]
        status_counts: dict = {}
        for a in apps:
            status_counts[a.status] = status_counts.get(a.status, 0) + 1
        ctx["application_summary"] = status_counts

    # Interview preps
    prep_row = await db.execute(
        select(InterviewPrep).where(InterviewPrep.user_id == user_id)
        .order_by(desc(InterviewPrep.created_at)).limit(3)
    )
    preps = prep_row.scalars().all()
    if preps:
        ctx["interview_preps"] = len(preps)

    return ctx


def _format_user_context(ctx: dict) -> str:
    """Format user context dict into a readable block for LLM prompts."""
    lines = []
    if "cv" in ctx:
        cv = ctx["cv"]
        lines.append(f"CANDIDATE PROFILE:")
        if cv.get("name"):
            lines.append(f"  Name: {cv['name']}")
        if cv.get("current_title"): lines.append(f"  Current role: {cv['current_title']}")
        if cv.get("location"):      lines.append(f"  Location: {cv['location']}")
        if cv.get("years_of_experience"): lines.append(f"  Experience depth: {cv['years_of_experience']} roles")
        if cv.get("technical_skills"): lines.append(f"  Technical skills: {', '.join(cv['technical_skills'])}")
        if cv.get("tools"):         lines.append(f"  Tools: {', '.join(cv['tools'])}")
        if cv.get("recent_companies"): lines.append(f"  Previous employers: {', '.join(cv['recent_companies'])}")
        if cv.get("education"):     lines.append(f"  Education: {'; '.join(cv['education'])}")
        if cv.get("summary"):       lines.append(f"  Profile summary: {cv['summary'][:200]}")
    else:
        lines.append("CANDIDATE PROFILE: Not yet uploaded (no CV found)")

    if "recent_jobs" in ctx:
        lines.append(f"RECENT JOB SEARCHES ({len(ctx['recent_jobs'])} jobs found):")
        for j in ctx["recent_jobs"][:5]:
            hr = "✓ HR found" if j.get("hr_found") else "✗ no HR"
            lines.append(f"  • {j['title']} @ {j['company']} — {j.get('match_score', 0)}% match, {hr}")

    if "application_summary" in ctx:
        lines.append(f"APPLICATION PIPELINE: {ctx['application_summary']}")
    if "interview_preps" in ctx:
        lines.append(f"INTERVIEW PREPS COMPLETED: {ctx['interview_preps']}")
    if not lines:
        lines.append("(No user data loaded yet)")
    return "\n".join(lines)


# ── Fast Keyword Pre-Classifier (deterministic, runs before LLM) ──────────────

_CONTINUATION_SET = frozenset({
    "yes", "ok", "okay", "proceed", "continue", "go", "do it", "sure",
    "send", "send it", "confirm", "approve", "sounds good", "alright",
    "yep", "yup", "next", "go ahead", "absolutely", "correct", "right",
    "great", "perfect", "done", "please", "let's go", "start",
    # Short follow-up words that always mean "continue" in context
    "any", "all", "whatever", "anything", "all of them", "any of them",
    "doesn't matter", "no preference", "up to you", "you decide",
})

_RE_JOB_SEARCH = re.compile(
    r"\b(find|search|look|get|fetch|discover|show|list)\b.{0,25}\bjobs?\b"
    r"|\bjobs?\s+in\s+\w"
    r"|\bjob\s+(opportunities|openings|listings|vacancies)\b"
    r"|\b(find|get|show)\s+me\s+(some\s+)?(?:jobs?|roles?|positions?|openings?)\b"
    r"|\b(looking|searching|hunting)\s+for\s+\w+\s+jobs?\b"
    r"|\b(software|developer|engineer|designer|product|data|backend|frontend|full.?stack|senior|junior|devops|ml|ai|python|react|node)\s+(developer|engineer|manager|analyst|architect|lead)\s+jobs?\b",
    re.IGNORECASE,
)

_RE_AUTO_APPLY = re.compile(
    r"\b(apply\s+to\s+all|auto(mate|matic(ally)?)\s+apply|apply\s+for\s+me|run\s+the\s+pipeline"
    r"|do\s+everything\s+for\s+me|send\s+to\s+all\s+companies|apply\s+automatically)\b",
    re.IGNORECASE,
)

# "apply for N [role] in [location]" — user wants job search + full pipeline
_RE_APPLY_SEARCH = re.compile(
    r"\bapply\s+(?:for\s+)?(?:\d+\s+)?(?:\w+\s+){0,5}(?:jobs?|positions?|roles?|openings?|vacancies?)\b"
    r"|\bapply\s+(?:for\s+)?(?:\w+\s+){1,5}(?:in|at|across|within)\s+\w"
    r"|\bfind\s+(?:and\s+)?apply\b"
    r"|\b(?:search|find|get)\s+(?:me\s+)?(?:\d+\s+)?(?:\w+\s+){0,4}jobs?\s+(?:and\s+)?apply\b",
    re.IGNORECASE,
)

_RE_CV_TAILOR = re.compile(
    r"\b(tailor|customize|customise|adapt|modify|adjust|optimise|optimize)\b.{0,25}\b(cv|resume)\b",
    re.IGNORECASE,
)

_RE_CV_UPLOAD = re.compile(
    r"\b(upload|add|attach|change|update|replace|submit)\b.{0,20}\b(cv|resume)\b",
    re.IGNORECASE,
)

_RE_INTERVIEW = re.compile(
    r"\b(interview\s+prep|prepare\s+(?:me\s+)?for\s+(?:the\s+)?interview"
    r"|mock\s+interview|practice\s+(?:interview\s+)?questions"
    r"|behavioral\s+questions|technical\s+interview|prep\s+for\s+interview)\b",
    re.IGNORECASE,
)

# Only trigger cv_analysis for EXPLICIT requests — never for general questions
_RE_CV_ANALYSIS = re.compile(
    r"\b(analyz[ei]|review|score|evaluate|assess|critique|rate|audit)\b.{0,25}\b(my\s+)?(cv|resume|profile)\b"
    r"|\b(my\s+)?(cv|resume|profile)\b.{0,25}\b(analysis|review|score|feedback|rating|critique|assessment)\b"
    r"|\bwhat.{0,20}wrong\b.{0,20}\b(cv|resume)\b"
    r"|\bhow\s+(good|bad|strong|weak)\s+is\s+my\s+(cv|resume)\b",
    re.IGNORECASE,
)

# Only explicit status/count questions — not "show me my jobs"
_RE_STATUS_EXPLICIT = re.compile(
    r"\b(how\s+many\s+(?:applications?|jobs?|CVs?))\b"
    r"|\b(application|pipeline)\s+status\b"
    r"|\bmy\s+stats?\b"
    r"|\bdashboard\s+stats?\b",
    re.IGNORECASE,
)

# Detects when the user wants improvements applied (used to show "Apply" button)
_RE_IMPROVEMENT_REQUEST = re.compile(
    r"\b(improve|fix|enhance|rewrite|revamp|strengthen|optimize|optimise|upgrade|update)\b"
    r"|\bwhat.{0,25}(missing|wrong|weak|lacking|improve|change|add|remove)\b"
    r"|\bhow.{0,20}(better|improve|stronger|stronger)\b"
    r"|\b(give me|provide|list|suggest).{0,20}(suggestions?|improvements?|recommendations?)\b"
    r"|\b(what\s+should\s+I\s+)(add|remove|change|fix|include)\b",
    re.IGNORECASE,
)

# Broad CV questions that aren't explicit analysis/tailor/upload — route to cv_general agent
# Checked AFTER cv_tailor, cv_upload, cv_analysis so those specific patterns win first.
_RE_CV_GENERAL = re.compile(
    # ── Verb-first patterns: "improve my CV", "fix my resume", "help me with my profile"
    r"\b(improve|fix|enhance|strengthen|revamp|upgrade|polish|update|work\s+on"
    r"|help\s+(?:me\s+)?(?:with\s+)?(?:my\s+)?|make\s+(?:my\s+)?)\b"
    r".{0,30}\b(my\s+)?(cv|resume|profile)\b"
    # ── CV-first patterns: "my CV is weak", "my resume needs fixing"
    r"|\b(my\s+)?(cv|resume|profile)\b.{0,40}"
    r"\b(good|bad|strong|weak|ready|missing|lacking|complete|tips|advice|better"
    r"|improve|fix|update|change|edit|look|issues?|problems?|wrong|gaps?|feedback)\b"
    # ── Question words + CV: "what's wrong with my CV", "how is my resume"
    r"|\b(what|how|tell me|show|is|are|can|could|would|should|help|give me|help me)\b"
    r".{0,50}\b(my\s+)?(cv|resume|profile)\b"
    # ── Strength/weakness questions
    r"|\bwhat\s+(are|is)\s+(my|the)\s+(strongest?|best|key|main|top|weakest?|core)\s+"
    r"(skills?|strengths?|weaknesses?|areas?|points?|qualities)\b"
    r"|\bam\s+I\s+(qualified|suitable|a\s+good\s+fit|ready|experienced\s+enough"
    r"|overqualified|underqualified)\b"
    # ── Section rewrites: "rewrite my summary", "improve my headline"
    r"|\b(rewrite|write|generate|draft|improve|enhance|revise)\b.{0,30}"
    r"\b(summary|headline|bio|objective|cover\s+letter|bullet\s+point|achievement)\b"
    # ── CV strategy terms
    r"|\b(ats|applicant\s+tracking|keyword\s+gap|skill\s+gap|missing\s+skills?"
    r"|personal\s+brand(ing)?|career\s+gap|employment\s+gap)\b"
    # ── Role fit based on background
    r"|\bwhat\s+(roles?|jobs?|positions?|companies?)\b.{0,30}\b(suited|fit|good|qualified|eligible)\b"
    r"|\bam\s+I\s+.{0,20}\b(senior|junior|mid.?level|lead|principal)\b",
    re.IGNORECASE,
)

# Questions about existing saved jobs / applications (route to rich status, not search)
_RE_MY_JOBS = re.compile(
    r"\b(show|list|what|which|tell me about|view)\b.{0,30}\b(my\s+)?(saved|discovered|found|applied|pending|recent)\b.{0,20}\bjobs?\b"
    r"|\b(my\s+)?(jobs?|applications?)\b.{0,20}\b(I\s+)?(applied|found|discovered|saved|have)\b"
    r"|\bwhat\s+jobs?\s+(?:did\s+I|have\s+I|do\s+I)\b"
    r"|\bmy\s+applications?\b"
    r"|\bapplied\s+(?:jobs?|positions?)\b",
    re.IGNORECASE,
)


def _keyword_classify(message: str) -> Optional[str]:
    """Deterministic keyword pre-classifier — returns intent or None to fall back to LLM.

    Order matters: more specific patterns are checked before broader ones.
    Only returns an intent when highly confident. Ambiguous messages → None → LLM.
    """
    msg_stripped = message.strip()
    msg_lower = msg_stripped.lower()
    tokens = set(msg_lower.split())

    # 1. Continuation — short unambiguous approval words
    if msg_lower in _CONTINUATION_SET:
        return "continuation"
    if len(tokens) <= 3 and tokens & _CONTINUATION_SET and len(msg_lower) < 30:
        return "continuation"
    # Very short messages (1-2 words) with no recognisable action → continuation
    if len(tokens) <= 2 and len(msg_lower) < 20:
        return "continuation"

    # 2. Explicit full-pipeline automation
    if _RE_AUTO_APPLY.search(msg_stripped):
        return "automated_apply"

    # 3. "apply for N role in location" patterns → full pipeline (job search + apply)
    if _RE_APPLY_SEARCH.search(msg_stripped):
        return "automated_apply"

    # 3. CV operations (specific, explicit)
    if _RE_CV_TAILOR.search(msg_stripped):
        return "cv_tailor"
    if _RE_CV_UPLOAD.search(msg_stripped):
        return "cv_upload"
    if _RE_CV_ANALYSIS.search(msg_stripped):
        return "cv_analysis"

    # 4. Interview prep (explicit phrases only)
    if _RE_INTERVIEW.search(msg_stripped):
        return "interview_prep"

    # 5. Questions about existing saved jobs/applications
    if _RE_MY_JOBS.search(msg_stripped):
        return "status"

    # 6. Explicit status/count questions
    if _RE_STATUS_EXPLICIT.search(msg_stripped):
        return "status"

    # 7. Job search (broad — must come after status to avoid false positives)
    if _RE_JOB_SEARCH.search(msg_stripped):
        return "job_search"

    # 8. Broad CV questions (checked last — catches anything mentioning CV/resume
    #    that wasn't caught by the more specific patterns above)
    if _RE_CV_GENERAL.search(msg_stripped):
        return "cv_general"

    # Ambiguous — let LLM decide
    return None


# ── Intent Classifier ─────────────────────────────────────────────────────────

async def _classify_intent(llm, message: str, history: list = None) -> str:
    """Two-stage intent classification:
    1. Fast deterministic keyword pre-classifier (regex) — handles obvious cases instantly.
    2. LLM with chain-of-thought — only for genuinely ambiguous messages.
    """
    # Stage 1: keyword classifier (never misclassifies obvious cases)
    keyword_intent = _keyword_classify(message)
    if keyword_intent:
        logger.debug("supervisor_keyword_intent", intent=keyword_intent, message=message[:80])
        return keyword_intent

    # Stage 2: LLM for ambiguous messages
    history_block = "(no prior messages)"
    if history:
        recent = [m for m in history[-10:] if not m["content"].startswith("__")][-6:]
        if recent:
            history_block = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:250]}"
                for m in recent
            )

    prompt = f"""You are the intent router for CareerAgent — an AI career assistant.
Classify the LATEST user message into EXACTLY ONE of these intents:

  job_search       — user explicitly wants to FIND / SEARCH for new jobs right now
  cv_upload        — user wants to upload, change, or replace their CV file
  cv_tailor        — user wants to tailor their CV for a SPECIFIC named job or company
                     (ONLY when they name or reference a particular job/company/role they applied to)
  cv_analysis      — user explicitly asks to formally ANALYSE, SCORE, or AUDIT their CV
  cv_general       — ANY question or request about their own CV/resume/profile that is NOT cv_tailor:
                     general improvements, rewrites, "improve my CV", "fix my resume",
                     strengths, weaknesses, skill gaps, ATS tips, career fit, etc.
  interview_prep   — interview preparation, practice questions, mock interview, study plan
  status           — asking about saved jobs, applications, or pipeline state they ALREADY have
  continuation     — confirming / approving / continuing an in-progress task
  automated_apply  — full automated end-to-end apply pipeline
  general          — EVERYTHING ELSE: career advice, salary, industry trends, networking, etc.

⚠️  CRITICAL RULES — read very carefully:
- "cv_tailor" requires the user to name a SPECIFIC job or company they want to tailor for.
  "improve my CV", "fix my resume", "make my CV better" → these are cv_general, NOT cv_tailor.
  "tailor my CV for the Google SWE role" → cv_tailor.
- "cv_general" is the default for ANYTHING about the user's own CV that isn't cv_tailor/cv_upload/cv_analysis.
- "general" is the BROAD default for all career/work/life questions not related to their specific CV.
- "job_search" ONLY when the user explicitly wants to search for new jobs RIGHT NOW.
- "status" ONLY for questions about jobs/applications the user has ALREADY found or applied to.
- NEVER return "cv_tailor" unless the user explicitly names a job or company they want to target.

CONVERSATION HISTORY:
{history_block}

USER MESSAGE: "{message}"

Return ONLY the intent label — one word, lowercase, no punctuation, nothing else."""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        lines = [ln.strip() for ln in content.strip().splitlines() if ln.strip()]
        raw = lines[-1] if lines else content.strip()
        intent = raw.lower().replace('"', "").replace("'", "").split()[-1]
        valid = {
            "job_search", "cv_upload", "cv_tailor", "interview_prep",
            "cv_analysis", "cv_general", "status", "continuation", "automated_apply", "general",
        }
        result = intent if intent in valid else "general"
        logger.debug("supervisor_llm_intent", intent=result, message=message[:80])
        return result
    except Exception:
        return "general"


# ── CV session cache helper ───────────────────────────────────────────────────

async def _get_cached_cv_selection(user_id: str, db: AsyncSession) -> Optional[str]:
    """Return the CV the user picked during the most recent job search, if any.
    Reads the last 20 assistant messages and finds the first job_results one
    that stored a selected_cv_id.
    """
    from sqlalchemy import select, desc
    from app.db.models import ChatMessage

    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id, ChatMessage.role == "assistant")
        .order_by(desc(ChatMessage.created_at))
        .limit(20)
    )
    for msg in result.scalars().all():
        meta = msg.metadata_ or {}
        if meta.get("type") == "job_results" and meta.get("selected_cv_id"):
            return meta["selected_cv_id"]
    return None


# ── Multi-CV selection helper ─────────────────────────────────────────────────

async def _maybe_ask_cv_selection(
    user_id: str,
    db: AsyncSession,
    pending_intent: str,
    pending_context: str,
    selected_cv_id: Optional[str],
) -> Tuple[Optional[str], Optional[dict]]:
    """Check CV count before starting a workflow.

    Returns:
      (None, None)          — only 0 or 1 CV, or caller already chose one → proceed
      (text, metadata)      — >1 CV and no selection yet → return selection card
      ("error text", None)  — no CV uploaded at all
    """
    import base64 as _b64
    from sqlalchemy import select
    from app.db.models import UserCV

    if selected_cv_id:
        return None, None  # already chosen by user, skip prompt

    cv_result = await db.execute(
        select(UserCV)
        .where(UserCV.user_id == user_id)
        .order_by(UserCV.created_at.desc())
    )
    cvs = cv_result.scalars().all()

    if not cvs:
        # Job search can proceed without a CV (scoring is skipped, tailoring still requires one)
        if pending_intent == "job_search":
            return None, None
        return (
            "Please **upload your CV** first using the upload button in the sidebar. "
            "I need it to tailor applications and match you to the right jobs.",
            None,
        )

    if len(cvs) == 1:
        return None, None  # only one CV, no choice needed

    # Multiple CVs — encode context so it survives the round-trip inside the action string
    if pending_intent == "job_search":
        # pending_context is the raw user message — base64-encode it to avoid colon conflicts
        safe_context = _b64.urlsafe_b64encode(pending_context.encode()).decode()
    else:
        safe_context = pending_context  # job_id or other simple value

    return (
        f"You have **{len(cvs)} CVs** uploaded. Which one should I use for this task?",
        {
            "type": "cv_selection",
            "pending_intent": pending_intent,
            "pending_context": safe_context,
            "cvs": [
                {
                    "id": cv.id,
                    "file_name": cv.file_name,
                    "file_type": cv.file_type,
                    "is_primary": cv.is_primary,
                    "created_at": str(cv.created_at) if cv.created_at else None,
                }
                for cv in cvs
            ],
        },
    )


# ── Job Search Handler ────────────────────────────────────────────────────────

async def _handle_job_search_v2(
    user_id: str, session_id: str, message: str, db: AsyncSession,
    limit: int = 5, selected_cv_id: Optional[str] = None,
) -> Tuple[str, dict]:
    """Search for jobs, save to DB, return job_results metadata card."""
    from sqlalchemy import select
    from app.db.models import UserCV, JobSearch, Job
    from app.agents.job_hunter import search_jobs

    # ── Multi-CV check: ask user to pick if they have more than one ───────────
    sel_text, sel_meta = await _maybe_ask_cv_selection(
        user_id, db, "job_search", message, selected_cv_id
    )
    if sel_text is not None:
        return sel_text, sel_meta

    _t = time.monotonic()
    await event_bus.emit_agent_started(user_id, "job_hunter", f"Parsing search query: {message[:60]}")

    llm = get_llm(task="parse_search_query")
    prompt = f"""Extract job search parameters from this message:
"{message}"

Return JSON:
{{
  "query": "job title/role only — no location or employment type",
  "location": "city, region or country — or null",
  "job_type": "one of: fulltime, parttime, contract, temporary, internship, remote, hybrid — or null",
  "count": "number of jobs requested as an integer — or null if not specified",
  "country_code": "ISO 3166-1 alpha-2 code (e.g. us, gb, pk, de, in, ae) — or null"
}}
Return ONLY valid JSON."""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        params = json.loads(content)
    except Exception:
        params = {"query": message, "location": None, "job_type": None}

    search_query = params.get("query", message) or message
    location = params.get("location")
    job_type = params.get("job_type")
    country_code = (params.get("country_code") or "").lower() or None
    from app.agents.job_hunter import _infer_country_code
    if location:
        country_code = _infer_country_code(location, country_code)
    if not country_code:
        country_code = "us"

    # Compute limit: caller override > LLM-extracted count > default 10
    if limit != 5:  # caller explicitly passed a limit (e.g., auto pipeline)
        computed_limit = min(limit * 2, 15)
    else:
        raw_count = params.get("count")
        if raw_count is not None:
            try:
                requested = int(raw_count)
                computed_limit = min(requested * 2, 15)
            except (ValueError, TypeError):
                computed_limit = 10
        else:
            computed_limit = 10  # default when user doesn't specify

    await event_bus.emit_agent_progress(user_id, "job_hunter", 1, 3, f"Searching for: {search_query}", location or "any location")

    # Load CV for scoring: use selected CV if provided, else fall back to primary
    if selected_cv_id:
        cv_result = await db.execute(
            select(UserCV).where(UserCV.id == selected_cv_id, UserCV.user_id == user_id)
        )
    else:
        cv_result = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
        )
    cv = cv_result.scalar_one_or_none()
    cv_id = cv.id if cv else None
    cv_parsed_data = cv.parsed_data if cv else None

    jobs = await search_jobs(
        query=search_query,
        user_id=user_id,
        location=location,
        job_type=job_type,
        limit=computed_limit,
        cv_data=cv_parsed_data,
        country_code=country_code,
        skip_llm_parse=True,
    )

    if not jobs:
        await event_bus.emit_agent_completed(user_id, "job_hunter", "No jobs found")
        return (
            "I couldn't find any jobs matching your criteria. "
            "Try a different search query or location.",
            None,
        )

    # Note: Cross-search dedup was removed — it was too aggressive and caused
    # "No new jobs found" when users re-searched. Within-search dedup is already
    # handled by the job_hunter's source deduplication logic.

    raw_count = len(jobs)
    await event_bus.emit_agent_progress(user_id, "job_hunter", 2, 3, f"Scoring {raw_count} jobs against your CV", "Calculating match scores")

    # HR lookup runs as a background task AFTER we return job results to the user.
    # This prevents the Railway gateway timeout (502) that occurred when batch HR
    # lookups blocked the HTTP response for 60-120 seconds.
    # The background task emits hr_stream WebSocket events that update the UI.

    # Use a fresh DB session for writes — the original session's connection may have
    # dropped during the long external API calls (job search can take 30+ seconds).
    from app.db.database import AsyncSessionLocal
    saved_jobs = []
    search_id = None
    job_entries_for_hr: list[dict] = []  # collected for background HR lookup

    async with AsyncSessionLocal() as fresh_db:
        # Save JobSearch record
        job_search = JobSearch(
            user_id=user_id,
            cv_id=cv_id,
            search_query=search_query,
            target_location=location,
            status="completed",
        )
        fresh_db.add(job_search)
        await fresh_db.flush()
        search_id = job_search.id

        # Save Job records — truncate string fields to fit DB column limits
        for job_data in jobs:
            job_record = Job(
                search_id=job_search.id,
                title=(job_data.get("title", "") or "")[:250],
                company=(job_data.get("company", "") or "")[:250],
                location=(job_data.get("location") or "")[:250] or None,
                salary_range=(job_data.get("salary_range") or "")[:100] or None,
                job_type=(_ensure_str(job_data.get("job_type")) or "")[:50] or None,
                description=job_data.get("description", ""),
                requirements=job_data.get("requirements", []),
                application_url=job_data.get("application_url"),
                posted_date=(job_data.get("posted_date") or "")[:50] or None,
                source=(job_data.get("source", "ai_generated") or "unknown")[:50],
                company_domain=job_data.get("company_domain") or None,
                match_score=job_data.get("match_score"),
                matching_skills=job_data.get("matching_skills", []),
                missing_skills=job_data.get("missing_skills", []),
            )
            fresh_db.add(job_record)
            await fresh_db.flush()

            # Build why-match bullets from data
            matching = job_data.get("matching_skills", [])
            missing = job_data.get("missing_skills", [])
            why_match = []
            if matching:
                why_match.append(f"Matched skills: {', '.join(matching[:4])}")
            if missing:
                why_match.append(f"Gap areas: {', '.join(missing[:2])} (learnable)")
            if not why_match:
                why_match = ["Good fit based on role requirements"]

            saved_jobs.append({
                "id": job_record.id,
                "title": job_record.title,
                "company": job_record.company,
                "location": job_record.location,
                "salary_range": job_record.salary_range,
                "job_type": job_record.job_type,
                "match_score": job_record.match_score or 0,
                "matching_skills": job_record.matching_skills or [],
                "missing_skills": job_record.missing_skills or [],
                "why_match": why_match,
                "application_url": job_record.application_url,
                "hr_found": False,  # will be updated by background HR lookup task
            })
            # Collect minimal data for background HR lookup
            job_entries_for_hr.append({
                "job_id": job_record.id,
                "company": job_record.company,
                "title": job_record.title,
                "company_domain": job_data.get("company_domain", ""),
            })

        await fresh_db.commit()
        await _log_execution(fresh_db, user_id, session_id, "job_hunter", f"search:{search_query}", "success",
                             int((time.monotonic() - _t) * 1000))
        await fresh_db.commit()

    # Launch HR lookup as a background asyncio task — does NOT block the HTTP response.
    # Results stream to the frontend via hr_stream WebSocket events.
    # Store a strong reference in _background_tasks to prevent GC collection.
    _task = asyncio.create_task(_bg_hr_lookup(user_id, job_entries_for_hr))
    _background_tasks.add(_task)
    _task.add_done_callback(_background_tasks.discard)
    # Also track per-user so cancel_user_tasks() can stop it on conversation switch
    _user_bg_tasks.setdefault(user_id, []).append(_task)

    await event_bus.emit_agent_completed(user_id, "job_hunter", f"Found {len(saved_jobs)} positions — searching HR contacts in background")
    await event_bus.emit_workflow_update(user_id, "job_hunter", ["job_hunter"], ["hr_finder", "cv_tailor", "email_sender"])

    location_str = f" in {location}" if location else ""
    text = (
        f"Found **{len(saved_jobs)} positions** matching \"{search_query}\"{location_str}. "
        "I'm now searching for HR contacts in the background — "
        "jobs will show a **✓ HR found** badge as contacts are discovered. "
        "Click **'Tailor CV & Apply'** on any job to begin the application pipeline."
    )

    return (text, {
        "type": "job_results",
        "search_id": search_id,
        "jobs": saved_jobs,
        "selected_cv_id": selected_cv_id or cv_id,   # remembered for tailor step
        "search_query": search_query,
        "search_location": location,
    })


# ── Background HR Lookup ──────────────────────────────────────────────────────

async def _bg_hr_lookup(user_id: str, job_entries: list[dict]) -> None:
    """Background task: find HR contacts in PARALLEL and update DB + emit WS events.

    All company lookups fire simultaneously (with a concurrency semaphore to
    avoid hammering external APIs). Results stream to the frontend via
    hr_stream WebSocket events as each one completes.
    """
    from app.agents.hr_finder import find_hr_contact
    from app.db.database import AsyncSessionLocal
    from app.db.models import HRContact as _HRContact

    if not job_entries:
        return

    await event_bus.emit_agent_started(
        user_id, "hr_finder",
        f"Searching HR contacts for {len(job_entries)} companies in parallel…"
    )

    # Emit "searching" for ALL companies up-front so the UI shows spinners
    for entry in job_entries:
        await event_bus.emit(user_id, "hr_stream", {
            "phase": "searching",
            "company": entry["company"],
            "job_title": entry["title"],
        })

    found_count = 0
    # Semaphore limits concurrency to avoid rate-limit issues with Hunter/APIs
    sem = asyncio.Semaphore(5)

    async def _lookup_one(entry: dict) -> bool:
        """Lookup a single company's HR contact. Returns True if found."""
        nonlocal found_count
        job_id = entry["job_id"]
        company = entry["company"]
        title = entry["title"]
        domain = entry.get("company_domain") or ""

        async with sem:
            try:
                result = await asyncio.wait_for(
                    find_hr_contact(
                        company=company,
                        job_title=title,
                        company_domain=domain or None,
                        user_id=user_id,
                    ),
                    timeout=45,
                )

                if result.get("hr_email"):
                    found_count += 1
                    async with AsyncSessionLocal() as db:
                        db.add(_HRContact(
                            job_id=job_id,
                            hr_name=result.get("hr_name"),
                            hr_email=result.get("hr_email"),
                            hr_title=result.get("hr_title"),
                            hr_linkedin=result.get("hr_linkedin") or "",
                            confidence_score=result.get("confidence_score"),
                            source=result.get("source"),
                            verified=result.get("verified", False),
                        ))
                        hunter_domain = result.get("resolved_domain")
                        if hunter_domain:
                            from app.db.models import Job as _Job
                            job_row = await db.get(_Job, job_id)
                            if job_row and not job_row.company_domain:
                                job_row.company_domain = hunter_domain
                        await db.commit()
                    await event_bus.emit(user_id, "hr_stream", {
                        "phase": "found",
                        "company": company,
                        "job_title": title,
                        "email": result.get("hr_email"),
                        "total_found": len(result.get("all_recipients", [])),
                    })
                    return True
                else:
                    await event_bus.emit(user_id, "hr_stream", {
                        "phase": "not_found",
                        "company": company,
                        "job_title": title,
                    })
                    return False
            except asyncio.TimeoutError:
                logger.warning("bg_hr_lookup_timeout", company=company)
                await event_bus.emit(user_id, "hr_stream", {
                    "phase": "not_found",
                    "company": company,
                    "job_title": title,
                })
                return False
            except Exception as e:
                logger.warning("bg_hr_lookup_error", company=company, error=str(e))
                await event_bus.emit(user_id, "hr_stream", {
                    "phase": "not_found",
                    "company": company,
                    "job_title": title,
                })
                return False

    # Fire ALL lookups in parallel
    await asyncio.gather(*[_lookup_one(entry) for entry in job_entries])

    await event_bus.emit_agent_completed(
        user_id, "hr_finder",
        f"HR search complete: {found_count}/{len(job_entries)} contacts found"
    )
    # Custom event so the frontend knows the BACKGROUND search is done
    await event_bus.emit(user_id, "hr_bg_search_done", {
        "found": found_count,
        "total": len(job_entries),
    })


# ── Continuation Handler ──────────────────────────────────────────────────────

_APPROVAL_WORDS = frozenset({
    "yes", "approve", "approved", "send", "send it", "proceed", "confirm",
    "ok", "okay", "go", "go ahead", "do it", "sure", "sounds good",
    "alright", "yep", "yup", "absolutely", "correct", "right",
})

def _is_explicit_approval(msg: str) -> bool:
    """Return True only when the user's message is a short, unambiguous approval.

    H5/M8 fix: Require the message to be short (<=8 words) and not contain
    qualifiers like 'but', 'however', 'also', 'change', 'edit', 'wait' that
    indicate the user wants modifications, not a plain approval.
    """
    cleaned = msg.lower().strip()
    tokens = cleaned.split()
    # Must be a short message — long messages with "yes" are likely conditional
    if len(tokens) > 8:
        return False
    # Reject if it contains qualifier/edit words
    _DISQUALIFIERS = {"but", "however", "also", "change", "edit", "modify", "wait",
                      "stop", "cancel", "don't", "dont", "no", "not", "instead",
                      "actually", "different", "wrong", "fix", "update", "redo"}
    if tokens and set(tokens) & _DISQUALIFIERS:
        return False
    return any(word in _APPROVAL_WORDS for word in tokens[:6])


async def _handle_continuation(
    user_id: str, session_id: str, history: list, db: AsyncSession, message: str = ""
) -> Tuple[str, Optional[dict]]:
    """Resume the pipeline from the last known state using conversation history metadata."""
    from sqlalchemy import select, desc
    from app.db.models import ChatMessage, Job, JobSearch, Application

    # Look at recent assistant messages for metadata to decide next step
    result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
            ChatMessage.role == "assistant",
        )
        .order_by(desc(ChatMessage.created_at))
        .limit(10)
    )
    recent_assistant = result.scalars().all()

    for msg in recent_assistant:
        meta = msg.metadata_ or {}
        mtype = meta.get("type")

        if mtype == "job_results":
            # Jobs were shown — the user must click a specific job card to start tailoring.
            # Do NOT auto-select or auto-tailor — that skips the user's choice.
            jobs_in_meta = meta.get("jobs", [])
            unapplied = []
            for job_entry in jobs_in_meta:
                job_id = job_entry.get("id")
                if not job_id:
                    continue
                # H2 fix: Verify job still exists in DB before referencing it
                job_exists = await db.execute(
                    select(Job).where(Job.id == job_id).limit(1)
                )
                if not job_exists.scalar_one_or_none():
                    continue  # Job was deleted — skip ghost reference
                app_check = await db.execute(
                    select(Application).where(
                        Application.user_id == user_id,
                        Application.job_id == job_id,
                    ).limit(1)
                )
                if not app_check.scalar_one_or_none():
                    unapplied.append(job_entry)

            if unapplied:
                titles = ", ".join(
                    f"**{j.get('title','?')}** at {j.get('company','?')}"
                    for j in unapplied[:3]
                )
                return (
                    f"You have {len(unapplied)} job(s) ready to apply to: {titles}.\n\n"
                    "Click **'Tailor CV & Apply'** on the job you want to apply to first.",
                    None,
                )
            return ("All jobs from that search have been processed! "
                    "Check your Applications tab or search for more jobs.", None)

        elif mtype == "cv_review":
            app_id = meta.get("application_id")
            if app_id:
                if _is_explicit_approval(message):
                    await event_bus.emit_log_entry(
                        user_id, "supervisor", "User approved CV", "Generating PDF and preparing email"
                    )
                    return await _handle_approve_cv(user_id, app_id, db)
                return (
                    "Please review your tailored CV above.\n\n"
                    "Click **Approve** on the card, or type **'approve'** / **'yes'** to generate the PDF and see the email draft.",
                    None,
                )

        elif mtype == "email_review":
            app_id = meta.get("application_id")
            if app_id:
                if _is_explicit_approval(message):
                    await event_bus.emit_log_entry(
                        user_id, "supervisor", "User approved email", "Sending application"
                    )
                    return await _handle_send_email(user_id, app_id, db)
                return (
                    "Please review the email draft above.\n\n"
                    "Click **Send** on the card, or type **'send'** / **'yes'** to send the application to the hiring team.",
                    None,
                )

        elif mtype == "application_sent":
            next_job = meta.get("next_job_suggestion")
            if next_job:
                job_id = next_job.get("job_id")
                if job_id and _is_explicit_approval(message):
                    await event_bus.emit_log_entry(
                        user_id, "supervisor", "Continuing Pipeline",
                        f"Moving to next job: {next_job.get('title','')} at {next_job.get('company','')}"
                    )
                    return await _handle_tailor_apply(user_id, job_id, db)
                elif job_id:
                    return (
                        f"Next up: **{next_job.get('title','?')}** at **{next_job.get('company','?')}**.\n\n"
                        "Type **'yes'** or **'next'** to start tailoring, or search for different jobs.",
                        None,
                    )
            return (
                "All pending applications have been sent! "
                "You can search for more jobs or check your Applications tab.",
                None,
            )

    # Fallback: look for any pending application in DB
    pending_app = await db.execute(
        select(Application)
        .where(Application.user_id == user_id, Application.status == "pending_approval")
        .order_by(Application.created_at.asc()).limit(1)
    )
    app = pending_app.scalar_one_or_none()
    if app:
        if _is_explicit_approval(message):
            return await _handle_approve_cv(user_id, app.id, db)
        return (
            "You have a pending application awaiting your approval. "
            "Scroll up to the CV review card and click **Approve**, or type **'approve'** to continue.",
            None,
        )

    # Look for recent unsent jobs — suggest instead of auto-triggering (C3 fix)
    recent_job = await db.execute(
        select(Job).join(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(desc(Job.created_at)).limit(1)
    )
    job = recent_job.scalar_one_or_none()
    if job:
        if _is_explicit_approval(message):
            return await _handle_tailor_apply(user_id, job.id, db)
        return (
            f"You have a recent job: **{getattr(job, 'title', '?')}** at **{getattr(job, 'company', '?')}**.\n\n"
            "Type **'yes'** to start tailoring your CV for it, or tell me what else you'd like to do.",
            None,
        )

    return (
        "I'm not sure what to continue — there's no active task in your session.\n\n"
        "You can:\n"
        "- **Find jobs**: *'Find me backend developer roles in London'*\n"
        "- **Check status**: *'Show my applications'*\n"
        "- **Upload CV**: Use the sidebar upload button",
        None,
    )


# ── Automated Full Pipeline ────────────────────────────────────────────────────

async def _handle_auto_pipeline(
    user_id: str, message: str, db: AsyncSession, session_id: str = None
) -> Tuple[str, Optional[dict]]:
    """Find jobs matching user criteria and present them as an interactive card.

    HR contacts are looked up in the background. The user reviews each job
    and clicks 'Tailor CV & Apply' — the full approval flow (CV review →
    email review → send) is triggered per-job, never auto-approved.
    """
    await event_bus.emit_workflow_update(user_id, "supervisor", [], ["job_hunter", "hr_finder"])

    text, search_meta = await _handle_job_search_v2(
        user_id, session_id or "", message, db
    )

    if not search_meta:
        return ("I couldn't find matching jobs. Please try a more specific search.", None)

    jobs = search_meta.get("jobs", [])
    if not jobs:
        return ("No jobs were found for that query. Try different keywords.", None)

    query = search_meta.get("search_query", "your criteria")
    location = search_meta.get("search_location")
    location_str = f" in **{location}**" if location else ""
    response_text = (
        f"Found **{len(jobs)} positions** for \"{query}\"{location_str}. "
        "HR contacts are being found in the background — "
        "jobs will update with **✓ HR** badges as contacts are discovered.\n\n"
        "Click **'Tailor CV & Apply'** on any job to start — "
        "you'll **review and approve** your tailored CV and email before anything is sent."
    )

    return (response_text, search_meta)


# ── CV Tailor Intent Handler ──────────────────────────────────────────────────

async def _handle_cv_tailor_intent(
    user_id: str, message: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """NL intent fallback — route to tailor-from-description."""
    return await _handle_cv_tailor_from_description(user_id, message, db)


async def _handle_cv_tailor_from_description(
    user_id: str, message: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """
    /tailor pipeline handler.

    If the message contains a job description (>40 chars), create a temp
    Job record and tailor the user's CV against it, then generate the PDF
    and return a cv_improved card with a download button.

    If there is no description, ask the user to paste one.
    """
    from sqlalchemy import select
    from app.db.models import UserCV, Job, JobSearch as JobSearchModel, TailoredCV
    from app.agents.cv_tailor import tailor_cv_for_job
    from app.agents.doc_generator import generate_cv_pdf

    # ── Require a job description ─────────────────────────────────────────────
    if len(message.strip()) < 40:
        return (
            "Please paste the **job description** (or at least the job title + company + key "
            "requirements) so I can tailor your CV specifically for it.\n\n"
            "Example: _/tailor then paste the full JD below_",
            None,
        )

    # ── Load user CV ──────────────────────────────────────────────────────────
    cv_result = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    cv = cv_result.scalar_one_or_none()
    if not cv or not cv.parsed_data:
        return (
            "Please **upload your CV** first using the sidebar upload button, "
            "then use /tailor with a job description.",
            None,
        )

    # ── Extract title + company from the description via LLM ─────────────────
    llm = get_llm(task="supervisor_routing")
    extract_prompt = f"""Extract job title and company name from this job description.
Return ONLY JSON: {{"title": "...", "company": "..."}}
If company is not mentioned, set it to "Unknown Company".
Job Description: \"\"\"{message[:800]}\"\"\""""
    try:
        resp = await llm.ainvoke(extract_prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        meta = json.loads(m.group()) if m else {}
    except Exception:
        meta = {}

    title   = (meta.get("title")   or "Unknown Role").strip()
    company = (meta.get("company") or "Unknown Company").strip()

    # ── Create temp JobSearch + Job records ───────────────────────────────────
    search = JobSearchModel(
        user_id=user_id,
        search_query=f"tailor for {title} at {company}",
        target_location="",
        status="completed",
    )
    db.add(search)
    await db.flush()

    job = Job(
        search_id=search.id,
        title=title,
        company=company,
        description=message,
        location="",
        job_type="Full-time",
        source="manual",
        match_score=0,
    )
    db.add(job)
    await db.flush()

    # ── Tailor CV ─────────────────────────────────────────────────────────────
    await event_bus.emit_agent_started(
        user_id, "cv_tailor", f"Tailoring CV for {title} at {company}"
    )
    job_data = {
        "title": title,
        "company": company,
        "description": message,
        "requirements": [],
    }
    tailoring_result = await tailor_cv_for_job(cv.parsed_data, job_data)
    await event_bus.emit_agent_completed(user_id, "cv_tailor", f"CV tailored for {title}")

    # ── Save TailoredCV ───────────────────────────────────────────────────────
    tailored_cv = TailoredCV(
        user_id=user_id,
        original_cv_id=cv.id,
        job_id=job.id,
        tailored_data=tailoring_result.get("tailored_cv", {}),
        cover_letter=tailoring_result.get("cover_letter"),
        ats_score=tailoring_result.get("ats_score"),
        match_score=tailoring_result.get("match_score"),
        changes_made=tailoring_result.get("changes_made", []),
        status="completed",
    )
    db.add(tailored_cv)
    await db.flush()

    # ── Generate PDF immediately ──────────────────────────────────────────────
    pdf_path = None
    candidate_name = (cv.parsed_data.get("personal_info", {}) or {}).get("name", "")
    try:
        await event_bus.emit_agent_started(user_id, "doc_generator", "Generating tailored CV PDF")
        pdf_path = await generate_cv_pdf({"tailored_cv": tailoring_result.get("tailored_cv", {})})
        tailored_cv.pdf_path = pdf_path
        await event_bus.emit_agent_completed(user_id, "doc_generator", "PDF ready")
    except Exception as e:
        logger.warning("tailor_pdf_failed", error=str(e))

    await db.commit()

    ats_score   = tailoring_result.get("ats_score", 0) or 0
    match_score = tailoring_result.get("match_score", 0) or 0

    metadata = {
        "type": "cv_improved",
        "tailored_cv_id": str(tailored_cv.id),
        "has_pdf": bool(pdf_path),
        "name": candidate_name,
    }

    text = (
        f"✅ Your CV has been tailored for **{title}** at **{company}**!\n\n"
        f"🎯 ATS Score: **{ats_score}%** · Match: **{match_score}%**\n\n"
        "Download the tailored CV PDF or open the editor to fine-tune it."
    )

    return (text, metadata)


# ── Skip-to-next-job helper ───────────────────────────────────────────────────

async def _skip_to_next_job(
    user_id: str,
    skipped_job_id: str,
    skipped_job,
    db: AsyncSession,
    skipped: set,
) -> Tuple[str, Optional[dict]]:
    """Find the next job in the same search that hasn't been tried or applied to yet."""
    from sqlalchemy import select
    from app.db.models import Job, JobSearch, Application

    skipped = skipped | {skipped_job_id}

    # Find sibling jobs in the same search, ordered by match_score desc
    candidate_rows = await db.execute(
        select(Job)
        .join(JobSearch, Job.search_id == JobSearch.id)
        .where(
            JobSearch.user_id == user_id,
            Job.id.notin_(skipped),
        )
        .order_by(Job.match_score.desc().nulls_last(), Job.created_at.desc())
        .limit(20)
    )
    candidates = candidate_rows.scalars().all()

    # Exclude jobs that already have an application
    applied_ids_result = await db.execute(
        select(Application.job_id).where(Application.user_id == user_id)
    )
    applied_ids = {r for r in applied_ids_result.scalars().all()}

    next_job = next((j for j in candidates if j.id not in applied_ids), None)

    if not next_job:
        return (
            f"Skipped **{skipped_job['company'] if isinstance(skipped_job, dict) else skipped_job.company}** "
            f"(no verified HR email). No more jobs available in this search — "
            f"try a new job search to find more opportunities.",
            None,
        )

    await event_bus.emit_log_entry(
        user_id, "supervisor", "Skipping Job",
        f"No HR email for {skipped_job.company} — trying {next_job.title} at {next_job.company}"
    )

    return await _handle_tailor_apply(user_id, next_job.id, db, _skipped=skipped)


# ── Tailor + Apply Handler ────────────────────────────────────────────────────

async def _handle_tailor_apply(
    user_id: str, job_id: str, db: AsyncSession, regenerate: bool = False,
    _skipped: set = None, selected_cv_id: Optional[str] = None,
) -> Tuple[str, Optional[dict]]:
    """Tailor CV, find HR contact, compose email, save records, return cv_review metadata."""
    if _skipped is None:
        _skipped = set()
    from sqlalchemy import select, desc
    from app.db.models import UserCV, Job, TailoredCV, HRContact, Application
    from app.agents.cv_tailor import tailor_cv_for_job
    from app.agents.hr_finder import find_hr_contact
    from app.agents.email_sender import compose_application_email

    # Load job
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        return ("Job not found. Please search for jobs first.", None)

    # ── Recall CV chosen during job search — never ask twice ─────────────────
    if not selected_cv_id:
        selected_cv_id = await _get_cached_cv_selection(user_id, db)

    # ── Multi-CV check: only prompts if no CV was ever selected yet ───────────
    sel_text, sel_meta = await _maybe_ask_cv_selection(
        user_id, db, "tailor", job_id, selected_cv_id
    )
    if sel_text is not None:
        return sel_text, sel_meta

    # Load CV: use selected if provided, else fall back to primary
    if selected_cv_id:
        cv_result = await db.execute(
            select(UserCV).where(UserCV.id == selected_cv_id, UserCV.user_id == user_id)
        )
    else:
        cv_result = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
        )
    cv = cv_result.scalar_one_or_none()
    if not cv or not cv.parsed_data:
        return (
            "Please **upload your CV** first (use the sidebar upload button) "
            "so I can tailor it for this job.",
            None,
        )

    await event_bus.emit_agent_started(
        user_id, "cv_tailor", f"Tailoring CV for {job.title} at {job.company}"
    )

    job_data = {
        "title": job.title,
        "company": job.company,
        "description": job.description or "",
        "requirements": job.requirements or [],
    }

    # 1. Tailor CV
    _t_tailor = time.monotonic()
    tailoring_result = await tailor_cv_for_job(cv.parsed_data, job_data)
    _session_id = str(getattr(db, "_session_id", "unknown"))
    await _log_execution(db, user_id, "tailor", "cv_tailor", f"tailor:{job.title}@{job.company}",
                         "success", int((time.monotonic() - _t_tailor) * 1000))

    await event_bus.emit_agent_completed(user_id, "cv_tailor", f"CV tailored for {job.title}")
    await event_bus.emit_agent_started(user_id, "hr_finder", f"Loading HR contact for {job.company}")

    # 2. Load pre-fetched HR contact from DB (stored during job search pre-filter)
    _t_hr = time.monotonic()
    existing_hr_result = await db.execute(
        select(HRContact).where(HRContact.job_id == job_id)
        .order_by(HRContact.created_at.desc()).limit(1)
    )
    existing_hr = existing_hr_result.scalar_one_or_none()

    if existing_hr and existing_hr.hr_email:
        # Use stored HR contact — no re-lookup needed
        hr_contact = {
            "hr_name": existing_hr.hr_name or "Hiring Team",
            "hr_email": existing_hr.hr_email,
            "hr_title": existing_hr.hr_title or "HR",
            "hr_linkedin": existing_hr.hr_linkedin or "",
            "confidence_score": existing_hr.confidence_score or 0.7,
            "source": existing_hr.source or "pre_fetched",
            "verified": existing_hr.verified or False,
        }
        _hr_already_saved = True
    else:
        # Fallback live lookup (e.g. manual tailor triggered outside of search flow)
        _hr_already_saved = False
        company_domain = job.company_domain or None
        hr_contact = await find_hr_contact(job.company, job.title, company_domain=company_domain, user_id=user_id)

        # Save Hunter-resolved domain back to the Job record for future lookups
        hunter_domain = hr_contact.get("resolved_domain")
        if hunter_domain and not job.company_domain:
            job.company_domain = hunter_domain
            await db.flush()

        if hr_contact.get("source") == "not_found":
            await _log_execution(db, user_id, "tailor", "hr_finder", f"find_hr:{job.company}",
                                 "warning", int((time.monotonic() - _t_hr) * 1000), "no verified email")
            await event_bus.emit_agent_completed(
                user_id, "hr_finder", f"No HR email found for {job.company}"
            )
            return (
                f"Could not find a verified HR contact email for **{job.company}**. "
                "Try a new job search — the pre-filter will only include jobs with findable HR contacts.",
                None,
            )

    await _log_execution(db, user_id, "tailor", "hr_finder", f"find_hr:{job.company}",
                         "success", int((time.monotonic() - _t_hr) * 1000))
    await event_bus.emit_agent_completed(user_id, "hr_finder", f"HR contact ready for {job.company}")

    await event_bus.emit_agent_started(user_id, "email_sender", f"Composing application email")

    # 3. Load user LinkedIn URL from preferences
    from app.db.models import User as _UserModel
    _user_row = await db.execute(select(_UserModel).where(_UserModel.id == user_id))
    _user_obj = _user_row.scalar_one_or_none()
    _linkedin_url = (_user_obj.preferences or {}).get("linkedin_url", "") if _user_obj else ""

    # 4. Compose email
    _t_email = time.monotonic()
    email_result = await compose_application_email(
        job_data=job_data,
        cv_data=cv.parsed_data,
        hr_contact=hr_contact,
        cover_letter=tailoring_result.get("cover_letter"),
        linkedin_url=_linkedin_url or None,
    )
    await _log_execution(db, user_id, "tailor", "email_sender", f"compose:{job.title}@{job.company}",
                         "success", int((time.monotonic() - _t_email) * 1000))

    await event_bus.emit_agent_completed(user_id, "email_sender", "Application email composed")
    await event_bus.emit_log_entry(user_id, "doc_generator", "Saving application records", "Persisting to database")

    # 4. Save TailoredCV
    tailored_cv = TailoredCV(
        user_id=user_id,
        original_cv_id=cv.id,
        job_id=job_id,
        tailored_data=tailoring_result.get("tailored_cv", {}),
        cover_letter=tailoring_result.get("cover_letter"),
        ats_score=tailoring_result.get("ats_score"),
        match_score=tailoring_result.get("match_score"),
        changes_made=tailoring_result.get("changes_made", []),
        status="completed",
    )
    db.add(tailored_cv)
    await db.flush()

    # 5. Save HRContact (skip if already saved during job search pre-filter)
    if _hr_already_saved and existing_hr:
        hr_contact_record = existing_hr
    else:
        hr_contact_record = HRContact(
            job_id=job_id,
            hr_name=hr_contact.get("hr_name"),
            hr_email=hr_contact.get("hr_email"),
            hr_title=hr_contact.get("hr_title"),
            hr_linkedin=hr_contact.get("hr_linkedin"),
            confidence_score=hr_contact.get("confidence_score"),
            source=hr_contact.get("source"),
            verified=bool(hr_contact.get("verified", False)),
            additional_emails=hr_contact.get("all_recipients", []),
        )
        db.add(hr_contact_record)
        await db.flush()

    # 6. Save/update Application
    application = None
    if regenerate:
        app_result = await db.execute(
            select(Application)
            .where(Application.user_id == user_id, Application.job_id == job_id)
            .order_by(desc(Application.created_at))
            .limit(1)
        )
        application = app_result.scalar_one_or_none()

    if application and regenerate:
        application.tailored_cv_id = tailored_cv.id
        application.hr_contact_id = hr_contact_record.id
        application.email_subject = email_result.get("email_subject")
        application.email_body = email_result.get("email_body")
        application.status = "pending_approval"
        application.user_approved = False
    else:
        application = Application(
            user_id=user_id,
            job_id=job_id,
            tailored_cv_id=tailored_cv.id,
            hr_contact_id=hr_contact_record.id,
            email_subject=email_result.get("email_subject"),
            email_body=email_result.get("email_body"),
            status="pending_approval",
        )
        db.add(application)

    await db.commit()
    await db.refresh(application)

    await event_bus.emit_log_entry(user_id, "supervisor", "Application Ready for Review",
                                   f"{job.title} at {job.company} — review CV below", "done")

    # Build metadata for CV review card
    tailored_cv_data = tailoring_result.get("tailored_cv", {})
    personal = cv.parsed_data.get("personal_info", {})

    contact_parts = [
        p for p in [personal.get("email"), personal.get("phone"), personal.get("location")] if p
    ]
    contact_str = " · ".join(contact_parts)

    skills = tailored_cv_data.get("skills", {})
    if isinstance(skills, dict):
        all_skills: list = []
        for sk_cat, sk_list in skills.items():
            if sk_cat.startswith("_") or sk_cat == "all":
                continue
            if isinstance(sk_list, list):
                all_skills.extend(sk_list[:5])
        skills_str = ", ".join(all_skills[:12])
    else:
        skills_str = str(skills) if skills else ""

    keyword_match = tailoring_result.get("keyword_match", [])
    ats_score = tailoring_result.get("ats_score", 0) or 0
    match_score = tailoring_result.get("match_score", 0) or 0
    bowjob_analysis = tailoring_result.get("_analysis", {})

    metadata = {
        "type": "cv_review",
        "application_id": application.id,
        "tailored_cv_id": tailored_cv.id,
        "job_id": job_id,
        "job": {"title": job.title, "company": job.company},
        "tailored_cv": {
            "name": personal.get("name", ""),
            "contact": contact_str,
            "summary": tailored_cv_data.get("summary", ""),
            "experience": tailored_cv_data.get("experience", []),
            "skills": skills_str,
            "skills_raw": tailored_cv_data.get("skills", {}),
            "education": tailored_cv_data.get("education") or cv.parsed_data.get("education", []),
            "certifications": tailored_cv_data.get("certifications", []),
            "projects": tailored_cv_data.get("projects", []),
        },
        "ats_score": ats_score,
        "match_score": match_score,
        "keywords_matched": len(keyword_match),
        "keywords_total": len(keyword_match) + 2,
        "changes_made": tailoring_result.get("changes_made", []),
        "cover_letter": tailoring_result.get("cover_letter", ""),
        # BowJob rich analysis
        "industry": bowjob_analysis.get("industry"),
        "skills_analysis": bowjob_analysis.get("skills_analysis", {}),
        "writing_quality": bowjob_analysis.get("writing_quality", {}),
        "red_flags": bowjob_analysis.get("red_flags", []),
        "overall_feedback": bowjob_analysis.get("overall_feedback", {}),
        "score_breakdown": (bowjob_analysis.get("scores") or {}).get("breakdown", {}),
    }

    text = (
        f"I've tailored your CV for **{job.title}** at **{job.company}**!\n\n"
        f"🎯 ATS Score: **{ats_score}%** | Match: **{match_score}%** | "
        f"Keywords matched: **{len(keyword_match)}**\n\n"
        "Review the tailored CV below. Click **Approve** to generate the PDF and review the email."
    )

    return (text, metadata)


# ── Approve CV Handler ────────────────────────────────────────────────────────

async def _handle_approve_cv(
    user_id: str, app_id: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Generate PDF for approved CV, return email_review metadata."""
    from sqlalchemy import select
    from app.db.models import Application, TailoredCV, HRContact, Job, UserCV, User

    app_result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user_id)
    )
    application = app_result.scalar_one_or_none()
    if not application:
        return ("Application not found.", None)

    # Load tailored CV
    tailored_cv = None
    if application.tailored_cv_id:
        tc_result = await db.execute(
            select(TailoredCV).where(TailoredCV.id == application.tailored_cv_id)
        )
        tailored_cv = tc_result.scalar_one_or_none()

    # Generate PDF
    pdf_path = None
    pdf_filename = "CV_Tailored.pdf"

    if tailored_cv and tailored_cv.tailored_data:
        from app.agents.doc_generator import generate_cv_pdf

        # Get candidate name for filename
        cv_result = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
        )
        cv = cv_result.scalar_one_or_none()
        personal = (cv.parsed_data or {}).get("personal_info", {}) if cv else {}
        candidate_name = (personal.get("name") or "Candidate").replace(" ", "_")

        job_result = await db.execute(select(Job).where(Job.id == application.job_id))
        job = job_result.scalar_one_or_none()
        company_name = ((job.company or "Company") if job else "Company").replace(" ", "_")

        await event_bus.emit_agent_started(user_id, "doc_generator", "Generating PDF")
        pdf_path = await generate_cv_pdf({"tailored_cv": tailored_cv.tailored_data})
        pdf_filename = f"{candidate_name}_{company_name}_Tailored.pdf"

        tailored_cv.pdf_path = pdf_path
        await event_bus.emit_agent_completed(user_id, "doc_generator", "PDF ready")

    # Update application
    application.user_approved = True
    application.user_approved_at = datetime.utcnow()
    application.status = "cv_approved"

    await db.commit()
    await db.refresh(application)

    # Load HR contact
    hr_contact_data: dict = {}
    if application.hr_contact_id:
        hr_result = await db.execute(
            select(HRContact).where(HRContact.id == application.hr_contact_id)
        )
        hr = hr_result.scalar_one_or_none()
        if hr:
            hr_contact_data = {
                "name": hr.hr_name,
                "email": hr.hr_email,
                "title": hr.hr_title,
                "confidence_score": hr.confidence_score,
                "source": hr.source,
            }

    # Get user email for CC
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    user_email = user.email if user else ""

    metadata = {
        "type": "email_review",
        "application_id": app_id,
        "hr_contact": hr_contact_data,
        "email": {
            "subject": application.email_subject or "Job Application",
            "body": application.email_body or "",
            "cc": user_email,
        },
        "pdf_filename": pdf_filename,
        "pdf_path": pdf_path,
    }

    text = (
        "Your CV has been approved and the PDF has been generated! "
        "Review the email below before sending it to the hiring team."
    )

    return (text, metadata)


# ── Send Email Handler ────────────────────────────────────────────────────────

async def _handle_send_email(
    user_id: str, app_id: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Send application email via Gmail (or mock), return application_sent metadata."""
    from sqlalchemy import select
    from app.db.models import Application, Job, HRContact, UserIntegration, TailoredCV
    from app.agents.email_sender import send_via_gmail

    app_result = await db.execute(
        select(Application).where(Application.id == app_id, Application.user_id == user_id)
    )
    application = app_result.scalar_one_or_none()
    if not application:
        return ("Application not found.", None)

    job_result = await db.execute(select(Job).where(Job.id == application.job_id))
    job = job_result.scalar_one_or_none()

    # Load HR contact — re-run finder if stale/low-confidence (old LLM-fabricated records)
    from app.agents.hr_finder import find_hr_contact as _find_hr
    hr_email = ""
    hr_name = "HR Team"
    hr_record = None

    if application.hr_contact_id:
        hr_result = await db.execute(
            select(HRContact).where(HRContact.id == application.hr_contact_id)
        )
        hr_record = hr_result.scalar_one_or_none()
        if hr_record:
            hr_email = hr_record.hr_email or ""
            hr_name = hr_record.hr_name or hr_name

    # Stale check: re-run finder if email is empty OR came from LLM guess (confidence < 0.5)
    stale_sources = {"guess", "constructed", "not_found", "llm", None}
    confidence = getattr(hr_record, "confidence_score", 0) or 0
    source = getattr(hr_record, "source", None)
    needs_refresh = not hr_email or source in stale_sources or confidence < 0.5

    if needs_refresh and job:
        await event_bus.emit_agent_started(user_id, "hr_finder", f"Re-finding HR contact for {job.company}")
        fresh = await _find_hr(job.company, job.title, user_id=user_id)
        await event_bus.emit_agent_completed(user_id, "hr_finder", "HR contact lookup complete")

        if fresh.get("hr_email"):
            hr_email = fresh["hr_email"]
            hr_name = fresh.get("hr_name", hr_name)
            # Update the DB record so future sends use the fresh email
            if hr_record:
                hr_record.hr_email = hr_email
                hr_record.hr_name = hr_name
                hr_record.hr_title = fresh.get("hr_title", hr_record.hr_title)
                hr_record.confidence_score = fresh.get("confidence_score", 0)
                hr_record.source = fresh.get("source", "refreshed")
                hr_record.verified = fresh.get("verified", False)
            else:
                new_hr = HRContact(
                    job_id=application.job_id,
                    hr_name=hr_name,
                    hr_email=hr_email,
                    hr_title=fresh.get("hr_title"),
                    confidence_score=fresh.get("confidence_score"),
                    source=fresh.get("source"),
                    verified=fresh.get("verified", False),
                    additional_emails=fresh.get("all_recipients", []),
                )
                db.add(new_hr)
                await db.flush()
                application.hr_contact_id = new_hr.id
            await db.flush()
        elif hr_email:
            # Re-lookup found nothing, but we already have an email from the
            # background pre-filter (possibly low-confidence/guessed). Fall
            # through and send — better to try than to silently block.
            logger.info("hr_refresh_failed_using_existing", email=hr_email, source=source)
        else:
            # Truly no email anywhere — block and report
            job_company_str = job.company if job else "the company"
            return (
                f"No HR contact email is available for **{job_company_str}** — the search could not find one.\n\n"
                "To resolve this, add a free API key to your Railway environment variables and redeploy:\n"
                "- `APOLLO_API_KEY` — https://app.apollo.io (50 free/month)\n"
                "- `PROSPEO_API_KEY` — https://prospeo.io (150 free/month)\n\n"
                "Or enter the HR email manually by editing the email draft above and retrying.",
                None,
            )

    # Generate PDF bytes — load tailored CV data, fall back to raw parsed CV
    pdf_bytes = None
    pdf_filename = "Tailored_CV.pdf"
    tc = None

    if application.tailored_cv_id:
        tc_result = await db.execute(
            select(TailoredCV).where(TailoredCV.id == application.tailored_cv_id)
        )
        tc = tc_result.scalar_one_or_none()

    # Resolve CV data to generate PDF from
    cv_data_for_pdf = None
    if tc and tc.tailored_data:
        cv_data_for_pdf = tc.tailored_data
        logger.info("pdf_source", source="tailored_cv", tc_id=tc.id)
    else:
        # Fallback: use the user's primary parsed CV
        logger.warning("pdf_no_tailored_cv", tailored_cv_id=application.tailored_cv_id)
        from app.db.models import UserCV
        cv_result = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
        )
        raw_cv = cv_result.scalar_one_or_none()
        if raw_cv and raw_cv.parsed_data:
            cv_data_for_pdf = raw_cv.parsed_data
            logger.info("pdf_source", source="raw_cv", cv_id=raw_cv.id)

    if cv_data_for_pdf:
        try:
            from app.agents.doc_generator import generate_cv_pdf_bytes
            await event_bus.emit_agent_started(user_id, "doc_generator", "Generating PDF for email")
            pdf_bytes = await generate_cv_pdf_bytes({"tailored_cv": cv_data_for_pdf})
            logger.info("pdf_bytes_result", has_bytes=pdf_bytes is not None,
                        size=len(pdf_bytes) if pdf_bytes else 0)
            if pdf_bytes and job and job.title:
                pdf_filename = f"CV_{job.title.replace(' ', '_')[:30]}.pdf"
            await event_bus.emit_agent_completed(
                user_id, "doc_generator",
                "PDF generated" if pdf_bytes else "PDF generation failed"
            )
        except Exception as _pdf_err:
            logger.error("pdf_gen_on_send_failed", error=str(_pdf_err), exc_info=True)
    else:
        logger.warning("pdf_no_cv_data_available", app_id=app_id)

    # Try Gmail integration — only use the user's own connected Gmail
    from app.config import settings as app_settings
    gmail_tokens: dict = {}

    int_result = await db.execute(
        select(UserIntegration).where(
            UserIntegration.user_id == user_id,
            UserIntegration.service_name.in_(["google", "gmail"]),
            UserIntegration.is_active == True,
        )
    )
    integration = int_result.scalar_one_or_none()
    if integration:
        gmail_tokens = {
            "access_token": integration.access_token,
            "refresh_token": integration.refresh_token,
            "client_id": app_settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": app_settings.GOOGLE_OAUTH_CLIENT_SECRET,
        }

    sent_ok = False
    gmail_message_id = None
    is_mock = False
    send_error: str = ""

    _t_send = time.monotonic()
    if gmail_tokens:
        await event_bus.emit_agent_started(user_id, "email_sender", f"Sending email to {hr_email}")
        send_result = await send_via_gmail(
            user_tokens=gmail_tokens,
            to_email=hr_email,
            subject=application.email_subject or "Job Application",
            body=application.email_body or "",
            attachment_bytes=pdf_bytes,
            attachment_filename=pdf_filename,
        )
        sent_ok = send_result.get("status") == "sent"
        gmail_message_id = send_result.get("message_id")
        send_error = send_result.get("error", "")
        error_code = send_result.get("error_code", "")

        if not sent_ok:
            logger.warning("gmail_send_failed", error=send_error, error_code=error_code, app_id=app_id)

        await _log_execution(db, user_id, app_id, "email_sender", f"send_email:{hr_email}",
                             "success" if sent_ok else "failed",
                             int((time.monotonic() - _t_send) * 1000),
                             send_error or None)

        # ── Token revoked / invalid_grant — clear stale token and tell user ──
        if not sent_ok and error_code == "token_revoked":
            # Deactivate the stored integration so subsequent requests don't retry
            if integration:
                integration.is_active = False
                integration.access_token = None
                integration.refresh_token = None
            # Also wipe the user-level refresh token
            from app.db.models import User as _User
            _user_res = await db.execute(select(_User).where(_User.id == user_id))
            _user = _user_res.scalar_one_or_none()
            if _user:
                _user.google_refresh_token = None
                _user.google_oauth_token = None
            application.status = "send_failed"
            await db.commit()
            return (
                "**Gmail authorization has expired or been revoked.**\n\n"
                "Your Google refresh token is no longer valid. To fix this:\n\n"
                "1. Go to **Settings → Integrations** tab\n"
                "2. Click **Reconnect Gmail** and authorize access again\n"
                "3. Come back here and click **Send via Gmail** to retry\n\n"
                "**Common causes:**\n"
                "- Google password was changed\n"
                "- App access was revoked from [myaccount.google.com/permissions](https://myaccount.google.com/permissions)\n"
                "- OAuth consent screen is in **Testing** mode (tokens expire after 7 days) — "
                "publish it in [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent) to fix this permanently",
                None,
            )
    else:
        # No Gmail credentials — tell user to connect first
        await event_bus.emit_agent_completed(user_id, "email_sender", "Gmail not connected")
        return (
            "**Gmail is not connected.** I can't send the email without access to your Gmail account.\n\n"
            "Please connect your Gmail first:\n\n"
            "1. Go to **Settings** (bottom-left) → **Integrations** tab\n"
            "2. Click **Connect Gmail** and authorize access\n"
            "3. Come back here and click **Send via Gmail** again\n\n"
            "Your application email and CV are saved — nothing will be lost.",
            None,
        )

    # Update application
    if sent_ok:
        application.status = "sent"
        application.email_sent_at = datetime.utcnow()
        application.gmail_message_id = gmail_message_id
    else:
        application.status = "send_failed"

    await db.commit()
    await db.refresh(application)

    # Find next job suggestion
    from app.db.models import JobSearch
    next_job_result = await db.execute(
        select(Job)
        .join(JobSearch)
        .where(JobSearch.user_id == user_id, Job.id != application.job_id)
        .order_by(Job.match_score.desc().nulls_last())
        .limit(1)
    )
    next_job_db = next_job_result.scalar_one_or_none()
    next_job = None
    if next_job_db:
        next_job = {
            "title": next_job_db.title,
            "company": next_job_db.company,
            "match_score": next_job_db.match_score,
            "job_id": next_job_db.id,
        }

    job_title = job.title if job else "the position"
    job_company = job.company if job else "the company"

    metadata = {
        "type": "application_sent",
        "job": {"title": job_title, "company": job_company, "id": application.job_id},
        "hr_email": hr_email,
        "sent_at": str(application.email_sent_at or datetime.utcnow()),
        "mock_send": is_mock,
        "next_steps": [
            f"Monitoring {hr_email} for replies (7-day follow-up window)",
            "Check your Applications page for status updates",
        ],
        "interview_prep_available": True,
        "next_job_suggestion": next_job,
    }

    if sent_ok:
        mock_note = " *(demo mode — connect Gmail to send for real)*" if is_mock else ""
        # M16 fix: Warn user if PDF attachment failed
        pdf_note = ""
        if not pdf_bytes and cv_data_for_pdf:
            pdf_note = "\n\n**Note:** CV PDF could not be generated. The email was sent without attachment."
        elif not cv_data_for_pdf:
            pdf_note = "\n\n**Note:** No CV data was available for PDF generation. The email was sent without attachment."
        text = (
            f"Application for **{job_title}** at **{job_company}** sent to **{hr_email}**!{mock_note}{pdf_note}"
        )
    else:
        error_hint = f"\n\n**Error:** `{send_error}`" if send_error else ""
        text = (
            f"I had trouble sending the email to **{hr_email}**.{error_hint}\n\n"
            "Common fixes:\n"
            "- Make sure the **Gmail API** is enabled in your Google Cloud Console\n"
            "- Reconnect Gmail in **Settings → Data Sources** (token may have expired)\n"
            "- Verify your Google Cloud credentials (`GOOGLE_OAUTH_CLIENT_ID` / `GOOGLE_OAUTH_CLIENT_SECRET`) are correct"
        )

    await event_bus.emit_agent_completed(user_id, "email_sender", "Email sent")
    return (text, metadata)


# ── Interview Prep Intent (natural language → find job → prep) ────────────────

async def _handle_interview_prep_intent(
    user_id: str, message: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Route an interview prep request.

    Priority:
      1. Message contains a job description (from /interview slash command) —
         optionally with an [ATTACHED FILE:] block for the candidate's CV.
         Creates a temporary Job record and runs prep against it.
      2. Most recent application in DB.
      3. Most recently searched job in DB.
      4. Fallback message asking the user to search first.
    """
    from sqlalchemy import select, desc
    from app.db.models import Job, JobSearch, Application, JobSearch as JS

    # ── Parse [ATTACHED FILE:] block if present ───────────────────────────────
    attached_cv_text: Optional[str] = None
    clean_message = message
    if "[ATTACHED FILE:" in message:
        parts = message.split("[ATTACHED FILE:", 1)
        clean_message = parts[0].strip()
        attached_cv_text = parts[1].strip() if len(parts) > 1 else None
        # Strip the filename line from the top of the CV block
        if attached_cv_text:
            cv_lines = attached_cv_text.splitlines()
            # First line is "filename]", skip it
            if cv_lines and cv_lines[0].endswith("]"):
                attached_cv_text = "\n".join(cv_lines[1:]).strip()

    # ── If message has meaningful content treat it as a job description ───────
    job_description_provided = len(clean_message.strip()) > 40

    if job_description_provided:
        # Extract title + company from description via LLM
        llm = get_llm(task="supervisor_routing")
        extract_prompt = f"""Extract job title and company name from this job description.
Return ONLY JSON: {{"title": "...", "company": "..."}}
If company is not mentioned, set it to "Unknown Company".
Job Description: \"\"\"{clean_message[:800]}\"\"\""""
        try:
            resp = await llm.ainvoke(extract_prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            meta = json.loads(json_match.group()) if json_match else {}
        except Exception:
            meta = {}

        title   = (meta.get("title") or "Unknown Role").strip()
        company = (meta.get("company") or "Unknown Company").strip()

        # Create a temporary Job record so _handle_prep_interview can run
        from app.db.models import JobSearch as JobSearchModel
        search = JobSearchModel(user_id=user_id, search_query=f"interview prep for {title}", target_location="")
        db.add(search)
        await db.flush()

        job = Job(
            search_id=search.id,
            title=title,
            company=company,
            description=clean_message,
            location="",
            job_type="Full-time",
            source="manual",
            match_score=0,
        )
        db.add(job)
        await db.flush()

        return await _handle_prep_interview(
            user_id, job.id, db, override_cv_text=attached_cv_text
        )

    # ── Fall back to DB context ───────────────────────────────────────────────
    app_result = await db.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(desc(Application.created_at))
        .limit(1)
    )
    application = app_result.scalar_one_or_none()
    if application:
        return await _handle_prep_interview(user_id, application.job_id, db)

    job_result = await db.execute(
        select(Job)
        .join(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(desc(Job.created_at))
        .limit(1)
    )
    job = job_result.scalar_one_or_none()
    if job:
        return await _handle_prep_interview(user_id, job.id, db)

    return (
        "I'd love to help you prepare! Use `/interview` and paste the job description directly. "
        "You can also attach your tailored CV via the 📎 button for personalised preparation.",
        None,
    )


# ── Interview Prep Handler ────────────────────────────────────────────────────

async def _handle_prep_interview(
    user_id: str, job_id: str, db: AsyncSession,
    override_cv_text: Optional[str] = None,
) -> Tuple[str, Optional[dict]]:
    """Generate interview prep, save to DB, return interview_ready metadata.

    override_cv_text: raw CV text passed directly from /interview command attachment.
    When provided, it takes priority over any tailored CV stored in the DB.
    """
    from sqlalchemy import select, desc
    from app.db.models import Job, InterviewPrep, TailoredCV, Application
    from app.agents.interview_prep import generate_interview_prep

    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        return ("Job not found. Please search for jobs first.", None)

    await event_bus.emit_agent_started(
        user_id, "interview_prep", f"Preparing for {job.title} at {job.company}"
    )

    # CV resolution: override text > tailored CV in DB > primary CV in DB
    tailored_cv_data = None
    application = None
    if override_cv_text:
        # Wrap the raw text so generate_interview_prep can use it
        tailored_cv_data = {"raw_text": override_cv_text, "source": "user_upload"}
    else:
        app_result = await db.execute(
            select(Application)
            .where(Application.user_id == user_id, Application.job_id == job_id)
            .order_by(desc(Application.created_at))
            .limit(1)
        )
        application = app_result.scalar_one_or_none()
        if application and application.tailored_cv_id:
            tc_result = await db.execute(
                select(TailoredCV).where(TailoredCV.id == application.tailored_cv_id)
            )
            tc = tc_result.scalar_one_or_none()
            if tc:
                tailored_cv_data = tc.tailored_data

    _t_prep = time.monotonic()
    prep_data = await generate_interview_prep(
        job_title=job.title,
        company=job.company,
        description=job.description or "",
        tailored_cv_data=tailored_cv_data,
    )
    await _log_execution(db, user_id, "prep", "interview_prep", f"prep:{job.title}@{job.company}",
                         "success", int((time.monotonic() - _t_prep) * 1000))

    # Save prep record — persist ALL generated categories
    prep_record = InterviewPrep(
        user_id=user_id,
        job_id=job_id,
        application_id=application.id if application else None,
        company_research=prep_data.get("company_research", {}),
        technical_questions=prep_data.get("technical_questions", []),
        behavioral_questions=prep_data.get("behavioral_questions", []),
        situational_questions=prep_data.get("situational_questions", []),
        salary_research=prep_data.get("salary_research", {}),
        tips=prep_data.get("tips", []),
        questions_to_ask=prep_data.get("questions_to_ask", []),
        system_design_questions=prep_data.get("system_design_questions", []),
        coding_challenges=prep_data.get("coding_challenges", []),
        cultural_questions=prep_data.get("cultural_questions", []),
        study_plan=prep_data.get("study_plan", {}),
        status="completed",
    )
    db.add(prep_record)
    await db.commit()
    await db.refresh(prep_record)

    tech_count = len(prep_data.get("technical_questions", []))
    behavioral_count = len(prep_data.get("behavioral_questions", []))
    situational_count = len(prep_data.get("situational_questions", []))
    sys_count = len(prep_data.get("system_design_questions", []))
    code_count = len(prep_data.get("coding_challenges", []))
    cult_count = len(prep_data.get("cultural_questions", []))

    # Build category list — only include non-empty categories
    categories = []
    if tech_count:      categories.append({"name": "Technical",     "count": tech_count,      "icon": "code"})
    if behavioral_count: categories.append({"name": "Behavioral",   "count": behavioral_count, "icon": "users"})
    if situational_count: categories.append({"name": "Situational", "count": situational_count,"icon": "file-code"})
    if sys_count:       categories.append({"name": "System Design",  "count": sys_count,        "icon": "layers"})
    if code_count:      categories.append({"name": "Coding",         "count": code_count,       "icon": "code2"})
    if cult_count:      categories.append({"name": "Cultural",       "count": cult_count,       "icon": "palette"})

    total_q = tech_count + behavioral_count + situational_count + sys_count + code_count + cult_count

    metadata = {
        "type": "interview_ready",
        "job": {"title": job.title, "company": job.company, "id": job_id},
        "categories": categories,
        "prep_id": prep_record.id,
        "salary_range": prep_data.get("salary_research", {}).get("market_range", ""),
        "questions_to_ask": prep_data.get("questions_to_ask", []),
    }

    text = (
        f"Your interview prep for **{job.title}** at **{job.company}** is ready! "
        f"I've prepared **{total_q}** questions across {len(categories)} categories — "
        f"technical, behavioral, situational, system design, coding challenges, and cultural fit. "
        f"Click **Start Mock Interview** to begin."
    )

    await event_bus.emit_agent_completed(user_id, "interview_prep", "Prep materials ready")
    return (text, metadata)


# ── CV Edit Handler ───────────────────────────────────────────────────────────

async def _handle_edit_cv(
    user_id: str, tailored_cv_id: str, json_str: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Persist user-edited CV sections to the TailoredCV record.

    When called with empty/no edits (i.e. the "Edit in Modal" button was clicked),
    returns a cv_review card with auto_open_edit=True so the frontend opens the
    edit dialog immediately.
    """
    from sqlalchemy import select
    from app.db.models import TailoredCV, UserCV

    result = await db.execute(
        select(TailoredCV).where(TailoredCV.id == tailored_cv_id, TailoredCV.user_id == user_id)
    )
    tailored_cv = result.scalar_one_or_none()
    if not tailored_cv:
        return ("Could not find the CV to save changes.", None)

    try:
        edits = json.loads(json_str) if json_str.strip() not in ("{}", "") else {}
    except Exception:
        return ("Invalid CV edit data received.", None)

    # Empty edits → open the edit modal client-side by returning cv_review metadata
    if not edits:
        td = tailored_cv.tailored_data or {}

        # Try to fetch user's personal info for contact string
        cv_result = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
        )
        user_cv = cv_result.scalar_one_or_none()
        personal = (user_cv.parsed_data or {}).get("personal_info", {}) if user_cv else {}
        contact_parts = [v for v in [
            personal.get("email", ""), personal.get("phone", ""),
            personal.get("location", ""), personal.get("linkedin", ""),
        ] if v]
        contact_str = " · ".join(contact_parts)

        skills = td.get("skills", {})
        if isinstance(skills, dict):
            all_skills = []
            for v in skills.values():
                if isinstance(v, list):
                    all_skills.extend(v)
            skills_str = ", ".join(all_skills[:20])
        else:
            skills_str = str(skills)[:200]

        return ("", {
            "type": "cv_review",
            "auto_open_edit": True,
            "tailored_cv_id": tailored_cv_id,
            "application_id": tailored_cv_id,
            "job": {"id": "", "title": "General CV", "company": "", "location": ""},
            "tailored_cv": {
                "name": personal.get("name", ""),
                "contact": contact_str,
                "summary": td.get("summary", ""),
                "experience": td.get("experience", []),
                "skills": skills_str,
                "skills_raw": td.get("skills", {}),
                "education": td.get("education", []),
                "certifications": td.get("certifications", []),
                "projects": td.get("projects", []),
            },
            "ats_score": 0,
            "match_score": 0,
            "keywords_matched": 0,
            "keywords_total": 0,
            "changes_made": [],
        })

    # Non-empty edits → merge and save
    current = tailored_cv.tailored_data or {}
    for section, value in edits.items():
        if value is not None:
            current[section] = value
    tailored_cv.tailored_data = current
    await db.commit()

    return (
        "✅ Your CV edits have been saved! Click **Approve Changes** to generate the PDF and proceed.",
        None,
    )


# ── Existing Handlers ─────────────────────────────────────────────────────────

async def _handle_cv_general_request(
    user_id: str, message: str, history: list, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Route any CV question (general or explicit analysis) to the cv_general agent.

    Returns metadata with type='cv_improvements_suggested' when the user asked
    for improvements, enabling the frontend to show an 'Apply' action button.
    """
    from sqlalchemy import select
    from app.db.models import UserCV
    from app.agents.cv_general import answer_cv_question

    cv_result = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    cv = cv_result.scalar_one_or_none()
    if not cv or not cv.parsed_data:
        return (
            "I don't see a CV on file yet. Upload your PDF or DOCX using the button in the "
            "left sidebar and I'll give you a full, personalised answer right away.",
            None,
        )

    await event_bus.emit_agent_started(user_id, "cv_parser", "Reading your CV")

    try:
        answer = await answer_cv_question(
            cv_data=cv.parsed_data,
            question=message,
            history=history,
        )
    except Exception as e:
        logger.error("cv_general_request_error", error=str(e))
        answer = (
            "I ran into a problem generating your CV analysis. Please try again — "
            "if the issue persists, re-upload your CV from the sidebar."
        )

    await event_bus.emit_agent_completed(user_id, "cv_parser", "CV answer ready")

    # Show "Apply improvements" button when the user asked for changes/improvements
    is_improvement = bool(_RE_IMPROVEMENT_REQUEST.search(message))
    metadata = {"type": "cv_improvements_suggested"} if is_improvement else None
    return (answer, metadata)


async def _apply_improvements_with_llm(cv_data: dict, conversation_context: str) -> dict:
    """Apply improvement suggestions from a conversation to the CV and return updated CV dict."""
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = get_llm(task="cv_tailor")
    cv_json = json.dumps(cv_data, indent=2)[:4500]

    system = (
        "You are an elite CV optimizer. Apply ALL improvement suggestions extracted from the "
        "conversation to the candidate's CV and return the complete updated CV as JSON.\n\n"
        "RULES:\n"
        "1. Apply every concrete improvement mentioned (rewrites, additions, removals, restructuring)\n"
        "2. Keep the EXACT same JSON structure as the input — same keys, same nesting\n"
        "3. Improve bullets with strong action verbs + quantified achievements\n"
        "4. If a rewrite was given verbatim, use that exact rewrite\n"
        "5. If the conversation says 'add X skill', add it to the skills section\n"
        "6. Return ONLY valid JSON — no explanation, no markdown fences, no commentary"
    )

    user = (
        f"CURRENT CV (JSON):\n{cv_json}\n\n"
        f"IMPROVEMENT CONVERSATION (extract and apply all suggestions):\n"
        f"{conversation_context[:3500]}\n\n"
        "Return the complete improved CV as valid JSON with the same structure."
    )

    try:
        response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        # Strip markdown fences
        if content.startswith("```"):
            for part in content.split("```"):
                candidate = part.lstrip("json").strip()
                if candidate.startswith("{"):
                    content = candidate
                    break
        if content.endswith("```"):
            content = content[:-3].strip()
        return json.loads(content)
    except Exception as e:
        logger.error("apply_improvements_llm_error", error=str(e))
        return cv_data  # Return original as safe fallback


async def _handle_apply_cv_improvements(
    user_id: str, session_id: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Apply CV improvement suggestions from recent chat history to the user's CV.

    Flow:
    1. Load user's original CV
    2. Extract recent improvement conversation from chat history
    3. Apply improvements via LLM → updated CV dict
    4. Generate PDF
    5. Save TailoredCV (job_id=None — general improvement)
    6. Return cv_improved metadata card
    """
    from sqlalchemy import select, desc
    from app.db.models import UserCV, TailoredCV, ChatMessage

    # 1. Load original CV
    cv_result = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    cv = cv_result.scalar_one_or_none()
    if not cv or not cv.parsed_data:
        return ("I couldn't find your CV. Please upload it first.", None)

    # 2. Pull recent conversation to extract improvement suggestions
    history_result = await db.execute(
        select(ChatMessage)
        .where(
            ChatMessage.user_id == user_id,
            ChatMessage.session_id == session_id,
        )
        .order_by(desc(ChatMessage.created_at))
        .limit(20)
    )
    recent_msgs = history_result.scalars().all()

    # Build conversation context: last several user+assistant messages
    # (the cv_general responses contain the suggestions)
    context_lines = []
    for msg in reversed(recent_msgs):
        if msg.content.startswith("__"):
            continue
        role = "User" if msg.role == "user" else "AI Coach"
        context_lines.append(f"{role}: {msg.content[:600]}")
    conversation_context = "\n\n".join(context_lines[-16:])  # last 8 exchanges

    if not conversation_context.strip():
        return (
            "I couldn't find any improvement suggestions in your recent conversation. "
            "Please ask me to review your CV first, then click 'Apply improvements'.",
            None,
        )

    await event_bus.emit_agent_started(user_id, "cv_tailor", "Applying improvements to your CV")

    # 3. Apply improvements with LLM
    improved_cv = await _apply_improvements_with_llm(cv.parsed_data, conversation_context)

    # 4. Generate PDF
    pdf_path = None
    pdf_bytes = None
    try:
        from app.agents.doc_generator import generate_cv_pdf
        result = await generate_cv_pdf(improved_cv)
        if isinstance(result, bytes):
            pdf_bytes = result
        elif isinstance(result, str):
            pdf_path = result
    except Exception as e:
        logger.error("cv_improvement_pdf_error", error=str(e))

    # 5. Save TailoredCV (job_id=None → general improvement)
    personal = (improved_cv.get("personal_info") or {})
    tcv = TailoredCV(
        user_id=user_id,
        original_cv_id=cv.id,
        job_id=None,
        tailored_data=improved_cv,
        pdf_path=pdf_path,
        changes_made=["General CV improvement based on AI suggestions"],
        status="completed",
    )
    db.add(tcv)
    await db.commit()
    await db.refresh(tcv)

    await event_bus.emit_agent_completed(user_id, "cv_tailor", "CV improvements applied")

    # 6. Return card metadata
    return (
        f"Done! I've applied all the suggested improvements to your CV. "
        f"{'A PDF has been generated — ' if (pdf_path or pdf_bytes) else ''}"
        "You can download it or open the editor to make further tweaks.",
        {
            "type": "cv_improved",
            "tailored_cv_id": tcv.id,
            "has_pdf": bool(pdf_path or pdf_bytes),
            "name": personal.get("name", ""),
        },
    )


async def _handle_hr_finder_standalone(
    user_id: str, message: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Standalone HR email finder invoked by /hr slash command.

    Extracts company + role from the message with a quick LLM call, then runs
    the hr_finder agent and formats results as markdown.
    """
    from app.agents.hr_finder import find_hr_contact

    await event_bus.emit_agent_started(user_id, "hr_finder", "Extracting company info from your message")

    llm = get_llm(task="supervisor_routing")
    extract_prompt = f"""Extract company name, job role, and domain from this message.
Return ONLY valid JSON: {{"company": "...", "role": "...", "domain": "..."}}
If domain not mentioned set it to null. If role not mentioned set to empty string.
Message: "{message}" """
    try:
        resp = await llm.ainvoke(extract_prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
        data = json.loads(json_match.group()) if json_match else {}
    except Exception:
        data = {}

    company = (data.get("company") or "").strip()
    role    = (data.get("role") or "").strip()
    domain  = (data.get("domain") or "").strip() or None

    if not company:
        return (
            "Please tell me the **company name** you want to reach. For example:\n"
            "> `/hr` Find HR email at Google for a Software Engineer role",
            None,
        )

    await event_bus.emit_agent_started(user_id, "hr_finder", f"Searching HR contacts at {company}")

    try:
        hr_result = await find_hr_contact(company, role, company_domain=domain)
    except Exception as exc:
        await event_bus.emit_agent_completed(user_id, "hr_finder", "Search failed")
        return (f"I couldn't search HR contacts for **{company}**: {exc}", None)

    await event_bus.emit_agent_completed(user_id, "hr_finder", f"Search complete for {company}")

    if not hr_result or not hr_result.get("hr_email"):
        d = domain or (company.lower().replace(" ", "") + ".com")
        prefixes = ["hr", "careers", "talent", "recruiting", "jobs"]
        fallbacks = "\n".join(f"- `{p}@{d}`" for p in prefixes)
        return (
            f"I couldn't find a verified HR email for **{company}** through our sources.\n\n"
            f"**Common pattern fallbacks to try:**\n{fallbacks}\n\n"
            "You can also check the company's LinkedIn page or careers site.",
            None,
        )

    lines = [f"✅ **HR contacts found for {company}**\n"]
    lines.append(f"📧 **Primary HR email:** `{hr_result['hr_email']}`")

    additional = hr_result.get("additional_emails") or []
    if additional:
        lines.append("\n**Additional contacts:**")
        for c in additional[:6]:
            email    = c.get("email", "")
            name     = c.get("full_name") or c.get("name", "")
            position = c.get("position", "")
            conf     = c.get("confidence", 0)
            label    = " — ".join(filter(None, [name, position]))
            lines.append(f"- `{email}`{f' ({label})' if label else ''} · confidence {conf}%")

    return ("\n".join(lines), None)


async def _handle_status_request(user_id: str, db: AsyncSession) -> str:
    from sqlalchemy import select, func, desc
    from app.db.models import UserCV, Job, JobSearch, Application, HRContact

    await event_bus.emit_agent_started(user_id, "supervisor", "Loading your pipeline data")

    # CV count
    cv_count = (await db.execute(
        select(func.count(UserCV.id)).where(UserCV.user_id == user_id)
    )).scalar() or 0

    # Total jobs found
    job_count_total = (await db.execute(
        select(func.count(Job.id)).join(JobSearch).where(JobSearch.user_id == user_id)
    )).scalar() or 0

    # Top jobs by match score (most relevant first)
    jobs_result = await db.execute(
        select(Job).join(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(Job.match_score.desc().nulls_last(), Job.created_at.desc())
        .limit(10)
    )
    top_jobs = jobs_result.scalars().all()

    # Applications with status breakdown
    apps_result = await db.execute(
        select(Application).where(Application.user_id == user_id)
        .order_by(Application.created_at.desc()).limit(12)
    )
    apps = apps_result.scalars().all()
    app_count = len(apps)

    status_counts: dict = {}
    for a in apps:
        status_counts[a.status] = status_counts.get(a.status, 0) + 1

    # ── Build response ─────────────────────────────────────────────────────────
    lines = [f"## 📊 Your CareerAgent Pipeline\n"]
    lines.append(
        f"**{cv_count}** CV · **{job_count_total}** jobs discovered · **{app_count}** applications filed\n"
    )

    # Top discovered jobs
    if top_jobs:
        lines.append("### 💼 Top Discovered Jobs")
        for j in top_jobs[:8]:
            hr_icon = "✅" if j.source not in ("not_found",) else "❌"
            score = f"{int(j.match_score)}%" if j.match_score else "—"
            loc = j.location or "Remote/Unspecified"
            jtype = f" · {j.job_type}" if j.job_type else ""
            lines.append(f"- **{j.title}** @ {j.company} · {loc}{jtype} · {score} match")
        if job_count_total > 8:
            lines.append(f"  *…and {job_count_total - 8} more jobs in your search history*")

    # Application breakdown
    if apps:
        lines.append("\n### 📨 Applications Breakdown")
        STATUS_LABEL = {
            "pending_approval": "⏳ Awaiting your approval",
            "cv_approved": "✅ CV approved, email not yet sent",
            "sent": "📩 Email sent to HR",
            "send_failed": "❌ Send failed",
            "draft": "📝 Draft",
        }
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            label = STATUS_LABEL.get(status, status.replace("_", " ").title())
            lines.append(f"- {label}: **{count}**")

    # Recommended next actions
    lines.append("\n### 🚀 Recommended Next Steps")
    pending = status_counts.get("pending_approval", 0)
    sent = status_counts.get("sent", 0)
    unapplied = job_count_total - app_count

    if pending:
        lines.append(f"- **{pending}** application(s) need your approval — scroll up to the CV review card and click **Approve**")
    if sent:
        lines.append(f"- **{sent}** application(s) sent — type **'prepare me for interview'** to start prep")
    if unapplied > 0:
        lines.append(f"- **{unapplied}** discovered job(s) not yet applied to — click **'Tailor CV & Apply'** on any job card")
    if job_count_total == 0:
        lines.append("- No jobs found yet — type **'find me [role] jobs in [location]'** to start")
    if cv_count == 0:
        lines.append("- Upload your CV first using the **sidebar upload button**")

    await event_bus.emit_agent_completed(user_id, "supervisor", "Pipeline status loaded")
    return "\n".join(lines)




async def _general_response(
    llm, message: str, history: list = None,
    user_id: str = None, db: AsyncSession = None,
) -> str:
    """Conversational, question-specific response — reads the question and answers it directly."""
    from langchain_core.messages import SystemMessage, HumanMessage

    # ── Load user context ──────────────────────────────────────────────────────
    profile_block = ""
    if user_id and db:
        try:
            ctx = await _load_user_context(user_id, db)
            profile_block = _format_user_context(ctx)
        except Exception as e:
            logger.warning("general_ctx_load_failed", error=str(e))

    # ── Build conversation history ─────────────────────────────────────────────
    history_lines = []
    if history:
        for m in history[-12:]:
            if m["content"].startswith("__"):
                continue
            role = "User" if m["role"] == "user" else "You"
            history_lines.append(f"{role}: {m['content'][:600]}")

    # ── System prompt: persona + context, no format constraints ───────────────
    system_content = """You are CareerAgent — a world-class AI career strategist with expert knowledge in:
• Global job markets, hiring processes, and recruiter psychology
• CV/resume writing, ATS optimisation, keyword strategy, and personal branding
• Cold outreach, networking, and HR email tactics
• Technical interview prep, system design, coding challenges, salary negotiation
• Career pivots, skill gap analysis, and industry trends

You give answers that are specific, intelligent, and directly responsive to what the user asked.
You never give the same templated answer twice. Every response is uniquely crafted for the question.
You draw on the user's real profile data when it's available and relevant."""

    if profile_block:
        system_content += f"\n\nUser's current profile and pipeline:\n{profile_block}"

    # ── User message: history + question ─────────────────────────────────────
    user_parts = []
    if history_lines:
        user_parts.append("Conversation so far:\n" + "\n".join(history_lines))
    user_parts.append(f"User: {message}")
    user_content = "\n\n".join(user_parts)

    messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    try:
        response = await llm.ainvoke(messages)
        text = response.content if hasattr(response, "content") else str(response)
        if text and text.strip():
            return text.strip()
        raise ValueError("Empty response")
    except Exception as e:
        logger.error("general_llm_messages_failed", error=str(e))
        # Fallback: plain string prompt
        try:
            plain = f"{system_content}\n\n{user_content}"
            response = await llm.ainvoke(plain)
            text = response.content if hasattr(response, "content") else str(response)
            return text.strip() if text and text.strip() else "I'm here to help — could you rephrase your question?"
        except Exception as e2:
            logger.error("general_llm_plain_failed", error=str(e2))
            return "I'm CareerAgent, your career assistant. Ask me anything about jobs, CVs, interviews, or career strategy."


# ── /email handler ────────────────────────────────────────────────────────────

async def _handle_email_compose_send(
    user_id: str,
    message: str,
    history: list,
    db: AsyncSession,
) -> Tuple[str, Optional[dict]]:
    """Compose a professional application email and present it in the EmailReviewCard.

    Flow:
      1. Parse HR email from message (regex).
      2. Parse job description from message + conversation history.
      3. If JD or HR email missing → ask user.
      4. Load user's primary CV, compose email with LLM (AIDA framework).
      5. Persist JobSearch → Job → HRContact → Application in DB.
      6. Return email_review metadata so EmailReviewCard renders for approval.
         User then clicks "Send via Gmail" → _handle_send_email() handles the actual send.
    """
    import re as _re
    from sqlalchemy import select
    from app.db.models import UserCV, JobSearch, Job, HRContact, Application, User as _User
    from app.agents.email_sender import compose_application_email

    # ── 1. Strip attached file block + extract plain text ────────────────────
    attached_content: Optional[str] = None
    clean_msg = message
    if "[ATTACHED FILE:" in message:
        parts = message.split("[ATTACHED FILE:", 1)
        clean_msg = parts[0].strip()
        block = parts[1].strip()
        if block and block.endswith("]"):
            block = block[:-1]
        lines = block.splitlines()
        if lines and lines[0].endswith("]"):
            attached_content = "\n".join(lines[1:]).strip()
        else:
            attached_content = block

    # ── 2. Extract HR email ───────────────────────────────────────────────────
    email_pattern = _re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    hr_email_match = email_pattern.search(clean_msg)
    hr_email: Optional[str] = hr_email_match.group() if hr_email_match else None

    # Also search history for an HR email if not in current message
    if not hr_email:
        for h in reversed(history):
            m = email_pattern.search(h.get("content", ""))
            if m:
                hr_email = m.group()
                break

    # ── 3. Extract job description ────────────────────────────────────────────
    jd_candidate = _re.sub(email_pattern, "", clean_msg).strip()

    jd_parts: list[str] = []
    if len(jd_candidate) > 50:
        jd_parts.append(jd_candidate)
    if attached_content and len(attached_content) > 50:
        jd_parts.append(attached_content)
    if not jd_parts:
        for h in reversed(history[-10:]):
            c = h.get("content", "")
            if h.get("role") == "user" and len(c) > 80:
                jd_parts.append(c)
                break

    job_description = "\n\n".join(jd_parts).strip()

    if not job_description:
        return (
            "I need the **job description** to write a targeted email.\n\n"
            "Please paste the full job description (from the job posting) in your next message and I'll compose the email right away.",
            None,
        )

    if not hr_email:
        return (
            "I have the job description — great!\n\n"
            "Now I need the **HR contact's email address**. Please share it and I'll draft the email for your review.",
            None,
        )

    # ── 4. Load user's primary CV ─────────────────────────────────────────────
    cv_row = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    primary_cv = cv_row.scalar_one_or_none()
    if not primary_cv:
        cv_row = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id).order_by(UserCV.created_at.desc()).limit(1)
        )
        primary_cv = cv_row.scalar_one_or_none()

    cv_data: dict = primary_cv.parsed_data or {} if primary_cv else {}
    candidate_name = cv_data.get("personal_info", {}).get("name") or "the candidate"

    # ── 5. Extract title + company from JD ───────────────────────────────────
    llm = get_llm(task="email_composition")
    extract_prompt = f"""Extract job title and company name from this job description.
Return ONLY JSON: {{"title": "...", "company": "..."}}
If company is not mentioned set it to "Unknown Company".
Job Description: \"\"\"{job_description[:800]}\"\"\""""
    try:
        resp = await llm.ainvoke(extract_prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        m = _re.search(r'\{[^{}]+\}', content, _re.DOTALL)
        meta = json.loads(m.group()) if m else {}
    except Exception:
        meta = {}

    job_title = (meta.get("title") or "the position").strip()
    company = (meta.get("company") or "the company").strip()

    # ── 6. Compose email via LLM ──────────────────────────────────────────────
    await event_bus.emit_agent_started(user_id, "email_composer", f"Writing email for {job_title} at {company}")

    user_row = await db.execute(select(_User).where(_User.id == user_id))
    user_obj = user_row.scalar_one_or_none()
    linkedin_url = (user_obj.preferences or {}).get("linkedin_url") if user_obj else None

    email_result = await compose_application_email(
        job_data={"title": job_title, "company": company, "description": job_description},
        cv_data=cv_data,
        hr_contact={"hr_name": "Hiring Manager", "email": hr_email},
        linkedin_url=linkedin_url,
    )
    subject = email_result.get("email_subject", f"Application for {job_title} – {candidate_name}")
    body = email_result.get("email_body", "")

    # ── 7. Check if a CV PDF will be available ───────────────────────────────
    pdf_filename = f"{candidate_name.replace(' ', '_')}_CV.pdf" if primary_cv else None

    # ── 8. Persist DB records: JobSearch → Job → HRContact → Application ────
    job_search = JobSearch(
        user_id=user_id,
        search_query=f"Manual email: {job_title} at {company}",
        target_role=job_title,
        status="completed",
    )
    db.add(job_search)
    await db.flush()

    job_rec = Job(
        search_id=job_search.id,
        title=job_title,
        company=company,
        description=job_description[:5000],
        source="manual",
    )
    db.add(job_rec)
    await db.flush()

    hr_record = HRContact(
        job_id=job_rec.id,
        hr_name="Hiring Manager",
        hr_email=hr_email,
        confidence_score=1.0,
        source="user_provided",
        verified=True,
    )
    db.add(hr_record)
    await db.flush()

    application = Application(
        user_id=user_id,
        job_id=job_rec.id,
        hr_contact_id=hr_record.id,
        email_subject=subject,
        email_body=body,
        status="pending_approval",
    )
    db.add(application)
    await db.commit()

    await event_bus.emit_agent_completed(user_id, "email_composer", "Email draft ready for review")

    # ── 9. Return email_review metadata — EmailReviewCard handles the rest ───
    return (
        f"✉️ Your application email for **{job_title}** at **{company}** is ready for review.\n\n"
        f"Edit the subject or body if needed, then click **Send via Gmail** to deliver it to `{hr_email}`.",
        {
            "type": "email_review",
            "application_id": application.id,
            "hr_contact": {
                "name": "Hiring Manager",
                "email": hr_email,
                "title": "HR",
            },
            "email": {
                "subject": subject,
                "body": body,
            },
            "pdf_filename": pdf_filename,
        },
    )


# ── Pipeline Planner ──────────────────────────────────────────────────────────

async def _plan_agents(llm, message: str, history: list) -> list:
    """LLM-based pipeline planner.

    Analyzes the user's message + last 20 conversation messages and returns
    an ordered list of agent names to run.
    """
    # Build full history context (up to 20 messages)
    history_block = "(no prior messages)"
    if history:
        recent = [m for m in history[-20:] if not m.get("content", "").startswith("__")]
        if recent:
            history_block = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:300]}"
                for m in recent
            )

    prompt = f"""You are the pipeline orchestrator for CareerAgent — an AI job-application assistant.
Analyze the user's message (and conversation history for context) and decide which agents to run.

AVAILABLE AGENTS:
  job_search    — Search the internet for job listings by role/location
  cv_tailor     — Tailor user's CV for a specific job description
  hr_finder     — Find HR contact email for a company/domain
  email_review  — Compose application email + show approval card before sending
  interview_prep — Generate interview Q&A, study plan, salary data
  cv_general    — General CV improvements, rewrites, ATS analysis
  status        — Show pipeline status (applications, jobs found, emails sent)
  clarify       — ONLY use when truly no actionable intent can be determined
  general       — General career advice / Q&A

CRITICAL RULES — read carefully:

RULE A: Any message about finding jobs, applying to jobs by role/location, or wanting job applications
sent → ALWAYS use ["job_search","cv_tailor","hr_finder","email_review"] (full pipeline).
This includes: "apply for X jobs in Y", "find X roles in Y", "get me Y positions in Z",
"I want to apply for [role]", "help me find [role] jobs", "apply in [country/city]", etc.

RULE B: If a FULL JOB DESCRIPTION (multiple lines / paragraphs) is pasted AND user says "apply"
→ ["cv_tailor","hr_finder","email_review"]

RULE C: If an HR email address is visible in the message AND user says "write email"/"send application"
→ ["email_review"]

RULE D: "find HR email for X company" → ["hr_finder"]
RULE E: "find HR for X AND send email" → ["hr_finder","email_review"]
RULE F: "interview prep"/"prepare for interview"/"mock interview" → ["interview_prep"]
RULE G: "tailor my CV for [job]" → ["cv_tailor"]
RULE H: "improve/fix/rewrite my CV" (no specific job) → ["cv_general"]
RULE I: "my applications"/"pipeline status"/"what have you done" → ["status"]
RULE J: General career questions → ["general"]
RULE K: Use ["clarify"] ONLY if the message is completely meaningless (e.g. random characters,
a single greeting like "hello", or truly impossible to determine any intent even with history).
NEVER use clarify when: a role, company, location, or any job-related word is present.

IMPORTANT: When the current message is short (1-5 words) or a follow-up like "any", "all",
"yes", "proceed", "whatever" — look at the CONVERSATION HISTORY to determine what pipeline
to continue. If prior messages discussed job search → run full pipeline.

Return ONLY a JSON array. No explanation. No markdown.

CONVERSATION HISTORY (last 20 messages):
{history_block}

CURRENT USER MESSAGE: "{message}"

JSON array:"""

    try:
        resp = await llm.ainvoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r'\[[\s\S]*?\]', content)
        if m:
            agents = json.loads(m.group())
            valid = {
                "job_search", "cv_tailor", "hr_finder", "email_review",
                "interview_prep", "cv_general", "status", "clarify", "general",
            }
            agents = [a for a in agents if a in valid]
            if agents:
                logger.debug("pipeline_plan", agents=agents, message=message[:80])
                return agents
    except Exception as exc:
        logger.warning("plan_agents_failed", error=str(exc))

    # Fallback: if any job-related word present → run full pipeline
    job_words = {"job", "jobs", "role", "roles", "position", "apply", "engineer",
                 "developer", "manager", "analyst", "designer", "work", "career"}
    if any(w in message.lower().split() for w in job_words):
        return ["job_search", "cv_tailor", "hr_finder", "email_review"]

    return ["general"]


# ── Pipeline Orchestrator ──────────────────────────────────────────────────────

async def _orchestrate_agents(
    user_id: str,
    session_id: str,
    message: str,
    history: list,
    agents: list,
    db: AsyncSession,
) -> tuple:
    """Execute a planned agent sequence, routing to existing handlers.

    Context flows between steps:
    - hr_finder email is injected into the email_review message
    - job_search + any other agent triggers the full auto-pipeline
    - cv_tailor + any other agent runs the apply-from-JD flow
    """
    if not agents:
        llm = get_llm(task="supervisor_routing")
        text = await _general_response(llm, message, history, user_id=user_id, db=db)
        return (text, None)

    # ── job_search present: full automated pipeline or standalone search ───────
    if "job_search" in agents:
        if len(agents) == 1:
            # Only job_search requested — show job listings card
            return await _handle_job_search_v2(user_id, session_id, message, db)
        else:
            # job_search + other agents → full auto-pipeline
            return await _handle_auto_pipeline(user_id, message, db, session_id=session_id)

    # ── cv_tailor in sequence → apply-from-JD flow ────────────────────────────
    if "cv_tailor" in agents:
        if len(agents) == 1:
            # Only tailor requested — just generate tailored CV (downloadable)
            return await _handle_cv_tailor_from_description(user_id, message, db)
        else:
            # Tailor + hr_finder + email_review (+ optionally interview_prep)
            # _handle_apply_from_jd runs tailor → HR → email (cv_review card)
            text, meta = await _handle_apply_from_jd(user_id, message, db)
            if "interview_prep" in agents:
                text += (
                    "\n\n---\n💡 Once you've approved and sent your application, "
                    "ask me **'prepare me for the interview'** and I'll build a full study plan!"
                )
            return (text, meta)

    # ── hr_finder → email_review: discover HR then compose email ──────────────
    if agents[0] == "hr_finder" and "email_review" in agents:
        hr_text, hr_meta = await _handle_hr_finder_standalone(user_id, message, db)
        # Extract the primary email from the response text
        _email_re = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
        m = _email_re.search(hr_text)
        if not m:
            # HR not found — surface the finder result as-is
            return (hr_text, hr_meta)
        found_email = m.group()
        await event_bus.emit_log_entry(
            user_id, "supervisor", "HR Found",
            f"HR email discovered: {found_email} — composing application email"
        )
        enriched_msg = f"{message}\nHR Email: {found_email}"
        email_text, email_meta = await _handle_email_compose_send(
            user_id, enriched_msg, history, db
        )
        combined = f"✅ **HR contact found:** `{found_email}`\n\n{email_text}"
        if "interview_prep" in agents:
            combined += (
                "\n\n---\n💡 After sending, ask me **'prepare me for the interview'** "
                "for a full study plan!"
            )
        return (combined, email_meta)

    # ── hr_finder only ────────────────────────────────────────────────────────
    if agents[0] == "hr_finder":
        return await _handle_hr_finder_standalone(user_id, message, db)

    # ── email_review (HR email already in message or ctx) ────────────────────
    if "email_review" in agents:
        text, meta = await _handle_email_compose_send(user_id, message, history, db)
        if "interview_prep" in agents:
            text += (
                "\n\n---\n💡 Once your email is sent, ask me **'prepare me for the interview'** "
                "for a full study plan!"
            )
        return (text, meta)

    # ── interview_prep ────────────────────────────────────────────────────────
    if "interview_prep" in agents:
        return await _handle_interview_prep_intent(user_id, message, db)

    # ── cv_general ────────────────────────────────────────────────────────────
    if "cv_general" in agents:
        return await _handle_cv_general_request(user_id, message, history, db)

    # ── status ────────────────────────────────────────────────────────────────
    if "status" in agents:
        text = await _handle_status_request(user_id, db)
        return (text, None)

    # ── clarify ───────────────────────────────────────────────────────────────
    if "clarify" in agents:
        return await _handle_clarify_request(user_id, message, history)

    # ── general / fallback ────────────────────────────────────────────────────
    llm = get_llm(task="supervisor_routing")
    text = await _general_response(llm, message, history, user_id=user_id, db=db)
    return (text, None)


# ── Clarify Handler ────────────────────────────────────────────────────────────

async def _handle_clarify_request(
    user_id: str,
    message: str,
    history: list,
) -> tuple:
    """Ask the user to clarify what they want CareerAgent to do."""
    llm = get_llm(task="supervisor_routing")

    history_block = "(new conversation)"
    if history:
        recent = [m for m in history[-6:] if not m.get("content", "").startswith("__")]
        if recent:
            history_block = "\n".join(
                f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content'][:200]}"
                for m in recent
            )

    prompt = f"""You are CareerAgent, an AI career assistant.
The user's message is unclear or too vague to act on. Write a SHORT, friendly response (3-5 lines) that:
1. Acknowledges what they said (one sentence)
2. Asks them to be more specific about what they want
3. Gives 3-4 concrete examples of what you can do

You can: find jobs, apply to a specific job posting, find HR contacts, send application emails, tailor CVs, prepare for interviews, improve CVs.

Conversation history:
{history_block}

User: "{message}"

Write the clarification (no markdown headers, keep it short and conversational):"""

    try:
        resp = await llm.ainvoke(prompt)
        text = resp.content if hasattr(resp, "content") else str(resp)
    except Exception:
        text = (
            "I'm not quite sure what you'd like me to do. Could you be more specific?\n\n"
            "Here are some things I can help with:\n"
            "- **`/search`** — Find jobs matching your role and location\n"
            "- **`/apply`** — Apply to a job (paste the job description)\n"
            "- **`/hr`** — Find HR contact emails for a company\n"
            "- **`/email`** — Write and send a job application email\n"
            "- **`/interview`** — Prepare for an upcoming interview"
        )
    return (text, None)


# ── /apply-from-JD Handler ────────────────────────────────────────────────────

async def _handle_apply_from_jd(
    user_id: str,
    message: str,
    db: AsyncSession,
) -> tuple:
    """/apply pipeline: user provides a job description, no job-search step needed.

    Creates JobSearch + Job records from the JD, then runs the full
    tailor → HR-find → email-compose pipeline and returns a cv_review card.
    The user then clicks Approve → email_review card → clicks Send via Gmail.
    """
    from sqlalchemy import select
    from app.db.models import UserCV, Job, JobSearch as _JobSearch

    if len(message.strip()) < 40:
        return (
            "Please paste the **job description** you want to apply to.\n\n"
            "Example: `/apply` then paste the full job posting below.",
            None,
        )

    # Verify CV uploaded
    cv_row = await db.execute(
        select(UserCV)
        .where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    cv = cv_row.scalar_one_or_none()
    if not cv:
        cv_row = await db.execute(
            select(UserCV)
            .where(UserCV.user_id == user_id)
            .order_by(UserCV.created_at.desc())
            .limit(1)
        )
        cv = cv_row.scalar_one_or_none()
    if not cv or not cv.parsed_data:
        return (
            "Please **upload your CV** first using the sidebar upload button, "
            "then use `/apply [job description]`.",
            None,
        )

    # Extract title + company from JD via LLM
    llm = get_llm(task="supervisor_routing")
    extract_prompt = f"""Extract job title and company name from this job description.
Return ONLY JSON: {{"title": "...", "company": "..."}}
If company is not mentioned, set it to "Unknown Company".
Job Description: \"\"\"{message[:800]}\"\"\""""
    try:
        resp = await llm.ainvoke(extract_prompt)
        raw = resp.content if hasattr(resp, "content") else str(resp)
        m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        jmeta = json.loads(m.group()) if m else {}
    except Exception:
        jmeta = {}

    title = (jmeta.get("title") or "Position").strip()
    company = (jmeta.get("company") or "Unknown Company").strip()

    # Create JobSearch + Job records so _handle_tailor_apply has a job_id
    search = _JobSearch(
        user_id=user_id,
        search_query=f"apply: {title} at {company}",
        target_role=title,
        status="completed",
    )
    db.add(search)
    await db.flush()

    job = Job(
        search_id=search.id,
        title=title,
        company=company,
        description=message,
        location="",
        job_type="Full-time",
        source="manual",
        match_score=0,
    )
    db.add(job)
    await db.flush()

    await event_bus.emit_log_entry(
        user_id, "supervisor", "/apply",
        f"Running tailor → HR → email pipeline for {title} at {company}"
    )

    # Full pipeline: tailor CV + find HR + compose email → returns cv_review card
    return await _handle_tailor_apply(user_id, job.id, db)


# ── /cover-letter handler ─────────────────────────────────────────────────────

async def _handle_cover_letter(
    user_id: str,
    message: str,
    history: list,
    db: AsyncSession,
) -> Tuple[str, Optional[dict]]:
    """Generate a tailored cover letter from a job description and the user's CV.

    Flow:
      1. Parse JD from message + [ATTACHED FILE:] block + conversation history.
      2. If JD missing → ask for it.
      3. Load primary CV (or use attached CV text).
      4. Generate cover letter with LLM.
      5. Return as formatted markdown.
    """
    from sqlalchemy import select
    from app.db.models import UserCV

    # ── 1. Parse attached file block ──────────────────────────────────────────
    attached_content: Optional[str] = None
    clean_msg = message
    if "[ATTACHED FILE:" in message:
        parts = message.split("[ATTACHED FILE:", 1)
        clean_msg = parts[0].strip()
        block = parts[1].strip()
        lines = block.splitlines()
        if lines and lines[0].endswith("]"):
            attached_content = "\n".join(lines[1:]).strip()
        else:
            attached_content = block

    # ── 2. Find job description ───────────────────────────────────────────────
    jd_parts: list[str] = []
    if len(clean_msg.strip()) > 50:
        jd_parts.append(clean_msg.strip())
    if attached_content and len(attached_content) > 50:
        jd_parts.append(attached_content)

    # Scan history if still empty
    if not jd_parts:
        for h in reversed(history[-10:]):
            c = h.get("content", "")
            if h.get("role") == "user" and len(c) > 80:
                jd_parts.append(c)
                break

    job_description = "\n\n".join(jd_parts).strip()

    if not job_description:
        return (
            "I need the **job description** to write a tailored cover letter.\n\n"
            "Please paste the full job posting and I'll craft a compelling cover letter using your CV.",
            None,
        )

    # ── 3. Load CV ────────────────────────────────────────────────────────────
    cv_row = await db.execute(
        select(UserCV).where(UserCV.user_id == user_id, UserCV.is_primary == True)
    )
    primary_cv = cv_row.scalar_one_or_none()
    if not primary_cv:
        cv_row = await db.execute(
            select(UserCV).where(UserCV.user_id == user_id).order_by(UserCV.created_at.desc()).limit(1)
        )
        primary_cv = cv_row.scalar_one_or_none()

    cv_data: dict = primary_cv.parsed_data or {} if primary_cv else {}
    personal = cv_data.get("personal_info", {})
    candidate_name = personal.get("name", "the candidate")
    candidate_email = personal.get("email", "")
    candidate_phone = personal.get("phone", "")
    candidate_location = personal.get("location", "")
    skills = cv_data.get("skills", {})
    experience = cv_data.get("experience", [])
    education = cv_data.get("education", [])
    summary = cv_data.get("summary", "")

    cv_text = f"""Name: {candidate_name}
Email: {candidate_email}
Phone: {candidate_phone}
Location: {candidate_location}
Summary: {summary[:400]}
Technical Skills: {", ".join(skills.get("technical", [])[:15])}
Soft Skills: {", ".join(skills.get("soft", [])[:8])}
Experience: {json.dumps(experience[:4], indent=2)[:800]}
Education: {json.dumps(education[:2], indent=2)[:400]}"""

    # ── 4. Extract job meta ───────────────────────────────────────────────────
    llm = get_llm(task="email_composition")
    extract_prompt = f"""Extract job title, company name, and key requirements from this job description.
Return ONLY JSON: {{"title": "...", "company": "...", "key_requirements": ["req1", "req2", "req3"]}}
Job Description: \"\"\"{job_description[:800]}\"\"\""""
    try:
        resp = await llm.ainvoke(extract_prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        import re as _re
        m = _re.search(r'\{[\s\S]+\}', content)
        meta = json.loads(m.group()) if m else {}
    except Exception:
        meta = {}

    job_title = (meta.get("title") or "the position").strip()
    company = (meta.get("company") or "the company").strip()
    key_reqs = meta.get("key_requirements", [])

    await event_bus.emit_agent_started(user_id, "cover_letter", f"Writing cover letter for {job_title} at {company}")

    # ── 5. Generate cover letter ──────────────────────────────────────────────
    from app.core.skills import get_combined_skills
    skills_context = get_combined_skills(["cover-letter-writing", "ats-optimization"])

    cover_letter_prompt = f"""You are an elite Career Communication Specialist.

{skills_context}

Write a professional, compelling cover letter for the following application.

RULES:
- 3–4 short paragraphs, maximum 350 words.
- Opening: hook with the specific role and a strong hook — no "I am writing to apply for…"
- Body: match 2–3 of the candidate's strongest achievements to the key requirements.
- Closing: clear CTA (interview request), confident — not desperate.
- Use the candidate's real name in the sign-off.
- Format with a professional header block (Name, email, phone, date) and address block (Company).
- Write in first person as the candidate.
- Do NOT include placeholder brackets like [Name] — use the real data provided.

CANDIDATE:
{cv_text}

JOB DESCRIPTION:
{job_description[:1500]}

KEY REQUIREMENTS: {", ".join(key_reqs[:5])}

Write ONLY the cover letter text — no preamble, no commentary."""

    try:
        response = await llm.ainvoke(cover_letter_prompt)
        cover_letter = response.content if hasattr(response, "content") else str(response)
        cover_letter = cover_letter.strip()
    except Exception as e:
        logger.error("cover_letter_generation_failed", error=str(e))
        return ("I ran into an issue generating your cover letter. Please try again.", None)

    return (
        f"📄 **Cover Letter — {job_title} at {company}**\n\n"
        f"---\n\n{cover_letter}\n\n"
        f"---\n\n*Copy the letter above. Use `/tailor` to also get a CV tailored for this role.*",
        None,
    )
