"""Skill Manager — loads and formats career agent guidelines from the skills directory."""

import os
from pathlib import Path
from typing import List, Dict
import structlog

logger = structlog.get_logger()

# Path to the root skills directory relative to this file
# d:\Projects\FTE HR\backend\app\core\skills.py -> d:\Projects\FTE HR\skills
SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"

def get_skill_content(skill_id: str) -> str:
    """Load the content of a specific skill or guideline file."""
    # Mapping of shorthand IDs to relative paths
    skill_map = {
        "email-writing": "01-email-writing/skill.md",
        "cover-letter-writing": "02-cover-letter-writting/skill.md",
        "cv-resume-writing": "03-cv-resume-writing/skill.md",
        "regional-adaptation": "04-regional-adaptation/skill.md",
        "ats-optimization": "05-ats-optimization/skill.md",
        "tone-guidelines": "_shared/tone-guidelines.md",
        "power-verbs": "_shared/power-verbs.md",
    }
    
    rel_path = skill_map.get(skill_id)
    if not rel_path:
        logger.warning("skill_not_found", skill_id=skill_id)
        return ""
    
    full_path = SKILLS_DIR / rel_path
    try:
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        else:
            logger.warning("skill_file_missing", path=str(full_path))
            return ""
    except Exception as e:
        logger.error("skill_load_error", skill_id=skill_id, error=str(e))
        return ""

def get_combined_skills(skill_ids: List[str]) -> str:
    """Combine multiple skills into a single instruction block for LLM prompts."""
    blocks = []
    for sid in skill_ids:
        content = get_skill_content(sid)
        if content:
            blocks.append(f"--- SKILL: {sid.upper()} ---\n{content}")
    
    return "\n\n".join(blocks)
