"""CV Parser Agent — BowJob-powered comprehensive CV extraction."""

import os
import io
import json
import base64
import structlog
from typing import Optional

logger = structlog.get_logger()


# ── BowJob CVParserV3 System Prompt ──────────────────────────────────────────
_PARSER_SYSTEM_PROMPT = """You are an expert CV/Resume parser. Your job is to extract ALL content from the CV and map it to the output schema. DO NOT MISS ANY CONTENT.

CRITICAL RULE: CAPTURE EVERYTHING
- Parse EVERY section of the CV
- Map ALL content to the nearest matching output field
- Do NOT skip or ignore any section - find a place for it in the schema

SECTION MAPPING - Map by CONTENT, not section title:
| CV Section | Maps To |
|------------|---------|
| Skills, Technical Skills, Core Competencies, Expertise | skills (flat array) |
| Interests, Hobbies (if professional/field-related) | skills |
| Tools, Technologies, Platforms | skills |
| Soft Skills, Interpersonal Skills | skills |
| Projects, Personal Projects, Side Projects | projects |
| Activities, Extracurriculars (if project-like) | projects |
| Volunteer Experience, Community Service | experience |
| Internships | experience |
| Achievements, Honors, Awards | awards_scholarships |
| Courses, Training, Workshops | certifications |
| Research, Papers, Publications | publications |
| Languages, Language Skills | languages |

SKILLS - FLAT ARRAY: Extract ALL skills into one array (technical, soft, tools, platforms, methodologies, domain skills). Extract from EVERYWHERE: skills section, work descriptions, projects, interests, hobbies.

MAPPING RULES:
1. Analyze CONTENT to decide where it belongs, not just the section title
2. "Interests: Building ML models" → skills + projects
3. "Volunteer: Taught coding to kids at NGO" → experience
4. Only skip content that is purely personal with zero professional relevance
5. When in doubt, include it

OTHER RULES:
1. Do NOT make up or infer information not in the CV
2. Return null only if a field is genuinely not present
3. Extract information exactly as written
4. For dates, normalize to YYYY-MM or YYYY where possible

DESCRIPTION FORMATTING:
- BULLET POINTS → return as ARRAY of strings
- MULTIPLE LINES → return as ARRAY of strings
- SINGLE PARAGRAPH → return as single STRING"""


async def parse_cv_file(file_path: str, file_type: str, user_id: str = "unknown") -> dict:
    """Parse a CV file and extract structured data using LLM.

    Args:
        file_path: Path to the uploaded CV file.
        file_type: 'pdf' or 'docx'.

    Returns:
        Structured CV data dictionary (Digital FTE format + BowJob extended fields).
    """
    from app.core.event_bus import event_bus
    await event_bus.emit_agent_started(user_id, "cv_parser", f"Parsing CV: {os.path.basename(file_path)}")

    # Step 1: Extract raw text
    await event_bus.emit_agent_progress(user_id, "cv_parser", 1, 3, "Extracting text from file")
    raw_text = _extract_text(file_path, file_type)
    if not raw_text.strip():
        logger.warning("empty_cv_text", file_path=file_path)
        await event_bus.emit_agent_error(user_id, "cv_parser", "Could not extract text from CV")
        return {"error": "Could not extract text from CV"}

    # Step 2: Use LLM to parse structured data
    await event_bus.emit_agent_progress(user_id, "cv_parser", 2, 3, "Analyzing structure with AI")
    parsed = await _llm_parse_cv(raw_text)

    # Step 3: Extract certificates embedded as images in the CV (PDFs only)
    await event_bus.emit_agent_progress(user_id, "cv_parser", 3, 3, "Scanning certificate images with vision AI")
    image_certs = await _extract_image_certificates(file_path, file_type)
    if image_certs:
        existing_certs = parsed.get("certifications") or []
        existing_names = {c.get("name", "").lower() for c in existing_certs if isinstance(c, dict)}
        new_certs = [c for c in image_certs if c.get("name", "").lower() not in existing_names]
        if new_certs:
            parsed["certifications"] = existing_certs + new_certs
            logger.info("image_certs_added", count=len(new_certs))

    await event_bus.emit_agent_completed(user_id, "cv_parser", "CV parsed successfully")
    return parsed


def _extract_text(file_path: str, file_type: str) -> str:
    """Extract raw text from PDF or DOCX."""
    if file_type == "pdf":
        return _extract_pdf_text(file_path)
    elif file_type == "docx":
        return _extract_docx_text(file_path)
    return ""


def _extract_pdf_text(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error("pdf_extraction_error", error=str(e))
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e2:
            logger.error("pypdf_fallback_error", error=str(e2))
            return ""


def _extract_docx_text(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        logger.error("docx_extraction_error", error=str(e))
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# Image Certificate Extraction (GPT-4o Vision)
# ─────────────────────────────────────────────────────────────────────────────

def _get_pdf_embedded_images(file_path: str) -> list:
    """Extract raw bytes of all meaningful embedded images from a PDF via pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        results = []
        seen_sizes = set()  # deduplicate identical images
        for page in reader.pages:
            try:
                for img_obj in page.images:
                    try:
                        data = img_obj.data
                        if not isinstance(data, bytes):
                            continue
                        # Skip tiny icons/logos (< 8 KB) and exact duplicates
                        if len(data) < 8_000:
                            continue
                        key = len(data)  # good-enough dedup for certificates
                        if key in seen_sizes:
                            continue
                        seen_sizes.add(key)
                        # Cap individual image at 4 MB to avoid overloading vision API
                        if len(data) > 4_000_000:
                            continue
                        results.append(data)
                    except Exception:
                        continue
            except Exception:
                continue
        return results
    except Exception as e:
        logger.warning("pdf_image_extract_error", error=str(e))
        return []


async def _vision_read_certificate(image_bytes: bytes) -> list:
    """Send one image to GPT-4o vision and return a list of extracted certificate dicts."""
    from app.config import settings as app_settings
    if not app_settings.OPENAI_API_KEY:
        return []

    # Normalize raw image bytes → PNG via Pillow (handles JPEG, CMYK, etc.)
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        final_bytes = buf.getvalue()
        mime = "image/png"
    except Exception:
        final_bytes = image_bytes
        mime = "image/jpeg"

    b64 = base64.b64encode(final_bytes).decode()

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=app_settings.OPENAI_API_KEY,
            temperature=0,
            max_tokens=600,
        )
        msg = HumanMessage(content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}", "detail": "low"},
            },
            {
                "type": "text",
                "text": (
                    "This image is from a CV. If it shows a certificate, credential, award, "
                    "course completion, or professional qualification, extract the info as JSON:\n"
                    '{"is_certificate": true, "certificates": [{"name": "...", '
                    '"issuing_organization": "... or null", "issue_date": "YYYY or null", '
                    '"expiry_date": "YYYY or null", "credential_id": "... or null"}]}\n'
                    'If NOT a certificate image, return: {"is_certificate": false, "certificates": []}\n'
                    "Return ONLY valid JSON, no markdown fences."
                ),
            },
        ])
        response = await llm.ainvoke([msg])
        content = response.content.strip()
        # Strip markdown fences if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        result = json.loads(content)
        if result.get("is_certificate") and result.get("certificates"):
            return [
                {
                    "name": c.get("name", ""),
                    "issuer": c.get("issuing_organization"),
                    "issue_date": c.get("issue_date"),
                    "expiry_date": c.get("expiry_date"),
                    "credential_id": c.get("credential_id"),
                    "_from_image": True,
                }
                for c in result["certificates"]
                if c.get("name")
            ]
        return []
    except Exception as e:
        logger.warning("vision_cert_ocr_error", error=str(e))
        return []


async def _extract_image_certificates(file_path: str, file_type: str) -> list:
    """Orchestrate image extraction + vision OCR for all embedded images in a PDF."""
    if file_type != "pdf":
        return []

    image_bytes_list = _get_pdf_embedded_images(file_path)
    if not image_bytes_list:
        return []

    logger.info("scanning_certificate_images", count=len(image_bytes_list))
    certs: list = []
    # Process up to 8 images concurrently would be nicer, but sequential is safer on rate limits
    for img_bytes in image_bytes_list[:8]:
        extracted = await _vision_read_certificate(img_bytes)
        certs.extend(extracted)

    return certs


# ── BowJob CV_FUNCTION Schema (OpenAI function calling — mirrors CVParserV3) ─
_CV_FUNCTION = [{
    "type": "function",
    "function": {
        "name": "extract_cv_information",
        "description": "Extract all information from a CV/Resume. Use null for any field not present.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_info": {
                    "type": "object",
                    "properties": {
                        "full_name": {"type": ["string", "null"]},
                        "email": {"type": ["string", "null"]},
                        "phone": {"type": ["string", "null"]},
                        "location": {"type": ["string", "null"]},
                        "linkedin": {"type": ["string", "null"]},
                        "github": {"type": ["string", "null"]},
                        "website": {"type": ["string", "null"]},
                        "portfolio": {"type": ["string", "null"]},
                        "nationality": {"type": ["string", "null"]},
                        "date_of_birth": {"type": ["string", "null"]},
                        "other_links": {"type": ["array", "null"], "items": {"type": "string"}},
                    },
                },
                "title": {"type": ["string", "null"]},
                "professional_summary": {
                    "type": ["string", "null"],
                    "description": "Summary as a single string; join multiple bullets with a space.",
                },
                "work_experience": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "job_title": {"type": ["string", "null"]},
                            "company": {"type": ["string", "null"]},
                            "location": {"type": ["string", "null"]},
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]},
                            "description": {
                                "type": ["array", "null"],
                                "items": {"type": "string"},
                                "description": "Each bullet point as a separate array element.",
                            },
                        },
                    },
                },
                "education": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "degree": {"type": ["string", "null"]},
                            "field_of_study": {"type": ["string", "null"]},
                            "institution": {"type": ["string", "null"]},
                            "location": {"type": ["string", "null"]},
                            "start_date": {"type": ["string", "null"]},
                            "end_date": {"type": ["string", "null"]},
                            "gpa": {"type": ["string", "null"]},
                        },
                    },
                },
                "skills": {
                    "type": ["array", "null"],
                    "items": {"type": "string"},
                    "description": "ALL skills in one flat array: technical, soft, tools, methodologies, domain.",
                },
                "languages": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "language": {"type": "string"},
                            "proficiency": {"type": ["string", "null"]},
                        },
                        "required": ["language"],
                    },
                },
                "projects": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "description": {"type": ["string", "null"]},
                            "technologies": {"type": ["array", "null"], "items": {"type": "string"}},
                            "date": {"type": ["string", "null"]},
                            "url": {"type": ["string", "null"]},
                        },
                    },
                },
                "certifications": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "issuing_organization": {"type": ["string", "null"]},
                            "issue_date": {"type": ["string", "null"]},
                            "expiry_date": {"type": ["string", "null"]},
                            "credential_id": {"type": ["string", "null"]},
                        },
                    },
                },
                "awards_scholarships": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": ["string", "null"]},
                            "issuer": {"type": ["string", "null"]},
                            "date": {"type": ["string", "null"]},
                            "description": {"type": ["string", "null"]},
                        },
                    },
                },
                "publications": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": ["string", "null"]},
                            "authors": {"type": ["string", "null"]},
                            "publisher": {"type": ["string", "null"]},
                            "date": {"type": ["string", "null"]},
                            "url": {"type": ["string", "null"]},
                        },
                    },
                },
                "total_years_of_experience": {
                    "type": ["number", "null"],
                    "description": "Total professional experience in decimal years, excluding employment gaps.",
                },
            },
            "required": [],
        },
    },
}]


async def _openai_parse_cv(raw_text: str) -> Optional[dict]:
    """Use OpenAI function calling — BowJob CVParserV3 style — for guaranteed structured output.

    Returns normalised Digital FTE dict, or None if OpenAI key unavailable / call fails.
    """
    from app.config import settings as app_settings
    if not app_settings.OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=app_settings.OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # cost-efficient — same model as BowJob CVParserV3
            messages=[
                {"role": "system", "content": _PARSER_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Extract all information from this CV. "
                        "Use null for any field not present.\n\n"
                        f"{raw_text[:8000]}"
                    ),
                },
            ],
            tools=_CV_FUNCTION,
            tool_choice={"type": "function", "function": {"name": "extract_cv_information"}},
        )
        if response.choices[0].message.tool_calls:
            raw = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
            logger.info("bowjob_cv_function_calling_success",
                        tokens=response.usage.total_tokens if response.usage else None)
            return _normalize_to_fte_format(raw)
        return None
    except Exception as e:
        logger.warning("bowjob_cv_function_calling_error", error=str(e))
        return None


async def _llm_parse_cv(raw_text: str) -> dict:
    """Use OpenAI function calling (BowJob CVParserV3) or LangChain LLM to extract CV data."""
    # Primary: OpenAI function calling — BowJob CVParserV3 style, guaranteed structured output
    result = await _openai_parse_cv(raw_text)
    if result is not None:
        return result

    # Fallback: LangChain LLM with prompt-based JSON extraction
    logger.info("bowjob_cv_fallback_to_langchain")
    from app.core.llm_router import get_llm
    from langchain_core.messages import SystemMessage, HumanMessage

    llm = get_llm(task="cv_parsing")

    user_prompt = f"""Extract ALL information from this CV. Return ONLY valid JSON with this exact structure. Use null for any field not present in the CV. Do NOT make up information.

{{
  "contact_info": {{
    "full_name": "string or null",
    "email": "string or null",
    "phone": "string or null",
    "location": "City, Country or null",
    "linkedin": "URL or null",
    "github": "URL or null",
    "website": "URL or null",
    "portfolio": "URL or null",
    "nationality": "string or null",
    "date_of_birth": "string or null",
    "other_links": ["array of other URLs"] or null
  }},
  "title": "Current job title or professional headline or null",
  "professional_summary": "Summary as single string, OR array of strings if bullet points, OR null",
  "work_experience": [
    {{
      "job_title": "string",
      "company": "string",
      "location": "string or null",
      "start_date": "YYYY-MM or YYYY or null",
      "end_date": "YYYY-MM or YYYY or 'Present' or null",
      "description": ["array of bullet strings"] or "single paragraph string" or null
    }}
  ] or null,
  "education": [
    {{
      "degree": "string or null",
      "field_of_study": "string or null",
      "institution": "string or null",
      "location": "string or null",
      "start_date": "YYYY or null",
      "end_date": "YYYY or 'Present' or null",
      "gpa": "string or null"
    }}
  ] or null,
  "skills": ["flat array of ALL skills - technical, soft, tools, methodologies, domain skills - extracted from EVERYWHERE in the CV"] or null,
  "languages": [
    {{"language": "string", "proficiency": "Native/Fluent/Professional/Intermediate/Basic or null"}}
  ] or null,
  "projects": [
    {{
      "name": "string or null",
      "description": ["array of strings"] or "string" or null,
      "technologies": ["array of strings"] or null,
      "date": "string or null",
      "url": "string or null"
    }}
  ] or null,
  "certifications": [
    {{
      "name": "string",
      "issuing_organization": "string or null",
      "issue_date": "YYYY-MM or YYYY or null",
      "expiry_date": "string or null",
      "credential_id": "string or null"
    }}
  ] or null,
  "awards_scholarships": [
    {{
      "title": "string",
      "issuer": "string or null",
      "date": "string or null",
      "description": "string or null"
    }}
  ] or null,
  "publications": [
    {{
      "title": "string",
      "authors": "string or null",
      "publisher": "string or null",
      "date": "string or null",
      "url": "string or null"
    }}
  ] or null,
  "total_years_of_experience": number or null
}}

CV TEXT:
{raw_text[:8000]}"""

    try:
        messages = [
            SystemMessage(content=_PARSER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        raw = json.loads(content)
        return _normalize_to_fte_format(raw)

    except Exception as e:
        logger.error("llm_cv_parse_error", error=str(e))
        return {
            "personal_info": {},
            "summary": raw_text[:500],
            "skills": {"technical": [], "soft": [], "tools": []},
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
            "languages": [],
            "_parse_error": str(e),
        }


def _normalize_to_fte_format(raw: dict) -> dict:
    """Convert BowJob schema → Digital FTE schema + preserve rich BowJob fields."""

    ci = raw.get("contact_info") or {}

    # personal_info (Digital FTE compat)
    personal_info = {
        "name": ci.get("full_name"),
        "email": ci.get("email"),
        "phone": ci.get("phone"),
        "location": ci.get("location"),
        "linkedin": ci.get("linkedin"),
        "github": ci.get("github"),
        "portfolio": ci.get("portfolio") or ci.get("website"),
        "nationality": ci.get("nationality"),
        "date_of_birth": ci.get("date_of_birth"),
        "other_links": ci.get("other_links"),
    }

    # summary: flatten professional_summary to string
    ps = raw.get("professional_summary")
    if isinstance(ps, list):
        summary = " ".join(ps)
    elif isinstance(ps, str):
        summary = ps
    else:
        summary = ""

    # skills: BowJob gives a flat array; split into technical/tools/soft heuristically
    flat_skills = raw.get("skills") or []
    technical, tools, soft = _categorize_skills(flat_skills)

    # experience: map work_experience → Digital FTE experience format
    work_exp = raw.get("work_experience") or []
    experience = []
    for job in work_exp:
        desc = job.get("description")
        if isinstance(desc, list):
            achievements = desc
        elif isinstance(desc, str) and desc:
            # Split paragraph by ". " or newline into bullets
            import re
            achievements = [s.strip() for s in re.split(r"\n|(?<=\.)\s+(?=[A-Z])", desc) if s.strip()]
        else:
            achievements = []

        start = job.get("start_date", "")
        end = job.get("end_date", "")
        duration = f"{start} - {end}".strip(" -")

        experience.append({
            "company": job.get("company", ""),
            "role": job.get("job_title", ""),
            "duration": duration,
            "location": job.get("location"),
            "achievements": achievements,
            "technologies": [],  # extracted from description by tailor
        })

    # education
    edu_raw = raw.get("education") or []
    education = []
    for e in edu_raw:
        year = e.get("end_date") or e.get("start_date") or ""
        education.append({
            "institution": e.get("institution", ""),
            "degree": e.get("degree", ""),
            "field": e.get("field_of_study", ""),
            "year": str(year),
            "gpa": e.get("gpa"),
            "location": e.get("location"),
        })

    # projects
    proj_raw = raw.get("projects") or []
    projects = []
    for p in proj_raw:
        desc = p.get("description")
        if isinstance(desc, list):
            desc_str = " ".join(desc)
        else:
            desc_str = desc or ""
        projects.append({
            "name": p.get("name", ""),
            "description": desc_str,
            "technologies": p.get("technologies") or [],
            "date": p.get("date"),
            "url": p.get("url"),
        })

    # certifications: normalize to list of dicts
    certs_raw = raw.get("certifications") or []
    certifications = []
    for c in certs_raw:
        if isinstance(c, str):
            certifications.append({"name": c})
        elif isinstance(c, dict):
            certifications.append({
                "name": c.get("name", ""),
                "issuer": c.get("issuing_organization"),
                "issue_date": c.get("issue_date"),
                "expiry_date": c.get("expiry_date"),
                "credential_id": c.get("credential_id"),
            })

    # languages
    langs_raw = raw.get("languages") or []
    languages = []
    for lang in langs_raw:
        if isinstance(lang, str):
            languages.append({"language": lang, "proficiency": None})
        elif isinstance(lang, dict):
            languages.append(lang)

    return {
        # ── Digital FTE compat fields ─────────────────────────
        "personal_info": personal_info,
        "title": raw.get("title"),
        "summary": summary,
        "skills": {
            "technical": technical,
            "soft": soft,
            "tools": tools,
            "all": flat_skills,  # preserve flat list for tailor
        },
        "experience": experience,
        "education": education,
        "projects": projects,
        "certifications": certifications,
        "languages": languages,
        # ── BowJob extended fields ─────────────────────────────
        "publications": raw.get("publications") or [],
        "awards_scholarships": raw.get("awards_scholarships") or [],
        "total_years_of_experience": raw.get("total_years_of_experience"),
        # ── Raw BowJob schema (for tailor agent) ───────────────
        "_bowjob_raw": raw,
    }


# Known tool/framework keywords for categorization
_TOOL_KEYWORDS = {
    "git", "docker", "kubernetes", "aws", "azure", "gcp", "jenkins", "jira",
    "figma", "photoshop", "excel", "powerpoint", "tableau", "powerbi", "looker",
    "vscode", "linux", "windows", "macos", "postman", "terraform", "ansible",
    "redis", "postgres", "mysql", "mongodb", "elasticsearch", "kafka", "rabbitmq",
    "react", "angular", "vue", "node", "express", "fastapi", "django", "flask",
    "pytorch", "tensorflow", "keras", "scikit", "pandas", "numpy", "spark",
    "hadoop", "airflow", "mlflow", "langchain", "hugging face", "openai",
}

_SOFT_KEYWORDS = {
    "communication", "leadership", "teamwork", "problem solving", "critical thinking",
    "time management", "creativity", "adaptability", "collaboration", "interpersonal",
    "presentation", "mentoring", "negotiation", "decision making", "analytical",
    "detail oriented", "organized", "proactive", "motivated", "empathy", "listening",
    "conflict resolution", "stakeholder management", "project management",
}


def _categorize_skills(flat_skills: list) -> tuple:
    """Heuristically split flat skills into technical / tools / soft."""
    technical, tools, soft = [], [], []
    for skill in flat_skills:
        s_lower = skill.lower()
        if any(kw in s_lower for kw in _SOFT_KEYWORDS):
            soft.append(skill)
        elif any(kw in s_lower for kw in _TOOL_KEYWORDS):
            tools.append(skill)
        else:
            technical.append(skill)
    return technical, tools, soft
