"""Supervisor Agent — routes user requests to specialized agents.

Returns (response_text, metadata_or_None) tuples to enable rich UI cards.
Action prefixes (__TAILOR_APPLY__:, etc.) are programmatic button-click handlers.
"""

import os
import re
import structlog
import json
import time
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.llm_router import get_llm
from app.core.event_bus import event_bus

logger = structlog.get_logger()


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
) -> Tuple[str, Optional[dict]]:
    """Process a user chat message and route to the appropriate handler.

    Returns:
        (response_text, metadata) where metadata drives rich UI card rendering.
    """
    await event_bus.emit_agent_started(user_id, "supervisor", "Analyzing your request")

    result: Tuple[str, Optional[dict]] = ("", None)
    _t0 = time.monotonic()

    try:
        # ── Action Prefix Routing (programmatic card button clicks) ──────────
        if message.startswith("__TAILOR_APPLY__:"):
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
            history = await _load_conversation_history(user_id, session_id, db, limit=25)

            # ── Natural Language Intent Routing ──────────────────────────────
            llm = get_llm(task="supervisor_routing")
            intent = await _classify_intent(llm, message, history)
            logger.info("supervisor_intent", intent=intent, message=message[:100])

            if intent == "continuation":
                result = await _handle_continuation(user_id, session_id, history, db, message=message)

            elif intent == "job_search":
                result = await _handle_job_search_v2(user_id, session_id, message, db)

            elif intent == "cv_tailor":
                result = await _handle_cv_tailor_intent(user_id, message, db)

            elif intent == "cv_upload":
                result = (
                    "I'd love to help with your CV! Use the **CV upload button** "
                    "in the sidebar to upload your PDF or DOCX file. Once uploaded, "
                    "I'll automatically parse and analyze it for you.",
                    None,
                )

            elif intent in ("cv_analysis", "cv_general"):
                result = await _handle_cv_general_request(user_id, message, history, db)

            elif intent == "interview_prep":
                result = await _handle_interview_prep_intent(user_id, message, db)

            elif intent == "status":
                text = await _handle_status_request(user_id, db)
                result = (text, None)

            elif intent == "automated_apply":
                result = await _handle_auto_pipeline(user_id, message, db, session_id=session_id)

            else:
                text = await _general_response(llm, message, history, user_id=user_id, db=db)
                result = (text, None)

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

    # 2. Explicit full-pipeline automation
    if _RE_AUTO_APPLY.search(msg_stripped):
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
  "job_type": "one of: fulltime, parttime, contract, temporary, internship, remote, hybrid — or null"
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

    # Search jobs (long-running external API calls — DB connection will be refreshed after)
    jobs = await search_jobs(
        query=search_query,
        user_id=user_id,
        location=location,
        job_type=job_type,
        limit=limit,
        cv_data=cv_parsed_data,
    )

    if not jobs:
        await event_bus.emit_agent_completed(user_id, "job_hunter", "No jobs found")
        return (
            "I couldn't find any jobs matching your criteria. "
            "Try a different search query or location.",
            None,
        )

    raw_count = len(jobs)
    await event_bus.emit_agent_progress(user_id, "job_hunter", 2, 3, f"Scoring {raw_count} jobs against your CV", "Calculating match scores")

    # ── HR email lookup: annotate ALL jobs with hr_found flag ─────────────────
    from app.agents.hr_finder import batch_find_hr_contacts
    await event_bus.emit_agent_started(
        user_id, "hr_finder",
        f"Checking HR contacts for {raw_count} jobs (concurrent lookup)"
    )
    jobs = await batch_find_hr_contacts(jobs)  # returns all, each with hr_found flag

    verified_count = sum(1 for j in jobs if j.get("hr_found"))
    await event_bus.emit_agent_completed(
        user_id, "hr_finder",
        f"HR lookup complete: {verified_count}/{raw_count} jobs have verified HR emails"
    )
    # ─────────────────────────────────────────────────────────────────────────

    # Use a fresh DB session for writes — the original session's connection may have
    # dropped during the long external API calls (job search + HR lookup can take 5+ min).
    from app.db.database import AsyncSessionLocal
    from app.db.models import HRContact as _HRContact
    saved_jobs = []
    search_id = None

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

        # Save Job records + pre-fetched HRContact records
        for job_data in jobs:
            job_record = Job(
                search_id=job_search.id,
                title=job_data.get("title", ""),
                company=job_data.get("company", ""),
                location=job_data.get("location"),
                salary_range=job_data.get("salary_range"),
                job_type=_ensure_str(job_data.get("job_type")),
                description=job_data.get("description", ""),
                requirements=job_data.get("requirements", []),
                application_url=job_data.get("application_url"),
                posted_date=job_data.get("posted_date"),
                source=job_data.get("source", "ai_generated"),
                match_score=job_data.get("match_score"),
                matching_skills=job_data.get("matching_skills", []),
                missing_skills=job_data.get("missing_skills", []),
            )
            fresh_db.add(job_record)
            await fresh_db.flush()

            # Persist the pre-fetched HR contact so tailor step can load it directly
            hr_pre = job_data.get("_hr_contact")
            if hr_pre:
                hr_rec = _HRContact(
                    job_id=job_record.id,
                    hr_name=hr_pre.get("hr_name"),
                    hr_email=hr_pre.get("hr_email"),
                    hr_title=hr_pre.get("hr_title"),
                    hr_linkedin=hr_pre.get("hr_linkedin") or "",
                    confidence_score=hr_pre.get("confidence_score"),
                    source=hr_pre.get("source"),
                    verified=hr_pre.get("verified", False),
                )
                fresh_db.add(hr_rec)
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
                "hr_found": job_data.get("hr_found", bool(hr_pre)),
            })

        await fresh_db.commit()
        await _log_execution(fresh_db, user_id, session_id, "job_hunter", f"search:{search_query}", "success",
                             int((time.monotonic() - _t) * 1000))
        await fresh_db.commit()
    verified_saved = sum(1 for j in saved_jobs if j.get("hr_found"))
    await event_bus.emit_agent_completed(user_id, "job_hunter", f"Found {len(saved_jobs)} unique jobs, {verified_saved} with verified HR contacts")
    await event_bus.emit_workflow_update(user_id, "job_hunter", ["job_hunter", "hr_finder"], ["cv_tailor", "email_sender"])

    location_str = f" in {location}" if location else ""
    hr_note = f" — **{verified_saved}** with verified HR email (apply-ready)" if verified_saved < len(saved_jobs) else ""
    text = (
        f"Found **{len(saved_jobs)} positions** matching \"{search_query}\"{location_str}.{hr_note} "
        "Jobs with a verified HR email show a **'Tailor CV & Apply'** button. "
        "Jobs without a verified HR contact show a red ✗ — you can still view them but cannot send a direct application."
    )

    return (text, {
        "type": "job_results",
        "search_id": search_id,
        "jobs": saved_jobs,
        "selected_cv_id": selected_cv_id or cv_id,   # remembered for tailor step
    })


# ── Continuation Handler ──────────────────────────────────────────────────────

_APPROVAL_WORDS = frozenset({
    "yes", "approve", "approved", "send", "send it", "proceed", "confirm",
    "ok", "okay", "go", "go ahead", "do it", "sure", "sounds good",
    "alright", "yep", "yup", "absolutely", "correct", "right",
})

def _is_explicit_approval(msg: str) -> bool:
    """Return True only when the user's message is an explicit approval/confirmation."""
    tokens = msg.lower().strip().split()
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
                if job_id:
                    await event_bus.emit_log_entry(
                        user_id, "supervisor", "Continuing Pipeline",
                        f"Moving to next job: {next_job.get('title','')} at {next_job.get('company','')}"
                    )
                    return await _handle_tailor_apply(user_id, job_id, db)
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

    # Look for recent unsent jobs
    recent_job = await db.execute(
        select(Job).join(JobSearch)
        .where(JobSearch.user_id == user_id)
        .order_by(desc(Job.created_at)).limit(1)
    )
    job = recent_job.scalar_one_or_none()
    if job:
        return await _handle_tailor_apply(user_id, job.id, db)

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
    """Full automated pipeline: search → tailor → approve → send for all found jobs."""
    llm = get_llm(task="parse_automation_query")
    prompt = f"""Extract automation parameters from: "{message}"
Return JSON: {{"count": 5, "location": "city/country or null", "query": "job role or industry"}}
Return ONLY valid JSON."""

    try:
        resp = await llm.ainvoke(prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        params = json.loads(content.strip().replace("```json", "").replace("```", ""))
    except Exception:
        params = {"count": 5, "location": None, "query": "software engineer"}

    count = min(int(params.get("count") or 5), 8)
    location = params.get("location")
    query = params.get("query") or message

    await event_bus.emit_workflow_update(user_id, "supervisor", [], ["job_hunter", "cv_tailor", "hr_finder", "email_sender"])

    # Step 1: Find jobs
    _, search_meta = await _handle_job_search_v2(user_id, session_id or "", query, db, limit=count)
    if not search_meta:
        return ("I couldn't find matching jobs. Please try a more specific search.", None)

    jobs = search_meta.get("jobs", [])
    if not jobs:
        return ("No jobs were found for that query. Try different keywords.", None)

    location_str = f" in **{location}**" if location else ""
    await event_bus.emit_log_entry(
        user_id, "supervisor", "Auto-Pipeline Started",
        f"Running full pipeline for {len(jobs)} jobs{location_str}"
    )

    results = []
    for i, job_entry in enumerate(jobs):
        job_id = job_entry["id"]
        job_title = job_entry.get("title", "Position")
        job_company = job_entry.get("company", "Company")

        await event_bus.emit_workflow_update(
            user_id, "cv_tailor",
            ["job_hunter"] + [j["id"] for j in jobs[:i]],
            [j["id"] for j in jobs[i + 1:]],
        )

        # Step 2: Tailor CV + find HR + compose email
        _, tailor_meta = await _handle_tailor_apply(user_id, job_id, db)
        if not tailor_meta or not tailor_meta.get("application_id"):
            results.append({"title": job_title, "company": job_company, "status": "tailor_failed"})
            continue

        app_id = tailor_meta["application_id"]

        # Step 3: Auto-approve + generate PDF
        await event_bus.emit_workflow_update(user_id, "doc_generator", ["job_hunter", "cv_tailor"], [])
        _, approve_meta = await _handle_approve_cv(user_id, app_id, db)
        if not approve_meta:
            results.append({"title": job_title, "company": job_company, "status": "approve_failed"})
            continue

        # Step 4: Send email
        await event_bus.emit_workflow_update(user_id, "email_sender", ["job_hunter", "cv_tailor", "doc_generator"], [])
        _, send_meta = await _handle_send_email(user_id, app_id, db)
        sent_ok = bool(send_meta)
        results.append({
            "title": job_title, "company": job_company,
            "status": "sent" if sent_ok else "send_failed",
            "ats_score": tailor_meta.get("ats_score", 0),
            "match_score": tailor_meta.get("match_score", 0),
        })

    # Build summary
    sent = [r for r in results if r["status"] == "sent"]
    failed = [r for r in results if r["status"] != "sent"]

    lines = [f"## Automated Pipeline Complete\n"]
    lines.append(f"**{len(sent)}/{len(results)} applications sent**{location_str}\n")
    for r in sent:
        lines.append(f"✅ **{r['title']}** at {r['company']} — ATS: {r.get('ats_score',0)}% | Match: {r.get('match_score',0)}%")
    for r in failed:
        lines.append(f"⚠️ **{r['title']}** at {r['company']} — {r['status'].replace('_', ' ')}")

    lines.append("\nCheck **Applications** in the sidebar for full details. "
                 "Click **'Prep Interview'** on any sent application to start preparing!")

    await event_bus.emit_workflow_update(user_id, "supervisor", ["job_hunter", "cv_tailor", "doc_generator", "email_sender"], [])

    return ("\n".join(lines), {
        "type": "job_results",
        "search_id": search_meta.get("search_id"),
        "jobs": jobs,
    })


# ── CV Tailor Intent Handler ──────────────────────────────────────────────────

async def _handle_cv_tailor_intent(
    user_id: str, message: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Handle natural language 'tailor CV' intent by finding the last-searched job."""
    from sqlalchemy import select, desc
    from app.db.models import Job, JobSearch

    llm = get_llm(task="extract_job_context")
    extract_prompt = f"""Extract company or job title from: "{message}"
Return JSON: {{"job_keyword": "company or title or null"}}
Return ONLY valid JSON."""

    keyword = None
    try:
        resp = await llm.ainvoke(extract_prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        keyword = json.loads(
            content.strip().replace("```json", "").replace("```", "")
        ).get("job_keyword")
    except Exception:
        pass

    target_job = None
    if keyword:
        job_query = (
            select(Job)
            .join(JobSearch)
            .where(JobSearch.user_id == user_id)
            .where((Job.title.ilike(f"%{keyword}%")) | (Job.company.ilike(f"%{keyword}%")))
            .order_by(desc(Job.created_at))
            .limit(1)
        )
        result = await db.execute(job_query)
        target_job = result.scalar_one_or_none()

    if not target_job:
        job_query = (
            select(Job)
            .join(JobSearch)
            .where(JobSearch.user_id == user_id)
            .order_by(desc(Job.created_at))
            .limit(1)
        )
        result = await db.execute(job_query)
        target_job = result.scalar_one_or_none()

    if not target_job:
        return (
            "I couldn't find a job in your history to tailor for. "
            "Please search for jobs first, then click **'Tailor CV & Apply'** on a job card.",
            None,
        )

    return await _handle_tailor_apply(user_id, target_job.id, db)


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
        company_domain = getattr(job, "company_domain", None)
        hr_contact = await find_hr_contact(job.company, job.title, company_domain=company_domain)

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
            confidence_score=hr_contact.get("confidence_score"),
            source=hr_contact.get("source"),
            **{k: hr_contact.get(k) for k in ("hr_linkedin", "verified")
               if hasattr(HRContact, k) and hr_contact.get(k) is not None},
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
        candidate_name = personal.get("name", "Candidate").replace(" ", "_")

        job_result = await db.execute(select(Job).where(Job.id == application.job_id))
        job = job_result.scalar_one_or_none()
        company_name = (job.company if job else "Company").replace(" ", "_")

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
        fresh = await _find_hr(job.company, job.title)
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
                )
                db.add(new_hr)
                await db.flush()
                application.hr_contact_id = new_hr.id
            await db.flush()
        else:
            # Still not found — block and report API errors
            api_errors = fresh.get("api_errors", [])
            error_detail = ("\n\n**API errors:**\n" + "\n".join(f"- `{e}`" for e in api_errors)) if api_errors else ""
            job_company_str = job.company if job else "the company"
            return (
                f"Still couldn't find a verified HR email for **{job_company_str}**. I won't send to a guessed address.{error_detail}\n\n"
                f"Add one of these free API keys to your `.env` and restart:\n"
                f"- `APOLLO_API_KEY` → https://app.apollo.io (50 free/month)\n"
                f"- `PROSPEO_API_KEY` → https://prospeo.io (150 free/month)",
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

    # Try Gmail integration — check DB (service_name="google") OR env fallback
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
    elif app_settings.GOOGLE_REFRESH_TOKEN:
        # Fall back to env-level credentials (GOOGLE_REFRESH_TOKEN in .env)
        gmail_tokens = {
            "access_token": None,
            "refresh_token": app_settings.GOOGLE_REFRESH_TOKEN,
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
                "1. Go to **Settings → Data Sources**\n"
                "2. Click **Reconnect Gmail** and authorize access again\n"
                "3. Come back here and click **Send Email** to retry\n\n"
                "**Common causes:**\n"
                "- Google password was changed\n"
                "- App access was revoked from [myaccount.google.com/permissions](https://myaccount.google.com/permissions)\n"
                "- OAuth consent screen is in **Testing** mode (tokens expire after 7 days) — "
                "publish it in [Google Cloud Console](https://console.cloud.google.com/apis/credentials/consent) to fix this permanently",
                None,
            )
    else:
        # No credentials at all — mock send
        is_mock = True
        sent_ok = True
        gmail_message_id = f"mock_{app_id[:8]}"
        await _log_execution(db, user_id, app_id, "email_sender", f"mock_send:{hr_email}",
                             "success", int((time.monotonic() - _t_send) * 1000))

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
        text = (
            f"Application for **{job_title}** at **{job_company}** sent to **{hr_email}**!{mock_note}"
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
    """Route a natural language 'interview prep' request to the actual prep handler.

    Looks for the most recent job the user applied to (or just searched for)
    and delegates to _handle_prep_interview.  Falls back to a helpful message
    if no job context is available.
    """
    from sqlalchemy import select, desc
    from app.db.models import Job, JobSearch, Application

    # 1. Prefer a job the user already applied to (most recent application)
    app_result = await db.execute(
        select(Application)
        .where(Application.user_id == user_id)
        .order_by(desc(Application.created_at))
        .limit(1)
    )
    application = app_result.scalar_one_or_none()
    if application:
        return await _handle_prep_interview(user_id, application.job_id, db)

    # 2. Fall back to the most recently searched job
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

    # 3. No job context at all
    return (
        "I'd love to help you prepare for an interview! "
        "First, **search for jobs** and apply to one — "
        "I'll then generate tailored technical questions, behavioral prep, company research, "
        "salary insights, and a full study plan for you.",
        None,
    )


# ── Interview Prep Handler ────────────────────────────────────────────────────

async def _handle_prep_interview(
    user_id: str, job_id: str, db: AsyncSession
) -> Tuple[str, Optional[dict]]:
    """Generate interview prep, save to DB, return interview_ready metadata."""
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

    # Try to load tailored CV for personalized prep
    tailored_cv_data = None
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
