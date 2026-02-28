"""Interview Prep Agent — 3 parallel LLM calls with explicit timeouts."""

import json
import asyncio
import structlog

logger = structlog.get_logger()

# Per-call timeout. 3 parallel calls → total wait = max of the 3, not sum.
_LLM_TIMEOUT = 90.0


def _extract_json(raw: str) -> dict:
    """Extract JSON from LLM response, handles markdown fences + minor truncation."""
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.lstrip("json").strip()
            if candidate.startswith("{"):
                text = candidate
                break
    if text.endswith("```"):
        text = text[:-3].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Walk backwards to recover truncated JSON
    for end in range(len(text), max(0, len(text) - 3000), -50):
        chunk = text[:end].rstrip().rstrip(",")
        for suffix in ["}", "}}", "}}}", "}}}}"]:
            try:
                return json.loads(chunk + suffix)
            except json.JSONDecodeError:
                continue
    raise ValueError("Cannot parse JSON")


async def _call_llm(llm, prompt: str, label: str) -> dict:
    """Invoke LLM with a hard timeout. Returns {} on any failure."""
    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=_LLM_TIMEOUT)
        content = response.content if hasattr(response, "content") else str(response)
        return _extract_json(content)
    except asyncio.TimeoutError:
        logger.error("interview_prep_timeout", label=label, timeout=_LLM_TIMEOUT)
        return {}
    except Exception as e:
        logger.error("interview_prep_error", label=label, error=str(e))
        return {}


async def generate_interview_prep(
    job_title: str, company: str, description: str, tailored_cv_data: dict = None
) -> dict:
    """Generate interview prep via 3 parallel LLM calls (each ≤90s).

    Call 1: company research + salary + tips + study plan + questions to ask
    Call 2: technical (10) + behavioral (8) questions
    Call 3: situational (8) + cultural (6) + system design (4) + coding (3)
    """
    from app.core.llm_router import get_llm

    llm = get_llm(task="interview_prep")

    cv_context = ""
    if tailored_cv_data:
        cv_summary = json.dumps(tailored_cv_data, indent=2)[:1200]
        cv_context = f"\nCANDIDATE PROFILE (personalise answers using this):\n{cv_summary}\n"

    desc_snippet = (description or "")[:2000]

    # ── Prompt 1: Company intel + salary + study essentials ──────────────────
    p1 = f"""You are a world-class interview coach. Generate intelligence for:

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}
{cv_context}

Return ONLY valid JSON — no markdown, no explanation:
{{
  "company_research": {{
    "overview": "3-4 sentences on business model, scale, market position",
    "culture": "specific values and engineering culture from JD clues",
    "recent_news": "notable launches, funding, challenges from your training data",
    "tech_stack": "inferred stack from JD keywords",
    "interview_style": "what this company is known for in interviews"
  }},
  "salary_research": {{
    "market_range": "$X – $Y for this role and level (give real numbers)",
    "negotiation_tips": [
      "Tactic 1: Use competing offer as leverage — exact script to say",
      "Tactic 2: Stay silent after making your ask — why it works",
      "Tactic 3: Reframe to total comp (equity + bonus + benefits)",
      "Tactic 4: Anchor with market data from Glassdoor/Levels.fyi",
      "Tactic 5: Ask for sign-on bonus if base is non-negotiable",
      "Tactic 6: Request time to evaluate — how to do it professionally",
      "Tactic 7: Trade base for equity if company is pre-IPO",
      "Tactic 8: Counter with a specific number, not a range"
    ],
    "counter_offer_script": "Word-for-word paragraph starting with: Thank you for the offer. Based on my research of the market...",
    "initial_ask_script": "Exact words to say when asked your salary expectation first",
    "red_flags": ["sign 1 of lowball offer", "sign 2", "sign 3", "sign 4", "sign 5"]
  }},
  "tips": [
    "tip 1 specific to {company} and this role",
    "tip 2", "tip 3", "tip 4", "tip 5",
    "tip 6", "tip 7", "tip 8", "tip 9", "tip 10"
  ],
  "questions_to_ask": [
    "smart question 1 about role clarity",
    "question 2", "question 3", "question 4",
    "question 5 about tech challenges",
    "question 6", "question 7", "question 8",
    "question 9 about growth", "question 10",
    "question 11", "question 12 about culture"
  ],
  "study_plan": {{
    "day_1": "focus + actions",
    "day_2": "focus + actions",
    "day_3": "focus + actions",
    "day_4": "focus + actions",
    "day_5": "focus + actions",
    "day_6": "focus + actions",
    "day_7": "Final prep + mindset"
  }}
}}"""

    # ── Prompt 2: Technical + Behavioral ────────────────────────────────────
    p2 = f"""You are a world-class interview coach. Generate questions for:

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}
{cv_context}

Return ONLY valid JSON:
{{
  "technical_questions": [
    {{
      "question": "specific question tied to the JD",
      "answer": "detailed model answer with code snippet if relevant, edge cases, tradeoffs",
      "difficulty": "easy|medium|hard",
      "topic": "React hooks | SQL optimization | etc.",
      "follow_up": "harder follow-up question"
    }}
  ],
  "behavioral_questions": [
    {{
      "question": "STAR behavioral question probing a competency",
      "answer": "fully written STAR answer referencing specific projects from CV if provided",
      "framework": "STAR",
      "competency": "ownership | leadership | conflict resolution | etc.",
      "why_asked": "what the interviewer is testing"
    }}
  ]
}}

Generate EXACTLY 10 technical_questions (mix easy/medium/hard covering all JD areas) and EXACTLY 8 behavioral_questions (each testing a different competency).
Return ONLY valid JSON."""

    # ── Prompt 3: Situational + Cultural + System Design + Coding ────────────
    p3 = f"""You are a world-class interview coach. Generate questions for:

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}

Return ONLY valid JSON:
{{
  "situational_questions": [
    {{
      "question": "realistic hypothetical scenario for this exact role at {company}",
      "answer": "step-by-step reasoning with decision process",
      "key_principle": "core insight the interviewer wants to see"
    }}
  ],
  "cultural_questions": [
    {{
      "question": "culture/values question specific to {company}",
      "what_they_want": "what {company} actually looks for",
      "sample_answer": "authentic answer aligned to {company} values"
    }}
  ],
  "system_design_questions": [
    {{
      "question": "system to design (adapt complexity to seniority)",
      "approach": "detailed answer: components, DB schema, caching, API design, scale",
      "evaluation_criteria": "strong vs weak answer",
      "common_mistakes": ["mistake 1", "mistake 2", "mistake 3"]
    }}
  ],
  "coding_challenges": [
    {{
      "problem": "problem statement with example input/output",
      "optimal_solution": "commented code in most relevant language",
      "time_complexity": "O(...)",
      "space_complexity": "O(...)",
      "brute_force_approach": "naive solution and why it is suboptimal",
      "edge_cases": ["edge case 1", "edge case 2", "edge case 3"]
    }}
  ]
}}

Generate EXACTLY 8 situational_questions, EXACTLY 6 cultural_questions, EXACTLY 4 system_design_questions, EXACTLY 3 coding_challenges.
Return ONLY valid JSON."""

    logger.info("interview_prep_start", job=job_title, company=company)

    # ── Run all 3 in PARALLEL — total time = slowest single call, not sum ────
    results = await asyncio.gather(
        _call_llm(llm, p1, "p1_context"),
        _call_llm(llm, p2, "p2_questions_ab"),
        _call_llm(llm, p3, "p3_questions_cd"),
        return_exceptions=True,
    )

    # gather with return_exceptions=True never raises; exceptions come back as values
    part1 = results[0] if isinstance(results[0], dict) else {}
    part2 = results[1] if isinstance(results[1], dict) else {}
    part3 = results[2] if isinstance(results[2], dict) else {}

    merged = {
        "company_research": part1.get("company_research") or {
            "overview": f"Research {company} thoroughly. Check their engineering blog, Glassdoor reviews, and recent press releases.",
            "culture": "Review the JD for values clues. Look for words like ownership, impact, growth, collaboration.",
            "recent_news": f"Search '{company} engineering blog' and '{company} news 2025' before your interview.",
            "tech_stack": "Infer from the JD keywords — list every technology mentioned and prepare depth on each.",
            "interview_style": "Research on Glassdoor and Blind for interview reports from candidates.",
        },
        "salary_research": part1.get("salary_research") or {
            "market_range": "Research on Glassdoor, Levels.fyi, and LinkedIn Salary for this exact role.",
            "negotiation_tips": [
                "Never give the first number — ask what their budget range is.",
                "Always counter, even on your dream job — they expect it.",
                "Research Levels.fyi and cite the data: 'Based on market data for this level...'",
                "Negotiate total comp: base + equity + bonus + benefits together.",
                "If base is fixed, negotiate sign-on bonus as a bridge.",
                "Get any verbal offer in writing before negotiating further.",
                "Take 24-48 hours to 'review with family' — it signals you have other options.",
                "If they push for a number, give a range where your target is the bottom.",
            ],
            "counter_offer_script": "Thank you for the offer — I'm genuinely excited about this opportunity. Based on my research of the market and the scope of this role, I was expecting something closer to [X]. Is there flexibility to get there?",
            "initial_ask_script": "I'd prefer to understand the full scope and responsibilities before discussing compensation. Could you share the budgeted range for this role?",
            "red_flags": [
                "They rush you to accept without giving time to review.",
                "The offer is below the range they posted in the job ad.",
                "They say 'we don't negotiate' — almost all companies do.",
                "Equity grant is below industry standard for your level.",
                "They can't explain how bonuses are calculated.",
            ],
        },
        "tips": part1.get("tips") or [
            f"Research {company}'s recent product announcements and engineering blog posts — reference them in answers.",
            "Prepare 3-5 STAR stories that can flex across multiple questions.",
            "Have a crisp 2-minute 'tell me about yourself' that ends with why THIS role.",
            "Ask clarifying questions before answering — shows structured thinking.",
            "For coding: think out loud, state assumptions, then code.",
            "For system design: start with requirements clarification, then high-level, then deep-dive.",
            "Send a personalised thank-you email within 1 hour of each interview.",
            "Research your interviewers on LinkedIn — reference their work if relevant.",
            "Prepare questions for each round — tailor to the interviewer's role.",
            "Practice your answers out loud, not just in your head.",
        ],
        "questions_to_ask": part1.get("questions_to_ask") or [
            "What does success look like for this role in the first 90 days?",
            "What are the biggest technical challenges the team is facing right now?",
            "How does the team handle on-call and incident response?",
            "What does the code review process look like?",
            "How are technical decisions made — top-down or bottom-up?",
            "What does the career growth path look like for this role?",
            "How much time does the team get for technical debt vs new features?",
            "What's the biggest lesson the team has learned in the past year?",
            "How do you measure engineering excellence here?",
            "What made you personally choose to join this company?",
            "What's the team's biggest challenge in the next 6 months?",
            "How does the company handle disagreements between engineering and product?",
        ],
        "study_plan": part1.get("study_plan") or {
            "day_1": f"Company research: read {company}'s engineering blog, Glassdoor reviews, recent news. Write 5 things that excite you about working there.",
            "day_2": "Review your CV line by line. For each bullet, prepare a STAR story with metrics. Identify your top 5 achievement stories.",
            "day_3": "Technical deep-dive: review every technology listed in the JD. Solve 3-5 LeetCode problems in the most relevant language.",
            "day_4": "System design practice: design 2 systems from scratch (e.g., URL shortener, notification service). Focus on trade-offs.",
            "day_5": "Behavioral prep: record yourself answering 10 behavioral questions. Watch back and refine.",
            "day_6": "Mock interview: get a friend or use Pramp/interviewing.io for a full mock session. Review and iterate.",
            "day_7": "Final prep: light review of your notes, prepare your questions to ask, pick your outfit, sleep by 10pm.",
        },
        "technical_questions": part2.get("technical_questions") or [],
        "behavioral_questions": part2.get("behavioral_questions") or [],
        "situational_questions": part3.get("situational_questions") or [],
        "cultural_questions": part3.get("cultural_questions") or [],
        "system_design_questions": part3.get("system_design_questions") or [],
        "coding_challenges": part3.get("coding_challenges") or [],
    }

    total_q = sum(len(merged.get(k, [])) for k in [
        "technical_questions", "behavioral_questions", "situational_questions",
        "cultural_questions", "system_design_questions", "coding_challenges",
    ])
    logger.info("interview_prep_done", total_questions=total_q, company=company)
    return merged


async def chat_with_coach(
    prep_data: dict, job_title: str, company: str, message: str, history: list[dict]
) -> str:
    from app.core.llm_router import get_llm
    llm = get_llm(task="interview_prep")

    history_text = "".join(
        f"{'You' if m['role']=='user' else 'Coach'}: {m['content']}\n"
        for m in history[-10:]
    )
    context_summary = (
        f"Role: {job_title} at {company}\n"
        f"Technical areas: {', '.join(q.get('topic','') for q in prep_data.get('technical_questions',[])[:5])}\n"
        f"Company style: {prep_data.get('company_research',{}).get('interview_style','Not specified')}"
    )

    prompt = f"""You are an elite interview coach for {job_title} at {company}.

CONTEXT:
{context_summary}

CONVERSATION:
{history_text}

CANDIDATE: {message}

If they practice an answer: score 1-10, strengths, weaknesses, improved version.
If concept question: explain with role-relevant examples.
If they want more questions: generate 3 hard ones on that topic specific to {company}.
If strategy: give tactical advice based on {company}'s interview style.
Be brutally honest. End with one concrete next action."""

    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=60.0)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as e:
        logger.error("coach_error", error=str(e))
        return "I'm having trouble connecting right now. Please try again in a moment."


async def ai_rewrite_cv_section(section: str, content: str, instruction: str, job_context: dict) -> str:
    from app.core.llm_router import get_llm
    llm = get_llm(task="cv_tailor")
    section_guidance = {
        "summary": "professional summary (3-4 sentences, title + years + value proposition)",
        "experience_bullet": "achievement bullet (X-Y-Z: accomplished [X] measured by [Y] by doing [Z])",
        "skills": "skills section (comma-separated, prioritised by role relevance)",
        "cover_letter": "cover letter (hook + 2 achievements matching JD + clear CTA, 3 paragraphs)",
    }
    prompt = f"""Rewrite this {section_guidance.get(section, section)} based on instruction.

ROLE: {job_context.get('title','')} at {job_context.get('company','')}
JD SNIPPET: {str(job_context.get('description',''))[:400]}

CURRENT:
{content}

INSTRUCTION: {instruction}

Rules: specific, quantified, strong verbs, match JD keywords, no clichés.
Return ONLY the rewritten content."""
    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=60.0)
        return (response.content if hasattr(response, "content") else str(response)).strip()
    except Exception as e:
        logger.error("cv_rewrite_error", error=str(e))
        return content


async def ai_rewrite_email(email_subject: str, email_body: str, instruction: str, job_context: dict) -> dict:
    from app.core.llm_router import get_llm
    llm = get_llm(task="email_sender")
    prompt = f"""Rewrite this job application email based on the instruction.

ROLE: {job_context.get('title','')} at {job_context.get('company','')}
SUBJECT: {email_subject}
BODY: {email_body}
INSTRUCTION: {instruction}

Rules: AIDA framework, professional, subject <60 chars, body 3 short paragraphs, clear CTA.
Return ONLY valid JSON: {{"subject": "...", "body": "..."}}"""
    try:
        response = await asyncio.wait_for(llm.ainvoke(prompt), timeout=60.0)
        content = response.content if hasattr(response, "content") else str(response)
        return _extract_json(content)
    except Exception as e:
        logger.error("email_rewrite_error", error=str(e))
        return {"subject": email_subject, "body": email_body}
