"""HR Finder Agent — finds verified HR/recruiter contacts for job applications.

Strategy order (stops only when confident contacts are found):
  1. Hunter.io Domain Search (HR department)         — HUNTER_API_KEY
  2. Hunter.io Domain Search (Executive/Management)  — HUNTER_API_KEY
  3. Hunter.io Domain Search (broad + scoring)       — HUNTER_API_KEY
  4. Company website scraper                         — FREE
  5. Apify Contact Info Scraper                      — APIFY_API_KEY
  6. Prospeo Search + Enrich Person                  — PROSPEO_API_KEY
  7. SerpAPI Google HR search                        — SERPAPI_API_KEY
  8. Pattern prefix fallback (with Hunter Verifier)  — HUNTER_API_KEY / FREE

Multi-email design:
  Every strategy contributes to a ranked list of contacts across four roles:
    - "hr"         HR / recruiter / talent acquisition
    - "management" Head of dept / department manager
    - "executive"  CEO / C-level / VP
    - "generic"    info@, contact@, company-level generic inboxes
    - "pattern"    constructed fallback addresses (hr@, careers@, …)

  The return dict always includes:
    hr_email       — single best choice (backward compat)
    all_recipients — list of {email, name, role, confidence, source}
                     ordered by priority; may include pattern fallbacks

Send strategy (used by send_to_all_recipients):
  - If ANY real contacts found (non-pattern): send to ALL of them
    grouped as: hr → management → executive → generic
  - If ONLY pattern fallbacks: send to verified/accept_all patterns (top 3)
"""

import re
import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger()

# ── HR keyword scoring ────────────────────────────────────────────────────────
_HR_KEYWORDS = (
    "recruiter", "talent acquisition", "hr manager", "human resources",
    "people operations", "hiring manager", "talent partner", "talent lead",
    "people & culture", "head of talent", "technical recruiter", "staffing",
    "hr", "recruit", "talent", "hiring", "people",
)

_EXEC_KEYWORDS = (
    "ceo", "chief executive", "coo", "cto", "founder", "co-founder",
    "president", "managing director", "executive director",
)

_MGMT_KEYWORDS = (
    "head of", "director of", "vp of", "vice president", "department head",
    "manager", "lead",
)

# ── Pattern fallback prefixes ─────────────────────────────────────────────────
# Ordered by likelihood of reaching an actual human
_FALLBACK_PREFIXES = [
    ("hr",              "HR Department",       "hr"),
    ("careers",         "Careers Team",        "hr"),
    ("talent",          "Talent Acquisition",  "hr"),
    ("recruiting",      "Recruiting Team",     "hr"),
    ("recruitment",     "Recruitment",         "hr"),
    ("jobs",            "Jobs Team",           "hr"),
    ("people",          "People & Culture",    "hr"),
    ("hiring",          "Hiring Team",         "hr"),
    ("apply",           "Applications",        "hr"),
    ("info",            "General Enquiries",   "generic"),
    ("contact",         "Contact",             "generic"),
    ("hello",           "General",             "generic"),
]

_CONTACT_PATHS = [
    "/contact", "/contact-us", "/about", "/about-us",
    "/team", "/our-team", "/careers", "/jobs", "/hiring",
    "/people", "/hr", "/",
]

# Prefixes we run Hunter Email Verifier on (saves credits vs verifying all)
_VERIFY_PREFIXES = {"hr", "careers", "talent", "recruiting", "jobs"}


# ── Public interface ──────────────────────────────────────────────────────────

async def find_hr_contact(
    company: str,
    job_title: str,
    company_domain: Optional[str] = None,
    user_id: str = "unknown",
) -> dict:
    """Find HR contacts and emit real-time stream events."""
    from app.core.event_bus import event_bus

    await event_bus.emit(user_id, "hr_stream", {
        "phase": "searching",
        "company": company,
        "job_title": job_title,
    })
    result = await _find_hr_contact_impl(company, job_title, company_domain)
    found = bool(result.get("hr_email"))
    await event_bus.emit(user_id, "hr_stream", {
        "phase": "found" if found else "not_found",
        "company": company,
        "job_title": job_title,
        "email": result.get("hr_email", ""),
        "total_found": len(result.get("all_recipients", [])),
    })
    return result


async def _find_hr_contact_impl(
    company: str,
    job_title: str,
    company_domain: Optional[str] = None,
) -> dict:
    """Find verified HR contacts. Returns all discovered recipients."""
    from app.config import settings

    guessed = company_domain or _guess_domain(company)
    domain = await _resolve_domain(guessed) if guessed else guessed
    api_errors = []

    # Accumulated contacts across all strategies.
    # Each entry: {email, name, title, role, confidence, source}
    all_contacts: list[dict] = []

    # ── 1. Hunter.io Domain Search (HR department) ─────────────────────────
    if settings.HUNTER_API_KEY and domain:
        try:
            contacts = await _hunter_domain_search(
                domain, settings.HUNTER_API_KEY,
                department="hr", company=company,
            )
            all_contacts.extend(contacts)
            logger.info("hunter_hr_dept", company=company, found=len(contacts))
        except Exception as e:
            api_errors.append(f"Hunter HR dept: {e}")
            logger.warning("hunter_hr_dept_failed", error=str(e))

    # ── 2. Hunter.io Domain Search (Executive + Management depts) ─────────
    if settings.HUNTER_API_KEY and domain:
        try:
            mgmt_contacts = await _hunter_domain_search(
                domain, settings.HUNTER_API_KEY,
                department="management", company=company,
            )
            exec_contacts = await _hunter_domain_search(
                domain, settings.HUNTER_API_KEY,
                department="executive", company=company,
            )
            all_contacts.extend(mgmt_contacts)
            all_contacts.extend(exec_contacts)
            logger.info(
                "hunter_exec_mgmt", company=company,
                found=len(mgmt_contacts) + len(exec_contacts),
            )
        except Exception as e:
            api_errors.append(f"Hunter exec/mgmt: {e}")
            logger.warning("hunter_exec_failed", error=str(e))

    # ── 3. Hunter.io Domain Search (broad — catch generic company emails) ─
    if settings.HUNTER_API_KEY and domain and not _has_hr_contact(all_contacts):
        try:
            contacts = await _hunter_domain_search(
                domain, settings.HUNTER_API_KEY,
                department=None, company=company,
            )
            all_contacts.extend(contacts)
            logger.info("hunter_broad", company=company, found=len(contacts))
        except Exception as e:
            api_errors.append(f"Hunter broad: {e}")
            logger.warning("hunter_broad_failed", error=str(e))

    # ── 4. Company website scraper (FREE) ─────────────────────────────────
    if domain:
        try:
            scraped = await _scrape_company_website(company, domain)
            if scraped:
                all_contacts.append(scraped)
                logger.info("website_scrape_found", company=company, email=scraped["email"])
        except Exception as e:
            api_errors.append(f"Website scraper: {e}")
            logger.warning("website_scrape_failed", error=str(e))

    # ── 5. Apify Contact Scraper ───────────────────────────────────────────
    if settings.APIFY_API_KEY and domain and not _has_hr_contact(all_contacts):
        try:
            apify_contacts = await _apify_contact_scraper(company, domain, settings.APIFY_API_KEY)
            all_contacts.extend(apify_contacts)
        except Exception as e:
            api_errors.append(f"Apify: {e}")
            logger.warning("apify_failed", error=str(e))

    # ── 6. Prospeo ─────────────────────────────────────────────────────────
    if settings.PROSPEO_API_KEY and domain and not _has_hr_contact(all_contacts):
        try:
            p = await _search_prospeo(company, domain, settings.PROSPEO_API_KEY)
            if p:
                all_contacts.append(p)
        except Exception as e:
            api_errors.append(f"Prospeo: {e}")
            logger.warning("prospeo_failed", error=str(e))

    # ── 7. SerpAPI HR snippet search ───────────────────────────────────────
    if settings.SERPAPI_API_KEY and domain and not _has_hr_contact(all_contacts):
        try:
            s = await _search_serpapi_hr(company, domain, settings.SERPAPI_API_KEY)
            if s:
                all_contacts.append(s)
        except Exception as e:
            api_errors.append(f"SerpAPI: {e}")
            logger.warning("serpapi_failed", error=str(e))

    # ── Deduplicate collected contacts ─────────────────────────────────────
    all_contacts = _deduplicate(all_contacts)

    # ── 8. Pattern prefix fallback + Hunter Email Verifier ────────────────
    # Build pattern emails; verify top ones via Hunter when available.
    # Patterns are always appended last so real contacts sort first.
    if domain:
        pattern_contacts = await _build_pattern_fallback(
            domain,
            api_key=settings.HUNTER_API_KEY if settings.HUNTER_API_KEY else None,
        )
        real_emails = {c["email"].lower() for c in all_contacts}
        for pc in pattern_contacts:
            if pc["email"].lower() not in real_emails:
                all_contacts.append(pc)

    # ── Sort contacts by priority ──────────────────────────────────────────
    _ROLE_PRIORITY = {"hr": 0, "management": 1, "executive": 2, "generic": 3, "pattern": 4}
    all_contacts.sort(key=lambda c: (
        _ROLE_PRIORITY.get(c["role"], 9),
        -c.get("confidence", 0),
    ))

    # ── Build final result ─────────────────────────────────────────────────
    # Pick the primary hr_email (best HR contact, or first contact of any type)
    primary = next(
        (c for c in all_contacts if c["role"] == "hr" and c.get("confidence", 0) >= 50),
        all_contacts[0] if all_contacts else None,
    )

    if not primary:
        logger.warning("hr_email_not_found", company=company, domain=domain, errors=api_errors)
        return {
            "hr_name": "Hiring Team",
            "hr_email": "",
            "hr_title": "HR Department",
            "hr_linkedin": "",
            "careers_page": f"https://{domain}/careers" if domain else "",
            "confidence_score": 0.0,
            "verified": False,
            "source": "not_found",
            "all_recipients": [],
            "api_errors": api_errors,
        }

    logger.info(
        "hr_contacts_found",
        company=company,
        primary=primary["email"],
        total=len(all_contacts),
    )
    return {
        "hr_name":         primary.get("name", "HR Team"),
        "hr_email":        primary["email"],
        "hr_title":        primary.get("title", primary.get("role", "HR")),
        "hr_linkedin":     primary.get("linkedin", ""),
        "confidence_score": primary.get("confidence", 0) / 100,
        "verified":        primary.get("verified", False),
        "source":          primary.get("source", "unknown"),
        "all_recipients":  all_contacts,   # full list for multi-send
        "api_errors":      api_errors,
    }


# ── Hunter.io: Domain Search ──────────────────────────────────────────────────

async def _hunter_domain_search(
    domain: str,
    api_key: str,
    department: Optional[str] = None,
    company: str = "",
) -> list[dict]:
    """Call Hunter /domain-search and return scored contact list."""
    import httpx

    params = {
        "domain": domain,
        "api_key": api_key,
        "limit": 20,
    }
    if department:
        params["department"] = department

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            "https://api.hunter.io/v2/domain-search",
            params=params,
        )
        if resp.status_code == 401:
            raise ValueError("Hunter API key invalid or quota exhausted")
        if resp.status_code == 429:
            raise ValueError("Hunter API rate limit hit")
        resp.raise_for_status()
        data = resp.json()

    emails = (data.get("data") or {}).get("emails") or []
    contacts: list[dict] = []

    for entry in emails:
        email = (entry.get("value") or "").strip().lower()
        if not email or "@" not in email:
            continue

        # Skip obvious noise
        local = email.split("@")[0]
        if any(b in local for b in ("noreply", "no-reply", "bounce", "spam", "unsubscribe")):
            continue

        position = (entry.get("position") or "").lower()
        seniority = (entry.get("seniority") or "").lower()
        dept = (entry.get("department") or "").lower()
        first = entry.get("first_name") or ""
        last = entry.get("last_name") or ""
        name = f"{first} {last}".strip() or ""
        confidence = entry.get("confidence") or 0

        # Verification status from Hunter
        verification = entry.get("verification") or {}
        ver_status = (verification.get("status") or "").lower()
        verified = ver_status in ("valid",)

        # Classify role
        role = _classify_role(position, dept, seniority, local)

        contacts.append({
            "email":      email,
            "name":       name,
            "title":      entry.get("position") or "",
            "role":       role,
            "confidence": confidence,
            "verified":   verified,
            "linkedin":   "",
            "source":     f"hunter_{department or 'broad'}",
        })

    return contacts


# ── Hunter.io: Email Verifier ─────────────────────────────────────────────────

async def _hunter_email_verifier(email: str, api_key: str) -> dict:
    """Call Hunter /email-verifier for a single address.

    Returns dict: {status, result, score}
      status: valid | invalid | accept_all | webmail | disposable | unknown
      result: deliverable | undeliverable | risky
      score:  0-100
    """
    import httpx

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.hunter.io/v2/email-verifier",
            params={"email": email, "api_key": api_key},
        )
        # 202 = still processing; poll once after a short wait
        if resp.status_code == 202:
            await asyncio.sleep(6)
            resp = await client.get(
                "https://api.hunter.io/v2/email-verifier",
                params={"email": email, "api_key": api_key},
            )
        if resp.status_code not in (200, 202):
            return {"status": "unknown", "result": "risky", "score": 0}

        d = (resp.json().get("data") or {})
        return {
            "status": d.get("status", "unknown"),
            "result": d.get("result", "risky"),
            "score":  d.get("score", 0),
        }


async def _hunter_verify_patterns(
    patterns: list[dict],
    api_key: str,
) -> list[dict]:
    """Run Hunter Email Verifier on priority pattern prefixes.

    Only verifies _VERIFY_PREFIXES (hr@, careers@, …) to conserve credits.
    Updates confidence / verified fields; drops confirmed-invalid addresses.
    """
    to_verify = [
        p for p in patterns
        if p["email"].split("@")[0] in _VERIFY_PREFIXES
    ]
    if not to_verify:
        return patterns

    results = await asyncio.gather(
        *[_hunter_email_verifier(p["email"], api_key) for p in to_verify],
        return_exceptions=True,
    )

    # Build a lookup of email → verifier result
    ver_map: dict[str, dict] = {}
    for p, r in zip(to_verify, results):
        if isinstance(r, dict):
            ver_map[p["email"]] = r

    updated: list[dict] = []
    for p in patterns:
        v = ver_map.get(p["email"])
        if v is None:
            # Not verified — keep as-is
            updated.append(p)
            continue

        status = v["status"]
        if status == "valid":
            updated.append({**p, "confidence": 85, "verified": True,
                             "source": "hunter_verified_pattern"})
        elif status == "accept_all":
            # Domain accepts all mail — can't confirm delivery but worth trying
            updated.append({**p, "confidence": 55, "verified": False,
                             "source": "hunter_accept_all_pattern"})
        elif status in ("invalid", "disposable"):
            # Skip — confirmed undeliverable
            logger.debug("pattern_invalid_skipped", email=p["email"], status=status)
        else:
            # unknown / webmail — keep with original low confidence
            updated.append(p)

    return updated


# ── Pattern prefix fallback ───────────────────────────────────────────────────

async def _build_pattern_fallback(
    domain: str,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Build and optionally verify pattern-based email addresses.

    When a Hunter API key is provided the top-priority prefixes are verified
    via /email-verifier.  Confirmed-invalid addresses are dropped; valid ones
    get confidence 85; accept_all addresses get confidence 55.

    Without an API key a quick MX check is done and all patterns are returned
    with confidence 30.
    """
    # Quick MX check — if domain doesn't accept mail at all, skip
    if not await _verify_email_domain(f"test@{domain}"):
        return []

    patterns = []
    for prefix, label, role in _FALLBACK_PREFIXES:
        patterns.append({
            "email":      f"{prefix}@{domain}",
            "name":       label,
            "title":      label,
            "role":       "pattern",
            "confidence": 30,
            "verified":   False,
            "source":     "pattern_fallback",
        })

    if api_key:
        try:
            patterns = await _hunter_verify_patterns(patterns, api_key)
            logger.info("pattern_fallback_verified", domain=domain,
                        total=len(patterns))
        except Exception as e:
            logger.warning("pattern_verify_failed", error=str(e))

    return patterns


# ── Role classifier ───────────────────────────────────────────────────────────

def _classify_role(position: str, dept: str, seniority: str, local: str) -> str:
    """Classify a Hunter.io contact into hr / management / executive / generic."""
    pos = position.lower()
    loc = local.lower()

    # Direct HR role markers
    if any(kw in pos for kw in ("hr", "human resources", "recruiter", "talent", "hiring",
                                 "people", "recruitment", "staffing")):
        return "hr"
    if dept in ("hr",):
        return "hr"
    if any(kw in loc for kw in ("hr", "recruit", "talent", "hiring", "careers", "people")):
        return "hr"

    # Executive / C-level
    if any(kw in pos for kw in _EXEC_KEYWORDS):
        return "executive"
    if seniority == "executive" and any(kw in pos for kw in ("chief", "ceo", "founder")):
        return "executive"

    # Management / head of dept
    if any(kw in pos for kw in _MGMT_KEYWORDS):
        return "management"

    # Generic mailboxes (info@, contact@, etc.)
    if loc in ("info", "contact", "hello", "general", "admin", "team"):
        return "generic"

    # Default: treat executive-seniority as management
    if seniority == "executive":
        return "management"

    return "generic"


def _has_hr_contact(contacts: list[dict]) -> bool:
    """Return True if we already have at least one confirmed HR contact."""
    return any(c["role"] == "hr" and c.get("confidence", 0) >= 40 for c in contacts)


def _deduplicate(contacts: list[dict]) -> list[dict]:
    """Remove duplicate emails, keeping the entry with highest confidence."""
    seen: dict[str, dict] = {}
    for c in contacts:
        key = c["email"].lower()
        if key not in seen or c.get("confidence", 0) > seen[key].get("confidence", 0):
            seen[key] = c
    return list(seen.values())


# ── Strategy: Company website scraper (FREE) ─────────────────────────────────

async def _scrape_company_website(company: str, domain: str) -> Optional[dict]:
    import httpx
    from bs4 import BeautifulSoup

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    BLOCKED = {
        "noreply", "no-reply", "admin@", "sales@", "marketing@",
        "press@", "media@", "legal@", "privacy@", "security@",
        "abuse@", "spam@", "unsubscribe@", "bounce@",
    }
    headers = {"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0 Safari/537.36"}
    found: list[tuple[int, str]] = []

    async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=headers) as client:
        for base in [f"https://{domain}", f"https://www.{domain}"]:
            for path in _CONTACT_PATHS:
                try:
                    resp = await client.get(f"{base}{path}")
                    if resp.status_code != 200:
                        continue
                    final_domain = resp.url.host.lstrip("www.")
                    soup = BeautifulSoup(resp.text, "html.parser")
                    page_text = soup.get_text(" ", strip=True).lower()
                    for email in set(EMAIL_RE.findall(resp.text)):
                        el = email.lower()
                        local = el.split("@")[0]
                        email_domain = el.split("@")[1] if "@" in el else ""
                        if any(b in el for b in BLOCKED):
                            continue
                        if email_domain != final_domain and email_domain != domain:
                            continue
                        score = 0
                        pos = page_text.find(el)
                        ctx = page_text[max(0, pos - 200):pos + 200] if pos >= 0 else ""
                        for kw in _HR_KEYWORDS:
                            if kw in ctx:
                                score += 3
                        for kw in ("hr", "recruit", "talent", "hiring", "people", "career"):
                            if kw in local:
                                score += 5
                        if local in ("info", "contact", "hello", "team"):
                            score = max(score, 1)
                        found.append((score, el))
                except Exception:
                    continue
            if found:
                break

    if not found:
        return None

    found.sort(reverse=True)
    best_score, best_email = found[0]
    if best_score < 0:
        return None

    local = best_email.split("@")[0]
    role = _classify_role("", "", "", local)
    verified = await _verify_email_domain(best_email)

    return {
        "email":      best_email,
        "name":       "HR Team",
        "title":      "HR / Recruiter",
        "role":       role,
        "confidence": min(50 + best_score * 5, 85),
        "verified":   verified,
        "source":     "website_scrape",
    }


# ── Strategy: Apify Contact Info Scraper ─────────────────────────────────────

async def _apify_contact_scraper(company: str, domain: str, api_key: str) -> list[dict]:
    import httpx

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
    BLOCKED = {"noreply", "no-reply", "admin", "sales", "marketing", "press", "legal", "privacy"}
    contacts = []

    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(actor_url, json={
            "startUrls": start_urls, "maxDepth": 1, "maxPageCount": 5,
            "proxy": {"useApifyProxy": True},
        })
        resp.raise_for_status()
        items = resp.json()

    for item in items:
        for email_entry in (item.get("emails") or []):
            email = (email_entry if isinstance(email_entry, str)
                     else email_entry.get("email") or "").strip().lower()
            if not email or "@" not in email:
                continue
            local = email.split("@")[0]
            email_domain = email.split("@")[1]
            if domain not in email_domain and email_domain not in domain:
                continue
            if any(b in local for b in BLOCKED):
                continue
            score = sum(5 for kw in ("hr", "recruit", "talent", "hiring", "people", "career")
                        if kw in local)
            role = _classify_role("", "", "", local)
            contacts.append({
                "email": email, "name": "HR Team", "title": "HR / Recruiter",
                "role": role, "confidence": min(50 + score * 5, 80),
                "verified": False, "source": "apify",
            })

    return contacts


# ── Strategy: Prospeo Search + Enrich ────────────────────────────────────────

async def _search_prospeo(company: str, domain: str, api_key: str) -> Optional[dict]:
    import httpx

    headers = {"X-KEY": api_key, "Content-Type": "application/json"}
    bare_domain = domain.lstrip("www.")

    for search_payload in [
        {"page": 1, "filters": {
            "company": {"websites": {"include": [bare_domain]}},
            "person_department": {"include": ["Human Resources"]},
            "person_seniority": {"include": ["Manager", "Director", "Head", "Vice President", "Senior"]},
        }},
        {"page": 1, "filters": {
            "company": {"websites": {"include": [bare_domain]}},
            "person_department": {"include": ["Human Resources"]},
        }},
    ]:
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.post("https://api.prospeo.io/search-person",
                                         headers=headers, json=search_payload)
                resp.raise_for_status()
                search_data = resp.json()
            except Exception as e:
                logger.debug("prospeo_search_failed", error=str(e))
                return None

            if search_data.get("error") or not search_data.get("results"):
                continue

            for result in search_data["results"][:5]:
                person = result.get("person", {})
                person_id = person.get("person_id")
                if not person_id:
                    continue
                try:
                    enrich_resp = await client.post(
                        "https://api.prospeo.io/enrich-person",
                        headers=headers,
                        json={"only_verified_email": True, "data": {"person_id": person_id}},
                    )
                    enrich_data = enrich_resp.json()
                except Exception:
                    continue

                ep = enrich_data.get("person", {})
                email_obj = ep.get("email", {})
                email = (email_obj.get("email") or "").strip().lower()
                if (not email or "@" not in email or "*" in email
                        or email_obj.get("status") != "VERIFIED"
                        or not email_obj.get("revealed")):
                    continue
                email_domain = email.split("@", 1)[1].lstrip("www.")
                if bare_domain not in email_domain and email_domain not in bare_domain:
                    continue
                if not await _verify_email_domain(email):
                    continue

                full_name = (ep.get("full_name") or
                             f"{ep.get('first_name','')} {ep.get('last_name','')}".strip() or
                             "HR Professional")
                return {
                    "email": email, "name": full_name,
                    "title": ep.get("current_job_title") or "HR Professional",
                    "role": "hr", "confidence": 95, "verified": True,
                    "linkedin": ep.get("linkedin_url") or "",
                    "source": "prospeo",
                }
    return None


# ── Strategy: SerpAPI HR search (snippet emails only) ────────────────────────

async def _search_serpapi_hr(company: str, domain: str, serpapi_key: str) -> Optional[dict]:
    import httpx

    EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
    company_clean = _norm_company(company)
    queries = [
        f'"{company}" recruiter OR "talent acquisition" OR "HR manager" email',
        f'site:{domain} recruiter OR HR OR talent email',
        f'"{company_clean}" recruiter LinkedIn',
    ]

    async with httpx.AsyncClient(timeout=20) as client:
        for query in queries:
            try:
                resp = await client.get("https://serpapi.com/search", params={
                    "engine": "google", "q": query,
                    "api_key": serpapi_key, "num": 5, "no_cache": "true",
                })
                resp.raise_for_status()
                data = resp.json()
                for result in data.get("organic_results", []):
                    raw_text = f"{result.get('title','')} {result.get('snippet','')}"
                    for email in EMAIL_RE.findall(raw_text):
                        email = email.lower()
                        if "@" not in email:
                            continue
                        email_domain = email.split("@")[1]
                        if domain not in email_domain and email_domain not in domain:
                            continue
                        local = email.split("@")[0]
                        if any(b in local for b in ("noreply", "no-reply", "admin",
                                                     "sales", "legal", "privacy")):
                            continue
                        verified = await _verify_email_domain(email)
                        role = _classify_role("", "", "", local)
                        return {
                            "email": email, "name": "HR Team",
                            "title": "HR / Recruiter",
                            "role": role,
                            "confidence": 75 if verified else 55,
                            "verified": verified,
                            "source": "serpapi",
                        }
            except Exception as e:
                logger.debug("serpapi_hr_failed", query=query[:60], error=str(e))
    return None


# ── Batch HR Contact Finder ───────────────────────────────────────────────────

async def batch_find_hr_contacts(jobs: list) -> list:
    """Run HR email lookup for all jobs concurrently.

    Annotates each job with:
      _hr_contact: dict  — full HR contact data (includes all_recipients list)
      hr_found: bool     — True if any real email found
    """
    async def _lookup(job_data: dict) -> dict:
        job_data = dict(job_data)
        try:
            result = await find_hr_contact(
                company=job_data.get("company", ""),
                job_title=job_data.get("title", ""),
                company_domain=job_data.get("company_domain"),
            )
            if result.get("hr_email"):
                job_data["_hr_contact"] = result
                job_data["hr_found"] = True
            else:
                job_data["hr_found"] = False
        except Exception as e:
            logger.warning("batch_hr_lookup_error", company=job_data.get("company"), error=str(e))
            job_data["hr_found"] = False
        return job_data

    results = await asyncio.gather(*[_lookup(j) for j in jobs], return_exceptions=True)
    all_jobs, verified = [], 0
    for r in results:
        if isinstance(r, Exception):
            logger.warning("batch_hr_gather_error", error=str(r))
            continue
        all_jobs.append(r)
        if r.get("hr_found"):
            verified += 1

    logger.info("batch_hr_complete", total=len(jobs), verified=verified)
    return all_jobs


# ── DNS / MX verification ─────────────────────────────────────────────────────

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


# ── Domain helpers ────────────────────────────────────────────────────────────

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
    """Follow HTTP redirect to find the real domain."""
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
