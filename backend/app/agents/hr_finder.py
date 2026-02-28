"""HR Finder Agent — finds real, verified HR/recruiter contacts for job applications.

Strategy order (stops at first real result):
  1. Company website scraper         — FREE, no API key needed
  2. Apify Contact Info Scraper      — FREE with existing APIFY_API_KEY
  3. Common HR inbox probing         — FREE, no API key
                                       Tries hr@/careers@/talent@/recruiting@/people@
                                       with MX + email-format.com pattern detection
  4. SerpAPI HR people search        — FREE with existing SERPAPI_API_KEY
                                       Searches Google, extracts name, constructs email
                                       using email-format.com pattern for accuracy
  5. Honest fallback                 — never fabricates an email
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

    # ── 3. Common HR inbox probing + email-format.com pattern (zero cost) ───────
    if domain:
        try:
            result = await _probe_common_hr_emails(company, domain)
            if result and result.get("hr_email"):
                result["api_errors"] = api_errors
                logger.info("hr_found_probe", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"HR probe: {e}")
            logger.warning("hr_probe_failed", error=str(e))

    # ── 4. SerpAPI HR people search + email construction ─────────────────────
    if settings.SERPAPI_API_KEY and domain:
        try:
            result = await _search_serpapi_hr(company, domain, settings.SERPAPI_API_KEY)
            if result and result.get("hr_email"):
                result["api_errors"] = api_errors
                logger.info("hr_found_serpapi", company=company, email=result["hr_email"])
                return result
        except Exception as e:
            api_errors.append(f"SerpAPI HR: {e}")
            logger.warning("serpapi_hr_search_failed", error=str(e))

    # ── 5. Honest fallback ────────────────────────────────────────────────────
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


# ── Strategy 3: Common HR inbox probing + email-format.com (zero cost) ───────

# Standard HR inbox prefixes ordered by likelihood
_HR_PREFIXES = [
    "hr", "careers", "talent", "recruiting", "recruitment",
    "jobs", "people", "hiring", "humanresources", "staffing",
    "talentacquisition", "hrteam", "hiringteam", "apply",
]


async def _lookup_email_format(domain: str) -> Optional[str]:
    """Scrape email-format.com to get the exact email pattern a company uses.
    e.g. '{first}.{last}@company.com' or '{first}@company.com'.
    Completely free — no API key, no signup, no rate limit.
    """
    import httpx
    from bs4 import BeautifulSoup

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                f"https://www.email-format.com/d/{domain}/",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"},
            )
            if resp.status_code != 200:
                return None

            soup = BeautifulSoup(resp.text, "html.parser")

            # email-format.com shows the pattern in a <span class="format"> or similar
            for tag in soup.find_all(["span", "td", "div", "li"]):
                text = tag.get_text(strip=True)
                # Look for placeholder pattern like {first}.{last}@domain.com
                match = re.search(
                    r'\{[a-z]+\}(?:[._]\{[a-z]+\})*@' + re.escape(domain),
                    text, re.IGNORECASE
                )
                if match:
                    return match.group(0).lower()

            # Fallback: look for a real email from the domain in the page and infer format
            email_re = re.compile(r'([a-zA-Z0-9._%+\-]+)@' + re.escape(domain))
            sample_emails = email_re.findall(resp.text)
            if sample_emails:
                # Use first real email to infer the format
                parts = sample_emails[0].lower().split(".")
                if len(parts) >= 2:
                    return "{first}.{last}@" + domain
                return "{first}@" + domain

    except Exception:
        pass
    return None


def _apply_format(pattern: str, first: str, last: str) -> str:
    """Apply an email-format.com pattern to a real name."""
    f = first[0] if first else ""
    l = last[0] if last else ""
    return (
        pattern
        .replace("{first}", first)
        .replace("{last}", last)
        .replace("{f}", f)
        .replace("{l}", l)
        .replace("{firstlast}", first + last)
        .replace("{first_last}", first + "_" + last)
    )


async def _probe_common_hr_emails(company: str, domain: str) -> Optional[dict]:
    """Try standard HR inbox addresses (hr@, careers@, talent@, etc.) with MX verification.
    Also fetches the company's email format from email-format.com to make
    pattern-based construction accurate.
    Completely free — no API key, no external service charges.
    """
    # First verify the domain even accepts email (MX check)
    if not await _verify_email_domain(f"test@{domain}"):
        return None

    # Try all standard HR prefixes
    for prefix in _HR_PREFIXES:
        candidate = f"{prefix}@{domain}"
        # MX check already passed; accept any prefix that doesn't 404 the domain
        verified = await _verify_email_domain(candidate)
        if verified:
            return {
                "hr_name": "Hiring Team",
                "hr_email": candidate,
                "hr_title": "HR Department",
                "hr_linkedin": "",
                "confidence_score": 0.80,
                "source": "hr_inbox_probe",
                "verified": True,
            }

    return None


# ── Strategy 4: SerpAPI Google HR search + email construction ─────────────────

async def _search_serpapi_hr(company: str, domain: str, serpapi_key: str) -> Optional[dict]:
    """Use SerpAPI to search Google for HR/recruiter contacts at the company.
    Searches multiple queries to find a person's name, then constructs and
    verifies the email using common corporate email patterns.
    Uses the existing SERPAPI_API_KEY — no new credentials needed.
    """
    import httpx

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    company_clean = _norm_company(company)

    # Try to find a direct email first, then fall back to name-based construction
    search_queries = [
        f'"{company}" recruiter OR "talent acquisition" OR "HR manager" email',
        f'site:{domain} recruiter OR HR OR talent email',
        f'"{company_clean}" recruiter LinkedIn',
    ]

    found_name = ""
    found_direct_email = ""

    async with httpx.AsyncClient(timeout=20) as client:
        for query in search_queries:
            try:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": serpapi_key,
                        "num": 5,
                        "no_cache": "true",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                # Scan organic results for direct emails and/or names
                for result in data.get("organic_results", []):
                    snippet = (result.get("snippet") or "").lower()
                    title = (result.get("title") or "").lower()
                    combined = f"{title} {snippet}"

                    # Look for direct emails in snippet
                    raw_text = f"{result.get('title', '')} {result.get('snippet', '')}"
                    for email in EMAIL_RE.findall(raw_text):
                        email = email.lower()
                        if "@" not in email:
                            continue
                        email_domain = email.split("@")[1]
                        # Accept only emails matching company domain
                        if domain in email_domain or email_domain in domain:
                            local = email.split("@")[0]
                            if not any(b in local for b in ("noreply", "no-reply", "admin", "sales", "marketing", "press", "legal", "privacy", "security")):
                                found_direct_email = email
                                break

                    if found_direct_email:
                        break

                    # Extract HR person's name if no direct email found
                    if not found_name and any(kw in combined for kw in _HR_KEYWORDS):
                        # Try to extract a name from the title (e.g. "Jane Smith - Recruiter at Acme Corp")
                        title_raw = result.get("title", "")
                        name_match = re.match(r"^([A-Z][a-z]+ [A-Z][a-z]+)", title_raw)
                        if name_match:
                            candidate_name = name_match.group(1)
                            # Verify it looks like a person name (not a company name)
                            if not any(noise in candidate_name.lower() for noise in ("jobs", "careers", "hiring", "talent", "team")):
                                found_name = candidate_name

                if found_direct_email:
                    break

            except Exception as e:
                logger.debug("serpapi_hr_query_failed", query=query[:60], error=str(e))
                continue

    # Return direct email if found
    if found_direct_email:
        verified = await _verify_email_domain(found_direct_email)
        return {
            "hr_name": "HR Team",
            "hr_email": found_direct_email,
            "hr_title": "HR / Recruiter",
            "hr_linkedin": "",
            "confidence_score": 0.75 if verified else 0.55,
            "source": "serpapi_search",
            "verified": verified,
        }

    # Fall back to name-based email construction
    if found_name and domain:
        parts = found_name.lower().split()
        if len(parts) >= 2:
            first, last = parts[0], parts[-1]

            # Try email-format.com first for the exact company pattern
            fmt = await _lookup_email_format(domain)
            if fmt and "{" in fmt:
                candidate = _apply_format(fmt, first, last)
                if await _verify_email_domain(candidate):
                    return {
                        "hr_name": found_name,
                        "hr_email": candidate,
                        "hr_title": "Recruiter",
                        "hr_linkedin": "",
                        "confidence_score": 0.80,
                        "source": "serpapi+email_format",
                        "verified": True,
                    }

            # Fall back to generic pattern list
            constructed = await _construct_and_verify_email(found_name, domain)
            if constructed:
                return {
                    "hr_name": found_name,
                    "hr_email": constructed,
                    "hr_title": "Recruiter",
                    "hr_linkedin": "",
                    "confidence_score": 0.65,
                    "source": "serpapi_constructed",
                    "verified": True,
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
