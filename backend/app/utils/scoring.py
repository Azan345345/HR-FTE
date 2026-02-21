"""
Digital FTE - Scoring Utilities
Match score calculation between CV skills and job requirements.
"""

from typing import List, Set, Tuple


def normalize_skill(skill: str) -> str:
    """Normalize a skill name for comparison."""
    return skill.lower().strip().replace("-", "").replace(".", "").replace(" ", "")


def extract_skills_from_cv(parsed_cv: dict) -> Set[str]:
    """Extract all skills from a parsed CV as a normalized set."""
    skills = set()
    cv_skills = parsed_cv.get("skills", {})
    if cv_skills:
        for category in ["technical", "soft", "tools"]:
            for s in cv_skills.get(category, []):
                skills.add(normalize_skill(s))

    # Also extract technologies from experience
    for exp in parsed_cv.get("experience", []):
        for tech in exp.get("technologies", []):
            skills.add(normalize_skill(tech))

    # And from projects
    for proj in parsed_cv.get("projects", []):
        for tech in proj.get("technologies", []):
            skills.add(normalize_skill(tech))

    return skills


def extract_keywords_from_job(job: dict) -> Set[str]:
    """Extract keywords from job description and requirements."""
    keywords = set()

    # From requirements
    for req in job.get("requirements", []):
        for word in req.replace(",", " ").replace(";", " ").split():
            cleaned = normalize_skill(word)
            if len(cleaned) > 2:
                keywords.add(cleaned)

    # From description (basic keyword extraction)
    desc = job.get("description", "")
    # Common technical terms to look for
    tech_indicators = [
        "python", "javascript", "typescript", "react", "node", "aws", "azure",
        "docker", "kubernetes", "sql", "nosql", "mongodb", "postgresql",
        "java", "csharp", "golang", "rust", "swift", "kotlin",
        "machine learning", "deep learning", "ai", "nlp", "llm",
        "fastapi", "django", "flask", "nextjs", "vue", "angular",
        "git", "cicd", "devops", "agile", "scrum", "rest", "graphql",
        "redis", "kafka", "rabbitmq", "elasticsearch",
        "tensorflow", "pytorch", "pandas", "numpy",
    ]
    desc_lower = desc.lower()
    for term in tech_indicators:
        if term in desc_lower:
            keywords.add(normalize_skill(term))

    return keywords


def calculate_match_score(
    cv_skills: Set[str],
    job_keywords: Set[str],
) -> Tuple[float, List[str], List[str]]:
    """
    Calculate match score between CV skills and job requirements.
    Returns (score, matching_skills, missing_skills).
    Score is 0-100.
    """
    if not job_keywords:
        return 50.0, [], []  # No requirements to match against

    matching = cv_skills & job_keywords
    missing = job_keywords - cv_skills

    # Score = weighted by matches
    if len(job_keywords) > 0:
        raw_score = (len(matching) / len(job_keywords)) * 100
    else:
        raw_score = 50.0

    # Clamp and round
    score = round(min(max(raw_score, 0), 100), 1)

    # Denormalize for display
    matching_display = sorted(list(matching))
    missing_display = sorted(list(missing))

    return score, matching_display, missing_display


def score_jobs_against_cv(
    jobs: List[dict],
    parsed_cv: dict,
) -> List[dict]:
    """
    Score and rank a list of jobs against a parsed CV.
    Adds match_score, matching_skills, missing_skills to each job.
    Returns jobs sorted by match_score descending.
    """
    cv_skills = extract_skills_from_cv(parsed_cv)

    scored_jobs = []
    for job in jobs:
        job_keywords = extract_keywords_from_job(job)
        score, matching, missing = calculate_match_score(cv_skills, job_keywords)

        job_with_score = {**job}
        job_with_score["match_score"] = score
        job_with_score["matching_skills"] = matching
        job_with_score["missing_skills"] = missing
        scored_jobs.append(job_with_score)

    # Sort by match score descending
    scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)
    return scored_jobs
