"""ORM models for all database tables."""

import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime, Date,
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from app.db.database import Base


def _uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    google_oauth_token = Column(JSON, default=None)
    google_refresh_token = Column(Text, default=None)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cvs = relationship("UserCV", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# CVs
# ---------------------------------------------------------------------------
class UserCV(Base):
    __tablename__ = "user_cvs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(10), nullable=False)
    parsed_data = Column(JSON, default=dict)
    raw_text = Column(Text, default=None)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="cvs")


# ---------------------------------------------------------------------------
# CV Embeddings
# ---------------------------------------------------------------------------
class CVEmbedding(Base):
    __tablename__ = "cv_embeddings"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_id = Column(String, ForeignKey("user_cvs.id", ondelete="CASCADE"), nullable=False)
    section = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Job Searches
# ---------------------------------------------------------------------------
class JobSearch(Base):
    __tablename__ = "job_searches"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_id = Column(String, ForeignKey("user_cvs.id"), nullable=True)
    search_query = Column(Text, nullable=False)
    target_role = Column(String(255), default=None)
    target_location = Column(String(255), default=None)
    filters = Column(JSON, default=dict)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", back_populates="search", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=_uuid)
    search_id = Column(String, ForeignKey("job_searches.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(255), default=None)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), default=None)
    salary_range = Column(String(100), default=None)
    job_type = Column(String(50), default=None)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, default=list)
    nice_to_have = Column(JSON, default=list)
    responsibilities = Column(JSON, default=list)
    posted_date = Column(String(50), default=None)
    application_url = Column(Text, default=None)
    source = Column(String(50), nullable=False)
    match_score = Column(Float, default=None)
    matching_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    raw_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    search = relationship("JobSearch", back_populates="jobs")

    __table_args__ = (
        Index("idx_jobs_search_id", "search_id"),
        Index("idx_jobs_match_score", match_score.desc()),
    )


# ---------------------------------------------------------------------------
# Job Embeddings
# ---------------------------------------------------------------------------
class JobEmbedding(Base):
    __tablename__ = "job_embeddings"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    search_id = Column(String, default=None)
    title = Column(String(255), default=None)
    company = Column(String(255), default=None)
    source = Column(String(50), default=None)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Tailored CVs
# ---------------------------------------------------------------------------
class TailoredCV(Base):
    __tablename__ = "tailored_cvs"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_cv_id = Column(String, ForeignKey("user_cvs.id"), nullable=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    tailored_data = Column(JSON, nullable=False)
    pdf_path = Column(Text, default=None)
    cover_letter = Column(Text, default=None)
    ats_score = Column(Float, default=None)
    match_score = Column(Float, default=None)
    changes_made = Column(JSON, default=dict)
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# HR Contacts
# ---------------------------------------------------------------------------
class HRContact(Base):
    __tablename__ = "hr_contacts"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    hr_name = Column(String(255), default=None)
    hr_email = Column(String(255), default=None)
    hr_title = Column(String(255), default=None)
    hr_linkedin = Column(String(255), default=None)
    confidence_score = Column(Float, default=None)
    source = Column(String(100), default=None)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    tailored_cv_id = Column(String, ForeignKey("tailored_cvs.id"), nullable=True)
    hr_contact_id = Column(String, ForeignKey("hr_contacts.id"), nullable=True)
    email_subject = Column(Text, default=None)
    email_body = Column(Text, default=None)
    email_sent_at = Column(DateTime, default=None)
    gmail_message_id = Column(String(255), default=None)
    status = Column(String(50), default="pending_approval")
    user_approved = Column(Boolean, default=False)
    user_approved_at = Column(DateTime, default=None)
    follow_up_count = Column(Integer, default=0)
    last_follow_up_at = Column(DateTime, default=None)
    notes = Column(Text, default=None)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")

    __table_args__ = (
        Index("idx_applications_user_id", "user_id"),
        Index("idx_applications_status", "status"),
    )


# ---------------------------------------------------------------------------
# Interview Preps
# ---------------------------------------------------------------------------
class InterviewPrep(Base):
    __tablename__ = "interview_preps"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(String, ForeignKey("applications.id"), nullable=True)
    company_research = Column(JSON, default=dict)
    technical_questions = Column(JSON, default=list)
    behavioral_questions = Column(JSON, default=list)
    situational_questions = Column(JSON, default=list)
    salary_research = Column(JSON, default=dict)
    tips = Column(JSON, default=list)
    questions_to_ask = Column(JSON, default=list)
    system_design_questions = Column(JSON, default=list)
    coding_challenges = Column(JSON, default=list)
    cultural_questions = Column(JSON, default=list)
    study_plan = Column(JSON, default=dict)
    study_material_path = Column(Text, default=None)
    prep_score = Column(Float, default=None)
    status = Column(String(50), default="generating")
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent Executions (observability)
# ---------------------------------------------------------------------------
class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    session_id = Column(String, nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    action = Column(String(255), nullable=False)
    plan = Column(Text, default=None)
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    llm_model = Column(String(100), default=None)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    execution_time_ms = Column(Integer, default=0)
    status = Column(String(50), default=None)
    error_message = Column(Text, default=None)
    trace_id = Column(String(255), default=None)
    langfuse_trace_id = Column(String(255), default=None)
    parent_execution_id = Column(String, ForeignKey("agent_executions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# API Quota Usage
# ---------------------------------------------------------------------------
class APIQuotaUsage(Base):
    __tablename__ = "api_quota_usage"

    id = Column(String, primary_key=True, default=_uuid)
    provider = Column(String(100), nullable=False)
    model = Column(String(100), default=None)
    date = Column(Date, nullable=False)
    requests_used = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    requests_limit = Column(Integer, default=None)
    tokens_limit = Column(Integer, default=None)
    last_updated = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("provider", "model", "date", name="uq_quota_provider_model_date"),
        Index("idx_api_quota_date", "provider", "date"),
    )


# ---------------------------------------------------------------------------
# Chat Messages
# ---------------------------------------------------------------------------
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String, nullable=False, index=True)
    role = Column(String(20), nullable=False)
    agent_name = Column(String(100), default=None)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


# ---------------------------------------------------------------------------
# User Integrations
# ---------------------------------------------------------------------------
class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_name = Column(String(100), nullable=False)
    access_token = Column(Text, default=None)
    refresh_token = Column(Text, default=None)
    token_expiry = Column(DateTime, default=None)
    scopes = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "service_name", name="uq_user_integration"),
    )
