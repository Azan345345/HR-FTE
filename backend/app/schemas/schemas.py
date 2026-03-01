"""Pydantic schemas for request / response models."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    preferences: dict = {}
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── CV ────────────────────────────────────────
class CVResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    parsed_data: Optional[dict] = None
    is_primary: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class CVListResponse(BaseModel):
    cvs: List[CVResponse]
    total: int


# ── Job ───────────────────────────────────────
class JobSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    location: Optional[str] = None
    job_type: Optional[str] = None  # remote, hybrid, onsite
    limit: int = Field(default=10, ge=1, le=20)


class JobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: Optional[str] = None
    salary_range: Optional[str] = None
    job_type: Optional[str] = None
    description: str
    requirements: list = []
    source: str
    match_score: Optional[float] = None
    matching_skills: list = []
    missing_skills: list = []
    application_url: Optional[str] = None
    posted_date: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    search_id: Optional[str] = None


# ── Application ───────────────────────────────
class ApplicationCreateRequest(BaseModel):
    job_id: str
    tailored_cv_id: Optional[str] = None


class ApplicationApproveRequest(BaseModel):
    email_subject: Optional[str] = None
    email_body: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: str
    job_id: str
    tailored_cv_id: Optional[str] = None
    status: str
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    email_sent_at: Optional[str] = None
    user_approved: bool = False
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ApplicationListResponse(BaseModel):
    applications: List[ApplicationResponse]
    total: int


# ── Chat ──────────────────────────────────────
class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: Optional[str] = None


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    agent_name: Optional[str] = None
    content: str
    metadata: Optional[dict] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: List[ChatMessageResponse]
    session_id: str


class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    updated_at: str


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]


# ── Interview Prep ────────────────────────────
class InterviewPrepRequest(BaseModel):
    job_id: str
    application_id: Optional[str] = None


class InterviewPrepResponse(BaseModel):
    id: str
    job_id: str
    company_research: dict = {}
    technical_questions: list = []
    behavioral_questions: list = []
    situational_questions: list = []
    salary_research: dict = {}
    tips: list = []
    questions_to_ask: list = []
    system_design_questions: list = []
    coding_challenges: list = []
    cultural_questions: list = []
    study_plan: dict = {}
    study_material_path: Optional[str] = None
    prep_score: Optional[float] = None
    status: str = "generating"
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Dashboard ─────────────────────────────────
class DashboardStatsResponse(BaseModel):
    total_cvs: int = 0
    total_jobs_found: int = 0
    total_applications: int = 0
    total_interviews: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    budget_limit: float = 5.0
    recent_activity: list = []
    application_pipeline: dict = {}
    match_score_distribution: dict = {}


# ── Agent / Observability ─────────────────────
class AgentStatusResponse(BaseModel):
    agent_name: str
    status: str
    plan: Optional[str] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_action: Optional[str] = None


class QuotaStatusResponse(BaseModel):
    model: str
    provider: str
    used: int
    limit: int
    percentage: float


# ── Tailored CV ───────────────────────────────
class TailorCVRequest(BaseModel):
    job_id: str
    cv_id: Optional[str] = None


class TailoredCVResponse(BaseModel):
    id: str
    job_id: str
    match_score: Optional[float] = None
    ats_score: Optional[float] = None
    cover_letter: Optional[str] = None
    pdf_path: Optional[str] = None
    changes_made: dict = {}
    status: str = "draft"
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ── Skills ────────────────────────────────────
class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    priority: int
    path: str

class SkillListResponse(BaseModel):
    skills: List[SkillResponse]
    persona: dict
    principles: List[str]
