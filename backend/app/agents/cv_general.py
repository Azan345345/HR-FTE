"""CV General Agent — deep, personalised answers to any question about the user's CV.

This agent is invoked whenever the user asks anything about their own CV that isn't
a formal analysis/score request (cv_analysis), a tailor request (cv_tailor), or an upload.

Examples of questions it handles:
  - "What are my strongest skills?"
  - "Is my work experience enough for a senior role?"
  - "Rewrite my professional summary"
  - "What's missing from my CV?"
  - "Am I ATS-friendly?"
  - "What kind of roles am I best suited for?"
  - "How do I improve my career progression story?"
  - "What should I remove from my CV?"
  - "Compare my skills against a data scientist role"
"""

import structlog
from langchain_core.messages import SystemMessage, HumanMessage

logger = structlog.get_logger()

_CV_GENERAL_SYSTEM = """You are an elite CV consultant and career strategist with 20+ years of hands-on experience across every industry globally — tech, finance, healthcare, consulting, marketing, operations, and more.

You have the user's complete CV loaded in front of you. Your job is to answer their question with DEEP, SPECIFIC, PERSONALISED intelligence — never generic advice.

WHAT YOU CAN DO (handle ALL of these with expert precision):
• Strengths & weaknesses analysis — reference actual job titles, companies, skills from the CV
• ATS optimisation — keyword density, formatting, missing keywords, structural gaps
• Career trajectory analysis — progression speed, seniority jumps, gaps, growth story
• Skill gap identification — against any target role, industry, or seniority level
• Full section rewrites — summary, experience bullets, skills, headline, cover letter snippets
• Benchmarking — compare their background against industry standards for their target level
• Career pivot guidance — identify transferable skills for a different domain or role
• Salary intelligence — estimate range based on their background, location, industry
• Personal branding — narrative, positioning, unique value proposition
• Job fit matching — which roles, companies, industries align best with their profile
• Actionable improvement plans — prioritised list of what to fix first for maximum impact

RULES — follow these without exception:
1. ALWAYS reference their actual job titles, companies, specific skills, and achievements — never talk about a fictional person
2. Be brutally honest — if something is weak, say so with a clear explanation and exact fix
3. Give specific, actionable advice — no vague platitudes like "tailor your CV" without showing HOW
4. Use clean markdown: ## headers, bullet points, **bold** for key terms — easy to scan
5. Calibrate response length to complexity: short question → concise answer; deep question → thorough analysis
6. If asked to REWRITE something → write the full rewritten version, not a template or example
7. If asked a yes/no question → answer it first, then explain why, then give specific next steps
8. Always end with 1-2 concrete next actions the user can take immediately"""


def _build_cv_context(cv_data: dict) -> str:
    """Serialize the parsed CV into a compact, structured text block for the LLM."""
    parts = []

    personal = cv_data.get("personal_info", {}) or {}
    if personal.get("name"):
        parts.append(f"Name: {personal['name']}")
    if personal.get("location"):
        parts.append(f"Location: {personal['location']}")
    if personal.get("email"):
        parts.append(f"Email: {personal['email']}")
    if personal.get("phone"):
        parts.append(f"Phone: {personal['phone']}")
    if personal.get("linkedin"):
        parts.append(f"LinkedIn: {personal['linkedin']}")
    if personal.get("github"):
        parts.append(f"GitHub: {personal['github']}")

    summary = cv_data.get("professional_summary", "") or ""
    if summary:
        parts.append(f"\n## Professional Summary\n{summary[:600]}")

    skills = cv_data.get("skills", {}) or {}
    tech = skills.get("technical", []) or []
    tools = skills.get("tools", []) or []
    soft = skills.get("soft", []) or []
    langs = skills.get("languages", []) or []
    if tech:
        parts.append(f"\n## Technical Skills\n{', '.join(str(s) for s in tech[:30])}")
    if tools:
        parts.append(f"Tools & Platforms: {', '.join(str(s) for s in tools[:20])}")
    if soft:
        parts.append(f"Soft Skills: {', '.join(str(s) for s in soft[:10])}")
    if langs:
        parts.append(f"Languages: {', '.join(str(s) for s in langs[:8])}")

    exp = cv_data.get("experience", []) or []
    if exp:
        parts.append("\n## Work Experience")
        for job in exp[:8]:
            role = job.get("role") or job.get("title") or "Role"
            company = job.get("company", "")
            duration = job.get("duration") or job.get("period") or ""
            location = job.get("location", "")
            loc_str = f" | {location}" if location else ""
            parts.append(f"\n**{role}** — {company}{loc_str} ({duration})")
            descs = job.get("descriptions", []) or job.get("bullets", []) or []
            for d in descs[:5]:
                parts.append(f"  • {str(d)[:150]}")

    edu = cv_data.get("education", []) or []
    if edu:
        parts.append("\n## Education")
        for school in edu[:4]:
            deg = school.get("degree", "")
            field = school.get("field", "")
            inst = school.get("institution", "")
            year = school.get("graduation_year", "") or school.get("year", "")
            gpa = school.get("gpa", "")
            gpa_str = f" | GPA: {gpa}" if gpa else ""
            parts.append(f"  • {deg} in {field} — {inst} ({year}){gpa_str}".strip(" —"))

    projects = cv_data.get("projects", []) or []
    if projects:
        parts.append(f"\n## Projects ({len(projects)} total)")
        for p in projects[:5]:
            name = p.get("name", "Project")
            desc = p.get("description", "")
            tech_used = p.get("technologies", []) or []
            tech_str = f" [{', '.join(str(t) for t in tech_used[:5])}]" if tech_used else ""
            parts.append(f"  • **{name}**{tech_str}: {str(desc)[:150]}")

    certs = cv_data.get("certifications", []) or []
    if certs:
        cert_names = []
        for c in certs[:8]:
            if isinstance(c, dict):
                cert_names.append(c.get("name", str(c)))
            else:
                cert_names.append(str(c))
        parts.append(f"\n## Certifications\n{', '.join(cert_names)}")

    awards = cv_data.get("awards", []) or cv_data.get("achievements", []) or []
    if awards:
        parts.append("\n## Awards & Achievements")
        for a in awards[:4]:
            parts.append(f"  • {str(a)[:150]}")

    return "\n".join(parts)


async def answer_cv_question(
    cv_data: dict,
    question: str,
    history: list = None,
) -> str:
    """Answer any CV-related question with deep, personalised intelligence.

    Args:
        cv_data:  The parsed CV dict from UserCV.parsed_data.
        question: The user's raw question / request.
        history:  Recent conversation messages [{"role": str, "content": str}].

    Returns:
        A rich markdown-formatted answer.
    """
    from app.core.llm_router import get_llm

    llm = get_llm(task="cv_general")
    cv_block = _build_cv_context(cv_data)

    # Attach recent conversation context to system prompt so the agent can
    # refer back to what was discussed (e.g. "improve what you suggested")
    system_content = _CV_GENERAL_SYSTEM
    if history:
        recent = [
            m for m in history[-10:]
            if not m.get("content", "").startswith("__")
        ][-8:]
        if recent:
            history_lines = "\n".join(
                "{}: {}".format(
                    "User" if m["role"] == "user" else "CareerAgent",
                    m["content"][:400],
                )
                for m in recent
            )
            system_content += f"\n\n---\nRecent conversation:\n{history_lines}"

    user_content = f"Here is my CV:\n\n{cv_block}\n\n---\n\nMy question: {question}"

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ])
        return (response.content if hasattr(response, "content") else str(response)).strip()
    except Exception as e:
        logger.error("cv_general_error", error=str(e))
        # Minimal fallback — still data-driven
        name = (cv_data.get("personal_info") or {}).get("name", "")
        prefix = f"**{name}** — " if name else ""
        skills_list = (cv_data.get("skills", {}) or {}).get("technical", [])
        skills_str = ", ".join(str(s) for s in skills_list[:8]) if skills_list else "not listed"
        return (
            f"{prefix}I had trouble generating a full response right now. "
            f"Based on your CV, your core skills include: {skills_str}. "
            "Please try your question again — I'll give you a detailed answer."
        )
