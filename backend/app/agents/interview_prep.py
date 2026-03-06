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
    # Strip markdown code fences
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part.lstrip("json").lstrip("JSON").strip()
            if candidate.startswith("{"):
                text = candidate
                break
    if text.endswith("```"):
        text = text[:-3].strip()
    # Strip leading non-JSON text (e.g. "Here is the JSON:\n{...")
    brace_idx = text.find("{")
    if brace_idx > 0:
        text = text[brace_idx:]
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
    p2 = f"""You are a senior FAANG/MIT-caliber interview coach who designs questions for top-tier companies (Google L5+, Meta E5+, Amazon SDE3, Apple ICT4, Stripe, Jane Street).

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}
{cv_context}

CRITICAL RULES for question quality:
- Every question MUST be directly derived from the JD technologies, not generic CS trivia
- Technical questions must test deep understanding, not textbook definitions — ask "why" and "what happens when", not "what is"
- Include production-scale failure scenarios: "Your service is returning 5% stale reads — walk me through debugging this"
- Hard questions should require synthesizing multiple concepts (e.g. concurrency + caching + consistency)
- Behavioral answers must include specific numbers, timelines, and outcomes — not vague stories
- Follow-ups should be adversarial: "Now what if the data doesn't fit in memory?" or "What breaks at 10x scale?"

Return ONLY valid JSON:
{{
  "technical_questions": [
    {{
      "question": "deep, specific question tied to the JD — not a definition, but a scenario that tests real understanding",
      "answer": "detailed model answer covering the WHY, tradeoffs, edge cases, and production gotchas. Include code if relevant.",
      "difficulty": "easy|medium|hard",
      "topic": "specific tech from the JD",
      "follow_up": "adversarial follow-up that raises the complexity (scale, failure, constraint change)"
    }}
  ],
  "behavioral_questions": [
    {{
      "question": "probing behavioral question that cannot be answered with a rehearsed generic story",
      "answer": "STAR answer with specific metrics, timeline, team size, and quantified outcome",
      "framework": "STAR",
      "competency": "ownership | leadership | conflict resolution | technical judgment | influence without authority | ambiguity | trade-off decisions | cross-team collaboration",
      "why_asked": "what the interviewer is really evaluating and what a weak vs strong answer looks like"
    }}
  ]
}}

Generate EXACTLY 10 technical_questions:
- 2 easy (fundamentals that MUST still connect to the JD stack)
- 4 medium (multi-concept scenarios, debugging, design tradeoffs)
- 4 hard (production failures, scale problems, adversarial constraints)

Generate EXACTLY 8 behavioral_questions (each probing a DIFFERENT competency — no repeats).
Return ONLY valid JSON."""

    # ── Prompt 3: Situational + Cultural ─────────────────────────────────────
    p3 = f"""You are a senior FAANG/MIT-caliber interview coach.

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}

CRITICAL RULES:
- Situational questions must present realistic, high-stakes dilemmas with NO obvious right answer — the interviewer is testing judgment and reasoning process, not memorized answers
- Include scenarios involving: deadline pressure vs quality, conflicting stakeholder demands, ethical gray areas, technical debt vs feature velocity, handling a team member's underperformance
- Cultural questions must reflect {company}'s ACTUAL values (infer from JD language) — not generic "tell me about teamwork"
- Sample answers must demonstrate self-awareness, nuance, and willingness to make hard trade-offs

Return ONLY valid JSON:
{{
  "situational_questions": [
    {{
      "question": "high-stakes scenario with competing priorities, no clear right answer, specific to this role at {company}",
      "answer": "structured reasoning: acknowledge the tension, state your framework for deciding, explain the trade-off you'd make and why, describe how you'd mitigate the downside",
      "key_principle": "the decision-making principle the interviewer wants to see demonstrated"
    }}
  ],
  "cultural_questions": [
    {{
      "question": "culture/values question specific to {company}'s actual values (inferred from JD)",
      "what_they_want": "the specific signal {company} is looking for — what separates a strong vs weak answer",
      "sample_answer": "authentic answer showing self-awareness and alignment, with a concrete example"
    }}
  ]
}}

Generate EXACTLY 8 situational_questions and EXACTLY 6 cultural_questions.
Return ONLY valid JSON."""

    # ── Prompt 4: System Design + Coding ─────────────────────────────────────
    p4 = f"""You are a senior FAANG/MIT-caliber interview coach who designs challenges for Google, Meta, Stripe, and Jane Street level interviews.

ROLE: {job_title} at {company}
JOB DESC: {desc_snippet}

CRITICAL RULES:
- System design questions must be RELEVANT to what {company} actually builds (infer from JD) — not random textbook systems
- Include scale numbers (QPS, data volume, latency requirements) in the problem statement
- Coding challenges must range from medium to hard LeetCode difficulty — NO easy problems like Two Sum or palindrome check
- Each coding problem must require algorithmic insight (not just API knowledge): dynamic programming, graph algorithms, sliding window, monotonic stack, union-find, or similar
- Solutions must be in the most relevant language for this role based on the JD
- Include optimal AND suboptimal approaches with clear Big-O comparison

Return ONLY valid JSON:
{{
  "system_design_questions": [
    {{
      "question": "system relevant to {company}'s domain, with specific scale numbers (e.g. '10M DAU, 50K writes/sec, p99 < 200ms')",
      "approach": "detailed architecture: components, data model, API design, caching strategy, consistency model, failure handling, monitoring. Include specific technology choices with justification.",
      "evaluation_criteria": "what distinguishes a strong candidate (mentions X, Y, Z) from a weak one (misses A, B, C)",
      "common_mistakes": ["mistake 1 with explanation of why it fails", "mistake 2", "mistake 3"]
    }}
  ],
  "coding_challenges": [
    {{
      "problem": "clear problem statement with concrete input/output examples. Medium-to-hard difficulty requiring algorithmic insight.",
      "optimal_solution": "fully commented code in the role's primary language with clear variable names",
      "time_complexity": "O(...) with explanation",
      "space_complexity": "O(...) with explanation",
      "brute_force_approach": "naive solution, its complexity, and exactly why it's too slow",
      "edge_cases": ["non-obvious edge case 1", "edge case 2", "edge case 3"]
    }}
  ]
}}

Generate EXACTLY 4 system_design_questions and EXACTLY 5 coding_challenges (2 medium, 2 hard, 1 very hard).
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
        "technical_questions": part2.get("technical_questions") or [
            {
                "question": f"Walk me through how you would design and implement a key feature described in this {job_title} role. What technologies would you choose and why?",
                "answer": f"I would start by breaking down the requirements from the JD, identifying the core user stories, and mapping them to a technical architecture. For a {job_title} role, I'd consider the tech stack mentioned in the JD, evaluate trade-offs between consistency and availability, and propose an iterative implementation plan with clear milestones.",
                "difficulty": "medium",
                "topic": "System Architecture & Design",
                "follow_up": "What would you change if the system needed to handle 100x the expected traffic?"
            },
            {
                "question": f"Describe a production debugging scenario relevant to the {job_title} stack. A critical service is experiencing intermittent 500 errors under load — walk me through your debugging process.",
                "answer": "First, I'd check monitoring dashboards for error rate patterns (time-based, endpoint-specific). Then examine logs for stack traces, check resource utilization (CPU, memory, connections). I'd look at recent deployments, check database query performance, and verify external service health. I'd use distributed tracing to identify the bottleneck, then apply targeted fixes with canary deployment.",
                "difficulty": "hard",
                "topic": "Production Debugging",
                "follow_up": "The issue only happens during peak hours and disappears when you add more instances. What's your hypothesis?"
            },
            {
                "question": "Explain the trade-offs between SQL and NoSQL databases. When would you choose one over the other for a new service?",
                "answer": "SQL databases (PostgreSQL, MySQL) excel at complex queries, ACID transactions, and structured data with relationships. NoSQL (MongoDB, DynamoDB, Redis) excels at horizontal scaling, flexible schemas, and specific access patterns. I'd choose SQL for transactional systems with complex joins, and NoSQL for high-throughput read/write with simple access patterns. Often the best approach is polyglot persistence — using both.",
                "difficulty": "easy",
                "topic": "Database Design",
                "follow_up": "Your SQL database is hitting performance limits at 10K writes/second. What are your options before migrating to NoSQL?"
            },
            {
                "question": "How do you ensure code quality and prevent regressions in a fast-moving team? Describe your testing strategy.",
                "answer": "I use a testing pyramid: unit tests (70%) for business logic, integration tests (20%) for API contracts and DB queries, and E2E tests (10%) for critical user flows. I enforce CI/CD with automated test runs, code review with at least one approval, and coverage thresholds. I also advocate for feature flags to decouple deployment from release.",
                "difficulty": "easy",
                "topic": "Testing & CI/CD",
                "follow_up": "A critical bug shipped to production despite passing all tests. How do you prevent this class of bug in the future?"
            },
            {
                "question": "Describe how you would implement authentication and authorization for a multi-tenant SaaS application.",
                "answer": "I'd use JWT tokens with short expiry for authentication, refresh tokens stored securely (httpOnly cookies). For authorization, implement RBAC with tenant isolation at the database level (row-level security or tenant_id foreign keys). Use middleware to validate tokens, extract tenant context, and enforce permissions. Add rate limiting per tenant and audit logging for sensitive operations.",
                "difficulty": "medium",
                "topic": "Security & Auth",
                "follow_up": "A customer reports they can see another tenant's data. How do you investigate and fix this?"
            },
            {
                "question": "You need to process 1 million records from an external API daily. Design the data pipeline.",
                "answer": "I'd use a scheduled job (cron/Airflow) to paginate through the API with rate limiting. Process records in batches (1000 at a time) using async workers. Store raw data in a staging table, validate and transform, then upsert into the production table. Add idempotency keys to handle restarts. Monitor with alerts on record counts, error rates, and processing duration.",
                "difficulty": "medium",
                "topic": "Data Engineering",
                "follow_up": "The API starts returning inconsistent data mid-pipeline. How do you handle partial failures?"
            },
            {
                "question": "Explain how you would optimize a slow API endpoint that currently takes 5 seconds to respond.",
                "answer": "First, profile to identify the bottleneck: database queries (add indexes, optimize N+1), external API calls (parallelize with asyncio/Promise.all), computation (cache results in Redis). Add database query logging, use EXPLAIN ANALYZE. Consider pagination if returning large datasets. Add response caching with appropriate TTL. Measure before and after each optimization.",
                "difficulty": "medium",
                "topic": "Performance Optimization",
                "follow_up": "After optimization it's down to 200ms, but P99 is still 3 seconds. What's causing the tail latency?"
            },
            {
                "question": f"How would you handle a situation where you need to make a breaking API change that affects multiple downstream consumers?",
                "answer": "I'd use API versioning (URL path or header-based). Deploy the new version alongside the old one. Communicate the deprecation timeline to consumers. Provide a migration guide and SDK updates. Monitor old version usage and set a sunset date. During transition, both versions run simultaneously. Use feature flags to gradually shift traffic.",
                "difficulty": "hard",
                "topic": "API Design & Versioning",
                "follow_up": "Two major consumers refuse to migrate before your deadline. How do you handle this?"
            },
            {
                "question": "Describe the CAP theorem and how it applies to designing a distributed system for this role.",
                "answer": "CAP states a distributed system can only guarantee two of: Consistency (all nodes see the same data), Availability (every request gets a response), Partition tolerance (system works despite network splits). In practice, partitions happen, so you choose CP (strong consistency, may reject requests) or AP (always available, may serve stale data). Most modern systems use eventual consistency with conflict resolution.",
                "difficulty": "hard",
                "topic": "Distributed Systems",
                "follow_up": "Your system chose AP but a customer complains about stale reads causing financial discrepancies. How do you solve this without switching to CP?"
            },
            {
                "question": "You inherit a legacy codebase with no tests, poor documentation, and tight deadlines. What's your strategy?",
                "answer": "First, understand the critical paths by reading logs and monitoring. Add characterization tests around the most critical/risky code. Introduce a 'boy scout rule' — improve any code you touch. Set up CI/CD if missing. Document architectural decisions as you discover them. Prioritize refactoring by risk and frequency of change. Never do a big-bang rewrite — strangle the monolith incrementally.",
                "difficulty": "hard",
                "topic": "Legacy Code & Refactoring",
                "follow_up": "Management wants a full rewrite in 3 months. How do you push back constructively?"
            },
        ],
        "behavioral_questions": part2.get("behavioral_questions") or [
            {
                "question": "Tell me about a time you had to make a critical technical decision under pressure with incomplete information. What was the outcome?",
                "answer": "In my previous role, we had a production outage affecting 10K users. I had to decide between a quick rollback (losing 2 hours of user data) or a forward fix (risky, could take 1-3 hours). I chose the forward fix because the data loss would violate our SLA. I isolated the root cause in 45 minutes, deployed a targeted fix, and we were back to normal in 1 hour. I then led a blameless postmortem and we added circuit breakers to prevent recurrence.",
                "framework": "STAR",
                "competency": "technical judgment",
                "why_asked": "Tests decision-making under pressure. Strong answers show structured reasoning and calculated risk-taking. Weak answers show either reckless speed or analysis paralysis."
            },
            {
                "question": "Describe a situation where you disagreed with a senior engineer or manager on a technical approach. How did you handle it?",
                "answer": "My tech lead wanted to use a microservices architecture for a new feature. I believed a modular monolith was better given our 4-person team. I wrote a one-page trade-off analysis comparing both approaches on 5 criteria: development speed, operational complexity, team size, deployment frequency, and scaling needs. After reviewing it together, we agreed on the modular monolith with clear service boundaries for future extraction. The feature shipped 3 weeks ahead of schedule.",
                "framework": "STAR",
                "competency": "influence without authority",
                "why_asked": "Tests ability to advocate for ideas respectfully with evidence. Strong answers show data-driven persuasion. Weak answers show either giving in immediately or creating conflict."
            },
            {
                "question": "Tell me about a project where the requirements changed significantly mid-development. How did you adapt?",
                "answer": "We were 60% through building a batch processing system when the business pivoted to needing real-time processing. I re-scoped the project: identified which components could be reused (data models, validation logic — about 40% of the work), proposed a streaming architecture using the same core transforms, and negotiated a 2-week extension instead of the 6 weeks a full restart would need. We delivered on the revised timeline and the real-time system processed 50K events/minute.",
                "framework": "STAR",
                "competency": "ambiguity",
                "why_asked": "Tests adaptability and pragmatism. Strong answers show reuse of existing work and proactive re-planning. Weak answers show frustration or starting over from scratch."
            },
            {
                "question": "Give an example of when you identified and fixed a systemic problem that others had been working around.",
                "answer": "Our team spent 30 minutes each Monday manually reconciling deployment configs across 3 environments. No one had flagged it because 'it's always been that way.' I built a config-as-code pipeline with environment variable injection and automated drift detection. Setup took 2 days. It eliminated 26 person-hours/month of manual work and prevented 3 config-related incidents in the first quarter.",
                "framework": "STAR",
                "competency": "ownership",
                "why_asked": "Tests proactive problem-solving and initiative. Strong answers quantify the impact. Weak answers describe fixing only their own problems."
            },
            {
                "question": "Describe a time you had to collaborate with a difficult team member or stakeholder to deliver a project.",
                "answer": "A product manager kept changing requirements mid-sprint, causing rework. Instead of escalating, I proposed a structured process: a brief requirements lock 2 days before sprint start, with a change request process for mid-sprint changes that included impact assessment. I framed it as helping them get better estimates and fewer surprises. They agreed, and our sprint completion rate went from 60% to 90% over 3 sprints.",
                "framework": "STAR",
                "competency": "cross-team collaboration",
                "why_asked": "Tests interpersonal skills and process thinking. Strong answers show empathy and systemic solutions. Weak answers blame the other person."
            },
            {
                "question": "Tell me about a time you failed or made a significant mistake at work. What did you learn?",
                "answer": "I deployed a database migration without testing the rollback procedure. The migration had a bug that corrupted an index, and the rollback script didn't account for the partial state. We had 2 hours of degraded performance. I learned three things: always test rollback scripts in staging, use blue-green deployments for risky migrations, and add pre-deployment checklists. I documented these as team standards and we haven't had a migration incident since.",
                "framework": "STAR",
                "competency": "leadership",
                "why_asked": "Tests self-awareness and growth mindset. Strong answers show specific lessons and systemic improvements. Weak answers minimize the failure or blame external factors."
            },
            {
                "question": "How do you prioritize when you have multiple urgent requests from different stakeholders simultaneously?",
                "answer": "I use an impact-urgency matrix. First, I assess true urgency (SLA breach? revenue impact? can it wait 24h?). Then I communicate transparently: 'I can do A today and B tomorrow, or both by Wednesday at 80% quality. Which do you prefer?' I've found that most 'urgent' requests can wait 24 hours when you surface the trade-offs explicitly. In my last role, this approach reduced my context-switching by 40% and improved my delivery consistency.",
                "framework": "STAR",
                "competency": "trade-off decisions",
                "why_asked": "Tests prioritization and communication skills. Strong answers show a framework and transparent communication. Weak answers say 'I just work harder.'"
            },
            {
                "question": "Describe a time you mentored someone or helped a team member grow technically.",
                "answer": "A junior developer was struggling with code reviews — their PRs would go through 4-5 revision cycles. Instead of just fixing their code, I set up weekly 30-minute pairing sessions where we'd review their PR together before submission. I taught them to self-review using a checklist I created. After 6 weeks, their first-pass approval rate went from 20% to 75%, and they started helping other juniors with the same checklist.",
                "framework": "STAR",
                "competency": "conflict resolution",
                "why_asked": "Tests ability to invest in others and multiply team output. Strong answers show patience, systematic teaching, and measurable improvement. Weak answers describe just answering questions."
            },
        ],
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
                "problem": "Given an array of integers and a window size k, return the maximum value in each sliding window. Example: nums=[1,3,-1,-3,5,3,6,7], k=3 → [3,3,5,5,6,7]",
                "optimal_solution": "from collections import deque\ndef max_sliding_window(nums, k):\n    dq = deque()  # stores indices, front is always max\n    result = []\n    for i, n in enumerate(nums):\n        # Remove indices outside window\n        while dq and dq[0] < i - k + 1:\n            dq.popleft()\n        # Remove smaller elements from back\n        while dq and nums[dq[-1]] < n:\n            dq.pop()\n        dq.append(i)\n        if i >= k - 1:\n            result.append(nums[dq[0]])\n    return result",
                "time_complexity": "O(n) — each element is pushed and popped at most once",
                "space_complexity": "O(k) for the deque",
                "brute_force_approach": "For each window position, scan all k elements to find max: O(n*k). Too slow when k is large.",
                "edge_cases": ["k equals array length (single window)", "All elements identical", "Strictly decreasing array", "k = 1 (return original array)"],
            },
            {
                "problem": "Given a string s, find the length of the longest substring without repeating characters. Example: 'abcabcbb' → 3 ('abc'), 'pwwkew' → 3 ('wke')",
                "optimal_solution": "def length_of_longest_substring(s):\n    char_index = {}  # char -> last seen index\n    max_len = 0\n    left = 0\n    for right, c in enumerate(s):\n        if c in char_index and char_index[c] >= left:\n            left = char_index[c] + 1\n        char_index[c] = right\n        max_len = max(max_len, right - left + 1)\n    return max_len",
                "time_complexity": "O(n) — single pass with hash map",
                "space_complexity": "O(min(n, alphabet_size))",
                "brute_force_approach": "Check every substring for duplicates: O(n³) with nested loops + set check. O(n²) with optimized inner loop. Both too slow for n > 10⁴.",
                "edge_cases": ["Empty string → 0", "All unique characters", "All same character → 1", "Unicode/special characters"],
            },
            {
                "problem": "Implement LRU Cache with O(1) get and put operations. get(key) returns value or -1. put(key, value) inserts/updates and evicts least recently used if at capacity. Example: capacity=2, put(1,1), put(2,2), get(1)→1, put(3,3), get(2)→-1 (evicted)",
                "optimal_solution": "class Node:\n    def __init__(self, k=0, v=0):\n        self.key, self.val = k, v\n        self.prev = self.next = None\n\nclass LRUCache:\n    def __init__(self, capacity):\n        self.cap = capacity\n        self.cache = {}  # key -> Node\n        self.head, self.tail = Node(), Node()\n        self.head.next, self.tail.prev = self.tail, self.head\n\n    def _remove(self, node):\n        node.prev.next, node.next.prev = node.next, node.prev\n\n    def _add_front(self, node):\n        node.next, node.prev = self.head.next, self.head\n        self.head.next.prev = node\n        self.head.next = node\n\n    def get(self, key):\n        if key not in self.cache: return -1\n        node = self.cache[key]\n        self._remove(node)\n        self._add_front(node)\n        return node.val\n\n    def put(self, key, value):\n        if key in self.cache:\n            self._remove(self.cache[key])\n        node = Node(key, value)\n        self._add_front(node)\n        self.cache[key] = node\n        if len(self.cache) > self.cap:\n            lru = self.tail.prev\n            self._remove(lru)\n            del self.cache[lru.key]",
                "time_complexity": "O(1) for both get and put",
                "space_complexity": "O(capacity) for hash map + doubly linked list",
                "brute_force_approach": "Use a list and move accessed elements to front: O(n) per get/put due to shifting. OrderedDict works but interviewers want you to implement the data structure.",
                "edge_cases": ["Capacity of 1", "Update existing key", "Get non-existent key", "Repeated puts of same key"],
            },
            {
                "problem": "Given n non-negative integers representing an elevation map where the width of each bar is 1, compute how much water it can trap after raining. Example: height=[0,1,0,2,1,0,1,3,2,1,2,1] → 6",
                "optimal_solution": "def trap(height):\n    left, right = 0, len(height) - 1\n    left_max = right_max = 0\n    water = 0\n    while left < right:\n        if height[left] < height[right]:\n            if height[left] >= left_max:\n                left_max = height[left]\n            else:\n                water += left_max - height[left]\n            left += 1\n        else:\n            if height[right] >= right_max:\n                right_max = height[right]\n            else:\n                water += right_max - height[right]\n            right -= 1\n    return water",
                "time_complexity": "O(n) — single pass with two pointers",
                "space_complexity": "O(1) — only two extra variables",
                "brute_force_approach": "For each bar, find max height to its left and right, water at that position = min(left_max, right_max) - height[i]. Two-pass prefix max arrays: O(n) time but O(n) space.",
                "edge_cases": ["Monotonically increasing (no water)", "Monotonically decreasing (no water)", "Single bar", "All same height (no water)"],
            },
            {
                "problem": "Given a list of accounts where each element is [name, email1, email2, ...], merge accounts belonging to the same person (connected by shared emails). Example: [['John','a@','b@'],['John','b@','c@'],['Mary','d@']] → [['John','a@','b@','c@'],['Mary','d@']]",
                "optimal_solution": "class UnionFind:\n    def __init__(self, n):\n        self.parent = list(range(n))\n        self.rank = [0] * n\n    def find(self, x):\n        while self.parent[x] != x:\n            self.parent[x] = self.parent[self.parent[x]]\n            x = self.parent[x]\n        return x\n    def union(self, a, b):\n        ra, rb = self.find(a), self.find(b)\n        if ra == rb: return\n        if self.rank[ra] < self.rank[rb]: ra, rb = rb, ra\n        self.parent[rb] = ra\n        if self.rank[ra] == self.rank[rb]: self.rank[ra] += 1\n\ndef accounts_merge(accounts):\n    from collections import defaultdict\n    uf = UnionFind(len(accounts))\n    email_to_id = {}\n    for i, acc in enumerate(accounts):\n        for email in acc[1:]:\n            if email in email_to_id:\n                uf.union(i, email_to_id[email])\n            email_to_id[email] = i\n    groups = defaultdict(set)\n    for email, i in email_to_id.items():\n        groups[uf.find(i)].add(email)\n    return [[accounts[i][0]] + sorted(emails) for i, emails in groups.items()]",
                "time_complexity": "O(n * k * α(n)) where k is avg emails per account, α is inverse Ackermann (nearly O(1))",
                "space_complexity": "O(n * k) for the email map and union-find",
                "brute_force_approach": "BFS/DFS on email graph: build adjacency list of emails, find connected components. Same complexity but Union-Find is cleaner and preferred in interviews.",
                "edge_cases": ["No shared emails (all separate)", "All accounts share one email (merge all)", "Same name but different people", "Single account with many emails"],
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
