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
    """Generate interview prep via 4 parallel LLM calls (each ≤90s).

    Call 1: company research + salary + tips + questions_to_ask + study_plan
    Call 2: technical (10) + behavioral (8)
    Call 3: situational (8) + cultural (6)
    Call 4: system_design (4) + coding (3)

    Splitting into 4 smaller calls prevents JSON truncation that caused
    system_design / coding / cultural / study_plan to be missing.
    """
    from app.core.llm_router import get_llm

    llm = get_llm(task="interview_prep")

    cv_context = ""
    if tailored_cv_data:
        cv_summary = json.dumps(tailored_cv_data, indent=2)[:1200]
        cv_context = f"\nCANDIDATE PROFILE (personalise answers using this):\n{cv_summary}\n"

    desc_snippet = (description or "")[:2000]

    # ── Prompt 1: Company intel + salary + tips + questions + study plan ─────
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
    "question 2 about team structure",
    "question 3 about technical challenges",
    "question 4 about success metrics",
    "question 5 about tech stack or tooling",
    "question 6 about code review process",
    "question 7 about on-call or incident response",
    "question 8 about career growth",
    "question 9 about team culture",
    "question 10 about what interviewer enjoys most",
    "question 11 about biggest challenge next 6 months",
    "question 12 about engineering vs product balance"
  ],
  "study_plan": {{
    "day_1": "Company research focus and specific actions to take",
    "day_2": "CV and STAR stories review focus and actions",
    "day_3": "Technical skills deep-dive focus and actions",
    "day_4": "System design practice focus and actions",
    "day_5": "Behavioral prep and mock answers focus",
    "day_6": "Full mock interview and iteration",
    "day_7": "Final light review, logistics, mindset prep"
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

    # ── Prompt 3: Situational + Cultural ─────────────────────────────────────
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
  ]
}}

Generate EXACTLY 8 situational_questions and EXACTLY 6 cultural_questions.
Return ONLY valid JSON."""

    # ── Prompt 4: System Design + Coding ─────────────────────────────────────
    p4 = f"""You are a world-class interview coach. Generate technical challenges for:

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}

Return ONLY valid JSON:
{{
  "system_design_questions": [
    {{
      "question": "system to design relevant to the role (adapt complexity to seniority)",
      "approach": "detailed architecture answer: components, DB schema, caching, API design, scale considerations",
      "evaluation_criteria": "what distinguishes a strong vs weak answer",
      "common_mistakes": ["mistake 1", "mistake 2", "mistake 3"]
    }}
  ],
  "coding_challenges": [
    {{
      "problem": "problem statement with concrete example input/output",
      "optimal_solution": "commented code in the most relevant language for this role",
      "time_complexity": "O(...)",
      "space_complexity": "O(...)",
      "brute_force_approach": "naive solution and why it is suboptimal",
      "edge_cases": ["edge case 1", "edge case 2", "edge case 3"]
    }}
  ]
}}

Generate EXACTLY 4 system_design_questions and EXACTLY 3 coding_challenges.
Return ONLY valid JSON."""

    logger.info("interview_prep_start", job=job_title, company=company)

    # ── Run all 4 in PARALLEL — total time = slowest single call, not sum ────
    results = await asyncio.gather(
        _call_llm(llm, p1, "p1_context"),
        _call_llm(llm, p2, "p2_tech_behavioral"),
        _call_llm(llm, p3, "p3_situational_cultural"),
        _call_llm(llm, p4, "p4_sysdesign_coding"),
        return_exceptions=True,
    )

    # gather with return_exceptions=True never raises; exceptions come back as values
    part1 = results[0] if isinstance(results[0], dict) else {}
    part2 = results[1] if isinstance(results[1], dict) else {}
    part3 = results[2] if isinstance(results[2], dict) else {}
    part4 = results[3] if isinstance(results[3], dict) else {}

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
        "cultural_questions": part3.get("cultural_questions") or [
            {
                "question": f"What excites you about {company}'s mission and how do you align with it?",
                "what_they_want": "Genuine enthusiasm and research into the company's values and direction.",
                "sample_answer": f"I've followed {company}'s journey and what stands out is the focus on impact at scale. The engineering culture of owning outcomes end-to-end resonates with how I've worked — I thrive when I can see the direct result of my work on users.",
            },
            {
                "question": "Tell me about a time you disagreed with a team decision. How did you handle it?",
                "what_they_want": "Constructive communication, respect for process, ability to advocate for ideas without creating conflict.",
                "sample_answer": "I once disagreed with a technical approach in a code review. I wrote up a concise technical doc outlining the trade-offs, shared it async, and we discussed it in a 20-minute call. The team ultimately chose a hybrid. I've learned the best ideas win when they're communicated clearly and respectfully.",
            },
            {
                "question": "How do you balance speed vs quality in your work?",
                "what_they_want": "Pragmatic thinking — they want builders who ship, not perfectionists who block.",
                "sample_answer": "My default is: ship a good-enough v1 with known trade-offs documented, then iterate. I use feature flags to reduce risk. I've found that shipping fast and learning from real usage beats internal debate about edge cases.",
            },
            {
                "question": "Describe your ideal team environment and how you contribute to it.",
                "what_they_want": "Cultural fit — do they collaborate, communicate, and contribute positively?",
                "sample_answer": "I thrive in teams with high trust and low bureaucracy. I contribute by being vocal in PRs, proactively sharing context async, and making time to onboard newer teammates. I believe good culture is built daily through small acts of generosity with knowledge.",
            },
            {
                "question": "How do you handle ambiguity in projects with unclear requirements?",
                "what_they_want": "Self-direction and structured thinking under uncertainty.",
                "sample_answer": "I start by listing assumptions and writing a one-pager on what I think we're building and why. I get early alignment with stakeholders on the key decisions, ship a low-fidelity prototype, then iterate. Ambiguity becomes a design problem once you name it.",
            },
            {
                "question": "What does work-life balance look like to you, and how do you maintain it?",
                "what_they_want": "Self-awareness and sustainability — high performers who burn out aren't assets.",
                "sample_answer": "I have non-negotiable recovery time — exercise and offline weekends. During intense sprints I protect it even more carefully. I've found that sustainable pace produces better long-term output than heroic crunch, and I try to model that for teammates.",
            },
        ],
        "system_design_questions": part4.get("system_design_questions") or [
            {
                "question": f"Design a notification delivery system for {company} at scale (email, push, SMS).",
                "approach": "Components: API gateway, message queue (Kafka/SQS), per-channel workers, retry logic with exponential backoff, user preferences DB, delivery status tracking. Use idempotency keys to prevent duplicate sends. Store notification state in a separate DB with TTL. Rate-limit per user per channel.",
                "evaluation_criteria": "Strong: Mentions queue, idempotency, retry, observability, preferences. Weak: Ignores delivery failures, no rate limiting, no deduplication.",
                "common_mistakes": [
                    "Synchronous delivery without queue — blocks and loses messages on failure",
                    "No idempotency — duplicate notifications on retry",
                    "Ignoring user unsubscribe/preference management",
                ],
            },
            {
                "question": "Design a URL shortener like bit.ly handling 100M reads/day.",
                "approach": "Write path: generate 7-char base62 ID, store in DB (original_url, short_code, created_at, user_id). Read path: check Redis cache first (hit rate ~90%), fallback to DB. Use consistent hashing for cache nodes. Analytics: stream click events to Kafka, batch-aggregate in data warehouse. CDN for popular links.",
                "evaluation_criteria": "Strong: Cache-first reads, hash collision handling, analytics design, expiry logic. Weak: No caching, no collision handling, single DB.",
                "common_mistakes": [
                    "Not handling hash collisions — two URLs could map to same short code",
                    "Storing analytics synchronously in the hot path — adds latency",
                    "No TTL or link expiry strategy",
                ],
            },
            {
                "question": "Design a real-time collaborative document editor (like Google Docs).",
                "approach": "Use Operational Transformation (OT) or CRDT for conflict resolution. WebSocket connections for real-time sync. Each operation is transformed against concurrent operations before applying. Store ops log for history/undo. Persist document state snapshots periodically. Use presence awareness (cursor positions) via pub/sub.",
                "evaluation_criteria": "Strong: Mentions OT/CRDT, conflict resolution, persistence strategy, offline support. Weak: Assumes lock-based approach, ignores concurrent edits.",
                "common_mistakes": [
                    "Using simple locking — kills collaboration experience",
                    "Not handling offline edits and reconnection merge",
                    "No operation log — can't implement undo/history",
                ],
            },
            {
                "question": "Design a rate limiter for an API gateway handling 50K RPS.",
                "approach": "Token bucket or sliding window counter per (user_id + endpoint). Store counters in Redis with TTL. Use Lua scripts for atomic check-and-increment. Distribute across Redis cluster. Add fallback to local in-memory rate limiting if Redis is unavailable. Return 429 with Retry-After header.",
                "evaluation_criteria": "Strong: Algorithm choice justification, Redis atomicity, distributed consistency, fallback. Weak: In-memory only (doesn't work across instances), no atomicity.",
                "common_mistakes": [
                    "Non-atomic read-increment-write — race condition under load",
                    "Fixed window algorithm — allows 2x traffic at window boundary",
                    "No graceful degradation when rate limiter itself is down",
                ],
            },
        ],
        "coding_challenges": part4.get("coding_challenges") or [
            {
                "problem": "Given an array of integers, return indices of the two numbers that add up to a target. Example: nums=[2,7,11,15], target=9 → [0,1]",
                "optimal_solution": "def two_sum(nums, target):\n    seen = {}  # value -> index\n    for i, n in enumerate(nums):\n        complement = target - n\n        if complement in seen:\n            return [seen[complement], i]\n        seen[n] = i\n    return []",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)",
                "brute_force_approach": "Nested loops checking every pair: O(n²) time, O(1) space. Too slow for large inputs.",
                "edge_cases": ["No solution exists", "Same element used twice", "Negative numbers", "Target is 0"],
            },
            {
                "problem": "Implement a function to check if a string is a valid palindrome, ignoring non-alphanumeric characters and case. Example: 'A man, a plan, a canal: Panama' → True",
                "optimal_solution": "def is_palindrome(s):\n    cleaned = [c.lower() for c in s if c.isalnum()]\n    return cleaned == cleaned[::-1]",
                "time_complexity": "O(n)",
                "space_complexity": "O(n)",
                "brute_force_approach": "Same approach — palindrome checking is inherently O(n). Two-pointer variant uses O(1) space: left/right pointers skipping non-alphanumeric chars.",
                "edge_cases": ["Empty string (True)", "Single character (True)", "All punctuation (True)", "Mixed case"],
            },
            {
                "problem": "Given a binary tree, return its level-order traversal (BFS). Example: Tree [3,9,20,null,null,15,7] → [[3],[9,20],[15,7]]",
                "optimal_solution": "from collections import deque\ndef level_order(root):\n    if not root: return []\n    result, queue = [], deque([root])\n    while queue:\n        level = []\n        for _ in range(len(queue)):\n            node = queue.popleft()\n            level.append(node.val)\n            if node.left: queue.append(node.left)\n            if node.right: queue.append(node.right)\n        result.append(level)\n    return result",
                "time_complexity": "O(n)",
                "space_complexity": "O(n) — queue holds at most one full level",
                "brute_force_approach": "Recursive DFS with level tracking works but uses call stack (O(h) space). BFS with deque is cleaner for level-order.",
                "edge_cases": ["Empty tree (return [])", "Single node", "Skewed tree (linear)", "Complete binary tree"],
            },
        ],
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
