"""
Digital FTE - Job Search Tools
Wrappers for SerpAPI (Google Jobs) and RapidAPI JSearch.
"""

import httpx
import structlog
from typing import List, Optional

from app.config import settings

logger = structlog.get_logger()


async def search_serpapi_jobs(
    query: str,
    location: str = "",
    num_results: int = 10,
) -> List[dict]:
    """
    Search Google Jobs via SerpAPI.
    Returns normalized job listings.
    """
    if not settings.SERPAPI_API_KEY:
        logger.warning("serpapi_key_missing", msg="Skipping SerpAPI search")
        return []

    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": settings.SERPAPI_API_KEY,
        "num": str(num_results),
    }
    if location:
        params["location"] = location

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get("https://serpapi.com/search", params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs_results = data.get("jobs_results", [])
        normalized = []
        for j in jobs_results:
            normalized.append({
                "title": j.get("title", ""),
                "company": j.get("company_name", ""),
                "location": j.get("location", ""),
                "description": j.get("description", ""),
                "job_type": _extract_job_type(j),
                "salary_range": j.get("detected_extensions", {}).get("salary", ""),
                "posted_date": j.get("detected_extensions", {}).get("posted_at", ""),
                "application_url": j.get("share_link", j.get("related_links", [{}])[0].get("link", "") if j.get("related_links") else ""),
                "source": "google_jobs",
                "requirements": [],
                "nice_to_have": [],
                "responsibilities": [],
            })

        logger.info("serpapi_search_complete", count=len(normalized))
        return normalized

    except Exception as e:
        logger.error("serpapi_search_failed", error=str(e))
        return []


async def search_jsearch_jobs(
    query: str,
    location: str = "",
    num_results: int = 10,
    remote_only: bool = False,
) -> List[dict]:
    """
    Search jobs via RapidAPI JSearch API.
    Returns normalized job listings.
    """
    if not settings.RAPIDAPI_KEY:
        logger.warning("rapidapi_key_missing", msg="Skipping JSearch")
        return []

    params = {
        "query": f"{query} {location}".strip(),
        "page": "1",
        "num_pages": "1",
    }
    if remote_only:
        params["remote_jobs_only"] = "true"

    headers = {
        "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        jobs_data = data.get("data", [])[:num_results]
        normalized = []
        for j in jobs_data:
            normalized.append({
                "title": j.get("job_title", ""),
                "company": j.get("employer_name", ""),
                "location": f"{j.get('job_city', '')}, {j.get('job_state', '')}, {j.get('job_country', '')}".strip(", "),
                "description": j.get("job_description", ""),
                "job_type": j.get("job_employment_type", ""),
                "salary_range": _format_salary(j),
                "posted_date": j.get("job_posted_at_datetime_utc", ""),
                "application_url": j.get("job_apply_link", ""),
                "source": "jsearch",
                "requirements": j.get("job_required_skills") or [],
                "nice_to_have": [],
                "responsibilities": [],
            })

        logger.info("jsearch_search_complete", count=len(normalized))
        return normalized

    except Exception as e:
        logger.error("jsearch_search_failed", error=str(e))
        return []


async def search_all_sources(
    query: str,
    location: str = "",
    num_results: int = 10,
) -> List[dict]:
    """Search all available job sources and merge results."""
    import asyncio

    tasks = [
        search_serpapi_jobs(query, location, num_results),
        search_jsearch_jobs(query, location, num_results),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)

    # Deduplicate by title + company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = (job["title"].lower().strip(), job["company"].lower().strip())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    logger.info("all_sources_merged", total=len(unique_jobs))
    return unique_jobs[:num_results * 2]  # Allow more results from multi-source


def _extract_job_type(job_data: dict) -> str:
    """Extract job type from SerpAPI extensions."""
    exts = job_data.get("detected_extensions", {})
    if exts.get("work_from_home"):
        return "remote"
    schedule = exts.get("schedule_type", "")
    return schedule.lower() if schedule else "full-time"


def _format_salary(job_data: dict) -> str:
    """Format salary range from JSearch data."""
    min_sal = job_data.get("job_min_salary")
    max_sal = job_data.get("job_max_salary")
    currency = job_data.get("job_salary_currency", "USD")
    period = job_data.get("job_salary_period", "")

    if min_sal and max_sal:
        return f"{currency} {min_sal:,.0f} - {max_sal:,.0f} {period}".strip()
    elif min_sal:
        return f"{currency} {min_sal:,.0f}+ {period}".strip()
    return ""
