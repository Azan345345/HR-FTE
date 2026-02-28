"""Job Hunter Agent — searches jobs across multiple platforms with deduplication."""

import re
import structlog
import json
from typing import Optional
from app.config import settings
from app.core.event_bus import event_bus
from app.core.llm_router import get_llm

logger = structlog.get_logger()

# ── Normalisation helpers for deduplication ───────────────────────────────────

_COMPANY_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|co|group|holdings|technologies|tech|solutions|services|consulting|global|international|the)\b\.?",
    re.IGNORECASE,
)
_TITLE_LEVELS = re.compile(
    r"\b(senior|sr|junior|jr|lead|principal|staff|associate|mid|entry|i|ii|iii|iv)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")


def _norm_company(name: str) -> str:
    s = _COMPANY_NOISE.sub("", name.lower())
    return _WHITESPACE.sub(" ", s).strip()


def _norm_title(title: str) -> str:
    s = _TITLE_LEVELS.sub("", title.lower())
    return _WHITESPACE.sub(" ", s).strip()


def _dedup_key(job: dict) -> str:
    return f"{_norm_company(job.get('company', ''))}|{_norm_title(job.get('title', ''))}"


def _merge_jobs(existing: dict, new: dict) -> dict:
    """Merge a duplicate job — keep richest data from both sources."""
    merged = dict(existing)
    # Prefer longer description
    if len(new.get("description", "")) > len(merged.get("description", "")):
        merged["description"] = new["description"]
    # Prefer first real application URL
    if not merged.get("application_url") and new.get("application_url"):
        merged["application_url"] = new["application_url"]
    # Merge requirements lists
    existing_reqs = set(merged.get("requirements") or [])
    new_reqs = set(new.get("requirements") or [])
    merged["requirements"] = list(existing_reqs | new_reqs)
    # Prefer salary if missing
    if not merged.get("salary_range") and new.get("salary_range"):
        merged["salary_range"] = new["salary_range"]
    # Accumulate sources
    existing_src = merged.get("source", "")
    new_src = new.get("source", "")
    if new_src and new_src not in existing_src:
        merged["source"] = f"{existing_src}+{new_src}" if existing_src else new_src
    # Keep LinkedIn URL if available
    if new.get("linkedin_url") and not merged.get("linkedin_url"):
        merged["linkedin_url"] = new["linkedin_url"]
    return merged


# ── Public entry point ────────────────────────────────────────────────────────

async def search_jobs(
    query: str,
    user_id: str = "unknown",
    location: Optional[str] = None,
    limit: int = 10,
    cv_data: Optional[dict] = None,
) -> list[dict]:
    """Search for jobs using all available APIs, deduplicate, score, and return."""
    await event_bus.emit_agent_started(user_id, "job_hunter", f"Searching jobs: {query}")

    # 1. Parse natural-language query into structured params
    llm = get_llm(task="search_query_parsing")
    parse_prompt = f"""Analyze this job search request: "{query}"

Extract:
1. Clean job title/keywords (without location)
2. Specific location (City, State, etc.)
3. Country name
4. ISO 3166-1 alpha-2 country code (e.g. 'au','us','gb','ca','in','de')

Return JSON: {{"title":"...","location":"...","country":"...","country_code":"..."}}
If no location specified default to "Remote" and null country.
Return ONLY JSON."""

    try:
        resp = await llm.ainvoke(parse_prompt)
        content = resp.content if hasattr(resp, "content") else str(resp)
        parsed = json.loads(content.strip().replace("```json", "").replace("```", ""))
        search_title = parsed.get("title", query)
        search_location = location or parsed.get("location")
        country_code = (parsed.get("country_code") or "us").lower()
        country_name = parsed.get("country")

        # Quick city → country code mapping
        if search_location and not country_name:
            loc = search_location.lower()
            if any(k in loc for k in ("london", " uk", "england", "britain")):
                country_code = "gb"
            elif any(k in loc for k in ("sydney", "melbourne", "brisbane", "australia")):
                country_code = "au"
            elif "paris" in loc or "france" in loc:
                country_code = "fr"
            elif "berlin" in loc or "germany" in loc:
                country_code = "de"
            elif "toronto" in loc or "canada" in loc:
                country_code = "ca"
            elif any(k in loc for k in ("india", "delhi", "bangalore", "mumbai")):
                country_code = "in"
            elif any(k in loc for k in ("dubai", "uae", "emirates")):
                country_code = "ae"
            elif any(k in loc for k in ("karachi", "lahore", "islamabad", "pakistan")):
                country_code = "pk"
    except Exception:
        search_title = query
        search_location = location
        country_code = "us"
        country_name = None

    all_jobs: list[dict] = []
    sources_tried: list[str] = []

    # 2. Apify LinkedIn (highest quality — real listings)
    if settings.APIFY_API_KEY:
        try:
            await event_bus.emit_agent_progress(
                user_id, "job_hunter", 1, 4, "Searching LinkedIn via Apify"
            )
            apify_jobs = await _search_apify_linkedin(
                search_title, search_location, limit, country_code
            )
            all_jobs.extend(apify_jobs)
            sources_tried.append("linkedin")
            logger.info("apify_linkedin_results", count=len(apify_jobs))
        except Exception as e:
            logger.warning("apify_linkedin_failed", error=str(e))

    # 3. SerpAPI Google Jobs
    if settings.SERPAPI_API_KEY:
        try:
            await event_bus.emit_agent_progress(
                user_id, "job_hunter", 2, 4,
                f"Searching Google Jobs ({country_name or 'Global'})"
            )
            serpapi_jobs = await _search_serpapi(
                search_title, search_location, limit, country_code
            )
            all_jobs.extend(serpapi_jobs)
            sources_tried.append("google_jobs")
            logger.info("serpapi_results", count=len(serpapi_jobs))
        except Exception as e:
            logger.warning("serpapi_failed", error=str(e))

    # 4. RapidAPI JSearch
    if settings.RAPIDAPI_KEY:
        try:
            await event_bus.emit_agent_progress(
                user_id, "job_hunter", 3, 4, "Searching RapidAPI JSearch"
            )
            jsearch_jobs = await _search_jsearch(
                search_title, search_location, limit, country_code
            )
            all_jobs.extend(jsearch_jobs)
            sources_tried.append("jsearch")
            logger.info("jsearch_results", count=len(jsearch_jobs))
        except Exception as e:
            logger.warning("jsearch_failed", error=str(e))

    # 5. LLM fallback if no real APIs returned anything
    if not all_jobs:
        await event_bus.emit_agent_progress(
            user_id, "job_hunter", 3, 4, "Generating AI sample jobs (no API keys active)"
        )
        all_jobs = await _generate_sample_jobs(query, location, limit)
        sources_tried.append("ai_generated")

    # 6. Cross-platform deduplication (fuzzy company+title match)
    await event_bus.emit_agent_progress(
        user_id, "job_hunter", 4, 4,
        f"Deduplicating {len(all_jobs)} listings from {len(sources_tried)} sources"
    )
    unique_jobs = _deduplicate(all_jobs)
    logger.info("after_dedup", before=len(all_jobs), after=len(unique_jobs))

    # 7. CV-based scoring
    if cv_data:
        unique_jobs = await _score_jobs_against_cv(unique_jobs, cv_data)

    unique_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)

    await event_bus.emit_agent_completed(
        user_id, "job_hunter",
        f"Found {len(unique_jobs[:limit])} unique positions across {'+'.join(sources_tried)}"
    )
    return unique_jobs[:limit]


# ── Deduplication ─────────────────────────────────────────────────────────────

def _deduplicate(jobs: list[dict]) -> list[dict]:
    """Merge jobs with the same (normalised company, normalised title)."""
    seen: dict[str, dict] = {}
    for job in jobs:
        key = _dedup_key(job)
        if key in seen:
            seen[key] = _merge_jobs(seen[key], job)
        else:
            seen[key] = dict(job)
    return list(seen.values())


# ── Apify LinkedIn Job Search ─────────────────────────────────────────────────

async def _search_apify_linkedin(
    query: str, location: Optional[str], limit: int, country_code: str = "us"
) -> list[dict]:
    """Search LinkedIn jobs via Apify's linkedin-jobs-search actor (sync run)."""
    import httpx

    actor_id = "curious_coder~linkedin-jobs-search"
    url = (
        f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
        f"?token={settings.APIFY_API_KEY}&timeout=60&memory=512"
    )

    payload = {
        "title": query,
        "location": location or "",
        "rows": min(limit * 2, 25),  # fetch extra so dedup still hits the limit
        "proxy": {"useApifyProxy": True},
    }

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        items = response.json()

    jobs = []
    for item in items:
        # Apify linkedin-jobs-search typical fields
        title = item.get("title") or item.get("job_title") or ""
        company = item.get("company") or item.get("companyName") or ""
        if not title or not company:
            continue

        jobs.append({
            "title": title,
            "company": company,
            "location": item.get("location") or item.get("jobLocation") or "",
            "description": item.get("description") or item.get("jobDescription") or "",
            "source": "linkedin",
            "application_url": item.get("url") or item.get("applyUrl") or item.get("jobUrl") or "",
            "linkedin_url": item.get("url") or item.get("jobUrl") or "",
            "posted_date": item.get("postedDate") or item.get("publishedAt") or "",
            "salary_range": item.get("salary") or item.get("salaryRange") or "",
            "job_type": item.get("employmentType") or item.get("jobType") or "",
            "requirements": _extract_requirements(
                item.get("description") or item.get("jobDescription") or ""
            ),
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": _guess_domain(company),
        })
    return jobs[:limit]


def _extract_requirements(description: str) -> list[str]:
    """Extract likely skill/requirement tokens from a job description."""
    if not description:
        return []
    # Simple heuristic: lines that look like bullet requirements
    lines = [l.strip().lstrip("•·-–*").strip() for l in description.splitlines()]
    reqs = [l for l in lines if 5 < len(l) < 120 and any(
        kw in l.lower() for kw in
        ("experience", "knowledge", "proficiency", "skill", "degree", "years", "familiar", "ability")
    )]
    return reqs[:8]


def _guess_domain(company: str) -> str:
    """Best-effort company domain guess for Hunter.io lookup."""
    clean = re.sub(r"[^a-z0-9]", "", company.lower())
    return f"{clean}.com" if clean else ""


# ── SerpAPI Google Jobs ───────────────────────────────────────────────────────

async def _search_serpapi(
    query: str, location: Optional[str], limit: int, country_code: str = "us"
) -> list[dict]:
    from serpapi import GoogleSearch

    domains = {"au": "google.com.au", "gb": "google.co.uk", "ca": "google.ca",
               "in": "google.co.in", "us": "google.com"}
    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": settings.SERPAPI_API_KEY,
        "num": limit,
        "gl": country_code,
        "hl": "en",
        "google_domain": domains.get(country_code, "google.com"),
    }
    if location:
        params["location"] = location

    search = GoogleSearch(params)
    results = search.get_dict()

    jobs = []
    for item in results.get("jobs_results", []):
        company = item.get("company_name", "")
        jobs.append({
            "title": item.get("title", ""),
            "company": company,
            "location": item.get("location", ""),
            "description": item.get("description", ""),
            "source": "google_jobs",
            "application_url": item.get("apply_link") or item.get("link") or "",
            "posted_date": item.get("detected_extensions", {}).get("posted_at", ""),
            "salary_range": item.get("detected_extensions", {}).get("salary", ""),
            "job_type": item.get("detected_extensions", {}).get("schedule_type", ""),
            "requirements": [],
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": _guess_domain(company),
        })
    return jobs


# ── RapidAPI JSearch ──────────────────────────────────────────────────────────

async def _search_jsearch(
    query: str, location: Optional[str], limit: int, country_code: str = "us"
) -> list[dict]:
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={
                "query": f"{query} {location or ''}".strip(),
                "num_pages": "1",
                "country": country_code,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data.get("data", []):
        company = item.get("employer_name", "")
        jobs.append({
            "title": item.get("job_title", ""),
            "company": company,
            "location": f"{item.get('job_city','')} {item.get('job_state','')}".strip(),
            "description": item.get("job_description", ""),
            "source": item.get("job_publisher", "jsearch"),
            "application_url": item.get("job_apply_link", ""),
            "posted_date": item.get("job_posted_at_datetime_utc", ""),
            "salary_range": _format_salary(item),
            "job_type": item.get("job_employment_type", ""),
            "requirements": item.get("job_required_skills") or [],
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": _guess_domain(company),
        })
    return jobs[:limit]


def _format_salary(item: dict) -> str:
    lo, hi = item.get("job_min_salary"), item.get("job_max_salary")
    if lo and hi:
        return f"${lo:,.0f} – ${hi:,.0f}"
    return ""


# ── LLM Sample Fallback ───────────────────────────────────────────────────────

async def _generate_sample_jobs(query: str, location: Optional[str], limit: int) -> list[dict]:
    llm = get_llm(task="job_search_sample")
    prompt = f"""Generate {limit} realistic job listings for "{query}" in "{location or 'Remote'}".

Return a JSON array. Each element:
{{
  "title": "Job Title",
  "company": "Real company name",
  "location": "City, State or Remote",
  "salary_range": "$X – $Y",
  "job_type": "Full-time",
  "description": "2-3 sentence description",
  "requirements": ["req1","req2","req3"],
  "source": "ai_generated",
  "posted_date": "2 days ago",
  "application_url": "https://example.com/apply"
}}
Return ONLY valid JSON array, no markdown."""
    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        jobs = json.loads(content)
        for j in jobs:
            j.setdefault("matching_skills", [])
            j.setdefault("missing_skills", [])
            j.setdefault("company_domain", _guess_domain(j.get("company", "")))
        return jobs
    except Exception as e:
        logger.error("sample_job_generation_error", error=str(e))
        return []


# ── CV Scoring ────────────────────────────────────────────────────────────────

async def _score_jobs_against_cv(jobs: list[dict], cv_data: dict) -> list[dict]:
    cv_skills: set[str] = set()
    for skill_list in (cv_data.get("skills") or {}).values():
        if isinstance(skill_list, list):
            cv_skills.update(s.lower() for s in skill_list)

    for job in jobs:
        job_text = (
            f"{job.get('title','')} {job.get('description','')} "
            f"{' '.join(job.get('requirements',[]))}"
        ).lower()
        matching = [s for s in cv_skills if s in job_text]
        missing = [r for r in (job.get("requirements") or []) if r.lower() not in " ".join(cv_skills)]
        overlap = len(matching)
        score = min(100, int((overlap / max(len(cv_skills), 1)) * 100 + 20))
        job["match_score"] = score
        job["matching_skills"] = matching[:10]
        job["missing_skills"] = missing[:5]
    return jobs
