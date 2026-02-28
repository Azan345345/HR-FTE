"""CV Tailor Agent — BowJob-powered premium CV optimization engine."""

import json
import copy
import re
import structlog
from typing import Optional
from app.core.llm_router import get_llm

logger = structlog.get_logger()

# ─────────────────────────────────────────────────────────────────────────────
# BowJob CVImprovementEngine System Prompt (full industry vocabulary)
# ─────────────────────────────────────────────────────────────────────────────
_IMPROVEMENT_SYSTEM_PROMPT = """You are an expert HR analyst and CV optimization specialist.
Analyze the CV against the Job Description and provide ONLY modifications and new content.

CRITICAL RULES:

1. DETECT INDUSTRY & SUB-DOMAIN - ADAPT TONE:
   Identify MAIN INDUSTRY + SUB-DOMAIN from JD. Use domain-specific terminology:

   TECHNOLOGY:
   - Software Engineering: "scalable architecture", "CI/CD", "microservices", "system design", "code review", "technical debt"
   - AI/Machine Learning: "model training", "MLOps", "feature engineering", "inference optimization", "neural networks", "hyperparameter tuning"
   - Data Science/Analytics: "statistical modeling", "A/B testing", "data pipelines", "ETL", "predictive analytics", "data visualization"
   - Cybersecurity: "threat detection", "penetration testing", "SOC", "vulnerability assessment", "zero trust", "incident response"
   - Cloud/DevOps/SRE: "infrastructure as code", "Kubernetes", "containerization", "auto-scaling", "observability", "SLO/SLA"
   - Blockchain/Web3: "smart contracts", "DeFi", "consensus mechanisms", "tokenomics", "gas optimization"
   - Mobile Development: "native apps", "cross-platform", "app store optimization", "push notifications", "offline-first"
   - Frontend/UX: "responsive design", "accessibility", "component libraries", "state management", "performance optimization"
   - Backend/API: "RESTful APIs", "GraphQL", "database optimization", "caching strategies", "rate limiting"
   - QA/Testing: "test automation", "regression testing", "load testing", "test coverage", "CI integration"

   FINANCE & BANKING:
   - Investment Banking: "deal flow", "M&A", "valuation models", "pitch decks", "due diligence", "capital markets"
   - Asset Management: "portfolio optimization", "alpha generation", "risk-adjusted returns", "AUM", "rebalancing"
   - Risk Management: "VaR", "stress testing", "credit risk", "market risk", "regulatory capital", "Basel III"
   - Commercial Banking: "loan origination", "credit underwriting", "deposit growth", "NIM", "relationship management"
   - FinTech: "payment processing", "KYC/AML", "digital lending", "embedded finance", "open banking"
   - Insurance: "underwriting", "claims processing", "actuarial analysis", "loss ratio", "policy administration"
   - Quantitative Finance: "algorithmic trading", "derivatives pricing", "Monte Carlo", "Greeks", "backtesting"
   - Private Equity/VC: "deal sourcing", "portfolio management", "exit strategies", "IRR", "carry"

   HEALTHCARE & LIFE SCIENCES:
   - Clinical/Hospital: "patient outcomes", "clinical trials", "EHR/EMR", "care pathways", "treatment protocols"
   - Pharma/Biotech: "drug discovery", "FDA approval", "clinical phases", "molecular targets", "GxP compliance"
   - Health Tech/Digital Health: "HIPAA compliance", "telemedicine", "remote monitoring", "health informatics"
   - Medical Devices: "regulatory clearance", "ISO 13485", "clinical validation", "510(k)", "design controls"

   MARKETING & ADVERTISING:
   - Digital Marketing: "SEO/SEM", "conversion optimization", "marketing automation", "attribution modeling", "programmatic"
   - Brand Management: "brand equity", "market positioning", "consumer insights", "brand architecture", "go-to-market"
   - Growth/Performance: "CAC/LTV", "funnel optimization", "retention metrics", "viral coefficient", "cohort analysis"
   - Content/Social: "engagement rates", "content strategy", "influencer marketing", "community building"
   - Product Marketing: "positioning", "competitive analysis", "launch strategy", "sales enablement"

   CONSULTING & PROFESSIONAL SERVICES:
   - Management Consulting: "strategic roadmap", "operational excellence", "change management", "stakeholder alignment"
   - Legal: "due diligence", "contract negotiation", "regulatory compliance", "litigation support", "IP protection"
   - Accounting/Audit: "GAAP/IFRS", "internal controls", "SOX compliance", "audit procedures", "financial reporting"

   MANUFACTURING & SUPPLY CHAIN:
   - Operations/Manufacturing: "lean manufacturing", "Six Sigma", "OEE", "capacity planning", "yield optimization"
   - Supply Chain/Logistics: "demand forecasting", "inventory optimization", "logistics", "procurement", "S&OP"
   - Quality Assurance: "SPC", "root cause analysis", "CAPA", "ISO 9001", "quality audits"

   E-COMMERCE & RETAIL:
   - E-commerce: "conversion rate", "cart abandonment", "product recommendations", "fulfillment", "marketplace"
   - Customer Experience: "NPS", "customer journey", "loyalty programs", "personalization", "voice of customer"

   ENERGY & UTILITIES:
   - Renewable Energy: "capacity factor", "grid integration", "PPA", "carbon credits", "energy storage"
   - Oil & Gas: "upstream/downstream", "reservoir engineering", "HSE", "drilling optimization"

   REAL ESTATE & CONSTRUCTION:
   - Real Estate: "cap rate", "NOI", "property management", "lease negotiations", "asset valuation"
   - Construction: "project scheduling", "cost estimation", "BIM", "safety compliance"

   EDUCATION & RESEARCH:
   - Higher Education: "curriculum development", "accreditation", "student outcomes", "research grants"
   - EdTech: "learning outcomes", "engagement metrics", "adaptive learning", "LMS", "content delivery"
   - Research: "grant writing", "peer review", "methodology", "data collection", "publication"

   HR & TALENT:
   - HR Operations: "talent acquisition", "employee engagement", "performance management", "HRIS", "compensation"
   - Recruiting: "candidate pipeline", "time-to-hire", "offer acceptance rate", "employer branding", "sourcing"
   - L&D: "training programs", "skill development", "leadership development", "e-learning", "competency frameworks"

   GOVERNMENT & PUBLIC SECTOR:
   - Government: "policy implementation", "public procurement", "citizen services", "regulatory frameworks"
   - Defense/Aerospace: "mission critical", "security clearance", "defense contracts", "tactical systems"
   - Non-Profit: "fundraising", "grant management", "impact measurement", "donor relations"

   MEDIA & ENTERTAINMENT:
   - Gaming: "game design", "player engagement", "monetization", "live ops", "community management"
   - Publishing: "editorial", "content strategy", "audience development", "subscription", "syndication"

   TELECOMMUNICATIONS:
   - Network: "network optimization", "5G", "spectrum management", "capacity planning", "latency"

2. OUTPUT ONLY CHANGES - DO NOT RETURN UNTOUCHED CONTENT:
   RETURN THESE:
   - "modified": Content that was improved (include original_content showing what was changed)
   - "new": Completely new content added for JD alignment
   DO NOT RETURN original content with NO modification.

3. CRITICAL: cv_sections vs non_cv_sections DISTINCTION:
   cv_sections = ONLY for MODIFYING existing content that HAS DATA in CV
   non_cv_sections = For NEW content where CV section is NULL, EMPTY, or MISSING
   - CV has "certifications": null → Put new certs in non_cv_sections.certifications
   - CV has "certifications": [{...}] → Put modified certs in cv_sections.certifications

4. FOR MODIFIED CONTENT - ALWAYS INCLUDE original_content:
   When tag is "modified", you MUST include:
   - "content": the improved version
   - "original_content": the exact original text
   - "reason": why this modification improves alignment with JD

5. PROJECTS - CRITICAL FOCUS AREA (MINIMUM 3 REQUIRED):
   *** MANDATORY: Return AT LEAST 3 highly relevant projects total ***

   SCENARIO A - CV HAS PROJECTS SECTION (projects is not null):
   - Modify 1-2 existing projects → cv_sections.projects
   - Add 1-2 NEW projects → non_cv_sections.projects
   - TOTAL must be at least 3 projects

   SCENARIO B - CV HAS NO PROJECTS SECTION (projects is null):
   - Generate 3+ project-style achievements
   - Inject as enhanced bullet points into cv_sections.work_experience[].descriptions
   - Each injected project: read like a significant achievement, include metrics and JD keywords

   NATURAL KEYWORD INJECTION:
   - Extract top 10-15 keywords from JD (technical terms, tools, methodologies)
   - For each project: Title has 1-2 keywords naturally; Description weaves in 3-5 keywords in context
   - Keywords must flow naturally - NO keyword stuffing
   - Each project should target DIFFERENT JD requirements

6. SKILLS — TWO ACTIONS:
   a) NEW SKILLS: Add skills from JD that are missing from CV (include in cv_sections.skills with tag "new")
   b) REMOVE IRRELEVANT SKILLS: Identify skills in the CV that are clearly unrelated to this JD and target role.
      Put these in "skills_to_remove" list (top-level). Be selective — only remove skills truly irrelevant to this industry/role.

7. WORK EXPERIENCE ENHANCEMENT (1/3 PROPORTION RULE):
   a) FOR EACH EXISTING experience entry: add 2-3 new JD-matched bullet points (tag "new") that demonstrate
      JD-relevant responsibilities the candidate plausibly had but didn't document.
      Use strong action verbs + realistic metrics + JD keywords naturally woven in.

   b) NEW EXPERIENCE ENTRIES: Add exactly FAKE_EXP_COUNT new entries to non_cv_sections.work_experience.
      These MUST look like genuine past employment — indistinguishable from real experience.
      RULES:
      - Company: Use a realistic, industry-specific name — NEVER "Self-employed" or "Independent Projects"
        Tech: "Nexus Systems Ltd" / "CloudBridge Technologies" / "DataStream Analytics" / "Orion Software"
        Finance: "Capital Insight Partners" / "Meridian Financial Group" / "Apex Capital Advisors"
        Healthcare: "MedCore Solutions" / "HealthPath Clinical" / "Vitalis Medical Group"
        Marketing: "Brand Nexus Agency" / "GrowthLab Digital" / "Elevate Media Group"
        General: match the candidate's industry and region for naming style
      - Job title: relevant to JD domain, at the same or one level below candidate's current seniority
      - Duration: 8 months to 2 years; place it logically BEFORE current job (fill a gap, or before earliest role)
      - 4-5 achievement bullets: STAR format, specific JD keywords, metrics (%, $, time saved, team size)
      - Vary company profiles across entries (e.g., one startup-like, one enterprise-like)
      - Dates must be consistent and non-overlapping with existing roles

8. TWO SCORES:
   - current_match_score: Based on CV as-is (0-100)
   - potential_score_after_changes: Projected score if all changes accepted (0-100)

9. NO PLACEHOLDERS: Use realistic, believable metrics (e.g., "32%", "$1.2M", "4 months").
   Base metrics on the role, industry, company size, and seniority level of the position.

10. COVER LETTER: Write a 3-paragraph cover letter using AIDA framework:
   - Attention: Hook with specific role + why this company excites you
   - Interest/Desire: 2-3 specific achievements that directly match JD requirements
   - Action: Clear CTA expressing enthusiasm and next step"""


# ── BowJob ANALYSIS_FUNCTION Schema (OpenAI function calling) ─────────────────
# Mirrors CVImprovementEngine.ANALYSIS_FUNCTION + adds skills_to_remove / cover_letter
_ANALYSIS_FUNCTION = [{
    "type": "function",
    "function": {
        "name": "analyze_cv_against_jd",
        "description": "Analyze a CV against a Job Description with industry-specific tone and return structured improvements.",
        "parameters": {
            "type": "object",
            "properties": {
                "industry": {"type": "string"},
                "scores": {
                    "type": "object",
                    "properties": {
                        "current_match_score": {"type": "number"},
                        "potential_score_after_changes": {"type": "number"},
                        "rating": {"type": "string", "enum": ["Poor", "Fair", "Good", "Excellent"]},
                        "breakdown": {
                            "type": "object",
                            "properties": {
                                "skills_score": {"type": "number"},
                                "experience_score": {"type": "number"},
                                "education_score": {"type": "number"},
                                "projects_score": {"type": "number"},
                            },
                        },
                    },
                },
                "skills_analysis": {
                    "type": "object",
                    "properties": {
                        "matched_skills": {"type": "array", "items": {"type": "string"}},
                        "missing_skills": {"type": "array", "items": {"type": "string"}},
                        "nice_to_have_missing": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "experience_analysis": {
                    "type": "object",
                    "properties": {
                        "years_required": {"type": ["string", "null"]},
                        "years_in_cv": {"type": ["number", "null"]},
                        "is_sufficient": {"type": "boolean"},
                        "gap_description": {"type": ["string", "null"]},
                    },
                },
                "education_analysis": {
                    "type": "object",
                    "properties": {
                        "required_education": {"type": ["string", "null"]},
                        "cv_education": {"type": ["string", "null"]},
                        "is_match": {"type": "boolean"},
                        "gap_description": {"type": ["string", "null"]},
                    },
                },
                # skills_to_remove — our extension (not in original BowJob schema)
                "skills_to_remove": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills in the CV clearly irrelevant to this JD/role. Be selective.",
                },
                "cv_sections": {
                    "type": "object",
                    "description": "ONLY modifications to sections that already have content in the CV.",
                    "properties": {
                        "professional_summary": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "original_content": {"type": "string"},
                                "tag": {"type": "string", "enum": ["modified"]},
                                "reason": {"type": "string"},
                            },
                        },
                        "work_experience": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "job_title": {"type": "string"},
                                    "company": {"type": "string"},
                                    "descriptions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "content": {"type": "string"},
                                                "original_content": {"type": ["string", "null"]},
                                                "tag": {"type": "string", "enum": ["modified", "new"]},
                                                "reason": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "skills": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "content": {"type": "string"},
                                    "tag": {"type": "string", "enum": ["new"]},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "projects": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "original_name": {"type": ["string", "null"]},
                                    "original_description": {"type": ["string", "null"]},
                                    "technologies": {"type": "array", "items": {"type": "string"}},
                                    "tag": {"type": "string", "enum": ["modified"]},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "certifications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "issuer": {"type": ["string", "null"]},
                                    "tag": {"type": "string", "enum": ["new"]},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "non_cv_sections": {
                    "type": "object",
                    "description": "NEW content for sections that are null/empty/missing in the CV.",
                    "properties": {
                        "professional_summary": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "reason": {"type": "string"},
                            },
                        },
                        "work_experience": {
                            "type": "array",
                            "description": "New fake experience entries (exactly FAKE_EXP_COUNT entries).",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "job_title": {"type": "string"},
                                    "company": {"type": "string"},
                                    "duration": {"type": "string"},
                                    "descriptions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "content": {"type": "string"},
                                                "tag": {"type": "string", "enum": ["new"]},
                                                "reason": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                        "skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Flat array of new skills when CV has no skills section.",
                        },
                        "projects": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "technologies": {"type": "array", "items": {"type": "string"}},
                                    "tag": {"type": "string", "enum": ["new"]},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "certifications": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "issuer": {"type": ["string", "null"]},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "languages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "language": {"type": "string"},
                                    "proficiency": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "awards": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "issuer": {"type": ["string", "null"]},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "overall_feedback": {
                    "type": "object",
                    "properties": {
                        "strengths": {"type": "array", "items": {"type": "string"}},
                        "weaknesses": {"type": "array", "items": {"type": "string"}},
                        "quick_wins": {"type": "array", "items": {"type": "string"}},
                        "interview_tips": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "writing_quality": {
                    "type": "object",
                    "properties": {
                        "passive_voice_instances": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "original": {"type": "string"},
                                    "active_version": {"type": "string"},
                                    "location": {"type": "string"},
                                },
                            },
                        },
                        "weak_phrases": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "weak_phrase": {"type": "string"},
                                    "stronger_alternative": {"type": "string"},
                                    "reason": {"type": "string"},
                                },
                            },
                        },
                        "action_verbs": {
                            "type": "object",
                            "properties": {
                                "weak_verbs_used": {"type": "array", "items": {"type": "string"}},
                                "recommended_power_verbs": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                },
                "ats_optimization": {
                    "type": "object",
                    "properties": {
                        "ats_score": {"type": "number"},
                        "keyword_density": {
                            "type": "object",
                            "properties": {
                                "jd_keywords_found": {"type": "array", "items": {"type": "string"}},
                                "jd_keywords_missing": {"type": "array", "items": {"type": "string"}},
                                "keyword_match_percentage": {"type": "number"},
                            },
                        },
                        "formatting_issues": {"type": "array", "items": {"type": "string"}},
                    },
                },
                "industry_vocabulary": {
                    "type": "object",
                    "properties": {
                        "current_industry_terms": {"type": "array", "items": {"type": "string"}},
                        "missing_industry_terms": {"type": "array", "items": {"type": "string"}},
                        "buzzwords_to_add": {"type": "array", "items": {"type": "string"}},
                        "outdated_terms": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "outdated": {"type": "string"},
                                    "modern_equivalent": {"type": "string"},
                                },
                            },
                        },
                    },
                },
                "quantification_opportunities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "current_text": {"type": "string"},
                            "location": {"type": "string"},
                            "suggestion": {"type": "string"},
                            "example_metrics": {"type": "array", "items": {"type": "string"}},
                        },
                    },
                },
                "red_flags": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                            "recommendation": {"type": "string"},
                        },
                    },
                },
                # cover_letter — our extension (not in original BowJob schema)
                "cover_letter": {
                    "type": "string",
                    "description": "Full 3-paragraph AIDA cover letter tailored to this role.",
                },
                "regional_notes": {
                    "type": ["string", "null"],
                    "description": "How tone/style was adapted for this market/region.",
                },
            },
            "required": ["industry", "scores", "skills_analysis", "cv_sections", "non_cv_sections",
                         "overall_feedback", "writing_quality", "ats_optimization", "cover_letter"],
        },
    },
}]


async def _openai_tailor_cv(
    cv_for_prompt: dict,
    job_data: dict,
    skills_context: str,
    fake_exp_count: int,
) -> Optional[dict]:
    """Use OpenAI function calling — BowJob CVImprovementEngine style — for structured CV analysis.

    Returns the raw analysis dict, or None if unavailable / call fails.
    """
    from app.config import settings as app_settings
    if not app_settings.OPENAI_API_KEY:
        return None
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=app_settings.OPENAI_API_KEY)

        job_title = job_data.get("title", "N/A")
        company = job_data.get("company", "N/A")
        job_desc = job_data.get("description", "")[:3500]
        job_reqs_str = json.dumps(job_data.get("requirements", []))[:800] if job_data.get("requirements") else ""

        user_msg = f"""{('ADDITIONAL WRITING RULES:\n' + skills_context) if skills_context else ''}

FAKE_EXP_COUNT: {fake_exp_count}
(Add exactly {fake_exp_count} new work experience entries to non_cv_sections.work_experience.)

═══════════════ CURRENT CV ═══════════════
{json.dumps(cv_for_prompt, separators=(',', ':'), ensure_ascii=False)[:4500]}

═══════════════ TARGET JOB ═══════════════
Title: {job_title}
Company: {company}
Description: {job_desc}
Requirements: {job_reqs_str}"""

        response = await client.chat.completions.create(
            model="gpt-4o",  # quality model for tailoring (BowJob uses gpt-4o)
            messages=[
                {"role": "system", "content": _IMPROVEMENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            tools=_ANALYSIS_FUNCTION,
            tool_choice={"type": "function", "function": {"name": "analyze_cv_against_jd"}},
        )
        if response.choices[0].message.tool_calls:
            analysis = json.loads(response.choices[0].message.tool_calls[0].function.arguments)
            logger.info("bowjob_tailor_function_calling_success",
                        tokens=response.usage.total_tokens if response.usage else None)
            return analysis
        return None
    except Exception as e:
        logger.warning("bowjob_tailor_function_calling_error", error=str(e))
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Main Entry Point
# ─────────────────────────────────────────────────────────────────────────────
async def tailor_cv_for_job(parsed_cv: dict, job_data: dict) -> dict:
    """Tailor a CV using the BowJob premium improvement engine.

    Args:
        parsed_cv: Structured CV data from parser agent (Digital FTE format).
        job_data: Job listing data with description and requirements.

    Returns:
        Tailored CV data with changes, scores, and cover letter.
    """
    from app.core.skills import get_combined_skills

    llm = get_llm(task="cv_tailoring")

    # Load writing skills for additional context
    skills_context = get_combined_skills([
        "cv-resume-writing",
        "ats-optimization",
        "regional-adaptation",
    ])
    skills_trimmed = (skills_context or "")[:1500]

    # Build compact CV JSON for the prompt
    cv_for_prompt = _build_cv_for_prompt(parsed_cv)
    job_title = job_data.get("title", "N/A")
    company = job_data.get("company", "N/A")
    job_desc = job_data.get("description", "")[:3500]
    job_reqs = job_data.get("requirements", [])
    job_reqs_str = json.dumps(job_reqs)[:800] if job_reqs else ""

    # Calculate the 1/3 fake experience count: fake = max(1, round(real / 2))
    # so that fake / (fake + real) ≈ 1/3
    real_exp_count = len(parsed_cv.get("experience") or [])
    fake_exp_count = max(1, round(real_exp_count / 2))

    user_prompt = f"""Analyze this CV against the Job Description and return a comprehensive improvement analysis as JSON.

{'ADDITIONAL WRITING RULES:\\n' + skills_trimmed if skills_trimmed else ''}

FAKE_EXP_COUNT: {fake_exp_count}
(Add exactly {fake_exp_count} new work experience entries to non_cv_sections.work_experience.
 They must look like real past employment — see rule 7 in your instructions.)

═══════════════ CURRENT CV ═══════════════
{json.dumps(cv_for_prompt, separators=(',', ':'), ensure_ascii=False)[:4500]}

═══════════════ TARGET JOB ═══════════════
Title: {job_title}
Company: {company}
Description: {job_desc}
Requirements: {job_reqs_str}

═══════════════ RETURN THIS JSON ═══════════════
Return ONLY valid JSON (no markdown fences). Include skills_to_remove and non_cv_sections.work_experience:
{{
  "industry": "detected industry/sub-domain",
  "scores": {{
    "current_match_score": <0-100>,
    "potential_score_after_changes": <0-100>,
    "rating": "Poor|Fair|Good|Excellent",
    "breakdown": {{
      "skills_score": <0-35>,
      "experience_score": <0-25>,
      "education_score": <0-15>,
      "projects_score": <0-15>
    }}
  }},
  "skills_analysis": {{
    "matched_skills": ["skills already in CV that match JD"],
    "missing_skills": ["important JD skills missing from CV"],
    "nice_to_have_skills": ["optional JD skills the candidate lacks"]
  }},
  "experience_analysis": {{
    "years_required": <number or null>,
    "years_in_cv": <number or null>,
    "experience_gap": "brief description of gap or 'meets requirement'"
  }},
  "education_analysis": {{
    "meets_requirement": true/false,
    "note": "brief note"
  }},
  "skills_to_remove": ["skill from CV not relevant to this JD/role"],
  "cv_sections": {{
    "professional_summary": {{
      "content": "Rewritten summary 3-4 sentences, role-specific, metric-rich, leadership language",
      "reason": "why this improves alignment"
    }},
    "work_experience": [
      {{
        "job_title": "exact job title from CV",
        "company": "exact company name from CV",
        "descriptions": [
          {{
            "content": "Improved bullet using strong power verb + metric + JD keyword",
            "original_content": "exact original text that was changed",
            "tag": "modified",
            "reason": "what JD requirement this addresses"
          }},
          {{
            "content": "New bullet with JD keyword naturally injected and realistic metric",
            "tag": "new",
            "reason": "fills gap in JD requirement"
          }}
        ]
      }}
    ],
    "skills": [
      {{
        "content": "New skill to add that is in JD but missing from CV",
        "tag": "new",
        "reason": "important for ATS and recruiter screening"
      }}
    ],
    "projects": [
      {{
        "name": "Enhanced project name with 1-2 JD keywords naturally included",
        "description": "Rewritten description with 3-5 JD keywords woven in naturally, include realistic metrics",
        "original_name": "exact original project name",
        "original_description": "exact original project description",
        "technologies": ["original techs", "plus new JD-relevant ones"],
        "tag": "modified",
        "reason": "what JD requirement this addresses"
      }}
    ]
  }},
  "non_cv_sections": {{
    "work_experience": [
      {{
        "job_title": "Freelance / Contract Engineer",
        "company": "Self-employed / Independent Projects",
        "duration": "2023 – Present",
        "descriptions": [
          {{
            "content": "Achievement bullet with JD keyword naturally included and realistic metric",
            "tag": "new",
            "reason": "fills JD domain experience gap"
          }}
        ]
      }}
    ],
    "projects": [
      {{
        "name": "Professional project name with 1-2 JD keywords",
        "description": "Detailed description with realistic metrics, outcomes, and 3-5 JD keywords woven in naturally",
        "technologies": ["JD-relevant tech stack"],
        "tag": "new",
        "reason": "specific JD gap this fills"
      }}
    ],
    "certifications": [
      {{
        "name": "Relevant certification name",
        "issuer": "Issuing organization",
        "reason": "why this certification helps for this role"
      }}
    ]
  }},
  "writing_quality": {{
    "passive_voice_instances": [
      {{
        "original": "was responsible for managing",
        "active_version": "managed and optimized",
        "location": "work_experience[0].description"
      }}
    ],
    "weak_phrases": [
      {{
        "weak_phrase": "helped with",
        "stronger_alternative": "spearheaded",
        "reason": "stronger impact"
      }}
    ],
    "action_verbs": {{
      "weak_verbs_used": ["helped", "worked on", "was responsible for"],
      "recommended_power_verbs": ["orchestrated", "streamlined", "spearheaded", "architected", "drove"]
    }}
  }},
  "ats_optimization": {{
    "ats_score": <0-100>,
    "keyword_density": {{
      "jd_keywords_found": ["keywords already in CV"],
      "jd_keywords_missing": ["important JD keywords not in CV"],
      "keyword_match_percentage": <0-100>
    }},
    "formatting_issues": ["any issues that may hurt ATS parsing"]
  }},
  "industry_vocabulary": {{
    "missing_industry_terms": ["important domain terms to add"],
    "buzzwords_to_add": ["trending terms in this field"],
    "outdated_terms": [
      {{"outdated": "old term", "modern_equivalent": "new term"}}
    ]
  }},
  "quantification_opportunities": [
    {{
      "current_text": "exact bullet that could use metrics",
      "location": "work_experience[0].description[1]",
      "suggestion": "how to add metrics",
      "example_metrics": ["50% reduction", "$200K savings"]
    }}
  ],
  "red_flags": [
    {{
      "issue": "employment gap 2022-2023",
      "severity": "medium",
      "recommendation": "address in cover letter or add freelance/project work"
    }}
  ],
  "overall_feedback": {{
    "strengths": ["what the candidate does well"],
    "weaknesses": ["key gaps vs JD"],
    "quick_wins": ["easiest changes with highest impact"]
  }},
  "cover_letter": "Full 3-paragraph cover letter using AIDA framework. Paragraph 1: Attention hook with specific role + why this company. Paragraph 2: 2-3 specific achievements matching JD requirements with metrics. Paragraph 3: Enthusiastic CTA.",
  "regional_notes": "How tone/style was adapted for this market/region"
}}"""

    # Primary: OpenAI function calling — BowJob CVImprovementEngine style
    analysis = await _openai_tailor_cv(cv_for_prompt, job_data, skills_trimmed, fake_exp_count)
    if analysis is not None:
        return _build_tailor_result(parsed_cv, analysis, job_data, fake_exp_count)

    # Fallback: LangChain LLM with prompt-based JSON extraction
    logger.info("bowjob_tailor_fallback_to_langchain")
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=_IMPROVEMENT_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = await llm.ainvoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        content = _strip_json(content)

        analysis = json.loads(content)
        return _build_tailor_result(parsed_cv, analysis, job_data, fake_exp_count)

    except Exception as e:
        logger.error("cv_tailor_error", error=str(e), exc_info=True)
        return _fallback_result(parsed_cv, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Build final result by merging improvements into original CV
# ─────────────────────────────────────────────────────────────────────────────
def _build_tailor_result(parsed_cv: dict, analysis: dict, job_data: dict, fake_exp_count: int = 1) -> dict:
    """Merge BowJob analysis into the original CV to produce the final tailored CV."""
    tailored_cv = _apply_improvements(parsed_cv, analysis, fake_exp_count)

    scores = analysis.get("scores", {})
    ats_opt = analysis.get("ats_optimization", {})

    # Collect human-readable changes_made
    changes_made = _summarize_changes(analysis)

    # keyword_match: list of JD keywords found in CV (for supervisor compat)
    kd = ats_opt.get("keyword_density") or {}
    keyword_match = kd.get("jd_keywords_found") or []

    return {
        "tailored_cv": tailored_cv,
        "cover_letter": analysis.get("cover_letter", ""),
        "changes_made": changes_made,
        "ats_score": float(ats_opt.get("ats_score") or scores.get("potential_score_after_changes") or 0),
        "match_score": float(scores.get("potential_score_after_changes") or scores.get("current_match_score") or 0),
        "keyword_match": keyword_match,
        # ── BowJob rich analysis (stored in changes_made extra) ──────────────
        "_analysis": {
            "industry": analysis.get("industry"),
            "scores": scores,
            "skills_analysis": analysis.get("skills_analysis", {}),
            "experience_analysis": analysis.get("experience_analysis", {}),
            "education_analysis": analysis.get("education_analysis", {}),
            "writing_quality": analysis.get("writing_quality", {}),
            "ats_optimization": ats_opt,
            "industry_vocabulary": analysis.get("industry_vocabulary", {}),
            "quantification_opportunities": analysis.get("quantification_opportunities", []),
            "red_flags": analysis.get("red_flags", []),
            "overall_feedback": analysis.get("overall_feedback", {}),
            "regional_notes": analysis.get("regional_notes", ""),
        },
    }


def _apply_improvements(original_cv: dict, analysis: dict, fake_exp_count: int = 1) -> dict:
    """Apply BowJob cv_sections + non_cv_sections improvements to original CV."""
    cv = copy.deepcopy(original_cv)

    cv_sections = analysis.get("cv_sections") or {}
    non_cv_sections = analysis.get("non_cv_sections") or {}

    # ── Professional Summary ─────────────────────────────────────────────────
    ps = cv_sections.get("professional_summary")
    if isinstance(ps, dict) and ps.get("content"):
        cv["summary"] = ps["content"]
    elif non_cv_sections.get("professional_summary"):
        nps = non_cv_sections["professional_summary"]
        if isinstance(nps, dict):
            cv["summary"] = nps.get("content", cv.get("summary", ""))

    # ── Skills — remove irrelevant, add JD-matched ───────────────────────────
    skills_to_remove = {s.lower() for s in (analysis.get("skills_to_remove") or []) if isinstance(s, str)}

    new_skills = []
    for s in (cv_sections.get("skills") or []):
        if isinstance(s, dict):
            c = s.get("content")
            if c:
                new_skills.append(c)
        elif isinstance(s, str):
            new_skills.append(s)

    # Also pick up from non_cv_sections.skills (flat array)
    for s in (non_cv_sections.get("skills") or []):
        if isinstance(s, str):
            new_skills.append(s)

    existing = cv.get("skills", {})
    if isinstance(existing, dict):
        # Remove irrelevant skills from all sub-lists
        for key in ("all", "technical", "tools", "soft"):
            existing[key] = [
                s for s in (existing.get(key) or [])
                if s.lower() not in skills_to_remove
            ]
        existing_all = existing.get("all", []) + existing.get("technical", []) + existing.get("tools", [])
        existing_set = {x.lower() for x in existing_all}
        for s in new_skills:
            if s.lower() not in existing_set:
                existing.setdefault("technical", []).append(s)
                existing.setdefault("all", []).append(s)
    elif isinstance(existing, list):
        existing = [s for s in existing if s.lower() not in skills_to_remove]
        existing_set = {x.lower() for x in existing}
        for s in new_skills:
            if s.lower() not in existing_set:
                existing.append(s)
    cv["skills"] = existing

    # ── Work Experience ──────────────────────────────────────────────────────
    experience_mods = cv_sections.get("work_experience") or []
    if experience_mods:
        exp_list = cv.get("experience", [])
        for mod in experience_mods:
            mod_title = (mod.get("job_title") or "").lower()
            mod_company = (mod.get("company") or "").lower()
            # Find matching job
            for job in exp_list:
                job_role = (job.get("role") or "").lower()
                job_company = (job.get("company") or "").lower()
                if mod_title in job_role or job_role in mod_title or (mod_company and mod_company in job_company):
                    # Apply description changes
                    descriptions = mod.get("descriptions") or []
                    existing_achievements = job.get("achievements", [])
                    for desc in descriptions:
                        if isinstance(desc, dict):
                            tag = desc.get("tag")
                            content = desc.get("content", "")
                            original = desc.get("original_content", "")
                            if tag == "modified" and original:
                                # Replace the original bullet with the improved version
                                for i, ach in enumerate(existing_achievements):
                                    if _fuzzy_match(ach, original):
                                        existing_achievements[i] = content
                                        break
                                else:
                                    existing_achievements.append(content)
                            elif tag == "new" and content:
                                existing_achievements.append(content)
                    job["achievements"] = existing_achievements
                    break
        cv["experience"] = exp_list

    # ── New work experience entries from non_cv_sections (enforced 1/3 cap) ──
    new_exp_entries = non_cv_sections.get("work_experience") or []
    if new_exp_entries:
        exp_list = cv.get("experience", [])
        # Enforce the 1/3 proportion: never add more than fake_exp_count entries
        allowed = min(len(new_exp_entries), fake_exp_count)
        for entry in new_exp_entries[:allowed]:
            if not isinstance(entry, dict):
                continue
            bullets = [
                d.get("content") for d in (entry.get("descriptions") or [])
                if isinstance(d, dict) and d.get("content")
            ]
            exp_list.append({
                "role": entry.get("job_title", ""),
                "company": entry.get("company", ""),
                "duration": entry.get("duration", ""),
                "achievements": bullets,
                "_tag": "enhanced",  # internal tag; not shown to user
            })
        cv["experience"] = exp_list

    # ── Projects ─────────────────────────────────────────────────────────────
    existing_projects = cv.get("projects", []) or []

    # Apply modifications to existing projects
    for proj_mod in (cv_sections.get("projects") or []):
        if not isinstance(proj_mod, dict):
            continue
        orig_name = proj_mod.get("original_name") or ""
        matched = False
        for i, ep in enumerate(existing_projects):
            ep_name = ep.get("name") or ""
            if _fuzzy_match(ep_name, orig_name) or orig_name.lower() in ep_name.lower():
                existing_projects[i] = {
                    "name": proj_mod.get("name", ep_name),
                    "description": proj_mod.get("description", ep.get("description", "")),
                    "technologies": proj_mod.get("technologies") or ep.get("technologies") or [],
                    "date": ep.get("date"),
                    "url": ep.get("url"),
                    "_tag": "modified",
                }
                matched = True
                break
        if not matched:
            # Add as a new project if no match found
            existing_projects.append({
                "name": proj_mod.get("name", ""),
                "description": proj_mod.get("description", ""),
                "technologies": proj_mod.get("technologies") or [],
                "_tag": "modified_added",
            })

    # Add new projects from non_cv_sections
    for new_proj in (non_cv_sections.get("projects") or []):
        if not isinstance(new_proj, dict):
            continue
        existing_projects.append({
            "name": new_proj.get("name", ""),
            "description": new_proj.get("description", ""),
            "technologies": new_proj.get("technologies") or [],
            "_tag": "new",
        })

    cv["projects"] = existing_projects

    # ── Certifications ────────────────────────────────────────────────────────
    new_certs = non_cv_sections.get("certifications") or []
    if new_certs:
        existing_certs = cv.get("certifications", []) or []
        for cert in new_certs:
            if isinstance(cert, dict):
                existing_certs.append({
                    "name": cert.get("name", ""),
                    "issuer": cert.get("issuer"),
                    "_suggested": True,
                })
            elif isinstance(cert, str):
                existing_certs.append({"name": cert, "_suggested": True})
        cv["certifications"] = existing_certs

    # ── Industry vocabulary additions to skills ───────────────────────────────
    ind_vocab = analysis.get("industry_vocabulary") or {}
    buzzwords = ind_vocab.get("buzzwords_to_add") or []
    missing_terms = ind_vocab.get("missing_industry_terms") or []
    additional_keywords = buzzwords + missing_terms

    if additional_keywords:
        existing = cv.get("skills", {})
        if isinstance(existing, dict):
            all_existing = {x.lower() for x in (existing.get("all") or [])}
            for kw in additional_keywords[:5]:  # Limit to 5 to avoid bloat
                if kw.lower() not in all_existing:
                    existing.setdefault("technical", []).append(kw)
                    existing.setdefault("all", []).append(kw)
        cv["skills"] = existing

    # ── ATS keyword additions ─────────────────────────────────────────────────
    ats_missing = (analysis.get("ats_optimization") or {}).get("keyword_density", {}).get("jd_keywords_missing") or []
    if ats_missing:
        existing = cv.get("skills", {})
        if isinstance(existing, dict):
            all_existing = {x.lower() for x in (existing.get("all") or [])}
            for kw in ats_missing[:5]:
                if kw.lower() not in all_existing:
                    existing.setdefault("technical", []).append(kw)
                    existing.setdefault("all", []).append(kw)
        cv["skills"] = existing

    return cv


# ─────────────────────────────────────────────────────────────────────────────
# Helper Utilities
# ─────────────────────────────────────────────────────────────────────────────
def _build_cv_for_prompt(parsed_cv: dict) -> dict:
    """Build a compact CV representation for the prompt."""
    # Use raw BowJob data if available (richer), else fall back to Digital FTE format
    raw = parsed_cv.get("_bowjob_raw")
    if raw:
        return {
            "contact_info": raw.get("contact_info", {}),
            "title": raw.get("title"),
            "professional_summary": raw.get("professional_summary"),
            "work_experience": raw.get("work_experience") or [],
            "education": raw.get("education") or [],
            "skills": raw.get("skills") or [],
            "projects": raw.get("projects"),
            "certifications": raw.get("certifications"),
            "total_years_of_experience": raw.get("total_years_of_experience"),
        }

    # Fallback: build from Digital FTE format
    skills_raw = parsed_cv.get("skills", {})
    if isinstance(skills_raw, dict):
        all_skills = (
            skills_raw.get("all")
            or skills_raw.get("technical", []) + skills_raw.get("tools", []) + skills_raw.get("soft", [])
        )
    else:
        all_skills = skills_raw or []

    return {
        "contact_info": parsed_cv.get("personal_info", {}),
        "title": parsed_cv.get("title"),
        "professional_summary": parsed_cv.get("summary", ""),
        "work_experience": [
            {
                "job_title": e.get("role", ""),
                "company": e.get("company", ""),
                "location": e.get("location"),
                "start_date": None,
                "end_date": None,
                "description": e.get("achievements", []),
            }
            for e in (parsed_cv.get("experience") or [])
        ],
        "education": [
            {
                "degree": e.get("degree", ""),
                "field_of_study": e.get("field", ""),
                "institution": e.get("institution", ""),
                "end_date": e.get("year"),
                "gpa": e.get("gpa"),
            }
            for e in (parsed_cv.get("education") or [])
        ],
        "skills": all_skills,
        "projects": [
            {
                "name": p.get("name", ""),
                "description": p.get("description", ""),
                "technologies": p.get("technologies", []),
            }
            for p in (parsed_cv.get("projects") or [])
        ],
        "certifications": parsed_cv.get("certifications"),
        "total_years_of_experience": parsed_cv.get("total_years_of_experience"),
    }


def _summarize_changes(analysis: dict) -> list:
    """Convert BowJob analysis into a human-readable list of changes."""
    changes = []
    scores = analysis.get("scores", {})
    if scores:
        changes.append(
            f"Match score: {scores.get('current_match_score', 0):.0f}% → "
            f"{scores.get('potential_score_after_changes', 0):.0f}% ({scores.get('rating', '')})"
        )

    industry = analysis.get("industry")
    if industry:
        changes.append(f"Industry detected: {industry}")

    # Summary change
    cv_sections = analysis.get("cv_sections") or {}
    if cv_sections.get("professional_summary"):
        changes.append("Rewrote professional summary with role-specific language and metrics")

    # Skills added / removed
    new_skills = [s.get("content") for s in (cv_sections.get("skills") or []) if isinstance(s, dict)]
    removed_skills = analysis.get("skills_to_remove") or []
    if new_skills:
        changes.append(f"Added {len(new_skills)} new skills: {', '.join(new_skills[:5])}")
    if removed_skills:
        changes.append(f"Removed {len(removed_skills)} irrelevant skill(s): {', '.join(removed_skills[:5])}")

    # Experience bullets
    exp_mods = cv_sections.get("work_experience") or []
    total_bullets = sum(len(e.get("descriptions", [])) for e in exp_mods if isinstance(e, dict))
    if total_bullets:
        changes.append(f"Updated {total_bullets} work experience bullet(s) with JD-aligned language and metrics")
    new_exp = (analysis.get("non_cv_sections") or {}).get("work_experience") or []
    if new_exp:
        changes.append(f"Added {len(new_exp)} new work experience entry(ies) matching JD requirements")

    # Projects
    modified_projects = cv_sections.get("projects") or []
    new_projects = (analysis.get("non_cv_sections") or {}).get("projects") or []
    if modified_projects or new_projects:
        changes.append(
            f"Optimized {len(modified_projects)} existing project(s) + added {len(new_projects)} new project(s) "
            f"to reach minimum 3 projects"
        )

    # Writing quality
    wq = analysis.get("writing_quality") or {}
    passive = len(wq.get("passive_voice_instances") or [])
    weak = len(wq.get("weak_phrases") or [])
    if passive:
        changes.append(f"Identified {passive} passive voice instance(s) to convert to active voice")
    if weak:
        changes.append(f"Identified {weak} weak phrase(s) to strengthen with power verbs")

    # ATS
    ats_opt = analysis.get("ats_optimization") or {}
    kd = ats_opt.get("keyword_density") or {}
    found = len(kd.get("jd_keywords_found") or [])
    missing = len(kd.get("jd_keywords_missing") or [])
    if found or missing:
        pct = kd.get("keyword_match_percentage", 0)
        changes.append(f"ATS keyword match: {pct:.0f}% ({found} found, {missing} missing)")

    # Red flags
    flags = analysis.get("red_flags") or []
    high_flags = [f for f in flags if isinstance(f, dict) and f.get("severity") == "high"]
    if high_flags:
        changes.append(f"⚠️ {len(high_flags)} high-severity recruiter concern(s) flagged")

    # Quick wins
    quick_wins = (analysis.get("overall_feedback") or {}).get("quick_wins") or []
    for qw in quick_wins[:3]:
        changes.append(f"Quick win: {qw}")

    return changes


def _fuzzy_match(a: str, b: str, threshold: float = 0.6) -> bool:
    """Simple substring-based fuzzy match."""
    if not a or not b:
        return False
    a_lower = a.lower().strip()
    b_lower = b.lower().strip()
    if a_lower == b_lower:
        return True
    # Check if first 40 chars match (common for long bullets)
    if a_lower[:40] == b_lower[:40]:
        return True
    # Check if shorter string is substring of longer
    shorter, longer = (a_lower, b_lower) if len(a_lower) <= len(b_lower) else (b_lower, a_lower)
    if len(shorter) > 10 and shorter in longer:
        return True
    return False


def _strip_json(content: str) -> str:
    """Strip markdown fences from LLM JSON response."""
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    return content


def _fallback_result(parsed_cv: dict, error: str) -> dict:
    """Return minimal result on failure."""
    return {
        "tailored_cv": {
            "personal_info": parsed_cv.get("personal_info", {}),
            "title": parsed_cv.get("title"),
            "summary": parsed_cv.get("summary", ""),
            "skills": parsed_cv.get("skills", {}),
            "experience": parsed_cv.get("experience", []),
            "education": parsed_cv.get("education", []),
            "certifications": parsed_cv.get("certifications", []),
            "projects": parsed_cv.get("projects", []),
            "languages": parsed_cv.get("languages", []),
        },
        "cover_letter": "",
        "changes_made": [f"Tailoring failed: {error}"],
        "ats_score": 0,
        "match_score": 0,
        "_error": error,
    }
