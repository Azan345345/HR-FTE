from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.api.deps import get_current_user
from app.db.models import User, UserCV, Job, JobSearch
from app.db.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.config import settings as app_settings
from app.schemas.schemas import SkillListResponse, SkillResponse
import os
import yaml
from pathlib import Path

router = APIRouter(prefix="/settings", tags=["Settings"])

# In-memory preferred model per user (resets on backend restart)
_preferred_models: dict[str, str] = {}

AVAILABLE_MODELS = [
    {"id": "auto",                    "label": "Auto",               "provider": "auto",   "tier": "auto"},
    {"id": "gpt-4o",                  "label": "GPT-4o",             "provider": "openai", "tier": "smart"},
    {"id": "gpt-4o-mini",             "label": "GPT-4o Mini",        "provider": "openai", "tier": "fast"},
    {"id": "o3-mini",                 "label": "o3 Mini",            "provider": "openai", "tier": "reasoning"},
    {"id": "gemini-2.5-flash",        "label": "Gemini 2.5 Flash",   "provider": "google", "tier": "smart"},
    {"id": "llama-3.3-70b-versatile", "label": "Llama 3.3 70B",      "provider": "groq",   "tier": "fast"},
    {"id": "mixtral-8x7b-32768",      "label": "Mixtral 8x7B",       "provider": "groq",   "tier": "balanced"},
    {"id": "llama-3.1-8b-instant",    "label": "Llama 3.1 8B",       "provider": "groq",   "tier": "lite"},
]

# "auto" resolves to gpt-4o (primary) with full fallback chain
_AUTO_MODEL = "gpt-4o"


def get_user_preferred_model(user_id: str) -> str:
    """Returns the resolved model ID (never 'auto')."""
    model = _preferred_models.get(user_id, "auto")
    return _AUTO_MODEL if model == "auto" else model


def get_user_display_model(user_id: str) -> str:
    """Returns what the user selected, including 'auto'."""
    return _preferred_models.get(user_id, "auto")


class SetModelRequest(BaseModel):
    model: str


@router.get("/model")
async def get_model(current_user: User = Depends(get_current_user)):
    """Get the user's preferred LLM model (display value, may be 'auto')."""
    return {
        "preferred_model": get_user_display_model(current_user.id),
        "available_models": AVAILABLE_MODELS,
    }


@router.post("/model")
async def set_model(body: SetModelRequest, current_user: User = Depends(get_current_user)):
    """Set the user's preferred LLM model."""
    valid_ids = {m["id"] for m in AVAILABLE_MODELS}
    if body.model not in valid_ids:
        raise HTTPException(status_code=400, detail=f"Unknown model: {body.model}")
    _preferred_models[current_user.id] = body.model
    return {"preferred_model": body.model}

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    linkedin_url: Optional[str] = None


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the user's profile including LinkedIn URL."""
    prefs = current_user.preferences or {}
    return {
        "name": current_user.name,
        "email": current_user.email,
        "linkedin_url": prefs.get("linkedin_url", ""),
    }


@router.patch("/profile")
async def update_profile(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile fields (name, LinkedIn URL)."""
    if body.name is not None:
        current_user.name = body.name.strip() or current_user.name
    prefs = dict(current_user.preferences or {})
    if body.linkedin_url is not None:
        prefs["linkedin_url"] = body.linkedin_url.strip()
    current_user.preferences = prefs
    await db.commit()
    return {
        "name": current_user.name,
        "email": current_user.email,
        "linkedin_url": prefs.get("linkedin_url", ""),
    }


@router.get("/config")
async def get_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get read-only configuration and data source status."""
    
    # Mask keys
    def mask(key: str):
        if not key or len(key) < 8: return "Missing"
        return f"{key[:8]}...{key[-4:]}"

    try:
        # Get counts
        cv_count = await db.scalar(select(func.count(UserCV.id)).where(UserCV.user_id == current_user.id))
        
        job_count_query = select(func.count(Job.id)).select_from(Job).join(JobSearch).where(JobSearch.user_id == current_user.id)
        job_count = await db.scalar(job_count_query)
        
        return {
            "api_keys": [
                {"label": "OpenAI API", "key": "openai", "val": mask(app_settings.OPENAI_API_KEY), "active": bool(app_settings.OPENAI_API_KEY)},
                {"label": "Google AI (Gemini)", "key": "google", "val": mask(app_settings.GOOGLE_AI_API_KEY), "active": bool(app_settings.GOOGLE_AI_API_KEY)},
                {"label": "Groq API", "key": "groq", "val": mask(app_settings.GROQ_API_KEY), "active": bool(app_settings.GROQ_API_KEY)},
                {"label": "SerpAPI (Google Jobs)", "key": "serpapi", "val": mask(app_settings.SERPAPI_API_KEY), "active": bool(app_settings.SERPAPI_API_KEY)},
                {"label": "RapidAPI (JSearch)", "key": "rapidapi", "val": mask(app_settings.RAPIDAPI_KEY), "active": bool(app_settings.RAPIDAPI_KEY)},
            ],
            "data_sources": [
                {"name": "Uploaded CVs", "count": cv_count, "status": "Connected" if cv_count > 0 else "Optional"},
                {"name": "Job Database", "count": job_count, "status": "Active"},
                {"name": "Gmail (OAuth2)", "status": "Connected" if (current_user.google_refresh_token or app_settings.GOOGLE_REFRESH_TOKEN) else "Disconnected"},
            ],
            "budget": {
                "spent": 12.40, # Mocked for now
                "limit": 50.00,
                "currency": "USD"
            }
        }
    except Exception as e:
        import logging
        logging.error(f"Error in get_config: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch configuration")

@router.get("/skills", response_model=SkillListResponse)
async def get_skills(
    current_user: User = Depends(get_current_user)
):
    """Get the AI agent's skills and persona configuration."""
    # Correct path: settings.py is in backend/app/api/routes/
    # 5 parents gets us to the root d:\Projects\FTE HR\
    config_path = Path(__file__).parent.parent.parent.parent.parent / "skills" / "agent-config.yaml"
    
    if not config_path.exists():
        import logging
        logging.error(f"Agent config NOT FOUND at: {config_path}")
        raise HTTPException(status_code=404, detail="Agent configuration not found")
        
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        agent_data = data.get("agent", {})
        skills = []
        for s in agent_data.get("skills", []):
            skills.append(SkillResponse(
                id=s["id"],
                name=s["id"].replace("-", " ").title(),
                description=f"Specialized logic for {s['id'].replace('-', ' ')} generation and optimization.",
                priority=s.get("priority", 1),
                path=s["path"]
            ))
            
        persona = agent_data.get("persona", {})
        return SkillListResponse(
            skills=skills,
            persona=persona,
            # Principles are nested under persona in the YAML
            principles=persona.get("principles", [])
        )
    except Exception as e:
        import logging
        logging.error(f"Error loading skills: {e}")
        raise HTTPException(status_code=500, detail="Failed to load skills")
