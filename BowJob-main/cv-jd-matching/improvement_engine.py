"""
CV Improvement Engine using OpenAI GPT-4o-mini.
Analyzes CVs against Job Descriptions and provides comprehensive improvement suggestions.
"""

import json
from typing import Dict, Any, Optional
from openai import OpenAI


class CVImprovementEngine:
    """Engine for CV-JD matching and improvement suggestions."""

    ANALYSIS_FUNCTION = [{
        "type": "function",
        "function": {
            "name": "analyze_cv_against_jd",
            "description": "Analyze a CV against a Job Description with industry-specific tone",
            "parameters": {
                "type": "object",
                "properties": {
                    "industry": {
                        "type": "string",
                        "description": "Detected industry/niche (e.g., 'technology', 'finance', 'healthcare', 'marketing')"
                    },
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
                                    "projects_score": {"type": "number"}
                                }
                            }
                        }
                    },
                    "skills_analysis": {
                        "type": "object",
                        "properties": {
                            "matched_skills": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "missing_skills": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "nice_to_have_missing": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        }
                    },
                    "experience_analysis": {
                        "type": "object",
                        "properties": {
                            "years_required": {"type": "string"},
                            "years_in_cv": {"type": "number"},
                            "is_sufficient": {"type": "boolean"},
                            "gap_description": {"type": ["string", "null"]}
                        }
                    },
                    "education_analysis": {
                        "type": "object",
                        "properties": {
                            "required_education": {"type": ["string", "null"]},
                            "cv_education": {"type": ["string", "null"]},
                            "is_match": {"type": "boolean"},
                            "gap_description": {"type": ["string", "null"]}
                        }
                    },
                    "cv_sections": {
                        "type": "object",
                        "description": "ONLY MODIFICATIONS to sections that HAVE EXISTING CONTENT in CV. If a section is null/empty/missing in CV, do NOT put new content here - put it in non_cv_sections instead.",
                        "properties": {
                            "title": {
                                "type": "object",
                                "description": "Only if title needs modification",
                                "properties": {
                                    "content": {"type": "string", "description": "Modified title"},
                                    "original_content": {"type": "string", "description": "Original title from CV"},
                                    "tag": {"type": "string", "enum": ["modified"]},
                                    "reason": {"type": "string"}
                                }
                            },
                            "professional_summary": {
                                "type": "object",
                                "description": "Only if summary needs modification",
                                "properties": {
                                    "content": {"type": "string", "description": "Modified summary"},
                                    "original_content": {"type": "string", "description": "Original summary from CV"},
                                    "tag": {"type": "string", "enum": ["modified"]},
                                    "reason": {"type": "string"}
                                }
                            },
                            "work_experience": {
                                "type": "array",
                                "description": "Only jobs with modifications or new responsibilities or projects that inject keywords from the job description and make story around those keywords or niche or required experience type",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "job_title": {"type": "string"},
                                        "company": {"type": "string"},
                                        "descriptions": {
                                            "type": "array",
                                            "description": "Only modified or new descriptions that inject keywords from the job description and make story around those keywords or niche or required experience type",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "content": {"type": "string"},
                                                    "original_content": {"type": "string", "description": "Only for modified - original text"},
                                                    "tag": {"type": "string", "enum": ["modified", "new"]},
                                                    "reason": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            },
                            "skills": {
                                "type": "array",
                                "description": "Only NEW skills to add (not already in CV). These are JD keywords important for ATS and recruiter screening.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "content": {"type": "string", "description": "The skill to add"},
                                        "tag": {"type": "string", "enum": ["new"]},
                                        "reason": {"type": "string", "description": "Why this skill is important for this JD"}
                                    }
                                }
                            },
                            "projects": {
                                "type": "array",
                                "description": "MODIFIED existing projects with JD keywords naturally injected. Modify 1-2 existing projects that can be aligned with JD requirements. Part of the MINIMUM 3 projects requirement.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Original or enhanced name with 1-2 JD keywords naturally included"},
                                        "description": {"type": "string", "description": "Rewritten description with 3-5 JD keywords woven in naturally"},
                                        "original_name": {"type": "string", "description": "Exact original project name"},
                                        "original_description": {"type": "string", "description": "Exact original project description"},
                                        "technologies": {"type": "array", "items": {"type": "string"}, "description": "Original + new JD-relevant technologies"},
                                        "tag": {"type": "string", "enum": ["modified"]},
                                        "reason": {"type": "string", "description": "What JD requirement this addresses"}
                                    }
                                }
                            },
                            "certifications": {
                                "type": "array",
                                "description": "ONLY if CV has EXISTING certifications with content - add modifications here. If CV certifications is null/empty, put new certs in non_cv_sections.certifications instead!",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "issuer": {"type": "string"},
                                        "tag": {"type": "string", "enum": ["new"]},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "non_cv_sections": {
                        "type": "object",
                        "description": "NEW content for sections that are NULL, EMPTY, or MISSING in CV. If CV has certifications:null → put new certs HERE. If CV has soft_skills:null → put new soft skills HERE. If CV has awards:null → suggest awards HERE.",
                        "properties": {
                            "professional_summary": {
                                "type": "object",
                                "description": "Only if CV has NO summary section",
                                "properties": {
                                    "content": {"type": "string"},
                                    "reason": {"type": "string"}
                                }
                            },
                            "work_experience": {
                                "type": "array",
                                "description": "Only if CV has NO work experience section - suggest relevant experience entries",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "job_title": {"type": "string"},
                                        "company": {"type": "string"},
                                        "descriptions": {"type": "array", "items": {"type": "string"}},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "education": {
                                "type": "array",
                                "description": "Only if CV has NO education section - suggest relevant education",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "degree": {"type": "string"},
                                        "institution": {"type": "string"},
                                        "field": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "skills": {
                                "type": "array",
                                "description": "If CV has NO skills or skills is null/empty - put ALL new skills HERE as flat array",
                                "items": {"type": "string"}
                            },
                            "certifications": {
                                "type": "array",
                                "description": "If CV certifications is null/empty/missing - put NEW certifications HERE (not in cv_sections)",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "issuer": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "projects": {
                                "type": "array",
                                "description": "NEW projects when CV HAS a projects section. Add 1-2 NEW projects to reach MINIMUM 3 total. Each project has JD keywords naturally injected in title and description. If CV has NO projects section, inject projects into work_experience instead.",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "Professional project name with 1-2 JD keywords naturally included"},
                                        "description": {"type": "string", "description": "Detailed description with metrics, outcomes, and 3-5 JD keywords woven in naturally"},
                                        "technologies": {"type": "array", "items": {"type": "string"}, "description": "JD-relevant tech stack"},
                                        "reason": {"type": "string", "description": "Specific JD gap this project fills"},
                                        "tag": {"type": "string", "enum": ["new"], "description": "Always 'new' for non_cv_sections projects"}
                                    }
                                }
                            },
                            "publications": {
                                "type": "array",
                                "description": "Only if CV has NO publications but JD requires research/publishing",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "publisher": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "languages": {
                                "type": "array",
                                "description": "Only if CV has NO languages section but JD requires language skills",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "language": {"type": "string"},
                                        "proficiency": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "awards": {
                                "type": "array",
                                "description": "If CV awards/awards_scholarships is null/empty - suggest relevant awards HERE",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "issuer": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "volunteer_experience": {
                                "type": "array",
                                "description": "Only if CV has NO volunteer section but JD values community involvement",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "role": {"type": "string"},
                                        "organization": {"type": "string"},
                                        "description": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "other_sections": {
                                "type": "array",
                                "description": "Any OTHER missing sections important for JD not covered above",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "section_name": {"type": "string"},
                                        "content": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "overall_feedback": {
                        "type": "object",
                        "properties": {
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "weaknesses": {"type": "array", "items": {"type": "string"}},
                            "quick_wins": {"type": "array", "items": {"type": "string"}},
                            "interview_tips": {"type": "array", "items": {"type": "string"}}
                        }
                    },
                    "writing_quality": {
                        "type": "object",
                        "description": "Analysis of writing quality, grammar, and professional tone",
                        "properties": {
                            "grammar_issues": {
                                "type": "array",
                                "description": "Grammatical errors found with corrections",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "original": {"type": "string"},
                                        "corrected": {"type": "string"},
                                        "location": {"type": "string", "description": "Where in CV (e.g., 'professional_summary', 'work_experience[0].description[2]')"},
                                        "issue_type": {"type": "string", "enum": ["grammar", "spelling", "punctuation", "capitalization"]}
                                    }
                                }
                            },
                            "tone_analysis": {
                                "type": "object",
                                "properties": {
                                    "current_tone": {"type": "string", "description": "e.g., 'casual', 'professional', 'overly formal', 'inconsistent'"},
                                    "recommended_tone": {"type": "string"},
                                    "tone_issues": {"type": "array", "items": {"type": "string"}, "description": "Specific tone problems found"}
                                }
                            },
                            "passive_voice_instances": {
                                "type": "array",
                                "description": "Passive voice phrases that should be active",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "original": {"type": "string"},
                                        "active_version": {"type": "string"},
                                        "location": {"type": "string"}
                                    }
                                }
                            },
                            "weak_phrases": {
                                "type": "array",
                                "description": "Weak or vague phrases that should be strengthened",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "weak_phrase": {"type": "string"},
                                        "stronger_alternative": {"type": "string"},
                                        "reason": {"type": "string"}
                                    }
                                }
                            },
                            "action_verbs": {
                                "type": "object",
                                "properties": {
                                    "weak_verbs_used": {"type": "array", "items": {"type": "string"}, "description": "Weak verbs like 'helped', 'worked on', 'responsible for'"},
                                    "recommended_power_verbs": {"type": "array", "items": {"type": "string"}, "description": "Strong action verbs for this industry"}
                                }
                            }
                        }
                    },
                    "ats_optimization": {
                        "type": "object",
                        "description": "Applicant Tracking System compatibility analysis",
                        "properties": {
                            "ats_score": {"type": "number", "description": "Estimated ATS compatibility score 0-100"},
                            "keyword_density": {
                                "type": "object",
                                "properties": {
                                    "jd_keywords_found": {"type": "array", "items": {"type": "string"}},
                                    "jd_keywords_missing": {"type": "array", "items": {"type": "string"}},
                                    "keyword_match_percentage": {"type": "number"}
                                }
                            },
                            "formatting_issues": {
                                "type": "array",
                                "description": "Formatting problems that may cause ATS parsing issues",
                                "items": {"type": "string"}
                            },
                            "section_headers": {
                                "type": "object",
                                "properties": {
                                    "standard_headers_used": {"type": "array", "items": {"type": "string"}},
                                    "non_standard_headers": {"type": "array", "items": {"type": "string"}, "description": "Headers that ATS might not recognize"},
                                    "recommended_headers": {"type": "array", "items": {"type": "string"}}
                                }
                            }
                        }
                    },
                    "industry_vocabulary": {
                        "type": "object",
                        "description": "Industry-specific terminology and jargon analysis",
                        "properties": {
                            "current_industry_terms": {"type": "array", "items": {"type": "string"}, "description": "Domain terms already in CV"},
                            "missing_industry_terms": {"type": "array", "items": {"type": "string"}, "description": "Important industry terms to add"},
                            "buzzwords_to_add": {"type": "array", "items": {"type": "string"}, "description": "Trending terms in this field"},
                            "outdated_terms": {
                                "type": "array",
                                "description": "Outdated terminology that should be updated",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "outdated": {"type": "string"},
                                        "modern_equivalent": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "quantification_opportunities": {
                        "type": "array",
                        "description": "Places where metrics/numbers could be added to strengthen impact",
                        "items": {
                            "type": "object",
                            "properties": {
                                "current_text": {"type": "string"},
                                "location": {"type": "string"},
                                "suggestion": {"type": "string", "description": "How to add metrics"},
                                "example_metrics": {"type": "array", "items": {"type": "string"}, "description": "Types of metrics that could be used"}
                            }
                        }
                    },
                    "red_flags": {
                        "type": "array",
                        "description": "Potential concerns a recruiter might have",
                        "items": {
                            "type": "object",
                            "properties": {
                                "issue": {"type": "string"},
                                "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                                "recommendation": {"type": "string", "description": "How to address or mitigate this"}
                            }
                        }
                    },
                    "length_analysis": {
                        "type": "object",
                        "properties": {
                            "current_length": {"type": "string", "description": "e.g., 'too long', 'appropriate', 'too short'"},
                            "recommended_length": {"type": "string"},
                            "sections_to_trim": {"type": "array", "items": {"type": "string"}},
                            "sections_to_expand": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "required": ["industry", "scores", "skills_analysis", "experience_analysis", "education_analysis", "cv_sections", "non_cv_sections", "overall_feedback", "writing_quality", "ats_optimization", "industry_vocabulary"]
            }
        }
    }]

    SYSTEM_PROMPT = """You are an expert HR analyst and CV optimization specialist.
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
   - Clinical/Hospital: "patient outcomes", "clinical trials", "EHR/EMR", "care pathways", "treatment protocols", "discharge planning"
   - Pharma/Biotech: "drug discovery", "FDA approval", "clinical phases", "molecular targets", "GxP compliance"
   - Health Tech/Digital Health: "HIPAA compliance", "telemedicine", "remote monitoring", "health informatics", "interoperability"
   - Medical Devices: "regulatory clearance", "ISO 13485", "clinical validation", "510(k)", "design controls"
   - Health Insurance: "claims adjudication", "provider networks", "utilization management", "HEDIS measures"

   MARKETING & ADVERTISING:
   - Digital Marketing: "SEO/SEM", "conversion optimization", "marketing automation", "attribution modeling", "programmatic"
   - Brand Management: "brand equity", "market positioning", "consumer insights", "brand architecture", "go-to-market"
   - Growth/Performance: "CAC/LTV", "funnel optimization", "retention metrics", "viral coefficient", "cohort analysis"
   - Content/Social: "engagement rates", "content strategy", "influencer marketing", "community building", "UGC"
   - Product Marketing: "positioning", "competitive analysis", "launch strategy", "sales enablement", "win/loss analysis"

   CONSULTING & PROFESSIONAL SERVICES:
   - Management Consulting: "strategic roadmap", "operational excellence", "change management", "stakeholder alignment", "workstreams"
   - Legal: "due diligence", "contract negotiation", "regulatory compliance", "litigation support", "IP protection"
   - Accounting/Audit: "GAAP/IFRS", "internal controls", "SOX compliance", "audit procedures", "financial reporting"
   - Tax: "tax planning", "transfer pricing", "tax compliance", "tax provisions", "tax credits"

   MANUFACTURING & SUPPLY CHAIN:
   - Operations/Manufacturing: "lean manufacturing", "Six Sigma", "OEE", "capacity planning", "yield optimization", "kaizen"
   - Supply Chain/Logistics: "demand forecasting", "inventory optimization", "logistics", "procurement", "S&OP"
   - Quality Assurance: "SPC", "root cause analysis", "CAPA", "ISO 9001", "quality audits"
   - Engineering: "product design", "CAD/CAM", "prototyping", "DFM", "tolerance analysis"

   E-COMMERCE & RETAIL:
   - E-commerce: "conversion rate", "cart abandonment", "product recommendations", "fulfillment", "marketplace"
   - Retail Operations: "merchandising", "inventory turnover", "omnichannel", "store operations", "planogram"
   - Customer Experience: "NPS", "customer journey", "loyalty programs", "personalization", "voice of customer"

   ENERGY & UTILITIES:
   - Oil & Gas: "upstream/downstream", "reservoir engineering", "HSE", "drilling optimization", "production"
   - Renewable Energy: "capacity factor", "grid integration", "PPA", "carbon credits", "energy storage"
   - Utilities: "demand response", "smart grid", "SCADA", "load forecasting", "rate design"

   REAL ESTATE & CONSTRUCTION:
   - Real Estate: "cap rate", "NOI", "property management", "lease negotiations", "asset valuation"
   - Construction: "project scheduling", "cost estimation", "BIM", "safety compliance", "subcontractor management"
   - Architecture/Design: "space planning", "building codes", "sustainability", "LEED", "design development"

   EDUCATION & RESEARCH:
   - Higher Education: "curriculum development", "accreditation", "student outcomes", "research grants", "faculty development"
   - K-12 Education: "lesson planning", "student assessment", "classroom management", "parent engagement"
   - EdTech: "learning outcomes", "engagement metrics", "adaptive learning", "LMS", "content delivery"
   - Research: "grant writing", "peer review", "methodology", "data collection", "publication"

   GOVERNMENT & PUBLIC SECTOR:
   - Government: "policy implementation", "public procurement", "citizen services", "regulatory frameworks", "compliance"
   - Defense/Aerospace: "mission critical", "security clearance", "defense contracts", "tactical systems", "ITAR"
   - Non-Profit: "fundraising", "grant management", "impact measurement", "donor relations", "program evaluation"

   HR & TALENT:
   - HR Operations: "talent acquisition", "employee engagement", "performance management", "HRIS", "compensation"
   - Recruiting: "candidate pipeline", "time-to-hire", "offer acceptance rate", "employer branding", "sourcing"
   - L&D: "training programs", "skill development", "leadership development", "e-learning", "competency frameworks"
   - DEIB: "diversity initiatives", "inclusion programs", "equity analysis", "belonging metrics"

   MEDIA & ENTERTAINMENT:
   - Film/TV Production: "pre-production", "post-production", "content licensing", "distribution", "ratings"
   - Gaming: "game design", "player engagement", "monetization", "live ops", "community management"
   - Publishing: "editorial", "content strategy", "audience development", "subscription", "syndication"
   - Music: "artist management", "licensing", "streaming", "royalties", "catalog management"

   HOSPITALITY & TRAVEL:
   - Hotels: "RevPAR", "occupancy", "guest experience", "yield management", "loyalty programs"
   - Airlines: "revenue management", "load factor", "on-time performance", "route optimization"
   - Food & Beverage: "menu engineering", "food cost", "table turnover", "health compliance"

   TELECOMMUNICATIONS:
   - Network: "network optimization", "5G", "spectrum management", "capacity planning", "latency"
   - Product: "subscriber growth", "ARPU", "churn reduction", "bundle optimization"

2. OUTPUT ONLY CHANGES - DO NOT RETURN UNTOUCHED CONTENT:

   RETURN THESE:
   - "modified": Content that was improved (include original_content field showing what was changed)
   - "new": Completely new content added for JD alignment

   DO NOT RETURN:
   - Original content that has NO modification (skip it entirely)
   - Untouched sections (don't include them in output)

3. CRITICAL: cv_sections vs non_cv_sections DISTINCTION:

   cv_sections = ONLY for MODIFYING existing content that HAS DATA in CV
   non_cv_sections = For NEW content where CV section is NULL, EMPTY, or MISSING

   EXAMPLES:
   - CV has "certifications": null → Put new certs in non_cv_sections.certifications
   - CV has "certifications": [{...}] → Put modified certs in cv_sections.certifications
   - CV has "soft_skills": null → Put new soft skills in non_cv_sections.skills.soft_skills
   - CV has "awards_scholarships": null → Put suggested awards in non_cv_sections.awards
   - CV has "languages": null → Put new languages in non_cv_sections.languages

   CHECK EACH SECTION: If the value is null, empty array [], or key missing → use non_cv_sections

4. FOR MODIFIED CONTENT - ALWAYS INCLUDE original_content:
   When tag is "modified", you MUST include:
   - "content": the improved version
   - "original_content": the exact original text that was modified
   - "reason": why this modification improves alignment with JD

5. ANALYZE EACH CV ITEM:
   - If it CAN be aligned with JD → create modified version with original_content
   - If it CANNOT be aligned (completely unrelated) → SKIP IT (don't include in output)
   - Add NEW items to fill JD gaps

6. PROJECTS - CRITICAL FOCUS AREA (MINIMUM 3 REQUIRED):

   *** MANDATORY: Return AT LEAST 3 highly relevant projects total ***

   SCENARIO A - CV HAS PROJECTS SECTION (projects is not null):
   - Modify 1-2 existing projects for JD alignment → cv_sections.projects
   - Add 1-2 NEW projects → non_cv_sections.projects
   - TOTAL must be at least 3 projects

   SCENARIO B - CV HAS NO PROJECTS SECTION (projects is null):
   - Generate 3+ project-style achievements
   - Inject as enhanced bullet points into cv_sections.work_experience[].descriptions
   - Each injected project should:
     * Read like a significant achievement/responsibility
     * Include metrics and JD keywords
     * Have tag: "new" with reason explaining it addresses JD requirements
     * Be placed under the most relevant job (match by role/industry)

   NATURAL KEYWORD INJECTION:
   - Extract top 10-15 keywords from JD (technical terms, tools, methodologies)
   - For each project:
     * Title: Include 1-2 keywords naturally (e.g., "AI-Powered Analytics Dashboard" NOT "AI ML Python Dashboard")
     * Description: Weave in 3-5 keywords in context
     * Technologies: List JD-required tech stack
   - Keywords must flow naturally - avoid keyword stuffing
   - Each project should target DIFFERENT JD requirements

   PROJECT OUTPUT STRUCTURE:
   For MODIFIED projects (in cv_sections.projects):
   - name: same or slightly enhanced with 1-2 JD keywords
   - description: rewritten to align with JD, naturally inject keywords
   - original_description: exact original text
   - technologies: original + new relevant ones from JD
   - tag: "modified"
   - reason: what JD requirement this addresses

   For NEW projects (in non_cv_sections.projects OR as work_experience descriptions):
   - name: descriptive, professional, includes JD keywords naturally
   - description: detailed with metrics, outcomes, and 3-5 JD keywords woven in
   - technologies: JD-relevant stack
   - tag: "new"
   - reason: specific JD gap this fills

7. SKILLS:
   - Only return NEW skills (JD keywords to add)
   - Don't list original skills that need no change

8. TWO SCORES:
   - current_match_score: Based on CV as-is
   - potential_score_after_changes: Projected score if all changes accepted

EXAMPLE OUTPUT STRUCTURE:

"work_experience": [
  {
    "job_title": "Software Engineer",
    "company": "Tech Corp",
    "descriptions": [
      {
        "content": "Architected microservices platform  for internal reporting that reduced latency by 40%",
        "original_content": "Built internal reporting tool",
        "tag": "modified",
        "reason": "Added metrics and JD-aligned terminology"
      },
      {
        "content": "Implemented CI/CD pipelines with 99.9% deployment success",
        "tag": "new",
        "reason": "JD requires CI/CD experience"
      }
    ]
  }
]

"projects": [
  {
    "name": "RAG System for Medical Articles with Compliance Controls",
    "description": "Built RAFT system for clinical article appraisal integrating bias detection algorithms and explainability layers, ensuring HIPAA compliance and achieving 94% fairness score across demographic groups. Implemented audit logging for regulatory reporting.",
    "original_description": "Built RAFT system for clinical article appraisal using LLMs",
    "technologies": ["LangChain", "Hugging Face", "FAISS", "Compliance Framework"],
    "tag": "modified",
    "reason": "Reframed to highlight governance, compliance, bias mitigation - key JD requirements"
  },
  {
    "name": "Enterprise AI Chatbot with Governance Framework",
    "description": "Developed multi-agent AI system with built-in model risk governance, real-time bias monitoring, and compliance audit trails. Reduced compliance review time by 60% and achieved 99.1% alignment with ethical AI guidelines.",
    "original_description": "Built multi-agent AI chatbot for enterprise query resolution",
    "technologies": ["LangChain", "FastAPI", "Docker", "MLflow"],
    "tag": "modified",
    "reason": "Added governance, risk monitoring, and ethical AI aspects from JD"
  },
  {
    "name": "AI Model Risk Governance Platform",
    "description": "Designed end-to-end model risk governance system handling 200+ ML models, implementing validation workflows, drift detection, and automated compliance reporting aligned with EU AI Act requirements.",
    "technologies": ["Python", "MLflow", "Docker", "Kubernetes"],
    "tag": "new",
    "reason": "Directly addresses JD requirement for model risk governance experience"
  },
  {
    "name": "Bias Detection & Fairness Monitoring Dashboard",
    "description": "Built real-time fairness monitoring system detecting demographic bias across AI models, with automated remediation workflows and executive reporting. Reduced bias incidents by 78%.",
    "technologies": ["Python", "TensorFlow", "React", "PostgreSQL"],
    "tag": "new",
    "reason": "Addresses JD requirements for fairness, explainability, and bias mitigation"
  }
]

"skills": [
  {"content": "Kubernetes", "tag": "new", "reason": "Required in JD"},
  {"content": "Risk Management", "tag": "new", "reason": "Key JD requirement"},
  {"content": "CI/CD", "tag": "new", "reason": "Mentioned in JD requirements"}
]

SCORING WEIGHTS:
- Technical Skills: 35%
- Experience: 25%
- Education: 15%
- Projects: 15%
- Keywords/Soft Skills: 10%

9. COMPREHENSIVE QUALITY ANALYSIS:

   WRITING QUALITY:
   - Check for grammatical errors, spelling mistakes, punctuation issues
   - Identify passive voice and suggest active alternatives
   - Find weak phrases ("responsible for", "helped with", "worked on") and suggest power phrases
   - Analyze overall tone (casual vs professional vs overly formal)
   - Recommend industry-appropriate action verbs

   ATS OPTIMIZATION:
   - Calculate keyword match percentage between CV and JD
   - Identify missing critical keywords for ATS scanning
   - Flag non-standard section headers that ATS might miss
   - Note any formatting that could cause parsing issues

   INDUSTRY VOCABULARY:
   - Identify domain-specific terms already present
   - Suggest missing industry jargon and buzzwords
   - Flag outdated terminology (e.g., "Webmaster" → "Web Developer")

   QUANTIFICATION OPPORTUNITIES:
   - Find vague statements lacking metrics
   - Suggest specific types of numbers to add (%, $, time saved, team size, etc.)

   RED FLAGS:
   - Employment gaps
   - Job hopping patterns
   - Overqualification/underqualification signals
   - Missing contact info or unprofessional email
   - Inconsistent date formats

   LENGTH ANALYSIS:
   - Assess if CV is appropriate length for experience level
   - Identify sections to trim or expand"""

    CHAT_SYSTEM_PROMPT = """You are a helpful CV improvement assistant. Use industry-specific terminology based on the job context."""

    # Scoring weights (must sum to 100)
    SCORE_WEIGHTS = {
        "skills": 35,
        "experience": 25,
        "education": 15,
        "projects": 15,
        "keywords": 10
    }

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def calculate_match_score(
        self,
        parsed_cv: Dict[str, Any],
        job_description: str,
        jd_requirements: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Calculate deterministic match score between CV and JD.

        Scoring Formula (100 points total):
        - Skills: 35 points (matched_skills / required_skills * 35)
        - Experience: 25 points (cv_years / required_years * 25, capped at 25)
        - Education: 15 points (degree match level)
        - Projects: 15 points (0=0, 1=5, 2=10, 3+=15)
        - Keywords: 10 points (keywords_found / total_keywords * 10)

        Returns consistent scores for same inputs.
        """
        import re

        # Extract text from CV for keyword matching
        cv_text = json.dumps(parsed_cv).lower()

        # Extract keywords from JD (simple extraction)
        jd_lower = job_description.lower()

        # Common skill/keyword patterns to look for
        # Extract words that appear after common requirement phrases
        requirement_patterns = [
            r'required?:?\s*([^.]+)',
            r'must have:?\s*([^.]+)',
            r'requirements?:?\s*([^.]+)',
            r'qualifications?:?\s*([^.]+)',
            r'skills?:?\s*([^.]+)',
            r'experience (?:with|in):?\s*([^.]+)',
        ]

        jd_keywords = set()

        # Extract multi-word technical terms and skills from JD
        # Common technical terms, tools, methodologies
        tech_patterns = [
            r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b',  # CamelCase or capitalized words
            r'\b\w+(?:\.js|\.py|\.io)\b',  # Framework names
            r'\b(?:SQL|API|AWS|GCP|Azure|Docker|Kubernetes|React|Angular|Vue|Node|Python|Java|C\+\+|JavaScript|TypeScript|MongoDB|PostgreSQL|Redis|GraphQL|REST|CI/CD|DevOps|Agile|Scrum|HIPAA|GDPR|SOC|PCI|ISO)\b',
        ]

        # Extract potential keywords from JD
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9+#.-]*[a-zA-Z0-9]\b|\b[A-Z]{2,}\b', job_description)
        for word in words:
            if len(word) > 2:
                jd_keywords.add(word.lower())

        # Filter out common non-skill words
        stop_words = {'the', 'and', 'for', 'with', 'our', 'you', 'your', 'will', 'are', 'have', 'has',
                      'been', 'being', 'was', 'were', 'can', 'could', 'should', 'would', 'may', 'might',
                      'must', 'shall', 'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
                      'where', 'when', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
                      'other', 'some', 'such', 'than', 'too', 'very', 'just', 'also', 'only', 'own', 'same',
                      'into', 'over', 'after', 'before', 'between', 'under', 'again', 'further', 'then',
                      'once', 'here', 'there', 'about', 'above', 'below', 'from', 'down', 'out', 'off',
                      'through', 'during', 'including', 'include', 'includes', 'etc', 'ability', 'able',
                      'work', 'working', 'worked', 'team', 'teams', 'role', 'roles', 'job', 'jobs',
                      'position', 'positions', 'company', 'companies', 'organization', 'organizations',
                      'looking', 'seeking', 'ideal', 'candidate', 'candidates', 'opportunity', 'opportunities'}

        jd_keywords = {w for w in jd_keywords if w not in stop_words and len(w) > 2}

        # --- SKILLS SCORE (35 points) ---
        cv_skills = parsed_cv.get("skills", []) or []
        if isinstance(cv_skills, dict):
            # Handle old format with categories
            all_skills = []
            for key, val in cv_skills.items():
                if isinstance(val, list):
                    all_skills.extend(val)
            cv_skills = all_skills

        cv_skills_lower = [s.lower() if isinstance(s, str) else str(s).lower() for s in cv_skills]
        cv_skills_text = ' '.join(cv_skills_lower)

        # Count JD keywords found in skills
        skills_matched = 0
        for kw in jd_keywords:
            if kw in cv_skills_text or kw in cv_text:
                skills_matched += 1

        skills_score = min(35, (skills_matched / max(len(jd_keywords), 1)) * 35) if jd_keywords else 20

        # --- EXPERIENCE SCORE (25 points) ---
        cv_years = parsed_cv.get("total_years_of_experience", 0) or 0

        # Try to extract required years from JD
        years_patterns = [
            r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*experience',
            r'minimum\s*(?:of)?\s*(\d+)\s*(?:years?|yrs?)',
            r'at\s*least\s*(\d+)\s*(?:years?|yrs?)',
            r'(\d+)\s*-\s*\d+\s*(?:years?|yrs?)',
        ]

        required_years = 0
        for pattern in years_patterns:
            match = re.search(pattern, jd_lower)
            if match:
                required_years = int(match.group(1))
                break

        if required_years > 0:
            experience_ratio = min(cv_years / required_years, 1.5)  # Cap at 150%
            experience_score = min(25, experience_ratio * 25)
        else:
            # No specific requirement, give partial credit based on having experience
            experience_score = min(25, cv_years * 2.5) if cv_years > 0 else 10

        # --- EDUCATION SCORE (15 points) ---
        cv_education = parsed_cv.get("education", []) or []
        has_degree = len(cv_education) > 0

        # Check for degree keywords in JD
        degree_keywords = ['bachelor', 'master', 'phd', 'doctorate', 'degree', 'mba', 'bs', 'ms', 'ba', 'ma']
        jd_requires_degree = any(dk in jd_lower for dk in degree_keywords)

        if has_degree:
            education_score = 15
        elif not jd_requires_degree:
            education_score = 12  # No requirement, no degree is okay
        else:
            education_score = 5  # Required but missing

        # --- PROJECTS SCORE (15 points) ---
        cv_projects = parsed_cv.get("projects", []) or []
        project_count = len(cv_projects) if isinstance(cv_projects, list) else 0

        if project_count >= 3:
            projects_score = 15
        elif project_count == 2:
            projects_score = 10
        elif project_count == 1:
            projects_score = 5
        else:
            projects_score = 0

        # --- KEYWORDS/ATS SCORE (10 points) ---
        keywords_found = 0
        for kw in jd_keywords:
            if kw in cv_text:
                keywords_found += 1

        keywords_score = min(10, (keywords_found / max(len(jd_keywords), 1)) * 10) if jd_keywords else 5

        # --- TOTAL SCORE ---
        total_score = round(skills_score + experience_score + education_score + projects_score + keywords_score)

        # Determine rating
        if total_score >= 80:
            rating = "Excellent"
        elif total_score >= 65:
            rating = "Good"
        elif total_score >= 50:
            rating = "Fair"
        else:
            rating = "Poor"

        return {
            "current_match_score": total_score,
            "rating": rating,
            "breakdown": {
                "skills_score": round(skills_score, 1),
                "experience_score": round(experience_score, 1),
                "education_score": round(education_score, 1),
                "projects_score": round(projects_score, 1),
                "keywords_score": round(keywords_score, 1)
            },
            "details": {
                "jd_keywords_count": len(jd_keywords),
                "keywords_matched": keywords_found,
                "cv_years": cv_years,
                "required_years": required_years,
                "project_count": project_count,
                "skills_count": len(cv_skills)
            }
        }

    def get_improvement_suggestions(
        self,
        parsed_cv: Dict[str, Any],
        job_description: str
    ) -> Dict[str, Any]:
        """
        Generate actionable suggestions based on score gaps.
        Returns prioritized list of what user should improve next.
        """
        scores = self.calculate_match_score(parsed_cv, job_description)
        breakdown = scores["breakdown"]
        details = scores["details"]

        suggestions = []
        priority = 1

        # Check projects (15 points max, high impact)
        if breakdown["projects_score"] < 15:
            project_count = details["project_count"]
            needed = 3 - project_count
            if needed > 0:
                suggestions.append({
                    "priority": priority,
                    "section": "projects",
                    "current_score": breakdown["projects_score"],
                    "max_score": 15,
                    "potential_gain": 15 - breakdown["projects_score"],
                    "action": f"Add {needed} more project(s) to reach 3 total",
                    "hint": "Ask me to 'add a project about [technology from JD]' or 'suggest projects for this role'",
                    "impact": "high"
                })
                priority += 1

        # Check skills (35 points max, highest weight)
        if breakdown["skills_score"] < 28:  # Less than 80% of max
            missing_keywords = details["jd_keywords_count"] - details["keywords_matched"]
            suggestions.append({
                "priority": priority,
                "section": "skills",
                "current_score": breakdown["skills_score"],
                "max_score": 35,
                "potential_gain": min(10, 35 - breakdown["skills_score"]),
                "action": f"Add more JD-relevant skills ({details['keywords_matched']}/{details['jd_keywords_count']} keywords matched)",
                "hint": "Ask me to 'add missing skills from the JD' or 'what skills am I missing?'",
                "impact": "high"
            })
            priority += 1

        # Check keywords (10 points max)
        if breakdown["keywords_score"] < 7:  # Less than 70% of max
            suggestions.append({
                "priority": priority,
                "section": "work_experience",
                "current_score": breakdown["keywords_score"],
                "max_score": 10,
                "potential_gain": 10 - breakdown["keywords_score"],
                "action": "Inject more JD keywords into work experience descriptions",
                "hint": "Ask me to 'optimize my work experience for ATS' or 'add keywords to my job descriptions'",
                "impact": "medium"
            })
            priority += 1

        # Check experience (25 points max)
        if breakdown["experience_score"] < 20:
            if details["cv_years"] < details["required_years"]:
                suggestions.append({
                    "priority": priority,
                    "section": "work_experience",
                    "current_score": breakdown["experience_score"],
                    "max_score": 25,
                    "potential_gain": 5,
                    "action": f"Experience gap: you have {details['cv_years']} years, JD wants {details['required_years']}+",
                    "hint": "Ask me to 'emphasize transferable skills' or 'highlight relevant experience'",
                    "impact": "medium"
                })
                priority += 1

        # Check education (15 points max)
        if breakdown["education_score"] < 15:
            suggestions.append({
                "priority": priority,
                "section": "education",
                "current_score": breakdown["education_score"],
                "max_score": 15,
                "potential_gain": 15 - breakdown["education_score"],
                "action": "Add relevant education or certifications",
                "hint": "Ask me to 'suggest certifications for this role'",
                "impact": "low"
            })
            priority += 1

        # Calculate total potential
        total_potential = sum(s["potential_gain"] for s in suggestions)

        return {
            "current_score": scores["current_match_score"],
            "potential_score": min(95, scores["current_match_score"] + total_potential),
            "rating": scores["rating"],
            "suggestions": suggestions[:5],  # Top 5 suggestions
            "summary": self._generate_suggestion_summary(suggestions) if suggestions else "Your CV is well-optimized for this role!"
        }

    def _generate_suggestion_summary(self, suggestions: list) -> str:
        """Generate a human-readable summary of top suggestions."""
        if not suggestions:
            return "No major improvements needed."

        top = suggestions[0]
        if top["section"] == "projects":
            return f"Focus on adding projects to gain up to {top['potential_gain']} points."
        elif top["section"] == "skills":
            return f"Add more JD-relevant skills to gain up to {top['potential_gain']} points."
        elif top["section"] == "work_experience":
            return f"Enhance work experience with JD keywords to improve your score."
        else:
            return f"Focus on {top['section']} to improve your match score."

    def _count_projects(self, result: Dict[str, Any], parsed_cv: Dict[str, Any]) -> int:
        """Count total projects in the analysis response."""
        cv_has_projects = parsed_cv.get("projects") not in [None, []]

        if cv_has_projects:
            # Count modified projects in cv_sections + new projects in non_cv_sections
            modified = len(result.get("cv_sections", {}).get("projects", []))
            new = len(result.get("non_cv_sections", {}).get("projects", []))
            return modified + new
        else:
            # Count project-like entries in work experience (new descriptions)
            count = 0
            for job in result.get("cv_sections", {}).get("work_experience", []):
                for desc in job.get("descriptions", []):
                    if desc.get("tag") == "new":
                        count += 1
            return count

    def _generate_missing_projects(
        self,
        parsed_cv: Dict[str, Any],
        job_title: str,
        job_description: str,
        needed: int,
        cv_has_projects: bool
    ) -> list:
        """Generate exactly the missing number of projects via a focused API call."""
        prompt = f"""Generate EXACTLY {needed} highly relevant project(s) for this job application.

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

REQUIREMENTS:
1. Each project must target a SPECIFIC JD requirement
2. Include realistic metrics and outcomes
3. Naturally inject 3-5 JD keywords into each description
4. Make projects impressive and recruiter-attractive

{"Return as projects with name, description, technologies, reason, tag='new'" if cv_has_projects else "Return as work experience bullet points with content, tag='new', reason"}

Return ONLY a JSON array of {needed} project(s)."""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a CV optimization expert. Generate realistic, impressive projects."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            # Handle both array and object with 'projects' key
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and "projects" in data:
                return data["projects"]
            elif isinstance(data, dict) and "descriptions" in data:
                return data["descriptions"]
            else:
                return list(data.values())[0] if data else []
        except:
            return []

    def _inject_projects_to_work_exp(self, result: Dict[str, Any], projects: list) -> None:
        """Inject projects as new descriptions into work experience."""
        work_exp = result.get("cv_sections", {}).get("work_experience", [])

        if not work_exp:
            # Create work experience entry if none exists
            if "cv_sections" not in result:
                result["cv_sections"] = {}
            if "work_experience" not in result["cv_sections"]:
                result["cv_sections"]["work_experience"] = []
            work_exp = result["cv_sections"]["work_experience"]

        for project in projects:
            # Convert project to work experience description format
            desc = {
                "content": f"{project.get('name', 'Project')}: {project.get('description', '')}",
                "tag": "new",
                "reason": project.get("reason", "Generated to meet JD requirements")
            }

            # Add to first job or create a new entry
            if work_exp:
                if "descriptions" not in work_exp[0]:
                    work_exp[0]["descriptions"] = []
                work_exp[0]["descriptions"].append(desc)
            else:
                work_exp.append({
                    "job_title": "Relevant Experience",
                    "company": "Various Projects",
                    "descriptions": [desc]
                })

    def _apply_project_guardrail(
        self,
        result: Dict[str, Any],
        parsed_cv: Dict[str, Any],
        job_title: str,
        job_description: str
    ) -> Dict[str, Any]:
        """Ensure minimum 3 projects exist in the response."""
        project_count = self._count_projects(result, parsed_cv)
        cv_has_projects = parsed_cv.get("projects") not in [None, []]

        if project_count < 3:
            missing = 3 - project_count
            additional_projects = self._generate_missing_projects(
                parsed_cv, job_title, job_description, missing, cv_has_projects
            )

            if additional_projects:
                if cv_has_projects:
                    # Add to non_cv_sections.projects
                    if "non_cv_sections" not in result:
                        result["non_cv_sections"] = {}
                    if "projects" not in result["non_cv_sections"]:
                        result["non_cv_sections"]["projects"] = []
                    result["non_cv_sections"]["projects"].extend(additional_projects)
                else:
                    # Inject into work experience
                    self._inject_projects_to_work_exp(result, additional_projects)

        return result

    def _add_field_paths(self, result: Dict[str, Any], parsed_cv: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add field_path to each recommendation so frontend knows where to apply changes.

        Examples:
        - title -> "title"
        - work_experience[0].description[2] -> for specific bullet
        - skills[5] -> for new skill at index 5
        """
        cv_sections = result.get("cv_sections", {})
        non_cv_sections = result.get("non_cv_sections", {})

        # Title
        if "title" in cv_sections and cv_sections["title"]:
            cv_sections["title"]["field_path"] = "title"

        # Professional summary
        if "professional_summary" in cv_sections and cv_sections["professional_summary"]:
            cv_sections["professional_summary"]["field_path"] = "professional_summary"

        # Work experience
        if "work_experience" in cv_sections:
            for job_idx, job in enumerate(cv_sections.get("work_experience", [])):
                job["job_index"] = job_idx
                if "descriptions" in job:
                    # Get existing description count for this job in CV
                    cv_work_exp = parsed_cv.get("work_experience", [])
                    existing_desc_count = 0
                    if job_idx < len(cv_work_exp):
                        existing_descs = cv_work_exp[job_idx].get("description", [])
                        if isinstance(existing_descs, list):
                            existing_desc_count = len(existing_descs)

                    new_desc_idx = existing_desc_count
                    for desc_idx, desc in enumerate(job["descriptions"]):
                        if desc.get("tag") == "modified" and desc.get("original_content"):
                            # Find the index of the original in CV
                            if job_idx < len(cv_work_exp):
                                cv_descs = cv_work_exp[job_idx].get("description", [])
                                if isinstance(cv_descs, list):
                                    for i, cv_desc in enumerate(cv_descs):
                                        if cv_desc == desc.get("original_content"):
                                            desc["field_path"] = f"work_experience[{job_idx}].description[{i}]"
                                            break
                                    else:
                                        # Not found, use desc_idx as fallback
                                        desc["field_path"] = f"work_experience[{job_idx}].description[{desc_idx}]"
                        elif desc.get("tag") == "new":
                            # New description, append at end
                            desc["field_path"] = f"work_experience[{job_idx}].description[{new_desc_idx}]"
                            new_desc_idx += 1

        # Skills (new skills to add)
        if "skills" in cv_sections:
            cv_skills = parsed_cv.get("skills", [])
            existing_count = len(cv_skills) if isinstance(cv_skills, list) else 0
            for idx, skill in enumerate(cv_sections.get("skills", [])):
                skill["field_path"] = f"skills[{existing_count + idx}]"

        # Projects in cv_sections (modified existing)
        if "projects" in cv_sections:
            for idx, project in enumerate(cv_sections.get("projects", [])):
                # Try to find original project index
                cv_projects = parsed_cv.get("projects", [])
                if cv_projects and project.get("original_name"):
                    for i, cv_proj in enumerate(cv_projects):
                        if cv_proj.get("name") == project.get("original_name"):
                            project["field_path"] = f"projects[{i}]"
                            break
                    else:
                        project["field_path"] = f"projects[{idx}]"
                else:
                    project["field_path"] = f"projects[{idx}]"

        # Certifications in cv_sections
        if "certifications" in cv_sections:
            cv_certs = parsed_cv.get("certifications", [])
            existing_count = len(cv_certs) if isinstance(cv_certs, list) else 0
            for idx, cert in enumerate(cv_sections.get("certifications", [])):
                cert["field_path"] = f"certifications[{existing_count + idx}]"

        # Non-CV sections (all new content)

        # Projects in non_cv_sections
        if "projects" in non_cv_sections:
            cv_projects = parsed_cv.get("projects", [])
            existing_count = len(cv_projects) if isinstance(cv_projects, list) else 0
            # Also count projects in cv_sections
            cv_section_projects = len(cv_sections.get("projects", []))
            start_idx = existing_count + cv_section_projects
            for idx, project in enumerate(non_cv_sections.get("projects", [])):
                project["field_path"] = f"projects[{start_idx + idx}]"

        # Certifications in non_cv_sections
        if "certifications" in non_cv_sections:
            cv_certs = parsed_cv.get("certifications", [])
            existing_count = len(cv_certs) if isinstance(cv_certs, list) else 0
            for idx, cert in enumerate(non_cv_sections.get("certifications", [])):
                cert["field_path"] = f"certifications[{existing_count + idx}]"

        # Skills in non_cv_sections (when CV has no skills)
        if "skills" in non_cv_sections:
            for idx, skill in enumerate(non_cv_sections.get("skills", [])):
                if isinstance(skill, dict):
                    skill["field_path"] = f"skills[{idx}]"
                # If skills are just strings, wrap them
                elif isinstance(skill, str):
                    non_cv_sections["skills"][idx] = {
                        "content": skill,
                        "field_path": f"skills[{idx}]",
                        "tag": "new"
                    }

        # Languages in non_cv_sections
        if "languages" in non_cv_sections:
            for idx, lang in enumerate(non_cv_sections.get("languages", [])):
                lang["field_path"] = f"languages[{idx}]"

        # Awards in non_cv_sections
        if "awards" in non_cv_sections:
            for idx, award in enumerate(non_cv_sections.get("awards", [])):
                award["field_path"] = f"awards_scholarships[{idx}]"

        # Publications in non_cv_sections
        if "publications" in non_cv_sections:
            for idx, pub in enumerate(non_cv_sections.get("publications", [])):
                pub["field_path"] = f"publications[{idx}]"

        # Education in non_cv_sections
        if "education" in non_cv_sections:
            cv_edu = parsed_cv.get("education", [])
            existing_count = len(cv_edu) if isinstance(cv_edu, list) else 0
            for idx, edu in enumerate(non_cv_sections.get("education", [])):
                edu["field_path"] = f"education[{existing_count + idx}]"

        # Professional summary in non_cv_sections
        if "professional_summary" in non_cv_sections and non_cv_sections["professional_summary"]:
            non_cv_sections["professional_summary"]["field_path"] = "professional_summary"

        return result

    def analyze(
        self,
        parsed_cv: Dict[str, Any],
        job_title: str,
        job_description: str,
        options: Dict[str, bool],
        instructions: str = None
    ) -> Dict[str, Any]:
        cv_text = json.dumps(parsed_cv, indent=2)

        # Build user instructions section if provided
        user_instructions_section = ""
        if instructions and instructions.strip():
            user_instructions_section = f"""
*******************************************************************
PRIORITY OVERRIDE - USER'S CUSTOM INSTRUCTIONS
These instructions from the user take precedence over ALL default
rules below. If user instructions conflict with any default behavior,
ALWAYS follow user instructions instead.
*******************************************************************
{instructions}
*******************************************************************

"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"""Analyze this CV against the Job Description.
{user_instructions_section}
CRITICAL: RETURN ONLY CHANGES, NOT ORIGINAL CONTENT

OUTPUT RULES:
1. MODIFIED content: Include "content" (new version) + "original_content" (what was changed) + "reason"
2. NEW content: Include "content" + "reason" (no original_content needed)
3. SKIP untouched content: If something doesn't need modification, don't include it at all

*** MANDATORY: MINIMUM 3 PROJECTS REQUIRED (unless user instructions say otherwise) ***
- If CV has projects section: Modify 1-2 existing + add 1-2 new = at least 3 total
- If CV has NO projects section: Inject 3+ project-style achievements into work_experience descriptions
- Each project MUST have JD keywords naturally woven into title and description

WHAT TO RETURN:
- Modified title (if needed) with original_content
- Modified professional_summary (if needed) with original_content
- Modified work experience descriptions with original_content + NEW responsibilities
- MINIMUM 3 projects total (modified + new) with JD keywords naturally injected
- NEW skills only (JD keywords to add)

CRITICAL - cv_sections vs non_cv_sections:
- If CV section has DATA → put modifications in cv_sections
- If CV section is NULL/EMPTY → put new content in non_cv_sections
  Examples: certifications:null → non_cv_sections.certifications
            soft_skills:null → non_cv_sections.skills.soft_skills
            awards_scholarships:null → non_cv_sections.awards
            projects:null → inject into work_experience as enhanced descriptions

WHAT NOT TO RETURN:
- Original content that needs no change
- Untouched skills
- Unmodified project descriptions

JOB TITLE: {job_title}

JOB DESCRIPTION:
{job_description}

PARSED CV DATA:
{cv_text}

Return ONLY modifications and new additions. Skip untouched original content. ENSURE AT LEAST 3 PROJECTS (unless user instructed otherwise)."""
                }
            ],
            tools=self.ANALYSIS_FUNCTION,
            tool_choice={"type": "function", "function": {"name": "analyze_cv_against_jd"}}
        )

        if response.choices[0].message.tool_calls:
            function_args = response.choices[0].message.tool_calls[0].function.arguments
            try:
                result = json.loads(function_args)
            except json.JSONDecodeError as e:
                # Try to fix common JSON issues
                import re
                # Remove trailing commas before closing brackets
                fixed = re.sub(r',(\s*[}\]])', r'\1', function_args)
                try:
                    result = json.loads(fixed)
                except:
                    raise ValueError(f"Invalid JSON from AI: {str(e)}")

            # Apply guardrail to ensure minimum 3 projects
            result = self._apply_project_guardrail(result, parsed_cv, job_title, job_description)

            # Add field_path to each recommendation for frontend
            result = self._add_field_paths(result, parsed_cv)

            # Override LLM scores with deterministic calculation for consistency
            deterministic_scores = self.calculate_match_score(parsed_cv, job_description)
            result["scores"] = {
                "current_match_score": deterministic_scores["current_match_score"],
                "potential_score_after_changes": min(95, deterministic_scores["current_match_score"] + 20),  # Estimate potential improvement
                "rating": deterministic_scores["rating"],
                "breakdown": deterministic_scores["breakdown"]
            }

            return result

        raise ValueError("Failed to generate analysis")

    def chat(self, message: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        job_title = session_context.get("job_title", "Unknown")
        chat_history = session_context.get("chat_history", [])
        history_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history[-10:]]

        messages = [
            {"role": "system", "content": f"{self.CHAT_SYSTEM_PROMPT}\n\nContext: Job Title: {job_title}"},
            *history_messages,
            {"role": "user", "content": message}
        ]

        response = self.client.chat.completions.create(model=self.model, messages=messages)

        return {
            "message": response.choices[0].message.content,
            "session_id": session_context.get("session_id"),
        }

    SECTION_CHAT_FUNCTION = [{
        "type": "function",
        "function": {
            "name": "respond_with_action",
            "description": "Respond to user message with optional actionable changes",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Your response message to the user"
                    },
                    "has_action": {
                        "type": "boolean",
                        "description": "Whether this response includes an actionable change (true) or is just conversation/brainstorming (false)"
                    },
                    "action": {
                        "type": "object",
                        "description": "The action to perform. Only include if has_action is true.",
                        "properties": {
                            "action_type": {
                                "type": "string",
                                "enum": ["improve", "add", "remove", "replace", "rewrite"],
                                "description": "Type of action"
                            },
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of what this action does"
                            },
                            "changes": {
                                "type": "array",
                                "description": "List of specific changes to apply",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "field": {
                                            "type": "string",
                                            "description": "Field path e.g., 'professional_summary', 'work_experience[0].description[2]', 'skills[5]'"
                                        },
                                        "change_type": {
                                            "type": "string",
                                            "enum": ["replace", "add", "remove", "modify"]
                                        },
                                        "original_value": {
                                            "type": "string",
                                            "description": "Original value (for replace/modify)"
                                        },
                                        "new_value": {
                                            "type": "string",
                                            "description": "New value to set"
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "required": ["message", "has_action"]
            }
        }
    }]

    def chat_with_section(self, message: str, section: str, session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chat with section context. Returns message and optional action.

        Args:
            message: User's message
            section: Section being discussed (entire_resume, professional_summary, work_experience, etc.)
            session_context: Session data including CV, JD, and chat history

        Returns:
            {
                "message": "AI response",
                "section": "section_name",
                "action": {  # Only if actionable
                    "action_id": "uuid",
                    "action_type": "improve|add|remove|replace|rewrite",
                    "section": "section_name",
                    "status": "pending",
                    "description": "What this action does",
                    "changes": [...],
                    "requires_confirmation": true
                }
            }
        """
        import uuid

        job_title = session_context.get("job_title", "Unknown")
        job_description = session_context.get("job_description", "")
        # Use current_cv (with approved changes) if available, otherwise fall back to parsed_cv
        parsed_cv = session_context.get("current_cv") or session_context.get("parsed_cv", {})
        chat_history = session_context.get("chat_history", [])
        applied_changes = session_context.get("applied_changes", [])
        confirmed_actions = session_context.get("confirmed_actions", {})

        # Get section-specific content
        section_content = self._get_section_content(parsed_cv, section)

        # Build history messages
        history_messages = [{"role": msg["role"], "content": msg["content"]} for msg in chat_history[-10:]]

        # Build changes summary
        changes_summary = ""
        if confirmed_actions:
            changes_summary = "\n\nPREVIOUSLY APPROVED CHANGES:\n"
            for action_id, action in list(confirmed_actions.items())[-5:]:  # Last 5 changes
                changes_summary += f"- {action.get('description', 'Change applied')} (section: {action.get('section', 'unknown')})\n"

        system_prompt = f"""{self.CHAT_SYSTEM_PROMPT}

CONTEXT:
- Job Title: {job_title}
- Current Section: {section}
- Section Content: {json.dumps(section_content, indent=2) if section_content else "Empty/Not available"}
{changes_summary}
JOB DESCRIPTION:
{job_description[:1500] if job_description else "Not provided"}

RULES:
1. If user is asking a question or brainstorming → has_action = false, just respond conversationally
2. If user wants you to improve/change/add/remove something → has_action = true, include the action with specific changes
3. For actions, provide EXACT field paths and values that can be applied to the CV
4. Always explain what you're suggesting before providing the action
5. Be specific with changes - include original_value when modifying existing content

SECTION FIELD PATHS:
- professional_summary → "professional_summary"
- work_experience items → "work_experience[index].field" (e.g., "work_experience[0].description[0]")
- education items → "education[index].field"
- skills → "skills[index]" or just "skills" for entire array
- projects → "projects[index].field"
- certifications → "certifications[index].field"
"""

        messages = [
            {"role": "system", "content": system_prompt},
            *history_messages,
            {"role": "user", "content": f"[Section: {section}] {message}"}
        ]

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.SECTION_CHAT_FUNCTION,
            tool_choice={"type": "function", "function": {"name": "respond_with_action"}}
        )

        # Parse response
        if response.choices[0].message.tool_calls:
            function_args = response.choices[0].message.tool_calls[0].function.arguments
            try:
                result = json.loads(function_args)
            except json.JSONDecodeError:
                result = {"message": response.choices[0].message.content or "I can help with that.", "has_action": False}
        else:
            result = {"message": response.choices[0].message.content or "I can help with that.", "has_action": False}

        # Build response
        response_data = {
            "message": result.get("message", ""),
            "section": section,
            "session_id": session_context.get("session_id"),
        }

        # Add action if present
        if result.get("has_action") and result.get("action"):
            action_data = result["action"]
            response_data["action"] = {
                "action_id": f"action_{uuid.uuid4().hex[:12]}",
                "action_type": action_data.get("action_type", "improve"),
                "section": section,
                "status": "pending",
                "description": action_data.get("description", "Apply suggested changes"),
                "changes": action_data.get("changes", []),
                "requires_confirmation": True
            }

        return response_data

    def _get_section_content(self, parsed_cv: Dict[str, Any], section: str) -> Any:
        """Extract content for a specific section from the parsed CV."""
        section_map = {
            "entire_resume": parsed_cv,
            "professional_summary": parsed_cv.get("professional_summary"),
            "work_experience": parsed_cv.get("work_experience"),
            "education": parsed_cv.get("education"),
            "skills": parsed_cv.get("skills"),
            "projects": parsed_cv.get("projects"),
            "certifications": parsed_cv.get("certifications"),
            "contact_info": parsed_cv.get("contact_info"),
            "title": parsed_cv.get("title"),
            "languages": parsed_cv.get("languages"),
            "awards_scholarships": parsed_cv.get("awards_scholarships"),
            "publications": parsed_cv.get("publications")
        }
        return section_map.get(section, parsed_cv)
