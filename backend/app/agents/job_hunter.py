"""Job Hunter Agent — searches jobs across multiple platforms with deduplication."""

import re
import asyncio
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

# Domains that are job-listing aggregators, NOT company domains.
# Used to avoid sending HR-finder lookups to indeed.com, linkedin.com, etc.
_JOB_BOARD_DOMAINS = frozenset({
    "indeed.com", "linkedin.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "google.com", "lever.co", "greenhouse.io",
    "workday.com", "smartrecruiters.com", "applytojob.com",
    "talent.com", "salary.com", "jora.com", "adzuna.com",
    "careerbuilder.com", "dice.com", "reed.co.uk", "simplyhired.com",
    "roberthalf.com", "snagajob.com", "hired.com", "wellfound.com",
    "angel.co", "remotive.com", "weworkremotely.com", "flexjobs.com",
    "jobvite.com", "icims.com", "myworkdayjobs.com", "breezy.hr",
    "recruitee.com", "ashbyhq.com", "jobs.lever.co", "boards.greenhouse.io",
    "apply.workable.com", "careers.jobscore.com", "bamboohr.com",
    "paylocity.com", "paycom.com", "naukri.com", "seek.com.au",
    "totaljobs.com", "cwjobs.co.uk", "cv-library.co.uk", "jooble.org",
})


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
    job_type: Optional[str] = None,
    limit: int = 10,
    cv_data: Optional[dict] = None,
    country_code: Optional[str] = None,
    skip_llm_parse: bool = False,
) -> list[dict]:
    """Search for jobs using all available APIs, deduplicate, score, and return."""
    await event_bus.emit_agent_started(user_id, "job_hunter", f"Searching jobs: {query}")

    if skip_llm_parse:
        # Caller already parsed the query — use pre-parsed values directly
        search_title = query
        search_location = location
        country_code = _infer_country_code(search_location, country_code)
        country_name = None
        job_type = _normalize_job_type(job_type)
    else:
        # 1. Parse natural-language query into structured params via LLM
        llm = get_llm(task="search_query_parsing")
        parse_prompt = f"""Analyze this job search request: "{query}"

Extract:
1. Clean job title/keywords (without location or employment type)
2. Specific location (City, State, country — or null if not mentioned)
3. Country name
4. ISO 3166-1 alpha-2 country code (e.g. 'au','us','gb','ca','in','de')
5. Employment/job type — one of: fulltime, parttime, contract, temporary, internship, remote, hybrid (or null)

Return JSON: {{"title":"...","location":"...","country":"...","country_code":"...","job_type":"..."}}
If no location specified use null. If no job type specified use null.
Return ONLY JSON."""

        try:
            resp = await llm.ainvoke(parse_prompt)
            content = resp.content if hasattr(resp, "content") else str(resp)
            parsed = json.loads(content.strip().replace("```json", "").replace("```", ""))
            search_title = parsed.get("title", query)
            search_location = location or parsed.get("location")
            country_code = (parsed.get("country_code") or "us").lower()
            country_name = parsed.get("country")
            # Caller-supplied job_type wins; fall back to LLM-extracted value
            job_type = _normalize_job_type(job_type) or _normalize_job_type(parsed.get("job_type"))

            # Refine country_code with deterministic mapping
            country_code = _infer_country_code(search_location, country_code)
        except Exception:
            search_title = query
            search_location = location
            country_code = "us"
            country_name = None
            job_type = _normalize_job_type(job_type)

    all_jobs: list[dict] = []
    sources_tried: list[str] = []

    async def _emit_batch(source_key: str, source_label: str, jobs: list[dict]):
        """Emit a batch of jobs found from one source to the frontend."""
        await event_bus.emit(user_id, "jobs_stream", {
            "phase": "searching",
            "source": source_key,
            "source_label": source_label,
            "jobs": [
                {
                    "title": j.get("title", ""),
                    "company": j.get("company", ""),
                    "location": j.get("location", ""),
                    "job_type": j.get("job_type", ""),
                    "salary_range": j.get("salary_range", ""),
                    "application_url": j.get("application_url", ""),
                    "source": j.get("source", source_key),
                }
                for j in jobs
            ],
            "count": len(jobs),
        })

    # 2. Build source tasks — run ALL sources concurrently so the total wait time
    #    equals the SLOWEST source (not the sum), preventing Railway proxy timeouts.
    async def _run_source(source_key: str, source_label: str, coro) -> tuple[str, list[dict]]:
        await event_bus.emit(user_id, "jobs_stream", {
            "phase": "source_start", "source": source_key, "source_label": source_label
        })
        try:
            jobs = await coro
            await _emit_batch(source_key, source_label, jobs)
            logger.info(f"{source_key}_results", count=len(jobs))
            return source_key, jobs
        except Exception as e:
            logger.warning(f"{source_key}_failed", error=str(e))
            return source_key, []

    # ── Tier 1: Free / low-cost sources (run concurrently) ─────────────────
    free_tasks = []
    if settings.RAPIDAPI_KEY:
        free_tasks.append(_run_source("jsearch", "JSearch",
            _search_jsearch(search_title, search_location, limit, country_code, job_type)))
        free_tasks.append(_run_source("indeed_rapid", "Indeed",
            _search_indeed_rapidapi(search_title, search_location, limit, country_code, job_type)))
        free_tasks.append(_run_source("glassdoor", "Glassdoor",
            _search_glassdoor_rapidapi(search_title, search_location, limit, country_code, job_type)))
    if settings.ADZUNA_APP_ID and settings.ADZUNA_APP_KEY:
        free_tasks.append(_run_source("adzuna", "Adzuna",
            _search_adzuna(search_title, search_location, limit, country_code, job_type)))

    if free_tasks:
        results = await asyncio.gather(*free_tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                logger.warning("source_task_exception", error=str(result))
                continue
            source_key, jobs = result
            if jobs:
                sources_tried.append(source_key)
            all_jobs.extend(jobs)

    # ── Tier 2: Paid fallback sources (only if free sources returned nothing) ─
    if not all_jobs:
        logger.info("free_sources_empty_trying_paid", sources_tried=sources_tried)
        paid_tasks = []
        if settings.APIFY_API_KEY:
            paid_tasks.append(_run_source("indeed", "Indeed (Apify)",
                _search_apify_indeed(search_title, search_location, limit, country_code, job_type)))
            paid_tasks.append(_run_source("linkedin", "LinkedIn (Apify)",
                _search_apify_linkedin(search_title, search_location, limit, country_code, job_type)))
        if settings.SERPAPI_API_KEY:
            paid_tasks.append(_run_source("google_jobs", f"Google Jobs ({country_name or 'Global'})",
                _search_serpapi(search_title, search_location, limit, country_code, job_type)))

        if paid_tasks:
            results = await asyncio.gather(*paid_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("paid_source_task_exception", error=str(result))
                    continue
                source_key, jobs = result
                if jobs:
                    sources_tried.append(source_key)
                all_jobs.extend(jobs)

    # 5. LLM fallback — runs only when every real API returned nothing
    if not all_jobs:
        logger.warning(
            "all_job_apis_empty_using_llm_fallback",
            query=search_title, location=search_location,
            sources_tried=sources_tried,
        )
        await event_bus.emit(user_id, "jobs_stream", {
            "phase": "source_start",
            "source": "ai_generated",
            "source_label": "AI-generated listings (no API keys configured)",
        })
        all_jobs = await _generate_sample_jobs(search_title, search_location, limit)
        sources_tried.append("ai_generated")
        await _emit_batch("ai_generated", "AI Generated", all_jobs)

    # 6. Cross-platform deduplication (fuzzy company+title match)
    await event_bus.emit(user_id, "jobs_stream", {
        "phase": "deduplicating",
        "total": len(all_jobs),
        "sources": len(sources_tried),
    })
    unique_jobs = _deduplicate(all_jobs)
    removed = len(all_jobs) - len(unique_jobs)
    await event_bus.emit(user_id, "jobs_stream", {
        "phase": "dedup_done",
        "before": len(all_jobs),
        "after": len(unique_jobs),
        "removed": removed,
    })
    logger.info("after_dedup", before=len(all_jobs), after=len(unique_jobs))

    # Emit the full unique jobs list for the center panel display
    await event_bus.emit(user_id, "jobs_stream", {
        "phase": "unique_jobs",
        "jobs": [
            {
                "title": j.get("title", ""),
                "company": j.get("company", ""),
                "location": j.get("location", ""),
                "job_type": j.get("job_type", ""),
                "salary_range": j.get("salary_range", ""),
                "application_url": j.get("application_url", ""),
                "source": j.get("source", ""),
            }
            for j in unique_jobs
        ],
    })

    # 7. CV-based scoring
    if cv_data:
        unique_jobs = await _score_jobs_against_cv(unique_jobs, cv_data)

    unique_jobs.sort(key=lambda j: j.get("match_score", 0), reverse=True)

    sources_label = "+".join(sources_tried) if sources_tried else "no sources"
    await event_bus.emit_agent_completed(
        user_id, "job_hunter",
        f"Found {len(unique_jobs)} unique positions across {sources_label}"
    )
    # Return ALL unique jobs — caller decides how many to display.
    # HR lookup should run on ALL of them, not a truncated subset.
    return unique_jobs


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


# ── Apify Indeed Job Search ───────────────────────────────────────────────────

async def _search_apify_indeed(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    """Search Indeed jobs via Apify's official indeed-scraper actor."""
    import httpx

    # Country code mapping: ISO 2-letter → Indeed country code (uppercase)
    indeed_country = country_code.upper() if country_code else "US"

    url = (
        f"https://api.apify.com/v2/acts/misceres~indeed-scraper/run-sync-get-dataset-items"
        f"?token={settings.APIFY_API_KEY}&timeout=120&memory=1024"
    )

    # Map canonical job_type → Indeed's jobType values
    _indeed_job_type = {
        "fulltime": "fulltime", "parttime": "parttime",
        "contract": "contract", "temporary": "temporary", "internship": "internship",
    }
    search_location = location or ""
    payload: dict = {
        "position": query,
        "country": indeed_country,
        "location": search_location,
        "maxItems": min(limit * 2, 20),
        "parseCompanyDetails": False,
        "saveOnlyUniqueItems": True,
        "followApplyRedirects": False,
        "fromage": 14,  # only jobs posted in the last 14 days
    }
    if job_type == "remote":
        payload["remoteness"] = "1"  # Indeed's remote filter
    elif job_type in _indeed_job_type:
        payload["jobType"] = _indeed_job_type[job_type]

    async with httpx.AsyncClient(timeout=35) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        items = response.json()

    jobs = []
    for item in items:
        title = item.get("positionName") or item.get("title") or ""
        company = item.get("company") or ""
        if not title or not company:
            continue
        # Try to extract real company domain from externalApplyLink
        apply_url = item.get("externalApplyLink") or item.get("url") or ""
        d = _extract_domain_from_url(apply_url)
        domain = d if d and not _is_job_board(d) else _guess_domain(company)
        jobs.append({
            "title": title,
            "company": company,
            "location": item.get("location") or "",
            "description": item.get("description") or item.get("jobDescription") or "",
            "source": "indeed",
            "application_url": apply_url,
            "posted_date": item.get("postedAt") or item.get("postedTime") or "",
            "salary_range": item.get("salary") or "",
            "job_type": _ensure_str(item.get("jobType")),
            "requirements": _extract_requirements(
                item.get("description") or item.get("jobDescription") or ""
            ),
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": domain,
        })
    return jobs[:limit]


# ── Apify LinkedIn Job Search ─────────────────────────────────────────────────

async def _search_apify_linkedin(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    """Search LinkedIn jobs via fantastic-jobs/advanced-linkedin-job-search-api actor.

    Input schema:
      titleSearch    – array of title keywords (AND-matched within each item)
      locationSearch – array of location strings in 'City, Region, Country' format
      workTypes      – array of employment type strings
      count          – max jobs to return (up to 5000)
    """
    import httpx

    # Map canonical job_type → LinkedIn work type labels
    _li_work_type = {
        "fulltime": "Full-time", "parttime": "Part-time",
        "contract": "Contract", "temporary": "Temporary", "internship": "Internship",
    }

    # Build location strings: actor requires full English names, no abbreviations
    location_terms: list[str] = []
    if job_type == "remote":
        location_terms.append("Remote")
    elif location:
        location_terms.append(location)

    url = (
        "https://api.apify.com/v2/acts/fantastic-jobs~advanced-linkedin-job-search-api"
        f"/run-sync-get-dataset-items?token={settings.APIFY_API_KEY}&timeout=120&memory=1024"
    )

    payload: dict = {
        "titleSearch": [query],
        "count": min(limit * 2, 50),
    }
    if location_terms:
        payload["locationSearch"] = location_terms
    if job_type in _li_work_type:
        payload["workTypes"] = [_li_work_type[job_type]]

    async with httpx.AsyncClient(timeout=35) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        items = response.json()

    jobs = []
    for item in items:
        # Actor returns nested job/company objects; handle both flat and nested
        job_obj = item.get("job") or item
        company_obj = item.get("company") or item

        title = (
            job_obj.get("title") or job_obj.get("positionName") or
            item.get("title") or item.get("jobTitle") or ""
        )
        company = (
            company_obj.get("name") or company_obj.get("companyName") or
            item.get("companyName") or item.get("company") or ""
        )
        if not title or not company:
            continue

        description = (
            job_obj.get("description") or job_obj.get("descriptionText") or
            item.get("description") or item.get("jobDescription") or ""
        )
        location_val = (
            job_obj.get("location") or job_obj.get("jobLocation") or
            item.get("location") or item.get("jobLocation") or ""
        )
        apply_url = (
            job_obj.get("applyUrl") or job_obj.get("url") or job_obj.get("jobUrl") or
            item.get("applyUrl") or item.get("url") or item.get("jobUrl") or ""
        )
        linkedin_url = (
            job_obj.get("linkedinUrl") or job_obj.get("url") or
            item.get("linkedinUrl") or item.get("url") or ""
        )
        posted = (
            job_obj.get("postedAt") or job_obj.get("publishedAt") or
            item.get("postedAt") or item.get("publishedAt") or item.get("postedDate") or ""
        )
        salary = (
            job_obj.get("salary") or job_obj.get("salaryRange") or
            item.get("salary") or item.get("salaryRange") or ""
        )
        job_type = _ensure_str(
            job_obj.get("employmentType") or job_obj.get("workType") or
            item.get("employmentType") or item.get("jobType")
        )

        # Try company website from actor data, then apply URL, then guess
        company_url = (
            company_obj.get("url") or company_obj.get("website") or
            company_obj.get("companyUrl") or ""
        )
        d = _extract_domain_from_url(company_url)
        if not d or _is_job_board(d):
            d = _extract_domain_from_url(apply_url)
        if not d or _is_job_board(d):
            d = _guess_domain(company)

        jobs.append({
            "title": title,
            "company": company,
            "location": location_val,
            "description": description,
            "source": "linkedin",
            "application_url": apply_url,
            "linkedin_url": linkedin_url,
            "posted_date": posted,
            "salary_range": salary,
            "job_type": job_type,
            "requirements": _extract_requirements(description),
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": d,
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


def _ensure_str(value) -> str:
    """Coerce a value to a string. Handles lists like ['Full-time'] → 'Full-time'."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else ""
    return str(value)


def _is_job_board(domain: str) -> bool:
    """Return True if the domain belongs to a known job-listing site."""
    d = domain.lower().strip()
    return any(d == jb or d.endswith("." + jb) for jb in _JOB_BOARD_DOMAINS)


def _extract_domain_from_url(url: str) -> str:
    """Extract domain from a URL, stripping protocol and www prefix."""
    if not url:
        return ""
    d = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].strip()
    return d if d and "." in d else ""


def _guess_domain(company: str) -> str:
    """Best-effort company domain guess for Hunter.io lookup."""
    if not company:
        return ""
    # Strip common suffixes that aren't in domain names
    c = re.sub(r"\b(inc|llc|ltd|limited|corp|corporation|co|group|gmbh|pty|plc)\b\.?", "", company, flags=re.IGNORECASE)
    # Keep hyphens between words (e.g. "Rolls-Royce" → "rolls-royce.com")
    c = re.sub(r"[^a-z0-9\s-]", "", c.lower()).strip()
    # Join words with nothing (most company domains) — e.g. "Adamantium Corp" → "adamantium"
    parts = c.split()
    if not parts:
        return ""
    # Single-word company → word.com; multi-word → try joined version
    domain = "".join(parts)
    return f"{domain}.com"


# ── Job type normalisation ─────────────────────────────────────────────────────

_JOB_TYPE_ALIASES: dict[str, str] = {
    # Full-time
    "full-time": "fulltime", "full time": "fulltime", "fulltime": "fulltime", "ft": "fulltime",
    # Part-time
    "part-time": "parttime", "part time": "parttime", "parttime": "parttime", "pt": "parttime",
    # Contract / Freelance
    "contract": "contract", "contractor": "contract", "freelance": "contract", "consulting": "contract",
    # Temporary
    "temporary": "temporary", "temp": "temporary",
    # Internship
    "internship": "internship", "intern": "internship",
    # Remote
    "remote": "remote", "work from home": "remote", "wfh": "remote", "fully remote": "remote",
    # Hybrid
    "hybrid": "hybrid",
}


def _normalize_job_type(job_type: Optional[str]) -> Optional[str]:
    """Map user-facing job type string to a canonical internal value."""
    if not job_type:
        return None
    return _JOB_TYPE_ALIASES.get(job_type.lower().strip())


def _infer_country_code(location: str, fallback: Optional[str] = None) -> str:
    """Map a location string to an ISO 3166-1 alpha-2 country code."""
    if not location:
        return fallback or "us"
    loc = location.lower()
    if any(k in loc for k in ("london", " uk", "england", "britain", "scotland", "wales")):
        return "gb"
    elif any(k in loc for k in ("sydney", "melbourne", "brisbane", "australia")):
        return "au"
    elif "paris" in loc or "france" in loc:
        return "fr"
    elif "berlin" in loc or "germany" in loc or "munich" in loc or "frankfurt" in loc:
        return "de"
    elif "toronto" in loc or "vancouver" in loc or "canada" in loc:
        return "ca"
    elif any(k in loc for k in ("india", "delhi", "bangalore", "mumbai", "hyderabad")):
        return "in"
    elif any(k in loc for k in ("dubai", "uae", "emirates", "abu dhabi")):
        return "ae"
    elif any(k in loc for k in ("karachi", "lahore", "islamabad", "pakistan")):
        return "pk"
    elif any(k in loc for k in ("finland", "helsinki", "tampere", "espoo")):
        return "fi"
    elif any(k in loc for k in ("norway", "oslo", "bergen", "trondheim")):
        return "no"
    elif any(k in loc for k in ("sweden", "stockholm", "gothenburg", "malmö", "malmo")):
        return "se"
    elif any(k in loc for k in ("denmark", "copenhagen", "aarhus")):
        return "dk"
    elif any(k in loc for k in ("netherlands", "amsterdam", "rotterdam", "hague")):
        return "nl"
    elif any(k in loc for k in ("switzerland", "zurich", "geneva", "bern")):
        return "ch"
    elif any(k in loc for k in ("austria", "vienna", "graz")):
        return "at"
    elif any(k in loc for k in ("singapore",)):
        return "sg"
    elif any(k in loc for k in ("poland", "warsaw", "krakow")):
        return "pl"
    elif any(k in loc for k in ("spain", "madrid", "barcelona")):
        return "es"
    elif any(k in loc for k in ("italy", "rome", "milan")):
        return "it"
    return fallback or "us"


# ── SerpAPI Google Jobs ───────────────────────────────────────────────────────

async def _search_serpapi(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    from serpapi import GoogleSearch

    domains = {
        "au": "google.com.au", "gb": "google.co.uk", "ca": "google.ca",
        "in": "google.co.in", "us": "google.com", "de": "google.de",
        "fr": "google.fr", "nl": "google.nl", "se": "google.se",
        "no": "google.no", "fi": "google.fi", "dk": "google.dk",
        "ch": "google.ch", "at": "google.at", "es": "google.es",
        "it": "google.it", "pl": "google.pl", "sg": "google.com.sg",
    }

    # Map canonical job_type → Google Jobs employment_type chip values
    _serp_employment = {
        "fulltime": "FULLTIME", "parttime": "PARTTIME",
        "contract": "CONTRACTOR", "internship": "INTERN",
    }

    search_q = f"{query} {location}".strip() if location else query
    # Build chips — always include freshness filter
    chips_parts = ["date:r,604800"]  # posted in last 7 days
    if job_type == "remote":
        search_q = f"{query} remote".strip()
    elif job_type == "hybrid":
        search_q = f"{query} hybrid".strip()
    elif job_type in _serp_employment:
        chips_parts.append(f"employment_type:{_serp_employment[job_type]}")

    params = {
        "engine": "google_jobs",
        "q": search_q,
        "api_key": settings.SERPAPI_API_KEY,
        "num": limit,
        "gl": country_code,
        "hl": "en",
        "google_domain": domains.get(country_code, "google.com"),
        "chips": ",".join(chips_parts),
        "no_cache": "true",        # always fetch fresh results, bypass SerpAPI cache
    }

    loop = asyncio.get_event_loop()
    search = GoogleSearch(params)
    results = await loop.run_in_executor(None, search.get_dict)

    jobs = []
    for item in results.get("jobs_results", []):
        company = item.get("company_name", "")
        # Try to extract real domain from apply_options (company career pages)
        domain = ""
        for opt in (item.get("apply_options") or []):
            link = opt.get("link", "")
            d = _extract_domain_from_url(link)
            if d and not _is_job_board(d):
                domain = d
                break
        if not domain:
            domain = _guess_domain(company)
        jobs.append({
            "title": item.get("title", ""),
            "company": company,
            "location": item.get("location", ""),
            "description": item.get("description", ""),
            "source": "google_jobs",
            "application_url": item.get("apply_link") or item.get("link") or "",
            "posted_date": item.get("detected_extensions", {}).get("posted_at", ""),
            "salary_range": item.get("detected_extensions", {}).get("salary", ""),
            "job_type": _ensure_str(item.get("detected_extensions", {}).get("schedule_type")),
            "requirements": [],
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": domain,
        })
    return jobs


# ── RapidAPI JSearch ──────────────────────────────────────────────────────────

async def _search_jsearch(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    import httpx

    # Map canonical job_type → JSearch employment_types values
    _jsearch_type = {
        "fulltime": "FULLTIME", "parttime": "PARTTIME",
        "contract": "CONTRACTOR", "temporary": "CONTRACTOR",
        "internship": "INTERN",
    }

    jsearch_params: dict = {
        "query": f"{query} {location or ''}".strip(),
        "num_pages": "1",
        "country": country_code,
        "date_posted": "week",  # only jobs from the past week
    }
    if job_type == "remote":
        jsearch_params["remote_jobs_only"] = "true"
    elif job_type in _jsearch_type:
        jsearch_params["employment_types"] = _jsearch_type[job_type]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params=jsearch_params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data.get("data", []):
        company = item.get("employer_name", "")
        # Use real employer_website when available (e.g. "https://www.google.com")
        raw_website = item.get("employer_website") or ""
        d = _extract_domain_from_url(raw_website)
        if d and not _is_job_board(d):
            domain = d
        else:
            domain = _guess_domain(company)
        jobs.append({
            "title": item.get("job_title", ""),
            "company": company,
            "location": " ".join(filter(None, [item.get('job_city'), item.get('job_state')])).strip(),
            "description": item.get("job_description", ""),
            "source": item.get("job_publisher", "jsearch"),
            "application_url": item.get("job_apply_link", ""),
            "posted_date": item.get("job_posted_at_datetime_utc", ""),
            "salary_range": _format_salary(item),
            "job_type": _ensure_str(item.get("job_employment_type")),
            "requirements": item.get("job_required_skills") or [],
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": domain,
        })
    return jobs[:limit]


def _format_salary(item: dict) -> str:
    lo, hi = item.get("job_min_salary"), item.get("job_max_salary")
    if lo and hi:
        return f"${lo:,.0f} – ${hi:,.0f}"
    return ""


# ── RapidAPI Indeed Scraper ───────────────────────────────────────────────────

async def _search_indeed_rapidapi(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    """Search Indeed via RapidAPI Indeed Scraper (border-line)."""
    import httpx

    _indeed_type = {
        "fulltime": "fulltime", "parttime": "parttime",
        "contract": "contract", "temporary": "temporary", "internship": "internship",
    }

    params: dict = {
        "query": query,
        "location": location or "",
        "page": "1",
        "country": country_code.upper() if country_code else "US",
        "sort": "date",
    }
    if job_type in _indeed_type:
        params["job_type"] = _indeed_type[job_type]

    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(
            "https://indeed-scraper-api.p.rapidapi.com/api/job",
            headers={
                "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "indeed-scraper-api.p.rapidapi.com",
            },
            params=params,
        )
        response.raise_for_status()
        data = response.json()

    items = data if isinstance(data, list) else data.get("jobs", data.get("data", data.get("results", [])))
    if not isinstance(items, list):
        items = []

    jobs = []
    for item in items:
        title = item.get("title") or item.get("job_title") or item.get("positionName") or ""
        company = item.get("company") or item.get("company_name") or item.get("employer") or ""
        if not title or not company:
            continue
        apply_url = item.get("url") or item.get("link") or item.get("job_url") or ""
        d = _extract_domain_from_url(apply_url)
        domain = d if d and not _is_job_board(d) else _guess_domain(company)
        jobs.append({
            "title": title,
            "company": company,
            "location": item.get("location") or item.get("job_location") or "",
            "description": item.get("description") or item.get("snippet") or "",
            "source": "indeed",
            "application_url": apply_url,
            "posted_date": item.get("date") or item.get("posted_at") or "",
            "salary_range": item.get("salary") or item.get("salary_range") or "",
            "job_type": _ensure_str(item.get("job_type") or item.get("employment_type")),
            "requirements": _extract_requirements(item.get("description") or ""),
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": domain,
        })
    return jobs[:limit]


# ── RapidAPI Glassdoor Real-Time ─────────────────────────────────────────────

async def _search_glassdoor_rapidapi(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    """Search Glassdoor via RapidAPI Glassdoor Real-Time."""
    import httpx

    params: dict = {
        "query": query,
        "location": location or "",
        "page": "1",
    }
    if country_code:
        params["country"] = country_code.upper()

    async with httpx.AsyncClient(timeout=25) as client:
        response = await client.get(
            "https://glassdoor-real-time.p.rapidapi.com/jobs/search",
            headers={
                "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
                "X-RapidAPI-Host": "glassdoor-real-time.p.rapidapi.com",
            },
            params=params,
        )
        response.raise_for_status()
        data = response.json()

    items = data if isinstance(data, list) else data.get("jobs", data.get("data", data.get("results", [])))
    if not isinstance(items, list):
        items = []

    jobs = []
    for item in items:
        title = item.get("title") or item.get("job_title") or item.get("jobTitle") or ""
        company = item.get("company") or item.get("company_name") or item.get("companyName") or item.get("employer_name") or ""
        if not title or not company:
            continue
        apply_url = item.get("url") or item.get("link") or item.get("job_url") or item.get("applyUrl") or ""
        d = _extract_domain_from_url(apply_url)
        domain = d if d and not _is_job_board(d) else _guess_domain(company)
        jobs.append({
            "title": title,
            "company": company,
            "location": item.get("location") or item.get("job_location") or "",
            "description": item.get("description") or item.get("snippet") or item.get("jobDescription") or "",
            "source": "glassdoor",
            "application_url": apply_url,
            "posted_date": item.get("date") or item.get("posted_at") or item.get("postedDate") or "",
            "salary_range": item.get("salary") or item.get("salary_range") or item.get("salaryRange") or "",
            "job_type": _ensure_str(item.get("job_type") or item.get("employment_type") or item.get("employmentType")),
            "requirements": _extract_requirements(item.get("description") or ""),
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": domain,
        })
    return jobs[:limit]


# ── Adzuna Official API ──────────────────────────────────────────────────────

async def _search_adzuna(
    query: str, location: Optional[str], limit: int, country_code: str = "us",
    job_type: Optional[str] = None,
) -> list[dict]:
    """Search jobs via Adzuna official API (free tier: 100 req/day)."""
    import httpx

    # Adzuna uses lowercase country codes in their URL path
    cc = (country_code or "us").lower()
    # Adzuna supports these country codes; fall back to 'us' for unsupported
    _adzuna_countries = {
        "us", "gb", "au", "ca", "de", "fr", "in", "nl", "br", "pl",
        "za", "nz", "sg", "at", "ch", "it", "es", "ru", "be", "mx",
    }
    if cc not in _adzuna_countries:
        cc = "us"

    _adzuna_type = {
        "fulltime": "full_time", "parttime": "part_time",
        "contract": "contract", "temporary": "contract",
        "internship": "full_time",
    }

    params: dict = {
        "app_id": settings.ADZUNA_APP_ID,
        "app_key": settings.ADZUNA_APP_KEY,
        "results_per_page": min(limit, 20),
        "what": query,
        "content-type": "application/json",
        "max_days_old": 14,
    }
    if location:
        params["where"] = location
    if job_type in _adzuna_type:
        params["full_time"] = "1" if job_type == "fulltime" else ""
        params["part_time"] = "1" if job_type == "parttime" else ""
        params["contract"] = "1" if job_type in ("contract", "temporary") else ""

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1",
            params=params,
        )
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data.get("results", []):
        title = item.get("title") or ""
        company_obj = item.get("company") or {}
        company = company_obj.get("display_name") or "" if isinstance(company_obj, dict) else str(company_obj)
        if not title or not company:
            continue
        apply_url = item.get("redirect_url") or item.get("adref") or ""
        d = _extract_domain_from_url(apply_url)
        domain = d if d and not _is_job_board(d) else _guess_domain(company)

        salary = ""
        sal_min = item.get("salary_min")
        sal_max = item.get("salary_max")
        if sal_min and sal_max:
            salary = f"${sal_min:,.0f} – ${sal_max:,.0f}"
        elif sal_min:
            salary = f"From ${sal_min:,.0f}"
        elif sal_max:
            salary = f"Up to ${sal_max:,.0f}"

        location_obj = item.get("location") or {}
        loc_parts = location_obj.get("display_name", "") if isinstance(location_obj, dict) else str(location_obj)

        jobs.append({
            "title": title,
            "company": company,
            "location": loc_parts,
            "description": item.get("description") or "",
            "source": "adzuna",
            "application_url": apply_url,
            "posted_date": item.get("created") or "",
            "salary_range": salary,
            "job_type": _ensure_str(item.get("contract_type") or item.get("contract_time")),
            "requirements": _extract_requirements(item.get("description") or ""),
            "matching_skills": [],
            "missing_skills": [],
            "company_domain": domain,
        })
    return jobs[:limit]


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
        # Strip markdown fences
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                stripped = part.strip()
                if stripped.startswith("json"):
                    stripped = stripped[4:].strip()
                if stripped.startswith("["):
                    content = stripped
                    break
        # Find JSON array bounds in case there is surrounding prose
        start = content.find("[")
        end = content.rfind("]")
        if start != -1 and end != -1 and end > start:
            content = content[start:end + 1]
        jobs = json.loads(content)
        if not isinstance(jobs, list):
            raise ValueError("LLM returned non-list JSON")
        for j in jobs:
            j.setdefault("matching_skills", [])
            j.setdefault("missing_skills", [])
            j.setdefault("company_domain", _guess_domain(j.get("company", "")))
        return jobs
    except Exception as e:
        logger.error("sample_job_generation_error", error=str(e))
        # Hard-coded fallback so the user always sees something meaningful
        loc = location or "Remote"
        return [
            {
                "title": query,
                "company": "Multiple Companies",
                "location": loc,
                "salary_range": "Competitive",
                "job_type": "Full-time",
                "description": f"We are looking for a talented {query} to join our team in {loc}.",
                "requirements": ["Relevant experience", "Strong communication skills", "Team player"],
                "source": "ai_generated",
                "posted_date": "Today",
                "application_url": "",
                "matching_skills": [],
                "missing_skills": [],
                "company_domain": "",
            }
        ]


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
