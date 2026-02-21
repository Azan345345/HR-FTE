"""
Digital FTE - ORM Models
All database tables as defined in Section 6.1 of the plan.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, Date,
    ForeignKey, TIMESTAMP, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


# ── Helpers ──────────────────────────────────────────


def new_uuid():
    return uuid.uuid4()


# ── Users ────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    google_oauth_token = Column(JSONB, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    preferences = Column(JSONB, server_default="{}")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # relationships
    cvs = relationship("UserCV", back_populates="user", cascade="all, delete-orphan")
    job_searches = relationship("JobSearch", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")
    interview_preps = relationship("InterviewPrep", back_populates="user", cascade="all, delete-orphan")
    integrations = relationship("UserIntegration", back_populates="user", cascade="all, delete-orphan")


# ── User CVs ─────────────────────────────────────────


class UserCV(Base):
    __tablename__ = "user_cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(String(10), nullable=False)  # pdf, docx
    parsed_data = Column(JSONB, nullable=False)
    raw_text = Column(Text, nullable=True)
    embedding_id = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="cvs")
    tailored_cvs = relationship("TailoredCV", back_populates="original_cv")


# ── Job Searches ─────────────────────────────────────


class JobSearch(Base):
    __tablename__ = "job_searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    cv_id = Column(UUID(as_uuid=True), ForeignKey("user_cvs.id"), nullable=True)
    search_query = Column(Text, nullable=False)
    target_role = Column(String(255), nullable=True)
    target_location = Column(String(255), nullable=True)
    filters = Column(JSONB, server_default="{}")
    status = Column(String(50), default="pending")  # pending, searching, completed, failed
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="job_searches")
    jobs = relationship("Job", back_populates="search", cascade="all, delete-orphan")


# ── Jobs ─────────────────────────────────────────────


class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    search_id = Column(UUID(as_uuid=True), ForeignKey("job_searches.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    salary_range = Column(String(100), nullable=True)
    job_type = Column(String(50), nullable=True)  # full-time, remote, hybrid
    description = Column(Text, nullable=False)
    requirements = Column(JSONB, nullable=True)
    nice_to_have = Column(JSONB, nullable=True)
    responsibilities = Column(JSONB, nullable=True)
    posted_date = Column(Date, nullable=True)
    application_url = Column(Text, nullable=True)
    source = Column(String(50), nullable=False)  # linkedin, indeed, glassdoor
    match_score = Column(Float, nullable=True)
    matching_skills = Column(JSONB, nullable=True)
    missing_skills = Column(JSONB, nullable=True)
    raw_data = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    search = relationship("JobSearch", back_populates="jobs")
    tailored_cvs = relationship("TailoredCV", back_populates="job", cascade="all, delete-orphan")
    hr_contacts = relationship("HRContact", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    interview_preps = relationship("InterviewPrep", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_jobs_search_id", "search_id"),
        Index("idx_jobs_match_score", match_score.desc()),
    )


# ── Tailored CVs ────────────────────────────────────


class TailoredCV(Base):
    __tablename__ = "tailored_cvs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    original_cv_id = Column(UUID(as_uuid=True), ForeignKey("user_cvs.id"), nullable=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    tailored_data = Column(JSONB, nullable=False)
    pdf_path = Column(Text, nullable=True)
    cover_letter = Column(Text, nullable=True)
    ats_score = Column(Float, nullable=True)
    match_score = Column(Float, nullable=True)
    changes_made = Column(JSONB, nullable=True)
    version = Column(Integer, default=1)
    status = Column(String(50), default="draft")  # draft, approved, sent
    created_at = Column(TIMESTAMP, server_default=func.now())

    original_cv = relationship("UserCV", back_populates="tailored_cvs")
    job = relationship("Job", back_populates="tailored_cvs")


# ── HR Contacts ──────────────────────────────────────


class HRContact(Base):
    __tablename__ = "hr_contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    hr_name = Column(String(255), nullable=True)
    hr_email = Column(String(255), nullable=True)
    hr_title = Column(String(255), nullable=True)
    hr_linkedin = Column(String(255), nullable=True)
    confidence_score = Column(Float, nullable=True)  # 0-1
    source = Column(String(100), nullable=True)  # hunter.io, apollo, scraped
    verified = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    job = relationship("Job", back_populates="hr_contacts")


# ── Applications ─────────────────────────────────────


class Application(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    tailored_cv_id = Column(UUID(as_uuid=True), ForeignKey("tailored_cvs.id"), nullable=True)
    hr_contact_id = Column(UUID(as_uuid=True), ForeignKey("hr_contacts.id"), nullable=True)
    email_subject = Column(Text, nullable=True)
    email_body = Column(Text, nullable=True)
    email_sent_at = Column(TIMESTAMP, nullable=True)
    gmail_message_id = Column(String(255), nullable=True)
    status = Column(String(50), default="pending_approval")
    user_approved = Column(Boolean, default=False)
    user_approved_at = Column(TIMESTAMP, nullable=True)
    follow_up_count = Column(Integer, default=0)
    last_follow_up_at = Column(TIMESTAMP, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")

    __table_args__ = (
        Index("idx_applications_user_id", "user_id"),
        Index("idx_applications_status", "status"),
    )


# ── Interview Preps ──────────────────────────────────


class InterviewPrep(Base):
    __tablename__ = "interview_preps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True)
    company_research = Column(JSONB, nullable=True)
    technical_questions = Column(JSONB, nullable=True)
    behavioral_questions = Column(JSONB, nullable=True)
    situational_questions = Column(JSONB, nullable=True)
    salary_research = Column(JSONB, nullable=True)
    tips = Column(JSONB, nullable=True)
    study_material_path = Column(Text, nullable=True)
    prep_score = Column(Float, nullable=True)
    status = Column(String(50), default="generating")
    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", back_populates="interview_preps")
    job = relationship("Job", back_populates="interview_preps")


# ── Agent Executions (Observability) ─────────────────


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    agent_name = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    plan = Column(Text, nullable=True)
    input_data = Column(JSONB, nullable=True)
    output_data = Column(JSONB, nullable=True)
    llm_model = Column(String(100), nullable=True)
    tokens_input = Column(Integer, nullable=True)
    tokens_output = Column(Integer, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    status = Column(String(50), nullable=True)  # started, completed, failed, retrying
    error_message = Column(Text, nullable=True)
    trace_id = Column(String(255), nullable=True)
    langfuse_trace_id = Column(String(255), nullable=True)
    parent_execution_id = Column(UUID(as_uuid=True), ForeignKey("agent_executions.id"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        Index("idx_agent_executions_session", "session_id"),
        Index("idx_agent_executions_agent", "agent_name"),
    )


# ── API Quota Usage ──────────────────────────────────


class ApiQuotaUsage(Base):
    __tablename__ = "api_quota_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider = Column(String(100), nullable=False)
    model = Column(String(100), nullable=True)
    date = Column(Date, nullable=False)
    requests_used = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)
    requests_limit = Column(Integer, nullable=True)
    tokens_limit = Column(Integer, nullable=True)
    last_updated = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "model", "date", name="uq_quota_provider_model_date"),
        Index("idx_api_quota_date", "provider", "date"),
    )


# ── Chat Messages ────────────────────────────────────


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUID(as_uuid=True), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, agent
    agent_name = Column(String(100), nullable=True)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONB, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        Index("idx_chat_messages_session", "session_id"),
    )


# ── User Integrations ───────────────────────────────


class UserIntegration(Base):
    __tablename__ = "user_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    service_name = Column(String(100), nullable=False)  # gmail, drive, docs
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(TIMESTAMP, nullable=True)
    scopes = Column(JSONB, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="integrations")

    __table_args__ = (
        UniqueConstraint("user_id", "service_name", name="uq_user_integration"),
    )
