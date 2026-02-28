-- ============================================================
-- Digital FTE — Supabase Database Schema
-- Run this in Supabase Dashboard → SQL Editor → New Query
-- ============================================================

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Users ────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    google_oauth_token JSONB DEFAULT NULL,
    google_refresh_token TEXT DEFAULT NULL,
    preferences JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ── User CVs ─────────────────────────────────
CREATE TABLE IF NOT EXISTS user_cvs (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    parsed_data JSONB DEFAULT '{}',
    raw_text TEXT,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ── CV Embeddings ────────────────────────────
CREATE TABLE IF NOT EXISTS cv_embeddings (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cv_id TEXT NOT NULL REFERENCES user_cvs(id) ON DELETE CASCADE,
    section VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Job Searches ─────────────────────────────
CREATE TABLE IF NOT EXISTS job_searches (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    cv_id TEXT REFERENCES user_cvs(id),
    search_query TEXT NOT NULL,
    target_role VARCHAR(255),
    target_location VARCHAR(255),
    filters JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Jobs ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    search_id TEXT NOT NULL REFERENCES job_searches(id) ON DELETE CASCADE,
    external_id VARCHAR(255),
    title VARCHAR(255) NOT NULL,
    company VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    salary_range VARCHAR(100),
    job_type VARCHAR(50),
    description TEXT NOT NULL,
    requirements JSONB DEFAULT '[]',
    nice_to_have JSONB DEFAULT '[]',
    responsibilities JSONB DEFAULT '[]',
    posted_date VARCHAR(50),
    application_url TEXT,
    source VARCHAR(50) NOT NULL,
    match_score FLOAT,
    matching_skills JSONB DEFAULT '[]',
    missing_skills JSONB DEFAULT '[]',
    raw_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_search_id ON jobs(search_id);
CREATE INDEX IF NOT EXISTS idx_jobs_match_score ON jobs(match_score DESC NULLS LAST);

-- ── Job Embeddings ───────────────────────────
CREATE TABLE IF NOT EXISTS job_embeddings (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    search_id TEXT,
    title VARCHAR(255),
    company VARCHAR(255),
    source VARCHAR(50),
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Tailored CVs ─────────────────────────────
CREATE TABLE IF NOT EXISTS tailored_cvs (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_cv_id TEXT REFERENCES user_cvs(id),
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    tailored_data JSONB NOT NULL,
    pdf_path TEXT,
    cover_letter TEXT,
    ats_score FLOAT,
    match_score FLOAT,
    changes_made JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── HR Contacts ──────────────────────────────
CREATE TABLE IF NOT EXISTS hr_contacts (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    hr_name VARCHAR(255),
    hr_email VARCHAR(255),
    hr_title VARCHAR(255),
    hr_linkedin VARCHAR(255),
    confidence_score FLOAT,
    source VARCHAR(100),
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Applications ─────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    tailored_cv_id TEXT REFERENCES tailored_cvs(id),
    hr_contact_id TEXT REFERENCES hr_contacts(id),
    email_subject TEXT,
    email_body TEXT,
    email_sent_at TIMESTAMP,
    gmail_message_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending_approval',
    user_approved BOOLEAN DEFAULT FALSE,
    user_approved_at TIMESTAMP,
    follow_up_count INTEGER DEFAULT 0,
    last_follow_up_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_user_id ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);

-- ── Interview Preps ──────────────────────────
CREATE TABLE IF NOT EXISTS interview_preps (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    application_id TEXT REFERENCES applications(id),
    company_research JSONB DEFAULT '{}',
    technical_questions JSONB DEFAULT '[]',
    behavioral_questions JSONB DEFAULT '[]',
    situational_questions JSONB DEFAULT '[]',
    salary_research JSONB DEFAULT '{}',
    tips JSONB DEFAULT '[]',
    study_material_path TEXT,
    prep_score FLOAT,
    status VARCHAR(50) DEFAULT 'generating',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Agent Executions ─────────────────────────
CREATE TABLE IF NOT EXISTS agent_executions (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT REFERENCES users(id),
    session_id TEXT NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    action VARCHAR(255) NOT NULL,
    plan TEXT,
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    llm_model VARCHAR(100),
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    execution_time_ms INTEGER DEFAULT 0,
    status VARCHAR(50),
    error_message TEXT,
    trace_id VARCHAR(255),
    langfuse_trace_id VARCHAR(255),
    parent_execution_id TEXT REFERENCES agent_executions(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_executions_session ON agent_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_executions_agent ON agent_executions(agent_name);

-- ── API Quota Usage ──────────────────────────
CREATE TABLE IF NOT EXISTS api_quota_usage (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    provider VARCHAR(100) NOT NULL,
    model VARCHAR(100),
    date DATE NOT NULL,
    requests_used INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    requests_limit INTEGER,
    tokens_limit INTEGER,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(provider, model, date)
);

-- ── Chat Messages ────────────────────────────
CREATE TABLE IF NOT EXISTS chat_messages (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    agent_name VARCHAR(100),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id);

-- ── User Integrations ────────────────────────
CREATE TABLE IF NOT EXISTS user_integrations (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_name VARCHAR(100) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    scopes JSONB DEFAULT '[]',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, service_name)
);

-- ============================================================
-- Storage Buckets (create manually in Supabase Storage)
-- 1. "cvs" (Private) — uploaded CVs
-- 2. "generated" (Private) — generated PDFs/PPTX
-- 3. "templates" (Public) — CV templates
-- ============================================================
