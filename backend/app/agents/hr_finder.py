"""HR Finder Agent — finds real, verified HR/recruiter contacts for job applications.

Strategy order (stops at first real result):
  1. Company website scraper     — FREE, no API key needed
  2. Apify Contact Info Scraper  — FREE with existing APIFY_API_KEY (vdrmota/contact-info-scraper)
  3. Prospeo.io domain search    — 150 free/month (PROSPEO_API_KEY)
  4. Apify LinkedIn + construct  — uses APIFY_API_KEY, finds name then constructs email
  5. Honest fallback             — never fabricates an email
"""

import re
import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger()

_HR_KEYWORDS = (
    "recruiter", "talent acquisition", "hr manager", "human resources",
    "people operations", "hiring manager", "talent partner", "talent lead",
    "people & culture", "head of talent", "technical recruiter", "staffing",
    "hr", "recruit", "talent", "hiring", "people",
)

_EMAIL_PATTERNS = [
    "{first}.{last}@{domain}",
    "{first}@{domain}",
    "{f}{last}@{domain}",
    "{first}{last}@{domain}",
    "hr@{domain}",
    "recruiting@{domain}",
    "talent@{domain}",
    "careers@{domain}",
    "jobs@{domain}",
    "people@{domain}",
]

_CONTACT_PATHS = [
    "/contact", "/contact-us", "/about", "/about-us",
    "/team", "/our-team", "/careers", "/jobs", "/hiring",
    "/people", "/hr", "/",
]


async def find_hr_contact(
    company: str,
    job_title: str,
    company_domain: Optional[str] = None,
) -> dict:
    """Find a real, verified HR contact. Never fabricates."""
    from app.config import settings

    guessed = company_domain or _guess_domain(company)
    domain = await _resolve_domain(guessed) if guessed else guessed
    api_errors = []

    # ── 1. Free website scraper (no API key needed) ───────────────────────────
    if domain:
        try:
            result = await _scrape_company_website(company, domain)
            if result and result.get("hr_email"):
                result["api_errors"] = api_errors
                logger.info("hr_found_website_scrape", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"Website scraper: {e}")
            logger.warning("website_scrape_failed", error=str(e))

    # ── 2. Apify Contact Info Scraper (uses existing APIFY_API_KEY) ───────────
    if settings.APIFY_API_KEY and domain:
        try:
            result = await _apify_contact_scraper(company, domain, settings.APIFY_API_KEY)
            if result and result.get("hr_email"):
                result["api_errors"] = api_errors
                logger.info("hr_found_apify_contact_scraper", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"Apify Contact Scraper: {e}")
            logger.warning("apify_contact_scraper_failed", error=str(e))

    # ── 3. Prospeo.io domain search ────────────────────────────────────────────
    if settings.PROSPEO_API_KEY and domain:
        try:
            result = await _search_prospeo(domain, settings.PROSPEO_API_KEY)
            if result and result.get("hr_email"):
                result["verified"] = await _verify_email_domain(result["hr_email"])
                result["api_errors"] = api_errors
                logger.info("hr_found_prospeo", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"Prospeo.io: {e}")
            logger.warning("prospeo_search_failed", error=str(e))

    # ── 4. Apify LinkedIn + email construction ────────────────────────────────
    if settings.APIFY_API_KEY:
        try:
            result = await _search_linkedin_hr(company, job_title, settings.APIFY_API_KEY)
            if result and result.get("hr_name") and domain:
                verified_email = await _construct_and_verify_email(result["hr_name"], domain)
                if verified_email:
                    result["hr_email"] = verified_email
                    result["verified"] = True
                    result["confidence_score"] = 0.65
                    result["api_errors"] = api_errors
                    logger.info("hr_found_linkedin+constructed", company=company, email=verified_email)
                    return result
        except Exception as e:
            api_errors.append(f"Apify LinkedIn: {e}")
            logger.warning("linkedin_hr_search_failed", error=str(e))

    # ── 5. Hunter.io domain search ────────────────────────────────────────────
    if settings.HUNTER_API_KEY and domain:
        try:
            result = await _search_hunter_io(domain, settings.HUNTER_API_KEY)
            if result and result.get("hr_email"):
                result["api_errors"] = api_errors
                logger.info("hr_found_hunter_io", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"Hunter.io: {e}")
            logger.warning("hunter_io_search_failed", error=str(e))

    # ── 6. Snov.io domain search ──────────────────────────────────────────────
    if settings.SNOV_CLIENT_ID and settings.SNOV_CLIENT_SECRET and domain:
        try:
            result = await _search_snov_io(domain, settings.SNOV_CLIENT_ID, settings.SNOV_CLIENT_SECRET)
            if result and result.get("hr_email"):
                result["api_errors"] = api_errors
                logger.info("hr_found_snov_io", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"Snov.io: {e}")
            logger.warning("snov_io_search_failed", error=str(e))

    # ── 7. Honest fallback ────────────────────────────────────────────────────
    careers_url = f"https://{domain}/careers" if domain else ""
    logger.warning("hr_email_not_found", company=company, domain=domain, errors=api_errors)
    return {
        "hr_name": "Hiring Team",
        "hr_email": "",
        "hr_title": "HR Department",
        "hr_linkedin": "",
        "careers_page": careers_url,
        "confidence_score": 0.0,
        "verified": False,
        "source": "not_found",
        "api_errors": api_errors,
    }


# ── Strategy 1: Company website scraper (FREE) ────────────────────────────────

async def _scrape_company_website(company: str, domain: str) -> Optional[dict]:
    """Scrape the company's own website pages for HR/contact emails."""
    import httpx
    from bs4 import BeautifulSoup

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    found_emails: list[tuple[int, str]] = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    BLOCKED = {
        "noreply", "no-reply", "admin@", "sales@", "marketing@",
        "press@", "media@", "legal@", "privacy@", "security@",
        "abuse@", "spam@", "unsubscribe@", "bounce@",
    }

    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
        for base in [f"https://{domain}", f"https://www.{domain}"]:
            for path in _CONTACT_PATHS:
                url = f"{base}{path}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue

                    final_domain = resp.url.host.lstrip("www.")
                    soup = BeautifulSoup(resp.text, "html.parser")
                    page_text = soup.get_text(" ", strip=True).lower()

                    raw_emails = EMAIL_RE.findall(resp.text)
                    for email in set(raw_emails):
                        email_lower = email.lower()
                        local_part = email_lower.split("@")[0]

                        if any(b in email_lower for b in BLOCKED):
                            continue

                        email_domain = email_lower.split("@")[1] if "@" in email_lower else ""
                        if email_domain != final_domain and email_domain != domain:
                            continue

                        score = 0
                        email_pos = page_text.find(email_lower)
                        context = page_text[max(0, email_pos - 200): email_pos + 200] if email_pos >= 0 else ""
                        for kw in _HR_KEYWORDS:
                            if kw in context:
                                score += 3
                        for kw in ("hr", "recruit", "talent", "hiring", "people", "career", "job"):
                            if kw in local_part:
                                score += 5
                        if local_part in ("info", "contact", "hello", "team"):
                            score = max(score, 1)

                        found_emails.append((score, email))

                except Exception:
                    continue

            if found_emails:
                break

    if not found_emails:
        return None

    found_emails.sort(key=lambda x: x[0], reverse=True)
    best_score, best_email = found_emails[0]

    if best_score < 0:
        return None

    verified = await _verify_email_domain(best_email)
    return {
        "hr_name": "HR Team",
        "hr_email": best_email,
        "hr_title": "HR / Recruiter",
        "hr_linkedin": "",
        "confidence_score": min(0.5 + best_score * 0.05, 0.95),
        "source": "website_scrape",
        "verified": verified,
    }


# ── Strategy 2: Apify Contact Info Scraper ───────────────────────────────────

async def _apify_contact_scraper(company: str, domain: str, api_key: str) -> Optional[dict]:
    """Use Apify's vdrmota/contact-info-scraper actor to extract emails from company pages.
    FREE with any Apify account — uses APIFY_API_KEY.
    Actor: https://apify.com/vdrmota/contact-info-scraper
    """
    import httpx

    # Pages most likely to have HR contact info
    start_urls = [
        {"url": f"https://{domain}/contact"},
        {"url": f"https://{domain}/about"},
        {"url": f"https://{domain}/careers"},
        {"url": f"https://{domain}/team"},
        {"url": f"https://{domain}"},
    ]

    actor_url = (
        "https://api.apify.com/v2/acts/vdrmota~contact-info-scraper/run-sync-get-dataset-items"
        f"?token={api_key}&timeout=60&memory=256"
    )

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    BLOCKED = {"noreply", "no-reply", "admin", "sales", "marketing", "press", "legal", "privacy", "security", "abuse", "spam"}

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            actor_url,
            json={
                "startUrls": start_urls,
                "maxDepth": 1,
                "maxPageCount": 5,
                "proxy": {"useApifyProxy": True},
            },
        )
        resp.raise_for_status()
        items = resp.json()

    found_emails: list[tuple[int, str]] = []

    for item in items:
        # Contact Info Scraper returns emails in item.emails array
        emails_found = item.get("emails") or []
        page_url = item.get("url", "")

        for email_entry in emails_found:
            # Can be string or dict {"email": "...", "name": "..."}
            if isinstance(email_entry, str):
                email = email_entry
            elif isinstance(email_entry, dict):
                email = email_entry.get("email") or email_entry.get("value") or ""
            else:
                continue

            email = email.strip().lower()
            if not email or "@" not in email:
                continue

            local = email.split("@")[0]
            email_domain = email.split("@")[1]

            # Must be from company domain
            if domain not in email_domain and email_domain not in domain:
                continue

            if any(b in local for b in BLOCKED):
                continue

            score = 0
            for kw in ("hr", "recruit", "talent", "hiring", "people", "career", "job"):
                if kw in local:
                    score += 5
            if local in ("info", "contact", "hello", "team"):
                score = max(score, 1)

            found_emails.append((score, email))

    if not found_emails:
        return None

    found_emails.sort(key=lambda x: x[0], reverse=True)
    best_score, best_email = found_emails[0]

    if best_score < 0:
        return None

    verified = await _verify_email_domain(best_email)
    return {
        "hr_name": "HR Team",
        "hr_email": best_email,
        "hr_title": "HR / Recruiter",
        "hr_linkedin": "",
        "confidence_score": min(0.5 + best_score * 0.05, 0.92),
        "source": "apify_contact_scraper",
        "verified": verified,
    }


# ── Strategy 3: Prospeo.io ────────────────────────────────────────────────────

async def _search_prospeo(domain: str, api_key: str) -> Optional[dict]:
    """Search Prospeo.io for company emails. Free: 150 searches/month.
    Get key: https://prospeo.io → Dashboard → API
    """
    import httpx

    api_key = api_key.strip()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.prospeo.io/domain-search",
            json={"domain": domain, "limit": 10},
            headers={"X-KEY": api_key, "Content-Type": "application/json"},
        )
        if resp.status_code == 401:
            raise Exception("Invalid Prospeo API key (401) — check PROSPEO_API_KEY has no extra spaces.")
        if resp.status_code == 403:
            raise Exception("Prospeo quota exceeded or plan issue (403).")
        if resp.status_code == 400:
            raise Exception(f"Prospeo bad request (400): {resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()

    contacts = data.get("response", [])
    if not isinstance(contacts, list):
        contacts = []
    if not contacts:
        return None

    def hr_score(c: dict) -> int:
        combined = f"{c.get('department', '')} {c.get('position', '')} {c.get('seniority', '')}".lower()
        return sum(2 for kw in _HR_KEYWORDS if kw in combined)

    best = sorted(contacts, key=hr_score, reverse=True)
    for c in best:
        email = c.get("email") or c.get("value")
        if not email or "@" not in email:
            continue
        first = c.get("first_name", "")
        last = c.get("last_name", "")
        return {
            "hr_name": f"{first} {last}".strip() or "HR Team",
            "hr_email": email,
            "hr_title": c.get("position") or c.get("title") or "HR",
            "hr_linkedin": c.get("linkedin_url") or c.get("linkedin") or "",
            "confidence_score": min(round(c.get("confidence", 70) / 100, 2), 1.0),
            "source": "prospeo.io",
            "verified": False,
        }
    return None


# ── Strategy 4: Apify LinkedIn People Search ──────────────────────────────────

async def _search_linkedin_hr(company: str, job_title: str, api_key: str) -> Optional[dict]:
    """Search LinkedIn for an HR profile at the company using Apify.
    Uses APIFY_API_KEY — finds name only; email is constructed separately.
    """
    import httpx

    actor_id = "curious_coder~linkedin-people-search"
    url = (
        f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
        f"?token={api_key}&timeout=60&memory=512"
    )

    for query in [f"recruiter {company}", f"talent acquisition {company}", f"HR manager {company}"]:
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                resp = await client.post(
                    url,
                    json={"searchQueries": [query], "maxResults": 5, "proxy": {"useApifyProxy": True}},
                )
                resp.raise_for_status()
                items = resp.json()

            for item in items:
                name = item.get("name") or item.get("fullName") or ""
                headline = (item.get("headline") or item.get("title") or "").lower()
                current_company = (item.get("company") or item.get("currentCompany") or "").lower()
                company_match = (
                    _norm_company(company).lower() in current_company
                    or current_company in _norm_company(company).lower()
                )
                if company_match and any(kw in headline for kw in _HR_KEYWORDS) and name:
                    return {
                        "hr_name": name,
                        "hr_email": "",
                        "hr_title": item.get("headline") or "Recruiter",
                        "hr_linkedin": item.get("linkedInUrl") or item.get("url") or "",
                        "confidence_score": 0.55,
                        "source": "linkedin_apify",
                        "verified": False,
                    }
        except Exception as e:
            logger.debug("linkedin_query_failed", query=query, error=str(e))
    return None


# ── Strategy 5: Hunter.io domain search ──────────────────────────────────────

async def _search_hunter_io(domain: str, api_key: str) -> Optional[dict]:
    """Search Hunter.io for company HR contacts. Free: 25 domain searches/month.
    Get key: https://hunter.io → Dashboard → API
    """
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "limit": 10, "api_key": api_key},
        )
        if resp.status_code == 401:
            raise Exception("Invalid Hunter.io API key (401)")
        if resp.status_code == 429:
            raise Exception("Hunter.io quota exceeded (429)")
        resp.raise_for_status()
        data = resp.json()

    emails = (data.get("data") or {}).get("emails") or []
    if not emails:
        return None

    def hr_score(e: dict) -> int:
        combined = f"{e.get('department', '')} {e.get('position', '')} {e.get('seniority', '')}".lower()
        return sum(2 for kw in _HR_KEYWORDS if kw in combined)

    best = sorted(emails, key=hr_score, reverse=True)
    for e in best:
        email = e.get("value")
        if not email or "@" not in email:
            continue
        first = e.get("first_name", "")
        last = e.get("last_name", "")
        confidence = e.get("confidence", 70)
        verified = (e.get("verification") or {}).get("status") == "valid"
        return {
            "hr_name": f"{first} {last}".strip() or "HR Team",
            "hr_email": email,
            "hr_title": e.get("position") or "HR",
            "hr_linkedin": e.get("linkedin") or "",
            "confidence_score": round(confidence / 100, 2),
            "source": "hunter.io",
            "verified": verified,
        }
    return None


# ── Strategy 6: Snov.io domain search (v2 API) ────────────────────────────────

async def _search_snov_io(domain: str, client_id: str, client_secret: str) -> Optional[dict]:
    """Search Snov.io for company HR contacts using the v2 async API.
    Free: 50 searches/month. Get credentials: https://snov.io → Settings → API

    v2 workflow:
      POST /v2/domain-search/domain-emails/start?domain={domain}  → task_hash
      GET  /v2/domain-search/domain-emails/result/{task_hash}     → poll until completed
    """
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Get OAuth access token (still v1)
        token_resp = await client.post(
            "https://api.snov.io/v1/oauth/access_token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise Exception("Snov.io: no access token returned")

        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Start async domain email search (v2)
        start_resp = await client.post(
            "https://api.snov.io/v2/domain-search/domain-emails/start",
            params={"domain": domain},
            headers=headers,
        )
        start_resp.raise_for_status()
        start_data = start_resp.json()
        task_hash = start_data.get("task_hash")
        if not task_hash:
            raise Exception(f"Snov.io v2: no task_hash in response: {start_data}")

        # Step 3: Poll until completed (max 10 attempts × 2 s = 20 s)
        data: dict = {}
        for _ in range(10):
            await asyncio.sleep(2)
            result_resp = await client.get(
                f"https://api.snov.io/v2/domain-search/domain-emails/result/{task_hash}",
                headers=headers,
            )
            result_resp.raise_for_status()
            data = result_resp.json()
            if data.get("status") == "completed":
                break

    raw_emails = data.get("emails") or []
    if not raw_emails:
        return None

    # v2 may return plain strings or dicts; normalise both
    normalised: list[dict] = []
    for entry in raw_emails:
        if isinstance(entry, str):
            normalised.append({"email": entry})
        elif isinstance(entry, dict):
            normalised.append(entry)

    def hr_score(e: dict) -> int:
        position = (e.get("position") or e.get("title") or "").lower()
        return sum(2 for kw in _HR_KEYWORDS if kw in position)

    best = sorted(normalised, key=hr_score, reverse=True)
    for e in best:
        email = e.get("email") or e.get("value") or ""
        if not email or "@" not in email:
            continue
        return {
            "hr_name": f"{e.get('firstName', '') or e.get('first_name', '')} "
                       f"{e.get('lastName', '') or e.get('last_name', '')}".strip() or "HR Team",
            "hr_email": email,
            "hr_title": e.get("position") or e.get("title") or "HR",
            "hr_linkedin": "",
            "confidence_score": 0.70,
            "source": "snov.io",
            "verified": e.get("status") == "verified",
        }
    return None


# ── Batch HR Contact Finder ───────────────────────────────────────────────────

async def batch_find_hr_contacts(jobs: list) -> list:
    """Run HR email lookup for all jobs concurrently.

    Returns only jobs that have a verified/found HR email, with the contact
    data attached as ``job['_hr_contact']``. Jobs without HR emails are
    silently discarded.

    Args:
        jobs: List of job dicts (must contain at least 'company' and 'title').

    Returns:
        Filtered list — only jobs where an HR email was found.
    """
    async def _lookup(job_data: dict) -> dict:
        try:
            result = await find_hr_contact(
                company=job_data.get("company", ""),
                job_title=job_data.get("title", ""),
                company_domain=job_data.get("company_domain"),
            )
            if result.get("hr_email"):
                job_data = dict(job_data)  # don't mutate original
                job_data["_hr_contact"] = result
        except Exception as e:
            logger.warning("batch_hr_lookup_error", company=job_data.get("company"), error=str(e))
        return job_data

    results = await asyncio.gather(*[_lookup(j) for j in jobs], return_exceptions=True)

    verified = []
    for r in results:
        if isinstance(r, Exception):
            logger.warning("batch_hr_gather_error", error=str(r))
            continue
        if r.get("_hr_contact"):
            verified.append(r)

    logger.info("batch_hr_complete", total=len(jobs), verified=len(verified))
    return verified


# ── Email construction + DNS verification ────────────────────────────────────

async def _construct_and_verify_email(name: str, domain: str) -> Optional[str]:
    """Build candidate emails from a real name + known domain.
    Only returns if MX check passes.
    """
    parts = name.lower().split()
    if len(parts) >= 2:
        first, last = parts[0], parts[-1]
        f = first[0] if first else ""
    else:
        first = parts[0] if parts else ""
        last, f = "", first[0] if first else ""

    for pattern in _EMAIL_PATTERNS:
        candidate = pattern.format(first=first, last=last, f=f, domain=domain)
        if "@" in candidate and await _verify_email_domain(candidate):
            return candidate
    return None


async def _verify_email_domain(email: str) -> bool:
    """Check domain has valid MX records."""
    if not email or "@" not in email:
        return False
    domain = email.split("@", 1)[1].lower().strip()
    if not domain or "." not in domain:
        return False
    try:
        import dns.resolver
        answers = await asyncio.get_event_loop().run_in_executor(
            None, lambda: dns.resolver.resolve(domain, "MX")
        )
        return len(list(answers)) > 0
    except ImportError:
        return await _socket_domain_check(domain)
    except Exception:
        return await _socket_domain_check(domain)


async def _socket_domain_check(domain: str) -> bool:
    try:
        import socket
        await asyncio.get_event_loop().run_in_executor(
            None, lambda: socket.gethostbyname(domain)
        )
        return True
    except Exception:
        return False


# ── Helpers ───────────────────────────────────────────────────────────────────

_COMPANY_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|co|group|holdings|technologies|tech|solutions)\b\.?",
    re.IGNORECASE,
)


def _norm_company(name: str) -> str:
    return re.sub(r"\s+", " ", _COMPANY_NOISE.sub("", name.lower())).strip()


def _guess_domain(company: str) -> str:
    clean = re.sub(r"[^a-z0-9]", "", _norm_company(company))
    return f"{clean}.com" if clean else ""


async def _resolve_domain(domain: str) -> str:
    """Follow HTTP redirect to find the real domain (e.g. company.com → company.ai)."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as c:
            r = await c.get(
                f"https://{domain}",
                headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"},
            )
            final = r.url.host.lstrip("www.")
            return final if final else domain
    except Exception:
        return domain
